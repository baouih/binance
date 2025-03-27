#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Backtest toàn diện hệ thống giao dịch
- Kiểm tra tất cả các chiến thuật giao dịch
- Sử dụng dữ liệu thực từ Binance
- Phân tích hiệu suất chi tiết
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback
import json
import concurrent.futures
import matplotlib.pyplot as plt
from binance.client import Client

# Thiết lập logging
log_file = f'full_system_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
result_dir = 'full_test_results'
os.makedirs(result_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(result_dir, log_file)),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('full_system_backtest')

# Danh sách tất cả các chiến thuật
ALL_STRATEGIES = [
    'ma_crossover',         # Chiến thuật cắt nhau MA
    'sideways_market',      # Chiến thuật thị trường đi ngang
    'rsi_divergence',       # Chiến thuật phân kỳ RSI
    'bollinger_breakout',   # Chiến thuật breakout Bollinger
    'multi_timeframe'       # Chiến thuật đa khung thời gian
]

# Danh sách tất cả các cặp tiền
ALL_SYMBOLS = [
    'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'XRP-USD',
    'ADA-USD', 'AVAX-USD', 'DOT-USD', 'DOGE-USD', 'MATIC-USD'
]

# Danh sách các khung thời gian
ALL_TIMEFRAMES = ['1h', '4h', '1d']

def get_binance_data(symbol, interval='1d', days=180):
    """Lấy dữ liệu từ Binance API"""
    try:
        # Lấy API key và secret
        api_key = os.environ.get('BINANCE_API_KEY', '')
        api_secret = os.environ.get('BINANCE_API_SECRET', '')
        
        client = Client(api_key, api_secret)
        
        # Chuyển đổi symbol
        if '-USD' in symbol:
            symbol = symbol.replace('-USD', 'USDT')
        
        logger.info(f"Tải dữ liệu {symbol} từ Binance ({interval}, {days} ngày)")
        
        # Định dạng thời gian
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Lấy dữ liệu lịch sử
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_date.strftime('%Y-%m-%d'),
            end_str=end_date.strftime('%Y-%m-%d')
        )
        
        # Chuyển đổi sang DataFrame
        df = pd.DataFrame(
            klines,
            columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignored'
            ]
        )
        
        # Xử lý dữ liệu
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Chuyển đổi kiểu dữ liệu
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        # Đổi tên cột để tương thích với code
        df.rename(
            columns={
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            },
            inplace=True
        )
        
        logger.info(f"Đã tải {len(df)} dòng dữ liệu")
        return df
        
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ Binance: {e}")
        logger.error(traceback.format_exc())
        return None

