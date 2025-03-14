#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Strategy Conflict Checker - Công cụ kiểm tra xung đột giữa các chiến lược giao dịch
Phát hiện mâu thuẫn tín hiệu, xung đột vị thế và vấn đề chồng chéo lệnh
"""

import os
import sys
import json
import time
import logging
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('strategy_conflict.log')
    ]
)

logger = logging.getLogger('strategy_conflict')

class StrategyConflictChecker:
    """
    Lớp kiểm tra xung đột giữa các chiến lược giao dịch
    """
    
    def __init__(self, config_path='strategy_conflict_config.json'):
        """
        Khởi tạo StrategyConflictChecker
        
        Args:
            config_path (str): Đường dẫn file cấu hình
        """
        self.config_path = config_path
        self.load_config()
        
        # Biến theo dõi kết quả phân tích
        self.conflicts = []
        self.overlaps = []
        self.strategy_statistics = {}
        
        # Biến theo dõi trạng thái
        self.signals = {}
        self.positions = {}
        
        # Tạo thư mục kết quả
        self.results_dir = 'conflict_results'
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info("Đã khởi tạo Strategy Conflict Checker")
    
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
                    'strategies': [
                        'ema_crossover',
                        'macd_divergence',
                        'rsi_extreme',
                        'supertrend',
                        'bollinger_bands_squeeze',
                        'hedge_mode',
                        'adaptive_mode',
                        'volatility_breakout'
                    ],
                    'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'],
                    'timeframes': ['1m', '5m', '15m', '1h', '4h', '1d'],
                    'test_days': 30,
                    'conflict_thresholds': {
                        'signal_conflict_percentage': 20,  # Phần trăm xung đột tín hiệu cho phép
                        'position_overlap_percentage': 10,  # Phần trăm chồng chéo vị thế cho phép
                        'time_window_minutes': 30,  # Cửa sổ thời gian để phát hiện xung đột (phút)
                        'min_signals_for_analysis': 10  # Số lượng tín hiệu tối thiểu để phân tích
                    },
                    'file_paths': {
                        'historical_data_dir': 'data',  # Thư mục chứa dữ liệu lịch sử
                        'strategy_signals_dir': 'signals',  # Thư mục chứa tín hiệu chiến lược
                        'backtest_results_dir': 'backtest_results'  # Thư mục chứa kết quả backtest
                    }
                }
                
                # Lưu cấu hình
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                
                logger.info(f"Đã tạo cấu hình mặc định và lưu vào {self.config_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            raise
    
    def load_strategy_signals(self, strategy, symbol, timeframe):
        """
        Tải tín hiệu từ một chiến lược
        
        Args:
            strategy (str): Tên chiến lược
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame chứa tín hiệu
        """
        try:
            # Kiểm tra xem có thư mục chứa tín hiệu không
            signals_dir = self.config['file_paths']['strategy_signals_dir']
            os.makedirs(signals_dir, exist_ok=True)
            
            # Đường dẫn file tín hiệu
            signals_file = os.path.join(signals_dir, f"{strategy}_{symbol}_{timeframe}_signals.csv")
            
            # Kiểm tra xem có file tín hiệu không
            if os.path.exists(signals_file):
                logger.info(f"Tải tín hiệu từ {signals_file}")
                df = pd.read_csv(signals_file)
                
                # Đảm bảo có cột thời gian
                if 'timestamp' not in df.columns:
                    logger.warning(f"File {signals_file} không có cột timestamp")
                    return None
                
                # Chuyển đổi timestamp sang datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                return df
            else:
                logger.warning(f"Không tìm thấy file tín hiệu {signals_file}")
                
                # Tạo tín hiệu mới nếu không có file
                df = self._generate_mock_signals(strategy, symbol, timeframe)
                
                # Lưu tín hiệu mới
                df.to_csv(signals_file, index=False)
                logger.info(f"Đã tạo và lưu tín hiệu mới vào {signals_file}")
                
                return df
        
        except Exception as e:
            logger.error(f"Lỗi khi tải tín hiệu của chiến lược {strategy} cho {symbol} {timeframe}: {e}")
            return None
    
    def _generate_mock_signals(self, strategy, symbol, timeframe):
        """
        Tạo tín hiệu mô phỏng cho mục đích kiểm tra
        
        Args:
            strategy (str): Tên chiến lược
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame chứa tín hiệu mô phỏng
        """
        logger.info(f"Tạo tín hiệu mô phỏng cho {strategy} - {symbol} - {timeframe}")
        
        # Tạo dữ liệu thời gian
        end_date = datetime.datetime.now()
        
        # Số ngày kiểm tra
        days = self.config['test_days']
        
        # Tính khoảng thời gian dựa trên timeframe
        if timeframe == '1m':
            start_date = end_date - datetime.timedelta(days=1)  # 1 ngày dữ liệu 1m
            freq = 'min'
        elif timeframe == '5m':
            start_date = end_date - datetime.timedelta(days=5)  # 5 ngày dữ liệu 5m
            freq = '5min'
        elif timeframe == '15m':
            start_date = end_date - datetime.timedelta(days=10)  # 10 ngày dữ liệu 15m
            freq = '15min'
        elif timeframe == '1h':
            start_date = end_date - datetime.timedelta(days=days)  # X ngày dữ liệu 1h
            freq = 'H'
        elif timeframe == '4h':
            start_date = end_date - datetime.timedelta(days=days)  # X ngày dữ liệu 4h
            freq = '4H'
        else:  # 1d
            start_date = end_date - datetime.timedelta(days=days * 2)  # 2X ngày dữ liệu 1d
            freq = 'D'
        
        # Tạo dãy thời gian
        timestamps = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        # Tạo DataFrame mới
        df = pd.DataFrame({'timestamp': timestamps})
        
        # Thêm cột tín hiệu
        # 1 = mua, -1 = bán, 0 = không có tín hiệu
        
        # Tạo tín hiệu dựa trên chiến lược
        if strategy == 'ema_crossover':
            # Tín hiệu EMA crossover thường có xu hướng theo đám đông
            signals = np.zeros(len(df))
            
            # Tạo xu hướng cơ bản
            trend = np.cumsum(np.random.normal(0, 1, len(df)))
            
            # Tạo tín hiệu dựa trên xu hướng
            signals[trend > 0.5] = 1  # Tín hiệu mua khi xu hướng tăng mạnh
            signals[trend < -0.5] = -1  # Tín hiệu bán khi xu hướng giảm mạnh
            
            # Đảm bảo tín hiệu không liên tiếp quá nhiều
            for i in range(1, len(signals)):
                if signals[i] == signals[i-1] and signals[i] != 0:
                    if np.random.random() < 0.7:  # 70% chance to revert to neutral
                        signals[i] = 0
            
            df['signal'] = signals
            
        elif strategy == 'macd_divergence':
            # MACD divergence thường tạo tín hiệu reversal (đảo chiều)
            signals = np.zeros(len(df))
            
            # Tạo xu hướng cơ bản
            trend = np.cumsum(np.random.normal(0, 1, len(df)))
            
            # Tạo tín hiệu đảo chiều
            for i in range(10, len(trend)):
                if trend[i] > trend[i-5] > trend[i-10] and np.random.random() < 0.3:
                    signals[i] = -1  # Tín hiệu bán khi xu hướng đang tăng
                elif trend[i] < trend[i-5] < trend[i-10] and np.random.random() < 0.3:
                    signals[i] = 1  # Tín hiệu mua khi xu hướng đang giảm
            
            df['signal'] = signals
            
        elif strategy == 'rsi_extreme':
            # RSI extreme thường tạo tín hiệu khi thị trường quá mua/quá bán
            signals = np.zeros(len(df))
            
            # Mô phỏng RSI
            rsi = 50 + 25 * np.sin(np.linspace(0, 10 * np.pi, len(df)))
            rsi += np.random.normal(0, 5, len(df))  # Thêm nhiễu
            
            # Tạo tín hiệu dựa trên RSI
            signals[rsi > 70] = -1  # Tín hiệu bán khi RSI > 70
            signals[rsi < 30] = 1  # Tín hiệu mua khi RSI < 30
            
            df['signal'] = signals
            
        elif strategy == 'supertrend':
            # Supertrend thường theo xu hướng mạnh
            signals = np.zeros(len(df))
            
            # Tạo xu hướng cơ bản
            trend = np.cumsum(np.random.normal(0, 1, len(df)))
            
            # Tạo tín hiệu dựa trên xu hướng
            for i in range(10, len(trend)):
                if all(trend[i-j] > trend[i-j-1] for j in range(5)) and signals[i-1] != 1:
                    signals[i] = 1  # Tín hiệu mua khi xu hướng tăng mạnh
                elif all(trend[i-j] < trend[i-j-1] for j in range(5)) and signals[i-1] != -1:
                    signals[i] = -1  # Tín hiệu bán khi xu hướng giảm mạnh
            
            df['signal'] = signals
            
        elif strategy == 'bollinger_bands_squeeze':
            # Bollinger Bands squeeze thường tạo tín hiệu breakout sau khi volatility thấp
            signals = np.zeros(len(df))
            
            # Tạo mô phỏng volatility
            volatility = np.abs(np.random.normal(0, 1, len(df)))
            volatility = pd.Series(volatility).rolling(10).mean().fillna(0).values
            
            # Tạo tín hiệu dựa trên volatility
            for i in range(10, len(volatility)):
                if volatility[i] > 1.5 * volatility[i-5] and volatility[i-5] < 0.5:
                    signals[i] = 1 if np.random.random() > 0.5 else -1  # Tín hiệu breakout
            
            df['signal'] = signals
            
        elif strategy == 'hedge_mode':
            # Hedge mode thường tạo tín hiệu đồng thời cả long và short
            signals = np.zeros(len(df))
            
            # Tạo biến động thị trường
            volatility = np.abs(np.random.normal(0, 1, len(df)))
            volatility = pd.Series(volatility).rolling(10).mean().fillna(0).values
            
            # Tạo tín hiệu dựa trên volatility
            # 2 = hedge mode (cả long và short)
            signals[volatility > 1.0] = 2  # Tín hiệu hedge khi volatility cao
            
            # Thêm một số tín hiệu long/short khi volatility thấp
            for i in range(len(signals)):
                if signals[i] == 0 and np.random.random() < 0.1:
                    signals[i] = 1 if np.random.random() > 0.5 else -1
            
            df['signal'] = signals
            
        elif strategy == 'adaptive_mode':
            # Adaptive mode chọn chiến lược tối ưu dựa trên điều kiện thị trường
            signals = np.zeros(len(df))
            
            # Mô phỏng các điều kiện thị trường
            trend_strength = np.abs(np.random.normal(0, 1, len(df)))
            trend_strength = pd.Series(trend_strength).rolling(10).mean().fillna(0).values
            
            volatility = np.abs(np.random.normal(0, 1, len(df)))
            volatility = pd.Series(volatility).rolling(10).mean().fillna(0).values
            
            # Tạo tín hiệu dựa trên điều kiện thị trường
            for i in range(10, len(df)):
                if trend_strength[i] > 0.8:  # Xu hướng mạnh
                    signals[i] = 1 if trend_strength[i-5] < trend_strength[i] else -1
                elif volatility[i] > 1.2:  # Biến động cao
                    signals[i] = 2  # Hedge mode
                elif np.random.random() < 0.1:  # Thỉnh thoảng có tín hiệu
                    signals[i] = 1 if np.random.random() > 0.5 else -1
            
            df['signal'] = signals
            
        elif strategy == 'volatility_breakout':
            # Volatility breakout tạo tín hiệu khi volatility tăng đột biến
            signals = np.zeros(len(df))
            
            # Tạo mô phỏng volatility
            volatility = np.abs(np.random.normal(0, 1, len(df)))
            volatility = pd.Series(volatility).rolling(10).mean().fillna(0).values
            
            # Tạo tín hiệu dựa trên volatility
            for i in range(10, len(volatility)):
                if volatility[i] > 2.0 * volatility[i-1]:
                    signals[i] = 1 if np.random.random() > 0.5 else -1  # Tín hiệu breakout
            
            df['signal'] = signals
            
        else:
            # Chiến lược không xác định, tạo tín hiệu ngẫu nhiên
            signals = np.zeros(len(df))
            
            # Xác suất xuất hiện tín hiệu khoảng 10%
            for i in range(len(signals)):
                if np.random.random() < 0.1:
                    signals[i] = 1 if np.random.random() > 0.5 else -1
            
            df['signal'] = signals
        
        # Thêm cột chiến lược
        df['strategy'] = strategy
        
        # Thêm cột symbol và timeframe
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        return df
    
    def check_conflicts(self):
        """
        Kiểm tra xung đột giữa các chiến lược
        
        Returns:
            dict: Kết quả phân tích xung đột
        """
        logger.info("Bắt đầu kiểm tra xung đột giữa các chiến lược...")
        
        # Lấy danh sách chiến lược
        strategies = self.config['strategies']
        
        # Lấy danh sách cặp tiền
        symbols = self.config['symbols']
        
        # Lấy danh sách timeframe
        timeframes = self.config['timeframes']
        
        # Lấy ngưỡng xung đột
        thresholds = self.config['conflict_thresholds']
        
        # Kết quả phân tích
        results = {
            'conflicts': [],
            'overlaps': [],
            'strategy_statistics': {},
            'symbol_statistics': {},
            'timeframe_statistics': {},
            'overall_summary': {},
            'recommendations': []
        }
        
        # Duyệt qua từng cặp tiền
        for symbol in symbols:
            logger.info(f"Kiểm tra xung đột cho {symbol}...")
            
            # Duyệt qua từng timeframe
            for timeframe in timeframes:
                logger.info(f"Kiểm tra xung đột cho {symbol} {timeframe}...")
                
                # Tải tín hiệu của tất cả chiến lược
                strategy_signals = {}
                for strategy in strategies:
                    signals = self.load_strategy_signals(strategy, symbol, timeframe)
                    if signals is not None and not signals.empty:
                        strategy_signals[strategy] = signals
                
                # Kiểm tra xung đột giữa các chiến lược
                if len(strategy_signals) >= 2:
                    # Kiểm tra xung đột tín hiệu
                    signal_conflicts = self._check_signal_conflicts(strategy_signals, symbol, timeframe, thresholds)
                    results['conflicts'].extend(signal_conflicts)
                    
                    # Kiểm tra chồng chéo vị thế
                    position_overlaps = self._check_position_overlaps(strategy_signals, symbol, timeframe, thresholds)
                    results['overlaps'].extend(position_overlaps)
                    
                    # Tính toán thống kê cho từng chiến lược
                    for strategy, signals in strategy_signals.items():
                        if strategy not in results['strategy_statistics']:
                            results['strategy_statistics'][strategy] = {
                                'total_signals': 0,
                                'buy_signals': 0,
                                'sell_signals': 0,
                                'hedge_signals': 0,
                                'conflict_count': 0,
                                'overlap_count': 0
                            }
                        
                        # Cập nhật thống kê
                        buy_signals = len(signals[signals['signal'] == 1])
                        sell_signals = len(signals[signals['signal'] == -1])
                        hedge_signals = len(signals[signals['signal'] == 2])
                        
                        results['strategy_statistics'][strategy]['total_signals'] += len(signals[signals['signal'] != 0])
                        results['strategy_statistics'][strategy]['buy_signals'] += buy_signals
                        results['strategy_statistics'][strategy]['sell_signals'] += sell_signals
                        results['strategy_statistics'][strategy]['hedge_signals'] += hedge_signals
                        
                        # Cập nhật số lượng xung đột
                        conflict_count = sum(1 for conflict in signal_conflicts if strategy in conflict['strategies'])
                        results['strategy_statistics'][strategy]['conflict_count'] += conflict_count
                        
                        # Cập nhật số lượng chồng chéo
                        overlap_count = sum(1 for overlap in position_overlaps if strategy in overlap['strategies'])
                        results['strategy_statistics'][strategy]['overlap_count'] += overlap_count
                
                # Cập nhật thống kê cho cặp tiền
                if symbol not in results['symbol_statistics']:
                    results['symbol_statistics'][symbol] = {
                        'total_signals': 0,
                        'buy_signals': 0,
                        'sell_signals': 0,
                        'hedge_signals': 0,
                        'conflict_count': 0,
                        'overlap_count': 0
                    }
                
                # Tính tổng tín hiệu cho cặp tiền
                for strategy, signals in strategy_signals.items():
                    buy_signals = len(signals[signals['signal'] == 1])
                    sell_signals = len(signals[signals['signal'] == -1])
                    hedge_signals = len(signals[signals['signal'] == 2])
                    
                    results['symbol_statistics'][symbol]['total_signals'] += len(signals[signals['signal'] != 0])
                    results['symbol_statistics'][symbol]['buy_signals'] += buy_signals
                    results['symbol_statistics'][symbol]['sell_signals'] += sell_signals
                    results['symbol_statistics'][symbol]['hedge_signals'] += hedge_signals
                
                # Cập nhật số lượng xung đột
                conflict_count = sum(1 for conflict in signal_conflicts if conflict['symbol'] == symbol)
                results['symbol_statistics'][symbol]['conflict_count'] += conflict_count
                
                # Cập nhật số lượng chồng chéo
                overlap_count = sum(1 for overlap in position_overlaps if overlap['symbol'] == symbol)
                results['symbol_statistics'][symbol]['overlap_count'] += overlap_count
                
                # Cập nhật thống kê cho timeframe
                if timeframe not in results['timeframe_statistics']:
                    results['timeframe_statistics'][timeframe] = {
                        'total_signals': 0,
                        'buy_signals': 0,
                        'sell_signals': 0,
                        'hedge_signals': 0,
                        'conflict_count': 0,
                        'overlap_count': 0
                    }
                
                # Tính tổng tín hiệu cho timeframe
                for strategy, signals in strategy_signals.items():
                    buy_signals = len(signals[signals['signal'] == 1])
                    sell_signals = len(signals[signals['signal'] == -1])
                    hedge_signals = len(signals[signals['signal'] == 2])
                    
                    results['timeframe_statistics'][timeframe]['total_signals'] += len(signals[signals['signal'] != 0])
                    results['timeframe_statistics'][timeframe]['buy_signals'] += buy_signals
                    results['timeframe_statistics'][timeframe]['sell_signals'] += sell_signals
                    results['timeframe_statistics'][timeframe]['hedge_signals'] += hedge_signals
                
                # Cập nhật số lượng xung đột
                conflict_count = sum(1 for conflict in signal_conflicts if conflict['timeframe'] == timeframe)
                results['timeframe_statistics'][timeframe]['conflict_count'] += conflict_count
                
                # Cập nhật số lượng chồng chéo
                overlap_count = sum(1 for overlap in position_overlaps if overlap['timeframe'] == timeframe)
                results['timeframe_statistics'][timeframe]['overlap_count'] += overlap_count
        
        # Tính tổng kết
        total_signals = sum(stats['total_signals'] for stats in results['strategy_statistics'].values())
        total_conflicts = len(results['conflicts'])
        total_overlaps = len(results['overlaps'])
        
        results['overall_summary'] = {
            'total_signals': total_signals,
            'total_conflicts': total_conflicts,
            'total_overlaps': total_overlaps,
            'conflict_percentage': (total_conflicts / total_signals * 100) if total_signals > 0 else 0,
            'overlap_percentage': (total_overlaps / total_signals * 100) if total_signals > 0 else 0,
            'strategies_analyzed': len(results['strategy_statistics']),
            'symbols_analyzed': len(results['symbol_statistics']),
            'timeframes_analyzed': len(results['timeframe_statistics'])
        }
        
        # Đưa ra khuyến nghị
        results['recommendations'] = self._generate_recommendations(results)
        
        # Lưu kết quả
        self._save_results(results)
        
        # Tạo biểu đồ
        self._create_charts(results)
        
        logger.info("Hoàn thành kiểm tra xung đột giữa các chiến lược")
        
        return results
    
    def _check_signal_conflicts(self, strategy_signals, symbol, timeframe, thresholds):
        """
        Kiểm tra xung đột tín hiệu giữa các chiến lược
        
        Args:
            strategy_signals (dict): Dictionary chứa tín hiệu của các chiến lược
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            thresholds (dict): Ngưỡng để phát hiện xung đột
            
        Returns:
            list: Danh sách xung đột
        """
        conflicts = []
        
        # Lấy tất cả chiến lược
        strategies = list(strategy_signals.keys())
        
        # Tạo khoảng thời gian để so sánh tín hiệu
        time_window = pd.Timedelta(minutes=thresholds['time_window_minutes'])
        
        # So sánh từng cặp chiến lược
        for i in range(len(strategies)):
            for j in range(i + 1, len(strategies)):
                strategy1 = strategies[i]
                strategy2 = strategies[j]
                
                signals1 = strategy_signals[strategy1]
                signals2 = strategy_signals[strategy2]
                
                # Lọc tín hiệu khác 0
                active_signals1 = signals1[signals1['signal'] != 0].copy()
                active_signals2 = signals2[signals2['signal'] != 0].copy()
                
                if len(active_signals1) < thresholds['min_signals_for_analysis'] or len(active_signals2) < thresholds['min_signals_for_analysis']:
                    logger.warning(f"Không đủ tín hiệu để phân tích xung đột giữa {strategy1} và {strategy2} cho {symbol} {timeframe}")
                    continue
                
                # Kiểm tra xung đột trong từng khoảng thời gian
                for _, row1 in active_signals1.iterrows():
                    # Lọc tín hiệu của chiến lược 2 trong cùng khoảng thời gian
                    time_diff = (active_signals2['timestamp'] - row1['timestamp']).abs()
                    nearby_signals = active_signals2[time_diff <= time_window]
                    
                    for _, row2 in nearby_signals.iterrows():
                        # Kiểm tra xung đột
                        # Xung đột khi một chiến lược đưa ra tín hiệu mua và chiến lược khác đưa ra tín hiệu bán
                        if (row1['signal'] == 1 and row2['signal'] == -1) or (row1['signal'] == -1 and row2['signal'] == 1):
                            conflicts.append({
                                'timestamp': row1['timestamp'],
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'strategies': [strategy1, strategy2],
                                'signals': [int(row1['signal']), int(row2['signal'])],
                                'conflict_type': 'Opposite Signals',
                                'time_difference_minutes': (row2['timestamp'] - row1['timestamp']).total_seconds() / 60
                            })
                        
                        # Kiểm tra xung đột giữa hedge mode và tín hiệu một chiều
                        elif (row1['signal'] == 2 and row2['signal'] != 2) or (row1['signal'] != 2 and row2['signal'] == 2):
                            conflicts.append({
                                'timestamp': row1['timestamp'],
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'strategies': [strategy1, strategy2],
                                'signals': [int(row1['signal']), int(row2['signal'])],
                                'conflict_type': 'Hedge vs Single Direction',
                                'time_difference_minutes': (row2['timestamp'] - row1['timestamp']).total_seconds() / 60
                            })
        
        logger.info(f"Tìm thấy {len(conflicts)} xung đột tín hiệu cho {symbol} {timeframe}")
        
        return conflicts
    
    def _check_position_overlaps(self, strategy_signals, symbol, timeframe, thresholds):
        """
        Kiểm tra chồng chéo vị thế giữa các chiến lược
        
        Args:
            strategy_signals (dict): Dictionary chứa tín hiệu của các chiến lược
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            thresholds (dict): Ngưỡng để phát hiện chồng chéo
            
        Returns:
            list: Danh sách chồng chéo
        """
        overlaps = []
        
        # Lấy tất cả chiến lược
        strategies = list(strategy_signals.keys())
        
        # Mô phỏng vị thế dựa trên tín hiệu
        # Giả sử mỗi tín hiệu mở một vị thế và giữ cho đến khi có tín hiệu ngược lại
        positions = {}
        
        for strategy in strategies:
            signals = strategy_signals[strategy]
            positions[strategy] = []
            
            active_position = None
            
            for _, row in signals.iterrows():
                # Xử lý tín hiệu
                if row['signal'] == 1:  # Long
                    if active_position is None:
                        # Mở vị thế mới
                        active_position = {
                            'entry_time': row['timestamp'],
                            'direction': 'LONG',
                            'status': 'OPEN'
                        }
                        positions[strategy].append(active_position)
                    elif active_position['direction'] == 'SHORT':
                        # Đóng vị thế SHORT và mở vị thế LONG mới
                        active_position['exit_time'] = row['timestamp']
                        active_position['status'] = 'CLOSED'
                        
                        active_position = {
                            'entry_time': row['timestamp'],
                            'direction': 'LONG',
                            'status': 'OPEN'
                        }
                        positions[strategy].append(active_position)
                
                elif row['signal'] == -1:  # Short
                    if active_position is None:
                        # Mở vị thế mới
                        active_position = {
                            'entry_time': row['timestamp'],
                            'direction': 'SHORT',
                            'status': 'OPEN'
                        }
                        positions[strategy].append(active_position)
                    elif active_position['direction'] == 'LONG':
                        # Đóng vị thế LONG và mở vị thế SHORT mới
                        active_position['exit_time'] = row['timestamp']
                        active_position['status'] = 'CLOSED'
                        
                        active_position = {
                            'entry_time': row['timestamp'],
                            'direction': 'SHORT',
                            'status': 'OPEN'
                        }
                        positions[strategy].append(active_position)
                
                elif row['signal'] == 2:  # Hedge Mode
                    if active_position is None:
                        # Mở vị thế HEDGE mới
                        active_position = {
                            'entry_time': row['timestamp'],
                            'direction': 'HEDGE',
                            'status': 'OPEN'
                        }
                        positions[strategy].append(active_position)
                    elif active_position['direction'] != 'HEDGE':
                        # Đóng vị thế hiện tại và mở vị thế HEDGE mới
                        active_position['exit_time'] = row['timestamp']
                        active_position['status'] = 'CLOSED'
                        
                        active_position = {
                            'entry_time': row['timestamp'],
                            'direction': 'HEDGE',
                            'status': 'OPEN'
                        }
                        positions[strategy].append(active_position)
            
            # Đóng vị thế cuối cùng nếu còn mở
            if active_position is not None and active_position['status'] == 'OPEN':
                active_position['exit_time'] = signals['timestamp'].iloc[-1]
                active_position['status'] = 'CLOSED'
        
        # Kiểm tra chồng chéo vị thế
        for i in range(len(strategies)):
            for j in range(i + 1, len(strategies)):
                strategy1 = strategies[i]
                strategy2 = strategies[j]
                
                positions1 = positions[strategy1]
                positions2 = positions[strategy2]
                
                for pos1 in positions1:
                    for pos2 in positions2:
                        # Kiểm tra chồng chéo thời gian
                        if pos1['status'] == 'CLOSED' and pos2['status'] == 'CLOSED':
                            # Tính thời gian chồng chéo
                            start_overlap = max(pos1['entry_time'], pos2['entry_time'])
                            end_overlap = min(pos1['exit_time'], pos2['exit_time'])
                            
                            if start_overlap < end_overlap:
                                # Có chồng chéo thời gian
                                # Kiểm tra hướng vị thế
                                if pos1['direction'] != pos2['direction'] and (pos1['direction'] != 'HEDGE' and pos2['direction'] != 'HEDGE'):
                                    # Vị thế ngược chiều và không phải hedge mode
                                    duration1 = (pos1['exit_time'] - pos1['entry_time']).total_seconds() / 60
                                    duration2 = (pos2['exit_time'] - pos2['entry_time']).total_seconds() / 60
                                    overlap_duration = (end_overlap - start_overlap).total_seconds() / 60
                                    
                                    # Tính phần trăm chồng chéo
                                    overlap_percentage1 = (overlap_duration / duration1) * 100 if duration1 > 0 else 0
                                    overlap_percentage2 = (overlap_duration / duration2) * 100 if duration2 > 0 else 0
                                    
                                    if overlap_percentage1 >= thresholds['position_overlap_percentage'] or overlap_percentage2 >= thresholds['position_overlap_percentage']:
                                        overlaps.append({
                                            'start_time': start_overlap,
                                            'end_time': end_overlap,
                                            'symbol': symbol,
                                            'timeframe': timeframe,
                                            'strategies': [strategy1, strategy2],
                                            'directions': [pos1['direction'], pos2['direction']],
                                            'overlap_type': 'Opposite Directions',
                                            'overlap_duration_minutes': overlap_duration,
                                            'overlap_percentage': max(overlap_percentage1, overlap_percentage2)
                                        })
        
        logger.info(f"Tìm thấy {len(overlaps)} chồng chéo vị thế cho {symbol} {timeframe}")
        
        return overlaps
    
    def _generate_recommendations(self, results):
        """
        Đưa ra khuyến nghị dựa trên kết quả phân tích
        
        Args:
            results (dict): Kết quả phân tích
            
        Returns:
            list: Danh sách khuyến nghị
        """
        recommendations = []
        
        # Khuyến nghị dựa trên tỷ lệ xung đột
        if results['overall_summary']['conflict_percentage'] > 20:
            recommendations.append({
                'type': 'critical',
                'recommendation': 'Tỷ lệ xung đột tín hiệu quá cao. Cần xem xét lại các chiến lược giao dịch.',
                'details': f"Tỷ lệ xung đột: {results['overall_summary']['conflict_percentage']:.2f}%"
            })
        elif results['overall_summary']['conflict_percentage'] > 10:
            recommendations.append({
                'type': 'warning',
                'recommendation': 'Tỷ lệ xung đột tín hiệu cao. Nên kiểm tra lại các chiến lược giao dịch.',
                'details': f"Tỷ lệ xung đột: {results['overall_summary']['conflict_percentage']:.2f}%"
            })
        
        # Khuyến nghị dựa trên tỷ lệ chồng chéo
        if results['overall_summary']['overlap_percentage'] > 20:
            recommendations.append({
                'type': 'critical',
                'recommendation': 'Tỷ lệ chồng chéo vị thế quá cao. Cần xem xét lại cách quản lý vị thế.',
                'details': f"Tỷ lệ chồng chéo: {results['overall_summary']['overlap_percentage']:.2f}%"
            })
        elif results['overall_summary']['overlap_percentage'] > 10:
            recommendations.append({
                'type': 'warning',
                'recommendation': 'Tỷ lệ chồng chéo vị thế cao. Nên kiểm tra lại cách quản lý vị thế.',
                'details': f"Tỷ lệ chồng chéo: {results['overall_summary']['overlap_percentage']:.2f}%"
            })
        
        # Khuyến nghị cho từng chiến lược
        for strategy, stats in results['strategy_statistics'].items():
            if stats['total_signals'] > 0:
                conflict_percentage = (stats['conflict_count'] / stats['total_signals']) * 100
                overlap_percentage = (stats['overlap_count'] / stats['total_signals']) * 100
                
                if conflict_percentage > 30:
                    recommendations.append({
                        'type': 'critical',
                        'recommendation': f"Chiến lược {strategy} có tỷ lệ xung đột quá cao. Cân nhắc loại bỏ.",
                        'details': f"Tỷ lệ xung đột: {conflict_percentage:.2f}%"
                    })
                elif conflict_percentage > 20:
                    recommendations.append({
                        'type': 'warning',
                        'recommendation': f"Chiến lược {strategy} có tỷ lệ xung đột cao. Nên tinh chỉnh lại.",
                        'details': f"Tỷ lệ xung đột: {conflict_percentage:.2f}%"
                    })
                
                if overlap_percentage > 30:
                    recommendations.append({
                        'type': 'critical',
                        'recommendation': f"Chiến lược {strategy} có tỷ lệ chồng chéo vị thế quá cao. Cân nhắc loại bỏ.",
                        'details': f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%"
                    })
                elif overlap_percentage > 20:
                    recommendations.append({
                        'type': 'warning',
                        'recommendation': f"Chiến lược {strategy} có tỷ lệ chồng chéo vị thế cao. Nên tinh chỉnh lại.",
                        'details': f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%"
                    })
        
        # Khuyến nghị cho từng cặp tiền
        for symbol, stats in results['symbol_statistics'].items():
            if stats['total_signals'] > 0:
                conflict_percentage = (stats['conflict_count'] / stats['total_signals']) * 100
                overlap_percentage = (stats['overlap_count'] / stats['total_signals']) * 100
                
                if conflict_percentage > 30:
                    recommendations.append({
                        'type': 'critical',
                        'recommendation': f"Cặp tiền {symbol} có tỷ lệ xung đột quá cao. Cân nhắc loại bỏ.",
                        'details': f"Tỷ lệ xung đột: {conflict_percentage:.2f}%"
                    })
                elif conflict_percentage > 20:
                    recommendations.append({
                        'type': 'warning',
                        'recommendation': f"Cặp tiền {symbol} có tỷ lệ xung đột cao. Nên tinh chỉnh lại.",
                        'details': f"Tỷ lệ xung đột: {conflict_percentage:.2f}%"
                    })
                
                if overlap_percentage > 30:
                    recommendations.append({
                        'type': 'critical',
                        'recommendation': f"Cặp tiền {symbol} có tỷ lệ chồng chéo vị thế quá cao. Cân nhắc loại bỏ.",
                        'details': f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%"
                    })
                elif overlap_percentage > 20:
                    recommendations.append({
                        'type': 'warning',
                        'recommendation': f"Cặp tiền {symbol} có tỷ lệ chồng chéo vị thế cao. Nên tinh chỉnh lại.",
                        'details': f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%"
                    })
        
        # Khuyến nghị cho từng timeframe
        for timeframe, stats in results['timeframe_statistics'].items():
            if stats['total_signals'] > 0:
                conflict_percentage = (stats['conflict_count'] / stats['total_signals']) * 100
                overlap_percentage = (stats['overlap_count'] / stats['total_signals']) * 100
                
                if conflict_percentage > 30:
                    recommendations.append({
                        'type': 'critical',
                        'recommendation': f"Timeframe {timeframe} có tỷ lệ xung đột quá cao. Cân nhắc loại bỏ.",
                        'details': f"Tỷ lệ xung đột: {conflict_percentage:.2f}%"
                    })
                elif conflict_percentage > 20:
                    recommendations.append({
                        'type': 'warning',
                        'recommendation': f"Timeframe {timeframe} có tỷ lệ xung đột cao. Nên tinh chỉnh lại.",
                        'details': f"Tỷ lệ xung đột: {conflict_percentage:.2f}%"
                    })
                
                if overlap_percentage > 30:
                    recommendations.append({
                        'type': 'critical',
                        'recommendation': f"Timeframe {timeframe} có tỷ lệ chồng chéo vị thế quá cao. Cân nhắc loại bỏ.",
                        'details': f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%"
                    })
                elif overlap_percentage > 20:
                    recommendations.append({
                        'type': 'warning',
                        'recommendation': f"Timeframe {timeframe} có tỷ lệ chồng chéo vị thế cao. Nên tinh chỉnh lại.",
                        'details': f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%"
                    })
        
        # Khuyến nghị chung
        if len(recommendations) == 0:
            recommendations.append({
                'type': 'info',
                'recommendation': 'Các chiến lược giao dịch hoạt động tốt, không có xung đột đáng kể.',
                'details': 'Tiếp tục theo dõi và tối ưu hệ thống.'
            })
        
        return recommendations
    
    def _save_results(self, results):
        """
        Lưu kết quả phân tích
        
        Args:
            results (dict): Kết quả phân tích
        """
        try:
            # Lưu kết quả dưới dạng JSON
            json_path = os.path.join(self.results_dir, 'conflict_results.json')
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Đã lưu kết quả phân tích vào {json_path}")
            
            # Tạo báo cáo văn bản
            txt_path = os.path.join(self.results_dir, 'conflict_report.txt')
            with open(txt_path, 'w') as f:
                f.write("=== BÁO CÁO PHÂN TÍCH XUNG ĐỘT CHIẾN LƯỢC ===\n\n")
                f.write(f"Thời gian phân tích: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Tổng quan
                f.write("== TỔNG QUAN ==\n")
                f.write(f"Tổng số tín hiệu: {results['overall_summary']['total_signals']}\n")
                f.write(f"Tổng số xung đột: {results['overall_summary']['total_conflicts']}\n")
                f.write(f"Tổng số chồng chéo: {results['overall_summary']['total_overlaps']}\n")
                f.write(f"Tỷ lệ xung đột: {results['overall_summary']['conflict_percentage']:.2f}%\n")
                f.write(f"Tỷ lệ chồng chéo: {results['overall_summary']['overlap_percentage']:.2f}%\n")
                f.write(f"Số chiến lược phân tích: {results['overall_summary']['strategies_analyzed']}\n")
                f.write(f"Số cặp tiền phân tích: {results['overall_summary']['symbols_analyzed']}\n")
                f.write(f"Số timeframe phân tích: {results['overall_summary']['timeframes_analyzed']}\n\n")
                
                # Thống kê chiến lược
                f.write("== THỐNG KÊ CHIẾN LƯỢC ==\n")
                for strategy, stats in results['strategy_statistics'].items():
                    f.write(f"\n= Chiến lược: {strategy} =\n")
                    f.write(f"Tổng số tín hiệu: {stats['total_signals']}\n")
                    f.write(f"Tín hiệu mua: {stats['buy_signals']}\n")
                    f.write(f"Tín hiệu bán: {stats['sell_signals']}\n")
                    f.write(f"Tín hiệu hedge: {stats['hedge_signals']}\n")
                    f.write(f"Số xung đột: {stats['conflict_count']}\n")
                    f.write(f"Số chồng chéo: {stats['overlap_count']}\n")
                    
                    if stats['total_signals'] > 0:
                        conflict_percentage = (stats['conflict_count'] / stats['total_signals']) * 100
                        overlap_percentage = (stats['overlap_count'] / stats['total_signals']) * 100
                        f.write(f"Tỷ lệ xung đột: {conflict_percentage:.2f}%\n")
                        f.write(f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%\n")
                
                # Thống kê cặp tiền
                f.write("\n\n== THỐNG KÊ CẶP TIỀN ==\n")
                for symbol, stats in results['symbol_statistics'].items():
                    f.write(f"\n= Cặp tiền: {symbol} =\n")
                    f.write(f"Tổng số tín hiệu: {stats['total_signals']}\n")
                    f.write(f"Tín hiệu mua: {stats['buy_signals']}\n")
                    f.write(f"Tín hiệu bán: {stats['sell_signals']}\n")
                    f.write(f"Tín hiệu hedge: {stats['hedge_signals']}\n")
                    f.write(f"Số xung đột: {stats['conflict_count']}\n")
                    f.write(f"Số chồng chéo: {stats['overlap_count']}\n")
                    
                    if stats['total_signals'] > 0:
                        conflict_percentage = (stats['conflict_count'] / stats['total_signals']) * 100
                        overlap_percentage = (stats['overlap_count'] / stats['total_signals']) * 100
                        f.write(f"Tỷ lệ xung đột: {conflict_percentage:.2f}%\n")
                        f.write(f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%\n")
                
                # Thống kê timeframe
                f.write("\n\n== THỐNG KÊ TIMEFRAME ==\n")
                for timeframe, stats in results['timeframe_statistics'].items():
                    f.write(f"\n= Timeframe: {timeframe} =\n")
                    f.write(f"Tổng số tín hiệu: {stats['total_signals']}\n")
                    f.write(f"Tín hiệu mua: {stats['buy_signals']}\n")
                    f.write(f"Tín hiệu bán: {stats['sell_signals']}\n")
                    f.write(f"Tín hiệu hedge: {stats['hedge_signals']}\n")
                    f.write(f"Số xung đột: {stats['conflict_count']}\n")
                    f.write(f"Số chồng chéo: {stats['overlap_count']}\n")
                    
                    if stats['total_signals'] > 0:
                        conflict_percentage = (stats['conflict_count'] / stats['total_signals']) * 100
                        overlap_percentage = (stats['overlap_count'] / stats['total_signals']) * 100
                        f.write(f"Tỷ lệ xung đột: {conflict_percentage:.2f}%\n")
                        f.write(f"Tỷ lệ chồng chéo: {overlap_percentage:.2f}%\n")
                
                # Top xung đột
                if results['conflicts']:
                    f.write("\n\n== TOP XUNG ĐỘT ==\n")
                    for i, conflict in enumerate(sorted(results['conflicts'], key=lambda x: x['timestamp'], reverse=True)[:10]):
                        f.write(f"\n{i+1}. Thời gian: {conflict['timestamp']}\n")
                        f.write(f"   Cặp tiền: {conflict['symbol']}\n")
                        f.write(f"   Timeframe: {conflict['timeframe']}\n")
                        f.write(f"   Chiến lược: {' vs '.join(conflict['strategies'])}\n")
                        f.write(f"   Tín hiệu: {conflict['signals']}\n")
                        f.write(f"   Loại xung đột: {conflict['conflict_type']}\n")
                        f.write(f"   Khoảng cách thời gian: {conflict['time_difference_minutes']:.2f} phút\n")
                
                # Top chồng chéo
                if results['overlaps']:
                    f.write("\n\n== TOP CHỒNG CHÉO ==\n")
                    for i, overlap in enumerate(sorted(results['overlaps'], key=lambda x: x['overlap_percentage'], reverse=True)[:10]):
                        f.write(f"\n{i+1}. Thời gian bắt đầu: {overlap['start_time']}\n")
                        f.write(f"   Thời gian kết thúc: {overlap['end_time']}\n")
                        f.write(f"   Cặp tiền: {overlap['symbol']}\n")
                        f.write(f"   Timeframe: {overlap['timeframe']}\n")
                        f.write(f"   Chiến lược: {' vs '.join(overlap['strategies'])}\n")
                        f.write(f"   Hướng: {' vs '.join(overlap['directions'])}\n")
                        f.write(f"   Loại chồng chéo: {overlap['overlap_type']}\n")
                        f.write(f"   Thời gian chồng chéo: {overlap['overlap_duration_minutes']:.2f} phút\n")
                        f.write(f"   Phần trăm chồng chéo: {overlap['overlap_percentage']:.2f}%\n")
                
                # Khuyến nghị
                f.write("\n\n== KHUYẾN NGHỊ ==\n")
                for i, recommendation in enumerate(results['recommendations']):
                    f.write(f"\n{i+1}. [{recommendation['type'].upper()}] {recommendation['recommendation']}\n")
                    f.write(f"   Chi tiết: {recommendation['details']}\n")
            
            logger.info(f"Đã tạo báo cáo văn bản: {txt_path}")
            
            # Tạo báo cáo HTML
            html_path = os.path.join(self.results_dir, 'conflict_report.html')
            with open(html_path, 'w') as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Báo cáo xung đột chiến lược</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 0; padding: 0; color: #333; }
                        .container { width: 90%; margin: 0 auto; padding: 20px; }
                        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
                        h2 { color: #2980b9; margin-top: 30px; }
                        h3 { color: #16a085; }
                        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                        tr:nth-child(even) { background-color: #f9f9f9; }
                        .critical { color: #e74c3c; font-weight: bold; }
                        .warning { color: #f39c12; font-weight: bold; }
                        .info { color: #3498db; }
                        .success { color: #2ecc71; }
                        .chart-container { margin: 20px 0; border: 1px solid #ddd; padding: 10px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Báo cáo phân tích xung đột chiến lược</h1>
                        <p>Thời gian phân tích: """)
                
                f.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                # Tổng quan
                f.write("""
                        </p>
                        
                        <h2>Tổng quan</h2>
                        <table>
                            <tr>
                                <th>Thông số</th>
                                <th>Giá trị</th>
                            </tr>
                """)
                
                for key, value in results['overall_summary'].items():
                    display_key = key.replace('_', ' ').title()
                    
                    if 'percentage' in key:
                        display_value = f"{value:.2f}%"
                    else:
                        display_value = value
                    
                    f.write(f"""
                            <tr>
                                <td>{display_key}</td>
                                <td>{display_value}</td>
                            </tr>
                    """)
                
                f.write("""
                        </table>
                        
                        <h2>Thống kê chiến lược</h2>
                        <table>
                            <tr>
                                <th>Chiến lược</th>
                                <th>Tổng tín hiệu</th>
                                <th>Tín hiệu mua</th>
                                <th>Tín hiệu bán</th>
                                <th>Tín hiệu hedge</th>
                                <th>Số xung đột</th>
                                <th>Số chồng chéo</th>
                                <th>Tỷ lệ xung đột</th>
                                <th>Tỷ lệ chồng chéo</th>
                            </tr>
                """)
                
                for strategy, stats in results['strategy_statistics'].items():
                    conflict_percentage = (stats['conflict_count'] / stats['total_signals'] * 100) if stats['total_signals'] > 0 else 0
                    overlap_percentage = (stats['overlap_count'] / stats['total_signals'] * 100) if stats['total_signals'] > 0 else 0
                    
                    # Phân loại màu dựa trên tỷ lệ
                    conflict_class = 'critical' if conflict_percentage > 30 else 'warning' if conflict_percentage > 20 else 'info' if conflict_percentage > 10 else 'success'
                    overlap_class = 'critical' if overlap_percentage > 30 else 'warning' if overlap_percentage > 20 else 'info' if overlap_percentage > 10 else 'success'
                    
                    f.write(f"""
                            <tr>
                                <td>{strategy}</td>
                                <td>{stats['total_signals']}</td>
                                <td>{stats['buy_signals']}</td>
                                <td>{stats['sell_signals']}</td>
                                <td>{stats['hedge_signals']}</td>
                                <td>{stats['conflict_count']}</td>
                                <td>{stats['overlap_count']}</td>
                                <td class="{conflict_class}">{conflict_percentage:.2f}%</td>
                                <td class="{overlap_class}">{overlap_percentage:.2f}%</td>
                            </tr>
                    """)
                
                f.write("""
                        </table>
                        
                        <h2>Thống kê cặp tiền</h2>
                        <table>
                            <tr>
                                <th>Cặp tiền</th>
                                <th>Tổng tín hiệu</th>
                                <th>Tín hiệu mua</th>
                                <th>Tín hiệu bán</th>
                                <th>Tín hiệu hedge</th>
                                <th>Số xung đột</th>
                                <th>Số chồng chéo</th>
                                <th>Tỷ lệ xung đột</th>
                                <th>Tỷ lệ chồng chéo</th>
                            </tr>
                """)
                
                for symbol, stats in results['symbol_statistics'].items():
                    conflict_percentage = (stats['conflict_count'] / stats['total_signals'] * 100) if stats['total_signals'] > 0 else 0
                    overlap_percentage = (stats['overlap_count'] / stats['total_signals'] * 100) if stats['total_signals'] > 0 else 0
                    
                    # Phân loại màu dựa trên tỷ lệ
                    conflict_class = 'critical' if conflict_percentage > 30 else 'warning' if conflict_percentage > 20 else 'info' if conflict_percentage > 10 else 'success'
                    overlap_class = 'critical' if overlap_percentage > 30 else 'warning' if overlap_percentage > 20 else 'info' if overlap_percentage > 10 else 'success'
                    
                    f.write(f"""
                            <tr>
                                <td>{symbol}</td>
                                <td>{stats['total_signals']}</td>
                                <td>{stats['buy_signals']}</td>
                                <td>{stats['sell_signals']}</td>
                                <td>{stats['hedge_signals']}</td>
                                <td>{stats['conflict_count']}</td>
                                <td>{stats['overlap_count']}</td>
                                <td class="{conflict_class}">{conflict_percentage:.2f}%</td>
                                <td class="{overlap_class}">{overlap_percentage:.2f}%</td>
                            </tr>
                    """)
                
                f.write("""
                        </table>
                        
                        <h2>Thống kê timeframe</h2>
                        <table>
                            <tr>
                                <th>Timeframe</th>
                                <th>Tổng tín hiệu</th>
                                <th>Tín hiệu mua</th>
                                <th>Tín hiệu bán</th>
                                <th>Tín hiệu hedge</th>
                                <th>Số xung đột</th>
                                <th>Số chồng chéo</th>
                                <th>Tỷ lệ xung đột</th>
                                <th>Tỷ lệ chồng chéo</th>
                            </tr>
                """)
                
                for timeframe, stats in results['timeframe_statistics'].items():
                    conflict_percentage = (stats['conflict_count'] / stats['total_signals'] * 100) if stats['total_signals'] > 0 else 0
                    overlap_percentage = (stats['overlap_count'] / stats['total_signals'] * 100) if stats['total_signals'] > 0 else 0
                    
                    # Phân loại màu dựa trên tỷ lệ
                    conflict_class = 'critical' if conflict_percentage > 30 else 'warning' if conflict_percentage > 20 else 'info' if conflict_percentage > 10 else 'success'
                    overlap_class = 'critical' if overlap_percentage > 30 else 'warning' if overlap_percentage > 20 else 'info' if overlap_percentage > 10 else 'success'
                    
                    f.write(f"""
                            <tr>
                                <td>{timeframe}</td>
                                <td>{stats['total_signals']}</td>
                                <td>{stats['buy_signals']}</td>
                                <td>{stats['sell_signals']}</td>
                                <td>{stats['hedge_signals']}</td>
                                <td>{stats['conflict_count']}</td>
                                <td>{stats['overlap_count']}</td>
                                <td class="{conflict_class}">{conflict_percentage:.2f}%</td>
                                <td class="{overlap_class}">{overlap_percentage:.2f}%</td>
                            </tr>
                    """)
                
                # Top xung đột
                if results['conflicts']:
                    f.write("""
                            </table>
                            
                            <h2>Top xung đột</h2>
                            <table>
                                <tr>
                                    <th>#</th>
                                    <th>Thời gian</th>
                                    <th>Cặp tiền</th>
                                    <th>Timeframe</th>
                                    <th>Chiến lược</th>
                                    <th>Tín hiệu</th>
                                    <th>Loại xung đột</th>
                                    <th>Khoảng cách thời gian</th>
                                </tr>
                    """)
                    
                    for i, conflict in enumerate(sorted(results['conflicts'], key=lambda x: x['timestamp'], reverse=True)[:10]):
                        f.write(f"""
                                <tr>
                                    <td>{i+1}</td>
                                    <td>{conflict['timestamp']}</td>
                                    <td>{conflict['symbol']}</td>
                                    <td>{conflict['timeframe']}</td>
                                    <td>{' vs '.join(conflict['strategies'])}</td>
                                    <td>{conflict['signals']}</td>
                                    <td>{conflict['conflict_type']}</td>
                                    <td>{conflict['time_difference_minutes']:.2f} phút</td>
                                </tr>
                        """)
                    
                    f.write("</table>")
                
                # Top chồng chéo
                if results['overlaps']:
                    f.write("""
                            <h2>Top chồng chéo</h2>
                            <table>
                                <tr>
                                    <th>#</th>
                                    <th>Thời gian bắt đầu</th>
                                    <th>Thời gian kết thúc</th>
                                    <th>Cặp tiền</th>
                                    <th>Timeframe</th>
                                    <th>Chiến lược</th>
                                    <th>Hướng</th>
                                    <th>Loại chồng chéo</th>
                                    <th>Thời gian chồng chéo</th>
                                    <th>Phần trăm chồng chéo</th>
                                </tr>
                    """)
                    
                    for i, overlap in enumerate(sorted(results['overlaps'], key=lambda x: x['overlap_percentage'], reverse=True)[:10]):
                        f.write(f"""
                                <tr>
                                    <td>{i+1}</td>
                                    <td>{overlap['start_time']}</td>
                                    <td>{overlap['end_time']}</td>
                                    <td>{overlap['symbol']}</td>
                                    <td>{overlap['timeframe']}</td>
                                    <td>{' vs '.join(overlap['strategies'])}</td>
                                    <td>{' vs '.join(overlap['directions'])}</td>
                                    <td>{overlap['overlap_type']}</td>
                                    <td>{overlap['overlap_duration_minutes']:.2f} phút</td>
                                    <td>{overlap['overlap_percentage']:.2f}%</td>
                                </tr>
                        """)
                    
                    f.write("</table>")
                
                # Khuyến nghị
                f.write("""
                        <h2>Khuyến nghị</h2>
                        <table>
                            <tr>
                                <th>#</th>
                                <th>Loại</th>
                                <th>Khuyến nghị</th>
                                <th>Chi tiết</th>
                            </tr>
                """)
                
                for i, recommendation in enumerate(results['recommendations']):
                    recommendation_class = 'critical' if recommendation['type'] == 'critical' else 'warning' if recommendation['type'] == 'warning' else 'info'
                    
                    f.write(f"""
                            <tr>
                                <td>{i+1}</td>
                                <td class="{recommendation_class}">{recommendation['type'].upper()}</td>
                                <td>{recommendation['recommendation']}</td>
                                <td>{recommendation['details']}</td>
                            </tr>
                    """)
                
                f.write("""
                        </table>
                        
                        <h2>Biểu đồ</h2>
                        <div class="chart-container">
                            <p>Các biểu đồ được lưu trong thư mục 'charts' của báo cáo.</p>
                        </div>
                        
                        <p>Báo cáo này được tạo tự động bởi công cụ phân tích xung đột chiến lược.</p>
                    </div>
                </body>
                </html>
                """)
            
            logger.info(f"Đã tạo báo cáo HTML: {html_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả phân tích: {e}")
    
    def _create_charts(self, results):
        """
        Tạo các biểu đồ phân tích
        
        Args:
            results (dict): Kết quả phân tích
        """
        try:
            # Tạo thư mục charts
            charts_dir = os.path.join(self.results_dir, 'charts')
            os.makedirs(charts_dir, exist_ok=True)
            
            # Biểu đồ tỷ lệ xung đột và chồng chéo theo chiến lược
            plt.figure(figsize=(12, 8))
            
            strategies = list(results['strategy_statistics'].keys())
            conflict_percentages = []
            overlap_percentages = []
            
            for strategy in strategies:
                stats = results['strategy_statistics'][strategy]
                if stats['total_signals'] > 0:
                    conflict_percentages.append((stats['conflict_count'] / stats['total_signals']) * 100)
                    overlap_percentages.append((stats['overlap_count'] / stats['total_signals']) * 100)
                else:
                    conflict_percentages.append(0)
                    overlap_percentages.append(0)
            
            x = range(len(strategies))
            
            plt.bar([i - 0.2 for i in x], conflict_percentages, width=0.4, color='#e74c3c', label='Tỷ lệ xung đột')
            plt.bar([i + 0.2 for i in x], overlap_percentages, width=0.4, color='#3498db', label='Tỷ lệ chồng chéo')
            
            plt.ylabel('Phần trăm (%)')
            plt.title('Tỷ lệ xung đột và chồng chéo theo chiến lược')
            plt.xticks(x, strategies, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, 'strategy_conflict_chart.png'))
            plt.close()
            
            # Biểu đồ phân bố tín hiệu theo chiến lược
            plt.figure(figsize=(12, 8))
            
            buy_signals = []
            sell_signals = []
            hedge_signals = []
            
            for strategy in strategies:
                stats = results['strategy_statistics'][strategy]
                buy_signals.append(stats['buy_signals'])
                sell_signals.append(stats['sell_signals'])
                hedge_signals.append(stats['hedge_signals'])
            
            x = range(len(strategies))
            
            plt.bar(x, buy_signals, width=0.3, color='#2ecc71', label='Tín hiệu mua')
            plt.bar(x, sell_signals, bottom=buy_signals, width=0.3, color='#e74c3c', label='Tín hiệu bán')
            plt.bar(x, hedge_signals, bottom=[buy + sell for buy, sell in zip(buy_signals, sell_signals)], width=0.3, color='#f39c12', label='Tín hiệu hedge')
            
            plt.ylabel('Số lượng tín hiệu')
            plt.title('Phân bố tín hiệu theo chiến lược')
            plt.xticks(x, strategies, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, 'signal_distribution_chart.png'))
            plt.close()
            
            # Biểu đồ xung đột theo cặp tiền
            plt.figure(figsize=(12, 8))
            
            symbols = list(results['symbol_statistics'].keys())
            conflict_counts = []
            overlap_counts = []
            
            for symbol in symbols:
                stats = results['symbol_statistics'][symbol]
                conflict_counts.append(stats['conflict_count'])
                overlap_counts.append(stats['overlap_count'])
            
            x = range(len(symbols))
            
            plt.bar([i - 0.2 for i in x], conflict_counts, width=0.4, color='#e74c3c', label='Số xung đột')
            plt.bar([i + 0.2 for i in x], overlap_counts, width=0.4, color='#3498db', label='Số chồng chéo')
            
            plt.ylabel('Số lượng')
            plt.title('Xung đột và chồng chéo theo cặp tiền')
            plt.xticks(x, symbols, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, 'symbol_conflict_chart.png'))
            plt.close()
            
            # Biểu đồ xung đột theo timeframe
            plt.figure(figsize=(12, 8))
            
            timeframes = list(results['timeframe_statistics'].keys())
            conflict_counts = []
            overlap_counts = []
            
            for timeframe in timeframes:
                stats = results['timeframe_statistics'][timeframe]
                conflict_counts.append(stats['conflict_count'])
                overlap_counts.append(stats['overlap_count'])
            
            x = range(len(timeframes))
            
            plt.bar([i - 0.2 for i in x], conflict_counts, width=0.4, color='#e74c3c', label='Số xung đột')
            plt.bar([i + 0.2 for i in x], overlap_counts, width=0.4, color='#3498db', label='Số chồng chéo')
            
            plt.ylabel('Số lượng')
            plt.title('Xung đột và chồng chéo theo timeframe')
            plt.xticks(x, timeframes, rotation=45, ha='right')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, 'timeframe_conflict_chart.png'))
            plt.close()
            
            # Biểu đồ ma trận xung đột
            plt.figure(figsize=(12, 10))
            
            # Tạo ma trận xung đột
            conflict_matrix = np.zeros((len(strategies), len(strategies)))
            
            for conflict in results['conflicts']:
                if len(conflict['strategies']) == 2:
                    idx1 = strategies.index(conflict['strategies'][0])
                    idx2 = strategies.index(conflict['strategies'][1])
                    conflict_matrix[idx1, idx2] += 1
                    conflict_matrix[idx2, idx1] += 1
            
            plt.imshow(conflict_matrix, cmap='YlOrRd', interpolation='nearest')
            plt.colorbar(label='Số lượng xung đột')
            
            plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
            plt.yticks(range(len(strategies)), strategies)
            
            plt.title('Ma trận xung đột giữa các chiến lược')
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, 'conflict_matrix_chart.png'))
            plt.close()
            
            logger.info(f"Đã tạo các biểu đồ phân tích trong thư mục {charts_dir}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích: {e}")


