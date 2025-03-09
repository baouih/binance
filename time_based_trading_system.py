#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hệ thống giao dịch dựa trên thời gian tối ưu

Module này tích hợp chiến lược giao dịch tối ưu theo thời gian
vào hệ thống chính, cung cấp giao diện để thực hiện giao dịch
tại thời điểm tối ưu.
"""

import os
import sys
import json
import time
import logging
import argparse
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# Đường dẫn tương đối cho các module của hệ thống
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('time_based_trading_system.log')
    ]
)

logger = logging.getLogger('time_based_trading_system')

# Thử import các module khác
try:
    from time_optimized_strategy import TimeOptimizedStrategy
except ImportError:
    logger.error("Không thể import module TimeOptimizedStrategy. Hãy đảm bảo tệp time_optimized_strategy.py tồn tại")
    sys.exit(1)

try:
    from telegram_notifier import TelegramNotifier
except ImportError:
    # Giả lập TelegramNotifier nếu không import được
    class TelegramNotifier:
        def __init__(self, token=None, chat_id=None, config_path=None):
            self.enabled = False
            self.token = token
            self.chat_id = chat_id
        
        def send_message(self, message, parse_mode=None):
            logger.info(f"[TELEGRAM] {message}")
            return True

try:
    from binance_api import BinanceAPI
except ImportError:
    # Giả lập BinanceAPI nếu không import được
    class BinanceAPI:
        def __init__(self, api_key=None, api_secret=None, testnet=True):
            self.api_key = api_key
            self.api_secret = api_secret
            self.testnet = testnet
        
        def get_current_prices(self):
            return {
                "BTCUSDT": 83000.0,
                "ETHUSDT": 2100.0,
                "BNBUSDT": 600.0,
                "SOLUSDT": 150.0,
                "LINKUSDT": 20.0
            }
        
        def get_account_balance(self):
            return 10000.0
        
        def place_order(self, symbol, side, quantity, price=None, order_type="MARKET", time_in_force="GTC"):
            logger.info(f"Đặt lệnh {side} {symbol}, số lượng: {quantity}, giá: {price}, loại: {order_type}")
            return {"orderId": 12345, "status": "FILLED"}

class TimeBasedTradingSystem:
    """
    Hệ thống giao dịch dựa trên thời gian tối ưu
    """
    
    def __init__(
        self, 
        config_path: str = "configs/time_based_trading_config.json",
        strategy_config_path: str = "configs/time_optimized_strategy_config.json",
        telegram_config_path: str = "telegram_config.json",
        api_key: str = None,
        api_secret: str = None,
        use_testnet: bool = True
    ):
        """
        Khởi tạo hệ thống giao dịch

        Args:
            config_path (str, optional): Đường dẫn đến file cấu hình hệ thống. Defaults to "configs/time_based_trading_config.json".
            strategy_config_path (str, optional): Đường dẫn đến file cấu hình chiến lược. Defaults to "configs/time_optimized_strategy_config.json".
            telegram_config_path (str, optional): Đường dẫn đến file cấu hình Telegram. Defaults to "telegram_config.json".
            api_key (str, optional): API key Binance. Defaults to None.
            api_secret (str, optional): API secret Binance. Defaults to None.
            use_testnet (bool, optional): Sử dụng testnet Binance. Defaults to True.
        """
        self.config_path = config_path
        self.strategy_config_path = strategy_config_path
        self.telegram_config_path = telegram_config_path
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo chiến lược tối ưu
        self.strategy = TimeOptimizedStrategy(strategy_config_path)
        
        # Khởi tạo kết nối Telegram
        self.telegram = TelegramNotifier(
            token=api_key or self.config.get("telegram_token"),
            chat_id=api_secret or self.config.get("telegram_chat_id"),
            config_path=telegram_config_path
        )
        
        # Khởi tạo kết nối Binance
        self.binance = BinanceAPI(
            api_key=api_key or self.config.get("binance_api_key"),
            api_secret=api_secret or self.config.get("binance_api_secret"),
            testnet=use_testnet
        )
        
        # Biến theo dõi trạng thái
        self.is_running = False
        self.last_check_time = datetime.now()
        self.scheduler_thread = None
        self.active_symbols = self.config.get("symbols", ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"])
        self.market_data_cache = {}
        self.last_market_data_update = datetime.now() - timedelta(minutes=10)  # Đảm bảo cập nhật ngay lần đầu
        
        # Thiết lập múi giờ
        self.timezone_offset = self.config.get("timezone_offset", 7)
        if self.timezone_offset != self.strategy.timezone_offset:
            self.strategy.timezone_offset = self.timezone_offset
            self.strategy.config["timezone_offset"] = self.timezone_offset
            self.strategy._save_config()
        
        logger.info(f"Đã khởi tạo TimeBasedTradingSystem với timezone UTC+{self.timezone_offset}")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file

        Returns:
            Dict: Cấu hình
        """
        config = {}
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                logger.warning(f"Không tìm thấy file cấu hình {self.config_path}, sử dụng cấu hình mặc định")
                # Tạo cấu hình mặc định
                config = self._create_default_config()
                # Lưu cấu hình mặc định
                self._save_config(config)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            config = self._create_default_config()
        
        return config
    
    def _create_default_config(self) -> Dict:
        """
        Tạo cấu hình mặc định

        Returns:
            Dict: Cấu hình mặc định
        """
        default_config = {
            "enabled": True,
            "timezone_offset": 7,
            "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"],
            "default_risk_percent": 2.0,  # 2% rủi ro mỗi lệnh
            "max_risk_per_day": 10.0,  # 10% rủi ro tối đa mỗi ngày
            "notification": {
                "enabled": True,
                "optimal_entry_reminder": True,  # Nhắc nhở khi đến thời điểm vào lệnh tối ưu
                "upcoming_session_alert": True,  # Cảnh báo trước khi bắt đầu phiên giao dịch tối ưu
                "trade_execution": True,  # Thông báo khi thực hiện giao dịch
                "daily_summary": True  # Tóm tắt hàng ngày
            },
            "auto_trading": {
                "enabled": False,  # Mặc định tắt giao dịch tự động
                "min_confidence": 85.0,  # Chỉ giao dịch tự động khi điểm tin cậy >= 85%
                "require_confirmation": True  # Yêu cầu xác nhận trước khi giao dịch tự động
            },
            "market_data_update_interval": 5,  # Cập nhật dữ liệu thị trường mỗi 5 phút
            "check_interval": 1,  # Kiểm tra cơ hội giao dịch mỗi 1 phút
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return default_config
    
    def _save_config(self, config: Dict = None):
        """
        Lưu cấu hình vào file

        Args:
            config (Dict, optional): Cấu hình cần lưu. Defaults to None.
        """
        if config is None:
            config = self.config
        
        try:
            # Tạo thư mục chứa file cấu hình nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
    
    def update_market_data(self) -> None:
        """
        Cập nhật dữ liệu thị trường
        """
        now = datetime.now()
        update_interval = timedelta(minutes=self.config.get("market_data_update_interval", 5))
        
        # Chỉ cập nhật nếu đã quá thời gian cập nhật
        if now - self.last_market_data_update < update_interval:
            return
        
        logger.info("Đang cập nhật dữ liệu thị trường...")
        
        try:
            # Lấy giá hiện tại
            current_prices = self.binance.get_current_prices()
            
            # Cập nhật dữ liệu cho từng symbol
            for symbol in self.active_symbols:
                if symbol not in current_prices:
                    continue
                
                # TODO: Thêm phân tích kỹ thuật để tính toán các chỉ báo
                # Ví dụ: RSI, MACD, Bollinger Bands, etc.
                # Đây là nơi bạn sẽ thêm các tính toán kỹ thuật thực tế
                
                # Dữ liệu thị trường mẫu
                self.market_data_cache[symbol] = {
                    "price": current_prices[symbol],
                    "updated_at": now,
                    "rsi": 50,  # Placeholder, sẽ được tính toán thực tế
                    "macd_histogram": 0,  # Placeholder
                    "macd_signal_cross": False,  # Placeholder
                    "volume_ratio": 1.0,  # Placeholder
                    "trend": "neutral",  # Placeholder, sẽ được xác định thực tế
                    "strength": 0.5,  # Placeholder
                    "support_bounce": False,  # Placeholder
                    "resistance_rejection": False  # Placeholder
                }
            
            self.last_market_data_update = now
            logger.info(f"Đã cập nhật dữ liệu thị trường cho {len(self.market_data_cache)} symbols")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {e}")
    
    def check_trading_opportunities(self) -> List[Dict]:
        """
        Kiểm tra các cơ hội giao dịch dựa trên thời gian tối ưu

        Returns:
            List[Dict]: Danh sách các cơ hội giao dịch
        """
        # Cập nhật dữ liệu thị trường
        self.update_market_data()
        
        opportunities = []
        
        # Kiểm tra từng symbol
        for symbol in self.active_symbols:
            if symbol not in self.market_data_cache:
                continue
            
            market_data = self.market_data_cache[symbol]
            
            # Phân tích cơ hội vào lệnh
            opportunity = self.strategy.analyze_entry_opportunity(symbol, market_data)
            
            if opportunity["should_enter"]:
                opportunity["symbol"] = symbol
                opportunity["current_price"] = market_data["price"]
                opportunities.append(opportunity)
        
        return opportunities
    
    def send_opportunity_notification(self, opportunity: Dict) -> None:
        """
        Gửi thông báo về cơ hội giao dịch

        Args:
            opportunity (Dict): Thông tin về cơ hội giao dịch
        """
        if not self.config.get("notification", {}).get("enabled", True):
            return
        
        symbol = opportunity["symbol"]
        direction = opportunity["direction"].upper()
        confidence = opportunity["confidence"]
        session = opportunity["session"]
        price = opportunity["current_price"]
        
        message = f"🔔 *CƠ HỘI GIAO DỊCH* 🔔\n\n"
        message += f"🪙 *{symbol}* tại giá {price}\n"
        message += f"📈 Hướng: *{direction}*\n"
        message += f"⏰ Phiên: {session}\n"
        message += f"🌟 Độ tin cậy: {confidence:.2f}%\n\n"
        
        # Thêm thông tin về SL/TP theo R:R
        risk_reward_ratio = opportunity.get("risk_reward_ratio", 3.0)
        position_size = opportunity.get("position_size", 0.02)
        account_balance = self.binance.get_account_balance()
        position_amount = account_balance * position_size
        
        # Tính SL/TP
        if direction == "LONG":
            stop_loss_price = price * 0.93  # -7%
            take_profit_price = price * (1 + 0.07 * risk_reward_ratio)  # +21% mặc định
        else:  # SHORT
            stop_loss_price = price * 1.07  # +7%
            take_profit_price = price * (1 - 0.07 * risk_reward_ratio)  # -21% mặc định
        
        message += f"💰 *Thông tin giao dịch*:\n"
        message += f"• Vị thế: {position_amount:.2f} USDT ({position_size*100:.1f}% tài khoản)\n"
        message += f"• Stop Loss: {stop_loss_price:.2f}\n"
        message += f"• Take Profit: {take_profit_price:.2f}\n"
        message += f"• R:R: 1:{risk_reward_ratio}\n\n"
        
        # Thêm lời khuyên
        message += "💡 *Lời khuyên*:\n"
        message += "• Chỉ vào lệnh khi có tín hiệu kỹ thuật rõ ràng\n"
        message += "• Đặt SL/TP ngay khi vào lệnh\n"
        message += "• Tuân thủ quản lý vốn\n"
        
        # Thêm xác nhận (nếu cần)
        if self.config.get("auto_trading", {}).get("enabled", False) and self.config.get("auto_trading", {}).get("require_confirmation", True):
            message += "\n✅ *Giao dịch tự động*: Phản hồi 'OK' để xác nhận giao dịch này"
        
        # Gửi thông báo
        self.telegram.send_message(message, parse_mode="Markdown")
        
        logger.info(f"Đã gửi thông báo về cơ hội giao dịch {direction} {symbol}")
    
    def send_upcoming_session_alert(self, window: Dict, minutes_before: int = 10) -> None:
        """
        Gửi cảnh báo trước khi bắt đầu phiên giao dịch tối ưu

        Args:
            window (Dict): Thông tin về cửa sổ thời gian
            minutes_before (int, optional): Số phút trước khi bắt đầu phiên. Defaults to 10.
        """
        if not self.config.get("notification", {}).get("upcoming_session_alert", True):
            return
        
        window_name = window["name"]
        start_time_local = window.get("start_time", f"{window['start_hour']}:{window['start_minute']}")
        
        # Lấy thông tin khuyến nghị
        direction = window.get("direction", "both").upper()
        if direction == "BOTH":
            direction = "LONG/SHORT (phân tích thêm)"
        
        coins = self.strategy.optimal_coins.get(window_name, [])
        coins_str = ", ".join(coins) if coins else "Không có khuyến nghị cụ thể"
        
        message = f"⏰ *SẮP ĐẾN THỜI ĐIỂM GIAO DỊCH TỐI ƯU* ⏰\n\n"
        message += f"🕒 Phiên: *{window_name}* bắt đầu lúc {start_time_local}\n"
        message += f"📈 Hướng khuyến nghị: *{direction}*\n"
        message += f"🪙 Coin khuyến nghị: {coins_str}\n"
        message += f"🌟 Tỷ lệ thắng: {window.get('win_rate', 50.0):.1f}%\n\n"
        
        message += "🔍 *Chuẩn bị*:\n"
        message += "• Nhận diện vùng hỗ trợ/kháng cự quan trọng\n"
        message += "• Tìm kiếm các mẫu hình giá tiềm năng\n"
        message += "• Chuẩn bị sẵn chiến lược giao dịch\n"
        
        # Gửi thông báo
        self.telegram.send_message(message, parse_mode="Markdown")
        
        logger.info(f"Đã gửi cảnh báo trước phiên giao dịch {window_name}")
    
    def send_daily_summary(self) -> None:
        """
        Gửi tóm tắt hàng ngày
        """
        if not self.config.get("notification", {}).get("daily_summary", True):
            return
        
        # Lấy tóm tắt về chiến lược giao dịch
        summary = self.strategy.get_trading_summary()
        
        # Tạo thông báo
        message = f"📊 *TÓM TẮT GIAO DỊCH HÀNG NGÀY* 📊\n\n"
        
        # Thông tin về ngày
        now = datetime.now()
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        weekday_name = weekday_names[now.weekday()]
        
        message += f"📅 *Ngày*: {now.strftime('%d/%m/%Y')} ({weekday_name})\n"
        message += f"⏰ *Múi giờ*: UTC+{self.timezone_offset}\n\n"
        
        # Thông tin về các phiên tối ưu
        message += "🔝 *Top 3 thời điểm giao dịch tối ưu*:\n"
        for i, time_info in enumerate(summary.get("top_times", []), 1):
            message += f"{i}. {time_info['name']} ({time_info['start_time']} - {time_info['end_time']})\n"
            message += f"   • Tỷ lệ thắng: {time_info['win_rate']:.1f}%\n"
            message += f"   • Hướng: {time_info['direction'].upper()}\n"
            message += f"   • Coins: {', '.join(time_info['symbols']) if time_info['symbols'] else 'N/A'}\n"
        
        message += "\n📊 *Top 3 ngày giao dịch tốt nhất*:\n"
        for i, day_info in enumerate(summary.get("top_days", []), 1):
            message += f"{i}. {day_info['name']} - Tỷ lệ thắng: {day_info['win_rate']:.1f}% - Lệnh tối đa: {day_info['max_trades']}\n"
        
        # Thông tin về giao dịch hôm nay
        message += f"\n📈 *Giao dịch hôm nay*: {summary.get('trades_today_count', 0)}/{summary.get('max_trades_today', 5)}\n\n"
        
        # Kiểm tra xem thời gian hiện tại có phải thời gian tối ưu không
        is_optimal, window = self.strategy.is_optimal_time()
        
        if is_optimal:
            message += f"⚠️ *Hiện tại là thời gian tối ưu để vào lệnh*: {window['name']}\n"
            message += f"   • Hướng khuyến nghị: {window.get('direction', 'both').upper()}\n"
            
            # Hiển thị coin khuyến nghị
            coins = self.strategy.optimal_coins.get(window['name'], [])
            message += f"   • Coin khuyến nghị: {', '.join(coins) if coins else 'Không có khuyến nghị cụ thể'}\n"
        else:
            # Tìm thời gian tối ưu tiếp theo
            optimal_times = self.strategy.get_all_optimal_times()
            now = datetime.now()
            next_optimal = None
            earliest_diff = timedelta(days=1)
            
            for time_info in optimal_times:
                hour, minute = map(int, time_info["start_time"].split(":"))
                start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if start_time < now:
                    start_time = start_time + timedelta(days=1)
                
                diff = start_time - now
                if diff < earliest_diff:
                    earliest_diff = diff
                    next_optimal = time_info
            
            if next_optimal:
                hours, remainder = divmod(earliest_diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                message += f"⏱ *Thời gian tối ưu tiếp theo*: {next_optimal['name']} ({next_optimal['start_time']})\n"
                message += f"   • Còn {hours} giờ {minutes} phút nữa\n"
                message += f"   • Hướng khuyến nghị: {next_optimal['direction'].upper()}\n"
                message += f"   • Coins: {', '.join(next_optimal['symbols']) if next_optimal['symbols'] else 'N/A'}\n"
        
        # Gửi thông báo
        self.telegram.send_message(message, parse_mode="Markdown")
        
        logger.info("Đã gửi tóm tắt hàng ngày")
    
    def run_periodic_tasks(self) -> None:
        """
        Chạy các tác vụ định kỳ
        """
        now = datetime.now()
        
        # Cập nhật dữ liệu thị trường
        self.update_market_data()
        
        # Kiểm tra cơ hội giao dịch
        opportunities = self.check_trading_opportunities()
        
        for opportunity in opportunities:
            # Gửi thông báo về cơ hội giao dịch
            self.send_opportunity_notification(opportunity)
            
            # Nếu bật giao dịch tự động và độ tin cậy đủ cao, thực hiện giao dịch
            auto_trading = self.config.get("auto_trading", {})
            if auto_trading.get("enabled", False) and opportunity["confidence"] >= auto_trading.get("min_confidence", 85.0):
                # Nếu không yêu cầu xác nhận, thực hiện giao dịch ngay
                if not auto_trading.get("require_confirmation", True):
                    self.execute_trade(opportunity)
        
        # Reset danh sách giao dịch hàng ngày vào 00:00
        if now.hour == 0 and now.minute < 5 and (now - self.last_check_time).total_seconds() > 300:
            self.strategy.reset_daily_trades()
            
            # Gửi tóm tắt hàng ngày vào đầu ngày mới
            self.send_daily_summary()
        
        # Kiểm tra xem sắp đến thời điểm giao dịch tối ưu chưa
        for window in self.strategy.entry_windows:
            # Chuyển đổi giờ UTC sang giờ địa phương
            start_hour_local, start_minute = self.strategy._convert_utc_to_local(window["start_hour"], window["start_minute"])
            
            # Tính thời gian còn lại đến thời điểm bắt đầu
            start_time = now.replace(hour=start_hour_local, minute=start_minute, second=0, microsecond=0)
            if start_time < now:
                start_time = start_time + timedelta(days=1)
            
            time_diff = (start_time - now).total_seconds() / 60
            
            # Nếu còn 10 phút nữa là đến thời điểm bắt đầu, gửi cảnh báo
            if 9 <= time_diff <= 11:
                window_info = {
                    "name": window["name"],
                    "start_time": f"{start_hour_local:02d}:{start_minute:02d}",
                    "direction": window.get("direction", "both"),
                    "win_rate": window.get("win_rate", 50.0)
                }
                self.send_upcoming_session_alert(window_info)
        
        self.last_check_time = now
    
    def execute_trade(self, opportunity: Dict) -> Dict:
        """
        Thực hiện giao dịch dựa trên cơ hội

        Args:
            opportunity (Dict): Thông tin về cơ hội giao dịch

        Returns:
            Dict: Kết quả giao dịch
        """
        symbol = opportunity["symbol"]
        direction = opportunity["direction"]
        price = opportunity["current_price"]
        position_size = opportunity.get("position_size", 0.02)
        
        # Tính toán số lượng
        account_balance = self.binance.get_account_balance()
        position_amount = account_balance * position_size
        quantity = position_amount / price
        
        # Đặt lệnh
        side = "BUY" if direction == "long" else "SELL"
        result = self.binance.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity
        )
        
        logger.info(f"Đã thực hiện giao dịch {side} {symbol}, số lượng: {quantity}, giá: {price}")
        
        # Gửi thông báo nếu cần
        if self.config.get("notification", {}).get("trade_execution", True):
            message = f"✅ *ĐÃ THỰC HIỆN GIAO DỊCH* ✅\n\n"
            message += f"🪙 *{symbol}* - {side}\n"
            message += f"💰 Số lượng: {quantity}\n"
            message += f"💵 Giá: {price}\n"
            message += f"📊 Vị thế: {position_amount} USDT ({position_size*100:.1f}% tài khoản)\n\n"
            
            # Tính SL/TP
            risk_reward_ratio = opportunity.get("risk_reward_ratio", 3.0)
            if direction == "long":
                stop_loss_price = price * 0.93  # -7%
                take_profit_price = price * (1 + 0.07 * risk_reward_ratio)  # +21% mặc định
            else:  # short
                stop_loss_price = price * 1.07  # +7%
                take_profit_price = price * (1 - 0.07 * risk_reward_ratio)  # -21% mặc định
            
            message += f"🛑 Stop Loss: {stop_loss_price:.2f}\n"
            message += f"🎯 Take Profit: {take_profit_price:.2f}\n"
            
            self.telegram.send_message(message, parse_mode="Markdown")
        
        return result
    
    def start(self) -> None:
        """
        Bắt đầu hệ thống giao dịch
        """
        if self.is_running:
            logger.warning("Hệ thống đã đang chạy")
            return
        
        self.is_running = True
        
        # Lên lịch kiểm tra định kỳ
        check_interval = self.config.get("check_interval", 1)  # Mặc định 1 phút
        schedule.every(check_interval).minutes.do(self.run_periodic_tasks)
        
        # Lên lịch gửi tóm tắt hàng ngày
        schedule.every().day.at("18:00").do(self.send_daily_summary)
        
        logger.info(f"Đã bắt đầu hệ thống giao dịch dựa trên thời gian tối ưu (kiểm tra mỗi {check_interval} phút)")
        
        # Gửi thông báo khởi động
        startup_message = f"🚀 *HỆ THỐNG GIAO DỊCH THEO THỜI GIAN TỐI ƯU ĐÃ KHỞI ĐỘNG* 🚀\n\n"
        startup_message += f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        startup_message += f"🌐 Múi giờ: UTC+{self.timezone_offset}\n"
        startup_message += f"💎 Coin theo dõi: {', '.join(self.active_symbols)}\n\n"
        
        # Thêm thông tin về cấu hình
        auto_trading = self.config.get("auto_trading", {})
        startup_message += f"⚙️ *Cấu hình*:\n"
        startup_message += f"• Giao dịch tự động: {'✅ BẬT' if auto_trading.get('enabled', False) else '❌ TẮT'}\n"
        if auto_trading.get("enabled", False):
            startup_message += f"• Độ tin cậy tối thiểu: {auto_trading.get('min_confidence', 85.0)}%\n"
            startup_message += f"• Yêu cầu xác nhận: {'✅ CÓ' if auto_trading.get('require_confirmation', True) else '❌ KHÔNG'}\n"
        
        startup_message += f"• Rủi ro mỗi lệnh: {self.config.get('default_risk_percent', 2.0)}%\n"
        startup_message += f"• Rủi ro tối đa mỗi ngày: {self.config.get('max_risk_per_day', 10.0)}%\n\n"
        
        # Thêm thông tin về thời điểm vào lệnh tối ưu tiếp theo
        is_optimal, window = self.strategy.is_optimal_time()
        if is_optimal:
            startup_message += f"⚠️ *Hiện tại là thời gian tối ưu để vào lệnh*: {window['name']}\n"
            startup_message += f"• Hướng khuyến nghị: {window.get('direction', 'both').upper()}\n"
        else:
            # Tìm thời gian tối ưu tiếp theo
            optimal_times = self.strategy.get_all_optimal_times()
            now = datetime.now()
            next_optimal = None
            earliest_diff = timedelta(days=1)
            
            for time_info in optimal_times:
                hour, minute = map(int, time_info["start_time"].split(":"))
                start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if start_time < now:
                    start_time = start_time + timedelta(days=1)
                
                diff = start_time - now
                if diff < earliest_diff:
                    earliest_diff = diff
                    next_optimal = time_info
            
            if next_optimal:
                hours, remainder = divmod(earliest_diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                startup_message += f"⏱ *Thời gian tối ưu tiếp theo*: {next_optimal['name']} ({next_optimal['start_time']})\n"
                startup_message += f"• Còn {hours} giờ {minutes} phút nữa\n"
        
        self.telegram.send_message(startup_message, parse_mode="Markdown")
        
        # Chạy scheduler trong thread riêng
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def _run_scheduler(self) -> None:
        """
        Chạy scheduler trong thread
        """
        while self.is_running:
            schedule.run_pending()
            time.sleep(10)
    
    def stop(self) -> None:
        """
        Dừng hệ thống giao dịch
        """
        if not self.is_running:
            logger.warning("Hệ thống chưa được khởi động")
            return
        
        self.is_running = False
        
        # Gửi thông báo dừng
        stop_message = f"🛑 *HỆ THỐNG GIAO DỊCH THEO THỜI GIAN TỐI ƯU ĐÃ DỪNG* 🛑\n\n"
        stop_message += f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        self.telegram.send_message(stop_message, parse_mode="Markdown")
        
        logger.info("Đã dừng hệ thống giao dịch dựa trên thời gian tối ưu")

def setup_environment():
    """
    Thiết lập môi trường làm việc
    """
    # Tạo các thư mục cần thiết
    os.makedirs("configs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Hệ thống giao dịch dựa trên thời gian tối ưu')
    parser.add_argument('--config', type=str, default='configs/time_based_trading_config.json', help='Đường dẫn đến file cấu hình')
    parser.add_argument('--strategy-config', type=str, default='configs/time_optimized_strategy_config.json', help='Đường dẫn đến file cấu hình chiến lược')
    parser.add_argument('--telegram-config', type=str, default='telegram_config.json', help='Đường dẫn đến file cấu hình Telegram')
    parser.add_argument('--api-key', type=str, help='API key Binance')
    parser.add_argument('--api-secret', type=str, help='API secret Binance')
    parser.add_argument('--timezone', type=int, default=7, help='Chênh lệch múi giờ so với UTC')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet Binance')
    parser.add_argument('--reset', action='store_true', help='Reset cấu hình về mặc định')
    parser.add_argument('--auto-trading', action='store_true', help='Bật giao dịch tự động')
    args = parser.parse_args()
    
    # Thiết lập môi trường
    setup_environment()
    
    # Nếu yêu cầu reset cấu hình
    if args.reset and os.path.exists(args.config):
        os.remove(args.config)
        logger.info(f"Đã xóa file cấu hình {args.config}")
    
    # Khởi tạo hệ thống
    system = TimeBasedTradingSystem(
        config_path=args.config,
        strategy_config_path=args.strategy_config,
        telegram_config_path=args.telegram_config,
        api_key=args.api_key,
        api_secret=args.api_secret,
        use_testnet=args.testnet
    )
    
    # Cập nhật timezone nếu có
    if args.timezone != system.timezone_offset:
        system.timezone_offset = args.timezone
        system.config["timezone_offset"] = args.timezone
        system._save_config()
    
    # Cập nhật giao dịch tự động nếu có
    if args.auto_trading:
        system.config["auto_trading"]["enabled"] = True
        system._save_config()
    
    # Hiển thị thông tin
    print("\n===== HỆ THỐNG GIAO DỊCH THEO THỜI GIAN TỐI ƯU =====")
    print(f"Thời gian hiện tại: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Múi giờ: UTC+{system.timezone_offset}")
    print(f"Testnet: {'✓' if args.testnet else '✗'}")
    print(f"Auto-trading: {'✓' if system.config.get('auto_trading', {}).get('enabled', False) else '✗'}")
    print(f"Coin theo dõi: {', '.join(system.active_symbols)}")
    
    # Kiểm tra xem thời gian hiện tại có phải thời gian tối ưu không
    is_optimal, window = system.strategy.is_optimal_time()
    if is_optimal:
        print(f"\nHiện tại là thời gian tối ưu để vào lệnh: {window['name']}")
        print(f"Hướng khuyến nghị: {window.get('direction', 'both').upper()}")
    else:
        print("\nHiện tại không phải thời gian tối ưu để vào lệnh")
    
    # Hiển thị hướng dẫn
    print("\nHướng dẫn:")
    print("- Nhấn Ctrl+C để dừng hệ thống")
    
    # Bắt đầu hệ thống
    try:
        system.start()
        
        # Chờ kết thúc
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐang dừng hệ thống...")
        system.stop()
        print("Đã dừng hệ thống!")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {e}", exc_info=True)
        system.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()