#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kiểm tra cơ bản thuật toán phát hiện thị trường đi ngang và tạo tín hiệu
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import traceback
from binance.client import Client
import json

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('basic_test')

def get_binance_data(symbol, interval='1d', days=90):
    """Lấy dữ liệu từ Binance API"""
    try:
        # Lấy API key và secret
        import os
        api_key = os.environ.get('BINANCE_API_KEY', '')
        api_secret = os.environ.get('BINANCE_API_SECRET', '')
        
        client = Client(api_key, api_secret)
        
        # Chuyển đổi symbol
        if '-USD' in symbol:
            symbol = symbol.replace('-USD', 'USDT')
        
        logger.info(f"Tải dữ liệu {symbol} từ Binance ({interval}, {days} ngày)")
        
        # Định dạng thời gian
        from datetime import datetime, timedelta
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
    """Tính các chỉ báo cơ bản"""
    try:
        df = data.copy()
        
        # Tính MA
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['sma50'] = df['Close'].rolling(window=50).mean()
        df['sma100'] = df['Close'].rolling(window=100).mean()
        
        # Tính EMA
        df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # Tính RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính ATR
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Tính Bollinger Bands
        df['stddev_20'] = df['Close'].rolling(window=20).std()
        df['bollinger_upper'] = df['sma20'] + (df['stddev_20'] * 2)
        df['bollinger_lower'] = df['sma20'] - (df['stddev_20'] * 2)
        
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi tính chỉ báo: {e}")
        logger.error(traceback.format_exc())
        return None

def detect_sideways_market(data):
    """Phát hiện thị trường đi ngang"""
    try:
        df = data.copy()
        
        # Tính ATR Volatility
        df['atr_volatility'] = (df['atr'] / df['Close']) * 100
        
        # Tính Price Range
        df['price_range'] = df['High'].rolling(20).max() - df['Low'].rolling(20).min()
        df['price_range_pct'] = (df['price_range'] / df['Low'].rolling(20).min()) * 100
        
        # Tính Bollinger Width
        df['bollinger_width'] = (df['bollinger_upper'] - df['bollinger_lower']) / df['sma20'] * 100
        df['bollinger_width_avg'] = df['bollinger_width'].rolling(30).mean()
        
        # Tính ADX (đơn giản hóa)
        df['plus_dm'] = np.where(
            (df['High'] - df['High'].shift(1)) > (df['Low'].shift(1) - df['Low']),
            np.maximum(df['High'] - df['High'].shift(1), 0),
            0
        )
        df['minus_dm'] = np.where(
            (df['Low'].shift(1) - df['Low']) > (df['High'] - df['High'].shift(1)),
            np.maximum(df['Low'].shift(1) - df['Low'], 0),
            0
        )
        
        # Tính True Range
        df['tr'] = df['atr'] * 14  # Đơn giản hóa
        
        # Tính +DI và -DI
        df['plus_di'] = 100 * (df['plus_dm'].rolling(14).sum() / df['tr'].rolling(14).sum())
        df['minus_di'] = 100 * (df['minus_dm'].rolling(14).sum() / df['tr'].rolling(14).sum())
        
        # Tính DX và ADX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Điều kiện thị trường đi ngang
        price_range_threshold = 5.0
        atr_volatility_threshold = 2.0
        
        df['is_sideways'] = (
            (df['price_range_pct'] < price_range_threshold) & 
            (df['atr_volatility'] < atr_volatility_threshold) &
            (df['bollinger_width'] < df['bollinger_width_avg']) &
            (df['adx'] < 25)
        )
        
        # Xác định các giai đoạn thị trường đi ngang kéo dài
        sideways_periods = []
        current_sideways = {'start': None, 'end': None, 'duration': 0}
        min_sideways_duration = 5
        
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
        return None, []

def generate_ma_signals(data):
    """Tạo tín hiệu từ MA crossover"""
    try:
        signals = []
        
        ma_pairs = [
            ('sma20', 'sma50'),
            ('ema9', 'ema21')
        ]
        
        for fast_ma, slow_ma in ma_pairs:
            # Kiểm tra các cột cần thiết
            if fast_ma not in data.columns or slow_ma not in data.columns:
                continue
            
            # Tìm điểm giao cắt
            for i in range(1, len(data)):
                # Lấy giá trị hiện tại và trước đó
                prev_fast = data[fast_ma].iloc[i-1]
                prev_slow = data[slow_ma].iloc[i-1]
                curr_fast = data[fast_ma].iloc[i]
                curr_slow = data[slow_ma].iloc[i]
                
                # Kiểm tra điều kiện cắt lên trên (LONG)
                if prev_fast <= prev_slow and curr_fast > curr_slow:
                    # Tạo tín hiệu LONG
                    entry_date = data.index[i]
                    entry_price = data['Close'].iloc[i]
                    
                    signals.append({
                        'date': entry_date,
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'signal_source': f'{fast_ma}_{slow_ma}_crossover',
                        'sideways_period': False
                    })
                
                # Kiểm tra điều kiện cắt xuống dưới (SHORT)
                elif prev_fast >= prev_slow and curr_fast < curr_slow:
                    # Tạo tín hiệu SHORT
                    entry_date = data.index[i]
                    entry_price = data['Close'].iloc[i]
                    
                    signals.append({
                        'date': entry_date,
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'signal_source': f'{fast_ma}_{slow_ma}_crossover',
                        'sideways_period': False
                    })
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu MA crossover")
        return signals
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo tín hiệu MA crossover: {e}")
        logger.error(traceback.format_exc())
        return []

