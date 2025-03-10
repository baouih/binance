#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý thông báo Telegram nâng cao
Hỗ trợ gửi thông báo, tín hiệu giao dịch, cập nhật vị thế và thông báo hệ thống
"""

import os
import requests
import json
import logging
import time
from datetime import datetime
import traceback

# Cấu hình logging
logger = logging.getLogger("telegram_notifier")

class TelegramNotifier:
    """
    Lớp quản lý thông báo Telegram
    Cung cấp các phương thức để gửi các loại thông báo khác nhau
    """
    
    def __init__(self, token=None, chat_id=None, config_file=None):
        """
        Khởi tạo với token và chat_id
        
        :param token: Telegram bot token
        :param chat_id: Telegram chat ID
        :param config_file: Đường dẫn đến file cấu hình (nếu không có token và chat_id)
        """
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.config = self.load_config(config_file)
        self.last_notification_time = {}
        self.api_url = f"https://api.telegram.org/bot{self.token}"
    
    def load_config(self, config_file=None):
        """
        Tải cấu hình từ file
        
        :param config_file: Đường dẫn đến file cấu hình
        :return: Dict cấu hình
        """
        try:
            # Nếu không có file cấu hình, thử tìm file mặc định
            if not config_file:
                config_file = "configs/telegram_config.json"
            
            if not os.path.exists(config_file):
                # Trả về cấu hình mặc định nếu không tìm thấy file
                return {
                    "notification_settings": {
                        "enable_trade_signals": True,
                        "enable_price_alerts": True,
                        "enable_position_updates": True,
                        "enable_sltp_alerts": True,
                        "min_price_change_percent": 3.0,
                        "price_alert_cooldown": 3600,
                        "position_update_interval": 3600,
                        "max_notifications_per_hour": 20,
                        "quiet_hours_start": 0,
                        "quiet_hours_end": 0
                    }
                }
            
            with open(config_file, "r") as f:
                config = json.load(f)
                return config
                
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Telegram: {str(e)}")
            # Trả về cấu hình mặc định nếu có lỗi
            return {
                "notification_settings": {
                    "enable_trade_signals": True,
                    "enable_price_alerts": True,
                    "enable_position_updates": True,
                    "enable_sltp_alerts": True,
                    "min_price_change_percent": 3.0,
                    "price_alert_cooldown": 3600,
                    "position_update_interval": 3600,
                    "max_notifications_per_hour": 20,
                    "quiet_hours_start": 0,
                    "quiet_hours_end": 0
                }
            }
    
    def is_valid_setup(self):
        """
        Kiểm tra xem đã cấu hình token và chat_id chưa
        
        :return: Boolean
        """
        return bool(self.token and self.chat_id)
    
    def is_in_quiet_hours(self):
        """
        Kiểm tra xem hiện tại có nằm trong "quiet hours" không
        
        :return: Boolean
        """
        # Lấy cấu hình quiet hours
        settings = self.config.get("notification_settings", {})
        quiet_start = settings.get("quiet_hours_start", 0)
        quiet_end = settings.get("quiet_hours_end", 0)
        
        # Nếu start = end = 0, không có quiet hours
        if quiet_start == 0 and quiet_end == 0:
            return False
        
        # Lấy giờ hiện tại
        current_hour = datetime.now().hour
        
        # Kiểm tra
        if quiet_start < quiet_end:  # VD: 22h - 6h
            return quiet_start <= current_hour < quiet_end
        else:  # VD: 22h - 6h (qua ngày)
            return current_hour >= quiet_start or current_hour < quiet_end
    
    def can_send_notification(self, notification_type):
        """
        Kiểm tra xem có thể gửi thông báo loại này không
        
        :param notification_type: Loại thông báo (trade_signals, price_alerts, position_updates, sltp_alerts)
        :return: Boolean
        """
        # Kiểm tra tính hợp lệ của cấu hình
        if not self.is_valid_setup():
            return False
        
        # Kiểm tra quiet hours
        if self.is_in_quiet_hours():
            return False
        
        # Kiểm tra cấu hình cho loại thông báo
        settings = self.config.get("notification_settings", {})
        
        if notification_type == "trade_signals":
            return settings.get("enable_trade_signals", True)
        elif notification_type == "price_alerts":
            return settings.get("enable_price_alerts", True)
        elif notification_type == "position_updates":
            return settings.get("enable_position_updates", True)
        elif notification_type == "sltp_alerts":
            return settings.get("enable_sltp_alerts", True)
        else:
            return True  # Các loại thông báo khác
    
    def check_cooldown(self, notification_type, identifier=None):
        """
        Kiểm tra cooldown cho loại thông báo
        
        :param notification_type: Loại thông báo
        :param identifier: ID để phân biệt (ví dụ: tên cặp tiền)
        :return: Boolean (True nếu đã hết cooldown)
        """
        # Tạo key duy nhất cho loại thông báo và identifier
        key = f"{notification_type}_{identifier}" if identifier else notification_type
        
        # Lấy thời gian hiện tại
        current_time = time.time()
        
        # Lấy cấu hình cooldown
        settings = self.config.get("notification_settings", {})
        cooldown = 0
        
        if notification_type == "price_alerts":
            cooldown = settings.get("price_alert_cooldown", 3600)
        elif notification_type == "position_updates":
            cooldown = settings.get("position_update_interval", 3600)
        else:
            cooldown = 300  # Mặc định 5 phút
        
        # Kiểm tra xem đã hết cooldown chưa
        if key in self.last_notification_time:
            last_time = self.last_notification_time[key]
            if (current_time - last_time) < cooldown:
                return False
        
        # Cập nhật thời gian gửi thông báo cuối cùng
        self.last_notification_time[key] = current_time
        return True
    
    def send_message(self, message, parse_mode="HTML"):
        """
        Gửi tin nhắn thông thường
        
        :param message: Nội dung tin nhắn
        :param parse_mode: Chế độ parse (HTML hoặc Markdown)
        :return: Boolean thành công/thất bại
        """
        if not self.is_valid_setup():
            logger.error("Thiếu thông tin token hoặc chat_id")
            return False
        
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Đã gửi tin nhắn thành công: {message[:50]}...")
                return True
            else:
                logger.error(f"Lỗi khi gửi tin nhắn: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi không xác định khi gửi tin nhắn: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def send_trade_signal(self, symbol, side, entry_price, stop_loss, take_profit, timeframe, strategy, confidence=None):
        """
        Gửi tín hiệu giao dịch
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param side: Hướng giao dịch (LONG hoặc SHORT)
        :param entry_price: Giá vào lệnh
        :param stop_loss: Giá stop loss
        :param take_profit: Giá take profit
        :param timeframe: Khung thời gian
        :param strategy: Tên chiến lược
        :param confidence: Độ tin cậy (0-100%)
        :return: Boolean thành công/thất bại
        """
        if not self.can_send_notification("trade_signals"):
            return False
        
        # Tính Risk/Reward
        if stop_loss and take_profit and entry_price:
            if side == "LONG":
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # SHORT
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk > 0:
                risk_reward = reward / risk
            else:
                risk_reward = 0
        else:
            risk_reward = 0
        
        # Tạo emoji cho side
        side_emoji = "🟢 LONG" if side == "LONG" else "🔴 SHORT"
        
        # Tạo emoji cho độ tin cậy
        confidence_stars = ""
        if confidence:
            num_stars = int((confidence / 100) * 5)
            confidence_stars = "⭐" * num_stars
        
        # Tạo nội dung tin nhắn
        message = f"""🚨 TÍN HIỆU GIAO DỊCH MỚI 🚨

