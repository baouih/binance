#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tập tin khởi động giao diện người dùng hệ thống giao dịch
"""

import os
import sys
import tkinter as tk
from trading_system_gui import TradingSystemGUI

if __name__ == "__main__":
    # Kiểm tra phiên bản Python
    if sys.version_info < (3, 8):
        print("ERROR: Yêu cầu Python 3.8 trở lên")
        sys.exit(1)
    
    # Kiểm tra các thư viện cần thiết
    try:
        import pandas
        import numpy
        import requests
        import binance
        import matplotlib
    except ImportError as e:
        print(f"ERROR: Thiếu thư viện cần thiết: {e}")
        print("Vui lòng chạy lệnh: pip install -r requirements.txt")
        sys.exit(1)
    
    # Kiểm tra file cấu hình
    if not os.path.exists("account_config.json"):
        print("Cảnh báo: Không tìm thấy file account_config.json")
        print("Tạo file cấu hình mặc định...")
        
        # Tạo file cấu hình mặc định
        import json
        default_config = {
            "api_key": "",
            "api_secret": "",
            "testnet": True,
            "exchange": "binance",
            "account_type": "futures",
            "base_currency": "USDT",
            "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            "risk_level": 10,
            "risk_per_trade": 10.0,
            "leverage": 20,
            "max_open_positions": 10,
            "position_size_limit": 800,
            "order_types": ["MARKET", "LIMIT", "STOP", "TAKE_PROFIT"],
            "capital_allocation": {
                "BTC": 0.3,
                "ETH": 0.2,
                "others": 0.5
            },
            "enable_notifications": True,
            "auto_reduce_leverage": True,
            "enable_trailing_stop": True,
            "enable_dynamic_risk": True
        }
        with open("account_config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
    
    # Kiểm tra thư mục và tạo các file cấu hình rủi ro
    if not os.path.exists("risk_configs"):
        print("Tạo thư mục risk_configs và các file cấu hình rủi ro...")
        os.makedirs("risk_configs", exist_ok=True)
        
        # Tạo các file cấu hình mức độ rủi ro
        risk_levels = [10, 15, 20, 30]
        
        # Cấu hình cho các mức rủi ro
        risk_configs = {
            10: {
                "max_open_positions": 2,
                "position_size_percent": 1.0,
                "stop_loss_percent": 1.0,
                "take_profit_percent": 2.0,
                "trailing_stop_percent": 0.3,
                "max_daily_trades": 5,
                "max_daily_drawdown_percent": 3.0,
                "use_adaptive_position_sizing": True,
                "use_dynamic_stop_loss": True,
                "leverage": 1,
                "risk_multipliers": {
                    "stop_loss_multiplier": 1.0,
                    "take_profit_multiplier": 1.0,
                    "trailing_stop_callback": 0.1,
                    "position_size_multiplier": 1.0
                }
            },
            15: {
                "max_open_positions": 3,
                "position_size_percent": 1.5,
                "stop_loss_percent": 1.5,
                "take_profit_percent": 3.0,
                "trailing_stop_percent": 0.5,
                "max_daily_trades": 8,
                "max_daily_drawdown_percent": 5.0,
                "use_adaptive_position_sizing": True,
                "use_dynamic_stop_loss": True,
                "leverage": 2,
                "risk_multipliers": {
                    "stop_loss_multiplier": 1.0,
                    "take_profit_multiplier": 1.0,
                    "trailing_stop_callback": 0.2,
                    "position_size_multiplier": 1.0
                }
            },
            20: {
                "max_open_positions": 4,
                "position_size_percent": 2.0,
                "stop_loss_percent": 2.0,
                "take_profit_percent": 4.0,
                "trailing_stop_percent": 0.7,
                "max_daily_trades": 10,
                "max_daily_drawdown_percent": 7.0,
                "use_adaptive_position_sizing": True,
                "use_dynamic_stop_loss": True,
                "leverage": 5,
                "risk_multipliers": {
                    "stop_loss_multiplier": 1.0,
                    "take_profit_multiplier": 1.0,
                    "trailing_stop_callback": 0.3,
                    "position_size_multiplier": 1.0
                }
            },
            30: {
                "max_open_positions": 5,
                "position_size_percent": 3.0,
                "stop_loss_percent": 3.0,
                "take_profit_percent": 6.0,
                "trailing_stop_percent": 1.0,
                "max_daily_trades": 15,
                "max_daily_drawdown_percent": 10.0,
                "use_adaptive_position_sizing": True,
                "use_dynamic_stop_loss": True,
                "leverage": 10,
                "risk_multipliers": {
                    "stop_loss_multiplier": 1.0,
                    "take_profit_multiplier": 1.0,
                    "trailing_stop_callback": 0.5,
                    "position_size_multiplier": 1.0
                }
            }
        }
        
        # Ghi các file cấu hình
        for level, config in risk_configs.items():
            file_path = os.path.join("risk_configs", f"risk_level_{level}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"Đã tạo file cấu hình mức rủi ro {level}%")
    
    # Khởi động giao diện
    print("Khởi động giao diện hệ thống giao dịch...")
    
    root = tk.Tk()
    app = TradingSystemGUI(root)
    
    # Hiển thị thông báo chào mừng
    from tkinter import messagebox
    messagebox.showinfo(
        "Chào mừng",
        "Chào mừng đến với Hệ thống Giao dịch Tiền điện tử Tự động!"
        "\n\nVui lòng thiết lập API Key trong phần 'Cài đặt API'"
        "\ntrước khi bắt đầu sử dụng hệ thống."
    )
    
    root.mainloop()