import socket
import os
import json
import uuid
from datetime import datetime
import threading

# Read server configuration. Try both package-style and local imports so the
# script works when executed from the project root (`python -m server.server`)
# and when executed from inside the `server/` directory (`python server.py`).
try:
    # Preferred when running as a package: python -m server.server
    from server.server_config import (
        SERVER_HOST,
        SERVER_PORT,
        UPLOAD_DIR,
        MAX_FILE_SIZE_MB,
        MAX_CONNECTIONS,
        ENABLE_LOGGING,
        LOG_FILE,
        CONNECTION_TIMEOUT,
    )
except Exception:
    try:
        # Fallback when running the script directly from the server/ directory
        from server_config import (
            SERVER_HOST,
            SERVER_PORT,
            UPLOAD_DIR,
            MAX_FILE_SIZE_MB,
            MAX_CONNECTIONS,
            ENABLE_LOGGING,
            LOG_FILE,
            CONNECTION_TIMEOUT,
        )
    except Exception:
        # Final fallback defaults if config cannot be imported
        SERVER_HOST = '127.0.0.1'
        SERVER_PORT = 9999
        UPLOAD_DIR = 'uploads'
        MAX_FILE_SIZE_MB = 100
        MAX_CONNECTIONS = 5
        ENABLE_LOGGING = False
        LOG_FILE = None
        CONNECTION_TIMEOUT = 60


