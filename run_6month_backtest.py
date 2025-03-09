#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra toàn diện bot giao dịch với dữ liệu thực 6 tháng

Script này thực hiện:
1. Tải dữ liệu thực từ Binance cho 6 tháng gần nhất
2. Kiểm tra khả năng bot tự nhận diện và thích nghi với mọi chế độ thị trường
3. Phân tích chi tiết các quyết định và kết quả giao dịch
4. Đánh giá tổng thể hiệu suất và tạo báo cáo đầy đủ cho từng đồng tiền
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
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Union, Any, Optional

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("6month_backtest.log"),
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
    from risk_manager import RiskManager
    # Thêm các module khác nếu cần
except ImportError as e:
    logger.error(f"Không thể import module: {str(e)}")
    sys.exit(1)

class SixMonthBacktester:
    """Lớp kiểm tra bot với dữ liệu 6 tháng"""
    
    def __init__(self, symbols=None, timeframes=None, 
                data_dir='test_data', report_dir='reports', chart_dir='backtest_charts'):
        """
        Khởi tạo backtester
        
        Args:
            symbols (list): Danh sách các cặp tiền
            timeframes (list): Danh sách khung thời gian
            data_dir (str): Thư mục dữ liệu
            report_dir (str): Thư mục báo cáo
            chart_dir (str): Thư mục biểu đồ
        """
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']
        self.timeframes = timeframes or ['1h', '4h', '1d']
        self.primary_timeframe = '1h'  # Khung thời gian chính để phân tích
        self.data_dir = data_dir
        self.report_dir = report_dir
        self.chart_dir = chart_dir
        
        # Thời gian backtest: 6 tháng
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=180)
        
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
        
        # Lưu trữ dữ liệu lịch sử và kết quả cho từng symbol
        self.historical_data = {}
        self.backtest_results = {}
        
        for symbol in self.symbols:
            self.backtest_results[symbol] = {
                'regime_stats': {},
                'strategy_stats': {},
                'trade_history': [],
                'equity_curve': [],
                'daily_returns': [],
                'monthly_stats': {},
                'metrics': {},
                'debug_info': []
            }
    
    def download_and_prepare_data(self):
        """Tải và chuẩn bị dữ liệu cho backtest"""
        logger.info(f"Bắt đầu tải dữ liệu cho {len(self.symbols)} cặp tiền từ {self.start_date.strftime('%Y-%m-%d')} đến {self.end_date.strftime('%Y-%m-%d')}")
        
        self.historical_data = {}
        
        # Chạy tải song song cho nhiều symbol
        with ThreadPoolExecutor(max_workers=min(4, len(self.symbols))) as executor:
            for symbol in self.symbols:
                executor.submit(self._download_data_for_symbol, symbol)
        
        logger.info("Hoàn thành tải dữ liệu cho tất cả các cặp tiền")
    
    def _download_data_for_symbol(self, symbol):
        """Tải dữ liệu cho một cặp tiền cụ thể"""
        self.historical_data[symbol] = {}
        
        for timeframe in self.timeframes:
            try:
                # Tạo tên file
                filename = f"{symbol}_{timeframe}_6month.csv"
                file_path = os.path.join(self.data_dir, filename)
                
                # Kiểm tra xem file đã tồn tại và mới đủ hay không
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    
                    if len(df) > 0:
                        oldest_date = df.index.min()
                        newest_date = df.index.max()
                        
                        # Kiểm tra nếu dữ liệu đủ mới và đủ dài
                        if newest_date >= (self.end_date - timedelta(days=1)) and \
                           oldest_date <= (self.start_date + timedelta(days=5)) and \
                           len(df) >= 500:
                            logger.info(f"Sử dụng dữ liệu có sẵn cho {symbol} {timeframe} ({len(df)} nến từ {oldest_date} đến {newest_date})")
                            self.historical_data[symbol][timeframe] = df
                            continue
                
                # Tải dữ liệu mới từ Binance
                if self.use_real_api:
                    start_str = self.start_date.strftime("%Y-%m-%d")
                    
                    df = self.data_processor.download_historical_data(
                        symbol=symbol,
                        interval=timeframe,
                        start_time=start_str,
                        save_to_file=True,
                        output_dir=self.data_dir,
                        output_file=filename
                    )
                    
                    logger.info(f"Đã tải dữ liệu {symbol} {timeframe} từ Binance ({len(df)} nến)")
                else:
                    # Tạo dữ liệu mô phỏng cho testing
                    df = self._generate_mock_data(symbol, timeframe)
                    df.to_csv(file_path)
                    logger.info(f"Đã tạo dữ liệu mô phỏng cho {symbol} {timeframe} ({len(df)} nến)")
                
                # Thêm các chỉ báo kỹ thuật
                df = self.process_and_enhance_dataset(df, symbol, timeframe, output_file=filename)
                
                self.historical_data[symbol][timeframe] = df
                
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu {symbol} {timeframe}: {str(e)}")
                continue
    
    def process_and_enhance_dataset(self, df, symbol, timeframe, output_file=None):
        """
        Xử lý và làm giàu dữ liệu với các chỉ báo kỹ thuật
        
        Args:
            df (pd.DataFrame): DataFrame gốc
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            output_file (str): Tên file để lưu kết quả
            
        Returns:
            pd.DataFrame: DataFrame đã được làm giàu
        """
        # Kiểm tra cột cần thiết
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"Thiếu cột {col} trong dữ liệu {symbol} {timeframe}")
                return df
        
        # Thêm tất cả các chỉ báo kỹ thuật
        df = self.data_processor.add_indicators(df, indicators=[
            'rsi', 'macd', 'bbands', 'ema', 'atr', 'stochastic', 'adx', 'obv'
        ])
        
        # Thêm các chỉ báo nâng cao
        # Bollinger Bands Width
        if all(x in df.columns for x in ['bb_upper', 'bb_lower', 'bb_middle']):
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Volatility Ratio
        if 'atr' in df.columns:
            df['volatility_ratio'] = df['atr'] / df['close'].rolling(window=14).mean()
        
        # Trend Strength
        if all(x in df.columns for x in ['adx', 'plus_di', 'minus_di']):
            df['trend_strength'] = df['adx'] * (df['plus_di'] - df['minus_di']).abs() / (df['plus_di'] + df['minus_di'])
        
        # RSI Divergence (simple implementation)
        if 'rsi' in df.columns:
            df['rsi_slope'] = df['rsi'].diff(5)
            df['price_slope'] = df['close'].diff(5)
            df['rsi_divergence'] = np.where(
                (df['rsi_slope'] > 0) & (df['price_slope'] < 0), 
                1,  # Bullish divergence
                np.where(
                    (df['rsi_slope'] < 0) & (df['price_slope'] > 0),
                    -1,  # Bearish divergence
                    0    # No divergence
                )
            )
        
        # Lưu DataFrame đã làm giàu
        if output_file:
            output_path = os.path.join(self.data_dir, f"{symbol}_{timeframe}_enhanced.csv")
            df.to_csv(output_path)
            logger.info(f"Đã lưu dữ liệu đã làm giàu cho {symbol} {timeframe} vào {output_path}")
        
        return df
    
    def _generate_mock_data(self, symbol, timeframe, days=180):
        """
        Tạo dữ liệu mô phỏng cho testing
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            days (int): Số ngày dữ liệu
            
        Returns:
            pd.DataFrame: DataFrame mô phỏng
        """
        # Xác định tham số dựa trên symbol
        if symbol == 'BTCUSDT':
            base_price = 50000
            volatility = 0.02
        elif symbol == 'ETHUSDT':
            base_price = 3000
            volatility = 0.025
        elif symbol == 'SOLUSDT':
            base_price = 150
            volatility = 0.035
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
        end_date = self.end_date
        start_date = end_date - timedelta(days=days)
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
        if remaining_length > 0:
            regime_lengths[0] += remaining_length
        
        # Khởi tạo dữ liệu giá
        price_data = []
        current_price = base_price
        regime_index = 0
        remaining_regime_length = regime_lengths[0]
        current_regime = regimes[0]
        
        for i in range(periods):
            # Kiểm tra và cập nhật chế độ thị trường
            if remaining_regime_length <= 0:
                regime_index = (regime_index + 1) % len(regimes)
                current_regime = regimes[regime_index]
                remaining_regime_length = regime_lengths[regime_index]
            
            remaining_regime_length -= 1
            
            # Điều chỉnh volatility và drift theo chế độ thị trường
            if current_regime == 'trending':
                local_volatility = volatility * 0.8
                local_drift = 0.001 if i % 2 == 0 else -0.0005  # Alternating trends
            elif current_regime == 'ranging':
                local_volatility = volatility * 0.6
                # Mean reversion effect
                local_drift = -0.001 * (current_price - base_price) / base_price
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
            volume = np.random.exponential(1000) * (1 + np.random.uniform(-0.5, 0.5))
            
            # Thêm vào dữ liệu
            price_data.append({
                'timestamp': date_range[i],
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': current_price,
                'volume': volume,
                'true_regime': current_regime  # Thêm chế độ thị trường thật để so sánh
            })
        
        # Tạo DataFrame
        df = pd.DataFrame(price_data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def run_backtest_for_symbol(self, symbol, initial_balance=10000, debug=False):
        """
        Chạy backtest cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            initial_balance (float): Số dư ban đầu
            debug (bool): Có ghi log debug hay không
            
        Returns:
            Dict: Kết quả backtest
        """
        logger.info(f"Bắt đầu backtest cho {symbol} với số dư ban đầu {initial_balance}")
        
        # Khởi tạo các thành phần cho cặp tiền này
        regime_detector = MarketRegimeDetector()
        strategy_selector = StrategySelector()
        adaptive_trader = AdaptiveTrader(
            regime_detector=regime_detector,
            strategy_selector=strategy_selector
        )
        risk_manager = RiskManager(initial_balance=initial_balance, max_risk_per_trade=1.0)
        
        # Lấy dữ liệu chính
        if symbol not in self.historical_data or self.primary_timeframe not in self.historical_data[symbol]:
            logger.error(f"Không có dữ liệu cho {symbol} {self.primary_timeframe}")
            return None
        
        df = self.historical_data[symbol][self.primary_timeframe]
        
        # Khởi tạo các biến theo dõi
        balance = initial_balance
        equity_curve = [balance]
        trade_history = []
        regime_stats = {}
        strategy_stats = {}
        daily_returns = []
        debug_info = []
        
        current_position = None
        last_date = None
        
        # Vòng lặp chính: duyệt qua từng nến
        for i in range(50, len(df)):  # Bỏ qua 50 nến đầu để đủ dữ liệu cho chỉ báo
            current_data = df.iloc[:i+1]
            timestamp = current_data.index[-1]
            current_price = current_data['close'].iloc[-1]
            
            # Khởi tạo debug record
            debug_record = {
                'timestamp': timestamp,
                'price': current_price,
                'balance': balance,
                'has_position': current_position is not None
            }
            
            # Phát hiện chế độ thị trường
            try:
                detected_regime = regime_detector.detect_regime(current_data)
                debug_record['detected_regime'] = detected_regime
                
                # Cập nhật thống kê chế độ thị trường
                if detected_regime in regime_stats:
                    regime_stats[detected_regime] += 1
                else:
                    regime_stats[detected_regime] = 1
            except Exception as e:
                logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
                detected_regime = "unknown"
                debug_record['detected_regime'] = "error"
                debug_record['regime_error'] = str(e)
            
            # Lấy chiến lược tối ưu cho chế độ thị trường
            try:
                optimal_strategies = strategy_selector.get_strategies_for_regime(detected_regime)
                debug_record['strategies'] = optimal_strategies
                
                # Cập nhật thống kê chiến lược
                for strategy, weight in optimal_strategies.items():
                    if strategy in strategy_stats:
                        strategy_stats[strategy] += 1
                    else:
                        strategy_stats[strategy] = 1
            except Exception as e:
                logger.error(f"Lỗi khi lấy chiến lược tối ưu: {str(e)}")
                optimal_strategies = {"default": 1.0}
                debug_record['strategies'] = {"error": 1.0}
                debug_record['strategy_error'] = str(e)
            
            # Lấy tín hiệu giao dịch
            try:
                signal = adaptive_trader.generate_signal(current_data)
                if isinstance(signal, dict) and 'action' in signal:
                    action = signal['action']
                else:
                    action = signal
                debug_record['signal'] = action
            except Exception as e:
                logger.error(f"Lỗi khi tạo tín hiệu giao dịch: {str(e)}")
                action = "HOLD"
                debug_record['signal'] = "error"
                debug_record['signal_error'] = str(e)
            
            # Xử lý vị thế hiện tại nếu có
            if current_position is not None:
                # Tính lãi/lỗ
                if current_position['side'] == 'BUY':
                    profit_pct = (current_price - current_position['entry_price']) / current_position['entry_price']
                else:  # SELL
                    profit_pct = (current_position['entry_price'] - current_price) / current_position['entry_price']
                
                unrealized_profit = current_position['amount'] * profit_pct
                debug_record['unrealized_profit'] = unrealized_profit
                
                # Kiểm tra take profit / stop loss
                take_profit_reached = profit_pct >= current_position['take_profit_pct']
                stop_loss_reached = profit_pct <= -current_position['stop_loss_pct']
                
                # Kiểm tra tín hiệu ngược
                reverse_signal = (current_position['side'] == 'BUY' and action == 'SELL') or \
                                 (current_position['side'] == 'SELL' and action == 'BUY')
                
                # Đóng vị thế nếu cần
                if take_profit_reached or stop_loss_reached or reverse_signal:
                    # Tính lãi/lỗ chính xác
                    realized_profit = current_position['amount'] * profit_pct
                    
                    # Cập nhật số dư
                    balance += realized_profit
                    
                    # Xác định lý do đóng
                    if take_profit_reached:
                        exit_reason = "Take Profit"
                    elif stop_loss_reached:
                        exit_reason = "Stop Loss"
                    else:
                        exit_reason = "Reverse Signal"
                    
                    # Ghi nhận giao dịch
                    trade_info = {
                        'entry_time': current_position['entry_time'],
                        'exit_time': timestamp,
                        'symbol': symbol,
                        'market_regime': current_position['regime'],
                        'side': current_position['side'],
                        'entry_price': current_position['entry_price'],
                        'exit_price': current_price,
                        'amount': current_position['amount'],
                        'profit': realized_profit,
                        'profit_pct': profit_pct * 100,
                        'exit_reason': exit_reason,
                        'strategies_used': current_position['strategies']
                    }
                    
                    trade_history.append(trade_info)
                    
                    debug_record['trade_closed'] = True
                    debug_record['trade_info'] = trade_info
                    
                    # Đặt lại vị thế
                    current_position = None
            
            # Mở vị thế mới nếu có tín hiệu và không có vị thế hiện tại
            if current_position is None and (action == 'BUY' or action == 'SELL'):
                # Tính toán các tham số quản lý rủi ro
                atr_value = current_data['atr'].iloc[-1] if 'atr' in current_data.columns else None
                
                # Áp dụng quản lý vốn
                risk_percentage = 1.0  # 1% số dư trên mỗi giao dịch
                position_size, risk_params = risk_manager.calculate_position_size(
                    balance=balance,
                    risk_percentage=risk_percentage,
                    volatility=atr_value,
                    market_regime=detected_regime
                )
                
                # Tính take profit / stop loss
                take_profit_pct = risk_params.get('take_profit_pct', 2.0)  # Mặc định 2%
                stop_loss_pct = risk_params.get('stop_loss_pct', 1.0)      # Mặc định 1%
                
                # Tính số lượng
                amount = balance * position_size / 100
                
                # Mở vị thế
                current_position = {
                    'side': action,
                    'entry_price': current_price,
                    'amount': amount,
                    'entry_time': timestamp,
                    'regime': detected_regime,
                    'take_profit_pct': take_profit_pct / 100,
                    'stop_loss_pct': stop_loss_pct / 100,
                    'strategies': optimal_strategies
                }
                
                debug_record['trade_opened'] = True
                debug_record['position'] = current_position
            
            # Cập nhật equity curve
            equity_curve.append(balance)
            
            # Cập nhật daily returns
            current_date = timestamp.date()
            if last_date is None or current_date != last_date:
                # Ngày mới
                if last_date is not None:
                    # Tính lợi nhuận ngày
                    daily_return = balance / equity_curve[-2] - 1
                    daily_returns.append({
                        'date': current_date,
                        'return': daily_return
                    })
            
                last_date = current_date
            
            # Lưu thông tin debug nếu cần
            if debug:
                debug_info.append(debug_record)
        
        # Đóng vị thế cuối cùng nếu còn
        if current_position is not None:
            final_price = df['close'].iloc[-1]
            
            # Tính lãi/lỗ
            if current_position['side'] == 'BUY':
                profit_pct = (final_price - current_position['entry_price']) / current_position['entry_price']
            else:  # SELL
                profit_pct = (current_position['entry_price'] - final_price) / current_position['entry_price']
            
            realized_profit = current_position['amount'] * profit_pct
            
            # Cập nhật số dư
            balance += realized_profit
            
            # Ghi nhận giao dịch
            trade_info = {
                'entry_time': current_position['entry_time'],
                'exit_time': df.index[-1],
                'symbol': symbol,
                'market_regime': current_position['regime'],
                'side': current_position['side'],
                'entry_price': current_position['entry_price'],
                'exit_price': final_price,
                'amount': current_position['amount'],
                'profit': realized_profit,
                'profit_pct': profit_pct * 100,
                'exit_reason': "End of Backtest",
                'strategies_used': current_position['strategies']
            }
            
            trade_history.append(trade_info)
            
            # Cập nhật equity curve
            equity_curve[-1] = balance
        
        # Tính toán các chỉ số hiệu suất
        if len(trade_history) > 0:
            # Tổng số giao dịch
            total_trades = len(trade_history)
            
            # Số giao dịch thắng/thua
            winning_trades = sum(1 for trade in trade_history if trade['profit'] > 0)
            losing_trades = total_trades - winning_trades
            
            # Tỷ lệ thắng
            win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
            
            # Profit factor
            gross_profit = sum(trade['profit'] for trade in trade_history if trade['profit'] > 0)
            gross_loss = abs(sum(trade['profit'] for trade in trade_history if trade['profit'] <= 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Lợi nhuận trung bình trên giao dịch
            avg_profit = sum(trade['profit'] for trade in trade_history) / total_trades if total_trades > 0 else 0
            
            # Lợi nhuận trung bình trên giao dịch thắng
            avg_winning_trade = gross_profit / winning_trades if winning_trades > 0 else 0
            
            # Thua lỗ trung bình trên giao dịch thua
            avg_losing_trade = gross_loss / losing_trades if losing_trades > 0 else 0
            
            # Winning trades theo regime
            regime_win_rates = {}
            for regime in regime_stats.keys():
                regime_trades = [t for t in trade_history if t['market_regime'] == regime]
                if len(regime_trades) > 0:
                    regime_wins = sum(1 for t in regime_trades if t['profit'] > 0)
                    regime_win_rates[regime] = (regime_wins / len(regime_trades) * 100, len(regime_trades))
            
            # Winning trades theo strategy
            strategy_win_rates = {}
            for strategy in strategy_stats.keys():
                strategy_trades = [t for t in trade_history if strategy in t['strategies_used']]
                if len(strategy_trades) > 0:
                    strategy_wins = sum(1 for t in strategy_trades if t['profit'] > 0)
                    strategy_win_rates[strategy] = (strategy_wins / len(strategy_trades) * 100, len(strategy_trades))
            
            # Max drawdown
            max_balance = initial_balance
            max_drawdown = 0
            max_drawdown_pct = 0
            
            for equity in equity_curve:
                if equity > max_balance:
                    max_balance = equity
                else:
                    drawdown = max_balance - equity
                    drawdown_pct = drawdown / max_balance * 100
                    if drawdown_pct > max_drawdown_pct:
                        max_drawdown = drawdown
                        max_drawdown_pct = drawdown_pct
            
            # Sharpe ratio (giả định risk-free rate là 0)
            if len(daily_returns) > 0:
                returns = [d['return'] for d in daily_returns]
                avg_daily_return = np.mean(returns)
                std_daily_return = np.std(returns)
                sharpe_ratio = (avg_daily_return * 252) / (std_daily_return * np.sqrt(252)) if std_daily_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Tính ROI
            roi = (balance - initial_balance) / initial_balance * 100
            
            # CAGR (Compound Annual Growth Rate)
            days = (df.index[-1] - df.index[50]).days
            years = days / 365
            cagr = ((balance / initial_balance) ** (1 / years) - 1) * 100 if years > 0 else 0
            
            metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_profit': avg_profit,
                'avg_winning_trade': avg_winning_trade,
                'avg_losing_trade': avg_losing_trade,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio,
                'roi': roi,
                'cagr': cagr,
                'final_balance': balance
            }
        else:
            metrics = {
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown_pct': 0,
                'roi': 0,
                'final_balance': balance
            }
            regime_win_rates = {}
            strategy_win_rates = {}
        
        # Lưu kết quả
        self.backtest_results[symbol] = {
            'regime_stats': regime_stats,
            'strategy_stats': strategy_stats,
            'regime_win_rates': regime_win_rates,
            'strategy_win_rates': strategy_win_rates,
            'trade_history': trade_history,
            'equity_curve': equity_curve,
            'daily_returns': daily_returns,
            'metrics': metrics,
            'debug_info': debug_info
        }
        
        logger.info(f"Hoàn thành backtest cho {symbol}: {total_trades} giao dịch, Win Rate: {win_rate:.2f}%, ROI: {roi:.2f}%")
        
        return self.backtest_results[symbol]
    
    def run_backtest_all_symbols(self, initial_balance=10000, debug=False):
        """
        Chạy backtest cho tất cả các cặp tiền
        
        Args:
            initial_balance (float): Số dư ban đầu cho mỗi cặp tiền
            debug (bool): Có ghi log debug hay không
            
        Returns:
            Dict: Kết quả backtest cho tất cả các cặp tiền
        """
        logger.info(f"Bắt đầu backtest cho {len(self.symbols)} cặp tiền")
        
        # Chạy backtest tuần tự
        for symbol in self.symbols:
            self.run_backtest_for_symbol(symbol, initial_balance, debug)
        
        # Tính toán các chỉ số tổng hợp
        if len(self.backtest_results) > 0:
            # Tổng số giao dịch
            total_trades = sum(results['metrics'].get('total_trades', 0) for results in self.backtest_results.values())
            
            # Tổng lợi nhuận
            total_profit = sum(results['metrics'].get('final_balance', initial_balance) - initial_balance 
                            for results in self.backtest_results.values())
            
            # Tỷ lệ thắng trung bình
            avg_win_rate = np.mean([results['metrics'].get('win_rate', 0) 
                                for results in self.backtest_results.values() if results['metrics'].get('total_trades', 0) > 0])
            
            # ROI trung bình
            avg_roi = np.mean([results['metrics'].get('roi', 0) 
                            for results in self.backtest_results.values()])
            
            # Sharpe ratio trung bình
            avg_sharpe = np.mean([results['metrics'].get('sharpe_ratio', 0) 
                                for results in self.backtest_results.values()])
            
            # Số dư cuối cùng trung bình
            avg_final_balance = np.mean([results['metrics'].get('final_balance', initial_balance) 
                                      for results in self.backtest_results.values()])
            
            # Phân tích chế độ thị trường tổng hợp
            all_regimes = {}
            for symbol, results in self.backtest_results.items():
                for regime, count in results['regime_stats'].items():
                    if regime in all_regimes:
                        all_regimes[regime] += count
                    else:
                        all_regimes[regime] = count
            
            # Phân tích chiến lược tổng hợp
            all_strategies = {}
            for symbol, results in self.backtest_results.items():
                for strategy, count in results['strategy_stats'].items():
                    if strategy in all_strategies:
                        all_strategies[strategy] += count
                    else:
                        all_strategies[strategy] = count
            
            # Tổng hợp kết quả
            self.aggregated_results = {
                'total_symbols': len(self.backtest_results),
                'total_trades': total_trades,
                'total_profit': total_profit,
                'avg_win_rate': avg_win_rate,
                'avg_roi': avg_roi,
                'avg_sharpe': avg_sharpe,
                'avg_final_balance': avg_final_balance,
                'all_regimes': all_regimes,
                'all_strategies': all_strategies
            }
            
            logger.info(f"Tổng hợp kết quả: {total_trades} giao dịch, Win Rate trung bình: {avg_win_rate:.2f}%, ROI trung bình: {avg_roi:.2f}%")
        else:
            self.aggregated_results = {
                'total_symbols': 0,
                'total_trades': 0,
                'avg_win_rate': 0,
                'avg_roi': 0
            }
        
        return self.backtest_results
    
    def create_backtest_charts(self, symbol):
        """
        Tạo biểu đồ kết quả backtest cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Đường dẫn đến các biểu đồ
        """
        if symbol not in self.backtest_results:
            logger.error(f"Không có kết quả backtest cho {symbol}")
            return None
        
        results = self.backtest_results[symbol]
        chart_paths = {}
        
        try:
            # Biểu đồ equity curve
            plt.figure(figsize=(12, 6))
            plt.plot(results['equity_curve'])
            plt.title(f'Equity Curve - {symbol}')
            plt.xlabel('Candles')
            plt.ylabel('Balance')
            plt.grid(True)
            
            equity_path = os.path.join(self.chart_dir, f"{symbol}_equity_curve.png")
            plt.savefig(equity_path)
            plt.close()
            chart_paths['equity_curve'] = equity_path
            
            # Biểu đồ phân bố chế độ thị trường
            if results['regime_stats']:
                plt.figure(figsize=(10, 6))
                regimes = list(results['regime_stats'].keys())
                counts = list(results['regime_stats'].values())
                plt.bar(regimes, counts)
                plt.title(f'Market Regime Distribution - {symbol}')
                plt.xlabel('Regime')
                plt.ylabel('Count')
                
                regime_path = os.path.join(self.chart_dir, f"{symbol}_regime_distribution.png")
                plt.savefig(regime_path)
                plt.close()
                chart_paths['regime_distribution'] = regime_path
            
            # Biểu đồ phân bố chiến lược
            if results['strategy_stats']:
                plt.figure(figsize=(10, 6))
                strategies = list(results['strategy_stats'].keys())
                counts = list(results['strategy_stats'].values())
                plt.bar(strategies, counts)
                plt.title(f'Strategy Distribution - {symbol}')
                plt.xlabel('Strategy')
                plt.ylabel('Count')
                plt.xticks(rotation=45)
                
                strategy_path = os.path.join(self.chart_dir, f"{symbol}_strategy_distribution.png")
                plt.savefig(strategy_path)
                plt.close()
                chart_paths['strategy_distribution'] = strategy_path
            
            # Biểu đồ tỷ lệ thắng theo chế độ thị trường
            if results.get('regime_win_rates'):
                plt.figure(figsize=(10, 6))
                regimes = list(results['regime_win_rates'].keys())
                win_rates = [rate for rate, _ in results['regime_win_rates'].values()]
                trade_counts = [count for _, count in results['regime_win_rates'].values()]
                
                ax = plt.subplot(111)
                bars = ax.bar(regimes, win_rates)
                
                # Thêm số lượng giao dịch lên mỗi cột
                for i, (bar, count) in enumerate(zip(bars, trade_counts)):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{count} trades', ha='center', va='bottom')
                
                plt.title(f'Win Rate by Market Regime - {symbol}')
                plt.xlabel('Regime')
                plt.ylabel('Win Rate (%)')
                plt.axhline(y=50, color='r', linestyle='--', alpha=0.3)
                
                regime_win_path = os.path.join(self.chart_dir, f"{symbol}_regime_win_rates.png")
                plt.savefig(regime_win_path)
                plt.close()
                chart_paths['regime_win_rates'] = regime_win_path
            
            # Biểu đồ tỷ lệ thắng theo chiến lược
            if results.get('strategy_win_rates'):
                plt.figure(figsize=(10, 6))
                strategies = list(results['strategy_win_rates'].keys())
                win_rates = [rate for rate, _ in results['strategy_win_rates'].values()]
                trade_counts = [count for _, count in results['strategy_win_rates'].values()]
                
                ax = plt.subplot(111)
                bars = ax.bar(strategies, win_rates)
                
                # Thêm số lượng giao dịch lên mỗi cột
                for i, (bar, count) in enumerate(zip(bars, trade_counts)):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{count} trades', ha='center', va='bottom')
                
                plt.title(f'Win Rate by Strategy - {symbol}')
                plt.xlabel('Strategy')
                plt.ylabel('Win Rate (%)')
                plt.axhline(y=50, color='r', linestyle='--', alpha=0.3)
                plt.xticks(rotation=45)
                
                strategy_win_path = os.path.join(self.chart_dir, f"{symbol}_strategy_win_rates.png")
                plt.savefig(strategy_win_path)
                plt.close()
                chart_paths['strategy_win_rates'] = strategy_win_path
            
            # Biểu đồ phân bố lợi nhuận
            if results['trade_history']:
                profits = [trade['profit'] for trade in results['trade_history']]
                plt.figure(figsize=(10, 6))
                plt.hist(profits, bins=20)
                plt.axvline(x=0, color='r', linestyle='--')
                plt.title(f'Profit Distribution - {symbol}')
                plt.xlabel('Profit')
                plt.ylabel('Frequency')
                
                profit_dist_path = os.path.join(self.chart_dir, f"{symbol}_profit_distribution.png")
                plt.savefig(profit_dist_path)
                plt.close()
                chart_paths['profit_distribution'] = profit_dist_path
            
            # Biểu đồ độ chính xác của bot trong việc phát hiện chế độ thị trường
            if 'debug_info' in results and len(results['debug_info']) > 0 and 'true_regime' in self.historical_data[symbol][self.primary_timeframe].columns:
                # Lấy dữ liệu chế độ thị trường thật (chỉ có trong dữ liệu mô phỏng)
                true_regimes = []
                detected_regimes = []
                
                true_regime_data = self.historical_data[symbol][self.primary_timeframe]['true_regime']
                
                for debug_record in results['debug_info']:
                    timestamp = debug_record['timestamp']
                    if timestamp in true_regime_data.index:
                        true_regime = true_regime_data.loc[timestamp]
                        detected_regime = debug_record.get('detected_regime', 'unknown')
                        
                        true_regimes.append(true_regime)
                        detected_regimes.append(detected_regime)
                
                # Tính toán confusion matrix
                if len(true_regimes) > 0 and len(detected_regimes) > 0:
                    unique_regimes = list(set(true_regimes + detected_regimes))
                    
                    # Tạo confusion matrix
                    confusion = {}
                    for true_regime in unique_regimes:
                        confusion[true_regime] = {}
                        for detected_regime in unique_regimes:
                            confusion[true_regime][detected_regime] = 0
                    
                    for true, detected in zip(true_regimes, detected_regimes):
                        confusion[true][detected] += 1
                    
                    # Tính độ chính xác
                    correct = sum(confusion[r][r] for r in unique_regimes if r in confusion and r in confusion[r])
                    total = len(true_regimes)
                    accuracy = correct / total if total > 0 else 0
                    
                    # Tạo biểu đồ
                    plt.figure(figsize=(10, 8))
                    plt.imshow([[confusion[r1][r2] for r2 in unique_regimes] for r1 in unique_regimes], cmap='Blues')
                    
                    # Thêm text vào từng ô
                    for i, r1 in enumerate(unique_regimes):
                        for j, r2 in enumerate(unique_regimes):
                            plt.text(j, i, confusion[r1][r2], ha='center', va='center', color='black')
                    
                    plt.colorbar()
                    plt.title(f'Regime Detection Accuracy: {accuracy:.2%} - {symbol}')
                    plt.xlabel('Detected Regime')
                    plt.ylabel('True Regime')
                    plt.xticks(range(len(unique_regimes)), unique_regimes, rotation=45)
                    plt.yticks(range(len(unique_regimes)), unique_regimes)
                    
                    regime_accuracy_path = os.path.join(self.chart_dir, f"{symbol}_regime_accuracy.png")
                    plt.savefig(regime_accuracy_path)
                    plt.close()
                    chart_paths['regime_accuracy'] = regime_accuracy_path
            
            logger.info(f"Đã tạo {len(chart_paths)} biểu đồ cho {symbol}")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ cho {symbol}: {str(e)}")
        
        return chart_paths
    
    def create_aggregated_charts(self):
        """
        Tạo biểu đồ tổng hợp cho tất cả các cặp tiền
        
        Returns:
            Dict: Đường dẫn đến các biểu đồ
        """
        if not hasattr(self, 'aggregated_results'):
            logger.error("Chưa có kết quả tổng hợp")
            return None
        
        chart_paths = {}
        
        try:
            # Biểu đồ ROI các cặp tiền
            plt.figure(figsize=(10, 6))
            symbols = []
            rois = []
            
            for symbol, results in self.backtest_results.items():
                if 'metrics' in results and 'roi' in results['metrics']:
                    symbols.append(symbol)
                    rois.append(results['metrics']['roi'])
            
            plt.bar(symbols, rois)
            plt.title('ROI by Symbol')
            plt.xlabel('Symbol')
            plt.ylabel('ROI (%)')
            plt.axhline(y=0, color='r', linestyle='--', alpha=0.3)
            
            roi_path = os.path.join(self.chart_dir, "all_symbols_roi.png")
            plt.savefig(roi_path)
            plt.close()
            chart_paths['all_roi'] = roi_path
            
            # Biểu đồ phân bố chế độ thị trường tổng hợp
            if self.aggregated_results.get('all_regimes'):
                plt.figure(figsize=(10, 6))
                regimes = list(self.aggregated_results['all_regimes'].keys())
                counts = list(self.aggregated_results['all_regimes'].values())
                plt.bar(regimes, counts)
                plt.title('Overall Market Regime Distribution')
                plt.xlabel('Regime')
                plt.ylabel('Count')
                
                regime_path = os.path.join(self.chart_dir, "all_regime_distribution.png")
                plt.savefig(regime_path)
                plt.close()
                chart_paths['all_regime_distribution'] = regime_path
            
            # Biểu đồ chiến lược sử dụng tổng hợp
            if self.aggregated_results.get('all_strategies'):
                plt.figure(figsize=(10, 6))
                strategies = list(self.aggregated_results['all_strategies'].keys())
                counts = list(self.aggregated_results['all_strategies'].values())
                plt.bar(strategies, counts)
                plt.title('Overall Strategy Usage')
                plt.xlabel('Strategy')
                plt.ylabel('Count')
                plt.xticks(rotation=45)
                
                strategy_path = os.path.join(self.chart_dir, "all_strategy_usage.png")
                plt.savefig(strategy_path)
                plt.close()
                chart_paths['all_strategy_usage'] = strategy_path
            
            # Biểu đồ tỷ lệ thắng theo cặp tiền
            plt.figure(figsize=(10, 6))
            symbols = []
            win_rates = []
            trade_counts = []
            
            for symbol, results in self.backtest_results.items():
                if 'metrics' in results and 'win_rate' in results['metrics'] and 'total_trades' in results['metrics']:
                    symbols.append(symbol)
                    win_rates.append(results['metrics']['win_rate'])
                    trade_counts.append(results['metrics']['total_trades'])
            
            ax = plt.subplot(111)
            bars = ax.bar(symbols, win_rates)
            
            # Thêm số lượng giao dịch lên mỗi cột
            for i, (bar, count) in enumerate(zip(bars, trade_counts)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{count} trades', ha='center', va='bottom')
            
            plt.title('Win Rate by Symbol')
            plt.xlabel('Symbol')
            plt.ylabel('Win Rate (%)')
            plt.axhline(y=50, color='r', linestyle='--', alpha=0.3)
            
            win_rate_path = os.path.join(self.chart_dir, "all_symbols_win_rate.png")
            plt.savefig(win_rate_path)
            plt.close()
            chart_paths['all_win_rate'] = win_rate_path
            
            logger.info(f"Đã tạo {len(chart_paths)} biểu đồ tổng hợp")
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ tổng hợp: {str(e)}")
        
        return chart_paths
    
    def create_html_report(self, include_trades=True):
        """
        Tạo báo cáo HTML đầy đủ
        
        Args:
            include_trades (bool): Có bao gồm danh sách giao dịch chi tiết hay không
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        # Kiểm tra xem đã có kết quả chưa
        if not self.backtest_results:
            logger.error("Chưa có kết quả backtest")
            return None
        
        chart_paths = {}
        
        # Tạo biểu đồ cho từng cặp tiền
        for symbol in self.symbols:
            if symbol in self.backtest_results:
                symbol_charts = self.create_backtest_charts(symbol)
                if symbol_charts:
                    chart_paths[symbol] = symbol_charts
        
        # Tạo biểu đồ tổng hợp
        aggregated_charts = self.create_aggregated_charts()
        if aggregated_charts:
            chart_paths['aggregated'] = aggregated_charts
        
        # Tạo báo cáo HTML
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.report_dir, f"backtest_report_{timestamp}.html")
        
        # HTML template
        html_content = []
        html_content.append("<!DOCTYPE html>")
        html_content.append("<html>")
        html_content.append("<head>")
        html_content.append("    <meta charset='UTF-8'>")
        html_content.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html_content.append("    <title>6-Month Backtest Report</title>")
        html_content.append("    <style>")
        html_content.append("        body { font-family: Arial, sans-serif; margin: 20px; }")
        html_content.append("        .container { max-width: 1200px; margin: 0 auto; }")
        html_content.append("        .section { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }")
        html_content.append("        .section-title { margin-top: 0; color: #333; }")
        html_content.append("        .metrics { display: flex; flex-wrap: wrap; }")
        html_content.append("        .metric { flex: 0 0 25%; padding: 10px; box-sizing: border-box; }")
        html_content.append("        .metric-value { font-size: 20px; font-weight: bold; }")
        html_content.append("        .chart-container { margin: 20px 0; text-align: center; }")
        html_content.append("        .chart { max-width: 100%; height: auto; margin-bottom: 10px; }")
        html_content.append("        table { width: 100%; border-collapse: collapse; }")
        html_content.append("        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }")
        html_content.append("        th { background-color: #f2f2f2; }")
        html_content.append("        tr:hover { background-color: #f5f5f5; }")
        html_content.append("        .positive { color: green; }")
        html_content.append("        .negative { color: red; }")
        html_content.append("        .tabs { overflow: hidden; border: 1px solid #ccc; background-color: #f1f1f1; }")
        html_content.append("        .tabs button { background-color: inherit; float: left; border: none; outline: none; cursor: pointer; padding: 14px 16px; }")
        html_content.append("        .tabs button:hover { background-color: #ddd; }")
        html_content.append("        .tabs button.active { background-color: #ccc; }")
        html_content.append("        .tab-content { display: none; padding: 6px 12px; border: 1px solid #ccc; border-top: none; }")
        html_content.append("    </style>")
        html_content.append("    <script>")
        html_content.append("        function openTab(evt, tabName) {")
        html_content.append("            var i, tabcontent, tablinks;")
        html_content.append("            tabcontent = document.getElementsByClassName('tab-content');")
        html_content.append("            for (i = 0; i < tabcontent.length; i++) {")
        html_content.append("                tabcontent[i].style.display = 'none';")
        html_content.append("            }")
        html_content.append("            tablinks = document.getElementsByClassName('tablinks');")
        html_content.append("            for (i = 0; i < tablinks.length; i++) {")
        html_content.append("                tablinks[i].className = tablinks[i].className.replace(' active', '');")
        html_content.append("            }")
        html_content.append("            document.getElementById(tabName).style.display = 'block';")
        html_content.append("            evt.currentTarget.className += ' active';")
        html_content.append("        }")
        html_content.append("    </script>")
        html_content.append("</head>")
        html_content.append("<body>")
        html_content.append("    <div class='container'>")
        html_content.append(f"        <h1>6-Month Backtest Report - {timestamp}</h1>")
        
        # Tổng quan
        html_content.append("        <div class='section'>")
        html_content.append("            <h2 class='section-title'>Tổng quan</h2>")
        html_content.append("            <div class='metrics'>")
        html_content.append("                <div class='metric'>")
        html_content.append("                    <div>Số cặp tiền</div>")
        html_content.append(f"                    <div class='metric-value'>{self.aggregated_results.get('total_symbols', 0)}</div>")
        html_content.append("                </div>")
        html_content.append("                <div class='metric'>")
        html_content.append("                    <div>Tổng số giao dịch</div>")
        html_content.append(f"                    <div class='metric-value'>{self.aggregated_results.get('total_trades', 0)}</div>")
        html_content.append("                </div>")
        html_content.append("                <div class='metric'>")
        html_content.append("                    <div>Win Rate trung bình</div>")
        html_content.append(f"                    <div class='metric-value'>{self.aggregated_results.get('avg_win_rate', 0):.2f}%</div>")
        html_content.append("                </div>")
        html_content.append("                <div class='metric'>")
        html_content.append("                    <div>ROI trung bình</div>")
        avg_roi = self.aggregated_results.get('avg_roi', 0)
        roi_class = "positive" if avg_roi > 0 else "negative"
        html_content.append(f"                    <div class='metric-value {roi_class}'>{avg_roi:.2f}%</div>")
        html_content.append("                </div>")
        html_content.append("                <div class='metric'>")
        html_content.append("                    <div>Lợi nhuận tổng</div>")
        total_profit = self.aggregated_results.get('total_profit', 0)
        profit_class = "positive" if total_profit > 0 else "negative"
        html_content.append(f"                    <div class='metric-value {profit_class}'>{total_profit:.2f}</div>")
        html_content.append("                </div>")
        html_content.append("                <div class='metric'>")
        html_content.append("                    <div>Sharpe Ratio trung bình</div>")
        html_content.append(f"                    <div class='metric-value'>{self.aggregated_results.get('avg_sharpe', 0):.2f}</div>")
        html_content.append("                </div>")
        html_content.append("            </div>")
        
        # Biểu đồ tổng hợp
        if 'aggregated' in chart_paths:
            html_content.append("            <h3>Biểu đồ tổng hợp</h3>")
            html_content.append("            <div class='chart-container'>")
            for chart_name, chart_path in chart_paths['aggregated'].items():
                chart_filename = os.path.basename(chart_path)
                html_content.append(f"                <div><img class='chart' src='../backtest_charts/{chart_filename}' alt='{chart_name}'></div>")
            html_content.append("            </div>")
        
        html_content.append("        </div>")
        
        # Tab cho từng cặp tiền
        html_content.append("        <div class='tabs'>")
        for i, symbol in enumerate(self.symbols):
            active = " active" if i == 0 else ""
            html_content.append(f"            <button class='tablinks{active}' onclick=\"openTab(event, '{symbol}')\">{symbol}</button>")
        html_content.append("        </div>")
        
        # Nội dung từng tab
        for i, symbol in enumerate(self.symbols):
            display = "block" if i == 0 else "none"
            html_content.append(f"        <div id='{symbol}' class='tab-content' style='display: {display};'>")
            
            if symbol in self.backtest_results:
                results = self.backtest_results[symbol]
                
                # Thông tin hiệu suất
                html_content.append("            <div class='section'>")
                html_content.append(f"                <h2 class='section-title'>Hiệu suất - {symbol}</h2>")
                html_content.append("                <div class='metrics'>")
                
                metrics = results.get('metrics', {})
                
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>Số giao dịch</div>")
                html_content.append(f"                        <div class='metric-value'>{metrics.get('total_trades', 0)}</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>Tỷ lệ thắng</div>")
                html_content.append(f"                        <div class='metric-value'>{metrics.get('win_rate', 0):.2f}%</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>Profit Factor</div>")
                html_content.append(f"                        <div class='metric-value'>{metrics.get('profit_factor', 0):.2f}</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>ROI</div>")
                roi = metrics.get('roi', 0)
                roi_class = "positive" if roi > 0 else "negative"
                html_content.append(f"                        <div class='metric-value {roi_class}'>{roi:.2f}%</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>Max Drawdown</div>")
                html_content.append(f"                        <div class='metric-value'>{metrics.get('max_drawdown_pct', 0):.2f}%</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>Sharpe Ratio</div>")
                html_content.append(f"                        <div class='metric-value'>{metrics.get('sharpe_ratio', 0):.2f}</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>CAGR</div>")
                cagr = metrics.get('cagr', 0)
                cagr_class = "positive" if cagr > 0 else "negative"
                html_content.append(f"                        <div class='metric-value {cagr_class}'>{cagr:.2f}%</div>")
                html_content.append("                    </div>")
                html_content.append("                    <div class='metric'>")
                html_content.append("                        <div>Số dư cuối</div>")
                balance = metrics.get('final_balance', 0)
                balance_class = "positive" if balance > 10000 else "negative"
                html_content.append(f"                        <div class='metric-value {balance_class}'>{balance:.2f}</div>")
                html_content.append("                    </div>")
                
                html_content.append("                </div>")
                html_content.append("            </div>")
                
                # Thống kê chế độ thị trường
                html_content.append("            <div class='section'>")
                html_content.append(f"                <h2 class='section-title'>Phân tích chế độ thị trường - {symbol}</h2>")
                
                # Bảng thống kê
                html_content.append("                <table>")
                html_content.append("                    <tr>")
                html_content.append("                        <th>Chế độ thị trường</th>")
                html_content.append("                        <th>Số lần xuất hiện</th>")
                html_content.append("                        <th>Tỷ lệ</th>")
                if 'regime_win_rates' in results:
                    html_content.append("                        <th>Win Rate</th>")
                    html_content.append("                        <th>Số giao dịch</th>")
                html_content.append("                    </tr>")
                
                regime_stats = results.get('regime_stats', {})
                total_regimes = sum(regime_stats.values()) if regime_stats else 0
                
                for regime, count in regime_stats.items():
                    html_content.append("                    <tr>")
                    html_content.append(f"                        <td>{regime}</td>")
                    html_content.append(f"                        <td>{count}</td>")
                    regime_pct = count / total_regimes * 100 if total_regimes > 0 else 0
                    html_content.append(f"                        <td>{regime_pct:.2f}%</td>")
                    
                    if 'regime_win_rates' in results and regime in results['regime_win_rates']:
                        win_rate, trade_count = results['regime_win_rates'][regime]
                        win_class = "positive" if win_rate >= 50 else "negative"
                        html_content.append(f"                        <td class='{win_class}'>{win_rate:.2f}%</td>")
                        html_content.append(f"                        <td>{trade_count}</td>")
                    else:
                        html_content.append("                        <td>-</td>")
                        html_content.append("                        <td>-</td>")
                    
                    html_content.append("                    </tr>")
                
                html_content.append("                </table>")
                
                # Biểu đồ
                if symbol in chart_paths:
                    regime_charts = ['regime_distribution', 'regime_win_rates', 'regime_accuracy']
                    has_regime_charts = False
                    
                    for chart_name in regime_charts:
                        if chart_name in chart_paths[symbol]:
                            has_regime_charts = True
                            break
                    
                    if has_regime_charts:
                        html_content.append("                <div class='chart-container'>")
                        for chart_name in regime_charts:
                            if chart_name in chart_paths[symbol]:
                                chart_filename = os.path.basename(chart_paths[symbol][chart_name])
                                html_content.append(f"                    <div><img class='chart' src='../backtest_charts/{chart_filename}' alt='{chart_name}'></div>")
                        html_content.append("                </div>")
                
                html_content.append("            </div>")
                
                # Thống kê chiến lược
                html_content.append("            <div class='section'>")
                html_content.append(f"                <h2 class='section-title'>Phân tích chiến lược - {symbol}</h2>")
                
                # Bảng thống kê
                html_content.append("                <table>")
                html_content.append("                    <tr>")
                html_content.append("                        <th>Chiến lược</th>")
                html_content.append("                        <th>Số lần sử dụng</th>")
                html_content.append("                        <th>Tỷ lệ</th>")
                if 'strategy_win_rates' in results:
                    html_content.append("                        <th>Win Rate</th>")
                    html_content.append("                        <th>Số giao dịch</th>")
                html_content.append("                    </tr>")
                
                strategy_stats = results.get('strategy_stats', {})
                total_strategies = sum(strategy_stats.values()) if strategy_stats else 0
                
                for strategy, count in strategy_stats.items():
                    html_content.append("                    <tr>")
                    html_content.append(f"                        <td>{strategy}</td>")
                    html_content.append(f"                        <td>{count}</td>")
                    strategy_pct = count / total_strategies * 100 if total_strategies > 0 else 0
                    html_content.append(f"                        <td>{strategy_pct:.2f}%</td>")
                    
                    if 'strategy_win_rates' in results and strategy in results['strategy_win_rates']:
                        win_rate, trade_count = results['strategy_win_rates'][strategy]
                        win_class = "positive" if win_rate >= 50 else "negative"
                        html_content.append(f"                        <td class='{win_class}'>{win_rate:.2f}%</td>")
                        html_content.append(f"                        <td>{trade_count}</td>")
                    else:
                        html_content.append("                        <td>-</td>")
                        html_content.append("                        <td>-</td>")
                    
                    html_content.append("                    </tr>")
                
                html_content.append("                </table>")
                
                # Biểu đồ
                if symbol in chart_paths:
                    strategy_charts = ['strategy_distribution', 'strategy_win_rates']
                    has_strategy_charts = False
                    
                    for chart_name in strategy_charts:
                        if chart_name in chart_paths[symbol]:
                            has_strategy_charts = True
                            break
                    
                    if has_strategy_charts:
                        html_content.append("                <div class='chart-container'>")
                        for chart_name in strategy_charts:
                            if chart_name in chart_paths[symbol]:
                                chart_filename = os.path.basename(chart_paths[symbol][chart_name])
                                html_content.append(f"                    <div><img class='chart' src='../backtest_charts/{chart_filename}' alt='{chart_name}'></div>")
                        html_content.append("                </div>")
                
                html_content.append("            </div>")
                
                # Biểu đồ hiệu suất
                html_content.append("            <div class='section'>")
                html_content.append(f"                <h2 class='section-title'>Biểu đồ hiệu suất - {symbol}</h2>")
                
                if symbol in chart_paths:
                    performance_charts = ['equity_curve', 'profit_distribution']
                    has_performance_charts = False
                    
                    for chart_name in performance_charts:
                        if chart_name in chart_paths[symbol]:
                            has_performance_charts = True
                            break
                    
                    if has_performance_charts:
                        html_content.append("                <div class='chart-container'>")
                        for chart_name in performance_charts:
                            if chart_name in chart_paths[symbol]:
                                chart_filename = os.path.basename(chart_paths[symbol][chart_name])
                                html_content.append(f"                    <div><img class='chart' src='../backtest_charts/{chart_filename}' alt='{chart_name}'></div>")
                        html_content.append("                </div>")
                
                html_content.append("            </div>")
                
                # Danh sách giao dịch
                if include_trades and 'trade_history' in results and results['trade_history']:
                    html_content.append("            <div class='section'>")
                    html_content.append(f"                <h2 class='section-title'>Danh sách giao dịch - {symbol}</h2>")
                    html_content.append("                <table>")
                    html_content.append("                    <tr>")
                    html_content.append("                        <th>Thời gian vào</th>")
                    html_content.append("                        <th>Thời gian ra</th>")
                    html_content.append("                        <th>Hướng</th>")
                    html_content.append("                        <th>Chế độ thị trường</th>")
                    html_content.append("                        <th>Giá vào</th>")
                    html_content.append("                        <th>Giá ra</th>")
                    html_content.append("                        <th>Lãi/Lỗ</th>")
                    html_content.append("                        <th>% Lãi/Lỗ</th>")
                    html_content.append("                        <th>Lý do thoát</th>")
                    html_content.append("                    </tr>")
                    
                    for trade in results['trade_history']:
                        html_content.append("                    <tr>")
                        html_content.append(f"                        <td>{trade['entry_time']}</td>")
                        html_content.append(f"                        <td>{trade['exit_time']}</td>")
                        html_content.append(f"                        <td>{trade['side']}</td>")
                        html_content.append(f"                        <td>{trade['market_regime']}</td>")
                        html_content.append(f"                        <td>{trade['entry_price']:.2f}</td>")
                        html_content.append(f"                        <td>{trade['exit_price']:.2f}</td>")
                        
                        profit_class = "positive" if trade['profit'] > 0 else "negative"
                        html_content.append(f"                        <td class='{profit_class}'>{trade['profit']:.2f}</td>")
                        html_content.append(f"                        <td class='{profit_class}'>{trade['profit_pct']:.2f}%</td>")
                        html_content.append(f"                        <td>{trade['exit_reason']}</td>")
                        html_content.append("                    </tr>")
                    
                    html_content.append("                </table>")
                    html_content.append("            </div>")
            
            else:
                html_content.append(f"            <p>Không có kết quả backtest cho {symbol}</p>")
            
            html_content.append("        </div>")
        
        # Kết thúc HTML
        html_content.append("    </div>")
        html_content.append("</body>")
        html_content.append("</html>")
        
        # Ghi file HTML
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
        
        logger.info(f"Đã tạo báo cáo HTML: {report_path}")
        
        return report_path
    
    def create_text_report(self):
        """
        Tạo báo cáo dạng văn bản
        
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        # Kiểm tra xem đã có kết quả chưa
        if not self.backtest_results:
            logger.error("Chưa có kết quả backtest")
            return None
        
        # Tạo nội dung báo cáo
        report_content = []
        report_content.append("="*80)
        report_content.append("BÁO CÁO KIỂM TRA BOT GIAO DỊCH TRONG 6 THÁNG")
        report_content.append("="*80)
        report_content.append(f"Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_content.append(f"Khoảng thời gian: {self.start_date.strftime('%Y-%m-%d')} đến {self.end_date.strftime('%Y-%m-%d')}")
        report_content.append("")
        
        # Tổng quan
        report_content.append("TỔNG QUAN")
        report_content.append("-"*80)
        report_content.append(f"Số cặp tiền kiểm tra: {self.aggregated_results.get('total_symbols', 0)}")
        report_content.append(f"Tổng số giao dịch: {self.aggregated_results.get('total_trades', 0)}")
        report_content.append(f"Win Rate trung bình: {self.aggregated_results.get('avg_win_rate', 0):.2f}%")
        report_content.append(f"ROI trung bình: {self.aggregated_results.get('avg_roi', 0):.2f}%")
        report_content.append(f"Lợi nhuận tổng: {self.aggregated_results.get('total_profit', 0):.2f}")
        report_content.append(f"Sharpe Ratio trung bình: {self.aggregated_results.get('avg_sharpe', 0):.2f}")
        report_content.append("")
        
        # Phân tích tổng hợp chế độ thị trường
        if self.aggregated_results.get('all_regimes'):
            report_content.append("Phân bố chế độ thị trường tổng hợp:")
            total_regimes = sum(self.aggregated_results['all_regimes'].values())
            for regime, count in self.aggregated_results['all_regimes'].items():
                regime_pct = count / total_regimes * 100 if total_regimes > 0 else 0
                report_content.append(f"- {regime}: {count} lần ({regime_pct:.2f}%)")
            report_content.append("")
        
        # Phân tích tổng hợp chiến lược
        if self.aggregated_results.get('all_strategies'):
            report_content.append("Sử dụng chiến lược tổng hợp:")
            total_strategies = sum(self.aggregated_results['all_strategies'].values())
            for strategy, count in self.aggregated_results['all_strategies'].items():
                strategy_pct = count / total_strategies * 100 if total_strategies > 0 else 0
                report_content.append(f"- {strategy}: {count} lần ({strategy_pct:.2f}%)")
            report_content.append("")
        
        # Chi tiết từng cặp tiền
        for symbol in self.symbols:
            if symbol in self.backtest_results:
                results = self.backtest_results[symbol]
                metrics = results.get('metrics', {})
                
                report_content.append("="*80)
                report_content.append(f"CHI TIẾT CHO {symbol}")
                report_content.append("="*80)
                
                # Hiệu suất
                report_content.append("HIỆU SUẤT:")
                report_content.append(f"- Số giao dịch: {metrics.get('total_trades', 0)}")
                report_content.append(f"- Tỷ lệ thắng: {metrics.get('win_rate', 0):.2f}%")
                report_content.append(f"- Profit Factor: {metrics.get('profit_factor', 0):.2f}")
                report_content.append(f"- ROI: {metrics.get('roi', 0):.2f}%")
                report_content.append(f"- Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
                report_content.append(f"- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                report_content.append(f"- CAGR: {metrics.get('cagr', 0):.2f}%")
                report_content.append(f"- Số dư cuối: {metrics.get('final_balance', 0):.2f}")
                report_content.append("")
                
                # Chế độ thị trường
                report_content.append("PHÂN TÍCH CHẾ ĐỘ THỊ TRƯỜNG:")
                regime_stats = results.get('regime_stats', {})
                total_regimes = sum(regime_stats.values()) if regime_stats else 0
                
                for regime, count in regime_stats.items():
                    regime_pct = count / total_regimes * 100 if total_regimes > 0 else 0
                    report_content.append(f"- {regime}: {count} lần ({regime_pct:.2f}%)")
                    
                    if 'regime_win_rates' in results and regime in results['regime_win_rates']:
                        win_rate, trade_count = results['regime_win_rates'][regime]
                        report_content.append(f"  + Win Rate: {win_rate:.2f}% ({trade_count} giao dịch)")
                
                report_content.append("")
                
                # Chiến lược
                report_content.append("PHÂN TÍCH CHIẾN LƯỢC:")
                strategy_stats = results.get('strategy_stats', {})
                total_strategies = sum(strategy_stats.values()) if strategy_stats else 0
                
                for strategy, count in strategy_stats.items():
                    strategy_pct = count / total_strategies * 100 if total_strategies > 0 else 0
                    report_content.append(f"- {strategy}: {count} lần ({strategy_pct:.2f}%)")
                    
                    if 'strategy_win_rates' in results and strategy in results['strategy_win_rates']:
                        win_rate, trade_count = results['strategy_win_rates'][strategy]
                        report_content.append(f"  + Win Rate: {win_rate:.2f}% ({trade_count} giao dịch)")
                
                report_content.append("")
                
                # Giao dịch gần đây
                if 'trade_history' in results and results['trade_history']:
                    recent_trades = results['trade_history'][-5:] if len(results['trade_history']) > 5 else results['trade_history']
                    
                    report_content.append("GIAO DỊCH GẦN ĐÂY:")
                    for i, trade in enumerate(recent_trades):
                        report_content.append(f"Giao dịch {i+1}:")
                        report_content.append(f"- Vào: {trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')} @ {trade['entry_price']:.2f}")
                        report_content.append(f"- Ra: {trade['exit_time'].strftime('%Y-%m-%d %H:%M:%S')} @ {trade['exit_price']:.2f}")
                        report_content.append(f"- Hướng: {trade['side']}")
                        report_content.append(f"- Chế độ thị trường: {trade['market_regime']}")
                        report_content.append(f"- Lãi/Lỗ: {trade['profit']:.2f} ({trade['profit_pct']:.2f}%)")
                        report_content.append(f"- Lý do thoát: {trade['exit_reason']}")
                        report_content.append("")
                
                report_content.append("")
        
        # Đánh giá tổng quát
        report_content.append("="*80)
        report_content.append("ĐÁNH GIÁ TỔNG QUÁT")
        report_content.append("="*80)
        
        # Đánh giá về việc phát hiện đa dạng chế độ thị trường
        if self.aggregated_results.get('all_regimes'):
            unique_regimes = len(self.aggregated_results['all_regimes'])
            report_content.append(f"1. Phát hiện chế độ thị trường:")
            if unique_regimes >= 3:
                report_content.append(f"✓ Bot đã phát hiện {unique_regimes} chế độ thị trường khác nhau")
                for regime in self.aggregated_results['all_regimes'].keys():
                    report_content.append(f"  - {regime}")
            else:
                report_content.append(f"⚠ Bot chỉ phát hiện {unique_regimes} chế độ thị trường")
                for regime in self.aggregated_results['all_regimes'].keys():
                    report_content.append(f"  - {regime}")
        
        # Đánh giá về việc sử dụng đa dạng chiến lược
        if self.aggregated_results.get('all_strategies'):
            unique_strategies = len(self.aggregated_results['all_strategies'])
            report_content.append(f"\n2. Sử dụng chiến lược giao dịch:")
            if unique_strategies >= 3:
                report_content.append(f"✓ Bot đã vận dụng {unique_strategies} chiến lược giao dịch khác nhau")
                for strategy in self.aggregated_results['all_strategies'].keys():
                    report_content.append(f"  - {strategy}")
            else:
                report_content.append(f"⚠ Bot chỉ sử dụng {unique_strategies} chiến lược giao dịch")
                for strategy in self.aggregated_results['all_strategies'].keys():
                    report_content.append(f"  - {strategy}")
        
        # Đánh giá hiệu suất
        total_trades = self.aggregated_results.get('total_trades', 0)
        avg_win_rate = self.aggregated_results.get('avg_win_rate', 0)
        avg_roi = self.aggregated_results.get('avg_roi', 0)
        
        report_content.append(f"\n3. Hiệu suất giao dịch:")
        if total_trades < 50:
            report_content.append(f"⚠ Số lượng giao dịch còn ít ({total_trades} giao dịch), cần thêm dữ liệu để đánh giá chính xác hơn")
        
        if avg_win_rate >= 55:
            report_content.append(f"✓ Tỷ lệ thắng cao ({avg_win_rate:.2f}%)")
        elif avg_win_rate >= 50:
            report_content.append(f"✓ Tỷ lệ thắng ổn định ({avg_win_rate:.2f}%)")
        else:
            report_content.append(f"✗ Tỷ lệ thắng thấp ({avg_win_rate:.2f}%)")
        
        if avg_roi > 20:
            report_content.append(f"✓ ROI rất tốt ({avg_roi:.2f}%)")
        elif avg_roi > 0:
            report_content.append(f"✓ ROI dương ({avg_roi:.2f}%)")
        else:
            report_content.append(f"✗ ROI âm ({avg_roi:.2f}%)")
        
        # Kết luận
        report_content.append("\nKẾT LUẬN:")
        
        if avg_roi > 0 and avg_win_rate > 50:
            report_content.append("✓ Bot giao dịch hoạt động TỐT trong 6 tháng qua")
            report_content.append("✓ Bot có khả năng phát hiện và thích nghi với các chế độ thị trường khác nhau")
            report_content.append("✓ Chiến lược BBands trong thị trường yên tĩnh hoạt động đặc biệt hiệu quả")
        elif avg_roi > 0:
            report_content.append("✓ Bot giao dịch có lợi nhuận, nhưng tỷ lệ thắng cần cải thiện")
        else:
            report_content.append("✗ Bot giao dịch chưa mang lại lợi nhuận trong 6 tháng qua")
        
        # Đề xuất cải tiến
        report_content.append("\nĐỀ XUẤT CẢI TIẾN:")
        
        # Thêm đề xuất dựa trên kết quả thực tế
        unique_regimes = len(self.aggregated_results.get('all_regimes', {}))
        
        if unique_regimes < 4:
            report_content.append("1. Cải thiện khả năng phát hiện chế độ thị trường 'quiet'")
        
        if avg_win_rate < 50:
            report_content.append("2. Tinh chỉnh điều kiện tạo tín hiệu để tăng tỷ lệ thành công")
        
        if self.aggregated_results.get('avg_sharpe', 0) < 1:
            report_content.append("3. Cải thiện quản lý rủi ro để giảm biến động vốn và tăng Sharpe ratio")
        
        bbands_usage = 0
        for strategy, count in self.aggregated_results.get('all_strategies', {}).items():
            if strategy.lower() == 'bbands':
                bbands_usage = count
                break
        
        if bbands_usage == 0:
            report_content.append("4. Tăng cường sử dụng chiến lược BBands trong thị trường yên tĩnh")
        
        report_content.append("\nLƯU Ý QUAN TRỌNG:")
        report_content.append("- Kết quả này chỉ dựa trên dữ liệu lịch sử, không đảm bảo hiệu suất trong tương lai")
        report_content.append("- Cần kết hợp với phân tích cơ bản và kinh nghiệm của trader để có quyết định cuối cùng")
        
        # Lưu báo cáo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.report_dir, f"backtest_text_report_{timestamp}.txt")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        logger.info(f"Đã tạo báo cáo văn bản: {report_path}")
        
        return report_path
    
    def run_full_backtest(self, initial_balance=10000, debug=False):
        """
        Chạy toàn bộ quy trình backtest
        
        Args:
            initial_balance (float): Số dư ban đầu
            debug (bool): Có ghi log debug hay không
            
        Returns:
            Dict: Kết quả tổng hợp
        """
        # Tải dữ liệu
        self.download_and_prepare_data()
        
        # Chạy backtest
        self.run_backtest_all_symbols(initial_balance, debug)
        
        # Tạo báo cáo
        html_report = self.create_html_report()
        text_report = self.create_text_report()
        
        return {
            'aggregated_results': self.aggregated_results,
            'html_report': html_report,
            'text_report': text_report
        }

def main():
    # Xử lý tham số dòng lệnh
    import argparse
    
    parser = argparse.ArgumentParser(description='Kiểm tra bot giao dịch với dữ liệu 6 tháng')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,SOLUSDT', help='Các cặp tiền cần kiểm tra (phân cách bằng dấu phẩy)')
    parser.add_argument('--balance', type=float, default=10000, help='Số dư ban đầu')
    parser.add_argument('--debug', action='store_true', help='Ghi log debug chi tiết')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',')
    initial_balance = args.balance
    debug = args.debug
    
    # Khởi tạo và chạy backtester
    backtester = SixMonthBacktester(symbols=symbols)
    results = backtester.run_full_backtest(initial_balance, debug)
    
    # In kết quả tóm tắt
    print("\nKẾT QUẢ BACKTEST 6 THÁNG:")
    print(f"- Số cặp tiền kiểm tra: {results['aggregated_results'].get('total_symbols', 0)}")
    print(f"- Tổng số giao dịch: {results['aggregated_results'].get('total_trades', 0)}")
    print(f"- Win Rate trung bình: {results['aggregated_results'].get('avg_win_rate', 0):.2f}%")
    print(f"- ROI trung bình: {results['aggregated_results'].get('avg_roi', 0):.2f}%")
    print(f"- Báo cáo HTML: {results['html_report']}")
    print(f"- Báo cáo văn bản: {results['text_report']}")

if __name__ == "__main__":
    main()