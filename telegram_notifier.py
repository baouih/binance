"""
Module gửi thông báo qua Telegram
Cung cấp các chức năng để gửi tin nhắn và hình ảnh đến Telegram
"""

import logging
import json
import os
import requests
from datetime import datetime

# Thiết lập logging
logger = logging.getLogger('telegram_notifier')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# File handler
file_handler = logging.FileHandler('logs/telegram_notifier.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class TelegramNotifier:
    """
    Lớp xử lý gửi thông báo qua Telegram
    """
    
    def __init__(self, token=None, chat_id=None, config_path='configs/telegram/telegram_notification_config.json'):
        """
        Khởi tạo Telegram notifier
        
        Args:
            token (str, optional): Token của bot Telegram. Mặc định là None.
            chat_id (str, optional): ID của chat. Mặc định là None.
            config_path (str, optional): Đường dẫn đến file cấu hình. Mặc định là 'configs/telegram/telegram_notification_config.json'.
        """
        self.config_path = config_path
        
        # Tải cấu hình nếu token hoặc chat_id không được cung cấp
        if token is None or chat_id is None:
            self.config = self._load_config()
            
            # Thay thế biến môi trường nếu có
            bot_token = self.config.get('bot_token', '')
            if isinstance(bot_token, str) and bot_token.startswith('${') and bot_token.endswith('}'):
                env_var = bot_token[2:-1]
                bot_token = os.environ.get(env_var, '')
                
            chat_id = self.config.get('chat_id', '')
            if isinstance(chat_id, str) and chat_id.startswith('${') and chat_id.endswith('}'):
                env_var = chat_id[2:-1]
                chat_id = os.environ.get(env_var, '')
            
            self.token = token or bot_token
            self.chat_id = chat_id or self.config.get('chat_id', '')
            self.enabled = self.config.get('enabled', False)
        else:
            self.token = token
            self.chat_id = chat_id
            self.enabled = True
            self.config = {
                'enabled': True,
                'bot_token': token,
                'chat_id': chat_id
            }
        
        # Kiểm tra token và chat_id
        if not self.token or not self.chat_id:
            logger.warning("Token hoặc chat_id không hợp lệ, thông báo Telegram bị tắt")
            self.enabled = False
        else:
            logger.info("Telegram notifications đã được kích hoạt")
        
        # API endpoint
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        
        logger.info(f"Đã tải cấu hình thông báo từ {config_path}")
    
    def _load_config(self):
        """
        Tải cấu hình từ file
        
        Returns:
            dict: Cấu hình Telegram
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                return config
            else:
                logger.warning(f"Không tìm thấy file cấu hình: {self.config_path}")
                return {'enabled': False}
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            return {'enabled': False}
    
    def send_message(self, message, parse_mode=None):
        """
        Gửi tin nhắn đến Telegram
        
        Args:
            message (str): Nội dung tin nhắn
            parse_mode (str, optional): Chế độ phân tích cú pháp (Markdown hoặc HTML). Mặc định là None.
            
        Returns:
            bool: True nếu gửi thành công, False nếu có lỗi
        """
        if not self.enabled:
            logger.info("Bỏ qua tin nhắn vì thông báo Telegram bị tắt")
            return False
        
        if not message:
            logger.warning("Bỏ qua tin nhắn vì nội dung trống")
            return False
        
        try:
            params = {
                'chat_id': self.chat_id,
                'text': message
            }
            
            if parse_mode:
                params['parse_mode'] = parse_mode
            
            response = requests.post(f"{self.api_url}/sendMessage", json=params)
            
            if response.status_code == 200:
                logger.info("Đã gửi thông báo Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
            return False
    
    def send_photo(self, photo_path, caption=None, parse_mode=None):
        """
        Gửi hình ảnh đến Telegram
        
        Args:
            photo_path (str): Đường dẫn đến file hình ảnh
            caption (str, optional): Chú thích cho hình ảnh. Mặc định là None.
            parse_mode (str, optional): Chế độ phân tích cú pháp (Markdown hoặc HTML). Mặc định là None.
            
        Returns:
            bool: True nếu gửi thành công, False nếu có lỗi
        """
        if not self.enabled:
            logger.info("Bỏ qua hình ảnh vì thông báo Telegram bị tắt")
            return False
        
        if not os.path.exists(photo_path):
            logger.warning(f"Bỏ qua hình ảnh vì file không tồn tại: {photo_path}")
            return False
        
        try:
            params = {
                'chat_id': self.chat_id
            }
            
            if caption:
                params['caption'] = caption
            
            if parse_mode:
                params['parse_mode'] = parse_mode
            
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                response = requests.post(f"{self.api_url}/sendPhoto", params=params, files=files)
            
            if response.status_code == 200:
                logger.info(f"Đã gửi hình ảnh {photo_path} qua Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi hình ảnh qua Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi hình ảnh qua Telegram: {str(e)}")
            return False
    
    def send_document(self, document_path, caption=None, parse_mode=None):
        """
        Gửi tài liệu đến Telegram
        
        Args:
            document_path (str): Đường dẫn đến file tài liệu
            caption (str, optional): Chú thích cho tài liệu. Mặc định là None.
            parse_mode (str, optional): Chế độ phân tích cú pháp (Markdown hoặc HTML). Mặc định là None.
            
        Returns:
            bool: True nếu gửi thành công, False nếu có lỗi
        """
        if not self.enabled:
            logger.info("Bỏ qua tài liệu vì thông báo Telegram bị tắt")
            return False
        
        if not os.path.exists(document_path):
            logger.warning(f"Bỏ qua tài liệu vì file không tồn tại: {document_path}")
            return False
        
        try:
            params = {
                'chat_id': self.chat_id
            }
            
            if caption:
                params['caption'] = caption
            
            if parse_mode:
                params['parse_mode'] = parse_mode
            
            with open(document_path, 'rb') as document:
                files = {'document': document}
                response = requests.post(f"{self.api_url}/sendDocument", params=params, files=files)
            
            if response.status_code == 200:
                logger.info(f"Đã gửi tài liệu {document_path} qua Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi tài liệu qua Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi tài liệu qua Telegram: {str(e)}")
            return False
    
    def test_connection(self):
        """
        Kiểm tra kết nối đến Telegram API
        
        Returns:
            bool: True nếu kết nối thành công, False nếu có lỗi
        """
        if not self.enabled:
            logger.info("Bỏ qua kiểm tra kết nối vì thông báo Telegram bị tắt")
            return False
        
        try:
            response = requests.get(f"{self.api_url}/getMe")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok', False):
                    bot_info = data.get('result', {})
                    bot_name = bot_info.get('first_name', 'Unknown')
                    logger.info(f"Kết nối thành công đến bot Telegram: {bot_name}")
                    return True
                else:
                    logger.error(f"Lỗi khi kết nối đến Telegram API: {data.get('description', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Lỗi khi kết nối đến Telegram API: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối đến Telegram API: {str(e)}")
            return False


# Hàm để sử dụng module này độc lập
def send_notification(message, telegram_config_path='configs/telegram/telegram_notification_config.json'):
    """
    Gửi thông báo qua Telegram
    
    Args:
        message (str): Nội dung thông báo
        telegram_config_path (str, optional): Đường dẫn đến file cấu hình. Mặc định là 'configs/telegram/telegram_notification_config.json'.
        
    Returns:
        bool: True nếu gửi thành công, False nếu có lỗi
    """
    notifier = TelegramNotifier(config_path=telegram_config_path)
    return notifier.send_message(message)