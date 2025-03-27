"""
Mô-đun quản lý rủi ro tùy chỉnh theo coin
----------------------------------------
Điều chỉnh các tham số rủi ro dựa trên đặc tính biến động và lịch sử hiệu suất của từng coin
"""

import os
import sys
import json
import logging
import datetime
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

# Thiết lập logging
logger = logging.getLogger("coin_specific_risk")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Thông tin coin và đặc điểm rủi ro của chúng
COIN_RISK_PROFILES = {
    "BTC": {
        "volatility_factor": 1.0,  # Tiêu chuẩn so sánh
        "sideways_performance": "excellent",  # Hiệu suất trong thị trường đi ngang
        "trending_performance": "excellent",  # Hiệu suất trong thị trường xu hướng
        "risk_adjustment": 0.0,  # Không điều chỉnh, mức rủi ro chuẩn
        "sl_adjustment": 0.0,  # Không điều chỉnh mức stop loss
        "tp_adjustment": 0.0,  # Không điều chỉnh mức take profit
        "safe_leverage": 20,  # Đòn bẩy an toàn tối đa
        "high_risk_compatible": True,  # Tương thích với mức rủi ro cao
        "extremely_high_risk_compatible": True,  # Tương thích với mức rủi ro cực cao
        "small_account_compatible": True,  # Tương thích với tài khoản nhỏ
        "recommended_timeframes": ["1h", "4h", "1d"],  # Khung thời gian đề xuất
        "recommended_strategies": ["AdaptiveStrategy", "MACrossoverStrategy", "BollingerBandsStrategy"]
    },
    "ETH": {
        "volatility_factor": 1.3,  # Biến động cao hơn BTC 30%
        "sideways_performance": "good",
        "trending_performance": "excellent",
        "risk_adjustment": -0.1,  # Giảm 10% mức rủi ro mặc định
        "sl_adjustment": 0.2,  # Tăng 20% khoảng cách stop loss
        "tp_adjustment": 0.0,
        "safe_leverage": 15,
        "high_risk_compatible": True,
        "extremely_high_risk_compatible": False,  # Không tương thích với mức rủi ro cực cao
        "small_account_compatible": True,
        "recommended_timeframes": ["1h", "4h"],
        "recommended_strategies": ["MACrossoverStrategy", "BollingerBandsStrategy"]
    },
    "BNB": {
        "volatility_factor": 1.4,
        "sideways_performance": "moderate",
        "trending_performance": "good",
        "risk_adjustment": -0.15,
        "sl_adjustment": 0.25,
        "tp_adjustment": 0.1,
        "safe_leverage": 10,
        "high_risk_compatible": True,
        "extremely_high_risk_compatible": False,
        "small_account_compatible": False,
        "recommended_timeframes": ["4h", "1d"],
        "recommended_strategies": ["MACrossoverStrategy", "SuperTrendStrategy"]
    },
    "SOL": {
        "volatility_factor": 1.8,
        "sideways_performance": "poor",
        "trending_performance": "excellent",
        "risk_adjustment": -0.25,
        "sl_adjustment": 0.3,
        "tp_adjustment": 0.2,
        "safe_leverage": 8,
        "high_risk_compatible": True,
        "extremely_high_risk_compatible": False,
        "small_account_compatible": False,
        "recommended_timeframes": ["4h", "1d"],
        "recommended_strategies": ["SuperTrendStrategy", "RSIDivergenceStrategy"]
    },
    "DOGE": {
        "volatility_factor": 2.5,
        "sideways_performance": "poor",
        "trending_performance": "moderate",
        "risk_adjustment": -0.4,
        "sl_adjustment": 0.5,
        "tp_adjustment": 0.3,
        "safe_leverage": 5,
        "high_risk_compatible": False,
        "extremely_high_risk_compatible": False,
        "small_account_compatible": False,
        "recommended_timeframes": ["4h", "1d"],
        "recommended_strategies": ["BollingerBandsStrategy", "SuperTrendStrategy"]
    },
    "XRP": {
        "volatility_factor": 1.7,
        "sideways_performance": "moderate",
        "trending_performance": "good",
        "risk_adjustment": -0.2,
        "sl_adjustment": 0.3,
        "tp_adjustment": 0.1,
        "safe_leverage": 8,
        "high_risk_compatible": True,
        "extremely_high_risk_compatible": False,
        "small_account_compatible": False,
        "recommended_timeframes": ["4h", "1d"],
        "recommended_strategies": ["MACrossoverStrategy", "SuperTrendStrategy"]
    }
}

