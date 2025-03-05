#!/usr/bin/env python3
"""
Script thu thập log và file quan trọng cho việc debug
"""

import os
import sys
import json
import shutil
import datetime
import zipfile
import glob
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Các thư mục chứa logs cần thu thập
LOG_DIRS = ['logs', '.']
LOG_PATTERNS = ['*.log', '*.pid', 'watchdog*', 'auto_recovery*']

# Các file cấu hình quan trọng
CONFIG_FILES = [
    'account_config.json', 
    'bot_config.json', 
    'bot_status.json',
    'active_positions.json',
    'configs/*.json'
]

# Các file code quan trọng
CODE_FILES = [
    'main.py',
    'app.py',
    'auto_recovery.sh',
    'watchdog.sh',
    'watchdog_runner.sh',
    'telegram_watchdog.py',
    'update_status.sh',
    'update_positions.sh',
    'binance_api.py',
    'enhanced_trailing_stop.py'
]

def create_debug_package():
    """Tạo package chứa các file quan trọng cho debug"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = f"debug_package_{timestamp}"
    
    # Tạo thư mục tạm thời
    os.makedirs(debug_dir, exist_ok=True)
    os.makedirs(os.path.join(debug_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(debug_dir, "configs"), exist_ok=True)
    os.makedirs(os.path.join(debug_dir, "code"), exist_ok=True)
    
    # Thu thập logs
    collected_logs = []
    for log_dir in LOG_DIRS:
        for pattern in LOG_PATTERNS:
            path_pattern = os.path.join(log_dir, pattern)
            for log_file in glob.glob(path_pattern):
                if os.path.isfile(log_file):
                    target_path = os.path.join(debug_dir, "logs", os.path.basename(log_file))
                    shutil.copy2(log_file, target_path)
                    collected_logs.append(log_file)
    
    logging.info(f"Đã thu thập {len(collected_logs)} file logs")
    
    # Thu thập file cấu hình
    collected_configs = []
    for config_pattern in CONFIG_FILES:
        for config_file in glob.glob(config_pattern):
            if os.path.isfile(config_file):
                if 'configs/' in config_file:
                    target_path = os.path.join(debug_dir, config_file)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                else:
                    target_path = os.path.join(debug_dir, "configs", os.path.basename(config_file))
                shutil.copy2(config_file, target_path)
                collected_configs.append(config_file)
    
    logging.info(f"Đã thu thập {len(collected_configs)} file cấu hình")
    
    # Thu thập file code
    collected_code = []
    for code_file in CODE_FILES:
        if os.path.isfile(code_file):
            target_path = os.path.join(debug_dir, "code", os.path.basename(code_file))
            shutil.copy2(code_file, target_path)
            collected_code.append(code_file)
    
    logging.info(f"Đã thu thập {len(collected_code)} file code")
    
    # Tạo file thông tin hệ thống
    system_info = {
        "timestamp": timestamp,
        "collected_logs": collected_logs,
        "collected_configs": collected_configs,
        "collected_code": collected_code
    }
    
    with open(os.path.join(debug_dir, "system_info.json"), "w") as f:
        json.dump(system_info, f, indent=2)
    
    # Tạo file README với hướng dẫn
    readme_content = f"""# Debug Package - Crypto Bot

