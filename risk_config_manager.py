#!/usr/bin/env python3
"""
Quản lý cấu hình rủi ro cho bot giao dịch

Module này cho phép cấu hình các thông số rủi ro và vốn ban đầu cho bot giao dịch.
Người dùng có thể chọn từ các hồ sơ rủi ro được cài đặt sẵn hoặc tạo cấu hình tùy chỉnh.
Module cũng cung cấp các tính năng tối ưu hóa tỷ lệ thắng và ROI dựa trên phân tích thống kê.
"""

import os
import json
import logging
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_config")

# Đường dẫn lưu cấu hình
CONFIG_DIR = "configs"
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "risk_config.json")
PERFORMANCE_DATA_PATH = os.path.join(CONFIG_DIR, "performance_data.json")

# Tạo thư mục configs nếu chưa tồn tại
os.makedirs(CONFIG_DIR, exist_ok=True)

# Các hồ sơ rủi ro có sẵn
RISK_PROFILES = {
    "very_low": {
        "name": "Rủi ro rất thấp (5-10%)",
        "description": "Ưu tiên bảo toàn vốn tối đa, tỷ lệ thắng cao nhưng lợi nhuận thấp.",
        "max_account_risk": 10.0,      # Rủi ro tối đa: 10% vốn
        "risk_per_trade": 1.0,         # Rủi ro mỗi giao dịch: 1%
        "max_leverage": 5,             # Đòn bẩy tối đa: x5
        "optimal_leverage": 3,         # Đòn bẩy khuyến nghị: x3
        "min_distance_to_liquidation": 40.0,  # Khoảng cách an toàn đến thanh lý: 40%
        "max_positions": 1,            # Số vị thế đồng thời: 1
        "max_margin_usage": 30.0,      # Sử dụng margin tối đa: 30%
        "use_trailing_stop": True,     # Sử dụng trailing stop
        "min_risk_reward": 2.0,        # Tỷ lệ R:R tối thiểu: 1:2
        "stop_loss_percent": {
            "scalping": 0.5,           # Stop loss scalping: 0.5%
            "trend": 0.8               # Stop loss trend: 0.8%
        },
        "take_profit_percent": {
            "scalping": 1.0,           # Take profit scalping: 1.0%
            "trend": 1.6               # Take profit trend: 1.6%
        }
    },
    "low": {
        "name": "Rủi ro thấp (10-15%)",
        "description": "Chiến lược an toàn, phù hợp với người mới bắt đầu.",
        "max_account_risk": 15.0,      # Rủi ro tối đa: 15% vốn
        "risk_per_trade": 1.5,         # Rủi ro mỗi giao dịch: 1.5%
        "max_leverage": 10,            # Đòn bẩy tối đa: x10
        "optimal_leverage": 7,         # Đòn bẩy khuyến nghị: x7
        "min_distance_to_liquidation": 35.0,  # Khoảng cách an toàn đến thanh lý: 35%
        "max_positions": 2,            # Số vị thế đồng thời: 2
        "max_margin_usage": 40.0,      # Sử dụng margin tối đa: 40%
        "use_trailing_stop": True,     # Sử dụng trailing stop
        "min_risk_reward": 1.8,        # Tỷ lệ R:R tối thiểu: 1:1.8
        "stop_loss_percent": {
            "scalping": 0.7,           # Stop loss scalping: 0.7%
            "trend": 1.0               # Stop loss trend: 1.0%
        },
        "take_profit_percent": {
            "scalping": 1.3,           # Take profit scalping: 1.3%
            "trend": 2.0               # Take profit trend: 2.0%
        }
    },
    "medium": {
        "name": "Rủi ro vừa phải (20-30%)",
        "description": "Cân bằng giữa rủi ro và lợi nhuận, phù hợp với người đã có kinh nghiệm.",
        "max_account_risk": 25.0,      # Rủi ro tối đa: 25% vốn
        "risk_per_trade": 2.5,         # Rủi ro mỗi giao dịch: 2.5%
        "max_leverage": 15,            # Đòn bẩy tối đa: x15
        "optimal_leverage": 12,        # Đòn bẩy khuyến nghị: x12
        "min_distance_to_liquidation": 30.0,  # Khoảng cách an toàn đến thanh lý: 30%
        "max_positions": 2,            # Số vị thế đồng thời: 2
        "max_margin_usage": 60.0,      # Sử dụng margin tối đa: 60%
        "use_trailing_stop": True,     # Sử dụng trailing stop
        "min_risk_reward": 1.5,        # Tỷ lệ R:R tối thiểu: 1:1.5
        "stop_loss_percent": {
            "scalping": 1.0,           # Stop loss scalping: 1.0%
            "trend": 1.5               # Stop loss trend: 1.5%
        },
        "take_profit_percent": {
            "scalping": 1.8,           # Take profit scalping: 1.8%
            "trend": 2.5               # Take profit trend: 2.5%
        }
    },
    "high": {
        "name": "Rủi ro cao (30-50%)",
        "description": "Đặt mục tiêu lợi nhuận cao, chấp nhận rủi ro lớn. Chỉ phù hợp với người có nhiều kinh nghiệm.",
        "max_account_risk": 50.0,      # Rủi ro tối đa: 50% vốn
        "risk_per_trade": 5.0,         # Rủi ro mỗi giao dịch: 5%
        "max_leverage": 20,            # Đòn bẩy tối đa: x20
        "optimal_leverage": 16,        # Đòn bẩy khuyến nghị: x16
        "min_distance_to_liquidation": 20.0,  # Khoảng cách an toàn đến thanh lý: 20%
        "max_positions": 3,            # Số vị thế đồng thời: 3
        "max_margin_usage": 80.0,      # Sử dụng margin tối đa: 80%
        "use_trailing_stop": True,     # Sử dụng trailing stop
        "min_risk_reward": 1.2,        # Tỷ lệ R:R tối thiểu: 1:1.2
        "stop_loss_percent": {
            "scalping": 1.2,           # Stop loss scalping: 1.2%
            "trend": 2.0               # Stop loss trend: 2.0%
        },
        "take_profit_percent": {
            "scalping": 2.0,           # Take profit scalping: 2.0%
            "trend": 3.0               # Take profit trend: 3.0%
        }
    },
    "very_high": {
        "name": "Rủi ro rất cao (50-70%)",
        "description": "Mục tiêu lợi nhuận cực cao, rủi ro mất vốn lớn. Chỉ dành cho trader chuyên nghiệp.",
        "max_account_risk": 70.0,      # Rủi ro tối đa: 70% vốn
        "risk_per_trade": 7.0,         # Rủi ro mỗi giao dịch: 7%
        "max_leverage": 20,            # Đòn bẩy tối đa: x20
        "optimal_leverage": 18,        # Đòn bẩy khuyến nghị: x18
        "min_distance_to_liquidation": 15.0,  # Khoảng cách an toàn đến thanh lý: 15%
        "max_positions": 4,            # Số vị thế đồng thời: 4
        "max_margin_usage": 90.0,      # Sử dụng margin tối đa: 90%
        "use_trailing_stop": True,     # Sử dụng trailing stop
        "min_risk_reward": 1.0,        # Tỷ lệ R:R tối thiểu: 1:1
        "stop_loss_percent": {
            "scalping": 1.5,           # Stop loss scalping: 1.5%
            "trend": 2.5               # Stop loss trend: 2.5%
        },
        "take_profit_percent": {
            "scalping": 2.5,           # Take profit scalping: 2.5%
            "trend": 3.5               # Take profit trend: 3.5%
        }
    }
}

