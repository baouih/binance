#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update Bot Module - Cập nhật hệ thống bot giao dịch
"""

import os
import sys
import json
import time
import shutil
import logging
import requests
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot_update.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot_updater')

class BotUpdater:
    """Lớp cập nhật bot"""
    
    def __init__(self, update_url=None, version_file="version.json"):
        """
        Khởi tạo updater
        
        Args:
            update_url (str, optional): URL để kiểm tra cập nhật. Mặc định là None.
            version_file (str, optional): File lưu thông tin phiên bản. Mặc định là "version.json".
        """
        self.update_url = update_url or "https://api.example.com/trading-bot/updates"
        self.version_file = version_file
        self.backup_dir = "backups"
        
        # Đảm bảo thư mục backup tồn tại
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Tạo file phiên bản nếu chưa tồn tại
        if not os.path.exists(version_file):
            self._create_version_file()
    
    def _create_version_file(self):
        """Tạo file phiên bản mặc định"""
        try:
            version_info = {
                "version": "1.0.0",
                "build_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_update": None,
                "components": {
                    "core": "1.0.0",
                    "gui": "1.0.0",
                    "risk_manager": "1.0.0",
                    "strategy": "1.0.0"
                }
            }
            
            with open(self.version_file, 'w') as f:
                json.dump(version_info, f, indent=4)
            
            logger.info(f"Đã tạo file phiên bản tại {self.version_file}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo file phiên bản: {str(e)}")
    
    def get_current_version(self):
        """
        Lấy phiên bản hiện tại của bot
        
        Returns:
            str: Phiên bản hiện tại
        """
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r') as f:
                    version_info = json.load(f)
                return version_info.get("version", "1.0.0")
            else:
                return "1.0.0"
        except Exception as e:
            logger.error(f"Lỗi khi đọc phiên bản hiện tại: {str(e)}")
            return "1.0.0"
    
    def get_latest_version(self):
        """
        Kiểm tra phiên bản mới nhất từ server
        
        Returns:
            str: Phiên bản mới nhất
        """
        try:
            # Thử gọi API để lấy thông tin phiên bản mới nhất
            # Trong môi trường thực tế, bạn sẽ gọi API thực sự
            # Ở đây chúng ta mô phỏng một phiên bản mới hơn
            current_version = self.get_current_version()
            
            # Giả lập phiên bản mới hơn để demo
            major, minor, patch = current_version.split('.')
            new_patch = str(int(patch) + 1)
            latest_version = f"{major}.{minor}.{new_patch}"
            
            logger.info(f"Phiên bản hiện tại: {current_version}, phiên bản mới nhất: {latest_version}")
            return latest_version
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra phiên bản mới nhất: {str(e)}")
            return self.get_current_version()
    
    def needs_update(self):
        """
        Kiểm tra xem có cần cập nhật không
        
        Returns:
            bool: True nếu cần cập nhật, False nếu không
        """
        current_version = self.get_current_version()
        latest_version = self.get_latest_version()
        
        # Chuyển đổi phiên bản thành tuple để so sánh
        current_parts = tuple(map(int, current_version.split('.')))
        latest_parts = tuple(map(int, latest_version.split('.')))
        
        # So sánh phiên bản
        return latest_parts > current_parts
    
    def _create_backup(self):
        """
        Tạo bản sao lưu trước khi cập nhật
        
        Returns:
            str: Đường dẫn đến thư mục backup, hoặc None nếu có lỗi
        """
        try:
            backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{backup_timestamp}")
            
            os.makedirs(backup_path, exist_ok=True)
            
            # Danh sách các file và thư mục cần sao lưu
            items_to_backup = [
                "account_config.json",
                "risk_level_manager.py",
                "bot_gui.py",
                "main.py",
                "feature_fusion_pipeline.py",
                "bot_startup.py",
                "build_executable.py",
                "risk_configs",
                "strategies",
                "ml_models",
                "app.py",
                "templates",
                "static"
            ]
            
            for item in items_to_backup:
                src_path = os.path.join(".", item)
                dst_path = os.path.join(backup_path, item)
                
                if os.path.exists(src_path):
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            
            logger.info(f"Đã tạo bản sao lưu tại {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo bản sao lưu: {str(e)}")
            return None
    
    def _download_update(self, latest_version):
        """
        Tải bản cập nhật từ server
        
        Args:
            latest_version (str): Phiên bản mới nhất
            
        Returns:
            str: Đường dẫn đến file cập nhật, hoặc None nếu có lỗi
        """
        try:
            # Trong môi trường thực tế, bạn sẽ tải từ URL thực sự
            # Ở đây chúng ta mô phỏng quá trình cập nhật bằng cách tạo các file mới cục bộ
            
            update_dir = "update_packages/temp"
            os.makedirs(update_dir, exist_ok=True)
            
            # Mô phỏng tạo file cập nhật
            update_file = os.path.join(update_dir, f"update_{latest_version}.zip")
            
            # Trong thực tế, bạn sẽ tải file từ server
            # urllib.request.urlretrieve(f"{self.update_url}/v{latest_version}", update_file)
            
            # Mô phỏng tạo file cập nhật bằng cách tạo file rỗng
            with open(update_file, 'w') as f:
                f.write(f"Mô phỏng cập nhật phiên bản {latest_version}")
            
            logger.info(f"Đã tải bản cập nhật phiên bản {latest_version} tại {update_file}")
            return update_file
        except Exception as e:
            logger.error(f"Lỗi khi tải bản cập nhật: {str(e)}")
            return None
    
    def _apply_update(self, update_file, latest_version):
        """
        Áp dụng bản cập nhật
        
        Args:
            update_file (str): Đường dẫn đến file cập nhật
            latest_version (str): Phiên bản mới nhất
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu có lỗi
        """
        try:
            # Trong môi trường thực tế, bạn sẽ giải nén và cài đặt các file cập nhật
            # Ở đây chúng ta mô phỏng quá trình cập nhật bằng cách cập nhật version.json
            
            # Cập nhật file phiên bản
            version_info = {
                "version": latest_version,
                "build_date": "2025-03-10 00:00:00",  # Giả lập thời gian build
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "components": {
                    "core": latest_version,
                    "gui": latest_version,
                    "risk_manager": latest_version,
                    "strategy": latest_version
                }
            }
            
            with open(self.version_file, 'w') as f:
                json.dump(version_info, f, indent=4)
            
            logger.info(f"Đã cập nhật thành công lên phiên bản {latest_version}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng bản cập nhật: {str(e)}")
            return False
    
    def _restore_backup(self, backup_path):
        """
        Khôi phục từ bản sao lưu nếu cập nhật thất bại
        
        Args:
            backup_path (str): Đường dẫn đến thư mục backup
            
        Returns:
            bool: True nếu khôi phục thành công, False nếu có lỗi
        """
        try:
            # Khôi phục từ bản sao lưu
            # Trong thực tế, bạn sẽ sao chép lại các file từ backup
            logger.info(f"Khôi phục từ bản sao lưu {backup_path}")
            
            # Danh sách các file và thư mục cần khôi phục
            items_to_restore = [
                "account_config.json",
                "risk_level_manager.py",
                "bot_gui.py",
                "main.py",
                "feature_fusion_pipeline.py",
                "bot_startup.py",
                "build_executable.py",
                "risk_configs",
                "strategies",
                "ml_models",
                "app.py",
                "templates",
                "static"
            ]
            
            for item in items_to_restore:
                src_path = os.path.join(backup_path, item)
                dst_path = os.path.join(".", item)
                
                if os.path.exists(src_path):
                    # Xóa đích trước khi khôi phục
                    if os.path.exists(dst_path):
                        if os.path.isdir(dst_path):
                            shutil.rmtree(dst_path)
                        else:
                            os.remove(dst_path)
                    
                    # Khôi phục từ backup
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            
            logger.info("Đã khôi phục thành công từ bản sao lưu")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi khôi phục từ bản sao lưu: {str(e)}")
            return False
    
    def _verify_update(self, latest_version):
        """
        Kiểm tra tính hợp lệ của bản cập nhật
        
        Args:
            latest_version (str): Phiên bản mới nhất
            
        Returns:
            bool: True nếu cập nhật hợp lệ, False nếu không
        """
        try:
            # Kiểm tra xem các file và thư mục quan trọng có tồn tại không
            essential_items = [
                "bot_gui.py",
                "risk_level_manager.py",
                "bot_startup.py",
                "main.py",
                "risk_configs",
                "strategies"
            ]
            
            for item in essential_items:
                if not os.path.exists(item):
                    logger.error(f"File/thư mục thiết yếu {item} không tồn tại sau khi cập nhật")
                    return False
            
            # Kiểm tra phiên bản
            current_version = self.get_current_version()
            if current_version != latest_version:
                logger.error(f"Phiên bản sau khi cập nhật ({current_version}) không khớp với phiên bản mới nhất ({latest_version})")
                return False
            
            logger.info("Kiểm tra bản cập nhật thành công")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra bản cập nhật: {str(e)}")
            return False
    
    def update(self):
        """
        Cập nhật bot lên phiên bản mới nhất
        
        Returns:
            bool: True nếu cập nhật thành công, False nếu có lỗi hoặc không cần cập nhật
        """
        try:
            # Kiểm tra xem có cần cập nhật không
            if not self.needs_update():
                logger.info("Bot đã ở phiên bản mới nhất, không cần cập nhật")
                return False
            
            # Lấy phiên bản mới nhất
            latest_version = self.get_latest_version()
            
            # Tạo bản sao lưu
            backup_path = self._create_backup()
            if not backup_path:
                logger.error("Không thể tạo bản sao lưu, hủy cập nhật")
                return False
            
            # Tải bản cập nhật
            update_file = self._download_update(latest_version)
            if not update_file:
                logger.error("Không thể tải bản cập nhật, hủy cập nhật")
                return False
            
            # Áp dụng bản cập nhật
            if not self._apply_update(update_file, latest_version):
                logger.error("Không thể áp dụng bản cập nhật, đang khôi phục từ bản sao lưu")
                self._restore_backup(backup_path)
                return False
            
            # Kiểm tra tính hợp lệ của bản cập nhật
            if not self._verify_update(latest_version):
                logger.error("Bản cập nhật không hợp lệ, đang khôi phục từ bản sao lưu")
                self._restore_backup(backup_path)
                return False
            
            logger.info(f"Đã cập nhật thành công lên phiên bản {latest_version}")
            return True
        except Exception as e:
            logger.error(f"Lỗi không xử lý được trong quá trình cập nhật: {str(e)}")
            return False
    
    def check_for_updates(self):
        """
        Kiểm tra xem có bản cập nhật mới không
        
        Returns:
            dict: Thông tin về bản cập nhật mới, hoặc None nếu không có
        """
        if self.needs_update():
            latest_version = self.get_latest_version()
            current_version = self.get_current_version()
            
            return {
                "available": True,
                "current_version": current_version,
                "latest_version": latest_version,
                "update_url": self.update_url
            }
        else:
            return {
                "available": False,
                "current_version": self.get_current_version()
            }
    
    def get_update_history(self):
        """
        Lấy lịch sử cập nhật
        
        Returns:
            list: Danh sách các lần cập nhật
        """
        try:
            history_file = "update_packages/update_history.json"
            
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
                return history
            else:
                return []
        except Exception as e:
            logger.error(f"Lỗi khi đọc lịch sử cập nhật: {str(e)}")
            return []
    
    def add_update_to_history(self, version, success):
        """
        Thêm một bản ghi vào lịch sử cập nhật
        
        Args:
            version (str): Phiên bản cập nhật
            success (bool): True nếu cập nhật thành công, False nếu thất bại
        """
        try:
            history_file = "update_packages/update_history.json"
            history = self.get_update_history()
            
            entry = {
                "version": version,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "success": success
            }
            
            history.append(entry)
            
            # Đảm bảo thư mục tồn tại
            os.makedirs("update_packages", exist_ok=True)
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi thêm bản ghi vào lịch sử cập nhật: {str(e)}")


# Hàm main để chạy trực tiếp module
def main():
    """Hàm main"""
    # Khởi tạo updater
    updater = BotUpdater()
    
    # Kiểm tra cập nhật
    update_info = updater.check_for_updates()
    
    if update_info["available"]:
        print(f"Có bản cập nhật mới: {update_info['latest_version']} (hiện tại: {update_info['current_version']})")
        print("Bạn có muốn cập nhật không? (y/n)")
        
        choice = input().strip().lower()
        if choice == 'y':
            print("Đang cập nhật...")
            if updater.update():
                print("Cập nhật thành công!")
                updater.add_update_to_history(update_info['latest_version'], True)
            else:
                print("Cập nhật thất bại!")
                updater.add_update_to_history(update_info['latest_version'], False)
        else:
            print("Đã hủy cập nhật")
    else:
        print(f"Bot đã ở phiên bản mới nhất ({update_info['current_version']})")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())