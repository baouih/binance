"""
Hệ thống thông báo qua Telegram cho bot giao dịch

Module này cho phép bot giao dịch gửi các thông báo quan trọng (tín hiệu, giao dịch,
cảnh báo, báo cáo hiệu suất) tới người dùng qua Telegram.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_notify")

class TelegramNotifier:
    """Lớp xử lý thông báo Telegram cho bot giao dịch"""
    
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Khởi tạo Telegram Notifier.
        
        Args:
            token (str, optional): Telegram Bot API token. Nếu None, sẽ lấy từ biến môi trường TELEGRAM_BOT_TOKEN
            chat_id (str, optional): Telegram chat ID. Nếu None, sẽ lấy từ biến môi trường TELEGRAM_CHAT_ID
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        
        if not self.token or not self.chat_id:
            logger.warning("Telegram notifier không được kích hoạt do thiếu token hoặc chat_id")
            logger.warning("Đặt TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID trong biến môi trường để kích hoạt")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram notifier đã được kích hoạt")
    
    def send_message(self, message: str) -> bool:
        """
        Gửi tin nhắn văn bản qua Telegram.
        
        Args:
            message (str): Nội dung tin nhắn
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            endpoint = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            response = requests.post(endpoint, json=data)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Lỗi gửi tin nhắn Telegram: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi gửi tin nhắn Telegram: {str(e)}")
            return False
    
    def send_trade_signal(self, signal_data: Dict) -> bool:
        """
        Gửi thông báo tín hiệu giao dịch.
        
        Args:
            signal_data (Dict): Dữ liệu tín hiệu giao dịch
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            # Tạo emoji cho tín hiệu
            signal = signal_data.get("signal", "neutral").lower()
            emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪️"
            
            # Định dạng tin nhắn
            message = f"<b>{emoji} TÍN HIỆU GIAO DỊCH</b>\n\n"
            message += f"<b>Cặp:</b> {signal_data.get('symbol', 'Unknown')}\n"
            message += f"<b>Tín hiệu:</b> {signal.upper()}\n"
            message += f"<b>Giá hiện tại:</b> ${signal_data.get('price', 0):,.2f}\n"
            message += f"<b>Độ tin cậy:</b> {signal_data.get('confidence', 0) * 100:.1f}%\n"
            message += f"<b>Chế độ thị trường:</b> {signal_data.get('market_regime', 'unknown')}\n"
            message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Thêm thông tin chi tiết
            if "individual_scores" in signal_data:
                message += "<b>Chi tiết chỉ báo:</b>\n"
                for indicator, score in signal_data["individual_scores"].items():
                    indicator_emoji = "🟢" if score > 0.1 else "🔴" if score < -0.1 else "⚪️"
                    message += f"{indicator_emoji} {indicator}: {score:.2f}\n"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi gửi tín hiệu giao dịch: {str(e)}")
            return False
    
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
        
        try:
            # Tạo emoji cho loại giao dịch
            side = trade_data.get("side", "").lower()
            emoji = "🟢" if side == "buy" else "🔴" if side == "sell" else "⚪️"
            
            # Định dạng tin nhắn
            message = f"<b>{emoji} GIAO DỊCH ĐÃ THỰC HIỆN</b>\n\n"
            message += f"<b>Cặp:</b> {trade_data.get('symbol', 'Unknown')}\n"
            message += f"<b>Hành động:</b> {side.upper()}\n"
            message += f"<b>Giá vào lệnh:</b> ${trade_data.get('entry_price', 0):,.2f}\n"
            message += f"<b>Số lượng:</b> {trade_data.get('quantity', 0):,.6f}\n"
            message += f"<b>Giá trị:</b> ${trade_data.get('value', 0):,.2f}\n"
            message += f"<b>Đòn bẩy:</b> {trade_data.get('leverage', 1)}x\n"
            message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Thêm thông tin rủi ro
            message += "<b>Quản lý rủi ro:</b>\n"
            message += f"🎯 Take Profit: ${trade_data.get('take_profit', 0):,.2f}\n"
            message += f"🛑 Stop Loss: ${trade_data.get('stop_loss', 0):,.2f}\n"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi gửi thông báo giao dịch: {str(e)}")
            return False
    
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
        
        try:
            # Tạo emoji cho kết quả
            pnl = position_data.get("pnl", 0)
            pnl_pct = position_data.get("pnl_percentage", 0)
            emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪️"
            
            # Định dạng tin nhắn
            message = f"<b>{emoji} VỊ THẾ ĐÃ ĐÓNG</b>\n\n"
            message += f"<b>Cặp:</b> {position_data.get('symbol', 'Unknown')}\n"
            message += f"<b>Hướng:</b> {position_data.get('side', '').upper()}\n"
            message += f"<b>Giá vào:</b> ${position_data.get('entry_price', 0):,.2f}\n"
            message += f"<b>Giá thoát:</b> ${position_data.get('exit_price', 0):,.2f}\n"
            message += f"<b>Lãi/Lỗ:</b> ${pnl:,.2f} ({pnl_pct:.2f}%)\n"
            message += f"<b>Lý do đóng:</b> {position_data.get('exit_reason', 'Unknown')}\n"
            message += f"<b>Thời gian nắm giữ:</b> {position_data.get('holding_time', 'Unknown')}\n"
            message += f"<b>Thời gian đóng:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi gửi thông báo đóng vị thế: {str(e)}")
            return False
    
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
        
        try:
            # Định dạng tin nhắn
            message = f"<b>📊 BÁO CÁO HIỆU SUẤT HÀNG NGÀY</b>\n\n"
            message += f"<b>Ngày:</b> {datetime.now().strftime('%Y-%m-%d')}\n"
            
            # Tổng quan
            message += "\n<b>TỔNG QUAN:</b>\n"
            message += f"💰 Số dư hiện tại: ${performance_data.get('current_balance', 0):,.2f}\n"
            message += f"📈 Lãi/Lỗ hôm nay: ${performance_data.get('daily_pnl', 0):,.2f} ({performance_data.get('daily_pnl_percentage', 0):.2f}%)\n"
            message += f"🔄 Giao dịch hôm nay: {performance_data.get('daily_trades', 0)}\n"
            message += f"✅ Tỷ lệ thắng: {performance_data.get('win_rate', 0) * 100:.1f}%\n"
            
            # Các vị thế đang mở
            open_positions = performance_data.get("open_positions", [])
            if open_positions:
                message += "\n<b>VỊ THẾ ĐANG MỞ:</b>\n"
                for pos in open_positions:
                    emoji = "🟢" if pos.get("unrealized_pnl", 0) > 0 else "🔴" if pos.get("unrealized_pnl", 0) < 0 else "⚪️"
                    message += f"{emoji} {pos.get('symbol')}: {pos.get('unrealized_pnl_percentage', 0):.2f}%\n"
            
            # Tóm tắt thị trường
            market_summary = performance_data.get("market_summary", {})
            if market_summary:
                message += "\n<b>TÓM TẮT THỊ TRƯỜNG:</b>\n"
                for symbol, data in market_summary.items():
                    message += f"📊 {symbol}: ${data.get('price', 0):,.2f} ({data.get('change_24h', 0):.2f}%)\n"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi gửi báo cáo hiệu suất: {str(e)}")
            return False
    
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
        
        try:
            # Định dạng tin nhắn
            message = f"<b>⚠️ CẢNH BÁO LỖI: {error_type}</b>\n\n"
            message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"<b>Thông báo lỗi:</b>\n{error_message}\n"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi gửi cảnh báo lỗi: {str(e)}")
            return False
    
    def send_startup_notification(self) -> bool:
        """
        Gửi thông báo khi bot khởi động.
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            message = f"<b>🚀 BOT GIAO DỊCH ĐÃ KHỞI ĐỘNG</b>\n\n"
            message += f"<b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"<b>Chế độ:</b> {'Thực tế' if os.environ.get('LIVE_MODE') == 'true' else 'Giả lập'}\n"
            message += f"<b>Phiên bản:</b> 1.0.0\n"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Lỗi gửi thông báo khởi động: {str(e)}")
            return False

# Tạo instance toàn cục
telegram_notifier = TelegramNotifier()