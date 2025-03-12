#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Service Guardian
---------------
Trình quản lý trung tâm để điều phối, giám sát và tự động khôi phục các tác vụ hệ thống
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

from telegram_notifier import TelegramNotifier

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('service_guardian.log')
    ]
)

logger = logging.getLogger("service_guardian")

class ServiceGuardian:
    """
    Lớp quản lý trung tâm cho tất cả các dịch vụ của hệ thống
    """
    
    def __init__(self, config_path: str = "configs/service_config.json"):
        """
        Khởi tạo Service Guardian
        
        Args:
            config_path: Đường dẫn tới file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Khởi tạo thông báo
        self.notifier = TelegramNotifier()
        
        # Trạng thái các dịch vụ
        self.services = {}
        self.processes = {}
        self.service_threads = {}
        self.service_status = {}
        self.service_health = {}
        self.service_last_check = {}
        self.recovery_attempts = {}
        
        # Trạng thái guardian
        self.running = False
        self.last_status_report = None
        
        # Khóa đồng bộ
        self.lock = threading.Lock()
        
        logger.info("Service Guardian đã được khởi tạo")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình
        """
        # Nếu không tìm thấy file cấu hình, tạo file cấu hình mặc định
        if not os.path.exists(self.config_path):
            default_config = {
                "services": {
                    "market_analyzer": {
                        "enabled": True,
                        "command": "python activate_market_analyzer.py",
                        "description": "Hệ thống phân tích thị trường và tín hiệu giao dịch",
                        "autostart": True,
                        "auto_restart": True,
                        "check_interval": 60,  # Kiểm tra mỗi 60 giây
                        "restart_delay": 10,   # Chờ 10 giây trước khi khởi động lại
                        "max_restart_attempts": 5,  # Tối đa 5 lần thử khởi động lại
                        "health_check": {
                            "type": "file",
                            "path": "market_analyzer.log",
                            "max_age": 600  # File log không được cũ hơn 10 phút
                        },
                        "dependencies": []
                    },
                    "auto_sltp_manager": {
                        "enabled": True,
                        "command": "python auto_sltp_manager.py",
                        "description": "Quản lý tự động Stop Loss và Take Profit",
                        "autostart": True,
                        "auto_restart": True,
                        "check_interval": 60,
                        "restart_delay": 10,
                        "max_restart_attempts": 5,
                        "health_check": {
                            "type": "file",
                            "path": "auto_sltp_manager.log",
                            "max_age": 600
                        },
                        "dependencies": []
                    },
                    "telegram_bot": {
                        "enabled": True,
                        "command": "python telegram_bot.py",
                        "description": "Bot Telegram để tương tác với hệ thống",
                        "autostart": True,
                        "auto_restart": True,
                        "check_interval": 60,
                        "restart_delay": 10,
                        "max_restart_attempts": 5,
                        "health_check": {
                            "type": "file",
                            "path": "telegram_bot.log",
                            "max_age": 900  # 15 phút
                        },
                        "dependencies": []
                    }
                },
                "system": {
                    "check_interval": 30,  # Kiểm tra trạng thái hệ thống mỗi 30 giây
                    "status_report_interval": 3600,  # Gửi báo cáo trạng thái mỗi 1 giờ
                    "enable_notifications": True,
                    "log_level": "INFO"
                }
            }
            
            # Tạo thư mục chứa file cấu hình nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Lưu cấu hình mặc định
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            logger.info(f"Đã tạo file cấu hình mặc định: {self.config_path}")
            return default_config
        
        # Nếu file cấu hình tồn tại, đọc từ file
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            return {
                "services": {},
                "system": {
                    "check_interval": 30,
                    "status_report_interval": 3600,
                    "enable_notifications": True,
                    "log_level": "INFO"
                }
            }
    
    def _save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
            return False
    
    def _start_service(self, service_name: str) -> bool:
        """
        Khởi động một dịch vụ
        
        Args:
            service_name: Tên dịch vụ cần khởi động
            
        Returns:
            bool: True nếu khởi động thành công, False nếu thất bại
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        service_config = self.config['services'][service_name]
        
        if not service_config.get('enabled', True):
            logger.warning(f"Dịch vụ đã bị tắt: {service_name}")
            return False
        
        if service_name in self.processes and self.processes[service_name].poll() is None:
            logger.warning(f"Dịch vụ đã đang chạy: {service_name}")
            return True
        
        # Kiểm tra các dịch vụ phụ thuộc
        for dependency in service_config.get('dependencies', []):
            if not self._check_service_status(dependency):
                logger.error(f"Dịch vụ phụ thuộc {dependency} chưa chạy, không thể khởi động {service_name}")
                return False
        
        # Khởi động dịch vụ
        try:
            command = service_config['command']
            logger.info(f"Đang khởi động dịch vụ: {service_name} với lệnh: {command}")
            
            # Tạo file log cho dịch vụ
            log_file = open(f"{service_name}.log", "a")
            
            # Khởi động tiến trình
            process = subprocess.Popen(
                command.split(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            
            # Lưu tiến trình
            with self.lock:
                self.processes[service_name] = process
                self.service_status[service_name] = 'STARTING'
                self.recovery_attempts[service_name] = 0
            
            # Ghi lại thời gian khởi động
            logger.info(f"Đã khởi động dịch vụ {service_name}, PID: {process.pid}")
            
            # Chờ một chút để kiểm tra xem dịch vụ có khởi động thành công không
            time.sleep(3)
            
            if process.poll() is None:
                # Tiến trình vẫn đang chạy
                with self.lock:
                    self.service_status[service_name] = 'RUNNING'
                logger.info(f"Dịch vụ {service_name} đã chạy thành công")
                return True
            else:
                # Tiến trình đã kết thúc
                with self.lock:
                    self.service_status[service_name] = 'FAILED'
                logger.error(f"Dịch vụ {service_name} không khởi động được, mã thoát: {process.returncode}")
                return False
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động dịch vụ {service_name}: {e}")
            with self.lock:
                self.service_status[service_name] = 'FAILED'
            return False
    
    def _stop_service(self, service_name: str) -> bool:
        """
        Dừng một dịch vụ
        
        Args:
            service_name: Tên dịch vụ cần dừng
            
        Returns:
            bool: True nếu dừng thành công, False nếu thất bại
        """
        if service_name not in self.processes:
            logger.warning(f"Dịch vụ không đang chạy: {service_name}")
            return True
        
        process = self.processes[service_name]
        
        if process.poll() is not None:
            # Tiến trình đã kết thúc
            logger.info(f"Dịch vụ {service_name} đã dừng")
            with self.lock:
                self.service_status[service_name] = 'STOPPED'
                del self.processes[service_name]
            return True
        
        # Dừng tiến trình
        try:
            logger.info(f"Đang dừng dịch vụ: {service_name}")
            
            # Gửi tín hiệu SIGTERM
            pgid = os.getpgid(process.pid)
            os.killpg(pgid, signal.SIGTERM)
            
            # Chờ tối đa 5 giây cho tiến trình kết thúc
            for _ in range(5):
                if process.poll() is not None:
                    break
                time.sleep(1)
            
            # Nếu tiến trình vẫn chưa kết thúc, gửi SIGKILL
            if process.poll() is None:
                logger.warning(f"Dịch vụ {service_name} không dừng sau SIGTERM, đang gửi SIGKILL")
                os.killpg(pgid, signal.SIGKILL)
                process.wait(2)
            
            logger.info(f"Đã dừng dịch vụ {service_name}")
            
            with self.lock:
                self.service_status[service_name] = 'STOPPED'
                if service_name in self.processes:
                    del self.processes[service_name]
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi dừng dịch vụ {service_name}: {e}")
            return False
    
    def _restart_service(self, service_name: str) -> bool:
        """
        Khởi động lại một dịch vụ
        
        Args:
            service_name: Tên dịch vụ cần khởi động lại
            
        Returns:
            bool: True nếu khởi động lại thành công, False nếu thất bại
        """
        # Dừng dịch vụ
        self._stop_service(service_name)
        
        # Đợi một chút
        time.sleep(self.config['services'][service_name].get('restart_delay', 5))
        
        # Khởi động lại dịch vụ
        return self._start_service(service_name)
    
    def _check_service_health(self, service_name: str) -> bool:
        """
        Kiểm tra sức khỏe của một dịch vụ
        
        Args:
            service_name: Tên dịch vụ cần kiểm tra
            
        Returns:
            bool: True nếu dịch vụ khỏe mạnh, False nếu không
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        if service_name not in self.processes:
            logger.warning(f"Dịch vụ không đang chạy: {service_name}")
            return False
        
        process = self.processes[service_name]
        
        if process.poll() is not None:
            # Tiến trình đã kết thúc
            logger.warning(f"Dịch vụ {service_name} đã dừng, mã thoát: {process.returncode}")
            with self.lock:
                self.service_status[service_name] = 'STOPPED'
            return False
        
        # Kiểm tra sức khỏe theo cấu hình
        health_check = self.config['services'][service_name].get('health_check', {})
        health_type = health_check.get('type', 'process')
        
        if health_type == 'process':
            # Chỉ cần kiểm tra tiến trình có đang chạy
            return True
            
        elif health_type == 'file':
            # Kiểm tra file có tồn tại và không quá cũ
            file_path = health_check.get('path')
            max_age = health_check.get('max_age', 600)  # Mặc định 10 phút
            
            if not file_path or not os.path.exists(file_path):
                logger.warning(f"File kiểm tra sức khỏe không tồn tại: {file_path}")
                return False
            
            # Kiểm tra thời gian sửa đổi file
            file_time = os.path.getmtime(file_path)
            current_time = time.time()
            
            if current_time - file_time > max_age:
                logger.warning(f"File kiểm tra sức khỏe quá cũ: {file_path}, {(current_time - file_time):.0f}s > {max_age}s")
                return False
            
            return True
            
        elif health_type == 'http':
            # Kiểm tra endpoint HTTP
            # (Không triển khai trong phiên bản này)
            logger.warning(f"Kiểm tra sức khỏe HTTP chưa được hỗ trợ")
            return True
            
        else:
            logger.warning(f"Không hỗ trợ loại kiểm tra sức khỏe: {health_type}")
            return True
    
    def _check_service_status(self, service_name: str) -> bool:
        """
        Kiểm tra trạng thái của một dịch vụ
        
        Args:
            service_name: Tên dịch vụ cần kiểm tra
            
        Returns:
            bool: True nếu dịch vụ đang chạy, False nếu không
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        if service_name not in self.processes:
            return False
        
        process = self.processes[service_name]
        
        if process.poll() is not None:
            # Tiến trình đã kết thúc
            with self.lock:
                self.service_status[service_name] = 'STOPPED'
            return False
        
        return True
    
    def _recover_service(self, service_name: str) -> bool:
        """
        Phục hồi một dịch vụ gặp sự cố
        
        Args:
            service_name: Tên dịch vụ cần phục hồi
            
        Returns:
            bool: True nếu phục hồi thành công, False nếu không
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        service_config = self.config['services'][service_name]
        
        if not service_config.get('auto_restart', True):
            logger.info(f"Dịch vụ {service_name} không được cấu hình tự khởi động lại")
            return False
        
        # Kiểm tra số lần thử phục hồi
        max_attempts = service_config.get('max_restart_attempts', 5)
        current_attempts = self.recovery_attempts.get(service_name, 0)
        
        if current_attempts >= max_attempts:
            logger.error(f"Đã vượt quá số lần thử phục hồi tối đa ({max_attempts}) cho dịch vụ {service_name}")
            
            # Gửi thông báo
            if self.config['system'].get('enable_notifications', True):
                self.notifier.send_notification(
                    "error",
                    f"Dịch vụ {service_name} không thể phục hồi sau {max_attempts} lần thử.\n"
                    f"Cần can thiệp thủ công để khắc phục."
                )
            
            return False
        
        # Tăng số lần thử phục hồi
        with self.lock:
            self.recovery_attempts[service_name] = current_attempts + 1
        
        # Thử khởi động lại dịch vụ
        logger.info(f"Đang thử phục hồi dịch vụ {service_name}, lần thử {current_attempts + 1}/{max_attempts}")
        
        success = self._restart_service(service_name)
        
        if success:
            logger.info(f"Đã phục hồi thành công dịch vụ {service_name}")
            
            # Gửi thông báo
            if self.config['system'].get('enable_notifications', True):
                self.notifier.send_notification(
                    "success",
                    f"Dịch vụ {service_name} đã được phục hồi thành công sau {current_attempts + 1} lần thử."
                )
        else:
            logger.error(f"Không thể phục hồi dịch vụ {service_name}")
        
        return success
    
    def _monitor_service(self, service_name: str):
        """
        Giám sát một dịch vụ trong một luồng riêng
        
        Args:
            service_name: Tên dịch vụ cần giám sát
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return
        
        service_config = self.config['services'][service_name]
        check_interval = service_config.get('check_interval', 60)
        
        logger.info(f"Bắt đầu giám sát dịch vụ {service_name}, kiểm tra mỗi {check_interval}s")
        
        while self.running:
            # Kiểm tra trạng thái dịch vụ
            is_running = self._check_service_status(service_name)
            
            if is_running:
                # Kiểm tra sức khỏe dịch vụ
                is_healthy = self._check_service_health(service_name)
                
                with self.lock:
                    self.service_health[service_name] = is_healthy
                    self.service_last_check[service_name] = datetime.now()
                
                if not is_healthy:
                    logger.warning(f"Dịch vụ {service_name} không khỏe mạnh, đang thử phục hồi")
                    self._recover_service(service_name)
            else:
                # Dịch vụ không chạy, thử phục hồi
                with self.lock:
                    self.service_health[service_name] = False
                    self.service_last_check[service_name] = datetime.now()
                
                if service_config.get('auto_restart', True):
                    logger.warning(f"Dịch vụ {service_name} không chạy, đang thử phục hồi")
                    self._recover_service(service_name)
            
            # Đợi đến lần kiểm tra tiếp theo
            time.sleep(check_interval)
    
    def _send_status_report(self):
        """
        Gửi báo cáo trạng thái hệ thống
        """
        if not self.config['system'].get('enable_notifications', True):
            return
        
        # Tạo báo cáo trạng thái
        report = {
            "timestamp": datetime.now().isoformat(),
            "services": {}
        }
        
        for service_name, service_config in self.config['services'].items():
            if not service_config.get('enabled', True):
                continue
            
            is_running = self._check_service_status(service_name)
            is_healthy = self.service_health.get(service_name, False)
            last_check = self.service_last_check.get(service_name)
            
            status = "RUNNING" if is_running else "STOPPED"
            health = "HEALTHY" if is_healthy else "UNHEALTHY"
            
            report['services'][service_name] = {
                "status": status,
                "health": health,
                "last_check": last_check.isoformat() if last_check else None,
                "description": service_config.get('description', '')
            }
        
        # Gửi báo cáo qua Telegram
        try:
            message = "<b>📊 BÁO CÁO TRẠNG THÁI HỆ THỐNG</b>\n\n"
            
            for service_name, service_info in report['services'].items():
                status = service_info['status']
                health = service_info['health']
                description = service_info['description']
                
                status_emoji = "✅" if status == "RUNNING" and health == "HEALTHY" else "⚠️" if status == "RUNNING" else "❌"
                
                message += f"{status_emoji} <b>{service_name}</b>: {status} ({health})\n"
                if description:
                    message += f"   <i>{description}</i>\n"
            
            message += f"\n⏱ <i>Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</i>"
            
            self.notifier.send_message(message)
            logger.info("Đã gửi báo cáo trạng thái hệ thống")
            
            self.last_status_report = datetime.now()
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo trạng thái: {e}")
    
    def start_service(self, service_name: str) -> bool:
        """
        Khởi động một dịch vụ theo yêu cầu của người dùng
        
        Args:
            service_name: Tên dịch vụ cần khởi động
            
        Returns:
            bool: True nếu khởi động thành công, False nếu thất bại
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        return self._start_service(service_name)
    
    def stop_service(self, service_name: str) -> bool:
        """
        Dừng một dịch vụ theo yêu cầu của người dùng
        
        Args:
            service_name: Tên dịch vụ cần dừng
            
        Returns:
            bool: True nếu dừng thành công, False nếu thất bại
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        return self._stop_service(service_name)
    
    def restart_service(self, service_name: str) -> bool:
        """
        Khởi động lại một dịch vụ theo yêu cầu của người dùng
        
        Args:
            service_name: Tên dịch vụ cần khởi động lại
            
        Returns:
            bool: True nếu khởi động lại thành công, False nếu thất bại
        """
        if service_name not in self.config['services']:
            logger.error(f"Dịch vụ không tồn tại: {service_name}")
            return False
        
        return self._restart_service(service_name)
    
    def get_service_status(self, service_name: str = None) -> Dict:
        """
        Lấy trạng thái của một hoặc tất cả các dịch vụ
        
        Args:
            service_name: Tên dịch vụ cần lấy trạng thái, nếu None thì lấy tất cả
            
        Returns:
            Dict: Trạng thái dịch vụ
        """
        result = {}
        
        if service_name:
            if service_name not in self.config['services']:
                logger.error(f"Dịch vụ không tồn tại: {service_name}")
                return {}
            
            is_enabled = self.config['services'][service_name].get('enabled', True)
            is_running = self._check_service_status(service_name)
            is_healthy = self.service_health.get(service_name, False)
            last_check = self.service_last_check.get(service_name)
            
            result[service_name] = {
                "enabled": is_enabled,
                "running": is_running,
                "healthy": is_healthy,
                "status": self.service_status.get(service_name, 'UNKNOWN'),
                "last_check": last_check.isoformat() if last_check else None,
                "description": self.config['services'][service_name].get('description', '')
            }
        else:
            # Lấy trạng thái tất cả các dịch vụ
            for service_name, service_config in self.config['services'].items():
                is_enabled = service_config.get('enabled', True)
                is_running = self._check_service_status(service_name)
                is_healthy = self.service_health.get(service_name, False)
                last_check = self.service_last_check.get(service_name)
                
                result[service_name] = {
                    "enabled": is_enabled,
                    "running": is_running,
                    "healthy": is_healthy,
                    "status": self.service_status.get(service_name, 'UNKNOWN'),
                    "last_check": last_check.isoformat() if last_check else None,
                    "description": service_config.get('description', '')
                }
        
        return result
    
    def start(self):
        """
        Khởi động Service Guardian và tất cả các dịch vụ được cấu hình tự động khởi động
        """
        if self.running:
            logger.warning("Service Guardian đã đang chạy")
            return
        
        self.running = True
        logger.info("Đang khởi động Service Guardian")
        
        # Khởi động các dịch vụ được cấu hình tự động khởi động
        for service_name, service_config in self.config['services'].items():
            if service_config.get('enabled', True) and service_config.get('autostart', True):
                self._start_service(service_name)
        
        # Bắt đầu giám sát các dịch vụ
        for service_name, service_config in self.config['services'].items():
            if service_config.get('enabled', True):
                thread = threading.Thread(
                    target=self._monitor_service,
                    args=(service_name,),
                    daemon=True
                )
                self.service_threads[service_name] = thread
                thread.start()
        
        # Bắt đầu vòng lặp chính
        try:
            check_interval = self.config['system'].get('check_interval', 30)
            status_report_interval = self.config['system'].get('status_report_interval', 3600)
            
            while self.running:
                # Kiểm tra xem có cần gửi báo cáo trạng thái không
                if (self.last_status_report is None or
                    (datetime.now() - self.last_status_report).total_seconds() >= status_report_interval):
                    self._send_status_report()
                
                # Đợi đến lần kiểm tra tiếp theo
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("Đã nhận lệnh dừng từ người dùng")
            self.running = False
        except Exception as e:
            logger.error(f"Lỗi trong vòng lặp chính: {e}")
            self.running = False
        
        # Dừng tất cả các dịch vụ
        self.stop_all()
    
    def stop(self):
        """
        Dừng Service Guardian nhưng giữ các dịch vụ chạy
        """
        if not self.running:
            logger.warning("Service Guardian không đang chạy")
            return
        
        self.running = False
        logger.info("Đang dừng Service Guardian")
    
    def stop_all(self):
        """
        Dừng Service Guardian và tất cả các dịch vụ
        """
        if not self.running:
            logger.warning("Service Guardian không đang chạy")
        
        self.running = False
        logger.info("Đang dừng tất cả các dịch vụ và Service Guardian")
        
        # Dừng tất cả các dịch vụ
        for service_name in list(self.processes.keys()):
            self._stop_service(service_name)

def main():
    """
    Hàm chính
    """
    # Tạo thư mục configs nếu chưa tồn tại
    os.makedirs("configs", exist_ok=True)
    
    # Khởi tạo và khởi động Service Guardian
    guardian = ServiceGuardian()
    
    try:
        guardian.start()
    except KeyboardInterrupt:
        logger.info("Đã nhận lệnh dừng từ người dùng")
        guardian.stop_all()
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {e}")
        guardian.stop_all()

if __name__ == "__main__":
    main()