class RiskConfigManager:
    """Quản lý cấu hình rủi ro cho bot giao dịch"""
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH, 
                performance_path: str = PERFORMANCE_DATA_PATH):
        """
        Khởi tạo trình quản lý cấu hình rủi ro
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            performance_path (str): Đường dẫn đến file dữ liệu hiệu suất
        """
        self.config_path = config_path
        self.performance_path = performance_path
        self.current_config = self._load_or_create_default()
        self.performance_data = self._load_performance_data()
        
        logger.info(f"Đã khởi tạo RiskConfigManager, sử dụng file cấu hình: {config_path}")
        
    def _load_performance_data(self) -> Dict:
        """
        Tải dữ liệu hiệu suất từ file hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Dữ liệu hiệu suất giao dịch
        """
        if os.path.exists(self.performance_path):
            try:
                with open(self.performance_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Đã tải dữ liệu hiệu suất từ {self.performance_path}")
                return data
            except Exception as e:
                logger.error(f"Lỗi khi tải dữ liệu hiệu suất: {e}")
                
        # Tạo dữ liệu mặc định
        default_data = {
            "trades": [],               # Lịch sử giao dịch
            "win_rate": 0.0,            # Tỷ lệ thắng
            "avg_win": 0.0,             # Lợi nhuận trung bình của các giao dịch thắng
            "avg_loss": 0.0,            # Thua lỗ trung bình của các giao dịch thua
            "profit_factor": 0.0,       # Hệ số lợi nhuận (tổng lợi nhuận / tổng thua lỗ)
            "max_drawdown": 0.0,        # Rút vốn tối đa
            "expectancy": 0.0,          # Kỳ vọng toán học
            "sharpe_ratio": 0.0,        # Tỷ số Sharpe
            "daily_stats": {},          # Thống kê theo ngày
            "monthly_stats": {},        # Thống kê theo tháng
            "by_symbol": {},            # Thống kê theo cặp giao dịch
            "by_strategy": {},          # Thống kê theo chiến lược
            "optimal_parameters": {},   # Các tham số tối ưu
            "last_updated": None,       # Thời gian cập nhật cuối
            "metadata": {               # Metadata
                "version": "1.0",
                "created_at": get_current_timestamp()
            }
        }
        
        # Lưu dữ liệu mặc định
        self._save_performance_data(default_data)
        logger.info(f"Đã tạo dữ liệu hiệu suất mặc định và lưu vào {self.performance_path}")
        
        return default_data
    
    def _save_performance_data(self, data: Dict) -> bool:
        """
        Lưu dữ liệu hiệu suất vào file
        
        Args:
            data (Dict): Dữ liệu hiệu suất cần lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            data["last_updated"] = get_current_timestamp()
            
            with open(self.performance_path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Đã lưu dữ liệu hiệu suất vào {self.performance_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu dữ liệu hiệu suất: {e}")
            return False
    
    def _load_or_create_default(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Cấu hình rủi ro
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
                return config
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {e}")
                
        # Tạo cấu hình mặc định
        default_config = {
            "initial_balance": 100.0,            # Số dư ban đầu: $100
            "risk_profile": "medium",            # Hồ sơ rủi ro mặc định: vừa phải
            "custom_settings": None,             # Cài đặt tùy chỉnh: None
            "strategy": "trend",                 # Chiến lược mặc định: trend
            "last_updated": None,                # Thời gian cập nhật cuối
            "creator": "system"                  # Người tạo: system
        }
        
        # Lưu cấu hình mặc định
        self._save_config(default_config)
        logger.info(f"Đã tạo cấu hình mặc định và lưu vào {self.config_path}")
        
        return default_config
    
    def _save_config(self, config: Dict) -> bool:
        """
        Lưu cấu hình vào file
        
        Args:
            config (Dict): Cấu hình cần lưu
            
        Returns:
            bool: True nếu lưu thành công, False nếu thất bại
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")
            return False
    
    def get_current_config(self) -> Dict:
        """
        Lấy cấu hình hiện tại
        
        Returns:
            Dict: Cấu hình hiện tại
        """
        return self.current_config
    
    def get_effective_risk_settings(self) -> Dict:
        """
        Lấy cài đặt rủi ro hiệu lực (từ hồ sơ hoặc tùy chỉnh)
        
        Returns:
            Dict: Cài đặt rủi ro hiệu lực
        """
        if self.current_config.get("custom_settings"):
            # Sử dụng cài đặt tùy chỉnh
            risk_settings = self.current_config["custom_settings"]
        else:
            # Sử dụng hồ sơ rủi ro
            profile_name = self.current_config.get("risk_profile", "medium")
            risk_settings = RISK_PROFILES.get(profile_name, RISK_PROFILES["medium"])
        
        # Thêm thông tin về vốn ban đầu
        risk_settings["initial_balance"] = self.current_config.get("initial_balance", 100.0)
        
        return risk_settings
    
    def set_initial_balance(self, balance: float, auto_detected: bool = False) -> bool:
        """
        Đặt vốn ban đầu
        
        Args:
            balance (float): Vốn ban đầu
            auto_detected (bool): Vốn được phát hiện tự động từ Binance
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if balance <= 0:
            logger.error(f"Vốn ban đầu không hợp lệ: ${balance}")
            return False
            
        self.current_config["initial_balance"] = balance
        self.current_config["last_updated"] = get_current_timestamp()
        
        if auto_detected:
            self.current_config["balance_auto_detected"] = True
            logger.info(f"Đã cập nhật vốn ban đầu từ tài khoản Binance: ${balance:.2f}")
        else:
            self.current_config["balance_auto_detected"] = False
        
        return self._save_config(self.current_config)
        
    def auto_update_balance_from_binance(self, account_type: str = 'futures') -> bool:
        """
        Tự động cập nhật số dư từ tài khoản Binance
        
        Args:
            account_type (str): Loại tài khoản ('spot' hoặc 'futures')
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        try:
            # Import ở đây để tránh import cycle
            from binance_balance_checker import BinanceBalanceChecker
            
            # Khởi tạo trình kiểm tra số dư
            checker = BinanceBalanceChecker()
            
            # Lấy số dư
            if account_type.lower() == 'spot':
                balance, success = checker.get_spot_balance()
            else:  # futures
                balance, success = checker.get_futures_balance()
                
            if not success:
                logger.warning("Không thể lấy số dư thực tế từ Binance.")
                return False
                
            # Cập nhật số dư
            return self.set_initial_balance(balance, auto_detected=True)
                
        except Exception as e:
            logger.error(f"Lỗi khi tự động cập nhật số dư: {e}")
            return False
    
    def set_risk_profile(self, profile_name: str) -> bool:
        """
        Đặt hồ sơ rủi ro
        
        Args:
            profile_name (str): Tên hồ sơ rủi ro
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if profile_name not in RISK_PROFILES:
            logger.error(f"Hồ sơ rủi ro không hợp lệ: {profile_name}")
            return False
            
        self.current_config["risk_profile"] = profile_name
        self.current_config["custom_settings"] = None  # Xóa cài đặt tùy chỉnh khi chọn hồ sơ
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def set_custom_settings(self, settings: Dict) -> bool:
        """
        Đặt cài đặt rủi ro tùy chỉnh
        
        Args:
            settings (Dict): Cài đặt rủi ro tùy chỉnh
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        # Xác thực cài đặt
        required_fields = [
            "max_account_risk", "risk_per_trade", "max_leverage", 
            "optimal_leverage", "min_distance_to_liquidation"
        ]
        
        for field in required_fields:
            if field not in settings:
                logger.error(f"Thiếu trường bắt buộc: {field}")
                return False
        
        self.current_config["custom_settings"] = settings
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def set_strategy(self, strategy: str) -> bool:
        """
        Đặt chiến lược giao dịch
        
        Args:
            strategy (str): Chiến lược giao dịch ('scalping', 'trend', 'combined')
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        valid_strategies = ["scalping", "trend", "combined"]
        if strategy not in valid_strategies:
            logger.error(f"Chiến lược không hợp lệ: {strategy}")
            return False
            
        self.current_config["strategy"] = strategy
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def reset_to_default(self) -> bool:
        """
        Đặt lại cấu hình về mặc định
        
        Returns:
            bool: True nếu đặt lại thành công
        """
        default_config = {
            "initial_balance": 100.0,
            "risk_profile": "medium",
            "custom_settings": None,
            "strategy": "trend",
            "last_updated": get_current_timestamp(),
            "creator": "system"
        }
        
        self.current_config = default_config
        return self._save_config(self.current_config)
    
    def get_risk_profiles(self) -> Dict:
        """
        Lấy danh sách các hồ sơ rủi ro có sẵn
        
        Returns:
            Dict: Danh sách các hồ sơ rủi ro
        """
        return RISK_PROFILES
    
    def get_profile_summary(self, profile_name: str) -> str:
        """
        Lấy tóm tắt hồ sơ rủi ro
        
        Args:
            profile_name (str): Tên hồ sơ rủi ro
            
        Returns:
            str: Tóm tắt hồ sơ rủi ro
        """
        if profile_name not in RISK_PROFILES:
            return f"Hồ sơ rủi ro không tồn tại: {profile_name}"
            
        profile = RISK_PROFILES[profile_name]
        initial_balance = self.current_config.get("initial_balance", 100.0)
        
        # Tính toán một số giá trị phụ thuộc
        max_risk_amount = initial_balance * (profile["max_account_risk"] / 100)
        risk_per_trade_amount = initial_balance * (profile["risk_per_trade"] / 100)
        max_position_size = initial_balance * (profile["max_margin_usage"] / 100) * profile["optimal_leverage"]
        
        summary = f"""
        === THÔNG TIN HỒ SƠ RỦI RO: {profile['name']} ===
        
        {profile['description']}
        
        Số dư ban đầu: ${initial_balance:.2f}
        Rủi ro tối đa: {profile['max_account_risk']:.1f}% (${max_risk_amount:.2f})
        Rủi ro mỗi giao dịch: {profile['risk_per_trade']:.1f}% (${risk_per_trade_amount:.2f})
        
        Đòn bẩy tối đa: x{profile['max_leverage']}
        Đòn bẩy khuyến nghị: x{profile['optimal_leverage']}
        
        Kích thước vị thế tối đa: ${max_position_size:.2f}
        Số vị thế đồng thời: {profile['max_positions']}
        
        Khoảng cách an toàn đến thanh lý: {profile['min_distance_to_liquidation']:.1f}%
        Sử dụng margin tối đa: {profile['max_margin_usage']:.1f}%
        
        Stop Loss Scalping: {profile['stop_loss_percent']['scalping']:.1f}%
        Take Profit Scalping: {profile['take_profit_percent']['scalping']:.1f}%
        
        Stop Loss Trend: {profile['stop_loss_percent']['trend']:.1f}%
        Take Profit Trend: {profile['take_profit_percent']['trend']:.1f}%
        """
        
        return summary
    
    def get_current_summary(self) -> str:
        """
        Lấy tóm tắt cấu hình hiện tại
        
        Returns:
            str: Tóm tắt cấu hình hiện tại
        """
        settings = self.get_effective_risk_settings()
        initial_balance = settings.get("initial_balance", 100.0)
        
        if self.current_config.get("custom_settings"):
            profile_type = "Tùy chỉnh"
        else:
            profile_name = self.current_config.get("risk_profile", "medium")
            profile_type = RISK_PROFILES[profile_name]["name"]
        
        max_risk_amount = initial_balance * (settings.get("max_account_risk", 25.0) / 100)
        risk_per_trade_amount = initial_balance * (settings.get("risk_per_trade", 2.5) / 100)
        max_position_size = initial_balance * (settings.get("max_margin_usage", 60.0) / 100) * settings.get("optimal_leverage", 12)
        
        summary = f"""
        === THÔNG TIN CẤU HÌNH HIỆN TẠI ===
        
        Số dư ban đầu: ${initial_balance:.2f}
        Hồ sơ rủi ro: {profile_type}
        Chiến lược: {self.current_config.get('strategy', 'trend').capitalize()}
        
        Rủi ro tối đa: {settings.get('max_account_risk', 25.0):.1f}% (${max_risk_amount:.2f})
        Rủi ro mỗi giao dịch: {settings.get('risk_per_trade', 2.5):.1f}% (${risk_per_trade_amount:.2f})
        
        Đòn bẩy tối đa: x{settings.get('max_leverage', 15)}
        Đòn bẩy khuyến nghị: x{settings.get('optimal_leverage', 12)}
        
        Kích thước vị thế tối đa: ${max_position_size:.2f}
        Số vị thế đồng thời: {settings.get('max_positions', 2)}
        
        Khoảng cách an toàn đến thanh lý: {settings.get('min_distance_to_liquidation', 30.0):.1f}%
        Sử dụng margin tối đa: {settings.get('max_margin_usage', 60.0):.1f}%
        """
        
        return summary
    
    def record_trade(self, trade_data: Dict) -> bool:
        """
        Ghi lại thông tin giao dịch để theo dõi hiệu suất
        
        Args:
            trade_data (Dict): Thông tin giao dịch
                {
                    'trade_id': str,
                    'symbol': str,
                    'side': str ('buy' or 'sell'),
                    'entry_price': float,
                    'exit_price': float,
                    'quantity': float,
                    'leverage': int,
                    'entry_time': str,
                    'exit_time': str,
                    'pnl': float,
                    'pnl_percent': float,
                    'strategy': str,
                    'stop_loss': float,
                    'take_profit': float,
                    'exit_reason': str,
                    'market_conditions': Dict,
                    'notes': str
                }
                
        Returns:
            bool: True nếu ghi thành công, False nếu không
        """
        try:
            # Làm sạch dữ liệu giao dịch
            trade = {
                'trade_id': trade_data.get('trade_id', f"trade_{len(self.performance_data['trades']) + 1}"),
                'symbol': trade_data.get('symbol', ''),
                'side': trade_data.get('side', ''),
                'entry_price': float(trade_data.get('entry_price', 0)),
                'exit_price': float(trade_data.get('exit_price', 0)),
                'quantity': float(trade_data.get('quantity', 0)),
                'leverage': int(trade_data.get('leverage', 1)),
                'entry_time': trade_data.get('entry_time', get_current_timestamp()),
                'exit_time': trade_data.get('exit_time', get_current_timestamp()),
                'pnl': float(trade_data.get('pnl', 0)),
                'pnl_percent': float(trade_data.get('pnl_percent', 0)),
                'strategy': trade_data.get('strategy', ''),
                'stop_loss': float(trade_data.get('stop_loss', 0)),
                'take_profit': float(trade_data.get('take_profit', 0)),
                'exit_reason': trade_data.get('exit_reason', ''),
                'duration': 0,
                'risk_reward_ratio': 0.0,
                'market_conditions': trade_data.get('market_conditions', {}),
                'notes': trade_data.get('notes', '')
            }
            
            # Tính thêm các chỉ số
            try:
                # Tính thời gian giao dịch
                entry_dt = parse_timestamp(trade['entry_time'])
                exit_dt = parse_timestamp(trade['exit_time'])
                duration_seconds = (exit_dt - entry_dt).total_seconds()
                trade['duration'] = duration_seconds
                
                # Tính tỷ lệ risk/reward
                if trade['stop_loss'] > 0 and trade['entry_price'] > 0:
                    if trade['side'].lower() == 'buy':
                        risk = (trade['entry_price'] - trade['stop_loss']) / trade['entry_price']
                        reward = (trade['take_profit'] - trade['entry_price']) / trade['entry_price']
                    else:  # sell
                        risk = (trade['stop_loss'] - trade['entry_price']) / trade['entry_price']
                        reward = (trade['entry_price'] - trade['take_profit']) / trade['entry_price']
                    
                    if risk > 0:
                        trade['risk_reward_ratio'] = reward / risk
            except Exception as e:
                logger.warning(f"Lỗi khi tính các chỉ số bổ sung: {e}")
            
            # Thêm giao dịch vào danh sách
            self.performance_data['trades'].append(trade)
            
            # Cập nhật các chỉ số hiệu suất
            self._update_performance_metrics()
            
            # Lưu dữ liệu hiệu suất
            return self._save_performance_data(self.performance_data)
            
        except Exception as e:
            logger.error(f"Lỗi khi ghi lại giao dịch: {e}")
            return False
    
    def _update_performance_metrics(self) -> None:
        """Cập nhật các chỉ số hiệu suất từ lịch sử giao dịch"""
        trades = self.performance_data['trades']
        
        if not trades:
            return
        
        # Tính tỷ lệ thắng và các chỉ số tổng quan
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        total_trades = len(trades)
        winning_count = len(winning_trades)
        
        if total_trades > 0:
            self.performance_data['win_rate'] = winning_count / total_trades
        
        # Tính lợi nhuận/thua lỗ trung bình
        if winning_trades:
            self.performance_data['avg_win'] = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
        
        if losing_trades:
            self.performance_data['avg_loss'] = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
        
        # Tính hệ số lợi nhuận
        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        
        if total_loss > 0:
            self.performance_data['profit_factor'] = total_profit / total_loss
        
        # Tính kỳ vọng toán học
        win_rate = self.performance_data['win_rate']
        avg_win = self.performance_data['avg_win']
        avg_loss = abs(self.performance_data['avg_loss'])
        
        if avg_loss > 0:
            self.performance_data['expectancy'] = (win_rate * avg_win / avg_loss) - (1 - win_rate)
        
        # Tính drawdown tối đa
        balances = []
        balance = 0
        for trade in trades:
            balance += trade['pnl']
            balances.append(balance)
        
        if balances:
            max_balance = max(balances)
            self.performance_data['max_drawdown'] = 0
            
            for i in range(len(balances)):
                peak = max(balances[:i+1])
                drawdown = peak - balances[i]
                drawdown_percent = drawdown / peak * 100 if peak > 0 else 0
                
                if drawdown_percent > self.performance_data['max_drawdown']:
                    self.performance_data['max_drawdown'] = drawdown_percent
        
        # Thống kê theo cặp giao dịch
        by_symbol = {}
        for trade in trades:
            symbol = trade['symbol']
            if symbol not in by_symbol:
                by_symbol[symbol] = {
                    'count': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0,
                    'win_rate': 0
                }
            
            by_symbol[symbol]['count'] += 1
            by_symbol[symbol]['total_pnl'] += trade['pnl']
            
            if trade['pnl'] > 0:
                by_symbol[symbol]['wins'] += 1
            else:
                by_symbol[symbol]['losses'] += 1
            
            if by_symbol[symbol]['count'] > 0:
                by_symbol[symbol]['win_rate'] = by_symbol[symbol]['wins'] / by_symbol[symbol]['count']
        
        self.performance_data['by_symbol'] = by_symbol
        
        # Thống kê theo chiến lược
        by_strategy = {}
        for trade in trades:
            strategy = trade['strategy']
            if not strategy:
                strategy = 'unknown'
                
            if strategy not in by_strategy:
                by_strategy[strategy] = {
                    'count': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0,
                    'win_rate': 0
                }
            
            by_strategy[strategy]['count'] += 1
            by_strategy[strategy]['total_pnl'] += trade['pnl']
            
            if trade['pnl'] > 0:
                by_strategy[strategy]['wins'] += 1
            else:
                by_strategy[strategy]['losses'] += 1
            
            if by_strategy[strategy]['count'] > 0:
                by_strategy[strategy]['win_rate'] = by_strategy[strategy]['wins'] / by_strategy[strategy]['count']
        
        self.performance_data['by_strategy'] = by_strategy
    
    def get_performance_summary(self) -> Dict:
        """
        Lấy tóm tắt hiệu suất giao dịch
        
        Returns:
            Dict: Tóm tắt hiệu suất
        """
        # Thông tin tổng quan
        summary = {
            'total_trades': len(self.performance_data['trades']),
            'win_rate': self.performance_data['win_rate'],
            'profit_factor': self.performance_data['profit_factor'],
            'expectancy': self.performance_data['expectancy'],
            'avg_win': self.performance_data['avg_win'],
            'avg_loss': self.performance_data['avg_loss'],
            'max_drawdown': self.performance_data['max_drawdown'],
            'by_symbol': self.performance_data['by_symbol'],
            'by_strategy': self.performance_data['by_strategy']
        }
        
        # Tính tổng lợi nhuận
        summary['total_pnl'] = sum(t['pnl'] for t in self.performance_data['trades'])
        
        # Thông tin giao dịch gần đây
        recent_trades = sorted(self.performance_data['trades'], 
                               key=lambda x: x.get('exit_time', ''), 
                               reverse=True)[:5]
        summary['recent_trades'] = recent_trades
        
        return summary
    
    def calculate_optimal_risk_per_trade(self) -> float:
        """
        Tính toán phần trăm rủi ro tối ưu trên mỗi giao dịch
        
        Returns:
            float: Rủi ro tối ưu trên mỗi giao dịch (%)
        """
        # Sử dụng Kelly Criterion
        win_rate = self.performance_data['win_rate']
        avg_win_ratio = 0
        
        if self.performance_data['avg_loss'] != 0:
            avg_win_ratio = self.performance_data['avg_win'] / abs(self.performance_data['avg_loss'])
        
        if win_rate <= 0 or avg_win_ratio <= 0:
            return 1.0  # Mặc định 1%
        
        kelly_percentage = (win_rate * avg_win_ratio - (1 - win_rate)) / avg_win_ratio
        
        # Giới hạn phần trăm Kelly
        half_kelly = kelly_percentage * 0.5
        
        # Giới hạn rủi ro tối đa
        max_risk = min(3.0, max(0.5, half_kelly * 100))
        
        return max_risk
    
    def optimize_take_profit_ratio(self) -> float:
        """
        Tối ưu hóa tỷ lệ take profit dựa trên dữ liệu giao dịch
        
        Returns:
            float: Tỷ lệ take profit / stop loss tối ưu
        """
        if not self.performance_data['trades']:
            return 2.0  # Mặc định 1:2
            
        avg_win = self.performance_data['avg_win']
        avg_loss = abs(self.performance_data['avg_loss'])
        win_rate = self.performance_data['win_rate']
        
        if avg_loss == 0:
            return 2.0
            
        # Tỷ lệ hiện tại
        current_ratio = avg_win / avg_loss
        
        # Nếu tỷ lệ thắng thấp, tăng tỷ lệ R:R
        if win_rate < 0.4:
            target_ratio = max(2.5, current_ratio * 1.2)
        # Nếu tỷ lệ thắng cao, có thể giảm tỷ lệ R:R để tăng số lượng giao dịch
        elif win_rate > 0.6:
            target_ratio = max(1.5, current_ratio * 0.9)
        else:
            # Giữ nguyên hoặc điều chỉnh nhẹ
            target_ratio = max(2.0, current_ratio)
            
        # Giới hạn tỷ lệ trong khoảng hợp lý
        target_ratio = min(4.0, max(1.2, target_ratio))
        
        return target_ratio
    
    def get_win_rate(self, symbol: str = None, strategy: str = None) -> float:
        """
        Lấy tỷ lệ thắng dựa trên bộ lọc
        
        Args:
            symbol (str, optional): Lọc theo cặp giao dịch
            strategy (str, optional): Lọc theo chiến lược
            
        Returns:
            float: Tỷ lệ thắng
        """
        trades = self.performance_data['trades']
        
        # Lọc theo điều kiện
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol]
            
        if strategy:
            trades = [t for t in trades if t.get('strategy') == strategy]
            
        if not trades:
            return 0.0
            
        # Tính tỷ lệ thắng
        winning_trades = [t for t in trades if t['pnl'] > 0]
        
        return len(winning_trades) / len(trades)
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, strategy: str = None) -> Dict:
        """
        Tính toán kích thước vị thế dựa trên cấu hình rủi ro
        
        Args:
            entry_price (float): Giá vào lệnh
            stop_loss (float): Giá stop loss
            strategy (str, optional): Chiến lược ('scalping', 'trend')
            
        Returns:
            Dict: Thông tin vị thế
        """
        # Lấy cài đặt rủi ro hiệu lực
        settings = self.get_effective_risk_settings()
        
        # Lấy chiến lược nếu không được cung cấp
        if strategy is None:
            strategy = self.current_config.get("strategy", "trend")
        
        # Tính khoảng cách % từ entry đến stop loss
        if entry_price > stop_loss:  # Long position
            stop_distance_percent = (entry_price - stop_loss) / entry_price * 100
            side = "buy"
        else:  # Short position
            stop_distance_percent = (stop_loss - entry_price) / entry_price * 100
            side = "sell"
        
        # Lấy các tham số cần thiết
        initial_balance = settings.get("initial_balance", 100.0)
        risk_per_trade = settings.get("risk_per_trade", 2.5)
        optimal_leverage = settings.get("optimal_leverage", 12)
        
        # Tính số tiền rủi ro
        risk_amount = initial_balance * (risk_per_trade / 100)
        
        # Tính kích thước vị thế (USD)
        position_size_usd = (risk_amount / stop_distance_percent) * 100 * optimal_leverage
        
        # Tính số lượng Bitcoin
        quantity = position_size_usd / entry_price
        
        # Kiểm tra điểm thanh lý (liquidation)
        if side == "buy":
            liquidation_price = entry_price * (1 - (1 / optimal_leverage) + 0.004)  # 0.4% duy trì margin
            liquidation_distance = (entry_price - liquidation_price) / entry_price * 100
        else:  # sell
            liquidation_price = entry_price * (1 + (1 / optimal_leverage) - 0.004)
            liquidation_distance = (liquidation_price - entry_price) / entry_price * 100
            
        # Kiểm tra khoảng cách an toàn đến thanh lý
        min_distance = settings.get("min_distance_to_liquidation", 30.0)
        if liquidation_distance * (1 - min_distance/100) > stop_distance_percent:
            # Stop loss quá gần điểm thanh lý, điều chỉnh lại kích thước vị thế
            adjustment_factor = stop_distance_percent / (liquidation_distance * (1 - min_distance/100))
            position_size_usd *= adjustment_factor
            quantity = position_size_usd / entry_price
            
        # Giới hạn kích thước vị thế tối đa
        max_margin_usage = settings.get("max_margin_usage", 60.0)
        max_size = initial_balance * (max_margin_usage/100) * optimal_leverage
        if position_size_usd > max_size:
            position_size_usd = max_size
            quantity = position_size_usd / entry_price
            
        # Tính take profit
        take_profit_ratio = settings.get("take_profit_percent", {}).get(strategy, 2.0) / settings.get("stop_loss_percent", {}).get(strategy, 1.0)
        
        if side == "buy":
            take_profit = entry_price * (1 + (stop_distance_percent * take_profit_ratio / 100))
        else:  # sell
            take_profit = entry_price * (1 - (stop_distance_percent * take_profit_ratio / 100))
            
        position_info = {
            'side': side,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'strategy': strategy,
            'leverage': optimal_leverage,
            'position_size_usd': position_size_usd,
            'quantity': quantity,
            'risk_amount': risk_amount,
            'risk_percent': risk_per_trade,
            'liquidation_price': liquidation_price,
            'stop_distance_percent': stop_distance_percent,
            'liquidation_distance_percent': liquidation_distance,
            'risk_reward_ratio': take_profit_ratio
        }
        
        return position_info

def get_current_timestamp() -> str:
    """
    Lấy thời gian hiện tại dạng chuỗi
    
    Returns:
        str: Thời gian hiện tại dạng chuỗi
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Chuyển đổi chuỗi thời gian thành đối tượng datetime
    
    Args:
        timestamp_str (str): Chuỗi thời gian định dạng "%Y-%m-%d %H:%M:%S"
        
    Returns:
        datetime: Đối tượng datetime
    """
    from datetime import datetime
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")


class RiskConfigManager:
    """Quản lý cấu hình rủi ro cho bot giao dịch"""
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH, 
                performance_path: str = PERFORMANCE_DATA_PATH):
        """
        Khởi tạo trình quản lý cấu hình rủi ro
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            performance_path (str): Đường dẫn đến file dữ liệu hiệu suất
        """
        self.config_path = config_path
        self.performance_path = performance_path
        self.current_config = self._load_or_create_default()
        self.performance_data = self._load_performance_data()
        
        logger.info(f"Đã khởi tạo RiskConfigManager, sử dụng file cấu hình: {config_path}")
        
    def optimize_risk_profile(self) -> Dict:
        """
        Tối ưu hóa cấu hình rủi ro dựa trên dữ liệu giao dịch lịch sử
        
        Returns:
            Dict: Cấu hình rủi ro đã tối ưu hóa
        """
        # Nếu không có dữ liệu đủ, giữ nguyên cấu hình hiện tại
        if len(self.performance_data['trades']) < 20:
            logger.info("Không đủ dữ liệu giao dịch để tối ưu hóa cấu hình rủi ro.")
            return self.get_effective_risk_settings()
        
        # Tính toán các tham số tối ưu
        optimal_risk_per_trade = self.calculate_optimal_risk_per_trade()
        optimal_take_profit_ratio = self.optimize_take_profit_ratio()
        
        # Xác định win rate theo chiến lược
        scalping_win_rate = self.get_win_rate(strategy="scalping")
        trend_win_rate = self.get_win_rate(strategy="trend")
        
        # Khuyến nghị chiến lược phù hợp
        if scalping_win_rate > trend_win_rate * 1.2:
            recommended_strategy = "scalping"
        elif trend_win_rate > scalping_win_rate * 1.2:
            recommended_strategy = "trend"
        else:
            recommended_strategy = "combined"
        
        # Lấy cấu hình hiện tại làm cơ sở
        current_settings = self.get_effective_risk_settings()
        
        # Tính toán số vị thế tối ưu
        if self.performance_data['max_drawdown'] > 20:
            # Drawdown cao, giảm số vị thế đồng thời
            optimal_positions = 1
        elif self.performance_data['max_drawdown'] > 10:
            optimal_positions = 2
        else:
            # Drawdown thấp, có thể tăng số vị thế
            optimal_positions = min(4, current_settings.get('max_positions', 2) + 1)
        
        # Khởi tạo cài đặt tối ưu
        optimal_settings = current_settings.copy()
        
        # Cập nhật các tham số
        optimal_settings['risk_per_trade'] = optimal_risk_per_trade
        optimal_settings['max_positions'] = optimal_positions
        
        # Cập nhật tỷ lệ take profit
        tp_to_sl_ratio = optimal_take_profit_ratio
        
        # Cập nhật tỷ lệ take profit/stop loss cho từng chiến lược
        for strategy_type in ['scalping', 'trend']:
            sl_percent = optimal_settings.get('stop_loss_percent', {}).get(strategy_type, 1.0)
            optimal_settings.setdefault('take_profit_percent', {})[strategy_type] = sl_percent * tp_to_sl_ratio
        
        # Lưu khuyến nghị chiến lược
        self.performance_data['optimal_parameters'] = {
            'timestamp': get_current_timestamp(),
            'recommended_strategy': recommended_strategy,
            'risk_per_trade': optimal_risk_per_trade,
            'max_positions': optimal_positions,
            'take_profit_ratio': tp_to_sl_ratio,
            'win_rates': {
                'overall': self.performance_data['win_rate'],
                'scalping': scalping_win_rate,
                'trend': trend_win_rate
            },
            'expectancy': self.performance_data['expectancy'],
            'max_drawdown': self.performance_data['max_drawdown']
        }
        
        # Lưu dữ liệu hiệu suất với các tham số tối ưu
        self._save_performance_data(self.performance_data)
        
        return optimal_settings
    
    def apply_optimized_settings(self, auto_apply: bool = False) -> bool:
        """
        Áp dụng cài đặt đã tối ưu hóa vào cấu hình
        
        Args:
            auto_apply (bool): Tự động áp dụng không cần xác nhận
            
        Returns:
            bool: True nếu áp dụng thành công, False nếu không
        """
        # Tạo cài đặt tối ưu mới
        optimal_settings = self.optimize_risk_profile()
        
        # Tạo cài đặt tùy chỉnh mới
        custom_settings = {
            "max_account_risk": optimal_settings.get("max_account_risk", 25.0),
            "risk_per_trade": optimal_settings.get("risk_per_trade", 2.5),
            "max_leverage": optimal_settings.get("max_leverage", 15),
            "optimal_leverage": optimal_settings.get("optimal_leverage", 12),
            "min_distance_to_liquidation": optimal_settings.get("min_distance_to_liquidation", 30.0),
            "max_positions": optimal_settings.get("max_positions", 2),
            "max_margin_usage": optimal_settings.get("max_margin_usage", 60.0),
            "use_trailing_stop": optimal_settings.get("use_trailing_stop", True),
            "min_risk_reward": optimal_settings.get("min_risk_reward", 1.5),
            "stop_loss_percent": optimal_settings.get("stop_loss_percent", {"scalping": 1.0, "trend": 1.5}),
            "take_profit_percent": optimal_settings.get("take_profit_percent", {"scalping": 1.8, "trend": 2.5})
        }
        
        # Lưu cài đặt tùy chỉnh
        self.current_config["custom_settings"] = custom_settings
        self.current_config["last_updated"] = get_current_timestamp()
        self.current_config["optimization_applied"] = True
        
        # Khuyến nghị chiến lược
        recommended_strategy = self.performance_data['optimal_parameters'].get('recommended_strategy', 'trend')
        self.current_config["strategy"] = recommended_strategy
        
        # Lưu cấu hình
        return self._save_config(self.current_config)
    
    def get_trading_optimization_report(self) -> str:
        """
        Tạo báo cáo tối ưu hóa giao dịch
        
        Returns:
            str: Báo cáo tối ưu hóa
        """
        # Kiểm tra xem có dữ liệu tối ưu không
        if not self.performance_data.get('optimal_parameters'):
            return "Chưa có dữ liệu tối ưu hóa. Hãy chạy tối ưu hóa trước khi tạo báo cáo."
        
        # Lấy dữ liệu hiệu suất
        perf = self.performance_data
        opt = perf['optimal_parameters']
        
        # Tạo báo cáo
        report = f"""
        === BÁO CÁO TỐI ƯU HÓA GIAO DỊCH ===
        
        Thời điểm tối ưu: {opt.get('timestamp', 'N/A')}
        Tổng số giao dịch phân tích: {len(perf['trades'])}
        
        ---- HIỆU SUẤT HIỆN TẠI ----
        Tỷ lệ thắng tổng thể: {perf['win_rate']*100:.1f}%
        Lợi nhuận trung bình: ${perf['avg_win']:.2f}
        Thua lỗ trung bình: ${perf['avg_loss']:.2f}
        Hệ số lợi nhuận: {perf['profit_factor']:.2f}
        Kỳ vọng toán học: {perf['expectancy']:.2f}
        Drawdown tối đa: {perf['max_drawdown']:.1f}%
        
        ---- KHUYẾN NGHỊ TỐI ƯU ----
        Chiến lược: {opt.get('recommended_strategy', 'trend').capitalize()}
        Rủi ro mỗi giao dịch: {opt.get('risk_per_trade', 2.5):.2f}%
        Số vị thế đồng thời: {opt.get('max_positions', 2)}
        Tỷ lệ TP:SL: {opt.get('take_profit_ratio', 2.0):.2f}
        
        ---- PHÂN TÍCH THEO CHIẾN LƯỢC ----
        Scalping - Tỷ lệ thắng: {opt.get('win_rates', {}).get('scalping', 0)*100:.1f}%
        Trend - Tỷ lệ thắng: {opt.get('win_rates', {}).get('trend', 0)*100:.1f}%
        
        ---- KHUYẾN NGHỊ HÀNH ĐỘNG ----
        """
        
        # Thêm khuyến nghị cụ thể dựa trên phân tích
        if perf['win_rate'] < 0.4:
            report += "- Tăng tỷ lệ risk:reward để bù đắp tỷ lệ thắng thấp\n"
            report += "- Giảm kích thước vị thế để giảm drawdown\n"
        
        if perf['max_drawdown'] > 20:
            report += "- Drawdown cao, nên giảm đòn bẩy và rủi ro mỗi giao dịch\n"
        
        if perf['profit_factor'] < 1.2:
            report += "- Hệ số lợi nhuận thấp, cần cải thiện quản lý vị thế hoặc chiến lược\n"
        
        if opt.get('win_rates', {}).get('scalping', 0) > opt.get('win_rates', {}).get('trend', 0) * 1.3:
            report += "- Chiến lược scalping hiệu quả hơn nhiều so với trend, nên tập trung vào scalping\n"
        
        if opt.get('win_rates', {}).get('trend', 0) > opt.get('win_rates', {}).get('scalping', 0) * 1.3:
            report += "- Chiến lược trend hiệu quả hơn nhiều so với scalping, nên tập trung vào trend\n"
        
        return report

def main():
    """Hàm chính để test và demo RiskConfigManager"""
    # Khởi tạo trình quản lý cấu hình
    risk_manager = RiskConfigManager()
    
    # Hiển thị thông tin các hồ sơ rủi ro
    print("=== CÁC HỒ SƠ RỦI RO CÓ SẴN ===\n")
    for profile_name, profile in RISK_PROFILES.items():
        print(f"{profile_name}: {profile['name']}")
        print(f"  {profile['description']}")
        print()
    
    # Demo thiết lập cấu hình
    print("=== DEMO THIẾT LẬP CẤU HÌNH ===\n")
    
    # Cấu hình mặc định
    print("1. Cấu hình mặc định:")
    print(risk_manager.get_current_summary())
    
    # Thay đổi vốn ban đầu
    risk_manager.set_initial_balance(200.0)
    print("\n2. Sau khi thay đổi vốn ban đầu:")
    print(risk_manager.get_current_summary())
    
    # Thay đổi hồ sơ rủi ro
    risk_manager.set_risk_profile("high")
    print("\n3. Sau khi thay đổi hồ sơ rủi ro sang 'high':")
    print(risk_manager.get_current_summary())
    
    # Thay đổi chiến lược
    risk_manager.set_strategy("scalping")
    print("\n4. Sau khi thay đổi chiến lược sang 'scalping':")
    print(risk_manager.get_current_summary())
    
    # Demo tính toán kích thước vị thế
    print("\n=== DEMO TÍNH TOÁN KÍCH THƯỚC VỊ THẾ ===\n")
    
    entry_price = 50000.0
    stop_loss = 49250.0  # 1.5% dưới giá vào
    
    position_info = risk_manager.calculate_position_size(entry_price, stop_loss, "scalping")
    
    print(f"Giá vào lệnh: ${entry_price:.2f}")
    print(f"Stop Loss: ${stop_loss:.2f} ({position_info['stop_distance_percent']:.2f}%)")
    print(f"Take Profit: ${position_info['take_profit']:.2f}")
    print(f"Đòn bẩy: x{position_info['leverage']}")
    print(f"Kích thước vị thế: ${position_info['position_size_usd']:.2f}")
    print(f"Số lượng Bitcoin: {position_info['quantity']:.8f} BTC")
    print(f"Điểm thanh lý: ${position_info['liquidation_price']:.2f} ({position_info['liquidation_distance_percent']:.2f}%)")
    print(f"Rủi ro: ${position_info['risk_amount']:.2f} ({position_info['risk_percent']:.2f}%)")
    print(f"Tỷ lệ R:R: 1:{position_info['risk_reward_ratio']:.2f}")
    
    # Demo ghi lại giao dịch
    print("\n=== DEMO GHI LẠI GIAO DỊCH ===\n")
    
    # Tạo vài giao dịch giả lập để test
    test_trades = [
        {
            'trade_id': 'test_1',
            'symbol': 'BTCUSDT',
            'side': 'buy',
            'entry_price': 50000.0,
            'exit_price': 52000.0,
            'quantity': 0.1,
            'leverage': 10,
            'pnl': 200.0,
            'pnl_percent': 4.0,
            'strategy': 'trend',
            'stop_loss': 49000.0,
            'take_profit': 53000.0,
            'exit_reason': 'take_profit',
        },
        {
            'trade_id': 'test_2',
            'symbol': 'ETHUSDT',
            'side': 'buy',
            'entry_price': 3000.0,
            'exit_price': 2900.0,
            'quantity': 1.0,
            'leverage': 10,
            'pnl': -100.0,
            'pnl_percent': -3.33,
            'strategy': 'scalping',
            'stop_loss': 2850.0,
            'take_profit': 3200.0,
            'exit_reason': 'manual_close',
        },
        {
            'trade_id': 'test_3',
            'symbol': 'BTCUSDT',
            'side': 'sell',
            'entry_price': 48000.0,
            'exit_price': 46000.0,
            'quantity': 0.05,
            'leverage': 10,
            'pnl': 100.0,
            'pnl_percent': 4.17,
            'strategy': 'trend',
            'stop_loss': 49000.0,
            'take_profit': 45000.0,
            'exit_reason': 'take_profit',
        },
    ]
    
    # Ghi lại các giao dịch
    for trade in test_trades:
        success = risk_manager.record_trade(trade)
        print(f"Ghi lại giao dịch {trade['trade_id']}: {'Thành công' if success else 'Thất bại'}")
    
    # Demo hiệu suất
    print("\n=== TỔNG HỢP HIỆU SUẤT ===\n")
    performance = risk_manager.get_performance_summary()
    
    print(f"Tổng số giao dịch: {performance['total_trades']}")
    print(f"Tỷ lệ thắng: {performance['win_rate'] * 100:.1f}%")
    print(f"Hệ số lợi nhuận: {performance['profit_factor']:.2f}")
    print(f"Kỳ vọng toán học: {performance['expectancy']:.2f}")
    print(f"Tổng P&L: ${performance['total_pnl']:.2f}")
    
    # Demo tối ưu hóa
    print("\n=== TỐI ƯU HÓA CHIẾN LƯỢC ===\n")
    optimal_settings = risk_manager.optimize_risk_profile()
    
    print(f"Rủi ro mỗi giao dịch tối ưu: {optimal_settings.get('risk_per_trade', 0):.2f}%")
    print(f"Số vị thế đồng thời tối ưu: {optimal_settings.get('max_positions', 0)}")
    
    # Áp dụng cài đặt tối ưu
    risk_manager.apply_optimized_settings(auto_apply=True)
    
    # Hiển thị báo cáo tối ưu hóa
    print("\n=== BÁO CÁO TỐI ƯU HÓA ===\n")
    print(risk_manager.get_trading_optimization_report())
    
    # Đặt lại về mặc định
    risk_manager.reset_to_default()
    print("\nĐã đặt lại cấu hình về mặc định")

if __name__ == "__main__":
    main()