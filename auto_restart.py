#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Restart System - Khởi động lại các dịch vụ khi Replit thức dậy
"""

import os
import time
import logging
import requests
import subprocess
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_restart.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_restart")

def start_services():
    """Khởi động các dịch vụ cần thiết"""
    logger.info("Khởi động tất cả dịch vụ...")
    
    # Khởi động qua script đã tạo
    try:
        subprocess.run(["python", "start_all_services.py"], check=True)
        logger.info("Đã khởi động thành công tất cả dịch vụ")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ: {e}")
        return False

def keep_replit_alive():
    """Giữ Replit luôn hoạt động bằng cách tự ping định kỳ"""
    try:
        # Lấy URL của Replit
        repl_url = os.environ.get('REPLIT_DB_URL', '').split("//")[1].split(".")[0]
        if repl_url:
            repl_url = f"https://{repl_url}.repl.co"
            logger.info(f"Ping URL: {repl_url}")
            
            # Gửi request để giữ Replit thức
            response = requests.get(repl_url)
            logger.info(f"Ping thành công, status: {response.status_code}")
            return True
    except Exception as e:
        logger.error(f"Lỗi khi ping Replit: {e}")
    
    return False

def check_services_running():
    """Kiểm tra xem các dịch vụ có đang chạy không"""
    try:
        # Kiểm tra auto_market_notifier
        market_notifier_pid = None
        if os.path.exists("market_notifier.pid"):
            with open("market_notifier.pid", "r") as f:
                market_notifier_pid = f.read().strip()
        
        # Kiểm tra unified_trading_service
        trading_service_pid = None
        if os.path.exists("unified_trading_service.pid"):
            with open("unified_trading_service.pid", "r") as f:
                trading_service_pid = f.read().strip()
        
        # Kiểm tra process có tồn tại không
        result = subprocess.run(["ps", "-p", f"{market_notifier_pid},{trading_service_pid}", "-o", "pid="], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Nếu có ít nhất 1 process đang chạy
        return len(result.stdout.decode().strip().split('\n')) > 0
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra dịch vụ: {e}")
        return False

def main():
    """Hàm chính của chương trình"""
    logger.info("===== Bắt đầu hệ thống Auto Restart =====")
    
    # Khởi động ban đầu
    start_services()
    
    try:
        while True:
            # Kiểm tra dịch vụ mỗi 5 phút
            time.sleep(300)
            
            # Ping để giữ Replit thức
            keep_replit_alive()
            
            # Kiểm tra và khởi động lại nếu cần
            if not check_services_running():
                logger.warning("Các dịch vụ không chạy, đang khởi động lại...")
                start_services()
            else:
                logger.info("Các dịch vụ đang chạy bình thường")
    except KeyboardInterrupt:
        logger.info("Nhận được tín hiệu dừng từ người dùng")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")
    finally:
        logger.info("===== Kết thúc hệ thống Auto Restart =====")

if __name__ == "__main__":
    main()