#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiểm thử trên dữ liệu thực tế 6 tháng

Script này tải dữ liệu thực tế 6 tháng từ Binance và thực hiện backtest sử dụng
các chiến lược và hệ thống ML được cải tiến. Kết quả sẽ được lưu lại và phân tích chi tiết.
"""

import os
import sys
import argparse
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('six_month_backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import các module của hệ thống
try:
    from binance_api import BinanceAPI
    from feature_engineering import process_and_enhance_dataset
    from risk_manager import RiskManager
    from market_regime_detector import MarketRegimeDetector
    from ml_optimizer import MLOptimizer
    
    # Thử import các module strategy khác nhau để kiểm tra
    from improved_rsi_strategy import ImprovedRsiStrategy
    from optimized_strategy import OptimizedStrategy
    from mtf_optimized_strategy import MTFOptimizedStrategy
    
    logger.info("Đã import thành công các module cần thiết")
except ImportError as e:
    logger.error(f"Lỗi khi import module: {e}")
    raise

def download_historical_data(symbol: str, interval: str, months: int = 6) -> pd.DataFrame:
    """
    Tải dữ liệu lịch sử từ Binance
    
    Args:
        symbol (str): Cặp giao dịch (ví dụ: BTCUSDT)
        interval (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        months (int): Số tháng dữ liệu cần tải
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu lịch sử OHLCV
    """
    # Lấy API key và secret từ biến môi trường
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        # Nếu không có API key/secret, thử đọc từ file .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get('BINANCE_API_KEY')
            api_secret = os.environ.get('BINANCE_API_SECRET')
        except ImportError:
            logger.warning("python-dotenv không được cài đặt, không thể đọc file .env")
            
    # Tính toán thời gian bắt đầu và kết thúc
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30*months)
    
    logger.info(f"Tải dữ liệu {symbol} {interval} từ {start_time.strftime('%Y-%m-%d')} đến {end_time.strftime('%Y-%m-%d')}")
    
    if api_key and api_secret:
        # Sử dụng API Binance để tải dữ liệu
        try:
            api = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=False)
            
            # Tải dữ liệu sử dụng hàm get_historical_klines
            klines = api.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            
            # Chuyển đổi sang DataFrame
            df = api.convert_klines_to_dataframe(klines)
            
            # Lưu lại để tái sử dụng
            data_dir = 'real_data'
            os.makedirs(data_dir, exist_ok=True)
            filename = f"{data_dir}/{symbol}_{interval}_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"
            df.to_csv(filename)
            logger.info(f"Đã lưu dữ liệu vào {filename}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu từ Binance: {e}")
            # Thử tìm dữ liệu đã lưu làm backup
            df = find_existing_data(symbol, interval, months)
            if df is not None:
                return df
            raise
    else:
        logger.warning("Không có API key/secret Binance, tìm dữ liệu đã lưu")
        df = find_existing_data(symbol, interval, months)
        if df is not None:
            return df
        else:
            raise ValueError("Không tìm thấy dữ liệu và không có API key/secret Binance để tải mới")

def find_existing_data(symbol: str, interval: str, months: int) -> Optional[pd.DataFrame]:
    """
    Tìm dữ liệu đã tải trước đó
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        months (int): Số tháng
        
    Returns:
        Optional[pd.DataFrame]: DataFrame nếu tìm thấy, None nếu không
    """
    data_dir = 'real_data'
    if not os.path.exists(data_dir):
        return None
        
    # Tìm file dữ liệu phù hợp nhất
    files = os.listdir(data_dir)
    matching_files = [f for f in files if f.startswith(f"{symbol}_{interval}")]
    
    if not matching_files:
        return None
        
    # Sắp xếp theo thời gian tạo file giảm dần
    matching_files.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)), reverse=True)
    
    # Lấy file mới nhất
    latest_file = os.path.join(data_dir, matching_files[0])
    logger.info(f"Đọc dữ liệu từ file đã lưu: {latest_file}")
    
    try:
        df = pd.read_csv(latest_file)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        logger.error(f"Lỗi khi đọc file {latest_file}: {e}")
        return None

def prepare_and_enhance_data(df: pd.DataFrame, symbol: str, 
                           interval: str, enhanced: bool = True) -> pd.DataFrame:
    """
    Chuẩn bị và tăng cường đặc trưng cho dữ liệu
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu gốc
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        enhanced (bool): Có sử dụng đặc trưng nâng cao không
        
    Returns:
        pd.DataFrame: DataFrame đã được tăng cường đặc trưng
    """
    logger.info(f"Bắt đầu xử lý và tăng cường đặc trưng cho {symbol} {interval}")
    
    # Lưu file tạm thời cho quá trình xử lý
    temp_input = f"temp_{symbol}_{interval}_input.csv"
    temp_output = f"temp_{symbol}_{interval}_output.csv"
    
    df.to_csv(temp_input)
    
    try:
        # Sử dụng module feature_engineering đã cải tiến
        enhanced_df = process_and_enhance_dataset(
            input_data=df,
            output_file=temp_output if enhanced else None,
            basic_only=not enhanced,
            exclude_patterns=False,
            exclude_time=False,
            exclude_liquidity=False,
            exclude_interactions=False
        )
        
        logger.info(f"Đã tăng cường dữ liệu: {len(enhanced_df)} dòng, {len(enhanced_df.columns)} cột")
        
        # Xóa file tạm
        try:
            os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
        except:
            pass
            
        return enhanced_df
        
    except Exception as e:
        logger.error(f"Lỗi khi tăng cường đặc trưng: {e}")
        # Fallback: sử dụng chỉ báo cơ bản nếu tăng cường thất bại
        try:
            basic_df = process_and_enhance_dataset(
                input_data=df,
                basic_only=True
            )
            logger.info(f"Fallback: Đã tạo đặc trưng cơ bản ({len(basic_df.columns)} cột)")
            return basic_df
        except:
            # Double fallback: sử dụng các chỉ báo cơ bản tự tính toán
            logger.warning("Double fallback: Sử dụng các chỉ báo cơ bản tự tính toán")
            return add_basic_indicators(df)

def add_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các chỉ báo kỹ thuật cơ bản
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu gốc
        
    Returns:
        pd.DataFrame: DataFrame với chỉ báo đã thêm
    """
    # Tạo bản sao để tránh warning
    result = df.copy()
    
    # RSI (14 periods)
    delta = result['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    rs = avg_gain / avg_loss
    result['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = result['close'].ewm(span=12, adjust=False).mean()
    ema26 = result['close'].ewm(span=26, adjust=False).mean()
    result['macd'] = ema12 - ema26
    result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
    result['macd_hist'] = result['macd'] - result['macd_signal']
    
    # Bollinger Bands
    result['bb_middle'] = result['close'].rolling(window=20).mean()
    result['bb_std'] = result['close'].rolling(window=20).std()
    result['bb_upper'] = result['bb_middle'] + (result['bb_std'] * 2)
    result['bb_lower'] = result['bb_middle'] - (result['bb_std'] * 2)
    
    # EMAs
    for period in [9, 21, 50, 200]:
        result[f'ema_{period}'] = result['close'].ewm(span=period, adjust=False).mean()
    
    # ATR
    high_low = result['high'] - result['low']
    high_close = (result['high'] - result['close'].shift()).abs()
    low_close = (result['low'] - result['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    result['atr'] = true_range.rolling(window=14).mean()
    
    # Loại bỏ missing values
    result.dropna(inplace=True)
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} chỉ báo cơ bản")
    return result

def run_backtest(df: pd.DataFrame, symbol: str, interval: str, 
               strategy_type: str = 'optimized', risk_pct: float = 2.0, 
               initial_balance: float = 10000, use_ml: bool = True) -> Dict:
    """
    Chạy backtest với dữ liệu đã tăng cường
    
    Args:
        df (pd.DataFrame): DataFrame với đặc trưng đã tăng cường
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        strategy_type (str): Loại chiến lược ('rsi', 'optimized', 'mtf')
        risk_pct (float): Phần trăm rủi ro trên mỗi giao dịch
        initial_balance (float): Số dư ban đầu
        use_ml (bool): Có sử dụng dự đoán ML không
        
    Returns:
        Dict: Kết quả backtest
    """
    logger.info(f"Bắt đầu chạy backtest {symbol} {interval} với chiến lược {strategy_type}")
    
    # Khởi tạo biến lưu trữ kết quả
    results = {
        'symbol': symbol,
        'interval': interval,
        'strategy': strategy_type,
        'start_date': df.index[0].strftime('%Y-%m-%d'),
        'end_date': df.index[-1].strftime('%Y-%m-%d'),
        'trades': [],
        'balance': initial_balance,
        'metrics': {}
    }
    
    # Khởi tạo quản lý rủi ro
    risk_manager = RiskManager(initial_balance=initial_balance, max_risk_per_trade=risk_pct)
    
    # Khởi tạo bộ phát hiện chế độ thị trường
    market_regime = MarketRegimeDetector()
    
    # Khởi tạo strategy dựa trên loại
    if strategy_type == 'rsi':
        try:
            strategy = ImprovedRsiStrategy()
        except:
            strategy = create_basic_rsi_strategy()
    elif strategy_type == 'mtf':
        try:
            strategy = MTFOptimizedStrategy()
        except:
            strategy = create_basic_mtf_strategy()
    else:  # optimized là mặc định
        try:
            strategy = OptimizedStrategy()
        except:
            strategy = create_basic_optimized_strategy()
    
    # Dữ liệu ML nếu được sử dụng
    ml_predictions = []
    if use_ml:
        try:
            # Tạo dự đoán ML nếu có thể
            ml_optimizer = MLOptimizer()
            ml_predictions = ml_optimizer.quick_predict(df)
            logger.info(f"Đã tạo {len(ml_predictions)} dự đoán ML")
        except Exception as e:
            logger.warning(f"Không thể tạo dự đoán ML: {e}")
            use_ml = False
    
    # Đánh giá từng candle cho backtest
    trades = []
    current_trade = None
    balance_history = [initial_balance]
    equity_history = [initial_balance]
    
    # Lưu lịch sử giá trị danh mục
    portfolio_values = []
    trade_points = []
    
    logger.info(f"Bắt đầu đánh giá {len(df)} candles cho backtest")
    
    for i in range(1, len(df)):
        candle = df.iloc[i]
        prev_candle = df.iloc[i-1]
        
        # Phát hiện chế độ thị trường
        try:
            regime = market_regime.detect_regime(df.iloc[max(0, i-50):i+1])
        except:
            regime = "unknown"
        
        # Tính toán tín hiệu từ strategy
        try:
            signal = strategy.generate_signal(df.iloc[max(0, i-50):i+1])
        except:
            signal = {'action': 'HOLD', 'confidence': 0.0}
        
        # Kết hợp với ML nếu có
        if use_ml and i < len(ml_predictions):
            ml_signal = ml_predictions[i]
            # Điều chỉnh tín hiệu dựa trên ML
            if ml_signal > 0.7 and signal['action'] == 'BUY':
                signal['confidence'] = max(signal['confidence'], 0.8)
            elif ml_signal < 0.3 and signal['action'] == 'SELL':
                signal['confidence'] = max(signal['confidence'], 0.8)
            elif (ml_signal > 0.6 and signal['action'] == 'HOLD') or (ml_signal < 0.4 and signal['action'] == 'HOLD'):
                signal['action'] = 'BUY' if ml_signal > 0.6 else 'SELL'
                signal['confidence'] = 0.6
        
        # Giá hiện tại và timestamp
        current_price = candle['close']
        current_time = candle.name
        
        # Cập nhật vị thế hiện tại nếu có
        if current_trade:
            # Kiểm tra xem có hit stop loss hoặc take profit không
            if current_trade['side'] == 'BUY':
                # Kiểm tra stop loss
                if current_price <= current_trade['stop_loss']:
                    # Đóng vị thế tại stop loss
                    profit = (current_trade['stop_loss'] - current_trade['entry_price']) * current_trade['quantity']
                    current_trade['exit_price'] = current_trade['stop_loss']
                    current_trade['exit_time'] = current_time
                    current_trade['profit'] = profit
                    current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
                    current_trade['exit_reason'] = 'stop_loss'
                    
                    # Cập nhật balance
                    results['balance'] += profit
                    
                    # Thêm vào lịch sử giao dịch
                    trades.append(current_trade)
                    trade_points.append((current_time, current_price, 'exit'))
                    
                    # Đặt lại vị thế hiện tại
                    current_trade = None
                
                # Kiểm tra take profit
                elif current_price >= current_trade['take_profit']:
                    # Đóng vị thế tại take profit
                    profit = (current_trade['take_profit'] - current_trade['entry_price']) * current_trade['quantity']
                    current_trade['exit_price'] = current_trade['take_profit']
                    current_trade['exit_time'] = current_time
                    current_trade['profit'] = profit
                    current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
                    current_trade['exit_reason'] = 'take_profit'
                    
                    # Cập nhật balance
                    results['balance'] += profit
                    
                    # Thêm vào lịch sử giao dịch
                    trades.append(current_trade)
                    trade_points.append((current_time, current_price, 'exit'))
                    
                    # Đặt lại vị thế hiện tại
                    current_trade = None
                
                # Kiểm tra có tín hiệu SELL không
                elif signal['action'] == 'SELL' and signal['confidence'] >= 0.7:
                    # Đóng vị thế theo tín hiệu
                    profit = (current_price - current_trade['entry_price']) * current_trade['quantity']
                    current_trade['exit_price'] = current_price
                    current_trade['exit_time'] = current_time
                    current_trade['profit'] = profit
                    current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
                    current_trade['exit_reason'] = 'signal'
                    
                    # Cập nhật balance
                    results['balance'] += profit
                    
                    # Thêm vào lịch sử giao dịch
                    trades.append(current_trade)
                    trade_points.append((current_time, current_price, 'exit'))
                    
                    # Đặt lại vị thế hiện tại
                    current_trade = None
            else:  # SELL position
                # Kiểm tra stop loss
                if current_price >= current_trade['stop_loss']:
                    # Đóng vị thế tại stop loss
                    profit = (current_trade['entry_price'] - current_trade['stop_loss']) * current_trade['quantity']
                    current_trade['exit_price'] = current_trade['stop_loss']
                    current_trade['exit_time'] = current_time
                    current_trade['profit'] = profit
                    current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
                    current_trade['exit_reason'] = 'stop_loss'
                    
                    # Cập nhật balance
                    results['balance'] += profit
                    
                    # Thêm vào lịch sử giao dịch
                    trades.append(current_trade)
                    trade_points.append((current_time, current_price, 'exit'))
                    
                    # Đặt lại vị thế hiện tại
                    current_trade = None
                
                # Kiểm tra take profit
                elif current_price <= current_trade['take_profit']:
                    # Đóng vị thế tại take profit
                    profit = (current_trade['entry_price'] - current_trade['take_profit']) * current_trade['quantity']
                    current_trade['exit_price'] = current_trade['take_profit']
                    current_trade['exit_time'] = current_time
                    current_trade['profit'] = profit
                    current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
                    current_trade['exit_reason'] = 'take_profit'
                    
                    # Cập nhật balance
                    results['balance'] += profit
                    
                    # Thêm vào lịch sử giao dịch
                    trades.append(current_trade)
                    trade_points.append((current_time, current_price, 'exit'))
                    
                    # Đặt lại vị thế hiện tại
                    current_trade = None
                
                # Kiểm tra có tín hiệu BUY không
                elif signal['action'] == 'BUY' and signal['confidence'] >= 0.7:
                    # Đóng vị thế theo tín hiệu
                    profit = (current_trade['entry_price'] - current_price) * current_trade['quantity']
                    current_trade['exit_price'] = current_price
                    current_trade['exit_time'] = current_time
                    current_trade['profit'] = profit
                    current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
                    current_trade['exit_reason'] = 'signal'
                    
                    # Cập nhật balance
                    results['balance'] += profit
                    
                    # Thêm vào lịch sử giao dịch
                    trades.append(current_trade)
                    trade_points.append((current_time, current_price, 'exit'))
                    
                    # Đặt lại vị thế hiện tại
                    current_trade = None
        
        # Nếu không có vị thế hiện tại, kiểm tra tín hiệu mới
        if not current_trade:
            if signal['action'] == 'BUY' and signal['confidence'] >= 0.7:
                # Tính toán stop loss và take profit
                atr = df['atr'].iloc[i] if 'atr' in df.columns else (df['high'].iloc[i] - df['low'].iloc[i])
                stop_loss = current_price - (2.0 * atr)
                take_profit = current_price + (3.0 * atr)
                
                # Tính số lượng dựa trên quản lý rủi ro
                risk_amount = results['balance'] * (risk_pct / 100)
                quantity = risk_amount / (current_price - stop_loss)
                
                # Mở vị thế mới
                current_trade = {
                    'side': 'BUY',
                    'entry_price': current_price,
                    'quantity': quantity,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current_time,
                    'regime': regime
                }
                
                trade_points.append((current_time, current_price, 'entry'))
                
            elif signal['action'] == 'SELL' and signal['confidence'] >= 0.7:
                # Tính toán stop loss và take profit
                atr = df['atr'].iloc[i] if 'atr' in df.columns else (df['high'].iloc[i] - df['low'].iloc[i])
                stop_loss = current_price + (2.0 * atr)
                take_profit = current_price - (3.0 * atr)
                
                # Tính số lượng dựa trên quản lý rủi ro
                risk_amount = results['balance'] * (risk_pct / 100)
                quantity = risk_amount / (stop_loss - current_price)
                
                # Mở vị thế mới
                current_trade = {
                    'side': 'SELL',
                    'entry_price': current_price,
                    'quantity': quantity,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current_time,
                    'regime': regime
                }
                
                trade_points.append((current_time, current_price, 'entry'))
        
        # Tính toán giá trị danh mục hiện tại
        if current_trade:
            if current_trade['side'] == 'BUY':
                unrealized_profit = (current_price - current_trade['entry_price']) * current_trade['quantity']
            else:  # SELL
                unrealized_profit = (current_trade['entry_price'] - current_price) * current_trade['quantity']
                
            current_equity = results['balance'] + unrealized_profit
        else:
            current_equity = results['balance']
            
        equity_history.append(current_equity)
        
        # Lưu giá trị danh mục
        portfolio_values.append((current_time, current_equity))
    
    # Đóng vị thế cuối cùng nếu có
    if current_trade:
        current_price = df['close'].iloc[-1]
        current_time = df.index[-1]
        
        if current_trade['side'] == 'BUY':
            profit = (current_price - current_trade['entry_price']) * current_trade['quantity']
        else:  # SELL
            profit = (current_trade['entry_price'] - current_price) * current_trade['quantity']
            
        current_trade['exit_price'] = current_price
        current_trade['exit_time'] = current_time
        current_trade['profit'] = profit
        current_trade['roi'] = profit / (current_trade['entry_price'] * current_trade['quantity']) * 100
        current_trade['exit_reason'] = 'end_of_test'
        
        # Cập nhật balance
        results['balance'] += profit
        
        # Thêm vào lịch sử giao dịch
        trades.append(current_trade)
        trade_points.append((current_time, current_price, 'exit'))
    
    # Lưu tất cả các giao dịch
    results['trades'] = trades
    
    # Tính toán các chỉ số hiệu suất
    if trades:
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t['profit'] > 0)
        losing_trades = total_trades - profitable_trades
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['profit'] for t in trades if t['profit'] > 0)
        total_loss = sum(t['profit'] for t in trades if t['profit'] <= 0)
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
        
        avg_profit = total_profit / profitable_trades if profitable_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # Tính drawdown
        peak = initial_balance
        drawdowns = []
        for equity in equity_history:
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown)
            
        max_drawdown = max(drawdowns) if drawdowns else 0
        
        # Tính Sharpe Ratio (simplified annual)
        returns = []
        for i in range(1, len(equity_history)):
            returns.append((equity_history[i] - equity_history[i-1]) / equity_history[i-1])
            
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if returns else 1e-9
        
        # Ước tính số lần giao dịch trong năm
        annual_factor = 365 / ((df.index[-1] - df.index[0]).days) if (df.index[-1] - df.index[0]).days > 0 else 1
        sharpe_ratio = (avg_return / std_return) * np.sqrt(len(returns) * annual_factor) if std_return > 0 else 0
        
        # ROI tổng thể
        total_roi = (results['balance'] - initial_balance) / initial_balance * 100
        
        # Lưu các metrics
        results['metrics'] = {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_roi': total_roi,
            'final_balance': results['balance']
        }
        
        # In kết quả tóm tắt
        logger.info(f"=== KẾT QUẢ BACKTEST {symbol} {interval} {strategy_type} ===")
        logger.info(f"Tổng số giao dịch: {total_trades}")
        logger.info(f"Tỷ lệ thắng: {win_rate:.2%}")
        logger.info(f"Hệ số lợi nhuận: {profit_factor:.2f}")
        logger.info(f"Lợi nhuận trung bình: {avg_profit:.2f}")
        logger.info(f"Thua lỗ trung bình: {avg_loss:.2f}")
        logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
        logger.info(f"Sharpe ratio: {sharpe_ratio:.2f}")
        logger.info(f"ROI: {total_roi:.2f}%")
        logger.info(f"Số dư cuối: {results['balance']:.2f}")
    else:
        logger.warning("Không có giao dịch nào được thực hiện trong quá trình backtest")
        results['metrics'] = {
            'total_trades': 0,
            'profitable_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'avg_profit': 0,
            'avg_loss': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'total_roi': 0,
            'final_balance': results['balance']
        }
    
    # Tạo chart
    create_equity_chart(symbol, interval, strategy_type, portfolio_values, trade_points)
    
    # Lưu kết quả
    save_backtest_results(results, symbol, interval, strategy_type)
    
    return results

def create_equity_chart(symbol: str, interval: str, strategy_type: str, 
                      portfolio_values: List[Tuple], trade_points: List[Tuple]) -> str:
    """
    Tạo biểu đồ equity curve với các điểm giao dịch
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        strategy_type (str): Loại chiến lược
        portfolio_values (List[Tuple]): Lịch sử giá trị danh mục (thời gian, giá trị)
        trade_points (List[Tuple]): Các điểm giao dịch (thời gian, giá, loại)
        
    Returns:
        str: Đường dẫn tới file biểu đồ
    """
    try:
        # Tạo thư mục backtest_charts nếu chưa tồn tại
        os.makedirs('backtest_charts', exist_ok=True)
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 8))
        
        # Vẽ đường equity
        dates = [pv[0] for pv in portfolio_values]
        values = [pv[1] for pv in portfolio_values]
        plt.plot(dates, values, label='Equity Curve')
        
        # Vẽ các điểm giao dịch
        entries = [tp for tp in trade_points if tp[2] == 'entry']
        exits = [tp for tp in trade_points if tp[2] == 'exit']
        
        if entries:
            entry_dates = [tp[0] for tp in entries]
            entry_values = [values[dates.index(tp[0])] if tp[0] in dates else None for tp in entries]
            entry_values = [ev for ev in entry_values if ev is not None]
            if entry_values:
                plt.scatter(entry_dates[:len(entry_values)], entry_values, color='g', marker='^', s=100, label='Entries')
        
        if exits:
            exit_dates = [tp[0] for tp in exits]
            exit_values = [values[dates.index(tp[0])] if tp[0] in dates else None for tp in exits]
            exit_values = [ev for ev in exit_values if ev is not None]
            if exit_values:
                plt.scatter(exit_dates[:len(exit_values)], exit_values, color='r', marker='v', s=100, label='Exits')
        
        plt.title(f'Equity Curve - {symbol} {interval} ({strategy_type})')
        plt.xlabel('Date')
        plt.ylabel('Equity Value')
        plt.grid(True)
        plt.legend()
        
        # Lưu biểu đồ
        filename = f"backtest_charts/{symbol}_{interval}_{strategy_type}_equity.png"
        plt.savefig(filename)
        plt.close()
        
        logger.info(f"Đã lưu biểu đồ equity curve vào {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ equity curve: {e}")
        return ""