def calculate_indicators(data):
    """Tính toán tất cả các chỉ báo kỹ thuật cần thiết"""
    try:
        df = data.copy()
        
        # ===== Chỉ báo xu hướng =====
        # Moving Averages
        df['sma5'] = df['Close'].rolling(window=5).mean()
        df['sma10'] = df['Close'].rolling(window=10).mean()
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['sma50'] = df['Close'].rolling(window=50).mean()
        df['sma100'] = df['Close'].rolling(window=100).mean()
        df['sma200'] = df['Close'].rolling(window=200).mean()
        
        # Exponential Moving Averages
        df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['ema55'] = df['Close'].ewm(span=55, adjust=False).mean()
        
        # MACD
        df['ema12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ===== Chỉ báo dao động =====
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Stochastic
        df['stoch_k'] = ((df['Close'] - df['Low'].rolling(14).min()) / 
                        (df['High'].rolling(14).max() - df['Low'].rolling(14).min())) * 100
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # ===== Chỉ báo biến động =====
        # ATR
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        df['atr_pct'] = (df['atr'] / df['Close']) * 100
        
        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(window=20).mean()
        df['bb_std'] = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
        df['bb_width_avg'] = df['bb_width'].rolling(30).mean()
        
        # ADX (Average Directional Index)
        # +DM & -DM
        df['high_shift'] = df['High'].shift(1)
        df['low_shift'] = df['Low'].shift(1)
        
        df['plus_dm'] = np.where(
            (df['High'] - df['high_shift']) > (df['low_shift'] - df['Low']),
            np.maximum(df['High'] - df['high_shift'], 0),
            0
        )
        df['minus_dm'] = np.where(
            (df['low_shift'] - df['Low']) > (df['High'] - df['high_shift']),
            np.maximum(df['low_shift'] - df['Low'], 0),
            0
        )
        
        # True Range
        df['tr'] = true_range
        
        # Smoothed +DM, -DM, and TR
        df['plus_di'] = 100 * (df['plus_dm'].rolling(14).sum() / df['tr'].rolling(14).sum())
        df['minus_di'] = 100 * (df['minus_dm'].rolling(14).sum() / df['tr'].rolling(14).sum())
        
        # DX & ADX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Loại bỏ các dòng có NaN do tính toán chỉ báo
        df = df.dropna()
        
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi tính chỉ báo: {e}")
        logger.error(traceback.format_exc())
        return None

def detect_sideways_market(data):
    """Phát hiện thị trường đi ngang"""
    try:
        df = data.copy()
        
        # Giá trị ngưỡng
        price_range_threshold = 5.0  # Biên độ dao động giá trong 20 ngày < 5%
        atr_volatility_threshold = 2.0  # Biến động ATR < 2%
        adx_threshold = 25  # ADX < 25 chỉ báo thị trường yếu
        bb_width_ratio_threshold = 0.95  # BB width < 95% BB width trung bình
        
        # Tính price range trong 20 nến
        df['price_range'] = df['High'].rolling(20).max() - df['Low'].rolling(20).min()
        df['price_range_pct'] = (df['price_range'] / df['Low'].rolling(20).min()) * 100
        
        # Xác định thị trường đi ngang
        df['is_sideways'] = (
            (df['price_range_pct'] < price_range_threshold) & 
            (df['atr_pct'] < atr_volatility_threshold) &
            (df['bb_width'] < df['bb_width'] * bb_width_ratio_threshold) &
            (df['adx'] < adx_threshold)
        )
        
        # Xác định các giai đoạn thị trường đi ngang kéo dài
        sideways_periods = []
        current_sideways = {'start': None, 'end': None, 'duration': 0}
        min_sideways_duration = 5  # Ít nhất 5 nến
        
        for i, (index, row) in enumerate(df.iterrows()):
            if pd.notna(row['is_sideways']) and row['is_sideways']:
                if current_sideways['start'] is None:
                    current_sideways['start'] = i
                current_sideways['end'] = i
                current_sideways['duration'] += 1
            else:
                if (current_sideways['start'] is not None and 
                    current_sideways['duration'] >= min_sideways_duration):
                    sideways_periods.append({
                        'start_idx': current_sideways['start'],
                        'end_idx': current_sideways['end'],
                        'start_date': df.index[current_sideways['start']],
                        'end_date': df.index[current_sideways['end']],
                        'duration': current_sideways['duration']
                    })
                
                current_sideways = {'start': None, 'end': None, 'duration': 0}
        
        # Kiểm tra sideways period cuối cùng
        if (current_sideways['start'] is not None and 
            current_sideways['duration'] >= min_sideways_duration):
            sideways_periods.append({
                'start_idx': current_sideways['start'],
                'end_idx': current_sideways['end'],
                'start_date': df.index[current_sideways['start']],
                'end_date': df.index[current_sideways['end']],
                'duration': current_sideways['duration']
            })
        
        logger.info(f"Đã phát hiện {len(sideways_periods)} giai đoạn thị trường đi ngang")
        
        return df, sideways_periods
    
    except Exception as e:
        logger.error(f"Lỗi khi phát hiện thị trường đi ngang: {e}")
        logger.error(traceback.format_exc())
        return data, []

def detect_rsi_divergence(data):
    """Phát hiện tín hiệu phân kỳ RSI"""
    try:
        df = data.copy()
        divergences = []
        
        # Phát hiện phân kỳ RSI
        for i in range(30, len(df) - 5):
            # Tìm đỉnh giá trong 15 nến
            if all(df['Close'].iloc[i] > df['Close'].iloc[i-j] for j in range(1, 6)) and \
               all(df['Close'].iloc[i] > df['Close'].iloc[i+j] for j in range(1, 6)):
                
                # Tìm đỉnh RSI trong 15 nến
                rsi_peak_idx = df['rsi'].iloc[i-5:i+6].idxmax()
                
                # Tìm đỉnh giá trước đó
                for j in range(i - 30, i - 10):
                    if all(df['Close'].iloc[j] > df['Close'].iloc[j-k] for k in range(1, 6)) and \
                       all(df['Close'].iloc[j] > df['Close'].iloc[j+k] for k in range(1, 6)):
                        
                        # Tìm đỉnh RSI trước đó
                        prev_rsi_peak_idx = df['rsi'].iloc[j-5:j+6].idxmax()
                        
                        # Kiểm tra phân kỳ
                        if df['Close'].iloc[i] > df['Close'].iloc[j] and df['rsi'].loc[rsi_peak_idx] < df['rsi'].loc[prev_rsi_peak_idx]:
                            divergences.append({
                                'index': i,
                                'date': df.index[i],
                                'type': 'bearish',
                                'price_idx1': j,
                                'price_idx2': i,
                                'rsi_idx1': df.index.get_loc(prev_rsi_peak_idx),
                                'rsi_idx2': df.index.get_loc(rsi_peak_idx)
                            })
                            break
                
            # Tìm đáy giá trong 15 nến
            if all(df['Close'].iloc[i] < df['Close'].iloc[i-j] for j in range(1, 6)) and \
               all(df['Close'].iloc[i] < df['Close'].iloc[i+j] for j in range(1, 6)):
                
                # Tìm đáy RSI trong 15 nến
                rsi_bottom_idx = df['rsi'].iloc[i-5:i+6].idxmin()
                
                # Tìm đáy giá trước đó
                for j in range(i - 30, i - 10):
                    if all(df['Close'].iloc[j] < df['Close'].iloc[j-k] for k in range(1, 6)) and \
                       all(df['Close'].iloc[j] < df['Close'].iloc[j+k] for k in range(1, 6)):
                        
                        # Tìm đáy RSI trước đó
                        prev_rsi_bottom_idx = df['rsi'].iloc[j-5:j+6].idxmin()
                        
                        # Kiểm tra phân kỳ
                        if df['Close'].iloc[i] < df['Close'].iloc[j] and df['rsi'].loc[rsi_bottom_idx] > df['rsi'].loc[prev_rsi_bottom_idx]:
                            divergences.append({
                                'index': i,
                                'date': df.index[i],
                                'type': 'bullish',
                                'price_idx1': j,
                                'price_idx2': i,
                                'rsi_idx1': df.index.get_loc(prev_rsi_bottom_idx),
                                'rsi_idx2': df.index.get_loc(rsi_bottom_idx)
                            })
                            break
        
        logger.info(f"Đã phát hiện {len(divergences)} tín hiệu phân kỳ RSI")
        return divergences
    
    except Exception as e:
        logger.error(f"Lỗi khi phát hiện phân kỳ RSI: {e}")
        logger.error(traceback.format_exc())
        return []

def generate_strategy_signals(data, symbol, timeframe, strategy, sideways_periods=None, rsi_divergences=None):
    """Tạo tín hiệu dựa trên chiến thuật"""
    try:
        signals = []
        df = data.copy()
        
        if strategy == 'ma_crossover':
            # Tín hiệu MA Crossover
            ma_pairs = [
                ('sma5', 'sma20'),
                ('ema9', 'ema21'),
                ('sma20', 'sma50')
            ]
            
            for fast_ma, slow_ma in ma_pairs:
                # Kiểm tra các cột cần thiết
                if fast_ma not in df.columns or slow_ma not in df.columns:
                    continue
                
                # Tạo cột tín hiệu
                df[f'{fast_ma}_gt_{slow_ma}'] = df[fast_ma] > df[slow_ma]
                df[f'{fast_ma}_{slow_ma}_cross_up'] = (df[f'{fast_ma}_gt_{slow_ma}'] != df[f'{fast_ma}_gt_{slow_ma}'].shift(1)) & df[f'{fast_ma}_gt_{slow_ma}']
                df[f'{fast_ma}_{slow_ma}_cross_down'] = (df[f'{fast_ma}_gt_{slow_ma}'] != df[f'{fast_ma}_gt_{slow_ma}'].shift(1)) & ~df[f'{fast_ma}_gt_{slow_ma}']
                
                # Tìm tín hiệu LONG
                for i, (index, row) in enumerate(df.iterrows()):
                    if i < 2 or i >= len(df) - 2:
                        continue
                        
                    if row[f'{fast_ma}_{slow_ma}_cross_up']:
                        signals.append({
                            'date': index,
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'type': 'LONG',
                            'entry_price': row['Close'],
                            'strategy': strategy,
                            'signal_details': f'{fast_ma}_{slow_ma}_cross_up',
                            'index': i
                        })
                    
                    if row[f'{fast_ma}_{slow_ma}_cross_down']:
                        signals.append({
                            'date': index,
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'type': 'SHORT',
                            'entry_price': row['Close'],
                            'strategy': strategy,
                            'signal_details': f'{fast_ma}_{slow_ma}_cross_down',
                            'index': i
                        })
        
        elif strategy == 'sideways_market' and sideways_periods:
            # Tín hiệu Sideways Market
            for period in sideways_periods:
                start_idx = period['start_idx']
                end_idx = period['end_idx']
                
                # Lấy dữ liệu trong giai đoạn sideways
                period_data = df.iloc[start_idx:end_idx+1].copy()
                
                # Tín hiệu khi giá chạm cận dưới Bollinger
                period_data['lower_band_touch'] = (
                    (period_data['Close'] <= period_data['bb_lower']) & 
                    (period_data['Close'].shift(1) > period_data['bb_lower'].shift(1))
                )
                
                # Tín hiệu khi giá chạm cận trên Bollinger
                period_data['upper_band_touch'] = (
                    (period_data['Close'] >= period_data['bb_upper']) & 
                    (period_data['Close'].shift(1) < period_data['bb_upper'].shift(1))
                )
                
                # Lọc tín hiệu với RSI
                period_data['lower_band_signal'] = (
                    period_data['lower_band_touch'] & 
                    (period_data['rsi'] < 40)
                )
                
                period_data['upper_band_signal'] = (
                    period_data['upper_band_touch'] & 
                    (period_data['rsi'] > 60)
                )
                
                # Xử lý các tín hiệu
                for i, (date, row) in enumerate(period_data.iterrows()):
                    # Bỏ qua vị trí đầu và cuối
                    if i < 2 or i >= len(period_data) - 2:
                        continue
                    
                    if pd.notna(row['lower_band_signal']) and row['lower_band_signal']:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'type': 'LONG',
                            'entry_price': row['Close'],
                            'strategy': strategy,
                            'signal_details': 'bollinger_lower_rsi_oversold',
                            'index': start_idx + i
                        })
                    
                    if pd.notna(row['upper_band_signal']) and row['upper_band_signal']:
                        signals.append({
                            'date': date,
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'type': 'SHORT',
                            'entry_price': row['Close'],
                            'strategy': strategy,
                            'signal_details': 'bollinger_upper_rsi_overbought',
                            'index': start_idx + i
                        })
        
        elif strategy == 'rsi_divergence' and rsi_divergences:
            # Tín hiệu RSI Divergence
            for div in rsi_divergences:
                signals.append({
                    'date': div['date'],
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'type': 'LONG' if div['type'] == 'bullish' else 'SHORT',
                    'entry_price': df.iloc[div['index']]['Close'],
                    'strategy': strategy,
                    'signal_details': f'rsi_{div["type"]}_divergence',
                    'index': div['index']
                })
        
        elif strategy == 'bollinger_breakout':
            # Tín hiệu Bollinger Breakout
            df['bb_upper_breakout'] = (
                (df['Close'] > df['bb_upper']) & 
                (df['Close'].shift(1) <= df['bb_upper'].shift(1)) &
                (df['Volume'] > df['Volume'].rolling(20).mean() * 1.5)
            )
            
            df['bb_lower_breakout'] = (
                (df['Close'] < df['bb_lower']) & 
                (df['Close'].shift(1) >= df['bb_lower'].shift(1)) &
                (df['Volume'] > df['Volume'].rolling(20).mean() * 1.5)
            )
            
            # Xác định tín hiệu
            for i, (index, row) in enumerate(df.iterrows()):
                if i < 2 or i >= len(df) - 2:
                    continue
                
                if pd.notna(row['bb_upper_breakout']) and row['bb_upper_breakout']:
                    signals.append({
                        'date': index,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'type': 'LONG',
                        'entry_price': row['Close'],
                        'strategy': strategy,
                        'signal_details': 'bollinger_upper_breakout',
                        'index': i
                    })
                
                if pd.notna(row['bb_lower_breakout']) and row['bb_lower_breakout']:
                    signals.append({
                        'date': index,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'type': 'SHORT',
                        'entry_price': row['Close'],
                        'strategy': strategy,
                        'signal_details': 'bollinger_lower_breakout',
                        'index': i
                    })
        
        elif strategy == 'multi_timeframe':
            # Tín hiệu đã được tạo ra bởi các timeframe khác
            # Trong test này, multi_timeframe sẽ tạo tín hiệu khi 2 timeframe khác nhau đều có tín hiệu
            pass
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu cho chiến thuật {strategy} ({symbol}, {timeframe})")
        return signals
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo tín hiệu chiến thuật {strategy}: {e}")
        logger.error(traceback.format_exc())
        return []