Cặp: {symbol}
Hướng: {side_emoji}
Giá vào lệnh: {entry_price:.2f}
Stop Loss: {stop_loss:.2f}
Take Profit: {take_profit:.2f}
Risk/Reward: 1:{risk_reward:.2f}
Khung thời gian: {timeframe}
Chiến lược: {strategy}"""

        if confidence:
            message += f"\nĐộ tin cậy: {confidence_stars} ({confidence:.1f}%)"
        
        message += "\n\n💡 Đặt SL/TP theo mức được gợi ý để đảm bảo quản lý vốn!"
        
        return self.send_message(message)
    
    def send_price_alert(self, symbol, current_price, change_percent, timeframe, reason=None):
        """
        Gửi cảnh báo biến động giá
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param current_price: Giá hiện tại
        :param change_percent: % thay đổi
        :param timeframe: Khung thời gian
        :param reason: Lý do cảnh báo
        :return: Boolean thành công/thất bại
        """
        if not self.can_send_notification("price_alerts"):
            return False
        
        # Kiểm tra cooldown
        if not self.check_cooldown("price_alerts", symbol):
            return False
        
        # Kiểm tra % thay đổi tối thiểu
        settings = self.config.get("notification_settings", {})
        min_change = settings.get("min_price_change_percent", 3.0)
        
        if abs(change_percent) < min_change:
            return False
        
        # Tạo emoji dựa trên hướng thay đổi
        emoji = "📈" if change_percent > 0 else "📉"
        
        # Tạo nội dung tin nhắn
        message = f"""{emoji} CẢNH BÁO GIÁ {symbol} {emoji}

