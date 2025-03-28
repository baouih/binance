#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Desktop Backtest Tab
-----------------------
Kiểm tra xem tab Backtest trên giao diện desktop có hoạt động đúng cách không
"""

import os
import sys
import json
import logging
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_desktop_backtest')

# Kiểm tra xem tệp cấu hình có đúng cấu trúc không
def test_gui_config():
    """Kiểm tra cấu hình GUI"""
    # Kiểm tra xem tệp cấu hình tồn tại
    config_path = os.path.join('desktop_app', 'gui_config.json')
    if not os.path.exists(config_path):
        logger.error(f"Không tìm thấy tệp cấu hình: {config_path}")
        return False

    # Đọc tệp cấu hình
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Kiểm tra các trường cần thiết
        required_fields = ['show_backtest_tab', 'backtest_reports', 'backtest_charts']
        for field in required_fields:
            if field not in config:
                logger.error(f"Thiếu trường {field} trong tệp cấu hình")
                return False
        
        # Kiểm tra danh sách báo cáo
        if not isinstance(config['backtest_reports'], list) or len(config['backtest_reports']) == 0:
            logger.error("Danh sách báo cáo trống hoặc không đúng định dạng")
            return False
        
        # Kiểm tra danh sách biểu đồ
        if not isinstance(config['backtest_charts'], list) or len(config['backtest_charts']) == 0:
            logger.error("Danh sách biểu đồ trống hoặc không đúng định dạng")
            return False
        
        logger.info("Tệp cấu hình GUI đúng cấu trúc")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi đọc tệp cấu hình: {e}")
        return False

# Kiểm tra xem các báo cáo có tồn tại không
def test_backtest_reports():
    """Kiểm tra các báo cáo backtest"""
    config_path = os.path.join('desktop_app', 'gui_config.json')
    if not os.path.exists(config_path):
        logger.error(f"Không tìm thấy tệp cấu hình: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        reports = config.get('backtest_reports', [])
        missing_reports = []
        
        for report in reports:
            report_path = os.path.join('desktop_app', report.get('file', ''))
            if not os.path.exists(report_path):
                missing_reports.append(report_path)
        
        if missing_reports:
            logger.error(f"Không tìm thấy các báo cáo sau: {', '.join(missing_reports)}")
            return False
        
        logger.info("Tất cả các báo cáo đều tồn tại")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra báo cáo: {e}")
        return False

# Kiểm tra xem các biểu đồ có tồn tại không
def test_backtest_charts():
    """Kiểm tra các biểu đồ backtest"""
    config_path = os.path.join('desktop_app', 'gui_config.json')
    if not os.path.exists(config_path):
        logger.error(f"Không tìm thấy tệp cấu hình: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        charts = config.get('backtest_charts', [])
        missing_charts = []
        
        for chart in charts:
            chart_path = os.path.join('desktop_app', chart.get('file', ''))
            if not os.path.exists(chart_path):
                missing_charts.append(chart_path)
        
        if missing_charts:
            logger.error(f"Không tìm thấy các biểu đồ sau: {', '.join(missing_charts)}")
            return False
        
        logger.info("Tất cả các biểu đồ đều tồn tại")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra biểu đồ: {e}")
        return False

# Kiểm tra dữ liệu tóm tắt backtest
def test_backtest_summary():
    """Kiểm tra dữ liệu tóm tắt backtest"""
    summary_path = os.path.join('desktop_app', 'backtest_results', 'backtest_summary.json')
    if not os.path.exists(summary_path):
        logger.error(f"Không tìm thấy tệp tóm tắt backtest: {summary_path}")
        return False
    
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # Kiểm tra cấu trúc dữ liệu
        required_sections = ['strategies', 'account_recommendations', 'market_conditions', 'comparison']
        for section in required_sections:
            if section not in summary:
                logger.error(f"Thiếu phần {section} trong tệp tóm tắt backtest")
                return False
        
        # Kiểm tra dữ liệu chiến lược
        if 'sideways' not in summary['strategies'] or 'multi_risk' not in summary['strategies'] or 'adaptive' not in summary['strategies']:
            logger.error("Thiếu dữ liệu chiến lược trong tệp tóm tắt backtest")
            return False
        
        logger.info("Tệp tóm tắt backtest đúng cấu trúc")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tệp tóm tắt backtest: {e}")
        return False

# Kiểm tra xem giao diện có thể tạo tab Backtest không
def test_create_backtest_tab():
    """Kiểm tra xem có thể tạo tab Backtest không"""
    try:
        from enhanced_trading_gui import MainApp
        
        # Kiểm tra xem lớp MainApp có phương thức create_backtest_tab không
        if not hasattr(MainApp, 'create_backtest_tab'):
            logger.error("Lớp MainApp không có phương thức create_backtest_tab")
            return False
        
        # Tạo ứng dụng Qt và kiểm tra tab
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        main_app = MainApp()
        
        # Kiểm tra xem có tab Backtest không
        for i in range(main_app.tab_widget.count()):
            if main_app.tab_widget.tabText(i) == "Backtest":
                logger.info("Đã tìm thấy tab Backtest trong giao diện")
                return True
        
        logger.error("Không tìm thấy tab Backtest trong giao diện")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra tab Backtest: {e}")
        return False

def main():
    """Hàm chính để chạy kiểm tra"""
    logger.info("Bắt đầu kiểm tra tab Backtest trên giao diện desktop")
    
    # Chạy các bài kiểm tra
    results = []
    results.append(("Kiểm tra cấu hình GUI", test_gui_config()))
    results.append(("Kiểm tra báo cáo backtest", test_backtest_reports()))
    results.append(("Kiểm tra biểu đồ backtest", test_backtest_charts()))
    results.append(("Kiểm tra dữ liệu tóm tắt backtest", test_backtest_summary()))
    
    # In kết quả
    logger.info("=== Kết quả kiểm tra ===")
    all_passed = True
    for name, result in results:
        status = "Đạt" if result else "Không đạt"
        logger.info(f"{name}: {status}")
        all_passed = all_passed and result
    
    if all_passed:
        logger.info("Tất cả các bài kiểm tra đều đạt")
    else:
        logger.error("Có bài kiểm tra không đạt")
    
    return all_passed

if __name__ == "__main__":
    main()