class FileUploadServer:
    def __init__(self, host=None, port=None, max_buffer=8192, upload_dir=None):
        # Use config values by default
        self.host = host or SERVER_HOST
        self.port = port or SERVER_PORT
        self.max_buffer = max_buffer
        self.server_socket = None
        # normalize upload directory from config if not provided
        self.upload_dir = os.path.abspath(upload_dir or UPLOAD_DIR)
        self.upload_stats = {
            'total_files': 0,
            'total_bytes': 0,
            'active_connections': 0
        }
        self.ensure_upload_directory()

    def ensure_upload_directory(self):
        """Create uploads directory if it doesn't exist"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir, exist_ok=True)

    def start(self):
        """Start the server and listen for connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            # Use configured max connections/backlog
            backlog = MAX_CONNECTIONS if isinstance(MAX_CONNECTIONS, int) and MAX_CONNECTIONS > 0 else 5
            self.server_socket.listen(backlog)
            print(f"[SERVER] Started on {self.host}:{self.port}")
            print(f"[SERVER] Upload directory: {self.upload_dir}")
            print(f"[SERVER] Waiting for connections... (backlog={backlog})")

            while True:
                try:
                    client_socket, address = self.server_socket.accept()
                    self.upload_stats['active_connections'] += 1
                    print(f"[CONNECTION] Client connected from {address} (Active: {self.upload_stats['active_connections']})")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except KeyboardInterrupt:
                    print("\n[SERVER] Shutting down...")
                    break
                except Exception as e:
                    print(f"[ERROR] Accept error: {e}")
        except Exception as e:
            print(f"[ERROR] Server start failed: {e}")
        finally:
            self.stop()

    def handle_client(self, client_socket, address):
        """Handle individual client connections"""
        filename = "unknown"
        start_time = datetime.now()

        try:
            # apply per-connection timeout if configured
            try:
                client_socket.settimeout(CONNECTION_TIMEOUT)
            except Exception:
                pass

            # Receive file metadata
            metadata_raw = self.receive_data(client_socket)
            if not metadata_raw:
                print(f"[{address}] No metadata received")
                return

            metadata = json.loads(metadata_raw.decode('utf-8'))
            filename = metadata.get('filename', 'unknown')
            filesize = int(metadata.get('filesize', 0))

            # Enforce max file size limit from config
            try:
                max_bytes = int(MAX_FILE_SIZE_MB) * 1024 * 1024
            except Exception:
                max_bytes = None
            if max_bytes and filesize > max_bytes:
                err = {"status": "error", "message": f"File exceeds max allowed size ({MAX_FILE_SIZE_MB} MB)"}
                client_socket.send(json.dumps(err).encode())
                print(f"[{address}] Rejected {filename}: exceeds max size")
                return

            print(f"[{address}] Receiving file: {filename} ({filesize/1024:.2f} KB)")

            # Send acknowledgment
            try:
                client_socket.send(b"READY")
            except Exception:
                print(f"[{address}] Failed to send READY")
                return

            # Sanitize filename and prepare save path
            safe_name = os.path.basename(filename)
            base, ext = os.path.splitext(safe_name)
            candidate = safe_name
            save_path = os.path.join(self.upload_dir, candidate)
            if os.path.exists(save_path):
                candidate = f"{base}_{uuid.uuid4().hex}{ext}"
                save_path = os.path.join(self.upload_dir, candidate)

            received_size = 0
            with open(save_path, 'wb') as f:
                while received_size < filesize:
                    try:
                        data = client_socket.recv(min(self.max_buffer, filesize - received_size))
                    except socket.timeout:
                        raise TimeoutError("Connection timed out while receiving file data")
                    if not data:
                        break
                    f.write(data)
                    received_size += len(data)

                    # Send progress acknowledgment
                    progress = int((received_size / filesize) * 100) if filesize else 100
                    try:
                        client_socket.send(str(progress).encode())
                    except Exception:
                        # If client disconnects, stop receiving
                        break

            # Calculate upload time and speed
            elapsed_time = (datetime.now() - start_time).total_seconds()
            speed = (received_size / 1024 / 1024) / elapsed_time if elapsed_time > 0 else 0

            # Send completion message
            if received_size == filesize:
                response = {
                    "status": "success",
                    "message": "File uploaded successfully",
                    "filename": filename,
                    "size": received_size,
                    "time": elapsed_time,
                    "speed": speed
                }
                self.upload_stats['total_files'] += 1
                self.upload_stats['total_bytes'] += received_size
                print(f"[{address}] ✓ Upload completed: {filename} ({speed:.2f} MB/s)")
            else:
                response = {
                    "status": "error",
                    "message": f"Upload incomplete ({received_size}/{filesize} bytes)"
                }
                print(f"[{address}] ✗ Upload incomplete: {filename}")

            try:
                client_socket.send(json.dumps(response).encode())
            except Exception:
                pass

        except Exception as e:
            error_msg = {"status": "error", "message": str(e)}
            print(f"[{address}] ✗ Error handling {filename}: {e}")
            try:
                client_socket.send(json.dumps(error_msg).encode())
            except Exception:
                pass
        finally:
            try:
                self.upload_stats['active_connections'] -= 1
            except Exception:
                pass
            try:
                client_socket.close()
            except Exception:
                pass
            print(f"[{address}] Connection closed (Active: {self.upload_stats.get('active_connections', 0)})")

    def receive_data(self, client_socket):
        """Receive data with 8-byte big-endian length prefix"""
        try:
            length_raw = client_socket.recv(8)
            if not length_raw or len(length_raw) < 8:
                return None
            length = int.from_bytes(length_raw, byteorder='big')
            data = b''
            while len(data) < length:
                chunk = client_socket.recv(min(self.max_buffer, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            return data
        except Exception:
            return None

    def stop(self):
        """Stop the server"""
        print(f"\n[SERVER] Shutting down...")
        print(f"[STATS] Total files received: {self.upload_stats.get('total_files', 0)}")
        print(f"[STATS] Total bytes received: {self.upload_stats.get('total_bytes', 0)/1024/1024:.2f} MB")
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        print(f"[SERVER] Stopped")


if __name__ == "__main__":
    print("="*60)
    print("FILE UPLOAD SERVER - Member 3")
    print("="*60)
    server = FileUploadServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Received shutdown signal")
        server.stop()
