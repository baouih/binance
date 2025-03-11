#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chạy backtest nhanh với dữ liệu thực từ Binance
"""

import os
import sys
import json
import time
import logging
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('quick_backtest.log')
    ]
)

logger = logging.getLogger('quick_backtest')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs('test_results', exist_ok=True)
os.makedirs('test_charts', exist_ok=True)
os.makedirs('test_data', exist_ok=True)

def load_data(symbol, timeframe, days=30, use_cache=True):
    """
    Tải dữ liệu từ Binance hoặc cache
    
    Args:
        symbol (str): Cặp tiền (ví dụ: BTCUSDT)
        timeframe (str): Khung thời gian (ví dụ: 1h, 4h)
        days (int): Số ngày dữ liệu
        use_cache (bool): Có sử dụng cache không
    
    Returns:
        pd.DataFrame: Dữ liệu giá
    """
    # Tạo tên file cache
    cache_file = f"test_data/{symbol}_{timeframe}_{days}d.csv"
    
    # Kiểm tra cache
    if use_cache and os.path.exists(cache_file):
        data = pd.read_csv(cache_file)
        
        # Đảm bảo cột timestamp có định dạng datetime
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        logger.info(f"Đã tải dữ liệu từ cache cho {symbol} {timeframe} ({len(data)} dòng)")
        return data
    
    try:
        # Import binance_api module
        try:
            import binance_api
            use_system_api = True
        except ImportError:
            use_system_api = False
        
        if use_system_api:
            # Sử dụng BinanceAPI của hệ thống
            binance = binance_api.BinanceAPI()
            
            # Tính thời gian bắt đầu và kết thúc
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Tải dữ liệu
            historical_klines = binance.get_historical_klines(
                symbol=symbol, 
                interval=timeframe, 
                start_time=start_time.strftime('%Y-%m-%d'), 
                end_time=end_time.strftime('%Y-%m-%d')
            )
            
            # Chuyển đổi dữ liệu thành DataFrame
            historical_data = []
            if historical_klines:
                for kline in historical_klines:
                    historical_data.append({
                        'timestamp': datetime.fromtimestamp(kline[0]/1000),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5])
                    })
            
            # Chuyển đổi dữ liệu
            data = pd.DataFrame(historical_data)
            
            # Đảm bảo cột timestamp có định dạng datetime
            if 'timestamp' in data.columns:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            elif 'open_time' in data.columns:
                data['timestamp'] = pd.to_datetime(data['open_time'])
                data = data.rename(columns={'open_time': 'timestamp'})
        else:
            raise ImportError("Không thể import Binance API")
        
        # Lưu vào cache
        try:
            data.to_csv(cache_file, index=False)
            logger.info(f"Đã lưu dữ liệu vào cache: {cache_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu vào cache: {e}")
        
        logger.info(f"Đã tải dữ liệu từ Binance cho {symbol} {timeframe} ({len(data)} dòng)")
        return data
    
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu từ Binance: {e}")
        return None

def calculate_indicators(data):
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        data (pd.DataFrame): Dữ liệu giá
    
    Returns:
        pd.DataFrame: Dữ liệu với các chỉ báo
    """
    df = data.copy()
    
    # RSI
    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    # Tính RSI
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    # MACD
    def calculate_macd(series, fast=12, slow=26, signal=9):
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        })
    
    # Tính MACD
    macd_data = calculate_macd(df['close'])
    df['macd_line'] = macd_data['macd_line']
    df['macd_signal'] = macd_data['signal_line']
    df['macd_histogram'] = macd_data['histogram']
    
    # Tính EMA
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # Tính Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['upper_band'] = df['sma20'] + 2 * df['close'].rolling(window=20).std()
    df['lower_band'] = df['sma20'] - 2 * df['close'].rolling(window=20).std()
    
    # Tính ATR
    def calculate_atr(df, period=14):
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    df['atr'] = calculate_atr(df)
    
    return df

