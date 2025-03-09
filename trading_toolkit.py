#!/usr/bin/env python3
"""
Trading Toolkit - Bộ công cụ giao dịch tổng hợp

Script này cung cấp một giao diện dòng lệnh đơn giản để truy cập tất cả các công cụ phân tích,
giúp người dùng dễ dàng tìm kiếm cơ hội giao dịch, phân tích lý do không đánh coin,
quản lý nhật ký giao dịch, và tương tác với hệ thống một cách hiệu quả.

Cách sử dụng:
    python trading_toolkit.py
"""

import os
import sys
import json
import logging
import datetime
import subprocess
from typing import List, Dict, Any

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("trading_toolkit")

# Danh sách các công cụ có sẵn
AVAILABLE_TOOLS = {
    "1": {
        "name": "Quét thị trường tìm cơ hội giao dịch",
        "script": "find_best_trading_opportunities.py",
        "description": "Quét toàn bộ thị trường để tìm ra TOP cơ hội giao dịch tốt nhất"
    },
    "2": {
        "name": "Phân tích chi tiết một cặp tiền",
        "script": "analyze_trading_opportunity.py",
        "description": "Phân tích chi tiết một cặp tiền cụ thể và đưa ra khuyến nghị giao dịch"
    },
    "3": {
        "name": "Phân tích lý do không giao dịch",
        "script": "analyze_no_trade_reasons.py",
        "description": "Phân tích chi tiết lý do tại sao không nên giao dịch một cặp tiền cụ thể"
    },
    "4": {
        "name": "Thêm giao dịch vào nhật ký",
        "script": "trading_journal.py",
        "description": "Thêm một giao dịch mới vào nhật ký giao dịch"
    },
    "5": {
        "name": "Phân tích hiệu suất giao dịch",
        "script": "trading_journal.py",
        "description": "Phân tích hiệu suất giao dịch dựa trên nhật ký"
    },
    "6": {
        "name": "So sánh giao dịch với khuyến nghị hệ thống",
        "script": "trading_journal.py",
        "description": "So sánh giao dịch của bạn với khuyến nghị của hệ thống"
    }
}

