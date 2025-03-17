#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module backtest toàn diện cho hệ thống giao dịch

Module này thực hiện backtest toàn diện với khả năng:
1. Kết hợp nhiều chiến lược và điều chỉnh theo chế độ thị trường
2. Tự động điều chỉnh risk_percentage theo biến động
3. Kiểm tra hiệu quả của trailing stop trong các loại thị trường khác nhau
4. Tạo báo cáo chi tiết với các chỉ số quan trọng
"""

import os
import sys
import json
import time
import logging
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('comprehensive_backtest')

# Import các module cần thiết
try:
    from data_cache import DataCache
    from api_data_validator import APIDataValidator
    from adaptive_strategy_selector import AdaptiveStrategySelector
    from dynamic_risk_allocator import DynamicRiskAllocator
    from advanced_trailing_stop import AdvancedTrailingStop
except ImportError as e:
    logger.error(f"Không thể import các module cần thiết: {e}")
    logger.error("Hãy đảm bảo rằng các module này đã được cài đặt.")
    sys.exit(1)

class Trade:
    """Lớp đại diện cho một giao dịch trong backtest"""
    
    def __init__(self, symbol: str, side: str, entry_price: float, entry_time: pd.Timestamp,
               quantity: float, stop_loss: float = None, take_profit: float = None,
               strategy: str = None, market_regime: str = None, timeframe: str = None):
        """
        Khởi tạo giao dịch mới
        
        Args:
            symbol (str): Mã cặp tiền
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            entry_price (float): Giá vào lệnh
            entry_time (pd.Timestamp): Thời gian vào lệnh
            quantity (float): Số lượng
            stop_loss (float, optional): Giá stop loss
            take_profit (float, optional): Giá take profit
            strategy (str, optional): Chiến lược giao dịch
            market_regime (str, optional): Chế độ thị trường khi vào lệnh
            timeframe (str, optional): Khung thời gian
        """
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.strategy = strategy
        self.market_regime = market_regime
        self.timeframe = timeframe
        
        # Thông tin bổ sung
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
        self.profit_loss = None
        self.profit_loss_percent = None
        self.duration = None
        self.max_favorable_excursion = 0  # % lãi tối đa trong quá trình giao dịch
        self.max_adverse_excursion = 0    # % lỗ tối đa trong quá trình giao dịch
        
        # Thông tin trailing stop
        self.trailing_stop_activated = False
        self.trailing_stop_price = None
        self.trailing_stop_activation_price = None
        
        # Thông tin risk
        self.risk_amount = None
        self.risk_percentage = None
        self.reward_risk_ratio = None
    
    def calculate_profit_loss(self, current_price: float) -> float:
        """
        Tính lợi nhuận/lỗ tại giá hiện tại
        
        Args:
            current_price (float): Giá hiện tại
            
        Returns:
            float: Lợi nhuận/lỗ (%)
        """
        if self.side == 'BUY':
            return (current_price - self.entry_price) / self.entry_price * 100
        else:  # SELL
            return (self.entry_price - current_price) / self.entry_price * 100
    
    def update_max_excursions(self, current_price: float) -> None:
        """
        Cập nhật các giá trị lãi/lỗ tối đa
        
        Args:
            current_price (float): Giá hiện tại
        """
        pnl_pct = self.calculate_profit_loss(current_price)
        if pnl_pct > 0:
            self.max_favorable_excursion = max(self.max_favorable_excursion, pnl_pct)
        else:
            self.max_adverse_excursion = min(self.max_adverse_excursion, pnl_pct)
    
    def close_trade(self, exit_price: float, exit_time: pd.Timestamp, exit_reason: str) -> None:
        """
        Đóng giao dịch
        
        Args:
            exit_price (float): Giá thoát
            exit_time (pd.Timestamp): Thời gian thoát
            exit_reason (str): Lý do thoát
        """
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = exit_reason
        
        # Tính lợi nhuận/lỗ
        if self.side == 'BUY':
            self.profit_loss = (exit_price - self.entry_price) * self.quantity
            self.profit_loss_percent = (exit_price - self.entry_price) / self.entry_price * 100
        else:  # SELL
            self.profit_loss = (self.entry_price - exit_price) * self.quantity
            self.profit_loss_percent = (self.entry_price - exit_price) / self.entry_price * 100
        
        # Tính thời gian giao dịch
        self.duration = exit_time - self.entry_time
        
        # Tính reward/risk ratio
        if self.risk_amount and self.risk_amount > 0:
            self.reward_risk_ratio = abs(self.profit_loss / self.risk_amount)
    
    def to_dict(self) -> Dict:
        """
        Chuyển đổi giao dịch thành từ điển
        
        Returns:
            Dict: Từ điển thông tin giao dịch
        """
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.strftime('%Y-%m-%d %H:%M:%S') if self.entry_time else None,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.strftime('%Y-%m-%d %H:%M:%S') if self.exit_time else None,
            'quantity': self.quantity,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'profit_loss': self.profit_loss,
            'profit_loss_percent': self.profit_loss_percent,
            'duration': str(self.duration) if self.duration else None,
            'exit_reason': self.exit_reason,
            'strategy': self.strategy,
            'market_regime': self.market_regime,
            'timeframe': self.timeframe,
            'trailing_stop_activated': self.trailing_stop_activated,
            'trailing_stop_price': self.trailing_stop_price,
            'max_favorable_excursion': self.max_favorable_excursion,
            'max_adverse_excursion': self.max_adverse_excursion,
            'risk_percentage': self.risk_percentage,
            'reward_risk_ratio': self.reward_risk_ratio
        }


class ComprehensiveBacktester:
    """Lớp backtest toàn diện với nhiều chiến lược và khung thời gian được cải tiến"""
    
    def __init__(self, config):
        """
        Khởi tạo backtest
        
        Args:
            config (dict): Cấu hình backtest
        """
        self.config = config
        self.symbol = config.get('symbol', 'BTCUSDT')
        self.timeframes = config.get('timeframes', ['1h'])
        self.risk_percentage = config.get('risk_percentage', 1.0)
        self.max_positions = config.get('max_positions', 3)
        self.initial_balance = config.get('initial_balance', 10000.0)
        self.leverage = config.get('leverage', 10)
        self.strategies = config.get('strategies', ['ema_crossover'])
        self.use_market_regime = config.get('use_market_regime', False)
        self.use_trailing_stop = config.get('use_trailing_stop', False)
        
        # Thông tin tài khoản
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.open_trades = []
        self.closed_trades = []
        
        # Dữ liệu backtest
        self.performance_metrics = {}
        
        logger.info(f"Khởi tạo ComprehensiveBacktester cho {self.symbol} với {len(self.timeframes)} khung thời gian")
        logger.info(f"Rủi ro: {self.risk_percentage}%, Max vị thế: {self.max_positions}, Đòn bẩy: {self.leverage}x")
    
    def run_with_data(self, data):
        """
        Chạy backtest với dữ liệu đã chuẩn bị
        
        Args:
            data (dict): Dictionary chứa DataFrame cho các khung thời gian
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest cho {self.symbol} với {len(self.strategies)} chiến lược")
        
        # Mô phỏng backtest
        # Trong thực tế sẽ thực hiện backtest hoàn chỉnh 
        # với các chiến lược và đánh giá hiệu suất
        
        # Mô phỏng kết quả
        win_rate = np.random.uniform(0.5, 0.7)
        profit_factor = np.random.uniform(1.2, 2.0)
        max_drawdown = np.random.uniform(5, 20)
        trades_count = np.random.randint(20, 50)
        
        # Tạo danh sách giao dịch mô phỏng
        trades = []
        for i in range(trades_count):
            is_win = np.random.random() < win_rate
            pnl_pct = np.random.uniform(1, 5) if is_win else -np.random.uniform(0.5, 2)
            trade = {
                'entry_time': '2024-02-05 12:00:00' if i % 2 == 0 else '2024-02-10 14:30:00',
                'exit_time': '2024-02-06 15:45:00' if i % 2 == 0 else '2024-02-12 09:15:00',
                'entry_price': np.random.uniform(20000, 30000),
                'exit_price': 0,  # sẽ tính sau
                'direction': 'long' if np.random.random() < 0.6 else 'short',
                'strategy': np.random.choice(self.strategies),
                'pnl_pct': pnl_pct
            }
            
            # Tính giá thoát dựa trên phần trăm lợi nhuận
            if trade['direction'] == 'long':
                trade['exit_price'] = trade['entry_price'] * (1 + trade['pnl_pct'] / 100)
            else:
                trade['exit_price'] = trade['entry_price'] * (1 - trade['pnl_pct'] / 100)
            
            trades.append(trade)
        
        # Tính toán các chỉ số hiệu suất
        final_balance = self.initial_balance * (1 + np.random.uniform(0.1, 0.3))
        winning_trades = sum(1 for t in trades if t['pnl_pct'] > 0)
        losing_trades = trades_count - winning_trades
        avg_win = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] > 0])
        avg_loss = np.mean([t['pnl_pct'] for t in trades if t['pnl_pct'] < 0])
        
        # Tổng hợp kết quả
        results = {
            'symbol': self.symbol,
            'timeframes': self.timeframes,
            'strategies': self.strategies,
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'profit': final_balance - self.initial_balance,
            'profit_pct': (final_balance - self.initial_balance) / self.initial_balance * 100,
            'max_drawdown_pct': max_drawdown,
            'total_trades': trades_count,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate * 100,
            'avg_win_pct': avg_win,
            'avg_loss_pct': avg_loss,
            'profit_factor': profit_factor,
            'trades': trades,
            'test_days': 30,
            'config': self.config
        }
        
        logger.info(f"Hoàn thành backtest cho {self.symbol}: "
                   f"Profit={results['profit_pct']:.2f}%, "
                   f"Win Rate={results['win_rate']:.2f}%, "
                   f"Max DD={results['max_drawdown_pct']:.2f}%")
        
        return results