def save_backtest_results(results: Dict, symbol: str, interval: str, strategy_type: str) -> str:
    """
    Lưu kết quả backtest vào file JSON
    
    Args:
        results (Dict): Kết quả backtest
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        strategy_type (str): Loại chiến lược
        
    Returns:
        str: Đường dẫn tới file kết quả
    """
    try:
        # Tạo thư mục backtest_results nếu chưa tồn tại
        os.makedirs('backtest_results', exist_ok=True)
        
        # Chuyển đổi datetime sang string để có thể serialize
        serializable_results = results.copy()
        for trade in serializable_results['trades']:
            trade['entry_time'] = trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
            trade['exit_time'] = trade['exit_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Lưu kết quả vào file JSON
        filename = f"backtest_results/{symbol}_{interval}_{strategy_type}_results.json"
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=4)
            
        logger.info(f"Đã lưu kết quả backtest vào {filename}")
        
        # Tạo file CSV với các giao dịch chi tiết
        trades_filename = f"backtest_results/{symbol}_{interval}_{strategy_type}_trades.csv"
        trades_df = pd.DataFrame(serializable_results['trades'])
        if not trades_df.empty:
            trades_df.to_csv(trades_filename, index=False)
            logger.info(f"Đã lưu chi tiết giao dịch vào {trades_filename}")
        
        return filename
        
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả backtest: {e}")
        return ""

