#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiểm thử trên dữ liệu thực tế 6 tháng (phiên bản đơn giản hóa)

Script này tải dữ liệu thực tế 6 tháng từ Binance và thực hiện backtest 
sử dụng các chiến lược đơn giản. Kết quả sẽ được lưu lại và phân tích chi tiết.
"""

import os
import sys
import argparse
import logging
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional, Union

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
    logger.info("Đã import thành công binance_api module")
except ImportError as e:
    logger.error(f"Lỗi khi import binance_api module: {e}")
    sys.exit(1)

def download_historical_data(symbol: str, interval: str, months: int = 6) -> pd.DataFrame:
    """
    Tải dữ liệu lịch sử từ Binance hoặc sử dụng dữ liệu mẫu
    
    Args:
        symbol (str): Cặp giao dịch (ví dụ: BTCUSDT)
        interval (str): Khung thời gian (ví dụ: 1h, 4h, 1d)
        months (int): Số tháng dữ liệu cần tải
        
    Returns:
        pd.DataFrame: DataFrame chứa dữ liệu lịch sử OHLCV
    """
    # Tính toán thời gian bắt đầu và kết thúc
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30*months)
    
    logger.info(f"Tải dữ liệu {symbol} {interval} từ {start_time.strftime('%Y-%m-%d')} đến {end_time.strftime('%Y-%m-%d')}")
    
    # Tạo thư mục nếu cần
    data_dir = 'real_data'
    os.makedirs(data_dir, exist_ok=True)
    
    # Tên file dữ liệu
    filename = f"{data_dir}/{symbol}_{interval}_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}.csv"
    
    # Nếu file đã tồn tại, sử dụng nó
    if os.path.exists(filename):
        logger.info(f"Sử dụng dữ liệu đã lưu từ {filename}")
        df = pd.read_csv(filename)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        return df
    
    # Tìm file dữ liệu mẫu
    sample_filename = f"{data_dir}/{symbol}_{interval}_sample.csv"
    if os.path.exists(sample_filename):
        logger.info(f"Sử dụng dữ liệu mẫu từ {sample_filename}")
        df = pd.read_csv(sample_filename)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        return df
    
    # Lấy API key và secret từ biến môi trường
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
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
            df.to_csv(filename)
            logger.info(f"Đã lưu dữ liệu vào {filename}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu từ Binance: {e}")
            # Tạo dữ liệu mẫu nếu có thể
            try:
                from generate_sample_data import generate_price_series
                logger.info(f"Tạo dữ liệu mẫu cho {symbol} {interval}...")
                
                sample_df = generate_price_series(symbol=symbol, days=30*months, interval=interval)
                sample_df.to_csv(sample_filename)
                logger.info(f"Đã lưu dữ liệu mẫu vào {sample_filename}")
                
                if 'timestamp' in sample_df.columns:
                    sample_df['timestamp'] = pd.to_datetime(sample_df['timestamp'])
                    sample_df.set_index('timestamp', inplace=True)
                    
                return sample_df
            except Exception as sample_error:
                logger.error(f"Không thể tạo dữ liệu mẫu: {sample_error}")
                raise ValueError(f"Không thể tải dữ liệu từ Binance và không thể tạo dữ liệu mẫu: {e}")
    else:
        # Tạo dữ liệu mẫu nếu không có API key
        try:
            from generate_sample_data import generate_price_series
            logger.info(f"Tạo dữ liệu mẫu cho {symbol} {interval}...")
            
            sample_df = generate_price_series(symbol=symbol, days=30*months, interval=interval)
            sample_df.to_csv(sample_filename)
            logger.info(f"Đã lưu dữ liệu mẫu vào {sample_filename}")
            
            if 'timestamp' in sample_df.columns:
                sample_df['timestamp'] = pd.to_datetime(sample_df['timestamp'])
                sample_df.set_index('timestamp', inplace=True)
                
            return sample_df
        except Exception as sample_error:
            logger.error(f"Không thể tạo dữ liệu mẫu: {sample_error}")
            raise ValueError("Không có API key/secret Binance và không thể tạo dữ liệu mẫu")

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thêm các chỉ báo kỹ thuật vào DataFrame
    
    Args:
        df (pd.DataFrame): DataFrame gốc
        
    Returns:
        pd.DataFrame: DataFrame với các chỉ báo đã thêm
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
    result['sma20'] = result['close'].rolling(window=20).mean()
    result['bb_middle'] = result['sma20']
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
    
    # Stochastic Oscillator
    period = 14
    result['lowest_low'] = result['low'].rolling(window=period).min()
    result['highest_high'] = result['high'].rolling(window=period).max()
    result['stoch_k'] = 100 * ((result['close'] - result['lowest_low']) / 
                              (result['highest_high'] - result['lowest_low']))
    result['stoch_d'] = result['stoch_k'].rolling(window=3).mean()
    
    # Loại bỏ missing values
    result.dropna(inplace=True)
    
    logger.info(f"Đã thêm {len(result.columns) - len(df.columns)} chỉ báo cơ bản")
    return result

class TradingStrategy:
    """Lớp chiến lược giao dịch cơ sở"""
    
    def __init__(self, name: str):
        self.name = name
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Tạo tín hiệu giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu và chỉ báo
            
        Returns:
            Dict: Tín hiệu giao dịch (action và confidence)
        """
        # Phương thức cơ sở, nên được ghi đè
        return {'action': 'HOLD', 'confidence': 0.0}

