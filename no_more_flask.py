#!/usr/bin/env python3
"""
Script to perform system-wide transition from Flask web to CLI-only mode

Script này sẽ:
1. Dừng và vô hiệu hóa các dịch vụ web Flask
2. Tạo các symbolic link cần thiết
3. Thiết lập các tham số mặc định cho CLI mode
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
        logging.FileHandler("cli_transition.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def backup_files():
    """Sao lưu các file quan trọng trước khi chuyển đổi"""
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = ['main.py', 'app.py', '.env', 'multi_coin_config.json']
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(backup_dir, file))
            logger.info(f"Đã sao lưu {file} vào {backup_dir}")
    
    return backup_dir

def kill_web_processes():
    """Dừng tất cả các tiến trình web Flask đang chạy"""
    try:
        subprocess.run(["pkill", "-f", "gunicorn --bind 0.0.0.0:5000"], 
                      check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Đã dừng các tiến trình web Flask")
    except Exception as e:
        logger.error(f"Lỗi khi dừng tiến trình web: {e}")

def make_executable(file_path):
    """Đặt quyền thực thi cho file"""
    try:
        os.chmod(file_path, 0o755)  # -rwxr-xr-x
        logger.info(f"Đã đặt quyền thực thi cho {file_path}")
    except Exception as e:
        logger.error(f"Lỗi khi đặt quyền thực thi: {e}")

def update_env_file():
    """Cập nhật file .env để vô hiệu hóa web server"""
    env_path = '.env'
    
    if not os.path.exists(env_path):
        with open(env_path, 'w') as f:
            f.write("AUTO_START_WEB=false\n")
            f.write("CLI_MODE=true\n")
        logger.info("Đã tạo file .env mới với cấu hình CLI mode")
        return
    
    env_content = []
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('AUTO_START_WEB='):
                env_content.append('AUTO_START_WEB=false\n')
            elif line.startswith('CLI_MODE='):
                env_content.append('CLI_MODE=true\n')
            else:
                env_content.append(line)
    
    # Thêm thiết lập nếu chưa có
    if not any(line.startswith('AUTO_START_WEB=') for line in env_content):
        env_content.append('AUTO_START_WEB=false\n')
    if not any(line.startswith('CLI_MODE=') for line in env_content):
        env_content.append('CLI_MODE=true\n')
    
    with open(env_path, 'w') as f:
        f.writelines(env_content)
    
    logger.info("Đã cập nhật file .env với cấu hình CLI mode")

def update_config_file():
    """Cập nhật file cấu hình để vô hiệu hóa web server"""
    config_path = 'multi_coin_config.json'
    
    if not os.path.exists(config_path):
        logger.warning(f"Không tìm thấy file {config_path}")
        return
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Cập nhật các thiết lập liên quan đến web
        if 'general' not in config:
            config['general'] = {}
        config['general']['use_web_ui'] = False
        config['general']['cli_mode'] = True
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info("Đã cập nhật file cấu hình với thiết lập CLI mode")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật file cấu hình: {e}")

def create_symbolic_links():
    """Tạo các symbolic link từ new_main.py sang main.py"""
    try:
        if os.path.exists('main.py') and not os.path.islink('main.py'):
            os.rename('main.py', 'main.py.bak')
            logger.info("Đã đổi tên main.py thành main.py.bak")
        
        if os.path.exists('main.py'):
            os.unlink('main.py')
        
        os.symlink('new_main.py', 'main.py')
        logger.info("Đã tạo symbolic link từ new_main.py sang main.py")
    except Exception as e:
        logger.error(f"Lỗi khi tạo symbolic link: {e}")

def set_executable_scripts():
    """Đặt quyền thực thi cho các script CLI"""
    scripts = ['run_cli.sh', 'cli_startup.sh']
    
    for script in scripts:
        if os.path.exists(script):
            make_executable(script)

def main():
    """Hàm chính thực hiện quá trình chuyển đổi"""
    logger.info("Bắt đầu quá trình chuyển đổi từ web sang CLI mode")
    
    # Sao lưu trước khi thay đổi
    backup_dir = backup_files()
    logger.info(f"Đã sao lưu các file quan trọng vào thư mục {backup_dir}")
    
    # Dừng các tiến trình web
    kill_web_processes()
    
    # Cập nhật file .env
    update_env_file()
    
    # Cập nhật file cấu hình
    update_config_file()
    
    # Tạo symbolic link
    create_symbolic_links()
    
    # Đặt quyền thực thi cho các script
    set_executable_scripts()
    
    logger.info("Đã hoàn thành quá trình chuyển đổi từ web sang CLI mode")
    print("==========================================================")
    print("  CHUYỂN ĐỔI THÀNH CÔNG TỪ WEB MODE SANG CLI MODE  ")
    print("==========================================================")
    print("Sử dụng một trong các lệnh sau để khởi động bot:")
    print("  - ./run_cli.sh")
    print("  - ./cli_startup.sh")
    print("  - python new_main.py")
    print("==========================================================")

if __name__ == "__main__":
    main()