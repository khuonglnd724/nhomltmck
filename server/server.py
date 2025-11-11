import socket
import os
import json
import uuid
from datetime import datetime
import threading

class FileUploadServer:
    def __init__(self, host='127.0.0.1', port=9999, max_buffer=8192, upload_dir='uploads'):
        self.host = host
        self.port = port
        self.max_buffer = max_buffer
        self.server_socket = None
        self.upload_dir = upload_dir
        self.upload_stats = {
            'total_files': 0,
            'total_bytes': 0,
            'active_connections': 0
        }
        self.ensure_upload_directory()

    def ensure_upload_directory(self):
        """Create uploads directory if it doesn't exist"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def start(self):
        """Start the server and listen for connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[SERVER] Started on {self.host}:{self.port}")
            print(f"[SERVER] Upload directory: {os.path.abspath(self.upload_dir)}")
            print(f"[SERVER] Waiting for connections...")

            while True:
                try:
                    client_socket, address = self.server_socket.accept()
                    self.upload_stats['active_connections'] += 1
                    print(f"[CONNECTION] Client connected from {address} (Active: {self.upload_stats['active_connections']})")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
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
            # Receive file metadata
            metadata_raw = self.receive_data(client_socket)
            if not metadata_raw:
                print(f"[{address}] No metadata received")
                return

            metadata = json.loads(metadata_raw.decode('utf-8'))
            filename = metadata['filename']
            filesize = metadata['filesize']
            
            print(f"[{address}] Receiving file: {filename} ({filesize/1024:.2f} KB)")

            # Send acknowledgment
            client_socket.send(b"READY")

            # Sanitize filename and prepare save path
            safe_name = os.path.basename(filename)
            base, ext = os.path.splitext(safe_name)
            # avoid overwrite: add uuid if file exists
            candidate = safe_name
            save_path = os.path.join(self.upload_dir, candidate)
            if os.path.exists(save_path):
                candidate = f"{base}_{uuid.uuid4().hex}{ext}"
                save_path = os.path.join(self.upload_dir, candidate)
            received_size = 0
            
            with open(save_path, 'wb') as f:
                while received_size < filesize:
                    data = client_socket.recv(min(self.max_buffer, filesize - received_size))
                    if not data:
                        break
                    f.write(data)
                    received_size += len(data)
                    
                    # Send progress acknowledgment
                    progress = int((received_size / filesize) * 100)
                    client_socket.send(str(progress).encode())

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
            
            client_socket.send(json.dumps(response).encode())

        except Exception as e:
            error_msg = {"status": "error", "message": str(e)}
            print(f"[{address}] ✗ Error handling {filename}: {e}")
            try:
                client_socket.send(json.dumps(error_msg).encode())
            except:
                pass
        finally:
            self.upload_stats['active_connections'] -= 1
            client_socket.close()
            print(f"[{address}] Connection closed (Active: {self.upload_stats['active_connections']})")

    def receive_data(self, client_socket):
        """Receive data with length prefix"""
        try:
            length_raw = client_socket.recv(8)
            if not length_raw:
                return None
            
            length = int.from_bytes(length_raw, byteorder='big')
            data = b''
            
            while len(data) < length:
                chunk = client_socket.recv(min(self.max_buffer, length - len(data)))
                if not chunk:
                    return None
                data += chunk
                
            return data
        except:
            return None

    def stop(self):
        """Stop the server"""
        print(f"\n[SERVER] Shutting down...")
        print(f"[STATS] Total files received: {self.upload_stats['total_files']}")
        print(f"[STATS] Total bytes received: {self.upload_stats['total_bytes']/1024/1024:.2f} MB")
        if self.server_socket:
            self.server_socket.close()
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
