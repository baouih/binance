#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Đóng gói ứng dụng desktop bao gồm kết quả backtest
=============================================

Script này đóng gói ứng dụng desktop thành file .exe cho Windows
với đầy đủ kết quả backtest để người dùng có thể chạy trên máy tính cá nhân.

Sử dụng pyinstaller để đóng gói ứng dụng.
"""

import os
import sys
import shutil
import platform
import subprocess
import logging
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("package_desktop_app")

# Các thư mục cần đóng gói
DESKTOP_APP_DIR = "desktop_app"
OUTPUT_DIR = "dist"
BUILD_DIR = "build"

# Yêu cầu cập nhật kết quả backtest trước khi đóng gói
def update_backtest_results():
    """Cập nhật kết quả backtest vào ứng dụng desktop"""
    try:
        logger.info("Đang cập nhật kết quả backtest...")
        subprocess.run(["python", "update_desktop_backtest_results.py"], check=True)
        logger.info("Đã cập nhật kết quả backtest thành công")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Lỗi khi cập nhật kết quả backtest: {e}")
        return False

# Hàm kiểm tra môi trường 
def check_environment():
    """Kiểm tra môi trường phù hợp để đóng gói"""
    # Kiểm tra hệ điều hành
    os_name = platform.system()
    if os_name != "Windows":
        logger.warning(f"Hệ điều hành {os_name} không phải Windows. Đóng gói có thể không hoạt động đúng.")
    
    # Kiểm tra PyInstaller
    try:
        import PyInstaller
        logger.info(f"Đã tìm thấy PyInstaller phiên bản {PyInstaller.__version__}")
    except ImportError:
        logger.error("Không tìm thấy PyInstaller. Hãy cài đặt bằng lệnh: pip install pyinstaller")
        return False
    
    # Kiểm tra PyQt5
    try:
        from PyQt5.QtWidgets import QApplication
        logger.info("Đã tìm thấy PyQt5")
    except ImportError:
        logger.error("Không tìm thấy PyQt5. Hãy cài đặt bằng lệnh: pip install pyqt5")
        return False
    
    return True

# Hàm tạo file spec cho PyInstaller
def create_spec_file():
    """Tạo file .spec cho PyInstaller"""
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

desktop_app_files = [
    ('desktop_app/assets/*', 'assets'),
    ('desktop_app/reports/*', 'reports'),
    ('desktop_app/backtest_results/*', 'backtest_results'),
    ('desktop_app/gui_config.json', '.'),
]

a = Analysis(
    ['enhanced_trading_gui.py'],
    pathex=[],
    binaries=[],
    datas=desktop_app_files,
    hiddenimports=['PyQt5.sip'],
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
    [],
    exclude_binaries=True,
    name='TradingSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TradingSystem',
)
"""
    
    with open("trading_system.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    logger.info("Đã tạo file spec cho PyInstaller")
    return True

# Hàm chính để đóng gói ứng dụng
def package_app():
    """Đóng gói ứng dụng desktop thành file exe"""
    # Kiểm tra môi trường
    if not check_environment():
        logger.error("Không thể đóng gói do môi trường không phù hợp")
        return False
    
    # Cập nhật kết quả backtest
    if not update_backtest_results():
        logger.error("Không thể cập nhật kết quả backtest")
        return False
    
    # Tạo file spec
    if not create_spec_file():
        logger.error("Không thể tạo file spec")
        return False
    
    # Chạy PyInstaller
    logger.info("Đang đóng gói ứng dụng...")
    try:
        subprocess.run(["pyinstaller", "--clean", "trading_system.spec"], check=True)
        logger.info("Đã đóng gói ứng dụng thành công")
    except subprocess.CalledProcessError as e:
        logger.error(f"Lỗi khi đóng gói ứng dụng: {e}")
        return False
    
    # Kiểm tra kết quả
    if os.path.exists(os.path.join(OUTPUT_DIR, "TradingSystem", "TradingSystem.exe")):
        logger.info(f"Ứng dụng đã được đóng gói thành công tại {os.path.join(OUTPUT_DIR, 'TradingSystem')}")
        return True
    else:
        logger.error("Không tìm thấy file .exe sau khi đóng gói")
        return False

# Hàm tạo file readme hướng dẫn cài đặt
def create_readme():
    """Tạo file README hướng dẫn cài đặt và sử dụng"""
    readme_content = """# Hướng dẫn cài đặt và sử dụng Trading System

## Cài đặt
1. Giải nén file TradingSystem.zip vào một thư mục trên máy tính
2. Chạy file TradingSystem.exe để bắt đầu sử dụng

## Cấu hình
1. Mở tab "Cài đặt" trong ứng dụng
2. Nhập API key và API secret của Binance
3. Chọn chiến lược giao dịch và mức độ rủi ro phù hợp
4. Nhấn "Lưu cấu hình" để lưu lại các thay đổi

## Xem kết quả backtest
1. Mở tab "Backtest" trong ứng dụng
2. Xem thông tin chi tiết về hiệu suất các chiến lược
3. Chọn xem báo cáo chi tiết trong các tab con

## Giao dịch
1. Mở tab "Giao dịch" trong ứng dụng
2. Chọn cặp tiền và chiến lược muốn giao dịch
3. Nhấn "Bắt đầu giao dịch" để bắt đầu

## Khắc phục sự cố
- Nếu gặp lỗi "Unable to load API key", hãy kiểm tra lại cấu hình API key trong tab "Cài đặt"
- Nếu ứng dụng không phản hồi, hãy khởi động lại ứng dụng

## Liên hệ hỗ trợ
- Email: support@tradingsystem.com
- Telegram: @tradingsystem_support
"""
    
    with open(os.path.join(OUTPUT_DIR, "TradingSystem", "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    logger.info("Đã tạo file README hướng dẫn cài đặt và sử dụng")
    return True

# Hàm tạo file ZIP để phân phối
def create_zip():
    """Tạo file ZIP để phân phối"""
    try:
        import zipfile
        
        # Tạo thư mục nếu không tồn tại
        if not os.path.exists("dist_packages"):
            os.makedirs("dist_packages")
        
        # Tên file ZIP
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"dist_packages/TradingSystem_{timestamp}.zip"
        
        # Tạo file ZIP
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(os.path.join(OUTPUT_DIR, "TradingSystem")):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.join(OUTPUT_DIR))
                    zipf.write(file_path, arcname)
        
        logger.info(f"Đã tạo file ZIP tại {zip_filename}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo file ZIP: {e}")
        return False

# Hàm chính
def main():
    """Hàm chính để đóng gói ứng dụng desktop"""
    logger.info("Bắt đầu đóng gói ứng dụng desktop...")
    
    # Đóng gói ứng dụng
    if not package_app():
        logger.error("Đóng gói không thành công")
        return False
    
    # Tạo file README
    if not create_readme():
        logger.warning("Không thể tạo file README")
    
    # Tạo file ZIP
    if not create_zip():
        logger.warning("Không thể tạo file ZIP")
    
    logger.info("Đã hoàn thành đóng gói ứng dụng desktop")
    return True

if __name__ == "__main__":
    main()