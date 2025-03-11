#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Công cụ đóng gói ứng dụng desktop giao dịch
"""

import os
import sys
import json
import shutil
import logging
import subprocess
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("packaging.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("packaging")

def get_current_version():
    """Lấy phiên bản hiện tại hoặc tạo phiên bản mới"""
    version_file = "version.txt"
    
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            version = f.read().strip()
        
        # Tăng phiên bản phụ
        major, minor, patch = version.split(".")
        patch = int(patch) + 1
        new_version = f"{major}.{minor}.{patch}"
    else:
        # Tạo phiên bản mới
        new_version = "1.0.0"
    
    # Lưu phiên bản mới
    with open(version_file, "w") as f:
        f.write(new_version)
    
    return new_version

def create_executable():
    """Tạo file thực thi"""
    logger.info("Bắt đầu tạo file thực thi...")
    
    try:
        # Lấy phiên bản
        version = get_current_version()
        logger.info(f"Đang đóng gói phiên bản {version}")
        
        # Tạo thư mục dist nếu chưa tồn tại
        if not os.path.exists("dist"):
            os.makedirs("dist")
        
        # Tạo thư mục temp để chứa các file cần thiết
        temp_dir = "temp_build"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Sao chép các file cần thiết
        logger.info("Đang sao chép các file cần thiết...")
        
        # Danh sách các file Python cần thiết
        python_files = [
            "run_desktop_app.py",
            "enhanced_trading_gui.py",
            "market_analyzer.py",
            "position_manager.py",
            "risk_manager.py",
            "auto_update_client.py"
        ]
        
        # Sao chép các file Python
        for file in python_files:
            if os.path.exists(file):
                shutil.copy(file, os.path.join(temp_dir, file))
                logger.info(f"Đã sao chép {file}")
            else:
                logger.warning(f"Không tìm thấy file {file}")
        
        # Tạo thư mục static
        static_dir = os.path.join(temp_dir, "static")
        os.makedirs(static_dir, exist_ok=True)
        
        # Sao chép thư mục static/icons
        if os.path.exists("static/icons"):
            shutil.copytree("static/icons", os.path.join(static_dir, "icons"), dirs_exist_ok=True)
            logger.info("Đã sao chép thư mục static/icons")
        
        # Tạo thư mục risk_configs
        risk_configs_dir = os.path.join(temp_dir, "risk_configs")
        os.makedirs(risk_configs_dir, exist_ok=True)
        
        # Sao chép các file cấu hình
        if os.path.exists("risk_configs"):
            for file in os.listdir("risk_configs"):
                if file.endswith(".json"):
                    shutil.copy(os.path.join("risk_configs", file), os.path.join(risk_configs_dir, file))
                    logger.info(f"Đã sao chép {file}")
        
        # Tạo file version
        with open(os.path.join(temp_dir, "version.txt"), "w") as f:
            f.write(version)
        
        # Tạo file README.txt
        with open(os.path.join(temp_dir, "README.txt"), "w", encoding="utf-8") as f:
            f.write(f"""Bot Giao Dịch Crypto - Phiên Bản Desktop {version}
            
Phiên bản: {version}
Ngày phát hành: {datetime.now().strftime("%d/%m/%Y")}

Hướng dẫn sử dụng:
1. Chạy file TradingBot.exe
2. Nhập API Key và API Secret từ Binance Testnet
3. Lưu cài đặt API và bắt đầu giao dịch

Lưu ý:
- Ứng dụng này sử dụng Binance Testnet để giao dịch
- Không sử dụng API Key và API Secret thật
- Để biết thêm thông tin, vui lòng xem tài liệu hướng dẫn