def generate_sideways_signals(data, sideways_periods):
    """Tạo tín hiệu từ thị trường đi ngang"""
    try:
        signals = []
        
        for period in sideways_periods:
            start_idx = period['start_idx']
            end_idx = period['end_idx']
            
            # Lấy dữ liệu trong giai đoạn sideways
            period_data = data.iloc[start_idx:end_idx+1].copy()
            
            # Tín hiệu khi giá chạm cận dưới Bollinger
            period_data['lower_band_signal'] = (
                (period_data['Close'] <= period_data['bollinger_lower']) & 
                (period_data['Close'].shift(1) > period_data['bollinger_lower'].shift(1))
            )
            
            # Tín hiệu khi giá chạm cận trên Bollinger
            period_data['upper_band_signal'] = (
                (period_data['Close'] >= period_data['bollinger_upper']) & 
                (period_data['Close'].shift(1) < period_data['bollinger_upper'].shift(1))
            )
            
            # Thêm điều kiện RSI
            if 'rsi' in period_data.columns:
                period_data['lower_band_signal'] = (
                    period_data['lower_band_signal'] & 
                    (period_data['rsi'] < 40)
                )
                
                period_data['upper_band_signal'] = (
                    period_data['upper_band_signal'] & 
                    (period_data['rsi'] > 60)
                )
            
            # Xử lý các tín hiệu
            for i, (date, row) in enumerate(period_data.iterrows()):
                # Bỏ qua vị trí đầu và cuối
                if i < 2 or i >= len(period_data) - 2:
                    continue
                
                if pd.notna(row['lower_band_signal']) and row['lower_band_signal']:
                    # Tín hiệu LONG khi giá chạm cận dưới
                    entry_price = row['Close']
                    
                    signals.append({
                        'date': date,
                        'type': 'LONG',
                        'entry_price': entry_price,
                        'signal_source': 'bollinger_lower',
                        'sideways_period': True
                    })
                
                if pd.notna(row['upper_band_signal']) and row['upper_band_signal']:
                    # Tín hiệu SHORT khi giá chạm cận trên
                    entry_price = row['Close']
                    
                    signals.append({
                        'date': date,
                        'type': 'SHORT',
                        'entry_price': entry_price,
                        'signal_source': 'bollinger_upper',
                        'sideways_period': True
                    })
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu sideways market")
        return signals
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo tín hiệu sideways market: {e}")
        logger.error(traceback.format_exc())
        return []

def apply_stop_loss_take_profit(signals, data):
    """Áp dụng stop loss và take profit cho các tín hiệu"""
    try:
        for signal in signals:
            idx = data.index.get_loc(signal['date'])
            current_row = data.iloc[idx]
            
            # Lấy giá trị ATR
            atr = current_row['atr']
            
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
        
        logger.info(f"Đã áp dụng stop loss và take profit cho {len(signals)} tín hiệu")
        return signals
    
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng stop loss và take profit: {e}")
        logger.error(traceback.format_exc())
        return signals