def time_optimized_strategy(data, symbol):
    """
    Chiến lược giao dịch tối ưu thời gian
    
    Args:
        data (pd.DataFrame): Dữ liệu giá với các chỉ báo
        symbol (str): Cặp tiền
    
    Returns:
        list: Danh sách tín hiệu
    """
    df = data.copy()
    signals = []
    
    for i in range(50, len(df)):
        current_time = df.iloc[i]['timestamp']
        hour = current_time.hour
        
        # Kiểm tra điều kiện SHORT trong giờ London/New York mở cửa
        if (8 <= hour <= 10) or (13 <= hour <= 15):
            # Điều kiện kỹ thuật bổ sung
            if df.iloc[i]['rsi'] > 65 and df.iloc[i]['close'] > df.iloc[i]['ema21']:
                signals.append({
                    'timestamp': current_time,
                    'type': 'entry',
                    'direction': 'short',
                    'price': df.iloc[i]['close'],
                    'reason': f'Tín hiệu SHORT tối ưu giờ: {hour}h - RSI: {df.iloc[i]["rsi"]:.2f}'
                })
        
        # Kiểm tra điều kiện LONG trong giờ đóng cửa
        elif 22 <= hour <= 23 or 0 <= hour <= 1:
            # Điều kiện kỹ thuật bổ sung
            if df.iloc[i]['rsi'] < 45 and df.iloc[i]['close'] < df.iloc[i]['ema21']:
                signals.append({
                    'timestamp': current_time,
                    'type': 'entry',
                    'direction': 'long',
                    'price': df.iloc[i]['close'],
                    'reason': f'Tín hiệu LONG tối ưu giờ: {hour}h - RSI: {df.iloc[i]["rsi"]:.2f}'
                })
    
    return signals

def improved_rsi_strategy(data, symbol):
    """
    Chiến lược RSI cải tiến
    
    Args:
        data (pd.DataFrame): Dữ liệu giá với các chỉ báo
        symbol (str): Cặp tiền
    
    Returns:
        list: Danh sách tín hiệu
    """
    df = data.copy()
    signals = []
    
    # In thông tin chỉ báo để debug
    logger.info(f"Giá trị RSI Min: {df['rsi'].min():.2f}, Max: {df['rsi'].max():.2f}")
    logger.info(f"Giá trị MACD Histogram Min: {df['macd_histogram'].min():.2f}, Max: {df['macd_histogram'].max():.2f}")
    
    for i in range(50, len(df)):
        # Điều kiện SHORT - Dùng chỉ mỗi điều kiện RSI để tạo nhiều tín hiệu hơn
        if df.iloc[i]['rsi'] > 55:  # Hạ ngưỡng xuống 55
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'type': 'entry',
                'direction': 'short',
                'price': df.iloc[i]['close'],
                'reason': f'RSI quá mua: {df.iloc[i]["rsi"]:.2f}'
            })
        
        # Điều kiện LONG - Dùng chỉ mỗi điều kiện RSI để tạo nhiều tín hiệu hơn
        elif df.iloc[i]['rsi'] < 45:  # Tăng ngưỡng lên 45
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'type': 'entry',
                'direction': 'long',
                'price': df.iloc[i]['close'],
                'reason': f'RSI quá bán: {df.iloc[i]["rsi"]:.2f}'
            })
    
    logger.info(f"Đã tạo {len(signals)} tín hiệu cho {symbol}")
    return signals

