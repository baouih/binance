"""
Package routes - Chứa các blueprint routes cho ứng dụng
"""

# Import các module routes để đảm bảo chúng được đăng ký
from . import bot_control
from . import sentiment_route
from . import update_route
from . import bot_api_routes
from . import config_routes