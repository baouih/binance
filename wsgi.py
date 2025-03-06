"""
WSGI entry point cho Gunicorn
"""
import eventlet
eventlet.monkey_patch()

from main import app, socketio

# Đảm bảo tác vụ nền được chạy trước khi app khởi động
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)