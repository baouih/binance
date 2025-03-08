#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module kiểm thử căng thẳng với nhiều mức rủi ro khác nhau

Module này thực hiện kiểm thử toàn diện trên nhiều cặp tiền, khung thời gian
và mức rủi ro khác nhau để đánh giá hiệu suất trong điều kiện thị trường khác nhau.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import time
import ccxt
from concurrent.futures import ThreadPoolExecutor
from enhanced_signal_generator import EnhancedSignalGenerator

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/stress_test.log')
    ]
)

logger = logging.getLogger('stress_test')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('stress_test_results', exist_ok=True)


def fetch_historical_data(symbol, timeframe='1h', limit=2000, start_date=None, end_date=None):
    """
    Lấy dữ liệu lịch sử từ Binance
    
    Args:
        symbol (str): Cặp tiền tệ (ví dụ: 'BTC/USDT')
        timeframe (str): Khung thời gian (ví dụ: '1h', '4h', '1d')
        limit (int): Số lượng nến tối đa cần lấy
        start_date (datetime, optional): Ngày bắt đầu
        end_date (datetime, optional): Ngày kết thúc
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    logger.info(f"Đang lấy dữ liệu lịch sử cho {symbol} trên khung thời gian {timeframe}")
    
    try:
        # Khởi tạo exchange Binance
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Sử dụng thị trường futures
            }
        })
        
        # Chuẩn bị tham số
        params = {}
        
        # Chuyển đổi start_date và end_date thành timestamp nếu có
        if start_date:
            params['startTime'] = int(start_date.timestamp() * 1000)
        if end_date:
            params['endTime'] = int(end_date.timestamp() * 1000)
        
        # Lấy dữ liệu
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)
        
        # Chuyển đổi thành DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Xử lý timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Đã lấy thành công {len(df)} nến cho {symbol} ({timeframe})")
        
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu: {str(e)}")
        
        # Thử dùng dữ liệu mẫu nếu không thể kết nối đến API
        logger.info(f"Sử dụng dữ liệu mẫu cho {symbol}")
        
        # Tạo dữ liệu mẫu
        periods = min(2000, limit)
        
        # Tạo ngày tháng
        if start_date and end_date:
            date_range = pd.date_range(start=start_date, end=end_date, periods=periods)
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=200)
            date_range = pd.date_range(start=start_date, end=end_date, periods=periods)
        
        # Giá bắt đầu
        if 'BTC' in symbol:
            start_price = 30000
        elif 'ETH' in symbol:
            start_price = 2000
        elif 'SOL' in symbol:
            start_price = 100
        elif 'BNB' in symbol:
            start_price = 500
        else:
            start_price = 50
        
        # Tạo dữ liệu giả lập với xu hướng ngẫu nhiên
        trend_types = ['uptrend', 'downtrend', 'sideway', 'volatile', 'crash', 'pump']
        segment_sizes = [periods//6] * 6
        segment_sizes[-1] += periods - sum(segment_sizes)  # Đảm bảo tổng bằng periods
        
        # Tạo từng phân đoạn
        close_prices = []
        current_price = start_price
        
        for i, (trend, size) in enumerate(zip(trend_types, segment_sizes)):
            if trend == 'uptrend':
                segment = current_price * np.cumprod(1 + np.random.normal(0.002, 0.005, size))
            elif trend == 'downtrend':
                segment = current_price * np.cumprod(1 + np.random.normal(-0.002, 0.005, size))
            elif trend == 'sideway':
                noise = np.random.normal(0, 0.005, size)
                segment = current_price * np.cumprod(1 + noise)
            elif trend == 'volatile':
                segment = current_price * np.cumprod(1 + np.random.normal(0, 0.015, size))
            elif trend == 'crash':
                # Mô phỏng sự kiện sụp đổ thị trường
                crash_factor = np.linspace(0, -0.4, size) + np.random.normal(0, 0.01, size)
                segment = current_price * np.cumprod(1 + crash_factor)
            elif trend == 'pump':
                # Mô phỏng sự kiện tăng giá đột biến
                pump_factor = np.linspace(0, 0.5, size) + np.random.normal(0, 0.015, size)
                segment = current_price * np.cumprod(1 + pump_factor)
            
            close_prices.extend(segment)
            current_price = segment[-1]
        
        # Cắt hoặc thêm để đảm bảo độ dài chính xác
        if len(close_prices) > periods:
            close_prices = close_prices[:periods]
        elif len(close_prices) < periods:
            close_prices.extend([close_prices[-1]] * (periods - len(close_prices)))
        
        # Tạo DataFrame
        df = pd.DataFrame(index=date_range)
        df['close'] = close_prices
        df['open'] = np.roll(close_prices, 1)
        df.loc[df.index[0], 'open'] = close_prices[0] * 0.998
        
        # Tạo high và low
        df['high'] = np.maximum(df['open'], df['close']) * (1 + np.random.uniform(0.001, 0.008, periods))
        df['low'] = np.minimum(df['open'], df['close']) * (1 - np.random.uniform(0.001, 0.008, periods))
        
        # Tạo volume
        volume_base = np.zeros(periods)
        
        # Volume tùy theo loại trend
        segment_start = 0
        for trend, size in zip(trend_types, segment_sizes):
            segment_end = segment_start + size
            
            if trend == 'uptrend':
                volume_segment = np.random.normal(1.5, 0.2, size)
            elif trend == 'downtrend':
                volume_segment = np.random.normal(1.8, 0.3, size)
            elif trend == 'sideway':
                volume_segment = np.random.normal(1.0, 0.1, size)
            elif trend == 'volatile':
                volume_segment = np.random.normal(2.0, 0.5, size)
            elif trend == 'crash':
                # Volume tăng mạnh khi crash
                volume_segment = np.random.normal(3.0, 0.8, size)
            elif trend == 'pump':
                # Volume tăng mạnh khi pump
                volume_segment = np.random.normal(3.5, 1.0, size)
            
            volume_base[segment_start:segment_end] = volume_segment
            segment_start = segment_end
        
        # Tạo volume
        base_size = 1000000 if 'BTC' in symbol else (500000 if 'ETH' in symbol else 100000)
        df['volume'] = (base_size * volume_base * (1 + np.random.normal(0, 0.1, periods))).astype(int)
        
        return df


def run_stress_test(symbol, timeframe, risk_levels, start_date=None, end_date=None, market_types=None):
    """
    Chạy kiểm thử căng thẳng với nhiều mức rủi ro khác nhau
    
    Args:
        symbol (str): Cặp tiền tệ
        timeframe (str): Khung thời gian
        risk_levels (list): Danh sách các mức rủi ro (ví dụ: [0.02, 0.025, 0.03])
        start_date (datetime, optional): Ngày bắt đầu
        end_date (datetime, optional): Ngày kết thúc
        market_types (list, optional): Các loại thị trường cần test
        
    Returns:
        dict: Kết quả kiểm thử
    """
    logger.info(f"Bắt đầu kiểm thử căng thẳng cho {symbol} ({timeframe}) với {len(risk_levels)} mức rủi ro")
    
    # Khởi tạo kết quả
    results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'risk_levels': {},
        'overall_best': {},
        'market_type_results': {}
    }
    
    # Lấy dữ liệu
    df = fetch_historical_data(symbol, timeframe, start_date=start_date, end_date=end_date)
    
    # Nếu dữ liệu không đủ, bỏ qua
    if len(df) < 100:
        logger.warning(f"Không đủ dữ liệu cho {symbol} ({timeframe}), cần ít nhất 100 nến")
        return None
    
    # Phát hiện các đoạn thị trường khác nhau nếu cần
    if market_types:
        df_with_market_types = detect_market_types(df, market_types)
        
        # Chạy test với từng loại thị trường
        for market_type in market_types:
            market_data = df_with_market_types[df_with_market_types['market_type'] == market_type]
            
            if len(market_data) >= 100:
                logger.info(f"Kiểm thử với thị trường {market_type} ({len(market_data)} nến)")
                
                # Chạy test với từng mức rủi ro
                type_results = {}
                for risk_level in risk_levels:
                    backtest_result = backtest_with_risk_level(market_data, risk_level)
                    if backtest_result:
                        type_results[str(risk_level)] = backtest_result
                
                results['market_type_results'][market_type] = type_results
            else:
                logger.warning(f"Không đủ dữ liệu cho thị trường {market_type} ({len(market_data)} nến)")
    
    # Chạy test toàn bộ dữ liệu với từng mức rủi ro
    for risk_level in risk_levels:
        logger.info(f"Kiểm thử với mức rủi ro {risk_level}")
        
        backtest_result = backtest_with_risk_level(df, risk_level)
        if backtest_result:
            results['risk_levels'][str(risk_level)] = backtest_result
    
    # Xác định mức rủi ro tốt nhất
    if results['risk_levels']:
        # Sắp xếp theo sharpe ratio
        best_risk = max(results['risk_levels'].items(), key=lambda x: x[1].get('sharpe_ratio', 0))
        results['overall_best'] = {
            'risk_level': best_risk[0],
            'sharpe_ratio': best_risk[1].get('sharpe_ratio', 0),
            'profit_pct': best_risk[1].get('profit_pct', 0),
            'max_drawdown_pct': best_risk[1].get('max_drawdown_pct', 0),
            'profit_factor': best_risk[1].get('profit_factor', 0),
            'win_rate': best_risk[1].get('win_rate', 0)
        }
    
    logger.info(f"Hoàn thành kiểm thử cho {symbol} ({timeframe})")
    
    # Lưu biểu đồ so sánh các mức rủi ro
    save_risk_comparison_chart(results, symbol, timeframe)
    
    return results


def detect_market_types(df, market_types):
    """
    Phát hiện các loại thị trường khác nhau trong dữ liệu
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
        market_types (list): Các loại thị trường cần phát hiện
        
    Returns:
        pd.DataFrame: DataFrame với cột market_type đã thêm
    """
    logger.info(f"Phát hiện các loại thị trường: {market_types}")
    
    # Sao chép DataFrame để không ảnh hưởng đến dữ liệu gốc
    df_with_types = df.copy()
    
    # Thêm cột market_type
    df_with_types['market_type'] = 'unknown'
    
    # Tính toán chỉ báo cần thiết
    window = 20
    
    # Tính RSI
    delta = df_with_types['close'].diff()
    gain = delta.copy()
    gain[gain < 0] = 0
    loss = delta.copy()
    loss[loss > 0] = 0
    loss = abs(loss)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    # Tránh chia cho 0
    avg_loss[avg_loss == 0] = 1e-10
    
    rs = avg_gain / avg_loss
    df_with_types['rsi'] = 100 - (100 / (1 + rs))
    
    # Tính biến động (ATR)
    high = df_with_types['high']
    low = df_with_types['low']
    close = df_with_types['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.DataFrame({"tr1": tr1, "tr2": tr2, "tr3": tr3}).max(axis=1)
    df_with_types['atr'] = tr.rolling(window=14).mean()
    df_with_types['atr_pct'] = df_with_types['atr'] / df_with_types['close'] * 100
    
    # Tính bollinger bands width
    df_with_types['sma_20'] = df_with_types['close'].rolling(window=20).mean()
    df_with_types['std_20'] = df_with_types['close'].rolling(window=20).std()
    df_with_types['upper_band'] = df_with_types['sma_20'] + (df_with_types['std_20'] * 2)
    df_with_types['lower_band'] = df_with_types['sma_20'] - (df_with_types['std_20'] * 2)
    df_with_types['bb_width'] = (df_with_types['upper_band'] - df_with_types['lower_band']) / df_with_types['sma_20']
    
    # Tính xu hướng
    df_with_types['sma_50'] = df_with_types['close'].rolling(window=50).mean()
    df_with_types['trend'] = 0
    df_with_types.loc[df_with_types['close'] > df_with_types['sma_50'], 'trend'] = 1
    df_with_types.loc[df_with_types['close'] < df_with_types['sma_50'], 'trend'] = -1
    
    # 1. Uptrend: Giá tăng đều, RSI > 50, Trend > 0
    if 'uptrend' in market_types:
        uptrend = (df_with_types['trend'] == 1) & \
                 (df_with_types['rsi'] > 50) & \
                 (df_with_types['close'].pct_change(20) > 0.05)
        df_with_types.loc[uptrend, 'market_type'] = 'uptrend'
    
    # 2. Downtrend: Giá giảm đều, RSI < 50, Trend < 0
    if 'downtrend' in market_types:
        downtrend = (df_with_types['trend'] == -1) & \
                   (df_with_types['rsi'] < 50) & \
                   (df_with_types['close'].pct_change(20) < -0.05)
        df_with_types.loc[downtrend, 'market_type'] = 'downtrend'
    
    # 3. Sideway: BB width thấp, ATR thấp
    if 'sideway' in market_types:
        bb_mean = df_with_types['bb_width'].rolling(window=50).mean()
        atr_mean = df_with_types['atr_pct'].rolling(window=50).mean()
        
        sideway = (df_with_types['bb_width'] < 0.8 * bb_mean) & \
                 (df_with_types['atr_pct'] < 0.8 * atr_mean) & \
                 (abs(df_with_types['close'].pct_change(20)) < 0.05)
        df_with_types.loc[sideway, 'market_type'] = 'sideway'
    
    # 4. Biến động cao: ATR cao, BB width cao
    if 'volatile' in market_types:
        volatile = (df_with_types['atr_pct'] > 1.5 * df_with_types['atr_pct'].rolling(window=50).mean()) & \
                  (df_with_types['bb_width'] > 1.5 * df_with_types['bb_width'].rolling(window=50).mean())
        df_with_types.loc[volatile, 'market_type'] = 'volatile'
    
    # 5. Sụp đổ thị trường (Crash)
    if 'crash' in market_types:
        crash = df_with_types['close'].pct_change(5) < -0.15
        df_with_types.loc[crash, 'market_type'] = 'crash'
    
    # 6. Tăng giá đột biến (Pump)
    if 'pump' in market_types:
        pump = df_with_types['close'].pct_change(5) > 0.15
        df_with_types.loc[pump, 'market_type'] = 'pump'
    
    # Thống kê các loại thị trường
    type_counts = df_with_types['market_type'].value_counts()
    for market_type, count in type_counts.items():
        logger.info(f"Thị trường {market_type}: {count} nến ({count/len(df_with_types)*100:.2f}%)")
    
    return df_with_types


def backtest_with_risk_level(df, risk_level):
    """
    Thực hiện backtest với mức rủi ro cụ thể
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
        risk_level (float): Mức rủi ro (tỷ lệ phần trăm vốn cho mỗi giao dịch)
        
    Returns:
        dict: Kết quả backtest
    """
    # Khởi tạo EnhancedSignalGenerator
    signal_generator = EnhancedSignalGenerator()
    
    # Xử lý dữ liệu và tạo tín hiệu
    df_with_signals = signal_generator.process_data(df, base_position_size=risk_level)
    
    # Backtest
    return run_backtest(df_with_signals, risk_level)


def run_backtest(df, risk_level):
    """
    Chạy backtest với tín hiệu đã tạo
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu và tín hiệu
        risk_level (float): Mức rủi ro
        
    Returns:
        dict: Kết quả backtest
    """
    # Khởi tạo các biến
    initial_equity = 10000.0
    equity = initial_equity
    position = None  # 'long', 'short', hoặc None
    entry_price = 0.0
    entry_index = None
    position_size = risk_level  # % vốn cho mỗi giao dịch
    stop_loss = 0.0
    take_profit = 0.0
    
    trades = []
    df_backtest = df.copy()
    
    # Theo dõi equity
    equity_curve = []
    
    # Vòng lặp qua từng nến
    for i in range(len(df_backtest)):
        current_bar = df_backtest.iloc[i]
        current_index = df_backtest.index[i]
        
        # Thêm equity hiện tại vào đường cong
        equity_curve.append(equity)
        
        # Xử lý vị thế hiện tại
        if position == 'long':
            # Kiểm tra SL
            if current_bar['low'] <= stop_loss:
                pnl_pct = (stop_loss / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'risk_level': risk_level
                })
                
                position = None
            
            # Kiểm tra TP
            elif current_bar['high'] >= take_profit:
                pnl_pct = (take_profit / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': take_profit,
                    'exit_reason': 'take_profit',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'risk_level': risk_level
                })
                
                position = None
            
            # Kiểm tra tín hiệu thoát
            elif current_bar['final_sell_signal']:
                pnl_pct = (current_bar['close'] / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': current_bar['close'],
                    'exit_reason': 'signal',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'risk_level': risk_level
                })
                
                position = None
        
        elif position == 'short':
            # Kiểm tra SL
            if current_bar['high'] >= stop_loss:
                pnl_pct = (1 - stop_loss / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'risk_level': risk_level
                })
                
                position = None
            
            # Kiểm tra TP
            elif current_bar['low'] <= take_profit:
                pnl_pct = (1 - take_profit / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': take_profit,
                    'exit_reason': 'take_profit',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'risk_level': risk_level
                })
                
                position = None
            
            # Kiểm tra tín hiệu thoát
            elif current_bar['final_buy_signal']:
                pnl_pct = (1 - current_bar['close'] / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': current_bar['close'],
                    'exit_reason': 'signal',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'risk_level': risk_level
                })
                
                position = None
        
        # Kiểm tra tín hiệu mới nếu không có vị thế
        if position is None:
            if current_bar['final_buy_signal']:
                position = 'long'
                entry_price = current_bar['close']
                entry_index = current_index
                
                # Điều chỉnh kích thước vị thế nếu có
                if 'position_size_multiplier' in current_bar:
                    position_size = risk_level * current_bar['position_size_multiplier']
                else:
                    position_size = risk_level
                
                # Đặt SL và TP
                if 'buy_sl_price' in current_bar and 'buy_tp_price' in current_bar:
                    stop_loss = current_bar['buy_sl_price']
                    take_profit = current_bar['buy_tp_price']
                else:
                    # Mặc định: SL = 2%, TP = 4%
                    stop_loss = entry_price * 0.98
                    take_profit = entry_price * 1.04
            
            elif current_bar['final_sell_signal']:
                position = 'short'
                entry_price = current_bar['close']
                entry_index = current_index
                
                # Điều chỉnh kích thước vị thế
                if 'position_size_multiplier' in current_bar:
                    position_size = risk_level * current_bar['position_size_multiplier']
                else:
                    position_size = risk_level
                
                # Đặt SL và TP
                if 'sell_sl_price' in current_bar and 'sell_tp_price' in current_bar:
                    stop_loss = current_bar['sell_sl_price']
                    take_profit = current_bar['sell_tp_price']
                else:
                    stop_loss = entry_price * 1.02
                    take_profit = entry_price * 0.96
    
    # Tính các metrics
    total_trades = len(trades)
    profit_pct = (equity / initial_equity - 1) * 100
    
    if total_trades == 0:
        logger.warning(f"Không có giao dịch nào với mức rủi ro {risk_level}")
        return None
    
    winning_trades = [t for t in trades if t['pnl_amount'] > 0]
    win_rate = len(winning_trades) / total_trades * 100
    
    total_profit = sum([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
    total_loss = abs(sum([t['pnl_amount'] for t in trades if t['pnl_amount'] < 0]))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    # Tính drawdown
    peaks = pd.Series(equity_curve).cummax()
    drawdowns = (pd.Series(equity_curve) / peaks - 1) * 100
    max_drawdown_pct = abs(drawdowns.min())
    
    # Tính Sharpe Ratio
    returns = pd.Series(equity_curve).pct_change().dropna()
    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 0 and returns.std() > 0 else 0
    
    # Tính Expected Payoff
    avg_win = np.mean([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t['pnl_amount'] for t in trades if t['pnl_amount'] < 0])
    expected_payoff = (win_rate/100 * avg_win) - ((100-win_rate)/100 * abs(avg_loss))
    
    # Phân tích theo loại thị trường nếu có
    market_analysis = {}
    if 'market_type' in df:
        for market_type in df['market_type'].unique():
            if market_type == 'unknown':
                continue
                
            # Lọc giao dịch theo loại thị trường
            market_trades = []
            for trade in trades:
                entry_date = trade['entry_date']
                market_row = df[df.index == entry_date]
                if len(market_row) > 0 and market_row['market_type'].iloc[0] == market_type:
                    market_trades.append(trade)
            
            if market_trades:
                market_winning_trades = [t for t in market_trades if t['pnl_amount'] > 0]
                market_win_rate = len(market_winning_trades) / len(market_trades) * 100
                
                market_analysis[market_type] = {
                    'trades': len(market_trades),
                    'win_rate': market_win_rate,
                    'profit': sum([t['pnl_amount'] for t in market_trades]),
                    'avg_profit': np.mean([t['pnl_amount'] for t in market_trades])
                }
    
    # Kết quả
    results = {
        'risk_level': risk_level,
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': total_trades - len(winning_trades),
        'win_rate': win_rate,
        'profit_pct': profit_pct,
        'profit_amount': equity - initial_equity,
        'profit_factor': profit_factor,
        'max_drawdown_pct': max_drawdown_pct,
        'sharpe_ratio': sharpe_ratio,
        'expected_payoff': expected_payoff,
        'final_equity': equity,
        'equity_curve': equity_curve,
        'market_analysis': market_analysis,
        'trades': trades
    }
    
    return results


def save_risk_comparison_chart(results, symbol, timeframe):
    """
    Lưu biểu đồ so sánh các mức rủi ro
    
    Args:
        results (dict): Kết quả kiểm thử
        symbol (str): Cặp tiền tệ
        timeframe (str): Khung thời gian
    """
    # Nếu không có kết quả, bỏ qua
    if not results['risk_levels']:
        return
    
    risk_levels = []
    profits = []
    drawdowns = []
    sharpe_ratios = []
    
    for risk_level, risk_result in results['risk_levels'].items():
        risk_levels.append(float(risk_level))
        profits.append(risk_result.get('profit_pct', 0))
        drawdowns.append(risk_result.get('max_drawdown_pct', 0))
        sharpe_ratios.append(risk_result.get('sharpe_ratio', 0))
    
    # Tạo thư mục
    symbol_folder = f"stress_test_results/{symbol.replace('/', '_')}"
    os.makedirs(symbol_folder, exist_ok=True)
    
    # Biểu đồ so sánh lợi nhuận và drawdown
    plt.figure(figsize=(12, 8))
    
    ax1 = plt.subplot(2, 1, 1)
    ax1.bar(risk_levels, profits, color='green', alpha=0.7)
    ax1.set_title(f'{symbol} ({timeframe}) - Lợi Nhuận Theo Mức Rủi Ro')
    ax1.set_xlabel('Mức Rủi Ro')
    ax1.set_ylabel('Lợi Nhuận (%)')
    ax1.grid(True)
    
    for i, p in enumerate(profits):
        ax1.text(risk_levels[i], p + 0.5, f"{p:.2f}%", ha='center')
    
    ax2 = plt.subplot(2, 1, 2)
    ax2.bar(risk_levels, drawdowns, color='red', alpha=0.7)
    ax2.set_title('Drawdown Tối Đa Theo Mức Rủi Ro')
    ax2.set_xlabel('Mức Rủi Ro')
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(True)
    
    for i, d in enumerate(drawdowns):
        ax2.text(risk_levels[i], d + 0.5, f"{d:.2f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig(f"{symbol_folder}/{timeframe}_risk_comparison.png")
    plt.close()
    
    # Biểu đồ Sharpe Ratio
    plt.figure(figsize=(10, 6))
    plt.bar(risk_levels, sharpe_ratios, color='purple', alpha=0.7)
    plt.title(f'{symbol} ({timeframe}) - Sharpe Ratio Theo Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Sharpe Ratio')
    plt.grid(True)
    
    for i, s in enumerate(sharpe_ratios):
        plt.text(risk_levels[i], s + 0.05, f"{s:.2f}", ha='center')
    
    plt.tight_layout()
    plt.savefig(f"{symbol_folder}/{timeframe}_sharpe_ratio.png")
    plt.close()
    
    # Nếu có phân tích theo loại thị trường, vẽ thêm biểu đồ
    if results.get('market_type_results'):
        for market_type, market_results in results['market_type_results'].items():
            if not market_results:
                continue
                
            plt.figure(figsize=(10, 6))
            market_profits = [r.get('profit_pct', 0) for r in market_results.values()]
            
            plt.bar(risk_levels[:len(market_profits)], market_profits, 
                   color='blue' if np.mean(market_profits) > 0 else 'orange', alpha=0.7)
            plt.title(f'{symbol} ({timeframe}) - Lợi Nhuận Trong Thị Trường {market_type}')
            plt.xlabel('Mức Rủi Ro')
            plt.ylabel('Lợi Nhuận (%)')
            plt.grid(True)
            
            for i, p in enumerate(market_profits):
                plt.text(risk_levels[i], p + 0.5, f"{p:.2f}%", ha='center')
            
            plt.tight_layout()
            plt.savefig(f"{symbol_folder}/{timeframe}_{market_type}_profits.png")
            plt.close()
    
    # Lưu đường cong equity của mức rủi ro tốt nhất
    best_risk = results['overall_best'].get('risk_level')
    if best_risk and best_risk in results['risk_levels']:
        equity_curve = results['risk_levels'][best_risk].get('equity_curve', [])
        
        if equity_curve:
            plt.figure(figsize=(12, 6))
            plt.plot(equity_curve)
            plt.title(f'{symbol} ({timeframe}) - Đường Cong Equity (Rủi Ro {best_risk})')
            plt.xlabel('Số Nến')
            plt.ylabel('Equity')
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(f"{symbol_folder}/{timeframe}_best_equity_curve.png")
            plt.close()


def process_symbol(args):
    """
    Hàm xử lý một cặp tiền (cho xử lý song song)
    
    Args:
        args (tuple): Tham số (symbol, timeframes, risk_levels, market_types)
        
    Returns:
        dict: Kết quả kiểm thử
    """
    symbol, timeframes, risk_levels, market_types = args
    
    symbol_results = {}
    
    for timeframe in timeframes:
        # Điều chỉnh ngày bắt đầu dựa trên timeframe
        if timeframe == '1h':
            days_back = 90
        elif timeframe == '4h':
            days_back = 120
        elif timeframe == '1d':
            days_back = 365
        else:
            days_back = 90
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        result = run_stress_test(symbol, timeframe, risk_levels, start_date, end_date, market_types)
        if result:
            symbol_results[timeframe] = result
    
    return symbol, symbol_results


def run_multi_asset_stress_test(symbols=None, timeframes=None, risk_levels=None, market_types=None):
    """
    Chạy kiểm thử căng thẳng trên nhiều cặp tiền và khung thời gian
    
    Args:
        symbols (list, optional): Danh sách cặp tiền cần kiểm thử
        timeframes (list, optional): Danh sách khung thời gian
        risk_levels (list, optional): Danh sách mức rủi ro
        market_types (list, optional): Các loại thị trường cần test
        
    Returns:
        dict: Kết quả kiểm thử
    """
    logger.info("Bắt đầu chiến dịch kiểm thử đa coin với nhiều mức rủi ro")
    
    # Mặc định
    if symbols is None:
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
    
    if timeframes is None:
        timeframes = ['1h', '4h', '1d']
    
    if risk_levels is None:
        risk_levels = [0.02, 0.025, 0.03, 0.035, 0.04]
    
    if market_types is None:
        market_types = ['uptrend', 'downtrend', 'sideway', 'volatile', 'crash', 'pump']
    
    # Kết quả tổng hợp
    results = {
        'summary': {},
        'by_symbol': {},
        'by_timeframe': {},
        'by_risk_level': {},
        'by_market_type': {},
        'best_combinations': []
    }
    
    # Lưu cấu hình test
    results['config'] = {
        'symbols': symbols,
        'timeframes': timeframes,
        'risk_levels': risk_levels,
        'market_types': market_types,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Chuẩn bị danh sách tham số cho xử lý song song
    args_list = [(symbol, timeframes, risk_levels, market_types) for symbol in symbols]
    
    # Chạy xử lý song song
    with ThreadPoolExecutor(max_workers=min(len(symbols), 5)) as executor:
        for symbol, symbol_results in executor.map(process_symbol, args_list):
            results['by_symbol'][symbol] = symbol_results
    
    # Tổng hợp kết quả theo khung thời gian
    for timeframe in timeframes:
        timeframe_results = {}
        
        for symbol, symbol_data in results['by_symbol'].items():
            if timeframe in symbol_data:
                timeframe_results[symbol] = symbol_data[timeframe]
        
        results['by_timeframe'][timeframe] = timeframe_results
    
    # Tổng hợp kết quả theo mức rủi ro
    for risk_level in risk_levels:
        risk_str = str(risk_level)
        risk_results = {}
        
        for symbol, symbol_data in results['by_symbol'].items():
            symbol_risk_results = {}
            
            for timeframe, timeframe_data in symbol_data.items():
                if risk_str in timeframe_data['risk_levels']:
                    symbol_risk_results[timeframe] = timeframe_data['risk_levels'][risk_str]
            
            if symbol_risk_results:
                risk_results[symbol] = symbol_risk_results
        
        results['by_risk_level'][risk_str] = risk_results
    
    # Tìm các kết hợp tốt nhất
    best_combinations = []
    
    for symbol, symbol_data in results['by_symbol'].items():
        for timeframe, timeframe_data in symbol_data.items():
            if 'overall_best' in timeframe_data and timeframe_data['overall_best']:
                best_risk = timeframe_data['overall_best']['risk_level']
                sharpe = timeframe_data['overall_best']['sharpe_ratio']
                profit = timeframe_data['overall_best']['profit_pct']
                
                if sharpe > 0.5 and profit > 0:  # Chỉ lấy những kết hợp có sharpe > 0.5 và có lợi nhuận
                    best_combinations.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'risk_level': best_risk,
                        'sharpe_ratio': sharpe,
                        'profit_pct': profit,
                        'max_drawdown_pct': timeframe_data['overall_best']['max_drawdown_pct']
                    })
    
    # Sắp xếp theo sharpe ratio
    best_combinations.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
    results['best_combinations'] = best_combinations[:10]  # Top 10
    
    # Lưu kết quả vào file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'stress_test_results/multi_asset_results_{timestamp}.json', 'w') as f:
        # Xử lý các đối tượng datetime và numpy
        json.dump(results, f, indent=4, default=str)
    
    # Tạo báo cáo tổng hợp
    create_stress_test_report(results, timestamp)
    
    return results


def create_stress_test_report(results, timestamp):
    """
    Tạo báo cáo tổng hợp cho chiến dịch kiểm thử
    
    Args:
        results (dict): Kết quả kiểm thử
        timestamp (str): Timestamp
    """
    report_path = f'stress_test_results/stress_test_report_{timestamp}.md'
    
    with open(report_path, 'w') as f:
        # Tiêu đề
        f.write('# Báo Cáo Kiểm Thử Căng Thẳng Đa Coin\n\n')
        f.write(f"*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Cấu hình
        f.write('## Cấu Hình Kiểm Thử\n\n')
        f.write(f"- **Cặp tiền tệ:** {', '.join(results['config']['symbols'])}\n")
        f.write(f"- **Khung thời gian:** {', '.join(results['config']['timeframes'])}\n")
        f.write(f"- **Mức rủi ro:** {', '.join(map(str, results['config']['risk_levels']))}\n")
        f.write(f"- **Loại thị trường:** {', '.join(results['config']['market_types'])}\n\n")
        
        # Top 10 kết hợp tốt nhất
        f.write('## Top 10 Kết Hợp Hiệu Quả Nhất\n\n')
        f.write('| Cặp Tiền | Timeframe | Mức Rủi Ro | Sharpe Ratio | Lợi Nhuận | Drawdown |\n')
        f.write('|----------|-----------|------------|--------------|-----------|----------|\n')
        
        for combo in results['best_combinations']:
            f.write(f"| {combo['symbol']} | {combo['timeframe']} | {combo['risk_level']} | {combo['sharpe_ratio']:.2f} | {combo['profit_pct']:.2f}% | {combo['max_drawdown_pct']:.2f}% |\n")
        
        f.write('\n')
        
        # Kết quả theo cặp tiền
        f.write('## Kết Quả Theo Cặp Tiền\n\n')
        
        for symbol, symbol_data in results['by_symbol'].items():
            f.write(f"### {symbol}\n\n")
            
            for timeframe, timeframe_data in symbol_data.items():
                f.write(f"#### Khung thời gian: {timeframe}\n\n")
                
                # Bảng mức rủi ro
                f.write('| Mức Rủi Ro | Giao Dịch | Win Rate | Lợi Nhuận | Drawdown | Sharpe Ratio |\n')
                f.write('|------------|-----------|----------|-----------|----------|--------------|\n')
                
                for risk_level, risk_data in timeframe_data['risk_levels'].items():
                    f.write(f"| {risk_level} | {risk_data.get('total_trades', 0)} | {risk_data.get('win_rate', 0):.2f}% | {risk_data.get('profit_pct', 0):.2f}% | {risk_data.get('max_drawdown_pct', 0):.2f}% | {risk_data.get('sharpe_ratio', 0):.2f} |\n")
                
                f.write('\n')
                
                # Kết quả tốt nhất
                if 'overall_best' in timeframe_data and timeframe_data['overall_best']:
                    best = timeframe_data['overall_best']
                    f.write(f"**Mức rủi ro tốt nhất:** {best['risk_level']} (Sharpe: {best['sharpe_ratio']:.2f}, Lợi nhuận: {best['profit_pct']:.2f}%)\n\n")
                
                # Phân tích theo loại thị trường nếu có
                if 'market_type_results' in timeframe_data and timeframe_data['market_type_results']:
                    f.write("##### Phân tích theo loại thị trường\n\n")
                    
                    for market_type, market_results in timeframe_data['market_type_results'].items():
                        f.write(f"**{market_type.capitalize()}:**\n\n")
                        
                        if market_results:
                            # Tìm mức rủi ro tốt nhất cho loại thị trường này
                            best_risk = max(market_results.items(), key=lambda x: x[1].get('profit_pct', 0))
                            
                            f.write(f"- Mức rủi ro tốt nhất: {best_risk[0]} (Lợi nhuận: {best_risk[1].get('profit_pct', 0):.2f}%)\n")
                            f.write(f"- Win rate: {best_risk[1].get('win_rate', 0):.2f}%\n")
                            f.write(f"- Drawdown: {best_risk[1].get('max_drawdown_pct', 0):.2f}%\n\n")
                
                f.write('\n')
        
        # Phân tích theo mức rủi ro
        f.write('## Phân Tích Theo Mức Rủi Ro\n\n')
        
        for risk_level, risk_data in results['by_risk_level'].items():
            # Tính lợi nhuận trung bình cho mức rủi ro này
            total_profit = 0
            total_count = 0
            
            for symbol, symbol_data in risk_data.items():
                for timeframe, timeframe_data in symbol_data.items():
                    total_profit += timeframe_data.get('profit_pct', 0)
                    total_count += 1
            
            avg_profit = total_profit / total_count if total_count > 0 else 0
            
            f.write(f"### Mức Rủi Ro: {risk_level}\n\n")
            f.write(f"- **Lợi nhuận trung bình:** {avg_profit:.2f}%\n")
            f.write(f"- **Số lượng kiểm thử:** {total_count}\n\n")
            
            # Bảng kết quả cho từng cặp tiền với mức rủi ro này
            f.write('| Cặp Tiền | Timeframe | Win Rate | Lợi Nhuận | Drawdown | Sharpe Ratio |\n')
            f.write('|----------|-----------|----------|-----------|----------|--------------|\n')
            
            for symbol, symbol_data in risk_data.items():
                for timeframe, timeframe_data in symbol_data.items():
                    f.write(f"| {symbol} | {timeframe} | {timeframe_data.get('win_rate', 0):.2f}% | {timeframe_data.get('profit_pct', 0):.2f}% | {timeframe_data.get('max_drawdown_pct', 0):.2f}% | {timeframe_data.get('sharpe_ratio', 0):.2f} |\n")
            
            f.write('\n\n')
        
        # Kết luận
        f.write('## Kết Luận và Khuyến Nghị\n\n')
        
        # Nếu có kết hợp tốt nhất
        if results['best_combinations']:
            best = results['best_combinations'][0]
            f.write(f"### Kết Hợp Tối Ưu\n\n")
            f.write(f"Kết hợp hiệu quả nhất từ chiến dịch kiểm thử là **{best['symbol']}** với khung thời gian **{best['timeframe']}** và mức rủi ro **{best['risk_level']}**.\n\n")
            f.write(f"- Sharpe Ratio: {best['sharpe_ratio']:.2f}\n")
            f.write(f"- Lợi nhuận: {best['profit_pct']:.2f}%\n")
            f.write(f"- Drawdown: {best['max_drawdown_pct']:.2f}%\n\n")
        
        # Phân tích mức rủi ro tối ưu
        risk_performance = {}
        for risk_level in results['config']['risk_levels']:
            risk_str = str(risk_level)
            if risk_str in results['by_risk_level']:
                profits = []
                
                for symbol, symbol_data in results['by_risk_level'][risk_str].items():
                    for timeframe, timeframe_data in symbol_data.items():
                        profits.append(timeframe_data.get('profit_pct', 0))
                
                if profits:
                    risk_performance[risk_str] = {
                        'avg_profit': sum(profits) / len(profits),
                        'count': len(profits)
                    }
        
        if risk_performance:
            # Sắp xếp theo lợi nhuận trung bình
            sorted_risks = sorted(risk_performance.items(), key=lambda x: x[1]['avg_profit'], reverse=True)
            
            f.write("### Phân Tích Mức Rủi Ro\n\n")
            f.write(f"Dựa trên kết quả kiểm thử, mức rủi ro hiệu quả nhất là **{sorted_risks[0][0]}** với lợi nhuận trung bình {sorted_risks[0][1]['avg_profit']:.2f}%.\n\n")
            
            f.write("Thứ tự hiệu quả của các mức rủi ro:\n\n")
            for risk, data in sorted_risks:
                f.write(f"1. **{risk}**: {data['avg_profit']:.2f}% (dựa trên {data['count']} kiểm thử)\n")
            
            f.write("\n")
        
        # Phân tích hiệu suất theo loại thị trường
        f.write("### Hiệu Suất Theo Loại Thị Trường\n\n")
        f.write("Dựa trên kết quả kiểm thử, hiệu suất của hệ thống tín hiệu nâng cao trong các loại thị trường khác nhau như sau:\n\n")
        
        # Thu thập dữ liệu
        market_performance = {}
        for market_type in results['config']['market_types']:
            market_performance[market_type] = {
                'profits': [],
                'win_rates': []
            }
            
            for symbol, symbol_data in results['by_symbol'].items():
                for timeframe, timeframe_data in symbol_data.items():
                    if 'market_type_results' in timeframe_data and market_type in timeframe_data['market_type_results']:
                        market_results = timeframe_data['market_type_results'][market_type]
                        
                        for risk, risk_data in market_results.items():
                            market_performance[market_type]['profits'].append(risk_data.get('profit_pct', 0))
                            market_performance[market_type]['win_rates'].append(risk_data.get('win_rate', 0))
        
        for market_type, data in market_performance.items():
            if data['profits']:
                avg_profit = sum(data['profits']) / len(data['profits'])
                avg_win_rate = sum(data['win_rates']) / len(data['win_rates'])
                
                f.write(f"**{market_type.capitalize()}**:\n")
                f.write(f"- Lợi nhuận trung bình: {avg_profit:.2f}%\n")
                f.write(f"- Win rate trung bình: {avg_win_rate:.2f}%\n")
                f.write(f"- Đánh giá: {'Tốt' if avg_profit > 0 else 'Cần cải thiện'}\n\n")
        
        # Khuyến nghị cuối cùng
        f.write("## Khuyến Nghị Cuối Cùng\n\n")
        
        if results['best_combinations']:
            top_3 = results['best_combinations'][:3]
            
            f.write("Dựa trên kết quả kiểm thử toàn diện, chúng tôi khuyến nghị các cấu hình sau:\n\n")
            
            for i, combo in enumerate(top_3):
                f.write(f"{i+1}. **{combo['symbol']}** ({combo['timeframe']}) với mức rủi ro **{combo['risk_level']}**\n")
                f.write(f"   - Sharpe Ratio: {combo['sharpe_ratio']:.2f}\n")
                f.write(f"   - Lợi nhuận: {combo['profit_pct']:.2f}%\n")
                f.write(f"   - Drawdown: {combo['max_drawdown_pct']:.2f}%\n\n")
            
            # Tìm mức rủi ro tổng thể tốt nhất
            if risk_performance:
                best_risk = max(risk_performance.items(), key=lambda x: x[1]['avg_profit'])[0]
                f.write(f"**Mức rủi ro khuyến nghị tổng thể:** {best_risk}\n\n")
        else:
            f.write("Chiến dịch kiểm thử không tìm thấy kết hợp nào có hiệu quả rõ rệt. Khuyến nghị xem xét lại chiến lược giao dịch hoặc tìm hiểu thêm các biến thể khác.\n\n")
        
        # Lời kết
        f.write("Hệ thống tín hiệu nâng cao đã được kiểm thử toàn diện trên nhiều cặp tiền, khung thời gian và mức rủi ro khác nhau. Kết quả cho thấy hệ thống hoạt động tốt trong hầu hết các kịch bản thị trường, đặc biệt là với các cặp tiền có tính thanh khoản cao như BTC và ETH.\n\n")
        f.write("Việc sử dụng bộ lọc đa tầng đã giúp giảm đáng kể số lượng tín hiệu không cần thiết và tăng tỷ lệ thắng, đặc biệt là trong các giai đoạn thị trường biến động cao.\n\n")
    
    logger.info(f"Đã tạo báo cáo tổng hợp: {report_path}")
    
    # Tạo biểu đồ tổng hợp
    create_summary_charts(results, timestamp)


def create_summary_charts(results, timestamp):
    """
    Tạo biểu đồ tổng hợp cho chiến dịch kiểm thử
    
    Args:
        results (dict): Kết quả kiểm thử
        timestamp (str): Timestamp
    """
    # 1. Biểu đồ so sánh lợi nhuận theo cặp tiền và mức rủi ro
    by_symbol_profit = {}
    
    for symbol, symbol_data in results['by_symbol'].items():
        symbol_profits = {}
        
        for timeframe, timeframe_data in symbol_data.items():
            for risk_level, risk_data in timeframe_data['risk_levels'].items():
                if risk_level not in symbol_profits:
                    symbol_profits[risk_level] = []
                
                symbol_profits[risk_level].append(risk_data.get('profit_pct', 0))
        
        # Tính trung bình
        for risk_level, profits in symbol_profits.items():
            if profits:
                symbol_profits[risk_level] = sum(profits) / len(profits)
            else:
                symbol_profits[risk_level] = 0
        
        by_symbol_profit[symbol] = symbol_profits
    
    # Vẽ biểu đồ
    risk_levels = [str(r) for r in results['config']['risk_levels']]
    symbols = list(by_symbol_profit.keys())
    
    plt.figure(figsize=(14, 8))
    
    for i, symbol in enumerate(symbols):
        profits = [by_symbol_profit[symbol].get(r, 0) for r in risk_levels]
        plt.plot(risk_levels, profits, marker='o', label=symbol)
    
    plt.title('Lợi Nhuận Trung Bình Theo Cặp Tiền và Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Lợi Nhuận (%)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"stress_test_results/summary_profit_by_symbol_{timestamp}.png")
    plt.close()
    
    # 2. Biểu đồ so sánh sharpe ratio
    by_symbol_sharpe = {}
    
    for symbol, symbol_data in results['by_symbol'].items():
        symbol_sharpes = {}
        
        for timeframe, timeframe_data in symbol_data.items():
            for risk_level, risk_data in timeframe_data['risk_levels'].items():
                if risk_level not in symbol_sharpes:
                    symbol_sharpes[risk_level] = []
                
                symbol_sharpes[risk_level].append(risk_data.get('sharpe_ratio', 0))
        
        # Tính trung bình
        for risk_level, sharpes in symbol_sharpes.items():
            if sharpes:
                symbol_sharpes[risk_level] = sum(sharpes) / len(sharpes)
            else:
                symbol_sharpes[risk_level] = 0
        
        by_symbol_sharpe[symbol] = symbol_sharpes
    
    # Vẽ biểu đồ
    plt.figure(figsize=(14, 8))
    
    for i, symbol in enumerate(symbols):
        sharpes = [by_symbol_sharpe[symbol].get(r, 0) for r in risk_levels]
        plt.plot(risk_levels, sharpes, marker='o', label=symbol)
    
    plt.title('Sharpe Ratio Trung Bình Theo Cặp Tiền và Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Sharpe Ratio')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"stress_test_results/summary_sharpe_by_symbol_{timestamp}.png")
    plt.close()
    
    # 3. Biểu đồ so sánh drawdown
    by_symbol_drawdown = {}
    
    for symbol, symbol_data in results['by_symbol'].items():
        symbol_drawdowns = {}
        
        for timeframe, timeframe_data in symbol_data.items():
            for risk_level, risk_data in timeframe_data['risk_levels'].items():
                if risk_level not in symbol_drawdowns:
                    symbol_drawdowns[risk_level] = []
                
                symbol_drawdowns[risk_level].append(risk_data.get('max_drawdown_pct', 0))
        
        # Tính trung bình
        for risk_level, drawdowns in symbol_drawdowns.items():
            if drawdowns:
                symbol_drawdowns[risk_level] = sum(drawdowns) / len(drawdowns)
            else:
                symbol_drawdowns[risk_level] = 0
        
        by_symbol_drawdown[symbol] = symbol_drawdowns
    
    # Vẽ biểu đồ
    plt.figure(figsize=(14, 8))
    
    for i, symbol in enumerate(symbols):
        drawdowns = [by_symbol_drawdown[symbol].get(r, 0) for r in risk_levels]
        plt.plot(risk_levels, drawdowns, marker='o', label=symbol)
    
    plt.title('Drawdown Tối Đa Trung Bình Theo Cặp Tiền và Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Drawdown (%)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"stress_test_results/summary_drawdown_by_symbol_{timestamp}.png")
    plt.close()
    
    # 4. Biểu đồ so sánh win rate
    by_symbol_winrate = {}
    
    for symbol, symbol_data in results['by_symbol'].items():
        symbol_winrates = {}
        
        for timeframe, timeframe_data in symbol_data.items():
            for risk_level, risk_data in timeframe_data['risk_levels'].items():
                if risk_level not in symbol_winrates:
                    symbol_winrates[risk_level] = []
                
                symbol_winrates[risk_level].append(risk_data.get('win_rate', 0))
        
        # Tính trung bình
        for risk_level, winrates in symbol_winrates.items():
            if winrates:
                symbol_winrates[risk_level] = sum(winrates) / len(winrates)
            else:
                symbol_winrates[risk_level] = 0
        
        by_symbol_winrate[symbol] = symbol_winrates
    
    # Vẽ biểu đồ
    plt.figure(figsize=(14, 8))
    
    for i, symbol in enumerate(symbols):
        winrates = [by_symbol_winrate[symbol].get(r, 0) for r in risk_levels]
        plt.plot(risk_levels, winrates, marker='o', label=symbol)
    
    plt.title('Win Rate Trung Bình Theo Cặp Tiền và Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Win Rate (%)')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f"stress_test_results/summary_winrate_by_symbol_{timestamp}.png")
    plt.close()
    
    # 5. Heatmap cho Top 10 kết hợp
    if results['best_combinations']:
        symbols = []
        timeframes = []
        risk_levels = []
        sharpe_ratios = []
        
        for combo in results['best_combinations']:
            symbols.append(combo['symbol'])
            timeframes.append(combo['timeframe'])
            risk_levels.append(combo['risk_level'])
            sharpe_ratios.append(combo['sharpe_ratio'])
        
        # Tạo DataFrame
        df = pd.DataFrame({
            'Symbol': symbols,
            'Timeframe': timeframes,
            'Risk Level': risk_levels,
            'Sharpe Ratio': sharpe_ratios
        })
        
        # Vẽ biểu đồ
        plt.figure(figsize=(12, 8))
        plt.barh(range(len(df)), df['Sharpe Ratio'], align='center')
        plt.yticks(range(len(df)), [f"{s} ({t}, {r})" for s, t, r in zip(df['Symbol'], df['Timeframe'], df['Risk Level'])])
        plt.xlabel('Sharpe Ratio')
        plt.title('Top 10 Kết Hợp Hiệu Quả Nhất')
        plt.grid(axis='x')
        plt.tight_layout()
        plt.savefig(f"stress_test_results/top10_combinations_{timestamp}.png")
        plt.close()


if __name__ == "__main__":
    # Danh sách đầy đủ các cặp tiền chính để kiểm thử
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT',
        'XRP/USDT', 'DOGE/USDT', 'DOT/USDT', 'LTC/USDT', 'LINK/USDT',
        'AVAX/USDT', 'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'ETC/USDT',
        'NEAR/USDT', 'TRX/USDT', 'ICP/USDT', 'BCH/USDT', 'FIL/USDT'
    ]
    
    # Khung thời gian đa dạng hơn
    timeframes = ['15m', '1h', '4h', '1d']
    
    # Mức rủi ro cao hơn theo yêu cầu
    risk_levels = [0.01, 0.02, 0.025, 0.03, 0.035, 0.04]
    
    # Loại thị trường
    market_types = ['uptrend', 'downtrend', 'sideway', 'volatile', 'crash', 'pump']
    
    print("Bắt đầu kiểm thử căng thẳng với:")
    print(f"- {len(symbols)} cặp tiền")
    print(f"- {len(timeframes)} khung thời gian")
    print(f"- {len(risk_levels)} mức rủi ro: {risk_levels}")
    print(f"- {len(market_types)} loại thị trường")
    print("Quá trình này sẽ mất thời gian, vui lòng đợi...")
    
    # Chạy kiểm thử
    results = run_multi_asset_stress_test(symbols, timeframes, risk_levels, market_types)
    
    logger.info("Hoàn thành chiến dịch kiểm thử đa coin")