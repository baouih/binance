#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy backtest với dữ liệu thật cho chiến lược rủi ro cao
Sử dụng dữ liệu lịch sử Binance Futures để đánh giá hiệu suất

Tác giả: AdvancedTradingBot
Ngày: 9/3/2025
"""

import os
import sys
import json
import time
import logging
import datetime
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thêm thư mục hiện tại vào sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import các module cần thiết
from binance_api import BinanceAPI
from adaptive_strategy_selector import AdaptiveStrategySelector
from adaptive_exit_strategy import AdaptiveExitStrategy
from time_optimized_strategy import TimeOptimizedStrategy
from risk_manager import RiskManager

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('high_risk_backtest.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('high_risk_backtest')

class HighRiskBacktester:
    """Lớp thực hiện backtest chiến lược rủi ro cao với dữ liệu thật"""
    
    def __init__(self):
        """Khởi tạo backtester và tải các cấu hình cần thiết"""
        self.logger = logger
        self.logger.info("Khởi tạo HighRiskBacktester")
        
        # Tải cấu hình tài khoản
        with open('account_config.json', 'r') as f:
            self.account_config = json.load(f)
        
        # Tải cấu hình chiến lược thị trường
        with open('configs/strategy_market_config.json', 'r') as f:
            self.strategy_config = json.load(f)
            
        # Khởi tạo API Binance (BinanceAPI tự động đọc account_config.json)
        self.api = BinanceAPI()
        
        # Khởi tạo Strategy Selector
        self.strategy_selector = AdaptiveStrategySelector()
        
        # Khởi tạo Exit Strategy
        self.exit_strategy = AdaptiveExitStrategy()
        
        # Khởi tạo Risk Manager
        self.risk_manager = RiskManager()
        
        # Danh sách coin để backtest
        self.symbols = self.account_config.get('symbols', [])
        
        # Thông số rủi ro
        self.risk_per_trade = self.account_config.get('risk_per_trade', 10.0)
        self.leverage = self.account_config.get('leverage', 20)
        
        # Thư mục lưu kết quả
        self.results_dir = 'backtest_results/'
        self.charts_dir = 'backtest_charts/'
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        
        # Thiết lập các thông số backtest
        self.initial_balance = 10000  # USDT
        self.backtest_days = 30  # Số ngày backtest
        self.timeframe = '1h'  # Khung thời gian
        
        self.logger.info(f"Đã khởi tạo backtester với {len(self.symbols)} cặp tiền, rủi ro: {self.risk_per_trade}%, đòn bẩy: {self.leverage}x")
    
    def download_historical_data(self, symbol, days=30, timeframe='1h'):
        """Tải dữ liệu lịch sử từ Binance API"""
        try:
            self.logger.info(f"Đang tải dữ liệu lịch sử cho {symbol}, khung thời gian {timeframe}, {days} ngày")
            
            # Tính thời gian bắt đầu và kết thúc
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            # Lấy dữ liệu từ API
            klines = self.api.get_historical_klines(
                symbol=symbol,
                interval=timeframe,
                start_time=start_time,
                end_time=end_time
            )
            
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                              'quote_asset_volume', 'taker_buy_base_asset_volume', 
                              'taker_buy_quote_asset_volume']
            
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Đặt index
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Đã tải {len(df)} dòng dữ liệu cho {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tải dữ liệu lịch sử cho {symbol}: {str(e)}")
            return None
    
    def apply_technical_indicators(self, df):
        """Thêm các chỉ báo kỹ thuật vào DataFrame"""
        try:
            # Bollinger Bands
            window = 20
            std_dev = 2
            
            df['sma'] = df['close'].rolling(window=window).mean()
            df['std'] = df['close'].rolling(window=window).std()
            df['upper_band'] = df['sma'] + (df['std'] * std_dev)
            df['lower_band'] = df['sma'] - (df['std'] * std_dev)
            df['bb_width'] = (df['upper_band'] - df['lower_band']) / df['sma']
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = df['ema12'] - df['ema26']
            df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['signal']
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['atr'] = true_range.rolling(14).mean()
            
            # Volume Change
            df['volume_change'] = df['volume'].pct_change()
            
            # Percentage Price Oscillator (PPO)
            df['ppo'] = ((df['ema12'] - df['ema26']) / df['ema26']) * 100
            
            # Remove NaN values
            df.dropna(inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi thêm chỉ báo kỹ thuật: {str(e)}")
            return df
    
    def apply_strategy(self, df, symbol):
        """Áp dụng chiến lược giao dịch vào dữ liệu"""
        try:
            # Đảm bảo các cột số có kiểu dữ liệu float
            numeric_cols = ['close', 'open', 'high', 'low', 'volume', 'rsi', 'macd', 'signal', 'upper_band', 'lower_band', 'sma', 'volume_change']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            # Tạo cột tín hiệu
            df['signal'] = 0
            df['stop_loss'] = 0.0
            df['take_profit'] = 0.0
            
            # Lấy thông số chiến lược
            strategy_params = self.strategy_config['strategy_parameters']
            
            # Bollinger Bounce Strategy
            bb_params = strategy_params['bollinger_bounce']
            rsi_overbought = float(bb_params['rsi_overbought'])
            rsi_oversold = float(bb_params['rsi_oversold'])
            
            # Điều kiện mua
            buy_condition = (
                (df['close'] < df['lower_band']) &  # Giá dưới lower band
                (df['rsi'] < rsi_oversold) &        # RSI quá bán
                (df['volume_change'] > 0.1)         # Tăng volume
            )
            
            # Điều kiện bán
            sell_condition = (
                (df['close'] > df['upper_band']) &  # Giá trên upper band
                (df['rsi'] > rsi_overbought) &      # RSI quá mua
                (df['volume_change'] > 0.1)         # Tăng volume
            )
            
            # Momentum Strategy
            mom_params = strategy_params.get('momentum_following', {'ma_fast_period': 9, 'ma_slow_period': 21})
            df['ma_fast'] = df['close'].rolling(window=mom_params['ma_fast_period']).mean()
            df['ma_slow'] = df['close'].rolling(window=mom_params['ma_slow_period']).mean()
            
            # Điều kiện theo xu hướng
            momentum_buy = (
                (df['ma_fast'] > df['ma_slow']) &   # MA nhanh cắt lên MA chậm
                (df['macd'] > df['signal']) &       # MACD cắt lên signal
                (df['close'] > df['sma'])          # Giá trên SMA
            )
            
            momentum_sell = (
                (df['ma_fast'] < df['ma_slow']) &   # MA nhanh cắt xuống MA chậm
                (df['macd'] < df['signal']) &       # MACD cắt xuống signal
                (df['close'] < df['sma'])          # Giá dưới SMA
            )
            
            # Kết hợp các tín hiệu
            df.loc[buy_condition | momentum_buy, 'signal'] = 1
            df.loc[sell_condition | momentum_sell, 'signal'] = -1
            
            # Tính stop loss và take profit
            for i in range(1, len(df)):
                if df.iloc[i]['signal'] == 1:  # Tín hiệu mua
                    entry_price = float(df.iloc[i]['close'])
                    stop_percentage = float(bb_params['stop_loss_percent']) / 100.0
                    take_percentage = float(bb_params['take_profit_percent']) / 100.0
                    
                    # Sử dụng at thay vì loc để tránh lỗi indexing
                    df.at[df.index[i], 'stop_loss'] = float(entry_price * (1.0 - stop_percentage))
                    df.at[df.index[i], 'take_profit'] = float(entry_price * (1.0 + take_percentage))
                    
                elif df.iloc[i]['signal'] == -1:  # Tín hiệu bán
                    entry_price = float(df.iloc[i]['close'])
                    stop_percentage = float(bb_params['stop_loss_percent']) / 100.0
                    take_percentage = float(bb_params['take_profit_percent']) / 100.0
                    
                    # Sử dụng at thay vì loc để tránh lỗi indexing
                    df.at[df.index[i], 'stop_loss'] = float(entry_price * (1.0 + stop_percentage))
                    df.at[df.index[i], 'take_profit'] = float(entry_price * (1.0 - take_percentage))
            
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi áp dụng chiến lược cho {symbol}: {str(e)}")
            return df
    
    def run_backtest(self, df, symbol):
        """Chạy backtest trên dữ liệu"""
        try:
            # Đảm bảo các cột số có kiểu dữ liệu float
            numeric_cols = ['close', 'open', 'high', 'low', 'volume', 'rsi', 'macd', 'signal', 'upper_band', 'lower_band', 'sma', 'volume_change', 'stop_loss', 'take_profit']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            # Khởi tạo các biến
            balance = float(self.initial_balance)
            position = 0.0
            entry_price = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            
            trades = []
            balance_history = [balance]
            
            # Điều chỉnh thông số rủi ro
            risk_per_trade = float(self.risk_per_trade) / 100.0
            position_size_pct = risk_per_trade * float(self.leverage)
            
            # Vòng lặp qua từng nến
            for i in range(1, len(df)):
                current_price = df.iloc[i]['close']
                signal = df.iloc[i]['signal']
                
                # Nếu đang có vị thế
                if position != 0:
                    # Kiểm tra take profit
                    if position > 0 and current_price >= take_profit:
                        profit = position * (current_price - entry_price)
                        balance += profit
                        
                        trades.append({
                            'type': 'LONG',
                            'entry_date': df.index[i-position],
                            'exit_date': df.index[i],
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'profit_pct': (current_price / entry_price - 1) * 100,
                            'balance': balance
                        })
                        
                        position = 0
                        self.logger.info(f"TAKE PROFIT LONG {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư: {balance:.2f} USDT")
                    
                    # Kiểm tra stop loss
                    elif position > 0 and current_price <= stop_loss:
                        loss = position * (current_price - entry_price)
                        balance += loss
                        
                        trades.append({
                            'type': 'LONG',
                            'entry_date': df.index[i-position],
                            'exit_date': df.index[i],
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'profit_pct': (current_price / entry_price - 1) * 100,
                            'balance': balance
                        })
                        
                        position = 0
                        self.logger.info(f"STOP LOSS LONG {symbol} tại {current_price}, lỗ: {loss:.2f} USDT, số dư: {balance:.2f} USDT")
                    
                    # Kiểm tra tín hiệu đảo chiều
                    elif position > 0 and signal == -1:
                        profit = position * (current_price - entry_price)
                        balance += profit
                        
                        trades.append({
                            'type': 'LONG',
                            'entry_date': df.index[i-position],
                            'exit_date': df.index[i],
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'profit_pct': (current_price / entry_price - 1) * 100,
                            'balance': balance
                        })
                        
                        # Mở vị thế mới theo tín hiệu đảo chiều
                        position = -1 * (balance * position_size_pct / current_price)
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        self.logger.info(f"LONG -> SHORT {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư: {balance:.2f} USDT")
                
                # Nếu không có vị thế
                elif position == 0:
                    if signal == 1:  # Tín hiệu mua
                        position = balance * position_size_pct / current_price
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        self.logger.info(f"OPEN LONG {symbol} tại {current_price}, kích thước: {position:.4f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                        
                    elif signal == -1:  # Tín hiệu bán
                        position = -1 * (balance * position_size_pct / current_price)
                        entry_price = current_price
                        stop_loss = df.iloc[i]['stop_loss']
                        take_profit = df.iloc[i]['take_profit']
                        
                        self.logger.info(f"OPEN SHORT {symbol} tại {current_price}, kích thước: {abs(position):.4f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")
                
                # Ghi lại số dư
                balance_history.append(balance)
            
            # Đóng vị thế cuối cùng nếu còn
            if position != 0:
                current_price = df.iloc[-1]['close']
                
                if position > 0:
                    profit = position * (current_price - entry_price)
                    balance += profit
                    
                    trades.append({
                        'type': 'LONG',
                        'entry_date': df.index[max(0, len(df)-abs(int(position)))],
                        'exit_date': df.index[-1],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'profit_pct': (current_price / entry_price - 1) * 100,
                        'balance': balance
                    })
                    
                    self.logger.info(f"CLOSE LONG {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư cuối: {balance:.2f} USDT")
                
                else:
                    profit = -position * (entry_price - current_price)
                    balance += profit
                    
                    trades.append({
                        'type': 'SHORT',
                        'entry_date': df.index[max(0, len(df)-abs(int(position)))],
                        'exit_date': df.index[-1],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'profit_pct': (entry_price / current_price - 1) * 100,
                        'balance': balance
                    })
                    
                    self.logger.info(f"CLOSE SHORT {symbol} tại {current_price}, lợi nhuận: {profit:.2f} USDT, số dư cuối: {balance:.2f} USDT")
            
            # Tính toán các chỉ số hiệu suất
            final_balance = balance
            profit_loss = final_balance - self.initial_balance
            profit_pct = (final_balance / self.initial_balance - 1) * 100
            
            # Tính drawdown
            peak = self.initial_balance
            drawdown = 0
            max_drawdown = 0
            
            for bal in balance_history:
                if bal > peak:
                    peak = bal
                
                dd = (peak - bal) / peak * 100
                drawdown = dd
                
                if dd > max_drawdown:
                    max_drawdown = dd
            
            # Tính các chỉ số khác
            if len(trades) > 0:
                win_trades = [t for t in trades if (t['type'] == 'LONG' and t['exit_price'] > t['entry_price']) or 
                             (t['type'] == 'SHORT' and t['exit_price'] < t['entry_price'])]
                
                win_rate = len(win_trades) / len(trades) * 100
                
                # Tính trung bình lợi nhuận và lỗ
                avg_profit = np.mean([t['profit_pct'] for t in win_trades]) if win_trades else 0
                
                lose_trades = [t for t in trades if t not in win_trades]
                avg_loss = np.mean([t['profit_pct'] for t in lose_trades]) if lose_trades else 0
                
                # Tính Profit Factor
                profit_factor = abs(sum([t['profit_pct'] for t in win_trades]) / 
                                  sum([t['profit_pct'] for t in lose_trades])) if sum([t['profit_pct'] for t in lose_trades]) != 0 else float('inf')
            else:
                win_rate = 0
                avg_profit = 0
                avg_loss = 0
                profit_factor = 0
            
            # Kết quả backtest
            backtest_result = {
                'symbol': symbol,
                'initial_balance': self.initial_balance,
                'final_balance': final_balance,
                'profit_loss': profit_loss,
                'profit_pct': profit_pct,
                'max_drawdown': max_drawdown,
                'trades_count': len(trades),
                'win_rate': win_rate,
                'avg_profit': avg_profit,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'risk_per_trade': self.risk_per_trade,
                'leverage': self.leverage,
                'balance_history': balance_history,
                'trades': trades
            }
            
            return backtest_result
            
        except Exception as e:
            self.logger.error(f"Lỗi khi chạy backtest cho {symbol}: {str(e)}")
            return None
    
    def plot_backtest_results(self, df, backtest_result, symbol):
        """Vẽ đồ thị kết quả backtest"""
        try:
            if backtest_result is None:
                return
                
            # Tạo figure với 3 subplot
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 18), gridspec_kw={'height_ratios': [2, 1, 1]})
            
            # Plot 1: Giá và tín hiệu
            ax1.plot(df.index, df['close'], label='Giá đóng cửa')
            ax1.plot(df.index, df['upper_band'], 'r--', alpha=0.3, label='Upper Band')
            ax1.plot(df.index, df['lower_band'], 'g--', alpha=0.3, label='Lower Band')
            ax1.plot(df.index, df['sma'], 'y-', alpha=0.5, label='SMA')
            
            # Vẽ các tín hiệu mua
            buy_signals = df[df['signal'] == 1]
            ax1.scatter(buy_signals.index, buy_signals['close'], marker='^', color='lime', s=100, label='Mua')
            
            # Vẽ các tín hiệu bán
            sell_signals = df[df['signal'] == -1]
            ax1.scatter(sell_signals.index, sell_signals['close'], marker='v', color='red', s=100, label='Bán')
            
            # Vẽ các điểm take profit và stop loss
            for trade in backtest_result['trades']:
                if trade['type'] == 'LONG':
                    color = 'green' if trade['exit_price'] > trade['entry_price'] else 'red'
                    ax1.plot([trade['entry_date'], trade['exit_date']], 
                           [trade['entry_price'], trade['exit_price']], 
                           color=color, linewidth=2, alpha=0.7)
                else:
                    color = 'green' if trade['exit_price'] < trade['entry_price'] else 'red'
                    ax1.plot([trade['entry_date'], trade['exit_date']], 
                           [trade['entry_price'], trade['exit_price']], 
                           color=color, linewidth=2, alpha=0.7)
            
            ax1.set_title(f'Backtest {symbol} - Chiến lược Rủi ro cao')
            ax1.set_ylabel('Giá')
            ax1.grid(True)
            ax1.legend()
            
            # Plot 2: RSI
            ax2.plot(df.index, df['rsi'], label='RSI')
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.3)
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.3)
            ax2.set_ylabel('RSI')
            ax2.grid(True)
            
            # Plot 3: Số dư
            balance_index = pd.date_range(start=df.index[0], periods=len(backtest_result['balance_history']), freq=df.index.to_series().diff().mode()[0])
            ax3.plot(balance_index, backtest_result['balance_history'], label='Số dư')
            ax3.set_ylabel('Số dư (USDT)')
            ax3.grid(True)
            
            plt.tight_layout()
            
            # Thêm thông tin hiệu suất
            performance_text = (
                f"Số dư ban đầu: {backtest_result['initial_balance']} USDT\n"
                f"Số dư cuối: {backtest_result['final_balance']:.2f} USDT\n"
                f"Lợi nhuận: {backtest_result['profit_loss']:.2f} USDT ({backtest_result['profit_pct']:.2f}%)\n"
                f"Drawdown tối đa: {backtest_result['max_drawdown']:.2f}%\n"
                f"Số lệnh: {backtest_result['trades_count']}\n"
                f"Tỷ lệ thắng: {backtest_result['win_rate']:.2f}%\n"
                f"Profit Factor: {backtest_result['profit_factor']:.2f}\n"
                f"Rủi ro/lệnh: {backtest_result['risk_per_trade']}%\n"
                f"Đòn bẩy: {backtest_result['leverage']}x"
            )
            
            plt.figtext(0.01, 0.01, performance_text, ha='left', fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
            
            # Lưu đồ thị
            filename = f"{self.charts_dir}{symbol}_high_risk_backtest.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Đã lưu đồ thị backtest cho {symbol} tại {filename}")
            
        except Exception as e:
            self.logger.error(f"Lỗi khi vẽ đồ thị kết quả backtest cho {symbol}: {str(e)}")
    
    def save_backtest_results(self, results):
        """Lưu kết quả backtest vào file"""
        try:
            # Lưu kết quả chi tiết cho từng symbol
            for symbol, result in results.items():
                if result is None:
                    continue
                    
                filename = f"{self.results_dir}{symbol}_high_risk_backtest.json"
                
                # Copy kết quả và loại bỏ các dữ liệu lớn
                result_to_save = result.copy()
                result_to_save.pop('balance_history', None)
                result_to_save.pop('trades', None)
                
                with open(filename, 'w') as f:
                    json.dump(result_to_save, f, indent=4)
                
                self.logger.info(f"Đã lưu kết quả backtest cho {symbol} tại {filename}")
            
            # Tạo báo cáo tổng hợp
            summary = []
            for symbol, result in results.items():
                if result is None:
                    continue
                    
                summary.append({
                    'symbol': symbol,
                    'profit_pct': result.get('profit_pct', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'trades_count': result.get('trades_count', 0),
                    'win_rate': result.get('win_rate', 0),
                    'profit_factor': result.get('profit_factor', 0)
                })
            
            # Sắp xếp theo lợi nhuận
            summary.sort(key=lambda x: x['profit_pct'], reverse=True)
            
            # Lưu báo cáo tổng hợp
            summary_filename = f"{self.results_dir}high_risk_backtest_summary.json"
            with open(summary_filename, 'w') as f:
                json.dump(summary, f, indent=4)
            
            self.logger.info(f"Đã lưu báo cáo tổng hợp backtest tại {summary_filename}")
            
            # Tạo báo cáo text
            text_report = "===== BÁO CÁO BACKTEST CHIẾN LƯỢC RỦI RO CAO =====\n\n"
            text_report += f"Ngày thực hiện: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_report += f"Số ngày backtest: {self.backtest_days}\n"
            text_report += f"Khung thời gian: {self.timeframe}\n"
            text_report += f"Rủi ro mỗi lệnh: {self.risk_per_trade}%\n"
            text_report += f"Đòn bẩy: {self.leverage}x\n\n"
            
            text_report += "TOP 5 COIN HIỆU SUẤT CAO NHẤT:\n"
            for i, item in enumerate(summary[:5]):
                text_report += f"{i+1}. {item['symbol']}: {item['profit_pct']:.2f}%, Drawdown: {item['max_drawdown']:.2f}%, Win rate: {item['win_rate']:.2f}%, PF: {item['profit_factor']:.2f}\n"
            
            text_report += "\nTOP 5 COIN HIỆU SUẤT THẤP NHẤT:\n"
            for i, item in enumerate(summary[-5:]):
                text_report += f"{i+1}. {item['symbol']}: {item['profit_pct']:.2f}%, Drawdown: {item['max_drawdown']:.2f}%, Win rate: {item['win_rate']:.2f}%, PF: {item['profit_factor']:.2f}\n"
            
            # Tính trung bình toàn bộ
            avg_profit = np.mean([item['profit_pct'] for item in summary])
            avg_drawdown = np.mean([item['max_drawdown'] for item in summary])
            avg_win_rate = np.mean([item['win_rate'] for item in summary])
            avg_pf = np.mean([item['profit_factor'] for item in summary])
            
            text_report += f"\nHIỆU SUẤT TRUNG BÌNH TOÀN BỘ COIN:\n"
            text_report += f"Lợi nhuận: {avg_profit:.2f}%\n"
            text_report += f"Drawdown: {avg_drawdown:.2f}%\n"
            text_report += f"Win rate: {avg_win_rate:.2f}%\n"
            text_report += f"Profit Factor: {avg_pf:.2f}\n"
            
            # Lưu báo cáo text
            report_filename = f"{self.results_dir}high_risk_backtest_report.txt"
            with open(report_filename, 'w') as f:
                f.write(text_report)
            
            self.logger.info(f"Đã lưu báo cáo backtest chi tiết tại {report_filename}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Lỗi khi lưu kết quả backtest: {str(e)}")
            return None
    
    def backtest_one_symbol(self, symbol):
        """Thực hiện backtest cho một symbol"""
        try:
            self.logger.info(f"Bắt đầu backtest cho {symbol}")
            
            # Tải dữ liệu lịch sử
            df = self.download_historical_data(symbol, days=self.backtest_days, timeframe=self.timeframe)
            
            if df is None or len(df) < 20:
                self.logger.warning(f"Không đủ dữ liệu cho {symbol}, bỏ qua.")
                return None
            
            # Thêm chỉ báo kỹ thuật
            df = self.apply_technical_indicators(df)
            
            # Áp dụng chiến lược
            df = self.apply_strategy(df, symbol)
            
            # Chạy backtest
            result = self.run_backtest(df, symbol)
            
            # Vẽ đồ thị kết quả
            self.plot_backtest_results(df, result, symbol)
            
            self.logger.info(f"Đã hoàn thành backtest cho {symbol}: Lợi nhuận {result.get('profit_pct', 0):.2f}%")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Lỗi khi thực hiện backtest cho {symbol}: {str(e)}")
            return None
    
    def run_all_backtests(self):
        """Thực hiện backtest cho tất cả các symbol"""
        self.logger.info(f"Bắt đầu backtest cho {len(self.symbols)} cặp tiền")
        
        results = {}
        
        # Sử dụng ThreadPoolExecutor để chạy song song
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Tạo dict future -> symbol để theo dõi kết quả
            future_to_symbol = {executor.submit(self.backtest_one_symbol, symbol): symbol for symbol in self.symbols}
            
            # Thu thập kết quả khi hoàn thành
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result = future.result()
                    if result is not None:
                        results[symbol] = result
                except Exception as e:
                    self.logger.error(f"Lỗi khi chạy backtest cho {symbol}: {str(e)}")
        
        # Lưu kết quả
        summary = self.save_backtest_results(results)
        
        self.logger.info(f"Đã hoàn thành backtest cho tất cả các cặp tiền, xem kết quả tại {self.results_dir}")
        
        return summary

def main():
    """Hàm chính để thực hiện backtest"""
    parser = argparse.ArgumentParser(description='Chạy backtest chiến lược rủi ro cao')
    parser.add_argument('--days', type=int, default=30, help='Số ngày backtest')
    parser.add_argument('--timeframe', type=str, default='1h', help='Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--balance', type=float, default=10000, help='Số dư ban đầu cho backtest')
    parser.add_argument('--symbol', type=str, help='Symbol cụ thể để backtest (không bắt buộc)')
    
    args = parser.parse_args()
    
    backtester = HighRiskBacktester()
    backtester.backtest_days = args.days
    backtester.timeframe = args.timeframe
    backtester.initial_balance = args.balance
    
    if args.symbol:
        backtester.symbols = [args.symbol]
    
    summary = backtester.run_all_backtests()
    
    # In ra báo cáo tóm tắt
    if summary:
        print("\n===== BÁO CÁO TÓM TẮT =====")
        print(f"TOP 5 HIỆU SUẤT CAO NHẤT:")
        for i, item in enumerate(summary[:5]):
            print(f"{i+1}. {item['symbol']}: {item['profit_pct']:.2f}%, Drawdown: {item['max_drawdown']:.2f}%, Win rate: {item['win_rate']:.2f}%")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())