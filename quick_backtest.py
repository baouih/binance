#!/usr/bin/env python3
"""
Script để chạy backtest nhanh và hiển thị kết quả lãi/lỗ
"""

import os
import sys
import json
import time
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('quick_backtest')

# Import các module cần thiết
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.market_regime_detector import MarketRegimeDetector
    from app.strategy_factory import StrategyFactory
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    sys.exit(1)

def run_backtest(symbol='BTCUSDT', interval='1h', days=30, strategy_type='auto', 
                initial_balance=10000.0, leverage=5, risk_percentage=1.0):
    """
    Chạy backtest nhanh và hiển thị kết quả
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        days (int): Số ngày để lấy dữ liệu lịch sử
        strategy_type (str): Loại chiến lược
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
    """
    logger.info(f"=== CHẠY BACKTEST NHANH ===")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Days: {days}")
    logger.info(f"Strategy: {strategy_type}")
    logger.info(f"Initial Balance: ${initial_balance}")
    logger.info(f"Leverage: {leverage}x")
    logger.info(f"Risk: {risk_percentage}%")
    
    # Khởi tạo API và các module
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Lấy dữ liệu lịch sử
    df = data_processor.get_historical_data(symbol, interval, lookback_days=days)
    
    if df is None or df.empty:
        logger.error("Không thể lấy dữ liệu lịch sử")
        return
    
    logger.info(f"Đã lấy {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    
    # Tạo chiến lược thông qua factory
    strategy = StrategyFactory.create_strategy(
        strategy_type=strategy_type,
        use_ml=True
    )
    
    if strategy is None:
        logger.error(f"Không thể tạo chiến lược {strategy_type}")
        return
    
    logger.info(f"Đã tạo chiến lược {type(strategy).__name__}")
    
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
    
    # Để dự đoán tốt hơn, chúng ta sẽ bỏ qua một số candlesticks đầu tiên
    start_idx = 100  # Bỏ qua 100 candlesticks đầu tiên
    
    for i in range(start_idx, len(df) - 1):
        current_data = df.iloc[:i+1]
        signal = strategy.generate_signal(current_data)
        
        current_price = current_data['close'].iloc[-1]
        current_date = current_data.index[-1]
        
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
                
                logger.info(f"Mở vị thế MUA tại {entry_date}: {entry_price}, Số lượng: {order_qty}")
                
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
                
                logger.info(f"Mở vị thế BÁN tại {entry_date}: {entry_price}, Số lượng: {order_qty}")
        
        # Đóng vị thế hiện tại
        elif ((current_position['side'] == 'BUY' and signal == -1) or 
              (current_position['side'] == 'SELL' and signal == 1)):
            
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
            
            logger.info(f"Đóng vị thế {current_position['side']} tại {exit_date}: {exit_price}, PnL: {pnl*100:.2f}%, ${pnl_amount:.2f}")
            
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
        plt.figure(figsize=(12, 6))
        plt.plot(dates, equity_curve)
        plt.title(f'Đường cong vốn - {strategy_type.upper()} ({symbol} {interval})')
        plt.xlabel('Thời gian')
        plt.ylabel('Vốn ($)')
        plt.grid(True)
        plt.savefig('backtest_results.png')
        logger.info(f"Đã lưu đồ thị đường cong vốn vào 'backtest_results.png'")
        
        # Lưu giao dịch
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('backtest_trades.csv', index=False)
        logger.info(f"Đã lưu lịch sử giao dịch vào 'backtest_trades.csv'")
        
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
            'start_date': str(df.index[0]),
            'end_date': str(df.index[-1])
        }
        
        with open('backtest_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Đã lưu kết quả backtest vào 'backtest_results.json'")
        
        return results
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong backtest")
        return None

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ backtest nhanh')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--days', type=int, default=90, help='Số ngày dữ liệu lịch sử (mặc định: 90)')
    parser.add_argument('--strategy', type=str, default='auto', 
                       choices=['auto', 'ml', 'combined', 'rsi', 'macd', 'ema', 'bbands', 'advanced_ml', 'regime_ml'],
                       help='Loại chiến lược giao dịch (mặc định: auto)')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro (mặc định: 1%)')
    
    args = parser.parse_args()
    
    run_backtest(
        symbol=args.symbol,
        interval=args.interval,
        days=args.days,
        strategy_type=args.strategy,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk
    )

if __name__ == "__main__":
    main()