def simulate_trades(signals, data, initial_balance=10000.0):
    """Mô phỏng giao dịch với partial take profit"""
    try:
        trades = []
        balance = initial_balance
        
        # Cho mỗi tín hiệu giao dịch
        for signal in signals:
            # Lấy vị trí của tín hiệu trong dữ liệu
            signal_idx = data.index.get_loc(signal['date'])
            
            # Bỏ qua tín hiệu quá gần cuối dữ liệu
            if signal_idx >= len(data) - 2:
                continue
            
            # Tính kích thước vị thế (đơn giản: 10% số dư)
            position_size = balance * 0.1
            leverage = 3
            
            # Thông tin giao dịch
            trade = {
                'entry_date': signal['date'],
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'type': signal['type'],
                'position_size': position_size,
                'leverage': leverage,
                'signal_source': signal['signal_source'],
                'sideways_period': signal.get('sideways_period', False),
                'partial_exits': []
            }
            
            # Mô phỏng giao dịch
            active_position = True
            remaining_size = position_size
            
            # Dữ liệu sau tín hiệu
            future_data = data.iloc[signal_idx+1:]
            exit_price = None
            exit_date = None
            exit_reason = None
            total_profit = 0
            
            # Di chuyển stop loss lên mức hòa vốn sau lần chốt lời đầu tiên
            stop_loss_moved_to_breakeven = False
            
            # Xử lý từng ngày sau tín hiệu
            for future_idx, future_row in future_data.iterrows():
                if not active_position:
                    break
                
                current_price = future_row['Close']
                
                # Kiểm tra partial take profit trước
                if 'partial_take_profits' in signal:
                    for i, tp in enumerate(signal['partial_take_profits']):
                        if tp['triggered']:
                            continue
                            
                        # Kiểm tra xem giá đã chạm mức take profit chưa
                        if (signal['type'] == 'LONG' and current_price >= tp['level']) or \
                           (signal['type'] == 'SHORT' and current_price <= tp['level']):
                            
                            # Tính kích thước và lợi nhuận cho phần này
                            tp_size = position_size * (tp['percentage'] / 100)
                            
                            if signal['type'] == 'LONG':
                                partial_profit = tp_size * leverage * (tp['level'] - signal['entry_price']) / signal['entry_price']
                            else:  # SHORT
                                partial_profit = tp_size * leverage * (signal['entry_price'] - tp['level']) / signal['entry_price']
                            
                            # Cập nhật kích thước vị thế còn lại
                            remaining_size -= tp_size
                            
                            # Cập nhật số dư
                            balance += partial_profit
                            total_profit += partial_profit
                            
                            # Đánh dấu đã kích hoạt
                            signal['partial_take_profits'][i]['triggered'] = True
                            
                            # Thêm vào danh sách chốt lời từng phần
                            trade['partial_exits'].append({
                                'date': future_idx,
                                'price': tp['level'],
                                'size': tp_size,
                                'profit': partial_profit
                            })
                            
                            logger.info(f"Chốt {tp['percentage']}% vị thế tại ${tp['level']:.2f}, lợi nhuận: ${partial_profit:.2f}")
                            
                            # Di chuyển stop loss lên mức hòa vốn sau lần chốt lời đầu tiên
                            if i == 0 and not stop_loss_moved_to_breakeven:
                                signal['stop_loss'] = signal['entry_price']
                                stop_loss_moved_to_breakeven = True
                                logger.info(f"Di chuyển stop loss lên mức hòa vốn: ${signal['entry_price']:.2f}")
                            
                            # Kiểm tra đã chốt hết chưa
                            if remaining_size < 0.001:
                                active_position = False
                                exit_price = tp['level']
                                exit_date = future_idx
                                exit_reason = 'full_take_profit'
                                break
                
                # Kiểm tra stop loss
                if active_position:
                    if (signal['type'] == 'LONG' and current_price <= signal['stop_loss']) or \
                       (signal['type'] == 'SHORT' and current_price >= signal['stop_loss']):
                        
                        # Tính lợi nhuận cho phần còn lại
                        if signal['type'] == 'LONG':
                            remaining_profit = remaining_size * leverage * (signal['stop_loss'] - signal['entry_price']) / signal['entry_price']
                        else:  # SHORT
                            remaining_profit = remaining_size * leverage * (signal['entry_price'] - signal['stop_loss']) / signal['entry_price']
                        
                        # Cập nhật số dư và tổng lợi nhuận
                        balance += remaining_profit
                        total_profit += remaining_profit
                        
                        # Đóng vị thế
                        active_position = False
                        exit_price = signal['stop_loss']
                        exit_date = future_idx
                        exit_reason = 'stop_loss'
                        
                # Kiểm tra take profit cuối cùng
                if active_position and 'partial_take_profits' not in signal:
                    if (signal['type'] == 'LONG' and current_price >= signal['take_profit']) or \
                       (signal['type'] == 'SHORT' and current_price <= signal['take_profit']):
                        
                        # Tính lợi nhuận
                        if signal['type'] == 'LONG':
                            profit = position_size * leverage * (signal['take_profit'] - signal['entry_price']) / signal['entry_price']
                        else:  # SHORT
                            profit = position_size * leverage * (signal['entry_price'] - signal['take_profit']) / signal['entry_price']
                        
                        # Cập nhật số dư và tổng lợi nhuận
                        balance += profit
                        total_profit = profit
                        
                        # Đóng vị thế
                        active_position = False
                        exit_price = signal['take_profit']
                        exit_date = future_idx
                        exit_reason = 'take_profit'
            
            # Nếu vẫn còn vị thế và đã hết dữ liệu, đóng ở giá cuối cùng
            if active_position:
                last_price = future_data['Close'].iloc[-1]
                
                # Tính lợi nhuận cho phần còn lại
                if signal['type'] == 'LONG':
                    remaining_profit = remaining_size * leverage * (last_price - signal['entry_price']) / signal['entry_price']
                else:  # SHORT
                    remaining_profit = remaining_size * leverage * (signal['entry_price'] - last_price) / signal['entry_price']
                
                # Cập nhật số dư và tổng lợi nhuận
                balance += remaining_profit
                total_profit += remaining_profit
                
                exit_price = last_price
                exit_date = future_data.index[-1]
                exit_reason = 'end_of_data'
            
            # Hoàn thiện thông tin giao dịch
            trade['exit_date'] = exit_date
            trade['exit_price'] = exit_price
            trade['exit_reason'] = exit_reason
            trade['profit'] = total_profit
            trade['profit_pct'] = (total_profit / (position_size * leverage)) * 100
            trade['balance_after'] = balance
            
            trades.append(trade)
            
            logger.info(f"Giao dịch {signal['type']} từ {signal['entry_price']:.2f} đến {exit_price:.2f}")
            logger.info(f"Lý do đóng: {exit_reason}, Lợi nhuận: ${total_profit:.2f} ({trade['profit_pct']:.2f}%)")
            logger.info(f"Số dư mới: ${balance:.2f}")
        
        # Tính thống kê
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['profit'] > 0)
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        profit = balance - initial_balance
        profit_pct = (profit / initial_balance) * 100
        
        logger.info(f"\n=== KẾT QUẢ BACKTEST ===")
        logger.info(f"Số giao dịch: {total_trades}")
        logger.info(f"Giao dịch thắng/thua: {winning_trades}/{losing_trades}")
        logger.info(f"Tỷ lệ thắng: {win_rate:.2f}%")
        logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
        logger.info(f"Số dư cuối cùng: ${balance:.2f}")
        logger.info(f"Tổng lợi nhuận: ${profit:.2f} ({profit_pct:.2f}%)")
        
        # Tạo summary
        summary = {
            'initial_balance': initial_balance,
            'final_balance': balance,
            'total_profit': profit,
            'total_profit_pct': profit_pct,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate
        }
        
        return trades, summary
    
    except Exception as e:
        logger.error(f"Lỗi khi mô phỏng giao dịch: {e}")
        logger.error(traceback.format_exc())
        return [], {'error': str(e)}

