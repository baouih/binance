#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module kiểm thử thị trường đầy đủ

Module này sử dụng dữ liệu thực từ API Binance để thực hiện
kiểm thử căng thẳng trên nhiều cặp tiền, khung thời gian và mức rủi ro.
Đặc biệt tập trung vào mức rủi ro cao theo yêu cầu (1-4%).
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from enhanced_signal_generator import EnhancedSignalGenerator

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/full_market_test.log')
    ]
)

logger = logging.getLogger('full_market_test')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)
os.makedirs('full_test_results', exist_ok=True)


def fetch_all_futures_coins():
    """
    Lấy danh sách tất cả các cặp tiền có sẵn trên thị trường futures
    
    Returns:
        list: Danh sách các cặp tiền
    """
    try:
        # Khởi tạo exchange Binance
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # Sử dụng thị trường futures
            }
        })
        
        # Lấy danh sách thị trường
        markets = exchange.load_markets()
        
        # Lọc để lấy các cặp USDT
        usdt_pairs = [symbol for symbol in markets.keys() if symbol.endswith('/USDT')]
        
        logger.info(f"Đã tìm thấy {len(usdt_pairs)} cặp USDT trên Binance Futures")
        
        return usdt_pairs
    
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách coin: {str(e)}")
        
        # Sử dụng danh sách cố định nếu không thể lấy từ API
        default_pairs = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT',
            'XRP/USDT', 'DOGE/USDT', 'DOT/USDT', 'LTC/USDT', 'LINK/USDT',
            'AVAX/USDT', 'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'ETC/USDT',
            'NEAR/USDT', 'TRX/USDT', 'ICP/USDT', 'BCH/USDT', 'FIL/USDT'
        ]
        
        logger.info(f"Sử dụng danh sách cố định với {len(default_pairs)} cặp tiền")
        return default_pairs


