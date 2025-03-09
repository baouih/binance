#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module tạo tín hiệu giao dịch nâng cao

Module này triển khai hệ thống tín hiệu giao dịch đa tầng, đa tiêu chí
với các bộ lọc nâng cao để cải thiện chất lượng tín hiệu và giảm thiểu
việc giao dịch quá mức (overtrading).
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/signal_generator.log')
    ]
)

logger = logging.getLogger('enhanced_signal_generator')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)


class EnhancedSignalGenerator:
    """
    Lớp tạo tín hiệu giao dịch nâng cao với nhiều bộ lọc và chiến lược
    """
    
    def __init__(self):
        """
        Khởi tạo lớp EnhancedSignalGenerator với các thiết lập mặc định
        """
        # Thiết lập các tham số cho chỉ báo
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        self.sma_short = 20
        self.sma_medium = 50
        self.sma_long = 200
        
        self.bb_period = 20
        self.bb_std = 2
        
        self.atr_period = 14
        
        # Các tham số cho bộ lọc nâng cao
        self.volume_min_ratio = 1.5  # Tỷ lệ volume tối thiểu so với trung bình
        self.trend_confirmation_bars = 5  # Số nến để xác nhận xu hướng
        self.signal_cooldown = 10  # Số nến chờ giữa các tín hiệu
        self.overextended_rsi_threshold = 75  # Ngưỡng RSI cho thị trường quá mức
        self.squeeze_threshold = 0.5  # Ngưỡng BB squeeze
        
        # Tham số cho quản lý vị thế
        self.sl_atr_multiplier = 1.5  # SL = entry ± ATR * multiplier
        self.tp_atr_multiplier = 3.0  # TP = entry ± ATR * multiplier
        
        # Tham số cho điều chỉnh kích thước vị thế
        self.base_position_size = 0.02  # Mặc định 2% vốn
        self.volatility_adjustment = True  # Điều chỉnh theo biến động
        self.market_regime_adjustment = True  # Điều chỉnh theo chế độ thị trường
        
        logger.info("Đã khởi tạo EnhancedSignalGenerator với các thiết lập mặc định")
    
    def process_data(self, df, base_position_size=None):
        """
        Xử lý dữ liệu và tạo tín hiệu giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            base_position_size (float, optional): Kích thước vị thế cơ bản, ghi đè thiết lập mặc định
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo và tín hiệu đã thêm
        """
        if base_position_size is not None:
            self.base_position_size = base_position_size
            logger.info(f"Đã cập nhật kích thước vị thế cơ bản thành {base_position_size}")
        
        # Sao chép DataFrame để tránh thay đổi dữ liệu gốc
        df = df.copy()
        
        # Thêm các chỉ báo
        df = self.add_indicators(df)
        
        # Xác định chế độ thị trường
        df = self.detect_market_regime(df)
        
        # Tạo tín hiệu giao dịch cơ bản
        df = self.generate_basic_signals(df)
        
        # Áp dụng các bộ lọc nâng cao
        df = self.apply_advanced_filters(df)
        
        # Tính toán giá SL và TP
        df = self.calculate_stop_levels(df)
        
        # Điều chỉnh kích thước vị thế
        df = self.adjust_position_size(df)
        
        logger.info(f"Đã xử lý xong dữ liệu với {len(df)} nến")
        
        return df
    
    def add_indicators(self, df):
        """
        Thêm các chỉ báo vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã thêm
        """
        # 1. RSI
        delta = df['close'].diff()
        gain = delta.copy()
        gain[gain < 0] = 0
        loss = delta.copy()
        loss[loss > 0] = 0
        loss = abs(loss)
        
        avg_gain = gain.rolling(window=self.rsi_period).mean()
        avg_loss = loss.rolling(window=self.rsi_period).mean()
        
        # Tránh chia cho 0
        avg_loss[avg_loss == 0] = 1e-10
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. MACD
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 3. SMA
        df['sma_short'] = df['close'].rolling(window=self.sma_short).mean()
        df['sma_medium'] = df['close'].rolling(window=self.sma_medium).mean()
        df['sma_long'] = df['close'].rolling(window=self.sma_long).mean()
        
        # 4. Bollinger Bands
        df['sma_bb'] = df['close'].rolling(window=self.bb_period).mean()
        df['std_bb'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['sma_bb'] + (df['std_bb'] * self.bb_std)
        df['bb_lower'] = df['sma_bb'] - (df['std_bb'] * self.bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['sma_bb']
        
        # 5. ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.DataFrame({"high_low": high_low, "high_close": high_close, "low_close": low_close}).max(axis=1)
        df['atr'] = tr.rolling(window=self.atr_period).mean()
        
        # 6. Volume Relative Strength
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # 7. Price Rate of Change (ROC)
        df['roc'] = df['close'].pct_change(10) * 100
        
        # 8. Parabolic SAR
        df['psar'] = self.calculate_psar(df)
        
        # 9. ADX (Average Directional Index)
        df = self.calculate_adx(df)
        
        # 10. Stochastic
        df = self.calculate_stochastic(df)
        
        # 11. Chaikin Money Flow
        df = self.calculate_cmf(df)
        
        # 12. Ichimoku Cloud
        df = self.calculate_ichimoku(df)
        
        return df
    
    def calculate_psar(self, df, af_start=0.02, af_inc=0.02, af_max=0.2):
        """
        Tính toán chỉ báo Parabolic SAR
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            af_start (float): Acceleration factor khởi đầu
            af_inc (float): Tăng acceleration factor
            af_max (float): Acceleration factor tối đa
            
        Returns:
            pd.Series: Series chứa giá trị PSAR
        """
        high = df['high']
        low = df['low']
        
        # Khởi tạo Series kết quả với giá trị NaN
        psar = pd.Series(index=df.index, dtype=float)
        
        # Khởi tạo biến
        bull = True  # Xu hướng tăng
        af = af_start  # Acceleration factor
        ep = low[0]  # Extreme point
        psar[0] = high[0]
        
        # Tính PSAR
        for i in range(1, len(df)):
            # Cập nhật PSAR
            if bull:
                psar[i] = psar[i-1] + af * (ep - psar[i-1])
                # Đảm bảo PSAR không vượt qua low của 2 nến trước
                if i >= 2:
                    psar[i] = min(psar[i], low[i-1], low[i-2])
                else:
                    psar[i] = min(psar[i], low[i-1])
                
                # Kiểm tra chuyển đổi xu hướng
                if psar[i] > low[i]:
                    bull = False
                    psar[i] = ep
                    ep = high[i]
                    af = af_start
                else:
                    # Cập nhật EP và AF
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + af_inc, af_max)
            else:
                psar[i] = psar[i-1] - af * (psar[i-1] - ep)
                # Đảm bảo PSAR không vượt qua high của 2 nến trước
                if i >= 2:
                    psar[i] = max(psar[i], high[i-1], high[i-2])
                else:
                    psar[i] = max(psar[i], high[i-1])
                
                # Kiểm tra chuyển đổi xu hướng
                if psar[i] < high[i]:
                    bull = True
                    psar[i] = ep
                    ep = low[i]
                    af = af_start
                else:
                    # Cập nhật EP và AF
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + af_inc, af_max)
        
        return psar
    
    def calculate_adx(self, df, period=14):
        """
        Tính toán chỉ báo ADX (Average Directional Index)
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            period (int): Chu kỳ cho ADX
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo ADX đã thêm
        """
        # True Range
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # +DM và -DM
        plus_dm = high.diff()
        minus_dm = low.diff()
        
        plus_dm[plus_dm < 0] = 0
        plus_dm[(high.shift(1) >= high) | (minus_dm > plus_dm)] = 0
        
        minus_dm[minus_dm > 0] = 0
        minus_dm = abs(minus_dm)
        minus_dm[(low.shift(1) <= low) | (plus_dm > minus_dm)] = 0
        
        # +DI và -DI
        plus_di = 100 * (plus_dm.rolling(window=period).sum() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).sum() / atr)
        
        # Tính ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        # Thêm vào DataFrame
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        df['adx'] = adx
        
        return df
    
    def calculate_stochastic(self, df, k_period=14, d_period=3):
        """
        Tính toán chỉ báo Stochastic
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            k_period (int): Chu kỳ cho %K
            d_period (int): Chu kỳ cho %D
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo Stochastic đã thêm
        """
        # Tính %K
        high_k = df['high'].rolling(window=k_period).max()
        low_k = df['low'].rolling(window=k_period).min()
        
        k = 100 * ((df['close'] - low_k) / (high_k - low_k))
        
        # Tính %D
        d = k.rolling(window=d_period).mean()
        
        # Thêm vào DataFrame
        df['stoch_k'] = k
        df['stoch_d'] = d
        
        return df
    
    def calculate_cmf(self, df, period=20):
        """
        Tính toán Chaikin Money Flow
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            period (int): Chu kỳ cho CMF
            
        Returns:
            pd.DataFrame: DataFrame với chỉ báo CMF đã thêm
        """
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        # Money Flow Multiplier
        mfm = ((close - low) - (high - close)) / (high - low)
        mfm = mfm.replace([np.inf, -np.inf], 0)
        mfm = mfm.fillna(0)
        
        # Money Flow Volume
        mfv = mfm * volume
        
        # Chaikin Money Flow
        cmf = mfv.rolling(window=period).sum() / volume.rolling(window=period).sum()
        
        # Thêm vào DataFrame
        df['cmf'] = cmf
        
        return df
    
    def calculate_ichimoku(self, df, tenkan_period=9, kijun_period=26, senkou_b_period=52, displacement=26):
        """
        Tính toán chỉ báo Ichimoku Cloud
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu OHLCV
            tenkan_period (int): Chu kỳ cho Tenkan-sen (Conversion Line)
            kijun_period (int): Chu kỳ cho Kijun-sen (Base Line)
            senkou_b_period (int): Chu kỳ cho Senkou Span B
            displacement (int): Displacement (lag) cho Kumo (Cloud)
            
        Returns:
            pd.DataFrame: DataFrame với các thành phần Ichimoku đã thêm
        """
        # Tenkan-sen (Conversion Line)
        tenkan_high = df['high'].rolling(window=tenkan_period).max()
        tenkan_low = df['low'].rolling(window=tenkan_period).min()
        df['tenkan_sen'] = (tenkan_high + tenkan_low) / 2
        
        # Kijun-sen (Base Line)
        kijun_high = df['high'].rolling(window=kijun_period).max()
        kijun_low = df['low'].rolling(window=kijun_period).min()
        df['kijun_sen'] = (kijun_high + kijun_low) / 2
        
        # Senkou Span A (Leading Span A)
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(displacement)
        
        # Senkou Span B (Leading Span B)
        senkou_high = df['high'].rolling(window=senkou_b_period).max()
        senkou_low = df['low'].rolling(window=senkou_b_period).min()
        df['senkou_span_b'] = ((senkou_high + senkou_low) / 2).shift(displacement)
        
        # Chikou Span (Lagging Span)
        df['chikou_span'] = df['close'].shift(-displacement)
        
        return df
    
    def detect_market_regime(self, df):
        """
        Phát hiện chế độ thị trường (Trending, Ranging, Volatile)
        
        Args:
            df (pd.DataFrame): DataFrame với các chỉ báo đã thêm
            
        Returns:
            pd.DataFrame: DataFrame với thông tin chế độ thị trường
        """
        # 1. Kiểm tra thị trường tăng (Uptrend)
        df['is_uptrend'] = (df['close'] > df['sma_medium']) & \
                          (df['sma_short'] > df['sma_medium']) & \
                          (df['macd'] > df['macd_signal'])
        
        # 2. Kiểm tra thị trường giảm (Downtrend)
        df['is_downtrend'] = (df['close'] < df['sma_medium']) & \
                            (df['sma_short'] < df['sma_medium']) & \
                            (df['macd'] < df['macd_signal'])
        
        # 3. Kiểm tra thị trường sideway (Ranging)
        # Sử dụng độ rộng Bollinger Band để xác định
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(window=20).mean() * self.squeeze_threshold
        
        df['is_ranging'] = df['bb_squeeze'] & \
                          (~df['is_uptrend']) & \
                          (~df['is_downtrend']) & \
                          (df['adx'] < 25)  # ADX thấp thường chỉ ra thị trường sideway
        
        # 4. Kiểm tra thị trường biến động (Volatile)
        df['is_volatile'] = (df['atr'] > df['atr'].rolling(window=50).mean() * 1.5) | \
                           (df['roc'].abs() > df['roc'].abs().rolling(window=50).mean() * 1.5)
        
        # 5. Xác định chế độ thị trường tổng hợp
        conditions = [
            df['is_uptrend'] & ~df['is_volatile'],
            df['is_downtrend'] & ~df['is_volatile'],
            df['is_uptrend'] & df['is_volatile'],
            df['is_downtrend'] & df['is_volatile'],
            df['is_ranging']
        ]
        
        choices = ['uptrend', 'downtrend', 'uptrend_volatile', 'downtrend_volatile', 'ranging']
        
        df['market_regime'] = np.select(conditions, choices, default='unknown')
        
        return df
    
    def generate_basic_signals(self, df):
        """
        Tạo tín hiệu giao dịch cơ bản dựa trên các chỉ báo
        
        Args:
            df (pd.DataFrame): DataFrame với các chỉ báo đã thêm
            
        Returns:
            pd.DataFrame: DataFrame với tín hiệu giao dịch cơ bản
        """
        # 1. Tín hiệu RSI
        df['rsi_buy_signal'] = (df['rsi'] < self.rsi_oversold) & (df['rsi'].shift(1) < self.rsi_oversold) & (df['rsi'] > df['rsi'].shift(1))
        df['rsi_sell_signal'] = (df['rsi'] > self.rsi_overbought) & (df['rsi'].shift(1) > self.rsi_overbought) & (df['rsi'] < df['rsi'].shift(1))
        
        # 2. Tín hiệu MACD
        df['macd_buy_signal'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        df['macd_sell_signal'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        
        # 3. Tín hiệu SMA
        df['sma_buy_signal'] = (df['close'] > df['sma_short']) & (df['close'].shift(1) <= df['sma_short'].shift(1))
        df['sma_sell_signal'] = (df['close'] < df['sma_short']) & (df['close'].shift(1) >= df['sma_short'].shift(1))
        
        # 4. Tín hiệu Bollinger Bands
        df['bb_buy_signal'] = (df['close'] < df['bb_lower']) & (df['close'].shift(1) <= df['bb_lower'].shift(1))
        df['bb_sell_signal'] = (df['close'] > df['bb_upper']) & (df['close'].shift(1) >= df['bb_upper'].shift(1))
        
        # 5. Tín hiệu ADX
        df['adx_trend_strength'] = df['adx'] > 25
        df['adx_buy_signal'] = df['adx_trend_strength'] & (df['plus_di'] > df['minus_di']) & (df['plus_di'].shift(1) <= df['minus_di'].shift(1))
        df['adx_sell_signal'] = df['adx_trend_strength'] & (df['plus_di'] < df['minus_di']) & (df['plus_di'].shift(1) >= df['minus_di'].shift(1))
        
        # 6. Tín hiệu Stochastic
        df['stoch_buy_signal'] = (df['stoch_k'] < 20) & (df['stoch_d'] < 20) & (df['stoch_k'] > df['stoch_d']) & (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1))
        df['stoch_sell_signal'] = (df['stoch_k'] > 80) & (df['stoch_d'] > 80) & (df['stoch_k'] < df['stoch_d']) & (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1))
        
        # 7. Tín hiệu Ichimoku
        df['ichimoku_buy_signal'] = (df['close'] > df['senkou_span_a']) & (df['close'] > df['senkou_span_b']) & \
                                  (df['tenkan_sen'] > df['kijun_sen']) & (df['tenkan_sen'].shift(1) <= df['kijun_sen'].shift(1))
        df['ichimoku_sell_signal'] = (df['close'] < df['senkou_span_a']) & (df['close'] < df['senkou_span_b']) & \
                                   (df['tenkan_sen'] < df['kijun_sen']) & (df['tenkan_sen'].shift(1) >= df['kijun_sen'].shift(1))
        
        # 8. Tín hiệu Parabolic SAR
        df['psar_buy_signal'] = df['close'] > df['psar']
        df['psar_sell_signal'] = df['close'] < df['psar']
        
        # 9. Tín hiệu Chaikin Money Flow
        df['cmf_buy_signal'] = (df['cmf'] > 0.05) & (df['cmf'].shift(1) <= 0.05)
        df['cmf_sell_signal'] = (df['cmf'] < -0.05) & (df['cmf'].shift(1) >= -0.05)
        
        # Tín hiệu mua và bán cơ bản (tổng hợp từ các tín hiệu trên)
        df['basic_buy_signal'] = False
        df['basic_sell_signal'] = False
        
        # Thị trường Uptrend
        uptrend_condition = df['market_regime'].isin(['uptrend', 'uptrend_volatile'])
        df.loc[uptrend_condition, 'basic_buy_signal'] = (
            df.loc[uptrend_condition, 'rsi_buy_signal'] | 
            df.loc[uptrend_condition, 'macd_buy_signal'] | 
            df.loc[uptrend_condition, 'adx_buy_signal'] |
            df.loc[uptrend_condition, 'ichimoku_buy_signal']
        )
        
        # Thị trường Downtrend
        downtrend_condition = df['market_regime'].isin(['downtrend', 'downtrend_volatile'])
        df.loc[downtrend_condition, 'basic_sell_signal'] = (
            df.loc[downtrend_condition, 'rsi_sell_signal'] | 
            df.loc[downtrend_condition, 'macd_sell_signal'] | 
            df.loc[downtrend_condition, 'adx_sell_signal'] |
            df.loc[downtrend_condition, 'ichimoku_sell_signal']
        )
        
        # Thị trường Ranging
        ranging_condition = df['market_regime'] == 'ranging'
        
        # Trong thị trường Ranging, sử dụng tín hiệu Bollinger Bands và Stochastic
        df.loc[ranging_condition, 'basic_buy_signal'] = (
            df.loc[ranging_condition, 'bb_buy_signal'] | 
            df.loc[ranging_condition, 'stoch_buy_signal']
        )
        
        df.loc[ranging_condition, 'basic_sell_signal'] = (
            df.loc[ranging_condition, 'bb_sell_signal'] | 
            df.loc[ranging_condition, 'stoch_sell_signal']
        )
        
        return df
    
    def apply_advanced_filters(self, df):
        """
        Áp dụng các bộ lọc nâng cao để cải thiện chất lượng tín hiệu
        
        Args:
            df (pd.DataFrame): DataFrame với tín hiệu cơ bản
            
        Returns:
            pd.DataFrame: DataFrame với tín hiệu đã lọc
        """
        # 1. Bộ lọc khối lượng giao dịch
        volume_filter = df['volume_ratio'] > self.volume_min_ratio
        
        # 2. Bộ lọc xác nhận xu hướng
        df['trend_confirmed'] = False
        
        # Xác nhận xu hướng tăng
        for i in range(self.trend_confirmation_bars, len(df)):
            up_count = 0
            for j in range(1, self.trend_confirmation_bars + 1):
                if df['close'].iloc[i-j] > df['sma_medium'].iloc[i-j]:
                    up_count += 1
            
            df['trend_confirmed'].iloc[i] = up_count >= self.trend_confirmation_bars * 0.7
        
        # 3. Bộ lọc tránh quá mức mua/bán
        df['overextended_market'] = (df['rsi'] > self.overextended_rsi_threshold) | (df['rsi'] < (100 - self.overextended_rsi_threshold))
        
        # 4. Bộ lọc tránh tín hiệu liên tiếp (cooldown)
        df['buy_cooldown'] = False
        df['sell_cooldown'] = False
        
        for i in range(len(df)):
            if df['basic_buy_signal'].iloc[i]:
                # Đánh dấu cooldown cho các nến tiếp theo
                end_idx = min(i + self.signal_cooldown, len(df))
                df['buy_cooldown'].iloc[i+1:end_idx] = True
            
            if df['basic_sell_signal'].iloc[i]:
                # Đánh dấu cooldown cho các nến tiếp theo
                end_idx = min(i + self.signal_cooldown, len(df))
                df['sell_cooldown'].iloc[i+1:end_idx] = True
        
        # 5. Bộ lọc phù hợp với chế độ thị trường
        df['market_appropriate_signal'] = False
        
        # Tín hiệu mua phù hợp với thị trường tăng
        uptrend_condition = df['market_regime'].isin(['uptrend', 'uptrend_volatile'])
        df.loc[uptrend_condition & df['basic_buy_signal'], 'market_appropriate_signal'] = True
        
        # Tín hiệu bán phù hợp với thị trường giảm
        downtrend_condition = df['market_regime'].isin(['downtrend', 'downtrend_volatile'])
        df.loc[downtrend_condition & df['basic_sell_signal'], 'market_appropriate_signal'] = True
        
        # Tín hiệu mua/bán phù hợp với thị trường sideway
        ranging_condition = df['market_regime'] == 'ranging'
        df.loc[ranging_condition & (df['basic_buy_signal'] | df['basic_sell_signal']), 'market_appropriate_signal'] = True
        
        # 6. Bộ lọc confluent (nhiều tín hiệu cùng một lúc)
        df['buy_signal_count'] = df['rsi_buy_signal'].astype(int) + \
                              df['macd_buy_signal'].astype(int) + \
                              df['sma_buy_signal'].astype(int) + \
                              df['bb_buy_signal'].astype(int) + \
                              df['adx_buy_signal'].astype(int) + \
                              df['stoch_buy_signal'].astype(int) + \
                              df['ichimoku_buy_signal'].astype(int) + \
                              df['psar_buy_signal'].astype(int) + \
                              df['cmf_buy_signal'].astype(int)
        
        df['sell_signal_count'] = df['rsi_sell_signal'].astype(int) + \
                               df['macd_sell_signal'].astype(int) + \
                               df['sma_sell_signal'].astype(int) + \
                               df['bb_sell_signal'].astype(int) + \
                               df['adx_sell_signal'].astype(int) + \
                               df['stoch_sell_signal'].astype(int) + \
                               df['ichimoku_sell_signal'].astype(int) + \
                               df['psar_sell_signal'].astype(int) + \
                               df['cmf_sell_signal'].astype(int)
        
        df['strong_confluence'] = (df['buy_signal_count'] >= 3) | (df['sell_signal_count'] >= 3)
        
        # Áp dụng tất cả các bộ lọc để có tín hiệu cuối cùng
        df['final_buy_signal'] = df['basic_buy_signal'] & \
                              volume_filter & \
                              ~df['overextended_market'] & \
                              ~df['buy_cooldown'] & \
                              (df['market_appropriate_signal'] | df['strong_confluence'])
        
        df['final_sell_signal'] = df['basic_sell_signal'] & \
                               volume_filter & \
                               ~df['overextended_market'] & \
                               ~df['sell_cooldown'] & \
                               (df['market_appropriate_signal'] | df['strong_confluence'])
        
        # Đảm bảo không có tín hiệu mua và bán đồng thời
        conflicting_signals = df['final_buy_signal'] & df['final_sell_signal']
        df.loc[conflicting_signals, 'final_buy_signal'] = False
        df.loc[conflicting_signals, 'final_sell_signal'] = False
        
        return df
    
    def calculate_stop_levels(self, df):
        """
        Tính toán giá stop loss và take profit cho các tín hiệu
        
        Args:
            df (pd.DataFrame): DataFrame với tín hiệu đã lọc
            
        Returns:
            pd.DataFrame: DataFrame với giá SL và TP
        """
        # Khởi tạo cột SL và TP
        df['buy_sl_price'] = np.nan
        df['buy_tp_price'] = np.nan
        df['sell_sl_price'] = np.nan
        df['sell_tp_price'] = np.nan
        
        # Tính SL và TP cho tín hiệu mua
        buy_signal_idx = df[df['final_buy_signal']].index
        for idx in buy_signal_idx:
            current_atr = df.loc[idx, 'atr']
            current_close = df.loc[idx, 'close']
            
            # SL = giá hiện tại - ATR * hệ số
            df.loc[idx, 'buy_sl_price'] = current_close - (current_atr * self.sl_atr_multiplier)
            
            # TP = giá hiện tại + ATR * hệ số
            df.loc[idx, 'buy_tp_price'] = current_close + (current_atr * self.tp_atr_multiplier)
        
        # Tính SL và TP cho tín hiệu bán
        sell_signal_idx = df[df['final_sell_signal']].index
        for idx in sell_signal_idx:
            current_atr = df.loc[idx, 'atr']
            current_close = df.loc[idx, 'close']
            
            # SL = giá hiện tại + ATR * hệ số
            df.loc[idx, 'sell_sl_price'] = current_close + (current_atr * self.sl_atr_multiplier)
            
            # TP = giá hiện tại - ATR * hệ số
            df.loc[idx, 'sell_tp_price'] = current_close - (current_atr * self.tp_atr_multiplier)
        
        return df
    
    def adjust_position_size(self, df):
        """
        Điều chỉnh kích thước vị thế dựa trên biến động thị trường và chế độ thị trường
        
        Args:
            df (pd.DataFrame): DataFrame với tín hiệu và giá SL/TP
            
        Returns:
            pd.DataFrame: DataFrame với kích thước vị thế đã điều chỉnh
        """
        # Khởi tạo cột position_size_multiplier với giá trị mặc định 1.0
        df['position_size_multiplier'] = 1.0
        
        if self.volatility_adjustment:
            # Điều chỉnh kích thước vị thế dựa trên biến động
            # Tính volatility ratio (ATR so với trung bình ATR)
            df['volatility_ratio'] = df['atr'] / df['atr'].rolling(window=50).mean()
            
            # Điều chỉnh kích thước vị thế dựa trên volatility ratio
            # Thấp hơn volatility => tăng vị thế, cao hơn volatility => giảm vị thế
            df.loc[df['volatility_ratio'] < 0.8, 'position_size_multiplier'] = 1.2
            df.loc[df['volatility_ratio'] > 1.3, 'position_size_multiplier'] = 0.8
        
        if self.market_regime_adjustment:
            # Điều chỉnh kích thước vị thế dựa trên chế độ thị trường
            
            # Thị trường tăng truyền thống => vị thế lớn hơn cho tín hiệu mua
            df.loc[(df['market_regime'] == 'uptrend') & df['final_buy_signal'], 'position_size_multiplier'] *= 1.2
            
            # Thị trường giảm truyền thống => vị thế lớn hơn cho tín hiệu bán
            df.loc[(df['market_regime'] == 'downtrend') & df['final_sell_signal'], 'position_size_multiplier'] *= 1.2
            
            # Thị trường biến động => vị thế nhỏ hơn
            df.loc[df['market_regime'].isin(['uptrend_volatile', 'downtrend_volatile']), 'position_size_multiplier'] *= 0.8
            
            # Thị trường sideway => vị thế nhỏ hơn
            df.loc[df['market_regime'] == 'ranging', 'position_size_multiplier'] *= 0.9
        
        # Đảm bảo giới hạn trên và dưới
        df['position_size_multiplier'] = np.clip(df['position_size_multiplier'], 0.5, 1.5)
        
        return df