# Mặc định cho các coin chưa được định nghĩa
DEFAULT_RISK_PROFILE = {
    "volatility_factor": 2.0,
    "sideways_performance": "unknown",
    "trending_performance": "unknown",
    "risk_adjustment": -0.3,
    "sl_adjustment": 0.4,
    "tp_adjustment": 0.2,
    "safe_leverage": 5,
    "high_risk_compatible": False,
    "extremely_high_risk_compatible": False,
    "small_account_compatible": False,
    "recommended_timeframes": ["4h", "1d"],
    "recommended_strategies": ["MACrossoverStrategy"]
}

def normalize_symbol(symbol: str) -> str:
    """
    Chuẩn hóa ký hiệu coin (loại bỏ USDT/BUSD và viết hoa)
    
    :param symbol: Ký hiệu coin cần chuẩn hóa
    :return: Ký hiệu đã chuẩn hóa
    """
    symbol = symbol.upper()
    for suffix in ["USDT", "BUSD", "USD", "USDC"]:
        if symbol.endswith(suffix):
            symbol = symbol[:-len(suffix)]
    return symbol

def get_coin_risk_profile(symbol: str) -> Dict[str, Any]:
    """
    Lấy thông tin rủi ro của coin
    
    :param symbol: Ký hiệu coin
    :return: Thông tin rủi ro
    """
    normalized_symbol = normalize_symbol(symbol)
    if normalized_symbol in COIN_RISK_PROFILES:
        return COIN_RISK_PROFILES[normalized_symbol]
    return DEFAULT_RISK_PROFILE.copy()

