#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Risk Level Manager - Quản lý các mức độ rủi ro trong giao dịch
"""

import os
import sys
import json
import time
import logging
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/risk_manager.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('risk_level_manager')

class RiskLevelManager:
    """
    Quản lý các mức độ rủi ro khác nhau trong hệ thống giao dịch.
    Hỗ trợ nhiều cấu hình rủi ro khác nhau dựa trên mức độ chấp nhận rủi ro của người dùng.
    """
    
    RISK_LEVELS = {
        10: "risk_level_10.json",
        15: "risk_level_15.json",
        20: "risk_level_20.json",
        30: "risk_level_30.json",
        "advanced": "advanced_risk_config.json"
    }
    
    def __init__(self, config_dir: str = "risk_configs", default_risk_level: int = 10):
        """
        Khởi tạo quản lý rủi ro
        
        Args:
            config_dir (str): Thư mục chứa các file cấu hình rủi ro
            default_risk_level (int): Mức độ rủi ro mặc định (10, 15, 20, 30)
        """
        self.config_dir = config_dir
        self.current_risk_level = default_risk_level
        self.current_config = None
        self.advanced_config = None
        self.trade_history = []
        self.position_sizing_history = []
        self.win_streak = 0
        self.loss_streak = 0
        self.daily_pl = 0.0
        self.weekly_pl = 0.0
        self.recovery_mode_active = False
        self.last_risk_adjustment = datetime.now()
        
        # Đảm bảo thư mục cấu hình tồn tại
        os.makedirs(config_dir, exist_ok=True)
        
        # Tải cấu hình mặc định
        self.load_risk_config(default_risk_level)
        
        # Tải cấu hình nâng cao
        self.load_advanced_config()
        
        logger.info(f"Khởi tạo Risk Level Manager với mức rủi ro mặc định: {default_risk_level}%")
    
    def load_risk_config(self, risk_level: Union[int, str]) -> bool:
        """
        Tải cấu hình rủi ro từ file
        
        Args:
            risk_level (Union[int, str]): Mức độ rủi ro (10, 15, 20, 30 hoặc "advanced")
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if isinstance(risk_level, int) and risk_level not in self.RISK_LEVELS:
                logger.error(f"Mức độ rủi ro không hợp lệ: {risk_level}. Chỉ hỗ trợ: {list(self.RISK_LEVELS.keys())}")
                return False
            
            if isinstance(risk_level, str) and risk_level != "advanced":
                logger.error(f"Mức độ rủi ro không hợp lệ: {risk_level}. Chuỗi chỉ hỗ trợ giá trị 'advanced'")
                return False
            
            config_file = os.path.join(self.config_dir, self.RISK_LEVELS[risk_level])
            
            if not os.path.exists(config_file):
                logger.error(f"File cấu hình không tồn tại: {config_file}")
                return False
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Cập nhật cấu hình hiện tại và mức rủi ro
            self.current_config = config
            self.current_risk_level = risk_level
            
            logger.info(f"Đã tải cấu hình rủi ro {risk_level} từ {config_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}")
            return False
    
    def load_advanced_config(self) -> bool:
        """
        Tải cấu hình rủi ro nâng cao từ file
        
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            config_file = os.path.join(self.config_dir, self.RISK_LEVELS["advanced"])
            
            if not os.path.exists(config_file):
                logger.warning(f"File cấu hình nâng cao không tồn tại: {config_file}")
                return False
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            self.advanced_config = config
            logger.info(f"Đã tải cấu hình rủi ro nâng cao từ {config_file}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro nâng cao: {str(e)}")
            return False
    
    def get_current_risk_level(self) -> Union[int, str]:
        """
        Lấy mức độ rủi ro hiện tại
        
        Returns:
            Union[int, str]: Mức độ rủi ro hiện tại
        """
        return self.current_risk_level
    
    def get_risk_config(self) -> Dict[str, Any]:
        """
        Lấy cấu hình rủi ro hiện tại
        
        Returns:
            Dict[str, Any]: Cấu hình rủi ro hiện tại
        """
        return self.current_config
    
    def get_advanced_config(self) -> Optional[Dict[str, Any]]:
        """
        Lấy cấu hình rủi ro nâng cao
        
        Returns:
            Optional[Dict[str, Any]]: Cấu hình rủi ro nâng cao
        """
        return self.advanced_config
    
    def switch_to_advanced_mode(self) -> bool:
        """
        Chuyển sang chế độ rủi ro nâng cao
        
        Returns:
            bool: True nếu chuyển thành công, False nếu thất bại
        """
        if self.advanced_config is None:
            self.load_advanced_config()
            
        if self.advanced_config is None:
            logger.error("Không thể chuyển sang chế độ nâng cao, cấu hình không tồn tại")
            return False
        
        self.current_config = self.advanced_config
        self.current_risk_level = "advanced"
        logger.info("Đã chuyển sang chế độ rủi ro nâng cao")
        return True
    
    def switch_to_risk_level(self, risk_level: int) -> bool:
        """
        Chuyển sang mức độ rủi ro khác
        
        Args:
            risk_level (int): Mức độ rủi ro mới (10, 15, 20, 30)
            
        Returns:
            bool: True nếu chuyển thành công, False nếu thất bại
        """
        if risk_level not in [10, 15, 20, 30]:
            logger.error(f"Mức độ rủi ro không hợp lệ: {risk_level}. Chỉ hỗ trợ: 10, 15, 20, 30")
            return False
        
        return self.load_risk_config(risk_level)
    
    def apply_risk_config(self, account_size: float, symbol: str, leverage: Optional[int] = None) -> Dict[str, Any]:
        """
        Áp dụng cấu hình rủi ro cho một giao dịch cụ thể
        
        Args:
            account_size (float): Kích thước tài khoản
            symbol (str): Biểu tượng giao dịch
            leverage (Optional[int]): Đòn bẩy, nếu None thì sử dụng từ cấu hình
            
        Returns:
            Dict[str, Any]: Thông số giao dịch được cấu hình theo mức rủi ro
        """
        if self.current_config is None:
            logger.error("Chưa tải cấu hình rủi ro")
            return {}
        
        # Tham số mặc định từ cấu hình rủi ro
        if self.current_risk_level == "advanced":
            position_size_percent = self.advanced_config["position_sizing"]["base_size_percent"]
            max_position_size_percent = self.advanced_config["position_sizing"]["max_position_size_percent"]
            stop_loss_percent = self.advanced_config["risk_management"]["stop_loss"]["base_percent"]
            take_profit_percent = self.advanced_config["risk_management"]["take_profit"]["base_percent"]
            leverage_val = self.advanced_config["leverage"]["base_level"] if leverage is None else leverage
            trailing_stop_enabled = self.advanced_config["risk_management"]["trailing_stop"]["enable"]
            trailing_stop_callback = self.advanced_config["risk_management"]["trailing_stop"]["callback_percent"]
        else:
            position_size_percent = self.current_config.get("max_position_size_percent", 1.0)
            max_position_size_percent = position_size_percent
            stop_loss_percent = self.current_config.get("stop_loss_percent", 0.5)
            take_profit_percent = self.current_config.get("take_profit_percent", 1.5)
            leverage_val = self.current_config.get("leverage", 3) if leverage is None else leverage
            trailing_stop_enabled = self.current_config.get("enable_trailing_stop", False)
            trailing_stop_callback = self.current_config.get("trailing_stop_callback", 0.15)
        
        # Điều chỉnh kích thước vị thế dựa trên lịch sử
        position_size_percent = self._adjust_position_size(position_size_percent, max_position_size_percent)
        
        # Tính toán kích thước vị thế
        position_size = (account_size * position_size_percent / 100)
        
        # Nếu đang ở chế độ recovery, giảm kích thước vị thế
        if self.recovery_mode_active and self.current_risk_level == "advanced":
            reduction = self.advanced_config["risk_management"]["capital_protection"]["recovery_mode"]["size_reduction"]
            position_size *= (1 - reduction)
            logger.info(f"Chế độ recovery đang kích hoạt, giảm kích thước vị thế xuống {100*(1-reduction):.1f}%")
        
        # Anti-Market Maker: Điều chỉnh ngẫu nhiên các tham số
        if self.current_risk_level == "advanced" and self.advanced_config["anti_mm_tactics"]["enable"]:
            position_size, stop_loss_percent, take_profit_percent = self._apply_anti_mm_tactics(
                position_size, stop_loss_percent, take_profit_percent
            )
        
        # Thiết lập đầu ra
        risk_config = {
            "position_size": position_size,
            "leverage": leverage_val,
            "stop_loss_percent": stop_loss_percent,
            "take_profit_percent": take_profit_percent,
            "trailing_stop_enabled": trailing_stop_enabled,
            "trailing_stop_callback": trailing_stop_callback
        }
        
        # Nếu sử dụng cấu hình nâng cao, thêm các tham số bổ sung
        if self.current_risk_level == "advanced":
            risk_config.update({
                "multi_targets": self.advanced_config["risk_management"]["take_profit"]["multi_targets"],
                "adaptive_sl": self.advanced_config["risk_management"]["stop_loss"]["adaptive_atr_based"]["enable"],
                "atr_multiplier": self.advanced_config["risk_management"]["stop_loss"]["adaptive_atr_based"]["atr_multiplier"],
                "hidden_stop": self.advanced_config["risk_management"]["stop_loss"]["hidden_stop"],
                "dynamic_trailing": self.advanced_config["risk_management"]["trailing_stop"]["dynamic_callback"]["enable"],
                "step_trailing": self.advanced_config["risk_management"]["trailing_stop"]["step_trailing"]["enable"],
                "profit_steps": self.advanced_config["risk_management"]["trailing_stop"]["step_trailing"]["profit_steps"],
                "callback_steps": self.advanced_config["risk_management"]["trailing_stop"]["step_trailing"]["callback_steps"],
                "limit_order_distance_percent": self.advanced_config["entry_optimization"]["smart_entry"]["limit_order_distance_percent"],
                "scale_in_enabled": self.advanced_config["entry_optimization"]["smart_entry"]["scale_in"]["enable"],
                "scale_in_levels": self.advanced_config["entry_optimization"]["smart_entry"]["scale_in"]["levels"],
                "scale_in_price_step": self.advanced_config["entry_optimization"]["smart_entry"]["scale_in"]["price_step_percent"]
            })
        
        # Lưu trữ thông tin kích thước vị thế
        self.position_sizing_history.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "position_size_percent": position_size_percent,
            "position_size": position_size,
            "account_size": account_size
        })
        
        return risk_config
    
    def _adjust_position_size(self, base_size_percent: float, max_size_percent: float) -> float:
        """
        Điều chỉnh kích thước vị thế dựa trên lịch sử giao dịch
        
        Args:
            base_size_percent (float): Phần trăm kích thước cơ bản
            max_size_percent (float): Phần trăm kích thước tối đa
            
        Returns:
            float: Phần trăm kích thước vị thế đã điều chỉnh
        """
        adjusted_size = base_size_percent
        
        if self.current_risk_level == "advanced" and self.advanced_config is not None:
            # Nếu kích hoạt tăng theo chuỗi thắng
            if self.advanced_config["position_sizing"]["win_streak_boost"]["enable"] and self.win_streak >= self.advanced_config["position_sizing"]["win_streak_boost"]["consecutive_wins_required"]:
                max_boost = self.advanced_config["position_sizing"]["win_streak_boost"]["max_boost_percent"]
                boost_factor = min(self.win_streak / 10, 1.0)  # Tăng dần đến 100% của max_boost khi chuỗi thắng dài
                boost_amount = max_boost * boost_factor
                adjusted_size = min(base_size_percent * (1 + boost_amount), max_size_percent)
                logger.info(f"Tăng kích thước vị thế thêm {boost_amount*100:.1f}% do chuỗi thắng {self.win_streak}")
            
            # Nếu kích hoạt giảm theo chuỗi thua
            if self.advanced_config["position_sizing"]["loss_streak_reduction"]["enable"] and self.loss_streak >= self.advanced_config["position_sizing"]["loss_streak_reduction"]["consecutive_losses_trigger"]:
                max_reduction = self.advanced_config["position_sizing"]["loss_streak_reduction"]["max_reduction_percent"]
                reduction_factor = min(self.loss_streak / 5, 1.0)  # Giảm dần đến 100% của max_reduction khi chuỗi thua dài
                reduction_amount = max_reduction * reduction_factor
                adjusted_size = base_size_percent * (1 - reduction_amount)
                logger.info(f"Giảm kích thước vị thế đi {reduction_amount*100:.1f}% do chuỗi thua {self.loss_streak}")
        
        return adjusted_size
    
    def _apply_anti_mm_tactics(self, position_size: float, stop_loss_percent: float, take_profit_percent: float) -> Tuple[float, float, float]:
        """
        Áp dụng các chiến thuật chống Market Makers
        
        Args:
            position_size (float): Kích thước vị thế
            stop_loss_percent (float): Phần trăm stop loss
            take_profit_percent (float): Phần trăm take profit
            
        Returns:
            Tuple[float, float, float]: (position_size, stop_loss_percent, take_profit_percent) đã điều chỉnh
        """
        try:
            # Tạo kích thước vị thế không đều đặn
            if self.advanced_config["anti_mm_tactics"]["irregular_position_sizing"]:
                variance_percent = self.advanced_config["anti_mm_tactics"]["random_entry_variance_percent"]
                random_factor = 1.0 + random.uniform(-variance_percent, variance_percent)
                position_size = position_size * random_factor
            
            # Điều chỉnh ngẫu nhiên stop loss
            variance_percent = self.advanced_config["anti_mm_tactics"]["stop_placement_variance_percent"]
            sl_random_factor = 1.0 + random.uniform(-variance_percent / 2, variance_percent)
            stop_loss_percent = stop_loss_percent * sl_random_factor
            
            # Tránh các số tròn trong stop loss
            if self.advanced_config["anti_mm_tactics"]["avoid_round_numbers"]:
                stop_loss_percent = self._avoid_round_number(stop_loss_percent)
                take_profit_percent = self._avoid_round_number(take_profit_percent)
            
            return position_size, stop_loss_percent, take_profit_percent
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng chiến thuật chống MM: {str(e)}")
            return position_size, stop_loss_percent, take_profit_percent
    
    def _avoid_round_number(self, value: float) -> float:
        """
        Tránh số tròn bằng cách thêm một lượng nhỏ ngẫu nhiên
        
        Args:
            value (float): Giá trị cần điều chỉnh
            
        Returns:
            float: Giá trị đã điều chỉnh
        """
        # Kiểm tra xem có phải số tròn không
        is_round = (abs(value * 100 - round(value * 100)) < 0.01)
        
        if is_round:
            # Thêm một lượng nhỏ ngẫu nhiên
            adjustment = random.uniform(0.01, 0.07)
            # 50% khả năng tăng, 50% khả năng giảm
            if random.random() > 0.5:
                return value + adjustment
            else:
                return value - adjustment
        
        return value
    
    def update_trade_result(self, trade_result: Dict[str, Any]) -> None:
        """
        Cập nhật kết quả giao dịch
        
        Args:
            trade_result (Dict[str, Any]): Kết quả giao dịch
        """
        try:
            # Thêm vào lịch sử giao dịch
            self.trade_history.append(trade_result)
            
            # Cập nhật chu kỳ thắng/thua
            if trade_result.get("profit", 0) > 0:
                self.win_streak += 1
                self.loss_streak = 0
            else:
                self.loss_streak += 1
                self.win_streak = 0
            
            # Cập nhật P&L hàng ngày và hàng tuần
            self.daily_pl += trade_result.get("profit", 0)
            self.weekly_pl += trade_result.get("profit", 0)
            
            # Kiểm tra chế độ recovery
            self._check_capital_protection()
            
            logger.info(f"Đã cập nhật kết quả giao dịch: {trade_result}")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật kết quả giao dịch: {str(e)}")
    
    def _check_capital_protection(self) -> None:
        """
        Kiểm tra và kích hoạt chế độ bảo vệ vốn nếu cần thiết
        """
        if self.current_risk_level != "advanced" or self.advanced_config is None:
            return
        
        capital_protection = self.advanced_config["risk_management"]["capital_protection"]
        
        # Kiểm tra giới hạn lỗ hàng ngày
        if abs(self.daily_pl) > capital_protection["max_daily_loss_percent"]:
            logger.warning(f"Đã đạt giới hạn lỗ hàng ngày: {self.daily_pl}%. Kích hoạt chế độ recovery.")
            self.recovery_mode_active = True
            self.last_risk_adjustment = datetime.now()
        
        # Kiểm tra giới hạn lỗ hàng tuần
        if abs(self.weekly_pl) > capital_protection["max_weekly_loss_percent"]:
            logger.warning(f"Đã đạt giới hạn lỗ hàng tuần: {self.weekly_pl}%. Kích hoạt chế độ recovery.")
            self.recovery_mode_active = True
            self.last_risk_adjustment = datetime.now()
        
        # Kiểm tra điều kiện để thoát chế độ recovery
        if self.recovery_mode_active:
            days_in_recovery = (datetime.now() - self.last_risk_adjustment).days
            if days_in_recovery >= capital_protection["recovery_mode"]["reset_after_profit_days"] and self.daily_pl > 0:
                logger.info(f"Đã đủ điều kiện thoát chế độ recovery sau {days_in_recovery} ngày có lợi nhuận.")
                self.recovery_mode_active = False
    
    def reset_daily_stats(self) -> None:
        """
        Đặt lại thống kê hàng ngày
        """
        self.daily_pl = 0.0
        logger.info("Đã đặt lại thống kê hàng ngày")
    
    def reset_weekly_stats(self) -> None:
        """
        Đặt lại thống kê hàng tuần
        """
        self.weekly_pl = 0.0
        logger.info("Đã đặt lại thống kê hàng tuần")
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử giao dịch
        
        Returns:
            List[Dict[str, Any]]: Lịch sử giao dịch
        """
        return self.trade_history
    
    def get_position_sizing_history(self) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử kích thước vị thế
        
        Returns:
            List[Dict[str, Any]]: Lịch sử kích thước vị thế
        """
        return self.position_sizing_history
    
    def get_strategy_parameters_for_regime(self, market_regime: str) -> Dict[str, Any]:
        """
        Lấy tham số chiến lược cho chế độ thị trường cụ thể
        
        Args:
            market_regime (str): Chế độ thị trường (trending, ranging, volatile, extremely_volatile)
            
        Returns:
            Dict[str, Any]: Tham số chiến lược được điều chỉnh
        """
        if self.current_risk_level != "advanced" or self.advanced_config is None:
            return {}
        
        # Kiểm tra xem chế độ thị trường có được phép không
        if market_regime in self.advanced_config["market_filters"]["regime_filter"]["forbidden_regimes"]:
            logger.warning(f"Chế độ thị trường {market_regime} bị cấm theo cấu hình")
            return {"allow_trading": False}
        
        # Điều chỉnh tham số dựa trên chế độ thị trường
        params = {"allow_trading": True}
        
        if market_regime == "trending":
            # Tối ưu hóa cho thị trường xu hướng
            params.update({
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.2,
                "trailing_stop_callback": self.advanced_config["risk_management"]["trailing_stop"]["callback_percent"] * 0.8,
                "position_size_multiplier": 1.1
            })
        elif market_regime == "ranging":
            # Tối ưu hóa cho thị trường sideway
            params.update({
                "stop_loss_multiplier": 0.8,
                "take_profit_multiplier": 0.9,
                "trailing_stop_callback": self.advanced_config["risk_management"]["trailing_stop"]["callback_percent"] * 1.2,
                "position_size_multiplier": 0.9
            })
        elif market_regime == "volatile":
            # Thận trọng trong thị trường biến động
            params.update({
                "stop_loss_multiplier": 1.2,
                "take_profit_multiplier": 1.1,
                "trailing_stop_callback": self.advanced_config["risk_management"]["trailing_stop"]["callback_percent"] * 1.5,
                "position_size_multiplier": 0.8
            })
        elif market_regime == "extremely_volatile":
            # Chỉ giao dịch nếu chế độ cực kỳ biến động không bị cấm
            params.update({
                "stop_loss_multiplier": 1.5,
                "take_profit_multiplier": 1.3,
                "trailing_stop_callback": self.advanced_config["risk_management"]["trailing_stop"]["callback_percent"] * 2.0,
                "position_size_multiplier": 0.5
            })
        
        return params
    
    def get_entry_parameters(self, signal_strength: str) -> Dict[str, Any]:
        """
        Lấy tham số vào lệnh dựa trên độ mạnh của tín hiệu
        
        Args:
            signal_strength (str): Độ mạnh của tín hiệu (strong, moderate, weak)
            
        Returns:
            Dict[str, Any]: Tham số vào lệnh
        """
        if self.current_risk_level != "advanced" or self.advanced_config is None:
            return {}
        
        # Khởi tạo tham số mặc định
        entry_params = {
            "entry_type": "market",
            "position_size_multiplier": 1.0,
            "use_scale_in": False
        }
        
        # Lấy bội số kích thước dựa trên độ mạnh tín hiệu
        if signal_strength in self.advanced_config["position_sizing"]["signal_strength_multipliers"]:
            entry_params["position_size_multiplier"] = self.advanced_config["position_sizing"]["signal_strength_multipliers"][signal_strength]
        
        # Quyết định loại lệnh dựa trên độ mạnh tín hiệu
        if signal_strength == "strong":
            entry_params["entry_type"] = "market"
            entry_params["use_scale_in"] = self.advanced_config["entry_optimization"]["smart_entry"]["scale_in"]["enable"] if signal_strength == "strong" else False
        elif signal_strength == "moderate":
            # 50/50 giữa market và limit
            entry_params["entry_type"] = "market" if random.random() > 0.5 else "limit"
        else:  # weak
            entry_params["entry_type"] = "limit"
            entry_params["position_size_multiplier"] *= 0.8  # Giảm thêm cho tín hiệu yếu
        
        return entry_params
    
    def save_trade_history(self, filename: str = "trade_history.json") -> bool:
        """
        Lưu lịch sử giao dịch vào file
        
        Args:
            filename (str): Tên file để lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.trade_history, f, indent=4)
            logger.info(f"Đã lưu lịch sử giao dịch vào {filename}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử giao dịch: {str(e)}")
            return False
    
    def load_trade_history(self, filename: str = "trade_history.json") -> bool:
        """
        Tải lịch sử giao dịch từ file
        
        Args:
            filename (str): Tên file để tải
            
        Returns:
            bool: True nếu tải thành công, False nếu thất bại
        """
        try:
            if not os.path.exists(filename):
                logger.warning(f"File lịch sử giao dịch không tồn tại: {filename}")
                return False
            
            with open(filename, 'r') as f:
                self.trade_history = json.load(f)
            
            logger.info(f"Đã tải lịch sử giao dịch từ {filename}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi tải lịch sử giao dịch: {str(e)}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Lấy thống kê hiệu suất giao dịch
        
        Returns:
            Dict[str, Any]: Thống kê hiệu suất
        """
        if not self.trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "average_win": 0,
                "average_loss": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "max_win_streak": 0,
                "max_loss_streak": 0,
                "daily_pl": self.daily_pl,
                "weekly_pl": self.weekly_pl
            }
        
        # Tính tổng số giao dịch
        total_trades = len(self.trade_history)
        
        # Tính số giao dịch thắng và thua
        winning_trades = [trade for trade in self.trade_history if trade.get("profit", 0) > 0]
        losing_trades = [trade for trade in self.trade_history if trade.get("profit", 0) <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        
        # Tính tỷ lệ thắng
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Tính tổng lợi nhuận và tổng lỗ
        total_profit = sum(trade.get("profit", 0) for trade in winning_trades)
        total_loss = abs(sum(trade.get("profit", 0) for trade in losing_trades))
        
        # Tính hệ số lợi nhuận
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Tính trung bình thắng và thua
        average_win = total_profit / win_count if win_count > 0 else 0
        average_loss = total_loss / loss_count if loss_count > 0 else 0
        
        # Tìm giao dịch thắng và thua lớn nhất
        largest_win = max([trade.get("profit", 0) for trade in winning_trades]) if winning_trades else 0
        largest_loss = abs(min([trade.get("profit", 0) for trade in losing_trades])) if losing_trades else 0
        
        # Tính chuỗi thắng và thua dài nhất
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for trade in self.trade_history:
            if trade.get("profit", 0) > 0:
                current_win_streak += 1
                current_loss_streak = 0
            else:
                current_loss_streak += 1
                current_win_streak = 0
            
            max_win_streak = max(max_win_streak, current_win_streak)
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "average_win": average_win,
            "average_loss": average_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "daily_pl": self.daily_pl,
            "weekly_pl": self.weekly_pl,
            "current_win_streak": self.win_streak,
            "current_loss_streak": self.loss_streak,
            "recovery_mode_active": self.recovery_mode_active
        }
    
    def save_config(self, config: Dict[str, Any], risk_level: Union[int, str]) -> bool:
        """
        Lưu cấu hình rủi ro vào file
        
        Args:
            config (Dict[str, Any]): Cấu hình cần lưu
            risk_level (Union[int, str]): Mức độ rủi ro (10, 15, 20, 30 hoặc "advanced")
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            if isinstance(risk_level, int) and risk_level not in self.RISK_LEVELS:
                logger.error(f"Mức độ rủi ro không hợp lệ: {risk_level}. Chỉ hỗ trợ: {list(self.RISK_LEVELS.keys())}")
                return False
            
            if isinstance(risk_level, str) and risk_level != "advanced":
                logger.error(f"Mức độ rủi ro không hợp lệ: {risk_level}. Chuỗi chỉ hỗ trợ giá trị 'advanced'")
                return False
            
            config_file = os.path.join(self.config_dir, self.RISK_LEVELS[risk_level])
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình rủi ro {risk_level} vào {config_file}")
            
            # Tải lại cấu hình nếu đang sử dụng mức rủi ro này
            if self.current_risk_level == risk_level:
                self.load_risk_config(risk_level)
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}")
            return False
    
    def is_trading_allowed(self, market_conditions: Dict[str, Any]) -> bool:
        """
        Kiểm tra xem có cho phép giao dịch với điều kiện thị trường hiện tại không
        
        Args:
            market_conditions (Dict[str, Any]): Điều kiện thị trường
            
        Returns:
            bool: True nếu cho phép giao dịch, False nếu không
        """
        if self.current_config is None:
            logger.error("Chưa tải cấu hình rủi ro")
            return False
        
        # Kiểm tra giới hạn lỗ hàng ngày
        if self.current_risk_level == "advanced":
            capital_protection = self.advanced_config["risk_management"]["capital_protection"]
            if abs(self.daily_pl) >= capital_protection["max_daily_loss_percent"]:
                logger.warning(f"Đã đạt giới hạn lỗ hàng ngày ({self.daily_pl}%), giao dịch không được phép")
                return False
            
            if abs(self.weekly_pl) >= capital_protection["max_weekly_loss_percent"]:
                logger.warning(f"Đã đạt giới hạn lỗ hàng tuần ({self.weekly_pl}%), giao dịch không được phép")
                return False
        else:
            if abs(self.daily_pl) >= self.current_config.get("max_daily_loss_percent", 100.0):
                logger.warning(f"Đã đạt giới hạn lỗ hàng ngày ({self.daily_pl}%), giao dịch không được phép")
                return False
        
        # Kiểm tra chế độ thị trường
        if self.current_risk_level == "advanced" and self.advanced_config["market_filters"]["regime_filter"]["enable"]:
            market_regime = market_conditions.get("market_regime", "unknown")
            if market_regime in self.advanced_config["market_filters"]["regime_filter"]["forbidden_regimes"]:
                logger.warning(f"Chế độ thị trường {market_regime} bị cấm, giao dịch không được phép")
                return False
        elif self.current_config.get("use_market_regime_filter", False):
            market_regime = market_conditions.get("market_regime", "unknown")
            if market_regime in ["extremely_volatile"]:
                logger.warning(f"Chế độ thị trường {market_regime} bị cấm, giao dịch không được phép")
                return False
        
        # Kiểm tra bộ lọc biến động
        if self.current_risk_level == "advanced" and self.advanced_config["market_filters"]["volatility_filter"]["enable"]:
            volatility = market_conditions.get("volatility", 0)
            max_volatility = self.advanced_config["market_filters"]["volatility_filter"]["max_atr_percent"]
            min_volatility = self.advanced_config["market_filters"]["volatility_filter"]["min_atr_percent"]
            
            if volatility > max_volatility:
                logger.warning(f"Biến động thị trường ({volatility}%) vượt quá ngưỡng tối đa ({max_volatility}%), giao dịch không được phép")
                return False
            
            if volatility < min_volatility:
                logger.warning(f"Biến động thị trường ({volatility}%) dưới ngưỡng tối thiểu ({min_volatility}%), giao dịch không được phép")
                return False
        elif self.current_config.get("use_volatility_filter", False):
            volatility = market_conditions.get("volatility", 0)
            if volatility > 3.0:
                logger.warning(f"Biến động thị trường ({volatility}%) quá cao, giao dịch không được phép")
                return False
        
        # Kiểm tra bộ lọc thanh khoản
        if self.current_risk_level == "advanced" and self.advanced_config["market_filters"]["liquidity_filter"]["enable"]:
            volume = market_conditions.get("volume", 0)
            min_volume = self.advanced_config["market_filters"]["liquidity_filter"]["min_volume_threshold"]
            
            if volume < min_volume:
                logger.warning(f"Thanh khoản thị trường ({volume}) dưới ngưỡng tối thiểu ({min_volume}), giao dịch không được phép")
                return False
        
        # Kiểm tra phiên giao dịch
        current_hour = datetime.now().hour
        
        if self.current_risk_level == "advanced":
            # Kiểm tra các phiên giao dịch được cấu hình
            allowed_in_any_session = False
            
            for session in self.advanced_config["session_management"]["trading_sessions"]:
                if not session["enabled"]:
                    continue
                
                start_hour = session["start_hour"]
                end_hour = session["end_hour"]
                
                if start_hour <= current_hour < end_hour:
                    allowed_in_any_session = True
                    break
            
            if not allowed_in_any_session:
                logger.warning(f"Ngoài phiên giao dịch được phép (giờ hiện tại: {current_hour}), giao dịch không được phép")
                return False
        else:
            # Kiểm tra phiên giao dịch đơn giản
            start_hour = self.current_config.get("session_start_hour", 0)
            end_hour = self.current_config.get("session_end_hour", 24)
            
            if not (start_hour <= current_hour < end_hour):
                logger.warning(f"Ngoài phiên giao dịch ({start_hour}-{end_hour}, giờ hiện tại: {current_hour}), giao dịch không được phép")
                return False
        
        # Kiểm tra tin tức
        if self.current_risk_level == "advanced" and self.advanced_config["session_management"]["high_impact_news_avoidance"]["enable"]:
            has_high_impact_news = market_conditions.get("has_high_impact_news", False)
            
            if has_high_impact_news:
                logger.warning(f"Có tin tức quan trọng, giao dịch không được phép")
                return False
        
        return True

# Hàm main để chạy trực tiếp module
def main():
    """Hàm main"""
    # Khởi tạo quản lý rủi ro
    risk_manager = RiskLevelManager()
    
    # Thử tải các cấu hình rủi ro
    for risk_level in [10, 15, 20, 30, "advanced"]:
        if risk_manager.load_risk_config(risk_level):
            print(f"Đã tải cấu hình rủi ro {risk_level}")
            print(f"Thông số: {json.dumps(risk_manager.get_risk_config(), indent=2)}")
            print()
    
    # Lấy thông số giao dịch cho một ví dụ
    account_size = 1000.0
    symbol = "BTCUSDT"
    
    basic_config = risk_manager.apply_risk_config(account_size, symbol)
    print(f"Thông số giao dịch cơ bản: {json.dumps(basic_config, indent=2)}")
    
    # Chuyển sang chế độ nâng cao
    if risk_manager.switch_to_advanced_mode():
        advanced_config = risk_manager.apply_risk_config(account_size, symbol)
        print(f"Thông số giao dịch nâng cao: {json.dumps(advanced_config, indent=2)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())