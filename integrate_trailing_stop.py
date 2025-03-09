#!/usr/bin/env python3
"""
Tích hợp hệ thống Trailing Stop tự động với hệ thống giao dịch hiện có

Script này tự động:
1. Thêm Trailing Stop cho tất cả các vị thế đang mở khi chạy
2. Có thể được thiết lập để chạy theo lịch định kỳ
3. Tích hợp với add_trailing_stop_to_positions.py và position_trailing_stop.py
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
import subprocess
from typing import Dict, List, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trailing_stop_integration.log')
    ]
)

logger = logging.getLogger("trailing_stop_integration")

# Files và paths
TRAILING_STOP_PID_FILE = 'trailing_stop.pid'
TRAILING_STOP_SERVICE_FILE = 'position_trailing_stop.py'
TRAILING_STOP_ADD_FILE = 'add_trailing_stop_to_positions.py'
CONFIG_PATH = 'account_config.json'
POSITIONS_FILE = 'active_positions.json'

def is_process_running(pid_file: str) -> bool:
    """
    Kiểm tra xem tiến trình có đang chạy không
    
    Args:
        pid_file (str): Đường dẫn đến file pid
        
    Returns:
        bool: True nếu tiến trình đang chạy, False nếu không
    """
    if not os.path.exists(pid_file):
        return False
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Kiểm tra xem tiến trình có tồn tại không
        os.kill(pid, 0)
        return True
    except (FileNotFoundError, ValueError, OSError):
        return False

def start_trailing_stop_service(interval: int = 60) -> Optional[subprocess.Popen]:
    """
    Khởi động dịch vụ giám sát trailing stop
    
    Args:
        interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        
    Returns:
        Optional[subprocess.Popen]: Tiến trình nếu khởi động thành công, None nếu thất bại
    """
    try:
        # Tạo lệnh chạy dịch vụ
        command = [sys.executable, TRAILING_STOP_SERVICE_FILE, "--mode", "service", "--interval", str(interval)]
        
        # Chạy dịch vụ trong nền
        with open("trailing_stop_service.log", "a") as log_file:
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
        
        # Lưu PID vào file
        with open(TRAILING_STOP_PID_FILE, "w") as f:
            f.write(str(process.pid))
        
        logger.info(f"Dịch vụ trailing stop đã khởi động với PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ trailing stop: {str(e)}")
        return None

def stop_trailing_stop_service() -> bool:
    """
    Dừng dịch vụ giám sát trailing stop
    
    Returns:
        bool: True nếu dừng thành công, False nếu thất bại
    """
    import signal
    
    if not os.path.exists(TRAILING_STOP_PID_FILE):
        logger.info("Không tìm thấy file PID, dịch vụ có thể không đang chạy")
        return True
    
    try:
        # Đọc PID từ file
        with open(TRAILING_STOP_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Kiểm tra xem tiến trình có tồn tại không
        try:
            os.kill(pid, 0)
        except OSError:
            logger.info(f"Tiến trình {pid} không tồn tại, xóa file PID")
            os.remove(TRAILING_STOP_PID_FILE)
            return True
        
        # Gửi tín hiệu để dừng tiến trình
        logger.info(f"Gửi tín hiệu dừng đến tiến trình {pid}")
        os.kill(pid, signal.SIGTERM)
        
        # Đợi tối đa 5 giây
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                # Tiến trình đã dừng
                break
        
        # Nếu tiến trình vẫn chạy, buộc dừng
        try:
            os.kill(pid, 0)
            logger.warning(f"Tiến trình {pid} không dừng sau 5 giây, buộc dừng")
            os.kill(pid, signal.SIGKILL)
        except OSError:
            # Tiến trình đã dừng
            pass
        
        # Xóa file PID
        if os.path.exists(TRAILING_STOP_PID_FILE):
            os.remove(TRAILING_STOP_PID_FILE)
        
        logger.info(f"Đã dừng dịch vụ trailing stop (PID: {pid})")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi dừng dịch vụ trailing stop: {str(e)}")
        return False

def add_trailing_stop_to_current_positions() -> bool:
    """
    Thêm trailing stop cho các vị thế hiện có
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    try:
        # Chạy script add_trailing_stop_to_positions.py
        command = [sys.executable, TRAILING_STOP_ADD_FILE]
        
        logger.info("Đang thêm trailing stop cho các vị thế hiện có...")
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Đã thêm trailing stop thành công")
            logger.debug(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Lỗi khi thêm trailing stop: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi thêm trailing stop: {str(e)}")
        return False

def check_trailing_status() -> Dict:
    """
    Kiểm tra trạng thái hiện tại của trailing stop
    
    Returns:
        Dict: Thông tin trạng thái
    """
    status = {
        "service_running": is_process_running(TRAILING_STOP_PID_FILE),
        "positions": {}
    }
    
    # Tải dữ liệu vị thế
    try:
        if os.path.exists(POSITIONS_FILE):
            with open(POSITIONS_FILE, 'r') as f:
                positions = json.load(f)
            
            status["positions"] = positions
            status["position_count"] = len(positions)
            
            # Đếm số lượng vị thế đã kích hoạt trailing stop
            activated_count = sum(1 for pos in positions.values() if pos.get("trailing_activated", False))
            status["activated_count"] = activated_count
            
            logger.info(f"Đang theo dõi {len(positions)} vị thế, {activated_count} đã kích hoạt trailing stop")
        else:
            logger.info(f"Không tìm thấy file vị thế {POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu vị thế: {str(e)}")
    
    return status

def integrate_trailing_stop(mode: str = "once", interval: int = 60, check_only: bool = False) -> None:
    """
    Tích hợp trailing stop với hệ thống giao dịch
    
    Args:
        mode (str): Chế độ hoạt động ('once', 'service')
        interval (int): Khoảng thời gian giữa các lần cập nhật (giây)
        check_only (bool): Chỉ kiểm tra trạng thái, không thực hiện thay đổi
    """
    try:
        # Kiểm tra trạng thái hiện tại
        status = check_trailing_status()
        
        if check_only:
            logger.info("=== Trạng thái Trailing Stop ===")
            logger.info(f"Dịch vụ đang chạy: {'Có' if status['service_running'] else 'Không'}")
            if "position_count" in status:
                logger.info(f"Số vị thế đang theo dõi: {status['position_count']}")
                logger.info(f"Số vị thế đã kích hoạt trailing stop: {status.get('activated_count', 0)}")
            return
        
        # Thêm trailing stop cho các vị thế hiện có
        add_trailing_stop_to_current_positions()
        
        if mode == "service":
            # Nếu dịch vụ đã chạy, không làm gì
            if status["service_running"]:
                logger.info("Dịch vụ trailing stop đã đang chạy")
            else:
                # Khởi động dịch vụ trailing stop
                start_trailing_stop_service(interval)
        else:
            # Chế độ chạy một lần
            logger.info("Chạy một lần, không khởi động dịch vụ")
    except Exception as e:
        logger.error(f"Lỗi khi tích hợp trailing stop: {str(e)}")

def run_scheduled_integration(interval: int = 3600) -> None:
    """
    Chạy tích hợp theo lịch định kỳ
    
    Args:
        interval (int): Khoảng thời gian giữa các lần chạy (giây)
    """
    logger.info(f"Bắt đầu tích hợp theo lịch định kỳ (interval: {interval} giây)")
    
    try:
        while True:
            # Tích hợp trailing stop
            integrate_trailing_stop(mode="once")
            
            # Đợi đến lần chạy tiếp theo
            logger.info(f"Đã tích hợp xong, đợi {interval} giây đến lần chạy tiếp theo")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Đã dừng theo yêu cầu người dùng")
    except Exception as e:
        logger.error(f"Lỗi khi chạy theo lịch: {str(e)}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Tích hợp Trailing Stop với hệ thống giao dịch')
    parser.add_argument('--mode', type=str, choices=['once', 'service', 'schedule', 'check', 'stop'], default='once',
                      help='Chế độ hoạt động (once: chạy một lần, service: khởi động dịch vụ, schedule: chạy theo lịch, check: kiểm tra trạng thái, stop: dừng dịch vụ)')
    parser.add_argument('--interval', type=int, default=60,
                      help='Khoảng thời gian giữa các lần cập nhật/chạy (giây)')
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    logger.info(f"Chạy tích hợp Trailing Stop trong chế độ {args.mode}")
    
    if args.mode == 'check':
        # Chỉ kiểm tra trạng thái
        integrate_trailing_stop(check_only=True)
    elif args.mode == 'stop':
        # Dừng dịch vụ trailing stop
        stop_trailing_stop_service()
    elif args.mode == 'service':
        # Thêm trailing stop và khởi động dịch vụ
        integrate_trailing_stop(mode="service", interval=args.interval)
    elif args.mode == 'schedule':
        # Chạy theo lịch định kỳ
        run_scheduled_integration(interval=args.interval)
    else:
        # Chế độ chạy một lần
        integrate_trailing_stop(mode="once")

if __name__ == "__main__":
    main()