def apply_risk_management(signals, data, initial_balance=10000.0, max_risk_per_trade=0.03, leverage=3):
    """Áp dụng quản lý rủi ro cho các tín hiệu"""
    try:
        for signal in signals:
            idx = signal['index']
            current_row = data.iloc[idx]
            
            # Lấy giá trị ATR
            atr = current_row['atr']
            
            # Tính kích thước vị thế
            position_size = initial_balance * max_risk_per_trade
            
            # Cập nhật signal
            signal['risk_per_trade'] = max_risk_per_trade
            signal['position_size'] = position_size
            signal['leverage'] = leverage
            
            if signal['type'] == 'LONG':
                # Áp dụng stop loss dựa trên ATR
                stop_loss = signal['entry_price'] - (2 * atr)
                
                # Áp dụng take profit với tỷ lệ risk:reward là 1:2
                take_profit = signal['entry_price'] + (4 * atr)
                
                # Thêm vào tín hiệu
                signal['stop_loss'] = stop_loss
                signal['take_profit'] = take_profit
                
                # Thêm các mức take profit từng phần
                signal['partial_take_profits'] = []
                for pct in [0.01, 0.02, 0.03, 0.05]:
                    tp_level = signal['entry_price'] * (1 + pct)
                    signal['partial_take_profits'].append({
                        'level': tp_level,
                        'percentage': 25.0,
                        'triggered': False
                    })
                
            else:  # SHORT
                # Áp dụng stop loss dựa trên ATR
                stop_loss = signal['entry_price'] + (2 * atr)
                
                # Áp dụng take profit với tỷ lệ risk:reward là 1:2
                take_profit = signal['entry_price'] - (4 * atr)
                
                # Thêm vào tín hiệu
                signal['stop_loss'] = stop_loss
                signal['take_profit'] = take_profit
                
                # Thêm các mức take profit từng phần
                signal['partial_take_profits'] = []
                for pct in [0.01, 0.02, 0.03, 0.05]:
                    tp_level = signal['entry_price'] * (1 - pct)
                    signal['partial_take_profits'].append({
                        'level': tp_level,
                        'percentage': 25.0,
                        'triggered': False
                    })
        
        logger.info(f"Đã áp dụng quản lý rủi ro cho {len(signals)} tín hiệu")
        return signals
    
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng quản lý rủi ro: {e}")
        logger.error(traceback.format_exc())
        return signals

