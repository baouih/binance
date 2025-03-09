import os
import sys
import requests
import zipfile
import shutil
import logging
import json
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_updater")

# Thông tin cập nhật
REPLIT_URL = "https://replit.com/@YourUsername/TradingSystem"  # Thay thế bằng URL thực tế
DOWNLOAD_URL = "https://github.com/yourusername/TradingSystem/archive/refs/heads/main.zip"  # Thay thế bằng URL thực tế
VERSION_INFO_URL = "https://raw.githubusercontent.com/yourusername/TradingSystem/main/version.json"  # Thay thế bằng URL thực tế
LOCAL_VERSION_FILE = "version.json"
BACKUP_DIR = "backups"
TEMP_DIR = "temp_update"

def get_current_version():
    """Lấy thông tin phiên bản hiện tại"""
    try:
        if os.path.exists(LOCAL_VERSION_FILE):
            with open(LOCAL_VERSION_FILE, 'r') as f:
                version_info = json.load(f)
            return version_info.get("version", "0.0.0")
        else:
            return "0.0.0"
    except Exception as e:
        logger.error(f"Lỗi khi đọc phiên bản hiện tại: {e}")
        return "0.0.0"

def get_latest_version():
    """Kiểm tra phiên bản mới nhất từ server"""
    try:
        response = requests.get(VERSION_INFO_URL, timeout=10)
        if response.status_code == 200:
            version_info = response.json()
            return version_info.get("version", "0.0.0")
        else:
            logger.warning(f"Không thể kết nối đến server kiểm tra phiên bản: {response.status_code}")
            return "0.0.0"
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra phiên bản mới: {e}")
        return "0.0.0"

def backup_current_files():
    """Sao lưu các tệp quan trọng hiện tại"""
    try:
        # Tạo thư mục backup nếu chưa tồn tại
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # Tạo thư mục backup cho phiên bản hiện tại
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_version = get_current_version()
        backup_folder = os.path.join(BACKUP_DIR, f"v{current_version}_{backup_time}")
        os.makedirs(backup_folder, exist_ok=True)
        
        # Danh sách các tệp và thư mục cần sao lưu
        important_files = [
            "account_config.json",
            ".env",
            "telegram_config.json",
            "configs",
            "data"
        ]
        
        # Sao lưu từng tệp
        for item in important_files:
            if os.path.exists(item):
                if os.path.isdir(item):
                    shutil.copytree(item, os.path.join(backup_folder, item), dirs_exist_ok=True)
                else:
                    shutil.copy2(item, os.path.join(backup_folder, item))
        
        logger.info(f"Đã sao lưu các tệp quan trọng vào {backup_folder}")
        return backup_folder
    
    except Exception as e:
        logger.error(f"Lỗi khi sao lưu tệp: {e}")
        return None

def download_update(url, destination):
    """Tải bản cập nhật từ server"""
    try:
        logger.info(f"Đang tải bản cập nhật từ {url}...")
        
        # Tạo thư mục tạm nếu chưa tồn tại
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
        
        # Tải file zip
        response = requests.get(url, stream=True, timeout=60)
        if response.status_code == 200:
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Đã tải bản cập nhật thành công: {destination}")
            return True
        else:
            logger.error(f"Không thể tải bản cập nhật: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Lỗi khi tải bản cập nhật: {e}")
        return False

def extract_update(zip_file, extract_dir):
    """Giải nén bản cập nhật"""
    try:
        logger.info(f"Đang giải nén {zip_file}...")
        
        # Giải nén file zip
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        logger.info(f"Đã giải nén thành công vào {extract_dir}")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi giải nén bản cập nhật: {e}")
        return False