def run_test():
    """Chạy kiểm tra tổng thể"""
    try:
        # Lấy dữ liệu từ Binance
        symbol = 'BTC-USD'
        data = get_binance_data(symbol, interval='1d', days=90)
        
        if data is None:
            logger.error("Không thể lấy dữ liệu, dừng test")
            return
        
        # Tính các chỉ báo
        data = calculate_indicators(data)
        
        if data is None:
            logger.error("Lỗi khi tính chỉ báo, dừng test")
            return
        
        # Phát hiện thị trường đi ngang
        processed_data, sideways_periods = detect_sideways_market(data)
        
        if processed_data is None:
            logger.error("Lỗi khi phát hiện thị trường đi ngang, dừng test")
            return
        
        # Tạo tín hiệu từ MA crossover
        ma_signals = generate_ma_signals(processed_data)
        
        # Tạo tín hiệu từ thị trường đi ngang
        sideways_signals = generate_sideways_signals(processed_data, sideways_periods)
        
        # Kết hợp và sắp xếp tín hiệu
        all_signals = ma_signals + sideways_signals
        all_signals.sort(key=lambda x: x['date'])
        
        # Áp dụng stop loss và take profit
        all_signals = apply_stop_loss_take_profit(all_signals, processed_data)
        
        # Mô phỏng giao dịch
        trades, summary = simulate_trades(all_signals, processed_data)
        
        # Lưu kết quả
        results = {
            'symbol': symbol,
            'period': '3 months',
            'ma_signals': len(ma_signals),
            'sideways_signals': len(sideways_signals),
            'total_signals': len(all_signals),
            'total_trades': len(trades),
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(f'basic_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(results, f, indent=4, default=str)
        
        logger.info(f"Đã lưu kết quả test vào file")
        
        return results
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"Bắt đầu kiểm tra cơ bản lúc: {start_time}")
    
    results = run_test()
    
    end_time = datetime.now()
    logger.info(f"Kết thúc kiểm tra cơ bản lúc: {end_time}")
    logger.info(f"Tổng thời gian thực hiện: {end_time - start_time}")
