#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest chiến lược thích ứng kết hợp MA crossover và tối ưu hóa thị trường đi ngang
"""

import argparse
import json
import logging
from datetime import datetime
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from sideways_market_detector import SidewaysMarketDetector

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_backtest')

def load_risk_config():
    """Tải cấu hình rủi ro từ file"""
    try:
        with open('account_risk_config.json', 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Lỗi tải cấu hình: {e}")
        return {
            "risk_levels": {
                "low": {
                    "risk_per_trade": 3.0,
                    "max_leverage": 3,
                    "max_open_positions": 5
                }
            },
            "atr_settings": {
                "atr_period": 14,
                "atr_multiplier": {"low": 1.5},
                "take_profit_atr_multiplier": {"low": 4.0}
            }
        }

def calculate_indicators(data):
    """Tính toán các chỉ báo"""
    # Tính các đường MA với nhiều chu kỳ khác nhau
    ma_periods = [10, 20, 50, 100, 200]
    for period in ma_periods:
        data[f'ma{period}'] = data['Close'].rolling(window=period).mean()
    
    # Tính EMA
    ema_periods = [9, 21, 55]
    for period in ema_periods:
        data[f'ema{period}'] = data['Close'].ewm(span=period, adjust=False).mean()
    
    # Tính RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # RSI với nhiều chu kỳ khác nhau
    for period in [7, 14, 21]:
        gain_p = delta.where(delta > 0, 0)
        loss_p = -delta.where(delta < 0, 0)
        avg_gain_p = gain_p.rolling(window=period).mean()
        avg_loss_p = loss_p.rolling(window=period).mean()
        rs_p = avg_gain_p / avg_loss_p
        data[f'rsi_{period}'] = 100 - (100 / (1 + rs_p))
    
    # Tính ATR (Average True Range)
    high_low = data['High'] - data['Low']
    high_close = abs(data['High'] - data['Close'].shift())
    low_close = abs(data['Low'] - data['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    
    # ATR với nhiều chu kỳ
    for period in [7, 14, 21]:
        data[f'atr_{period}'] = true_range.rolling(period).mean()
    
    # Đảm bảo tương thích với code cũ
    data['atr'] = data['atr_14'] if 'atr_14' in data.columns else true_range.rolling(14).mean()
    
    # Bollinger Bands
    for period in [20, 50]:
        data[f'sma{period}'] = data['Close'].rolling(period).mean()
        data[f'stddev_{period}'] = data['Close'].rolling(period).std()
        data[f'bb_upper_{period}'] = data[f'sma{period}'] + (data[f'stddev_{period}'] * 2)
        data[f'bb_lower_{period}'] = data[f'sma{period}'] - (data[f'stddev_{period}'] * 2)
        # Bollinger Band Width (độ rộng của dải)
        data[f'bb_width_{period}'] = (data[f'bb_upper_{period}'] - data[f'bb_lower_{period}']) / data[f'sma{period}']
    
    # Đảm bảo tương thích với code cũ
    data['sma20'] = data['sma20'] if 'sma20' in data.columns else data['Close'].rolling(20).mean()
    data['stddev'] = data['stddev_20'] if 'stddev_20' in data.columns else data['Close'].rolling(20).std()
    data['bollinger_upper'] = data['bb_upper_20'] if 'bb_upper_20' in data.columns else data['sma20'] + (data['stddev'] * 2)
    data['bollinger_lower'] = data['bb_lower_20'] if 'bb_lower_20' in data.columns else data['sma20'] - (data['stddev'] * 2)
    
    # MACD
    data['ema12'] = data['Close'].ewm(span=12, adjust=False).mean()
    data['ema26'] = data['Close'].ewm(span=26, adjust=False).mean()
    data['macd'] = data['ema12'] - data['ema26']
    data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
    data['macd_hist'] = data['macd'] - data['macd_signal']
    
    # Stochastic Oscillator
    period = 14
    data['lowest_low'] = data['Low'].rolling(window=period).min()
    data['highest_high'] = data['High'].rolling(window=period).max()
    data['stoch_k'] = 100 * ((data['Close'] - data['lowest_low']) / 
                            (data['highest_high'] - data['lowest_low']))
    data['stoch_d'] = data['stoch_k'].rolling(window=3).mean()
    
    # Volume Indicators
    if 'Volume' in data.columns:
        # On-Balance Volume (OBV)
        data['obv'] = np.where(data['Close'] > data['Close'].shift(1), 
                              data['Volume'], 
                              np.where(data['Close'] < data['Close'].shift(1), 
                                     -data['Volume'], 0)).cumsum()
        
        # Volume Moving Average
        data['volume_ma20'] = data['Volume'].rolling(window=20).mean()
        data['volume_ratio'] = data['Volume'] / data['volume_ma20']
    
    return data

def ma_crossover_signals(data):
    """Tạo tín hiệu MA crossover với nhiều chiến lược khác nhau"""
    signals = []
    
    # Danh sách các cặp MA để tạo tín hiệu crossover
    ma_pairs = [
        ('ma10', 'ma20'), 
        ('ma20', 'ma50'),
        ('ma50', 'ma100'),
        ('ema9', 'ema21'),
        ('ema21', 'ema55')
    ]
    
    # Kiểm tra từng cặp MA
    for fast_ma, slow_ma in ma_pairs:
        if fast_ma not in data.columns or slow_ma not in data.columns:
            continue
            
        ma_min_periods = int(max(fast_ma.replace('ma', '').replace('ema', ''), 
                                slow_ma.replace('ma', '').replace('ema', '')))
        
        for i in range(ma_min_periods, len(data)-1):
            # Kiểm tra điều kiện MA crossover
            current_fast = float(data[fast_ma].iloc[i])
            current_slow = float(data[slow_ma].iloc[i])
            prev_fast = float(data[fast_ma].iloc[i-1])
            prev_slow = float(data[slow_ma].iloc[i-1])
            
            current_close = float(data['Close'].iloc[i])
            current_rsi = float(data['rsi'].iloc[i]) if 'rsi' in data.columns else 50
            
            # LONG signal: fast MA crosses above slow MA
            if prev_fast <= prev_slow and current_fast > current_slow:
                # Thêm bộ lọc tín hiệu giả bằng RSI và khối lượng
                valid_signal = True
                
                # Lọc theo RSI: Không vào lệnh khi RSI quá cao (>70)
                if 'rsi' in data.columns and current_rsi > 70:
                    valid_signal = False
                
                # Lọc theo volume: Không vào lệnh khi volume thấp
                if 'Volume' in data.columns and 'volume_ratio' in data.columns:
                    current_vol_ratio = float(data['volume_ratio'].iloc[i])
                    if current_vol_ratio < 0.8:  # Volume thấp hơn 80% trung bình
                        valid_signal = False
                
                # Kiểm tra xu hướng: Không vào lệnh khi đã trong xu hướng giảm mạnh
                if 'ma100' in data.columns and current_close < float(data['ma100'].iloc[i]):
                    # Nếu giá dưới MA100, kiểm tra thêm điều kiện
                    if current_close < float(data['ma50'].iloc[i]) * 0.95:
                        valid_signal = False
                
                if valid_signal:
                    entry_date = data.index[i]
                    entry_price = current_close
                    
                    signals.append({
                        'date': entry_date,
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'signal_source': f'{fast_ma}_{slow_ma}_crossover',
                        'sideways_period': False,
                        'ma_pair': f'{fast_ma}_{slow_ma}'
                    })
            
            # SHORT signal: fast MA crosses below slow MA
            elif prev_fast >= prev_slow and current_fast < current_slow:
                # Thêm bộ lọc tín hiệu giả bằng RSI và khối lượng
                valid_signal = True
                
                # Lọc theo RSI: Không vào lệnh khi RSI quá thấp (<30)
                if 'rsi' in data.columns and current_rsi < 30:
                    valid_signal = False
                
                # Lọc theo volume: Không vào lệnh khi volume thấp
                if 'Volume' in data.columns and 'volume_ratio' in data.columns:
                    current_vol_ratio = float(data['volume_ratio'].iloc[i])
                    if current_vol_ratio < 0.8:
                        valid_signal = False
                
                # Kiểm tra xu hướng: Không vào lệnh khi đã trong xu hướng tăng mạnh
                if 'ma100' in data.columns and current_close > float(data['ma100'].iloc[i]):
                    # Nếu giá trên MA100, kiểm tra thêm điều kiện
                    if current_close > float(data['ma50'].iloc[i]) * 1.05:
                        valid_signal = False
                
                if valid_signal:
                    entry_date = data.index[i]
                    entry_price = current_close
                    
                    signals.append({
                        'date': entry_date,
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'signal_source': f'{fast_ma}_{slow_ma}_crossover',
                        'sideways_period': False,
                        'ma_pair': f'{fast_ma}_{slow_ma}'
                    })
    
    # Bộ lọc tín hiệu giao dịch tập trung
    # Loại bỏ các tín hiệu quá gần nhau trong cùng một ngày
    filtered_signals = []
    if signals:
        # Sắp xếp tín hiệu theo thời gian
        sorted_signals = sorted(signals, key=lambda x: x['date'])
        
        # Nhóm tín hiệu theo ngày
        date_groups = {}
        for signal in sorted_signals:
            date_str = signal['date'].strftime('%Y-%m-%d')
            if date_str not in date_groups:
                date_groups[date_str] = []
            date_groups[date_str].append(signal)
        
        # Lấy tín hiệu tốt nhất cho mỗi ngày
        for date_str, day_signals in date_groups.items():
            if len(day_signals) == 1:
                filtered_signals.append(day_signals[0])
            else:
                # Ưu tiên EMA over SMA và chu kỳ ngắn
                priority_signals = [s for s in day_signals if 'ema' in s['ma_pair']]
                if priority_signals:
                    filtered_signals.append(priority_signals[0])
                else:
                    filtered_signals.append(day_signals[0])
    
    logger.info(f"Đã tạo {len(signals)} tín hiệu MA crossover, sau khi lọc còn {len(filtered_signals)}")
    return filtered_signals

def apply_atr_based_stops(data, signals, risk_config, risk_level="low"):
    """Áp dụng stop loss và take profit dựa trên ATR"""
    atr_settings = risk_config["atr_settings"]
    atr_multiplier = atr_settings["atr_multiplier"][risk_level]
    tp_multiplier = atr_settings["take_profit_atr_multiplier"][risk_level]
    
    for signal in signals:
        signal_idx = data.index.get_loc(signal['date'])
        
        if signal_idx < len(data)-1:
            current_atr = data['atr'].iloc[signal_idx]
            entry_price = signal['entry_price']
            
            if not np.isnan(current_atr):
                if signal['type'] == 'LONG':
                    stop_loss = entry_price - (current_atr * atr_multiplier)
                    take_profit = entry_price + (current_atr * tp_multiplier)
                else:  # SHORT
                    stop_loss = entry_price + (current_atr * atr_multiplier)
                    take_profit = entry_price - (current_atr * tp_multiplier)
                
                signal['stop_loss'] = stop_loss
                signal['take_profit'] = take_profit
            else:
                # Fallback nếu không có dữ liệu ATR
                if signal['type'] == 'LONG':
                    signal['stop_loss'] = entry_price * 0.95  # 5% stop loss
                    signal['take_profit'] = entry_price * 1.15  # 15% take profit
                else:  # SHORT
                    signal['stop_loss'] = entry_price * 1.05  # 5% stop loss
                    signal['take_profit'] = entry_price * 0.85  # 15% take profit
    
    return signals

def calculate_position_size(signal, balance, risk_params):
    """Tính toán kích thước vị thế dựa trên quản lý rủi ro"""
    entry_price = signal['entry_price']
    stop_loss = signal['stop_loss']
    
    # Rủi ro theo % tài khoản
    risk_amount = balance * (risk_params['risk_per_trade'] / 100)
    
    # Khoảng cách entry đến stop loss
    if signal['type'] == 'LONG':
        risk_per_unit = entry_price - stop_loss
    else:  # SHORT
        risk_per_unit = stop_loss - entry_price
    
    # Tránh chia cho zero
    if abs(risk_per_unit) < 0.0001:
        position_size = 0
    else:
        position_size = risk_amount / abs(risk_per_unit)
    
    # Áp dụng đòn bẩy
    leverage = risk_params['max_leverage']
    
    # Điều chỉnh position size theo thị trường đi ngang
    if signal['sideways_period']:
        # Giảm kích thước vị thế 30% trong thị trường đi ngang
        position_size = position_size * 0.7
    
    return position_size, leverage

def simulate_trades(data, signals, risk_params, initial_balance=10000.0, symbol=None):
    """
    Mô phỏng các giao dịch từ tín hiệu
    
    Args:
        data (pd.DataFrame): Dữ liệu giá
        signals (List[Dict]): Danh sách tín hiệu giao dịch
        risk_params (Dict): Tham số quản lý rủi ro
        initial_balance (float): Số dư ban đầu
        symbol (str): Mã cặp tiền giao dịch
    """
    trades = []
    balance = initial_balance
    
    for signal in signals:
        # Tìm vị trí của tín hiệu trong dữ liệu
        signal_idx = data.index.get_loc(signal['date'])
        
        if signal_idx >= len(data) - 2:
            # Bỏ qua tín hiệu quá gần cuối chuỗi dữ liệu
            continue
        
        # Tính kích thước vị thế
        position_size, leverage = calculate_position_size(signal, balance, risk_params)
        
        # Thông tin giao dịch
        trade = {
            'symbol': symbol,  # Sử dụng symbol được truyền vào
            'entry_date': signal['date'],
            'entry_price': signal['entry_price'],
            'type': signal['type'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'position_size': position_size,
            'leverage': leverage,
            'signal_source': signal['signal_source'],
            'sideways_period': signal['sideways_period']
        }
        
        # Mô phỏng giao dịch
        exit_date = None
        exit_price = None
        exit_reason = None
        
        for j in range(signal_idx + 1, len(data)):
            curr_price = float(data['Close'].iloc[j])
            
            if trade['type'] == 'LONG':
                # Kiểm tra stop loss
                if curr_price <= trade['stop_loss']:
                    exit_date = data.index[j]
                    exit_price = trade['stop_loss']
                    exit_reason = "stop_loss"
                    break
                    
                # Kiểm tra take profit  
                if curr_price >= trade['take_profit']:
                    exit_date = data.index[j]
                    exit_price = trade['take_profit']
                    exit_reason = "take_profit"
                    break
            else:  # SHORT
                # Kiểm tra stop loss
                if curr_price >= trade['stop_loss']:
                    exit_date = data.index[j]
                    exit_price = trade['stop_loss']
                    exit_reason = "stop_loss"
                    break
                    
                # Kiểm tra take profit  
                if curr_price <= trade['take_profit']:
                    exit_date = data.index[j]
                    exit_price = trade['take_profit']
                    exit_reason = "take_profit"
                    break
        
        # Nếu không chạm SL/TP thì tính đến điểm kết thúc backtest
        if exit_date is None:
            exit_date = data.index[-1]
            exit_price = float(data['Close'].iloc[-1])
            exit_reason = "end_of_test"
        
        # Tính lợi nhuận
        if trade['type'] == 'LONG':
            profit = (exit_price - trade['entry_price']) * trade['position_size'] * trade['leverage']
            profit_pct = ((exit_price / trade['entry_price']) - 1) * 100 * trade['leverage']
        else:  # SHORT
            profit = (trade['entry_price'] - exit_price) * trade['position_size'] * trade['leverage']
            profit_pct = ((trade['entry_price'] / exit_price) - 1) * 100 * trade['leverage']
        
        # Cập nhật số dư
        balance += profit
        
        # Cập nhật thông tin giao dịch
        trade.update({
            'exit_date': exit_date,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'profit': profit,
            'profit_pct': profit_pct,
            'balance_after': balance
        })
        
        trades.append(trade)
        
        # Log thông tin giao dịch
        logger.info(f"[{trade['symbol']}] Tín hiệu {trade['type']} ({trade['signal_source']}) tại {trade['entry_date']}, giá ${trade['entry_price']:.2f}")
        logger.info(f"  Stop Loss: ${trade['stop_loss']:.2f}, Take Profit: ${trade['take_profit']:.2f}")
        logger.info(f"  Kích thước vị thế: {trade['position_size']:.4f}, Đòn bẩy: {trade['leverage']}x")
        logger.info(f"  Kết quả: {trade['exit_reason']} tại {trade['exit_date']}, giá ${trade['exit_price']:.2f}")
        logger.info(f"  Lợi nhuận: ${trade['profit']:.2f} ({trade['profit_pct']:.2f}%)")
        logger.info(f"  Số dư mới: ${balance:.2f}")
        
    return trades, balance

def run_adaptive_backtest(symbols, period="3mo", timeframe="1d", initial_balance=10000.0, use_binance_data=False):
    """
    Chạy backtest với chiến lược thích ứng kết hợp và tối ưu hóa
    
    Args:
        symbols (list): Danh sách mã giao dịch
        period (str): Khoảng thời gian backtest
        timeframe (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        use_binance_data (bool): Sử dụng dữ liệu từ Binance thay vì Yahoo Finance
    """
    # Tải cấu hình rủi ro
    risk_config = load_risk_config()
    risk_level = "low"
    risk_params = risk_config["risk_levels"][risk_level]
    
    logger.info(f"=== BẮT ĐẦU BACKTEST CHIẾN LƯỢC THÍCH ỨNG ===")
    logger.info(f"Số lượng symbols: {len(symbols)}")
    logger.info(f"Khung thời gian: {timeframe}")
    logger.info(f"Khoảng thời gian: {period}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Mức rủi ro: {risk_level}")
    logger.info(f"Rủi ro/Giao dịch: {risk_params['risk_per_trade']}%")
    logger.info(f"Đòn bẩy: {risk_params['max_leverage']}x")
    logger.info(f"Nguồn dữ liệu: {'Binance' if use_binance_data else 'Yahoo Finance'}")
    
    # Tạo bộ phát hiện thị trường đi ngang
    sideways_detector = SidewaysMarketDetector()
    
    # Thông tin kết quả
    balance = initial_balance
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    all_trades = []
    symbol_results = {}
    
    # Chạy backtest cho từng symbol
    for symbol in symbols:
        logger.info(f"\nBắt đầu backtest {symbol}")
        
        try:
            # Tải dữ liệu
            if use_binance_data:
                try:
                    # Tải dữ liệu từ Binance
                    from binance.client import Client
                    import os
                    
                    # Lấy API key và secret
                    api_key = os.environ.get('BINANCE_API_KEY', '')
                    api_secret = os.environ.get('BINANCE_API_SECRET', '')
                    
                    # Nếu dùng testnet thì dùng key testnet
                    use_testnet = False  # Dùng dữ liệu thực
                    if use_testnet:
                        api_key = os.environ.get('BINANCE_TESTNET_API_KEY', api_key)
                        api_secret = os.environ.get('BINANCE_TESTNET_API_SECRET', api_secret)
                    
                    # Chuyển đổi period sang timestamp
                    from datetime import datetime, timedelta
                    end_date = datetime.now()
                    
                    # Chuyển đổi period từ định dạng Yahoo Finance sang số ngày
                    if period.endswith('d'):
                        days = int(period[:-1])
                    elif period.endswith('mo'):
                        days = int(period[:-2]) * 30
                    elif period.endswith('y'):
                        days = int(period[:-1]) * 365
                    else:
                        days = 90  # Mặc định 90 ngày
                    
                    start_date = end_date - timedelta(days=days)
                    
                    # Chuyển đổi timeframe sang định dạng Binance
                    interval_mapping = {
                        '1m': Client.KLINE_INTERVAL_1MINUTE,
                        '5m': Client.KLINE_INTERVAL_5MINUTE,
                        '15m': Client.KLINE_INTERVAL_15MINUTE,
                        '30m': Client.KLINE_INTERVAL_30MINUTE,
                        '1h': Client.KLINE_INTERVAL_1HOUR,
                        '2h': Client.KLINE_INTERVAL_2HOUR,
                        '4h': Client.KLINE_INTERVAL_4HOUR,
                        '1d': Client.KLINE_INTERVAL_1DAY,
                    }
                    binance_interval = interval_mapping.get(timeframe, Client.KLINE_INTERVAL_1DAY)
                    
                    # Chuyển đổi symbol (Binance dùng BTCUSDT thay vì BTC-USD)
                    binance_symbol = symbol
                    if '-USD' in symbol:
                        binance_symbol = symbol.replace('-USD', 'USDT')
                    elif 'USD' not in symbol and 'USDT' not in symbol:
                        binance_symbol = f"{symbol}USDT"
                    
                    logger.info(f"Tải dữ liệu {binance_symbol} từ Binance ({binance_interval}, {days} ngày)")
                    
                    # Tạo Binance client
                    client = Client(api_key, api_secret, testnet=use_testnet)
                    
                    # Lấy dữ liệu
                    klines = client.get_historical_klines(
                        symbol=binance_symbol,
                        interval=binance_interval,
                        start_str=start_date.strftime('%Y-%m-%d'),
                        end_str=end_date.strftime('%Y-%m-%d')
                    )
                    
                    # Chuyển đổi sang DataFrame
                    data = pd.DataFrame(klines, columns=[
                        'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
                        'taker_buy_quote', 'ignored'
                    ])
                    
                    # Chuyển đổi kiểu dữ liệu
                    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
                    data.set_index('timestamp', inplace=True)
                    
                    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                        data[col] = pd.to_numeric(data[col])
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu từ Binance: {e}")
                    logger.info(f"Chuyển sang sử dụng dữ liệu từ Yahoo Finance cho {symbol}")
                    
                    # Fallback: dùng Yahoo Finance
                    data = yf.download(symbol, period=period, interval=timeframe)
            else:
                # Sử dụng Yahoo Finance
                data = yf.download(symbol, period=period, interval=timeframe)
                
            logger.info(f"Đã tải {len(data)} dòng dữ liệu cho {symbol}")
            
            if len(data) < 20:
                logger.warning(f"Không đủ dữ liệu cho {symbol}, bỏ qua")
                continue
            
            # Tính các chỉ báo
            data = calculate_indicators(data)
            
            # Phát hiện thị trường đi ngang
            processed_data, sideways_periods = sideways_detector.detect_sideways_market(data)
            logger.info(f"Đã phát hiện {len(sideways_periods)} giai đoạn thị trường đi ngang")
            
            # Cập nhật data với dữ liệu đã xử lý
            data = processed_data
            
            # Tạo tín hiệu từ MA crossover
            ma_signals = ma_crossover_signals(data)
            logger.info(f"Đã tạo {len(ma_signals)} tín hiệu MA crossover")
            
            # Tạo tín hiệu từ thị trường đi ngang
            sideways_signals = []
            if len(sideways_periods) > 0:
                sideways_signals = sideways_detector.generate_sideways_signals(data, sideways_periods)
                logger.info(f"Đã tạo {len(sideways_signals)} tín hiệu thị trường đi ngang")
            
            # Kết hợp tất cả tín hiệu và sắp xếp theo thời gian
            all_signals = ma_signals + sideways_signals
            all_signals.sort(key=lambda x: x['date'])
            
            # Áp dụng stop loss và take profit dựa trên ATR
            all_signals = apply_atr_based_stops(data, all_signals, risk_config, risk_level)
            
            # Triển khai chốt lời từng phần (partial take profit)
            for signal in all_signals:
                # Thêm các mức chốt lời từng phần
                entry_price = signal['entry_price']
                signal['partial_take_profits'] = []
                
                if signal['type'] == 'LONG':
                    # Mức chốt lời tăng dần: 1%, 2%, 3%, 5%
                    for pct in [0.01, 0.02, 0.03, 0.05]:
                        tp_level = entry_price * (1 + pct)
                        signal['partial_take_profits'].append({
                            'level': tp_level,
                            'percentage': 25.0,  # Chốt 25% vị thế ở mỗi mức
                            'triggered': False
                        })
                else:  # SHORT
                    # Mức chốt lời giảm dần: 1%, 2%, 3%, 5%
                    for pct in [0.01, 0.02, 0.03, 0.05]:
                        tp_level = entry_price * (1 - pct)
                        signal['partial_take_profits'].append({
                            'level': tp_level,
                            'percentage': 25.0,  # Chốt 25% vị thế ở mỗi mức
                            'triggered': False
                        })
            
            # Mô phỏng giao dịch
            symbol_trades, symbol_balance = simulate_trades(data, all_signals, risk_params, balance, symbol)
            
            # Cập nhật số dư
            balance = symbol_balance
            
            # Cập nhật thông tin giao dịch
            all_trades.extend(symbol_trades)
            
            # Cập nhật thống kê
            symbol_win_trades = sum(1 for t in symbol_trades if t['profit'] > 0)
            symbol_lose_trades = len(symbol_trades) - symbol_win_trades
            
            total_trades += len(symbol_trades)
            winning_trades += symbol_win_trades
            losing_trades += symbol_lose_trades
            
            # Lưu kết quả cho symbol
            symbol_profit = sum(t['profit'] for t in symbol_trades)
            symbol_win_rate = symbol_win_trades / len(symbol_trades) * 100 if len(symbol_trades) > 0 else 0
            
            symbol_results[symbol] = {
                "trades": len(symbol_trades),
                "winning_trades": symbol_win_trades,
                "losing_trades": symbol_lose_trades,
                "profit": symbol_profit,
                "win_rate": symbol_win_rate,
                "ma_signals": len(ma_signals),
                "sideways_signals": len(sideways_signals)
            }
            
            logger.info(f"Kết quả {symbol}: {len(symbol_trades)} giao dịch, Lợi nhuận: ${symbol_profit:.2f}, Tỷ lệ thắng: {symbol_win_rate:.2f}%")
            
        except Exception as e:
            logger.error(f"Lỗi khi backtest {symbol}: {e}")
    
    # Tổng kết backtest
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    profit = balance - initial_balance
    profit_pct = (balance / initial_balance - 1) * 100
    
    logger.info(f"\n=== KẾT QUẢ BACKTEST THÍCH ỨNG ===")
    logger.info(f"Số lượng giao dịch: {total_trades}")
    logger.info(f"Giao dịch thắng/thua: {winning_trades}/{losing_trades}")
    logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
    logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
    logger.info(f"Số dư cuối cùng: ${balance:.2f}")
    logger.info(f"Tổng lợi nhuận: ${profit:.2f} ({profit_pct:.2f}%)")
    
    # Chi tiết từng symbol
    logger.info(f"\n=== CHI TIẾT TỪNG SYMBOL ===")
    for symbol, result in symbol_results.items():
        logger.info(f"{symbol}: {result['trades']} giao dịch, Lợi nhuận: ${result['profit']:.2f}, Tỷ lệ thắng: {result['win_rate']:.2f}%")
    
    # Tạo báo cáo
    report = {
        "initial_balance": initial_balance,
        "final_balance": balance,
        "total_profit": profit,
        "total_profit_pct": profit_pct,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "symbol_results": symbol_results,
        "all_trades": all_trades
    }
    
    return report

def save_report(report, output_dir="backtest_reports"):
    """Lưu báo cáo backtest"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = os.path.join(output_dir, f'adaptive_backtest_report_{timestamp}.txt')
    json_file = os.path.join(output_dir, f'adaptive_backtest_data_{timestamp}.json')
    
    # Lưu dữ liệu JSON
    with open(json_file, 'w') as f:
        # Chuyển đổi các đối tượng datetime sang string
        json_data = report.copy()
        
        # Xử lý Timestamp cho tất cả các trades
        for trade in json_data['all_trades']:
            trade['entry_date'] = str(trade['entry_date'])
            trade['exit_date'] = str(trade['exit_date'])
        
        # Xử lý Timestamp cho kết quả từng symbol
        for symbol, data in json_data['symbol_results'].items():
            # Kiểm tra và chuyển đổi các field có thể chứa timestamp
            if 'sideways_periods' in data:
                for period in data['sideways_periods']:
                    if 'start_date' in period:
                        period['start_date'] = str(period['start_date'])
                    if 'end_date' in period:
                        period['end_date'] = str(period['end_date'])
        
        # Tạo một custom JSON encoder để xử lý các loại dữ liệu đặc biệt
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, (datetime, pd.Timestamp)):
                    return str(o)
                elif isinstance(o, pd.Series):
                    return o.to_dict()
                elif isinstance(o, pd.DataFrame):
                    return o.to_dict(orient='records')
                elif isinstance(o, np.integer):
                    return int(o)
                elif isinstance(o, np.floating):
                    return float(o)
                elif isinstance(o, np.ndarray):
                    return o.tolist()
                else:
                    return super().default(o)
        
        # Sử dụng custom encoder
        json.dump(json_data, f, indent=4, cls=DateTimeEncoder)
    
    # Tạo báo cáo văn bản
    with open(report_file, 'w') as f:
        f.write("=== BÁO CÁO KẾT QUẢ BACKTEST CHIẾN LƯỢC THÍCH ỨNG ===\n\n")
        f.write(f"Ngày tạo báo cáo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("THỐNG KÊ TỔNG QUAN\n")
        f.write(f"Số dư ban đầu: ${report['initial_balance']:.2f}\n")
        f.write(f"Số dư cuối cùng: ${report['final_balance']:.2f}\n")
        f.write(f"Lợi nhuận: ${report['total_profit']:.2f} ({report['total_profit_pct']:.2f}%)\n")
        f.write(f"Tổng số giao dịch: {report['total_trades']}\n")
        f.write(f"Số giao dịch thắng: {report['winning_trades']}\n")
        f.write(f"Số giao dịch thua: {report['losing_trades']}\n")
        f.write(f"Tỷ lệ thắng: {report['win_rate']:.2f}%\n\n")
        
        f.write("CHI TIẾT TỪNG SYMBOL\n")
        for symbol, result in report['symbol_results'].items():
            f.write(f"Symbol: {symbol}\n")
            f.write(f"  Số giao dịch: {result['trades']}\n")
            f.write(f"  Giao dịch thắng/thua: {result['winning_trades']}/{result['losing_trades']}\n")
            f.write(f"  Lợi nhuận: ${result['profit']:.2f}\n")
            f.write(f"  Tỷ lệ thắng: {result['win_rate']:.2f}%\n")
            if 'ma_signals' in result and 'sideways_signals' in result:
                f.write(f"  Tín hiệu MA/Sideways: {result['ma_signals']}/{result['sideways_signals']}\n")
            f.write("\n")
        
        f.write("CHI TIẾT GIAO DỊCH\n")
        for i, trade in enumerate(report['all_trades'], 1):
            f.write(f"Giao dịch #{i}\n")
            f.write(f"  Symbol: {trade['symbol']}\n")
            f.write(f"  Nguồn tín hiệu: {trade['signal_source']}")
            if trade['sideways_period']:
                f.write(" (thị trường đi ngang)\n")
            else:
                f.write("\n")
            f.write(f"  Loại: {trade['type']}\n")
            f.write(f"  Mở lệnh: {trade['entry_date']} tại ${trade['entry_price']:.2f}\n")
            f.write(f"  Stop Loss: ${trade['stop_loss']:.2f}\n")
            f.write(f"  Take Profit: ${trade['take_profit']:.2f}\n")
            f.write(f"  Kích thước vị thế: {trade['position_size']:.4f}, Đòn bẩy: {trade['leverage']}x\n")
            f.write(f"  Đóng lệnh: {trade['exit_date']} tại ${trade['exit_price']:.2f}\n")
            f.write(f"  Lý do đóng: {trade['exit_reason']}\n")
            f.write(f"  Lợi nhuận: ${trade['profit']:.2f} ({trade['profit_pct']:.2f}%)\n\n")
    
    logger.info(f"Đã lưu báo cáo: {report_file}")
    logger.info(f"Đã lưu dữ liệu JSON: {json_file}")
    
    return report_file

def plot_results(report, output_dir="backtest_reports"):
    """Vẽ biểu đồ kết quả backtest"""
    if not report['all_trades']:
        logger.warning("Không có dữ liệu giao dịch để vẽ biểu đồ")
        return
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_file = os.path.join(output_dir, f'adaptive_backtest_chart_{timestamp}.png')
        
        # Dữ liệu cho biểu đồ
        trades_df = pd.DataFrame(report['all_trades'])
        
        plt.figure(figsize=(15, 12))
        
        # 1. Biểu đồ lợi nhuận theo giao dịch
        plt.subplot(3, 2, 1)
        colors = ['green' if x > 0 else 'red' for x in trades_df['profit_pct']]
        plt.bar(range(1, len(trades_df) + 1), trades_df['profit_pct'], color=colors)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.title('Lợi nhuận theo giao dịch (%)')
        plt.xlabel('Giao dịch #')
        plt.ylabel('Lợi nhuận (%)')
        
        # 2. Biểu đồ tỉ lệ thắng/thua
        plt.subplot(3, 2, 2)
        plt.pie([report['winning_trades'], report['losing_trades']], 
               labels=['Thắng', 'Thua'],
               colors=['green', 'red'],
               autopct='%1.1f%%',
               startangle=90)
        plt.axis('equal')
        plt.title('Tỉ lệ thắng/thua')
        
        # 3. Biểu đồ số dư
        plt.subplot(3, 2, (3, 4))
        balances = [report['initial_balance']]
        
        for trade in report['all_trades']:
            balances.append(trade['balance_after'])
        
        plt.plot(range(len(balances)), balances, marker='o', linestyle='-', color='blue')
        plt.title('Tăng trưởng số dư')
        plt.xlabel('Giao dịch #')
        plt.ylabel('Số dư ($)')
        plt.grid(True, alpha=0.3)
        
        # 4. Biểu đồ lợi nhuận theo symbol
        plt.subplot(3, 2, 5)
        symbols = list(report['symbol_results'].keys())
        symbol_profits = [report['symbol_results'][s]['profit'] for s in symbols]
        colors = ['green' if x > 0 else 'red' for x in symbol_profits]
        
        plt.bar(symbols, symbol_profits, color=colors)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.title('Lợi nhuận theo symbol')
        plt.xlabel('Symbol')
        plt.ylabel('Lợi nhuận ($)')
        plt.xticks(rotation=45)
        
        # 5. Biểu đồ tỉ lệ nguồn tín hiệu
        plt.subplot(3, 2, 6)
        signal_sources = trades_df['signal_source'].value_counts()
        plt.pie(signal_sources.values, 
               labels=signal_sources.index,
               autopct='%1.1f%%',
               startangle=90)
        plt.axis('equal')
        plt.title('Nguồn tín hiệu giao dịch')
        
        plt.tight_layout()
        plt.savefig(chart_file)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ: {chart_file}")
        
    except Exception as e:
        logger.error(f"Lỗi khi vẽ biểu đồ: {e}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Công cụ backtest chiến lược thích ứng')
    parser.add_argument('--symbols', nargs='+', default=['BTC-USD', 'ETH-USD', 'SOL-USD'],
                        help='Danh sách các symbols cần test (e.g., BTC-USD ETH-USD)')
    parser.add_argument('--period', default='3mo', help='Khoảng thời gian (e.g., 1mo, 3mo, 6mo)')
    parser.add_argument('--timeframe', default='1d', help='Khung thời gian (e.g., 1d, 4h, 1h)')
    parser.add_argument('--balance', type=float, default=10000, help='Số dư ban đầu')
    parser.add_argument('--output-dir', default='backtest_reports', help='Thư mục đầu ra')
    parser.add_argument('--no-plot', action='store_true', default=True, help='Không vẽ biểu đồ')
    parser.add_argument('--plot', action='store_false', dest='no_plot', help='Vẽ biểu đồ (cần môi trường hỗ trợ đồ họa Qt)')
    parser.add_argument('--use-binance', action='store_true', help='Sử dụng dữ liệu từ Binance thay vì Yahoo Finance')
    
    args = parser.parse_args()
    
    # Kiểm tra, nếu chuỗi được truyền vào (e.g., --symbols "BTC-USD,ETH-USD"), thì tách ra
    if len(args.symbols) == 1 and ',' in args.symbols[0]:
        args.symbols = args.symbols[0].split(',')
    
    # Kiểm tra API keys khi sử dụng dữ liệu Binance
    if args.use_binance:
        import os
        api_key = os.environ.get('BINANCE_API_KEY', '')
        api_secret = os.environ.get('BINANCE_API_SECRET', '')
        
        if not api_key or not api_secret:
            logger.warning("BINANCE_API_KEY hoặc BINANCE_API_SECRET không được thiết lập. Chuyển sang sử dụng Yahoo Finance.")
            args.use_binance = False
    
    # Chạy backtest
    logger.info(f"Bắt đầu backtest với nguồn dữ liệu: {('Binance' if args.use_binance else 'Yahoo Finance')}")
    
    report = run_adaptive_backtest(
        symbols=args.symbols,
        period=args.period,
        timeframe=args.timeframe,
        initial_balance=args.balance,
        use_binance_data=args.use_binance
    )
    
    # Lưu báo cáo
    save_report(report, args.output_dir)
    
    # Vẽ biểu đồ
    if not args.no_plot:
        plot_results(report, args.output_dir)

if __name__ == "__main__":
    main()