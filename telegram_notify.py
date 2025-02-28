"""
Hệ thống thông báo qua Telegram cho bot giao dịch

Module này cho phép bot giao dịch gửi các thông báo quan trọng (tín hiệu, giao dịch,
cảnh báo, báo cáo hiệu suất) tới người dùng qua Telegram.
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

# Thiết lập logging
logger = logging.getLogger('telegram_notify')

class TelegramNotifier:
    """Lớp xử lý thông báo Telegram cho bot giao dịch"""
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Khởi tạo Telegram Notifier.
        
        Args:
            token (str, optional): Telegram Bot API token. Nếu None, sẽ lấy từ biến môi trường TELEGRAM_BOT_TOKEN
            chat_id (str, optional): Telegram chat ID. Nếu None, sẽ lấy từ biến môi trường TELEGRAM_CHAT_ID
        """
        self.token = token or os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID')
        self.enabled = self.token is not None and self.chat_id is not None
        
        if not self.enabled:
            logger.warning("Telegram notifier không được kích hoạt do thiếu token hoặc chat_id")
            logger.warning("Đặt TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong biến môi trường để kích hoạt")
        else:
            logger.info(f"Telegram notifier đã được kích hoạt cho chat ID: {self.chat_id}")
    
    def send_message(self, message: str) -> bool:
        """
        Gửi tin nhắn văn bản qua Telegram.
        
        Args:
            message (str): Nội dung tin nhắn
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            logger.debug(f"Không gửi tin nhắn Telegram (không kích hoạt): {message}")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug(f"Đã gửi tin nhắn Telegram: {message[:50]}...")
                return True
            else:
                logger.error(f"Lỗi khi gửi tin nhắn Telegram: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn Telegram: {str(e)}")
            return False
    
    def send_trade_signal(self, signal_data: Dict) -> bool:
        """
        Gửi thông báo tín hiệu giao dịch.
        
        Args:
            signal_data (Dict): Dữ liệu tín hiệu giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled or signal_data.get('final_signal') == 'neutral':
            return False
        
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal = signal_data.get('final_signal', 'neutral')
        confidence = signal_data.get('ml_confidence', 0)
        regime = signal_data.get('market_regime', 'unknown')
        price = signal_data.get('current_price', 0)
        
        # Biểu tượng emoji
        emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪️"
        
        # Xây dựng tin nhắn
        message = f"<b>{emoji} TÍN HIỆU GIAO DỊCH: {symbol}</b>\n\n"
        message += f"<b>Tín hiệu:</b> {signal.upper()}\n"
        message += f"<b>Giá hiện tại:</b> ${price:,.2f}\n"
        message += f"<b>Độ tin cậy:</b> {confidence:.2%}\n"
        message += f"<b>Chế độ thị trường:</b> {regime}\n"
        message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Thêm chi tiết từ các chỉ báo riêng biệt
        if 'individual_scores' in signal_data:
            message += "\n<b>Chi tiết chỉ báo:</b>\n"
            for indicator, score in signal_data['individual_scores'].items():
                if abs(score) >= 0.3:  # Chỉ hiện thị các chỉ báo có tín hiệu đáng kể
                    direction = "↗️" if score > 0 else "↘️"
                    message += f"- {indicator}: {direction} {score:.2f}\n"
        
        return self.send_message(message)
    
    def send_trade_execution(self, trade_data: Dict) -> bool:
        """
        Gửi thông báo khi thực hiện giao dịch.
        
        Args:
            trade_data (Dict): Dữ liệu giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        symbol = trade_data.get('symbol', 'UNKNOWN')
        side = trade_data.get('side', 'UNKNOWN')
        quantity = trade_data.get('quantity', 0)
        price = trade_data.get('price', 0)
        
        # Biểu tượng emoji
        emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪️"
        
        # Xây dựng tin nhắn
        message = f"<b>{emoji} ĐÃ THỰC HIỆN GIAO DỊCH: {symbol}</b>\n\n"
        message += f"<b>Hành động:</b> {side}\n"
        message += f"<b>Số lượng:</b> {quantity}\n"
        message += f"<b>Giá:</b> ${price:,.2f}\n"
        message += f"<b>Tổng giá trị:</b> ${quantity * price:,.2f}\n"
        message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if 'simulated' in trade_data and trade_data['simulated']:
            message += "\n<i>Ghi chú: Đây là giao dịch giả lập</i>"
        
        return self.send_message(message)
    
    def send_position_closed(self, position_data: Dict) -> bool:
        """
        Gửi thông báo khi đóng vị thế.
        
        Args:
            position_data (Dict): Dữ liệu về vị thế đã đóng
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        symbol = position_data.get('symbol', 'UNKNOWN')
        side = position_data.get('side', 'UNKNOWN')
        entry_price = position_data.get('entry_price', 0)
        exit_price = position_data.get('exit_price', 0)
        quantity = position_data.get('quantity', 0)
        pnl = position_data.get('pnl', 0)
        
        # Biểu tượng emoji
        emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪️"
        
        # Xây dựng tin nhắn
        message = f"<b>{emoji} ĐÃ ĐÓNG VỊ THẾ: {symbol}</b>\n\n"
        message += f"<b>Loại vị thế:</b> {side}\n"
        message += f"<b>Giá vào:</b> ${entry_price:,.2f}\n"
        message += f"<b>Giá ra:</b> ${exit_price:,.2f}\n"
        message += f"<b>Số lượng:</b> {quantity}\n"
        message += f"<b>Lãi/Lỗ:</b> ${pnl:,.2f}\n"
        
        pnl_pct = (pnl / (entry_price * quantity)) * 100
        message += f"<b>Lãi/Lỗ (%):</b> {pnl_pct:,.2f}%\n"
        message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return self.send_message(message)
    
    def send_daily_report(self, performance_data: Dict) -> bool:
        """
        Gửi báo cáo hiệu suất hàng ngày.
        
        Args:
            performance_data (Dict): Dữ liệu hiệu suất
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        # Xây dựng tin nhắn
        message = f"<b>📊 BÁO CÁO HIỆU SUẤT HÀNG NGÀY</b>\n\n"
        message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Thông tin số dư
        balance = performance_data.get('balance', 0)
        message += f"<b>Số dư hiện tại:</b> ${balance:,.2f}\n"
        
        # Thông tin lãi/lỗ
        daily_pnl = performance_data.get('daily_pnl', 0)
        daily_pnl_pct = performance_data.get('daily_pnl_pct', 0)
        emoji = "📈" if daily_pnl >= 0 else "📉"
        message += f"<b>Lãi/Lỗ hôm nay:</b> {emoji} ${daily_pnl:,.2f} ({daily_pnl_pct:,.2f}%)\n\n"
        
        # Thông tin giao dịch
        trades = performance_data.get('trades', [])
        num_trades = len(trades)
        win_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        loss_trades = sum(1 for t in trades if t.get('pnl', 0) < 0)
        
        if num_trades > 0:
            win_rate = (win_trades / num_trades) * 100
            message += f"<b>Số giao dịch:</b> {num_trades}\n"
            message += f"<b>Thắng/Thua:</b> {win_trades}/{loss_trades}\n"
            message += f"<b>Tỷ lệ thắng:</b> {win_rate:.2f}%\n\n"
        else:
            message += "<b>Không có giao dịch nào hôm nay</b>\n\n"
        
        # Hiệu suất các cặp giao dịch
        if 'symbol_performance' in performance_data:
            message += "<b>Hiệu suất theo cặp:</b>\n"
            for symbol, perf in performance_data['symbol_performance'].items():
                symbol_emoji = "🟢" if perf.get('pnl', 0) >= 0 else "🔴"
                message += f"- {symbol_emoji} {symbol}: ${perf.get('pnl', 0):,.2f}\n"
        
        # Ghi chú
        message += "\n<i>Bot đang hoạt động bình thường.</i>"
        
        return self.send_message(message)
    
    def send_error_alert(self, error_message: str, error_type: str = "General") -> bool:
        """
        Gửi cảnh báo lỗi.
        
        Args:
            error_message (str): Thông báo lỗi
            error_type (str): Loại lỗi
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        # Xây dựng tin nhắn
        message = f"<b>⚠️ CẢNH BÁO LỖI: {error_type}</b>\n\n"
        message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"<b>Chi tiết:</b> {error_message}\n"
        
        return self.send_message(message)
    
    def send_startup_notification(self) -> bool:
        """
        Gửi thông báo khi bot khởi động.
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        message = (
            "<b>🤖 BOT GIAO DỊCH ĐÃ KHỞI ĐỘNG</b>\n\n"
            f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "<b>Trạng thái:</b> Đang hoạt động\n"
            "<b>Chế độ:</b> Giả lập (không có giao dịch thực)\n\n"
            "<i>Bot đang theo dõi thị trường và sẽ gửi tín hiệu khi có cơ hội giao dịch.</i>"
        )
        
        return self.send_message(message)

# Tạo instance khi import module
telegram_notifier = TelegramNotifier()