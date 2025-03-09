#!/usr/bin/env python3
"""
Tạo báo cáo phân tích thị trường

Module này tạo báo cáo chi tiết về tình hình thị trường, bao gồm phân tích kỹ thuật,
phân tích tâm lý và xác định các vùng quan trọng của thị trường.
"""

import os
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_report")

# Import các module cần thiết
try:
    from telegram_notify import telegram_notifier
except ImportError:
    logger.warning("Không thể import telegram_notifier")
    telegram_notifier = None

class MarketReporter:
    """Lớp tạo báo cáo phân tích thị trường"""
    
    def __init__(self, data_folder="./data", report_folder="./reports", chart_folder="./reports/charts"):
        """
        Khởi tạo Market Reporter.
        
        Args:
            data_folder (str): Thư mục chứa dữ liệu thị trường
            report_folder (str): Thư mục lưu báo cáo
            chart_folder (str): Thư mục lưu biểu đồ
        """
        self.data_folder = data_folder
        self.report_folder = report_folder
        self.chart_folder = chart_folder
        
        # Tạo thư mục nếu chưa tồn tại
        for folder in [data_folder, report_folder, chart_folder]:
            os.makedirs(folder, exist_ok=True)
    
    def load_market_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """
        Tải dữ liệu thị trường.
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            
        Returns:
            pd.DataFrame: DataFrame chứa dữ liệu thị trường
        """
        try:
            # Cấu trúc tên file: symbol_timeframe_ohlcv.json
            file_path = os.path.join(self.data_folder, f"{symbol}_{timeframe}_ohlcv.json")
            
            if not os.path.exists(file_path):
                logger.warning(f"Không tìm thấy dữ liệu cho {symbol} ({timeframe})")
                return pd.DataFrame()
            
            # Đọc dữ liệu từ file JSON
            with open(file_path, "r") as f:
                data = json.load(f)
            
            # Chuyển đổi sang DataFrame
            df = pd.DataFrame(data)
            
            # Đảm bảo có cột timestamp
            if "timestamp" not in df.columns and "time" in df.columns:
                df["timestamp"] = df["time"]
            
            # Chuyển đổi timestamp thành datetime
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu thị trường {symbol} ({timeframe}): {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            pd.DataFrame: DataFrame với các chỉ báo đã tính
        """
        if df.empty:
            return df
        
        # Tạo bản sao để tránh cảnh báo SettingWithCopyWarning
        df = df.copy()
        
        # Định nghĩa các cột cần có
        required_columns = ["open", "high", "low", "close", "volume"]
        
        # Kiểm tra các cột cần thiết
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Không tìm thấy cột {col} trong dữ liệu")
                return df
        
        try:
            # Tính SMA
            df["sma20"] = df["close"].rolling(window=20).mean()
            df["sma50"] = df["close"].rolling(window=50).mean()
            df["sma200"] = df["close"].rolling(window=200).mean()
            
            # Tính EMA
            df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
            df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
            
            # Tính RSI
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df["rsi"] = 100 - (100 / (1 + rs))
            
            # Tính MACD
            ema12 = df["close"].ewm(span=12, adjust=False).mean()
            ema26 = df["close"].ewm(span=26, adjust=False).mean()
            df["macd"] = ema12 - ema26
            df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
            df["macd_hist"] = df["macd"] - df["macd_signal"]
            
            # Tính Bollinger Bands
            df["bb_middle"] = df["close"].rolling(window=20).mean()
            df["bb_std"] = df["close"].rolling(window=20).std()
            df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
            df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]
            
            # Tính khối lượng trung bình
            df["volume_sma20"] = df["volume"].rolling(window=20).mean()
            df["volume_ratio"] = df["volume"] / df["volume_sma20"]
            
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi tính toán chỉ báo: {e}")
            return df
    
    def identify_support_resistance(self, df: pd.DataFrame, window: int = 20, sensitivity: float = 0.02) -> Tuple[List[float], List[float]]:
        """
        Xác định các vùng hỗ trợ và kháng cự.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            window (int): Kích thước cửa sổ để xác định cực trị
            sensitivity (float): Độ nhạy cho việc gom nhóm mức giá
            
        Returns:
            Tuple[List[float], List[float]]: Các mức hỗ trợ và kháng cự
        """
        if df.empty or "close" not in df.columns:
            return [], []
        
        supports = []
        resistances = []
        
        try:
            # Tìm các điểm cực tiểu cục bộ (hỗ trợ tiềm năng)
            for i in range(window, len(df) - window):
                if all(df["low"].iloc[i] <= df["low"].iloc[i-j] for j in range(1, window)) and \
                   all(df["low"].iloc[i] <= df["low"].iloc[i+j] for j in range(1, window)):
                    supports.append(df["low"].iloc[i])
            
            # Tìm các điểm cực đại cục bộ (kháng cự tiềm năng)
            for i in range(window, len(df) - window):
                if all(df["high"].iloc[i] >= df["high"].iloc[i-j] for j in range(1, window)) and \
                   all(df["high"].iloc[i] >= df["high"].iloc[i+j] for j in range(1, window)):
                    resistances.append(df["high"].iloc[i])
            
            # Gom nhóm các mức giá gần nhau
            grouped_supports = self._group_price_levels(supports, sensitivity)
            grouped_resistances = self._group_price_levels(resistances, sensitivity)
            
            return grouped_supports, grouped_resistances
        
        except Exception as e:
            logger.error(f"Lỗi khi xác định hỗ trợ/kháng cự: {e}")
            return [], []
    
    def _group_price_levels(self, price_levels: List[float], sensitivity: float) -> List[float]:
        """
        Gom nhóm các mức giá gần nhau.
        
        Args:
            price_levels (List[float]): Danh sách các mức giá
            sensitivity (float): Độ nhạy cho việc gom nhóm
            
        Returns:
            List[float]: Danh sách các mức giá đã gom nhóm
        """
        if not price_levels:
            return []
        
        # Sắp xếp các mức giá
        sorted_levels = sorted(price_levels)
        
        # Khởi tạo các nhóm
        grouped_levels = []
        current_group = [sorted_levels[0]]
        
        # Phân nhóm các mức giá
        for level in sorted_levels[1:]:
            last_level = current_group[-1]
            if (level - last_level) / last_level <= sensitivity:
                # Mức giá đủ gần để gộp vào nhóm hiện tại
                current_group.append(level)
            else:
                # Tạo nhóm mới
                grouped_levels.append(sum(current_group) / len(current_group))
                current_group = [level]
        
        # Thêm nhóm cuối cùng
        if current_group:
            grouped_levels.append(sum(current_group) / len(current_group))
        
        return grouped_levels
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        Phân tích xu hướng thị trường.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict: Kết quả phân tích xu hướng
        """
        if df.empty:
            return {
                "trend": "unknown",
                "strength": 0,
                "description": "Không có dữ liệu để phân tích"
            }
        
        result = {
            "trend": "sideways",
            "strength": 0,
            "description": "Thị trường đang đi ngang"
        }
        
        try:
            # Lấy dữ liệu gần đây nhất
            recent_data = df.tail(50)
            
            # Kiểm tra xu hướng dựa trên SMA
            if "sma20" in recent_data.columns and "sma50" in recent_data.columns:
                last_row = recent_data.iloc[-1]
                
                # Xu hướng dựa trên SMA
                if last_row["sma20"] > last_row["sma50"]:
                    trend_score = 1  # Uptrend
                elif last_row["sma20"] < last_row["sma50"]:
                    trend_score = -1  # Downtrend
                else:
                    trend_score = 0  # Sideways
                
                # Tăng cường bằng SMA dài hạn nếu có
                if "sma200" in recent_data.columns:
                    if last_row["close"] > last_row["sma200"]:
                        trend_score += 0.5
                    elif last_row["close"] < last_row["sma200"]:
                        trend_score -= 0.5
                
                # Kiểm tra RSI
                if "rsi" in recent_data.columns:
                    rsi = last_row["rsi"]
                    if rsi > 70:
                        trend_score -= 0.3  # Quá mua
                    elif rsi < 30:
                        trend_score += 0.3  # Quá bán
                
                # Kiểm tra MACD
                if "macd" in recent_data.columns and "macd_signal" in recent_data.columns:
                    if last_row["macd"] > last_row["macd_signal"]:
                        trend_score += 0.3
                    elif last_row["macd"] < last_row["macd_signal"]:
                        trend_score -= 0.3
                
                # Xác định xu hướng và độ mạnh
                if trend_score >= 1:
                    result["trend"] = "uptrend"
                    result["strength"] = min(trend_score, 2)
                    result["description"] = "Thị trường đang trong xu hướng tăng"
                elif trend_score <= -1:
                    result["trend"] = "downtrend"
                    result["strength"] = min(abs(trend_score), 2)
                    result["description"] = "Thị trường đang trong xu hướng giảm"
                else:
                    result["trend"] = "sideways"
                    result["strength"] = 0.5
                    result["description"] = "Thị trường đang đi ngang, không có xu hướng rõ ràng"
            
            return result
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích xu hướng: {e}")
            return result
    
    def create_chart(self, df: pd.DataFrame, symbol: str, timeframe: str, 
                    supports: List[float] = None, resistances: List[float] = None) -> str:
        """
        Tạo biểu đồ phân tích kỹ thuật.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            symbol (str): Mã cặp giao dịch
            timeframe (str): Khung thời gian
            supports (List[float], optional): Các mức hỗ trợ
            resistances (List[float], optional): Các mức kháng cự
            
        Returns:
            str: Đường dẫn đến file biểu đồ
        """
        if df.empty:
            logger.warning(f"Không có dữ liệu để tạo biểu đồ cho {symbol}")
            return ""
        
        try:
            # Lấy dữ liệu gần đây
            recent_data = df.tail(100).copy()
            
            # Tạo biểu đồ
            fig, axes = plt.subplots(3, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [5, 2, 2]})
            
            # Thiết lập style
            plt.style.use('dark_background')
            
            # Biểu đồ giá và các đường MA
            ax1 = axes[0]
            ax1.plot(recent_data.index, recent_data["close"], label="Giá đóng cửa", color="white")
            
            if "sma20" in recent_data.columns:
                ax1.plot(recent_data.index, recent_data["sma20"], label="SMA 20", color="green")
            
            if "sma50" in recent_data.columns:
                ax1.plot(recent_data.index, recent_data["sma50"], label="SMA 50", color="blue")
            
            if "sma200" in recent_data.columns:
                ax1.plot(recent_data.index, recent_data["sma200"], label="SMA 200", color="red", alpha=0.7)
            
            # Bollinger Bands
            if all(band in recent_data.columns for band in ["bb_upper", "bb_middle", "bb_lower"]):
                ax1.plot(recent_data.index, recent_data["bb_upper"], linestyle="--", color="gray", alpha=0.7)
                ax1.plot(recent_data.index, recent_data["bb_middle"], linestyle="--", color="gray", alpha=0.5)
                ax1.plot(recent_data.index, recent_data["bb_lower"], linestyle="--", color="gray", alpha=0.7)
            
            # Vẽ các mức hỗ trợ và kháng cự
            if supports:
                for level in supports:
                    ax1.axhline(y=level, linestyle="-.", color="green", alpha=0.6)
            
            if resistances:
                for level in resistances:
                    ax1.axhline(y=level, linestyle="-.", color="red", alpha=0.6)
            
            ax1.set_title(f"{symbol} - {timeframe} - Phân tích kỹ thuật")
            ax1.set_ylabel("Giá")
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc="upper left")
            
            # Định dạng trục x
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            # Biểu đồ RSI
            ax2 = axes[1]
            if "rsi" in recent_data.columns:
                ax2.plot(recent_data.index, recent_data["rsi"], color="purple")
                ax2.axhline(y=70, linestyle="--", color="red", alpha=0.5)
                ax2.axhline(y=30, linestyle="--", color="green", alpha=0.5)
                ax2.axhline(y=50, linestyle="-", color="gray", alpha=0.5)
                ax2.set_ylabel("RSI")
                ax2.set_ylim(0, 100)
                ax2.grid(True, alpha=0.3)
            
            # Biểu đồ MACD
            ax3 = axes[2]
            if all(macd in recent_data.columns for macd in ["macd", "macd_signal", "macd_hist"]):
                ax3.plot(recent_data.index, recent_data["macd"], label="MACD", color="blue")
                ax3.plot(recent_data.index, recent_data["macd_signal"], label="Signal", color="red")
                
                # Vẽ histogram
                for i in range(len(recent_data) - 1):
                    value = recent_data["macd_hist"].iloc[i]
                    color = "green" if value > 0 else "red"
                    ax3.bar(recent_data.index[i], value, width=0.7, color=color, alpha=0.5)
                
                ax3.set_ylabel("MACD")
                ax3.axhline(y=0, linestyle="-", color="gray", alpha=0.5)
                ax3.grid(True, alpha=0.3)
                ax3.legend(loc="upper left")
            
            # Điều chỉnh khoảng cách giữa các biểu đồ
            plt.tight_layout()
            
            # Xoay nhãn trục x
            for ax in axes:
                ax.tick_params(axis='x', rotation=45)
            
            # Lưu biểu đồ
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{symbol}_{timeframe}_analysis_{timestamp}.png"
            file_path = os.path.join(self.chart_folder, file_name)
            
            plt.savefig(file_path, bbox_inches="tight", dpi=150)
            plt.close(fig)
            
            logger.info(f"Đã tạo biểu đồ phân tích cho {symbol}_{timeframe}: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ: {e}")
            return ""
    
    def generate_market_report(self, symbol: str, timeframes: List[str] = None) -> Dict:
        """
        Tạo báo cáo phân tích thị trường.
        
        Args:
            symbol (str): Mã cặp giao dịch
            timeframes (List[str], optional): Danh sách khung thời gian
            
        Returns:
            Dict: Báo cáo phân tích thị trường
        """
        if timeframes is None:
            timeframes = ["1h", "4h", "1d"]
        
        logger.info(f"Đang tạo báo cáo phân tích thị trường cho {symbol}")
        
        report = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "timeframes": {},
            "charts": {},
            "summary": {
                "trend": "unknown",
                "sentiment": "neutral",
                "recommendation": "hold",
                "key_levels": {
                    "supports": [],
                    "resistances": []
                }
            }
        }
        
        try:
            # Phân tích cho từng khung thời gian
            for timeframe in timeframes:
                # Tải dữ liệu
                df = self.load_market_data(symbol, timeframe)
                
                # Bỏ qua nếu không có dữ liệu
                if df.empty:
                    continue
                
                # Tính toán chỉ báo
                df = self.calculate_indicators(df)
                
                # Xác định hỗ trợ/kháng cự
                supports, resistances = self.identify_support_resistance(df)
                
                # Phân tích xu hướng
                trend_analysis = self.analyze_trend(df)
                
                # Tạo biểu đồ
                chart_path = self.create_chart(df, symbol, timeframe, supports, resistances)
                
                # Lưu kết quả
                report["timeframes"][timeframe] = {
                    "trend": trend_analysis,
                    "supports": supports,
                    "resistances": resistances,
                    "last_price": float(df["close"].iloc[-1]) if "close" in df.columns else None,
                    "indicators": {
                        "rsi": float(df["rsi"].iloc[-1]) if "rsi" in df.columns else None,
                        "macd": float(df["macd"].iloc[-1]) if "macd" in df.columns else None,
                        "macd_signal": float(df["macd_signal"].iloc[-1]) if "macd_signal" in df.columns else None,
                        "sma20": float(df["sma20"].iloc[-1]) if "sma20" in df.columns else None,
                        "sma50": float(df["sma50"].iloc[-1]) if "sma50" in df.columns else None,
                        "sma200": float(df["sma200"].iloc[-1]) if "sma200" in df.columns else None
                    }
                }
                
                # Lưu đường dẫn biểu đồ
                if chart_path:
                    report["charts"][timeframe] = chart_path
            
            # Tạo tóm tắt
            self._generate_summary(report)
            
            return report
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo phân tích thị trường: {e}")
            return report
    
    def _generate_summary(self, report: Dict) -> None:
        """
        Tạo tóm tắt phân tích.
        
        Args:
            report (Dict): Báo cáo phân tích
        """
        try:
            timeframes = report.get("timeframes", {})
            
            if not timeframes:
                report["summary"]["description"] = "Không có dữ liệu phân tích"
                return
            
            # Tính điểm xu hướng
            trend_scores = []
            for tf, data in timeframes.items():
                trend = data.get("trend", {})
                trend_type = trend.get("trend", "sideways")
                strength = trend.get("strength", 0)
                
                # Tính điểm
                score = 0
                if trend_type == "uptrend":
                    score = strength
                elif trend_type == "downtrend":
                    score = -strength
                
                # Áp dụng trọng số cho các khung thời gian khác nhau
                if tf == "1d":
                    score *= 3
                elif tf == "4h":
                    score *= 2
                
                trend_scores.append(score)
            
            # Tính điểm trung bình
            avg_trend_score = sum(trend_scores) / len(trend_scores)
            
            # Xác định xu hướng chung
            if avg_trend_score >= 1:
                report["summary"]["trend"] = "uptrend"
                report["summary"]["sentiment"] = "bullish"
            elif avg_trend_score <= -1:
                report["summary"]["trend"] = "downtrend"
                report["summary"]["sentiment"] = "bearish"
            else:
                report["summary"]["trend"] = "sideways"
                report["summary"]["sentiment"] = "neutral"
            
            # Xác định khuyến nghị
            if report["summary"]["trend"] == "uptrend":
                report["summary"]["recommendation"] = "buy"
            elif report["summary"]["trend"] == "downtrend":
                report["summary"]["recommendation"] = "sell"
            else:
                report["summary"]["recommendation"] = "hold"
            
            # Tổng hợp các mức hỗ trợ/kháng cự
            all_supports = []
            all_resistances = []
            
            # Ưu tiên khung thời gian dài hơn
            for tf in ["1d", "4h", "1h"]:
                if tf in timeframes:
                    all_supports.extend(timeframes[tf].get("supports", []))
                    all_resistances.extend(timeframes[tf].get("resistances", []))
            
            # Lấy giá hiện tại
            current_price = None
            for tf in timeframes:
                if timeframes[tf].get("last_price") is not None:
                    current_price = timeframes[tf]["last_price"]
                    break
            
            # Lọc các mức gần với giá hiện tại
            if current_price is not None:
                # Hỗ trợ dưới giá hiện tại
                supports_below = [s for s in all_supports if s < current_price]
                supports_below.sort(reverse=True)  # Sắp xếp giảm dần
                
                # Kháng cự trên giá hiện tại
                resistances_above = [r for r in all_resistances if r > current_price]
                resistances_above.sort()  # Sắp xếp tăng dần
                
                # Lấy 3 mức gần nhất
                report["summary"]["key_levels"]["supports"] = supports_below[:3]
                report["summary"]["key_levels"]["resistances"] = resistances_above[:3]
            
            # Tạo mô tả
            self._create_description(report)
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo tóm tắt: {e}")
    
    def _create_description(self, report: Dict) -> None:
        """
        Tạo mô tả báo cáo.
        
        Args:
            report (Dict): Báo cáo phân tích
        """
        try:
            symbol = report.get("symbol", "")
            timeframes = report.get("timeframes", {})
            summary = report.get("summary", {})
            
            # Tìm giá hiện tại
            current_price = None
            for tf in timeframes:
                if timeframes[tf].get("last_price") is not None:
                    current_price = timeframes[tf]["last_price"]
                    break
            
            # Mô tả
            description = f"Phân tích kỹ thuật {symbol}: "
            
            # Xu hướng
            trend = summary.get("trend", "unknown")
            if trend == "uptrend":
                description += "Xu hướng TĂNG. "
            elif trend == "downtrend":
                description += "Xu hướng GIẢM. "
            else:
                description += "Đang giao dịch ĐI NGANG. "
            
            # Chỉ báo
            if timeframes and "1h" in timeframes:
                indicators = timeframes["1h"].get("indicators", {})
                
                # RSI
                rsi = indicators.get("rsi")
                if rsi is not None:
                    if rsi > 70:
                        description += "RSI quá mua (%.1f). " % rsi
                    elif rsi < 30:
                        description += "RSI quá bán (%.1f). " % rsi
                
                # MACD
                macd = indicators.get("macd")
                macd_signal = indicators.get("macd_signal")
                if macd is not None and macd_signal is not None:
                    if macd > macd_signal:
                        description += "MACD tích cực. "
                    elif macd < macd_signal:
                        description += "MACD tiêu cực. "
            
            # Các mức quan trọng
            key_levels = summary.get("key_levels", {})
            supports = key_levels.get("supports", [])
            resistances = key_levels.get("resistances", [])
            
            if current_price is not None and supports:
                closest_support = supports[0]
                description += f"Hỗ trợ gần nhất: ${closest_support:.2f}. "
            
            if current_price is not None and resistances:
                closest_resistance = resistances[0]
                description += f"Kháng cự gần nhất: ${closest_resistance:.2f}. "
            
            # Khuyến nghị
            recommendation = summary.get("recommendation", "hold")
            if recommendation == "buy":
                description += "Khuyến nghị: MUA."
            elif recommendation == "sell":
                description += "Khuyến nghị: BÁN."
            else:
                description += "Khuyến nghị: NẮM GIỮ."
            
            report["summary"]["description"] = description
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo mô tả: {e}")
            report["summary"]["description"] = "Không thể tạo mô tả phân tích"
    
    def save_report(self, report: Dict, file_name: str = None) -> str:
        """
        Lưu báo cáo phân tích thị trường.
        
        Args:
            report (Dict): Báo cáo phân tích
            file_name (str, optional): Tên file báo cáo
            
        Returns:
            str: Đường dẫn đến file báo cáo
        """
        if not report:
            return ""
        
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            symbol = report.get("symbol", "unknown")
            file_name = f"market_report_{symbol}_{timestamp}.json"
        
        file_path = os.path.join(self.report_folder, file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Đã lưu báo cáo phân tích thị trường: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu báo cáo: {e}")
            return ""
    
    def generate_text_report(self, report: Dict) -> str:
        """
        Tạo báo cáo văn bản từ báo cáo phân tích.
        
        Args:
            report (Dict): Báo cáo phân tích
            
        Returns:
            str: Nội dung báo cáo văn bản
        """
        if not report:
            return "Không có dữ liệu báo cáo"
        
        try:
            symbol = report.get("symbol", "Unknown")
            timestamp = datetime.fromisoformat(report.get("timestamp", datetime.now().isoformat()))
            timeframes = report.get("timeframes", {})
            summary = report.get("summary", {})
            
            # Tạo báo cáo văn bản
            text_report = f"BÁO CÁO PHÂN TÍCH THỊ TRƯỜNG: {symbol}\n"
            text_report += f"Thời gian: {timestamp.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            
            # Tóm tắt
            text_report += "TÓM TẮT:\n"
            text_report += f"{summary.get('description', 'Không có mô tả')}\n\n"
            
            # Các mức quan trọng
            key_levels = summary.get("key_levels", {})
            supports = key_levels.get("supports", [])
            resistances = key_levels.get("resistances", [])
            
            text_report += "CÁC MỨC QUAN TRỌNG:\n"
            
            if supports:
                text_report += "Hỗ trợ:\n"
                for i, level in enumerate(supports):
                    text_report += f"  {i+1}. ${level:.2f}\n"
            else:
                text_report += "Không có mức hỗ trợ quan trọng\n"
            
            if resistances:
                text_report += "Kháng cự:\n"
                for i, level in enumerate(resistances):
                    text_report += f"  {i+1}. ${level:.2f}\n"
            else:
                text_report += "Không có mức kháng cự quan trọng\n"
            
            text_report += "\n"
            
            # Phân tích chi tiết theo khung thời gian
            text_report += "PHÂN TÍCH CHI TIẾT:\n"
            
            for tf in ["1d", "4h", "1h"]:
                if tf in timeframes:
                    data = timeframes[tf]
                    trend = data.get("trend", {})
                    indicators = data.get("indicators", {})
                    
                    text_report += f"{tf.upper()}:\n"
                    text_report += f"  Xu hướng: {trend.get('description', 'Không xác định')}\n"
                    
                    # Giá và chỉ báo
                    text_report += f"  Giá gần nhất: ${data.get('last_price', 0):.2f}\n"
                    
                    if indicators:
                        text_report += "  Chỉ báo:\n"
                        
                        rsi = indicators.get("rsi")
                        if rsi is not None:
                            rsi_status = "Quá mua" if rsi > 70 else "Quá bán" if rsi < 30 else "Trung tính"
                            text_report += f"    RSI: {rsi:.2f} ({rsi_status})\n"
                        
                        macd = indicators.get("macd")
                        macd_signal = indicators.get("macd_signal")
                        if macd is not None and macd_signal is not None:
                            macd_status = "Tích cực" if macd > macd_signal else "Tiêu cực"
                            text_report += f"    MACD: {macd:.6f} (Signal: {macd_signal:.6f}) - {macd_status}\n"
                        
                        sma20 = indicators.get("sma20")
                        sma50 = indicators.get("sma50")
                        if sma20 is not None and sma50 is not None:
                            sma_status = "Tích cực" if sma20 > sma50 else "Tiêu cực"
                            text_report += f"    SMA: SMA20 ({sma20:.2f}) vs SMA50 ({sma50:.2f}) - {sma_status}\n"
                    
                    text_report += "\n"
            
            # Khuyến nghị
            text_report += "KHUYẾN NGHỊ:\n"
            recommendation = summary.get("recommendation", "hold")
            
            if recommendation == "buy":
                text_report += "MUA - Thị trường đang trong xu hướng tăng, có thể xem xét mở vị thế mua\n"
            elif recommendation == "sell":
                text_report += "BÁN - Thị trường đang trong xu hướng giảm, có thể xem xét mở vị thế bán\n"
            else:
                text_report += "NẮM GIỮ - Thị trường không có xu hướng rõ ràng, nên chờ tín hiệu rõ ràng hơn\n"
            
            return text_report
        
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo văn bản: {e}")
            return "Lỗi khi tạo báo cáo văn bản"
    
    def send_telegram_notification(self, report: Dict) -> bool:
        """
        Gửi báo cáo phân tích thị trường qua Telegram.
        
        Args:
            report (Dict): Báo cáo phân tích
            
        Returns:
            bool: True nếu gửi thành công, False nếu không
        """
        if not telegram_notifier or not telegram_notifier.enabled:
            logger.warning("Telegram notifier không được kích hoạt")
            return False
        
        try:
            symbol = report.get("symbol", "Unknown")
            summary = report.get("summary", {})
            
            # Tạo tin nhắn
            message = f"<b>📊 BÁO CÁO THỊ TRƯỜNG: {symbol}</b>\n\n"
            
            # Mô tả
            description = summary.get("description", "")
            if description:
                message += f"{description}\n\n"
            
            # Các mức quan trọng
            key_levels = summary.get("key_levels", {})
            supports = key_levels.get("supports", [])
            resistances = key_levels.get("resistances", [])
            
            message += "<b>CÁC MỨC QUAN TRỌNG:</b>\n"
            
            if supports:
                message += "🟢 <b>Hỗ trợ:</b>\n"
                for i, level in enumerate(supports[:3]):  # Chỉ hiển thị 3 mức đầu tiên
                    message += f"  {i+1}. ${level:.2f}\n"
            
            if resistances:
                message += "🔴 <b>Kháng cự:</b>\n"
                for i, level in enumerate(resistances[:3]):  # Chỉ hiển thị 3 mức đầu tiên
                    message += f"  {i+1}. ${level:.2f}\n"
            
            message += "\n"
            
            # Xu hướng
            trend = summary.get("trend", "unknown")
            sentiment = summary.get("sentiment", "neutral")
            
            if trend == "uptrend":
                message += "📈 <b>Xu hướng:</b> TĂNG\n"
            elif trend == "downtrend":
                message += "📉 <b>Xu hướng:</b> GIẢM\n"
            else:
                message += "↔️ <b>Xu hướng:</b> ĐI NGANG\n"
            
            # Khuyến nghị
            recommendation = summary.get("recommendation", "hold")
            
            if recommendation == "buy":
                message += "✅ <b>Khuyến nghị:</b> MUA\n"
            elif recommendation == "sell":
                message += "❌ <b>Khuyến nghị:</b> BÁN\n"
            else:
                message += "⏹️ <b>Khuyến nghị:</b> NẮM GIỮ\n"
            
            # Gửi tin nhắn
            sent = telegram_notifier.send_message(message)
            
            # Gửi biểu đồ (nếu có)
            charts = report.get("charts", {})
            if charts and "1d" in charts:
                # TODO: Nếu muốn gửi ảnh qua Telegram, cần phát triển thêm chức năng gửi ảnh
                pass
            
            return sent
        
        except Exception as e:
            logger.error(f"Lỗi khi gửi báo cáo qua Telegram: {e}")
            return False

def main():
    """Hàm chính để tạo báo cáo phân tích thị trường"""
    # Tạo thư mục dữ liệu nếu chưa tồn tại
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("reports/charts", exist_ok=True)
    
    # Danh sách các cặp giao dịch cần phân tích
    symbols = ["BTCUSDT", "ETHUSDT"]
    
    # Tạo reporter
    reporter = MarketReporter()
    
    for symbol in symbols:
        # Tạo báo cáo
        report = reporter.generate_market_report(symbol, timeframes=["1h", "4h", "1d"])
        
        if report:
            # Lưu báo cáo
            report_path = reporter.save_report(report)
            
            # Tạo báo cáo văn bản
            text_report = reporter.generate_text_report(report)
            
            # Lưu báo cáo văn bản
            if text_report:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                text_report_path = os.path.join(reporter.report_folder, f"market_report_{symbol}_{timestamp}.txt")
                
                try:
                    with open(text_report_path, "w", encoding="utf-8") as f:
                        f.write(text_report)
                    
                    logger.info(f"Đã lưu báo cáo văn bản: {text_report_path}")
                except Exception as e:
                    logger.error(f"Lỗi khi lưu báo cáo văn bản: {e}")
            
            # Gửi thông báo qua Telegram
            if telegram_notifier and telegram_notifier.enabled:
                reporter.send_telegram_notification(report)
    
    print("Báo cáo phân tích thị trường đã được tạo và gửi đi")

if __name__ == "__main__":
    main()