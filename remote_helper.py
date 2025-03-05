#!/usr/bin/env python3
"""
Remote Helper - Công cụ hỗ trợ kết nối và điều khiển bot từ xa

Script này cung cấp các công cụ để kết nối và điều khiển bot từ xa, cho phép 
giám sát và sửa chữa mà không cần truy cập trực tiếp vào máy chủ.
"""

import os
import sys
import json
import time
import socket
import argparse
import logging
import requests
import subprocess
import platform
import shutil
import tempfile
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("remote_helper.log"),
        logging.StreamHandler()
    ]
)

# Cấu hình mặc định
DEFAULT_CONFIG = {
    "connect_url": "https://your-connection-service.com/api/connect",
    "auth_token": "your_auth_token_here",
    "client_id": "bot_client_" + socket.gethostname(),
    "authorized_keys": [],
    "log_files": ["*.log", "auto_recovery.log", "watchdog.log", "telegram_watchdog.log"],
    "config_files": ["*.json", "*.env"],
    "code_files": ["*.py", "*.sh"],
    "ping_interval": 60,
    "auto_update": True,
    "auto_restart": True
}

# Các màu cho terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class RemoteHelper:
    """Lớp chính xử lý kết nối và điều khiển từ xa"""
    
    def __init__(self, config_path: str = "remote_helper_config.json"):
        """
        Khởi tạo Remote Helper
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_or_create_config()
        self.connected = False
        self.connection_id = None
        self.last_ping_time = 0
        self.commands_queue = []
        self.updates_available = False
        
        logging.info("Remote Helper đã khởi động")
    
    def _load_or_create_config(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo mới
        
        Returns:
            Dict: Cấu hình
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Cập nhật các key mặc định nếu thiếu
                    for key, value in DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                logging.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logging.error(f"Lỗi khi tải cấu hình: {str(e)}")
        
        # Tạo cấu hình mặc định
        logging.info(f"Tạo cấu hình mặc định tại {self.config_path}")
        with open(self.config_path, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        
        return DEFAULT_CONFIG
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logging.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logging.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            return False
    
    def connect(self) -> bool:
        """
        Kết nối đến dịch vụ từ xa
        
        Returns:
            bool: True nếu kết nối thành công, False nếu không
        """
        try:
            # Thu thập thông tin hệ thống
            system_info = self._collect_system_info()
            
            # Dữ liệu kết nối
            connect_data = {
                "client_id": self.config["client_id"],
                "auth_token": self.config["auth_token"],
                "system_info": system_info,
                "timestamp": datetime.now().isoformat()
            }
            
            # Gửi yêu cầu kết nối
            logging.info(f"Đang kết nối đến {self.config['connect_url']}...")
            response = requests.post(
                self.config["connect_url"],
                json=connect_data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    self.connected = True
                    self.connection_id = response_data.get("connection_id")
                    self.last_ping_time = time.time()
                    
                    # Kiểm tra cập nhật
                    if response_data.get("updates_available", False):
                        self.updates_available = True
                        logging.info("Có các cập nhật khả dụng từ máy chủ")
                    
                    logging.info(f"Kết nối thành công! ID: {self.connection_id}")
                    print(f"{Colors.GREEN}✓ Kết nối thành công! ID: {self.connection_id}{Colors.ENDC}")
                    return True
                else:
                    logging.error(f"Kết nối thất bại: {response_data.get('message', 'Không rõ lỗi')}")
                    print(f"{Colors.RED}✗ Kết nối thất bại: {response_data.get('message', 'Không rõ lỗi')}{Colors.ENDC}")
            else:
                logging.error(f"Kết nối thất bại với mã lỗi HTTP: {response.status_code}")
                print(f"{Colors.RED}✗ Kết nối thất bại với mã lỗi HTTP: {response.status_code}{Colors.ENDC}")
            
            return False
        
        except Exception as e:
            logging.error(f"Lỗi khi kết nối: {str(e)}")
            logging.error(traceback.format_exc())
            print(f"{Colors.RED}✗ Lỗi khi kết nối: {str(e)}{Colors.ENDC}")
            return False
    
    def _collect_system_info(self) -> Dict:
        """
        Thu thập thông tin hệ thống
        
        Returns:
            Dict: Thông tin hệ thống
        """
        system_info = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "cpu_count": os.cpu_count(),
            "python_version": platform.python_version(),
            "timestamp": datetime.now().isoformat(),
            "bot_version": self._get_bot_version(),
            "active_processes": self._get_active_processes(),
            "disk_usage": self._get_disk_usage(),
            "memory_usage": self._get_memory_usage()
        }
        
        return system_info
    
    def _get_bot_version(self) -> str:
        """
        Lấy phiên bản của bot
        
        Returns:
            str: Phiên bản bot
        """
        bot_status_file = "bot_status.json"
        if os.path.exists(bot_status_file):
            try:
                with open(bot_status_file, 'r') as f:
                    bot_status = json.load(f)
                return bot_status.get("version", "unknown")
            except Exception:
                pass
        return "unknown"
    
    def _get_active_processes(self) -> List[str]:
        """
        Lấy danh sách các tiến trình đang chạy
        
        Returns:
            List[str]: Danh sách các tiến trình
        """
        processes = []
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output("tasklist", shell=True).decode("utf-8")
            else:
                output = subprocess.check_output("ps aux", shell=True).decode("utf-8")
            
            # Lọc các tiến trình liên quan đến bot
            for line in output.split('\n'):
                if any(keyword in line for keyword in ["python", "bot", "crypto", "watchdog", "gunicorn"]):
                    processes.append(line.strip())
        except Exception as e:
            logging.error(f"Lỗi khi lấy danh sách tiến trình: {str(e)}")
        
        return processes
    
    def _get_disk_usage(self) -> Dict:
        """
        Lấy thông tin sử dụng ổ đĩa
        
        Returns:
            Dict: Thông tin sử dụng ổ đĩa
        """
        try:
            total, used, free = shutil.disk_usage("/")
            return {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round((used / total) * 100, 2)
            }
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin ổ đĩa: {str(e)}")
            return {"error": str(e)}
    
    def _get_memory_usage(self) -> Dict:
        """
        Lấy thông tin sử dụng bộ nhớ
        
        Returns:
            Dict: Thông tin sử dụng bộ nhớ
        """
        try:
            if platform.system() == "Windows":
                # Trên Windows, chúng ta sử dụng wmic
                output = subprocess.check_output(
                    "wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value", 
                    shell=True
                ).decode("utf-8")
                
                total_mem = 0
                free_mem = 0
                
                for line in output.split('\n'):
                    if "=" in line:
                        key, value = line.split('=', 1)
                        if key.strip() == "TotalVisibleMemorySize":
                            total_mem = int(value.strip()) / 1024  # Chuyển về MB
                        elif key.strip() == "FreePhysicalMemory":
                            free_mem = int(value.strip()) / 1024  # Chuyển về MB
            else:
                # Trên Linux, chúng ta sử dụng /proc/meminfo
                with open('/proc/meminfo', 'r') as f:
                    mem_info = f.read()
                
                total_mem = 0
                free_mem = 0
                
                for line in mem_info.split('\n'):
                    if "MemTotal" in line:
                        total_mem = int(line.split()[1]) / 1024  # Chuyển về MB
                    elif "MemAvailable" in line or "MemFree" in line and free_mem == 0:
                        free_mem = int(line.split()[1]) / 1024  # Chuyển về MB
            
            used_mem = total_mem - free_mem
            
            return {
                "total_mb": round(total_mem, 2),
                "used_mb": round(used_mem, 2),
                "free_mb": round(free_mem, 2),
                "percent_used": round((used_mem / total_mem) * 100, 2) if total_mem > 0 else 0
            }
        except Exception as e:
            logging.error(f"Lỗi khi lấy thông tin bộ nhớ: {str(e)}")
            return {"error": str(e)}
    
    def ping(self) -> bool:
        """
        Gửi ping để duy trì kết nối
        
        Returns:
            bool: True nếu ping thành công, False nếu không
        """
        if not self.connected or not self.connection_id:
            logging.warning("Không thể ping vì chưa kết nối")
            return False
        
        try:
            # Thu thập thông tin hiện tại
            system_info = self._collect_system_info()
            
            # Dữ liệu ping
            ping_data = {
                "connection_id": self.connection_id,
                "client_id": self.config["client_id"],
                "auth_token": self.config["auth_token"],
                "system_info": system_info,
                "timestamp": datetime.now().isoformat()
            }
            
            # Gửi ping
            ping_url = self.config["connect_url"].replace("/connect", "/ping")
            response = requests.post(
                ping_url,
                json=ping_data,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    self.last_ping_time = time.time()
                    
                    # Kiểm tra xem có lệnh mới không
                    new_commands = response_data.get("commands", [])
                    if new_commands:
                        self.commands_queue.extend(new_commands)
                        logging.info(f"Nhận được {len(new_commands)} lệnh mới")
                    
                    # Kiểm tra cập nhật
                    if response_data.get("updates_available", False):
                        self.updates_available = True
                        logging.info("Có các cập nhật khả dụng từ máy chủ")
                    
                    return True
                else:
                    logging.warning(f"Ping thất bại: {response_data.get('message', 'Không rõ lỗi')}")
            else:
                logging.warning(f"Ping thất bại với mã lỗi HTTP: {response.status_code}")
            
            return False
        
        except Exception as e:
            logging.error(f"Lỗi khi ping: {str(e)}")
            return False
    
    def process_commands(self) -> None:
        """Xử lý các lệnh trong hàng đợi"""
        if not self.commands_queue:
            return
        
        logging.info(f"Xử lý {len(self.commands_queue)} lệnh")
        
        while self.commands_queue:
            command = self.commands_queue.pop(0)
            cmd_type = command.get("type")
            cmd_payload = command.get("payload", {})
            
            logging.info(f"Xử lý lệnh: {cmd_type}")
            
            try:
                if cmd_type == "restart_bot":
                    self._handle_restart_bot(cmd_payload)
                elif cmd_type == "update_config":
                    self._handle_update_config(cmd_payload)
                elif cmd_type == "update_code":
                    self._handle_update_code(cmd_payload)
                elif cmd_type == "execute_shell":
                    self._handle_execute_shell(cmd_payload)
                elif cmd_type == "collect_logs":
                    self._handle_collect_logs(cmd_payload)
                else:
                    logging.warning(f"Loại lệnh không hỗ trợ: {cmd_type}")
            except Exception as e:
                logging.error(f"Lỗi khi xử lý lệnh {cmd_type}: {str(e)}")
                logging.error(traceback.format_exc())
    
    def _handle_restart_bot(self, payload: Dict) -> None:
        """
        Xử lý lệnh khởi động lại bot
        
        Args:
            payload (Dict): Dữ liệu lệnh
        """
        logging.info("Đang khởi động lại bot...")
        
        restart_script = payload.get("script", "watchdog_runner.sh")
        
        try:
            # Dừng các tiến trình hiện tại
            if platform.system() == "Windows":
                os.system("taskkill /f /im python.exe")
                os.system("taskkill /f /im gunicorn.exe")
            else:
                os.system("pkill -f python")
                os.system("pkill -f gunicorn")
            
            # Chờ một chút
            time.sleep(2)
            
            # Khởi động lại
            if os.path.exists(restart_script):
                if platform.system() == "Windows":
                    subprocess.Popen(f"start {restart_script}", shell=True)
                else:
                    subprocess.Popen(f"./{restart_script} &", shell=True)
                logging.info(f"Đã khởi động lại bot với script {restart_script}")
            else:
                logging.error(f"Không tìm thấy script khởi động {restart_script}")
        except Exception as e:
            logging.error(f"Lỗi khi khởi động lại bot: {str(e)}")
    
    def _handle_update_config(self, payload: Dict) -> None:
        """
        Xử lý lệnh cập nhật cấu hình
        
        Args:
            payload (Dict): Dữ liệu lệnh
        """
        config_file = payload.get("file", "bot_config.json")
        config_data = payload.get("data")
        
        if not config_data:
            logging.warning("Không có dữ liệu cấu hình để cập nhật")
            return
        
        logging.info(f"Đang cập nhật cấu hình {config_file}...")
        
        try:
            # Sao lưu file cấu hình cũ
            if os.path.exists(config_file):
                backup_file = f"{config_file}.bak.{int(time.time())}"
                shutil.copy2(config_file, backup_file)
                logging.info(f"Đã sao lưu cấu hình cũ vào {backup_file}")
            
            # Ghi cấu hình mới
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            logging.info(f"Đã cập nhật cấu hình {config_file}")
        except Exception as e:
            logging.error(f"Lỗi khi cập nhật cấu hình: {str(e)}")
    
    def _handle_update_code(self, payload: Dict) -> None:
        """
        Xử lý lệnh cập nhật mã nguồn
        
        Args:
            payload (Dict): Dữ liệu lệnh
        """
        file_path = payload.get("file")
        file_content = payload.get("content")
        
        if not file_path or file_content is None:
            logging.warning("Thiếu thông tin để cập nhật mã nguồn")
            return
        
        logging.info(f"Đang cập nhật mã nguồn {file_path}...")
        
        try:
            # Sao lưu file cũ
            if os.path.exists(file_path):
                backup_file = f"{file_path}.bak.{int(time.time())}"
                shutil.copy2(file_path, backup_file)
                logging.info(f"Đã sao lưu mã nguồn cũ vào {backup_file}")
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Ghi mã nguồn mới
            with open(file_path, 'w') as f:
                f.write(file_content)
            
            # Cấp quyền thực thi nếu là script
            if file_path.endswith(".sh") or file_path.endswith(".py"):
                os.chmod(file_path, 0o755)
            
            logging.info(f"Đã cập nhật mã nguồn {file_path}")
        except Exception as e:
            logging.error(f"Lỗi khi cập nhật mã nguồn: {str(e)}")
    
    def _handle_execute_shell(self, payload: Dict) -> None:
        """
        Xử lý lệnh thực thi shell
        
        Args:
            payload (Dict): Dữ liệu lệnh
        """
        command = payload.get("command")
        
        if not command:
            logging.warning("Không có lệnh shell để thực thi")
            return
        
        logging.info(f"Đang thực thi lệnh shell: {command}")
        
        try:
            # Thực thi lệnh và lấy kết quả
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
            
            logging.info(f"Kết quả lệnh shell: {result[:100]}{'...' if len(result) > 100 else ''}")
            
            # Gửi kết quả về máy chủ
            self._send_command_result({
                "type": "shell_result",
                "command": command,
                "result": result,
                "success": True
            })
        except subprocess.CalledProcessError as e:
            error_message = e.output.decode("utf-8") if e.output else str(e)
            logging.error(f"Lỗi khi thực thi lệnh shell: {error_message}")
            
            # Gửi thông báo lỗi về máy chủ
            self._send_command_result({
                "type": "shell_result",
                "command": command,
                "result": error_message,
                "success": False
            })
    
    def _handle_collect_logs(self, payload: Dict) -> None:
        """
        Xử lý lệnh thu thập logs
        
        Args:
            payload (Dict): Dữ liệu lệnh
        """
        log_files = payload.get("files", self.config["log_files"])
        max_lines = payload.get("max_lines", 1000)
        
        logging.info(f"Đang thu thập logs từ {len(log_files)} file...")
        
        collected_logs = {}
        
        for log_pattern in log_files:
            for log_file in glob.glob(log_pattern):
                if os.path.isfile(log_file):
                    try:
                        with open(log_file, 'r') as f:
                            # Đọc các dòng cuối cùng
                            lines = f.readlines()
                            if len(lines) > max_lines:
                                lines = lines[-max_lines:]
                            
                            collected_logs[log_file] = "".join(lines)
                        
                        logging.info(f"Đã thu thập {len(lines)} dòng từ {log_file}")
                    except Exception as e:
                        logging.error(f"Lỗi khi đọc file log {log_file}: {str(e)}")
                        collected_logs[log_file] = f"ERROR: {str(e)}"
        
        # Gửi logs về máy chủ
        self._send_command_result({
            "type": "logs_collected",
            "logs": collected_logs
        })
    
    def _send_command_result(self, result: Dict) -> bool:
        """
        Gửi kết quả lệnh về máy chủ
        
        Args:
            result (Dict): Kết quả lệnh
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.connected or not self.connection_id:
            logging.warning("Không thể gửi kết quả vì chưa kết nối")
            return False
        
        try:
            # Dữ liệu kết quả
            result_data = {
                "connection_id": self.connection_id,
                "client_id": self.config["client_id"],
                "auth_token": self.config["auth_token"],
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            # Gửi kết quả
            result_url = self.config["connect_url"].replace("/connect", "/command_result")
            response = requests.post(
                result_url,
                json=result_data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success":
                    logging.info("Đã gửi kết quả lệnh thành công")
                    return True
                else:
                    logging.warning(f"Gửi kết quả lệnh thất bại: {response_data.get('message', 'Không rõ lỗi')}")
            else:
                logging.warning(f"Gửi kết quả lệnh thất bại với mã lỗi HTTP: {response.status_code}")
            
            return False
        
        except Exception as e:
            logging.error(f"Lỗi khi gửi kết quả lệnh: {str(e)}")
            return False
    
    def check_for_updates(self) -> bool:
        """
        Kiểm tra cập nhật từ máy chủ
        
        Returns:
            bool: True nếu có cập nhật, False nếu không
        """
        if not self.connected:
            return False
        
        if not self.updates_available:
            return False
        
        try:
            # Gửi yêu cầu kiểm tra cập nhật
            update_url = self.config["connect_url"].replace("/connect", "/check_updates")
            response = requests.post(
                update_url,
                json={
                    "connection_id": self.connection_id,
                    "client_id": self.config["client_id"],
                    "auth_token": self.config["auth_token"],
                    "current_version": self._get_bot_version(),
                    "timestamp": datetime.now().isoformat()
                },
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "success" and response_data.get("updates"):
                    logging.info("Đã tìm thấy cập nhật mới")
                    
                    # Xử lý cập nhật
                    updates = response_data.get("updates", [])
                    self._process_updates(updates)
                    
                    # Đặt lại trạng thái cập nhật
                    self.updates_available = False
                    
                    return True
                else:
                    logging.info("Không có cập nhật mới")
                    self.updates_available = False
            else:
                logging.warning(f"Kiểm tra cập nhật thất bại với mã lỗi HTTP: {response.status_code}")
            
            return False
        
        except Exception as e:
            logging.error(f"Lỗi khi kiểm tra cập nhật: {str(e)}")
            return False
    
    def _process_updates(self, updates: List[Dict]) -> None:
        """
        Xử lý các cập nhật từ máy chủ
        
        Args:
            updates (List[Dict]): Danh sách các cập nhật
        """
        logging.info(f"Đang xử lý {len(updates)} cập nhật...")
        
        for update in updates:
            update_type = update.get("type")
            update_data = update.get("data", {})
            
            logging.info(f"Đang xử lý cập nhật: {update_type}")
            
            try:
                if update_type == "config_update":
                    self._handle_update_config(update_data)
                elif update_type == "code_update":
                    self._handle_update_code(update_data)
                else:
                    logging.warning(f"Loại cập nhật không hỗ trợ: {update_type}")
            except Exception as e:
                logging.error(f"Lỗi khi xử lý cập nhật {update_type}: {str(e)}")
        
        # Khởi động lại bot nếu được cấu hình
        if self.config.get("auto_restart", True):
            logging.info("Đang khởi động lại bot sau khi cập nhật...")
            self._handle_restart_bot({"script": "watchdog_runner.sh"})
    
    def run(self) -> None:
        """Chạy vòng lặp chính của Remote Helper"""
        # Kết nối ban đầu
        if not self.connect():
            print(f"{Colors.YELLOW}Không thể kết nối. Remote Helper sẽ tiếp tục chạy và thử kết nối lại sau...{Colors.ENDC}")
        
        ping_interval = self.config.get("ping_interval", 60)
        update_check_interval = 3600  # 1 giờ
        last_update_check = time.time()
        
        try:
            while True:
                current_time = time.time()
                
                # Xử lý lệnh trong hàng đợi
                self.process_commands()
                
                # Ping nếu đã kết nối và đến thời gian ping
                if self.connected and current_time - self.last_ping_time >= ping_interval:
                    if not self.ping():
                        logging.warning("Ping thất bại, cố gắng kết nối lại...")
                        self.connected = False
                        self.connection_id = None
                        if self.connect():
                            logging.info("Đã kết nối lại thành công")
                
                # Thử kết nối lại nếu chưa kết nối
                if not self.connected and current_time - self.last_ping_time >= ping_interval:
                    if self.connect():
                        logging.info("Đã kết nối thành công")
                
                # Kiểm tra cập nhật định kỳ
                if self.connected and current_time - last_update_check >= update_check_interval:
                    self.check_for_updates()
                    last_update_check = current_time
                
                # Kiểm tra nếu đã bật cờ updates_available
                if self.connected and self.updates_available:
                    self.check_for_updates()
                
                # Ngủ một chút để tránh sử dụng quá nhiều CPU
                time.sleep(5)
                
        except KeyboardInterrupt:
            logging.info("Remote Helper đã dừng bởi người dùng")
            print(f"\n{Colors.YELLOW}Remote Helper đã dừng bởi người dùng{Colors.ENDC}")
        except Exception as e:
            logging.error(f"Lỗi không mong đợi: {str(e)}")
            logging.error(traceback.format_exc())
            print(f"\n{Colors.RED}Lỗi không mong đợi: {str(e)}{Colors.ENDC}")

def setup_remote_connection(config_path: str = "remote_helper_config.json") -> None:
    """
    Thiết lập kết nối từ xa mới
    
    Args:
        config_path (str): Đường dẫn đến file cấu hình
    """
    print(f"{Colors.HEADER}===== Thiết lập Remote Helper =====\n{Colors.ENDC}")
    
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception:
            config = DEFAULT_CONFIG
    else:
        config = DEFAULT_CONFIG
    
    print(f"{Colors.CYAN}Vui lòng cung cấp các thông tin sau để thiết lập kết nối từ xa:{Colors.ENDC}")
    
    # Nhập URL kết nối
    default_url = config.get("connect_url", DEFAULT_CONFIG["connect_url"])
    connect_url = input(f"URL kết nối [{default_url}]: ").strip()
    if not connect_url:
        connect_url = default_url
    
    # Nhập token xác thực
    default_token = config.get("auth_token", DEFAULT_CONFIG["auth_token"])
    auth_token = input(f"Token xác thực [{'*' * len(default_token)}]: ").strip()
    if not auth_token:
        auth_token = default_token
    
    # Nhập ID client
    default_client_id = config.get("client_id", DEFAULT_CONFIG["client_id"])
    client_id = input(f"ID client [{default_client_id}]: ").strip()
    if not client_id:
        client_id = default_client_id
    
    # Cập nhật cấu hình
    config["connect_url"] = connect_url
    config["auth_token"] = auth_token
    config["client_id"] = client_id
    
    # Lưu cấu hình
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\n{Colors.GREEN}✓ Đã lưu cấu hình vào {config_path}{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}✗ Lỗi khi lưu cấu hình: {str(e)}{Colors.ENDC}")
    
    print(f"\n{Colors.CYAN}Để kết nối từ xa, hãy chạy: python3 remote_helper.py{Colors.ENDC}")

def main():
    """Hàm chính của script"""
    parser = argparse.ArgumentParser(description="Remote Helper - Công cụ hỗ trợ kết nối và điều khiển bot từ xa")
    parser.add_argument("--setup", action="store_true", help="Thiết lập kết nối từ xa mới")
    parser.add_argument("--config", type=str, default="remote_helper_config.json", help="Đường dẫn đến file cấu hình")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_remote_connection(args.config)
    else:
        helper = RemoteHelper(args.config)
        helper.run()

if __name__ == "__main__":
    main()