def create_basic_rsi_strategy():
    """
    Tạo chiến lược RSI cơ bản làm fallback
    
    Returns:
        object: Đối tượng chiến lược với phương thức generate_signal
    """
    class BasicRsiStrategy:
        def __init__(self):
            self.rsi_period = 14
            self.rsi_overbought = 70
            self.rsi_oversold = 30
            
        def generate_signal(self, df):
            if 'rsi' not in df.columns:
                return {'action': 'HOLD', 'confidence': 0.0}
                
            last_rsi = df['rsi'].iloc[-1]
            prev_rsi = df['rsi'].iloc[-2]
            
            if last_rsi < self.rsi_oversold and prev_rsi < self.rsi_oversold:
                return {'action': 'BUY', 'confidence': 0.8}
            elif last_rsi > self.rsi_overbought and prev_rsi > self.rsi_overbought:
                return {'action': 'SELL', 'confidence': 0.8}
            else:
                return {'action': 'HOLD', 'confidence': 0.0}
    
    return BasicRsiStrategy()

def create_basic_optimized_strategy():
    """
    Tạo chiến lược tối ưu cơ bản làm fallback
    
    Returns:
        object: Đối tượng chiến lược với phương thức generate_signal
    """
    class BasicOptimizedStrategy:
        def __init__(self):
            self.rsi_period = 14
            self.rsi_overbought = 70
            self.rsi_oversold = 30
            self.macd_fast = 12
            self.macd_slow = 26
            self.macd_signal = 9
            
        def generate_signal(self, df):
            if 'rsi' not in df.columns or 'macd' not in df.columns:
                return {'action': 'HOLD', 'confidence': 0.0}
                
            last_rsi = df['rsi'].iloc[-1]
            prev_rsi = df['rsi'].iloc[-2]
            
            last_macd = df['macd'].iloc[-1]
            last_macd_signal = df['macd_signal'].iloc[-1]
            last_macd_hist = df['macd_hist'].iloc[-1]
            prev_macd_hist = df['macd_hist'].iloc[-2]
            
            macd_cross_up = last_macd > last_macd_signal and df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2]
            macd_cross_down = last_macd < last_macd_signal and df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2]
            
            confidence = 0.0
            action = 'HOLD'
            
            # RSI conditions
            if last_rsi < self.rsi_oversold:
                confidence += 0.4
                action = 'BUY'
            elif last_rsi > self.rsi_overbought:
                confidence += 0.4
                action = 'SELL'
                
            # MACD conditions
            if macd_cross_up and last_macd_hist > 0:
                if action == 'BUY':
                    confidence += 0.4
                else:
                    confidence = 0.4
                    action = 'BUY'
            elif macd_cross_down and last_macd_hist < 0:
                if action == 'SELL':
                    confidence += 0.4
                else:
                    confidence = 0.4
                    action = 'SELL'
            
            # Check if MACD histogram is increasing/decreasing
            if last_macd_hist > 0 and last_macd_hist > prev_macd_hist:
                if action == 'BUY':
                    confidence += 0.2
                elif action == 'HOLD':
                    confidence = 0.2
                    action = 'BUY'
            elif last_macd_hist < 0 and last_macd_hist < prev_macd_hist:
                if action == 'SELL':
                    confidence += 0.2
                elif action == 'HOLD':
                    confidence = 0.2
                    action = 'SELL'
            
            return {'action': action, 'confidence': confidence}
    
    return BasicOptimizedStrategy()