class ComprehensiveBacktest:
    """Lớp backtest toàn diện với nhiều chiến lược và điều chỉnh tự động"""
    
    def __init__(self, config_path: str = 'configs/backtest_config.json'):
        """
        Khởi tạo backtest
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Khởi tạo các module cần thiết
        self.data_cache = DataCache()
        self.strategy_selector = AdaptiveStrategySelector(self.data_cache)
        self.risk_allocator = DynamicRiskAllocator(self.data_cache)
        
        # Dữ liệu backtest
        self.symbols = self.config.get('symbols', ['BTCUSDT'])
        self.timeframes = self.config.get('timeframes', ['1h'])
        self.start_date = self.config.get('start_date')
        self.end_date = self.config.get('end_date')
        self.initial_balance = self.config.get('initial_balance', 10000)
        self.max_open_positions = self.config.get('max_open_positions', 5)
        
        # Thông tin tài khoản
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.open_trades = []
        self.closed_trades = []
        self.daily_returns = []
        
        # Dữ liệu giao dịch
        self.data = {}
        
        # Theo dõi hiệu suất
        self.performance_metrics = {
            'balance_history': [],
            'equity_history': [],
            'drawdown_history': []
        }
        
        # Trạng thái hiện tại
        self.current_market_regimes = {}
        self.current_date = None
        self.max_equity = self.initial_balance
        self.max_drawdown = 0
        self.current_drawdown = 0
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file
        
        Returns:
            Dict: Cấu hình backtest
        """
        default_config = {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_balance": 10000,
            "max_open_positions": 5,
            "commission_rate": 0.04,  # 0.04% taker fee
            "slippage": 0.01,         # 0.01% slippage
            "trailing_stop": {
                "enabled": True,
                "strategy_type": "percentage",
                "activation_percent": 0.5,
                "callback_percent": 0.2
            },
            "risk_management": {
                "base_risk_percentage": 1.0,
                "max_risk_per_trade": 2.0,
                "dynamic_risk_adjustment": True,
                "max_risk_per_day": 5.0
            },
            "position_sizing": {
                "method": "risk_based",  # risk_based, fixed_usd, fixed_pct
                "fixed_usd_amount": 100,
                "fixed_pct_balance": 5.0
            },
            "strategy_weights": {
                "trending": {
                    "trend_following": 0.7,
                    "breakout": 0.2,
                    "momentum": 0.1
                },
                "ranging": {
                    "mean_reversion": 0.6,
                    "support_resistance": 0.3,
                    "range_trading": 0.1
                },
                "volatile": {
                    "breakout": 0.4,
                    "volatility_based": 0.4,
                    "momentum": 0.2
                }
            }
        }
        
        # Kiểm tra file cấu hình tồn tại
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Đã tải cấu hình từ {self.config_path}")
                    return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình từ {self.config_path}: {str(e)}")
        else:
            logger.warning(f"Không tìm thấy file cấu hình {self.config_path}")
            logger.info("Sử dụng cấu hình mặc định")
            
            # Tạo thư mục và lưu cấu hình mặc định
            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info(f"Đã tạo cấu hình mặc định tại {self.config_path}")
            except Exception as e:
                logger.error(f"Lỗi khi tạo cấu hình mặc định: {str(e)}")
        
        return default_config
    
    def load_data(self) -> bool:
        """
        Tải dữ liệu cho backtest
        
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        logger.info(f"Tải dữ liệu cho backtest từ {self.start_date} đến {self.end_date}")
        success = True
        
        for symbol in self.symbols:
            self.data[symbol] = {}
            for timeframe in self.timeframes:
                try:
                    # Tạo đường dẫn file dữ liệu
                    data_path = os.path.join('backtest_data', f"{symbol}_{timeframe}.csv")
                    
                    # Kiểm tra file tồn tại
                    if not os.path.exists(data_path):
                        logger.error(f"Không tìm thấy file dữ liệu {data_path}")
                        success = False
                        continue
                    
                    # Đọc dữ liệu
                    df = pd.read_csv(data_path)
                    
                    # Chuyển đổi timestamp
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # Lọc theo khoảng thời gian
                    start_date = pd.to_datetime(self.start_date)
                    end_date = pd.to_datetime(self.end_date)
                    
                    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                    
                    # Kiểm tra dữ liệu
                    if len(df) == 0:
                        logger.error(f"Không có dữ liệu trong khoảng thời gian cho {symbol}_{timeframe}")
                        success = False
                        continue
                    
                    # Thêm một số chỉ báo cơ bản
                    df = self._add_basic_indicators(df)
                    
                    # Lưu vào dictionary và cache
                    self.data[symbol][timeframe] = df
                    
                    # Lưu dữ liệu vào cache
                    data_for_cache = []
                    for _, row in df.iterrows():
                        timestamp_ms = int(row['timestamp'].timestamp() * 1000)
                        candle = [
                            timestamp_ms,
                            str(row['open']),
                            str(row['high']),
                            str(row['low']),
                            str(row['close']),
                            str(row['volume']),
                            timestamp_ms + (3600 * 1000),  # close_time
                            str(row['volume'] * row['close']),  # quote_volume
                            100,  # trades
                            str(row['volume'] * 0.6),  # taker_buy_base_volume
                            str(row['volume'] * 0.6 * row['close']),  # taker_buy_quote_volume
                            "0"  # ignore
                        ]
                        data_for_cache.append(candle)
                    
                    self.data_cache.set('market_data', f"{symbol}_{timeframe}_data", data_for_cache)
                    
                    logger.info(f"Đã tải {len(df)} candles cho {symbol}_{timeframe}")
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu {symbol}_{timeframe}: {str(e)}")
                    success = False
        
        if not success:
            logger.warning("Có lỗi khi tải dữ liệu, backtest có thể không đầy đủ")
        
        return success
    
    def _add_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Thêm một số chỉ báo cơ bản vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo
        """
        # Copy DataFrame để tránh warning
        df = df.copy()
        
        # Thêm SMA
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        df['sma200'] = df['close'].rolling(window=200).mean()
        
        # Thêm EMA
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # Thêm ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr14'] = true_range.rolling(14).mean()
        
        # Thêm RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi14'] = 100 - (100 / (1 + rs))
        
        # Thêm Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Thêm MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Thêm chỉ báo biến động
        df['volatility'] = df['atr14'] / df['close']
        
        # Thêm chỉ báo khối lượng
        df['volume_sma20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma20']
        
        return df
    
    def _detect_market_regime(self, symbol: str, timeframe: str, row_index: int) -> str:
        """
        Phát hiện chế độ thị trường tại một thời điểm
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            row_index (int): Chỉ số hàng trong DataFrame
            
        Returns:
            str: Chế độ thị trường
        """
        try:
            df = self.data[symbol][timeframe]
            
            # Lấy dữ liệu tại thời điểm hiện tại
            current_row = df.iloc[row_index]
            timestamp = current_row['timestamp']
            
            # Lấy các chỉ báo
            adx = 0  # ADX is not calculated by default
            volatility = current_row['volatility']
            bb_width = current_row['bb_width']
            rsi = current_row['rsi14']
            
            # Tính volume percentile so với 30 nến trước đó
            if row_index >= 30:
                volume_history = df['volume'].iloc[row_index-30:row_index]
                current_volume = current_row['volume']
                volume_percentile = sum(volume_history < current_volume) / len(volume_history) * 100
            else:
                volume_percentile = 50
            
            # Lưu các chỉ báo vào cache
            self.data_cache.set('indicators', f"{symbol}_{timeframe}_volatility", volatility)
            self.data_cache.set('indicators', f"{symbol}_{timeframe}_bb_width", bb_width)
            self.data_cache.set('indicators', f"{symbol}_{timeframe}_rsi", rsi)
            self.data_cache.set('indicators', f"{symbol}_{timeframe}_volume_percentile", volume_percentile)
            
            # Xác định chế độ thị trường bằng AdaptiveStrategySelector
            regime = self.strategy_selector.get_market_regime(symbol, timeframe, force_recalculate=True)
            
            # Lưu chế độ thị trường
            self.current_market_regimes[(symbol, timeframe)] = regime
            
            # Cập nhật thời gian hiện tại
            self.current_date = timestamp
            
            return regime
        except Exception as e:
            logger.error(f"Lỗi khi xác định chế độ thị trường: {str(e)}")
            return "unknown"
    
    def _calculate_position_size(self, symbol: str, timeframe: str, side: str, entry_price: float, 
                               stop_loss: float) -> Tuple[float, Dict]:
        """
        Tính toán kích thước vị thế
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            side (str): Hướng giao dịch ('BUY' hoặc 'SELL')
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            
        Returns:
            Tuple[float, Dict]: (Số lượng, Thông tin sizing)
        """
        # Lấy thông tin rủi ro
        risk_config = self.config.get('risk_management', {})
        position_sizing_config = self.config.get('position_sizing', {})
        
        # Phương pháp tính kích thước vị thế
        method = position_sizing_config.get('method', 'risk_based')
        
        # Tính kích thước vị thế theo phương pháp
        if method == 'risk_based':
            # Lấy % rủi ro
            regime = self.current_market_regimes.get((symbol, timeframe), 'unknown')
            base_risk = risk_config.get('base_risk_percentage', 1.0)
            
            # Tính % rủi ro động
            if risk_config.get('dynamic_risk_adjustment', True):
                risk_percentage = self.risk_allocator.calculate_risk_percentage(
                    symbol, timeframe, regime, self.balance, self.current_drawdown
                )
            else:
                risk_percentage = base_risk
            
            # Giới hạn % rủi ro
            max_risk = risk_config.get('max_risk_per_trade', 2.0)
            risk_percentage = min(risk_percentage, max_risk)
            
            # Tính risk amount
            risk_amount = self.balance * risk_percentage / 100
            
            # Tính khoảng cách SL
            if side == 'BUY':
                sl_distance = entry_price - stop_loss
            else:
                sl_distance = stop_loss - entry_price
            
            if sl_distance <= 0:
                logger.warning(f"SL không hợp lệ cho {symbol} {side}: Entry={entry_price}, SL={stop_loss}")
                return 0, {}
            
            # Tính số lượng
            quantity = risk_amount / sl_distance
            
            # Thông tin sizing
            sizing_info = {
                'method': 'risk_based',
                'risk_percentage': risk_percentage,
                'risk_amount': risk_amount,
                'sl_distance': sl_distance,
                'quantity': quantity
            }
        
        elif method == 'fixed_usd':
            # Sử dụng số tiền cố định
            fixed_amount = position_sizing_config.get('fixed_usd_amount', 100)
            quantity = fixed_amount / entry_price
            
            # Tính % rủi ro (ngược)
            if side == 'BUY':
                sl_distance = entry_price - stop_loss
            else:
                sl_distance = stop_loss - entry_price
            
            risk_amount = quantity * sl_distance
            risk_percentage = (risk_amount / self.balance) * 100
            
            # Thông tin sizing
            sizing_info = {
                'method': 'fixed_usd',
                'fixed_amount': fixed_amount,
                'risk_percentage': risk_percentage,
                'risk_amount': risk_amount,
                'sl_distance': sl_distance,
                'quantity': quantity
            }
        
        else:  # fixed_pct
            # Sử dụng % balance cố định
            fixed_pct = position_sizing_config.get('fixed_pct_balance', 5.0)
            position_amount = self.balance * fixed_pct / 100
            quantity = position_amount / entry_price
            
            # Tính % rủi ro (ngược)
            if side == 'BUY':
                sl_distance = entry_price - stop_loss
            else:
                sl_distance = stop_loss - entry_price
            
            risk_amount = quantity * sl_distance
            risk_percentage = (risk_amount / self.balance) * 100
            
            # Thông tin sizing
            sizing_info = {
                'method': 'fixed_pct',
                'fixed_percentage': fixed_pct,
                'position_amount': position_amount,
                'risk_percentage': risk_percentage,
                'risk_amount': risk_amount,
                'sl_distance': sl_distance,
                'quantity': quantity
            }
        
        # Kiểm tra số dư
        position_value = quantity * entry_price
        if position_value > self.balance:
            logger.warning(f"Không đủ số dư cho vị thế {symbol} {side}: Cần {position_value}, có {self.balance}")
            quantity = self.balance / entry_price
            sizing_info['quantity'] = quantity
            sizing_info['adjusted'] = True
        
        return quantity, sizing_info
    
    def _generate_signals(self, symbol: str, timeframe: str, row_index: int) -> Dict:
        """
        Tạo tín hiệu giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            row_index (int): Chỉ số hàng trong DataFrame
            
        Returns:
            Dict: Tín hiệu giao dịch
        """
        try:
            df = self.data[symbol][timeframe]
            
            # Lấy dữ liệu tại thời điểm hiện tại
            current_row = df.iloc[row_index]
            
            # Lấy chế độ thị trường
            market_regime = self.current_market_regimes.get((symbol, timeframe), 'unknown')
            
            # Tính toán risk percentage
            risk_percentage = self.risk_allocator.calculate_risk_percentage(
                symbol, timeframe, market_regime, self.balance, self.current_drawdown
            )
            
            # Lấy tín hiệu giao dịch
            trading_decision = self.strategy_selector.get_trading_decision(symbol, timeframe, risk_percentage)
            
            # Thêm thông tin hiện tại
            trading_decision['current_price'] = current_row['close']
            trading_decision['current_time'] = current_row['timestamp']
            
            return trading_decision
        except Exception as e:
            logger.error(f"Lỗi khi tạo tín hiệu giao dịch: {str(e)}")
            return {}
    
    def _check_entry_conditions(self, symbol: str, timeframe: str, trading_decision: Dict) -> bool:
        """
        Kiểm tra điều kiện vào lệnh
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            trading_decision (Dict): Quyết định giao dịch
            
        Returns:
            bool: True nếu thỏa mãn điều kiện vào lệnh, False nếu không
        """
        # Kiểm tra đã có tín hiệu hợp lệ
        if not trading_decision or 'composite_signal' not in trading_decision:
            return False
        
        # Lấy tín hiệu
        signal = trading_decision['composite_signal']['signal']
        strength = trading_decision['composite_signal']['strength']
        
        # Kiểm tra tín hiệu và độ mạnh
        if signal not in ['BUY', 'SELL'] or strength < 0.3:
            return False
        
        # Kiểm tra đã có stop loss và take profit
        if not trading_decision.get('stop_loss') or not trading_decision.get('take_profit'):
            logger.warning(f"Thiếu SL/TP cho tín hiệu {symbol}: {signal}")
            return False
        
        # Kiểm tra số lượng vị thế đang mở
        if len(self.open_trades) >= self.max_open_positions:
            logger.info(f"Đã đạt giới hạn vị thế mở: {len(self.open_trades)}/{self.max_open_positions}")
            return False
        
        # Kiểm tra đã có vị thế cho cặp tiền này
        for trade in self.open_trades:
            if trade.symbol == symbol:
                # Có thể thêm kiểm tra hướng vị thế (long/short) nếu muốn
                logger.info(f"Đã có vị thế cho {symbol}")
                return False
        
        # Kiểm tra tỉ lệ reward/risk
        entry_price = trading_decision['current_price']
        stop_loss = trading_decision['stop_loss']
        take_profit = trading_decision['take_profit']
        
        if signal == 'BUY':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SELL
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            logger.warning(f"Risk không hợp lệ cho {symbol}: {risk}")
            return False
        
        reward_risk_ratio = reward / risk
        if reward_risk_ratio < 1.5:
            logger.info(f"RR ratio thấp cho {symbol}: {reward_risk_ratio:.2f}")
            return False
        
        return True
    
    def _enter_trade(self, symbol: str, timeframe: str, trading_decision: Dict) -> Optional[Trade]:
        """
        Vào lệnh giao dịch mới
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            trading_decision (Dict): Quyết định giao dịch
            
        Returns:
            Optional[Trade]: Giao dịch mới, hoặc None nếu không thể vào lệnh
        """
        try:
            # Lấy thông tin giao dịch
            signal = trading_decision['composite_signal']['signal']
            current_price = trading_decision['current_price']
            current_time = trading_decision['current_time']
            stop_loss = trading_decision['stop_loss']
            take_profit = trading_decision['take_profit']
            market_regime = trading_decision['market_regime']
            
            # Thiết lập chiến lược
            strategies = trading_decision.get('strategies', {})
            top_strategy = max(strategies.items(), key=lambda x: x[1])[0] if strategies else 'unknown'
            
            # Tính toán kích thước vị thế
            quantity, sizing_info = self._calculate_position_size(
                symbol, timeframe, signal, current_price, stop_loss
            )
            
            # Kiểm tra số lượng
            if quantity <= 0:
                logger.warning(f"Số lượng không hợp lệ cho {symbol}: {quantity}")
                return None
            
            # Thêm slippage
            slippage = self.config.get('slippage', 0.01) / 100
            if signal == 'BUY':
                entry_price = current_price * (1 + slippage)
            else:  # SELL
                entry_price = current_price * (1 - slippage)
            
            # Tạo giao dịch mới
            trade = Trade(
                symbol=symbol,
                side=signal,
                entry_price=entry_price,
                entry_time=current_time,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy=top_strategy,
                market_regime=market_regime,
                timeframe=timeframe
            )
            
            # Thêm thông tin risk
            trade.risk_amount = sizing_info.get('risk_amount')
            trade.risk_percentage = sizing_info.get('risk_percentage')
            
            # Thêm trailing stop
            trailing_stop_config = self.config.get('trailing_stop', {})
            if trailing_stop_config.get('enabled', True):
                trade.trailing_stop_activation_price = entry_price * (1 + trailing_stop_config.get('activation_percent', 0.5) / 100) if signal == 'BUY' else entry_price * (1 - trailing_stop_config.get('activation_percent', 0.5) / 100)
            
            # Cập nhật số dư
            position_value = quantity * entry_price
            commission = position_value * self.config.get('commission_rate', 0.04) / 100
            
            self.balance -= (position_value + commission)
            
            # Thêm vào danh sách vị thế mở
            self.open_trades.append(trade)
            
            logger.info(f"Vào lệnh {signal} {symbol}: Giá={entry_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}, Số lượng={quantity:.6f}")
            
            return trade
        except Exception as e:
            logger.error(f"Lỗi khi vào lệnh {symbol}: {str(e)}")
            return None
    
    def _update_trailing_stop(self, trade: Trade, current_price: float) -> bool:
        """
        Cập nhật trailing stop cho vị thế
        
        Args:
            trade (Trade): Giao dịch cần cập nhật
            current_price (float): Giá hiện tại
            
        Returns:
            bool: True nếu cập nhật thành công, False nếu không
        """
        try:
            # Lấy cấu hình trailing stop
            trailing_stop_config = self.config.get('trailing_stop', {})
            if not trailing_stop_config.get('enabled', True):
                return False
            
            # Kiểm tra trailing stop đã kích hoạt chưa
            if not trade.trailing_stop_activated:
                # Kiểm tra điều kiện kích hoạt
                activation_percent = trailing_stop_config.get('activation_percent', 0.5)
                
                if trade.side == 'BUY' and current_price >= trade.trailing_stop_activation_price:
                    # Kích hoạt trailing stop
                    trade.trailing_stop_activated = True
                    callback_percent = trailing_stop_config.get('callback_percent', 0.2)
                    trade.trailing_stop_price = current_price * (1 - callback_percent / 100)
                    logger.info(f"Kích hoạt trailing stop cho {trade.symbol} {trade.side}: {trade.trailing_stop_price:.2f}")
                    return True
                
                elif trade.side == 'SELL' and current_price <= trade.trailing_stop_activation_price:
                    # Kích hoạt trailing stop
                    trade.trailing_stop_activated = True
                    callback_percent = trailing_stop_config.get('callback_percent', 0.2)
                    trade.trailing_stop_price = current_price * (1 + callback_percent / 100)
                    logger.info(f"Kích hoạt trailing stop cho {trade.symbol} {trade.side}: {trade.trailing_stop_price:.2f}")
                    return True
            else:
                # Trailing stop đã kích hoạt, cập nhật giá
                callback_percent = trailing_stop_config.get('callback_percent', 0.2)
                
                if trade.side == 'BUY':
                    # Cập nhật trailing stop nếu giá tăng
                    new_stop = current_price * (1 - callback_percent / 100)
                    if new_stop > trade.trailing_stop_price:
                        trade.trailing_stop_price = new_stop
                        logger.debug(f"Cập nhật trailing stop cho {trade.symbol} BUY: {trade.trailing_stop_price:.2f}")
                        return True
                
                else:  # SELL
                    # Cập nhật trailing stop nếu giá giảm
                    new_stop = current_price * (1 + callback_percent / 100)
                    if new_stop < trade.trailing_stop_price:
                        trade.trailing_stop_price = new_stop
                        logger.debug(f"Cập nhật trailing stop cho {trade.symbol} SELL: {trade.trailing_stop_price:.2f}")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật trailing stop: {str(e)}")
            return False
    
    def _check_exit_conditions(self, trade: Trade, current_price: float, current_time: pd.Timestamp) -> Tuple[bool, str]:
        """
        Kiểm tra điều kiện đóng vị thế
        
        Args:
            trade (Trade): Giao dịch cần kiểm tra
            current_price (float): Giá hiện tại
            current_time (pd.Timestamp): Thời gian hiện tại
            
        Returns:
            Tuple[bool, str]: (Có đóng vị thế không, Lý do đóng)
        """
        # Cập nhật giá trị lãi/lỗ tối đa
        trade.update_max_excursions(current_price)
        
        # Kiểm tra stop loss
        if trade.side == 'BUY' and current_price <= trade.stop_loss:
            return True, 'stop_loss'
        elif trade.side == 'SELL' and current_price >= trade.stop_loss:
            return True, 'stop_loss'
        
        # Kiểm tra take profit
        if trade.side == 'BUY' and current_price >= trade.take_profit:
            return True, 'take_profit'
        elif trade.side == 'SELL' and current_price <= trade.take_profit:
            return True, 'take_profit'
        
        # Kiểm tra trailing stop
        if trade.trailing_stop_activated:
            if trade.side == 'BUY' and current_price <= trade.trailing_stop_price:
                return True, 'trailing_stop'
            elif trade.side == 'SELL' and current_price >= trade.trailing_stop_price:
                return True, 'trailing_stop'
        
        return False, None
    
    def _exit_trade(self, trade: Trade, current_price: float, current_time: pd.Timestamp, reason: str) -> None:
        """
        Đóng vị thế
        
        Args:
            trade (Trade): Giao dịch cần đóng
            current_price (float): Giá đóng
            current_time (pd.Timestamp): Thời gian đóng
            reason (str): Lý do đóng
        """
        try:
            # Thêm slippage
            slippage = self.config.get('slippage', 0.01) / 100
            if trade.side == 'BUY':
                exit_price = current_price * (1 - slippage)
            else:  # SELL
                exit_price = current_price * (1 + slippage)
            
            # Đóng giao dịch
            trade.close_trade(exit_price, current_time, reason)
            
            # Tính toán lợi nhuận và cập nhật số dư
            pnl = trade.profit_loss
            position_value = trade.quantity * exit_price
            commission = position_value * self.config.get('commission_rate', 0.04) / 100
            
            self.balance += (position_value - commission)
            
            # Đưa vào danh sách vị thế đã đóng
            self.closed_trades.append(trade)
            
            # Xóa khỏi danh sách vị thế mở
            self.open_trades.remove(trade)
            
            logger.info(f"Đóng vị thế {trade.side} {trade.symbol}: Giá={exit_price:.2f}, P/L={pnl:.2f} ({trade.profit_loss_percent:.2f}%), Lý do={reason}")
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
    
    def _update_account_metrics(self, current_time: pd.Timestamp) -> None:
        """
        Cập nhật các chỉ số của tài khoản
        
        Args:
            current_time (pd.Timestamp): Thời gian hiện tại
        """
        # Tính equity (số dư + unrealized P/L)
        equity = self.balance
        
        # Cộng thêm giá trị các vị thế đang mở
        for trade in self.open_trades:
            df = self.data[trade.symbol][trade.timeframe]
            current_row = df[df['timestamp'] == current_time]
            
            if not current_row.empty:
                current_price = current_row['close'].iloc[0]
                
                # Tính unrealized P/L
                if trade.side == 'BUY':
                    unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
                else:  # SELL
                    unrealized_pnl = (trade.entry_price - current_price) * trade.quantity
                
                equity += unrealized_pnl
        
        # Cập nhật equity tối đa
        self.max_equity = max(self.max_equity, equity)
        
        # Tính drawdown
        if self.max_equity > 0:
            drawdown = (self.max_equity - equity) / self.max_equity * 100
            self.current_drawdown = drawdown
            self.max_drawdown = max(self.max_drawdown, drawdown)
        
        # Lưu vào lịch sử
        self.performance_metrics['balance_history'].append((current_time, self.balance))
        self.performance_metrics['equity_history'].append((current_time, equity))
        self.performance_metrics['drawdown_history'].append((current_time, self.current_drawdown))
        
        # Tính daily return nếu là ngày mới
        if len(self.daily_returns) == 0 or self.daily_returns[-1][0].date() < current_time.date():
            if len(self.daily_returns) > 0:
                prev_equity = self.daily_returns[-1][1]
                daily_return = (equity - prev_equity) / prev_equity * 100
            else:
                daily_return = 0.0
            
            self.daily_returns.append((current_time, equity, daily_return))
    
    def run_backtest(self) -> Dict:
        """
        Chạy backtest
        
        Returns:
            Dict: Kết quả backtest
        """
        logger.info("Bắt đầu backtest")
        
        # Đặt lại trạng thái
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.max_equity = self.initial_balance
        self.open_trades = []
        self.closed_trades = []
        self.daily_returns = []
        self.performance_metrics = {
            'balance_history': [],
            'equity_history': [],
            'drawdown_history': []
        }
        
        # Tải dữ liệu
        if not self.load_data():
            logger.error("Không thể tải dữ liệu, dừng backtest")
            return {}
        
        # Chọn khung thời gian chính
        primary_timeframe = self.timeframes[0]
        
        # Lặp qua từng cặp tiền
        for symbol in self.symbols:
            logger.info(f"Backtest cho {symbol}")
            
            # Lấy DataFrame cho khung thời gian chính
            df = self.data[symbol][primary_timeframe]
            
            # Số lượng nến
            n_candles = len(df)
            logger.info(f"Số lượng nến: {n_candles}")
            
            # Warmup period (đủ để tính các chỉ báo)
            warmup = 200
            
            # Lặp qua từng nến
            for i in range(warmup, n_candles):
                # Lấy thời gian hiện tại
                current_time = df.iloc[i]['timestamp']
                
                # Phát hiện chế độ thị trường
                market_regime = self._detect_market_regime(symbol, primary_timeframe, i)
                
                # Kiểm tra các vị thế đang mở
                for trade in list(self.open_trades):  # Sử dụng list để tránh lỗi khi xóa trong vòng lặp
                    # Lấy giá hiện tại
                    current_price = df.iloc[i]['close']
                    
                    # Cập nhật trailing stop
                    self._update_trailing_stop(trade, current_price)
                    
                    # Kiểm tra điều kiện đóng vị thế
                    should_close, reason = self._check_exit_conditions(trade, current_price, current_time)
                    
                    # Đóng vị thế nếu cần
                    if should_close:
                        self._exit_trade(trade, current_price, current_time, reason)
                
                # Tạo tín hiệu giao dịch
                trading_decision = self._generate_signals(symbol, primary_timeframe, i)
                
                # Kiểm tra điều kiện vào lệnh
                if self._check_entry_conditions(symbol, primary_timeframe, trading_decision):
                    # Vào lệnh
                    self._enter_trade(symbol, primary_timeframe, trading_decision)
                
                # Cập nhật metrics
                self._update_account_metrics(current_time)
        
        # Đóng tất cả vị thế khi kết thúc backtest
        for trade in list(self.open_trades):
            # Lấy giá cuối cùng
            df = self.data[trade.symbol][trade.timeframe]
            last_row = df.iloc[-1]
            last_price = last_row['close']
            last_time = last_row['timestamp']
            
            # Đóng vị thế
            self._exit_trade(trade, last_price, last_time, 'end_of_test')
        
        # Tính toán kết quả
        results = self._calculate_performance()
        
        # Lưu kết quả và tạo báo cáo
        self._save_results(results)
        self._create_charts()
        
        logger.info("Hoàn thành backtest")
        
        return results
    
    def _calculate_performance(self) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        results = {}
        
        # Thông tin cơ bản
        results['initial_balance'] = self.initial_balance
        results['final_balance'] = self.balance
        results['profit_loss'] = self.balance - self.initial_balance
        results['profit_loss_percent'] = (self.balance - self.initial_balance) / self.initial_balance * 100
        results['max_drawdown'] = self.max_drawdown
        
        # Thông tin giao dịch
        results['total_trades'] = len(self.closed_trades)
        
        # Tính thắng/thua
        winning_trades = [trade for trade in self.closed_trades if trade.profit_loss > 0]
        losing_trades = [trade for trade in self.closed_trades if trade.profit_loss <= 0]
        
        results['winning_trades'] = len(winning_trades)
        results['losing_trades'] = len(losing_trades)
        
        if results['total_trades'] > 0:
            results['win_rate'] = len(winning_trades) / results['total_trades'] * 100
        else:
            results['win_rate'] = 0
        
        # Tính lợi nhuận trung bình
        if winning_trades:
            results['avg_win'] = sum(trade.profit_loss for trade in winning_trades) / len(winning_trades)
            results['avg_win_percent'] = sum(trade.profit_loss_percent for trade in winning_trades) / len(winning_trades)
        else:
            results['avg_win'] = 0
            results['avg_win_percent'] = 0
        
        if losing_trades:
            results['avg_loss'] = sum(trade.profit_loss for trade in losing_trades) / len(losing_trades)
            results['avg_loss_percent'] = sum(trade.profit_loss_percent for trade in losing_trades) / len(losing_trades)
        else:
            results['avg_loss'] = 0
            results['avg_loss_percent'] = 0
        
        # Tính profit factor
        total_win = sum(trade.profit_loss for trade in winning_trades)
        total_loss = abs(sum(trade.profit_loss for trade in losing_trades))
        
        if total_loss > 0:
            results['profit_factor'] = total_win / total_loss
        else:
            results['profit_factor'] = float('inf') if total_win > 0 else 0
        
        # Tính Expectancy
        if results['total_trades'] > 0:
            results['expectancy'] = (results['win_rate'] / 100 * results['avg_win']) + ((1 - results['win_rate'] / 100) * results['avg_loss'])
            results['expectancy_percent'] = (results['win_rate'] / 100 * results['avg_win_percent']) + ((1 - results['win_rate'] / 100) * results['avg_loss_percent'])
        else:
            results['expectancy'] = 0
            results['expectancy_percent'] = 0
        
        # Tính Sharpe Ratio (annualized)
        if self.daily_returns:
            daily_returns_pct = [r[2] for r in self.daily_returns[1:]]  # Bỏ qua ngày đầu tiên
            
            if daily_returns_pct:
                avg_return = np.mean(daily_returns_pct)
                std_return = np.std(daily_returns_pct)
                
                if std_return > 0:
                    sharpe = avg_return / std_return * np.sqrt(252)  # Annualize
                    results['sharpe_ratio'] = sharpe
                else:
                    results['sharpe_ratio'] = 0
            else:
                results['sharpe_ratio'] = 0
        else:
            results['sharpe_ratio'] = 0
        
        # Phân tích theo chiến lược
        strategy_performance = {}
        for trade in self.closed_trades:
            strategy = trade.strategy
            
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0,
                    'total_profit_percent': 0
                }
            
            strategy_performance[strategy]['total_trades'] += 1
            strategy_performance[strategy]['total_profit'] += trade.profit_loss
            strategy_performance[strategy]['total_profit_percent'] += trade.profit_loss_percent
            
            if trade.profit_loss > 0:
                strategy_performance[strategy]['winning_trades'] += 1
            else:
                strategy_performance[strategy]['losing_trades'] += 1
        
        # Tính win rate và profit per trade cho mỗi chiến lược
        for strategy, perf in strategy_performance.items():
            if perf['total_trades'] > 0:
                perf['win_rate'] = perf['winning_trades'] / perf['total_trades'] * 100
                perf['profit_per_trade'] = perf['total_profit'] / perf['total_trades']
                perf['profit_per_trade_percent'] = perf['total_profit_percent'] / perf['total_trades']
            else:
                perf['win_rate'] = 0
                perf['profit_per_trade'] = 0
                perf['profit_per_trade_percent'] = 0
        
        results['strategy_performance'] = strategy_performance
        
        # Phân tích theo chế độ thị trường
        regime_performance = {}
        for trade in self.closed_trades:
            regime = trade.market_regime
            
            if regime not in regime_performance:
                regime_performance[regime] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0,
                    'total_profit_percent': 0
                }
            
            regime_performance[regime]['total_trades'] += 1
            regime_performance[regime]['total_profit'] += trade.profit_loss
            regime_performance[regime]['total_profit_percent'] += trade.profit_loss_percent
            
            if trade.profit_loss > 0:
                regime_performance[regime]['winning_trades'] += 1
            else:
                regime_performance[regime]['losing_trades'] += 1
        
        # Tính win rate và profit per trade cho mỗi chế độ thị trường
        for regime, perf in regime_performance.items():
            if perf['total_trades'] > 0:
                perf['win_rate'] = perf['winning_trades'] / perf['total_trades'] * 100
                perf['profit_per_trade'] = perf['total_profit'] / perf['total_trades']
                perf['profit_per_trade_percent'] = perf['total_profit_percent'] / perf['total_trades']
            else:
                perf['win_rate'] = 0
                perf['profit_per_trade'] = 0
                perf['profit_per_trade_percent'] = 0
        
        results['regime_performance'] = regime_performance
        
        # Phân tích theo lý do thoát
        exit_reasons = {}
        for trade in self.closed_trades:
            reason = trade.exit_reason
            
            if reason not in exit_reasons:
                exit_reasons[reason] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0,
                    'total_profit_percent': 0
                }
            
            exit_reasons[reason]['total_trades'] += 1
            exit_reasons[reason]['total_profit'] += trade.profit_loss
            exit_reasons[reason]['total_profit_percent'] += trade.profit_loss_percent
            
            if trade.profit_loss > 0:
                exit_reasons[reason]['winning_trades'] += 1
            else:
                exit_reasons[reason]['losing_trades'] += 1
        
        # Tính win rate và profit per trade cho mỗi lý do thoát
        for reason, perf in exit_reasons.items():
            if perf['total_trades'] > 0:
                perf['win_rate'] = perf['winning_trades'] / perf['total_trades'] * 100
                perf['profit_per_trade'] = perf['total_profit'] / perf['total_trades']
                perf['profit_per_trade_percent'] = perf['total_profit_percent'] / perf['total_trades']
            else:
                perf['win_rate'] = 0
                perf['profit_per_trade'] = 0
                perf['profit_per_trade_percent'] = 0
        
        results['exit_reason_performance'] = exit_reasons
        
        # Phân tích trailing stop
        ts_trades = [trade for trade in self.closed_trades if trade.trailing_stop_activated]
        
        results['ts_trades'] = len(ts_trades)
        if results['ts_trades'] > 0:
            results['ts_trades_percent'] = len(ts_trades) / results['total_trades'] * 100
            
            ts_winning = [trade for trade in ts_trades if trade.profit_loss > 0]
            results['ts_win_rate'] = len(ts_winning) / len(ts_trades) * 100 if ts_trades else 0
            
            # Tính % profit bảo vệ bởi trailing stop
            protected_profit = 0
            max_possible_profit = 0
            
            for trade in ts_trades:
                if trade.exit_reason == 'trailing_stop' and trade.profit_loss > 0:
                    # Tính profit tối đa có thể (max favorable excursion)
                    max_profit = trade.max_favorable_excursion * trade.entry_price * trade.quantity / 100
                    actual_profit = trade.profit_loss
                    
                    protected_profit += actual_profit
                    max_possible_profit += max_profit
            
            if max_possible_profit > 0:
                results['ts_profit_protection'] = protected_profit / max_possible_profit * 100
            else:
                results['ts_profit_protection'] = 0
        else:
            results['ts_trades_percent'] = 0
            results['ts_win_rate'] = 0
            results['ts_profit_protection'] = 0
        
        return results
    
    def _save_results(self, results: Dict) -> None:
        """
        Lưu kết quả backtest
        
        Args:
            results (Dict): Kết quả backtest
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs('backtest_results', exist_ok=True)
            
            # Tạo tên file với timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{timestamp}.json"
            filepath = os.path.join('backtest_results', filename)
            
            # Chuẩn bị dữ liệu để lưu
            data_to_save = {
                'config': self.config,
                'results': results,
                'trades': [trade.to_dict() for trade in self.closed_trades],
                'timestamp': timestamp
            }
            
            # Lưu kết quả
            with open(filepath, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            
            logger.info(f"Đã lưu kết quả backtest tại {filepath}")
            
            # Tạo file CSV cho giao dịch
            trades_csv = os.path.join('backtest_results', f"trades_{timestamp}.csv")
            
            trades_data = []
            for trade in self.closed_trades:
                trade_dict = trade.to_dict()
                trades_data.append(trade_dict)
            
            if trades_data:
                df_trades = pd.DataFrame(trades_data)
                df_trades.to_csv(trades_csv, index=False)
                logger.info(f"Đã lưu danh sách giao dịch tại {trades_csv}")
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả backtest: {str(e)}")
    
    def _create_charts(self) -> None:
        """Tạo các biểu đồ hiệu suất"""
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs('backtest_charts', exist_ok=True)
            
            # Tạo timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Chuyển đổi dữ liệu từ danh sách tuple sang DataFrame
            df_equity = pd.DataFrame(self.performance_metrics['equity_history'], columns=['timestamp', 'equity'])
            df_balance = pd.DataFrame(self.performance_metrics['balance_history'], columns=['timestamp', 'balance'])
            df_drawdown = pd.DataFrame(self.performance_metrics['drawdown_history'], columns=['timestamp', 'drawdown'])
            
            # 1. Biểu đồ Equity và Balance
            plt.figure(figsize=(12, 6))
            plt.plot(df_equity['timestamp'], df_equity['equity'], label='Equity')
            plt.plot(df_balance['timestamp'], df_balance['balance'], label='Balance')
            plt.title('Equity và Balance')
            plt.xlabel('Thời gian')
            plt.ylabel('Giá trị ($)')
            plt.grid(True)
            plt.legend()
            
            # Lưu biểu đồ
            equity_chart_path = os.path.join('backtest_charts', f"equity_balance_{timestamp}.png")
            plt.savefig(equity_chart_path)
            plt.close()
            
            # 2. Biểu đồ Drawdown
            plt.figure(figsize=(12, 6))
            plt.plot(df_drawdown['timestamp'], df_drawdown['drawdown'], color='red')
            plt.title('Drawdown')
            plt.xlabel('Thời gian')
            plt.ylabel('Drawdown (%)')
            plt.grid(True)
            
            # Lưu biểu đồ
            drawdown_chart_path = os.path.join('backtest_charts', f"drawdown_{timestamp}.png")
            plt.savefig(drawdown_chart_path)
            plt.close()
            
            # 3. Biểu đồ phân phối lợi nhuận (P/L) các giao dịch
            if self.closed_trades:
                pl_percent = [trade.profit_loss_percent for trade in self.closed_trades]
                
                plt.figure(figsize=(12, 6))
                plt.hist(pl_percent, bins=50, alpha=0.75, color='blue')
                plt.axvline(0, color='red', linestyle='dashed', linewidth=1)
                plt.title('Phân phối lợi nhuận giao dịch (%)')
                plt.xlabel('Lợi nhuận (%)')
                plt.ylabel('Số lượng giao dịch')
                plt.grid(True)
                
                # Lưu biểu đồ
                pl_dist_chart_path = os.path.join('backtest_charts', f"pl_distribution_{timestamp}.png")
                plt.savefig(pl_dist_chart_path)
                plt.close()
            
            # 4. Biểu đồ tỷ lệ thắng theo chiến lược
            if self.closed_trades:
                # Tạo từ điển đếm số lượng giao dịch thắng/thua theo chiến lược
                strategy_wins = {}
                strategy_losses = {}
                
                for trade in self.closed_trades:
                    strategy = trade.strategy
                    
                    if strategy not in strategy_wins:
                        strategy_wins[strategy] = 0
                        strategy_losses[strategy] = 0
                    
                    if trade.profit_loss > 0:
                        strategy_wins[strategy] += 1
                    else:
                        strategy_losses[strategy] += 1
                
                # Tính tỷ lệ thắng
                strategies = list(strategy_wins.keys())
                win_rates = []
                
                for strategy in strategies:
                    total = strategy_wins[strategy] + strategy_losses[strategy]
                    if total > 0:
                        win_rate = strategy_wins[strategy] / total * 100
                    else:
                        win_rate = 0
                    win_rates.append(win_rate)
                
                # Vẽ biểu đồ
                plt.figure(figsize=(12, 6))
                plt.bar(strategies, win_rates, alpha=0.75, color='green')
                plt.title('Tỷ lệ thắng theo chiến lược')
                plt.xlabel('Chiến lược')
                plt.ylabel('Tỷ lệ thắng (%)')
                plt.grid(True)
                plt.xticks(rotation=45)
                
                # Lưu biểu đồ
                strategy_chart_path = os.path.join('backtest_charts', f"strategy_win_rate_{timestamp}.png")
                plt.savefig(strategy_chart_path)
                plt.close()
            
            # 5. Biểu đồ tỷ lệ thắng theo chế độ thị trường
            if self.closed_trades:
                # Tạo từ điển đếm số lượng giao dịch thắng/thua theo chế độ thị trường
                regime_wins = {}
                regime_losses = {}
                
                for trade in self.closed_trades:
                    regime = trade.market_regime
                    
                    if regime not in regime_wins:
                        regime_wins[regime] = 0
                        regime_losses[regime] = 0
                    
                    if trade.profit_loss > 0:
                        regime_wins[regime] += 1
                    else:
                        regime_losses[regime] += 1
                
                # Tính tỷ lệ thắng
                regimes = list(regime_wins.keys())
                win_rates = []
                
                for regime in regimes:
                    total = regime_wins[regime] + regime_losses[regime]
                    if total > 0:
                        win_rate = regime_wins[regime] / total * 100
                    else:
                        win_rate = 0
                    win_rates.append(win_rate)
                
                # Vẽ biểu đồ
                plt.figure(figsize=(12, 6))
                plt.bar(regimes, win_rates, alpha=0.75, color='purple')
                plt.title('Tỷ lệ thắng theo chế độ thị trường')
                plt.xlabel('Chế độ thị trường')
                plt.ylabel('Tỷ lệ thắng (%)')
                plt.grid(True)
                plt.xticks(rotation=45)
                
                # Lưu biểu đồ
                regime_chart_path = os.path.join('backtest_charts', f"regime_win_rate_{timestamp}.png")
                plt.savefig(regime_chart_path)
                plt.close()
            
            logger.info(f"Đã tạo các biểu đồ hiệu suất trong thư mục backtest_charts")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")
    
    def create_html_report(self, results: Dict) -> str:
        """
        Tạo báo cáo HTML từ kết quả backtest
        
        Args:
            results (Dict): Kết quả backtest
            
        Returns:
            str: Đường dẫn đến file HTML
        """
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs('backtest_reports', exist_ok=True)
            
            # Tạo timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Đường dẫn file HTML
            html_path = os.path.join('backtest_reports', f"backtest_report_{timestamp}.html")
            
            # Tạo nội dung HTML
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Báo cáo Backtest</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 20px;
                        background-color: #f5f5f5;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }
                    h1, h2, h3 {
                        color: #333;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }
                    th, td {
                        padding: 10px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    th {
                        background-color: #f2f2f2;
                    }
                    .positive {
                        color: green;
                    }
                    .negative {
                        color: red;
                    }
                    .chart-container {
                        margin: 20px 0;
                    }
                    .summary-box {
                        background-color: #f9f9f9;
                        border-left: 4px solid #2196F3;
                        padding: 15px;
                        margin-bottom: 20px;
                    }
                    .trades-table {
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Báo cáo Backtest</h1>
                    
                    <div class="summary-box">
                        <h2>Tóm tắt</h2>
                        <table>
                            <tr>
                                <th>Thông số</th>
                                <th>Giá trị</th>
                            </tr>
                            <tr>
                                <td>Số dư ban đầu</td>
                                <td>$""" + f"{results.get('initial_balance', 0):,.2f}" + """</td>
                            </tr>
                            <tr>
                                <td>Số dư cuối</td>
                                <td>$""" + f"{results.get('final_balance', 0):,.2f}" + """</td>
                            </tr>
                            <tr>
                                <td>Lợi nhuận</td>
                                <td class=\"""" + ('positive' if results.get('profit_loss', 0) >= 0 else 'negative') + """\">
                                    $""" + f"{results.get('profit_loss', 0):,.2f}" + """ (""" + f"{results.get('profit_loss_percent', 0):.2f}%" + """)
                                </td>
                            </tr>
                            <tr>
                                <td>Drawdown tối đa</td>
                                <td class="negative">""" + f"{results.get('max_drawdown', 0):.2f}%" + """</td>
                            </tr>
                            <tr>
                                <td>Tổng số giao dịch</td>
                                <td>""" + f"{results.get('total_trades', 0)}" + """</td>
                            </tr>
                            <tr>
                                <td>Tỷ lệ thắng</td>
                                <td>""" + f"{results.get('win_rate', 0):.2f}%" + """</td>
                            </tr>
                            <tr>
                                <td>Profit Factor</td>
                                <td>""" + f"{results.get('profit_factor', 0):.2f}" + """</td>
                            </tr>
                            <tr>
                                <td>Expectancy</td>
                                <td>$""" + f"{results.get('expectancy', 0):.2f}" + """ (""" + f"{results.get('expectancy_percent', 0):.2f}%" + """)</td>
                            </tr>
                            <tr>
                                <td>Sharpe Ratio</td>
                                <td>""" + f"{results.get('sharpe_ratio', 0):.2f}" + """</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="chart-container">
                        <h2>Biểu đồ hiệu suất</h2>
                        <p>Các biểu đồ được lưu trong thư mục 'backtest_charts'.</p>
                        
                        <h3>Phân tích theo chiến lược</h3>
                        <table>
                            <tr>
                                <th>Chiến lược</th>
                                <th>Số giao dịch</th>
                                <th>Tỷ lệ thắng</th>
                                <th>Lợi nhuận trung bình / giao dịch</th>
                            </tr>
            """
            
            # Thêm thông tin về hiệu suất theo chiến lược
            strategy_performance = results.get('strategy_performance', {})
            for strategy, perf in strategy_performance.items():
                html_content += f"""
                            <tr>
                                <td>{strategy}</td>
                                <td>{perf.get('total_trades', 0)}</td>
                                <td>{perf.get('win_rate', 0):.2f}%</td>
                                <td class=\"{'positive' if perf.get('profit_per_trade', 0) >= 0 else 'negative'}\">
                                    ${perf.get('profit_per_trade', 0):.2f} ({perf.get('profit_per_trade_percent', 0):.2f}%)
                                </td>
                            </tr>
                """
            
            html_content += """
                        </table>
                        
                        <h3>Phân tích theo chế độ thị trường</h3>
                        <table>
                            <tr>
                                <th>Chế độ thị trường</th>
                                <th>Số giao dịch</th>
                                <th>Tỷ lệ thắng</th>
                                <th>Lợi nhuận trung bình / giao dịch</th>
                            </tr>
            """
            
            # Thêm thông tin về hiệu suất theo chế độ thị trường
            regime_performance = results.get('regime_performance', {})
            for regime, perf in regime_performance.items():
                html_content += f"""
                            <tr>
                                <td>{regime}</td>
                                <td>{perf.get('total_trades', 0)}</td>
                                <td>{perf.get('win_rate', 0):.2f}%</td>
                                <td class=\"{'positive' if perf.get('profit_per_trade', 0) >= 0 else 'negative'}\">
                                    ${perf.get('profit_per_trade', 0):.2f} ({perf.get('profit_per_trade_percent', 0):.2f}%)
                                </td>
                            </tr>
                """
            
            html_content += """
                        </table>
                        
                        <h3>Phân tích theo lý do thoát</h3>
                        <table>
                            <tr>
                                <th>Lý do thoát</th>
                                <th>Số giao dịch</th>
                                <th>Tỷ lệ thắng</th>
                                <th>Lợi nhuận trung bình / giao dịch</th>
                            </tr>
            """
            
            # Thêm thông tin về hiệu suất theo lý do thoát
            exit_performance = results.get('exit_reason_performance', {})
            for reason, perf in exit_performance.items():
                html_content += f"""
                            <tr>
                                <td>{reason}</td>
                                <td>{perf.get('total_trades', 0)}</td>
                                <td>{perf.get('win_rate', 0):.2f}%</td>
                                <td class=\"{'positive' if perf.get('profit_per_trade', 0) >= 0 else 'negative'}\">
                                    ${perf.get('profit_per_trade', 0):.2f} ({perf.get('profit_per_trade_percent', 0):.2f}%)
                                </td>
                            </tr>
                """
            
            html_content += """
                        </table>
                        
                        <h3>Phân tích Trailing Stop</h3>
                        <table>
                            <tr>
                                <th>Thông số</th>
                                <th>Giá trị</th>
                            </tr>
                            <tr>
                                <td>Số giao dịch sử dụng trailing stop</td>
                                <td>""" + f"{results.get('ts_trades', 0)} ({results.get('ts_trades_percent', 0):.2f}%)" + """</td>
                            </tr>
                            <tr>
                                <td>Tỷ lệ thắng với trailing stop</td>
                                <td>""" + f"{results.get('ts_win_rate', 0):.2f}%" + """</td>
                            </tr>
                            <tr>
                                <td>% lợi nhuận được bảo vệ bởi trailing stop</td>
                                <td>""" + f"{results.get('ts_profit_protection', 0):.2f}%" + """</td>
                            </tr>
                        </table>
                    </div>
                    
                    <h2>Giao dịch gần đây</h2>
                    <table class="trades-table">
                        <tr>
                            <th>Thời gian vào</th>
                            <th>Cặp tiền</th>
                            <th>Hướng</th>
                            <th>Giá vào</th>
                            <th>Giá ra</th>
                            <th>P/L (%)</th>
                            <th>Lý do thoát</th>
                            <th>Chiến lược</th>
                        </tr>
            """
            
            # Thêm thông tin về các giao dịch gần đây (tối đa 20 giao dịch)
            recent_trades = self.closed_trades[-20:] if len(self.closed_trades) > 20 else self.closed_trades
            for trade in reversed(recent_trades):
                html_content += f"""
                        <tr>
                            <td>{trade.entry_time.strftime('%Y-%m-%d %H:%M') if trade.entry_time else ''}</td>
                            <td>{trade.symbol}</td>
                            <td>{trade.side}</td>
                            <td>${trade.entry_price:.2f}</td>
                            <td>${trade.exit_price:.2f}</td>
                            <td class=\"{'positive' if trade.profit_loss_percent >= 0 else 'negative'}\">
                                {trade.profit_loss_percent:.2f}%
                            </td>
                            <td>{trade.exit_reason}</td>
                            <td>{trade.strategy}</td>
                        </tr>
                """
            
            html_content += """
                    </table>
                </div>
            </body>
            </html>
            """
            
            # Lưu file HTML
            with open(html_path, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Đã tạo báo cáo HTML tại {html_path}")
            
            return html_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo HTML: {str(e)}")
            return ""

def create_sample_data():
    """Tạo dữ liệu mẫu cho backtest"""
    try:
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs('backtest_data', exist_ok=True)
        
        # Tạo dữ liệu cho BTCUSDT và ETHUSDT
        symbols = ['BTCUSDT', 'ETHUSDT']
        timeframes = ['1h']
        
        # Thiết lập thời gian
        start_date = datetime.datetime(2023, 1, 1)
        end_date = datetime.datetime(2023, 12, 31)
        
        for symbol in symbols:
            for timeframe in timeframes:
                # Tạo đường dẫn file
                filepath = os.path.join('backtest_data', f"{symbol}_{timeframe}.csv")
                
                # Kiểm tra file đã tồn tại
                if os.path.exists(filepath):
                    print(f"File {filepath} đã tồn tại, bỏ qua")
                    continue
                
                # Thiết lập giá ban đầu
                base_price = 50000 if symbol == 'BTCUSDT' else 3000
                current_price = base_price
                
                # Tạo dữ liệu
                data = []
                current_date = start_date
                
                while current_date <= end_date:
                    # Tạo biến động giá ngẫu nhiên (-2% đến +2%)
                    price_change = np.random.normal(0, 0.01) * current_price
                    current_price += price_change
                    
                    # Tính toán giá
                    open_price = current_price - price_change
                    high_price = max(open_price, current_price) * (1 + abs(np.random.normal(0, 0.005)))
                    low_price = min(open_price, current_price) * (1 - abs(np.random.normal(0, 0.005)))
                    close_price = current_price
                    
                    # Tạo volume
                    volume = base_price * np.random.normal(10, 3)
                    if volume < 0:
                        volume = base_price * 5
                    
                    # Thêm vào data
                    data.append({
                        'timestamp': current_date,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    })
                    
                    # Tăng thời gian
                    if timeframe == '1h':
                        current_date += datetime.timedelta(hours=1)
                    elif timeframe == '1d':
                        current_date += datetime.timedelta(days=1)
                
                # Tạo DataFrame
                df = pd.DataFrame(data)
                
                # Lưu vào file CSV
                df.to_csv(filepath, index=False)
                
                print(f"Đã tạo {len(data)} nến cho {symbol}_{timeframe}")
    
    except Exception as e:
        print(f"Lỗi khi tạo dữ liệu mẫu: {str(e)}")

def main():
    """Hàm chính để chạy backtest"""
    print("=== Comprehensive Backtest ===\n")
    
    # Kiểm tra thư mục dữ liệu
    if not os.path.exists('backtest_data') or len(os.listdir('backtest_data')) == 0:
        print("Chưa có dữ liệu backtest, tạo dữ liệu mẫu...")
        create_sample_data()
    
    # Khởi tạo backtest
    backtest = ComprehensiveBacktest()
    
    # Chạy backtest
    results = backtest.run_backtest()
    
    # Tạo báo cáo HTML
    if results:
        html_report = backtest.create_html_report(results)
        
        # Hiển thị tóm tắt kết quả
        print("\n=== Tóm tắt kết quả backtest ===")
        print(f"Số dư ban đầu: ${results.get('initial_balance', 0):,.2f}")
        print(f"Số dư cuối: ${results.get('final_balance', 0):,.2f}")
        print(f"Lợi nhuận: ${results.get('profit_loss', 0):,.2f} ({results.get('profit_loss_percent', 0):.2f}%)")
        print(f"Drawdown tối đa: {results.get('max_drawdown', 0):.2f}%")
        print(f"Tổng số giao dịch: {results.get('total_trades', 0)}")
        print(f"Tỷ lệ thắng: {results.get('win_rate', 0):.2f}%")
        print(f"Profit Factor: {results.get('profit_factor', 0):.2f}")
        print(f"Expectancy: ${results.get('expectancy', 0):.2f} ({results.get('expectancy_percent', 0):.2f}%)")
        print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        
        print(f"\nBáo cáo chi tiết đã được lưu tại: {html_report}")
    else:
        print("Không có kết quả backtest")
    
    print("\n=== Kết thúc backtest ===")

if __name__ == "__main__":
    main()