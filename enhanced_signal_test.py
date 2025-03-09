#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module kiểm thử hệ thống tín hiệu nâng cao

Module này kiểm thử các chức năng của module enhanced_signal_generator,
với nhiều kịch bản thị trường và điều kiện khác nhau.
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
from enhanced_signal_generator import EnhancedSignalGenerator

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/enhanced_signal_test.log')
    ]
)

logger = logging.getLogger('enhanced_signal_test')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('test_results', exist_ok=True)


def generate_test_data(scenario='mixed', periods=500):
    """
    Tạo dữ liệu test giả lập với nhiều kịch bản thị trường khác nhau
    
    Args:
        scenario (str): Kịch bản thị trường ('uptrend', 'downtrend', 'sideway', 'volatile', 'mixed')
        periods (int): Số lượng nến
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    logger.info(f"Tạo dữ liệu test cho kịch bản {scenario} với {periods} nến")
    
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='1h')
    df = pd.DataFrame(index=dates)
    
    # Chuẩn bị các tham số theo kịch bản
    if scenario == 'uptrend':
        # Xu hướng tăng mạnh
        trend = np.linspace(0, 0.4, periods)  # Tăng 40%
        noise_level = 0.01
        
    elif scenario == 'downtrend':
        # Xu hướng giảm mạnh
        trend = np.linspace(0, -0.35, periods)  # Giảm 35%
        noise_level = 0.015
        
    elif scenario == 'sideway':
        # Thị trường sideway
        trend = 0.05 * np.sin(np.linspace(0, 8*np.pi, periods))
        noise_level = 0.008
        
    elif scenario == 'volatile':
        # Thị trường biến động cao
        trend = 0.1 * np.sin(np.linspace(0, 4*np.pi, periods))
        noise_level = 0.03
        
    elif scenario == 'mixed':
        # Kết hợp các loại thị trường
        segment_size = periods // 5
        
        # 1. Uptrend
        up_trend = np.linspace(0, 0.25, segment_size)
        up_noise = np.random.normal(0, 0.01, segment_size)
        up_prices = 100 * (1 + up_trend + up_noise)
        
        # 2. Sideway sau uptrend
        sideways1_center = up_prices[-1]
        sideways1_noise = np.random.normal(0, 0.008, segment_size)
        sideways1_prices = sideways1_center * (1 + 0.03 * np.sin(np.linspace(0, 4*np.pi, segment_size)) + sideways1_noise)
        
        # 3. Downtrend
        down_start = sideways1_prices[-1]
        down_trend = np.linspace(0, -0.3, segment_size)
        down_noise = np.random.normal(0, 0.015, segment_size)
        down_prices = down_start * (1 + down_trend + down_noise)
        
        # 4. Volatile period
        volatile_start = down_prices[-1]
        volatile_trend = 0.15 * np.sin(np.linspace(0, 6*np.pi, segment_size))
        volatile_noise = np.random.normal(0, 0.03, segment_size)
        volatile_prices = volatile_start * (1 + volatile_trend + volatile_noise)
        
        # 5. Sideway after volatile
        sideways2_center = volatile_prices[-1]
        sideways2_noise = np.random.normal(0, 0.007, segment_size)
        sideways2_prices = sideways2_center * (1 + 0.02 * np.sin(np.linspace(0, 3*np.pi, segment_size)) + sideways2_noise)
        
        # Ghép tất cả lại
        prices = np.concatenate([up_prices, sideways1_prices, down_prices, volatile_prices, sideways2_prices])
        
        # Đảm bảo prices có đúng độ dài
        if len(prices) != periods:
            if len(prices) < periods:
                prices = np.append(prices, [prices[-1]] * (periods - len(prices)))
            else:
                prices = prices[:periods]
        
        df['close'] = prices
        
    else:
        # Mặc định: Kịch bản hỗn hợp đơn giản
        trend = np.concatenate([
            np.linspace(0, 0.2, periods//3),
            np.linspace(0, -0.15, periods//3),
            0.03 * np.sin(np.linspace(0, 6*np.pi, periods - 2*(periods//3)))
        ])
        
        noise_level = 0.012
        
        # Đảm bảo trend có đúng độ dài
        if len(trend) != periods:
            if len(trend) < periods:
                trend = np.append(trend, [trend[-1]] * (periods - len(trend)))
            else:
                trend = trend[:periods]
    
    # Tạo giá nếu chưa có (cho các kịch bản không phải 'mixed')
    if 'close' not in df.columns:
        noise = np.random.normal(0, noise_level, periods)
        df['close'] = 100 * np.cumprod(1 + trend + noise)
    
    # Tạo giá mở
    df['open'] = np.roll(df['close'], 1)
    df.loc[df.index[0], 'open'] = df.loc[df.index[0], 'close'] * 0.998
    
    # Tạo high và low
    high_adjust = 1 + np.random.uniform(0.001, 0.008, len(df))
    df['high'] = np.maximum(df['open'], df['close']) * high_adjust
    
    low_adjust = 1 - np.random.uniform(0.001, 0.008, len(df))
    df['low'] = np.minimum(df['open'], df['close']) * low_adjust
    
    # Tạo volume
    if scenario == 'mixed':
        # Volume tương ứng với 5 phân đoạn
        segment_size = periods // 5
        
        vol1 = np.linspace(1, 2, segment_size)  # Volume tăng dần (uptrend)
        vol2 = np.random.normal(1.5, 0.3, segment_size)  # Volume sideway sau uptrend
        vol3 = np.linspace(2, 3, segment_size)  # Volume tăng mạnh (downtrend)
        vol4 = np.random.normal(3, 0.8, segment_size)  # Volume biến động cao
        vol5 = np.random.normal(1.2, 0.2, segment_size)  # Volume thấp và ổn định (sideway)
        
        volume_trend = np.concatenate([vol1, vol2, vol3, vol4, vol5])
        
        # Thêm spike volume tại các điểm chuyển tiếp
        for i in range(1, 5):
            start_idx = i * segment_size - 5
            end_idx = i * segment_size + 5
            if end_idx < len(volume_trend):
                volume_trend[start_idx:end_idx] *= 2.5
    
    elif scenario == 'volatile':
        # Volume cao và biến động mạnh
        volume_base = 2.5 + np.random.normal(0, 0.7, periods)
        volume_spikes = np.zeros(periods)
        
        # Thêm đột biến volume
        spike_indices = np.random.choice(periods, size=periods//10, replace=False)
        volume_spikes[spike_indices] = np.random.uniform(3, 5, len(spike_indices))
        
        volume_trend = volume_base + volume_spikes
        
    elif scenario == 'sideway':
        # Volume thấp và ổn định
        volume_trend = np.random.normal(1.2, 0.2, periods)
        
    else:
        # Volume cơ bản
        volume_trend = np.random.normal(1.5, 0.4, periods)
    
    # Đảm bảo volume_trend có đúng độ dài
    if len(volume_trend) != periods:
        if len(volume_trend) < periods:
            volume_trend = np.append(volume_trend, [volume_trend[-1]] * (periods - len(volume_trend)))
        else:
            volume_trend = volume_trend[:periods]
    
    base_volume = 1000
    volume_noise = 1 + np.random.normal(0, 0.15, periods)
    df['volume'] = (base_volume * volume_trend * volume_noise).astype(int)
    
    logger.info(f"Đã tạo xong dữ liệu test, kích thước: {df.shape}")
    
    return df


def evaluate_signals(df_with_signals, scenario_name, base_position_size=1.0):
    """
    Đánh giá chất lượng tín hiệu giao dịch
    
    Args:
        df_with_signals (pd.DataFrame): DataFrame với tín hiệu giao dịch
        scenario_name (str): Tên kịch bản đang kiểm thử
        base_position_size (float): Kích thước vị thế cơ sở
        
    Returns:
        dict: Kết quả đánh giá
    """
    logger.info(f"Đánh giá tín hiệu giao dịch cho kịch bản {scenario_name}")
    
    # Kết quả đánh giá
    evaluation = {
        'scenario': scenario_name,
        'total_bars': len(df_with_signals),
        'buy_signals': 0,
        'sell_signals': 0,
        'buy_signal_pct': 0.0,
        'sell_signal_pct': 0.0,
        'conflicting_signals': 0,
        'avg_bars_between_signals': 0,
        'backtest_results': {}
    }
    
    # Đếm tín hiệu
    buy_signals = df_with_signals[df_with_signals['final_buy_signal']]
    sell_signals = df_with_signals[df_with_signals['final_sell_signal']]
    
    evaluation['buy_signals'] = len(buy_signals)
    evaluation['sell_signals'] = len(sell_signals)
    
    if len(df_with_signals) > 0:
        evaluation['buy_signal_pct'] = len(buy_signals) / len(df_with_signals) * 100
        evaluation['sell_signal_pct'] = len(sell_signals) / len(df_with_signals) * 100
    
    # Kiểm tra xung đột tín hiệu
    if 'final_buy_signal' in df_with_signals.columns and 'final_sell_signal' in df_with_signals.columns:
        conflicting = df_with_signals[df_with_signals['final_buy_signal'] & df_with_signals['final_sell_signal']]
        evaluation['conflicting_signals'] = len(conflicting)
    
    # Tính khoảng cách trung bình giữa các tín hiệu
    all_signal_indices = sorted(list(buy_signals.index) + list(sell_signals.index))
    
    if len(all_signal_indices) > 1:
        signal_distances = []
        for i in range(1, len(all_signal_indices)):
            dist = (all_signal_indices[i] - all_signal_indices[i-1]).total_seconds() / 3600  # Giờ
            signal_distances.append(dist)
        
        evaluation['avg_bars_between_signals'] = sum(signal_distances) / len(signal_distances)
    
    # Thực hiện backtest đơn giản
    backtest_results = simple_backtest(df_with_signals, base_position_size)
    evaluation['backtest_results'] = backtest_results
    
    # In kết quả đánh giá
    logger.info(f"Đánh giá tín hiệu cho {scenario_name}:")
    logger.info(f"Tổng số nến: {evaluation['total_bars']}")
    logger.info(f"Tín hiệu mua: {evaluation['buy_signals']} ({evaluation['buy_signal_pct']:.2f}%)")
    logger.info(f"Tín hiệu bán: {evaluation['sell_signals']} ({evaluation['sell_signal_pct']:.2f}%)")
    logger.info(f"Tín hiệu xung đột: {evaluation['conflicting_signals']}")
    logger.info(f"Khoảng cách trung bình giữa các tín hiệu: {evaluation['avg_bars_between_signals']:.2f} giờ")
    
    logger.info(f"Kết quả backtest:")
    logger.info(f"Tổng số giao dịch: {backtest_results['total_trades']}")
    logger.info(f"Lợi nhuận: {backtest_results['profit_pct']:.2f}%")
    logger.info(f"Win rate: {backtest_results['win_rate']:.2f}%")
    logger.info(f"Profit factor: {backtest_results['profit_factor']:.2f}")
    logger.info(f"Max drawdown: {backtest_results['max_drawdown_pct']:.2f}%")
    
    return evaluation


def simple_backtest(df, base_position_size=1.0):
    """
    Thực hiện backtest đơn giản cho tín hiệu giao dịch
    
    Args:
        df (pd.DataFrame): DataFrame với tín hiệu giao dịch
        base_position_size (float): Kích thước vị thế cơ sở
        
    Returns:
        dict: Kết quả backtest
    """
    logger.info("Thực hiện backtest đơn giản...")
    
    # Tạo bản sao để không ảnh hưởng đến dữ liệu gốc
    df_backtest = df.copy()
    
    # Khởi tạo trạng thái
    position = None  # 'long', 'short', hoặc None
    entry_price = 0.0
    entry_index = None
    position_size = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    equity = 10000.0  # Vốn ban đầu
    initial_equity = equity
    
    # Danh sách lưu trữ các giao dịch
    trades = []
    
    # Theo dõi equity qua thời gian
    df_backtest['equity'] = initial_equity
    
    # Vòng lặp qua từng nến
    for i in range(len(df_backtest)):
        # Lấy dữ liệu hiện tại
        current_bar = df_backtest.iloc[i]
        current_index = df_backtest.index[i]
        
        # Cập nhật equity
        if i > 0:
            df_backtest.loc[df_backtest.index[i], 'equity'] = equity
        
        # Kiểm tra TP/SL nếu đang có vị thế
        if position == 'long':
            # Kiểm tra SL
            if current_bar['low'] <= stop_loss:
                # Tính P/L
                pnl_pct = (stop_loss / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                
                # Cập nhật equity
                equity += pnl_amount
                
                # Lưu giao dịch
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                # Log
                logger.info(f"Thoát LONG qua SL tại {stop_loss:.2f}, Entry: {entry_price:.2f}, P/L: {pnl_pct:.2f}%, ${pnl_amount:.2f}")
                
                # Reset trạng thái
                position = None
            
            # Kiểm tra TP
            elif current_bar['high'] >= take_profit:
                # Tính P/L
                pnl_pct = (take_profit / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                
                # Cập nhật equity
                equity += pnl_amount
                
                # Lưu giao dịch
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': take_profit,
                    'exit_reason': 'take_profit',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                # Log
                logger.info(f"Thoát LONG qua TP tại {take_profit:.2f}, Entry: {entry_price:.2f}, P/L: {pnl_pct:.2f}%, ${pnl_amount:.2f}")
                
                # Reset trạng thái
                position = None
            
            # Kiểm tra tín hiệu thoát
            elif current_bar['final_sell_signal']:
                # Tính P/L
                pnl_pct = (current_bar['close'] / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                
                # Cập nhật equity
                equity += pnl_amount
                
                # Lưu giao dịch
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': current_bar['close'],
                    'exit_reason': 'signal',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                # Log
                logger.info(f"Thoát LONG qua tín hiệu tại {current_bar['close']:.2f}, Entry: {entry_price:.2f}, P/L: {pnl_pct:.2f}%, ${pnl_amount:.2f}")
                
                # Reset trạng thái
                position = None
        
        elif position == 'short':
            # Kiểm tra SL
            if current_bar['high'] >= stop_loss:
                # Tính P/L
                pnl_pct = (1 - stop_loss / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                
                # Cập nhật equity
                equity += pnl_amount
                
                # Lưu giao dịch
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                # Log
                logger.info(f"Thoát SHORT qua SL tại {stop_loss:.2f}, Entry: {entry_price:.2f}, P/L: {pnl_pct:.2f}%, ${pnl_amount:.2f}")
                
                # Reset trạng thái
                position = None
            
            # Kiểm tra TP
            elif current_bar['low'] <= take_profit:
                # Tính P/L
                pnl_pct = (1 - take_profit / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                
                # Cập nhật equity
                equity += pnl_amount
                
                # Lưu giao dịch
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': take_profit,
                    'exit_reason': 'take_profit',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                # Log
                logger.info(f"Thoát SHORT qua TP tại {take_profit:.2f}, Entry: {entry_price:.2f}, P/L: {pnl_pct:.2f}%, ${pnl_amount:.2f}")
                
                # Reset trạng thái
                position = None
            
            # Kiểm tra tín hiệu thoát
            elif current_bar['final_buy_signal']:
                # Tính P/L
                pnl_pct = (1 - current_bar['close'] / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                
                # Cập nhật equity
                equity += pnl_amount
                
                # Lưu giao dịch
                trades.append({
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': current_bar['close'],
                    'exit_reason': 'signal',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                # Log
                logger.info(f"Thoát SHORT qua tín hiệu tại {current_bar['close']:.2f}, Entry: {entry_price:.2f}, P/L: {pnl_pct:.2f}%, ${pnl_amount:.2f}")
                
                # Reset trạng thái
                position = None
        
        # Nếu không có vị thế, kiểm tra tín hiệu vào lệnh
        if position is None:
            if current_bar['final_buy_signal']:
                # Mở vị thế LONG
                position = 'long'
                entry_price = current_bar['close']
                entry_index = current_index
                
                # Áp dụng kích thước vị thế động nếu có
                if 'position_size_multiplier' in current_bar:
                    position_size = base_position_size * current_bar['position_size_multiplier']
                else:
                    position_size = base_position_size
                
                # Tính SL và TP
                if 'buy_sl_price' in current_bar and 'buy_tp_price' in current_bar:
                    stop_loss = current_bar['buy_sl_price']
                    take_profit = current_bar['buy_tp_price']
                else:
                    # Mặc định: SL = 2% dưới giá vào, TP = 4% trên giá vào
                    stop_loss = entry_price * 0.98
                    take_profit = entry_price * 1.04
                
                # Log
                trade_size = equity * position_size
                logger.info(f"Mở vị thế LONG tại {entry_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}, Size: ${trade_size:.2f}")
            
            elif current_bar['final_sell_signal']:
                # Mở vị thế SHORT
                position = 'short'
                entry_price = current_bar['close']
                entry_index = current_index
                
                # Áp dụng kích thước vị thế động nếu có
                if 'position_size_multiplier' in current_bar:
                    position_size = base_position_size * current_bar['position_size_multiplier']
                else:
                    position_size = base_position_size
                
                # Tính SL và TP
                if 'sell_sl_price' in current_bar and 'sell_tp_price' in current_bar:
                    stop_loss = current_bar['sell_sl_price']
                    take_profit = current_bar['sell_tp_price']
                else:
                    # Mặc định: SL = 2% trên giá vào, TP = 4% dưới giá vào
                    stop_loss = entry_price * 1.02
                    take_profit = entry_price * 0.96
                
                # Log
                trade_size = equity * position_size
                logger.info(f"Mở vị thế SHORT tại {entry_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}, Size: ${trade_size:.2f}")
    
    # Tính các chỉ số hiệu suất
    total_trades = len(trades)
    profit_pct = (equity / initial_equity - 1) * 100
    
    winning_trades = [t for t in trades if t['pnl_amount'] > 0]
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = sum([t['pnl_amount'] for t in winning_trades])
    total_loss = abs(sum([t['pnl_amount'] for t in trades if t['pnl_amount'] < 0]))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    # Tính max drawdown
    cumulative_returns = (df_backtest['equity'] / initial_equity)
    running_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns / running_max - 1) * 100
    max_drawdown_pct = abs(drawdown.min())
    
    # Vẽ biểu đồ equity
    plt.figure(figsize=(12, 6))
    plt.plot(df_backtest.index, df_backtest['equity'])
    plt.title(f'Equity Curve (Profit: {profit_pct:.2f}%, Max DD: {max_drawdown_pct:.2f}%)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f'test_results/equity_curve.png')
    plt.close()
    
    # Vẽ biểu đồ drawdown
    plt.figure(figsize=(12, 6))
    plt.fill_between(df_backtest.index, drawdown, 0, color='red', alpha=0.3)
    plt.plot(df_backtest.index, drawdown, color='red')
    plt.title(f'Drawdown (Max: {max_drawdown_pct:.2f}%)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f'test_results/drawdown.png')
    plt.close()
    
    # Kết quả
    results = {
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': total_trades - len(winning_trades),
        'win_rate': win_rate,
        'profit_pct': profit_pct,
        'profit_amount': equity - initial_equity,
        'profit_factor': profit_factor,
        'max_drawdown_pct': max_drawdown_pct,
        'final_equity': equity,
        'trades': trades
    }
    
    return results


def test_signal_generator(scenarios=None, periods=500):
    """
    Kiểm thử toàn diện EnhancedSignalGenerator với nhiều kịch bản khác nhau
    
    Args:
        scenarios (list, optional): Danh sách các kịch bản cần kiểm thử
        periods (int): Số lượng nến cho mỗi kịch bản
        
    Returns:
        dict: Kết quả kiểm thử cho mỗi kịch bản
    """
    logger.info("Bắt đầu kiểm thử toàn diện EnhancedSignalGenerator")
    
    # Mặc định kiểm thử tất cả các kịch bản
    if scenarios is None:
        scenarios = ['uptrend', 'downtrend', 'sideway', 'volatile', 'mixed']
    
    # Khởi tạo EnhancedSignalGenerator
    signal_generator = EnhancedSignalGenerator()
    
    # Kết quả kiểm thử
    test_results = {}
    
    # Kiểm thử từng kịch bản
    for scenario in scenarios:
        logger.info(f"Kiểm thử kịch bản: {scenario}")
        
        # Tạo dữ liệu kiểm thử
        test_data = generate_test_data(scenario=scenario, periods=periods)
        
        # Xử lý dữ liệu và tạo tín hiệu
        result_df = signal_generator.process_data(test_data, base_position_size=0.02)
        
        # Đánh giá tín hiệu
        evaluation = evaluate_signals(result_df, scenario, base_position_size=0.02)
        
        # Lưu kết quả
        test_results[scenario] = evaluation
        
        # Lưu biểu đồ tổng quan
        plt.figure(figsize=(14, 10))
        
        # Vẽ giá và tín hiệu
        ax1 = plt.subplot(3, 1, 1)
        ax1.set_title(f'Giá và Tín Hiệu - Kịch bản {scenario}')
        
        # Chỉ vẽ 200 nến cuối cùng để biểu đồ rõ ràng hơn
        display_df = result_df.iloc[-200:].copy() if len(result_df) > 200 else result_df.copy()
        
        # Vẽ giá
        ax1.plot(display_df.index, display_df['close'], color='blue')
        
        # Vẽ SMA
        for sma_period in [20, 50, 200]:
            col_name = f'sma_{sma_period}'
            if col_name in display_df.columns:
                ax1.plot(display_df.index, display_df[col_name], linestyle='--', label=f'SMA {sma_period}')
        
        # Đánh dấu tín hiệu
        buy_signals = display_df[display_df['final_buy_signal']]
        sell_signals = display_df[display_df['final_sell_signal']]
        
        ax1.scatter(buy_signals.index, buy_signals['close'], marker='^', color='lime', s=100, label='Mua')
        ax1.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='Bán')
        
        ax1.legend()
        ax1.grid(True)
        
        # Vẽ các chỉ báo
        ax2 = plt.subplot(3, 1, 2)
        ax2.set_title('RSI và Stochastic')
        
        if 'rsi' in display_df.columns:
            ax2.plot(display_df.index, display_df['rsi'], color='blue', label='RSI')
            ax2.axhline(y=70, color='r', linestyle='--')
            ax2.axhline(y=30, color='g', linestyle='--')
        
        if all(col in display_df.columns for col in ['stoch_k', 'stoch_d']):
            ax2b = ax2.twinx()
            ax2b.plot(display_df.index, display_df['stoch_k'], color='orange', label='Stoch K')
            ax2b.plot(display_df.index, display_df['stoch_d'], color='purple', label='Stoch D')
            ax2b.set_ylim(0, 100)
            ax2b.legend(loc='upper right')
        
        ax2.set_ylim(0, 100)
        ax2.legend(loc='upper left')
        ax2.grid(True)
        
        # Vẽ equity
        ax3 = plt.subplot(3, 1, 3)
        ax3.set_title('Equity')
        
        if 'equity' in display_df.columns:
            ax3.plot(display_df.index, display_df['equity'], color='green')
        
        ax3.grid(True)
        
        plt.tight_layout()
        plt.savefig(f'test_results/{scenario}_overview.png')
        plt.close()
    
    # Tổng hợp kết quả kiểm thử
    logger.info("Tổng hợp kết quả kiểm thử:")
    
    for scenario, result in test_results.items():
        logger.info(f"\n--- Kịch bản: {scenario} ---")
        logger.info(f"Buy Signal: {result['buy_signals']} ({result['buy_signal_pct']:.2f}%)")
        logger.info(f"Sell Signal: {result['sell_signals']} ({result['sell_signal_pct']:.2f}%)")
        logger.info(f"Conflicting Signals: {result['conflicting_signals']}")
        logger.info(f"Win Rate: {result['backtest_results']['win_rate']:.2f}%")
        logger.info(f"Profit: {result['backtest_results']['profit_pct']:.2f}%")
        logger.info(f"Max Drawdown: {result['backtest_results']['max_drawdown_pct']:.2f}%")
    
    # Vẽ biểu đồ so sánh
    scenarios_list = list(test_results.keys())
    win_rates = [result['backtest_results']['win_rate'] for result in test_results.values()]
    profits = [result['backtest_results']['profit_pct'] for result in test_results.values()]
    drawdowns = [result['backtest_results']['max_drawdown_pct'] for result in test_results.values()]
    
    # Vẽ biểu đồ win rate
    plt.figure(figsize=(10, 6))
    plt.bar(scenarios_list, win_rates, color='green')
    plt.title('Win Rate by Scenario')
    plt.ylabel('Win Rate (%)')
    plt.grid(axis='y')
    plt.ylim(0, 100)
    
    for i, v in enumerate(win_rates):
        plt.text(i, v + 1, f"{v:.1f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig('test_results/win_rate_comparison.png')
    plt.close()
    
    # Vẽ biểu đồ lợi nhuận
    plt.figure(figsize=(10, 6))
    plt.bar(scenarios_list, profits, color='blue')
    plt.title('Profit by Scenario')
    plt.ylabel('Profit (%)')
    plt.grid(axis='y')
    
    for i, v in enumerate(profits):
        plt.text(i, v + 0.5, f"{v:.1f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig('test_results/profit_comparison.png')
    plt.close()
    
    # Vẽ biểu đồ drawdown
    plt.figure(figsize=(10, 6))
    plt.bar(scenarios_list, drawdowns, color='red')
    plt.title('Max Drawdown by Scenario')
    plt.ylabel('Max Drawdown (%)')
    plt.grid(axis='y')
    
    for i, v in enumerate(drawdowns):
        plt.text(i, v + 0.5, f"{v:.1f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig('test_results/drawdown_comparison.png')
    plt.close()
    
    return test_results


if __name__ == "__main__":
    # Kiểm thử với tất cả các kịch bản
    test_results = test_signal_generator(periods=1000)
    
    # Lưu kết quả kiểm thử
    with open('test_results/test_results.json', 'w') as f:
        # Chuyển đổi datetime thành string
        import json
        
        def datetime_handler(x):
            if isinstance(x, datetime):
                return x.isoformat()
            raise TypeError("Unknown type")
        
        # Xử lý các đối tượng không serialize được
        serializable_results = {}
        for scenario, result in test_results.items():
            serializable_result = result.copy()
            
            # Xử lý danh sách giao dịch
            trades = []
            for trade in result['backtest_results']['trades']:
                trade_copy = trade.copy()
                trade_copy['entry_date'] = trade_copy['entry_date'].isoformat()
                trade_copy['exit_date'] = trade_copy['exit_date'].isoformat()
                trades.append(trade_copy)
            
            serializable_result['backtest_results']['trades'] = trades
            serializable_results[scenario] = serializable_result
        
        json.dump(serializable_results, f, indent=4, default=datetime_handler)
    
    logger.info("Đã lưu kết quả kiểm thử vào test_results/test_results.json")
    logger.info("Hoàn thành kiểm thử EnhancedSignalGenerator")