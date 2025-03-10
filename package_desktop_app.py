#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script đóng gói ứng dụng desktop thành file thực thi (.exe)
"""

import os
import sys
import subprocess
import shutil
import logging
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("packaging.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("packaging")

def create_executable():
    """
    Tạo file thực thi từ ứng dụng Python
    """
    logger.info("Bắt đầu đóng gói ứng dụng desktop thành file thực thi...")
    
    # Tạo thư mục dist nếu chưa tồn tại
    os.makedirs("dist", exist_ok=True)
    
    # Tên file spec
    spec_file = "crypto_trading_bot.spec"
    
    # Tạo file spec cho PyInstaller
    with open(spec_file, "w") as f:
        f.write("""# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Thu thập tất cả submodule cần thiết
modules = collect_submodules('PyQt5')
modules += collect_submodules('ccxt')
modules += collect_submodules('pandas')
modules += collect_submodules('numpy')
modules += collect_submodules('matplotlib')
modules += collect_submodules('requests')

# Thu thập data files
datas = collect_data_files('templates')
datas += collect_data_files('static')
datas += collect_data_files('risk_configs')
datas += collect_data_files('configs')

# Thêm thư mục gốc vào datas
datas += [('.env.example', '.')]
datas += [('README.md', '.')]

a = Analysis(
    ['run_desktop_app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=modules,
    hookspath=[],
    hooksconfig={},
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
    name='CryptoTradingBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/img/icon.ico' if os.path.exists('static/img/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CryptoTradingBot',
)
""")
    
    # Chạy PyInstaller
    logger.info("Đang chạy PyInstaller để tạo file thực thi...")
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", spec_file, "--clean"], 
                      check=True, capture_output=True, text=True)
        logger.info("Đã chạy PyInstaller thành công")
    except subprocess.CalledProcessError as e:
        logger.error(f"Lỗi khi chạy PyInstaller: {str(e)}")
        logger.error(f"Output: {e.output}")
        logger.error(f"Stderr: {e.stderr}")
        return False
    
    # Tạo file README trong thư mục dist
    try:
        dist_readme = os.path.join("dist", "CryptoTradingBot", "README.txt")
        with open(dist_readme, "w", encoding="utf-8") as f:
            f.write("""# Crypto Trading Bot

## Hướng dẫn sử dụng

1. Tạo file `.env` trong thư mục này với nội dung tương tự như `.env.example`
2. Thêm API Key và Secret của Binance vào file `.env`:
   ```
   BINANCE_TESTNET_API_KEY=your_api_key
   BINANCE_TESTNET_API_SECRET=your_api_secret
   ```
3. Thêm thông tin Bot Telegram (nếu sử dụng):
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
4. Chạy file `CryptoTradingBot.exe` để khởi động ứng dụng

## Cấu hình

- Cấu hình rủi ro: Trong thư mục `risk_configs`
- Cấu hình khác: Trong thư mục `configs`

## Hỗ trợ

Nếu cần hỗ trợ, vui lòng liên hệ nhà phát triển.
""")
        logger.info(f"Đã tạo file README tại {dist_readme}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo file README: {str(e)}")
    
    # Tạo file .env.example
    try:
        env_example = os.path.join("dist", "CryptoTradingBot", ".env.example")
        if not os.path.exists(env_example):
            with open(env_example, "w", encoding="utf-8") as f:
                f.write("""# Binance API (Testnet)
BINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Cấu hình hệ thống
AUTO_RESTART=true
DEBUG_MODE=false
LOG_LEVEL=INFO
""")
            logger.info(f"Đã tạo file .env.example tại {env_example}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo file .env.example: {str(e)}")
    
    # Tạo thư mục cần thiết trong dist
    for folder in ["logs", "data", "results"]:
        try:
            os.makedirs(os.path.join("dist", "CryptoTradingBot", folder), exist_ok=True)
            logger.info(f"Đã tạo thư mục {folder}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo thư mục {folder}: {str(e)}")
    
    # Tạo zip file
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"CryptoTradingBot_{timestamp}.zip"
        shutil.make_archive(
            os.path.join("dist", f"CryptoTradingBot_{timestamp}"),
            'zip',
            os.path.join("dist", "CryptoTradingBot")
        )
        logger.info(f"Đã tạo file zip: dist/{zip_filename}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo file zip: {str(e)}")
    
    logger.info("Quá trình đóng gói hoàn tất!")
    logger.info(f"File thực thi được tạo tại: dist/CryptoTradingBot/CryptoTradingBot.exe")
    return True

if __name__ == "__main__":
    create_executable()