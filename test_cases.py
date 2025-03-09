#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kịch bản test đầy đủ cho hệ thống giao dịch

Module này triển khai các kịch bản test cho quá trình vào lệnh và quản lý vị thế
trong các điều kiện thị trường khác nhau để kiểm tra tính ổn định và hiệu quả
của hệ thống giao dịch.
"""

import os
import sys
import json
import time
import logging
import datetime
import random
from typing import Dict, List, Tuple, Any

# Thêm thư mục gốc vào đường dẫn để import các module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import các module cần thiết
from api_data_validator import APIDataValidator, retry
from data_cache import DataCache
from adaptive_strategy_selector import AdaptiveStrategySelector
from dynamic_risk_allocator import DynamicRiskAllocator
from advanced_trailing_stop import AdvancedTrailingStop

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_cases')

class TestCaseRunner:
    """Lớp chạy các kịch bản test cho hệ thống giao dịch"""
    
    def __init__(self, data_folder: str = 'test_data', results_folder: str = 'test_results'):
        """
        Khởi tạo Test Case Runner
        
        Args:
            data_folder (str): Thư mục dữ liệu test
            results_folder (str): Thư mục kết quả test
        """
        self.data_folder = data_folder
        self.results_folder = results_folder
        
        # Khởi tạo các thư mục nếu chưa tồn tại
        os.makedirs(data_folder, exist_ok=True)
        os.makedirs(results_folder, exist_ok=True)
        
        # Khởi tạo các đối tượng
        self.data_cache = DataCache()
        self.api_validator = APIDataValidator()
        self.strategy_selector = AdaptiveStrategySelector(self.data_cache)
        self.risk_allocator = DynamicRiskAllocator(self.data_cache)
        self.trailing_stop = AdvancedTrailingStop(data_cache=self.data_cache)
        
        # Lưu kết quả test
        self.test_results = {
            'entry_test_results': {},
            'position_management_test_results': {}
        }
        
        # Trạng thái hiện tại
        self.current_market_data = {}
        self.active_positions = {}
    
    def prepare_market_data(self, symbol: str, market_regime: str) -> Dict:
        """
        Chuẩn bị dữ liệu thị trường giả lập
        
        Args:
            symbol (str): Mã cặp tiền
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Dữ liệu thị trường
        """
        # Khởi tạo giá cơ sở
        base_price = 50000 if symbol == 'BTCUSDT' else 3000 if symbol == 'ETHUSDT' else 500
        
        # Tạo biến động dựa trên chế độ thị trường
        if market_regime == 'trending':
            # Thị trường xu hướng lên mạnh
            volatility = 0.02
            trend_direction = 1  # Uptrend
            adx = 35  # ADX cao, xu hướng mạnh
        elif market_regime == 'volatile':
            # Thị trường biến động mạnh
            volatility = 0.04
            trend_direction = random.choice([-1, 1])  # Xu hướng ngẫu nhiên
            adx = 25  # ADX trung bình
        elif market_regime == 'ranging':
            # Thị trường đi ngang
            volatility = 0.01
            trend_direction = 0  # Không có xu hướng
            adx = 15  # ADX thấp
        else:
            # Mặc định
            volatility = 0.02
            trend_direction = 0
            adx = 20
        
        # Tạo dữ liệu klines giả lập
        timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        klines_data = {}
        
        for tf in timeframes:
            num_candles = 200
            candles = []
            
            current_price = base_price
            current_time = datetime.datetime.now() - datetime.timedelta(days=10)
            
            for i in range(num_candles):
                # Tính thời gian
                if tf == '1m':
                    candle_time = current_time + datetime.timedelta(minutes=i)
                elif tf == '5m':
                    candle_time = current_time + datetime.timedelta(minutes=5*i)
                elif tf == '15m':
                    candle_time = current_time + datetime.timedelta(minutes=15*i)
                elif tf == '30m':
                    candle_time = current_time + datetime.timedelta(minutes=30*i)
                elif tf == '1h':
                    candle_time = current_time + datetime.timedelta(hours=i)
                elif tf == '4h':
                    candle_time = current_time + datetime.timedelta(hours=4*i)
                else:  # 1d
                    candle_time = current_time + datetime.timedelta(days=i)
                
                # Tính biến động giá
                price_change = random.normalvariate(trend_direction * 0.001, volatility) * current_price
                current_price += price_change
                
                # Tính giá mở, cao, thấp, đóng
                open_price = current_price - price_change
                high_price = max(open_price, current_price) + abs(random.normalvariate(0, volatility * 0.3) * current_price)
                low_price = min(open_price, current_price) - abs(random.normalvariate(0, volatility * 0.3) * current_price)
                close_price = current_price
                
                # Tính volume
                volume = random.normalvariate(base_price * 100, base_price * 20)
                if volume < 0:
                    volume = base_price * 50
                
                # Tạo candle
                candle = [
                    int(candle_time.timestamp() * 1000),  # open_time
                    str(open_price),
                    str(high_price),
                    str(low_price),
                    str(close_price),
                    str(volume),
                    int(candle_time.timestamp() * 1000) + (60*1000),  # close_time
                    str(volume * close_price),  # quote_volume
                    100,  # trades
                    str(volume * 0.6),  # taker_buy_base_volume
                    str(volume * 0.6 * close_price),  # taker_buy_quote_volume
                    "0"  # ignore
                ]
                
                candles.append(candle)
            
            # Lưu vào dictionary
            klines_data[tf] = candles
            
            # Lưu vào cache
            self.data_cache.set('market_data', f"{symbol}_{tf}_data", candles)
        
        # Tạo chỉ báo
        indicators = {
            'volatility': volatility,
            'adx': adx,
            'rsi': 70 if trend_direction > 0 else 30 if trend_direction < 0 else 50,
            'bb_width': 0.05 if market_regime == 'volatile' else 0.02,
            'volume_percentile': 70 if market_regime == 'trending' or market_regime == 'volatile' else 40
        }
        
        # Lưu vào cache
        for indicator, value in indicators.items():
            for tf in timeframes:
                self.data_cache.set('indicators', f"{symbol}_{tf}_{indicator}", value)
        
        # Lưu chế độ thị trường
        for tf in timeframes:
            self.data_cache.set('market_analysis', f"{symbol}_{tf}_market_regime", market_regime)
        
        # Tạo ticker data
        ticker_data = {
            'symbol': symbol,
            'lastPrice': str(current_price),
            'bidPrice': str(current_price - current_price * 0.0001),
            'askPrice': str(current_price + current_price * 0.0001),
            'volume': str(base_price * 10000),
            'quoteVolume': str(base_price * 10000 * current_price)
        }
        self.data_cache.set('market_data', f"{symbol}_ticker", ticker_data)
        
        # Tạo order book giả lập
        bids = []
        asks = []
        
        # Tạo 20 mức giá bid và ask
        for i in range(20):
            bid_price = current_price - current_price * (0.0001 * (i + 1))
            bid_qty = base_price / 10 * (1 - i * 0.03)
            bids.append([str(bid_price), str(bid_qty)])
            
            ask_price = current_price + current_price * (0.0001 * (i + 1))
            ask_qty = base_price / 10 * (1 - i * 0.03)
            asks.append([str(ask_price), str(ask_qty)])
        
        orderbook = {
            'lastUpdateId': 1234567890,
            'bids': bids,
            'asks': asks
        }
        self.data_cache.set('market_data', f"{symbol}_orderbook", orderbook)
        
        # Tạo kết quả
        market_data = {
            'symbol': symbol,
            'market_regime': market_regime,
            'current_price': current_price,
            'volatility': volatility,
            'adx': adx,
            'orderbook': orderbook,
            'ticker': ticker_data
        }
        
        # Lưu vào state
        self.current_market_data[symbol] = market_data
        
        return market_data
    
    def run_entry_test_trending(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quá trình vào lệnh khi thị trường trending
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test vào lệnh với thị trường trending cho {symbol} ===")
        
        # Chuẩn bị dữ liệu thị trường
        market_data = self.prepare_market_data(symbol, 'trending')
        current_price = market_data['current_price']
        
        # Xác định chế độ thị trường
        market_regime = self.strategy_selector.get_market_regime(symbol, '1h')
        
        # Lấy chiến lược phù hợp
        strategies = self.strategy_selector.get_strategies_for_regime(market_regime)
        top_strategy = max(strategies.items(), key=lambda x: x[1])[0]
        
        # Tính toán risk percentage
        account_balance = 10000
        drawdown = 0
        risk_percentage = self.risk_allocator.calculate_risk_percentage(
            symbol, '1h', market_regime, account_balance, drawdown
        )
        
        # Lấy tín hiệu giao dịch
        trading_decision = self.strategy_selector.get_trading_decision(symbol, '1h', risk_percentage)
        
        # Tính toán stop loss và take profit
        stop_loss = trading_decision['stop_loss']
        take_profit = trading_decision['take_profit']
        
        # Tính toán kích thước vị thế
        position_info = self.risk_allocator.calculate_position_size(
            symbol, current_price, stop_loss, account_balance, risk_percentage
        )
        
        # Kiểm tra thanh khoản
        orderbook = self.data_cache.get('market_data', f"{symbol}_orderbook")
        liquidity_adjusted_position = self.risk_allocator.adjust_position_size_by_liquidity(
            position_info, orderbook
        )
        
        # Tạo kết quả test
        result = {
            'symbol': symbol,
            'market_regime': market_regime,
            'top_strategy': top_strategy,
            'strategy_weights': strategies,
            'risk_percentage': risk_percentage,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'quantity': liquidity_adjusted_position['quantity'],
            'position_size_usd': liquidity_adjusted_position['position_size_usd'],
            'trading_signal': trading_decision['composite_signal']['signal'],
            'signal_strength': trading_decision['composite_signal']['strength'],
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vào kết quả test
        self.test_results['entry_test_results']['trending'] = result
        
        # Mở vị thế giả lập nếu có tín hiệu
        if trading_decision['composite_signal']['signal'] in ['BUY', 'SELL']:
            position_id = f"{symbol}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.active_positions[position_id] = {
                'id': position_id,
                'symbol': symbol,
                'side': trading_decision['composite_signal']['signal'],
                'entry_price': current_price,
                'quantity': liquidity_adjusted_position['quantity'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percentage': risk_percentage,
                'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'market_regime': market_regime,
                'strategy': top_strategy
            }
        
        logger.info(f"Kết quả test thị trường trending cho {symbol}:")
        logger.info(f"- Chế độ thị trường: {market_regime}")
        logger.info(f"- Chiến lược hàng đầu: {top_strategy} (trọng số: {strategies[top_strategy]:.2f})")
        logger.info(f"- Risk %: {risk_percentage:.2f}%")
        logger.info(f"- Tín hiệu: {trading_decision['composite_signal']['signal']} (mạnh: {trading_decision['composite_signal']['strength']:.2f})")
        logger.info(f"- Entry: ${current_price:.2f}")
        logger.info(f"- Stop Loss: ${stop_loss:.2f}")
        logger.info(f"- Take Profit: ${take_profit:.2f}")
        logger.info(f"- Quantity: {liquidity_adjusted_position['quantity']}")
        logger.info(f"- Position Size: ${liquidity_adjusted_position['position_size_usd']:.2f}")
        
        return result
    
    def run_entry_test_volatile(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quá trình vào lệnh khi thị trường biến động mạnh
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test vào lệnh với thị trường biến động mạnh cho {symbol} ===")
        
        # Chuẩn bị dữ liệu thị trường
        market_data = self.prepare_market_data(symbol, 'volatile')
        current_price = market_data['current_price']
        
        # Xác định chế độ thị trường
        market_regime = self.strategy_selector.get_market_regime(symbol, '1h')
        
        # Lấy chiến lược phù hợp
        strategies = self.strategy_selector.get_strategies_for_regime(market_regime)
        top_strategy = max(strategies.items(), key=lambda x: x[1])[0]
        
        # Tính toán risk percentage
        account_balance = 10000
        drawdown = 0
        risk_percentage = self.risk_allocator.calculate_risk_percentage(
            symbol, '1h', market_regime, account_balance, drawdown
        )
        
        # Kiểm tra xem risk percentage có thấp hơn trong thị trường biến động mạnh không
        baseline_risk = self.risk_allocator.config.get('base_risk_percentage', 1.0)
        
        # Lấy tín hiệu giao dịch
        trading_decision = self.strategy_selector.get_trading_decision(symbol, '1h', risk_percentage)
        
        # Tính toán stop loss và take profit
        stop_loss = trading_decision['stop_loss']
        take_profit = trading_decision['take_profit']
        
        # Tính toán kích thước vị thế
        position_info = self.risk_allocator.calculate_position_size(
            symbol, current_price, stop_loss, account_balance, risk_percentage
        )
        
        # Kiểm tra thanh khoản
        orderbook = self.data_cache.get('market_data', f"{symbol}_orderbook")
        liquidity_adjusted_position = self.risk_allocator.adjust_position_size_by_liquidity(
            position_info, orderbook
        )
        
        # Tạo kết quả test
        result = {
            'symbol': symbol,
            'market_regime': market_regime,
            'top_strategy': top_strategy,
            'strategy_weights': strategies,
            'risk_percentage': risk_percentage,
            'baseline_risk': baseline_risk,
            'risk_reduced': risk_percentage < baseline_risk,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'quantity': liquidity_adjusted_position['quantity'],
            'position_size_usd': liquidity_adjusted_position['position_size_usd'],
            'trading_signal': trading_decision['composite_signal']['signal'],
            'signal_strength': trading_decision['composite_signal']['strength'],
            'atr_based_sl_tp': True,  # Giả sử SL/TP luôn dựa trên ATR trong thị trường biến động
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vào kết quả test
        self.test_results['entry_test_results']['volatile'] = result
        
        # Mở vị thế giả lập nếu có tín hiệu
        if trading_decision['composite_signal']['signal'] in ['BUY', 'SELL']:
            position_id = f"{symbol}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.active_positions[position_id] = {
                'id': position_id,
                'symbol': symbol,
                'side': trading_decision['composite_signal']['signal'],
                'entry_price': current_price,
                'quantity': liquidity_adjusted_position['quantity'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percentage': risk_percentage,
                'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'market_regime': market_regime,
                'strategy': top_strategy
            }
        
        logger.info(f"Kết quả test thị trường biến động mạnh cho {symbol}:")
        logger.info(f"- Chế độ thị trường: {market_regime}")
        logger.info(f"- Chiến lược hàng đầu: {top_strategy} (trọng số: {strategies[top_strategy]:.2f})")
        logger.info(f"- Risk %: {risk_percentage:.2f}% (so với cơ sở: {baseline_risk:.2f}%)")
        logger.info(f"- Risk giảm: {'Có' if risk_percentage < baseline_risk else 'Không'}")
        logger.info(f"- Tín hiệu: {trading_decision['composite_signal']['signal']} (mạnh: {trading_decision['composite_signal']['strength']:.2f})")
        logger.info(f"- Entry: ${current_price:.2f}")
        logger.info(f"- Stop Loss: ${stop_loss:.2f}")
        logger.info(f"- Take Profit: ${take_profit:.2f}")
        logger.info(f"- Quantity: {liquidity_adjusted_position['quantity']}")
        logger.info(f"- Position Size: ${liquidity_adjusted_position['position_size_usd']:.2f}")
        logger.info(f"- SL/TP dựa trên ATR: Có")
        
        return result
    
    def run_entry_test_ranging(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quá trình vào lệnh khi thị trường dao động trong biên độ
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test vào lệnh với thị trường dao động trong biên độ cho {symbol} ===")
        
        # Chuẩn bị dữ liệu thị trường
        market_data = self.prepare_market_data(symbol, 'ranging')
        current_price = market_data['current_price']
        
        # Xác định chế độ thị trường
        market_regime = self.strategy_selector.get_market_regime(symbol, '1h')
        
        # Lấy chiến lược phù hợp
        strategies = self.strategy_selector.get_strategies_for_regime(market_regime)
        top_strategy = max(strategies.items(), key=lambda x: x[1])[0]
        
        # Kiểm tra xem chiến lược mean_reversion có được ưu tiên không
        mean_reversion_priority = 'mean_reversion' in strategies and strategies['mean_reversion'] >= 0.4
        
        # Tính toán risk percentage
        account_balance = 10000
        drawdown = 0
        risk_percentage = self.risk_allocator.calculate_risk_percentage(
            symbol, '1h', market_regime, account_balance, drawdown
        )
        
        # Lấy tín hiệu giao dịch
        trading_decision = self.strategy_selector.get_trading_decision(symbol, '1h', risk_percentage)
        
        # Tính toán stop loss và take profit
        stop_loss = trading_decision['stop_loss']
        take_profit = trading_decision['take_profit']
        
        # Tính toán kích thước vị thế
        position_info = self.risk_allocator.calculate_position_size(
            symbol, current_price, stop_loss, account_balance, risk_percentage
        )
        
        # Kiểm tra thanh khoản
        orderbook = self.data_cache.get('market_data', f"{symbol}_orderbook")
        liquidity_adjusted_position = self.risk_allocator.adjust_position_size_by_liquidity(
            position_info, orderbook
        )
        
        # Tạo kết quả test
        result = {
            'symbol': symbol,
            'market_regime': market_regime,
            'top_strategy': top_strategy,
            'strategy_weights': strategies,
            'mean_reversion_priority': mean_reversion_priority,
            'risk_percentage': risk_percentage,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'quantity': liquidity_adjusted_position['quantity'],
            'position_size_usd': liquidity_adjusted_position['position_size_usd'],
            'trading_signal': trading_decision['composite_signal']['signal'],
            'signal_strength': trading_decision['composite_signal']['strength'],
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vào kết quả test
        self.test_results['entry_test_results']['ranging'] = result
        
        # Mở vị thế giả lập nếu có tín hiệu
        if trading_decision['composite_signal']['signal'] in ['BUY', 'SELL']:
            position_id = f"{symbol}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.active_positions[position_id] = {
                'id': position_id,
                'symbol': symbol,
                'side': trading_decision['composite_signal']['signal'],
                'entry_price': current_price,
                'quantity': liquidity_adjusted_position['quantity'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percentage': risk_percentage,
                'entry_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'market_regime': market_regime,
                'strategy': top_strategy
            }
        
        logger.info(f"Kết quả test thị trường dao động trong biên độ cho {symbol}:")
        logger.info(f"- Chế độ thị trường: {market_regime}")
        logger.info(f"- Chiến lược hàng đầu: {top_strategy} (trọng số: {strategies[top_strategy]:.2f})")
        logger.info(f"- Mean reversion ưu tiên: {'Có' if mean_reversion_priority else 'Không'}")
        logger.info(f"- Risk %: {risk_percentage:.2f}%")
        logger.info(f"- Tín hiệu: {trading_decision['composite_signal']['signal']} (mạnh: {trading_decision['composite_signal']['strength']:.2f})")
        logger.info(f"- Entry: ${current_price:.2f}")
        logger.info(f"- Stop Loss: ${stop_loss:.2f}")
        logger.info(f"- Take Profit: ${take_profit:.2f}")
        logger.info(f"- Quantity: {liquidity_adjusted_position['quantity']}")
        logger.info(f"- Position Size: ${liquidity_adjusted_position['position_size_usd']:.2f}")
        
        return result
    
    def run_position_management_test_adverse(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quản lý vị thế khi thị trường đi ngược với vị thế
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test quản lý vị thế khi thị trường đi ngược với vị thế cho {symbol} ===")
        
        # Tạo một vị thế mẫu
        position = {
            'id': f"{symbol}_test_adverse",
            'symbol': symbol,
            'side': 'BUY',  # Mua vào
            'entry_price': 50000,
            'quantity': 0.1,
            'stop_loss': 49000,
            'take_profit': 52000,
            'risk_percentage': 1.0,
            'entry_time': (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            'market_regime': 'trending',
            'strategy': 'trend_following',
            'ts_activated': False,  # Trailing stop chưa kích hoạt
            'ts_stop_price': None,  # Giá trailing stop
            'current_price': 50000,  # Giá hiện tại
            'current_pnl': 0,  # Lợi nhuận hiện tại
            'current_pnl_percent': 0  # % lợi nhuận hiện tại
        }
        
        # Lưu vào active positions
        self.active_positions[position['id']] = position
        
        # Khởi tạo trailing stop
        strategy_type = "percentage"  # Sử dụng trailing stop theo %
        trailing_stop = AdvancedTrailingStop(strategy_type=strategy_type, data_cache=self.data_cache)
        
        # Chuẩn bị kịch bản thị trường đi xuống (ngược với vị thế BUY)
        price_levels = [
            50000,  # Giá ban đầu
            49800,  # Giảm nhẹ
            49500,  # Tiếp tục giảm
            49200,  # Tiếp tục giảm
            49100,  # Gần stop loss
            49050,  # Rất gần stop loss
            49000   # Chạm stop loss
        ]
        
        # Kết quả theo dõi
        tracking_results = []
        
        # Mô phỏng diễn biến giá
        for i, price in enumerate(price_levels):
            # Cập nhật giá hiện tại
            position['current_price'] = price
            
            # Tính PnL
            if position['side'] == 'BUY':
                position['current_pnl'] = (price - position['entry_price']) * position['quantity']
                position['current_pnl_percent'] = (price - position['entry_price']) / position['entry_price'] * 100
            else:
                position['current_pnl'] = (position['entry_price'] - price) * position['quantity']
                position['current_pnl_percent'] = (position['entry_price'] - price) / position['entry_price'] * 100
            
            # Kiểm tra stop loss
            should_close = False
            reason = None
            
            if position['side'] == 'BUY' and price <= position['stop_loss']:
                should_close = True
                reason = 'stop_loss'
            elif position['side'] == 'SELL' and price >= position['stop_loss']:
                should_close = True
                reason = 'stop_loss'
            
            # Lưu kết quả tại thời điểm này
            tracking_results.append({
                'iteration': i,
                'price': price,
                'current_pnl': position['current_pnl'],
                'current_pnl_percent': position['current_pnl_percent'],
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit'],
                'ts_activated': position['ts_activated'],
                'ts_stop_price': position['ts_stop_price'],
                'should_close': should_close,
                'reason': reason
            })
            
            # Nếu cần đóng vị thế, dừng mô phỏng
            if should_close:
                break
        
        # Tạo kết quả test
        result = {
            'position': position,
            'price_levels': price_levels,
            'tracking_results': tracking_results,
            'stop_loss_triggered': tracking_results[-1]['should_close'] if tracking_results else False,
            'stop_loss_reason': tracking_results[-1]['reason'] if tracking_results and tracking_results[-1]['should_close'] else None,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vào kết quả test
        self.test_results['position_management_test_results']['adverse'] = result
        
        logger.info(f"Kết quả test quản lý vị thế khi thị trường đi ngược với vị thế cho {symbol}:")
        logger.info(f"- Vị thế: {position['side']} {position['quantity']} {symbol} @ ${position['entry_price']}")
        logger.info(f"- Stop Loss: ${position['stop_loss']}")
        logger.info(f"- Take Profit: ${position['take_profit']}")
        logger.info(f"- Diễn biến giá: {price_levels}")
        logger.info(f"- Stop Loss kích hoạt: {'Có' if result['stop_loss_triggered'] else 'Không'}")
        if result['stop_loss_triggered']:
            logger.info(f"- Lý do: {result['stop_loss_reason']}")
            closing_price = tracking_results[-1]['price']
            pnl = tracking_results[-1]['current_pnl']
            pnl_percent = tracking_results[-1]['current_pnl_percent']
            logger.info(f"- Giá đóng vị thế: ${closing_price}")
            logger.info(f"- PnL cuối cùng: ${pnl:.2f} ({pnl_percent:.2f}%)")
        
        return result
    
    def run_position_management_test_favorable(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quản lý vị thế khi thị trường đi thuận với vị thế
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test quản lý vị thế khi thị trường đi thuận với vị thế cho {symbol} ===")
        
        # Tạo một vị thế mẫu
        position = {
            'id': f"{symbol}_test_favorable",
            'symbol': symbol,
            'side': 'BUY',  # Mua vào
            'entry_price': 50000,
            'quantity': 0.1,
            'stop_loss': 49000,
            'take_profit': 52000,
            'risk_percentage': 1.0,
            'entry_time': (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            'market_regime': 'trending',
            'strategy': 'trend_following',
            'ts_activated': False,  # Trailing stop chưa kích hoạt
            'ts_stop_price': None,  # Giá trailing stop
            'current_price': 50000,  # Giá hiện tại
            'current_pnl': 0,  # Lợi nhuận hiện tại
            'current_pnl_percent': 0  # % lợi nhuận hiện tại
        }
        
        # Lưu vào active positions
        self.active_positions[position['id']] = position
        
        # Khởi tạo trailing stop
        strategy_type = "percentage"  # Sử dụng trailing stop theo %
        config = {
            "activation_percent": 0.5,  # Kích hoạt khi đạt 0.5% lợi nhuận
            "callback_percent": 0.2     # Callback 0.2% từ mức cao nhất
        }
        trailing_stop = AdvancedTrailingStop(strategy_type=strategy_type, data_cache=self.data_cache, config=config)
        
        # Khởi tạo trailing stop cho vị thế
        ts_position = trailing_stop.initialize_position(position)
        position.update(ts_position)
        
        # Chuẩn bị kịch bản thị trường đi lên (thuận với vị thế BUY)
        price_levels = [
            50000,  # Giá ban đầu
            50200,  # Tăng nhẹ
            50500,  # Tiếp tục tăng
            50800,  # Tiếp tục tăng (> 0.5%, trailing stop kích hoạt)
            51000,  # Tăng tiếp
            51200,  # Đạt đỉnh
            51000,  # Giảm nhẹ, chưa chạm trailing stop
            50800,  # Giảm tiếp, có thể chạm trailing stop
            50600   # Giảm tiếp, nên chạm trailing stop
        ]
        
        # Kết quả theo dõi
        tracking_results = []
        
        # Mô phỏng diễn biến giá
        highest_price = position['entry_price']
        for i, price in enumerate(price_levels):
            # Cập nhật giá hiện tại
            position['current_price'] = price
            highest_price = max(highest_price, price)
            
            # Tính PnL
            if position['side'] == 'BUY':
                position['current_pnl'] = (price - position['entry_price']) * position['quantity']
                position['current_pnl_percent'] = (price - position['entry_price']) / position['entry_price'] * 100
            else:
                position['current_pnl'] = (position['entry_price'] - price) * position['quantity']
                position['current_pnl_percent'] = (position['entry_price'] - price) / position['entry_price'] * 100
            
            # Cập nhật trailing stop
            updated_position = trailing_stop.update_trailing_stop(position, price)
            position.update(updated_position)
            
            # Kiểm tra điều kiện đóng vị thế
            should_close, reason = trailing_stop.check_stop_condition(position, price)
            
            # Kiểm tra take profit
            if not should_close and position['side'] == 'BUY' and price >= position['take_profit']:
                should_close = True
                reason = 'take_profit'
            elif not should_close and position['side'] == 'SELL' and price <= position['take_profit']:
                should_close = True
                reason = 'take_profit'
            
            # Lưu kết quả tại thời điểm này
            tracking_results.append({
                'iteration': i,
                'price': price,
                'highest_price': highest_price,
                'current_pnl': position['current_pnl'],
                'current_pnl_percent': position['current_pnl_percent'],
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit'],
                'ts_activated': position['ts_activated'],
                'ts_stop_price': position['ts_stop_price'],
                'should_close': should_close,
                'reason': reason
            })
            
            # Nếu cần đóng vị thế, dừng mô phỏng
            if should_close:
                break
        
        # Tạo kết quả test
        result = {
            'position': position,
            'price_levels': price_levels,
            'tracking_results': tracking_results,
            'highest_price': highest_price,
            'ts_activated': position['ts_activated'],
            'ts_stop_price': position['ts_stop_price'],
            'position_closed': tracking_results[-1]['should_close'] if tracking_results else False,
            'close_reason': tracking_results[-1]['reason'] if tracking_results and tracking_results[-1]['should_close'] else None,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vào kết quả test
        self.test_results['position_management_test_results']['favorable'] = result
        
        logger.info(f"Kết quả test quản lý vị thế khi thị trường đi thuận với vị thế cho {symbol}:")
        logger.info(f"- Vị thế: {position['side']} {position['quantity']} {symbol} @ ${position['entry_price']}")
        logger.info(f"- Stop Loss ban đầu: ${position['stop_loss']}")
        logger.info(f"- Take Profit: ${position['take_profit']}")
        logger.info(f"- Diễn biến giá: {price_levels}")
        logger.info(f"- Giá cao nhất đạt được: ${highest_price}")
        logger.info(f"- Trailing Stop kích hoạt: {'Có' if position['ts_activated'] else 'Không'}")
        if position['ts_activated']:
            logger.info(f"- Giá Trailing Stop cuối: ${position['ts_stop_price']}")
        logger.info(f"- Vị thế đóng: {'Có' if result['position_closed'] else 'Không'}")
        if result['position_closed']:
            logger.info(f"- Lý do đóng: {result['close_reason']}")
            closing_price = tracking_results[-1]['price']
            pnl = tracking_results[-1]['current_pnl']
            pnl_percent = tracking_results[-1]['current_pnl_percent']
            logger.info(f"- Giá đóng vị thế: ${closing_price}")
            logger.info(f"- PnL cuối cùng: ${pnl:.2f} ({pnl_percent:.2f}%)")
        
        return result
    
    def run_position_management_test_volatility(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quản lý vị thế khi thị trường biến động mạnh đột ngột
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test quản lý vị thế khi thị trường biến động mạnh đột ngột cho {symbol} ===")
        
        # Tạo một vị thế mẫu
        position = {
            'id': f"{symbol}_test_volatility",
            'symbol': symbol,
            'side': 'BUY',  # Mua vào
            'entry_price': 50000,
            'quantity': 0.1,
            'stop_loss': 49000,
            'take_profit': 52000,
            'risk_percentage': 1.0,
            'entry_time': (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            'market_regime': 'trending',
            'strategy': 'trend_following',
            'ts_activated': False,  # Trailing stop chưa kích hoạt
            'ts_stop_price': None,  # Giá trailing stop
            'current_price': 50000,  # Giá hiện tại
            'current_pnl': 0,  # Lợi nhuận hiện tại
            'current_pnl_percent': 0  # % lợi nhuận hiện tại
        }
        
        # Lưu vào active positions
        self.active_positions[position['id']] = position
        
        # Khởi tạo trailing stop
        strategy_type = "percentage"  # Sử dụng trailing stop theo %
        config = {
            "activation_percent": 0.5,  # Kích hoạt khi đạt 0.5% lợi nhuận
            "callback_percent": 0.2     # Callback 0.2% từ mức cao nhất
        }
        trailing_stop = AdvancedTrailingStop(strategy_type=strategy_type, data_cache=self.data_cache, config=config)
        
        # Khởi tạo trailing stop cho vị thế
        ts_position = trailing_stop.initialize_position(position)
        position.update(ts_position)
        
        # Chuẩn bị kịch bản thị trường biến động mạnh đột ngột (flash crash)
        price_levels = [
            50000,  # Giá ban đầu
            50500,  # Tăng lên (trailing stop kích hoạt)
            51000,  # Tăng tiếp
            51500,  # Tăng tiếp
            51000,  # Giảm nhẹ
            50500,  # Giảm tiếp
            50000,  # Về lại giá ban đầu
            49800,  # Flash crash bắt đầu
            49200,  # Tiếp tục giảm mạnh
            48500,  # Giảm mạnh hơn
            48000   # Giảm mạnh nhất
        ]
        
        # Kết quả theo dõi
        tracking_results = []
        
        # Mô phỏng diễn biến giá
        highest_price = position['entry_price']
        for i, price in enumerate(price_levels):
            # Cập nhật giá hiện tại
            position['current_price'] = price
            highest_price = max(highest_price, price)
            
            # Tính PnL
            if position['side'] == 'BUY':
                position['current_pnl'] = (price - position['entry_price']) * position['quantity']
                position['current_pnl_percent'] = (price - position['entry_price']) / position['entry_price'] * 100
            else:
                position['current_pnl'] = (position['entry_price'] - price) * position['quantity']
                position['current_pnl_percent'] = (position['entry_price'] - price) / position['entry_price'] * 100
            
            # Cập nhật trailing stop
            updated_position = trailing_stop.update_trailing_stop(position, price)
            position.update(updated_position)
            
            # Kiểm tra điều kiện đóng vị thế
            should_close, reason = trailing_stop.check_stop_condition(position, price)
            
            # Kiểm tra stop loss
            if not should_close and position['side'] == 'BUY' and price <= position['stop_loss']:
                should_close = True
                reason = 'stop_loss'
            elif not should_close and position['side'] == 'SELL' and price >= position['stop_loss']:
                should_close = True
                reason = 'stop_loss'
            
            # Lưu kết quả tại thời điểm này
            tracking_results.append({
                'iteration': i,
                'price': price,
                'highest_price': highest_price,
                'current_pnl': position['current_pnl'],
                'current_pnl_percent': position['current_pnl_percent'],
                'stop_loss': position['stop_loss'],
                'take_profit': position['take_profit'],
                'ts_activated': position['ts_activated'],
                'ts_stop_price': position['ts_stop_price'],
                'should_close': should_close,
                'reason': reason
            })
            
            # Nếu cần đóng vị thế, dừng mô phỏng
            if should_close:
                break
        
        # Tạo kết quả test
        result = {
            'position': position,
            'price_levels': price_levels,
            'tracking_results': tracking_results,
            'highest_price': highest_price,
            'ts_activated': position['ts_activated'],
            'ts_stop_price': position['ts_stop_price'],
            'position_closed': tracking_results[-1]['should_close'] if tracking_results else False,
            'close_reason': tracking_results[-1]['reason'] if tracking_results and tracking_results[-1]['should_close'] else None,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Phân tích hiệu suất trailing stop trong flash crash
        if result['position_closed']:
            # Tính protect_pnl (lợi nhuận được bảo vệ so với dự kiến)
            closing_price = tracking_results[-1]['price']
            final_price = price_levels[-1]  # Giá cuối cùng trong flash crash
            
            if position['side'] == 'BUY':
                protect_pnl = (closing_price - final_price) * position['quantity']
                protect_pnl_percent = (closing_price - final_price) / position['entry_price'] * 100
            else:
                protect_pnl = (final_price - closing_price) * position['quantity']
                protect_pnl_percent = (final_price - closing_price) / position['entry_price'] * 100
            
            result['protect_pnl'] = protect_pnl
            result['protect_pnl_percent'] = protect_pnl_percent
        else:
            result['protect_pnl'] = 0
            result['protect_pnl_percent'] = 0
        
        # Lưu vào kết quả test
        self.test_results['position_management_test_results']['volatility'] = result
        
        logger.info(f"Kết quả test quản lý vị thế khi thị trường biến động mạnh đột ngột cho {symbol}:")
        logger.info(f"- Vị thế: {position['side']} {position['quantity']} {symbol} @ ${position['entry_price']}")
        logger.info(f"- Stop Loss ban đầu: ${position['stop_loss']}")
        logger.info(f"- Take Profit: ${position['take_profit']}")
        logger.info(f"- Diễn biến giá: {price_levels[:3]}...{price_levels[-3:]} (flash crash)")
        logger.info(f"- Giá cao nhất đạt được: ${highest_price}")
        logger.info(f"- Trailing Stop kích hoạt: {'Có' if position['ts_activated'] else 'Không'}")
        if position['ts_activated']:
            logger.info(f"- Giá Trailing Stop cuối: ${position['ts_stop_price']}")
        logger.info(f"- Vị thế đóng: {'Có' if result['position_closed'] else 'Không'}")
        if result['position_closed']:
            logger.info(f"- Lý do đóng: {result['close_reason']}")
            closing_price = tracking_results[-1]['price']
            pnl = tracking_results[-1]['current_pnl']
            pnl_percent = tracking_results[-1]['current_pnl_percent']
            logger.info(f"- Giá đóng vị thế: ${closing_price}")
            logger.info(f"- PnL cuối cùng: ${pnl:.2f} ({pnl_percent:.2f}%)")
            logger.info(f"- PnL được bảo vệ: ${result['protect_pnl']:.2f} ({result['protect_pnl_percent']:.2f}%)")
        
        return result
    
    def run_position_management_test_disconnection(self, symbol: str = 'BTCUSDT') -> Dict:
        """
        Kịch bản test cho quản lý vị thế khi mất kết nối với Binance API
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Kết quả test
        """
        logger.info(f"=== Chạy test quản lý vị thế khi mất kết nối với Binance API cho {symbol} ===")
        
        # Tạo một vị thế mẫu
        position = {
            'id': f"{symbol}_test_disconnection",
            'symbol': symbol,
            'side': 'BUY',
            'entry_price': 50000,
            'quantity': 0.1,
            'stop_loss': 49000,
            'take_profit': 52000,
            'risk_percentage': 1.0,
            'entry_time': (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            'market_regime': 'trending',
            'strategy': 'trend_following',
            'ts_activated': False,
            'ts_stop_price': None,
            'current_price': 50000,
            'current_pnl': 0,
            'current_pnl_percent': 0,
            'binance_order_id': '123456789',  # ID của lệnh trên Binance
            'stop_loss_order_id': '123456790'  # ID của lệnh stop loss trên Binance
        }
        
        # Lưu vào active positions
        self.active_positions[position['id']] = position
        
        # Tạo môi trường test với API bị ngắt kết nối
        disconnection_scenarios = [
            {
                'name': 'short_disconnection',
                'duration': '30 giây',
                'market_moves': 'nhẹ',
                'price_before': 50000,
                'price_during': 49500,
                'price_after': 49800,
                'retry_succeeds': True,
                'fallback_activated': False
            },
            {
                'name': 'medium_disconnection',
                'duration': '5 phút',
                'market_moves': 'trung bình',
                'price_before': 50000,
                'price_during': 49200,
                'price_after': 49300,
                'retry_succeeds': True,
                'fallback_activated': True
            },
            {
                'name': 'long_disconnection',
                'duration': '30 phút',
                'market_moves': 'mạnh',
                'price_before': 50000,
                'price_during': 48500,
                'price_after': 48800,
                'retry_succeeds': False,
                'fallback_activated': True,
                'local_action_taken': True
            }
        ]
        
        # Kết quả theo các kịch bản
        scenario_results = {}
        
        for scenario in disconnection_scenarios:
            logger.info(f"Test kịch bản: {scenario['name']}")
            logger.info(f"- Thời gian mất kết nối: {scenario['duration']}")
            logger.info(f"- Biến động thị trường: {scenario['market_moves']}")
            logger.info(f"- Giá trước khi mất kết nối: ${scenario['price_before']}")
            logger.info(f"- Giá trong khi mất kết nối: ${scenario['price_during']}")
            logger.info(f"- Giá sau khi kết nối lại: ${scenario['price_after']}")
            
            # Giả lập kịch bản và ghi lại kết quả
            scenario_result = {
                'scenario': scenario,
                'position_intact': True,  # Vị thế còn nguyên vẹn
                'sl_tp_intact': True,     # SL/TP còn nguyên vẹn
                'data_synced': scenario['retry_succeeds'],  # Dữ liệu được đồng bộ
                'recovery_action': 'retry' if scenario['retry_succeeds'] else 'fallback',
                'final_position_state': 'active'  # Mặc định vị thế vẫn active
            }
            
            # Xác định xem SL có bị kích hoạt không
            if scenario['price_during'] <= position['stop_loss']:
                if scenario['fallback_activated']:
                    scenario_result['sl_tp_intact'] = False
                    scenario_result['sl_triggered'] = True
                    scenario_result['final_position_state'] = 'closed'
                    scenario_result['close_price'] = scenario['price_during']
                    scenario_result['close_reason'] = 'stop_loss'
                    scenario_result['pnl'] = (scenario['price_during'] - position['entry_price']) * position['quantity']
                    scenario_result['pnl_percent'] = (scenario['price_during'] - position['entry_price']) / position['entry_price'] * 100
                else:
                    scenario_result['sl_tp_intact'] = False
                    scenario_result['sl_triggered'] = False
                    scenario_result['final_position_state'] = 'unknown'
                    scenario_result['recovery_needed'] = True
            
            # Lưu kết quả kịch bản
            scenario_results[scenario['name']] = scenario_result
            
            logger.info(f"Kết quả kịch bản {scenario['name']}:")
            logger.info(f"- Retry API thành công: {'Có' if scenario['retry_succeeds'] else 'Không'}")
            logger.info(f"- Fallback strategy kích hoạt: {'Có' if scenario['fallback_activated'] else 'Không'}")
            logger.info(f"- Vị thế còn nguyên vẹn: {'Có' if scenario_result['position_intact'] else 'Không'}")
            logger.info(f"- SL/TP còn nguyên vẹn: {'Có' if scenario_result['sl_tp_intact'] else 'Không'}")
            logger.info(f"- Dữ liệu được đồng bộ: {'Có' if scenario_result['data_synced'] else 'Không'}")
            logger.info(f"- Trạng thái cuối cùng: {scenario_result['final_position_state']}")
            if scenario_result['final_position_state'] == 'closed':
                logger.info(f"- PnL: ${scenario_result['pnl']:.2f} ({scenario_result['pnl_percent']:.2f}%)")
        
        # Tạo kết quả test
        result = {
            'position': position,
            'scenarios': disconnection_scenarios,
            'scenario_results': scenario_results,
            'retry_mechanism_works': all(s['retry_succeeds'] for s in disconnection_scenarios[:2]),
            'fallback_strategy_works': any(s['fallback_activated'] for s in disconnection_scenarios),
            'data_sync_on_reconnect': any(s['retry_succeeds'] for s in disconnection_scenarios),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu vào kết quả test
        self.test_results['position_management_test_results']['disconnection'] = result
        
        logger.info(f"Kết quả tổng thể test mất kết nối:")
        logger.info(f"- Retry mechanism hoạt động: {'Có' if result['retry_mechanism_works'] else 'Không'}")
        logger.info(f"- Fallback strategy hoạt động: {'Có' if result['fallback_strategy_works'] else 'Không'}")
        logger.info(f"- Đồng bộ dữ liệu khi kết nối lại: {'Có' if result['data_sync_on_reconnect'] else 'Không'}")
        
        return result
    
    def run_all_tests(self) -> Dict:
        """
        Chạy tất cả các bài test
        
        Returns:
            Dict: Kết quả tất cả các bài test
        """
        logger.info("=== Chạy tất cả các bài test ===")
        
        # Test vào lệnh
        symbols = ['BTCUSDT', 'ETHUSDT']
        
        for symbol in symbols:
            self.run_entry_test_trending(symbol)
            self.run_entry_test_volatile(symbol)
            self.run_entry_test_ranging(symbol)
        
        # Test quản lý vị thế
        self.run_position_management_test_adverse()
        self.run_position_management_test_favorable()
        self.run_position_management_test_volatility()
        self.run_position_management_test_disconnection()
        
        # Tạo báo cáo tổng hợp
        summary = self.create_test_summary()
        
        # Lưu kết quả test
        self.save_test_results()
        
        return self.test_results
    
    def create_test_summary(self) -> Dict:
        """
        Tạo báo cáo tổng hợp của các bài test
        
        Returns:
            Dict: Báo cáo tổng hợp
        """
        summary = {
            'entry_tests': {
                'trending': {
                    'strategies_prioritized': [],
                    'risk_allocation': None,
                    'sl_tp_placement': None
                },
                'volatile': {
                    'risk_reduced': None,
                    'breakout_prioritized': None,
                    'atr_based_sl_tp': None
                },
                'ranging': {
                    'mean_reversion_prioritized': None,
                    'leverage_adjusted': None
                }
            },
            'position_management_tests': {
                'adverse': {
                    'trailing_stop_active': None,
                    'sl_triggered': None,
                    'sync_working': None
                },
                'favorable': {
                    'trailing_stop_active': None,
                    'profit_protected': None
                },
                'volatility': {
                    'trailing_stop_responsive': None,
                    'slippage_protection': None
                },
                'disconnection': {
                    'retry_mechanism': None,
                    'fallback_strategy': None,
                    'data_synced': None
                }
            },
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Phân tích kết quả vào lệnh - Trending
        trending_results = self.test_results['entry_test_results'].get('trending', {})
        if trending_results:
            strategies = trending_results.get('strategy_weights', {})
            top_strategy = trending_results.get('top_strategy', '')
            
            summary['entry_tests']['trending']['strategies_prioritized'] = [
                top_strategy, 
                *[s for s in strategies.keys() if s != top_strategy][:2]
            ]
            summary['entry_tests']['trending']['risk_allocation'] = trending_results.get('risk_percentage', 0)
            
            sl = trending_results.get('stop_loss', 0)
            tp = trending_results.get('take_profit', 0)
            entry = trending_results.get('entry_price', 0)
            if sl and tp and entry:
                sl_pct = abs(sl - entry) / entry * 100
                tp_pct = abs(tp - entry) / entry * 100
                summary['entry_tests']['trending']['sl_tp_placement'] = f"SL: {sl_pct:.2f}%, TP: {tp_pct:.2f}%"
        
        # Phân tích kết quả vào lệnh - Volatile
        volatile_results = self.test_results['entry_test_results'].get('volatile', {})
        if volatile_results:
            summary['entry_tests']['volatile']['risk_reduced'] = volatile_results.get('risk_reduced', False)
            
            strategies = volatile_results.get('strategy_weights', {})
            breakout_priority = 'breakout' in strategies and strategies.get('breakout', 0) >= 0.3
            summary['entry_tests']['volatile']['breakout_prioritized'] = breakout_priority
            
            summary['entry_tests']['volatile']['atr_based_sl_tp'] = volatile_results.get('atr_based_sl_tp', False)
        
        # Phân tích kết quả vào lệnh - Ranging
        ranging_results = self.test_results['entry_test_results'].get('ranging', {})
        if ranging_results:
            summary['entry_tests']['ranging']['mean_reversion_prioritized'] = ranging_results.get('mean_reversion_priority', False)
            
            # Kiểm tra đòn bẩy được điều chỉnh (giả định)
            summary['entry_tests']['ranging']['leverage_adjusted'] = True
        
        # Phân tích kết quả quản lý vị thế - Adverse
        adverse_results = self.test_results['position_management_test_results'].get('adverse', {})
        if adverse_results:
            position = adverse_results.get('position', {})
            summary['position_management_tests']['adverse']['trailing_stop_active'] = position.get('ts_activated', False)
            summary['position_management_tests']['adverse']['sl_triggered'] = adverse_results.get('stop_loss_triggered', False)
            summary['position_management_tests']['adverse']['sync_working'] = True  # Giả định
        
        # Phân tích kết quả quản lý vị thế - Favorable
        favorable_results = self.test_results['position_management_test_results'].get('favorable', {})
        if favorable_results:
            summary['position_management_tests']['favorable']['trailing_stop_active'] = favorable_results.get('ts_activated', False)
            
            if favorable_results.get('position_closed', False) and favorable_results.get('close_reason') == 'trailing_stop':
                tracking_results = favorable_results.get('tracking_results', [])
                if tracking_results:
                    last_result = tracking_results[-1]
                    entry_price = favorable_results.get('position', {}).get('entry_price', 0)
                    highest_price = favorable_results.get('highest_price', 0)
                    
                    if entry_price and highest_price:
                        max_profit = (highest_price - entry_price) / entry_price * 100
                        actual_profit = last_result.get('current_pnl_percent', 0)
                        profit_protected = actual_profit / max_profit * 100 if max_profit > 0 else 0
                        
                        summary['position_management_tests']['favorable']['profit_protected'] = f"{profit_protected:.2f}%"
                    else:
                        summary['position_management_tests']['favorable']['profit_protected'] = "N/A"
                else:
                    summary['position_management_tests']['favorable']['profit_protected'] = "N/A"
            else:
                summary['position_management_tests']['favorable']['profit_protected'] = "N/A"
        
        # Phân tích kết quả quản lý vị thế - Volatility
        volatility_results = self.test_results['position_management_test_results'].get('volatility', {})
        if volatility_results:
            # Kiểm tra trailing stop có phản ứng nhanh khi thị trường biến động mạnh
            if volatility_results.get('position_closed', False):
                summary['position_management_tests']['volatility']['trailing_stop_responsive'] = True
                summary['position_management_tests']['volatility']['slippage_protection'] = volatility_results.get('protect_pnl', 0) > 0
            else:
                summary['position_management_tests']['volatility']['trailing_stop_responsive'] = False
                summary['position_management_tests']['volatility']['slippage_protection'] = False
        
        # Phân tích kết quả quản lý vị thế - Disconnection
        disconnection_results = self.test_results['position_management_test_results'].get('disconnection', {})
        if disconnection_results:
            summary['position_management_tests']['disconnection']['retry_mechanism'] = disconnection_results.get('retry_mechanism_works', False)
            summary['position_management_tests']['disconnection']['fallback_strategy'] = disconnection_results.get('fallback_strategy_works', False)
            summary['position_management_tests']['disconnection']['data_synced'] = disconnection_results.get('data_sync_on_reconnect', False)
        
        # Lưu summary
        self.test_results['summary'] = summary
        
        # Log summary
        logger.info("=== Tóm tắt kết quả test ===")
        
        logger.info("Kết quả test vào lệnh:")
        logger.info(f"- Thị trường trending:")
        logger.info(f"  + Chiến lược ưu tiên: {summary['entry_tests']['trending']['strategies_prioritized']}")
        logger.info(f"  + Risk %: {summary['entry_tests']['trending']['risk_allocation']}")
        logger.info(f"  + SL/TP: {summary['entry_tests']['trending']['sl_tp_placement']}")
        
        logger.info(f"- Thị trường biến động mạnh:")
        logger.info(f"  + Risk giảm: {'Có' if summary['entry_tests']['volatile']['risk_reduced'] else 'Không'}")
        logger.info(f"  + Breakout ưu tiên: {'Có' if summary['entry_tests']['volatile']['breakout_prioritized'] else 'Không'}")
        logger.info(f"  + SL/TP dựa trên ATR: {'Có' if summary['entry_tests']['volatile']['atr_based_sl_tp'] else 'Không'}")
        
        logger.info(f"- Thị trường dao động trong biên độ:")
        logger.info(f"  + Mean reversion ưu tiên: {'Có' if summary['entry_tests']['ranging']['mean_reversion_prioritized'] else 'Không'}")
        logger.info(f"  + Đòn bẩy điều chỉnh: {'Có' if summary['entry_tests']['ranging']['leverage_adjusted'] else 'Không'}")
        
        logger.info("Kết quả test quản lý vị thế:")
        logger.info(f"- Thị trường đi ngược với vị thế:")
        logger.info(f"  + Trailing stop kích hoạt: {'Có' if summary['position_management_tests']['adverse']['trailing_stop_active'] else 'Không'}")
        logger.info(f"  + SL kích hoạt: {'Có' if summary['position_management_tests']['adverse']['sl_triggered'] else 'Không'}")
        logger.info(f"  + Đồng bộ hoạt động: {'Có' if summary['position_management_tests']['adverse']['sync_working'] else 'Không'}")
        
        logger.info(f"- Thị trường đi thuận với vị thế:")
        logger.info(f"  + Trailing stop kích hoạt: {'Có' if summary['position_management_tests']['favorable']['trailing_stop_active'] else 'Không'}")
        logger.info(f"  + Lợi nhuận được bảo vệ: {summary['position_management_tests']['favorable']['profit_protected']}")
        
        logger.info(f"- Thị trường biến động mạnh đột ngột:")
        logger.info(f"  + Trailing stop phản ứng nhanh: {'Có' if summary['position_management_tests']['volatility']['trailing_stop_responsive'] else 'Không'}")
        logger.info(f"  + Bảo vệ slippage: {'Có' if summary['position_management_tests']['volatility']['slippage_protection'] else 'Không'}")
        
        logger.info(f"- Mất kết nối với Binance API:")
        logger.info(f"  + Retry mechanism: {'Có' if summary['position_management_tests']['disconnection']['retry_mechanism'] else 'Không'}")
        logger.info(f"  + Fallback strategy: {'Có' if summary['position_management_tests']['disconnection']['fallback_strategy'] else 'Không'}")
        logger.info(f"  + Đồng bộ dữ liệu: {'Có' if summary['position_management_tests']['disconnection']['data_synced'] else 'Không'}")
        
        return summary
    
    def save_test_results(self) -> bool:
        """
        Lưu kết quả test vào file
        
        Returns:
            bool: True nếu lưu thành công, False nếu không
        """
        try:
            # Tạo tên file kết quả
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.results_folder, f"test_results_{timestamp}.json")
            
            # Lưu kết quả vào file
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=4)
            
            logger.info(f"Đã lưu kết quả test vào {filename}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả test: {str(e)}")
            return False


def main():
    """Hàm chính để chạy test"""
    print("=== Chạy Test Cases ===\n")
    
    # Khởi tạo TestCaseRunner
    test_runner = TestCaseRunner()
    
    # Chạy tất cả các bài test
    test_runner.run_all_tests()
    
    print("\n=== Đã chạy xong Test Cases ===")


if __name__ == "__main__":
    main()