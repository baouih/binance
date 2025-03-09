#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Feature Engineering nâng cao cho mô hình ML giao dịch Bitcoin

Script này cung cấp các hàm tính toán đặc trưng nâng cao cho mô hình ML,
bao gồm các chỉ báo kỹ thuật phức tạp, phân tích thanh khoản, phát hiện mẫu hình và hơn thế nữa.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional
import logging
import sys

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm tất cả các chỉ báo kỹ thuật cơ bản
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLCV
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo kỹ thuật
    """
    logger.info("Đang thêm các chỉ báo kỹ thuật cơ bản...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    # Đảm bảo cột timestamp là datetime nếu là index
    if not isinstance(result.index, pd.DatetimeIndex):
        result['timestamp'] = pd.to_datetime(result['timestamp'] if 'timestamp' in result.columns else result.index)
        if 'timestamp' in result.columns:
            result.set_index('timestamp', inplace=True)
    
    # --- Trend Indicators ---
    
    # Moving Averages
    result['sma_10'] = result['close'].rolling(window=10).mean()
    result['sma_20'] = result['close'].rolling(window=20).mean()
    result['sma_50'] = result['close'].rolling(window=50).mean()
    result['sma_100'] = result['close'].rolling(window=100).mean()
    result['sma_200'] = result['close'].rolling(window=200).mean()
    
    result['ema_9'] = result['close'].ewm(span=9, adjust=False).mean()
    result['ema_21'] = result['close'].ewm(span=21, adjust=False).mean()
    result['ema_50'] = result['close'].ewm(span=50, adjust=False).mean()
    result['ema_100'] = result['close'].ewm(span=100, adjust=False).mean()
    result['ema_200'] = result['close'].ewm(span=200, adjust=False).mean()
    
    # MACD
    result['macd'] = result['close'].ewm(span=12, adjust=False).mean() - result['close'].ewm(span=26, adjust=False).mean()
    result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
    result['macd_hist'] = result['macd'] - result['macd_signal']
    
    # Parabolic SAR (simplified)
    result['sar'] = result['close'].shift(1)  # Placeholder, needs complex calculation
    
    # Average Directional Index (ADX)
    high_minus_low = result['high'] - result['low']
    high_minus_close = np.abs(result['high'] - result['close'].shift(1))
    low_minus_close = np.abs(result['low'] - result['close'].shift(1))
    tr = pd.concat([high_minus_low, high_minus_close, low_minus_close], axis=1).max(axis=1)
    result['atr'] = tr.rolling(14).mean()
    
    # --- Momentum Indicators ---
    
    # RSI
    delta = result['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    result['rsi'] = 100 - (100 / (1 + rs))
    
    # Stochastic Oscillator
    low_14 = result['low'].rolling(window=14).min()
    high_14 = result['high'].rolling(window=14).max()
    result['stoch_k'] = 100 * ((result['close'] - low_14) / (high_14 - low_14))
    result['stoch_d'] = result['stoch_k'].rolling(window=3).mean()
    
    # Rate of Change (ROC)
    result['roc'] = result['close'].pct_change(periods=12) * 100
    
    # Commodity Channel Index (CCI)
    tp = (result['high'] + result['low'] + result['close']) / 3
    tp_sma = tp.rolling(window=20).mean()
    tp_md = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean())
    result['cci'] = (tp - tp_sma) / (0.015 * tp_md)
    
    # Williams %R
    result['williams_r'] = ((high_14 - result['close']) / (high_14 - low_14)) * -100
    
    # --- Volatility Indicators ---
    
    # Bollinger Bands
    result['bb_middle'] = result['close'].rolling(window=20).mean()
    result['bb_std'] = result['close'].rolling(window=20).std()
    result['bb_upper'] = result['bb_middle'] + (result['bb_std'] * 2)
    result['bb_lower'] = result['bb_middle'] - (result['bb_std'] * 2)
    result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
    
    # Average True Range (ATR) - already calculated
    
    # Keltner Channel
    result['keltner_middle'] = result['ema_21']
    result['keltner_upper'] = result['keltner_middle'] + (result['atr'] * 2)
    result['keltner_lower'] = result['keltner_middle'] - (result['atr'] * 2)
    
    # --- Volume Indicators ---
    
    # On-Balance Volume (OBV)
    result['obv'] = (np.sign(result['close'].diff()) * result['volume']).fillna(0).cumsum()
    
    # Volume Rate of Change
    result['volume_roc'] = result['volume'].pct_change(periods=1) * 100
    
    # Money Flow Index (MFI)
    typical_price = (result['high'] + result['low'] + result['close']) / 3
    raw_money_flow = typical_price * result['volume']
    
    money_flow_pos = np.where(typical_price > typical_price.shift(1), raw_money_flow, 0)
    money_flow_neg = np.where(typical_price < typical_price.shift(1), raw_money_flow, 0)
    
    money_flow_pos_sum = pd.Series(money_flow_pos).rolling(window=14).sum()
    money_flow_neg_sum = pd.Series(money_flow_neg).rolling(window=14).sum()
    
    money_ratio = money_flow_pos_sum / money_flow_neg_sum
    result['mfi'] = 100 - (100 / (1 + money_ratio))
    
    # Chaikin Money Flow (CMF)
    mfm = ((result['close'] - result['low']) - (result['high'] - result['close'])) / (result['high'] - result['low'])
    mfv = mfm * result['volume']
    result['cmf'] = mfv.rolling(window=20).sum() / result['volume'].rolling(window=20).sum()
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} chỉ báo kỹ thuật cơ bản")
    
    return result

def add_advanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các chỉ báo kỹ thuật nâng cao
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLCV và chỉ báo cơ bản
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo kỹ thuật nâng cao
    """
    logger.info("Đang thêm các chỉ báo kỹ thuật nâng cao...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    # --- Chỉ báo xung lượng nâng cao ---
    
    # Divergence RSI (sử dụng slope)
    result['rsi_slope'] = np.gradient(result['rsi']) if 'rsi' in result.columns else np.nan
    result['price_slope'] = np.gradient(result['close'])
    
    result['rsi_divergence'] = np.where(
        (result['rsi_slope'] > 0) & (result['price_slope'] < 0), 1,  # Bullish divergence
        np.where((result['rsi_slope'] < 0) & (result['price_slope'] > 0), -1, 0)  # Bearish divergence
    )
    
    # Triple Exponential Moving Average (TEMA)
    if 'ema_9' in result.columns:
        ema1 = result['ema_9']
        ema2 = ema1.ewm(span=9, adjust=False).mean()
        ema3 = ema2.ewm(span=9, adjust=False).mean()
        result['tema_9'] = 3 * ema1 - 3 * ema2 + ema3
    
    # Double Smoothed Stochastic
    if 'stoch_k' in result.columns and 'stoch_d' in result.columns:
        result['stoch_double_smoothed'] = result['stoch_d'].rolling(window=3).mean()
    
    # Fisher Transform of RSI
    if 'rsi' in result.columns:
        # Normalize RSI from 0-100 to -1 to +1
        y = 0.1 * (result['rsi'] - 50)
        # Apply Fisher Transform
        result['fisher_rsi'] = (np.exp(2 * y) - 1) / (np.exp(2 * y) + 1)
        
    # Relative Vigor Index (RVI)
    close_open = result['close'] - result['open']
    high_low = result['high'] - result['low']
    
    result['rvi_num'] = close_open.rolling(window=10).mean()
    result['rvi_den'] = high_low.rolling(window=10).mean()
    result['rvi'] = result['rvi_num'] / result['rvi_den']
    result['rvi_signal'] = result['rvi'].rolling(window=4).mean()
    
    # --- Chỉ báo xu hướng nâng cao ---
    
    # Ichimoku Cloud
    high_9 = result['high'].rolling(window=9).max()
    low_9 = result['low'].rolling(window=9).min()
    high_26 = result['high'].rolling(window=26).max()
    low_26 = result['low'].rolling(window=26).min()
    high_52 = result['high'].rolling(window=52).max()
    low_52 = result['low'].rolling(window=52).min()
    
    result['ichimoku_tenkan'] = (high_9 + low_9) / 2  # Conversion Line (Tenkan-sen)
    result['ichimoku_kijun'] = (high_26 + low_26) / 2  # Base Line (Kijun-sen)
    result['ichimoku_senkou_a'] = ((result['ichimoku_tenkan'] + result['ichimoku_kijun']) / 2).shift(26)  # Leading Span A
    result['ichimoku_senkou_b'] = ((high_52 + low_52) / 2).shift(26)  # Leading Span B
    result['ichimoku_chikou'] = result['close'].shift(-26)  # Lagging Span
    
    # Vortex Indicator
    vm_plus = abs(result['high'] - result['low'].shift(1))
    vm_minus = abs(result['low'] - result['high'].shift(1))
    tr = high_minus_low = result['high'] - result['low']
    high_minus_close = np.abs(result['high'] - result['close'].shift(1))
    low_minus_close = np.abs(result['low'] - result['close'].shift(1))
    tr = pd.concat([high_minus_low, high_minus_close, low_minus_close], axis=1).max(axis=1)
    
    result['vortex_plus_14'] = vm_plus.rolling(window=14).sum() / tr.rolling(window=14).sum()
    result['vortex_minus_14'] = vm_minus.rolling(window=14).sum() / tr.rolling(window=14).sum()
    result['vortex_diff'] = abs(result['vortex_plus_14'] - result['vortex_minus_14'])
    result['vortex_ratio'] = result['vortex_plus_14'] / result['vortex_minus_14']
    
    # MESA Adaptive Moving Average (MAMA) and FAMA - simplified version
    if 'ema_9' in result.columns:
        result['mesa_mama'] = result['ema_9'].ewm(span=0.5 * 100, adjust=False).mean()
        result['mesa_fama'] = result['mesa_mama'].ewm(span=0.05 * 100, adjust=False).mean()
    
    # --- Chỉ báo biến động nâng cao ---
    
    # Chande Volatility Index (CVI)
    if 'atr' in result.columns:
        result['cvi'] = result['atr'].rolling(window=10).mean() / result['close'] * 100
    
    # Historical Volatility (HV)
    result['returns'] = np.log(result['close'] / result['close'].shift(1))
    result['hv_10'] = result['returns'].rolling(window=10).std() * np.sqrt(252) * 100  # Annualized
    result['hv_20'] = result['returns'].rolling(window=20).std() * np.sqrt(252) * 100
    
    # Choppiness Index
    if 'atr' in result.columns:
        high_low_range = result['high'].rolling(window=14).max() - result['low'].rolling(window=14).min()
        result['choppiness'] = 100 * np.log10(np.sum(result['atr'].rolling(window=14).sum()) / high_low_range) / np.log10(14)
    
    # --- Chỉ báo khối lượng nâng cao ---
    
    # Ease of Movement (EOM)
    if 'volume' in result.columns:
        move = ((result['high'] + result['low']) / 2) - ((result['high'].shift(1) + result['low'].shift(1)) / 2)
        box_ratio = (result['volume'] / 100000000) / (result['high'] - result['low'])
        result['eom'] = move / box_ratio
        result['eom_14'] = result['eom'].rolling(window=14).mean()
    
    # Force Index
    if 'volume' in result.columns:
        result['force_index'] = result['close'].diff(1) * result['volume']
        result['force_index_13'] = result['force_index'].ewm(span=13, adjust=False).mean()
    
    # Accumulation/Distribution Line
    if 'volume' in result.columns:
        clv = ((result['close'] - result['low']) - (result['high'] - result['close'])) / (result['high'] - result['low'])
        clv = clv.replace([np.inf, -np.inf], 0)
        clv = clv.fillna(0)
        result['adl'] = (clv * result['volume']).cumsum()
    
    # Klinger Volume Oscillator (KVO)
    if 'volume' in result.columns:
        trend = np.sign(result['close'].diff(1))
        sv = result['volume'] * trend
        result['kvo_fast'] = sv.ewm(span=34, adjust=False).mean()
        result['kvo_slow'] = sv.ewm(span=55, adjust=False).mean()
        result['kvo'] = result['kvo_fast'] - result['kvo_slow']
        result['kvo_signal'] = result['kvo'].ewm(span=13, adjust=False).mean()
    
    # --- Chỉ báo thanh khoản ---
    
    # Liquidity Index
    if 'volume' in result.columns:
        result['liquidity_index'] = result['volume'] / (result['high'] - result['low'])
        result['liquidity_ma'] = result['liquidity_index'].rolling(window=20).mean()
    
    # Volume Zone Oscillator (VZO)
    if 'volume' in result.columns:
        vp = np.where(result['close'] > result['close'].shift(1), result['volume'], 0)
        vm = np.where(result['close'] < result['close'].shift(1), result['volume'], 0)
        
        result['vzo_ema'] = pd.Series(vp - vm).ewm(span=14, adjust=False).mean()
        result['volume_ema'] = result['volume'].ewm(span=14, adjust=False).mean()
        result['vzo'] = 100 * result['vzo_ema'] / result['volume_ema']
    
    # --- Chỉ báo phát hiện Choke Points ---
    
    # Choke Point Detection
    result['high_max_5'] = result['high'].rolling(window=5).max()
    result['low_min_5'] = result['low'].rolling(window=5).min()
    result['choke_range'] = result['high_max_5'] - result['low_min_5']
    
    if 'volume' in result.columns:
        # Volume Concentration at Price Levels
        result['volume_per_price_range'] = result['volume'] / (result['high'] - result['low'])
        result['volume_concentration'] = result['volume_per_price_range'] / result['volume_per_price_range'].rolling(window=10).mean()
        
        # Relative Volume at Price Levels
        result['rel_vol_at_price'] = result['volume'] / result['volume'].rolling(window=20).mean()
    
    # --- Các chỉ báo giao dịch hỗn hợp ---
    
    # Trading Range Index (TRI)
    result['m_value'] = (result['high'] - result['low']).abs()
    result['tri'] = (np.log(np.sum(result['m_value'].rolling(window=10).sum())) - np.log(result['m_value'].rolling(window=10).max())) / (np.log(10))
    
    # Composite Index
    if all(col in result.columns for col in ['rsi', 'stoch_k', 'macd']):
        # Chuẩn hóa các chỉ báo về cùng tỷ lệ
        rsi_norm = (result['rsi'] - 50) / 50
        stoch_norm = (result['stoch_k'] - 50) / 50
        
        # Chuẩn hóa MACD bằng min-max scaling qua window
        max_macd = result['macd'].rolling(window=100).max()
        min_macd = result['macd'].rolling(window=100).min()
        range_macd = max_macd - min_macd
        macd_norm = (result['macd'] - min_macd) / range_macd
        macd_norm = macd_norm.replace([np.inf, -np.inf], 0).fillna(0)
        
        # Composite index kết hợp
        result['composite_index'] = (0.4 * rsi_norm + 0.3 * stoch_norm + 0.3 * macd_norm).fillna(0)
    
    # Relative Strength Histogram
    if 'rsi' in result.columns:
        result['rsi_overbought'] = np.where(result['rsi'] > 70, result['rsi'] - 70, 0)
        result['rsi_oversold'] = np.where(result['rsi'] < 30, 30 - result['rsi'], 0)
    
    # Volume-Weighted MACD
    if all(col in result.columns for col in ['macd', 'volume']):
        norm_volume = result['volume'] / result['volume'].rolling(window=20).mean()
        result['vw_macd'] = result['macd'] * norm_volume
        result['vw_macd_signal'] = result['vw_macd'].ewm(span=9, adjust=False).mean()
        result['vw_macd_hist'] = result['vw_macd'] - result['vw_macd_signal']
    
    # --- Các chỉ báo đồng thuận thị trường ---
    
    # Mẫu chỉ báo đồng thuận
    if all(col in result.columns for col in ['ema_9', 'ema_21']):
        # +1 khi xu hướng ngắn hạn vượt xu hướng trung hạn, -1 ngược lại
        result['trend_consensus'] = np.where(result['ema_9'] > result['ema_21'], 1, -1)
    
    # Hệ số đồng thuận giữa các chỉ báo mô-men-tum
    if all(col in result.columns for col in ['rsi', 'macd_hist', 'stoch_k']):
        result['momentum_consensus'] = (
            (np.sign(result['rsi'] - 50) + 
             np.sign(result['macd_hist']) + 
             np.sign(result['stoch_k'] - 50)) / 3
        )
    
    # Chỉ số sức mạnh thị trường dựa trên khối lượng
    if 'volume' in result.columns:
        vol_trend = np.where(result['close'] > result['close'].shift(1), result['volume'], -result['volume'])
        result['volume_trend_sum'] = pd.Series(vol_trend).rolling(window=10).sum()
        result['market_strength'] = result['volume_trend_sum'] / result['volume'].rolling(window=10).sum()
    
    # Loại bỏ các giá trị NaN
    result.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} chỉ báo kỹ thuật nâng cao")
    
    return result

