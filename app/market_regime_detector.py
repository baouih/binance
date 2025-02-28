"""
Market Regime Detector - Phân tích và phát hiện chế độ thị trường

Module này cung cấp các công cụ để phân tích và phát hiện chế độ thị trường
hiện tại, giúp chọn chiến lược giao dịch phù hợp và điều chỉnh tham số
cho các mô hình học máy.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
import os
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('market_regime_detector')

class MarketRegimeDetector:
    """
    Phát hiện và phân loại các chế độ thị trường
    để tối ưu hóa chiến lược giao dịch.
    """
    
    # Định nghĩa các ngưỡng cho từng chế độ thị trường
    REGIME_THRESHOLDS = {
        "trending_up": {
            "adx_min": 25,
            "trend_strength_min": 0.5,
            "volatility_max": 0.025,
            "volume_trend_min": 0.3
        },
        "trending_down": {
            "adx_min": 25,
            "trend_strength_max": -0.5,
            "volatility_max": 0.025,
            "volume_trend_min": 0.3
        },
        "volatile": {
            "volatility_min": 0.03,
            "trend_strength_max_abs": 0.3,
            "price_range_min": 0.02
        },
        "ranging": {
            "adx_max": 20,
            "volatility_max": 0.02,
            "trend_strength_max_abs": 0.2,
            "bb_width_max": 0.03
        },
        "breakout": {
            "volatility_increase": 0.5,  # 50% tăng biến động
            "volume_increase": 1.5,      # 50% tăng khối lượng
            "price_move": 0.015          # 1.5% thay đổi giá
        }
    }
    
    # Chiến lược ML phù hợp nhất cho mỗi chế độ
    REGIME_STRATEGIES = {
        "trending_up": ["ema_cross", "macd", "ml"],
        "trending_down": ["ema_cross", "macd", "ml"],
        "volatile": ["bbands", "ml", "rsi"],
        "ranging": ["rsi", "bbands", "ml"],
        "breakout": ["bbands", "ml", "macd"],
        "neutral": ["combined", "ml"]
    }
    
    # Trọng số cho các chiến lược kết hợp tùy theo chế độ thị trường
    REGIME_WEIGHTS = {
        "trending_up": [0.4, 0.3, 0.2, 0.1, 0.0],  # [ema_cross, macd, ml, rsi, bbands]
        "trending_down": [0.4, 0.3, 0.2, 0.1, 0.0],  # [ema_cross, macd, ml, rsi, bbands]
        "volatile": [0.1, 0.2, 0.3, 0.1, 0.3],  # [ema_cross, macd, ml, rsi, bbands]
        "ranging": [0.0, 0.1, 0.3, 0.3, 0.3],  # [ema_cross, macd, ml, rsi, bbands]
        "breakout": [0.1, 0.3, 0.3, 0.0, 0.3],  # [ema_cross, macd, ml, rsi, bbands]
        "neutral": [0.2, 0.2, 0.4, 0.1, 0.1]  # [ema_cross, macd, ml, rsi, bbands]
    }
    
    def __init__(self, data_storage_path='data/market_regimes'):
        """
        Khởi tạo detector với đường dẫn lưu trữ dữ liệu.
        
        Args:
            data_storage_path (str): Đường dẫn để lưu trữ dữ liệu chế độ thị trường
        """
        self.data_storage_path = data_storage_path
        self.current_regime = "neutral"
        self.previous_regime = "neutral"
        self.regime_start_time = datetime.now()
        self.regime_history = []
        self.regime_stats = {}
        
        # Thời gian tối thiểu (phút) mà một chế độ cần tồn tại trước khi xác nhận
        self.min_regime_duration = 60  # 60 phút = 1 giờ
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(data_storage_path, exist_ok=True)
        
        # Tải lịch sử chế độ nếu có
        self._load_regime_history()
    
    def detect_regime(self, df: pd.DataFrame) -> str:
        """
        Phát hiện chế độ thị trường hiện tại dựa trên dữ liệu kỹ thuật.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo kỹ thuật
            
        Returns:
            str: Chế độ thị trường được phát hiện
        """
        if df is None or df.empty or len(df) < 10:
            logger.warning("Không đủ dữ liệu để phát hiện chế độ thị trường")
            return "neutral"
            
        try:
            # Lấy hàng cuối cùng của dataframe
            latest = df.iloc[-1]
            
            # Kiểm tra xem các chỉ báo cần thiết có tồn tại không
            required_indicators = ['ADX', 'Trend_Strength', 'Price_Volatility', 'BB_Width']
            missing = [ind for ind in required_indicators if ind not in df.columns]
            
            if missing:
                logger.warning(f"Thiếu các chỉ báo để phát hiện chế độ thị trường: {missing}")
                return "neutral"
                
            # Lấy các giá trị chỉ báo hiện tại
            adx = latest.get('ADX', 0)
            trend_strength = latest.get('Trend_Strength', 0)
            volatility = latest.get('Price_Volatility', 0)
            bb_width = latest.get('BB_Width', 0)
            volume_ratio = latest.get('Volume_Ratio', 1.0)
            volume_trend = latest.get('Volume_Trend', 0)
            
            # Tính toán biến động về giá so với N phiên trước
            if len(df) >= 20:
                price_range = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / df['close'].iloc[-1]
            else:
                price_range = 0
                
            # Kiểm tra xem có đang xảy ra breakout hay không
            is_breakout = self._detect_breakout(df)
            if is_breakout:
                detected_regime = "breakout"
                logger.info(f"Phát hiện breakout! Thay đổi chế độ thị trường sang: {detected_regime}")
                
            # Phát hiện xu hướng tăng mạnh
            elif (adx >= self.REGIME_THRESHOLDS["trending_up"]["adx_min"] and 
                  trend_strength >= self.REGIME_THRESHOLDS["trending_up"]["trend_strength_min"] and
                  volatility <= self.REGIME_THRESHOLDS["trending_up"]["volatility_max"] and
                  volume_trend >= self.REGIME_THRESHOLDS["trending_up"]["volume_trend_min"]):
                detected_regime = "trending_up"
                
            # Phát hiện xu hướng giảm mạnh
            elif (adx >= self.REGIME_THRESHOLDS["trending_down"]["adx_min"] and 
                  trend_strength <= self.REGIME_THRESHOLDS["trending_down"]["trend_strength_max"] and
                  volatility <= self.REGIME_THRESHOLDS["trending_down"]["volatility_max"] and
                  volume_trend >= self.REGIME_THRESHOLDS["trending_down"]["volume_trend_min"]):
                detected_regime = "trending_down"
                
            # Phát hiện thị trường biến động mạnh
            elif (volatility >= self.REGIME_THRESHOLDS["volatile"]["volatility_min"] and 
                  abs(trend_strength) <= self.REGIME_THRESHOLDS["volatile"]["trend_strength_max_abs"] and
                  price_range >= self.REGIME_THRESHOLDS["volatile"]["price_range_min"]):
                detected_regime = "volatile"
                
            # Phát hiện thị trường sideway (dao động trong biên độ hẹp)
            elif (adx <= self.REGIME_THRESHOLDS["ranging"]["adx_max"] and
                  volatility <= self.REGIME_THRESHOLDS["ranging"]["volatility_max"] and
                  abs(trend_strength) <= self.REGIME_THRESHOLDS["ranging"]["trend_strength_max_abs"] and
                  bb_width <= self.REGIME_THRESHOLDS["ranging"]["bb_width_max"]):
                detected_regime = "ranging"
                
            # Nếu không rõ ràng, coi là neutral
            else:
                detected_regime = "neutral"
            
            # Kiểm tra độ ổn định của chế độ phát hiện được
            if detected_regime != self.current_regime:
                # Lưu chế độ trước đó
                self.previous_regime = self.current_regime
                
                # Cập nhật chế độ hiện tại và thời gian bắt đầu
                self.current_regime = detected_regime
                self.regime_start_time = datetime.now()
                
                # Log thay đổi chế độ
                logger.info(f"Chế độ thị trường thay đổi từ {self.previous_regime} sang {self.current_regime}")
                
                # Lưu vào lịch sử
                self._add_to_regime_history(self.current_regime)
                
            return self.current_regime
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return "neutral"
    
    def _detect_breakout(self, df: pd.DataFrame) -> bool:
        """
        Phát hiện thời điểm breakout (bứt phá) trong thị trường.
        
        Args:
            df (pd.DataFrame): DataFrame chứa dữ liệu giá và chỉ báo kỹ thuật
            
        Returns:
            bool: True nếu có breakout, False nếu không
        """
        try:
            if len(df) < 20:
                return False
                
            # Lấy dữ liệu N phiên gần nhất
            recent_data = df.iloc[-20:]
            
            # Kiểm tra sự tăng đột biến về biến động
            volatility_now = recent_data['Price_Volatility'].iloc[-1]
            volatility_prev = recent_data['Price_Volatility'].iloc[-5:].mean()
            
            if volatility_prev > 0:
                volatility_change = (volatility_now / volatility_prev) - 1
            else:
                volatility_change = 0
                
            # Kiểm tra sự tăng đột biến về khối lượng
            volume_now = recent_data['volume'].iloc[-1]
            volume_prev = recent_data['volume'].iloc[-5:].mean()
            
            if volume_prev > 0:
                volume_change = (volume_now / volume_prev) - 1
            else:
                volume_change = 0
                
            # Kiểm tra sự thay đổi giá đáng kể
            price_now = recent_data['close'].iloc[-1]
            price_prev = recent_data['close'].iloc[-2]
            
            if price_prev > 0:
                price_change = abs(price_now / price_prev - 1)
            else:
                price_change = 0
                
            # Các điều kiện breakout
            thresholds = self.REGIME_THRESHOLDS["breakout"]
            
            is_breakout = (
                volatility_change >= thresholds["volatility_increase"] and
                volume_change >= thresholds["volume_increase"] and
                price_change >= thresholds["price_move"]
            )
            
            return is_breakout
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện breakout: {str(e)}")
            return False
    
    def get_recommended_strategy(self) -> dict:
        """
        Đề xuất chiến lược giao dịch phù hợp với chế độ thị trường hiện tại.
        
        Returns:
            dict: Thông tin về chiến lược được đề xuất
        """
        regime = self.current_regime
        strategies = self.REGIME_STRATEGIES.get(regime, self.REGIME_STRATEGIES["neutral"])
        weights = self.REGIME_WEIGHTS.get(regime, self.REGIME_WEIGHTS["neutral"])
        
        return {
            "regime": regime,
            "strategies": strategies,
            "weights": weights,
            "primary_strategy": strategies[0] if strategies else "combined",
            "use_ml": "ml" in strategies[:2],  # Sử dụng ML nếu nó là một trong hai chiến lược hàng đầu
            "description": self._get_regime_description(regime)
        }
    
    def _get_regime_description(self, regime: str) -> dict:
        """
        Lấy mô tả chi tiết về một chế độ thị trường.
        
        Args:
            regime (str): Tên chế độ thị trường
            
        Returns:
            dict: Mô tả về chế độ thị trường bằng cả tiếng Anh và tiếng Việt
        """
        descriptions = {
            "trending_up": {
                "en": "Strong uptrend market - prices consistently moving higher with good momentum.",
                "vi": "Thị trường xu hướng tăng mạnh - giá liên tục tăng với động lực tốt."
            },
            "trending_down": {
                "en": "Strong downtrend market - prices consistently moving lower with momentum.",
                "vi": "Thị trường xu hướng giảm mạnh - giá liên tục giảm với động lực mạnh."
            },
            "volatile": {
                "en": "Highly volatile market - significant price swings with elevated uncertainty.",
                "vi": "Thị trường biến động mạnh - biên độ dao động lớn với độ bất định cao."
            },
            "ranging": {
                "en": "Ranging market - price moving sideways within a defined range.",
                "vi": "Thị trường đi ngang - giá dao động trong một khoảng hẹp xác định."
            },
            "breakout": {
                "en": "Market breakout - price breaking out of recent range with increased volume.",
                "vi": "Thị trường bứt phá - giá vượt ra khỏi vùng dao động gần đây với khối lượng tăng."
            },
            "neutral": {
                "en": "Neutral market - no clear directional bias or distinctive characteristics.",
                "vi": "Thị trường trung tính - không có xu hướng rõ ràng hoặc đặc điểm nổi bật."
            }
        }
        
        return descriptions.get(regime, descriptions["neutral"])
    
    def _add_to_regime_history(self, regime: str) -> None:
        """
        Thêm một chế độ mới vào lịch sử.
        
        Args:
            regime (str): Chế độ thị trường mới phát hiện
        """
        # Thêm chế độ trước đó vào lịch sử với thời gian kết thúc là hiện tại
        if self.regime_history:
            self.regime_history[-1]["end_time"] = datetime.now().isoformat()
            self.regime_history[-1]["duration"] = (
                datetime.now() - datetime.fromisoformat(self.regime_history[-1]["start_time"])
            ).total_seconds() / 60  # Thời gian tồn tại theo phút
        
        # Thêm chế độ mới
        self.regime_history.append({
            "regime": regime,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "duration": 0
        })
        
        # Cập nhật thống kê
        if regime not in self.regime_stats:
            self.regime_stats[regime] = {
                "count": 0,
                "total_duration": 0,
                "avg_duration": 0
            }
        
        self.regime_stats[regime]["count"] += 1
        
        # Lưu lịch sử và thống kê
        self._save_regime_history()
    
    def _save_regime_history(self) -> None:
        """Lưu lịch sử chế độ thị trường vào file."""
        try:
            # Lưu lịch sử
            with open(os.path.join(self.data_storage_path, 'regime_history.json'), 'w') as f:
                json.dump(self.regime_history, f, indent=2)
            
            # Cập nhật thống kê
            for regime, stats in self.regime_stats.items():
                # Tính thời gian trung bình
                if stats["count"] > 0:
                    stats["avg_duration"] = stats["total_duration"] / stats["count"]
            
            # Lưu thống kê
            with open(os.path.join(self.data_storage_path, 'regime_stats.json'), 'w') as f:
                json.dump(self.regime_stats, f, indent=2)
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử chế độ thị trường: {str(e)}")
    
    def _load_regime_history(self) -> None:
        """Tải lịch sử chế độ thị trường từ file."""
        try:
            # Tải lịch sử
            history_file = os.path.join(self.data_storage_path, 'regime_history.json')
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.regime_history = json.load(f)
                    
                # Cập nhật chế độ hiện tại từ lịch sử nếu có
                if self.regime_history:
                    latest = self.regime_history[-1]
                    self.current_regime = latest["regime"]
                    self.regime_start_time = datetime.fromisoformat(latest["start_time"])
            
            # Tải thống kê
            stats_file = os.path.join(self.data_storage_path, 'regime_stats.json')
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    self.regime_stats = json.load(f)
                    
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử chế độ thị trường: {str(e)}")
    
    def get_regime_performance(self) -> dict:
        """
        Lấy thông tin về hiệu suất của các chiến lược theo từng chế độ thị trường.
        
        Returns:
            dict: Thông tin hiệu suất theo chế độ
        """
        return self.regime_stats
    
    def update_regime_performance(self, regime: str, win: bool, pnl: float) -> None:
        """
        Cập nhật hiệu suất của một chiến lược trong một chế độ thị trường cụ thể.
        
        Args:
            regime (str): Chế độ thị trường
            win (bool): True nếu giao dịch thắng, False nếu thua
            pnl (float): Lợi nhuận/thua lỗ
        """
        try:
            if regime not in self.regime_stats:
                self.regime_stats[regime] = {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0,
                    "win_rate": 0,
                    "avg_pnl": 0
                }
            
            # Cập nhật thống kê giao dịch
            self.regime_stats[regime]["trades"] += 1
            if win:
                self.regime_stats[regime]["wins"] += 1
            else:
                self.regime_stats[regime]["losses"] += 1
            
            self.regime_stats[regime]["total_pnl"] += pnl
            
            # Cập nhật tỷ lệ thắng và PnL trung bình
            if self.regime_stats[regime]["trades"] > 0:
                self.regime_stats[regime]["win_rate"] = (
                    self.regime_stats[regime]["wins"] / self.regime_stats[regime]["trades"]
                )
                self.regime_stats[regime]["avg_pnl"] = (
                    self.regime_stats[regime]["total_pnl"] / self.regime_stats[regime]["trades"]
                )
            
            # Lưu thống kê
            self._save_regime_history()
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hiệu suất chế độ thị trường: {str(e)}")
    
    def get_best_ml_params_for_regime(self, regime: str) -> dict:
        """
        Lấy các tham số tối ưu cho mô hình học máy dựa trên chế độ thị trường.
        
        Args:
            regime (str): Chế độ thị trường
            
        Returns:
            dict: Các tham số tối ưu cho ML
        """
        # Tham số mặc định
        default_params = {
            "use_ensemble": True,
            "probability_threshold": 0.6,
            "feature_selection": True,
            "use_pca": False,
            "pca_components": 0,
            "preferred_model": "ensemble"
        }
        
        # Tham số tùy chỉnh theo chế độ
        regime_params = {
            "trending_up": {
                "probability_threshold": 0.55,  # Giảm ngưỡng để tận dụng trend
                "preferred_model": "gradient_boosting"
            },
            "trending_down": {
                "probability_threshold": 0.55,  # Giảm ngưỡng để tận dụng trend
                "preferred_model": "gradient_boosting"
            },
            "volatile": {
                "probability_threshold": 0.7,  # Tăng ngưỡng, thận trọng hơn
                "preferred_model": "random_forest"
            },
            "ranging": {
                "probability_threshold": 0.65,
                "preferred_model": "svm"
            },
            "breakout": {
                "probability_threshold": 0.6,
                "preferred_model": "ensemble"
            },
            "neutral": {
                "probability_threshold": 0.65,
                "preferred_model": "ensemble"
            }
        }
        
        # Kết hợp tham số mặc định với tham số theo chế độ
        params = default_params.copy()
        if regime in regime_params:
            params.update(regime_params[regime])
            
        return params