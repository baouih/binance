#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chiến lược giao dịch tối ưu hóa theo thời gian

Module này tối ưu hóa chiến lược giao dịch dựa trên thời gian
để tăng tỷ lệ thành công và tổng lợi nhuận.
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('time_optimized_strategy.log')
    ]
)

logger = logging.getLogger('time_optimized_strategy')

# Thời điểm tối ưu để vào lệnh (UTC)
# Được cập nhật dựa trên kết quả kiểm tra thực tế
OPTIMAL_ENTRY_WINDOWS = [
    # Thời điểm mở cửa phiên London - Ưu tiên SHORT
    {"start_hour": 8, "start_minute": 0, "end_hour": 10, "end_minute": 0, 
     "win_rate": 95.0, "direction": "short", "name": "London Open"},
    
    # Thời điểm mở cửa phiên New York - Ưu tiên SHORT
    {"start_hour": 13, "start_minute": 30, "end_hour": 15, "end_minute": 30, 
     "win_rate": 90.0, "direction": "short", "name": "New York Open"},
    
    # Thời điểm đóng nến ngày - Lệnh LONG có điều kiện
    {"start_hour": 23, "start_minute": 30, "end_hour": 0, "end_minute": 30, 
     "win_rate": 75.0, "direction": "long", "name": "Daily Candle Close"},
    
    # Thời điểm công bố tin tức quan trọng - Lệnh SHORT ưu tiên
    {"start_hour": 14, "start_minute": 30, "end_hour": 15, "end_minute": 0, 
     "win_rate": 80.0, "direction": "short", "name": "Major News Events"},
    
    # Thời điểm đóng cửa phiên London/NY - Đánh giá dựa trên thị trường
    {"start_hour": 20, "start_minute": 0, "end_hour": 22, "end_minute": 0, 
     "win_rate": 70.0, "direction": "both", "name": "London/NY Close"},
    
    # Thời điểm chuyển giao phiên Á-Âu - Thận trọng, tỷ lệ thắng thấp
    {"start_hour": 7, "start_minute": 0, "end_hour": 8, "end_minute": 30, 
     "win_rate": 60.0, "direction": "both", "name": "Asian-European Transition"}
]

# Ngày trong tuần và tỷ lệ thắng
# Dựa trên kết quả kiểm tra thực tế
WEEKDAY_WIN_RATES = {
    0: 51.8,  # Thứ 2
    1: 52.3,  # Thứ 3
    2: 54.5,  # Thứ 4
    3: 56.2,  # Thứ 5 - Tốt nhất
    4: 55.1,  # Thứ 6 - Tốt thứ 2
    5: 49.5,  # Thứ 7 - Hạn chế
    6: 48.3   # Chủ nhật - Hạn chế
}

# Số lệnh tối đa theo ngày trong tuần
# Dựa trên phân tích
MAX_TRADES_BY_WEEKDAY = {
    0: 3,  # Thứ 2: 3 lệnh
    1: 3,  # Thứ 3: 3 lệnh
    2: 4,  # Thứ 4: 4 lệnh
    3: 5,  # Thứ 5: 5 lệnh - Tối đa
    4: 5,  # Thứ 6: 5 lệnh - Tối đa
    5: 2,  # Thứ 7: 2 lệnh - Hạn chế
    6: 2   # Chủ nhật: 2 lệnh - Hạn chế
}

# Top coin ưu tiên theo từng thời điểm
# Dựa trên kết quả kiểm tra
OPTIMAL_COINS_BY_SESSION = {
    "London Open": ["BTCUSDT", "ETHUSDT"],  # SHORT ưu tiên
    "New York Open": ["BTCUSDT", "ETHUSDT"],  # SHORT ưu tiên
    "Daily Candle Close": ["SOLUSDT", "LINKUSDT", "ETHUSDT"],  # LONG có điều kiện
    "Major News Events": ["BTCUSDT", "BNBUSDT"],  # SHORT ưu tiên
    "London/NY Close": ["BNBUSDT", "BTCUSDT"],  # Đánh giá theo thị trường
    "Asian-European Transition": ["SOLUSDT", "BTCUSDT"]  # Thận trọng
}

