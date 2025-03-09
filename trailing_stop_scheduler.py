#!/usr/bin/env python3
"""
Hệ thống điều phối và lập lịch cho Trailing Stop

Script này đảm bảo không xảy ra chồng chéo khi hoạt động và cung cấp
một giao diện thống nhất để quản lý tất cả chức năng trailing stop.
"""

import os
import sys
import time
import json
import logging
import argparse
import datetime
import subprocess
import signal
from typing import Dict, List, Optional, Tuple, Union

# Thiết lập logging cho script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trailing_stop_scheduler.log')
    ]
)

logger = logging.getLogger("trailing_stop_scheduler")

# Các đường dẫn file và PID
TRAILING_STOP_PID_FILE = 'trailing_stop.pid'
SCHEDULER_PID_FILE = 'trailing_stop_scheduler.pid'

# Đường dẫn đến các scripts
POSITION_TRAILING_STOP = 'position_trailing_stop.py'
ADD_TRAILING_STOP = 'add_trailing_stop_to_positions.py'
TEST_TRAILING_STOP = 'create_test_order_with_trailing_stop.py'

# Thời gian chờ mặc định (giây)
DEFAULT_WAIT_TIME = 3600  # 1 giờ

# Biểu thức cron mặc định
DEFAULT_SCHEDULE = "0 */1 * * *"  # Mỗi giờ

def save_pid(pid_file: str, pid: int) -> None:
    """Lưu PID vào file"""
    with open(pid_file, 'w') as f:
        f.write(str(pid))
    logger.info(f"Đã lưu PID {pid} vào {pid_file}")

def is_process_running(pid_or_file: Union[str, int]) -> bool:
    """
    Kiểm tra xem tiến trình có đang chạy không
    
    Args:
        pid_or_file: Có thể là PID hoặc đường dẫn đến file PID
        
    Returns:
        bool: True nếu tiến trình đang chạy, False nếu không
    """
    pid = None
    
    # Nếu pid_or_file là string và có thể đọc như file
    if isinstance(pid_or_file, str) and os.path.exists(pid_or_file):
        try:
            with open(pid_or_file, 'r') as f:
                pid = int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return False
    elif isinstance(pid_or_file, int) or (isinstance(pid_or_file, str) and pid_or_file.isdigit()):
        # Nếu pid_or_file là số hoặc string số
        pid = int(pid_or_file)
    else:
        return False
    
    # Kiểm tra PID
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False

def kill_process(pid: int, force: bool = False) -> bool:
    """
    Dừng một tiến trình dựa trên PID
    
    Args:
        pid: PID của tiến trình cần dừng
        force: Nếu True, sử dụng SIGKILL ngay lập tức
        
    Returns:
        bool: True nếu dừng thành công, False nếu thất bại
    """
    try:
        if force:
            os.kill(pid, signal.SIGKILL)
        else:
            os.kill(pid, signal.SIGTERM)
            
            # Đợi tối đa 5 giây
            for _ in range(10):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.5)
                except OSError:
                    break
            
            # Nếu vẫn chạy, sử dụng SIGKILL
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        
        return True
    except OSError as e:
        logger.error(f"Lỗi khi dừng tiến trình {pid}: {str(e)}")
        return False

