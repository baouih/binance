#!/usr/bin/env python3
"""
Script kiểm tra kết nối Telegram
"""

import os
import logging
import requests
import json
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_test_message():
    # Tải biến môi trường
    load_dotenv()
    
    # Lấy thông tin cấu hình từ biến môi trường
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.error("Thiếu thông tin cấu hình Telegram (token hoặc chat_id)")
        print("Lỗi: Thiếu thông tin cấu hình Telegram (token hoặc chat_id)")
        return False
    
    logger.info(f"Bot Token: {token[:5]}...{token[-5:]}")
    logger.info(f"Chat ID: {chat_id}")
    
    # Gửi tin nhắn test
    base_url = "https://api.telegram.org/bot"
    url = f"{base_url}{token}/sendMessage"
    message = "🔄 Đây là tin nhắn test từ Bot Giao Dịch Crypto.\n\n⏱️ Thời gian: " + \
              f"{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" + \
              "✅ Nếu bạn nhận được tin nhắn này, kết nối Telegram đang hoạt động bình thường."
    
    try:
        params = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, params=params)
        
        # Kiểm tra kết quả
        if response.status_code == 200:
            logger.info("Đã gửi tin nhắn test thành công!")
            print("Thành công: Đã gửi tin nhắn test tới Telegram!")
            print(f"Thông tin phản hồi: {response.json()}")
            return True
        else:
            logger.error(f"Lỗi khi gửi tin nhắn: {response.status_code} - {response.text}")
            print(f"Lỗi: Không thể gửi tin nhắn. Mã lỗi: {response.status_code}")
            print(f"Chi tiết lỗi: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn qua Telegram: {e}")
        print(f"Lỗi: {str(e)}")
        return False

if __name__ == "__main__":
    print("Đang kiểm tra kết nối Telegram...")
    send_test_message()