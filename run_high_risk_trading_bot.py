#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy bot giao dịch tích hợp với cấu hình rủi ro cao
Chạy tất cả các chiến lược trên tất cả các coin được cấu hình

Tác giả: AdvancedTradingBot
Ngày: 9/3/2025
"""

import os
import sys
import time
import json
import logging
import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor

# Thêm thư mục hiện tại vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import các module cần thiết
from binance_api import BinanceAPI
from strategy_integration import StrategyIntegration
from telegram_notifier import TelegramNotifier
from risk_manager import RiskManager
from adaptive_strategy_selector import AdaptiveStrategySelector
from adaptive_exit_strategy import AdaptiveExitStrategy
from time_optimized_strategy import TimeOptimizedStrategy
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from market_regime_classifier import MarketRegimeClassifier
from trade_scheduler import TradeScheduler

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('high_risk_trading.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('high_risk_bot')

class HighRiskTradingBot:
    """Bot giao dịch sử dụng cấu hình rủi ro cao với tất cả chiến lược tích hợp"""
    
    def __init__(self):
        """Khởi tạo bot và tải các cấu hình cần thiết"""
        self.logger = logging.getLogger('high_risk_bot')
        self.logger.info("Khởi tạo HighRiskTradingBot")
        
        # Tải cấu hình tài khoản
        with open('account_config.json', 'r') as f:
            self.account_config = json.load(f)
        
        # Tải cấu hình chiến lược thị trường
        with open('configs/strategy_market_config.json', 'r') as f:
            self.strategy_config = json.load(f)
        
        # Khởi tạo API Binance
        self.api = BinanceAPI(account_config_path='account_config.json')
        
        # Khởi tạo Telegram Notifier
        self.notifier = TelegramNotifier()
        
        # Khởi tạo Risk Manager
        self.risk_manager = RiskManager()
        
        # Khởi tạo Strategy Selector
        self.strategy_selector = AdaptiveStrategySelector()
        
        # Khởi tạo Exit Strategy
        self.exit_strategy = AdaptiveExitStrategy()
        
        # Khởi tạo Time Strategy
        self.time_strategy = TimeOptimizedStrategy()
        
        # Khởi tạo Multi Timeframe Analyzer
        self.multi_tf_analyzer = MultiTimeframeAnalyzer()
        
        # Khởi tạo Market Regime Classifier
        self.regime_classifier = MarketRegimeClassifier()
        
        # Khởi tạo StrategyIntegration (bot chính)
        self.bot = StrategyIntegration(
            risk_manager=self.risk_manager,
            strategy_selector=self.strategy_selector,
            exit_strategy=self.exit_strategy,
            time_strategy=self.time_strategy,
            multi_tf_analyzer=self.multi_tf_analyzer,
            regime_classifier=self.regime_classifier
        )
        
        # Khởi tạo Trade Scheduler
        self.scheduler = TradeScheduler(trading_bot=self.bot)
        
        # Danh sách coin để giao dịch
        self.symbols = self.account_config.get('symbols', [])
        
        # Thông số rủi ro
        self.risk_per_trade = self.account_config.get('risk_per_trade', 10.0)
        self.leverage = self.account_config.get('leverage', 20)
        self.max_positions = self.account_config.get('max_open_positions', 10)
        
        # Thiết lập các biến cơ bản
        self.active_positions = {}
        self.last_update_time = datetime.datetime.now()
        self.account_balance = 0
        
        self.logger.info(f"Đã khởi tạo bot với {len(self.symbols)} cặp tiền, rủi ro: {self.risk_per_trade}%, đòn bẩy: {self.leverage}x")
        
    def set_leverage_for_all_symbols(self):
        """Thiết lập đòn bẩy cho tất cả các cặp tiền"""
        self.logger.info(f"Thiết lập đòn bẩy {self.leverage}x cho tất cả các cặp tiền")
        
        for symbol in self.symbols:
            try:
                result = self.api.set_leverage(symbol=symbol, leverage=self.leverage)
                self.logger.info(f"Đã thiết lập đòn bẩy cho {symbol}: {result}")
                time.sleep(0.5)  # Tránh rate limit
            except Exception as e:
                self.logger.error(f"Lỗi khi thiết lập đòn bẩy cho {symbol}: {str(e)}")
    
    def update_account_balance(self):
        """Cập nhật số dư tài khoản"""
        try:
            self.account_balance = self.api.get_account_balance()
            self.logger.info(f"Số dư tài khoản: {self.account_balance} USDT")
            return self.account_balance
        except Exception as e:
            self.logger.error(f"Lỗi khi cập nhật số dư tài khoản: {str(e)}")
            return 0
    
    def get_active_positions(self):
        """Lấy danh sách vị thế đang mở"""
        try:
            positions = self.api.get_open_positions()
            self.active_positions = {pos['symbol']: pos for pos in positions if float(pos['positionAmt']) != 0}
            
            position_info = []
            for symbol, pos in self.active_positions.items():
                side = "LONG" if float(pos['positionAmt']) > 0 else "SHORT"
                amount = abs(float(pos['positionAmt']))
                entry_price = float(pos['entryPrice'])
                unrealized_pnl = float(pos['unrealizedProfit'])
                
                position_info.append(f"{symbol} {side}: {amount} @ {entry_price} (PnL: {unrealized_pnl:.2f} USDT)")
            
            if position_info:
                self.logger.info(f"Vị thế đang mở ({len(position_info)}): {', '.join(position_info)}")
            else:
                self.logger.info("Không có vị thế nào đang mở")
                
            return self.active_positions
        except Exception as e:
            self.logger.error(f"Lỗi khi lấy vị thế đang mở: {str(e)}")
            return {}
    
    def analyze_all_symbols(self):
        """Phân tích tất cả các cặp tiền và tìm cơ hội giao dịch"""
        self.logger.info(f"Phân tích {len(self.symbols)} cặp tiền...")
        
        opportunities = []
        
        for symbol in self.symbols:
            try:
                # Kiểm tra nếu đã có vị thế cho symbol này
                if symbol in self.active_positions:
                    continue
                    
                # Lấy chế độ thị trường
                market_regime = self.regime_classifier.classify_regime(symbol)
                
                # Lựa chọn chiến lược phù hợp với chế độ thị trường
                strategies = self.strategy_selector.select_strategy(symbol, market_regime)
                
                # Kiểm tra thời gian tối ưu
                time_optimized = self.time_strategy.check_optimal_entry_time(symbol)
                
                # Phân tích đa khung thời gian
                multi_tf_analysis = self.multi_tf_analyzer.analyze(symbol)
                
                # Tính toán cơ hội giao dịch dựa trên các phân tích trên
                opportunity = self.bot.evaluate_trading_opportunity(
                    symbol=symbol,
                    market_regime=market_regime,
                    strategies=strategies,
                    time_optimized=time_optimized,
                    multi_tf_analysis=multi_tf_analysis
                )
                
                if opportunity and opportunity.get('score', 0) > 70:
                    opportunities.append(opportunity)
                    self.logger.info(f"Tìm thấy cơ hội giao dịch: {symbol}, Điểm: {opportunity.get('score')}, Hướng: {opportunity.get('direction')}")
            
            except Exception as e:
                self.logger.error(f"Lỗi khi phân tích {symbol}: {str(e)}")
                traceback.print_exc()
        
        # Sắp xếp cơ hội theo điểm số giảm dần
        opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return opportunities
    
    def execute_trades(self, opportunities):
        """Thực hiện giao dịch dựa trên cơ hội tìm thấy"""
        # Kiểm tra số lượng vị thế hiện tại
        current_positions = len(self.active_positions)
        max_new_positions = max(0, self.max_positions - current_positions)
        
        if max_new_positions <= 0:
            self.logger.info(f"Đã đạt số lượng vị thế tối đa ({current_positions}/{self.max_positions}), không mở thêm vị thế mới")
            return
        
        # Thực hiện giao dịch cho các cơ hội tốt nhất
        executed_count = 0
        for opportunity in opportunities[:max_new_positions]:
            symbol = opportunity.get('symbol')
            direction = opportunity.get('direction')
            score = opportunity.get('score')
            
            try:
                # Tính kích thước vị thế dựa trên quản lý rủi ro
                position_size = self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    risk_percentage=self.risk_per_trade,
                    account_balance=self.account_balance,
                    leverage=self.leverage
                )
                
                # Tính toán stop loss và take profit
                entry_price = float(self.api.get_symbol_price(symbol))
                stop_loss, take_profit = self.exit_strategy.calculate_exit_points(
                    symbol=symbol,
                    entry_price=entry_price,
                    direction=direction
                )
                
                # Thực hiện lệnh
                order_result = self.bot.execute_trade(
                    symbol=symbol,
                    direction=direction,
                    position_size=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if order_result:
                    self.logger.info(f"Đã mở vị thế {direction} cho {symbol}: Size={position_size}, Entry={entry_price}, SL={stop_loss}, TP={take_profit}")
                    
                    # Gửi thông báo
                    self.notifier.send_trade_notification(
                        symbol=symbol,
                        side=direction,
                        entry_price=entry_price,
                        position_size=position_size,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        score=score,
                        strategy=opportunity.get('strategy', 'Combined')
                    )
                    
                    executed_count += 1
                    time.sleep(1)  # Tránh rate limit
            
            except Exception as e:
                self.logger.error(f"Lỗi khi thực hiện giao dịch {symbol}: {str(e)}")
        
        if executed_count > 0:
            self.logger.info(f"Đã thực hiện {executed_count} giao dịch mới")
        else:
            self.logger.info("Không thực hiện giao dịch nào mới")
    
    def monitor_active_positions(self):
        """Giám sát và quản lý các vị thế đang hoạt động"""
        if not self.active_positions:
            return
            
        self.logger.info(f"Đang giám sát {len(self.active_positions)} vị thế hoạt động")
        
        for symbol, position in self.active_positions.items():
            try:
                # Kiểm tra nếu nên đóng vị thế
                should_close = self.exit_strategy.should_close_position(
                    symbol=symbol, 
                    position=position
                )
                
                if should_close:
                    reason = should_close.get('reason', 'Unknown')
                    self.logger.info(f"Đóng vị thế {symbol} do: {reason}")
                    
                    close_result = self.bot.close_position(symbol=symbol)
                    
                    if close_result:
                        self.logger.info(f"Đã đóng vị thế {symbol} thành công: {close_result}")
                        self.notifier.send_position_closed_notification(
                            symbol=symbol,
                            reason=reason,
                            profit_loss=should_close.get('profit_loss', 0)
                        )
                    else:
                        self.logger.error(f"Không thể đóng vị thế {symbol}")
                
                # Kiểm tra nếu nên di chuyển stop loss
                elif self.account_config.get('enable_trailing_stop', True):
                    new_stop = self.exit_strategy.calculate_trailing_stop(
                        symbol=symbol,
                        position=position
                    )
                    
                    if new_stop and new_stop.get('update', False):
                        self.logger.info(f"Cập nhật trailing stop cho {symbol}: {new_stop.get('new_stop_price')}")
                        update_result = self.bot.update_stop_loss(
                            symbol=symbol,
                            new_stop_price=new_stop.get('new_stop_price')
                        )
                        
                        if update_result:
                            self.logger.info(f"Đã cập nhật stop loss cho {symbol} thành công")
                
            except Exception as e:
                self.logger.error(f"Lỗi khi giám sát vị thế {symbol}: {str(e)}")
    
    def run(self):
        """Chạy bot giao dịch rủi ro cao"""
        self.logger.info("Bắt đầu chạy HighRiskTradingBot")
        
        try:
            # Cập nhật số dư tài khoản
            self.update_account_balance()
            
            # Thiết lập đòn bẩy cho tất cả các cặp tiền
            self.set_leverage_for_all_symbols()
            
            # Gửi thông báo khởi động
            self.notifier.send_message(
                f"🚀 Bot Giao Dịch Rủi Ro Cao đã khởi động!\n"
                f"💰 Số dư: {self.account_balance} USDT\n"
                f"⚙️ Cấu hình: {self.risk_per_trade}% rủi ro/giao dịch, {self.leverage}x đòn bẩy, tối đa {self.max_positions} vị thế\n"
                f"🪙 Coin: {', '.join(self.symbols[:5])} và {len(self.symbols) - 5} cặp khác"
            )
            
            # Vòng lặp chính của bot
            while True:
                try:
                    # Lấy các vị thế đang mở
                    self.get_active_positions()
                    
                    # Giám sát vị thế đang mở
                    self.monitor_active_positions()
                    
                    # Tìm kiếm cơ hội giao dịch mới
                    opportunities = self.analyze_all_symbols()
                    
                    # Thực hiện giao dịch nếu có cơ hội
                    if opportunities:
                        self.execute_trades(opportunities)
                    
                    # Cập nhật lại số dư mỗi giờ
                    current_time = datetime.datetime.now()
                    if (current_time - self.last_update_time).seconds >= 3600:
                        self.update_account_balance()
                        self.last_update_time = current_time
                    
                    # Chờ 5 phút trước khi quét lại
                    self.logger.info(f"Đã hoàn thành chu kỳ phân tích, nghỉ 5 phút")
                    time.sleep(300)
                
                except Exception as e:
                    self.logger.error(f"Lỗi trong chu kỳ giao dịch: {str(e)}")
                    traceback.print_exc()
                    time.sleep(60)  # Nghỉ 1 phút nếu có lỗi
        
        except KeyboardInterrupt:
            self.logger.info("Bot đã dừng bởi người dùng")
            self.notifier.send_message("🛑 Bot Giao Dịch Rủi Ro Cao đã dừng bởi người dùng")
        
        except Exception as e:
            self.logger.error(f"Lỗi nghiêm trọng, bot đã dừng: {str(e)}")
            self.notifier.send_message(f"⚠️ Bot Giao Dịch Rủi Ro Cao đã dừng do lỗi: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    bot = HighRiskTradingBot()
    bot.run()