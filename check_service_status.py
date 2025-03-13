#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiểm tra trạng thái tất cả các dịch vụ trong hệ thống
"""

import os
import sys
import psutil
import logging
from datetime import datetime, timedelta
from tabulate import tabulate

# Danh sách các dịch vụ cần kiểm tra
SERVICES = [
    {
        "name": "Market Notifier",
        "pid_file": "market_notifier.pid",
        "log_file": "market_notifier.log"
    },
    {
        "name": "Unified Trading Service",
        "pid_file": "unified_trading_service.pid", 
        "log_file": "unified_trading_service.log"
    },
    {
        "name": "Service Manager",
        "pid_file": "service_manager.pid",
        "log_file": "service_manager.log"
    },
    {
        "name": "Watchdog",
        "pid_file": "watchdog.pid",
        "log_file": "watchdog.log"
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
        print(f"Lỗi khi đọc file PID {pid_file}: {e}")
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
        print(f"Lỗi khi kiểm tra tiến trình {pid}: {e}")
        return False

def get_log_last_update(log_file):
    """Lấy thời điểm cập nhật cuối cùng của file log"""
    try:
        if os.path.exists(log_file):
            return datetime.fromtimestamp(os.path.getmtime(log_file))
        return None
    except Exception as e:
        print(f"Lỗi khi kiểm tra thời gian file log {log_file}: {e}")
        return None

def get_process_info(pid):
    """Lấy thông tin về tiến trình"""
    try:
        if not pid:
            return None
            
        process = psutil.Process(pid)
        
        # Lấy thông tin CPU và memory
        cpu_percent = process.cpu_percent(interval=0.5)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Chuyển sang MB
        
        # Lấy thời gian chạy
        create_time = datetime.fromtimestamp(process.create_time())
        running_time = datetime.now() - create_time
        
        # Trả về thông tin
        return {
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "create_time": create_time,
            "running_time": running_time
        }
    except Exception as e:
        print(f"Lỗi khi lấy thông tin tiến trình {pid}: {e}")
        return None

def check_heartbeat_in_log(log_file, timeout_seconds=600):
    """Kiểm tra heartbeat trong file log"""
    try:
        if not os.path.exists(log_file):
            return False
            
        # Kiểm tra thời gian cập nhật cuối của file
        file_mtime = os.path.getmtime(log_file)
        file_mtime_dt = datetime.fromtimestamp(file_mtime)
        
        # Nếu file đã được cập nhật gần đây
        if datetime.now() - file_mtime_dt < timedelta(seconds=timeout_seconds):
            try:
                with open(log_file, "r") as f:
                    # Đọc 50 dòng cuối
                    lines = f.readlines()[-50:]
                    for line in reversed(lines):
                        if "Heartbeat:" in line:
                            return True
            except Exception as e:
                print(f"Lỗi khi đọc file log {log_file}: {e}")
                
        return False
    except Exception as e:
        print(f"Lỗi khi kiểm tra heartbeat trong log {log_file}: {e}")
        return False

def main():
    """Hàm chính"""
    print(f"\n===== KIỂM TRA TRẠNG THÁI DỊCH VỤ =====")
    print(f"Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n")
    
    # Tạo danh sách để hiển thị
    table_data = []
    
    for service in SERVICES:
        name = service["name"]
        pid_file = service["pid_file"]
        log_file = service["log_file"]
        
        # Lấy PID
        pid = get_pid_from_file(pid_file)
        
        # Kiểm tra tiến trình
        is_running = is_process_running(pid)
        
        # Lấy thông tin tiến trình
        process_info = get_process_info(pid) if is_running else None
        
        # Kiểm tra log
        last_log_update = get_log_last_update(log_file)
        last_log_time_str = last_log_update.strftime("%H:%M:%S %d/%m/%Y") if last_log_update else "N/A"
        
        # Kiểm tra heartbeat
        has_heartbeat = check_heartbeat_in_log(log_file)
        
        # Xác định trạng thái
        if is_running:
            if has_heartbeat:
                status = "✅ HOẠT ĐỘNG"
            else:
                status = "⚠️ CHẠY NHƯNG KHÔNG CÓ HEARTBEAT"
        else:
            status = "❌ KHÔNG HOẠT ĐỘNG"
        
        # CPU và Memory
        cpu_percent = f"{process_info['cpu_percent']:.1f}%" if process_info else "N/A"
        memory = f"{process_info['memory_mb']:.1f} MB" if process_info else "N/A"
        
        # Thời gian chạy
        if process_info and process_info.get('running_time'):
            days = process_info['running_time'].days
            hours = process_info['running_time'].seconds // 3600
            minutes = (process_info['running_time'].seconds // 60) % 60
            running_time = f"{days}d {hours}h {minutes}m"
        else:
            running_time = "N/A"
        
        # Thêm vào bảng
        table_data.append([
            name,
            str(pid) if pid else "N/A",
            status,
            cpu_percent,
            memory,
            running_time,
            last_log_time_str
        ])
    
    # Hiển thị bảng
    headers = ["Dịch vụ", "PID", "Trạng thái", "CPU", "Memory", "Thời gian chạy", "Log cuối"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Kiểm tra xem tất cả các dịch vụ có đang chạy không
    all_running = all(row[2].startswith("✅") for row in table_data)
    
    if all_running:
        print("\n✅ Tất cả các dịch vụ đang hoạt động bình thường!")
    else:
        print("\n⚠️ Một số dịch vụ không hoạt động. Chạy 'python start_all_services.py' để khởi động lại.")
        print("   Hoặc chạy 'python service_watchdog.py' để bật watchdog giám sát tự động.")

if __name__ == "__main__":
    main()