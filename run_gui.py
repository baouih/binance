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
            "api_mode": "testnet",
            "account_type": "futures"
        }
        with open("account_config.json", "w") as f:
            json.dump(default_config, f, indent=4)
    
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