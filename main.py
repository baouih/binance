"""
Main entry point cho Replit

Sử dụng phiên bản fixed_app.py mà không sử dụng dịch vụ Gunicorn
"""
# Import fixed_app và sử dụng các biến từ đó
from fixed_app import app, socketio

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)