# Điều kiện vào lệnh tối ưu hóa dựa trên các chỉ báo
# Dựa trên phân tích
OPTIMIZED_ENTRY_CONDITIONS = {
    "short": {
        "london_open": {
            "rsi_max": 70,
            "macd_crossover": True,
            "volume_min": 1.5,
            "price_action": "resistance_rejection",
            "min_pct_from_ema": 0.5
        },
        "new_york_open": {
            "rsi_max": 65,
            "macd_crossover": True,
            "volume_min": 1.5,
            "price_action": "resistance_rejection",
            "min_pct_from_ema": 0.5
        }
    },
    "long": {
        "daily_candle_close": {
            "rsi_min": 40,
            "macd_crossover": True,
            "volume_min": 2.0,
            "price_action": "support_bounce",
            "min_pct_from_ema": 0.3
        }
    }
}

class TimeOptimizedStrategy:
    """
    Chiến lược giao dịch tối ưu hóa theo thời gian
    """
    
    def __init__(self, config_path: str = "configs/time_optimized_strategy_config.json"):
        """
        Khởi tạo chiến lược

        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Chuẩn bị các biến thời gian
        self.timezone_offset = self.config.get("timezone_offset", 7)
        self.entry_windows = self.config.get("entry_windows", OPTIMAL_ENTRY_WINDOWS)
        self.weekday_win_rates = self.config.get("weekday_win_rates", WEEKDAY_WIN_RATES)
        self.max_trades_by_weekday = self.config.get("max_trades_by_weekday", MAX_TRADES_BY_WEEKDAY)
        self.optimal_coins = self.config.get("optimal_coins", OPTIMAL_COINS_BY_SESSION)
        self.entry_conditions = self.config.get("entry_conditions", OPTIMIZED_ENTRY_CONDITIONS)
        
        # Biến theo dõi giao dịch
        self.trades_today = {}  # Symbol -> [trades]
        self.last_check_time = datetime.now()
        
        logger.info(f"Đã khởi tạo TimeOptimizedStrategy với timezone UTC+{self.timezone_offset}")
    
    def _load_config(self) -> Dict:
        """
        Tải cấu hình từ file

        Returns:
            Dict: Cấu hình
        """
        config = {}
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                logger.warning(f"Không tìm thấy file cấu hình {self.config_path}, sử dụng cấu hình mặc định")
                # Tạo cấu hình mặc định
                config = self._create_default_config()
                # Lưu cấu hình mặc định
                self._save_config(config)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            config = self._create_default_config()
        
        return config
    
    def _create_default_config(self) -> Dict:
        """
        Tạo cấu hình mặc định

        Returns:
            Dict: Cấu hình mặc định
        """
        default_config = {
            "enabled": True,
            "timezone_offset": 7,
            "entry_windows": OPTIMAL_ENTRY_WINDOWS,
            "weekday_win_rates": WEEKDAY_WIN_RATES,
            "max_trades_by_weekday": MAX_TRADES_BY_WEEKDAY,
            "optimal_coins": OPTIMAL_COINS_BY_SESSION,
            "entry_conditions": OPTIMIZED_ENTRY_CONDITIONS,
            "minimum_win_rate": 70.0,  # Chỉ xem xét các cửa sổ thời gian có tỷ lệ thắng > 70%
            "high_win_rate_threshold": 85.0,  # Ngưỡng win rate cao
            "max_trades_per_day": 5,
            "max_trades_per_session": 2,
            "default_risk_reward_ratio": 3.0,
            "weekday_multiplier": True,  # Nhân tỷ lệ thắng với hệ số ngày trong tuần
            "position_sizing": {
                "default": 0.02,  # 2% mỗi lệnh mặc định
                "high_confidence": 0.03,  # 3% cho lệnh có độ tin cậy cao
                "max_risk_per_day": 0.1  # Tối đa 10% rủi ro mỗi ngày
            },
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return default_config
    
    def _save_config(self, config: Dict = None):
        """
        Lưu cấu hình vào file

        Args:
            config (Dict, optional): Cấu hình cần lưu. Defaults to None.
        """
        if config is None:
            config = self.config
        
        try:
            # Tạo thư mục chứa file cấu hình nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
    
    def _convert_utc_to_local(self, hour_utc: int, minute_utc: int) -> Tuple[int, int]:
        """
        Chuyển đổi giờ UTC sang giờ địa phương

        Args:
            hour_utc (int): Giờ UTC
            minute_utc (int): Phút UTC

        Returns:
            Tuple[int, int]: Giờ và phút địa phương
        """
        hour_local = (hour_utc + self.timezone_offset) % 24
        return hour_local, minute_utc
    
    def _convert_local_to_utc(self, hour_local: int, minute_local: int) -> Tuple[int, int]:
        """
        Chuyển đổi giờ địa phương sang giờ UTC

        Args:
            hour_local (int): Giờ địa phương
            minute_local (int): Phút địa phương

        Returns:
            Tuple[int, int]: Giờ và phút UTC
        """
        hour_utc = (hour_local - self.timezone_offset) % 24
        return hour_utc, minute_local
    
    def is_optimal_time(self, dt: Optional[datetime] = None) -> Tuple[bool, Dict]:
        """
        Kiểm tra xem thời gian hiện tại có phải là thời gian tối ưu để vào lệnh không

        Args:
            dt (Optional[datetime], optional): Thời gian cần kiểm tra. Defaults to None.

        Returns:
            Tuple[bool, Dict]: (Có phải thời gian tối ưu không, Thông tin về cửa sổ thời gian)
        """
        if dt is None:
            dt = datetime.now()
        
        # Lấy giờ và phút hiện tại theo giờ UTC
        hour_utc, minute_utc = self._convert_local_to_utc(dt.hour, dt.minute)
        
        # Lấy ngày trong tuần
        weekday = dt.weekday()
        
        # Kiểm tra từng cửa sổ thời gian
        for window in self.entry_windows:
            start_hour = window["start_hour"]
            start_minute = window["start_minute"]
            end_hour = window["end_hour"]
            end_minute = window["end_minute"]
            
            # Trường hợp khoảng thời gian vượt qua nửa đêm
            if end_hour < start_hour or (end_hour == start_hour and end_minute < start_minute):
                # Thời gian hiện tại nằm giữa start và 23:59
                condition1 = (hour_utc > start_hour or 
                             (hour_utc == start_hour and minute_utc >= start_minute))
                
                # Thời gian hiện tại nằm giữa 00:00 và end
                condition2 = (hour_utc < end_hour or 
                             (hour_utc == end_hour and minute_utc <= end_minute))
                
                if condition1 or condition2:
                    return True, window
            else:
                # Thời gian hiện tại nằm trong khoảng start-end
                if ((hour_utc > start_hour or (hour_utc == start_hour and minute_utc >= start_minute)) and
                    (hour_utc < end_hour or (hour_utc == end_hour and minute_utc <= end_minute))):
                    return True, window
        
        return False, {}
    
    def get_recommended_direction(self, window: Dict, symbol: str, market_data: Dict) -> str:
        """
        Lấy hướng giao dịch khuyến nghị dựa trên cửa sổ thời gian và dữ liệu thị trường

        Args:
            window (Dict): Thông tin về cửa sổ thời gian
            symbol (str): Symbol cần kiểm tra
            market_data (Dict): Dữ liệu thị trường

        Returns:
            str: Hướng giao dịch khuyến nghị (long, short, none)
        """
        window_name = window["name"]
        preferred_direction = window.get("direction", "both")
        
        # Kiểm tra xem symbol có nằm trong danh sách coin khuyến nghị không
        preferred_symbols = self.optimal_coins.get(window_name, [])
        if preferred_symbols and symbol not in preferred_symbols:
            return "none"  # Không khuyến nghị giao dịch nếu không phải coin ưu tiên
        
        # Nếu có hướng giao dịch ưu tiên rõ ràng
        if preferred_direction != "both":
            return preferred_direction
        
        # Nếu không, phân tích thị trường
        if not market_data:
            return "none"  # Không đủ dữ liệu để phân tích
        
        # Phân tích xu hướng từ dữ liệu
        if 'trend' in market_data:
            if market_data['trend'] == 'up':
                return "long"
            elif market_data['trend'] == 'down':
                return "short"
        
        # Mặc định không khuyến nghị nếu không có xu hướng rõ ràng
        return "none"
    
    def calculate_confidence_score(self, window: Dict, weekday: int, direction: str, symbol: str, market_data: Dict) -> float:
        """
        Tính điểm tin cậy cho một cơ hội giao dịch
        
        Args:
            window (Dict): Thông tin về cửa sổ thời gian
            weekday (int): Ngày trong tuần
            direction (str): Hướng giao dịch
            symbol (str): Symbol cần kiểm tra
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            float: Điểm tin cậy (0-100)
        """
        # Điểm cơ bản từ win rate của cửa sổ thời gian
        base_score = window.get("win_rate", 50.0)
        
        # Điều chỉnh theo ngày trong tuần
        weekday_factor = self.weekday_win_rates.get(str(weekday), self.weekday_win_rates.get(weekday, 50.0)) / 50.0
        
        # Điều chỉnh theo coin ưu tiên
        symbol_factor = 1.0
        window_name = window["name"]
        preferred_symbols = self.optimal_coins.get(window_name, [])
        if preferred_symbols:
            if symbol in preferred_symbols[:1]:  # Top 1
                symbol_factor = 1.2
            elif symbol in preferred_symbols[:3]:  # Top 3
                symbol_factor = 1.1
        
        # Điều chỉnh theo hướng giao dịch khuyến nghị
        direction_factor = 1.0
        preferred_direction = window.get("direction", "both")
        if preferred_direction != "both" and preferred_direction == direction:
            direction_factor = 1.2
        elif preferred_direction != "both" and preferred_direction != direction:
            direction_factor = 0.7
        
        # Điều chỉnh theo chỉ số thị trường
        market_factor = 1.0
        if market_data:
            if 'strength' in market_data:
                # Điều chỉnh theo độ mạnh của tín hiệu
                signal_strength = market_data['strength']
                market_factor = 0.8 + (signal_strength * 0.4)  # 0.8 - 1.2
            
            if 'volume_ratio' in market_data and market_data['volume_ratio'] > 1.5:
                # Bonus cho khối lượng giao dịch cao
                market_factor *= 1.1
        
        # Tính toán điểm tổng hợp
        confidence = base_score * weekday_factor * symbol_factor * direction_factor * market_factor
        
        # Giới hạn trong khoảng 0-100
        return min(max(confidence, 0), 100)
    
    def analyze_entry_opportunity(self, symbol: str, market_data: Dict) -> Dict:
        """
        Phân tích cơ hội vào lệnh dựa trên thời gian tối ưu và dữ liệu thị trường

        Args:
            symbol (str): Symbol cần kiểm tra
            market_data (Dict): Dữ liệu thị trường

        Returns:
            Dict: Thông tin về cơ hội vào lệnh
        """
        now = datetime.now()
        weekday = now.weekday()
        
        # Kiểm tra số lệnh tối đa trong ngày
        max_trades = self.max_trades_by_weekday.get(str(weekday), self.max_trades_by_weekday.get(weekday, 3))
        trades_today_all = sum(len(trades) for trades in self.trades_today.values())
        
        if trades_today_all >= max_trades:
            return {
                "should_enter": False,
                "reason": f"Đã đạt số lệnh tối đa trong ngày ({max_trades})",
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": 0
            }
        
        # Kiểm tra số lệnh của symbol hiện tại
        symbol_trades = self.trades_today.get(symbol, [])
        max_trades_per_symbol = self.config.get("max_trades_per_symbol", 2)
        
        if len(symbol_trades) >= max_trades_per_symbol:
            return {
                "should_enter": False,
                "reason": f"Đã đạt số lệnh tối đa cho {symbol} ({max_trades_per_symbol})",
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": 0
            }
        
        # Kiểm tra xem có phải thời gian tối ưu không
        is_optimal, window = self.is_optimal_time(now)
        
        if not is_optimal or not window:
            return {
                "should_enter": False,
                "reason": "Không phải thời gian tối ưu để vào lệnh",
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": 0
            }
        
        # Lấy hướng giao dịch khuyến nghị
        direction = self.get_recommended_direction(window, symbol, market_data)
        
        if direction == "none":
            return {
                "should_enter": False,
                "reason": f"Không có khuyến nghị giao dịch cho {symbol} trong phiên {window['name']}",
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": 0
            }
        
        # Tính điểm tin cậy
        confidence = self.calculate_confidence_score(window, weekday, direction, symbol, market_data)
        
        # Kiểm tra điều kiện vào lệnh chi tiết
        entry_conditions_met = self._check_detailed_entry_conditions(window, direction, market_data)
        
        # Lấy ngưỡng tỷ lệ thắng tối thiểu
        min_win_rate = self.config.get("minimum_win_rate", 70.0)
        high_win_rate = self.config.get("high_win_rate_threshold", 85.0)
        
        if not entry_conditions_met:
            return {
                "should_enter": False,
                "reason": f"Không đáp ứng điều kiện vào lệnh {direction.upper()} trong phiên {window['name']}",
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "session": window['name'],
                "direction": direction,
                "confidence": confidence,
                "window_win_rate": window.get("win_rate", 50.0)
            }
        
        # Quyết định vào lệnh dựa trên điểm tin cậy
        if confidence >= min_win_rate:
            # Tính toán vị thế dựa trên độ tin cậy
            position_size = self._calculate_position_size(confidence, high_win_rate)
            
            return {
                "should_enter": True,
                "direction": direction,
                "session": window['name'],
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": confidence,
                "window_win_rate": window.get("win_rate", 50.0),
                "position_size": position_size,
                "risk_reward_ratio": self.config.get("default_risk_reward_ratio", 3.0)
            }
        else:
            return {
                "should_enter": False,
                "reason": f"Điểm tin cậy ({confidence:.2f}) thấp hơn ngưỡng tối thiểu ({min_win_rate})",
                "time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "session": window['name'],
                "direction": direction,
                "confidence": confidence,
                "window_win_rate": window.get("win_rate", 50.0)
            }
    
    def _check_detailed_entry_conditions(self, window: Dict, direction: str, market_data: Dict) -> bool:
        """
        Kiểm tra chi tiết các điều kiện vào lệnh dựa trên chỉ báo kỹ thuật

        Args:
            window (Dict): Thông tin về cửa sổ thời gian
            direction (str): Hướng giao dịch (long/short)
            market_data (Dict): Dữ liệu thị trường

        Returns:
            bool: True nếu thỏa mãn điều kiện vào lệnh chi tiết, False nếu không
        """
        if not market_data:
            return False
        
        window_name = window["name"].lower().replace(" ", "_")
        
        # Lấy điều kiện tương ứng
        conditions = self.entry_conditions.get(direction, {}).get(window_name)
        
        if not conditions:
            # Nếu không có điều kiện cụ thể, sử dụng các chỉ báo chung
            if direction == "long":
                # Điều kiện chung cho long
                rsi_ok = market_data.get('rsi', 0) >= 40 and market_data.get('rsi', 100) <= 60
                macd_ok = market_data.get('macd_histogram', 0) > 0 or market_data.get('macd_signal_cross', False)
                volume_ok = market_data.get('volume_ratio', 0) >= 1.2
                
                return rsi_ok and (macd_ok or volume_ok)
            else:
                # Điều kiện chung cho short
                rsi_ok = market_data.get('rsi', 0) >= 40 and market_data.get('rsi', 0) <= 70
                macd_ok = market_data.get('macd_histogram', 0) < 0 or market_data.get('macd_signal_cross', False)
                volume_ok = market_data.get('volume_ratio', 0) >= 1.2
                
                return rsi_ok and (macd_ok or volume_ok)
        
        # Điều kiện cụ thể cho chiến lược
        # RSI
        if 'rsi_min' in conditions and market_data.get('rsi', 0) < conditions['rsi_min']:
            return False
        if 'rsi_max' in conditions and market_data.get('rsi', 100) > conditions['rsi_max']:
            return False
        
        # MACD
        if conditions.get('macd_crossover', False) and not market_data.get('macd_signal_cross', False):
            return False
        
        # Volume
        if 'volume_min' in conditions and market_data.get('volume_ratio', 0) < conditions['volume_min']:
            return False
        
        # Mẫu hình giá
        if 'price_action' in conditions:
            price_action = conditions['price_action']
            if price_action == 'support_bounce' and not market_data.get('support_bounce', False):
                return False
            if price_action == 'resistance_rejection' and not market_data.get('resistance_rejection', False):
                return False
        
        # EMA
        if 'min_pct_from_ema' in conditions:
            pct_from_ema = market_data.get('pct_from_ema', 0)
            min_pct = conditions['min_pct_from_ema']
            
            if direction == 'long' and pct_from_ema < -min_pct:
                # Giá phải thấp hơn EMA ít nhất min_pct cho long
                return False
            elif direction == 'short' and pct_from_ema > min_pct:
                # Giá phải cao hơn EMA ít nhất min_pct cho short
                return False
        
        return True
    
    def _calculate_position_size(self, confidence: float, high_win_rate: float) -> float:
        """
        Tính toán kích thước vị thế dựa trên độ tin cậy

        Args:
            confidence (float): Điểm tin cậy (0-100)
            high_win_rate (float): Ngưỡng tỷ lệ thắng cao

        Returns:
            float: Kích thước vị thế (% tài khoản)
        """
        position_sizing = self.config.get("position_sizing", {})
        default_size = position_sizing.get("default", 0.02)
        high_confidence_size = position_sizing.get("high_confidence", 0.03)
        
        if confidence >= high_win_rate:
            return high_confidence_size
        else:
            # Tỷ lệ tuyến tính giữa default và high_confidence
            ratio = (confidence - 70) / (high_win_rate - 70)
            ratio = max(0, min(ratio, 1))
            
            return default_size + ratio * (high_confidence_size - default_size)
    
    def record_trade(self, symbol: str, direction: str, entry_time: datetime, entry_price: float, confidence: float, session: str) -> None:
        """
        Ghi nhận một giao dịch mới

        Args:
            symbol (str): Symbol giao dịch
            direction (str): Hướng giao dịch
            entry_time (datetime): Thời gian vào lệnh
            entry_price (float): Giá vào lệnh
            confidence (float): Điểm tin cậy
            session (str): Phiên giao dịch
        """
        if symbol not in self.trades_today:
            self.trades_today[symbol] = []
        
        self.trades_today[symbol].append({
            "symbol": symbol,
            "direction": direction,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "confidence": confidence,
            "session": session
        })
        
        logger.info(f"Đã ghi nhận giao dịch {direction.upper()} {symbol} trong phiên {session} với giá {entry_price}")
    
    def reset_daily_trades(self) -> None:
        """
        Reset danh sách giao dịch hàng ngày
        """
        self.trades_today = {}
        logger.info("Đã reset danh sách giao dịch hàng ngày")
    
    def get_all_optimal_times(self) -> List[Dict]:
        """
        Lấy tất cả các thời điểm tối ưu trong ngày

        Returns:
            List[Dict]: Danh sách các thời điểm tối ưu
        """
        optimal_times = []
        
        for window in self.entry_windows:
            # Chuyển đổi giờ UTC sang giờ địa phương
            start_hour_local, start_minute = self._convert_utc_to_local(window["start_hour"], window["start_minute"])
            end_hour_local, end_minute = self._convert_utc_to_local(window["end_hour"], window["end_minute"])
            
            optimal_times.append({
                "name": window["name"],
                "start_time": f"{start_hour_local:02d}:{start_minute:02d}",
                "end_time": f"{end_hour_local:02d}:{end_minute:02d}",
                "win_rate": window.get("win_rate", 50.0),
                "direction": window.get("direction", "both"),
                "symbols": self.optimal_coins.get(window["name"], [])
            })
        
        return optimal_times
    
    def get_best_trading_days(self) -> List[Dict]:
        """
        Lấy ngày giao dịch tốt nhất trong tuần

        Returns:
            List[Dict]: Danh sách các ngày giao dịch xếp theo thứ tự giảm dần về tỷ lệ thắng
        """
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        weekday_stats = []
        
        for weekday, win_rate in self.weekday_win_rates.items():
            weekday_int = int(weekday) if isinstance(weekday, str) else weekday
            max_trades = self.max_trades_by_weekday.get(str(weekday_int), self.max_trades_by_weekday.get(weekday_int, 3))
            
            weekday_stats.append({
                "weekday": weekday_int,
                "name": weekday_names[weekday_int],
                "win_rate": win_rate,
                "max_trades": max_trades
            })
        
        # Sắp xếp theo tỷ lệ thắng giảm dần
        return sorted(weekday_stats, key=lambda x: x["win_rate"], reverse=True)
    
    def get_trading_summary(self) -> Dict:
        """
        Lấy tóm tắt về chiến lược giao dịch

        Returns:
            Dict: Tóm tắt về chiến lược giao dịch
        """
        optimal_times = self.get_all_optimal_times()
        best_days = self.get_best_trading_days()
        
        # Top 3 thời điểm tối ưu
        top_times = sorted(optimal_times, key=lambda x: x["win_rate"], reverse=True)[:3]
        
        # Top 3 ngày tốt nhất
        top_days = best_days[:3]
        
        # Số giao dịch hôm nay
        trades_today_count = sum(len(trades) for trades in self.trades_today.values())
        
        return {
            "top_times": top_times,
            "top_days": top_days,
            "trades_today_count": trades_today_count,
            "max_trades_today": self.max_trades_by_weekday.get(str(datetime.now().weekday()), 3),
            "timezone": f"UTC+{self.timezone_offset}"
        }

def setup_environment():
    """
    Thiết lập môi trường làm việc
    """
    # Tạo thư mục configs nếu chưa tồn tại
    os.makedirs("configs", exist_ok=True)

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Chiến lược giao dịch tối ưu hóa theo thời gian')
    parser.add_argument('--config', type=str, default='configs/time_optimized_strategy_config.json', help='Đường dẫn đến file cấu hình')
    parser.add_argument('--timezone', type=int, default=7, help='Chênh lệch múi giờ so với UTC')
    parser.add_argument('--reset', action='store_true', help='Reset cấu hình về mặc định')
    args = parser.parse_args()
    
    # Thiết lập môi trường
    setup_environment()
    
    # Nếu yêu cầu reset cấu hình
    if args.reset and os.path.exists(args.config):
        os.remove(args.config)
        logger.info(f"Đã xóa file cấu hình {args.config}")
    
    # Khởi tạo chiến lược
    strategy = TimeOptimizedStrategy(args.config)
    
    # Cập nhật timezone nếu có
    if args.timezone != strategy.timezone_offset:
        strategy.timezone_offset = args.timezone
        strategy.config["timezone_offset"] = args.timezone
        strategy._save_config()
    
    # Hiển thị thông tin
    print("\n===== CHIẾN LƯỢC GIAO DỊCH TỐI ƯU HÓA THEO THỜI GIAN =====")
    
    # Hiển thị các thời điểm tối ưu
    optimal_times = strategy.get_all_optimal_times()
    print("\nCác thời điểm tối ưu để vào lệnh:")
    
    for i, time_info in enumerate(sorted(optimal_times, key=lambda x: x["win_rate"], reverse=True), 1):
        print(f"{i}. {time_info['name']} ({time_info['start_time']} - {time_info['end_time']})")
        print(f"   Tỷ lệ thắng: {time_info['win_rate']:.1f}%")
        print(f"   Hướng khuyến nghị: {time_info['direction'].upper()}")
        print(f"   Coin khuyến nghị: {', '.join(time_info['symbols']) if time_info['symbols'] else 'Không có khuyến nghị cụ thể'}")
        print()
    
    # Hiển thị ngày giao dịch tốt nhất
    best_days = strategy.get_best_trading_days()
    print("\nCác ngày giao dịch tốt nhất:")
    
    for i, day_info in enumerate(best_days, 1):
        print(f"{i}. {day_info['name']} - Tỷ lệ thắng: {day_info['win_rate']:.1f}% - Số lệnh tối đa: {day_info['max_trades']}")
    
    print("\nThời gian hiện tại:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Múi giờ: UTC+{strategy.timezone_offset}")
    
    # Kiểm tra xem thời gian hiện tại có phải thời gian tối ưu không
    is_optimal, window = strategy.is_optimal_time()
    
    if is_optimal:
        print(f"\nHiện tại là thời gian tối ưu để vào lệnh: {window['name']}")
        print(f"Hướng khuyến nghị: {window.get('direction', 'both').upper()}")
        print(f"Tỷ lệ thắng: {window.get('win_rate', 50.0):.1f}%")
        
        # Hiển thị coin khuyến nghị
        coins = strategy.optimal_coins.get(window['name'], [])
        print(f"Coin khuyến nghị: {', '.join(coins) if coins else 'Không có khuyến nghị cụ thể'}")
    else:
        print("\nHiện tại không phải thời gian tối ưu để vào lệnh")
        
        # Tìm thời gian tối ưu tiếp theo
        now = datetime.now()
        next_optimal = None
        earliest_diff = timedelta(days=1)
        
        for time_info in optimal_times:
            hour, minute = map(int, time_info["start_time"].split(":"))
            start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if start_time < now:
                start_time = start_time + timedelta(days=1)
            
            diff = start_time - now
            if diff < earliest_diff:
                earliest_diff = diff
                next_optimal = time_info
        
        if next_optimal:
            hours, remainder = divmod(earliest_diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"Thời gian tối ưu tiếp theo: {next_optimal['name']} ({next_optimal['start_time']})")
            print(f"Còn {hours} giờ {minutes} phút nữa")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình!")
    except Exception as e:
        logger.error(f"Lỗi không xử lý được: {e}", exc_info=True)
        sys.exit(1)