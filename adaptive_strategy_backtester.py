#!/usr/bin/env python3
"""
Script backtest nâng cao với chiến lược thích ứng và tự động điều chỉnh

Script này thực hiện backtest với khả năng:
1. Kết hợp nhiều chiến lược giao dịch (RSI, MACD, Bollinger, v.v.)
2. Tự động phát hiện chế độ thị trường (trending, ranging, volatile)
3. Điều chỉnh tham số chiến lược dựa trên điều kiện thị trường
4. Quản lý rủi ro động theo biến động thị trường
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_backtester')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

class MarketRegimeDetector:
    """Lớp phát hiện chế độ thị trường và chuyển đổi chiến lược phù hợp"""
    
    def __init__(self):
        """Khởi tạo bộ phát hiện chế độ thị trường"""
        self.regimes = ['trending', 'ranging', 'volatile', 'quiet']
        self.regime_probabilities = {regime: 0.0 for regime in self.regimes}
        self.current_regime = 'unknown'
        self.min_regime_duration = 5  # Số candlestick tối thiểu để xác nhận chế độ
        self.regime_history = []
    
    def detect_regime(self, df: pd.DataFrame, window: int = 20) -> str:
        """
        Phát hiện chế độ thị trường hiện tại
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            window (int): Kích thước cửa sổ để phân tích
            
        Returns:
            str: Chế độ thị trường hiện tại ('trending', 'ranging', 'volatile', 'quiet')
        """
        if len(df) < window:
            return 'unknown'
        
        # Lấy dữ liệu trong cửa sổ
        recent_data = df.iloc[-window:]
        
        # Tính các chỉ số đặc trưng
        # 1. Trend strength (Độ mạnh xu hướng)
        price_change = (recent_data['close'].iloc[-1] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
        price_direction = 1 if price_change > 0 else -1
        
        # 2. Volatility (Biến động)
        volatility = recent_data['close'].pct_change().std() * np.sqrt(window)
        
        # 3. Range width (Độ rộng biên độ)
        price_range = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean()
        
        # 4. Directional movement (Chuyển động có hướng)
        if 'adx' in recent_data.columns:
            adx_value = recent_data['adx'].iloc[-1]
        else:
            # Tính ADX nếu chưa có
            plus_dm = recent_data['high'].diff()
            minus_dm = recent_data['low'].diff() * -1
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            tr = np.maximum(
                recent_data['high'] - recent_data['low'],
                np.abs(recent_data['high'] - recent_data['close'].shift(1)),
                np.abs(recent_data['low'] - recent_data['close'].shift(1))
            )
            
            atr = tr.rolling(window=14).mean()
            plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr)
            dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di))
            adx_value = dx.rolling(window=14).mean().iloc[-1]
        
        # Tính xác suất cho từng chế độ
        trend_probability = min(abs(price_change) * 100, 1.0) * min(adx_value / 50.0, 1.0)
        range_probability = (1.0 - abs(price_change) * 10) * (1.0 - min(adx_value / 40.0, 1.0)) * min(price_range * 5, 1.0)
        volatility_probability = min(volatility * 10, 1.0)
        quiet_probability = (1.0 - volatility * 20) * (1.0 - abs(price_change) * 10)
        
        # Chuẩn hóa xác suất
        total_probability = trend_probability + range_probability + volatility_probability + quiet_probability
        
        if total_probability > 0:
            trend_probability /= total_probability
            range_probability /= total_probability
            volatility_probability /= total_probability
            quiet_probability /= total_probability
        
        # Cập nhật xác suất
        self.regime_probabilities['trending'] = trend_probability
        self.regime_probabilities['ranging'] = range_probability
        self.regime_probabilities['volatile'] = volatility_probability
        self.regime_probabilities['quiet'] = quiet_probability
        
        # Xác định chế độ có xác suất cao nhất
        regime = max(self.regime_probabilities, key=self.regime_probabilities.get)
        
        # Lưu lịch sử chế độ thị trường
        self.regime_history.append(regime)
        if len(self.regime_history) > self.min_regime_duration:
            self.regime_history.pop(0)
        
        # Xác định chế độ ổn định
        if len(self.regime_history) >= self.min_regime_duration:
            most_common_regime = max(set(self.regime_history), key=self.regime_history.count)
            count = self.regime_history.count(most_common_regime)
            
            if count >= self.min_regime_duration * 0.6:  # Nếu chiếm ít nhất 60% thời gian
                self.current_regime = most_common_regime
            else:
                self.current_regime = 'mixed'
        else:
            self.current_regime = regime
        
        return self.current_regime
    
    def get_regime_description(self, regime: str = None) -> str:
        """
        Trả về mô tả về chế độ thị trường hiện tại
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            str: Mô tả về chế độ thị trường
        """
        if regime is None:
            regime = self.current_regime
        
        descriptions = {
            'trending': 'Thị trường xu hướng - giá đang di chuyển mạnh theo một hướng',
            'ranging': 'Thị trường đi ngang - giá dao động trong một khoảng hẹp xác định',
            'volatile': 'Thị trường biến động mạnh - giá thay đổi nhanh chóng và không ổn định',
            'quiet': 'Thị trường trầm lắng - biến động thấp, khối lượng thấp',
            'mixed': 'Thị trường hỗn hợp - không có đặc điểm rõ ràng hoặc đang chuyển tiếp',
            'unknown': 'Không thể xác định - không đủ dữ liệu để phân tích'
        }
        
        return descriptions.get(regime, 'Không xác định')
    
    def get_suitable_strategies(self, regime: str = None) -> Dict[str, float]:
        """
        Trả về các chiến lược phù hợp với chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, float]: Ánh xạ chiến lược -> trọng số
        """
        if regime is None:
            regime = self.current_regime
        
        strategy_weights = {
            'rsi': 0.0,
            'macd': 0.0,
            'bbands': 0.0,
            'ema_cross': 0.0,
            'adx': 0.0,
            'volume': 0.0
        }
        
        if regime == 'trending':
            strategy_weights['macd'] = 0.35
            strategy_weights['adx'] = 0.25
            strategy_weights['ema_cross'] = 0.25
            strategy_weights['volume'] = 0.15
        elif regime == 'ranging':
            strategy_weights['rsi'] = 0.40
            strategy_weights['bbands'] = 0.40
            strategy_weights['macd'] = 0.10
            strategy_weights['volume'] = 0.10
        elif regime == 'volatile':
            strategy_weights['bbands'] = 0.30
            strategy_weights['adx'] = 0.20
            strategy_weights['macd'] = 0.20
            strategy_weights['rsi'] = 0.20
            strategy_weights['volume'] = 0.10
        elif regime == 'quiet':
            strategy_weights['ema_cross'] = 0.30
            strategy_weights['rsi'] = 0.25
            strategy_weights['macd'] = 0.25
            strategy_weights['bbands'] = 0.20
        else:  # mixed or unknown
            strategy_weights['rsi'] = 0.20
            strategy_weights['macd'] = 0.20
            strategy_weights['bbands'] = 0.20
            strategy_weights['ema_cross'] = 0.20
            strategy_weights['adx'] = 0.10
            strategy_weights['volume'] = 0.10
        
        return strategy_weights
    
    def get_optimal_parameters(self, regime: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Trả về tham số tối ưu cho từng chiến lược dựa trên chế độ thị trường
        
        Args:
            regime (str, optional): Chế độ thị trường, nếu None sẽ sử dụng chế độ hiện tại
            
        Returns:
            Dict[str, Dict[str, Any]]: Ánh xạ chiến lược -> tham số
        """
        if regime is None:
            regime = self.current_regime
        
        parameters = {}
        
        # RSI parameters
        if regime == 'trending':
            parameters['rsi'] = {'period': 14, 'overbought': 75, 'oversold': 25, 'filter_adx': True}
        elif regime == 'ranging':
            parameters['rsi'] = {'period': 14, 'overbought': 70, 'oversold': 30, 'filter_adx': False}
        elif regime == 'volatile':
            parameters['rsi'] = {'period': 10, 'overbought': 80, 'oversold': 20, 'filter_adx': True}
        elif regime == 'quiet':
            parameters['rsi'] = {'period': 21, 'overbought': 65, 'oversold': 35, 'filter_adx': False}
        else:  # mixed or unknown
            parameters['rsi'] = {'period': 14, 'overbought': 70, 'oversold': 30, 'filter_adx': False}
        
        # MACD parameters
        if regime == 'trending':
            parameters['macd'] = {'fast': 12, 'slow': 26, 'signal': 9, 'filter_adx': False}
        elif regime == 'ranging':
            parameters['macd'] = {'fast': 8, 'slow': 17, 'signal': 9, 'filter_adx': True}
        elif regime == 'volatile':
            parameters['macd'] = {'fast': 6, 'slow': 13, 'signal': 6, 'filter_adx': True}
        elif regime == 'quiet':
            parameters['macd'] = {'fast': 16, 'slow': 34, 'signal': 9, 'filter_adx': True}
        else:  # mixed or unknown
            parameters['macd'] = {'fast': 12, 'slow': 26, 'signal': 9, 'filter_adx': False}
        
        # Bollinger Bands parameters
        if regime == 'trending':
            parameters['bbands'] = {'period': 20, 'std_dev': 2.5, 'use_close': True}
        elif regime == 'ranging':
            parameters['bbands'] = {'period': 20, 'std_dev': 2.0, 'use_close': True}
        elif regime == 'volatile':
            parameters['bbands'] = {'period': 14, 'std_dev': 2.5, 'use_close': False}
        elif regime == 'quiet':
            parameters['bbands'] = {'period': 30, 'std_dev': 1.5, 'use_close': True}
        else:  # mixed or unknown
            parameters['bbands'] = {'period': 20, 'std_dev': 2.0, 'use_close': True}
        
        # EMA Cross parameters
        if regime == 'trending':
            parameters['ema_cross'] = {'fast': 9, 'slow': 21, 'filter_macd': False}
        elif regime == 'ranging':
            parameters['ema_cross'] = {'fast': 5, 'slow': 13, 'filter_macd': True}
        elif regime == 'volatile':
            parameters['ema_cross'] = {'fast': 5, 'slow': 10, 'filter_macd': True}
        elif regime == 'quiet':
            parameters['ema_cross'] = {'fast': 13, 'slow': 34, 'filter_macd': False}
        else:  # mixed or unknown
            parameters['ema_cross'] = {'fast': 9, 'slow': 21, 'filter_macd': False}
        
        # ADX parameters
        if regime == 'trending':
            parameters['adx'] = {'period': 14, 'threshold': 25}
        elif regime == 'ranging':
            parameters['adx'] = {'period': 14, 'threshold': 20}
        elif regime == 'volatile':
            parameters['adx'] = {'period': 10, 'threshold': 30}
        elif regime == 'quiet':
            parameters['adx'] = {'period': 21, 'threshold': 15}
        else:  # mixed or unknown
            parameters['adx'] = {'period': 14, 'threshold': 25}
        
        # Volume parameters
        parameters['volume'] = {'period': 20, 'threshold': 1.5}
        
        return parameters

