#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script khởi động dịch vụ tích hợp ML vào hệ thống giao dịch
"""

import os
import sys
import logging
import argparse
import json
import time
import subprocess
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ml_integration_startup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('start_ml_integration')

def check_configuration():
    """
    Kiểm tra cấu hình triển khai ML
    
    Returns:
        Dict chứa thông tin cấu hình hoặc None nếu không tìm thấy
    """
    config_path = "ml_pipeline_results/ml_deployment_config.json"
    
    if not os.path.exists(config_path):
        logger.error(f"Không tìm thấy file cấu hình {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Kiểm tra tính hợp lệ của cấu hình
        if "trading_configs" not in config or not config["trading_configs"]:
            logger.error("Cấu hình không hợp lệ: Không có trading_configs")
            return None
        
        if "ml_integration_enabled" not in config:
            logger.warning("Cấu hình không có trường ml_integration_enabled, mặc định là True")
            config["ml_integration_enabled"] = True
        
        logger.info(f"Đã tải cấu hình từ {config_path}")
        logger.info(f"Số lượng mô hình được cấu hình: {len(config['trading_configs'])}")
        logger.info(f"Tích hợp ML được bật: {config['ml_integration_enabled']}")
        
        return config
        
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
        return None

def start_integration_service(interval_minutes=60, daemon=True, data_dir='real_data'):
    """
    Khởi động dịch vụ tích hợp ML
    
    Args:
        interval_minutes: Khoảng thời gian cập nhật (phút)
        daemon: Chạy như daemon hay không
        data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
    
    Returns:
        Đường dẫn đến file log hoặc None nếu thất bại
    """
    config = check_configuration()
    
    if not config:
        logger.error("Không thể khởi động dịch vụ tích hợp ML do lỗi cấu hình")
        return None
    
    if not config["ml_integration_enabled"]:
        logger.warning("Tích hợp ML bị tắt trong cấu hình, không khởi động dịch vụ")
        return None
    
    # Tạo lệnh khởi động
    command = f"python ml_integration_manager.py --interval {interval_minutes} --mode continuous --data-dir {data_dir}"
    
    if daemon:
        # Tạo file log riêng
        log_file = f"ml_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        command = f"nohup {command} > {log_file} 2>&1 &"
    
    try:
        logger.info(f"Khởi động dịch vụ tích hợp ML với khoảng thời gian {interval_minutes} phút")
        
        if daemon:
            # Khởi động như daemon
            subprocess.Popen(command, shell=True)
            
            # Đợi một chút để kiểm tra quá trình khởi động
            time.sleep(2)
            
            # Kiểm tra xem dịch vụ đã chạy chưa
            ps_command = "ps aux | grep ml_integration_manager.py | grep -v grep"
            ps_result = subprocess.run(ps_command, shell=True, capture_output=True, text=True)
            
            if ps_result.stdout.strip():
                logger.info("Dịch vụ tích hợp ML đã được khởi động thành công")
                logger.info(f"Log file: {log_file}")
                return log_file
            else:
                logger.error("Không thể khởi động dịch vụ tích hợp ML")
                return None
        else:
            # Chạy trực tiếp (blocking)
            logger.info("Chạy dịch vụ tích hợp ML trong chế độ trực tiếp")
            subprocess.run(command, shell=True)
            return "direct_mode"
            
    except Exception as e:
        logger.error(f"Lỗi khi khởi động dịch vụ tích hợp ML: {str(e)}")
        return None

def stop_integration_service():
    """
    Dừng dịch vụ tích hợp ML
    
    Returns:
        True nếu thành công
    """
    try:
        # Tìm tiến trình
        ps_command = "ps aux | grep ml_integration_manager.py | grep -v grep"
        ps_result = subprocess.run(ps_command, shell=True, capture_output=True, text=True)
        
        if not ps_result.stdout.strip():
            logger.info("Không tìm thấy tiến trình tích hợp ML đang chạy")
            return True
        
        # Lấy PID
        pids = []
        for line in ps_result.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) > 1:
                pids.append(parts[1])
        
        if not pids:
            logger.warning("Không thể xác định PID của tiến trình tích hợp ML")
            return False
        
        logger.info(f"Dừng {len(pids)} tiến trình tích hợp ML: {', '.join(pids)}")
        
        # Dừng các tiến trình
        for pid in pids:
            kill_command = f"kill {pid}"
            subprocess.run(kill_command, shell=True)
        
        # Kiểm tra xem tiến trình đã dừng chưa
        time.sleep(2)
        ps_result = subprocess.run(ps_command, shell=True, capture_output=True, text=True)
        
        if ps_result.stdout.strip():
            logger.warning("Vẫn còn tiến trình tích hợp ML đang chạy, thử kill -9")
            for pid in pids:
                kill_command = f"kill -9 {pid}"
                subprocess.run(kill_command, shell=True)
            
            time.sleep(1)
            ps_result = subprocess.run(ps_command, shell=True, capture_output=True, text=True)
            
            if ps_result.stdout.strip():
                logger.error("Không thể dừng hết các tiến trình tích hợp ML")
                return False
        
        logger.info("Đã dừng tất cả các tiến trình tích hợp ML")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi dừng dịch vụ tích hợp ML: {str(e)}")
        return False

def run_once(data_dir='real_data'):
    """
    Chạy tích hợp ML một lần
    
    Args:
        data_dir: Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)
    
    Returns:
        True nếu thành công
    """
    config = check_configuration()
    
    if not config:
        logger.error("Không thể chạy tích hợp ML do lỗi cấu hình")
        return False
    
    if not config["ml_integration_enabled"]:
        logger.warning("Tích hợp ML bị tắt trong cấu hình, không chạy")
        return False
    
    try:
        logger.info("Chạy tích hợp ML một lần")
        
        command = f"python ml_integration_manager.py --data-dir {data_dir}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Lỗi khi chạy tích hợp ML: {result.stderr}")
            return False
        
        logger.info("Đã chạy tích hợp ML thành công")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy tích hợp ML: {str(e)}")
        return False

def run_install():
    """
    Cài đặt dịch vụ tích hợp ML vào cron để chạy tự động
    
    Returns:
        True nếu thành công
    """
    try:
        logger.info("Cài đặt dịch vụ tích hợp ML vào cron")
        
        # Lấy đường dẫn hiện tại
        current_dir = os.getcwd()
        
        # Tạo lệnh cron
        cron_command = f"cd {current_dir} && python start_ml_integration.py --run-once >> ml_integration_cron.log 2>&1"
        
        # Tạo lệnh cài đặt cron
        cron_job = f"0 */1 * * * {cron_command}"
        
        # Thêm vào crontab
        temp_file = "temp_crontab"
        subprocess.run(f"crontab -l > {temp_file} 2>/dev/null || true", shell=True)
        
        with open(temp_file, 'a') as f:
            f.write(f"{cron_job}\n")
        
        subprocess.run(f"crontab {temp_file}", shell=True)
        subprocess.run(f"rm {temp_file}", shell=True)
        
        logger.info("Đã cài đặt dịch vụ tích hợp ML vào cron (chạy mỗi giờ)")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi cài đặt dịch vụ tích hợp ML vào cron: {str(e)}")
        return False

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Khởi động dịch vụ tích hợp ML')
    parser.add_argument('--interval', type=int, default=60, 
                      help='Khoảng thời gian cập nhật (phút) (mặc định: 60)')
    parser.add_argument('--no-daemon', action='store_true', 
                      help='Không chạy như daemon (mặc định: False)')
    parser.add_argument('--stop', action='store_true', 
                      help='Dừng dịch vụ tích hợp ML (mặc định: False)')
    parser.add_argument('--run-once', action='store_true', 
                      help='Chạy tích hợp ML một lần (mặc định: False)')
    parser.add_argument('--install', action='store_true', 
                      help='Cài đặt dịch vụ tích hợp ML vào cron (mặc định: False)')
    parser.add_argument('--data-dir', type=str, default='real_data',
                      help='Thư mục chứa dữ liệu thị trường thực (mặc định: real_data)')
    
    args = parser.parse_args()
    
    if args.stop:
        stop_integration_service()
    elif args.run_once:
        run_once(data_dir=args.data_dir)
    elif args.install:
        run_install()
    else:
        start_integration_service(
            interval_minutes=args.interval,
            daemon=not args.no_daemon,
            data_dir=args.data_dir
        )

if __name__ == "__main__":
    main()