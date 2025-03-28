#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cập nhật kết quả backtest vào giao diện desktop
Tích hợp các báo cáo backtest mới nhất vào ứng dụng desktop
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update_desktop_backtest')

# Đường dẫn đến các file báo cáo backtest
BACKTEST_SUMMARY_REPORT = 'backtest_summary_report.md'
RISK_PERFORMANCE_SUMMARY = 'risk_performance_summary.md'
TRADING_SYSTEM_VALIDATION = 'trading_system_validation.md'

# Đường dẫn đến thư mục desktop app
DESKTOP_APP_DIR = 'desktop_app'
DESKTOP_REPORTS_DIR = os.path.join(DESKTOP_APP_DIR, 'reports')
DESKTOP_BACKTEST_DIR = os.path.join(DESKTOP_APP_DIR, 'backtest_results')
DESKTOP_ASSETS_DIR = os.path.join(DESKTOP_APP_DIR, 'assets')

def ensure_directories():
    """Đảm bảo các thư mục cần thiết tồn tại"""
    for directory in [DESKTOP_APP_DIR, DESKTOP_REPORTS_DIR, DESKTOP_BACKTEST_DIR, DESKTOP_ASSETS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Đã tạo thư mục {directory}")

def copy_report_files():
    """Sao chép các file báo cáo backtest vào thư mục desktop"""
    reports = [
        (BACKTEST_SUMMARY_REPORT, os.path.join(DESKTOP_REPORTS_DIR, 'backtest_summary.md')),
        (RISK_PERFORMANCE_SUMMARY, os.path.join(DESKTOP_REPORTS_DIR, 'risk_performance.md')),
        (TRADING_SYSTEM_VALIDATION, os.path.join(DESKTOP_REPORTS_DIR, 'trading_validation.md'))
    ]
    
    for src, dst in reports:
        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info(f"Đã sao chép {src} đến {dst}")
        else:
            logger.warning(f"Không tìm thấy file báo cáo {src}")

def copy_backtest_results():
    """Sao chép kết quả backtest vào thư mục desktop"""
    # Sao chép từ thư mục backtest_results
    if os.path.exists('backtest_results'):
        # Lấy 5 file JSON mới nhất
        json_files = [f for f in os.listdir('backtest_results') if f.endswith('.json')]
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join('backtest_results', x)), reverse=True)
        
        for json_file in json_files[:5]:
            src = os.path.join('backtest_results', json_file)
            dst = os.path.join(DESKTOP_BACKTEST_DIR, json_file)
            shutil.copy2(src, dst)
            logger.info(f"Đã sao chép {src} đến {dst}")
    
    # Sao chép từ thư mục quick_test_results
    if os.path.exists('quick_test_results'):
        # Lấy 5 file PNG mới nhất
        png_files = [f for f in os.listdir('quick_test_results') if f.endswith('.png')]
        png_files.sort(key=lambda x: os.path.getmtime(os.path.join('quick_test_results', x)), reverse=True)
        
        for png_file in png_files[:5]:
            src = os.path.join('quick_test_results', png_file)
            dst = os.path.join(DESKTOP_ASSETS_DIR, png_file)
            shutil.copy2(src, dst)
            logger.info(f"Đã sao chép {src} đến {dst}")

