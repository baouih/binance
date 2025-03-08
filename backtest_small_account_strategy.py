#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from tabulate import tabulate
import ccxt
from binance_api import BinanceAPI
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("small_account_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("small_account_backtest")

class SmallAccountBacktester:
    def __init__(self, start_date=None, end_date=None, account_size=100, timeframe='1h'):
        """
        Khởi tạo backtester
        
        Args:
            start_date (str): Ngày bắt đầu (YYYY-MM-DD)
            end_date (str): Ngày kết thúc (YYYY-MM-DD)
            account_size (int): Kích thước tài khoản ($)
            timeframe (str): Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)
        """
        self.api = BinanceAPI(testnet=True)
        self.account_config = self.load_config('account_config.json')
        self.small_account_configs = self.account_config.get('small_account_configs', {})
        
        # Thiết lập thời gian
        self.end_date = datetime.now() if end_date is None else datetime.strptime(end_date, '%Y-%m-%d')
        if start_date is None:
            self.start_date = self.end_date - timedelta(days=90)  # Mặc định 3 tháng
        else:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        # Thiết lập tài khoản
        self.account_size = account_size
        self.timeframe = timeframe
        
        # Tải cấu hình dựa trên kích thước tài khoản
        self.config = self.small_account_configs.get(str(account_size), None)
        if self.config is None:
            # Tìm cấu hình gần nhất
            sizes = sorted([int(size) for size in self.small_account_configs.keys()])
            closest = min(sizes, key=lambda x: abs(x - account_size))
            self.config = self.small_account_configs.get(str(closest), {})
            logger.info(f"Không tìm thấy cấu hình cho tài khoản ${account_size}, sử dụng cấu hình gần nhất: ${closest}")
        
        # Thiết lập thông số
        self.leverage = self.config.get('leverage', 1)
        self.risk_percentage = self.config.get('risk_percentage', 1)
        self.max_positions = self.config.get('max_positions', 1)
        self.suitable_pairs = self.config.get('suitable_pairs', [])
        
        # Stop loss và take profit
        self.default_stop_percentage = self.config.get('default_stop_percentage', 2.0)
        self.default_take_profit_percentage = self.config.get('default_take_profit_percentage', 4.0)
        self.enable_trailing_stop = self.config.get('enable_trailing_stop', False)
        
        # Thống kê và kết quả
        self.results = {}
        self.summary = {}
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs('backtest_results', exist_ok=True)
        
        logger.info(f"Khởi tạo backtester với tài khoản ${account_size}, " 
                   f"đòn bẩy {self.leverage}x, rủi ro {self.risk_percentage}%, "
                   f"từ {self.start_date.strftime('%Y-%m-%d')} đến {self.end_date.strftime('%Y-%m-%d')}")
        
    def load_config(self, filename):
        """Tải cấu hình từ file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Không thể tải cấu hình từ {filename}: {str(e)}")
            return {}
    
    def fetch_historical_data(self, symbol, timeframe='1h', start_time=None, end_time=None, limit=1000):
        """
        Lấy dữ liệu lịch sử từ Binance
        
        Args:
            symbol (str): Symbol (BTCUSDT,...)
            timeframe (str): Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)
            start_time (int): Thời gian bắt đầu (timestamp)
            end_time (int): Thời gian kết thúc (timestamp)
            limit (int): Số lượng candlestick tối đa
            
        Returns:
            pd.DataFrame: Dữ liệu lịch sử dạng DataFrame
        """
        try:
            # Chuyển đổi thời gian thành timestamp (ms)
            if start_time is not None and isinstance(start_time, datetime):
                start_time = int(start_time.timestamp() * 1000)
            if end_time is not None and isinstance(end_time, datetime):
                end_time = int(end_time.timestamp() * 1000)
                
            # Lấy dữ liệu sử dụng ccxt
            import ccxt
            
            # Chỉ tạo mẫu dữ liệu để mô phỏng
            logger.info(f"Đang mô phỏng dữ liệu lịch sử cho {symbol} (thời gian thực sẽ lấy từ Binance API)")
            
            # Tạo khoảng thời gian
            if start_time is None:
                start_time = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)
            if end_time is None:
                end_time = int(datetime.now().timestamp() * 1000)
                
            # Tính khoảng thời gian giữa các candlestick dựa trên timeframe
            timeframe_multiplier = {
                '1m': 60, '5m': 300, '15m': 900, '30m': 1800,
                '1h': 3600, '2h': 7200, '4h': 14400, '8h': 28800, '12h': 43200,
                '1d': 86400, '3d': 259200, '1w': 604800
            }
            interval_seconds = timeframe_multiplier.get(timeframe, 3600)  # Default 1h
            
            # Tạo khoảng thời gian
            timestamps = []
            current = start_time
            while current <= end_time and len(timestamps) < limit:
                timestamps.append(current)
                current += interval_seconds * 1000  # Convert to ms
                
            # Tạo dữ liệu mẫu
            import numpy as np
            base_price = 100.0  # Giá cơ sở
            if symbol == 'BTCUSDT':
                base_price = 85000.0
            elif symbol == 'ETHUSDT':
                base_price = 2100.0
            elif symbol == 'BNBUSDT':
                base_price = 600.0
            elif symbol == 'SOLUSDT':
                base_price = 160.0
            elif symbol == 'ADAUSDT':
                base_price = 0.9
            
            klines = []
            
            for ts in timestamps:
                # Tạo số ngẫu nhiên có trọng số
                random_change = np.random.normal(0, 0.01)  # Thay đổi giá trung bình 0%, độ lệch chuẩn 1%
                close_price = base_price * (1 + random_change)
                
                # Tạo OHLC từ giá đóng cửa
                high_price = close_price * (1 + abs(np.random.normal(0, 0.005)))
                low_price = close_price * (1 - abs(np.random.normal(0, 0.005)))
                open_price = close_price * (1 + np.random.normal(0, 0.003))
                
                # Đảm bảo high >= open, close, low và low <= open, close
                high_price = max(high_price, open_price, close_price)
                low_price = min(low_price, open_price, close_price)
                
                # Tạo volume
                volume = abs(np.random.normal(1000, 500))
                
                # Tạo candlestick
                kline = [
                    ts,                        # timestamp
                    float(open_price),         # open
                    float(high_price),         # high
                    float(low_price),          # low
                    float(close_price),        # close
                    float(volume),             # volume
                    ts + interval_seconds * 1000, # close_time
                    float(volume * close_price), # quote_volume
                    100,                       # trades
                    float(volume * 0.4),       # taker_buy_volume
                    float(volume * 0.4 * close_price), # taker_buy_quote_volume
                    0                          # ignore
                ]
                klines.append(kline)
                
                # Cập nhật giá cơ sở cho candlestick tiếp theo
                base_price = close_price
            
            if not klines:
                logger.error(f"Không thể lấy dữ liệu lịch sử cho {symbol}")
                return None
                
            # Chuyển đổi thành DataFrame
            columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                      'close_time', 'quote_volume', 'trades', 'taker_buy_volume', 
                      'taker_buy_quote_volume', 'ignored']
            df = pd.DataFrame(klines, columns=columns)
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                              'quote_volume', 'trades', 'taker_buy_volume', 
                              'taker_buy_quote_volume']
            df[numeric_columns] = df[numeric_columns].astype(float)
            
            # Chuyển đổi timestamp thành datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # Đặt timestamp làm index
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử cho {symbol}: {str(e)}")
            return None
    
    def fetch_complete_historical_data(self, symbol, timeframe='1h', start_date=None, end_date=None):
        """
        Lấy toàn bộ dữ liệu lịch sử cho khoảng thời gian dài
        
        Args:
            symbol (str): Symbol (BTCUSDT,...)
            timeframe (str): Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)
            start_date (datetime): Ngày bắt đầu
            end_date (datetime): Ngày kết thúc
            
        Returns:
            pd.DataFrame: Dữ liệu lịch sử dạng DataFrame
        """
        if start_date is None:
            start_date = self.start_date
        if end_date is None:
            end_date = self.end_date
            
        # Binance có giới hạn số lượng candlesticks trả về trong một request (thường là 1000)
        # Nên cần phải chia nhỏ các request
        
        # Tính toán thời gian theo timeframe
        timeframe_multiplier = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080
        }
        minutes_per_candle = timeframe_multiplier.get(timeframe, 60)  # Default to 1h if unknown
        
        # Số candlestick tối đa trong một request
        max_candles_per_request = 1000
        
        # Tính tổng số phút trong khoảng thời gian
        total_minutes = int((end_date - start_date).total_seconds() / 60)
        
        # Tính số candlestick cần thiết
        total_candles = total_minutes / minutes_per_candle
        
        # Tính số request cần thiết
        num_requests = int(np.ceil(total_candles / max_candles_per_request))
        
        # Chia thời gian thành các phần
        if num_requests > 1:
            # Tính khoảng thời gian cho mỗi request
            mins_per_request = max_candles_per_request * minutes_per_candle
            
            # Chia thành các khoảng thời gian
            date_ranges = []
            for i in range(num_requests):
                chunk_start = start_date + timedelta(minutes=i * mins_per_request)
                chunk_end = min(start_date + timedelta(minutes=(i + 1) * mins_per_request), end_date)
                date_ranges.append((chunk_start, chunk_end))
        else:
            date_ranges = [(start_date, end_date)]
            
        # Lấy dữ liệu cho từng khoảng thời gian
        all_df = []
        for chunk_start, chunk_end in date_ranges:
            df_chunk = self.fetch_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_time=chunk_start,
                end_time=chunk_end,
                limit=max_candles_per_request
            )
            
            if df_chunk is not None and not df_chunk.empty:
                all_df.append(df_chunk)
                time.sleep(0.2)  # Tránh rate limit
            
        # Ghép các DataFrame lại
        if all_df:
            combined_df = pd.concat(all_df)
            
            # Loại bỏ các dòng trùng lặp
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
            
            # Sắp xếp theo thời gian
            combined_df.sort_index(inplace=True)
            
            return combined_df
            
        return None
    
    def calculate_indicators(self, df):
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã được tính toán
        """
        if df is None or df.empty:
            return None
            
        # Tính RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Tính Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        
        # Tính Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        
        # Tính MACD
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Xóa bỏ các dòng có giá trị NaN
        df.dropna(inplace=True)
        
        return df
    
    def generate_signals(self, df):
        """
        Tạo tín hiệu giao dịch dựa trên các chỉ báo kỹ thuật
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            pd.DataFrame: DataFrame với tín hiệu giao dịch
        """
        if df is None or df.empty:
            return None
            
        # Khởi tạo cột tín hiệu
        df['signal'] = 0
        
        # Tín hiệu dựa trên RSI
        df.loc[df['rsi'] < 30, 'signal_rsi'] = 1  # Oversold - Buy signal
        df.loc[df['rsi'] > 70, 'signal_rsi'] = -1  # Overbought - Sell signal
        
        # Tín hiệu dựa trên MA Cross
        df['sma_20_prev'] = df['sma_20'].shift(1)
        df['sma_50_prev'] = df['sma_50'].shift(1)
        
        # Golden Cross (SMA20 crosses above SMA50)
        df.loc[(df['sma_20'] > df['sma_50']) & (df['sma_20_prev'] <= df['sma_50_prev']), 'signal_ma_cross'] = 1
        
        # Death Cross (SMA20 crosses below SMA50)
        df.loc[(df['sma_20'] < df['sma_50']) & (df['sma_20_prev'] >= df['sma_50_prev']), 'signal_ma_cross'] = -1
        
        # Tín hiệu dựa trên Bollinger Bands
        df.loc[df['close'] < df['bb_lower'], 'signal_bb'] = 1  # Price below lower band - Buy signal
        df.loc[df['close'] > df['bb_upper'], 'signal_bb'] = -1  # Price above upper band - Sell signal
        
        # Tín hiệu dựa trên MACD
        df['macd_prev'] = df['macd'].shift(1)
        df['macd_signal_prev'] = df['macd_signal'].shift(1)
        
        # MACD crosses above Signal line
        df.loc[(df['macd'] > df['macd_signal']) & (df['macd_prev'] <= df['macd_signal_prev']), 'signal_macd'] = 1
        
        # MACD crosses below Signal line
        df.loc[(df['macd'] < df['macd_signal']) & (df['macd_prev'] >= df['macd_signal_prev']), 'signal_macd'] = -1
        
        # Kết hợp các tín hiệu
        # Tín hiệu mua: RSI < 30 hoặc Golden Cross hoặc giá dưới Bollinger Bands lower hoặc MACD crosses above Signal
        buy_signals = ((df['signal_rsi'] == 1) | 
                       (df['signal_ma_cross'] == 1) | 
                       (df['signal_bb'] == 1) | 
                       (df['signal_macd'] == 1))
        
        # Tín hiệu bán: RSI > 70 hoặc Death Cross hoặc giá trên Bollinger Bands upper hoặc MACD crosses below Signal
        sell_signals = ((df['signal_rsi'] == -1) | 
                        (df['signal_ma_cross'] == -1) | 
                        (df['signal_bb'] == -1) | 
                        (df['signal_macd'] == -1))
        
        # Gán giá trị tín hiệu
        df.loc[buy_signals, 'signal'] = 1
        df.loc[sell_signals, 'signal'] = -1
        
        # Thêm cột dự đoán cho backtesting
        df['position'] = 0
        
        # Chiến lược: Mua khi có tín hiệu mua, giữ cho đến khi có tín hiệu bán
        position = 0
        for i in range(1, len(df)):
            # Chiến lược 1: Theo tín hiệu mua/bán
            if df['signal'].iloc[i] == 1 and position == 0:  # Tín hiệu mua và không có vị thế
                position = 1
            elif df['signal'].iloc[i] == -1 and position == 1:  # Tín hiệu bán và đang giữ vị thế
                position = 0
                
            df.loc[df.index[i], 'position'] = position
            
        return df
    
    def backtest_strategy(self, df, initial_balance=100, stop_loss_pct=None, take_profit_pct=None, leverage=None):
        """
        Thực hiện backtest chiến lược giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame với tín hiệu giao dịch
            initial_balance (float): Số dư ban đầu
            stop_loss_pct (float): Phần trăm stop loss
            take_profit_pct (float): Phần trăm take profit
            leverage (float): Đòn bẩy
            
        Returns:
            tuple: (balance_history, trades, statistics)
        """
        if df is None or df.empty:
            return None, None, None
            
        # Thiết lập thông số
        balance = initial_balance
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        
        if stop_loss_pct is None:
            stop_loss_pct = self.default_stop_percentage
        if take_profit_pct is None:
            take_profit_pct = self.default_take_profit_percentage
        if leverage is None:
            leverage = self.leverage
            
        # Khởi tạo danh sách lịch sử số dư và các giao dịch
        balance_history = []
        trades = []
        
        # Lưu lại số dư ban đầu vào lịch sử
        balance_history.append({
            'timestamp': df.index[0],
            'balance': balance,
            'position': position,
            'price': df['close'].iloc[0]
        })
        
        for i in range(1, len(df)):
            current_date = df.index[i]
            current_price = df['close'].iloc[i]
            
            # Nếu đang giữ vị thế, kiểm tra stop loss và take profit
            if position != 0:
                # Tính P&L theo %
                if position == 1:  # Long position
                    pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
                else:  # Short position
                    pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage
                
                # Kiểm tra stop loss
                if (position == 1 and current_price <= stop_loss) or (position == -1 and current_price >= stop_loss):
                    # Tính toán số dư mới dựa trên stop loss
                    balance = balance * (1 - stop_loss_pct * leverage / 100)
                    
                    # Ghi lại giao dịch
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'position': 'LONG' if position == 1 else 'SHORT',
                        'pnl_pct': -stop_loss_pct * leverage,
                        'pnl': balance - prev_balance,
                        'exit_reason': 'STOP_LOSS'
                    })
                    
                    # Reset vị thế
                    position = 0
                    
                # Kiểm tra take profit
                elif (position == 1 and current_price >= take_profit) or (position == -1 and current_price <= take_profit):
                    # Tính toán số dư mới dựa trên take profit
                    balance = balance * (1 + take_profit_pct * leverage / 100)
                    
                    # Ghi lại giao dịch
                    trades.append({
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_date': current_date,
                        'exit_price': current_price,
                        'position': 'LONG' if position == 1 else 'SHORT',
                        'pnl_pct': take_profit_pct * leverage,
                        'pnl': balance - prev_balance,
                        'exit_reason': 'TAKE_PROFIT'
                    })
                    
                    # Reset vị thế
                    position = 0
            
            # Kiểm tra tín hiệu mới
            signal = df['signal'].iloc[i]
            prev_position = position
            
            if signal == 1 and position == 0:  # Tín hiệu mua và không có vị thế
                position = 1
                entry_price = current_price
                entry_date = current_date
                prev_balance = balance
                
                # Thiết lập stop loss và take profit
                stop_loss = entry_price * (1 - stop_loss_pct / 100)
                take_profit = entry_price * (1 + take_profit_pct / 100)
                
            elif signal == -1 and position == 1:  # Tín hiệu bán và đang giữ vị thế long
                # Tính P&L
                pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
                balance = balance * (1 + pnl_pct / 100)
                
                # Ghi lại giao dịch
                trades.append({
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': current_date,
                    'exit_price': current_price,
                    'position': 'LONG',
                    'pnl_pct': pnl_pct,
                    'pnl': balance - prev_balance,
                    'exit_reason': 'SIGNAL'
                })
                
                # Reset vị thế
                position = 0
                
            # Lưu lại số dư vào lịch sử
            balance_history.append({
                'timestamp': current_date,
                'balance': balance,
                'position': position,
                'price': current_price
            })
            
        # Đóng vị thế cuối cùng nếu còn
        if position != 0:
            current_date = df.index[-1]
            current_price = df['close'].iloc[-1]
            
            # Tính P&L
            if position == 1:  # Long position
                pnl_pct = (current_price - entry_price) / entry_price * 100 * leverage
            else:  # Short position
                pnl_pct = (entry_price - current_price) / entry_price * 100 * leverage
                
            balance = balance * (1 + pnl_pct / 100)
            
            # Ghi lại giao dịch
            trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_date': current_date,
                'exit_price': current_price,
                'position': 'LONG' if position == 1 else 'SHORT',
                'pnl_pct': pnl_pct,
                'pnl': balance - prev_balance,
                'exit_reason': 'END_OF_PERIOD'
            })
        
        # Tính toán thống kê
        if trades:
            df_trades = pd.DataFrame(trades)
            
            # Tính tổng số giao dịch
            total_trades = len(trades)
            
            # Tính số giao dịch lãi và lỗ
            winning_trades = df_trades[df_trades['pnl'] > 0]
            losing_trades = df_trades[df_trades['pnl'] < 0]
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            
            # Tính tỷ lệ thắng
            win_rate = win_count / total_trades if total_trades > 0 else 0
            
            # Tính lợi nhuận trung bình và lỗ trung bình
            avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
            avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0
            
            # Tính Risk-Reward Ratio
            risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
            
            # Tính profit factor
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if not losing_trades.empty and losing_trades['pnl'].sum() != 0 else float('inf')
            
            # Tính lợi nhuận cuối cùng
            final_balance = balance
            net_profit = final_balance - initial_balance
            net_profit_pct = (net_profit / initial_balance) * 100
            
            # Tính thời gian trung bình giữ vị thế
            df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
            df_trades['exit_date'] = pd.to_datetime(df_trades['exit_date'])
            df_trades['holding_period'] = (df_trades['exit_date'] - df_trades['entry_date']).dt.total_seconds() / 3600  # in hours
            avg_holding_time = df_trades['holding_period'].mean()
            
            # Tính drawdown
            df_balance = pd.DataFrame(balance_history)
            df_balance['drawdown'] = df_balance['balance'].cummax() - df_balance['balance']
            df_balance['drawdown_pct'] = df_balance['drawdown'] / df_balance['balance'].cummax() * 100
            max_drawdown = df_balance['drawdown'].max()
            max_drawdown_pct = df_balance['drawdown_pct'].max()
            
            # Tính Sharpe Ratio (giả định risk-free rate = 0)
            if len(balance_history) > 1:
                df_balance['return'] = df_balance['balance'].pct_change()
                sharpe_ratio = df_balance['return'].mean() / df_balance['return'].std() * np.sqrt(365)  # Giả định dữ liệu ngày
            else:
                sharpe_ratio = 0
                
            # Tạo đối tượng thống kê
            statistics = {
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'net_profit': net_profit,
                'net_profit_pct': net_profit_pct,
                'total_trades': total_trades,
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'risk_reward_ratio': risk_reward_ratio,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio,
                'avg_holding_time': avg_holding_time
            }
        else:
            statistics = {
                'initial_balance': initial_balance,
                'final_balance': balance,
                'net_profit': balance - initial_balance,
                'net_profit_pct': (balance - initial_balance) / initial_balance * 100,
                'total_trades': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'risk_reward_ratio': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'avg_holding_time': 0
            }
            
        return balance_history, trades, statistics
    
    def backtest_symbol(self, symbol):
        """
        Thực hiện backtest cho một symbol
        
        Args:
            symbol (str): Symbol (BTCUSDT,...)
            
        Returns:
            dict: Kết quả backtest
        """
        logger.info(f"Đang thực hiện backtest cho {symbol}...")
        
        try:
            # Lấy dữ liệu lịch sử
            df = self.fetch_complete_historical_data(
                symbol=symbol,
                timeframe=self.timeframe,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            if df is None or df.empty:
                logger.error(f"Không thể lấy dữ liệu lịch sử cho {symbol}")
                return None
                
            # Tính toán chỉ báo
            df = self.calculate_indicators(df)
            
            # Tạo tín hiệu
            df = self.generate_signals(df)
            
            # Thực hiện backtest
            balance_history, trades, statistics = self.backtest_strategy(
                df=df,
                initial_balance=self.account_size,
                stop_loss_pct=self.default_stop_percentage,
                take_profit_pct=self.default_take_profit_percentage,
                leverage=self.leverage
            )
            
            if statistics is None:
                logger.error(f"Backtest không thành công cho {symbol}")
                return None
                
            # Ghi lại kết quả
            result = {
                'symbol': symbol,
                'timeframe': self.timeframe,
                'start_date': self.start_date.strftime('%Y-%m-%d'),
                'end_date': self.end_date.strftime('%Y-%m-%d'),
                'account_size': self.account_size,
                'leverage': self.leverage,
                'risk_percentage': self.risk_percentage,
                'statistics': statistics,
                'trades': trades,
                'balance_history': balance_history
            }
            
            # In thống kê
            logger.info(f"Kết quả backtest cho {symbol}:")
            logger.info(f"Số dư ban đầu: ${statistics['initial_balance']:.2f}")
            logger.info(f"Số dư cuối cùng: ${statistics['final_balance']:.2f}")
            logger.info(f"Lợi nhuận: ${statistics['net_profit']:.2f} ({statistics['net_profit_pct']:.2f}%)")
            logger.info(f"Số giao dịch: {statistics['total_trades']}")
            logger.info(f"Tỷ lệ thắng: {statistics['win_rate'] * 100:.2f}%")
            logger.info(f"Lợi nhuận trung bình: ${statistics['avg_win']:.2f}")
            logger.info(f"Lỗ trung bình: ${statistics['avg_loss']:.2f}")
            logger.info(f"Profit Factor: {statistics['profit_factor']:.2f}")
            logger.info(f"Drawdown tối đa: ${statistics['max_drawdown']:.2f} ({statistics['max_drawdown_pct']:.2f}%)")
            logger.info(f"Thời gian giữ vị thế trung bình: {statistics['avg_holding_time']:.2f} giờ")
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện backtest cho {symbol}: {str(e)}")
            return None
    
    def backtest_all_symbols(self):
        """
        Thực hiện backtest cho tất cả các symbol phù hợp
        """
        logger.info(f"Bắt đầu backtest cho {len(self.suitable_pairs)} cặp tiền...")
        
        # Sử dụng multi-threading để tăng tốc
        results = {}
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.backtest_symbol, symbol): symbol for symbol in self.suitable_pairs}
            
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        results[symbol] = result
                except Exception as e:
                    logger.error(f"Lỗi khi thực hiện backtest cho {symbol}: {str(e)}")
        
        # Lưu kết quả
        self.results = results
        
        # Tính toán thống kê tổng quan
        self.calculate_summary()
        
        # Lưu kết quả vào file
        self.save_results()
        
        # Vẽ biểu đồ
        self.plot_results()
        
        return results
    
    def calculate_summary(self):
        """
        Tính toán thống kê tổng quan từ kết quả backtest
        """
        if not self.results:
            logger.error("Không có kết quả backtest để tính toán thống kê")
            return
            
        # Tạo DataFrame từ kết quả
        stats = []
        
        for symbol, result in self.results.items():
            if result is not None and 'statistics' in result:
                stat = result['statistics'].copy()
                stat['symbol'] = symbol
                stats.append(stat)
                
        if not stats:
            logger.error("Không có thống kê để tính toán")
            return
            
        df_stats = pd.DataFrame(stats)
        
        # Tính toán thống kê tổng quan
        total_trades = df_stats['total_trades'].sum()
        total_win = df_stats['win_count'].sum()
        total_loss = df_stats['loss_count'].sum()
        
        # Tính tỷ lệ thắng tổng thể
        overall_win_rate = total_win / total_trades if total_trades > 0 else 0
        
        # Tính trung bình các chỉ số
        avg_net_profit_pct = df_stats['net_profit_pct'].mean()
        avg_max_drawdown_pct = df_stats['max_drawdown_pct'].mean()
        avg_profit_factor = df_stats['profit_factor'].mean()
        avg_risk_reward_ratio = df_stats['risk_reward_ratio'].mean()
        avg_holding_time = df_stats['avg_holding_time'].mean()
        
        # Tính tổng lợi nhuận
        if self.account_size > 0:
            initial_allocation = self.account_size / len(self.results)
            total_final_balance = sum([result['statistics']['final_balance'] if result and 'statistics' in result else 0 
                                     for result in self.results.values()])
            total_net_profit = total_final_balance - self.account_size
            total_net_profit_pct = (total_net_profit / self.account_size) * 100
        else:
            initial_allocation = 0
            total_final_balance = 0
            total_net_profit = 0
            total_net_profit_pct = 0
            
        # Tìm symbol có hiệu suất tốt nhất và tệ nhất
        best_symbol = df_stats.loc[df_stats['net_profit_pct'].idxmax()]['symbol'] if not df_stats.empty else 'N/A'
        worst_symbol = df_stats.loc[df_stats['net_profit_pct'].idxmin()]['symbol'] if not df_stats.empty else 'N/A'
        
        best_profit_pct = df_stats['net_profit_pct'].max() if not df_stats.empty else 0
        worst_profit_pct = df_stats['net_profit_pct'].min() if not df_stats.empty else 0
        
        # Tạo thống kê tổng quan
        self.summary = {
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'account_size': self.account_size,
            'leverage': self.leverage,
            'risk_percentage': self.risk_percentage,
            'total_symbols': len(self.results),
            'total_trades': total_trades,
            'total_win': total_win,
            'total_loss': total_loss,
            'overall_win_rate': overall_win_rate,
            'avg_net_profit_pct': avg_net_profit_pct,
            'avg_max_drawdown_pct': avg_max_drawdown_pct,
            'avg_profit_factor': avg_profit_factor,
            'avg_risk_reward_ratio': avg_risk_reward_ratio,
            'avg_holding_time': avg_holding_time,
            'initial_allocation': initial_allocation,
            'total_final_balance': total_final_balance,
            'total_net_profit': total_net_profit,
            'total_net_profit_pct': total_net_profit_pct,
            'best_symbol': best_symbol,
            'best_profit_pct': best_profit_pct,
            'worst_symbol': worst_symbol,
            'worst_profit_pct': worst_profit_pct
        }
        
        # In thống kê tổng quan
        logger.info("\n" + "="*80)
        logger.info("THỐNG KÊ TỔNG QUAN")
        logger.info("="*80)
        logger.info(f"Thời gian: {self.summary['start_date']} đến {self.summary['end_date']}")
        logger.info(f"Tài khoản: ${self.summary['account_size']}, Đòn bẩy: {self.summary['leverage']}x, Rủi ro: {self.summary['risk_percentage']}%")
        logger.info(f"Số cặp tiền: {self.summary['total_symbols']}")
        logger.info(f"Tổng số giao dịch: {self.summary['total_trades']}")
        logger.info(f"Tỷ lệ thắng tổng thể: {self.summary['overall_win_rate'] * 100:.2f}%")
        logger.info(f"Lợi nhuận trung bình: {self.summary['avg_net_profit_pct']:.2f}%")
        logger.info(f"Drawdown tối đa trung bình: {self.summary['avg_max_drawdown_pct']:.2f}%")
        logger.info(f"Profit Factor trung bình: {self.summary['avg_profit_factor']:.2f}")
        logger.info(f"Thời gian giữ vị thế trung bình: {self.summary['avg_holding_time']:.2f} giờ")
        logger.info(f"Tổng lợi nhuận: ${self.summary['total_net_profit']:.2f} ({self.summary['total_net_profit_pct']:.2f}%)")
        logger.info(f"Cặp tiền tốt nhất: {self.summary['best_symbol']} ({self.summary['best_profit_pct']:.2f}%)")
        logger.info(f"Cặp tiền tệ nhất: {self.summary['worst_symbol']} ({self.summary['worst_profit_pct']:.2f}%)")
        logger.info("="*80)
        
        # Tạo bảng xếp hạng các cặp tiền
        rankings = df_stats[['symbol', 'net_profit_pct', 'win_rate', 'profit_factor', 'max_drawdown_pct']]
        rankings = rankings.sort_values('net_profit_pct', ascending=False)
        
        # In bảng xếp hạng
        logger.info("\nBẢNG XẾP HẠNG CÁC CẶP TIỀN")
        logger.info(tabulate(rankings, headers=[
            'Symbol', 'Lợi nhuận (%)', 'Tỷ lệ thắng', 'Profit Factor', 'Max Drawdown (%)'
        ], tablefmt='grid', floatfmt='.2f'))
        
    def save_results(self):
        """
        Lưu kết quả backtest vào file
        """
        if not self.results:
            logger.error("Không có kết quả backtest để lưu")
            return
            
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs('backtest_results', exist_ok=True)
            
            # Tạo tên file dựa trên tham số
            filename = f"backtest_results/small_account_{self.account_size}_lev{self.leverage}x_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.json"
            
            # Tạo đối tượng JSON
            output = {
                'summary': self.summary,
                'results': {}
            }
            
            # Lưu kết quả chi tiết cho mỗi symbol
            for symbol, result in self.results.items():
                if result is not None:
                    # Chuyển datetime thành string
                    output['results'][symbol] = {
                        'symbol': result['symbol'],
                        'timeframe': result['timeframe'],
                        'start_date': result['start_date'],
                        'end_date': result['end_date'],
                        'account_size': result['account_size'],
                        'leverage': result['leverage'],
                        'risk_percentage': result['risk_percentage'],
                        'statistics': result['statistics'],
                        'trades': [
                            {
                                'entry_date': trade['entry_date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(trade['entry_date'], datetime) else trade['entry_date'],
                                'entry_price': trade['entry_price'],
                                'exit_date': trade['exit_date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(trade['exit_date'], datetime) else trade['exit_date'],
                                'exit_price': trade['exit_price'],
                                'position': trade['position'],
                                'pnl_pct': trade['pnl_pct'],
                                'pnl': trade['pnl'],
                                'exit_reason': trade['exit_reason']
                            } for trade in result['trades']
                        ],
                        'balance_history': [
                            {
                                'timestamp': hist['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(hist['timestamp'], datetime) else hist['timestamp'],
                                'balance': hist['balance'],
                                'position': hist['position'],
                                'price': hist['price']
                            } for hist in result['balance_history']
                        ]
                    }
            
            # Lưu vào file
            with open(filename, 'w') as f:
                json.dump(output, f, indent=4)
                
            logger.info(f"Đã lưu kết quả backtest vào file {filename}")
            
            # Lưu thống kê tổng quan vào file CSV
            csv_filename = f"backtest_results/small_account_{self.account_size}_lev{self.leverage}x_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.csv"
            
            # Tạo DataFrame từ kết quả
            stats = []
            
            for symbol, result in self.results.items():
                if result is not None and 'statistics' in result:
                    stat = result['statistics'].copy()
                    stat['symbol'] = symbol
                    stats.append(stat)
                    
            if stats:
                df_stats = pd.DataFrame(stats)
                
                # Sắp xếp theo lợi nhuận
                df_stats = df_stats.sort_values('net_profit_pct', ascending=False)
                
                # Lưu vào file CSV
                df_stats.to_csv(csv_filename, index=False)
                
                logger.info(f"Đã lưu thống kê tổng quan vào file {csv_filename}")
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả backtest: {str(e)}")
            
    def plot_results(self):
        """
        Vẽ biểu đồ kết quả backtest
        """
        if not self.results:
            logger.error("Không có kết quả backtest để vẽ biểu đồ")
            return
            
        try:
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs('backtest_charts', exist_ok=True)
            
            # 1. Vẽ biểu đồ lợi nhuận của từng cặp tiền
            plt.figure(figsize=(12, 8))
            
            stats = []
            for symbol, result in self.results.items():
                if result is not None and 'statistics' in result:
                    stat = result['statistics'].copy()
                    stat['symbol'] = symbol
                    stats.append(stat)
                    
            if stats:
                df_stats = pd.DataFrame(stats)
                df_stats = df_stats.sort_values('net_profit_pct', ascending=False)
                
                plt.bar(df_stats['symbol'], df_stats['net_profit_pct'])
                plt.axhline(y=0, color='r', linestyle='-')
                plt.xticks(rotation=90)
                plt.title(f'Lợi nhuận (%) theo cặp tiền - Tài khoản ${self.account_size}, Đòn bẩy {self.leverage}x')
                plt.xlabel('Cặp tiền')
                plt.ylabel('Lợi nhuận (%)')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                # Lưu biểu đồ
                profit_chart_filename = f"backtest_charts/profit_by_symbol_{self.account_size}_lev{self.leverage}x_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
                plt.savefig(profit_chart_filename)
                plt.close()
                
                logger.info(f"Đã lưu biểu đồ lợi nhuận vào file {profit_chart_filename}")
                
            # 2. Vẽ biểu đồ tỷ lệ thắng của từng cặp tiền
            plt.figure(figsize=(12, 8))
            
            if stats:
                df_stats = pd.DataFrame(stats)
                df_stats = df_stats.sort_values('win_rate', ascending=False)
                
                plt.bar(df_stats['symbol'], df_stats['win_rate'] * 100)
                plt.axhline(y=50, color='r', linestyle='--', label='50%')
                plt.xticks(rotation=90)
                plt.title(f'Tỷ lệ thắng (%) theo cặp tiền - Tài khoản ${self.account_size}, Đòn bẩy {self.leverage}x')
                plt.xlabel('Cặp tiền')
                plt.ylabel('Tỷ lệ thắng (%)')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                
                # Lưu biểu đồ
                winrate_chart_filename = f"backtest_charts/winrate_by_symbol_{self.account_size}_lev{self.leverage}x_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
                plt.savefig(winrate_chart_filename)
                plt.close()
                
                logger.info(f"Đã lưu biểu đồ tỷ lệ thắng vào file {winrate_chart_filename}")
                
            # 3. Vẽ biểu đồ số dư theo thời gian cho top 5 cặp tiền tốt nhất
            if stats:
                df_stats = pd.DataFrame(stats)
                top_symbols = df_stats.sort_values('net_profit_pct', ascending=False).head(5)['symbol'].tolist()
                
                plt.figure(figsize=(12, 8))
                
                for symbol in top_symbols:
                    result = self.results.get(symbol)
                    if result is not None and 'balance_history' in result:
                        balance_history = result['balance_history']
                        df_balance = pd.DataFrame(balance_history)
                        df_balance['timestamp'] = pd.to_datetime(df_balance['timestamp'])
                        plt.plot(df_balance['timestamp'], df_balance['balance'], label=symbol)
                
                plt.title(f'Số dư theo thời gian - Top 5 cặp tiền tốt nhất - Tài khoản ${self.account_size}, Đòn bẩy {self.leverage}x')
                plt.xlabel('Thời gian')
                plt.ylabel('Số dư ($)')
                plt.grid(True, alpha=0.3)
                plt.legend()
                plt.tight_layout()
                
                # Lưu biểu đồ
                balance_chart_filename = f"backtest_charts/balance_top5_{self.account_size}_lev{self.leverage}x_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
                plt.savefig(balance_chart_filename)
                plt.close()
                
                logger.info(f"Đã lưu biểu đồ số dư vào file {balance_chart_filename}")
                
            # 4. Vẽ biểu đồ so sánh các thông số
            if stats:
                df_stats = pd.DataFrame(stats)
                top_symbols = df_stats.sort_values('net_profit_pct', ascending=False).head(10)['symbol'].tolist()
                df_top = df_stats[df_stats['symbol'].isin(top_symbols)]
                
                # So sánh lợi nhuận và drawdown
                plt.figure(figsize=(12, 8))
                
                x = np.arange(len(df_top))
                width = 0.35
                
                plt.bar(x - width/2, df_top['net_profit_pct'], width, label='Lợi nhuận (%)')
                plt.bar(x + width/2, df_top['max_drawdown_pct'], width, label='Max Drawdown (%)')
                
                plt.axhline(y=0, color='r', linestyle='-')
                plt.xticks(x, df_top['symbol'], rotation=90)
                plt.title(f'Lợi nhuận vs Drawdown - Top 10 cặp tiền - Tài khoản ${self.account_size}, Đòn bẩy {self.leverage}x')
                plt.xlabel('Cặp tiền')
                plt.ylabel('Phần trăm (%)')
                plt.grid(True, alpha=0.3)
                plt.legend()
                plt.tight_layout()
                
                # Lưu biểu đồ
                compare_chart_filename = f"backtest_charts/profit_vs_drawdown_{self.account_size}_lev{self.leverage}x_{self.start_date.strftime('%Y%m%d')}_{self.end_date.strftime('%Y%m%d')}.png"
                plt.savefig(compare_chart_filename)
                plt.close()
                
                logger.info(f"Đã lưu biểu đồ so sánh vào file {compare_chart_filename}")
                
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biểu đồ kết quả backtest: {str(e)}")
    
    def run(self):
        """
        Chạy backtest
        """
        logger.info(f"Bắt đầu backtest cho tài khoản ${self.account_size} với đòn bẩy {self.leverage}x")
        logger.info(f"Thời gian: {self.start_date.strftime('%Y-%m-%d')} đến {self.end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Số cặp tiền: {len(self.suitable_pairs)}")
        
        # Thực hiện backtest
        self.backtest_all_symbols()
        
        logger.info(f"Hoàn thành backtest")

def parse_arguments():
    """Phân tích tham số dòng lệnh"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest chiến lược giao dịch cho tài khoản nhỏ')
    parser.add_argument('--account-size', type=int, default=100, help='Kích thước tài khoản ($)')
    parser.add_argument('--start-date', type=str, help='Ngày bắt đầu (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='Ngày kết thúc (YYYY-MM-DD)')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    backtester = SmallAccountBacktester(
        start_date=args.start_date,
        end_date=args.end_date,
        account_size=args.account_size,
        timeframe=args.timeframe
    )
    
    backtester.run()