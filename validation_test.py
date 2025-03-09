#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra độ chính xác của các chỉ số và tín hiệu trading.
Phân tích từng bước để đảm bảo không có sai lệch khi vào lệnh.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/validation_test.log')
    ]
)

logger = logging.getLogger('validation_test')

# Đảm bảo các thư mục cần thiết tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('validation_results', exist_ok=True)


def generate_test_data(type="real"):
    """
    Tạo dữ liệu kiểm thử.
    
    Args:
        type (str): Loại dữ liệu - "real" sử dụng dữ liệu thực tế nếu có, 
                   "synthetic" tạo dữ liệu giả lập với các mẫu đã biết
    
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    if type == "real" and os.path.exists('data/BTC_USDT_1h.csv'):
        # Sử dụng dữ liệu thực tế
        df = pd.read_csv('data/BTC_USDT_1h.csv')
        
        # Kiểm tra định dạng và chuyển đổi nếu cần
        if 'timestamp' in df.columns or 'date' in df.columns:
            date_col = 'timestamp' if 'timestamp' in df.columns else 'date'
            
            # Chuyển đổi timestamp thành index datetime nếu cần
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                if pd.api.types.is_numeric_dtype(df[date_col]):
                    # Giả định là unix timestamp
                    df[date_col] = pd.to_datetime(df[date_col], unit='ms')
                else:
                    # Giả định là chuỗi datetime
                    df[date_col] = pd.to_datetime(df[date_col])
            
            df.set_index(date_col, inplace=True)
        
        logger.info(f"Đã tải dữ liệu thực tế, kích thước: {df.shape}")
        return df
    else:
        # Tạo dữ liệu giả lập với 3 mẫu rõ ràng
        logger.info("Tạo dữ liệu giả lập với các mẫu đặc trưng")
        
        # 1. Tạo khung thời gian
        periods = 1000
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='1H')
        
        # 2. Chuẩn bị dữ liệu cơ sở
        base_price = 50000
        df = pd.DataFrame(index=dates)
        
        # 3. Tạo 3 mẫu khác nhau: up-trend, down-trend, và sideways
        segment_size = periods // 3
        
        # Up-trend
        up_trend = np.linspace(0, 0.25, segment_size)  # Tăng 25%
        up_noise = np.random.normal(0, 0.01, segment_size)
        up_prices = base_price * (1 + up_trend + up_noise)
        
        # Sideways
        sideways_center = up_prices[-1]
        sideways_noise = np.random.normal(0, 0.01, segment_size)
        sideways_prices = sideways_center * (1 + 0.03 * np.sin(np.linspace(0, 6*np.pi, segment_size)) + sideways_noise)
        
        # Down-trend
        down_start = sideways_prices[-1]
        down_trend = np.linspace(0, -0.2, segment_size)  # Giảm 20%
        down_noise = np.random.normal(0, 0.015, segment_size)
        down_prices = down_start * (1 + down_trend + down_noise)
        
        # Ghép tất cả lại
        prices = np.concatenate([up_prices, sideways_prices, down_prices])
        
        # Đảm bảo prices có đúng độ dài bằng với số hàng trong df
        if len(prices) != len(df):
            # Thêm phần tử cuối cùng nếu thiếu
            if len(prices) < len(df):
                prices = np.append(prices, prices[-1])
            # Cắt bớt nếu thừa
            else:
                prices = prices[:len(df)]
        
        # Tính open, high, low từ close
        df['close'] = prices
        df['open'] = np.roll(prices, 1)
        df['open'].iloc[0] = df['close'].iloc[0] * 0.998
        
        # High là max của open và close, cộng thêm biến động - đảm bảo độ dài đúng
        high_adjust = 1 + np.random.uniform(0.001, 0.008, len(df))
        df['high'] = np.maximum(df['open'], df['close']) * high_adjust
        
        # Low là min của open và close, trừ đi biến động - đảm bảo độ dài đúng
        low_adjust = 1 - np.random.uniform(0.001, 0.008, len(df))
        df['low'] = np.minimum(df['open'], df['close']) * low_adjust
        
        # Volume
        base_volume = 1000
        volume_trend = np.concatenate([
            np.linspace(1, 2, segment_size),  # Tăng volume trong uptrend
            np.random.normal(1.5, 0.3, segment_size),  # Volume sideway
            np.linspace(2, 1, segment_size)   # Giảm volume trong downtrend
        ])
        
        # Đảm bảo volume_trend có đúng độ dài bằng với số hàng trong df
        if len(volume_trend) != len(df):
            # Thêm phần tử cuối cùng nếu thiếu
            if len(volume_trend) < len(df):
                n_to_add = len(df) - len(volume_trend)
                volume_trend = np.append(volume_trend, [volume_trend[-1]] * n_to_add)
            # Cắt bớt nếu thừa
            else:
                volume_trend = volume_trend[:len(df)]
        
        # Thêm spike volume tại các điểm chuyển tiếp
        volume_trend[segment_size-5:segment_size+5] *= 2.5
        volume_trend[2*segment_size-5:2*segment_size+5] *= 2.5
        
        # Tạo noise cùng độ dài với df
        volume_noise = 1 + np.random.normal(0, 0.2, len(df))
        
        df['volume'] = base_volume * volume_trend * volume_noise
        df['volume'] = df['volume'].astype(int)
        
        logger.info(f"Đã tạo dữ liệu giả lập, kích thước: {df.shape}")
        
        return df


def calculate_basic_indicators(df):
    """
    Tính toán các chỉ báo cơ bản và kiểm tra độ chính xác
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã tính
    """
    logger.info("Tính toán các chỉ báo cơ bản...")
    
    # Sao chép DataFrame để không ảnh hưởng đến dữ liệu gốc
    df_indicators = df.copy()
    
    # 1. Tính SMA (Simple Moving Average)
    for period in [20, 50, 200]:
        df_indicators[f'sma_{period}'] = df_indicators['close'].rolling(window=period).mean()
        
        # Kiểm tra độ chính xác
        validation_sma = []
        for i in range(len(df_indicators)):
            if i >= period - 1:
                expected_sma = df_indicators['close'].iloc[i-(period-1):i+1].mean()
                actual_sma = df_indicators[f'sma_{period}'].iloc[i]
                if not np.isnan(actual_sma):
                    is_valid = np.isclose(expected_sma, actual_sma, rtol=1e-10)
                    if not is_valid:
                        logger.warning(f"SMA-{period} không chính xác tại dòng {i}: Expected {expected_sma}, Got {actual_sma}")
                    validation_sma.append(is_valid)
                    
        valid_pct = 100 * sum(validation_sma) / len(validation_sma) if validation_sma else 0
        logger.info(f"SMA-{period} chính xác {valid_pct:.2f}% trên {len(validation_sma)} mẫu có thể kiểm tra")
    
    # 2. Tính Bollinger Bands
    period = 20
    std_dev = 2
    
    df_indicators['sma_20'] = df_indicators['close'].rolling(window=period).mean()
    df_indicators['std_20'] = df_indicators['close'].rolling(window=period).std()
    df_indicators['upper_band'] = df_indicators['sma_20'] + (df_indicators['std_20'] * std_dev)
    df_indicators['lower_band'] = df_indicators['sma_20'] - (df_indicators['std_20'] * std_dev)
    df_indicators['bb_width'] = (df_indicators['upper_band'] - df_indicators['lower_band']) / df_indicators['sma_20']
    
    # Kiểm tra độ chính xác Bollinger Bands
    validation_bb = []
    for i in range(len(df_indicators)):
        if i >= period - 1:
            window_data = df_indicators['close'].iloc[i-(period-1):i+1]
            expected_sma = window_data.mean()
            expected_std = window_data.std()
            expected_upper = expected_sma + (expected_std * std_dev)
            expected_lower = expected_sma - (expected_std * std_dev)
            
            actual_upper = df_indicators['upper_band'].iloc[i]
            actual_lower = df_indicators['lower_band'].iloc[i]
            
            if not np.isnan(actual_upper) and not np.isnan(actual_lower):
                is_valid_upper = np.isclose(expected_upper, actual_upper, rtol=1e-10)
                is_valid_lower = np.isclose(expected_lower, actual_lower, rtol=1e-10)
                
                if not is_valid_upper or not is_valid_lower:
                    logger.warning(f"BB không chính xác tại dòng {i}: " +
                                f"Upper: Expected {expected_upper}, Got {actual_upper}, " +
                                f"Lower: Expected {expected_lower}, Got {actual_lower}")
                    
                validation_bb.append(is_valid_upper and is_valid_lower)
    
    valid_pct = 100 * sum(validation_bb) / len(validation_bb) if validation_bb else 0
    logger.info(f"Bollinger Bands chính xác {valid_pct:.2f}% trên {len(validation_bb)} mẫu có thể kiểm tra")
    
    # 3. Tính RSI
    period = 14
    delta = df_indicators['close'].diff()
    
    gain = delta.copy()
    gain[gain < 0] = 0
    
    loss = delta.copy()
    loss[loss > 0] = 0
    loss = abs(loss)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Tránh chia cho 0
    avg_loss_nonzero = avg_loss.copy()
    avg_loss_nonzero[avg_loss_nonzero == 0] = 1e-10
    
    rs = avg_gain / avg_loss_nonzero
    df_indicators['rsi'] = 100 - (100 / (1 + rs))
    
    # Kiểm tra độ chính xác RSI
    validation_rsi = []
    for i in range(period + 10, len(df_indicators), 10):  # Kiểm tra mỗi 10 dòng để tiết kiệm thời gian
        delta_slice = delta.iloc[i-period+1:i+1]
        
        gains = delta_slice.copy()
        gains[gains < 0] = 0
        
        losses = delta_slice.copy()
        losses[losses > 0] = 0
        losses = abs(losses)
        
        avg_g = gains.mean()
        avg_l = losses.mean()
        
        if avg_l == 0:
            expected_rsi = 100
        else:
            rs_val = avg_g / avg_l
            expected_rsi = 100 - (100 / (1 + rs_val))
        
        actual_rsi = df_indicators['rsi'].iloc[i]
        
        if not np.isnan(actual_rsi):
            is_valid = np.isclose(expected_rsi, actual_rsi, rtol=1e-2, atol=1e-2)  # RSI có thể có sai số nhỏ do làm tròn
            if not is_valid:
                logger.warning(f"RSI không chính xác tại dòng {i}: Expected {expected_rsi}, Got {actual_rsi}")
            validation_rsi.append(is_valid)
    
    valid_pct = 100 * sum(validation_rsi) / len(validation_rsi) if validation_rsi else 0
    logger.info(f"RSI chính xác {valid_pct:.2f}% trên {len(validation_rsi)} mẫu có thể kiểm tra")
    
    # 4. Tính ATR (Average True Range)
    period = 14
    
    high = df_indicators['high']
    low = df_indicators['low']
    close = df_indicators['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
    df_indicators['tr'] = tr
    df_indicators['atr'] = tr.rolling(window=period).mean()
    df_indicators['atr_percent'] = df_indicators['atr'] / df_indicators['close'] * 100
    
    # Kiểm tra độ chính xác ATR
    validation_atr = []
    for i in range(period + 10, len(df_indicators), 10):  # Kiểm tra mỗi 10 dòng
        expected_atr = tr.iloc[i-period+1:i+1].mean()
        actual_atr = df_indicators['atr'].iloc[i]
        
        if not np.isnan(actual_atr):
            is_valid = np.isclose(expected_atr, actual_atr, rtol=1e-10)
            if not is_valid:
                logger.warning(f"ATR không chính xác tại dòng {i}: Expected {expected_atr}, Got {actual_atr}")
            validation_atr.append(is_valid)
    
    valid_pct = 100 * sum(validation_atr) / len(validation_atr) if validation_atr else 0
    logger.info(f"ATR chính xác {valid_pct:.2f}% trên {len(validation_atr)} mẫu có thể kiểm tra")
    
    return df_indicators


def detect_market_regimes(df):
    """
    Phát hiện các chế độ thị trường và kiểm tra độ chính xác
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV và các chỉ báo
    
    Returns:
        pd.DataFrame: DataFrame với chế độ thị trường đã được đánh dấu
    """
    logger.info("Phát hiện các chế độ thị trường...")
    
    # Đảm bảo DataFrame đã có các chỉ báo cần thiết
    required_cols = ['close', 'sma_20', 'sma_50', 'bb_width', 'atr_percent', 'rsi']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"Thiếu các cột: {missing_cols}. Tính toán các chỉ báo cần thiết...")
        df = calculate_basic_indicators(df)
    
    # Sao chép DataFrame để không ảnh hưởng đến dữ liệu gốc
    df_regimes = df.copy()
    
    # 1. Phát hiện xu hướng dựa trên SMA
    df_regimes['trend'] = 'neutral'
    df_regimes.loc[(df_regimes['close'] > df_regimes['sma_50']) & 
                 (df_regimes['sma_20'] > df_regimes['sma_50']), 'trend'] = 'uptrend'
    df_regimes.loc[(df_regimes['close'] < df_regimes['sma_50']) & 
                 (df_regimes['sma_20'] < df_regimes['sma_50']), 'trend'] = 'downtrend'
    
    # 2. Phát hiện thị trường sideway dựa trên BB width và ATR
    # Thị trường sideway có đặc trưng: BB width thấp và ATR% thấp
    bb_threshold = df_regimes['bb_width'].rolling(window=60).mean().iloc[-1] * 0.8
    atr_threshold = df_regimes['atr_percent'].rolling(window=60).mean().iloc[-1] * 0.8
    
    df_regimes['is_sideway'] = (df_regimes['bb_width'] < bb_threshold) & \
                             (df_regimes['atr_percent'] < atr_threshold)
    
    # 3. Tính điểm sideway dựa trên nhiều tiêu chí
    # Tính BB squeeze (Bollinger Bands thu hẹp)
    df_regimes['bb_squeeze'] = 1 - df_regimes['bb_width'] / df_regimes['bb_width'].rolling(window=100).max()
    
    # Tính RSI trung tính (gần 50)
    df_regimes['rsi_neutral'] = 1 - abs(df_regimes['rsi'] - 50) / 50
    
    # Kết hợp chỉ số để có điểm sideway tổng hợp
    bb_weight = 0.5
    atr_weight = 0.3
    rsi_weight = 0.2
    
    # Chuẩn hóa ATR%
    max_atr = df_regimes['atr_percent'].rolling(window=100).max()
    df_regimes['atr_low'] = 1 - (df_regimes['atr_percent'] / max_atr)
    
    # Tính điểm sideway
    df_regimes['sideways_score'] = (bb_weight * df_regimes['bb_squeeze'] + 
                                 atr_weight * df_regimes['atr_low'] + 
                                 rsi_weight * df_regimes['rsi_neutral'])
    
    # 4. Đánh dấu các vùng có điểm sideway cao
    high_sideway_threshold = 0.7
    df_regimes['is_strong_sideway'] = df_regimes['sideways_score'] > high_sideway_threshold
    
    # 5. Phát hiện thị trường biến động cao (volatile)
    volatility_threshold = df_regimes['atr_percent'].rolling(window=60).mean().iloc[-1] * 1.5
    df_regimes['is_volatile'] = df_regimes['atr_percent'] > volatility_threshold
    
    # 6. Phân loại thành các chế độ thị trường
    df_regimes['market_regime'] = 'normal'
    df_regimes.loc[df_regimes['is_strong_sideway'], 'market_regime'] = 'sideways'
    df_regimes.loc[df_regimes['is_volatile'] & (df_regimes['trend'] == 'uptrend'), 'market_regime'] = 'volatile_uptrend'
    df_regimes.loc[df_regimes['is_volatile'] & (df_regimes['trend'] == 'downtrend'), 'market_regime'] = 'volatile_downtrend'
    
    # 7. Kiểm tra tính nhất quán của việc phân loại
    # Kiểm tra xem có trường hợp nào được gán cả sideway và volatile không
    contradictory = df_regimes[(df_regimes['is_strong_sideway']) & (df_regimes['is_volatile'])]
    if len(contradictory) > 0:
        logger.warning(f"Có {len(contradictory)} trường hợp được đánh dấu cả sideway và volatile, điều này có thể không hợp lý")
        
    # Kiểm tra sự chuyển tiếp đột ngột giữa các chế độ
    regime_changes = (df_regimes['market_regime'] != df_regimes['market_regime'].shift(1)).sum()
    total_records = len(df_regimes)
    change_pct = regime_changes / total_records * 100
    
    if change_pct > 20:  # Nếu có hơn 20% dữ liệu là chuyển tiếp chế độ thị trường
        logger.warning(f"Có {regime_changes} thay đổi chế độ thị trường ({change_pct:.2f}% tổng dữ liệu), điều này có thể chỉ ra quá nhiều chuyển tiếp đột ngột")
    else:
        logger.info(f"Có {regime_changes} thay đổi chế độ thị trường ({change_pct:.2f}% tổng dữ liệu)")
    
    return df_regimes


def validate_trading_signals(df):
    """
    Tạo tín hiệu giao dịch dựa trên chế độ thị trường và xác thực tính chính xác
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV, chỉ báo và chế độ thị trường
    
    Returns:
        pd.DataFrame: DataFrame với tín hiệu giao dịch
    """
    logger.info("Tạo và xác thực tín hiệu giao dịch...")
    
    # Đảm bảo chế độ thị trường đã được phát hiện
    if 'market_regime' not in df.columns:
        logger.warning("Chưa phát hiện chế độ thị trường. Thực hiện phát hiện...")
        df = detect_market_regimes(df)
    
    # Sao chép DataFrame để không ảnh hưởng đến dữ liệu gốc
    df_signals = df.copy()
    
    # 1. Tạo tín hiệu dựa trên chế độ thị trường
    
    # Tạo cột tín hiệu
    df_signals['buy_signal'] = False
    df_signals['sell_signal'] = False
    df_signals['exit_long'] = False
    df_signals['exit_short'] = False
    
    # a. Chiến lược trend-following cho thị trường thông thường và volatile
    # Buy signal: SMA 20 cắt lên trên SMA 50 hoặc giá cắt lên trên SMA 20
    df_signals['sma_cross_up'] = (df_signals['sma_20'] > df_signals['sma_50']) & \
                               (df_signals['sma_20'].shift(1) <= df_signals['sma_50'].shift(1))
    
    df_signals['price_cross_sma20_up'] = (df_signals['close'] > df_signals['sma_20']) & \
                                       (df_signals['close'].shift(1) <= df_signals['sma_20'].shift(1))
    
    # Sell signal: SMA 20 cắt xuống dưới SMA 50 hoặc giá cắt xuống dưới SMA 20
    df_signals['sma_cross_down'] = (df_signals['sma_20'] < df_signals['sma_50']) & \
                                 (df_signals['sma_20'].shift(1) >= df_signals['sma_50'].shift(1))
    
    df_signals['price_cross_sma20_down'] = (df_signals['close'] < df_signals['sma_20']) & \
                                         (df_signals['close'].shift(1) >= df_signals['sma_20'].shift(1))
    
    # Tín hiệu trend-following
    trend_markets = df_signals['market_regime'].isin(['normal', 'volatile_uptrend', 'volatile_downtrend'])
    
    df_signals.loc[trend_markets & (df_signals['sma_cross_up'] | df_signals['price_cross_sma20_up']), 'buy_signal'] = True
    df_signals.loc[trend_markets & (df_signals['sma_cross_down'] | df_signals['price_cross_sma20_down']), 'sell_signal'] = True
    
    # b. Chiến lược mean-reversion cho thị trường sideway
    # Buy signal: Giá chạm BB dưới (%B < 0.1) và RSI < 30
    df_signals['percent_b'] = (df_signals['close'] - df_signals['lower_band']) / \
                            (df_signals['upper_band'] - df_signals['lower_band'])
    
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'buy_signal'] = \
        (df_signals['percent_b'] < 0.1) & (df_signals['rsi'] < 30)
    
    # Sell signal: Giá chạm BB trên (%B > 0.9) và RSI > 70
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'sell_signal'] = \
        (df_signals['percent_b'] > 0.9) & (df_signals['rsi'] > 70)
    
    # 2. Thêm tín hiệu thoát vị thế
    # Thoát long: Khi giá cắt xuống dưới SMA 20 (trend) hoặc RSI > 70 (sideway)
    df_signals.loc[trend_markets, 'exit_long'] = df_signals['price_cross_sma20_down']
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'exit_long'] = \
        (df_signals['rsi'] > 70) | (df_signals['percent_b'] > 0.9)
    
    # Thoát short: Khi giá cắt lên trên SMA 20 (trend) hoặc RSI < 30 (sideway)
    df_signals.loc[trend_markets, 'exit_short'] = df_signals['price_cross_sma20_up']
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'exit_short'] = \
        (df_signals['rsi'] < 30) | (df_signals['percent_b'] < 0.1)
    
    # 3. Tính toán kích thước lệnh điều chỉnh theo chế độ thị trường
    df_signals['position_size_multiplier'] = 1.0
    
    # Giảm kích thước cho thị trường sideway
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'position_size_multiplier'] = 0.5
    
    # Giảm kích thước cho thị trường volatile
    df_signals.loc[df_signals['market_regime'].isin(['volatile_uptrend', 'volatile_downtrend']), 'position_size_multiplier'] = 0.7
    
    # 4. Điều chỉnh stop loss và take profit theo chế độ thị trường
    df_signals['sl_multiplier'] = 1.0
    df_signals['tp_multiplier'] = 1.0
    
    # Thị trường sideway: SL rộng hơn và TP gần hơn
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'sl_multiplier'] = 1.5
    df_signals.loc[df_signals['market_regime'] == 'sideways', 'tp_multiplier'] = 0.7
    
    # Thị trường volatile: SL và TP đều rộng hơn
    df_signals.loc[df_signals['market_regime'].isin(['volatile_uptrend', 'volatile_downtrend']), 'sl_multiplier'] = 1.3
    df_signals.loc[df_signals['market_regime'].isin(['volatile_uptrend', 'volatile_downtrend']), 'tp_multiplier'] = 1.2
    
    # 5. Tính các điểm stop loss và take profit cơ bản
    # ATR-based stops
    atr_multiplier = 2.0
    df_signals['base_sl_pct'] = df_signals['atr'] / df_signals['close'] * atr_multiplier
    df_signals['adjusted_sl_pct'] = df_signals['base_sl_pct'] * df_signals['sl_multiplier']
    
    # R/R ratio 1:2 for take profit
    df_signals['base_tp_pct'] = df_signals['base_sl_pct'] * 2.0
    df_signals['adjusted_tp_pct'] = df_signals['base_tp_pct'] * df_signals['tp_multiplier']
    
    # 6. Kiểm tra tính hợp lý của tín hiệu
    # Đếm tổng số tín hiệu
    buy_signals = df_signals['buy_signal'].sum()
    sell_signals = df_signals['sell_signal'].sum()
    
    logger.info(f"Tổng số tín hiệu mua: {buy_signals}")
    logger.info(f"Tổng số tín hiệu bán: {sell_signals}")
    
    # Tính tỷ lệ tín hiệu so với tổng số dữ liệu
    buy_pct = buy_signals / len(df_signals) * 100
    sell_pct = sell_signals / len(df_signals) * 100
    
    logger.info(f"Tỷ lệ tín hiệu mua: {buy_pct:.2f}%")
    logger.info(f"Tỷ lệ tín hiệu bán: {sell_pct:.2f}%")
    
    # Kiểm tra nếu có quá nhiều hoặc quá ít tín hiệu
    if buy_pct > 10 or sell_pct > 10:
        logger.warning(f"Có quá nhiều tín hiệu (>10% tổng số dữ liệu), có thể cần điều chỉnh điều kiện nghiêm ngặt hơn")
    
    if buy_pct < 0.5 or sell_pct < 0.5:
        logger.warning(f"Có quá ít tín hiệu (<0.5% tổng số dữ liệu), có thể cần điều chỉnh điều kiện nới lỏng hơn")
    
    # 7. Kiểm tra tín hiệu giao nhau
    conflicting = df_signals[(df_signals['buy_signal'] & df_signals['sell_signal'])]
    if len(conflicting) > 0:
        logger.warning(f"Có {len(conflicting)} tín hiệu mua và bán xảy ra cùng lúc, điều này không hợp lý")
    
    # 8. Kiểm tra tính hợp lý của điều chỉnh stop loss và take profit
    # Kiểm tra xem SL và TP có quá lớn không
    max_sl_pct = df_signals['adjusted_sl_pct'].max()
    max_tp_pct = df_signals['adjusted_tp_pct'].max()
    
    if max_sl_pct > 0.1:  # >10%
        logger.warning(f"Stop loss điều chỉnh tối đa ({max_sl_pct*100:.2f}%) quá lớn, có thể dẫn đến lỗ lớn")
    
    if max_tp_pct > 0.2:  # >20%
        logger.warning(f"Take profit điều chỉnh tối đa ({max_tp_pct*100:.2f}%) có thể quá xa để đạt được")
    
    return df_signals


def backtest_trading_strategy(df_signals, initial_capital=10000, position_size_pct=0.02):
    """
    Mô phỏng backtest chiến lược giao dịch dựa trên tín hiệu và xác thực tính chính xác
    
    Args:
        df_signals (pd.DataFrame): DataFrame với dữ liệu OHLCV, chỉ báo và tín hiệu giao dịch
        initial_capital (float): Vốn ban đầu
        position_size_pct (float): Phần trăm vốn cho mỗi lệnh
        
    Returns:
        pd.DataFrame: DataFrame với kết quả backtest
        dict: Thông tin hiệu suất
    """
    logger.info("Thực hiện backtest và xác thực tính chính xác chiến lược...")
    
    # Đảm bảo tín hiệu đã được tạo
    required_cols = ['buy_signal', 'sell_signal', 'exit_long', 'exit_short', 
                    'position_size_multiplier', 'adjusted_sl_pct', 'adjusted_tp_pct']
    
    missing_cols = [col for col in required_cols if col not in df_signals.columns]
    
    if missing_cols:
        logger.warning(f"Thiếu các cột: {missing_cols}. Tạo tín hiệu giao dịch...")
        df_signals = validate_trading_signals(df_signals)
    
    # Sao chép DataFrame để không ảnh hưởng đến dữ liệu gốc
    df_backtest = df_signals.copy()
    
    # 1. Khởi tạo các biến theo dõi
    capital = initial_capital
    position = 0  # 0: không có vị thế, 1: long, -1: short
    entry_price = 0
    stop_loss_price = 0
    take_profit_price = 0
    position_size = 0
    
    # Tạo danh sách giao dịch để theo dõi
    trades = []
    
    # Thêm các cột backtest
    df_backtest['position'] = 0
    df_backtest['capital'] = initial_capital
    df_backtest['equity'] = initial_capital
    df_backtest['trade_pnl'] = 0.0
    
    # 2. Thực hiện backtest
    for i in range(1, len(df_backtest)):
        # Lấy dữ liệu hiện tại
        current_row = df_backtest.iloc[i]
        prev_row = df_backtest.iloc[i-1]
        
        # Cập nhật cột position
        df_backtest.at[df_backtest.index[i], 'position'] = position
        
        # Tính giá trị vị thế hiện tại
        if position != 0:
            price_diff = current_row['close'] - entry_price
            if position == -1:
                price_diff = -price_diff
                
            position_value = position_size + (position_size * price_diff / entry_price)
            equity = capital + position_value - position_size
            df_backtest.at[df_backtest.index[i], 'equity'] = equity
        else:
            df_backtest.at[df_backtest.index[i], 'capital'] = capital
            df_backtest.at[df_backtest.index[i], 'equity'] = capital
        
        # Kiểm tra thoát vị thế
        if position == 1:  # Đang có vị thế long
            # Kiểm tra stop loss
            if current_row['low'] <= stop_loss_price:
                # Kích hoạt stop loss
                trade_pnl = (stop_loss_price - entry_price) / entry_price
                trade_profit = position_size * trade_pnl
                capital += position_size + trade_profit
                
                # Ghi log
                logger.info(f"Thoát LONG qua stop loss tại {stop_loss_price:.2f}, Entry: {entry_price:.2f}, P/L: {trade_pnl*100:.2f}%, ${trade_profit:.2f}")
                
                # Lưu thông tin giao dịch
                trades.append({
                    'entry_date': df_backtest.index[i-1],
                    'exit_date': df_backtest.index[i],
                    'direction': 'long',
                    'entry_price': entry_price,
                    'exit_price': stop_loss_price,
                    'exit_type': 'stop_loss',
                    'pnl_pct': trade_pnl * 100,
                    'pnl_amount': trade_profit,
                    'market_regime': prev_row['market_regime']
                })
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'capital'] = capital
                df_backtest.at[df_backtest.index[i], 'equity'] = capital
                df_backtest.at[df_backtest.index[i], 'trade_pnl'] = trade_pnl * 100
                df_backtest.at[df_backtest.index[i], 'position'] = 0
                
                # Reset trạng thái
                position = 0
                entry_price = 0
                position_size = 0
                
            # Kiểm tra take profit
            elif current_row['high'] >= take_profit_price:
                # Kích hoạt take profit
                trade_pnl = (take_profit_price - entry_price) / entry_price
                trade_profit = position_size * trade_pnl
                capital += position_size + trade_profit
                
                # Ghi log
                logger.info(f"Thoát LONG qua take profit tại {take_profit_price:.2f}, Entry: {entry_price:.2f}, P/L: {trade_pnl*100:.2f}%, ${trade_profit:.2f}")
                
                # Lưu thông tin giao dịch
                trades.append({
                    'entry_date': df_backtest.index[i-1],
                    'exit_date': df_backtest.index[i],
                    'direction': 'long',
                    'entry_price': entry_price,
                    'exit_price': take_profit_price,
                    'exit_type': 'take_profit',
                    'pnl_pct': trade_pnl * 100,
                    'pnl_amount': trade_profit,
                    'market_regime': prev_row['market_regime']
                })
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'capital'] = capital
                df_backtest.at[df_backtest.index[i], 'equity'] = capital
                df_backtest.at[df_backtest.index[i], 'trade_pnl'] = trade_pnl * 100
                df_backtest.at[df_backtest.index[i], 'position'] = 0
                
                # Reset trạng thái
                position = 0
                entry_price = 0
                position_size = 0
                
            # Kiểm tra tín hiệu thoát
            elif current_row['exit_long']:
                # Tính P/L
                exit_price = current_row['close']
                trade_pnl = (exit_price - entry_price) / entry_price
                trade_profit = position_size * trade_pnl
                capital += position_size + trade_profit
                
                # Ghi log
                logger.info(f"Thoát LONG qua tín hiệu tại {exit_price:.2f}, Entry: {entry_price:.2f}, P/L: {trade_pnl*100:.2f}%, ${trade_profit:.2f}")
                
                # Lưu thông tin giao dịch
                trades.append({
                    'entry_date': df_backtest.index[i-1],
                    'exit_date': df_backtest.index[i],
                    'direction': 'long',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_type': 'signal',
                    'pnl_pct': trade_pnl * 100,
                    'pnl_amount': trade_profit,
                    'market_regime': prev_row['market_regime']
                })
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'capital'] = capital
                df_backtest.at[df_backtest.index[i], 'equity'] = capital
                df_backtest.at[df_backtest.index[i], 'trade_pnl'] = trade_pnl * 100
                df_backtest.at[df_backtest.index[i], 'position'] = 0
                
                # Reset trạng thái
                position = 0
                entry_price = 0
                position_size = 0
        
        elif position == -1:  # Đang có vị thế short
            # Kiểm tra stop loss
            if current_row['high'] >= stop_loss_price:
                # Kích hoạt stop loss
                trade_pnl = (entry_price - stop_loss_price) / entry_price
                trade_profit = position_size * trade_pnl
                capital += position_size + trade_profit
                
                # Ghi log
                logger.info(f"Thoát SHORT qua stop loss tại {stop_loss_price:.2f}, Entry: {entry_price:.2f}, P/L: {trade_pnl*100:.2f}%, ${trade_profit:.2f}")
                
                # Lưu thông tin giao dịch
                trades.append({
                    'entry_date': df_backtest.index[i-1],
                    'exit_date': df_backtest.index[i],
                    'direction': 'short',
                    'entry_price': entry_price,
                    'exit_price': stop_loss_price,
                    'exit_type': 'stop_loss',
                    'pnl_pct': trade_pnl * 100,
                    'pnl_amount': trade_profit,
                    'market_regime': prev_row['market_regime']
                })
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'capital'] = capital
                df_backtest.at[df_backtest.index[i], 'equity'] = capital
                df_backtest.at[df_backtest.index[i], 'trade_pnl'] = trade_pnl * 100
                df_backtest.at[df_backtest.index[i], 'position'] = 0
                
                # Reset trạng thái
                position = 0
                entry_price = 0
                position_size = 0
                
            # Kiểm tra take profit
            elif current_row['low'] <= take_profit_price:
                # Kích hoạt take profit
                trade_pnl = (entry_price - take_profit_price) / entry_price
                trade_profit = position_size * trade_pnl
                capital += position_size + trade_profit
                
                # Ghi log
                logger.info(f"Thoát SHORT qua take profit tại {take_profit_price:.2f}, Entry: {entry_price:.2f}, P/L: {trade_pnl*100:.2f}%, ${trade_profit:.2f}")
                
                # Lưu thông tin giao dịch
                trades.append({
                    'entry_date': df_backtest.index[i-1],
                    'exit_date': df_backtest.index[i],
                    'direction': 'short',
                    'entry_price': entry_price,
                    'exit_price': take_profit_price,
                    'exit_type': 'take_profit',
                    'pnl_pct': trade_pnl * 100,
                    'pnl_amount': trade_profit,
                    'market_regime': prev_row['market_regime']
                })
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'capital'] = capital
                df_backtest.at[df_backtest.index[i], 'equity'] = capital
                df_backtest.at[df_backtest.index[i], 'trade_pnl'] = trade_pnl * 100
                df_backtest.at[df_backtest.index[i], 'position'] = 0
                
                # Reset trạng thái
                position = 0
                entry_price = 0
                position_size = 0
                
            # Kiểm tra tín hiệu thoát
            elif current_row['exit_short']:
                # Tính P/L
                exit_price = current_row['close']
                trade_pnl = (entry_price - exit_price) / entry_price
                trade_profit = position_size * trade_pnl
                capital += position_size + trade_profit
                
                # Ghi log
                logger.info(f"Thoát SHORT qua tín hiệu tại {exit_price:.2f}, Entry: {entry_price:.2f}, P/L: {trade_pnl*100:.2f}%, ${trade_profit:.2f}")
                
                # Lưu thông tin giao dịch
                trades.append({
                    'entry_date': df_backtest.index[i-1],
                    'exit_date': df_backtest.index[i],
                    'direction': 'short',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'exit_type': 'signal',
                    'pnl_pct': trade_pnl * 100,
                    'pnl_amount': trade_profit,
                    'market_regime': prev_row['market_regime']
                })
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'capital'] = capital
                df_backtest.at[df_backtest.index[i], 'equity'] = capital
                df_backtest.at[df_backtest.index[i], 'trade_pnl'] = trade_pnl * 100
                df_backtest.at[df_backtest.index[i], 'position'] = 0
                
                # Reset trạng thái
                position = 0
                entry_price = 0
                position_size = 0
        
        # Kiểm tra tín hiệu vào lệnh mới (chỉ khi không có vị thế hiện tại)
        if position == 0:
            # Kiểm tra tín hiệu mua
            if current_row['buy_signal']:
                # Tính toán kích thước vị thế
                adjusted_position_size_pct = position_size_pct * current_row['position_size_multiplier']
                position_size = capital * adjusted_position_size_pct
                
                # Thiết lập thông tin vị thế
                position = 1
                entry_price = current_row['close']
                stop_loss_price = entry_price * (1 - current_row['adjusted_sl_pct'])
                take_profit_price = entry_price * (1 + current_row['adjusted_tp_pct'])
                
                # Ghi log
                logger.info(f"Mở vị thế LONG tại {entry_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}, Size: ${position_size:.2f}")
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'position'] = position
                df_backtest.at[df_backtest.index[i], 'equity'] = capital  # Equity không đổi ngay sau khi mở vị thế
                
            # Kiểm tra tín hiệu bán
            elif current_row['sell_signal']:
                # Tính toán kích thước vị thế
                adjusted_position_size_pct = position_size_pct * current_row['position_size_multiplier']
                position_size = capital * adjusted_position_size_pct
                
                # Thiết lập thông tin vị thế
                position = -1
                entry_price = current_row['close']
                stop_loss_price = entry_price * (1 + current_row['adjusted_sl_pct'])
                take_profit_price = entry_price * (1 - current_row['adjusted_tp_pct'])
                
                # Ghi log
                logger.info(f"Mở vị thế SHORT tại {entry_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}, Size: ${position_size:.2f}")
                
                # Cập nhật backtest
                df_backtest.at[df_backtest.index[i], 'position'] = position
                df_backtest.at[df_backtest.index[i], 'equity'] = capital  # Equity không đổi ngay sau khi mở vị thế
    
    # 3. Tính toán các chỉ số hiệu suất
    trades_df = pd.DataFrame(trades)
    
    if len(trades_df) == 0:
        logger.warning("Không có giao dịch nào được thực hiện trong thời gian backtest")
        return df_backtest, {
            'total_trades': 0,
            'win_rate': 0,
            'final_capital': capital,
            'total_return': (capital / initial_capital - 1) * 100,
            'max_drawdown': 0
        }
    
    # Tính thống kê hiệu suất
    trades_df['is_win'] = trades_df['pnl_pct'] > 0
    
    total_trades = len(trades_df)
    winning_trades = trades_df['is_win'].sum()
    win_rate = winning_trades / total_trades * 100
    
    average_win = trades_df[trades_df['is_win']]['pnl_pct'].mean() if winning_trades > 0 else 0
    average_loss = trades_df[~trades_df['is_win']]['pnl_pct'].mean() if total_trades - winning_trades > 0 else 0
    
    profit_factor = abs(trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum() / 
                    trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum()) if trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum() != 0 else float('inf')
    
    # Tính max drawdown
    df_backtest['peak'] = df_backtest['equity'].cummax()
    df_backtest['drawdown'] = (df_backtest['equity'] / df_backtest['peak'] - 1) * 100
    max_drawdown = df_backtest['drawdown'].min()
    
    # 4. Xác thực tính nhất quán của kết quả backtest
    # Kiểm tra xem số tiền cuối cùng có hợp lý không
    expected_final_capital = initial_capital * (1 + trades_df['pnl_amount'].sum() / initial_capital)
    actual_final_capital = df_backtest['capital'].iloc[-1]
    
    if not np.isclose(expected_final_capital, actual_final_capital, rtol=1e-3):
        logger.warning(f"Không nhất quán trong tính toán capital: Expected {expected_final_capital:.2f}, Got {actual_final_capital:.2f}")
    
    # Kiểm tra số lượng giao dịch có vượt quá số lượng tín hiệu không
    total_buy_signals = df_signals['buy_signal'].sum()
    total_sell_signals = df_signals['sell_signal'].sum()
    
    long_trades = len(trades_df[trades_df['direction'] == 'long'])
    short_trades = len(trades_df[trades_df['direction'] == 'short'])
    
    if long_trades > total_buy_signals:
        logger.warning(f"Số lượng giao dịch long ({long_trades}) vượt quá số lượng tín hiệu mua ({total_buy_signals})")
    
    if short_trades > total_sell_signals:
        logger.warning(f"Số lượng giao dịch short ({short_trades}) vượt quá số lượng tín hiệu bán ({total_sell_signals})")
    
    # Phân tích hiệu suất theo chế độ thị trường
    regime_performance = trades_df.groupby('market_regime').agg({
        'pnl_pct': ['mean', 'sum', 'count'],
        'is_win': 'mean'
    })
    
    # 5. In tổng kết hiệu suất
    logger.info("\n===== BACKTEST PERFORMANCE =====")
    logger.info(f"Số vốn ban đầu: ${initial_capital:.2f}")
    logger.info(f"Số vốn cuối cùng: ${actual_final_capital:.2f}")
    logger.info(f"Tổng lợi nhuận: {(actual_final_capital / initial_capital - 1) * 100:.2f}%")
    logger.info(f"Tổng số giao dịch: {total_trades}")
    logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
    logger.info(f"Lợi nhuận trung bình mỗi giao dịch thắng: {average_win:.2f}%")
    logger.info(f"Lỗ trung bình mỗi giao dịch thua: {average_loss:.2f}%")
    logger.info(f"Profit factor: {profit_factor:.2f}")
    logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
    
    logger.info("\n----- Hiệu Suất Theo Chế Độ Thị Trường -----")
    for regime, stats in regime_performance.iterrows():
        logger.info(f"{regime}:")
        logger.info(f"  - Số giao dịch: {stats[('pnl_pct', 'count')]:.0f}")
        logger.info(f"  - Tỷ lệ thắng: {stats[('is_win', 'mean')] * 100:.2f}%")
        logger.info(f"  - Lợi nhuận trung bình: {stats[('pnl_pct', 'mean')]:.2f}%")
        logger.info(f"  - Tổng lợi nhuận: {stats[('pnl_pct', 'sum')]:.2f}%")
    
    # 6. Lưu kết quả
    performance_summary = {
        'initial_capital': initial_capital,
        'final_capital': actual_final_capital,
        'total_return': (actual_final_capital / initial_capital - 1) * 100,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'average_win': average_win,
        'average_loss': average_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'regime_performance': regime_performance.to_dict()
    }
    
    return df_backtest, performance_summary


def create_visualization(df_backtest, trades_df=None, performance=None):
    """
    Tạo biểu đồ trực quan từ kết quả backtest
    
    Args:
        df_backtest (pd.DataFrame): DataFrame với kết quả backtest
        trades_df (pd.DataFrame, optional): DataFrame với thông tin giao dịch
        performance (dict, optional): Thông tin hiệu suất
        
    Returns:
        list: Đường dẫn đến các file biểu đồ
    """
    logger.info("Tạo biểu đồ trực quan từ kết quả phân tích và backtest...")
    
    chart_files = []
    
    # 1. Biểu đồ giá và chế độ thị trường
    plt.figure(figsize=(14, 7))
    plt.subplot(2, 1, 1)
    
    # Vẽ đường giá
    plt.plot(df_backtest.index, df_backtest['close'], label='Giá đóng cửa')
    
    # Thêm SMA
    if 'sma_20' in df_backtest.columns:
        plt.plot(df_backtest.index, df_backtest['sma_20'], label='SMA 20', linestyle='--')
    if 'sma_50' in df_backtest.columns:
        plt.plot(df_backtest.index, df_backtest['sma_50'], label='SMA 50', linestyle='--')
    
    # Thêm Bollinger Bands
    if all(col in df_backtest.columns for col in ['upper_band', 'lower_band']):
        plt.plot(df_backtest.index, df_backtest['upper_band'], label='Upper BB', linestyle=':')
        plt.plot(df_backtest.index, df_backtest['lower_band'], label='Lower BB', linestyle=':')
    
    # Thêm các vùng chế độ thị trường
    if 'market_regime' in df_backtest.columns:
        regimes = df_backtest['market_regime'].unique()
        colors = {'normal': 'white', 'sideways': 'gray', 'volatile_uptrend': 'lightgreen', 'volatile_downtrend': 'salmon'}
        
        for regime in regimes:
            regime_periods = df_backtest[df_backtest['market_regime'] == regime]
            starts = regime_periods.index[0]
            if len(regime_periods) > 1:
                # Tô màu vùng chế độ thị trường
                for i in range(len(regime_periods) - 1):
                    if i == 0:
                        plt.axvspan(regime_periods.index[i], regime_periods.index[i+1], alpha=0.2, color=colors.get(regime, 'white'), label=regime)
                    else:
                        plt.axvspan(regime_periods.index[i], regime_periods.index[i+1], alpha=0.2, color=colors.get(regime, 'white'))
    
    plt.title('Diễn Biến Giá và Chế Độ Thị Trường')
    plt.legend()
    
    # Subplot cho RSI
    plt.subplot(2, 1, 2)
    if 'rsi' in df_backtest.columns:
        plt.plot(df_backtest.index, df_backtest['rsi'], label='RSI')
        plt.axhline(y=70, color='r', linestyle='--')
        plt.axhline(y=30, color='g', linestyle='--')
        plt.title('RSI')
        plt.legend()
    
    # Lưu biểu đồ
    chart_path = 'validation_results/market_regimes.png'
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    chart_files.append(chart_path)
    logger.info(f"Đã lưu biểu đồ chế độ thị trường: {chart_path}")
    
    # 2. Biểu đồ vốn và drawdown
    plt.figure(figsize=(14, 8))
    
    # Vẽ vốn
    plt.subplot(2, 1, 1)
    plt.plot(df_backtest.index, df_backtest['equity'], label='Equity')
    plt.title('Vốn Theo Thời Gian')
    plt.legend()
    
    # Vẽ drawdown
    plt.subplot(2, 1, 2)
    plt.fill_between(df_backtest.index, df_backtest['drawdown'], 0, color='r', alpha=0.3)
    plt.title('Drawdown (%)')
    
    # Lưu biểu đồ
    chart_path = 'validation_results/equity_drawdown.png'
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    
    chart_files.append(chart_path)
    logger.info(f"Đã lưu biểu đồ vốn và drawdown: {chart_path}")
    
    # 3. Biểu đồ hiệu suất theo chế độ thị trường
    if performance is not None and 'regime_performance' in performance:
        # Chuẩn bị dữ liệu
        regimes = list(performance['regime_performance'].keys())
        
        # Tạo dữ liệu win rate
        win_rates = [performance['regime_performance'][regime][('is_win', 'mean')] * 100 
                    for regime in regimes]
        
        # Tạo dữ liệu lợi nhuận trung bình
        avg_profits = [performance['regime_performance'][regime][('pnl_pct', 'mean')]
                      for regime in regimes]
        
        # Tạo dữ liệu số lượng giao dịch
        trade_counts = [performance['regime_performance'][regime][('pnl_pct', 'count')]
                       for regime in regimes]
        
        # Vẽ biểu đồ
        plt.figure(figsize=(14, 10))
        
        # Win rate
        plt.subplot(3, 1, 1)
        bars = plt.bar(regimes, win_rates)
        plt.axhline(y=50, color='r', linestyle='--')
        plt.title('Tỷ Lệ Thắng Theo Chế Độ Thị Trường (%)')
        plt.ylabel('Win Rate (%)')
        
        # Thêm giá trị trên mỗi cột
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        # Lợi nhuận trung bình
        plt.subplot(3, 1, 2)
        bars = plt.bar(regimes, avg_profits)
        plt.axhline(y=0, color='r', linestyle='--')
        plt.title('Lợi Nhuận Trung Bình Theo Chế Độ Thị Trường (%)')
        plt.ylabel('Average P/L (%)')
        
        # Thêm giá trị trên mỗi cột
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.1f}%', ha='center', va='bottom')
        
        # Số lượng giao dịch
        plt.subplot(3, 1, 3)
        bars = plt.bar(regimes, trade_counts)
        plt.title('Số Lượng Giao Dịch Theo Chế Độ Thị Trường')
        plt.ylabel('Số Giao Dịch')
        
        # Thêm giá trị trên mỗi cột
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Lưu biểu đồ
        chart_path = 'validation_results/regime_performance.png'
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()
        
        chart_files.append(chart_path)
        logger.info(f"Đã lưu biểu đồ hiệu suất theo chế độ thị trường: {chart_path}")
    
    return chart_files


def run_validation_test():
    """
    Chạy toàn bộ quy trình kiểm tra và xác thực
    """
    logger.info("===== BẮT ĐẦU KIỂM TRA VÀ XÁC THỰC HỆ THỐNG GIAO DỊCH =====")
    
    # 1. Tạo dữ liệu kiểm thử
    df = generate_test_data(type="synthetic")
    
    # 2. Tính toán các chỉ báo cơ bản và kiểm tra độ chính xác
    df_indicators = calculate_basic_indicators(df)
    
    # 3. Phát hiện các chế độ thị trường
    df_regimes = detect_market_regimes(df_indicators)
    
    # 4. Tạo tín hiệu giao dịch và xác thực
    df_signals = validate_trading_signals(df_regimes)
    
    # 5. Thực hiện backtest và kiểm tra tính chính xác
    df_backtest, performance = backtest_trading_strategy(df_signals)
    
    # 6. Tạo biểu đồ trực quan
    chart_files = create_visualization(df_backtest, performance=performance)
    
    # 7. Lưu kết quả
    results_path = 'validation_results/validation_results.json'
    with open(results_path, 'w') as f:
        json.dump(performance, f, indent=4)
    
    logger.info(f"Đã lưu kết quả kiểm tra vào: {results_path}")
    
    logger.info("===== KẾT THÚC KIỂM TRA VÀ XÁC THỰC HỆ THỐNG GIAO DỊCH =====")
    
    # 8. Tóm tắt kết quả
    print("\n===== TÓM TẮT KẾT QUẢ KIỂM TRA =====")
    print(f"Tổng số giao dịch: {performance['total_trades']}")
    print(f"Tỷ lệ thắng: {performance['win_rate']:.2f}%")
    print(f"Lợi nhuận trung bình mỗi giao dịch thắng: {performance['average_win']:.2f}%")
    print(f"Lỗ trung bình mỗi giao dịch thua: {performance['average_loss']:.2f}%")
    print(f"Profit factor: {performance['profit_factor']:.2f}")
    print(f"Tổng lợi nhuận: {performance['total_return']:.2f}%")
    print(f"Drawdown tối đa: {performance['max_drawdown']:.2f}%")
    print(f"\nBiểu đồ kết quả đã được lưu vào thư mục: validation_results/")
    
    return df_backtest, performance


if __name__ == "__main__":
    # Chạy kiểm tra và xác thực
    run_validation_test()