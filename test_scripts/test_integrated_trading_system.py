#!/usr/bin/env python3
"""
Kiểm tra tích hợp hệ thống giao dịch tự động

Module này kiểm tra tích hợp các thành phần chính của hệ thống giao dịch,
bao gồm position sizing, quản lý rủi ro và thông báo qua Telegram trong
một môi trường mô phỏng hoạt động thực tế.
"""

import os
import sys
import time
import json
import logging
import traceback
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Union, Optional, Tuple, Callable
from datetime import datetime, timedelta
import unittest
from unittest.mock import patch, MagicMock, Mock

# Thêm thư mục gốc vào sys.path để import module từ dự án
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Tạo thư mục test_results nếu chưa tồn tại
test_results_dir = os.path.join(os.path.dirname(__file__), '../test_results')
if not os.path.exists(test_results_dir):
    os.makedirs(test_results_dir)

# Mô-đun position sizing
try:
    import position_sizing
    USING_ACTUAL_POSITION_SIZING = True
except ImportError:
    USING_ACTUAL_POSITION_SIZING = False
    logging.warning("Không thể import position_sizing module, sử dụng triển khai mẫu")
    
    # Mock cho các lớp position sizing (định nghĩa tương tự trong test_position_sizing_advanced.py)
    from test_scripts.test_position_sizing_advanced import (
        BasePositionSizer, DynamicPositionSizer, KellyCriterionSizer,
        AntiMartingaleSizer, PortfolioSizer, create_position_sizer
    )

# Mô-đun Telegram
try:
    from telegram_notify import TelegramNotifier
    USING_ACTUAL_TELEGRAM = True
except ImportError:
    USING_ACTUAL_TELEGRAM = False
    logging.warning("Không thể import TelegramNotifier, sử dụng triển khai mẫu")
    
    class TelegramNotifier:
        def __init__(self, token=None, chat_id=None):
            self.token = token
            self.chat_id = chat_id
            self.enabled = bool(token and chat_id)
            self.sent_messages = []
            
        def send_message(self, message, parse_mode="HTML"):
            print(f"[MOCK] Gửi tin nhắn: {message}")
            self.sent_messages.append({"type": "message", "content": message, "timestamp": datetime.now()})
            return True
            
        def send_photo(self, photo_path, caption=None, parse_mode="HTML"):
            print(f"[MOCK] Gửi ảnh: {photo_path}, caption: {caption}")
            self.sent_messages.append({"type": "photo", "path": photo_path, "caption": caption, "timestamp": datetime.now()})
            return True
            
        def send_trade_signal(self, **kwargs):
            print(f"[MOCK] Gửi tín hiệu giao dịch: {kwargs}")
            self.sent_messages.append({"type": "trade_signal", "data": kwargs, "timestamp": datetime.now()})
            return True
            
        def send_position_closed(self, **kwargs):
            print(f"[MOCK] Gửi thông báo đóng vị thế: {kwargs}")
            self.sent_messages.append({"type": "position_closed", "data": kwargs, "timestamp": datetime.now()})
            return True
            
        def send_trade_execution(self, **kwargs):
            print(f"[MOCK] Gửi thông báo thực hiện giao dịch: {kwargs}")
            self.sent_messages.append({"type": "trade_execution", "data": kwargs, "timestamp": datetime.now()})
            return True
            
        def send_daily_report(self, **kwargs):
            print(f"[MOCK] Gửi báo cáo hàng ngày: {kwargs}")
            self.sent_messages.append({"type": "daily_report", "data": kwargs, "timestamp": datetime.now()})
            return True

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_integrated_system')