def analyze_signal_quality(signal_generator, df, plot=True):
    """
    Phân tích chất lượng tín hiệu được tạo ra bởi EnhancedSignalGenerator
    
    Args:
        signal_generator (EnhancedSignalGenerator): Đối tượng tạo tín hiệu
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
        plot (bool): Có vẽ biểu đồ phân tích hay không
        
    Returns:
        dict: Thông tin phân tích chất lượng tín hiệu
    """
    # Xử lý dữ liệu và tạo tín hiệu
    df_with_signals = signal_generator.process_data(df)
    
    # Tổng hợp số lượng tín hiệu
    basic_buy_count = df_with_signals['basic_buy_signal'].sum()
    basic_sell_count = df_with_signals['basic_sell_signal'].sum()
    final_buy_count = df_with_signals['final_buy_signal'].sum()
    final_sell_count = df_with_signals['final_sell_signal'].sum()
    
    # Tính tỷ lệ giảm tín hiệu
    buy_signal_reduction = (basic_buy_count - final_buy_count) / basic_buy_count * 100 if basic_buy_count > 0 else 0
    sell_signal_reduction = (basic_sell_count - final_sell_count) / basic_sell_count * 100 if basic_sell_count > 0 else 0
    
    # Phân tích phân phối tín hiệu theo chế độ thị trường
    market_regime_distribution = df_with_signals['market_regime'].value_counts().to_dict()
    
    # Phân tích tín hiệu mua theo chế độ thị trường
    buy_by_regime = {}
    sell_by_regime = {}
    
    for regime in df_with_signals['market_regime'].unique():
        regime_df = df_with_signals[df_with_signals['market_regime'] == regime]
        buy_by_regime[regime] = regime_df['final_buy_signal'].sum()
        sell_by_regime[regime] = regime_df['final_sell_signal'].sum()
    
    # Tính khoảng cách trung bình giữa các tín hiệu
    buy_signal_indices = df_with_signals[df_with_signals['final_buy_signal']].index.tolist()
    sell_signal_indices = df_with_signals[df_with_signals['final_sell_signal']].index.tolist()
    
    buy_signal_distances = []
    for i in range(1, len(buy_signal_indices)):
        distance = (buy_signal_indices[i] - buy_signal_indices[i-1]).total_seconds() / 3600  # Khoảng cách theo giờ
        buy_signal_distances.append(distance)
    
    sell_signal_distances = []
    for i in range(1, len(sell_signal_indices)):
        distance = (sell_signal_indices[i] - sell_signal_indices[i-1]).total_seconds() / 3600  # Khoảng cách theo giờ
        sell_signal_distances.append(distance)
    
    avg_buy_distance = np.mean(buy_signal_distances) if buy_signal_distances else 0
    avg_sell_distance = np.mean(sell_signal_distances) if sell_signal_distances else 0
    
    # Phân tích tín hiệu xung đột (mua và bán cùng lúc)
    conflicting_signals = (df_with_signals['basic_buy_signal'] & df_with_signals['basic_sell_signal']).sum()
    
    # Kết quả phân tích
    analysis = {
        'basic_buy_count': basic_buy_count,
        'basic_sell_count': basic_sell_count,
        'final_buy_count': final_buy_count,
        'final_sell_count': final_sell_count,
        'buy_signal_reduction': buy_signal_reduction,
        'sell_signal_reduction': sell_signal_reduction,
        'market_regime_distribution': market_regime_distribution,
        'buy_by_regime': buy_by_regime,
        'sell_by_regime': sell_by_regime,
        'avg_buy_distance': avg_buy_distance,
        'avg_sell_distance': avg_sell_distance,
        'conflicting_signals': conflicting_signals
    }
    
    # Vẽ biểu đồ phân tích
    if plot:
        # Biểu đồ so sánh số lượng tín hiệu cơ bản và tín hiệu cuối cùng
        plt.figure(figsize=(12, 8))
        plt.subplot(2, 2, 1)
        plt.bar(['Basic Buy', 'Final Buy', 'Basic Sell', 'Final Sell'], 
               [basic_buy_count, final_buy_count, basic_sell_count, final_sell_count])
        plt.title('Signal Count Comparison')
        plt.ylabel('Count')
        
        # Biểu đồ phân phối chế độ thị trường
        plt.subplot(2, 2, 2)
        regimes = list(market_regime_distribution.keys())
        regime_counts = list(market_regime_distribution.values())
        plt.bar(regimes, regime_counts)
        plt.title('Market Regime Distribution')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        
        # Biểu đồ tín hiệu theo chế độ thị trường
        plt.subplot(2, 2, 3)
        regimes = list(buy_by_regime.keys())
        buy_counts = [buy_by_regime[r] for r in regimes]
        sell_counts = [sell_by_regime[r] for r in regimes]
        
        x = np.arange(len(regimes))
        width = 0.35
        
        plt.bar(x - width/2, buy_counts, width, label='Buy Signals')
        plt.bar(x + width/2, sell_counts, width, label='Sell Signals')
        plt.title('Signals by Market Regime')
        plt.xticks(x, regimes, rotation=45)
        plt.legend()
        
        # Biểu đồ khoảng cách giữa các tín hiệu
        plt.subplot(2, 2, 4)
        plt.hist(buy_signal_distances, bins=10, alpha=0.5, label='Buy Signal Distances')
        plt.hist(sell_signal_distances, bins=10, alpha=0.5, label='Sell Signal Distances')
        plt.title('Distance Between Signals (Hours)')
        plt.xlabel('Hours')
        plt.ylabel('Frequency')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('signal_quality_analysis.png')
        plt.close()
        
        # Vẽ biểu đồ giá và tín hiệu
        plt.figure(figsize=(14, 10))
        
        # Plot giá
        plt.subplot(3, 1, 1)
        plt.plot(df_with_signals.index, df_with_signals['close'], label='Close Price')
        plt.plot(df_with_signals.index, df_with_signals['sma_short'], label=f'SMA {signal_generator.sma_short}')
        plt.plot(df_with_signals.index, df_with_signals['sma_medium'], label=f'SMA {signal_generator.sma_medium}')
        
        # Đánh dấu tín hiệu mua và bán
        buy_signals = df_with_signals[df_with_signals['final_buy_signal']]
        sell_signals = df_with_signals[df_with_signals['final_sell_signal']]
        
        plt.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', s=100, label='Buy Signal')
        plt.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', s=100, label='Sell Signal')
        
        plt.title('Price Chart with Signals')
        plt.ylabel('Price')
        plt.legend()
        
        # Plot RSI
        plt.subplot(3, 1, 2)
        plt.plot(df_with_signals.index, df_with_signals['rsi'], label='RSI')
        plt.axhline(y=signal_generator.rsi_overbought, color='r', linestyle='--', label=f'Overbought ({signal_generator.rsi_overbought})')
        plt.axhline(y=signal_generator.rsi_oversold, color='g', linestyle='--', label=f'Oversold ({signal_generator.rsi_oversold})')
        plt.title('RSI Indicator')
        plt.ylabel('RSI')
        plt.legend()
        
        # Plot MACD
        plt.subplot(3, 1, 3)
        plt.plot(df_with_signals.index, df_with_signals['macd'], label='MACD')
        plt.plot(df_with_signals.index, df_with_signals['macd_signal'], label='Signal Line')
        plt.bar(df_with_signals.index, df_with_signals['macd_hist'], color='gray', alpha=0.5, label='Histogram')
        plt.title('MACD Indicator')
        plt.ylabel('MACD')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('price_and_signals.png')
        plt.close()
    
    return analysis