def main():
    """
    Hàm chính
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Strategy Conflict Checker')
    parser.add_argument('--config', type=str, default='strategy_conflict_config.json',
                      help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Khởi tạo Conflict Checker
    checker = StrategyConflictChecker(config_path=args.config)
    
    # Chạy kiểm tra xung đột
    results = checker.check_conflicts()
    
    # Hiển thị kết quả tổng thể
    total_conflicts = len(results['conflicts'])
    total_overlaps = len(results['overlaps'])
    total_signals = results['overall_summary']['total_signals']
    
    print("\n===== STRATEGY CONFLICT ANALYSIS SUMMARY =====")
    print(f"Total Signals: {total_signals}")
    print(f"Total Conflicts: {total_conflicts}")
    print(f"Total Overlaps: {total_overlaps}")
    
    if total_signals > 0:
        conflict_percentage = (total_conflicts / total_signals) * 100
        overlap_percentage = (total_overlaps / total_signals) * 100
        
        print(f"Conflict Percentage: {conflict_percentage:.2f}%")
        print(f"Overlap Percentage: {overlap_percentage:.2f}%")
    
    print("\nRecommendations:")
    for i, recommendation in enumerate(results['recommendations']):
        print(f"{i+1}. [{recommendation['type'].upper()}] {recommendation['recommendation']}")
        print(f"   Details: {recommendation['details']}")
    
    print(f"\nDetailed reports have been saved to {checker.results_dir}")
    print("=============================================")

if __name__ == "__main__":
    main()