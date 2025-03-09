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
        dates = pd.date_range(start=start_date, end=end_date, freq='h')
    elif interval == '15m':
        dates = pd.date_range(start=start_date, end=end_date, freq='15min')
    elif interval == '1d':
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
    else:
        dates = pd.date_range(start=start_date, end=end_date, freq='h')
    
    # Giới hạn số lượng
    dates = dates[:periods]
    
    # Tạo đối tượng numpy random với seed cố định
    rng = np.random.RandomState(42)
    
    # Tạo giá mẫu có tính chất giống Bitcoin thực tế hơn
    initial_price = 80000  # Giá ban đầu trên Binance
    prices = [initial_price]
    
    # Biến động giá BTC giảm dần với kích thước
    volatility = 0.015  # 1.5% biến động hàng ngày trung bình
    drift = 0.001       # 0.1% xu hướng tăng trung bình mỗi ngày
    
    for i in range(1, periods):
        # Xu hướng ngẫu nhiên với thiên hướng tăng nhẹ
        daily_return = drift + volatility * rng.randn()
        
        # Thêm một số dao động theo mùa
        seasonal = 0.005 * np.sin(i / (periods/6))  # dao động 6 chu kỳ
        
        # Thêm biến động thời gian thực (trong ngày)
        intraday = 0.003 * np.sin(i / 24 * 2 * np.pi)
        
        # Tính giá mới
        new_price = prices[-1] * (1 + daily_return + seasonal + intraday)
        
        # Đôi khi có biến động lớn
        if rng.random() < 0.01:  # 1% khả năng có biến động lớn
            spike = rng.choice([-1, 1]) * rng.uniform(0.03, 0.08)  # Biến động 3-8%
            new_price *= (1 + spike)
        
        # Không cho phép giá dưới 20000
        new_price = max(20000, new_price)
        
        prices.append(new_price)
    
    # Tạo DataFrame
    df = pd.DataFrame(index=dates)
    df['close'] = prices
    
    # Tạo open, high, low
    df['open'] = df['close'].shift(1)
    df.loc[df.index[0], 'open'] = prices[0] * (1 - rng.uniform(0, 0.01))
    
    daily_volatility = 0.01
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + rng.uniform(0, daily_volatility, size=len(df)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - rng.uniform(0, daily_volatility, size=len(df)))
    
    # Tạo khối lượng
    base_volume = 1000
    
    # Tạo mẫu khối lượng dựa trên biến động giá
    price_changes = np.abs(df['close'].pct_change().fillna(0).values)
    volume = base_volume * (1 + 5 * price_changes)  # Khối lượng tăng khi giá biến động mạnh
    
    # Thêm một xu hướng nhẹ tăng dần
    volume_trend = np.linspace(1, 1.5, len(df))
    
    # Thêm một số dao động ngẫu nhiên
    volume_noise = 1 + 0.3 * rng.randn(len(df))
    volume_noise = np.maximum(volume_noise, 0.5)  # Giới hạn dưới
    
    df['volume'] = volume * volume_trend * volume_noise
    
    # Tính toán chỉ báo RSI
    # Tính toán delta
    delta = df['close'].diff()
    gain = delta.copy()
    gain[gain < 0] = 0
    loss = -delta.copy()
    loss[loss < 0] = 0
    
    # Tính trung bình di động theo kiểu Wilder
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    # Tính RS và RSI
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Thêm nhiễu vào RSI để tạo ra các tín hiệu giao dịch
    rsi_noise = 5 * rng.randn(len(df))
    rsi = rsi + rsi_noise
    
    # Clip để đảm bảo giá trị RSI trong khoảng 0-100
    df['rsi'] = np.clip(rsi, 0, 100)
    
    # Đảm bảo không có giá trị NaN
    df = df.fillna(method='bfill')
    
    logger.info(f"Đã tạo {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    return df

def backtest_rsi_strategy(days=90, interval='1h', initial_balance=10000.0, 
                          leverage=5, risk_percentage=2.0, overbought=70, oversold=30,
                          use_sample_data=True, use_trend_filter=True, use_volume_filter=True,
                          trailing_stop=True, take_profit_pct=15.0, stop_loss_pct=7.0):
    """
    Thực hiện backtest với chiến lược RSI cải tiến
    
    Args:
        days (int): Số ngày dữ liệu lịch sử
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        overbought (int): Ngưỡng quá mua
        oversold (int): Ngưỡng quá bán
        use_sample_data (bool): Sử dụng dữ liệu mẫu thay vì dữ liệu API
        use_trend_filter (bool): Sử dụng bộ lọc xu hướng - chỉ vào lệnh khi có xu hướng rõ ràng
        use_volume_filter (bool): Sử dụng bộ lọc khối lượng - chỉ vào lệnh khi khối lượng đủ lớn
        trailing_stop (bool): Sử dụng trailing stop - tự động điều chỉnh điểm dừng lỗ theo giá
        take_profit_pct (float): Phần trăm chốt lời - mức lợi nhuận để đóng vị thế
        stop_loss_pct (float): Phần trăm cắt lỗ - mức thua lỗ để đóng vị thế
    """
    logger.info(f"=== BACKTEST RSI STRATEGY ===")
    logger.info(f"Interval: {interval}")
    logger.info(f"Days: {days}")
    logger.info(f"Initial Balance: ${initial_balance}")
    logger.info(f"Leverage: {leverage}x")
    logger.info(f"Risk: {risk_percentage}%")
    logger.info(f"RSI Overbought: {overbought}")
    logger.info(f"RSI Oversold: {oversold}")
    logger.info(f"Take Profit: {take_profit_pct}%")
    logger.info(f"Stop Loss: {stop_loss_pct}%")
    logger.info(f"Trailing Stop: {'Enabled' if trailing_stop else 'Disabled'}")
    logger.info(f"Trend Filter: {'Enabled' if use_trend_filter else 'Disabled'}")
    logger.info(f"Volume Filter: {'Enabled' if use_volume_filter else 'Disabled'}")
    
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
    
    # Chiến lược RSI tùy chỉnh trực tiếp, không dựa vào lớp RSIStrategy
    # để tránh các vấn đề về phụ thuộc và tương thích
    logger.info(f"Sử dụng chiến lược RSI tùy chỉnh với ngưỡng overbought={overbought}, oversold={oversold}")
    
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
    
    # Thêm bộ đệm tín hiệu để ngăn quá nhiều tín hiệu liên tục
    signal_buffer_count = 0
    last_signal = 0
    
    for i in range(start_idx, len(df) - 1):
        current_data = df.iloc[:i+1]
        
        # Tạo tín hiệu RSI tùy chỉnh
        current_rsi = current_data['rsi'].iloc[-1]
        
        # Tạo tín hiệu dựa trên RSI
        signal = 0
        
        # Tính toán các chỉ báo bổ sung cho bộ lọc
        if use_trend_filter or use_volume_filter:
            # Tính EMA để xác định xu hướng
            if 'ema20' not in current_data.columns:
                current_data['ema20'] = current_data['close'].ewm(span=20, adjust=False).mean()
                current_data['ema50'] = current_data['close'].ewm(span=50, adjust=False).mean()
            
            # Tính trung bình khối lượng
            if 'volume_sma20' not in current_data.columns:
                current_data['volume_sma20'] = current_data['volume'].rolling(window=20).mean()
    
        # Chỉ tạo tín hiệu mới nếu hết thời gian đệm
        if signal_buffer_count <= 0:
            # Tín hiệu cơ bản dựa trên RSI
            if current_rsi <= oversold:
                base_signal = 1  # Mua khi RSI dưới ngưỡng oversold
            elif current_rsi >= overbought:
                base_signal = -1  # Bán khi RSI trên ngưỡng overbought
            else:
                base_signal = 0
            
            # Áp dụng các bộ lọc
            if base_signal != 0:
                signal = base_signal
                
                # Bộ lọc xu hướng - EMA
                if use_trend_filter:
                    current_ema20 = current_data['ema20'].iloc[-1]
                    current_ema50 = current_data['ema50'].iloc[-1]
                    price = current_data['close'].iloc[-1]
                    
                    # Xác định xu hướng
                    if base_signal == 1:  # Tín hiệu MUA
                        # Trong xu hướng tăng, EMA ngắn hạn trên EMA dài hạn
                        trend_ok = current_ema20 >= current_ema50 and price > current_ema20
                        if not trend_ok:
                            signal = 0  # Hủy tín hiệu nếu điều kiện xu hướng không tốt
                            logger.info(f"Candle {i}: Tín hiệu MUA bị hủy do điều kiện xu hướng")
                    
                    elif base_signal == -1:  # Tín hiệu BÁN
                        # Trong xu hướng giảm, EMA ngắn hạn dưới EMA dài hạn
                        trend_ok = current_ema20 <= current_ema50 and price < current_ema20
                        if not trend_ok:
                            signal = 0  # Hủy tín hiệu nếu điều kiện xu hướng không tốt
                            logger.info(f"Candle {i}: Tín hiệu BÁN bị hủy do điều kiện xu hướng")
                
                # Bộ lọc khối lượng
                if use_volume_filter and signal != 0:
                    current_volume = current_data['volume'].iloc[-1]
                    avg_volume = current_data['volume_sma20'].iloc[-1]
                    
                    # Khối lượng nên cao hơn trung bình
                    volume_ok = current_volume >= avg_volume * 1.2  # Yêu cầu khối lượng cao hơn 20%
                    if not volume_ok:
                        signal = 0  # Hủy tín hiệu nếu khối lượng thấp
                        logger.info(f"Candle {i}: Tín hiệu bị hủy do khối lượng thấp")
                
                # Đặt đệm thời gian nếu có tín hiệu
                if signal != 0:
                    signal_buffer_count = 5  # Đặt thời gian đệm
        else:
            signal_buffer_count -= 1
            
        if signal != 0:
            logger.info(f"Candle {i}: RSI = {current_rsi:.2f}, Signal = {signal}")
        
        # Lưu tín hiệu cuối cùng
        last_signal = signal
        
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
                
                # Tính toán take profit và stop loss
                if trailing_stop:
                    tp_level = entry_price * (1 + take_profit_pct/100)
                    sl_level = entry_price * (1 - stop_loss_pct/100)
                    highest_price = entry_price  # Theo dõi giá cao nhất cho trailing stop
                else:
                    tp_level = entry_price * (1 + take_profit_pct/100)
                    sl_level = entry_price * (1 - stop_loss_pct/100)
                
                current_position = {
                    'side': 'BUY',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'take_profit': tp_level,
                    'stop_loss': sl_level,
                    'highest_price': highest_price,
                    'trailing_active': False,  # Trailing stop chưa kích hoạt
                    'trailing_stop': trailing_stop
                }
                
                logger.info(f"Mở vị thế MUA tại {entry_date}: {entry_price:.2f}, Số lượng: {order_qty:.5f}")
                
            elif signal == -1:  # Tín hiệu bán
                # Tính toán số lượng
                order_qty = (risk_amount * leverage) / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Tính toán take profit và stop loss cho vị thế bán
                if trailing_stop:
                    tp_level = entry_price * (1 - take_profit_pct/100)
                    sl_level = entry_price * (1 + stop_loss_pct/100)
                    lowest_price = entry_price  # Theo dõi giá thấp nhất cho trailing stop
                else:
                    tp_level = entry_price * (1 - take_profit_pct/100)
                    sl_level = entry_price * (1 + stop_loss_pct/100)
                
                current_position = {
                    'side': 'SELL',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'take_profit': tp_level,
                    'stop_loss': sl_level,
                    'lowest_price': lowest_price,
                    'trailing_active': False,  # Trailing stop chưa kích hoạt
                    'trailing_stop': trailing_stop
                }
                
                logger.info(f"Mở vị thế BÁN tại {entry_date}: {entry_price:.2f}, Số lượng: {order_qty:.5f}")
        
        # Cập nhật trailing stop nếu có vị thế đang mở
        elif current_position is not None:
            close_position = False
            exit_reason = "Tín hiệu đảo chiều"
            
            # Kiểm tra take profit và stop loss
            if current_position['side'] == 'BUY':
                # Vị thế mua - cập nhật giá cao nhất
                if current_price > current_position['highest_price']:
                    current_position['highest_price'] = current_price
                
                # Kiểm tra take profit
                if current_price >= current_position['take_profit']:
                    if not current_position['trailing_active'] and trailing_stop:
                        # Kích hoạt trailing stop
                        current_position['trailing_active'] = True
                        logger.info(f"Kích hoạt trailing stop tại {current_date}: {current_price:.2f}")
                    else:
                        # Chốt lời
                        close_position = True
                        exit_reason = "Take profit"
                
                # Kiểm tra trailing stop
                elif current_position['trailing_active'] and trailing_stop:
                    # Tính toán giá trailing stop: Giá cao nhất - % trailing
                    trailing_level = current_position['highest_price'] * (1 - stop_loss_pct/200)  # Một nửa stop loss
                    if current_price < trailing_level:
                        close_position = True
                        exit_reason = "Trailing stop"
                
                # Kiểm tra stop loss
                elif current_price <= current_position['stop_loss']:
                    close_position = True
                    exit_reason = "Stop loss"
                
                # Kiểm tra tín hiệu đảo chiều
                elif signal == -1:
                    close_position = True
                    exit_reason = "Tín hiệu đảo chiều"
            
            elif current_position['side'] == 'SELL':
                # Vị thế bán - cập nhật giá thấp nhất
                if current_price < current_position['lowest_price']:
                    current_position['lowest_price'] = current_price
                
                # Kiểm tra take profit
                if current_price <= current_position['take_profit']:
                    if not current_position['trailing_active'] and trailing_stop:
                        # Kích hoạt trailing stop
                        current_position['trailing_active'] = True
                        logger.info(f"Kích hoạt trailing stop tại {current_date}: {current_price:.2f}")
                    else:
                        # Chốt lời
                        close_position = True
                        exit_reason = "Take profit"
                
                # Kiểm tra trailing stop
                elif current_position['trailing_active'] and trailing_stop:
                    # Tính toán giá trailing stop: Giá thấp nhất + % trailing
                    trailing_level = current_position['lowest_price'] * (1 + stop_loss_pct/200)  # Một nửa stop loss
                    if current_price > trailing_level:
                        close_position = True
                        exit_reason = "Trailing stop"
                
                # Kiểm tra stop loss
                elif current_price >= current_position['stop_loss']:
                    close_position = True
                    exit_reason = "Stop loss"
                
                # Kiểm tra tín hiệu đảo chiều
                elif signal == 1:
                    close_position = True
                    exit_reason = "Tín hiệu đảo chiều"
            
            # Đóng vị thế nếu cần
            if close_position or i == len(df) - 2:  # Đóng vị thế ở candlestick cuối cùng
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
                    'balance': balance,
                    'exit_reason': exit_reason
                }
                trades.append(trade)
                
                logger.info(f"Đóng vị thế {current_position['side']} tại {exit_date}: {exit_price:.2f}, PnL: {pnl*100:.2f}%, ${pnl_amount:.2f} ({exit_reason})")
                
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
            'risk_management': {
                'trailing_stop': trailing_stop,
                'take_profit_pct': take_profit_pct,
                'stop_loss_pct': stop_loss_pct
            },
            'filters': {
                'trend_filter': use_trend_filter,
                'volume_filter': use_volume_filter
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
    parser.add_argument('--use-trend-filter', action='store_true', help='Sử dụng bộ lọc xu hướng (mặc định: False)')
    parser.add_argument('--use-volume-filter', action='store_true', help='Sử dụng bộ lọc khối lượng (mặc định: False)')
    parser.add_argument('--trailing-stop', action='store_true', help='Sử dụng trailing stop (mặc định: False)')
    parser.add_argument('--take-profit', type=float, default=15.0, help='Phần trăm chốt lời (mặc định: 15%)')
    parser.add_argument('--stop-loss', type=float, default=7.0, help='Phần trăm cắt lỗ (mặc định: 7%)')
    
    args = parser.parse_args()
    
    backtest_rsi_strategy(
        days=args.days,
        interval=args.interval,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        overbought=args.overbought,
        oversold=args.oversold,
        use_sample_data=not args.use_api_data,
        use_trend_filter=args.use_trend_filter,
        use_volume_filter=args.use_volume_filter,
        trailing_stop=args.trailing_stop,
        take_profit_pct=args.take_profit,
        stop_loss_pct=args.stop_loss
    )

if __name__ == "__main__":
    main()