Giá hiện tại: {current_price}
Thay đổi: {'+' if change_percent > 0 else ''}{change_percent:.2f}%
Khung thời gian: {timeframe}"""

        if reason:
            message += f"\nLý do: {reason}"
        
        message += "\n\nCảnh báo này dựa trên các thay đổi đáng kể về giá."
        
        return self.send_message(message)
    
    def send_position_update(self, positions, account_balance, unrealized_pnl=None, daily_pnl=None):
        """
        Gửi cập nhật vị thế
        
        :param positions: List các vị thế đang mở
        :param account_balance: Số dư tài khoản
        :param unrealized_pnl: Lợi nhuận chưa thực hiện
        :param daily_pnl: Lợi nhuận trong ngày
        :return: Boolean thành công/thất bại
        """
        if not self.can_send_notification("position_updates"):
            return False
        
        # Kiểm tra cooldown
        if not self.check_cooldown("position_updates"):
            return False
        
        # Tính tổng giá trị vị thế
        total_position_value = sum(pos.get("amount", 0) * pos.get("entry_price", 0) for pos in positions)
        
        # Tính % margin
        margin_percent = (total_position_value / account_balance * 100) if account_balance > 0 else 0
        
        # Tạo nội dung tin nhắn
        message = f"""📊 CẬP NHẬT VỊ THẾ

Vị thế đang mở: {len(positions)}
"""
        
        # Thêm thông tin từng vị thế
        for pos in positions:
            symbol = pos.get("symbol", "")
            side = pos.get("side", "")
            side_emoji = "📈 LONG" if side == "LONG" else "📉 SHORT"
            amount = pos.get("amount", 0)
            entry_price = pos.get("entry_price", 0)
            mark_price = pos.get("mark_price", 0)
            unrealized_pos_pnl = pos.get("unrealized_pnl", 0)
            profit_percent = pos.get("profit_percent", 0)
            
            # Tạo emoji cho side
            side_emoji = "🟢" if side == "LONG" else "🔴"
            
            # Tính giá trị vị thế
            position_value = amount * entry_price
            
            message += f"""
{side_emoji} {symbol} {side_emoji} {side}
   Size: {amount:.4f} ({position_value:.2f} USDT)
   Entry: {entry_price:.2f} | Mark: {mark_price:.2f}
   P/L: {'+' if unrealized_pos_pnl >= 0 else ''}{unrealized_pos_pnl:.2f} USDT ({'+' if profit_percent >= 0 else ''}{profit_percent:.2f}%)
"""
        
        # Thêm tổng quan tài khoản
        message += f"""
Số dư tài khoản: {account_balance:.2f} USDT
Tổng vị thế: {total_position_value:.2f} USDT
Tỷ lệ margin: {margin_percent:.2f}%"""

        if unrealized_pnl is not None:
            message += f"\nUnrealized P/L: {'+' if unrealized_pnl >= 0 else ''}{unrealized_pnl:.2f} USDT"
        
        if daily_pnl is not None:
            daily_pnl_percent = (daily_pnl / account_balance * 100) if account_balance > 0 else 0
            message += f"\nP/L ngày: {'+' if daily_pnl >= 0 else ''}{daily_pnl:.2f} USDT ({'+' if daily_pnl_percent >= 0 else ''}{daily_pnl_percent:.2f}%)"
        
        return self.send_message(message)
    
    def send_sltp_update(self, symbol, side, old_sl=None, new_sl=None, old_tp=None, new_tp=None, reason=None):
        """
        Gửi thông báo cập nhật Stop Loss/Take Profit
        
        :param symbol: Cặp tiền, ví dụ BTCUSDT
        :param side: Hướng vị thế (LONG hoặc SHORT)
        :param old_sl: SL cũ
        :param new_sl: SL mới
        :param old_tp: TP cũ
        :param new_tp: TP mới
        :param reason: Lý do cập nhật
        :return: Boolean thành công/thất bại
        """
        if not self.can_send_notification("sltp_alerts"):
            return False
        
        # Tạo emoji cho side
        side_emoji = "📈" if side == "LONG" else "📉"
        
        # Tạo nội dung tin nhắn
        message = f"""🔄 CẬP NHẬT SL/TP 🔄

