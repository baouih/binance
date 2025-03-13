#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchdog - ứng dụng theo dõi và khởi động lại tự động các dịch vụ khi cần thiết

Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import json
import logging
import psutil
import subprocess
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("watchdog.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("watchdog")

# Danh sách các dịch vụ cần giám sát
SERVICES = [
    {
        "name": "Market Notifier",
        "pid_file": "market_notifier.pid",
        "script": "auto_market_notifier.py",
        "check_interval": 60  # Giây
    },
    {
        "name": "Unified Trading Service",
        "pid_file": "unified_trading_service.pid",
        "script": "unified_trading_service.py",
        "check_interval": 60  # Giây
    },
    {
        "name": "Service Manager",
        "pid_file": "service_manager.pid",
        "script": "enhanced_service_manager.py", 
        "check_interval": 120  # Giây
    }
]

def get_pid_from_file(pid_file):
    """Lấy PID từ file"""
    try:
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
                return pid
        return None
    except Exception as e:
        logger.error(f"Lỗi khi đọc file PID {pid_file}: {e}")
        return None
        
def is_process_running(pid):
    """Kiểm tra xem tiến trình có đang chạy không"""
    try:
        if not pid:
            return False
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tiến trình {pid}: {e}")
        return False
        
def start_service(service):
    """Khởi động dịch vụ"""
    logger.info(f"Đang khởi động dịch vụ {service['name']}...")
    
    script_path = service['script']
    pid_file = service['pid_file']
    log_file = f"{service['name'].lower().replace(' ', '_')}.log"
    
    # Kiểm tra xem script có tồn tại không
    if not os.path.exists(script_path):
        logger.error(f"Không tìm thấy script {script_path}")
        return False
    
    # Khởi động dịch vụ với nohup
    cmd = f"python {script_path} > {log_file} 2>&1 & echo $! > {pid_file}"
    
    try:
        subprocess.run(cmd, shell=True, check=True)
        logger.info(f"Đã khởi động dịch vụ {service['name']}")
        
        # Đợi một chút để tiến trình được khởi tạo
        time.sleep(3)
        
        # Kiểm tra lại xem dịch vụ đã khởi động thành công chưa
        pid = get_pid_from_file(pid_file)
        if pid and is_process_running(pid):
            logger.info(f"Dịch vụ {service['name']} đã được khởi động thành công (PID: {pid})")
            return True
        else:
            logger.error(f"Dịch vụ {service['name']} không khởi động được")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ {service['name']}: {e}")
        return False
        
def check_service(service):
    """Kiểm tra và khởi động lại dịch vụ nếu cần"""
    name = service['name']
    pid_file = service['pid_file']
    
    logger.debug(f"Đang kiểm tra dịch vụ {name}...")
    
    # Lấy PID từ file
    pid = get_pid_from_file(pid_file)
    
    # Nếu không có PID, khởi động dịch vụ
    if not pid:
        logger.warning(f"Không tìm thấy PID cho dịch vụ {name}, đang khởi động lại...")
        return start_service(service)
    
    # Kiểm tra xem tiến trình có đang chạy không
    if not is_process_running(pid):
        logger.warning(f"Dịch vụ {name} đã dừng (PID: {pid}), đang khởi động lại...")
        return start_service(service)
    
    # Tiến trình đang chạy
    logger.debug(f"Dịch vụ {name} đang chạy bình thường (PID: {pid})")
    return True
    
def run():
    """Chạy watchdog"""
    logger.info("===== KHỞI ĐỘNG WATCHDOG =====")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    
    # Lưu PID của watchdog
    with open("watchdog.pid", "w") as f:
        f.write(str(os.getpid()))
    
    # Tạo từ điển lưu thời gian kiểm tra cuối cùng
    last_check_times = {}
    for service in SERVICES:
        last_check_times[service['name']] = datetime.now() - timedelta(minutes=5)  # Kiểm tra ngay lập tức
    
    # Vòng lặp chính
    try:
        while True:
            now = datetime.now()
            
            for service in SERVICES:
                name = service['name']
                interval = service['check_interval']
                
                # Kiểm tra xem đã đến thời gian kiểm tra chưa
                if (now - last_check_times[name]).total_seconds() >= interval:
                    logger.info(f"Đang kiểm tra dịch vụ {name}...")
                    status = check_service(service)
                    last_check_times[name] = now
                    
                    status_text = "✅ OK" if status else "❌ FAIL"
                    logger.info(f"Dịch vụ {name}: {status_text}")
            
            # Log heartbeat
            logger.info("Watchdog hoạt động bình thường")
            
            # Đợi 30 giây trước khi kiểm tra lại
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Watchdog đã bị dừng bởi người dùng")
    except Exception as e:
        logger.error(f"Lỗi trong vòng lặp chính của watchdog: {e}", exc_info=True)
    finally:
        # Xóa file PID
        try:
            os.remove("watchdog.pid")
        except:
            pass
        
        logger.info("===== WATCHDOG ĐÃ DỪNG =====")

if __name__ == "__main__":
    run()