def backtest_strategy(data, signals, risk_percentage, initial_balance=10000):
    """
    Backtest chiến lược giao dịch
    
    Args:
        data (pd.DataFrame): Dữ liệu giá
        signals (list): Danh sách tín hiệu
        risk_percentage (float): Phần trăm rủi ro cho mỗi giao dịch
        initial_balance (float): Số dư ban đầu
    
    Returns:
        dict: Kết quả backtest
    """
    df = data.copy()
    balance = initial_balance
    positions = []
    trades = []
    
    # Ánh xạ tín hiệu vào dữ liệu
    signal_map = {}
    for signal in signals:
        signal_time = signal['timestamp']
        signal_map[signal_time] = signal
    
    for i in range(50, len(df) - 1):
        current_time = df.iloc[i]['timestamp']
        current_price = df.iloc[i]['close']
        next_price = df.iloc[i+1]['close']
        
        # Kiểm tra tín hiệu
        if current_time in signal_map and signal_map[current_time]['type'] == 'entry':
            signal = signal_map[current_time]
            
            # Tính kích thước vị thế dựa trên rủi ro
            position_size = (balance * (risk_percentage / 100)) / current_price
            
            # Giá stop loss và take profit
            sl_percentage = 0.05  # 5%
            tp_percentage = 0.15  # 15%
            
            if signal['direction'] == 'long':
                stop_loss = current_price * (1 - sl_percentage)
                take_profit = current_price * (1 + tp_percentage)
            else:  # short
                stop_loss = current_price * (1 + sl_percentage)
                take_profit = current_price * (1 - tp_percentage)
            
            # Mở vị thế
            position = {
                'entry_time': current_time,
                'direction': signal['direction'],
                'entry_price': current_price,
                'size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': signal['reason'] if 'reason' in signal else None
            }
            
            positions.append(position)
        
        # Kiểm tra các vị thế hiện có
        for pos in positions[:]:  # Sao chép danh sách để có thể xóa trong khi lặp
            # Kiểm tra stop loss
            if (pos['direction'] == 'long' and next_price <= pos['stop_loss']) or \
               (pos['direction'] == 'short' and next_price >= pos['stop_loss']):
                # Tính lợi nhuận
                if pos['direction'] == 'long':
                    profit = pos['size'] * (pos['stop_loss'] - pos['entry_price'])
                else:  # short
                    profit = pos['size'] * (pos['entry_price'] - pos['stop_loss'])
                
                # Cập nhật số dư
                balance += profit
                
                # Ghi nhận giao dịch
                trade = {
                    'entry_time': pos['entry_time'],
                    'exit_time': df.iloc[i+1]['timestamp'],
                    'direction': pos['direction'],
                    'entry_price': pos['entry_price'],
                    'exit_price': pos['stop_loss'],
                    'size': pos['size'],
                    'profit': profit,
                    'profit_percentage': (profit / (pos['entry_price'] * pos['size'])) * 100,
                    'exit_reason': 'stop_loss',
                    'reason': pos['reason']
                }
                
                trades.append(trade)
                positions.remove(pos)
            
            # Kiểm tra take profit
            elif (pos['direction'] == 'long' and next_price >= pos['take_profit']) or \
                 (pos['direction'] == 'short' and next_price <= pos['take_profit']):
                # Tính lợi nhuận
                if pos['direction'] == 'long':
                    profit = pos['size'] * (pos['take_profit'] - pos['entry_price'])
                else:  # short
                    profit = pos['size'] * (pos['entry_price'] - pos['take_profit'])
                
                # Cập nhật số dư
                balance += profit
                
                # Ghi nhận giao dịch
                trade = {
                    'entry_time': pos['entry_time'],
                    'exit_time': df.iloc[i+1]['timestamp'],
                    'direction': pos['direction'],
                    'entry_price': pos['entry_price'],
                    'exit_price': pos['take_profit'],
                    'size': pos['size'],
                    'profit': profit,
                    'profit_percentage': (profit / (pos['entry_price'] * pos['size'])) * 100,
                    'exit_reason': 'take_profit',
                    'reason': pos['reason']
                }
                
                trades.append(trade)
                positions.remove(pos)
    
    # Đóng các vị thế còn lại
    last_price = df.iloc[-1]['close']
    for pos in positions:
        if pos['direction'] == 'long':
            profit = pos['size'] * (last_price - pos['entry_price'])
        else:  # short
            profit = pos['size'] * (pos['entry_price'] - last_price)
        
        # Cập nhật số dư
        balance += profit
        
        # Ghi nhận giao dịch
        trade = {
            'entry_time': pos['entry_time'],
            'exit_time': df.iloc[-1]['timestamp'],
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': last_price,
            'size': pos['size'],
            'profit': profit,
            'profit_percentage': (profit / (pos['entry_price'] * pos['size'])) * 100,
            'exit_reason': 'end_of_test',
            'reason': pos['reason']
        }
        
        trades.append(trade)
    
    # Tính toán kết quả
    total_trades = len(trades)
    winning_trades = [t for t in trades if t['profit'] > 0]
    losing_trades = [t for t in trades if t['profit'] <= 0]
    
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    
    win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
    
    total_profit = sum([t['profit'] for t in trades])
    profit_percentage = (total_profit / initial_balance) * 100
    
    avg_win = sum([t['profit'] for t in winning_trades]) / win_count if win_count > 0 else 0
    avg_loss = sum([t['profit'] for t in losing_trades]) / loss_count if loss_count > 0 else 0
    
    # Tính Profit Factor
    total_gain = sum([t['profit'] for t in winning_trades]) if winning_trades else 0
    total_loss = sum([abs(t['profit']) for t in losing_trades]) if losing_trades else 0
    profit_factor = total_gain / total_loss if total_loss != 0 else float('inf')
    
    # Tính Drawdown
    equity_curve = [initial_balance]
    peak = initial_balance
    drawdowns = []
    
    for trade in trades:
        equity_curve.append(equity_curve[-1] + trade['profit'])
        if equity_curve[-1] > peak:
            peak = equity_curve[-1]
        drawdown = (peak - equity_curve[-1]) / peak * 100 if peak > 0 else 0
        drawdowns.append(drawdown)
    
    max_drawdown = max(drawdowns) if drawdowns else 0
    
    return {
        'initial_balance': initial_balance,
        'final_balance': balance,
        'total_profit': total_profit,
        'profit_percentage': profit_percentage,
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'trades': trades,
        'equity_curve': equity_curve
    }

