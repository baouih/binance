#!/usr/bin/env python3
"""
Script backtest nhanh để kiểm tra các tính năng mới

Script này thực hiện backtest với dữ liệu giả lập nhỏ hơn 
để kiểm tra nhanh chóng các tính năng:
1. Tích hợp vị thế Pythagorean Position Sizer
2. Tích hợp phân tích rủi ro Monte Carlo
3. Tích hợp phát hiện chế độ thị trường Fractal
4. Tích hợp tối ưu hóa thời gian giao dịch
"""

import os
import sys
import json
import time
import random
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("quick_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("quick_backtest")

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

# Import các module mới phát triển
from position_sizing_enhanced import PythagoreanPositionSizer, MonteCarloRiskAnalyzer
from fractal_market_regime import FractalMarketRegimeDetector
from trading_time_optimizer import TradingTimeOptimizer

def generate_sample_price_data(days=90):
    """
    Tạo dữ liệu giá mẫu với các chế độ thị trường khác nhau
    
    Returns:
        pd.DataFrame: DataFrame với dữ liệu OHLCV
    """
    # Tạo index từ ngày hiện tại trở về trước
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='1h')
    
    # Tạo dữ liệu giá
    prices = np.zeros(len(date_range))
    prices[0] = 50000  # Giá ban đầu $50k
    
    # Thêm xu hướng và nhiễu
    for i in range(1, len(prices)):
        # Thay đổi chế độ thị trường
        if i < len(prices) // 5:  # 1/5 đầu: Trending up
            trend = 0.05
            volatility = 0.5
        elif i < 2 * len(prices) // 5:  # 1/5 tiếp theo: Ranging
            trend = 0.0
            volatility = 0.3
        elif i < 3 * len(prices) // 5:  # 1/5 tiếp theo: Trending down
            trend = -0.05
            volatility = 0.5
        elif i < 4 * len(prices) // 5:  # 1/5 tiếp theo: Volatile
            trend = -0.01
            volatility = 1.2
        else:  # 1/5 cuối: Quiet
            trend = 0.01
            volatility = 0.2
            
        # Tạo giá
        price_change = np.random.normal(trend, volatility)
        prices[i] = max(1, prices[i-1] * (1 + price_change / 100))
    
    # Tạo DataFrame
    df = pd.DataFrame(index=date_range)
    df['close'] = prices
    
    # Tạo OHLCV
    df['open'] = df['close'].shift(1)
    df.loc[df.index[0], 'open'] = df['close'].iloc[0] * 0.99
    
    # High & Low - thêm nhiễu ngẫu nhiên
    random_factors = np.random.uniform(0.001, 0.01, len(df))
    df['high'] = df['close'] * (1 + random_factors)
    df['low'] = df['close'] * (1 - random_factors)
    
    # Thêm volume
    df['volume'] = np.random.uniform(100, 1000, len(df)) * df['close'] / 1000
    
    return df

