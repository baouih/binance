#!/usr/bin/env python3
"""
Script backtest đơn giản sử dụng dữ liệu mẫu đã tạo trước đó

Script này thực hiện backtest đơn giản với chiến lược RSI cơ bản
sử dụng dữ liệu mẫu đã tạo từ trước, không phụ thuộc vào các module ngoài.
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('simple_backtest')

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

def calculate_indicators(df):
    """
    Tính toán các chỉ báo kỹ thuật
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã tính
    """
    # Tính RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Tính MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    
    # Tính Bollinger Bands
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (df['stddev'] * 2)
    df['lower_band'] = df['sma20'] - (df['stddev'] * 2)
    
    # Tính ATR
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    
    df['atr'] = true_range.rolling(14).mean()
    
    return df

def load_data(symbol, interval, data_dir='test_data'):
    """
    Tải dữ liệu giá từ file CSV
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        data_dir (str): Thư mục dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame với dữ liệu giá
    """
    file_path = f"{data_dir}/{symbol}/{symbol}_{interval}.csv"
    
    if not os.path.exists(file_path):
        logger.error(f"Không tìm thấy file dữ liệu: {file_path}")
        return None
    
    # Đọc dữ liệu
    df = pd.read_csv(file_path)
    
    # Chuyển đổi timestamp thành datetime và đặt làm index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # Tính các chỉ báo
    df = calculate_indicators(df)
    
    logger.info(f"Đã tải {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    
    return df

def generate_rsi_signals(df, overbought=70, oversold=30):
    """
    Tạo tín hiệu giao dịch dựa trên RSI
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá và RSI
        overbought (int): Ngưỡng quá mua
        oversold (int): Ngưỡng quá bán
        
    Returns:
        np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
    """
    signals = np.zeros(len(df))
    
    # Tín hiệu mua: RSI vượt lên trên ngưỡng quá bán
    buy_signals = (df['rsi'] > oversold) & (df['rsi'].shift(1) <= oversold)
    signals[buy_signals] = 1
    
    # Tín hiệu bán: RSI vượt xuống dưới ngưỡng quá mua
    sell_signals = (df['rsi'] < overbought) & (df['rsi'].shift(1) >= overbought)
    signals[sell_signals] = -1
    
    return signals

def generate_macd_signals(df):
    """
    Tạo tín hiệu giao dịch dựa trên MACD
    
    Args:
        df (pd.DataFrame): DataFrame với dữ liệu giá và MACD
        
    Returns:
        np.array: Mảng tín hiệu (1: mua, -1: bán, 0: không giao dịch)
    """
    signals = np.zeros(len(df))
    
    # Tín hiệu mua: MACD cắt lên trên Signal Line
    buy_signals = (df['macd'] > df['signal']) & (df['macd'].shift(1) <= df['signal'].shift(1))
    signals[buy_signals] = 1
    
    # Tín hiệu bán: MACD cắt xuống dưới Signal Line
    sell_signals = (df['macd'] < df['signal']) & (df['macd'].shift(1) >= df['signal'].shift(1))
    signals[sell_signals] = -1
    
    return signals

def run_backtest(symbol='BTCUSDT', interval='1h', strategy_type='rsi',
               initial_balance=10000.0, leverage=5, risk_percentage=1.0,
               take_profit_pct=15.0, stop_loss_pct=7.0, data_dir='test_data',
               overbought=70, oversold=30):
    """
    Chạy backtest với chiến lược đã chọn
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        strategy_type (str): Loại chiến lược ('rsi', 'macd', 'combined')
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro trên mỗi giao dịch
        take_profit_pct (float): Phần trăm chốt lời
        stop_loss_pct (float): Phần trăm cắt lỗ
        data_dir (str): Thư mục dữ liệu
        overbought (int): Ngưỡng quá mua (cho RSI)
        oversold (int): Ngưỡng quá bán (cho RSI)
    """
    logger.info(f"=== CHẠY BACKTEST ĐƠN GIẢN ===")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Strategy: {strategy_type}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Rủi ro: {risk_percentage}%")
    logger.info(f"Take Profit: {take_profit_pct}%")
    logger.info(f"Stop Loss: {stop_loss_pct}%")
    
    # Tải dữ liệu
    df = load_data(symbol, interval, data_dir)
    
    if df is None or df.empty:
        logger.error("Không thể tải dữ liệu")
        return
    
    # Tạo tín hiệu dựa trên chiến lược
    if strategy_type == 'rsi':
        signals = generate_rsi_signals(df, overbought, oversold)
    elif strategy_type == 'macd':
        signals = generate_macd_signals(df)
    elif strategy_type == 'combined':
        # Kết hợp RSI và MACD
        rsi_signals = generate_rsi_signals(df, overbought, oversold)
        macd_signals = generate_macd_signals(df)
        # Chỉ mua khi cả hai đều đưa ra tín hiệu mua, chỉ bán khi cả hai đều đưa ra tín hiệu bán
        signals = np.zeros(len(df))
        signals[(rsi_signals == 1) & (macd_signals == 1)] = 1
        signals[(rsi_signals == -1) & (macd_signals == -1)] = -1
    else:
        logger.error(f"Chiến lược không hợp lệ: {strategy_type}")
        return
    
    # Thêm tín hiệu vào DataFrame
    df['signal'] = signals
    
    # Danh sách để lưu trữ các giao dịch
    trades = []
    
    # Danh sách để lưu trữ giá trị vốn
    equity_curve = [initial_balance]
    dates = [df.index[0]]
    
    # Trạng thái giao dịch hiện tại
    current_position = None
    balance = initial_balance
    
    # Tỷ lệ rủi ro
    risk_amount = initial_balance * (risk_percentage / 100)
    
    # Chạy backtest
    logger.info("Bắt đầu backtest...")
    
    # Bỏ qua một số candlesticks đầu tiên để chờ các chỉ báo có đủ dữ liệu
    start_idx = 100
    
    for i in range(start_idx, len(df)):
        current_row = df.iloc[i]
        current_price = current_row['close']
        current_date = df.index[i]
        current_signal = current_row['signal']
        
        # Mở vị thế mới nếu chưa có vị thế
        if current_position is None:
            if current_signal == 1:  # Tín hiệu mua
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Tính toán stop loss và take profit
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                take_profit_price = entry_price * (1 + take_profit_pct / 100)
                
                current_position = {
                    'side': 'BUY',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price
                }
                
                logger.info(f"Mở vị thế MUA tại {entry_date}: ${entry_price:.2f}, Số lượng: {order_qty:.6f}, "
                          f"SL: ${stop_loss_price:.2f}, TP: ${take_profit_price:.2f}")
                
            elif current_signal == -1:  # Tín hiệu bán
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Tính toán stop loss và take profit
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
                take_profit_price = entry_price * (1 - take_profit_pct / 100)
                
                current_position = {
                    'side': 'SELL',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price
                }
                
                logger.info(f"Mở vị thế BÁN tại {entry_date}: ${entry_price:.2f}, Số lượng: {order_qty:.6f}, "
                          f"SL: ${stop_loss_price:.2f}, TP: ${take_profit_price:.2f}")
        
        # Kiểm tra các điều kiện để đóng vị thế hiện tại
        elif current_position is not None:
            exit_reason = None
            
            # Kiểm tra take profit
            if (current_position['side'] == 'BUY' and current_price >= current_position['take_profit']) or \
               (current_position['side'] == 'SELL' and current_price <= current_position['take_profit']):
                exit_reason = "Take Profit"
            
            # Kiểm tra stop loss
            elif (current_position['side'] == 'BUY' and current_price <= current_position['stop_loss']) or \
                 (current_position['side'] == 'SELL' and current_price >= current_position['stop_loss']):
                exit_reason = "Stop Loss"
            
            # Kiểm tra tín hiệu đảo chiều
            elif (current_position['side'] == 'BUY' and current_signal == -1) or \
                 (current_position['side'] == 'SELL' and current_signal == 1):
                exit_reason = "Reverse Signal"
            
            # Đóng vị thế nếu có lý do
            if exit_reason:
                exit_price = current_price
                exit_date = current_date
                
                # Tính lợi nhuận
                if current_position['side'] == 'BUY':
                    pnl = (exit_price - current_position['entry_price']) / current_position['entry_price']
                else:  # SELL
                    pnl = (current_position['entry_price'] - exit_price) / current_position['entry_price']
                
                # Áp dụng đòn bẩy
                pnl = pnl * leverage
                
                # Trừ phí giao dịch (giả sử 0.075% mỗi lần vào/ra)
                fee_rate = 0.00075  # 0.075%
                position_value = current_position['quantity'] * current_position['entry_price']
                fees = (position_value * fee_rate) + (current_position['quantity'] * exit_price * fee_rate)
                
                pnl_amount = pnl * position_value - fees
                
                # Cập nhật số dư
                balance += pnl_amount
                
                # Lưu giao dịch
                trade = {
                    'entry_date': current_position['entry_date'],
                    'exit_date': exit_date,
                    'side': current_position['side'],
                    'entry_price': current_position['entry_price'],
                    'exit_price': exit_price,
                    'quantity': current_position['quantity'],
                    'leverage': current_position['leverage'],
                    'exit_reason': exit_reason,
                    'pnl_percent': pnl * 100,
                    'pnl_amount': pnl_amount,
                    'fees': fees,
                    'balance': balance
                }
                trades.append(trade)
                
                logger.info(f"Đóng vị thế {current_position['side']} tại {exit_date}: ${exit_price:.2f}, "
                          f"PnL: {pnl*100:.2f}%, ${pnl_amount:.2f}, Lý do: {exit_reason}")
                
                # Reset vị thế
                current_position = None
        
        # Cập nhật đường cong vốn
        if i % 24 == 0 or i == len(df) - 1:  # Cập nhật hàng ngày hoặc ở candle cuối cùng
            equity_curve.append(balance)
            dates.append(current_date)
    
    # Tính toán số liệu hiệu suất
    num_trades = len(trades)
    
    if num_trades > 0:
        winning_trades = sum(1 for t in trades if t['pnl_amount'] > 0)
        losing_trades = sum(1 for t in trades if t['pnl_amount'] <= 0)
        
        win_rate = (winning_trades / num_trades) * 100 if num_trades > 0 else 0
        
        total_profit = sum(t['pnl_amount'] for t in trades if t['pnl_amount'] > 0)
        total_loss = abs(sum(t['pnl_amount'] for t in trades if t['pnl_amount'] <= 0))
        
        profit_factor = (total_profit / total_loss) if total_loss != 0 else float('inf')
        
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Tính max drawdown
        peak = initial_balance
        drawdowns = []
        for t in trades:
            if t['balance'] > peak:
                peak = t['balance']
            dd = (peak - t['balance']) / peak
            drawdowns.append(dd)
        
        max_drawdown = max(drawdowns) * 100 if drawdowns else 0
        
        # Kết quả cuối cùng
        final_balance = balance
        profit_percent = ((final_balance - initial_balance) / initial_balance) * 100
        
        # Hiển thị kết quả
        logger.info(f"\n=== KẾT QUẢ BACKTEST ===")
        logger.info(f"Số giao dịch: {num_trades}")
        logger.info(f"Giao dịch thắng/thua: {winning_trades}/{losing_trades}")
        logger.info(f"Win rate: {win_rate:.2f}%")
        logger.info(f"Profit factor: {profit_factor:.2f}")
        logger.info(f"Lợi nhuận trung bình: ${avg_profit:.2f}")
        logger.info(f"Thua lỗ trung bình: ${avg_loss:.2f}")
        logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
        logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
        logger.info(f"Số dư cuối cùng: ${final_balance:.2f}")
        logger.info(f"Lợi nhuận: ${final_balance - initial_balance:.2f} ({profit_percent:.2f}%)")
        
        # Vẽ đồ thị
        plt.figure(figsize=(12, 6))
        plt.plot(dates, equity_curve)
        plt.title(f'Đường cong vốn - {strategy_type.upper()} ({symbol} {interval})')
        plt.xlabel('Thời gian')
        plt.ylabel('Vốn ($)')
        plt.grid(True)
        
        chart_path = f'backtest_charts/{symbol}_{interval}_{strategy_type}_equity.png'
        plt.savefig(chart_path)
        logger.info(f"Đã lưu đồ thị đường cong vốn vào '{chart_path}'")
        
        # Lưu giao dịch
        trades_df = pd.DataFrame(trades)
        trades_file = f'backtest_results/{symbol}_{interval}_{strategy_type}_trades.csv'
        trades_df.to_csv(trades_file, index=False)
        logger.info(f"Đã lưu lịch sử giao dịch vào '{trades_file}'")
        
        # Vẽ đồ thị cây nến và tín hiệu
        plt.figure(figsize=(14, 8))
        
        # Đồ thị giá
        plt.subplot(2, 1, 1)
        
        # Tính mid point của mỗi candlestick để vẽ
        dates_candlestick = df.index[start_idx:len(df)]
        
        # Vẽ candlestick đơn giản
        for i in range(start_idx, len(df)):
            date = df.index[i]
            open_price = df['open'].iloc[i]
            close_price = df['close'].iloc[i]
            high_price = df['high'].iloc[i]
            low_price = df['low'].iloc[i]
            
            color = 'green' if close_price >= open_price else 'red'
            
            # Vẽ thân nến
            plt.plot([date, date], [open_price, close_price], color=color, linewidth=2)
            
            # Vẽ bóng nến
            plt.plot([date, date], [low_price, high_price], color=color, linewidth=0.5)
        
        # Vẽ các đường MA
        plt.plot(df.index[start_idx:], df['sma20'].iloc[start_idx:], color='blue', label='SMA 20')
        
        # Vẽ Bollinger Bands
        plt.plot(df.index[start_idx:], df['upper_band'].iloc[start_idx:], 'r--', label='Upper Band')
        plt.plot(df.index[start_idx:], df['lower_band'].iloc[start_idx:], 'r--', label='Lower Band')
        
        # Vẽ các điểm mua/bán
        buy_signals = df[df['signal'] == 1]
        sell_signals = df[df['signal'] == -1]
        
        plt.scatter(buy_signals.index, buy_signals['close'], color='green', marker='^', s=100, label='Mua')
        plt.scatter(sell_signals.index, sell_signals['close'], color='red', marker='v', s=100, label='Bán')
        
        plt.title(f'Tín hiệu giao dịch - {strategy_type.upper()} ({symbol} {interval})')
        plt.xlabel('Thời gian')
        plt.ylabel('Giá ($)')
        plt.grid(True)
        plt.legend()
        
        # Vẽ RSI
        plt.subplot(2, 1, 2)
        plt.plot(df.index[start_idx:], df['rsi'].iloc[start_idx:], color='purple')
        plt.axhline(y=overbought, color='r', linestyle='-', label=f'Quá mua ({overbought})')
        plt.axhline(y=oversold, color='g', linestyle='-', label=f'Quá bán ({oversold})')
        plt.axhline(y=50, color='gray', linestyle='--')
        
        plt.title('RSI (14)')
        plt.xlabel('Thời gian')
        plt.ylabel('RSI')
        plt.grid(True)
        plt.legend()
        
        plt.tight_layout()
        
        signals_chart_path = f'backtest_charts/{symbol}_{interval}_{strategy_type}_signals.png'
        plt.savefig(signals_chart_path)
        logger.info(f"Đã lưu đồ thị tín hiệu vào '{signals_chart_path}'")
        
        # Lưu kết quả
        results = {
            'symbol': symbol,
            'interval': interval,
            'strategy': strategy_type,
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'profit': final_balance - initial_balance,
            'profit_percent': profit_percent,
            'num_trades': num_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'take_profit_pct': take_profit_pct,
            'stop_loss_pct': stop_loss_pct,
            'leverage': leverage,
            'risk_percentage': risk_percentage,
            'overbought': overbought,
            'oversold': oversold
        }
        
        results_file = f'backtest_results/{symbol}_{interval}_{strategy_type}_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Đã lưu kết quả backtest vào '{results_file}'")
        
        return results
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong backtest")
        return None

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ backtest đơn giản')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--strategy', type=str, default='rsi', 
                       choices=['rsi', 'macd', 'combined'],
                       help='Loại chiến lược giao dịch (mặc định: rsi)')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro (mặc định: 1%%)')
    parser.add_argument('--take_profit', type=float, default=15.0, help='Phần trăm chốt lời (mặc định: 15%%)')
    parser.add_argument('--stop_loss', type=float, default=7.0, help='Phần trăm cắt lỗ (mặc định: 7%%)')
    parser.add_argument('--data_dir', type=str, default='test_data', help='Thư mục dữ liệu (mặc định: test_data)')
    parser.add_argument('--overbought', type=int, default=70, help='Ngưỡng quá mua RSI (mặc định: 70)')
    parser.add_argument('--oversold', type=int, default=30, help='Ngưỡng quá bán RSI (mặc định: 30)')
    
    args = parser.parse_args()
    
    run_backtest(
        symbol=args.symbol,
        interval=args.interval,
        strategy_type=args.strategy,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        take_profit_pct=args.take_profit,
        stop_loss_pct=args.stop_loss,
        data_dir=args.data_dir,
        overbought=args.overbought,
        oversold=args.oversold
    )

if __name__ == "__main__":
    main()