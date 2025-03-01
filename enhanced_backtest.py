#!/usr/bin/env python3
"""
Script backtest nâng cao sử dụng dữ liệu thực từ Binance

Script này thực hiện backtesting chi tiết hơn với các tính năng nâng cao:
1. Sử dụng dữ liệu thực từ Binance (không phải dữ liệu giả lập)
2. Hỗ trợ phân tích đa khung thời gian
3. Tích hợp với quản lý vốn và quản lý rủi ro thực tế
4. Tạo báo cáo và biểu đồ chi tiết
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
from typing import Dict, List, Tuple, Any, Optional
import traceback

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("enhanced_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("enhanced_backtest")

# Tạo thư mục kết quả nếu chưa tồn tại
os.makedirs("backtest_results", exist_ok=True)
os.makedirs("backtest_charts", exist_ok=True)

# Import các module cần thiết
try:
    # Thử import từ app 
    sys.path.append('.')
    try:
        from app.binance_api import BinanceAPI
        from app.data_processor import DataProcessor
        from app.market_regime_detector import MarketRegimeDetector
        from app.strategy_factory import StrategyFactory
        from position_sizing import create_position_sizer
        from order_execution import OrderExecutionFactory
        from risk_manager import RiskManager
    except ImportError:
        # Thử import từ thư mục gốc
        from binance_api import BinanceAPI
        from data_processor import DataProcessor
        from market_regime_detector import MarketRegimeDetector
        from strategy_factory import StrategyFactory
        from position_sizing import create_position_sizer
        from order_execution import OrderExecutionFactory
        from risk_manager import RiskManager
except ImportError as e:
    logger.error(f"Lỗi khi import modules: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def load_historical_data(symbol: str, interval: str, data_dir: str = 'test_data') -> pd.DataFrame:
    """
    Tải dữ liệu lịch sử từ file CSV
    
    Args:
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        data_dir (str): Thư mục chứa dữ liệu
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu lịch sử
    """
    try:
        file_path = os.path.join(data_dir, symbol, f"{symbol}_{interval}.csv")
        
        if not os.path.exists(file_path):
            logger.error(f"File dữ liệu không tồn tại: {file_path}")
            return None
        
        df = pd.read_csv(file_path)
        
        # Chuyển đổi timestamp thành datetime index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Đã tải {len(df)} candles từ {df.index[0]} đến {df.index[-1]}")
        return df
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu: {str(e)}")
        return None

def run_enhanced_backtest(
    symbol='BTCUSDT', 
    primary_interval='1h',
    secondary_intervals=None,
    strategy_type='auto',
    initial_balance=10000.0, 
    leverage=5, 
    risk_percentage=1.0,
    position_sizing_method='dynamic',
    risk_method='fixed',
    stop_loss_pct=5.0,
    take_profit_pct=15.0,
    trailing_stop=True,
    data_dir='test_data',
    start_date=None,
    end_date=None,
    output_prefix=''
):
    """
    Chạy backtest nâng cao với dữ liệu thực
    
    Args:
        symbol (str): Cặp giao dịch
        primary_interval (str): Khung thời gian chính
        secondary_intervals (List[str], optional): Danh sách khung thời gian phụ
        strategy_type (str): Loại chiến lược
        initial_balance (float): Số dư ban đầu
        leverage (int): Đòn bẩy
        risk_percentage (float): Phần trăm rủi ro
        position_sizing_method (str): Phương pháp sizing ('fixed', 'dynamic', 'kelly', 'anti_martingale')
        risk_method (str): Phương pháp quản lý rủi ro ('fixed', 'adaptive', 'volatility_based')
        stop_loss_pct (float): Phần trăm cắt lỗ
        take_profit_pct (float): Phần trăm chốt lời
        trailing_stop (bool): Sử dụng trailing stop hay không
        data_dir (str): Thư mục chứa dữ liệu
        start_date (str, optional): Ngày bắt đầu (YYYY-MM-DD)
        end_date (str, optional): Ngày kết thúc (YYYY-MM-DD)
    """
    secondary_intervals = secondary_intervals or []
    
    logger.info(f"=== CHẠY BACKTEST NÂNG CAO ===")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Khung thời gian chính: {primary_interval}")
    logger.info(f"Khung thời gian phụ: {secondary_intervals}")
    logger.info(f"Chiến lược: {strategy_type}")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Rủi ro: {risk_percentage}%")
    logger.info(f"Phương pháp sizing: {position_sizing_method}")
    logger.info(f"Phương pháp quản lý rủi ro: {risk_method}")
    logger.info(f"Stop Loss: {stop_loss_pct}%")
    logger.info(f"Take Profit: {take_profit_pct}%")
    logger.info(f"Trailing Stop: {'Có' if trailing_stop else 'Không'}")
    
    # Tải dữ liệu lịch sử
    df_primary = load_historical_data(symbol, primary_interval, data_dir)
    
    if df_primary is None or df_primary.empty:
        logger.error("Không thể tải dữ liệu lịch sử cho khung thời gian chính")
        return
    
    # Lọc dữ liệu theo ngày bắt đầu và kết thúc nếu có
    if start_date:
        df_primary = df_primary[df_primary.index >= start_date]
    
    if end_date:
        df_primary = df_primary[df_primary.index <= end_date]
    
    if df_primary.empty:
        logger.error("Không có dữ liệu trong khoảng thời gian đã chọn")
        return
    
    # Tải dữ liệu cho các khung thời gian phụ
    secondary_data = {}
    for interval in secondary_intervals:
        df_secondary = load_historical_data(symbol, interval, data_dir)
        if df_secondary is not None and not df_secondary.empty:
            # Lọc dữ liệu theo ngày bắt đầu và kết thúc nếu có
            if start_date:
                df_secondary = df_secondary[df_secondary.index >= start_date]
            
            if end_date:
                df_secondary = df_secondary[df_secondary.index <= end_date]
                
            if not df_secondary.empty:
                secondary_data[interval] = df_secondary
                logger.info(f"Đã tải dữ liệu khung thời gian phụ {interval}: {len(df_secondary)} candles")
    
    # Khởi tạo binance api và data processor
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Tính toán các chỉ báo kỹ thuật cho dữ liệu chính
    df_primary = data_processor.add_indicators(df_primary.copy())
    
    # Tính toán các chỉ báo kỹ thuật cho dữ liệu phụ
    for interval, df in secondary_data.items():
        secondary_data[interval] = data_processor.add_indicators(df.copy())
    
    # Khởi tạo market regime detector
    market_regime_detector = MarketRegimeDetector(data_folder=data_dir)
    
    # Tạo chiến lược thông qua factory
    strategy = StrategyFactory.create_strategy(
        strategy_type=strategy_type,
        use_ml=True
    )
    
    if strategy is None:
        logger.error(f"Không thể tạo chiến lược {strategy_type}")
        return
    
    logger.info(f"Đã tạo chiến lược {type(strategy).__name__}")
    
    # Khởi tạo position sizer
    position_sizer = create_position_sizer(
        sizer_type=position_sizing_method,
        account_balance=initial_balance,
        risk_percentage=risk_percentage
    )
    
    # Khởi tạo risk manager
    risk_manager = RiskManager(
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        trailing_stop=trailing_stop,
        max_trades=5,
        risk_method=risk_method
    )
    
    # Danh sách để lưu trữ các giao dịch
    trades = []
    
    # Danh sách để lưu trữ giá trị vốn
    equity_curve = [initial_balance]
    dates = [df_primary.index[0]]
    
    # Trạng thái giao dịch hiện tại
    current_position = None
    balance = initial_balance
    
    # Chạy backtest
    logger.info("Bắt đầu backtest...")
    
    # Để dự đoán tốt hơn, chúng ta sẽ bỏ qua một số candlesticks đầu tiên
    start_idx = min(100, len(df_primary) // 4)  # Bỏ qua 100 candles đầu tiên hoặc 1/4 dữ liệu, tùy theo giá trị nào nhỏ hơn
    
    for i in range(start_idx, len(df_primary) - 1):
        current_data = df_primary.iloc[:i+1].copy()
        current_date = current_data.index[-1]
        
        # Lấy dữ liệu từ các khung thời gian phụ tại thời điểm hiện tại
        multi_timeframe_data = {}
        for interval, df in secondary_data.items():
            # Lấy dữ liệu cho đến thời điểm hiện tại
            mask = df.index <= current_date
            if mask.any():
                multi_timeframe_data[interval] = df[mask].copy()
        
        # Cập nhật market regime
        current_regime = None
        if len(current_data) > 50:  # Cần đủ dữ liệu để xác định chế độ thị trường
            market_data = current_data.iloc[-50:].copy()  # Sử dụng 50 candles gần nhất
            current_regime = market_regime_detector.detect_regime(market_data)
            
            if current_regime:
                logger.debug(f"Chế độ thị trường hiện tại: {current_regime}")
        
        # Sinh tín hiệu giao dịch
        signal = 0
        signal_strength = 0
        signal_data = {'primary': current_data}
        signal_data.update(multi_timeframe_data)
        
        try:
            # Tạo tín hiệu từ chiến lược
            signal_result = strategy.generate_signal(
                signal_data, 
                timeframe=primary_interval,
                market_regime=current_regime
            )
            
            if isinstance(signal_result, dict):
                signal = signal_result.get('signal', 0)
                signal_strength = signal_result.get('strength', 0)
            else:
                signal = signal_result
                signal_strength = 1.0 if abs(signal) > 0 else 0
                
        except Exception as e:
            logger.error(f"Lỗi khi sinh tín hiệu: {str(e)}")
            logger.error(traceback.format_exc())
            signal = 0
            signal_strength = 0
        
        current_price = current_data['close'].iloc[-1]
        
        # Mở vị thế mới nếu chưa có vị thế
        if current_position is None:
            if signal == 1:  # Tín hiệu mua
                # Tính toán kích thước vị thế dựa trên quản lý rủi ro
                volatility = current_data['atr'].iloc[-1] if 'atr' in current_data else None
                
                position_size_amount = position_sizer.calculate_position_size(
                    current_price=current_price,
                    account_balance=balance,
                    leverage=leverage,
                    volatility=volatility,
                    market_data=current_data
                )
                
                order_qty = position_size_amount / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Điều chỉnh các thông số quản lý rủi ro dựa trên điều kiện thị trường
                stop_loss, take_profit = risk_manager.calculate_stop_levels(
                    entry_price=entry_price,
                    side='BUY',
                    market_data=current_data,
                    position_size=position_size_amount,
                    balance=balance
                )
                
                current_position = {
                    'side': 'BUY',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'trailing_stop_activated': False,
                    'trailing_stop_level': None
                }
                
                logger.info(f"Mở vị thế MUA tại {entry_date}: ${entry_price:.2f}, Số lượng: {order_qty:.6f}, "
                           f"SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}")
                
            elif signal == -1:  # Tín hiệu bán
                # Tính toán kích thước vị thế dựa trên quản lý rủi ro
                volatility = current_data['atr'].iloc[-1] if 'atr' in current_data else None
                
                position_size_amount = position_sizer.calculate_position_size(
                    current_price=current_price,
                    account_balance=balance,
                    leverage=leverage,
                    volatility=volatility,
                    market_data=current_data
                )
                
                order_qty = position_size_amount / current_price
                entry_price = current_price
                entry_date = current_date
                
                # Điều chỉnh các thông số quản lý rủi ro dựa trên điều kiện thị trường
                stop_loss, take_profit = risk_manager.calculate_stop_levels(
                    entry_price=entry_price,
                    side='SELL',
                    market_data=current_data,
                    position_size=position_size_amount,
                    balance=balance
                )
                
                current_position = {
                    'side': 'SELL',
                    'entry_price': entry_price,
                    'quantity': order_qty,
                    'entry_date': entry_date,
                    'leverage': leverage,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'trailing_stop_activated': False,
                    'trailing_stop_level': None
                }
                
                logger.info(f"Mở vị thế BÁN tại {entry_date}: ${entry_price:.2f}, Số lượng: {order_qty:.6f}, "
                           f"SL: ${stop_loss:.2f}, TP: ${take_profit:.2f}")
        
        # Cập nhật vị thế hiện tại
        elif current_position is not None:
            # Cập nhật trailing stop nếu có
            if trailing_stop and current_position['trailing_stop_activated'] is False:
                if current_position['side'] == 'BUY' and current_price >= current_position['entry_price'] * (1 + take_profit_pct / 200):
                    # Kích hoạt trailing stop khi giá đạt 50% mức take profit
                    current_position['trailing_stop_activated'] = True
                    current_position['trailing_stop_level'] = max(
                        current_position['stop_loss'],
                        current_price * (1 - stop_loss_pct / 100)
                    )
                    logger.info(f"Kích hoạt trailing stop tại ${current_price:.2f}, Mức: ${current_position['trailing_stop_level']:.2f}")
                
                elif current_position['side'] == 'SELL' and current_price <= current_position['entry_price'] * (1 - take_profit_pct / 200):
                    # Kích hoạt trailing stop khi giá đạt 50% mức take profit
                    current_position['trailing_stop_activated'] = True
                    current_position['trailing_stop_level'] = min(
                        current_position['stop_loss'],
                        current_price * (1 + stop_loss_pct / 100)
                    )
                    logger.info(f"Kích hoạt trailing stop tại ${current_price:.2f}, Mức: ${current_position['trailing_stop_level']:.2f}")
            
            # Cập nhật trailing stop level
            if current_position['trailing_stop_activated']:
                if current_position['side'] == 'BUY' and current_price > current_position['trailing_stop_level'] * (1 + stop_loss_pct / 200):
                    # Trailing stop theo giá tăng
                    new_stop = current_price * (1 - stop_loss_pct / 100)
                    if new_stop > current_position['trailing_stop_level']:
                        current_position['trailing_stop_level'] = new_stop
                        logger.info(f"Cập nhật trailing stop lên ${current_position['trailing_stop_level']:.2f}")
                
                elif current_position['side'] == 'SELL' and current_price < current_position['trailing_stop_level'] * (1 - stop_loss_pct / 200):
                    # Trailing stop theo giá giảm
                    new_stop = current_price * (1 + stop_loss_pct / 100)
                    if new_stop < current_position['trailing_stop_level']:
                        current_position['trailing_stop_level'] = new_stop
                        logger.info(f"Cập nhật trailing stop xuống ${current_position['trailing_stop_level']:.2f}")
            
            # Kiểm tra điều kiện đóng vị thế
            exit_reason = None
            
            # Kiểm tra take profit
            if (current_position['side'] == 'BUY' and current_price >= current_position['take_profit']) or \
               (current_position['side'] == 'SELL' and current_price <= current_position['take_profit']):
                exit_reason = "Take Profit"
            
            # Kiểm tra stop loss hoặc trailing stop
            elif (current_position['side'] == 'BUY' and current_price <= 
                  (current_position['trailing_stop_level'] if current_position['trailing_stop_activated'] else current_position['stop_loss'])) or \
                 (current_position['side'] == 'SELL' and current_price >= 
                  (current_position['trailing_stop_level'] if current_position['trailing_stop_activated'] else current_position['stop_loss'])):
                exit_reason = "Trailing Stop" if current_position['trailing_stop_activated'] else "Stop Loss"
            
            # Kiểm tra đảo chiều tín hiệu
            elif (current_position['side'] == 'BUY' and signal == -1) or \
                 (current_position['side'] == 'SELL' and signal == 1):
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
                    'stop_loss': current_position['stop_loss'],
                    'take_profit': current_position['take_profit'],
                    'trailing_stop': current_position['trailing_stop_activated'],
                    'exit_reason': exit_reason,
                    'pnl_percent': pnl * 100,
                    'pnl_amount': pnl_amount,
                    'fees': fees,
                    'balance': balance,
                    'market_regime': current_regime
                }
                trades.append(trade)
                
                logger.info(f"Đóng vị thế {current_position['side']} tại {exit_date}: ${exit_price:.2f}, "
                           f"PnL: {pnl*100:.2f}%, ${pnl_amount:.2f}, Lý do: {exit_reason}")
                
                # Reset vị thế
                current_position = None
                
                # Cập nhật position sizer với kết quả giao dịch
                position_sizer.update_trade_result(pnl > 0)
        
        # Cập nhật đường cong vốn
        if i % 24 == 0 or i == len(df_primary) - 2:  # Cập nhật hàng ngày hoặc ở candle cuối cùng
            equity_curve.append(balance)
            dates.append(current_date)
    
    # Tính toán số liệu hiệu suất
    num_trades = len(trades)
    
    if num_trades > 0:
        performance_metrics = calculate_performance_metrics(trades, initial_balance)
        
        # Hiển thị kết quả
        display_results(
            performance_metrics=performance_metrics,
            trades=trades,
            equity_curve=equity_curve,
            dates=dates,
            symbol=symbol,
            interval=primary_interval,
            strategy_type=strategy_type,
            initial_balance=initial_balance
        )
        
        return performance_metrics
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong backtest")
        return None

def calculate_performance_metrics(trades: List[Dict], initial_balance: float) -> Dict:
    """
    Tính toán các chỉ số hiệu suất từ lịch sử giao dịch
    
    Args:
        trades (List[Dict]): Danh sách các giao dịch
        initial_balance (float): Số dư ban đầu
        
    Returns:
        Dict: Các chỉ số hiệu suất
    """
    num_trades = len(trades)
    winning_trades = sum(1 for t in trades if t['pnl_amount'] > 0)
    losing_trades = sum(1 for t in trades if t['pnl_amount'] <= 0)
    
    win_rate = (winning_trades / num_trades) * 100 if num_trades > 0 else 0
    
    total_profit = sum(t['pnl_amount'] for t in trades if t['pnl_amount'] > 0)
    total_loss = abs(sum(t['pnl_amount'] for t in trades if t['pnl_amount'] <= 0))
    
    profit_factor = (total_profit / total_loss) if total_loss != 0 else float('inf')
    
    avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
    avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
    
    # Tính risk-reward ratio
    risk_reward_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else float('inf')
    
    # Tính max drawdown
    peak = initial_balance
    drawdowns = []
    max_drawdown_value = 0
    max_drawdown_start = None
    max_drawdown_end = None
    
    current_drawdown_start = None
    
    for i, t in enumerate(trades):
        balance = t['balance']
        
        if balance > peak:
            peak = balance
            current_drawdown_start = None
        else:
            dd = (peak - balance) / peak
            drawdowns.append(dd)
            
            if current_drawdown_start is None:
                current_drawdown_start = t['exit_date']
            
            if dd > max_drawdown_value:
                max_drawdown_value = dd
                max_drawdown_start = current_drawdown_start
                max_drawdown_end = t['exit_date']
    
    max_drawdown = max(drawdowns) * 100 if drawdowns else 0
    
    # Tính thời gian drawdown
    max_drawdown_duration = None
    if max_drawdown_start and max_drawdown_end:
        try:
            start_date = datetime.strptime(str(max_drawdown_start).split(' ')[0], '%Y-%m-%d')
            end_date = datetime.strptime(str(max_drawdown_end).split(' ')[0], '%Y-%m-%d')
            max_drawdown_duration = (end_date - start_date).days
        except:
            # Nếu có lỗi khi chuyển đổi ngày, thử cách khác
            try:
                if isinstance(max_drawdown_start, pd.Timestamp):
                    start_date = max_drawdown_start.to_pydatetime()
                else:
                    start_date = pd.to_datetime(max_drawdown_start)
                
                if isinstance(max_drawdown_end, pd.Timestamp):
                    end_date = max_drawdown_end.to_pydatetime()
                else:
                    end_date = pd.to_datetime(max_drawdown_end)
                
                max_drawdown_duration = (end_date - start_date).days
            except:
                max_drawdown_duration = None
    
    # Tính Expectancy và Expectancy Score
    expectancy = ((win_rate / 100) * avg_profit) - ((1 - win_rate / 100) * avg_loss)
    expectancy_score = expectancy * num_trades / 100  # Scale theo số lượng giao dịch
    
    # Tính Sharpe Ratio (giả sử risk-free rate = 0)
    if len(trades) > 1:
        returns = [t['pnl_percent'] for t in trades]
        mean_return = sum(returns) / len(returns)
        std_dev = np.std(returns) if len(returns) > 1 else 1
        sharpe_ratio = (mean_return / std_dev) * np.sqrt(len(returns)) if std_dev != 0 else 0
    else:
        sharpe_ratio = 0
    
    # Thống kê theo loại đóng lệnh
    exit_reason_stats = {}
    for t in trades:
        reason = t['exit_reason']
        if reason not in exit_reason_stats:
            exit_reason_stats[reason] = {
                'count': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0
            }
        
        exit_reason_stats[reason]['count'] += 1
        if t['pnl_amount'] > 0:
            exit_reason_stats[reason]['wins'] += 1
        else:
            exit_reason_stats[reason]['losses'] += 1
        exit_reason_stats[reason]['total_pnl'] += t['pnl_amount']
    
    # Thống kê theo chế độ thị trường
    regime_stats = {}
    for t in trades:
        regime = t.get('market_regime', 'unknown')
        if regime not in regime_stats:
            regime_stats[regime] = {
                'count': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0
            }
        
        regime_stats[regime]['count'] += 1
        if t['pnl_amount'] > 0:
            regime_stats[regime]['wins'] += 1
        else:
            regime_stats[regime]['losses'] += 1
        regime_stats[regime]['total_pnl'] += t['pnl_amount']
    
    # Kết quả cuối cùng
    final_balance = trades[-1]['balance'] if trades else initial_balance
    profit_amount = final_balance - initial_balance
    profit_percent = ((final_balance - initial_balance) / initial_balance) * 100
    
    return {
        'num_trades': num_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'risk_reward_ratio': risk_reward_ratio,
        'avg_profit': avg_profit,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'expectancy_score': expectancy_score,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'max_drawdown_duration': max_drawdown_duration,
        'exit_reason_stats': exit_reason_stats,
        'regime_stats': regime_stats,
        'initial_balance': initial_balance,
        'final_balance': final_balance,
        'profit_amount': profit_amount,
        'profit_percent': profit_percent
    }

def display_results(
    performance_metrics: Dict,
    trades: List[Dict],
    equity_curve: List[float],
    dates: List[datetime],
    symbol: str,
    interval: str,
    strategy_type: str,
    initial_balance: float
):
    """
    Hiển thị kết quả backtest
    
    Args:
        performance_metrics (Dict): Các chỉ số hiệu suất
        trades (List[Dict]): Danh sách các giao dịch
        equity_curve (List[float]): Đường cong vốn
        dates (List[datetime]): Danh sách các ngày
        symbol (str): Mã cặp giao dịch
        interval (str): Khung thời gian
        strategy_type (str): Loại chiến lược
        initial_balance (float): Số dư ban đầu
    """
    # Hiển thị kết quả
    logger.info(f"\n=== KẾT QUẢ BACKTEST ===")
    logger.info(f"Số giao dịch: {performance_metrics['num_trades']}")
    logger.info(f"Giao dịch thắng/thua: {performance_metrics['winning_trades']}/{performance_metrics['losing_trades']}")
    logger.info(f"Win rate: {performance_metrics['win_rate']:.2f}%")
    logger.info(f"Profit factor: {performance_metrics['profit_factor']:.2f}")
    logger.info(f"Risk-Reward ratio: {performance_metrics['risk_reward_ratio']:.2f}")
    logger.info(f"Lợi nhuận trung bình: ${performance_metrics['avg_profit']:.2f}")
    logger.info(f"Thua lỗ trung bình: ${performance_metrics['avg_loss']:.2f}")
    logger.info(f"Expectancy: ${performance_metrics['expectancy']:.2f}")
    logger.info(f"Sharpe ratio: {performance_metrics['sharpe_ratio']:.2f}")
    logger.info(f"Drawdown tối đa: {performance_metrics['max_drawdown']:.2f}%")
    
    if performance_metrics['max_drawdown_duration'] is not None:
        logger.info(f"Thời gian drawdown tối đa: {performance_metrics['max_drawdown_duration']} ngày")
    
    logger.info(f"Số dư ban đầu: ${performance_metrics['initial_balance']:.2f}")
    logger.info(f"Số dư cuối cùng: ${performance_metrics['final_balance']:.2f}")
    logger.info(f"Lợi nhuận: ${performance_metrics['profit_amount']:.2f} ({performance_metrics['profit_percent']:.2f}%)")
    
    # Hiển thị thống kê theo lý do đóng lệnh
    logger.info(f"\n=== THỐNG KÊ THEO LÝ DO ĐÓNG LỆNH ===")
    for reason, stats in performance_metrics['exit_reason_stats'].items():
        win_rate = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
        logger.info(f"{reason}: {stats['count']} giao dịch, Win rate: {win_rate:.2f}%, P&L: ${stats['total_pnl']:.2f}")
    
    # Hiển thị thống kê theo chế độ thị trường
    logger.info(f"\n=== THỐNG KÊ THEO CHẾ ĐỘ THỊ TRƯỜNG ===")
    for regime, stats in performance_metrics['regime_stats'].items():
        win_rate = (stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0
        logger.info(f"{regime}: {stats['count']} giao dịch, Win rate: {win_rate:.2f}%, P&L: ${stats['total_pnl']:.2f}")
    
    # Vẽ đồ thị
    plt.figure(figsize=(12, 6))
    plt.plot(dates, equity_curve)
    plt.title(f'Đường cong vốn - {strategy_type.upper()} ({symbol} {interval})')
    plt.xlabel('Thời gian')
    plt.ylabel('Vốn ($)')
    plt.grid(True)
    
    # Vẽ các điểm mua/bán
    trade_dates = [pd.to_datetime(t['entry_date']) for t in trades]
    trade_exits = [pd.to_datetime(t['exit_date']) for t in trades]
    
    trade_entry_values = []
    trade_exit_values = []
    
    # Lấy giá trị vốn tương ứng với từng ngày giao dịch
    for t_date in trade_dates:
        # Tìm equity value tại ngày gần nhất trước ngày giao dịch
        closest_date_idx = 0
        for i, d in enumerate(dates):
            if pd.to_datetime(d) <= t_date:
                closest_date_idx = i
        trade_entry_values.append(equity_curve[closest_date_idx])
    
    for t_date in trade_exits:
        # Tìm equity value tại ngày gần nhất trước ngày giao dịch
        closest_date_idx = 0
        for i, d in enumerate(dates):
            if pd.to_datetime(d) <= t_date:
                closest_date_idx = i
        trade_exit_values.append(equity_curve[closest_date_idx])
    
    # Vẽ điểm vào lệnh
    plt.scatter(
        trade_dates, 
        trade_entry_values,
        color='green', 
        marker='^', 
        s=50, 
        label='Entry'
    )
    
    # Vẽ điểm thoát lệnh
    for i, (exit_date, exit_value) in enumerate(zip(trade_exits, trade_exit_values)):
        color = 'blue' if trades[i]['pnl_amount'] > 0 else 'red'
        plt.scatter(
            exit_date, 
            exit_value,
            color=color, 
            marker='v' if trades[i]['side'] == 'BUY' else 'o', 
            s=50
        )
    
    plt.legend()
    
    # Lưu đồ thị
    chart_path = f'backtest_charts/{symbol}_{interval}_{strategy_type}_equity.png'
    plt.savefig(chart_path)
    logger.info(f"Đã lưu đồ thị đường cong vốn vào '{chart_path}'")
    
    # Vẽ thêm biểu đồ thống kê
    plt.figure(figsize=(15, 10))
    
    # Subplot 1: Thống kê thắng/thua
    plt.subplot(2, 2, 1)
    plt.bar(['Thắng', 'Thua'], [performance_metrics['winning_trades'], performance_metrics['losing_trades']], color=['green', 'red'])
    plt.title('Số lượng giao dịch thắng/thua')
    plt.grid(True, axis='y')
    
    # Subplot 2: Win rate theo lý do đóng lệnh
    plt.subplot(2, 2, 2)
    reasons = list(performance_metrics['exit_reason_stats'].keys())
    win_rates = [(stats['wins'] / stats['count']) * 100 if stats['count'] > 0 else 0 
                for stats in performance_metrics['exit_reason_stats'].values()]
    
    plt.bar(reasons, win_rates, color='blue')
    plt.title('Win rate theo lý do đóng lệnh')
    plt.ylabel('Win rate (%)')
    plt.grid(True, axis='y')
    plt.xticks(rotation=45)
    
    # Subplot 3: P&L theo lý do đóng lệnh
    plt.subplot(2, 2, 3)
    pnls = [stats['total_pnl'] for stats in performance_metrics['exit_reason_stats'].values()]
    colors = ['green' if p > 0 else 'red' for p in pnls]
    
    plt.bar(reasons, pnls, color=colors)
    plt.title('P&L theo lý do đóng lệnh')
    plt.ylabel('P&L ($)')
    plt.grid(True, axis='y')
    plt.xticks(rotation=45)
    
    # Subplot 4: Thống kê theo chế độ thị trường
    plt.subplot(2, 2, 4)
    regimes = list(performance_metrics['regime_stats'].keys())
    regime_counts = [stats['count'] for stats in performance_metrics['regime_stats'].values()]
    regime_pnls = [stats['total_pnl'] for stats in performance_metrics['regime_stats'].values()]
    
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    
    bars = ax1.bar(regimes, regime_counts, color='blue', alpha=0.6, label='Số lượng')
    ax1.set_ylabel('Số lượng giao dịch')
    
    ax2.plot(regimes, regime_pnls, 'ro-', label='P&L')
    ax2.set_ylabel('P&L ($)')
    
    plt.title('Phân tích theo chế độ thị trường')
    plt.grid(True, axis='y')
    plt.xticks(rotation=45)
    
    # Combine legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')
    
    plt.tight_layout()
    
    # Lưu biểu đồ thống kê
    stats_chart_path = f'backtest_charts/{symbol}_{interval}_{strategy_type}_stats.png'
    plt.savefig(stats_chart_path)
    logger.info(f"Đã lưu biểu đồ thống kê vào '{stats_chart_path}'")
    
    # Lưu giao dịch
    trades_df = pd.DataFrame(trades)
    trades_file = f'backtest_results/{symbol}_{interval}_{strategy_type}_trades.csv'
    trades_df.to_csv(trades_file, index=False)
    logger.info(f"Đã lưu lịch sử giao dịch vào '{trades_file}'")
    
    # Lưu kết quả
    results_file = f'backtest_results/{symbol}_{interval}_{strategy_type}_results.json'
    
    with open(results_file, 'w') as f:
        # Chuyển danh sách giao dịch thành định dạng có thể serialize
        serializable_metrics = performance_metrics.copy()
        # Loại bỏ datetime objects
        if 'max_drawdown_start' in serializable_metrics:
            serializable_metrics['max_drawdown_start'] = str(serializable_metrics['max_drawdown_start'])
        if 'max_drawdown_end' in serializable_metrics:
            serializable_metrics['max_drawdown_end'] = str(serializable_metrics['max_drawdown_end'])
        
        json.dump({
            'symbol': symbol,
            'interval': interval,
            'strategy': strategy_type,
            'performance_metrics': serializable_metrics,
            'equity_curve': {
                'dates': [str(d) for d in dates],
                'values': equity_curve
            }
        }, f, indent=2)
    
    logger.info(f"Đã lưu kết quả backtest vào '{results_file}'")

def main():
    """Hàm chính"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Công cụ backtest nâng cao')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Cặp giao dịch (mặc định: BTCUSDT)')
    parser.add_argument('--interval', type=str, default='1h', help='Khung thời gian chính (mặc định: 1h)')
    parser.add_argument('--secondary_intervals', type=str, default='4h,1d', 
                        help='Khung thời gian phụ, phân cách bằng dấu phẩy (mặc định: 4h,1d)')
    parser.add_argument('--strategy', type=str, default='auto', 
                       choices=['auto', 'ml', 'combined', 'rsi', 'macd', 'ema', 'bbands', 'advanced_ml', 'regime_ml'],
                       help='Loại chiến lược giao dịch (mặc định: auto)')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu (mặc định: $10,000)')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy (mặc định: 5x)')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro (mặc định: 1%)')
    parser.add_argument('--position_sizing', type=str, default='dynamic', 
                       choices=['fixed', 'dynamic', 'kelly', 'anti_martingale'],
                       help='Phương pháp quản lý vốn (mặc định: dynamic)')
    parser.add_argument('--risk_method', type=str, default='fixed', 
                       choices=['fixed', 'adaptive', 'volatility_based'],
                       help='Phương pháp quản lý rủi ro (mặc định: fixed)')
    parser.add_argument('--stop_loss', type=float, default=5.0, help='Phần trăm cắt lỗ (mặc định: 5%)')
    parser.add_argument('--take_profit', type=float, default=15.0, help='Phần trăm chốt lời (mặc định: 15%)')
    parser.add_argument('--trailing_stop', type=str, default='true', 
                       choices=['true', 'false'],
                       help='Sử dụng trailing stop (mặc định: true)')
    parser.add_argument('--data_dir', type=str, default='test_data', help='Thư mục chứa dữ liệu (mặc định: test_data)')
    parser.add_argument('--start_date', type=str, default=None, help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default=None, help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--output_prefix', type=str, default='', help='Tiền tố cho file đầu ra (ví dụ: "3month_")')
    
    args = parser.parse_args()
    
    secondary_intervals = args.secondary_intervals.split(',') if args.secondary_intervals else []
    trailing_stop = args.trailing_stop.lower() == 'true'
    
    run_enhanced_backtest(
        symbol=args.symbol,
        primary_interval=args.interval,
        secondary_intervals=secondary_intervals,
        strategy_type=args.strategy,
        initial_balance=args.balance,
        leverage=args.leverage,
        risk_percentage=args.risk,
        position_sizing_method=args.position_sizing,
        risk_method=args.risk_method,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        trailing_stop=trailing_stop,
        data_dir=args.data_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        output_prefix=args.output_prefix
    )

if __name__ == "__main__":
    main()