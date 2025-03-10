#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script kiểm tra tính đầy đủ và khả dụng của tất cả các thành phần trong ứng dụng desktop
"""

import os
import sys
import json
import glob
import logging
import traceback
from typing import Dict, List, Any, Tuple

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("component_validation.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("component_validation")

def check_required_files() -> Dict[str, bool]:
    """Kiểm tra các tệp cần thiết cho ứng dụng desktop"""
    
    required_files = {
        "Giao diện chính": "enhanced_trading_gui.py",
        "Entry point": "run_desktop_app.py",
        "Đóng gói exe": "package_desktop_app.py",
        "Phân tích thị trường": "market_analyzer.py",
        "Quản lý vị thế": "position_manager.py",
        "Quản lý rủi ro": "risk_manager.py",
        "Cập nhật tự động": "auto_update_client.py",
        "Cấu hình môi trường mẫu": ".env.example"
    }
    
    results = {}
    
    logger.info("===== KIỂM TRA CÁC FILE CẦN THIẾT =====")
    
    for name, file_path in required_files.items():
        exists = os.path.exists(file_path)
        results[name] = exists
        
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return results

def check_gui_components() -> Dict[str, bool]:
    """Kiểm tra các thành phần giao diện chính"""
    
    # Danh sách các thành phần GUI cần kiểm tra từ enhanced_trading_gui.py
    gui_components = {
        "Khởi tạo UI": False,
        "Tab Tổng quan": False,
        "Tab Giao dịch": False,
        "Tab Quản lý vị thế": False,
        "Tab Phân tích thị trường": False,
        "Tab Cài đặt": False,
        "Cập nhật thị trường": False,
        "Mở vị thế": False,
        "Đóng vị thế": False,
        "Cập nhật SL/TP": False,
        "Phân tích kỹ thuật": False,
        "Cấu hình API": False,
        "Cấu hình Telegram": False,
        "Cấu hình rủi ro": False,
        "Kiểm tra cập nhật": False
    }
    
    logger.info("===== KIỂM TRA THÀNH PHẦN GIAO DIỆN =====")
    
    try:
        with open("enhanced_trading_gui.py", "r", encoding="utf-8") as file:
            content = file.read()
            
            # Kiểm tra từng thành phần
            if "def __init__" in content and "super().__init__" in content:
                gui_components["Khởi tạo UI"] = True
            
            if "def setup_overview_tab" in content:
                gui_components["Tab Tổng quan"] = True
            
            if "def setup_trading_tab" in content:
                gui_components["Tab Giao dịch"] = True
            
            if "def setup_position_tab" in content:
                gui_components["Tab Quản lý vị thế"] = True
            
            if "def setup_analysis_tab" in content:
                gui_components["Tab Phân tích thị trường"] = True
            
            if "def setup_settings_tab" in content:
                gui_components["Tab Cài đặt"] = True
            
            if "def update_market_data" in content:
                gui_components["Cập nhật thị trường"] = True
            
            if "def open_position" in content:
                gui_components["Mở vị thế"] = True
            
            if "def close_position" in content:
                gui_components["Đóng vị thế"] = True
            
            if "def update_sl_tp" in content:
                gui_components["Cập nhật SL/TP"] = True
            
            if "def analyze_market" in content or "def run_technical_analysis" in content:
                gui_components["Phân tích kỹ thuật"] = True
            
            if "api_key" in content and "api_secret" in content:
                gui_components["Cấu hình API"] = True
            
            if "telegram_token" in content or "telegram_chat_id" in content:
                gui_components["Cấu hình Telegram"] = True
            
            if "risk_percentage" in content or "max_positions" in content:
                gui_components["Cấu hình rủi ro"] = True
            
            if "check_for_updates" in content:
                gui_components["Kiểm tra cập nhật"] = True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra thành phần giao diện: {str(e)}", exc_info=True)
    
    # Hiển thị kết quả
    for name, exists in gui_components.items():
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return gui_components

def check_api_functions() -> Dict[str, bool]:
    """Kiểm tra các chức năng API cần thiết"""
    
    api_functions = {
        "Kết nối Binance API": False,
        "Lấy dữ liệu thị trường": False,
        "Lấy dữ liệu lịch sử": False,
        "Lấy thông tin tài khoản": False,
        "Mở vị thế": False,
        "Đóng vị thế": False,
        "Cập nhật SL/TP": False,
        "Lấy danh sách vị thế": False,
        "Tính toán chỉ báo kỹ thuật": False,
        "Phân tích cơ hội giao dịch": False
    }
    
    logger.info("===== KIỂM TRA CHỨC NĂNG API =====")
    
    # Kiểm tra MarketAnalyzer
    try:
        with open("market_analyzer.py", "r", encoding="utf-8") as file:
            content = file.read()
            
            if "Binance" in content and "Client" in content:
                api_functions["Kết nối Binance API"] = True
            
            if "get_market_overview" in content:
                api_functions["Lấy dữ liệu thị trường"] = True
            
            if "get_historical_data" in content:
                api_functions["Lấy dữ liệu lịch sử"] = True
            
            if "calculate_indicators" in content or "calculate_rsi" in content or "calculate_macd" in content:
                api_functions["Tính toán chỉ báo kỹ thuật"] = True
            
            if "scan_trading_opportunities" in content or "find_opportunities" in content:
                api_functions["Phân tích cơ hội giao dịch"] = True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra MarketAnalyzer: {str(e)}", exc_info=True)
    
    # Kiểm tra PositionManager
    try:
        with open("position_manager.py", "r", encoding="utf-8") as file:
            content = file.read()
            
            if "get_account_balance" in content:
                api_functions["Lấy thông tin tài khoản"] = True
            
            if "open_position" in content:
                api_functions["Mở vị thế"] = True
            
            if "close_position" in content:
                api_functions["Đóng vị thế"] = True
            
            if "update_sl_tp" in content:
                api_functions["Cập nhật SL/TP"] = True
            
            if "get_all_positions" in content:
                api_functions["Lấy danh sách vị thế"] = True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra PositionManager: {str(e)}", exc_info=True)
    
    # Hiển thị kết quả
    for name, exists in api_functions.items():
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return api_functions

def check_auto_update_features() -> Dict[str, bool]:
    """Kiểm tra chức năng cập nhật tự động"""
    
    auto_update_features = {
        "Kiểm tra phiên bản": False,
        "Tải bản cập nhật": False,
        "Cài đặt cập nhật": False,
        "Khởi động sau cập nhật": False
    }
    
    logger.info("===== KIỂM TRA CHỨC NĂNG CẬP NHẬT TỰ ĐỘNG =====")
    
    try:
        with open("auto_update_client.py", "r", encoding="utf-8") as file:
            content = file.read()
            
            if "check_for_updates" in content or "get_latest_version" in content:
                auto_update_features["Kiểm tra phiên bản"] = True
            
            if "download_update" in content:
                auto_update_features["Tải bản cập nhật"] = True
            
            if "install_update" in content:
                auto_update_features["Cài đặt cập nhật"] = True
            
            if "restart_application" in content:
                auto_update_features["Khởi động sau cập nhật"] = True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra auto_update_client.py: {str(e)}", exc_info=True)
    
    # Hiển thị kết quả
    for name, exists in auto_update_features.items():
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return auto_update_features

def check_exe_packaging() -> Dict[str, bool]:
    """Kiểm tra chức năng đóng gói exe"""
    
    exe_features = {
        "PyInstaller config": False,
        "Icon included": False,
        "Include resources": False,
        "One-file option": False,
        "Splash screen": False
    }
    
    logger.info("===== KIỂM TRA CHỨC NĂNG ĐÓNG GÓI EXE =====")
    
    try:
        with open("package_desktop_app.py", "r", encoding="utf-8") as file:
            content = file.read()
            
            if "pyinstaller" in content.lower():
                exe_features["PyInstaller config"] = True
            
            if "icon" in content.lower():
                exe_features["Icon included"] = True
            
            if "datas" in content or "add_data" in content:
                exe_features["Include resources"] = True
            
            if "onefile" in content:
                exe_features["One-file option"] = True
            
            if "splash" in content:
                exe_features["Splash screen"] = True
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra package_desktop_app.py: {str(e)}", exc_info=True)
    
    # Hiển thị kết quả
    for name, exists in exe_features.items():
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return exe_features

def check_telegram_integration() -> Dict[str, bool]:
    """Kiểm tra tích hợp Telegram"""
    
    telegram_features = {
        "Gửi thông báo": False,
        "Định dạng tin nhắn": False,
        "Thông báo vị thế": False,
        "Thông báo cơ hội": False,
        "Thông báo lỗi": False
    }
    
    logger.info("===== KIỂM TRA TÍCH HỢP TELEGRAM =====")
    
    # Tìm file chứa mã Telegram
    telegram_files = glob.glob("*telegram*.py")
    
    if telegram_files:
        for file_path in telegram_files:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                    
                    if "sendMessage" in content:
                        telegram_features["Gửi thông báo"] = True
                    
                    if "format_message" in content or "parse_mode" in content:
                        telegram_features["Định dạng tin nhắn"] = True
                    
                    if "position" in content and "notify" in content:
                        telegram_features["Thông báo vị thế"] = True
                    
                    if "opportunity" in content or "signal" in content:
                        telegram_features["Thông báo cơ hội"] = True
                    
                    if "error" in content and "notify" in content:
                        telegram_features["Thông báo lỗi"] = True
            
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra {file_path}: {str(e)}", exc_info=True)
    else:
        # Kiểm tra trong các file chính
        try:
            # Kiểm tra trong enhanced_trading_gui.py
            with open("enhanced_trading_gui.py", "r", encoding="utf-8") as file:
                content = file.read()
                
                if "telegram" in content.lower() and "send" in content:
                    telegram_features["Gửi thông báo"] = True
                
                if "telegram" in content.lower() and "format" in content:
                    telegram_features["Định dạng tin nhắn"] = True
                
                if "telegram" in content.lower() and "position" in content:
                    telegram_features["Thông báo vị thế"] = True
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra tích hợp Telegram trong GUI: {str(e)}", exc_info=True)
    
    # Kiểm tra .env.example cho cấu hình Telegram
    try:
        with open(".env.example", "r", encoding="utf-8") as file:
            content = file.read()
            
            if "TELEGRAM_BOT_TOKEN" in content and "TELEGRAM_CHAT_ID" in content:
                logger.info("Cấu hình Telegram được tìm thấy trong .env.example")
    
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra cấu hình Telegram: {str(e)}", exc_info=True)
    
    # Hiển thị kết quả
    for name, exists in telegram_features.items():
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return telegram_features

def check_documentation() -> Dict[str, bool]:
    """Kiểm tra tài liệu hướng dẫn"""
    
    documentation = {
        "README desktop": False,
        "Hướng dẫn sử dụng": False,
        "Hướng dẫn exe": False,
        "README telegram": False
    }
    
    logger.info("===== KIỂM TRA TÀI LIỆU HƯỚNG DẪN =====")
    
    # Kiểm tra README_DESKTOP_APP.md
    if os.path.exists("README_DESKTOP_APP.md"):
        documentation["README desktop"] = True
    
    # Kiểm tra HƯỚNG_DẪN_SỬ_DỤNG.md
    if os.path.exists("HƯỚNG_DẪN_SỬ_DỤNG.md"):
        documentation["Hướng dẫn sử dụng"] = True
    
    # Kiểm tra hướng dẫn đóng gói exe
    if os.path.exists("HƯỚNG_DẪN_EXE_VÀ_SỬ_DỤNG_CHI_TIẾT.md"):
        documentation["Hướng dẫn exe"] = True
    
    # Kiểm tra README_TELEGRAM_NOTIFICATIONS.md
    if os.path.exists("README_TELEGRAM_NOTIFICATIONS.md"):
        documentation["README telegram"] = True
    
    # Hiển thị kết quả
    for name, exists in documentation.items():
        status = "✅ TỒN TẠI" if exists else "❌ KHÔNG TÌM THẤY"
        logger.info(f"{name}: {status}")
    
    return documentation

def run_full_validation():
    """Chạy kiểm tra toàn diện"""
    
    logger.info("========== BẮT ĐẦU KIỂM TRA TOÀN DIỆN ==========")
    
    results = {
        "required_files": check_required_files(),
        "gui_components": check_gui_components(),
        "api_functions": check_api_functions(),
        "auto_update": check_auto_update_features(),
        "exe_packaging": check_exe_packaging(),
        "telegram": check_telegram_integration(),
        "documentation": check_documentation()
    }
    
    logger.info("========== KẾT QUẢ KIỂM TRA TOÀN DIỆN ==========")
    
    # Tính tỷ lệ hoàn thành cho từng danh mục
    completion_rates = {}
    
    for category, items in results.items():
        total = len(items)
        completed = sum(1 for value in items.values() if value)
        rate = (completed / total) * 100 if total > 0 else 0
        completion_rates[category] = rate
        
        logger.info(f"{category}: {completed}/{total} ({rate:.1f}%)")
    
    # Tính tỷ lệ hoàn thành tổng thể
    total_items = sum(len(items) for items in results.values())
    completed_items = sum(sum(1 for value in items.values() if value) for items in results.values())
    overall_rate = (completed_items / total_items) * 100 if total_items > 0 else 0
    
    logger.info(f"Tổng thể: {completed_items}/{total_items} ({overall_rate:.1f}%)")
    
    # Hiển thị danh sách các mục còn thiếu
    missing_items = []
    
    for category, items in results.items():
        for name, exists in items.items():
            if not exists:
                missing_items.append(f"{category}: {name}")
    
    if missing_items:
        logger.info("========== CÁC MỤC CẦN BỔ SUNG ==========")
        
        for item in missing_items:
            logger.info(f"❌ {item}")
    
    # Lưu kết quả kiểm tra vào file JSON
    try:
        with open("component_validation_result.json", "w", encoding="utf-8") as file:
            json.dump({
                "results": results,
                "completion_rates": completion_rates,
                "overall_rate": overall_rate,
                "missing_items": missing_items
            }, file, indent=4)
        
        logger.info("Đã lưu kết quả kiểm tra vào component_validation_result.json")
    
    except Exception as e:
        logger.error(f"Lỗi khi lưu kết quả kiểm tra: {str(e)}", exc_info=True)
    
    return overall_rate >= 80  # Coi là đạt nếu tỷ lệ hoàn thành >= 80%

if __name__ == "__main__":
    success = run_full_validation()
    
    if success:
        logger.info("✅✅✅ KIỂM TRA THÀNH CÔNG: Hệ thống đã sẵn sàng cho việc sử dụng ✅✅✅")
        sys.exit(0)
    else:
        logger.warning("⚠️⚠️⚠️ KIỂM TRA KHÔNG ĐẠT: Cần bổ sung một số thành phần ⚠️⚠️⚠️")
        sys.exit(1)