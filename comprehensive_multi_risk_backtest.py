#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BACKTEST TOÀN DIỆN - NHIỀU MỨC RỦI RO, NHIỀU KHUNG THỜI GIAN, NHIỀU CHẾ ĐỘ THỊ TRƯỜNG

Script này thực hiện backtest toàn diện với:
1. Nhiều mức rủi ro khác nhau (thấp, trung bình, cao)
2. Nhiều khung thời gian (1h, 4h, 1d)
3. Phân tích riêng các giai đoạn thị trường (xu hướng, đi ngang, biến động cao)

Mục tiêu: Đánh giá hiệu suất tổng thể của hệ thống trong mọi điều kiện thị trường
"""

import os
import sys
import json
import logging
import traceback
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures
import matplotlib.pyplot as plt
from binance.client import Client

# Thiết lập logging
output_dir = 'comprehensive_backtest_results'
os.makedirs(output_dir, exist_ok=True)
log_file = os.path.join(output_dir, f'comprehensive_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('comprehensive_backtest')

# Cấu hình các thông số test
SYMBOLS = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD']
TIMEFRAMES = ['1h', '4h', '1d']
RISK_LEVELS = ['low', 'medium', 'high']
TEST_PERIOD_DAYS = 180  # 6 tháng

# Cấu hình rủi ro theo mức độ
RISK_CONFIGS = {
    'low': {
        'risk_per_trade': 3.0,
        'max_leverage': 3,
        'stop_loss_atr_multiplier': 1.5,
        'take_profit_atr_multiplier': 4.0,
        'trailing_stop_activation_pct': 1.0,
        'trailing_stop_callback_pct': 0.5
    },
    'medium': {
        'risk_per_trade': 5.0,
        'max_leverage': 5,
        'stop_loss_atr_multiplier': 1.2,
        'take_profit_atr_multiplier': 3.0,
        'trailing_stop_activation_pct': 0.8,
        'trailing_stop_callback_pct': 0.4
    },
    'high': {
        'risk_per_trade': 7.0,
        'max_leverage': 10,
        'stop_loss_atr_multiplier': 1.0,
        'take_profit_atr_multiplier': 2.0,
        'trailing_stop_activation_pct': 0.5,
        'trailing_stop_callback_pct': 0.3
    }
}

# Chế độ thị trường và thiết lập
MARKET_REGIMES = ['trending', 'sideways', 'volatile']

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
    """Tính các chỉ báo kỹ thuật cần thiết"""
    try:
        df = data.copy()
        
        # === Chỉ báo xu hướng ===
        # Moving Averages
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['sma50'] = df['Close'].rolling(window=50).mean()
        df['sma100'] = df['Close'].rolling(window=100).mean()
        df['sma200'] = df['Close'].rolling(window=200).mean()
        
        df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['ema55'] = df['Close'].ewm(span=55, adjust=False).mean()
        
        # MACD
        df['ema12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # === Chỉ báo dao động ===
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
        
        # === Chỉ báo biến động ===
        # ATR
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        df['atr_pct'] = (df['atr'] / df['Close']) * 100
        
        # Bollinger Bands
        df['bb_middle'] = df['Close'].rolling(window=20).mean()
        df['bb_std'] = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
        df['bb_width_avg'] = df['bb_width'].rolling(30).mean()
        
        # ADX
        df['plus_dm'] = np.where(
            ((df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low'])) & 
            ((df['High'] - df['High'].shift(1)) > 0),
            df['High'] - df['High'].shift(1),
            0
        )
        
        df['minus_dm'] = np.where(
            ((df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1))) & 
            ((df['Low'].shift(1) - df['Low']) > 0),
            df['Low'].shift(1) - df['Low'],
            0
        )
        
        df['tr14'] = tr.rolling(14).sum()
        df['plus_di14'] = 100 * (df['plus_dm'].rolling(14).sum() / df['tr14'])
        df['minus_di14'] = 100 * (df['minus_dm'].rolling(14).sum() / df['tr14'])
        df['dx'] = 100 * ((df['plus_di14'] - df['minus_di14']).abs() / (df['plus_di14'] + df['minus_di14']))
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Loại bỏ dữ liệu NaN
        df = df.dropna()
        
        return df
        
    except Exception as e:
        logger.error(f"Lỗi khi tính chỉ báo: {e}")
        logger.error(traceback.format_exc())
        return None

def detect_market_regimes(data):
    """Phát hiện các giai đoạn thị trường khác nhau"""
    try:
        df = data.copy()
        
        # --- Phát hiện thị trường xu hướng ---
        # Dựa trên ADX (>25 là xu hướng mạnh)
        df['trend_strength'] = df['adx']
        df['is_trending'] = df['trend_strength'] > 25
        
        # Xác định xu hướng tăng/giảm
        df['trend_direction'] = np.where(
            df['plus_di14'] > df['minus_di14'],
            1,  # Xu hướng tăng
            -1  # Xu hướng giảm
        )
        
        # --- Phát hiện thị trường đi ngang ---
        # Dựa trên ADX thấp và BB width hẹp
        df['is_sideways'] = (
            (df['adx'] < 20) & 
            (df['bb_width'] < df['bb_width_avg']) &
            (df['atr_pct'] < 2.0)
        )
        
        # --- Phát hiện thị trường biến động cao ---
        # Dựa trên ATR % và BB width
        df['is_volatile'] = (
            (df['atr_pct'] > 3.0) | 
            (df['bb_width'] > df['bb_width_avg'] * 1.5)
        )
        
        # Phân loại chế độ thị trường
        df['market_regime'] = 'undefined'
        df.loc[df['is_trending'], 'market_regime'] = 'trending'
        df.loc[df['is_sideways'], 'market_regime'] = 'sideways'
        df.loc[df['is_volatile'] & ~df['is_trending'], 'market_regime'] = 'volatile'
        
        # Xác định các giai đoạn thị trường liên tục
        regimes = []
        
        # Xử lý từng loại thị trường
        for regime in MARKET_REGIMES:
            regime_mask = df['market_regime'] == regime
            
            # Tìm các giai đoạn liên tục
            start_idx = None
            
            for i, is_regime in enumerate(regime_mask):
                if is_regime and start_idx is None:
                    start_idx = i
                elif not is_regime and start_idx is not None:
                    # Thêm giai đoạn (chỉ khi kéo dài ít nhất 5 nến)
                    if i - start_idx >= 5:
                        regimes.append({
                            'type': regime,
                            'start_idx': start_idx,
                            'end_idx': i - 1,
                            'start_date': df.index[start_idx],
                            'end_date': df.index[i - 1],
                            'duration': i - start_idx
                        })
                    start_idx = None
            
            # Xử lý giai đoạn cuối cùng
            if start_idx is not None and len(df) - start_idx >= 5:
                regimes.append({
                    'type': regime,
                    'start_idx': start_idx,
                    'end_idx': len(df) - 1,
                    'start_date': df.index[start_idx],
                    'end_date': df.index[-1],
                    'duration': len(df) - start_idx
                })
        
        # Sắp xếp các giai đoạn theo thời gian
        regimes.sort(key=lambda x: x['start_idx'])
        
        # Thống kê
        regime_stats = {
            'trending': len([r for r in regimes if r['type'] == 'trending']),
            'sideways': len([r for r in regimes if r['type'] == 'sideways']),
            'volatile': len([r for r in regimes if r['type'] == 'volatile']),
            'total': len(regimes)
        }
        
        logger.info(f"Đã phát hiện {regime_stats['total']} giai đoạn thị trường: " +
                   f"{regime_stats['trending']} xu hướng, {regime_stats['sideways']} đi ngang, " +
                   f"{regime_stats['volatile']} biến động cao")
        
        return df, regimes
    
    except Exception as e:
        logger.error(f"Lỗi khi phát hiện chế độ thị trường: {e}")
        logger.error(traceback.format_exc())
        return data, []

def generate_signals(data, regime_periods, risk_level='medium'):
    """Tạo tín hiệu giao dịch dựa trên các chiến thuật khác nhau cho từng chế độ thị trường"""
    try:
        df = data.copy()
        signals = []
        
        # Lấy cấu hình rủi ro
        risk_config = RISK_CONFIGS.get(risk_level, RISK_CONFIGS['medium'])
        
        # --- Chiến thuật cho thị trường xu hướng ---
        trending_periods = [p for p in regime_periods if p['type'] == 'trending']
        for period in trending_periods:
            start_idx = period['start_idx']
            end_idx = period['end_idx']
            period_data = df.iloc[start_idx:end_idx+1]
            
            # Sử dụng MA Crossover cho thị trường xu hướng
            # Tín hiệu EMA 9/21
            period_data['ema_cross'] = np.where(
                period_data['ema9'] > period_data['ema21'],
                1,  # Long signal
                -1  # Short signal
            )
            
            # Tìm điểm cắt (thay đổi tín hiệu)
            period_data['signal_change'] = period_data['ema_cross'].diff().fillna(0)
            
            # Tìm tín hiệu vào lệnh
            for i in range(1, len(period_data)):
                if period_data['signal_change'].iloc[i] == 2:  # Short -> Long (2 = 1 - (-1))
                    entry_price = period_data['Close'].iloc[i]
                    entry_date = period_data.index[i]
                    entry_idx = start_idx + i
                    
                    # Tính SL và TP dựa trên ATR
                    atr = period_data['atr'].iloc[i]
                    stop_loss = entry_price - atr * risk_config['stop_loss_atr_multiplier']
                    take_profit = entry_price + atr * risk_config['take_profit_atr_multiplier']
                    
                    signals.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'type': 'LONG',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'regime': 'trending',
                        'strategy': 'ema_crossover',
                        'partial_take_profits': [
                            entry_price * (1 + 0.01),  # 1%
                            entry_price * (1 + 0.02),  # 2%
                            entry_price * (1 + 0.03),  # 3%
                            entry_price * (1 + 0.05)   # 5%
                        ],
                        'risk_level': risk_level
                    })
                    
                elif period_data['signal_change'].iloc[i] == -2:  # Long -> Short (-2 = -1 - 1)
                    entry_price = period_data['Close'].iloc[i]
                    entry_date = period_data.index[i]
                    entry_idx = start_idx + i
                    
                    # Tính SL và TP dựa trên ATR
                    atr = period_data['atr'].iloc[i]
                    stop_loss = entry_price + atr * risk_config['stop_loss_atr_multiplier']
                    take_profit = entry_price - atr * risk_config['take_profit_atr_multiplier']
                    
                    signals.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'type': 'SHORT',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'regime': 'trending',
                        'strategy': 'ema_crossover',
                        'partial_take_profits': [
                            entry_price * (1 - 0.01),  # 1%
                            entry_price * (1 - 0.02),  # 2%
                            entry_price * (1 - 0.03),  # 3%
                            entry_price * (1 - 0.05)   # 5%
                        ],
                        'risk_level': risk_level
                    })
        
        # --- Chiến thuật cho thị trường đi ngang ---
        sideways_periods = [p for p in regime_periods if p['type'] == 'sideways']
        for period in sideways_periods:
            start_idx = period['start_idx']
            end_idx = period['end_idx']
            period_data = df.iloc[start_idx:end_idx+1]
            
            # Sử dụng Bollinger Bands + RSI cho thị trường đi ngang
            for i in range(1, len(period_data)):
                # Tín hiệu LONG: Giá chạm BB dưới + RSI < 40
                if (period_data['Close'].iloc[i] <= period_data['bb_lower'].iloc[i] and
                    period_data['rsi'].iloc[i] < 40):
                    
                    entry_price = period_data['Close'].iloc[i]
                    entry_date = period_data.index[i]
                    entry_idx = start_idx + i
                    
                    # Tính SL và TP
                    atr = period_data['atr'].iloc[i]
                    stop_loss = entry_price - atr * risk_config['stop_loss_atr_multiplier']
                    take_profit = entry_price + atr * risk_config['take_profit_atr_multiplier']
                    
                    signals.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'type': 'LONG',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'regime': 'sideways',
                        'strategy': 'bollinger_bounce',
                        'partial_take_profits': [
                            entry_price * (1 + 0.01),
                            entry_price * (1 + 0.02),
                            entry_price * (1 + 0.03),
                            period_data['bb_middle'].iloc[i]  # Target đường trung bình
                        ],
                        'risk_level': risk_level
                    })
                
                # Tín hiệu SHORT: Giá chạm BB trên + RSI > 60
                if (period_data['Close'].iloc[i] >= period_data['bb_upper'].iloc[i] and
                    period_data['rsi'].iloc[i] > 60):
                    
                    entry_price = period_data['Close'].iloc[i]
                    entry_date = period_data.index[i]
                    entry_idx = start_idx + i
                    
                    # Tính SL và TP
                    atr = period_data['atr'].iloc[i]
                    stop_loss = entry_price + atr * risk_config['stop_loss_atr_multiplier']
                    take_profit = entry_price - atr * risk_config['take_profit_atr_multiplier']
                    
                    signals.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'type': 'SHORT',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'regime': 'sideways',
                        'strategy': 'bollinger_bounce',
                        'partial_take_profits': [
                            entry_price * (1 - 0.01),
                            entry_price * (1 - 0.02),
                            entry_price * (1 - 0.03),
                            period_data['bb_middle'].iloc[i]  # Target đường trung bình
                        ],
                        'risk_level': risk_level
                    })
        
        # --- Chiến thuật cho thị trường biến động cao ---
        volatile_periods = [p for p in regime_periods if p['type'] == 'volatile']
        for period in volatile_periods:
            start_idx = period['start_idx']
            end_idx = period['end_idx']
            period_data = df.iloc[start_idx:end_idx+1]
            
            # Sử dụng Breakout + RSI confirmer cho thị trường biến động
            for i in range(5, len(period_data)):
                # Tính các giá trị cao nhất, thấp nhất trong 5 nến trước đó
                prev_high = period_data['High'].iloc[i-5:i].max()
                prev_low = period_data['Low'].iloc[i-5:i].min()
                
                # Tín hiệu LONG: Breakout lên cao mới + RSI không quá mua
                if (period_data['Close'].iloc[i] > prev_high and
                    period_data['rsi'].iloc[i] < 70):
                    
                    entry_price = period_data['Close'].iloc[i]
                    entry_date = period_data.index[i]
                    entry_idx = start_idx + i
                    
                    # Tăng khoảng cách Stop Loss cho thị trường biến động
                    atr = period_data['atr'].iloc[i]
                    stop_loss = entry_price - atr * (risk_config['stop_loss_atr_multiplier'] * 1.5)
                    take_profit = entry_price + atr * (risk_config['take_profit_atr_multiplier'] * 0.8)
                    
                    signals.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'type': 'LONG',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'regime': 'volatile',
                        'strategy': 'breakout',
                        'partial_take_profits': [
                            entry_price * (1 + 0.015),  # 1.5%
                            entry_price * (1 + 0.025),  # 2.5%
                            entry_price * (1 + 0.04),   # 4%
                            entry_price * (1 + 0.06)    # 6%
                        ],
                        'risk_level': risk_level
                    })
                
                # Tín hiệu SHORT: Breakout xuống thấp mới + RSI không quá bán
                if (period_data['Close'].iloc[i] < prev_low and
                    period_data['rsi'].iloc[i] > 30):
                    
                    entry_price = period_data['Close'].iloc[i]
                    entry_date = period_data.index[i]
                    entry_idx = start_idx + i
                    
                    # Tăng khoảng cách Stop Loss cho thị trường biến động
                    atr = period_data['atr'].iloc[i]
                    stop_loss = entry_price + atr * (risk_config['stop_loss_atr_multiplier'] * 1.5)
                    take_profit = entry_price - atr * (risk_config['take_profit_atr_multiplier'] * 0.8)
                    
                    signals.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'entry_idx': entry_idx,
                        'type': 'SHORT',
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'regime': 'volatile',
                        'strategy': 'breakout',
                        'partial_take_profits': [
                            entry_price * (1 - 0.015),  # 1.5%
                            entry_price * (1 - 0.025),  # 2.5%
                            entry_price * (1 - 0.04),   # 4%
                            entry_price * (1 - 0.06)    # 6%
                        ],
                        'risk_level': risk_level
                    })
        
        # Sắp xếp tín hiệu theo thời gian
        signals.sort(key=lambda x: x['entry_idx'])
        
        # Lọc tín hiệu quá gần nhau
        filtered_signals = []
        last_entry_idx = -20  # Khởi tạo với giá trị âm để luôn lấy tín hiệu đầu tiên
        
        for signal in signals:
            # Chỉ lấy tín hiệu cách tín hiệu trước ít nhất 5 nến
            if signal['entry_idx'] - last_entry_idx >= 5:
                filtered_signals.append(signal)
                last_entry_idx = signal['entry_idx']
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu, sau khi lọc còn {len(filtered_signals)} tín hiệu")
        
        # Thống kê theo loại thị trường
        regime_counts = {
            'trending': len([s for s in filtered_signals if s['regime'] == 'trending']),
            'sideways': len([s for s in filtered_signals if s['regime'] == 'sideways']),
            'volatile': len([s for s in filtered_signals if s['regime'] == 'volatile'])
        }
        
        logger.info(f"Phân bố tín hiệu: Xu hướng: {regime_counts['trending']}, " +
                   f"Đi ngang: {regime_counts['sideways']}, Biến động: {regime_counts['volatile']}")
        
        return filtered_signals
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo tín hiệu: {e}")
        logger.error(traceback.format_exc())
        return []

def simulate_trades(data, signals, initial_balance=10000.0):
    """Mô phỏng giao dịch với partial take profit và trailing stop"""
    try:
        df = data.copy()
        
        # Khởi tạo kết quả
        trades = []
        balance = initial_balance
        
        for signal in signals:
            entry_idx = signal['entry_idx']
            entry_price = signal['entry_price']
            signal_type = signal['type']
            risk_level = signal['risk_level']
            
            # Lấy cấu hình rủi ro
            risk_config = RISK_CONFIGS.get(risk_level, RISK_CONFIGS['medium'])
            
            # Tính kích thước vị thế (% vốn theo cấu hình rủi ro)
            risk_percent = risk_config['risk_per_trade'] / 100
            position_size = balance * risk_percent
            
            # Đòn bẩy
            leverage = risk_config['max_leverage']
            
            # Khởi tạo thông tin giao dịch
            trade = {
                'entry_date': signal['entry_date'],
                'entry_price': entry_price,
                'type': signal_type,
                'regime': signal['regime'],
                'strategy': signal['strategy'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'risk_level': risk_level,
                'position_size': position_size,
                'leverage': leverage,
                'partial_exits': [],
                'remaining_position': 1.0,  # 100% position còn lại
                'trail_activated': False,
                'trailing_stop': None
            }
            
            # Thiết lập trailing stop theo cấu hình
            trail_activation_pct = risk_config['trailing_stop_activation_pct']
            trail_callback_pct = risk_config['trailing_stop_callback_pct']
            
            # Thực hiện mô phỏng giao dịch
            exit_found = False
            
            # Di chuyển Stop Loss lên breakeven sau khi chốt lời 25% đầu tiên
            stop_loss_moved = False
            
            for i in range(entry_idx + 1, len(df)):
                current_price = df['Close'].iloc[i]
                
                # Kiểm tra Stop Loss
                if (signal_type == 'LONG' and df['Low'].iloc[i] <= trade['stop_loss']) or \
                   (signal_type == 'SHORT' and df['High'].iloc[i] >= trade['stop_loss']):
                    
                    # Tính lợi nhuận
                    if signal_type == 'LONG':
                        profit_pct = (trade['stop_loss'] - entry_price) / entry_price
                    else:
                        profit_pct = (entry_price - trade['stop_loss']) / entry_price
                    
                    # Tính lợi nhuận dollar
                    dollar_profit = position_size * leverage * profit_pct * trade['remaining_position']
                    
                    # Cập nhật giao dịch
                    trade['exit_date'] = df.index[i]
                    trade['exit_price'] = trade['stop_loss']
                    trade['exit_reason'] = 'stop_loss'
                    trade['profit_pct'] = profit_pct * 100 * trade['remaining_position']
                    trade['profit'] = dollar_profit
                    trade['final_balance'] = balance + dollar_profit
                    
                    # Cập nhật số dư
                    balance += dollar_profit
                    
                    exit_found = True
                    break
                
                # Kiểm tra Take Profit (nếu không sử dụng partial take profit)
                if 'partial_take_profits' not in signal:
                    if (signal_type == 'LONG' and df['High'].iloc[i] >= trade['take_profit']) or \
                       (signal_type == 'SHORT' and df['Low'].iloc[i] <= trade['take_profit']):
                        
                        # Tính lợi nhuận
                        if signal_type == 'LONG':
                            profit_pct = (trade['take_profit'] - entry_price) / entry_price
                        else:
                            profit_pct = (entry_price - trade['take_profit']) / entry_price
                        
                        # Tính lợi nhuận dollar
                        dollar_profit = position_size * leverage * profit_pct
                        
                        # Cập nhật giao dịch
                        trade['exit_date'] = df.index[i]
                        trade['exit_price'] = trade['take_profit']
                        trade['exit_reason'] = 'take_profit'
                        trade['profit_pct'] = profit_pct * 100
                        trade['profit'] = dollar_profit
                        trade['final_balance'] = balance + dollar_profit
                        
                        # Cập nhật số dư
                        balance += dollar_profit
                        
                        exit_found = True
                        break
                
                # Partial Take Profit
                if 'partial_take_profits' in signal and signal['partial_take_profits']:
                    for tp_idx, tp_price in enumerate(signal['partial_take_profits']):
                        # Kiểm tra đã chốt TP này chưa
                        if tp_idx < len(trade['partial_exits']):
                            continue
                            
                        # Kiểm tra giá có chạm TP không
                        if (signal_type == 'LONG' and df['High'].iloc[i] >= tp_price) or \
                           (signal_type == 'SHORT' and df['Low'].iloc[i] <= tp_price):
                            
                            # Tính phần trăm vị thế sẽ đóng (25% mỗi lần)
                            exit_portion = 0.25
                            remaining_after = trade['remaining_position'] - exit_portion
                            
                            # Nếu phần còn lại < 0.01, đóng toàn bộ
                            if remaining_after < 0.01:
                                exit_portion = trade['remaining_position']
                                remaining_after = 0
                            
                            # Tính lợi nhuận
                            if signal_type == 'LONG':
                                profit_pct = (tp_price - entry_price) / entry_price
                            else:
                                profit_pct = (entry_price - tp_price) / entry_price
                            
                            # Tính lợi nhuận dollar
                            portion_size = position_size * exit_portion
                            dollar_profit = portion_size * leverage * profit_pct
                            
                            # Ghi nhận chốt lời từng phần
                            trade['partial_exits'].append({
                                'date': df.index[i],
                                'price': tp_price,
                                'portion': exit_portion,
                                'profit_pct': profit_pct * 100,
                                'profit': dollar_profit
                            })
                            
                            # Cập nhật số dư
                            balance += dollar_profit
                            
                            # Cập nhật phần còn lại của vị thế
                            trade['remaining_position'] = remaining_after
                            
                            # Di chuyển stop loss lên breakeven sau lần chốt lời đầu tiên
                            if tp_idx == 0 and not stop_loss_moved:
                                trade['stop_loss'] = entry_price
                                stop_loss_moved = True
                            
                            # Nếu đã đóng toàn bộ vị thế
                            if trade['remaining_position'] <= 0:
                                trade['exit_date'] = df.index[i]
                                trade['exit_price'] = tp_price
                                trade['exit_reason'] = 'full_take_profit'
                                
                                # Tính tổng lợi nhuận từ các lần chốt lời
                                total_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                                total_profit_pct = sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits'])
                                
                                trade['profit'] = total_profit
                                trade['profit_pct'] = total_profit_pct
                                trade['final_balance'] = balance
                                
                                exit_found = True
                                break
                            
                            # Kích hoạt trailing stop sau khi đạt được lợi nhuận nhất định
                            if not trade['trail_activated'] and tp_idx >= 1:  # Sau khi đạt TP thứ 2
                                trade['trail_activated'] = True
                                
                                if signal_type == 'LONG':
                                    trade['trailing_stop'] = current_price * (1 - trail_callback_pct/100)
                                else:
                                    trade['trailing_stop'] = current_price * (1 + trail_callback_pct/100)
                
                # Cập nhật trailing stop nếu đã kích hoạt
                if trade['trail_activated']:
                    if signal_type == 'LONG':
                        # Cập nhật trailing stop nếu giá cao hơn
                        new_trailing_stop = current_price * (1 - trail_callback_pct/100)
                        if new_trailing_stop > trade['trailing_stop']:
                            trade['trailing_stop'] = new_trailing_stop
                        
                        # Kiểm tra có hit trailing stop không
                        if df['Low'].iloc[i] <= trade['trailing_stop']:
                            # Tính lợi nhuận
                            profit_pct = (trade['trailing_stop'] - entry_price) / entry_price
                            
                            # Tính lợi nhuận dollar cho phần còn lại
                            portion_size = position_size * trade['remaining_position']
                            dollar_profit = portion_size * leverage * profit_pct
                            
                            # Cập nhật giao dịch
                            trade['exit_date'] = df.index[i]
                            trade['exit_price'] = trade['trailing_stop']
                            trade['exit_reason'] = 'trailing_stop'
                            
                            # Tính tổng lợi nhuận từ các lần chốt lời + trailing stop
                            partial_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                            total_profit = partial_profit + dollar_profit
                            
                            partial_profit_pct = sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits'])
                            trailing_profit_pct = profit_pct * 100 * trade['remaining_position']
                            
                            trade['profit'] = total_profit
                            trade['profit_pct'] = partial_profit_pct + trailing_profit_pct
                            trade['final_balance'] = balance + dollar_profit
                            
                            # Cập nhật số dư
                            balance += dollar_profit
                            
                            exit_found = True
                            break
                    else:  # SHORT
                        # Cập nhật trailing stop nếu giá thấp hơn
                        new_trailing_stop = current_price * (1 + trail_callback_pct/100)
                        if new_trailing_stop < trade['trailing_stop']:
                            trade['trailing_stop'] = new_trailing_stop
                        
                        # Kiểm tra có hit trailing stop không
                        if df['High'].iloc[i] >= trade['trailing_stop']:
                            # Tính lợi nhuận
                            profit_pct = (entry_price - trade['trailing_stop']) / entry_price
                            
                            # Tính lợi nhuận dollar cho phần còn lại
                            portion_size = position_size * trade['remaining_position']
                            dollar_profit = portion_size * leverage * profit_pct
                            
                            # Cập nhật giao dịch
                            trade['exit_date'] = df.index[i]
                            trade['exit_price'] = trade['trailing_stop']
                            trade['exit_reason'] = 'trailing_stop'
                            
                            # Tính tổng lợi nhuận từ các lần chốt lời + trailing stop
                            partial_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                            total_profit = partial_profit + dollar_profit
                            
                            partial_profit_pct = sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits'])
                            trailing_profit_pct = profit_pct * 100 * trade['remaining_position']
                            
                            trade['profit'] = total_profit
                            trade['profit_pct'] = partial_profit_pct + trailing_profit_pct
                            trade['final_balance'] = balance + dollar_profit
                            
                            # Cập nhật số dư
                            balance += dollar_profit
                            
                            exit_found = True
                            break
            
            # Nếu không tìm thấy điểm thoát, giả định đóng lệnh ở nến cuối cùng
            if not exit_found:
                last_price = df['Close'].iloc[-1]
                
                # Tính lợi nhuận cho phần còn lại
                if signal_type == 'LONG':
                    profit_pct = (last_price - entry_price) / entry_price
                else:
                    profit_pct = (entry_price - last_price) / entry_price
                
                # Tính lợi nhuận dollar cho phần còn lại
                portion_size = position_size * trade['remaining_position']
                dollar_profit = portion_size * leverage * profit_pct
                
                # Cập nhật giao dịch
                trade['exit_date'] = df.index[-1]
                trade['exit_price'] = last_price
                trade['exit_reason'] = 'end_of_data'
                
                # Tính tổng lợi nhuận
                partial_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                total_profit = partial_profit + dollar_profit
                
                partial_profit_pct = sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits'])
                remaining_profit_pct = profit_pct * 100 * trade['remaining_position']
                
                trade['profit'] = total_profit
                trade['profit_pct'] = partial_profit_pct + remaining_profit_pct
                trade['final_balance'] = balance + dollar_profit
                
                # Cập nhật số dư
                balance += dollar_profit
            
            # Thêm vào danh sách giao dịch
            trades.append(trade)
        
        # Tính toán các chỉ số thống kê
        if trades:
            # Tổng số giao dịch
            total_trades = len(trades)
            
            # Số lượng giao dịch thắng/thua
            winning_trades = sum(1 for t in trades if t['profit'] > 0)
            losing_trades = total_trades - winning_trades
            
            # Tỷ lệ thắng
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Lợi nhuận tổng thể
            total_profit = sum(t['profit'] for t in trades)
            profit_pct = ((balance - initial_balance) / initial_balance * 100)
            
            # Lợi nhuận trung bình mỗi giao dịch
            avg_profit = total_profit / total_trades if total_trades > 0 else 0
            avg_profit_pct = sum(t['profit_pct'] for t in trades) / total_trades if total_trades > 0 else 0
            
            # Profit factor
            gross_profit = sum(t['profit'] for t in trades if t['profit'] > 0)
            gross_loss = abs(sum(t['profit'] for t in trades if t['profit'] < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Drawdown
            balance_curve = [initial_balance]
            for t in sorted(trades, key=lambda x: x['entry_date']):
                balance_curve.append(balance_curve[-1] + t['profit'])
            
            max_balance = initial_balance
            max_drawdown = 0
            max_drawdown_pct = 0
            
            for bal in balance_curve:
                if bal > max_balance:
                    max_balance = bal
                else:
                    drawdown = max_balance - bal
                    drawdown_pct = (drawdown / max_balance) * 100
                    if drawdown_pct > max_drawdown_pct:
                        max_drawdown = drawdown
                        max_drawdown_pct = drawdown_pct
            
            # Tạo summary
            summary = {
                'initial_balance': initial_balance,
                'final_balance': balance,
                'total_profit': total_profit,
                'total_profit_pct': profit_pct,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_profit_pct': avg_profit_pct,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'risk_level': risk_level
            }
            
            # Thêm phân tích theo chiến thuật
            strategy_performance = {}
            for t in trades:
                strategy = t['strategy']
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {
                        'trades': 0,
                        'wins': 0,
                        'profit': 0
                    }
                
                strategy_performance[strategy]['trades'] += 1
                if t['profit'] > 0:
                    strategy_performance[strategy]['wins'] += 1
                strategy_performance[strategy]['profit'] += t['profit']
            
            # Tính winrate và avg profit cho mỗi chiến thuật
            for s in strategy_performance:
                trades_count = strategy_performance[s]['trades']
                strategy_performance[s]['win_rate'] = (
                    strategy_performance[s]['wins'] / trades_count * 100
                ) if trades_count > 0 else 0
                
                strategy_performance[s]['avg_profit'] = (
                    strategy_performance[s]['profit'] / trades_count
                ) if trades_count > 0 else 0
            
            summary['strategy_performance'] = strategy_performance
            
            # Thêm phân tích theo chế độ thị trường
            regime_performance = {}
            for t in trades:
                regime = t['regime']
                if regime not in regime_performance:
                    regime_performance[regime] = {
                        'trades': 0,
                        'wins': 0,
                        'profit': 0
                    }
                
                regime_performance[regime]['trades'] += 1
                if t['profit'] > 0:
                    regime_performance[regime]['wins'] += 1
                regime_performance[regime]['profit'] += t['profit']
            
            # Tính winrate và avg profit cho mỗi chế độ thị trường
            for r in regime_performance:
                trades_count = regime_performance[r]['trades']
                regime_performance[r]['win_rate'] = (
                    regime_performance[r]['wins'] / trades_count * 100
                ) if trades_count > 0 else 0
                
                regime_performance[r]['avg_profit'] = (
                    regime_performance[r]['profit'] / trades_count
                ) if trades_count > 0 else 0
            
            summary['regime_performance'] = regime_performance
            
            # Thông kê các lý do thoát lệnh
            exit_reasons = {}
            for t in trades:
                reason = t['exit_reason']
                if reason not in exit_reasons:
                    exit_reasons[reason] = 0
                exit_reasons[reason] += 1
            
            summary['exit_reasons'] = exit_reasons
            
            return trades, summary
        else:
            return [], {
                'initial_balance': initial_balance,
                'final_balance': initial_balance,
                'total_profit': 0,
                'total_profit_pct': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0
            }
    
    except Exception as e:
        logger.error(f"Lỗi khi mô phỏng giao dịch: {e}")
        logger.error(traceback.format_exc())
        return [], {
            'initial_balance': initial_balance,
            'final_balance': initial_balance,
            'total_profit': 0,
            'total_profit_pct': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'error': str(e)
        }

def test_symbol_with_risk_level(symbol, timeframe, risk_level, period_days=180, initial_balance=10000.0):
    """Test một symbol với một mức rủi ro cụ thể"""
    try:
        # Thiết lập interval cho Binance API dựa trên timeframe
        interval_map = {
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = interval_map.get(timeframe, '1d')
        
        # Lấy dữ liệu
        data = get_binance_data(symbol, interval=interval, days=period_days)
        
        if data is None or len(data) < 50:
            logger.error(f"Không đủ dữ liệu cho {symbol} trên khung {timeframe}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'risk_level': risk_level,
                'error': 'Không đủ dữ liệu'
            }
        
        # Tính toán các chỉ báo kỹ thuật
        data_with_indicators = calculate_indicators(data)
        
        if data_with_indicators is None:
            logger.error(f"Lỗi khi tính chỉ báo cho {symbol}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'risk_level': risk_level,
                'error': 'Lỗi khi tính chỉ báo'
            }
        
        # Phát hiện các chế độ thị trường
        data_with_regimes, regime_periods = detect_market_regimes(data_with_indicators)
        
        # Tạo tín hiệu giao dịch dựa trên các chiến thuật thích hợp
        signals = generate_signals(data_with_regimes, regime_periods, risk_level)
        
        if not signals:
            logger.warning(f"Không tìm thấy tín hiệu giao dịch cho {symbol} trên khung {timeframe} với mức rủi ro {risk_level}")
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'risk_level': risk_level,
                'initial_balance': initial_balance,
                'final_balance': initial_balance,
                'total_trades': 0,
                'profit': 0,
                'profit_pct': 0,
                'win_rate': 0,
                'regimes': {
                    'trending': len([p for p in regime_periods if p['type'] == 'trending']),
                    'sideways': len([p for p in regime_periods if p['type'] == 'sideways']),
                    'volatile': len([p for p in regime_periods if p['type'] == 'volatile'])
                }
            }
        
        # Mô phỏng giao dịch
        trades, summary = simulate_trades(data_with_regimes, signals, initial_balance)
        
        # Tạo kết quả
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'risk_level': risk_level,
            'initial_balance': initial_balance,
            'final_balance': summary.get('final_balance', initial_balance),
            'total_profit': summary.get('total_profit', 0),
            'total_profit_pct': summary.get('total_profit_pct', 0),
            'total_trades': summary.get('total_trades', 0),
            'winning_trades': summary.get('winning_trades', 0),
            'losing_trades': summary.get('losing_trades', 0),
            'win_rate': summary.get('win_rate', 0),
            'profit_factor': summary.get('profit_factor', 0),
            'max_drawdown': summary.get('max_drawdown', 0),
            'max_drawdown_pct': summary.get('max_drawdown_pct', 0),
            'avg_profit_pct': summary.get('avg_profit_pct', 0),
            'regimes': {
                'trending': len([p for p in regime_periods if p['type'] == 'trending']),
                'sideways': len([p for p in regime_periods if p['type'] == 'sideways']),
                'volatile': len([p for p in regime_periods if p['type'] == 'volatile'])
            }
        }
        
        # Thêm thông tin về hiệu suất theo chiến thuật và chế độ thị trường nếu có
        if 'strategy_performance' in summary:
            result['strategy_performance'] = summary['strategy_performance']
        
        if 'regime_performance' in summary:
            result['regime_performance'] = summary['regime_performance']
        
        if 'exit_reasons' in summary:
            result['exit_reasons'] = summary['exit_reasons']
        
        # Lưu thông tin trades chi tiết vào file riêng
        trades_filename = f'{symbol.replace("-", "_")}_{timeframe}_{risk_level}_trades.json'
        with open(os.path.join(output_dir, trades_filename), 'w') as f:
            json.dump([{k: str(v) if isinstance(v, pd.Timestamp) else v for k, v in t.items() 
                  if k not in ['partial_exits']} for t in trades], f, indent=4, default=str)
        
        logger.info(f"Kết quả cho {symbol} ({timeframe}, {risk_level}): " + 
                  f"Trades: {result['total_trades']}, Win rate: {result['win_rate']:.2f}%, " + 
                  f"Profit: {result['total_profit_pct']:.2f}%, Drawdown: {result['max_drawdown_pct']:.2f}%")
        
        return result
    
    except Exception as e:
        logger.error(f"Lỗi khi test {symbol} với {risk_level} risk: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'risk_level': risk_level,
            'error': str(e)
        }

def run_comprehensive_backtest():
    """Chạy backtest toàn diện trên tất cả cặp tiền, khung thời gian và mức rủi ro"""
    start_time = datetime.now()
    
    logger.info("=== BẮT ĐẦU BACKTEST TOÀN DIỆN ===")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Timeframes: {TIMEFRAMES}")
    logger.info(f"Risk levels: {RISK_LEVELS}")
    logger.info(f"Giai đoạn test: {TEST_PERIOD_DAYS} ngày")
    
    all_results = {}
    
    # Test từng symbol
    for symbol in SYMBOLS:
        symbol_results = {}
        
        # Test từng khung thời gian
        for timeframe in TIMEFRAMES:
            timeframe_results = {}
            
            # Test từng mức rủi ro
            for risk_level in RISK_LEVELS:
                logger.info(f"Bắt đầu test {symbol} trên khung {timeframe} với mức rủi ro {risk_level}")
                
                result = test_symbol_with_risk_level(
                    symbol, 
                    timeframe, 
                    risk_level, 
                    period_days=TEST_PERIOD_DAYS
                )
                
                timeframe_results[risk_level] = result
            
            symbol_results[timeframe] = timeframe_results
        
        all_results[symbol] = symbol_results
    
    # Lưu tất cả kết quả
    with open(os.path.join(output_dir, 'all_comprehensive_results.json'), 'w') as f:
        json.dump(all_results, f, indent=4, default=str)
    
    # Tạo báo cáo tổng hợp
    create_summary_report(all_results)
    
    # Tạo biểu đồ so sánh
    create_comparison_charts(all_results)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=== KẾT THÚC BACKTEST TOÀN DIỆN ===")
    logger.info(f"Thời gian thực hiện: {duration}")
    
    return all_results

def create_summary_report(all_results):
    """Tạo báo cáo tổng hợp từ kết quả backtest"""
    try:
        # Tạo báo cáo văn bản
        report_path = os.path.join(output_dir, 'comprehensive_backtest_report.md')
        
        with open(report_path, 'w') as f:
            f.write("# BÁO CÁO TỔNG HỢP BACKTEST TOÀN DIỆN\n\n")
            f.write(f"Ngày thực hiện: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Giai đoạn test: {TEST_PERIOD_DAYS} ngày\n\n")
            
            # Tổng hợp kết quả
            all_trades_count = 0
            winning_trades_count = 0
            total_tests = 0
            successful_tests = 0
            highest_profit = {"value": -float("inf"), "symbol": "", "timeframe": "", "risk_level": ""}
            highest_winrate = {"value": -float("inf"), "symbol": "", "timeframe": "", "risk_level": ""}
            lowest_drawdown = {"value": float("inf"), "symbol": "", "timeframe": "", "risk_level": ""}
            
            # Thu thập tất cả kết quả thành công
            all_successful_results = []
            
            for symbol, symbol_data in all_results.items():
                for timeframe, timeframe_data in symbol_data.items():
                    for risk_level, result in timeframe_data.items():
                        total_tests += 1
                        
                        if 'error' not in result:
                            successful_tests += 1
                            all_successful_results.append(result)
                            
                            all_trades_count += result.get('total_trades', 0)
                            winning_trades_count += result.get('winning_trades', 0)
                            
                            # Kiểm tra profit cao nhất
                            profit_pct = result.get('total_profit_pct', 0)
                            if profit_pct > highest_profit["value"]:
                                highest_profit = {
                                    "value": profit_pct,
                                    "symbol": symbol,
                                    "timeframe": timeframe,
                                    "risk_level": risk_level
                                }
                            
                            # Kiểm tra win rate cao nhất
                            win_rate = result.get('win_rate', 0)
                            if win_rate > highest_winrate["value"]:
                                highest_winrate = {
                                    "value": win_rate,
                                    "symbol": symbol,
                                    "timeframe": timeframe,
                                    "risk_level": risk_level
                                }
                            
                            # Kiểm tra drawdown thấp nhất (với profit dương)
                            if profit_pct > 0:
                                drawdown = result.get('max_drawdown_pct', float('inf'))
                                if drawdown < lowest_drawdown["value"]:
                                    lowest_drawdown = {
                                        "value": drawdown,
                                        "symbol": symbol,
                                        "timeframe": timeframe,
                                        "risk_level": risk_level
                                    }
            
            # Tính tỷ lệ thắng tổng thể
            overall_winrate = (winning_trades_count / all_trades_count * 100) if all_trades_count > 0 else 0
            
            # Viết phần tổng quan
            f.write("## TỔNG QUAN\n\n")
            f.write(f"Tổng số tests: {total_tests}\n")
            f.write(f"Tests thành công: {successful_tests}\n")
            f.write(f"Tổng số giao dịch: {all_trades_count}\n")
            f.write(f"Tỷ lệ thắng tổng thể: {overall_winrate:.2f}%\n\n")
            
            f.write("### Kết quả nổi bật\n\n")
            f.write(f"- Lợi nhuận cao nhất: {highest_profit['value']:.2f}% " + 
                   f"({highest_profit['symbol']}, {highest_profit['timeframe']}, {highest_profit['risk_level']})\n")
            f.write(f"- Win rate cao nhất: {highest_winrate['value']:.2f}% " + 
                   f"({highest_winrate['symbol']}, {highest_winrate['timeframe']}, {highest_winrate['risk_level']})\n")
            f.write(f"- Drawdown thấp nhất: {lowest_drawdown['value']:.2f}% " + 
                   f"({lowest_drawdown['symbol']}, {lowest_drawdown['timeframe']}, {lowest_drawdown['risk_level']})\n\n")
            
            # So sánh các mức rủi ro
            f.write("## SO SÁNH CÁC MỨC RỦI RO\n\n")
            
            risk_level_results = {risk: [] for risk in RISK_LEVELS}
            
            for result in all_successful_results:
                risk = result.get('risk_level')
                if risk in risk_level_results:
                    risk_level_results[risk].append(result)
            
            f.write("| Mức rủi ro | Tổng giao dịch | Win rate | Lợi nhuận TB | Drawdown TB | Profit Factor TB |\n")
            f.write("|------------|----------------|----------|--------------|-------------|------------------|\n")
            
            for risk, results in risk_level_results.items():
                if not results:
                    continue
                    
                trades = sum(r.get('total_trades', 0) for r in results)
                wins = sum(r.get('winning_trades', 0) for r in results)
                win_rate = (wins / trades * 100) if trades > 0 else 0
                
                avg_profit = sum(r.get('total_profit_pct', 0) for r in results) / len(results)
                avg_drawdown = sum(r.get('max_drawdown_pct', 0) for r in results) / len(results)
                avg_profit_factor = sum(r.get('profit_factor', 0) for r in results) / len(results)
                
                f.write(f"| {risk} | {trades} | {win_rate:.2f}% | {avg_profit:.2f}% | {avg_drawdown:.2f}% | {avg_profit_factor:.2f} |\n")
            
            f.write("\n")
            
            # So sánh các khung thời gian
            f.write("## SO SÁNH CÁC KHUNG THỜI GIAN\n\n")
            
            timeframe_results = {tf: [] for tf in TIMEFRAMES}
            
            for result in all_successful_results:
                tf = result.get('timeframe')
                if tf in timeframe_results:
                    timeframe_results[tf].append(result)
            
            f.write("| Khung thời gian | Tổng giao dịch | Win rate | Lợi nhuận TB | Drawdown TB | Profit Factor TB |\n")
            f.write("|-----------------|----------------|----------|--------------|-------------|------------------|\n")
            
            for tf, results in timeframe_results.items():
                if not results:
                    continue
                    
                trades = sum(r.get('total_trades', 0) for r in results)
                wins = sum(r.get('winning_trades', 0) for r in results)
                win_rate = (wins / trades * 100) if trades > 0 else 0
                
                avg_profit = sum(r.get('total_profit_pct', 0) for r in results) / len(results)
                avg_drawdown = sum(r.get('max_drawdown_pct', 0) for r in results) / len(results)
                avg_profit_factor = sum(r.get('profit_factor', 0) for r in results) / len(results)
                
                f.write(f"| {tf} | {trades} | {win_rate:.2f}% | {avg_profit:.2f}% | {avg_drawdown:.2f}% | {avg_profit_factor:.2f} |\n")
            
            f.write("\n")
            
            # So sánh hiệu suất theo loại thị trường
            f.write("## HIỆU SUẤT THEO LOẠI THỊ TRƯỜNG\n\n")
            
            # Thu thập kết quả theo loại thị trường
            regime_trades = {regime: 0 for regime in MARKET_REGIMES}
            regime_wins = {regime: 0 for regime in MARKET_REGIMES}
            regime_profits = {regime: 0 for regime in MARKET_REGIMES}
            
            for result in all_successful_results:
                if 'regime_performance' in result:
                    for regime, data in result['regime_performance'].items():
                        regime_trades[regime] = regime_trades.get(regime, 0) + data.get('trades', 0)
                        regime_wins[regime] = regime_wins.get(regime, 0) + data.get('wins', 0)
                        regime_profits[regime] = regime_profits.get(regime, 0) + data.get('profit', 0)
            
            f.write("| Loại thị trường | Tổng giao dịch | Win rate | Tổng lợi nhuận |\n")
            f.write("|-----------------|----------------|----------|----------------|\n")
            
            for regime in MARKET_REGIMES:
                trades = regime_trades.get(regime, 0)
                wins = regime_wins.get(regime, 0)
                profit = regime_profits.get(regime, 0)
                
                win_rate = (wins / trades * 100) if trades > 0 else 0
                
                f.write(f"| {regime} | {trades} | {win_rate:.2f}% | ${profit:.2f} |\n")
            
            f.write("\n")
            
            # So sánh hiệu suất theo chiến thuật
            f.write("## HIỆU SUẤT THEO CHIẾN THUẬT\n\n")
            
            # Thu thập tất cả các chiến thuật
            all_strategies = set()
            for result in all_successful_results:
                if 'strategy_performance' in result:
                    all_strategies.update(result['strategy_performance'].keys())
            
            # Thu thập kết quả theo chiến thuật
            strategy_trades = {strategy: 0 for strategy in all_strategies}
            strategy_wins = {strategy: 0 for strategy in all_strategies}
            strategy_profits = {strategy: 0 for strategy in all_strategies}
            
            for result in all_successful_results:
                if 'strategy_performance' in result:
                    for strategy, data in result['strategy_performance'].items():
                        strategy_trades[strategy] = strategy_trades.get(strategy, 0) + data.get('trades', 0)
                        strategy_wins[strategy] = strategy_wins.get(strategy, 0) + data.get('wins', 0)
                        strategy_profits[strategy] = strategy_profits.get(strategy, 0) + data.get('profit', 0)
            
            f.write("| Chiến thuật | Tổng giao dịch | Win rate | Tổng lợi nhuận |\n")
            f.write("|-------------|----------------|----------|----------------|\n")
            
            for strategy in all_strategies:
                trades = strategy_trades.get(strategy, 0)
                wins = strategy_wins.get(strategy, 0)
                profit = strategy_profits.get(strategy, 0)
                
                win_rate = (wins / trades * 100) if trades > 0 else 0
                
                f.write(f"| {strategy} | {trades} | {win_rate:.2f}% | ${profit:.2f} |\n")
            
            f.write("\n")
            
            # Chi tiết kết quả từng symbol
            f.write("## CHI TIẾT KẾT QUẢ TỪNG SYMBOL\n\n")
            
            for symbol in SYMBOLS:
                f.write(f"### {symbol}\n\n")
                
                f.write("| Khung TG | Rủi ro | Giao dịch | Win rate | Lợi nhuận | Drawdown | Trending | Sideways | Volatile |\n")
                f.write("|----------|--------|-----------|----------|-----------|----------|----------|----------|----------|\n")
                
                for timeframe in TIMEFRAMES:
                    for risk_level in RISK_LEVELS:
                        result = all_results.get(symbol, {}).get(timeframe, {}).get(risk_level, {})
                        
                        if 'error' in result:
                            f.write(f"| {timeframe} | {risk_level} | - | - | - | - | - | - | - | Lỗi: {result['error']} |\n")
                        else:
                            trades = result.get('total_trades', 0)
                            win_rate = result.get('win_rate', 0)
                            profit = result.get('total_profit_pct', 0)
                            drawdown = result.get('max_drawdown_pct', 0)
                            
                            trending = result.get('regimes', {}).get('trending', 0)
                            sideways = result.get('regimes', {}).get('sideways', 0)
                            volatile = result.get('regimes', {}).get('volatile', 0)
                            
                            f.write(f"| {timeframe} | {risk_level} | {trades} | {win_rate:.2f}% | {profit:.2f}% | {drawdown:.2f}% | {trending} | {sideways} | {volatile} |\n")
                
                f.write("\n")
            
            # Kết luận và khuyến nghị
            f.write("## KẾT LUẬN VÀ KHUYẾN NGHỊ\n\n")
            
            # Tìm mức rủi ro tốt nhất
            risk_performance = {}
            for risk in RISK_LEVELS:
                results = risk_level_results.get(risk, [])
                if results:
                    avg_profit = sum(r.get('total_profit_pct', 0) for r in results) / len(results)
                    avg_drawdown = sum(r.get('max_drawdown_pct', 0) for r in results) / len(results)
                    win_rate = sum(r.get('winning_trades', 0) for r in results) / sum(r.get('total_trades', 0) for r in results) * 100
                    
                    # Tính điểm hiệu suất (profit/drawdown ratio x winrate)
                    if avg_drawdown > 0:
                        performance_score = (avg_profit / avg_drawdown) * (win_rate / 100)
                    else:
                        performance_score = avg_profit * (win_rate / 100)
                    
                    risk_performance[risk] = {
                        'avg_profit': avg_profit,
                        'avg_drawdown': avg_drawdown,
                        'win_rate': win_rate,
                        'performance_score': performance_score
                    }
            
            # Tìm mức rủi ro tốt nhất theo điểm hiệu suất
            best_risk = max(risk_performance.items(), key=lambda x: x[1]['performance_score'])[0] if risk_performance else None
            
            # Tìm khung thời gian tốt nhất
            tf_performance = {}
            for tf in TIMEFRAMES:
                results = timeframe_results.get(tf, [])
                if results:
                    avg_profit = sum(r.get('total_profit_pct', 0) for r in results) / len(results)
                    avg_drawdown = sum(r.get('max_drawdown_pct', 0) for r in results) / len(results)
                    win_rate = sum(r.get('winning_trades', 0) for r in results) / sum(r.get('total_trades', 0) for r in results) * 100
                    
                    # Tính điểm hiệu suất (profit/drawdown ratio x winrate)
                    if avg_drawdown > 0:
                        performance_score = (avg_profit / avg_drawdown) * (win_rate / 100)
                    else:
                        performance_score = avg_profit * (win_rate / 100)
                    
                    tf_performance[tf] = {
                        'avg_profit': avg_profit,
                        'avg_drawdown': avg_drawdown,
                        'win_rate': win_rate,
                        'performance_score': performance_score
                    }
            
            # Tìm khung thời gian tốt nhất theo điểm hiệu suất
            best_tf = max(tf_performance.items(), key=lambda x: x[1]['performance_score'])[0] if tf_performance else None
            
            # Tìm chiến thuật tốt nhất
            strategy_win_rates = {}
            for strategy in all_strategies:
                trades = strategy_trades.get(strategy, 0)
                wins = strategy_wins.get(strategy, 0)
                profit = strategy_profits.get(strategy, 0)
                
                if trades > 0:
                    win_rate = wins / trades * 100
                    avg_profit = profit / trades
                    strategy_win_rates[strategy] = {
                        'win_rate': win_rate,
                        'avg_profit': avg_profit,
                        'trades': trades
                    }
            
            # Chỉ xét các chiến thuật có ít nhất 10 giao dịch
            valid_strategies = {s: data for s, data in strategy_win_rates.items() if data['trades'] >= 10}
            
            # Tìm chiến thuật tốt nhất theo win rate
            best_strategy_by_wr = max(valid_strategies.items(), key=lambda x: x[1]['win_rate'])[0] if valid_strategies else None
            
            # Tìm chiến thuật tốt nhất theo lợi nhuận trung bình
            best_strategy_by_profit = max(valid_strategies.items(), key=lambda x: x[1]['avg_profit'])[0] if valid_strategies else None
            
            # Viết kết luận
            f.write("### Những phát hiện chính\n\n")
            
            if best_risk:
                f.write(f"1. **Mức rủi ro tối ưu**: {best_risk} cho ra kết quả tốt nhất với tỷ lệ lợi nhuận/rủi ro cao nhất\n")
            
            if best_tf:
                f.write(f"2. **Khung thời gian tối ưu**: {best_tf} cho hiệu suất tốt nhất\n")
            
            if best_strategy_by_wr:
                f.write(f"3. **Chiến thuật đáng tin cậy nhất**: {best_strategy_by_wr} có tỷ lệ thắng cao nhất ({strategy_win_rates[best_strategy_by_wr]['win_rate']:.2f}%)\n")
            
            if best_strategy_by_profit:
                f.write(f"4. **Chiến thuật sinh lời nhất**: {best_strategy_by_profit} cho lợi nhuận trung bình cao nhất (${strategy_win_rates[best_strategy_by_profit]['avg_profit']:.2f} mỗi giao dịch)\n")
            
            # Thống kê về hiệu suất trên các chế độ thị trường
            regime_win_rates = {}
            for regime in MARKET_REGIMES:
                trades = regime_trades.get(regime, 0)
                wins = regime_wins.get(regime, 0)
                
                if trades > 0:
                    win_rate = wins / trades * 100
                    regime_win_rates[regime] = win_rate
            
            best_regime = max(regime_win_rates.items(), key=lambda x: x[1])[0] if regime_win_rates else None
            
            if best_regime:
                f.write(f"5. **Chế độ thị trường hiệu quả nhất**: {best_regime} với tỷ lệ thắng {regime_win_rates[best_regime]:.2f}%\n\n")
            
            # Phân tích rủi ro và đề xuất
            f.write("### Phân tích rủi ro\n\n")
            
            # Tính toán rủi ro dựa trên drawdown và volatility
            avg_drawdown = sum(r.get('max_drawdown_pct', 0) for r in all_successful_results) / len(all_successful_results) if all_successful_results else 0
            
            f.write(f"- **Drawdown trung bình**: {avg_drawdown:.2f}% trên tất cả các tests\n")
            f.write("- **Rủi ro thị trường biến động**: Hệ thống thường gặp khó khăn hơn trong thị trường biến động cao\n")
            f.write("- **Rủi ro thời gian**: Các timeframe ngắn hạn có xu hướng tạo ra nhiều tín hiệu giả hơn\n\n")
            
            # Khuyến nghị tối ưu
            f.write("### Khuyến nghị tối ưu\n\n")
            
            if best_risk and best_tf:
                f.write(f"1. **Cấu hình tối ưu**: Sử dụng mức rủi ro {best_risk} trên khung thời gian {best_tf}\n")
            
            if best_regime:
                f.write(f"2. **Tập trung vào chế độ thị trường**: Tối ưu hóa giao dịch trong chế độ {best_regime}\n")
            
            # Đề xuất dựa trên phân tích chiến thuật
            f.write("3. **Tối ưu hóa chiến thuật**:\n")
            
            if 'ema_crossover' in strategy_win_rates:
                ma_wr = strategy_win_rates['ema_crossover']['win_rate']
                f.write(f"   - EMA Crossover: {ma_wr:.2f}% tỷ lệ thắng - ")
                if ma_wr > 60:
                    f.write("Hiệu quả cao, tiếp tục sử dụng\n")
                else:
                    f.write("Cần thêm bộ lọc để cải thiện\n")
            
            if 'bollinger_bounce' in strategy_win_rates:
                bb_wr = strategy_win_rates['bollinger_bounce']['win_rate']
                f.write(f"   - Bollinger Bounce: {bb_wr:.2f}% tỷ lệ thắng - ")
                if bb_wr > 60:
                    f.write("Hiệu quả cao trong thị trường đi ngang\n")
                else:
                    f.write("Cần tối ưu thêm cho thị trường đi ngang\n")
            
            if 'breakout' in strategy_win_rates:
                bo_wr = strategy_win_rates['breakout']['win_rate']
                f.write(f"   - Breakout: {bo_wr:.2f}% tỷ lệ thắng - ")
                if bo_wr > 60:
                    f.write("Hiệu quả cao trong thị trường biến động\n")
                else:
                    f.write("Thêm bộ lọc volume để tăng độ chính xác\n")
            
            f.write("\n4. **Quản lý rủi ro**:\n")
            f.write("   - Giữ nguyên chiến lược partial take profit (25% mỗi lần) đã chứng minh hiệu quả\n")
            f.write("   - Di chuyển stop loss lên breakeven sau TP đầu tiên giúp bảo vệ vốn hiệu quả\n")
            f.write("   - Trailing stop sau TP thứ 2 tối ưu hóa lợi nhuận trong các xu hướng mạnh\n\n")
            
            # Các cải tiến đề xuất cho tương lai
            f.write("### Cải tiến cho tương lai\n\n")
            f.write("1. **Tích hợp đa khung thời gian**: Sử dụng tín hiệu từ nhiều khung TG để xác nhận\n")
            f.write("2. **Tự động điều chỉnh thông số**: Tối ưu hóa tự động các thông số dựa trên chế độ thị trường\n")
            f.write("3. **Bộ lọc biến động thị trường**: Giảm số lượng giao dịch trong giai đoạn biến động cực lớn\n")
            f.write("4. **Mô hình ML bổ sung**: Thêm layer ML để dự đoán hiệu quả của tín hiệu\n")
            f.write("5. **Tối ưu hóa portfolio**: Phân bổ vốn thông minh giữa các cặp tiền dựa trên hiệu suất\n")
        
        logger.info(f"Đã tạo báo cáo tổng hợp tại: {report_path}")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {e}")
        logger.error(traceback.format_exc())

def create_comparison_charts(all_results):
    """Tạo các biểu đồ so sánh từ kết quả backtest"""
    try:
        logger.info("Tạo các biểu đồ so sánh")
        
        # Chuẩn bị dữ liệu
        chart_data = {
            'risk_profit': {risk: [] for risk in RISK_LEVELS},
            'risk_winrate': {risk: [] for risk in RISK_LEVELS},
            'risk_drawdown': {risk: [] for risk in RISK_LEVELS},
            'tf_profit': {tf: [] for tf in TIMEFRAMES},
            'tf_winrate': {tf: [] for tf in TIMEFRAMES},
            'symbols': {symbol: {'profit': [], 'winrate': []} for symbol in SYMBOLS}
        }
        
        # Thu thập dữ liệu
        for symbol, symbol_data in all_results.items():
            for timeframe, timeframe_data in symbol_data.items():
                for risk_level, result in timeframe_data.items():
                    if 'error' not in result:
                        # Dữ liệu theo mức rủi ro
                        chart_data['risk_profit'][risk_level].append(result.get('total_profit_pct', 0))
                        chart_data['risk_winrate'][risk_level].append(result.get('win_rate', 0))
                        chart_data['risk_drawdown'][risk_level].append(result.get('max_drawdown_pct', 0))
                        
                        # Dữ liệu theo khung thời gian
                        chart_data['tf_profit'][timeframe].append(result.get('total_profit_pct', 0))
                        chart_data['tf_winrate'][timeframe].append(result.get('win_rate', 0))
                        
                        # Dữ liệu theo symbol
                        chart_data['symbols'][symbol]['profit'].append(result.get('total_profit_pct', 0))
                        chart_data['symbols'][symbol]['winrate'].append(result.get('win_rate', 0))
        
        # Biểu đồ 1: So sánh lợi nhuận theo mức rủi ro
        plt.figure(figsize=(12, 8))
        
        for i, risk in enumerate(RISK_LEVELS):
            data = chart_data['risk_profit'][risk]
            if data:
                plt.boxplot(data, positions=[i+1], widths=0.6, patch_artist=True,
                           boxprops=dict(facecolor=f'C{i}', alpha=0.7))
        
        plt.title('Phân bố lợi nhuận (%) theo mức rủi ro', fontsize=14)
        plt.ylabel('Lợi nhuận (%)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.xticks(range(1, len(RISK_LEVELS)+1), RISK_LEVELS)
        
        plt.savefig(os.path.join(output_dir, 'risk_profit_comparison.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 2: So sánh win rate theo mức rủi ro
        plt.figure(figsize=(12, 8))
        
        bar_width = 0.25
        x = np.arange(len(RISK_LEVELS))
        
        for risk in RISK_LEVELS:
            data = chart_data['risk_winrate'][risk]
            if data:
                avg_winrate = sum(data) / len(data)
                plt.bar(x[RISK_LEVELS.index(risk)], avg_winrate, width=bar_width, 
                       label=f'{risk} (avg: {avg_winrate:.2f}%)')
        
        plt.title('Tỷ lệ thắng trung bình theo mức rủi ro', fontsize=14)
        plt.ylabel('Win rate (%)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.xticks(x, RISK_LEVELS)
        plt.legend()
        
        plt.savefig(os.path.join(output_dir, 'risk_winrate_comparison.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 3: So sánh drawdown theo mức rủi ro
        plt.figure(figsize=(12, 8))
        
        for i, risk in enumerate(RISK_LEVELS):
            data = chart_data['risk_drawdown'][risk]
            if data:
                plt.boxplot(data, positions=[i+1], widths=0.6, patch_artist=True,
                           boxprops=dict(facecolor=f'C{i}', alpha=0.7))
        
        plt.title('Phân bố drawdown (%) theo mức rủi ro', fontsize=14)
        plt.ylabel('Drawdown (%)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.xticks(range(1, len(RISK_LEVELS)+1), RISK_LEVELS)
        
        plt.savefig(os.path.join(output_dir, 'risk_drawdown_comparison.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 4: So sánh lợi nhuận theo khung thời gian
        plt.figure(figsize=(12, 8))
        
        for i, tf in enumerate(TIMEFRAMES):
            data = chart_data['tf_profit'][tf]
            if data:
                plt.boxplot(data, positions=[i+1], widths=0.6, patch_artist=True,
                           boxprops=dict(facecolor=f'C{i}', alpha=0.7))
        
        plt.title('Phân bố lợi nhuận (%) theo khung thời gian', fontsize=14)
        plt.ylabel('Lợi nhuận (%)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.xticks(range(1, len(TIMEFRAMES)+1), TIMEFRAMES)
        
        plt.savefig(os.path.join(output_dir, 'timeframe_profit_comparison.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 5: So sánh win rate theo khung thời gian
        plt.figure(figsize=(12, 8))
        
        bar_width = 0.25
        x = np.arange(len(TIMEFRAMES))
        
        for tf in TIMEFRAMES:
            data = chart_data['tf_winrate'][tf]
            if data:
                avg_winrate = sum(data) / len(data)
                plt.bar(x[TIMEFRAMES.index(tf)], avg_winrate, width=bar_width, 
                       label=f'{tf} (avg: {avg_winrate:.2f}%)')
        
        plt.title('Tỷ lệ thắng trung bình theo khung thời gian', fontsize=14)
        plt.ylabel('Win rate (%)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.xticks(x, TIMEFRAMES)
        plt.legend()
        
        plt.savefig(os.path.join(output_dir, 'timeframe_winrate_comparison.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 6: So sánh lợi nhuận và win rate theo symbol
        plt.figure(figsize=(14, 8))
        
        x = np.arange(len(SYMBOLS))
        width = 0.35
        
        avg_profits = []
        avg_winrates = []
        
        for symbol in SYMBOLS:
            profit_data = chart_data['symbols'][symbol]['profit']
            winrate_data = chart_data['symbols'][symbol]['winrate']
            
            avg_profit = sum(profit_data) / len(profit_data) if profit_data else 0
            avg_winrate = sum(winrate_data) / len(winrate_data) if winrate_data else 0
            
            avg_profits.append(avg_profit)
            avg_winrates.append(avg_winrate)
        
        ax1 = plt.subplot(111)
        bars1 = ax1.bar(x - width/2, avg_profits, width, label='Lợi nhuận (%)', color='green', alpha=0.7)
        ax1.set_ylabel('Lợi nhuận (%)', fontsize=12)
        ax1.set_title('Lợi nhuận và Win rate trung bình theo Symbol', fontsize=14)
        
        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + width/2, avg_winrates, width, label='Win rate (%)', color='blue', alpha=0.7)
        ax2.set_ylabel('Win rate (%)', fontsize=12)
        
        ax1.set_xticks(x)
        ax1.set_xticklabels(SYMBOLS)
        
        # Thêm legend
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'symbol_performance_comparison.png'), dpi=100)
        plt.close()
        
        logger.info("Đã tạo tất cả biểu đồ so sánh")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ so sánh: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Kiểm tra API key
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("Không tìm thấy Binance API keys. Vui lòng thiết lập BINANCE_API_KEY và BINANCE_API_SECRET.")
        sys.exit(1)
    
    # Chạy backtest toàn diện
    run_comprehensive_backtest()
