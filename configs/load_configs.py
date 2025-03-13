#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module để tải cấu hình từ các file config
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("configs.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("configs")

def load_api_config() -> Dict[str, Any]:
    """
    Tải cấu hình API
    
    :return: Dict chứa cấu hình API
    """
    config_file = "configs/api_config.json"
    
    # Kiểm tra tồn tại của file cấu hình
    if not os.path.exists(config_file):
        logger.warning(f"Không tìm thấy file cấu hình API: {config_file}")
        return {}
    
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            logger.info(f"Đã tải cấu hình API từ {config_file}")
            
            # Lưu vào biến môi trường
            if "api_key" in config:
                os.environ["BINANCE_TESTNET_API_KEY"] = config["api_key"]
            if "api_secret" in config:
                os.environ["BINANCE_TESTNET_API_SECRET"] = config["api_secret"]
                
            return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình API: {str(e)}")
        return {}

def load_telegram_config() -> Dict[str, Any]:
    """
    Tải cấu hình Telegram
    
    :return: Dict chứa cấu hình Telegram
    """
    config_file = "configs/telegram_config.json"
    
    # Kiểm tra tồn tại của file cấu hình
    if not os.path.exists(config_file):
        logger.warning(f"Không tìm thấy file cấu hình Telegram: {config_file}")
        return {}
    
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            logger.info(f"Đã tải cấu hình Telegram từ {config_file}")
            
            # Lưu vào biến môi trường
            if "bot_token" in config:
                os.environ["TELEGRAM_BOT_TOKEN"] = config["bot_token"]
            if "chat_id" in config:
                os.environ["TELEGRAM_CHAT_ID"] = config["chat_id"]
                
            return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình Telegram: {str(e)}")
        return {}

def load_risk_config(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Tải cấu hình rủi ro
    
    :param file_path: Đường dẫn đến file cấu hình rủi ro, mặc định sẽ tìm trong risk_configs/
    :return: Dict chứa cấu hình rủi ro
    """
    if file_path is None:
        # Ưu tiên cấu hình desktop trước
        if os.path.exists("risk_configs/desktop_risk_config.json"):
            file_path = "risk_configs/desktop_risk_config.json"
        else:
            # Tìm file cấu hình trong thư mục risk_configs
            risk_configs_dir = "risk_configs"
            if os.path.exists(risk_configs_dir):
                config_files = [f for f in os.listdir(risk_configs_dir) if f.endswith(".json")]
                if config_files:
                    file_path = os.path.join(risk_configs_dir, config_files[0])
    
    # Nếu không tìm thấy file cấu hình
    if file_path is None or not os.path.exists(file_path):
        logger.warning("Không tìm thấy file cấu hình rủi ro")
        return {}
    
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
            logger.info(f"Đã tải cấu hình rủi ro từ {file_path}")
            return config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}")
        return {}

def load_ui_settings() -> Dict[str, Any]:
    """
    Tải cài đặt giao diện từ QSettings
    
    :return: Dict chứa cài đặt giao diện
    """
    try:
        from PyQt5.QtCore import QSettings
        
        settings = QSettings("TradingBot", "Desktop")
        
        ui_settings = {
            "dark_mode": settings.value("dark_mode", True, type=bool),
            "refresh_interval": settings.value("refresh_interval", 5, type=int),
            "notifications": settings.value("notifications", True, type=bool)
        }
        
        logger.info("Đã tải cài đặt giao diện")
        return ui_settings
    except Exception as e:
        logger.error(f"Lỗi khi tải cài đặt giao diện: {str(e)}")
        return {
            "dark_mode": True,
            "refresh_interval": 5,
            "notifications": True
        }

def load_all_configs() -> Dict[str, Dict[str, Any]]:
    """
    Tải tất cả các cấu hình
    
    :return: Dict chứa tất cả các cấu hình
    """
    return {
        "api": load_api_config(),
        "telegram": load_telegram_config(),
        "risk": load_risk_config(),
        "ui": load_ui_settings()
    }

def verify_configs() -> Dict[str, bool]:
    """
    Kiểm tra tính hợp lệ của các cấu hình
    
    :return: Dict trạng thái hợp lệ của các cấu hình
    """
    configs = load_all_configs()
    
    return {
        "api": bool(configs["api"].get("api_key") and configs["api"].get("api_secret")),
        "telegram": bool(configs["telegram"].get("bot_token") and configs["telegram"].get("chat_id")),
        "risk": bool(configs["risk"])
    }

def get_config_status_text() -> Dict[str, str]:
    """
    Lấy trạng thái của các cấu hình dưới dạng text
    
    :return: Dict chứa trạng thái của các cấu hình
    """
    status = verify_configs()
    
    return {
        "api": "✅ Đã cấu hình" if status["api"] else "❌ Chưa cấu hình",
        "telegram": "✅ Đã cấu hình" if status["telegram"] else "❌ Chưa cấu hình",
        "risk": "✅ Đã cấu hình" if status["risk"] else "❌ Chưa cấu hình"
    }

if __name__ == "__main__":
    print("Đang kiểm tra cấu hình...")
    configs = load_all_configs()
    status = verify_configs()
    
    print("\n=== TRẠNG THÁI CẤU HÌNH ===")
    for key, value in status.items():
        print(f"{key.upper()}: {'✅ Đã cấu hình' if value else '❌ Chưa cấu hình'}")