Liên hệ hỗ trợ: support@example.com
            """)
        
        # Chuyển đến thư mục temp
        os.chdir(temp_dir)
        
        # Tạo file spec cho PyInstaller
        spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('risk_configs', 'risk_configs'),
        ('version.txt', '.'),
        ('README.txt', '.')
    ],
    hiddenimports=[
        'PyQt5',
        'pandas',
        'numpy',
        'requests',
        'json',
        'logging',
        'datetime',
        'time',
        'os',
        'sys',
        'threading',
        'binance'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TradingBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/icons/app_icon.ico' if os.path.exists('static/icons/app_icon.ico') else None,
    version='{version}',
)
"""
        
        with open("TradingBot.spec", "w") as f:
            f.write(spec_content)
        
        # Tạo file exe bằng PyInstaller
        logger.info("Đang tạo file thực thi bằng PyInstaller...")
        
        # Kiểm tra xem PyInstaller có được cài đặt không
        try:
            import PyInstaller
            logger.info("PyInstaller đã được cài đặt")
        except ImportError:
            logger.info("PyInstaller chưa được cài đặt, đang cài đặt...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
        # Chạy PyInstaller
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "TradingBot.spec", "--clean"])
        
        # Quay lại thư mục gốc
        os.chdir("..")
        
        # Di chuyển file exe vào thư mục dist
        if os.path.exists(os.path.join(temp_dir, "dist", "TradingBot.exe")):
            # Tạo tên file với phiên bản
            dist_file = f"TradingBot_v{version}.exe"
            shutil.move(
                os.path.join(temp_dir, "dist", "TradingBot.exe"),
                os.path.join("dist", dist_file)
            )
            logger.info(f"Đã tạo file thực thi: {dist_file}")
        else:
            logger.error("Không tìm thấy file thực thi sau khi đóng gói")
            return False
        
        # Xóa thư mục temp
        shutil.rmtree(temp_dir)
        
        logger.info("Đã hoàn thành đóng gói ứng dụng")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo file thực thi: {str(e)}", exc_info=True)
        return False

def create_auto_updater():
    """Tạo công cụ cập nhật tự động"""
    logger.info("Đang tạo công cụ cập nhật tự động...")
    
    try:
        # Tạo file auto_update_client.py nếu chưa tồn tại
        if not os.path.exists("auto_update_client.py"):
            with open("auto_update_client.py", "w") as f:
                f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Công cụ cập nhật tự động
\"\"\"

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
    \"\"\"Lớp cập nhật tự động\"\"\"
    
    def __init__(self):
        \"\"\"Khởi tạo công cụ cập nhật\"\"\"
        self.current_version = self.get_current_version()
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Phiên bản hiện tại: {self.current_version}")
    
    def get_current_version(self) -> str:
        \"\"\"Lấy phiên bản hiện tại\"\"\"
        version_file = "version.txt"
        
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return f.read().strip()
        
        return "1.0.0"  # Phiên bản mặc định
    
    def check_for_updates(self) -> Tuple[bool, str, Dict[str, Any]]:
        \"\"\"
        Kiểm tra cập nhật mới
        
        :return: Tuple (có cập nhật, phiên bản mới, thông tin cập nhật)
        \"\"\"
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
        \"\"\"
        Tải xuống bản cập nhật
        
        :param version: Phiên bản cần tải
        :return: True nếu thành công, False nếu thất bại
        \"\"\"
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
        \"\"\"
        Cài đặt bản cập nhật
        
        :param version: Phiên bản cần cài đặt
        :return: True nếu thành công, False nếu thất bại
        \"\"\"
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
        \"\"\"Dọn dẹp các file tạm\"\"\"
        try:
            # Xóa thư mục tạm
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            logger.info("Đã dọn dẹp các file tạm")
        
        except Exception as e:
            logger.error(f"Lỗi khi dọn dẹp các file tạm: {str(e)}")

def main():
    \"\"\"Hàm chính\"\"\"
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
""")
            
            logger.info("Đã tạo file auto_update_client.py")
        
        # Tạo file update_server.py nếu chưa tồn tại
        if not os.path.exists("update_server.py"):
            with open("update_server.py", "w") as f:
                f.write("""#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Server cập nhật tự động
\"\"\"

import os
import json
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Thư mục chứa các bản cập nhật
UPDATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")

# Thông tin các phiên bản
VERSIONS = {}