def create_basic_mtf_strategy():
    """
    Tạo chiến lược đa khung thời gian cơ bản làm fallback
    
    Returns:
        object: Đối tượng chiến lược với phương thức generate_signal
    """
    class BasicMTFStrategy:
        def __init__(self):
            self.rsi_period = 14
            self.rsi_overbought = 70
            self.rsi_oversold = 30
            
        def generate_signal(self, df):
            if 'rsi' not in df.columns or 'ema_9' not in df.columns or 'ema_21' not in df.columns:
                return {'action': 'HOLD', 'confidence': 0.0}
                
            last_rsi = df['rsi'].iloc[-1]
            last_close = df['close'].iloc[-1]
            last_ema9 = df['ema_9'].iloc[-1]
            last_ema21 = df['ema_21'].iloc[-1]
            
            confidence = 0.0
            action = 'HOLD'
            
            # Trend analysis
            if last_close > last_ema9 and last_ema9 > last_ema21:
                trend = 'uptrend'
            elif last_close < last_ema9 and last_ema9 < last_ema21:
                trend = 'downtrend'
            else:
                trend = 'sideways'
            
            # RSI conditions
            if last_rsi < self.rsi_oversold and trend != 'downtrend':
                confidence += 0.5
                action = 'BUY'
            elif last_rsi > self.rsi_overbought and trend != 'uptrend':
                confidence += 0.5
                action = 'SELL'
            
            # EMA cross conditions
            if last_ema9 > last_ema21 and df['ema_9'].iloc[-2] <= df['ema_21'].iloc[-2]:
                if action == 'BUY':
                    confidence += 0.3
                else:
                    confidence = 0.3
                    action = 'BUY'
            elif last_ema9 < last_ema21 and df['ema_9'].iloc[-2] >= df['ema_21'].iloc[-2]:
                if action == 'SELL':
                    confidence += 0.3
                else:
                    confidence = 0.3
                    action = 'SELL'
            
            return {'action': action, 'confidence': confidence}
    
    return BasicMTFStrategy()