Gói thu thập debug được tạo lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Nội dung:
- **logs/**: Chứa các file log của hệ thống
- **configs/**: Chứa các file cấu hình
- **code/**: Chứa các file code quan trọng

## Cách sử dụng:
1. Giải nén toàn bộ package
2. Đảm bảo bạn cài đặt đầy đủ các thư viện trong requirements.txt
3. Sau khi khắc phục sự cố, chạy `python main.py` để khởi động bot

## Cách khắc phục sự cố thường gặp:
1. **Bot không khởi động**: Kiểm tra file logs/flask_app.log
2. **Kết nối API thất bại**: Kiểm tra cấu hình API trong configs/account_config.json
3. **Watchdog không hoạt động**: Đảm bảo các file watchdog có quyền thực thi (chmod +x)

Nếu cần hỗ trợ, vui lòng liên hệ qua hệ thống support.
"""
    
    with open(os.path.join(debug_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    # Tạo danh sách các thư viện cần thiết
    requirements = [
        "flask",
        "flask-sqlalchemy",
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
        "simple-websocket"
    ]
    
    with open(os.path.join(debug_dir, "requirements.txt"), "w") as f:
        for req in requirements:
            f.write(f"{req}\n")
    
    # Nén lại thành file zip
    zip_filename = f"{debug_dir}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(debug_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(debug_dir))
                zipf.write(file_path, arcname)
    
    # Xóa thư mục tạm
    shutil.rmtree(debug_dir)
    
    logging.info(f"Đã tạo file debug package: {zip_filename}")
    return zip_filename

def create_deployment_package():
    """Tạo package để triển khai trên máy khác"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    deploy_dir = f"deployment_package_{timestamp}"
    
    # Tạo thư mục tạm thời
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Danh sách thư mục cần copy
    dirs_to_copy = [
        'app', 'configs', 'models', 'routes', 'static', 'templates'
    ]
    
    # Copy các thư mục
    for dir_name in dirs_to_copy:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            shutil.copytree(dir_name, os.path.join(deploy_dir, dir_name))
    
    # Danh sách các file Python quan trọng cần copy
    py_files = glob.glob("*.py")
    sh_files = glob.glob("*.sh")
    json_files = glob.glob("*.json")
    
    # Copy tất cả file Python
    for file in py_files + sh_files + json_files:
        if os.path.isfile(file):
            shutil.copy2(file, os.path.join(deploy_dir, file))
    
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
2. Chỉnh sửa file `.env` và cung cấp các thông tin API key cần thiết
3. Kiểm tra file `account_config.json` đảm bảo nó phù hợp với tài khoản của bạn

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

## Bước 6: Giám sát logs
```bash
tail -f *.log
```

## Xử lý sự cố
Nếu gặp vấn đề, hãy kiểm tra các file log:
- `flask_app.log` - Log của web server
- `auto_recovery.log` - Log của hệ thống tự khôi phục
- `watchdog.log` - Log của hệ thống giám sát
- `telegram_watchdog.log` - Log của hệ thống thông báo Telegram

## Cách dừng bot
```bash
pkill -f "watchdog_runner.sh"
pkill -f "python"
pkill -f "gunicorn"
```
"""
    
    with open(os.path.join(deploy_dir, "DEPLOY_GUIDE.md"), "w") as f:
        f.write(deploy_guide)
    
    # Tạo danh sách các thư viện cần thiết
    requirements = [
        "flask",
        "flask-sqlalchemy",
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
        "simple-websocket"
    ]
    
    with open(os.path.join(deploy_dir, "requirements.txt"), "w") as f:
        for req in requirements:
            f.write(f"{req}\n")
    
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
    return zip_filename

def main():
    """Hàm chính của script"""
    print("=== Crypto Bot Package Creator ===")
    print("1. Tạo gói debug (chỉ chứa logs và file cấu hình)")
    print("2. Tạo gói triển khai đầy đủ (toàn bộ mã nguồn và cấu hình)")
    print("3. Tạo cả hai")
    
    choice = input("Lựa chọn của bạn (1-3): ")
    
    if choice == '1' or choice == '3':
        debug_zip = create_debug_package()
        print(f"✅ Đã tạo gói debug: {debug_zip}")
    
    if choice == '2' or choice == '3':
        deploy_zip = create_deployment_package()
        print(f"✅ Đã tạo gói triển khai: {deploy_zip}")
    
    print("Hoàn tất! Bạn có thể tải xuống các file zip này để sử dụng.")

if __name__ == "__main__":
    main()