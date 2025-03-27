"""
Mô-đun điều chỉnh mức độ rủi ro dựa trên kích thước tài khoản
-----------------------------------------------------------
Cung cấp các hàm tính toán mức độ rủi ro phù hợp dựa trên kích thước tài khoản
và đề xuất các chiến lược phù hợp.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, List, Optional

# Thiết lập logging
logger = logging.getLogger("account_risk_scaling")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Bảng ánh xạ kích thước tài khoản đến mức độ rủi ro tương ứng
ACCOUNT_SIZE_RISK_MAPPING = {
    100: {"recommended_risk_level": "extremely_high", "risk_per_trade": 30.0, "leverage_boost": 1.5, "tp_multiplier": 1.5},
    200: {"recommended_risk_level": "extremely_high", "risk_per_trade": 25.0, "leverage_boost": 1.3, "tp_multiplier": 1.4},
    300: {"recommended_risk_level": "high", "risk_per_trade": 20.0, "leverage_boost": 1.2, "tp_multiplier": 1.3},
    500: {"recommended_risk_level": "high", "risk_per_trade": 15.0, "leverage_boost": 1.1, "tp_multiplier": 1.2},
    1000: {"recommended_risk_level": "medium", "risk_per_trade": 8.0, "leverage_boost": 1.0, "tp_multiplier": 1.1},
    3000: {"recommended_risk_level": "medium", "risk_per_trade": 5.0, "leverage_boost": 0.9, "tp_multiplier": 1.0},
    5000: {"recommended_risk_level": "low", "risk_per_trade": 3.0, "leverage_boost": 0.8, "tp_multiplier": 0.9},
    10000: {"recommended_risk_level": "low", "risk_per_trade": 1.5, "leverage_boost": 0.7, "tp_multiplier": 0.8},
    50000: {"recommended_risk_level": "extremely_low", "risk_per_trade": 0.5, "leverage_boost": 0.5, "tp_multiplier": 0.7}
}

# Mức rủi ro cơ bản
RISK_LEVELS = {
    'extremely_low': {'name': 'Cực kỳ thấp', 'risk_range': (0.5, 1.0), 'default': 1.0, 'leverage_range': (1, 2), 'default_leverage': 2},
    'low': {'name': 'Thấp', 'risk_range': (1.5, 3.0), 'default': 2.5, 'leverage_range': (2, 5), 'default_leverage': 3},
    'medium': {'name': 'Trung bình', 'risk_range': (3.0, 7.0), 'default': 5.0, 'leverage_range': (3, 10), 'default_leverage': 5},
    'high': {'name': 'Cao', 'risk_range': (7.0, 15.0), 'default': 10.0, 'leverage_range': (5, 20), 'default_leverage': 10},
    'extremely_high': {'name': 'Cực kỳ cao', 'risk_range': (15.0, 50.0), 'default': 25.0, 'leverage_range': (10, 50), 'default_leverage': 20}
}

def get_nearest_account_tier(account_balance: float) -> int:
    """
    Lấy mức tài khoản gần nhất từ bảng ánh xạ

    :param account_balance: Số dư tài khoản
    :return: Mức tài khoản gần nhất
    """
    tiers = sorted(ACCOUNT_SIZE_RISK_MAPPING.keys())
    
    # Nếu số dư nhỏ hơn mức thấp nhất, trả về mức thấp nhất
    if account_balance <= tiers[0]:
        return tiers[0]
    
    # Nếu số dư lớn hơn mức cao nhất, trả về mức cao nhất
    if account_balance >= tiers[-1]:
        return tiers[-1]
    
    # Tìm mức phù hợp
    for i in range(len(tiers) - 1):
        if tiers[i] <= account_balance < tiers[i + 1]:
            # Nếu gần hơn với mức cao, trả về mức cao
            if account_balance - tiers[i] > tiers[i + 1] - account_balance:
                return tiers[i + 1]
            return tiers[i]
    
    # Mặc định trả về mức trung bình nếu không tìm thấy
    return 1000

def calculate_adjusted_risk_params(account_balance: float) -> Dict[str, Any]:
    """
    Tính toán các tham số rủi ro được điều chỉnh dựa trên kích thước tài khoản
    
    :param account_balance: Số dư tài khoản
    :return: Tham số rủi ro điều chỉnh
    """
    nearest_tier = get_nearest_account_tier(account_balance)
    risk_params = ACCOUNT_SIZE_RISK_MAPPING[nearest_tier].copy()
    
    # Thêm thông tin về mức tài khoản đã sử dụng
    risk_params["account_tier"] = nearest_tier
    risk_params["account_balance"] = account_balance
    
    # Lấy tham số cơ bản từ mức rủi ro được đề xuất
    base_risk_level = risk_params["recommended_risk_level"]
    base_risk_params = RISK_LEVELS[base_risk_level]
    
    # Áp dụng các tham số cơ bản
    risk_params["base_risk_level"] = base_risk_level
    risk_params["base_leverage"] = base_risk_params["default_leverage"]
    risk_params["leverage"] = min(round(base_risk_params["default_leverage"] * risk_params["leverage_boost"]), 50)
    
    # Điều chỉnh các tham số khác
    if account_balance < 500:
        risk_params["small_account_optimization"] = True
        risk_params["recommended_coins"] = ["BTC", "ETH"]
        risk_params["max_positions"] = 2
    elif account_balance < 1000:
        risk_params["small_account_optimization"] = True
        risk_params["recommended_coins"] = ["BTC", "ETH", "BNB", "SOL"]
        risk_params["max_positions"] = 3
    elif account_balance < 5000:
        risk_params["small_account_optimization"] = False
        risk_params["recommended_coins"] = ["BTC", "ETH", "BNB", "SOL", "DOGE", "XRP", "ADA"]
        risk_params["max_positions"] = 5
    else:
        risk_params["small_account_optimization"] = False
        risk_params["recommended_coins"] = ["BTC", "ETH", "BNB", "SOL", "DOGE", "XRP", "ADA", "DOT", "AVAX", "LINK"]
        risk_params["max_positions"] = 8
    
    return risk_params

def generate_risk_config(account_balance: float, save_file: bool = False) -> Dict[str, Any]:
    """
    Tạo cấu hình rủi ro đầy đủ dựa trên kích thước tài khoản
    
    :param account_balance: Số dư tài khoản
    :param save_file: Có lưu tệp cấu hình hay không
    :return: Cấu hình rủi ro đầy đủ
    """
    risk_params = calculate_adjusted_risk_params(account_balance)
    
    # Tạo cấu hình rủi ro đầy đủ
    risk_config = {
        "risk_level": risk_params["recommended_risk_level"],
        "risk_per_trade": risk_params["risk_per_trade"],
        "max_leverage": risk_params["leverage"],
        "stop_loss_atr_multiplier": 1.0,  # Giá trị mặc định, điều chỉnh dựa trên mức rủi ro
        "take_profit_atr_multiplier": 2.0 * risk_params["tp_multiplier"],
        "trailing_stop": True,
        "trailing_activation_pct": 1.0 if risk_params["risk_per_trade"] < 10 else 0.5,
        "trailing_callback_pct": 0.5 if risk_params["risk_per_trade"] < 10 else 0.3,
        "partial_profit_taking": {
            "enabled": True,
            "levels": [
                {"pct": 1.0, "portion": 0.25},
                {"pct": 2.0, "portion": 0.25},
                {"pct": 3.0, "portion": 0.25},
                {"pct": 5.0, "portion": 0.25}
            ]
        },
        "max_open_risk": min(risk_params["risk_per_trade"] * 5, 100.0),
        "max_positions": risk_params["max_positions"],
        "adaptive_risk": True,
        "market_based_risk": True,
        "account_info": {
            "balance": account_balance,
            "tier": risk_params["account_tier"],
            "small_account_optimization": risk_params["small_account_optimization"],
            "recommended_coins": risk_params["recommended_coins"]
        },
        "warnings": {
            "high_risk": max(risk_params["risk_per_trade"] * 1.0, 10.0),
            "ultra_high_risk": max(risk_params["risk_per_trade"] * 2.0, 20.0)
        }
    }
    
    # Điều chỉnh SL/TP dựa trên mức rủi ro
    if risk_config["risk_level"] == "extremely_low":
        risk_config["stop_loss_atr_multiplier"] = 2.0
        risk_config["take_profit_atr_multiplier"] = 6.0 * risk_params["tp_multiplier"]
    elif risk_config["risk_level"] == "low":
        risk_config["stop_loss_atr_multiplier"] = 1.5
        risk_config["take_profit_atr_multiplier"] = 4.0 * risk_params["tp_multiplier"]
    elif risk_config["risk_level"] == "medium":
        risk_config["stop_loss_atr_multiplier"] = 1.2
        risk_config["take_profit_atr_multiplier"] = 3.0 * risk_params["tp_multiplier"]
    elif risk_config["risk_level"] == "high":
        risk_config["stop_loss_atr_multiplier"] = 1.0
        risk_config["take_profit_atr_multiplier"] = 2.0 * risk_params["tp_multiplier"]
    elif risk_config["risk_level"] == "extremely_high":
        risk_config["stop_loss_atr_multiplier"] = 0.7
        risk_config["take_profit_atr_multiplier"] = 1.5 * risk_params["tp_multiplier"]
    
    # Lưu cấu hình vào tệp nếu được yêu cầu
    if save_file:
        try:
            os.makedirs("risk_configs", exist_ok=True)
            file_path = f"risk_configs/account_{int(account_balance)}_risk_config.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(risk_config, f, indent=4)
            logger.info(f"Đã lưu cấu hình rủi ro cho tài khoản {account_balance} vào {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}")
    
    return risk_config

def main():
    """Hàm chính để chạy thử"""
    
    # Các ví dụ với những kích thước tài khoản khác nhau
    account_sizes = [100, 200, 300, 500, 1000, 3000, 5000, 10000, 50000]
    
    for account_size in account_sizes:
        risk_config = generate_risk_config(account_size, save_file=True)
        logger.info(f"Cấu hình cho tài khoản {account_size}:")
        logger.info(f"  - Mức rủi ro: {risk_config['risk_level']}")
        logger.info(f"  - Rủi ro mỗi giao dịch: {risk_config['risk_per_trade']}%")
        logger.info(f"  - Đòn bẩy: {risk_config['max_leverage']}x")
        logger.info(f"  - Tối đa vị thế: {risk_config['max_positions']}")
        logger.info(f"  - Coin đề xuất: {', '.join(risk_config['account_info']['recommended_coins'])}")
        logger.info("-" * 50)

if __name__ == "__main__":
    main()