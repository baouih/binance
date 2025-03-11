#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module bot giao dịch chính
"""

import os
import logging
import json
import time
import traceback
from datetime import datetime, timedelta

# Cấu hình logging
logger = logging.getLogger("trading_bot")

class TradingBot:
    """
    Bot giao dịch tự động với các chiến lược quản lý rủi ro
    """
    
    def __init__(self, market_analyzer, signal_generator, position_manager, risk_manager, telegram_notifier=None, config=None):
        """
        Khởi tạo với các thành phần cần thiết
        
        :param market_analyzer: Đối tượng MarketAnalyzer
        :param signal_generator: Đối tượng SignalGenerator
        :param position_manager: Đối tượng PositionManager
        :param risk_manager: Đối tượng RiskManager
        :param telegram_notifier: Đối tượng TelegramNotifier (có thể None)
        :param config: Dict cấu hình
        """
        self.market_analyzer = market_analyzer
        self.signal_generator = signal_generator
        self.position_manager = position_manager
        self.risk_manager = risk_manager
        self.telegram_notifier = telegram_notifier
        self.config = config or {}
        
        self.start_time = datetime.now()
        self.trades_today = 0
        self.last_check_time = {}
        self.last_signal_check = datetime.now() - timedelta(minutes=30)  # Để lần đầu chạy ngay lập tức
    
    def run_cycle(self):
        """
        Chạy một chu kỳ của bot giao dịch
        
        :return: Dict kết quả của chu kỳ
        """
        cycle_result = {
            "actions": [],
            "errors": [],
            "timestamp": datetime.now()
        }
        
        try:
            # Kiểm tra các vị thế đang mở
            self.check_open_positions(cycle_result)
            
            # Kiểm tra tín hiệu mới theo thời gian
            time_since_last_check = datetime.now() - self.last_signal_check
            if time_since_last_check.total_seconds() > 1800:  # 30 phút
                self.check_for_new_signals(cycle_result)
                self.last_signal_check = datetime.now()
            
            # Gửi thông báo cập nhật định kỳ
            self.send_periodic_updates(cycle_result)
            
            return cycle_result
            
        except Exception as e:
            error_msg = f"Lỗi trong chu kỳ của bot: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            cycle_result["errors"].append(error_msg)
            return cycle_result
    
    def check_open_positions(self, cycle_result):
        """
        Kiểm tra các vị thế đang mở và cập nhật SL/TP nếu cần
        
        :param cycle_result: Dict kết quả chu kỳ để cập nhật
        """
        try:
            positions = self.position_manager.get_all_positions()
            
            for position in positions:
                try:
                    symbol = position["symbol"]
                    side = position["side"]
                    
                    # Kiểm tra trailing stop nếu lợi nhuận đủ lớn
                    profit_percent = position.get("profit_percent", 0)
                    
                    # Nếu lợi nhuận > 2%, cập nhật trailing stop
                    if profit_percent > 2:
                        self.update_trailing_stop(position, cycle_result)
                        
                except Exception as e:
                    error_msg = f"Lỗi khi kiểm tra vị thế {position.get('symbol', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    cycle_result["errors"].append(error_msg)
            
            # Cập nhật kết quả
            cycle_result["actions"].append(f"Đã kiểm tra {len(positions)} vị thế")
            
        except Exception as e:
            error_msg = f"Lỗi khi kiểm tra các vị thế: {str(e)}"
            logger.error(error_msg)
            cycle_result["errors"].append(error_msg)
    
    def update_trailing_stop(self, position, cycle_result):
        """
        Cập nhật trailing stop cho vị thế có lợi nhuận
        
        :param position: Dict thông tin vị thế
        :param cycle_result: Dict kết quả chu kỳ để cập nhật
        """
        try:
            symbol = position["symbol"]
            side = position["side"]
            entry_price = position["entry_price"]
            current_price = position["mark_price"]
            current_sl = position.get("stop_loss")
            profit_percent = position.get("profit_percent", 0)
            
            # Nếu không có SL hiện tại, không cập nhật
            if current_sl is None:
                return
            
            new_sl = None
            
            # Tính toán trailing stop mới dựa trên % lợi nhuận
            if side == "LONG":
                # Đối với LONG, trailing stop sẽ tăng theo giá
                if profit_percent > 3:  # > 3% lợi nhuận
                    # Di chuyển SL lên breakeven + 0.5%
                    new_sl = max(current_sl, entry_price * 1.005)
                    
                if profit_percent > 5:  # > 5% lợi nhuận
                    # Di chuyển SL lên giá vào + 1% lợi nhuận
                    new_sl = max(current_sl, entry_price * 1.01)
                    
                if profit_percent > 10:  # > 10% lợi nhuận
                    # Đảm bảo SL gần giá hiện tại hơn, ít nhất là giá hiện tại - 3%
                    new_sl = max(current_sl, current_price * 0.97)
            else:  # SHORT
                # Đối với SHORT, trailing stop sẽ giảm theo giá
                if profit_percent > 3:  # > 3% lợi nhuận
                    # Di chuyển SL xuống breakeven - 0.5%
                    new_sl = min(current_sl, entry_price * 0.995)
                    
                if profit_percent > 5:  # > 5% lợi nhuận
                    # Di chuyển SL xuống giá vào - 1% lợi nhuận
                    new_sl = min(current_sl, entry_price * 0.99)
                    
                if profit_percent > 10:  # > 10% lợi nhuận
                    # Đảm bảo SL gần giá hiện tại hơn, ít nhất là giá hiện tại + 3%
                    new_sl = min(current_sl, current_price * 1.03)
            
            # Nếu có SL mới, cập nhật
            if new_sl is not None and abs(new_sl - current_sl) / current_sl > 0.005:  # Chỉ cập nhật nếu thay đổi > 0.5%
                result = self.position_manager.update_sl_tp(
                    symbol=symbol,
                    side=side,
                    stop_loss=new_sl
                )
                
                if result["status"] == "success":
                    action_msg = f"Đã cập nhật trailing stop cho {symbol} {side}: {current_sl:.2f} -> {new_sl:.2f}"
                    logger.info(action_msg)
                    cycle_result["actions"].append(action_msg)
                    
                    # Gửi thông báo Telegram nếu có
                    if self.telegram_notifier:
                        self.telegram_notifier.send_sltp_update(
                            symbol=symbol,
                            side=side,
                            old_sl=current_sl,
                            new_sl=new_sl,
                            reason="Trailing Stop"
                        )
                else:
                    error_msg = f"Lỗi khi cập nhật trailing stop cho {symbol} {side}: {result.get('message', 'Unknown error')}"
                    logger.error(error_msg)
                    cycle_result["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Lỗi khi cập nhật trailing stop cho {position.get('symbol', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            cycle_result["errors"].append(error_msg)
    
    def check_for_new_signals(self, cycle_result):
        """
        Kiểm tra các tín hiệu giao dịch mới
        
        :param cycle_result: Dict kết quả chu kỳ để cập nhật
        """
        try:
            # Kiểm tra xem có thể mở vị thế mới không
            risk_limits = self.risk_manager.check_risk_limits()
            
            if risk_limits["positions_limit_reached"]:
                logger.info(f"Đã đạt giới hạn vị thế: {risk_limits['positions_count']}/{risk_limits['max_positions']}")
                return
            
            # Lấy tất cả các tín hiệu giao dịch mới
            signals = self.signal_generator.get_current_signals()
            
            if not signals:
                logger.info("Không tìm thấy tín hiệu giao dịch mới")
                return
            
            # Sắp xếp tín hiệu theo độ tin cậy
            signals.sort(key=lambda x: x["confidence"], reverse=True)
            
            positions = self.position_manager.get_all_positions()
            position_symbols = [p["symbol"] for p in positions]
            
            # Tìm tín hiệu tốt nhất chưa mở vị thế
            for signal in signals:
                symbol = signal["symbol"]
                side = signal["side"]
                
                # Kiểm tra xem đã có vị thế cho cặp tiền này chưa
                if symbol in position_symbols:
                    continue
                
                # Kiểm tra tính hợp lệ của tín hiệu
                is_valid, reason = self.signal_generator.validate_signal(signal)
                if not is_valid:
                    logger.warning(f"Tín hiệu không hợp lệ cho {symbol} {side}: {reason}")
                    continue
                
                # Kiểm tra giới hạn rủi ro
                is_valid, reason = self.risk_manager.validate_new_position(symbol, side, 0)
                if not is_valid:
                    logger.warning(f"Không thể mở vị thế mới cho {symbol} {side}: {reason}")
                    continue
                
                # Tính kích thước vị thế
                account_info = self.market_analyzer.get_account_info()
                if account_info["status"] != "success":
                    logger.error(f"Không thể lấy thông tin tài khoản: {account_info.get('message', 'Unknown error')}")
                    continue
                
                account_balance = account_info["account"]["balance"]
                position_size = self.risk_manager.calculate_position_size(account_balance, symbol)
                
                # Lấy giá vào, SL, TP từ tín hiệu
                entry_price = signal["entry_price"]
                stop_loss = signal["stop_loss"]
                take_profit = signal["take_profit"]
                
                # Mở vị thế
                result = self.position_manager.open_position(
                    symbol=symbol,
                    side=side,
                    amount=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if result["status"] == "success":
                    action_msg = f"Đã mở vị thế {side} trên {symbol} tại giá {entry_price:.2f} với SL={stop_loss:.2f}, TP={take_profit:.2f}"
                    logger.info(action_msg)
                    cycle_result["actions"].append(action_msg)
                    self.trades_today += 1
                    
                    # Gửi thông báo Telegram nếu có
                    if self.telegram_notifier:
                        # Tính R:R
                        if side == "LONG":
                            risk = entry_price - stop_loss
                            reward = take_profit - entry_price
                        else:  # SHORT
                            risk = stop_loss - entry_price
                            reward = entry_price - take_profit
                        
                        risk_reward = reward / risk if risk > 0 else 0
                        
                        self.telegram_notifier.send_trade_signal(
                            symbol=symbol,
                            side=side,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timeframe=signal["timeframe"],
                            strategy=signal["strategy"],
                            confidence=signal["confidence"]
                        )
                    
                    break  # Chỉ mở một vị thế mỗi lần
                else:
                    error_msg = f"Lỗi khi mở vị thế {side} trên {symbol}: {result.get('message', 'Unknown error')}"
                    logger.error(error_msg)
                    cycle_result["errors"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Lỗi khi kiểm tra tín hiệu mới: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            cycle_result["errors"].append(error_msg)
    
    def send_periodic_updates(self, cycle_result):
        """
        Gửi thông báo cập nhật định kỳ
        
        :param cycle_result: Dict kết quả chu kỳ để cập nhật
        """
        if not self.telegram_notifier:
            return
        
        try:
            # Kiểm tra thời gian từ lần cập nhật cuối
            now = datetime.now()
            
            # Kiểm tra thời gian hoạt động
            uptime_hours = (now - self.start_time).total_seconds() / 3600
            
            # Gửi báo cáo hệ thống mỗi 12 giờ
            last_system_report = self.last_check_time.get("system_report", self.start_time)
            if (now - last_system_report).total_seconds() > 12 * 3600:  # 12 giờ
                # Lấy thông tin tài khoản
                account_info = self.market_analyzer.get_account_info()
                if account_info["status"] == "success":
                    # Lấy thông tin cần thiết
                    uptime = (now - self.start_time).total_seconds()
                    account_balance = account_info["account"]["balance"]
                    positions = self.position_manager.get_all_positions()
                    
                    # Gửi thông báo
                    self.telegram_notifier.send_system_status(
                        uptime=uptime,
                        account_balance=account_balance,
                        open_positions=len(positions),
                        daily_trades=self.trades_today,
                        daily_pnl=account_info["account"].get("unrealized_pnl", 0)
                    )
                    
                    # Cập nhật thời gian kiểm tra
                    self.last_check_time["system_report"] = now
                    
                    action_msg = "Đã gửi báo cáo trạng thái hệ thống qua Telegram"
                    logger.info(action_msg)
                    cycle_result["actions"].append(action_msg)
            
            # Gửi cập nhật vị thế mỗi 6 giờ
            last_position_update = self.last_check_time.get("position_update", self.start_time)
            if (now - last_position_update).total_seconds() > 6 * 3600:  # 6 giờ
                # Lấy thông tin vị thế
                positions = self.position_manager.get_all_positions()
                
                if positions:
                    # Lấy thông tin tài khoản
                    account_info = self.market_analyzer.get_account_info()
                    if account_info["status"] == "success":
                        # Gửi thông báo
                        self.telegram_notifier.send_position_update(
                            positions=positions,
                            account_balance=account_info["account"]["balance"],
                            unrealized_pnl=account_info["account"].get("unrealized_pnl", 0)
                        )
                        
                        # Cập nhật thời gian kiểm tra
                        self.last_check_time["position_update"] = now
                        
                        action_msg = "Đã gửi cập nhật vị thế qua Telegram"
                        logger.info(action_msg)
                        cycle_result["actions"].append(action_msg)
            
            # Reset số lượng giao dịch khi sang ngày mới
            if now.date() != self.start_time.date() and now.hour == 0 and now.minute < 10:
                self.trades_today = 0
                
        except Exception as e:
            error_msg = f"Lỗi khi gửi cập nhật định kỳ: {str(e)}"
            logger.error(error_msg)
            cycle_result["errors"].append(error_msg)

# Hàm để thử nghiệm module
def test_trading_bot():
    """Hàm kiểm tra chức năng của TradingBot"""
    # Cấu hình logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        from market_analyzer import MarketAnalyzer
        from signal_generator import SignalGenerator
        from position_manager import PositionManager
        from risk_manager import RiskManager
        from advanced_telegram_notifier import TelegramNotifier
        
        # Tải cấu hình
        config_file = "account_config.json"
        config = {}
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)
        
        # Khởi tạo các thành phần
        market_analyzer = MarketAnalyzer(testnet=True)
        signal_generator = SignalGenerator(market_analyzer, config)
        
        # Tải cấu hình rủi ro
        risk_level = config.get("risk_level", 10)
        risk_config_file = f"risk_configs/risk_level_{risk_level}.json"
        risk_config = {}
        if os.path.exists(risk_config_file):
            with open(risk_config_file, "r") as f:
                risk_config = json.load(f)
        
        position_manager = PositionManager(testnet=True, risk_config=risk_config)
        risk_manager = RiskManager(position_manager, risk_config)
        
        # Khởi tạo Telegram notifier nếu có API key
        telegram_notifier = None
        if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            telegram_notifier = TelegramNotifier()
        
        # Khởi tạo bot
        bot = TradingBot(
            market_analyzer=market_analyzer,
            signal_generator=signal_generator,
            position_manager=position_manager,
            risk_manager=risk_manager,
            telegram_notifier=telegram_notifier,
            config=config
        )
        
        # Chạy một chu kỳ của bot
        print("Đang chạy một chu kỳ của bot...")
        cycle_result = bot.run_cycle()
        
        print("\nKết quả chu kỳ:")
        print(f"Thời gian: {cycle_result['timestamp']}")
        
        print("\nHành động:")
        for action in cycle_result["actions"]:
            print(f"  - {action}")
        
        print("\nLỗi:")
        for error in cycle_result["errors"]:
            print(f"  - {error}")
        
    except Exception as e:
        print(f"Lỗi khi test TradingBot: {str(e)}")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_trading_bot()