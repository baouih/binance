#!/usr/bin/env python3
"""
Script tạo bản xuất phần mềm Bot Giao Dịch

Script này tạo package để triển khai trên máy cá nhân hoặc server riêng
"""

import os
import sys
import shutil
import zipfile
import glob
import datetime
import json
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Thư mục và file quan trọng cần đóng gói
IMPORTANT_DIRS = [
    'app', 'configs', 'models', 'routes', 'static', 'templates'
]

IMPORTANT_FILES = [
    # File chính
    'main.py', 'app.py', 'bot_api_routes.py', 'config_route.py', 
    
    # Script giám sát
    'auto_recovery.sh', 'watchdog.sh', 'watchdog_runner.sh', 
    'telegram_watchdog.py', 'update_status.sh', 'update_positions.sh',
    
    # Script phân tích
    'binance_api.py', 'enhanced_trailing_stop.py', 'data_processor.py',
    'composite_indicator.py', 'market_regime_detector.py',
    
    # Công cụ khôi phục
    'log_collector.py', 'remote_helper.py',
    
    # Cấu hình và trạng thái
    'bot_config.json', 'account_config.json', 'bot_status.json',
    
    # Tài liệu
    'README*.md', 'API_DOCS.md', 'recovery_kit.md'
]

def create_deployment_package():
    """Tạo package để triển khai trên máy khác"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    deploy_dir = f"crypto_bot_deploy_{timestamp}"
    
    # Tạo thư mục tạm thời
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Tạo cấu trúc thư mục
    for dir_name in IMPORTANT_DIRS:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            dest_dir = os.path.join(deploy_dir, dir_name)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            shutil.copytree(dir_name, dest_dir)
            logging.info(f"Sao chép thư mục: {dir_name}")
    
    # Tạo các thư mục logs và data
    os.makedirs(os.path.join(deploy_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(deploy_dir, "data"), exist_ok=True)
    
    # Sao chép các file quan trọng
    copied_files = []
    for pattern in IMPORTANT_FILES:
        for file_path in glob.glob(pattern):
            if os.path.isfile(file_path):
                dest_file = os.path.join(deploy_dir, os.path.basename(file_path))
                shutil.copy2(file_path, dest_file)
                copied_files.append(file_path)
    
    logging.info(f"Đã sao chép {len(copied_files)} file")
    
    # Tạo file .env mẫu
    env_sample = """# Binance API Keys
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Notification
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Session Secret
SESSION_SECRET=generate_a_strong_random_secret
"""
    
    with open(os.path.join(deploy_dir, ".env.example"), "w") as f:
        f.write(env_sample)
    
    # Tạo hướng dẫn triển khai
    deploy_guide = """# Hướng dẫn triển khai Crypto Trading Bot

## Yêu cầu hệ thống
- Python 3.9+
- pip (Python package installer)
- Linux hoặc macOS (Windows cũng hỗ trợ nhưng khuyến nghị Linux/macOS)

## Bước 1: Cài đặt các gói phụ thuộc
```bash
pip install -r requirements.txt
```

## Bước 2: Cấu hình
1. Sao chép file `.env.example` thành `.env`
   ```bash
   cp .env.example .env
   ```
2. Chỉnh sửa file `.env` và cung cấp các thông tin API key cần thiết:
   - BINANCE_API_KEY: API key Binance của bạn
   - BINANCE_API_SECRET: API secret Binance của bạn
   - TELEGRAM_BOT_TOKEN: Token của Telegram bot (nếu muốn nhận thông báo)
   - TELEGRAM_CHAT_ID: Chat ID Telegram của bạn
3. Kiểm tra file `account_config.json` để cấu hình tài khoản và chiến lược

## Bước 3: Cấp quyền thực thi cho các script
```bash
chmod +x *.sh
```

## Bước 4: Khởi động bot
```bash
./watchdog_runner.sh
```

Lệnh này sẽ khởi động toàn bộ hệ thống bao gồm:
- Web server cho giao diện người dùng
- Các script giám sát và tự động khôi phục
- Thông báo qua Telegram khi có sự cố

## Bước 5: Truy cập giao diện quản lý
Mở trình duyệt và truy cập: http://localhost:5000

## Xử lý sự cố
Nếu gặp vấn đề, vui lòng tham khảo file `recovery_kit.md` để biết cách khắc phục.

## Cách dừng bot
```bash
pkill -f "watchdog_runner.sh"
pkill -f "python"
pkill -f "gunicorn"
```
"""
    
    with open(os.path.join(deploy_dir, "INSTALL.md"), "w") as f:
        f.write(deploy_guide)
    
    # Tạo danh sách các thư viện cần thiết
    requirements = [
        "flask",
        "flask-login",
        "flask-socketio",
        "python-binance",
        "python-dotenv",
        "gunicorn",
        "requests",
        "pandas",
        "numpy",
        "matplotlib",
        "schedule",
        "joblib",
        "scikit-learn",
        "seaborn",
        "simple-websocket"
    ]
    
    with open(os.path.join(deploy_dir, "requirements.txt"), "w") as f:
        for req in requirements:
            f.write(f"{req}\n")
    
    # Tạo file khởi động nhanh
    quickstart_sh = """#!/bin/bash
# Script khởi động nhanh

# Kiểm tra Python và pip
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 không được cài đặt. Vui lòng cài đặt Python 3.9+"
    exit 1
fi

# Đảm bảo các thư mục cần thiết tồn tại
mkdir -p logs data

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# Kiểm tra file .env
if [ ! -f .env ]; then
    echo "CẢNH BÁO: File .env không tồn tại."
    echo "Đang tạo từ mẫu. Vui lòng chỉnh sửa với thông tin thực tế của bạn."
    cp .env.example .env
fi

# Cấp quyền thực thi cho các script
chmod +x *.sh *.py

# Khởi động bot
echo "Khởi động bot..."
./watchdog_runner.sh

echo "Bot đã được khởi động!"
echo "Truy cập http://localhost:5000 để xem giao diện quản lý"
"""
    
    with open(os.path.join(deploy_dir, "quickstart.sh"), "w") as f:
        f.write(quickstart_sh)
    
    # Nén lại thành file zip
    zip_filename = f"{deploy_dir}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(deploy_dir))
                zipf.write(file_path, arcname)
    
    # Xóa thư mục tạm
    shutil.rmtree(deploy_dir)
    
    logging.info(f"Đã tạo file triển khai: {zip_filename}")
    print(f"\n✅ Đã tạo gói cài đặt: {zip_filename}")
    print(f"   Tải xuống file này và giải nén để sử dụng.")
    print(f"   Xem file INSTALL.md trong gói để được hướng dẫn chi tiết.")
    
    return zip_filename

def main():
    """Hàm chính"""
    print("=== Bot Crypto Giao Dịch - Tạo Gói Cài Đặt ===")
    print("Công cụ này sẽ tạo file zip chứa tất cả mã nguồn và tài liệu cần thiết")
    print("để cài đặt bot trên máy tính cá nhân hoặc server riêng của bạn.")
    print("\nĐang tạo gói cài đặt, vui lòng đợi...")
    
    deploy_zip = create_deployment_package()

if __name__ == "__main__":
    main()