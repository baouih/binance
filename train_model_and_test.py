#!/usr/bin/env python3
"""
Script để huấn luyện mô hình ML và sau đó chạy backtest
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('train_and_test')

# Import các module cần thiết
try:
    from app.binance_api import BinanceAPI
    from app.data_processor import DataProcessor
    from app.ml_optimizer import MLOptimizer
    from app.market_regime_detector import MarketRegimeDetector
    from app.strategy import MLStrategy, RSIStrategy, MACDStrategy, EMACrossStrategy, BBandsStrategy, CombinedStrategy
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    sys.exit(1)

def train_model(symbol='BTCUSDT', interval='1h', days=90):
    """
    Huấn luyện mô hình ML
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        days (int): Số ngày để lấy dữ liệu lịch sử
    """
    logger.info(f"=== HUẤN LUYỆN MÔ HÌNH ML ===")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Interval: {interval}")
    logger.info(f"Days: {days}")
    
    # Khởi tạo API và các module
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Lấy dữ liệu lịch sử
    df = data_processor.get_historical_data(symbol, interval, lookback_days=days)
    
    if df is None or df.empty:
        logger.error("Không thể lấy dữ liệu lịch sử")
        return None
    
    logger.info(f"Đã lấy {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
    
    # Khởi tạo ML Optimizer
    ml_optimizer = MLOptimizer()
    
    # Chuẩn bị dữ liệu huấn luyện
    X = df.copy()
    
    # Tạo nhãn cho mục tiêu (target): Giá trong 6 giờ tiếp theo sẽ tăng hay giảm
    lookahead = 6  # Nhìn trước 6 candlesticks
    threshold = 0.003  # 0.3% thay đổi giá được coi là tín hiệu
    
    # Tạo cột mục tiêu: 1 = tăng giá, -1 = giảm giá, 0 = không đổi
    future_returns = df['close'].pct_change(periods=lookahead).shift(-lookahead)
    y = pd.Series(0, index=df.index)
    y[future_returns > threshold] = 1  # Tín hiệu BUY nếu giá tăng hơn threshold
    y[future_returns < -threshold] = -1  # Tín hiệu SELL nếu giá giảm hơn threshold
    
    # Huấn luyện mô hình
    logger.info("Bắt đầu huấn luyện mô hình...")
    ml_optimizer.train_models(X, y)
    
    # Lưu mô hình
    os.makedirs('models', exist_ok=True)
    ml_optimizer.save_models('models')
    logger.info("Đã lưu mô hình vào thư mục 'models'")
    
    return ml_optimizer

def run_backtest_with_ml(ml_optimizer, symbol='BTCUSDT', interval='1h', days=30, 
                      initial_balance=10000.0, leverage=5, risk_percentage=1.0,
                      strategy_type='ml'):
    """
    Chạy backtest với mô hình ML đã huấn luyện
    
    Args:
        ml_optimizer: ML Optimizer đã huấn luyện
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        days (int): Số ngày để lấy dữ liệu lịch sử
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        strategy_type (str): Loại chiến lược
    """
    logger.info(f"=== BACKTEST VỚI MÔ HÌNH ML ===")
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
    
    # Khởi tạo market regime detector
    market_regime_detector = MarketRegimeDetector()
    
    # Tạo chiến lược dựa trên loại được chỉ định
    if strategy_type == 'ml':
        strategy = MLStrategy(ml_optimizer=ml_optimizer, market_regime_detector=market_regime_detector)
    elif strategy_type == 'combined':
        strategies = [
            RSIStrategy(overbought=70, oversold=30),
            MACDStrategy(),
            EMACrossStrategy(short_period=9, long_period=21),
            BBandsStrategy(deviation_multiplier=2.0),
            MLStrategy(ml_optimizer=ml_optimizer, market_regime_detector=market_regime_detector)
        ]
        weights = [0.2, 0.2, 0.2, 0.2, 0.2]  # Trọng số bằng nhau
        strategy = CombinedStrategy(strategies=strategies, weights=weights)
    else:
        # Mặc định sử dụng ML Strategy
        strategy = MLStrategy(ml_optimizer=ml_optimizer, market_regime_detector=market_regime_detector)
    
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
    start_idx = 50  # Bỏ qua 50 candlesticks đầu tiên
    
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
        
        import matplotlib.pyplot as plt
        # Vẽ đồ thị
        plt.figure(figsize=(12, 6))
        plt.plot(dates, equity_curve)
        plt.title(f'Đường cong vốn - {strategy_type.upper()} ({symbol} {interval})')
        plt.xlabel('Thời gian')
        plt.ylabel('Vốn ($)')
        plt.grid(True)
        plt.savefig('backtest_ml_results.png')
        logger.info(f"Đã lưu đồ thị đường cong vốn vào 'backtest_ml_results.png'")
        
        # Lưu giao dịch
        trades_df = pd.DataFrame(trades)
        trades_df.to_csv('backtest_ml_trades.csv', index=False)
        logger.info(f"Đã lưu lịch sử giao dịch vào 'backtest_ml_trades.csv'")
        
        # Trả về kết quả
        return {
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
            'max_drawdown': max_drawdown
        }
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong backtest")
        return None

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Huấn luyện mô hình ML và chạy backtest')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian (mặc định: 1h)')
    parser.add_argument('--train-days', type=int, default=180, help='Số ngày dữ liệu lịch sử để huấn luyện (mặc định: 180)')
    parser.add_argument('--test-days', type=int, default=30, help='Số ngày dữ liệu lịch sử để test (mặc định: 30)')
    parser.add_argument('--strategy', type=str, default='ml', 
                       choices=['ml', 'combined'],
                       help='Loại chiến lược giao dịch (mặc định: ml)')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=2.0, help='Phần trăm rủi ro (mặc định: 2%)')
    
    args = parser.parse_args()
    
    # 1. Huấn luyện mô hình
    ml_optimizer = train_model(
        symbol=args.symbol,
        interval=args.interval,
        days=args.train_days
    )
    
    if ml_optimizer is not None:
        # 2. Chạy backtest với mô hình đã huấn luyện
        run_backtest_with_ml(
            ml_optimizer=ml_optimizer,
            symbol=args.symbol,
            interval=args.interval,
            days=args.test_days,
            initial_balance=args.balance,
            leverage=args.leverage,
            risk_percentage=args.risk,
            strategy_type=args.strategy
        )

if __name__ == "__main__":
    main()