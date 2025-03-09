#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra toàn diện bot giao dịch với dữ liệu thị trường thật

Script này thực hiện:
1. Kết nối với Binance API để lấy dữ liệu thị trường thực
2. Theo dõi bot phản ứng với các chế độ thị trường khác nhau
3. Phân tích chi tiết việc bot tự chọn thuật toán cho từng trường hợp
4. Tạo báo cáo chi tiết về hoạt động của toàn bộ hệ thống
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("comprehensive_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load môi trường
load_dotenv()

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
    from market_regime_ml_optimized import (
        MarketRegimeDetector, AdaptiveTrader, StrategySelector, 
        BollingerBandsStrategy, RSIStrategy, MACDStrategy, EMACrossStrategy, 
        ADXStrategy, Strategy, CompositeStrategy
    )
    from data_processor import DataProcessor
except ImportError as e:
    logger.error(f"Không thể import module: {str(e)}")
    sys.exit(1)

class ComprehensiveTester:
    """Lớp kiểm tra toàn diện bot giao dịch"""
    
    def __init__(self, symbols=None, timeframes=None, test_duration_hours=24, 
                data_dir='test_data', report_dir='reports', chart_dir='backtest_charts'):
        """
        Khởi tạo tester
        
        Args:
            symbols (list): Danh sách các cặp tiền
            timeframes (list): Danh sách khung thời gian
            test_duration_hours (int): Thời lượng kiểm tra (giờ)
            data_dir (str): Thư mục dữ liệu
            report_dir (str): Thư mục báo cáo
            chart_dir (str): Thư mục biểu đồ
        """
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.timeframes = timeframes or ['1h', '4h', '1d']
        self.test_duration_hours = test_duration_hours
        self.data_dir = data_dir
        self.report_dir = report_dir
        self.chart_dir = chart_dir
        
        # Đảm bảo các thư mục tồn tại
        for directory in [data_dir, report_dir, chart_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Khởi tạo các thành phần
        self.api_key = os.environ.get('BINANCE_API_KEY')
        self.api_secret = os.environ.get('BINANCE_API_SECRET')
        
        if not self.api_key or not self.api_secret:
            logger.warning("API key hoặc secret không tồn tại. Sử dụng mode mô phỏng.")
            self.use_real_api = False
            self.binance_api = None
        else:
            self.use_real_api = True
            try:
                self.binance_api = BinanceAPI(api_key=self.api_key, api_secret=self.api_secret, testnet=True)
                logger.info("Đã kết nối thành công với Binance API (testnet)")
            except Exception as e:
                logger.error(f"Lỗi khi kết nối Binance API: {str(e)}")
                self.use_real_api = False
                self.binance_api = None
        
        self.data_processor = DataProcessor(binance_api=self.binance_api)
        
        # Khởi tạo bot cho từng cặp tiền
        self.regime_detectors = {}
        self.strategy_selectors = {}
        self.adaptive_traders = {}
        
        for symbol in self.symbols:
            self.regime_detectors[symbol] = MarketRegimeDetector()
            self.strategy_selectors[symbol] = StrategySelector()
            self.adaptive_traders[symbol] = AdaptiveTrader(
                regime_detector=self.regime_detectors[symbol],
                strategy_selector=self.strategy_selectors[symbol]
            )
        
        # Dữ liệu lịch sử
        self.historical_data = {}
        
        # Dữ liệu theo dõi
        self.test_data = {
            'start_time': datetime.now(),
            'iterations': 0,
            'by_symbol': {}
        }
        
        for symbol in self.symbols:
            self.test_data['by_symbol'][symbol] = {
                'regime_counts': {},
                'signal_counts': {},
                'strategy_usage': {},
                'decisions': [],
                'iterations': 0
            }
    
    def load_historical_data(self):
        """Tải dữ liệu lịch sử từ Binance hoặc từ file"""
        logger.info("Đang tải dữ liệu lịch sử...")
        
        for symbol in self.symbols:
            self.historical_data[symbol] = {}
            
            for timeframe in self.timeframes:
                try:
                    # Thử tải từ file trước
                    file_path = os.path.join(self.data_dir, f"{symbol}_{timeframe}.csv")
                    
                    if os.path.exists(file_path):
                        df = pd.read_csv(file_path)
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                        logger.info(f"Đã tải dữ liệu {symbol} {timeframe} từ file ({len(df)} nến)")
                    elif self.use_real_api:
                        # Tải từ Binance nếu không có file
                        start_time = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                        
                        df = self.data_processor.download_historical_data(
                            symbol=symbol,
                            interval=timeframe,
                            start_time=start_time,
                            save_to_file=True,
                            output_dir=self.data_dir
                        )
                        
                        logger.info(f"Đã tải dữ liệu {symbol} {timeframe} từ Binance ({len(df)} nến)")
                    else:
                        # Tạo dữ liệu mô phỏng nếu không có API
                        df = self._generate_simulated_data(symbol, timeframe)
                        logger.info(f"Đã tạo dữ liệu mô phỏng cho {symbol} {timeframe} ({len(df)} nến)")
                    
                    # Thêm các chỉ báo kỹ thuật
                    df = self.data_processor.add_indicators(df)
                    
                    self.historical_data[symbol][timeframe] = df
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {str(e)}")
                    continue
    
    def _generate_simulated_data(self, symbol, timeframe, days=30):
        """
        Tạo dữ liệu mô phỏng khi không có API
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            days (int): Số ngày dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame dữ liệu mô phỏng
        """
        # Xác định tham số dựa trên symbol
        if symbol == 'BTCUSDT':
            base_price = 60000
            volatility = 0.02
        elif symbol == 'ETHUSDT':
            base_price = 3500
            volatility = 0.025
        else:
            base_price = 100
            volatility = 0.03
        
        # Xác định số nến dựa trên timeframe
        if timeframe == '1h':
            periods = days * 24
            freq = 'H'
        elif timeframe == '4h':
            periods = days * 6
            freq = '4H'
        else:  # 1d
            periods = days
            freq = 'D'
        
        # Tạo thời gian
        start_date = datetime.now() - timedelta(days=days)
        date_range = pd.date_range(start=start_date, periods=periods, freq=freq)
        
        # Tạo giá với random walk
        np.random.seed(hash(symbol + timeframe) % 2**32)
        
        # Tạo các giai đoạn thị trường khác nhau
        regimes = ['trending', 'ranging', 'volatile', 'quiet']
        regime_lengths = np.random.randint(periods // 10, periods // 5, size=len(regimes))
        
        # Đảm bảo tổng độ dài không vượt quá số nến
        if sum(regime_lengths) > periods:
            scale_factor = periods / sum(regime_lengths)
            regime_lengths = (regime_lengths * scale_factor).astype(int)
        
        remaining_length = periods - sum(regime_lengths)
        current_regime_idx = 0
        if remaining_length > 0 and current_regime_idx < len(regime_lengths):
            regime_lengths[current_regime_idx] += remaining_length
        
        # Khởi tạo dữ liệu giá
        price_data = []
        current_price = base_price
        current_regime = regimes[0]
        
        for i in range(periods):
            # Xác định chế độ thị trường hiện tại
            for j, length in enumerate(regime_lengths):
                if i < sum(regime_lengths[:j+1]):
                    current_regime = regimes[j]
                    break
            
            # Điều chỉnh volatility và drift theo chế độ thị trường
            if current_regime == 'trending':
                local_volatility = volatility * 0.8
                local_drift = 0.001
            elif current_regime == 'ranging':
                local_volatility = volatility * 0.6
                local_drift = 0.0
            elif current_regime == 'volatile':
                local_volatility = volatility * 1.5
                local_drift = 0.0
            else:  # quiet
                local_volatility = volatility * 0.3
                local_drift = 0.0
            
            # Random walk với drift
            price_change = np.random.normal(local_drift, local_volatility)
            
            # Thêm spike với xác suất thấp
            spike_prob = 0.01
            if np.random.random() < spike_prob:
                price_change += np.random.choice([-1, 1]) * local_volatility * 5
            
            # Cập nhật giá
            current_price *= (1 + price_change)
            
            # Tạo OHLCV
            high_price = current_price * (1 + np.random.uniform(0, local_volatility))
            low_price = current_price * (1 - np.random.uniform(0, local_volatility))
            open_price = current_price * (1 + np.random.uniform(-local_volatility/2, local_volatility/2))
            volume = np.random.exponential(100) * (1 + np.random.uniform(-0.5, 0.5))
            
            # Thêm vào dữ liệu
            price_data.append({
                'timestamp': date_range[i],
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': current_price,
                'volume': volume,
                'regime': current_regime  # Thêm chế độ thị trường thật để so sánh
            })
        
        # Tạo DataFrame
        df = pd.DataFrame(price_data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def update_market_data(self):
        """Cập nhật dữ liệu thị trường mới nhất"""
        logger.info("Đang cập nhật dữ liệu thị trường...")
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                try:
                    if self.use_real_api:
                        # Lấy dữ liệu mới từ Binance
                        new_candles = self.binance_api.get_klines(
                            symbol=symbol,
                            interval=timeframe,
                            limit=10  # Chỉ lấy 10 nến gần nhất
                        )
                        
                        if not new_candles:
                            logger.warning(f"Không có dữ liệu mới cho {symbol} {timeframe}")
                            continue
                        
                        # Chuyển đổi thành DataFrame
                        new_df = self.binance_api.convert_klines_to_dataframe(new_candles)
                        
                        # Cập nhật dữ liệu lịch sử
                        df = self.historical_data[symbol][timeframe]
                        
                        # Loại bỏ các nến trùng lặp và thêm nến mới
                        df = pd.concat([df, new_df]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
                        
                    else:
                        # Trong mode mô phỏng, thêm 1-2 nến mới với biến động nhỏ
                        df = self.historical_data[symbol][timeframe]
                        last_row = df.iloc[-1].copy()
                        
                        # Xác định timestamp mới
                        if timeframe == '1h':
                            new_timestamp = last_row.name + timedelta(hours=1)
                        elif timeframe == '4h':
                            new_timestamp = last_row.name + timedelta(hours=4)
                        else:  # 1d
                            new_timestamp = last_row.name + timedelta(days=1)
                        
                        # Tạo giá mới với biến động nhỏ
                        price_change = np.random.normal(0, 0.005)  # 0.5% biến động
                        new_close = last_row['close'] * (1 + price_change)
                        new_high = max(new_close, last_row['close']) * (1 + np.random.uniform(0, 0.002))
                        new_low = min(new_close, last_row['close']) * (1 - np.random.uniform(0, 0.002))
                        new_open = last_row['close']
                        new_volume = last_row['volume'] * (1 + np.random.uniform(-0.1, 0.1))
                        
                        # Tạo DataFrame mới
                        new_data = pd.DataFrame({
                            'open': [new_open],
                            'high': [new_high],
                            'low': [new_low],
                            'close': [new_close],
                            'volume': [new_volume]
                        }, index=[new_timestamp])
                        
                        # Cập nhật DataFrame
                        df = pd.concat([df, new_data])
                    
                    # Thêm các chỉ báo kỹ thuật
                    df = self.data_processor.add_indicators(df)
                    
                    # Cập nhật lại dữ liệu
                    self.historical_data[symbol][timeframe] = df
                    
                    logger.info(f"Đã cập nhật dữ liệu {symbol} {timeframe} - Nến mới nhất: {df.index[-1]}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi cập nhật dữ liệu {symbol} {timeframe}: {str(e)}")
                    continue
    
    def run_bot_test_iteration(self):
        """Chạy một vòng lặp kiểm tra bot"""
        logger.info("Chạy một vòng kiểm tra bot...")
        
        for symbol in self.symbols:
            try:
                # Lấy dữ liệu khung thời gian chính (1h)
                primary_tf = '1h'
                df = self.historical_data[symbol][primary_tf]
                
                if df.empty:
                    logger.warning(f"Không có dữ liệu cho {symbol} {primary_tf}")
                    continue
                
                # Phát hiện chế độ thị trường
                regime_detector = self.regime_detectors[symbol]
                current_regime = regime_detector.detect_regime(df)
                
                # Cập nhật số lần xuất hiện mỗi chế độ
                if current_regime in self.test_data['by_symbol'][symbol]['regime_counts']:
                    self.test_data['by_symbol'][symbol]['regime_counts'][current_regime] += 1
                else:
                    self.test_data['by_symbol'][symbol]['regime_counts'][current_regime] = 1
                
                # Lấy chiến lược tối ưu cho chế độ thị trường hiện tại
                strategy_selector = self.strategy_selectors[symbol]
                optimal_strategies = strategy_selector.get_strategies_for_regime(current_regime)
                
                # Cập nhật việc sử dụng chiến lược
                for strategy_name, weight in optimal_strategies.items():
                    if strategy_name in self.test_data['by_symbol'][symbol]['strategy_usage']:
                        self.test_data['by_symbol'][symbol]['strategy_usage'][strategy_name] += 1
                    else:
                        self.test_data['by_symbol'][symbol]['strategy_usage'][strategy_name] = 1
                
                # Lấy tín hiệu giao dịch từ bot thích ứng
                adaptive_trader = self.adaptive_traders[symbol]
                signal = adaptive_trader.generate_signal(df)
                
                # Ghi nhận tín hiệu
                if isinstance(signal, dict) and 'action' in signal:
                    action = signal['action']
                else:
                    action = signal
                
                if action in self.test_data['by_symbol'][symbol]['signal_counts']:
                    self.test_data['by_symbol'][symbol]['signal_counts'][action] += 1
                else:
                    self.test_data['by_symbol'][symbol]['signal_counts'][action] = 1
                
                # Lấy thông tin chi tiết về các chiến lược được sử dụng
                strategy_details = {}
                if hasattr(adaptive_trader, 'current_strategy') and adaptive_trader.current_strategy:
                    if hasattr(adaptive_trader.current_strategy, 'strategies'):
                        for name, strategy in adaptive_trader.current_strategy.strategies.items():
                            strategy_details[name] = {
                                'signal': strategy.generate_signal(df),
                                'weight': adaptive_trader.current_strategy.strategy_weights.get(name, 0)
                            }
                
                # Ghi nhận quyết định
                timestamp = datetime.now()
                current_price = df['close'].iloc[-1]
                
                decision = {
                    'timestamp': timestamp,
                    'iteration': self.test_data['iterations'],
                    'regime': current_regime,
                    'action': action,
                    'price': current_price,
                    'strategies': optimal_strategies,
                    'strategy_details': strategy_details,
                    'indicators': {
                        'rsi': df['rsi'].iloc[-1] if 'rsi' in df.columns else None,
                        'macd': df['macd'].iloc[-1] if 'macd' in df.columns else None,
                        'bb_width': ((df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1]) / df['bb_middle'].iloc[-1]) 
                                    if all(x in df.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']) else None,
                        'adx': df['adx'].iloc[-1] if 'adx' in df.columns else None
                    }
                }
                
                self.test_data['by_symbol'][symbol]['decisions'].append(decision)
                
                # Cập nhật số lần kiểm tra
                self.test_data['by_symbol'][symbol]['iterations'] += 1
                
                logger.info(f"{symbol}: Chế độ: {current_regime}, Hành động: {action}")
                logger.info(f"Chiến lược được chọn: {optimal_strategies}")
                
            except Exception as e:
                logger.error(f"Lỗi khi chạy bot cho {symbol}: {str(e)}")
                continue
        
        # Cập nhật tổng số lần kiểm tra
        self.test_data['iterations'] += 1
    
    def create_regime_detection_chart(self, symbol, output_dir=None):
        """
        Tạo biểu đồ phân bố chế độ thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            output_dir (str): Thư mục đầu ra
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        if output_dir is None:
            output_dir = self.chart_dir
        
        if symbol not in self.test_data['by_symbol']:
            logger.error(f"Không có dữ liệu test cho {symbol}")
            return None
        
        regime_counts = self.test_data['by_symbol'][symbol]['regime_counts']
        
        if not regime_counts:
            logger.warning(f"Không có dữ liệu chế độ thị trường cho {symbol}")
            return None
        
        try:
            # Tạo biểu đồ pie
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(regime_counts.values(), labels=regime_counts.keys(), autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            plt.title(f"Phân bố chế độ thị trường - {symbol}")
            
            # Lưu biểu đồ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"{symbol}_regime_distribution_{timestamp}.png")
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ phân bố chế độ thị trường cho {symbol}: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ chế độ thị trường cho {symbol}: {str(e)}")
            return None
    
    def create_strategy_usage_chart(self, symbol, output_dir=None):
        """
        Tạo biểu đồ sử dụng chiến lược
        
        Args:
            symbol (str): Mã cặp tiền
            output_dir (str): Thư mục đầu ra
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        if output_dir is None:
            output_dir = self.chart_dir
        
        if symbol not in self.test_data['by_symbol']:
            logger.error(f"Không có dữ liệu test cho {symbol}")
            return None
        
        strategy_usage = self.test_data['by_symbol'][symbol]['strategy_usage']
        
        if not strategy_usage:
            logger.warning(f"Không có dữ liệu sử dụng chiến lược cho {symbol}")
            return None
        
        try:
            # Tạo biểu đồ bar
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(strategy_usage.keys(), strategy_usage.values())
            plt.title(f"Sử dụng chiến lược - {symbol}")
            plt.xlabel("Chiến lược")
            plt.ylabel("Số lần sử dụng")
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Lưu biểu đồ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"{symbol}_strategy_usage_{timestamp}.png")
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ sử dụng chiến lược cho {symbol}: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ sử dụng chiến lược cho {symbol}: {str(e)}")
            return None
    
    def create_signal_distribution_chart(self, symbol, output_dir=None):
        """
        Tạo biểu đồ phân bố tín hiệu giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            output_dir (str): Thư mục đầu ra
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        if output_dir is None:
            output_dir = self.chart_dir
        
        if symbol not in self.test_data['by_symbol']:
            logger.error(f"Không có dữ liệu test cho {symbol}")
            return None
        
        signal_counts = self.test_data['by_symbol'][symbol]['signal_counts']
        
        if not signal_counts:
            logger.warning(f"Không có dữ liệu tín hiệu giao dịch cho {symbol}")
            return None
        
        try:
            # Tạo biểu đồ pie
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(signal_counts.values(), labels=signal_counts.keys(), autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            plt.title(f"Phân bố tín hiệu giao dịch - {symbol}")
            
            # Lưu biểu đồ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"{symbol}_signal_distribution_{timestamp}.png")
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ phân bố tín hiệu giao dịch cho {symbol}: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân bố tín hiệu giao dịch cho {symbol}: {str(e)}")
            return None
    
    def create_strategy_by_regime_chart(self, symbol, output_dir=None):
        """
        Tạo biểu đồ phân bố chiến lược theo chế độ thị trường
        
        Args:
            symbol (str): Mã cặp tiền
            output_dir (str): Thư mục đầu ra
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        if output_dir is None:
            output_dir = self.chart_dir
        
        if symbol not in self.test_data['by_symbol']:
            logger.error(f"Không có dữ liệu test cho {symbol}")
            return None
        
        decisions = self.test_data['by_symbol'][symbol]['decisions']
        
        if not decisions:
            logger.warning(f"Không có dữ liệu quyết định cho {symbol}")
            return None
        
        try:
            # Phân tích chiến lược theo chế độ thị trường
            strategy_by_regime = {}
            
            for decision in decisions:
                regime = decision['regime']
                
                if regime not in strategy_by_regime:
                    strategy_by_regime[regime] = {}
                
                for strategy, _ in decision['strategies'].items():
                    if strategy not in strategy_by_regime[regime]:
                        strategy_by_regime[regime][strategy] = 0
                    
                    strategy_by_regime[regime][strategy] += 1
            
            # Tạo biểu đồ
            fig, ax = plt.subplots(figsize=(12, 8))
            
            regimes = list(strategy_by_regime.keys())
            unique_strategies = set()
            for regime_data in strategy_by_regime.values():
                unique_strategies.update(regime_data.keys())
            
            unique_strategies = list(unique_strategies)
            
            x = np.arange(len(regimes))
            width = 0.8 / len(unique_strategies)
            
            for i, strategy in enumerate(unique_strategies):
                values = [strategy_by_regime[regime].get(strategy, 0) for regime in regimes]
                ax.bar(x + i * width, values, width, label=strategy)
            
            ax.set_xlabel('Chế độ thị trường')
            ax.set_ylabel('Số lần sử dụng')
            ax.set_title(f'Chiến lược theo chế độ thị trường - {symbol}')
            ax.set_xticks(x + width * (len(unique_strategies) - 1) / 2)
            ax.set_xticklabels(regimes)
            ax.legend()
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"{symbol}_strategy_by_regime_{timestamp}.png")
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ chiến lược theo chế độ thị trường cho {symbol}: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ chiến lược theo chế độ thị trường cho {symbol}: {str(e)}")
            return None

    def generate_comprehensive_report(self):
        """
        Tạo báo cáo tổng hợp về kết quả kiểm tra
        
        Returns:
            Dict: Thông tin về báo cáo đã tạo
        """
        # Tạo báo cáo JSON
        report_data = {
            'test_summary': {
                'start_time': self.test_data['start_time'],
                'end_time': datetime.now(),
                'duration_hours': (datetime.now() - self.test_data['start_time']).total_seconds() / 3600,
                'iterations': self.test_data['iterations'],
                'symbols_tested': self.symbols,
                'timeframes': self.timeframes
            },
            'by_symbol': {}
        }
        
        charts = {}
        
        # Xử lý dữ liệu từng cặp tiền
        for symbol in self.symbols:
            symbol_data = self.test_data['by_symbol'][symbol]
            
            # Tạo các biểu đồ
            charts[symbol] = {
                'regime_distribution': self.create_regime_detection_chart(symbol),
                'strategy_usage': self.create_strategy_usage_chart(symbol),
                'signal_distribution': self.create_signal_distribution_chart(symbol),
                'strategy_by_regime': self.create_strategy_by_regime_chart(symbol)
            }
            
            # Phân tích tương quan giữa chiến lược và chế độ thị trường
            strategy_regime_correlation = {}
            strategy_effectiveness = {}
            
            if symbol_data['decisions']:
                # Phân nhóm quyết định theo chế độ thị trường
                decisions_by_regime = {}
                
                for decision in symbol_data['decisions']:
                    regime = decision['regime']
                    
                    if regime not in decisions_by_regime:
                        decisions_by_regime[regime] = []
                    
                    decisions_by_regime[regime].append(decision)
                
                # Phân tích từng chế độ thị trường
                for regime, decisions in decisions_by_regime.items():
                    strategy_regime_correlation[regime] = {}
                    
                    # Đếm số lần sử dụng mỗi chiến lược trong chế độ này
                    strategy_counts = {}
                    
                    for decision in decisions:
                        for strategy, _ in decision['strategies'].items():
                            if strategy not in strategy_counts:
                                strategy_counts[strategy] = 0
                            
                            strategy_counts[strategy] += 1
                    
                    # Tính tỷ lệ phần trăm
                    total_decisions = len(decisions)
                    
                    if total_decisions > 0:
                        for strategy, count in strategy_counts.items():
                            strategy_regime_correlation[regime][strategy] = count / total_decisions * 100
            
            # Phân tích độ chính xác của quyết định
            # (Đánh giá hiệu quả yêu cầu thông tin về kết quả các giao dịch,
            # nên chúng ta chỉ phân tích cách chọn chiến lược ở đây)
            
            report_data['by_symbol'][symbol] = {
                'iterations': symbol_data['iterations'],
                'regime_counts': symbol_data['regime_counts'],
                'signal_counts': symbol_data['signal_counts'],
                'strategy_usage': symbol_data['strategy_usage'],
                'strategy_regime_correlation': strategy_regime_correlation,
                'strategy_effectiveness': strategy_effectiveness,
                'charts': {k: os.path.basename(v) if v else None for k, v in charts[symbol].items()}
            }
        
        # Tạo báo cáo tổng quát dạng văn bản
        text_report = []
        text_report.append("="*80)
        text_report.append("BÁO CÁO KIỂM TRA TOÀN DIỆN BOT GIAO DỊCH")
        text_report.append("="*80)
        text_report.append(f"Thời gian bắt đầu: {self.test_data['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        text_report.append(f"Thời gian kết thúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        text_report.append(f"Số vòng lặp: {self.test_data['iterations']}")
        text_report.append(f"Các cặp tiền: {', '.join(self.symbols)}")
        text_report.append(f"Các khung thời gian: {', '.join(self.timeframes)}")
        text_report.append("")
        
        for symbol in self.symbols:
            symbol_data = self.test_data['by_symbol'][symbol]
            
            text_report.append(f"PHÂN TÍCH CHO {symbol}")
            text_report.append("-"*50)
            
            # Phân bố chế độ thị trường
            text_report.append("\nPhân bố chế độ thị trường:")
            for regime, count in symbol_data['regime_counts'].items():
                text_report.append(f"  - {regime}: {count} lần")
            
            # Phân bố tín hiệu giao dịch
            text_report.append("\nPhân bố tín hiệu giao dịch:")
            for signal, count in symbol_data['signal_counts'].items():
                text_report.append(f"  - {signal}: {count} lần")
            
            # Sử dụng chiến lược
            text_report.append("\nSử dụng chiến lược:")
            for strategy, count in symbol_data['strategy_usage'].items():
                text_report.append(f"  - {strategy}: {count} lần")
            
            # Chiến lược theo chế độ thị trường
            if 'strategy_regime_correlation' in report_data['by_symbol'][symbol]:
                text_report.append("\nChiến lược theo chế độ thị trường:")
                for regime, strategies in report_data['by_symbol'][symbol]['strategy_regime_correlation'].items():
                    text_report.append(f"  Chế độ {regime}:")
                    for strategy, percentage in strategies.items():
                        text_report.append(f"    - {strategy}: {percentage:.1f}%")
            
            # Phân tích 3 quyết định gần nhất
            if symbol_data['decisions']:
                text_report.append("\nQuyết định gần nhất:")
                for i, decision in enumerate(symbol_data['decisions'][-3:]):
                    text_report.append(f"  Quyết định {i+1}:")
                    text_report.append(f"    - Thời gian: {decision['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                    text_report.append(f"    - Chế độ thị trường: {decision['regime']}")
                    text_report.append(f"    - Hành động: {decision['action']}")
                    text_report.append(f"    - Giá: {decision['price']}")
                    text_report.append(f"    - Chiến lược: {decision['strategies']}")
            
            text_report.append("")
        
        # Phần đánh giá tổng quát
        text_report.append("\nĐÁNH GIÁ TỔNG QUÁT")
        text_report.append("-"*50)
        
        # Đánh giá về việc phát hiện đa dạng chế độ thị trường
        unique_regimes = set()
        for symbol in self.symbols:
            unique_regimes.update(self.test_data['by_symbol'][symbol]['regime_counts'].keys())
        
        text_report.append(f"\n1. Phát hiện chế độ thị trường:")
        if len(unique_regimes) >= 3:
            text_report.append("   ✓ Bot đã phát hiện đa dạng các chế độ thị trường")
            for regime in unique_regimes:
                text_report.append(f"     - {regime}")
        else:
            text_report.append(f"   ⚠ Bot chỉ phát hiện {len(unique_regimes)} chế độ thị trường")
            for regime in unique_regimes:
                text_report.append(f"     - {regime}")
        
        # Đánh giá về việc sử dụng đa dạng chiến lược
        unique_strategies = set()
        for symbol in self.symbols:
            unique_strategies.update(self.test_data['by_symbol'][symbol]['strategy_usage'].keys())
        
        text_report.append(f"\n2. Sử dụng chiến lược giao dịch:")
        if len(unique_strategies) >= 3:
            text_report.append("   ✓ Bot đã vận dụng đa dạng các chiến lược giao dịch")
            for strategy in unique_strategies:
                text_report.append(f"     - {strategy}")
        else:
            text_report.append(f"   ⚠ Bot chỉ sử dụng {len(unique_strategies)} chiến lược giao dịch")
            for strategy in unique_strategies:
                text_report.append(f"     - {strategy}")
        
        # Đánh giá về sự phù hợp giữa chiến lược và chế độ thị trường
        text_report.append(f"\n3. Sự phù hợp giữa chiến lược và chế độ thị trường:")
        
        strategy_regime_mapping = {
            'trending': ['ema_cross', 'macd', 'adx'],
            'ranging': ['rsi', 'stochastic', 'bbands'],
            'volatile': ['atr', 'adx', 'rsi'],
            'quiet': ['bbands', 'rsi', 'stochastic']
        }
        
        matching_scores = []
        
        for symbol in self.symbols:
            if 'strategy_regime_correlation' in report_data['by_symbol'][symbol]:
                for regime, strategies in report_data['by_symbol'][symbol]['strategy_regime_correlation'].items():
                    if regime in strategy_regime_mapping:
                        expected_strategies = strategy_regime_mapping[regime]
                        actual_strategies = list(strategies.keys())
                        
                        # Tính số lượng chiến lược trùng khớp
                        matching = sum(1 for s in actual_strategies if s.lower() in expected_strategies)
                        
                        if actual_strategies:
                            score = matching / len(actual_strategies)
                            matching_scores.append(score)
        
        if matching_scores:
            avg_matching_score = sum(matching_scores) / len(matching_scores)
            
            if avg_matching_score >= 0.7:
                text_report.append("   ✓ Bot chọn chiến lược PHÙ HỢP với từng chế độ thị trường")
            elif avg_matching_score >= 0.5:
                text_report.append("   ⚠ Bot chọn chiến lược TƯƠNG ĐỐI PHÙ HỢP với từng chế độ thị trường")
            else:
                text_report.append("   ✗ Bot chọn chiến lược CHƯA PHÙ HỢP với từng chế độ thị trường")
        else:
            text_report.append("   ? Chưa đủ dữ liệu để đánh giá sự phù hợp")
        
        # Đánh giá về chiến lược BBands trong thị trường yên tĩnh
        text_report.append(f"\n4. Chiến lược BBands trong thị trường yên tĩnh:")
        
        bbands_in_quiet = False
        for symbol in self.symbols:
            if 'strategy_regime_correlation' in report_data['by_symbol'][symbol]:
                if 'quiet' in report_data['by_symbol'][symbol]['strategy_regime_correlation']:
                    quiet_strategies = report_data['by_symbol'][symbol]['strategy_regime_correlation']['quiet']
                    
                    for strategy in quiet_strategies:
                        if strategy.lower() == 'bbands':
                            bbands_in_quiet = True
                            break
        
        if bbands_in_quiet:
            text_report.append("   ✓ Bot đã vận dụng chiến lược BBands trong thị trường yên tĩnh")
        else:
            text_report.append("   ⚠ Bot chưa vận dụng chiến lược BBands trong thị trường yên tĩnh")
        
        # Tính tỷ lệ tín hiệu HOLD
        hold_ratio = {}
        for symbol in self.symbols:
            signal_counts = self.test_data['by_symbol'][symbol]['signal_counts']
            total_signals = sum(signal_counts.values())
            
            if total_signals > 0:
                hold_count = signal_counts.get('HOLD', 0)
                hold_ratio[symbol] = hold_count / total_signals
        
        text_report.append(f"\n5. Tỷ lệ giữ vị thế (HOLD):")
        for symbol, ratio in hold_ratio.items():
            text_report.append(f"   - {symbol}: {ratio:.1%}")
        
        avg_hold_ratio = sum(hold_ratio.values()) / len(hold_ratio) if hold_ratio else 0
        
        if avg_hold_ratio >= 0.7:
            text_report.append("   ⚠ Tỷ lệ HOLD quá cao, bot có thể quá thận trọng")
        elif avg_hold_ratio <= 0.3:
            text_report.append("   ⚠ Tỷ lệ HOLD quá thấp, bot có thể quá mạo hiểm")
        else:
            text_report.append("   ✓ Tỷ lệ HOLD phù hợp, bot có xu hướng cân bằng")
        
        # Kết luận chung
        text_report.append("\nKẾT LUẬN VÀ KIẾN NGHỊ")
        text_report.append("-"*50)
        
        # Kiến nghị dựa trên các phát hiện
        text_report.append("\nCác phát hiện chính:")
        
        if len(unique_regimes) < 4:
            text_report.append("- Bot chưa phát hiện đủ các chế độ thị trường")
            text_report.append("  Kiến nghị: Nên tăng thời gian test hoặc đa dạng hóa dữ liệu test")
        
        if not bbands_in_quiet:
            text_report.append("- Chiến lược BBands chưa được áp dụng trong thị trường yên tĩnh")
            text_report.append("  Kiến nghị: Điều chỉnh logic lựa chọn chiến lược trong chế độ yên tĩnh")
        
        if avg_hold_ratio >= 0.7:
            text_report.append("- Bot có xu hướng quá thận trọng (tỷ lệ HOLD cao)")
            text_report.append("  Kiến nghị: Điều chỉnh ngưỡng tín hiệu để bot chủ động hơn")
        
        if avg_hold_ratio <= 0.3:
            text_report.append("- Bot có xu hướng quá mạo hiểm (tỷ lệ HOLD thấp)")
            text_report.append("  Kiến nghị: Điều chỉnh ngưỡng tín hiệu để bot thận trọng hơn")
        
        # Lưu báo cáo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Lưu báo cáo JSON
        json_report_path = os.path.join(self.report_dir, f"comprehensive_report_{timestamp}.json")
        with open(json_report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4, default=str)
        
        # Lưu báo cáo văn bản
        text_report_path = os.path.join(self.report_dir, f"comprehensive_report_{timestamp}.txt")
        with open(text_report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(text_report))
        
        logger.info(f"Đã tạo báo cáo JSON: {json_report_path}")
        logger.info(f"Đã tạo báo cáo văn bản: {text_report_path}")
        
        return {
            'json_report': json_report_path,
            'text_report': text_report_path,
            'charts': charts
        }
    
    def run_comprehensive_test(self):
        """Chạy kiểm tra toàn diện"""
        logger.info(f"Bắt đầu kiểm tra toàn diện (thời lượng: {self.test_duration_hours} giờ)")
        
        # Tải dữ liệu lịch sử
        self.load_historical_data()
        
        # Tính thời điểm kết thúc
        end_time = datetime.now() + timedelta(hours=self.test_duration_hours)
        
        try:
            # Vòng lặp chính
            while datetime.now() < end_time:
                # Cập nhật dữ liệu thị trường
                self.update_market_data()
                
                # Chạy một vòng lặp kiểm tra
                self.run_bot_test_iteration()
                
                # Chờ một khoảng thời gian
                logger.info(f"Hoàn thành vòng lặp {self.test_data['iterations']}. Chờ 5 phút trước khi cập nhật.")
                
                # Trong test ngắn, nên chờ ít thời gian hơn
                wait_time = min(60, 300 if self.test_duration_hours > 1 else 30)
                time.sleep(wait_time)
                
        except KeyboardInterrupt:
            logger.info("Kiểm tra bị ngắt bởi người dùng")
        except Exception as e:
            logger.error(f"Lỗi không xác định: {str(e)}")
        finally:
            # Tạo báo cáo kết quả
            report_info = self.generate_comprehensive_report()
            
            return report_info

def main():
    # Xử lý tham số dòng lệnh
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm tra toàn diện bot giao dịch tiền điện tử')
    parser.add_argument('--duration', type=float, default=2, help='Thời lượng test (giờ)')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,SOLUSDT', help='Các cặp tiền cần test (phân cách bằng dấu phẩy)')
    parser.add_argument('--timeframes', type=str, default='1h,4h', help='Các khung thời gian (phân cách bằng dấu phẩy)')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',')
    timeframes = args.timeframes.split(',')
    
    # Khởi tạo và chạy tester
    tester = ComprehensiveTester(
        symbols=symbols,
        timeframes=timeframes,
        test_duration_hours=args.duration
    )
    
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()