import socket
import os
import json
from datetime import datetime
import threading

class FileUploadServer:
    def __init__(self, host='0.0.0.0', port=9999, max_buffer=8192):
        self.host = host
        self.port = port
        self.max_buffer = max_buffer
        self.server_socket = None
        self.upload_dir = 'uploads'
        self.ensure_upload_directory()

    def ensure_upload_directory(self):
        """Create uploads directory if it doesn't exist"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def start(self):
        """Start the server and listen for connections"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")

        while True:
            client_socket, address = self.server_socket.accept()
            print(f"Connection from {address}")
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(client_socket, address)
            )
            client_thread.start()

    def handle_client(self, client_socket, address):
        """Handle individual client connections"""
        try:
            # Receive file metadata
            metadata_raw = self.receive_data(client_socket)
            if not metadata_raw:
                return

            metadata = json.loads(metadata_raw.decode('utf-8'))
            filename = metadata['filename']
            filesize = metadata['filesize']

            # Send acknowledgment
            client_socket.send(b"READY")

            # Receive and save file
            save_path = os.path.join(self.upload_dir, filename)
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

            # Send completion message
            if received_size == filesize:
                response = {"status": "success", "message": "File uploaded successfully"}
            else:
                response = {"status": "error", "message": "Upload incomplete"}
            
            client_socket.send(json.dumps(response).encode())

        except Exception as e:
            error_msg = {"status": "error", "message": str(e)}
            try:
                client_socket.send(json.dumps(error_msg).encode())
            except:
                pass
        finally:
            client_socket.close()

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
        if self.server_socket:
            self.server_socket.close()

if __name__ == "__main__":
    server = FileUploadServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
