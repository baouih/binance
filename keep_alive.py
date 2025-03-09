#!/usr/bin/env python3
"""
Script giữ cho Replit luôn chạy bằng cách tạo một HTTP server nhỏ
và sử dụng dịch vụ uptime để ping liên tục.
"""

from flask import Flask
from threading import Thread
import os
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("keep_alive")

app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Received keep-alive ping")
    return "Bot đang chạy!"

@app.route('/status')
def status():
    return {
        "status": "running",
        "version": "1.0.0",
        "uptime": "active"
    }

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    logger.info("Khởi động dịch vụ keep-alive")
    t = Thread(target=run)
    t.daemon = True
    t.start()
    logger.info(f"Dịch vụ keep-alive đang chạy trên cổng 8080")
    logger.info("Sử dụng dịch vụ như UptimeRobot để ping URL của Replit để giữ nó luôn hoạt động")

if __name__ == "__main__":
    keep_alive()