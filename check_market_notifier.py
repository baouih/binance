#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tiện ích kiểm tra và khởi động dịch vụ thông báo thị trường tự động
Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import logging
import subprocess
import json
import psutil
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='market_notifier_checker.log'
)
logger = logging.getLogger('market_notifier_checker')

# File PID cho market notifier
PID_FILE = 'market_notifier.pid'
LOG_FILE = 'market_notifier.log'

def check_market_notifier_status():
    """
    Kiểm tra trạng thái của dịch vụ thông báo thị trường
    Returns:
        dict: Thông tin trạng thái dịch vụ
    """
    status = {
        'running': False,
        'pid': None,
        'started_at': None,
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'monitored_coins': [],
        'last_notification': None
    }
    
    try:
        # Kiểm tra file PID
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
                
                # Kiểm tra xem process còn sống không
                if psutil.pid_exists(pid):
                    status['running'] = True
                    status['pid'] = pid
                    
                    # Lấy thời gian process đã chạy
                    try:
                        process = psutil.Process(pid)
                        create_time = datetime.fromtimestamp(process.create_time())
                        status['started_at'] = create_time.strftime('%Y-%m-%d %H:%M:%S')
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    
                    logger.info(f"Dịch vụ thông báo thị trường đang chạy với PID {pid}")
                else:
                    # Process không tồn tại, xóa file PID
                    logger.warning(f"Process {pid} không tồn tại, xóa file PID")
                    os.remove(PID_FILE)
        
        # Kiểm tra file log để lấy thông tin gần đây
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    # Đọc 10 dòng cuối
                    lines = f.readlines()[-10:]
                    
                    for line in lines:
                        # Tìm thông tin về coin được giám sát
                        if "Đang giám sát coin" in line:
                            parts = line.split("Đang giám sát coin")
                            if len(parts) > 1:
                                coins = parts[1].strip()
                                status['monitored_coins'] = [c.strip() for c in coins.split(',')]
                        
                        # Tìm thông tin về thông báo gần đây
                        if "Đã gửi thông báo thị trường" in line:
                            parts = line.split(" - ")
                            if len(parts) > 0:
                                timestamp = parts[0].strip()
                                status['last_notification'] = timestamp
            except Exception as e:
                logger.error(f"Lỗi khi đọc file log: {e}")
        
        return status
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái dịch vụ thông báo thị trường: {e}")
        return status

def start_market_notifier():
    """
    Khởi động dịch vụ thông báo thị trường
    Returns:
        bool: True nếu khởi động thành công, False nếu thất bại
    """
    logger.info("Đang khởi động dịch vụ thông báo thị trường...")
    
    try:
        # Kiểm tra xem dịch vụ đã chạy chưa
        status = check_market_notifier_status()
        if status['running']:
            logger.info(f"Dịch vụ thông báo thị trường đã đang chạy với PID {status['pid']}")
            return True
        
        # Khởi động script
        result = subprocess.run(
            ['./start_market_notifier.sh'],
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Dịch vụ thông báo thị trường đã được khởi động thành công")
            
            # Đợi một lúc để file PID được tạo
            time.sleep(2)
            
            # Kiểm tra lại trạng thái
            new_status = check_market_notifier_status()
            if new_status['running']:
                logger.info(f"Xác nhận dịch vụ thông báo thị trường đang chạy với PID {new_status['pid']}")
                return True
            else:
                logger.warning("Khởi động thành công nhưng không tìm thấy PID")
                return False
        else:
            logger.error(f"Không thể khởi động dịch vụ thông báo thị trường: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ thông báo thị trường: {e}")
        return False

if __name__ == "__main__":
    # Kiểm tra trạng thái
    status = check_market_notifier_status()
    print(json.dumps(status, indent=2))
    
    # Khởi động lại nếu cần
    if not status['running'] and len(sys.argv) > 1 and sys.argv[1] == '--start':
        if start_market_notifier():
            print("Dịch vụ thông báo thị trường đã được khởi động")
        else:
            print("Không thể khởi động dịch vụ thông báo thị trường")