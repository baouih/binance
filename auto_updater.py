#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module cập nhật tự động cho ứng dụng desktop
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
from typing import Dict, Any, Optional, Tuple, List

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

# URL cơ sở cho máy chủ cập nhật
UPDATE_SERVER_URL = "https://api.github.com/repos/yourusername/tradingbot/releases/latest"

class AutoUpdater:
    """Lớp xử lý cập nhật tự động"""
    
    def __init__(self):
        """Khởi tạo updater"""
        # Tạo thư mục tạm
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Khởi tạo updater với thư mục tạm: {self.temp_dir}")
        
        # Tải thông tin phiên bản hiện tại
        self.current_version = self.get_current_version()
        logger.info(f"Phiên bản hiện tại: {self.current_version}")
    
    def get_current_version(self) -> str:
        """
        Lấy thông tin phiên bản hiện tại
        
        :return: Chuỗi phiên bản (ví dụ: "1.0.0")
        """
        # Đường dẫn đến file phiên bản
        version_file = "version.txt"
        
        # Nếu file tồn tại, đọc phiên bản
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as f:
                    version = f.read().strip()
                return version
            except Exception as e:
                logger.error(f"Lỗi khi đọc file phiên bản: {str(e)}")
        
        # Nếu không tìm thấy file hoặc có lỗi, trả về phiên bản mặc định
        return "1.0.0"
    
    def save_current_version(self, version: str):
        """
        Lưu phiên bản hiện tại vào file
        
        :param version: Chuỗi phiên bản cần lưu
        """
        try:
            # Lưu phiên bản vào file
            with open("version.txt", "w") as f:
                f.write(version)
            logger.info(f"Đã lưu phiên bản {version} vào file")
        except Exception as e:
            logger.error(f"Lỗi khi lưu phiên bản: {str(e)}")
    
    def check_for_updates(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Kiểm tra cập nhật mới từ máy chủ
        
        :return: Tuple (có cập nhật, phiên bản mới, thông tin cập nhật)
        """
        try:
            logger.info("Đang kiểm tra cập nhật từ máy chủ...")
            
            # Thực hiện kiểm tra cập nhật từ máy chủ
            # Mẫu: Sử dụng GitHub API để kiểm tra phiên bản mới nhất
            response = requests.get(UPDATE_SERVER_URL)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").lstrip("v")
                
                # So sánh phiên bản
                if self.compare_versions(latest_version, self.current_version) > 0:
                    logger.info(f"Có phiên bản mới: {latest_version}")
                    
                    # Thông tin cập nhật
                    update_info = {
                        "version": latest_version,
                        "description": data.get("body", ""),
                        "download_url": data.get("assets", [{}])[0].get("browser_download_url", ""),
                        "release_date": data.get("published_at", "")
                    }
                    
                    return True, latest_version, update_info
                else:
                    logger.info(f"Không có phiên bản mới (hiện tại: {self.current_version}, mới nhất: {latest_version})")
                    return False, self.current_version, {}
            else:
                logger.error(f"Lỗi khi truy cập máy chủ cập nhật: {response.status_code}")
                return False, self.current_version, {}
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra cập nhật: {str(e)}")
            return False, self.current_version, {}
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        So sánh hai phiên bản
        
        :param version1: Phiên bản thứ nhất
        :param version2: Phiên bản thứ hai
        :return: 1 nếu version1 > version2, 0 nếu bằng nhau, -1 nếu version1 < version2
        """
        try:
            v1_parts = list(map(int, version1.split('.')))
            v2_parts = list(map(int, version2.split('.')))
            
            # Đảm bảo cả hai danh sách có cùng độ dài
            while len(v1_parts) < len(v2_parts):
                v1_parts.append(0)
            while len(v2_parts) < len(v1_parts):
                v2_parts.append(0)
            
            # So sánh từng phần
            for i in range(len(v1_parts)):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            
            # Hai phiên bản bằng nhau
            return 0
        
        except Exception as e:
            logger.error(f"Lỗi khi so sánh phiên bản: {str(e)}")
            # Trong trường hợp lỗi, giả định không có cập nhật
            return 0
    
    def download_update(self, download_url: str, version: str) -> Optional[str]:
        """
        Tải bản cập nhật từ máy chủ
        
        :param download_url: URL tải bản cập nhật
        :param version: Phiên bản của bản cập nhật
        :return: Đường dẫn đến file đã tải, hoặc None nếu có lỗi
        """
        try:
            logger.info(f"Đang tải bản cập nhật {version} từ {download_url}...")
            
            # Tạo tên file
            file_name = f"TradingBot_v{version}.zip"
            download_path = os.path.join(self.temp_dir, file_name)
            
            # Tải file
            response = requests.get(download_url, stream=True)
            
            if response.status_code == 200:
                with open(download_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                logger.info(f"Đã tải bản cập nhật thành công: {download_path}")
                return download_path
            else:
                logger.error(f"Lỗi khi tải bản cập nhật: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Lỗi khi tải bản cập nhật: {str(e)}")
            return None
    
    def install_update(self, update_file: str, version: str) -> bool:
        """
        Cài đặt bản cập nhật đã tải
        
        :param update_file: Đường dẫn đến file cập nhật
        :param version: Phiên bản mới
        :return: True nếu thành công, False nếu thất bại
        """
        try:
            logger.info(f"Đang cài đặt bản cập nhật {version}...")
            
            # Đường dẫn giải nén
            extract_dir = os.path.join(self.temp_dir, f"update_{version}")
            os.makedirs(extract_dir, exist_ok=True)
            
            # Giải nén file cập nhật
            import zipfile
            with zipfile.ZipFile(update_file, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info(f"Đã giải nén bản cập nhật vào {extract_dir}")
            
            # Tạo script cập nhật
            update_script = self.create_update_script(extract_dir, version)
            
            if update_script:
                logger.info(f"Đã tạo script cập nhật: {update_script}")
                
                # Chạy script cập nhật
                if sys.platform == "win32":
                    os.startfile(update_script)
                else:
                    subprocess.Popen(["python", update_script])
                
                logger.info("Đã chạy script cập nhật, đang thoát ứng dụng...")
                
                # Thoát ứng dụng hiện tại
                time.sleep(2)
                sys.exit(0)
                
                return True
            else:
                logger.error("Không thể tạo script cập nhật")
                return False
            
        except Exception as e:
            logger.error(f"Lỗi khi cài đặt bản cập nhật: {str(e)}")
            return False
    
    def create_update_script(self, extract_dir: str, version: str) -> Optional[str]:
        """
        Tạo script để cập nhật ứng dụng
        
        :param extract_dir: Thư mục chứa bản cập nhật đã giải nén
        :param version: Phiên bản mới
        :return: Đường dẫn đến script cập nhật, hoặc None nếu có lỗi
        """
        try:
            # Tạo đường dẫn script
            script_path = os.path.join(self.temp_dir, "do_update.py")
            
            # Lấy đường dẫn hiện tại
            current_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
            
            # Nội dung script
            script_content = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Script cập nhật ứng dụng Trading Bot
\"\"\"

import os
import sys
import time
import shutil
import logging
import subprocess
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update_execution.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("update_execution")

def main():
    \"\"\"Hàm chính thực hiện cập nhật\"\"\"
    try:
        logger.info("Bắt đầu quá trình cập nhật...")
        
        # Đường dẫn ứng dụng hiện tại
        app_dir = "{current_dir}"
        logger.info(f"Thư mục ứng dụng: {{app_dir}}")
        
        # Đường dẫn bản cập nhật
        update_dir = "{extract_dir}"
        logger.info(f"Thư mục bản cập nhật: {{update_dir}}")
        
        # Thời gian chờ để đảm bảo ứng dụng chính đã đóng
        logger.info("Đang chờ ứng dụng chính đóng...")
        time.sleep(3)
        
        # Sao chép các file từ bản cập nhật
        logger.info("Đang sao chép files...")
        
        for root, dirs, files in os.walk(update_dir):
            # Tạo đường dẫn tương đối
            rel_path = os.path.relpath(root, update_dir)
            
            # Tạo thư mục đích
            dest_dir = os.path.join(app_dir, rel_path) if rel_path != "." else app_dir
            os.makedirs(dest_dir, exist_ok=True)
            
            # Sao chép các file
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_dir, file)
                
                # Sao chép file
                shutil.copy2(src_file, dest_file)
                logger.info(f"Đã sao chép: {{src_file}} -> {{dest_file}}")
        
        # Cập nhật file phiên bản
        with open(os.path.join(app_dir, "version.txt"), "w") as f:
            f.write("{version}")
        logger.info(f"Đã cập nhật phiên bản thành {version}")
        
        # Khởi động lại ứng dụng
        logger.info("Đang khởi động lại ứng dụng...")
        
        if sys.platform == "win32":
            # Windows
            os.startfile(os.path.join(app_dir, "run_desktop_app.py"))
        else:
            # Linux/Mac
            subprocess.Popen(["python", os.path.join(app_dir, "run_desktop_app.py")])
        
        logger.info("Cập nhật hoàn tất!")
        
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật: {{str(e)}}")
        
        # Hiển thị thông báo lỗi
        try:
            if sys.platform == "win32":
                subprocess.Popen(["msg", "*", f"Lỗi khi cập nhật: {{str(e)}}"])
        except:
            pass

if __name__ == "__main__":
    main()
"""
            
            # Ghi script ra file
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Đặt quyền thực thi cho script (nếu không phải Windows)
            if sys.platform != "win32":
                os.chmod(script_path, 0o755)
            
            return script_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo script cập nhật: {str(e)}")
            return None
    
    def cleanup(self):
        """Dọn dẹp các file tạm"""
        try:
            # Xóa thư mục tạm
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            logger.info(f"Đã dọn dẹp thư mục tạm: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Lỗi khi dọn dẹp: {str(e)}")
    
    def check_and_update(self) -> Dict[str, Any]:
        """
        Kiểm tra và cập nhật (nếu có)
        
        :return: Dict chứa thông tin kết quả cập nhật
        """
        result = {
            "success": False,
            "message": "",
            "current_version": self.current_version,
            "new_version": "",
            "has_update": False
        }
        
        try:
            # Kiểm tra cập nhật
            has_update, new_version, update_info = self.check_for_updates()
            
            result["has_update"] = has_update
            result["new_version"] = new_version
            
            if has_update:
                # Hiển thị thông tin cập nhật
                result["message"] = f"Đã tìm thấy phiên bản mới: {new_version}"
                result["update_info"] = update_info
            else:
                # Không có cập nhật
                result["message"] = f"Không có phiên bản mới (hiện tại: {self.current_version})"
                result["success"] = True
        
        except Exception as e:
            result["message"] = f"Lỗi khi kiểm tra cập nhật: {str(e)}"
            logger.error(result["message"])
        
        return result
    
    def perform_update(self, update_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực hiện cập nhật
        
        :param update_info: Thông tin cập nhật
        :return: Dict chứa kết quả cập nhật
        """
        result = {
            "success": False,
            "message": "",
            "version": update_info.get("version", ""),
        }
        
        try:
            # Tải bản cập nhật
            download_url = update_info.get("download_url", "")
            version = update_info.get("version", "")
            
            if not download_url or not version:
                result["message"] = "Thiếu thông tin cập nhật"
                return result
            
            # Tải bản cập nhật
            update_file = self.download_update(download_url, version)
            
            if not update_file:
                result["message"] = "Không thể tải bản cập nhật"
                return result
            
            # Cài đặt bản cập nhật
            if self.install_update(update_file, version):
                result["success"] = True
                result["message"] = f"Đang cập nhật lên phiên bản {version}..."
            else:
                result["message"] = "Lỗi khi cài đặt bản cập nhật"
        
        except Exception as e:
            result["message"] = f"Lỗi khi thực hiện cập nhật: {str(e)}"
            logger.error(result["message"])
        
        return result

def check_for_updates() -> Dict[str, Any]:
    """
    Kiểm tra cập nhật (hàm tiện ích)
    
    :return: Dict chứa thông tin kết quả kiểm tra
    """
    updater = AutoUpdater()
    result = updater.check_and_update()
    updater.cleanup()
    return result

def install_update(update_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cài đặt bản cập nhật (hàm tiện ích)
    
    :param update_info: Thông tin cập nhật
    :return: Dict chứa kết quả cập nhật
    """
    updater = AutoUpdater()
    result = updater.perform_update(update_info)
    # Không cần cleanup vì ứng dụng sẽ thoát sau khi cài đặt
    return result

if __name__ == "__main__":
    # Kiểm tra cập nhật khi chạy trực tiếp module này
    result = check_for_updates()
    
    if result["success"]:
        if result["has_update"]:
            print(f"Có phiên bản mới: {result['new_version']}")
            
            # Hỏi người dùng có muốn cập nhật không
            answer = input("Bạn có muốn cập nhật không? (y/n): ")
            
            if answer.lower() == "y":
                install_result = install_update(result["update_info"])
                print(install_result["message"])
        else:
            print(f"Không có phiên bản mới. Phiên bản hiện tại: {result['current_version']}")
    else:
        print(f"Lỗi: {result['message']}")