#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Update Client - Tự động cập nhật code từ Replit

Script này tự động tải và áp dụng các bản cập nhật mới từ máy chủ Replit
đến máy tính cục bộ. Hỗ trợ sao lưu tự động, kiểm tra tính toàn vẹn,
và tự động rollback nếu cập nhật thất bại.
"""

import os
import sys
import json
import time
import hashlib
import zipfile
import logging
import argparse
import datetime
import tempfile
import requests
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("auto_update_client.log")
    ]
)
logger = logging.getLogger("auto_update_client")

# Cấu hình mặc định
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "update_server_url": "",
    "auth_token": "",
    "check_interval": 3600,  # Kiểm tra cập nhật mỗi 1 giờ
    "backup_dir": "backups",
    "max_backups": 5,
    "update_history": [],
    "rollback_on_failure": True,
    "failure_timeout": 300,  # 5 phút
    "restart_command": "",
    "last_check_time": 0,
    "auto_update": False
}

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


class AutoUpdateClient:
    """
    Client tự động cập nhật code từ Replit
    """
    
    def __init__(self, config_path: str = "auto_update_config.json"):
        """
        Khởi tạo client
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_or_create_config()
        
        # Đảm bảo các thư mục cần thiết tồn tại
        os.makedirs(self.config["backup_dir"], exist_ok=True)
    
    def _load_or_create_config(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Cấu hình cập nhật
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Cập nhật các key mới nếu có
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.error(f"Lỗi khi đọc file cấu hình: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            # Tạo mới nếu không tồn tại
            config = DEFAULT_CONFIG.copy()
            self._save_config(config)
            return config
    
    def _save_config(self, config: Dict = None) -> bool:
        """
        Lưu cấu hình vào file
        
        Args:
            config (Dict, optional): Cấu hình cần lưu, mặc định là cấu hình hiện tại
            
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu file cấu hình: {e}")
            return False
    
    def setup(self, url: str = None, token: str = None) -> bool:
        """
        Thiết lập cấu hình ban đầu
        
        Args:
            url (str, optional): URL của máy chủ cập nhật
            token (str, optional): Token xác thực
            
        Returns:
            bool: True nếu thiết lập thành công, False nếu không
        """
        # Nếu không cung cấp tham số, yêu cầu nhập từ bàn phím
        if url is None:
            url = input(f"{Colors.CYAN}Nhập URL máy chủ cập nhật (vd: http://example.com/update/api/client/check): {Colors.ENDC}")
        
        if token is None:
            token = input(f"{Colors.CYAN}Nhập token xác thực: {Colors.ENDC}")
        
        # Cập nhật cấu hình
        self.config["update_server_url"] = url
        self.config["auth_token"] = token
        
        # Hỏi về tần suất kiểm tra
        try:
            interval = input(f"{Colors.CYAN}Tần suất kiểm tra cập nhật (giây, mặc định 3600): {Colors.ENDC}")
            if interval.strip():
                self.config["check_interval"] = int(interval)
        except ValueError:
            pass
        
        # Hỏi về tự động cập nhật
        auto_update = input(f"{Colors.CYAN}Tự động cập nhật khi có phiên bản mới? (y/n, mặc định n): {Colors.ENDC}")
        self.config["auto_update"] = auto_update.lower() == 'y'
        
        # Hỏi về lệnh khởi động lại
        restart_command = input(f"{Colors.CYAN}Lệnh khởi động lại sau khi cập nhật (để trống nếu không cần): {Colors.ENDC}")
        self.config["restart_command"] = restart_command
        
        # Lưu cấu hình
        return self._save_config()
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Kiểm tra cập nhật từ máy chủ
        
        Returns:
            Optional[Dict]: Thông tin cập nhật nếu có, None nếu không
        """
        if not self.config["update_server_url"]:
            logger.error("URL máy chủ cập nhật chưa được cấu hình")
            return None
        
        current_version = self.config["version"]
        url = self.config["update_server_url"]
        
        # Thêm tham số phiên bản vào URL
        if "?" in url:
            url += f"&version={current_version}"
        else:
            url += f"?version={current_version}"
        
        # Cập nhật thời gian kiểm tra cuối cùng
        self.config["last_check_time"] = time.time()
        self._save_config()
        
        try:
            # Gửi yêu cầu đến máy chủ
            headers = {
                "X-Auth-Token": self.config["auth_token"],
                "User-Agent": f"AutoUpdateClient/{current_version} ({platform.system()} {platform.release()})"
            }
            
            logger.info(f"Đang kiểm tra cập nhật từ {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data["success"]:
                logger.error(f"Lỗi từ máy chủ: {data.get('message', 'Không xác định')}")
                return None
            
            if data["has_update"]:
                logger.info(f"Phát hiện bản cập nhật mới: {data['update']['version']}")
                return data["update"]
            else:
                logger.info("Bạn đang sử dụng phiên bản mới nhất")
                return None
        
        except requests.RequestException as e:
            logger.error(f"Lỗi khi kết nối đến máy chủ cập nhật: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi khi phân tích phản hồi từ máy chủ: {e}")
            return None
        except Exception as e:
            logger.error(f"Lỗi không xác định khi kiểm tra cập nhật: {e}")
            return None
    
    def create_backup(self, backup_name: str = None) -> Optional[str]:
        """
        Tạo bản sao lưu của hệ thống hiện tại
        
        Args:
            backup_name (str, optional): Tên bản sao lưu, mặc định là timestamp
            
        Returns:
            Optional[str]: Đường dẫn đến file sao lưu hoặc None nếu thất bại
        """
        if backup_name is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        backup_path = os.path.join(self.config["backup_dir"], f"{backup_name}.zip")
        
        try:
            # Tạo file zip
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Bỏ qua các thư mục không cần thiết
                excludes = [
                    "__pycache__", 
                    self.config["backup_dir"],
                    ".git",
                    "venv",
                    "env"
                ]
                
                # Thêm các file vào zip
                for root, dirs, files in os.walk("."):
                    # Bỏ qua các thư mục trong excludes
                    dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Bỏ qua file sao lưu đang tạo
                        if file_path == backup_path:
                            continue
                        # Bỏ qua các file không cần sao lưu
                        if (file.endswith(".pyc") or 
                            file.startswith(".") or 
                            "backup_" in file):
                            continue
                        
                        arcname = os.path.join(root, file)[2:]  # remove ./ from path
                        zipf.write(file_path, arcname)
            
            # Lưu lại thông tin bản sao lưu
            self.config.setdefault("backups", [])
            self.config["backups"].insert(0, {
                "name": backup_name,
                "path": backup_path,
                "timestamp": datetime.datetime.now().timestamp(),
                "version": self.config["version"]
            })
            
            # Giới hạn số lượng bản sao lưu
            if len(self.config["backups"]) > self.config["max_backups"]:
                # Xóa bản sao lưu cũ nhất
                old_backup = self.config["backups"].pop()
                if os.path.exists(old_backup["path"]):
                    os.remove(old_backup["path"])
            
            self._save_config()
            logger.info(f"Đã tạo bản sao lưu thành công: {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo bản sao lưu: {e}")
            return None
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Tính toán hash MD5 của file
        
        Args:
            file_path (str): Đường dẫn đến file
            
        Returns:
            str: Hash MD5 của file
        """
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            # Đọc theo chunk để tiết kiệm bộ nhớ
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def download_update(self, download_url: str, version: str) -> Optional[str]:
        """
        Tải xuống bản cập nhật từ URL
        
        Args:
            download_url (str): URL để tải xuống
            version (str): Phiên bản cần tải xuống
            
        Returns:
            Optional[str]: Đường dẫn đến gói cập nhật đã tải xuống hoặc None nếu thất bại
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        package_name = f"update_package_{version}_{timestamp}.zip"
        package_path = os.path.join(tempfile.gettempdir(), package_name)
        
        try:
            # Tải file
            headers = {
                "X-Auth-Token": self.config["auth_token"],
                "User-Agent": f"AutoUpdateClient/{self.config['version']} ({platform.system()} {platform.release()})"
            }
            
            logger.info(f"Đang tải xuống bản cập nhật từ {download_url}")
            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            # Ghi file
            with open(package_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Kiểm tra tính hợp lệ của gói cập nhật
            if not self._verify_update_package(package_path):
                logger.error(f"Gói cập nhật không hợp lệ: {package_path}")
                os.remove(package_path)
                return None
            
            logger.info(f"Đã tải xuống bản cập nhật thành công: {package_path}")
            return package_path
        
        except Exception as e:
            logger.error(f"Lỗi khi tải xuống bản cập nhật: {e}")
            # Xóa file nếu tải xuống thất bại
            if os.path.exists(package_path):
                os.remove(package_path)
            return None
    
    def _verify_update_package(self, package_path: str) -> bool:
        """
        Kiểm tra tính toàn vẹn của gói cập nhật
        
        Args:
            package_path (str): Đường dẫn đến gói cập nhật
            
        Returns:
            bool: True nếu gói hợp lệ, False nếu không
        """
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Kiểm tra manifest
                if "manifest.json" not in zipf.namelist():
                    logger.error(f"Gói cập nhật không hợp lệ: Không tìm thấy manifest.json")
                    return False
                
                # Đọc manifest
                with zipf.open("manifest.json") as f:
                    manifest = json.load(f)
                
                # Kiểm tra các file trong gói
                for file_path in manifest["files"]:
                    if file_path not in zipf.namelist():
                        logger.error(f"Gói cập nhật không hợp lệ: Thiếu file {file_path}")
                        return False
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra gói cập nhật: {e}")
            return False
    
    def apply_update(self, package_path: str, auto_backup: bool = True) -> bool:
        """
        Áp dụng bản cập nhật từ gói cập nhật
        
        Args:
            package_path (str): Đường dẫn đến gói cập nhật
            auto_backup (bool): Tự động sao lưu trước khi cập nhật
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        # Kiểm tra gói cập nhật
        if not self._verify_update_package(package_path):
            return False
        
        # Đọc manifest
        with zipfile.ZipFile(package_path, 'r') as zipf:
            with zipf.open("manifest.json") as f:
                manifest = json.load(f)
        
        # Tạo bản sao lưu nếu cần
        if auto_backup:
            backup_path = self.create_backup(f"backup_before_{manifest['version']}")
            if not backup_path:
                logger.error("Không thể tạo bản sao lưu, hủy cập nhật")
                return False
        
        try:
            # Giải nén gói cập nhật
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Áp dụng từng file
                for file_path in manifest["files"]:
                    # Tạo thư mục cha nếu cần
                    os.makedirs(os.path.dirname(os.path.join(".", file_path)), exist_ok=True)
                    
                    # Giải nén file
                    zipf.extract(file_path, ".")
                    
                    # Kiểm tra hash của file đã giải nén
                    extracted_hash = self._calculate_file_hash(os.path.join(".", file_path))
                    if extracted_hash != manifest["files"][file_path]["hash"]:
                        raise Exception(f"File {file_path} bị hỏng sau khi giải nén")
            
            # Cập nhật thông tin phiên bản
            self.config["version"] = manifest["version"]
            self.config["last_update_time"] = datetime.datetime.now().timestamp()
            self.config["update_history"].append({
                "version": manifest["version"],
                "timestamp": datetime.datetime.now().timestamp(),
                "changes": manifest.get("changes", [])
            })
            self._save_config()
            
            logger.info(f"Đã áp dụng bản cập nhật thành công: {manifest['version']}")
            
            # Khởi động lại dịch vụ nếu cần
            if self.config.get("restart_command"):
                self._restart_service()
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng bản cập nhật: {e}")
            # Tự động rollback nếu cấu hình cho phép
            if self.config.get("rollback_on_failure", True) and auto_backup:
                logger.info("Đang thực hiện rollback...")
                self.rollback_to_latest_backup()
            return False
    
    def _restart_service(self) -> bool:
        """
        Khởi động lại dịch vụ sau khi cập nhật
        
        Returns:
            bool: True nếu khởi động lại thành công, False nếu không
        """
        try:
            restart_command = self.config.get("restart_command", "")
            if restart_command:
                logger.info(f"Đang khởi động lại dịch vụ: {restart_command}")
                subprocess.run(restart_command, shell=True, check=True)
                return True
            return False
        except Exception as e:
            logger.error(f"Lỗi khi khởi động lại dịch vụ: {e}")
            return False
    
    def rollback_to_latest_backup(self) -> bool:
        """
        Quay về bản sao lưu mới nhất
        
        Returns:
            bool: True nếu rollback thành công, False nếu không
        """
        try:
            if not self.config.get("backups"):
                logger.error("Không có bản sao lưu nào để rollback")
                return False
            
            # Lấy bản sao lưu mới nhất
            latest_backup = self.config["backups"][0]
            backup_path = latest_backup["path"]
            
            if not os.path.exists(backup_path):
                logger.error(f"Không tìm thấy file sao lưu: {backup_path}")
                return False
            
            # Giải nén bản sao lưu
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(".")
            
            # Cập nhật thông tin phiên bản
            self.config["version"] = latest_backup["version"]
            self.config["rollback_time"] = datetime.datetime.now().timestamp()
            self._save_config()
            
            logger.info(f"Đã rollback thành công về phiên bản: {latest_backup['version']}")
            
            # Khởi động lại dịch vụ
            self._restart_service()
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi rollback: {e}")
            return False
    
    def run_check(self, auto_update: bool = None) -> bool:
        """
        Kiểm tra và cập nhật nếu có phiên bản mới
        
        Args:
            auto_update (bool, optional): Tự động cập nhật nếu có phiên bản mới
            
        Returns:
            bool: True nếu kiểm tra thành công, False nếu không
        """
        # Nếu không chỉ định auto_update, sử dụng giá trị từ cấu hình
        if auto_update is None:
            auto_update = self.config.get("auto_update", False)
        
        # Kiểm tra cập nhật
        update_info = self.check_for_updates()
        
        if not update_info:
            return True
        
        logger.info(f"Đã tìm thấy bản cập nhật mới: {update_info['version']}")
        logger.info(f"Mô tả: {update_info['description']}")
        
        # In danh sách thay đổi
        if update_info.get('changes'):
            logger.info("Thay đổi:")
            for change in update_info['changes']:
                logger.info(f"- {change}")
        
        # Nếu không tự động cập nhật, chỉ thông báo và kết thúc
        if not auto_update:
            logger.info(f"Để cập nhật, chạy lại script với tham số --update")
            return True
        
        # Tải xuống bản cập nhật
        package_path = self.download_update(update_info['download_url'], update_info['version'])
        
        if not package_path:
            logger.error("Không thể tải xuống bản cập nhật")
            return False
        
        # Áp dụng bản cập nhật
        success = self.apply_update(package_path, auto_backup=True)
        
        if success:
            logger.info(f"Đã cập nhật thành công lên phiên bản {update_info['version']}")
            
            # Xóa file gói cập nhật tạm thời
            if os.path.exists(package_path):
                os.remove(package_path)
            
            return True
        else:
            logger.error("Không thể áp dụng bản cập nhật")
            return False
    
    def run_auto_check(self) -> None:
        """
        Chạy kiểm tra cập nhật tự động theo lịch trình
        """
        # Kiểm tra xem đã đến lúc kiểm tra cập nhật chưa
        current_time = time.time()
        last_check_time = self.config.get("last_check_time", 0)
        check_interval = self.config.get("check_interval", 3600)
        
        if current_time - last_check_time >= check_interval:
            logger.info("Đang chạy kiểm tra cập nhật tự động...")
            self.run_check(auto_update=self.config.get("auto_update", False))
        else:
            logger.info(f"Kiểm tra cập nhật tiếp theo trong {int(check_interval - (current_time - last_check_time))} giây")


def main():
    """
    Hàm chính của script
    """
    parser = argparse.ArgumentParser(description="Auto Update Client - Tự động cập nhật code từ Replit")
    
    # Các tham số tùy chọn
    parser.add_argument("--setup", action="store_true", help="Thiết lập cấu hình ban đầu")
    parser.add_argument("--url", type=str, help="URL máy chủ cập nhật")
    parser.add_argument("--token", type=str, help="Token xác thực")
    parser.add_argument("--check", action="store_true", help="Kiểm tra cập nhật")
    parser.add_argument("--update", action="store_true", help="Kiểm tra và áp dụng cập nhật")
    parser.add_argument("--auto", action="store_true", help="Chạy kiểm tra cập nhật tự động")
    parser.add_argument("--backup", action="store_true", help="Tạo bản sao lưu")
    parser.add_argument("--rollback", action="store_true", help="Rollback về bản sao lưu mới nhất")
    parser.add_argument("--config", type=str, default="auto_update_config.json", help="Đường dẫn đến file cấu hình")
    
    args = parser.parse_args()
    
    # Khởi tạo client
    client = AutoUpdateClient(args.config)
    
    # Xử lý các tham số
    if args.setup:
        print(f"{Colors.HEADER}=== Thiết lập Auto Update Client ==={Colors.ENDC}")
        if client.setup(args.url, args.token):
            print(f"{Colors.GREEN}Đã thiết lập cấu hình thành công!{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Không thể thiết lập cấu hình!{Colors.ENDC}")
    
    elif args.backup:
        print(f"{Colors.HEADER}=== Tạo bản sao lưu ==={Colors.ENDC}")
        backup_path = client.create_backup()
        if backup_path:
            print(f"{Colors.GREEN}Đã tạo bản sao lưu thành công: {backup_path}{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Không thể tạo bản sao lưu!{Colors.ENDC}")
    
    elif args.rollback:
        print(f"{Colors.HEADER}=== Rollback về bản sao lưu mới nhất ==={Colors.ENDC}")
        if client.rollback_to_latest_backup():
            print(f"{Colors.GREEN}Đã rollback thành công!{Colors.ENDC}")
        else:
            print(f"{Colors.RED}Không thể rollback!{Colors.ENDC}")
    
    elif args.check:
        print(f"{Colors.HEADER}=== Kiểm tra cập nhật ==={Colors.ENDC}")
        client.run_check(auto_update=False)
    
    elif args.update:
        print(f"{Colors.HEADER}=== Kiểm tra và áp dụng cập nhật ==={Colors.ENDC}")
        client.run_check(auto_update=True)
    
    elif args.auto:
        print(f"{Colors.HEADER}=== Chạy kiểm tra cập nhật tự động ==={Colors.ENDC}")
        client.run_auto_check()
    
    else:
        # Chạy kiểm tra tự động nếu không có tham số nào
        print(f"{Colors.HEADER}=== Auto Update Client ==={Colors.ENDC}")
        print(f"{Colors.CYAN}Phiên bản hiện tại: {client.config['version']}{Colors.ENDC}")
        print(f"{Colors.CYAN}URL máy chủ: {client.config['update_server_url'] or 'Chưa thiết lập'}{Colors.ENDC}")
        print()
        print(f"{Colors.YELLOW}Sử dụng tham số --help để xem hướng dẫn sử dụng{Colors.ENDC}")
        client.run_auto_check()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng script")
    except Exception as e:
        logger.exception(f"Lỗi không xử lý được: {e}")
        print(f"{Colors.RED}Đã xảy ra lỗi không xử lý được! Xem file log để biết thêm chi tiết.{Colors.ENDC}")
        sys.exit(1)