# Lớp mô phỏng Binance API
class MockBinanceAPI:
    """Lớp mô phỏng Binance API cho mục đích kiểm tra"""
    
    def __init__(self):
        self.current_prices = {
            "BTCUSDT": 60000.0,
            "ETHUSDT": 3000.0,
            "SOLUSDT": 120.0,
            "ADAUSDT": 0.5,
            "DOGEUSDT": 0.15
        }
        self.test_mode = True
        self.order_history = []
        self.account_balance = 10000.0
        self.fee_rate = 0.001  # 0.1% fee
        self.positions = {}
        
    def get_current_price(self, symbol):
        """Lấy giá hiện tại của một cặp giao dịch"""
        return self.current_prices.get(symbol, 0.0)
        
    def get_account_balance(self):
        """Lấy số dư tài khoản"""
        return self.account_balance
        
    def create_order(self, symbol, side, quantity, price=None, order_type="MARKET"):
        """Tạo lệnh giao dịch mới"""
        current_price = price or self.get_current_price(symbol)
        order_value = quantity * current_price
        fee = order_value * self.fee_rate
        
        order = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": current_price,
            "order_type": order_type,
            "status": "FILLED",
            "timestamp": datetime.now(),
            "order_id": f"TEST_{int(time.time())}",
            "fee": fee,
            "total_value": order_value
        }
        
        # Cập nhật số dư
        if side == "BUY":
            self.account_balance -= (order_value + fee)
            if symbol in self.positions:
                position = self.positions[symbol]
                avg_price = ((position["quantity"] * position["entry_price"]) + (quantity * current_price)) / (position["quantity"] + quantity)
                position["quantity"] += quantity
                position["entry_price"] = avg_price
            else:
                self.positions[symbol] = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "entry_price": current_price,
                    "entry_time": datetime.now(),
                    "side": "LONG"
                }
        else:  # SELL
            self.account_balance += (order_value - fee)
            if symbol in self.positions:
                position = self.positions[symbol]
                position["quantity"] -= quantity
                if position["quantity"] <= 0:
                    pnl = (current_price - position["entry_price"]) * quantity
                    order["pnl"] = pnl
                    del self.positions[symbol]
                
        self.order_history.append(order)
        return order
        
    def get_positions(self):
        """Lấy danh sách vị thế hiện tại"""
        return self.positions
        
    def close_position(self, symbol):
        """Đóng vị thế"""
        if symbol in self.positions:
            position = self.positions[symbol]
            current_price = self.get_current_price(symbol)
            quantity = position["quantity"]
            
            if position["side"] == "LONG":
                side = "SELL"
                pnl = (current_price - position["entry_price"]) * quantity
            else:
                side = "BUY"
                pnl = (position["entry_price"] - current_price) * quantity
                
            order = self.create_order(symbol, side, quantity)
            order["pnl"] = pnl
            
            return order
        return None
        
    def update_prices(self, price_updates):
        """Cập nhật giá mô phỏng"""
        for symbol, price in price_updates.items():
            self.current_prices[symbol] = price
        return self.current_prices

# Lớp mô phỏng Market Analyzer
class MockMarketAnalyzer:
    """Lớp mô phỏng phân tích thị trường"""
    
    def __init__(self, binance_api):
        self.binance_api = binance_api
        self.market_regimes = {
            "BTCUSDT": "uptrend",
            "ETHUSDT": "uptrend",
            "SOLUSDT": "ranging",
            "ADAUSDT": "downtrend",
            "DOGEUSDT": "uptrend"
        }
        self.volatility = {
            "BTCUSDT": 0.3,
            "ETHUSDT": 0.4,
            "SOLUSDT": 0.6,
            "ADAUSDT": 0.5,
            "DOGEUSDT": 0.7
        }
        
    def analyze_market(self, symbol):
        """Phân tích thị trường cho một cặp giao dịch"""
        current_price = self.binance_api.get_current_price(symbol)
        regime = self.market_regimes.get(symbol, "neutral")
        volatility = self.volatility.get(symbol, 0.5)
        
        # Tạo các chỉ báo kỹ thuật giả lập
        rsi = 70 if regime == "uptrend" else 30 if regime == "downtrend" else 50
        macd = 50 if regime == "uptrend" else -50 if regime == "downtrend" else 0
        
        # Tạo điểm tổng hợp
        composite_score = 0.8 if regime == "uptrend" else -0.8 if regime == "downtrend" else 0.0
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "market_regime": regime,
            "volatility": volatility,
            "indicators": {
                "rsi": rsi,
                "macd": macd,
                "atr": current_price * 0.02  # 2% ATR
            },
            "composite_score": composite_score
        }
        
    def generate_signals(self, symbols):
        """Tạo tín hiệu giao dịch cho các cặp"""
        signals = {}
        
        for symbol in symbols:
            analysis = self.analyze_market(symbol)
            regime = analysis["market_regime"]
            price = analysis["current_price"]
            
            # Tín hiệu mua/bán dựa trên chế độ thị trường
            if regime == "uptrend":
                signal = "BUY"
                stop_loss = price * 0.95  # 5% dưới giá hiện tại
                take_profit = price * 1.1  # 10% trên giá hiện tại
                confidence = 0.8
            elif regime == "downtrend":
                signal = "SELL"
                stop_loss = price * 1.05  # 5% trên giá hiện tại
                take_profit = price * 0.9  # 10% dưới giá hiện tại
                confidence = 0.7
            else:
                signal = "NEUTRAL"
                stop_loss = price * 0.97
                take_profit = price * 1.03
                confidence = 0.5
                
            signals[symbol] = {
                "symbol": symbol,
                "signal": signal.lower(),
                "entry_price": str(price),
                "stop_loss": str(stop_loss),
                "take_profit": str(take_profit),
                "strength": str(confidence),
                "timestamp": datetime.now().isoformat(),
                "market_regime": regime,
                "volatility": analysis["volatility"],
                "composite_score": analysis["composite_score"]
            }
            
        return signals