def filter_signals(all_signals, data):
    """Lọc tín hiệu để loại bỏ các tín hiệu trùng lặp"""
    try:
        # Sắp xếp tín hiệu theo ngày
        sorted_signals = sorted(all_signals, key=lambda x: (x['date'], x['index']))
        
        # Lọc tín hiệu trong cùng ngày, ưu tiên chiến lược có độ tin cậy cao hơn
        filtered_signals = []
        current_date = None
        current_signals = []
        
        for signal in sorted_signals:
            signal_date = signal['date'].date() if hasattr(signal['date'], 'date') else signal['date']
            
            if current_date != signal_date:
                # Xử lý và lọc tín hiệu của ngày trước
                if current_signals:
                    # Ưu tiên theo chiến lược
                    strategy_priority = {
                        'rsi_divergence': 1,
                        'sideways_market': 2,
                        'ma_crossover': 3,
                        'bollinger_breakout': 4,
                        'multi_timeframe': 5
                    }
                    
                    # Sắp xếp theo ưu tiên
                    current_signals.sort(key=lambda x: strategy_priority.get(x['strategy'], 99))
                    
                    # Lấy tín hiệu ưu tiên cao nhất cho mỗi loại (LONG/SHORT)
                    long_signal = next((s for s in current_signals if s['type'] == 'LONG'), None)
                    short_signal = next((s for s in current_signals if s['type'] == 'SHORT'), None)
                    
                    if long_signal:
                        filtered_signals.append(long_signal)
                    
                    if short_signal:
                        filtered_signals.append(short_signal)
                
                # Reset cho ngày mới
                current_date = signal_date
                current_signals = [signal]
            else:
                current_signals.append(signal)
        
        # Xử lý các tín hiệu cuối cùng
        if current_signals:
            strategy_priority = {
                'rsi_divergence': 1,
                'sideways_market': 2,
                'ma_crossover': 3,
                'bollinger_breakout': 4,
                'multi_timeframe': 5
            }
            
            current_signals.sort(key=lambda x: strategy_priority.get(x['strategy'], 99))
            
            long_signal = next((s for s in current_signals if s['type'] == 'LONG'), None)
            short_signal = next((s for s in current_signals if s['type'] == 'SHORT'), None)
            
            if long_signal:
                filtered_signals.append(long_signal)
            
            if short_signal:
                filtered_signals.append(short_signal)
        
        logger.info(f"Đã lọc từ {len(all_signals)} xuống còn {len(filtered_signals)} tín hiệu")
        return filtered_signals
    
    except Exception as e:
        logger.error(f"Lỗi khi lọc tín hiệu: {e}")
        logger.error(traceback.format_exc())
        return all_signals

def simulate_trades(signals, data, initial_balance=10000.0):
    """Mô phỏng giao dịch với partial take profit"""
    try:
        trades = []
        balance = initial_balance
        active_trades = []
        max_simultaneous_trades = 3
        
        # Sắp xếp tín hiệu theo ngày
        sorted_signals = sorted(signals, key=lambda x: (x['date'], x['index']))
        
        # Mô phỏng giao dịch theo thời gian
        for date_idx, date in enumerate(data.index):
            # Đóng các giao dịch hiện tại nếu đạt điều kiện
            for trade in list(active_trades):
                # Lấy giá hiện tại
                current_price = data.iloc[date_idx]['Close']
                
                # Cập nhật trạng thái chốt lời từng phần
                if 'partial_take_profits' in trade:
                    for i, tp in enumerate(trade['partial_take_profits']):
                        if tp['triggered']:
                            continue
                            
                        # Kiểm tra giá chạm mức take profit
                        if (trade['type'] == 'LONG' and current_price >= tp['level']) or \
                           (trade['type'] == 'SHORT' and current_price <= tp['level']):
                            
                            # Tính kích thước và lợi nhuận cho phần này
                            tp_size = trade['position_size'] * (tp['percentage'] / 100)
                            
                            if trade['type'] == 'LONG':
                                partial_profit = tp_size * trade['leverage'] * (tp['level'] - trade['entry_price']) / trade['entry_price']
                            else:  # SHORT
                                partial_profit = tp_size * trade['leverage'] * (trade['entry_price'] - tp['level']) / trade['entry_price']
                            
                            # Cập nhật kích thước vị thế còn lại
                            trade['remaining_size'] -= tp_size
                            
                            # Cập nhật số dư
                            balance += partial_profit
                            trade['total_profit'] += partial_profit
                            
                            # Đánh dấu đã kích hoạt
                            trade['partial_take_profits'][i]['triggered'] = True
                            
                            # Thêm vào danh sách chốt lời từng phần
                            trade['partial_exits'].append({
                                'date': date,
                                'price': tp['level'],
                                'size': tp_size,
                                'profit': partial_profit
                            })
                            
                            # Di chuyển stop loss lên mức hòa vốn sau lần chốt lời đầu tiên
                            if i == 0 and not trade['stop_loss_moved']:
                                trade['stop_loss'] = trade['entry_price']
                                trade['stop_loss_moved'] = True
                
                # Kiểm tra stop loss
                if (trade['type'] == 'LONG' and current_price <= trade['stop_loss']) or \
                   (trade['type'] == 'SHORT' and current_price >= trade['stop_loss']):
                    
                    # Tính lợi nhuận cho phần còn lại
                    if trade['type'] == 'LONG':
                        remaining_profit = trade['remaining_size'] * trade['leverage'] * (trade['stop_loss'] - trade['entry_price']) / trade['entry_price']
                    else:  # SHORT
                        remaining_profit = trade['remaining_size'] * trade['leverage'] * (trade['entry_price'] - trade['stop_loss']) / trade['entry_price']
                    
                    # Cập nhật số dư và tổng lợi nhuận
                    balance += remaining_profit
                    trade['total_profit'] += remaining_profit
                    
                    # Đóng vị thế
                    trade['exit_date'] = date
                    trade['exit_price'] = trade['stop_loss']
                    trade['exit_reason'] = 'stop_loss'
                    trade['profit_pct'] = (trade['total_profit'] / (trade['position_size'] * trade['leverage'])) * 100
                    trade['balance_after'] = balance
                    
                    # Thêm vào danh sách giao dịch đã hoàn thành
                    trades.append(trade)
                    
                    # Xóa khỏi danh sách giao dịch đang hoạt động
                    active_trades.remove(trade)
                    continue
                
                # Kiểm tra take profit (nếu không dùng partial take profit)
                if 'partial_take_profits' not in trade:
                    if (trade['type'] == 'LONG' and current_price >= trade['take_profit']) or \
                       (trade['type'] == 'SHORT' and current_price <= trade['take_profit']):
                        
                        # Tính lợi nhuận
                        if trade['type'] == 'LONG':
                            profit = trade['position_size'] * trade['leverage'] * (trade['take_profit'] - trade['entry_price']) / trade['entry_price']
                        else:  # SHORT
                            profit = trade['position_size'] * trade['leverage'] * (trade['entry_price'] - trade['take_profit']) / trade['entry_price']
                        
                        # Cập nhật số dư
                        balance += profit
                        
                        # Đóng vị thế
                        trade['exit_date'] = date
                        trade['exit_price'] = trade['take_profit']
                        trade['exit_reason'] = 'take_profit'
                        trade['total_profit'] = profit
                        trade['profit_pct'] = (profit / (trade['position_size'] * trade['leverage'])) * 100
                        trade['balance_after'] = balance
                        
                        # Thêm vào danh sách giao dịch đã hoàn thành
                        trades.append(trade)
                        
                        # Xóa khỏi danh sách giao dịch đang hoạt động
                        active_trades.remove(trade)
                        continue
                
                # Kiểm tra nếu đã chốt hết vị thế
                if 'remaining_size' in trade and trade['remaining_size'] < 0.001:
                    trade['exit_date'] = date
                    trade['exit_price'] = current_price
                    trade['exit_reason'] = 'full_take_profit'
                    trade['profit_pct'] = (trade['total_profit'] / (trade['position_size'] * trade['leverage'])) * 100
                    trade['balance_after'] = balance
                    
                    # Thêm vào danh sách giao dịch đã hoàn thành
                    trades.append(trade)
                    
                    # Xóa khỏi danh sách giao dịch đang hoạt động
                    active_trades.remove(trade)
            
            # Mở giao dịch mới từ tín hiệu
            for signal in sorted_signals:
                if signal['date'] == date and len(active_trades) < max_simultaneous_trades:
                    # Tạo giao dịch mới
                    trade = signal.copy()
                    trade['entry_date'] = date
                    trade['remaining_size'] = trade['position_size']
                    trade['total_profit'] = 0
                    trade['partial_exits'] = []
                    trade['stop_loss_moved'] = False
                    
                    # Thêm vào danh sách giao dịch đang hoạt động
                    active_trades.append(trade)
        
        # Đóng các giao dịch còn lại ở cuối dữ liệu
        last_date = data.index[-1]
        last_price = data.iloc[-1]['Close']
        
        for trade in active_trades:
            # Tính lợi nhuận cho phần còn lại
            if trade['type'] == 'LONG':
                remaining_profit = trade['remaining_size'] * trade['leverage'] * (last_price - trade['entry_price']) / trade['entry_price']
            else:  # SHORT
                remaining_profit = trade['remaining_size'] * trade['leverage'] * (trade['entry_price'] - last_price) / trade['entry_price']
            
            # Cập nhật số dư và tổng lợi nhuận
            balance += remaining_profit
            trade['total_profit'] += remaining_profit
            
            # Đóng vị thế
            trade['exit_date'] = last_date
            trade['exit_price'] = last_price
            trade['exit_reason'] = 'end_of_data'
            trade['profit_pct'] = (trade['total_profit'] / (trade['position_size'] * trade['leverage'])) * 100
            trade['balance_after'] = balance
            
            # Thêm vào danh sách giao dịch đã hoàn thành
            trades.append(trade)
        
        # Tính thống kê
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['total_profit'] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        profit = balance - initial_balance
        profit_pct = (profit / initial_balance) * 100
        
        # Tính ROI
        roi = profit_pct
        
        # Tính drawdown
        max_balance = initial_balance
        max_drawdown = 0
        max_drawdown_pct = 0
        current_balance = initial_balance
        
        for trade in sorted(trades, key=lambda x: x['entry_date']):
            current_balance += trade['total_profit']
            
            if current_balance > max_balance:
                max_balance = current_balance
            
            drawdown = max_balance - current_balance
            drawdown_pct = (drawdown / max_balance) * 100
            
            if drawdown_pct > max_drawdown_pct:
                max_drawdown = drawdown
                max_drawdown_pct = drawdown_pct
        
        # Tính Sharpe Ratio (giả định)
        if len(trades) > 0:
            trade_returns = [t['profit_pct'] for t in trades]
            avg_return = np.mean(trade_returns)
            std_return = np.std(trade_returns) if len(trade_returns) > 1 else 1
            sharpe_ratio = avg_return / std_return if std_return != 0 else 0
        else:
            sharpe_ratio = 0
        
        # Tính metadata theo chiến thuật
        strategies_results = {}
        for strategy in ALL_STRATEGIES:
            strategy_trades = [t for t in trades if t['strategy'] == strategy]
            strategy_count = len(strategy_trades)
            
            if strategy_count > 0:
                strategy_win_count = sum(1 for t in strategy_trades if t['total_profit'] > 0)
                strategy_profit = sum(t['total_profit'] for t in strategy_trades)
                
                strategies_results[strategy] = {
                    'total_trades': strategy_count,
                    'winning_trades': strategy_win_count,
                    'win_rate': (strategy_win_count / strategy_count * 100),
                    'total_profit': strategy_profit,
                    'avg_profit_per_trade': strategy_profit / strategy_count
                }
        
        # Tạo summary
        summary = {
            'initial_balance': initial_balance,
            'final_balance': balance,
            'total_profit': profit,
            'total_profit_pct': profit_pct,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'roi': roi,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'sharpe_ratio': sharpe_ratio,
            'strategies_results': strategies_results
        }
        
        logger.info(f"\n=== KẾT QUẢ BACKTEST TỔNG THỂ ===")
        logger.info(f"Số giao dịch: {total_trades}")
        logger.info(f"Giao dịch thắng/thua: {winning_trades}/{losing_trades}")
        logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
        logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
        logger.info(f"Số dư cuối cùng: ${balance:.2f}")
        logger.info(f"Tổng lợi nhuận: ${profit:.2f} ({profit_pct:.2f}%)")
        logger.info(f"Drawdown tối đa: ${max_drawdown:.2f} ({max_drawdown_pct:.2f}%)")
        
        return trades, summary
    
    except Exception as e:
        logger.error(f"Lỗi khi mô phỏng giao dịch: {e}")
        logger.error(traceback.format_exc())
        return [], {'error': str(e)}

