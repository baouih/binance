#!/usr/bin/env python3
"""
Module gửi thông báo qua Telegram

Module này xử lý việc gửi thông báo đến Telegram Bot API, cho phép
bot giao dịch cập nhật trạng thái, cảnh báo và thông tin giao dịch.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Union, Optional
import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("telegram_notifier")

# Đường dẫn đến file cấu hình
CONFIG_FILE = '.env'
TELEGRAM_CONFIG_FILE = 'telegram_config.json'
NOTIFICATION_CONFIG_FILE = 'configs/telegram_notification_config.json'

class TelegramNotifier:
    """Lớp quản lý gửi thông báo qua Telegram"""
    
    def __init__(self, token: str = None, chat_id: str = None, config_file: str = TELEGRAM_CONFIG_FILE):
        """
        Khởi tạo Telegram Notifier
        
        Args:
            token (str, optional): Telegram Bot Token
            chat_id (str, optional): Telegram Chat ID
            config_file (str): Đường dẫn đến file cấu hình
        """
        self.config_file = config_file
        self.token = token
        self.chat_id = chat_id
        self.last_notifications = {}  # Dictionary lưu các thông báo đã gửi gần đây
        self.notification_config = {
            "cache_duration_seconds": 300,  # Mặc định 5 phút
            "enable_double_notification_prevention": True,  # Mặc định bật
            "notification_types": ["trade", "position", "error", "warning", "info"]  # Các loại thông báo cần lọc
        }
        
        # Nếu không cung cấp token hoặc chat_id, đọc từ file cấu hình
        if not token or not chat_id:
            self.load_config()
            
        # Tải cấu hình thông báo từ file
        self._load_notification_config()
    
    def load_config(self) -> bool:
        """
        Tải cấu hình từ file
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            # Đầu tiên thử đọc từ file .env
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            if key == 'TELEGRAM_TOKEN':
                                self.token = value.strip('"\'')
                            elif key == 'TELEGRAM_CHAT_ID':
                                self.chat_id = value.strip('"\'')
            
            # Sau đó thử đọc từ file cấu hình JSON
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                    # Chỉ cập nhật nếu chưa có thông tin
                    if not self.token and 'token' in config:
                        self.token = config['token']
                    if not self.chat_id and 'chat_id' in config:
                        self.chat_id = config['chat_id']
            
            return bool(self.token and self.chat_id)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Telegram: {str(e)}")
            return False
            
    def _load_notification_config(self) -> bool:
        """
        Tải cấu hình thông báo từ file
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            if os.path.exists(NOTIFICATION_CONFIG_FILE):
                with open(NOTIFICATION_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    
                    # Cập nhật cấu hình thông báo
                    if 'cache_duration_seconds' in config:
                        self.notification_config['cache_duration_seconds'] = config['cache_duration_seconds']
                    if 'enable_double_notification_prevention' in config:
                        self.notification_config['enable_double_notification_prevention'] = config['enable_double_notification_prevention']
                    if 'notification_types' in config:
                        self.notification_config['notification_types'] = config['notification_types']
                
                logger.info(f"Đã tải cấu hình thông báo từ {NOTIFICATION_CONFIG_FILE}")
                return True
            else:
                # Nếu file không tồn tại, tạo file với cấu hình mặc định
                os.makedirs(os.path.dirname(NOTIFICATION_CONFIG_FILE), exist_ok=True)
                with open(NOTIFICATION_CONFIG_FILE, 'w') as f:
                    json.dump(self.notification_config, f, indent=4)
                logger.info(f"Đã tạo file cấu hình thông báo mặc định tại {NOTIFICATION_CONFIG_FILE}")
                return True
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình thông báo: {str(e)}")
            return False
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            config = {
                'token': self.token,
                'chat_id': self.chat_id,
                'last_updated': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            logger.info(f"Đã lưu cấu hình Telegram vào {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình Telegram: {str(e)}")
            return False
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> Dict:
        """
        Gửi tin nhắn Telegram
        
        Args:
            message (str): Nội dung tin nhắn
            parse_mode (str): Chế độ hiển thị ('HTML' hoặc 'Markdown')
            
        Returns:
            Dict: Kết quả từ API
        """
        try:
            if not self.token or not self.chat_id:
                logger.error("Không tìm thấy Telegram token hoặc chat ID")
                return {'ok': False, 'error': 'Missing token or chat ID'}
            
            # Kiểm tra xem tin nhắn này đã được gửi gần đây chưa (tránh gửi trùng lặp trong 5 phút)
            message_hash = hash(message)
            current_time = datetime.datetime.now()
            
            # Kiểm tra xem tin nhắn tương tự đã được gửi trong vòng 5 phút không
            if message_hash in self.last_notifications:
                last_time = self.last_notifications[message_hash]
                time_diff = (current_time - last_time).total_seconds()
                if time_diff < 300:  # 5 phút = 300 giây
                    logger.info(f"Bỏ qua tin nhắn trùng lặp (đã gửi cách đây {time_diff:.0f}s)")
                    return {'ok': True, 'skipped': True, 'reason': 'Duplicate message within 5 minutes'}
            
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, data=data)
            result = response.json()
            
            if result.get('ok'):
                logger.info("Đã gửi thông báo Telegram thành công")
                # Lưu thông tin về tin nhắn vừa gửi
                self.last_notifications[message_hash] = current_time
                
                # Xóa các thông báo cũ hơn 5 phút
                self._clean_old_notifications()
            else:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {result.get('description', 'Unknown error')}")
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
            return {'ok': False, 'error': str(e)}
    
    def _clean_old_notifications(self):
        """Xóa các thông báo cũ hơn 5 phút để tránh tràn bộ nhớ"""
        current_time = datetime.datetime.now()
        to_remove = []
        
        for msg_hash, time_sent in self.last_notifications.items():
            if (current_time - time_sent).total_seconds() >= 300:  # 5 phút = 300 giây
                to_remove.append(msg_hash)
        
        for msg_hash in to_remove:
            del self.last_notifications[msg_hash]
    
    def send_notification(self, message_type: str, message_content: str) -> Dict:
        """
        Gửi thông báo với định dạng dựa trên loại thông báo
        
        Args:
            message_type (str): Loại thông báo ('info', 'warning', 'success', 'error')
            message_content (str): Nội dung thông báo
            
        Returns:
            Dict: Kết quả từ API
        """
        try:
            # Định dạng thông báo dựa trên loại
            emoji_map = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'success': '✅',
                'error': '❌',
                'alert': '🔔',
                'trade': '💰',
                'position': '📊',
                'trailing': '🔄'
            }
            
            emoji = emoji_map.get(message_type.lower(), 'ℹ️')
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Tạo tin nhắn với định dạng HTML
            formatted_message = f"{emoji} <b>BINANCE TRADER BOT</b> {emoji}\n\n"
            formatted_message += f"{message_content}\n\n"
            formatted_message += f"<i>Thời gian: {current_time}</i>"
            
            # Tạo một key xác định nội dung chính của tin nhắn (không bao gồm thời gian)
            message_key = f"{message_type}_{message_content}"
            message_hash = hash(message_key)
            current_time_obj = datetime.datetime.now()
            
            # Kiểm tra xem nội dung chính này đã được gửi trong 5 phút qua chưa
            if message_hash in self.last_notifications:
                last_time = self.last_notifications[message_hash]
                time_diff = (current_time_obj - last_time).total_seconds()
                if time_diff < 300:  # 5 phút = 300 giây
                    logger.info(f"Bỏ qua thông báo trùng lặp loại {message_type} (đã gửi cách đây {time_diff:.0f}s)")
                    return {'ok': True, 'skipped': True, 'reason': 'Duplicate content within 5 minutes'}
            
            # Gửi tin nhắn và lưu thời gian gửi của nội dung này
            result = self.send_message(formatted_message)
            if result.get('ok') and not result.get('skipped', False):
                self.last_notifications[message_hash] = current_time_obj
            
            return result
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo: {str(e)}")
            return {'ok': False, 'error': str(e)}
    
    def send_trade_notification(self, trade_data: Dict) -> Dict:
        """
        Gửi thông báo về giao dịch
        
        Args:
            trade_data (Dict): Thông tin giao dịch
                {
                    'symbol': str,
                    'side': str,
                    'entry_price': float,
                    'quantity': float,
                    'leverage': int,
                    'take_profit': float,
                    'stop_loss': float,
                    ...
                }
                
        Returns:
            Dict: Kết quả từ API
        """
        try:
            symbol = trade_data.get('symbol', 'UNKNOWN')
            side = trade_data.get('side', 'UNKNOWN')
            entry_price = trade_data.get('entry_price', 0)
            quantity = trade_data.get('quantity', 0)
            leverage = trade_data.get('leverage', 1)
            take_profit = trade_data.get('take_profit', 0)
            stop_loss = trade_data.get('stop_loss', 0)
            
            # Emoji dựa trên hướng giao dịch
            emoji = '🟢' if side.upper() == 'LONG' or side.upper() == 'BUY' else '🔴'
            
            # Tạo nội dung thông báo
            message = f"{emoji} <b>GIAO DỊCH MỚI - {side.upper()} {symbol}</b> {emoji}\n\n"
            message += f"💵 Giá vào: {entry_price}\n"
            message += f"🔢 Số lượng: {quantity}\n"
            message += f"⚡ Đòn bẩy: {leverage}x\n"
            
            if stop_loss:
                message += f"🛑 Stop Loss: {stop_loss}\n"
            if take_profit:
                message += f"🎯 Take Profit: {take_profit}\n"
            
            # Gửi thông báo
            return self.send_notification('trade', message)
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo giao dịch: {str(e)}")
            return {'ok': False, 'error': str(e)}
    
    def send_trailing_stop_notification(self, position_data: Dict) -> Dict:
        """
        Gửi thông báo về trailing stop
        
        Args:
            position_data (Dict): Thông tin vị thế
                {
                    'symbol': str,
                    'side': str,
                    'entry_price': float,
                    'current_price': float,
                    'trailing_stop': float,
                    'profit_percent': float,
                    ...
                }
                
        Returns:
            Dict: Kết quả từ API
        """
        try:
            symbol = position_data.get('symbol', 'UNKNOWN')
            side = position_data.get('side', 'UNKNOWN')
            entry_price = position_data.get('entry_price', 0)
            current_price = position_data.get('current_price', 0)
            trailing_stop = position_data.get('trailing_stop', 0)
            profit_percent = position_data.get('profit_percent', 0)
            
            # Emoji dựa trên hướng vị thế
            emoji = '🟢' if side.upper() == 'LONG' or side.upper() == 'BUY' else '🔴'
            
            # Tạo nội dung thông báo
            message = f"🔄 <b>TRAILING STOP KÍCH HOẠT - {side.upper()} {symbol}</b> 🔄\n\n"
            message += f"{emoji} Vị thế: {side.upper()}\n"
            message += f"💵 Giá vào: {entry_price}\n"
            message += f"💹 Giá hiện tại: {current_price}\n"
            message += f"🔄 Trailing Stop: {trailing_stop}\n"
            message += f"📈 Lợi nhuận: {profit_percent:.2f}%\n"
            
            # Gửi thông báo
            return self.send_notification('trailing', message)
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo trailing stop: {str(e)}")
            return {'ok': False, 'error': str(e)}
    
    def send_position_close_notification(self, position_data: Dict) -> Dict:
        """
        Gửi thông báo về đóng vị thế
        
        Args:
            position_data (Dict): Thông tin vị thế
                {
                    'symbol': str,
                    'side': str,
                    'entry_price': float,
                    'exit_price': float,
                    'profit_loss': float,
                    'profit_percent': float,
                    'close_reason': str,
                    ...
                }
                
        Returns:
            Dict: Kết quả từ API
        """
        try:
            symbol = position_data.get('symbol', 'UNKNOWN')
            side = position_data.get('side', 'UNKNOWN')
            entry_price = position_data.get('entry_price', 0)
            exit_price = position_data.get('exit_price', 0)
            profit_loss = position_data.get('profit_loss', 0)
            profit_percent = position_data.get('profit_percent', 0)
            close_reason = position_data.get('close_reason', 'manual')
            
            # Emoji dựa trên lợi nhuận
            emoji = '✅' if profit_loss > 0 else '❌'
            
            # Emoji cho lý do đóng vị thế
            reason_emoji = {
                'take_profit': '🎯',
                'stop_loss': '🛑',
                'trailing_stop': '🔄',
                'manual': '👤',
                'liquidation': '💥'
            }
            reason_icon = reason_emoji.get(close_reason.lower(), '🔄')
            
            # Tạo nội dung thông báo
            message = f"{emoji} <b>VỊ THẾ ĐÓNG - {side.upper()} {symbol}</b> {emoji}\n\n"
            message += f"💵 Giá vào: {entry_price}\n"
            message += f"💹 Giá thoát: {exit_price}\n"
            message += f"💰 Lợi nhuận: {profit_loss:.2f} USDT ({profit_percent:.2f}%)\n"
            message += f"{reason_icon} Lý do: {close_reason.upper()}\n"
            
            # Gửi thông báo
            return self.send_notification('position', message)
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo đóng vị thế: {str(e)}")
            return {'ok': False, 'error': str(e)}
    
    def send_daily_summary(self, summary_data: Dict) -> Dict:
        """
        Gửi tóm tắt hàng ngày
        
        Args:
            summary_data (Dict): Dữ liệu tóm tắt
                {
                    'date': str,
                    'total_trades': int,
                    'winning_trades': int,
                    'losing_trades': int,
                    'total_profit_loss': float,
                    'win_rate': float,
                    'best_trade': Dict,
                    'worst_trade': Dict,
                    ...
                }
                
        Returns:
            Dict: Kết quả từ API
        """
        try:
            date = summary_data.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))
            total_trades = summary_data.get('total_trades', 0)
            winning_trades = summary_data.get('winning_trades', 0)
            losing_trades = summary_data.get('losing_trades', 0)
            total_profit_loss = summary_data.get('total_profit_loss', 0)
            win_rate = summary_data.get('win_rate', 0) * 100 if 'win_rate' in summary_data else 0
            
            # Emoji dựa trên tổng lợi nhuận
            emoji = '📈' if total_profit_loss > 0 else '📉'
            
            # Tạo nội dung thông báo
            message = f"{emoji} <b>TÓM TẮT NGÀY {date}</b> {emoji}\n\n"
            message += f"🔢 Tổng số giao dịch: {total_trades}\n"
            message += f"✅ Giao dịch thắng: {winning_trades}\n"
            message += f"❌ Giao dịch thua: {losing_trades}\n"
            message += f"💰 Tổng lợi nhuận: {total_profit_loss:.2f} USDT\n"
            message += f"📊 Tỷ lệ thắng: {win_rate:.2f}%\n"
            
            # Thêm thông tin về giao dịch tốt nhất và tệ nhất nếu có
            best_trade = summary_data.get('best_trade')
            if best_trade:
                message += f"\n🏆 <b>Giao dịch tốt nhất:</b>\n"
                message += f"   {best_trade.get('symbol')} {best_trade.get('side')}: {best_trade.get('profit_percent', 0):.2f}%\n"
            
            worst_trade = summary_data.get('worst_trade')
            if worst_trade:
                message += f"\n💔 <b>Giao dịch tệ nhất:</b>\n"
                message += f"   {worst_trade.get('symbol')} {worst_trade.get('side')}: {worst_trade.get('profit_percent', 0):.2f}%\n"
            
            # Gửi thông báo
            return self.send_notification('info', message)
        except Exception as e:
            logger.error(f"Lỗi khi gửi tóm tắt hàng ngày: {str(e)}")
            return {'ok': False, 'error': str(e)}

def test_telegram_notifier():
    """Hàm test Telegram Notifier"""
    
    # Khởi tạo Telegram Notifier
    notifier = TelegramNotifier()
    
    # Kiểm tra xem đã có cấu hình chưa
    if not notifier.token or not notifier.chat_id:
        print("Chưa có cấu hình Telegram. Vui lòng nhập thông tin:")
        token = input("Telegram Bot Token: ")
        chat_id = input("Telegram Chat ID: ")
        
        notifier.token = token
        notifier.chat_id = chat_id
        notifier.save_config()
    
    # Gửi thông báo test
    print("\nGửi thông báo test...")
    result = notifier.send_notification('info', "Đây là thông báo test từ Binance Trader Bot")
    
    if result.get('ok'):
        print("Gửi thông báo thành công!")
    else:
        print(f"Lỗi khi gửi thông báo: {result.get('error', 'Unknown error')}")
    
    # Gửi thông báo giao dịch test
    print("\nGửi thông báo giao dịch test...")
    trade_data = {
        'symbol': 'BTCUSDT',
        'side': 'LONG',
        'entry_price': 60000,
        'quantity': 0.1,
        'leverage': 10,
        'take_profit': 65000,
        'stop_loss': 58000
    }
    result = notifier.send_trade_notification(trade_data)
    
    if result.get('ok'):
        print("Gửi thông báo giao dịch thành công!")
    else:
        print(f"Lỗi khi gửi thông báo giao dịch: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_telegram_notifier()