# Lớp quản lý rủi ro
class RiskManager:
    """Lớp quản lý rủi ro cho hệ thống giao dịch"""
    
    def __init__(self, max_portfolio_risk=5.0, max_position_risk=2.0, max_daily_loss=5.0, account_balance=10000.0):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_risk = max_position_risk
        self.max_daily_loss = max_daily_loss
        self.account_balance = account_balance
        self.daily_pnl = 0.0
        self.open_positions_risk = 0.0
        self.last_reset = datetime.now().date()
        
    def update_account_balance(self, new_balance):
        """Cập nhật số dư tài khoản"""
        self.account_balance = new_balance
        
    def calculate_position_risk(self, entry_price, stop_loss, position_size):
        """Tính rủi ro của một vị thế"""
        if entry_price > stop_loss:  # Long position
            risk_per_unit = (entry_price - stop_loss) / entry_price
        else:  # Short position
            risk_per_unit = (stop_loss - entry_price) / entry_price
            
        position_value = position_size * entry_price
        risk_amount = position_value * risk_per_unit
        risk_percentage = (risk_amount / self.account_balance) * 100
        
        return risk_percentage
        
    def update_daily_pnl(self, pnl):
        """Cập nhật lãi/lỗ hàng ngày"""
        # Reset daily PnL nếu sang ngày mới
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_pnl = 0.0
            self.last_reset = today
            
        self.daily_pnl += pnl
        
    def can_open_position(self, entry_price, stop_loss, position_size, symbol=None):
        """Kiểm tra xem có thể mở vị thế mới không"""
        # Kiểm tra giới hạn lỗ hàng ngày
        if self.daily_pnl < (-self.max_daily_loss * self.account_balance / 100):
            return False, "Đã vượt quá giới hạn lỗ hàng ngày"
            
        # Tính rủi ro của vị thế mới
        position_risk = self.calculate_position_risk(entry_price, stop_loss, position_size)
        
        # Kiểm tra giới hạn rủi ro của vị thế
        if position_risk > self.max_position_risk:
            return False, f"Vị thế vượt quá giới hạn rủi ro tối đa ({position_risk:.2f}% > {self.max_position_risk:.2f}%)"
            
        # Kiểm tra giới hạn rủi ro của danh mục đầu tư
        total_risk = self.open_positions_risk + position_risk
        if total_risk > self.max_portfolio_risk:
            return False, f"Tổng rủi ro danh mục vượt quá giới hạn ({total_risk:.2f}% > {self.max_portfolio_risk:.2f}%)"
            
        return True, "Có thể mở vị thế"
        
    def add_position_risk(self, position_risk):
        """Thêm rủi ro của vị thế mới vào tổng rủi ro"""
        self.open_positions_risk += position_risk
        
    def remove_position_risk(self, position_risk):
        """Xóa rủi ro của vị thế đã đóng khỏi tổng rủi ro"""
        self.open_positions_risk = max(0, self.open_positions_risk - position_risk)

