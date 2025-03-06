"""
Configuration file for Gunicorn to run with Flask-SocketIO
"""
import os
import multiprocessing

# Worker settings
worker_class = 'eventlet'
workers = 1  # SocketIO needs exactly 1 worker when using eventlet

# Bind to port 5000
bind = '0.0.0.0:5000'

# Application module
wsgi_app = 'main:app'

# Set reload to True for development
reload = True

# Set reuse-port for better connection handling
reuse_port = True

# Log settings
errorlog = '-'
accesslog = '-'
loglevel = 'info'