#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module đóng gói ứng dụng desktop thành file exe
"""

import os
import sys
import shutil
import logging
import subprocess
import json
import argparse
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('package_desktop_app')

def create_directories():
    """Tạo các thư mục cần thiết"""
    directories = [
        "dist",
        "build",
        "static",
        "static/img",
        "configs",
        "risk_configs",
        "logs"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Đã tạo thư mục {directory}")

def create_icon():
    """Tạo biểu tượng cho ứng dụng"""
    if not os.path.exists("static/img/icon.ico"):
        # Sử dụng biểu tượng mặc định nếu có
        if os.path.exists("static/img/icon.png"):
            try:
                from PIL import Image
                img = Image.open("static/img/icon.png")
                img.save("static/img/icon.ico")
                logger.info("Đã tạo biểu tượng từ file PNG")
            except Exception as e:
                logger.error(f"Không thể tạo biểu tượng: {str(e)}")
                # Sử dụng biểu tượng có sẵn
                if os.path.exists("static/img/default_icon.ico"):
                    shutil.copy("static/img/default_icon.ico", "static/img/icon.ico")
                    logger.info("Đã sử dụng biểu tượng mặc định")
        else:
            logger.warning("Không tìm thấy file icon.png")

def copy_config_files():
    """Sao chép các tệp cấu hình"""
    # Tạo tệp cấu hình mẫu nếu chưa có
    if not os.path.exists("account_config.json"):
        # Tạo tệp cấu hình mẫu
        default_config = {
            "risk_level": 10,  # Mức rủi ro mặc định (10%, 15%, 20%, 30%)
            "symbols": ["BTCUSDT", "ETHUSDT"],  # Các cặp tiền mặc định
            "timeframes": ["1h", "4h"],  # Khung thời gian mặc định
            "testnet": True,  # Sử dụng testnet
            "telegram_notifications": True,  # Bật thông báo Telegram
            "quiet_hours": {  # Giờ không làm phiền
                "enabled": False,
                "start": "22:00",
                "end": "07:00"
            },
            "auto_trailing_stop": True,  # Tự động trailing stop
            "language": "vi",  # Ngôn ngữ giao diện
            "auto_update": True,  # Tự động cập nhật
            "update_frequency": 24  # Tần suất kiểm tra cập nhật (giờ)
        }
        
        with open("account_config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        
        logger.info("Đã tạo tệp cấu hình mẫu account_config.json")
    
    # Sao chép tệp cấu hình vào thư mục dist
    config_files = [
        "account_config.json"
    ]
    
    for file in config_files:
        if os.path.exists(file):
            shutil.copy(file, f"dist/{file}")
            logger.info(f"Đã sao chép {file} vào thư mục dist")
    
    # Tạo các tệp cấu hình rủi ro
    if not os.path.exists("risk_configs"):
        os.makedirs("risk_configs")
    
    risk_levels = [10, 15, 20, 30]
    
    for level in risk_levels:
        risk_file = f"risk_configs/risk_level_{level}.json"
        
        if not os.path.exists(risk_file):
            # Tạo cấu hình dựa trên mức độ rủi ro
            risk_config = {
                "risk_percentage": level / 100,  # Chuyển thành tỷ lệ phần trăm
                "max_positions": 5 if level <= 15 else (4 if level <= 20 else 3),
                "leverage": int(level * 0.5) if level <= 20 else int(level * 0.7),  # Đòn bẩy tăng theo mức rủi ro
                "position_size_percentage": level / 100,
                "partial_take_profit": {
                    "enabled": level > 15,
                    "levels": [
                        {"percentage": 30, "profit_percentage": 2},
                        {"percentage": 30, "profit_percentage": 5},
                        {"percentage": 40, "profit_percentage": 10}
                    ]
                },
                "stop_loss_percentage": level / 100 * 1.5,  # SL tỷ lệ với mức rủi ro
                "take_profit_percentage": level / 100 * 3,  # TP tỷ lệ với mức rủi ro
                "trailing_stop": {
                    "enabled": True,
                    "activation_percentage": 2,
                    "trailing_percentage": 1.5
                },
                "trading_hours_restriction": {
                    "enabled": level <= 15,  # Chỉ bật cho mức rủi ro thấp
                    "trading_hours": ["09:00-12:00", "14:00-21:00"]
                }
            }
            
            with open(risk_file, "w", encoding="utf-8") as f:
                json.dump(risk_config, f, indent=4)
            
            logger.info(f"Đã tạo tệp cấu hình rủi ro {risk_file}")
    
    # Sao chép thư mục risk_configs vào dist
    if os.path.exists("risk_configs"):
        if os.path.exists("dist/risk_configs"):
            shutil.rmtree("dist/risk_configs")
        shutil.copytree("risk_configs", "dist/risk_configs")
        logger.info("Đã sao chép thư mục risk_configs vào dist")
    
    # Tạo các thư mục cần thiết trong dist
    for directory in ["configs", "logs", "static/img"]:
        if not os.path.exists(f"dist/{directory}"):
            os.makedirs(f"dist/{directory}")
            logger.info(f"Đã tạo thư mục dist/{directory}")

def create_version_file():
    """Tạo tệp phiên bản"""
    version_info = {
        "version": "1.0.0",
        "build_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "build_id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "update_url": "https://example.com/updates/crypto_trading_bot"
    }
    
    with open("dist/version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=4)
    
    logger.info("Đã tạo tệp phiên bản version.json")

def create_auto_updater():
    """Tạo tệp auto updater"""
    updater_code = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Module tự động cập nhật ứng dụng
\"\"\"

import os
import sys
import json
import shutil
import logging
import requests
import subprocess
import zipfile
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='auto_updater.log'
)
logger = logging.getLogger('auto_updater')

def check_for_updates():
    \"\"\"Kiểm tra cập nhật mới\"\"\"
    try:
        logger.info("Đang kiểm tra cập nhật...")
        
        # Đọc thông tin phiên bản hiện tại
        if not os.path.exists("version.json"):
            logger.error("Không tìm thấy tệp version.json")
            return False
        
        with open("version.json", "r", encoding="utf-8") as f:
            current_version = json.load(f)
        
        # Kiểm tra phiên bản mới từ máy chủ
        update_url = current_version.get("update_url")
        if not update_url:
            logger.error("Không có URL cập nhật trong tệp version.json")
            return False
        
        # Tải thông tin phiên bản mới
        try:
            response = requests.get(f"{update_url}/version.json", timeout=10)
            response.raise_for_status()
            latest_version = response.json()
        except Exception as e:
            logger.error(f"Không thể tải thông tin phiên bản mới: {str(e)}")
            return False
        
        # So sánh phiên bản
        if latest_version.get("version") == current_version.get("version"):
            logger.info("Đã sử dụng phiên bản mới nhất")
            return False
        
        # Nếu có phiên bản mới, tải xuống
        logger.info(f"Đã tìm thấy phiên bản mới: {latest_version.get('version')}")
        
        # Tải gói cập nhật
        try:
            response = requests.get(f"{update_url}/update.zip", timeout=60)
            response.raise_for_status()
            
            # Lưu gói cập nhật
            with open("update.zip", "wb") as f:
                f.write(response.content)
            
            logger.info("Đã tải gói cập nhật")
            return True
        except Exception as e:
            logger.error(f"Không thể tải gói cập nhật: {str(e)}")
            return False
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra cập nhật: {str(e)}")
        return False

def install_update():
    \"\"\"Cài đặt cập nhật\"\"\"
    try:
        logger.info("Đang cài đặt cập nhật...")
        
        # Kiểm tra tệp cập nhật
        if not os.path.exists("update.zip"):
            logger.error("Không tìm thấy tệp update.zip")
            return False
        
        # Tạo thư mục tạm
        if os.path.exists("update_temp"):
            shutil.rmtree("update_temp")
        os.makedirs("update_temp")
        
        # Giải nén gói cập nhật
        with zipfile.ZipFile("update.zip", "r") as zip_ref:
            zip_ref.extractall("update_temp")
        
        logger.info("Đã giải nén gói cập nhật")
        
        # Sao chép các tệp cập nhật
        # Danh sách các tệp không cập nhật
        excluded_files = ["account_config.json", "configs", "logs"]
        
        for item in os.listdir("update_temp"):
            src_path = os.path.join("update_temp", item)
            dst_path = os.path.join(".", item)
            
            if item in excluded_files:
                continue
            
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
        
        logger.info("Đã sao chép các tệp cập nhật")
        
        # Xóa các tệp tạm
        shutil.rmtree("update_temp")
        os.remove("update.zip")
        
        logger.info("Cài đặt cập nhật thành công")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi cài đặt cập nhật: {str(e)}")
        return False

def main():
    \"\"\"Hàm chính\"\"\"
    try:
        logger.info("Auto Updater đã khởi động")
        
        # Kiểm tra cập nhật
        if check_for_updates():
            # Cài đặt cập nhật
            if install_update():
                logger.info("Cập nhật thành công, khởi động lại ứng dụng...")
                
                # Khởi động lại ứng dụng
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                logger.error("Không thể cài đặt cập nhật")
        
        logger.info("Auto Updater đã kết thúc")
    
    except Exception as e:
        logger.error(f"Lỗi không xác định: {str(e)}")

if __name__ == "__main__":
    main()
"""
    
    with open("dist/auto_updater.py", "w", encoding="utf-8") as f:
        f.write(updater_code)
    
    logger.info("Đã tạo tệp auto_updater.py")

