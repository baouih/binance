#!/usr/bin/env python3
"""
Phiên bản cải tiến của chiến lược RSI với các biện pháp bảo vệ tốt hơn
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('improved_rsi')

# Import các module cần thiết
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.strategy import RSIStrategy
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    sys.exit(1)

def generate_sample_data(days=90, interval='1h'):
    """
    Tạo dữ liệu mẫu đáng tin cậy hơn cho backtest
    
    Args:
        days (int): Số ngày dữ liệu
        interval (str): Khung thời gian
    
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    logger.info(f"Tạo dữ liệu mẫu cho {days} ngày với khung thời gian {interval}")
    
    # Tính số lượng candles
    if interval == '1h':
        periods = days * 24
    elif interval == '15m':
        periods = days * 24 * 4
    elif interval == '1d':
        periods = days
    else:
        periods = days * 24  # Mặc định 1h
    
    # Tạo dữ liệu thời gian
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    if interval == '1h':
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
    elif interval == '15m':
        dates = pd.date_range(start=start_date, end=end_date, freq='15min')
    elif interval == '1d':
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
    else:
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Giới hạn số lượng
    dates = dates[:periods]
    
    # Tạo giá mô phỏng với xu hướng, dao động và một số biến động
    np.random.seed(42)  # Để kết quả có thể tái tạo
    
    # Giá ban đầu
    initial_price = 80000
    
    # Tạo xu hướng cơ bản
    trend = np.linspace(0, 0.2, periods)  # Xu hướng tăng nhẹ
    
    # Thêm dao động
    oscillation = np.sin(np.linspace(0, 15, periods)) * 0.1
    
    # Thêm biến động ngẫu nhiên
    noise = np.random.normal(0, 0.01, periods)
    
    # Thêm các biến động đột ngột
    random_spikes = np.zeros(periods)
    spike_points = np.random.choice(periods, size=5, replace=False)
    random_spikes[spike_points] = np.random.uniform(-0.1, 0.1, 5)
    
    # Tính toán chỉ số giá theo ngày
    price_factors = 1 + trend + oscillation + noise + random_spikes
    price_index = initial_price * np.cumprod(price_factors)
    
    # Tạo giá OHLC
    df = pd.DataFrame(index=dates)
    df['close'] = price_index
    
    # Tạo open, high, low từ close
    df['open'] = df['close'].shift(1)
    df.loc[df.index[0], 'open'] = df['close'].iloc[0] * (1 - np.random.uniform(0, 0.01))
    
    daily_volatility = 0.02
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, daily_volatility, size=len(df)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, daily_volatility, size=len(df)))
    
    # Tạo khối lượng
    base_volume = 1000
    volume_trend = np.linspace(0, 0.5, periods)  # Tăng dần khối lượng
    volume_oscillation = np.sin(np.linspace(0, 30, periods)) * 0.5  # Dao động khối lượng
    volume_noise = np.random.normal(0, 0.2, periods)  # Nhiễu khối lượng
    
    volume_factors = 1 + volume_trend + volume_oscillation + volume_noise
    volume_factors = np.maximum(volume_factors, 0.1)  # Đảm bảo toàn bộ giá trị là dương
    df['volume'] = base_volume * volume_factors
    
    # Thêm các chỉ báo
    # RSI (phương pháp Wilder)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    # Sử dụng phương pháp Wilder's Smoothing
    avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Thêm một vài biến động ngẫu nhiên vào RSI để tạo tín hiệu
    np.random.seed(42)
    rsi_noise = np.random.normal(0, 5, len(df))
    df['rsi'] = df['rsi'] + rsi_noise
    
    # Đảm bảo giá trị RSI trong khoảng 0-100
    df['rsi'] = np.clip(df['rsi'], 0, 100)
    
    logger.info(f"Đã tạo {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    return df

def backtest_rsi_strategy(days=90, interval='1h', initial_balance=10000.0, 
                          leverage=5, risk_percentage=2.0, overbought=70, oversold=30,
                          use_sample_data=True):
    """
    Thực hiện backtest với chiến lược RSI
    
    Args:
        days (int): Số ngày dữ liệu lịch sử
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        overbought (int): Ngưỡng quá mua
        oversold (int): Ngưỡng quá bán
        use_sample_data (bool): Sử dụng dữ liệu mẫu thay vì dữ liệu API
    """
    logger.info(f"=== BACKTEST RSI STRATEGY ===")
    logger.info(f"Interval: {interval}")
    logger.info(f"Days: {days}")
    logger.info(f"Initial Balance: ${initial_balance}")
    logger.info(f"Leverage: {leverage}x")
    logger.info(f"Risk: {risk_percentage}%")
    logger.info(f"RSI Overbought: {overbought}")
    logger.info(f"RSI Oversold: {oversold}")
    
    # Lấy dữ liệu
    if use_sample_data:
        df = generate_sample_data(days=days, interval=interval)
    else:
        # Khởi tạo API và các module
        binance_api = BinanceAPI(simulation_mode=True)
        data_processor = DataProcessor(binance_api, simulation_mode=True)
        
        # Lấy dữ liệu lịch sử
        df = data_processor.get_historical_data('BTCUSDT', interval, lookback_days=days)
    
    if df is None or df.empty:
        logger.error("Không thể lấy dữ liệu")
        return None
    
    # Khởi tạo chiến lược RSI
    strategy = RSIStrategy(overbought=overbought, oversold=oversold)
    logger.info(f"Đã tạo chiến lược RSI")
    
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
    
    # Để có đủ dữ liệu cho RSI, bỏ qua các candles đầu tiên
    start_idx = 20  # Bỏ qua 20 candles đầu tiên
    
    for i in range(start_idx, len(df) - 1):
        current_data = df.iloc[:i+1]
        signal = strategy.generate_signal(current_data)
        
        current_price = current_data['close'].iloc[-1]
        current_date = current_data.index[-1]
        
        # Đảm bảo giá là hợp lệ và lớn hơn 0
        if current_price <= 0:
            logger.warning(f"Bỏ qua candle tại {current_date} do giá không hợp lệ: {current_price}")
            continue
        
        # Mở vị thế mới nếu chưa có vị thế
        if current_position is None:
            if signal == 1:  # Tín hiệu mua
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                current_position = {
                    'side': 'BUY',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage
                }
                
                logger.info(f"Mở vị thế MUA tại {entry_date}: {entry_price:.2f}, Số lượng: {order_qty:.5f}")
                
            elif signal == -1:  # Tín hiệu bán
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                current_position = {
                    'side': 'SELL',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage
                }
                
                logger.info(f"Mở vị thế BÁN tại {entry_date}: {entry_price:.2f}, Số lượng: {order_qty:.5f}")
        
        # Đóng vị thế hiện tại
        elif ((current_position['side'] == 'BUY' and signal == -1) or 
              (current_position['side'] == 'SELL' and signal == 1) or
              (i == len(df) - 2)):  # Đóng vị thế ở candlestick cuối cùng
            
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
            fees = (current_position['quantity'] * current_position['entry_price'] * fee_rate) + \
                   (current_position['quantity'] * exit_price * fee_rate)
            
            pnl_amount = pnl * risk_amount - fees
            
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
                'pnl_percent': pnl * 100,
                'pnl_amount': pnl_amount,
                'balance': balance
            }
            trades.append(trade)
            
            logger.info(f"Đóng vị thế {current_position['side']} tại {exit_date}: {exit_price:.2f}, PnL: {pnl*100:.2f}%, ${pnl_amount:.2f}")
            
            # Reset vị thế
            current_position = None
        
        # Cập nhật đường cong vốn
        if i % 24 == 0 or i == len(df) - 2:  # Cập nhật hàng ngày hoặc ở candle cuối cùng
            equity_curve.append(balance)
            dates.append(current_date)
    
    # Tính toán số liệu hiệu suất
    num_trades = len(trades)
    
    if num_trades > 0:
        winning_trades = sum(1 for t in trades if t['pnl_amount'] > 0)
        losing_trades = sum(1 for t in trades if t['pnl_amount'] <= 0)
        
        win_rate = (winning_trades / num_trades) * 100 if num_trades > 0 else 0
        
        total_profit = sum(t['pnl_amount'] for t in trades if t['pnl_amount'] > 0)
        total_loss = sum(t['pnl_amount'] for t in trades if t['pnl_amount'] <= 0)
        
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
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
        import matplotlib.pyplot as plt
        plt.figure(figsize=(12, 6))
        plt.plot(dates, equity_curve)
        plt.title(f'Đường cong vốn - RSI Strategy ({interval})')
        plt.xlabel('Thời gian')
        plt.ylabel('Vốn ($)')
        plt.grid(True)
        plt.savefig('improved_rsi_results.png')
        logger.info(f"Đã lưu đồ thị đường cong vốn vào 'improved_rsi_results.png'")
        
        # Lưu giao dịch
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('improved_rsi_trades.csv', index=False)
        logger.info(f"Đã lưu lịch sử giao dịch vào 'improved_rsi_trades.csv'")
        
        # Lưu kết quả
        results = {
            'interval': interval,
            'strategy': 'RSI',
            'rsi_settings': {
                'overbought': overbought,
                'oversold': oversold
            },
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
            'start_date': str(df.index[0]),
            'end_date': str(df.index[-1])
        }
        
        with open('improved_rsi_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Đã lưu kết quả backtest vào 'improved_rsi_results.json'")
        
        return results
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong backtest")
        return None

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest RSI Strategy cải tiến')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--days', type=int, default=90, help='Số ngày dữ liệu lịch sử (mặc định: 90)')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=2.0, help='Phần trăm rủi ro (mặc định: 2%)')
    parser.add_argument('--overbought', type=int, default=70, help='Ngưỡng quá mua (mặc định: 70)')
    parser.add_argument('--oversold', type=int, default=30, help='Ngưỡng quá bán (mặc định: 30)')
    parser.add_argument('--use-api-data', action='store_true', help='Sử dụng dữ liệu API thay vì dữ liệu mẫu')
    
    args = parser.parse_args()
    
    backtest_rsi_strategy(
        days=args.days,
        interval=args.interval,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        overbought=args.overbought,
        oversold=args.oversold,
        use_sample_data=not args.use_api_data
    )

if __name__ == "__main__":
    main()