#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal Consistency Analyzer - Công cụ phân tích tính nhất quán của tín hiệu giao dịch 
từ các thuật toán khác nhau để đảm bảo không có xung đột khi vào lệnh
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
import matplotlib.dates as mdates
from collections import defaultdict, Counter

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('signal_analyzer.log')
    ]
)

logger = logging.getLogger('signal_analyzer')

class SignalConsistencyAnalyzer:
    """
    Phân tích tính nhất quán của tín hiệu giao dịch từ các thuật toán khác nhau
    """
    
    def __init__(self, config_path='signal_analyzer_config.json'):
        """
        Khởi tạo SignalConsistencyAnalyzer
        
        Args:
            config_path (str): Đường dẫn file cấu hình
        """
        self.config_path = config_path
        self.load_config()
        
        # Tạo thư mục kết quả
        self.results_dir = 'signal_analysis'
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Biến lưu trữ dữ liệu
        self.signals_data = {}
        self.strategy_correlation = {}
        self.strategy_performance = {}
        self.consistency_metrics = {}
        
        logger.info("Đã khởi tạo Signal Consistency Analyzer")
    
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
                    "signals_dir": "signals",
                    "strategies": [
                        "ema_crossover",
                        "macd_divergence", 
                        "rsi_extreme",
                        "supertrend",
                        "bollinger_bands_squeeze",
                        "adaptive_mode"
                    ],
                    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                    "timeframes": ["1h", "4h", "1d"],
                    "analysis_period_days": 30,
                    "consistency_thresholds": {
                        "min_agreement_percentage": 70,
                        "max_contradiction_percentage": 20,
                        "min_strategy_correlation": 0.5,
                        "max_false_signal_ratio": 0.3
                    },
                    "signal_validation": {
                        "validate_with_price_action": True,
                        "price_data_dir": "data",
                        "min_price_move_percent": 1.0,
                        "validation_window_hours": 24
                    },
                    "output_formats": ["html", "json", "csv", "charts"]
                }
                
                # Lưu cấu hình
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)
                
                logger.info(f"Đã tạo cấu hình mặc định và lưu vào {self.config_path}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            raise
    
    def load_signals(self):
        """
        Tải dữ liệu tín hiệu từ tất cả chiến lược
        
        Returns:
            bool: True nếu tải thành công, False nếu có lỗi
        """
        try:
            signals_dir = self.config["signals_dir"]
            
            if not os.path.exists(signals_dir):
                os.makedirs(signals_dir, exist_ok=True)
                logger.warning(f"Thư mục tín hiệu {signals_dir} không tồn tại, đã tạo mới")
            
            # Tải tín hiệu cho từng symbol và timeframe
            for symbol in self.config["symbols"]:
                if symbol not in self.signals_data:
                    self.signals_data[symbol] = {}
                
                for timeframe in self.config["timeframes"]:
                    if timeframe not in self.signals_data[symbol]:
                        self.signals_data[symbol][timeframe] = {}
                    
                    logger.info(f"Đang tải tín hiệu cho {symbol} {timeframe}...")
                    
                    # Tải tín hiệu từ mỗi chiến lược
                    for strategy in self.config["strategies"]:
                        signal_file = os.path.join(signals_dir, f"{strategy}_{symbol}_{timeframe}_signals.csv")
                        
                        if os.path.exists(signal_file):
                            try:
                                df = pd.read_csv(signal_file)
                                
                                # Đảm bảo cột timestamp là datetime
                                if 'timestamp' in df.columns:
                                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                                else:
                                    logger.warning(f"File {signal_file} không có cột timestamp")
                                    continue
                                
                                # Chỉ giữ lại dữ liệu trong khoảng thời gian phân tích
                                analysis_period = self.config["analysis_period_days"]
                                end_date = datetime.datetime.now()
                                start_date = end_date - datetime.timedelta(days=analysis_period)
                                
                                df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                                
                                if len(df) > 0:
                                    self.signals_data[symbol][timeframe][strategy] = df
                                    logger.info(f"Đã tải {len(df)} tín hiệu từ {signal_file}")
                                else:
                                    logger.warning(f"Không có tín hiệu trong khoảng thời gian phân tích từ {signal_file}")
                            
                            except Exception as e:
                                logger.error(f"Lỗi khi đọc file {signal_file}: {e}")
                        else:
                            logger.warning(f"Không tìm thấy file tín hiệu {signal_file}")
            
            # Kiểm tra xem có tín hiệu nào không
            signals_loaded = False
            for symbol in self.signals_data:
                for timeframe in self.signals_data[symbol]:
                    if len(self.signals_data[symbol][timeframe]) > 0:
                        signals_loaded = True
                        break
                
                if signals_loaded:
                    break
            
            if not signals_loaded:
                logger.warning("Không tìm thấy dữ liệu tín hiệu nào. Sẽ tạo dữ liệu mẫu để kiểm tra")
                self._generate_sample_data()
            
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu tín hiệu: {e}")
            return False
    
    def _generate_sample_data(self):
        """
        Tạo dữ liệu mẫu để kiểm tra
        """
        signals_dir = self.config["signals_dir"]
        os.makedirs(signals_dir, exist_ok=True)
        
        for symbol in self.config["symbols"]:
            if symbol not in self.signals_data:
                self.signals_data[symbol] = {}
            
            for timeframe in self.config["timeframes"]:
                if timeframe not in self.signals_data[symbol]:
                    self.signals_data[symbol][timeframe] = {}
                
                # Tạo dãy thời gian
                end_date = datetime.datetime.now()
                start_date = end_date - datetime.timedelta(days=self.config["analysis_period_days"])
                
                if timeframe == '1h':
                    freq = 'H'
                elif timeframe == '4h':
                    freq = '4H'
                elif timeframe == '1d':
                    freq = 'D'
                else:
                    freq = 'D'
                
                timestamps = pd.date_range(start=start_date, end=end_date, freq=freq)
                
                # Tạo tín hiệu cho mỗi chiến lược
                for strategy in self.config["strategies"]:
                    # Tạo DataFrame mới
                    df = pd.DataFrame({'timestamp': timestamps})
                    
                    # Tạo tín hiệu giả
                    # 1 = mua, -1 = bán, 0 = không có tín hiệu, 2 = hedge
                    if strategy == 'ema_crossover':
                        # EMA crossover tạo tín hiệu theo xu hướng
                        signals = np.zeros(len(df))
                        
                        # Tạo xu hướng cơ bản
                        trend = np.cumsum(np.random.normal(0, 1, len(df)))
                        
                        # Tạo tín hiệu dựa trên xu hướng
                        for i in range(1, len(trend)):
                            if trend[i] > trend[i-1] + 0.5 and np.random.random() < 0.3:
                                signals[i] = 1  # Tín hiệu mua
                            elif trend[i] < trend[i-1] - 0.5 and np.random.random() < 0.3:
                                signals[i] = -1  # Tín hiệu bán
                        
                        df['signal'] = signals
                    
                    elif strategy == 'macd_divergence':
                        # MACD tạo tín hiệu theo dao động
                        signals = np.zeros(len(df))
                        
                        # Mô phỏng MACD
                        oscillator = np.sin(np.linspace(0, 4 * np.pi, len(df)))
                        oscillator += np.random.normal(0, 0.3, len(df))  # Thêm nhiễu
                        
                        # Tạo tín hiệu dựa trên dao động
                        for i in range(1, len(oscillator)):
                            if oscillator[i] > 0 and oscillator[i-1] <= 0 and np.random.random() < 0.5:
                                signals[i] = 1  # Tín hiệu mua khi cắt lên
                            elif oscillator[i] < 0 and oscillator[i-1] >= 0 and np.random.random() < 0.5:
                                signals[i] = -1  # Tín hiệu bán khi cắt xuống
                        
                        df['signal'] = signals
                    
                    elif strategy == 'rsi_extreme':
                        # RSI tạo tín hiệu khi quá mua/quá bán
                        signals = np.zeros(len(df))
                        
                        # Mô phỏng RSI
                        rsi = 50 + 25 * np.sin(np.linspace(0, 6 * np.pi, len(df)))
                        rsi += np.random.normal(0, 5, len(df))  # Thêm nhiễu
                        
                        # Giới hạn RSI trong khoảng [0, 100]
                        rsi = np.clip(rsi, 0, 100)
                        
                        # Tạo tín hiệu dựa trên RSI
                        for i in range(len(rsi)):
                            if rsi[i] < 30 and np.random.random() < 0.5:
                                signals[i] = 1  # Tín hiệu mua khi RSI < 30
                            elif rsi[i] > 70 and np.random.random() < 0.5:
                                signals[i] = -1  # Tín hiệu bán khi RSI > 70
                        
                        df['signal'] = signals
                    
                    elif strategy == 'supertrend':
                        # Supertrend tạo tín hiệu ít hơn nhưng rõ ràng hơn
                        signals = np.zeros(len(df))
                        
                        # Mô phỏng xu hướng
                        trend = np.cumsum(np.random.normal(0, 1, len(df)))
                        
                        # Tạo tín hiệu dựa trên xu hướng
                        current_trend = 0  # 0 = không có xu hướng, 1 = uptrend, -1 = downtrend
                        
                        for i in range(10, len(trend)):
                            # Xác định xu hướng dựa trên trung bình 10 giá trị gần nhất
                            avg_10 = np.mean(trend[i-10:i])
                            
                            # Đổi xu hướng khi có sự thay đổi lớn
                            if avg_10 > trend[i-10] + 1 and current_trend != 1:
                                current_trend = 1
                                signals[i] = 1  # Tín hiệu mua khi chuyển thành uptrend
                            elif avg_10 < trend[i-10] - 1 and current_trend != -1:
                                current_trend = -1
                                signals[i] = -1  # Tín hiệu bán khi chuyển thành downtrend
                        
                        df['signal'] = signals
                    
                    elif strategy == 'bollinger_bands_squeeze':
                        # Bollinger Bands tạo tín hiệu khi băng thu hẹp rồi mở rộng
                        signals = np.zeros(len(df))
                        
                        # Mô phỏng biến động
                        volatility = np.abs(np.random.normal(0, 1, len(df)))
                        volatility = pd.Series(volatility).rolling(20).std().fillna(0).values
                        
                        # Tạo tín hiệu dựa trên biến động
                        is_squeeze = False
                        
                        for i in range(5, len(volatility)):
                            # Phát hiện squeeze (biến động giảm)
                            if not is_squeeze and volatility[i] < np.mean(volatility[i-5:i]) * 0.7:
                                is_squeeze = True
                            
                            # Phát hiện hết squeeze (biến động tăng)
                            elif is_squeeze and volatility[i] > np.mean(volatility[i-5:i]) * 1.5:
                                is_squeeze = False
                                # Random tín hiệu mua hoặc bán khi hết squeeze
                                signals[i] = 1 if np.random.random() > 0.5 else -1
                        
                        df['signal'] = signals
                    
                    elif strategy == 'adaptive_mode':
                        # Adaptive mode kết hợp các tín hiệu từ nhiều chiến lược
                        signals = np.zeros(len(df))
                        
                        # Mô phỏng xu hướng và biến động
                        trend = np.cumsum(np.random.normal(0, 1, len(df)))
                        volatility = np.abs(np.random.normal(0, 1, len(df)))
                        volatility = pd.Series(volatility).rolling(10).std().fillna(0).values
                        
                        # Tạo tín hiệu dựa trên xu hướng và biến động
                        for i in range(10, len(trend)):
                            # Trong thị trường biến động cao
                            if volatility[i] > np.mean(volatility[i-10:i]) * 1.5:
                                # Sử dụng cả long và short (hedge mode) khi biến động cao
                                if np.random.random() < 0.2:  # 20% cơ hội
                                    signals[i] = 2  # Hedge mode
                            
                            # Trong thị trường có xu hướng rõ ràng
                            elif abs(trend[i] - trend[i-10]) > 2:
                                if trend[i] > trend[i-10] and np.random.random() < 0.3:
                                    signals[i] = 1  # Tín hiệu mua khi xu hướng tăng
                                elif trend[i] < trend[i-10] and np.random.random() < 0.3:
                                    signals[i] = -1  # Tín hiệu bán khi xu hướng giảm
                        
                        df['signal'] = signals
                    
                    else:
                        # Chiến lược mặc định tạo tín hiệu ngẫu nhiên
                        signals = np.zeros(len(df))
                        
                        # Tạo tín hiệu ngẫu nhiên với xác suất 10%
                        for i in range(len(signals)):
                            if np.random.random() < 0.1:
                                signals[i] = 1 if np.random.random() > 0.5 else -1
                        
                        df['signal'] = signals
                    
                    # Thêm thông tin chiến lược, symbol và timeframe
                    df['strategy'] = strategy
                    df['symbol'] = symbol
                    df['timeframe'] = timeframe
                    
                    # Lưu DataFrame vào từ điển
                    self.signals_data[symbol][timeframe][strategy] = df
                    
                    # Lưu tín hiệu ra file
                    signal_file = os.path.join(signals_dir, f"{strategy}_{symbol}_{timeframe}_signals.csv")
                    df.to_csv(signal_file, index=False)
                    
                    logger.info(f"Đã tạo {len(df)} tín hiệu mẫu cho {strategy}_{symbol}_{timeframe}")
        
        logger.info("Đã tạo dữ liệu mẫu cho tất cả chiến lược, symbol và timeframe")
    
    def analyze_consistency(self):
        """
        Phân tích tính nhất quán giữa các chiến lược
        
        Returns:
            dict: Kết quả phân tích tính nhất quán
        """
        logger.info("Bắt đầu phân tích tính nhất quán giữa các chiến lược...")
        
        # Đảm bảo đã tải dữ liệu tín hiệu
        if not self.signals_data:
            if not self.load_signals():
                logger.error("Không thể tải dữ liệu tín hiệu, không thể phân tích")
                return {}
        
        # Kết quả phân tích
        analysis_results = {
            "overall_consistency": {},
            "symbol_consistency": {},
            "timeframe_consistency": {},
            "strategy_consistency": {},
            "correlation_matrix": {},
            "false_signals": {},
            "conflicting_periods": [],
            "recommendations": []
        }
        
        # Phân tích cho từng symbol và timeframe
        for symbol in self.signals_data:
            analysis_results["symbol_consistency"][symbol] = {}
            
            for timeframe in self.signals_data[symbol]:
                logger.info(f"Phân tích tính nhất quán cho {symbol} {timeframe}...")
                
                # Lấy tất cả chiến lược trong symbol và timeframe này
                strategies = list(self.signals_data[symbol][timeframe].keys())
                
                if len(strategies) < 2:
                    logger.warning(f"Không đủ chiến lược để phân tích cho {symbol} {timeframe}")
                    continue
                
                # Phân tích tín hiệu
                timeframe_results = self._analyze_timeframe_consistency(symbol, timeframe, strategies)
                
                # Lưu kết quả
                analysis_results["symbol_consistency"][symbol][timeframe] = timeframe_results
                
                # Tích luỹ kết quả cho phân tích tổng thể
                if "timeframe_consistency" not in analysis_results:
                    analysis_results["timeframe_consistency"] = {}
                
                if timeframe not in analysis_results["timeframe_consistency"]:
                    analysis_results["timeframe_consistency"][timeframe] = {
                        "agreement_percentage": 0,
                        "contradiction_percentage": 0,
                        "false_signal_ratio": 0,
                        "samples_count": 0
                    }
                
                # Cập nhật kết quả timeframe
                tf_result = analysis_results["timeframe_consistency"][timeframe]
                tf_result["agreement_percentage"] += timeframe_results["agreement_percentage"]
                tf_result["contradiction_percentage"] += timeframe_results["contradiction_percentage"]
                tf_result["false_signal_ratio"] += timeframe_results["false_signal_ratio"]
                tf_result["samples_count"] += 1
        
        # Tính toán giá trị trung bình cho từng timeframe
        for timeframe, results in analysis_results["timeframe_consistency"].items():
            if results["samples_count"] > 0:
                results["agreement_percentage"] /= results["samples_count"]
                results["contradiction_percentage"] /= results["samples_count"]
                results["false_signal_ratio"] /= results["samples_count"]
        
        # Tính toán tổng hợp tính nhất quán cho từng chiến lược
        self._calculate_strategy_consistency(analysis_results)
        
        # Tính toán ma trận tương quan giữa các chiến lược
        self._calculate_correlation_matrix(analysis_results)
        
        # Tính toán tính nhất quán tổng thể
        self._calculate_overall_consistency(analysis_results)
        
        # Xác định giai đoạn có xung đột
        self._identify_conflicting_periods(analysis_results)
        
        # Đưa ra khuyến nghị
        self._generate_recommendations(analysis_results)
        
        # Lưu kết quả
        self._save_results(analysis_results)
        
        logger.info("Hoàn thành phân tích tính nhất quán")
        
        return analysis_results
    
    def _analyze_timeframe_consistency(self, symbol, timeframe, strategies):
        """
        Phân tích tính nhất quán trong một timeframe cụ thể
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            strategies (list): Danh sách chiến lược
            
        Returns:
            dict: Kết quả phân tích
        """
        # Tạo DataFrame chung với tất cả tín hiệu
        signals_combined = None
        
        for strategy in strategies:
            df = self.signals_data[symbol][timeframe][strategy]
            
            # Chỉ giữ lại cột timestamp và signal
            df_signals = df[['timestamp', 'signal']].copy()
            df_signals.columns = ['timestamp', strategy]
            
            if signals_combined is None:
                signals_combined = df_signals
            else:
                signals_combined = pd.merge(signals_combined, df_signals, on='timestamp', how='outer')
        
        if signals_combined is None or len(signals_combined) == 0:
            logger.warning(f"Không có dữ liệu tín hiệu cho {symbol} {timeframe}")
            return {
                "agreement_percentage": 0,
                "contradiction_percentage": 0,
                "false_signal_ratio": 0,
                "correlation_matrix": {},
                "conflicting_periods": []
            }
        
        # Đảm bảo tất cả giá trị NaN được thay thế bằng 0 (không có tín hiệu)
        signals_combined = signals_combined.fillna(0)
        
        # Thêm cột đếm số lượng tín hiệu mua và bán
        signals_combined['buy_count'] = (signals_combined[strategies] == 1).sum(axis=1)
        signals_combined['sell_count'] = (signals_combined[strategies] == -1).sum(axis=1)
        signals_combined['hedge_count'] = (signals_combined[strategies] == 2).sum(axis=1)
        signals_combined['total_signals'] = (signals_combined[strategies] != 0).sum(axis=1)
        
        # Tính tỷ lệ đồng thuận
        signals_with_any = signals_combined[signals_combined['total_signals'] > 0]
        
        if len(signals_with_any) == 0:
            logger.warning(f"Không có tín hiệu nào cho {symbol} {timeframe}")
            return {
                "agreement_percentage": 0,
                "contradiction_percentage": 0,
                "false_signal_ratio": 0,
                "correlation_matrix": {},
                "conflicting_periods": []
            }
        
        # Đồng thuận: khi tất cả tín hiệu đều cùng hướng
        agreement_count = len(signals_with_any[(signals_with_any['buy_count'] > 0) & (signals_with_any['sell_count'] == 0) & (signals_with_any['hedge_count'] == 0)]) + \
                         len(signals_with_any[(signals_with_any['sell_count'] > 0) & (signals_with_any['buy_count'] == 0) & (signals_with_any['hedge_count'] == 0)]) + \
                         len(signals_with_any[(signals_with_any['hedge_count'] > 0) & (signals_with_any['buy_count'] == 0) & (signals_with_any['sell_count'] == 0)])
        
        agreement_percentage = (agreement_count / len(signals_with_any)) * 100
        
        # Mâu thuẫn: khi có cả tín hiệu mua và bán cùng lúc
        contradiction_count = len(signals_with_any[(signals_with_any['buy_count'] > 0) & (signals_with_any['sell_count'] > 0)])
        contradiction_percentage = (contradiction_count / len(signals_with_any)) * 100
        
        # Tính ma trận tương quan giữa các chiến lược
        correlation_matrix = signals_combined[strategies].corr()
        
        # Xác định giai đoạn có xung đột
        conflicting_periods = []
        
        for idx, row in signals_with_any[(signals_with_any['buy_count'] > 0) & (signals_with_any['sell_count'] > 0)].iterrows():
            # Tìm các chiến lược đưa ra tín hiệu mua
            buy_strategies = [s for s in strategies if row[s] == 1]
            
            # Tìm các chiến lược đưa ra tín hiệu bán
            sell_strategies = [s for s in strategies if row[s] == -1]
            
            conflicting_periods.append({
                "timestamp": row['timestamp'],
                "buy_strategies": buy_strategies,
                "sell_strategies": sell_strategies,
                "buy_count": row['buy_count'],
                "sell_count": row['sell_count']
            })
        
        # Phân tích tín hiệu sai (giả định tín hiệu sai là khi chỉ có một chiến lược đưa ra tín hiệu)
        false_signals = len(signals_with_any[(signals_with_any['total_signals'] == 1)]) / len(signals_with_any) if len(signals_with_any) > 0 else 0
        
        # Kết quả phân tích
        analysis_result = {
            "agreement_percentage": agreement_percentage,
            "contradiction_percentage": contradiction_percentage,
            "false_signal_ratio": false_signals,
            "correlation_matrix": correlation_matrix.to_dict(),
            "conflicting_periods": conflicting_periods
        }
        
        return analysis_result
    
    def _calculate_strategy_consistency(self, analysis_results):
        """
        Tính toán tính nhất quán cho từng chiến lược
        
        Args:
            analysis_results (dict): Kết quả phân tích
        """
        # Khởi tạo kết quả cho từng chiến lược
        for strategy in self.config["strategies"]:
            analysis_results["strategy_consistency"][strategy] = {
                "agreement_count": 0,
                "contradiction_count": 0,
                "false_signal_count": 0,
                "total_signals": 0,
                "average_correlation": 0
            }
        
        # Tính toán từ dữ liệu chi tiết
        for symbol in analysis_results["symbol_consistency"]:
            for timeframe in analysis_results["symbol_consistency"][symbol]:
                tf_results = analysis_results["symbol_consistency"][symbol][timeframe]
                
                # Xử lý ma trận tương quan
                if "correlation_matrix" in tf_results:
                    corr_matrix = tf_results["correlation_matrix"]
                    
                    for strategy1 in corr_matrix:
                        for strategy2 in corr_matrix[strategy1]:
                            if strategy1 != strategy2:
                                analysis_results["strategy_consistency"][strategy1]["average_correlation"] += corr_matrix[strategy1][strategy2]
                                analysis_results["strategy_consistency"][strategy1]["total_signals"] += 1
                
                # Xử lý giai đoạn xung đột
                if "conflicting_periods" in tf_results:
                    for period in tf_results["conflicting_periods"]:
                        for strategy in period["buy_strategies"]:
                            analysis_results["strategy_consistency"][strategy]["contradiction_count"] += 1
                        
                        for strategy in period["sell_strategies"]:
                            analysis_results["strategy_consistency"][strategy]["contradiction_count"] += 1
        
        # Tính giá trị trung bình cho mỗi chiến lược
        for strategy in analysis_results["strategy_consistency"]:
            if analysis_results["strategy_consistency"][strategy]["total_signals"] > 0:
                analysis_results["strategy_consistency"][strategy]["average_correlation"] /= analysis_results["strategy_consistency"][strategy]["total_signals"]
    
    def _calculate_correlation_matrix(self, analysis_results):
        """
        Tính toán ma trận tương quan tổng thể giữa các chiến lược
        
        Args:
            analysis_results (dict): Kết quả phân tích
        """
        strategies = self.config["strategies"]
        correlation_matrix = {s: {s2: 0 for s2 in strategies} for s in strategies}
        count_matrix = {s: {s2: 0 for s2 in strategies} for s in strategies}
        
        # Tính tổng tương quan từ tất cả symbol và timeframe
        for symbol in analysis_results["symbol_consistency"]:
            for timeframe in analysis_results["symbol_consistency"][symbol]:
                tf_results = analysis_results["symbol_consistency"][symbol][timeframe]
                
                if "correlation_matrix" in tf_results:
                    corr_matrix = tf_results["correlation_matrix"]
                    
                    for strategy1 in corr_matrix:
                        for strategy2 in corr_matrix[strategy1]:
                            if strategy1 in strategies and strategy2 in strategies:
                                correlation_matrix[strategy1][strategy2] += corr_matrix[strategy1][strategy2]
                                count_matrix[strategy1][strategy2] += 1
        
        # Tính giá trị trung bình
        for strategy1 in correlation_matrix:
            for strategy2 in correlation_matrix[strategy1]:
                if count_matrix[strategy1][strategy2] > 0:
                    correlation_matrix[strategy1][strategy2] /= count_matrix[strategy1][strategy2]
                    
                    # Xử lý NaN
                    if np.isnan(correlation_matrix[strategy1][strategy2]):
                        correlation_matrix[strategy1][strategy2] = 0
        
        analysis_results["correlation_matrix"] = correlation_matrix
    
    def _calculate_overall_consistency(self, analysis_results):
        """
        Tính toán tính nhất quán tổng thể
        
        Args:
            analysis_results (dict): Kết quả phân tích
        """
        # Kết quả tổng thể
        analysis_results["overall_consistency"] = {
            "agreement_percentage": 0,
            "contradiction_percentage": 0,
            "false_signal_ratio": 0,
            "average_correlation": 0,
            "samples_count": 0
        }
        
        # Tính tổng từ tất cả symbol và timeframe
        for symbol in analysis_results["symbol_consistency"]:
            for timeframe in analysis_results["symbol_consistency"][symbol]:
                tf_results = analysis_results["symbol_consistency"][symbol][timeframe]
                
                analysis_results["overall_consistency"]["agreement_percentage"] += tf_results["agreement_percentage"]
                analysis_results["overall_consistency"]["contradiction_percentage"] += tf_results["contradiction_percentage"]
                analysis_results["overall_consistency"]["false_signal_ratio"] += tf_results["false_signal_ratio"]
                analysis_results["overall_consistency"]["samples_count"] += 1
        
        # Tính giá trị trung bình
        if analysis_results["overall_consistency"]["samples_count"] > 0:
            analysis_results["overall_consistency"]["agreement_percentage"] /= analysis_results["overall_consistency"]["samples_count"]
            analysis_results["overall_consistency"]["contradiction_percentage"] /= analysis_results["overall_consistency"]["samples_count"]
            analysis_results["overall_consistency"]["false_signal_ratio"] /= analysis_results["overall_consistency"]["samples_count"]
        
        # Tính tương quan trung bình
        total_correlation = 0
        correlation_count = 0
        
        for strategy1 in analysis_results["correlation_matrix"]:
            for strategy2 in analysis_results["correlation_matrix"][strategy1]:
                if strategy1 != strategy2:
                    total_correlation += analysis_results["correlation_matrix"][strategy1][strategy2]
                    correlation_count += 1
        
        if correlation_count > 0:
            analysis_results["overall_consistency"]["average_correlation"] = total_correlation / correlation_count
    
    def _identify_conflicting_periods(self, analysis_results):
        """
        Xác định các giai đoạn có xung đột lớn
        
        Args:
            analysis_results (dict): Kết quả phân tích
        """
        # Tập hợp tất cả giai đoạn xung đột từ các symbol và timeframe
        all_conflicts = []
        
        for symbol in analysis_results["symbol_consistency"]:
            for timeframe in analysis_results["symbol_consistency"][symbol]:
                tf_results = analysis_results["symbol_consistency"][symbol][timeframe]
                
                if "conflicting_periods" in tf_results:
                    for period in tf_results["conflicting_periods"]:
                        all_conflicts.append({
                            "timestamp": period["timestamp"],
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "buy_strategies": period["buy_strategies"],
                            "sell_strategies": period["sell_strategies"],
                            "buy_count": period["buy_count"],
                            "sell_count": period["sell_count"],
                            "conflict_severity": period["buy_count"] * period["sell_count"]  # Độ nghiêm trọng
                        })
        
        # Sắp xếp theo độ nghiêm trọng
        all_conflicts.sort(key=lambda x: x["conflict_severity"], reverse=True)
        
        # Lấy top 20 xung đột nghiêm trọng nhất
        analysis_results["conflicting_periods"] = all_conflicts[:20]
    
    def _generate_recommendations(self, analysis_results):
        """
        Đưa ra các khuyến nghị dựa trên kết quả phân tích
        
        Args:
            analysis_results (dict): Kết quả phân tích
        """
        # Lấy ngưỡng tính nhất quán
        thresholds = self.config["consistency_thresholds"]
        
        # Khuyến nghị dựa trên tính nhất quán tổng thể
        overall = analysis_results["overall_consistency"]
        recommendations = []
        
        if overall["agreement_percentage"] < thresholds["min_agreement_percentage"]:
            recommendations.append({
                "type": "critical",
                "recommendation": "Tỷ lệ đồng thuận giữa các chiến lược quá thấp.",
                "details": f"Tỷ lệ đồng thuận hiện tại: {overall['agreement_percentage']:.2f}%, cần tối thiểu {thresholds['min_agreement_percentage']}%.",
                "action": "Cân nhắc loại bỏ hoặc tinh chỉnh một số chiến lược để tăng tính đồng thuận."
            })
        
        if overall["contradiction_percentage"] > thresholds["max_contradiction_percentage"]:
            recommendations.append({
                "type": "critical",
                "recommendation": "Tỷ lệ mâu thuẫn giữa các chiến lược quá cao.",
                "details": f"Tỷ lệ mâu thuẫn hiện tại: {overall['contradiction_percentage']:.2f}%, cần tối đa {thresholds['max_contradiction_percentage']}%.",
                "action": "Xem xét lại việc kết hợp các chiến lược và tăng cường cơ chế phòng ngừa mâu thuẫn."
            })
        
        if overall["false_signal_ratio"] > thresholds["max_false_signal_ratio"]:
            recommendations.append({
                "type": "warning",
                "recommendation": "Tỷ lệ tín hiệu giả cao.",
                "details": f"Tỷ lệ tín hiệu giả hiện tại: {overall['false_signal_ratio']:.2f}, cần tối đa {thresholds['max_false_signal_ratio']}.",
                "action": "Cải thiện bộ lọc tín hiệu và xác nhận chéo giữa các chiến lược."
            })
        
        if overall["average_correlation"] < thresholds["min_strategy_correlation"]:
            recommendations.append({
                "type": "warning",
                "recommendation": "Tương quan giữa các chiến lược quá thấp.",
                "details": f"Tương quan trung bình hiện tại: {overall['average_correlation']:.2f}, cần tối thiểu {thresholds['min_strategy_correlation']}.",
                "action": "Cân nhắc kết hợp các chiến lược có tương quan cao hơn hoặc cải thiện cơ chế đồng thuận."
            })
        
        # Khuyến nghị cho từng chiến lược
        for strategy, stats in analysis_results["strategy_consistency"].items():
            # Kiểm tra tương quan
            if stats["average_correlation"] < thresholds["min_strategy_correlation"] / 2:
                recommendations.append({
                    "type": "warning",
                    "recommendation": f"Chiến lược {strategy} có tương quan thấp với các chiến lược khác.",
                    "details": f"Tương quan trung bình: {stats['average_correlation']:.2f}, quá thấp so với ngưỡng {thresholds['min_strategy_correlation']}.",
                    "action": f"Xem xét lại cách hoạt động của chiến lược {strategy} hoặc cân nhắc loại bỏ."
                })
            
            # Kiểm tra mâu thuẫn
            if stats["contradiction_count"] > 10:  # Ngưỡng tùy chỉnh, có thể điều chỉnh
                recommendations.append({
                    "type": "warning",
                    "recommendation": f"Chiến lược {strategy} thường xuyên mâu thuẫn với các chiến lược khác.",
                    "details": f"Số lần mâu thuẫn: {stats['contradiction_count']}, quá cao.",
                    "action": f"Xem xét lại cách tạo tín hiệu của chiến lược {strategy}."
                })
        
        # Khuyến nghị cho từng timeframe
        for timeframe, stats in analysis_results["timeframe_consistency"].items():
            if stats["contradiction_percentage"] > thresholds["max_contradiction_percentage"] * 1.5:
                recommendations.append({
                    "type": "warning",
                    "recommendation": f"Timeframe {timeframe} có tỷ lệ mâu thuẫn rất cao.",
                    "details": f"Tỷ lệ mâu thuẫn: {stats['contradiction_percentage']:.2f}%, vượt quá ngưỡng {thresholds['max_contradiction_percentage']}% nhiều.",
                    "action": f"Xem xét lại việc kết hợp các chiến lược trong timeframe {timeframe}."
                })
        
        # Khuyến nghị dựa trên xung đột
        if len(analysis_results["conflicting_periods"]) > 0:
            # Đếm số lượng xung đột theo từng cặp chiến lược
            strategy_pairs = defaultdict(int)
            
            for conflict in analysis_results["conflicting_periods"]:
                for buy_strategy in conflict["buy_strategies"]:
                    for sell_strategy in conflict["sell_strategies"]:
                        pair = tuple(sorted([buy_strategy, sell_strategy]))
                        strategy_pairs[pair] += 1
            
            # Tìm cặp chiến lược xung đột nhiều nhất
            if strategy_pairs:
                most_conflicting_pair = max(strategy_pairs.items(), key=lambda x: x[1])
                
                recommendations.append({
                    "type": "critical",
                    "recommendation": f"Cặp chiến lược {most_conflicting_pair[0][0]} và {most_conflicting_pair[0][1]} thường xuyên xung đột.",
                    "details": f"Số lần xung đột: {most_conflicting_pair[1]}, cao nhất trong các cặp chiến lược.",
                    "action": "Cân nhắc sử dụng cơ chế trọng số hoặc thiết lập một cơ chế quyết định chung để giải quyết xung đột."
                })
        
        # Nếu không có vấn đề gì
        if len(recommendations) == 0:
            recommendations.append({
                "type": "info",
                "recommendation": "Các chiến lược có tính nhất quán tốt.",
                "details": f"Tỷ lệ đồng thuận: {overall['agreement_percentage']:.2f}%, tỷ lệ mâu thuẫn: {overall['contradiction_percentage']:.2f}%.",
                "action": "Tiếp tục theo dõi và tối ưu hóa cơ chế quyết định."
            })
        
        analysis_results["recommendations"] = recommendations
    
    def _save_results(self, analysis_results):
        """
        Lưu kết quả phân tích
        
        Args:
            analysis_results (dict): Kết quả phân tích
        """
        output_formats = self.config["output_formats"]
        
        # Tạo timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Lưu dạng JSON
        if "json" in output_formats:
            json_path = os.path.join(self.results_dir, f"signal_consistency_{timestamp}.json")
            with open(json_path, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            logger.info(f"Đã lưu kết quả phân tích dạng JSON vào {json_path}")
        
        # Lưu dạng CSV
        if "csv" in output_formats:
            # Tạo DataFrame từ kết quả phân tích tổng quan
            overall_df = pd.DataFrame([analysis_results["overall_consistency"]])
            overall_csv = os.path.join(self.results_dir, f"signal_consistency_overall_{timestamp}.csv")
            overall_df.to_csv(overall_csv, index=False)
            
            # Tạo DataFrame từ kết quả phân tích theo timeframe
            timeframe_df = pd.DataFrame.from_dict(analysis_results["timeframe_consistency"], orient='index')
            timeframe_csv = os.path.join(self.results_dir, f"signal_consistency_timeframe_{timestamp}.csv")
            timeframe_df.to_csv(timeframe_csv, index=True, index_label='timeframe')
            
            # Tạo DataFrame từ kết quả phân tích theo chiến lược
            strategy_df = pd.DataFrame.from_dict(analysis_results["strategy_consistency"], orient='index')
            strategy_csv = os.path.join(self.results_dir, f"signal_consistency_strategy_{timestamp}.csv")
            strategy_df.to_csv(strategy_csv, index=True, index_label='strategy')
            
            logger.info(f"Đã lưu kết quả phân tích dạng CSV vào {self.results_dir}")
        
        # Tạo báo cáo HTML
        if "html" in output_formats:
            html_path = os.path.join(self.results_dir, f"signal_consistency_{timestamp}.html")
            
            with open(html_path, 'w') as f:
                f.write("""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Báo cáo phân tích tính nhất quán tín hiệu</title>
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
                        .chart-container { margin: 20px 0; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Báo cáo phân tích tính nhất quán tín hiệu</h1>
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
                
                for key, value in analysis_results["overall_consistency"].items():
                    display_key = key.replace('_', ' ').title()
                    
                    if 'percentage' in key:
                        display_value = f"{value:.2f}%"
                    else:
                        display_value = f"{value:.2f}" if isinstance(value, float) else value
                    
                    f.write(f"""
                            <tr>
                                <td>{display_key}</td>
                                <td>{display_value}</td>
                            </tr>
                    """)
                
                # Thống kê theo timeframe
                f.write("""
                        </table>
                        
                        <h2>Thống kê theo timeframe</h2>
                        <table>
                            <tr>
                                <th>Timeframe</th>
                                <th>Tỷ lệ đồng thuận</th>
                                <th>Tỷ lệ mâu thuẫn</th>
                                <th>Tỷ lệ tín hiệu giả</th>
                            </tr>
                """)
                
                for timeframe, stats in analysis_results["timeframe_consistency"].items():
                    f.write(f"""
                            <tr>
                                <td>{timeframe}</td>
                                <td>{stats['agreement_percentage']:.2f}%</td>
                                <td>{stats['contradiction_percentage']:.2f}%</td>
                                <td>{stats['false_signal_ratio']:.2f}</td>
                            </tr>
                    """)
                
                # Thống kê theo chiến lược
                f.write("""
                        </table>
                        
                        <h2>Thống kê theo chiến lược</h2>
                        <table>
                            <tr>
                                <th>Chiến lược</th>
                                <th>Số xung đột</th>
                                <th>Tương quan trung bình</th>
                            </tr>
                """)
                
                for strategy, stats in analysis_results["strategy_consistency"].items():
                    f.write(f"""
                            <tr>
                                <td>{strategy}</td>
                                <td>{stats['contradiction_count']}</td>
                                <td>{stats['average_correlation']:.2f}</td>
                            </tr>
                    """)
                
                # Ma trận tương quan
                f.write("""
                        </table>
                        
                        <h2>Ma trận tương quan</h2>
                        <table>
                            <tr>
                                <th>Chiến lược</th>
                """)
                
                strategies = list(analysis_results["correlation_matrix"].keys())
                
                for strategy in strategies:
                    f.write(f"<th>{strategy}</th>")
                
                f.write("</tr>")
                
                for strategy1 in strategies:
                    f.write(f"<tr><td>{strategy1}</td>")
                    
                    for strategy2 in strategies:
                        corr_value = analysis_results["correlation_matrix"].get(strategy1, {}).get(strategy2, 0)
                        
                        # Màu sắc dựa trên giá trị tương quan
                        color = ""
                        if strategy1 != strategy2:
                            if corr_value > 0.7:
                                color = "style='background-color: #e6ffe6;'"  # xanh lá nhạt
                            elif corr_value > 0.3:
                                color = "style='background-color: #ffffcc;'"  # vàng nhạt
                            elif corr_value < 0:
                                color = "style='background-color: #ffe6e6;'"  # đỏ nhạt
                        
                        f.write(f"<td {color}>{corr_value:.2f}</td>")
                    
                    f.write("</tr>")
                
                # Top xung đột
                if analysis_results["conflicting_periods"]:
                    f.write("""
                            </table>
                            
                            <h2>Top xung đột</h2>
                            <table>
                                <tr>
                                    <th>#</th>
                                    <th>Thời gian</th>
                                    <th>Cặp tiền</th>
                                    <th>Timeframe</th>
                                    <th>Chiến lược mua</th>
                                    <th>Chiến lược bán</th>
                                    <th>Số tín hiệu mua</th>
                                    <th>Số tín hiệu bán</th>
                                    <th>Độ nghiêm trọng</th>
                                </tr>
                    """)
                    
                    for i, conflict in enumerate(analysis_results["conflicting_periods"]):
                        f.write(f"""
                                <tr>
                                    <td>{i+1}</td>
                                    <td>{conflict['timestamp']}</td>
                                    <td>{conflict['symbol']}</td>
                                    <td>{conflict['timeframe']}</td>
                                    <td>{', '.join(conflict['buy_strategies'])}</td>
                                    <td>{', '.join(conflict['sell_strategies'])}</td>
                                    <td>{conflict['buy_count']}</td>
                                    <td>{conflict['sell_count']}</td>
                                    <td>{conflict['conflict_severity']}</td>
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
                                <th>Hành động đề xuất</th>
                            </tr>
                """)
                
                for i, recommendation in enumerate(analysis_results["recommendations"]):
                    recommendation_class = 'critical' if recommendation['type'] == 'critical' else 'warning' if recommendation['type'] == 'warning' else 'info'
                    
                    f.write(f"""
                            <tr>
                                <td>{i+1}</td>
                                <td class="{recommendation_class}">{recommendation['type'].upper()}</td>
                                <td>{recommendation['recommendation']}</td>
                                <td>{recommendation['details']}</td>
                                <td>{recommendation['action']}</td>
                            </tr>
                    """)
                
                f.write("""
                        </table>
                        
                        <h2>Biểu đồ</h2>
                        <div class="chart-container">
                            <p>Các biểu đồ được lưu trong thư mục 'charts' của báo cáo.</p>
                        </div>
                        
                        <p>Báo cáo này được tạo tự động bởi công cụ phân tích tính nhất quán tín hiệu.</p>
                    </div>
                </body>
                </html>
                """)
            
            logger.info(f"Đã tạo báo cáo HTML: {html_path}")
        
        # Tạo biểu đồ
        if "charts" in output_formats:
            self._create_charts(analysis_results, timestamp)
    
    def _create_charts(self, analysis_results, timestamp):
        """
        Tạo các biểu đồ phân tích
        
        Args:
            analysis_results (dict): Kết quả phân tích
            timestamp (str): Timestamp
        """
        try:
            # Tạo thư mục charts
            charts_dir = os.path.join(self.results_dir, 'charts')
            os.makedirs(charts_dir, exist_ok=True)
            
            # 1. Biểu đồ tỷ lệ đồng thuận và mâu thuẫn theo timeframe
            plt.figure(figsize=(10, 6))
            
            timeframes = list(analysis_results["timeframe_consistency"].keys())
            agreement_percentages = [analysis_results["timeframe_consistency"][tf]["agreement_percentage"] for tf in timeframes]
            contradiction_percentages = [analysis_results["timeframe_consistency"][tf]["contradiction_percentage"] for tf in timeframes]
            
            x = range(len(timeframes))
            width = 0.35
            
            plt.bar([i - width/2 for i in x], agreement_percentages, width, label='Tỷ lệ đồng thuận')
            plt.bar([i + width/2 for i in x], contradiction_percentages, width, label='Tỷ lệ mâu thuẫn')
            
            plt.xlabel('Timeframe')
            plt.ylabel('Phần trăm (%)')
            plt.title('Tỷ lệ đồng thuận và mâu thuẫn theo timeframe')
            plt.xticks(x, timeframes)
            plt.legend()
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, f"timeframe_consistency_{timestamp}.png"))
            plt.close()
            
            # 2. Biểu đồ số lượng xung đột theo chiến lược
            plt.figure(figsize=(12, 6))
            
            strategies = list(analysis_results["strategy_consistency"].keys())
            contradiction_counts = [analysis_results["strategy_consistency"][s]["contradiction_count"] for s in strategies]
            
            plt.bar(strategies, contradiction_counts, color='#e74c3c')
            
            plt.xlabel('Chiến lược')
            plt.ylabel('Số lượng xung đột')
            plt.title('Số lượng xung đột theo chiến lược')
            plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, f"strategy_conflicts_{timestamp}.png"))
            plt.close()
            
            # 3. Biểu đồ ma trận tương quan
            plt.figure(figsize=(10, 8))
            
            strategies = list(analysis_results["correlation_matrix"].keys())
            corr_matrix = np.zeros((len(strategies), len(strategies)))
            
            for i, strategy1 in enumerate(strategies):
                for j, strategy2 in enumerate(strategies):
                    corr_matrix[i, j] = analysis_results["correlation_matrix"].get(strategy1, {}).get(strategy2, 0)
            
            plt.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
            plt.colorbar()
            
            plt.xticks(range(len(strategies)), strategies, rotation=45, ha='right')
            plt.yticks(range(len(strategies)), strategies)
            
            plt.title('Ma trận tương quan giữa các chiến lược')
            
            for i in range(len(strategies)):
                for j in range(len(strategies)):
                    text = plt.text(j, i, f"{corr_matrix[i, j]:.2f}",
                                   ha="center", va="center", color="black" if abs(corr_matrix[i, j]) < 0.5 else "white")
            
            plt.tight_layout()
            plt.savefig(os.path.join(charts_dir, f"correlation_matrix_{timestamp}.png"))
            plt.close()
            
            # 4. Biểu đồ xung đột theo thời gian (nếu có dữ liệu)
            if analysis_results["conflicting_periods"]:
                plt.figure(figsize=(12, 6))
                
                conflict_times = [pd.to_datetime(conflict["timestamp"]) for conflict in analysis_results["conflicting_periods"]]
                conflict_severity = [conflict["conflict_severity"] for conflict in analysis_results["conflicting_periods"]]
                
                plt.scatter(conflict_times, conflict_severity, color='#e74c3c', s=50, alpha=0.7)
                
                plt.xlabel('Thời gian')
                plt.ylabel('Độ nghiêm trọng xung đột')
                plt.title('Phân bố xung đột theo thời gian')
                
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
                plt.gcf().autofmt_xdate()
                
                plt.tight_layout()
                plt.savefig(os.path.join(charts_dir, f"conflict_timeline_{timestamp}.png"))
                plt.close()
            
            logger.info(f"Đã tạo các biểu đồ phân tích trong thư mục {charts_dir}")
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ phân tích: {e}")


def main():
    """
    Hàm chính
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Signal Consistency Analyzer')
    parser.add_argument('--config', type=str, default='signal_analyzer_config.json',
                      help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Khởi tạo analyzer
    analyzer = SignalConsistencyAnalyzer(config_path=args.config)
    
    # Tải dữ liệu tín hiệu
    analyzer.load_signals()
    
    # Phân tích tính nhất quán
    results = analyzer.analyze_consistency()
    
    # Hiển thị kết quả tổng thể
    print("\n===== SIGNAL CONSISTENCY ANALYSIS SUMMARY =====")
    print(f"Agreement Percentage: {results['overall_consistency']['agreement_percentage']:.2f}%")
    print(f"Contradiction Percentage: {results['overall_consistency']['contradiction_percentage']:.2f}%")
    print(f"Average Correlation: {results['overall_consistency']['average_correlation']:.2f}")
    
    # Hiển thị khuyến nghị
    print("\nRecommendations:")
    for i, recommendation in enumerate(results['recommendations']):
        print(f"{i+1}. [{recommendation['type'].upper()}] {recommendation['recommendation']}")
        print(f"   Details: {recommendation['details']}")
        print(f"   Action: {recommendation['action']}")
    
    print(f"\nDetailed reports have been saved to {analyzer.results_dir}")
    print("================================================")

if __name__ == "__main__":
    main()