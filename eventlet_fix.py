"""
Eventlet monkey patching để cải thiện hiệu suất với gunicorn và SocketIO
"""
import eventlet
eventlet.monkey_patch()