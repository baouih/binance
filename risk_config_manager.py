#!/usr/bin/env python3
"""
Quản lý cấu hình rủi ro cho bot giao dịch

Module này cho phép cấu hình các thông số rủi ro và vốn ban đầu cho bot giao dịch.
Người dùng có thể chọn từ các hồ sơ rủi ro được cài đặt sẵn hoặc tạo cấu hình tùy chỉnh.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_config")

# Đường dẫn lưu cấu hình
CONFIG_DIR = "configs"
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "risk_config.json")

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
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """
        Khởi tạo trình quản lý cấu hình rủi ro
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.config_path = config_path
        self.current_config = self._load_or_create_default()
        
        logger.info(f"Đã khởi tạo RiskConfigManager, sử dụng file cấu hình: {config_path}")
    
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
    
    # Đặt lại về mặc định
    risk_manager.reset_to_default()
    print("\nĐã đặt lại cấu hình về mặc định")

if __name__ == "__main__":
    main()