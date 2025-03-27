#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BACKTEST TOÀN DIỆN - TẤT CẢ 5 MỨC RỦI RO
----------------------------------------
Script này thực hiện backtest với đầy đủ 5 mức rủi ro:
- extremely_low
- low
- medium
- high
- extremely_high

Mục tiêu: Tìm ra cấu hình rủi ro tối ưu với tỷ lệ lợi nhuận/rủi ro cao nhất
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import traceback
from binance.client import Client

# Thiết lập logging
output_dir = 'full_risk_backtest_results'
os.makedirs(output_dir, exist_ok=True)
log_file = os.path.join(output_dir, f'full_risk_backtest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('full_risk_backtest')

# Cấu hình test
SYMBOLS = ['BTC-USD', 'ETH-USD']
TIMEFRAME = '1h'
TEST_PERIOD = 90  # Giảm xuống 90 ngày để chạy nhanh hơn

# 5 mức rủi ro đầy đủ
RISK_LEVELS = ['extremely_low', 'low', 'medium', 'high', 'extremely_high']

# Cấu hình cho mỗi mức rủi ro
RISK_CONFIGS = {
    'extremely_low': {
        'risk_per_trade': 1.0,
        'max_leverage': 2,
        'stop_loss_atr_multiplier': 2.0,
        'take_profit_atr_multiplier': 6.0,
        'trailing_stop_activation_pct': 1.5,
        'trailing_stop_callback_pct': 0.7
    },
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
    },
    'extremely_high': {
        'risk_per_trade': 10.0,
        'max_leverage': 20,
        'stop_loss_atr_multiplier': 0.7,
        'take_profit_atr_multiplier': 1.5,
        'trailing_stop_activation_pct': 0.3,
        'trailing_stop_callback_pct': 0.2
    }
}

