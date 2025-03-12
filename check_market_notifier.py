#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiểm tra trạng thái dịch vụ thông báo thị trường
"""

import os
import json
import logging
import psutil
import datetime
import traceback

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("market_notifier_check.log")
    ]
)
logger = logging.getLogger("market_notifier_check")

def check_pid_file():
    """Kiểm tra file PID của market_notifier"""
    pid_file = 'market_notifier.pid'
    
    # Kiểm tra xem file PID có tồn tại không
    if not os.path.exists(pid_file):
        logger.warning("File PID không tồn tại")
        return None
    
    # Đọc PID từ file
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
            logger.info(f"Đã đọc PID {pid} từ file")
            return pid
    except Exception as e:
        logger.error(f"Lỗi khi đọc file PID: {str(e)}")
        return None

def check_process_running(pid):
    """Kiểm tra xem process có đang chạy không dựa trên PID"""
    if pid is None:
        return False
    
    try:
        process = psutil.Process(pid)
        process_status = process.status()
        
        # Kiểm tra tên process có phải là Python không
        process_name = process.name().lower()
        if "python" not in process_name:
            logger.warning(f"Process {pid} không phải là Python process ({process_name})")
            return False
        
        # Kiểm tra command line có chứa auto_market_notifier.py không
        cmd_line = " ".join(process.cmdline()).lower()
        if "auto_market_notifier.py" not in cmd_line:
            logger.warning(f"Process {pid} không phải là auto_market_notifier process ({cmd_line})")
            return False
            
        logger.info(f"Process {pid} đang chạy với trạng thái: {process_status}")
        return process_status in ['running', 'sleeping']
    except psutil.NoSuchProcess:
        logger.warning(f"Process với PID {pid} không tồn tại")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra process {pid}: {str(e)}")
        return False

def check_log_file():
    """Kiểm tra log file của market_notifier để xem hoạt động gần đây"""
    log_file = 'market_notifier.log'
    
    # Kiểm tra xem file log có tồn tại không
    if not os.path.exists(log_file):
        logger.warning("File log của market_notifier không tồn tại")
        return None
    
    # Kiểm tra thời gian sửa đổi cuối cùng của file log
    try:
        mtime = os.path.getmtime(log_file)
        last_modified = datetime.datetime.fromtimestamp(mtime)
        logger.info(f"File log được cập nhật lần cuối vào: {last_modified}")
        
        # Nếu file log đã được cập nhật trong 5 phút gần đây thì có vẻ dịch vụ đang hoạt động
        now = datetime.datetime.now()
        time_diff = now - last_modified
        recent_activity = time_diff.total_seconds() < 300  # 5 phút
        
        # Đọc các dòng log cuối cùng
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-5:] if len(lines) >= 5 else lines
            
        return {
            'last_modified': last_modified.strftime('%Y-%m-%d %H:%M:%S'),
            'recent_activity': recent_activity,
            'last_lines': [line.strip() for line in last_lines]
        }
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra file log: {str(e)}")
        return None

def main():
    """Chức năng chính để kiểm tra và báo cáo trạng thái"""
    # Kết quả mặc định
    result = {
        'running': False,
        'pid': None,
        'started_at': None,
        'last_check': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status_detail': 'Không xác định',
        'log_activity': None,
        'status': 'stopped'  # Thêm trường status để phù hợp với JavaScript
    }
    
    # Kiểm tra file PID
    pid = check_pid_file()
    result['pid'] = pid
    
    # Nếu có PID, kiểm tra xem process có đang chạy không
    if pid is not None:
        is_running = check_process_running(pid)
        result['running'] = is_running
        
        if is_running:
            result['status_detail'] = 'Đang chạy'
            result['status'] = 'running'  # Cập nhật trạng thái để phù hợp với JavaScript
            
            # Kiểm tra thời gian khởi động
            try:
                process = psutil.Process(pid)
                create_time = datetime.datetime.fromtimestamp(process.create_time())
                result['started_at'] = create_time.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
        else:
            result['status_detail'] = 'Process không tồn tại hoặc không phải là market_notifier'
            result['status'] = 'stopped'  # Cập nhật trạng thái để phù hợp với JavaScript
    else:
        result['status_detail'] = 'Không tìm thấy file PID'
        result['status'] = 'stopped'  # Cập nhật trạng thái để phù hợp với JavaScript
    
    # Kiểm tra hoạt động log gần đây
    log_info = check_log_file()
    if log_info:
        result['log_activity'] = log_info
        
        # Nếu PID check thất bại nhưng log có hoạt động gần đây, vẫn có thể service đang chạy
        if not result['running'] and log_info['recent_activity']:
            logger.warning("PID check thất bại nhưng log file có hoạt động gần đây, dịch vụ có thể vẫn đang chạy")
            # Không đặt running = True vì không xác định được PID
    
    # In kết quả dưới dạng JSON
    print(json.dumps(result, ensure_ascii=False))
    return result

if __name__ == "__main__":
    main()