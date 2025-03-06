"""
Cấu hình Gunicorn với tắt sendfile để tránh lỗi sockets không chặn
"""
import multiprocessing

# Cài đặt cơ bản
bind = "0.0.0.0:5000"
workers = 1  # Chỉ dùng 1 worker cho Replit
timeout = 120
keepalive = 5

# File application
wsgi_app = "app:app"

# Debug và logging
errorlog = "-"  # stdout
accesslog = "-"  # stdout
loglevel = "info"

# TẮT SENDFILE (điều này là quan trọng để tránh lỗi non-blocking sockets)
enable_stdio_inheritance = True
sendfile = False  # Tắt sendfile để tránh lỗi

# Options để tăng hiệu suất
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Cài đặt ứng dụng
preload = True

print("Khởi động Gunicorn với sendfile=False")