def get_binance_data(symbol, interval='1h', days=90):
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
    """Tính toán các chỉ báo kỹ thuật"""
    try:
        df = data.copy()
        
        # === Chỉ báo xu hướng ===
        # Moving Averages
        df['sma5'] = df['Close'].rolling(window=5).mean()
        df['sma20'] = df['Close'].rolling(window=20).mean()
        df['sma50'] = df['Close'].rolling(window=50).mean()
        df['sma100'] = df['Close'].rolling(window=100).mean()
        
        df['ema9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
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
        
        # Loại bỏ dữ liệu NaN
        df = df.dropna()
        
        return df
        
    except Exception as e:
        logger.error(f"Lỗi khi tính chỉ báo: {e}")
        logger.error(traceback.format_exc())
        return None

def generate_signals(data):
    """Tạo tín hiệu giao dịch"""
    try:
        df = data.copy()
        signals = []
        
        # Tín hiệu EMA crossover (9 và 21)
        df['ema_cross'] = np.where(df['ema9'] > df['ema21'], 1, -1)
        df['ema_cross_change'] = df['ema_cross'].diff()
        
        # Tín hiệu LONG khi EMA 9 cắt lên trên EMA 21
        long_signals = df[df['ema_cross_change'] == 2].index
        
        for date in long_signals:
            idx = df.index.get_loc(date)
            if idx < len(df) - 1:  # Đảm bảo không phải là nến cuối cùng
                signals.append({
                    'date': date,
                    'type': 'LONG',
                    'entry_price': df['Close'].iloc[idx],
                    'index': idx,
                    'atr': df['atr'].iloc[idx]
                })
        
        # Tín hiệu SHORT khi EMA 9 cắt xuống dưới EMA 21
        short_signals = df[df['ema_cross_change'] == -2].index
        
        for date in short_signals:
            idx = df.index.get_loc(date)
            if idx < len(df) - 1:  # Đảm bảo không phải là nến cuối cùng
                signals.append({
                    'date': date,
                    'type': 'SHORT',
                    'entry_price': df['Close'].iloc[idx],
                    'index': idx,
                    'atr': df['atr'].iloc[idx]
                })
        
        # Tín hiệu Bollinger Band bounce
        # LONG khi giá chạm cận dưới Bollinger và RSI < 30
        for i in range(1, len(df) - 1):
            if (df['Close'].iloc[i] <= df['bb_lower'].iloc[i] and
                df['rsi'].iloc[i] < 30):
                signals.append({
                    'date': df.index[i],
                    'type': 'LONG',
                    'entry_price': df['Close'].iloc[i],
                    'index': i,
                    'atr': df['atr'].iloc[i],
                    'strategy': 'bb_bounce'
                })
        
        # SHORT khi giá chạm cận trên Bollinger và RSI > 70
        for i in range(1, len(df) - 1):
            if (df['Close'].iloc[i] >= df['bb_upper'].iloc[i] and
                df['rsi'].iloc[i] > 70):
                signals.append({
                    'date': df.index[i],
                    'type': 'SHORT',
                    'entry_price': df['Close'].iloc[i],
                    'index': i,
                    'atr': df['atr'].iloc[i],
                    'strategy': 'bb_bounce'
                })
                
        # Lọc tín hiệu quá gần nhau (ít nhất 5 nến)
        filtered_signals = []
        last_signal_idx = -20  # Khởi tạo với giá trị âm
        
        for signal in sorted(signals, key=lambda x: x['index']):
            if signal['index'] - last_signal_idx >= 5:
                filtered_signals.append(signal)
                last_signal_idx = signal['index']
        
        logger.info(f"Đã tạo {len(signals)} tín hiệu gốc, sau khi lọc còn {len(filtered_signals)} tín hiệu")
        return filtered_signals
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo tín hiệu: {e}")
        logger.error(traceback.format_exc())
        return []

def apply_risk_management(signals, risk_level, initial_balance=10000.0):
    """Áp dụng quản lý rủi ro cho tín hiệu"""
    try:
        # Lấy cấu hình rủi ro
        risk_config = RISK_CONFIGS.get(risk_level, RISK_CONFIGS['medium'])
        signals_with_risk = []
        
        for signal in signals:
            atr = signal['atr']
            entry_price = signal['entry_price']
            
            # Tính kích thước vị thế
            risk_percent = risk_config['risk_per_trade'] / 100
            position_size = initial_balance * risk_percent
            
            # Tính SL và TP dựa trên ATR
            if signal['type'] == 'LONG':
                stop_loss = entry_price - (atr * risk_config['stop_loss_atr_multiplier'])
                take_profit = entry_price + (atr * risk_config['take_profit_atr_multiplier'])
                
                # Thêm các mức chốt lời từng phần
                partial_take_profits = [
                    entry_price * (1 + 0.01),  # 1%
                    entry_price * (1 + 0.02),  # 2%
                    entry_price * (1 + 0.03),  # 3%
                    entry_price * (1 + 0.05)   # 5%
                ]
            else:  # SHORT
                stop_loss = entry_price + (atr * risk_config['stop_loss_atr_multiplier'])
                take_profit = entry_price - (atr * risk_config['take_profit_atr_multiplier'])
                
                # Thêm các mức chốt lời từng phần
                partial_take_profits = [
                    entry_price * (1 - 0.01),  # 1%
                    entry_price * (1 - 0.02),  # 2%
                    entry_price * (1 - 0.03),  # 3%
                    entry_price * (1 - 0.05)   # 5%
                ]
            
            # Thiết lập trailing stop
            trailing_activation = risk_config['trailing_stop_activation_pct']
            trailing_callback = risk_config['trailing_stop_callback_pct']
            
            # Tạo tín hiệu mới với thông tin quản lý rủi ro
            signal_with_risk = signal.copy()
            signal_with_risk.update({
                'risk_level': risk_level,
                'position_size': position_size,
                'leverage': risk_config['max_leverage'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'partial_take_profits': partial_take_profits,
                'trailing_activation_pct': trailing_activation,
                'trailing_callback_pct': trailing_callback
            })
            
            signals_with_risk.append(signal_with_risk)
        
        return signals_with_risk
        
    except Exception as e:
        logger.error(f"Lỗi khi áp dụng quản lý rủi ro: {e}")
        logger.error(traceback.format_exc())
        return signals

def simulate_trades(signals, data, initial_balance=10000.0):
    """Mô phỏng giao dịch"""
    try:
        df = data.copy()
        trades = []
        balance = initial_balance
        
        # Mô phỏng từng tín hiệu
        for signal in signals:
            entry_idx = signal['index']
            entry_price = signal['entry_price']
            signal_type = signal['type']
            
            # Khởi tạo thông tin giao dịch
            trade = {
                'entry_date': signal['date'],
                'entry_price': entry_price,
                'type': signal_type,
                'risk_level': signal['risk_level'],
                'position_size': signal['position_size'],
                'leverage': signal['leverage'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'partial_exits': [],
                'remaining_position': 1.0,  # 100% position còn lại
                'trail_activated': False,
                'trailing_stop': None
            }
            
            # Mô phỏng giao dịch từ ngày vào lệnh
            exit_found = False
            
            # Di chuyển Stop Loss lên breakeven sau khi chốt lời 25% đầu tiên
            stop_loss_moved = False
            
            # Mục tiêu trailing stop
            trailing_activation_pct = signal['trailing_activation_pct']
            trailing_callback_pct = signal['trailing_callback_pct']
            
            # Xử lý giao dịch theo từng nến
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
                    dollar_profit = trade['position_size'] * trade['leverage'] * profit_pct * trade['remaining_position']
                    
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
                
                # Kiểm tra partial take profits
                for tp_idx, tp_level in enumerate(signal['partial_take_profits']):
                    # Bỏ qua nếu đã chốt ở level này
                    if tp_idx < len(trade['partial_exits']):
                        continue
                        
                    # Kiểm tra nếu giá chạm mức chốt lời
                    if (signal_type == 'LONG' and df['High'].iloc[i] >= tp_level) or \
                       (signal_type == 'SHORT' and df['Low'].iloc[i] <= tp_level):
                        
                        # Kích thước phần chốt (25%)
                        portion = 0.25
                        portion_size = trade['position_size'] * portion
                        
                        # Tính lợi nhuận
                        if signal_type == 'LONG':
                            profit_pct = (tp_level - entry_price) / entry_price
                        else:
                            profit_pct = (entry_price - tp_level) / entry_price
                            
                        # Tính lợi nhuận dollar
                        dollar_profit = portion_size * trade['leverage'] * profit_pct
                        
                        # Thêm vào danh sách chốt từng phần
                        trade['partial_exits'].append({
                            'date': df.index[i],
                            'price': tp_level,
                            'portion': portion,
                            'profit_pct': profit_pct * 100,
                            'profit': dollar_profit
                        })
                        
                        # Cập nhật số dư và vị thế còn lại
                        balance += dollar_profit
                        trade['remaining_position'] -= portion
                        
                        # Di chuyển stop loss lên breakeven sau lần chốt lời đầu tiên
                        if tp_idx == 0 and not stop_loss_moved:
                            trade['stop_loss'] = entry_price
                            stop_loss_moved = True
                        
                        # Kích hoạt trailing stop sau lần chốt thứ 2
                        if tp_idx >= 1 and not trade['trail_activated']:
                            trade['trail_activated'] = True
                            
                            if signal_type == 'LONG':
                                trade['trailing_stop'] = current_price * (1 - trailing_callback_pct/100)
                            else:
                                trade['trailing_stop'] = current_price * (1 + trailing_callback_pct/100)
                        
                        # Kiểm tra nếu đã chốt hết vị thế
                        if trade['remaining_position'] <= 0.001:
                            trade['exit_date'] = df.index[i]
                            trade['exit_price'] = tp_level
                            trade['exit_reason'] = 'full_take_profit'
                            
                            # Tính tổng lợi nhuận
                            total_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                            trade['profit'] = total_profit
                            trade['profit_pct'] = sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits'])
                            trade['final_balance'] = balance
                            
                            exit_found = True
                            break
                
                if exit_found:
                    break
                    
                # Cập nhật trailing stop nếu đã kích hoạt
                if trade['trail_activated']:
                    if signal_type == 'LONG':
                        # Cập nhật trailing stop khi giá tăng
                        new_trailing_stop = current_price * (1 - trailing_callback_pct/100)
                        if new_trailing_stop > trade['trailing_stop']:
                            trade['trailing_stop'] = new_trailing_stop
                        
                        # Kiểm tra thoát vị thế nếu giá chạm trailing stop
                        if df['Low'].iloc[i] <= trade['trailing_stop']:
                            # Tính lợi nhuận cho phần còn lại
                            profit_pct = (trade['trailing_stop'] - entry_price) / entry_price
                            dollar_profit = trade['position_size'] * trade['leverage'] * profit_pct * trade['remaining_position']
                            
                            # Cập nhật giao dịch
                            trade['exit_date'] = df.index[i]
                            trade['exit_price'] = trade['trailing_stop']
                            trade['exit_reason'] = 'trailing_stop'
                            
                            # Tổng hợp lợi nhuận
                            partial_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                            total_profit = partial_profit + dollar_profit
                            
                            trade['profit'] = total_profit
                            trade['profit_pct'] = (sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits']) + 
                                                 profit_pct * 100 * trade['remaining_position'])
                            trade['final_balance'] = balance + dollar_profit
                            
                            # Cập nhật số dư
                            balance += dollar_profit
                            
                            exit_found = True
                            break
                    else:  # SHORT
                        # Cập nhật trailing stop khi giá giảm
                        new_trailing_stop = current_price * (1 + trailing_callback_pct/100)
                        if new_trailing_stop < trade['trailing_stop']:
                            trade['trailing_stop'] = new_trailing_stop
                        
                        # Kiểm tra thoát vị thế nếu giá chạm trailing stop
                        if df['High'].iloc[i] >= trade['trailing_stop']:
                            # Tính lợi nhuận cho phần còn lại
                            profit_pct = (entry_price - trade['trailing_stop']) / entry_price
                            dollar_profit = trade['position_size'] * trade['leverage'] * profit_pct * trade['remaining_position']
                            
                            # Cập nhật giao dịch
                            trade['exit_date'] = df.index[i]
                            trade['exit_price'] = trade['trailing_stop']
                            trade['exit_reason'] = 'trailing_stop'
                            
                            # Tổng hợp lợi nhuận
                            partial_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                            total_profit = partial_profit + dollar_profit
                            
                            trade['profit'] = total_profit
                            trade['profit_pct'] = (sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits']) + 
                                                 profit_pct * 100 * trade['remaining_position'])
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
                dollar_profit = trade['position_size'] * trade['leverage'] * profit_pct * trade['remaining_position']
                
                # Cập nhật giao dịch
                trade['exit_date'] = df.index[-1]
                trade['exit_price'] = last_price
                trade['exit_reason'] = 'end_of_data'
                
                # Tính tổng lợi nhuận
                partial_profit = sum(exit['profit'] for exit in trade['partial_exits'])
                total_profit = partial_profit + dollar_profit
                
                trade['profit'] = total_profit
                trade['profit_pct'] = (sum(exit['profit_pct'] * exit['portion'] for exit in trade['partial_exits']) + 
                                     profit_pct * 100 * trade['remaining_position'])
                trade['final_balance'] = balance + dollar_profit
                
                # Cập nhật số dư
                balance += dollar_profit
            
            # Thêm vào danh sách giao dịch
            trades.append(trade)
        
        # Tính toán các chỉ số thống kê
        if trades:
            # Số lượng giao dịch
            total_trades = len(trades)
            
            # Giao dịch thắng/thua
            winning_trades = sum(1 for t in trades if t['profit'] > 0)
            losing_trades = total_trades - winning_trades
            
            # Tỷ lệ thắng
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Lợi nhuận
            total_profit = sum(t['profit'] for t in trades)
            profit_pct = ((balance - initial_balance) / initial_balance * 100)
            
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
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'risk_level': signals[0]['risk_level'] if signals else 'unknown'
            }
            
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
            'error': str(e),
            'initial_balance': initial_balance,
            'final_balance': initial_balance
        }

def test_risk_level(symbol, risk_level, initial_balance=10000.0):
    """Test một mức rủi ro cụ thể"""
    try:
        # Lấy dữ liệu
        data = get_binance_data(symbol, interval=TIMEFRAME, days=TEST_PERIOD)
        
        if data is None or len(data) < 50:
            logger.error(f"Không đủ dữ liệu cho {symbol}")
            return {
                'symbol': symbol,
                'risk_level': risk_level,
                'error': 'Không đủ dữ liệu'
            }
        
        # Tính toán chỉ báo
        data_with_indicators = calculate_indicators(data)
        
        if data_with_indicators is None:
            logger.error(f"Lỗi khi tính chỉ báo cho {symbol}")
            return {
                'symbol': symbol,
                'risk_level': risk_level,
                'error': 'Lỗi khi tính chỉ báo'
            }
        
        # Tạo tín hiệu
        signals = generate_signals(data_with_indicators)
        
        if not signals:
            logger.warning(f"Không có tín hiệu giao dịch cho {symbol}")
            return {
                'symbol': symbol,
                'risk_level': risk_level,
                'initial_balance': initial_balance,
                'final_balance': initial_balance,
                'total_trades': 0,
                'profit': 0,
                'profit_pct': 0,
                'win_rate': 0
            }
        
        # Áp dụng quản lý rủi ro
        signals_with_risk = apply_risk_management(signals, risk_level, initial_balance)
        
        # Mô phỏng giao dịch
        trades, summary = simulate_trades(signals_with_risk, data_with_indicators, initial_balance)
        
        # Tạo kết quả
        result = {
            'symbol': symbol,
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
            'max_drawdown_pct': summary.get('max_drawdown_pct', 0)
        }
        
        # Lưu thông tin trades chi tiết
        trades_filename = f'{symbol.replace("-", "_")}_{risk_level}_trades.json'
        with open(os.path.join(output_dir, trades_filename), 'w') as f:
            json.dump([{k: str(v) if isinstance(v, pd.Timestamp) else v for k, v in t.items() 
                  if k not in ['partial_exits']} for t in trades], f, indent=4, default=str)
        
        logger.info(f"Kết quả cho {symbol} ({risk_level}): " + 
                  f"Trades: {result['total_trades']}, Win rate: {result['win_rate']:.2f}%, " + 
                  f"Profit: {result['total_profit_pct']:.2f}%, Drawdown: {result['max_drawdown_pct']:.2f}%")
        
        return result
    
    except Exception as e:
        logger.error(f"Lỗi khi test {symbol} với {risk_level} risk: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'symbol': symbol,
            'risk_level': risk_level,
            'error': str(e)
        }

def run_full_risk_test():
    """Chạy test với tất cả các mức rủi ro"""
    start_time = datetime.now()
    
    logger.info("=== BẮT ĐẦU BACKTEST ĐẦY ĐỦ 5 MỨC RỦI RO ===")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Timeframe: {TIMEFRAME}")
    logger.info(f"Risk levels: {RISK_LEVELS}")
    logger.info(f"Giai đoạn test: {TEST_PERIOD} ngày")
    
    all_results = {}
    
    # Test từng symbol
    for symbol in SYMBOLS:
        symbol_results = {}
        
        # Test từng mức rủi ro
        for risk_level in RISK_LEVELS:
            logger.info(f"Bắt đầu test {symbol} với mức rủi ro {risk_level}")
            
            result = test_risk_level(symbol, risk_level)
            symbol_results[risk_level] = result
        
        all_results[symbol] = symbol_results
    
    # Lưu tất cả kết quả
    with open(os.path.join(output_dir, 'all_risk_results.json'), 'w') as f:
        json.dump(all_results, f, indent=4, default=str)
    
    # Tạo báo cáo và biểu đồ
    create_report_and_charts(all_results)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=== KẾT THÚC BACKTEST ĐẦY ĐỦ 5 MỨC RỦI RO ===")
    logger.info(f"Thời gian thực hiện: {duration}")
    
    return all_results

def create_report_and_charts(all_results):
    """Tạo báo cáo và biểu đồ so sánh"""
    try:
        # Tạo báo cáo văn bản
        report_path = os.path.join(output_dir, 'full_risk_report.md')
        
        with open(report_path, 'w') as f:
            f.write("# BÁO CÁO BACKTEST ĐẦY ĐỦ 5 MỨC RỦI RO\n\n")
            f.write(f"Ngày thực hiện: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Timeframe: {TIMEFRAME}\n")
            f.write(f"Giai đoạn test: {TEST_PERIOD} ngày\n\n")
            
            # Bảng so sánh tổng thể
            f.write("## BẢNG SO SÁNH TỔNG THỂ\n\n")
            f.write("| Symbol | Mức rủi ro | Số giao dịch | Win rate | Lợi nhuận | Drawdown | Profit Factor |\n")
            f.write("|--------|-----------|-------------|----------|-----------|----------|---------------|\n")
            
            for symbol, symbol_data in all_results.items():
                for risk_level, result in symbol_data.items():
                    if 'error' in result:
                        f.write(f"| {symbol} | {risk_level} | - | - | - | - | - | Lỗi: {result['error']} |\n")
                    else:
                        trades = result.get('total_trades', 0)
                        win_rate = result.get('win_rate', 0)
                        profit = result.get('total_profit_pct', 0)
                        drawdown = result.get('max_drawdown_pct', 0)
                        profit_factor = result.get('profit_factor', 0)
                        
                        f.write(f"| {symbol} | {risk_level} | {trades} | {win_rate:.2f}% | {profit:.2f}% | {drawdown:.2f}% | {profit_factor:.2f} |\n")
            
            f.write("\n")
            
            # Phân tích hiệu suất theo mức rủi ro
            f.write("## PHÂN TÍCH HIỆU SUẤT THEO MỨC RỦI RO\n\n")
            
            # Thu thập thống kê theo mức rủi ro
            risk_stats = {risk: {'trades': 0, 'wins': 0, 'profit': 0, 'drawdown': 0, 'symbols': 0} 
                        for risk in RISK_LEVELS}
            
            for symbol, symbol_data in all_results.items():
                for risk_level, result in symbol_data.items():
                    if 'error' not in result and result.get('total_trades', 0) > 0:
                        risk_stats[risk_level]['trades'] += result.get('total_trades', 0)
                        risk_stats[risk_level]['wins'] += result.get('winning_trades', 0)
                        risk_stats[risk_level]['profit'] += result.get('total_profit', 0)
                        risk_stats[risk_level]['drawdown'] += result.get('max_drawdown_pct', 0)
                        risk_stats[risk_level]['symbols'] += 1
            
            # Tính tỷ lệ thắng và các thống kê trung bình
            for risk, stats in risk_stats.items():
                if stats['trades'] > 0:
                    stats['win_rate'] = (stats['wins'] / stats['trades'] * 100)
                    
                if stats['symbols'] > 0:
                    stats['avg_drawdown'] = stats['drawdown'] / stats['symbols']
                    
                stats['profit_per_trade'] = stats['profit'] / stats['trades'] if stats['trades'] > 0 else 0
            
            # Hiển thị thống kê
            f.write("| Mức rủi ro | Tổng giao dịch | Win rate | Tổng lợi nhuận | Lợi nhuận/Giao dịch | Drawdown TB |\n")
            f.write("|------------|----------------|----------|----------------|---------------------|------------|\n")
            
            for risk in RISK_LEVELS:
                stats = risk_stats[risk]
                f.write(f"| {risk} | {stats['trades']} | {stats.get('win_rate', 0):.2f}% | ${stats['profit']:.2f} | ${stats.get('profit_per_trade', 0):.2f} | {stats.get('avg_drawdown', 0):.2f}% |\n")
            
            f.write("\n")
            
            # So sánh tỷ lệ lợi nhuận / drawdown (risk-adjusted return)
            f.write("## TỶ LỆ LỢI NHUẬN / RỦI RO\n\n")
            
            # Tính tỷ lệ lợi nhuận / drawdown cho từng mức rủi ro và symbol
            risk_adjusted_returns = {}
            
            for symbol, symbol_data in all_results.items():
                risk_adjusted_returns[symbol] = {}
                
                for risk_level, result in symbol_data.items():
                    if 'error' not in result and result.get('max_drawdown_pct', 0) > 0:
                        profit = result.get('total_profit_pct', 0)
                        drawdown = result.get('max_drawdown_pct', 0)
                        
                        # Tỷ lệ lợi nhuận / drawdown
                        ratio = profit / drawdown if drawdown > 0 else 0
                        
                        risk_adjusted_returns[symbol][risk_level] = ratio
            
            # Hiển thị tỷ lệ
            f.write("| Symbol | extremely_low | low | medium | high | extremely_high |\n")
            f.write("|--------|--------------|-----|--------|------|---------------|\n")
            
            for symbol in SYMBOLS:
                f.write(f"| {symbol} |")
                
                for risk in RISK_LEVELS:
                    ratio = risk_adjusted_returns.get(symbol, {}).get(risk, 0)
                    f.write(f" {ratio:.2f} |")
                
                f.write("\n")
            
            f.write("\n")
            
            # Kết luận
            f.write("## KẾT LUẬN VÀ KHUYẾN NGHỊ\n\n")
            
            # Xác định mức rủi ro tối ưu
            optimal_risk = max(risk_stats.items(), key=lambda x: x[1].get('profit', 0))[0]
            highest_winrate_risk = max(risk_stats.items(), key=lambda x: x[1].get('win_rate', 0))[0]
            best_risk_adjusted = max(risk_stats.items(), key=lambda x: x[1].get('profit', 0) / x[1].get('avg_drawdown', 1) if x[1].get('avg_drawdown', 0) > 0 else 0)[0]
            
            f.write(f"1. **Mức rủi ro có lợi nhuận cao nhất**: {optimal_risk}\n")
            f.write(f"2. **Mức rủi ro có tỷ lệ thắng cao nhất**: {highest_winrate_risk}\n")
            f.write(f"3. **Mức rủi ro có tỷ lệ lợi nhuận/rủi ro tốt nhất**: {best_risk_adjusted}\n\n")
            
            # Đề xuất cấu hình
            f.write("### Đề xuất cấu hình tối ưu\n\n")
            
            optimal_config = RISK_CONFIGS[best_risk_adjusted]
            
            f.write(f"Dựa trên phân tích, chúng tôi đề xuất sử dụng mức rủi ro **{best_risk_adjusted}** với các thông số sau:\n\n")
            f.write(f"- Rủi ro mỗi giao dịch: {optimal_config['risk_per_trade']}%\n")
            f.write(f"- Đòn bẩy tối đa: {optimal_config['max_leverage']}x\n")
            f.write(f"- Hệ số ATR cho Stop Loss: {optimal_config['stop_loss_atr_multiplier']}\n")
            f.write(f"- Hệ số ATR cho Take Profit: {optimal_config['take_profit_atr_multiplier']}\n")
            f.write(f"- Kích hoạt Trailing Stop: {optimal_config['trailing_stop_activation_pct']}%\n")
            f.write(f"- Callback Trailing Stop: {optimal_config['trailing_stop_callback_pct']}%\n\n")
            
            # Đề xuất cải thiện
            f.write("### Đề xuất cải thiện\n\n")
            f.write("1. **Cải thiện bộ lọc tín hiệu** để tăng tỷ lệ thắng\n")
            f.write("2. **Tích hợp phân tích đa khung thời gian** để xác nhận tín hiệu\n")
            f.write("3. **Tối ưu hóa partial take profit** dựa trên biến động thị trường\n")
            f.write("4. **Điều chỉnh động các thông số rủi ro** dựa trên hiệu suất gần đây\n")
            f.write("5. **Thêm bộ lọc khối lượng giao dịch** để xác nhận các tín hiệu breakout\n")
        
        logger.info(f"Đã tạo báo cáo tại: {report_path}")
        
        # Tạo biểu đồ so sánh
        create_comparison_charts(all_results)
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo: {e}")
        logger.error(traceback.format_exc())

def create_comparison_charts(all_results):
    """Tạo biểu đồ so sánh hiệu suất"""
    try:
        # Biểu đồ 1: So sánh lợi nhuận theo mức rủi ro
        profits_by_risk = {risk: [] for risk in RISK_LEVELS}
        
        for symbol, symbol_data in all_results.items():
            for risk_level, result in symbol_data.items():
                if 'error' not in result:
                    profits_by_risk[risk_level].append(result.get('total_profit_pct', 0))
        
        plt.figure(figsize=(12, 6))
        
        x = range(len(RISK_LEVELS))
        width = 0.8
        
        # Vẽ boxplot
        medians = []
        for i, risk in enumerate(RISK_LEVELS):
            box = plt.boxplot(profits_by_risk[risk], positions=[i], widths=width/2, patch_artist=True,
                           boxprops=dict(facecolor=f'C{i}', alpha=0.7))
            medians.append(np.median(profits_by_risk[risk]) if profits_by_risk[risk] else 0)
        
        plt.axhline(y=0, color='red', linestyle='--', alpha=0.7)
        plt.title('Lợi nhuận (%) theo mức rủi ro', fontsize=14)
        plt.ylabel('Lợi nhuận (%)', fontsize=12)
        plt.xticks(x, RISK_LEVELS)
        plt.grid(axis='y', alpha=0.3)
        
        # Thêm giá trị trung vị
        for i, med in enumerate(medians):
            plt.text(i, med + 0.5, f'{med:.2f}%', ha='center')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'profit_by_risk_level.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 2: So sánh win rate theo mức rủi ro
        winrates_by_risk = {risk: [] for risk in RISK_LEVELS}
        
        for symbol, symbol_data in all_results.items():
            for risk_level, result in symbol_data.items():
                if 'error' not in result:
                    winrates_by_risk[risk_level].append(result.get('win_rate', 0))
        
        plt.figure(figsize=(12, 6))
        
        # Tính giá trị trung bình
        avg_winrates = [np.mean(winrates_by_risk[risk]) if winrates_by_risk[risk] else 0 for risk in RISK_LEVELS]
        
        bars = plt.bar(x, avg_winrates, width=width, alpha=0.7)
        
        plt.axhline(y=50, color='red', linestyle='--', alpha=0.7)
        plt.title('Tỷ lệ thắng (%) theo mức rủi ro', fontsize=14)
        plt.ylabel('Tỷ lệ thắng (%)', fontsize=12)
        plt.xticks(x, RISK_LEVELS)
        plt.grid(axis='y', alpha=0.3)
        
        # Thêm giá trị
        for i, v in enumerate(avg_winrates):
            plt.text(i, v + 1, f'{v:.2f}%', ha='center')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'winrate_by_risk_level.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 3: So sánh drawdown theo mức rủi ro
        drawdowns_by_risk = {risk: [] for risk in RISK_LEVELS}
        
        for symbol, symbol_data in all_results.items():
            for risk_level, result in symbol_data.items():
                if 'error' not in result:
                    drawdowns_by_risk[risk_level].append(result.get('max_drawdown_pct', 0))
        
        plt.figure(figsize=(12, 6))
        
        # Vẽ boxplot
        medians = []
        for i, risk in enumerate(RISK_LEVELS):
            box = plt.boxplot(drawdowns_by_risk[risk], positions=[i], widths=width/2, patch_artist=True,
                           boxprops=dict(facecolor=f'C{i}', alpha=0.7))
            medians.append(np.median(drawdowns_by_risk[risk]) if drawdowns_by_risk[risk] else 0)
        
        plt.title('Drawdown (%) theo mức rủi ro', fontsize=14)
        plt.ylabel('Drawdown (%)', fontsize=12)
        plt.xticks(x, RISK_LEVELS)
        plt.grid(axis='y', alpha=0.3)
        
        # Thêm giá trị trung vị
        for i, med in enumerate(medians):
            plt.text(i, med + 0.5, f'{med:.2f}%', ha='center')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'drawdown_by_risk_level.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 4: So sánh tỷ lệ lợi nhuận / drawdown (risk-adjusted return)
        risk_adjusted_returns = {risk: [] for risk in RISK_LEVELS}
        
        for symbol, symbol_data in all_results.items():
            for risk_level, result in symbol_data.items():
                if 'error' not in result and result.get('max_drawdown_pct', 0) > 0:
                    profit = result.get('total_profit_pct', 0)
                    drawdown = result.get('max_drawdown_pct', 0)
                    
                    # Tỷ lệ lợi nhuận / drawdown
                    ratio = profit / drawdown if drawdown > 0 else 0
                    
                    risk_adjusted_returns[risk_level].append(ratio)
        
        plt.figure(figsize=(12, 6))
        
        # Tính giá trị trung bình
        avg_ratios = [np.mean(risk_adjusted_returns[risk]) if risk_adjusted_returns[risk] else 0 for risk in RISK_LEVELS]
        
        bars = plt.bar(x, avg_ratios, width=width, alpha=0.7)
        
        plt.axhline(y=1, color='red', linestyle='--', alpha=0.7)
        plt.title('Tỷ lệ lợi nhuận / rủi ro theo mức rủi ro', fontsize=14)
        plt.ylabel('Lợi nhuận / Drawdown', fontsize=12)
        plt.xticks(x, RISK_LEVELS)
        plt.grid(axis='y', alpha=0.3)
        
        # Thêm giá trị
        for i, v in enumerate(avg_ratios):
            plt.text(i, v + 0.1, f'{v:.2f}', ha='center')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'risk_adjusted_return.png'), dpi=100)
        plt.close()
        
        # Biểu đồ 5: So sánh hiệu suất giữa các symbol
        plt.figure(figsize=(14, 10))
        
        # Tạo subplot
        plt.subplot(2, 1, 1)
        
        width = 0.15
        x = np.arange(len(SYMBOLS))
        
        for i, risk in enumerate(RISK_LEVELS):
            profits = [all_results.get(symbol, {}).get(risk, {}).get('total_profit_pct', 0) for symbol in SYMBOLS]
            plt.bar(x + width * (i - 2), profits, width=width, label=risk)
        
        plt.title('Lợi nhuận (%) theo symbol và mức rủi ro', fontsize=14)
        plt.ylabel('Lợi nhuận (%)', fontsize=12)
        plt.xticks(x, SYMBOLS)
        plt.grid(axis='y', alpha=0.3)
        plt.legend()
        
        # Subplot win rate
        plt.subplot(2, 1, 2)
        
        for i, risk in enumerate(RISK_LEVELS):
            winrates = [all_results.get(symbol, {}).get(risk, {}).get('win_rate', 0) for symbol in SYMBOLS]
            plt.bar(x + width * (i - 2), winrates, width=width, label=risk)
        
        plt.title('Tỷ lệ thắng (%) theo symbol và mức rủi ro', fontsize=14)
        plt.ylabel('Tỷ lệ thắng (%)', fontsize=12)
        plt.xticks(x, SYMBOLS)
        plt.grid(axis='y', alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'symbol_performance.png'), dpi=100)
        plt.close()
        
        logger.info("Đã tạo các biểu đồ so sánh")
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Kiểm tra API key
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("Không tìm thấy Binance API keys. Vui lòng thiết lập BINANCE_API_KEY và BINANCE_API_SECRET.")
        sys.exit(1)
    
    # Chạy test đầy đủ 5 mức rủi ro
    run_full_risk_test()
