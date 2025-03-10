#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import requests
import logging
import time
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("TelegramNotifier")

class TelegramNotifier:
    """
    Class xử lý thông báo Telegram cho bot giao dịch
    """
    
    def __init__(self, token=None, chat_id=None):
        """
        Khởi tạo TelegramNotifier
        
        Args:
            token (str, optional): Telegram Bot Token
            chat_id (str, optional): Telegram Chat ID
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.connected = self._check_connection()
        self.last_message_time = 0
        self.message_queue = []
    
    def _check_connection(self):
        """
        Kiểm tra kết nối tới Telegram API
        
        Returns:
            bool: True nếu kết nối thành công, False nếu không
        """
        if not self.token or not self.chat_id:
            logger.warning("Thiếu Telegram Bot Token hoặc Chat ID")
            return False
        
        try:
            # Kiểm tra kết nối bằng cách gọi API getMe
            response = requests.get(f"{self.base_url}/getMe")
            data = response.json()
            
            if data.get("ok"):
                logger.info(f"Kết nối Telegram thành công. Bot: {data['result']['username']}")
                return True
            else:
                logger.error(f"Kết nối Telegram thất bại: {data.get('description', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}")
            return False
    
    def send_message(self, message, parse_mode="HTML"):
        """
        Gửi tin nhắn tới Telegram
        
        Args:
            message (str): Nội dung tin nhắn
            parse_mode (str, optional): Chế độ định dạng (HTML, Markdown)
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.connected:
            logger.warning("Không kết nối được Telegram, bỏ qua gửi tin nhắn")
            return False
        
        # Tránh gửi quá nhiều tin nhắn trong thời gian ngắn
        current_time = time.time()
        if current_time - self.last_message_time < 1:  # Đợi ít nhất 1 giây giữa các tin nhắn
            time.sleep(1)
            current_time = time.time()
        
        try:
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(f"{self.base_url}/sendMessage", data=data)
            result = response.json()
            
            if result.get("ok"):
                logger.info("Gửi tin nhắn Telegram thành công")
                self.last_message_time = current_time
                return True
            else:
                logger.error(f"Gửi tin nhắn Telegram thất bại: {result.get('description', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn Telegram: {str(e)}")
            return False
    
    def send_trade_notification(self, trade_type, symbol, entry_price, stop_loss, take_profit, risk_level):
        """
        Gửi thông báo về giao dịch mới
        
        Args:
            trade_type (str): Loại giao dịch (BUY/SELL)
            symbol (str): Symbol giao dịch
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            take_profit (float): Giá take profit
            risk_level (float): Mức độ rủi ro (%)
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        direction = "🟢 LONG" if trade_type == "BUY" else "🔴 SHORT"
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
🤖 <b>THÔNG BÁO GIAO DỊCH MỚI</b>

🪙 <b>Coin:</b> {symbol}
📊 <b>Loại:</b> {direction}
⏱ <b>Thời gian:</b> {current_time}

💰 <b>Giá vào lệnh:</b> {entry_price}
🛑 <b>Stop Loss:</b> {stop_loss}
🎯 <b>Take Profit:</b> {take_profit}

⚠️ <b>Mức độ rủi ro:</b> {risk_level}%
        """
        
        return self.send_message(message)
    
    def send_close_position_notification(self, symbol, trade_type, entry_price, close_price, profit_usdt, profit_percent):
        """
        Gửi thông báo về đóng vị thế
        
        Args:
            symbol (str): Symbol giao dịch
            trade_type (str): Loại giao dịch (BUY/SELL)
            entry_price (float): Giá vào lệnh
            close_price (float): Giá đóng lệnh
            profit_usdt (float): Lợi nhuận (USDT)
            profit_percent (float): Lợi nhuận (%)
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        direction = "🟢 LONG" if trade_type == "BUY" else "🔴 SHORT"
        result_emoji = "✅" if profit_usdt >= 0 else "❌"
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
{result_emoji} <b>ĐÓNG VỊ THẾ</b>

🪙 <b>Coin:</b> {symbol}
📊 <b>Loại:</b> {direction}
⏱ <b>Thời gian:</b> {current_time}

💰 <b>Giá vào lệnh:</b> {entry_price}
💸 <b>Giá đóng lệnh:</b> {close_price}

💵 <b>Lợi nhuận:</b> {profit_usdt:.2f} USDT ({profit_percent:.2f}%)
        """
        
        return self.send_message(message)
    
    def send_market_update(self, symbol, current_price, change_24h, highest_24h, lowest_24h, volume_24h):
        """
        Gửi cập nhật về thị trường
        
        Args:
            symbol (str): Symbol
            current_price (float): Giá hiện tại
            change_24h (float): Thay đổi trong 24h (%)
            highest_24h (float): Giá cao nhất trong 24h
            lowest_24h (float): Giá thấp nhất trong 24h
            volume_24h (float): Khối lượng giao dịch trong 24h
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        change_emoji = "🟢" if change_24h >= 0 else "🔴"
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
📊 <b>CẬP NHẬT THỊ TRƯỜNG</b>

🪙 <b>Coin:</b> {symbol}
⏱ <b>Thời gian:</b> {current_time}

💰 <b>Giá hiện tại:</b> {current_price}
{change_emoji} <b>Thay đổi 24h:</b> {change_24h:.2f}%

📈 <b>Cao nhất 24h:</b> {highest_24h}
📉 <b>Thấp nhất 24h:</b> {lowest_24h}
📊 <b>Khối lượng 24h:</b> {volume_24h}
        """
        
        return self.send_message(message)
    
    def send_error_notification(self, error_message):
        """
        Gửi thông báo lỗi
        
        Args:
            error_message (str): Thông báo lỗi
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        message = f"""
❌ <b>LỖI HỆ THỐNG</b>

⏱ <b>Thời gian:</b> {current_time}

🔍 <b>Chi tiết lỗi:</b>
<code>{error_message}</code>

⚠️ Vui lòng kiểm tra hệ thống!
        """
        
        return self.send_message(message)

def main():
    """Hàm chính để kiểm tra Telegram Notifier"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.error("Thiếu Telegram Bot Token hoặc Chat ID")
        return
    
    notifier = TelegramNotifier(token, chat_id)
    
    if notifier.connected:
        notifier.send_message("🤖 Telegram Notifier đã kết nối thành công!")
        
        # Thử gửi thông báo giao dịch
        notifier.send_trade_notification(
            trade_type="BUY",
            symbol="BTCUSDT",
            entry_price=50000,
            stop_loss=49000,
            take_profit=52000,
            risk_level=10
        )
    else:
        print("Không kết nối được Telegram")

if __name__ == "__main__":
    main()