#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("MarketAnalyzer")

class MarketAnalyzer:
    """
    Class phân tích thị trường và tính toán các chỉ báo kỹ thuật
    """
    
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        """
        Khởi tạo MarketAnalyzer
        
        Args:
            api_key (str, optional): API key
            api_secret (str, optional): API secret
            testnet (bool, optional): Sử dụng testnet hay không
        """
        self.api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY")
        self.api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET")
        self.testnet = testnet
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Thiếu API key hoặc API secret")
        
        # Khởi tạo client
        self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        self.cache = {}
        self.last_update = {}
    
    def get_market_overview(self):
        """
        Lấy tổng quan thị trường
        
        Returns:
            dict: Thông tin thị trường
        """
        try:
            # Lấy thông tin tài khoản futures
            account = self.client.futures_account()
            total_balance = float(account['totalWalletBalance'])
            available_balance = float(account['availableBalance'])
            positions = account['positions']
            
            # Lấy thông tin thị trường cho các cặp tiền được giao dịch
            active_symbols = [pos['symbol'] for pos in positions if float(pos['positionAmt']) != 0]
            all_tickers = self.client.futures_ticker()
            
            market_data = {
                'account_balance': total_balance,
                'available_balance': available_balance,
                'positions': []
            }
            
            # Thêm thông tin vị thế
            for position in positions:
                if float(position['positionAmt']) != 0:
                    market_data['positions'].append({
                        'symbol': position['symbol'],
                        'size': float(position['positionAmt']),
                        'entry_price': float(position['entryPrice']),
                        'mark_price': float(position['markPrice']),
                        'unrealized_pnl': float(position['unrealizedProfit']),
                        'liquidation_price': float(position['liquidationPrice'])
                    })
            
            # Thêm thông tin thị trường
            for ticker in all_tickers:
                symbol = ticker['symbol']
                if symbol in active_symbols:
                    market_data[symbol] = {
                        'price': float(ticker['lastPrice']),
                        'price_change': float(ticker['priceChange']),
                        'price_change_percent': float(ticker['priceChangePercent']),
                        'volume': float(ticker['volume']),
                        'high_24h': float(ticker['highPrice']),
                        'low_24h': float(ticker['lowPrice'])
                    }
            
            return market_data
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy thông tin thị trường: {str(e)}")
            return None
    
    def get_historical_klines(self, symbol, interval, limit=500):
        """
        Lấy dữ liệu lịch sử
        
        Args:
            symbol (str): Symbol
            interval (str): Khoảng thời gian (1m, 5m, 15m, 1h, 4h, 1d)
            limit (int, optional): Số lượng nến tối đa
        
        Returns:
            pd.DataFrame: Dữ liệu lịch sử
        """
        try:
            # Kiểm tra cache
            cache_key = f"{symbol}_{interval}"
            if cache_key in self.cache:
                last_update = self.last_update.get(cache_key, 0)
                if datetime.now().timestamp() - last_update < 60:  # Cache 1 phút
                    return self.cache[cache_key]
            
            # Lấy dữ liệu mới
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_base',
                'taker_quote', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Cập nhật cache
            self.cache[cache_key] = df
            self.last_update[cache_key] = datetime.now().timestamp()
            
            return df
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử cho {symbol}: {str(e)}")
            return None
    
    def calculate_indicators(self, df):
        """
        Tính toán các chỉ báo kỹ thuật
        
        Args:
            df (pd.DataFrame): DataFrame với dữ liệu giá
        
        Returns:
            dict: Các chỉ báo kỹ thuật
        """
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            
            # Bollinger Bands
            ma20 = df['close'].rolling(window=20).mean()
            std20 = df['close'].rolling(window=20).std()
            upper_band = ma20 + (std20 * 2)
            lower_band = ma20 - (std20 * 2)
            
            # Moving Averages
            ma50 = df['close'].rolling(window=50).mean()
            ma200 = df['close'].rolling(window=200).mean()
            
            # Volume Analysis
            volume_ma = df['volume'].rolling(window=20).mean()
            volume_ratio = df['volume'] / volume_ma
            
            return {
                'rsi': rsi.iloc[-1],
                'macd': macd.iloc[-1],
                'macd_signal': signal.iloc[-1],
                'macd_hist': (macd - signal).iloc[-1],
                'bb_upper': upper_band.iloc[-1],
                'bb_middle': ma20.iloc[-1],
                'bb_lower': lower_band.iloc[-1],
                'ma50': ma50.iloc[-1],
                'ma200': ma200.iloc[-1],
                'volume_ratio': volume_ratio.iloc[-1]
            }
        except Exception as e:
            logger.error(f"Lỗi khi tính toán chỉ báo: {str(e)}")
            return None
    
    def get_market_analysis(self, symbol, interval='1h'):
        """
        Phân tích thị trường cho một symbol
        
        Args:
            symbol (str): Symbol cần phân tích
            interval (str, optional): Khoảng thời gian
        
        Returns:
            dict: Kết quả phân tích
        """
        try:
            # Lấy dữ liệu lịch sử
            df = self.get_historical_klines(symbol, interval)
            if df is None or len(df) < 200:  # Cần ít nhất 200 nến cho MA200
                return None
            
            # Tính toán chỉ báo
            indicators = self.calculate_indicators(df)
            if indicators is None:
                return None
            
            # Lấy giá hiện tại
            current_price = float(df['close'].iloc[-1])
            
            # Phân tích xu hướng
            trend = "SIDEWAYS"
            if current_price > indicators['ma200'] and current_price > indicators['ma50']:
                trend = "UPTREND"
            elif current_price < indicators['ma200'] and current_price < indicators['ma50']:
                trend = "DOWNTREND"
            
            # Phân tích RSI
            rsi_signal = "NEUTRAL"
            if indicators['rsi'] > 70:
                rsi_signal = "OVERBOUGHT"
            elif indicators['rsi'] < 30:
                rsi_signal = "OVERSOLD"
            
            # Phân tích MACD
            macd_signal = "NEUTRAL"
            if indicators['macd_hist'] > 0 and indicators['macd'] > 0:
                macd_signal = "BULLISH"
            elif indicators['macd_hist'] < 0 and indicators['macd'] < 0:
                macd_signal = "BEARISH"
            
            # Phân tích Bollinger Bands
            bb_signal = "NEUTRAL"
            if current_price > indicators['bb_upper']:
                bb_signal = "OVERBOUGHT"
            elif current_price < indicators['bb_lower']:
                bb_signal = "OVERSOLD"
            
            # Phân tích khối lượng
            volume_signal = "NORMAL"
            if indicators['volume_ratio'] > 2:
                volume_signal = "HIGH"
            elif indicators['volume_ratio'] < 0.5:
                volume_signal = "LOW"
            
            return {
                'symbol': symbol,
                'interval': interval,
                'current_price': current_price,
                'trend': trend,
                'indicators': indicators,
                'signals': {
                    'rsi': rsi_signal,
                    'macd': macd_signal,
                    'bollinger': bb_signal,
                    'volume': volume_signal
                }
            }
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường cho {symbol}: {str(e)}")
            return None

def main():
    """Hàm chính để kiểm tra MarketAnalyzer"""
    api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("Thiếu API key hoặc API secret")
        return
    
    analyzer = MarketAnalyzer(api_key, api_secret, testnet=True)
    
    # Lấy tổng quan thị trường
    market_data = analyzer.get_market_overview()
    if market_data:
        print("\nTổng quan thị trường:")
        print(f"Số dư tài khoản: {market_data['account_balance']} USDT")
        print(f"Số dư khả dụng: {market_data['available_balance']} USDT")
        print(f"Số vị thế đang mở: {len(market_data['positions'])}")
    
    # Phân tích BTCUSDT
    analysis = analyzer.get_market_analysis("BTCUSDT", "1h")
    if analysis:
        print("\nPhân tích BTCUSDT:")
        print(f"Giá hiện tại: {analysis['current_price']}")
        print(f"Xu hướng: {analysis['trend']}")
        print("\nTín hiệu:")
        for signal_type, signal in analysis['signals'].items():
            print(f"{signal_type.upper()}: {signal}")

if __name__ == "__main__":
    main()