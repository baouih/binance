#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Telegram Notifier
=========================
Hệ thống thông báo Telegram nâng cao với các tính năng:
- Thông báo tín hiệu giao dịch
- Cảnh báo biến động giá
- Cập nhật vị thế
- Thông báo SL/TP
- Thông báo hệ thống

Sử dụng:
    from advanced_telegram_notifier import AdvancedTelegramNotifier
    
    # Khởi tạo
    notifier = AdvancedTelegramNotifier()
    
    # Gửi thông báo tín hiệu giao dịch
    notifier.notify_trade_signal(
        symbol="BTCUSDT",
        side="LONG",
        entry_price=85000.0,
        stop_loss=83000.0,
        take_profit=89000.0,
        risk_reward=2.0,
        timeframe="1h",
        strategy="Composite Strategy",
        confidence=75.0
    )
"""

import os
import json
import time
import logging
import datetime
import requests
from typing import List, Dict, Optional, Any, Union

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("advanced_telegram_notifier")

class AdvancedTelegramNotifier:
    """Hệ thống thông báo Telegram nâng cao"""
    
    def __init__(self, config_path: str = "configs/telegram_config.json"):
        """
        Khởi tạo AdvancedTelegramNotifier
        
        Args:
            config_path: Đường dẫn tới file cấu hình Telegram
        """
        self.config_path = config_path
        self.config = self.load_config()
        
        # Lấy token và chat_id từ config hoặc env
        token_from_config = self.config.get("bot_token")
        chat_id_from_config = self.config.get("chat_id")
        use_env_variables = self.config.get("use_env_variables", False)
        
        # Kiểm tra xem có phải dùng biến môi trường không
        if use_env_variables or token_from_config == "ENVIRONMENT" or not token_from_config:
            self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            logger.info("Sử dụng TELEGRAM_BOT_TOKEN từ biến môi trường")
        else:
            self.bot_token = token_from_config
            
        if use_env_variables or chat_id_from_config == "ENVIRONMENT" or not chat_id_from_config:
            self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            logger.info("Sử dụng TELEGRAM_CHAT_ID từ biến môi trường")
        else:
            self.chat_id = chat_id_from_config
            
        self.enabled = self.config.get("enabled", True)
        
        # Load settings
        self.settings = self.config.get("notification_settings", {})
        self.templates = self.config.get("message_templates", {})
        
        # Kiểm tra cấu hình
        if not self.bot_token:
            logger.warning("Chưa cấu hình TELEGRAM_BOT_TOKEN. Thông báo Telegram sẽ không hoạt động.")
        if not self.chat_id:
            logger.warning("Chưa cấu hình TELEGRAM_CHAT_ID. Thông báo Telegram sẽ không hoạt động.")
        
        # Theo dõi thông báo
        self.notification_count = 0
        self.last_notification_reset = time.time()
        self.last_price_alert = {}  # {symbol: timestamp}
    
    def load_config(self) -> Dict:
        """
        Load cấu hình từ file
        
        Returns:
            Dict: Cấu hình Telegram
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            else:
                # Tạo file cấu hình mặc định nếu chưa tồn tại
                return self.create_default_config()
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình Telegram: {str(e)}")
            return {}
    
    def create_default_config(self) -> Dict:
        """
        Tạo cấu hình mặc định
        
        Returns:
            Dict: Cấu hình mặc định
        """
        config = {
            "bot_token": "",
            "chat_id": "",
            "use_env_variables": True,
            "enabled": True,
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
            },
            "message_templates": {
                "startup": "🚀 HỆ THỐNG GIAO DỊCH TỰ ĐỘNG ĐÃ KHỞI ĐỘNG\n\nSố dư: {account_balance:.2f} USDT\nVị thế đang mở: {positions_count}\n\nThời gian: {date_time}",
                "trade_signal": "🚨 TÍN HIỆU GIAO DỊCH MỚI 🚨\n\nCặp: {symbol}\nHướng: {side_emoji} {side}\nGiá vào lệnh: {entry_price:.2f}\nStop Loss: {stop_loss:.2f}\nTake Profit: {take_profit:.2f}\nRisk/Reward: 1:{risk_reward:.2f}\nKhung thời gian: {timeframe}\nChiến lược: {strategy}\nĐộ tin cậy: {confidence_stars} ({confidence:.1f}%)\n\n💡 Đặt SL/TP theo mức được gợi ý để đảm bảo quản lý vốn!",
                "price_alert": "📈 CẢNH BÁO GIÁ {symbol} 📈\n\nGiá hiện tại: {current_price}\nThay đổi: {price_change:.2f}%\nKhung thời gian: {timeframe}\nLý do: {reason}\n\nCảnh báo này dựa trên các thay đổi đáng kể về giá.",
                "position_update": "📊 CẬP NHẬT VỊ THẾ\n\nVị thế đang mở: {positions_count}\n\n{positions_detail}\n\nSố dư tài khoản: {account_balance:.2f} USDT\nTổng vị thế: {total_position_size:.2f} USDT\nTỷ lệ margin: {margin_ratio:.2f}%\nUnrealized P/L: {unrealized_pnl:.2f} USDT\nP/L ngày: {daily_pnl:.2f} USDT ({daily_pnl_percent:.2f}%)",
                "sltp_update": "🔄 CẬP NHẬT SL/TP 🔄\n\nCặp: {symbol}\nHướng: {side_emoji} {side}\n{sl_update}{tp_update}\nLý do: {reason}\n\nHệ thống đã tự động điều chỉnh mức SL/TP.",
                "error": "⚠️ LỖI HỆ THỐNG ⚠️\n\nThời gian: {date_time}\nMô-đun: {module}\nMức độ: {severity}\nMô tả: {description}\n\nVui lòng kiểm tra log để biết thêm chi tiết."
            }
        }
        
        # Đảm bảo thư mục cha tồn tại
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Lưu config
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info(f"Đã tạo file cấu hình mặc định tại {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo file cấu hình mặc định: {str(e)}")
        
        return config
    
    def _should_send_notification(self) -> bool:
        """
        Kiểm tra xem có nên gửi thông báo không dựa trên các điều kiện:
        - Số lượng thông báo mỗi giờ
        - Thời gian im lặng
        
        Returns:
            bool: True nếu nên gửi thông báo
        """
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False
        
        # Kiểm tra thời gian im lặng
        quiet_start = self.settings.get("quiet_hours_start", 0)
        quiet_end = self.settings.get("quiet_hours_end", 0)
        
        if quiet_start != quiet_end:  # Nếu có cấu hình thời gian im lặng
            current_hour = datetime.datetime.now().hour
            if quiet_start < quiet_end:  # Ví dụ: 22h -> 6h
                if quiet_start <= current_hour < quiet_end:
                    logger.info(f"Hiện tại là thời gian im lặng ({quiet_start}h-{quiet_end}h). Không gửi thông báo.")
                    return False
            else:  # Ví dụ: 22h -> 6h (qua ngày)
                if current_hour >= quiet_start or current_hour < quiet_end:
                    logger.info(f"Hiện tại là thời gian im lặng ({quiet_start}h-{quiet_end}h). Không gửi thông báo.")
                    return False
        
        # Kiểm tra số lượng thông báo mỗi giờ
        now = time.time()
        max_per_hour = self.settings.get("max_notifications_per_hour", 20)
        
        # Reset bộ đếm nếu đã qua 1 giờ
        if now - self.last_notification_reset > 3600:
            self.notification_count = 0
            self.last_notification_reset = now
        
        # Kiểm tra số lượng tối đa
        if self.notification_count >= max_per_hour:
            logger.info(f"Đã đạt giới hạn thông báo mỗi giờ ({max_per_hour}). Không gửi thêm thông báo.")
            return False
        
        # Tăng bộ đếm
        self.notification_count += 1
        return True
    
    def send_message(self, text: str) -> bool:
        """
        Gửi tin nhắn tới Telegram
        
        Args:
            text: Nội dung tin nhắn
            
        Returns:
            bool: True nếu thành công
        """
        if not self._should_send_notification():
            return False
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Không thể gửi thông báo Telegram do thiếu bot token hoặc chat ID")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Đã gửi thông báo Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {response_data}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
            return False
    
    def notify_system_status(self, status: str, uptime: int = 0, account_balance: float = 0.0,
                             positions_count: int = 0, next_maintenance: Optional[str] = None) -> bool:
        """
        Thông báo trạng thái hệ thống
        
        Args:
            status: Trạng thái (running, stopped, error)
            uptime: Thời gian hoạt động (giây)
            account_balance: Số dư tài khoản
            positions_count: Số lượng vị thế
            next_maintenance: Thời gian bảo trì tiếp theo
            
        Returns:
            bool: True nếu thành công
        """
        # Format uptime
        uptime_str = ""
        if uptime > 0:
            days, remainder = divmod(uptime, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                uptime_str = f"{int(days)}d {int(hours)}h {int(minutes)}m"
            elif hours > 0:
                uptime_str = f"{int(hours)}h {int(minutes)}m"
            else:
                uptime_str = f"{int(minutes)}m {int(seconds)}s"
        
        # Tùy chỉnh emoji dựa vào trạng thái
        if status == "running":
            status_emoji = "🟢"
            status_text = "ĐANG CHẠY"
        elif status == "stopped":
            status_emoji = "🔴"
            status_text = "ĐÃ DỪNG"
        elif status == "error":
            status_emoji = "⚠️"
            status_text = "LỖI"
        else:
            status_emoji = "ℹ️"
            status_text = status.upper()
        
        # Tạo thông báo
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = self.templates.get("startup", "🚀 HỆ THỐNG GIAO DỊCH TỰ ĐỘNG").format(
            status_emoji=status_emoji,
            status=status_text,
            uptime=uptime_str,
            account_balance=account_balance,
            positions_count=positions_count,
            date_time=date_time,
            next_maintenance=next_maintenance or "Không có"
        )
        
        return self.send_message(message)
    
    def notify_trade_signal(self, symbol: str, side: str, entry_price: float, stop_loss: float,
                           take_profit: float, risk_reward: float, timeframe: str = "1h",
                           strategy: str = "", confidence: float = 0.0) -> bool:
        """
        Thông báo tín hiệu giao dịch
        
        Args:
            symbol: Cặp giao dịch
            side: Hướng (LONG/SHORT)
            entry_price: Giá vào lệnh
            stop_loss: Giá stop loss
            take_profit: Giá take profit
            risk_reward: Tỷ lệ Risk/Reward
            timeframe: Khung thời gian
            strategy: Chiến lược
            confidence: Độ tin cậy (0-100%)
            
        Returns:
            bool: True nếu thành công
        """
        if not self.settings.get("enable_trade_signals", True):
            return False
        
        # Format các giá trị
        side = side.upper()
        side_emoji = "🟢" if side == "LONG" else "🔴"
        
        # Tạo độ tin cậy bằng sao
        confidence_stars = ""
        if confidence > 0:
            stars_count = min(5, max(1, int(confidence / 20)))
            confidence_stars = "⭐" * stars_count
        
        # Tạo thông báo
        message = self.templates.get("trade_signal").format(
            symbol=symbol,
            side=side,
            side_emoji=side_emoji,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            timeframe=timeframe,
            strategy=strategy,
            confidence=confidence,
            confidence_stars=confidence_stars
        )
        
        return self.send_message(message)
    
    def notify_price_alert(self, symbol: str, current_price: Union[float, str], price_change: float,
                          timeframe: str = "15m", reason: str = "Significant movement") -> bool:
        """
        Thông báo cảnh báo giá
        
        Args:
            symbol: Cặp giao dịch
            current_price: Giá hiện tại
            price_change: Phần trăm thay đổi giá
            timeframe: Khung thời gian
            reason: Lý do cảnh báo
            
        Returns:
            bool: True nếu thành công
        """
        if not self.settings.get("enable_price_alerts", True):
            return False
        
        # Kiểm tra ngưỡng thay đổi giá tối thiểu
        min_change = self.settings.get("min_price_change_percent", 3.0)
        if abs(price_change) < min_change:
            return False
        
        # Kiểm tra thời gian chờ giữa các cảnh báo
        now = time.time()
        cooldown = self.settings.get("price_alert_cooldown", 3600)  # 1 giờ mặc định
        
        if symbol in self.last_price_alert and now - self.last_price_alert[symbol] < cooldown:
            logger.info(f"Đang trong thời gian chờ cho cảnh báo giá {symbol}. Bỏ qua.")
            return False
        
        # Cập nhật thời gian cảnh báo cuối cùng
        self.last_price_alert[symbol] = now
        
        # Tạo thông báo
        message = self.templates.get("price_alert").format(
            symbol=symbol,
            current_price=current_price,
            price_change=price_change,
            timeframe=timeframe,
            reason=reason
        )
        
        return self.send_message(message)
    
    def notify_position_update(self, positions: List[Dict], account_balance: float = 0.0,
                              unrealized_pnl: float = 0.0, daily_pnl: float = 0.0,
                              daily_pnl_percent: float = 0.0) -> bool:
        """
        Thông báo cập nhật vị thế
        
        Args:
            positions: Danh sách vị thế
            account_balance: Số dư tài khoản
            unrealized_pnl: Lợi nhuận chưa thực hiện
            daily_pnl: Lợi nhuận ngày
            daily_pnl_percent: Phần trăm lợi nhuận ngày
            
        Returns:
            bool: True nếu thành công
        """
        if not self.settings.get("enable_position_updates", True):
            return False
        
        if not positions:
            return False
        
        # Tính tổng giá trị vị thế và margin ratio
        total_position_size = 0.0
        for pos in positions:
            amt = abs(float(pos.get("positionAmt", 0)))
            price = float(pos.get("entryPrice", 0))
            total_position_size += amt * price
        
        margin_ratio = (total_position_size / account_balance * 100) if account_balance > 0 else 0
        
        # Format chi tiết vị thế
        positions_detail = ""
        for pos in positions:
            symbol = pos.get("symbol", "UNKNOWN")
            amt = float(pos.get("positionAmt", 0))
            side = "LONG" if amt > 0 else "SHORT"
            side_emoji = "🟢" if side == "LONG" else "🔴"
            chart_emoji = "📈" if side == "LONG" else "📉"
            entry_price = float(pos.get("entryPrice", 0))
            mark_price = float(pos.get("markPrice", 0))
            unrealized_profit = float(pos.get("unrealizedProfit", 0))
            
            # Tính % P/L
            position_size = abs(amt) * entry_price
            pnl_percent = (unrealized_profit / position_size * 100) if position_size > 0 else 0
            
            positions_detail += f"{side_emoji} {symbol} {chart_emoji} {side}\n"
            positions_detail += f"   Size: {abs(amt):.4f} ({abs(amt) * entry_price:.2f} USDT)\n"
            positions_detail += f"   Entry: {entry_price:.2f} | Mark: {mark_price:.2f}\n"
            positions_detail += f"   P/L: {'+' if unrealized_profit >= 0 else ''}{unrealized_profit:.2f} USDT ({'+' if pnl_percent >= 0 else ''}{pnl_percent:.2f}%)\n"
        
        # Tạo thông báo
        message = self.templates.get("position_update").format(
            positions_count=len(positions),
            positions_detail=positions_detail,
            account_balance=account_balance,
            total_position_size=total_position_size,
            margin_ratio=margin_ratio,
            unrealized_pnl=unrealized_pnl,
            daily_pnl=daily_pnl,
            daily_pnl_percent=daily_pnl_percent
        )
        
        return self.send_message(message)
    
    def notify_sltp_update(self, symbol: str, side: str, old_sl: float = 0, new_sl: float = 0,
                          old_tp: float = 0, new_tp: float = 0, reason: str = "manual") -> bool:
        """
        Thông báo cập nhật SL/TP
        
        Args:
            symbol: Cặp giao dịch
            side: Hướng (LONG/SHORT)
            old_sl: Giá SL cũ
            new_sl: Giá SL mới
            old_tp: Giá TP cũ
            new_tp: Giá TP mới
            reason: Lý do cập nhật
            
        Returns:
            bool: True nếu thành công
        """
        if not self.settings.get("enable_sltp_alerts", True):
            return False
        
        # Kiểm tra xem có sự thay đổi không
        sl_changed = old_sl > 0 and new_sl > 0 and old_sl != new_sl
        tp_changed = old_tp > 0 and new_tp > 0 and old_tp != new_tp
        
        if not sl_changed and not tp_changed:
            return False
        
        # Format các giá trị
        side = side.upper()
        side_emoji = "📈" if side == "LONG" else "📉"
        
        # Format lý do
        reason_text = reason
        if reason == "trailing_stop":
            reason_text = "Trailing Stop"
        elif reason == "manual":
            reason_text = "Điều chỉnh thủ công"
        elif reason == "breakeven":
            reason_text = "Điều chỉnh về điểm hòa vốn"
        
        # Tạo phần SL update
        sl_update = ""
        if sl_changed:
            sl_update = f"Stop Loss: {old_sl:.2f} ➡️ {new_sl:.2f}\n"
        
        # Tạo phần TP update
        tp_update = ""
        if tp_changed:
            tp_update = f"Take Profit: {old_tp:.2f} ➡️ {new_tp:.2f}\n"
        
        # Tạo thông báo
        message = self.templates.get("sltp_update").format(
            symbol=symbol,
            side=side,
            side_emoji=side_emoji,
            sl_update=sl_update,
            tp_update=tp_update,
            reason=reason_text
        )
        
        return self.send_message(message)
    
    def notify_error(self, description: str, module: str = "system", severity: str = "critical") -> bool:
        """
        Thông báo lỗi hệ thống
        
        Args:
            description: Mô tả lỗi
            module: Tên module gặp lỗi
            severity: Mức độ nghiêm trọng (critical, warning, info)
            
        Returns:
            bool: True nếu thành công
        """
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tạo thông báo
        message = self.templates.get("error").format(
            date_time=date_time,
            module=module,
            severity=severity,
            description=description
        )
        
        return self.send_message(message)


# For testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Advanced Telegram Notifier')
    parser.add_argument('--test', choices=['startup', 'trade', 'price', 'position', 'sltp', 'error'], 
                        help='Test notification type')
    args = parser.parse_args()
    
    notifier = AdvancedTelegramNotifier()
    
    if args.test == 'startup':
        notifier.notify_system_status('running', 3600, 10000.0, 3)
    elif args.test == 'trade':
        notifier.notify_trade_signal('BTCUSDT', 'LONG', 85000.0, 83000.0, 89000.0, 2.0, '1h', 'Breakout', 75.0)
    elif args.test == 'price':
        notifier.notify_price_alert('BTCUSDT', 86000, 5.2, '15m', 'Breakout detected')
    elif args.test == 'position':
        positions = [
            {"symbol": "BTCUSDT", "positionAmt": "0.025", "entryPrice": "85000", "markPrice": "86000", "unrealizedProfit": "25"},
            {"symbol": "ETHUSDT", "positionAmt": "-1.5", "entryPrice": "2200", "markPrice": "2210", "unrealizedProfit": "-15"}
        ]
        notifier.notify_position_update(positions, 13500.0, 10.0, 120.5, 0.89)
    elif args.test == 'sltp':
        notifier.notify_sltp_update('BTCUSDT', 'LONG', 83000.0, 83500.0, 0, 0, 'trailing_stop')
    elif args.test == 'error':
        notifier.notify_error('Lỗi kết nối tới API Binance', 'binance_api', 'critical')
    else:
        print("Sử dụng --test để kiểm tra các loại thông báo")