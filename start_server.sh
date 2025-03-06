#!/bin/bash
# Script khởi động server với gunicorn và eventlet

# Đảm bảo có quyền thực thi
chmod +x start_server.sh

# Cài đặt môi trường
export PYTHONUNBUFFERED=1

# Thực hiện monkey patching eventlet trước
python -c "import eventlet; eventlet.monkey_patch()"

# Khởi động server với gunicorn và worker eventlet
exec gunicorn --worker-class eventlet --workers 1 --bind 0.0.0.0:5000 --reload "wsgi:app"