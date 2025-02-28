"""
Script huấn luyện mô hình học máy và chạy backtest cho tất cả các chiến lược

Script này sẽ:
1. Huấn luyện các mô hình học máy trên các chế độ thị trường khác nhau
2. Kiểm tra hiệu suất của các mô hình với dữ liệu mới
3. Chạy backtest các chiến lược giao dịch khác nhau
4. So sánh hiệu suất của các chiến lược
"""

import os
import sys
import logging
import time
import json
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any

from app.binance_api import BinanceAPI
from app.data_processor import DataProcessor
from app.market_regime_detector import MarketRegimeDetector
from app.advanced_ml_optimizer import AdvancedMLOptimizer
from app.advanced_ml_strategy import AdvancedMLStrategy

from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from composite_indicator import CompositeIndicator
from liquidity_analyzer import LiquidityAnalyzer
from advanced_trading_system import AdvancedTradingSystem

# Thiết lập logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('run_training')

def create_output_dir():
    """Tạo thư mục đầu ra cho kết quả"""
    os.makedirs('results', exist_ok=True)
    os.makedirs('results/images', exist_ok=True)
    os.makedirs('results/data', exist_ok=True)
    os.makedirs('models', exist_ok=True)

def train_ml_models(symbol='BTCUSDT', timeframes=['1h', '4h', '1d']):
    """
    Huấn luyện các mô hình học máy trên dữ liệu lịch sử
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframes (list): Danh sách các khung thời gian
    
    Returns:
        dict: Thông tin các mô hình đã huấn luyện
    """
    logger.info(f"=== Huấn luyện mô hình học máy cho {symbol} ===")
    
    # Khởi tạo các thành phần
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    market_regime_detector = MarketRegimeDetector()
    ml_optimizer = AdvancedMLOptimizer(
        base_models=["random_forest", "gradient_boosting", "neural_network"],
        use_model_per_regime=True,
        feature_selection=True,
        use_ensemble=True
    )
    
    results = {}
    
    # Huấn luyện mô hình trên từng khung thời gian
    for timeframe in timeframes:
        logger.info(f"Đang huấn luyện mô hình cho khung thời gian {timeframe}...")
        
        # Lấy dữ liệu và xử lý
        df = data_processor.get_historical_data(symbol, timeframe, lookback_days=90)
        if df is None or len(df) < 100:
            logger.error(f"Không đủ dữ liệu cho khung thời gian {timeframe}")
            continue
        
        # Phát hiện chế độ thị trường
        regimes = []
        for i in range(100, len(df)):
            segment = df.iloc[i-100:i]
            regime = market_regime_detector.detect_regime(segment)
            regimes.append(regime)
        
        df_train = df.iloc[100:].copy()
        df_train['regime'] = regimes
        
        # Chuẩn bị dữ liệu cho huấn luyện
        X = ml_optimizer.prepare_features_for_prediction(df_train)
        y = ml_optimizer.prepare_target_for_training(df_train, lookahead=10, threshold=0.5)
        
        if X is None or y is None:
            logger.error("X hoặc y là None, không thể tiếp tục huấn luyện")
            continue
            
        if len(X) != len(y):
            logger.warning(f"Kích thước X ({len(X)}) và y ({len(y)}) không khớp, đang điều chỉnh...")
            # Điều chỉnh kích thước để khớp nhau
            min_len = min(len(X), len(y))
            X = X.iloc[:min_len]
            y = y[:min_len]
            logger.info(f"Đã điều chỉnh kích thước: X = {len(X)}, y = {len(y)}")
            
        if len(X) < 100:
            logger.error(f"Không đủ dữ liệu sau khi điều chỉnh kích thước (chỉ có {len(X)} mẫu)")
            continue
        
        # Chia dữ liệu thành các chế độ thị trường khác nhau
        regime_data = {}
        for regime in market_regime_detector.REGIME_THRESHOLDS.keys():
            mask = df_train['regime'] == regime
            if sum(mask) > 30:  # Cần ít nhất 30 mẫu để huấn luyện
                regime_data[regime] = {
                    'X': X[mask],
                    'y': y[mask]
                }
                logger.info(f"Chế độ {regime}: {sum(mask)} mẫu")
        
        # Huấn luyện mô hình cho từng chế độ thị trường
        performance = {}
        for regime, data in regime_data.items():
            if len(data['X']) < 30:
                continue
                
            logger.info(f"Huấn luyện mô hình cho chế độ {regime}...")
            metrics = ml_optimizer.train_models(data['X'], data['y'], regime=regime)
            performance[regime] = metrics
            logger.info(f"Hiệu suất mô hình {regime}: Accuracy={metrics.get('accuracy', 0):.2f}, F1={metrics.get('f1', 0):.2f}")
        
        # Lưu mô hình
        model_path = f"models/{symbol}_{timeframe}_ml_models.joblib"
        ml_optimizer.save_models(model_path)
        logger.info(f"Đã lưu mô hình vào {model_path}")
        
        # Lưu kết quả
        results[timeframe] = {
            'performance': performance,
            'model_path': model_path,
            'data_length': len(df),
            'regimes': {regime: sum(df_train['regime'] == regime) for regime in market_regime_detector.REGIME_THRESHOLDS.keys()}
        }
    
    # Lưu kết quả tổng hợp ra file
    with open('results/data/ml_training_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def run_backtest_with_ml(symbol='BTCUSDT', timeframe='1h', days=30):
    """
    Chạy backtest sử dụng chiến lược học máy
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        days (int): Số ngày dữ liệu lịch sử
    
    Returns:
        dict: Kết quả backtest
    """
    logger.info(f"=== Chạy backtest với chiến lược học máy cho {symbol} trên khung {timeframe} ===")
    
    # Khởi tạo các thành phần
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    ml_optimizer = AdvancedMLOptimizer()
    market_regime_detector = MarketRegimeDetector()
    
    # Tải mô hình đã huấn luyện
    model_path = f"models/{symbol}_{timeframe}_ml_models.joblib"
    if not os.path.exists(model_path):
        logger.error(f"Không tìm thấy mô hình {model_path}")
        return None
    
    ml_optimizer.load_models(model_path)
    logger.info(f"Đã tải mô hình từ {model_path}")
    
    # Khởi tạo chiến lược ML
    ml_strategy = AdvancedMLStrategy(
        ml_optimizer=ml_optimizer,
        market_regime_detector=market_regime_detector,
        model_path=model_path,
        probability_threshold=0.65,
        confidence_threshold=0.6
    )
    
    # Khởi tạo hệ thống giao dịch
    trading_system = AdvancedTradingSystem(
        binance_api=binance_api,
        data_processor=data_processor,
        initial_balance=10000.0,
        risk_percentage=1.0
    )
    
    # Lấy dữ liệu backtest
    df = data_processor.get_historical_data(symbol, timeframe, lookback_days=days)
    if df is None or len(df) < 10:
        logger.error(f"Không đủ dữ liệu cho backtest")
        return None
    
    # Chuẩn bị dữ liệu cho backtest
    logger.info(f"Chạy backtest với {len(df)} mẫu dữ liệu")
    
    # Phát hiện chế độ thị trường
    regimes = []
    for i in range(min(100, len(df) // 2), len(df)):
        segment = df.iloc[i-min(100, len(df) // 2):i]
        regime = market_regime_detector.detect_regime(segment)
        regimes.append(regime)
    
    while len(regimes) < len(df):
        regimes.insert(0, "neutral")
    
    df['regime'] = regimes
    
    # Tạo các tính năng cho dự đoán
    X = ml_optimizer.prepare_features_for_prediction(df)
    
    # Dự đoán tín hiệu
    signals = []
    for i in range(len(X)):
        regime = df['regime'].iloc[i]
        features = X[i:i+1]
        signal, proba = ml_optimizer.predict(features, regime=regime)
        signals.append(signal)
    
    df['ml_signal'] = signals
    
    # Chạy backtest
    balance = 10000.0
    position = None
    trades = []
    equity_curve = [balance]
    
    for i in range(1, len(df)):
        current_price = df['close'].iloc[i]
        current_signal = df['ml_signal'].iloc[i]
        
        # Nếu không có vị thế và có tín hiệu
        if position is None and current_signal != 0:
            # Tạo vị thế mới
            side = "BUY" if current_signal == 1 else "SELL"
            position_size = balance * 0.02  # 2% rủi ro
            quantity = position_size / current_price
            
            position = {
                'side': side,
                'entry_price': current_price,
                'quantity': quantity,
                'entry_time': df.index[i],
                'regime': df['regime'].iloc[i]
            }
            
            logger.info(f"Mở vị thế {side} tại {current_price:.2f} ({df.index[i]})")
        
        # Nếu có vị thế, kiểm tra các điều kiện đóng vị thế
        elif position is not None:
            # Điều kiện lấy lãi: 1.5% lợi nhuận
            take_profit = position['entry_price'] * 1.015 if position['side'] == "BUY" else position['entry_price'] * 0.985
            
            # Điều kiện cắt lỗ: 1% thua lỗ
            stop_loss = position['entry_price'] * 0.99 if position['side'] == "BUY" else position['entry_price'] * 1.01
            
            # Điều kiện đảo chiều tín hiệu
            signal_reversed = (position['side'] == "BUY" and current_signal == -1) or (position['side'] == "SELL" and current_signal == 1)
            
            # Kiểm tra các điều kiện đóng vị thế
            close_position = False
            exit_reason = None
            
            if (position['side'] == "BUY" and current_price >= take_profit) or (position['side'] == "SELL" and current_price <= take_profit):
                close_position = True
                exit_reason = "Take Profit"
            elif (position['side'] == "BUY" and current_price <= stop_loss) or (position['side'] == "SELL" and current_price >= stop_loss):
                close_position = True
                exit_reason = "Stop Loss"
            elif signal_reversed:
                close_position = True
                exit_reason = "Signal Reversed"
            
            # Đóng vị thế
            if close_position:
                # Tính lãi/lỗ
                if position['side'] == "BUY":
                    pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
                else:
                    pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
                
                balance = balance * (1 + pnl / 100)
                
                # Lưu thông tin giao dịch
                trade = position.copy()
                trade['exit_price'] = current_price
                trade['exit_time'] = df.index[i]
                trade['exit_reason'] = exit_reason
                trade['pnl'] = pnl
                trades.append(trade)
                
                logger.info(f"Đóng vị thế tại {current_price:.2f} ({df.index[i]}), Lý do: {exit_reason}, PnL: {pnl:.2f}%")
                
                # Reset vị thế
                position = None
        
        # Cập nhật equity curve
        equity_curve.append(balance if position is None else balance * (1 + calc_unrealized_pnl(position, current_price) / 100))
    
    # Đóng vị thế nếu còn mở ở cuối backtest
    if position is not None:
        current_price = df['close'].iloc[-1]
        
        # Tính lãi/lỗ
        if position['side'] == "BUY":
            pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
        else:
            pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
        
        balance = balance * (1 + pnl / 100)
        
        # Lưu thông tin giao dịch
        trade = position.copy()
        trade['exit_price'] = current_price
        trade['exit_time'] = df.index[-1]
        trade['exit_reason'] = "End of Backtest"
        trade['pnl'] = pnl
        trades.append(trade)
        
        logger.info(f"Đóng vị thế cuối cùng tại {current_price:.2f}, PnL: {pnl:.2f}%")
    
    # Tính toán các chỉ số hiệu suất
    performance = calculate_performance(trades, equity_curve, initial_balance=10000.0)
    
    # In kết quả
    logger.info(f"Số dư cuối cùng: ${balance:.2f}")
    logger.info(f"Tổng lợi nhuận: {performance['total_return']:.2f}%")
    logger.info(f"Tỷ lệ thắng: {performance['win_rate']:.2f}%")
    logger.info(f"Hệ số lợi nhuận: {performance['profit_factor']:.2f}")
    logger.info(f"Drawdown tối đa: {performance['max_drawdown']:.2f}%")
    
    # Vẽ biểu đồ equity curve
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(equity_curve)), equity_curve)
    plt.title(f"{symbol} ML Strategy Backtest - {timeframe} ({days} days)")
    plt.xlabel("Bars")
    plt.ylabel("Account Balance ($)")
    plt.grid(True)
    plt.savefig(f"results/images/{symbol}_{timeframe}_ml_backtest.png")
    
    # Lưu kết quả
    results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'days': days,
        'trades': [trade for trade in trades],
        'performance': performance,
        'equity_curve': equity_curve
    }
    
    with open(f"results/data/{symbol}_{timeframe}_ml_backtest_results.json", 'w') as f:
        # Chuyển đổi datetime thành string
        results_clean = results.copy()
        for trade in results_clean['trades']:
            trade['entry_time'] = trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
            trade['exit_time'] = trade['exit_time'].strftime('%Y-%m-%d %H:%M:%S')
        json.dump(results_clean, f, indent=2)
    
    return results

def calc_unrealized_pnl(position, current_price):
    """Tính lãi/lỗ chưa thực hiện của vị thế"""
    # Xử lý trường hợp entry_price là 0 hoặc NaN
    entry_price = position['entry_price']
    if entry_price is None or entry_price == 0:
        return 0.0
        
    try:
        if position['side'] == "BUY":
            pnl = (current_price - entry_price) / entry_price * 100
        else:
            pnl = (entry_price - current_price) / entry_price * 100
            
        # Kiểm tra giá trị NaN hoặc vô cùng
        if pnl is None or np.isnan(pnl) or np.isinf(pnl):
            return 0.0
            
        return pnl
    except (ZeroDivisionError, TypeError):
        logger.warning(f"Lỗi tính PnL: entry_price={entry_price}, current_price={current_price}")
        return 0.0

def calculate_performance(trades, equity_curve, initial_balance=10000.0):
    """Tính toán các chỉ số hiệu suất"""
    if not trades:
        return {
            'total_return': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'total_trades': 0
        }
    
    try:
        # Đảm bảo equity_curve không chứa NaN hoặc inf
        equity_curve = [e if e is not None and not np.isnan(e) and not np.isinf(e) else initial_balance for e in equity_curve]
        
        # Tính tổng lợi nhuận
        if len(equity_curve) > 0 and equity_curve[-1] != 0:
            total_return = (equity_curve[-1] - initial_balance) / initial_balance * 100
        else:
            total_return = 0
        
        # Lọc các PnL không hợp lệ trong trades
        for trade in trades:
            if trade['pnl'] is None or np.isnan(trade['pnl']) or np.isinf(trade['pnl']):
                trade['pnl'] = 0.0
        
        # Tính tỷ lệ thắng
        win_trades = [t for t in trades if t.get('pnl', 0) > 0]
        win_rate = len(win_trades) / len(trades) * 100 if trades else 0
        
        # Tính profit factor
        total_win = sum([t.get('pnl', 0) for t in win_trades]) if win_trades else 0
        loss_trades = [t for t in trades if t.get('pnl', 0) <= 0]
        total_loss = abs(sum([t.get('pnl', 0) for t in loss_trades])) if loss_trades else 1.0
        profit_factor = abs(total_win / total_loss) if total_loss != 0 else 1.0
        
        # Tính drawdown tối đa
        max_equity = equity_curve[0]
        max_drawdown = 0
        
        for equity in equity_curve:
            max_equity = max(max_equity, equity) if not np.isnan(equity) else max_equity
            if max_equity > 0 and not np.isnan(equity):
                drawdown = (max_equity - equity) / max_equity * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        # Tính trung bình lãi/lỗ
        avg_win = sum([t.get('pnl', 0) for t in win_trades]) / len(win_trades) if win_trades else 0
        avg_loss = sum([t.get('pnl', 0) for t in loss_trades]) / len(loss_trades) if loss_trades else 0
        
        return {
            'total_return': float(total_return) if not np.isnan(total_return) else 0,
            'win_rate': float(win_rate) if not np.isnan(win_rate) else 0,
            'profit_factor': float(profit_factor) if not np.isnan(profit_factor) and not np.isinf(profit_factor) else 1.0,
            'max_drawdown': float(max_drawdown) if not np.isnan(max_drawdown) else 0,
            'avg_win': float(avg_win) if not np.isnan(avg_win) else 0,
            'avg_loss': float(avg_loss) if not np.isnan(avg_loss) else 0,
            'total_trades': len(trades)
        }
    except Exception as e:
        logger.error(f"Lỗi trong quá trình tính toán hiệu suất: {e}")
        return {
            'total_return': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'total_trades': len(trades) if trades else 0
        }

def run_backtest_with_advanced_system(symbol='BTCUSDT', timeframe='1h', days=30):
    """
    Chạy backtest sử dụng hệ thống giao dịch nâng cao
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian
        days (int): Số ngày dữ liệu lịch sử
    
    Returns:
        dict: Kết quả backtest
    """
    logger.info(f"=== Chạy backtest với hệ thống giao dịch nâng cao cho {symbol} trên khung {timeframe} ===")
    
    # Khởi tạo các thành phần
    binance_api = BinanceAPI(simulation_mode=True)
    data_processor = DataProcessor(binance_api, simulation_mode=True)
    
    # Khởi tạo hệ thống giao dịch nâng cao
    trading_system = AdvancedTradingSystem(
        binance_api=binance_api,
        data_processor=data_processor,
        initial_balance=10000.0,
        risk_percentage=1.0,
        timeframes=[timeframe, '4h', '1d'] if timeframe not in ['4h', '1d'] else [timeframe, '1d']
    )
    
    # Lấy dữ liệu backtest
    df = data_processor.get_historical_data(symbol, timeframe, lookback_days=days)
    if df is None or len(df) < 10:
        logger.error(f"Không đủ dữ liệu cho backtest")
        return None
    
    # Chạy backtest
    logger.info(f"Chạy backtest với {len(df)} mẫu dữ liệu")
    
    balance = 10000.0
    position = None
    trades = []
    equity_curve = [balance]
    
    for i in range(30, len(df)):  # Bắt đầu từ bar thứ 30 để có đủ dữ liệu lịch sử
        # Lấy phân tích thị trường tại thời điểm hiện tại
        current_df = df.iloc[:i+1].copy()
        analysis = trading_system.analyze_market(symbol, timeframe)
        
        current_price = df['close'].iloc[i]
        current_signal = 0
        
        if analysis and 'signal' in analysis:
            if analysis['signal'] == 'BUY':
                current_signal = 1
            elif analysis['signal'] == 'SELL':
                current_signal = -1
        
        # Nếu không có vị thế và có tín hiệu
        if position is None and current_signal != 0:
            # Tạo vị thế mới
            side = "BUY" if current_signal == 1 else "SELL"
            
            # Lấy các tham số quản lý rủi ro từ phân tích
            risk_params = analysis.get('risk_management', {})
            position_size = risk_params.get('position_size_pct', 1.0)
            
            # Tính số lượng dựa trên kích thước vị thế
            position_value = balance * (position_size / 100)
            quantity = position_value / current_price
            
            position = {
                'side': side,
                'entry_price': current_price,
                'quantity': quantity,
                'entry_time': df.index[i],
                'take_profit_pct': risk_params.get('take_profit_pct', 2.0),
                'stop_loss_pct': risk_params.get('stop_loss_pct', 1.0),
                'trailing_stop': risk_params.get('trailing_stop', False),
                'highest_price': current_price if side == "BUY" else None,
                'lowest_price': current_price if side == "SELL" else None
            }
            
            # Tính giá chốt lời và cắt lỗ
            if side == "BUY":
                position['take_profit_price'] = current_price * (1 + position['take_profit_pct'] / 100)
                position['stop_loss_price'] = current_price * (1 - position['stop_loss_pct'] / 100)
            else:
                position['take_profit_price'] = current_price * (1 - position['take_profit_pct'] / 100)
                position['stop_loss_price'] = current_price * (1 + position['stop_loss_pct'] / 100)
            
            logger.info(f"Mở vị thế {side} tại {current_price:.2f} ({df.index[i]})")
        
        # Nếu có vị thế, cập nhật và kiểm tra các điều kiện đóng vị thế
        elif position is not None:
            # Cập nhật giá cao nhất/thấp nhất
            if position['side'] == "BUY":
                position['highest_price'] = max(position['highest_price'], current_price)
            else:
                position['lowest_price'] = min(position['lowest_price'], current_price)
            
            # Kiểm tra trailing stop
            trailing_stop_hit = False
            if position['trailing_stop'] and 'trailing_stop_price' in position:
                if (position['side'] == "BUY" and current_price < position['trailing_stop_price']) or \
                   (position['side'] == "SELL" and current_price > position['trailing_stop_price']):
                    trailing_stop_hit = True
            
            # Cập nhật trailing stop nếu cần
            if position['trailing_stop'] and position['side'] == "BUY" and position['highest_price'] > position['entry_price'] * 1.01:
                # Kích hoạt trailing stop khi giá tăng 1%
                trailing_callback = position['stop_loss_pct'] * 0.5
                position['trailing_stop_price'] = position['highest_price'] * (1 - trailing_callback / 100)
            
            elif position['trailing_stop'] and position['side'] == "SELL" and position['lowest_price'] < position['entry_price'] * 0.99:
                # Kích hoạt trailing stop khi giá giảm 1%
                trailing_callback = position['stop_loss_pct'] * 0.5
                position['trailing_stop_price'] = position['lowest_price'] * (1 + trailing_callback / 100)
            
            # Kiểm tra các điều kiện đóng vị thế
            close_position = False
            exit_reason = None
            
            if trailing_stop_hit:
                close_position = True
                exit_reason = "Trailing Stop"
            elif (position['side'] == "BUY" and current_price >= position['take_profit_price']) or \
                 (position['side'] == "SELL" and current_price <= position['take_profit_price']):
                close_position = True
                exit_reason = "Take Profit"
            elif (position['side'] == "BUY" and current_price <= position['stop_loss_price']) or \
                 (position['side'] == "SELL" and current_price >= position['stop_loss_price']):
                close_position = True
                exit_reason = "Stop Loss"
            elif (position['side'] == "BUY" and current_signal == -1) or \
                 (position['side'] == "SELL" and current_signal == 1):
                close_position = True
                exit_reason = "Signal Reversed"
            
            # Đóng vị thế
            if close_position:
                # Tính lãi/lỗ
                if position['side'] == "BUY":
                    pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
                else:
                    pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
                
                balance = balance * (1 + pnl / 100)
                
                # Lưu thông tin giao dịch
                trade = position.copy()
                trade['exit_price'] = current_price
                trade['exit_time'] = df.index[i]
                trade['exit_reason'] = exit_reason
                trade['pnl'] = pnl
                trades.append(trade)
                
                logger.info(f"Đóng vị thế tại {current_price:.2f} ({df.index[i]}), Lý do: {exit_reason}, PnL: {pnl:.2f}%")
                
                # Reset vị thế
                position = None
        
        # Cập nhật equity curve
        equity_curve.append(balance if position is None else balance * (1 + calc_unrealized_pnl(position, current_price) / 100))
    
    # Đóng vị thế nếu còn mở ở cuối backtest
    if position is not None:
        current_price = df['close'].iloc[-1]
        
        # Tính lãi/lỗ
        if position['side'] == "BUY":
            pnl = (current_price - position['entry_price']) / position['entry_price'] * 100
        else:
            pnl = (position['entry_price'] - current_price) / position['entry_price'] * 100
        
        balance = balance * (1 + pnl / 100)
        
        # Lưu thông tin giao dịch
        trade = position.copy()
        trade['exit_price'] = current_price
        trade['exit_time'] = df.index[-1]
        trade['exit_reason'] = "End of Backtest"
        trade['pnl'] = pnl
        trades.append(trade)
        
        logger.info(f"Đóng vị thế cuối cùng tại {current_price:.2f}, PnL: {pnl:.2f}%")
    
    # Tính toán các chỉ số hiệu suất
    performance = calculate_performance(trades, equity_curve, initial_balance=10000.0)
    
    # In kết quả
    logger.info(f"Số dư cuối cùng: ${balance:.2f}")
    logger.info(f"Tổng lợi nhuận: {performance['total_return']:.2f}%")
    logger.info(f"Tỷ lệ thắng: {performance['win_rate']:.2f}%")
    logger.info(f"Hệ số lợi nhuận: {performance['profit_factor']:.2f}")
    logger.info(f"Drawdown tối đa: {performance['max_drawdown']:.2f}%")
    
    # Vẽ biểu đồ equity curve
    plt.figure(figsize=(10, 6))
    plt.plot(range(len(equity_curve)), equity_curve)
    plt.title(f"{symbol} Advanced Trading System - {timeframe} ({days} days)")
    plt.xlabel("Bars")
    plt.ylabel("Account Balance ($)")
    plt.grid(True)
    plt.savefig(f"results/images/{symbol}_{timeframe}_advanced_system_backtest.png")
    
    # Lưu kết quả
    results = {
        'symbol': symbol,
        'timeframe': timeframe,
        'days': days,
        'trades': [trade for trade in trades],
        'performance': performance,
        'equity_curve': equity_curve
    }
    
    with open(f"results/data/{symbol}_{timeframe}_advanced_system_results.json", 'w') as f:
        # Chuyển đổi datetime thành string
        results_clean = results.copy()
        for trade in results_clean['trades']:
            # Xử lý entry_time
            if hasattr(trade['entry_time'], 'strftime'):
                trade['entry_time'] = trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                trade['entry_time'] = str(trade['entry_time'])
                
            # Xử lý exit_time
            if hasattr(trade['exit_time'], 'strftime'):
                trade['exit_time'] = trade['exit_time'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                trade['exit_time'] = str(trade['exit_time'])
        json.dump(results_clean, f, indent=2)
    
    return results

def compare_strategies(results: Dict):
    """So sánh hiệu suất của các chiến lược"""
    logger.info("=== So sánh hiệu suất các chiến lược ===")
    
    strategies = list(results.keys())
    
    # Tạo bảng so sánh
    comparison = {
        'total_return': [],
        'win_rate': [],
        'profit_factor': [],
        'max_drawdown': [],
        'total_trades': []
    }
    
    for strategy, result in results.items():
        performance = result['performance']
        comparison['total_return'].append(performance['total_return'])
        comparison['win_rate'].append(performance['win_rate'])
        comparison['profit_factor'].append(performance['profit_factor'])
        comparison['max_drawdown'].append(performance['max_drawdown'])
        comparison['total_trades'].append(performance['total_trades'])
    
    # In bảng so sánh
    logger.info("Tổng lợi nhuận (%):")
    for i, strategy in enumerate(strategies):
        logger.info(f"  {strategy}: {comparison['total_return'][i]:.2f}%")
    
    logger.info("Tỷ lệ thắng (%):")
    for i, strategy in enumerate(strategies):
        logger.info(f"  {strategy}: {comparison['win_rate'][i]:.2f}%")
    
    logger.info("Hệ số lợi nhuận:")
    for i, strategy in enumerate(strategies):
        logger.info(f"  {strategy}: {comparison['profit_factor'][i]:.2f}")
    
    logger.info("Drawdown tối đa (%):")
    for i, strategy in enumerate(strategies):
        logger.info(f"  {strategy}: {comparison['max_drawdown'][i]:.2f}%")
    
    logger.info("Tổng số giao dịch:")
    for i, strategy in enumerate(strategies):
        logger.info(f"  {strategy}: {comparison['total_trades'][i]}")
    
    # Vẽ biểu đồ so sánh
    plt.figure(figsize=(10, 6))
    x = range(len(strategies))
    plt.bar(x, comparison['total_return'])
    plt.xticks(x, strategies)
    plt.title("So sánh tổng lợi nhuận (%)")
    plt.ylabel("Tổng lợi nhuận (%)")
    plt.grid(True)
    plt.savefig("results/images/strategy_return_comparison.png")
    
    # Vẽ biểu đồ so sánh win rate
    plt.figure(figsize=(10, 6))
    plt.bar(x, comparison['win_rate'])
    plt.xticks(x, strategies)
    plt.title("So sánh tỷ lệ thắng (%)")
    plt.ylabel("Tỷ lệ thắng (%)")
    plt.grid(True)
    plt.savefig("results/images/strategy_winrate_comparison.png")
    
    # Vẽ biểu đồ equity curve cho tất cả các chiến lược
    plt.figure(figsize=(12, 6))
    for strategy, result in results.items():
        plt.plot(range(len(result['equity_curve'])), result['equity_curve'], label=strategy)
    plt.title("So sánh equity curve")
    plt.xlabel("Bars")
    plt.ylabel("Account Balance ($)")
    plt.legend()
    plt.grid(True)
    plt.savefig("results/images/equity_curve_comparison.png")
    
    # Lưu kết quả so sánh
    comparison_results = {
        'strategies': strategies,
        'comparison': comparison
    }
    
    with open("results/data/strategy_comparison.json", 'w') as f:
        json.dump(comparison_results, f, indent=2)
    
    return comparison_results

def main():
    """Hàm chính"""
    # Tạo thư mục đầu ra
    create_output_dir()
    
    # Danh sách các cặp giao dịch và khung thời gian cần test
    symbols = ['BTCUSDT']
    timeframes = ['1h', '4h']
    
    # Huấn luyện mô hình học máy
    training_results = train_ml_models(symbol=symbols[0], timeframes=timeframes)
    
    # Chạy backtest cho các chiến lược
    backtest_results = {}
    
    for timeframe in timeframes:
        # Chạy backtest với ML
        ml_results = run_backtest_with_ml(symbol=symbols[0], timeframe=timeframe, days=30)
        if ml_results:
            backtest_results[f"ML_{timeframe}"] = ml_results
        
        # Chạy backtest với hệ thống giao dịch nâng cao
        advanced_results = run_backtest_with_advanced_system(symbol=symbols[0], timeframe=timeframe, days=30)
        if advanced_results:
            backtest_results[f"Advanced_{timeframe}"] = advanced_results
    
    # So sánh các chiến lược
    if len(backtest_results) >= 2:
        comparison = compare_strategies(backtest_results)
    
    logger.info("Hoàn thành tất cả các tests!")

if __name__ == "__main__":
    main()