def create_equity_chart(results, output_path):
    """
    Tạo biểu đồ vốn
    
    Args:
        results (dict): Kết quả backtest
        output_path (str): Đường dẫn lưu biểu đồ
    """
    equity_curve = results['equity_curve']
    trades = results['trades']
    
    plt.figure(figsize=(12, 8))
    
    # Vẽ đường equity
    plt.plot(range(len(equity_curve)), equity_curve, 'b-', label='Equity Curve')
    
    # Đánh dấu các giao dịch
    entry_indices = [0]  # Chỉ số ban đầu
    exit_indices = []
    profits = []
    
    for i, trade in enumerate(trades):
        entry_indices.append(i + 1)  # +1 vì đã có initial_balance ở đầu
        exit_indices.append(i + 1)
        profits.append(trade['profit'])
    
    # Vẽ các giao dịch thắng và thua
    for i, (idx, profit) in enumerate(zip(exit_indices, profits)):
        if profit > 0:
            plt.plot(idx, equity_curve[idx], 'go', markersize=8)  # Giao dịch thắng (màu xanh)
        else:
            plt.plot(idx, equity_curve[idx], 'ro', markersize=8)  # Giao dịch thua (màu đỏ)
    
    # Thêm thông tin hiệu suất
    info_text = (
        f"Số dư ban đầu: ${results['initial_balance']:,.2f}\n"
        f"Số dư cuối: ${results['final_balance']:,.2f}\n"
        f"Lợi nhuận: ${results['total_profit']:,.2f} ({results['profit_percentage']:.2f}%)\n"
        f"Tổng giao dịch: {results['total_trades']}\n"
        f"Thắng/Thua: {results['winning_trades']}/{results['losing_trades']}\n"
        f"Tỷ lệ thắng: {results['win_rate']:.2f}%\n"
        f"Profit Factor: {results['profit_factor']:.2f}\n"
        f"Max Drawdown: {results['max_drawdown']:.2f}%"
    )
    
    plt.text(0.02, 0.02, info_text, transform=plt.gca().transAxes,
             bbox=dict(facecolor='white', alpha=0.8), fontsize=10, verticalalignment='bottom')
    
    plt.title('Biểu đồ vốn trong quá trình backtest')
    plt.xlabel('Số giao dịch')
    plt.ylabel('Số dư ($)')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(output_path)
    logger.info(f"Đã tạo biểu đồ vốn: {output_path}")

