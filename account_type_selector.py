#!/usr/bin/env python3
"""
Module lựa chọn loại tài khoản giao dịch (Spot/Futures)

Module này cho phép người dùng lựa chọn và cấu hình loại tài khoản (spot hoặc futures)
cho bot giao dịch, cùng với các tham số và giới hạn tương ứng.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("account_type_selector")

# Đường dẫn lưu cấu hình
CONFIG_DIR = "configs"
ACCOUNT_CONFIG_PATH = os.path.join(CONFIG_DIR, "account_config.json")

# Tạo thư mục configs nếu chưa tồn tại
os.makedirs(CONFIG_DIR, exist_ok=True)

# Cấu hình mặc định cho các loại tài khoản
DEFAULT_ACCOUNT_TYPES = {
    "spot": {
        "name": "Spot (Mua/Bán thông thường)",
        "description": "Giao dịch mua/bán thông thường, không sử dụng đòn bẩy. An toàn hơn nhưng lợi nhuận thấp hơn.",
        "leverage_available": False,
        "max_leverage": 1,
        "default_leverage": 1,
        "margin_required": False,
        "short_available": False,
        "trading_fee": 0.1,  # 0.1%
        "default_order_types": ["LIMIT", "MARKET", "STOP_LOSS", "TAKE_PROFIT"],
        "min_order_size": 10.0,  # USD
        "default_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
        "default_timeframes": ["1h", "4h", "1d"]
    },
    "futures": {
        "name": "Futures (Hợp đồng tương lai)",
        "description": "Giao dịch hợp đồng tương lai với đòn bẩy, cho phép bán khống. Rủi ro cao hơn nhưng tiềm năng lợi nhuận lớn hơn.",
        "leverage_available": True,
        "max_leverage": 20,
        "default_leverage": 10,
        "margin_required": True,
        "short_available": True,
        "trading_fee": 0.04,  # 0.04%
        "default_order_types": ["LIMIT", "MARKET", "STOP", "TAKE_PROFIT", "TRAILING_STOP"],
        "min_order_size": 5.0,  # USD
        "default_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"],
        "default_timeframes": ["5m", "15m", "1h", "4h"]
    }
}

class AccountTypeSelector:
    """Lớp lựa chọn và cấu hình loại tài khoản giao dịch"""
    
    def __init__(self, config_path: str = ACCOUNT_CONFIG_PATH):
        """
        Khởi tạo bộ chọn loại tài khoản
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình tài khoản
        """
        self.config_path = config_path
        self.current_config = self._load_or_create_default()
        
        logger.info(f"Đã khởi tạo AccountTypeSelector, sử dụng file cấu hình: {config_path}")
    
    def _load_or_create_default(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Cấu hình tài khoản
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
            "account_type": "futures",     # Mặc định là futures
            "custom_settings": None,       # Cài đặt tùy chỉnh: None
            "symbols": DEFAULT_ACCOUNT_TYPES["futures"]["default_symbols"],
            "timeframes": DEFAULT_ACCOUNT_TYPES["futures"]["default_timeframes"],
            "leverage": 10,                # Đòn bẩy mặc định: x10
            "last_updated": None,          # Thời gian cập nhật cuối
            "creator": "system"            # Người tạo: system
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
    
    def get_account_types(self) -> Dict:
        """
        Lấy danh sách các loại tài khoản có sẵn
        
        Returns:
            Dict: Danh sách các loại tài khoản
        """
        return DEFAULT_ACCOUNT_TYPES
    
    def set_account_type(self, account_type: str) -> bool:
        """
        Đặt loại tài khoản
        
        Args:
            account_type (str): Loại tài khoản ('spot' hoặc 'futures')
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if account_type not in DEFAULT_ACCOUNT_TYPES:
            logger.error(f"Loại tài khoản không hợp lệ: {account_type}")
            return False
            
        self.current_config["account_type"] = account_type
        
        # Cập nhật các tham số liên quan
        account_settings = DEFAULT_ACCOUNT_TYPES[account_type]
        self.current_config["symbols"] = account_settings["default_symbols"]
        self.current_config["timeframes"] = account_settings["default_timeframes"]
        
        if account_type == "futures" and "leverage" not in self.current_config:
            self.current_config["leverage"] = account_settings["default_leverage"]
        elif account_type == "spot":
            self.current_config["leverage"] = 1  # Không có đòn bẩy cho spot
            
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def set_symbols(self, symbols: list) -> bool:
        """
        Đặt danh sách các cặp giao dịch
        
        Args:
            symbols (list): Danh sách các cặp giao dịch
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if not symbols or not isinstance(symbols, list):
            logger.error("Danh sách symbols không hợp lệ")
            return False
            
        self.current_config["symbols"] = symbols
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def set_timeframes(self, timeframes: list) -> bool:
        """
        Đặt danh sách các khung thời gian
        
        Args:
            timeframes (list): Danh sách các khung thời gian
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if not timeframes or not isinstance(timeframes, list):
            logger.error("Danh sách timeframes không hợp lệ")
            return False
            
        self.current_config["timeframes"] = timeframes
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def set_leverage(self, leverage: int) -> bool:
        """
        Đặt đòn bẩy (chỉ cho futures)
        
        Args:
            leverage (int): Đòn bẩy
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        account_type = self.current_config.get("account_type", "futures")
        
        if account_type == "spot":
            logger.warning("Không thể đặt đòn bẩy cho tài khoản spot")
            return False
            
        if leverage <= 0 or leverage > DEFAULT_ACCOUNT_TYPES["futures"]["max_leverage"]:
            logger.error(f"Đòn bẩy không hợp lệ: {leverage}, phải trong khoảng [1, {DEFAULT_ACCOUNT_TYPES['futures']['max_leverage']}]")
            return False
            
        self.current_config["leverage"] = leverage
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def get_effective_settings(self) -> Dict:
        """
        Lấy cài đặt tài khoản hiệu lực
        
        Returns:
            Dict: Cài đặt tài khoản hiệu lực
        """
        effective_settings = {}
        
        # Bắt đầu với các cài đặt mặc định của loại tài khoản
        account_type = self.current_config.get("account_type", "futures")
        effective_settings.update(DEFAULT_ACCOUNT_TYPES[account_type])
        
        # Ghi đè với các cài đặt trong cấu hình
        effective_settings["symbols"] = self.current_config.get("symbols", effective_settings["default_symbols"])
        effective_settings["timeframes"] = self.current_config.get("timeframes", effective_settings["default_timeframes"])
        
        if account_type == "futures":
            effective_settings["leverage"] = self.current_config.get("leverage", effective_settings["default_leverage"])
        else:
            effective_settings["leverage"] = 1
            
        return effective_settings
    
    def get_account_summary(self) -> str:
        """
        Lấy tóm tắt cài đặt tài khoản hiện tại
        
        Returns:
            str: Tóm tắt cài đặt tài khoản
        """
        settings = self.get_effective_settings()
        account_type = self.current_config.get("account_type", "futures")
        
        summary = f"""
        === THÔNG TIN CẤU HÌNH TÀI KHOẢN ===
        
        Loại tài khoản: {settings['name']}
        {settings['description']}
        
        Biểu tượng giao dịch: {', '.join(settings['symbols'])}
        Khung thời gian: {', '.join(settings['timeframes'])}
        
        Phí giao dịch: {settings['trading_fee']}%
        Loại lệnh hỗ trợ: {', '.join(settings['default_order_types'])}
        Kích thước lệnh tối thiểu: {settings['min_order_size']} USD
        """
        
        if account_type == "futures":
            summary += f"""
        Đòn bẩy: x{settings['leverage']}
        Đòn bẩy tối đa: x{settings['max_leverage']}
        """
            
        return summary
    
    def reset_to_default(self) -> bool:
        """
        Đặt lại cấu hình về mặc định
        
        Returns:
            bool: True nếu đặt lại thành công
        """
        default_config = {
            "account_type": "futures",
            "custom_settings": None,
            "symbols": DEFAULT_ACCOUNT_TYPES["futures"]["default_symbols"],
            "timeframes": DEFAULT_ACCOUNT_TYPES["futures"]["default_timeframes"],
            "leverage": 10,
            "last_updated": get_current_timestamp(),
            "creator": "system"
        }
        
        self.current_config = default_config
        return self._save_config(self.current_config)
        
def get_current_timestamp() -> str:
    """
    Lấy thời gian hiện tại dạng chuỗi
    
    Returns:
        str: Thời gian hiện tại dạng chuỗi
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    """Hàm chính để test AccountTypeSelector"""
    selector = AccountTypeSelector()
    
    print("===== CẤU HÌNH LOẠI TÀI KHOẢN GIAO DỊCH =====")
    print()
    
    # Hiển thị cấu hình hiện tại
    current_config = selector.get_current_config()
    current_type = current_config.get("account_type", "futures")
    print(f"Loại tài khoản hiện tại: {current_type}")
    print()
    
    # Hiển thị menu
    account_types = selector.get_account_types()
    print("Các loại tài khoản có sẵn:")
    for i, (type_name, type_info) in enumerate(account_types.items(), 1):
        print(f"{i}. {type_info['name']}")
        print(f"   {type_info['description']}")
        print()
    
    # Chọn loại tài khoản
    choice = input("Chọn loại tài khoản (1-2, Enter để giữ nguyên): ")
    
    types = {
        "1": "spot",
        "2": "futures"
    }
    
    if choice and choice in types:
        account_type = types[choice]
        if selector.set_account_type(account_type):
            print(f"Đã chọn loại tài khoản: {account_type}")
        else:
            print("Lỗi khi đặt loại tài khoản.")
    
    # Nếu là futures, chọn đòn bẩy
    if current_type == "futures" or (choice and types.get(choice) == "futures"):
        leverage = input(f"Nhập đòn bẩy (1-20, mặc định: {selector.current_config.get('leverage', 10)}): ")
        
        if leverage:
            try:
                leverage = int(leverage)
                if selector.set_leverage(leverage):
                    print(f"Đã đặt đòn bẩy: x{leverage}")
                else:
                    print("Lỗi khi đặt đòn bẩy.")
            except ValueError:
                print("Giá trị đòn bẩy không hợp lệ.")
    
    # Hiển thị tóm tắt
    print("\nTóm tắt cấu hình tài khoản:")
    print(selector.get_account_summary())

if __name__ == "__main__":
    main()