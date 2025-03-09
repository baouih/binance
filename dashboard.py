#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dashboard giám sát hệ thống trading
"""

import os
import sys
import json
import time
import datetime
import logging
import argparse
import subprocess
import threading
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("dashboard")

# Danh sách các dịch vụ cần giám sát
SERVICES = {
    "main_trading_bot": {
        "pid_file": "main.pid",
        "log_file": "auto_trade.log",
        "description": "Bot giao dịch chính"
    },
    "auto_sltp_manager": {
        "pid_file": "auto_sltp_manager.pid",
        "log_file": "auto_sltp_manager.log",
        "description": "Quản lý SL/TP tự động"
    },
    "trailing_stop": {
        "pid_file": "trailing_stop.pid",
        "log_file": "trailing_stop_service.log",
        "description": "Dịch vụ Trailing Stop"
    },
    "telegram_notifier": {
        "pid_file": "telegram_notifier.pid",
        "log_file": "telegram_notifier.log",
        "description": "Thông báo Telegram"
    }
}

# Các tệp dữ liệu quan trọng cần giám sát
IMPORTANT_FILES = {
    "account_balance": {
        "file": "account_balance.json",
        "description": "Số dư tài khoản"
    },
    "active_positions": {
        "file": "active_positions.json",
        "description": "Vị thế đang mở"
    },
    "trading_history": {
        "file": "trading_history.json", 
        "description": "Lịch sử giao dịch"
    },
    "trailing_stop_history": {
        "file": "trailing_stop_history.json",
        "description": "Lịch sử trailing stop"
    }
}

class Dashboard:
    def __init__(self):
        self.service_statuses = {}
        self.file_data = {}
        self.account_data = {}
        self.positions = {}
        self.update_interval = 30  # Chu kỳ cập nhật (giây)
        self.integrated_manager = "integrated_startup.py"
        self.last_update_time = datetime.datetime.now()
    
    def check_service_status(self, name, details):
        """Kiểm tra trạng thái của một dịch vụ"""
        pid_file = details["pid_file"]
        log_file = details["log_file"]
        
        status = {
            "name": name,
            "description": details["description"],
            "running": False,
            "pid": None,
            "last_log": None,
            "uptime": None,
            "status": "stopped",
            "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Kiểm tra PID file
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())
                    status["pid"] = pid
                    
                    # Kiểm tra xem tiến trình có đang chạy không
                    try:
                        os.kill(pid, 0)  # Kiểm tra tiến trình tồn tại
                        status["running"] = True
                        status["status"] = "running"
                        
                        # Lấy thời gian khởi động
                        try:
                            process_start_time = datetime.datetime.fromtimestamp(
                                os.path.getctime(pid_file)
                            )
                            uptime = datetime.datetime.now() - process_start_time
                            status["uptime"] = str(uptime).split('.')[0]  # Bỏ microseconds
                        except Exception as e:
                            logger.warning(f"Không thể lấy thời gian khởi động cho {name}: {e}")
                    except ProcessLookupError:
                        status["status"] = "stopped (stale pid)"
                    except Exception as e:
                        logger.error(f"Lỗi khi kiểm tra tiến trình {pid} cho {name}: {e}")
                        status["status"] = "unknown"
            except Exception as e:
                logger.error(f"Không thể đọc PID từ {pid_file} cho {name}: {e}")
        
        # Kiểm tra log file
        if os.path.exists(log_file):
            try:
                # Lấy các dòng log cuối cùng
                p = subprocess.run(["tail", "-n", "1", log_file], capture_output=True, text=True)
                status["last_log"] = p.stdout.strip() if p.stdout else "No logs"
            except Exception as e:
                logger.error(f"Không thể đọc log từ {log_file} cho {name}: {e}")
        
        return status
    
    def update_service_statuses(self):
        """Cập nhật trạng thái của tất cả các dịch vụ"""
        for name, details in SERVICES.items():
            self.service_statuses[name] = self.check_service_status(name, details)
    
    def update_file_data(self):
        """Cập nhật dữ liệu từ các file quan trọng"""
        for name, details in IMPORTANT_FILES.items():
            file_path = details["file"]
            self.file_data[name] = {
                "name": name,
                "description": details["description"],
                "exists": os.path.exists(file_path),
                "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                "last_modified": datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).strftime("%Y-%m-%d %H:%M:%S") if os.path.exists(file_path) else "N/A"
            }
    
    def update_account_data(self):
        """Cập nhật dữ liệu tài khoản"""
        try:
            if os.path.exists("account_balance.json"):
                with open("account_balance.json", "r") as f:
                    self.account_data = json.load(f)
        except Exception as e:
            logger.error(f"Không thể đọc dữ liệu tài khoản: {e}")
    
    def update_positions(self):
        """Cập nhật thông tin vị thế"""
        try:
            if os.path.exists("active_positions.json"):
                with open("active_positions.json", "r") as f:
                    self.positions = json.load(f)
        except Exception as e:
            logger.error(f"Không thể đọc dữ liệu vị thế: {e}")
    
    def update_all(self):
        """Cập nhật tất cả dữ liệu"""
        self.update_service_statuses()
        self.update_file_data()
        self.update_account_data()
        self.update_positions()
        self.last_update_time = datetime.datetime.now()
    
    def start_service(self, name):
        """Khởi động một dịch vụ"""
        if os.path.exists(self.integrated_manager):
            cmd = f"python {self.integrated_manager} --action start --service {name}"
            try:
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"Đã khởi động dịch vụ {name}")
                return True
            except Exception as e:
                logger.error(f"Không thể khởi động dịch vụ {name}: {e}")
                return False
        else:
            logger.error(f"Không tìm thấy integrated manager {self.integrated_manager}")
            return False
    
    def stop_service(self, name):
        """Dừng một dịch vụ"""
        if os.path.exists(self.integrated_manager):
            cmd = f"python {self.integrated_manager} --action stop --service {name}"
            try:
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"Đã dừng dịch vụ {name}")
                return True
            except Exception as e:
                logger.error(f"Không thể dừng dịch vụ {name}: {e}")
                return False
        else:
            logger.error(f"Không tìm thấy integrated manager {self.integrated_manager}")
            return False
    
    def restart_service(self, name):
        """Khởi động lại một dịch vụ"""
        if os.path.exists(self.integrated_manager):
            cmd = f"python {self.integrated_manager} --action restart --service {name}"
            try:
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"Đã khởi động lại dịch vụ {name}")
                return True
            except Exception as e:
                logger.error(f"Không thể khởi động lại dịch vụ {name}: {e}")
                return False
        else:
            logger.error(f"Không tìm thấy integrated manager {self.integrated_manager}")
            return False
    
    def start_all_services(self):
        """Khởi động tất cả dịch vụ"""
        if os.path.exists(self.integrated_manager):
            cmd = f"python {self.integrated_manager} --action start"
            try:
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"Đã khởi động tất cả dịch vụ")
                return True
            except Exception as e:
                logger.error(f"Không thể khởi động tất cả dịch vụ: {e}")
                return False
        else:
            logger.error(f"Không tìm thấy integrated manager {self.integrated_manager}")
            return False
    
    def stop_all_services(self):
        """Dừng tất cả dịch vụ"""
        if os.path.exists(self.integrated_manager):
            cmd = f"python {self.integrated_manager} --action stop"
            try:
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"Đã dừng tất cả dịch vụ")
                return True
            except Exception as e:
                logger.error(f"Không thể dừng tất cả dịch vụ: {e}")
                return False
        else:
            logger.error(f"Không tìm thấy integrated manager {self.integrated_manager}")
            return False
    
    def restart_all_services(self):
        """Khởi động lại tất cả dịch vụ"""
        if os.path.exists(self.integrated_manager):
            cmd = f"python {self.integrated_manager} --action restart"
            try:
                subprocess.run(cmd, shell=True, check=True)
                logger.info(f"Đã khởi động lại tất cả dịch vụ")
                return True
            except Exception as e:
                logger.error(f"Không thể khởi động lại tất cả dịch vụ: {e}")
                return False
        else:
            logger.error(f"Không tìm thấy integrated manager {self.integrated_manager}")
            return False
    
    def display_service_status(self):
        """Hiển thị trạng thái dịch vụ"""
        headers = ["Dịch vụ", "Mô tả", "Trạng thái", "PID", "Thời gian chạy", "Log gần nhất"]
        rows = []
        
        for name, status in self.service_statuses.items():
            rows.append([
                name,
                status["description"],
                "🟢 Running" if status["running"] else "🔴 Stopped",
                status["pid"] if status["pid"] else "N/A",
                status["uptime"] if status["uptime"] else "N/A",
                status["last_log"][:50] + "..." if status["last_log"] and len(status["last_log"]) > 50 else status["last_log"] if status["last_log"] else "N/A"
            ])
        
        return tabulate(rows, headers, tablefmt="pretty")
    
    def display_file_status(self):
        """Hiển thị trạng thái các file dữ liệu"""
        headers = ["Tệp dữ liệu", "Mô tả", "Tồn tại", "Kích thước", "Cập nhật lần cuối"]
        rows = []
        
        for name, data in self.file_data.items():
            rows.append([
                name,
                data["description"],
                "✅" if data["exists"] else "❌",
                f"{data['size'] / 1024:.2f} KB" if data["exists"] else "N/A",
                data["last_modified"]
            ])
        
        return tabulate(rows, headers, tablefmt="pretty")
    
    def display_account_info(self):
        """Hiển thị thông tin tài khoản"""
        if not self.account_data:
            return "Không có dữ liệu tài khoản"
        
        try:
            if "balance" in self.account_data:
                balance = self.account_data["balance"]
                result = f"Số dư tài khoản: {balance:.2f} USDT\n"
            else:
                result = "Không tìm thấy thông tin số dư trong file account_balance.json\n"
            
            if "profit_today" in self.account_data:
                profit = self.account_data["profit_today"]
                result += f"Lợi nhuận hôm nay: {profit:.2f} USDT\n"
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi hiển thị thông tin tài khoản: {e}")
            return "Không thể hiển thị thông tin tài khoản"
    
    def display_positions(self):
        """Hiển thị thông tin vị thế đang mở"""
        if not self.positions:
            return "Không có vị thế đang mở"
        
        headers = ["Cặp", "Hướng", "Giá vào", "Số lượng", "Đòn bẩy", "SL", "TP", "Lợi nhuận %"]
        rows = []
        
        try:
            for symbol, position in self.positions.items():
                rows.append([
                    symbol,
                    position.get("side", "N/A"),
                    f"{float(position.get('entry_price', 0)):.2f}",
                    position.get("quantity", "N/A"),
                    position.get("leverage", "N/A"),
                    f"{float(position.get('stop_loss', 0)):.2f}" if position.get("stop_loss") else "N/A",
                    f"{float(position.get('take_profit', 0)):.2f}" if position.get("take_profit") else "N/A",
                    f"{float(position.get('profit_percent', 0)):.2f}%"
                ])
            
            return tabulate(rows, headers, tablefmt="pretty")
        except Exception as e:
            logger.error(f"Lỗi khi hiển thị thông tin vị thế: {e}")
            return "Không thể hiển thị thông tin vị thế"
    
    def display_dashboard(self):
        """Hiển thị dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n" + "="*80)
        print(f"🚀 DASHBOARD QUẢN LÝ HỆ THỐNG GIAO DỊCH TIỀN ĐIỆN TỬ")
        print(f"⏰ Cập nhật lần cuối: {self.last_update_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
        
        print("📊 THÔNG TIN TÀI KHOẢN")
        print("-"*80)
        print(self.display_account_info())
        print()
        
        print("📈 VỊ THẾ ĐANG MỞ")
        print("-"*80)
        print(self.display_positions())
        print()
        
        print("🔄 TRẠNG THÁI DỊCH VỤ")
        print("-"*80)
        print(self.display_service_status())
        print()
        
        print("📁 TRẠNG THÁI TỆP DỮ LIỆU")
        print("-"*80)
        print(self.display_file_status())
        print()
        
        print("💡 MENU ĐIỀU KHIỂN")
        print("-"*80)
        print("1. Cập nhật dashboard")
        print("2. Khởi động tất cả dịch vụ")
        print("3. Dừng tất cả dịch vụ")
        print("4. Khởi động lại tất cả dịch vụ")
        print("5. Quản lý dịch vụ riêng lẻ")
        print("q. Thoát")
        print("\n" + "="*80)
    
    def manage_services(self):
        """Menu quản lý dịch vụ riêng lẻ"""
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            print("\n" + "="*80)
            print("🔧 QUẢN LÝ DỊCH VỤ RIÊNG LẺ")
            print("="*80 + "\n")
            
            print(self.display_service_status())
            print("\nChọn dịch vụ để quản lý:")
            
            services = list(SERVICES.keys())
            for i, service in enumerate(services, 1):
                print(f"{i}. {service} - {SERVICES[service]['description']}")
            
            print("\nr. Quay lại menu chính")
            print("q. Thoát")
            
            choice = input("\nNhập lựa chọn của bạn: ")
            
            if choice.lower() == 'r':
                break
            elif choice.lower() == 'q':
                sys.exit(0)
            elif choice.isdigit() and 1 <= int(choice) <= len(services):
                service_name = services[int(choice) - 1]
                
                while True:
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print("\n" + "="*80)
                    print(f"🔧 QUẢN LÝ DỊCH VỤ: {service_name}")
                    print("="*80 + "\n")
                    
                    status = self.service_statuses.get(service_name, {})
                    print(f"Trạng thái: {'🟢 Đang chạy' if status.get('running', False) else '🔴 Đã dừng'}")
                    print(f"PID: {status.get('pid', 'N/A')}")
                    print(f"Thời gian chạy: {status.get('uptime', 'N/A')}")
                    
                    print("\nHành động:")
                    print("1. Khởi động dịch vụ")
                    print("2. Dừng dịch vụ")
                    print("3. Khởi động lại dịch vụ")
                    print("\nr. Quay lại menu quản lý dịch vụ")
                    print("q. Thoát")
                    
                    sub_choice = input("\nNhập lựa chọn của bạn: ")
                    
                    if sub_choice == '1':
                        self.start_service(service_name)
                        time.sleep(2)
                        self.update_all()
                    elif sub_choice == '2':
                        self.stop_service(service_name)
                        time.sleep(2)
                        self.update_all()
                    elif sub_choice == '3':
                        self.restart_service(service_name)
                        time.sleep(2)
                        self.update_all()
                    elif sub_choice.lower() == 'r':
                        break
                    elif sub_choice.lower() == 'q':
                        sys.exit(0)
    
    def run(self):
        """Chạy dashboard"""
        self.update_all()
        
        while True:
            self.display_dashboard()
            
            choice = input("\nNhập lựa chọn của bạn: ")
            
            if choice == '1':
                self.update_all()
            elif choice == '2':
                self.start_all_services()
                time.sleep(2)
                self.update_all()
            elif choice == '3':
                self.stop_all_services()
                time.sleep(2)
                self.update_all()
            elif choice == '4':
                self.restart_all_services()
                time.sleep(2)
                self.update_all()
            elif choice == '5':
                self.manage_services()
                self.update_all()
            elif choice.lower() == 'q':
                break
            else:
                print("Lựa chọn không hợp lệ")
                time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="Dashboard giám sát hệ thống trading")
    parser.add_argument("--auto-update", action="store_true", help="Tự động cập nhật dashboard mỗi 30 giây")
    
    args = parser.parse_args()
    
    dashboard = Dashboard()
    
    if args.auto_update:
        def update_thread_func():
            while True:
                time.sleep(30)
                dashboard.update_all()
                dashboard.display_dashboard()
        
        update_thread = threading.Thread(target=update_thread_func, daemon=True)
        update_thread.start()
    
    dashboard.run()

if __name__ == "__main__":
    main()