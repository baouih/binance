#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script để chạy giao diện kiểm tra
"""

import os
import sys
import tkinter as tk
from test_gui import TestGUI

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
    except ImportError as e:
        print(f"ERROR: Thiếu thư viện cần thiết: {e}")
        print("Vui lòng chạy lệnh: pip install pandas numpy requests")
        sys.exit(1)
    
    # Khởi động giao diện kiểm tra
    print("Khởi động giao diện kiểm tra hệ thống giao dịch...")
    
    root = tk.Tk()
    app = TestGUI(root)
    
    # Hiển thị thông báo chào mừng
    from tkinter import messagebox
    messagebox.showinfo(
        "Chào mừng",
        "Chào mừng đến với Giao Diện Kiểm Tra!"
        "\n\nBạn có thể sử dụng giao diện này để kiểm tra các chức năng hệ thống."
    )
    
    root.mainloop()