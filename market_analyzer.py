#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module phân tích thị trường
"""

import os
import json
import time
import math
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Union, Any

# Thiết lập logging
logger = logging.getLogger("market_analyzer")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

try:
    # Sử dụng python-binance cho việc gọi API
    import requests
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    import pandas as pd
    import numpy as np
    
    # Ghi log nếu import thành công
    logger.info("Đã import các thư viện cần thiết")
except ImportError as e:
    logger.error(f"Lỗi khi import thư viện: {str(e)}")

class MarketAnalyzer:
    """
    Lớp phân tích thị trường sử dụng API Binance
    """
    def __init__(self, testnet=True):
        """
        Khởi tạo phân tích thị trường
        
        :param testnet: Sử dụng testnet hay không
        """
        self.testnet = testnet
        self.client = None
        self.initialized = False
        
        # Khởi tạo API client
        self.initialize_client()
    
    def initialize_client(self):
        """Khởi tạo client API"""
        try:
            # Lấy khóa API từ biến môi trường
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                logger.warning("API key hoặc API secret không được cung cấp")
                return
            
            # Khởi tạo client
            self.client = Client(api_key, api_secret, testnet=self.testnet)
            
            # Test kết nối
            self.client.get_account()
            
            self.initialized = True
            logger.info("Đã khởi tạo Binance API client thành công")
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo client: {str(e)}")
    
    def get_market_overview(self) -> Dict[str, Any]:
        """
        Lấy tổng quan thị trường
        
        :return: Dict với thông tin thị trường
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT"]
            market_data = []
            
            for symbol in symbols:
                try:
                    # Lấy ticker
                    ticker = self.client.get_ticker(symbol=symbol)
                    
                    # Tính toán khối lượng thành USD
                    volume_usdt = float(ticker["volume"]) * float(ticker["lastPrice"])
                    
                    # Thêm vào danh sách
                    market_data.append({
                        "symbol": symbol,
                        "price": float(ticker["lastPrice"]),
                        "change_24h": float(ticker["priceChangePercent"]),
                        "volume": volume_usdt,
                        "high_24h": float(ticker["highPrice"]),
                        "low_24h": float(ticker["lowPrice"])
                    })
                except Exception as e:
                    logger.error(f"Lỗi khi lấy dữ liệu cho {symbol}: {str(e)}")
            
            # Sắp xếp theo khối lượng giảm dần
            market_data.sort(key=lambda x: x["volume"], reverse=True)
            
            return {"status": "success", "data": market_data}
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi lấy tổng quan thị trường: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """
        Lấy dữ liệu nến (klines)
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param interval: Khung thời gian (ví dụ: 1h, 4h, 1d)
        :param limit: Số lượng nến tối đa
        :return: DataFrame với dữ liệu nến
        """
        if not self.initialized:
            logger.error("API client chưa được khởi tạo")
            return pd.DataFrame()
        
        try:
            # Lấy dữ liệu nến từ Binance
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Chuyển đổi dữ liệu thành DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                               'quote_asset_volume', 'number_of_trades',
                               'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # Đặt timestamp làm index
            df.set_index('timestamp', inplace=True)
            
            return df
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu nến: {str(e)}")
            return pd.DataFrame()
    
    def calculate_rsi(self, closes: pd.Series, period: int = 14) -> pd.Series:
        """
        Tính toán chỉ báo RSI (Relative Strength Index)
        
        :param closes: Series giá đóng cửa
        :param period: Chu kỳ RSI
        :return: Series chứa giá trị RSI
        """
        # Tính toán thay đổi giá
        delta = closes.diff()
        
        # Tách các giá trị dương và âm
        gain = delta.copy()
        loss = delta.copy()
        gain[gain < 0] = 0
        loss[loss > 0] = 0
        loss = abs(loss)
        
        # Tính toán giá trị trung bình
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Tính toán RS và RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Tính toán chỉ báo SMA (Simple Moving Average)
        
        :param data: Series dữ liệu
        :param period: Chu kỳ SMA
        :return: Series chứa giá trị SMA
        """
        return data.rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Tính toán chỉ báo EMA (Exponential Moving Average)
        
        :param data: Series dữ liệu
        :param period: Chu kỳ EMA
        :return: Series chứa giá trị EMA
        """
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_macd(self, closes: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Tính toán chỉ báo MACD (Moving Average Convergence Divergence)
        
        :param closes: Series giá đóng cửa
        :param fast_period: Chu kỳ nhanh
        :param slow_period: Chu kỳ chậm
        :param signal_period: Chu kỳ đường tín hiệu
        :return: Tuple (macd, signal, histogram)
        """
        # Tính toán EMA nhanh và chậm
        ema_fast = self.calculate_ema(closes, fast_period)
        ema_slow = self.calculate_ema(closes, slow_period)
        
        # Tính toán MACD Line
        macd_line = ema_fast - ema_slow
        
        # Tính toán Signal Line
        signal_line = self.calculate_ema(macd_line, signal_period)
        
        # Tính toán Histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, closes: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Tính toán chỉ báo Bollinger Bands
        
        :param closes: Series giá đóng cửa
        :param period: Chu kỳ
        :param num_std: Số độ lệch chuẩn
        :return: Tuple (upper_band, middle_band, lower_band)
        """
        # Tính toán SMA
        middle_band = self.calculate_sma(closes, period)
        
        # Tính toán độ lệch chuẩn
        std = closes.rolling(window=period).std()
        
        # Tính toán upper và lower bands
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        return upper_band, middle_band, lower_band
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Tính toán chỉ báo ATR (Average True Range)
        
        :param df: DataFrame dữ liệu nến
        :param period: Chu kỳ
        :return: Series chứa giá trị ATR
        """
        # Tính toán True Range
        high_low = df['high'] - df['low']
        high_close_prev = np.abs(df['high'] - df['close'].shift(1))
        low_close_prev = np.abs(df['low'] - df['close'].shift(1))
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # Tính toán ATR
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def analyze_technical(self, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Phân tích kỹ thuật cho một cặp tiền
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param interval: Khung thời gian (ví dụ: 1h, 4h, 1d)
        :return: Dict với phân tích kỹ thuật
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            # Lấy dữ liệu nến
            df = self.get_klines(symbol, interval, 100)
            
            if df.empty:
                return {"status": "error", "message": "Không thể lấy dữ liệu nến"}
            
            # Tính toán các chỉ báo kỹ thuật
            
            # RSI
            rsi = self.calculate_rsi(df['close'])
            latest_rsi = rsi.iloc[-1]
            
            # MACD
            macd, signal, histogram = self.calculate_macd(df['close'])
            latest_macd = macd.iloc[-1]
            latest_signal = signal.iloc[-1]
            latest_histogram = histogram.iloc[-1]
            
            # Bollinger Bands
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df['close'])
            latest_upper = upper_band.iloc[-1]
            latest_middle = middle_band.iloc[-1]
            latest_lower = lower_band.iloc[-1]
            
            # Moving Averages
            sma_20 = self.calculate_sma(df['close'], 20)
            sma_50 = self.calculate_sma(df['close'], 50)
            sma_200 = self.calculate_sma(df['close'], 50)  # Giả lập SMA 200 với SMA 50 vì dữ liệu ít
            
            latest_sma_20 = sma_20.iloc[-1]
            latest_sma_50 = sma_50.iloc[-1]
            latest_sma_200 = sma_200.iloc[-1]
            
            # ATR
            atr = self.calculate_atr(df)
            latest_atr = atr.iloc[-1]
            
            # Giá hiện tại
            current_price = df['close'].iloc[-1]
            
            # Phân tích tín hiệu
            
            # Tín hiệu RSI
            if latest_rsi > 70:
                rsi_signal = "Bán"
            elif latest_rsi < 30:
                rsi_signal = "Mua"
            else:
                rsi_signal = "Trung lập"
            
            # Tín hiệu MACD
            if latest_macd > latest_signal and latest_histogram > 0 and latest_histogram > histogram.iloc[-2]:
                macd_signal = "Mua"
            elif latest_macd < latest_signal and latest_histogram < 0 and latest_histogram < histogram.iloc[-2]:
                macd_signal = "Bán"
            else:
                macd_signal = "Trung lập"
            
            # Tín hiệu Bollinger Bands
            bb_width = (latest_upper - latest_lower) / latest_middle
            
            if current_price > latest_upper:
                bb_signal = "Bán"
            elif current_price < latest_lower:
                bb_signal = "Mua"
            elif bb_width < 0.1:  # Dải hẹp, chuẩn bị breakout
                bb_signal = "Chuẩn bị breakout"
            else:
                bb_signal = "Trung lập"
            
            # Tín hiệu Moving Average
            if latest_sma_20 > latest_sma_50 and latest_sma_20 > latest_sma_200:
                ma_signal = "Mua"
            elif latest_sma_20 < latest_sma_50 and latest_sma_20 < latest_sma_200:
                ma_signal = "Bán"
            else:
                ma_signal = "Trung lập"
            
            # Tổng hợp tín hiệu
            signals = [rsi_signal, macd_signal, bb_signal, ma_signal]
            buy_count = signals.count("Mua")
            sell_count = signals.count("Bán")
            
            if buy_count > sell_count and buy_count >= 2:
                overall_signal = "Mua"
                if buy_count >= 3:
                    strength = "Mạnh"
                else:
                    strength = "Trung bình"
            elif sell_count > buy_count and sell_count >= 2:
                overall_signal = "Bán"
                if sell_count >= 3:
                    strength = "Mạnh"
                else:
                    strength = "Trung bình"
            else:
                overall_signal = "Trung lập"
                strength = "Yếu"
            
            # Phân tích xu hướng
            if sma_20.iloc[-1] > sma_20.iloc[-5] and sma_50.iloc[-1] > sma_50.iloc[-5]:
                short_term_trend = "Tăng"
            elif sma_20.iloc[-1] < sma_20.iloc[-5] and sma_50.iloc[-1] < sma_50.iloc[-5]:
                short_term_trend = "Giảm"
            else:
                short_term_trend = "Sideway"
            
            if sma_50.iloc[-1] > sma_50.iloc[-10]:
                mid_term_trend = "Tăng"
            elif sma_50.iloc[-1] < sma_50.iloc[-10]:
                mid_term_trend = "Giảm"
            else:
                mid_term_trend = "Sideway"
            
            if sma_200.iloc[-1] > sma_200.iloc[-20]:
                long_term_trend = "Tăng"
            elif sma_200.iloc[-1] < sma_200.iloc[-20]:
                long_term_trend = "Giảm"
            else:
                long_term_trend = "Sideway"
            
            # Xác định các mức hỗ trợ/kháng cự
            support_resistance = []
            
            # Giá cao nhất và thấp nhất trong 100 nến
            highest_high = df['high'].max()
            lowest_low = df['low'].min()
            
            # Thêm mức hỗ trợ/kháng cự
            support_resistance.append({"type": "Kháng cự 1", "value": highest_high})
            support_resistance.append({"type": "Kháng cự 2", "value": current_price + latest_atr * 2})
            support_resistance.append({"type": "Hỗ trợ 1", "value": lowest_low})
            support_resistance.append({"type": "Hỗ trợ 2", "value": current_price - latest_atr * 2})
            
            # Tạo kết quả
            result = {
                "status": "success",
                "symbol": symbol,
                "interval": interval,
                "price": current_price,
                "overall_signal": overall_signal,
                "strength": strength,
                "short_term_trend": short_term_trend,
                "mid_term_trend": mid_term_trend,
                "long_term_trend": long_term_trend,
                "support_resistance": support_resistance,
                "indicators": [
                    {"name": "RSI", "value": f"{latest_rsi:.2f}", "signal": rsi_signal},
                    {"name": "MACD", "value": f"MACD: {latest_macd:.2f}, Signal: {latest_signal:.2f}, Histogram: {latest_histogram:.2f}", "signal": macd_signal},
                    {"name": "Bollinger Bands", "value": f"Upper: {latest_upper:.2f}, Middle: {latest_middle:.2f}, Lower: {latest_lower:.2f}", "signal": bb_signal},
                    {"name": "Moving Averages", "value": f"SMA20: {latest_sma_20:.2f}, SMA50: {latest_sma_50:.2f}, SMA200: {latest_sma_200:.2f}", "signal": ma_signal},
                    {"name": "ATR", "value": f"{latest_atr:.2f}", "signal": "N/A"}
                ]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích kỹ thuật: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Lấy thông tin tài khoản
        
        :return: Dict với thông tin tài khoản
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            # Lấy thông tin tài khoản futures
            account_info = self.client.futures_account()
            
            # Tạo dữ liệu trả về
            account_data = {
                "balance": float(account_info["totalWalletBalance"]),
                "unrealized_pnl": float(account_info["totalUnrealizedProfit"]),
                "margin_balance": float(account_info["totalMarginBalance"]),
                "positions": []
            }
            
            # Lấy thông tin vị thế
            for position in account_info["positions"]:
                # Chỉ lấy các vị thế có số lượng khác 0
                if float(position["positionAmt"]) != 0:
                    account_data["positions"].append({
                        "symbol": position["symbol"],
                        "side": "LONG" if float(position["positionAmt"]) > 0 else "SHORT",
                        "amount": abs(float(position["positionAmt"])),
                        "entry_price": float(position["entryPrice"]),
                        "mark_price": float(position["markPrice"]),
                        "unrealized_pnl": float(position["unrealizedProfit"]),
                        "leverage": float(position["leverage"])
                    })
            
            return {"status": "success", "account": account_data}
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_market_data(self, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Lấy dữ liệu thị trường cho một cặp tiền
        
        :param symbol: Cặp giao dịch (ví dụ: BTCUSDT)
        :param interval: Khung thời gian (ví dụ: 1h, 4h, 1d)
        :return: Dict với dữ liệu thị trường
        """
        if not self.initialized:
            return {"status": "error", "message": "API client chưa được khởi tạo"}
        
        try:
            # Lấy dữ liệu nến
            df = self.get_klines(symbol, interval, 100)
            
            if df.empty:
                return {"status": "error", "message": "Không thể lấy dữ liệu nến"}
            
            # Lấy ticker hiện tại
            ticker = self.client.get_ticker(symbol=symbol)
            
            # Tính toán khối lượng thành USD
            volume_usdt = float(ticker["volume"]) * float(ticker["lastPrice"])
            
            # Tạo kết quả
            result = {
                "status": "success",
                "symbol": symbol,
                "interval": interval,
                "price": float(ticker["lastPrice"]),
                "change_24h": float(ticker["priceChangePercent"]),
                "volume": volume_usdt,
                "high_24h": float(ticker["highPrice"]),
                "low_24h": float(ticker["lowPrice"]),
                "open": float(df['open'].iloc[-1]),
                "close": float(df['close'].iloc[-1]),
                "high": float(df['high'].iloc[-1]),
                "low": float(df['low'].iloc[-1])
            }
            
            return result
            
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
            return {"status": "error", "message": str(e)}

# Hàm kiểm tra kết nối
def test_analyzer():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Đang kiểm tra MarketAnalyzer...")
    
    # Tạo instance
    analyzer = MarketAnalyzer(testnet=True)
    
    # Kiểm tra kết nối
    logger.info("Đang lấy tổng quan thị trường...")
    overview = analyzer.get_market_overview()
    if overview["status"] == "success":
        logger.info(f"Đã tìm thấy {len(overview['data'])} cặp tiền")
    else:
        logger.error(f"Lỗi: {overview.get('message', 'Không rõ lỗi')}")
    
    # Phân tích kỹ thuật
    logger.info("Đang phân tích kỹ thuật cho BTCUSDT...")
    analysis = analyzer.analyze_technical("BTCUSDT", "1h")
    if analysis["status"] == "success":
        logger.info(f"Tín hiệu: {analysis['overall_signal']} ({analysis['strength']})")
        logger.info(f"Xu hướng ngắn hạn: {analysis['short_term_trend']}")
        logger.info(f"Xu hướng trung hạn: {analysis['mid_term_trend']}")
        logger.info(f"Xu hướng dài hạn: {analysis['long_term_trend']}")
        
        for indicator in analysis["indicators"]:
            logger.info(f"{indicator['name']}: {indicator['value']} - {indicator['signal']}")
    else:
        logger.error(f"Lỗi: {analysis.get('message', 'Không rõ lỗi')}")
    
    # Lấy thông tin tài khoản
    logger.info("Đang lấy thông tin tài khoản...")
    account = analyzer.get_account_info()
    if account["status"] == "success":
        logger.info(f"Số dư: {account['account']['balance']} USDT")
        logger.info(f"Unrealized PnL: {account['account']['unrealized_pnl']} USDT")
        logger.info(f"Số lượng vị thế: {len(account['account']['positions'])}")
    else:
        logger.error(f"Lỗi: {account.get('message', 'Không rõ lỗi')}")

if __name__ == "__main__":
    test_analyzer()