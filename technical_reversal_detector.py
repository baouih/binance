#!/usr/bin/env python3
"""
Module phát hiện đảo chiều kỹ thuật (Technical Reversal Detector)

Module này cung cấp các phương pháp để phát hiện tín hiệu đảo chiều kỹ thuật trong thị trường,
cho phép vào lệnh ngược với xu hướng chính khi có tín hiệu đảo chiều đáng tin cậy.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("technical_reversal_detector")

# Đường dẫn lưu cấu hình
REVERSAL_CONFIG_PATH = "configs/reversal_detector_config.json"

class TechnicalReversalDetector:
    """Lớp phát hiện tín hiệu đảo chiều kỹ thuật"""
    
    def __init__(self, binance_api=None):
        """
        Khởi tạo detector
        
        Args:
            binance_api: Đối tượng BinanceAPI (tùy chọn)
        """
        self.binance_api = binance_api
        self.config = self._load_or_create_config()
        
    def _load_or_create_config(self) -> Dict:
        """
        Tải hoặc tạo cấu hình mặc định
        
        Returns:
            Dict: Cấu hình phát hiện đảo chiều
        """
        if os.path.exists(REVERSAL_CONFIG_PATH):
            try:
                with open(REVERSAL_CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình phát hiện đảo chiều từ {REVERSAL_CONFIG_PATH}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình phát hiện đảo chiều: {str(e)}")
        
        # Tạo cấu hình mặc định
        logger.info("Tạo cấu hình phát hiện đảo chiều mặc định")
        
        config = {
            "indicators": {
                "rsi": {
                    "period": 14,
                    "oversold_threshold": 30,
                    "overbought_threshold": 70,
                    "weight": 1.5
                },
                "macd": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "weight": 2.0
                },
                "bollinger_bands": {
                    "period": 20,
                    "std_dev": 2.0,
                    "weight": 1.0
                },
                "stochastic": {
                    "k_period": 14,
                    "d_period": 3,
                    "smooth_k": 3,
                    "oversold_threshold": 20,
                    "overbought_threshold": 80,
                    "weight": 1.0
                },
                "price_action": {
                    "lookback": 3,
                    "weight": 2.0
                },
                "volume": {
                    "period": 20,
                    "threshold": 1.5,
                    "weight": 1.0
                }
            },
            "reversal_thresholds": {
                "upward": 65,  # Mức tối thiểu để xác nhận đảo chiều lên
                "downward": 65  # Mức tối thiểu để xác nhận đảo chiều xuống
            },
            "confirmation_requirements": {
                "min_indicators": 2,  # Số chỉ báo tối thiểu phải có tín hiệu
                "min_weighted_score": 3.0  # Tổng điểm có trọng số tối thiểu
            },
            "additional_filters": {
                "require_volume_confirmation": True,
                "require_candle_confirmation": True,
                "require_multiple_timeframe": False
            },
            "candlestick_patterns": {
                "enabled": True,
                "weight": 1.5,
                "patterns": [
                    "hammer", "inverted_hammer", "bullish_engulfing", "piercing_line",
                    "morning_star", "three_white_soldiers", "three_inside_up",
                    "shooting_star", "hanging_man", "bearish_engulfing", "dark_cloud_cover",
                    "evening_star", "three_black_crows", "three_inside_down"
                ]
            },
            "market_regime_adjustments": {
                "trending": {
                    "threshold_multiplier": 1.2,  # Yêu cầu tín hiệu mạnh hơn trong thị trường trending
                    "min_indicators_add": 1       # Yêu cầu thêm chỉ báo xác nhận trong thị trường trending
                },
                "ranging": {
                    "threshold_multiplier": 0.9,  # Yêu cầu ít nghiêm ngặt hơn trong thị trường ranging
                    "min_indicators_add": 0
                },
                "volatile": {
                    "threshold_multiplier": 1.3,  # Yêu cầu tín hiệu rất mạnh trong thị trường biến động
                    "min_indicators_add": 2
                },
                "quiet": {
                    "threshold_multiplier": 0.8,  # Yêu cầu ít nghiêm ngặt hơn trong thị trường ít biến động
                    "min_indicators_add": 0
                }
            },
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình
        try:
            os.makedirs(os.path.dirname(REVERSAL_CONFIG_PATH), exist_ok=True)
            with open(REVERSAL_CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã tạo cấu hình phát hiện đảo chiều mặc định tại {REVERSAL_CONFIG_PATH}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình phát hiện đảo chiều: {str(e)}")
        
        return config
    
    def save_config(self) -> bool:
        """
        Lưu cấu hình hiện tại
        
        Returns:
            bool: True nếu lưu thành công, False nếu lỗi
        """
        try:
            # Cập nhật thời gian
            self.config["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo thư mục tồn tại
            os.makedirs(os.path.dirname(REVERSAL_CONFIG_PATH), exist_ok=True)
            
            # Lưu cấu hình
            with open(REVERSAL_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình phát hiện đảo chiều vào {REVERSAL_CONFIG_PATH}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình phát hiện đảo chiều: {str(e)}")
            return False
    
    def detect_reversal(self, symbol: str, direction: str, df: pd.DataFrame = None,
                      timeframe: str = "1h", market_regime: str = "ranging") -> Dict:
        """
        Phát hiện tín hiệu đảo chiều kỹ thuật
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            df (pd.DataFrame, optional): DataFrame chứa dữ liệu giá
            timeframe (str): Khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Dict: Kết quả phát hiện đảo chiều
        """
        try:
            # Kiểm tra hướng
            if direction not in ['up', 'down']:
                logger.error(f"Hướng đảo chiều không hợp lệ: {direction}")
                return {"is_reversal": False, "score": 0, "signals": [], "details": {}}
            
            # Tải dữ liệu nếu chưa có
            if df is None:
                df = self._get_ohlcv_data(symbol, timeframe)
            
            if df is None or df.empty:
                logger.error(f"Không có dữ liệu cho {symbol} khung {timeframe}")
                return {"is_reversal": False, "score": 0, "signals": [], "details": {}}
            
            # Điều chỉnh ngưỡng theo chế độ thị trường
            regime_adjustments = self.config["market_regime_adjustments"].get(market_regime, {})
            threshold_multiplier = regime_adjustments.get("threshold_multiplier", 1.0)
            min_indicators_add = regime_adjustments.get("min_indicators_add", 0)
            
            # Ngưỡng đảo chiều
            reversal_threshold = self.config["reversal_thresholds"][f"{direction}ward"] * threshold_multiplier
            
            # Số chỉ báo tối thiểu
            min_indicators = self.config["confirmation_requirements"]["min_indicators"] + min_indicators_add
            
            # Phát hiện tín hiệu từ các chỉ báo
            signals = []
            details = {}
            weighted_scores = []
            
            # 1. RSI
            rsi_signal = self._detect_rsi_reversal(df, direction)
            if rsi_signal["is_signal"]:
                signals.append("rsi")
                weight = self.config["indicators"]["rsi"]["weight"]
                weighted_scores.append(weight)
            details["rsi"] = rsi_signal
            
            # 2. MACD
            macd_signal = self._detect_macd_reversal(df, direction)
            if macd_signal["is_signal"]:
                signals.append("macd")
                weight = self.config["indicators"]["macd"]["weight"]
                weighted_scores.append(weight)
            details["macd"] = macd_signal
            
            # 3. Bollinger Bands
            bb_signal = self._detect_bollinger_reversal(df, direction)
            if bb_signal["is_signal"]:
                signals.append("bollinger_bands")
                weight = self.config["indicators"]["bollinger_bands"]["weight"]
                weighted_scores.append(weight)
            details["bollinger_bands"] = bb_signal
            
            # 4. Stochastic
            stoch_signal = self._detect_stochastic_reversal(df, direction)
            if stoch_signal["is_signal"]:
                signals.append("stochastic")
                weight = self.config["indicators"]["stochastic"]["weight"]
                weighted_scores.append(weight)
            details["stochastic"] = stoch_signal
            
            # 5. Price Action
            price_signal = self._detect_price_action_reversal(df, direction)
            if price_signal["is_signal"]:
                signals.append("price_action")
                weight = self.config["indicators"]["price_action"]["weight"]
                weighted_scores.append(weight)
            details["price_action"] = price_signal
            
            # 6. Volume
            volume_signal = self._detect_volume_confirmation(df)
            if volume_signal["is_signal"]:
                signals.append("volume")
                weight = self.config["indicators"]["volume"]["weight"]
                weighted_scores.append(weight)
            details["volume"] = volume_signal
            
            # 7. Candlestick Patterns
            if self.config["candlestick_patterns"]["enabled"]:
                pattern_signal = self._detect_candlestick_patterns(df, direction)
                if pattern_signal["is_signal"]:
                    signals.append("candlestick")
                    weight = self.config["candlestick_patterns"]["weight"]
                    weighted_scores.append(weight)
                details["candlestick"] = pattern_signal
            
            # Kiểm tra xem có đủ tín hiệu không
            if len(signals) < min_indicators:
                return {
                    "is_reversal": False,
                    "score": len(signals) * 10,
                    "signals": signals,
                    "details": details,
                    "reason": f"Không đủ chỉ báo ({len(signals)}/{min_indicators})"
                }
            
            # Kiểm tra tổng điểm có trọng số
            weighted_sum = sum(weighted_scores)
            min_weighted_score = self.config["confirmation_requirements"]["min_weighted_score"]
            
            if weighted_sum < min_weighted_score:
                return {
                    "is_reversal": False,
                    "score": len(signals) * 10,
                    "signals": signals,
                    "details": details,
                    "weighted_sum": weighted_sum,
                    "reason": f"Tổng điểm có trọng số không đủ ({weighted_sum:.1f}/{min_weighted_score})"
                }
            
            # Kiểm tra bộ lọc bổ sung
            if self.config["additional_filters"]["require_volume_confirmation"] and "volume" not in signals:
                return {
                    "is_reversal": False,
                    "score": len(signals) * 10,
                    "signals": signals,
                    "details": details,
                    "weighted_sum": weighted_sum,
                    "reason": "Không có xác nhận khối lượng"
                }
            
            if self.config["additional_filters"]["require_candle_confirmation"]:
                # Kiểm tra nến
                if direction == "up" and df['close'].iloc[-1] <= df['open'].iloc[-1]:
                    return {
                        "is_reversal": False,
                        "score": len(signals) * 10,
                        "signals": signals,
                        "details": details,
                        "weighted_sum": weighted_sum,
                        "reason": "Nến gần nhất không phải nến tăng"
                    }
                elif direction == "down" and df['close'].iloc[-1] >= df['open'].iloc[-1]:
                    return {
                        "is_reversal": False,
                        "score": len(signals) * 10,
                        "signals": signals,
                        "details": details,
                        "weighted_sum": weighted_sum,
                        "reason": "Nến gần nhất không phải nến giảm"
                    }
            
            # Tính điểm tổng hợp
            base_score = (len(signals) / 7) * 100
            # Điều chỉnh theo trọng số
            adjusted_score = min(100, base_score * (weighted_sum / (min_indicators * 1.5)))
            
            # Xác định kết quả
            is_reversal = adjusted_score >= reversal_threshold
            
            return {
                "is_reversal": is_reversal,
                "score": adjusted_score,
                "signals": signals,
                "details": details,
                "weighted_sum": weighted_sum,
                "threshold": reversal_threshold,
                "reason": "Thành công" if is_reversal else f"Điểm không đủ ({adjusted_score:.1f}/{reversal_threshold})"
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện đảo chiều: {str(e)}")
            return {"is_reversal": False, "score": 0, "signals": [], "details": {}, "error": str(e)}
    
    def _detect_rsi_reversal(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Phát hiện tín hiệu đảo chiều từ RSI
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Lấy cài đặt
            period = self.config["indicators"]["rsi"]["period"]
            oversold = self.config["indicators"]["rsi"]["oversold_threshold"]
            overbought = self.config["indicators"]["rsi"]["overbought_threshold"]
            
            # Tính RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Kiểm tra tín hiệu đảo chiều
            if direction == "up":
                # Tín hiệu đảo chiều lên: RSI vừa vượt lên trên ngưỡng oversold
                prev_oversold = rsi.iloc[-2] <= oversold
                current_above = rsi.iloc[-1] > oversold
                
                is_signal = prev_oversold and current_above
                
                return {
                    "is_signal": is_signal,
                    "current_value": rsi.iloc[-1],
                    "previous_value": rsi.iloc[-2],
                    "threshold": oversold,
                    "detail": "RSI vượt lên trên ngưỡng oversold" if is_signal else "RSI không đủ điều kiện đảo chiều lên"
                }
            else:  # direction == "down"
                # Tín hiệu đảo chiều xuống: RSI vừa giảm xuống dưới ngưỡng overbought
                prev_overbought = rsi.iloc[-2] >= overbought
                current_below = rsi.iloc[-1] < overbought
                
                is_signal = prev_overbought and current_below
                
                return {
                    "is_signal": is_signal,
                    "current_value": rsi.iloc[-1],
                    "previous_value": rsi.iloc[-2],
                    "threshold": overbought,
                    "detail": "RSI giảm xuống dưới ngưỡng overbought" if is_signal else "RSI không đủ điều kiện đảo chiều xuống"
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện đảo chiều RSI: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi tính RSI"
            }
    
    def _detect_macd_reversal(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Phát hiện tín hiệu đảo chiều từ MACD
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Lấy cài đặt
            fast_period = self.config["indicators"]["macd"]["fast_period"]
            slow_period = self.config["indicators"]["macd"]["slow_period"]
            signal_period = self.config["indicators"]["macd"]["signal_period"]
            
            # Tính MACD
            ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
            
            histogram = macd_line - signal_line
            
            # Kiểm tra tín hiệu đảo chiều
            if direction == "up":
                # Tín hiệu đảo chiều lên: histogram chuyển từ âm sang dương
                prev_negative = histogram.iloc[-2] < 0
                current_positive = histogram.iloc[-1] > 0
                
                # Hoặc MACD line vừa cắt lên trên signal line
                macd_crossover = macd_line.iloc[-2] < signal_line.iloc[-2] and macd_line.iloc[-1] > signal_line.iloc[-1]
                
                is_signal = (prev_negative and current_positive) or macd_crossover
                
                return {
                    "is_signal": is_signal,
                    "macd_line": macd_line.iloc[-1],
                    "signal_line": signal_line.iloc[-1],
                    "histogram": histogram.iloc[-1],
                    "prev_histogram": histogram.iloc[-2],
                    "macd_crossover": macd_crossover,
                    "detail": ("Histogram MACD chuyển từ âm sang dương" if (prev_negative and current_positive) else
                              "MACD cắt lên trên signal line" if macd_crossover else
                              "MACD không đủ điều kiện đảo chiều lên")
                }
            else:  # direction == "down"
                # Tín hiệu đảo chiều xuống: histogram chuyển từ dương sang âm
                prev_positive = histogram.iloc[-2] > 0
                current_negative = histogram.iloc[-1] < 0
                
                # Hoặc MACD line vừa cắt xuống dưới signal line
                macd_crossunder = macd_line.iloc[-2] > signal_line.iloc[-2] and macd_line.iloc[-1] < signal_line.iloc[-1]
                
                is_signal = (prev_positive and current_negative) or macd_crossunder
                
                return {
                    "is_signal": is_signal,
                    "macd_line": macd_line.iloc[-1],
                    "signal_line": signal_line.iloc[-1],
                    "histogram": histogram.iloc[-1],
                    "prev_histogram": histogram.iloc[-2],
                    "macd_crossunder": macd_crossunder,
                    "detail": ("Histogram MACD chuyển từ dương sang âm" if (prev_positive and current_negative) else
                              "MACD cắt xuống dưới signal line" if macd_crossunder else
                              "MACD không đủ điều kiện đảo chiều xuống")
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện đảo chiều MACD: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi tính MACD"
            }
    
    def _detect_bollinger_reversal(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Phát hiện tín hiệu đảo chiều từ Bollinger Bands
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Lấy cài đặt
            period = self.config["indicators"]["bollinger_bands"]["period"]
            std_dev = self.config["indicators"]["bollinger_bands"]["std_dev"]
            
            # Tính Bollinger Bands
            df_bb = df.copy()
            df_bb['sma'] = df_bb['close'].rolling(window=period).mean()
            df_bb['std'] = df_bb['close'].rolling(window=period).std()
            
            df_bb['upper'] = df_bb['sma'] + (df_bb['std'] * std_dev)
            df_bb['lower'] = df_bb['sma'] - (df_bb['std'] * std_dev)
            
            # Kiểm tra tín hiệu đảo chiều
            if direction == "up":
                # Tín hiệu đảo chiều lên: giá trước đó chạm/vượt dưới lower band và giá hiện tại quay trở lại
                prev_below = df_bb['low'].iloc[-2] <= df_bb['lower'].iloc[-2]
                current_above = df_bb['close'].iloc[-1] > df_bb['lower'].iloc[-1]
                price_rise = df_bb['close'].iloc[-1] > df_bb['close'].iloc[-2]
                
                is_signal = prev_below and current_above and price_rise
                
                return {
                    "is_signal": is_signal,
                    "current_price": df_bb['close'].iloc[-1],
                    "previous_low": df_bb['low'].iloc[-2],
                    "lower_band": df_bb['lower'].iloc[-1],
                    "prev_lower_band": df_bb['lower'].iloc[-2],
                    "detail": "Giá phục hồi sau khi chạm/vượt dưới lower band" if is_signal else "Giá không đủ điều kiện đảo chiều lên theo Bollinger Bands"
                }
            else:  # direction == "down"
                # Tín hiệu đảo chiều xuống: giá trước đó chạm/vượt trên upper band và giá hiện tại quay trở lại
                prev_above = df_bb['high'].iloc[-2] >= df_bb['upper'].iloc[-2]
                current_below = df_bb['close'].iloc[-1] < df_bb['upper'].iloc[-1]
                price_fall = df_bb['close'].iloc[-1] < df_bb['close'].iloc[-2]
                
                is_signal = prev_above and current_below and price_fall
                
                return {
                    "is_signal": is_signal,
                    "current_price": df_bb['close'].iloc[-1],
                    "previous_high": df_bb['high'].iloc[-2],
                    "upper_band": df_bb['upper'].iloc[-1],
                    "prev_upper_band": df_bb['upper'].iloc[-2],
                    "detail": "Giá giảm sau khi chạm/vượt trên upper band" if is_signal else "Giá không đủ điều kiện đảo chiều xuống theo Bollinger Bands"
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện đảo chiều Bollinger Bands: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi tính Bollinger Bands"
            }
    
    def _detect_stochastic_reversal(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Phát hiện tín hiệu đảo chiều từ Stochastic Oscillator
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Lấy cài đặt
            k_period = self.config["indicators"]["stochastic"]["k_period"]
            d_period = self.config["indicators"]["stochastic"]["d_period"]
            smooth_k = self.config["indicators"]["stochastic"]["smooth_k"]
            oversold = self.config["indicators"]["stochastic"]["oversold_threshold"]
            overbought = self.config["indicators"]["stochastic"]["overbought_threshold"]
            
            # Tính Stochastic Oscillator
            df_stoch = df.copy()
            
            # Tính %K
            low_min = df_stoch['low'].rolling(window=k_period).min()
            high_max = df_stoch['high'].rolling(window=k_period).max()
            
            k = 100 * ((df_stoch['close'] - low_min) / (high_max - low_min))
            
            # Smooth %K
            if smooth_k > 1:
                k = k.rolling(window=smooth_k).mean()
            
            # Tính %D
            d = k.rolling(window=d_period).mean()
            
            # Kiểm tra tín hiệu đảo chiều
            if direction == "up":
                # Tín hiệu đảo chiều lên: %K vừa vượt lên trên %D khi cả hai đều ở vùng oversold
                prev_k_below_d = k.iloc[-2] < d.iloc[-2]
                current_k_above_d = k.iloc[-1] > d.iloc[-1]
                in_oversold = k.iloc[-2] < oversold and d.iloc[-2] < oversold
                
                is_signal = prev_k_below_d and current_k_above_d and in_oversold
                
                return {
                    "is_signal": is_signal,
                    "k_value": k.iloc[-1],
                    "d_value": d.iloc[-1],
                    "prev_k": k.iloc[-2],
                    "prev_d": d.iloc[-2],
                    "oversold_threshold": oversold,
                    "detail": "%K vượt lên trên %D trong vùng oversold" if is_signal else "Stochastic không đủ điều kiện đảo chiều lên"
                }
            else:  # direction == "down"
                # Tín hiệu đảo chiều xuống: %K vừa cắt xuống dưới %D khi cả hai đều ở vùng overbought
                prev_k_above_d = k.iloc[-2] > d.iloc[-2]
                current_k_below_d = k.iloc[-1] < d.iloc[-1]
                in_overbought = k.iloc[-2] > overbought and d.iloc[-2] > overbought
                
                is_signal = prev_k_above_d and current_k_below_d and in_overbought
                
                return {
                    "is_signal": is_signal,
                    "k_value": k.iloc[-1],
                    "d_value": d.iloc[-1],
                    "prev_k": k.iloc[-2],
                    "prev_d": d.iloc[-2],
                    "overbought_threshold": overbought,
                    "detail": "%K cắt xuống dưới %D trong vùng overbought" if is_signal else "Stochastic không đủ điều kiện đảo chiều xuống"
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện đảo chiều Stochastic Oscillator: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi tính Stochastic Oscillator"
            }
    
    def _detect_price_action_reversal(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Phát hiện tín hiệu đảo chiều từ Price Action
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Lấy cài đặt
            lookback = self.config["indicators"]["price_action"]["lookback"]
            
            # Kiểm tra price action
            if direction == "up":
                # Kiểm tra đáy kép hoặc đáy cao hơn
                recent_lows = []
                for i in range(1, lookback + 1):
                    if i <= len(df) - 1:
                        recent_lows.append(df['low'].iloc[-i])
                
                if len(recent_lows) < 2:
                    return {
                        "is_signal": False,
                        "detail": "Không đủ dữ liệu để phát hiện đáy kép hoặc đáy cao hơn"
                    }
                
                # Đáy kép
                double_bottom = abs(recent_lows[0] - recent_lows[1]) / recent_lows[0] < 0.01
                
                # Đáy cao hơn (higher low)
                higher_low = recent_lows[0] > recent_lows[1]
                
                # Giá vượt lên trên mức kháng cự gần nhất
                resistance_break = False
                if len(df) > lookback + 2:
                    recent_high = max(df['high'].iloc[-(lookback+2):-2])
                    resistance_break = df['close'].iloc[-1] > recent_high
                
                is_signal = double_bottom or higher_low or resistance_break
                
                details = []
                if double_bottom:
                    details.append("Hình thành đáy kép")
                if higher_low:
                    details.append("Đáy mới cao hơn đáy trước")
                if resistance_break:
                    details.append("Giá vượt lên trên mức kháng cự gần nhất")
                
                return {
                    "is_signal": is_signal,
                    "recent_lows": recent_lows,
                    "double_bottom": double_bottom,
                    "higher_low": higher_low,
                    "resistance_break": resistance_break,
                    "detail": ", ".join(details) if details else "Không phát hiện tín hiệu đảo chiều lên từ price action"
                }
            else:  # direction == "down"
                # Kiểm tra đỉnh kép hoặc đỉnh thấp hơn
                recent_highs = []
                for i in range(1, lookback + 1):
                    if i <= len(df) - 1:
                        recent_highs.append(df['high'].iloc[-i])
                
                if len(recent_highs) < 2:
                    return {
                        "is_signal": False,
                        "detail": "Không đủ dữ liệu để phát hiện đỉnh kép hoặc đỉnh thấp hơn"
                    }
                
                # Đỉnh kép
                double_top = abs(recent_highs[0] - recent_highs[1]) / recent_highs[0] < 0.01
                
                # Đỉnh thấp hơn (lower high)
                lower_high = recent_highs[0] < recent_highs[1]
                
                # Giá phá xuống dưới mức hỗ trợ gần nhất
                support_break = False
                if len(df) > lookback + 2:
                    recent_low = min(df['low'].iloc[-(lookback+2):-2])
                    support_break = df['close'].iloc[-1] < recent_low
                
                is_signal = double_top or lower_high or support_break
                
                details = []
                if double_top:
                    details.append("Hình thành đỉnh kép")
                if lower_high:
                    details.append("Đỉnh mới thấp hơn đỉnh trước")
                if support_break:
                    details.append("Giá phá xuống dưới mức hỗ trợ gần nhất")
                
                return {
                    "is_signal": is_signal,
                    "recent_highs": recent_highs,
                    "double_top": double_top,
                    "lower_high": lower_high,
                    "support_break": support_break,
                    "detail": ", ".join(details) if details else "Không phát hiện tín hiệu đảo chiều xuống từ price action"
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện đảo chiều Price Action: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi phân tích Price Action"
            }
    
    def _detect_volume_confirmation(self, df: pd.DataFrame) -> Dict:
        """
        Phát hiện xác nhận từ khối lượng giao dịch
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Lấy cài đặt
            period = self.config["indicators"]["volume"]["period"]
            threshold = self.config["indicators"]["volume"]["threshold"]
            
            # Kiểm tra xem có cột volume không
            if 'volume' not in df.columns:
                return {
                    "is_signal": False,
                    "detail": "Dữ liệu không có thông tin khối lượng giao dịch"
                }
            
            # Tính trung bình khối lượng
            avg_volume = df['volume'].rolling(window=period).mean()
            current_volume = df['volume'].iloc[-1]
            
            # Kiểm tra xem khối lượng hiện tại có cao hơn trung bình không
            volume_ratio = current_volume / avg_volume.iloc[-1] if not np.isnan(avg_volume.iloc[-1]) and avg_volume.iloc[-1] > 0 else 0
            
            is_signal = volume_ratio >= threshold
            
            # Kiểm tra khối lượng tăng dần
            volume_increasing = False
            if len(df) >= 3:
                volume_increasing = df['volume'].iloc[-1] > df['volume'].iloc[-2] > df['volume'].iloc[-3]
            
            return {
                "is_signal": is_signal or volume_increasing,
                "volume_ratio": volume_ratio,
                "threshold": threshold,
                "current_volume": current_volume,
                "average_volume": avg_volume.iloc[-1] if not np.isnan(avg_volume.iloc[-1]) else 0,
                "volume_increasing": volume_increasing,
                "detail": (f"Khối lượng cao hơn trung bình {period} nến (x{volume_ratio:.2f})" if is_signal else
                         "Khối lượng tăng dần trong 3 nến gần nhất" if volume_increasing else
                         f"Khối lượng không đủ cao ({volume_ratio:.2f}x trung bình, cần {threshold}x)")
            }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện xác nhận khối lượng: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi phân tích khối lượng giao dịch"
            }
    
    def _detect_candlestick_patterns(self, df: pd.DataFrame, direction: str) -> Dict:
        """
        Phát hiện mô hình nến đảo chiều
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            
        Returns:
            Dict: Kết quả phát hiện
        """
        try:
            # Kiểm tra đủ dữ liệu
            if len(df) < 3:
                return {
                    "is_signal": False,
                    "detail": "Không đủ dữ liệu để phát hiện mô hình nến"
                }
            
            patterns = self.config["candlestick_patterns"]["patterns"]
            detected_patterns = []
            
            # Lấy dữ liệu nến gần nhất
            o1, h1, l1, c1 = df[['open', 'high', 'low', 'close']].iloc[-1]
            o2, h2, l2, c2 = df[['open', 'high', 'low', 'close']].iloc[-2]
            o3, h3, l3, c3 = df[['open', 'high', 'low', 'close']].iloc[-3]
            
            # Xác định thân nến và bóng nến
            body1 = abs(c1 - o1)
            body2 = abs(c2 - o2)
            body3 = abs(c3 - o3)
            
            upper_shadow1 = h1 - max(o1, c1)
            lower_shadow1 = min(o1, c1) - l1
            upper_shadow2 = h2 - max(o2, c2)
            lower_shadow2 = min(o2, c2) - l2
            
            if direction == "up":
                # Kiểm tra các mô hình nến đảo chiều lên
                
                # 1. Hammer (búa)
                if "hammer" in patterns:
                    if c1 > o1 and body1 > 0 and lower_shadow1 >= 2 * body1 and upper_shadow1 < 0.1 * body1:
                        detected_patterns.append("hammer")
                
                # 2. Inverted Hammer (búa ngược)
                if "inverted_hammer" in patterns:
                    if c1 > o1 and body1 > 0 and upper_shadow1 >= 2 * body1 and lower_shadow1 < 0.1 * body1:
                        detected_patterns.append("inverted_hammer")
                
                # 3. Bullish Engulfing (bao phủ tăng)
                if "bullish_engulfing" in patterns:
                    if c2 < o2 and c1 > o1 and c1 > o2 and o1 < c2 and body1 > body2:
                        detected_patterns.append("bullish_engulfing")
                
                # 4. Piercing Line (xuyên thủng)
                if "piercing_line" in patterns:
                    if c2 < o2 and c1 > o1 and c1 > (o2 + c2) / 2 and o1 < c2:
                        detected_patterns.append("piercing_line")
                
                # 5. Morning Star (sao mai)
                if "morning_star" in patterns and len(df) >= 4:
                    o4, h4, l4, c4 = df[['open', 'high', 'low', 'close']].iloc[-4]
                    if c4 < o4 and body3 < body4 * 0.5 and c2 > o2 and c2 > c3:
                        detected_patterns.append("morning_star")
                
                # 6. Three White Soldiers (ba chàng lính trắng)
                if "three_white_soldiers" in patterns and len(df) >= 4:
                    o4, h4, l4, c4 = df[['open', 'high', 'low', 'close']].iloc[-4]
                    if (c2 > o2 and c3 > o3 and c1 > o1 and 
                        o3 > o4 and o2 > o3 and o1 > o2 and
                        c3 > c4 and c2 > c3 and c1 > c2):
                        detected_patterns.append("three_white_soldiers")
                
                # 7. Three Inside Up (ba trong lên)
                if "three_inside_up" in patterns:
                    if c3 < o3 and body2 < body3 and o2 > c3 and c2 < o3 and c1 > c2 and c1 > o3:
                        detected_patterns.append("three_inside_up")
                
            else:  # direction == "down"
                # Kiểm tra các mô hình nến đảo chiều xuống
                
                # 1. Shooting Star (sao băng)
                if "shooting_star" in patterns:
                    if c1 < o1 and body1 > 0 and upper_shadow1 >= 2 * body1 and lower_shadow1 < 0.1 * body1:
                        detected_patterns.append("shooting_star")
                
                # 2. Hanging Man (người treo cổ)
                if "hanging_man" in patterns:
                    if c1 < o1 and body1 > 0 and lower_shadow1 >= 2 * body1 and upper_shadow1 < 0.1 * body1:
                        detected_patterns.append("hanging_man")
                
                # 3. Bearish Engulfing (bao phủ giảm)
                if "bearish_engulfing" in patterns:
                    if c2 > o2 and c1 < o1 and c1 < o2 and o1 > c2 and body1 > body2:
                        detected_patterns.append("bearish_engulfing")
                
                # 4. Dark Cloud Cover (mây đen che phủ)
                if "dark_cloud_cover" in patterns:
                    if c2 > o2 and c1 < o1 and c1 < (o2 + c2) / 2 and o1 > c2:
                        detected_patterns.append("dark_cloud_cover")
                
                # 5. Evening Star (sao hôm)
                if "evening_star" in patterns and len(df) >= 4:
                    o4, h4, l4, c4 = df[['open', 'high', 'low', 'close']].iloc[-4]
                    if c4 > o4 and body3 < body4 * 0.5 and c2 < o2 and c2 < c3:
                        detected_patterns.append("evening_star")
                
                # 6. Three Black Crows (ba con quạ đen)
                if "three_black_crows" in patterns and len(df) >= 4:
                    o4, h4, l4, c4 = df[['open', 'high', 'low', 'close']].iloc[-4]
                    if (c2 < o2 and c3 < o3 and c1 < o1 and 
                        o3 < o4 and o2 < o3 and o1 < o2 and
                        c3 < c4 and c2 < c3 and c1 < c2):
                        detected_patterns.append("three_black_crows")
                
                # 7. Three Inside Down (ba trong xuống)
                if "three_inside_down" in patterns:
                    if c3 > o3 and body2 < body3 and o2 < c3 and c2 > o3 and c1 < c2 and c1 < o3:
                        detected_patterns.append("three_inside_down")
            
            is_signal = len(detected_patterns) > 0
            
            return {
                "is_signal": is_signal,
                "detected_patterns": detected_patterns,
                "detail": ", ".join(detected_patterns) if detected_patterns else f"Không phát hiện mô hình nến đảo chiều {direction}"
            }
                
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện mô hình nến: {str(e)}")
            return {
                "is_signal": False,
                "error": str(e),
                "detail": "Lỗi khi phân tích mô hình nến"
            }
    
    def check_technical_reversal(self, symbol: str, direction: str, timeframe: str = "1h",
                              market_regime: str = "ranging") -> Tuple[bool, Dict]:
        """
        Kiểm tra đảo chiều kỹ thuật, phiên bản đơn giản để tích hợp vào kiểm tra điều kiện giao dịch
        
        Args:
            symbol (str): Mã cặp tiền
            direction (str): Hướng đảo chiều ('up' hoặc 'down')
            timeframe (str): Khung thời gian
            market_regime (str): Chế độ thị trường
            
        Returns:
            Tuple[bool, Dict]: (Có phải đảo chiều không, Chi tiết)
        """
        try:
            # Tải dữ liệu
            df = self._get_ohlcv_data(symbol, timeframe)
            
            if df is None or df.empty:
                logger.error(f"Không có dữ liệu cho {symbol} khung {timeframe}")
                return False, {"error": "Không có dữ liệu"}
            
            # Phát hiện đảo chiều
            result = self.detect_reversal(symbol, direction, df, timeframe, market_regime)
            
            return result["is_reversal"], result
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra đảo chiều kỹ thuật: {str(e)}")
            return False, {"error": str(e)}
    
    def _get_ohlcv_data(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Lấy dữ liệu OHLCV từ API
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            limit (int): Số lượng nến tối đa
            
        Returns:
            Optional[pd.DataFrame]: DataFrame chứa dữ liệu OHLCV hoặc None nếu lỗi
        """
        try:
            if not self.binance_api:
                return None
            
            # Lấy dữ liệu từ API
            klines = self.binance_api.get_klines(symbol=symbol, interval=timeframe, limit=limit)
            
            if not klines:
                return None
            
            # Chuyển đổi thành DataFrame
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                             'close_time', 'quote_asset_volume', 'number_of_trades',
                                             'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Chuyển đổi timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu OHLCV: {str(e)}")
            return None

def main():
    """Hàm chính để test module"""
    
    try:
        # Khởi tạo
        from binance_api import BinanceAPI
        api = BinanceAPI()
        detector = TechnicalReversalDetector(api)
        
        # Test phát hiện đảo chiều
        symbol = "BTCUSDT"
        timeframe = "1h"
        
        # Lấy dữ liệu
        df = detector._get_ohlcv_data(symbol, timeframe)
        
        if df is not None and not df.empty:
            # Test đảo chiều lên
            print(f"=== Kiểm tra đảo chiều lên cho {symbol} ===")
            up_result = detector.detect_reversal(symbol, "up", df, timeframe, "ranging")
            
            print(f"Có đảo chiều lên: {up_result['is_reversal']}")
            print(f"Điểm: {up_result['score']:.2f}")
            print(f"Ngưỡng: {up_result.get('threshold', 0):.2f}")
            print(f"Tín hiệu: {up_result['signals']}")
            print(f"Lý do: {up_result.get('reason', '')}")
            print()
            
            # Chi tiết các chỉ báo
            print("Chi tiết các chỉ báo:")
            for indicator, detail in up_result['details'].items():
                print(f"- {indicator}: {detail.get('detail', '')}")
            print()
            
            # Test đảo chiều xuống
            print(f"=== Kiểm tra đảo chiều xuống cho {symbol} ===")
            down_result = detector.detect_reversal(symbol, "down", df, timeframe, "ranging")
            
            print(f"Có đảo chiều xuống: {down_result['is_reversal']}")
            print(f"Điểm: {down_result['score']:.2f}")
            print(f"Ngưỡng: {down_result.get('threshold', 0):.2f}")
            print(f"Tín hiệu: {down_result['signals']}")
            print(f"Lý do: {down_result.get('reason', '')}")
            print()
            
            # Chi tiết các chỉ báo
            print("Chi tiết các chỉ báo:")
            for indicator, detail in down_result['details'].items():
                print(f"- {indicator}: {detail.get('detail', '')}")
        else:
            print(f"Không có dữ liệu cho {symbol} khung {timeframe}")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()