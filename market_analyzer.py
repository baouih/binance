#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module phân tích thị trường
"""

# Xử lý vấn đề import để tránh lỗi
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except ImportError:
    # Tạo lớp giả khi không import được
    class Client:
        def __init__(self, *args, **kwargs):
            pass
    
    class BinanceAPIException(Exception):
        pass

try:
    import pandas as pd
    import numpy as np
except ImportError:
    # Tạo module giả khi không import được
    class ModuleStub:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    
    pd = ModuleStub()
    np = ModuleStub()

import os
import json
import time
import logging
import datetime
import traceback
import statistics
import math
from typing import Dict, List, Union, Tuple, Any, Optional

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("market_analyzer")

try:
    # Import thư viện Binance
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    
    # Import pandas và numpy cho phân tích dữ liệu
    import pandas as pd
    import numpy as np
    
    logger.info("Đã import thành công các thư viện phân tích")
except ImportError as e:
    logger.error(f"Lỗi khi import thư viện: {str(e)}")

class MarketAnalyzer:
    """Phân tích thị trường"""
    
    def __init__(self, testnet: bool = True):
        """
        Khởi tạo Market Analyzer
        
        :param testnet: Sử dụng testnet hay không
        """
        self.testnet = testnet
        self.client = self._create_client()
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", 
                        "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT"]
        
        logger.info("Đã khởi tạo Market Analyzer")
    
    def _create_client(self):
        """
        Tạo client Binance
        
        :return: Đối tượng Client
        """
        try:
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                logger.error("Thiếu API Key hoặc API Secret")
                self._log_connection_failure("missing_credentials", "Thiếu API Key hoặc API Secret")
                return None
            
            client = Client(api_key, api_secret, testnet=self.testnet)
            
            # Thử lấy thông tin thời gian để xác minh kết nối hoạt động đầy đủ
            try:
                client.ping()
                server_time = client.get_server_time()
            except AttributeError:
                # Nếu không có phương thức ping hoặc get_server_time, thử sử dụng phương thức futures_ping
                try:
                    client.futures_ping()
                    server_time = {"serverTime": int(time.time() * 1000)}
                except:
                    # Fallback - tạo thời gian từ máy tính local
                    server_time = {"serverTime": int(time.time() * 1000)}
            if server_time:
                logger.info(f"Thời gian máy chủ Binance: {datetime.datetime.fromtimestamp(server_time['serverTime']/1000)}")
            
            # Lưu thông tin kết nối thành công
            self._log_connection_success()
            
            logger.info("Đã kết nối thành công với Binance API")
            return client
        
        except BinanceAPIException as e:
            error_code = getattr(e, "code", "unknown")
            error_message = str(e)
            
            logger.error(f"Lỗi Binance API: Code {error_code} - {error_message}")
            self._log_connection_failure(f"api_error_{error_code}", error_message)
            return None
            
        except Exception as e:
            logger.error(f"Lỗi không xác định khi kết nối tới Binance API: {str(e)}")
            logger.error(traceback.format_exc())
            self._log_connection_failure("unknown_error", str(e))
            return None
            
    def _log_connection_success(self):
        """Ghi nhận kết nối thành công"""
        try:
            connection_log = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success",
                "api_type": "binance",
                "mode": "testnet" if self.testnet else "mainnet"
            }
            
            # Lưu log kết nối
            self._save_connection_log(connection_log)
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu log kết nối thành công: {str(e)}")
    
    def _log_connection_failure(self, error_type, error_message):
        """
        Ghi nhận lỗi kết nối
        
        :param error_type: Loại lỗi
        :param error_message: Thông báo lỗi
        """
        try:
            connection_log = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "error",
                "api_type": "binance",
                "mode": "testnet" if self.testnet else "mainnet",
                "error_type": error_type,
                "error_message": error_message
            }
            
            # Lưu log kết nối
            self._save_connection_log(connection_log)
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu log kết nối thất bại: {str(e)}")
    
    def _save_connection_log(self, log_entry):
        """
        Lưu log kết nối
        
        :param log_entry: Thông tin log cần lưu
        """
        try:
            # Tạo thư mục logs nếu không tồn tại
            os.makedirs("logs", exist_ok=True)
            
            log_file = "logs/api_connection_logs.json"
            connection_logs = []
            
            # Đọc log cũ nếu có
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        connection_logs = json.load(f)
                        
                        # Đảm bảo connection_logs là list
                        if not isinstance(connection_logs, list):
                            connection_logs = []
                except:
                    connection_logs = []
            
            # Thêm log mới
            connection_logs.append(log_entry)
            
            # Giới hạn số lượng log (giữ 100 log gần nhất)
            if len(connection_logs) > 100:
                connection_logs = connection_logs[-100:]
            
            # Lưu log
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(connection_logs, f, indent=4)
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu log kết nối: {str(e)}")
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi tạo client: {str(e)}", exc_info=True)
            return None
    
    def get_current_price(self, symbol: str) -> Dict[str, Any]:
        """
        Lấy giá hiện tại
        
        :param symbol: Cặp giao dịch
        :return: Dict với giá hiện tại
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"status": "error", "message": "Chưa kết nối với Binance API"}
            
            # Kiểm tra xem đang ở môi trường testnet hay mainnet
            if hasattr(self, "testnet") and self.testnet:
                # Lấy giá hiện tại từ Future API cho testnet
                ticker = self.client.futures_symbol_ticker(symbol=symbol)
                
                # Lấy thông tin thay đổi 24h
                ticker_24h = self.client.futures_ticker(symbol=symbol)
                
                # Kết quả
                result = {
                    "status": "success",
                    "price": float(ticker["price"]),
                    "change_24h": float(ticker_24h["priceChangePercent"]) if "priceChangePercent" in ticker_24h else 0.0,
                    "volume": float(ticker_24h["volume"]) if "volume" in ticker_24h else 0.0
                }
            else:
                # Lấy giá hiện tại từ Spot API 
                ticker = self.client.get_ticker(symbol=symbol)
                
                # Kết quả
                result = {
                    "status": "success",
                    "price": float(ticker["lastPrice"]),
                    "change_24h": float(ticker["priceChangePercent"]),
                    "volume": float(ticker["volume"])
                }
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy giá hiện tại: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy giá hiện tại: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_market_overview(self) -> Dict[str, Any]:
        """
        Lấy tổng quan thị trường
        
        :return: Dict với tổng quan thị trường
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return {"status": "error", "message": "Chưa kết nối với Binance API"}
            
            # Lấy giá và khối lượng cho các cặp giao dịch
            market_data = []
            
            # Tạo DataFrame để lưu dữ liệu
            df = pd.DataFrame()
            
            # Lấy dữ liệu cho từng cặp
            for symbol in self.symbols:
                try:
                    # Lấy giá hiện tại - sử dụng futures API thay vì spot API
                    ticker = self.client.futures_ticker(symbol=symbol)
                    
                    # Thêm vào danh sách
                    market_data.append({
                        "symbol": symbol,
                        "price": float(ticker["lastPrice"]),
                        "change_24h": float(ticker["priceChangePercent"]),
                        "volume": float(ticker["volume"])
                    })
                except Exception as e:
                    logger.error(f"Lỗi khi lấy dữ liệu cho {symbol}: {str(e)}")
            
            # Kết quả
            result = {
                "status": "success",
                "data": market_data
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy tổng quan thị trường: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_historical_data(self, symbol: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
        """
        Lấy dữ liệu lịch sử
        
        :param symbol: Cặp giao dịch
        :param interval: Khoảng thời gian (1m, 5m, 15m, 1h, 4h, 1d)
        :param limit: Số lượng nến
        :return: DataFrame với dữ liệu lịch sử
        """
        try:
            if not self.client:
                logger.error("Chưa kết nối với Binance API")
                return pd.DataFrame()
            
            # Lấy dữ liệu lịch sử - sử dụng futures API thay vì spot API
            candles = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Tạo DataFrame
            df = pd.DataFrame(candles, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            
            # Chuyển đổi kiểu dữ liệu
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["open"] = pd.to_numeric(df["open"])
            df["high"] = pd.to_numeric(df["high"])
            df["low"] = pd.to_numeric(df["low"])
            df["close"] = pd.to_numeric(df["close"])
            df["volume"] = pd.to_numeric(df["volume"])
            
            return df
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy dữ liệu lịch sử: {str(e)}")
            return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy dữ liệu lịch sử: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Tính SMA (Simple Moving Average)
        
        :param df: DataFrame với dữ liệu
        :param period: Số nến
        :return: Series với giá trị SMA
        """
        return df["close"].rolling(window=period).mean()
    
    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Tính EMA (Exponential Moving Average)
        
        :param df: DataFrame với dữ liệu
        :param period: Số nến
        :return: Series với giá trị EMA
        """
        return df["close"].ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Tính RSI (Relative Strength Index)
        
        :param df: DataFrame với dữ liệu
        :param period: Số nến
        :return: Series với giá trị RSI
        """
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Tính MACD (Moving Average Convergence Divergence)
        
        :param df: DataFrame với dữ liệu
        :param fast: Kỳ hạn ngắn
        :param slow: Kỳ hạn dài
        :param signal: Kỳ hạn tín hiệu
        :return: Tuple (MACD, Signal, Histogram)
        """
        ema_fast = self.calculate_ema(df, fast)
        ema_slow = self.calculate_ema(df, slow)
        
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        
        return macd, signal_line, histogram
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Tính Bollinger Bands
        
        :param df: DataFrame với dữ liệu
        :param period: Số nến
        :param std_dev: Số lần độ lệch chuẩn
        :return: Tuple (Upper Band, Middle Band, Lower Band)
        """
        middle_band = self.calculate_sma(df, period)
        std = df["close"].rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    def get_technical_indicators(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Lấy các chỉ báo kỹ thuật cho danh sách cặp tiền và khung thời gian
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1h', '4h', '1d']
        :return: Dict chứa kết quả phân tích chỉ báo kỹ thuật
        """
        if not symbols:
            symbols = self.symbols
        
        if not timeframes:
            timeframes = ['1h', '4h', '1d']
            
        logger.info(f"Phân tích chỉ báo kỹ thuật cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy dữ liệu lịch sử
                    df = self.get_historical_data(symbol, timeframe, 100)
                    
                    if df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không có dữ liệu"
                        }
                        continue
                    
                    # Tính các chỉ báo kỹ thuật
                    sma_20 = self.calculate_sma(df, 20).iloc[-1]
                    sma_50 = self.calculate_sma(df, 50).iloc[-1]
                    sma_200 = self.calculate_sma(df, 200).iloc[-1] if len(df) >= 200 else None
                    
                    ema_12 = self.calculate_ema(df, 12).iloc[-1]
                    ema_26 = self.calculate_ema(df, 26).iloc[-1]
                    
                    rsi = self.calculate_rsi(df).iloc[-1]
                    
                    macd, signal, histogram = self.calculate_macd(df)
                    macd_value = macd.iloc[-1]
                    signal_value = signal.iloc[-1]
                    histogram_value = histogram.iloc[-1]
                    
                    upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df)
                    upper_value = upper_band.iloc[-1]
                    middle_value = middle_band.iloc[-1]
                    lower_value = lower_band.iloc[-1]
                    
                    # Tính xu hướng dựa trên SMA
                    current_price = df["close"].iloc[-1]
                    trend = "neutral"
                    
                    if current_price > sma_50 and sma_20 > sma_50:
                        trend = "bullish"
                    elif current_price < sma_50 and sma_20 < sma_50:
                        trend = "bearish"
                    
                    # Tính tín hiệu dựa trên RSI
                    rsi_signal = "neutral"
                    
                    if rsi > 70:
                        rsi_signal = "overbought"
                    elif rsi < 30:
                        rsi_signal = "oversold"
                    
                    # Tín hiệu MACD
                    macd_signal = "neutral"
                    
                    if macd_value > signal_value and histogram_value > 0:
                        macd_signal = "bullish"
                    elif macd_value < signal_value and histogram_value < 0:
                        macd_signal = "bearish"
                    
                    # Đánh giá tổng hợp
                    signals_count = {
                        "bullish": 0,
                        "bearish": 0,
                        "neutral": 0
                    }
                    
                    if trend == "bullish":
                        signals_count["bullish"] += 1
                    elif trend == "bearish":
                        signals_count["bearish"] += 1
                    else:
                        signals_count["neutral"] += 1
                    
                    if rsi_signal == "overbought":
                        signals_count["bearish"] += 1
                    elif rsi_signal == "oversold":
                        signals_count["bullish"] += 1
                    else:
                        signals_count["neutral"] += 1
                    
                    if macd_signal == "bullish":
                        signals_count["bullish"] += 1
                    elif macd_signal == "bearish":
                        signals_count["bearish"] += 1
                    else:
                        signals_count["neutral"] += 1
                    
                    # Xác định tín hiệu cuối cùng
                    overall_signal = "neutral"
                    
                    if signals_count["bullish"] > signals_count["bearish"]:
                        overall_signal = "bullish"
                    elif signals_count["bearish"] > signals_count["bullish"]:
                        overall_signal = "bearish"
                    
                    # Thêm vào kết quả
                    result["data"][symbol][timeframe] = {
                        "status": "success",
                        "price": current_price,
                        "indicators": {
                            "sma": {
                                "sma20": sma_20,
                                "sma50": sma_50,
                                "sma200": sma_200
                            },
                            "ema": {
                                "ema12": ema_12,
                                "ema26": ema_26
                            },
                            "rsi": rsi,
                            "macd": {
                                "macd": macd_value,
                                "signal": signal_value,
                                "histogram": histogram_value
                            },
                            "bollinger_bands": {
                                "upper": upper_value,
                                "middle": middle_value,
                                "lower": lower_value
                            }
                        },
                        "signals": {
                            "trend": trend,
                            "rsi": rsi_signal,
                            "macd": macd_signal,
                            "overall": overall_signal
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tính chỉ báo cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result

    def get_market_regime(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Xác định chế độ thị trường (trending, ranging, volatile)
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1d']
        :return: Dict chứa kết quả phân tích chế độ thị trường
        """
        if not symbols:
            symbols = self.symbols[:2]  # Chỉ lấy vài cặp đại diện
        
        if not timeframes:
            timeframes = ['1d']
            
        logger.info(f"Phân tích chế độ thị trường cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy dữ liệu lịch sử
                    df = self.get_historical_data(symbol, timeframe, 100)
                    
                    if df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không có dữ liệu"
                        }
                        continue
                    
                    # Tính các chỉ số biến động
                    df['returns'] = df['close'].pct_change()
                    volatility = df['returns'].std() * 100  # Độ biến động chuẩn hoá
                    
                    # Tính xu hướng với chỉ số ADX
                    df['tr1'] = abs(df['high'] - df['low'])
                    df['tr2'] = abs(df['high'] - df['close'].shift(1))
                    df['tr3'] = abs(df['low'] - df['close'].shift(1))
                    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
                    df['atr'] = df['tr'].rolling(window=14).mean()
                    
                    # Tính +DM và -DM
                    df['up_move'] = df['high'] - df['high'].shift(1)
                    df['down_move'] = df['low'].shift(1) - df['low']
                    
                    df['+dm'] = ((df['up_move'] > df['down_move']) & (df['up_move'] > 0)) * df['up_move']
                    df['-dm'] = ((df['down_move'] > df['up_move']) & (df['down_move'] > 0)) * df['down_move']
                    
                    # Tính +DI và -DI
                    df['+di'] = 100 * (df['+dm'] / df['atr']).rolling(window=14).mean()
                    df['-di'] = 100 * (df['-dm'] / df['atr']).rolling(window=14).mean()
                    
                    # Tính DX và ADX
                    df['dx'] = 100 * abs(df['+di'] - df['-di']) / (df['+di'] + df['-di'])
                    df['adx'] = df['dx'].rolling(window=14).mean()
                    
                    # Lấy giá trị ADX
                    try:
                        adx = df['adx'].iloc[-1]
                    except:
                        adx = 0
                    
                    # Phân loại chế độ thị trường
                    regime = "undetermined"
                    regime_strength = "neutral"
                    
                    if adx > 25:
                        regime = "trending"
                        if adx > 50:
                            regime_strength = "strong"
                        else:
                            regime_strength = "moderate"
                    else:
                        if volatility > 3:  # Ngưỡng biến động cao
                            regime = "volatile"
                            if volatility > 5:
                                regime_strength = "strong"
                            else:
                                regime_strength = "moderate"
                        else:
                            regime = "ranging"
                            if volatility < 1:
                                regime_strength = "strong"
                            else:
                                regime_strength = "moderate"
                    
                    # Thêm vào kết quả
                    result["data"][symbol][timeframe] = {
                        "status": "success",
                        "regime": regime,
                        "strength": regime_strength,
                        "metrics": {
                            "adx": adx,
                            "volatility": volatility,
                            "plus_di": df['+di'].iloc[-1] if '+di' in df else 0,
                            "minus_di": df['-di'].iloc[-1] if '-di' in df else 0,
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi phân tích chế độ thị trường cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result
    
    def get_market_forecast(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Dự báo xu hướng thị trường
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1d']
        :return: Dict chứa kết quả dự báo thị trường
        """
        if not symbols:
            symbols = self.symbols[:2]  # Chỉ lấy vài cặp đại diện
        
        if not timeframes:
            timeframes = ['1d']
            
        logger.info(f"Dự báo thị trường cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy dữ liệu lịch sử
                    df = self.get_historical_data(symbol, timeframe, 100)
                    
                    if df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không có dữ liệu"
                        }
                        continue
                    
                    # Tính chỉ báo
                    sma_20 = self.calculate_sma(df, 20)
                    sma_50 = self.calculate_sma(df, 50)
                    current_price = df['close'].iloc[-1]
                    
                    # Dự báo xu hướng giá
                    price_trend = "neutral"
                    if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_50.iloc[-1]:
                        price_trend = "bullish"
                    elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_50.iloc[-1]:
                        price_trend = "bearish"
                    
                    # Dự báo mức biến động 
                    returns = df['close'].pct_change()
                    volatility = returns.std() * 100
                    avg_volatility = returns.rolling(window=20).std().mean() * 100
                    
                    volatility_forecast = "normal"
                    if volatility > avg_volatility * 1.5:
                        volatility_forecast = "high"
                    elif volatility < avg_volatility * 0.5:
                        volatility_forecast = "low"
                    
                    # Dự báo mức hỗ trợ và kháng cự
                    sr_levels = self.identify_support_resistance(df)
                    support_levels = [level for level in sr_levels if level['type'] == 'Hỗ trợ']
                    resistance_levels = [level for level in sr_levels if level['type'] == 'Kháng cự']
                    
                    # Sắp xếp và lấy các mức gần nhất
                    support_levels.sort(key=lambda x: abs(x['value'] - current_price))
                    resistance_levels.sort(key=lambda x: abs(x['value'] - current_price))
                    
                    nearest_support = support_levels[0]['value'] if support_levels else None
                    nearest_resistance = resistance_levels[0]['value'] if resistance_levels else None
                    
                    # Thêm vào kết quả
                    result["data"][symbol][timeframe] = {
                        "status": "success",
                        "price_trend": price_trend,
                        "volatility_forecast": volatility_forecast,
                        "nearest_support": nearest_support,
                        "nearest_resistance": nearest_resistance,
                        "price_target": {
                            "short_term": current_price * (1.05 if price_trend == "bullish" else 0.95),
                            "medium_term": current_price * (1.1 if price_trend == "bullish" else 0.9)
                        },
                        "confidence": 0.7  # Độ tin cậy của dự báo
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi dự báo thị trường cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result
    
    def get_trading_recommendation(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Đưa ra khuyến nghị giao dịch
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1h', '4h']
        :return: Dict chứa kết quả khuyến nghị giao dịch
        """
        if not symbols:
            symbols = self.symbols[:3]  # Chỉ lấy vài cặp đại diện
        
        if not timeframes:
            timeframes = ['1h', '4h']
            
        logger.info(f"Khuyến nghị giao dịch cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy dữ liệu lịch sử
                    df = self.get_historical_data(symbol, timeframe, 100)
                    
                    if df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không có dữ liệu"
                        }
                        continue
                    
                    # Tính các chỉ báo
                    sma_20 = self.calculate_sma(df, 20)
                    sma_50 = self.calculate_sma(df, 50)
                    rsi = self.calculate_rsi(df)
                    macd, signal, histogram = self.calculate_macd(df)
                    upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df)
                    
                    # Phân tích chỉ báo
                    current_price = df['close'].iloc[-1]
                    
                    # Tín hiệu từ SMA
                    sma_signal = "neutral"
                    if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_50.iloc[-1]:
                        sma_signal = "buy"
                    elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_50.iloc[-1]:
                        sma_signal = "sell"
                    
                    # Tín hiệu từ RSI
                    rsi_signal = "neutral"
                    rsi_value = rsi.iloc[-1]
                    if rsi_value < 30:
                        rsi_signal = "buy"  # Quá bán
                    elif rsi_value > 70:
                        rsi_signal = "sell"  # Quá mua
                    
                    # Tín hiệu từ MACD
                    macd_signal_result = "neutral"
                    if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                        macd_signal_result = "buy"  # Cắt lên
                    elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
                        macd_signal_result = "sell"  # Cắt xuống
                    
                    # Tín hiệu từ Bollinger Bands
                    bb_signal = "neutral"
                    if current_price < lower_band.iloc[-1]:
                        bb_signal = "buy"  # Chạm dải dưới
                    elif current_price > upper_band.iloc[-1]:
                        bb_signal = "sell"  # Chạm dải trên
                    
                    # Kết hợp các tín hiệu
                    signals = {
                        "sma": sma_signal,
                        "rsi": rsi_signal,
                        "macd": macd_signal_result,
                        "bb": bb_signal
                    }
                    
                    buy_count = sum(1 for signal in signals.values() if signal == "buy")
                    sell_count = sum(1 for signal in signals.values() if signal == "sell")
                    
                    final_recommendation = "neutral"
                    if buy_count > sell_count and buy_count >= 2:
                        final_recommendation = "buy"
                    elif sell_count > buy_count and sell_count >= 2:
                        final_recommendation = "sell"
                    
                    # Tính mức giá vào lệnh và stop loss
                    entry_price = current_price
                    
                    # Tính stop loss và take profit dựa trên ATR
                    atr = self.calculate_atr(df).iloc[-1]
                    
                    stop_loss = None
                    take_profit = None
                    
                    if final_recommendation == "buy":
                        stop_loss = entry_price - (2 * atr)
                        take_profit = entry_price + (3 * atr)
                    elif final_recommendation == "sell":
                        stop_loss = entry_price + (2 * atr)
                        take_profit = entry_price - (3 * atr)
                    
                    # Thêm vào kết quả
                    result["data"][symbol][timeframe] = {
                        "status": "success",
                        "recommendation": final_recommendation,
                        "current_price": current_price,
                        "entry_price": entry_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "signals": signals,
                        "metrics": {
                            "rsi": rsi_value,
                            "sma20": sma_20.iloc[-1],
                            "sma50": sma_50.iloc[-1],
                            "macd": macd.iloc[-1],
                            "signal": signal.iloc[-1],
                            "bb_upper": upper_band.iloc[-1],
                            "bb_lower": lower_band.iloc[-1]
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lấy khuyến nghị giao dịch cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result
    
    def get_trading_signals(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Lấy tín hiệu giao dịch
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1h', '4h']
        :return: Dict chứa kết quả tín hiệu giao dịch
        """
        if not symbols:
            symbols = self.symbols[:3]  # Chỉ lấy vài cặp đại diện
        
        if not timeframes:
            timeframes = ['1h', '4h']
            
        logger.info(f"Lấy tín hiệu giao dịch cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy khuyến nghị giao dịch
                    recommendation = self.get_trading_recommendation([symbol], [timeframe])
                    
                    if recommendation["status"] == "success" and symbol in recommendation["data"]:
                        symbol_data = recommendation["data"][symbol]
                        if timeframe in symbol_data and symbol_data[timeframe]["status"] == "success":
                            # Lấy dữ liệu từ khuyến nghị
                            rec_data = symbol_data[timeframe]
                            
                            # Tính toán thêm thông tin tín hiệu
                            signal_strength = "medium"
                            signal_type = rec_data["recommendation"].upper()
                            
                            # Tính độ mạnh của tín hiệu
                            buy_signals = sum(1 for signal in rec_data["signals"].values() if signal == "buy")
                            sell_signals = sum(1 for signal in rec_data["signals"].values() if signal == "sell")
                            
                            if signal_type == "BUY" and buy_signals >= 3:
                                signal_strength = "strong"
                            elif signal_type == "SELL" and sell_signals >= 3:
                                signal_strength = "strong"
                            elif signal_type == "NEUTRAL":
                                signal_strength = "weak"
                            
                            # Thêm vào kết quả
                            result["data"][symbol][timeframe] = {
                                "status": "success",
                                "signal": {
                                    "type": signal_type,
                                    "strength": signal_strength,
                                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "price": rec_data["current_price"],
                                    "timeframe": timeframe,
                                    "stop_loss": rec_data["stop_loss"],
                                    "take_profit": rec_data["take_profit"]
                                }
                            }
                        else:
                            result["data"][symbol][timeframe] = {
                                "status": "error",
                                "message": "Không có dữ liệu khuyến nghị"
                            }
                    else:
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không thể lấy khuyến nghị"
                        }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lấy tín hiệu giao dịch cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result
    
    def get_market_trends(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Lấy xu hướng thị trường
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1d']
        :return: Dict chứa kết quả xu hướng thị trường
        """
        if not symbols:
            symbols = self.symbols[:3]  # Chỉ lấy vài cặp đại diện
        
        if not timeframes:
            timeframes = ['1d']
            
        logger.info(f"Lấy xu hướng thị trường cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy dữ liệu lịch sử
                    df = self.get_historical_data(symbol, timeframe, 100)
                    
                    if df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không có dữ liệu"
                        }
                        continue
                    
                    # Tính các chỉ báo
                    sma_20 = self.calculate_sma(df, 20)
                    sma_50 = self.calculate_sma(df, 50)
                    sma_200 = self.calculate_sma(df, 200) if len(df) >= 200 else None
                    
                    # Phân tích xu hướng
                    current_price = df['close'].iloc[-1]
                    
                    short_term_trend = "Sideway"
                    if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_20.iloc[-5]:
                        short_term_trend = "Uptrend"
                    elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_20.iloc[-5]:
                        short_term_trend = "Downtrend"
                    
                    medium_term_trend = "Sideway"
                    if sma_50.iloc[-1] > sma_50.iloc[-20]:
                        medium_term_trend = "Uptrend"
                    elif sma_50.iloc[-1] < sma_50.iloc[-20]:
                        medium_term_trend = "Downtrend"
                    
                    long_term_trend = "Sideway"
                    if sma_200 is not None:
                        if sma_200.iloc[-1] > sma_200.iloc[-50]:
                            long_term_trend = "Uptrend"
                        elif sma_200.iloc[-1] < sma_200.iloc[-50]:
                            long_term_trend = "Downtrend"
                    
                    # Thêm vào kết quả
                    result["data"][symbol][timeframe] = {
                        "status": "success",
                        "trends": {
                            "short_term": short_term_trend,
                            "medium_term": medium_term_trend,
                            "long_term": long_term_trend
                        },
                        "price": current_price,
                        "indicators": {
                            "sma20": sma_20.iloc[-1],
                            "sma50": sma_50.iloc[-1],
                            "sma200": sma_200.iloc[-1] if sma_200 is not None else None
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lấy xu hướng thị trường cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result
    
    def get_market_volumes(self, symbols: List[str] = None, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Lấy khối lượng giao dịch
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :param timeframes: Danh sách khung thời gian, mặc định là ['1d']
        :return: Dict chứa kết quả khối lượng giao dịch
        """
        if not symbols:
            symbols = self.symbols[:3]  # Chỉ lấy vài cặp đại diện
        
        if not timeframes:
            timeframes = ['1d']
            
        logger.info(f"Lấy khối lượng giao dịch cho {len(symbols)} cặp tiền và {len(timeframes)} khung thời gian")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            result["data"][symbol] = {}
            
            for timeframe in timeframes:
                try:
                    # Lấy dữ liệu lịch sử
                    df = self.get_historical_data(symbol, timeframe, 100)
                    
                    if df.empty:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result["data"][symbol][timeframe] = {
                            "status": "error",
                            "message": "Không có dữ liệu"
                        }
                        continue
                    
                    # Tính chỉ báo về khối lượng
                    volume = df['volume']
                    avg_volume = volume.rolling(window=20).mean()
                    volume_change = (volume.iloc[-1] / avg_volume.iloc[-1] - 1) * 100
                    
                    # Phân tích khối lượng
                    volume_trend = "normal"
                    if volume.iloc[-1] > avg_volume.iloc[-1] * 1.5:
                        volume_trend = "increasing"
                    elif volume.iloc[-1] < avg_volume.iloc[-1] * 0.5:
                        volume_trend = "decreasing"
                    
                    # Tính OBV (On-Balance Volume)
                    df['direction'] = np.where(df['close'] > df['close'].shift(1), 1, -1)
                    df.loc[df['close'] == df['close'].shift(1), 'direction'] = 0
                    df['obv'] = (df['volume'] * df['direction']).cumsum()
                    
                    # Thêm vào kết quả
                    result["data"][symbol][timeframe] = {
                        "status": "success",
                        "volumes": {
                            "current": float(volume.iloc[-1]),
                            "average": float(avg_volume.iloc[-1]),
                            "change": float(volume_change),
                            "trend": volume_trend
                        },
                        "obv": {
                            "current": float(df['obv'].iloc[-1]),
                            "previous": float(df['obv'].iloc[-2])
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lấy khối lượng giao dịch cho {symbol} - {timeframe}: {str(e)}")
                    result["data"][symbol][timeframe] = {
                        "status": "error",
                        "message": str(e)
                    }
        
        return result
    
    def get_24h_volumes(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Lấy khối lượng giao dịch 24h
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :return: Dict chứa kết quả khối lượng giao dịch 24h
        """
        if not symbols:
            symbols = self.symbols[:3]  # Chỉ lấy vài cặp đại diện
            
        logger.info(f"Lấy khối lượng giao dịch 24h cho {len(symbols)} cặp tiền")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        for symbol in symbols:
            try:
                # Lấy thông tin 24h từ API
                if hasattr(self.client, 'futures_ticker'):
                    ticker = self.client.futures_ticker(symbol=symbol)
                    
                    if ticker:
                        volume_24h = float(ticker.get('volume', 0))
                        quote_volume_24h = float(ticker.get('quoteVolume', 0))
                        
                        result["data"][symbol] = {
                            "status": "success",
                            "volume_24h": volume_24h,
                            "quote_volume_24h": quote_volume_24h,
                            "trades_24h": int(ticker.get('count', 0))
                        }
                    else:
                        result["data"][symbol] = {
                            "status": "error",
                            "message": "Không lấy được dữ liệu từ API"
                        }
                else:
                    # Sử dụng dữ liệu lịch sử 1h, 24 nến
                    df = self.get_historical_data(symbol, '1h', 24)
                    
                    if not df.empty:
                        volume_24h = df['volume'].sum()
                        
                        result["data"][symbol] = {
                            "status": "success",
                            "volume_24h": float(volume_24h),
                            "average_hourly": float(volume_24h / 24)
                        }
                    else:
                        result["data"][symbol] = {
                            "status": "error",
                            "message": "Không có dữ liệu lịch sử"
                        }
                
            except Exception as e:
                logger.error(f"Lỗi khi lấy khối lượng giao dịch 24h cho {symbol}: {str(e)}")
                result["data"][symbol] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return result
    
    def get_market_summary(self, symbols: List[str] = None) -> Dict[str, Any]:
        """
        Lấy tóm tắt thị trường
        
        :param symbols: Danh sách cặp tiền cần phân tích, mặc định là self.symbols
        :return: Dict chứa kết quả tóm tắt thị trường
        """
        if not symbols:
            symbols = self.symbols[:3]  # Chỉ lấy vài cặp đại diện
            
        logger.info(f"Lấy tóm tắt thị trường cho {len(symbols)} cặp tiền")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        # Lấy các chỉ báo tổng hợp
        for symbol in symbols:
            try:
                # Lấy giá hiện tại
                price_info = self.get_current_price(symbol)
                
                if price_info["status"] == "success":
                    current_price = price_info["price"]
                    change_24h = price_info["change_24h"]
                    
                    # Lấy chỉ báo kỹ thuật
                    indicator_1h = self.get_technical_indicators([symbol], ['1h'])
                    
                    # Lấy xu hướng
                    trend_1d = self.get_market_trends([symbol], ['1d'])
                    
                    # Tổng hợp dữ liệu
                    summary = {
                        "price": current_price,
                        "change_24h": change_24h,
                        "signal": "NEUTRAL"
                    }
                    
                    # Thêm tín hiệu từ chỉ báo 1h nếu có
                    if indicator_1h["status"] == "success" and symbol in indicator_1h["data"]:
                        if "1h" in indicator_1h["data"][symbol]:
                            indicator_data = indicator_1h["data"][symbol]["1h"]
                            if "signals" in indicator_data and "overall" in indicator_data["signals"]:
                                summary["signal"] = indicator_data["signals"]["overall"]
                    
                    # Thêm xu hướng từ dữ liệu 1d nếu có
                    if trend_1d["status"] == "success" and symbol in trend_1d["data"]:
                        if "1d" in trend_1d["data"][symbol]:
                            trend_data = trend_1d["data"][symbol]["1d"]
                            if "trends" in trend_data:
                                summary["trends"] = trend_data["trends"]
                    
                    result["data"][symbol] = summary
                else:
                    result["data"][symbol] = {
                        "status": "error",
                        "message": "Không lấy được giá hiện tại"
                    }
                
            except Exception as e:
                logger.error(f"Lỗi khi lấy tóm tắt thị trường cho {symbol}: {str(e)}")
                result["data"][symbol] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return result
    
    def get_btc_levels(self) -> Dict[str, Any]:
        """
        Lấy các mức giá Bitcoin quan trọng
        
        :return: Dict chứa kết quả các mức giá Bitcoin
        """
        logger.info("Phân tích các mức giá Bitcoin quan trọng")
        
        result = {
            "status": "success",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": {}
        }
        
        try:
            # Lấy dữ liệu lịch sử
            df = self.get_historical_data("BTCUSDT", "1d", 100)
            
            if df.empty:
                logger.warning("Không có dữ liệu lịch sử cho Bitcoin")
                return {
                    "status": "error",
                    "message": "Không có dữ liệu lịch sử"
                }
            
            # Tính các mức hỗ trợ và kháng cự
            sr_levels = self.identify_support_resistance(df)
            
            # Lấy giá hiện tại
            current_price = df["close"].iloc[-1]
            
            # Phân loại các mức theo loại và khoảng cách
            support_levels = [level for level in sr_levels if level['type'] == 'Hỗ trợ' and level['value'] < current_price]
            resistance_levels = [level for level in sr_levels if level['type'] == 'Kháng cự' and level['value'] > current_price]
            
            # Sắp xếp theo khoảng cách
            support_levels.sort(key=lambda x: current_price - x['value'])
            resistance_levels.sort(key=lambda x: x['value'] - current_price)
            
            # Lấy các mức đáng chú ý
            result["data"] = {
                "current_price": current_price,
                "support_levels": [level['value'] for level in support_levels[:3]],
                "resistance_levels": [level['value'] for level in resistance_levels[:3]],
                "psychological_levels": [
                    round(current_price / 10000) * 10000,  # Mức tâm lý gần nhất 10k
                    round(current_price / 5000) * 5000,    # Mức tâm lý gần nhất 5k
                    round(current_price / 1000) * 1000     # Mức tâm lý gần nhất 1k
                ]
            }
            
            # Thêm các vùng giá lịch sử
            all_time_high = df["high"].max()
            result["data"]["all_time_high"] = all_time_high
            
            # Tính các mức Fibonacci retracement từ đỉnh cao nhất gần đây đến đáy gần đây
            recent_high = df["high"].iloc[-20:].max()
            recent_low = df["low"].iloc[-20:].min()
            
            range_price = recent_high - recent_low
            
            result["data"]["fibonacci_levels"] = {
                "0.0": recent_low,
                "0.236": recent_low + 0.236 * range_price,
                "0.382": recent_low + 0.382 * range_price,
                "0.5": recent_low + 0.5 * range_price,
                "0.618": recent_low + 0.618 * range_price,
                "0.786": recent_low + 0.786 * range_price,
                "1.0": recent_high
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích các mức giá Bitcoin: {str(e)}")
            result = {
                "status": "error",
                "message": str(e)
            }
        
        return result
    
    def get_signal(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """
        Lấy tín hiệu giao dịch cho một cặp tiền cụ thể
        
        :param symbol: Cặp tiền cần phân tích
        :param timeframe: Khung thời gian
        :return: Dict chứa kết quả tín hiệu giao dịch
        """
        logger.info(f"Phân tích tín hiệu cho {symbol} - {timeframe}")
        
        try:
            # Lấy dữ liệu lịch sử
            df = self.get_historical_data(symbol, timeframe, 100)
            
            if df.empty:
                logger.warning(f"Không có dữ liệu lịch sử cho {symbol}")
                return {
                    "status": "error",
                    "message": "Không có dữ liệu lịch sử"
                }
            
            # Tính các chỉ báo
            sma_20 = self.calculate_sma(df, 20)
            sma_50 = self.calculate_sma(df, 50)
            rsi = self.calculate_rsi(df)
            macd, signal, histogram = self.calculate_macd(df)
            
            # Lấy giá hiện tại
            current_price = df["close"].iloc[-1]
            
            # Tín hiệu từ SMA
            sma_signal = "NEUTRAL"
            if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_50.iloc[-1]:
                sma_signal = "BUY"
            elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_50.iloc[-1]:
                sma_signal = "SELL"
            
            # Tín hiệu từ RSI
            rsi_signal = "NEUTRAL"
            rsi_value = rsi.iloc[-1]
            if rsi_value < 30:
                rsi_signal = "BUY"  # Quá bán
            elif rsi_value > 70:
                rsi_signal = "SELL"  # Quá mua
            
            # Tín hiệu từ MACD
            macd_signal_result = "NEUTRAL"
            if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                macd_signal_result = "BUY"  # Cắt lên
            elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
                macd_signal_result = "SELL"  # Cắt xuống
            
            # Tính tín hiệu tổng hợp
            signals = [sma_signal, rsi_signal, macd_signal_result]
            buy_count = signals.count("BUY")
            sell_count = signals.count("SELL")
            
            final_signal = "NEUTRAL"
            if buy_count > sell_count:
                final_signal = "BUY"
            elif sell_count > buy_count:
                final_signal = "SELL"
            
            # Tính độ mạnh tín hiệu
            signal_strength = "medium"
            if final_signal == "BUY" and buy_count >= 2:
                signal_strength = "strong"
            elif final_signal == "SELL" and sell_count >= 2:
                signal_strength = "strong"
            elif final_signal == "NEUTRAL":
                signal_strength = "weak"
            
            return {
                "status": "success",
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": final_signal,
                "strength": signal_strength,
                "price": current_price,
                "indicators": {
                    "sma": sma_signal,
                    "rsi": {
                        "value": rsi_value,
                        "signal": rsi_signal
                    },
                    "macd": {
                        "value": macd.iloc[-1],
                        "signal_line": signal.iloc[-1],
                        "signal": macd_signal_result
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích tín hiệu cho {symbol}: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def get_trend(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """
        Lấy xu hướng cho một cặp tiền cụ thể
        
        :param symbol: Cặp tiền cần phân tích
        :param timeframe: Khung thời gian
        :return: Dict chứa kết quả xu hướng
        """
        logger.info(f"Phân tích xu hướng cho {symbol} - {timeframe}")
        
        try:
            # Lấy dữ liệu lịch sử
            df = self.get_historical_data(symbol, timeframe, 100)
            
            if df.empty:
                logger.warning(f"Không có dữ liệu lịch sử cho {symbol}")
                return {
                    "status": "error",
                    "message": "Không có dữ liệu lịch sử"
                }
            
            # Tính các chỉ báo
            sma_20 = self.calculate_sma(df, 20)
            sma_50 = self.calculate_sma(df, 50)
            sma_200 = self.calculate_sma(df, 200) if len(df) >= 200 else None
            
            # Lấy giá hiện tại
            current_price = df["close"].iloc[-1]
            
            # Xác định xu hướng ngắn hạn
            short_term_trend = "SIDEWAY"
            if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_20.iloc[-5]:
                short_term_trend = "UPTREND"
            elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_20.iloc[-5]:
                short_term_trend = "DOWNTREND"
            
            # Xác định xu hướng trung hạn
            medium_term_trend = "SIDEWAY"
            if sma_50.iloc[-1] > sma_50.iloc[-20]:
                medium_term_trend = "UPTREND"
            elif sma_50.iloc[-1] < sma_50.iloc[-20]:
                medium_term_trend = "DOWNTREND"
            
            # Xác định xu hướng dài hạn
            long_term_trend = "SIDEWAY"
            if sma_200 is not None:
                if current_price > sma_200.iloc[-1]:
                    long_term_trend = "UPTREND"
                elif current_price < sma_200.iloc[-1]:
                    long_term_trend = "DOWNTREND"
            
            # Xác định xu hướng tổng thể
            trends = [short_term_trend, medium_term_trend, long_term_trend]
            uptrend_count = trends.count("UPTREND")
            downtrend_count = trends.count("DOWNTREND")
            
            overall_trend = "SIDEWAY"
            if uptrend_count > downtrend_count:
                overall_trend = "UPTREND"
            elif downtrend_count > uptrend_count:
                overall_trend = "DOWNTREND"
            
            return {
                "status": "success",
                "symbol": symbol,
                "timeframe": timeframe,
                "trend": overall_trend,
                "trends": {
                    "short_term": short_term_trend,
                    "medium_term": medium_term_trend,
                    "long_term": long_term_trend
                },
                "price": current_price,
                "indicators": {
                    "sma20": sma_20.iloc[-1],
                    "sma50": sma_50.iloc[-1],
                    "sma200": sma_200.iloc[-1] if sma_200 is not None else None
                }
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích xu hướng cho {symbol}: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def identify_support_resistance(self, df: pd.DataFrame, window_size: int = 10, threshold: float = 0.02) -> List[Dict[str, Any]]:
        """
        Xác định các mức hỗ trợ và kháng cự
        
        :param df: DataFrame với dữ liệu
        :param window_size: Kích thước cửa sổ để tìm đỉnh và đáy
        :param threshold: Ngưỡng để xác định các mức
        :return: List các mức hỗ trợ và kháng cự
        """
        sr_levels = []
        
        # Tìm các đỉnh và đáy cục bộ
        for i in range(window_size, len(df) - window_size):
            # Kiểm tra đỉnh
            if all(df["high"][i] > df["high"][i-j] for j in range(1, window_size+1)) and \
               all(df["high"][i] > df["high"][i+j] for j in range(1, window_size+1)):
                sr_levels.append({
                    "type": "Kháng cự",
                    "value": df["high"][i],
                    "timestamp": df["timestamp"][i]
                })
            
            # Kiểm tra đáy
            if all(df["low"][i] < df["low"][i-j] for j in range(1, window_size+1)) and \
               all(df["low"][i] < df["low"][i+j] for j in range(1, window_size+1)):
                sr_levels.append({
                    "type": "Hỗ trợ",
                    "value": df["low"][i],
                    "timestamp": df["timestamp"][i]
                })
        
        # Gộp các mức gần nhau
        if len(sr_levels) > 0:
            # Sắp xếp theo giá trị
            sr_levels = sorted(sr_levels, key=lambda x: x["value"])
            
            # Gộp các mức gần nhau
            merged_levels = [sr_levels[0]]
            
            for level in sr_levels[1:]:
                last_level = merged_levels[-1]
                
                # Tính phần trăm chênh lệch
                diff_percent = abs(level["value"] - last_level["value"]) / last_level["value"]
                
                if diff_percent <= threshold:
                    # Gộp các mức gần nhau
                    if level["type"] == last_level["type"]:
                        # Lấy giá trị trung bình
                        merged_value = (level["value"] + last_level["value"]) / 2
                        merged_levels[-1]["value"] = merged_value
                    else:
                        # Nếu khác loại (hỗ trợ/kháng cự), thêm vào
                        merged_levels.append(level)
                else:
                    # Nếu quá xa, thêm vào
                    merged_levels.append(level)
            
            return merged_levels
        
        return sr_levels
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Tính ATR (Average True Range)
        
        :param df: DataFrame với dữ liệu
        :param period: Số nến
        :return: Series với giá trị ATR
        """
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def analyze_technical(self, symbol: str, interval: str = "1h") -> Dict[str, Any]:
        """
        Phân tích kỹ thuật
        
        :param symbol: Cặp giao dịch
        :param interval: Khoảng thời gian (1m, 5m, 15m, 1h, 4h, 1d)
        :return: Dict với kết quả phân tích
        """
        try:
            # Lấy dữ liệu lịch sử
            df = self.get_historical_data(symbol, interval, 100)
            
            if df.empty:
                return {"status": "error", "message": f"Không thể lấy dữ liệu lịch sử cho {symbol}"}
            
            # Lấy giá hiện tại
            current_price = df["close"].iloc[-1]
            
            # Tính các chỉ báo
            df["sma20"] = self.calculate_sma(df, 20)
            df["sma50"] = self.calculate_sma(df, 50)
            df["sma200"] = self.calculate_sma(df, 200)
            
            df["ema12"] = self.calculate_ema(df, 12)
            df["ema26"] = self.calculate_ema(df, 26)
            
            df["rsi"] = self.calculate_rsi(df)
            
            macd, signal, histogram = self.calculate_macd(df)
            df["macd"] = macd
            df["macd_signal"] = signal
            df["macd_histogram"] = histogram
            
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df)
            df["bb_upper"] = upper_band
            df["bb_middle"] = middle_band
            df["bb_lower"] = lower_band
            
            df["atr"] = self.calculate_atr(df)
            
            # Xác định xu hướng
            short_term_trend = ""
            if df["sma20"].iloc[-1] > df["sma50"].iloc[-1]:
                short_term_trend = "Tăng"
            elif df["sma20"].iloc[-1] < df["sma50"].iloc[-1]:
                short_term_trend = "Giảm"
            else:
                short_term_trend = "Sideway"
            
            mid_term_trend = ""
            if df["sma50"].iloc[-1] > df["sma50"].iloc[-10]:
                mid_term_trend = "Tăng"
            elif df["sma50"].iloc[-1] < df["sma50"].iloc[-10]:
                mid_term_trend = "Giảm"
            else:
                mid_term_trend = "Sideway"
            
            long_term_trend = ""
            if df["sma200"].iloc[-1] > df["sma200"].iloc[-20]:
                long_term_trend = "Tăng"
            elif df["sma200"].iloc[-1] < df["sma200"].iloc[-20]:
                long_term_trend = "Giảm"
            else:
                long_term_trend = "Sideway"
            
            # Phân tích RSI
            rsi_signal = ""
            rsi_value = df["rsi"].iloc[-1]
            if rsi_value > 70:
                rsi_signal = "Bán"
            elif rsi_value < 30:
                rsi_signal = "Mua"
            else:
                rsi_signal = "Trung lập"
            
            # Phân tích MACD
            macd_signal = ""
            if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
                macd_signal = "Mua"
            elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] >= df["macd_signal"].iloc[-2]:
                macd_signal = "Bán"
            else:
                macd_signal = "Trung lập"
            
            # Phân tích Bollinger Bands
            bb_signal = ""
            if df["close"].iloc[-1] > df["bb_upper"].iloc[-1]:
                bb_signal = "Bán"
            elif df["close"].iloc[-1] < df["bb_lower"].iloc[-1]:
                bb_signal = "Mua"
            else:
                bb_signal = "Trung lập"
            
            # Xác định mức hỗ trợ và kháng cự
            support_resistance = self.identify_support_resistance(df)
            
            # Phân tích tổng hợp
            buy_signals = 0
            sell_signals = 0
            neutral_signals = 0
            
            # Đếm tín hiệu
            if rsi_signal == "Mua":
                buy_signals += 1
            elif rsi_signal == "Bán":
                sell_signals += 1
            else:
                neutral_signals += 1
            
            if macd_signal == "Mua":
                buy_signals += 1
            elif macd_signal == "Bán":
                sell_signals += 1
            else:
                neutral_signals += 1
            
            if bb_signal == "Mua":
                buy_signals += 1
            elif bb_signal == "Bán":
                sell_signals += 1
            else:
                neutral_signals += 1
            
            if short_term_trend == "Tăng":
                buy_signals += 1
            elif short_term_trend == "Giảm":
                sell_signals += 1
            else:
                neutral_signals += 1
            
            # Xác định tín hiệu tổng hợp
            overall_signal = ""
            if buy_signals > sell_signals:
                overall_signal = "Mua"
            elif sell_signals > buy_signals:
                overall_signal = "Bán"
            else:
                overall_signal = "Chờ đợi"
            
            # Xác định độ mạnh tín hiệu
            strength = ""
            total_signals = buy_signals + sell_signals + neutral_signals
            signal_strength = 0.0
            confidence = 0.5
            
            if total_signals > 0:
                # Tính độ mạnh tín hiệu (0-10)
                if overall_signal == "Mua":
                    signal_strength = buy_signals / total_signals * 10
                    confidence = buy_signals / total_signals
                elif overall_signal == "Bán":
                    signal_strength = sell_signals / total_signals * 10
                    confidence = sell_signals / total_signals
                
                # Xác định độ mạnh bằng chữ
                if buy_signals / total_signals > 0.7 or sell_signals / total_signals > 0.7:
                    strength = "Rất mạnh"
                elif buy_signals / total_signals > 0.5 or sell_signals / total_signals > 0.5:
                    strength = "Mạnh"
                else:
                    strength = "Trung bình"
            else:
                strength = "Trung bình"
                signal_strength = 0.0
                confidence = 0.5
            
            # Tính khối lượng trung bình
            avg_volume = df["volume"].mean()
            current_volume = df["volume"].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Tính biến động
            volatility = df["atr"].iloc[-1] / current_price * 100
            
            # Danh sách các chỉ báo
            indicators = [
                {"name": "RSI", "value": rsi_value, "signal": rsi_signal},
                {"name": "MACD", "value": df["macd"].iloc[-1], "signal": macd_signal},
                {"name": "Bollinger Bands", "value": f"Upper: {df['bb_upper'].iloc[-1]:.2f}, Lower: {df['bb_lower'].iloc[-1]:.2f}", "signal": bb_signal},
                {"name": "SMA20", "value": df["sma20"].iloc[-1], "signal": "Trung lập"},
                {"name": "SMA50", "value": df["sma50"].iloc[-1], "signal": "Trung lập"},
                {"name": "SMA200", "value": df["sma200"].iloc[-1], "signal": "Trung lập"},
                {"name": "Khối lượng", "value": current_volume, "signal": "Cao" if volume_ratio > 1.5 else "Thấp" if volume_ratio < 0.5 else "Trung bình"},
                {"name": "Biến động", "value": f"{volatility:.2f}%", "signal": "Cao" if volatility > 5 else "Thấp" if volatility < 1 else "Trung bình"}
            ]
            
            # Kết quả
            result = {
                "status": "success",
                "symbol": symbol,
                "interval": interval,
                "price": current_price,
                "overall_signal": overall_signal,
                "strength": strength,
                "signal_strength": signal_strength,
                "confidence": confidence,
                "short_term_trend": short_term_trend,
                "mid_term_trend": mid_term_trend,
                "long_term_trend": long_term_trend,
                "indicators": indicators,
                "support_resistance": support_resistance,
                "volume_ratio": volume_ratio,
                "volatility": volatility
            }
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi phân tích kỹ thuật: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi phân tích kỹ thuật: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        """
        Lấy tâm lý thị trường
        
        :return: Dict với tâm lý thị trường
        """
        try:
            # Lấy dữ liệu Bitcoin
            btc_data = self.get_historical_data("BTCUSDT", "1d", 30)
            
            if btc_data.empty:
                return {"status": "error", "message": "Không thể lấy dữ liệu Bitcoin"}
            
            # Tính tổng khối lượng
            total_volume = btc_data["volume"].sum()
            
            # Tính biến động
            btc_volatility = btc_data["close"].pct_change().std() * 100
            
            # Tính xu hướng
            btc_trend = ""
            if btc_data["close"].iloc[-1] > btc_data["close"].iloc[-7]:
                btc_trend = "Tăng"
            elif btc_data["close"].iloc[-1] < btc_data["close"].iloc[-7]:
                btc_trend = "Giảm"
            else:
                btc_trend = "Sideway"
            
            # Phân tích dữ liệu thị trường
            market_data = self.get_market_overview()
            
            if market_data.get("status") != "success":
                return {"status": "error", "message": "Không thể lấy dữ liệu thị trường"}
            
            # Tính tỷ lệ tăng/giảm
            up_count = 0
            down_count = 0
            
            for coin in market_data.get("data", []):
                if coin.get("change_24h", 0) > 0:
                    up_count += 1
                elif coin.get("change_24h", 0) < 0:
                    down_count += 1
            
            total_coins = up_count + down_count
            up_percent = up_count / total_coins * 100 if total_coins > 0 else 0
            
            # Xác định tâm lý thị trường
            sentiment = ""
            if up_percent > 70:
                sentiment = "Rất tích cực"
            elif up_percent > 50:
                sentiment = "Tích cực"
            elif up_percent > 30:
                sentiment = "Trung lập"
            elif up_percent > 10:
                sentiment = "Tiêu cực"
            else:
                sentiment = "Rất tiêu cực"
            
            # Kết quả
            result = {
                "status": "success",
                "sentiment": sentiment,
                "btc_trend": btc_trend,
                "btc_volatility": btc_volatility,
                "up_percent": up_percent,
                "total_coins": total_coins,
                "up_count": up_count,
                "down_count": down_count
            }
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi lấy tâm lý thị trường: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi lấy tâm lý thị trường: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_market_correlation(self) -> Dict[str, Any]:
        """
        Tính tương quan giữa các đồng tiền
        
        :return: Dict với tương quan
        """
        try:
            # Lấy dữ liệu cho các đồng tiền
            all_data = {}
            
            for symbol in self.symbols:
                data = self.get_historical_data(symbol, "1d", 30)
                
                if not data.empty:
                    all_data[symbol] = data["close"]
            
            if not all_data:
                return {"status": "error", "message": "Không thể lấy dữ liệu cho các đồng tiền"}
            
            # Tính tương quan
            price_df = pd.DataFrame(all_data)
            correlation = price_df.corr()
            
            # Chuyển đổi ma trận tương quan thành danh sách
            correlations = []
            
            for i in range(len(self.symbols)):
                for j in range(i + 1, len(self.symbols)):
                    if self.symbols[i] in correlation.index and self.symbols[j] in correlation.columns:
                        corr_value = correlation.loc[self.symbols[i], self.symbols[j]]
                        
                        correlations.append({
                            "symbol1": self.symbols[i],
                            "symbol2": self.symbols[j],
                            "correlation": corr_value
                        })
            
            # Sắp xếp theo tương quan giảm dần
            correlations = sorted(correlations, key=lambda x: abs(x["correlation"]), reverse=True)
            
            # Tính tương quan với Bitcoin
            btc_correlations = []
            
            for symbol in self.symbols:
                if symbol != "BTCUSDT" and symbol in correlation.index and "BTCUSDT" in correlation.columns:
                    corr_value = correlation.loc[symbol, "BTCUSDT"]
                    
                    btc_correlations.append({
                        "symbol": symbol,
                        "correlation": corr_value
                    })
            
            # Sắp xếp theo tương quan giảm dần
            btc_correlations = sorted(btc_correlations, key=lambda x: abs(x["correlation"]), reverse=True)
            
            # Kết quả
            result = {
                "status": "success",
                "correlations": correlations,
                "btc_correlations": btc_correlations
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi tính tương quan: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def scan_trading_opportunities(self) -> Dict[str, Any]:
        """
        Quét cơ hội giao dịch
        
        :return: Dict với các cơ hội giao dịch
        """
        try:
            opportunities = []
            
            # Quét các cặp giao dịch
            for symbol in self.symbols:
                # Phân tích kỹ thuật
                analysis = self.analyze_technical(symbol, "1h")
                
                if analysis.get("status") != "success":
                    continue
                
                # Kiểm tra các điều kiện
                overall_signal = analysis.get("overall_signal", "")
                strength = analysis.get("strength", "")
                short_term_trend = analysis.get("short_term_trend", "")
                mid_term_trend = analysis.get("mid_term_trend", "")
                
                # Kiểm tra thêm các chỉ báo cụ thể
                rsi = analysis.get("rsi", 50)
                macd_signal = analysis.get("macd_signal", "")
                
                logger.info(f"Phân tích {symbol}: Tín hiệu={overall_signal}, Mạnh={strength}, Trend={short_term_trend}, RSI={rsi}")
                
                # Xác định cơ hội giao dịch với điều kiện nới lỏng hơn
                opportunity = None
                
                # Cơ hội LONG
                if (overall_signal == "Mua" and strength in ["Mạnh", "Rất mạnh", "Trung bình"] and 
                    (short_term_trend == "Tăng" or (mid_term_trend == "Tăng" and short_term_trend != "Giảm"))):
                    opportunity = {
                        "symbol": symbol,
                        "signal": "LONG",
                        "side": "BUY",
                        "strength": strength,
                        "price": analysis.get("price", 0),
                        "signal_strength": float(analysis.get("signal_strength", 0)),
                        "confidence": float(analysis.get("confidence", 0.7)),
                        "entry_price": float(analysis.get("price", 0)),
                        "reason": f"Tín hiệu {overall_signal} {strength}, xu hướng ngắn hạn {short_term_trend}"
                    }
                # Cơ hội SHORT
                elif (overall_signal == "Bán" and strength in ["Mạnh", "Rất mạnh", "Trung bình"] and 
                      (short_term_trend == "Giảm" or (mid_term_trend == "Giảm" and short_term_trend != "Tăng"))):
                    opportunity = {
                        "symbol": symbol,
                        "signal": "SHORT",
                        "side": "SELL",
                        "strength": strength, 
                        "price": analysis.get("price", 0),
                        "signal_strength": float(analysis.get("signal_strength", 0)),
                        "confidence": float(analysis.get("confidence", 0.7)),
                        "entry_price": float(analysis.get("price", 0)),
                        "reason": f"Tín hiệu {overall_signal} {strength}, xu hướng ngắn hạn {short_term_trend}"
                    }
                
                # Nếu tìm thấy cơ hội, thêm vào danh sách
                if opportunity:
                    # Tính Stop Loss và Take Profit
                    if opportunity["signal"] == "LONG":
                        # Tìm mức hỗ trợ gần nhất dưới giá hiện tại
                        support_levels = []
                        for sr in analysis.get("support_resistance", []):
                            if sr.get("type") == "Hỗ trợ" and sr.get("value") < opportunity["price"]:
                                support_levels.append(sr.get("value"))
                        
                        # Nếu tìm thấy mức hỗ trợ, sử dụng làm Stop Loss
                        if support_levels:
                            # Sắp xếp giảm dần để lấy mức hỗ trợ gần nhất
                            support_levels.sort(reverse=True)
                            stop_loss = support_levels[0]
                        else:
                            # Nếu không tìm thấy, sử dụng 1.5% dưới giá hiện tại
                            stop_loss = opportunity["price"] * 0.985
                        
                        # Take Profit: 3% trên giá hiện tại hoặc mức kháng cự gần nhất
                        take_profit = opportunity["price"] * 1.03
                    else:  # SHORT
                        # Tìm mức kháng cự gần nhất trên giá hiện tại
                        resistance_levels = []
                        for sr in analysis.get("support_resistance", []):
                            if sr.get("type") == "Kháng cự" and sr.get("value") > opportunity["price"]:
                                resistance_levels.append(sr.get("value"))
                        
                        # Nếu tìm thấy mức kháng cự, sử dụng làm Stop Loss
                        if resistance_levels:
                            # Sắp xếp tăng dần để lấy mức kháng cự gần nhất
                            resistance_levels.sort()
                            stop_loss = resistance_levels[0]
                        else:
                            # Nếu không tìm thấy, sử dụng 1.5% trên giá hiện tại
                            stop_loss = opportunity["price"] * 1.015
                        
                        # Take Profit: 3% dưới giá hiện tại hoặc mức hỗ trợ gần nhất
                        take_profit = opportunity["price"] * 0.97
                    
                    # Thêm Stop Loss và Take Profit vào cơ hội
                    opportunity["stop_loss"] = stop_loss
                    opportunity["take_profit"] = take_profit
                    opportunity["risk_reward_ratio"] = abs(opportunity["price"] - take_profit) / abs(opportunity["price"] - stop_loss)
                    
                    # Thêm vào danh sách
                    opportunities.append(opportunity)
            
            # Sắp xếp cơ hội theo tỷ lệ risk/reward
            opportunities = sorted(opportunities, key=lambda x: x.get("risk_reward_ratio", 0), reverse=True)
            
            # Kết quả
            result = {
                "status": "success",
                "opportunities": opportunities,
                "count": len(opportunities)
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi quét cơ hội giao dịch: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def get_price_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        Dự đoán giá
        
        :param symbol: Cặp giao dịch
        :return: Dict với dự đoán giá
        """
        try:
            # Lấy dữ liệu lịch sử
            df = self.get_historical_data(symbol, "1d", 60)
            
            if df.empty:
                return {"status": "error", "message": f"Không thể lấy dữ liệu lịch sử cho {symbol}"}
            
            # Lấy giá hiện tại
            current_price = df["close"].iloc[-1]
            
            # Tính các chỉ báo kỹ thuật
            df["sma20"] = self.calculate_sma(df, 20)
            df["sma50"] = self.calculate_sma(df, 50)
            df["sma200"] = self.calculate_sma(df, 200)
            
            df["rsi"] = self.calculate_rsi(df)
            
            macd, signal, histogram = self.calculate_macd(df)
            df["macd"] = macd
            df["macd_signal"] = signal
            df["macd_histogram"] = histogram
            
            upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df)
            df["bb_upper"] = upper_band
            df["bb_middle"] = middle_band
            df["bb_lower"] = lower_band
            
            # Tính độ lệch chuẩn hàng ngày
            daily_returns = df["close"].pct_change()
            daily_volatility = daily_returns.std()
            
            # Tính giá dự đoán 7 ngày
            prediction_7d = current_price * (1 + np.random.normal(0, daily_volatility * np.sqrt(7)))
            
            # Tính giá dự đoán 30 ngày
            prediction_30d = current_price * (1 + np.random.normal(0, daily_volatility * np.sqrt(30)))
            
            # Tính biến động
            volatility = daily_volatility * 100
            
            # Mô hình dự đoán đơn giản
            # Sử dụng xu hướng hiện tại để dự đoán
            trend = 0
            if df["sma20"].iloc[-1] > df["sma20"].iloc[-2]:
                trend += 1
            elif df["sma20"].iloc[-1] < df["sma20"].iloc[-2]:
                trend -= 1
            
            if df["sma50"].iloc[-1] > df["sma50"].iloc[-2]:
                trend += 1
            elif df["sma50"].iloc[-1] < df["sma50"].iloc[-2]:
                trend -= 1
            
            if df["rsi"].iloc[-1] > 50:
                trend += 1
            elif df["rsi"].iloc[-1] < 50:
                trend -= 1
            
            if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1]:
                trend += 1
            elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1]:
                trend -= 1
            
            # Điều chỉnh dự đoán dựa trên xu hướng
            prediction_7d *= (1 + trend * 0.01)
            prediction_30d *= (1 + trend * 0.02)
            
            # Dự đoán xu hướng
            predicted_trend = ""
            if trend > 0:
                predicted_trend = "Tăng"
            elif trend < 0:
                predicted_trend = "Giảm"
            else:
                predicted_trend = "Sideway"
            
            # Kết quả
            result = {
                "status": "success",
                "symbol": symbol,
                "current_price": current_price,
                "prediction_7d": prediction_7d,
                "prediction_30d": prediction_30d,
                "volatility": volatility,
                "predicted_trend": predicted_trend,
                "confidence": abs(trend) / 4 * 100  # Độ tin cậy từ 0-100%
            }
            
            return result
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi khi dự đoán giá: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        except Exception as e:
            logger.error(f"Lỗi không xác định khi dự đoán giá: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}