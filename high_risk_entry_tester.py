#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hệ thống kiểm tra điểm vào lệnh rủi ro cao

Module này phân tích hiệu suất của các điểm vào lệnh có rủi ro cao 
và thời điểm tối ưu để vào lệnh, tập trung vào lệnh SHORT trong phiên 
London và New York.
"""

import os
import sys
import json
import time
import logging
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('high_risk_entry_tester.log')
    ]
)

logger = logging.getLogger('high_risk_entry_tester')

# Thử import các module khác
try:
    from time_optimized_strategy import TimeOptimizedStrategy
except ImportError:
    logger.error("Không thể import module TimeOptimizedStrategy. Hãy đảm bảo tệp time_optimized_strategy.py tồn tại")
    sys.exit(1)

class HighRiskEntryTester:
    """
    Lớp kiểm tra điểm vào lệnh rủi ro cao
    """
    
    def __init__(
        self, 
        config_path: str = "configs/high_risk_entry_config.json",
        strategy_config_path: str = "configs/time_optimized_strategy_config.json",
        test_data_dir: str = "test_data",
        results_dir: str = "high_risk_results"
    ):
        """
        Khởi tạo hệ thống kiểm tra

        Args:
            config_path (str, optional): Đường dẫn đến file cấu hình. Defaults to "configs/high_risk_entry_config.json".
            strategy_config_path (str, optional): Đường dẫn đến file cấu hình chiến lược. Defaults to "configs/time_optimized_strategy_config.json".
            test_data_dir (str, optional): Thư mục chứa dữ liệu kiểm tra. Defaults to "test_data".
            results_dir (str, optional): Thư mục chứa kết quả kiểm tra. Defaults to "high_risk_results".
        """
        self.config_path = config_path
        self.strategy_config_path = strategy_config_path
        self.test_data_dir = test_data_dir
        self.results_dir = results_dir
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.test_data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Tải cấu hình
        self.config = self._load_config()
        
        # Khởi tạo chiến lược tối ưu
        self.strategy = TimeOptimizedStrategy(strategy_config_path)
        
        # Cấu hình khung thời gian kiểm tra
        self.test_timeframes = self.config.get("test_timeframes", [
            {"name": "London Open", "start_hour": 15, "start_minute": 0, "end_hour": 17, "end_minute": 0, "direction": "short"},
            {"name": "New York Open", "start_hour": 20, "start_minute": 30, "end_hour": 22, "end_minute": 30, "direction": "short"},
            {"name": "Daily Candle Close", "start_hour": 6, "start_minute": 30, "end_hour": 7, "end_minute": 30, "direction": "long"},
            {"name": "Major News Events", "start_hour": 21, "start_minute": 30, "end_hour": 22, "end_minute": 0, "direction": "short"}
        ])
        
        # Cấu hình các cặp tiền kiểm tra
        self.test_symbols = self.config.get("test_symbols", ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"])
        
        # Cấu hình các chỉ báo kiểm tra
        self.test_indicators = self.config.get("test_indicators", [
            {"name": "RSI", "condition": "> 70", "timeframe": "1h", "for_direction": "short"},
            {"name": "RSI", "condition": "< 30", "timeframe": "1h", "for_direction": "long"},
            {"name": "MACD", "condition": "signal_cross_down", "timeframe": "1h", "for_direction": "short"},
            {"name": "MACD", "condition": "signal_cross_up", "timeframe": "1h", "for_direction": "long"},
            {"name": "Price vs EMA", "condition": "> 1%", "timeframe": "1h", "for_direction": "short"},
            {"name": "Price vs EMA", "condition": "< -1%", "timeframe": "1h", "for_direction": "long"}
        ])
        
        # Kết quả kiểm tra
        self.test_results = {}
        
        logger.info(f"Đã khởi tạo HighRiskEntryTester với {len(self.test_timeframes)} khung thời gian và {len(self.test_symbols)} cặp tiền")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file

        Returns:
            Dict: Cấu hình
        """
        config = {}
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                logger.warning(f"Không tìm thấy file cấu hình {self.config_path}, sử dụng cấu hình mặc định")
                # Tạo cấu hình mặc định
                config = self._create_default_config()
                # Lưu cấu hình mặc định
                self._save_config(config)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            config = self._create_default_config()
        
        return config
    
    def _create_default_config(self) -> Dict:
        """
        Tạo cấu hình mặc định

        Returns:
            Dict: Cấu hình mặc định
        """
        default_config = {
            "test_timeframes": [
                {"name": "London Open", "start_hour": 15, "start_minute": 0, "end_hour": 17, "end_minute": 0, "direction": "short"},
                {"name": "New York Open", "start_hour": 20, "start_minute": 30, "end_hour": 22, "end_minute": 30, "direction": "short"},
                {"name": "Daily Candle Close", "start_hour": 6, "start_minute": 30, "end_hour": 7, "end_minute": 30, "direction": "long"},
                {"name": "Major News Events", "start_hour": 21, "start_minute": 30, "end_hour": 22, "end_minute": 0, "direction": "short"}
            ],
            "test_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "LINKUSDT"],
            "test_indicators": [
                {"name": "RSI", "condition": "> 70", "timeframe": "1h", "for_direction": "short"},
                {"name": "RSI", "condition": "< 30", "timeframe": "1h", "for_direction": "long"},
                {"name": "MACD", "condition": "signal_cross_down", "timeframe": "1h", "for_direction": "short"},
                {"name": "MACD", "condition": "signal_cross_up", "timeframe": "1h", "for_direction": "long"},
                {"name": "Price vs EMA", "condition": "> 1%", "timeframe": "1h", "for_direction": "short"},
                {"name": "Price vs EMA", "condition": "< -1%", "timeframe": "1h", "for_direction": "long"}
            ],
            "test_settings": {
                "days_to_test": 30,
                "risk_reward_ratio": 3.0,
                "stop_loss_percent": 7.0,
                "take_profit_percent": 21.0,
                "entry_timeout_minutes": 15,
                "use_trailing_stop": True,
                "trailing_stop_activation": 10.0,
                "trailing_stop_callback": 3.0
            },
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return default_config
    
    def _save_config(self, config: Dict = None):
        """
        Lưu cấu hình vào file

        Args:
            config (Dict, optional): Cấu hình cần lưu. Defaults to None.
        """
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
    
    def load_test_data(self, symbol: str, timeframe: str = "1h", days: int = 30) -> pd.DataFrame:
        """
        Tải dữ liệu kiểm tra cho một cặp tiền

        Args:
            symbol (str): Cặp tiền cần tải dữ liệu
            timeframe (str, optional): Khung thời gian. Defaults to "1h".
            days (int, optional): Số ngày dữ liệu. Defaults to 30.

        Returns:
            pd.DataFrame: Dữ liệu kiểm tra
        """
        # Đường dẫn đến file dữ liệu
        file_path = os.path.join(self.test_data_dir, f"{symbol}_{timeframe}_{days}d.csv")
        
        # Kiểm tra xem file đã tồn tại chưa
        if os.path.exists(file_path):
            try:
                # Tải dữ liệu từ file
                data = pd.read_csv(file_path)
                
                # Chuyển cột timestamp sang datetime
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                logger.info(f"Đã tải dữ liệu từ {file_path}, {len(data)} dòng")
                
                return data
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu từ {file_path}: {e}")
        
        # Nếu không tìm thấy file hoặc có lỗi, tạo dữ liệu mẫu để kiểm tra
        logger.warning(f"Không tìm thấy file dữ liệu {file_path}, tạo dữ liệu mẫu để kiểm tra")
        
        # Tạo dữ liệu mẫu
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Tạo danh sách ngày
        dates = pd.date_range(start=start_date, end=end_date, freq=timeframe)
        
        # Tạo dữ liệu giả
        np.random.seed(42)  # Để kết quả ổn định
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.normal(1000, 100, len(dates)),
            'high': np.random.normal(1050, 100, len(dates)),
            'low': np.random.normal(950, 100, len(dates)),
            'close': np.random.normal(1000, 100, len(dates)),
            'volume': np.random.lognormal(10, 1, len(dates))
        })
        
        # Đảm bảo mỗi nến có giá open, high, low, close hợp lý
        for i in range(len(data)):
            high = max(data.loc[i, 'open'], data.loc[i, 'close']) + abs(np.random.normal(10, 5))
            low = min(data.loc[i, 'open'], data.loc[i, 'close']) - abs(np.random.normal(10, 5))
            data.loc[i, 'high'] = high
            data.loc[i, 'low'] = low
        
        # Lưu dữ liệu
        try:
            data.to_csv(file_path, index=False)
            logger.info(f"Đã tạo và lưu dữ liệu mẫu vào {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu mẫu vào {file_path}: {e}")
        
        return data
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật

        Args:
            data (pd.DataFrame): Dữ liệu giá

        Returns:
            pd.DataFrame: Dữ liệu với các chỉ báo
        """
        df = data.copy()
        
        # RSI
        def calculate_rsi(series, period=14):
            # Tính toán RSI
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        
        # Tính RSI
        df['rsi'] = calculate_rsi(df['close'], 14)
        
        # MACD
        def calculate_macd(series, fast=12, slow=26, signal=9):
            # Tính EMA nhanh và chậm
            ema_fast = series.ewm(span=fast, adjust=False).mean()
            ema_slow = series.ewm(span=slow, adjust=False).mean()
            
            # Tính MACD Line = EMA nhanh - EMA chậm
            macd_line = ema_fast - ema_slow
            
            # Tính đường tín hiệu = EMA của MACD Line
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            
            # Tính histogram = MACD Line - Signal Line
            histogram = macd_line - signal_line
            
            return pd.DataFrame({
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram
            })
        
        # Tính MACD
        macd_data = calculate_macd(df['close'])
        df['macd_line'] = macd_data['macd_line']
        df['macd_signal'] = macd_data['signal_line']
        df['macd_histogram'] = macd_data['histogram']
        
        # Tính EMA
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema55'] = df['close'].ewm(span=55, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # Tính SMA
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        df['sma200'] = df['close'].rolling(window=200).mean()
        
        # Tính Bollinger Bands
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['upper_band'] = df['sma20'] + 2 * df['close'].rolling(window=20).std()
        df['lower_band'] = df['sma20'] - 2 * df['close'].rolling(window=20).std()
        
        # Tính phần trăm giá so với EMA21
        df['pct_from_ema21'] = 100 * (df['close'] - df['ema21']) / df['ema21']
        
        # Tính khối lượng giao dịch tương đối
        df['volume_sma20'] = df['volume'].rolling(window=20).mean()
        df['relative_volume'] = df['volume'] / df['volume_sma20']
        
        # Tính chỉ báo MACD tín hiệu cắt nhau
        df['macd_signal_cross'] = np.zeros(len(df))
        for i in range(1, len(df)):
            if df['macd_line'].iloc[i-1] < df['macd_signal'].iloc[i-1] and df['macd_line'].iloc[i] > df['macd_signal'].iloc[i]:
                df.loc[df.index[i], 'macd_signal_cross'] = 1  # Tín hiệu cắt lên
            elif df['macd_line'].iloc[i-1] > df['macd_signal'].iloc[i-1] and df['macd_line'].iloc[i] < df['macd_signal'].iloc[i]:
                df.loc[df.index[i], 'macd_signal_cross'] = -1  # Tín hiệu cắt xuống
        
        return df
    
    def detect_high_risk_entries(self, data: pd.DataFrame, timeframe_info: Dict, direction: str) -> List[Dict]:
        """
        Phát hiện các điểm vào lệnh rủi ro cao

        Args:
            data (pd.DataFrame): Dữ liệu với các chỉ báo
            timeframe_info (Dict): Thông tin về khung thời gian
            direction (str): Hướng giao dịch (long/short)

        Returns:
            List[Dict]: Danh sách các điểm vào lệnh
        """
        entries = []
        
        # Lấy thông tin về thời gian
        start_hour = timeframe_info["start_hour"]
        start_minute = timeframe_info["start_minute"]
        end_hour = timeframe_info["end_hour"]
        end_minute = timeframe_info["end_minute"]
        
        # Lọc các điểm vào lệnh theo thời gian
        for i in range(1, len(data) - 1):
            dt = data.iloc[i]['timestamp']
            
            # Kiểm tra xem thời gian có nằm trong khoảng cho phép không
            if start_hour < end_hour or (start_hour == end_hour and start_minute <= end_minute):
                # Trường hợp bình thường
                is_in_timeframe = (
                    (dt.hour > start_hour or (dt.hour == start_hour and dt.minute >= start_minute)) and
                    (dt.hour < end_hour or (dt.hour == end_hour and dt.minute <= end_minute))
                )
            else:
                # Trường hợp vượt qua nửa đêm
                is_in_timeframe = (
                    (dt.hour > start_hour or (dt.hour == start_hour and dt.minute >= start_minute)) or
                    (dt.hour < end_hour or (dt.hour == end_hour and dt.minute <= end_minute))
                )
            
            if not is_in_timeframe:
                continue
            
            # Các điều kiện vào lệnh
            if direction == "long":
                # Điểm vào lệnh LONG
                # Điều kiện 1: RSI < 40
                rsi_condition = data.iloc[i]['rsi'] < 40
                
                # Điều kiện 2: Giá dưới EMA21 > 1%
                ema_condition = data.iloc[i]['pct_from_ema21'] < -1
                
                # Điều kiện 3: MACD cắt lên hoặc histogram > 0
                macd_condition = (
                    data.iloc[i]['macd_signal_cross'] == 1 or
                    (data.iloc[i]['macd_histogram'] > 0 and data.iloc[i-1]['macd_histogram'] < 0)
                )
                
                # Điều kiện 4: Khối lượng giao dịch tăng
                volume_condition = data.iloc[i]['relative_volume'] > 1.2
                
                # Điều kiện 5: Giá nằm gần vùng hỗ trợ (giá đã chạm hoặc gần chạm lower_band)
                support_condition = data.iloc[i]['low'] <= data.iloc[i]['lower_band'] * 1.01
                
                # Nếu thỏa mãn đủ điều kiện, thêm vào danh sách
                if (rsi_condition and ema_condition and volume_condition) or (macd_condition and support_condition):
                    entries.append({
                        "index": i,
                        "timestamp": data.iloc[i]['timestamp'],
                        "price": data.iloc[i]['close'],
                        "direction": "long",
                        "rsi": data.iloc[i]['rsi'],
                        "macd_histogram": data.iloc[i]['macd_histogram'],
                        "pct_from_ema21": data.iloc[i]['pct_from_ema21'],
                        "relative_volume": data.iloc[i]['relative_volume']
                    })
            else:
                # Điểm vào lệnh SHORT
                # Điều kiện 1: RSI > 70
                rsi_condition = data.iloc[i]['rsi'] > 70
                
                # Điều kiện 2: Giá trên EMA21 > 1%
                ema_condition = data.iloc[i]['pct_from_ema21'] > 1
                
                # Điều kiện 3: MACD cắt xuống hoặc histogram < 0
                macd_condition = (
                    data.iloc[i]['macd_signal_cross'] == -1 or
                    (data.iloc[i]['macd_histogram'] < 0 and data.iloc[i-1]['macd_histogram'] > 0)
                )
                
                # Điều kiện 4: Khối lượng giao dịch tăng
                volume_condition = data.iloc[i]['relative_volume'] > 1.2
                
                # Điều kiện 5: Giá nằm gần vùng kháng cự (giá đã chạm hoặc gần chạm upper_band)
                resistance_condition = data.iloc[i]['high'] >= data.iloc[i]['upper_band'] * 0.99
                
                # Nếu thỏa mãn đủ điều kiện, thêm vào danh sách
                if (rsi_condition and ema_condition and volume_condition) or (macd_condition and resistance_condition):
                    entries.append({
                        "index": i,
                        "timestamp": data.iloc[i]['timestamp'],
                        "price": data.iloc[i]['close'],
                        "direction": "short",
                        "rsi": data.iloc[i]['rsi'],
                        "macd_histogram": data.iloc[i]['macd_histogram'],
                        "pct_from_ema21": data.iloc[i]['pct_from_ema21'],
                        "relative_volume": data.iloc[i]['relative_volume']
                    })
        
        return entries
    
    def simulate_trade_results(self, data: pd.DataFrame, entries: List[Dict], direction: str) -> List[Dict]:
        """
        Mô phỏng kết quả các lệnh giao dịch

        Args:
            data (pd.DataFrame): Dữ liệu giá
            entries (List[Dict]): Danh sách các điểm vào lệnh
            direction (str): Hướng giao dịch (long/short)

        Returns:
            List[Dict]: Danh sách kết quả giao dịch
        """
        results = []
        
        # Lấy cấu hình kiểm tra
        test_settings = self.config.get("test_settings", {})
        
        # Tỷ lệ R:R
        risk_reward_ratio = test_settings.get("risk_reward_ratio", 3.0)
        
        # Phần trăm stop loss và take profit
        stop_loss_percent = test_settings.get("stop_loss_percent", 7.0) / 100
        take_profit_percent = test_settings.get("take_profit_percent", 21.0) / 100
        
        # Cấu hình trailing stop
        use_trailing_stop = test_settings.get("use_trailing_stop", True)
        trailing_stop_activation = test_settings.get("trailing_stop_activation", 10.0) / 100
        trailing_stop_callback = test_settings.get("trailing_stop_callback", 3.0) / 100
        
        # Mô phỏng kết quả cho từng điểm vào lệnh
        for entry in entries:
            # Lấy thông tin điểm vào lệnh
            entry_index = entry["index"]
            entry_price = entry["price"]
            
            # Tính stop loss và take profit
            if direction == "long":
                stop_loss = entry_price * (1 - stop_loss_percent)
                take_profit = entry_price * (1 + take_profit_percent)
            else:  # short
                stop_loss = entry_price * (1 + stop_loss_percent)
                take_profit = entry_price * (1 - take_profit_percent)
            
            # Kết quả ban đầu
            result = {
                "entry_index": entry_index,
                "entry_timestamp": entry["timestamp"],
                "entry_price": entry_price,
                "direction": direction,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_price": None,
                "exit_timestamp": None,
                "exit_reason": None,
                "pnl_percent": None,
                "pnl_r": None,
                "duration_bars": None
            }
            
            # Theo dõi giá trailing stop
            trailing_stop = stop_loss
            trailing_activated = False
            
            # Mô phỏng giao dịch
            for i in range(entry_index + 1, len(data)):
                current_price = data.iloc[i]["close"]
                current_high = data.iloc[i]["high"]
                current_low = data.iloc[i]["low"]
                
                # Kiểm tra xem đã hit stop loss chưa
                if direction == "long" and current_low <= stop_loss:
                    result["exit_price"] = stop_loss
                    result["exit_timestamp"] = data.iloc[i]["timestamp"]
                    result["exit_reason"] = "stop_loss"
                    break
                elif direction == "short" and current_high >= stop_loss:
                    result["exit_price"] = stop_loss
                    result["exit_timestamp"] = data.iloc[i]["timestamp"]
                    result["exit_reason"] = "stop_loss"
                    break
                
                # Kiểm tra xem đã hit take profit chưa
                if direction == "long" and current_high >= take_profit:
                    result["exit_price"] = take_profit
                    result["exit_timestamp"] = data.iloc[i]["timestamp"]
                    result["exit_reason"] = "take_profit"
                    break
                elif direction == "short" and current_low <= take_profit:
                    result["exit_price"] = take_profit
                    result["exit_timestamp"] = data.iloc[i]["timestamp"]
                    result["exit_reason"] = "take_profit"
                    break
                
                # Kiểm tra trailing stop
                if use_trailing_stop:
                    # Kiểm tra xem trailing stop đã được kích hoạt chưa
                    if not trailing_activated:
                        if direction == "long" and current_price >= entry_price * (1 + trailing_stop_activation):
                            trailing_activated = True
                            trailing_stop = current_price * (1 - trailing_stop_callback)
                            trailing_stop = max(trailing_stop, stop_loss)  # Đảm bảo trailing stop không thấp hơn stop loss ban đầu
                        elif direction == "short" and current_price <= entry_price * (1 - trailing_stop_activation):
                            trailing_activated = True
                            trailing_stop = current_price * (1 + trailing_stop_callback)
                            trailing_stop = min(trailing_stop, stop_loss)  # Đảm bảo trailing stop không cao hơn stop loss ban đầu
                    else:
                        # Cập nhật trailing stop
                        if direction == "long" and current_price > trailing_stop / (1 - trailing_stop_callback):
                            new_trailing_stop = current_price * (1 - trailing_stop_callback)
                            trailing_stop = max(trailing_stop, new_trailing_stop)
                        elif direction == "short" and current_price < trailing_stop / (1 + trailing_stop_callback):
                            new_trailing_stop = current_price * (1 + trailing_stop_callback)
                            trailing_stop = min(trailing_stop, new_trailing_stop)
                    
                    # Kiểm tra xem đã hit trailing stop chưa
                    if trailing_activated:
                        if direction == "long" and current_low <= trailing_stop:
                            result["exit_price"] = trailing_stop
                            result["exit_timestamp"] = data.iloc[i]["timestamp"]
                            result["exit_reason"] = "trailing_stop"
                            break
                        elif direction == "short" and current_high >= trailing_stop:
                            result["exit_price"] = trailing_stop
                            result["exit_timestamp"] = data.iloc[i]["timestamp"]
                            result["exit_reason"] = "trailing_stop"
                            break
            
            # Nếu không có điểm ra, lấy giá đóng cửa của nến cuối cùng
            if result["exit_price"] is None:
                result["exit_price"] = data.iloc[-1]["close"]
                result["exit_timestamp"] = data.iloc[-1]["timestamp"]
                result["exit_reason"] = "end_of_data"
            
            # Tính P/L
            if direction == "long":
                result["pnl_percent"] = 100 * (result["exit_price"] - entry_price) / entry_price
                result["pnl_r"] = result["pnl_percent"] / (100 * stop_loss_percent)
            else:  # short
                result["pnl_percent"] = 100 * (entry_price - result["exit_price"]) / entry_price
                result["pnl_r"] = result["pnl_percent"] / (100 * stop_loss_percent)
            
            # Tính thời gian giao dịch
            result["duration_bars"] = result["exit_timestamp"] - result["entry_timestamp"]
            
            results.append(result)
        
        return results
    
    def run_tests(self) -> None:
        """
        Chạy kiểm tra cho tất cả các cặp tiền và khung thời gian
        """
        # Lấy cấu hình kiểm tra
        test_settings = self.config.get("test_settings", {})
        days_to_test = test_settings.get("days_to_test", 30)
        
        # Chạy kiểm tra cho từng cặp tiền
        for symbol in self.test_symbols:
            self.test_results[symbol] = {}
            
            # Tải dữ liệu
            data = self.load_test_data(symbol, "1h", days_to_test)
            
            # Tính toán các chỉ báo
            data = self.calculate_indicators(data)
            
            # Kiểm tra từng khung thời gian
            for timeframe_info in self.test_timeframes:
                timeframe_name = timeframe_info["name"]
                direction = timeframe_info["direction"]
                
                # Phát hiện các điểm vào lệnh
                entries = self.detect_high_risk_entries(data, timeframe_info, direction)
                
                # Mô phỏng kết quả giao dịch
                results = self.simulate_trade_results(data, entries, direction)
                
                # Lưu kết quả
                self.test_results[symbol][timeframe_name] = {
                    "direction": direction,
                    "entries_count": len(entries),
                    "results": results
                }
                
                # Thống kê kết quả
                if len(results) > 0:
                    win_count = sum(1 for r in results if r["pnl_percent"] > 0)
                    loss_count = sum(1 for r in results if r["pnl_percent"] <= 0)
                    win_rate = 100 * win_count / len(results) if len(results) > 0 else 0
                    
                    total_pnl_percent = sum(r["pnl_percent"] for r in results)
                    avg_pnl_percent = total_pnl_percent / len(results) if len(results) > 0 else 0
                    
                    total_pnl_r = sum(r["pnl_r"] for r in results)
                    avg_pnl_r = total_pnl_r / len(results) if len(results) > 0 else 0
                    
                    logger.info(f"{symbol} - {timeframe_name} ({direction.upper()}) - {len(results)} lệnh - Win: {win_rate:.2f}% - Avg P/L: {avg_pnl_percent:.2f}% ({avg_pnl_r:.2f}R)")
                else:
                    logger.info(f"{symbol} - {timeframe_name} ({direction.upper()}) - Không có lệnh")
        
        # Lưu kết quả
        self.save_results()
    
    def save_results(self) -> None:
        """
        Lưu kết quả kiểm tra
        """
        # Tạo tên file kết quả
        result_filename = f"high_risk_entry_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_path = os.path.join(self.results_dir, result_filename)
        
        # Tổng hợp kết quả
        summary = self.generate_summary()
        
        # Chuẩn bị dữ liệu để lưu
        save_data = {
            "summary": summary,
            "detailed_results": self.test_results,
            "test_settings": self.config.get("test_settings", {}),
            "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Lưu kết quả
        try:
            with open(result_path, 'w') as f:
                json.dump(save_data, f, indent=2, default=str)
            
            logger.info(f"Đã lưu kết quả vào {result_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu kết quả: {e}")
    
    def generate_summary(self) -> Dict:
        """
        Tạo tóm tắt kết quả kiểm tra

        Returns:
            Dict: Tóm tắt kết quả
        """
        summary = {
            "overall": {
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0,
                "total_pnl_percent": 0,
                "avg_pnl_percent": 0,
                "total_pnl_r": 0,
                "avg_pnl_r": 0
            },
            "by_timeframe": {},
            "by_symbol": {},
            "by_direction": {
                "long": {
                    "total_trades": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "win_rate": 0,
                    "avg_pnl_percent": 0,
                    "avg_pnl_r": 0
                },
                "short": {
                    "total_trades": 0,
                    "win_count": 0,
                    "loss_count": 0,
                    "win_rate": 0,
                    "avg_pnl_percent": 0,
                    "avg_pnl_r": 0
                }
            },
            "best_timeframe": None,
            "best_symbol": None,
            "best_direction": None
        }
        
        # Tính toán tóm tắt cho từng khung thời gian
        for timeframe_info in self.test_timeframes:
            timeframe_name = timeframe_info["name"]
            summary["by_timeframe"][timeframe_name] = {
                "direction": timeframe_info["direction"],
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0,
                "avg_pnl_percent": 0,
                "avg_pnl_r": 0
            }
        
        # Tính toán tóm tắt cho từng cặp tiền
        for symbol in self.test_symbols:
            summary["by_symbol"][symbol] = {
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0,
                "avg_pnl_percent": 0,
                "avg_pnl_r": 0
            }
        
        # Thống kê kết quả
        for symbol, symbol_results in self.test_results.items():
            for timeframe_name, timeframe_data in symbol_results.items():
                direction = timeframe_data["direction"]
                results = timeframe_data["results"]
                
                if len(results) == 0:
                    continue
                
                # Thống kê chung
                summary["overall"]["total_trades"] += len(results)
                
                win_count = sum(1 for r in results if r["pnl_percent"] > 0)
                loss_count = sum(1 for r in results if r["pnl_percent"] <= 0)
                
                summary["overall"]["win_count"] += win_count
                summary["overall"]["loss_count"] += loss_count
                
                total_pnl_percent = sum(r["pnl_percent"] for r in results)
                summary["overall"]["total_pnl_percent"] += total_pnl_percent
                
                total_pnl_r = sum(r["pnl_r"] for r in results)
                summary["overall"]["total_pnl_r"] += total_pnl_r
                
                # Thống kê theo khung thời gian
                summary["by_timeframe"][timeframe_name]["total_trades"] += len(results)
                summary["by_timeframe"][timeframe_name]["win_count"] += win_count
                summary["by_timeframe"][timeframe_name]["loss_count"] += loss_count
                
                if summary["by_timeframe"][timeframe_name]["total_trades"] > 0:
                    summary["by_timeframe"][timeframe_name]["win_rate"] = 100 * summary["by_timeframe"][timeframe_name]["win_count"] / summary["by_timeframe"][timeframe_name]["total_trades"]
                    summary["by_timeframe"][timeframe_name]["avg_pnl_percent"] = total_pnl_percent / len(results)
                    summary["by_timeframe"][timeframe_name]["avg_pnl_r"] = total_pnl_r / len(results)
                
                # Thống kê theo cặp tiền
                summary["by_symbol"][symbol]["total_trades"] += len(results)
                summary["by_symbol"][symbol]["win_count"] += win_count
                summary["by_symbol"][symbol]["loss_count"] += loss_count
                
                if summary["by_symbol"][symbol]["total_trades"] > 0:
                    summary["by_symbol"][symbol]["win_rate"] = 100 * summary["by_symbol"][symbol]["win_count"] / summary["by_symbol"][symbol]["total_trades"]
                    summary["by_symbol"][symbol]["avg_pnl_percent"] = total_pnl_percent / len(results)
                    summary["by_symbol"][symbol]["avg_pnl_r"] = total_pnl_r / len(results)
                
                # Thống kê theo hướng giao dịch
                summary["by_direction"][direction]["total_trades"] += len(results)
                summary["by_direction"][direction]["win_count"] += win_count
                summary["by_direction"][direction]["loss_count"] += loss_count
                
                if summary["by_direction"][direction]["total_trades"] > 0:
                    summary["by_direction"][direction]["win_rate"] = 100 * summary["by_direction"][direction]["win_count"] / summary["by_direction"][direction]["total_trades"]
                    summary["by_direction"][direction]["avg_pnl_percent"] = (summary["by_direction"][direction]["avg_pnl_percent"] * (summary["by_direction"][direction]["total_trades"] - len(results)) + total_pnl_percent) / summary["by_direction"][direction]["total_trades"]
                    summary["by_direction"][direction]["avg_pnl_r"] = (summary["by_direction"][direction]["avg_pnl_r"] * (summary["by_direction"][direction]["total_trades"] - len(results)) + total_pnl_r) / summary["by_direction"][direction]["total_trades"]
        
        # Tính win rate tổng thể
        if summary["overall"]["total_trades"] > 0:
            summary["overall"]["win_rate"] = 100 * summary["overall"]["win_count"] / summary["overall"]["total_trades"]
            summary["overall"]["avg_pnl_percent"] = summary["overall"]["total_pnl_percent"] / summary["overall"]["total_trades"]
            summary["overall"]["avg_pnl_r"] = summary["overall"]["total_pnl_r"] / summary["overall"]["total_trades"]
        
        # Tìm khung thời gian tốt nhất
        best_timeframe_win_rate = 0
        for timeframe_name, timeframe_data in summary["by_timeframe"].items():
            if timeframe_data["total_trades"] >= 3 and timeframe_data["win_rate"] > best_timeframe_win_rate:
                best_timeframe_win_rate = timeframe_data["win_rate"]
                summary["best_timeframe"] = {
                    "name": timeframe_name,
                    "win_rate": timeframe_data["win_rate"],
                    "avg_pnl_percent": timeframe_data["avg_pnl_percent"],
                    "direction": timeframe_data["direction"]
                }
        
        # Tìm cặp tiền tốt nhất
        best_symbol_win_rate = 0
        for symbol, symbol_data in summary["by_symbol"].items():
            if symbol_data["total_trades"] >= 3 and symbol_data["win_rate"] > best_symbol_win_rate:
                best_symbol_win_rate = symbol_data["win_rate"]
                summary["best_symbol"] = {
                    "symbol": symbol,
                    "win_rate": symbol_data["win_rate"],
                    "avg_pnl_percent": symbol_data["avg_pnl_percent"]
                }
        
        # Tìm hướng giao dịch tốt nhất
        if summary["by_direction"]["long"]["total_trades"] >= 3 and summary["by_direction"]["short"]["total_trades"] >= 3:
            if summary["by_direction"]["long"]["win_rate"] > summary["by_direction"]["short"]["win_rate"]:
                summary["best_direction"] = {
                    "direction": "long",
                    "win_rate": summary["by_direction"]["long"]["win_rate"],
                    "avg_pnl_percent": summary["by_direction"]["long"]["avg_pnl_percent"]
                }
            else:
                summary["best_direction"] = {
                    "direction": "short",
                    "win_rate": summary["by_direction"]["short"]["win_rate"],
                    "avg_pnl_percent": summary["by_direction"]["short"]["avg_pnl_percent"]
                }
        
        return summary
    
    def print_summary(self) -> None:
        """
        In tóm tắt kết quả kiểm tra
        """
        summary = self.generate_summary()
        
        print("\n===== TÓM TẮT KẾT QUẢ KIỂM TRA ĐIỂM VÀO LỆNH RỦI RO CAO =====")
        
        print(f"\nTổng số lệnh: {summary['overall']['total_trades']}")
        print(f"Tỷ lệ thắng: {summary['overall']['win_rate']:.2f}%")
        print(f"P/L trung bình: {summary['overall']['avg_pnl_percent']:.2f}% ({summary['overall']['avg_pnl_r']:.2f}R)")
        
        print("\nTheo khung thời gian:")
        for timeframe_name, timeframe_data in summary["by_timeframe"].items():
            if timeframe_data["total_trades"] > 0:
                print(f"- {timeframe_name} ({timeframe_data['direction'].upper()}): {timeframe_data['total_trades']} lệnh - Win: {timeframe_data['win_rate']:.2f}% - Avg P/L: {timeframe_data['avg_pnl_percent']:.2f}% ({timeframe_data['avg_pnl_r']:.2f}R)")
        
        print("\nTheo cặp tiền:")
        for symbol, symbol_data in summary["by_symbol"].items():
            if symbol_data["total_trades"] > 0:
                print(f"- {symbol}: {symbol_data['total_trades']} lệnh - Win: {symbol_data['win_rate']:.2f}% - Avg P/L: {symbol_data['avg_pnl_percent']:.2f}% ({symbol_data['avg_pnl_r']:.2f}R)")
        
        print("\nTheo hướng giao dịch:")
        for direction, direction_data in summary["by_direction"].items():
            if direction_data["total_trades"] > 0:
                print(f"- {direction.upper()}: {direction_data['total_trades']} lệnh - Win: {direction_data['win_rate']:.2f}% - Avg P/L: {direction_data['avg_pnl_percent']:.2f}% ({direction_data['avg_pnl_r']:.2f}R)")
        
        print("\nKết quả tốt nhất:")
        if summary["best_timeframe"]:
            print(f"- Khung thời gian tốt nhất: {summary['best_timeframe']['name']} ({summary['best_timeframe']['direction'].upper()}) - Win: {summary['best_timeframe']['win_rate']:.2f}% - Avg P/L: {summary['best_timeframe']['avg_pnl_percent']:.2f}%")
        if summary["best_symbol"]:
            print(f"- Cặp tiền tốt nhất: {summary['best_symbol']['symbol']} - Win: {summary['best_symbol']['win_rate']:.2f}% - Avg P/L: {summary['best_symbol']['avg_pnl_percent']:.2f}%")
        if summary["best_direction"]:
            print(f"- Hướng giao dịch tốt nhất: {summary['best_direction']['direction'].upper()} - Win: {summary['best_direction']['win_rate']:.2f}% - Avg P/L: {summary['best_direction']['avg_pnl_percent']:.2f}%")
        
        # Hiển thị kết luận
        print("\nKết luận:")
        if summary["overall"]["win_rate"] > 70:
            print("✅ Chiến lược này có tỷ lệ thắng rất cao và đáng để áp dụng.")
        elif summary["overall"]["win_rate"] > 60:
            print("✅ Chiến lược này có tỷ lệ thắng khá tốt và có thể áp dụng với quản lý vốn cẩn thận.")
        elif summary["overall"]["win_rate"] > 50:
            print("⚠️ Chiến lược này có tỷ lệ thắng trung bình, cần cải thiện các điều kiện vào lệnh.")
        else:
            print("❌ Chiến lược này có tỷ lệ thắng thấp, không nên áp dụng trong thực tế.")
        
        # Tư vấn cải thiện
        print("\nĐề xuất cải thiện:")
        
        # Khung thời gian tốt nhất
        if summary["best_timeframe"] and summary["best_timeframe"]["win_rate"] > 80:
            print(f"- Tập trung vào giao dịch trong khung thời gian {summary['best_timeframe']['name']} với lệnh {summary['best_timeframe']['direction'].upper()}.")
        
        # Cặp tiền tốt nhất
        if summary["best_symbol"] and summary["best_symbol"]["win_rate"] > 80:
            print(f"- Ưu tiên giao dịch cặp tiền {summary['best_symbol']['symbol']} để có tỷ lệ thắng cao nhất.")
        
        # Hướng giao dịch tốt nhất
        if summary["best_direction"] and summary["best_direction"]["win_rate"] > 80:
            print(f"- Ưu tiên giao dịch theo hướng {summary['best_direction']['direction'].upper()} vì có tỷ lệ thắng cao hơn.")
        
        # Gợi ý thêm
        if summary["overall"]["avg_pnl_r"] < 1:
            print("- Cần cải thiện tỷ lệ R:R hoặc trailing stop để tăng lợi nhuận trung bình.")
        
        if summary["overall"]["win_rate"] < 60:
            print("- Thêm các bộ lọc chất lượng để tăng tỷ lệ thắng, ví dụ: lọc theo vùng hỗ trợ/kháng cự hoặc khối lượng giao dịch.")

def setup_environment():
    """
    Thiết lập môi trường làm việc
    """
    # Tạo các thư mục cần thiết
    os.makedirs("configs", exist_ok=True)
    os.makedirs("test_data", exist_ok=True)
    os.makedirs("high_risk_results", exist_ok=True)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Hệ thống kiểm tra điểm vào lệnh rủi ro cao')
    parser.add_argument('--config', type=str, default='configs/high_risk_entry_config.json', help='Đường dẫn đến file cấu hình')
    parser.add_argument('--strategy-config', type=str, default='configs/time_optimized_strategy_config.json', help='Đường dẫn đến file cấu hình chiến lược')
    parser.add_argument('--data-dir', type=str, default='test_data', help='Thư mục chứa dữ liệu kiểm tra')
    parser.add_argument('--results-dir', type=str, default='high_risk_results', help='Thư mục chứa kết quả kiểm tra')
    parser.add_argument('--reset', action='store_true', help='Reset cấu hình về mặc định')
    parser.add_argument('--symbols', type=str, help='Danh sách cặp tiền cần kiểm tra, phân cách bởi dấu phẩy')
    parser.add_argument('--days', type=int, default=30, help='Số ngày dữ liệu cần kiểm tra')
    args = parser.parse_args()
    
    # Thiết lập môi trường
    setup_environment()
    
    # Nếu yêu cầu reset cấu hình
    if args.reset and os.path.exists(args.config):
        os.remove(args.config)
        logger.info(f"Đã xóa file cấu hình {args.config}")
    
    # Khởi tạo hệ thống kiểm tra
    tester = HighRiskEntryTester(
        config_path=args.config,
        strategy_config_path=args.strategy_config,
        test_data_dir=args.data_dir,
        results_dir=args.results_dir
    )
    
    # Cập nhật cấu hình nếu có
    if args.symbols:
        symbols = args.symbols.split(',')
        tester.config["test_symbols"] = symbols
        tester._save_config()
    
    if args.days:
        tester.config["test_settings"]["days_to_test"] = args.days
        tester._save_config()
    
    # Hiển thị thông tin
    print("\n===== HỆ THỐNG KIỂM TRA ĐIỂM VÀO LỆNH RỦI RO CAO =====")
    print(f"- Các cặp tiền kiểm tra: {', '.join(tester.test_symbols)}")
    print(f"- Số ngày dữ liệu: {tester.config['test_settings']['days_to_test']}")
    print(f"- Tỷ lệ R:R: {tester.config['test_settings']['risk_reward_ratio']}")
    print(f"- Stop Loss: {tester.config['test_settings']['stop_loss_percent']}%")
    print(f"- Take Profit: {tester.config['test_settings']['take_profit_percent']}%")
    
    print("\nCác khung thời gian kiểm tra:")
    for tf in tester.test_timeframes:
        print(f"- {tf['name']} ({tf['start_hour']:02d}:{tf['start_minute']:02d}-{tf['end_hour']:02d}:{tf['end_minute']:02d}) - {tf['direction'].upper()}")
    
    print("\nCác chỉ báo kiểm tra:")
    for ind in tester.test_indicators:
        print(f"- {ind['name']} {ind['condition']} ({ind['timeframe']}) - Cho lệnh {ind['for_direction'].upper()}")
    
    print("\nĐang chạy kiểm tra...")
    
    # Chạy kiểm tra
    tester.run_tests()
    
    # In tóm tắt kết quả
    tester.print_summary()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng kiểm tra!")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {e}", exc_info=True)
        sys.exit(1)