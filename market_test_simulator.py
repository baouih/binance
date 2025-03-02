#!/usr/bin/env python3
"""
Module mô phỏng thử nghiệm thị trường

Module này cung cấp công cụ để tự động kiểm thử các chiến lược giao dịch
trên nhiều điều kiện thị trường, giúp đánh giá toàn diện hiệu suất và độ tin cậy.
"""

import os
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime, timedelta
import concurrent.futures
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='market_test_simulator.log'
)
logger = logging.getLogger("market_test_simulator")
logger.addHandler(logging.StreamHandler())  # Thêm log ra console

# Thư mục lưu kết quả
RESULTS_DIR = "test_results"
CHARTS_DIR = "test_charts"

# Đảm bảo thư mục tồn tại
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# Các tình huống thị trường định trước
MARKET_SCENARIOS = {
    "strong_bull": {
        "name": "Thị trường tăng mạnh",
        "description": "Xu hướng tăng mạnh, ít biến động, thích hợp cho chiến lược theo xu hướng",
        "price_factor": 1.5,  # Hệ số nhân giá
        "volatility_factor": 0.7,  # Hệ số nhân biến động
        "volume_factor": 1.3,  # Hệ số nhân khối lượng
        "trend_factor": 0.8,  # Hệ số nhân trend (0-1: uptrend, -1-0: downtrend)
        "duration_days": 30  # Thời gian kéo dài (ngày)
    },
    "steady_bull": {
        "name": "Thị trường tăng ổn định",
        "description": "Xu hướng tăng ổn định, biến động trung bình, thích hợp cho đa số chiến lược",
        "price_factor": 1.2,
        "volatility_factor": 1.0,
        "volume_factor": 1.1,
        "trend_factor": 0.5,
        "duration_days": 30
    },
    "choppy_bull": {
        "name": "Thị trường tăng giằng co",
        "description": "Xu hướng tăng nhưng có nhiều dao động lớn, thách thức quản lý rủi ro",
        "price_factor": 1.1,
        "volatility_factor": 1.5,
        "volume_factor": 1.2,
        "trend_factor": 0.3,
        "duration_days": 30
    },
    "sideways": {
        "name": "Thị trường đi ngang",
        "description": "Không có xu hướng rõ ràng, thích hợp cho chiến lược mean-reversion",
        "price_factor": 1.0,
        "volatility_factor": 0.9,
        "volume_factor": 0.8,
        "trend_factor": 0.0,
        "duration_days": 30
    },
    "choppy_bear": {
        "name": "Thị trường giảm giằng co",
        "description": "Xu hướng giảm nhưng có nhiều dao động lớn, thách thức quản lý rủi ro",
        "price_factor": 0.9,
        "volatility_factor": 1.5,
        "volume_factor": 1.2,
        "trend_factor": -0.3,
        "duration_days": 30
    },
    "steady_bear": {
        "name": "Thị trường giảm ổn định",
        "description": "Xu hướng giảm ổn định, biến động trung bình, thách thức nhiều chiến lược",
        "price_factor": 0.85,
        "volatility_factor": 1.0,
        "volume_factor": 1.1,
        "trend_factor": -0.5,
        "duration_days": 30
    },
    "strong_bear": {
        "name": "Thị trường giảm mạnh",
        "description": "Xu hướng giảm mạnh, biến động lớn, thách thức quản lý rủi ro",
        "price_factor": 0.7,
        "volatility_factor": 1.8,
        "volume_factor": 1.5,
        "trend_factor": -0.8,
        "duration_days": 30
    },
    "crash": {
        "name": "Thị trường sụp đổ",
        "description": "Giảm đột ngột, biến động cực lớn, rủi ro thanh khoản cao",
        "price_factor": 0.5,
        "volatility_factor": 3.0,
        "volume_factor": 2.0,
        "trend_factor": -0.9,
        "duration_days": 15
    },
    "high_volatility": {
        "name": "Thị trường biến động cao",
        "description": "Biến động cao trong cả hai hướng, không có xu hướng rõ ràng",
        "price_factor": 1.05,
        "volatility_factor": 2.5,
        "volume_factor": 1.8,
        "trend_factor": 0.1,
        "duration_days": 30
    },
    "low_volatility": {
        "name": "Thị trường biến động thấp",
        "description": "Biến động thấp, khối lượng thấp, thách thức chiến lược dựa trên momentum",
        "price_factor": 1.02,
        "volatility_factor": 0.5,
        "volume_factor": 0.6,
        "trend_factor": 0.1,
        "duration_days": 30
    }
}