def load_versions():
    \"\"\"Tải thông tin các phiên bản\"\"\"
    global VERSIONS
    
    version_file = os.path.join(UPDATES_DIR, "versions.json")
    
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            VERSIONS = json.load(f)
    else:
        # Tạo file versions.json mặc định
        VERSIONS = {
            "latest": "1.0.0",
            "versions": {
                "1.0.0": {
                    "release_date": "2023-01-01",
                    "changes": ["Phiên bản đầu tiên"],
                    "filename": "TradingBot_v1.0.0.exe"
                }
            }
        }
        
        with open(version_file, "w") as f:
            json.dump(VERSIONS, f, indent=4)

@app.route("/updates/check")
def check_update():
    \"\"\"API kiểm tra cập nhật\"\"\"
    current_version = request.args.get("version", "1.0.0")
    latest_version = VERSIONS.get("latest", "1.0.0")
    
    # So sánh phiên bản
    if current_version != latest_version:
        return jsonify({
            "update_available": True,
            "new_version": latest_version,
            "update_info": VERSIONS.get("versions", {}).get(latest_version, {})
        })
    else:
        return jsonify({
            "update_available": False
        })

@app.route("/updates/download")
def download_update():
    \"\"\"API tải xuống bản cập nhật\"\"\"
    version = request.args.get("version", "1.0.0")
    
    # Lấy tên file từ thông tin phiên bản
    filename = VERSIONS.get("versions", {}).get(version, {}).get("filename")
    
    if not filename:
        return jsonify({"error": "Phiên bản không hợp lệ"}), 400
    
    # Đường dẫn đầy đủ đến file
    file_path = os.path.join(UPDATES_DIR, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": "Không tìm thấy file cập nhật"}), 404
    
    # Gửi file về client
    return send_file(file_path, as_attachment=True)

@app.route("/")
def index():
    \"\"\"Trang chủ\"\"\"
    return jsonify({
        "name": "Trading Bot Update Server",
        "version": "1.0.0",
        "endpoints": [
            "/updates/check",
            "/updates/download"
        ]
    })

if __name__ == "__main__":
    # Tải thông tin các phiên bản
    load_versions()
    
    # Chạy server
    app.run(host="0.0.0.0", port=5000, debug=True)
""")
            
            logger.info("Đã tạo file update_server.py")
        
        # Tạo thư mục dist nếu chưa tồn tại
        if not os.path.exists("dist"):
            os.makedirs("dist")
        
        # Tạo file versions.json nếu chưa tồn tại
        versions_file = os.path.join("dist", "versions.json")
        
        if not os.path.exists(versions_file):
            version = get_current_version()
            
            versions_data = {
                "latest": version,
                "versions": {
                    version: {
                        "release_date": datetime.now().strftime("%Y-%m-%d"),
                        "changes": ["Phiên bản đầu tiên"],
                        "filename": f"TradingBot_v{version}.exe"
                    }
                }
            }
            
            with open(versions_file, "w") as f:
                json.dump(versions_data, f, indent=4)
            
            logger.info(f"Đã tạo file versions.json với phiên bản {version}")
        
        logger.info("Đã hoàn thành tạo công cụ cập nhật tự động")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo công cụ cập nhật tự động: {str(e)}", exc_info=True)
        return False

def main():
    """Hàm chính"""
    logger.info("Đang bắt đầu quá trình đóng gói...")
    
    # Tạo công cụ cập nhật tự động
    if create_auto_updater():
        logger.info("Đã tạo công cụ cập nhật tự động thành công")
    else:
        logger.error("Không thể tạo công cụ cập nhật tự động")
    
    # Tạo file thực thi
    if create_executable():
        logger.info("Đã tạo file thực thi thành công")
    else:
        logger.error("Không thể tạo file thực thi")

def save_config(config, file_path):
    """
    Lưu cấu hình ra file JSON
    
    :param config: Dict cấu hình
    :param file_path: Đường dẫn file
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def load_config(file_path):
    """
    Tải cấu hình từ file JSON
    
    :param file_path: Đường dẫn file
    :return: Dict cấu hình
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

if __name__ == "__main__":
    main()