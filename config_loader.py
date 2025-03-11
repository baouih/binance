#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tải và lưu cấu hình
"""

import os
import json
import logging
import traceback

# Cấu hình logging
logger = logging.getLogger("config_loader")

def load_config(config_file, default_config=None):
    """
    Tải cấu hình từ file JSON
    
    :param config_file: Đường dẫn đến file cấu hình
    :param default_config: Cấu hình mặc định nếu không tìm thấy file
    :return: Dict cấu hình
    """
    if default_config is None:
        default_config = {}
    
    try:
        if not os.path.exists(config_file):
            logger.warning(f"Không tìm thấy file cấu hình {config_file}, sử dụng cấu hình mặc định")
            return default_config
        
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {config_file}")
            return config
    
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi định dạng JSON trong file {config_file}: {str(e)}")
        return default_config
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình từ {config_file}: {str(e)}")
        logger.error(traceback.format_exc())
        return default_config

def save_config(config, config_file):
    """
    Lưu cấu hình vào file JSON
    
    :param config: Dict cấu hình
    :param config_file: Đường dẫn đến file lưu cấu hình
    :return: Boolean thành công/thất bại
    """
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
            logger.info(f"Đã lưu cấu hình vào {config_file}")
            return True
    
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình vào {config_file}: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def load_account_config(filepath="account_config.json"):
    """
    Tải cấu hình tài khoản
    
    :param filepath: Đường dẫn đến file cấu hình tài khoản
    :return: Dict cấu hình tài khoản
    """
    default_config = {
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"],
        "timeframes": ["15m", "1h", "4h", "1d"],
        "strategy": "combined",
        "leverage": 3,
        "max_positions": 3,
        "risk_level": 20,
        "enable_telegram": True,
        "auto_sltp": True
    }
    
    return load_config(filepath, default_config)

def save_account_config(config, filepath="account_config.json"):
    """
    Lưu cấu hình tài khoản
    
    :param config: Dict cấu hình tài khoản
    :param filepath: Đường dẫn đến file lưu cấu hình tài khoản
    :return: Boolean thành công/thất bại
    """
    return save_config(config, filepath)

def load_risk_config(risk_level=10):
    """
    Tải cấu hình rủi ro
    
    :param risk_level: Mức độ rủi ro (10, 15, 20, 30)
    :return: Dict cấu hình rủi ro
    """
    filepath = f"risk_configs/risk_level_{risk_level}.json"
    
    # Cấu hình mặc định cho mức rủi ro
    default_configs = {
        10: {
            "position_size_percent": 1,
            "stop_loss_percent": 1,
            "take_profit_percent": 2,
            "leverage": 1,
            "max_open_positions": 2,
            "max_daily_trades": 5,
            "risk_multipliers": {
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.0
            }
        },
        15: {
            "position_size_percent": 2,
            "stop_loss_percent": 1.5,
            "take_profit_percent": 3,
            "leverage": 2,
            "max_open_positions": 3,
            "max_daily_trades": 8,
            "risk_multipliers": {
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.0
            }
        },
        20: {
            "position_size_percent": 3,
            "stop_loss_percent": 2,
            "take_profit_percent": 4,
            "leverage": 3,
            "max_open_positions": 4,
            "max_daily_trades": 12,
            "risk_multipliers": {
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.0
            }
        },
        30: {
            "position_size_percent": 5,
            "stop_loss_percent": 3,
            "take_profit_percent": 6,
            "leverage": 5,
            "max_open_positions": 5,
            "max_daily_trades": 20,
            "risk_multipliers": {
                "stop_loss_multiplier": 1.0,
                "take_profit_multiplier": 1.0
            }
        }
    }
    
    # Sử dụng cấu hình mặc định phù hợp với mức rủi ro
    default_config = default_configs.get(risk_level, default_configs[10])
    
    return load_config(filepath, default_config)

def load_telegram_config(filepath="configs/telegram_config.json"):
    """
    Tải cấu hình Telegram
    
    :param filepath: Đường dẫn đến file cấu hình Telegram
    :return: Dict cấu hình Telegram
    """
    default_config = {
        "notification_settings": {
            "enable_trade_signals": True,
            "enable_price_alerts": True,
            "enable_position_updates": True,
            "enable_sltp_alerts": True,
            "min_price_change_percent": 3.0,
            "price_alert_cooldown": 3600,
            "position_update_interval": 3600,
            "max_notifications_per_hour": 20,
            "quiet_hours_start": 0,
            "quiet_hours_end": 0
        },
        "templates": {
            "trade_signal": "🚨 TÍN HIỆU GIAO DỊCH MỚI 🚨\n\nCặp: {symbol}\nHướng: {side_emoji} {side}\nGiá vào lệnh: {entry_price:.2f}\nStop Loss: {stop_loss:.2f}\nTake Profit: {take_profit:.2f}\nRisk/Reward: 1:{risk_reward:.2f}\nKhung thời gian: {timeframe}\nChiến lược: {strategy}\n{confidence_info}\n\n💡 Đặt SL/TP theo mức được gợi ý để đảm bảo quản lý vốn!",
            "price_alert": "{emoji} CẢNH BÁO GIÁ {symbol} {emoji}\n\nGiá hiện tại: {price}\nThay đổi: {change_prefix}{change_percent:.2f}%\nKhung thời gian: {timeframe}\n{reason}\n\nCảnh báo này dựa trên các thay đổi đáng kể về giá.",
            "position_update": "📊 CẬP NHẬT VỊ THẾ\n\nVị thế đang mở: {num_positions}\n\n{positions_info}\n\nSố dư tài khoản: {account_balance:.2f} USDT\nTổng vị thế: {total_position_value:.2f} USDT\nTỷ lệ margin: {margin_percent:.2f}%\n{pnl_info}",
            "sltp_update": "🔄 CẬP NHẬT SL/TP 🔄\n\nCặp: {symbol}\nHướng: {side_emoji} {side}\n{sl_info}\n{tp_info}\n{reason}\n\nHệ thống đã tự động điều chỉnh mức SL/TP.",
            "system_status": "🤖 BÁO CÁO TRẠNG THÁI HỆ THỐNG\n\n⏱️ Thời gian hoạt động: {uptime_str}\n💰 Số dư tài khoản: {account_balance:.2f} USDT\n📊 Vị thế đang mở: {open_positions}\n🔄 Giao dịch hôm nay: {daily_trades}\n{pnl_info}\n{system_load_info}\n\n🕒 Thời gian báo cáo: {timestamp}"
        },
        "emoji": {
            "long": "🟢",
            "short": "🔴",
            "price_up": "📈",
            "price_down": "📉",
            "profit": "📈",
            "loss": "📉",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
    }
    
    return load_config(filepath, default_config)

if __name__ == "__main__":
    # Cấu hình logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test load và save cấu hình
    account_config = load_account_config()
    print("Account config:", account_config)
    
    risk_config = load_risk_config(20)
    print("Risk config:", risk_config)
    
    telegram_config = load_telegram_config()
    print("Telegram config:", telegram_config)