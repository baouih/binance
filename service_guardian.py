#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guardian dịch vụ - Giám sát và tự động khởi động lại dịch vụ hợp nhất
khi nó bị lỗi hoặc dừng đột ngột

Sử dụng:
1. Đặt script này chạy cùng với dịch vụ hợp nhất
2. Script sẽ kiểm tra định kỳ xem dịch vụ có đang hoạt động không
3. Nếu dịch vụ không hoạt động, sẽ tự động khởi động lại

Tác giả: BinanceTrader Bot
"""

import os
import sys
import time
import signal
import logging
import subprocess
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("service_guardian.log"),
        logging.StreamHandler()
    ]
)

# Tạo logger
logger = logging.getLogger("service_guardian")

# Thông số cấu hình
PID_FILE = 'unified_trading_service.pid'
RESTART_SCRIPT = './start_unified_service.sh'
CHECK_INTERVAL = 60  # Kiểm tra mỗi 60 giây
MAX_RESTARTS = 5  # Số lần khởi động lại tối đa trong khoảng thời gian RESTART_WINDOW
RESTART_WINDOW = 3600  # Cửa sổ thời gian để đếm số lần khởi động lại (giây)

# Biến toàn cục
running = True
restart_history = []  # Lưu lịch sử thời gian khởi động lại


def signal_handler(sig, frame):
    """Xử lý tín hiệu khi nhận SIGTERM hoặc SIGINT"""
    global running
    logger.info(f"Đã nhận tín hiệu {sig}, dừng guardian...")
    running = False
    sys.exit(0)


def check_service_running():
    """Kiểm tra xem dịch vụ có đang chạy không"""
    if not os.path.exists(PID_FILE):
        logger.warning(f"File PID {PID_FILE} không tồn tại, dịch vụ có thể không chạy")
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Kiểm tra xem process có tồn tại không
        os.kill(pid, 0)  # Gửi tín hiệu 0 để kiểm tra process
        logger.debug(f"Dịch vụ đang chạy với PID {pid}")
        return True
    except ProcessLookupError:
        logger.warning(f"Process với PID {pid} không tồn tại")
        return False
    except ValueError:
        logger.error(f"Không thể đọc PID từ file {PID_FILE}")
        return False
    except PermissionError:
        logger.error(f"Không đủ quyền để kiểm tra process {pid}")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái dịch vụ: {e}")
        return False


def can_restart():
    """Kiểm tra xem có thể khởi động lại dịch vụ không (giới hạn số lần khởi động lại)"""
    global restart_history
    
    now = time.time()
    
    # Xóa những lần khởi động lại cũ hơn RESTART_WINDOW
    restart_history = [t for t in restart_history if now - t < RESTART_WINDOW]
    
    # Kiểm tra số lần khởi động lại trong cửa sổ thời gian
    if len(restart_history) >= MAX_RESTARTS:
        logger.error(f"Đã vượt quá số lần khởi động lại tối đa ({MAX_RESTARTS}) trong {RESTART_WINDOW//60} phút")
        return False
    
    return True


def restart_service():
    """Khởi động lại dịch vụ hợp nhất"""
    global restart_history
    
    if not can_restart():
        logger.warning("Không thể khởi động lại dịch vụ do vượt quá giới hạn")
        return False
    
    logger.info("Đang khởi động lại dịch vụ hợp nhất...")
    
    try:
        # Xóa file PID cũ nếu tồn tại
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.debug(f"Đã xóa file PID cũ {PID_FILE}")
        
        # Chạy script khởi động
        result = subprocess.run([RESTART_SCRIPT], shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Đã khởi động lại dịch vụ thành công")
            
            # Thêm vào lịch sử khởi động lại
            restart_history.append(time.time())
            
            # Đợi một chút để dịch vụ khởi động
            time.sleep(5)
            
            # Kiểm tra xem dịch vụ đã chạy chưa
            if check_service_running():
                logger.info("Xác nhận dịch vụ đã chạy thành công")
                return True
            else:
                logger.warning("Dịch vụ không chạy sau khi khởi động lại")
                return False
        else:
            logger.error(f"Không thể khởi động lại dịch vụ: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi khởi động lại dịch vụ: {e}")
        return False


def main():
    """Hàm chính để chạy guardian"""
    logger.info("===== Khởi động Service Guardian =====")
    logger.info(f"Đường dẫn tới script khởi động: {RESTART_SCRIPT}")
    logger.info(f"Chu kỳ kiểm tra: {CHECK_INTERVAL} giây")
    logger.info(f"Số lần khởi động lại tối đa: {MAX_RESTARTS} lần trong {RESTART_WINDOW//60} phút")
    
    # Đăng ký handler xử lý tín hiệu
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Khởi đầu thông báo
    startup_message = """
    ┌───────────────────────────────────────────────┐
    │                                               │
    │         BINANCE TRADER BOT - GUARDIAN         │
    │                                               │
    │  Giám sát và tự động khởi động lại dịch vụ    │
    │                                               │
    └───────────────────────────────────────────────┘
    """
    print(startup_message)
    
    # Vòng lặp chính
    try:
        while running:
            # Kiểm tra trạng thái dịch vụ
            if not check_service_running():
                logger.warning("Dịch vụ không chạy, đang thử khởi động lại...")
                restart_service()
            
            # Đợi đến chu kỳ kiểm tra tiếp theo
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Nhận được tín hiệu thoát từ bàn phím")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")
    finally:
        logger.info("===== Đã dừng Service Guardian =====")


if __name__ == "__main__":
    main()