class MarketTestSimulator:
    """Lớp mô phỏng thử nghiệm thị trường"""
    
    def __init__(self, 
                base_data_file: str = None,
                symbol: str = "BTCUSDT",
                timeframe: str = "1h",
                initial_balance: float = 1000.0,
                trading_strategies: Dict = None,
                risk_profiles: Dict = None):
        """
        Khởi tạo bộ mô phỏng thử nghiệm thị trường
        
        Args:
            base_data_file (str): Đường dẫn đến file dữ liệu cơ sở (CSV)
            symbol (str): Biểu tượng giao dịch
            timeframe (str): Khung thời gian
            initial_balance (float): Số dư ban đầu
            trading_strategies (Dict): Các chiến lược giao dịch
            risk_profiles (Dict): Các hồ sơ rủi ro
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_balance = initial_balance
        
        # Tải dữ liệu cơ sở
        self.base_data = self._load_base_data(base_data_file) if base_data_file else None
        
        # Thiết lập chiến lược và hồ sơ rủi ro
        self.trading_strategies = trading_strategies or {}
        self.risk_profiles = risk_profiles or {}
        
        # Khởi tạo kết quả
        self.results = {}
        
        logger.info(f"Đã khởi tạo MarketTestSimulator cho {symbol} {timeframe}")
    
    def _load_base_data(self, file_path: str) -> pd.DataFrame:
        """
        Tải dữ liệu cơ sở từ file
        
        Args:
            file_path (str): Đường dẫn đến file dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Định dạng file không được hỗ trợ: {file_path}")
                
            # Chuyển đổi cột thời gian
            for col in ['timestamp', 'time', 'date', 'open_time', 'close_time']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
                    break
                    
            # Kiểm tra dữ liệu OHLCV
            required_columns = ['open', 'high', 'low', 'close']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"Dữ liệu thiếu cột {col}")
                    
            logger.info(f"Đã tải dữ liệu cơ sở từ {file_path}: {len(df)} bản ghi")
            
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu cơ sở: {e}")
            return pd.DataFrame()
    
    def generate_scenario_data(self, scenario_name: str, days: int = None) -> pd.DataFrame:
        """
        Tạo dữ liệu dựa trên kịch bản thị trường
        
        Args:
            scenario_name (str): Tên kịch bản thị trường
            days (int, optional): Số ngày dữ liệu, ghi đè lên giá trị mặc định
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu kịch bản
        """
        if scenario_name not in MARKET_SCENARIOS:
            logger.error(f"Kịch bản không hợp lệ: {scenario_name}")
            return pd.DataFrame()
            
        if self.base_data is None or self.base_data.empty:
            logger.error("Không có dữ liệu cơ sở để tạo kịch bản")
            return pd.DataFrame()
            
        # Lấy thông tin kịch bản
        scenario = MARKET_SCENARIOS[scenario_name]
        duration = days if days is not None else scenario['duration_days']
        
        # Xác định số lượng bản ghi cần lấy
        # Giả sử 24 bản ghi = 1 ngày cho timeframe 1h
        if self.timeframe == '1h':
            num_records = duration * 24
        elif self.timeframe == '4h':
            num_records = duration * 6
        elif self.timeframe == '1d':
            num_records = duration
        elif self.timeframe == '15m':
            num_records = duration * 24 * 4
        elif self.timeframe == '5m':
            num_records = duration * 24 * 12
        else:
            # Mặc định 24 bản ghi/ngày
            num_records = duration * 24
            
        # Lấy số lượng bản ghi từ dữ liệu cơ sở
        if len(self.base_data) < num_records:
            logger.warning(f"Dữ liệu cơ sở không đủ ({len(self.base_data)} < {num_records}), sử dụng tất cả dữ liệu có sẵn")
            base_subset = self.base_data.copy()
        else:
            # Lấy ngẫu nhiên một đoạn dữ liệu liên tiếp
            start_idx = np.random.randint(0, len(self.base_data) - num_records)
            base_subset = self.base_data.iloc[start_idx:start_idx + num_records].copy()
            
        # Áp dụng các hệ số từ kịch bản
        price_factor = scenario['price_factor']
        volatility_factor = scenario['volatility_factor']
        volume_factor = scenario['volume_factor']
        trend_factor = scenario['trend_factor']
        
        # Tạo xu hướng giá dựa trên các hệ số
        trend_component = np.linspace(0, trend_factor, num=len(base_subset))
        
        # Áp dụng vào dữ liệu
        # 1. Điều chỉnh giá theo xu hướng và hệ số giá
        base_price = base_subset['close'].iloc[0]
        for col in ['open', 'high', 'low', 'close']:
            if col in base_subset.columns:
                # Giữ nguyên phần tương đối so với giá đầu tiên, nhưng thêm xu hướng và nhân hệ số
                relative_price = base_subset[col] / base_price
                base_subset[col] = base_price * relative_price * (1 + trend_component) * price_factor
                
        # 2. Điều chỉnh biến động (high-low)
        if all(col in base_subset.columns for col in ['high', 'low']):
            # Tăng khoảng cách high-low theo hệ số biến động
            midpoint = (base_subset['high'] + base_subset['low']) / 2
            half_range = (base_subset['high'] - base_subset['low']) / 2
            
            base_subset['high'] = midpoint + half_range * volatility_factor
            base_subset['low'] = midpoint - half_range * volatility_factor
            
            # Đảm bảo high >= open, close và low <= open, close
            base_subset['high'] = base_subset[['high', 'open', 'close']].max(axis=1)
            base_subset['low'] = base_subset[['low', 'open', 'close']].min(axis=1)
                
        # 3. Điều chỉnh khối lượng
        if 'volume' in base_subset.columns:
            base_subset['volume'] = base_subset['volume'] * volume_factor
            
        # Đặt tên kịch bản và mô tả vào metadata
        base_subset['scenario_name'] = scenario_name
        base_subset['scenario_description'] = scenario['name']
        
        logger.info(f"Đã tạo dữ liệu kịch bản {scenario_name}: {len(base_subset)} bản ghi")
        
        return base_subset
    
    def run_backtest(self, strategy_name: str, risk_profile: str, data: pd.DataFrame) -> Dict:
        """
        Chạy backtest một chiến lược trên dữ liệu
        
        Args:
            strategy_name (str): Tên chiến lược
            risk_profile (str): Tên hồ sơ rủi ro
            data (pd.DataFrame): Dữ liệu thị trường
            
        Returns:
            Dict: Kết quả backtest
        """
        if strategy_name not in self.trading_strategies:
            logger.error(f"Không tìm thấy chiến lược {strategy_name}")
            return {}
            
        if risk_profile not in self.risk_profiles:
            logger.error(f"Không tìm thấy hồ sơ rủi ro {risk_profile}")
            return {}
            
        if data is None or data.empty:
            logger.error("Không có dữ liệu để chạy backtest")
            return {}
            
        # Lấy chiến lược và hồ sơ rủi ro
        strategy = self.trading_strategies[strategy_name]
        risk_params = self.risk_profiles[risk_profile]
        
        # Cài đặt balance ban đầu
        balance = self.initial_balance
        
        # Khởi tạo danh sách giao dịch
        trades = []
        
        # Khởi tạo trạng thái
        in_position = False
        entry_price = 0
        position_size = 0
        entry_time = None
        stop_loss = 0
        take_profit = 0
        
        # Chạy backtest qua từng bản ghi
        for i in range(1, len(data)):
            row = data.iloc[i]
            prev_row = data.iloc[i-1]
            
            # Lấy thời gian hiện tại
            timestamp = row.get('timestamp', row.get('time', row.get('date', pd.Timestamp(i))))
            
            # Lấy giá hiện tại
            current_price = row['close']
            
            # Kiểm tra nếu đang trong vị thế
            if in_position:
                # Kiểm tra stop loss và take profit
                if (entry_price > stop_loss and current_price <= stop_loss) or \
                   (entry_price < stop_loss and current_price >= stop_loss):
                    # Dừng lỗ
                    if entry_price > stop_loss:  # Long position
                        profit = (stop_loss - entry_price) * position_size
                    else:  # Short position
                        profit = (entry_price - stop_loss) * position_size
                        
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'side': 'buy' if entry_price > stop_loss else 'sell',
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'quantity': position_size,
                        'profit': profit,
                        'exit_reason': 'stop_loss'
                    })
                    
                    balance += profit
                    in_position = False
                    
                elif (entry_price < take_profit and current_price >= take_profit) or \
                     (entry_price > take_profit and current_price <= take_profit):
                    # Chốt lời
                    if entry_price < take_profit:  # Long position
                        profit = (take_profit - entry_price) * position_size
                    else:  # Short position
                        profit = (entry_price - take_profit) * position_size
                        
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'side': 'buy' if entry_price < take_profit else 'sell',
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'quantity': position_size,
                        'profit': profit,
                        'exit_reason': 'take_profit'
                    })
                    
                    balance += profit
                    in_position = False
            
            # Tạo tín hiệu giao dịch
            signal = self._generate_signal(strategy, row, prev_row)
            
            # Xử lý tín hiệu
            if not in_position and signal != 0:
                # Mở vị thế mới
                # Tính position size dựa trên quản lý rủi ro
                risk_amount = balance * (risk_params['risk_per_trade'] / 100)
                
                if signal > 0:  # Buy signal
                    # Tính stop loss
                    stop_distance = row['close'] * (risk_params['stop_loss_percent_long'] / 100)
                    stop_loss = row['close'] - stop_distance
                    
                    # Tính position size
                    position_size = risk_amount / stop_distance
                    
                    # Tính take profit
                    take_profit_distance = stop_distance * risk_params['risk_reward_ratio']
                    take_profit = row['close'] + take_profit_distance
                    
                    # Mở vị thế
                    entry_price = row['close']
                    entry_time = timestamp
                    in_position = True
                    
                elif signal < 0:  # Sell signal
                    # Tính stop loss
                    stop_distance = row['close'] * (risk_params['stop_loss_percent_short'] / 100)
                    stop_loss = row['close'] + stop_distance
                    
                    # Tính position size
                    position_size = risk_amount / stop_distance
                    
                    # Tính take profit
                    take_profit_distance = stop_distance * risk_params['risk_reward_ratio']
                    take_profit = row['close'] - take_profit_distance
                    
                    # Mở vị thế
                    entry_price = row['close']
                    entry_time = timestamp
                    in_position = True
        
        # Đóng vị thế cuối cùng nếu còn mở
        if in_position:
            if entry_price < current_price:  # Long position
                profit = (current_price - entry_price) * position_size
            else:  # Short position
                profit = (entry_price - current_price) * position_size
                
            trades.append({
                'entry_time': entry_time,
                'exit_time': timestamp,
                'side': 'buy' if entry_price < current_price else 'sell',
                'entry_price': entry_price,
                'exit_price': current_price,
                'quantity': position_size,
                'profit': profit,
                'exit_reason': 'end_of_data'
            })
            
            balance += profit
            
        # Tạo DataFrame giao dịch
        trades_df = pd.DataFrame(trades)
        
        # Tính toán các chỉ số hiệu suất
        performance = self._calculate_performance(trades_df, balance)
        
        # Tạo kết quả
        results = {
            'strategy': strategy_name,
            'risk_profile': risk_profile,
            'scenario': data['scenario_name'].iloc[0],
            'scenario_description': data['scenario_description'].iloc[0],
            'initial_balance': self.initial_balance,
            'final_balance': balance,
            'total_trades': len(trades),
            'trades': trades_df,
            'performance': performance
        }
        
        logger.info(f"Đã chạy backtest {strategy_name} với {risk_profile} trên {data['scenario_name'].iloc[0]}: {len(trades)} giao dịch, balance: ${balance:.2f}")
        
        return results
    
    def _generate_signal(self, strategy: Dict, current_row: pd.Series, previous_row: pd.Series) -> int:
        """
        Tạo tín hiệu dựa trên chiến lược
        
        Args:
            strategy (Dict): Cấu hình chiến lược
            current_row (pd.Series): Dữ liệu hiện tại
            previous_row (pd.Series): Dữ liệu trước đó
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Lấy tên chiến lược
        strategy_type = strategy.get('type', '').lower()
        
        if strategy_type == 'rsi':
            return self._rsi_strategy(strategy, current_row, previous_row)
        elif strategy_type == 'macd':
            return self._macd_strategy(strategy, current_row, previous_row)
        elif strategy_type == 'bollinger':
            return self._bollinger_strategy(strategy, current_row, previous_row)
        elif strategy_type == 'ema_cross':
            return self._ema_cross_strategy(strategy, current_row, previous_row)
        elif strategy_type == 'breakout':
            return self._breakout_strategy(strategy, current_row, previous_row)
        else:
            # Mặc định không giao dịch
            return 0
    
    def _rsi_strategy(self, strategy: Dict, current_row: pd.Series, previous_row: pd.Series) -> int:
        """
        Chiến lược RSI
        
        Args:
            strategy (Dict): Cấu hình chiến lược
            current_row (pd.Series): Dữ liệu hiện tại
            previous_row (pd.Series): Dữ liệu trước đó
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra các cột cần thiết
        if 'rsi' not in current_row or 'rsi' not in previous_row:
            return 0
            
        # Lấy tham số
        oversold = strategy.get('oversold', 30)
        overbought = strategy.get('overbought', 70)
        
        # Kiểm tra tín hiệu
        if previous_row['rsi'] < oversold and current_row['rsi'] > oversold:
            return 1  # Mua khi RSI vượt lên trên ngưỡng oversold
        elif previous_row['rsi'] > overbought and current_row['rsi'] < overbought:
            return -1  # Bán khi RSI giảm xuống dưới ngưỡng overbought
            
        return 0
    
    def _macd_strategy(self, strategy: Dict, current_row: pd.Series, previous_row: pd.Series) -> int:
        """
        Chiến lược MACD
        
        Args:
            strategy (Dict): Cấu hình chiến lược
            current_row (pd.Series): Dữ liệu hiện tại
            previous_row (pd.Series): Dữ liệu trước đó
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra các cột cần thiết
        if 'macd' not in current_row or 'macd_signal' not in current_row:
            return 0
            
        # Kiểm tra tín hiệu
        if previous_row['macd'] < previous_row['macd_signal'] and current_row['macd'] > current_row['macd_signal']:
            return 1  # Mua khi MACD cắt lên trên đường tín hiệu
        elif previous_row['macd'] > previous_row['macd_signal'] and current_row['macd'] < current_row['macd_signal']:
            return -1  # Bán khi MACD cắt xuống dưới đường tín hiệu
            
        return 0
    
    def _bollinger_strategy(self, strategy: Dict, current_row: pd.Series, previous_row: pd.Series) -> int:
        """
        Chiến lược Bollinger Bands
        
        Args:
            strategy (Dict): Cấu hình chiến lược
            current_row (pd.Series): Dữ liệu hiện tại
            previous_row (pd.Series): Dữ liệu trước đó
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra các cột cần thiết
        if 'bb_upper' not in current_row or 'bb_lower' not in current_row:
            return 0
            
        # Kiểm tra tín hiệu
        if previous_row['close'] <= previous_row['bb_lower'] and current_row['close'] > current_row['bb_lower']:
            return 1  # Mua khi giá vượt lên trên dải dưới
        elif previous_row['close'] >= previous_row['bb_upper'] and current_row['close'] < current_row['bb_upper']:
            return -1  # Bán khi giá giảm xuống dưới dải trên
            
        return 0
    
    def _ema_cross_strategy(self, strategy: Dict, current_row: pd.Series, previous_row: pd.Series) -> int:
        """
        Chiến lược EMA Cross
        
        Args:
            strategy (Dict): Cấu hình chiến lược
            current_row (pd.Series): Dữ liệu hiện tại
            previous_row (pd.Series): Dữ liệu trước đó
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra các cột cần thiết
        if 'ema_short' not in current_row or 'ema_long' not in current_row:
            return 0
            
        # Kiểm tra tín hiệu
        if previous_row['ema_short'] < previous_row['ema_long'] and current_row['ema_short'] > current_row['ema_long']:
            return 1  # Mua khi EMA ngắn cắt lên trên EMA dài
        elif previous_row['ema_short'] > previous_row['ema_long'] and current_row['ema_short'] < current_row['ema_long']:
            return -1  # Bán khi EMA ngắn cắt xuống dưới EMA dài
            
        return 0
    
    def _breakout_strategy(self, strategy: Dict, current_row: pd.Series, previous_row: pd.Series) -> int:
        """
        Chiến lược Breakout
        
        Args:
            strategy (Dict): Cấu hình chiến lược
            current_row (pd.Series): Dữ liệu hiện tại
            previous_row (pd.Series): Dữ liệu trước đó
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra các cột cần thiết
        if 'resistance' not in current_row or 'support' not in current_row:
            return 0
            
        # Lấy tham số
        breakout_threshold = strategy.get('breakout_threshold', 0.3)  # % vượt qua ngưỡng
        
        # Tính ngưỡng
        resistance_threshold = current_row['resistance'] * (1 + breakout_threshold / 100)
        support_threshold = current_row['support'] * (1 - breakout_threshold / 100)
        
        # Kiểm tra tín hiệu
        if previous_row['close'] < current_row['resistance'] and current_row['close'] > resistance_threshold:
            return 1  # Mua khi giá vượt lên trên ngưỡng kháng cự
        elif previous_row['close'] > current_row['support'] and current_row['close'] < support_threshold:
            return -1  # Bán khi giá giảm xuống dưới ngưỡng hỗ trợ
            
        return 0
    
    def _calculate_performance(self, trades_df: pd.DataFrame, final_balance: float) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Args:
            trades_df (pd.DataFrame): DataFrame chứa dữ liệu giao dịch
            final_balance (float): Số dư cuối cùng
            
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if trades_df.empty:
            return {
                'win_rate': 0,
                'profit_factor': 0,
                'average_profit': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'roi': 0,
                'total_trades': 0
            }
            
        # Số lượng giao dịch
        total_trades = len(trades_df)
        
        # Tính thắng/thua
        winning_trades = len(trades_df[trades_df['profit'] > 0])
        losing_trades = len(trades_df[trades_df['profit'] <= 0])
        
        # Tính tỷ lệ thắng
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Tính profit factor
        gross_profit = trades_df[trades_df['profit'] > 0]['profit'].sum()
        gross_loss = abs(trades_df[trades_df['profit'] < 0]['profit'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Tính lợi nhuận trung bình
        average_profit = trades_df['profit'].mean()
        
        # Tính max drawdown
        balances = [self.initial_balance]
        for profit in trades_df['profit']:
            balances.append(balances[-1] + profit)
            
        cumulative_returns = np.array(balances)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100  # %
        
        # Tính Sharpe ratio (giả sử risk-free rate = 0)
        if len(trades_df) > 1:
            returns = trades_df['profit'] / self.initial_balance
            sharpe_ratio = returns.mean() / returns.std() if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
            
        # Tính ROI
        roi = (final_balance - self.initial_balance) / self.initial_balance * 100  # %
        
        return {
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'average_profit': average_profit,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'roi': roi,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'final_balance': final_balance
        }
    
    def run_multi_scenario_test(self, scenarios: List[str] = None, 
                             strategies: List[str] = None,
                             risk_profiles: List[str] = None,
                             days: int = None,
                             parallel: bool = True) -> Dict[str, Dict]:
        """
        Chạy kiểm thử trên nhiều kịch bản, chiến lược và hồ sơ rủi ro
        
        Args:
            scenarios (List[str]): Danh sách kịch bản thị trường
            strategies (List[str]): Danh sách chiến lược
            risk_profiles (List[str]): Danh sách hồ sơ rủi ro
            days (int): Số ngày dữ liệu
            parallel (bool): Chạy song song hay tuần tự
            
        Returns:
            Dict[str, Dict]: Kết quả kiểm thử
        """
        # Nếu không chỉ định, sử dụng tất cả
        if scenarios is None:
            scenarios = list(MARKET_SCENARIOS.keys())
            
        if strategies is None:
            strategies = list(self.trading_strategies.keys())
            
        if risk_profiles is None:
            risk_profiles = list(self.risk_profiles.keys())
            
        # Kiểm tra dữ liệu đầu vào
        if not scenarios:
            logger.error("Không có kịch bản thị trường")
            return {}
            
        if not strategies:
            logger.error("Không có chiến lược giao dịch")
            return {}
            
        if not risk_profiles:
            logger.error("Không có hồ sơ rủi ro")
            return {}
            
        # Tạo danh sách các bài test
        test_configs = []
        for scenario in scenarios:
            for strategy_name in strategies:
                for risk_profile in risk_profiles:
                    test_configs.append((scenario, strategy_name, risk_profile))
                    
        logger.info(f"Chạy {len(test_configs)} bài test trên {len(scenarios)} kịch bản, {len(strategies)} chiến lược và {len(risk_profiles)} hồ sơ rủi ro")
        
        results = {}
        
        if parallel and len(test_configs) > 1:
            # Chạy song song
            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = []
                for scenario, strategy_name, risk_profile in test_configs:
                    futures.append(executor.submit(
                        self._run_single_test, scenario, strategy_name, risk_profile, days
                    ))
                    
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        result = future.result()
                        if result:
                            test_id = f"{result['scenario']}_{result['strategy']}_{result['risk_profile']}"
                            results[test_id] = result
                            logger.info(f"Hoàn thành {i+1}/{len(test_configs)}: {test_id}")
                    except Exception as e:
                        logger.error(f"Lỗi khi chạy test: {e}")
        else:
            # Chạy tuần tự
            for i, (scenario, strategy_name, risk_profile) in enumerate(test_configs):
                try:
                    result = self._run_single_test(scenario, strategy_name, risk_profile, days)
                    if result:
                        test_id = f"{scenario}_{strategy_name}_{risk_profile}"
                        results[test_id] = result
                        logger.info(f"Hoàn thành {i+1}/{len(test_configs)}: {test_id}")
                except Exception as e:
                    logger.error(f"Lỗi khi chạy test {scenario}_{strategy_name}_{risk_profile}: {e}")
                    
        # Lưu kết quả
        self.results = results
        
        # Lưu kết quả vào file
        self._save_results()
        
        return results
    
    def _run_single_test(self, scenario: str, strategy_name: str, risk_profile: str, days: int = None) -> Dict:
        """
        Chạy một bài test đơn
        
        Args:
            scenario (str): Tên kịch bản thị trường
            strategy_name (str): Tên chiến lược
            risk_profile (str): Tên hồ sơ rủi ro
            days (int): Số ngày dữ liệu
            
        Returns:
            Dict: Kết quả test
        """
        # Tạo dữ liệu kịch bản
        scenario_data = self.generate_scenario_data(scenario, days)
        
        if scenario_data.empty:
            logger.error(f"Không thể tạo dữ liệu kịch bản {scenario}")
            return {}
            
        # Chạy backtest
        result = self.run_backtest(strategy_name, risk_profile, scenario_data)
        
        return result
    
    def _save_results(self, file_path: str = None) -> str:
        """
        Lưu kết quả vào file
        
        Args:
            file_path (str, optional): Đường dẫn lưu file
            
        Returns:
            str: Đường dẫn đến file đã lưu
        """
        if not self.results:
            logger.warning("Không có kết quả để lưu")
            return None
            
        if file_path is None:
            # Tạo tên file với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(RESULTS_DIR, f"test_results_{timestamp}.json")
            
        try:
            # Tạo bản sao của kết quả
            results_copy = {}
            
            for test_id, result in self.results.items():
                # Loại bỏ DataFrame (không thể serialize)
                result_copy = {k: v for k, v in result.items() if k != 'trades'}
                
                # Chuyển đổi các đối tượng không thể serialize
                if 'trades' in result and isinstance(result['trades'], pd.DataFrame):
                    trades_list = []
                    for _, row in result['trades'].iterrows():
                        trade_dict = {k: v for k, v in row.items()}
                        # Chuyển đổi timestamp
                        for key in ['entry_time', 'exit_time']:
                            if key in trade_dict and isinstance(trade_dict[key], (pd.Timestamp, datetime)):
                                trade_dict[key] = trade_dict[key].strftime("%Y-%m-%d %H:%M:%S")
                        trades_list.append(trade_dict)
                    result_copy['trades'] = trades_list
                    
                results_copy[test_id] = result_copy
                
            # Lưu vào file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(results_copy, f, indent=4)
                
            logger.info(f"Đã lưu kết quả vào {file_path}")
            
            return file_path
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả: {e}")
            return None
    
    def generate_summary_report(self, output_path: str = None) -> str:
        """
        Tạo báo cáo tổng hợp
        
        Args:
            output_path (str, optional): Đường dẫn lưu báo cáo
            
        Returns:
            str: Đường dẫn đến báo cáo
        """
        if not self.results:
            logger.warning("Không có kết quả để tạo báo cáo")
            return None
            
        # Chuẩn bị dữ liệu
        summary_data = []
        
        for test_id, result in self.results.items():
            # Lấy thông tin
            scenario = result.get('scenario', 'unknown')
            scenario_desc = result.get('scenario_description', 'unknown')
            strategy = result.get('strategy', 'unknown')
            risk_profile = result.get('risk_profile', 'unknown')
            
            # Lấy hiệu suất
            performance = result.get('performance', {})
            
            # Thêm vào dữ liệu tổng hợp
            summary_data.append({
                'test_id': test_id,
                'scenario': scenario,
                'scenario_description': scenario_desc,
                'strategy': strategy,
                'risk_profile': risk_profile,
                'total_trades': performance.get('total_trades', 0),
                'win_rate': performance.get('win_rate', 0),
                'roi': performance.get('roi', 0),
                'profit_factor': performance.get('profit_factor', 0),
                'max_drawdown': performance.get('max_drawdown', 0),
                'sharpe_ratio': performance.get('sharpe_ratio', 0),
                'final_balance': performance.get('final_balance', 0)
            })
            
        # Tạo DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        # Tạo báo cáo text
        if output_path is None:
            # Tạo tên file với timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(RESULTS_DIR, f"test_summary_{timestamp}.txt")
            
        try:
            # Tạo nội dung báo cáo
            report_content = f"""
========================================================
MARKET TEST SIMULATOR - SUMMARY REPORT
========================================================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Initial Balance: ${self.initial_balance:.2f}
Symbol: {self.symbol}
Timeframe: {self.timeframe}
Total Tests: {len(self.results)}

PERFORMANCE BY SCENARIO
------------------
"""
            
            # Tạo bảng hiệu suất theo kịch bản
            scenario_performance = summary_df.groupby('scenario').agg({
                'roi': 'mean',
                'win_rate': 'mean',
                'profit_factor': 'mean',
                'max_drawdown': 'mean',
                'total_trades': 'sum',
                'sharpe_ratio': 'mean'
            }).reset_index()
            
            scenario_table = tabulate(
                scenario_performance.values,
                headers=['Scenario', 'Avg ROI (%)', 'Avg Win Rate', 'Avg Profit Factor', 'Avg Max DD (%)', 'Total Trades', 'Avg Sharpe Ratio'],
                tablefmt="grid",
                numalign="right",
                floatfmt=".2f"
            )
            
            report_content += scenario_table
            
            report_content += """

PERFORMANCE BY STRATEGY
------------------
"""
            
            # Tạo bảng hiệu suất theo chiến lược
            strategy_performance = summary_df.groupby('strategy').agg({
                'roi': 'mean',
                'win_rate': 'mean',
                'profit_factor': 'mean',
                'max_drawdown': 'mean',
                'total_trades': 'sum',
                'sharpe_ratio': 'mean'
            }).reset_index()
            
            strategy_table = tabulate(
                strategy_performance.values,
                headers=['Strategy', 'Avg ROI (%)', 'Avg Win Rate', 'Avg Profit Factor', 'Avg Max DD (%)', 'Total Trades', 'Avg Sharpe Ratio'],
                tablefmt="grid",
                numalign="right",
                floatfmt=".2f"
            )
            
            report_content += strategy_table
            
            report_content += """

PERFORMANCE BY RISK PROFILE
------------------
"""
            
            # Tạo bảng hiệu suất theo hồ sơ rủi ro
            risk_performance = summary_df.groupby('risk_profile').agg({
                'roi': 'mean',
                'win_rate': 'mean',
                'profit_factor': 'mean',
                'max_drawdown': 'mean',
                'total_trades': 'sum',
                'sharpe_ratio': 'mean'
            }).reset_index()
            
            risk_table = tabulate(
                risk_performance.values,
                headers=['Risk Profile', 'Avg ROI (%)', 'Avg Win Rate', 'Avg Profit Factor', 'Avg Max DD (%)', 'Total Trades', 'Avg Sharpe Ratio'],
                tablefmt="grid",
                numalign="right",
                floatfmt=".2f"
            )
            
            report_content += risk_table
            
            report_content += """

TOP 5 PERFORMING TESTS
------------------
"""
            
            # Tạo bảng top 5 bài test
            top_tests = summary_df.sort_values('roi', ascending=False).head(5)
            
            top_table = tabulate(
                top_tests[['test_id', 'strategy', 'risk_profile', 'scenario', 'roi', 'win_rate', 'profit_factor', 'max_drawdown']].values,
                headers=['Test ID', 'Strategy', 'Risk Profile', 'Scenario', 'ROI (%)', 'Win Rate', 'Profit Factor', 'Max DD (%)'],
                tablefmt="grid",
                numalign="right",
                floatfmt=".2f"
            )
            
            report_content += top_table
            
            report_content += """

WORST 5 PERFORMING TESTS
------------------
"""
            
            # Tạo bảng worst 5 bài test
            worst_tests = summary_df.sort_values('roi', ascending=True).head(5)
            
            worst_table = tabulate(
                worst_tests[['test_id', 'strategy', 'risk_profile', 'scenario', 'roi', 'win_rate', 'profit_factor', 'max_drawdown']].values,
                headers=['Test ID', 'Strategy', 'Risk Profile', 'Scenario', 'ROI (%)', 'Win Rate', 'Profit Factor', 'Max DD (%)'],
                tablefmt="grid",
                numalign="right",
                floatfmt=".2f"
            )
            
            report_content += worst_table
            
            report_content += """

OVERALL BEST COMBINATIONS
------------------
"""
            
            # Tạo bảng best strategy + risk profile combinations
            combination_performance = summary_df.groupby(['strategy', 'risk_profile']).agg({
                'roi': 'mean',
                'win_rate': 'mean',
                'profit_factor': 'mean',
                'max_drawdown': 'mean',
                'sharpe_ratio': 'mean'
            }).reset_index()
            
            best_combinations = combination_performance.sort_values('roi', ascending=False).head(5)
            
            combination_table = tabulate(
                best_combinations[['strategy', 'risk_profile', 'roi', 'win_rate', 'profit_factor', 'max_drawdown', 'sharpe_ratio']].values,
                headers=['Strategy', 'Risk Profile', 'Avg ROI (%)', 'Avg Win Rate', 'Avg Profit Factor', 'Avg Max DD (%)', 'Avg Sharpe Ratio'],
                tablefmt="grid",
                numalign="right",
                floatfmt=".2f"
            )
            
            report_content += combination_table
            
            report_content += """
========================================================
                Generated by Market Test Simulator
========================================================
"""
            
            # Lưu vào file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            logger.info(f"Đã tạo báo cáo tổng hợp và lưu tại {output_path}")
            
            # Tạo biểu đồ
            self._generate_summary_charts()
            
            return output_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {e}")
            return None
    
    def _generate_summary_charts(self) -> List[str]:
        """
        Tạo các biểu đồ tổng hợp
        
        Returns:
            List[str]: Danh sách đường dẫn đến các biểu đồ
        """
        if not self.results:
            logger.warning("Không có kết quả để tạo biểu đồ")
            return []
            
        # Chuẩn bị dữ liệu
        summary_data = []
        
        for test_id, result in self.results.items():
            # Lấy thông tin
            scenario = result.get('scenario', 'unknown')
            strategy = result.get('strategy', 'unknown')
            risk_profile = result.get('risk_profile', 'unknown')
            
            # Lấy hiệu suất
            performance = result.get('performance', {})
            
            # Thêm vào dữ liệu tổng hợp
            summary_data.append({
                'test_id': test_id,
                'scenario': scenario,
                'strategy': strategy,
                'risk_profile': risk_profile,
                'roi': performance.get('roi', 0),
                'win_rate': performance.get('win_rate', 0) * 100,  # Chuyển thành %
                'profit_factor': performance.get('profit_factor', 0),
                'max_drawdown': performance.get('max_drawdown', 0)
            })
            
        # Tạo DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        chart_paths = []
        
        # 1. Biểu đồ ROI theo kịch bản và chiến lược
        try:
            plt.figure(figsize=(12, 8))
            
            # Tạo pivot table
            roi_pivot = summary_df.pivot_table(
                values='roi',
                index='scenario',
                columns='strategy',
                aggfunc='mean'
            )
            
            # Vẽ heatmap
            ax = plt.axes()
            im = ax.imshow(roi_pivot.values, cmap='RdYlGn')
            
            # Thêm nhãn
            ax.set_xticks(np.arange(len(roi_pivot.columns)))
            ax.set_yticks(np.arange(len(roi_pivot.index)))
            ax.set_xticklabels(roi_pivot.columns)
            ax.set_yticklabels(roi_pivot.index)
            
            # Xoay nhãn
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
            
            # Thêm giá trị
            for i in range(len(roi_pivot.index)):
                for j in range(len(roi_pivot.columns)):
                    text = ax.text(j, i, f"{roi_pivot.values[i, j]:.2f}%",
                               ha="center", va="center", color="black")
                    
            # Thêm colorbar
            cbar = ax.figure.colorbar(im, ax=ax)
            cbar.ax.set_ylabel("ROI (%)", rotation=-90, va="bottom")
            
            # Đặt tiêu đề
            plt.title("ROI by Market Scenario and Strategy")
            plt.tight_layout()
            
            # Lưu biểu đồ
            chart_path = os.path.join(CHARTS_DIR, f"roi_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            chart_paths.append(chart_path)
            logger.info(f"Đã tạo biểu đồ ROI heatmap và lưu tại {chart_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ ROI heatmap: {e}")
            
        # 2. Biểu đồ so sánh ROI theo chiến lược
        try:
            plt.figure(figsize=(10, 6))
            
            # Nhóm theo chiến lược
            strategy_roi = summary_df.groupby('strategy')['roi'].mean().sort_values(ascending=False)
            
            # Vẽ biểu đồ cột
            ax = strategy_roi.plot(kind='bar', color='#2196F3')
            
            # Thêm nhãn giá trị
            for i, v in enumerate(strategy_roi):
                ax.text(i, v + 0.5, f"{v:.2f}%", ha='center', fontsize=9)
                
            # Đặt tiêu đề và nhãn
            plt.title("Average ROI by Strategy")
            plt.xlabel("Strategy")
            plt.ylabel("ROI (%)")
            plt.tight_layout()
            
            # Lưu biểu đồ
            chart_path = os.path.join(CHARTS_DIR, f"strategy_roi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            chart_paths.append(chart_path)
            logger.info(f"Đã tạo biểu đồ so sánh ROI theo chiến lược và lưu tại {chart_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ so sánh ROI theo chiến lược: {e}")
            
        # 3. Biểu đồ so sánh ROI theo hồ sơ rủi ro
        try:
            plt.figure(figsize=(10, 6))
            
            # Nhóm theo hồ sơ rủi ro
            risk_roi = summary_df.groupby('risk_profile')['roi'].mean().sort_values(ascending=False)
            
            # Vẽ biểu đồ cột
            ax = risk_roi.plot(kind='bar', color='#4CAF50')
            
            # Thêm nhãn giá trị
            for i, v in enumerate(risk_roi):
                ax.text(i, v + 0.5, f"{v:.2f}%", ha='center', fontsize=9)
                
            # Đặt tiêu đề và nhãn
            plt.title("Average ROI by Risk Profile")
            plt.xlabel("Risk Profile")
            plt.ylabel("ROI (%)")
            plt.tight_layout()
            
            # Lưu biểu đồ
            chart_path = os.path.join(CHARTS_DIR, f"risk_roi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            chart_paths.append(chart_path)
            logger.info(f"Đã tạo biểu đồ so sánh ROI theo hồ sơ rủi ro và lưu tại {chart_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ so sánh ROI theo hồ sơ rủi ro: {e}")
            
        # 4. Biểu đồ so sánh Win Rate vs Max Drawdown
        try:
            plt.figure(figsize=(10, 8))
            
            # Vẽ scatter plot
            for strategy in summary_df['strategy'].unique():
                strategy_data = summary_df[summary_df['strategy'] == strategy]
                plt.scatter(
                    strategy_data['win_rate'],
                    strategy_data['max_drawdown'],
                    label=strategy,
                    s=80,
                    alpha=0.7
                )
                
            # Đặt tiêu đề và nhãn
            plt.title("Win Rate vs Max Drawdown by Strategy")
            plt.xlabel("Win Rate (%)")
            plt.ylabel("Max Drawdown (%)")
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Lưu biểu đồ
            chart_path = os.path.join(CHARTS_DIR, f"winrate_drawdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(chart_path, dpi=300)
            plt.close()
            
            chart_paths.append(chart_path)
            logger.info(f"Đã tạo biểu đồ so sánh Win Rate vs Max Drawdown và lưu tại {chart_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ so sánh Win Rate vs Max Drawdown: {e}")
            
        return chart_paths

def main():
    """Hàm chính để chạy MarketTestSimulator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Market Test Simulator')
    parser.add_argument('--data', type=str, required=True, help='Path to base data file (CSV)')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Trading symbol')
    parser.add_argument('--timeframe', type=str, default='1h', help='Trading timeframe')
    parser.add_argument('--balance', type=float, default=1000.0, help='Initial balance')
    parser.add_argument('--strategies', type=str, help='Path to strategies configuration file (JSON)')
    parser.add_argument('--risk-profiles', type=str, help='Path to risk profiles configuration file (JSON)')
    parser.add_argument('--scenarios', type=str, nargs='+', help='Market scenarios to test')
    parser.add_argument('--days', type=int, help='Number of days for each scenario')
    parser.add_argument('--no-parallel', action='store_true', help='Disable parallel testing')
    parser.add_argument('--output-dir', type=str, help='Output directory for results and charts')
    
    args = parser.parse_args()
    
    # Cập nhật thư mục đầu ra nếu được chỉ định
    if args.output_dir:
        global RESULTS_DIR, CHARTS_DIR
        RESULTS_DIR = os.path.join(args.output_dir, 'results')
        CHARTS_DIR = os.path.join(args.output_dir, 'charts')
        os.makedirs(RESULTS_DIR, exist_ok=True)
        os.makedirs(CHARTS_DIR, exist_ok=True)
    
    # Tải cấu hình chiến lược
    strategies = {}
    if args.strategies:
        try:
            with open(args.strategies, 'r') as f:
                strategies = json.load(f)
            logger.info(f"Đã tải {len(strategies)} chiến lược từ {args.strategies}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình chiến lược: {e}")
            strategies = {
                "rsi_standard": {
                    "type": "rsi",
                    "oversold": 30,
                    "overbought": 70
                },
                "macd_standard": {
                    "type": "macd"
                },
                "bollinger_standard": {
                    "type": "bollinger"
                },
                "ema_cross_standard": {
                    "type": "ema_cross"
                }
            }
    else:
        # Chiến lược mặc định
        strategies = {
            "rsi_standard": {
                "type": "rsi",
                "oversold": 30,
                "overbought": 70
            },
            "macd_standard": {
                "type": "macd"
            },
            "bollinger_standard": {
                "type": "bollinger"
            },
            "ema_cross_standard": {
                "type": "ema_cross"
            }
        }
    
    # Tải cấu hình hồ sơ rủi ro
    risk_profiles = {}
    if args.risk_profiles:
        try:
            with open(args.risk_profiles, 'r') as f:
                risk_profiles = json.load(f)
            logger.info(f"Đã tải {len(risk_profiles)} hồ sơ rủi ro từ {args.risk_profiles}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình hồ sơ rủi ro: {e}")
            risk_profiles = {
                "conservative": {
                    "risk_per_trade": 1.0,
                    "stop_loss_percent_long": 1.0,
                    "stop_loss_percent_short": 1.0,
                    "risk_reward_ratio": 2.0
                },
                "moderate": {
                    "risk_per_trade": 2.0,
                    "stop_loss_percent_long": 1.5,
                    "stop_loss_percent_short": 1.5,
                    "risk_reward_ratio": 1.5
                },
                "aggressive": {
                    "risk_per_trade": 3.0,
                    "stop_loss_percent_long": 2.0,
                    "stop_loss_percent_short": 2.0,
                    "risk_reward_ratio": 1.2
                }
            }
    else:
        # Hồ sơ rủi ro mặc định
        risk_profiles = {
            "conservative": {
                "risk_per_trade": 1.0,
                "stop_loss_percent_long": 1.0,
                "stop_loss_percent_short": 1.0,
                "risk_reward_ratio": 2.0
            },
            "moderate": {
                "risk_per_trade": 2.0,
                "stop_loss_percent_long": 1.5,
                "stop_loss_percent_short": 1.5,
                "risk_reward_ratio": 1.5
            },
            "aggressive": {
                "risk_per_trade": 3.0,
                "stop_loss_percent_long": 2.0,
                "stop_loss_percent_short": 2.0,
                "risk_reward_ratio": 1.2
            }
        }
    
    # Khởi tạo simulator
    simulator = MarketTestSimulator(
        base_data_file=args.data,
        symbol=args.symbol,
        timeframe=args.timeframe,
        initial_balance=args.balance,
        trading_strategies=strategies,
        risk_profiles=risk_profiles
    )
    
    # Chạy các bài test
    results = simulator.run_multi_scenario_test(
        scenarios=args.scenarios,
        days=args.days,
        parallel=not args.no_parallel
    )
    
    # Tạo báo cáo tổng hợp
    summary_report = simulator.generate_summary_report()
    
    if summary_report:
        print(f"Báo cáo tổng hợp: {summary_report}")
    
    print(f"Hoàn thành {len(results)} bài test!")

if __name__ == "__main__":
    main()