def clear_screen():
    """Xóa màn hình"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_welcome_message():
    """In thông báo chào mừng"""
    clear_screen()
    print("\n" + "="*80)
    print("BỘ CÔNG CỤ GIAO DỊCH TIỀN ĐIỆN TỬ".center(80))
    print("="*80)
    print("\nChào mừng đến với Bộ công cụ giao dịch tiền điện tử!")
    print("Hệ thống này giúp bạn phân tích thị trường, tìm cơ hội giao dịch, theo dõi hiệu suất,")
    print("và cải thiện chiến lược giao dịch một cách hiệu quả.\n")

def print_available_tools():
    """In danh sách các công cụ có sẵn"""
    print("-"*80)
    print("CÁC CÔNG CỤ CÓ SẴN".center(80))
    print("-"*80 + "\n")
    
    for key, tool in AVAILABLE_TOOLS.items():
        print(f"{key}. {tool['name']}")
        print(f"   {tool['description']}")
        print()
    
    print("0. Thoát\n")
    print("-"*80)

def run_market_scan():
    """Chạy công cụ quét thị trường"""
    clear_screen()
    print("\n" + "="*80)
    print("QUÉT THỊ TRƯỜNG TÌM CƠ HỘI GIAO DỊCH".center(80))
    print("="*80 + "\n")
    
    timeframe = input("Nhập khung thời gian (1m/5m/15m/1h/4h/1d, mặc định: 1h): ") or "1h"
    min_score = input("Nhập điểm tối thiểu (0-100, mặc định: 60): ") or "60"
    top_n = input("Nhập số lượng cơ hội hiển thị (mặc định: 5): ") or "5"
    
    command = [sys.executable, AVAILABLE_TOOLS["1"]["script"], 
              "--timeframe", timeframe, 
              "--min-score", min_score, 
              "--top", top_n]
    
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Lỗi khi chạy công cụ: {str(e)}")
    
    input("\nNhấn Enter để tiếp tục...")

def run_detailed_analysis():
    """Chạy công cụ phân tích chi tiết"""
    clear_screen()
    print("\n" + "="*80)
    print("PHÂN TÍCH CHI TIẾT MỘT CẶP TIỀN".center(80))
    print("="*80 + "\n")
    
    symbol = input("Nhập mã cặp tiền (VD: BTCUSDT): ")
    if not symbol:
        print("Mã cặp tiền không được để trống!")
        input("\nNhấn Enter để tiếp tục...")
        return
    
    timeframe = input("Nhập khung thời gian (1m/5m/15m/1h/4h/1d, mặc định: 1h): ") or "1h"
    
    command = [sys.executable, AVAILABLE_TOOLS["2"]["script"], 
              "--symbol", symbol, 
              "--timeframe", timeframe]
    
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Lỗi khi chạy công cụ: {str(e)}")
    
    input("\nNhấn Enter để tiếp tục...")

def run_no_trade_analysis():
    """Chạy công cụ phân tích lý do không giao dịch"""
    clear_screen()
    print("\n" + "="*80)
    print("PHÂN TÍCH LÝ DO KHÔNG GIAO DỊCH".center(80))
    print("="*80 + "\n")
    
    symbol = input("Nhập mã cặp tiền (VD: BTCUSDT): ")
    if not symbol:
        print("Mã cặp tiền không được để trống!")
        input("\nNhấn Enter để tiếp tục...")
        return
    
    timeframe = input("Nhập khung thời gian (1m/5m/15m/1h/4h/1d, mặc định: 1h): ") or "1h"
    
    command = [sys.executable, AVAILABLE_TOOLS["3"]["script"], 
              "--symbol", symbol, 
              "--timeframe", timeframe]
    
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Lỗi khi chạy công cụ: {str(e)}")
    
    input("\nNhấn Enter để tiếp tục...")

def run_add_trade():
    """Chạy công cụ thêm giao dịch vào nhật ký"""
    clear_screen()
    print("\n" + "="*80)
    print("THÊM GIAO DỊCH VÀO NHẬT KÝ".center(80))
    print("="*80 + "\n")
    
    symbol = input("Nhập mã cặp tiền (VD: BTCUSDT): ")
    if not symbol:
        print("Mã cặp tiền không được để trống!")
        input("\nNhấn Enter để tiếp tục...")
        return
    
    direction = input("Nhập hướng giao dịch (long/short): ")
    if direction not in ["long", "short"]:
        print("Hướng giao dịch phải là 'long' hoặc 'short'!")
        input("\nNhấn Enter để tiếp tục...")
        return
    
    try:
        entry_price = input("Nhập giá vào: ")
        exit_price = input("Nhập giá ra: ")
        volume = input("Nhập khối lượng giao dịch: ")
        
        if not entry_price or not exit_price or not volume:
            print("Giá vào, giá ra và khối lượng không được để trống!")
            input("\nNhấn Enter để tiếp tục...")
            return
        
        entry_price = float(entry_price)
        exit_price = float(exit_price)
        volume = float(volume)
    except ValueError:
        print("Giá vào, giá ra và khối lượng phải là số!")
        input("\nNhấn Enter để tiếp tục...")
        return
    
    timeframe = input("Nhập khung thời gian (1m/5m/15m/1h/4h/1d, mặc định: 1h): ") or "1h"
    notes = input("Nhập ghi chú về giao dịch (không bắt buộc): ")
    
    command = [sys.executable, AVAILABLE_TOOLS["4"]["script"], "add",
              "--symbol", symbol,
              "--direction", direction,
              "--entry", str(entry_price),
              "--exit", str(exit_price),
              "--volume", str(volume),
              "--timeframe", timeframe]
    
    if notes:
        command.extend(["--notes", notes])
    
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Lỗi khi chạy công cụ: {str(e)}")
    
    input("\nNhấn Enter để tiếp tục...")

def run_analyze_trades():
    """Chạy công cụ phân tích hiệu suất giao dịch"""
    clear_screen()
    print("\n" + "="*80)
    print("PHÂN TÍCH HIỆU SUẤT GIAO DỊCH".center(80))
    print("="*80 + "\n")
    
    period = input("Nhập số ngày cần phân tích (mặc định: 30): ") or "30"
    
    command = [sys.executable, AVAILABLE_TOOLS["5"]["script"], "analyze",
              "--period", period]
    
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Lỗi khi chạy công cụ: {str(e)}")
    
    input("\nNhấn Enter để tiếp tục...")

def run_compare_trades():
    """Chạy công cụ so sánh giao dịch với khuyến nghị hệ thống"""
    clear_screen()
    print("\n" + "="*80)
    print("SO SÁNH GIAO DỊCH VỚI KHUYẾN NGHỊ HỆ THỐNG".center(80))
    print("="*80 + "\n")
    
    symbol = input("Nhập mã cặp tiền (VD: BTCUSDT): ")
    if not symbol:
        print("Mã cặp tiền không được để trống!")
        input("\nNhấn Enter để tiếp tục...")
        return
    
    timeframe = input("Nhập khung thời gian (1m/5m/15m/1h/4h/1d, mặc định: 1h): ") or "1h"
    
    command = [sys.executable, AVAILABLE_TOOLS["6"]["script"], "compare",
              "--symbol", symbol,
              "--timeframe", timeframe]
    
    try:
        subprocess.run(command)
    except Exception as e:
        print(f"Lỗi khi chạy công cụ: {str(e)}")
    
    input("\nNhấn Enter để tiếp tục...")

def main():
    """Hàm chính"""
    while True:
        print_welcome_message()
        print_available_tools()
        
        choice = input("Chọn một công cụ (0-6): ")
        
        if choice == "0":
            print("\nCảm ơn bạn đã sử dụng Bộ công cụ giao dịch tiền điện tử!")
            break
        elif choice == "1":
            run_market_scan()
        elif choice == "2":
            run_detailed_analysis()
        elif choice == "3":
            run_no_trade_analysis()
        elif choice == "4":
            run_add_trade()
        elif choice == "5":
            run_analyze_trades()
        elif choice == "6":
            run_compare_trades()
        else:
            print(f"\nLựa chọn không hợp lệ: {choice}")
            input("\nNhấn Enter để tiếp tục...")

if __name__ == "__main__":
    main()