def create_trade_distribution_chart(results, output_path):
    """
    Tạo biểu đồ phân bố giao dịch
    
    Args:
        results (dict): Kết quả backtest
        output_path (str): Đường dẫn lưu biểu đồ
    """
    trades = results['trades']
    
    if not trades:
        logger.warning("Không có giao dịch để tạo biểu đồ phân bố")
        return
    
    plt.figure(figsize=(16, 12))
    
    # 1. Phân bố lợi nhuận của từng giao dịch
    plt.subplot(2, 2, 1)
    profits = [t['profit_percentage'] for t in trades]
    plt.hist(profits, bins=20, color='skyblue', edgecolor='black')
    plt.title('Phân bố lợi nhuận (%) của các giao dịch')
    plt.xlabel('Lợi nhuận (%)')
    plt.ylabel('Số lượng giao dịch')
    plt.grid(True, alpha=0.3)
    
    # 2. Phân tích theo hướng giao dịch (long/short)
    plt.subplot(2, 2, 2)
    long_trades = [t for t in trades if t['direction'] == 'long']
    short_trades = [t for t in trades if t['direction'] == 'short']
    
    long_win = len([t for t in long_trades if t['profit'] > 0])
    long_loss = len(long_trades) - long_win
    short_win = len([t for t in short_trades if t['profit'] > 0])
    short_loss = len(short_trades) - short_win
    
    directions = ['Long', 'Short']
    win_counts = [long_win, short_win]
    loss_counts = [long_loss, short_loss]
    
    x = np.arange(len(directions))
    width = 0.35
    
    plt.bar(x - width/2, win_counts, width, label='Thắng', color='green', alpha=0.7)
    plt.bar(x + width/2, loss_counts, width, label='Thua', color='red', alpha=0.7)
    
    plt.xlabel('Hướng giao dịch')
    plt.ylabel('Số lượng giao dịch')
    plt.title('Phân tích giao dịch theo hướng')
    plt.xticks(x, directions)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 3. Phân tích theo lý do thoát lệnh
    plt.subplot(2, 2, 3)
    exit_reasons = [t['exit_reason'] for t in trades]
    reason_counts = {}
    for reason in exit_reasons:
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    
    plt.pie(reason_counts.values(), labels=reason_counts.keys(), autopct='%1.1f%%', 
            colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'], startangle=90)
    plt.axis('equal')
    plt.title('Phân bố lý do thoát lệnh')
    
    # 4. Phân tích theo giờ trong ngày
    plt.subplot(2, 2, 4)
    trade_hours = [t['entry_time'].hour for t in trades]
    plt.hist(trade_hours, bins=24, range=(0, 24), color='purple', alpha=0.7, edgecolor='black')
    plt.title('Phân bố giao dịch theo giờ trong ngày')
    plt.xlabel('Giờ (0-23)')
    plt.ylabel('Số lượng giao dịch')
    plt.xticks(range(0, 24, 2))
    plt.grid(True, alpha=0.3)
    
    # Tiêu đề chung và lưu biểu đồ
    plt.suptitle('Phân tích chi tiết các giao dịch', fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    plt.savefig(output_path)
    logger.info(f"Đã tạo biểu đồ phân bố giao dịch: {output_path}")

def run_test(symbol, timeframe, strategy_name, risk_level, days=30):
    """
    Chạy backtest cho một cặp tiền và chiến lược
    
    Args:
        symbol (str): Cặp tiền
        timeframe (str): Khung thời gian
        strategy_name (str): Tên chiến lược
        risk_level (float): Mức rủi ro (%)
        days (int): Số ngày dữ liệu
    
    Returns:
        dict: Kết quả backtest
    """
    logger.info(f"Bắt đầu backtest {strategy_name} cho {symbol} {timeframe} với mức rủi ro {risk_level}%")
    
    # Tải dữ liệu
    data = load_data(symbol, timeframe, days)
    if data is None or len(data) < 100:
        logger.error(f"Không đủ dữ liệu để backtest {symbol} {timeframe}")
        return None
    
    # Tính toán chỉ báo
    data = calculate_indicators(data)
    
    # Tạo tín hiệu
    signals = []
    if strategy_name == 'time_optimized_strategy':
        signals = time_optimized_strategy(data, symbol)
    elif strategy_name == 'improved_rsi_strategy':
        signals = improved_rsi_strategy(data, symbol)
    else:
        logger.error(f"Không tìm thấy chiến lược {strategy_name}")
        return None
    
    if not signals:
        logger.warning(f"Không có tín hiệu nào được tạo cho {symbol} {timeframe} với chiến lược {strategy_name}")
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'strategy': strategy_name,
            'risk_level': risk_level,
            'total_trades': 0,
            'signals': []
        }
    
    # Chạy backtest
    results = backtest_strategy(data, signals, risk_level)
    
    # Bổ sung thông tin
    results['symbol'] = symbol
    results['timeframe'] = timeframe
    results['strategy'] = strategy_name
    results['risk_level'] = risk_level
    results['signals'] = signals
    
    # Tạo biểu đồ
    chart_file = f"test_charts/{strategy_name}_{symbol}_{timeframe}_risk{risk_level:.1f}.png"
    create_equity_chart(results, chart_file)
    
    distribution_chart_file = f"test_charts/{strategy_name}_{symbol}_{timeframe}_risk{risk_level:.1f}_distribution.png"
    create_trade_distribution_chart(results, distribution_chart_file)
    
    # Lưu kết quả
    result_file = f"test_results/{strategy_name}_{symbol}_{timeframe}_risk{risk_level:.1f}.json"
    
    with open(result_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Đã lưu kết quả backtest vào {result_file}")
    
    # In kết quả tóm tắt
    logger.info(f"Kết quả backtest {strategy_name} cho {symbol} {timeframe} với mức rủi ro {risk_level}%:")
    logger.info(f"  Tổng giao dịch: {results['total_trades']}")
    logger.info(f"  Tỷ lệ thắng: {results['win_rate']:.2f}%")
    logger.info(f"  Lợi nhuận: {results['profit_percentage']:.2f}%")
    logger.info(f"  Profit Factor: {results['profit_factor']:.2f}")
    logger.info(f"  Max Drawdown: {results['max_drawdown']:.2f}%")
    
    return results

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    parser = argparse.ArgumentParser(description='Chạy backtest nhanh với dữ liệu thực từ Binance')
    
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp tiền (mặc định: BTCUSDT)')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--strategy', type=str, default='time_optimized_strategy', 
                        choices=['time_optimized_strategy', 'improved_rsi_strategy'],
                        help='Chiến lược giao dịch (mặc định: time_optimized_strategy)')
    parser.add_argument('--risk', type=float, default=5.0, help='Mức rủi ro % (mặc định: 5.0)')
    parser.add_argument('--days', type=int, default=30, help='Số ngày dữ liệu (mặc định: 30)')
    
    return parser.parse_args()

def main():
    """Hàm chính"""
    args = parse_arguments()
    
    run_test(args.symbol, args.timeframe, args.strategy, args.risk, args.days)

if __name__ == "__main__":
    main()