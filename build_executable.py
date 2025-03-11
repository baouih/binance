#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build Executable - Tạo file thực thi cho hệ thống giao dịch
"""

import os
import sys
import shutil
import logging
import argparse
import subprocess
import platform
import zipfile
import json
from datetime import datetime

# Tạo thư mục logs nếu chưa tồn tại
os.makedirs("logs", exist_ok=True)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/build.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('build_executable')

# Danh sách các module cần thiết cho việc biên dịch
REQUIRED_MODULES = [
    'pyinstaller',
    'numpy',
    'pandas',
    'matplotlib',
    'PyQt5',
    'ccxt',
    'python-binance',
    'scikit-learn',
    'joblib',
    'scipy',
    'flask',
    'werkzeug',
    'flask-sqlalchemy',
    'flask-login',
    'requests',
    'cryptography',
]

# Danh sách các file và thư mục cần được đóng gói
FILES_TO_INCLUDE = [
    'account_config.json',
    'risk_level_manager.py',
    'bot_gui.py',
    'main.py',
    'feature_fusion_pipeline.py',
    'build_executable.py',
    'bot_startup.py',
    'README.md',
]

# Thư mục cần được đóng gói
FOLDERS_TO_INCLUDE = [
    'strategies',
    'risk_configs',
    'ml_models',
    'data',
    'templates',
    'static',
    'logs',
    'update_packages',
]

# Icon cho ứng dụng (với đường dẫn phụ thuộc vào OS)
ICON_PATH = 'static/images/bot_icon.ico' if platform.system() == 'Windows' else 'static/images/bot_icon.png'

# Spec file cho PyInstaller
PYINSTALLER_SPEC = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Danh sách các file dữ liệu cần đóng gói
datas = [
    ('account_config.json', '.'),
    ('bot_settings.json', '.'),
    ('risk_configs', 'risk_configs'),
    ('strategies', 'strategies'),
    ('ml_models', 'ml_models'),
    ('data', 'data'),
    ('static', 'static'),
    ('templates', 'templates'),
    ('update_packages', 'update_packages'),
]

# Các module ẩn cần đóng gói
hidden_imports = [
    # Core dependencies
    'numpy',
    'pandas',
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.dates',
    'matplotlib.backends.backend_qt5agg',
    
    # Machine learning
    'sklearn',
    'sklearn.decomposition',
    'sklearn.preprocessing',
    'sklearn.pipeline',
    'sklearn.feature_selection',
    'sklearn.impute',
    'sklearn.base',
    'sklearn.manifold',
    'sklearn.feature_selection',
    'joblib',
    
    # Trading & Data
    'ccxt',
    'binance',
    'binance.client',
    'binance.enums',
    'binance.exceptions',
    'binance.streams',
    
    # GUI
    'PyQt5',
    'PyQt5.QtWidgets',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtChart',
    
    # Web 
    'flask',
    'flask_sqlalchemy',
    'flask_login',
    'werkzeug',
    'werkzeug.security',
    'jinja2',
    
    # Utilities
    'logging',
    'json',
    'datetime',
    'requests',
    'urllib',
    'sqlite3',
    'threading',
    'subprocess',
    'shutil',
    'os',
    'sys',
    're',
    'time',
    'uuid',
    'hashlib',
    'base64',
    'io',
    'zipfile',
    'scipy',
]

a = Analysis(
    ['bot_gui.py'],  # Sử dụng bot_gui.py làm entry point
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
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

# Tạo file exe riêng biệt
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TradingBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # False để ẩn cửa sổ console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{ICON_PATH}',
)

# Thư mục chứa các file đóng gói
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TradingBot',
)

# Tạo file exe đơn lẻ (one-file)
exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TradingBot_OneFile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False để ẩn cửa sổ console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{ICON_PATH}',
)
"""