def create_backtest_summary_json():
    """Tạo file JSON tóm tắt kết quả backtest cho giao diện desktop"""
    # Dữ liệu tóm tắt dựa trên báo cáo
    summary_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategies": {
            "sideways": {
                "win_rates": {
                    "risk_10": 100.0,
                    "risk_15": 100.0,
                    "risk_20": 90.76,
                    "risk_25": 85.33
                },
                "profits": {
                    "risk_10": 0.10,
                    "risk_15": 0.18,
                    "risk_20": 0.25,
                    "risk_25": 0.30
                },
                "trades_count": {
                    "risk_10": 177,
                    "risk_15": 163,
                    "risk_20": 130,
                    "risk_25": 75
                },
                "max_drawdown": {
                    "risk_10": 0.00,
                    "risk_15": 0.00,
                    "risk_20": 0.01,
                    "risk_25": 0.05
                }
            },
            "multi_risk": {
                "win_rates": {
                    "risk_10": 94.96,
                    "risk_15": 91.45,
                    "risk_20": 74.73,
                    "risk_25": 63.64
                },
                "profits": {
                    "risk_10": 0.03,
                    "risk_15": 0.07,
                    "risk_20": 0.09,
                    "risk_25": 0.07
                },
                "trades_count": {
                    "risk_10": 119,
                    "risk_15": 117,
                    "risk_20": 91,
                    "risk_25": 55
                },
                "max_drawdown": {
                    "risk_10": 0.00,
                    "risk_15": 0.00,
                    "risk_20": 0.00,
                    "risk_25": 0.01
                }
            },
            "adaptive": {
                "win_rates": {
                    "risk_low": 85.71,
                    "risk_medium": 76.19,
                    "risk_high": 64.81
                },
                "profits": {
                    "risk_low": 0.15,
                    "risk_medium": 0.31,
                    "risk_high": 0.52
                },
                "trades_count": {
                    "risk_low": 63,
                    "risk_medium": 88,
                    "risk_high": 108
                },
                "max_drawdown": {
                    "risk_low": 0.01,
                    "risk_medium": 0.06,
                    "risk_high": 0.18
                }
            }
        },
        "account_recommendations": {
            "small": {
                "risk_level": "20-30%",
                "leverage": "15-20x",
                "strategy": "Sideways + Adaptive",
                "expected_monthly_profit": "30-100%",
                "target_win_rate": "50-75%"
            },
            "medium": {
                "risk_level": "10-15%",
                "leverage": "5-10x",
                "strategy": "Multi-Risk + Adaptive",
                "expected_monthly_profit": "5-30%",
                "target_win_rate": "70-90%"
            },
            "large": {
                "risk_level": "2-3%",
                "leverage": "3-5x",
                "strategy": "Sideways + Multi-Risk",
                "expected_monthly_profit": "0.5-5%",
                "target_win_rate": "90-100%"
            }
        },
        "market_conditions": {
            "bull": {
                "best_strategy": "Sideways",
                "best_win_rate": 85.0,
                "best_profit": 0.20
            },
            "bear": {
                "best_strategy": "Sideways",
                "best_win_rate": 90.0,
                "best_profit": 0.25
            },
            "sideways": {
                "best_strategy": "Sideways",
                "best_win_rate": 95.0,
                "best_profit": 0.30
            },
            "volatile": {
                "best_strategy": "Adaptive",
                "best_win_rate": 80.0,
                "best_profit": 0.50
            }
        },
        "comparison": {
            "system_low_risk": {
                "annual_profit": "6-60%",
                "drawdown": "0-1%",
                "sharpe": "3.5-5.0"
            },
            "system_high_risk": {
                "annual_profit": "180-1200%",
                "drawdown": "0.5-12%",
                "sharpe": "1.5-2.5"
            },
            "hodl_bitcoin": {
                "annual_profit": "130%",
                "drawdown": "30-85%",
                "sharpe": "0.8-1.2"
            }
        }
    }
    
    # Lưu dữ liệu tóm tắt vào file JSON
    output_file = os.path.join(DESKTOP_BACKTEST_DIR, 'backtest_summary.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Đã tạo file tóm tắt backtest: {output_file}")

def update_desktop_gui_config():
    """Cập nhật file cấu hình của desktop GUI để hiển thị kết quả backtest mới nhất"""
    config_file = os.path.join(DESKTOP_APP_DIR, 'gui_config.json')
    
    # Tạo cấu hình mặc định nếu không tồn tại
    if not os.path.exists(config_file):
        config = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "show_backtest_tab": True,
            "default_risk_level": "medium",
            "default_strategy": "sideways",
            "backtest_reports": [
                {"name": "Tổng quan Backtest", "file": "reports/backtest_summary.md"},
                {"name": "Phân tích Mức Rủi ro", "file": "reports/risk_performance.md"},
                {"name": "Kiểm định Hệ thống", "file": "reports/trading_validation.md"}
            ],
            "backtest_charts": []
        }
    else:
        # Đọc cấu hình hiện tại
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Cập nhật thời gian
        config["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        config["show_backtest_tab"] = True
    
    # Thêm đường dẫn đến các biểu đồ backtest
    config["backtest_charts"] = []
    if os.path.exists(DESKTOP_ASSETS_DIR):
        png_files = [f for f in os.listdir(DESKTOP_ASSETS_DIR) if f.endswith('.png')]
        for png_file in png_files:
            config["backtest_charts"].append({
                "name": png_file.replace('.png', '').replace('_', ' '),
                "file": f"assets/{png_file}"
            })
    
    # Lưu cấu hình
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Đã cập nhật file cấu hình GUI: {config_file}")

def update_gui_code():
    """Cập nhật mã nguồn của giao diện desktop để hiển thị kết quả backtest"""
    try:
        # Đọc file enhanced_trading_gui.py
        with open('enhanced_trading_gui.py', 'r', encoding='utf-8') as f:
            gui_code = f.read()
        
        # Kiểm tra xem đã có tab Backtest chưa
        if 'def create_backtest_tab' not in gui_code:
            # Thêm vào cuối class MainApp
            add_position = gui_code.find('if __name__ == "__main__":')
            if add_position != -1:
                # Code cho tab Backtest
                backtest_tab_code = """
    def create_backtest_tab(self):
        \"\"\"Tạo tab Backtest Results\"\"\"
        backtest_tab = QWidget()
        layout = QVBoxLayout(backtest_tab)
        
        # Tiêu đề
        title_label = QLabel("Kết quả Backtest")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Tạo tab widget cho các báo cáo khác nhau
        reports_tabs = QTabWidget()
        
        # Tab tóm tắt
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        
        # Hiển thị biểu đồ chiến lược
        strategy_group = QGroupBox("Hiệu suất Chiến lược")
        strategy_layout = QVBoxLayout()
        
        # Tạo bảng hiển thị win rate
        win_rate_table = QTableWidget()
        win_rate_table.setColumnCount(5)
        win_rate_table.setHorizontalHeaderLabels(["Chiến lược", "Rủi ro 10%", "Rủi ro 15%", "Rủi ro 20%", "Rủi ro 25%"])
        win_rate_table.setRowCount(3)
        win_rate_table.setVerticalHeaderLabels(["Sideways", "Multi-Risk", "Adaptive"])
        
        # Tải dữ liệu từ file JSON
        summary_file = os.path.join('desktop_app', 'backtest_results', 'backtest_summary.json')
        if os.path.exists(summary_file):
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # Đổ dữ liệu vào bảng
            # Sideways
            win_rate_table.setItem(0, 0, QTableWidgetItem("Sideways"))
            win_rate_table.setItem(0, 1, QTableWidgetItem(f"{summary_data['strategies']['sideways']['win_rates']['risk_10']}%"))
            win_rate_table.setItem(0, 2, QTableWidgetItem(f"{summary_data['strategies']['sideways']['win_rates']['risk_15']}%"))
            win_rate_table.setItem(0, 3, QTableWidgetItem(f"{summary_data['strategies']['sideways']['win_rates']['risk_20']}%"))
            win_rate_table.setItem(0, 4, QTableWidgetItem(f"{summary_data['strategies']['sideways']['win_rates']['risk_25']}%"))
            
            # Multi-Risk
            win_rate_table.setItem(1, 0, QTableWidgetItem("Multi-Risk"))
            win_rate_table.setItem(1, 1, QTableWidgetItem(f"{summary_data['strategies']['multi_risk']['win_rates']['risk_10']}%"))
            win_rate_table.setItem(1, 2, QTableWidgetItem(f"{summary_data['strategies']['multi_risk']['win_rates']['risk_15']}%"))
            win_rate_table.setItem(1, 3, QTableWidgetItem(f"{summary_data['strategies']['multi_risk']['win_rates']['risk_20']}%"))
            win_rate_table.setItem(1, 4, QTableWidgetItem(f"{summary_data['strategies']['multi_risk']['win_rates']['risk_25']}%"))
            
            # Adaptive
            win_rate_table.setItem(2, 0, QTableWidgetItem("Adaptive"))
            win_rate_table.setItem(2, 1, QTableWidgetItem(f"{summary_data['strategies']['adaptive']['win_rates']['risk_low']}%"))
            win_rate_table.setItem(2, 2, QTableWidgetItem(f"{summary_data['strategies']['adaptive']['win_rates']['risk_medium']}%"))
            win_rate_table.setItem(2, 3, QTableWidgetItem(f"{summary_data['strategies']['adaptive']['win_rates']['risk_high']}%"))
            win_rate_table.setItem(2, 4, QTableWidgetItem("N/A"))
        
        strategy_layout.addWidget(win_rate_table)
        strategy_group.setLayout(strategy_layout)
        summary_layout.addWidget(strategy_group)
        
        # Đề xuất theo kích thước tài khoản
        account_group = QGroupBox("Đề xuất theo Kích thước Tài khoản")
        account_layout = QVBoxLayout()
        
        # Tạo bảng đề xuất
        account_table = QTableWidget()
        account_table.setColumnCount(5)
        account_table.setHorizontalHeaderLabels(["Kích thước", "Rủi ro", "Đòn bẩy", "Chiến lược", "Profit/tháng"])
        account_table.setRowCount(3)
        account_table.setVerticalHeaderLabels(["Nhỏ ($100-500)", "Trung bình ($500-$5,000)", "Lớn (>$5,000)"])
        
        if os.path.exists(summary_file):
            # Nhỏ
            account_table.setItem(0, 0, QTableWidgetItem("Nhỏ ($100-500)"))
            account_table.setItem(0, 1, QTableWidgetItem(summary_data['account_recommendations']['small']['risk_level']))
            account_table.setItem(0, 2, QTableWidgetItem(summary_data['account_recommendations']['small']['leverage']))
            account_table.setItem(0, 3, QTableWidgetItem(summary_data['account_recommendations']['small']['strategy']))
            account_table.setItem(0, 4, QTableWidgetItem(summary_data['account_recommendations']['small']['expected_monthly_profit']))
            
            # Trung bình
            account_table.setItem(1, 0, QTableWidgetItem("Trung bình ($500-$5,000)"))
            account_table.setItem(1, 1, QTableWidgetItem(summary_data['account_recommendations']['medium']['risk_level']))
            account_table.setItem(1, 2, QTableWidgetItem(summary_data['account_recommendations']['medium']['leverage']))
            account_table.setItem(1, 3, QTableWidgetItem(summary_data['account_recommendations']['medium']['strategy']))
            account_table.setItem(1, 4, QTableWidgetItem(summary_data['account_recommendations']['medium']['expected_monthly_profit']))
            
            # Lớn
            account_table.setItem(2, 0, QTableWidgetItem("Lớn (>$5,000)"))
            account_table.setItem(2, 1, QTableWidgetItem(summary_data['account_recommendations']['large']['risk_level']))
            account_table.setItem(2, 2, QTableWidgetItem(summary_data['account_recommendations']['large']['leverage']))
            account_table.setItem(2, 3, QTableWidgetItem(summary_data['account_recommendations']['large']['strategy']))
            account_table.setItem(2, 4, QTableWidgetItem(summary_data['account_recommendations']['large']['expected_monthly_profit']))
        
        account_layout.addWidget(account_table)
        account_group.setLayout(account_layout)
        summary_layout.addWidget(account_group)
        
        # Thêm vào tab tóm tắt
        summary_tab.setLayout(summary_layout)
        reports_tabs.addTab(summary_tab, "Tóm tắt")
        
        # Tab báo cáo chi tiết
        for report_file in ['reports/backtest_summary.md', 'reports/risk_performance.md', 'reports/trading_validation.md']:
            full_path = os.path.join('desktop_app', report_file)
            if os.path.exists(full_path):
                report_tab = QWidget()
                report_layout = QVBoxLayout(report_tab)
                
                report_text = QTextEdit()
                report_text.setReadOnly(True)
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                
                report_text.setMarkdown(report_content)
                report_layout.addWidget(report_text)
                
                tab_name = os.path.basename(report_file).replace('.md', '').replace('_', ' ').title()
                reports_tabs.addTab(report_tab, tab_name)
        
        # Thêm tab widget vào layout
        layout.addWidget(reports_tabs)
        
        return backtest_tab
"""
                
                # Thêm vào MainApp.__init__ để tạo tab
                init_content = gui_code[:add_position]
                # Tìm vị trí sau khi tạo các tab khác
                tab_position = init_content.find('self.tabs.addTab(self.create_market_tab(), "Thị Trường")')
                if tab_position != -1:
                    # Tìm điểm kết thúc của init
                    tab_end = init_content[tab_position:].find('\n        # ')
                    if tab_end != -1:
                        # Vị trí thêm mã
                        insert_position = tab_position + tab_end
                        # Thêm tab mới
                        new_tab_code = '\n        self.tabs.addTab(self.create_backtest_tab(), "Backtest")'
                        # Ghép mã
                        new_gui_code = init_content[:insert_position] + new_tab_code + init_content[insert_position:] + backtest_tab_code + gui_code[add_position:]
                        
                        # Lưu mã mới
                        with open('enhanced_trading_gui.py', 'w', encoding='utf-8') as f:
                            f.write(new_gui_code)
                        
                        logger.info("Đã cập nhật mã GUI để thêm tab Backtest")
                    else:
                        logger.warning("Không tìm thấy vị trí để thêm tab Backtest vào GUI")
                else:
                    logger.warning("Không tìm thấy vị trí tabs.addTab trong GUI")
        else:
            logger.info("Tab Backtest đã tồn tại trong GUI, không cần cập nhật")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật mã GUI: {e}")

def main():
    """Hàm chính để cập nhật kết quả backtest vào giao diện desktop"""
    logger.info("Bắt đầu cập nhật kết quả backtest vào giao diện desktop")
    
    # Đảm bảo các thư mục cần thiết tồn tại
    ensure_directories()
    
    # Sao chép các file báo cáo
    copy_report_files()
    
    # Sao chép kết quả backtest
    copy_backtest_results()
    
    # Tạo file JSON tóm tắt
    create_backtest_summary_json()
    
    # Cập nhật file cấu hình GUI
    update_desktop_gui_config()
    
    # Cập nhật mã nguồn GUI
    update_gui_code()
    
    logger.info("Hoàn thành cập nhật kết quả backtest vào giao diện desktop")

if __name__ == "__main__":
    main()