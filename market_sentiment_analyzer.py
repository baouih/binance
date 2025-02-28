"""
Module phân tích tâm lý thị trường tiền điện tử (Market Sentiment Analysis)

Module này cung cấp các công cụ để phân tích tâm lý thị trường tiền điện tử từ nhiều
nguồn dữ liệu, bao gồm phân tích kỹ thuật, chỉ số sợ hãi và tham lam,
volume đặc biệt, và thông tin từ mạng xã hội.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from collections import defaultdict

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_sentiment_analyzer")

class MarketSentimentAnalyzer:
    """
    Lớp phân tích tâm lý thị trường tiền điện tử từ nhiều nguồn dữ liệu.
    """
    
    # Các trạng thái tâm lý thị trường
    SENTIMENT_STATES = {
        "extreme_fear": {"range": (0, 25), "description": "Vô cùng sợ hãi"},
        "fear": {"range": (25, 40), "description": "Sợ hãi"},
        "neutral": {"range": (40, 60), "description": "Trung tính"},
        "greed": {"range": (60, 75), "description": "Tham lam"},
        "extreme_greed": {"range": (75, 100), "description": "Vô cùng tham lam"}
    }
    
    def __init__(self, cache_timeout: int = 3600):
        """
        Khởi tạo bộ phân tích tâm lý thị trường.
        
        Args:
            cache_timeout (int): Thời gian hết hạn của bộ nhớ cache (giây)
        """
        self.cache_timeout = cache_timeout
        self.cache = {}
        self.last_update = {}
        
        # Lưu trữ lịch sử tâm lý
        self.sentiment_history = {
            "fear_greed_index": [],
            "technical_sentiment": defaultdict(list),
            "volume_analysis": defaultdict(list),
            "social_sentiment": defaultdict(list),
            "composite_sentiment": defaultdict(list),
        }
        
        # Chỉ số hiện tại
        self.current_sentiment = {}
        
        # Các tham số cấu hình
        self.config = {
            "technical_weight": 0.4,
            "fear_greed_weight": 0.3,
            "volume_weight": 0.2,
            "social_weight": 0.1,
            "use_fear_greed": True,
            "use_technical": True,
            "use_volume": True,
            "use_social": False,  # Mặc định tắt do cần API key
        }
        
        logger.info("Khởi tạo MarketSentimentAnalyzer")
    
    def get_fear_greed_index(self) -> Dict:
        """
        Lấy chỉ số Fear & Greed Index.
        
        Returns:
            Dict: Thông tin về chỉ số Fear & Greed hiện tại
        """
        if "fear_greed" in self.cache and (datetime.now() - self.last_update.get("fear_greed", datetime.min)).total_seconds() < self.cache_timeout:
            return self.cache["fear_greed"]
        
        try:
            # API miễn phí của Alternative.me
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    # Lấy dữ liệu mới nhất
                    latest = data["data"][0]
                    
                    # Phân loại trạng thái
                    value = int(latest["value"])
                    state = "neutral"
                    for sentiment, info in self.SENTIMENT_STATES.items():
                        if info["range"][0] <= value < info["range"][1]:
                            state = sentiment
                            break
                    
                    result = {
                        "value": value,
                        "state": state,
                        "description": self.SENTIMENT_STATES[state]["description"],
                        "timestamp": datetime.fromtimestamp(int(latest["timestamp"])).isoformat(),
                        "source": "alternative.me"
                    }
                    
                    # Cập nhật cache
                    self.cache["fear_greed"] = result
                    self.last_update["fear_greed"] = datetime.now()
                    
                    # Lưu vào lịch sử
                    self.sentiment_history["fear_greed_index"].append({
                        "timestamp": datetime.now().isoformat(),
                        "value": value,
                        "state": state
                    })
                    
                    return result
            
            # Nếu không lấy được dữ liệu mới, trả về dữ liệu cũ nếu có
            if "fear_greed" in self.cache:
                logger.warning("Sử dụng dữ liệu fear & greed từ cache do không lấy được dữ liệu mới")
                return self.cache["fear_greed"]
            
            # Nếu không có cả dữ liệu mới và cũ, trả về giá trị mặc định
            return {
                "value": 50,
                "state": "neutral",
                "description": "Trung tính (giá trị mặc định)",
                "timestamp": datetime.now().isoformat(),
                "source": "default"
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy chỉ số Fear & Greed: {str(e)}")
            
            # Trả về dữ liệu cũ nếu có
            if "fear_greed" in self.cache:
                logger.warning("Sử dụng dữ liệu fear & greed từ cache do lỗi API")
                return self.cache["fear_greed"]
            
            # Nếu không có dữ liệu cũ, trả về giá trị mặc định
            return {
                "value": 50,
                "state": "neutral",
                "description": "Trung tính (giá trị mặc định do lỗi)",
                "timestamp": datetime.now().isoformat(),
                "source": "default"
            }
    
    def analyze_technical_sentiment(self, symbol: str, dataframe: pd.DataFrame) -> Dict:
        """
        Phân tích tâm lý thị trường dựa trên dữ liệu kỹ thuật.
        
        Args:
            symbol (str): Mã cặp giao dịch
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict: Kết quả phân tích tâm lý thị trường dựa trên kỹ thuật
        """
        if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
            logger.error("DataFrame không hợp lệ cho phân tích kỹ thuật")
            return {
                "value": 50,
                "state": "neutral",
                "description": "Trung tính (không đủ dữ liệu)",
                "timestamp": datetime.now().isoformat(),
                "source": "technical_analysis",
                "details": {}
            }
        
        try:
            # Số điểm tâm lý, phạm vi 0-100
            sentiment_score = 50.0
            details = {}
            
            # 1. Phân tích RSI
            if 'rsi' in dataframe.columns:
                rsi = dataframe['rsi'].iloc[-1]
                if rsi < 30:
                    # Quá bán - dấu hiệu tích cực
                    rsi_score = 80
                elif rsi > 70:
                    # Quá mua - dấu hiệu tiêu cực
                    rsi_score = 20
                else:
                    # Trung tính, ánh xạ RSI 30-70 thành 60-40
                    rsi_score = 60 - ((rsi - 30) / 40) * 20
                
                details["rsi"] = {
                    "value": float(rsi),
                    "score": float(rsi_score),
                    "description": "Quá bán" if rsi < 30 else "Quá mua" if rsi > 70 else "Trung tính"
                }
                sentiment_score += rsi_score * 0.25  # RSI chiếm 25% trọng số
            
            # 2. Phân tích MACD
            if all(col in dataframe.columns for col in ['macd', 'macd_signal']):
                macd = dataframe['macd'].iloc[-1]
                macd_signal = dataframe['macd_signal'].iloc[-1]
                macd_hist = macd - macd_signal
                
                # Kiểm tra MACD trong 5 phiên gần nhất để phát hiện xu hướng
                recent_macd_hist = dataframe['macd'].iloc[-5:] - dataframe['macd_signal'].iloc[-5:]
                macd_trend = "bullish" if recent_macd_hist.is_monotonic_increasing else "bearish" if recent_macd_hist.is_monotonic_decreasing else "neutral"
                
                if macd_hist > 0 and macd_trend == "bullish":
                    macd_score = 80  # Rất tích cực
                elif macd_hist > 0:
                    macd_score = 65  # Tích cực
                elif macd_hist < 0 and macd_trend == "bearish":
                    macd_score = 20  # Rất tiêu cực
                elif macd_hist < 0:
                    macd_score = 35  # Tiêu cực
                else:
                    macd_score = 50  # Trung tính
                
                details["macd"] = {
                    "value": float(macd_hist),
                    "score": float(macd_score),
                    "trend": macd_trend,
                    "description": "Tích cực" if macd_hist > 0 else "Tiêu cực" if macd_hist < 0 else "Trung tính"
                }
                sentiment_score += macd_score * 0.25  # MACD chiếm 25% trọng số
            
            # 3. Phân tích xu hướng dựa trên EMA
            if all(x in dataframe.columns for x in ['ema_short', 'ema_long']):
                ema_short = dataframe['ema_short'].iloc[-1]
                ema_long = dataframe['ema_long'].iloc[-1]
                
                # Tính % chênh lệch giữa EMA ngắn và dài
                ema_diff_pct = (ema_short - ema_long) / ema_long * 100
                
                if ema_diff_pct > 3:
                    ema_score = 85  # Xu hướng tăng mạnh
                elif ema_diff_pct > 1:
                    ema_score = 70  # Xu hướng tăng
                elif ema_diff_pct < -3:
                    ema_score = 15  # Xu hướng giảm mạnh
                elif ema_diff_pct < -1:
                    ema_score = 30  # Xu hướng giảm
                else:
                    ema_score = 50  # Trung tính
                
                details["ema_trend"] = {
                    "value": float(ema_diff_pct),
                    "score": float(ema_score),
                    "description": "Xu hướng tăng mạnh" if ema_diff_pct > 3 else 
                                "Xu hướng tăng" if ema_diff_pct > 1 else 
                                "Xu hướng giảm mạnh" if ema_diff_pct < -3 else 
                                "Xu hướng giảm" if ema_diff_pct < -1 else 
                                "Trung tính"
                }
                sentiment_score += ema_score * 0.25  # Xu hướng chiếm 25% trọng số
            
            # 4. Phân tích Bollinger Bands
            if all(x in dataframe.columns for x in ['close', 'bb_upper', 'bb_lower']):
                close = dataframe['close'].iloc[-1]
                bb_upper = dataframe['bb_upper'].iloc[-1]
                bb_lower = dataframe['bb_lower'].iloc[-1]
                bb_width = (bb_upper - bb_lower) / close * 100
                
                # Vị trí giá trong band (0 = lower band, 1 = upper band)
                if bb_upper == bb_lower:  # Tránh chia cho 0
                    bb_position = 0.5
                else:
                    bb_position = (close - bb_lower) / (bb_upper - bb_lower)
                
                # Xác định tâm lý dựa trên vị trí và độ rộng band
                if bb_position < 0.2:
                    bb_score = 75  # Gần dải dưới - tín hiệu mua tiềm năng
                elif bb_position > 0.8:
                    bb_score = 25  # Gần dải trên - tín hiệu bán tiềm năng
                else:
                    bb_score = 50 - (bb_position - 0.5) * 40  # Ánh xạ tuyến tính
                
                # Hiệu chỉnh dựa trên độ rộng bands
                if bb_width > 5:  # Bands rộng = biến động cao = thêm trọng số cho tín hiệu
                    bb_score = bb_score * 0.8 + (50 if bb_score < 50 else 70 if bb_position < 0.3 else 30) * 0.2
                
                details["bollinger"] = {
                    "position": float(bb_position),
                    "width": float(bb_width),
                    "score": float(bb_score),
                    "description": "Gần dải dưới" if bb_position < 0.2 else 
                                "Gần dải trên" if bb_position > 0.8 else 
                                "Trung tâm band"
                }
                sentiment_score += bb_score * 0.25  # BB chiếm 25% trọng số
            
            # Phân loại trạng thái tâm lý
            state = "neutral"
            for sentiment, info in self.SENTIMENT_STATES.items():
                if info["range"][0] <= sentiment_score < info["range"][1]:
                    state = sentiment
                    break
            
            result = {
                "value": float(sentiment_score),
                "state": state,
                "description": self.SENTIMENT_STATES[state]["description"],
                "timestamp": datetime.now().isoformat(),
                "source": "technical_analysis",
                "details": details
            }
            
            # Lưu vào lịch sử
            self.sentiment_history["technical_sentiment"][symbol].append({
                "timestamp": datetime.now().isoformat(),
                "value": float(sentiment_score),
                "state": state
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích tâm lý kỹ thuật: {str(e)}")
            return {
                "value": 50,
                "state": "neutral",
                "description": "Trung tính (lỗi phân tích)",
                "timestamp": datetime.now().isoformat(),
                "source": "technical_analysis",
                "details": {"error": str(e)}
            }
    
    def analyze_volume_sentiment(self, symbol: str, dataframe: pd.DataFrame) -> Dict:
        """
        Phân tích tâm lý thị trường dựa trên khối lượng giao dịch.
        
        Args:
            symbol (str): Mã cặp giao dịch
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và khối lượng
            
        Returns:
            Dict: Kết quả phân tích tâm lý thị trường dựa trên khối lượng
        """
        if not isinstance(dataframe, pd.DataFrame) or dataframe.empty or 'volume' not in dataframe.columns:
            logger.error("DataFrame không hợp lệ hoặc thiếu dữ liệu khối lượng")
            return {
                "value": 50,
                "state": "neutral",
                "description": "Trung tính (không đủ dữ liệu)",
                "timestamp": datetime.now().isoformat(),
                "source": "volume_analysis",
                "details": {}
            }
        
        try:
            # Số điểm tâm lý, phạm vi 0-100
            sentiment_score = 50.0
            details = {}
            
            # 1. Phân tích khối lượng bất thường
            # Tính khối lượng trung bình trong 20 phiên
            avg_volume = dataframe['volume'].rolling(window=20).mean()
            current_volume = dataframe['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume.iloc[-1] if not pd.isna(avg_volume.iloc[-1]) and avg_volume.iloc[-1] > 0 else 1.0
            
            # Phân tích chênh lệch giá (close - open)
            if 'close' in dataframe.columns and 'open' in dataframe.columns:
                price_change = dataframe['close'].iloc[-1] - dataframe['open'].iloc[-1]
                price_change_pct = price_change / dataframe['open'].iloc[-1] * 100 if dataframe['open'].iloc[-1] > 0 else 0
                
                # Tính điểm tâm lý dựa trên khối lượng và biến động giá
                if volume_ratio > 2:  # Khối lượng bất thường - hơn 2 lần trung bình
                    if price_change_pct > 1:  # Tăng mạnh với khối lượng lớn = tín hiệu tích cực mạnh
                        volume_score = 85
                        volume_desc = "Khối lượng đột biến kèm tăng giá mạnh (rất tích cực)"
                    elif price_change_pct > 0:  # Tăng nhẹ với khối lượng lớn = tích cực
                        volume_score = 70
                        volume_desc = "Khối lượng đột biến kèm tăng giá (tích cực)"
                    elif price_change_pct < -1:  # Giảm mạnh với khối lượng lớn = tiêu cực mạnh
                        volume_score = 15
                        volume_desc = "Khối lượng đột biến kèm giảm giá mạnh (rất tiêu cực)"
                    elif price_change_pct < 0:  # Giảm nhẹ với khối lượng lớn = tiêu cực
                        volume_score = 30
                        volume_desc = "Khối lượng đột biến kèm giảm giá (tiêu cực)"
                    else:
                        volume_score = 50
                        volume_desc = "Khối lượng đột biến nhưng giá đi ngang (trung tính)"
                elif volume_ratio > 1.5:  # Khối lượng cao
                    if price_change_pct > 0.5:
                        volume_score = 65
                        volume_desc = "Khối lượng cao kèm tăng giá (tích cực)"
                    elif price_change_pct < -0.5:
                        volume_score = 35
                        volume_desc = "Khối lượng cao kèm giảm giá (tiêu cực)"
                    else:
                        volume_score = 50
                        volume_desc = "Khối lượng cao nhưng giá đi ngang (trung tính)"
                elif volume_ratio < 0.5:  # Khối lượng thấp
                    volume_score = 50  # Khối lượng thấp thường ít ý nghĩa
                    volume_desc = "Khối lượng thấp (thị trường thiếu sự quan tâm)"
                else:  # Khối lượng bình thường
                    volume_score = 50
                    volume_desc = "Khối lượng bình thường"
            else:
                # Không có dữ liệu giá
                if volume_ratio > 2:
                    volume_score = 60  # Khối lượng cao thường tích cực
                    volume_desc = "Khối lượng đột biến"
                elif volume_ratio < 0.5:
                    volume_score = 40  # Khối lượng thấp thường tiêu cực
                    volume_desc = "Khối lượng thấp"
                else:
                    volume_score = 50
                    volume_desc = "Khối lượng bình thường"
            
            details["volume_analysis"] = {
                "volume_ratio": float(volume_ratio),
                "score": float(volume_score),
                "description": volume_desc
            }
            sentiment_score += volume_score * 0.5  # Phân tích khối lượng chiếm 50% trọng số
            
            # 2. Phân tích OBV (On-Balance Volume) nếu có
            if 'obv' in dataframe.columns:
                # Tính xu hướng OBV gần đây
                obv_trend = dataframe['obv'].iloc[-5:].is_monotonic_increasing
                obv_reverse_trend = dataframe['obv'].iloc[-5:].is_monotonic_decreasing
                
                if obv_trend:
                    obv_score = 75  # OBV tăng = tín hiệu tích cực
                    obv_desc = "OBV tăng (tích cực)"
                elif obv_reverse_trend:
                    obv_score = 25  # OBV giảm = tín hiệu tiêu cực
                    obv_desc = "OBV giảm (tiêu cực)"
                else:
                    # So sánh OBV hiện tại với OBV 5 chu kỳ trước
                    obv_change = dataframe['obv'].iloc[-1] - dataframe['obv'].iloc[-6]
                    if obv_change > 0:
                        obv_score = 60  # OBV cao hơn = hơi tích cực
                        obv_desc = "OBV tích lũy tích cực"
                    elif obv_change < 0:
                        obv_score = 40  # OBV thấp hơn = hơi tiêu cực
                        obv_desc = "OBV tích lũy tiêu cực"
                    else:
                        obv_score = 50  # OBV không đổi = trung tính
                        obv_desc = "OBV đi ngang"
                
                details["obv_analysis"] = {
                    "trend": "up" if obv_trend else "down" if obv_reverse_trend else "neutral",
                    "score": float(obv_score),
                    "description": obv_desc
                }
                sentiment_score += obv_score * 0.5  # OBV chiếm 50% trọng số
            
            # Phân loại trạng thái tâm lý
            state = "neutral"
            for sentiment, info in self.SENTIMENT_STATES.items():
                if info["range"][0] <= sentiment_score < info["range"][1]:
                    state = sentiment
                    break
            
            result = {
                "value": float(sentiment_score),
                "state": state,
                "description": self.SENTIMENT_STATES[state]["description"],
                "timestamp": datetime.now().isoformat(),
                "source": "volume_analysis",
                "details": details
            }
            
            # Lưu vào lịch sử
            self.sentiment_history["volume_analysis"][symbol].append({
                "timestamp": datetime.now().isoformat(),
                "value": float(sentiment_score),
                "state": state
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích tâm lý khối lượng: {str(e)}")
            return {
                "value": 50,
                "state": "neutral",
                "description": "Trung tính (lỗi phân tích)",
                "timestamp": datetime.now().isoformat(),
                "source": "volume_analysis",
                "details": {"error": str(e)}
            }
    
    def calculate_composite_sentiment(self, symbol: str, dataframe: pd.DataFrame) -> Dict:
        """
        Tính toán chỉ số tâm lý tổng hợp từ nhiều nguồn.
        
        Args:
            symbol (str): Mã cặp giao dịch
            dataframe (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo
            
        Returns:
            Dict: Kết quả tâm lý thị trường tổng hợp
        """
        try:
            scores = []
            weights = []
            details = {}
            
            # 1. Fear & Greed Index (thị trường chung)
            if self.config["use_fear_greed"]:
                fear_greed = self.get_fear_greed_index()
                scores.append(fear_greed["value"])
                weights.append(self.config["fear_greed_weight"])
                details["fear_greed_index"] = {
                    "value": fear_greed["value"],
                    "state": fear_greed["state"],
                    "description": fear_greed["description"]
                }
            
            # 2. Phân tích kỹ thuật
            if self.config["use_technical"] and isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
                technical = self.analyze_technical_sentiment(symbol, dataframe)
                scores.append(technical["value"])
                weights.append(self.config["technical_weight"])
                details["technical_analysis"] = {
                    "value": technical["value"],
                    "state": technical["state"],
                    "description": technical["description"],
                    "details": technical.get("details", {})
                }
            
            # 3. Phân tích khối lượng
            if self.config["use_volume"] and isinstance(dataframe, pd.DataFrame) and not dataframe.empty and 'volume' in dataframe.columns:
                volume = self.analyze_volume_sentiment(symbol, dataframe)
                scores.append(volume["value"])
                weights.append(self.config["volume_weight"])
                details["volume_analysis"] = {
                    "value": volume["value"],
                    "state": volume["state"],
                    "description": volume["description"],
                    "details": volume.get("details", {})
                }
            
            # Tính điểm tâm lý tổng hợp
            if scores and weights:
                composite_score = sum(score * weight for score, weight in zip(scores, weights)) / sum(weights)
            else:
                composite_score = 50.0
            
            # Phân loại trạng thái tâm lý
            state = "neutral"
            for sentiment, info in self.SENTIMENT_STATES.items():
                if info["range"][0] <= composite_score < info["range"][1]:
                    state = sentiment
                    break
            
            # Tạo nội dung mô tả
            description = self.SENTIMENT_STATES[state]["description"]
            if "technical_analysis" in details:
                description += f" (Phân tích kỹ thuật: {details['technical_analysis']['description']})"
            
            result = {
                "symbol": symbol,
                "value": float(composite_score),
                "state": state,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "sources_count": len(scores),
                "details": details
            }
            
            # Lưu vào lịch sử và dữ liệu hiện tại
            self.sentiment_history["composite_sentiment"][symbol].append({
                "timestamp": datetime.now().isoformat(),
                "value": float(composite_score),
                "state": state
            })
            
            self.current_sentiment[symbol] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tính toán tâm lý tổng hợp: {str(e)}")
            return {
                "symbol": symbol,
                "value": 50.0,
                "state": "neutral",
                "description": "Trung tính (lỗi phân tích)",
                "timestamp": datetime.now().isoformat(),
                "sources_count": 0,
                "details": {"error": str(e)}
            }
    
    def get_sentiment_trend(self, symbol: str = None, time_period: str = "24h") -> Dict:
        """
        Lấy xu hướng tâm lý thị trường trong khoảng thời gian.
        
        Args:
            symbol (str, optional): Mã cặp giao dịch cụ thể, None để lấy tổng quan thị trường
            time_period (str): Khoảng thời gian ("1h", "6h", "24h", "7d")
            
        Returns:
            Dict: Thông tin về xu hướng tâm lý
        """
        try:
            # Chuyển đổi time_period thành timedelta
            if time_period == "1h":
                delta = timedelta(hours=1)
            elif time_period == "6h":
                delta = timedelta(hours=6)
            elif time_period == "7d":
                delta = timedelta(days=7)
            else:  # 24h là mặc định
                delta = timedelta(days=1)
            
            cutoff_time = datetime.now() - delta
            
            results = {}
            
            # 1. Chỉ số Fear & Greed
            if self.sentiment_history["fear_greed_index"]:
                # Lọc dữ liệu trong khoảng thời gian
                recent_data = [
                    item for item in self.sentiment_history["fear_greed_index"]
                    if datetime.fromisoformat(item["timestamp"]) > cutoff_time
                ]
                
                if recent_data:
                    # Lấy giá trị đầu tiên và cuối cùng để tính xu hướng
                    start_value = recent_data[0]["value"]
                    end_value = recent_data[-1]["value"]
                    change = end_value - start_value
                    
                    # Xác định xu hướng
                    if change > 5:
                        trend = "improving"  # Cải thiện
                        desc = "Tâm lý thị trường đang cải thiện"
                    elif change < -5:
                        trend = "worsening"  # Xấu đi
                        desc = "Tâm lý thị trường đang xấu đi"
                    else:
                        trend = "stable"  # Ổn định
                        desc = "Tâm lý thị trường ổn định"
                    
                    results["fear_greed_trend"] = {
                        "start_value": float(start_value),
                        "end_value": float(end_value),
                        "change": float(change),
                        "trend": trend,
                        "description": desc
                    }
            
            # 2. Tâm lý tổng hợp theo symbol
            if symbol:
                composite_key = "composite_sentiment"
                if symbol in self.sentiment_history[composite_key]:
                    # Lọc dữ liệu trong khoảng thời gian
                    recent_data = [
                        item for item in self.sentiment_history[composite_key][symbol]
                        if datetime.fromisoformat(item["timestamp"]) > cutoff_time
                    ]
                    
                    if recent_data:
                        # Lấy giá trị đầu tiên và cuối cùng để tính xu hướng
                        start_value = recent_data[0]["value"]
                        end_value = recent_data[-1]["value"]
                        change = end_value - start_value
                        
                        # Xác định xu hướng
                        if change > 5:
                            trend = "improving"
                            desc = f"Tâm lý {symbol} đang cải thiện"
                        elif change < -5:
                            trend = "worsening"
                            desc = f"Tâm lý {symbol} đang xấu đi"
                        else:
                            trend = "stable"
                            desc = f"Tâm lý {symbol} ổn định"
                        
                        results["symbol_sentiment_trend"] = {
                            "symbol": symbol,
                            "start_value": float(start_value),
                            "end_value": float(end_value),
                            "change": float(change),
                            "trend": trend,
                            "description": desc
                        }
            
            # Kết quả chung
            if results:
                return {
                    "time_period": time_period,
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat(),
                    "trends": results
                }
            else:
                return {
                    "time_period": time_period,
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat(),
                    "trends": {},
                    "description": "Không đủ dữ liệu để phân tích xu hướng"
                }
            
        except Exception as e:
            logger.error(f"Lỗi khi phân tích xu hướng tâm lý: {str(e)}")
            return {
                "time_period": time_period,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "description": "Lỗi khi phân tích xu hướng tâm lý"
            }
    
    def get_current_sentiment(self, symbol: str = None) -> Dict:
        """
        Lấy tâm lý thị trường hiện tại.
        
        Args:
            symbol (str, optional): Mã cặp giao dịch cụ thể, None để lấy tổng quan thị trường
            
        Returns:
            Dict: Thông tin tâm lý thị trường hiện tại
        """
        if symbol and symbol in self.current_sentiment:
            return self.current_sentiment[symbol]
        
        # Nếu không có dữ liệu cho symbol cụ thể, trả về chỉ số Fear & Greed chung
        return self.get_fear_greed_index()
    
    def save_history(self, file_path: str = "sentiment_history.json") -> bool:
        """
        Lưu lịch sử tâm lý thị trường vào file.
        
        Args:
            file_path (str): Đường dẫn đến file lưu lịch sử
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            # Chuyển đổi defaultdict thành dict thông thường để serialization
            history_dict = {
                "fear_greed_index": self.sentiment_history["fear_greed_index"],
                "technical_sentiment": dict(self.sentiment_history["technical_sentiment"]),
                "volume_analysis": dict(self.sentiment_history["volume_analysis"]),
                "social_sentiment": dict(self.sentiment_history["social_sentiment"]),
                "composite_sentiment": dict(self.sentiment_history["composite_sentiment"]),
                "last_update": datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(history_dict, f, indent=2)
            
            logger.info(f"Đã lưu lịch sử tâm lý thị trường vào {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử tâm lý thị trường: {str(e)}")
            return False
    
    def load_history(self, file_path: str = "sentiment_history.json") -> bool:
        """
        Tải lịch sử tâm lý thị trường từ file.
        
        Args:
            file_path (str): Đường dẫn đến file chứa lịch sử
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    history_dict = json.load(f)
                
                # Chuyển đổi dict thành defaultdict
                self.sentiment_history["fear_greed_index"] = history_dict.get("fear_greed_index", [])
                
                for key in ["technical_sentiment", "volume_analysis", "social_sentiment", "composite_sentiment"]:
                    self.sentiment_history[key] = defaultdict(list)
                    for symbol, data in history_dict.get(key, {}).items():
                        self.sentiment_history[key][symbol] = data
                
                logger.info(f"Đã tải lịch sử tâm lý thị trường từ {file_path}")
                return True
            else:
                logger.warning(f"File {file_path} không tồn tại. Sử dụng lịch sử mặc định.")
                return False
        
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử tâm lý thị trường: {str(e)}")
            return False
    
    def update_config(self, new_config: Dict) -> None:
        """
        Cập nhật cấu hình cho bộ phân tích tâm lý.
        
        Args:
            new_config (Dict): Cấu hình mới
        """
        for key, value in new_config.items():
            if key in self.config:
                self.config[key] = value
        
        logger.info("Đã cập nhật cấu hình bộ phân tích tâm lý thị trường")

# Tạo instance toàn cục
market_sentiment_analyzer = MarketSentimentAnalyzer()