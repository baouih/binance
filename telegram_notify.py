#!/usr/bin/env python3
"""
Hệ thống thông báo qua Telegram cho bot giao dịch

Module này cho phép bot giao dịch gửi các thông báo quan trọng (tín hiệu, giao dịch,
cảnh báo, báo cáo hiệu suất) tới người dùng qua Telegram.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, List, Union, Optional
from datetime import datetime

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Lớp xử lý thông báo Telegram cho bot giao dịch, hỗ trợ gửi văn bản,
    biểu đồ và các báo cáo định kỳ.
    """
    
    def __init__(self, token: str = None, chat_id: str = None):
        """
        Khởi tạo TelegramNotifier.
        
        Args:
            token (str, optional): Bot token Telegram
            chat_id (str, optional): ID của chat nơi gửi tin nhắn
        """
        self.base_url = "https://api.telegram.org/bot"
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.token and self.chat_id)
        
        if not self.enabled:
            logger.warning("Telegram không được kích hoạt. Thiếu token hoặc chat_id.")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Gửi tin nhắn văn bản qua Telegram.
        
        Args:
            message (str): Nội dung tin nhắn
            parse_mode (str): Chế độ định dạng ("HTML" hoặc "Markdown")
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            logger.warning("Telegram không được kích hoạt. Bỏ qua gửi tin nhắn.")
            return False
        
        try:
            url = f"{self.base_url}{self.token}/sendMessage"
            params = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, params=params)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn qua Telegram: {e}")
            return False
    
    def send_photo(self, photo_path: str, caption: str = None, parse_mode: str = "HTML") -> bool:
        """
        Gửi hình ảnh qua Telegram.
        
        Args:
            photo_path (str): Đường dẫn đến file hình ảnh
            caption (str, optional): Chú thích cho hình ảnh
            parse_mode (str): Chế độ định dạng cho chú thích
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            logger.warning("Telegram không được kích hoạt. Bỏ qua gửi hình ảnh.")
            return False
        
        try:
            # Kiểm tra file có tồn tại không
            if not os.path.exists(photo_path):
                logger.error(f"File hình ảnh không tồn tại: {photo_path}")
                return False
                
            # Kiểm tra kích thước file
            if os.path.getsize(photo_path) == 0:
                logger.error(f"File hình ảnh trống: {photo_path}")
                return False
                
            url = f"{self.base_url}{self.token}/sendPhoto"
            data = {
                "chat_id": self.chat_id,
                "parse_mode": parse_mode
            }
            
            if caption:
                data["caption"] = caption
            
            # Mở file với tùy chọn xử lý lỗi
            try:
                with open(photo_path, "rb") as photo_file:
                    files = {"photo": photo_file}
                    response = requests.post(url, data=data, files=files)
                    
                    # Kiểm tra kết quả
                    if response.status_code == 200:
                        return True
                    else:
                        logger.error(f"Lỗi khi gửi hình ảnh: {response.status_code} - {response.text}")
                        return False
            except IOError as e:
                logger.error(f"Lỗi mở file hình ảnh: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi hình ảnh qua Telegram: {e}")
            return False
    
    def send_document(self, document_path: str, caption: str = None, parse_mode: str = "HTML") -> bool:
        """
        Gửi tài liệu (file) qua Telegram.
        
        Args:
            document_path (str): Đường dẫn đến file
            caption (str, optional): Chú thích cho tài liệu
            parse_mode (str): Chế độ định dạng cho chú thích
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            logger.warning("Telegram không được kích hoạt. Bỏ qua gửi tài liệu.")
            return False
        
        try:
            # Kiểm tra file có tồn tại không
            if not os.path.exists(document_path):
                logger.error(f"File tài liệu không tồn tại: {document_path}")
                return False
                
            # Kiểm tra kích thước file
            if os.path.getsize(document_path) == 0:
                logger.error(f"File tài liệu trống: {document_path}")
                return False
                
            url = f"{self.base_url}{self.token}/sendDocument"
            data = {
                "chat_id": self.chat_id,
                "parse_mode": parse_mode
            }
            
            if caption:
                data["caption"] = caption
            
            # Mở file với tùy chọn xử lý lỗi
            try:
                with open(document_path, "rb") as doc_file:
                    files = {"document": doc_file}
                    response = requests.post(url, data=data, files=files)
                    
                    # Kiểm tra kết quả
                    if response.status_code == 200:
                        return True
                    else:
                        logger.error(f"Lỗi khi gửi tài liệu: {response.status_code} - {response.text}")
                        return False
            except IOError as e:
                logger.error(f"Lỗi mở file tài liệu: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi tài liệu qua Telegram: {e}")
            return False
    
    def send_trade_signal(self, signal_info: Dict = None, symbol: str = None, signal: str = None, 
                         confidence: float = None, price: float = None, 
                         timeframe: str = None, description: str = None) -> bool:
        """
        Gửi tín hiệu giao dịch qua Telegram.
        
        Args:
            signal_info (Dict, optional): Dictionary chứa thông tin tín hiệu đầy đủ
            symbol (str, optional): Cặp giao dịch
            signal (str, optional): Loại tín hiệu ('BUY', 'SELL', 'NEUTRAL')
            confidence (float, optional): Độ tin cậy của tín hiệu (0-100)
            price (float, optional): Giá hiện tại
            timeframe (str, optional): Khung thời gian
            description (str, optional): Mô tả thêm về tín hiệu
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            # Nếu có dictionary thông tin tín hiệu, ưu tiên sử dụng thông tin từ đó
            if signal_info:
                symbol = signal_info.get("symbol", symbol)
                signal = signal_info.get("final_signal", signal_info.get("ml_signal", signal))
                confidence = signal_info.get("ml_confidence", confidence)
                if confidence is not None:
                    confidence *= 100  # Chuyển từ 0-1 sang 0-100
                price = signal_info.get("current_price", price)
                timeframe = signal_info.get("timeframe", timeframe)
                
                # Tạo mô tả từ thông tin phân tích
                if description is None and "market_regime" in signal_info:
                    regime = signal_info.get("market_regime", "")
                    composite_score = signal_info.get("composite_score", 0)
                    description = f"Chế độ thị trường: {regime.replace('_', ' ').title()}\n"
                    description += f"Điểm tổng hợp: {composite_score:.2f}"
            
            # Đảm bảo các giá trị mặc định hợp lệ
            signal = signal.upper() if signal else "NEUTRAL"
            confidence = confidence if confidence is not None else 50.0
            
            signal_emoji = "🔴 BÁN" if signal == "SELL" else "🟢 MUA" if signal == "BUY" else "⚪ TRUNG LẬP"
            
            # Xác định màu confidence
            confidence_color = "🟢" if confidence >= 75 else "🟡" if confidence >= 50 else "🔴"
            
            # Tạo tin nhắn
            message = f"<b>📊 TÍN HIỆU GIAO DỊCH</b>\n\n"
            if symbol:
                message += f"<b>Cặp:</b> {symbol}\n"
            if timeframe:
                message += f"<b>Khung TG:</b> {timeframe}\n"
            message += f"<b>Tín hiệu:</b> {signal_emoji}\n"
            message += f"<b>Độ tin cậy:</b> {confidence_color} {confidence:.1f}%\n"
            if price is not None:
                message += f"<b>Giá hiện tại:</b> ${price:.2f}\n"
            
            if description:
                message += f"\n<i>{description}</i>"
            
            message += f"\n\n<i>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi tín hiệu giao dịch qua Telegram: {e}")
            return False
    
    def send_position_closed(self, position_data: Dict = None, symbol: str = None, 
                          side: str = None, entry_price: float = None, exit_price: float = None,
                          quantity: float = None, pnl: float = None, pnl_percent: float = None,
                          exit_reason: str = None) -> bool:
        """
        Gửi thông báo đóng vị thế qua Telegram.
        
        Args:
            position_data (Dict, optional): Dictionary chứa thông tin vị thế đã đóng
            symbol (str, optional): Cặp giao dịch
            side (str, optional): Hướng vị thế ('BUY'/'SELL' hoặc 'LONG'/'SHORT')
            entry_price (float, optional): Giá vào lệnh
            exit_price (float, optional): Giá thoát lệnh
            quantity (float, optional): Số lượng
            pnl (float, optional): Lãi/lỗ (giá trị tuyệt đối)
            pnl_percent (float, optional): Lãi/lỗ (%)
            exit_reason (str, optional): Lý do thoát lệnh
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
            
        try:
            # Nếu có dictionary thông tin vị thế, ưu tiên sử dụng thông tin từ đó
            if position_data:
                symbol = position_data.get("symbol", symbol)
                side = position_data.get("side", position_data.get("type", side))
                entry_price = position_data.get("entry_price", entry_price)
                exit_price = position_data.get("exit_price", exit_price)
                quantity = position_data.get("quantity", quantity)
                pnl = position_data.get("pnl", pnl)
                pnl_percent = position_data.get("pnl_percent", pnl_percent)
                exit_reason = position_data.get("exit_reason", exit_reason)
            
            # Chuẩn hóa side
            if side:
                side = side.upper()
                side_display = "LONG" if side in ["BUY", "LONG"] else "SHORT" if side in ["SELL", "SHORT"] else side
                side_emoji = "🟢" if side in ["BUY", "LONG"] else "🔴" if side in ["SELL", "SHORT"] else "⚪"
            else:
                side_display = "N/A"
                side_emoji = "⚪"
            
            # Tính toán tổng giá trị nếu có thể
            total = None
            if quantity is not None and exit_price is not None:
                total = quantity * exit_price
            
            # Tạo tin nhắn
            message = f"<b>🔚 VỊ THẾ ĐÓNG</b>\n\n"
            if symbol:
                message += f"<b>Cặp:</b> {symbol}\n"
            message += f"<b>Vị thế:</b> {side_emoji} {side_display}\n"
            
            if quantity is not None:
                message += f"<b>Số lượng:</b> {quantity}\n"
            
            if entry_price is not None:
                message += f"<b>Giá vào:</b> ${entry_price:.2f}\n"
                
            if exit_price is not None:
                message += f"<b>Giá ra:</b> ${exit_price:.2f}\n"
                
            if total is not None:
                message += f"<b>Tổng giá trị:</b> ${total:.2f}\n"
            
            if pnl is not None:
                is_profit = pnl >= 0
                pnl_emoji = "✅" if is_profit else "❌"
                message += f"<b>Lãi/Lỗ:</b> {pnl_emoji} ${abs(pnl):.2f}"
                
                if pnl_percent is not None:
                    message += f" ({'+' if is_profit else '-'}{abs(pnl_percent):.2f}%)"
                
                message += "\n"
            
            if exit_reason:
                message += f"<b>Lý do:</b> {exit_reason}\n"
            
            message += f"\n<i>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo đóng vị thế qua Telegram: {e}")
            return False
    
    def send_trade_execution(self, symbol: str = None, side: str = None, quantity: float = None, 
                           price: float = None, total: float = None, pnl: float = None) -> bool:
        """
        Gửi thông báo thực hiện giao dịch qua Telegram.
        
        Args:
            symbol (str): Cặp giao dịch
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            quantity (float): Số lượng giao dịch
            price (float): Giá giao dịch
            total (float): Tổng giá trị giao dịch
            pnl (float, optional): Lãi/lỗ nếu là lệnh đóng vị thế
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            action_emoji = "🟢 MUA" if side == "BUY" else "🔴 BÁN"
            
            # Tạo tin nhắn
            message = f"<b>🔄 GIAO DỊCH</b>\n\n"
            message += f"<b>Cặp:</b> {symbol}\n"
            message += f"<b>Hành động:</b> {action_emoji}\n"
            message += f"<b>Số lượng:</b> {quantity}\n"
            message += f"<b>Giá:</b> ${price:.2f}\n"
            message += f"<b>Tổng:</b> ${total:.2f}\n"
            
            if pnl is not None:
                pnl_emoji = "✅" if pnl >= 0 else "❌"
                message += f"<b>Lãi/Lỗ:</b> {pnl_emoji} ${abs(pnl):.2f} ({'+' if pnl >= 0 else '-'}{abs(pnl/total)*100:.2f}%)\n"
            
            message += f"\n<i>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo giao dịch qua Telegram: {e}")
            return False
    
    def send_daily_report(self, performance_data: Dict) -> bool:
        """
        Gửi báo cáo hàng ngày qua Telegram.
        
        Args:
            performance_data (Dict): Dữ liệu hiệu suất
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            balance = performance_data.get('current_balance', 0)
            daily_pnl = performance_data.get('daily_pnl', 0)
            daily_trades = performance_data.get('daily_trades', 0)
            win_rate = performance_data.get('win_rate', 0) * 100
            positions = performance_data.get('open_positions', [])
            
            # Xác định emoji cho PnL
            pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
            
            # Tạo tin nhắn
            message = f"<b>🗓️ BÁO CÁO HÀNG NGÀY</b>\n\n"
            message += f"<b>Số dư:</b> ${balance:.2f}\n"
            message += f"<b>Lãi/Lỗ hôm nay:</b> {pnl_emoji} ${daily_pnl:.2f} ({'+' if daily_pnl >= 0 else ''}{(daily_pnl/balance)*100:.2f}%)\n"
            message += f"<b>Giao dịch hôm nay:</b> {daily_trades}\n"
            message += f"<b>Tỷ lệ thắng:</b> {win_rate:.1f}%\n\n"
            
            # Thêm thông tin vị thế đang mở
            if positions:
                message += "<b>Vị thế đang mở:</b>\n"
                for pos in positions:
                    sym = pos.get('symbol', '')
                    side = "🟢 LONG" if pos.get('type', '').upper() == 'LONG' else "🔴 SHORT"
                    entry = pos.get('entry_price', 0)
                    current = pos.get('current_price', 0)
                    pos_pnl = pos.get('pnl', 0)
                    pos_pnl_pct = pos.get('pnl_percent', 0)
                    
                    message += f"• {sym} {side} - Giá vào: ${entry:.2f}, Hiện tại: ${current:.2f}\n"
                    message += f"  P&L: {'✅' if pos_pnl >= 0 else '❌'} ${abs(pos_pnl):.2f} ({'+' if pos_pnl >= 0 else ''}{pos_pnl_pct:.2f}%)\n"
            else:
                message += "<i>Không có vị thế đang mở</i>\n"
            
            message += f"\n<i>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            # Gửi báo cáo
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo hàng ngày qua Telegram: {e}")
            return False
    
    def send_error_alert(self, error_message: str, error_type: str = "System Error",
                    severity: str = "medium") -> bool:
        """
        Gửi thông báo cảnh báo lỗi qua Telegram.
        
        Args:
            error_message (str): Nội dung thông báo lỗi
            error_type (str, optional): Loại lỗi
            severity (str, optional): Mức độ nghiêm trọng ('low', 'medium', 'high')
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        return self.send_error_notification(error_type, error_message, severity)
        
    def send_error_notification(self, error_type: str, description: str, 
                              severity: str = "medium") -> bool:
        """
        Gửi thông báo lỗi qua Telegram.
        
        Args:
            error_type (str): Loại lỗi
            description (str): Mô tả chi tiết về lỗi
            severity (str): Mức độ nghiêm trọng ('low', 'medium', 'high')
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            # Xác định emoji cho mức độ nghiêm trọng
            severity_emoji = "🔴" if severity == "high" else "🟠" if severity == "medium" else "🟡"
            
            # Tạo tin nhắn
            message = f"<b>{severity_emoji} LỖI HỆ THỐNG</b>\n\n"
            message += f"<b>Loại lỗi:</b> {error_type}\n"
            message += f"<b>Mức độ:</b> {severity.upper()}\n\n"
            message += f"<b>Chi tiết:</b>\n<pre>{description}</pre>\n"
            message += f"\n<i>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo lỗi qua Telegram: {e}")
            return False
            
    def send_startup_notification(self) -> bool:
        """
        Gửi thông báo khởi động hệ thống qua Telegram.
        
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not self.enabled:
            return False
        
        try:
            # Tạo tin nhắn
            message = f"<b>🚀 BOT GIAO DỊCH ĐÃ KHỞI ĐỘNG</b>\n\n"
            message += f"Hệ thống giao dịch tự động đã khởi động và đang hoạt động.\n"
            message += f"Bạn sẽ nhận được thông báo khi có tín hiệu hoặc giao dịch mới.\n\n"
            message += f"<i>Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo khởi động qua Telegram: {e}")
            return False

# Khởi tạo một instance toàn cục
telegram_notifier = TelegramNotifier()

def main():
    """Hàm chính để test module"""
    # Cấu hình token và chat_id (chỉ cho mục đích test)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Thiếu biến môi trường TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
        return
    
    # Khởi tạo notifier
    notifier = TelegramNotifier(token, chat_id)
    
    # Test gửi tin nhắn
    print("Gửi tin nhắn test...")
    success = notifier.send_message("<b>🧪 Tin nhắn kiểm tra</b>\n\nĐây là tin nhắn kiểm tra từ bot giao dịch.")
    print(f"Kết quả: {'Thành công' if success else 'Thất bại'}")
    
    # Test gửi tín hiệu giao dịch
    print("Gửi tín hiệu giao dịch test...")
    success = notifier.send_trade_signal(
        symbol="BTCUSDT",
        signal="BUY",
        confidence=85.5,
        price=67800.25,
        timeframe="1h",
        description="RSI oversold, MACD crossover, strong support at $67,500"
    )
    print(f"Kết quả: {'Thành công' if success else 'Thất bại'}")
    
    # Đợi 1 giây để tránh spam API
    time.sleep(1)
    
    # Test gửi báo cáo hàng ngày
    print("Gửi báo cáo hàng ngày test...")
    performance_data = {
        "current_balance": 10500.75,
        "daily_pnl": 250.35,
        "daily_trades": 5,
        "win_rate": 0.8,
        "open_positions": [
            {
                "symbol": "BTCUSDT",
                "type": "LONG",
                "entry_price": 67500.0,
                "current_price": 67800.25,
                "pnl": 150.25,
                "pnl_percent": 0.45
            }
        ]
    }
    success = notifier.send_daily_report(performance_data)
    print(f"Kết quả: {'Thành công' if success else 'Thất bại'}")

if __name__ == "__main__":
    main()