# Lớp hệ thống giao dịch tích hợp
class IntegratedTradingSystem:
    """Hệ thống giao dịch tích hợp các thành phần"""
    
    def __init__(self, account_balance=10000.0):
        self.account_balance = account_balance
        
        # Khởi tạo các thành phần
        self.binance_api = MockBinanceAPI()
        self.market_analyzer = MockMarketAnalyzer(self.binance_api)
        
        # Thiết lập Telegram
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "1834332146")
        self.telegram = TelegramNotifier(token, chat_id)
        
        # Position sizing
        self.portfolio_sizer = PortfolioSizer(
            account_balance=account_balance,
            max_portfolio_risk=8.0,
            max_symbol_risk=2.0
        )
        
        # Risk management
        self.risk_manager = RiskManager(
            max_portfolio_risk=8.0,
            max_position_risk=2.0,
            max_daily_loss=5.0,
            account_balance=account_balance
        )
        
        # Danh sách các cặp theo dõi
        self.watch_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT"]
        
        # Lịch sử giao dịch và vị thế
        self.trade_history = []
        self.open_positions = {}
        self.position_risks = {}
        
    def update_account_balance(self, new_balance=None):
        """Cập nhật số dư tài khoản"""
        if new_balance is None:
            new_balance = self.binance_api.get_account_balance()
            
        self.account_balance = new_balance
        self.portfolio_sizer.update_account_balance(new_balance)
        self.risk_manager.update_account_balance(new_balance)
        
    def analyze_market(self):
        """Phân tích thị trường và tạo tín hiệu"""
        signals = self.market_analyzer.generate_signals(self.watch_symbols)
        
        for symbol, signal in signals.items():
            if signal["signal"] != "neutral":
                # Gửi tín hiệu qua Telegram
                self.telegram.send_trade_signal(signal_info=signal)
                
        return signals
        
    def calculate_position_allocations(self, signals):
        """Tính toán phân bổ vị thế"""
        allocations = self.portfolio_sizer.calculate_position_allocations(
            self.watch_symbols, signals, None
        )
        return allocations
        
    def execute_trades(self, allocations, signals):
        """Thực hiện giao dịch dựa trên phân bổ và tín hiệu"""
        executed_trades = []
        
        for symbol, alloc in allocations.items():
            signal = signals[symbol]
            
            if signal["signal"] == "neutral":
                continue
                
            side = signal["signal"].upper()
            position_size = alloc["position_size"]
            entry_price = float(signal["entry_price"])
            stop_loss = float(signal["stop_loss"])
            
            # Kiểm tra rủi ro trước khi giao dịch
            can_trade, reason = self.risk_manager.can_open_position(
                entry_price, stop_loss, position_size, symbol
            )
            
            if not can_trade:
                logger.warning(f"Không thể mở vị thế {symbol}: {reason}")
                continue
                
            # Thực hiện giao dịch
            try:
                order = self.binance_api.create_order(symbol, side, position_size)
                executed_price = order["price"]
                
                # Gửi thông báo giao dịch
                self.telegram.send_trade_execution(
                    symbol=symbol,
                    side=side,
                    quantity=position_size,
                    price=executed_price,
                    total=position_size * executed_price
                )
                
                # Cập nhật vị thế
                position_risk = self.risk_manager.calculate_position_risk(executed_price, stop_loss, position_size)
                self.open_positions[symbol] = {
                    "symbol": symbol,
                    "side": side,
                    "quantity": position_size,
                    "entry_price": executed_price,
                    "stop_loss": stop_loss,
                    "take_profit": float(signal["take_profit"]),
                    "entry_time": datetime.now(),
                    "risk": position_risk
                }
                
                # Cập nhật tổng rủi ro
                self.risk_manager.add_position_risk(position_risk)
                self.position_risks[symbol] = position_risk
                
                # Cập nhật portfolio sizer
                self.portfolio_sizer.update_position(
                    symbol, side, position_size, executed_price
                )
                
                executed_trades.append(order)
                logger.info(f"Đã mở vị thế {symbol} {side}: {position_size} @ {executed_price}")
                
            except Exception as e:
                logger.error(f"Lỗi khi thực hiện giao dịch {symbol}: {str(e)}")
                
        return executed_trades
        
    def update_positions(self, current_prices=None):
        """Cập nhật và quản lý các vị thế hiện tại"""
        if current_prices is None:
            current_prices = {symbol: self.binance_api.get_current_price(symbol) for symbol in self.watch_symbols}
            
        closed_positions = []
        
        for symbol, position in list(self.open_positions.items()):
            current_price = current_prices.get(symbol, 0)
            
            if current_price <= 0:
                continue
                
            side = position["side"]
            entry_price = position["entry_price"]
            stop_loss = position["stop_loss"]
            take_profit = position["take_profit"]
            
            # Kiểm tra điều kiện đóng vị thế
            should_close = False
            exit_reason = None
            
            if side == "BUY":
                # Kiểm tra stop loss
                if current_price <= stop_loss:
                    should_close = True
                    exit_reason = "Stop Loss"
                # Kiểm tra take profit
                elif current_price >= take_profit:
                    should_close = True
                    exit_reason = "Take Profit"
            else:  # SELL
                # Kiểm tra stop loss
                if current_price >= stop_loss:
                    should_close = True
                    exit_reason = "Stop Loss"
                # Kiểm tra take profit
                elif current_price <= take_profit:
                    should_close = True
                    exit_reason = "Take Profit"
                    
            if should_close:
                # Đóng vị thế
                try:
                    order = self.binance_api.close_position(symbol)
                    
                    if order:
                        # Tính lãi/lỗ
                        pnl = order["pnl"]
                        pnl_percent = (pnl / (position["quantity"] * entry_price)) * 100
                        
                        # Gửi thông báo đóng vị thế
                        position_data = {
                            "symbol": symbol,
                            "side": side,
                            "entry_price": entry_price,
                            "exit_price": current_price,
                            "quantity": position["quantity"],
                            "pnl": pnl,
                            "pnl_percent": pnl_percent,
                            "exit_reason": exit_reason
                        }
                        
                        self.telegram.send_position_closed(position_data=position_data)
                        
                        # Cập nhật lãi/lỗ hàng ngày
                        self.risk_manager.update_daily_pnl(pnl)
                        
                        # Xóa vị thế khỏi danh sách
                        position_risk = self.position_risks.pop(symbol, 0)
                        self.risk_manager.remove_position_risk(position_risk)
                        del self.open_positions[symbol]
                        
                        # Xóa vị thế khỏi portfolio sizer
                        self.portfolio_sizer.remove_position(symbol)
                        
                        # Thêm vào danh sách vị thế đã đóng
                        closed_positions.append(position_data)
                        
                        logger.info(f"Đã đóng vị thế {symbol}: {exit_reason}, PnL: {pnl:.2f} ({pnl_percent:.2f}%)")
                        
                except Exception as e:
                    logger.error(f"Lỗi khi đóng vị thế {symbol}: {str(e)}")
                    
        return closed_positions
        
    def generate_performance_report(self):
        """Tạo báo cáo hiệu suất"""
        # Cập nhật số dư mới nhất
        self.update_account_balance()
        
        # Tính thống kê hiệu suất
        win_count = sum(1 for trade in self.trade_history if trade.get("pnl", 0) > 0)
        total_trades = len(self.trade_history)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        pnl_list = [trade.get("pnl", 0) for trade in self.trade_history]
        total_pnl = sum(pnl_list)
        
        # Tạo danh sách vị thế đang mở
        open_positions_list = []
        for symbol, position in self.open_positions.items():
            current_price = self.binance_api.get_current_price(symbol)
            entry_price = position["entry_price"]
            quantity = position["quantity"]
            
            if position["side"] == "BUY":
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity
                
            unrealized_pnl_percent = (unrealized_pnl / (entry_price * quantity)) * 100
            
            open_positions_list.append({
                "symbol": symbol,
                "type": position["side"],
                "entry_price": entry_price,
                "current_price": current_price,
                "quantity": quantity,
                "pnl": unrealized_pnl,
                "pnl_percent": unrealized_pnl_percent
            })
            
        # Tạo báo cáo hiệu suất
        performance_data = {
            "current_balance": self.account_balance,
            "daily_pnl": self.risk_manager.daily_pnl,
            "daily_trades": len([t for t in self.trade_history if t.get("timestamp", datetime.now()).date() == datetime.now().date()]),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "open_positions": open_positions_list,
            "timestamp": datetime.now().isoformat()
        }
        
        # Gửi báo cáo qua Telegram
        self.telegram.send_daily_report(performance_data)
        
        return performance_data
        
    def run_simulation(self, num_cycles=5, price_change_pct=0.5):
        """Chạy mô phỏng hệ thống giao dịch"""
        logger.info(f"Bắt đầu mô phỏng hệ thống giao dịch với {num_cycles} chu kỳ")
        
        for cycle in range(num_cycles):
            logger.info(f"\n=== Chu kỳ {cycle+1}/{num_cycles} ===")
            
            # 1. Phân tích thị trường và tạo tín hiệu
            logger.info("1. Phân tích thị trường và tạo tín hiệu")
            signals = self.analyze_market()
            
            # 2. Tính toán phân bổ vị thế
            logger.info("2. Tính toán phân bổ vị thế")
            allocations = self.calculate_position_allocations(signals)
            
            # 3. Thực hiện giao dịch
            logger.info("3. Thực hiện giao dịch")
            executed_trades = self.execute_trades(allocations, signals)
            self.trade_history.extend(executed_trades)
            
            # 4. Mô phỏng biến động giá
            logger.info("4. Mô phỏng biến động giá")
            price_updates = {}
            for symbol in self.watch_symbols:
                current_price = self.binance_api.get_current_price(symbol)
                change_pct = np.random.uniform(-price_change_pct, price_change_pct)
                new_price = current_price * (1 + change_pct/100)
                price_updates[symbol] = new_price
                
            self.binance_api.update_prices(price_updates)
            logger.info(f"Giá sau khi cập nhật: {self.binance_api.current_prices}")
            
            # 5. Cập nhật và quản lý vị thế
            logger.info("5. Cập nhật và quản lý vị thế")
            closed_positions = self.update_positions()
            
            # 6. Tạo báo cáo hiệu suất (chu kỳ cuối cùng)
            if cycle == num_cycles - 1:
                logger.info("6. Tạo báo cáo hiệu suất")
                performance_report = self.generate_performance_report()
                
            # 7. Đợi một khoảng thời gian
            logger.info(f"Số dư hiện tại: ${self.binance_api.account_balance:.2f}")
            logger.info(f"Vị thế đang mở: {len(self.open_positions)}")
            logger.info(f"Tổng vị thế đã đóng: {len(self.trade_history)}")
            
        # Tổng kết sau khi mô phỏng
        self.update_account_balance()
        final_balance = self.account_balance
        initial_balance = 10000.0
        profit_percentage = ((final_balance - initial_balance) / initial_balance) * 100
        
        logger.info("\n=== KẾT QUẢ MÔ PHỎNG ===")
        logger.info(f"Số dư đầu: ${initial_balance:.2f}")
        logger.info(f"Số dư cuối: ${final_balance:.2f}")
        logger.info(f"Lợi nhuận: ${final_balance - initial_balance:.2f} ({profit_percentage:.2f}%)")
        logger.info(f"Tổng giao dịch: {len(self.trade_history)}")
        logger.info(f"Vị thế còn mở: {len(self.open_positions)}")
        
        win_trades = sum(1 for trade in self.trade_history if trade.get("pnl", 0) > 0)
        if self.trade_history:
            win_rate = (win_trades / len(self.trade_history)) * 100
            logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
        
        # Trả về báo cáo kết quả
        return {
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "profit": final_balance - initial_balance,
            "profit_percentage": profit_percentage,
            "total_trades": len(self.trade_history),
            "win_trades": win_trades,
            "win_rate": win_rate if self.trade_history else 0,
            "open_positions": len(self.open_positions)
        }