def stop_trailing_service() -> bool:
    """
    Dừng dịch vụ trailing stop nếu đang chạy
    
    Returns:
        bool: True nếu dừng thành công hoặc không có dịch vụ, False nếu thất bại
    """
    if not os.path.exists(TRAILING_STOP_PID_FILE):
        logger.info("Không tìm thấy file PID, dịch vụ có thể không đang chạy")
        return True
    
    try:
        with open(TRAILING_STOP_PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        if is_process_running(pid):
            logger.info(f"Đang dừng dịch vụ trailing stop (PID: {pid})")
            if kill_process(pid):
                logger.info(f"Đã dừng thành công dịch vụ trailing stop (PID: {pid})")
            else:
                logger.error(f"Không thể dừng dịch vụ trailing stop (PID: {pid})")
                return False
        
        # Xóa file PID
        if os.path.exists(TRAILING_STOP_PID_FILE):
            os.remove(TRAILING_STOP_PID_FILE)
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi dừng dịch vụ trailing stop: {str(e)}")
        return False

def start_trailing_service(interval: int = 60) -> Tuple[bool, Optional[int]]:
    """
    Khởi động dịch vụ trailing stop
    
    Args:
        interval: Khoảng thời gian giữa các lần cập nhật (giây)
        
    Returns:
        Tuple[bool, Optional[int]]: (Thành công/Thất bại, PID nếu thành công)
    """
    # Dừng dịch vụ nếu đang chạy
    if is_process_running(TRAILING_STOP_PID_FILE):
        stop_trailing_service()
    
    try:
        # Khởi động dịch vụ
        command = [sys.executable, POSITION_TRAILING_STOP, "--mode", "service", "--interval", str(interval)]
        
        logger.info(f"Đang khởi động dịch vụ trailing stop với lệnh: {' '.join(command)}")
        
        # Chạy trong nền và redirect output
        with open("trailing_stop_service.log", "a") as log_file:
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
        
        # Lưu PID
        save_pid(TRAILING_STOP_PID_FILE, process.pid)
        
        logger.info(f"Đã khởi động dịch vụ trailing stop với PID {process.pid}")
        return True, process.pid
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ trailing stop: {str(e)}")
        return False, None

def add_trailing_stop() -> bool:
    """
    Thêm trailing stop cho các vị thế hiện có
    
    Returns:
        bool: True nếu thành công, False nếu thất bại
    """
    try:
        command = [sys.executable, ADD_TRAILING_STOP]
        
        logger.info(f"Đang thêm trailing stop với lệnh: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Đã thêm trailing stop thành công cho các vị thế hiện có")
            return True
        else:
            logger.error(f"Lỗi khi thêm trailing stop: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi thêm trailing stop: {str(e)}")
        return False

def check_status() -> Dict:
    """
    Kiểm tra trạng thái của hệ thống trailing stop
    
    Returns:
        Dict: Thông tin trạng thái
    """
    status = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trailing_service_running": is_process_running(TRAILING_STOP_PID_FILE),
        "scheduler_running": is_process_running(SCHEDULER_PID_FILE),
        "positions": {}
    }
    
    # Kiểm tra file PID
    if os.path.exists(TRAILING_STOP_PID_FILE):
        try:
            with open(TRAILING_STOP_PID_FILE, 'r') as f:
                status["trailing_service_pid"] = int(f.read().strip())
        except:
            status["trailing_service_pid"] = None
    
    if os.path.exists(SCHEDULER_PID_FILE):
        try:
            with open(SCHEDULER_PID_FILE, 'r') as f:
                status["scheduler_pid"] = int(f.read().strip())
        except:
            status["scheduler_pid"] = None
    
    # Lấy thông tin vị thế
    positions_file = 'active_positions.json'
    if os.path.exists(positions_file):
        try:
            with open(positions_file, 'r') as f:
                positions = json.load(f)
            
            status["positions"] = positions
            status["position_count"] = len(positions)
            
            # Đếm vị thế đã kích hoạt trailing stop
            activated = 0
            for symbol, data in positions.items():
                if data.get("trailing_activated", False):
                    activated += 1
            
            status["trailing_activated_count"] = activated
        except Exception as e:
            logger.error(f"Lỗi khi đọc file vị thế: {str(e)}")
    
    return status

def print_status(status: Dict) -> None:
    """In thông tin trạng thái ra console"""
    print("\n=== TRẠNG THÁI HỆ THỐNG TRAILING STOP ===")
    print(f"Thời gian kiểm tra: {status['time']}")
    print(f"Dịch vụ trailing stop: {'ĐANG CHẠY' if status.get('trailing_service_running') else 'DỪNG'}")
    
    if 'trailing_service_pid' in status:
        print(f"  PID: {status['trailing_service_pid']}")
    
    print(f"Dịch vụ lập lịch: {'ĐANG CHẠY' if status.get('scheduler_running') else 'DỪNG'}")
    
    if 'scheduler_pid' in status:
        print(f"  PID: {status['scheduler_pid']}")
    
    if 'positions' in status and status['positions']:
        print(f"\nĐang theo dõi: {status.get('position_count', 0)} vị thế")
        print(f"Đã kích hoạt trailing stop: {status.get('trailing_activated_count', 0)} vị thế")
        
        print("\nCHI TIẾT VỊ THẾ:")
        for symbol, data in status['positions'].items():
            print(f"  {symbol} ({data.get('side', 'Unknown')}):")
            print(f"    Giá vào: {data.get('entry_price', 'N/A')}")
            print(f"    Trailing stop: {data.get('trailing_stop', 'N/A')} ({'Đã kích hoạt' if data.get('trailing_activated', False) else 'Chưa kích hoạt'})")
            if data.get('trailing_activated', False):
                activation_price = data.get('trailing_activation', 'N/A')
                callback_rate = data.get('trailing_callback', 'N/A')
                print(f"    Kích hoạt tại: {activation_price} (Callback: {callback_rate}%)")
            print("")
    else:
        print("\nKhông tìm thấy vị thế nào đang mở")