def add_indicators(df):
    """Thêm các indicator vào dữ liệu giá"""
    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * std
    df['bb_lower'] = df['bb_middle'] - 2 * std
    
    # EMA
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # MACD
    df['macd_fast'] = df['close'].ewm(span=12, adjust=False).mean()
    df['macd_slow'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['macd_fast'] - df['macd_slow']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    # Stochastic
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    
    df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
    
    # ADX (Simplified for backtest)
    df['adx'] = abs(df['ema9'] - df['ema21']) / df['ema21'] * 100
    
    return df

def run_quick_backtest(days=90, initial_balance=10000.0):
    """
    Chạy backtest nhanh với dữ liệu giả lập
    
    Args:
        days (int): Số ngày dữ liệu
        initial_balance (float): Số dư ban đầu
    
    Returns:
        Dict: Kết quả backtest
    """
    # Tạo dữ liệu giả lập
    logger.info(f"Tạo dữ liệu giả lập cho {days} ngày...")
    price_data = generate_sample_price_data(days=days)
    price_data = add_indicators(price_data)
    
    logger.info(f"Đã tạo {len(price_data)} candlesticks giả lập")
    
    # Khởi tạo các thành phần
    logger.info("Khởi tạo các thành phần cho backtest...")
    
    # Market Regime Detector
    regime_detector = FractalMarketRegimeDetector(lookback_periods=50)
    
    # Position Sizer
    pythag_sizer = PythagoreanPositionSizer(
        trade_history=[],
        account_balance=initial_balance,
        risk_percentage=1.0
    )
    
    # Monte Carlo Risk Analyzer
    mc_analyzer = MonteCarloRiskAnalyzer(
        trade_history=[],
        default_risk=1.0
    )
    
    # Trading Time Optimizer
    time_optimizer = TradingTimeOptimizer(
        trade_history=[],
        time_segments=24
    )
    
    # Các biến trạng thái
    current_balance = initial_balance
    max_balance = current_balance
    min_balance = current_balance
    current_position = None
    trades = []
    balance_history = [{
        'timestamp': price_data.index[0],
        'balance': current_balance
    }]
    regime_history = []
    trade_count = 0
    win_count = 0
    loss_count = 0
    
    # Log bắt đầu backtest
    logger.info(f"Bắt đầu backtest với {len(price_data)} candlesticks")
    logger.info(f"Thời gian: {price_data.index[0]} đến {price_data.index[-1]}")
    
    # Lặp qua từng candlestick
    for i in range(len(price_data)):
        timestamp = price_data.index[i]
        row = price_data.iloc[i]
        
        # Bỏ qua các candlestick đầu tiên để có đủ dữ liệu cho các indicator
        if i < 20:
            continue
            
        # Phát hiện chế độ thị trường nếu i là bội số của 10 hoặc vừa mở vị thế mới
        if i % 10 == 0 or (i > 0 and current_position is None and trades):
            # Lấy dữ liệu gần đây
            recent_data = price_data.iloc[:i+1].copy()
            
            # Phát hiện chế độ thị trường
            if len(recent_data) > 50:  # Cần đủ dữ liệu cho phát hiện
                regime_result = regime_detector.detect_regime(recent_data)
                regime = regime_result['regime']
                confidence = regime_result['confidence']
                
                # Lưu chế độ thị trường vào lịch sử
                regime_history.append({
                    'time': timestamp,
                    'regime': regime,
                    'confidence': confidence
                })
                
                logger.info(f"Chế độ thị trường tại {timestamp}: {regime} (Độ tin cậy: {confidence:.2f})")
        
        # Cập nhật vị thế hiện tại nếu có
        if current_position:
            # Kiểm tra stop loss
            if current_position['side'] == 'buy':
                if row['low'] <= current_position['stop_loss']:
                    # Thực hiện stop loss
                    pnl = (current_position['stop_loss'] - current_position['entry_price']) * current_position['size']
                    pnl_pct = pnl / (current_position['entry_price'] * current_position['size']) * 100
                    
                    # Cập nhật số dư
                    current_balance += pnl
                    
                    # Cập nhật số liệu thống kê
                    if pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                        
                    # Cập nhật số dư tối đa/tối thiểu
                    max_balance = max(max_balance, current_balance)
                    min_balance = min(min_balance, current_balance)
                    
                    # Ghi log giao dịch
                    trade = {
                        'id': trade_count,
                        'symbol': 'BTCUSDT',
                        'side': current_position['side'],
                        'entry_time': current_position['entry_time'],
                        'entry_price': current_position['entry_price'],
                        'exit_time': timestamp,
                        'exit_price': current_position['stop_loss'],
                        'size': current_position['size'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'balance_after': current_balance,
                        'exit_reason': 'stop_loss'
                    }
                    
                    trades.append(trade)
                    trade_count += 1
                    
                    logger.info(f"Đóng vị thế (stop loss): {current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
                    
                    # Reset vị thế hiện tại
                    current_position = None
                    
                # Kiểm tra take profit
                elif row['high'] >= current_position['take_profit']:
                    # Thực hiện take profit
                    pnl = (current_position['take_profit'] - current_position['entry_price']) * current_position['size']
                    pnl_pct = pnl / (current_position['entry_price'] * current_position['size']) * 100
                    
                    # Cập nhật số dư
                    current_balance += pnl
                    
                    # Cập nhật số liệu thống kê
                    if pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                        
                    # Cập nhật số dư tối đa/tối thiểu
                    max_balance = max(max_balance, current_balance)
                    min_balance = min(min_balance, current_balance)
                    
                    # Ghi log giao dịch
                    trade = {
                        'id': trade_count,
                        'symbol': 'BTCUSDT',
                        'side': current_position['side'],
                        'entry_time': current_position['entry_time'],
                        'entry_price': current_position['entry_price'],
                        'exit_time': timestamp,
                        'exit_price': current_position['take_profit'],
                        'size': current_position['size'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'balance_after': current_balance,
                        'exit_reason': 'take_profit'
                    }
                    
                    trades.append(trade)
                    trade_count += 1
                    
                    logger.info(f"Đóng vị thế (take profit): {current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
                    
                    # Reset vị thế hiện tại
                    current_position = None
                    
            else:  # 'sell'
                if row['high'] >= current_position['stop_loss']:
                    # Thực hiện stop loss
                    pnl = (current_position['entry_price'] - current_position['stop_loss']) * current_position['size']
                    pnl_pct = pnl / (current_position['entry_price'] * current_position['size']) * 100
                    
                    # Cập nhật số dư
                    current_balance += pnl
                    
                    # Cập nhật số liệu thống kê
                    if pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                        
                    # Cập nhật số dư tối đa/tối thiểu
                    max_balance = max(max_balance, current_balance)
                    min_balance = min(min_balance, current_balance)
                    
                    # Ghi log giao dịch
                    trade = {
                        'id': trade_count,
                        'symbol': 'BTCUSDT',
                        'side': current_position['side'],
                        'entry_time': current_position['entry_time'],
                        'entry_price': current_position['entry_price'],
                        'exit_time': timestamp,
                        'exit_price': current_position['stop_loss'],
                        'size': current_position['size'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'balance_after': current_balance,
                        'exit_reason': 'stop_loss'
                    }
                    
                    trades.append(trade)
                    trade_count += 1
                    
                    logger.info(f"Đóng vị thế (stop loss): {current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
                    
                    # Reset vị thế hiện tại
                    current_position = None
                    
                # Kiểm tra take profit
                elif row['low'] <= current_position['take_profit']:
                    # Thực hiện take profit
                    pnl = (current_position['entry_price'] - current_position['take_profit']) * current_position['size']
                    pnl_pct = pnl / (current_position['entry_price'] * current_position['size']) * 100
                    
                    # Cập nhật số dư
                    current_balance += pnl
                    
                    # Cập nhật số liệu thống kê
                    if pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                        
                    # Cập nhật số dư tối đa/tối thiểu
                    max_balance = max(max_balance, current_balance)
                    min_balance = min(min_balance, current_balance)
                    
                    # Ghi log giao dịch
                    trade = {
                        'id': trade_count,
                        'symbol': 'BTCUSDT',
                        'side': current_position['side'],
                        'entry_time': current_position['entry_time'],
                        'entry_price': current_position['entry_price'],
                        'exit_time': timestamp,
                        'exit_price': current_position['take_profit'],
                        'size': current_position['size'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'balance_after': current_balance,
                        'exit_reason': 'take_profit'
                    }
                    
                    trades.append(trade)
                    trade_count += 1
                    
                    logger.info(f"Đóng vị thế (take profit): {current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
                    
                    # Reset vị thế hiện tại
                    current_position = None
        
        # Tạo tín hiệu giao dịch
        if current_position is None and i % 5 == 0:  # Chỉ tạo tín hiệu mỗi 5 candle
            # Tín hiệu đơn giản: RSI oversold/overbought
            rsi = row['rsi']
            
            # Xác định tín hiệu giao dịch
            signal = 'neutral'
            if rsi < 30:
                signal = 'buy'
            elif rsi > 70:
                signal = 'sell'
                
            # Nếu có tín hiệu giao dịch
            if signal in ['buy', 'sell']:
                # Kiểm tra thời gian giao dịch nếu có đủ dữ liệu
                should_trade = True
                if len(trades) >= 10:
                    time_optimizer.trade_history = trades
                    time_optimizer.update_performance_analysis()
                    should_trade, reason = time_optimizer.should_trade_now(timestamp)
                    
                    if not should_trade:
                        logger.info(f"Bỏ qua giao dịch tại {timestamp}: {reason}")
                
                if should_trade:
                    # Tính stop loss và take profit
                    atr = row['atr']
                    
                    if signal == 'buy':
                        stop_loss = row['close'] - 2 * atr
                        take_profit = row['close'] + 2 * atr  # 1:1 risk-reward ratio
                    else:  # 'sell'
                        stop_loss = row['close'] + 2 * atr
                        take_profit = row['close'] - 2 * atr  # 1:1 risk-reward ratio
                    
                    # Tính toán % rủi ro
                    risk_percentage = 1.0
                    
                    # Điều chỉnh % rủi ro theo Monte Carlo nếu có đủ dữ liệu
                    if len(trades) >= 30:
                        mc_analyzer.trade_history = trades
                        mc_risk = mc_analyzer.analyze(
                            confidence_level=0.95,
                            simulations=1000,
                            sequence_length=20,
                            max_risk_limit=2.0
                        )
                        risk_percentage = mc_risk
                        logger.info(f"Điều chỉnh % rủi ro theo Monte Carlo: {risk_percentage:.2f}%")
                    
                    # Điều chỉnh % rủi ro theo Market Regime nếu có đủ dữ liệu
                    if regime_history:
                        regime_adjustment = regime_detector.get_risk_adjustment()
                        risk_percentage *= regime_adjustment
                        logger.info(f"Điều chỉnh % rủi ro theo chế độ thị trường: {risk_percentage:.2f}%")
                    
                    # Điều chỉnh % rủi ro theo thời gian nếu có đủ dữ liệu
                    if len(trades) >= 10:
                        time_adjustment = time_optimizer.get_risk_adjustment(timestamp)
                        risk_percentage *= time_adjustment
                        logger.info(f"Điều chỉnh % rủi ro theo thời gian: {risk_percentage:.2f}%")
                    
                    # Tính kích thước vị thế
                    pythag_sizer.trade_history = trades
                    pythag_sizer.account_balance = current_balance
                    pythag_sizer.max_risk_percentage = risk_percentage
                    
                    position_size = pythag_sizer.calculate_position_size(
                        current_price=row['close'],
                        account_balance=current_balance,
                        entry_price=row['close'],
                        stop_loss_price=stop_loss
                    )
                    
                    # Mở vị thế mới
                    current_position = {
                        'side': signal,
                        'entry_time': timestamp,
                        'entry_price': row['close'],
                        'size': position_size,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit
                    }
                    
                    logger.info(f"Mở vị thế: {signal} | Giá: {row['close']:.2f} | Size: {position_size:.6f} | SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
        
        # Lưu số dư vào lịch sử
        if i % 10 == 0 or i == len(price_data) - 1:  # Mỗi 10 candle hoặc candle cuối cùng
            balance_history.append({
                'timestamp': timestamp,
                'balance': current_balance
            })
    
    # Đóng vị thế cuối cùng nếu còn
    if current_position:
        # Tính P&L
        last_price = price_data['close'].iloc[-1]
        
        if current_position['side'] == 'buy':
            pnl = (last_price - current_position['entry_price']) * current_position['size']
        else:  # 'sell'
            pnl = (current_position['entry_price'] - last_price) * current_position['size']
            
        pnl_pct = pnl / (current_position['entry_price'] * current_position['size']) * 100
        
        # Cập nhật số dư
        current_balance += pnl
        
        # Cập nhật số liệu thống kê
        if pnl > 0:
            win_count += 1
        else:
            loss_count += 1
            
        # Cập nhật số dư tối đa/tối thiểu
        max_balance = max(max_balance, current_balance)
        min_balance = min(min_balance, current_balance)
        
        # Ghi log giao dịch
        trade = {
            'id': trade_count,
            'symbol': 'BTCUSDT',
            'side': current_position['side'],
            'entry_time': current_position['entry_time'],
            'entry_price': current_position['entry_price'],
            'exit_time': price_data.index[-1],
            'exit_price': last_price,
            'size': current_position['size'],
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'balance_after': current_balance,
            'exit_reason': 'end_of_backtest'
        }
        
        trades.append(trade)
        
        logger.info(f"Đóng vị thế cuối cùng: {current_position['side']} | P&L: {pnl:.2f} USD ({pnl_pct:.2f}%)")
    
    # Tính toán kết quả
    
    # Số liệu cơ bản
    profit = current_balance - initial_balance
    profit_pct = profit / initial_balance * 100
    
    # Win rate
    total_trades = len(trades)
    win_rate = win_count / total_trades if total_trades > 0 else 0
    
    # Drawdown
    max_drawdown_pct = (1 - min_balance / max_balance) * 100 if max_balance > 0 else 0
    
    # Thống kê giao dịch
    if total_trades > 0:
        winning_trades = [trade for trade in trades if trade['pnl'] > 0]
        losing_trades = [trade for trade in trades if trade['pnl'] <= 0]
        
        avg_profit = sum(trade['pnl'] for trade in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(trade['pnl'] for trade in losing_trades) / len(losing_trades) if losing_trades else 0
        
        profit_factor = abs(sum(trade['pnl'] for trade in winning_trades) / sum(trade['pnl'] for trade in losing_trades)) if losing_trades and sum(trade['pnl'] for trade in losing_trades) != 0 else float('inf')
    else:
        avg_profit = 0
        avg_loss = 0
        profit_factor = 0
    
    # Phân tích lý do đóng vị thế
    exit_reasons = {}
    for trade in trades:
        reason = trade['exit_reason']
        if reason in exit_reasons:
            exit_reasons[reason] += 1
        else:
            exit_reasons[reason] = 1
    
    # Phân tích chế độ thị trường
    regime_stats = {}
    if regime_history:
        for regime_info in regime_history:
            regime = regime_info['regime']
            if regime in regime_stats:
                regime_stats[regime] += 1
            else:
                regime_stats[regime] = 1
    
    # Lặp qua các giao dịch để gán chế độ thị trường
    if regime_history:
        # Tạo mapping của thời gian -> chế độ
        regime_map = {}
        for entry in regime_history:
            regime_map[entry['time']] = entry['regime']
        
        # Gán chế độ thị trường cho từng giao dịch
        for trade in trades:
            # Tìm chế độ gần nhất với thời gian vào lệnh
            closest_time = min(regime_map.keys(), key=lambda x: abs((x - trade['entry_time']).total_seconds()))
            trade['market_regime'] = regime_map[closest_time]
            
        # Phân tích theo chế độ
        regime_performance = {}
        for regime in set(trade.get('market_regime', 'unknown') for trade in trades):
            regime_trades = [trade for trade in trades if trade.get('market_regime', 'unknown') == regime]
            
            regime_win_count = sum(1 for trade in regime_trades if trade['pnl'] > 0)
            regime_win_rate = regime_win_count / len(regime_trades) if regime_trades else 0
            
            regime_performance[regime] = {
                'trades': len(regime_trades),
                'win_rate': regime_win_rate,
                'pnl': sum(trade['pnl'] for trade in regime_trades)
            }
    
    # Vẽ biểu đồ
    try:
        # Tạo figure với 3 subplot
        fig = plt.figure(figsize=(15, 10))
        
        # 1. Biểu đồ giá và vị thế
        ax1 = plt.subplot2grid((3, 1), (0, 0), rowspan=1)
        
        # Vẽ giá
        ax1.plot(price_data.index, price_data['close'], color='blue', alpha=0.5)
        
        # Vẽ các điểm vào lệnh và thoát lệnh
        buy_entries = [trade['entry_time'] for trade in trades if trade['side'] == 'buy']
        buy_prices = [trade['entry_price'] for trade in trades if trade['side'] == 'buy']
        
        sell_entries = [trade['entry_time'] for trade in trades if trade['side'] == 'sell']
        sell_prices = [trade['entry_price'] for trade in trades if trade['side'] == 'sell']
        
        exits = [trade['exit_time'] for trade in trades]
        exit_prices = [trade['exit_price'] for trade in trades]
        
        if buy_entries:
            ax1.scatter(buy_entries, buy_prices, color='green', marker='^', s=100, label='Buy')
        
        if sell_entries:
            ax1.scatter(sell_entries, sell_prices, color='red', marker='v', s=100, label='Sell')
        
        if exits:
            ax1.scatter(exits, exit_prices, color='black', marker='x', s=70, label='Exit')
        
        ax1.set_title('Giá và Vị thế')
        ax1.set_ylabel('Giá')
        ax1.grid(True)
        ax1.legend()
        
        # 2. Biểu đồ số dư
        ax2 = plt.subplot2grid((3, 1), (1, 0), rowspan=1)
        
        if balance_history:
            timestamps = [entry['timestamp'] for entry in balance_history]
            balances = [entry['balance'] for entry in balance_history]
            
            ax2.plot(timestamps, balances, color='green')
            ax2.axhline(y=initial_balance, color='red', linestyle='--')
            
            ax2.set_title('Đường cong Equity')
            ax2.set_ylabel('Số dư')
            ax2.grid(True)
        
        # 3. Biểu đồ Win/Loss và phân bố P&L
        ax3 = plt.subplot2grid((3, 1), (2, 0), rowspan=1)
        
        if trades:
            # Phân bố P&L
            pnl_values = [trade['pnl_pct'] for trade in trades]
            
            ax3.hist(pnl_values, bins=10, alpha=0.7, color='blue')
            ax3.axvline(x=0, color='red', linestyle='--')
            
            ax3.set_title('Phân bố P&L (%)')
            ax3.set_xlabel('P&L (%)')
            ax3.set_ylabel('Số lượng')
            ax3.grid(True)
        
        plt.tight_layout()
        
        # Lưu biểu đồ
        plt.savefig("backtest_charts/quick_backtest_results.png")
        
        logger.info("Đã lưu biểu đồ vào backtest_charts/quick_backtest_results.png")
        
    except Exception as e:
        logger.error(f"Lỗi khi vẽ biểu đồ: {e}")
    
    # Tạo kết quả
    results = {
        'summary': {
            'initial_balance': initial_balance,
            'final_balance': current_balance,
            'profit': profit,
            'profit_pct': profit_pct,
            'max_balance': max_balance,
            'min_balance': min_balance,
            'max_drawdown_pct': max_drawdown_pct,
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'start_date': price_data.index[0],
            'end_date': price_data.index[-1]
        },
        'trades': trades,
        'balance_history': balance_history,
        'exit_reasons': exit_reasons,
        'regime_stats': regime_stats
    }
    
    if 'regime_performance' in locals():
        results['regime_performance'] = regime_performance
    
    # Log kết quả
    logger.info("\n" + "="*50)
    logger.info("KẾT QUẢ BACKTEST")
    logger.info("="*50)
    logger.info(f"Số dư ban đầu: ${initial_balance:.2f}")
    logger.info(f"Số dư cuối cùng: ${current_balance:.2f}")
    logger.info(f"Lợi nhuận: ${profit:.2f} ({profit_pct:.2f}%)")
    logger.info(f"Drawdown tối đa: {max_drawdown_pct:.2f}%")
    logger.info(f"Tổng số giao dịch: {total_trades}")
    logger.info(f"Win rate: {win_rate:.2f}")
    logger.info(f"Profit factor: {profit_factor:.2f}")
    logger.info("Lý do đóng vị thế:")
    for reason, count in exit_reasons.items():
        logger.info(f"  - {reason}: {count}")
    if regime_stats:
        logger.info("Chế độ thị trường:")
        for regime, count in regime_stats.items():
            logger.info(f"  - {regime}: {count}")
    logger.info("="*50)
    
    if 'regime_performance' in locals():
        logger.info("Hiệu suất theo chế độ thị trường:")
        for regime, stats in regime_performance.items():
            logger.info(f"  - {regime}: Số giao dịch: {stats['trades']}, Win rate: {stats['win_rate']:.2f}, P&L: ${stats['pnl']:.2f}")
    
    # Lưu kết quả vào file
    with open("backtest_results/quick_backtest_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)
        
    logger.info("Đã lưu kết quả vào backtest_results/quick_backtest_results.json")
    
    # Phân tích Monte Carlo
    if len(trades) >= 20:
        logger.info("\n" + "="*50)
        logger.info("PHÂN TÍCH MONTE CARLO")
        logger.info("="*50)
        
        # Cập nhật trade history
        mc_analyzer.trade_history = trades
        
        # Lấy phân phối drawdown
        drawdown_dist = mc_analyzer.get_drawdown_distribution(simulations=1000)
        
        if 'percentiles' in drawdown_dist:
            logger.info(f"Drawdown VaR (95%): {drawdown_dist['percentiles']['95%']:.2f}%")
            logger.info(f"Drawdown VaR (99%): {drawdown_dist['percentiles']['99%']:.2f}%")
        
        # Lấy mức rủi ro đề xuất
        risk_levels = mc_analyzer.get_risk_levels()
        
        logger.info("Mức rủi ro đề xuất:")
        for level, risk in risk_levels.items():
            logger.info(f"  - Mức tin cậy {level}: {risk:.2f}%")
    
    return results

def main():
    """Hàm chính để chạy backtest"""
    results = run_quick_backtest(days=90, initial_balance=10000.0)
    
    print("\n" + "="*50)
    print("KẾT QUẢ BACKTEST NHANH")
    print("="*50)
    print(f"Số dư ban đầu: ${results['summary']['initial_balance']:.2f}")
    print(f"Số dư cuối cùng: ${results['summary']['final_balance']:.2f}")
    print(f"Lợi nhuận: ${results['summary']['profit']:.2f} ({results['summary']['profit_pct']:.2f}%)")
    print(f"Tổng số giao dịch: {results['summary']['total_trades']}")
    print(f"Win rate: {results['summary']['win_rate']:.2f}")
    print(f"Profit factor: {results['summary']['profit_factor']:.2f}")
    print("="*50)
    
    return results

if __name__ == "__main__":
    main()