if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from datetime import datetime, timedelta
    
    # Tạo dữ liệu mẫu
    def generate_sample_data(days=180, trend_type='mixed'):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Khởi tạo giá cơ bản
        base_price = 100
        
        if trend_type == 'uptrend':
            # Tạo xu hướng tăng
            trend = np.linspace(0, 30, len(date_range))
            noise_level = 5
        elif trend_type == 'downtrend':
            # Tạo xu hướng giảm
            trend = np.linspace(0, -30, len(date_range))
            noise_level = 5
        elif trend_type == 'sideways':
            # Tạo xu hướng sideway
            trend = np.zeros(len(date_range))
            noise_level = 5
        elif trend_type == 'volatile':
            # Tạo xu hướng biến động
            trend = np.zeros(len(date_range))
            noise_level = 10
        else:  # 'mixed'
            # Tạo xu hướng hỗn hợp
            trend = np.zeros(len(date_range))
            
            # Thêm các đoạn xu hướng khác nhau
            segment_size = len(date_range) // 4
            
            # Xu hướng tăng
            trend[:segment_size] = np.linspace(0, 15, segment_size)
            
            # Xu hướng sideway
            trend[segment_size:2*segment_size] = np.linspace(15, 15, segment_size)
            
            # Xu hướng giảm
            trend[2*segment_size:3*segment_size] = np.linspace(15, -5, segment_size)
            
            # Xu hướng biến động
            trend[3*segment_size:] = np.linspace(-5, 10, len(date_range) - 3*segment_size)
            
            noise_level = 5
        
        # Thêm nhiễu ngẫu nhiên
        noise = np.random.normal(0, noise_level, len(date_range))
        price = base_price + trend + noise
        
        # Tạo OHLC từ giá close
        df = pd.DataFrame(index=date_range)
        df['close'] = price
        
        # Tạo giá open gần với giá close của ngày hôm trước
        df['open'] = df['close'].shift(1) * (1 + np.random.normal(0, 0.005, len(date_range)))
        df.loc[df.index[0], 'open'] = df.loc[df.index[0], 'close'] * 0.99
        
        # Tạo giá high và low
        daily_volatility = 0.02  # 2% biến động hàng ngày
        df['high'] = df[['open', 'close']].max(axis=1) * (1 + abs(np.random.normal(0, daily_volatility/2, len(date_range))))
        df['low'] = df[['open', 'close']].min(axis=1) * (1 - abs(np.random.normal(0, daily_volatility/2, len(date_range))))
        
        # Tạo volume
        base_volume = 1000000
        df['volume'] = base_volume * (1 + np.random.normal(0, 0.3, len(date_range)))
        
        # Tăng volume khi giá thay đổi nhiều
        price_change = df['close'].pct_change().abs()
        df['volume'] = df['volume'] * (1 + price_change * 10)
        
        # Điền giá trị NaN
        df = df.fillna(method='bfill')
        
        # Đảm bảo high >= open, close và low <= open, close
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)
        
        return df
    
    # Tạo dữ liệu mẫu và kiểm thử tín hiệu
    sample_data = generate_sample_data(days=180, trend_type='mixed')
    
    # Khởi tạo EnhancedSignalGenerator và xử lý dữ liệu
    signal_generator = EnhancedSignalGenerator()
    df_with_signals = signal_generator.process_data(sample_data, base_position_size=0.03)
    
    # Phân tích chất lượng tín hiệu
    analysis = analyze_signal_quality(signal_generator, sample_data, plot=True)
    
    # In kết quả phân tích
    print("=== Phân Tích Chất Lượng Tín Hiệu ===")
    print(f"Số tín hiệu mua cơ bản: {analysis['basic_buy_count']}")
    print(f"Số tín hiệu mua cuối cùng: {analysis['final_buy_count']}")
    print(f"Giảm tín hiệu mua: {analysis['buy_signal_reduction']:.2f}%")
    print(f"Số tín hiệu bán cơ bản: {analysis['basic_sell_count']}")
    print(f"Số tín hiệu bán cuối cùng: {analysis['final_sell_count']}")
    print(f"Giảm tín hiệu bán: {analysis['sell_signal_reduction']:.2f}%")
    print(f"Khoảng cách trung bình giữa các tín hiệu mua: {analysis['avg_buy_distance']:.2f} giờ")
    print(f"Khoảng cách trung bình giữa các tín hiệu bán: {analysis['avg_sell_distance']:.2f} giờ")
    print(f"Số tín hiệu xung đột: {analysis['conflicting_signals']}")
    
    print("\n=== Phân Phối Chế Độ Thị Trường ===")
    for regime, count in analysis['market_regime_distribution'].items():
        pct = count / len(sample_data) * 100
        print(f"{regime}: {count} nến ({pct:.2f}%)")
    
    print("\n=== Tín Hiệu Theo Chế Độ Thị Trường ===")
    for regime in analysis['buy_by_regime'].keys():
        buy_count = analysis['buy_by_regime'][regime]
        sell_count = analysis['sell_by_regime'][regime]
        regime_count = analysis['market_regime_distribution'].get(regime, 0)
        
        if regime_count > 0:
            buy_pct = buy_count / regime_count * 100
            sell_pct = sell_count / regime_count * 100
            print(f"{regime}: Mua {buy_count} ({buy_pct:.2f}%), Bán {sell_count} ({sell_pct:.2f}%)")
    
    print("\nHoàn thành phân tích chất lượng tín hiệu!")