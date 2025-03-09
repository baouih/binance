#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

# Đọc token bot từ biến môi trường hoặc file cấu hình
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Nếu không có trong biến môi trường, thử đọc từ file cấu hình
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    try:
        with open('bot_config.json', 'r') as f:
            config = json.load(f)
            if not TELEGRAM_BOT_TOKEN:
                TELEGRAM_BOT_TOKEN = config.get('telegram_bot_token')
            if not TELEGRAM_CHAT_ID:
                TELEGRAM_CHAT_ID = config.get('telegram_chat_id')
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def send_telegram_message(message_type, message_content):
    """
    Gửi thông báo qua Telegram
    
    Args:
        message_type (str): Loại thông báo ('info', 'warning', 'success', 'error')
        message_content (str): Nội dung thông báo
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Thiếu thông tin cấu hình Telegram")
        return False
    
    # Thêm emoji tương ứng với loại thông báo
    emoji_map = {
        'info': 'ℹ️',
        'warning': '⚠️',
        'success': '✅',
        'error': '❌'
    }
    
    emoji = emoji_map.get(message_type.lower(), 'ℹ️')
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # Chuẩn bị tin nhắn
    formatted_message = f"{emoji} *{message_type.upper()}* [{timestamp}]\n{message_content}"
    
    # Gửi tin nhắn thông qua API Telegram
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": formatted_message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(api_url, data=data)
        result = response.json()
        
        if result.get("ok"):
            return True
        else:
            print(f"Lỗi API Telegram: {result.get('description')}")
            return False
    except Exception as e:
        print(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
        return False

if __name__ == "__main__":
    # Kiểm tra tham số
    if len(sys.argv) < 3:
        print("Sử dụng: python telegram_send_message.py <message_type> <message_content>")
        sys.exit(1)
    
    message_type = sys.argv[1]
    message_content = sys.argv[2]
    
    # Gửi tin nhắn
    result = send_telegram_message(message_type, message_content)
    
    if result:
        print(f"Đã gửi thông báo {message_type} thành công")
    else:
        print(f"Không thể gửi thông báo {message_type}")