def check_and_install_requirements():
    """Kiểm tra và cài đặt các module cần thiết"""
    logger.info("Kiểm tra các module cần thiết...")
    
    for module in REQUIRED_MODULES:
        try:
            __import__(module)
            logger.info(f"Module {module} đã được cài đặt")
        except ImportError:
            logger.info(f"Đang cài đặt module {module}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                logger.info(f"Đã cài đặt thành công module {module}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Lỗi khi cài đặt module {module}: {str(e)}")
                return False
    
    return True

def create_spec_file():
    """Tạo file spec cho PyInstaller"""
    try:
        with open("trading_bot.spec", "w") as f:
            f.write(PYINSTALLER_SPEC)
        logger.info("Đã tạo file spec thành công")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi tạo file spec: {str(e)}")
        return False

def prepare_build_folders():
    """Chuẩn bị các thư mục cần thiết cho việc build"""
    try:
        # Tạo thư mục build nếu chưa tồn tại
        if not os.path.exists("build"):
            os.makedirs("build")
        
        # Tạo các thư mục cần thiết
        for folder in FOLDERS_TO_INCLUDE:
            if not os.path.exists(folder):
                os.makedirs(folder)
                logger.info(f"Đã tạo thư mục {folder}")
        
        # Tạo file icon nếu chưa tồn tại
        icon_dir = "static/images"
        if not os.path.exists(icon_dir):
            os.makedirs(icon_dir)
        
        if not os.path.exists(f"{icon_dir}/bot_icon.ico"):
            # Tạo icon mặc định
            create_default_icon(f"{icon_dir}/bot_icon.ico")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi chuẩn bị thư mục: {str(e)}")
        return False

def create_default_icon(file_path):
    """Tạo icon mặc định"""
    try:
        from PIL import Image, ImageDraw
        
        # Tạo hình vuông 256x256 làm icon
        img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Vẽ biểu tượng đơn giản
        draw.rectangle([(48, 48), (208, 208)], fill=(0, 120, 212))
        draw.rectangle([(78, 78), (178, 178)], fill=(255, 255, 255))
        draw.rectangle([(98, 98), (158, 158)], fill=(0, 120, 212))
        
        # Lưu như .ico
        img.save(file_path, format='ICO')
        logger.info(f"Đã tạo icon mặc định tại {file_path}")
        return True
    except ImportError:
        logger.warning("Không thể tạo icon mặc định, thiếu thư viện PIL")
        # Tạo file trống
        with open(file_path, 'wb') as f:
            f.write(b'')
        return False
    except Exception as e:
        logger.error(f"Lỗi khi tạo icon mặc định: {str(e)}")
        return False

def build_executable():
    """Build file thực thi"""
    try:
        logger.info("Đang build file thực thi...")
        
        # Chạy PyInstaller với spec file
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "trading_bot.spec", "--clean"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("Đã build thành công!")
            logger.info(f"Output:\n{result.stdout}")
            return True
        else:
            logger.error(f"Lỗi khi build: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi build file thực thi: {str(e)}")
        return False

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description='Build Executable Tool')
    parser.add_argument('--output', type=str, default='dist', help='Thư mục output')
    parser.add_argument('--onefile', action='store_true', help='Tạo một file duy nhất')
    parser.add_argument('--name', type=str, default='TradingBot', help='Tên file thực thi')
    parser.add_argument('--icon', type=str, help='Đường dẫn đến file icon')
    
    args = parser.parse_args()
    
    logger.info("===== Bắt đầu quá trình build file thực thi =====")
    
    # Kiểm tra và cài đặt requirements
    if not check_and_install_requirements():
        logger.error("Không thể cài đặt các module cần thiết")
        return 1
    
    # Chuẩn bị thư mục
    if not prepare_build_folders():
        logger.error("Không thể chuẩn bị thư mục build")
        return 1
    
    # Tạo spec file
    if not create_spec_file():
        logger.error("Không thể tạo file spec")
        return 1
    
    # Build executable
    if not build_executable():
        logger.error("Không thể build file thực thi")
        return 1
    
    logger.info("===== Hoàn tất quá trình build =====")
    logger.info(f"File thực thi được lưu tại: dist/{args.name}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())