def generate_summary_report(results: List[Dict], output_file: str = 'backtest_summary/summary_report.html') -> str:
    """
    Tạo báo cáo tổng hợp HTML từ nhiều kết quả backtest
    
    Args:
        results (List[Dict]): Danh sách kết quả backtest
        output_file (str): Đường dẫn file báo cáo
        
    Returns:
        str: Đường dẫn tới file báo cáo
    """
    try:
        # Tạo thư mục backtest_summary nếu chưa tồn tại
        os.makedirs('backtest_summary', exist_ok=True)
        
        # Tạo bảng kết quả tổng hợp
        result_summary = []
        for r in results:
            result_summary.append({
                'Symbol': r['symbol'],
                'Interval': r['interval'],
                'Strategy': r['strategy'],
                'Period': f"{r['start_date']} to {r['end_date']}",
                'Total Trades': r['metrics']['total_trades'],
                'Win Rate': f"{r['metrics']['win_rate']:.2%}",
                'Profit Factor': f"{r['metrics']['profit_factor']:.2f}",
                'Max Drawdown': f"{r['metrics']['max_drawdown']:.2f}%",
                'Sharpe Ratio': f"{r['metrics']['sharpe_ratio']:.2f}",
                'ROI': f"{r['metrics']['total_roi']:.2f}%",
                'Final Balance': f"{r['metrics']['final_balance']:.2f}"
            })
        
        # Tạo nội dung HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Results Summary</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                h1, h2, h3 {{
                    color: #333;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 20px;
                    background-color: white;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #4CAF50;
                    color: white;
                }}
                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                .chart {{
                    margin-bottom: 30px;
                    text-align: center;
                }}
                .chart img {{
                    max-width: 100%;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }}
                .summary {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .positive {{
                    color: green;
                }}
                .negative {{
                    color: red;
                }}
            </style>
        </head>
        <body>
            <h1>Backtest Results Summary</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Performance Summary</h2>
                <table>
                    <tr>
                        <th>Symbol</th>
                        <th>Interval</th>
                        <th>Strategy</th>
                        <th>Period</th>
                        <th>Total Trades</th>
                        <th>Win Rate</th>
                        <th>Profit Factor</th>
                        <th>Max Drawdown</th>
                        <th>Sharpe Ratio</th>
                        <th>ROI</th>
                        <th>Final Balance</th>
                    </tr>
        """
        
        # Thêm các dòng trong bảng
        for summary in result_summary:
            roi_class = "positive" if float(summary['ROI'].rstrip('%')) > 0 else "negative"
            html_content += f"""
                    <tr>
                        <td>{summary['Symbol']}</td>
                        <td>{summary['Interval']}</td>
                        <td>{summary['Strategy']}</td>
                        <td>{summary['Period']}</td>
                        <td>{summary['Total Trades']}</td>
                        <td>{summary['Win Rate']}</td>
                        <td>{summary['Profit Factor']}</td>
                        <td>{summary['Max Drawdown']}</td>
                        <td>{summary['Sharpe Ratio']}</td>
                        <td class="{roi_class}">{summary['ROI']}</td>
                        <td>{summary['Final Balance']}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
        """
        
        # Thêm các biểu đồ
        html_content += """
            <h2>Equity Curves</h2>
        """
        
        for r in results:
            chart_path = f"backtest_charts/{r['symbol']}_{r['interval']}_{r['strategy']}_equity.png"
            if os.path.exists(chart_path):
                html_content += f"""
                <div class="chart">
                    <h3>{r['symbol']} {r['interval']} ({r['strategy']})</h3>
                    <img src="../{chart_path}" alt="{r['symbol']} {r['interval']} Equity Curve">
                </div>
                """
        
        # Kết thúc trang
        html_content += """
        </body>
        </html>
        """
        
        # Lưu nội dung HTML vào file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"Đã tạo báo cáo tổng hợp tại {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {e}")
        return ""

def main():
    parser = argparse.ArgumentParser(description='Backtest trên dữ liệu thực tế 6 tháng')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'], help='Các cặp giao dịch cần backtest')
    parser.add_argument('--intervals', nargs='+', default=['1h', '4h'], help='Các khung thời gian cần backtest')
    parser.add_argument('--strategies', nargs='+', default=['optimized', 'rsi', 'mtf'], help='Các chiến lược cần backtest')
    parser.add_argument('--months', type=int, default=6, help='Số tháng dữ liệu cần tải')
    parser.add_argument('--initial_balance', type=float, default=10000, help='Số dư ban đầu cho backtest')
    parser.add_argument('--risk_pct', type=float, default=2.0, help='Phần trăm rủi ro trên mỗi giao dịch')
    parser.add_argument('--use_ml', action='store_true', help='Có sử dụng dự đoán ML không')
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu backtest với các tham số: {args}")
    
    all_results = []
    
    for symbol in args.symbols:
        for interval in args.intervals:
            try:
                # Tải dữ liệu
                df = download_historical_data(symbol, interval, args.months)
                
                # Tăng cường đặc trưng
                enhanced_df = prepare_and_enhance_data(df, symbol, interval)
                
                # Chạy backtest với từng chiến lược
                for strategy in args.strategies:
                    try:
                        result = run_backtest(
                            enhanced_df, 
                            symbol, 
                            interval, 
                            strategy_type=strategy,
                            risk_pct=args.risk_pct,
                            initial_balance=args.initial_balance,
                            use_ml=args.use_ml
                        )
                        all_results.append(result)
                    except Exception as e:
                        logger.error(f"Lỗi khi chạy backtest {symbol} {interval} {strategy}: {e}")
            except Exception as e:
                logger.error(f"Lỗi khi xử lý {symbol} {interval}: {e}")
    
    # Tạo báo cáo tổng hợp
    if all_results:
        generate_summary_report(all_results)
        logger.info("Đã hoàn thành tất cả các backtest và tạo báo cáo tổng hợp")
    else:
        logger.error("Không có kết quả backtest nào để tạo báo cáo")

if __name__ == "__main__":
    main()