def fetch_historical_data(symbol, timeframe='1h', start_date=None, end_date=None, limit=1500):
    """
    Lấy dữ liệu lịch sử từ Binance
    
    Args:
        symbol (str): Cặp tiền tệ (ví dụ: 'BTC/USDT')
        timeframe (str): Khung thời gian (ví dụ: '1h', '4h', '1d')
        start_date (datetime): Ngày bắt đầu
        end_date (datetime): Ngày kết thúc
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
        logger.error(f"Lỗi khi lấy dữ liệu cho {symbol} ({timeframe}): {str(e)}")
        return None


def backtest_with_real_data(df, risk_level, symbol, timeframe):
    """
    Thực hiện backtest với dữ liệu thực và mức rủi ro cụ thể
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu OHLCV
        risk_level (float): Mức rủi ro (tỷ lệ phần trăm vốn cho mỗi giao dịch)
        symbol (str): Cặp tiền
        timeframe (str): Khung thời gian
        
    Returns:
        dict: Kết quả backtest
    """
    if df is None or len(df) < 100:
        logger.warning(f"Không đủ dữ liệu cho {symbol} ({timeframe}) để thực hiện backtest")
        return None
    
    # Khởi tạo EnhancedSignalGenerator
    signal_generator = EnhancedSignalGenerator()
    
    # Xử lý dữ liệu và tạo tín hiệu
    try:
        df_with_signals = signal_generator.process_data(df, base_position_size=risk_level)
        
        # Thực hiện backtest
        initial_equity = 10000.0
        equity = initial_equity
        position = None
        entry_price = 0.0
        entry_index = None
        position_size = risk_level
        stop_loss = 0.0
        take_profit = 0.0
        
        trades = []
        df_backtest = df_with_signals.copy()
        
        # Theo dõi equity
        equity_curve = [initial_equity]
        
        # Vòng lặp qua từng nến
        for i in range(1, len(df_backtest)):
            current_bar = df_backtest.iloc[i]
            current_index = df_backtest.index[i]
            prev_bar = df_backtest.iloc[i-1]
            
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
                        'symbol': symbol,
                        'timeframe': timeframe,
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
                elif prev_bar['final_sell_signal']:
                    pnl_pct = (current_bar['open'] / entry_price - 1) * 100
                    pnl_amount = equity * position_size * pnl_pct / 100
                    equity += pnl_amount
                    
                    trades.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'position': position,
                        'entry_date': entry_index,
                        'entry_price': entry_price,
                        'exit_date': current_index,
                        'exit_price': current_bar['open'],
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
                        'symbol': symbol,
                        'timeframe': timeframe,
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
                        'symbol': symbol,
                        'timeframe': timeframe,
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
                elif prev_bar['final_buy_signal']:
                    pnl_pct = (1 - current_bar['open'] / entry_price) * 100
                    pnl_amount = equity * position_size * pnl_pct / 100
                    equity += pnl_amount
                    
                    trades.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'position': position,
                        'entry_date': entry_index,
                        'entry_price': entry_price,
                        'exit_date': current_index,
                        'exit_price': current_bar['open'],
                        'exit_reason': 'signal',
                        'pnl_pct': pnl_pct,
                        'pnl_amount': pnl_amount,
                        'risk_level': risk_level
                    })
                    
                    position = None
            
            # Kiểm tra tín hiệu mới nếu không có vị thế
            if position is None:
                if prev_bar['final_buy_signal']:
                    position = 'long'
                    entry_price = current_bar['open']
                    entry_index = current_index
                    
                    # Điều chỉnh kích thước vị thế nếu có
                    if 'position_size_multiplier' in prev_bar:
                        position_size = risk_level * prev_bar['position_size_multiplier']
                    else:
                        position_size = risk_level
                    
                    # Đặt SL và TP
                    if 'buy_sl_price' in prev_bar and 'buy_tp_price' in prev_bar:
                        # Điều chỉnh SL và TP theo giá mở cửa hiện tại
                        price_diff = current_bar['open'] / prev_bar['close']
                        stop_loss = prev_bar['buy_sl_price'] * price_diff
                        take_profit = prev_bar['buy_tp_price'] * price_diff
                    else:
                        # Mặc định: SL = 2%, TP = 4%
                        stop_loss = entry_price * 0.98
                        take_profit = entry_price * 1.04
                
                elif prev_bar['final_sell_signal']:
                    position = 'short'
                    entry_price = current_bar['open']
                    entry_index = current_index
                    
                    # Điều chỉnh kích thước vị thế
                    if 'position_size_multiplier' in prev_bar:
                        position_size = risk_level * prev_bar['position_size_multiplier']
                    else:
                        position_size = risk_level
                    
                    # Đặt SL và TP
                    if 'sell_sl_price' in prev_bar and 'sell_tp_price' in prev_bar:
                        # Điều chỉnh SL và TP theo giá mở cửa hiện tại
                        price_diff = current_bar['open'] / prev_bar['close']
                        stop_loss = prev_bar['sell_sl_price'] * price_diff
                        take_profit = prev_bar['sell_tp_price'] * price_diff
                    else:
                        stop_loss = entry_price * 1.02
                        take_profit = entry_price * 0.96
            
            # Thêm equity hiện tại vào đường cong
            equity_curve.append(equity)
        
        # Tính các metrics
        total_trades = len(trades)
        
        if total_trades == 0:
            logger.warning(f"Không có giao dịch nào cho {symbol} ({timeframe}) với mức rủi ro {risk_level}")
            return None
        
        profit_pct = (equity / initial_equity - 1) * 100
        
        winning_trades = [t for t in trades if t['pnl_amount'] > 0]
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        total_profit = sum([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
        total_loss = abs(sum([t['pnl_amount'] for t in trades if t['pnl_amount'] < 0]))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Tính drawdown
        peaks = pd.Series(equity_curve).cummax()
        drawdowns = (pd.Series(equity_curve) / peaks - 1) * 100
        max_drawdown_pct = abs(drawdowns.min())
        
        # Tính Sharpe Ratio
        equity_series = pd.Series(equity_curve)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 0 and returns.std() > 0 else 0
        
        # Tính Expected Payoff
        avg_win = np.mean([t['pnl_amount'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_amount'] for t in trades if t['pnl_amount'] < 0]) if total_trades - len(winning_trades) > 0 else 0
        expected_payoff = (win_rate/100 * avg_win) - ((100-win_rate)/100 * abs(avg_loss)) if avg_loss != 0 else 0
        
        # Kết quả
        results = {
            'symbol': symbol,
            'timeframe': timeframe,
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
            'avg_win': avg_win,
            'avg_loss': abs(avg_loss) if avg_loss != 0 else 0,
            'trades': trades,
            'equity_curve': equity_curve
        }
        
        logger.info(f"Kết quả backtest cho {symbol} ({timeframe}, risk={risk_level}):")
        logger.info(f"Trades: {total_trades}, Win Rate: {win_rate:.2f}%, Profit: {profit_pct:.2f}%, Drawdown: {max_drawdown_pct:.2f}%")
        
        return results
    
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện backtest cho {symbol} ({timeframe}): {str(e)}")
        return None


def process_symbol_timeframe(args):
    """
    Xử lý một cặp tiền và khung thời gian
    
    Args:
        args (tuple): (symbol, timeframe, risk_levels, days_back)
    
    Returns:
        dict: Kết quả kiểm thử
    """
    symbol, timeframe, risk_levels, days_back = args
    
    results = {}
    
    try:
        # Tính số ngày dữ liệu cần lấy
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Lấy dữ liệu
        df = fetch_historical_data(symbol, timeframe, start_date, end_date)
        
        if df is not None and len(df) >= 100:
            # Thực hiện backtest với từng mức rủi ro
            for risk_level in risk_levels:
                backtest_result = backtest_with_real_data(df, risk_level, symbol, timeframe)
                if backtest_result:
                    results[str(risk_level)] = backtest_result
        else:
            logger.warning(f"Không đủ dữ liệu cho {symbol} ({timeframe}) để thực hiện backtest")
    
    except Exception as e:
        logger.error(f"Lỗi khi xử lý {symbol} ({timeframe}): {str(e)}")
    
    return symbol, timeframe, results


def run_full_market_test(symbols=None, timeframes=None, risk_levels=None, days_back=90, max_workers=5):
    """
    Chạy kiểm thử toàn thị trường với dữ liệu thực
    
    Args:
        symbols (list): Danh sách các cặp tiền
        timeframes (list): Danh sách các khung thời gian
        risk_levels (list): Danh sách các mức rủi ro
        days_back (int): Số ngày dữ liệu để kiểm thử
        max_workers (int): Số luồng xử lý cùng lúc
    
    Returns:
        dict: Kết quả kiểm thử
    """
    # Lấy danh sách tất cả các cặp tiền nếu không được chỉ định
    if symbols is None:
        symbols = fetch_all_futures_coins()
        # Giới hạn số lượng cặp tiền để test
        if len(symbols) > 20:
            # Ưu tiên các cặp tiền lớn
            top_coins = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT']
            remaining_coins = [s for s in symbols if s not in top_coins]
            symbols = top_coins + remaining_coins[:20-len(top_coins)]
    
    # Khung thời gian mặc định
    if timeframes is None:
        timeframes = ['15m', '1h', '4h', '1d']
    
    # Mức rủi ro mặc định
    if risk_levels is None:
        risk_levels = [0.01, 0.02, 0.025, 0.03, 0.035, 0.04]
    
    # Kết quả tổng hợp
    results = {
        'summary': {},
        'by_symbol': {},
        'by_timeframe': {},
        'by_risk_level': {},
        'best_combinations': []
    }
    
    # Lưu cấu hình test
    results['config'] = {
        'symbols': symbols,
        'timeframes': timeframes,
        'risk_levels': risk_levels,
        'days_back': days_back,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Chuẩn bị danh sách tham số
    args_list = [(symbol, timeframe, risk_levels, days_back) 
                for symbol in symbols 
                for timeframe in timeframes]
    
    # Theo dõi tiến trình
    total_tasks = len(args_list)
    completed_tasks = 0
    lock = threading.Lock()
    
    def update_progress():
        nonlocal completed_tasks
        with lock:
            completed_tasks += 1
            progress = completed_tasks / total_tasks * 100
            sys.stdout.write(f"\rTiến trình: {completed_tasks}/{total_tasks} ({progress:.1f}%)")
            sys.stdout.flush()
    
    # Chạy xử lý song song
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_args = {executor.submit(process_symbol_timeframe, args): args for args in args_list}
        
        for future in as_completed(future_to_args):
            try:
                symbol, timeframe, result = future.result()
                
                if result:
                    # Lưu kết quả
                    if symbol not in results['by_symbol']:
                        results['by_symbol'][symbol] = {}
                    
                    results['by_symbol'][symbol][timeframe] = result
                    
                    # Cập nhật kết quả theo khung thời gian
                    if timeframe not in results['by_timeframe']:
                        results['by_timeframe'][timeframe] = {}
                    
                    results['by_timeframe'][timeframe][symbol] = result
                    
                    # Cập nhật kết quả theo mức rủi ro
                    for risk_level, risk_result in result.items():
                        if risk_level not in results['by_risk_level']:
                            results['by_risk_level'][risk_level] = {}
                        
                        if symbol not in results['by_risk_level'][risk_level]:
                            results['by_risk_level'][risk_level][symbol] = {}
                        
                        results['by_risk_level'][risk_level][symbol][timeframe] = risk_result
                
                update_progress()
                
            except Exception as e:
                logger.error(f"Lỗi khi xử lý kết quả: {str(e)}")
                update_progress()
    
    print("\nĐang tổng hợp kết quả kiểm thử...")
    
    # Tìm các kết hợp tốt nhất
    best_combinations = []
    
    for symbol, symbol_data in results['by_symbol'].items():
        for timeframe, timeframe_data in symbol_data.items():
            for risk_level, risk_result in timeframe_data.items():
                sharpe = risk_result.get('sharpe_ratio', 0)
                profit = risk_result.get('profit_pct', 0)
                drawdown = risk_result.get('max_drawdown_pct', float('inf'))
                
                if sharpe > 0.5 and profit > 0 and drawdown < 25:  
                    best_combinations.append({
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'risk_level': risk_level,
                        'sharpe_ratio': sharpe,
                        'profit_pct': profit,
                        'max_drawdown_pct': drawdown,
                        'win_rate': risk_result.get('win_rate', 0),
                        'trades': risk_result.get('total_trades', 0)
                    })
    
    # Sắp xếp theo sharpe ratio
    best_combinations.sort(key=lambda x: x['sharpe_ratio'], reverse=True)
    results['best_combinations'] = best_combinations[:20]  # Top 20
    
    # Tính toán tổng hợp chung
    calculate_summary_stats(results)
    
    # Lưu kết quả vào file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'full_test_results/full_market_results_{timestamp}.json', 'w') as f:
        # Xử lý các đối tượng datetime và numpy
        def json_serializer(obj):
            if isinstance(obj, (datetime, np.datetime64)):
                return obj.isoformat()
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        # Lưu kết quả đã lọc bỏ các dữ liệu lớn
        filtered_results = filter_results_for_saving(results)
        json.dump(filtered_results, f, indent=4, default=json_serializer)
    
    # Tạo báo cáo tổng hợp
    create_full_market_report(results, timestamp)
    
    # Tạo biểu đồ tổng hợp
    create_full_market_charts(results, timestamp)
    
    return results


def filter_results_for_saving(results):
    """
    Lọc bỏ các dữ liệu lớn (equity curve, danh sách giao dịch) trước khi lưu
    
    Args:
        results (dict): Kết quả kiểm thử
        
    Returns:
        dict: Kết quả đã lọc
    """
    filtered = {
        'summary': results['summary'],
        'config': results['config'],
        'best_combinations': results['best_combinations']
    }
    
    # Lọc kết quả theo symbol
    filtered['by_symbol'] = {}
    for symbol, symbol_data in results['by_symbol'].items():
        filtered['by_symbol'][symbol] = {}
        for timeframe, timeframe_data in symbol_data.items():
            filtered['by_symbol'][symbol][timeframe] = {}
            for risk_level, risk_result in timeframe_data.items():
                if isinstance(risk_result, dict):
                    filtered_result = {k: v for k, v in risk_result.items() 
                                      if k not in ['trades', 'equity_curve']}
                    filtered['by_symbol'][symbol][timeframe][risk_level] = filtered_result
    
    # Lọc kết quả theo timeframe và risk_level
    for section in ['by_timeframe', 'by_risk_level']:
        if section in results:
            filtered[section] = {}
            for key1, data1 in results[section].items():
                filtered[section][key1] = {}
                for key2, data2 in data1.items():
                    filtered[section][key1][key2] = {}
                    if isinstance(data2, dict):
                        if all(isinstance(v, dict) for v in data2.values()):
                            # Cấu trúc 3 cấp (risk_level -> symbol -> timeframe)
                            for key3, data3 in data2.items():
                                filtered[section][key1][key2][key3] = {k: v for k, v in data3.items() 
                                                                    if k not in ['trades', 'equity_curve']}
                        else:
                            # Cấu trúc 2 cấp (timeframe -> symbol hoặc symbol -> timeframe)
                            for key3, data3 in data2.items():
                                if isinstance(data3, dict):
                                    filtered[section][key1][key2][key3] = {k: v for k, v in data3.items() 
                                                                        if k not in ['trades', 'equity_curve']}
    
    return filtered


def calculate_summary_stats(results):
    """
    Tính toán các thống kê tổng hợp
    
    Args:
        results (dict): Kết quả kiểm thử
    """
    # Khởi tạo tổng hợp
    summary = {
        'total_tests': 0,
        'successful_tests': 0,
        'profitable_tests': 0,
        'avg_profit_pct': 0,
        'avg_drawdown_pct': 0,
        'avg_win_rate': 0,
        'avg_sharpe_ratio': 0,
        'by_symbol': {},
        'by_timeframe': {},
        'by_risk_level': {}
    }
    
    # Biến đếm
    total_profit = 0
    total_drawdown = 0
    total_win_rate = 0
    total_sharpe = 0
    count = 0
    
    # Theo dõi số lượng test theo symbol
    symbol_counts = {}
    timeframe_counts = {}
    risk_level_counts = {}
    
    # Tổng hợp theo symbol
    for symbol, symbol_data in results['by_symbol'].items():
        symbol_profits = []
        symbol_drawdowns = []
        symbol_win_rates = []
        symbol_sharpes = []
        
        for timeframe, timeframe_data in symbol_data.items():
            for risk_level, risk_result in timeframe_data.items():
                profit = risk_result.get('profit_pct', 0)
                drawdown = risk_result.get('max_drawdown_pct', 0)
                win_rate = risk_result.get('win_rate', 0)
                sharpe = risk_result.get('sharpe_ratio', 0)
                
                # Cập nhật tổng
                total_profit += profit
                total_drawdown += drawdown
                total_win_rate += win_rate
                total_sharpe += sharpe
                
                # Cập nhật theo symbol
                symbol_profits.append(profit)
                symbol_drawdowns.append(drawdown)
                symbol_win_rates.append(win_rate)
                symbol_sharpes.append(sharpe)
                
                # Tăng đếm
                count += 1
                
                # Theo dõi symbol
                if symbol not in symbol_counts:
                    symbol_counts[symbol] = 0
                symbol_counts[symbol] += 1
                
                # Theo dõi timeframe
                if timeframe not in timeframe_counts:
                    timeframe_counts[timeframe] = 0
                timeframe_counts[timeframe] += 1
                
                # Theo dõi risk_level
                if risk_level not in risk_level_counts:
                    risk_level_counts[risk_level] = 0
                risk_level_counts[risk_level] += 1
                
                # Đếm test thành công
                summary['successful_tests'] += 1
                
                # Đếm test có lợi nhuận
                if profit > 0:
                    summary['profitable_tests'] += 1
        
        # Tính trung bình cho mỗi symbol
        if symbol_profits:
            summary['by_symbol'][symbol] = {
                'avg_profit_pct': sum(symbol_profits) / len(symbol_profits),
                'avg_drawdown_pct': sum(symbol_drawdowns) / len(symbol_drawdowns),
                'avg_win_rate': sum(symbol_win_rates) / len(symbol_win_rates),
                'avg_sharpe_ratio': sum(symbol_sharpes) / len(symbol_sharpes),
                'test_count': len(symbol_profits),
                'profitable_count': sum(1 for p in symbol_profits if p > 0)
            }
    
    # Tổng hợp theo timeframe
    for timeframe, timeframe_data in results.get('by_timeframe', {}).items():
        timeframe_profits = []
        timeframe_drawdowns = []
        timeframe_win_rates = []
        timeframe_sharpes = []
        
        for symbol, symbol_data in timeframe_data.items():
            for risk_level, risk_result in symbol_data.items():
                profit = risk_result.get('profit_pct', 0)
                drawdown = risk_result.get('max_drawdown_pct', 0)
                win_rate = risk_result.get('win_rate', 0)
                sharpe = risk_result.get('sharpe_ratio', 0)
                
                # Cập nhật theo timeframe
                timeframe_profits.append(profit)
                timeframe_drawdowns.append(drawdown)
                timeframe_win_rates.append(win_rate)
                timeframe_sharpes.append(sharpe)
        
        # Tính trung bình cho mỗi timeframe
        if timeframe_profits:
            summary['by_timeframe'][timeframe] = {
                'avg_profit_pct': sum(timeframe_profits) / len(timeframe_profits),
                'avg_drawdown_pct': sum(timeframe_drawdowns) / len(timeframe_drawdowns),
                'avg_win_rate': sum(timeframe_win_rates) / len(timeframe_win_rates),
                'avg_sharpe_ratio': sum(timeframe_sharpes) / len(timeframe_sharpes),
                'test_count': len(timeframe_profits),
                'profitable_count': sum(1 for p in timeframe_profits if p > 0)
            }
    
    # Tổng hợp theo risk_level
    for risk_level, risk_data in results.get('by_risk_level', {}).items():
        risk_profits = []
        risk_drawdowns = []
        risk_win_rates = []
        risk_sharpes = []
        
        for symbol, symbol_data in risk_data.items():
            for timeframe, timeframe_data in symbol_data.items():
                profit = timeframe_data.get('profit_pct', 0)
                drawdown = timeframe_data.get('max_drawdown_pct', 0)
                win_rate = timeframe_data.get('win_rate', 0)
                sharpe = timeframe_data.get('sharpe_ratio', 0)
                
                # Cập nhật theo risk_level
                risk_profits.append(profit)
                risk_drawdowns.append(drawdown)
                risk_win_rates.append(win_rate)
                risk_sharpes.append(sharpe)
        
        # Tính trung bình cho mỗi risk_level
        if risk_profits:
            summary['by_risk_level'][risk_level] = {
                'avg_profit_pct': sum(risk_profits) / len(risk_profits),
                'avg_drawdown_pct': sum(risk_drawdowns) / len(risk_drawdowns),
                'avg_win_rate': sum(risk_win_rates) / len(risk_win_rates),
                'avg_sharpe_ratio': sum(risk_sharpes) / len(risk_sharpes),
                'test_count': len(risk_profits),
                'profitable_count': sum(1 for p in risk_profits if p > 0)
            }
    
    # Tính trung bình tổng thể
    if count > 0:
        summary['avg_profit_pct'] = total_profit / count
        summary['avg_drawdown_pct'] = total_drawdown / count
        summary['avg_win_rate'] = total_win_rate / count
        summary['avg_sharpe_ratio'] = total_sharpe / count
    
    # Tổng số test
    summary['total_tests'] = sum(symbol_counts.values())
    
    # Cập nhật kết quả
    results['summary'] = summary


def create_full_market_report(results, timestamp):
    """
    Tạo báo cáo tổng hợp cho kiểm thử toàn thị trường
    
    Args:
        results (dict): Kết quả kiểm thử
        timestamp (str): Timestamp
    """
    report_path = f'full_test_results/full_market_report_{timestamp}.md'
    
    with open(report_path, 'w') as f:
        # Tiêu đề
        f.write('# Báo Cáo Kiểm Thử Toàn Thị Trường\n\n')
        f.write(f"*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        
        # Cấu hình
        f.write('## Cấu Hình Kiểm Thử\n\n')
        f.write(f"- **Số cặp tiền tệ:** {len(results['config']['symbols'])}\n")
        f.write(f"- **Khung thời gian:** {', '.join(results['config']['timeframes'])}\n")
        f.write(f"- **Mức rủi ro:** {', '.join(map(str, results['config']['risk_levels']))}\n")
        f.write(f"- **Số ngày dữ liệu:** {results['config']['days_back']}\n\n")
        
        # Tổng quan
        f.write('## Tổng Quan\n\n')
        
        summary = results['summary']
        f.write(f"- **Tổng số kiểm thử:** {summary['total_tests']}\n")
        f.write(f"- **Số kiểm thử thành công:** {summary['successful_tests']} ({summary['successful_tests']/summary['total_tests']*100 if summary['total_tests'] > 0 else 0:.2f}%)\n")
        f.write(f"- **Số kiểm thử có lợi nhuận:** {summary['profitable_tests']} ({summary['profitable_tests']/summary['successful_tests']*100 if summary['successful_tests'] > 0 else 0:.2f}%)\n")
        f.write(f"- **Lợi nhuận trung bình:** {summary['avg_profit_pct']:.2f}%\n")
        f.write(f"- **Drawdown trung bình:** {summary['avg_drawdown_pct']:.2f}%\n")
        f.write(f"- **Win rate trung bình:** {summary['avg_win_rate']:.2f}%\n")
        f.write(f"- **Sharpe ratio trung bình:** {summary['avg_sharpe_ratio']:.2f}\n\n")
        
        # Top 20 kết hợp tốt nhất
        f.write('## Top 20 Kết Hợp Hiệu Quả Nhất\n\n')
        f.write('| Cặp Tiền | Timeframe | Mức Rủi Ro | Sharpe Ratio | Lợi Nhuận | Drawdown | Win Rate | Giao Dịch |\n')
        f.write('|----------|-----------|------------|--------------|-----------|----------|----------|----------|\n')
        
        for combo in results['best_combinations']:
            f.write(f"| {combo['symbol']} | {combo['timeframe']} | {combo['risk_level']} | {combo['sharpe_ratio']:.2f} | {combo['profit_pct']:.2f}% | {combo['max_drawdown_pct']:.2f}% | {combo['win_rate']:.2f}% | {combo['trades']} |\n")
        
        f.write('\n')
        
        # Phân tích theo mức rủi ro
        f.write('## Phân Tích Theo Mức Rủi Ro\n\n')
        
        # Tạo bảng cho mức rủi ro
        f.write('| Mức Rủi Ro | Số Test | Tỷ Lệ Có Lợi Nhuận | Lợi Nhuận TB | Drawdown TB | Win Rate TB | Sharpe Ratio TB |\n')
        f.write('|------------|---------|-------------------|--------------|-------------|-------------|----------------|\n')
        
        risk_levels = sorted(summary['by_risk_level'].keys(), key=lambda x: float(x))
        
        for risk_level in risk_levels:
            risk_data = summary['by_risk_level'][risk_level]
            profit_ratio = risk_data['profitable_count'] / risk_data['test_count'] * 100 if risk_data['test_count'] > 0 else 0
            
            f.write(f"| {risk_level} | {risk_data['test_count']} | {profit_ratio:.2f}% | {risk_data['avg_profit_pct']:.2f}% | {risk_data['avg_drawdown_pct']:.2f}% | {risk_data['avg_win_rate']:.2f}% | {risk_data['avg_sharpe_ratio']:.2f} |\n")
        
        f.write('\n')
        
        # Phân tích theo khung thời gian
        f.write('## Phân Tích Theo Khung Thời Gian\n\n')
        
        # Tạo bảng cho khung thời gian
        f.write('| Khung Thời Gian | Số Test | Tỷ Lệ Có Lợi Nhuận | Lợi Nhuận TB | Drawdown TB | Win Rate TB | Sharpe Ratio TB |\n')
        f.write('|-----------------|---------|-------------------|--------------|-------------|-------------|----------------|\n')
        
        for timeframe in results['config']['timeframes']:
            if timeframe in summary['by_timeframe']:
                timeframe_data = summary['by_timeframe'][timeframe]
                profit_ratio = timeframe_data['profitable_count'] / timeframe_data['test_count'] * 100 if timeframe_data['test_count'] > 0 else 0
                
                f.write(f"| {timeframe} | {timeframe_data['test_count']} | {profit_ratio:.2f}% | {timeframe_data['avg_profit_pct']:.2f}% | {timeframe_data['avg_drawdown_pct']:.2f}% | {timeframe_data['avg_win_rate']:.2f}% | {timeframe_data['avg_sharpe_ratio']:.2f} |\n")
        
        f.write('\n')
        
        # Top 10 cặp tiền hiệu quả nhất
        f.write('## Top 10 Cặp Tiền Hiệu Quả Nhất\n\n')
        
        # Sắp xếp các cặp tiền theo lợi nhuận trung bình
        symbols_sorted = sorted(summary['by_symbol'].items(), key=lambda x: x[1]['avg_profit_pct'], reverse=True)
        
        # Tạo bảng cho cặp tiền
        f.write('| Cặp Tiền | Số Test | Tỷ Lệ Có Lợi Nhuận | Lợi Nhuận TB | Drawdown TB | Win Rate TB | Sharpe Ratio TB |\n')
        f.write('|----------|---------|-------------------|--------------|-------------|-------------|----------------|\n')
        
        for symbol, symbol_data in symbols_sorted[:10]:
            profit_ratio = symbol_data['profitable_count'] / symbol_data['test_count'] * 100 if symbol_data['test_count'] > 0 else 0
            
            f.write(f"| {symbol} | {symbol_data['test_count']} | {profit_ratio:.2f}% | {symbol_data['avg_profit_pct']:.2f}% | {symbol_data['avg_drawdown_pct']:.2f}% | {symbol_data['avg_win_rate']:.2f}% | {symbol_data['avg_sharpe_ratio']:.2f} |\n")
        
        f.write('\n')
        
        # Phân tích chi tiết mức rủi ro tốt nhất
        f.write('## Phân Tích Chi Tiết Mức Rủi Ro Tốt Nhất\n\n')
        
        # Tìm mức rủi ro tốt nhất dựa trên sharpe ratio
        best_risk = max(summary['by_risk_level'].items(), key=lambda x: x[1]['avg_sharpe_ratio'])
        
        f.write(f"Dựa trên kết quả kiểm thử, mức rủi ro tối ưu nhất là **{best_risk[0]}** với:\n\n")
        f.write(f"- Sharpe Ratio trung bình: {best_risk[1]['avg_sharpe_ratio']:.2f}\n")
        f.write(f"- Lợi nhuận trung bình: {best_risk[1]['avg_profit_pct']:.2f}%\n")
        f.write(f"- Drawdown trung bình: {best_risk[1]['avg_drawdown_pct']:.2f}%\n")
        f.write(f"- Win Rate trung bình: {best_risk[1]['avg_win_rate']:.2f}%\n\n")
        
        # Phân tích chi tiết khung thời gian tốt nhất
        f.write('## Phân Tích Chi Tiết Khung Thời Gian Tốt Nhất\n\n')
        
        # Tìm khung thời gian tốt nhất dựa trên sharpe ratio
        best_timeframe = max(summary['by_timeframe'].items(), key=lambda x: x[1]['avg_sharpe_ratio'])
        
        f.write(f"Dựa trên kết quả kiểm thử, khung thời gian tối ưu nhất là **{best_timeframe[0]}** với:\n\n")
        f.write(f"- Sharpe Ratio trung bình: {best_timeframe[1]['avg_sharpe_ratio']:.2f}\n")
        f.write(f"- Lợi nhuận trung bình: {best_timeframe[1]['avg_profit_pct']:.2f}%\n")
        f.write(f"- Drawdown trung bình: {best_timeframe[1]['avg_drawdown_pct']:.2f}%\n")
        f.write(f"- Win Rate trung bình: {best_timeframe[1]['avg_win_rate']:.2f}%\n\n")
        
        # Kết luận và khuyến nghị
        f.write('## Kết Luận và Khuyến Nghị\n\n')
        
        if results['best_combinations']:
            top_3 = results['best_combinations'][:3]
            
            f.write("### Khuyến Nghị Chính\n\n")
            f.write("Dựa trên kết quả kiểm thử toàn diện trên thị trường, chúng tôi khuyến nghị sử dụng các cấu hình sau:\n\n")
            
            for i, combo in enumerate(top_3):
                f.write(f"{i+1}. **{combo['symbol']}** ({combo['timeframe']}) với mức rủi ro **{combo['risk_level']}**\n")
                f.write(f"   - Sharpe Ratio: {combo['sharpe_ratio']:.2f}\n")
                f.write(f"   - Lợi nhuận: {combo['profit_pct']:.2f}%\n")
                f.write(f"   - Drawdown: {combo['max_drawdown_pct']:.2f}%\n")
                f.write(f"   - Win Rate: {combo['win_rate']:.2f}%\n\n")
                
            f.write(f"### Mức Rủi Ro Khuyến Nghị\n\n")
            f.write(f"Mức rủi ro tối ưu nhất là **{best_risk[0]}**, cung cấp sự cân bằng tốt giữa lợi nhuận và rủi ro. ")
            f.write("Đây là mức rủi ro được khuyến nghị cho phần lớn các giao dịch, đặc biệt khi giao dịch các cặp ")
            f.write(f"tiền thanh khoản cao trên khung thời gian **{best_timeframe[0]}**.\n\n")
            
            # Cảnh báo về các mức rủi ro cao
            high_risk_levels = [r for r in risk_levels if float(r) >= 0.03]
            if high_risk_levels:
                f.write("### Cảnh Báo Về Mức Rủi Ro Cao\n\n")
                f.write("Mức rủi ro từ 3% trở lên (3%, 3.5%, 4%) có thể mang lại lợi nhuận cao hơn ")
                f.write("nhưng cũng có drawdown lớn hơn đáng kể. Những mức rủi ro này chỉ nên được sử dụng ")
                f.write("bởi các trader có kinh nghiệm và trên các cặp tiền có thanh khoản cao.\n\n")
                
                # Phân tích drawdown theo từng mức rủi ro cao
                f.write("Phân tích drawdown cho các mức rủi ro cao:\n\n")
                
                for risk in high_risk_levels:
                    if risk in summary['by_risk_level']:
                        risk_data = summary['by_risk_level'][risk]
                        f.write(f"- **{risk}**: Drawdown trung bình {risk_data['avg_drawdown_pct']:.2f}%, ")
                        f.write(f"Lợi nhuận trung bình {risk_data['avg_profit_pct']:.2f}%\n")
                
                f.write("\n")
        
        # Phân tích tổng thể về hiệu suất của hệ thống
        f.write("### Đánh Giá Tổng Thể Hiệu Suất\n\n")
        f.write(f"Hệ thống tín hiệu nâng cao đã chứng minh hiệu quả tốt với ")
        f.write(f"{summary['profitable_tests']}/{summary['successful_tests']} kiểm thử có lợi nhuận ")
        f.write(f"({summary['profitable_tests']/summary['successful_tests']*100 if summary['successful_tests'] > 0 else 0:.2f}%). ")
        
        # Đánh giá win rate
        if summary['avg_win_rate'] > 60:
            f.write(f"Win rate trung bình {summary['avg_win_rate']:.2f}% là rất tốt, ")
            f.write("cho thấy hệ thống có độ chính xác cao trong việc dự đoán hướng di chuyển của thị trường. ")
        elif summary['avg_win_rate'] > 50:
            f.write(f"Win rate trung bình {summary['avg_win_rate']:.2f}% là khá tốt, ")
            f.write("cho thấy hệ thống có khả năng dự đoán hướng di chuyển của thị trường tốt hơn xác suất ngẫu nhiên. ")
        else:
            f.write(f"Win rate trung bình {summary['avg_win_rate']:.2f}% thấp hơn mong đợi, ")
            f.write("cho thấy cần cải thiện thêm độ chính xác của tín hiệu. ")
        
        # Đánh giá profit/drawdown
        profit_to_dd_ratio = summary['avg_profit_pct'] / summary['avg_drawdown_pct'] if summary['avg_drawdown_pct'] > 0 else float('inf')
        
        if profit_to_dd_ratio > 2:
            f.write(f"Tỷ lệ lợi nhuận/drawdown trung bình là {profit_to_dd_ratio:.2f}, rất tốt ")
            f.write("và cho thấy hệ thống có khả năng sinh lời cao so với rủi ro chịu đựng.\n\n")
        elif profit_to_dd_ratio > 1:
            f.write(f"Tỷ lệ lợi nhuận/drawdown trung bình là {profit_to_dd_ratio:.2f}, khá tốt ")
            f.write("và cho thấy hệ thống có lợi nhuận lớn hơn rủi ro chịu đựng.\n\n")
        else:
            f.write(f"Tỷ lệ lợi nhuận/drawdown trung bình là {profit_to_dd_ratio:.2f}, ")
            f.write("cần cải thiện để đảm bảo lợi nhuận tương xứng với rủi ro.\n\n")
        
        # Các biểu đồ phân tích
        f.write("## Biểu Đồ Phân Tích\n\n")
        f.write("Các biểu đồ phân tích chi tiết được lưu trong thư mục `full_test_results/`.\n\n")
    
    logger.info(f"Đã tạo báo cáo tổng hợp: {report_path}")


def create_full_market_charts(results, timestamp):
    """
    Tạo biểu đồ tổng hợp cho kết quả kiểm thử
    
    Args:
        results (dict): Kết quả kiểm thử
        timestamp (str): Timestamp
    """
    # 1. Biểu đồ tổng hợp lợi nhuận theo risk level
    risk_levels = sorted(results['summary']['by_risk_level'].keys(), key=lambda x: float(x))
    risk_profits = [results['summary']['by_risk_level'][r]['avg_profit_pct'] for r in risk_levels]
    risk_drawdowns = [results['summary']['by_risk_level'][r]['avg_drawdown_pct'] for r in risk_levels]
    risk_win_rates = [results['summary']['by_risk_level'][r]['avg_win_rate'] for r in risk_levels]
    risk_sharpes = [results['summary']['by_risk_level'][r]['avg_sharpe_ratio'] for r in risk_levels]
    
    # Biểu đồ lợi nhuận theo risk level
    plt.figure(figsize=(12, 8))
    plt.subplot(2, 1, 1)
    
    plt.bar(risk_levels, risk_profits, color='green', alpha=0.7)
    plt.title('Lợi Nhuận Trung Bình Theo Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Lợi Nhuận (%)')
    plt.grid(axis='y')
    
    for i, v in enumerate(risk_profits):
        plt.text(i, v + 0.5, f"{v:.2f}%", ha='center')
    
    plt.subplot(2, 1, 2)
    plt.bar(risk_levels, risk_drawdowns, color='red', alpha=0.7)
    plt.title('Drawdown Trung Bình Theo Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Drawdown (%)')
    plt.grid(axis='y')
    
    for i, v in enumerate(risk_drawdowns):
        plt.text(i, v + 0.5, f"{v:.2f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig(f'full_test_results/profit_drawdown_by_risk_{timestamp}.png')
    plt.close()
    
    # Biểu đồ sharpe ratio và win rate theo risk level
    plt.figure(figsize=(12, 8))
    plt.subplot(2, 1, 1)
    
    plt.bar(risk_levels, risk_sharpes, color='purple', alpha=0.7)
    plt.title('Sharpe Ratio Trung Bình Theo Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Sharpe Ratio')
    plt.grid(axis='y')
    
    for i, v in enumerate(risk_sharpes):
        plt.text(i, v + 0.05, f"{v:.2f}", ha='center')
    
    plt.subplot(2, 1, 2)
    plt.bar(risk_levels, risk_win_rates, color='blue', alpha=0.7)
    plt.title('Win Rate Trung Bình Theo Mức Rủi Ro')
    plt.xlabel('Mức Rủi Ro')
    plt.ylabel('Win Rate (%)')
    plt.grid(axis='y')
    
    for i, v in enumerate(risk_win_rates):
        plt.text(i, v + 0.5, f"{v:.2f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig(f'full_test_results/sharpe_winrate_by_risk_{timestamp}.png')
    plt.close()
    
    # 2. Biểu đồ theo timeframe
    timeframes = results['config']['timeframes']
    timeframe_profits = [results['summary']['by_timeframe'].get(t, {}).get('avg_profit_pct', 0) for t in timeframes]
    timeframe_sharpes = [results['summary']['by_timeframe'].get(t, {}).get('avg_sharpe_ratio', 0) for t in timeframes]
    
    plt.figure(figsize=(10, 6))
    plt.bar(timeframes, timeframe_profits, color='green', alpha=0.7)
    plt.title('Lợi Nhuận Trung Bình Theo Khung Thời Gian')
    plt.xlabel('Khung Thời Gian')
    plt.ylabel('Lợi Nhuận (%)')
    plt.grid(axis='y')
    
    for i, v in enumerate(timeframe_profits):
        plt.text(i, v + 0.5, f"{v:.2f}%", ha='center')
    
    plt.tight_layout()
    plt.savefig(f'full_test_results/profit_by_timeframe_{timestamp}.png')
    plt.close()
    
    # 3. Top 10 cặp tiền
    top_symbols = sorted(results['summary']['by_symbol'].items(), 
                         key=lambda x: x[1]['avg_profit_pct'], reverse=True)[:10]
    symbol_names = [s[0] for s in top_symbols]
    symbol_profits = [s[1]['avg_profit_pct'] for s in top_symbols]
    
    plt.figure(figsize=(12, 8))
    plt.barh(symbol_names, symbol_profits, color='blue', alpha=0.7)
    plt.title('Top 10 Cặp Tiền Theo Lợi Nhuận Trung Bình')
    plt.xlabel('Lợi Nhuận (%)')
    plt.ylabel('Cặp Tiền')
    plt.grid(axis='x')
    
    for i, v in enumerate(symbol_profits):
        plt.text(v + 0.5, i, f"{v:.2f}%", va='center')
    
    plt.tight_layout()
    plt.savefig(f'full_test_results/top10_symbols_{timestamp}.png')
    plt.close()
    
    # 4. Top 20 kết hợp
    if results['best_combinations']:
        plt.figure(figsize=(14, 10))
        
        combos = results['best_combinations'][:min(20, len(results['best_combinations']))]
        combo_labels = [f"{c['symbol']} ({c['timeframe']}, {c['risk_level']})" for c in combos]
        combo_sharpes = [c['sharpe_ratio'] for c in combos]
        
        plt.barh(range(len(combo_labels)), combo_sharpes, align='center')
        plt.yticks(range(len(combo_labels)), combo_labels)
        plt.xlabel('Sharpe Ratio')
        plt.title('Top Kết Hợp Theo Sharpe Ratio')
        plt.grid(axis='x')
        
        for i, v in enumerate(combo_sharpes):
            plt.text(v + 0.05, i, f"{v:.2f}", va='center')
        
        plt.tight_layout()
        plt.savefig(f'full_test_results/top_combinations_{timestamp}.png')
        plt.close()
    
    logger.info(f"Đã tạo các biểu đồ tổng hợp trong thư mục full_test_results/")


if __name__ == "__main__":
    # Danh sách các cặp tiền để test (để None để lấy tự động từ API)
    symbols = None
    
    # Khung thời gian (theo yêu cầu)
    timeframes = ['15m', '1h', '4h', '1d']
    
    # Mức rủi ro (theo yêu cầu)
    risk_levels = [0.01, 0.02, 0.025, 0.03, 0.035, 0.04]
    
    # Số ngày dữ liệu
    days_back = 90
    
    # Số luồng xử lý tối đa
    max_workers = 5
    
    print("=== KIỂM THỬ TOÀN THỊ TRƯỜNG VỚI DỮ LIỆU THỰC ===")
    print(f"Các mức rủi ro: {risk_levels}")
    print(f"Các khung thời gian: {timeframes}")
    print(f"Dữ liệu {days_back} ngày gần nhất")
    print("Quá trình này sẽ mất thời gian, vui lòng đợi...")
    
    # Chạy kiểm thử
    results = run_full_market_test(symbols, timeframes, risk_levels, days_back, max_workers)
    
    print("\nHoàn thành kiểm thử toàn thị trường!")
    print(f"Báo cáo và biểu đồ đã được lưu trong thư mục full_test_results/")
    
    # In Top 5 kết hợp tốt nhất
    if results['best_combinations']:
        print("\nTop 5 Kết Hợp Tốt Nhất:")
        for i, combo in enumerate(results['best_combinations'][:5]):
            print(f"{i+1}. {combo['symbol']} ({combo['timeframe']}, risk={combo['risk_level']}): "
                f"Sharpe {combo['sharpe_ratio']:.2f}, "
                f"Profit {combo['profit_pct']:.2f}%, "
                f"DD {combo['max_drawdown_pct']:.2f}%, "
                f"WR {combo['win_rate']:.2f}%")