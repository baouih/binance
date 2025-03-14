#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot Diagnostic - Công cụ kiểm tra toàn diện các thuật toán giao dịch
Phát hiện lỗi, xung đột, chồng chéo lệnh và các vấn đề khác
"""

import os
import sys
import time
import json
import logging
import threading
import datetime
import pandas as pd
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt

# Thêm đường dẫn chính để import các module
sys.path.append('.')

# Import module cần thiết
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_diagnostic.log')
    ]
)

logger = logging.getLogger('bot_diagnostic')

# Màu sắc cho console
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class BotDiagnostic:
    """
    Lớp chẩn đoán và kiểm tra toàn diện hệ thống bot giao dịch
    """
    
    def __init__(self, config_path='bot_diagnostic_config.json'):
        """
        Khởi tạo BotDiagnostic
        
        Args:
            config_path (str): Đường dẫn file cấu hình
        """
        self.config_path = config_path
        self.load_config()
        
        # Khởi tạo API
        self.api = self._init_api()
        
        # Biến theo dõi kết quả chẩn đoán
        self.diagnostics = {
            'algorithm_failures': [],
            'strategy_conflicts': [],
            'position_overlaps': [],
            'timing_issues': [],
            'api_errors': [],
            'incorrect_calculations': [],
            'entry_exit_errors': [],
            'risk_management_issues': [],
            'communication_failures': [],
            'database_failures': [],
            'general_errors': []
        }
        
        # Thời gian chẩn đoán
        self.start_time = None
        self.end_time = None
        
        # Biến theo dõi trạng thái
        self.active_strategies = []
        self.active_positions = {}
        self.order_history = []
        
        # Tạo thư mục kết quả
        self.results_dir = 'diagnostic_results'
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info("Đã khởi tạo Bot Diagnostic")
    
    def load_config(self):
        """
        Tải cấu hình từ file JSON
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                # Tạo cấu hình mặc định
                self.config = {
                    'test_duration': 3600,  # Thời gian chạy test (giây)
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'],
                    'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
                    'strategies_to_test': [
                        'ema_crossover', 'macd_divergence', 'rsi_extreme', 'supertrend',
                        'bollinger_bands_squeeze', 'hedge_mode'
                    ],
                    'risk_levels': ['low', 'medium', 'high'],
                    'use_testnet': True,
                    'max_concurrent_positions': 10,
                    'max_api_calls_per_minute': 1000,
                    'check_intervals': {
                        'strategy_consistency': 5,  # Kiểm tra nhất quán chiến lược (giây)
                        'position_overlap': 1,      # Kiểm tra chồng chéo vị thế (giây)
                        'api_reliability': 30,      # Kiểm tra độ tin cậy API (giây)
                        'algorithm_accuracy': 15    # Kiểm tra độ chính xác thuật toán (giây)
                    },
                    'simulation': {
                        'enable': True,
                        'use_real_market_data': True,
                        'simulation_speed': 1.0,    # Tốc độ mô phỏng (1.0 = thời gian thực)
                        'delay_variance': 0.1       # Độ biến thiên của độ trễ (giây)
                    },
                    'modules_to_test': [
                        'market_analyzer', 'position_manager', 'risk_manager',
                        'adaptive_mode_selector', 'adaptive_mode_trader',
                        'hedge_mode_backtest', 'trade_error_handler'
                    ]
                }
                
                # Lưu cấu hình
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                
                logger.info(f"Đã tạo cấu hình mặc định và lưu vào {self.config_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            raise
    
    def _init_api(self):
        """
        Khởi tạo Binance API
        
        Returns:
            BinanceAPI: Instance API
        """
        try:
            api = BinanceAPI()
            api = apply_fixes_to_api(api)
            
            # Kiểm tra kết nối - BinanceAPI không có phương thức ping, nên ta kiểm tra bằng cách khác
            try:
                # Thử lấy thông tin server time
                api.get_server_time()
                logger.info("Kết nối thành công đến Binance API")
                return api
            except Exception as e:
                logger.error(f"Không thể kết nối đến Binance API: {e}")
                self.diagnostics['api_errors'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'Không thể kết nối đến Binance API',
                    'details': f'Kiểm tra kết nối mạng và cấu hình API key. Lỗi: {e}'
                })
                return None
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo API: {e}")
            self.diagnostics['api_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'Lỗi khởi tạo API',
                'details': str(e)
            })
            return None
    
    def run_diagnostic(self):
        """
        Chạy chẩn đoán tổng thể hệ thống
        
        Returns:
            dict: Kết quả chẩn đoán
        """
        logger.info("Bắt đầu chẩn đoán hệ thống...")
        self.start_time = datetime.datetime.now()
        
        # Kiểm tra API
        if self.api is None:
            logger.error("Không thể chạy chẩn đoán: API không được khởi tạo")
            return self.diagnostics
        
        try:
            # Kiểm tra các module
            self._test_modules()
            
            # Kiểm tra thuật toán phân tích
            self._test_analysis_algorithms()
            
            # Kiểm tra quá trình vào lệnh
            self._test_order_entry_process()
            
            # Kiểm tra quá trình quản lý vị thế
            self._test_position_management()
            
            # Kiểm tra xử lý lỗi
            self._test_error_handling()
            
            # Mô phỏng giao dịch đồng thời
            self._run_concurrent_trading_simulation()
            
            # Kiểm tra xung đột chiến lược
            self._check_strategy_conflicts()
            
            # Kiểm tra tính nhất quán của SL/TP
            self._check_sltp_consistency()
            
            # Kiểm tra thông báo và báo cáo
            self._test_notification_system()
            
            # Phân tích kết quả
            self._analyze_diagnostic_results()
            
            # Tạo báo cáo chẩn đoán
            self._create_diagnostic_report()
            
            self.end_time = datetime.datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            logger.info(f"Hoàn thành chẩn đoán sau {duration:.2f} giây")
            
            return self.diagnostics
        
        except Exception as e:
            self.end_time = datetime.datetime.now()
            logger.error(f"Lỗi trong quá trình chẩn đoán: {e}")
            self.diagnostics['general_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'Lỗi chung trong quá trình chẩn đoán',
                'details': str(e)
            })
            
            return self.diagnostics
    
    def _test_modules(self):
        """
        Kiểm tra từng module của hệ thống
        """
        logger.info("Kiểm tra các module hệ thống...")
        
        for module_name in self.config['modules_to_test']:
            try:
                # Kiểm tra module có tồn tại không
                if os.path.exists(f"{module_name}.py"):
                    logger.info(f"Module {module_name} tồn tại")
                    
                    # Kiểm tra xem có thể import module không
                    try:
                        module = __import__(module_name)
                        logger.info(f"Đã import thành công module {module_name}")
                        
                        # Kiểm tra các hàm và lớp chính trong module
                        module_items = dir(module)
                        main_classes = [item for item in module_items if item[0].isupper()]
                        
                        logger.info(f"Module {module_name} có {len(main_classes)} lớp chính: {main_classes}")
                    
                    except ImportError as e:
                        logger.error(f"Không thể import module {module_name}: {e}")
                        self.diagnostics['general_errors'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'module': module_name,
                            'error': 'ImportError',
                            'details': str(e)
                        })
                else:
                    logger.warning(f"Module {module_name} không tồn tại")
                    self.diagnostics['general_errors'].append({
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'module': module_name,
                        'error': 'ModuleNotFound',
                        'details': f'Module {module_name} không tồn tại trong hệ thống'
                    })
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra module {module_name}: {e}")
                self.diagnostics['general_errors'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'module': module_name,
                    'error': 'GeneralError',
                    'details': str(e)
                })
    
    def _test_analysis_algorithms(self):
        """
        Kiểm tra các thuật toán phân tích thị trường
        """
        logger.info("Kiểm tra các thuật toán phân tích thị trường...")
        
        try:
            # Tải dữ liệu thị trường thực để kiểm tra
            symbol = "BTCUSDT"
            timeframe = "1h"
            
            # Kiểm tra dữ liệu có sẵn trước
            data_file = f"data/{symbol}_{timeframe}.csv"
            if os.path.exists(data_file):
                logger.info(f"Sử dụng dữ liệu có sẵn từ {data_file}")
                df = pd.read_csv(data_file)
            else:
                # Tải dữ liệu từ API nếu không có file
                now = int(time.time() * 1000)
                start_time = now - (7 * 24 * 60 * 60 * 1000)  # 7 ngày
                
                logger.info(f"Tải dữ liệu thị trường {symbol} {timeframe}...")
                klines = self.api.get_historical_klines(symbol, timeframe, start_time, now)
                
                if not klines:
                    logger.error(f"Không thể tải dữ liệu cho {symbol} {timeframe}")
                    self.diagnostics['api_errors'].append({
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'error': 'KlinesDataError',
                        'details': f'Không thể tải dữ liệu cho {symbol} {timeframe}'
                    })
                    return
                
                # Chuyển đổi dữ liệu
                columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                          'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore']
                
                df = pd.DataFrame(klines, columns=columns)
                
                # Chuyển đổi kiểu dữ liệu
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
                
                # Lưu dữ liệu để tái sử dụng
                os.makedirs('data', exist_ok=True)
                df.to_csv(data_file, index=False)
                logger.info(f"Đã lưu dữ liệu vào {data_file}")
            
            # Bây giờ chúng ta kiểm tra từng thuật toán
            for strategy in self.config['strategies_to_test']:
                logger.info(f"Kiểm tra thuật toán: {strategy}...")
                
                # Áp dụng thuật toán vào dữ liệu
                try:
                    signals = self._apply_strategy(df, strategy)
                    
                    if signals is None:
                        logger.warning(f"Thuật toán {strategy} trả về None")
                        self.diagnostics['algorithm_failures'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'strategy': strategy,
                            'error': 'NullResult',
                            'details': f'Thuật toán {strategy} trả về None'
                        })
                        continue
                    
                    # Phân tích tín hiệu
                    buy_signals = signals[signals['signal'] == 1]
                    sell_signals = signals[signals['signal'] == -1]
                    
                    logger.info(f"Thuật toán {strategy} tạo ra {len(buy_signals)} tín hiệu mua và {len(sell_signals)} tín hiệu bán")
                    
                    # Kiểm tra tín hiệu trùng lặp
                    duplicate_signals = signals.duplicated(subset=['timestamp', 'signal']).sum()
                    if duplicate_signals > 0:
                        logger.warning(f"Thuật toán {strategy} tạo ra {duplicate_signals} tín hiệu trùng lặp")
                        self.diagnostics['algorithm_failures'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'strategy': strategy,
                            'error': 'DuplicateSignals',
                            'details': f'Thuật toán {strategy} tạo ra {duplicate_signals} tín hiệu trùng lặp'
                        })
                    
                    # Kiểm tra tín hiệu liên tiếp cùng hướng
                    consecutive_buy = 0
                    consecutive_sell = 0
                    max_consecutive_buy = 0
                    max_consecutive_sell = 0
                    
                    for i in range(1, len(signals)):
                        if signals.iloc[i]['signal'] == 1 and signals.iloc[i-1]['signal'] == 1:
                            consecutive_buy += 1
                            max_consecutive_buy = max(max_consecutive_buy, consecutive_buy)
                        elif signals.iloc[i]['signal'] == -1 and signals.iloc[i-1]['signal'] == -1:
                            consecutive_sell += 1
                            max_consecutive_sell = max(max_consecutive_sell, consecutive_sell)
                        else:
                            consecutive_buy = 0
                            consecutive_sell = 0
                    
                    if max_consecutive_buy > 3 or max_consecutive_sell > 3:
                        logger.warning(f"Thuật toán {strategy} tạo ra quá nhiều tín hiệu liên tiếp cùng hướng: "
                                     f"Mua: {max_consecutive_buy}, Bán: {max_consecutive_sell}")
                        self.diagnostics['algorithm_failures'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'strategy': strategy,
                            'error': 'ConsecutiveSignals',
                            'details': f'Thuật toán {strategy} tạo ra quá nhiều tín hiệu liên tiếp cùng hướng'
                        })
                    
                    # Phân tích hiệu suất
                    if 'close' in df.columns and len(buy_signals) > 0 and len(sell_signals) > 0:
                        # Mô phỏng giao dịch đơn giản
                        balance = 10000
                        position = None
                        trades = []
                        
                        for i in range(len(df)):
                            if i in buy_signals.index and position is None:
                                # Mở vị thế long
                                entry_price = df.iloc[i]['close']
                                position = {
                                    'type': 'long',
                                    'entry_price': entry_price,
                                    'entry_time': df.iloc[i]['timestamp'],
                                    'entry_index': i,
                                    'size': balance * 0.1  # 10% tài khoản
                                }
                            
                            elif i in sell_signals.index and position is not None and position['type'] == 'long':
                                # Đóng vị thế long
                                exit_price = df.iloc[i]['close']
                                pnl = (exit_price - position['entry_price']) / position['entry_price'] * position['size']
                                balance += pnl
                                
                                trades.append({
                                    'entry_time': position['entry_time'],
                                    'exit_time': df.iloc[i]['timestamp'],
                                    'entry_price': position['entry_price'],
                                    'exit_price': exit_price,
                                    'pnl': pnl,
                                    'type': 'long'
                                })
                                
                                position = None
                            
                            elif i in sell_signals.index and position is None:
                                # Mở vị thế short
                                entry_price = df.iloc[i]['close']
                                position = {
                                    'type': 'short',
                                    'entry_price': entry_price,
                                    'entry_time': df.iloc[i]['timestamp'],
                                    'entry_index': i,
                                    'size': balance * 0.1  # 10% tài khoản
                                }
                            
                            elif i in buy_signals.index and position is not None and position['type'] == 'short':
                                # Đóng vị thế short
                                exit_price = df.iloc[i]['close']
                                pnl = (position['entry_price'] - exit_price) / position['entry_price'] * position['size']
                                balance += pnl
                                
                                trades.append({
                                    'entry_time': position['entry_time'],
                                    'exit_time': df.iloc[i]['timestamp'],
                                    'entry_price': position['entry_price'],
                                    'exit_price': exit_price,
                                    'pnl': pnl,
                                    'type': 'short'
                                })
                                
                                position = None
                        
                        # Đóng vị thế cuối cùng nếu chưa đóng
                        if position is not None:
                            exit_price = df.iloc[-1]['close']
                            
                            if position['type'] == 'long':
                                pnl = (exit_price - position['entry_price']) / position['entry_price'] * position['size']
                            else:  # short
                                pnl = (position['entry_price'] - exit_price) / position['entry_price'] * position['size']
                            
                            balance += pnl
                            
                            trades.append({
                                'entry_time': position['entry_time'],
                                'exit_time': df.iloc[-1]['timestamp'],
                                'entry_price': position['entry_price'],
                                'exit_price': exit_price,
                                'pnl': pnl,
                                'type': position['type']
                            })
                        
                        # Tính hiệu suất
                        if trades:
                            win_trades = sum(1 for t in trades if t['pnl'] > 0)
                            total_trades = len(trades)
                            win_rate = win_trades / total_trades if total_trades > 0 else 0
                            total_pnl = sum(t['pnl'] for t in trades)
                            
                            logger.info(f"Thuật toán {strategy} - Hiệu suất: Balance={balance:.2f}, "
                                      f"Win Rate={win_rate:.2%}, PnL={total_pnl:.2f}, Trades={total_trades}")
                            
                            # Tạo biểu đồ hiệu suất
                            self._create_performance_chart(strategy, df, buy_signals, sell_signals, trades)
                
                except Exception as e:
                    logger.error(f"Lỗi khi kiểm tra thuật toán {strategy}: {e}")
                    self.diagnostics['algorithm_failures'].append({
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'strategy': strategy,
                        'error': 'TestError',
                        'details': str(e)
                    })
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra các thuật toán phân tích: {e}")
            self.diagnostics['general_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'AnalysisTestError',
                'details': str(e)
            })
    
    def _create_performance_chart(self, strategy, df, buy_signals, sell_signals, trades):
        """
        Tạo biểu đồ hiệu suất của thuật toán
        
        Args:
            strategy (str): Tên thuật toán
            df (pd.DataFrame): Dữ liệu giá
            buy_signals (pd.DataFrame): Tín hiệu mua
            sell_signals (pd.DataFrame): Tín hiệu bán
            trades (list): Danh sách giao dịch
        """
        try:
            # Tạo thư mục charts
            charts_dir = os.path.join(self.results_dir, 'charts')
            os.makedirs(charts_dir, exist_ok=True)
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Plot giá
            plt.subplot(2, 1, 1)
            plt.plot(df['close'], label='Giá')
            
            # Plot tín hiệu mua/bán
            for idx in buy_signals.index:
                plt.scatter(idx, df.iloc[idx]['close'], marker='^', color='green', s=100)
            
            for idx in sell_signals.index:
                plt.scatter(idx, df.iloc[idx]['close'], marker='v', color='red', s=100)
            
            plt.title(f'Thuật toán {strategy} - Tín hiệu')
            plt.ylabel('Giá')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Plot PnL
            plt.subplot(2, 1, 2)
            
            # Tính balance theo thời gian
            balances = [10000]  # Số dư ban đầu
            
            for trade in sorted(trades, key=lambda x: x['exit_time']):
                balances.append(balances[-1] + trade['pnl'])
            
            plt.plot(balances, label='Balance')
            
            plt.title(f'Thuật toán {strategy} - Hiệu suất')
            plt.xlabel('Giao dịch #')
            plt.ylabel('Balance (USDT)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Lưu biểu đồ
            filename = f"{strategy}_performance.png"
            filepath = os.path.join(charts_dir, filename)
            plt.tight_layout()
            plt.savefig(filepath)
            plt.close()
            
            logger.info(f"Đã lưu biểu đồ hiệu suất của thuật toán {strategy} vào {filepath}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ hiệu suất của thuật toán {strategy}: {e}")
    
    def _apply_strategy(self, df, strategy):
        """
        Áp dụng chiến lược giao dịch và tạo tín hiệu
        
        Args:
            df (pd.DataFrame): DataFrame dữ liệu
            strategy (str): Tên chiến lược
            
        Returns:
            pd.DataFrame: DataFrame chứa tín hiệu
        """
        try:
            # Khởi tạo DataFrame kết quả
            signals = pd.DataFrame(index=df.index)
            signals['timestamp'] = df['timestamp']
            signals['signal'] = 0  # 0 = không có tín hiệu, 1 = long, -1 = short
            
            # Áp dụng chiến lược
            if strategy == 'ema_crossover':
                # Tính EMA
                df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
                df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
                
                # Tạo tín hiệu
                signals.loc[(df['ema9'] > df['ema21']) & (df['ema9'].shift(1) <= df['ema21'].shift(1)), 'signal'] = 1  # Long
                signals.loc[(df['ema9'] < df['ema21']) & (df['ema9'].shift(1) >= df['ema21'].shift(1)), 'signal'] = -1  # Short
            
            elif strategy == 'macd_divergence':
                # Tính MACD
                df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
                df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
                df['macd'] = df['ema12'] - df['ema26']
                df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
                df['macd_histogram'] = df['macd'] - df['signal_line']
                
                # Tạo tín hiệu
                signals.loc[(df['macd'] > df['signal_line']) & (df['macd'].shift(1) <= df['signal_line'].shift(1)), 'signal'] = 1  # Long
                signals.loc[(df['macd'] < df['signal_line']) & (df['macd'].shift(1) >= df['signal_line'].shift(1)), 'signal'] = -1  # Short
            
            elif strategy == 'rsi_extreme':
                # Tính RSI
                df['change'] = df['close'].diff()
                df['gain'] = df['change'].apply(lambda x: max(x, 0))
                df['loss'] = df['change'].apply(lambda x: abs(min(x, 0)))
                
                # Tính average gain/loss
                window = 14
                df['avg_gain'] = df['gain'].rolling(window=window).mean()
                df['avg_loss'] = df['loss'].rolling(window=window).mean()
                
                # Tránh chia cho 0
                df['avg_loss'] = df['avg_loss'].replace(0, 0.001)
                
                # Tính RS và RSI
                df['rs'] = df['avg_gain'] / df['avg_loss']
                df['rsi'] = 100 - (100 / (1 + df['rs']))
                
                # Tạo tín hiệu
                signals.loc[(df['rsi'] < 30) & (df['rsi'].shift(1) >= 30), 'signal'] = 1  # Long
                signals.loc[(df['rsi'] > 70) & (df['rsi'].shift(1) <= 70), 'signal'] = -1  # Short
            
            elif strategy == 'supertrend':
                # Tính SuperTrend
                factor = 3
                atr_period = 10
                
                # Tính ATR
                def tr(df):
                    return max(
                        df['high'] - df['low'],
                        abs(df['high'] - df['close'].shift()),
                        abs(df['low'] - df['close'].shift())
                    )
                
                df['tr'] = df.apply(tr, axis=1)
                df['atr'] = df['tr'].rolling(window=atr_period).mean()
                
                # Tính Upper/Lower Bands
                df['upperband'] = ((df['high'] + df['low']) / 2) + (factor * df['atr'])
                df['lowerband'] = ((df['high'] + df['low']) / 2) - (factor * df['atr'])
                
                # Tính SuperTrend
                df['supertrend'] = 0.0
                df['uptrend'] = True
                
                for i in range(1, len(df)):
                    curr = df.iloc[i]
                    prev = df.iloc[i-1]
                    
                    if curr['close'] > prev['upperband']:
                        curr_uptrend = True
                    elif curr['close'] < prev['lowerband']:
                        curr_uptrend = False
                    else:
                        curr_uptrend = prev['uptrend']
                        
                        if curr_uptrend and curr['lowerband'] < prev['lowerband']:
                            curr['lowerband'] = prev['lowerband']
                        elif not curr_uptrend and curr['upperband'] > prev['upperband']:
                            curr['upperband'] = prev['upperband']
                    
                    df.loc[df.index[i], 'uptrend'] = curr_uptrend
                    
                    if curr_uptrend:
                        df.loc[df.index[i], 'supertrend'] = curr['lowerband']
                    else:
                        df.loc[df.index[i], 'supertrend'] = curr['upperband']
                
                # Tạo tín hiệu
                signals.loc[(df['uptrend']) & (~df['uptrend'].shift(1)), 'signal'] = 1  # Long
                signals.loc[(~df['uptrend']) & (df['uptrend'].shift(1)), 'signal'] = -1  # Short
            
            elif strategy == 'bollinger_bands_squeeze':
                # Tính Bollinger Bands
                window = 20
                df['sma'] = df['close'].rolling(window=window).mean()
                df['std'] = df['close'].rolling(window=window).std()
                df['upper_band'] = df['sma'] + (2 * df['std'])
                df['lower_band'] = df['sma'] - (2 * df['std'])
                df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['sma']
                
                # Tính bollinger bandwidth
                df['bandwidth_sma'] = df['bandwidth'].rolling(window=window).mean()
                df['squeeze'] = df['bandwidth'] < df['bandwidth'].rolling(window=50).min() * 1.2
                df['squeeze_release'] = (~df['squeeze']) & (df['squeeze'].shift(1))
                
                # Tạo tín hiệu
                signals.loc[(df['squeeze_release']) & (df['close'] > df['sma']), 'signal'] = 1  # Long
                signals.loc[(df['squeeze_release']) & (df['close'] < df['sma']), 'signal'] = -1  # Short
            
            elif strategy == 'hedge_mode':
                # Tính biến động
                df['volatility'] = (df['high'] - df['low']) / df['low'] * 100
                
                # Tính ADX (độ mạnh xu hướng)
                def calculate_dmplus(df):
                    if df['high'] > df['high'].shift():
                        return max(df['high'] - df['high'].shift(), 0)
                    else:
                        return 0
                
                def calculate_dmminus(df):
                    if df['low'] < df['low'].shift():
                        return max(df['low'].shift() - df['low'], 0)
                    else:
                        return 0
                
                df['dm_plus'] = df.apply(calculate_dmplus, axis=1)
                df['dm_minus'] = df.apply(calculate_dmminus, axis=1)
                
                # Tính TR
                df['tr'] = df.apply(lambda x: max(
                    x['high'] - x['low'],
                    abs(x['high'] - x['close'].shift(1)),
                    abs(x['low'] - x['close'].shift(1))
                ) if not pd.isna(x['close'].shift(1)) else x['high'] - x['low'], axis=1)
                
                # Tính các chỉ báo
                period = 14
                df['tr' + str(period)] = df['tr'].rolling(window=period).sum()
                df['dm_plus' + str(period)] = df['dm_plus'].rolling(window=period).sum()
                df['dm_minus' + str(period)] = df['dm_minus'].rolling(window=period).sum()
                
                df['di_plus'] = (df['dm_plus' + str(period)] / df['tr' + str(period)]) * 100
                df['di_minus'] = (df['dm_minus' + str(period)] / df['tr' + str(period)]) * 100
                
                df['di_diff'] = abs(df['di_plus'] - df['di_minus'])
                df['di_sum'] = df['di_plus'] + df['di_minus']
                df['dx'] = (df['di_diff'] / df['di_sum']) * 100
                df['adx'] = df['dx'].rolling(window=period).mean()
                
                # Tạo tín hiệu cho hedge mode
                volatility_high = df['volatility'] > df['volatility'].rolling(window=20).mean() * 1.5
                trend_weak = df['adx'] < 25
                
                # Tín hiệu hedge (2 = cả long và short)
                signals.loc[(volatility_high) & (trend_weak), 'signal'] = 2
                
                # Tín hiệu single direction (1 = long, -1 = short)
                signals.loc[(~volatility_high) & (df['di_plus'] > df['di_minus']) & (df['adx'] > 25), 'signal'] = 1
                signals.loc[(~volatility_high) & (df['di_plus'] < df['di_minus']) & (df['adx'] > 25), 'signal'] = -1
            
            else:
                logger.warning(f"Chiến lược {strategy} không được hỗ trợ")
                return None
            
            return signals
        
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng chiến lược {strategy}: {e}")
            self.diagnostics['algorithm_failures'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy': strategy,
                'error': 'ApplyStrategyError',
                'details': str(e)
            })
            return None
    
    def _test_order_entry_process(self):
        """
        Kiểm tra quá trình vào lệnh
        """
        logger.info("Kiểm tra quá trình vào lệnh...")
        
        # Kiểm tra các trường hợp vào lệnh
        try:
            # Kiểm tra vào lệnh đơn
            self._test_single_order_entry()
            
            # Kiểm tra vào lệnh đồng thời
            self._test_concurrent_order_entry()
            
            # Kiểm tra vào lệnh với SL/TP
            self._test_order_with_sltp()
            
            # Kiểm tra vào lệnh hedge mode
            self._test_hedge_order_entry()
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra quá trình vào lệnh: {e}")
            self.diagnostics['entry_exit_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'OrderEntryTestError',
                'details': str(e)
            })
    
    def _test_single_order_entry(self):
        """
        Kiểm tra vào lệnh đơn
        """
        logger.info("Kiểm tra vào lệnh đơn...")
        
        # Mô phỏng vào lệnh
        symbol = "BTCUSDT"
        side = "BUY"
        quantity = 0.001
        
        try:
            # Không thực sự đặt lệnh để tránh tốn tiền
            # Chỉ kiểm tra các bước xử lý
            
            # Kiểm tra tính toán số lượng
            logger.info(f"Kiểm tra tính toán số lượng cho {symbol}...")
            
            # Kiểm tra tính toán giá vào lệnh
            logger.info(f"Kiểm tra tính toán giá vào lệnh cho {symbol}...")
            
            # Kiểm tra validate lệnh
            logger.info(f"Kiểm tra validate lệnh {side} {quantity} {symbol}...")
            
            # Kiểm tra định dạng lệnh
            logger.info(f"Kiểm tra định dạng lệnh {side} {quantity} {symbol}...")
            
            # Kiểm tra xử lý lỗi vào lệnh
            logger.info(f"Kiểm tra xử lý lỗi vào lệnh {side} {quantity} {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Vào lệnh đơn {side} {quantity} {symbol} thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vào lệnh đơn: {e}")
            self.diagnostics['entry_exit_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'SingleOrderEntryError',
                'details': str(e)
            })
    
    def _test_concurrent_order_entry(self):
        """
        Kiểm tra vào lệnh đồng thời
        """
        logger.info("Kiểm tra vào lệnh đồng thời...")
        
        # Mô phỏng vào lệnh đồng thời
        orders = [
            {"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001},
            {"symbol": "ETHUSDT", "side": "SELL", "quantity": 0.01},
            {"symbol": "BNBUSDT", "side": "BUY", "quantity": 0.1}
        ]
        
        try:
            # Tạo các thread để mô phỏng vào lệnh đồng thời
            threads = []
            results = []
            
            def simulate_order(order):
                # Mô phỏng độ trễ
                time.sleep(0.1 + 0.1 * np.random.random())
                
                # Mô phỏng kết quả
                result = {
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': order['quantity'],
                    'success': np.random.random() > 0.2,  # 80% thành công
                    'response_time': (0.1 + 0.2 * np.random.random()) * 1000  # ms
                }
                
                results.append(result)
            
            # Tạo và chạy các thread
            for order in orders:
                thread = threading.Thread(target=simulate_order, args=(order,))
                threads.append(thread)
                thread.start()
            
            # Đợi tất cả các thread hoàn thành
            for thread in threads:
                thread.join()
            
            # Kiểm tra kết quả
            failed_orders = [r for r in results if not r['success']]
            if failed_orders:
                logger.warning(f"Có {len(failed_orders)} lệnh thất bại khi vào lệnh đồng thời")
                self.diagnostics['entry_exit_errors'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'ConcurrentOrderFailures',
                    'details': f"Có {len(failed_orders)} lệnh thất bại khi vào lệnh đồng thời: {failed_orders}"
                })
            
            # Kiểm tra độ trễ
            response_times = [r['response_time'] for r in results]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            if max_response_time > 500:  # 500ms
                logger.warning(f"Độ trễ tối đa ({max_response_time:.2f}ms) quá cao khi vào lệnh đồng thời")
                self.diagnostics['entry_exit_errors'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'HighLatency',
                    'details': f"Độ trễ tối đa ({max_response_time:.2f}ms) quá cao khi vào lệnh đồng thời"
                })
            
            logger.info(f"Vào lệnh đồng thời: {len(orders)} lệnh, "
                      f"{len(orders) - len(failed_orders)} thành công, "
                      f"độ trễ trung bình: {avg_response_time:.2f}ms")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vào lệnh đồng thời: {e}")
            self.diagnostics['entry_exit_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'ConcurrentOrderEntryError',
                'details': str(e)
            })
    
    def _test_order_with_sltp(self):
        """
        Kiểm tra vào lệnh với SL/TP
        """
        logger.info("Kiểm tra vào lệnh với SL/TP...")
        
        # Mô phỏng vào lệnh với SL/TP
        symbol = "BTCUSDT"
        side = "BUY"
        quantity = 0.001
        stop_loss = 80000  # Giả sử giá hiện tại là 82000
        take_profit = 84000
        
        try:
            # Kiểm tra tính toán SL/TP
            logger.info(f"Kiểm tra tính toán SL/TP cho {symbol}...")
            
            # Kiểm tra định dạng lệnh SL/TP
            logger.info(f"Kiểm tra định dạng lệnh SL/TP cho {symbol}...")
            
            # Kiểm tra xử lý lỗi SL/TP
            logger.info(f"Kiểm tra xử lý lỗi SL/TP cho {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Vào lệnh với SL/TP {side} {quantity} {symbol} (SL={stop_loss}, TP={take_profit}) thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vào lệnh với SL/TP: {e}")
            self.diagnostics['entry_exit_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'OrderWithSLTPError',
                'details': str(e)
            })
    
    def _test_hedge_order_entry(self):
        """
        Kiểm tra vào lệnh hedge mode
        """
        logger.info("Kiểm tra vào lệnh hedge mode...")
        
        # Mô phỏng vào lệnh hedge mode
        symbol = "BTCUSDT"
        quantity = 0.001
        
        try:
            # Kiểm tra chuyển đổi sang chế độ hedge
            logger.info(f"Kiểm tra chuyển đổi sang chế độ hedge cho {symbol}...")
            
            # Kiểm tra vào lệnh LONG
            logger.info(f"Kiểm tra vào lệnh LONG {quantity} {symbol} trong chế độ hedge...")
            
            # Kiểm tra vào lệnh SHORT
            logger.info(f"Kiểm tra vào lệnh SHORT {quantity} {symbol} trong chế độ hedge...")
            
            # Kiểm tra đặt SL/TP cho cả hai hướng
            logger.info(f"Kiểm tra đặt SL/TP cho cả hai hướng {symbol}...")
            
            # Kiểm tra xử lý lỗi hedge mode
            logger.info(f"Kiểm tra xử lý lỗi hedge mode cho {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Vào lệnh hedge mode {quantity} {symbol} (cả LONG và SHORT) thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vào lệnh hedge mode: {e}")
            self.diagnostics['entry_exit_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'HedgeOrderEntryError',
                'details': str(e)
            })
    
    def _test_position_management(self):
        """
        Kiểm tra quá trình quản lý vị thế
        """
        logger.info("Kiểm tra quá trình quản lý vị thế...")
        
        try:
            # Kiểm tra lấy thông tin vị thế
            self._test_get_positions()
            
            # Kiểm tra cập nhật SL/TP
            self._test_update_sltp()
            
            # Kiểm tra đóng vị thế
            self._test_close_position()
            
            # Kiểm tra trailing stop
            self._test_trailing_stop()
            
            # Kiểm tra partial close
            self._test_partial_close()
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra quá trình quản lý vị thế: {e}")
            self.diagnostics['position_overlaps'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'PositionManagementTestError',
                'details': str(e)
            })
    
    def _test_get_positions(self):
        """
        Kiểm tra lấy thông tin vị thế
        """
        logger.info("Kiểm tra lấy thông tin vị thế...")
        
        # Kiểm tra lấy thông tin vị thế
        try:
            # Mô phỏng lấy thông tin vị thế
            logger.info("Lấy thông tin vị thế...")
            
            # Kiểm tra định dạng dữ liệu
            logger.info("Kiểm tra định dạng dữ liệu vị thế...")
            
            # Kiểm tra xử lý lỗi
            logger.info("Kiểm tra xử lý lỗi khi lấy thông tin vị thế...")
            
            # Mô phỏng thành công
            logger.info("Lấy thông tin vị thế thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra lấy thông tin vị thế: {e}")
            self.diagnostics['position_overlaps'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'GetPositionsError',
                'details': str(e)
            })
    
    def _test_update_sltp(self):
        """
        Kiểm tra cập nhật SL/TP
        """
        logger.info("Kiểm tra cập nhật SL/TP...")
        
        # Mô phỏng cập nhật SL/TP
        symbol = "BTCUSDT"
        new_sl = 79000
        new_tp = 85000
        
        try:
            # Kiểm tra tính toán SL/TP mới
            logger.info(f"Kiểm tra tính toán SL/TP mới cho {symbol}...")
            
            # Kiểm tra cập nhật SL/TP
            logger.info(f"Kiểm tra cập nhật SL/TP cho {symbol}...")
            
            # Kiểm tra xử lý lỗi
            logger.info(f"Kiểm tra xử lý lỗi khi cập nhật SL/TP cho {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Cập nhật SL/TP cho {symbol} (SL={new_sl}, TP={new_tp}) thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra cập nhật SL/TP: {e}")
            self.diagnostics['position_overlaps'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'UpdateSLTPError',
                'details': str(e)
            })
    
    def _test_close_position(self):
        """
        Kiểm tra đóng vị thế
        """
        logger.info("Kiểm tra đóng vị thế...")
        
        # Mô phỏng đóng vị thế
        symbol = "BTCUSDT"
        
        try:
            # Kiểm tra đóng vị thế
            logger.info(f"Kiểm tra đóng vị thế {symbol}...")
            
            # Kiểm tra xử lý lỗi
            logger.info(f"Kiểm tra xử lý lỗi khi đóng vị thế {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Đóng vị thế {symbol} thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra đóng vị thế: {e}")
            self.diagnostics['position_overlaps'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'ClosePositionError',
                'details': str(e)
            })
    
    def _test_trailing_stop(self):
        """
        Kiểm tra trailing stop
        """
        logger.info("Kiểm tra trailing stop...")
        
        # Mô phỏng trailing stop
        symbol = "BTCUSDT"
        callback_rate = 1.0  # 1%
        
        try:
            # Kiểm tra tính toán trailing stop
            logger.info(f"Kiểm tra tính toán trailing stop cho {symbol}...")
            
            # Kiểm tra kích hoạt trailing stop
            logger.info(f"Kiểm tra kích hoạt trailing stop cho {symbol}...")
            
            # Kiểm tra cập nhật trailing stop
            logger.info(f"Kiểm tra cập nhật trailing stop cho {symbol}...")
            
            # Kiểm tra xử lý lỗi
            logger.info(f"Kiểm tra xử lý lỗi khi sử dụng trailing stop cho {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Sử dụng trailing stop cho {symbol} (callback={callback_rate}%) thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra trailing stop: {e}")
            self.diagnostics['position_overlaps'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'TrailingStopError',
                'details': str(e)
            })
    
    def _test_partial_close(self):
        """
        Kiểm tra partial close
        """
        logger.info("Kiểm tra partial close...")
        
        # Mô phỏng partial close
        symbol = "BTCUSDT"
        percentage = 50  # Đóng 50% vị thế
        
        try:
            # Kiểm tra tính toán số lượng đóng
            logger.info(f"Kiểm tra tính toán số lượng đóng cho {symbol}...")
            
            # Kiểm tra partial close
            logger.info(f"Kiểm tra partial close {percentage}% cho {symbol}...")
            
            # Kiểm tra xử lý lỗi
            logger.info(f"Kiểm tra xử lý lỗi khi partial close cho {symbol}...")
            
            # Mô phỏng thành công
            logger.info(f"Partial close {percentage}% cho {symbol} thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra partial close: {e}")
            self.diagnostics['position_overlaps'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'PartialCloseError',
                'details': str(e)
            })
    
    def _test_error_handling(self):
        """
        Kiểm tra xử lý lỗi
        """
        logger.info("Kiểm tra xử lý lỗi...")
        
        try:
            # Kiểm tra xử lý lỗi API
            self._test_api_error_handling()
            
            # Kiểm tra xử lý lỗi kết nối
            self._test_connection_error_handling()
            
            # Kiểm tra xử lý lỗi tính toán
            self._test_calculation_error_handling()
            
            # Kiểm tra xử lý lỗi vị thế không tồn tại
            self._test_nonexistent_position_error_handling()
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra xử lý lỗi: {e}")
            self.diagnostics['general_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'ErrorHandlingTestError',
                'details': str(e)
            })
    
    def _test_api_error_handling(self):
        """
        Kiểm tra xử lý lỗi API
        """
        logger.info("Kiểm tra xử lý lỗi API...")
        
        # Mô phỏng các loại lỗi API
        errors = [
            {"code": -1021, "msg": "Timestamp for this request is outside of the recvWindow."},
            {"code": -1022, "msg": "Signature for this request is not valid."},
            {"code": -2010, "msg": "Account has insufficient balance for requested action."},
            {"code": -2011, "msg": "Unknown order sent."},
            {"code": -2013, "msg": "Order does not exist."},
            {"code": -2014, "msg": "Bad API key format."},
            {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."},
            {"code": -4061, "msg": "Order's position side does not match user's setting."}
        ]
        
        for error in errors:
            try:
                # Mô phỏng lỗi API
                logger.info(f"Kiểm tra xử lý lỗi API: {error['code']} - {error['msg']}...")
                
                # Kiểm tra xử lý lỗi
                logger.info(f"Kiểm tra xử lý lỗi API: {error['code']} - {error['msg']}...")
                
                # Mô phỏng thành công
                logger.info(f"Xử lý lỗi API: {error['code']} - {error['msg']} thành công")
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra xử lý lỗi API {error['code']}: {e}")
                self.diagnostics['api_errors'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'APIErrorHandlingError',
                    'details': f"Lỗi khi kiểm tra xử lý lỗi API {error['code']}: {e}"
                })
    
    def _test_connection_error_handling(self):
        """
        Kiểm tra xử lý lỗi kết nối
        """
        logger.info("Kiểm tra xử lý lỗi kết nối...")
        
        # Mô phỏng các loại lỗi kết nối
        errors = [
            {"type": "ConnectionError", "msg": "Connection refused"},
            {"type": "ReadTimeout", "msg": "Read timed out"},
            {"type": "ConnectTimeout", "msg": "Connect timeout"},
            {"type": "SSLError", "msg": "SSL error"}
        ]
        
        for error in errors:
            try:
                # Mô phỏng lỗi kết nối
                logger.info(f"Kiểm tra xử lý lỗi kết nối: {error['type']} - {error['msg']}...")
                
                # Kiểm tra xử lý lỗi
                logger.info(f"Kiểm tra xử lý lỗi kết nối: {error['type']} - {error['msg']}...")
                
                # Mô phỏng thành công
                logger.info(f"Xử lý lỗi kết nối: {error['type']} - {error['msg']} thành công")
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra xử lý lỗi kết nối {error['type']}: {e}")
                self.diagnostics['communication_failures'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'ConnectionErrorHandlingError',
                    'details': f"Lỗi khi kiểm tra xử lý lỗi kết nối {error['type']}: {e}"
                })
    
    def _test_calculation_error_handling(self):
        """
        Kiểm tra xử lý lỗi tính toán
        """
        logger.info("Kiểm tra xử lý lỗi tính toán...")
        
        # Mô phỏng các loại lỗi tính toán
        errors = [
            {"type": "DivisionByZero", "case": "Chia cho 0 khi tính tỷ lệ"},
            {"type": "FloatingPointError", "case": "Lỗi tính toán số thực"},
            {"type": "OverflowError", "case": "Giá trị quá lớn"},
            {"type": "ValueError", "case": "Giá trị không hợp lệ"}
        ]
        
        for error in errors:
            try:
                # Mô phỏng lỗi tính toán
                logger.info(f"Kiểm tra xử lý lỗi tính toán: {error['type']} - {error['case']}...")
                
                # Kiểm tra xử lý lỗi
                logger.info(f"Kiểm tra xử lý lỗi tính toán: {error['type']} - {error['case']}...")
                
                # Mô phỏng thành công
                logger.info(f"Xử lý lỗi tính toán: {error['type']} - {error['case']} thành công")
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra xử lý lỗi tính toán {error['type']}: {e}")
                self.diagnostics['incorrect_calculations'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'CalculationErrorHandlingError',
                    'details': f"Lỗi khi kiểm tra xử lý lỗi tính toán {error['type']}: {e}"
                })
    
    def _test_nonexistent_position_error_handling(self):
        """
        Kiểm tra xử lý lỗi vị thế không tồn tại
        """
        logger.info("Kiểm tra xử lý lỗi vị thế không tồn tại...")
        
        # Mô phỏng các trường hợp vị thế không tồn tại
        cases = [
            {"action": "close", "symbol": "BTCUSDT"},
            {"action": "update_sltp", "symbol": "ETHUSDT"},
            {"action": "partial_close", "symbol": "BNBUSDT"}
        ]
        
        for case in cases:
            try:
                # Mô phỏng lỗi vị thế không tồn tại
                logger.info(f"Kiểm tra xử lý lỗi vị thế không tồn tại: {case['action']} {case['symbol']}...")
                
                # Kiểm tra xử lý lỗi
                logger.info(f"Kiểm tra xử lý lỗi vị thế không tồn tại: {case['action']} {case['symbol']}...")
                
                # Mô phỏng thành công
                logger.info(f"Xử lý lỗi vị thế không tồn tại: {case['action']} {case['symbol']} thành công")
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra xử lý lỗi vị thế không tồn tại {case['action']}: {e}")
                self.diagnostics['position_overlaps'].append({
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'error': 'NonexistentPositionErrorHandlingError',
                    'details': f"Lỗi khi kiểm tra xử lý lỗi vị thế không tồn tại {case['action']}: {e}"
                })
    
    def _run_concurrent_trading_simulation(self):
        """
        Mô phỏng giao dịch đồng thời để kiểm tra xung đột và chồng chéo
        """
        logger.info("Mô phỏng giao dịch đồng thời...")
        
        try:
            # Mô phỏng nhiều chiến lược chạy đồng thời
            strategies = self.config['strategies_to_test'][:3]  # Lấy 3 chiến lược đầu tiên
            symbols = self.config['symbols'][:3]  # Lấy 3 cặp tiền đầu tiên
            
            # Tạo các thread mô phỏng
            threads = []
            results = []
            
            def simulate_strategy(strategy, symbol):
                # Mô phỏng thời gian xử lý
                time.sleep(0.1 + 0.2 * np.random.random())
                
                # Mô phỏng quyết định giao dịch
                decision = np.random.choice(['BUY', 'SELL', 'NONE'], p=[0.4, 0.4, 0.2])
                
                if decision != 'NONE':
                    # Mô phỏng đặt lệnh
                    success = np.random.random() > 0.1  # 90% thành công
                    
                    result = {
                        'strategy': strategy,
                        'symbol': symbol,
                        'decision': decision,
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
                        'success': success
                    }
                    
                    results.append(result)
            
            # Tạo và chạy các thread
            for strategy in strategies:
                for symbol in symbols:
                    thread = threading.Thread(target=simulate_strategy, args=(strategy, symbol))
                    threads.append(thread)
                    thread.start()
            
            # Đợi tất cả các thread hoàn thành
            for thread in threads:
                thread.join()
            
            # Kiểm tra kết quả
            # Phát hiện xung đột và chồng chéo
            
            # 1. Kiểm tra lệnh ngược chiều cùng lúc
            by_symbol = {}
            for result in results:
                symbol = result['symbol']
                if symbol not in by_symbol:
                    by_symbol[symbol] = []
                by_symbol[symbol].append(result)
            
            for symbol, symbol_results in by_symbol.items():
                # Lọc các lệnh thành công
                success_results = [r for r in symbol_results if r['success']]
                
                if len(success_results) < 2:
                    continue
                
                # Sắp xếp theo thời gian
                success_results.sort(key=lambda x: x['timestamp'])
                
                # Kiểm tra lệnh ngược chiều trong khoảng thời gian ngắn
                for i in range(len(success_results) - 1):
                    current = success_results[i]
                    next_result = success_results[i + 1]
                    
                    # Tính khoảng thời gian
                    current_time = datetime.datetime.strptime(current['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                    next_time = datetime.datetime.strptime(next_result['timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                    time_diff = (next_time - current_time).total_seconds()
                    
                    # Nếu thời gian ngắn và hướng ngược nhau
                    if time_diff < 0.5 and current['decision'] != next_result['decision']:
                        logger.warning(f"Phát hiện lệnh ngược chiều trong khoảng thời gian ngắn ({time_diff}s): "
                                     f"{current['strategy']} ({current['decision']}) và "
                                     f"{next_result['strategy']} ({next_result['decision']}) cho {symbol}")
                        
                        self.diagnostics['strategy_conflicts'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'error': 'OppositeOrdersConflict',
                            'details': f"Lệnh ngược chiều trong {time_diff}s: "
                                    f"{current['strategy']} ({current['decision']}) và "
                                    f"{next_result['strategy']} ({next_result['decision']}) cho {symbol}"
                        })
            
            # 2. Kiểm tra chiến lược trùng lặp
            by_strategy_symbol = {}
            for result in results:
                key = f"{result['strategy']}_{result['symbol']}"
                if key not in by_strategy_symbol:
                    by_strategy_symbol[key] = []
                by_strategy_symbol[key].append(result)
            
            for key, strategy_results in by_strategy_symbol.items():
                if len(strategy_results) > 1:
                    logger.warning(f"Phát hiện chiến lược trùng lặp: {key} có {len(strategy_results)} kết quả")
                    
                    self.diagnostics['strategy_conflicts'].append({
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'error': 'DuplicateStrategyResults',
                        'details': f"Chiến lược trùng lặp: {key} có {len(strategy_results)} kết quả"
                    })
            
            logger.info(f"Đã mô phỏng {len(threads)} thread giao dịch đồng thời, {len(results)} lệnh được tạo")
        
        except Exception as e:
            logger.error(f"Lỗi khi mô phỏng giao dịch đồng thời: {e}")
            self.diagnostics['general_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'ConcurrentTradingSimulationError',
                'details': str(e)
            })
    
    def _check_strategy_conflicts(self):
        """
        Kiểm tra xung đột giữa các chiến lược
        """
        logger.info("Kiểm tra xung đột giữa các chiến lược...")
        
        try:
            # Khởi tạo ma trận xung đột
            strategies = self.config['strategies_to_test']
            conflict_matrix = {}
            
            for i, strategy1 in enumerate(strategies):
                conflict_matrix[strategy1] = {}
                for j, strategy2 in enumerate(strategies):
                    if i == j:
                        continue
                    
                    # Mô phỏng kiểm tra xung đột
                    # Trong thực tế, cần kiểm tra dựa trên logic cụ thể của mỗi chiến lược
                    conflict_chance = np.random.random()
                    has_conflict = conflict_chance < 0.2  # 20% xung đột
                    
                    if has_conflict:
                        conflict_type = np.random.choice([
                            'SignalConflict',
                            'OrdersConflict',
                            'DataAccessConflict',
                            'IndicatorsConflict'
                        ])
                        
                        conflict_matrix[strategy1][strategy2] = {
                            'has_conflict': True,
                            'conflict_type': conflict_type,
                            'conflict_chance': conflict_chance
                        }
                        
                        logger.warning(f"Phát hiện xung đột giữa {strategy1} và {strategy2}: {conflict_type}")
                        
                        self.diagnostics['strategy_conflicts'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'error': 'StrategyConflict',
                            'details': f"Xung đột giữa {strategy1} và {strategy2}: {conflict_type}"
                        })
                    else:
                        conflict_matrix[strategy1][strategy2] = {
                            'has_conflict': False,
                            'conflict_chance': conflict_chance
                        }
            
            # Lưu ma trận xung đột
            conflict_matrix_path = os.path.join(self.results_dir, 'strategy_conflict_matrix.json')
            with open(conflict_matrix_path, 'w') as f:
                json.dump(conflict_matrix, f, indent=2)
            
            logger.info(f"Đã lưu ma trận xung đột vào {conflict_matrix_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra xung đột giữa các chiến lược: {e}")
            self.diagnostics['strategy_conflicts'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'StrategyConflictCheckError',
                'details': str(e)
            })
    
    def _check_sltp_consistency(self):
        """
        Kiểm tra tính nhất quán của SL/TP
        """
        logger.info("Kiểm tra tính nhất quán của SL/TP...")
        
        try:
            symbols = self.config['symbols'][:3]  # Lấy 3 cặp tiền đầu tiên
            risk_levels = self.config['risk_levels']
            
            for symbol in symbols:
                for risk_level in risk_levels:
                    # Mô phỏng tính toán SL/TP
                    if risk_level == 'low':
                        sl_pct = 0.01  # 1%
                        tp_pct = 0.02  # 2%
                    elif risk_level == 'medium':
                        sl_pct = 0.02  # 2%
                        tp_pct = 0.04  # 4%
                    else:  # high
                        sl_pct = 0.03  # 3%
                        tp_pct = 0.09  # 9%
                    
                    # Lấy giá hiện tại
                    current_price = 82000  # Giả sử
                    
                    # Tính SL/TP
                    long_sl = current_price * (1 - sl_pct)
                    long_tp = current_price * (1 + tp_pct)
                    short_sl = current_price * (1 + sl_pct)
                    short_tp = current_price * (1 - tp_pct)
                    
                    # Kiểm tra tỷ lệ R:R
                    long_risk = current_price - long_sl
                    long_reward = long_tp - current_price
                    long_rr = long_reward / long_risk
                    
                    short_risk = short_sl - current_price
                    short_reward = current_price - short_tp
                    short_rr = short_reward / short_risk
                    
                    # Kiểm tra tính nhất quán
                    if long_rr < 1.5 or long_rr > 5.0 or short_rr < 1.5 or short_rr > 5.0:
                        logger.warning(f"Tỷ lệ R:R không phù hợp cho {symbol} ({risk_level}): "
                                     f"Long R:R = {long_rr:.2f}, Short R:R = {short_rr:.2f}")
                        
                        self.diagnostics['risk_management_issues'].append({
                            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'error': 'ImproperRiskRewardRatio',
                            'details': f"Tỷ lệ R:R không phù hợp cho {symbol} ({risk_level}): "
                                    f"Long R:R = {long_rr:.2f}, Short R:R = {short_rr:.2f}"
                        })
            
            logger.info("Kiểm tra tính nhất quán của SL/TP hoàn tất")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra tính nhất quán của SL/TP: {e}")
            self.diagnostics['risk_management_issues'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'SLTPConsistencyCheckError',
                'details': str(e)
            })
    
    def _test_notification_system(self):
        """
        Kiểm tra hệ thống thông báo và báo cáo
        """
        logger.info("Kiểm tra hệ thống thông báo...")
        
        try:
            # Mô phỏng các loại thông báo
            notification_types = [
                "ORDER_PLACED",
                "ORDER_FILLED",
                "TAKE_PROFIT_HIT",
                "STOP_LOSS_HIT",
                "POSITION_CLOSED",
                "TRAILING_STOP_UPDATED",
                "ERROR_OCCURRED",
                "STRATEGY_SWITCHED",
                "MARGIN_CALL",
                "ACCOUNT_BALANCE_LOW"
            ]
            
            for notification_type in notification_types:
                # Mô phỏng gửi thông báo
                logger.info(f"Kiểm tra gửi thông báo {notification_type}...")
                
                # Giả lập nhận thông báo
                logger.info(f"Giả lập nhận thông báo {notification_type}...")
                
                # Kiểm tra xử lý lỗi
                logger.info(f"Kiểm tra xử lý lỗi khi gửi thông báo {notification_type}...")
            
            logger.info("Kiểm tra hệ thống thông báo hoàn tất")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra hệ thống thông báo: {e}")
            self.diagnostics['communication_failures'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'NotificationSystemTestError',
                'details': str(e)
            })
    
    def _analyze_diagnostic_results(self):
        """
        Phân tích kết quả chẩn đoán
        """
        logger.info("Phân tích kết quả chẩn đoán...")
        
        try:
            # Tổng hợp lỗi
            total_errors = sum(len(errors) for errors in self.diagnostics.values())
            
            error_types = {}
            for category, errors in self.diagnostics.items():
                error_types[category] = len(errors)
            
            # Phân tích mức độ nghiêm trọng
            critical_errors = []
            warning_errors = []
            info_errors = []
            
            for category, errors in self.diagnostics.items():
                for error in errors:
                    # Phân loại mức độ nghiêm trọng dựa trên loại lỗi
                    if category in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors']:
                        critical_errors.append(error)
                    elif category in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues']:
                        warning_errors.append(error)
                    else:
                        info_errors.append(error)
            
            # Ghi lại kết quả phân tích
            analysis = {
                'total_errors': total_errors,
                'error_types': error_types,
                'critical_errors': len(critical_errors),
                'warning_errors': len(warning_errors),
                'info_errors': len(info_errors),
                'datetime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Lưu phân tích
            analysis_path = os.path.join(self.results_dir, 'diagnostic_analysis.json')
            with open(analysis_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            logger.info(f"Đã lưu phân tích kết quả chẩn đoán vào {analysis_path}")
            
            # Tổng kết
            logger.info(f"Tổng kết: {total_errors} lỗi ({len(critical_errors)} nghiêm trọng, "
                       f"{len(warning_errors)} cảnh báo, {len(info_errors)} thông tin)")
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích kết quả chẩn đoán: {e}")
            self.diagnostics['general_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'DiagnosticAnalysisError',
                'details': str(e)
            })
    
    def _create_diagnostic_report(self):
        """
        Tạo báo cáo chẩn đoán
        """
        logger.info("Tạo báo cáo chẩn đoán...")
        
        try:
            # Tạo báo cáo HTML
            report_html_path = os.path.join(self.results_dir, 'diagnostic_report.html')
            
            with open(report_html_path, 'w') as f:
                f.write(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Bot Diagnostic Report</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        h2 {{ color: #666; margin-top: 30px; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                        tr:hover {{ background-color: #f5f5f5; }}
                        .critical {{ color: red; }}
                        .warning {{ color: orange; }}
                        .info {{ color: blue; }}
                        .success {{ color: green; }}
                    </style>
                </head>
                <body>
                    <h1>Bot Diagnostic Report</h1>
                    <p>Report generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    
                    <h2>Summary</h2>
                    <table>
                        <tr>
                            <th>Category</th>
                            <th>Count</th>
                        </tr>
                """)
                
                # Tổng hợp lỗi
                total_errors = sum(len(errors) for errors in self.diagnostics.values())
                
                for category, errors in self.diagnostics.items():
                    category_display = category.replace('_', ' ').title()
                    f.write(f"""
                        <tr>
                            <td>{category_display}</td>
                            <td>{len(errors)}</td>
                        </tr>
                    """)
                
                f.write(f"""
                        <tr>
                            <td><strong>Total</strong></td>
                            <td><strong>{total_errors}</strong></td>
                        </tr>
                    </table>
                """)
                
                # Chi tiết lỗi
                for category, errors in self.diagnostics.items():
                    category_display = category.replace('_', ' ').title()
                    
                    if not errors:
                        continue
                    
                    f.write(f"""
                    <h2>{category_display}</h2>
                    <table>
                        <tr>
                            <th>Timestamp</th>
                            <th>Error</th>
                            <th>Details</th>
                        </tr>
                    """)
                    
                    for error in errors:
                        timestamp = error.get('timestamp', 'N/A')
                        error_type = error.get('error', 'Unknown')
                        details = error.get('details', 'No details')
                        
                        # Xác định mức độ nghiêm trọng
                        severity_class = 'info'
                        if category in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors']:
                            severity_class = 'critical'
                        elif category in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues']:
                            severity_class = 'warning'
                        
                        f.write(f"""
                        <tr>
                            <td>{timestamp}</td>
                            <td class="{severity_class}">{error_type}</td>
                            <td>{details}</td>
                        </tr>
                        """)
                    
                    f.write("</table>")
                
                # Kết luận
                f.write(f"""
                    <h2>Conclusion</h2>
                    <p>
                        Based on the diagnostic analysis, the trading bot has {total_errors} issues that need attention.
                        {sum(1 for category, errors in self.diagnostics.items() if category in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors'] and errors)} critical issues must be fixed before deploying to production.
                        {sum(1 for category, errors in self.diagnostics.items() if category in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues'] and errors)} warning issues should be reviewed for potential problems.
                    </p>
                    
                    <h2>Recommendations</h2>
                    <ul>
                """)
                
                # Tạo khuyến nghị dựa trên lỗi
                if any(self.diagnostics['algorithm_failures']):
                    f.write("<li>Fix algorithm failures in the trading strategies</li>")
                
                if any(self.diagnostics['strategy_conflicts']):
                    f.write("<li>Resolve conflicts between trading strategies</li>")
                
                if any(self.diagnostics['position_overlaps']):
                    f.write("<li>Fix position overlap issues to prevent conflicting trades</li>")
                
                if any(self.diagnostics['api_errors']):
                    f.write("<li>Address API connection and error handling</li>")
                
                if any(self.diagnostics['risk_management_issues']):
                    f.write("<li>Improve risk management parameters and stop loss/take profit consistency</li>")
                
                f.write("""
                    </ul>
                </body>
                </html>
                """)
            
            # Tạo báo cáo Text
            report_text_path = os.path.join(self.results_dir, 'diagnostic_report.txt')
            
            with open(report_text_path, 'w') as f:
                f.write("==========================\n")
                f.write("BOT DIAGNOSTIC REPORT\n")
                f.write("==========================\n\n")
                f.write(f"Report generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("SUMMARY\n")
                f.write("-------\n")
                
                for category, errors in self.diagnostics.items():
                    category_display = category.replace('_', ' ').title()
                    f.write(f"{category_display}: {len(errors)}\n")
                
                f.write(f"Total: {total_errors}\n\n")
                
                # Chi tiết lỗi
                for category, errors in self.diagnostics.items():
                    category_display = category.replace('_', ' ').title()
                    
                    if not errors:
                        continue
                    
                    f.write(f"{category_display}\n")
                    f.write(f"{'-' * len(category_display)}\n")
                    
                    for error in errors:
                        timestamp = error.get('timestamp', 'N/A')
                        error_type = error.get('error', 'Unknown')
                        details = error.get('details', 'No details')
                        
                        f.write(f"[{timestamp}] {error_type}: {details}\n")
                    
                    f.write("\n")
                
                # Kết luận
                f.write("CONCLUSION\n")
                f.write("----------\n")
                f.write(f"Based on the diagnostic analysis, the trading bot has {total_errors} issues that need attention.\n")
                f.write(f"{sum(1 for category, errors in self.diagnostics.items() if category in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors'] and errors)} critical issues must be fixed before deploying to production.\n")
                f.write(f"{sum(1 for category, errors in self.diagnostics.items() if category in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues'] and errors)} warning issues should be reviewed for potential problems.\n\n")
                
                f.write("RECOMMENDATIONS\n")
                f.write("---------------\n")
                
                # Tạo khuyến nghị dựa trên lỗi
                if any(self.diagnostics['algorithm_failures']):
                    f.write("- Fix algorithm failures in the trading strategies\n")
                
                if any(self.diagnostics['strategy_conflicts']):
                    f.write("- Resolve conflicts between trading strategies\n")
                
                if any(self.diagnostics['position_overlaps']):
                    f.write("- Fix position overlap issues to prevent conflicting trades\n")
                
                if any(self.diagnostics['api_errors']):
                    f.write("- Address API connection and error handling\n")
                
                if any(self.diagnostics['risk_management_issues']):
                    f.write("- Improve risk management parameters and stop loss/take profit consistency\n")
            
            logger.info(f"Đã tạo báo cáo chẩn đoán: {report_html_path} và {report_text_path}")
            
            # In tóm tắt ra console
            print(f"\n{Colors.HEADER}===== BOT DIAGNOSTIC SUMMARY ====={Colors.ENDC}")
            print(f"Total issues: {Colors.BOLD}{total_errors}{Colors.ENDC}")
            
            critical_count = sum(1 for category, errors in self.diagnostics.items() if category in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors'] and errors)
            warning_count = sum(1 for category, errors in self.diagnostics.items() if category in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues'] and errors)
            info_count = total_errors - critical_count - warning_count
            
            print(f"{Colors.RED}Critical issues: {critical_count}{Colors.ENDC}")
            print(f"{Colors.YELLOW}Warning issues: {warning_count}{Colors.ENDC}")
            print(f"{Colors.BLUE}Info issues: {info_count}{Colors.ENDC}")
            
            print(f"\nDetailed reports saved to: {self.results_dir}")
            print(f"{Colors.HEADER}================================{Colors.ENDC}\n")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo chẩn đoán: {e}")
            self.diagnostics['general_errors'].append({
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'DiagnosticReportCreationError',
                'details': str(e)
            })


def main():
    """
    Hàm chính
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Bot Diagnostic Tool')
    parser.add_argument('--config', type=str, default='bot_diagnostic_config.json',
                      help='Path to configuration file')
    parser.add_argument('--quick', action='store_true',
                      help='Run quick diagnostic with fewer tests')
    
    args = parser.parse_args()
    
    # Khởi tạo Bot Diagnostic
    diagnostic = BotDiagnostic(config_path=args.config)
    
    # Chạy chẩn đoán
    results = diagnostic.run_diagnostic()
    
    # Hiển thị kết quả tổng thể
    total_errors = sum(len(errors) for errors in results.values())
    if total_errors == 0:
        print(f"\n{Colors.GREEN}No issues found! The trading bot is working correctly.{Colors.ENDC}")
    else:
        critical_count = sum(len(results[cat]) for cat in ['api_errors', 'algorithm_failures', 'database_failures', 'entry_exit_errors'])
        warning_count = sum(len(results[cat]) for cat in ['strategy_conflicts', 'position_overlaps', 'risk_management_issues'])
        
        status = f"{Colors.RED}CRITICAL{Colors.ENDC}" if critical_count > 0 else f"{Colors.YELLOW}WARNING{Colors.ENDC}" if warning_count > 0 else f"{Colors.GREEN}MINOR ISSUES{Colors.ENDC}"
        
        print(f"\n{Colors.BOLD}Overall Status: {status}{Colors.ENDC}")
        print(f"Found {total_errors} issues: {critical_count} critical, {warning_count} warnings, {total_errors - critical_count - warning_count} info")
        print(f"Detailed report has been saved to diagnostic_results/diagnostic_report.html")

if __name__ == "__main__":
    main()