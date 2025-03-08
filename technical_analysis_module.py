#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
import ccxt
import talib
import requests
from binance.client import Client
import json
import time

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('technical_analysis')

class TechnicalAnalysisModule:
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        """Khởi tạo module phân tích kỹ thuật"""
        self.testnet = testnet
        
        # Sử dụng API key nếu được cung cấp, nếu không thì lấy từ biến môi trường
        self.api_key = api_key or os.environ.get('BINANCE_TESTNET_API_KEY') if testnet else os.environ.get('BINANCE_API_KEY')
        self.api_secret = api_secret or os.environ.get('BINANCE_TESTNET_API_SECRET') if testnet else os.environ.get('BINANCE_API_SECRET')
        
        # Thiết lập client Binance dựa trên môi trường
        if testnet:
            self.client = Client(self.api_key, self.api_secret, testnet=True)
            logger.info("Khởi tạo kết nối đến Binance Testnet")
        else:
            self.client = Client(self.api_key, self.api_secret)
            logger.info("Khởi tạo kết nối đến Binance Live")
        
        # Khởi tạo binance ccxt
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True
            }
        })
        
        if testnet:
            self.exchange.urls['api'] = {
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
            }
        
        # Cache dữ liệu để tránh gọi API quá nhiều
        self.ohlcv_cache = {}
        self.support_resistance_cache = {}
        
    def get_historical_data(self, symbol, timeframe='1h', limit=500):
        """Lấy dữ liệu lịch sử cho một cặp tiền và timeframe cụ thể"""
        cache_key = f"{symbol}_{timeframe}_{limit}"
        
        # Kiểm tra cache trước, nếu dữ liệu được lấy trong 5 phút trước, sử dụng cache
        current_time = time.time()
        if cache_key in self.ohlcv_cache and (current_time - self.ohlcv_cache[cache_key]['timestamp']) < 300:
            logger.info(f"Sử dụng dữ liệu cache cho {symbol} {timeframe}")
            return self.ohlcv_cache[cache_key]['data']
        
        try:
            # Sử dụng ccxt để lấy dữ liệu OHLCV
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Lưu vào cache
            self.ohlcv_cache[cache_key] = {
                'data': df,
                'timestamp': current_time
            }
            
            logger.info(f"Đã lấy dữ liệu lịch sử cho {symbol} {timeframe}, {len(df)} nến")
            return df
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {str(e)}")
            return None
    
    def find_support_resistance(self, symbol, timeframe='1h', window=20, strong_levels=3):
        """Tìm các mức hỗ trợ và kháng cự quan trọng
        Args:
            symbol: Cặp tiền cần phân tích
            timeframe: Khung thời gian
            window: Cửa sổ để tìm swing highs/lows
            strong_levels: Số lượng mức giá mạnh nhất để trả về
        Returns:
            Các mức hỗ trợ và kháng cự
        """
        cache_key = f"{symbol}_{timeframe}_sr"
        
        # Kiểm tra cache trước, nếu dữ liệu được lấy trong 30 phút trước, sử dụng cache
        current_time = time.time()
        if cache_key in self.support_resistance_cache and (current_time - self.support_resistance_cache[cache_key]['timestamp']) < 1800:
            logger.info(f"Sử dụng dữ liệu cache cho SR levels {symbol} {timeframe}")
            return self.support_resistance_cache[cache_key]['data']
        
        # Lấy dữ liệu lịch sử
        df = self.get_historical_data(symbol, timeframe, limit=500)
        if df is None:
            return None
        
        # Tìm các swing highs (kháng cự) và swing lows (hỗ trợ)
        highs = []
        lows = []
        
        for i in range(window, len(df) - window):
            # Kiểm tra swing high
            if all(df['high'].iloc[i] > df['high'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['high'].iloc[i] > df['high'].iloc[i+j] for j in range(1, window+1)):
                highs.append(df['high'].iloc[i])
            
            # Kiểm tra swing low
            if all(df['low'].iloc[i] < df['low'].iloc[i-j] for j in range(1, window+1)) and \
               all(df['low'].iloc[i] < df['low'].iloc[i+j] for j in range(1, window+1)):
                lows.append(df['low'].iloc[i])
        
        # Nhóm các mức giá gần nhau để tìm các vùng giá quan trọng
        def group_levels(levels, threshold_percent=0.5):
            if not levels:
                return []
            
            levels = sorted(levels)
            grouped = []
            current_group = [levels[0]]
            
            for level in levels[1:]:
                # Nếu mức giá hiện tại gần với mức giá cuối cùng trong nhóm hiện tại
                if abs(level - current_group[-1]) / current_group[-1] * 100 < threshold_percent:
                    current_group.append(level)
                else:
                    # Tính giá trị trung bình của nhóm hiện tại và bắt đầu nhóm mới
                    grouped.append(sum(current_group) / len(current_group))
                    current_group = [level]
            
            # Thêm nhóm cuối cùng
            if current_group:
                grouped.append(sum(current_group) / len(current_group))
            
            return grouped
        
        # Nhóm các mức giá
        resistance_levels = group_levels(highs)
        support_levels = group_levels(lows)
        
        # Lấy các mức mạnh nhất (dựa trên khoảng cách với giá hiện tại)
        current_price = df['close'].iloc[-1]
        
        # Sắp xếp các mức kháng cự theo khoảng cách (chỉ những mức trên giá hiện tại)
        resistances_above = [r for r in resistance_levels if r > current_price]
        resistances_above.sort(key=lambda x: abs(x - current_price))
        
        # Sắp xếp các mức hỗ trợ theo khoảng cách (chỉ những mức dưới giá hiện tại)
        supports_below = [s for s in support_levels if s < current_price]
        supports_below.sort(key=lambda x: abs(x - current_price))
        
        # Lấy số lượng mức giá mạnh nhất
        strong_resistances = resistances_above[:strong_levels] if resistances_above else []
        strong_supports = supports_below[:strong_levels] if supports_below else []
        
        result = {
            'current_price': current_price,
            'resistance_levels': strong_resistances,
            'support_levels': strong_supports
        }
        
        # Lưu vào cache
        self.support_resistance_cache[cache_key] = {
            'data': result,
            'timestamp': current_time
        }
        
        logger.info(f"Đã tìm thấy {len(strong_resistances)} mức kháng cự và {len(strong_supports)} mức hỗ trợ cho {symbol}")
        return result
    
    def calculate_optimal_stop_loss(self, symbol, timeframe='1h', risk_percent=1):
        """Tính toán mức stop loss tối ưu dựa trên phân tích kỹ thuật
        
        Args:
            symbol: Cặp tiền cần phân tích
            timeframe: Khung thời gian
            risk_percent: Phần trăm rủi ro tối đa nếu không tìm thấy mức hỗ trợ phù hợp
            
        Returns:
            Mức stop loss và % giảm so với giá hiện tại
        """
        # Lấy các mức hỗ trợ và kháng cự
        sr_levels = self.find_support_resistance(symbol, timeframe)
        if sr_levels is None or not sr_levels['support_levels']:
            # Nếu không tìm thấy mức hỗ trợ, sử dụng % mặc định
            current_price = self.get_current_price(symbol)
            if current_price is None:
                logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
                return None
            
            sl_price = current_price * (1 - risk_percent / 100)
            sl_percent = risk_percent
            logger.info(f"Không tìm thấy mức hỗ trợ phù hợp, sử dụng stop loss mặc định {risk_percent}% cho {symbol}")
        else:
            # Sử dụng mức hỗ trợ gần nhất làm mức stop loss
            current_price = sr_levels['current_price']
            
            # Lọc ra các mức hỗ trợ không quá xa
            valid_supports = [s for s in sr_levels['support_levels'] if (current_price - s) / current_price * 100 <= 5]
            
            if valid_supports:
                # Lấy mức hỗ trợ gần nhất
                sl_price = max(valid_supports)
                sl_percent = (current_price - sl_price) / current_price * 100
                logger.info(f"Sử dụng mức hỗ trợ {sl_price} làm stop loss cho {symbol}, khoảng cách {sl_percent:.2f}%")
            else:
                # Nếu tất cả các mức hỗ trợ đều quá xa, sử dụng % mặc định
                sl_price = current_price * (1 - risk_percent / 100)
                sl_percent = risk_percent
                logger.info(f"Các mức hỗ trợ quá xa, sử dụng stop loss mặc định {risk_percent}% cho {symbol}")
        
        return {
            'price': sl_price,
            'percent': sl_percent
        }
    
    def calculate_optimal_take_profit(self, symbol, timeframe='1h', default_profit_percent=1.5):
        """Tính toán mức take profit tối ưu dựa trên phân tích kỹ thuật
        
        Args:
            symbol: Cặp tiền cần phân tích
            timeframe: Khung thời gian
            default_profit_percent: Phần trăm lợi nhuận mặc định nếu không tìm thấy mức kháng cự phù hợp
            
        Returns:
            Mức take profit và % tăng so với giá hiện tại
        """
        # Lấy các mức hỗ trợ và kháng cự
        sr_levels = self.find_support_resistance(symbol, timeframe)
        if sr_levels is None or not sr_levels['resistance_levels']:
            # Nếu không tìm thấy mức kháng cự, sử dụng % mặc định
            current_price = self.get_current_price(symbol)
            if current_price is None:
                logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
                return None
            
            tp_price = current_price * (1 + default_profit_percent / 100)
            tp_percent = default_profit_percent
            logger.info(f"Không tìm thấy mức kháng cự phù hợp, sử dụng take profit mặc định {default_profit_percent}% cho {symbol}")
        else:
            # Sử dụng mức kháng cự gần nhất làm mức take profit
            current_price = sr_levels['current_price']
            
            # Lọc ra các mức kháng cự không quá xa
            valid_resistances = [r for r in sr_levels['resistance_levels'] if (r - current_price) / current_price * 100 <= 7.5]
            
            if valid_resistances:
                # Lấy mức kháng cự gần nhất
                tp_price = min(valid_resistances)
                tp_percent = (tp_price - current_price) / current_price * 100
                logger.info(f"Sử dụng mức kháng cự {tp_price} làm take profit cho {symbol}, khoảng cách {tp_percent:.2f}%")
            else:
                # Nếu tất cả các mức kháng cự đều quá xa, sử dụng % mặc định
                tp_price = current_price * (1 + default_profit_percent / 100)
                tp_percent = default_profit_percent
                logger.info(f"Các mức kháng cự quá xa, sử dụng take profit mặc định {default_profit_percent}% cho {symbol}")
        
        return {
            'price': tp_price,
            'percent': tp_percent
        }
    
    def get_current_price(self, symbol):
        """Lấy giá hiện tại cho một cặp tiền"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá hiện tại cho {symbol}: {str(e)}")
            return None
    
    def adjust_for_leverage(self, sl_percent, tp_percent, leverage):
        """Điều chỉnh % stop loss và take profit dựa trên đòn bẩy
        
        Args:
            sl_percent: Phần trăm stop loss
            tp_percent: Phần trăm take profit
            leverage: Đòn bẩy
            
        Returns:
            % stop loss và take profit đã điều chỉnh
        """
        # Phần trăm risk/reward thực tế sau khi tính đòn bẩy
        actual_sl_percent = sl_percent * leverage
        actual_tp_percent = tp_percent * leverage
        
        # Điều chỉnh % để có được actual % mong muốn
        adjusted_sl_percent = sl_percent / leverage
        adjusted_tp_percent = tp_percent / leverage
        
        logger.info(f"Điều chỉnh stop loss từ {sl_percent:.2f}% thành {adjusted_sl_percent:.2f}% với đòn bẩy {leverage}x (thực tế {actual_sl_percent:.2f}%)")
        logger.info(f"Điều chỉnh take profit từ {tp_percent:.2f}% thành {adjusted_tp_percent:.2f}% với đòn bẩy {leverage}x (thực tế {actual_tp_percent:.2f}%)")
        
        return {
            'adjusted_sl_percent': adjusted_sl_percent,
            'adjusted_tp_percent': adjusted_tp_percent,
            'actual_sl_percent': sl_percent,
            'actual_tp_percent': tp_percent
        }
    
    def get_trading_recommendation(self, symbol, timeframe='1h', leverage=5, risk_percent=5, reward_percent=7.5):
        """Lấy khuyến nghị giao dịch cho một cặp tiền
        
        Args:
            symbol: Cặp tiền cần phân tích
            timeframe: Khung thời gian
            leverage: Đòn bẩy
            risk_percent: % rủi ro mục tiêu sau khi tính đòn bẩy
            reward_percent: % lợi nhuận mục tiêu sau khi tính đòn bẩy
            
        Returns:
            Khuyến nghị giao dịch với các mức stop loss và take profit tối ưu
        """
        # Điều chỉnh % theo đòn bẩy
        target_sl_percent = risk_percent / leverage
        target_tp_percent = reward_percent / leverage
        
        # Lấy mức stop loss và take profit tối ưu
        sl_info = self.calculate_optimal_stop_loss(symbol, timeframe, risk_percent=target_sl_percent)
        tp_info = self.calculate_optimal_take_profit(symbol, timeframe, default_profit_percent=target_tp_percent)
        
        if sl_info is None or tp_info is None:
            logger.error(f"Không thể tính toán mức stop loss hoặc take profit cho {symbol}")
            return None
        
        # Lấy giá hiện tại
        current_price = self.get_current_price(symbol)
        if current_price is None:
            logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
            return None
        
        # Tính toán tỷ lệ risk/reward
        risk = (current_price - sl_info['price']) / current_price * 100
        reward = (tp_info['price'] - current_price) / current_price * 100
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Điều chỉnh các giá trị phần trăm dựa trên đòn bẩy
        leverage_adjustment = self.adjust_for_leverage(sl_info['percent'], tp_info['percent'], leverage)
        
        result = {
            'symbol': symbol,
            'current_price': current_price,
            'stop_loss': {
                'price': sl_info['price'],
                'percent': sl_info['percent'],
                'adjusted_percent': leverage_adjustment['adjusted_sl_percent']
            },
            'take_profit': {
                'price': tp_info['price'],
                'percent': tp_info['percent'],
                'adjusted_percent': leverage_adjustment['adjusted_tp_percent']
            },
            'risk_reward_ratio': risk_reward_ratio,
            'leverage': leverage,
            'actual_risk_percent': leverage_adjustment['actual_sl_percent'],
            'actual_reward_percent': leverage_adjustment['actual_tp_percent']
        }
        
        logger.info(f"Khuyến nghị giao dịch cho {symbol}:")
        logger.info(f"  - Giá hiện tại: {current_price}")
        logger.info(f"  - Stop Loss: {sl_info['price']} ({sl_info['percent']:.2f}%, sau đòn bẩy: {leverage_adjustment['actual_sl_percent']:.2f}%)")
        logger.info(f"  - Take Profit: {tp_info['price']} ({tp_info['percent']:.2f}%, sau đòn bẩy: {leverage_adjustment['actual_tp_percent']:.2f}%)")
        logger.info(f"  - Tỷ lệ R:R: 1:{risk_reward_ratio:.2f}")
        
        return result

def test_module():
    """Hàm test module phân tích kỹ thuật"""
    ta = TechnicalAnalysisModule(testnet=True)
    
    # Test lấy dữ liệu lịch sử
    symbol = "BTCUSDT"
    logger.info(f"Test lấy dữ liệu lịch sử cho {symbol}")
    df = ta.get_historical_data(symbol, timeframe='1h', limit=100)
    if df is not None:
        logger.info(f"Đã lấy {len(df)} nến cho {symbol}")
        logger.info(f"5 nến gần nhất:\n{df.tail(5)}")
    
    # Test tìm các mức hỗ trợ và kháng cự
    logger.info(f"Test tìm các mức hỗ trợ và kháng cự cho {symbol}")
    sr_levels = ta.find_support_resistance(symbol, timeframe='1h')
    if sr_levels is not None:
        logger.info(f"Giá hiện tại: {sr_levels['current_price']}")
        logger.info(f"Các mức kháng cự: {sr_levels['resistance_levels']}")
        logger.info(f"Các mức hỗ trợ: {sr_levels['support_levels']}")
    
    # Test các hàm tính toán stop loss và take profit
    logger.info(f"Test tính toán stop loss và take profit cho {symbol}")
    sl_info = ta.calculate_optimal_stop_loss(symbol, timeframe='1h')
    tp_info = ta.calculate_optimal_take_profit(symbol, timeframe='1h')
    
    if sl_info is not None and tp_info is not None:
        logger.info(f"Stop loss: {sl_info['price']} ({sl_info['percent']:.2f}%)")
        logger.info(f"Take profit: {tp_info['price']} ({tp_info['percent']:.2f}%)")
    
    # Test khuyến nghị giao dịch
    logger.info(f"Test khuyến nghị giao dịch cho {symbol}")
    recommendation = ta.get_trading_recommendation(symbol, timeframe='1h', leverage=5)
    
    if recommendation is not None:
        logger.info(f"Khuyến nghị đã được tạo thành công")
    
    logger.info("Hoàn thành kiểm thử module phân tích kỹ thuật")

if __name__ == "__main__":
    test_module()