#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra thông báo Telegram
"""

import os
import requests
import json
import logging
import sys
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("telegram_test")

def load_env_variables():
    """Tải biến môi trường từ file .env nếu có"""
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

def get_telegram_credentials():
    """Lấy thông tin đăng nhập Telegram từ biến môi trường hoặc config file"""
    # Tải từ file .env nếu có
    load_env_variables()
    
    # Thử lấy từ biến môi trường
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Nếu không có trong biến môi trường, thử đọc từ file config
    if not bot_token or not chat_id:
        try:
            if os.path.exists("telegram_config.json"):
                with open("telegram_config.json", "r") as config_file:
                    config = json.load(config_file)
                    if not bot_token and "bot_token" in config:
                        bot_token = config["bot_token"]
                    if not chat_id and "chat_id" in config:
                        chat_id = config["chat_id"]
                    print("Đã tải thông tin Telegram từ file config")
        except Exception as e:
            logger.error(f"Lỗi khi đọc file config Telegram: {e}")
    
    return bot_token, chat_id

def send_telegram_message(bot_token, chat_id, message):
    """Gửi tin nhắn tới Telegram"""
    if not bot_token or not chat_id:
        print("Không tìm thấy thông tin Bot Token hoặc Chat ID")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=data)
        result = response.json()
        
        if result.get("ok"):
            print("Gửi tin nhắn thành công!")
            return True
        else:
            print(f"Lỗi khi gửi tin nhắn: {result.get('description')}")
            return False
    
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn: {e}")
        logger.error(f"Lỗi khi gửi tin nhắn: {e}")
        return False

def main():
    print("=" * 50)
    print("KIỂM TRA THÔNG BÁO TELEGRAM")
    print("=" * 50)
    
    # Lấy thông tin đăng nhập
    bot_token, chat_id = get_telegram_credentials()
    
    if not bot_token or not chat_id:
        print("Không tìm thấy thông tin Bot Token hoặc Chat ID")
        print("\nVui lòng thiết lập biến môi trường sau:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("TELEGRAM_CHAT_ID=your_chat_id")
        print("\nHoặc thêm chúng vào file .env trong thư mục hiện tại")
        sys.exit(1)
    
    # Tạo nội dung tin nhắn kiểm tra
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"""
<b>🤖 KIỂM TRA BOT GIAO DỊCH</b>

📊 <b>Trạng thái hệ thống:</b> Hoạt động
⏱ <b>Thời gian:</b> {current_time}

<b>Thông tin kiểm tra:</b>
✅ Kết nối API: Thành công
✅ Cơ sở dữ liệu: Hoạt động
✅ Hệ thống giao dịch: Sẵn sàng

<i>Đây là tin nhắn kiểm tra từ hệ thống giao dịch tự động.</i>
"""
    
    # Gửi tin nhắn
    print("Đang gửi tin nhắn kiểm tra đến Telegram...")
    result = send_telegram_message(bot_token, chat_id, message)
    
    print("\nKết quả:")
    if result:
        print("✅ Gửi thông báo Telegram thành công!")
    else:
        print("❌ Gửi thông báo Telegram thất bại!")
    
    print("\nHướng dẫn:")
    print("1. Nếu gửi thất bại, kiểm tra lại Bot Token và Chat ID")
    print("2. Đảm bảo bạn đã khởi động bot và gửi ít nhất một tin nhắn cho bot")
    print('3. Kiểm tra kết nối internet')
    
    print("\nThời gian kiểm tra:", current_time)
    print("=" * 50)

if __name__ == "__main__":
    main()