def add_price_pattern_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các đặc trưng dựa trên mẫu hình giá
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLCV và chỉ báo kỹ thuật
        
    Returns:
        pd.DataFrame: DataFrame với các đặc trưng mẫu hình giá
    """
    logger.info("Đang thêm các đặc trưng mẫu hình giá...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    # --- Các mẫu hình đảo chiều ---
    
    # Doji
    result['doji'] = np.where(
        abs(result['open'] - result['close']) <= (result['high'] - result['low']) * 0.05,
        1, 0
    )
    
    # Hammer
    # Thân nhỏ ở phần trên, bóng dưới dài ít nhất 2 lần thân
    lower_wick = np.where(result['close'] >= result['open'], 
                          result['close'] - result['low'],
                          result['open'] - result['low'])
    upper_wick = np.where(result['close'] >= result['open'],
                          result['high'] - result['close'],
                          result['high'] - result['open'])
    body_size = abs(result['close'] - result['open'])
    
    result['hammer'] = np.where(
        (body_size > 0) &
        (body_size <= (result['high'] - result['low']) * 0.3) &
        (lower_wick >= 2 * body_size) &
        (upper_wick <= 0.1 * body_size),
        1, 0
    )
    
    # Shooting Star
    # Thân nhỏ ở phần dưới, bóng trên dài ít nhất 2 lần thân
    result['shooting_star'] = np.where(
        (body_size > 0) &
        (body_size <= (result['high'] - result['low']) * 0.3) &
        (upper_wick >= 2 * body_size) &
        (lower_wick <= 0.1 * body_size),
        1, 0
    )
    
    # Engulfing Pattern
    # Nến hiện tại bao trùm hoàn toàn nến trước đó
    result['bullish_engulfing'] = np.where(
        (result['close'].shift(1) < result['open'].shift(1)) &  # Nến trước đỏ
        (result['close'] > result['open']) &  # Nến hiện tại xanh
        (result['open'] <= result['close'].shift(1)) &  # Mở cửa thấp hơn đóng cửa trước
        (result['close'] >= result['open'].shift(1)),  # Đóng cửa cao hơn mở cửa trước
        1, 0
    )
    
    result['bearish_engulfing'] = np.where(
        (result['close'].shift(1) > result['open'].shift(1)) &  # Nến trước xanh
        (result['close'] < result['open']) &  # Nến hiện tại đỏ
        (result['open'] >= result['close'].shift(1)) &  # Mở cửa cao hơn đóng cửa trước
        (result['close'] <= result['open'].shift(1)),  # Đóng cửa thấp hơn mở cửa trước
        1, 0
    )
    
    # Morning Star & Evening Star (simplified)
    result['morning_star'] = np.where(
        (result['close'].shift(2) < result['open'].shift(2)) &  # Nến 1 đỏ lớn
        (abs(result['close'].shift(1) - result['open'].shift(1)) < body_size.shift(2) * 0.3) &  # Nến 2 nhỏ
        (result['close'] > result['open']) &  # Nến 3 xanh
        (result['close'] > (result['close'].shift(2) + result['open'].shift(2)) / 2),  # Nến 3 đóng trên giữa nến 1
        1, 0
    )
    
    result['evening_star'] = np.where(
        (result['close'].shift(2) > result['open'].shift(2)) &  # Nến 1 xanh lớn
        (abs(result['close'].shift(1) - result['open'].shift(1)) < body_size.shift(2) * 0.3) &  # Nến 2 nhỏ
        (result['close'] < result['open']) &  # Nến 3 đỏ
        (result['close'] < (result['close'].shift(2) + result['open'].shift(2)) / 2),  # Nến 3 đóng dưới giữa nến 1
        1, 0
    )
    
    # Harami Pattern
    result['bullish_harami'] = np.where(
        (result['close'].shift(1) < result['open'].shift(1)) &  # Nến trước đỏ
        (result['close'] > result['open']) &  # Nến hiện tại xanh
        (result['open'] > result['close'].shift(1)) &  # Mở cửa cao hơn đóng cửa trước
        (result['close'] < result['open'].shift(1)),  # Đóng cửa thấp hơn mở cửa trước
        1, 0
    )
    
    result['bearish_harami'] = np.where(
        (result['close'].shift(1) > result['open'].shift(1)) &  # Nến trước xanh
        (result['close'] < result['open']) &  # Nến hiện tại đỏ
        (result['open'] < result['close'].shift(1)) &  # Mở cửa thấp hơn đóng cửa trước
        (result['close'] > result['open'].shift(1)),  # Đóng cửa cao hơn mở cửa trước
        1, 0
    )
    
    # --- Các mẫu hình tiếp diễn ---
    
    # Three White Soldiers
    result['three_white_soldiers'] = np.where(
        (result['close'] > result['open']) &  # Nến hiện tại xanh
        (result['close'].shift(1) > result['open'].shift(1)) &  # Nến -1 xanh
        (result['close'].shift(2) > result['open'].shift(2)) &  # Nến -2 xanh
        (result['open'] > result['open'].shift(1)) &  # Mở cửa cao hơn mở cửa trước
        (result['open'].shift(1) > result['open'].shift(2)) &  # Mở cửa trước cao hơn mở cửa -2
        (result['close'] > result['close'].shift(1)) &  # Đóng cửa cao hơn đóng cửa trước
        (result['close'].shift(1) > result['close'].shift(2)),  # Đóng cửa trước cao hơn đóng cửa -2
        1, 0
    )
    
    # Three Black Crows
    result['three_black_crows'] = np.where(
        (result['close'] < result['open']) &  # Nến hiện tại đỏ
        (result['close'].shift(1) < result['open'].shift(1)) &  # Nến -1 đỏ
        (result['close'].shift(2) < result['open'].shift(2)) &  # Nến -2 đỏ
        (result['open'] < result['open'].shift(1)) &  # Mở cửa thấp hơn mở cửa trước
        (result['open'].shift(1) < result['open'].shift(2)) &  # Mở cửa trước thấp hơn mở cửa -2
        (result['close'] < result['close'].shift(1)) &  # Đóng cửa thấp hơn đóng cửa trước
        (result['close'].shift(1) < result['close'].shift(2)),  # Đóng cửa trước thấp hơn đóng cửa -2
        1, 0
    )
    
    # Tweezer pattern (simplified)
    result['tweezer_bottom'] = np.where(
        (result['close'].shift(1) < result['open'].shift(1)) &  # Nến trước đỏ
        (result['close'] > result['open']) &  # Nến hiện tại xanh
        (abs(result['low'] - result['low'].shift(1)) < result['atr'] * 0.1),  # Đáy gần nhau
        1, 0
    )
    
    result['tweezer_top'] = np.where(
        (result['close'].shift(1) > result['open'].shift(1)) &  # Nến trước xanh
        (result['close'] < result['open']) &  # Nến hiện tại đỏ
        (abs(result['high'] - result['high'].shift(1)) < result['atr'] * 0.1),  # Đỉnh gần nhau
        1, 0
    )
    
    # --- Phát hiện các mẫu hình kỹ thuật nâng cao ---
    
    # Head and Shoulders / Inverse H&S detection (simplified)
    # Lưu ý: đây là phiên bản đơn giản, phát hiện đầy đủ cần thuật toán phức tạp hơn
    
    # Xác định các đỉnh và đáy cục bộ
    window = 5  # Cửa sổ để xem xét các đỉnh và đáy
    
    # Đỉnh cục bộ nếu giá cao hơn 'window' nến trước và sau
    peaks = ((result['high'] > result['high'].shift(window)) & 
             (result['high'] > result['high'].shift(-window)))
    
    # Đáy cục bộ nếu giá thấp hơn 'window' nến trước và sau
    troughs = ((result['low'] < result['low'].shift(window)) & 
               (result['low'] < result['low'].shift(-window)))
    
    # Đánh dấu các đỉnh và đáy
    result['is_peak'] = np.where(peaks, 1, 0)
    result['is_trough'] = np.where(troughs, 1, 0)
    
    # Tính toán các mẫu hình hỗn hợp và quy mô cao hơn với cách tiếp cận đơn giản
    
    # Divergence RSI (sử dụng đỉnh và đáy cục bộ)
    if 'rsi' in result.columns:
        # Tạo cột dành cho divergence
        result['peak_divergence'] = 0
        result['trough_divergence'] = 0
        
        # Tính toán trong vòng lặp để tìm đỉnh và đáy cục bộ
        for i in range(window, len(result) - window):
            if result['is_peak'].iloc[i] == 1:
                # Tìm đỉnh trước đó
                j = i - 1
                while j >= window and result['is_peak'].iloc[j] != 1:
                    j -= 1
                
                if j >= window:
                    # Kiểm tra divergence: giá tăng nhưng RSI giảm
                    if (result['high'].iloc[i] > result['high'].iloc[j] and 
                        result['rsi'].iloc[i] < result['rsi'].iloc[j]):
                        result['peak_divergence'].iloc[i] = -1  # Bearish divergence
            
            if result['is_trough'].iloc[i] == 1:
                # Tìm đáy trước đó
                j = i - 1
                while j >= window and result['is_trough'].iloc[j] != 1:
                    j -= 1
                
                if j >= window:
                    # Kiểm tra divergence: giá giảm nhưng RSI tăng
                    if (result['low'].iloc[i] < result['low'].iloc[j] and 
                        result['rsi'].iloc[i] > result['rsi'].iloc[j]):
                        result['trough_divergence'].iloc[i] = 1  # Bullish divergence
    
    # --- Tính toán các đặc trưng hỗn hợp từ các mẫu hình ---
    
    # Chỉ số mẫu hình đảo chiều tăng
    result['bullish_reversal_score'] = (
        result['hammer'] + 
        result['bullish_engulfing'] * 2 +  # Trọng số cao hơn cho engulfing
        result['morning_star'] * 2 + 
        result['bullish_harami'] + 
        result['tweezer_bottom'] +
        result['trough_divergence']
    )
    
    # Chỉ số mẫu hình đảo chiều giảm
    result['bearish_reversal_score'] = (
        result['shooting_star'] + 
        result['bearish_engulfing'] * 2 +  # Trọng số cao hơn cho engulfing
        result['evening_star'] * 2 + 
        result['bearish_harami'] + 
        result['tweezer_top'] +
        result['peak_divergence'] * -1  # Để giữ dấu nhất quán
    )
    
    # Chỉ số mẫu hình tiếp diễn tăng
    result['bullish_continuation_score'] = result['three_white_soldiers'] * 2
    
    # Chỉ số mẫu hình tiếp diễn giảm
    result['bearish_continuation_score'] = result['three_black_crows'] * 2
    
    # Chỉ số tổng hợp
    result['pattern_score'] = (
        result['bullish_reversal_score'] + 
        result['bullish_continuation_score'] - 
        result['bearish_reversal_score'] - 
        result['bearish_continuation_score']
    )
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} đặc trưng mẫu hình giá")
    
    return result

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các đặc trưng dựa trên thời gian
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLCV
        
    Returns:
        pd.DataFrame: DataFrame với các đặc trưng thời gian
    """
    logger.info("Đang thêm các đặc trưng thời gian...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    # Đảm bảo index là datetime
    if not isinstance(result.index, pd.DatetimeIndex):
        result['timestamp'] = pd.to_datetime(result['timestamp'] if 'timestamp' in result.columns else result.index)
        if 'timestamp' in result.columns:
            result.set_index('timestamp', inplace=True)
    
    # Các đặc trưng thời gian cơ bản
    result['hour'] = result.index.hour
    result['day_of_week'] = result.index.dayofweek
    result['day_of_month'] = result.index.day
    result['week_of_year'] = result.index.isocalendar().week
    result['month'] = result.index.month
    result['quarter'] = result.index.quarter
    result['year'] = result.index.year
    
    # Tạo biến dummy cho thời gian
    result['is_weekend'] = np.where(result['day_of_week'] >= 5, 1, 0)
    result['is_month_start'] = result.index.is_month_start.astype(int)
    result['is_month_end'] = result.index.is_month_end.astype(int)
    result['is_quarter_start'] = result.index.is_quarter_start.astype(int)
    result['is_quarter_end'] = result.index.is_quarter_end.astype(int)
    result['is_year_start'] = result.index.is_year_start.astype(int)
    result['is_year_end'] = result.index.is_year_end.astype(int)
    
    # Phân loại thời gian giao dịch
    result['session_time'] = pd.cut(
        result['hour'], 
        bins=[0, 6, 9, 12, 15, 19, 24], 
        labels=['night', 'early_morning', 'morning', 'afternoon', 'evening', 'night']
    )
    
    # One-hot encoding cho session time
    session_dummies = pd.get_dummies(result['session_time'], prefix='session')
    result = pd.concat([result, session_dummies], axis=1)
    
    # Biến hàm sin và cos để biểu diễn chu kỳ
    result['hour_sin'] = np.sin(2 * np.pi * result['hour'] / 24)
    result['hour_cos'] = np.cos(2 * np.pi * result['hour'] / 24)
    result['day_of_week_sin'] = np.sin(2 * np.pi * result['day_of_week'] / 7)
    result['day_of_week_cos'] = np.cos(2 * np.pi * result['day_of_week'] / 7)
    result['day_of_month_sin'] = np.sin(2 * np.pi * result['day_of_month'] / 31)
    result['day_of_month_cos'] = np.cos(2 * np.pi * result['day_of_month'] / 31)
    result['month_sin'] = np.sin(2 * np.pi * result['month'] / 12)
    result['month_cos'] = np.cos(2 * np.pi * result['month'] / 12)
    
    # Đặc trưng về khoảng thời gian từ sự kiện trước đó
    # Ví dụ: số ngày từ đỉnh/đáy gần nhất, v.v.
    if 'is_peak' in result.columns and 'is_trough' in result.columns:
        # Tính ngày từ đỉnh gần nhất
        peak_indices = result.index[result['is_peak'] == 1]
        for i, idx in enumerate(result.index):
            previous_peaks = peak_indices[peak_indices < idx]
            if len(previous_peaks) > 0:
                last_peak = previous_peaks[-1]
                result.loc[idx, 'days_since_last_peak'] = (idx - last_peak).days
            else:
                result.loc[idx, 'days_since_last_peak'] = 365  # Giá trị lớn nếu không có đỉnh trước đó
        
        # Tính ngày từ đáy gần nhất
        trough_indices = result.index[result['is_trough'] == 1]
        for i, idx in enumerate(result.index):
            previous_troughs = trough_indices[trough_indices < idx]
            if len(previous_troughs) > 0:
                last_trough = previous_troughs[-1]
                result.loc[idx, 'days_since_last_trough'] = (idx - last_trough).days
            else:
                result.loc[idx, 'days_since_last_trough'] = 365  # Giá trị lớn nếu không có đáy trước đó
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} đặc trưng thời gian")
    
    return result

