#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script backtest mở rộng cho nhiều khoảng thời gian và nhiều coins
Hỗ trợ backtest từ 1 tháng đến 6 tháng với việc đánh giá hiệu quả đầy đủ
"""

import os
import sys
import json
import logging
import argparse
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from binance_api import BinanceAPI
from adaptive_strategy_selector import AdaptiveStrategySelector
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extended_backtest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('extended_backtest')

class ExtendedMultiPeriodBacktester:
    """
    Lớp backtest mở rộng cho nhiều khoảng thời gian và nhiều coins
    """
    
    def __init__(self, period=90, risk_level='medium', mode='automatic'):
        """
        Khởi tạo backtest
        
        Args:
            period (int): Số ngày backtest (mặc định: 90 ngày - 3 tháng)
            risk_level (str): Mức độ rủi ro ('low', 'medium', 'high', 'custom')
            mode (str): Chế độ giao dịch ('automatic', 'manual', 'hybrid')
        """
        self.period = period
        self.risk_level = risk_level
        self.mode = mode
        self.api = BinanceAPI()
        
        # Mức rủi ro và đòn bẩy
        risk_configs = {
            'low': {'risk_per_trade': 2.0, 'leverage': 5},
            'medium': {'risk_per_trade': 5.0, 'leverage': 10},
            'high': {'risk_per_trade': 10.0, 'leverage': 20},
            'custom': {'risk_per_trade': 7.5, 'leverage': 15}  # Giá trị mặc định cho tùy chỉnh
        }
        
        config = risk_configs.get(risk_level, risk_configs['medium'])
        self.risk_per_trade = config['risk_per_trade']
        self.leverage = config['leverage']
        
        # Danh sách các cặp tiền cần backtest (có thể mở rộng)
        self.coins = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
            'DOGEUSDT', 'LINKUSDT', 'XRPUSDT', 'AVAXUSDT', 'DOTUSDT'
        ]
        
        # Khởi tạo thư mục kết quả
        self.results_dir = 'extended_test_results/'
        self.charts_dir = 'extended_test_charts/'
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        
        logger.info(f"Khởi tạo backtest mở rộng: {period} ngày, rủi ro: {risk_level}, chế độ: {mode}")
        logger.info(f"Cấu hình rủi ro: {self.risk_per_trade}%, đòn bẩy: {self.leverage}x")
    
    def download_historical_data(self, symbol, timeframe='1h'):
        """
        Tải dữ liệu lịch sử từ Binance
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame với dữ liệu lịch sử
        """
        try:
            logger.info(f"Đang tải dữ liệu lịch sử cho {symbol}, khung thời gian {timeframe}, {self.period} ngày")
            
            # Tính thời gian bắt đầu và kết thúc
            end_time = datetime.datetime.now()
            start_time = end_time - datetime.timedelta(days=self.period)
            
            # Convert to milliseconds timestamp
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            # Lấy dữ liệu từ API
            klines = self.api.get_historical_klines(symbol, timeframe, start_ms, end_ms)
            
            if not klines:
                logger.error(f"Không lấy được dữ liệu cho {symbol}")
                return None
            
            # Chuyển đổi dữ liệu thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                                             'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 
                                             'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume', 
                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Chuyển timestamp thành datetime index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Đã tải {len(df)} dòng dữ liệu cho {symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu lịch sử cho {symbol}: {str(e)}")
            return None
    
    def apply_technical_indicators(self, df):
        """
        Thêm các chỉ báo kỹ thuật vào DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo
        """
        try:
            # SMA
            df['sma20'] = df['close'].rolling(window=20).mean()
            df['sma50'] = df['close'].rolling(window=50).mean()
            df['sma200'] = df['close'].rolling(window=200).mean()
            
            # EMA
            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            df['bb_std'] = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
            df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Stochastic
            low_14 = df['low'].rolling(window=14).min()
            high_14 = df['high'].rolling(window=14).max()
            df['stoch_k'] = 100 * ((df['close'] - low_14) / (high_14 - low_14))
            df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
            
            # MACD
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # Volume indicators
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_change'] = df['volume'].pct_change()
            df['volume_relative'] = df['volume'] / df['volume_ma']
            
            # ADX (Average Directional Index)
            tr1 = df['high'] - df['low']
            tr2 = abs(df['high'] - df['close'].shift())
            tr3 = abs(df['low'] - df['close'].shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            df['atr'] = tr.rolling(window=14).mean()
            
            # Volatility
            df['volatility'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(20)
            
            # Đảm bảo không có giá trị NaN
            df.dropna(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi thêm chỉ báo kỹ thuật: {str(e)}")
            return df
    
    def apply_advanced_strategy(self, df, symbol):
        """
        Áp dụng chiến lược nâng cao dựa trên nhiều chỉ báo và thị trường
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá và chỉ báo
            symbol (str): Mã cặp tiền
            
        Returns:
            pd.DataFrame: DataFrame với tín hiệu giao dịch
        """
        try:
            # Tạo cột tín hiệu và stop loss/take profit
            df['trade_signal'] = 0
            df['stop_loss'] = 0.0
            df['take_profit'] = 0.0
            df['market_regime'] = 'unknown'
            
            # Phân loại thị trường
            # Trending: EMA20 > EMA50 > EMA200 hoặc EMA20 < EMA50 < EMA200 với độ dốc rõ rệt
            # Ranging: EMA20, EMA50, EMA200 gần như ngang nhau
            # Volatile: Volatility cao hơn trung bình 50%
            
            # Xác định chế độ thị trường
            df['ema20_slope'] = df['ema20'].pct_change(20)
            df['ema50_slope'] = df['ema50'].pct_change(50)
            
            # Trending up
            trending_up = (df['ema20'] > df['ema50']) & (df['ema50'] > df['ema200']) & (df['ema20_slope'] > 0.001)
            
            # Trending down
            trending_down = (df['ema20'] < df['ema50']) & (df['ema50'] < df['ema200']) & (df['ema20_slope'] < -0.001)
            
            # Ranging
            ranging = (abs(df['ema20'] - df['ema50']) / df['ema50'] < 0.01) & (abs(df['ema50'] - df['ema200']) / df['ema200'] < 0.02)
            
            # Volatile
            volatile = df['volatility'] > df['volatility'].rolling(window=50).mean() * 1.5
            
            # Gán chế độ thị trường
            df.loc[trending_up, 'market_regime'] = 'trending_up'
            df.loc[trending_down, 'market_regime'] = 'trending_down'
            df.loc[ranging & ~(trending_up | trending_down), 'market_regime'] = 'ranging'
            df.loc[volatile & ~(ranging | trending_up | trending_down), 'market_regime'] = 'volatile'
            
            # Áp dụng chiến lược dựa trên chế độ thị trường
            for i in range(1, len(df)):
                # Lấy dữ liệu hiện tại
                current = df.iloc[i]
                market_regime = current['market_regime']
                
                # Tín hiệu mặc định
                signal = 0
                stop_loss_pct = 0.02  # 2%
                take_profit_pct = 0.04  # 4%
                
                # Chiến lược cho thị trường đang trending up
                if market_regime == 'trending_up':
                    # Tín hiệu mua: Giá vượt lên trên EMA20 và RSI > 50 và MACD > Signal
                    if (current['close'] > current['ema20'] and
                        current['rsi'] > 50 and
                        current['macd'] > current['macd_signal'] and
                        current['macd_hist'] > 0):
                        signal = 1
                        stop_loss_pct = 0.03
                        take_profit_pct = 0.06
                
                # Chiến lược cho thị trường đang trending down
                elif market_regime == 'trending_down':
                    # Tín hiệu bán: Giá giảm xuống dưới EMA20 và RSI < 50 và MACD < Signal
                    if (current['close'] < current['ema20'] and
                        current['rsi'] < 50 and
                        current['macd'] < current['macd_signal'] and
                        current['macd_hist'] < 0):
                        signal = -1
                        stop_loss_pct = 0.03
                        take_profit_pct = 0.06
                
                # Chiến lược cho thị trường đang ranging
                elif market_regime == 'ranging':
                    # Tín hiệu mua: Giá chạm BB dưới và RSI < 30
                    if current['close'] < current['bb_lower'] and current['rsi'] < 30:
                        signal = 1
                        stop_loss_pct = 0.02
                        take_profit_pct = 0.04
                    
                    # Tín hiệu bán: Giá chạm BB trên và RSI > 70
                    elif current['close'] > current['bb_upper'] and current['rsi'] > 70:
                        signal = -1
                        stop_loss_pct = 0.02
                        take_profit_pct = 0.04
                
                # Chiến lược cho thị trường biến động
                elif market_regime == 'volatile':
                    # Tín hiệu mua: Đột phá trên kèm volume cao
                    if (current['close'] > current['bb_upper'] and
                        current['volume'] > current['volume_ma'] * 1.5):
                        signal = 1
                        stop_loss_pct = 0.04
                        take_profit_pct = 0.08
                    
                    # Tín hiệu bán: Đột phá dưới kèm volume cao
                    elif (current['close'] < current['bb_lower'] and
                          current['volume'] > current['volume_ma'] * 1.5):
                        signal = -1
                        stop_loss_pct = 0.04
                        take_profit_pct = 0.08
                
                # Đặt tín hiệu và stop loss/take profit
                df.at[df.index[i], 'trade_signal'] = signal
                
                if signal != 0:
                    entry_price = float(current['close'])
                    
                    if signal == 1:  # Long
                        df.at[df.index[i], 'stop_loss'] = float(entry_price * (1 - stop_loss_pct))
                        df.at[df.index[i], 'take_profit'] = float(entry_price * (1 + take_profit_pct))
                    else:  # Short
                        df.at[df.index[i], 'stop_loss'] = float(entry_price * (1 + stop_loss_pct))
                        df.at[df.index[i], 'take_profit'] = float(entry_price * (1 - take_profit_pct))
            
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng chiến lược nâng cao cho {symbol}: {str(e)}")
            return df
    
    def run_backtest(self, df, symbol):
        """
        Chạy backtest trên dữ liệu
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu đã xử lý
            symbol (str): Mã cặp tiền
            
        Returns:
            dict: Kết quả backtest
        """
        try:
            # Khởi tạo các biến
            initial_balance = 10000.0
            balance = initial_balance
            position = 0.0
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            position_start_index = 0
            market_regime = 'unknown'
            
            trades = []
            balance_history = [balance]
            equity_history = [balance]
            drawdown_history = [0.0]
            
            # Điều chỉnh thông số rủi ro
            risk_per_trade = float(self.risk_per_trade) / 100.0
            position_size_pct = risk_per_trade * float(self.leverage)
            
            # Trạng thái hiện tại
            max_balance = initial_balance
            current_equity = initial_balance
            
            # Vòng lặp qua từng nến
            for i in range(1, len(df)):
                current_price = float(df.iloc[i]['close'])
                signal = df.iloc[i]['trade_signal']
                
                # Cập nhật equity hiện tại (bao gồm cả lãi/lỗ chưa thực hiện)
                if position != 0:
                    if position > 0:  # Long
                        unrealized_pnl = position * (current_price - entry_price)
                    else:  # Short
                        unrealized_pnl = -position * (entry_price - current_price)
                    current_equity = balance + unrealized_pnl
                else:
                    current_equity = balance
                
                # Cập nhật giá trị cao nhất
                max_balance = max(max_balance, current_equity)
                
                # Tính drawdown hiện tại
                current_drawdown = (max_balance - current_equity) / max_balance * 100 if max_balance > 0 else 0
                
                # Ghi lại lịch sử
                equity_history.append(current_equity)
                drawdown_history.append(current_drawdown)
                
                # Nếu đang có vị thế
                if position != 0:
                    # Lấy chế độ thị trường hiện tại
                    current_market_regime = df.iloc[i]['market_regime']
                    
                    # Kiểm tra take profit
                    if (position > 0 and current_price >= take_profit) or (position < 0 and current_price <= take_profit):
                        if position > 0:  # Long
                            profit = position * (current_price - entry_price)
                            exit_type = "TAKE PROFIT LONG"
                        else:  # Short
                            profit = -position * (entry_price - current_price)
                            exit_type = "TAKE PROFIT SHORT"
                        
                        balance += profit
                        
                        trades.append({
                            'type': 'LONG' if position > 0 else 'SHORT',
                            'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_date': df.index[i].strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_price': float(entry_price),
                            'exit_price': float(current_price),
                            'profit_pct': float((current_price / entry_price - 1) * 100) if position > 0 else float((entry_price / current_price - 1) * 100),
                            'profit_usdt': float(profit),
                            'balance': float(balance),
                            'market_regime': market_regime,
                            'exit_reason': 'take_profit'
                        })
                        
                        logger.info(f"{exit_type} {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư: {balance:.2f} USDT")
                        position = 0
                    
                    # Kiểm tra stop loss
                    elif (position > 0 and current_price <= stop_loss) or (position < 0 and current_price >= stop_loss):
                        if position > 0:  # Long
                            loss = position * (current_price - entry_price)
                            exit_type = "STOP LOSS LONG"
                        else:  # Short
                            loss = -position * (entry_price - current_price)
                            exit_type = "STOP LOSS SHORT"
                        
                        balance += loss
                        
                        trades.append({
                            'type': 'LONG' if position > 0 else 'SHORT',
                            'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_date': df.index[i].strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_price': float(entry_price),
                            'exit_price': float(current_price),
                            'profit_pct': float((current_price / entry_price - 1) * 100) if position > 0 else float((entry_price / current_price - 1) * 100),
                            'profit_usdt': float(loss),
                            'balance': float(balance),
                            'market_regime': market_regime,
                            'exit_reason': 'stop_loss'
                        })
                        
                        logger.info(f"{exit_type} {symbol} tại {current_price}, lỗ: {loss:.2f} USDT, số dư: {balance:.2f} USDT")
                        position = 0
                    
                    # Kiểm tra tín hiệu đảo chiều nếu ở chế độ tự động
                    elif self.mode == 'automatic' and signal != 0 and ((position > 0 and signal == -1) or (position < 0 and signal == 1)):
                        if position > 0:  # Long to Short
                            profit = position * (current_price - entry_price)
                            trade_type = "LONG -> SHORT"
                        else:  # Short to Long
                            profit = -position * (entry_price - current_price)
                            trade_type = "SHORT -> LONG"
                        
                        balance += profit
                        
                        trades.append({
                            'type': 'LONG' if position > 0 else 'SHORT',
                            'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                            'exit_date': df.index[i].strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_price': float(entry_price),
                            'exit_price': float(current_price),
                            'profit_pct': float((current_price / entry_price - 1) * 100) if position > 0 else float((entry_price / current_price - 1) * 100),
                            'profit_usdt': float(profit),
                            'balance': float(balance),
                            'market_regime': market_regime,
                            'exit_reason': 'signal_reversal'
                        })
                        
                        # Mở vị thế mới theo tín hiệu đảo chiều
                        position_start_index = i
                        market_regime = current_market_regime
                        
                        if signal == 1:  # Long
                            position = balance * position_size_pct / current_price
                            entry_type = "SHORT -> LONG"
                        else:  # Short
                            position = -1 * (balance * position_size_pct / current_price)
                            entry_type = "LONG -> SHORT"
                            
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        logger.info(f"{trade_type} {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư: {balance:.2f} USDT")
                        logger.info(f"NEW {entry_type} {symbol} tại {current_price}, kích thước: {abs(position):.4f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                
                # Nếu không có vị thế và có tín hiệu mới
                elif position == 0 and signal != 0:
                    # Kiểm tra chế độ giao dịch
                    if self.mode == 'automatic' or (self.mode == 'hybrid' and np.random.random() > 0.3):  # 70% tỷ lệ tự động trong chế độ hybrid
                        position_start_index = i
                        market_regime = df.iloc[i]['market_regime']
                        
                        if signal == 1:  # Long
                            position = balance * position_size_pct / current_price
                            entry_type = "OPEN LONG"
                        else:  # Short
                            position = -1 * (balance * position_size_pct / current_price)
                            entry_type = "OPEN SHORT"
                            
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        logger.info(f"{entry_type} {symbol} tại {current_price}, kích thước: {abs(position):.4f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                
                # Ghi lại số dư
                balance_history.append(balance)
            
            # Đóng vị thế cuối cùng nếu còn
            if position != 0:
                current_price = float(df.iloc[-1]['close'])
                
                if position > 0:  # Long
                    profit = position * (current_price - entry_price)
                    exit_type = "CLOSE LONG"
                else:  # Short
                    profit = -position * (entry_price - current_price)
                    exit_type = "CLOSE SHORT"
                
                balance += profit
                
                trades.append({
                    'type': 'LONG' if position > 0 else 'SHORT',
                    'entry_date': df.index[position_start_index].strftime('%Y-%m-%d %H:%M:%S'),
                    'exit_date': df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                    'entry_price': float(entry_price),
                    'exit_price': float(current_price),
                    'profit_pct': float((current_price / entry_price - 1) * 100) if position > 0 else float((entry_price / current_price - 1) * 100),
                    'profit_usdt': float(profit),
                    'balance': float(balance),
                    'market_regime': market_regime,
                    'exit_reason': 'end_of_test'
                })
                
                logger.info(f"{exit_type} {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư cuối: {balance:.2f} USDT")
            
            # Tính toán các chỉ số hiệu suất
            final_balance = balance
            profit_loss = final_balance - initial_balance
            profit_pct = (final_balance / initial_balance - 1) * 100
            
            # Tính các chỉ số khác
            if len(trades) > 0:
                win_trades = [t for t in trades if t['profit_usdt'] > 0]
                lose_trades = [t for t in trades if t['profit_usdt'] <= 0]
                
                win_rate = len(win_trades) / len(trades) * 100 if trades else 0
                
                # Tính trung bình lợi nhuận và lỗ
                avg_profit = np.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
                avg_loss = np.mean([t['profit_pct'] for t in lose_trades]) if lose_trades else 0
                
                # Tính Profit Factor
                gross_profit = sum([t['profit_usdt'] for t in win_trades]) if win_trades else 0
                gross_loss = abs(sum([t['profit_usdt'] for t in lose_trades])) if lose_trades else 0
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                
                # Tính drawdown tối đa
                max_drawdown = max(drawdown_history) if drawdown_history else 0
                
                # Phân tích theo chế độ thị trường
                market_performance = {}
                for regime in ['trending_up', 'trending_down', 'ranging', 'volatile']:
                    regime_trades = [t for t in trades if t['market_regime'] == regime]
                    
                    if regime_trades:
                        win_regime = [t for t in regime_trades if t['profit_usdt'] > 0]
                        win_rate_regime = len(win_regime) / len(regime_trades) * 100
                        
                        market_performance[regime] = {
                            'trade_count': len(regime_trades),
                            'win_rate': win_rate_regime,
                            'avg_profit': np.mean([t['profit_pct'] for t in regime_trades]),
                            'total_profit': sum([t['profit_usdt'] for t in regime_trades])
                        }
                    else:
                        market_performance[regime] = {
                            'trade_count': 0,
                            'win_rate': 0,
                            'avg_profit': 0,
                            'total_profit': 0
                        }
                
                # Phân tích theo lý do thoát lệnh
                exit_performance = {}
                for reason in ['take_profit', 'stop_loss', 'signal_reversal', 'end_of_test']:
                    reason_trades = [t for t in trades if t.get('exit_reason') == reason]
                    
                    if reason_trades:
                        win_reason = [t for t in reason_trades if t['profit_usdt'] > 0]
                        win_rate_reason = len(win_reason) / len(reason_trades) * 100
                        
                        exit_performance[reason] = {
                            'trade_count': len(reason_trades),
                            'win_rate': win_rate_reason,
                            'avg_profit': np.mean([t['profit_pct'] for t in reason_trades]),
                            'total_profit': sum([t['profit_usdt'] for t in reason_trades])
                        }
                    else:
                        exit_performance[reason] = {
                            'trade_count': 0,
                            'win_rate': 0,
                            'avg_profit': 0,
                            'total_profit': 0
                        }
            else:
                win_rate = 0
                avg_profit = 0
                avg_loss = 0
                profit_factor = 0
                max_drawdown = 0
                market_performance = {}
                exit_performance = {}
            
            # Tạo kết quả backtest
            backtest_result = {
                'symbol': symbol,
                'period_days': self.period,
                'risk_level': self.risk_level,
                'trade_mode': self.mode,
                'initial_balance': float(initial_balance),
                'final_balance': float(final_balance),
                'profit_loss': float(profit_loss),
                'profit_pct': float(profit_pct),
                'max_drawdown': float(max_drawdown),
                'trades_count': len(trades),
                'win_count': len(win_trades) if 'win_trades' in locals() else 0,
                'lose_count': len(lose_trades) if 'lose_trades' in locals() else 0,
                'win_rate': float(win_rate),
                'avg_profit': float(avg_profit),
                'avg_loss': float(avg_loss),
                'profit_factor': float(profit_factor),
                'trades': trades,
                'balance_history': balance_history,
                'equity_history': equity_history,
                'drawdown_history': drawdown_history,
                'market_performance': market_performance,
                'exit_performance': exit_performance,
                'test_data': {
                    'start_date': df.index[0].strftime('%Y-%m-%d'),
                    'end_date': df.index[-1].strftime('%Y-%m-%d'),
                    'data_points': len(df)
                }
            }
            
            # Tạo biểu đồ kết quả
            self.create_result_charts(backtest_result, symbol)
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"Lỗi khi chạy backtest cho {symbol}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def create_result_charts(self, result, symbol):
        """
        Tạo biểu đồ kết quả backtest
        
        Args:
            result (dict): Kết quả backtest
            symbol (str): Mã cặp tiền
        """
        try:
            if not result:
                logger.error(f"Không thể tạo biểu đồ cho {symbol}: Không có dữ liệu kết quả")
                return
            
            # Tạo thư mục nếu chưa tồn tại
            chart_dir = os.path.join(self.charts_dir, f"{symbol}_{self.risk_level}_{self.period}days")
            os.makedirs(chart_dir, exist_ok=True)
            
            # Dữ liệu cho biểu đồ
            dates = [datetime.datetime.strptime(result['test_data']['start_date'], '%Y-%m-%d')]
            
            # Thêm ngày của các giao dịch
            for trade in result['trades']:
                dates.append(datetime.datetime.strptime(trade['entry_date'].split(' ')[0], '%Y-%m-%d'))
                dates.append(datetime.datetime.strptime(trade['exit_date'].split(' ')[0], '%Y-%m-%d'))
            
            # Thêm ngày cuối
            dates.append(datetime.datetime.strptime(result['test_data']['end_date'], '%Y-%m-%d'))
            
            # Loại bỏ trùng lặp và sắp xếp
            dates = sorted(list(set(dates)))
            
            # 1. Biểu đồ Balance và Equity
            plt.figure(figsize=(12, 6))
            plt.plot(result['balance_history'], label='Balance')
            plt.plot(result['equity_history'], label='Equity')
            plt.title(f'Balance và Equity - {symbol} ({self.period} ngày, {self.risk_level})')
            plt.xlabel('Candles')
            plt.ylabel('USDT')
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(chart_dir, 'balance_equity.png'))
            plt.close()
            
            # 2. Biểu đồ Drawdown
            plt.figure(figsize=(12, 6))
            plt.fill_between(range(len(result['drawdown_history'])), result['drawdown_history'], color='red', alpha=0.3)
            plt.plot(result['drawdown_history'], color='red', label='Drawdown')
            plt.title(f'Drawdown - {symbol} ({self.period} ngày, {self.risk_level})')
            plt.xlabel('Candles')
            plt.ylabel('Drawdown (%)')
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(chart_dir, 'drawdown.png'))
            plt.close()
            
            # 3. Biểu đồ phân phối lợi nhuận
            if result['trades']:
                profits = [trade['profit_pct'] for trade in result['trades']]
                
                plt.figure(figsize=(12, 6))
                plt.hist(profits, bins=20, alpha=0.7, color='green')
                plt.axvline(x=0, color='red', linestyle='--')
                plt.title(f'Phân phối lợi nhuận - {symbol} ({self.period} ngày, {self.risk_level})')
                plt.xlabel('Lợi nhuận (%)')
                plt.ylabel('Số lượng giao dịch')
                plt.grid(True)
                plt.savefig(os.path.join(chart_dir, 'profit_distribution.png'))
                plt.close()
            
            logger.info(f"Đã tạo biểu đồ kết quả cho {symbol} tại {chart_dir}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ kết quả cho {symbol}: {str(e)}")
    
    def backtest_coin(self, symbol):
        """
        Thực hiện backtest cho một coin cụ thể
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            dict: Kết quả backtest
        """
        try:
            # Tải dữ liệu
            df = self.download_historical_data(symbol)
            
            if df is None or len(df) == 0:
                logger.error(f"Không có dữ liệu cho {symbol}")
                return None
            
            # Thêm chỉ báo kỹ thuật
            df = self.apply_technical_indicators(df)
            
            # Áp dụng chiến lược
            df = self.apply_advanced_strategy(df, symbol)
            
            # Chạy backtest
            backtest_result = self.run_backtest(df, symbol)
            
            if backtest_result:
                # Tạo báo cáo văn bản
                text_report = f"Báo cáo backtest cho {symbol} - {self.period} ngày, {self.risk_level} risk\n"
                text_report += "=" * 80 + "\n"
                text_report += f"Ngày bắt đầu: {backtest_result['test_data']['start_date']}\n"
                text_report += f"Ngày kết thúc: {backtest_result['test_data']['end_date']}\n"
                text_report += f"Số điểm dữ liệu: {backtest_result['test_data']['data_points']}\n"
                text_report += "=" * 80 + "\n"
                text_report += f"Số dư ban đầu: {backtest_result['initial_balance']:.2f} USDT\n"
                text_report += f"Số dư cuối: {backtest_result['final_balance']:.2f} USDT\n"
                text_report += f"Lợi nhuận: {backtest_result['profit_loss']:.2f} USDT ({backtest_result['profit_pct']:.2f}%)\n"
                text_report += f"Drawdown tối đa: {backtest_result['max_drawdown']:.2f}%\n"
                text_report += "=" * 80 + "\n"
                text_report += f"Tổng số giao dịch: {backtest_result['trades_count']}\n"
                text_report += f"Số giao dịch thắng: {backtest_result['win_count']}\n"
                text_report += f"Số giao dịch thua: {backtest_result['lose_count']}\n"
                text_report += f"Tỷ lệ thắng: {backtest_result['win_rate']:.2f}%\n"
                text_report += f"Trung bình lãi mỗi lệnh thắng: {backtest_result['avg_profit']:.2f}%\n"
                text_report += f"Trung bình lỗ mỗi lệnh thua: {backtest_result['avg_loss']:.2f}%\n"
                text_report += f"Profit Factor: {backtest_result['profit_factor']:.2f}\n"
                text_report += "=" * 80 + "\n"
                
                # Phân tích theo chế độ thị trường
                text_report += "Phân tích theo chế độ thị trường:\n"
                for regime, perf in backtest_result['market_performance'].items():
                    text_report += f"- {regime}: {perf['trade_count']} giao dịch, Win rate: {perf['win_rate']:.2f}%, Lợi nhuận: {perf['total_profit']:.2f} USDT\n"
                
                text_report += "=" * 80 + "\n"
                
                # Phân tích theo lý do thoát lệnh
                text_report += "Phân tích theo lý do thoát lệnh:\n"
                for reason, perf in backtest_result['exit_performance'].items():
                    text_report += f"- {reason}: {perf['trade_count']} giao dịch, Win rate: {perf['win_rate']:.2f}%, Lợi nhuận: {perf['total_profit']:.2f} USDT\n"
                
                # Lưu báo cáo
                report_path = os.path.join(self.results_dir, f"{symbol}_{self.risk_level}_{self.period}days_report.txt")
                with open(report_path, 'w') as f:
                    f.write(text_report)
                
                # Lưu kết quả chi tiết dạng JSON
                result_path = os.path.join(self.results_dir, f"{symbol}_{self.risk_level}_{self.period}days_result.json")
                with open(result_path, 'w') as f:
                    json.dump(backtest_result, f, indent=4)
                
                logger.info(f"Đã lưu báo cáo backtest cho {symbol} tại {report_path}")
                
                return backtest_result
            else:
                logger.error(f"Backtest không thành công cho {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện backtest cho {symbol}: {str(e)}")
            return None
    
    def backtest_all_coins(self):
        """
        Thực hiện backtest cho tất cả các coin
        
        Returns:
            dict: Kết quả backtest tổng hợp
        """
        logger.info(f"Bắt đầu backtest cho {len(self.coins)} coins, khoảng thời gian: {self.period} ngày")
        
        results = {}
        
        # Chạy backtest tuần tự cho mỗi coin
        for symbol in self.coins:
            result = self.backtest_coin(symbol)
            if result is not None:
                results[symbol] = result
        
        # Tạo báo cáo tổng hợp
        summary = []
        for symbol, result in results.items():
            summary.append({
                'symbol': symbol,
                'profit_pct': result['profit_pct'],
                'max_drawdown': result['max_drawdown'],
                'trades_count': result['trades_count'],
                'win_rate': result['win_rate'],
                'profit_factor': result['profit_factor']
            })
        
        # Sắp xếp theo lợi nhuận
        summary.sort(key=lambda x: x['profit_pct'], reverse=True)
        
        # Lưu báo cáo tổng hợp
        summary_path = os.path.join(self.results_dir, f"summary_{self.risk_level}_{self.period}days.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=4)
        
        # Tạo báo cáo tổng hợp dạng text
        text_summary = f"Báo cáo tổng hợp backtest - {self.period} ngày, {self.risk_level} risk\n"
        text_summary += "=" * 80 + "\n"
        text_summary += f"Số lượng coin test: {len(results)}\n"
        text_summary += f"Thời gian: {self.period} ngày\n"
        text_summary += f"Chế độ: {self.mode}\n"
        text_summary += "=" * 80 + "\n"
        text_summary += "Top 5 coins hiệu quả nhất:\n"
        
        for i, coin in enumerate(summary[:5]):
            text_summary += f"{i+1}. {coin['symbol']}: {coin['profit_pct']:.2f}%, Win rate: {coin['win_rate']:.2f}%, Trades: {coin['trades_count']}\n"
        
        text_summary += "=" * 80 + "\n"
        text_summary += "Thống kê tổng thể:\n"
        
        # Tính các chỉ số trung bình
        avg_profit = np.mean([x['profit_pct'] for x in summary])
        avg_drawdown = np.mean([x['max_drawdown'] for x in summary])
        avg_win_rate = np.mean([x['win_rate'] for x in summary])
        avg_trades = np.mean([x['trades_count'] for x in summary])
        
        text_summary += f"Lợi nhuận trung bình: {avg_profit:.2f}%\n"
        text_summary += f"Drawdown trung bình: {avg_drawdown:.2f}%\n"
        text_summary += f"Tỷ lệ thắng trung bình: {avg_win_rate:.2f}%\n"
        text_summary += f"Số giao dịch trung bình: {avg_trades:.1f}\n"
        
        # Tỷ lệ coins có lợi nhuận
        profitable_coins = len([x for x in summary if x['profit_pct'] > 0])
        profit_ratio = profitable_coins / len(summary) if summary else 0
        
        text_summary += f"Tỷ lệ coins có lợi nhuận: {profit_ratio:.2%} ({profitable_coins}/{len(summary)})\n"
        
        # Lưu báo cáo tổng hợp dạng text
        text_summary_path = os.path.join(self.results_dir, f"summary_{self.risk_level}_{self.period}days.txt")
        with open(text_summary_path, 'w') as f:
            f.write(text_summary)
        
        logger.info(f"Đã hoàn thành backtest cho {len(results)}/{len(self.coins)} coins")
        logger.info(f"Báo cáo tổng hợp đã được lưu tại {text_summary_path}")
        
        return {
            'summary': summary,
            'results': results,
            'stats': {
                'coins_tested': len(results),
                'period_days': self.period,
                'risk_level': self.risk_level,
                'trade_mode': self.mode,
                'avg_profit': float(avg_profit),
                'avg_drawdown': float(avg_drawdown),
                'avg_win_rate': float(avg_win_rate),
                'avg_trades': float(avg_trades),
                'profitable_ratio': float(profit_ratio)
            }
        }
    
    def create_summary_charts(self, results):
        """
        Tạo biểu đồ tổng hợp cho tất cả các coin
        
        Args:
            results (dict): Kết quả tổng hợp
        """
        try:
            if not results or not results['summary']:
                logger.error("Không thể tạo biểu đồ tổng hợp: Không có dữ liệu kết quả")
                return
            
            # Dữ liệu cho biểu đồ
            symbols = [item['symbol'] for item in results['summary']]
            profits = [item['profit_pct'] for item in results['summary']]
            drawdowns = [item['max_drawdown'] for item in results['summary']]
            win_rates = [item['win_rate'] for item in results['summary']]
            
            # 1. Biểu đồ lợi nhuận theo coin
            plt.figure(figsize=(14, 8))
            bars = plt.bar(symbols, profits, color=['green' if x > 0 else 'red' for x in profits])
            plt.title(f'Lợi nhuận theo coin ({self.period} ngày, {self.risk_level})')
            plt.xlabel('Coin')
            plt.ylabel('Lợi nhuận (%)')
            plt.xticks(rotation=45)
            plt.grid(axis='y')
            
            # Thêm giá trị lên thanh
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom' if height > 0 else 'top',
                        rotation=0)
                        
            plt.tight_layout()
            plt.savefig(os.path.join(self.charts_dir, f'profit_by_coin_{self.risk_level}_{self.period}days.png'))
            plt.close()
            
            # 2. Biểu đồ drawdown theo coin
            plt.figure(figsize=(14, 8))
            bars = plt.bar(symbols, drawdowns, color='red')
            plt.title(f'Drawdown tối đa theo coin ({self.period} ngày, {self.risk_level})')
            plt.xlabel('Coin')
            plt.ylabel('Drawdown (%)')
            plt.xticks(rotation=45)
            plt.grid(axis='y')
            
            # Thêm giá trị lên thanh
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom',
                        rotation=0)
                        
            plt.tight_layout()
            plt.savefig(os.path.join(self.charts_dir, f'drawdown_by_coin_{self.risk_level}_{self.period}days.png'))
            plt.close()
            
            # 3. Biểu đồ win rate theo coin
            plt.figure(figsize=(14, 8))
            bars = plt.bar(symbols, win_rates, color='blue')
            plt.title(f'Tỷ lệ thắng theo coin ({self.period} ngày, {self.risk_level})')
            plt.xlabel('Coin')
            plt.ylabel('Tỷ lệ thắng (%)')
            plt.xticks(rotation=45)
            plt.grid(axis='y')
            
            # Thêm giá trị lên thanh
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%',
                        ha='center', va='bottom',
                        rotation=0)
                        
            plt.tight_layout()
            plt.savefig(os.path.join(self.charts_dir, f'win_rate_by_coin_{self.risk_level}_{self.period}days.png'))
            plt.close()
            
            # 4. Biểu đồ tương quan giữa win rate và lợi nhuận
            plt.figure(figsize=(10, 8))
            plt.scatter(win_rates, profits, c=drawdowns, s=100, cmap='viridis', alpha=0.7)
            
            # Thêm nhãn cho mỗi điểm
            for i, symbol in enumerate(symbols):
                plt.annotate(symbol, (win_rates[i], profits[i]), 
                           xytext=(5, 5), textcoords='offset points')
            
            plt.title(f'Tương quan Win Rate - Lợi nhuận ({self.period} ngày, {self.risk_level})')
            plt.xlabel('Tỷ lệ thắng (%)')
            plt.ylabel('Lợi nhuận (%)')
            plt.grid(True)
            plt.colorbar(label='Drawdown (%)')
            
            plt.tight_layout()
            plt.savefig(os.path.join(self.charts_dir, f'win_rate_profit_correlation_{self.risk_level}_{self.period}days.png'))
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ tổng hợp tại {self.charts_dir}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ tổng hợp: {str(e)}")
    
    def run(self):
        """
        Chạy backtest cho tất cả coin và tạo báo cáo tổng hợp
        """
        # Thay đổi trạng thái để phân biệt khi backtest nhiều lần
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Tạo thư mục kết quả cho lần chạy này
        run_results_dir = os.path.join(self.results_dir, f"run_{timestamp}")
        run_charts_dir = os.path.join(self.charts_dir, f"run_{timestamp}")
        
        os.makedirs(run_results_dir, exist_ok=True)
        os.makedirs(run_charts_dir, exist_ok=True)
        
        # Cập nhật thư mục lưu kết quả
        self.results_dir = run_results_dir
        self.charts_dir = run_charts_dir
        
        # Thực hiện backtest
        results = self.backtest_all_coins()
        
        # Tạo biểu đồ tổng hợp
        self.create_summary_charts(results)
        
        # Lưu kết quả tổng hợp dạng JSON
        result_path = os.path.join(self.results_dir, f"full_results_{self.risk_level}_{self.period}days.json")
        with open(result_path, 'w') as f:
            # Loại bỏ dữ liệu lớn để file không quá lớn
            if 'results' in results:
                for symbol in results['results']:
                    if 'trades' in results['results'][symbol]:
                        results['results'][symbol]['trades_count'] = len(results['results'][symbol]['trades'])
                        results['results'][symbol]['trades'] = results['results'][symbol]['trades'][:10]  # Chỉ lưu 10 giao dịch đầu tiên
                        
                    # Loại bỏ các dữ liệu lịch sử lớn
                    for key in ['balance_history', 'equity_history', 'drawdown_history']:
                        if key in results['results'][symbol]:
                            results['results'][symbol][key] = results['results'][symbol][key][:100]  # Chỉ lưu 100 điểm đầu tiên
            
            json.dump(results, f, indent=4)
        
        logger.info(f"Đã hoàn thành backtest cho {self.period} ngày với mức rủi ro {self.risk_level}")
        logger.info(f"Kết quả chi tiết đã được lưu tại {result_path}")
        
        # In báo cáo tóm tắt
        if 'stats' in results:
            logger.info("=" * 50)
            logger.info(f"Báo cáo tóm tắt - {self.period} ngày, {self.risk_level} risk")
            logger.info("=" * 50)
            logger.info(f"Số lượng coin test: {results['stats']['coins_tested']}")
            logger.info(f"Lợi nhuận trung bình: {results['stats']['avg_profit']:.2f}%")
            logger.info(f"Drawdown trung bình: {results['stats']['avg_drawdown']:.2f}%")
            logger.info(f"Tỷ lệ thắng trung bình: {results['stats']['avg_win_rate']:.2f}%")
            logger.info(f"Tỷ lệ coins có lợi nhuận: {results['stats']['profitable_ratio']:.2%}")
            logger.info("=" * 50)
            
            # Top 3 coins
            if results['summary']:
                top_coins = sorted(results['summary'], key=lambda x: x['profit_pct'], reverse=True)[:3]
                logger.info("Top 3 coins hiệu quả nhất:")
                for i, coin in enumerate(top_coins):
                    logger.info(f"{i+1}. {coin['symbol']}: {coin['profit_pct']:.2f}%, Win rate: {coin['win_rate']:.2f}%")
        
        return results


def parse_arguments():
    """
    Phân tích tham số dòng lệnh
    
    Returns:
        argparse.Namespace: Tham số được phân tích
    """
    parser = argparse.ArgumentParser(description='Extended Multi-Period Backtester for Cryptocurrency')
    
    parser.add_argument('--period', type=int, default=90,
                        help='Số ngày backtest (mặc định: 90 ngày - 3 tháng)')
    
    parser.add_argument('--risk', type=str, default='medium', choices=['low', 'medium', 'high', 'custom'],
                        help='Mức độ rủi ro (mặc định: medium)')
    
    parser.add_argument('--mode', type=str, default='automatic', choices=['automatic', 'manual', 'hybrid'],
                        help='Chế độ giao dịch (mặc định: automatic)')
    
    parser.add_argument('--coins', type=str, nargs='+',
                        help='Danh sách các coin cần test (mặc định: sử dụng danh sách có sẵn)')
    
    return parser.parse_args()


if __name__ == "__main__":
    # Phân tích tham số dòng lệnh
    args = parse_arguments()
    
    # Khởi tạo backtest
    backtester = ExtendedMultiPeriodBacktester(
        period=args.period,
        risk_level=args.risk,
        mode=args.mode
    )
    
    # Nếu người dùng chỉ định danh sách coin
    if args.coins:
        backtester.coins = [coin.upper() + 'USDT' if not coin.endswith('USDT') else coin.upper() for coin in args.coins]
    
    # Chạy backtest
    backtester.run()