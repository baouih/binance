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
    # Tính các đường MA
    data['ma20'] = data['Close'].rolling(window=20).mean()
    data['ma50'] = data['Close'].rolling(window=50).mean()
    data['ma100'] = data['Close'].rolling(window=100).mean()
    
    # Tính RSI
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    data['rsi'] = 100 - (100 / (1 + rs))
    
    # Tính ATR (Average True Range)
    high_low = data['High'] - data['Low']
    high_close = abs(data['High'] - data['Close'].shift())
    low_close = abs(data['Low'] - data['Close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    data['atr'] = true_range.rolling(14).mean()
    
    # Bollinger Bands
    data['sma20'] = data['Close'].rolling(20).mean()
    data['stddev'] = data['Close'].rolling(20).std()
    data['bollinger_upper'] = data['sma20'] + (data['stddev'] * 2)
    data['bollinger_lower'] = data['sma20'] - (data['stddev'] * 2)
    
    return data

def ma_crossover_signals(data):
    """Tạo tín hiệu MA crossover"""
    signals = []
    
    for i in range(20, len(data)-1):
        # Kiểm tra điều kiện MA crossover
        current_close = float(data['Close'].iloc[i])
        current_ma20 = float(data['ma20'].iloc[i])
        prev_close = float(data['Close'].iloc[i-1])
        prev_ma20 = float(data['ma20'].iloc[i-1])
        
        # Tín hiệu mua khi giá vượt lên trên MA20
        if prev_close <= prev_ma20 and current_close > current_ma20:
            entry_date = data.index[i]
            entry_price = current_close
            
            signals.append({
                'date': entry_date,
                'type': 'LONG',
                'entry_price': entry_price,
                'signal_source': 'ma_crossover',
                'sideways_period': False
            })
    
    return signals

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

def run_adaptive_backtest(symbols, period="3mo", timeframe="1d", initial_balance=10000.0):
    """Chạy backtest với chiến lược thích ứng"""
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
    
    args = parser.parse_args()
    
    # Kiểm tra, nếu chuỗi được truyền vào (e.g., --symbols "BTC-USD,ETH-USD"), thì tách ra
    if len(args.symbols) == 1 and ',' in args.symbols[0]:
        args.symbols = args.symbols[0].split(',')
    
    # Chạy backtest
    report = run_adaptive_backtest(
        symbols=args.symbols,
        period=args.period,
        timeframe=args.timeframe,
        initial_balance=args.balance
    )
    
    # Lưu báo cáo
    save_report(report, args.output_dir)
    
    # Vẽ biểu đồ
    if not args.no_plot:
        plot_results(report, args.output_dir)

if __name__ == "__main__":
    main()