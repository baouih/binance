#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiểm thử nhiều chiến lược trên nhiều cặp tiền và khung thời gian

Script này sử dụng dữ liệu mẫu để kiểm thử hiệu suất của nhiều chiến lược giao dịch 
khác nhau trên nhiều cặp tiền và khung thời gian, từ đó lựa chọn chiến lược tối ưu.
"""

import os
import sys
import argparse
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_strategy_backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_sample_data(symbol: str, interval: str, data_dir='real_data') -> pd.DataFrame:
    """
    Tải dữ liệu mẫu từ file CSV
    
    Args:
        symbol (str): Cặp giao dịch (ví dụ: BTCUSDT)
        interval (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        data_dir (str): Thư mục chứa dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu OHLCV
    """
    # Tìm file dữ liệu mẫu
    filename = f"{data_dir}/{symbol}_{interval}_sample.csv"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(filename):
        logger.error(f"Không tìm thấy dữ liệu mẫu: {filename}")
        # Nếu chưa có sẵn dữ liệu mẫu, thử tạo dữ liệu mẫu
        try:
            from generate_sample_data import generate_price_series
            logger.info(f"Tạo dữ liệu mẫu mới cho {symbol}_{interval}...")
            df = generate_price_series(symbol=symbol, days=180, interval=interval)
            os.makedirs(data_dir, exist_ok=True)
            df.to_csv(filename, index=False)
        except Exception as e:
            logger.error(f"Không thể tạo dữ liệu mẫu: {e}")
            return None
    else:
        # Tải dữ liệu từ file CSV
        df = pd.read_csv(filename)
        logger.info(f"Đã tải dữ liệu mẫu từ {filename}: {len(df)} dòng")
        
    # Chuyển đổi timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
    
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo
    """
    # Tạo bản sao để tránh warning
    result = df.copy()
    
    # RSI (14 periods)
    delta = result['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    result['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = result['close'].ewm(span=12, adjust=False).mean()
    ema26 = result['close'].ewm(span=26, adjust=False).mean()
    result['macd'] = ema12 - ema26
    result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
    result['macd_hist'] = result['macd'] - result['macd_signal']
    
    # Bollinger Bands
    result['sma20'] = result['close'].rolling(window=20).mean()
    result['bb_middle'] = result['sma20']
    result['bb_std'] = result['close'].rolling(window=20).std()
    result['bb_upper'] = result['bb_middle'] + (result['bb_std'] * 2)
    result['bb_lower'] = result['bb_middle'] - (result['bb_std'] * 2)
    
    # EMAs
    for period in [9, 21, 50, 200]:
        result[f'ema_{period}'] = result['close'].ewm(span=period, adjust=False).mean()
    
    # ATR
    high_low = result['high'] - result['low']
    high_close = (result['high'] - result['close'].shift()).abs()
    low_close = (result['low'] - result['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    result['atr'] = true_range.rolling(window=14).mean()
    
    # Stochastic Oscillator
    period = 14
    result['lowest_low'] = result['low'].rolling(window=period).min()
    result['highest_high'] = result['high'].rolling(window=period).max()
    result['stoch_k'] = 100 * ((result['close'] - result['lowest_low']) / 
                             (result['highest_high'] - result['lowest_low']))
    result['stoch_d'] = result['stoch_k'].rolling(window=3).mean()
    
    # Loại bỏ missing values
    result.dropna(inplace=True)
    
    # Thêm một số dữ liệu thống kê
    
    # Volatility - biến động giá (độ lệch chuẩn của % thay đổi)
    result['volatility'] = result['close'].pct_change().rolling(window=14).std() * 100
    
    # Trend Strength - độ mạnh xu hướng (ADX)
    plus_dm = result['high'].diff()
    minus_dm = result['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    tr = true_range
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    result['adx'] = dx.rolling(window=14).mean()
    result['plus_di'] = plus_di
    result['minus_di'] = minus_di
    
    # Volume Metrics
    if 'volume' in result.columns:
        result['volume_sma20'] = result['volume'].rolling(window=20).mean()
        result['volume_ratio'] = result['volume'] / result['volume_sma20']
    
    # Price Momentum
    result['momentum'] = result['close'].pct_change(periods=10) * 100
    
    logger.info(f"Đã tính toán {len(result.columns) - len(df.columns)} chỉ báo kỹ thuật")
    
    return result

class Strategy:
    """Lớp cơ sở cho các chiến lược giao dịch"""
    
    def __init__(self, name: str, parameters: Dict = None):
        """
        Khởi tạo chiến lược
        
        Args:
            name (str): Tên chiến lược
            parameters (Dict): Các tham số tùy chỉnh
        """
        self.name = name
        self.parameters = parameters or {}
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Phương thức cơ sở, cần được ghi đè
        return 0
        
    def get_info(self) -> Dict:
        """
        Lấy thông tin về chiến lược
        
        Returns:
            Dict: Thông tin về chiến lược
        """
        return {
            "name": self.name,
            "parameters": self.parameters
        }

class RSIStrategy(Strategy):
    """Chiến lược dựa trên RSI"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược RSI
        
        Args:
            parameters (Dict): Các tham số tùy chỉnh
        """
        # Tham số mặc định
        default_params = {
            "rsi_period": 14,
            "overbought": 70,
            "oversold": 30,
            "use_trend_filter": True,
            "trend_ema": 50
        }
        
        # Kết hợp tham số mặc định và tham số tùy chỉnh
        params = {**default_params, **(parameters or {})}
        
        super().__init__("RSI", params)
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch dựa trên RSI
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra dữ liệu
        if 'rsi' not in df.columns:
            return 0
            
        # Lấy các giá trị
        current_rsi = df['rsi'].iloc[-1]
        previous_rsi = df['rsi'].iloc[-2] if len(df) > 1 else current_rsi
        
        # Lấy tham số từ chiến lược
        overbought = self.parameters.get("overbought", 70)
        oversold = self.parameters.get("oversold", 30)
        use_trend_filter = self.parameters.get("use_trend_filter", True)
        trend_ema = self.parameters.get("trend_ema", 50)
        
        # Khởi tạo tín hiệu
        signal = 0
        
        # Kiểm tra bộ lọc xu hướng nếu được kích hoạt
        if use_trend_filter:
            if f'ema_{trend_ema}' not in df.columns:
                return 0
                
            current_price = df['close'].iloc[-1]
            current_ema = df[f'ema_{trend_ema}'].iloc[-1]
            trend_up = current_price > current_ema
            trend_down = current_price < current_ema
        else:
            trend_up = trend_down = True
        
        # Áp dụng chiến lược RSI
        if current_rsi < oversold and previous_rsi <= current_rsi:
            # Tín hiệu mua khi RSI dưới ngưỡng oversold và đang đi lên
            if trend_up or not use_trend_filter:
                signal = 1
        elif current_rsi > overbought and previous_rsi >= current_rsi:
            # Tín hiệu bán khi RSI trên ngưỡng overbought và đang đi xuống
            if trend_down or not use_trend_filter:
                signal = -1
                
        return signal

class MACDStrategy(Strategy):
    """Chiến lược dựa trên MACD"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược MACD
        
        Args:
            parameters (Dict): Các tham số tùy chỉnh
        """
        # Tham số mặc định
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "use_histogram": True,
            "min_hist_change": 0.0
        }
        
        # Kết hợp tham số mặc định và tham số tùy chỉnh
        params = {**default_params, **(parameters or {})}
        
        super().__init__("MACD", params)
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch dựa trên MACD
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra dữ liệu
        if 'macd' not in df.columns or 'macd_signal' not in df.columns or 'macd_hist' not in df.columns:
            return 0
            
        # Lấy các giá trị
        current_macd = df['macd'].iloc[-1]
        current_signal = df['macd_signal'].iloc[-1]
        current_hist = df['macd_hist'].iloc[-1]
        
        previous_macd = df['macd'].iloc[-2] if len(df) > 1 else current_macd
        previous_signal = df['macd_signal'].iloc[-2] if len(df) > 1 else current_signal
        previous_hist = df['macd_hist'].iloc[-2] if len(df) > 1 else current_hist
        
        # Lấy tham số từ chiến lược
        use_histogram = self.parameters.get("use_histogram", True)
        min_hist_change = self.parameters.get("min_hist_change", 0.0)
        
        # Khởi tạo tín hiệu
        signal = 0
        
        # Kiểm tra tín hiệu cắt nhau
        if previous_macd < previous_signal and current_macd > current_signal:
            # MACD cắt lên trên đường tín hiệu - tín hiệu mua
            signal = 1
        elif previous_macd > previous_signal and current_macd < current_signal:
            # MACD cắt xuống dưới đường tín hiệu - tín hiệu bán
            signal = -1
            
        # Kiểm tra sự thay đổi histogram (độ mạnh của xu hướng)
        if use_histogram and signal == 0:
            hist_change = current_hist - previous_hist
            
            if current_hist > 0 and hist_change > min_hist_change:
                # Histogram dương và đang tăng - tín hiệu mua
                signal = 1
            elif current_hist < 0 and hist_change < -min_hist_change:
                # Histogram âm và đang giảm - tín hiệu bán
                signal = -1
                
        return signal

class BollingerBandsStrategy(Strategy):
    """Chiến lược dựa trên Bollinger Bands"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược Bollinger Bands
        
        Args:
            parameters (Dict): Các tham số tùy chỉnh
        """
        # Tham số mặc định
        default_params = {
            "bb_period": 20,
            "bb_std": 2.0,
            "use_bb_squeeze": True,
            "squeeze_threshold": 0.1,
            "use_price_action": True
        }
        
        # Kết hợp tham số mặc định và tham số tùy chỉnh
        params = {**default_params, **(parameters or {})}
        
        super().__init__("BollingerBands", params)
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch dựa trên Bollinger Bands
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra dữ liệu
        if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns or 'bb_middle' not in df.columns:
            return 0
            
        # Lấy các giá trị
        current_close = df['close'].iloc[-1]
        current_upper = df['bb_upper'].iloc[-1]
        current_lower = df['bb_lower'].iloc[-1]
        current_middle = df['bb_middle'].iloc[-1]
        
        previous_close = df['close'].iloc[-2] if len(df) > 1 else current_close
        previous_upper = df['bb_upper'].iloc[-2] if len(df) > 1 else current_upper
        previous_lower = df['bb_lower'].iloc[-2] if len(df) > 1 else current_lower
        
        # Lấy tham số từ chiến lược
        use_bb_squeeze = self.parameters.get("use_bb_squeeze", True)
        squeeze_threshold = self.parameters.get("squeeze_threshold", 0.1)
        use_price_action = self.parameters.get("use_price_action", True)
        
        # Khởi tạo tín hiệu
        signal = 0
        
        # Chiến lược Bollinger Bands cơ bản
        
        # Tín hiệu mua khi giá chạm hoặc phá vỡ dải dưới
        if previous_close <= previous_lower and current_close > current_lower:
            signal = 1
        # Tín hiệu bán khi giá chạm hoặc phá vỡ dải trên
        elif previous_close >= previous_upper and current_close < current_upper:
            signal = -1
            
        # Nếu không có tín hiệu và sử dụng BB squeeze
        if signal == 0 and use_bb_squeeze:
            # Tính bandwidth (độ rộng của dải)
            bandwidth = (current_upper - current_lower) / current_middle
            previous_bandwidth = (previous_upper - previous_lower) / current_middle
            
            # Phát hiện BB squeeze (dải bị thắt chặt)
            if bandwidth < squeeze_threshold and bandwidth < previous_bandwidth:
                # Thắt chặt dải + giá trên dải giữa = tín hiệu mua tiềm năng
                if current_close > current_middle:
                    signal = 1
                # Thắt chặt dải + giá dưới dải giữa = tín hiệu bán tiềm năng
                elif current_close < current_middle:
                    signal = -1
                    
        # Nếu vẫn không có tín hiệu và sử dụng price action
        if signal == 0 and use_price_action:
            # Tín hiệu oversold (quá bán)
            if current_close < current_lower:
                signal = 1
            # Tín hiệu overbought (quá mua)
            elif current_close > current_upper:
                signal = -1
                
        return signal

class StochasticStrategy(Strategy):
    """Chiến lược dựa trên Stochastic Oscillator"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược Stochastic
        
        Args:
            parameters (Dict): Các tham số tùy chỉnh
        """
        # Tham số mặc định
        default_params = {
            "k_period": 14,
            "d_period": 3,
            "overbought": 80,
            "oversold": 20,
            "use_crossover": True
        }
        
        # Kết hợp tham số mặc định và tham số tùy chỉnh
        params = {**default_params, **(parameters or {})}
        
        super().__init__("Stochastic", params)
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch dựa trên Stochastic Oscillator
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra dữ liệu
        if 'stoch_k' not in df.columns or 'stoch_d' not in df.columns:
            return 0
            
        # Lấy các giá trị
        current_k = df['stoch_k'].iloc[-1]
        current_d = df['stoch_d'].iloc[-1]
        
        previous_k = df['stoch_k'].iloc[-2] if len(df) > 1 else current_k
        previous_d = df['stoch_d'].iloc[-2] if len(df) > 1 else current_d
        
        # Lấy tham số từ chiến lược
        overbought = self.parameters.get("overbought", 80)
        oversold = self.parameters.get("oversold", 20)
        use_crossover = self.parameters.get("use_crossover", True)
        
        # Khởi tạo tín hiệu
        signal = 0
        
        # Chiến lược Stochastic cơ bản
        
        # Sử dụng tín hiệu cắt nhau
        if use_crossover:
            # Tín hiệu mua khi %K cắt lên trên %D trong vùng oversold
            if previous_k < previous_d and current_k > current_d and current_k < oversold:
                signal = 1
            # Tín hiệu bán khi %K cắt xuống dưới %D trong vùng overbought
            elif previous_k > previous_d and current_k < current_d and current_k > overbought:
                signal = -1
        else:
            # Tín hiệu đơn giản dựa trên ngưỡng
            if current_k < oversold and previous_k < current_k:
                # Stochastic dưới ngưỡng oversold và đang đi lên - tín hiệu mua
                signal = 1
            elif current_k > overbought and previous_k > current_k:
                # Stochastic trên ngưỡng overbought và đang đi xuống - tín hiệu bán
                signal = -1
                
        return signal

class EMACrossStrategy(Strategy):
    """Chiến lược dựa trên cắt nhau của 2 đường EMA"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược EMA Cross
        
        Args:
            parameters (Dict): Các tham số tùy chỉnh
        """
        # Tham số mặc định
        default_params = {
            "fast_ema": 9,
            "slow_ema": 21,
            "use_confirmation": True,
            "confirmation_periods": 2
        }
        
        # Kết hợp tham số mặc định và tham số tùy chỉnh
        params = {**default_params, **(parameters or {})}
        
        super().__init__("EMACross", params)
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch dựa trên cắt nhau của 2 đường EMA
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Lấy tham số từ chiến lược
        fast_ema = self.parameters.get("fast_ema", 9)
        slow_ema = self.parameters.get("slow_ema", 21)
        use_confirmation = self.parameters.get("use_confirmation", True)
        confirmation_periods = self.parameters.get("confirmation_periods", 2)
        
        # Kiểm tra dữ liệu
        fast_col = f'ema_{fast_ema}'
        slow_col = f'ema_{slow_ema}'
        
        if fast_col not in df.columns or slow_col not in df.columns:
            return 0
            
        # Lấy các giá trị
        current_fast = df[fast_col].iloc[-1]
        current_slow = df[slow_col].iloc[-1]
        
        # Khởi tạo tín hiệu
        signal = 0
        
        # Chiến lược EMA Cross cơ bản
        
        # Tín hiệu cắt nhau đơn giản
        if not use_confirmation:
            previous_fast = df[fast_col].iloc[-2] if len(df) > 1 else current_fast
            previous_slow = df[slow_col].iloc[-2] if len(df) > 1 else current_slow
            
            # Tín hiệu mua khi EMA nhanh cắt lên trên EMA chậm
            if previous_fast < previous_slow and current_fast > current_slow:
                signal = 1
            # Tín hiệu bán khi EMA nhanh cắt xuống dưới EMA chậm
            elif previous_fast > previous_slow and current_fast < current_slow:
                signal = -1
        else:
            # Sử dụng xác nhận qua nhiều nến
            if len(df) > confirmation_periods:
                # Xác nhận xu hướng tăng
                if current_fast > current_slow:
                    # Kiểm tra EMA nhanh cắt lên trên EMA chậm trong khoảng xác nhận
                    cross_up = False
                    for i in range(1, confirmation_periods + 1):
                        if i < len(df) and df[fast_col].iloc[-i-1] < df[slow_col].iloc[-i-1]:
                            cross_up = True
                            break
                    
                    if cross_up:
                        signal = 1
                
                # Xác nhận xu hướng giảm
                elif current_fast < current_slow:
                    # Kiểm tra EMA nhanh cắt xuống dưới EMA chậm trong khoảng xác nhận
                    cross_down = False
                    for i in range(1, confirmation_periods + 1):
                        if i < len(df) and df[fast_col].iloc[-i-1] > df[slow_col].iloc[-i-1]:
                            cross_down = True
                            break
                    
                    if cross_down:
                        signal = -1
                        
        return signal

class ADXStrategy(Strategy):
    """Chiến lược dựa trên ADX và Directional Movement Index"""
    
    def __init__(self, parameters: Dict = None):
        """
        Khởi tạo chiến lược ADX
        
        Args:
            parameters (Dict): Các tham số tùy chỉnh
        """
        # Tham số mặc định
        default_params = {
            "adx_period": 14,
            "adx_threshold": 25,
            "use_di_cross": True,
            "use_adx_filter": True
        }
        
        # Kết hợp tham số mặc định và tham số tùy chỉnh
        params = {**default_params, **(parameters or {})}
        
        super().__init__("ADX", params)
        
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch dựa trên ADX và DI
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        # Kiểm tra dữ liệu
        if 'adx' not in df.columns or 'plus_di' not in df.columns or 'minus_di' not in df.columns:
            return 0
            
        # Lấy các giá trị
        current_adx = df['adx'].iloc[-1]
        current_plus_di = df['plus_di'].iloc[-1]
        current_minus_di = df['minus_di'].iloc[-1]
        
        previous_plus_di = df['plus_di'].iloc[-2] if len(df) > 1 else current_plus_di
        previous_minus_di = df['minus_di'].iloc[-2] if len(df) > 1 else current_minus_di
        
        # Lấy tham số từ chiến lược
        adx_threshold = self.parameters.get("adx_threshold", 25)
        use_di_cross = self.parameters.get("use_di_cross", True)
        use_adx_filter = self.parameters.get("use_adx_filter", True)
        
        # Khởi tạo tín hiệu
        signal = 0
        
        # Chiến lược ADX cơ bản
        
        # Kiểm tra sức mạnh xu hướng
        strong_trend = not use_adx_filter or current_adx > adx_threshold
        
        if strong_trend:
            if use_di_cross:
                # Sử dụng tín hiệu cắt nhau của DI+/DI-
                if previous_plus_di < previous_minus_di and current_plus_di > current_minus_di:
                    # DI+ cắt lên trên DI- - tín hiệu mua
                    signal = 1
                elif previous_plus_di > previous_minus_di and current_plus_di < current_minus_di:
                    # DI+ cắt xuống dưới DI- - tín hiệu bán
                    signal = -1
            else:
                # Sử dụng so sánh trực tiếp DI+/DI-
                if current_plus_di > current_minus_di:
                    # DI+ lớn hơn DI- - xu hướng tăng
                    signal = 1
                elif current_plus_di < current_minus_di:
                    # DI+ nhỏ hơn DI- - xu hướng giảm
                    signal = -1
                    
        return signal

class CompositeStrategy(Strategy):
    """Chiến lược kết hợp các chiến lược khác"""
    
    def __init__(self, strategies: List[Strategy] = None, weights: Dict[str, float] = None):
        """
        Khởi tạo chiến lược kết hợp
        
        Args:
            strategies (List[Strategy]): Danh sách các chiến lược thành phần
            weights (Dict[str, float]): Trọng số cho mỗi chiến lược
        """
        super().__init__("Composite")
        self.strategies = strategies or []
        self.weights = weights or {}
        
        # Nếu không có trọng số, gán đều
        if not self.weights and self.strategies:
            equal_weight = 1.0 / len(self.strategies)
            self.weights = {s.name: equal_weight for s in self.strategies}
            
    def add_strategy(self, strategy: Strategy, weight: float = None):
        """
        Thêm chiến lược vào composite
        
        Args:
            strategy (Strategy): Chiến lược cần thêm
            weight (float): Trọng số của chiến lược
        """
        self.strategies.append(strategy)
        
        # Cập nhật trọng số
        if weight is not None:
            self.weights[strategy.name] = weight
        else:
            # Nếu không có trọng số, gán đều cho tất cả
            equal_weight = 1.0 / len(self.strategies)
            self.weights = {s.name: equal_weight for s in self.strategies}
            
    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Tạo tín hiệu giao dịch kết hợp từ nhiều chiến lược
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            int: Tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        if not self.strategies:
            return 0
            
        # Thu thập tín hiệu từ tất cả các chiến lược
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for strategy in self.strategies:
            try:
                signal = strategy.generate_signal(df)
                weight = self.weights.get(strategy.name, 1.0 / len(self.strategies))
                
                if signal > 0:
                    buy_score += weight
                elif signal < 0:
                    sell_score += weight
                    
                total_weight += weight
            except Exception as e:
                logger.error(f"Lỗi khi tạo tín hiệu từ chiến lược {strategy.name}: {e}")
                
        # Chuẩn hóa điểm số
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight
            
        # Quyết định tín hiệu cuối cùng
        signal = 0
        
        if buy_score > 0.5 and buy_score > sell_score:
            signal = 1
        elif sell_score > 0.5 and sell_score > buy_score:
            signal = -1
            
        return signal
            
    def get_strategy_signals(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Lấy tín hiệu từ từng chiến lược thành phần
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu
            
        Returns:
            Dict[str, int]: Tín hiệu của từng chiến lược
        """
        signals = {}
        
        for strategy in self.strategies:
            try:
                signal = strategy.generate_signal(df)
                signals[strategy.name] = signal
            except Exception as e:
                logger.error(f"Lỗi khi tạo tín hiệu từ chiến lược {strategy.name}: {e}")
                signals[strategy.name] = 0
                
        return signals
    
    def get_info(self) -> Dict:
        """
        Lấy thông tin về chiến lược kết hợp
        
        Returns:
            Dict: Thông tin về chiến lược kết hợp
        """
        info = super().get_info()
        info["strategies"] = [s.get_info() for s in self.strategies]
        info["weights"] = self.weights
        return info

def backtest_strategy(df: pd.DataFrame, strategy: Strategy, 
                    initial_balance: float = 10000.0,
                    risk_percentage: float = 1.0,
                    leverage: int = 5,
                    take_profit_pct: float = 15.0,
                    stop_loss_pct: float = 7.0,
                    use_trailing_stop: bool = False,
                    symbol: str = "UNKNOWN",
                    interval: str = "UNKNOWN") -> Dict:
    """
    Chạy backtest một chiến lược trên dữ liệu
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu
        strategy (Strategy): Chiến lược giao dịch
        initial_balance (float): Số dư ban đầu
        risk_percentage (float): Phần trăm rủi ro trên mỗi giao dịch
        leverage (int): Đòn bẩy
        take_profit_pct (float): Phần trăm chốt lời
        stop_loss_pct (float): Phần trăm cắt lỗ
        use_trailing_stop (bool): Sử dụng trailing stop hay không
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        
    Returns:
        Dict: Kết quả backtest
    """
    # Khởi tạo kết quả
    results = {
        "symbol": symbol,
        "interval": interval,
        "strategy": strategy.name,
        "start_date": df.index[0] if isinstance(df.index[0], str) else df.index[0].strftime('%Y-%m-%d'),
        "end_date": df.index[-1] if isinstance(df.index[-1], str) else df.index[-1].strftime('%Y-%m-%d'),
        "trades": [],
        "balance": initial_balance,
        "metrics": {}
    }
    
    # Danh sách để lưu trữ các giao dịch
    trades = []
    
    # Danh sách lưu trữ giá trị danh mục
    equity_history = [initial_balance]
    dates = [df.index[0]]
    
    # Trạng thái giao dịch hiện tại
    current_position = None
    balance = initial_balance
    
    # Chạy backtest
    for i in range(1, len(df) - 1):  # Bỏ qua nến đầu tiên và cuối cùng
        current_data = df.iloc[:i+1]
        next_data = df.iloc[i+1:i+2]  # Dữ liệu nến tiếp theo
        
        # Tạo tín hiệu
        signal = strategy.generate_signal(current_data)
        
        current_price = current_data['close'].iloc[-1]
        current_date = current_data.index[-1]
        
        # Giả định giá mở cửa của nến tiếp theo là giá vào lệnh
        entry_price = next_data['open'].iloc[0] if not next_data.empty else current_price
        
        # Cập nhật trailing stop nếu có vị thế mở
        if current_position:
            close_position = False
            exit_reason = ""
            exit_price = entry_price  # Mặc định
            
            # Kiểm tra take profit và stop loss
            if current_position['side'] == 'BUY':
                # Tính PnL nếu đóng ở giá entry_price
                pnl = (entry_price - current_position['entry_price']) * current_position['quantity'] * leverage
                current_roi = pnl / initial_balance * 100
                
                # Cập nhật trailing stop
                if use_trailing_stop and entry_price > current_position['entry_price']:
                    # Điểm kích hoạt trailing stop (khi đạt 50% đường đến take profit)
                    activation_threshold = current_position['entry_price'] + (current_position['take_profit'] - current_position['entry_price']) * 0.5
                    
                    if entry_price >= activation_threshold:
                        # Trailing stop đã được kích hoạt
                        if not current_position.get('trailing_active', False):
                            logger.debug(f"Trailing stop được kích hoạt tại {current_date}: {entry_price:.2f}")
                            current_position['trailing_active'] = True
                        
                        # Cập nhật giá cao nhất
                        if entry_price > current_position.get('highest_price', current_position['entry_price']):
                            current_position['highest_price'] = entry_price
                            
                            # Cập nhật stop loss mới (10% dưới giá cao nhất)
                            new_stop_loss = current_position['highest_price'] * (1 - 0.1)
                            
                            # Chỉ di chuyển stop loss lên, không bao giờ xuống
                            if new_stop_loss > current_position['stop_loss']:
                                current_position['stop_loss'] = new_stop_loss
                                logger.debug(f"Cập nhật trailing stop tại {current_date}: {new_stop_loss:.2f}")
                
                # Kiểm tra hit stop loss (giả định nến tiếp theo có thể xuống dưới stop loss)
                if next_data.empty or next_data['low'].iloc[0] <= current_position['stop_loss']:
                    # Đóng vị thế - STOP LOSS
                    close_position = True
                    exit_reason = 'stop_loss'
                    exit_price = current_position['stop_loss']
                    
                # Kiểm tra hit take profit (giả định nến tiếp theo có thể lên trên take profit)
                elif (next_data.empty or next_data['high'].iloc[0] >= current_position['take_profit']) and not current_position.get('trailing_active', False):
                    # Đóng vị thế - TAKE PROFIT
                    close_position = True
                    exit_reason = 'take_profit'
                    exit_price = current_position['take_profit']
                    
                # Kiểm tra tín hiệu đảo chiều mạnh
                elif signal < 0:
                    # Đóng vị thế - TÍN HIỆU
                    close_position = True
                    exit_reason = 'signal_reverse'
                    exit_price = entry_price
                    
            else:  # SELL position
                # Tính PnL nếu đóng ở giá entry_price
                pnl = (current_position['entry_price'] - entry_price) * current_position['quantity'] * leverage
                current_roi = pnl / initial_balance * 100
                
                # Cập nhật trailing stop
                if use_trailing_stop and entry_price < current_position['entry_price']:
                    # Điểm kích hoạt trailing stop (khi đạt 50% đường đến take profit)
                    activation_threshold = current_position['entry_price'] - (current_position['entry_price'] - current_position['take_profit']) * 0.5
                    
                    if entry_price <= activation_threshold:
                        # Trailing stop đã được kích hoạt
                        if not current_position.get('trailing_active', False):
                            logger.debug(f"Trailing stop được kích hoạt tại {current_date}: {entry_price:.2f}")
                            current_position['trailing_active'] = True
                        
                        # Cập nhật giá thấp nhất
                        if entry_price < current_position.get('lowest_price', current_position['entry_price']):
                            current_position['lowest_price'] = entry_price
                            
                            # Cập nhật stop loss mới (10% trên giá thấp nhất)
                            new_stop_loss = current_position['lowest_price'] * (1 + 0.1)
                            
                            # Chỉ di chuyển stop loss xuống, không bao giờ lên
                            if new_stop_loss < current_position['stop_loss']:
                                current_position['stop_loss'] = new_stop_loss
                                logger.debug(f"Cập nhật trailing stop tại {current_date}: {new_stop_loss:.2f}")
                
                # Kiểm tra hit stop loss (giả định nến tiếp theo có thể lên trên stop loss)
                if next_data.empty or next_data['high'].iloc[0] >= current_position['stop_loss']:
                    # Đóng vị thế - STOP LOSS
                    close_position = True
                    exit_reason = 'stop_loss'
                    exit_price = current_position['stop_loss']
                    
                # Kiểm tra hit take profit (giả định nến tiếp theo có thể xuống dưới take profit)
                elif (next_data.empty or next_data['low'].iloc[0] <= current_position['take_profit']) and not current_position.get('trailing_active', False):
                    # Đóng vị thế - TAKE PROFIT
                    close_position = True
                    exit_reason = 'take_profit'
                    exit_price = current_position['take_profit']
                    
                # Kiểm tra tín hiệu đảo chiều mạnh
                elif signal > 0:
                    # Đóng vị thế - TÍN HIỆU
                    close_position = True
                    exit_reason = 'signal_reverse'
                    exit_price = entry_price
                    
            if close_position:
                # Tính lợi nhuận
                if current_position['side'] == 'BUY':
                    pnl = (exit_price - current_position['entry_price']) * current_position['quantity'] * leverage
                else:  # SELL
                    pnl = (current_position['entry_price'] - exit_price) * current_position['quantity'] * leverage
                    
                balance += pnl
                roi = pnl / initial_balance * 100
                
                # Thông tin giao dịch
                trade_info = {
                    'entry_date': current_position['entry_date'],
                    'entry_price': current_position['entry_price'],
                    'exit_date': current_date,
                    'exit_price': exit_price,
                    'side': current_position['side'],
                    'quantity': current_position['quantity'],
                    'pnl': pnl,
                    'roi': roi,
                    'exit_reason': exit_reason,
                    'leverage': leverage
                }
                
                trades.append(trade_info)
                logger.debug(f"{exit_reason.upper()} ({current_position['side']}) tại {current_date}: {exit_price:.2f}, PnL: {pnl:.2f}")
                
                current_position = None
                
        # Mở vị thế mới nếu có tín hiệu và không có vị thế hiện tại
        if current_position is None and signal != 0:
            # Tính toán kích thước vị thế
            risk_amount = balance * (risk_percentage / 100)
            
            if signal > 0:  # Tín hiệu MUA
                # Tính stop loss và take profit
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                take_profit_price = entry_price * (1 + take_profit_pct / 100)
                
                # Tính số lượng dựa trên rủi ro
                price_delta = entry_price - stop_loss_price
                quantity = risk_amount / (price_delta * leverage) if price_delta > 0 else 0
                
                if quantity > 0:
                    # Mở vị thế long
                    current_position = {
                        'side': 'BUY',
                        'entry_price': entry_price,
                        'entry_date': current_date,
                        'quantity': quantity,
                        'stop_loss': stop_loss_price,
                        'take_profit': take_profit_price,
                        'highest_price': entry_price,
                        'trailing_active': False
                    }
                    
                    logger.debug(f"MỞ VỊ THẾ BUY tại {current_date}: {entry_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}")
                    
            else:  # Tín hiệu BÁN
                # Tính stop loss và take profit
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
                take_profit_price = entry_price * (1 - take_profit_pct / 100)
                
                # Tính số lượng dựa trên rủi ro
                price_delta = stop_loss_price - entry_price
                quantity = risk_amount / (price_delta * leverage) if price_delta > 0 else 0
                
                if quantity > 0:
                    # Mở vị thế short
                    current_position = {
                        'side': 'SELL',
                        'entry_price': entry_price,
                        'entry_date': current_date,
                        'quantity': quantity,
                        'stop_loss': stop_loss_price,
                        'take_profit': take_profit_price,
                        'lowest_price': entry_price,
                        'trailing_active': False
                    }
                    
                    logger.debug(f"MỞ VỊ THẾ SELL tại {current_date}: {entry_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}")
                    
        # Tính giá trị danh mục hiện tại
        current_equity = balance
        if current_position:
            # Tính lợi nhuận chưa thực hiện
            if current_position['side'] == 'BUY':
                unrealized_pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
            else:  # SELL
                unrealized_pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
                
            current_equity = balance + unrealized_pnl
            
        # Lưu giá trị danh mục
        equity_history.append(current_equity)
        dates.append(current_date)
        
    # Đóng vị thế cuối cùng nếu còn
    if current_position:
        current_price = df['close'].iloc[-1]
        current_date = df.index[-1]
        
        # Tính PnL
        if current_position['side'] == 'BUY':
            pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
        else:  # SELL
            pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
            
        balance += pnl
        roi = pnl / initial_balance * 100
        
        # Thông tin giao dịch
        trade_info = {
            'entry_date': current_position['entry_date'],
            'entry_price': current_position['entry_price'],
            'exit_date': current_date,
            'exit_price': current_price,
            'side': current_position['side'],
            'quantity': current_position['quantity'],
            'pnl': pnl,
            'roi': roi,
            'exit_reason': 'end_of_test',
            'leverage': leverage
        }
        
        trades.append(trade_info)
        logger.debug(f"ĐÓNG VỊ THẾ CUỐI CÙNG ({current_position['side']}) tại {current_date}: {current_price:.2f}, PnL: {pnl:.2f}")
        
    # Cập nhật kết quả
    results['trades'] = trades
    results['balance'] = balance
    
    # Tính toán các chỉ số hiệu suất
    if trades:
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = total_trades - profitable_trades
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_loss = sum(t['pnl'] for t in trades if t['pnl'] <= 0)
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        avg_profit = total_profit / profitable_trades if profitable_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Tính drawdown
        peak = initial_balance
        drawdowns = []
        for equity in equity_history:
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown)
            
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Tính Sharpe Ratio (simplified annual)
        returns = []
        for i in range(1, len(equity_history)):
            ret = (equity_history[i] - equity_history[i-1]) / equity_history[i-1]
            returns.append(ret)
            
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if returns else 1e-9
        
        # Ước tính số lần giao dịch trong năm
        annual_factor = 365 / ((df.index[-1] - df.index[0]).days) if hasattr(df.index[-1], 'days') else 365
        sharpe_ratio = (avg_return / std_return) * np.sqrt(len(returns) * annual_factor) if std_return > 0 else 0
        
        # ROI tổng thể
        total_roi = (balance - initial_balance) / initial_balance * 100
        
        # Lưu các metrics
        results['metrics'] = {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_roi': total_roi,
            'final_balance': balance
        }
        
        # Lưu dữ liệu về equity curve
        results['equity_history'] = equity_history
        results['dates'] = [d.strftime('%Y-%m-%d %H:%M:%S') if hasattr(d, 'strftime') else str(d) for d in dates]
        
        # In kết quả tóm tắt
        logger.info(f"=== KẾT QUẢ BACKTEST {symbol} {interval} ({strategy.name}) ===")
        logger.info(f"Tổng số giao dịch: {total_trades}")
        logger.info(f"Tỷ lệ thắng: {win_rate:.2%}")
        logger.info(f"Hệ số lợi nhuận: {profit_factor:.2f}")
        logger.info(f"Lợi nhuận trung bình: {avg_profit:.2f}")
        logger.info(f"Thua lỗ trung bình: {avg_loss:.2f}")
        logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
        logger.info(f"Sharpe ratio: {sharpe_ratio:.2f}")
        logger.info(f"ROI: {total_roi:.2f}%")
        logger.info(f"Số dư cuối: {balance:.2f}")
    else:
        logger.warning(f"Không có giao dịch nào được thực hiện với chiến lược {strategy.name}")
        results['metrics'] = {
            'total_trades': 0,
            'profitable_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'total_roi': 0,
            'final_balance': balance
        }
        
    return results

def create_equity_chart(results: List[Dict], title: str = "Backtest Results") -> str:
    """
    Tạo biểu đồ equity curve từ kết quả backtest
    
    Args:
        results (List[Dict]): Danh sách kết quả backtest
        title (str): Tiêu đề biểu đồ
        
    Returns:
        str: Đường dẫn đến file biểu đồ
    """
    # Tạo thư mục lưu biểu đồ
    chart_dir = 'backtest_charts'
    os.makedirs(chart_dir, exist_ok=True)
    
    # Tạo file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{chart_dir}/equity_comparison_{timestamp}.png"
    
    # Tạo biểu đồ
    plt.figure(figsize=(12, 8))
    
    # Vẽ đường equity cho mỗi chiến lược
    for result in results:
        if 'equity_history' in result and 'dates' in result:
            plt.plot(
                range(len(result['equity_history'])),  # Dùng chỉ số thay vì dates để khớp trục x
                result['equity_history'],
                label=f"{result['strategy']} ({result['metrics']['total_roi']:.2f}%)"
            )
    
    # Thêm chi tiết biểu đồ
    plt.title(title)
    plt.xlabel('Trading Periods')
    plt.ylabel('Account Balance')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Lưu biểu đồ
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    
    logger.info(f"Đã tạo biểu đồ so sánh: {filename}")
    
    return filename

def create_performance_summary(results: List[Dict]) -> str:
    """
    Tạo báo cáo HTML tổng hợp hiệu suất các chiến lược
    
    Args:
        results (List[Dict]): Danh sách kết quả backtest
        
    Returns:
        str: Đường dẫn đến file báo cáo
    """
    # Tạo thư mục lưu báo cáo
    report_dir = 'backtest_summary'
    os.makedirs(report_dir, exist_ok=True)
    
    # Tạo file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{report_dir}/performance_summary_{timestamp}.html"
    
    # Sắp xếp kết quả theo ROI
    sorted_results = sorted(results, key=lambda x: x['metrics']['total_roi'], reverse=True)
    
    # Tạo nội dung HTML
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Strategy Performance Summary</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f8f9fa;
            }
            h1, h2 {
                color: #336699;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                border-radius: 5px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            table, th, td {
                border: 1px solid #ddd;
            }
            th, td {
                padding: 12px;
                text-align: left;
            }
            th {
                background-color: #336699;
                color: white;
            }
            tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            .positive {
                color: green;
                font-weight: bold;
            }
            .negative {
                color: red;
                font-weight: bold;
            }
            .chart {
                width: 100%;
                height: auto;
                margin: 20px 0;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .summary {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }
            .summary-box {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                width: 30%;
                box-sizing: border-box;
            }
            .footer {
                margin-top: 30px;
                text-align: center;
                color: #666;
                font-size: 0.8em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Strategy Performance Summary</h1>
            <p>Report generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
            
            <div class="summary">
                <div class="summary-box">
                    <h3>Best Strategy</h3>
                    <p><strong>""" + sorted_results[0]['strategy'] + """</strong></p>
                    <p>ROI: <span class="positive">""" + f"{sorted_results[0]['metrics']['total_roi']:.2f}%" + """</span></p>
                    <p>Win Rate: """ + f"{sorted_results[0]['metrics']['win_rate']:.2%}" + """</p>
                </div>
                <div class="summary-box">
                    <h3>Total Strategies</h3>
                    <p><strong>""" + str(len(results)) + """</strong></p>
                    <p>Profitable: """ + str(sum(1 for r in results if r['metrics']['total_roi'] > 0)) + """</p>
                    <p>Losing: """ + str(sum(1 for r in results if r['metrics']['total_roi'] <= 0)) + """</p>
                </div>
                <div class="summary-box">
                    <h3>Test Period</h3>
                    <p><strong>""" + sorted_results[0]['start_date'] + """ to """ + sorted_results[0]['end_date'] + """</strong></p>
                    <p>Symbol: """ + sorted_results[0]['symbol'] + """</p>
                    <p>Interval: """ + sorted_results[0]['interval'] + """</p>
                </div>
            </div>
            
            <h2>Performance Comparison</h2>
            <table>
                <tr>
                    <th>Rank</th>
                    <th>Strategy</th>
                    <th>ROI (%)</th>
                    <th>Win Rate</th>
                    <th>Trades</th>
                    <th>Profit Factor</th>
                    <th>Avg Profit</th>
                    <th>Avg Loss</th>
                    <th>Max Drawdown (%)</th>
                    <th>Sharpe Ratio</th>
                    <th>Final Balance</th>
                </tr>
    """
    
    # Thêm hàng cho mỗi chiến lược
    for i, result in enumerate(sorted_results):
        metrics = result['metrics']
        roi_class = "positive" if metrics['total_roi'] > 0 else "negative"
        pf_class = "positive" if metrics['profit_factor'] > 1 else "negative"
        sr_class = "positive" if metrics['sharpe_ratio'] > 0 else "negative"
        
        html_content += f"""
                <tr>
                    <td>{i+1}</td>
                    <td>{result['strategy']}</td>
                    <td class="{roi_class}">{metrics['total_roi']:.2f}%</td>
                    <td>{metrics['win_rate']:.2%}</td>
                    <td>{metrics['total_trades']}</td>
                    <td class="{pf_class}">{metrics['profit_factor']:.2f}</td>
                    <td>{metrics['avg_profit']:.2f}</td>
                    <td>{metrics['avg_loss']:.2f}</td>
                    <td>{metrics['max_drawdown']:.2f}%</td>
                    <td class="{sr_class}">{metrics['sharpe_ratio']:.2f}</td>
                    <td>${metrics['final_balance']:.2f}</td>
                </tr>
        """
    
    # Thêm phần còn lại của HTML
    html_content += """
            </table>
            
            <h2>Equity Curves</h2>
            <img src="../%s" alt="Equity Curves" class="chart">
            
            <div class="footer">
                <p>Generated by Multi-Strategy Backtest Tool</p>
            </div>
        </div>
    </body>
    </html>
    """ % os.path.basename(create_equity_chart(sorted_results))
    
    # Lưu file HTML
    with open(filename, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Đã tạo báo cáo tổng hợp: {filename}")
    
    return filename

def run_multi_strategy_test(symbol: str, interval: str, 
                         initial_balance: float = 10000.0,
                         risk_percentage: float = 1.0,
                         leverage: int = 5,
                         use_trailing_stop: bool = False):
    """
    Chạy kiểm thử nhiều chiến lược trên một cặp tiền và khung thời gian
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        risk_percentage (float): Phần trăm rủi ro
        leverage (int): Đòn bẩy
        use_trailing_stop (bool): Sử dụng trailing stop
    """
    logger.info(f"=== MULTI-STRATEGY BACKTEST: {symbol} {interval} ===")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Rủi ro: {risk_percentage}%")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Trailing Stop: {'Enabled' if use_trailing_stop else 'Disabled'}")
    
    # Tải dữ liệu
    df = load_sample_data(symbol, interval)
    if df is None:
        logger.error(f"Không thể tải dữ liệu cho {symbol} {interval}")
        return
    
    # Tính toán các chỉ báo
    df_with_indicators = calculate_indicators(df)
    
    # Khởi tạo các chiến lược đơn lẻ
    strategies = [
        RSIStrategy({'overbought': 70, 'oversold': 30, 'use_trend_filter': True}),
        MACDStrategy({'fast_period': 12, 'slow_period': 26, 'signal_period': 9, 'use_histogram': True}),
        BollingerBandsStrategy({'bb_period': 20, 'bb_std': 2.0, 'use_bb_squeeze': True}),
        StochasticStrategy({'k_period': 14, 'd_period': 3, 'overbought': 80, 'oversold': 20}),
        EMACrossStrategy({'fast_ema': 9, 'slow_ema': 21, 'use_confirmation': True}),
        ADXStrategy({'adx_threshold': 25, 'use_di_cross': True})
    ]
    
    # Khởi tạo chiến lược kết hợp
    composite = CompositeStrategy()
    for strategy in strategies:
        composite.add_strategy(strategy)
    
    # Thêm chiến lược kết hợp vào danh sách
    strategies.append(composite)
    
    # Chạy backtest cho mỗi chiến lược
    all_results = []
    
    for strategy in strategies:
        try:
            logger.info(f"Kiểm thử chiến lược: {strategy.name}")
            result = backtest_strategy(
                df=df_with_indicators,
                strategy=strategy,
                initial_balance=initial_balance,
                risk_percentage=risk_percentage,
                leverage=leverage,
                use_trailing_stop=use_trailing_stop,
                symbol=symbol,
                interval=interval
            )
            all_results.append(result)
            
            # Lưu kết quả chi tiết
            save_detail_results(result, symbol, interval, strategy.name)
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm thử chiến lược {strategy.name}: {e}")
    
    # Tạo báo cáo tổng hợp
    if all_results:
        summary_file = create_performance_summary(all_results)
        logger.info(f"Báo cáo tổng hợp: {summary_file}")
    else:
        logger.warning("Không có kết quả kiểm thử nào để tạo báo cáo")

def save_detail_results(result: Dict, symbol: str, interval: str, strategy_name: str) -> str:
    """
    Lưu kết quả chi tiết vào file
    
    Args:
        result (Dict): Kết quả backtest
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        strategy_name (str): Tên chiến lược
        
    Returns:
        str: Đường dẫn đến file kết quả
    """
    # Tạo thư mục nếu chưa tồn tại
    result_dir = 'backtest_results'
    os.makedirs(result_dir, exist_ok=True)
    
    # Tạo tên file
    safe_strategy_name = strategy_name.replace(' ', '_').replace('/', '_')
    filename = f"{result_dir}/{symbol}_{interval}_{safe_strategy_name}_results.json"
    
    # Chuẩn bị dữ liệu để lưu (chuyển đổi các kiểu dữ liệu không hỗ trợ JSON)
    serializable_result = result.copy()
    
    # Xử lý dates nếu là đối tượng datetime
    if 'dates' in serializable_result:
        serializable_result['dates'] = [str(d) for d in serializable_result['dates']]
    
    # Xử lý các trường datetime trong danh sách giao dịch
    for trade in serializable_result['trades']:
        for field in ['entry_date', 'exit_date']:
            if field in trade and not isinstance(trade[field], str):
                try:
                    if hasattr(trade[field], 'strftime'):
                        trade[field] = trade[field].strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        trade[field] = str(trade[field])
                except:
                    trade[field] = str(trade[field])
    
    # Lưu kết quả
    with open(filename, 'w') as f:
        json.dump(serializable_result, f, indent=4)
    
    # Lưu danh sách giao dịch vào CSV
    if serializable_result['trades']:
        trades_file = f"{result_dir}/{symbol}_{interval}_{safe_strategy_name}_trades.csv"
        trades_df = pd.DataFrame(serializable_result['trades'])
        trades_df.to_csv(trades_file, index=False)
        logger.info(f"Đã lưu chi tiết giao dịch: {trades_file}")
    
    logger.info(f"Đã lưu kết quả chi tiết: {filename}")
    return filename

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Multi-Strategy Backtest Tool')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT'], help='Các cặp giao dịch cần kiểm thử')
    parser.add_argument('--intervals', nargs='+', default=['1h'], help='Các khung thời gian cần kiểm thử')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro trên mỗi giao dịch')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy')
    parser.add_argument('--trail', action='store_true', help='Sử dụng trailing stop')
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu backtest nhiều chiến lược với tham số: {args}")
    
    for symbol in args.symbols:
        for interval in args.intervals:
            try:
                run_multi_strategy_test(
                    symbol=symbol,
                    interval=interval,
                    initial_balance=args.balance,
                    risk_percentage=args.risk,
                    leverage=args.leverage,
                    use_trailing_stop=args.trail
                )
            except Exception as e:
                logger.error(f"Lỗi khi chạy backtest cho {symbol} {interval}: {e}")
    
    logger.info("Đã hoàn thành tất cả các backtest")

if __name__ == "__main__":
    main()