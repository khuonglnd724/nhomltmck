import os
import json
from typing import Callable
from .connection import ServerConnection

class UploadClient:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.chunk_size = 8192

    def upload_file(self, filepath: str, progress_callback: Callable[[int, float], None] = None) -> dict:
        """
        Upload a file to the server
        Args:
            filepath: Path to the file to upload
            progress_callback: Callback function receiving progress percentage and speed in MB/s
        Returns:
            dict: Server response with status and message
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        with ServerConnection(self.host, self.port) as connection:
            # Send file metadata
            metadata = {
                "filename": filename,
                "filesize": filesize
            }
            connection.send_data(metadata)

            # Wait for server ready signal
            response = connection.receive_response()
            if response != b"READY":
                raise ConnectionError("Server not ready to receive file")

            # Upload file in chunks
            start_time = os.times().elapsed
            uploaded_size = 0

            with open(filepath, 'rb') as f:
                while uploaded_size < filesize:
                    chunk = f.read(min(self.chunk_size, filesize - uploaded_size))
                    if not chunk:
                        break

                    connection.socket.send(chunk)
                    uploaded_size += len(chunk)

                    # Get progress acknowledgment
                    try:
                        progress_raw = connection.receive_response()
                        progress = int(progress_raw.decode())
                        
                        if progress_callback:
                            elapsed_time = os.times().elapsed - start_time
                            speed = (uploaded_size / 1024 / 1024) / elapsed_time if elapsed_time > 0 else 0
                            progress_callback(progress, speed)
                    except:
                        pass

            # Get final response
            try:
                final_response = connection.receive_response()
                return json.loads(final_response.decode())
            except Exception as e:
                return {"status": "error", "message": str(e)}

    def cancel_upload(self):
        """Cancel the current upload operation"""
        if hasattr(self, 'connection') and self.connection.socket:
            self.connection.close()

class UploadError(Exception):
    """Custom exception for upload errors"""
    pass
