"""
Cấu hình Gunicorn cho Flask SocketIO với Eventlet
"""
import multiprocessing
import os

# Cài đặt môi trường
bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"
timeout = 120
keepalive = 5

# File application
wsgi_app = "app_wsgi:app"

# Debug và logging
errorlog = "-"  # stdout
accesslog = "-"  # stdout
loglevel = "info"

# Eventlet worker settings
worker_connections = 1000
raw_env = [
    "EVENTLET_NO_GREENDNS=yes",  # Tránh vấn đề DNS với greenlet
]

# Tùy chỉnh cho Socket
proxy_protocol = False
forwarded_allow_ips = "*"

# Options để tăng hiệu suất
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Tắt sendfile
enable_stdio_inheritance = True

# Cài đặt ứng dụng
preload = True

print("Khởi động Gunicorn với cấu hình worker_class=eventlet")