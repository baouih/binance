#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module quản lý rủi ro thích ứng

Module này điều chỉnh mức rủi ro dựa vào điều kiện thị trường hiện tại,
phân tích xu hướng, và các thông số biến động để tối ưu hóa tỉ lệ lợi nhuận/rủi ro.
"""

import os
import sys
import json
import logging
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import time

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('adaptive_risk_allocator.log')
    ]
)

logger = logging.getLogger('adaptive_risk_allocator')

# Thư mục lưu trữ cấu hình
CONFIG_DIR = './'
RISK_CONFIG_FILE = os.path.join(CONFIG_DIR, 'bot_config.json')


class AdaptiveRiskAllocator:
    """
    Quản lý và điều chỉnh mức độ rủi ro dựa trên các điều kiện thị trường
    
    Attributes:
        config (dict): Cấu hình rủi ro và thị trường
        default_risk (float): Mức rủi ro mặc định
        min_risk (float): Mức rủi ro tối thiểu
        max_risk (float): Mức rủi ro tối đa
        adaptive_risk (bool): Bật/tắt chức năng rủi ro thích ứng
        market_condition_risk (dict): Mức rủi ro cho từng điều kiện thị trường
    """
    
    def __init__(self, config_file=RISK_CONFIG_FILE):
        """
        Khởi tạo quản lý rủi ro thích ứng
        
        Args:
            config_file (str): Đường dẫn tới file cấu hình
        """
        try:
            self.load_config(config_file)
            logger.info(f"Đã khởi tạo AdaptiveRiskAllocator với mức rủi ro mặc định: {self.default_risk}")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo AdaptiveRiskAllocator: {str(e)}")
            # Thiết lập giá trị mặc định nếu không đọc được cấu hình
            self.default_risk = 0.02
            self.min_risk = 0.01
            self.max_risk = 0.04
            self.adaptive_risk = True
            self.market_condition_risk = {
                "uptrend": 0.03,
                "downtrend": 0.02,
                "sideway": 0.02,
                "volatile": 0.025,
                "crash": 0.01,
                "pump": 0.035
            }
    
    def load_config(self, config_file):
        """
        Đọc cấu hình từ file
        
        Args:
            config_file (str): Đường dẫn tới file cấu hình
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Đọc các tham số cấu hình
            self.config = config
            self.default_risk = config.get('risk_level', 0.025)
            self.min_risk = config.get('min_risk', 0.01)
            self.max_risk = config.get('max_risk', 0.04)
            self.adaptive_risk = config.get('adaptive_risk', True)
            self.market_condition_risk = config.get('market_condition_risk', {
                "uptrend": 0.03,
                "downtrend": 0.02,
                "sideway": 0.02,
                "volatile": 0.025,
                "crash": 0.01,
                "pump": 0.035
            })
            
            logger.info(f"Đã đọc cấu hình từ {config_file}")
        except Exception as e:
            logger.error(f"Lỗi khi đọc file cấu hình {config_file}: {str(e)}")
            raise
    
    def save_config(self, config_file=RISK_CONFIG_FILE):
        """
        Lưu cấu hình hiện tại vào file
        
        Args:
            config_file (str): Đường dẫn tới file cấu hình
        """
        try:
            config = {
                'risk_level': self.default_risk,
                'min_risk': self.min_risk,
                'max_risk': self.max_risk,
                'adaptive_risk': self.adaptive_risk,
                'market_condition_risk': self.market_condition_risk
            }
            
            # Cập nhật bất kỳ cấu hình khác nếu có
            if hasattr(self, 'config') and isinstance(self.config, dict):
                for key, value in self.config.items():
                    if key not in config:
                        config[key] = value
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã lưu cấu hình vào {config_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu file cấu hình {config_file}: {str(e)}")
    
    def get_risk_for_market_condition(self, market_condition):
        """
        Lấy mức rủi ro phù hợp cho một điều kiện thị trường cụ thể
        
        Args:
            market_condition (str): Điều kiện thị trường ('uptrend', 'downtrend', 'sideway', 'volatile', 'crash', 'pump')
            
        Returns:
            float: Mức rủi ro phù hợp
        """
        if not self.adaptive_risk:
            return self.default_risk
        
        risk = self.market_condition_risk.get(market_condition, self.default_risk)
        
        # Đảm bảo rủi ro nằm trong khoảng cho phép
        risk = max(min(risk, self.max_risk), self.min_risk)
        
        logger.info(f"Mức rủi ro cho điều kiện thị trường '{market_condition}': {risk}")
        return risk
    
    def analyze_market_condition(self, price_data, volume_data=None, timeframe='1h'):
        """
        Phân tích điều kiện thị trường dựa trên dữ liệu giá
        
        Args:
            price_data (pandas.DataFrame): Dữ liệu giá
            volume_data (pandas.DataFrame, optional): Dữ liệu khối lượng
            timeframe (str): Khung thời gian
            
        Returns:
            str: Điều kiện thị trường ('uptrend', 'downtrend', 'sideway', 'volatile', 'crash', 'pump')
        """
        try:
            # Đảm bảo price_data là DataFrame hoặc Series
            if not isinstance(price_data, (pd.DataFrame, pd.Series)):
                if isinstance(price_data, list) or isinstance(price_data, np.ndarray):
                    price_data = pd.Series(price_data)
                else:
                    raise ValueError("price_data phải là pandas DataFrame, Series, list hoặc numpy array")
            
            # Tính toán các chỉ số thị trường
            # 1. Xu hướng: sử dụng SMA
            if isinstance(price_data, pd.DataFrame) and 'close' in price_data.columns:
                close_prices = price_data['close']
            else:
                close_prices = price_data
            
            # SMA ngắn và dài
            short_period = 20
            long_period = 50
            
            if len(close_prices) < long_period:
                logger.warning(f"Không đủ dữ liệu cho SMA {long_period}, chỉ có {len(close_prices)} dữ liệu")
                # Điều chỉnh chu kỳ nếu không đủ dữ liệu
                short_period = min(short_period, len(close_prices) // 3)
                long_period = min(long_period, len(close_prices) // 2)
            
            short_sma = close_prices.rolling(window=short_period).mean()
            long_sma = close_prices.rolling(window=long_period).mean()
            
            # 2. Biến động: tính theo ATR
            if isinstance(price_data, pd.DataFrame) and 'high' in price_data.columns and 'low' in price_data.columns:
                # Tính ATR
                high = price_data['high']
                low = price_data['low']
                close = price_data['close']
                
                # Tính True Range
                tr1 = high - low
                tr2 = abs(high - close.shift())
                tr3 = abs(low - close.shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()
                
                # Tính biến động theo phần trăm so với giá
                volatility = (atr / close) * 100
                current_volatility = volatility.iloc[-1]
            else:
                # Sử dụng độ lệch chuẩn nếu không có dữ liệu high/low
                volatility = close_prices.pct_change().rolling(window=14).std() * 100
                current_volatility = volatility.iloc[-1]
            
            # 3. Phân tích xu hướng
            current_short_sma = short_sma.iloc[-1]
            current_long_sma = long_sma.iloc[-1]
            price_change_1d = (close_prices.iloc[-1] / close_prices.iloc[-min(24, len(close_prices))]) - 1
            
            # Định nghĩa ngưỡng
            uptrend_threshold = 0.01  # 1%
            strong_uptrend_threshold = 0.04  # 4%
            downtrend_threshold = -0.01  # -1%
            strong_downtrend_threshold = -0.04  # -4%
            sideway_threshold = 0.005  # 0.5%
            high_volatility_threshold = 2.5  # 2.5%
            very_high_volatility_threshold = 5.0  # 5%
            
            # Xác định điều kiện thị trường
            market_condition = 'sideway'  # mặc định
            
            if price_change_1d > strong_uptrend_threshold and current_volatility > very_high_volatility_threshold:
                market_condition = 'pump'
            elif price_change_1d < strong_downtrend_threshold and current_volatility > very_high_volatility_threshold:
                market_condition = 'crash'
            elif current_volatility > high_volatility_threshold:
                market_condition = 'volatile'
            elif current_short_sma > current_long_sma and price_change_1d > uptrend_threshold:
                market_condition = 'uptrend'
            elif current_short_sma < current_long_sma and price_change_1d < downtrend_threshold:
                market_condition = 'downtrend'
            elif abs(price_change_1d) <= sideway_threshold:
                market_condition = 'sideway'
            
            logger.info(f"Phân tích thị trường: {market_condition} (Biến động: {current_volatility:.2f}%, Thay đổi giá: {price_change_1d*100:.2f}%)")
            return market_condition
        
        except Exception as e:
            logger.error(f"Lỗi phân tích điều kiện thị trường: {str(e)}")
            return 'sideway'  # trả về giá trị mặc định an toàn
    
    def calculate_position_risk(self, market_condition, symbol=None, timeframe=None, account_balance=None):
        """
        Tính toán mức rủi ro cho một vị thế giao dịch cụ thể
        
        Args:
            market_condition (str): Điều kiện thị trường
            symbol (str, optional): Cặp tiền giao dịch
            timeframe (str, optional): Khung thời gian
            account_balance (float, optional): Số dư tài khoản
            
        Returns:
            float: Mức rủi ro cho vị thế
        """
        # Lấy mức rủi ro cơ bản theo điều kiện thị trường
        base_risk = self.get_risk_for_market_condition(market_condition)
        
        # Điều chỉnh theo cặp tiền nếu cần
        symbol_risk_adjustment = 0.0
        if symbol:
            # Ví dụ: giảm rủi ro cho altcoin có thanh khoản thấp
            major_coins = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            if symbol not in major_coins:
                symbol_risk_adjustment = -0.005  # giảm 0.5%
        
        # Điều chỉnh theo khung thời gian nếu cần
        timeframe_risk_adjustment = 0.0
        if timeframe:
            # Ví dụ: tăng rủi ro cho khung thời gian dài hơn
            if timeframe == '4h':
                timeframe_risk_adjustment = 0.005  # tăng 0.5%
            elif timeframe == '1d':
                timeframe_risk_adjustment = 0.01  # tăng 1%
            elif timeframe == '15m':
                timeframe_risk_adjustment = -0.005  # giảm 0.5%
        
        # Tính toán rủi ro cuối cùng
        final_risk = base_risk + symbol_risk_adjustment + timeframe_risk_adjustment
        
        # Đảm bảo nằm trong giới hạn
        final_risk = max(min(final_risk, self.max_risk), self.min_risk)
        
        logger.info(f"Rủi ro cuối cùng cho {symbol} ({timeframe}, {market_condition}): {final_risk}")
        return final_risk
    
    def update_risk_config(self, new_risk_config):
        """
        Cập nhật cấu hình rủi ro
        
        Args:
            new_risk_config (dict): Cấu hình rủi ro mới
        """
        try:
            if 'risk_level' in new_risk_config:
                self.default_risk = new_risk_config['risk_level']
            
            if 'min_risk' in new_risk_config:
                self.min_risk = new_risk_config['min_risk']
            
            if 'max_risk' in new_risk_config:
                self.max_risk = new_risk_config['max_risk']
            
            if 'adaptive_risk' in new_risk_config:
                self.adaptive_risk = new_risk_config['adaptive_risk']
            
            if 'market_condition_risk' in new_risk_config:
                self.market_condition_risk.update(new_risk_config['market_condition_risk'])
            
            # Lưu cấu hình mới
            self.save_config()
            logger.info(f"Đã cập nhật cấu hình rủi ro: {new_risk_config}")
        except Exception as e:
            logger.error(f"Lỗi cập nhật cấu hình rủi ro: {str(e)}")


def create_default_config():
    """
    Tạo file cấu hình mặc định nếu chưa tồn tại
    """
    if not os.path.exists(RISK_CONFIG_FILE):
        default_config = {
            "risk_level": 0.025,
            "adaptive_risk": True,
            "market_condition_risk": {
                "uptrend": 0.03,
                "downtrend": 0.02,
                "sideway": 0.02,
                "volatile": 0.025,
                "crash": 0.01,
                "pump": 0.035
            },
            "max_risk": 0.04,
            "min_risk": 0.01
        }
        
        with open(RISK_CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Đã tạo file cấu hình mặc định: {RISK_CONFIG_FILE}")


def test_risk_allocator():
    """
    Hàm kiểm thử quản lý rủi ro thích ứng
    """
    # Tạo dữ liệu giá mẫu
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    
    # Tạo dữ liệu mô phỏng uptrend
    uptrend_prices = pd.DataFrame({
        'open': np.linspace(100, 120, 100) + np.random.normal(0, 1, 100),
        'high': np.linspace(101, 122, 100) + np.random.normal(0, 1.5, 100),
        'low': np.linspace(99, 118, 100) + np.random.normal(0, 1.5, 100),
        'close': np.linspace(100, 120, 100) + np.random.normal(0, 1, 100),
    }, index=dates)
    
    # Tạo dữ liệu mô phỏng downtrend
    downtrend_prices = pd.DataFrame({
        'open': np.linspace(120, 100, 100) + np.random.normal(0, 1, 100),
        'high': np.linspace(122, 101, 100) + np.random.normal(0, 1.5, 100),
        'low': np.linspace(118, 99, 100) + np.random.normal(0, 1.5, 100),
        'close': np.linspace(120, 100, 100) + np.random.normal(0, 1, 100),
    }, index=dates)
    
    # Tạo dữ liệu mô phỏng sideway
    sideway_prices = pd.DataFrame({
        'open': 100 + np.random.normal(0, 1, 100),
        'high': 102 + np.random.normal(0, 1.5, 100),
        'low': 98 + np.random.normal(0, 1.5, 100),
        'close': 100 + np.random.normal(0, 1, 100),
    }, index=dates)
    
    # Tạo dữ liệu mô phỏng volatile
    volatile_prices = pd.DataFrame({
        'open': 100 + np.random.normal(0, 5, 100),
        'high': 105 + np.random.normal(0, 5, 100),
        'low': 95 + np.random.normal(0, 5, 100),
        'close': 100 + np.random.normal(0, 5, 100),
    }, index=dates)
    
    # Tạo dữ liệu mô phỏng crash
    crash_base = np.linspace(100, 70, 100)
    crash_prices = pd.DataFrame({
        'open': crash_base + np.random.normal(0, 3, 100),
        'high': crash_base + 3 + np.random.normal(0, 3, 100),
        'low': crash_base - 3 + np.random.normal(0, 3, 100),
        'close': crash_base + np.random.normal(0, 3, 100),
    }, index=dates)
    
    # Tạo dữ liệu mô phỏng pump
    pump_base = np.linspace(100, 150, 100)
    pump_prices = pd.DataFrame({
        'open': pump_base + np.random.normal(0, 3, 100),
        'high': pump_base + 3 + np.random.normal(0, 3, 100),
        'low': pump_base - 3 + np.random.normal(0, 3, 100),
        'close': pump_base + np.random.normal(0, 3, 100),
    }, index=dates)
    
    # Tạo đối tượng quản lý rủi ro
    create_default_config()
    risk_allocator = AdaptiveRiskAllocator()
    
    # Kiểm thử phân tích điều kiện thị trường
    print("=== Kiểm thử phân tích điều kiện thị trường ===")
    print(f"Uptrend: {risk_allocator.analyze_market_condition(uptrend_prices)}")
    print(f"Downtrend: {risk_allocator.analyze_market_condition(downtrend_prices)}")
    print(f"Sideway: {risk_allocator.analyze_market_condition(sideway_prices)}")
    print(f"Volatile: {risk_allocator.analyze_market_condition(volatile_prices)}")
    print(f"Crash: {risk_allocator.analyze_market_condition(crash_prices)}")
    print(f"Pump: {risk_allocator.analyze_market_condition(pump_prices)}")
    
    # Kiểm thử tính toán rủi ro
    print("\n=== Kiểm thử tính toán rủi ro ===")
    for market_condition in ['uptrend', 'downtrend', 'sideway', 'volatile', 'crash', 'pump']:
        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'SHIBUSDT']:
            for timeframe in ['15m', '1h', '4h', '1d']:
                risk = risk_allocator.calculate_position_risk(
                    market_condition, symbol, timeframe
                )
                print(f"{market_condition}, {symbol}, {timeframe}: {risk}")


if __name__ == "__main__":
    # Tạo cấu hình mặc định nếu chưa tồn tại
    create_default_config()
    
    # Chạy các kiểm thử
    test_risk_allocator()