class StrategiesManager:
    """Lớp quản lý và kết hợp nhiều chiến lược giao dịch"""
    
    def __init__(self, market_regime_detector: MarketRegimeDetector = None):
        """
        Khởi tạo quản lý chiến lược
        
        Args:
            market_regime_detector (MarketRegimeDetector, optional): Bộ phát hiện chế độ thị trường
        """
        self.market_regime_detector = market_regime_detector or MarketRegimeDetector()
        self.strategies = {}
        self.weights = {}
        self.parameters = {}
        self.last_signals = {}
        self.initialized = False
    
    def initialize_strategies(self, df: pd.DataFrame):
        """
        Khởi tạo các chiến lược với tham số mặc định
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
        """
        regime = self.market_regime_detector.detect_regime(df)
        
        self.weights = self.market_regime_detector.get_suitable_strategies(regime)
        self.parameters = self.market_regime_detector.get_optimal_parameters(regime)
        
        self.strategies = {
            'rsi': self._generate_rsi_signals,
            'macd': self._generate_macd_signals,
            'bbands': self._generate_bbands_signals,
            'ema_cross': self._generate_ema_cross_signals,
            'adx': self._generate_adx_signals,
            'volume': self._generate_volume_signals
        }
        
        self.last_signals = {name: 0 for name in self.strategies.keys()}
        self.initialized = True
    
    def update_regime_and_parameters(self, df: pd.DataFrame):
        """
        Cập nhật chế độ thị trường và tham số chiến lược
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
        """
        regime = self.market_regime_detector.detect_regime(df)
        
        # Cập nhật trọng số và tham số
        self.weights = self.market_regime_detector.get_suitable_strategies(regime)
        self.parameters = self.market_regime_detector.get_optimal_parameters(regime)
    
    def _generate_rsi_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch dựa trên RSI
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá và RSI
            
        Returns:
            np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        rsi_params = self.parameters['rsi']
        period = rsi_params.get('period', 14)
        overbought = rsi_params.get('overbought', 70)
        oversold = rsi_params.get('oversold', 30)
        filter_adx = rsi_params.get('filter_adx', False)
        
        # Tính RSI nếu chưa có
        if 'rsi' not in df.columns or period != 14:  # 14 là period mặc định
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            
            rsi_col = f'rsi_{period}'
        else:
            rsi_col = 'rsi'
        
        signals = np.zeros(len(df))
        
        # Áp dụng filter ADX nếu cần
        if filter_adx and 'adx' in df.columns:
            adx_threshold = self.parameters['adx'].get('threshold', 25)
            strong_trend = df['adx'] > adx_threshold
            
            # Tín hiệu mua: RSI vượt lên trên ngưỡng quá bán VÀ ADX > ngưỡng
            buy_signals = (df[rsi_col] > oversold) & (df[rsi_col].shift(1) <= oversold) & strong_trend
            signals[buy_signals] = 1
            
            # Tín hiệu bán: RSI vượt xuống dưới ngưỡng quá mua VÀ ADX > ngưỡng
            sell_signals = (df[rsi_col] < overbought) & (df[rsi_col].shift(1) >= overbought) & strong_trend
            signals[sell_signals] = -1
        else:
            # Tín hiệu mua: RSI vượt lên trên ngưỡng quá bán
            buy_signals = (df[rsi_col] > oversold) & (df[rsi_col].shift(1) <= oversold)
            signals[buy_signals] = 1
            
            # Tín hiệu bán: RSI vượt xuống dưới ngưỡng quá mua
            sell_signals = (df[rsi_col] < overbought) & (df[rsi_col].shift(1) >= overbought)
            signals[sell_signals] = -1
        
        return signals
    
    def _generate_macd_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch dựa trên MACD
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá và MACD
            
        Returns:
            np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        macd_params = self.parameters['macd']
        fast = macd_params.get('fast', 12)
        slow = macd_params.get('slow', 26)
        signal_period = macd_params.get('signal', 9)
        filter_adx = macd_params.get('filter_adx', False)
        
        # Tính MACD nếu chưa có hoặc tham số khác mặc định
        if 'macd' not in df.columns or 'signal' not in df.columns or fast != 12 or slow != 26 or signal_period != 9:
            df[f'ema_{fast}'] = df['close'].ewm(span=fast, adjust=False).mean()
            df[f'ema_{slow}'] = df['close'].ewm(span=slow, adjust=False).mean()
            df[f'macd_{fast}_{slow}'] = df[f'ema_{fast}'] - df[f'ema_{slow}']
            df[f'signal_{signal_period}'] = df[f'macd_{fast}_{slow}'].ewm(span=signal_period, adjust=False).mean()
            df[f'macd_hist_{fast}_{slow}_{signal_period}'] = df[f'macd_{fast}_{slow}'] - df[f'signal_{signal_period}']
            
            macd_col = f'macd_{fast}_{slow}'
            signal_col = f'signal_{signal_period}'
            hist_col = f'macd_hist_{fast}_{slow}_{signal_period}'
        else:
            macd_col = 'macd'
            signal_col = 'signal'
            hist_col = 'macd_hist'
        
        signals = np.zeros(len(df))
        
        # Áp dụng filter ADX nếu cần
        if filter_adx and 'adx' in df.columns:
            adx_threshold = self.parameters['adx'].get('threshold', 25)
            strong_trend = df['adx'] > adx_threshold
            
            # Tín hiệu mua: MACD cắt lên trên Signal Line VÀ ADX > ngưỡng
            buy_signals = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1)) & strong_trend
            signals[buy_signals] = 1
            
            # Tín hiệu bán: MACD cắt xuống dưới Signal Line VÀ ADX > ngưỡng
            sell_signals = (df[macd_col] < df[signal_col]) & (df[macd_col].shift(1) >= df[signal_col].shift(1)) & strong_trend
            signals[sell_signals] = -1
        else:
            # Tín hiệu mua: MACD cắt lên trên Signal Line
            buy_signals = (df[macd_col] > df[signal_col]) & (df[macd_col].shift(1) <= df[signal_col].shift(1))
            signals[buy_signals] = 1
            
            # Tín hiệu bán: MACD cắt xuống dưới Signal Line
            sell_signals = (df[macd_col] < df[signal_col]) & (df[macd_col].shift(1) >= df[signal_col].shift(1))
            signals[sell_signals] = -1
        
        return signals
    
    def _generate_bbands_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch dựa trên Bollinger Bands
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá và Bollinger Bands
            
        Returns:
            np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        bbands_params = self.parameters['bbands']
        period = bbands_params.get('period', 20)
        std_dev = bbands_params.get('std_dev', 2.0)
        use_close = bbands_params.get('use_close', True)
        
        # Tính Bollinger Bands nếu chưa có hoặc tham số khác mặc định
        if ('upper_band' not in df.columns or 'lower_band' not in df.columns or 
            period != 20 or std_dev != 2.0):
            
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'stddev_{period}'] = df['close'].rolling(window=period).std()
            df[f'upper_band_{period}_{std_dev}'] = df[f'sma_{period}'] + (df[f'stddev_{period}'] * std_dev)
            df[f'lower_band_{period}_{std_dev}'] = df[f'sma_{period}'] - (df[f'stddev_{period}'] * std_dev)
            
            sma_col = f'sma_{period}'
            upper_col = f'upper_band_{period}_{std_dev}'
            lower_col = f'lower_band_{period}_{std_dev}'
        else:
            sma_col = 'sma20'
            upper_col = 'upper_band'
            lower_col = 'lower_band'
        
        signals = np.zeros(len(df))
        
        if use_close:
            # Tín hiệu mua: Giá đóng cửa vượt dưới dải dưới
            buy_signals = (df['close'] < df[lower_col]) & (df['close'].shift(1) >= df[lower_col].shift(1))
            signals[buy_signals] = 1
            
            # Tín hiệu bán: Giá đóng cửa vượt trên dải trên
            sell_signals = (df['close'] > df[upper_col]) & (df['close'].shift(1) <= df[upper_col].shift(1))
            signals[sell_signals] = -1
        else:
            # Tín hiệu mua: Giá thấp nhất chạm dải dưới
            buy_signals = (df['low'] < df[lower_col]) & (df['low'].shift(1) >= df[lower_col].shift(1))
            signals[buy_signals] = 1
            
            # Tín hiệu bán: Giá cao nhất chạm dải trên
            sell_signals = (df['high'] > df[upper_col]) & (df['high'].shift(1) <= df[upper_col].shift(1))
            signals[sell_signals] = -1
        
        return signals
    
    def _generate_ema_cross_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch dựa trên EMA Cross
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        ema_params = self.parameters['ema_cross']
        fast = ema_params.get('fast', 9)
        slow = ema_params.get('slow', 21)
        filter_macd = ema_params.get('filter_macd', False)
        
        # Tính EMA nếu chưa có hoặc tham số khác mặc định
        if f'ema_{fast}' not in df.columns or f'ema_{slow}' not in df.columns:
            df[f'ema_{fast}'] = df['close'].ewm(span=fast, adjust=False).mean()
            df[f'ema_{slow}'] = df['close'].ewm(span=slow, adjust=False).mean()
        
        signals = np.zeros(len(df))
        
        # Áp dụng filter MACD nếu cần
        if filter_macd and 'macd' in df.columns and 'macd_hist' in df.columns:
            # Tín hiệu mua: EMA ngắn cắt lên trên EMA dài VÀ MACD histogram > 0
            buy_signals = ((df[f'ema_{fast}'] > df[f'ema_{slow}']) & 
                         (df[f'ema_{fast}'].shift(1) <= df[f'ema_{slow}'].shift(1)) & 
                         (df['macd_hist'] > 0))
            signals[buy_signals] = 1
            
            # Tín hiệu bán: EMA ngắn cắt xuống dưới EMA dài VÀ MACD histogram < 0
            sell_signals = ((df[f'ema_{fast}'] < df[f'ema_{slow}']) & 
                          (df[f'ema_{fast}'].shift(1) >= df[f'ema_{slow}'].shift(1)) & 
                          (df['macd_hist'] < 0))
            signals[sell_signals] = -1
        else:
            # Tín hiệu mua: EMA ngắn cắt lên trên EMA dài
            buy_signals = (df[f'ema_{fast}'] > df[f'ema_{slow}']) & (df[f'ema_{fast}'].shift(1) <= df[f'ema_{slow}'].shift(1))
            signals[buy_signals] = 1
            
            # Tín hiệu bán: EMA ngắn cắt xuống dưới EMA dài
            sell_signals = (df[f'ema_{fast}'] < df[f'ema_{slow}']) & (df[f'ema_{fast}'].shift(1) >= df[f'ema_{slow}'].shift(1))
            signals[sell_signals] = -1
        
        return signals
    
    def _generate_adx_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch dựa trên ADX và Directional Movement Index (DMI)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        adx_params = self.parameters['adx']
        period = adx_params.get('period', 14)
        threshold = adx_params.get('threshold', 25)
        
        # Tính ADX nếu chưa có hoặc tham số khác mặc định
        if 'adx' not in df.columns or 'di_plus' not in df.columns or 'di_minus' not in df.columns or period != 14:
            # Tính True Range
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift(1))
            low_close = np.abs(df['low'] - df['close'].shift(1))
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            tr = np.max(ranges, axis=1)
            
            # Tính Directional Movement
            up_move = df['high'] - df['high'].shift(1)
            down_move = df['low'].shift(1) - df['low']
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            # Tính ATR
            atr = pd.Series(tr).rolling(window=period).mean()
            
            # Tính DI+ và DI-
            plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() / atr)
            minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() / atr)
            
            # Tính Directional Index
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
            
            # Tính ADX
            adx = pd.Series(dx).rolling(window=period).mean()
            
            df[f'di_plus_{period}'] = plus_di
            df[f'di_minus_{period}'] = minus_di
            df[f'adx_{period}'] = adx
            
            adx_col = f'adx_{period}'
            di_plus_col = f'di_plus_{period}'
            di_minus_col = f'di_minus_{period}'
        else:
            adx_col = 'adx'
            di_plus_col = 'di_plus'
            di_minus_col = 'di_minus'
        
        signals = np.zeros(len(df))
        
        # Tín hiệu mua: ADX > threshold và DI+ vượt lên trên DI-
        buy_signals = ((df[adx_col] > threshold) & 
                      (df[di_plus_col] > df[di_minus_col]) & 
                      (df[di_plus_col].shift(1) <= df[di_minus_col].shift(1)))
        signals[buy_signals] = 1
        
        # Tín hiệu bán: ADX > threshold và DI- vượt lên trên DI+
        sell_signals = ((df[adx_col] > threshold) & 
                       (df[di_minus_col] > df[di_plus_col]) & 
                       (df[di_minus_col].shift(1) <= df[di_plus_col].shift(1)))
        signals[sell_signals] = -1
        
        return signals
    
    def _generate_volume_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch dựa trên biến động khối lượng giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá và khối lượng
            
        Returns:
            np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
        """
        volume_params = self.parameters['volume']
        period = volume_params.get('period', 20)
        threshold = volume_params.get('threshold', 1.5)
        
        if 'volume' not in df.columns:
            return np.zeros(len(df))
        
        # Tính volume trung bình
        df[f'avg_volume_{period}'] = df['volume'].rolling(window=period).mean()
        
        signals = np.zeros(len(df))
        
        # Khối lượng cao bất thường
        high_volume = df['volume'] > df[f'avg_volume_{period}'] * threshold
        
        # Tín hiệu mua: Khối lượng cao bất thường và giá tăng
        buy_signals = high_volume & (df['close'] > df['close'].shift(1)) & (df['close'] > df['open'])
        signals[buy_signals] = 1
        
        # Tín hiệu bán: Khối lượng cao bất thường và giá giảm
        sell_signals = high_volume & (df['close'] < df['close'].shift(1)) & (df['close'] < df['open'])
        signals[sell_signals] = -1
        
        return signals
    
    def generate_combined_signals(self, df: pd.DataFrame) -> np.array:
        """
        Tạo tín hiệu giao dịch kết hợp từ nhiều chiến lược
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá và chỉ báo
            
        Returns:
            np.array: Mảng tín hiệu kết hợp (1: mua, -1: bán, 0: không giao dịch)
        """
        if not self.initialized:
            self.initialize_strategies(df)
        
        # Cập nhật chế độ thị trường và tham số
        self.update_regime_and_parameters(df)
        
        combined_signals = np.zeros(len(df))
        total_weight = sum(self.weights.values())
        
        # Tạo tín hiệu cho từng chiến lược
        for strategy_name, strategy_func in self.strategies.items():
            # Lấy trọng số chiến lược
            weight = self.weights.get(strategy_name, 0.0)
            
            if weight > 0:
                # Tạo tín hiệu chiến lược
                signals = strategy_func(df)
                self.last_signals[strategy_name] = signals
                
                # Cộng dồn vào tín hiệu kết hợp
                combined_signals += signals * (weight / total_weight)
        
        # Chuyển đổi tín hiệu kết hợp thành quyết định cuối cùng
        result_signals = np.zeros(len(df), dtype=int)
        
        # Ngưỡng để xác định tín hiệu
        buy_threshold = 0.3  # Nếu tín hiệu > 0.3 -> Mua
        sell_threshold = -0.3  # Nếu tín hiệu < -0.3 -> Bán
        
        result_signals[combined_signals > buy_threshold] = 1
        result_signals[combined_signals < sell_threshold] = -1
        
        return result_signals
    
    def get_strategy_contribution(self) -> Dict[str, float]:
        """
        Trả về đóng góp của từng chiến lược vào quyết định cuối cùng
        
        Returns:
            Dict[str, float]: Ánh xạ chiến lược -> đóng góp
        """
        contribution = {}
        total_weight = sum(self.weights.values())
        
        for strategy_name, weight in self.weights.items():
            contribution[strategy_name] = weight / total_weight
        
        return contribution
    
    def get_last_signals_detail(self) -> Dict[str, int]:
        """
        Trả về tín hiệu gần nhất của từng chiến lược
        
        Returns:
            Dict[str, int]: Ánh xạ chiến lược -> tín hiệu (-1, 0, 1)
        """
        return {name: signals[-1] if len(signals) > 0 else 0 
                for name, signals in self.last_signals.items()}

class RiskManager:
    """Lớp quản lý rủi ro và sizing vị thế"""
    
    def __init__(self, initial_balance: float = 10000.0, max_risk_per_trade: float = 1.0):
        """
        Khởi tạo quản lý rủi ro
        
        Args:
            initial_balance (float): Số dư ban đầu
            max_risk_per_trade (float): Phần trăm rủi ro tối đa trên mỗi giao dịch
        """
        self.initial_balance = initial_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.current_balance = initial_balance
        self.risk_history = []
        self.open_positions = []
        self.closed_positions = []
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, 
                              leverage: int = 1, market_regime: str = 'neutral') -> Tuple[float, Dict]:
        """
        Tính toán kích thước vị thế dựa trên quản lý rủi ro
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            leverage (int): Đòn bẩy
            market_regime (str): Chế độ thị trường hiện tại
            
        Returns:
            Tuple[float, Dict]: (Số lượng, Thông tin sizing)
        """
        # Điều chỉnh phần trăm rủi ro dựa trên chế độ thị trường
        risk_adjustment = {
            'trending': 1.0,    # 100% rủi ro cơ bản cho thị trường xu hướng
            'ranging': 0.8,     # 80% rủi ro cơ bản cho thị trường đi ngang
            'volatile': 0.6,    # 60% rủi ro cơ bản cho thị trường biến động
            'quiet': 0.9,       # 90% rủi ro cơ bản cho thị trường trầm lắng
            'mixed': 0.7,       # 70% rủi ro cơ bản cho thị trường hỗn hợp
            'unknown': 0.5      # 50% rủi ro cơ bản nếu không xác định được
        }
        
        # Phần trăm rủi ro điều chỉnh
        adjusted_risk = self.max_risk_per_trade * risk_adjustment.get(market_regime, 1.0)
        
        # Số tiền rủi ro
        risk_amount = self.current_balance * (adjusted_risk / 100)
        
        # Khoảng cách từ entry đến stop (%)
        stop_distance_percent = abs(entry_price - stop_loss_price) / entry_price * 100
        
        # Tính số lượng
        position_value = risk_amount * leverage / (stop_distance_percent / 100)
        quantity = position_value / entry_price
        
        sizing_info = {
            'risk_percent': adjusted_risk,
            'risk_amount': risk_amount,
            'stop_distance_percent': stop_distance_percent,
            'position_value': position_value,
            'leverage': leverage,
            'quantity': quantity
        }
        
        return quantity, sizing_info
    
    def calculate_dynamic_take_profit(self, entry_price: float, stop_loss_price: float, 
                                    side: str, atr: float = None, market_regime: str = 'neutral') -> float:
        """
        Tính toán mức take profit động dựa trên chế độ thị trường và ATR
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            side (str): Hướng vị thế ('BUY' hoặc 'SELL')
            atr (float, optional): Giá trị ATR
            market_regime (str): Chế độ thị trường hiện tại
            
        Returns:
            float: Giá take profit
        """
        # Mặc định: take profit = 2x stop loss distance
        stop_distance = abs(entry_price - stop_loss_price)
        
        # Điều chỉnh dựa trên chế độ thị trường
        tp_multiplier = {
            'trending': 3.0,    # 3x stop distance cho thị trường xu hướng
            'ranging': 1.5,     # 1.5x stop distance cho thị trường đi ngang
            'volatile': 2.0,    # 2x stop distance cho thị trường biến động
            'quiet': 2.5,       # 2.5x stop distance cho thị trường trầm lắng
            'mixed': 2.0,       # 2x stop distance cho thị trường hỗn hợp
            'unknown': 2.0      # 2x stop distance mặc định
        }
        
        # Tính khoảng cách take profit
        tp_distance = stop_distance * tp_multiplier.get(market_regime, 2.0)
        
        # Nếu có ATR, điều chỉnh dựa trên biến động
        if atr:
            # Đảm bảo take profit ít nhất 1.5x ATR
            min_tp_distance = 1.5 * atr
            tp_distance = max(tp_distance, min_tp_distance)
        
        # Tính giá take profit
        if side == 'BUY':
            take_profit_price = entry_price + tp_distance
        else:  # SELL
            take_profit_price = entry_price - tp_distance
        
        return take_profit_price
    
    def update_trailing_stop(self, position_index: int, current_price: float) -> Tuple[bool, float]:
        """
        Cập nhật trailing stop cho vị thế mở
        
        Args:
            position_index (int): Chỉ số của vị thế trong danh sách vị thế mở
            current_price (float): Giá hiện tại
            
        Returns:
            Tuple[bool, float]: (Đã kích hoạt trailing stop chưa, Giá stop loss mới)
        """
        if position_index >= len(self.open_positions):
            return False, 0.0
        
        position = self.open_positions[position_index]
        
        # Kiểm tra xem có trailing stop hay không
        if not position.get('use_trailing_stop', False):
            return False, position.get('stop_loss_price', 0.0)
        
        side = position.get('side', '')
        entry_price = position.get('entry_price', 0.0)
        original_stop_loss = position.get('original_stop_loss', 0.0)
        current_stop_loss = position.get('stop_loss_price', 0.0)
        activation_pct = position.get('ts_activation_pct', 0.5)  # % lợi nhuận để kích hoạt
        callback_pct = position.get('ts_callback_pct', 0.25)  # % lùi lại từ mức cao nhất/thấp nhất
        
        # Tính % lợi nhuận hiện tại
        if side == 'BUY':
            current_profit_pct = (current_price - entry_price) / entry_price * 100
            
            # Kiểm tra xem đã đạt ngưỡng kích hoạt chưa
            if current_profit_pct >= activation_pct:
                # Tính stop loss mới
                new_stop_loss = current_price * (1 - callback_pct / 100)
                
                # Chỉ cập nhật nếu stop loss mới cao hơn stop loss hiện tại
                if new_stop_loss > current_stop_loss and new_stop_loss > original_stop_loss:
                    self.open_positions[position_index]['stop_loss_price'] = new_stop_loss
                    return True, new_stop_loss
        
        elif side == 'SELL':
            current_profit_pct = (entry_price - current_price) / entry_price * 100
            
            # Kiểm tra xem đã đạt ngưỡng kích hoạt chưa
            if current_profit_pct >= activation_pct:
                # Tính stop loss mới
                new_stop_loss = current_price * (1 + callback_pct / 100)
                
                # Chỉ cập nhật nếu stop loss mới thấp hơn stop loss hiện tại
                if (new_stop_loss < current_stop_loss or current_stop_loss == 0.0) and new_stop_loss < original_stop_loss:
                    self.open_positions[position_index]['stop_loss_price'] = new_stop_loss
                    return True, new_stop_loss
        
        return False, current_stop_loss
    
    def open_position(self, side: str, entry_price: float, quantity: float, 
                    leverage: int = 1, stop_loss_price: float = None, take_profit_price: float = None,
                    use_trailing_stop: bool = False, ts_activation_pct: float = 0.5,
                    ts_callback_pct: float = 0.25, entry_time: datetime = None) -> int:
        """
        Mở vị thế mới
        
        Args:
            side (str): Hướng vị thế ('BUY' hoặc 'SELL')
            entry_price (float): Giá vào lệnh
            quantity (float): Số lượng
            leverage (int): Đòn bẩy
            stop_loss_price (float, optional): Giá stop loss
            take_profit_price (float, optional): Giá take profit
            use_trailing_stop (bool): Sử dụng trailing stop hay không
            ts_activation_pct (float): % lợi nhuận để kích hoạt trailing stop
            ts_callback_pct (float): % lùi lại từ mức cao nhất/thấp nhất
            entry_time (datetime, optional): Thời gian vào lệnh
            
        Returns:
            int: ID của vị thế mới
        """
        if entry_time is None:
            entry_time = datetime.now()
        
        position = {
            'id': len(self.open_positions) + len(self.closed_positions),
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'leverage': leverage,
            'stop_loss_price': stop_loss_price,
            'original_stop_loss': stop_loss_price,  # Lưu stop loss ban đầu để so sánh
            'take_profit_price': take_profit_price,
            'entry_time': entry_time,
            'use_trailing_stop': use_trailing_stop,
            'ts_activation_pct': ts_activation_pct,
            'ts_callback_pct': ts_callback_pct,
            'position_value': entry_price * quantity,
            'current_price': entry_price,
            'current_pnl': 0.0,
            'current_pnl_pct': 0.0,
            'max_profit': 0.0,
            'max_drawdown': 0.0
        }
        
        self.open_positions.append(position)
        
        return position['id']
    
    def close_position(self, position_id: int, exit_price: float, exit_time: datetime = None, 
                     exit_reason: str = '') -> Dict:
        """
        Đóng vị thế
        
        Args:
            position_id (int): ID của vị thế
            exit_price (float): Giá thoát
            exit_time (datetime, optional): Thời gian thoát
            exit_reason (str): Lý do thoát
            
        Returns:
            Dict: Thông tin vị thế đã đóng
        """
        if exit_time is None:
            exit_time = datetime.now()
        
        # Tìm vị thế trong danh sách vị thế mở
        position_index = None
        for i, pos in enumerate(self.open_positions):
            if pos['id'] == position_id:
                position_index = i
                break
        
        if position_index is None:
            return None
        
        # Lấy thông tin vị thế
        position = self.open_positions.pop(position_index)
        
        # Tính lợi nhuận
        entry_price = position['entry_price']
        quantity = position['quantity']
        leverage = position['leverage']
        side = position['side']
        
        if side == 'BUY':
            pnl_pct = (exit_price - entry_price) / entry_price * 100 * leverage
        else:  # SELL
            pnl_pct = (entry_price - exit_price) / entry_price * 100 * leverage
        
        position_value = entry_price * quantity
        pnl = position_value * pnl_pct / 100
        
        # Trừ phí giao dịch (giả sử 0.075% mỗi lần vào/ra)
        fee_rate = 0.00075  # 0.075%
        fees = (position_value * fee_rate) + (quantity * exit_price * fee_rate)
        pnl -= fees
        
        # Cập nhật thông tin vị thế
        position.update({
            'exit_price': exit_price,
            'exit_time': exit_time,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'fees': fees,
            'duration': (exit_time - position['entry_time']).total_seconds() / 3600  # giờ
        })
        
        # Cập nhật số dư
        self.current_balance += pnl
        
        # Thêm vào danh sách vị thế đã đóng
        self.closed_positions.append(position)
        
        # Cập nhật lịch sử rủi ro
        self.risk_history.append({
            'position_id': position_id,
            'timestamp': exit_time,
            'balance': self.current_balance,
            'risk_amount': position_value * leverage * (self.max_risk_per_trade / 100),
            'result': pnl
        })
        
        return position
    
    def update_positions(self, current_prices: Dict[int, float], current_time: datetime = None) -> List[Dict]:
        """
        Cập nhật trạng thái tất cả các vị thế đang mở với giá hiện tại
        
        Args:
            current_prices (Dict[int, float]): Giá hiện tại cho mỗi vị thế
            current_time (datetime, optional): Thời gian hiện tại
            
        Returns:
            List[Dict]: Danh sách các vị thế đã đóng
        """
        if current_time is None:
            current_time = datetime.now()
        
        closed_positions = []
        
        # Duyệt qua từng vị thế
        for i in range(len(self.open_positions) - 1, -1, -1):
            position = self.open_positions[i]
            position_id = position['id']
            
            # Kiểm tra xem có giá cho vị thế này không
            if position_id not in current_prices:
                continue
            
            current_price = current_prices[position_id]
            position['current_price'] = current_price
            
            # Cập nhật P&L hiện tại
            side = position['side']
            entry_price = position['entry_price']
            quantity = position['quantity']
            leverage = position['leverage']
            
            if side == 'BUY':
                pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
                position['current_pnl_pct'] = pnl_pct
                position['current_pnl'] = entry_price * quantity * pnl_pct / 100
                
                # Cập nhật max profit và max drawdown
                position['max_profit'] = max(position['max_profit'], pnl_pct)
                position['max_drawdown'] = min(position['max_drawdown'], pnl_pct)
                
                # Cập nhật trailing stop
                if position['use_trailing_stop']:
                    self.update_trailing_stop(i, current_price)
                
                # Kiểm tra điều kiện đóng vị thế
                if (position['stop_loss_price'] is not None and current_price <= position['stop_loss_price']):
                    closed_position = self.close_position(position_id, current_price, current_time, 'Stop Loss')
                    closed_positions.append(closed_position)
                    continue
                
                if (position['take_profit_price'] is not None and current_price >= position['take_profit_price']):
                    closed_position = self.close_position(position_id, current_price, current_time, 'Take Profit')
                    closed_positions.append(closed_position)
                    continue
            
            else:  # SELL
                pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage
                position['current_pnl_pct'] = pnl_pct
                position['current_pnl'] = entry_price * quantity * pnl_pct / 100
                
                # Cập nhật max profit và max drawdown
                position['max_profit'] = max(position['max_profit'], pnl_pct)
                position['max_drawdown'] = min(position['max_drawdown'], pnl_pct)
                
                # Cập nhật trailing stop
                if position['use_trailing_stop']:
                    self.update_trailing_stop(i, current_price)
                
                # Kiểm tra điều kiện đóng vị thế
                if (position['stop_loss_price'] is not None and current_price >= position['stop_loss_price']):
                    closed_position = self.close_position(position_id, current_price, current_time, 'Stop Loss')
                    closed_positions.append(closed_position)
                    continue
                
                if (position['take_profit_price'] is not None and current_price <= position['take_profit_price']):
                    closed_position = self.close_position(position_id, current_price, current_time, 'Take Profit')
                    closed_positions.append(closed_position)
                    continue
        
        return closed_positions
    
    def get_performance_metrics(self) -> Dict:
        """
        Tính toán các chỉ số hiệu suất
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if not self.closed_positions:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'max_drawdown': 0.0,
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'profit_amount': 0.0,
                'profit_percent': 0.0
            }
        
        # Số giao dịch
        total_trades = len(self.closed_positions)
        
        # Giao dịch thắng/thua
        winning_trades = sum(1 for p in self.closed_positions if p['pnl'] > 0)
        losing_trades = total_trades - winning_trades
        
        # Win rate
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0.0
        
        # Lợi nhuận/Thua lỗ
        total_profit = sum(p['pnl'] for p in self.closed_positions if p['pnl'] > 0)
        total_loss = abs(sum(p['pnl'] for p in self.closed_positions if p['pnl'] <= 0))
        
        # Profit factor
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Trung bình lợi nhuận/thua lỗ
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0.0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0.0
        
        # Max drawdown
        balance_history = []
        balance = self.initial_balance
        
        for position in sorted(self.closed_positions, key=lambda p: p['exit_time']):
            balance += position['pnl']
            balance_history.append(balance)
        
        peak = self.initial_balance
        drawdowns = []
        
        for b in balance_history:
            if b > peak:
                peak = b
            dd = (peak - b) / peak * 100
            drawdowns.append(dd)
        
        max_drawdown = max(drawdowns) if drawdowns else 0.0
        
        # Tổng lợi nhuận
        profit_amount = self.current_balance - self.initial_balance
        profit_percent = profit_amount / self.initial_balance * 100
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'profit_amount': profit_amount,
            'profit_percent': profit_percent
        }

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã tính
    """
    # Tính RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Tính MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    
    # Tính Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (df['stddev'] * 2)
    df['lower_band'] = df['sma20'] - (df['stddev'] * 2)
    
    # Tính EMA
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # Tính ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    df['atr'] = true_range.rolling(14).mean()
    
    # Tính ADX
    plus_dm = df['high'].diff()
    minus_dm = df['low'].diff() * -1
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr = np.maximum(
        df['high'] - df['low'],
        np.abs(df['high'] - df['close'].shift(1)),
        np.abs(df['low'] - df['close'].shift(1))
    )
    
    atr = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
    df['di_plus'] = plus_di
    df['di_minus'] = minus_di
    
    dx = 100 * (np.abs(plus_di - minus_di) / (plus_di + minus_di))
    df['adx'] = dx.rolling(14).mean()
    
    return df

def load_data(symbol, interval, data_dir='test_data'):
    """
    Tải dữ liệu giá từ file CSV
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        data_dir (str): Thư mục dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu giá
    """
    file_path = f"{data_dir}/{symbol}/{symbol}_{interval}.csv"
    
    if not os.path.exists(file_path):
        logger.error(f"Không tìm thấy file dữ liệu: {file_path}")
        return None
    
    # Đọc dữ liệu
    df = pd.read_csv(file_path)
    
    # Chuyển đổi timestamp thành datetime và đặt làm index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Tính các chỉ báo
    df = calculate_indicators(df)
    
    logger.info(f"Đã tải {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    
    return df

def run_adaptive_backtest(
    symbol='BTCUSDT', 
    interval='1h',
    initial_balance=10000.0, 
    leverage=5, 
    risk_percentage=1.0,
    use_trailing_stop=True,
    data_dir='test_data'):
    """
    Chạy backtest với chiến lược thích ứng
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        use_trailing_stop (bool): Sử dụng trailing stop hay không
        data_dir (str): Thư mục dữ liệu
    """
    logger.info(f"=== CHẠY BACKTEST THÍCH ỨNG ===")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Rủi ro: {risk_percentage}%")
    logger.info(f"Trailing Stop: {'Bật' if use_trailing_stop else 'Tắt'}")
    
    # Tải dữ liệu
    df = load_data(symbol, interval, data_dir)
    
    if df is None or df.empty:
        logger.error("Không thể tải dữ liệu")
        return
    
    # Khởi tạo các thành phần
    market_regime_detector = MarketRegimeDetector()
    strategies_manager = StrategiesManager(market_regime_detector)
    risk_manager = RiskManager(initial_balance, risk_percentage)
    
    # Danh sách để lưu trữ giá trị vốn
    equity_curve = [initial_balance]
    dates = [df.index[0]]
    regime_history = []
    
    # Khởi tạo các biến theo dõi
    current_position = None
    position_id = None
    
    # Chạy backtest
    logger.info("Bắt đầu backtest...")
    
    # Bỏ qua một số candlesticks đầu tiên để chờ các chỉ báo có đủ dữ liệu
    start_idx = 100
    
    # Thêm cột tín hiệu để theo dõi
    df['signal'] = 0
    df['regime'] = 'unknown'
    
    for i in range(start_idx, len(df)):
        # Dữ liệu đến candlestick hiện tại
        data_so_far = df.iloc[:i+1]
        current_row = data_so_far.iloc[-1]
        current_date = data_so_far.index[-1]
        current_price = current_row['close']
        
        # Phát hiện chế độ thị trường
        regime = market_regime_detector.detect_regime(data_so_far)
        df.loc[current_date, 'regime'] = regime
        regime_history.append(regime)
        
        # Tạo tín hiệu giao dịch
        signals = strategies_manager.generate_combined_signals(data_so_far)
        current_signal = signals[-1]
        df.loc[current_date, 'signal'] = current_signal
        
        # Kiểm tra vị thế
        if current_position is None:
            # Chưa có vị thế, kiểm tra tín hiệu để mở vị thế mới
            if current_signal == 1:  # Tín hiệu mua
                # Tính toán stop loss
                atr_value = current_row['atr']
                stop_loss_price = current_price - (atr_value * 2)
                
                # Tính toán kích thước vị thế
                quantity, sizing_info = risk_manager.calculate_position_size(
                    current_price, stop_loss_price, leverage, regime)
                
                # Tính toán take profit
                take_profit_price = risk_manager.calculate_dynamic_take_profit(
                    current_price, stop_loss_price, 'BUY', atr_value, regime)
                
                # Mở vị thế
                position_id = risk_manager.open_position(
                    'BUY', current_price, quantity, leverage, 
                    stop_loss_price, take_profit_price, 
                    use_trailing_stop, 0.5, 0.2, current_date)
                
                current_position = 'BUY'
                
                logger.info(f"Mở vị thế MUA tại {current_date}: ${current_price:.2f}, "
                          f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                          f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
                
            elif current_signal == -1:  # Tín hiệu bán
                # Tính toán stop loss
                atr_value = current_row['atr']
                stop_loss_price = current_price + (atr_value * 2)
                
                # Tính toán kích thước vị thế
                quantity, sizing_info = risk_manager.calculate_position_size(
                    current_price, stop_loss_price, leverage, regime)
                
                # Tính toán take profit
                take_profit_price = risk_manager.calculate_dynamic_take_profit(
                    current_price, stop_loss_price, 'SELL', atr_value, regime)
                
                # Mở vị thế
                position_id = risk_manager.open_position(
                    'SELL', current_price, quantity, leverage, 
                    stop_loss_price, take_profit_price, 
                    use_trailing_stop, 0.5, 0.2, current_date)
                
                current_position = 'SELL'
                
                logger.info(f"Mở vị thế BÁN tại {current_date}: ${current_price:.2f}, "
                          f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                          f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
        else:
            # Đã có vị thế, kiểm tra tín hiệu đóng hoặc đảo chiều
            if ((current_position == 'BUY' and current_signal == -1) or 
                (current_position == 'SELL' and current_signal == 1)):
                
                # Đóng vị thế hiện tại do đảo chiều
                closed_position = risk_manager.close_position(
                    position_id, current_price, current_date, 'Reverse Signal')
                
                # Log kết quả
                logger.info(f"Đóng vị thế {closed_position['side']} tại {current_date}: "
                          f"${current_price:.2f}, PnL: {closed_position['pnl_pct']:.2f}%, "
                          f"${closed_position['pnl']:.2f}, Lý do: Đảo chiều")
                
                # Reset vị thế
                current_position = None
                position_id = None
                
                # Mở vị thế mới với tín hiệu mới
                if current_signal == 1:  # Tín hiệu mua
                    # Tính toán stop loss
                    atr_value = current_row['atr']
                    stop_loss_price = current_price - (atr_value * 2)
                    
                    # Tính toán kích thước vị thế
                    quantity, sizing_info = risk_manager.calculate_position_size(
                        current_price, stop_loss_price, leverage, regime)
                    
                    # Tính toán take profit
                    take_profit_price = risk_manager.calculate_dynamic_take_profit(
                        current_price, stop_loss_price, 'BUY', atr_value, regime)
                    
                    # Mở vị thế
                    position_id = risk_manager.open_position(
                        'BUY', current_price, quantity, leverage, 
                        stop_loss_price, take_profit_price, 
                        use_trailing_stop, 0.5, 0.2, current_date)
                    
                    current_position = 'BUY'
                    
                    logger.info(f"Mở vị thế MUA tại {current_date}: ${current_price:.2f}, "
                              f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                              f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
                    
                elif current_signal == -1:  # Tín hiệu bán
                    # Tính toán stop loss
                    atr_value = current_row['atr']
                    stop_loss_price = current_price + (atr_value * 2)
                    
                    # Tính toán kích thước vị thế
                    quantity, sizing_info = risk_manager.calculate_position_size(
                        current_price, stop_loss_price, leverage, regime)
                    
                    # Tính toán take profit
                    take_profit_price = risk_manager.calculate_dynamic_take_profit(
                        current_price, stop_loss_price, 'SELL', atr_value, regime)
                    
                    # Mở vị thế
                    position_id = risk_manager.open_position(
                        'SELL', current_price, quantity, leverage, 
                        stop_loss_price, take_profit_price, 
                        use_trailing_stop, 0.5, 0.2, current_date)
                    
                    current_position = 'SELL'
                    
                    logger.info(f"Mở vị thế BÁN tại {current_date}: ${current_price:.2f}, "
                              f"Số lượng: {quantity:.6f}, SL: ${stop_loss_price:.2f}, "
                              f"TP: ${take_profit_price:.2f}, Chế độ: {regime}")
            else:
                # Cập nhật vị thế
                price_dict = {position_id: current_price}
                closed_positions = risk_manager.update_positions(price_dict, current_date)
                
                # Kiểm tra xem vị thế có bị đóng không
                if closed_positions:
                    closed_position = closed_positions[0]
                    logger.info(f"Đóng vị thế {closed_position['side']} tại {current_date}: "
                              f"${current_price:.2f}, PnL: {closed_position['pnl_pct']:.2f}%, "
                              f"${closed_position['pnl']:.2f}, Lý do: {closed_position['exit_reason']}")
                    
                    # Reset vị thế
                    current_position = None
                    position_id = None
        
        # Cập nhật đường cong vốn
        if i % 24 == 0 or i == len(df) - 1:  # Cập nhật hàng ngày hoặc ở candle cuối cùng
            equity_curve.append(risk_manager.current_balance)
            dates.append(current_date)
    
    # Đóng vị thế cuối cùng nếu còn
    if current_position is not None:
        final_price = df['close'].iloc[-1]
        final_date = df.index[-1]
        
        closed_position = risk_manager.close_position(
            position_id, final_price, final_date, 'End of Backtest')
        
        logger.info(f"Đóng vị thế cuối cùng {closed_position['side']} tại {final_date}: "
                  f"${final_price:.2f}, PnL: {closed_position['pnl_pct']:.2f}%, "
                  f"${closed_position['pnl']:.2f}, Lý do: Kết thúc backtest")
    
    # Tính toán hiệu suất
    performance = risk_manager.get_performance_metrics()
    
    # Hiển thị kết quả
    logger.info(f"\n=== KẾT QUẢ BACKTEST ===")
    logger.info(f"Số giao dịch: {performance['total_trades']}")
    logger.info(f"Giao dịch thắng/thua: {performance['winning_trades']}/{performance['losing_trades']}")
    logger.info(f"Win rate: {performance['win_rate']:.2f}%")
    logger.info(f"Profit factor: {performance['profit_factor']:.2f}")
    logger.info(f"Lợi nhuận trung bình: ${performance['avg_profit']:.2f}")
    logger.info(f"Thua lỗ trung bình: ${performance['avg_loss']:.2f}")
    logger.info(f"Drawdown tối đa: {performance['max_drawdown']:.2f}%")
    logger.info(f"Số dư ban đầu: ${performance['initial_balance']:.2f}")
    logger.info(f"Số dư cuối cùng: ${performance['current_balance']:.2f}")
    logger.info(f"Lợi nhuận: ${performance['profit_amount']:.2f} ({performance['profit_percent']:.2f}%)")
    
    # Phân phối chế độ thị trường
    regime_counts = {}
    for r in regime_history:
        regime_counts[r] = regime_counts.get(r, 0) + 1
    
    total_regimes = len(regime_history)
    logger.info(f"\n=== PHÂN PHỐI CHẾ ĐỘ THỊ TRƯỜNG ===")
    for regime, count in regime_counts.items():
        logger.info(f"{regime}: {count} candles ({count/total_regimes*100:.2f}%)")
    
    # Vẽ đồ thị đường cong vốn
    plt.figure(figsize=(12, 6))
    plt.plot(dates, equity_curve)
    plt.title(f'Đường cong vốn - Chiến lược thích ứng ({symbol} {interval})')
    plt.xlabel('Thời gian')
    plt.ylabel('Vốn ($)')
    plt.grid(True)
    
    chart_path = f'backtest_charts/{symbol}_{interval}_adaptive_equity.png'
    plt.savefig(chart_path)
    logger.info(f"Đã lưu đồ thị đường cong vốn vào '{chart_path}'")
    
    # Vẽ đồ thị phân phối chế độ thị trường
    plt.figure(figsize=(10, 5))
    plt.bar(regime_counts.keys(), regime_counts.values())
    plt.title(f'Phân phối chế độ thị trường ({symbol} {interval})')
    plt.xlabel('Chế độ')
    plt.ylabel('Số lượng candles')
    plt.grid(True, axis='y')
    
    regime_chart_path = f'backtest_charts/{symbol}_{interval}_regime_distribution.png'
    plt.savefig(regime_chart_path)
    logger.info(f"Đã lưu đồ thị phân phối chế độ thị trường vào '{regime_chart_path}'")
    
    # Vẽ đồ thị giá và tín hiệu
    plt.figure(figsize=(14, 10))
    
    # Đồ thị giá và chế độ thị trường
    plt.subplot(3, 1, 1)
    plt.plot(df.index[start_idx:], df['close'].iloc[start_idx:], label='Giá đóng cửa')
    plt.plot(df.index[start_idx:], df['sma20'].iloc[start_idx:], 'b--', label='SMA 20')
    plt.plot(df.index[start_idx:], df['upper_band'].iloc[start_idx:], 'r--', label='Upper Band')
    plt.plot(df.index[start_idx:], df['lower_band'].iloc[start_idx:], 'g--', label='Lower Band')
    
    # Đánh dấu các khu vực theo chế độ thị trường
    regimes = df['regime'].iloc[start_idx:]
    for regime in ['trending', 'ranging', 'volatile', 'quiet', 'mixed']:
        mask = regimes == regime
        if mask.any():
            plt.scatter(df.index[start_idx:][mask], df['close'].iloc[start_idx:][mask], 
                      marker='.', alpha=0.5, label=f'Chế độ: {regime}')
    
    plt.title(f'Giá và chế độ thị trường - {symbol} {interval}')
    plt.ylabel('Giá ($)')
    plt.grid(True)
    plt.legend()
    
    # Đồ thị tín hiệu giao dịch
    plt.subplot(3, 1, 2)
    
    # Tìm tín hiệu mua và bán
    buy_signals = df['signal'].iloc[start_idx:] == 1
    sell_signals = df['signal'].iloc[start_idx:] == -1
    
    plt.plot(df.index[start_idx:], df['close'].iloc[start_idx:], alpha=0.3)
    plt.scatter(df.index[start_idx:][buy_signals], df['close'].iloc[start_idx:][buy_signals], 
              color='green', marker='^', s=100, label='Mua')
    plt.scatter(df.index[start_idx:][sell_signals], df['close'].iloc[start_idx:][sell_signals], 
              color='red', marker='v', s=100, label='Bán')
    
    # Vẽ các vị thế
    for position in risk_manager.closed_positions:
        if position['side'] == 'BUY':
            # Tạo arrow từ điểm vào đến điểm ra
            plt.plot([position['entry_time'], position['exit_time']], 
                   [position['entry_price'], position['exit_price']], 
                   'g-', alpha=0.5)
            
            # Đánh dấu điểm vào và ra
            plt.scatter(position['entry_time'], position['entry_price'], 
                      color='green', marker='o', s=50)
            
            # Màu điểm ra phụ thuộc vào lợi nhuận
            exit_color = 'green' if position['pnl'] > 0 else 'red'
            plt.scatter(position['exit_time'], position['exit_price'], 
                      color=exit_color, marker='x', s=50)
        else:  # SELL
            # Tạo arrow từ điểm vào đến điểm ra
            plt.plot([position['entry_time'], position['exit_time']], 
                   [position['entry_price'], position['exit_price']], 
                   'r-', alpha=0.5)
            
            # Đánh dấu điểm vào và ra
            plt.scatter(position['entry_time'], position['entry_price'], 
                      color='red', marker='o', s=50)
            
            # Màu điểm ra phụ thuộc vào lợi nhuận
            exit_color = 'green' if position['pnl'] > 0 else 'red'
            plt.scatter(position['exit_time'], position['exit_price'], 
                      color=exit_color, marker='x', s=50)
    
    plt.title('Tín hiệu giao dịch và vị thế')
    plt.ylabel('Giá ($)')
    plt.grid(True)
    plt.legend()
    
    # Đồ thị chỉ báo
    plt.subplot(3, 1, 3)
    plt.plot(df.index[start_idx:], df['rsi'].iloc[start_idx:], label='RSI')
    plt.axhline(y=70, color='r', linestyle='-', alpha=0.3)
    plt.axhline(y=30, color='g', linestyle='-', alpha=0.3)
    plt.axhline(y=50, color='gray', linestyle='--', alpha=0.3)
    
    plt.title('RSI (14)')
    plt.ylabel('RSI')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    
    signals_chart_path = f'backtest_charts/{symbol}_{interval}_adaptive_signals.png'
    plt.savefig(signals_chart_path)
    logger.info(f"Đã lưu đồ thị tín hiệu vào '{signals_chart_path}'")
    
    # Lưu giao dịch
    trades_df = pd.DataFrame([position for position in risk_manager.closed_positions])
    trades_file = f'backtest_results/{symbol}_{interval}_adaptive_trades.csv'
    
    if not trades_df.empty:
        trades_df.to_csv(trades_file, index=False)
        logger.info(f"Đã lưu lịch sử giao dịch vào '{trades_file}'")
    
    # Lưu kết quả
    results = {
        'symbol': symbol,
        'interval': interval,
        'strategy': 'adaptive',
        'initial_balance': initial_balance,
        'final_balance': risk_manager.current_balance,
        'profit': risk_manager.current_balance - initial_balance,
        'profit_percent': (risk_manager.current_balance - initial_balance) / initial_balance * 100,
        'num_trades': performance['total_trades'],
        'winning_trades': performance['winning_trades'],
        'losing_trades': performance['losing_trades'],
        'win_rate': performance['win_rate'],
        'profit_factor': performance['profit_factor'],
        'max_drawdown': performance['max_drawdown'],
        'leverage': leverage,
        'risk_percentage': risk_percentage,
        'use_trailing_stop': use_trailing_stop,
        'regime_distribution': regime_counts
    }
    
    results_file = f'backtest_results/{symbol}_{interval}_adaptive_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Đã lưu kết quả backtest vào '{results_file}'")
    
    return results

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ backtest thích ứng')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro (mặc định: 1%%)')
    parser.add_argument('--trailing_stop', type=bool, default=True, 
                       help='Sử dụng trailing stop hay không (mặc định: True)')
    parser.add_argument('--data_dir', type=str, default='test_data', 
                       help='Thư mục dữ liệu (mặc định: test_data)')
    
    args = parser.parse_args()
    
    run_adaptive_backtest(
        symbol=args.symbol,
        interval=args.interval,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        use_trailing_stop=args.trailing_stop,
        data_dir=args.data_dir
    )

if __name__ == "__main__":
    main()