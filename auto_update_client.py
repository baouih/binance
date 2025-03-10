#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Công cụ cập nhật tự động
"""

import os
import sys
import json
import time
import shutil
import logging
import requests
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auto_update.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("auto_updater")

# URL cơ sở cho việc cập nhật
BASE_URL = "https://x37xj5-5000.csb.app/updates"  # Thay thế bằng URL thực

class AutoUpdater:
    """Lớp cập nhật tự động"""
    
    def __init__(self):
        """Khởi tạo công cụ cập nhật"""
        self.current_version = self.get_current_version()
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Phiên bản hiện tại: {self.current_version}")
    
    def get_current_version(self) -> str:
        """Lấy phiên bản hiện tại"""
        version_file = "version.txt"
        
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
        
        return "1.0.0"  # Phiên bản mặc định
    
    def check_for_updates(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Kiểm tra cập nhật mới
        
        :return: Tuple (có cập nhật, phiên bản mới, thông tin cập nhật)
        """
        try:
            # Gửi yêu cầu kiểm tra cập nhật
            response = requests.get(f"{BASE_URL}/check", params={"version": self.current_version})
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("update_available", False):
                    new_version = data.get("new_version", "")
                    update_info = data.get("update_info", {})
                    
                    logger.info(f"Có cập nhật mới: {new_version}")
                    return True, new_version, update_info
                else:
                    logger.info("Không có cập nhật mới")
                    return False, self.current_version, {}
            else:
                logger.error(f"Lỗi khi kiểm tra cập nhật: {response.status_code}")
                return False, self.current_version, {}
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra cập nhật: {str(e)}")
            return False, self.current_version, {}
    
    def download_update(self, version: str) -> bool:
        """
        Tải xuống bản cập nhật
        
        :param version: Phiên bản cần tải
        :return: True nếu thành công, False nếu thất bại
        """
        try:
            # Tạo đường dẫn tải xuống
            download_path = os.path.join(self.temp_dir, f"TradingBot_v{version}.exe")
            
            # Gửi yêu cầu tải xuống
            response = requests.get(f"{BASE_URL}/download", params={"version": version}, stream=True)
            
            if response.status_code == 200:
                # Tải xuống file
                with open(download_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"Đã tải xuống bản cập nhật {version}")
                return True
            else:
                logger.error(f"Lỗi khi tải xuống bản cập nhật: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Lỗi khi tải xuống bản cập nhật: {str(e)}")
            return False
    
    def install_update(self, version: str) -> bool:
        """
        Cài đặt bản cập nhật
        
        :param version: Phiên bản cần cài đặt
        :return: True nếu thành công, False nếu thất bại
        """
        try:
            # Đường dẫn file cập nhật
            update_file = os.path.join(self.temp_dir, f"TradingBot_v{version}.exe")
            
            if not os.path.exists(update_file):
                logger.error(f"Không tìm thấy file cập nhật: {update_file}")
                return False
            
            # Chạy file cài đặt
            subprocess.Popen([update_file])
            
            # Cập nhật phiên bản hiện tại
            with open("version.txt", "w") as f:
                f.write(version)
            
            logger.info(f"Đã cài đặt bản cập nhật {version}")
            
            # Thoát ứng dụng hiện tại để cài đặt bản mới
            sys.exit(0)
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi cài đặt bản cập nhật: {str(e)}")
            return False
    
    def cleanup(self):
        """Dọn dẹp các file tạm"""
        try:
            # Xóa thư mục tạm
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            logger.info("Đã dọn dẹp các file tạm")
        
        except Exception as e:
            logger.error(f"Lỗi khi dọn dẹp các file tạm: {str(e)}")

def main():
    """Hàm chính"""
    updater = AutoUpdater()
    
    # Kiểm tra cập nhật
    has_update, new_version, update_info = updater.check_for_updates()
    
    if has_update:
        # Tải xuống bản cập nhật
        if updater.download_update(new_version):
            # Cài đặt bản cập nhật
            updater.install_update(new_version)
    
    # Dọn dẹp
    updater.cleanup()

if __name__ == "__main__":
    main()