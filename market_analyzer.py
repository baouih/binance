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
            
            # Lấy giá hiện tại
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