def create_launcher():
    """Tạo tệp khởi động"""
    launcher_code = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Module khởi động ứng dụng
\"\"\"

import os
import sys
import json
import logging
import subprocess
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='launcher.log'
)
logger = logging.getLogger('launcher')

def check_requirements():
    \"\"\"Kiểm tra các yêu cầu\"\"\"
    try:
        # Đảm bảo các thư mục cần thiết tồn tại
        for directory in ["configs", "logs", "risk_configs", "static/img"]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Đã tạo thư mục {directory}")
        
        # Kiểm tra tệp cấu hình
        if not os.path.exists("account_config.json"):
            # Tạo tệp cấu hình mẫu
            default_config = {
                "risk_level": 10,
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "timeframes": ["1h", "4h"],
                "testnet": True,
                "telegram_notifications": True,
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "07:00"
                },
                "auto_trailing_stop": True,
                "language": "vi",
                "auto_update": True,
                "update_frequency": 24
            }
            
            with open("account_config.json", "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            
            logger.info("Đã tạo tệp cấu hình mẫu account_config.json")
        
        # Kiểm tra auto updater
        if os.path.exists("auto_updater.py") and os.path.exists("version.json"):
            # Đọc cấu hình
            with open("account_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Kiểm tra cài đặt tự động cập nhật
            if config.get("auto_update", True):
                logger.info("Đang chạy auto updater...")
                subprocess.run([sys.executable, "auto_updater.py"])
        
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra yêu cầu: {str(e)}")
        return False

def run_app():
    \"\"\"Chạy ứng dụng\"\"\"
    try:
        logger.info("Đang khởi động ứng dụng...")
        
        # Kiểm tra tệp ứng dụng chính
        if not os.path.exists("run_desktop_app.py"):
            logger.error("Không tìm thấy tệp run_desktop_app.py")
            return False
        
        # Chạy ứng dụng
        subprocess.run([sys.executable, "run_desktop_app.py"])
        
        logger.info("Ứng dụng đã đóng")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy ứng dụng: {str(e)}")
        return False

def main():
    \"\"\"Hàm chính\"\"\"
    try:
        logger.info("Launcher đã khởi động")
        
        # Kiểm tra yêu cầu
        if check_requirements():
            # Chạy ứng dụng
            run_app()
        
        logger.info("Launcher đã kết thúc")
    
    except Exception as e:
        logger.error(f"Lỗi không xác định: {str(e)}")

if __name__ == "__main__":
    main()
"""
    
    with open("dist/launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_code)
    
    logger.info("Đã tạo tệp launcher.py")

def create_windows_batch_file():
    """Tạo tệp batch cho Windows"""
    batch_code = """@echo off
start pythonw launcher.py
"""
    
    with open("dist/Crypto_Trading_Bot.bat", "w") as f:
        f.write(batch_code)
    
    logger.info("Đã tạo tệp Crypto_Trading_Bot.bat")

def copy_source_files():
    """Sao chép các tệp mã nguồn"""
    # Danh sách các tệp cần sao chép
    source_files = [
        "run_desktop_app.py",
        "enhanced_trading_gui.py",
        "market_analyzer.py",
        "signal_generator.py",
        "position_manager.py",
        "risk_manager.py",
        "trading_bot.py",
        "advanced_telegram_notifier.py",
        "api_data_validator.py",
        "config_loader.py"
    ]
    
    for file in source_files:
        if os.path.exists(file):
            shutil.copy(file, f"dist/{file}")
            logger.info(f"Đã sao chép {file} vào thư mục dist")
        else:
            logger.warning(f"Không tìm thấy tệp {file}")
    
    # Sao chép thư mục static
    if os.path.exists("static"):
        if os.path.exists("dist/static"):
            # Chỉ sao chép các tệp, không xóa thư mục hiện có
            for item in os.listdir("static"):
                src_path = os.path.join("static", item)
                dst_path = os.path.join("dist/static", item)
                
                if os.path.isdir(src_path):
                    if os.path.exists(dst_path):
                        # Đối với thư mục, sao chép từng tệp
                        for subitem in os.listdir(src_path):
                            src_subpath = os.path.join(src_path, subitem)
                            dst_subpath = os.path.join(dst_path, subitem)
                            
                            if os.path.isfile(src_subpath):
                                shutil.copy2(src_subpath, dst_subpath)
                    else:
                        shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
        else:
            shutil.copytree("static", "dist/static")
        
        logger.info("Đã sao chép thư mục static vào dist")

def create_requirements_file():
    """Tạo tệp requirements.txt"""
    requirements = """
python-binance>=1.0.16
PyQt5>=5.15.4
requests>=2.25.1
python-dotenv>=0.17.1
Pillow>=8.2.0
matplotlib>=3.4.2
pandas>=1.3.0
numpy>=1.20.3
joblib>=1.0.1
scikit-learn>=0.24.2
    """
    
    with open("requirements.txt", "w") as f:
        f.write(requirements.strip())
    
    logger.info("Đã tạo tệp requirements.txt")

def create_spec_file():
    """Tạo tệp spec cho PyInstaller"""
    spec_code = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['launcher.py'],
             pathex=['.'],
             binaries=[],
             datas=[
                ('static', 'static'),
                ('risk_configs', 'risk_configs'),
                ('configs', 'configs'),
                ('account_config.json', '.'),
                ('version.json', '.'),
                ('auto_updater.py', '.'),
                ('run_desktop_app.py', '.'),
                ('enhanced_trading_gui.py', '.'),
                ('market_analyzer.py', '.'),
                ('signal_generator.py', '.'),
                ('position_manager.py', '.'),
                ('risk_manager.py', '.'),
                ('trading_bot.py', '.'),
                ('advanced_telegram_notifier.py', '.'),
                ('api_data_validator.py', '.'),
                ('config_loader.py', '.')
             ],
             hiddenimports=[
                'PyQt5',
                'PyQt5.QtWidgets',
                'PyQt5.QtCore',
                'PyQt5.QtGui',
                'python-binance',
                'requests',
                'json',
                'logging',
                'datetime',
                'time',
                'os',
                'sys',
                'threading'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Crypto_Trading_Bot',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='static/img/icon.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Crypto_Trading_Bot')
"""
    
    with open("launcher.spec", "w") as f:
        f.write(spec_code)
    
    logger.info("Đã tạo tệp launcher.spec")

def create_executable():
    """Tạo tệp thực thi"""
    try:
        # Cài đặt PyInstaller nếu chưa có
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        
        # Sao chép các tệp cần thiết vào thư mục dist
        shutil.copy("launcher.py", "dist/launcher.py")
        
        if os.path.exists("requirements.txt"):
            shutil.copy("requirements.txt", "dist/requirements.txt")
        
        # Thay đổi thư mục làm việc
        os.chdir("dist")
        
        # Tạo tệp thực thi
        subprocess.run(["pyinstaller", "--onedir", "--windowed", "--icon=static/img/icon.ico", "launcher.py", "--name=Crypto_Trading_Bot"], check=True)
        
        logger.info("Đã tạo tệp thực thi thành công")
        return True
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo tệp thực thi: {str(e)}")
        return False

def build_package():
    """Đóng gói ứng dụng"""
    try:
        # Tạo thư mục nén
        output_dir = f"Crypto_Trading_Bot_v1.0.0_{datetime.now().strftime('%Y%m%d')}"
        
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        
        # Sao chép thư mục dist/Crypto_Trading_Bot vào thư mục nén
        if os.path.exists("dist/Crypto_Trading_Bot"):
            shutil.copytree("dist/Crypto_Trading_Bot", output_dir)
            
            # Sao chép tệp batch
            if os.path.exists("dist/Crypto_Trading_Bot.bat"):
                shutil.copy("dist/Crypto_Trading_Bot.bat", output_dir)
            
            # Tạo tệp README.txt
            readme_content = """Crypto Trading Bot v1.0.0
===================================

HƯỚNG DẪN CÀI ĐẶT
-----------------
1. Giải nén toàn bộ thư mục này vào nơi bạn muốn lưu ứng dụng.
2. Chạy tệp "Crypto_Trading_Bot.bat" để khởi động ứng dụng.
3. Nếu là lần đầu chạy, ứng dụng sẽ tạo các tệp cấu hình mặc định.
4. Trong ứng dụng, vào tab "Cài đặt" để thiết lập API key và các tham số giao dịch.

YÊU CẦU HỆ THỐNG
----------------
- Windows 10 hoặc cao hơn
- Kết nối Internet ổn định

LƯU Ý
-----
- Đây là phiên bản sử dụng Testnet, không giao dịch bằng tiền thật.
- Hãy đảm bảo bạn đã đọc kỹ hướng dẫn trước khi giao dịch.
- Sử dụng ứng dụng với mục đích thử nghiệm và học tập.

LIÊN HỆ HỖ TRỢ
-------------
Email: support@example.com
"""
            with open(f"{output_dir}/README.txt", "w", encoding="utf-8") as f:
                f.write(readme_content)
            
            # Nén thư mục
            import zipfile
            zip_file = f"{output_dir}.zip"
            
            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(output_dir)))
            
            logger.info(f"Đã đóng gói ứng dụng thành công: {zip_file}")
            return True
        else:
            logger.error("Không tìm thấy thư mục dist/Crypto_Trading_Bot")
            return False
    
    except Exception as e:
        logger.error(f"Lỗi khi đóng gói ứng dụng: {str(e)}")
        return False

