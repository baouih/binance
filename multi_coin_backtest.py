#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module kiểm tra chiến lược giao dịch trên nhiều coin và khung thời gian khác nhau

Module này sử dụng EnhancedSignalGenerator để kiểm thử hiệu suất
trên dữ liệu thực từ nhiều cặp tiền và khung thời gian.
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
from enhanced_signal_generator import EnhancedSignalGenerator

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/multi_coin_test.log')
    ]
)

logger = logging.getLogger('multi_coin_test')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('test_results/multi_coin', exist_ok=True)


def fetch_historical_data(symbol, timeframe='1h', limit=5000):
    """
    Lấy dữ liệu lịch sử từ Binance
    
    Args:
        symbol (str): Cặp tiền tệ (ví dụ: 'BTC/USDT')
        timeframe (str): Khung thời gian (ví dụ: '1h', '4h', '1d')
        limit (int): Số lượng nến tối đa cần lấy
        
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
        
        # Lấy dữ liệu
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
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
        periods = 1000
        dates = pd.date_range(end=datetime.now(), periods=periods, freq=timeframe)
        
        # Giá bắt đầu
        if 'BTC' in symbol:
            start_price = 30000
        elif 'ETH' in symbol:
            start_price = 2000
        elif 'SOL' in symbol:
            start_price = 100
        else:
            start_price = 50
        
        # Tạo dữ liệu giả lập với xu hướng ngẫu nhiên
        trend = np.concatenate([
            np.linspace(0, 0.2, periods//3),  # Uptrend
            np.linspace(0, -0.15, periods//3),  # Downtrend
            0.05 * np.sin(np.linspace(0, 6*np.pi, periods - 2*(periods//3)))  # Sideways
        ])
        
        noise = np.random.normal(0, 0.01, periods)
        close_prices = start_price * np.cumprod(1 + trend + noise)
        
        # Tạo DataFrame
        df = pd.DataFrame(index=dates)
        df['close'] = close_prices
        df['open'] = np.roll(close_prices, 1)
        df.loc[df.index[0], 'open'] = close_prices[0] * 0.998
        
        # Tạo high và low
        df['high'] = np.maximum(df['open'], df['close']) * (1 + np.random.uniform(0.001, 0.008, periods))
        df['low'] = np.minimum(df['open'], df['close']) * (1 - np.random.uniform(0.001, 0.008, periods))
        
        # Tạo volume
        df['volume'] = np.random.normal(100000, 50000, periods).astype(int)
        
        return df


def run_multi_coin_test(symbols=None, timeframes=None, test_period=90):
    """
    Chạy kiểm thử trên nhiều cặp tiền và khung thời gian
    
    Args:
        symbols (list): Danh sách các cặp tiền cần kiểm thử
        timeframes (list): Danh sách các khung thời gian
        test_period (int): Số ngày để kiểm thử (tính từ hiện tại trở về trước)
        
    Returns:
        dict: Kết quả kiểm thử
    """
    logger.info(f"Bắt đầu kiểm thử đa coin cho giai đoạn {test_period} ngày")
    
    # Mặc định
    if symbols is None:
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
    
    if timeframes is None:
        timeframes = ['1h', '4h', '1d']
    
    # Khởi tạo EnhancedSignalGenerator
    signal_generator = EnhancedSignalGenerator()
    
    # Kết quả tổng hợp
    results = {
        'summary': {},
        'details': {}
    }
    
    # Chạy kiểm thử cho từng cặp tiền và khung thời gian
    for symbol in symbols:
        symbol_results = {}
        
        for timeframe in timeframes:
            logger.info(f"Kiểm thử {symbol} trên khung thời gian {timeframe}")
            
            # Tính số nến cần lấy dựa trên khung thời gian và số ngày kiểm thử
            if timeframe == '1h':
                limit = 24 * test_period
            elif timeframe == '4h':
                limit = 6 * test_period
            elif timeframe == '1d':
                limit = test_period
            else:
                limit = 1000  # Mặc định
            
            # Lấy dữ liệu
            df = fetch_historical_data(symbol, timeframe, limit)
            
            # Xử lý dữ liệu và tạo tín hiệu
            result_df = signal_generator.process_data(df, base_position_size=0.02)
            
            # Backtest
            backtest_results = run_backtest(result_df, symbol, timeframe)
            
            # Lưu kết quả
            symbol_results[timeframe] = backtest_results
            
            # Tạo biểu đồ
            save_chart(result_df, symbol, timeframe, backtest_results)
        
        # Lưu kết quả cho cặp tiền
        results['details'][symbol] = symbol_results
    
    # Tổng hợp kết quả
    summary = calculate_summary(results['details'])
    results['summary'] = summary
    
    # Lưu kết quả vào file JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'test_results/multi_coin/results_{timestamp}.json', 'w') as f:
        # Xử lý các đối tượng datetime
        json.dump(results, f, indent=4, default=str)
    
    # Tạo báo cáo tổng hợp
    create_summary_report(results, timestamp)
    
    return results


def run_backtest(df_with_signals, symbol, timeframe):
    """
    Chạy backtest trên DataFrame với tín hiệu
    
    Args:
        df_with_signals (pd.DataFrame): DataFrame với tín hiệu giao dịch
        symbol (str): Ký hiệu cặp tiền
        timeframe (str): Khung thời gian
        
    Returns:
        dict: Kết quả backtest
    """
    logger.info(f"Chạy backtest cho {symbol} ({timeframe})")
    
    # Khởi tạo các biến
    equity = 10000.0  # Vốn ban đầu
    initial_equity = equity
    position = None  # 'long', 'short', hoặc None
    entry_price = 0.0
    position_size = 0.02  # Mặc định 2% vốn
    stop_loss = 0.0
    take_profit = 0.0
    
    trades = []  # Danh sách giao dịch
    df_backtest = df_with_signals.copy()
    df_backtest['equity'] = initial_equity
    
    # Vòng lặp qua từng nến
    for i in range(len(df_backtest)):
        current_bar = df_backtest.iloc[i]
        current_index = df_backtest.index[i]
        
        # Cập nhật equity
        if i > 0:
            df_backtest.loc[df_backtest.index[i], 'equity'] = equity
        
        # Xử lý vị thế hiện tại
        if position == 'long':
            # Kiểm tra SL
            if current_bar['low'] <= stop_loss:
                pnl_pct = (stop_loss / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                position = None
            
            # Kiểm tra TP
            elif current_bar['high'] >= take_profit:
                pnl_pct = (take_profit / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': take_profit,
                    'exit_reason': 'take_profit',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                position = None
            
            # Kiểm tra tín hiệu thoát
            elif current_bar['final_sell_signal']:
                pnl_pct = (current_bar['close'] / entry_price - 1) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': current_bar['close'],
                    'exit_reason': 'signal',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                position = None
        
        elif position == 'short':
            # Kiểm tra SL
            if current_bar['high'] >= stop_loss:
                pnl_pct = (1 - stop_loss / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': stop_loss,
                    'exit_reason': 'stop_loss',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                position = None
            
            # Kiểm tra TP
            elif current_bar['low'] <= take_profit:
                pnl_pct = (1 - take_profit / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': take_profit,
                    'exit_reason': 'take_profit',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
                })
                
                position = None
            
            # Kiểm tra tín hiệu thoát
            elif current_bar['final_buy_signal']:
                pnl_pct = (1 - current_bar['close'] / entry_price) * 100
                pnl_amount = equity * position_size * pnl_pct / 100
                equity += pnl_amount
                
                trades.append({
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'position': position,
                    'entry_date': entry_index,
                    'entry_price': entry_price,
                    'exit_date': current_index,
                    'exit_price': current_bar['close'],
                    'exit_reason': 'signal',
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount
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
                    position_size = 0.02 * current_bar['position_size_multiplier']
                else:
                    position_size = 0.02
                
                # Đặt SL và TP
                if 'buy_sl_price' in current_bar and 'buy_tp_price' in current_bar:
                    stop_loss = current_bar['buy_sl_price']
                    take_profit = current_bar['buy_tp_price']
                else:
                    # Mặc định: SL 2%, TP 4%
                    stop_loss = entry_price * 0.98
                    take_profit = entry_price * 1.04
            
            elif current_bar['final_sell_signal']:
                position = 'short'
                entry_price = current_bar['close']
                entry_index = current_index
                
                # Điều chỉnh kích thước vị thế
                if 'position_size_multiplier' in current_bar:
                    position_size = 0.02 * current_bar['position_size_multiplier']
                else:
                    position_size = 0.02
                
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
    
    winning_trades = [t for t in trades if t['pnl_amount'] > 0]
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    
    total_profit = sum([t['pnl_amount'] for t in winning_trades])
    total_loss = abs(sum([t['pnl_amount'] for t in trades if t['pnl_amount'] < 0]))
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
    
    # Tính drawdown
    cumulative_returns = (df_backtest['equity'] / initial_equity)
    running_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns / running_max - 1) * 100
    max_drawdown_pct = abs(drawdown.min())
    
    # Thêm thống kê theo ngày/tháng
    monthly_returns = []
    if len(df_backtest) > 0:
        # Chuyển đổi equity thành lợi nhuận hàng tháng
        df_backtest['month'] = df_backtest.index.to_period('M')
        monthly_equity = df_backtest.groupby('month')['equity'].last()
        
        prev_equity = initial_equity
        for month, eq in monthly_equity.items():
            monthly_return = (eq / prev_equity - 1) * 100
            monthly_returns.append({
                'month': str(month),
                'return_pct': monthly_return
            })
            prev_equity = eq
    
    # Kết quả backtest
    results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': total_trades - len(winning_trades),
        'win_rate': win_rate,
        'profit_pct': profit_pct,
        'profit_amount': equity - initial_equity,
        'profit_factor': profit_factor,
        'max_drawdown_pct': max_drawdown_pct,
        'final_equity': equity,
        'monthly_returns': monthly_returns,
        'trades': trades
    }
    
    logger.info(f"Kết quả backtest cho {symbol} ({timeframe}):")
    logger.info(f"Tổng số giao dịch: {total_trades}")
    logger.info(f"Win rate: {win_rate:.2f}%")
    logger.info(f"Lợi nhuận: {profit_pct:.2f}%")
    logger.info(f"Max drawdown: {max_drawdown_pct:.2f}%")
    
    return results


def save_chart(df, symbol, timeframe, backtest_results):
    """
    Lưu biểu đồ phân tích
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu và tín hiệu
        symbol (str): Ký hiệu cặp tiền
        timeframe (str): Khung thời gian
        backtest_results (dict): Kết quả backtest
    """
    # Tạo thư mục nếu chưa tồn tại
    symbol_folder = os.path.join('test_results/multi_coin', symbol.replace('/', '_'))
    os.makedirs(symbol_folder, exist_ok=True)
    
    try:
        # Chỉ hiển thị 200 nến gần nhất
        display_df = df.iloc[-200:].copy() if len(df) > 200 else df.copy()
        
        plt.figure(figsize=(14, 10))
        
        # Biểu đồ giá và tín hiệu
        ax1 = plt.subplot(3, 1, 1)
        ax1.set_title(f'{symbol} ({timeframe}) - Giá và Tín Hiệu Giao Dịch')
        
        # Vẽ giá
        ax1.plot(display_df.index, display_df['close'], color='blue', label='Giá đóng cửa')
        
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
        
        ax1.legend(loc='upper left')
        ax1.grid(True)
        
        # Biểu đồ RSI và Stochastic
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
        
        # Biểu đồ equity
        ax3 = plt.subplot(3, 1, 3)
        
        profit = backtest_results['profit_pct']
        drawdown = backtest_results['max_drawdown_pct']
        win_rate = backtest_results['win_rate']
        
        ax3.set_title(f'Equity (Lợi nhuận: {profit:.2f}%, DD: {drawdown:.2f}%, WR: {win_rate:.2f}%)')
        
        if 'equity' in display_df.columns:
            ax3.plot(display_df.index, display_df['equity'], color='green')
        
        ax3.grid(True)
        
        plt.tight_layout()
        plt.savefig(f'{symbol_folder}/{timeframe}_chart.png')
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ cho {symbol} ({timeframe})")
    
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ cho {symbol} ({timeframe}): {str(e)}")


def calculate_summary(details):
    """
    Tính toán tổng hợp từ kết quả chi tiết
    
    Args:
        details (dict): Kết quả chi tiết theo cặp tiền và khung thời gian
        
    Returns:
        dict: Tổng hợp kết quả
    """
    # Khởi tạo biến tổng hợp
    all_trades = []
    total_profit = 0.0
    max_drawdown = 0.0
    
    # Tổng hợp theo symbol và timeframe
    symbol_summaries = {}
    timeframe_summaries = {}
    
    for symbol, timeframes in details.items():
        symbol_trades = []
        symbol_profit = 0.0
        symbol_drawdown = 0.0
        
        for timeframe, results in timeframes.items():
            # Thêm vào tổng hợp chung
            all_trades.extend(results['trades'])
            total_profit += results['profit_amount']
            max_drawdown = max(max_drawdown, results['max_drawdown_pct'])
            
            # Thêm vào tổng hợp symbol
            symbol_trades.extend(results['trades'])
            symbol_profit += results['profit_amount']
            symbol_drawdown = max(symbol_drawdown, results['max_drawdown_pct'])
            
            # Cập nhật tổng hợp timeframe
            if timeframe not in timeframe_summaries:
                timeframe_summaries[timeframe] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'profit_amount': 0.0,
                    'max_drawdown_pct': 0.0
                }
            
            timeframe_summaries[timeframe]['total_trades'] += results['total_trades']
            timeframe_summaries[timeframe]['winning_trades'] += results['winning_trades']
            timeframe_summaries[timeframe]['profit_amount'] += results['profit_amount']
            timeframe_summaries[timeframe]['max_drawdown_pct'] = max(
                timeframe_summaries[timeframe]['max_drawdown_pct'], 
                results['max_drawdown_pct']
            )
        
        # Lưu tổng hợp symbol
        symbol_winning_trades = sum(1 for t in symbol_trades if t['pnl_amount'] > 0)
        symbol_win_rate = symbol_winning_trades / len(symbol_trades) * 100 if symbol_trades else 0
        
        symbol_summaries[symbol] = {
            'total_trades': len(symbol_trades),
            'winning_trades': symbol_winning_trades,
            'win_rate': symbol_win_rate,
            'profit_amount': symbol_profit,
            'max_drawdown_pct': symbol_drawdown
        }
    
    # Hoàn thiện tổng hợp timeframe
    for timeframe, summary in timeframe_summaries.items():
        summary['win_rate'] = summary['winning_trades'] / summary['total_trades'] * 100 if summary['total_trades'] > 0 else 0
    
    # Tổng hợp chung
    winning_trades = sum(1 for t in all_trades if t['pnl_amount'] > 0)
    
    overall = {
        'total_trades': len(all_trades),
        'winning_trades': winning_trades,
        'win_rate': winning_trades / len(all_trades) * 100 if all_trades else 0,
        'profit_amount': total_profit,
        'max_drawdown_pct': max_drawdown
    }
    
    # Kết quả tổng hợp
    summary = {
        'overall': overall,
        'by_symbol': symbol_summaries,
        'by_timeframe': timeframe_summaries
    }
    
    return summary


def create_summary_report(results, timestamp):
    """
    Tạo báo cáo tổng hợp
    
    Args:
        results (dict): Kết quả kiểm thử
        timestamp (str): Thời gian tạo báo cáo
    """
    summary = results['summary']
    details = results['details']
    
    # Tạo báo cáo MD
    report_path = f'test_results/multi_coin/report_{timestamp}.md'
    
    with open(report_path, 'w') as f:
        # Tiêu đề
        f.write(f"# Báo Cáo Kiểm Thử Đa Coin\n\n")
        f.write(f"*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Tổng hợp chung
        f.write("## Tổng Hợp Chung\n\n")
        
        overall = summary['overall']
        f.write(f"- **Tổng số giao dịch:** {overall['total_trades']}\n")
        f.write(f"- **Tỷ lệ thắng:** {overall['win_rate']:.2f}%\n")
        f.write(f"- **Lợi nhuận:** ${overall['profit_amount']:.2f}\n")
        f.write(f"- **Drawdown tối đa:** {overall['max_drawdown_pct']:.2f}%\n\n")
        
        # Biểu đồ so sánh theo cặp tiền
        create_comparison_charts(summary, timestamp)
        
        # Báo cáo theo cặp tiền
        f.write("## Kết Quả Theo Coin\n\n")
        
        for symbol, symbol_summary in summary['by_symbol'].items():
            f.write(f"### {symbol}\n\n")
            f.write(f"- **Tổng số giao dịch:** {symbol_summary['total_trades']}\n")
            f.write(f"- **Tỷ lệ thắng:** {symbol_summary['win_rate']:.2f}%\n")
            f.write(f"- **Lợi nhuận:** ${symbol_summary['profit_amount']:.2f}\n")
            f.write(f"- **Drawdown tối đa:** {symbol_summary['max_drawdown_pct']:.2f}%\n\n")
            
            # Kết quả theo khung thời gian
            f.write("| Khung Thời Gian | Giao Dịch | Tỷ Lệ Thắng | Lợi Nhuận | Drawdown |\n")
            f.write("|-----------------|-----------|-------------|-----------|----------|\n")
            
            for timeframe, timeframe_results in details[symbol].items():
                f.write(f"| {timeframe} | {timeframe_results['total_trades']} | {timeframe_results['win_rate']:.2f}% | ${timeframe_results['profit_amount']:.2f} | {timeframe_results['max_drawdown_pct']:.2f}% |\n")
            
            f.write("\n")
        
        # Báo cáo theo khung thời gian
        f.write("## Kết Quả Theo Khung Thời Gian\n\n")
        
        for timeframe, timeframe_summary in summary['by_timeframe'].items():
            f.write(f"### {timeframe}\n\n")
            f.write(f"- **Tổng số giao dịch:** {timeframe_summary['total_trades']}\n")
            f.write(f"- **Tỷ lệ thắng:** {timeframe_summary['win_rate']:.2f}%\n")
            f.write(f"- **Lợi nhuận:** ${timeframe_summary['profit_amount']:.2f}\n")
            f.write(f"- **Drawdown tối đa:** {timeframe_summary['max_drawdown_pct']:.2f}%\n\n")
        
        # Kết luận
        f.write("## Kết Luận\n\n")
        
        # Tìm cặp tiền và khung thời gian có hiệu suất tốt nhất
        best_symbol = max(summary['by_symbol'].items(), key=lambda x: x[1]['profit_amount'])
        best_timeframe = max(summary['by_timeframe'].items(), key=lambda x: x[1]['profit_amount'])
        
        f.write(f"- **Coin hiệu quả nhất:** {best_symbol[0]} (${best_symbol[1]['profit_amount']:.2f})\n")
        f.write(f"- **Khung thời gian hiệu quả nhất:** {best_timeframe[0]} (${best_timeframe[1]['profit_amount']:.2f})\n\n")
        
        # Đánh giá rủi ro
        avg_win_rate = sum(s['win_rate'] for s in summary['by_symbol'].values()) / len(summary['by_symbol'])
        f.write(f"- **Tỷ lệ thắng trung bình:** {avg_win_rate:.2f}%\n")
        f.write(f"- **Đánh giá rủi ro:** Drawdown tối đa {overall['max_drawdown_pct']:.2f}%\n\n")
        
        # Biểu đồ
        f.write("## Biểu Đồ Phân Tích\n\n")
        f.write("Xem các biểu đồ chi tiết trong thư mục `test_results/multi_coin/`\n\n")
    
    logger.info(f"Đã tạo báo cáo tổng hợp: {report_path}")


def create_comparison_charts(summary, timestamp):
    """
    Tạo biểu đồ so sánh kết quả
    
    Args:
        summary (dict): Tổng hợp kết quả
        timestamp (str): Thời gian tạo báo cáo
    """
    # So sánh theo cặp tiền
    symbols = list(summary['by_symbol'].keys())
    profits = [s['profit_amount'] for s in summary['by_symbol'].values()]
    win_rates = [s['win_rate'] for s in summary['by_symbol'].values()]
    drawdowns = [s['max_drawdown_pct'] for s in summary['by_symbol'].values()]
    
    # Biểu đồ lợi nhuận theo coin
    plt.figure(figsize=(12, 6))
    plt.bar(symbols, profits, color='green')
    plt.title('Lợi Nhuận Theo Coin')
    plt.ylabel('Lợi Nhuận ($)')
    plt.grid(axis='y')
    
    for i, v in enumerate(profits):
        plt.text(i, v + 1, f"${v:.1f}", ha='center')
    
    plt.tight_layout()
    plt.savefig(f'test_results/multi_coin/profits_by_symbol_{timestamp}.png')
    plt.close()
    
    # Biểu đồ win rate theo coin
    plt.figure(figsize=(12, 6))
    plt.bar(symbols, win_rates, color='blue')
    plt.title('Tỷ Lệ Thắng Theo Coin')
    plt.ylabel('Win Rate (%)')
    plt.grid(axis='y')
    plt.ylim(0, 100)
    
    for i, v in enumerate(win_rates):
        plt.text(i, v + 1, f"{v:.1f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig(f'test_results/multi_coin/win_rates_by_symbol_{timestamp}.png')
    plt.close()
    
    # So sánh theo khung thời gian
    timeframes = list(summary['by_timeframe'].keys())
    tf_profits = [t['profit_amount'] for t in summary['by_timeframe'].values()]
    tf_win_rates = [t['win_rate'] for t in summary['by_timeframe'].values()]
    
    # Biểu đồ lợi nhuận theo khung thời gian
    plt.figure(figsize=(10, 6))
    plt.bar(timeframes, tf_profits, color='purple')
    plt.title('Lợi Nhuận Theo Khung Thời Gian')
    plt.ylabel('Lợi Nhuận ($)')
    plt.grid(axis='y')
    
    for i, v in enumerate(tf_profits):
        plt.text(i, v + 1, f"${v:.1f}", ha='center')
    
    plt.tight_layout()
    plt.savefig(f'test_results/multi_coin/profits_by_timeframe_{timestamp}.png')
    plt.close()
    
    # Ma trận hiệu suất
    if len(symbols) > 1 and len(timeframes) > 1:
        # Tạo ma trận hiệu suất
        performance_matrix = pd.DataFrame(index=symbols, columns=timeframes)
        
        # Điền dữ liệu
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    profit = summary['details'][symbol][timeframe]['profit_amount']
                    performance_matrix.loc[symbol, timeframe] = profit
                except:
                    performance_matrix.loc[symbol, timeframe] = 0
        
        # Vẽ heatmap
        plt.figure(figsize=(12, 8))
        ax = plt.subplot(111)
        
        # Dùng coolwarm colormap: đỏ cho âm, xanh cho dương
        cmap = plt.cm.coolwarm
        im = ax.imshow(performance_matrix.values, cmap=cmap)
        
        # Đặt tên trục
        ax.set_xticks(np.arange(len(timeframes)))
        ax.set_yticks(np.arange(len(symbols)))
        ax.set_xticklabels(timeframes)
        ax.set_yticklabels(symbols)
        
        # Hiển thị giá trị
        for i in range(len(symbols)):
            for j in range(len(timeframes)):
                value = performance_matrix.iloc[i, j]
                text_color = 'white' if abs(value) > 100 else 'black'
                ax.text(j, i, f"${value:.1f}", ha="center", va="center", color=text_color)
        
        plt.colorbar(im, label='Lợi Nhuận ($)')
        plt.title('Ma Trận Hiệu Suất: Coin vs. Khung Thời Gian')
        plt.tight_layout()
        plt.savefig(f'test_results/multi_coin/performance_matrix_{timestamp}.png')
        plt.close()
    
    logger.info("Đã tạo các biểu đồ so sánh")


if __name__ == "__main__":
    # Danh sách coin cần kiểm thử
    symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
    
    # Khung thời gian
    timeframes = ['1h', '4h', '1d']
    
    # Chạy kiểm thử
    results = run_multi_coin_test(symbols, timeframes, test_period=90)
    
    logger.info("Hoàn thành kiểm thử đa coin")