def apply_update(source_dir, target_dir):
    """Áp dụng bản cập nhật"""
    try:
        logger.info(f"Đang áp dụng bản cập nhật từ {source_dir} vào {target_dir}...")
        
        # Tìm thư mục con trong thư mục giải nén (thường là tên repo-branch)
        extracted_folders = [f for f in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, f))]
        if not extracted_folders:
            logger.error("Không tìm thấy thư mục con sau khi giải nén")
            return False
        
        # Sử dụng thư mục đầu tiên trong danh sách
        source_dir = os.path.join(source_dir, extracted_folders[0])
        
        # Danh sách các tệp và thư mục cần giữ nguyên
        keep_items = [
            "account_config.json",
            ".env",
            "telegram_config.json",
            "backups"
        ]
        
        # Danh sách các thư mục cần giữ nội dung
        merge_folders = [
            "configs",
            "data"
        ]
        
        # Sao chép tất cả các tệp từ thư mục nguồn, ngoại trừ các tệp cần giữ nguyên
        for item in os.listdir(source_dir):
            source_path = os.path.join(source_dir, item)
            target_path = os.path.join(target_dir, item)
            
            # Bỏ qua các tệp và thư mục cần giữ nguyên
            if item in keep_items:
                continue
            
            # Xử lý các thư mục cần merge
            elif item in merge_folders:
                # Nếu thư mục đích chưa tồn tại, tạo mới
                if not os.path.exists(target_path):
                    os.makedirs(target_path)
                
                # Merge nội dung
                for sub_item in os.listdir(source_path):
                    sub_source = os.path.join(source_path, sub_item)
                    sub_target = os.path.join(target_path, sub_item)
                    
                    # Nếu là thư mục, sao chép toàn bộ
                    if os.path.isdir(sub_source):
                        if os.path.exists(sub_target):
                            shutil.rmtree(sub_target)
                        shutil.copytree(sub_source, sub_target)
                    else:
                        # Nếu là tệp, sao chép ghi đè
                        shutil.copy2(sub_source, sub_target)
            
            # Với các tệp và thư mục khác, sao chép ghi đè
            else:
                if os.path.isdir(source_path):
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    shutil.copytree(source_path, target_path)
                else:
                    shutil.copy2(source_path, target_path)
        
        logger.info("Đã áp dụng bản cập nhật thành công")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng bản cập nhật: {e}")
        return False

def update_version_file(version):
    """Cập nhật tệp thông tin phiên bản"""
    try:
        version_info = {
            "version": version,
            "update_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(LOCAL_VERSION_FILE, 'w') as f:
            json.dump(version_info, f, indent=4)
        
        logger.info(f"Đã cập nhật thông tin phiên bản: {version}")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật tệp thông tin phiên bản: {e}")
        return False

def clean_temp_files():
    """Dọn dẹp các tệp tạm thời"""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        
        logger.info("Đã dọn dẹp các tệp tạm thời")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi dọn dẹp tệp tạm thời: {e}")
        return False

def run_update():
    """Thực hiện quy trình cập nhật"""
    logger.info("Bắt đầu quá trình cập nhật...")
    
    # Kiểm tra phiên bản
    current_version = get_current_version()
    latest_version = get_latest_version()
    
    logger.info(f"Phiên bản hiện tại: {current_version}")
    logger.info(f"Phiên bản mới nhất: {latest_version}")
    
    # So sánh phiên bản
    if latest_version == "0.0.0":
        logger.warning("Không thể kiểm tra phiên bản mới. Quá trình cập nhật bị hủy.")
        return False
    
    if current_version == latest_version:
        logger.info("Bạn đang sử dụng phiên bản mới nhất. Không cần cập nhật.")
        return True
    
    # Sao lưu các tệp quan trọng
    backup_folder = backup_current_files()
    if not backup_folder:
        logger.warning("Không thể sao lưu tệp. Quá trình cập nhật bị hủy.")
        return False
    
    # Tải bản cập nhật
    download_path = os.path.join(TEMP_DIR, "update.zip")
    if not download_update(DOWNLOAD_URL, download_path):
        logger.warning("Không thể tải bản cập nhật. Quá trình cập nhật bị hủy.")
        return False
    
    # Giải nén bản cập nhật
    extract_path = os.path.join(TEMP_DIR, "extracted")
    if not extract_update(download_path, extract_path):
        logger.warning("Không thể giải nén bản cập nhật. Quá trình cập nhật bị hủy.")
        return False
    
    # Áp dụng bản cập nhật
    if not apply_update(extract_path, os.getcwd()):
        logger.warning("Không thể áp dụng bản cập nhật. Quá trình cập nhật bị hủy.")
        return False
    
    # Cập nhật tệp thông tin phiên bản
    if not update_version_file(latest_version):
        logger.warning("Không thể cập nhật tệp thông tin phiên bản.")
    
    # Dọn dẹp các tệp tạm thời
    clean_temp_files()
    
    logger.info(f"Cập nhật thành công lên phiên bản {latest_version}")
    return True

if __name__ == "__main__":
    success = run_update()
    if success:
        print("Cập nhật hoàn tất. Vui lòng khởi động lại ứng dụng.")
        sys.exit(0)
    else:
        print("Cập nhật thất bại. Vui lòng thử lại sau hoặc liên hệ hỗ trợ.")
        sys.exit(1)