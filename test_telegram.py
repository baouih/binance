import os
import json
import logging
import requests
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('telegram_test')

# Lấy token và chat_id từ biến môi trường
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
chat_id = os.environ.get('TELEGRAM_CHAT_ID')

if not bot_token or not chat_id:
    logger.error("Không tìm thấy TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong biến môi trường")
    exit(1)

logger.info(f"Bot token: {bot_token[:5]}...{bot_token[-5:]}")
logger.info(f"Chat ID: {chat_id}")

# Khởi tạo API URL
api_url = f"https://api.telegram.org/bot{bot_token}"

# Kiểm tra kết nối
try:
    response = requests.get(f"{api_url}/getMe")
    response_data = response.json()
    
    if response.status_code == 200 and response_data.get('ok'):
        bot_info = response_data.get('result', {})
        logger.info(f"Kết nối thành công! Bot: @{bot_info.get('username')} - {bot_info.get('first_name')}")
    else:
        logger.error(f"Lỗi khi kết nối đến Bot API: {response.text}")
        exit(1)
except Exception as e:
    logger.error(f"Lỗi khi kết nối đến Bot API: {str(e)}")
    exit(1)

# Gửi tin nhắn kiểm tra
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
test_message = f"🧪 Tin nhắn kiểm tra hệ thống giao dịch\n⏰ Thời gian: {current_time}\n\n✅ Hệ thống đang hoạt động bình thường\n🔄 Đang theo dõi thị trường, chờ cơ hội giao dịch"

try:
    params = {
        'chat_id': chat_id,
        'text': test_message
    }
    
    logger.info("Đang gửi tin nhắn kiểm tra...")
    response = requests.post(f"{api_url}/sendMessage", json=params)
    
    if response.status_code == 200 and response.json().get('ok'):
        logger.info("✅ Đã gửi tin nhắn kiểm tra thành công!")
        print("\n✅ ĐÃ GỬI TIN NHẮN KIỂM TRA TELEGRAM THÀNH CÔNG!")
    else:
        logger.error(f"❌ Lỗi khi gửi tin nhắn: {response.text}")
        print(f"\n❌ LỖI KHI GỬI TIN NHẮN: {response.text}")
except Exception as e:
    logger.error(f"❌ Lỗi khi gửi tin nhắn: {str(e)}")
    print(f"\n❌ LỖI KHI GỬI TIN NHẮN: {str(e)}")