def add_liquidity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các đặc trưng dựa trên thanh khoản thị trường
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLCV và chỉ báo kỹ thuật
        
    Returns:
        pd.DataFrame: DataFrame với các đặc trưng thanh khoản
    """
    logger.info("Đang thêm các đặc trưng thanh khoản...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    if 'volume' in result.columns:
        # Tính toán các chỉ số thanh khoản cơ bản
        result['volume_ma_10'] = result['volume'].rolling(window=10).mean()
        result['volume_ma_20'] = result['volume'].rolling(window=20).mean()
        result['volume_ma_50'] = result['volume'].rolling(window=50).mean()
        
        # Relative Volume Ratio
        result['rel_volume'] = result['volume'] / result['volume_ma_20']
        result['rel_volume_z_score'] = (result['volume'] - result['volume_ma_20']) / result['volume'].rolling(window=20).std()
        
        # Volume Trend
        result['volume_5_10_ratio'] = result['volume'].rolling(window=5).mean() / result['volume'].rolling(window=10).mean()
        result['volume_10_20_ratio'] = result['volume'].rolling(window=10).mean() / result['volume'].rolling(window=20).mean()
        
        # Chaikin Money Flow (CMF)
        money_flow_multiplier = ((result['close'] - result['low']) - (result['high'] - result['close'])) / (result['high'] - result['low'])
        money_flow_volume = money_flow_multiplier * result['volume']
        result['cmf_20'] = money_flow_volume.rolling(window=20).sum() / result['volume'].rolling(window=20).sum()
        
        # On Balance Volume (OBV) Rate of Change
        if 'obv' in result.columns:
            result['obv_roc_5'] = result['obv'].pct_change(periods=5) * 100
            result['obv_roc_10'] = result['obv'].pct_change(periods=10) * 100
        
        # Volume Spread Analysis
        result['spread_factor'] = (result['high'] - result['low']) / (result['volume'] / result['volume_ma_20'])
        
        # Đặc trưng Liquidity Cluster
        result['liquidity_depth'] = result['volume'] / (result['high'] - result['low'])
        result['liquidity_depth_ma'] = result['liquidity_depth'].rolling(window=10).mean()
        result['liquidity_depth_relative'] = result['liquidity_depth'] / result['liquidity_depth_ma']
        
        # Phát hiện thanh khoản bất thường
        result['volume_spike'] = np.where(result['rel_volume'] > 2, 1, 0)
        result['volume_dry_up'] = np.where(result['rel_volume'] < 0.5, 1, 0)
        
        # Liquidity breakout detection
        result['volume_breakout'] = np.where(
            (result['rel_volume'] > 1.5) & 
            ((result['close'] > result['high'].shift(1)) | (result['close'] < result['low'].shift(1))),
            1, 0
        )
        
        # Phân tích thanh khoản theo vùng giá
        
        # Chia vùng giá thành các phân vị
        price_range = result['high'].rolling(window=20).max() - result['low'].rolling(window=20).min()
        price_percentile = (result['close'] - result['low'].rolling(window=20).min()) / price_range
        
        # Volume tại các vùng giá khác nhau
        result['volume_at_highs'] = np.where(price_percentile > 0.8, result['volume'], 0) / result['volume']
        result['volume_at_lows'] = np.where(price_percentile < 0.2, result['volume'], 0) / result['volume']
        result['volume_at_mid'] = np.where((price_percentile >= 0.4) & (price_percentile <= 0.6), result['volume'], 0) / result['volume']
        
        # High Volume Nodes - vùng có khối lượng giao dịch cao
        rolling_volume_by_price = pd.DataFrame()
        price_brackets = 10  # Chia thành 10 vùng giá
        
        for i in range(price_brackets):
            lower_bound = result['low'].rolling(window=20).min() + i * price_range / price_brackets
            upper_bound = result['low'].rolling(window=20).min() + (i + 1) * price_range / price_brackets
            
            rolling_volume_by_price[f'volume_bracket_{i}'] = np.where(
                (result['close'] >= lower_bound) & (result['close'] < upper_bound),
                result['volume'], 0
            )
        
        # Tìm vùng có khối lượng cao nhất
        max_vol_bracket = rolling_volume_by_price.idxmax(axis=1)
        result['high_volume_price_zone'] = max_vol_bracket.apply(lambda x: int(x.split('_')[-1]) if pd.notnull(x) else np.nan)
        
        # Volume khô cạn trước khi bùng nổ
        result['volume_exhaustion'] = np.where(
            (result['volume'].rolling(window=3).mean() < result['volume_ma_20'] * 0.7) &
            (result['volume'].shift(-1) > result['volume_ma_20'] * 1.5),
            1, 0
        )
        
        # Biến động khối lượng (cho sự kiện cụ thể)
        # Tăng mạnh sau giảm liên tục
        down_days = (result['close'] < result['open']).rolling(window=3).sum()
        result['accumulation_signal'] = np.where(
            (down_days >= 2) & (result['close'] > result['open']) & (result['volume'] > result['volume_ma_20'] * 1.3),
            1, 0
        )
        
        # Tăng khối lượng với cây nến Doji
        if 'doji' in result.columns:
            result['high_vol_doji'] = np.where(
                (result['doji'] == 1) & (result['volume'] > result['volume_ma_20'] * 1.5),
                1, 0
            )
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} đặc trưng thanh khoản")
    
    return result

def create_feature_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo các tương tác giữa các đặc trưng
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu và đặc trưng
        
    Returns:
        pd.DataFrame: DataFrame với các tương tác đặc trưng bổ sung
    """
    logger.info("Đang tạo các tương tác đặc trưng...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    # Danh sách các cặp đặc trưng cần tạo tương tác
    interaction_pairs = [
        # RSI và Biến động
        ('rsi', 'volatility', lambda x, y: x * y),
        ('rsi', 'atr', lambda x, y: x * y),
        
        # Chỉ báo Momentum và Trend
        ('macd_hist', 'ema_9_21_cross', lambda x, y: x * y),
        ('rsi', 'trend_consensus', lambda x, y: x * y),
        
        # Khối lượng và Chỉ báo kỹ thuật
        ('volume', 'rsi', lambda x, y: np.log1p(x) * y),
        ('rel_volume', 'macd_hist', lambda x, y: x * y),
        
        # Tương tác giữa các mẫu hình
        ('pattern_score', 'rsi', lambda x, y: x * (y - 50)),
        ('pattern_score', 'macd_hist', lambda x, y: x * y),
        
        # Chỉ báo kỹ thuật và đặc trưng thanh khoản
        ('rsi', 'liquidity_depth_relative', lambda x, y: x * y),
        ('macd_hist', 'volume_breakout', lambda x, y: x * y)
    ]
    
    # Tạo các đặc trưng tương tác
    for col1, col2, func in interaction_pairs:
        if col1 in result.columns and col2 in result.columns:
            interaction_name = f'interaction_{col1}_{col2}'
            result[interaction_name] = func(result[col1], result[col2])
    
    # Tạo các chỉ báo tổ hợp cho các cặp chỉ báo có mối quan hệ mạnh
    
    # RSI và Stochastic
    if 'rsi' in result.columns and 'stoch_k' in result.columns:
        result['rsi_stoch_composite'] = (result['rsi'] + result['stoch_k']) / 2
        
        # Chỉ số phân kỳ (xác nhận lẫn nhau hoặc phân kỳ)
        result['rsi_stoch_divergence'] = np.where(
            ((result['rsi'] > 50) & (result['stoch_k'] < 50)) | 
            ((result['rsi'] < 50) & (result['stoch_k'] > 50)),
            1, 0
        )
    
    # MACD và Bollinger Bands
    if 'macd_hist' in result.columns and 'bb_width' in result.columns:
        # Composite score kết hợp sức mạnh MACD với biến động Bollinger
        result['macd_bb_composite'] = result['macd_hist'] * result['bb_width']
    
    # Tương tác giữa thanh khoản và biến động
    if 'rel_volume' in result.columns and 'volatility' in result.columns:
        result['volume_volatility_ratio'] = result['rel_volume'] / result['volatility']
    
    # Tương tác giữa nhiều chỉ báo động lượng
    if all(col in result.columns for col in ['rsi', 'macd_hist', 'stoch_k']):
        # Chỉ số 3-way momentum
        result['triple_momentum'] = (
            (result['rsi'] / 100) * 
            np.sign(result['macd_hist']) * 
            (result['stoch_k'] / 100)
        )
    
    logger.info(f"Đã tạo {len(result.columns) - len(df.columns)} tương tác đặc trưng")
    
    return result

def create_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tạo tất cả các đặc trưng
    
    Args:
        df (pd.DataFrame): DataFrame chứa dữ liệu OHLCV ban đầu
        
    Returns:
        pd.DataFrame: DataFrame với tất cả các đặc trưng
    """
    logger.info("Bắt đầu tạo tất cả các đặc trưng...")
    
    # Tạo bản sao để tránh SettingWithCopyWarning
    result = df.copy()
    
    # Thêm các chỉ báo kỹ thuật cơ bản
    result = add_technical_indicators(result)
    
    # Thêm các chỉ báo kỹ thuật nâng cao
    result = add_advanced_indicators(result)
    
    # Thêm các đặc trưng mẫu hình giá
    result = add_price_pattern_features(result)
    
    # Thêm các đặc trưng thời gian
    result = add_time_features(result)
    
    # Thêm các đặc trưng thanh khoản
    result = add_liquidity_features(result)
    
    # Tạo các tương tác đặc trưng
    result = create_feature_interactions(result)
    
    # Loại bỏ các giá trị NaN
    result = result.replace([np.inf, -np.inf], np.nan)
    
    # Đếm số lượng giá trị NaN trong mỗi cột
    na_counts = result.isna().sum()
    
    # Loại bỏ các cột có quá nhiều NaN (>30% của dữ liệu)
    threshold = len(result) * 0.3
    cols_to_drop = na_counts[na_counts > threshold].index
    
    if len(cols_to_drop) > 0:
        logger.info(f"Loại bỏ {len(cols_to_drop)} cột có quá nhiều giá trị NaN: {list(cols_to_drop)}")
        result = result.drop(columns=cols_to_drop)
    
    # Điền các giá trị NaN còn lại
    num_na = result.isna().sum().sum()
    if num_na > 0:
        logger.info(f"Điền {num_na} giá trị NaN còn lại")
        result = result.fillna(method='ffill').fillna(method='bfill').fillna(0)
    
    logger.info(f"Đã tạo tổng cộng {len(result.columns) - len(df.columns)} đặc trưng mới")
    
    return result

def process_and_enhance_dataset(input_data: Union[str, pd.DataFrame], output_file: str = None, 
                            basic_only: bool = False,
                            exclude_patterns: bool = False,
                            exclude_time: bool = False,
                            exclude_liquidity: bool = False,
                            exclude_interactions: bool = False,
                            max_nan_ratio: float = 0.3) -> Union[pd.DataFrame, str]:
    """
    Xử lý và nâng cao dataset, thêm các đặc trưng ML nâng cao
    
    Args:
        input_data (Union[str, pd.DataFrame]): Đường dẫn đến file CSV hoặc DataFrame chứa dữ liệu đầu vào
        output_file (str, optional): Đường dẫn đến file CSV dữ liệu đầu ra, nếu None chỉ trả về DataFrame
        basic_only (bool): Chỉ tạo đặc trưng cơ bản
        exclude_patterns (bool): Không tạo đặc trưng mẫu hình giá
        exclude_time (bool): Không tạo đặc trưng thời gian
        exclude_liquidity (bool): Không tạo đặc trưng thanh khoản
        exclude_interactions (bool): Không tạo tương tác đặc trưng
        max_nan_ratio (float): Tỷ lệ tối đa giá trị NaN cho phép trong một cột (0.0-1.0)
        
    Returns:
        Union[pd.DataFrame, str]: DataFrame đã xử lý hoặc đường dẫn đến file kết quả
    """
    try:
        # Xác định nguồn dữ liệu đầu vào
        if isinstance(input_data, str):
            # Đọc từ file
            logger.info(f"Đọc dữ liệu từ file: {input_data}")
            input_df = pd.read_csv(input_data)
        else:
            # Đã cung cấp DataFrame
            logger.info(f"Sử dụng DataFrame với {len(input_data)} dòng")
            input_df = input_data.copy()
        
        # Chuyển đổi cột timestamp nếu có
        if 'timestamp' in input_df.columns:
            input_df['timestamp'] = pd.to_datetime(input_df['timestamp'])
        
        # Xử lý dữ liệu và tạo đặc trưng
        logger.info("Bắt đầu xử lý dữ liệu và tạo đặc trưng...")
        
        if basic_only:
            logger.info("Chỉ tạo đặc trưng cơ bản")
            output_df = add_technical_indicators(input_df)
        else:
            logger.info("Đang tạo đặc trưng cơ bản...")
            output_df = add_technical_indicators(input_df)
            
            logger.info("Đang tạo đặc trưng nâng cao...")
            output_df = add_advanced_indicators(output_df)
            
            if not exclude_patterns:
                output_df = add_price_pattern_features(output_df)
            
            if not exclude_time:
                output_df = add_time_features(output_df)
            
            if not exclude_liquidity:
                output_df = add_liquidity_features(output_df)
            
            if not exclude_interactions:
                output_df = create_feature_interactions(output_df)
        
        # Xử lý missing values
        output_df = output_df.replace([np.inf, -np.inf], np.nan)
        
        # Loại bỏ các cột có quá nhiều NaN (>30% của dữ liệu)
        threshold = len(output_df) * 0.3
        na_counts = output_df.isna().sum()
        cols_to_drop = na_counts[na_counts > threshold].index
        
        if len(cols_to_drop) > 0:
            logger.info(f"Loại bỏ {len(cols_to_drop)} cột có quá nhiều giá trị NaN: {list(cols_to_drop)}")
            output_df = output_df.drop(columns=cols_to_drop)
        
        # Điền các giá trị NaN còn lại
        num_na = output_df.isna().sum().sum()
        if num_na > 0:
            logger.info(f"Điền {num_na} giá trị NaN còn lại với forward/backward fill")
            output_df = output_df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        # Ghi dữ liệu ra file đầu ra
        logger.info(f"Lưu dữ liệu đã xử lý vào {output_file}")
        output_df.to_csv(output_file, index=False)
        
        logger.info(f"Đã tạo thành công tổng cộng {len(output_df.columns) - len(input_df.columns)} đặc trưng mới")
        logger.info(f"Dữ liệu đầu ra có {len(output_df)} dòng và {len(output_df.columns)} cột")
        
        return output_file
    
    except Exception as e:
        logger.error(f"Lỗi khi xử lý dữ liệu: {e}")
        raise e

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Tạo các đặc trưng nâng cao cho mô hình ML')
    parser.add_argument('--input_file', type=str, required=True, help='Đường dẫn đến file CSV dữ liệu đầu vào')
    parser.add_argument('--output_file', type=str, required=True, help='Đường dẫn đến file CSV dữ liệu đầu ra')
    parser.add_argument('--basic_only', action='store_true', help='Chỉ tạo các đặc trưng cơ bản')
    parser.add_argument('--exclude_patterns', action='store_true', help='Không tạo đặc trưng mẫu hình giá')
    parser.add_argument('--exclude_time', action='store_true', help='Không tạo đặc trưng thời gian')
    parser.add_argument('--exclude_liquidity', action='store_true', help='Không tạo đặc trưng thanh khoản')
    parser.add_argument('--exclude_interactions', action='store_true', help='Không tạo tương tác đặc trưng')
    parser.add_argument('--max_nan_ratio', type=float, default=0.3, help='Tỷ lệ tối đa giá trị NaN cho phép trong một cột (0.0-1.0)')
    
    args = parser.parse_args()
    
    try:
        # Gọi hàm xử lý và nâng cao dataset
        process_and_enhance_dataset(
            input_data=args.input_file, 
            output_file=args.output_file,
            basic_only=args.basic_only,
            exclude_patterns=args.exclude_patterns,
            exclude_time=args.exclude_time,
            exclude_liquidity=args.exclude_liquidity,
            exclude_interactions=args.exclude_interactions,
            max_nan_ratio=args.max_nan_ratio
        )
        
        logger.info("Hoàn thành quá trình tạo đặc trưng nâng cao!")
        
    except Exception as e:
        logger.error(f"Lỗi khi xử lý dữ liệu: {str(e)}")
        raise