def analyze_timeframe_results(all_trades, timeframe):
    """Phân tích kết quả theo khung thời gian"""
    try:
        tf_trades = [t for t in all_trades if t['timeframe'] == timeframe]
        
        if not tf_trades:
            return None
        
        winning_trades = sum(1 for t in tf_trades if t['total_profit'] > 0)
        total_trades = len(tf_trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t['total_profit'] for t in tf_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        return {
            'timeframe': timeframe,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit
        }
    
    except Exception as e:
        logger.error(f"Lỗi khi phân tích kết quả theo khung thời gian {timeframe}: {e}")
        logger.error(traceback.format_exc())
        return None

def analyze_strategy_results(all_trades, strategy):
    """Phân tích kết quả theo chiến thuật"""
    try:
        strategy_trades = [t for t in all_trades if t['strategy'] == strategy]
        
        if not strategy_trades:
            return None
        
        winning_trades = sum(1 for t in strategy_trades if t['total_profit'] > 0)
        total_trades = len(strategy_trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t['total_profit'] for t in strategy_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        # Phân tích theo loại tín hiệu
        signal_details = {}
        for trade in strategy_trades:
            signal_type = trade.get('signal_details', 'unknown')
            if signal_type not in signal_details:
                signal_details[signal_type] = {
                    'count': 0,
                    'wins': 0,
                    'profit': 0
                }
            
            signal_details[signal_type]['count'] += 1
            if trade['total_profit'] > 0:
                signal_details[signal_type]['wins'] += 1
            signal_details[signal_type]['profit'] += trade['total_profit']
        
        # Tính tỷ lệ thắng cho từng loại tín hiệu
        for signal_type in signal_details:
            count = signal_details[signal_type]['count']
            wins = signal_details[signal_type]['wins']
            signal_details[signal_type]['win_rate'] = (wins / count * 100) if count > 0 else 0
            signal_details[signal_type]['avg_profit'] = signal_details[signal_type]['profit'] / count if count > 0 else 0
        
        return {
            'strategy': strategy,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit,
            'signal_details': signal_details
        }
    
    except Exception as e:
        logger.error(f"Lỗi khi phân tích kết quả theo chiến thuật {strategy}: {e}")
        logger.error(traceback.format_exc())
        return None

def analyze_symbol_results(all_trades, symbol):
    """Phân tích kết quả theo symbol"""
    try:
        symbol_trades = [t for t in all_trades if t['symbol'] == symbol]
        
        if not symbol_trades:
            return None
        
        winning_trades = sum(1 for t in symbol_trades if t['total_profit'] > 0)
        total_trades = len(symbol_trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t['total_profit'] for t in symbol_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        # Phân tích theo chiến thuật
        strategy_breakdown = {}
        for strategy in ALL_STRATEGIES:
            strategy_trades = [t for t in symbol_trades if t['strategy'] == strategy]
            if strategy_trades:
                strategy_win = sum(1 for t in strategy_trades if t['total_profit'] > 0)
                strategy_profit = sum(t['total_profit'] for t in strategy_trades)
                
                strategy_breakdown[strategy] = {
                    'count': len(strategy_trades),
                    'wins': strategy_win,
                    'win_rate': (strategy_win / len(strategy_trades) * 100),
                    'profit': strategy_profit,
                    'avg_profit': strategy_profit / len(strategy_trades)
                }
        
        return {
            'symbol': symbol,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit_per_trade': avg_profit,
            'strategy_breakdown': strategy_breakdown
        }
    
    except Exception as e:
        logger.error(f"Lỗi khi phân tích kết quả theo symbol {symbol}: {e}")
        logger.error(traceback.format_exc())
        return None

def test_single_symbol(symbol, timeframe='1d', period='6mo', initial_balance=10000.0):
    """Test một symbol cụ thể với đầy đủ thông tin"""
    try:
        logger.info(f"Test symbol {symbol} với {period} dữ liệu trên khung {timeframe}")
        
        # Map period sang số ngày
        period_days = {
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365
        }
        
        days = period_days.get(period, 180)
        
        # Map timeframe sang interval của Binance
        timeframe_map = {
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        
        interval = timeframe_map.get(timeframe, '1d')
        
        # Lấy dữ liệu từ Binance
        data = get_binance_data(symbol, interval=interval, days=days)
        
        if data is None:
            logger.error(f"Không thể lấy dữ liệu cho {symbol}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'period': period,
                'error': 'Không thể lấy dữ liệu'
            }
        
        # Tính toán các chỉ báo
        with_indicators = calculate_indicators(data)
        
        if with_indicators is None:
            logger.error(f"Lỗi khi tính chỉ báo cho {symbol}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'period': period,
                'error': 'Lỗi khi tính chỉ báo'
            }
        
        # Phát hiện thị trường đi ngang
        processed_data, sideways_periods = detect_sideways_market(with_indicators)
        
        # Phát hiện phân kỳ RSI
        rsi_divergences = detect_rsi_divergence(processed_data)
        
        # Khởi tạo danh sách tín hiệu
        all_signals = []
        
        # Tạo tín hiệu cho từng chiến thuật
        for strategy in ALL_STRATEGIES:
            signals = generate_strategy_signals(
                processed_data, 
                symbol, 
                timeframe, 
                strategy, 
                sideways_periods,
                rsi_divergences
            )
            all_signals.extend(signals)
        
        # Lọc tín hiệu
        filtered_signals = filter_signals(all_signals, processed_data)
        
        # Áp dụng quản lý rủi ro
        managed_signals = apply_risk_management(
            filtered_signals,
            processed_data,
            initial_balance=initial_balance,
            max_risk_per_trade=0.03,
            leverage=3
        )
        
        # Mô phỏng giao dịch
        trades, summary = simulate_trades(
            managed_signals,
            processed_data,
            initial_balance=initial_balance
        )
        
        # Tạo kết quả cho symbol
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'period': period,
            'total_data_points': len(processed_data),
            'initial_balance': initial_balance,
            'final_balance': summary.get('final_balance', initial_balance),
            'total_profit': summary.get('total_profit', 0),
            'total_profit_pct': summary.get('total_profit_pct', 0),
            'total_trades': summary.get('total_trades', 0),
            'winning_trades': summary.get('winning_trades', 0),
            'losing_trades': summary.get('losing_trades', 0),
            'win_rate': summary.get('win_rate', 0),
            'max_drawdown': summary.get('max_drawdown', 0),
            'max_drawdown_pct': summary.get('max_drawdown_pct', 0),
            'sharpe_ratio': summary.get('sharpe_ratio', 0),
            'sideways_periods': len(sideways_periods),
            'rsi_divergences': len(rsi_divergences),
            'signals': {
                'total': len(all_signals),
                'filtered': len(filtered_signals),
                'by_strategy': {s: len([sig for sig in all_signals if sig['strategy'] == s]) for s in ALL_STRATEGIES}
            },
            'strategies_results': summary.get('strategies_results', {})
        }
        
        # Lưu kết quả chi tiết
        detailed_result = {
            **result,
            'trades': [
                {k: str(v) if isinstance(v, (datetime, pd.Timestamp)) else v for k, v in t.items() 
                 if k not in ['partial_take_profits', 'partial_exits']}
                for t in trades
            ]
        }
        
        results_file = os.path.join(result_dir, f'{symbol.replace("-", "_")}_{timeframe}_{period}.json')
        with open(results_file, 'w') as f:
            json.dump(detailed_result, f, indent=4, default=str)
        
        logger.info(f"Hoàn thành test cho {symbol} ({timeframe}, {period})")
        logger.info(f"Tổng giao dịch: {result['total_trades']}, Win rate: {result['win_rate']:.2f}%, Lợi nhuận: {result['total_profit_pct']:.2f}%")
        
        return result
    
    except Exception as e:
        logger.error(f"Lỗi khi test {symbol}: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'period': period,
            'error': str(e)
        }

def run_full_backtest():
    """Chạy backtest toàn diện trên tất cả symbols và timeframes"""
    try:
        logger.info("BẮT ĐẦU BACKTEST TOÀN DIỆN HỆ THỐNG")
        logger.info(f"Số lượng symbols: {len(ALL_SYMBOLS)}")
        logger.info(f"Số lượng timeframes: {len(ALL_TIMEFRAMES)}")
        logger.info(f"Số lượng chiến thuật: {len(ALL_STRATEGIES)}")
        
        # Danh sách các cấu hình cần test
        test_configs = []
        
        for symbol in ALL_SYMBOLS:
            for timeframe in ALL_TIMEFRAMES:
                test_configs.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'period': '6mo',
                    'initial_balance': 10000.0
                })
        
        logger.info(f"Tổng số cấu hình cần test: {len(test_configs)}")
        
        # Chạy test tuần tự
        all_results = []
        for config in test_configs:
            result = test_single_symbol(**config)
            all_results.append(result)
        
        # Tạo báo cáo tổng hợp
        successful_results = [r for r in all_results if 'error' not in r]
        failed_results = [r for r in all_results if 'error' in r]
        
        final_report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(all_results),
            'successful_tests': len(successful_results),
            'failed_tests': len(failed_results),
            'timeframe_analysis': {},
            'strategy_analysis': {},
            'symbol_analysis': {},
            'overall_results': {}
        }
        
        # Tính toán tổng hợp
        if successful_results:
            # Tổng hợp tất cả giao dịch
            all_trades = []
            for result in successful_results:
                try:
                    trades_file = os.path.join(
                        result_dir, 
                        f"{result['symbol'].replace('-', '_')}_{result['timeframe']}_{result['period']}.json"
                    )
                    
                    with open(trades_file, 'r') as f:
                        detail_data = json.load(f)
                        if 'trades' in detail_data:
                            all_trades.extend(detail_data['trades'])
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file giao dịch {trades_file}: {e}")
            
            # Tính toán tổng quát
            total_trades = sum(r.get('total_trades', 0) for r in successful_results)
            winning_trades = sum(r.get('winning_trades', 0) for r in successful_results)
            total_profit = sum(r.get('total_profit', 0) for r in successful_results)
            
            # Tính tỉ lệ thắng
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Tính ROI trung bình
            avg_roi = sum(r.get('total_profit_pct', 0) for r in successful_results) / len(successful_results) if successful_results else 0
            
            # Tính drawdown tối đa
            max_drawdown = max(r.get('max_drawdown', 0) for r in successful_results)
            max_drawdown_pct = max(r.get('max_drawdown_pct', 0) for r in successful_results)
            
            # Cập nhật kết quả tổng thể
            final_report['overall_results'] = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_roi': avg_roi,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct
            }
            
            # Phân tích theo khung thời gian
            for timeframe in ALL_TIMEFRAMES:
                tf_analysis = analyze_timeframe_results(all_trades, timeframe)
                if tf_analysis:
                    final_report['timeframe_analysis'][timeframe] = tf_analysis
            
            # Phân tích theo chiến thuật
            for strategy in ALL_STRATEGIES:
                strategy_analysis = analyze_strategy_results(all_trades, strategy)
                if strategy_analysis:
                    final_report['strategy_analysis'][strategy] = strategy_analysis
            
            # Phân tích theo symbol
            for symbol in ALL_SYMBOLS:
                symbol_analysis = analyze_symbol_results(all_trades, symbol)
                if symbol_analysis:
                    final_report['symbol_analysis'][symbol] = symbol_analysis
        
        # Lưu báo cáo tổng hợp
        with open(os.path.join(result_dir, 'full_system_backtest_report.json'), 'w') as f:
            json.dump(final_report, f, indent=4, default=str)
        
        # Tạo báo cáo dạng văn bản
        with open(os.path.join(result_dir, 'full_system_backtest_report.txt'), 'w') as f:
            f.write("=== BÁO CÁO BACKTEST TOÀN DIỆN HỆ THỐNG ===\n\n")
            f.write(f"Ngày giờ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("I. TỔNG QUAN\n")
            f.write(f"Tổng số test: {len(all_results)}\n")
            f.write(f"Test thành công: {len(successful_results)}\n")
            f.write(f"Test thất bại: {len(failed_results)}\n\n")
            
            if 'overall_results' in final_report:
                overall = final_report['overall_results']
                f.write("II. KẾT QUẢ TỔNG THỂ\n")
                f.write(f"Tổng giao dịch: {overall.get('total_trades', 0)}\n")
                f.write(f"Giao dịch thắng: {overall.get('winning_trades', 0)}\n")
                f.write(f"Giao dịch thua: {overall.get('losing_trades', 0)}\n")
                f.write(f"Tỷ lệ thắng: {overall.get('win_rate', 0):.2f}%\n")
                f.write(f"Tổng lợi nhuận: ${overall.get('total_profit', 0):.2f}\n")
                f.write(f"ROI trung bình: {overall.get('avg_roi', 0):.2f}%\n")
                f.write(f"Drawdown tối đa: ${overall.get('max_drawdown', 0):.2f} ({overall.get('max_drawdown_pct', 0):.2f}%)\n\n")
            
            f.write("III. PHÂN TÍCH THEO CHIẾN THUẬT\n")
            for strategy, analysis in final_report.get('strategy_analysis', {}).items():
                f.write(f"\n{strategy.upper()}:\n")
                f.write(f"- Số giao dịch: {analysis.get('total_trades', 0)}\n")
                f.write(f"- Giao dịch thắng: {analysis.get('winning_trades', 0)}\n")
                f.write(f"- Tỷ lệ thắng: {analysis.get('win_rate', 0):.2f}%\n")
                f.write(f"- Tổng lợi nhuận: ${analysis.get('total_profit', 0):.2f}\n")
                f.write(f"- Lợi nhuận trung bình/giao dịch: ${analysis.get('avg_profit_per_trade', 0):.2f}\n")
                
                f.write("  Chi tiết theo loại tín hiệu:\n")
                for signal_type, signal_data in analysis.get('signal_details', {}).items():
                    f.write(f"  * {signal_type}: {signal_data.get('count', 0)} giao dịch, ")
                    f.write(f"Win rate: {signal_data.get('win_rate', 0):.2f}%, ")
                    f.write(f"Lợi nhuận: ${signal_data.get('profit', 0):.2f}\n")
            
            f.write("\nIV. PHÂN TÍCH THEO KHUNG THỜI GIAN\n")
            for timeframe, analysis in final_report.get('timeframe_analysis', {}).items():
                f.write(f"\n{timeframe}:\n")
                f.write(f"- Số giao dịch: {analysis.get('total_trades', 0)}\n")
                f.write(f"- Giao dịch thắng: {analysis.get('winning_trades', 0)}\n")
                f.write(f"- Tỷ lệ thắng: {analysis.get('win_rate', 0):.2f}%\n")
                f.write(f"- Tổng lợi nhuận: ${analysis.get('total_profit', 0):.2f}\n")
                f.write(f"- Lợi nhuận trung bình/giao dịch: ${analysis.get('avg_profit_per_trade', 0):.2f}\n")
            
            f.write("\nV. TOP 5 SYMBOL HIỆU SUẤT TỐT NHẤT\n")
            top_symbols = sorted(
                [s for s in final_report.get('symbol_analysis', {}).values()],
                key=lambda x: x.get('win_rate', 0),
                reverse=True
            )[:5]
            
            for idx, symbol_data in enumerate(top_symbols, 1):
                f.write(f"{idx}. {symbol_data.get('symbol')}: ")
                f.write(f"Win rate: {symbol_data.get('win_rate', 0):.2f}%, ")
                f.write(f"Trades: {symbol_data.get('total_trades', 0)}, ")
                f.write(f"Profit: ${symbol_data.get('total_profit', 0):.2f}\n")
            
            f.write("\nVI. CÁC LỖI GẶP PHẢI\n")
            for failed in failed_results:
                f.write(f"- {failed.get('symbol', 'Unknown')}: {failed.get('error', 'Unknown error')}\n")
            
            f.write("\nVII. KẾT LUẬN VÀ ĐỀ XUẤT\n")
            # Xác định chiến thuật hiệu quả nhất
            if final_report.get('strategy_analysis'):
                best_strategy = max(
                    final_report['strategy_analysis'].keys(),
                    key=lambda s: final_report['strategy_analysis'][s].get('win_rate', 0)
                )
                
                worst_strategy = min(
                    final_report['strategy_analysis'].keys(),
                    key=lambda s: final_report['strategy_analysis'][s].get('win_rate', 0)
                )
                
                best_timeframe = max(
                    final_report['timeframe_analysis'].keys(),
                    key=lambda tf: final_report['timeframe_analysis'][tf].get('win_rate', 0)
                )
                
                f.write(f"1. Chiến thuật hiệu quả nhất: {best_strategy} ")
                f.write(f"(Win rate: {final_report['strategy_analysis'][best_strategy].get('win_rate', 0):.2f}%)\n")
                
                f.write(f"2. Chiến thuật kém hiệu quả nhất: {worst_strategy} ")
                f.write(f"(Win rate: {final_report['strategy_analysis'][worst_strategy].get('win_rate', 0):.2f}%)\n")
                
                f.write(f"3. Khung thời gian hiệu quả nhất: {best_timeframe}\n")
                
                f.write("\nĐề xuất cải thiện:\n")
                f.write("1. Tinh chỉnh chiến thuật Sideways Market để giảm tín hiệu giả\n")
                f.write("2. Thêm bộ lọc xu hướng thị trường tổng thể cho các tín hiệu MA Crossover\n")
                f.write("3. Tối ưu hóa quản lý rủi ro với mức Stop Loss động dựa trên chế độ thị trường\n")
                f.write("4. Cải thiện chiến thuật RSI Divergence để tăng độ chính xác\n")
                f.write("5. Thêm cơ chế quản lý vốn tự động điều chỉnh kích thước vị thế dựa trên hiệu suất gần đây\n")
        
        # Tạo biểu đồ hiệu suất
        try:
            plt.figure(figsize=(15, 10))
            
            # Biểu đồ tỷ lệ thắng theo chiến thuật
            plt.subplot(2, 2, 1)
            strategies = list(final_report.get('strategy_analysis', {}).keys())
            win_rates = [final_report['strategy_analysis'][s].get('win_rate', 0) for s in strategies]
            
            plt.bar(strategies, win_rates, color='blue')
            plt.title('Tỷ lệ thắng theo chiến thuật')
            plt.ylabel('Tỷ lệ thắng (%)')
            plt.axhline(y=50, color='red', linestyle='--')
            plt.xticks(rotation=45)
            
            # Biểu đồ lợi nhuận theo chiến thuật
            plt.subplot(2, 2, 2)
            profits = [final_report['strategy_analysis'][s].get('total_profit', 0) for s in strategies]
            
            plt.bar(strategies, profits, color='green')
            plt.title('Lợi nhuận theo chiến thuật')
            plt.ylabel('Lợi nhuận ($)')
            plt.axhline(y=0, color='red', linestyle='--')
            plt.xticks(rotation=45)
            
            # Biểu đồ tỷ lệ thắng theo khung thời gian
            plt.subplot(2, 2, 3)
            timeframes = list(final_report.get('timeframe_analysis', {}).keys())
            tf_win_rates = [final_report['timeframe_analysis'][tf].get('win_rate', 0) for tf in timeframes]
            
            plt.bar(timeframes, tf_win_rates, color='purple')
            plt.title('Tỷ lệ thắng theo khung thời gian')
            plt.ylabel('Tỷ lệ thắng (%)')
            plt.axhline(y=50, color='red', linestyle='--')
            
            # Biểu đồ số lượng giao dịch theo symbol
            plt.subplot(2, 2, 4)
            symbols = list(final_report.get('symbol_analysis', {}).keys())[:10]  # Chỉ lấy 10 symbol đầu tiên
            symbol_trades = [final_report['symbol_analysis'][s].get('total_trades', 0) for s in symbols]
            
            plt.bar(symbols, symbol_trades, color='orange')
            plt.title('Số lượng giao dịch theo symbol (Top 10)')
            plt.ylabel('Số giao dịch')
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, 'performance_summary.png'))
            plt.close()
            
            # Biểu đồ hiệu suất chi tiết theo từng chiến thuật
            plt.figure(figsize=(15, 10))
            
            for i, strategy in enumerate(strategies, 1):
                plt.subplot(len(strategies), 1, i)
                
                signal_types = list(final_report['strategy_analysis'][strategy].get('signal_details', {}).keys())
                signal_win_rates = [
                    final_report['strategy_analysis'][strategy]['signal_details'][s].get('win_rate', 0) 
                    for s in signal_types
                ]
                
                plt.bar(signal_types, signal_win_rates, color='cyan')
                plt.title(f'Chi tiết tỷ lệ thắng của {strategy}')
                plt.ylabel('Win rate (%)')
                plt.axhline(y=50, color='red', linestyle='--')
                plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, 'strategy_details.png'))
            plt.close()
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ: {e}")
            logger.error(traceback.format_exc())
        
        logger.info("Đã hoàn thành backtest toàn diện hệ thống")
        logger.info(f"Báo cáo đã được lưu trong thư mục {result_dir}")
        
        return final_report
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy backtest toàn diện: {e}")
        logger.error(traceback.format_exc())
        return {'error': str(e)}