class RsiStrategy(TradingStrategy):
    """Chiến lược dựa trên RSI"""
    
    def __init__(self, overbought: int = 70, oversold: int = 30, period: int = 14):
        super().__init__("RSI")
        self.overbought = overbought
        self.oversold = oversold
        self.period = period
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        if 'rsi' not in df.columns:
            return {'action': 'HOLD', 'confidence': 0.0}
            
        last_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2] if len(df) > 1 else last_rsi
        
        action = 'HOLD'
        confidence = 0.0
        
        # Tín hiệu mua khi RSI dưới ngưỡng oversold và đang tăng
        if last_rsi < self.oversold:
            action = 'BUY'
            confidence = 0.7
            # Tăng độ tin cậy nếu RSI đang đi lên từ đáy
            if last_rsi > prev_rsi:
                confidence = 0.8
                
        # Tín hiệu bán khi RSI trên ngưỡng overbought và đang giảm
        elif last_rsi > self.overbought:
            action = 'SELL'
            confidence = 0.7
            # Tăng độ tin cậy nếu RSI đang đi xuống từ đỉnh
            if last_rsi < prev_rsi:
                confidence = 0.8
                
        return {'action': action, 'confidence': confidence}

class MacdStrategy(TradingStrategy):
    """Chiến lược dựa trên MACD"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__("MACD")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        if 'macd' not in df.columns or 'macd_signal' not in df.columns:
            return {'action': 'HOLD', 'confidence': 0.0}
            
        last_macd = df['macd'].iloc[-1]
        last_signal = df['macd_signal'].iloc[-1]
        last_hist = df['macd_hist'].iloc[-1]
        
        prev_macd = df['macd'].iloc[-2] if len(df) > 1 else last_macd
        prev_signal = df['macd_signal'].iloc[-2] if len(df) > 1 else last_signal
        prev_hist = df['macd_hist'].iloc[-2] if len(df) > 1 else last_hist
        
        action = 'HOLD'
        confidence = 0.0
        
        # Tín hiệu cắt lên (bullish)
        if last_macd > last_signal and prev_macd <= prev_signal:
            action = 'BUY'
            confidence = 0.7
            # Tăng độ tin cậy nếu histogram đi lên và dương
            if last_hist > 0 and last_hist > prev_hist:
                confidence = 0.8
                
        # Tín hiệu cắt xuống (bearish)
        elif last_macd < last_signal and prev_macd >= prev_signal:
            action = 'SELL'
            confidence = 0.7
            # Tăng độ tin cậy nếu histogram đi xuống và âm
            if last_hist < 0 and last_hist < prev_hist:
                confidence = 0.8
        
        # Tín hiệu xác nhận xu hướng
        elif last_macd > last_signal and last_hist > prev_hist and last_hist > 0:
            action = 'BUY'
            confidence = 0.6
        elif last_macd < last_signal and last_hist < prev_hist and last_hist < 0:
            action = 'SELL'
            confidence = 0.6
                
        return {'action': action, 'confidence': confidence}

class BollingerBandsStrategy(TradingStrategy):
    """Chiến lược dựa trên Bollinger Bands"""
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("BollingerBands")
        self.period = period
        self.std_dev = std_dev
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
            return {'action': 'HOLD', 'confidence': 0.0}
            
        last_close = df['close'].iloc[-1]
        last_upper = df['bb_upper'].iloc[-1]
        last_lower = df['bb_lower'].iloc[-1]
        last_middle = df['bb_middle'].iloc[-1]
        
        prev_close = df['close'].iloc[-2] if len(df) > 1 else last_close
        
        action = 'HOLD'
        confidence = 0.0
        
        # Tín hiệu phá vỡ từ dưới lên
        if prev_close <= last_lower and last_close > last_lower:
            action = 'BUY'
            confidence = 0.7
            
        # Tín hiệu phá vỡ từ trên xuống
        elif prev_close >= last_upper and last_close < last_upper:
            action = 'SELL'
            confidence = 0.7
            
        # Tín hiệu quá bán (dưới dải dưới)
        elif last_close < last_lower:
            action = 'BUY'
            confidence = 0.6
            # Tăng độ tin cậy nếu càng xa dải dưới
            ratio = (last_lower - last_close) / (last_upper - last_lower)
            if ratio > 0.1:  # Càng xa dải dưới
                confidence = min(0.8, 0.6 + ratio)
                
        # Tín hiệu quá mua (trên dải trên)
        elif last_close > last_upper:
            action = 'SELL'
            confidence = 0.6
            # Tăng độ tin cậy nếu càng xa dải trên
            ratio = (last_close - last_upper) / (last_upper - last_lower)
            if ratio > 0.1:  # Càng xa dải trên
                confidence = min(0.8, 0.6 + ratio)
                
        return {'action': action, 'confidence': confidence}

class CompositeStrategy(TradingStrategy):
    """Chiến lược kết hợp nhiều chỉ báo"""
    
    def __init__(self, strategies: List[TradingStrategy] = None, weights: Dict[str, float] = None):
        super().__init__("Composite")
        self.strategies = strategies or []
        self.weights = weights or {}
        
        # Nếu không có trọng số, gán đều
        if not self.weights and self.strategies:
            equal_weight = 1.0 / len(self.strategies)
            self.weights = {s.name: equal_weight for s in self.strategies}
    
    def add_strategy(self, strategy: TradingStrategy, weight: float = None):
        """Thêm chiến lược vào composite"""
        self.strategies.append(strategy)
        
        # Nếu không có trọng số, gán đều cho tất cả
        if weight is not None:
            self.weights[strategy.name] = weight
        else:
            equal_weight = 1.0 / len(self.strategies)
            self.weights = {s.name: equal_weight for s in self.strategies}
    
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        if not self.strategies:
            return {'action': 'HOLD', 'confidence': 0.0}
            
        # Thu thập tín hiệu từ tất cả các chiến lược
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        strategy_signals = {}
        
        for strategy in self.strategies:
            try:
                signal = strategy.generate_signal(df)
                weight = self.weights.get(strategy.name, 1.0 / len(self.strategies))
                
                strategy_signals[strategy.name] = signal
                
                if signal['action'] == 'BUY':
                    buy_score += signal['confidence'] * weight
                elif signal['action'] == 'SELL':
                    sell_score += signal['confidence'] * weight
                    
                total_weight += weight
            except Exception as e:
                logger.error(f"Lỗi khi tạo tín hiệu từ chiến lược {strategy.name}: {e}")
        
        # Chuẩn hóa tổng trọng số
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight
        
        # Quyết định tín hiệu cuối cùng
        action = 'HOLD'
        confidence = 0.0
        
        if buy_score > sell_score and buy_score > 0.5:
            action = 'BUY'
            confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.5:
            action = 'SELL'
            confidence = sell_score
            
        # Thêm chi tiết về các tín hiệu thành phần
        return {
            'action': action, 
            'confidence': confidence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'strategy_signals': strategy_signals
        }

def run_backtest(df: pd.DataFrame, strategy: TradingStrategy, 
               symbol: str, interval: str,
               initial_balance: float = 10000.0, 
               risk_pct: float = 2.0,
               leverage: int = 5,
               take_profit_pct: float = 15.0,
               stop_loss_pct: float = 7.0,
               use_trailing_stop: bool = True) -> Dict:
    """
    Chạy backtest với một chiến lược
    
    Args:
        df (pd.DataFrame): DataFrame dữ liệu với chỉ báo
        strategy (TradingStrategy): Chiến lược giao dịch
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        initial_balance (float): Số dư ban đầu
        risk_pct (float): Phần trăm rủi ro trên mỗi giao dịch
        leverage (int): Đòn bẩy
        take_profit_pct (float): Phần trăm take profit
        stop_loss_pct (float): Phần trăm stop loss
        use_trailing_stop (bool): Sử dụng trailing stop
        
    Returns:
        Dict: Kết quả backtest
    """
    logger.info(f"=== BACKTEST {strategy.name} on {symbol} {interval} ===")
    logger.info(f"Số dư ban đầu: ${initial_balance}")
    logger.info(f"Rủi ro: {risk_pct}%")
    logger.info(f"Đòn bẩy: {leverage}x")
    logger.info(f"Take profit: {take_profit_pct}%")
    logger.info(f"Stop loss: {stop_loss_pct}%")
    logger.info(f"Trailing stop: {'Enabled' if use_trailing_stop else 'Disabled'}")
    
    # Khởi tạo biến lưu trữ kết quả
    results = {
        'symbol': symbol,
        'interval': interval,
        'strategy': strategy.name,
        'start_date': df.index[0].strftime('%Y-%m-%d'),
        'end_date': df.index[-1].strftime('%Y-%m-%d'),
        'trades': [],
        'balance': initial_balance,
        'metrics': {}
    }
    
    # Danh sách để lưu trữ các giao dịch và giá trị danh mục
    trades = []
    portfolio_values = []
    equity_history = [initial_balance]
    dates = [df.index[0]]
    
    # Trạng thái giao dịch hiện tại
    current_position = None
    balance = initial_balance
    
    # Chạy backtest
    for i in range(1, len(df)):
        current_data = df.iloc[:i+1]
        
        # Tạo tín hiệu từ chiến lược
        signal = strategy.generate_signal(current_data)
        
        current_price = current_data['close'].iloc[-1]
        current_date = current_data.index[-1]
        
        # Cập nhật trailing stop nếu có vị thế mở
        if current_position:
            # Kiểm tra stop loss hoặc take profit
            if current_position['side'] == 'BUY':
                # Cập nhật trailing stop
                if use_trailing_stop and current_price > current_position['entry_price']:
                    # Điểm kích hoạt trailing stop (khi đạt 50% đường đến take profit)
                    activation_threshold = current_position['entry_price'] + (current_position['take_profit'] - current_position['entry_price']) * 0.5
                    
                    if current_price >= activation_threshold:
                        # Trailing stop đã được kích hoạt
                        if not current_position.get('trailing_active', False):
                            logger.info(f"Trailing stop được kích hoạt tại {current_date}: {current_price:.2f}")
                            current_position['trailing_active'] = True
                        
                        # Cập nhật highest price
                        if current_price > current_position.get('highest_price', current_position['entry_price']):
                            current_position['highest_price'] = current_price
                            
                            # Cập nhật stop loss mới (10% dưới giá cao nhất)
                            new_stop_loss = current_position['highest_price'] * (1 - 0.1)
                            
                            # Chỉ di chuyển stop loss lên, không bao giờ xuống
                            if new_stop_loss > current_position['stop_loss']:
                                current_position['stop_loss'] = new_stop_loss
                                logger.info(f"Cập nhật trailing stop tại {current_date}: {new_stop_loss:.2f}")
                
                # Kiểm tra hit stop loss
                if current_price <= current_position['stop_loss']:
                    # Đóng vị thế - STOP LOSS
                    pnl = (current_position['stop_loss'] - current_position['entry_price']) * current_position['quantity'] * leverage
                    balance += pnl
                    
                    close_details = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_position['stop_loss'],
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': 'stop_loss',
                        'leverage': leverage
                    }
                    
                    trades.append(close_details)
                    logger.info(f"STOP LOSS (BUY) tại {current_date}: {current_position['stop_loss']:.2f}, PnL: {pnl:.2f}")
                    
                    current_position = None
                    
                # Kiểm tra hit take profit
                elif current_price >= current_position['take_profit'] and not current_position.get('trailing_active', False):
                    # Đóng vị thế - TAKE PROFIT
                    pnl = (current_position['take_profit'] - current_position['entry_price']) * current_position['quantity'] * leverage
                    balance += pnl
                    
                    close_details = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_position['take_profit'],
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': 'take_profit',
                        'leverage': leverage
                    }
                    
                    trades.append(close_details)
                    logger.info(f"TAKE PROFIT (BUY) tại {current_date}: {current_position['take_profit']:.2f}, PnL: {pnl:.2f}")
                    
                    current_position = None
                
                # Kiểm tra tín hiệu đảo chiều mạnh
                elif signal['action'] == 'SELL' and signal['confidence'] >= 0.8:
                    # Đóng vị thế - TÍN HIỆU
                    pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
                    balance += pnl
                    
                    close_details = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': 'signal_reverse',
                        'leverage': leverage
                    }
                    
                    trades.append(close_details)
                    logger.info(f"TÍN HIỆU ĐẢO CHIỀU (BUY->SELL) tại {current_date}: {current_price:.2f}, PnL: {pnl:.2f}")
                    
                    current_position = None
                
            else:  # SELL position
                # Cập nhật trailing stop
                if use_trailing_stop and current_price < current_position['entry_price']:
                    # Điểm kích hoạt trailing stop (khi đạt 50% đường đến take profit)
                    activation_threshold = current_position['entry_price'] - (current_position['entry_price'] - current_position['take_profit']) * 0.5
                    
                    if current_price <= activation_threshold:
                        # Trailing stop đã được kích hoạt
                        if not current_position.get('trailing_active', False):
                            logger.info(f"Trailing stop được kích hoạt tại {current_date}: {current_price:.2f}")
                            current_position['trailing_active'] = True
                        
                        # Cập nhật lowest price
                        if current_price < current_position.get('lowest_price', current_position['entry_price']):
                            current_position['lowest_price'] = current_price
                            
                            # Cập nhật stop loss mới (10% trên giá thấp nhất)
                            new_stop_loss = current_position['lowest_price'] * (1 + 0.1)
                            
                            # Chỉ di chuyển stop loss xuống, không bao giờ lên
                            if new_stop_loss < current_position['stop_loss']:
                                current_position['stop_loss'] = new_stop_loss
                                logger.info(f"Cập nhật trailing stop tại {current_date}: {new_stop_loss:.2f}")
                
                # Kiểm tra hit stop loss
                if current_price >= current_position['stop_loss']:
                    # Đóng vị thế - STOP LOSS
                    pnl = (current_position['entry_price'] - current_position['stop_loss']) * current_position['quantity'] * leverage
                    balance += pnl
                    
                    close_details = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_position['stop_loss'],
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': 'stop_loss',
                        'leverage': leverage
                    }
                    
                    trades.append(close_details)
                    logger.info(f"STOP LOSS (SELL) tại {current_date}: {current_position['stop_loss']:.2f}, PnL: {pnl:.2f}")
                    
                    current_position = None
                    
                # Kiểm tra hit take profit
                elif current_price <= current_position['take_profit'] and not current_position.get('trailing_active', False):
                    # Đóng vị thế - TAKE PROFIT
                    pnl = (current_position['entry_price'] - current_position['take_profit']) * current_position['quantity'] * leverage
                    balance += pnl
                    
                    close_details = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_position['take_profit'],
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': 'take_profit',
                        'leverage': leverage
                    }
                    
                    trades.append(close_details)
                    logger.info(f"TAKE PROFIT (SELL) tại {current_date}: {current_position['take_profit']:.2f}, PnL: {pnl:.2f}")
                    
                    current_position = None
                
                # Kiểm tra tín hiệu đảo chiều mạnh
                elif signal['action'] == 'BUY' and signal['confidence'] >= 0.8:
                    # Đóng vị thế - TÍN HIỆU
                    pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
                    balance += pnl
                    
                    close_details = {
                        'entry_date': current_position['entry_date'],
                        'entry_price': current_position['entry_price'],
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'side': current_position['side'],
                        'quantity': current_position['quantity'],
                        'pnl': pnl,
                        'roi': pnl / initial_balance * 100,
                        'exit_reason': 'signal_reverse',
                        'leverage': leverage
                    }
                    
                    trades.append(close_details)
                    logger.info(f"TÍN HIỆU ĐẢO CHIỀU (SELL->BUY) tại {current_date}: {current_price:.2f}, PnL: {pnl:.2f}")
                    
                    current_position = None
        
        # Mở vị thế mới nếu không có vị thế hiện tại và tín hiệu đủ mạnh
        if current_position is None and signal['confidence'] >= 0.7:
            if signal['action'] == 'BUY':
                # Tính toán kích thước vị thế
                risk_amount = balance * (risk_pct / 100)
                
                # Giả định tỷ lệ stop loss
                stop_loss_price = current_price * (1 - stop_loss_pct / 100)
                take_profit_price = current_price * (1 + take_profit_pct / 100)
                
                # Tính số lượng dựa trên rủi ro
                price_delta = current_price - stop_loss_price
                quantity = risk_amount / (price_delta * leverage)
                
                # Mở vị thế long
                current_position = {
                    'side': 'BUY',
                    'entry_price': current_price,
                    'entry_date': current_date,
                    'quantity': quantity,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'highest_price': current_price,
                    'lowest_price': current_price,
                    'trailing_active': False
                }
                
                logger.info(f"MỞ VỊ THẾ BUY tại {current_date}: {current_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}")
                
            elif signal['action'] == 'SELL':
                # Tính toán kích thước vị thế
                risk_amount = balance * (risk_pct / 100)
                
                # Giả định tỷ lệ stop loss
                stop_loss_price = current_price * (1 + stop_loss_pct / 100)
                take_profit_price = current_price * (1 - take_profit_pct / 100)
                
                # Tính số lượng dựa trên rủi ro
                price_delta = stop_loss_price - current_price
                quantity = risk_amount / (price_delta * leverage)
                
                # Mở vị thế short
                current_position = {
                    'side': 'SELL',
                    'entry_price': current_price,
                    'entry_date': current_date,
                    'quantity': quantity,
                    'stop_loss': stop_loss_price,
                    'take_profit': take_profit_price,
                    'highest_price': current_price,
                    'lowest_price': current_price,
                    'trailing_active': False
                }
                
                logger.info(f"MỞ VỊ THẾ SELL tại {current_date}: {current_price:.2f}, SL: {stop_loss_price:.2f}, TP: {take_profit_price:.2f}")
        
        # Tính giá trị danh mục hiện tại
        current_equity = balance
        if current_position:
            # Tính lợi nhuận chưa thực hiện
            if current_position['side'] == 'BUY':
                unrealized_pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
            else:  # SELL
                unrealized_pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
                
            current_equity = balance + unrealized_pnl
            
        # Lưu giá trị danh mục
        equity_history.append(current_equity)
        dates.append(current_date)
        portfolio_values.append((current_date, current_equity))
    
    # Đóng vị thế cuối cùng nếu còn
    if current_position:
        current_price = df['close'].iloc[-1]
        current_date = df.index[-1]
        
        # Tính PnL
        if current_position['side'] == 'BUY':
            pnl = (current_price - current_position['entry_price']) * current_position['quantity'] * leverage
        else:  # SELL
            pnl = (current_position['entry_price'] - current_price) * current_position['quantity'] * leverage
            
        balance += pnl
        
        close_details = {
            'entry_date': current_position['entry_date'],
            'entry_price': current_position['entry_price'],
            'exit_date': current_date,
            'exit_price': current_price,
            'side': current_position['side'],
            'quantity': current_position['quantity'],
            'pnl': pnl,
            'roi': pnl / initial_balance * 100,
            'exit_reason': 'end_of_test',
            'leverage': leverage
        }
        
        trades.append(close_details)
        logger.info(f"ĐÓNG VỊ THẾ CUỐI CÙNG ({current_position['side']}) tại {current_date}: {current_price:.2f}, PnL: {pnl:.2f}")
    
    # Cập nhật kết quả
    results['trades'] = trades
    results['balance'] = balance
    
    # Tính toán các chỉ số hiệu suất
    if trades:
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t['pnl'] > 0)
        losing_trades = total_trades - profitable_trades
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
        total_loss = sum(t['pnl'] for t in trades if t['pnl'] <= 0)
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
            ret = (equity_history[i] - equity_history[i-1]) / equity_history[i-1]
            returns.append(ret)
            
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if returns else 1e-9
        
        # Ước tính số lần giao dịch trong năm
        annual_factor = 365 / ((df.index[-1] - df.index[0]).days) if (df.index[-1] - df.index[0]).days > 0 else 1
        sharpe_ratio = (avg_return / std_return) * np.sqrt(len(returns) * annual_factor) if std_return > 0 else 0
        
        # ROI tổng thể
        total_roi = (balance - initial_balance) / initial_balance * 100
        
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
            'final_balance': balance
        }
        
        # In kết quả tóm tắt
        logger.info(f"=== KẾT QUẢ BACKTEST {symbol} {interval} ({strategy.name}) ===")
        logger.info(f"Tổng số giao dịch: {total_trades}")
        logger.info(f"Tỷ lệ thắng: {win_rate:.2%}")
        logger.info(f"Hệ số lợi nhuận: {profit_factor:.2f}")
        logger.info(f"Lợi nhuận trung bình: {avg_profit:.2f}")
        logger.info(f"Thua lỗ trung bình: {avg_loss:.2f}")
        logger.info(f"Drawdown tối đa: {max_drawdown:.2f}%")
        logger.info(f"Sharpe ratio: {sharpe_ratio:.2f}")
        logger.info(f"ROI: {total_roi:.2f}%")
        logger.info(f"Số dư cuối: {balance:.2f}")
        
        # Tạo chart
        filename = create_equity_chart(symbol, interval, strategy.name, dates, equity_history, trades)
        results['chart_file'] = filename
        
        # Lưu kết quả
        results_file = save_backtest_results(results, symbol, interval, strategy.name)
        results['results_file'] = results_file
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
            'final_balance': balance
        }
    
    return results

def create_equity_chart(symbol: str, interval: str, strategy_name: str, 
                       dates: List, equity_history: List,
                       trades: List[Dict]) -> str:
    """
    Tạo biểu đồ đường equity với các điểm giao dịch
    
    Args:
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        strategy_name (str): Tên chiến lược
        dates (List): Danh sách ngày
        equity_history (List): Lịch sử giá trị danh mục
        trades (List[Dict]): Danh sách giao dịch
        
    Returns:
        str: Đường dẫn file biểu đồ
    """
    try:
        # Tạo thư mục backtest_charts nếu chưa có
        os.makedirs('backtest_charts', exist_ok=True)
        
        # Tên file
        filename = f"backtest_charts/{symbol}_{interval}_{strategy_name.replace(' ', '_')}_equity.png"
        
        # Tạo biểu đồ
        plt.figure(figsize=(12, 6))
        
        # Vẽ đường equity
        plt.plot(dates, equity_history, label='Portfolio Value', color='blue')
        
        # Đánh dấu các điểm giao dịch
        for trade in trades:
            # Tìm chỉ số cho ngày vào lệnh và thoát lệnh
            try:
                entry_idx = dates.index(trade['entry_date'])
                exit_idx = dates.index(trade['exit_date'])
                
                entry_value = equity_history[entry_idx]
                exit_value = equity_history[exit_idx]
                
                # Màu cho điểm thoát lệnh dựa trên lợi nhuận
                exit_color = 'green' if trade['pnl'] > 0 else 'red'
                
                # Vẽ điểm entry
                plt.scatter(trade['entry_date'], entry_value, color='orange', marker='^', s=100)
                
                # Vẽ điểm exit
                plt.scatter(trade['exit_date'], exit_value, color=exit_color, marker='v', s=100)
                
                # Vẽ đường nối entry và exit
                plt.plot([trade['entry_date'], trade['exit_date']], [entry_value, exit_value], 
                         color=exit_color, linestyle='--', alpha=0.5)
            except (ValueError, IndexError) as e:
                logger.warning(f"Không thể vẽ giao dịch: {e}")
                continue
        
        # Chú thích và tiêu đề
        plt.title(f'{symbol} {interval} - {strategy_name} Backtest Results')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.grid(True, alpha=0.3)
        
        # Định dạng trục x
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Lưu và đóng biểu đồ
        plt.savefig(filename)
        plt.close()
        
        logger.info(f"Đã tạo biểu đồ equity: {filename}")
        return filename
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ: {e}")
        return ""

def save_backtest_results(results: Dict, symbol: str, interval: str, strategy_name: str) -> str:
    """
    Lưu kết quả backtest vào file
    
    Args:
        results (Dict): Kết quả backtest
        symbol (str): Cặp giao dịch
        interval (str): Khung thời gian
        strategy_name (str): Tên chiến lược
        
    Returns:
        str: Đường dẫn file kết quả
    """
    try:
        # Tạo thư mục backtest_results nếu chưa có
        os.makedirs('backtest_results', exist_ok=True)
        
        # Tên file
        filename = f"backtest_results/{symbol}_{interval}_{strategy_name.replace(' ', '_')}_results.json"
        
        # Xử lý datetime trước khi lưu JSON
        serializable_results = results.copy()
        
        for trade in serializable_results['trades']:
            if isinstance(trade['entry_date'], (datetime, pd.Timestamp)):
                trade['entry_date'] = trade['entry_date'].strftime('%Y-%m-%d %H:%M:%S')
            if isinstance(trade['exit_date'], (datetime, pd.Timestamp)):
                trade['exit_date'] = trade['exit_date'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Lưu file JSON
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=4)
            
        logger.info(f"Đã lưu kết quả backtest: {filename}")
        
        # Lưu file CSV với chi tiết giao dịch
        if results['trades']:
            trade_file = f"backtest_results/{symbol}_{interval}_{strategy_name.replace(' ', '_')}_trades.csv"
            trades_df = pd.DataFrame(results['trades'])
            trades_df.to_csv(trade_file, index=False)
            logger.info(f"Đã lưu chi tiết giao dịch: {trade_file}")
            
        return filename
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả backtest: {e}")
        return ""

def generate_summary_report(results: List[Dict]) -> str:
    """
    Tạo báo cáo tổng hợp HTML từ kết quả backtest
    
    Args:
        results (List[Dict]): Danh sách kết quả backtest
        
    Returns:
        str: Đường dẫn file báo cáo
    """
    try:
        # Tạo thư mục backtest_summary
        os.makedirs('backtest_summary', exist_ok=True)
        
        # Tên file báo cáo
        report_file = f"backtest_summary/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Tạo bảng tóm tắt
        summary_rows = ""
        
        # Sắp xếp kết quả theo ROI giảm dần
        sorted_results = sorted(results, key=lambda x: x['metrics']['total_roi'], reverse=True)
        
        for result in sorted_results:
            metrics = result['metrics']
            
            # Định dạng Class cho ROI
            roi_class = "positive" if metrics['total_roi'] > 0 else "negative"
            
            # Tạo hàng HTML
            row = f"""
            <tr>
                <td>{result['symbol']}</td>
                <td>{result['interval']}</td>
                <td>{result['strategy']}</td>
                <td>{metrics['total_trades']}</td>
                <td>{metrics['win_rate']:.2%}</td>
                <td>{metrics['profit_factor']:.2f}</td>
                <td>{metrics['avg_profit']:.2f}</td>
                <td>{metrics['avg_loss']:.2f}</td>
                <td>{metrics['max_drawdown']:.2f}%</td>
                <td>{metrics['sharpe_ratio']:.2f}</td>
                <td class="{roi_class}">{metrics['total_roi']:.2f}%</td>
                <td>${metrics['final_balance']:.2f}</td>
            </tr>
            """
            
            summary_rows += row
        
        # Tạo phần biểu đồ
        chart_sections = ""
        
        for result in sorted_results:
            if 'chart_file' in result and result['chart_file']:
                chart_section = f"""
                <div class="chart-container">
                    <h3>{result['symbol']} {result['interval']} - {result['strategy']}</h3>
                    <img src="../{result['chart_file']}" alt="{result['symbol']} equity chart" class="chart-img">
                    <div class="chart-metrics">
                        <p>ROI: <span class="{'positive' if result['metrics']['total_roi'] > 0 else 'negative'}">{result['metrics']['total_roi']:.2f}%</span></p>
                        <p>Tỷ lệ thắng: {result['metrics']['win_rate']:.2%}</p>
                        <p>Số giao dịch: {result['metrics']['total_trades']}</p>
                    </div>
                </div>
                """
                
                chart_sections += chart_section
        
        # Tạo nội dung HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Backtest Results Report</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 20px;
                    background-color: #f4f4f4;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #0066cc;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px 15px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #0066cc;
                    color: white;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .positive {{
                    color: green;
                    font-weight: bold;
                }}
                .negative {{
                    color: red;
                    font-weight: bold;
                }}
                .charts-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
                    gap: 20px;
                    margin-top: 30px;
                }}
                .chart-container {{
                    background: white;
                    border-radius: 5px;
                    padding: 15px;
                    box-shadow: 0 0 5px rgba(0,0,0,0.1);
                }}
                .chart-img {{
                    width: 100%;
                    height: auto;
                    border: 1px solid #ddd;
                }}
                .chart-metrics {{
                    margin-top: 10px;
                    display: flex;
                    justify-content: space-between;
                }}
                .chart-metrics p {{
                    margin: 5px 0;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .date {{
                    color: #666;
                    font-style: italic;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Backtest Results Report</h1>
                    <p class="date">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h2>Summary</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Interval</th>
                            <th>Strategy</th>
                            <th>Trades</th>
                            <th>Win Rate</th>
                            <th>Profit Factor</th>
                            <th>Avg Profit</th>
                            <th>Avg Loss</th>
                            <th>Max DD</th>
                            <th>Sharpe</th>
                            <th>ROI</th>
                            <th>Final Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        {summary_rows}
                    </tbody>
                </table>
                
                <h2>Equity Charts</h2>
                <div class="charts-grid">
                    {chart_sections}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Lưu file HTML
        with open(report_file, 'w') as f:
            f.write(html_content)
            
        logger.info(f"Đã tạo báo cáo tổng hợp: {report_file}")
        return report_file
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo tổng hợp: {e}")
        return ""

def main():
    parser = argparse.ArgumentParser(description='Script kiểm thử 6 tháng cho hệ thống giao dịch')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSDT', 'ETHUSDT'], help='Các cặp giao dịch cần kiểm thử')
    parser.add_argument('--intervals', nargs='+', default=['1h', '4h'], help='Các khung thời gian cần kiểm thử')
    parser.add_argument('--months', type=int, default=6, help='Số tháng dữ liệu lịch sử')
    parser.add_argument('--balance', type=float, default=10000.0, help='Số dư ban đầu')
    parser.add_argument('--risk', type=float, default=1.0, help='Phần trăm rủi ro trên mỗi giao dịch')
    parser.add_argument('--leverage', type=int, default=5, help='Đòn bẩy')
    parser.add_argument('--trail', action='store_true', help='Sử dụng trailing stop')
    
    args = parser.parse_args()
    
    logger.info(f"Bắt đầu backtest với tham số: {args}")
    
    all_results = []
    
    try:
        # Chạy backtest cho mỗi cặp tiền và khung thời gian
        for symbol in args.symbols:
            for interval in args.intervals:
                try:
                    # Tải dữ liệu
                    df = download_historical_data(symbol, interval, args.months)
                    
                    # Thêm chỉ báo
                    df_with_indicators = add_indicators(df)
                    
                    # Tạo các chiến lược
                    rsi_strategy = RsiStrategy(overbought=70, oversold=30)
                    macd_strategy = MacdStrategy()
                    bb_strategy = BollingerBandsStrategy()
                    
                    # Tạo chiến lược tổng hợp
                    composite = CompositeStrategy()
                    composite.add_strategy(rsi_strategy, 0.4)
                    composite.add_strategy(macd_strategy, 0.4)
                    composite.add_strategy(bb_strategy, 0.2)
                    
                    # Danh sách các chiến lược sẽ chạy backtest
                    strategies = [
                        rsi_strategy,
                        macd_strategy,
                        bb_strategy,
                        composite
                    ]
                    
                    # Chạy backtest cho mỗi chiến lược
                    for strategy in strategies:
                        try:
                            result = run_backtest(
                                df=df_with_indicators,
                                strategy=strategy,
                                symbol=symbol,
                                interval=interval,
                                initial_balance=args.balance,
                                risk_pct=args.risk,
                                leverage=args.leverage,
                                use_trailing_stop=args.trail
                            )
                            
                            all_results.append(result)
                            
                        except Exception as e:
                            logger.error(f"Lỗi khi backtest {symbol} {interval} với chiến lược {strategy.name}: {e}")
                        
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý {symbol} {interval}: {e}")
        
        # Tạo báo cáo tổng hợp
        if all_results:
            report_file = generate_summary_report(all_results)
            logger.info(f"Đã hoàn thành tất cả các backtest. Báo cáo: {report_file}")
        else:
            logger.warning("Không có kết quả backtest nào để tạo báo cáo")
            
    except Exception as e:
        logger.error(f"Lỗi chính trong quá trình backtest: {e}")

if __name__ == "__main__":
    main()