def main():
    """Hàm chính"""
    logger.info("===== Bắt đầu đóng gói ứng dụng =====")
    
    parser = argparse.ArgumentParser(description="Đóng gói ứng dụng thành file exe")
    parser.add_argument("--build-only", action="store_true", help="Chỉ tạo cấu trúc thư mục và các tệp cần thiết")
    parser.add_argument("--package-only", action="store_true", help="Chỉ đóng gói từ thư mục dist hiện có")
    args = parser.parse_args()
    
    if args.package_only:
        # Chỉ đóng gói từ thư mục dist hiện có
        if os.path.exists("dist"):
            os.chdir("dist")
            build_package()
        else:
            logger.error("Không tìm thấy thư mục dist")
        return
    
    # Tạo các thư mục cần thiết
    create_directories()
    
    # Tạo biểu tượng
    create_icon()
    
    # Sao chép các tệp cấu hình
    copy_config_files()
    
    # Tạo tệp phiên bản
    create_version_file()
    
    # Tạo tệp auto updater
    create_auto_updater()
    
    # Tạo tệp khởi động
    create_launcher()
    
    # Tạo tệp batch
    create_windows_batch_file()
    
    # Sao chép các tệp mã nguồn
    copy_source_files()
    
    # Tạo tệp requirements.txt
    create_requirements_file()
    
    # Tạo tệp spec
    create_spec_file()
    
    if not args.build_only:
        # Tạo tệp thực thi
        if create_executable():
            # Đóng gói ứng dụng
            build_package()
    
    logger.info("===== Kết thúc đóng gói ứng dụng =====")

if __name__ == "__main__":
    main()