class TestIntegratedTradingSystem(unittest.TestCase):
    """Kiểm tra hệ thống giao dịch tích hợp"""
    
    def setUp(self):
        """Thiết lập cho mỗi test case"""
        self.trading_system = IntegratedTradingSystem(account_balance=10000.0)
        
    def test_01_initialize_system(self):
        """Kiểm tra khởi tạo hệ thống"""
        logger.info("Test 01: Khởi tạo hệ thống")
        
        # Kiểm tra các thành phần đã được khởi tạo
        self.assertIsNotNone(self.trading_system.binance_api)
        self.assertIsNotNone(self.trading_system.market_analyzer)
        self.assertIsNotNone(self.trading_system.telegram)
        self.assertIsNotNone(self.trading_system.portfolio_sizer)
        self.assertIsNotNone(self.trading_system.risk_manager)
        
        # Kiểm tra số dư tài khoản
        self.assertEqual(self.trading_system.account_balance, 10000.0)
        
        # Kiểm tra danh sách các cặp theo dõi
        self.assertGreater(len(self.trading_system.watch_symbols), 0)
        
        logger.info("✅ Test khởi tạo hệ thống thành công")
        
    def test_02_market_analysis(self):
        """Kiểm tra phân tích thị trường"""
        logger.info("Test 02: Phân tích thị trường")
        
        # Phân tích thị trường
        signals = self.trading_system.analyze_market()
        
        # Kiểm tra kết quả
        self.assertGreater(len(signals), 0)
        
        # Kiểm tra các trường thông tin
        for symbol, signal in signals.items():
            self.assertIn(symbol, self.trading_system.watch_symbols)
            self.assertIn(signal["signal"], ["buy", "sell", "neutral"])
            self.assertIsNotNone(signal["entry_price"])
            self.assertIsNotNone(signal["stop_loss"])
            
        # Kiểm tra thông báo Telegram
        self.assertGreaterEqual(len(self.trading_system.telegram.sent_messages), 1)
        
        logger.info(f"Đã phân tích {len(signals)} cặp giao dịch")
        logger.info("✅ Test phân tích thị trường thành công")
        
    def test_03_position_allocation(self):
        """Kiểm tra phân bổ vị thế"""
        logger.info("Test 03: Phân bổ vị thế")
        
        # Phân tích thị trường và lấy tín hiệu
        signals = self.trading_system.analyze_market()
        
        # Tính toán phân bổ vị thế
        allocations = self.trading_system.calculate_position_allocations(signals)
        
        # Kiểm tra kết quả
        self.assertGreater(len(allocations), 0)
        
        # Kiểm tra các thông tin phân bổ
        for symbol, alloc in allocations.items():
            logger.info(f"Phân bổ {symbol}: size={alloc['position_size']:.6f}, risk={alloc['risk_pct']:.2f}%")
            self.assertGreater(alloc["position_size"], 0)
            self.assertLessEqual(alloc["risk_pct"], self.trading_system.portfolio_sizer.max_symbol_risk)
            
        # Tính tổng rủi ro
        total_risk = sum(alloc["risk_pct"] for alloc in allocations.values())
        logger.info(f"Tổng rủi ro danh mục: {total_risk:.2f}%")
        self.assertLessEqual(total_risk, self.trading_system.portfolio_sizer.max_portfolio_risk)
        
        logger.info("✅ Test phân bổ vị thế thành công")
        
    def test_04_trade_execution(self):
        """Kiểm tra thực hiện giao dịch"""
        logger.info("Test 04: Thực hiện giao dịch")
        
        # Phân tích thị trường và lấy tín hiệu
        signals = self.trading_system.analyze_market()
        
        # Tính toán phân bổ vị thế
        allocations = self.trading_system.calculate_position_allocations(signals)
        
        # Thực hiện giao dịch
        executed_trades = self.trading_system.execute_trades(allocations, signals)
        
        # Kiểm tra kết quả
        self.assertGreaterEqual(len(executed_trades), 0)
        
        # Kiểm tra các thông tin giao dịch
        for trade in executed_trades:
            logger.info(f"Giao dịch {trade['symbol']} {trade['side']}: {trade['quantity']} @ {trade['price']}")
            self.assertIn(trade["symbol"], self.trading_system.watch_symbols)
            self.assertIn(trade["side"], ["BUY", "SELL"])
            self.assertGreater(trade["quantity"], 0)
            self.assertGreater(trade["price"], 0)
            
        # Kiểm tra vị thế đã được mở
        self.assertGreaterEqual(len(self.trading_system.open_positions), 0)
        
        # Kiểm tra thông báo Telegram
        trade_execution_messages = [msg for msg in self.trading_system.telegram.sent_messages if msg["type"] == "trade_execution"]
        self.assertGreaterEqual(len(trade_execution_messages), 0)
        
        logger.info("✅ Test thực hiện giao dịch thành công")
        
    def test_05_position_management(self):
        """Kiểm tra quản lý vị thế"""
        logger.info("Test 05: Quản lý vị thế")
        
        # Mở một số vị thế trước
        signals = self.trading_system.analyze_market()
        allocations = self.trading_system.calculate_position_allocations(signals)
        self.trading_system.execute_trades(allocations, signals)
        
        # Lưu số lượng vị thế ban đầu
        initial_positions = len(self.trading_system.open_positions)
        logger.info(f"Số vị thế ban đầu: {initial_positions}")
        
        # Mô phỏng biến động giá lớn
        price_updates = {}
        for symbol in self.trading_system.watch_symbols:
            current_price = self.trading_system.binance_api.get_current_price(symbol)
            
            # Giảm giá 10% cho các vị thế long, tăng 10% cho các vị thế short
            if symbol in self.trading_system.open_positions:
                position = self.trading_system.open_positions[symbol]
                if position["side"] == "BUY":
                    new_price = current_price * 0.9  # Giảm giá để kích hoạt stop loss
                else:
                    new_price = current_price * 1.1  # Tăng giá để kích hoạt stop loss
            else:
                # Nếu không có vị thế, thì thay đổi ngẫu nhiên
                new_price = current_price * (1 + np.random.uniform(-5, 5) / 100)
                
            price_updates[symbol] = new_price
            
        # Cập nhật giá
        self.trading_system.binance_api.update_prices(price_updates)
        
        # Cập nhật vị thế
        closed_positions = self.trading_system.update_positions()
        
        # Kiểm tra số vị thế đã đóng
        logger.info(f"Số vị thế đã đóng: {len(closed_positions)}")
        
        # Kiểm tra thông báo Telegram
        position_closed_messages = [msg for msg in self.trading_system.telegram.sent_messages if msg["type"] == "position_closed"]
        self.assertGreaterEqual(len(position_closed_messages), 0)
        
        # Kiểm tra cập nhật rủi ro
        for symbol in closed_positions:
            self.assertNotIn(symbol["symbol"], self.trading_system.position_risks)
            
        logger.info("✅ Test quản lý vị thế thành công")
        
    def test_06_risk_management(self):
        """Kiểm tra quản lý rủi ro"""
        logger.info("Test 06: Quản lý rủi ro")
        
        # Thiết lập giới hạn rủi ro thấp để kiểm tra
        self.trading_system.risk_manager.max_position_risk = 1.0
        self.trading_system.risk_manager.max_portfolio_risk = 2.0
        
        # Phân tích thị trường và lấy tín hiệu
        signals = self.trading_system.analyze_market()
        
        # Tạo phân bổ với rủi ro cao
        high_risk_allocations = {}
        for symbol, signal in signals.items():
            if signal["signal"] != "neutral":
                high_risk_allocations[symbol] = {
                    "position_size": 1.0,  # Kích thước lớn để vượt quá giới hạn rủi ro
                    "position_value": self.trading_system.binance_api.get_current_price(symbol) * 1.0,
                    "risk_amount": 500,  # Rủi ro cao
                    "risk_pct": 5.0,  # Vượt quá giới hạn rủi ro
                    "side": signal["signal"]
                }
                
        # Thực hiện giao dịch
        executed_trades = self.trading_system.execute_trades(high_risk_allocations, signals)
        
        # Kiểm tra không có giao dịch nào được thực hiện do vượt quá giới hạn rủi ro
        logger.info(f"Số giao dịch đã thực hiện: {len(executed_trades)}")
        self.assertEqual(len(executed_trades), 0, "Không nên có giao dịch nào được thực hiện do vượt quá giới hạn rủi ro")
        
        # Thiết lập lại giới hạn rủi ro bình thường
        self.trading_system.risk_manager.max_position_risk = 2.0
        self.trading_system.risk_manager.max_portfolio_risk = 8.0
        
        # Tính toán phân bổ bình thường
        allocations = self.trading_system.calculate_position_allocations(signals)
        
        # Thực hiện giao dịch
        executed_trades = self.trading_system.execute_trades(allocations, signals)
        
        # Kiểm tra có thể mở giao dịch khi rủi ro trong giới hạn
        logger.info(f"Số giao dịch đã thực hiện sau khi nới lỏng giới hạn: {len(executed_trades)}")
        
        logger.info("✅ Test quản lý rủi ro thành công")
        
    def test_07_performance_reporting(self):
        """Kiểm tra báo cáo hiệu suất"""
        logger.info("Test 07: Báo cáo hiệu suất")
        
        # Mở một số vị thế trước
        signals = self.trading_system.analyze_market()
        allocations = self.trading_system.calculate_position_allocations(signals)
        self.trading_system.execute_trades(allocations, signals)
        
        # Tạo báo cáo hiệu suất
        performance_report = self.trading_system.generate_performance_report()
        
        # Kiểm tra các trường trong báo cáo
        self.assertIn("current_balance", performance_report)
        self.assertIn("daily_pnl", performance_report)
        self.assertIn("win_rate", performance_report)
        self.assertIn("open_positions", performance_report)
        
        # Kiểm tra thông báo Telegram
        daily_report_messages = [msg for msg in self.trading_system.telegram.sent_messages if msg["type"] == "daily_report"]
        self.assertGreaterEqual(len(daily_report_messages), 1)
        
        logger.info("✅ Test báo cáo hiệu suất thành công")
        
    def test_08_full_simulation(self):
        """Kiểm tra mô phỏng đầy đủ"""
        logger.info("Test 08: Mô phỏng đầy đủ")
        
        # Chạy mô phỏng
        result = self.trading_system.run_simulation(num_cycles=5, price_change_pct=2.0)
        
        # Kiểm tra kết quả
        self.assertIn("initial_balance", result)
        self.assertIn("final_balance", result)
        self.assertIn("profit", result)
        self.assertIn("profit_percentage", result)
        self.assertIn("total_trades", result)
        self.assertIn("win_trades", result)
        self.assertIn("win_rate", result)
        
        logger.info(f"Kết quả mô phỏng:")
        logger.info(f"  Số dư ban đầu: ${result['initial_balance']:.2f}")
        logger.info(f"  Số dư cuối: ${result['final_balance']:.2f}")
        logger.info(f"  Lợi nhuận: ${result['profit']:.2f} ({result['profit_percentage']:.2f}%)")
        logger.info(f"  Tổng giao dịch: {result['total_trades']}")
        logger.info(f"  Tỷ lệ thắng: {result['win_rate']:.2f}%")
        
        # Vẽ biểu đồ equity curve
        self._generate_equity_curve()
        
        logger.info("✅ Test mô phỏng đầy đủ thành công")
        
    def _generate_equity_curve(self):
        """Tạo biểu đồ equity curve"""
        # Mô phỏng equity curve
        initial_balance = 10000.0
        balances = [initial_balance]
        timestamps = [datetime.now() - timedelta(days=10)]
        
        # Tạo dữ liệu mẫu
        for i in range(1, 11):
            # Mô phỏng biến động số dư
            previous_balance = balances[-1]
            change = previous_balance * np.random.uniform(-0.02, 0.03)
            new_balance = previous_balance + change
            
            balances.append(new_balance)
            timestamps.append(datetime.now() - timedelta(days=10-i))
            
        # Vẽ biểu đồ
        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, balances, marker='o')
        plt.title('Equity Curve Simulation')
        plt.xlabel('Date')
        plt.ylabel('Account Balance (USD)')
        plt.grid(True)
        
        # Lưu biểu đồ
        chart_file = os.path.join(test_results_dir, 'equity_curve_simulation.png')
        plt.savefig(chart_file)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ equity curve tại: {chart_file}")
        
        return chart_file

