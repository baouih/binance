"""
Module quản lý cập nhật hệ thống

Module này cung cấp các công cụ để quản lý việc tạo, phân phối, cài đặt và quay lại
các bản cập nhật cho hệ thống. Nó bao gồm quản lý phiên bản, tạo gói cập nhật, 
sao lưu hệ thống trước khi cập nhật, và quay lại phiên bản trước nếu cần.
"""

import os
import json
import time
import shutil
import hashlib
import logging
import zipfile
import datetime
from typing import Dict, List, Optional, Tuple, Any

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('update_manager')

class UpdateManager:
    """Lớp quản lý cập nhật hệ thống"""

    def __init__(self, config_path: str = "update_config.json", 
                 update_dir: str = "update_packages", 
                 backup_dir: str = "backups"):
        """
        Khởi tạo UpdateManager
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            update_dir (str): Thư mục chứa các gói cập nhật
            backup_dir (str): Thư mục chứa các bản sao lưu
        """
        self.config_path = config_path
        self.update_dir = update_dir
        self.backup_dir = backup_dir
        
        # Tạo thư mục nếu không tồn tại
        os.makedirs(update_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        
        # Tải hoặc tạo cấu hình
        self.config = self._load_or_create_config()
        
        logger.info(f"Đã khởi tạo UpdateManager với phiên bản hiện tại: {self.config.get('version', '1.0.0')}")

    def _load_or_create_config(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Cấu hình cập nhật
        """
        default_config = {
            "version": "1.0.0",
            "last_update": None,
            "update_history": [],
            "auto_update": False,
            "update_check_interval": 86400,  # 24 tiếng
            "update_server": "https://update.example.com",
            "update_token": ""
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Đã tải cấu hình cập nhật từ {self.config_path}")
                    return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình cập nhật: {str(e)}")
        
        # Tạo file cấu hình mặc định nếu không tồn tại
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo file cấu hình cập nhật mới tại {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo file cấu hình cập nhật: {str(e)}")
        
        return default_config

    def _save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
                logger.info(f"Đã lưu cấu hình cập nhật vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình cập nhật: {str(e)}")
            return False

    def get_current_version(self) -> str:
        """
        Lấy phiên bản hiện tại
        
        Returns:
            str: Phiên bản hiện tại
        """
        return self.config.get("version", "1.0.0")

    def get_update_history(self) -> List[Dict]:
        """
        Lấy lịch sử cập nhật
        
        Returns:
            List[Dict]: Danh sách các bản ghi cập nhật
        """
        return self.config.get("update_history", [])

    def get_available_updates(self) -> List[Dict]:
        """
        Lấy danh sách các bản cập nhật có sẵn
        
        Returns:
            List[Dict]: Danh sách các bản cập nhật
        """
        updates = []
        if not os.path.exists(self.update_dir):
            logger.warning(f"Thư mục cập nhật {self.update_dir} không tồn tại")
            return updates
        
        try:
            current_version = self.get_current_version()
            for item in os.listdir(self.update_dir):
                if item.endswith('.zip') and '_v' in item:
                    try:
                        # Trích xuất thông tin phiên bản từ tên file
                        version = item.split('_v')[1].split('.zip')[0]
                        
                        # So sánh phiên bản
                        if self._is_newer_version(version, current_version):
                            file_path = os.path.join(self.update_dir, item)
                            file_info = os.stat(file_path)
                            
                            updates.append({
                                "filename": item,
                                "version": version,
                                "size": file_info.st_size,
                                "created_time": datetime.datetime.fromtimestamp(file_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                                "path": file_path
                            })
                    except Exception as e:
                        logger.error(f"Lỗi khi xử lý file cập nhật {item}: {str(e)}")
            
            # Sắp xếp theo phiên bản mới nhất
            updates.sort(key=lambda x: self._version_tuple(x['version']), reverse=True)
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách cập nhật: {str(e)}")
        
        return updates

    def get_available_backups(self) -> List[Dict]:
        """
        Lấy danh sách các bản sao lưu có sẵn
        
        Returns:
            List[Dict]: Danh sách các bản sao lưu
        """
        backups = []
        if not os.path.exists(self.backup_dir):
            logger.warning(f"Thư mục sao lưu {self.backup_dir} không tồn tại")
            return backups
        
        try:
            for item in os.listdir(self.backup_dir):
                if item.endswith('.zip') and ('backup_' in item or 'before_update_' in item):
                    try:
                        file_path = os.path.join(self.backup_dir, item)
                        file_info = os.stat(file_path)
                        
                        # Trích xuất phiên bản từ tên file nếu có
                        version = "unknown"
                        if 'before_update_v' in item:
                            version = item.split('before_update_v')[1].split('.zip')[0]
                        
                        backups.append({
                            "filename": item,
                            "version": version,
                            "size": file_info.st_size,
                            "created_time": datetime.datetime.fromtimestamp(file_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                            "path": file_path
                        })
                    except Exception as e:
                        logger.error(f"Lỗi khi xử lý file sao lưu {item}: {str(e)}")
            
            # Sắp xếp theo thời gian tạo mới nhất
            backups.sort(key=lambda x: x['created_time'], reverse=True)
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách sao lưu: {str(e)}")
        
        return backups

    def create_backup(self, name: str = None) -> Optional[str]:
        """
        Tạo bản sao lưu của hệ thống hiện tại
        
        Args:
            name (str, optional): Tên bản sao lưu, mặc định là timestamp
            
        Returns:
            Optional[str]: Đường dẫn đến file sao lưu hoặc None nếu thất bại
        """
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if name is None:
            name = f"backup_{timestamp}"
        
        backup_path = os.path.join(self.backup_dir, f"{name}.zip")
        
        try:
            # Danh sách các thư mục và file cần sao lưu
            dirs_to_backup = ['app', 'configs', 'models', 'routes', 'static', 'templates']
            files_to_backup = ['main.py', 'app.py', 'config.json', '.env.example', 'account_config.json']
            
            # Thêm các file quan trọng khác
            important_files = []
            for file in os.listdir('.'):
                if file.endswith('.py') and not file.startswith('__') and file not in files_to_backup:
                    important_files.append(file)
            
            files_to_backup.extend(important_files)
            
            # Tạo file zip
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
                # Sao lưu các thư mục
                for dir_name in dirs_to_backup:
                    if os.path.exists(dir_name) and os.path.isdir(dir_name):
                        for root, _, files in os.walk(dir_name):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path) and os.path.isfile(file_path):
                                    backup_zip.write(file_path)
                
                # Sao lưu các file
                for file_name in files_to_backup:
                    if os.path.exists(file_name) and os.path.isfile(file_name):
                        backup_zip.write(file_name)
            
            logger.info(f"Đã tạo bản sao lưu tại {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo bản sao lưu: {str(e)}")
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except:
                    pass
            return None

    def create_update_package(self, version: str, files: List[str] = None, 
                           description: str = "", include_deps: bool = True) -> Optional[str]:
        """
        Tạo gói cập nhật mới
        
        Args:
            version (str): Phiên bản của gói cập nhật
            files (List[str], optional): Danh sách đường dẫn tới các file cần bao gồm
            description (str): Mô tả về bản cập nhật
            include_deps (bool): Có bao gồm các file phụ thuộc không
            
        Returns:
            Optional[str]: Đường dẫn đến gói cập nhật hoặc None nếu thất bại
        """
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        package_name = f"update_{timestamp}_v{version}"
        package_path = os.path.join(self.update_dir, f"{package_name}.zip")
        
        try:
            current_version = self.get_current_version()
            
            # Kiểm tra phiên bản
            if not self._is_newer_version(version, current_version):
                logger.error(f"Phiên bản {version} không mới hơn phiên bản hiện tại {current_version}")
                return None
            
            # Nếu không có danh sách file cụ thể, sử dụng danh sách mặc định
            if not files:
                files = []
                # Thêm các file Python quan trọng
                for file in os.listdir('.'):
                    if file.endswith('.py') and not file.startswith('__'):
                        files.append(file)
                
                # Thêm các thư mục cần thiết
                dirs_to_include = ['app', 'routes', 'models', 'templates', 'static/js', 'static/css']
                for dir_name in dirs_to_include:
                    if os.path.exists(dir_name) and os.path.isdir(dir_name):
                        for root, _, dir_files in os.walk(dir_name):
                            for file in dir_files:
                                if not file.startswith('.'):
                                    file_path = os.path.join(root, file)
                                    files.append(file_path)
            
            # Tạo file zip
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as update_zip:
                # Thêm các file
                for file_path in files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        update_zip.write(file_path)
                
                # Tạo file metadata
                metadata = {
                    "version": version,
                    "previous_version": current_version,
                    "created_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "description": description,
                    "files": files
                }
                
                # Thêm file metadata vào zip
                update_zip.writestr('update_metadata.json', json.dumps(metadata, indent=4))
            
            logger.info(f"Đã tạo gói cập nhật {package_name} tại {package_path}")
            return package_path
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo gói cập nhật: {str(e)}")
            if os.path.exists(package_path):
                try:
                    os.remove(package_path)
                except:
                    pass
            return None

    def apply_update(self, update_path: str, auto_backup: bool = True) -> bool:
        """
        Áp dụng bản cập nhật
        
        Args:
            update_path (str): Đường dẫn đến gói cập nhật
            auto_backup (bool): Tự động tạo bản sao lưu trước khi cập nhật
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        if not os.path.exists(update_path):
            logger.error(f"Gói cập nhật không tồn tại: {update_path}")
            return False
        
        try:
            # Kiểm tra tính hợp lệ của gói cập nhật
            with zipfile.ZipFile(update_path, 'r') as update_zip:
                # Kiểm tra xem có file metadata không
                if 'update_metadata.json' not in update_zip.namelist():
                    logger.error(f"Gói cập nhật không hợp lệ: Thiếu file metadata")
                    return False
                
                # Đọc metadata
                metadata = json.loads(update_zip.read('update_metadata.json').decode('utf-8'))
                version = metadata.get('version')
                
                # Kiểm tra phiên bản
                current_version = self.get_current_version()
                if not self._is_newer_version(version, current_version):
                    logger.error(f"Phiên bản {version} không mới hơn phiên bản hiện tại {current_version}")
                    return False
                
                # Tạo bản sao lưu trước khi cập nhật
                backup_path = None
                if auto_backup:
                    backup_path = self.create_backup(f"before_update_v{version}")
                    if not backup_path:
                        logger.error("Không thể tạo bản sao lưu trước khi cập nhật")
                        return False
                
                # Giải nén và áp dụng cập nhật
                for file_info in update_zip.infolist():
                    if file_info.filename != 'update_metadata.json':
                        update_zip.extract(file_info, '.')
                
                # Cập nhật phiên bản và lịch sử
                self.config['previous_version'] = current_version
                self.config['version'] = version
                self.config['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Thêm vào lịch sử cập nhật
                update_history = self.config.get('update_history', [])
                update_history.append({
                    "version": version,
                    "previous_version": current_version,
                    "update_time": self.config['last_update'],
                    "description": metadata.get('description', ''),
                    "backup_path": backup_path
                })
                
                self.config['update_history'] = update_history
                self._save_config()
                
                logger.info(f"Đã cập nhật thành công lên phiên bản {version}")
                return True
        
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng cập nhật: {str(e)}")
            return False

    def rollback(self, backup_path: str = None) -> bool:
        """
        Quay lại phiên bản trước
        
        Args:
            backup_path (str, optional): Đường dẫn đến bản sao lưu
            
        Returns:
            bool: True nếu quay lại thành công, False nếu không
        """
        # Nếu không có backup_path, sử dụng bản sao lưu mới nhất
        if not backup_path:
            backups = self.get_available_backups()
            if not backups:
                logger.error("Không có bản sao lưu nào để quay lại")
                return False
            backup_path = backups[0]['path']
        
        if not os.path.exists(backup_path):
            logger.error(f"Bản sao lưu không tồn tại: {backup_path}")
            return False
        
        try:
            # Tạo bản sao lưu của phiên bản hiện tại trước khi rollback
            current_backup = self.create_backup(f"before_rollback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
            if not current_backup:
                logger.warning("Không thể tạo bản sao lưu của phiên bản hiện tại trước khi rollback")
            
            # Giải nén bản sao lưu
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                backup_zip.extractall('.')
            
            # Cập nhật phiên bản
            # Lấy phiên bản từ tên file nếu có
            version = "Unknown"
            if 'before_update_v' in backup_path:
                version = backup_path.split('before_update_v')[1].split('.zip')[0]
            
            # Cập nhật lịch sử và phiên bản
            current_version = self.get_current_version()
            self.config['previous_version'] = current_version
            self.config['version'] = version
            self.config['last_update'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Thêm vào lịch sử cập nhật
            update_history = self.config.get('update_history', [])
            update_history.append({
                "version": version,
                "previous_version": current_version,
                "update_time": self.config['last_update'],
                "description": f"Rollback to version {version}",
                "rollback": True
            })
            
            self.config['update_history'] = update_history
            self._save_config()
            
            logger.info(f"Đã quay lại phiên bản {version} thành công")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi quay lại phiên bản trước: {str(e)}")
            return False

    def check_for_updates(self, url: str = None, token: str = None) -> List[Dict]:
        """
        Kiểm tra cập nhật từ máy chủ
        
        Args:
            url (str, optional): URL của máy chủ cập nhật
            token (str, optional): Token xác thực
            
        Returns:
            List[Dict]: Danh sách các bản cập nhật có sẵn
        """
        if not url:
            url = self.config.get('update_server')
        if not token:
            token = self.config.get('update_token')
        
        # Thực hiện kiểm tra từ máy chủ
        # Ở đây là phần mã giả, cần thay thế bằng cài đặt thực tế
        logger.info(f"Kiểm tra cập nhật từ máy chủ {url}")
        
        # Mô phỏng kết quả
        return []

    def download_update(self, url: str, version: str) -> Optional[str]:
        """
        Tải xuống bản cập nhật từ máy chủ
        
        Args:
            url (str): URL của bản cập nhật
            version (str): Phiên bản của bản cập nhật
            
        Returns:
            Optional[str]: Đường dẫn đến gói cập nhật đã tải xuống hoặc None nếu thất bại
        """
        # Mã giả, cần thay thế bằng cài đặt thực tế
        logger.info(f"Tải xuống bản cập nhật phiên bản {version} từ {url}")
        
        return None

    def _is_newer_version(self, version1: str, version2: str) -> bool:
        """
        Kiểm tra xem version1 có mới hơn version2 không
        
        Args:
            version1 (str): Phiên bản thứ nhất
            version2 (str): Phiên bản thứ hai
            
        Returns:
            bool: True nếu version1 mới hơn version2, False nếu không
        """
        v1_parts = self._version_tuple(version1)
        v2_parts = self._version_tuple(version2)
        
        return v1_parts > v2_parts

    def _version_tuple(self, version: str) -> Tuple[int, ...]:
        """
        Chuyển đổi chuỗi phiên bản thành tuple để so sánh
        
        Args:
            version (str): Chuỗi phiên bản (ví dụ: '1.2.3')
            
        Returns:
            Tuple[int, ...]: Tuple các phần phiên bản
        """
        # Xử lý các trường hợp đặc biệt
        if version.lower() == 'unknown':
            return (0, 0, 0)
        
        # Tách và chuyển đổi các phần phiên bản thành số nguyên
        parts = []
        for part in version.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                # Xử lý các phần không phải số
                parts.append(0)
        
        # Đảm bảo có ít nhất 3 phần
        while len(parts) < 3:
            parts.append(0)
        
        return tuple(parts)

def main():
    """Hàm chính để test UpdateManager"""
    manager = UpdateManager()
    
    # Tạo bản sao lưu
    backup_path = manager.create_backup()
    print(f"Đã tạo bản sao lưu tại: {backup_path}")
    
    # Tạo gói cập nhật
    version = "1.1.0"  # Phiên bản mới
    update_path = manager.create_update_package(
        version=version,
        description="Cập nhật tính năng quản lý cập nhật"
    )
    print(f"Đã tạo gói cập nhật tại: {update_path}")
    
    if update_path:
        # Áp dụng cập nhật
        result = manager.apply_update(update_path)
        print(f"Kết quả cập nhật: {'Thành công' if result else 'Thất bại'}")

if __name__ == "__main__":
    main()