def check_environment():
    """Kiểm tra môi trường trước khi chạy backtest"""
    try:
        # Kiểm tra API keys
        api_key = os.environ.get('BINANCE_API_KEY')
        api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            logger.warning("Không tìm thấy Binance API keys. Hãy đảm bảo đã thiết lập BINANCE_API_KEY và BINANCE_API_SECRET.")
            return False
        
        # Kiểm tra thư viện cần thiết
        try:
            import pandas as pd
            import numpy as np
            import matplotlib.pyplot as plt
            from binance.client import Client
        except ImportError as e:
            logger.error(f"Thiếu thư viện cần thiết: {e}")
            return False
        
        # Kết nối thử với Binance API
        try:
            client = Client(api_key, api_secret)
            status = client.get_system_status()
            logger.info(f"Trạng thái hệ thống Binance: {status}")
            
            if status.get('status') != 0:
                logger.warning("Hệ thống Binance đang trong trạng thái bảo trì.")
                return False
            
            # Test lấy dữ liệu
            klines = client.get_historical_klines('BTCUSDT', '1d', "1 day ago UTC")
            if not klines:
                logger.warning("Không thể lấy dữ liệu từ Binance.")
                return False
            
            logger.info("Kết nối với Binance API thành công.")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi kết nối với Binance API: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra môi trường: {e}")
        return False

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Bắt đầu backtest toàn diện hệ thống lúc: {start_time}")
    
    # Kiểm tra môi trường
    if check_environment():
        # Chạy backtest toàn hệ thống
        run_full_backtest()
    else:
        logger.error("Kiểm tra môi trường thất bại. Vui lòng đảm bảo cài đặt đầy đủ thư viện và API keys.")
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Kết thúc backtest toàn diện hệ thống lúc: {end_time}")
    logger.info(f"Tổng thời gian thực hiện: {duration}")
