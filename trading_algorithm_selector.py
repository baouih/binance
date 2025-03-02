#!/usr/bin/env python3
"""
Module chọn thuật toán giao dịch

Module này cho phép người dùng lựa chọn và cấu hình các thuật toán giao dịch
khác nhau, cùng với các tham số tương ứng và cập nhật cấu hình.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("trading_algorithm_selector")

# Đường dẫn lưu cấu hình
CONFIG_DIR = "configs"
ALGORITHM_CONFIG_PATH = os.path.join(CONFIG_DIR, "algorithm_config.json")

# Tạo thư mục configs nếu chưa tồn tại
os.makedirs(CONFIG_DIR, exist_ok=True)

# Mô tả các thuật toán giao dịch có sẵn
AVAILABLE_ALGORITHMS = {
    "rsi_strategy": {
        "name": "RSI Strategy (Relative Strength Index)",
        "description": "Chiến lược giao dịch dựa trên chỉ báo RSI, phù hợp cho thị trường sideway.",
        "category": "indicator_based",
        "complexity": "simple",
        "timeframes": ["15m", "1h", "4h"],
        "parameters": {
            "rsi_period": {
                "description": "Chu kỳ RSI",
                "default": 14,
                "min": 5,
                "max": 30,
                "type": "int"
            },
            "rsi_overbought": {
                "description": "Ngưỡng mua quá (overbought)",
                "default": 70,
                "min": 60,
                "max": 90,
                "type": "int"
            },
            "rsi_oversold": {
                "description": "Ngưỡng bán quá (oversold)",
                "default": 30,
                "min": 10,
                "max": 40,
                "type": "int"
            },
            "use_ema_confirmation": {
                "description": "Sử dụng EMA để xác nhận",
                "default": True,
                "type": "bool"
            },
            "ema_period": {
                "description": "Chu kỳ EMA để xác nhận",
                "default": 50,
                "min": 20,
                "max": 200,
                "type": "int"
            }
        }
    },
    "macd_strategy": {
        "name": "MACD Strategy (Moving Average Convergence Divergence)",
        "description": "Chiến lược giao dịch dựa trên chỉ báo MACD, phù hợp để nắm bắt xu hướng.",
        "category": "indicator_based",
        "complexity": "medium",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "fast_period": {
                "description": "Chu kỳ đường nhanh",
                "default": 12,
                "min": 5,
                "max": 20,
                "type": "int"
            },
            "slow_period": {
                "description": "Chu kỳ đường chậm",
                "default": 26,
                "min": 15,
                "max": 40,
                "type": "int"
            },
            "signal_period": {
                "description": "Chu kỳ đường tín hiệu",
                "default": 9,
                "min": 5,
                "max": 15,
                "type": "int"
            },
            "use_histogram": {
                "description": "Sử dụng histogram để tạo tín hiệu",
                "default": True,
                "type": "bool"
            },
            "use_price_action": {
                "description": "Kết hợp với price action",
                "default": False,
                "type": "bool"
            }
        }
    },
    "bollinger_strategy": {
        "name": "Bollinger Bands Strategy",
        "description": "Chiến lược giao dịch dựa trên băng Bollinger, phù hợp cho thị trường dao động và đảo chiều.",
        "category": "volatility_based",
        "complexity": "medium",
        "timeframes": ["15m", "1h", "4h"],
        "parameters": {
            "bb_period": {
                "description": "Chu kỳ Bollinger",
                "default": 20,
                "min": 10,
                "max": 50,
                "type": "int"
            },
            "bb_std": {
                "description": "Độ lệch chuẩn",
                "default": 2.0,
                "min": 1.0,
                "max": 3.0,
                "type": "float"
            },
            "use_bb_squeeze": {
                "description": "Sử dụng kỹ thuật Bollinger Squeeze",
                "default": True,
                "type": "bool"
            },
            "use_rsi_filter": {
                "description": "Sử dụng RSI để lọc tín hiệu",
                "default": True,
                "type": "bool"
            },
            "rsi_period": {
                "description": "Chu kỳ RSI",
                "default": 14,
                "min": 5,
                "max": 30,
                "type": "int"
            }
        }
    },
    "ema_cross_strategy": {
        "name": "EMA Crossover Strategy",
        "description": "Chiến lược giao dịch dựa trên giao cắt EMA, phù hợp cho thị trường có xu hướng mạnh.",
        "category": "trend_based",
        "complexity": "simple",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "fast_ema": {
                "description": "Chu kỳ EMA nhanh",
                "default": 10,
                "min": 5,
                "max": 20,
                "type": "int"
            },
            "slow_ema": {
                "description": "Chu kỳ EMA chậm",
                "default": 50,
                "min": 20,
                "max": 200,
                "type": "int"
            },
            "use_volume_filter": {
                "description": "Sử dụng lọc khối lượng",
                "default": True,
                "type": "bool"
            },
            "volume_period": {
                "description": "Chu kỳ lọc khối lượng",
                "default": 20,
                "min": 10,
                "max": 50,
                "type": "int"
            },
            "use_adx_filter": {
                "description": "Sử dụng lọc ADX",
                "default": False,
                "type": "bool"
            }
        }
    },
    "support_resistance_strategy": {
        "name": "Support & Resistance Strategy",
        "description": "Chiến lược giao dịch dựa trên hỗ trợ và kháng cự, kết hợp với price action.",
        "category": "price_action",
        "complexity": "advanced",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "lookback_period": {
                "description": "Chu kỳ nhìn lại để tìm hỗ trợ/kháng cự",
                "default": 100,
                "min": 50,
                "max": 500,
                "type": "int"
            },
            "zone_threshold": {
                "description": "Ngưỡng xác định vùng hỗ trợ/kháng cự",
                "default": 0.5,
                "min": 0.2,
                "max": 1.0,
                "type": "float"
            },
            "use_fibonacci": {
                "description": "Sử dụng mức Fibonacci",
                "default": True,
                "type": "bool"
            },
            "confirmation_candles": {
                "description": "Số nến xác nhận",
                "default": 2,
                "min": 1,
                "max": 5,
                "type": "int"
            },
            "use_volume_confirmation": {
                "description": "Sử dụng khối lượng để xác nhận",
                "default": True,
                "type": "bool"
            }
        }
    },
    "breakout_strategy": {
        "name": "Breakout Strategy",
        "description": "Chiến lược giao dịch đột phá, phù hợp cho thị trường hình thành xu hướng mới.",
        "category": "price_action",
        "complexity": "medium",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "lookback_period": {
                "description": "Chu kỳ nhìn lại để tìm mẫu hình",
                "default": 50,
                "min": 20,
                "max": 200,
                "type": "int"
            },
            "breakout_threshold": {
                "description": "Ngưỡng xác định đột phá",
                "default": 1.0,
                "min": 0.5,
                "max": 3.0,
                "type": "float"
            },
            "use_volume_surge": {
                "description": "Sử dụng tăng vọt khối lượng để xác nhận",
                "default": True,
                "type": "bool"
            },
            "volume_surge_threshold": {
                "description": "Ngưỡng tăng vọt khối lượng",
                "default": 1.5,
                "min": 1.2,
                "max": 3.0,
                "type": "float"
            },
            "confirmation_candles": {
                "description": "Số nến xác nhận",
                "default": 1,
                "min": 1,
                "max": 3,
                "type": "int"
            }
        }
    },
    "ml_strategy": {
        "name": "Machine Learning Strategy",
        "description": "Chiến lược giao dịch dựa trên mô hình Machine Learning, phù hợp cho thị trường phức tạp.",
        "category": "ml_based",
        "complexity": "advanced",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "model_type": {
                "description": "Loại mô hình",
                "default": "RandomForest",
                "options": ["RandomForest", "XGBoost", "LSTM", "Ensemble"],
                "type": "enum"
            },
            "feature_count": {
                "description": "Số đặc trưng sử dụng",
                "default": 20,
                "min": 10,
                "max": 50,
                "type": "int"
            },
            "prediction_horizon": {
                "description": "Khoảng thời gian dự đoán",
                "default": 12,
                "min": 3,
                "max": 24,
                "type": "int"
            },
            "confidence_threshold": {
                "description": "Ngưỡng độ tin cậy",
                "default": 0.7,
                "min": 0.5,
                "max": 0.95,
                "type": "float"
            },
            "use_market_regime": {
                "description": "Sử dụng phát hiện chế độ thị trường",
                "default": True,
                "type": "bool"
            }
        }
    },
    "combined_strategy": {
        "name": "Combined Strategy",
        "description": "Kết hợp nhiều chiến lược với trọng số động, tự động chọn chiến lược tốt nhất cho điều kiện thị trường hiện tại.",
        "category": "hybrid",
        "complexity": "advanced",
        "timeframes": ["1h", "4h", "1d"],
        "parameters": {
            "strategies": {
                "description": "Các chiến lược sử dụng",
                "default": ["rsi_strategy", "macd_strategy", "bollinger_strategy"],
                "options": ["rsi_strategy", "macd_strategy", "bollinger_strategy", "ema_cross_strategy", "support_resistance_strategy", "breakout_strategy", "ml_strategy"],
                "type": "multi_select"
            },
            "dynamic_weights": {
                "description": "Sử dụng trọng số động",
                "default": True,
                "type": "bool"
            },
            "use_market_regime": {
                "description": "Sử dụng phát hiện chế độ thị trường",
                "default": True,
                "type": "bool"
            },
            "min_signal_agreement": {
                "description": "Tỷ lệ đồng thuận tối thiểu",
                "default": 0.5,
                "min": 0.3,
                "max": 0.8,
                "type": "float"
            },
            "performance_lookback": {
                "description": "Chu kỳ nhìn lại để đánh giá hiệu suất",
                "default": 50,
                "min": 20,
                "max": 200,
                "type": "int"
            }
        }
    }
}

class TradingAlgorithmSelector:
    """Lớp lựa chọn và cấu hình thuật toán giao dịch"""
    
    def __init__(self, config_path: str = ALGORITHM_CONFIG_PATH):
        """
        Khởi tạo bộ chọn thuật toán giao dịch
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình thuật toán
        """
        self.config_path = config_path
        self.current_config = self._load_or_create_default()
        
        logger.info(f"Đã khởi tạo TradingAlgorithmSelector, sử dụng file cấu hình: {config_path}")
    
    def _load_or_create_default(self) -> Dict:
        """
        Tải cấu hình từ file hoặc tạo mới nếu không tồn tại
        
        Returns:
            Dict: Cấu hình thuật toán
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
            "primary_algorithm": "combined_strategy",
            "backup_algorithm": "ema_cross_strategy",
            "algorithms": {},
            "last_updated": None,
            "creator": "system"
        }
        
        # Thêm các tham số mặc định cho mỗi thuật toán
        for algo_name, algo_info in AVAILABLE_ALGORITHMS.items():
            default_config["algorithms"][algo_name] = {
                "enabled": True if algo_name in ["combined_strategy", "ema_cross_strategy"] else False,
                "parameters": {}
            }
            
            # Thêm các tham số mặc định
            for param_name, param_info in algo_info["parameters"].items():
                default_config["algorithms"][algo_name]["parameters"][param_name] = param_info["default"]
        
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
    
    def get_available_algorithms(self) -> Dict:
        """
        Lấy danh sách các thuật toán có sẵn
        
        Returns:
            Dict: Danh sách các thuật toán
        """
        return AVAILABLE_ALGORITHMS
    
    def set_primary_algorithm(self, algorithm: str) -> bool:
        """
        Đặt thuật toán chính
        
        Args:
            algorithm (str): Tên thuật toán
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if algorithm not in AVAILABLE_ALGORITHMS:
            logger.error(f"Thuật toán không hợp lệ: {algorithm}")
            return False
            
        self.current_config["primary_algorithm"] = algorithm
        
        # Đảm bảo thuật toán được kích hoạt
        self.current_config["algorithms"][algorithm]["enabled"] = True
        
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def set_backup_algorithm(self, algorithm: str) -> bool:
        """
        Đặt thuật toán dự phòng
        
        Args:
            algorithm (str): Tên thuật toán
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if algorithm not in AVAILABLE_ALGORITHMS:
            logger.error(f"Thuật toán không hợp lệ: {algorithm}")
            return False
            
        self.current_config["backup_algorithm"] = algorithm
        
        # Đảm bảo thuật toán được kích hoạt
        self.current_config["algorithms"][algorithm]["enabled"] = True
        
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def enable_algorithm(self, algorithm: str, enabled: bool = True) -> bool:
        """
        Bật/tắt một thuật toán
        
        Args:
            algorithm (str): Tên thuật toán
            enabled (bool): Trạng thái kích hoạt
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if algorithm not in AVAILABLE_ALGORITHMS:
            logger.error(f"Thuật toán không hợp lệ: {algorithm}")
            return False
            
        self.current_config["algorithms"][algorithm]["enabled"] = enabled
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def update_algorithm_parameters(self, algorithm: str, parameters: Dict) -> bool:
        """
        Cập nhật tham số cho một thuật toán
        
        Args:
            algorithm (str): Tên thuật toán
            parameters (Dict): Tham số mới
            
        Returns:
            bool: True nếu cập nhật thành công
        """
        if algorithm not in AVAILABLE_ALGORITHMS:
            logger.error(f"Thuật toán không hợp lệ: {algorithm}")
            return False
            
        # Xác thực tham số
        for param_name, param_value in parameters.items():
            if param_name not in AVAILABLE_ALGORITHMS[algorithm]["parameters"]:
                logger.error(f"Tham số không hợp lệ: {param_name}")
                return False
                
            param_info = AVAILABLE_ALGORITHMS[algorithm]["parameters"][param_name]
            
            # Kiểm tra kiểu dữ liệu
            if param_info["type"] == "int":
                if not isinstance(param_value, int):
                    logger.error(f"Tham số {param_name} phải là số nguyên")
                    return False
                    
                if "min" in param_info and param_value < param_info["min"]:
                    logger.error(f"Tham số {param_name} phải lớn hơn hoặc bằng {param_info['min']}")
                    return False
                    
                if "max" in param_info and param_value > param_info["max"]:
                    logger.error(f"Tham số {param_name} phải nhỏ hơn hoặc bằng {param_info['max']}")
                    return False
            
            elif param_info["type"] == "float":
                if not isinstance(param_value, (float, int)):
                    logger.error(f"Tham số {param_name} phải là số thực")
                    return False
                    
                if "min" in param_info and param_value < param_info["min"]:
                    logger.error(f"Tham số {param_name} phải lớn hơn hoặc bằng {param_info['min']}")
                    return False
                    
                if "max" in param_info and param_value > param_info["max"]:
                    logger.error(f"Tham số {param_name} phải nhỏ hơn hoặc bằng {param_info['max']}")
                    return False
            
            elif param_info["type"] == "bool":
                if not isinstance(param_value, bool):
                    logger.error(f"Tham số {param_name} phải là boolean")
                    return False
            
            elif param_info["type"] == "enum":
                if param_value not in param_info["options"]:
                    logger.error(f"Tham số {param_name} phải là một trong {param_info['options']}")
                    return False
            
            elif param_info["type"] == "multi_select":
                if not isinstance(param_value, list):
                    logger.error(f"Tham số {param_name} phải là danh sách")
                    return False
                    
                for item in param_value:
                    if item not in param_info["options"]:
                        logger.error(f"Phần tử {item} trong {param_name} phải là một trong {param_info['options']}")
                        return False
        
        # Cập nhật tham số
        for param_name, param_value in parameters.items():
            self.current_config["algorithms"][algorithm]["parameters"][param_name] = param_value
            
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def reset_algorithm_parameters(self, algorithm: str) -> bool:
        """
        Đặt lại tham số cho một thuật toán về mặc định
        
        Args:
            algorithm (str): Tên thuật toán
            
        Returns:
            bool: True nếu đặt lại thành công
        """
        if algorithm not in AVAILABLE_ALGORITHMS:
            logger.error(f"Thuật toán không hợp lệ: {algorithm}")
            return False
            
        # Đặt lại tham số về mặc định
        self.current_config["algorithms"][algorithm]["parameters"] = {}
        
        for param_name, param_info in AVAILABLE_ALGORITHMS[algorithm]["parameters"].items():
            self.current_config["algorithms"][algorithm]["parameters"][param_name] = param_info["default"]
            
        self.current_config["last_updated"] = get_current_timestamp()
        
        return self._save_config(self.current_config)
    
    def get_algorithm_summary(self, algorithm: str) -> str:
        """
        Lấy tóm tắt cấu hình thuật toán
        
        Args:
            algorithm (str): Tên thuật toán
            
        Returns:
            str: Tóm tắt cấu hình thuật toán
        """
        if algorithm not in AVAILABLE_ALGORITHMS:
            return f"Thuật toán không tồn tại: {algorithm}"
            
        algo_info = AVAILABLE_ALGORITHMS[algorithm]
        algo_config = self.current_config["algorithms"][algorithm]
        
        summary = f"""
        === THÔNG TIN THUẬT TOÁN: {algo_info['name']} ===
        
        {algo_info['description']}
        
        Loại: {algo_info['category']}
        Độ phức tạp: {algo_info['complexity']}
        Khung thời gian phù hợp: {', '.join(algo_info['timeframes'])}
        Trạng thái: {'Kích hoạt' if algo_config['enabled'] else 'Không kích hoạt'}
        
        Tham số:
        """
        
        for param_name, param_info in algo_info["parameters"].items():
            param_value = algo_config["parameters"].get(param_name, param_info["default"])
            
            summary += f"  - {param_name}: {param_value} ({param_info['description']})\n"
            
        if algorithm == self.current_config["primary_algorithm"]:
            summary += "\n  [Đây là thuật toán chính]"
            
        if algorithm == self.current_config["backup_algorithm"]:
            summary += "\n  [Đây là thuật toán dự phòng]"
            
        return summary
    
    def get_current_summary(self) -> str:
        """
        Lấy tóm tắt cấu hình thuật toán hiện tại
        
        Returns:
            str: Tóm tắt cấu hình thuật toán hiện tại
        """
        primary_algo = self.current_config["primary_algorithm"]
        backup_algo = self.current_config["backup_algorithm"]
        
        primary_info = AVAILABLE_ALGORITHMS[primary_algo]
        backup_info = AVAILABLE_ALGORITHMS[backup_algo]
        
        enabled_algos = [algo for algo, config in self.current_config["algorithms"].items() if config["enabled"]]
        
        summary = f"""
        === THÔNG TIN CẤU HÌNH THUẬT TOÁN ===
        
        Thuật toán chính: {primary_info['name']}
        {primary_info['description']}
        
        Thuật toán dự phòng: {backup_info['name']}
        {backup_info['description']}
        
        Số thuật toán đã kích hoạt: {len(enabled_algos)} / {len(AVAILABLE_ALGORITHMS)}
        Thuật toán kích hoạt: {', '.join(enabled_algos)}
        
        Thời gian cập nhật cuối: {self.current_config.get('last_updated', 'Chưa có')}
        """
        
        return summary
    
    def reset_to_default(self) -> bool:
        """
        Đặt lại cấu hình về mặc định
        
        Returns:
            bool: True nếu đặt lại thành công
        """
        self.current_config = self._load_or_create_default()
        return True

def get_current_timestamp() -> str:
    """
    Lấy thời gian hiện tại dạng chuỗi
    
    Returns:
        str: Thời gian hiện tại dạng chuỗi
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    """Hàm chính để test TradingAlgorithmSelector"""
    selector = TradingAlgorithmSelector()
    
    print("===== CẤU HÌNH THUẬT TOÁN GIAO DỊCH =====")
    print()
    
    # Hiển thị tóm tắt cấu hình hiện tại
    print(selector.get_current_summary())
    print()
    
    # Hiển thị menu chính
    print("MENU CHÍNH:")
    print("1. Xem danh sách thuật toán có sẵn")
    print("2. Chọn thuật toán chính")
    print("3. Chọn thuật toán dự phòng")
    print("4. Cấu hình tham số thuật toán")
    print("5. Bật/tắt thuật toán")
    print("6. Đặt lại cấu hình mặc định")
    print("0. Thoát")
    print()
    
    choice = input("Nhập lựa chọn của bạn (0-6): ")
    
    if choice == "1":
        # Hiển thị danh sách thuật toán
        print("\nDanh sách thuật toán có sẵn:")
        for i, (algo_name, algo_info) in enumerate(AVAILABLE_ALGORITHMS.items(), 1):
            print(f"{i}. {algo_info['name']}")
            print(f"   {algo_info['description']}")
            print(f"   Độ phức tạp: {algo_info['complexity']}, Loại: {algo_info['category']}")
            print()
    
    elif choice == "2":
        # Chọn thuật toán chính
        print("\nChọn thuật toán chính:")
        for i, (algo_name, algo_info) in enumerate(AVAILABLE_ALGORITHMS.items(), 1):
            print(f"{i}. {algo_info['name']}")
        
        algo_choice = input("Nhập lựa chọn của bạn (1-8): ")
        try:
            idx = int(algo_choice) - 1
            if 0 <= idx < len(AVAILABLE_ALGORITHMS):
                algo_name = list(AVAILABLE_ALGORITHMS.keys())[idx]
                if selector.set_primary_algorithm(algo_name):
                    print(f"Đã đặt thuật toán chính: {AVAILABLE_ALGORITHMS[algo_name]['name']}")
                else:
                    print("Lỗi khi đặt thuật toán chính.")
            else:
                print("Lựa chọn không hợp lệ.")
        except ValueError:
            print("Vui lòng nhập một số.")
    
    elif choice == "3":
        # Chọn thuật toán dự phòng
        print("\nChọn thuật toán dự phòng:")
        for i, (algo_name, algo_info) in enumerate(AVAILABLE_ALGORITHMS.items(), 1):
            print(f"{i}. {algo_info['name']}")
        
        algo_choice = input("Nhập lựa chọn của bạn (1-8): ")
        try:
            idx = int(algo_choice) - 1
            if 0 <= idx < len(AVAILABLE_ALGORITHMS):
                algo_name = list(AVAILABLE_ALGORITHMS.keys())[idx]
                if selector.set_backup_algorithm(algo_name):
                    print(f"Đã đặt thuật toán dự phòng: {AVAILABLE_ALGORITHMS[algo_name]['name']}")
                else:
                    print("Lỗi khi đặt thuật toán dự phòng.")
            else:
                print("Lựa chọn không hợp lệ.")
        except ValueError:
            print("Vui lòng nhập một số.")
    
    elif choice == "4":
        # Cấu hình tham số thuật toán
        print("\nChọn thuật toán để cấu hình:")
        for i, (algo_name, algo_info) in enumerate(AVAILABLE_ALGORITHMS.items(), 1):
            print(f"{i}. {algo_info['name']}")
        
        algo_choice = input("Nhập lựa chọn của bạn (1-8): ")
        try:
            idx = int(algo_choice) - 1
            if 0 <= idx < len(AVAILABLE_ALGORITHMS):
                algo_name = list(AVAILABLE_ALGORITHMS.keys())[idx]
                print(f"\nCấu hình tham số cho {AVAILABLE_ALGORITHMS[algo_name]['name']}:")
                
                # Hiển thị chi tiết thuật toán
                print(selector.get_algorithm_summary(algo_name))
                
                # Hỏi người dùng có muốn đặt lại tham số về mặc định không
                reset = input("\nBạn có muốn đặt lại tham số về mặc định không? (y/n): ")
                if reset.lower() == 'y':
                    if selector.reset_algorithm_parameters(algo_name):
                        print("Đã đặt lại tham số về mặc định.")
                    else:
                        print("Lỗi khi đặt lại tham số.")
                else:
                    # Cập nhật tham số
                    print("\nNhập tham số mới (Enter để giữ nguyên):")
                    new_params = {}
                    
                    for param_name, param_info in AVAILABLE_ALGORITHMS[algo_name]["parameters"].items():
                        current_value = selector.current_config["algorithms"][algo_name]["parameters"].get(param_name, param_info["default"])
                        
                        if param_info["type"] in ["int", "float"]:
                            input_value = input(f"  {param_name} ({param_info['description']}, hiện tại: {current_value}): ")
                            if input_value:
                                try:
                                    if param_info["type"] == "int":
                                        value = int(input_value)
                                    else:
                                        value = float(input_value)
                                        
                                    new_params[param_name] = value
                                except ValueError:
                                    print(f"  Giá trị không hợp lệ cho {param_name}, giữ nguyên.")
                        
                        elif param_info["type"] == "bool":
                            input_value = input(f"  {param_name} ({param_info['description']}, hiện tại: {current_value}): ")
                            if input_value.lower() in ['true', 'yes', 'y', '1']:
                                new_params[param_name] = True
                            elif input_value.lower() in ['false', 'no', 'n', '0']:
                                new_params[param_name] = False
                                
                        elif param_info["type"] == "enum":
                            print(f"  {param_name} ({param_info['description']}, hiện tại: {current_value}):")
                            for i, option in enumerate(param_info["options"], 1):
                                print(f"    {i}. {option}")
                                
                            input_value = input("  Lựa chọn: ")
                            if input_value:
                                try:
                                    idx = int(input_value) - 1
                                    if 0 <= idx < len(param_info["options"]):
                                        new_params[param_name] = param_info["options"][idx]
                                except ValueError:
                                    print(f"  Giá trị không hợp lệ cho {param_name}, giữ nguyên.")
                    
                    if new_params:
                        if selector.update_algorithm_parameters(algo_name, new_params):
                            print("Đã cập nhật tham số.")
                        else:
                            print("Lỗi khi cập nhật tham số.")
                    else:
                        print("Không có tham số nào được thay đổi.")
            else:
                print("Lựa chọn không hợp lệ.")
        except ValueError:
            print("Vui lòng nhập một số.")
    
    elif choice == "5":
        # Bật/tắt thuật toán
        print("\nChọn thuật toán để bật/tắt:")
        for i, (algo_name, algo_info) in enumerate(AVAILABLE_ALGORITHMS.items(), 1):
            enabled = selector.current_config["algorithms"][algo_name]["enabled"]
            print(f"{i}. {algo_info['name']} - {'Kích hoạt' if enabled else 'Không kích hoạt'}")
        
        algo_choice = input("Nhập lựa chọn của bạn (1-8): ")
        try:
            idx = int(algo_choice) - 1
            if 0 <= idx < len(AVAILABLE_ALGORITHMS):
                algo_name = list(AVAILABLE_ALGORITHMS.keys())[idx]
                current_status = selector.current_config["algorithms"][algo_name]["enabled"]
                
                toggle = input(f"{'Tắt' if current_status else 'Bật'} thuật toán {AVAILABLE_ALGORITHMS[algo_name]['name']}? (y/n): ")
                if toggle.lower() == 'y':
                    if selector.enable_algorithm(algo_name, not current_status):
                        print(f"Đã {'tắt' if current_status else 'bật'} thuật toán {AVAILABLE_ALGORITHMS[algo_name]['name']}.")
                    else:
                        print(f"Lỗi khi {'tắt' if current_status else 'bật'} thuật toán.")
            else:
                print("Lựa chọn không hợp lệ.")
        except ValueError:
            print("Vui lòng nhập một số.")
    
    elif choice == "6":
        # Đặt lại cấu hình mặc định
        confirm = input("Bạn có chắc chắn muốn đặt lại cấu hình về mặc định? (y/n): ")
        if confirm.lower() == 'y':
            if selector.reset_to_default():
                print("Đã đặt lại cấu hình về mặc định.")
            else:
                print("Lỗi khi đặt lại cấu hình.")
    
    elif choice == "0":
        print("Thoát khỏi chương trình.")
    
    else:
        print("Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()