def run_scheduled_tasks(interval: int = DEFAULT_WAIT_TIME) -> None:
    """
    Chạy các tác vụ theo lịch trình
    
    Args:
        interval: Khoảng thời gian giữa các lần chạy (giây)
    """
    # Lưu PID của scheduler
    save_pid(SCHEDULER_PID_FILE, os.getpid())
    
    logger.info(f"Bắt đầu dịch vụ lập lịch với interval {interval} giây")
    
    try:
        last_run_time = 0
        
        while True:
            current_time = int(time.time())
            
            # Nếu đã đến lúc chạy lại
            if current_time - last_run_time >= interval:
                logger.info(f"Thực hiện tác vụ theo lịch trình (interval: {interval}s)")
                
                # Thêm trailing stop cho các vị thế mới
                add_trailing_stop()
                
                # Đảm bảo dịch vụ trailing stop đang chạy
                if not is_process_running(TRAILING_STOP_PID_FILE):
                    logger.warning("Dịch vụ trailing stop không hoạt động, đang khởi động lại...")
                    start_trailing_service()
                
                last_run_time = current_time
            
            # Đợi 30 giây trước khi kiểm tra lại
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Đã dừng dịch vụ lập lịch theo yêu cầu người dùng")
    except Exception as e:
        logger.error(f"Lỗi trong dịch vụ lập lịch: {str(e)}")
    finally:
        # Xóa file PID khi thoát
        if os.path.exists(SCHEDULER_PID_FILE):
            os.remove(SCHEDULER_PID_FILE)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Hệ thống điều phối Trailing Stop')
    parser.add_argument('action', type=str, 
                      choices=['start', 'stop', 'restart', 'status', 'add', 'schedule'],
                      help='Hành động (start/stop/restart dịch vụ, check trạng thái, thêm trailing stop)')
    parser.add_argument('--interval', type=int, default=60,
                      help='Khoảng thời gian giữa các lần cập nhật (giây)')
    parser.add_argument('--schedule-interval', type=int, default=DEFAULT_WAIT_TIME,
                      help='Khoảng thời gian giữa các lần chạy tác vụ theo lịch (giây)')
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    action = args.action.lower()
    logger.info(f"Thực hiện hành động: {action}")
    
    if action == 'start':
        # Khởi động dịch vụ trailing stop
        success, _ = start_trailing_service(args.interval)
        if success:
            print("Đã khởi động dịch vụ trailing stop thành công")
        else:
            print("Không thể khởi động dịch vụ trailing stop")
    
    elif action == 'stop':
        # Dừng dịch vụ trailing stop
        if stop_trailing_service():
            print("Đã dừng dịch vụ trailing stop thành công")
        else:
            print("Không thể dừng dịch vụ trailing stop")
    
    elif action == 'restart':
        # Khởi động lại dịch vụ trailing stop
        logger.info("Đang khởi động lại dịch vụ trailing stop")
        stop_trailing_service()
        success, _ = start_trailing_service(args.interval)
        if success:
            print("Đã khởi động lại dịch vụ trailing stop thành công")
        else:
            print("Không thể khởi động lại dịch vụ trailing stop")
    
    elif action == 'status':
        # Hiển thị trạng thái
        status = check_status()
        print_status(status)
    
    elif action == 'add':
        # Thêm trailing stop cho các vị thế hiện có
        if add_trailing_stop():
            print("Đã thêm trailing stop thành công")
        else:
            print("Không thể thêm trailing stop")
    
    elif action == 'schedule':
        # Chạy dịch vụ lập lịch
        if is_process_running(SCHEDULER_PID_FILE):
            print("Dịch vụ lập lịch đã đang chạy")
            status = check_status()
            if 'scheduler_pid' in status:
                print(f"PID: {status['scheduler_pid']}")
        else:
            print(f"Đang khởi động dịch vụ lập lịch (interval: {args.schedule_interval}s)")
            try:
                run_scheduled_tasks(args.schedule_interval)
            except KeyboardInterrupt:
                print("Đã dừng dịch vụ lập lịch")

if __name__ == "__main__":
    main()