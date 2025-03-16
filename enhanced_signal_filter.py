#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Signal Filter - Bộ lọc tín hiệu nâng cao

Module này triển khai các bộ lọc nâng cao để cải thiện win rate cho chiến lược rủi ro cao.
Các bộ lọc được thiết kế để loại bỏ các tín hiệu giả và lựa chọn những cơ hội tốt nhất.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_signal_filter.log')
    ]
)

logger = logging.getLogger('enhanced_signal_filter')

class EnhancedSignalFilter:
    """
    Bộ lọc tín hiệu giao dịch nâng cao để cải thiện tỷ lệ thắng
    """
    
    def __init__(self, config_path: str = 'configs/enhanced_filter_config.json'):
        """
        Khởi tạo bộ lọc tín hiệu nâng cao
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self.load_or_create_config()
        self.timeframe_priority = {
            '1d': 3,  # Độ ưu tiên cao nhất
            '4h': 2,
            '1h': 1,
            '30m': 0
        }
        logger.info("Khởi tạo EnhancedSignalFilter với cấu hình từ %s", config_path)
    
    def load_or_create_config(self) -> Dict[str, Any]:
        """
        Tải hoặc tạo cấu hình mặc định
        
        Returns:
            Dict[str, Any]: Cấu hình
        """
        default_config = {
            "filter_settings": {
                "multi_timeframe": {
                    "enabled": True,
                    "min_confirmations": 2,
                    "timeframes": ["1d", "4h", "1h", "30m"],
                    "weight": {
                        "1d": 0.4,
                        "4h": 0.3,
                        "1h": 0.2,
                        "30m": 0.1
                    }
                },
                "market_regime": {
                    "enabled": True,
                    "preferred_regimes": {
                        "LONG": ["BULL", "STRONG_BULL", "RECOVERY"],
                        "SHORT": ["BEAR", "STRONG_BEAR", "DISTRIBUTION"]
                    },
                    "avoid_regimes": ["CHOPPY", "EXTREME_VOLATILE"]
                },
                "time_based": {
                    "enabled": True,
                    "preferred_windows": {
                        "london_open": {
                            "hours": [15, 16],
                            "preferred_direction": "SHORT",
                            "boost_factor": 1.25
                        },
                        "ny_open": {
                            "hours": [20, 21, 22],
                            "preferred_direction": "SHORT",
                            "boost_factor": 1.25
                        },
                        "daily_close": {
                            "hours": [6, 7],
                            "preferred_direction": "LONG",
                            "boost_factor": 1.0
                        }
                    },
                    "default_boost": 0.8
                },
                "volume_confirmation": {
                    "enabled": True,
                    "min_volume_ratio": 1.2,
                    "lookback_periods": 20
                },
                "trend_alignment": {
                    "enabled": True,
                    "lookback_periods": 100,
                    "min_slope": 0.01
                },
                "sl_tp_optimizations": {
                    "dynamic_sl": {
                        "trending": {
                            "sl_atr_mult": 2.0,
                            "tp_atr_mult": 3.5
                        },
                        "ranging": {
                            "sl_atr_mult": 1.7,
                            "tp_atr_mult": 3.0
                        },
                        "volatile": {
                            "sl_atr_mult": 1.9,
                            "tp_atr_mult": 3.2
                        }
                    }
                }
            },
            "weights": {
                "multi_timeframe": 0.3,
                "market_regime": 0.25,
                "time_based": 0.2,
                "volume_confirmation": 0.15,
                "trend_alignment": 0.1
            },
            "score_threshold": 0.65  # Điểm tối thiểu để chấp nhận tín hiệu
        }
        
        # Tạo thư mục configs nếu chưa tồn tại
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # Kiểm tra nếu file cấu hình tồn tại
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info("Đã tải cấu hình từ %s", self.config_path)
                return config
            except Exception as e:
                logger.error("Lỗi khi tải cấu hình: %s. Sử dụng cấu hình mặc định.", str(e))
                return default_config
        else:
            # Tạo file cấu hình mặc định
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                logger.info("Đã tạo cấu hình mặc định tại %s", self.config_path)
                return default_config
            except Exception as e:
                logger.error("Lỗi khi tạo cấu hình mặc định: %s", str(e))
                return default_config
    
    def filter_signal(self, signal_data: Dict[str, Any]) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Lọc tín hiệu dựa trên nhiều tiêu chí
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            Tuple[bool, float, Dict[str, Any]]:
                - accepted (bool): True nếu tín hiệu được chấp nhận
                - score (float): Điểm đánh giá tín hiệu (0-1)
                - details (Dict[str, Any]): Chi tiết đánh giá từng tiêu chí
        """
        scores = {}
        filter_settings = self.config["filter_settings"]
        weights = self.config["weights"]
        
        # 1. Đánh giá bằng nhiều timeframe
        if filter_settings["multi_timeframe"]["enabled"]:
            multi_tf_score = self._evaluate_multi_timeframe(signal_data)
            scores["multi_timeframe"] = multi_tf_score
        
        # 2. Đánh giá chế độ thị trường
        if filter_settings["market_regime"]["enabled"]:
            regime_score = self._evaluate_market_regime(signal_data)
            scores["market_regime"] = regime_score
        
        # 3. Đánh giá theo thời gian
        if filter_settings["time_based"]["enabled"]:
            time_score = self._evaluate_time_window(signal_data)
            scores["time_based"] = time_score
        
        # 4. Đánh giá volume
        if filter_settings["volume_confirmation"]["enabled"]:
            volume_score = self._evaluate_volume(signal_data)
            scores["volume_confirmation"] = volume_score
        
        # 5. Đánh giá xu hướng
        if filter_settings["trend_alignment"]["enabled"]:
            trend_score = self._evaluate_trend_alignment(signal_data)
            scores["trend_alignment"] = trend_score
        
        # Tính điểm tổng hợp
        final_score = 0.0
        for key, score in scores.items():
            final_score += score * weights.get(key, 0.0)
        
        # Kiểm tra ngưỡng
        accepted = final_score >= self.config["score_threshold"]
        
        # Điều chỉnh SL/TP nếu tín hiệu được chấp nhận
        sl_tp_adjustments = {}
        if accepted:
            sl_tp_adjustments = self._optimize_sl_tp(signal_data)
        
        details = {
            "scores": scores,
            "sl_tp_adjustments": sl_tp_adjustments
        }
        
        logger.info(
            "Đánh giá tín hiệu %s %s trên %s, kết quả: %s (score: %.2f)",
            signal_data.get("direction", "UNKNOWN"),
            signal_data.get("symbol", "UNKNOWN"),
            signal_data.get("timeframe", "UNKNOWN"),
            "CHẤP NHẬN" if accepted else "TỪ CHỐI",
            final_score
        )
        
        return accepted, final_score, details
    
    def _evaluate_multi_timeframe(self, signal_data: Dict[str, Any]) -> float:
        """
        Đánh giá tín hiệu theo nhiều khung thời gian
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            float: Điểm đánh giá (0-1)
        """
        multi_tf = self.config["filter_settings"]["multi_timeframe"]
        timeframes = multi_tf["timeframes"]
        weights = multi_tf["weight"]
        
        # Kiểm tra xem có dữ liệu về nhiều timeframe hay không
        if "multi_timeframe_signals" not in signal_data:
            return 0.5  # Giá trị trung bình nếu không có dữ liệu
        
        mtf_signals = signal_data["multi_timeframe_signals"]
        direction = signal_data.get("direction", "UNKNOWN")
        
        # Đếm số timeframe xác nhận cùng hướng
        confirming_timeframes = 0
        weighted_score = 0.0
        
        for tf in timeframes:
            if tf in mtf_signals and mtf_signals[tf] == direction:
                confirming_timeframes += 1
                weighted_score += weights.get(tf, 0.0)
        
        # Kiểm tra số lượng timeframe xác nhận tối thiểu
        if confirming_timeframes < multi_tf["min_confirmations"]:
            return 0.3  # Điểm thấp nếu không đủ xác nhận
        
        return min(1.0, weighted_score)
    
    def _evaluate_market_regime(self, signal_data: Dict[str, Any]) -> float:
        """
        Đánh giá tín hiệu theo chế độ thị trường
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            float: Điểm đánh giá (0-1)
        """
        market_regime = self.config["filter_settings"]["market_regime"]
        current_regime = signal_data.get("market_regime", "NEUTRAL")
        direction = signal_data.get("direction", "UNKNOWN")
        
        # Trường hợp nên tránh
        if current_regime in market_regime["avoid_regimes"]:
            return 0.2
        
        # Trường hợp khớp với hướng ưu tiên
        preferred_regimes = market_regime["preferred_regimes"].get(direction, [])
        
        if current_regime in preferred_regimes:
            return 1.0
        
        # Trường hợp không khớp hoặc không có thông tin
        return 0.5
    
    def _evaluate_time_window(self, signal_data: Dict[str, Any]) -> float:
        """
        Đánh giá tín hiệu theo cửa sổ thời gian
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            float: Điểm đánh giá (0-1)
        """
        time_based = self.config["filter_settings"]["time_based"]
        direction = signal_data.get("direction", "UNKNOWN")
        
        # Lấy giờ hiện tại
        signal_time = signal_data.get("timestamp", datetime.now())
        if isinstance(signal_time, str):
            try:
                signal_time = datetime.fromisoformat(signal_time.replace('Z', '+00:00'))
            except:
                signal_time = datetime.now()
        
        current_hour = signal_time.hour
        
        # Kiểm tra từng cửa sổ thời gian ưu tiên
        for window_name, window_config in time_based["preferred_windows"].items():
            hours = window_config["hours"]
            preferred_direction = window_config["preferred_direction"]
            boost_factor = window_config["boost_factor"]
            
            if current_hour in hours:
                # Trong cửa sổ thời gian ưu tiên
                if direction == preferred_direction:
                    return boost_factor  # Boost nếu khớp hướng ưu tiên
                else:
                    return 0.7  # Vẫn ổn nhưng không boost
        
        # Không nằm trong cửa sổ ưu tiên
        return time_based["default_boost"]
    
    def _evaluate_volume(self, signal_data: Dict[str, Any]) -> float:
        """
        Đánh giá tín hiệu theo volume
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            float: Điểm đánh giá (0-1)
        """
        volume_config = self.config["filter_settings"]["volume_confirmation"]
        
        # Kiểm tra nếu có thông tin volume
        if "volume_ratio" not in signal_data:
            return 0.5  # Giá trị trung bình nếu không có dữ liệu
        
        volume_ratio = signal_data["volume_ratio"]
        
        # Đánh giá dựa trên tỷ lệ volume
        if volume_ratio >= volume_config["min_volume_ratio"]:
            # Tỷ lệ volume càng cao càng tốt, cấp số nhân đến 2.0
            score = min(1.0, 0.7 + 0.3 * (volume_ratio - volume_config["min_volume_ratio"]))
            return score
        else:
            # Volume thấp, giảm điểm
            ratio = volume_ratio / volume_config["min_volume_ratio"]
            return max(0.3, ratio * 0.5)
    
    def _evaluate_trend_alignment(self, signal_data: Dict[str, Any]) -> float:
        """
        Đánh giá tín hiệu theo sự phù hợp với xu hướng
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            float: Điểm đánh giá (0-1)
        """
        trend_config = self.config["filter_settings"]["trend_alignment"]
        direction = signal_data.get("direction", "UNKNOWN")
        
        # Kiểm tra nếu có thông tin xu hướng
        if "trend_slope" not in signal_data:
            return 0.5  # Giá trị trung bình nếu không có dữ liệu
        
        trend_slope = signal_data["trend_slope"]
        min_slope = trend_config["min_slope"]
        
        # Đánh giá dựa trên độ dốc xu hướng và hướng giao dịch
        if direction == "LONG":
            if trend_slope >= min_slope:
                # Xu hướng tăng khớp với LONG
                return min(1.0, 0.7 + 0.3 * (trend_slope / min_slope))
            else:
                # Xu hướng không khớp với LONG
                return max(0.3, 0.7 + trend_slope)
        elif direction == "SHORT":
            if trend_slope <= -min_slope:
                # Xu hướng giảm khớp với SHORT
                return min(1.0, 0.7 + 0.3 * (abs(trend_slope) / min_slope))
            else:
                # Xu hướng không khớp với SHORT
                return max(0.3, 0.7 - trend_slope)
        
        return 0.5  # Mặc định nếu không có thông tin rõ ràng
    
    def _optimize_sl_tp(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tối ưu hóa SL/TP dựa trên điều kiện thị trường
        
        Args:
            signal_data (Dict[str, Any]): Dữ liệu tín hiệu
        
        Returns:
            Dict[str, Any]: Điều chỉnh SL/TP
        """
        sl_tp_config = self.config["filter_settings"]["sl_tp_optimizations"]["dynamic_sl"]
        market_regime = signal_data.get("market_regime", "NEUTRAL")
        
        # Xác định chế độ thị trường thích hợp để điều chỉnh SL/TP
        if market_regime in ["BULL", "STRONG_BULL", "BEAR", "STRONG_BEAR"]:
            regime_type = "trending"
        elif market_regime in ["CHOPPY", "VOLATILE"]:
            regime_type = "volatile"
        else:
            regime_type = "ranging"
        
        # Lấy hệ số điều chỉnh từ cấu hình
        regime_config = sl_tp_config.get(regime_type, sl_tp_config["ranging"])
        sl_atr_mult = regime_config["sl_atr_mult"]
        tp_atr_mult = regime_config["tp_atr_mult"]
        
        return {
            "sl_atr_mult": sl_atr_mult,
            "tp_atr_mult": tp_atr_mult,
            "regime_type": regime_type
        }

def test_enhanced_filter():
    """
    Hàm kiểm tra bộ lọc tín hiệu nâng cao
    """
    filter = EnhancedSignalFilter()
    
    # Tạo dữ liệu tín hiệu mẫu
    sample_signal = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "timeframe": "4h",
        "timestamp": datetime.now(),
        "market_regime": "BULL",
        "volume_ratio": 1.5,
        "trend_slope": 0.02,
        "multi_timeframe_signals": {
            "1d": "LONG",
            "4h": "LONG",
            "1h": "NEUTRAL",
            "30m": "SHORT"
        }
    }
    
    # Lọc tín hiệu
    accepted, score, details = filter.filter_signal(sample_signal)
    
    print(f"Tín hiệu: {sample_signal['direction']} {sample_signal['symbol']} ({sample_signal['timeframe']})")
    print(f"Kết quả: {'CHẤP NHẬN' if accepted else 'TỪ CHỐI'} (Score: {score:.2f})")
    print("Chi tiết điểm:")
    for key, value in details["scores"].items():
        print(f"  - {key}: {value:.2f}")
    
    if "sl_tp_adjustments" in details and details["sl_tp_adjustments"]:
        print("Điều chỉnh SL/TP:")
        for key, value in details["sl_tp_adjustments"].items():
            print(f"  - {key}: {value}")

if __name__ == "__main__":
    test_enhanced_filter()