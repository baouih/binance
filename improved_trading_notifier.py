#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module cung cấp chức năng thông báo giao dịch với nhiều thông tin chi tiết
Hỗ trợ thông báo qua Telegram với các loại thông báo khác nhau
Cung cấp phân tích thị trường, tín hiệu giao dịch, và trạng thái vị thế
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Union, Optional, Any
import traceback

# Import telegram notifier
try:
    from telegram_notifier import TelegramNotifier
except ImportError:
    pass

# Thiết lập logging
logger = logging.getLogger("improved_trading_notifier")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_notifications.log"),
        logging.StreamHandler()
    ]
)

class ImprovedTradingNotifier:
    """
    Lớp cung cấp thông báo giao dịch chi tiết
    """
    
    def __init__(self, use_telegram: bool = True):
        """
        Khởi tạo trading notifier
        
        Args:
            use_telegram: Có sử dụng Telegram không
        """
        self.use_telegram = use_telegram
        self.telegram = None
        
        # Khởi tạo Telegram notifier nếu được yêu cầu
        if self.use_telegram:
            try:
                self.telegram = TelegramNotifier()
                logger.info("Đã khởi tạo Telegram notifier")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Telegram notifier: {str(e)}")
                self.use_telegram = False
        
        # File log thông báo
        self.log_file = "trading_notifications.log"
        
        # Đảm bảo file log tồn tại
        if not os.path.exists(os.path.dirname(self.log_file)) and os.path.dirname(self.log_file):
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def _log_notification(self, message: str):
        """
        Ghi log thông báo
        
        Args:
            message: Nội dung thông báo
        """
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    
    def send_market_analysis(self, symbol: str, analysis: Dict[str, Any]):
        """
        Gửi thông báo phân tích thị trường
        
        Args:
            symbol: Cặp giao dịch
            analysis: Kết quả phân tích
        """
        # Tạo nội dung thông báo
        signal = analysis.get("signal", "KHÔNG XÁC ĐỊNH")
        score = analysis.get("score", 0)
        timeframe = analysis.get("timeframe", "1h")
        price = analysis.get("price", 0)
        
        # Xác định emoji dựa trên tín hiệu
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        
        # Tạo thông báo chi tiết
        message = (
            f"{emoji} PHÂN TÍCH THỊ TRƯỜNG {symbol} ({timeframe})\n\n"
            f"• Tín hiệu: {signal}\n"
            f"• Độ tin cậy: {score:.2f}%\n"
            f"• Giá hiện tại: {price:.2f} USDT\n"
        )
        
        # Thêm thông tin về hỗ trợ/kháng cự nếu có
        support_resistance = analysis.get("support_resistance", [])
        if support_resistance:
            supports = [sr.get("value", 0) for sr in support_resistance if sr.get("type", "").lower() == "support"]
            resistances = [sr.get("value", 0) for sr in support_resistance if sr.get("type", "").lower() == "resistance"]
            
            if supports:
                message += f"• Hỗ trợ gần nhất: {min(supports):.2f}\n"
            
            if resistances:
                message += f"• Kháng cự gần nhất: {max(resistances):.2f}\n"
        
        # Thêm thông tin chỉ báo kỹ thuật
        indicators = analysis.get("indicators", {})
        if indicators:
            message += "\n📊 CHỈ BÁO KỸ THUẬT:\n"
            
            # Các chỉ báo phổ biến
            for indicator_name, indicator_data in indicators.items():
                if isinstance(indicator_data, dict):
                    indicator_signal = indicator_data.get("signal", "KHÔNG XÁC ĐỊNH")
                    indicator_value = indicator_data.get("value", 0)
                    
                    indicator_emoji = "🟢" if indicator_signal == "BUY" else "🔴" if indicator_signal == "SELL" else "⚪"
                    message += f"{indicator_emoji} {indicator_name}: {indicator_value:.2f} ({indicator_signal})\n"
        
        # Thêm gợi ý giao dịch
        if score >= 70:
            if signal == "BUY":
                message += "\n💡 GỢI Ý: Xem xét mở vị thế LONG với SL dưới mức hỗ trợ gần nhất\n"
            elif signal == "SELL":
                message += "\n💡 GỢI Ý: Xem xét mở vị thế SHORT với SL trên mức kháng cự gần nhất\n"
        else:
            message += "\n💡 GỢI Ý: Theo dõi thêm và chờ tín hiệu mạnh hơn\n"
        
        # Thêm thời gian
        message += f"\n⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Gửi thông báo
        self._log_notification(message)
        logger.info(f"Đã ghi log phân tích thị trường {symbol}")
        
        if self.use_telegram and self.telegram:
            try:
                self.telegram.send_message(message)
                logger.info(f"Đã gửi phân tích thị trường {symbol} qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi phân tích thị trường qua Telegram: {str(e)}")
    
    def send_trade_entry(self, symbol: str, side: str, entry_price: float, 
                         quantity: float, stop_loss: float, take_profit: float, 
                         analysis: Dict[str, Any] = None):
        """
        Gửi thông báo mở vị thế
        
        Args:
            symbol: Cặp giao dịch
            side: Hướng giao dịch (BUY/SELL)
            entry_price: Giá vào lệnh
            quantity: Số lượng
            stop_loss: Giá stop loss
            take_profit: Giá take profit
            analysis: Kết quả phân tích (nếu có)
        """
        # Định dạng hướng giao dịch
        direction = "LONG" if side == "BUY" else "SHORT" if side == "SELL" else side
        emoji = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "⚪"
        
        # Tính toán % SL và TP
        sl_percent = abs((stop_loss - entry_price) / entry_price * 100)
        tp_percent = abs((take_profit - entry_price) / entry_price * 100)
        
        # Dự đoán kết quả lãi/lỗ tiềm năng
        potential_loss = abs(entry_price - stop_loss) * quantity
        potential_profit = abs(take_profit - entry_price) * quantity
        risk_reward_ratio = potential_profit / potential_loss if potential_loss != 0 else 0
        
        # Tạo thông báo chi tiết
        message = (
            f"{emoji} ĐÃ MỞ VỊ THẾ {direction} - {symbol}\n\n"
            f"• Giá vào lệnh: {entry_price:.2f} USDT\n"
            f"• Khối lượng: {quantity:.4f} ({quantity * entry_price:.2f} USDT)\n"
            f"• Stop Loss: {stop_loss:.2f} USDT ({sl_percent:.2f}%)\n"
            f"• Take Profit: {take_profit:.2f} USDT ({tp_percent:.2f}%)\n"
            f"• Tỷ lệ lãi/lỗ: {risk_reward_ratio:.2f} (RR)\n"
            f"• Lỗ tối đa: {potential_loss:.2f} USDT\n"
            f"• Lãi tiềm năng: {potential_profit:.2f} USDT\n"
        )
        
        # Thêm thông tin phân tích nếu có
        if analysis:
            score = analysis.get("score", 0)
            timeframe = analysis.get("timeframe", "1h")
            
            message += (
                f"\n📊 PHÂN TÍCH THỊ TRƯỜNG:\n"
                f"• Khung thời gian: {timeframe}\n"
                f"• Điểm tín hiệu: {score:.2f}%\n"
            )
            
            # Thêm thông tin chỉ báo
            indicators = analysis.get("indicators", {})
            if indicators:
                message += "• Chỉ báo hỗ trợ:\n"
                for name, data in list(indicators.items())[:3]:  # Chỉ hiển thị 3 chỉ báo hàng đầu
                    if isinstance(data, dict) and data.get("signal") == side:
                        message += f"  ✓ {name}\n"
        
        # Thêm gợi ý quản lý vị thế
        message += (
            f"\n💡 GỢI Ý QUẢN LÝ VỊ THẾ:\n"
            f"• Theo dõi vùng {stop_loss:.2f} để kích hoạt SL nếu cần\n"
            f"• Cân nhắc di chuyển SL về hòa vốn khi giá đạt {(entry_price + (take_profit - entry_price) * 0.3):.2f}\n"
            f"• Có thể chốt một phần khi đạt {(entry_price + (take_profit - entry_price) * 0.5):.2f}\n"
        )
        
        # Thêm thời gian
        message += f"\n⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Gửi thông báo
        self._log_notification(message)
        logger.info(f"Đã ghi log mở vị thế {direction} cho {symbol}")
        
        if self.use_telegram and self.telegram:
            try:
                self.telegram.send_message(message)
                logger.info(f"Đã gửi thông báo mở vị thế {direction} cho {symbol} qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo mở vị thế qua Telegram: {str(e)}")
    
    def send_trade_exit(self, symbol: str, side: str, entry_price: float, 
                        exit_price: float, quantity: float,
                        profit_loss: float, profit_loss_percent: float,
                        exit_reason: str = "Lệnh đóng thủ công"):
        """
        Gửi thông báo đóng vị thế
        
        Args:
            symbol: Cặp giao dịch
            side: Hướng giao dịch (BUY/SELL)
            entry_price: Giá vào lệnh
            exit_price: Giá đóng lệnh
            quantity: Số lượng
            profit_loss: Lãi/lỗ (tuyệt đối)
            profit_loss_percent: Lãi/lỗ (%)
            exit_reason: Lý do đóng lệnh
        """
        # Định dạng hướng giao dịch
        direction = "LONG" if side == "BUY" else "SHORT" if side == "SELL" else side
        
        # Xác định emoji dựa trên lãi/lỗ
        if profit_loss > 0:
            emoji = "✅"
            result = "THẮNG"
        else:
            emoji = "❌"
            result = "THUA"
        
        # Tạo thông báo chi tiết
        message = (
            f"{emoji} ĐÃ ĐÓNG VỊ THẾ {direction} - {symbol} ({result})\n\n"
            f"• Giá vào lệnh: {entry_price:.2f} USDT\n"
            f"• Giá đóng lệnh: {exit_price:.2f} USDT\n"
            f"• Khối lượng: {quantity:.4f} ({quantity * entry_price:.2f} USDT)\n"
            f"• Kết quả: {profit_loss_percent:+.2f}% ({profit_loss:+.2f} USDT)\n"
            f"• Lý do đóng: {exit_reason}\n"
        )
        
        # Thêm tổng kết
        message += (
            f"\n📊 TỔNG KẾT:\n"
            f"• Tổng vốn giao dịch: {quantity * entry_price:.2f} USDT\n"
            f"• Giá trị hoàn trả: {quantity * exit_price:.2f} USDT\n"
            f"• Lãi/lỗ: {profit_loss:+.2f} USDT ({profit_loss_percent:+.2f}%)\n"
        )
        
        # Thêm gợi ý cho lần giao dịch tiếp theo
        if profit_loss > 0:
            message += (
                f"\n💡 GỢI Ý CHO LẦN SAU:\n"
                f"• Giữ phương pháp giao dịch hiện tại\n"
                f"• Xem xét tăng kích thước vị thế nếu các điều kiện tương tự\n"
            )
        else:
            message += (
                f"\n💡 GỢI Ý CHO LẦN SAU:\n"
                f"• Xem xét điều chỉnh điểm vào lệnh hoặc SL\n"
                f"• Có thể giảm kích thước vị thế để quản lý rủi ro tốt hơn\n"
            )
        
        # Thêm thời gian
        message += f"\n⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Gửi thông báo
        self._log_notification(message)
        logger.info(f"Đã ghi log đóng vị thế {direction} cho {symbol}, PL: {profit_loss:+.2f} USDT")
        
        if self.use_telegram and self.telegram:
            try:
                self.telegram.send_message(message)
                logger.info(f"Đã gửi thông báo đóng vị thế {direction} cho {symbol} qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo đóng vị thế qua Telegram: {str(e)}")
    
    def send_trading_error(self, error_info: Dict[str, Any]):
        """
        Gửi thông báo lỗi giao dịch
        
        Args:
            error_info: Thông tin lỗi
        """
        # Trích xuất thông tin lỗi
        error_code = error_info.get("error_code", "UNKNOWN")
        error_message = error_info.get("error_message", "Lỗi không xác định")
        description = error_info.get("description", "")
        solution = error_info.get("solution", "")
        context = error_info.get("context", {})
        
        # Trích xuất thông tin giao dịch từ ngữ cảnh
        symbol = context.get("symbol", "N/A")
        side = context.get("side", "N/A")
        
        # Tạo thông báo chi tiết
        message = (
            f"⚠️ LỖI KHI GIAO DỊCH {symbol}\n\n"
            f"• Mã lỗi: {error_code}\n"
            f"• Thông báo: {error_message[:100]}...\n"
            f"• Mô tả: {description}\n"
            f"• Giải pháp: {solution}\n"
        )
        
        # Thêm thông tin giao dịch nếu có
        if symbol != "N/A" and side != "N/A":
            direction = "LONG" if side == "BUY" else "SHORT" if side == "SELL" else side
            message += (
                f"\n📊 CHI TIẾT GIAO DỊCH LỖI:\n"
                f"• Cặp giao dịch: {symbol}\n"
                f"• Hướng: {direction}\n"
            )
            
            # Thêm các thông tin khác nếu có
            for key, value in context.items():
                if key not in ["symbol", "side"] and value is not None:
                    message += f"• {key}: {value}\n"
        
        # Thêm thời gian
        message += f"\n⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Gửi thông báo
        self._log_notification(message)
        logger.info(f"Đã ghi log lỗi giao dịch: {error_code}")
        
        if self.use_telegram and self.telegram:
            try:
                self.telegram.send_message(message)
                logger.info(f"Đã gửi thông báo lỗi giao dịch qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo lỗi giao dịch qua Telegram: {str(e)}")
    
    def send_account_status(self, account_info: Dict[str, Any], positions: List[Dict[str, Any]] = None):
        """
        Gửi thông báo trạng thái tài khoản
        
        Args:
            account_info: Thông tin tài khoản
            positions: Danh sách vị thế hiện tại
        """
        # Trích xuất thông tin tài khoản
        total_balance = account_info.get("total_balance", 0)
        available_balance = account_info.get("available_balance", 0)
        unrealized_pnl = account_info.get("unrealized_pnl", 0)
        margin_balance = account_info.get("margin_balance", 0)
        
        # Tạo thông báo chi tiết
        message = (
            f"📊 TRẠNG THÁI TÀI KHOẢN\n\n"
            f"• Tổng số dư: {total_balance:.2f} USDT\n"
            f"• Số dư khả dụng: {available_balance:.2f} USDT\n"
            f"• Lợi nhuận chưa thực hiện: {unrealized_pnl:+.2f} USDT\n"
            f"• Margin balance: {margin_balance:.2f} USDT\n"
        )
        
        # Thêm thông tin vị thế nếu có
        if positions and len(positions) > 0:
            message += "\n📈 VỊ THẾ HIỆN TẠI:\n"
            
            for i, position in enumerate(positions, 1):
                symbol = position.get("symbol", "N/A")
                side = position.get("side", "N/A")
                entry_price = position.get("entry_price", 0)
                current_price = position.get("current_price", 0)
                quantity = position.get("quantity", 0)
                pnl = position.get("pnl", 0)
                pnl_percent = position.get("pnl_percent", 0)
                
                direction = "LONG" if side == "BUY" else "SHORT" if side == "SELL" else side
                emoji = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "⚪"
                
                message += (
                    f"{emoji} {i}. {symbol} ({direction}):\n"
                    f"   Giá vào: {entry_price:.2f}, Giá hiện tại: {current_price:.2f}\n"
                    f"   Khối lượng: {quantity:.4f}, P/L: {pnl:+.2f} USDT ({pnl_percent:+.2f}%)\n"
                )
        else:
            message += "\n📈 VỊ THẾ HIỆN TẠI: Không có vị thế nào đang mở\n"
        
        # Thêm thời gian
        message += f"\n⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Gửi thông báo
        self._log_notification(message)
        logger.info(f"Đã ghi log trạng thái tài khoản")
        
        if self.use_telegram and self.telegram:
            try:
                self.telegram.send_message(message)
                logger.info(f"Đã gửi thông báo trạng thái tài khoản qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo trạng thái tài khoản qua Telegram: {str(e)}")
    
    def send_system_status(self, services_status: Dict[str, bool], system_info: Dict[str, Any] = None):
        """
        Gửi thông báo trạng thái hệ thống
        
        Args:
            services_status: Trạng thái các dịch vụ
            system_info: Thông tin hệ thống (nếu có)
        """
        # Tạo thông báo chi tiết
        message = f"🖥️ TRẠNG THÁI HỆ THỐNG\n\n"
        
        # Thêm thông tin dịch vụ
        message += "📋 DỊCH VỤ:\n"
        for service_name, is_running in services_status.items():
            status_emoji = "✅" if is_running else "❌"
            status_text = "Đang chạy" if is_running else "Đã dừng"
            message += f"{status_emoji} {service_name}: {status_text}\n"
        
        # Thêm thông tin hệ thống nếu có
        if system_info:
            message += "\n💻 THÔNG TIN HỆ THỐNG:\n"
            
            # Thông tin CPU/RAM
            cpu_usage = system_info.get("cpu_usage", 0)
            memory_usage = system_info.get("memory_usage", 0)
            message += f"• CPU: {cpu_usage:.1f}%\n"
            message += f"• RAM: {memory_usage:.1f}%\n"
            
            # Thông tin thời gian hoạt động
            uptime = system_info.get("uptime", "N/A")
            if uptime != "N/A":
                message += f"• Thời gian hoạt động: {uptime}\n"
            
            # Thông tin lỗi
            error_count = system_info.get("error_count", 0)
            message += f"• Số lỗi gần đây: {error_count}\n"
            
            # Hiệu suất giao dịch
            trade_count = system_info.get("trade_count", 0)
            win_rate = system_info.get("win_rate", 0)
            if trade_count > 0:
                message += f"• Số lệnh giao dịch: {trade_count}\n"
                message += f"• Tỷ lệ thắng: {win_rate:.1f}%\n"
        
        # Thêm thời gian
        message += f"\n⏱️ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Gửi thông báo
        self._log_notification(message)
        logger.info(f"Đã ghi log trạng thái hệ thống")
        
        if self.use_telegram and self.telegram:
            try:
                self.telegram.send_message(message)
                logger.info(f"Đã gửi thông báo trạng thái hệ thống qua Telegram")
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo trạng thái hệ thống qua Telegram: {str(e)}")


# Singleton instance
_notifier_instance = None

def get_trading_notifier() -> ImprovedTradingNotifier:
    """Lấy singleton instance của ImprovedTradingNotifier"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = ImprovedTradingNotifier()
    return _notifier_instance


if __name__ == "__main__":
    # Test thông báo
    notifier = ImprovedTradingNotifier()
    
    # Test thông báo phân tích thị trường
    notifier.send_market_analysis("BTCUSDT", {
        "signal": "BUY",
        "score": 75.5,
        "timeframe": "1h",
        "price": 65000.0,
        "support_resistance": [
            {"type": "support", "value": 64000.0},
            {"type": "resistance", "value": 66000.0}
        ],
        "indicators": {
            "RSI": {"signal": "BUY", "value": 42.5},
            "MACD": {"signal": "BUY", "value": 100.5},
            "Bollinger": {"signal": "NEUTRAL", "value": 0}
        }
    })
    
    print("Đã gửi thông báo test")