Cặp: {symbol}
Hướng: {side_emoji} {side}"""

        if old_sl is not None and new_sl is not None:
            message += f"\nStop Loss: {old_sl:.2f} ➡️ {new_sl:.2f}"
        elif new_sl is not None:
            message += f"\nStop Loss: {new_sl:.2f}"
        
        if old_tp is not None and new_tp is not None:
            message += f"\nTake Profit: {old_tp:.2f} ➡️ {new_tp:.2f}"
        elif new_tp is not None:
            message += f"\nTake Profit: {new_tp:.2f}"
        
        if reason:
            message += f"\nLý do: {reason}"
        
        message += "\n\nHệ thống đã tự động điều chỉnh mức SL/TP."
        
        return self.send_message(message)
    
    def send_system_status(self, uptime, account_balance, open_positions, daily_trades, daily_pnl=None, system_load=None):
        """
        Gửi thông báo trạng thái hệ thống
        
        :param uptime: Thời gian hoạt động (giây)
        :param account_balance: Số dư tài khoản
        :param open_positions: Số vị thế đang mở
        :param daily_trades: Số giao dịch trong ngày
        :param daily_pnl: Lợi nhuận trong ngày
        :param system_load: Thông tin tải hệ thống
        :return: Boolean thành công/thất bại
        """
        # Chuyển đổi uptime thành định dạng dễ đọc
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = ""
        if days > 0:
            uptime_str += f"{int(days)} ngày "
        if hours > 0:
            uptime_str += f"{int(hours)} giờ "
        if minutes > 0:
            uptime_str += f"{int(minutes)} phút "
        if seconds > 0 or uptime_str == "":
            uptime_str += f"{int(seconds)} giây"
        
        # Tạo nội dung tin nhắn
        message = f"""🤖 BÁO CÁO TRẠNG THÁI HỆ THỐNG

⏱️ Thời gian hoạt động: {uptime_str}
💰 Số dư tài khoản: {account_balance:.2f} USDT
📊 Vị thế đang mở: {open_positions}
🔄 Giao dịch hôm nay: {daily_trades}"""

        if daily_pnl is not None:
            pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
            daily_pnl_percent = (daily_pnl / account_balance * 100) if account_balance > 0 else 0
            message += f"\n{pnl_emoji} P/L hôm nay: {'+' if daily_pnl >= 0 else ''}{daily_pnl:.2f} USDT ({'+' if daily_pnl_percent >= 0 else ''}{daily_pnl_percent:.2f}%)"
        
        if system_load:
            message += f"\n⚙️ Tải hệ thống: {system_load}"
        
        message += f"\n\n🕒 Thời gian báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        return self.send_message(message)

# Hàm để thử nghiệm module
def test_telegram_notifier():
    """Hàm kiểm tra chức năng của TelegramNotifier"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("Đang kiểm tra TelegramNotifier...")
    
    # Kiểm tra biến môi trường
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Thiếu biến môi trường TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
        return
    
    # Khởi tạo notifier
    notifier = TelegramNotifier(token=token, chat_id=chat_id)
    
    # Kiểm tra gửi tin nhắn đơn giản
    print("Đang gửi tin nhắn kiểm tra...")
    message = f"🤖 Đây là tin nhắn kiểm tra. Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    if notifier.send_message(message):
        print("✅ Gửi tin nhắn thành công")
    else:
        print("❌ Gửi tin nhắn thất bại")
        return
    
    # Kiểm tra gửi tín hiệu giao dịch
    print("Đang gửi tín hiệu giao dịch...")
    if notifier.send_trade_signal(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=50000,
        stop_loss=49000,
        take_profit=52000,
        timeframe="1h",
        strategy="MACD + RSI",
        confidence=75
    ):
        print("✅ Gửi tín hiệu giao dịch thành công")
    else:
        print("❌ Gửi tín hiệu giao dịch thất bại")
    
    # Kiểm tra gửi cập nhật vị thế
    print("Đang gửi cập nhật vị thế...")
    positions = [
        {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "amount": 0.05,
            "entry_price": 50000,
            "mark_price": 50500,
            "unrealized_pnl": 25,
            "profit_percent": 1.0
        },
        {
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "amount": 1.5,
            "entry_price": 3000,
            "mark_price": 2950,
            "unrealized_pnl": 75,
            "profit_percent": 1.67
        }
    ]
    if notifier.send_position_update(
        positions=positions,
        account_balance=10000,
        unrealized_pnl=100,
        daily_pnl=250
    ):
        print("✅ Gửi cập nhật vị thế thành công")
    else:
        print("❌ Gửi cập nhật vị thế thất bại")
    
    print("Kiểm tra hoàn tất!")

if __name__ == "__main__":
    test_telegram_notifier()