def adjust_risk_params_for_coin(base_risk_config: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    Điều chỉnh các tham số rủi ro dựa trên đặc tính của coin
    
    :param base_risk_config: Cấu hình rủi ro cơ bản
    :param symbol: Ký hiệu coin
    :return: Cấu hình rủi ro được điều chỉnh
    """
    # Tạo bản sao cấu hình cơ bản
    adjusted_config = base_risk_config.copy()
    
    # Lấy thông tin rủi ro của coin
    coin_profile = get_coin_risk_profile(symbol)
    
    # Điều chỉnh mức rủi ro cho từng giao dịch
    base_risk = adjusted_config.get("risk_per_trade", 5.0)
    risk_adjustment = coin_profile["risk_adjustment"]
    adjusted_risk = base_risk * (1 + risk_adjustment)
    adjusted_config["risk_per_trade"] = max(1.0, adjusted_risk)  # Tối thiểu 1%
    
    # Điều chỉnh đòn bẩy
    base_leverage = adjusted_config.get("max_leverage", 10)
    adjusted_leverage = min(base_leverage, coin_profile["safe_leverage"])
    adjusted_config["max_leverage"] = adjusted_leverage
    
    # Điều chỉnh Stop Loss và Take Profit
    base_sl = adjusted_config.get("stop_loss_atr_multiplier", 1.0)
    base_tp = adjusted_config.get("take_profit_atr_multiplier", 2.0)
    
    adjusted_sl = base_sl * (1 + coin_profile["sl_adjustment"])
    adjusted_tp = base_tp * (1 + coin_profile["tp_adjustment"])
    
    adjusted_config["stop_loss_atr_multiplier"] = adjusted_sl
    adjusted_config["take_profit_atr_multiplier"] = adjusted_tp
    
    # Thêm thông tin về coin vào cấu hình
    adjusted_config["coin_info"] = {
        "symbol": symbol,
        "normalized_symbol": normalize_symbol(symbol),
        "volatility_factor": coin_profile["volatility_factor"],
        "sideways_performance": coin_profile["sideways_performance"],
        "trending_performance": coin_profile["trending_performance"],
        "recommended_timeframes": coin_profile["recommended_timeframes"],
        "recommended_strategies": coin_profile["recommended_strategies"]
    }
    
    # Kiểm tra tương thích với mức rủi ro
    risk_level = base_risk_config.get("risk_level", "medium")
    if risk_level == "high" and not coin_profile["high_risk_compatible"]:
        logger.warning(f"Coin {symbol} không tương thích với mức rủi ro cao. Đã giảm rủi ro tự động.")
        adjusted_config["risk_per_trade"] = min(adjusted_config["risk_per_trade"], 5.0)
        adjusted_config["max_leverage"] = min(adjusted_config["max_leverage"], 5)
    
    if risk_level == "extremely_high" and not coin_profile["extremely_high_risk_compatible"]:
        logger.warning(f"Coin {symbol} không tương thích với mức rủi ro cực cao. Đã giảm rủi ro tự động.")
        adjusted_config["risk_per_trade"] = min(adjusted_config["risk_per_trade"], 5.0)
        adjusted_config["max_leverage"] = min(adjusted_config["max_leverage"], 5)
    
    # Kiểm tra tương thích với tài khoản nhỏ
    account_size = base_risk_config.get("account_info", {}).get("balance", 1000)
    if account_size < 500 and not coin_profile["small_account_compatible"]:
        logger.warning(f"Coin {symbol} không phù hợp với tài khoản nhỏ ({account_size}$). Không khuyến nghị giao dịch.")
        adjusted_config["small_account_warning"] = True
    
    return adjusted_config

def get_optimized_coins_for_account(account_balance: float, risk_level: str) -> List[Dict[str, Any]]:
    """
    Lấy danh sách coin được tối ưu hóa cho kích thước tài khoản và mức rủi ro
    
    :param account_balance: Số dư tài khoản
    :param risk_level: Mức rủi ro (extremely_low, low, medium, high, extremely_high)
    :return: Danh sách thông tin coin được tối ưu hóa
    """
    optimized_coins = []
    
    for symbol, profile in COIN_RISK_PROFILES.items():
        # Kiểm tra tương thích với tài khoản nhỏ
        if account_balance < 500 and not profile["small_account_compatible"]:
            continue
        
        # Kiểm tra tương thích với mức rủi ro
        if risk_level == "high" and not profile["high_risk_compatible"]:
            continue
        
        if risk_level == "extremely_high" and not profile["extremely_high_risk_compatible"]:
            continue
        
        # Tính điểm tối ưu
        optimization_score = 0
        
        # Với tài khoản nhỏ, ưu tiên coin ít biến động
        if account_balance < 500:
            optimization_score = 10 - profile["volatility_factor"] * 2
        # Với tài khoản trung bình, cân bằng
        elif account_balance < 5000:
            if risk_level in ["high", "extremely_high"]:
                # Với rủi ro cao, ưu tiên coin có hiệu suất tốt trong xu hướng
                if profile["trending_performance"] == "excellent":
                    optimization_score = 10
                elif profile["trending_performance"] == "good":
                    optimization_score = 8
                else:
                    optimization_score = 5
            else:
                # Với rủi ro thấp/trung bình, ưu tiên coin ổn định
                if profile["sideways_performance"] == "excellent":
                    optimization_score = 10
                elif profile["sideways_performance"] == "good":
                    optimization_score = 8
                else:
                    optimization_score = 5
        # Với tài khoản lớn, ưu tiên đa dạng hóa
        else:
            optimization_score = 7  # Điểm cơ bản cho tất cả coin
        
        # Thêm vào danh sách
        optimized_coins.append({
            "symbol": symbol,
            "optimization_score": optimization_score,
            "volatility_factor": profile["volatility_factor"],
            "sideways_performance": profile["sideways_performance"],
            "trending_performance": profile["trending_performance"],
            "recommended_timeframes": profile["recommended_timeframes"],
            "recommended_strategies": profile["recommended_strategies"]
        })
    
    # Sắp xếp theo điểm tối ưu giảm dần
    optimized_coins.sort(key=lambda x: x["optimization_score"], reverse=True)
    
    return optimized_coins

def create_coin_specific_config(symbol: str, base_risk_level: str = "medium", account_balance: float = 1000, save_file: bool = False) -> Dict[str, Any]:
    """
    Tạo cấu hình rủi ro tùy chỉnh cho coin cụ thể
    
    :param symbol: Ký hiệu coin
    :param base_risk_level: Mức rủi ro cơ bản
    :param account_balance: Số dư tài khoản
    :param save_file: Có lưu tệp cấu hình hay không
    :return: Cấu hình rủi ro được tùy chỉnh
    """
    # Tạo cấu hình cơ bản dựa trên mức rủi ro
    if base_risk_level == "extremely_low":
        base_config = {
            "risk_level": "extremely_low",
            "risk_per_trade": 1.0,
            "max_leverage": 2,
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_atr_multiplier": 6.0
        }
    elif base_risk_level == "low":
        base_config = {
            "risk_level": "low",
            "risk_per_trade": 2.5,
            "max_leverage": 3,
            "stop_loss_atr_multiplier": 1.5,
            "take_profit_atr_multiplier": 4.0
        }
    elif base_risk_level == "medium":
        base_config = {
            "risk_level": "medium",
            "risk_per_trade": 5.0,
            "max_leverage": 5,
            "stop_loss_atr_multiplier": 1.2,
            "take_profit_atr_multiplier": 3.0
        }
    elif base_risk_level == "high":
        base_config = {
            "risk_level": "high",
            "risk_per_trade": 10.0,
            "max_leverage": 10,
            "stop_loss_atr_multiplier": 1.0,
            "take_profit_atr_multiplier": 2.0
        }
    elif base_risk_level == "extremely_high":
        base_config = {
            "risk_level": "extremely_high",
            "risk_per_trade": 25.0,
            "max_leverage": 20,
            "stop_loss_atr_multiplier": 0.7,
            "take_profit_atr_multiplier": 1.5
        }
    else:
        # Mặc định medium
        base_config = {
            "risk_level": "medium",
            "risk_per_trade": 5.0,
            "max_leverage": 5,
            "stop_loss_atr_multiplier": 1.2,
            "take_profit_atr_multiplier": 3.0
        }
    
    # Thêm thông tin tài khoản
    base_config["account_info"] = {
        "balance": account_balance
    }
    
    # Điều chỉnh cấu hình dựa trên đặc tính của coin
    adjusted_config = adjust_risk_params_for_coin(base_config, symbol)
    
    # Lưu cấu hình vào tệp nếu được yêu cầu
    if save_file:
        try:
            normalized_symbol = normalize_symbol(symbol)
            os.makedirs("risk_configs", exist_ok=True)
            file_path = f"risk_configs/{normalized_symbol}_risk_config.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(adjusted_config, f, indent=4)
            logger.info(f"Đã lưu cấu hình rủi ro cho {symbol} vào {file_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}")
    
    return adjusted_config

def main():
    """Hàm chính để chạy thử"""
    
    # Test với BTC và các mức rủi ro khác nhau
    for risk_level in ["medium", "high", "extremely_high"]:
        btc_config = create_coin_specific_config("BTCUSDT", risk_level, account_balance=1000, save_file=True)
        logger.info(f"Cấu hình BTC với mức rủi ro {risk_level}:")
        logger.info(f"  - Rủi ro mỗi giao dịch: {btc_config['risk_per_trade']}%")
        logger.info(f"  - Đòn bẩy: {btc_config['max_leverage']}x")
        logger.info(f"  - Stop Loss ATR: {btc_config['stop_loss_atr_multiplier']}")
        logger.info(f"  - Take Profit ATR: {btc_config['take_profit_atr_multiplier']}")
        logger.info("-" * 50)
    
    # Test với ETH và các mức rủi ro khác nhau
    for risk_level in ["medium", "high", "extremely_high"]:
        eth_config = create_coin_specific_config("ETHUSDT", risk_level, account_balance=1000, save_file=True)
        logger.info(f"Cấu hình ETH với mức rủi ro {risk_level}:")
        logger.info(f"  - Rủi ro mỗi giao dịch: {eth_config['risk_per_trade']}%")
        logger.info(f"  - Đòn bẩy: {eth_config['max_leverage']}x")
        logger.info(f"  - Stop Loss ATR: {eth_config['stop_loss_atr_multiplier']}")
        logger.info(f"  - Take Profit ATR: {eth_config['take_profit_atr_multiplier']}")
        logger.info("-" * 50)
    
    # Test với tài khoản nhỏ
    account_balance = 200
    for risk_level in ["high", "extremely_high"]:
        logger.info(f"Coins tối ưu cho tài khoản {account_balance}$ với mức rủi ro {risk_level}:")
        optimized_coins = get_optimized_coins_for_account(account_balance, risk_level)
        for coin in optimized_coins:
            logger.info(f"  - {coin['symbol']}: Điểm tối ưu = {coin['optimization_score']}, Chiến lược đề xuất = {', '.join(coin['recommended_strategies'])}")
        logger.info("-" * 50)

if __name__ == "__main__":
    main()