#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trình quản lý dịch vụ nâng cao - giám sát và khởi động lại các dịch vụ khi cần thiết

Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import json
import signal
import logging
import psutil
import threading
import subprocess
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("service_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("service_manager")

# Danh sách các dịch vụ cần giám sát
SERVICES = [
    {
        "name": "Market Notifier",
        "script": "auto_market_notifier.py",
        "pid_file": "market_notifier.pid",
        "log_file": "market_notifier.log",
        "check_interval": 120,  # Kiểm tra mỗi 2 phút
        "restart_on_fail": True,
        "max_memory_mb": 200,  # Giới hạn bộ nhớ (MB)
        "max_cpu_percent": 50,  # Giới hạn CPU (%)
        "heartbeat_timeout": 600,  # Thời gian chờ tín hiệu heartbeat (giây)
        "last_checked": None
    },
    {
        "name": "Unified Trading Service",
        "script": "unified_trading_service.py",
        "pid_file": "unified_trading_service.pid",
        "log_file": "unified_trading_service.log",
        "check_interval": 120,  # Kiểm tra mỗi 2 phút
        "restart_on_fail": True,
        "max_memory_mb": 300,  # Giới hạn bộ nhớ (MB)
        "max_cpu_percent": 60,  # Giới hạn CPU (%)
        "heartbeat_timeout": 600,  # Thời gian chờ tín hiệu heartbeat (giây)
        "last_checked": None
    }
]

# Biến để kiểm soát vòng lặp chính
running = True

def signal_handler(sig, frame):
    """Xử lý tín hiệu thoát"""
    global running
    logger.info(f"Nhận được tín hiệu {sig}, đang dừng dịch vụ...")
    running = False

def is_process_running_by_pid(pid):
    """Kiểm tra xem tiến trình có đang chạy không dựa trên PID"""
    try:
        if not pid:
            return False
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tiến trình: {e}")
        return False

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

def check_heartbeat_in_log(log_file, timeout_seconds):
    """Kiểm tra heartbeat trong log file"""
    try:
        if not os.path.exists(log_file):
            logger.warning(f"Không tìm thấy file log {log_file}")
            return False
        
        # Lấy thời gian sửa đổi cuối cùng của file
        file_mtime = os.path.getmtime(log_file)
        file_mtime_dt = datetime.fromtimestamp(file_mtime)
        
        # Nếu file đã được sửa đổi gần đây, kiểm tra nội dung heartbeat
        if datetime.now() - file_mtime_dt < timedelta(seconds=timeout_seconds):
            with open(log_file, "r") as f:
                # Đọc 50 dòng cuối cùng để tìm heartbeat
                lines = f.readlines()[-50:]
                for line in reversed(lines):
                    if "Heartbeat:" in line:
                        # Lấy thời gian từ dòng log
                        try:
                            log_time_str = line.split(" - ")[0].strip()
                            log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S,%f")
                            
                            # Kiểm tra xem heartbeat có quá cũ không
                            if datetime.now() - log_time < timedelta(seconds=timeout_seconds):
                                return True
                        except Exception:
                            # Nếu không thể phân tích thời gian, giả định heartbeat gần đây
                            # vì log file mới được sửa đổi
                            return True
        
        # Không tìm thấy heartbeat gần đây
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra heartbeat trong log {log_file}: {e}")
        return False

def check_resource_usage(pid, max_memory_mb, max_cpu_percent):
    """Kiểm tra mức sử dụng tài nguyên của tiến trình"""
    try:
        process = psutil.Process(pid)
        
        # Kiểm tra mức sử dụng bộ nhớ
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Chuyển đổi sang MB
        
        # Kiểm tra mức sử dụng CPU
        cpu_percent = process.cpu_percent(interval=1)
        
        # Ghi nhật ký thông tin về tài nguyên
        logger.debug(f"Tiến trình {pid}: Bộ nhớ = {memory_mb:.2f}MB, CPU = {cpu_percent:.2f}%")
        
        # Kiểm tra có vượt quá giới hạn không
        if memory_mb > max_memory_mb:
            logger.warning(f"Tiến trình {pid} sử dụng quá nhiều bộ nhớ: {memory_mb:.2f}MB (Giới hạn: {max_memory_mb}MB)")
            return False
        
        if cpu_percent > max_cpu_percent:
            logger.warning(f"Tiến trình {pid} sử dụng quá nhiều CPU: {cpu_percent:.2f}% (Giới hạn: {max_cpu_percent}%)")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tài nguyên của tiến trình {pid}: {e}")
        return True  # Giả định OK nếu không thể kiểm tra

def start_service(service):
    """Khởi động lại một dịch vụ"""
    logger.info(f"Đang khởi động lại dịch vụ {service['name']}...")
    
    script_path = service['script']
    pid_file = service['pid_file']
    log_file = service['log_file']
    
    # Kiểm tra xem script có tồn tại không
    if not os.path.exists(script_path):
        logger.error(f"Không tìm thấy script {script_path}")
        return False
    
    # Khởi động dịch vụ với nohup
    cmd = f"python {script_path} > {log_file} 2>&1 & echo $! > {pid_file}"
    
    try:
        # Khởi động dịch vụ
        subprocess.run(cmd, shell=True, check=True)
        
        # Đợi một chút để chắc chắn tiến trình đã được khởi động
        time.sleep(2)
        
        # Kiểm tra xem tiến trình có đang chạy không
        pid = get_pid_from_file(pid_file)
        if pid and is_process_running_by_pid(pid):
            logger.info(f"Đã khởi động lại dịch vụ {service['name']} thành công (PID: {pid})")
            return True
        else:
            logger.error(f"Không thể khởi động lại dịch vụ {service['name']}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động lại dịch vụ {service['name']}: {e}")
        return False

def check_service_status(service):
    """Kiểm tra trạng thái của một dịch vụ và khởi động lại nếu cần"""
    name = service['name']
    pid_file = service['pid_file']
    log_file = service['log_file']
    heartbeat_timeout = service['heartbeat_timeout']
    max_memory_mb = service['max_memory_mb']
    max_cpu_percent = service['max_cpu_percent']
    
    logger.debug(f"Đang kiểm tra dịch vụ {name}...")
    
    # Lấy PID từ file
    pid = get_pid_from_file(pid_file)
    
    # Nếu không có PID, dịch vụ có thể chưa được khởi động
    if not pid:
        logger.warning(f"Không tìm thấy PID cho dịch vụ {name}")
        if service['restart_on_fail']:
            return start_service(service)
        return False
    
    # Kiểm tra xem tiến trình có đang chạy không
    if not is_process_running_by_pid(pid):
        logger.warning(f"Dịch vụ {name} không còn chạy (PID: {pid})")
        if service['restart_on_fail']:
            return start_service(service)
        return False
    
    # Kiểm tra heartbeat trong log
    if not check_heartbeat_in_log(log_file, heartbeat_timeout):
        logger.warning(f"Không tìm thấy heartbeat gần đây cho dịch vụ {name}")
        if service['restart_on_fail']:
            try:
                # Thử kill tiến trình cũ trước
                process = psutil.Process(pid)
                process.terminate()
                logger.info(f"Đã dừng tiến trình cũ {pid}")
                time.sleep(2)  # Đợi tiến trình dừng
            except Exception as e:
                logger.error(f"Không thể dừng tiến trình cũ {pid}: {e}")
            
            return start_service(service)
        return False
    
    # Kiểm tra tài nguyên
    if not check_resource_usage(pid, max_memory_mb, max_cpu_percent):
        logger.warning(f"Dịch vụ {name} sử dụng quá nhiều tài nguyên")
        if service['restart_on_fail']:
            try:
                # Thử kill tiến trình cũ trước
                process = psutil.Process(pid)
                process.terminate()
                logger.info(f"Đã dừng tiến trình cũ {pid}")
                time.sleep(2)  # Đợi tiến trình dừng
            except Exception as e:
                logger.error(f"Không thể dừng tiến trình cũ {pid}: {e}")
            
            return start_service(service)
        return False
    
    # Nếu mọi thứ OK
    logger.debug(f"Dịch vụ {name} đang hoạt động bình thường (PID: {pid})")
    return True

def monitor_services():
    """Giám sát tất cả các dịch vụ"""
    logger.info("Bắt đầu giám sát dịch vụ...")
    
    while running:
        try:
            current_time = datetime.now()
            
            # Kiểm tra từng dịch vụ
            for service in SERVICES:
                # Kiểm tra xem đã đến thời điểm kiểm tra lại chưa
                last_checked = service.get('last_checked')
                check_interval = service.get('check_interval', 300)  # Mặc định 5 phút
                
                if not last_checked or (current_time - last_checked).total_seconds() >= check_interval:
                    logger.info(f"Đang kiểm tra dịch vụ {service['name']}...")
                    status = check_service_status(service)
                    service['last_checked'] = current_time
                    
                    if status:
                        logger.info(f"✅ Dịch vụ {service['name']} đang hoạt động bình thường")
                    else:
                        logger.error(f"❌ Dịch vụ {service['name']} gặp sự cố")
            
            # Ghi log heartbeat
            logger.info("Heartbeat: Service Manager đang hoạt động")
            
            # Đợi một chút
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp giám sát: {e}", exc_info=True)
            time.sleep(60)  # Đợi lâu hơn nếu có lỗi

def main():
    """Hàm chính"""
    # Đăng ký xử lý tín hiệu
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Lưu PID
    with open("service_manager.pid", "w") as f:
        f.write(str(os.getpid()))
    
    logger.info(f"===== KHỞI ĐỘNG TRÌNH QUẢN LÝ DỊCH VỤ =====")
    logger.info(f"PID: {os.getpid()}")
    logger.info(f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
    
    # Giám sát các dịch vụ
    try:
        monitor_services()
    except Exception as e:
        logger.error(f"Lỗi khi giám sát dịch vụ: {e}", exc_info=True)
    finally:
        logger.info("Dừng trình quản lý dịch vụ")
        
        # Xóa file PID
        try:
            os.remove("service_manager.pid")
        except:
            pass

if __name__ == "__main__":
    main()