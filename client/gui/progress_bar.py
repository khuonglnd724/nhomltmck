"""
Progress Bar Component
Member 1 - GUI Component
Hiển thị progress bar và tốc độ upload cho từng file
"""

import tkinter as tk
from tkinter import ttk


class ProgressBar(tk.Frame):
    """Widget hiển thị progress bar với tốc độ upload"""
    
    def __init__(self, parent, file_name, file_size, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.file_name = file_name
        self.file_size = file_size
        self.uploaded = 0
        self.speed = 0
        
        self.configure(bg="#2d2d44", relief="solid", bd=1)
        self.setup_ui()
    
    def setup_ui(self):
        """Thiết lập giao diện progress bar"""
        # File info
        info_frame = tk.Frame(self, bg="#2d2d44")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.name_label = tk.Label(
            info_frame,
            text=f"📄 {self.file_name}",
            font=("Segoe UI", 10, "bold"),
            bg="#2d2d44",
            fg="#e0e0e0",
            anchor="w"
        )
        self.name_label.pack(side="left")
        
        self.size_label = tk.Label(
            info_frame,
            text=self.format_size(self.file_size),
            font=("Segoe UI", 9),
            bg="#2d2d44",
            fg="#9ca3af",
            anchor="e"
        )
        self.size_label.pack(side="right")
        
        # Progress bar
        progress_frame = tk.Frame(self, bg="#2d2d44")
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            length=400,
            maximum=100
        )
        self.progress.pack(fill="x")
        
        # Status info
        status_frame = tk.Frame(self, bg="#2d2d44")
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.percent_label = tk.Label(
            status_frame,
            text="0%",
            font=("Segoe UI", 9, "bold"),
            bg="#2d2d44",
            fg="#7c3aed"
        )
        self.percent_label.pack(side="left")
        
        self.speed_label = tk.Label(
            status_frame,
            text="0 KB/s",
            font=("Segoe UI", 9),
            bg="#2d2d44",
            fg="#9ca3af"
        )
        self.speed_label.pack(side="right")
    
    def update_progress(self, uploaded, total, speed):
        """
        Cập nhật progress bar
        
        Args:
            uploaded (int): Số byte đã upload
            total (int): Tổng số byte
            speed (float): Tốc độ upload (bytes/s)
        """
        self.uploaded = uploaded
        self.speed = speed
        
        # Tính phần trăm
        percent = int((uploaded / total) * 100) if total > 0 else 0
        
        # Cập nhật progress bar
        self.progress['value'] = percent
        
        # Cập nhật labels
        self.percent_label.config(text=f"{percent}%")
        self.speed_label.config(text=f"{self.format_speed(speed)}")
        
        # Đổi màu theo trạng thái
        if percent == 100:
            self.percent_label.config(fg="#10b981")  # Green
        elif percent > 0:
            self.percent_label.config(fg="#7c3aed")  # Purple
    
    def set_status(self, status):
        """
        Đặt trạng thái cho progress bar
        
        Args:
            status (str): Trạng thái (waiting, uploading, completed, error)
        """
        status_colors = {
            'waiting': '#9ca3af',
            'uploading': '#7c3aed',
            'completed': '#10b981',
            'error': '#ef4444'
        }
        
        status_texts = {
            'waiting': '⏳ Đang chờ...',
            'uploading': '📤 Đang tải lên...',
            'completed': '✅ Hoàn thành',
            'error': '❌ Lỗi'
        }
        
        color = status_colors.get(status, '#9ca3af')
        text = status_texts.get(status, status)
        
        self.name_label.config(text=f"{text} - {self.file_name}")
        self.percent_label.config(fg=color)
    
    def format_size(self, size):
        """Format kích thước file"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def format_speed(self, speed):
        """Format tốc độ upload"""
        if speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        else:
            return f"{speed / (1024 * 1024):.1f} MB/s"


class ProgressBarManager:
    """Quản lý nhiều progress bar"""
    
    def __init__(self, parent):
        self.parent = parent
        self.progress_bars = {}  # file_id -> ProgressBar
        
        # Container frame với scrollbar
        self.setup_container()
    
    def setup_container(self):
        """Thiết lập container với scrollbar"""
        # Canvas và scrollbar
        self.canvas = tk.Canvas(self.parent, bg="#1e1e2e", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.parent, 
            orient="vertical", 
            command=self.canvas.yview
        )
        
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1e1e2e")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
    
    def add_progress_bar(self, file_id, file_name, file_size):
        """
        Thêm progress bar mới
        
        Args:
            file_id (str): ID của file
            file_name (str): Tên file
            file_size (int): Kích thước file (bytes)
        
        Returns:
            ProgressBar: Progress bar được tạo
        """
        if file_id in self.progress_bars:
            return self.progress_bars[file_id]
        
        progress_bar = ProgressBar(
            self.scrollable_frame,
            file_name,
            file_size
        )
        progress_bar.pack(fill="x", padx=5, pady=5)
        
        self.progress_bars[file_id] = progress_bar
        return progress_bar
    
    def update_progress(self, file_id, uploaded, total, speed):
        """Cập nhật progress của một file"""
        if file_id in self.progress_bars:
            self.progress_bars[file_id].update_progress(uploaded, total, speed)
    
    def set_status(self, file_id, status):
        """Đặt trạng thái cho một file"""
        if file_id in self.progress_bars:
            self.progress_bars[file_id].set_status(status)
    
    def remove_progress_bar(self, file_id):
        """Xóa progress bar"""
        if file_id in self.progress_bars:
            self.progress_bars[file_id].destroy()
            del self.progress_bars[file_id]
    
    def clear_all(self):
        """Xóa tất cả progress bars"""
        for progress_bar in self.progress_bars.values():
            progress_bar.destroy()
        self.progress_bars.clear()
    
    def get_progress_bar(self, file_id):
        """Lấy progress bar theo ID"""
        return self.progress_bars.get(file_id)


# Demo code
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Progress Bar Demo")
    root.geometry("600x400")
    root.configure(bg="#1e1e2e")
    
    # Tạo progress bar manager
    manager = ProgressBarManager(root)
    
    # Thêm một số progress bars demo
    manager.add_progress_bar("file1", "document.pdf", 5242880)  # 5MB
    manager.add_progress_bar("file2", "video.mp4", 104857600)  # 100MB
    manager.add_progress_bar("file3", "image.jpg", 2097152)    # 2MB
    
    # Demo update progress
    import time
    
    def demo_upload():
        for i in range(0, 101, 5):
            manager.update_progress("file1", i * 52429, 5242880, 524288)
            manager.update_progress("file2", i * 1048576, 104857600, 1048576)
            manager.update_progress("file3", i * 20972, 2097152, 209715)
            time.sleep(0.1)
            root.update()
        
        manager.set_status("file1", "completed")
        manager.set_status("file2", "completed")
        manager.set_status("file3", "completed")
    
    # Button để test
    tk.Button(
        root,
        text="Start Demo Upload",
        command=lambda: demo_upload(),
        bg="#7c3aed",
        fg="white",
        font=("Segoe UI", 10, "bold")
    ).pack(side="bottom", pady=10)
    
    root.mainloop()