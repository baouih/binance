#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chạy ứng dụng desktop giao dịch crypto
"""

import os
import sys
import logging
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='desktop_app.log'
)
logger = logging.getLogger("desktop_app")

try:
    # Import các module chính
    logger.info("Khởi tạo ứng dụng desktop...")
    
    # Tạo thư mục logs nếu chưa tồn tại
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Tạo thư mục data nếu chưa tồn tại
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # Kiểm tra xem tệp cấu hình tồn tại chưa
    if not os.path.exists("account_config.json"):
        # Tạo tệp cấu hình mẫu
        default_config = {
            "risk_level": 10,  # Mức rủi ro mặc định (10%, 15%, 20%, 30%)
            "symbols": ["BTCUSDT", "ETHUSDT"],  # Các cặp tiền mặc định
            "timeframes": ["1h", "4h"],  # Khung thời gian mặc định
            "testnet": True,  # Sử dụng testnet
            "telegram_notifications": True,  # Bật thông báo Telegram
            "quiet_hours": {  # Giờ không làm phiền
                "enabled": False,
                "start": "22:00",
                "end": "07:00"
            },
            "auto_trailing_stop": True,  # Tự động trailing stop
            "language": "vi"  # Ngôn ngữ giao diện
        }
        
        with open("account_config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
    
    # Kiểm tra thư mục configs tồn tại chưa
    if not os.path.exists("configs"):
        os.makedirs("configs")
    
    # Kiểm tra thư mục risk_configs tồn tại chưa
    if not os.path.exists("risk_configs"):
        os.makedirs("risk_configs")
        
        # Tạo các tệp cấu hình rủi ro mẫu
        risk_levels = [10, 15, 20, 30]
        
        for level in risk_levels:
            risk_file = f"risk_configs/risk_level_{level}.json"
            
            if not os.path.exists(risk_file):
                # Tạo cấu hình dựa trên mức độ rủi ro
                risk_config = {
                    "risk_percentage": level / 100,  # Chuyển thành tỷ lệ phần trăm
                    "max_positions": 5 if level <= 15 else (4 if level <= 20 else 3),
                    "leverage": int(level * 0.5) if level <= 20 else int(level * 0.7),  # Đòn bẩy tăng theo mức rủi ro
                    "position_size_percentage": level / 100,
                    "partial_take_profit": {
                        "enabled": level > 15,
                        "levels": [
                            {"percentage": 30, "profit_percentage": 2},
                            {"percentage": 30, "profit_percentage": 5},
                            {"percentage": 40, "profit_percentage": 10}
                        ]
                    },
                    "stop_loss_percentage": level / 100 * 1.5,  # SL tỷ lệ với mức rủi ro
                    "take_profit_percentage": level / 100 * 3,  # TP tỷ lệ với mức rủi ro
                    "trailing_stop": {
                        "enabled": True,
                        "activation_percentage": 2,
                        "trailing_percentage": 1.5
                    },
                    "trading_hours_restriction": {
                        "enabled": level <= 15,  # Chỉ bật cho mức rủi ro thấp
                        "trading_hours": ["09:00-12:00", "14:00-21:00"]
                    }
                }
                
                with open(risk_file, "w", encoding="utf-8") as f:
                    json.dump(risk_config, f, indent=4)
    
    # Kiểm tra telegram_config.json tồn tại chưa
    telegram_config_file = "configs/telegram_config.json"
    if not os.path.exists(telegram_config_file):
        if not os.path.exists("configs"):
            os.makedirs("configs")
        
        # Tạo cấu hình mẫu
        telegram_config = {
            "enabled": True,
            "notification_types": {
                "signals": True,
                "trades": True,
                "position_updates": True,
                "system_status": True,
                "error_alerts": True
            },
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "07:00"
            },
            "formatting": {
                "use_emojis": True,
                "detailed_trade_info": True
            }
        }
        
        with open(telegram_config_file, "w", encoding="utf-8") as f:
            json.dump(telegram_config, f, indent=4)
    
    # Import giao diện người dùng
    from enhanced_trading_gui import TradingApp
    
    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    app.setApplicationName("Crypto Trading Bot")
    
    # Thiết lập biểu tượng nếu có
    icon_path = "static/img/icon.png"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Khởi tạo cửa sổ chính
    window = TradingApp()
    window.show()
    
    # Chạy ứng dụng
    sys.exit(app.exec_())
    
except ImportError as e:
    import_error = str(e)
    print(f"Import lỗi: {import_error}")
    logger.error(f"Import lỗi: {import_error}")
    
    if "talib" in import_error:
        print("Chưa cài đặt thư viện TA-Lib. Vui lòng cài đặt bằng lệnh: pip install ta-lib")
        logger.error("Thiếu thư viện TA-Lib")
    
    if "PyQt5" in import_error:
        print("Chưa cài đặt thư viện PyQt5. Vui lòng cài đặt bằng lệnh: pip install PyQt5")
        logger.error("Thiếu thư viện PyQt5")
    
    sys.exit(1)
    
except Exception as e:
    print(f"Lỗi khi chạy ứng dụng: {str(e)}")
    logger.error(f"Lỗi khi chạy ứng dụng: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)