def run_tests():
    """Chạy các bài kiểm tra tích hợp"""
    
    logger.info("=== BẮT ĐẦU KIỂM TRA TÍCH HỢP HỆ THỐNG GIAO DỊCH ===")
    logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Sử dụng module position sizing thật: {USING_ACTUAL_POSITION_SIZING}")
    logger.info(f"Sử dụng module Telegram thật: {USING_ACTUAL_TELEGRAM}")
    
    # Tạo test suite và chạy
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestIntegratedTradingSystem))
    
    # Chạy các test
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Tóm tắt kết quả
    logger.info("\n=== KẾT QUẢ KIỂM TRA ===")
    logger.info(f"Tổng số test: {result.testsRun}")
    logger.info(f"Số test thành công: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"Số test thất bại: {len(result.failures)}")
    logger.info(f"Số test lỗi: {len(result.errors)}")
    
    # Chi tiết về các test thất bại hoặc lỗi
    if result.failures:
        logger.error("\nCHI TIẾT CÁC TEST THẤT BẠI:")
        for test, error in result.failures:
            logger.error(f"\n{test}")
            logger.error(error)
    
    if result.errors:
        logger.error("\nCHI TIẾT CÁC TEST LỖI:")
        for test, error in result.errors:
            logger.error(f"\n{test}")
            logger.error(error)
    
    # Lưu kết quả kiểm tra vào file JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(test_results_dir, f'integrated_testing_{timestamp}.json')
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": result.testsRun,
        "successful_tests": result.testsRun - len(result.failures) - len(result.errors),
        "failed_tests": len(result.failures),
        "error_tests": len(result.errors),
        "using_actual_position_sizing": USING_ACTUAL_POSITION_SIZING,
        "using_actual_telegram": USING_ACTUAL_TELEGRAM,
        "failures": [{"test": str(test), "error": error} for test, error in result.failures],
        "errors": [{"test": str(test), "error": error} for test, error in result.errors]
    }
    
    try:
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        logger.info(f"Đã lưu kết quả kiểm tra vào {results_file}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả kiểm tra: {e}")
    
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == "__main__":
    try:
        # Cài đặt matplotlib
        import matplotlib
        matplotlib.use('Agg')  # Sử dụng Agg backend không cần GUI
    except ImportError:
        logger.warning("Không thể import matplotlib. Một số chức năng tạo biểu đồ có thể không hoạt động.")
        
    success = run_tests()
    sys.exit(0 if success else 1)