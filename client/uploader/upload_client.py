import os
import sys
import json
import time
from typing import Callable
from .connection import ServerConnection
import concurrent.futures

# Import FileQueue từ Member 2
try:
    # Thử import từ relative path
    from ..file_manager.file_queue import FileQueue
except ImportError:
    try:
        # Thử import từ absolute path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from file_manager.file_queue import FileQueue
    except ImportError:
        FileQueue = None  # Fallback nếu không tìm thấy

class UploadClient:
    def __init__(self, host='127.0.0.1', port=9999, user_id: int | None = None):
        self.host = host
        self.port = port
        self.chunk_size = 8192
        self._cancel_flag = False
        self.current_upload = None
        self.user_id = user_id
        self.use_udp_precheck = False  # Disable UDP optimization (removed)

    def upload_file(self, filepath: str, 
                   progress_callback: Callable[[int, float, str], None] = None,
                   status_callback: Callable[[str, str], None] = None) -> dict:
        """
        Upload a file to the server
        Args:
            filepath: Path to the file to upload
            progress_callback: Callback function receiving (progress %, speed MB/s, status)
            status_callback: Callback function receiving (status, message)
        Returns:
            dict: Server response with status and message
        """
        import logging
        logger = logging.getLogger("upload_client")
        try:
            if not os.path.exists(filepath):
                logger.error(f"File not found: {filepath}")
                if status_callback:
                    status_callback("error", f"File not found: {filepath}")
                raise FileNotFoundError(f"File not found: {filepath}")

            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            logger.info(f"Preparing to upload: {filename} ({filesize} bytes) to {self.host}:{self.port}")
            # Reset cancel flag and set current upload
            self._cancel_flag = False
            self.current_upload = filepath

            # UDP Pre-check optimization (tiết kiệm ~50-100ms)
            if self.use_udp_precheck:
                try:
                    from client.udp_discovery import pre_check_upload
                    if status_callback:
                        status_callback("info", "Đang kiểm tra qua UDP...")
                    logger.info(f"UDP pre-check for {filename} ({filesize} bytes) to {self.host}")
                    result = pre_check_upload(self.host, filename, filesize, 
                                            self.user_id if self.user_id else 0, 
                                            timeout=1.0)
                    logger.info(f"UDP pre-check result: {result}")
                    if result.get("status") == "REJECT":
                        logger.error(f"Server từ chối qua UDP: {result.get('reason', 'Unknown')}")
                        if status_callback:
                            status_callback("error", f"Server từ chối: {result.get('reason', 'Unknown')}")
                        return {"status": "error", "message": result.get("reason", "Server rejected")}
                    elif result.get("status") == "ERROR":
                        logger.warning(f"UDP pre-check ERROR: {result}")
                        # UDP failed, fallback to TCP (silent)
                        pass
                except ImportError:
                    logger.warning("UDP module not available, skip pre-check")
                    # UDP module not available, skip pre-check
                    pass
                except Exception as e:
                    logger.error(f"UDP pre-check exception: {e}")

            with ServerConnection(self.host, self.port) as connection:
                # Send file metadata
                metadata = {
                    "filename": filename,
                    "filesize": filesize,
                    "user_id": int(self.user_id) if isinstance(self.user_id, int) else 1  # Default to Guest
                }
                logger.info(f"Sending metadata: {metadata}")
                connection.send_data(metadata)

                # Wait for server ready signal
                response = connection.receive_response()
                if response != b"READY":
                    logger.error(f"Server not ready, response: {response}")
                    if status_callback:
                        status_callback("error", "Server not ready")
                    raise ConnectionError("Server not ready to receive file")

                # Upload file in chunks
                start_time = time.perf_counter()
                uploaded_size = 0

                with open(filepath, 'rb') as f:
                    while uploaded_size < filesize and not self._cancel_flag:
                        chunk = f.read(min(self.chunk_size, filesize - uploaded_size))
                        if not chunk:
                            break

                        connection.socket.send(chunk)
                        uploaded_size += len(chunk)

                        # Calculate progress and speed
                        elapsed_time = time.perf_counter() - start_time
                        progress = int((uploaded_size / filesize) * 100)
                        speed = (uploaded_size / 1024 / 1024) / elapsed_time if elapsed_time > 0 else 0

                        # Get progress acknowledgment from server
                        try:
                            progress_raw = connection.receive_response()
                            server_progress = int(progress_raw.decode())
                        except Exception as e:
                            logger.warning(f"Progress ack error: {e}")

                        # Call progress callback with status text
                        if progress_callback:
                            status_text = "Đang upload..." if not self._cancel_flag else "Đã hủy"
                            progress_callback(progress, speed, status_text)

                # Handle cancel case
                if self._cancel_flag:
                    logger.warning(f"Upload cancelled by user: {filename}")
                    if status_callback:
                        status_callback("cancelled", "Upload đã bị hủy")
                    return {"status": "cancelled", "message": "Upload cancelled by user"}

                # Get final response from server
                try:
                    final_response = connection.receive_response()
                    response_data = json.loads(final_response.decode())
                    logger.info(f"Server final response: {response_data}")
                    if status_callback:
                        status = "Hoàn thành" if response_data["status"] == "success" else "Lỗi"
                        status_callback(response_data["status"], status)
                    return response_data
                except Exception as e:
                    logger.error(f"Error parsing server response: {e}")
                    return {"status": "error", "message": str(e)}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Upload error: {error_msg}")
            if status_callback:
                status_callback("error", f"Lỗi: {error_msg}")
            return {"status": "error", "message": error_msg}
        finally:
            logger.info(f"Upload finished for {filepath}")
            self.current_upload = None
            self._cancel_flag = False

    def cancel_upload(self):
        """Cancel the current upload operation"""
        self._cancel_flag = True
        if hasattr(self, 'connection') and self.connection.socket:
            self.connection.close()

    @property
    def is_uploading(self):
        """Check if there's an ongoing upload"""
        return self.current_upload is not None
    
    def upload_from_queue(self, file_queue, 
                         progress_callback: Callable[[str, int, float, str], None] = None,
                         status_callback: Callable[[str, str, str], None] = None,
                         complete_callback: Callable[[str, dict], None] = None,
                         max_workers: int = 1) -> list:
        """
        Upload tất cả file từ FileQueue (Member 2)
        
        Args:
            file_queue: FileQueue object từ Member 2
            progress_callback: Callback(file_path, progress%, speed MB/s, status)
            status_callback: Callback(file_path, status, message)
            complete_callback: Callback(file_path, result) khi hoàn thành một file
            
        Returns:
            list: Danh sách kết quả upload cho từng file
        """
        if FileQueue is None:
            raise ImportError("FileQueue from Member 2 is not available")
        
        # Kiểm tra xem object có method cần thiết không thay vì isinstance
        if not hasattr(file_queue, 'get_next') or not hasattr(file_queue, 'add_file'):
            raise TypeError("Expected FileQueue-like object with get_next() and add_file() methods")
        
        results = []
        
        # If max_workers == 1, behave sequentially (compatible behavior)
        if max_workers <= 1:
            while True:
                file_item = file_queue.get_next()
                if not file_item:
                    break

                file_path = file_item['path']
                filename = os.path.basename(file_path)

                # Wrapper cho progress callback để thêm thông tin file
                def wrapped_progress(progress, speed, status, _file_path=file_path):
                    if progress_callback:
                        progress_callback(_file_path, progress, speed, status)

                # Wrapper cho status callback
                def wrapped_status(status, message, _file_path=file_path):
                    if status_callback:
                        status_callback(_file_path, status, message)

                # Upload file
                try:
                    result = self.upload_file(
                        file_path,
                        progress_callback=wrapped_progress,
                        status_callback=wrapped_status
                    )

                    results.append({
                        'file': file_path,
                        'filename': filename,
                        'result': result
                    })

                    # Callback khi hoàn thành file
                    if complete_callback:
                        complete_callback(file_path, result)

                except Exception as e:
                    error_result = {'status': 'error', 'message': str(e)}
                    results.append({
                        'file': file_path,
                        'filename': filename,
                        'result': error_result
                    })
                    if complete_callback:
                        complete_callback(file_path, error_result)
        else:
            # Parallel execution using ThreadPoolExecutor. Member 4 can choose max_workers.
            futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                while True:
                    file_item = file_queue.get_next()
                    if not file_item:
                        break
                    file_path = file_item['path']
                    filename = os.path.basename(file_path)

                    def task(path=file_path):
                        # inner wrapped callbacks for this task
                        def wrapped_progress(p, speed, status):
                            if progress_callback:
                                progress_callback(path, p, speed, status)

                        def wrapped_status(s, msg):
                            if status_callback:
                                status_callback(path, s, msg)

                        return self.upload_file(path, progress_callback=wrapped_progress, status_callback=wrapped_status)

                    futures.append((ex.submit(task), file_path, filename))

                # Collect results as they complete
                for fut, file_path, filename in futures:
                    try:
                        result = fut.result()
                    except Exception as e:
                        result = {'status': 'error', 'message': str(e)}

                    results.append({'file': file_path, 'filename': filename, 'result': result})
                    if complete_callback:
                        complete_callback(file_path, result)
        
        return results

class UploadError(Exception):
    """Custom exception for upload errors"""
    pass