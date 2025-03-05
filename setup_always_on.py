#!/usr/bin/env python3
"""
Thiết lập dịch vụ Keep Alive để bot luôn chạy 24/7
Chạy file này để khởi tạo dịch vụ keep-alive và đăng ký với UptimeRobot
"""

import os
import sys
import logging
import requests
import json
from flask import Flask
from threading import Thread
import time

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("setup_always_on")

# URL của dịch vụ UptimeRobot
UPTIME_ROBOT_URL = "https://uptimerobot.com/"

app = Flask(__name__)

@app.route('/')
def home():
    logger.info("Đã nhận ping keep-alive")
    return "Bot Binance Trader đang hoạt động!"

@app.route('/status')
def status():
    return {
        "status": "running",
        "version": "1.0.0",
        "uptime": "active"
    }

def run():
    try:
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"Khởi động dịch vụ keep-alive trên cổng {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ keep-alive: {str(e)}")

def setup_uptime_robot():
    """Hiển thị hướng dẫn cho người dùng để thiết lập UptimeRobot"""
    logger.info("\n=== HƯỚNG DẪN THIẾT LẬP UPTIME ROBOT ===")
    logger.info("1. Truy cập website: https://uptimerobot.com/")
    logger.info("2. Đăng ký tài khoản miễn phí")
    logger.info("3. Sau khi đăng nhập, chọn 'Add New Monitor'")
    logger.info("4. Chọn 'HTTP(s)' làm Monitor Type")
    logger.info("5. Đặt tên cho monitor, ví dụ: 'Binance Trader Bot'")
    logger.info(f"6. Nhập URL của Replit của bạn: https://YourReplitURL.replit.app")
    logger.info("7. Để mọi cài đặt khác ở mặc định và lưu")
    logger.info("8. UptimeRobot sẽ tự động ping ứng dụng của bạn mỗi 5 phút")
    logger.info("\nLưu ý: Tài khoản miễn phí của UptimeRobot cho phép 50 monitors")
    logger.info("Keep-alive đã được thiết lập thành công!")

if __name__ == "__main__":
    logger.info("Đang thiết lập dịch vụ Always On...")
    
    # Khởi động server trong thread riêng biệt
    t = Thread(target=run)
    t.daemon = True
    t.start()
    logger.info("Đã bắt đầu dịch vụ keep-alive trong nền")
    
    # Hiển thị hướng dẫn thiết lập UptimeRobot
    setup_uptime_robot()
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Đã dừng dịch vụ Keep-Alive")
        sys.exit(0)
