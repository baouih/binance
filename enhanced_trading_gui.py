#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module giao diện desktop nâng cao
"""

import os
import sys
import json
import time
import logging
import traceback
from datetime import datetime, timedelta
from functools import partial
from typing import Dict, List, Tuple, Union, Any, Optional

# Thiết lập logging
logger = logging.getLogger("enhanced_trading_gui")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# PyQt5 imports
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QSizePolicy, QSplitter, QStatusBar, QToolBar, QAction, QMenu,
    QSystemTrayIcon, QStyle
)
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QDateTime, QSettings
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QCursor, QDesktopServices

# Import các modules cấu hình
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from configs.load_configs import load_all_configs, verify_configs, get_config_status_text
    logger.info("Đã import thành công module cấu hình")
except ImportError as e:
    logger.error(f"Lỗi khi import module cấu hình: {str(e)}")

# Import các module từ dự án
try:
    from market_analyzer import MarketAnalyzer
    from position_manager import PositionManager
    from risk_manager import RiskManager
    from market_scanner import get_scanner, MarketScanner
    logger.info("Đã import thành công các module từ dự án")
except ImportError as e:
    logger.error(f"Lỗi khi import module: {str(e)}")
    from typing import Any
    # Tạo các class giả trong trường hợp import thất bại

# CSS cho dark theme độ tương phản cao
HIGH_CONTRAST_DARK_THEME_CSS = """
    QMainWindow {
        background-color: #1F2937;
        color: #FFFFFF;
    }
    QTabWidget {
        background-color: #1F2937;
        color: #FFFFFF;
    }
    QTabWidget::pane {
        border: 1px solid #3B4252;
        background-color: #1F2937;
    }
    QTabBar::tab {
        background-color: #2D3748;
        color: white;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background-color: #4B5563;
        font-weight: bold;
        border-bottom: 2px solid #63B3ED;
    }
    QPushButton {
        background-color: #3B82F6;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2563EB;
    }
    QPushButton:pressed {
        background-color: #1D4ED8;
    }
    QMenuBar {
        background-color: #2D3748;
        color: #FFFFFF;
        padding: 4px;
        font-weight: bold;
        border-bottom: 1px solid #4A5568;
    }
    QMenuBar::item {
        background-color: transparent;
        padding: 6px 12px;
        color: #FFFFFF;
        font-weight: bold;
        border-radius: 4px;
        margin: 1px;
    }
    QMenuBar::item:selected {
        background-color: #4A5568;
        color: #FFFFFF;
        border: 1px solid #63B3ED;
    }
    QMenu {
        background-color: #2D3748;
        color: #FFFFFF;
        border: 1px solid #4A5568;
        padding: 4px;
    }
    QMenu::item {
        padding: 8px 24px;
        color: #FFFFFF;
        font-weight: bold;
        border-radius: 4px;
        margin: 2px;
    }
    QMenu::item:selected {
        background-color: #4A5568;
        color: #FFFFFF;
        border-left: 3px solid #63B3ED;
    }
    QMenu::separator {
        height: 1px;
        background-color: #4A5568;
        margin: 6px 0px;
    }
"""

# Tạo các class giả trong trường hợp import thất bại
class MarketAnalyzer:
    def __init__(self, *args, **kwargs):
        self.client = None
        logger.warning("Sử dụng lớp MarketAnalyzer giả")
    
    def get_market_overview(self):
        logger.warning("Gọi phương thức get_market_overview trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động", "data": []}
    
    def analyze_technical(self, *args, **kwargs):
        logger.warning("Gọi phương thức analyze_technical trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động", "data": {}}
    
class PositionManager:
    def __init__(self, *args, **kwargs):
        self.client = None
        logger.warning("Sử dụng lớp PositionManager giả")
    
    def get_all_positions(self):
        logger.warning("Gọi phương thức get_all_positions trong lớp giả")
        return []
    
    def get_account_balance(self):
        logger.warning("Gọi phương thức get_account_balance trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động", "balance": {}}
    
    def get_position_history(self):
        logger.warning("Gọi phương thức get_position_history trong lớp giả")
        return []
    
    def open_position(self, *args, **kwargs):
        logger.warning("Gọi phương thức open_position trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động"}
    
    def close_position(self, *args, **kwargs):
        logger.warning("Gọi phương thức close_position trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động"}
    
    def update_sl_tp(self, *args, **kwargs):
        logger.warning("Gọi phương thức update_sl_tp trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động"}
    
class RiskManager:
    def __init__(self, *args, **kwargs):
        self.risk_config = {}
        logger.warning("Sử dụng lớp RiskManager giả")
    
    def calculate_sl_tp(self, *args, **kwargs):
        logger.warning("Gọi phương thức calculate_sl_tp trong lớp giả")
        return {"stop_loss": 0, "take_profit": 0}
    
    def validate_sl_tp(self, *args, **kwargs):
        logger.warning("Gọi phương thức validate_sl_tp trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động"}
    
    def validate_new_position(self, *args, **kwargs):
        logger.warning("Gọi phương thức validate_new_position trong lớp giả")
        return {"status": "error", "message": "Chức năng không hoạt động"}
    
    def calculate_position_size(self, *args, **kwargs):
        logger.warning("Gọi phương thức calculate_position_size trong lớp giả")
        return 0.0

class RefreshThread(QThread):
    """Thread cập nhật dữ liệu theo thời gian thực"""
    signal = pyqtSignal(dict)
    
    def __init__(self, market_analyzer, position_manager, interval=10):
        """
        Khởi tạo thread cập nhật
        
        :param market_analyzer: Đối tượng MarketAnalyzer
        :param position_manager: Đối tượng PositionManager
        :param interval: Khoảng thời gian cập nhật (giây)
        """
        super().__init__()
        self.market_analyzer = market_analyzer
        self.position_manager = position_manager
        self.interval = interval
        self.running = True
    
    def run(self):
        """Chạy thread"""
        while self.running:
            try:
                # Lấy dữ liệu thị trường
                market_data = {}
                if self.market_analyzer:
                    market_overview = self.market_analyzer.get_market_overview()
                    if market_overview.get("status") == "success":
                        market_data["market_overview"] = market_overview.get("data", [])
                
                # Lấy danh sách vị thế
                positions = []
                if self.position_manager:
                    positions = self.position_manager.get_all_positions()
                market_data["positions"] = positions
                
                # Lấy số dư tài khoản
                account_balance = {}
                if self.position_manager:
                    account_info = self.position_manager.get_account_balance()
                    if account_info.get("status") == "success":
                        account_balance = account_info.get("balance", {})
                market_data["account_balance"] = account_balance
                
                # Phát tín hiệu với dữ liệu mới
                self.signal.emit(market_data)
            
            except Exception as e:
                logger.error(f"Lỗi trong thread cập nhật: {str(e)}", exc_info=True)
            
            # Ngủ theo khoảng thời gian cập nhật
            time.sleep(self.interval)
    
    def stop(self):
        """Dừng thread"""
        self.running = False
        self.wait()

class EnhancedTradingGUI(QMainWindow):
    """Giao diện đồ họa nâng cao cho giao dịch"""
    
    def __init__(self):
        """Khởi tạo giao diện đồ họa"""
        super().__init__()
        
        # Thiết lập thuộc tính cửa sổ
        self.setWindowTitle("Bot Giao Dịch Crypto - Phiên Bản Desktop")
        self.setGeometry(100, 100, 1024, 600)  # Kích thước có tỷ lệ 16:9, nhỏ gọn hơn
        
        # Thiết lập icon
        self.setWindowIcon(QIcon("static/icons/app_icon.png"))
        
        # Tạo stylesheet chung cho ứng dụng
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1F2937;
                color: white;
            }
            QTabWidget {
                background-color: #1F2937;
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #3B4252;
                background-color: #1F2937;
            }
            QTabBar::tab {
                background-color: #2D3748;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4B5563;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QTableWidget {
                background-color: #1F2937;
                color: white;
                gridline-color: #4B5563;
                border: 1px solid #4B5563;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #2D3748;
                color: white;
                padding: 4px;
                border: 1px solid #4B5563;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #2D3748;
                border: 1px solid #4B5563;
            }
            QLabel {
                color: white;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #374151;
                color: white;
                border: 1px solid #4B5563;
                border-radius: 4px;
                padding: 4px;
            }
            QGroupBox {
                border: 1px solid #4B5563;
                border-radius: 4px;
                margin-top: 8px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
            }
            QDialog {
                background-color: #1F2937;
                color: white;
            }
            QMessageBox {
                background-color: #1F2937;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                background-color: transparent;
            }
            QTextEdit {
                background-color: #374151;
                color: white;
                border: 1px solid #4B5563;
                border-radius: 4px;
            }
            QCheckBox {
                color: white;
            }
            QRadioButton {
                color: white;
            }
            QScrollBar:vertical {
                background-color: #1F2937;
                width: 14px;
                margin: 14px 0px 14px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4B5563;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical {
                background-color: #2D3748;
                height: 14px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical {
                background-color: #2D3748;
                height: 14px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            /* Thêm màu chữ cho tất cả các widget con */
            * {
                color: white;
            }
        """)
        
        # Khởi tạo các đối tượng
        self.init_objects()
        
        # Thiết lập giao diện
        self.init_ui()
        
        # Khởi tạo thread cập nhật
        self.init_refresh_thread()
        
        # Kết nối các sự kiện
        self.connect_events()
        
        # Tải cấu hình
        self.load_config()
    
    def init_objects(self):
        """Khởi tạo các đối tượng cần thiết"""
        try:
            # Kiểm tra các khóa API
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            if not api_key or not api_secret:
                self.show_missing_api_keys_error()
            
            # Tải cấu hình rủi ro từ file
            risk_config = self.load_risk_config()
            
            # Khởi tạo các đối tượng thực (không sử dụng lớp giả)
            try:
                from market_analyzer import MarketAnalyzer as RealMarketAnalyzer
                self.market_analyzer = RealMarketAnalyzer(testnet=True)
                logger.info("Đã khởi tạo MarketAnalyzer thực")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Market Analyzer thực: {str(e)}")
                # Sử dụng lớp giả chỉ khi lớp thực không hoạt động
                self.market_analyzer = self.create_mock_market_analyzer()
                logger.warning("Sử dụng lớp MarketAnalyzer giả")
            
            try:
                from position_manager import PositionManager as RealPositionManager
                self.position_manager = RealPositionManager(testnet=True)
                logger.info("Đã khởi tạo PositionManager thực")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Position Manager thực: {str(e)}")
                # Sử dụng lớp giả chỉ khi lớp thực không hoạt động
                self.position_manager = self.create_mock_position_manager()
                logger.warning("Sử dụng lớp PositionManager giả")
            
            try:
                from risk_manager import RiskManager as RealRiskManager
                self.risk_manager = RealRiskManager(self.position_manager, risk_config)
                logger.info("Đã khởi tạo RiskManager thực")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo Risk Manager thực: {str(e)}")
                # Sử dụng lớp giả chỉ khi lớp thực không hoạt động
                self.risk_manager = self.create_mock_risk_manager(risk_config)
                logger.warning("Sử dụng lớp RiskManager giả")
            
            # Khởi tạo Scanner thị trường
            try:
                from market_scanner import get_scanner
                self.market_scanner = get_scanner(testnet=True)
                logger.info("Đã khởi tạo Market Scanner thực")
            except Exception as e:
                logger.error(f"Lỗi khi khởi tạo market_scanner: {str(e)}")
                self.market_scanner = None
                logger.warning("Market Scanner không khả dụng")
            
            # Thử kết nối API
            self.test_api_connection()
            
            logger.info("Đã khởi tạo các đối tượng")
        
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo các đối tượng: {str(e)}", exc_info=True)
            # Khởi tạo các lớp giả nếu có lỗi
            self.market_analyzer = self.create_mock_market_analyzer()
            self.position_manager = self.create_mock_position_manager()
            self.risk_manager = self.create_mock_risk_manager({})
            self.market_scanner = None
    
    def load_risk_config(self) -> Dict[str, Any]:
        """
        Tải cấu hình rủi ro từ file
        
        :return: Dict với cấu hình rủi ro
        """
        try:
            # Tải cấu hình từ file
            config_file = "risk_configs/desktop_risk_config.json"
            
            # Kiểm tra xem file có tồn tại không
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    risk_config = json.load(f)
                logger.info(f"Đã tải cấu hình rủi ro từ {config_file}")
                return risk_config
            else:
                # Sử dụng cấu hình mặc định
                risk_config = {
                    "risk_percentage": 0.01,  # 1% rủi ro trên mỗi giao dịch
                    "max_positions": 5,  # Số lượng vị thế tối đa
                    "leverage": 5,  # Đòn bẩy mặc định
                    "position_size_percentage": 0.1,  # 10% số dư cho mỗi vị thế
                    "partial_take_profit": {
                        "enabled": False,
                        "levels": [
                            {"percentage": 30, "profit_percentage": 2},
                            {"percentage": 30, "profit_percentage": 5},
                            {"percentage": 40, "profit_percentage": 10}
                        ]
                    },
                    "stop_loss_percentage": 0.015,  # 1.5% Stop Loss
                    "take_profit_percentage": 0.03,  # 3% Take Profit
                    "trailing_stop": {
                        "enabled": True,
                        "activation_percentage": 2,
                        "trailing_percentage": 1.5
                    },
                    "trading_hours_restriction": {
                        "enabled": False,
                        "trading_hours": ["09:00-12:00", "14:00-21:00"]
                    }
                }
                
                # Tạo thư mục nếu chưa tồn tại
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                
                # Lưu cấu hình mặc định
                with open(config_file, "w") as f:
                    json.dump(risk_config, f, indent=4)
                
                logger.info(f"Đã tạo cấu hình rủi ro mặc định tại {config_file}")
                return risk_config
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro: {str(e)}", exc_info=True)
            # Trả về cấu hình mặc định
            return {}
    
    def init_ui(self):
        """Thiết lập giao diện người dùng"""
        # Tạo widget trung tâm và layout chính
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tạo toolbar
        self.create_toolbar()
        
        # Tạo tab container
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Tạo các tab
        self.create_dashboard_tab()
        self.create_trading_tab()
        self.create_positions_tab()
        self.create_market_analysis_tab()
        self.create_settings_tab()
        self.create_system_management_tab()
        
        # Tạo thanh trạng thái
        self.create_status_bar()
    
    def create_toolbar(self):
        """Tạo thanh công cụ"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Nút refresh dữ liệu
        refresh_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_BrowserReload)), "Cập nhật dữ liệu", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # Nút đăng nhập/tài khoản
        account_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton)), "Tài khoản", self)
        account_action.triggered.connect(self.show_account_info)
        toolbar.addAction(account_action)
        
        # Nút cài đặt
        settings_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView)), "Cài đặt", self)
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(4))  # Chuyển đến tab cài đặt
        toolbar.addAction(settings_action)
        
        # Nút cập nhật phần mềm
        update_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_ArrowUp)), "Cập nhật phần mềm", self)
        update_action.triggered.connect(self.check_software_update)
        toolbar.addAction(update_action)
        
        # Nút trợ giúp
        help_action = QAction(QIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion)), "Trợ giúp", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)
        
        # Thêm spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)
        
        # Đọc phiên bản từ file
        try:
            version = "1.0.0"
            if os.path.exists("version.txt"):
                with open("version.txt", "r") as f:
                    version = f.read().strip()
        except:
            version = "1.0.0"
        
        # Hiển thị thông tin phiên bản
        self.version_label = QLabel(f"Phiên bản {version}")
        toolbar.addWidget(self.version_label)
    
    def create_dashboard_tab(self):
        """Tạo tab tổng quan"""
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # Tạo layout tổng quát compact hơn
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(5)
        
        # Tạo phần trên hiển thị số dư tài khoản và thị trường (compact hơn)
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(5, 5, 5, 5)
        top_layout.setSpacing(10)
        
        # PHẦN TÀI KHOẢN - Thông tin chi tiết hơn
        account_widget = QWidget()
        account_layout = QGridLayout(account_widget)
        account_layout.setContentsMargins(2, 2, 2, 2)
        account_layout.setVerticalSpacing(2)
        account_layout.setHorizontalSpacing(10)
        
        # Tiêu đề tài khoản
        account_title = QLabel("Số dư tài khoản")
        account_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #63B3ED;")
        account_layout.addWidget(account_title, 0, 0, 1, 2)
        
        # Các thành phần hiển thị số dư - Gọn hơn và chi tiết hơn
        account_layout.addWidget(QLabel("Tổng số dư:"), 1, 0)
        self.total_balance_label = QLabel("0.00 USDT")
        self.total_balance_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        account_layout.addWidget(self.total_balance_label, 1, 1)
        
        account_layout.addWidget(QLabel("Số dư khả dụng:"), 2, 0)
        self.available_balance_label = QLabel("0.00 USDT")
        self.available_balance_label.setStyleSheet("font-size: 10px;")
        account_layout.addWidget(self.available_balance_label, 2, 1)
        
        account_layout.addWidget(QLabel("Lợi nhuận:"), 3, 0)
        self.unrealized_pnl_label = QLabel("0.00 USDT")
        self.unrealized_pnl_label.setStyleSheet("font-size: 10px;")
        account_layout.addWidget(self.unrealized_pnl_label, 3, 1)
        
        account_layout.addWidget(QLabel("Tỷ lệ ROE:"), 4, 0)
        self.roe_label = QLabel("0.00%")
        self.roe_label.setStyleSheet("font-size: 10px;")
        account_layout.addWidget(self.roe_label, 4, 1)
        
        account_layout.addWidget(QLabel("Tổng vốn:"), 5, 0)
        self.total_margin_label = QLabel("0.00 USDT")
        self.total_margin_label.setStyleSheet("font-size: 10px;")
        account_layout.addWidget(self.total_margin_label, 5, 1)
        
        # PHẦN THỊ TRƯỜNG - Hiển thị nhiều thông tin xu hướng
        market_widget = QWidget()
        market_layout = QGridLayout(market_widget)
        market_layout.setContentsMargins(2, 2, 2, 2)
        market_layout.setVerticalSpacing(2)
        market_layout.setHorizontalSpacing(10)
        
        # Tiêu đề thị trường
        market_title = QLabel("Thông tin thị trường")
        market_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #63B3ED;")
        market_layout.addWidget(market_title, 0, 0, 1, 2)
        
        # Thông tin chi tiết hơn về thị trường chính
        market_layout.addWidget(QLabel("BTC:"), 1, 0)
        self.btc_price_label = QLabel("0.00 USDT")
        self.btc_price_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        market_layout.addWidget(self.btc_price_label, 1, 1)
        
        market_layout.addWidget(QLabel("24h:"), 2, 0)
        self.btc_change_label = QLabel("0.00%")
        self.btc_change_label.setStyleSheet("font-size: 10px;")
        market_layout.addWidget(self.btc_change_label, 2, 1)
        
        market_layout.addWidget(QLabel("ETH:"), 3, 0)
        self.eth_price_label = QLabel("0.00 USDT")
        self.eth_price_label.setStyleSheet("font-size: 10px;")
        market_layout.addWidget(self.eth_price_label, 3, 1)
        
        market_layout.addWidget(QLabel("SOL:"), 4, 0)
        self.sol_price_label = QLabel("0.00 USDT")
        self.sol_price_label.setStyleSheet("font-size: 10px;")
        market_layout.addWidget(self.sol_price_label, 4, 1)
        
        market_layout.addWidget(QLabel("Dominance:"), 5, 0)
        self.btc_dominance_label = QLabel("0.00%")
        self.btc_dominance_label.setStyleSheet("font-size: 10px;")
        market_layout.addWidget(self.btc_dominance_label, 5, 1)
        
        # PHẦN ĐIỀU KHIỂN - Đặt nút ở phần riêng
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setContentsMargins(2, 2, 2, 2)
        control_layout.setSpacing(5)
        
        # Tiêu đề điều khiển
        control_title = QLabel("Điều khiển")
        control_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #63B3ED;")
        control_layout.addWidget(control_title)
        
        # Nút Auto Trading nhỏ gọn hơn
        self.auto_trading_button = QPushButton("Kích hoạt Auto Trading")
        self.auto_trading_button.setStyleSheet("""
            background-color: #22C55E;
            color: white;
            font-weight: bold;
            font-size: 11px;
            padding: 6px 10px;
            border-radius: 4px;
        """)
        self.auto_trading_button.clicked.connect(lambda: self.start_service("unified_trading_service"))
        control_layout.addWidget(self.auto_trading_button)
        
        # Nút quét thị trường
        self.scan_market_button = QPushButton("Quét thị trường")
        self.scan_market_button.setStyleSheet("""
            background-color: #3B82F6;
            color: white;
            font-weight: bold;
            font-size: 11px;
            padding: 6px 10px;
            border-radius: 4px;
        """)
        self.scan_market_button.clicked.connect(lambda: self.start_service("market_scanner"))
        control_layout.addWidget(self.scan_market_button)
        
        # Thêm các widget vào layout trên
        top_layout.addWidget(account_widget, 3) # Tỷ lệ 3
        top_layout.addWidget(market_widget, 3)  # Tỷ lệ 3
        top_layout.addWidget(control_widget, 2) # Tỷ lệ 2
        
        # Thêm widget trên vào layout chính
        layout.addWidget(top_widget, 1)
        
        # Tạo phần hiển thị các vị thế đang mở - Phần này nhỏ gọn hơn
        positions_group = QGroupBox("Vị thế đang mở")
        positions_group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; }")
        positions_layout = QVBoxLayout(positions_group)
        positions_layout.setContentsMargins(3, 10, 3, 3)
        positions_layout.setSpacing(2)
        
        self.positions_table = QTableWidget(0, 8)
        self.positions_table.setHorizontalHeaderLabels([
            "Cặp", "Hướng", "Size", "Giá vào", "Giá hiện tại", "SL", "TP", "P/L"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.positions_table.setStyleSheet("font-size: 10px;")
        self.positions_table.verticalHeader().setDefaultSectionSize(20) # Giảm chiều cao các dòng
        positions_layout.addWidget(self.positions_table)
        
        # Thêm phần vị thế vào layout chính
        layout.addWidget(positions_group, 2)
        
        # Tạo phần hiển thị thị trường - Hiển thị nhiều cặp hơn
        market_group = QGroupBox("Top 10 cặp tiền")
        market_group.setStyleSheet("QGroupBox { font-size: 11px; font-weight: bold; }")
        market_layout = QVBoxLayout(market_group)
        market_layout.setContentsMargins(3, 10, 3, 3)
        market_layout.setSpacing(2)
        
        self.market_table = QTableWidget(0, 5)
        self.market_table.setHorizontalHeaderLabels([
            "Cặp", "Giá", "Thay đổi 24h", "Vol 24h (USDT)", "Tín hiệu"
        ])
        self.market_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.market_table.setStyleSheet("font-size: 10px;")
        self.market_table.verticalHeader().setDefaultSectionSize(20) # Giảm chiều cao các dòng
        market_layout.addWidget(self.market_table)
        
        # Thêm phần thị trường vào layout chính
        layout.addWidget(market_group, 2)
        
        # Thêm tab vào container
        self.tab_widget.addTab(dashboard_tab, "Tổng quan")
    
    def create_trading_tab(self):
        """Tạo tab giao dịch"""
        trading_tab = QWidget()
        layout = QHBoxLayout(trading_tab)
        
        # Tạo khung giao dịch bên trái
        trading_frame = QWidget()
        trading_layout = QVBoxLayout(trading_frame)
        
        # Tạo form nhập thông tin giao dịch
        form_group = QGroupBox("Đặt lệnh mới")
        form_layout = QFormLayout(form_group)
        
        # Chọn cặp giao dịch
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems([
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", 
            "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT"
        ])
        form_layout.addRow("Cặp giao dịch:", self.symbol_combo)
        
        # Chọn hướng giao dịch
        self.side_combo = QComboBox()
        self.side_combo.addItems(["LONG", "SHORT"])
        form_layout.addRow("Hướng giao dịch:", self.side_combo)
        
        # Nhập kích thước vị thế
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setDecimals(3)
        self.amount_spin.setMinimum(0.001)
        self.amount_spin.setMaximum(100.0)
        self.amount_spin.setValue(0.01)
        form_layout.addRow("Kích thước:", self.amount_spin)
        
        # Đòn bẩy
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setMinimum(1)
        self.leverage_spin.setMaximum(20)
        self.leverage_spin.setValue(5)
        form_layout.addRow("Đòn bẩy:", self.leverage_spin)
        
        # Stop Loss
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setDecimals(2)
        self.stop_loss_spin.setMinimum(0.0)
        self.stop_loss_spin.setMaximum(100000.0)
        self.stop_loss_checkbox = QCheckBox("Tự động")
        self.stop_loss_checkbox.setChecked(True)
        self.stop_loss_spin.setEnabled(False)
        
        sl_layout = QHBoxLayout()
        sl_layout.addWidget(self.stop_loss_spin)
        sl_layout.addWidget(self.stop_loss_checkbox)
        form_layout.addRow("Stop Loss:", sl_layout)
        
        # Take Profit
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setDecimals(2)
        self.take_profit_spin.setMinimum(0.0)
        self.take_profit_spin.setMaximum(100000.0)
        self.take_profit_checkbox = QCheckBox("Tự động")
        self.take_profit_checkbox.setChecked(True)
        self.take_profit_spin.setEnabled(False)
        
        tp_layout = QHBoxLayout()
        tp_layout.addWidget(self.take_profit_spin)
        tp_layout.addWidget(self.take_profit_checkbox)
        form_layout.addRow("Take Profit:", tp_layout)
        
        trading_layout.addWidget(form_group)
        
        # Nút đặt lệnh
        buttons_layout = QHBoxLayout()
        
        self.calculate_button = QPushButton("Tính toán vị thế")
        self.calculate_button.clicked.connect(self.calculate_position)
        buttons_layout.addWidget(self.calculate_button)
        
        self.open_long_button = QPushButton("Mở Long")
        self.open_long_button.setStyleSheet("background-color: #22C55E; color: white; font-weight: bold;")
        self.open_long_button.clicked.connect(lambda: self.open_position("LONG"))
        buttons_layout.addWidget(self.open_long_button)
        
        self.open_short_button = QPushButton("Mở Short")
        self.open_short_button.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold;")
        self.open_short_button.clicked.connect(lambda: self.open_position("SHORT"))
        buttons_layout.addWidget(self.open_short_button)
        
        trading_layout.addLayout(buttons_layout)
        
        # Tạo khung thông tin giao dịch
        info_group = QGroupBox("Thông tin giao dịch")
        info_layout = QFormLayout(info_group)
        
        self.current_price_label = QLabel("0.00 USDT")
        info_layout.addRow("Giá hiện tại:", self.current_price_label)
        
        self.position_value_label = QLabel("0.00 USDT")
        info_layout.addRow("Giá trị vị thế:", self.position_value_label)
        
        self.margin_required_label = QLabel("0.00 USDT")
        info_layout.addRow("Margin yêu cầu:", self.margin_required_label)
        
        self.risk_percentage_label = QLabel("0.00%")
        info_layout.addRow("Phần trăm rủi ro:", self.risk_percentage_label)
        
        self.liquidation_price_label = QLabel("0.00 USDT")
        info_layout.addRow("Giá thanh lý:", self.liquidation_price_label)
        
        trading_layout.addWidget(info_group)
        
        # Thêm các widget vào layout
        layout.addWidget(trading_frame, 1)
        
        # Tạo khung phân tích thị trường bên phải
        analysis_frame = QWidget()
        analysis_layout = QVBoxLayout(analysis_frame)
        
        # Chọn cặp để phân tích
        analysis_symbol_layout = QHBoxLayout()
        self.analysis_symbol_combo = QComboBox()
        self.analysis_symbol_combo.addItems([
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", 
            "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT"
        ])
        analysis_symbol_layout.addWidget(QLabel("Cặp:"))
        analysis_symbol_layout.addWidget(self.analysis_symbol_combo)
        
        self.analysis_interval_combo = QComboBox()
        self.analysis_interval_combo.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.analysis_interval_combo.setCurrentText("1h")
        analysis_symbol_layout.addWidget(QLabel("Khung thời gian:"))
        analysis_symbol_layout.addWidget(self.analysis_interval_combo)
        
        self.analyze_button = QPushButton("Phân tích")
        self.analyze_button.clicked.connect(self.analyze_market)
        analysis_symbol_layout.addWidget(self.analyze_button)
        
        analysis_layout.addLayout(analysis_symbol_layout)
        
        # Kết quả phân tích
        analysis_result_group = QGroupBox("Kết quả phân tích kỹ thuật")
        analysis_result_layout = QVBoxLayout(analysis_result_group)
        
        self.analysis_result_text = QTextEdit()
        self.analysis_result_text.setReadOnly(True)
        analysis_result_layout.addWidget(self.analysis_result_text)
        
        analysis_layout.addWidget(analysis_result_group)
        
        # Tín hiệu giao dịch
        signals_group = QGroupBox("Tín hiệu giao dịch")
        signals_layout = QGridLayout(signals_group)
        
        self.signal_label = QLabel("N/A")
        self.signal_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        signals_layout.addWidget(QLabel("Tín hiệu:"), 0, 0)
        signals_layout.addWidget(self.signal_label, 0, 1)
        
        self.strength_label = QLabel("N/A")
        signals_layout.addWidget(QLabel("Độ mạnh:"), 1, 0)
        signals_layout.addWidget(self.strength_label, 1, 1)
        
        self.trend_label = QLabel("N/A")
        signals_layout.addWidget(QLabel("Xu hướng:"), 2, 0)
        signals_layout.addWidget(self.trend_label, 2, 1)
        
        analysis_layout.addWidget(signals_group)
        
        # Thêm các widget vào layout
        layout.addWidget(analysis_frame, 1)
        
        # Thêm tab vào container
        self.tab_widget.addTab(trading_tab, "Giao dịch")
    
    def create_positions_tab(self):
        """Tạo tab quản lý vị thế"""
        positions_tab = QWidget()
        layout = QVBoxLayout(positions_tab)
        
        # Tạo bảng vị thế
        self.positions_detail_table = QTableWidget(0, 9)
        self.positions_detail_table.setHorizontalHeaderLabels([
            "Cặp", "Hướng", "Kích thước", "Giá vào", "Giá hiện tại", "SL", "TP", "Lợi nhuận", "Thao tác"
        ])
        self.positions_detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.positions_detail_table)
        
        # Tạo phần quản lý vị thế
        management_group = QGroupBox("Quản lý vị thế")
        management_layout = QFormLayout(management_group)
        
        # Chọn vị thế để quản lý
        self.manage_symbol_combo = QComboBox()
        management_layout.addRow("Cặp giao dịch:", self.manage_symbol_combo)
        
        # Cập nhật Stop Loss và Take Profit
        self.manage_sl_spin = QDoubleSpinBox()
        self.manage_sl_spin.setDecimals(2)
        self.manage_sl_spin.setMinimum(0.0)
        self.manage_sl_spin.setMaximum(100000.0)
        management_layout.addRow("Stop Loss mới:", self.manage_sl_spin)
        
        self.manage_tp_spin = QDoubleSpinBox()
        self.manage_tp_spin.setDecimals(2)
        self.manage_tp_spin.setMinimum(0.0)
        self.manage_tp_spin.setMaximum(100000.0)
        management_layout.addRow("Take Profit mới:", self.manage_tp_spin)
        
        # Tạo các nút quản lý
        manage_buttons_layout = QHBoxLayout()
        
        self.update_sltp_button = QPushButton("Cập nhật SL/TP")
        self.update_sltp_button.clicked.connect(self.update_sltp)
        manage_buttons_layout.addWidget(self.update_sltp_button)
        
        self.close_position_button = QPushButton("Đóng vị thế")
        self.close_position_button.clicked.connect(self.close_position)
        self.close_position_button.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold;")
        manage_buttons_layout.addWidget(self.close_position_button)
        
        management_layout.addRow("", manage_buttons_layout)
        
        layout.addWidget(management_group)
        
        # Tạo phần lịch sử giao dịch
        history_group = QGroupBox("Lịch sử giao dịch")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels([
            "Cặp", "Hướng", "Giá", "Kích thước", "Phí", "Lợi nhuận", "Thời gian"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_layout.addWidget(self.history_table)
        
        self.refresh_history_button = QPushButton("Cập nhật lịch sử")
        self.refresh_history_button.clicked.connect(self.refresh_history)
        history_layout.addWidget(self.refresh_history_button)
        
        layout.addWidget(history_group)
        
        # Thêm tab vào container
        self.tab_widget.addTab(positions_tab, "Quản lý vị thế")
    
    def create_market_analysis_tab(self):
        """Tạo tab phân tích thị trường"""
        market_tab = QWidget()
        layout = QVBoxLayout(market_tab)
        
        # Tạo phần thông tin thị trường
        market_info_layout = QHBoxLayout()
        
        # Chọn cặp để phân tích
        self.market_symbol_combo = QComboBox()
        self.market_symbol_combo.addItems([
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT", 
            "ADAUSDT", "XRPUSDT", "DOTUSDT", "LTCUSDT", "AVAXUSDT"
        ])
        market_info_layout.addWidget(QLabel("Cặp:"))
        market_info_layout.addWidget(self.market_symbol_combo)
        
        self.market_interval_combo = QComboBox()
        self.market_interval_combo.addItems(["1m", "5m", "15m", "1h", "4h", "1d"])
        self.market_interval_combo.setCurrentText("1h")
        market_info_layout.addWidget(QLabel("Khung thời gian:"))
        market_info_layout.addWidget(self.market_interval_combo)
        
        self.market_analyze_button = QPushButton("Phân tích")
        self.market_analyze_button.clicked.connect(self.analyze_market_detail)
        market_info_layout.addWidget(self.market_analyze_button)
        
        layout.addLayout(market_info_layout)
        
        # Tạo phần hiển thị kết quả phân tích
        analysis_detail_widget = QSplitter(Qt.Horizontal)
        
        # Phần trái: chỉ báo kỹ thuật
        indicators_group = QGroupBox("Chỉ báo kỹ thuật")
        indicators_layout = QVBoxLayout(indicators_group)
        
        self.indicators_table = QTableWidget(0, 3)
        self.indicators_table.setHorizontalHeaderLabels([
            "Chỉ báo", "Giá trị", "Tín hiệu"
        ])
        self.indicators_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        indicators_layout.addWidget(self.indicators_table)
        
        analysis_detail_widget.addWidget(indicators_group)
        
        # Phần phải: thông tin chi tiết
        detail_group = QGroupBox("Thông tin chi tiết")
        detail_layout = QVBoxLayout(detail_group)
        
        self.market_detail_text = QTextEdit()
        self.market_detail_text.setReadOnly(True)
        detail_layout.addWidget(self.market_detail_text)
        
        analysis_detail_widget.addWidget(detail_group)
        
        layout.addWidget(analysis_detail_widget)
        
        # Tạo phần hỗ trợ/kháng cự
        support_resistance_group = QGroupBox("Mức hỗ trợ và kháng cự")
        support_resistance_layout = QVBoxLayout(support_resistance_group)
        
        self.support_resistance_table = QTableWidget(0, 2)
        self.support_resistance_table.setHorizontalHeaderLabels([
            "Loại", "Giá trị"
        ])
        self.support_resistance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        support_resistance_layout.addWidget(self.support_resistance_table)
        
        layout.addWidget(support_resistance_group)
        
        # Tạo phần xu hướng thị trường
        trend_group = QGroupBox("Xu hướng thị trường")
        trend_layout = QGridLayout(trend_group)
        
        self.short_term_trend_label = QLabel("N/A")
        trend_layout.addWidget(QLabel("Ngắn hạn:"), 0, 0)
        trend_layout.addWidget(self.short_term_trend_label, 0, 1)
        
        self.mid_term_trend_label = QLabel("N/A")
        trend_layout.addWidget(QLabel("Trung hạn:"), 0, 2)
        trend_layout.addWidget(self.mid_term_trend_label, 0, 3)
        
        self.long_term_trend_label = QLabel("N/A")
        trend_layout.addWidget(QLabel("Dài hạn:"), 0, 4)
        trend_layout.addWidget(self.long_term_trend_label, 0, 5)
        
        layout.addWidget(trend_group)
        
        # Thêm tab vào container
        self.tab_widget.addTab(market_tab, "Phân tích thị trường")
    
    def create_settings_tab(self):
        """Tạo tab cài đặt"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # Tạo phần cài đặt API
        api_group = QGroupBox("Cài đặt API")
        api_layout = QFormLayout(api_group)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Key:", self.api_key_edit)
        
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        api_layout.addRow("API Secret:", self.api_secret_edit)
        
        self.testnet_checkbox = QCheckBox("Sử dụng testnet")
        self.testnet_checkbox.setChecked(True)
        api_layout.addRow("", self.testnet_checkbox)
        
        api_button_layout = QHBoxLayout()
        save_api_button = QPushButton("Lưu cài đặt API")
        save_api_button.clicked.connect(self.save_api_settings)
        test_api_button = QPushButton("Kiểm tra kết nối")
        test_api_button.clicked.connect(self.test_api_connection)
        api_button_layout.addWidget(save_api_button)
        api_button_layout.addWidget(test_api_button)
        api_layout.addRow("", api_button_layout)
        
        layout.addWidget(api_group)
        
        # Tạo phần cài đặt Telegram
        telegram_group = QGroupBox("Cài đặt thông báo Telegram")
        telegram_layout = QFormLayout(telegram_group)
        
        self.telegram_token_edit = QLineEdit()
        self.telegram_token_edit.setEchoMode(QLineEdit.Password)
        self.telegram_token_edit.setPlaceholderText("Nhập Bot Token")
        telegram_layout.addRow("Bot Token:", self.telegram_token_edit)
        
        self.telegram_chat_id_edit = QLineEdit()
        self.telegram_chat_id_edit.setPlaceholderText("Nhập Chat ID")
        telegram_layout.addRow("Chat ID:", self.telegram_chat_id_edit)
        
        telegram_button_layout = QHBoxLayout()
        save_telegram_button = QPushButton("Lưu cài đặt Telegram")
        save_telegram_button.clicked.connect(self.save_telegram_settings)
        test_telegram_button = QPushButton("Kiểm tra kết nối")
        test_telegram_button.clicked.connect(self.test_telegram_connection)
        telegram_button_layout.addWidget(save_telegram_button)
        telegram_button_layout.addWidget(test_telegram_button)
        telegram_layout.addRow("", telegram_button_layout)
        
        telegram_help_text = QLabel("Hướng dẫn thiết lập Telegram Bot:")
        telegram_help_text.setTextFormat(Qt.RichText)
        telegram_help_text.setWordWrap(True)
        telegram_layout.addRow(telegram_help_text)
        
        telegram_steps = QLabel(
            "1. Tìm @BotFather trên Telegram<br>"
            "2. Gửi lệnh /newbot và làm theo hướng dẫn<br>"
            "3. Sao chép Bot Token được cung cấp<br>"
            "4. Chat với bot của bạn hoặc thêm vào group<br>"
            "5. Truy cập api.telegram.org/botXXX:YYY/getUpdates<br>"
            "   (thay XXX:YYY bằng token của bạn)<br>"
            "6. Sao chép chat_id từ phản hồi JSON"
        )
        telegram_steps.setTextFormat(Qt.RichText)
        telegram_steps.setWordWrap(True)
        telegram_layout.addRow(telegram_steps)
        
        notification_options_box = QGroupBox("Tùy chọn thông báo")
        notification_options_layout = QVBoxLayout()
        
        self.notify_position_checkbox = QCheckBox("Thông báo khi mở/đóng vị thế")
        self.notify_position_checkbox.setChecked(True)
        notification_options_layout.addWidget(self.notify_position_checkbox)
        
        self.notify_sltp_checkbox = QCheckBox("Thông báo khi cập nhật SL/TP")
        self.notify_sltp_checkbox.setChecked(True)
        notification_options_layout.addWidget(self.notify_sltp_checkbox)
        
        self.notify_opportunity_checkbox = QCheckBox("Thông báo cơ hội giao dịch")
        self.notify_opportunity_checkbox.setChecked(True)
        notification_options_layout.addWidget(self.notify_opportunity_checkbox)
        
        self.notify_error_checkbox = QCheckBox("Thông báo lỗi hệ thống")
        self.notify_error_checkbox.setChecked(True)
        notification_options_layout.addWidget(self.notify_error_checkbox)
        
        self.notify_summary_checkbox = QCheckBox("Gửi báo cáo tổng kết hàng ngày")
        self.notify_summary_checkbox.setChecked(True)
        notification_options_layout.addWidget(self.notify_summary_checkbox)
        
        notification_options_box.setLayout(notification_options_layout)
        telegram_layout.addRow(notification_options_box)
        
        layout.addWidget(telegram_group)
        
        # Tạo phần cài đặt rủi ro
        risk_group = QGroupBox("Cài đặt rủi ro")
        risk_layout = QFormLayout(risk_group)
        
        self.risk_percentage_spin = QDoubleSpinBox()
        self.risk_percentage_spin.setDecimals(2)
        self.risk_percentage_spin.setMinimum(0.1)
        self.risk_percentage_spin.setMaximum(10.0)
        self.risk_percentage_spin.setValue(1.0)
        self.risk_percentage_spin.setSuffix("%")
        risk_layout.addRow("Phần trăm rủi ro:", self.risk_percentage_spin)
        
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setMinimum(1)
        self.max_positions_spin.setMaximum(20)
        self.max_positions_spin.setValue(5)
        risk_layout.addRow("Số lượng vị thế tối đa:", self.max_positions_spin)
        
        self.default_leverage_spin = QSpinBox()
        self.default_leverage_spin.setMinimum(1)
        self.default_leverage_spin.setMaximum(20)
        self.default_leverage_spin.setValue(5)
        risk_layout.addRow("Đòn bẩy mặc định:", self.default_leverage_spin)
        
        self.position_size_percentage_spin = QDoubleSpinBox()
        self.position_size_percentage_spin.setDecimals(2)
        self.position_size_percentage_spin.setMinimum(1.0)
        self.position_size_percentage_spin.setMaximum(50.0)
        self.position_size_percentage_spin.setValue(10.0)
        self.position_size_percentage_spin.setSuffix("%")
        risk_layout.addRow("Phần trăm số dư cho mỗi vị thế:", self.position_size_percentage_spin)
        
        self.stop_loss_percentage_spin = QDoubleSpinBox()
        self.stop_loss_percentage_spin.setDecimals(2)
        self.stop_loss_percentage_spin.setMinimum(0.5)
        self.stop_loss_percentage_spin.setMaximum(10.0)
        self.stop_loss_percentage_spin.setValue(1.5)
        self.stop_loss_percentage_spin.setSuffix("%")
        risk_layout.addRow("Phần trăm Stop Loss:", self.stop_loss_percentage_spin)
        
        self.take_profit_percentage_spin = QDoubleSpinBox()
        self.take_profit_percentage_spin.setDecimals(2)
        self.take_profit_percentage_spin.setMinimum(0.5)
        self.take_profit_percentage_spin.setMaximum(20.0)
        self.take_profit_percentage_spin.setValue(3.0)
        self.take_profit_percentage_spin.setSuffix("%")
        risk_layout.addRow("Phần trăm Take Profit:", self.take_profit_percentage_spin)
        
        self.trailing_stop_checkbox = QCheckBox("Bật Trailing Stop")
        self.trailing_stop_checkbox.setChecked(True)
        risk_layout.addRow("", self.trailing_stop_checkbox)
        
        self.partial_tp_checkbox = QCheckBox("Bật chốt lời một phần")
        self.partial_tp_checkbox.setChecked(False)
        risk_layout.addRow("", self.partial_tp_checkbox)
        
        self.trading_hours_checkbox = QCheckBox("Giới hạn giờ giao dịch")
        self.trading_hours_checkbox.setChecked(False)
        risk_layout.addRow("", self.trading_hours_checkbox)
        
        self.save_risk_button = QPushButton("Lưu cài đặt rủi ro")
        self.save_risk_button.clicked.connect(self.save_risk_settings)
        risk_layout.addRow("", self.save_risk_button)
        
        layout.addWidget(risk_group)
        
        # Tạo phần cài đặt giao diện
        ui_group = QGroupBox("Cài đặt giao diện")
        ui_layout = QFormLayout(ui_group)
        
        self.dark_mode_checkbox = QCheckBox("Chế độ tối")
        self.dark_mode_checkbox.setChecked(False)
        self.dark_mode_checkbox.toggled.connect(self.toggle_dark_mode)
        ui_layout.addRow("", self.dark_mode_checkbox)
        
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setMinimum(5)
        self.refresh_interval_spin.setMaximum(60)
        self.refresh_interval_spin.setValue(10)
        self.refresh_interval_spin.setSuffix(" giây")
        ui_layout.addRow("Thời gian cập nhật:", self.refresh_interval_spin)
        
        self.notifications_checkbox = QCheckBox("Bật thông báo")
        self.notifications_checkbox.setChecked(True)
        ui_layout.addRow("", self.notifications_checkbox)
        
        self.save_ui_button = QPushButton("Lưu cài đặt giao diện")
        self.save_ui_button.clicked.connect(self.save_ui_settings)
        ui_layout.addRow("", self.save_ui_button)
        
        layout.addWidget(ui_group)
        
        # Thêm tab vào container
        self.tab_widget.addTab(settings_tab, "Cài đặt")
    
    def create_system_management_tab(self):
        """Tạo tab quản lý hệ thống"""
        system_tab = QWidget()
        layout = QVBoxLayout(system_tab)
        
        # Khởi tạo trạng thái các dịch vụ nếu chưa có
        if not hasattr(self, 'service_status'):
            self.service_status = {
                "market_notifier": False,
                "unified_trading_service": False,
                "service_manager": False,
                "watchdog": False,
                "telegram_notifier": True,
                "auto_trade": False,
                "ml_training": False,
                "market_scanner": False
            }
        
        # Tạo phần quản lý các dịch vụ
        services_group = QGroupBox("Quản lý dịch vụ")
        services_layout = QVBoxLayout(services_group)
        
        # Market Notifier Service
        market_notifier_layout = QHBoxLayout()
        market_notifier_label = QLabel("Market Notifier:")
        self.market_notifier_status = QLabel("Chưa khởi động")
        self.market_notifier_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_market_notifier_button = QPushButton("Khởi động")
        self.start_market_notifier_button.clicked.connect(lambda: self.start_service("market_notifier"))
        self.start_market_notifier_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_market_notifier_button = QPushButton("Dừng")
        self.stop_market_notifier_button.clicked.connect(lambda: self.stop_service("market_notifier"))
        self.stop_market_notifier_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_market_notifier_button.setEnabled(False)
        
        market_notifier_layout.addWidget(market_notifier_label)
        market_notifier_layout.addWidget(self.market_notifier_status)
        market_notifier_layout.addWidget(self.start_market_notifier_button)
        market_notifier_layout.addWidget(self.stop_market_notifier_button)
        
        services_layout.addLayout(market_notifier_layout)
        
        # Unified Trading Service
        unified_trading_service_layout = QHBoxLayout()
        unified_trading_service_label = QLabel("Unified Trading Service:")
        self.unified_trading_service_status = QLabel("Chưa khởi động")
        self.unified_trading_service_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_unified_trading_service_button = QPushButton("Khởi động")
        self.start_unified_trading_service_button.clicked.connect(lambda: self.start_service("unified_trading_service"))
        self.start_unified_trading_service_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_unified_trading_service_button = QPushButton("Dừng")
        self.stop_unified_trading_service_button.clicked.connect(lambda: self.stop_service("unified_trading_service"))
        self.stop_unified_trading_service_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_unified_trading_service_button.setEnabled(False)
        
        unified_trading_service_layout.addWidget(unified_trading_service_label)
        unified_trading_service_layout.addWidget(self.unified_trading_service_status)
        unified_trading_service_layout.addWidget(self.start_unified_trading_service_button)
        unified_trading_service_layout.addWidget(self.stop_unified_trading_service_button)
        
        services_layout.addLayout(unified_trading_service_layout)
        
        # Service Manager
        service_manager_layout = QHBoxLayout()
        service_manager_label = QLabel("Service Manager:")
        self.service_manager_status = QLabel("Chưa khởi động")
        self.service_manager_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_service_manager_button = QPushButton("Khởi động")
        self.start_service_manager_button.clicked.connect(lambda: self.start_service("service_manager"))
        self.start_service_manager_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_service_manager_button = QPushButton("Dừng")
        self.stop_service_manager_button.clicked.connect(lambda: self.stop_service("service_manager"))
        self.stop_service_manager_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_service_manager_button.setEnabled(False)
        
        service_manager_layout.addWidget(service_manager_label)
        service_manager_layout.addWidget(self.service_manager_status)
        service_manager_layout.addWidget(self.start_service_manager_button)
        service_manager_layout.addWidget(self.stop_service_manager_button)
        
        services_layout.addLayout(service_manager_layout)
        
        # Watchdog Service
        watchdog_layout = QHBoxLayout()
        watchdog_label = QLabel("Watchdog Service:")
        self.watchdog_status = QLabel("Chưa khởi động")
        self.watchdog_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_watchdog_button = QPushButton("Khởi động")
        self.start_watchdog_button.clicked.connect(lambda: self.start_service("watchdog"))
        self.start_watchdog_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_watchdog_button = QPushButton("Dừng")
        self.stop_watchdog_button.clicked.connect(lambda: self.stop_service("watchdog"))
        self.stop_watchdog_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_watchdog_button.setEnabled(False)
        
        watchdog_layout.addWidget(watchdog_label)
        watchdog_layout.addWidget(self.watchdog_status)
        watchdog_layout.addWidget(self.start_watchdog_button)
        watchdog_layout.addWidget(self.stop_watchdog_button)
        
        services_layout.addLayout(watchdog_layout)
        
        # Telegram Notifier Service
        telegram_notifier_layout = QHBoxLayout()
        telegram_notifier_label = QLabel("Telegram Notifier:")
        self.telegram_notifier_status = QLabel("Đang chạy")
        self.telegram_notifier_status.setStyleSheet("color: #22C55E; font-weight: bold;")
        
        self.start_telegram_notifier_button = QPushButton("Khởi động")
        self.start_telegram_notifier_button.clicked.connect(lambda: self.start_service("telegram_notifier"))
        self.start_telegram_notifier_button.setStyleSheet("background-color: #22C55E; color: white;")
        self.start_telegram_notifier_button.setEnabled(False)
        
        self.stop_telegram_notifier_button = QPushButton("Dừng")
        self.stop_telegram_notifier_button.clicked.connect(lambda: self.stop_service("telegram_notifier"))
        self.stop_telegram_notifier_button.setStyleSheet("background-color: #EF4444; color: white;")
        
        telegram_notifier_layout.addWidget(telegram_notifier_label)
        telegram_notifier_layout.addWidget(self.telegram_notifier_status)
        telegram_notifier_layout.addWidget(self.start_telegram_notifier_button)
        telegram_notifier_layout.addWidget(self.stop_telegram_notifier_button)
        
        services_layout.addLayout(telegram_notifier_layout)
        
        # Auto Trading Service
        auto_trade_layout = QHBoxLayout()
        auto_trade_label = QLabel("Auto Trading:")
        self.auto_trade_status = QLabel("Chưa khởi động")
        self.auto_trade_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_auto_trade_button = QPushButton("Khởi động")
        self.start_auto_trade_button.clicked.connect(lambda: self.start_service("auto_trade"))
        self.start_auto_trade_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_auto_trade_button = QPushButton("Dừng")
        self.stop_auto_trade_button.clicked.connect(lambda: self.stop_service("auto_trade"))
        self.stop_auto_trade_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_auto_trade_button.setEnabled(False)
        
        auto_trade_layout.addWidget(auto_trade_label)
        auto_trade_layout.addWidget(self.auto_trade_status)
        auto_trade_layout.addWidget(self.start_auto_trade_button)
        auto_trade_layout.addWidget(self.stop_auto_trade_button)
        
        services_layout.addLayout(auto_trade_layout)
        
        # ML Training Service
        ml_training_layout = QHBoxLayout()
        ml_training_label = QLabel("ML Training:")
        self.ml_training_status = QLabel("Chưa khởi động")
        self.ml_training_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_ml_training_button = QPushButton("Khởi động")
        self.start_ml_training_button.clicked.connect(lambda: self.start_service("ml_training"))
        self.start_ml_training_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_ml_training_button = QPushButton("Dừng")
        self.stop_ml_training_button.clicked.connect(lambda: self.stop_service("ml_training"))
        self.stop_ml_training_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_ml_training_button.setEnabled(False)
        
        ml_training_layout.addWidget(ml_training_label)
        ml_training_layout.addWidget(self.ml_training_status)
        ml_training_layout.addWidget(self.start_ml_training_button)
        ml_training_layout.addWidget(self.stop_ml_training_button)
        
        services_layout.addLayout(ml_training_layout)
        
        # Market Scanner Service
        market_scanner_layout = QHBoxLayout()
        market_scanner_label = QLabel("Multi-Coin Scanner:")
        self.market_scanner_status = QLabel("Chưa khởi động")
        self.market_scanner_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        
        self.start_market_scanner_button = QPushButton("Khởi động")
        self.start_market_scanner_button.clicked.connect(lambda: self.start_service("market_scanner"))
        self.start_market_scanner_button.setStyleSheet("background-color: #22C55E; color: white;")
        
        self.stop_market_scanner_button = QPushButton("Dừng")
        self.stop_market_scanner_button.clicked.connect(lambda: self.stop_service("market_scanner"))
        self.stop_market_scanner_button.setStyleSheet("background-color: #EF4444; color: white;")
        self.stop_market_scanner_button.setEnabled(False)
        
        market_scanner_layout.addWidget(market_scanner_label)
        market_scanner_layout.addWidget(self.market_scanner_status)
        market_scanner_layout.addWidget(self.start_market_scanner_button)
        market_scanner_layout.addWidget(self.stop_market_scanner_button)
        
        services_layout.addLayout(market_scanner_layout)
        
        # Nút khởi động tất cả dịch vụ
        start_all_layout = QHBoxLayout()
        
        self.start_all_services_button = QPushButton("Khởi động tất cả dịch vụ")
        self.start_all_services_button.clicked.connect(self.start_all_services)
        self.start_all_services_button.setStyleSheet("background-color: #22C55E; color: white; font-weight: bold; padding: 8px;")
        
        self.stop_all_services_button = QPushButton("Dừng tất cả dịch vụ")
        self.stop_all_services_button.clicked.connect(self.stop_all_services)
        self.stop_all_services_button.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold; padding: 8px;")
        
        start_all_layout.addWidget(self.start_all_services_button)
        start_all_layout.addWidget(self.stop_all_services_button)
        
        services_layout.addLayout(start_all_layout)
        
        layout.addWidget(services_group)
        
        # Tạo phần nhật ký hệ thống
        logs_group = QGroupBox("Nhật ký hệ thống")
        logs_layout = QVBoxLayout(logs_group)
        
        self.system_logs = QTextEdit()
        self.system_logs.setReadOnly(True)
        self.system_logs.setMinimumHeight(200)
        logs_layout.addWidget(self.system_logs)
        
        refresh_logs_layout = QHBoxLayout()
        self.refresh_logs_button = QPushButton("Cập nhật nhật ký")
        self.refresh_logs_button.clicked.connect(self.refresh_system_logs)
        
        self.clear_logs_button = QPushButton("Xóa nhật ký")
        self.clear_logs_button.clicked.connect(self.clear_system_logs)
        
        refresh_logs_layout.addWidget(self.refresh_logs_button)
        refresh_logs_layout.addWidget(self.clear_logs_button)
        
        logs_layout.addLayout(refresh_logs_layout)
        
        layout.addWidget(logs_group)
        
        # Thêm tab vào container
        self.tab_widget.addTab(system_tab, "Quản lý hệ thống")
    
    def create_status_bar(self):
        """Tạo thanh trạng thái"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.status_label = QLabel("Sẵn sàng")
        self.statusBar.addWidget(self.status_label, 1)
        
        self.connection_label = QLabel("Trạng thái kết nối: Chưa kết nối")
        self.statusBar.addPermanentWidget(self.connection_label)
        
        self.last_update_label = QLabel("Cập nhật lần cuối: N/A")
        self.statusBar.addPermanentWidget(self.last_update_label)
    
    def init_refresh_thread(self):
        """Khởi tạo thread cập nhật dữ liệu"""
        self.refresh_thread = RefreshThread(self.market_analyzer, self.position_manager)
        self.refresh_thread.signal.connect(self.update_data)
        self.refresh_thread.start()
    
    def connect_events(self):
        """Kết nối các sự kiện"""
        # Kết nối sự kiện cho Stop Loss và Take Profit checkbox
        self.stop_loss_checkbox.toggled.connect(lambda checked: self.stop_loss_spin.setEnabled(not checked))
        self.take_profit_checkbox.toggled.connect(lambda checked: self.take_profit_spin.setEnabled(not checked))
        
        # Kết nối sự kiện thay đổi cặp giao dịch
        self.symbol_combo.currentTextChanged.connect(self.update_trading_info)
        
        # Kết nối sự kiện thay đổi vị thế quản lý
        self.manage_symbol_combo.currentTextChanged.connect(self.update_manage_position)
        
        # Kết nối sự kiện double-click vào bảng vị thế
        self.positions_table.cellDoubleClicked.connect(lambda row, col: self.select_position_from_table(self.positions_table, row))
        self.positions_detail_table.cellDoubleClicked.connect(lambda row, col: self.select_position_from_table(self.positions_detail_table, row))
    
    def load_config(self):
        """Tải cấu hình từ file"""
        try:
            # Tải cấu hình API
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY", "")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "")
            
            self.api_key_edit.setText(api_key)
            self.api_secret_edit.setText(api_secret)
            
            # Tải cấu hình Telegram
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
            
            self.telegram_token_edit.setText(telegram_token)
            self.telegram_chat_id_edit.setText(telegram_chat_id)
            
            # Tải cấu hình thông báo Telegram
            try:
                telegram_config_file = "configs/telegram_config.json"
                if os.path.exists(telegram_config_file):
                    with open(telegram_config_file, "r") as f:
                        telegram_config = json.load(f)
                    
                    self.notify_position_checkbox.setChecked(telegram_config.get("notify_position", True))
                    self.notify_sltp_checkbox.setChecked(telegram_config.get("notify_sltp", True))
                    self.notify_opportunity_checkbox.setChecked(telegram_config.get("notify_opportunity", True))
                    self.notify_error_checkbox.setChecked(telegram_config.get("notify_error", True))
                    self.notify_summary_checkbox.setChecked(telegram_config.get("notify_summary", True))
            except Exception as e:
                logger.warning(f"Không tải được cấu hình Telegram: {str(e)}")
            
            # Tải cấu hình rủi ro nếu có Risk Manager
            if self.risk_manager:
                risk_config = self.risk_manager.risk_config
                
                self.risk_percentage_spin.setValue(risk_config.get("risk_percentage", 0.01) * 100)
                self.max_positions_spin.setValue(risk_config.get("max_positions", 5))
                self.default_leverage_spin.setValue(risk_config.get("leverage", 5))
                self.position_size_percentage_spin.setValue(risk_config.get("position_size_percentage", 0.1) * 100)
                self.stop_loss_percentage_spin.setValue(risk_config.get("stop_loss_percentage", 0.015) * 100)
                self.take_profit_percentage_spin.setValue(risk_config.get("take_profit_percentage", 0.03) * 100)
                
                self.trailing_stop_checkbox.setChecked(risk_config.get("trailing_stop", {}).get("enabled", True))
                self.partial_tp_checkbox.setChecked(risk_config.get("partial_take_profit", {}).get("enabled", False))
                self.trading_hours_checkbox.setChecked(risk_config.get("trading_hours_restriction", {}).get("enabled", False))
            
            # Cập nhật UI
            self.refresh_data()
            
            logger.info("Đã tải cấu hình thành công")
        
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}", exc_info=True)
    
    def update_data(self, data: Dict[str, Any]):
        """
        Cập nhật dữ liệu từ thread cập nhật
        
        :param data: Dữ liệu cập nhật
        """
        try:
            # Cập nhật thông tin tài khoản
            account_balance = data.get("account_balance", {})
            self.update_account_balance(account_balance)
            
            # Cập nhật danh sách vị thế
            positions = data.get("positions", [])
            self.update_positions(positions)
            
            # Cập nhật thông tin thị trường
            market_overview = data.get("market_overview", [])
            self.update_market_overview(market_overview)
            
            # Cập nhật thông tin giao dịch
            self.update_trading_info()
            
            # Cập nhật trạng thái kết nối
            self.connection_label.setText("Trạng thái kết nối: Đã kết nối")
            
            # Cập nhật thời gian cập nhật lần cuối
            current_time = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.setText(f"Cập nhật lần cuối: {current_time}")
            
            # Cập nhật danh sách vị thế trong combobox
            self.update_position_combos(positions)
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu: {str(e)}", exc_info=True)
    
    def update_account_balance(self, account_balance: Dict[str, Any]):
        """
        Cập nhật thông tin số dư tài khoản
        
        :param account_balance: Thông tin số dư tài khoản
        """
        total_balance = account_balance.get("total_balance", 0)
        available_balance = account_balance.get("available_balance", 0)
        unrealized_pnl = account_balance.get("unrealized_pnl", 0)
        
        # Cập nhật các label
        self.total_balance_label.setText(f"{total_balance:.2f} USDT")
        self.available_balance_label.setText(f"{available_balance:.2f} USDT")
        
        # Thay đổi màu sắc dựa trên lợi nhuận
        if unrealized_pnl > 0:
            self.unrealized_pnl_label.setStyleSheet("color: #22C55E;")  # Màu xanh khi lời
        elif unrealized_pnl < 0:
            self.unrealized_pnl_label.setStyleSheet("color: #EF4444;")  # Màu đỏ khi lỗ
        else:
            self.unrealized_pnl_label.setStyleSheet("")  # Màu mặc định
        
        self.unrealized_pnl_label.setText(f"{unrealized_pnl:.2f} USDT")
    
    def update_positions(self, positions: List[Dict[str, Any]]):
        """
        Cập nhật danh sách vị thế
        
        :param positions: Danh sách vị thế
        """
        # Cập nhật bảng vị thế trong tab tổng quan
        self.positions_table.setRowCount(len(positions))
        
        for row, position in enumerate(positions):
            symbol = position.get("symbol", "")
            side = position.get("side", "")
            size = position.get("size", 0)
            entry_price = position.get("entry_price", 0)
            mark_price = position.get("mark_price", 0)
            stop_loss = position.get("stop_loss", "N/A")
            take_profit = position.get("take_profit", "N/A")
            unrealized_pnl = position.get("unrealized_pnl", 0)
            profit_percent = position.get("profit_percent", 0)
            
            # Tạo các item cho bảng
            self.positions_table.setItem(row, 0, QTableWidgetItem(symbol))
            
            side_item = QTableWidgetItem(side)
            if side == "LONG":
                side_item.setForeground(QColor("#22C55E"))  # Màu xanh cho Long
            else:
                side_item.setForeground(QColor("#EF4444"))  # Màu đỏ cho Short
            self.positions_table.setItem(row, 1, side_item)
            
            self.positions_table.setItem(row, 2, QTableWidgetItem(f"{size:.4f}"))
            self.positions_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
            self.positions_table.setItem(row, 4, QTableWidgetItem(f"{mark_price:.2f}"))
            
            self.positions_table.setItem(row, 5, QTableWidgetItem(f"{stop_loss}" if stop_loss != "N/A" else "N/A"))
            self.positions_table.setItem(row, 6, QTableWidgetItem(f"{take_profit}" if take_profit != "N/A" else "N/A"))
            
            pnl_item = QTableWidgetItem(f"{unrealized_pnl:.2f} ({profit_percent:.2f}%)")
            if unrealized_pnl > 0:
                pnl_item.setForeground(QColor("#22C55E"))  # Màu xanh khi lời
            elif unrealized_pnl < 0:
                pnl_item.setForeground(QColor("#EF4444"))  # Màu đỏ khi lỗ
            self.positions_table.setItem(row, 7, pnl_item)
        
        # Cập nhật bảng vị thế trong tab quản lý vị thế
        self.positions_detail_table.setRowCount(len(positions))
        
        for row, position in enumerate(positions):
            symbol = position.get("symbol", "")
            side = position.get("side", "")
            size = position.get("size", 0)
            entry_price = position.get("entry_price", 0)
            mark_price = position.get("mark_price", 0)
            stop_loss = position.get("stop_loss", "N/A")
            take_profit = position.get("take_profit", "N/A")
            unrealized_pnl = position.get("unrealized_pnl", 0)
            profit_percent = position.get("profit_percent", 0)
            
            # Tạo các item cho bảng
            self.positions_detail_table.setItem(row, 0, QTableWidgetItem(symbol))
            
            side_item = QTableWidgetItem(side)
            if side == "LONG":
                side_item.setForeground(QColor("#22C55E"))  # Màu xanh cho Long
            else:
                side_item.setForeground(QColor("#EF4444"))  # Màu đỏ cho Short
            self.positions_detail_table.setItem(row, 1, side_item)
            
            self.positions_detail_table.setItem(row, 2, QTableWidgetItem(f"{size:.4f}"))
            self.positions_detail_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
            self.positions_detail_table.setItem(row, 4, QTableWidgetItem(f"{mark_price:.2f}"))
            
            self.positions_detail_table.setItem(row, 5, QTableWidgetItem(f"{stop_loss}" if stop_loss != "N/A" else "N/A"))
            self.positions_detail_table.setItem(row, 6, QTableWidgetItem(f"{take_profit}" if take_profit != "N/A" else "N/A"))
            
            pnl_item = QTableWidgetItem(f"{unrealized_pnl:.2f} ({profit_percent:.2f}%)")
            if unrealized_pnl > 0:
                pnl_item.setForeground(QColor("#22C55E"))  # Màu xanh khi lời
            elif unrealized_pnl < 0:
                pnl_item.setForeground(QColor("#EF4444"))  # Màu đỏ khi lỗ
            self.positions_detail_table.setItem(row, 7, pnl_item)
            
            # Tạo nút đóng vị thế
            close_button = QPushButton("Đóng")
            close_button.setStyleSheet("background-color: #EF4444; color: white;")
            close_button.clicked.connect(lambda checked, s=symbol: self.close_position_from_table(s))
            
            # Thêm nút vào bảng
            self.positions_detail_table.setCellWidget(row, 8, close_button)
    
    def update_market_overview(self, market_overview: List[Dict[str, Any]]):
        """
        Cập nhật thông tin tổng quan thị trường
        
        :param market_overview: Thông tin tổng quan thị trường
        """
        self.market_table.setRowCount(len(market_overview))
        
        # Cập nhật giá BTC và ETH trên dashboard
        for market_data in market_overview:
            symbol = market_data.get("symbol", "")
            price = market_data.get("price", 0)
            
            if symbol == "BTCUSDT":
                self.btc_price_label.setText(f"{price:.2f} USDT")
            elif symbol == "ETHUSDT":
                self.eth_price_label.setText(f"{price:.2f} USDT")
        
        for row, market_data in enumerate(market_overview):
            symbol = market_data.get("symbol", "")
            price = market_data.get("price", 0)
            change_24h = market_data.get("change_24h", 0)
            volume = market_data.get("volume", 0)
            
            # Tạo các item cho bảng
            self.market_table.setItem(row, 0, QTableWidgetItem(symbol))
            self.market_table.setItem(row, 1, QTableWidgetItem(f"{price:.2f}"))
            
            change_item = QTableWidgetItem(f"{change_24h:.2f}%")
            if change_24h > 0:
                change_item.setForeground(QColor("#22C55E"))  # Màu xanh khi tăng
            elif change_24h < 0:
                change_item.setForeground(QColor("#EF4444"))  # Màu đỏ khi giảm
            self.market_table.setItem(row, 2, change_item)
            
            # Format khối lượng theo đơn vị K, M, B
            if volume >= 1_000_000_000:
                volume_str = f"{volume / 1_000_000_000:.2f}B"
            elif volume >= 1_000_000:
                volume_str = f"{volume / 1_000_000:.2f}M"
            elif volume >= 1_000:
                volume_str = f"{volume / 1_000:.2f}K"
            else:
                volume_str = f"{volume:.2f}"
            
            self.market_table.setItem(row, 3, QTableWidgetItem(volume_str))
    
    def update_trading_info(self):
        """Cập nhật thông tin giao dịch"""
        symbol = self.symbol_combo.currentText()
        # Lấy hướng giao dịch hiện tại từ combobox trước mọi thao tác
        side = self.side_combo.currentText()
        
        try:
            # Lấy giá hiện tại
            if self.market_analyzer and self.market_analyzer.client:
                symbol_ticker = self.market_analyzer.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(symbol_ticker["price"])
                
                # Cập nhật giá hiện tại
                self.current_price_label.setText(f"{current_price:.2f} USDT")
                
                # Tính toán giá trị vị thế
                amount = self.amount_spin.value()
                position_value = amount * current_price
                self.position_value_label.setText(f"{position_value:.2f} USDT")
                
                # Tính toán margin yêu cầu
                leverage = self.leverage_spin.value()
                margin_required = position_value / leverage
                self.margin_required_label.setText(f"{margin_required:.2f} USDT")
                
                # Tính toán phần trăm rủi ro
                if self.position_manager and self.position_manager.client:
                    account_info = self.position_manager.get_account_balance()
                    if account_info.get("status") == "success":
                        total_balance = account_info.get("balance", {}).get("total_balance", 0)
                        if total_balance > 0:
                            risk_percentage = margin_required / total_balance * 100
                            self.risk_percentage_label.setText(f"{risk_percentage:.2f}%")
                
                # Tính toán giá thanh lý (giả sử)
                if side.upper() in ["LONG", "BUY", "MUA"]:
                    liquidation_price = current_price * (1 - (1 / leverage) * 0.9)  # 90% margin
                else:
                    liquidation_price = current_price * (1 + (1 / leverage) * 0.9)  # 90% margin
                
                self.liquidation_price_label.setText(f"{liquidation_price:.2f} USDT")
                
                # Tính toán SL và TP tự động
                if self.stop_loss_checkbox.isChecked() or self.take_profit_checkbox.isChecked():
                    if self.risk_manager:
                        # Đã lấy side ở trên, không cần lấy lại
                        sl_tp = self.risk_manager.calculate_sl_tp(symbol, side, current_price)
                        
                        if self.stop_loss_checkbox.isChecked():
                            self.stop_loss_spin.setValue(sl_tp["stop_loss"])
                        
                        if self.take_profit_checkbox.isChecked():
                            self.take_profit_spin.setValue(sl_tp["take_profit"])
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật thông tin giao dịch: {str(e)}", exc_info=True)
    
    def update_position_combos(self, positions: List[Dict[str, Any]]):
        """
        Cập nhật danh sách vị thế trong combobox
        
        :param positions: Danh sách vị thế
        """
        # Lưu lại giá trị hiện tại
        current_symbol = self.manage_symbol_combo.currentText()
        
        # Xóa tất cả các item
        self.manage_symbol_combo.clear()
        
        # Thêm các vị thế vào combobox
        for position in positions:
            symbol = position.get("symbol", "")
            self.manage_symbol_combo.addItem(symbol)
        
        # Khôi phục lại giá trị nếu có thể
        index = self.manage_symbol_combo.findText(current_symbol)
        if index >= 0:
            self.manage_symbol_combo.setCurrentIndex(index)
        
        # Cập nhật thông tin vị thế quản lý
        self.update_manage_position()
    
    def update_manage_position(self):
        """Cập nhật thông tin vị thế đang quản lý"""
        symbol = self.manage_symbol_combo.currentText()
        
        # Nếu không có vị thế nào được chọn
        if not symbol:
            self.manage_sl_spin.setValue(0)
            self.manage_tp_spin.setValue(0)
            return
        
        # Tìm vị thế trong danh sách
        for row in range(self.positions_detail_table.rowCount()):
            if self.positions_detail_table.item(row, 0).text() == symbol:
                # Lấy thông tin SL và TP
                stop_loss_item = self.positions_detail_table.item(row, 5)
                take_profit_item = self.positions_detail_table.item(row, 6)
                
                stop_loss = float(stop_loss_item.text()) if stop_loss_item.text() != "N/A" else 0
                take_profit = float(take_profit_item.text()) if take_profit_item.text() != "N/A" else 0
                
                # Cập nhật các spinbox
                self.manage_sl_spin.setValue(stop_loss)
                self.manage_tp_spin.setValue(take_profit)
                
                break
    
    def calculate_position(self):
        """Tính toán kích thước vị thế dựa trên rủi ro"""
        try:
            if not self.position_manager or not self.risk_manager:
                self.show_error("Không thể tính toán vị thế", "Chưa khởi tạo PositionManager hoặc RiskManager")
                return
            
            # Lấy số dư tài khoản
            account_info = self.position_manager.get_account_balance()
            if account_info.get("status") != "success":
                self.show_error("Không thể lấy số dư tài khoản", account_info.get("message", "Lỗi không xác định"))
                return
            
            total_balance = account_info.get("balance", {}).get("total_balance", 0)
            
            # Tính toán kích thước vị thế
            symbol = self.symbol_combo.currentText()
            position_size = self.risk_manager.calculate_position_size(total_balance, symbol)
            
            # Cập nhật kích thước vị thế
            self.amount_spin.setValue(position_size)
            
            # Thông báo thành công
            self.status_label.setText(f"Đã tính toán kích thước vị thế: {position_size:.4f}")
            
            # Cập nhật thông tin giao dịch
            self.update_trading_info()
        
        except Exception as e:
            logger.error(f"Lỗi khi tính toán kích thước vị thế: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi tính toán kích thước vị thế", str(e))
    
    def open_position(self, side_override=None):
        """
        Mở vị thế mới
        
        :param side_override: Ghi đè hướng giao dịch (tùy chọn)
        """
        try:
            if not self.position_manager:
                self.show_error("Không thể mở vị thế", "Chưa khởi tạo PositionManager")
                return
            
            # Lấy thông tin giao dịch
            symbol = self.symbol_combo.currentText()
            side = side_override if side_override else self.side_combo.currentText()
            amount = self.amount_spin.value()
            leverage = self.leverage_spin.value()
            
            stop_loss = None if self.stop_loss_checkbox.isChecked() else self.stop_loss_spin.value()
            take_profit = None if self.take_profit_checkbox.isChecked() else self.take_profit_spin.value()
            
            # Kiểm tra tính hợp lệ của vị thế
            if self.risk_manager:
                is_valid, reason = self.risk_manager.validate_new_position(symbol, side, amount)
                if not is_valid:
                    self.show_error("Vị thế không hợp lệ", reason)
                    return
                
                # Tính toán SL và TP tự động nếu cần
                if self.stop_loss_checkbox.isChecked() or self.take_profit_checkbox.isChecked():
                    # Lấy giá hiện tại - Xử lý an toàn
                    try:
                        symbol_ticker = self.position_manager.get_current_price(symbol)
                        current_price = float(symbol_ticker)
                    except Exception as e:
                        logger.error(f"Lỗi khi lấy giá hiện tại: {str(e)}")
                        current_price = 0.0
                    
                    sl_tp = self.risk_manager.calculate_sl_tp(symbol, side, current_price)
                    
                    if self.stop_loss_checkbox.isChecked():
                        stop_loss = sl_tp["stop_loss"]
                    
                    if self.take_profit_checkbox.isChecked():
                        take_profit = sl_tp["take_profit"]
                
                # Kiểm tra tính hợp lệ của SL và TP
                if stop_loss is not None and take_profit is not None:
                    # Lấy giá hiện tại - Xử lý an toàn
                    try:
                        symbol_ticker = self.position_manager.get_current_price(symbol)
                        current_price = float(symbol_ticker)
                    except Exception as e:
                        logger.error(f"Lỗi khi lấy giá hiện tại: {str(e)}")
                        current_price = 0.0
                    
                    is_valid_sltp, reason_sltp = self.risk_manager.validate_sl_tp(symbol, side, current_price, stop_loss, take_profit)
                    if not is_valid_sltp:
                        self.show_error("SL và TP không hợp lệ", reason_sltp)
                        return
            
            # Xác nhận trước khi đặt lệnh
            reply = QMessageBox.question(
                self, 
                "Xác nhận giao dịch", 
                f"Bạn có chắc chắn muốn mở vị thế {side} trên {symbol} với kích thước {amount:.4f} không?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Mở vị thế
            result = self.position_manager.open_position(symbol, side, amount, stop_loss, take_profit, leverage)
            
            if result.get("status") == "success":
                self.show_info("Đặt lệnh thành công", f"Đã mở vị thế {side} trên {symbol} với kích thước {amount:.4f}")
                self.status_label.setText(f"Đã mở vị thế {side} trên {symbol}")
                
                # Cập nhật dữ liệu
                self.refresh_data()
            else:
                self.show_error("Lỗi khi đặt lệnh", result.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi mở vị thế: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi mở vị thế", str(e))
    
    def update_sltp(self):
        """Cập nhật Stop Loss và Take Profit"""
        try:
            if not self.position_manager:
                self.show_error("Không thể cập nhật SL/TP", "Chưa khởi tạo PositionManager")
                return
            
            # Lấy thông tin vị thế
            symbol = self.manage_symbol_combo.currentText()
            if not symbol:
                self.show_error("Không thể cập nhật SL/TP", "Chưa chọn vị thế")
                return
            
            stop_loss = self.manage_sl_spin.value()
            take_profit = self.manage_tp_spin.value()
            
            # Cập nhật SL và TP
            result = self.position_manager.update_sl_tp(symbol, None, stop_loss, take_profit)
            
            if result.get("status") == "success":
                self.show_info("Cập nhật thành công", f"Đã cập nhật SL/TP cho {symbol}")
                self.status_label.setText(f"Đã cập nhật SL/TP cho {symbol}")
                
                # Cập nhật dữ liệu
                self.refresh_data()
            else:
                self.show_error("Lỗi khi cập nhật SL/TP", result.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật SL/TP: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi cập nhật SL/TP", str(e))
    
    def close_position(self):
        """Đóng vị thế được chọn"""
        try:
            if not self.position_manager:
                self.show_error("Không thể đóng vị thế", "Chưa khởi tạo PositionManager")
                return
            
            # Lấy thông tin vị thế
            symbol = self.manage_symbol_combo.currentText()
            if not symbol:
                self.show_error("Không thể đóng vị thế", "Chưa chọn vị thế")
                return
            
            # Xác nhận trước khi đóng vị thế
            reply = QMessageBox.question(
                self, 
                "Xác nhận đóng vị thế", 
                f"Bạn có chắc chắn muốn đóng vị thế {symbol} không?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Đóng vị thế
            result = self.position_manager.close_position(symbol)
            
            if result.get("status") == "success":
                self.show_info("Đóng vị thế thành công", f"Đã đóng vị thế {symbol} với lợi nhuận {result.get('profit', 0):.2f} USDT ({result.get('profit_percent', 0):.2f}%)")
                self.status_label.setText(f"Đã đóng vị thế {symbol}")
                
                # Cập nhật dữ liệu
                self.refresh_data()
            else:
                self.show_error("Lỗi khi đóng vị thế", result.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi đóng vị thế", str(e))
    
    def close_position_from_table(self, symbol: str):
        """
        Đóng vị thế từ bảng
        
        :param symbol: Cặp giao dịch
        """
        try:
            if not self.position_manager:
                self.show_error("Không thể đóng vị thế", "Chưa khởi tạo PositionManager")
                return
            
            # Xác nhận trước khi đóng vị thế
            reply = QMessageBox.question(
                self, 
                "Xác nhận đóng vị thế", 
                f"Bạn có chắc chắn muốn đóng vị thế {symbol} không?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Đóng vị thế
            result = self.position_manager.close_position(symbol)
            
            if result.get("status") == "success":
                self.show_info("Đóng vị thế thành công", f"Đã đóng vị thế {symbol} với lợi nhuận {result.get('profit', 0):.2f} USDT ({result.get('profit_percent', 0):.2f}%)")
                self.status_label.setText(f"Đã đóng vị thế {symbol}")
                
                # Cập nhật dữ liệu
                self.refresh_data()
            else:
                self.show_error("Lỗi khi đóng vị thế", result.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi đóng vị thế", str(e))
    
    def select_position_from_table(self, table, row: int):
        """
        Chọn vị thế từ bảng
        
        :param table: Bảng chứa vị thế
        :param row: Chỉ số hàng
        """
        # Lấy thông tin vị thế
        symbol = table.item(row, 0).text()
        
        # Chọn vị thế trong combobox quản lý
        index = self.manage_symbol_combo.findText(symbol)
        if index >= 0:
            self.manage_symbol_combo.setCurrentIndex(index)
            
            # Chuyển đến tab quản lý vị thế
            self.tab_widget.setCurrentIndex(2)
    
    def refresh_history(self):
        """Cập nhật lịch sử giao dịch"""
        try:
            if not self.position_manager:
                self.show_error("Không thể cập nhật lịch sử", "Chưa khởi tạo PositionManager")
                return
            
            # Lấy lịch sử giao dịch
            history = self.position_manager.get_position_history(limit=20)
            
            # Cập nhật bảng lịch sử
            self.history_table.setRowCount(len(history))
            
            for row, trade in enumerate(history):
                symbol = trade.get("symbol", "")
                side = trade.get("side", "")
                price = trade.get("price", 0)
                quantity = trade.get("quantity", 0)
                commission = trade.get("commission", 0)
                realized_pnl = trade.get("realized_pnl", 0)
                time = trade.get("time", "")
                
                # Tạo các item cho bảng
                self.history_table.setItem(row, 0, QTableWidgetItem(symbol))
                
                side_item = QTableWidgetItem(side)
                if side == "LONG":
                    side_item.setForeground(QColor("#22C55E"))  # Màu xanh cho Long
                else:
                    side_item.setForeground(QColor("#EF4444"))  # Màu đỏ cho Short
                self.history_table.setItem(row, 1, side_item)
                
                self.history_table.setItem(row, 2, QTableWidgetItem(f"{price:.2f}"))
                self.history_table.setItem(row, 3, QTableWidgetItem(f"{quantity:.4f}"))
                self.history_table.setItem(row, 4, QTableWidgetItem(f"{commission:.4f}"))
                
                pnl_item = QTableWidgetItem(f"{realized_pnl:.2f}")
                if realized_pnl > 0:
                    pnl_item.setForeground(QColor("#22C55E"))  # Màu xanh khi lời
                elif realized_pnl < 0:
                    pnl_item.setForeground(QColor("#EF4444"))  # Màu đỏ khi lỗ
                self.history_table.setItem(row, 5, pnl_item)
                
                self.history_table.setItem(row, 6, QTableWidgetItem(time))
            
            self.status_label.setText("Đã cập nhật lịch sử giao dịch")
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật lịch sử giao dịch: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi cập nhật lịch sử giao dịch", str(e))
    
    def analyze_market(self):
        """Phân tích thị trường"""
        try:
            if not self.market_analyzer:
                self.show_error("Không thể phân tích thị trường", "Chưa khởi tạo MarketAnalyzer")
                return
            
            # Lấy thông tin cặp giao dịch và khung thời gian
            symbol = self.analysis_symbol_combo.currentText()
            interval = self.analysis_interval_combo.currentText()
            
            # Phân tích kỹ thuật
            analysis = self.market_analyzer.analyze_technical(symbol, interval)
            
            if analysis.get("status") == "success":
                # Cập nhật kết quả phân tích
                self.analysis_result_text.clear()
                
                # Tạo nội dung phân tích
                content = f"<h3>Phân tích kỹ thuật cho {symbol} ({interval})</h3>"
                content += f"<p>Giá hiện tại: {analysis.get('price', 0):.2f} USDT</p>"
                content += f"<p>Tín hiệu: <b>{analysis.get('overall_signal', 'N/A')}</b></p>"
                content += f"<p>Độ mạnh: <b>{analysis.get('strength', 'N/A')}</b></p>"
                
                content += "<h4>Xu hướng</h4>"
                content += f"<p>Ngắn hạn: {analysis.get('short_term_trend', 'N/A')}</p>"
                content += f"<p>Trung hạn: {analysis.get('mid_term_trend', 'N/A')}</p>"
                content += f"<p>Dài hạn: {analysis.get('long_term_trend', 'N/A')}</p>"
                
                content += "<h4>Các chỉ báo</h4>"
                for indicator in analysis.get("indicators", []):
                    content += f"<p><b>{indicator.get('name', 'N/A')}</b>: {indicator.get('value', 'N/A')} - <i>{indicator.get('signal', 'N/A')}</i></p>"
                
                content += "<h4>Hỗ trợ và kháng cự</h4>"
                for sr in analysis.get("support_resistance", []):
                    content += f"<p><b>{sr.get('type', 'N/A')}</b>: {sr.get('value', 0):.2f}</p>"
                
                self.analysis_result_text.setHtml(content)
                
                # Cập nhật các label tín hiệu
                signal = analysis.get("overall_signal", "N/A")
                self.signal_label.setText(signal)
                
                # Tính mức độ tin cậy (dựa vào score nếu có)
                confidence = analysis.get("score", 0)
                if isinstance(confidence, (int, float)):
                    confidence_text = f"{confidence:.0f}%"
                else:
                    confidence_text = "N/A"
                
                # Xác định màu và lời khuyên
                if signal == "Mua":
                    self.signal_label.setStyleSheet("color: #22C55E; font-size: 16px; font-weight: bold;")
                    recommendation = "NÊN VÀO LỆNH" if confidence >= 65 else "THEO DÕI"
                elif signal == "Bán":
                    self.signal_label.setStyleSheet("color: #EF4444; font-size: 16px; font-weight: bold;")
                    recommendation = "NÊN VÀO LỆNH" if confidence >= 65 else "THEO DÕI"
                else:
                    self.signal_label.setStyleSheet("font-size: 16px; font-weight: bold;")
                    recommendation = "KHÔNG VÀO LỆNH"
                
                # Xác định chiến thuật dựa trên điều kiện thị trường
                market_regime = analysis.get("market_regime", "")
                long_term_trend = analysis.get("long_term_trend", "")
                strength = analysis.get("strength", "N/A")
                strategy = "Chưa xác định"
                
                if long_term_trend == "Tăng" or long_term_trend == "Giảm":
                    strategy = "Theo xu hướng (Trend Following)"
                elif long_term_trend == "Sideway":
                    if market_regime == "volatile":
                        strategy = "Giao dịch biên độ cao (Volatility Range)"
                    else:
                        strategy = "Giao dịch biên (Range Trading)"
                
                # Cập nhật các label
                self.strength_label.setText(f"{strength} (Tin cậy: {confidence_text})")
                self.trend_label.setText(f"{analysis.get('short_term_trend', 'N/A')} - {recommendation}")
                
                # Chỉ hiển thị chiến thuật trong kết quả phân tích mà không tạo label mới
                content += f"<h4>Chiến thuật đề xuất</h4>"
                content += f"<p>{strategy}</p>"
                
                # Cập nhật kết quả phân tích với chiến thuật đề xuất
                self.analysis_result_text.setHtml(content)
                
                self.status_label.setText(f"Đã phân tích thị trường cho {symbol} ({interval})")
            else:
                self.show_error("Lỗi khi phân tích thị trường", analysis.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi phân tích thị trường", str(e))
    
    def analyze_market_detail(self):
        """Phân tích thị trường chi tiết"""
        try:
            if not self.market_analyzer:
                self.show_error("Không thể phân tích thị trường", "Chưa khởi tạo MarketAnalyzer")
                return
            
            # Lấy thông tin cặp giao dịch và khung thời gian
            symbol = self.market_symbol_combo.currentText()
            interval = self.market_interval_combo.currentText()
            
            # Phân tích kỹ thuật
            analysis = self.market_analyzer.analyze_technical(symbol, interval)
            
            if analysis.get("status") == "success":
                # Cập nhật bảng chỉ báo
                indicators = analysis.get("indicators", [])
                self.indicators_table.setRowCount(len(indicators))
                
                for row, indicator in enumerate(indicators):
                    name = indicator.get("name", "")
                    value = indicator.get("value", "")
                    signal = indicator.get("signal", "")
                    
                    self.indicators_table.setItem(row, 0, QTableWidgetItem(name))
                    self.indicators_table.setItem(row, 1, QTableWidgetItem(str(value)))
                    
                    signal_item = QTableWidgetItem(signal)
                    if signal == "Mua":
                        signal_item.setForeground(QColor("#22C55E"))  # Màu xanh cho Mua
                    elif signal == "Bán":
                        signal_item.setForeground(QColor("#EF4444"))  # Màu đỏ cho Bán
                    self.indicators_table.setItem(row, 2, signal_item)
                
                # Cập nhật bảng hỗ trợ/kháng cự
                support_resistance = analysis.get("support_resistance", [])
                self.support_resistance_table.setRowCount(len(support_resistance))
                
                for row, sr in enumerate(support_resistance):
                    type_sr = sr.get("type", "")
                    value = sr.get("value", 0)
                    
                    self.support_resistance_table.setItem(row, 0, QTableWidgetItem(type_sr))
                    self.support_resistance_table.setItem(row, 1, QTableWidgetItem(f"{value:.2f}"))
                
                # Cập nhật thông tin chi tiết
                self.market_detail_text.clear()
                
                # Tạo nội dung chi tiết
                content = f"<h3>Phân tích chi tiết cho {symbol} ({interval})</h3>"
                content += f"<p>Giá hiện tại: {analysis.get('price', 0):.2f} USDT</p>"
                content += f"<p>Tín hiệu tổng hợp: <b>{analysis.get('overall_signal', 'N/A')}</b></p>"
                content += f"<p>Độ mạnh: <b>{analysis.get('strength', 'N/A')}</b></p>"
                
                content += "<h4>Phân tích xu hướng</h4>"
                content += "<p>Xu hướng ngắn hạn (dựa trên SMA20 và SMA50):</p>"
                content += f"<p><b>{analysis.get('short_term_trend', 'N/A')}</b></p>"
                
                content += "<p>Xu hướng trung hạn (dựa trên SMA50):</p>"
                content += f"<p><b>{analysis.get('mid_term_trend', 'N/A')}</b></p>"
                
                content += "<p>Xu hướng dài hạn (dựa trên SMA200):</p>"
                content += f"<p><b>{analysis.get('long_term_trend', 'N/A')}</b></p>"
                
                content += "<h4>Gợi ý giao dịch</h4>"
                confidence = analysis.get("score", 0)
                confidence_text = f"{confidence:.0f}%" if isinstance(confidence, (int, float)) else "N/A"
                
                # Xác định chiến thuật dựa trên điều kiện thị trường
                market_regime = analysis.get("market_regime", "")
                long_term_trend = analysis.get("long_term_trend", "")
                strategy = "Chưa xác định"
                
                if long_term_trend == "Tăng" or long_term_trend == "Giảm":
                    strategy = "Theo xu hướng (Trend Following)"
                elif long_term_trend == "Sideway":
                    if market_regime == "volatile":
                        strategy = "Giao dịch biên độ cao (Volatility Range)"
                    else:
                        strategy = "Giao dịch biên (Range Trading)"
                
                # Thêm thông tin về độ tin cậy và chiến thuật
                content += f"<p><b>Mức độ tin cậy:</b> {confidence_text}</p>"
                content += f"<p><b>Chiến thuật đề xuất:</b> {strategy}</p>"
                
                if analysis.get("overall_signal") == "Mua":
                    recommendation = "NÊN VÀO LỆNH" if confidence >= 65 else "THEO DÕI"
                    content += f"<p style='color: #22C55E;'><b>Khuyến nghị: {recommendation}</b></p>"
                    
                    # Lấy các thông tin giá
                    current_price = analysis.get("price", 0)
                    support_prices = [sr.get("value", 0) for sr in analysis.get("support_resistance", []) if sr.get("type", "").lower() == "support"]
                    nearest_support = max(support_prices) if support_prices else current_price * 0.985
                    
                    # Tính toán mức giá vào lệnh
                    entry_price = current_price
                    entry_zone_low = nearest_support
                    entry_zone_high = current_price
                    
                    # Mức giá Stop Loss và Take Profit
                    stop_loss = nearest_support * 0.99
                    take_profit_1 = current_price * 1.02  # TP mục tiêu 1
                    take_profit_2 = current_price * 1.05  # TP mục tiêu 2
                    
                    # Hiển thị lời khuyên cụ thể về vị thế
                    content += "<p style='color: #22C55E;'><b>Mua:</b> Xem xét mở vị thế LONG khi có dấu hiệu xác nhận xu hướng.</p>"
                    content += f"<p><b>Giá vào lệnh đề xuất:</b> {entry_price:.2f} USDT</p>"
                    content += f"<p><b>Vùng giá vào lệnh:</b> {entry_zone_low:.2f} - {entry_zone_high:.2f} USDT</p>"
                    content += f"<p><b>Stop Loss:</b> {stop_loss:.2f} USDT (dưới mức hỗ trợ gần nhất)</p>"
                    content += f"<p><b>Take Profit 1:</b> {take_profit_1:.2f} USDT (2% lợi nhuận)</p>"
                    content += f"<p><b>Take Profit 2:</b> {take_profit_2:.2f} USDT (5% lợi nhuận)</p>"
                elif analysis.get("overall_signal") == "Bán":
                    recommendation = "NÊN VÀO LỆNH" if confidence >= 65 else "THEO DÕI"
                    content += f"<p style='color: #EF4444;'><b>Khuyến nghị: {recommendation}</b></p>"
                    
                    # Lấy các thông tin giá
                    current_price = analysis.get("price", 0)
                    resistance_prices = [sr.get("value", 0) for sr in analysis.get("support_resistance", []) if sr.get("type", "").lower() == "resistance"]
                    nearest_resistance = min(resistance_prices) if resistance_prices else current_price * 1.015
                    
                    # Tính toán mức giá vào lệnh
                    entry_price = current_price
                    entry_zone_low = current_price
                    entry_zone_high = nearest_resistance
                    
                    # Mức giá Stop Loss và Take Profit
                    stop_loss = nearest_resistance * 1.01
                    take_profit_1 = current_price * 0.98  # TP mục tiêu 1
                    take_profit_2 = current_price * 0.95  # TP mục tiêu 2
                    
                    # Hiển thị lời khuyên cụ thể về vị thế
                    content += "<p style='color: #EF4444;'><b>Bán:</b> Xem xét mở vị thế SHORT khi có dấu hiệu xác nhận xu hướng.</p>"
                    content += f"<p><b>Giá vào lệnh đề xuất:</b> {entry_price:.2f} USDT</p>"
                    content += f"<p><b>Vùng giá vào lệnh:</b> {entry_zone_low:.2f} - {entry_zone_high:.2f} USDT</p>"
                    content += f"<p><b>Stop Loss:</b> {stop_loss:.2f} USDT (trên mức kháng cự gần nhất)</p>"
                    content += f"<p><b>Take Profit 1:</b> {take_profit_1:.2f} USDT (2% lợi nhuận)</p>"
                    content += f"<p><b>Take Profit 2:</b> {take_profit_2:.2f} USDT (5% lợi nhuận)</p>"
                else:
                    content += "<p><b>Khuyến nghị: KHÔNG VÀO LỆNH</b></p>"
                    content += "<p><b>Chờ đợi:</b> Thị trường đang sideway, chờ tín hiệu rõ ràng hơn.</p>"
                
                self.market_detail_text.setHtml(content)
                
                # Cập nhật các label xu hướng
                self.short_term_trend_label.setText(analysis.get("short_term_trend", "N/A"))
                self.mid_term_trend_label.setText(analysis.get("mid_term_trend", "N/A"))
                self.long_term_trend_label.setText(analysis.get("long_term_trend", "N/A"))
                
                # Thiết lập màu sắc cho xu hướng
                if analysis.get("short_term_trend") == "Tăng":
                    self.short_term_trend_label.setStyleSheet("color: #22C55E;")
                elif analysis.get("short_term_trend") == "Giảm":
                    self.short_term_trend_label.setStyleSheet("color: #EF4444;")
                else:
                    self.short_term_trend_label.setStyleSheet("")
                
                if analysis.get("mid_term_trend") == "Tăng":
                    self.mid_term_trend_label.setStyleSheet("color: #22C55E;")
                elif analysis.get("mid_term_trend") == "Giảm":
                    self.mid_term_trend_label.setStyleSheet("color: #EF4444;")
                else:
                    self.mid_term_trend_label.setStyleSheet("")
                
                if analysis.get("long_term_trend") == "Tăng":
                    self.long_term_trend_label.setStyleSheet("color: #22C55E;")
                elif analysis.get("long_term_trend") == "Giảm":
                    self.long_term_trend_label.setStyleSheet("color: #EF4444;")
                else:
                    self.long_term_trend_label.setStyleSheet("")
                
                self.status_label.setText(f"Đã phân tích chi tiết thị trường cho {symbol} ({interval})")
            else:
                self.show_error("Lỗi khi phân tích thị trường", analysis.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích thị trường chi tiết: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi phân tích thị trường chi tiết", str(e))
    
    def save_api_settings(self):
        """Lưu cài đặt API"""
        try:
            # Lấy thông tin API
            api_key = self.api_key_edit.text()
            api_secret = self.api_secret_edit.text()
            testnet = self.testnet_checkbox.isChecked()
            
            # Kiểm tra thông tin API
            if not api_key or not api_secret:
                self.show_error("Thông tin API không hợp lệ", "API Key và API Secret không được để trống")
                return
            
            # Lưu API key và secret vào biến môi trường
            os.environ["BINANCE_TESTNET_API_KEY"] = api_key
            os.environ["BINANCE_TESTNET_API_SECRET"] = api_secret
            
            # Lưu vào file cấu hình
            api_config = {
                "api_key": api_key,
                "api_secret": api_secret,
                "testnet": testnet
            }
            
            # Tạo thư mục configs nếu chưa tồn tại
            os.makedirs("configs", exist_ok=True)
            
            # Lưu cấu hình API vào file
            with open("configs/api_config.json", "w") as f:
                json.dump(api_config, f, indent=4)
            
            logger.info("Đã lưu cấu hình API vào file configs/api_config.json")
            
            # Khởi tạo lại các đối tượng
            self.market_analyzer = MarketAnalyzer(testnet=testnet)
            self.position_manager = PositionManager(testnet=testnet)
            
            # Tải cấu hình rủi ro từ file
            risk_config = self.load_risk_config()
            
            # Khởi tạo Risk Manager
            self.risk_manager = RiskManager(self.position_manager, risk_config)
            
            # Thông báo thành công
            self.show_info("Lưu cài đặt API thành công", "Đã lưu cài đặt API và khởi tạo lại các đối tượng")
            self.status_label.setText("Đã lưu cài đặt API")
            
            # Cập nhật dữ liệu
            self.refresh_data()
            
            # Thêm thông báo vào nhật ký hệ thống
            self.add_to_system_log(f"✅ Đã lưu cài đặt API thành công (Testnet: {testnet})")
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt API: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi lưu cài đặt API", str(e))
            
    def test_api_connection(self):
        """Kiểm tra kết nối API"""
        try:
            # Lấy thông tin API
            api_key = self.api_key_edit.text()
            api_secret = self.api_secret_edit.text()
            testnet = self.testnet_checkbox.isChecked()
            
            # Kiểm tra thông tin API
            if not api_key or not api_secret:
                self.show_error("Thông tin API không hợp lệ", "API Key và API Secret không được để trống")
                return
            
            # Tạm thời lưu API key và secret vào biến môi trường
            os.environ["BINANCE_TESTNET_API_KEY"] = api_key
            os.environ["BINANCE_TESTNET_API_SECRET"] = api_secret
            
            # Hiển thị đang kiểm tra
            self.status_label.setText("Đang kiểm tra kết nối API...")
            QApplication.processEvents()
            
            # Tạo client tạm thời để kiểm tra
            from binance.client import Client
            from binance.exceptions import BinanceAPIException
            
            # Sử dụng testnet nếu được chọn
            if testnet:
                client = Client(api_key, api_secret, testnet=True)
            else:
                client = Client(api_key, api_secret)
            
            # Thử lấy thông tin tài khoản
            account_info = client.futures_account() if testnet else client.get_account()
            
            # Nếu không có lỗi, kết nối thành công
            self.show_info("Kết nối API thành công", "Đã kết nối thành công đến API Binance")
            self.status_label.setText("Kết nối API thành công")
            
            # Thêm thông báo vào nhật ký hệ thống
            self.add_to_system_log(f"✅ Kiểm tra kết nối API thành công (Testnet: {testnet})")
            
            # Trả về true nếu thành công
            return True
        
        except BinanceAPIException as e:
            logger.error(f"Lỗi API Binance: {str(e)}", exc_info=True)
            self.show_error("Lỗi kết nối API", f"Mã lỗi: {e.code}, Thông báo: {e.message}")
            self.status_label.setText("Lỗi kết nối API")
            
            # Thêm thông báo vào nhật ký hệ thống
            self.add_to_system_log(f"❌ Lỗi kết nối API: {e.message}")
            
            # Trả về false nếu có lỗi
            return False
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối API: {str(e)}", exc_info=True)
            self.show_error("Lỗi kết nối API", str(e))
            self.status_label.setText("Lỗi kết nối API")
            
            # Thêm thông báo vào nhật ký hệ thống
            self.add_to_system_log(f"❌ Lỗi kết nối API: {str(e)}")
            
            # Trả về false nếu có lỗi
            return False
            
    def save_telegram_settings(self):
        """Lưu cài đặt Telegram"""
        try:
            # Lấy thông tin Telegram
            telegram_token = self.telegram_token_edit.text()
            telegram_chat_id = self.telegram_chat_id_edit.text()
            
            # Kiểm tra thông tin Telegram
            if not telegram_token or not telegram_chat_id:
                self.show_error("Thông tin Telegram không hợp lệ", "Bot Token và Chat ID không được để trống")
                return
            
            # Lưu thông tin Telegram vào biến môi trường
            os.environ["TELEGRAM_BOT_TOKEN"] = telegram_token
            os.environ["TELEGRAM_CHAT_ID"] = telegram_chat_id
            
            # Tạo cấu hình đầy đủ
            telegram_config = {
                "bot_token": telegram_token,
                "chat_id": telegram_chat_id,
                "enabled": True,
                "notifications": {
                    "notify_position": self.notify_position_checkbox.isChecked(),
                    "notify_sltp": self.notify_sltp_checkbox.isChecked(),
                    "notify_opportunity": self.notify_opportunity_checkbox.isChecked(),
                    "notify_error": self.notify_error_checkbox.isChecked(),
                    "notify_summary": self.notify_summary_checkbox.isChecked()
                }
            }
            
            # Lưu cấu hình vào file
            config_file = "configs/telegram_config.json"
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            with open(config_file, "w") as f:
                json.dump(telegram_config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình Telegram vào file {config_file}")
            
            # Thông báo thành công
            self.show_info("Lưu cài đặt Telegram thành công", "Đã lưu thông tin Telegram vào cấu hình")
            self.status_label.setText("Đã lưu cài đặt Telegram")
            
            # Thêm thông báo vào nhật ký hệ thống
            self.add_to_system_log(f"✅ Đã lưu cài đặt Telegram thành công")
            
            # Khởi tạo và kiểm tra kết nối Telegram
            self.test_telegram_connection()
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt Telegram: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi lưu cài đặt Telegram", str(e))
            
            # Thêm thông báo vào nhật ký hệ thống
            self.add_to_system_log(f"❌ Lỗi khi lưu cài đặt Telegram: {str(e)}")
            
    def test_telegram_connection(self):
        """Kiểm tra kết nối Telegram"""
        try:
            # Lấy thông tin Telegram
            telegram_token = self.telegram_token_edit.text()
            telegram_chat_id = self.telegram_chat_id_edit.text()
            
            # Kiểm tra thông tin Telegram
            if not telegram_token or not telegram_chat_id:
                self.show_error("Thông tin Telegram không hợp lệ", "Bot Token và Chat ID không được để trống")
                return
            
            # Gửi tin nhắn test
            import requests
            
            # Thời gian hiện tại
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Tạo nội dung tin nhắn
            message = f"🔄 Kiểm tra kết nối Telegram từ ứng dụng Desktop\n⏱️ Thời gian: {current_time}"
            
            # Gửi tin nhắn
            response = requests.get(
                f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                params={"chat_id": telegram_chat_id, "text": message}
            )
            
            # Kiểm tra kết quả
            if response.status_code == 200:
                self.show_info("Kết nối Telegram thành công", "Đã gửi tin nhắn kiểm tra đến Telegram")
                self.status_label.setText("Đã kết nối Telegram thành công")
                
                # Lưu cài đặt nếu chưa lưu
                if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
                    self.save_telegram_settings()
            else:
                error_message = response.json().get("description", "Lỗi không xác định")
                self.show_error("Lỗi kết nối Telegram", f"Không thể gửi tin nhắn: {error_message}")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi kiểm tra kết nối Telegram", str(e))
    
    def save_risk_settings(self):
        """Lưu cài đặt rủi ro"""
        try:
            # Lấy thông tin cài đặt rủi ro
            risk_percentage = self.risk_percentage_spin.value() / 100
            max_positions = self.max_positions_spin.value()
            leverage = self.default_leverage_spin.value()
            position_size_percentage = self.position_size_percentage_spin.value() / 100
            stop_loss_percentage = self.stop_loss_percentage_spin.value() / 100
            take_profit_percentage = self.take_profit_percentage_spin.value() / 100
            
            trailing_stop_enabled = self.trailing_stop_checkbox.isChecked()
            partial_tp_enabled = self.partial_tp_checkbox.isChecked()
            trading_hours_enabled = self.trading_hours_checkbox.isChecked()
            
            # Tạo cấu hình rủi ro mới
            risk_config = {
                "risk_percentage": risk_percentage,
                "max_positions": max_positions,
                "leverage": leverage,
                "position_size_percentage": position_size_percentage,
                "partial_take_profit": {
                    "enabled": partial_tp_enabled,
                    "levels": [
                        {"percentage": 30, "profit_percentage": 2},
                        {"percentage": 30, "profit_percentage": 5},
                        {"percentage": 40, "profit_percentage": 10}
                    ]
                },
                "stop_loss_percentage": stop_loss_percentage,
                "take_profit_percentage": take_profit_percentage,
                "trailing_stop": {
                    "enabled": trailing_stop_enabled,
                    "activation_percentage": 2,
                    "trailing_percentage": 1.5
                },
                "trading_hours_restriction": {
                    "enabled": trading_hours_enabled,
                    "trading_hours": ["09:00-12:00", "14:00-21:00"]
                }
            }
            
            # Lưu cấu hình rủi ro vào file
            config_file = "risk_configs/desktop_risk_config.json"
            
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            # Lưu cấu hình
            with open(config_file, "w") as f:
                json.dump(risk_config, f, indent=4)
            
            # Cập nhật Risk Manager
            if self.risk_manager:
                self.risk_manager.risk_config = risk_config
            
            # Thông báo thành công
            self.show_info("Lưu cài đặt rủi ro thành công", "Đã lưu cài đặt rủi ro vào file")
            self.status_label.setText("Đã lưu cài đặt rủi ro")
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt rủi ro: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi lưu cài đặt rủi ro", str(e))
    
    def save_ui_settings(self):
        """Lưu cài đặt giao diện"""
        try:
            # Lấy thông tin cài đặt giao diện
            dark_mode = self.dark_mode_checkbox.isChecked()
            refresh_interval = self.refresh_interval_spin.value()
            notifications = self.notifications_checkbox.isChecked()
            
            # Lưu cài đặt giao diện vào QSettings
            settings = QSettings("TradingBot", "Desktop")
            settings.setValue("dark_mode", dark_mode)
            settings.setValue("refresh_interval", refresh_interval)
            settings.setValue("notifications", notifications)
            
            # Cập nhật giao diện
            self.toggle_dark_mode(dark_mode)
            
            # Cập nhật thời gian cập nhật
            if self.refresh_thread:
                self.refresh_thread.interval = refresh_interval
            
            # Thông báo thành công
            self.show_info("Lưu cài đặt giao diện thành công", "Đã lưu cài đặt giao diện")
            self.status_label.setText("Đã lưu cài đặt giao diện")
        
        except Exception as e:
            logger.error(f"Lỗi khi lưu cài đặt giao diện: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi lưu cài đặt giao diện", str(e))
    
    def toggle_dark_mode(self, enabled: bool):
        """
        Bật/tắt chế độ tối
        
        :param enabled: Bật hay tắt
        """
        if enabled:
            # Thiết lập bảng màu tối
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.black)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            
            self.setPalette(palette)
        else:
            # Khôi phục bảng màu mặc định
            self.setPalette(self.style().standardPalette())
    
    def start_service(self, service_name):
        """
        Khởi động một dịch vụ cụ thể
        
        :param service_name: Tên dịch vụ cần khởi động
        """
        try:
            logger.info(f"Đang khởi động dịch vụ {service_name}...")
            
            # Ánh xạ tên dịch vụ đến script tương ứng
            service_scripts = {
                "market_notifier": "auto_market_notifier.py",
                "unified_trading_service": "unified_trading_service.py",
                "service_manager": "enhanced_service_manager.py",
                "watchdog": "service_watchdog.py",
                "telegram_notifier": "advanced_telegram_notifier.py",
                "auto_trade": "auto_trade.py",
                "ml_training": "train_ml_model.py",
                "market_scanner": "market_scanner.py"
            }
            
            # Lấy tên script dựa trên service_name
            script = service_scripts.get(service_name)
            if not script:
                logger.error(f"Không tìm thấy script cho dịch vụ {service_name}")
                QMessageBox.critical(self, "Lỗi", f"Không tìm thấy script cho dịch vụ {service_name}")
                return False
            
            # Kiểm tra xem script có tồn tại không
            if not os.path.exists(script):
                logger.error(f"Không tìm thấy file {script}")
                QMessageBox.critical(self, "Lỗi", f"Không tìm thấy file {script}")
                return False
            
            # Khởi động dịch vụ
            pid_file = f"{service_name}.pid"
            log_file = f"{service_name}.log"
            
            # Sử dụng python để khởi động script
            cmd = f"python {script} > {log_file} 2>&1 & echo $! > {pid_file}"
            
            # Thực thi lệnh
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Cập nhật trạng thái dịch vụ
                self.service_status[service_name] = True
                
                # Cập nhật UI
                self.update_service_status(service_name)
                
                # Thêm thông báo vào nhật ký
                self.add_to_system_log(f"✅ Đã khởi động dịch vụ {service_name}")
                QMessageBox.information(self, "Thông báo", f"Đã khởi động dịch vụ {service_name} thành công")
                
                return True
            else:
                logger.error(f"Lỗi khi khởi động {service_name}: {result.stderr}")
                QMessageBox.critical(self, "Lỗi", f"Lỗi khi khởi động {service_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi khởi động dịch vụ {service_name}: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi khởi động dịch vụ {service_name}: {str(e)}")
            return False
    
    def stop_service(self, service_name):
        """
        Dừng một dịch vụ cụ thể
        
        :param service_name: Tên dịch vụ cần dừng
        """
        try:
            logger.info(f"Đang dừng dịch vụ {service_name}...")
            
            # Kiểm tra xem có file pid không
            pid_file = f"{service_name}.pid"
            
            if not os.path.exists(pid_file):
                logger.warning(f"Không tìm thấy file PID cho dịch vụ {service_name}")
                QMessageBox.warning(self, "Cảnh báo", f"Không tìm thấy thông tin PID của dịch vụ {service_name}")
                return False
            
            # Đọc PID từ file
            with open(pid_file, "r") as f:
                pid = f.read().strip()
            
            if not pid:
                logger.warning(f"PID không hợp lệ cho dịch vụ {service_name}")
                QMessageBox.warning(self, "Cảnh báo", f"PID không hợp lệ cho dịch vụ {service_name}")
                return False
            
            # Dừng process bằng PID
            import subprocess
            result = subprocess.run(f"kill {pid}", shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Xóa file PID
                os.remove(pid_file)
                
                # Cập nhật trạng thái dịch vụ
                self.service_status[service_name] = False
                
                # Cập nhật UI
                self.update_service_status(service_name)
                
                # Thêm thông báo vào nhật ký
                self.add_to_system_log(f"🛑 Đã dừng dịch vụ {service_name}")
                QMessageBox.information(self, "Thông báo", f"Đã dừng dịch vụ {service_name} thành công")
                
                return True
            else:
                logger.error(f"Lỗi khi dừng {service_name}: {result.stderr}")
                QMessageBox.critical(self, "Lỗi", f"Lỗi khi dừng {service_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Lỗi khi dừng dịch vụ {service_name}: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi dừng dịch vụ {service_name}: {str(e)}")
            return False
    
    def start_all_services(self):
        """Khởi động tất cả các dịch vụ"""
        try:
            logger.info("Đang khởi động tất cả các dịch vụ...")
            
            # Hiển thị thông báo đang khởi động
            self.status_label.setText("Đang khởi động dịch vụ...")
            
            # Phương pháp an toàn: khởi động từng dịch vụ riêng biệt
            self.add_to_system_log("🚀 Đang lần lượt khởi động các dịch vụ...")
            
            # Danh sách các dịch vụ cần khởi động
            services_to_start = [
                "market_notifier",
                "unified_trading_service",
                "service_manager",
                "watchdog_service", 
                "telegram_notifier",
                "auto_trade",
                "ml_training",
                "market_scanner"
            ]
            
            # Đếm số lượng dịch vụ khởi động thành công
            success_count = 0
            total_services = len(services_to_start)
            
            # Khởi động từng dịch vụ
            for service in services_to_start:
                if service in self.service_status and not self.service_status[service]:  # Chỉ khởi động dịch vụ chưa chạy
                    # Thêm try-except cho từng dịch vụ để một dịch vụ lỗi không ảnh hưởng đến các dịch vụ khác
                    try:
                        self.add_to_system_log(f"Đang khởi động dịch vụ {service}...")
                        if self.start_service(service):
                            success_count += 1
                            self.add_to_system_log(f"✅ Đã khởi động dịch vụ {service}")
                        else:
                            self.add_to_system_log(f"❌ Không thể khởi động dịch vụ {service}")
                    except Exception as e:
                        logger.error(f"Lỗi khi khởi động dịch vụ {service}: {str(e)}", exc_info=True)
                        self.add_to_system_log(f"❌ Lỗi khi khởi động dịch vụ {service}: {str(e)}")
                elif service in self.service_status:
                    # Dịch vụ đã chạy
                    success_count += 1
                    
                # Cập nhật UI trong khi đợi
                QApplication.processEvents()
                time.sleep(0.5)
            
            # Thông báo kết quả
            if success_count == total_services:
                self.add_to_system_log("✅ Đã khởi động tất cả dịch vụ thành công")
                QMessageBox.information(self, "Thông báo", "Đã khởi động tất cả dịch vụ thành công")
                self.status_label.setText("Tất cả dịch vụ đang chạy")
            elif success_count > 0:
                self.add_to_system_log(f"⚠️ Đã khởi động {success_count}/{total_services} dịch vụ")
                QMessageBox.warning(self, "Cảnh báo", f"Đã khởi động {success_count}/{total_services} dịch vụ")
                self.status_label.setText("Một số dịch vụ đang chạy")
            else:
                self.add_to_system_log("❌ Không thể khởi động bất kỳ dịch vụ nào")
                QMessageBox.critical(self, "Lỗi", "Không thể khởi động bất kỳ dịch vụ nào")
                self.status_label.setText("Không có dịch vụ nào đang chạy")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động tất cả dịch vụ: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi khởi động tất cả dịch vụ: {str(e)}")
            self.status_label.setText("Lỗi khi khởi động dịch vụ")
    
    def stop_all_services(self):
        """Dừng tất cả các dịch vụ"""
        try:
            logger.info("Đang dừng tất cả các dịch vụ...")
            
            # Hiển thị thông báo đang dừng
            self.status_label.setText("Đang dừng dịch vụ...")
            
            # Dừng từng dịch vụ
            success = True
            for service in self.service_status:
                if self.service_status[service]:  # Chỉ dừng dịch vụ đang chạy
                    if not self.stop_service(service):
                        success = False
            
            if success:
                self.add_to_system_log("✅ Đã dừng tất cả dịch vụ thành công")
                QMessageBox.information(self, "Thông báo", "Đã dừng tất cả dịch vụ thành công")
                self.status_label.setText("Tất cả dịch vụ đã dừng")
            else:
                self.add_to_system_log("⚠️ Một số dịch vụ không thể dừng")
                QMessageBox.warning(self, "Cảnh báo", "Một số dịch vụ không thể dừng")
                self.status_label.setText("Một số dịch vụ vẫn đang chạy")
                
        except Exception as e:
            logger.error(f"Lỗi khi dừng tất cả dịch vụ: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi dừng tất cả dịch vụ: {str(e)}")
            self.status_label.setText("Lỗi khi dừng dịch vụ")
    
    def update_service_status(self, service_name):
        """
        Cập nhật hiển thị trạng thái dịch vụ
        
        :param service_name: Tên dịch vụ cần cập nhật
        """
        # Lấy trạng thái dịch vụ
        is_running = self.service_status.get(service_name, False)
        
        # Cập nhật label và button
        if service_name == "market_notifier":
            if is_running:
                self.market_notifier_status.setText("Đang chạy")
                self.market_notifier_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_market_notifier_button.setEnabled(False)
                self.stop_market_notifier_button.setEnabled(True)
            else:
                self.market_notifier_status.setText("Chưa khởi động")
                self.market_notifier_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_market_notifier_button.setEnabled(True)
                self.stop_market_notifier_button.setEnabled(False)
                
        elif service_name == "unified_trading_service":
            if is_running:
                self.unified_trading_service_status.setText("Đang chạy")
                self.unified_trading_service_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_unified_trading_service_button.setEnabled(False)
                self.stop_unified_trading_service_button.setEnabled(True)
            else:
                self.unified_trading_service_status.setText("Chưa khởi động")
                self.unified_trading_service_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_unified_trading_service_button.setEnabled(True)
                self.stop_unified_trading_service_button.setEnabled(False)
                
        elif service_name == "service_manager":
            if is_running:
                self.service_manager_status.setText("Đang chạy")
                self.service_manager_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_service_manager_button.setEnabled(False)
                self.stop_service_manager_button.setEnabled(True)
            else:
                self.service_manager_status.setText("Chưa khởi động")
                self.service_manager_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_service_manager_button.setEnabled(True)
                self.stop_service_manager_button.setEnabled(False)
        
        elif service_name == "watchdog":
            if is_running:
                self.watchdog_status.setText("Đang chạy")
                self.watchdog_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_watchdog_button.setEnabled(False)
                self.stop_watchdog_button.setEnabled(True)
            else:
                self.watchdog_status.setText("Chưa khởi động")
                self.watchdog_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_watchdog_button.setEnabled(True)
                self.stop_watchdog_button.setEnabled(False)
                
        elif service_name == "telegram_notifier":
            if is_running:
                self.telegram_notifier_status.setText("Đang chạy")
                self.telegram_notifier_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_telegram_notifier_button.setEnabled(False)
                self.stop_telegram_notifier_button.setEnabled(True)
            else:
                self.telegram_notifier_status.setText("Chưa khởi động")
                self.telegram_notifier_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_telegram_notifier_button.setEnabled(True)
                self.stop_telegram_notifier_button.setEnabled(False)
                
        elif service_name == "auto_trade":
            if is_running:
                self.auto_trade_status.setText("Đang chạy")
                self.auto_trade_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_auto_trade_button.setEnabled(False)
                self.stop_auto_trade_button.setEnabled(True)
            else:
                self.auto_trade_status.setText("Chưa khởi động")
                self.auto_trade_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_auto_trade_button.setEnabled(True)
                self.stop_auto_trade_button.setEnabled(False)
                
        elif service_name == "ml_training":
            if is_running:
                self.ml_training_status.setText("Đang chạy")
                self.ml_training_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_ml_training_button.setEnabled(False)
                self.stop_ml_training_button.setEnabled(True)
            else:
                self.ml_training_status.setText("Chưa khởi động")
                self.ml_training_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_ml_training_button.setEnabled(True)
                self.stop_ml_training_button.setEnabled(False)
                
        elif service_name == "market_scanner":
            if is_running:
                self.market_scanner_status.setText("Đang chạy")
                self.market_scanner_status.setStyleSheet("color: #22C55E; font-weight: bold;")
                self.start_market_scanner_button.setEnabled(False)
                self.stop_market_scanner_button.setEnabled(True)
            else:
                self.market_scanner_status.setText("Chưa khởi động")
                self.market_scanner_status.setStyleSheet("color: #EF4444; font-weight: bold;")
                self.start_market_scanner_button.setEnabled(True)
                self.stop_market_scanner_button.setEnabled(False)
    
    def check_software_update(self):
        """Kiểm tra cập nhật phần mềm"""
        try:
            self.status_label.setText("Đang kiểm tra cập nhật...")
            
            # Import mô-đun cập nhật
            try:
                from auto_updater import check_for_updates, install_update
            except ImportError as e:
                self.show_error("Lỗi khi kiểm tra cập nhật", f"Không thể tải mô-đun cập nhật: {str(e)}")
                self.status_label.setText("Lỗi khi kiểm tra cập nhật")
                return
            
            # Kiểm tra cập nhật
            result = check_for_updates()
            
            if result["success"]:
                if result["has_update"]:
                    # Có cập nhật mới
                    current_version = result["current_version"]
                    new_version = result["new_version"]
                    
                    # Hiển thị thông báo cập nhật
                    message = (
                        f"Đã có phiên bản mới!\n\n"
                        f"Phiên bản hiện tại: {current_version}\n"
                        f"Phiên bản mới: {new_version}\n\n"
                        f"Bạn có muốn cập nhật lên phiên bản mới không?"
                    )
                    
                    answer = QMessageBox.question(
                        self, 
                        "Có bản cập nhật mới", 
                        message,
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if answer == QMessageBox.Yes:
                        # Thực hiện cập nhật
                        self.status_label.setText("Đang cập nhật...")
                        install_result = install_update(result["update_info"])
                        
                        if install_result["success"]:
                            self.show_info("Cập nhật", "Đang cài đặt bản cập nhật. Ứng dụng sẽ khởi động lại.")
                        else:
                            self.show_error("Lỗi cập nhật", install_result["message"])
                            self.status_label.setText("Lỗi cập nhật")
                    else:
                        self.status_label.setText("Đã bỏ qua cập nhật")
                else:
                    # Không có cập nhật mới
                    self.show_info("Kiểm tra cập nhật", f"Không có phiên bản mới. Phiên bản hiện tại: {result['current_version']}")
                    self.status_label.setText("Không có cập nhật mới")
            else:
                # Có lỗi khi kiểm tra cập nhật
                self.show_error("Lỗi kiểm tra cập nhật", result["message"])
                self.status_label.setText("Lỗi kiểm tra cập nhật")
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra cập nhật phần mềm: {str(e)}", exc_info=True)
            self.show_error("Lỗi kiểm tra cập nhật", str(e))
            self.status_label.setText("Lỗi kiểm tra cập nhật")

    def update_all_service_status(self):
        """Cập nhật hiển thị trạng thái tất cả dịch vụ"""
        for service in self.service_status:
            self.update_service_status(service)
    
    def refresh_system_logs(self):
        """Cập nhật nhật ký hệ thống"""
        try:
            logs = []
            
            # Đọc log từ telegram_notification.log (thông báo Telegram) nếu có
            if os.path.exists("telegram_notification.log"):
                with open("telegram_notification.log", "r", encoding="utf-8", errors="ignore") as f:
                    logs.append("\n=== THÔNG BÁO GIAO DỊCH ===")
                    # Lấy 30 dòng cuối chứa các thông báo quan trọng
                    lines = f.readlines()
                    notification_lines = []
                    for line in lines[-100:]:
                        if "PHÁT HIỆN CƠ HỘI GIAO DỊCH" in line or "BÁO CÁO TÌNH HÌNH THỊ TRƯỜNG" in line:
                            notification_lines.append(line.strip())
                    # Hiển thị 5 thông báo gần nhất
                    for line in notification_lines[-5:]:
                        logs.append(line.strip())
            
            # Đọc log từ thông tin vị thế và lệnh giao dịch
            if os.path.exists("auto_trade.log"):
                with open("auto_trade.log", "r", encoding="utf-8", errors="ignore") as f:
                    logs.append("\n=== NHẬT KÝ GIAO DỊCH ===")
                    lines = f.readlines()
                    trade_lines = []
                    for line in lines[-100:]:
                        if "Mở vị thế" in line or "Đóng vị thế" in line or "Stop loss" in line or "Take profit" in line:
                            trade_lines.append(line.strip())
                    # Hiển thị 5 thông báo gần nhất
                    for line in trade_lines[-5:]:
                        logs.append(line.strip())
            
            # Đọc log từ start_all_services.log nếu có
            if os.path.exists("start_all_services.log"):
                with open("start_all_services.log", "r", encoding="utf-8", errors="ignore") as f:
                    logs.append("\n=== TRẠNG THÁI HỆ THỐNG ===")
                    # Lấy 10 dòng cuối
                    lines = f.readlines()
                    for line in lines[-10:]:
                        logs.append(line.strip())
            
            # Danh sách các file log cần kiểm tra
            log_files = {
                "market_scanner": "market_scanner.log",
                "market_notifier": "market_notifier.log",
                "unified_trading_service": "unified_trading_service.log",
                "service_manager": "service_manager.log",
                "watchdog": "watchdog.log"
            }
            
            # Đọc log từ các file log dịch vụ - ưu tiên market_scanner
            for service_name, log_file in log_files.items():
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        logs.append(f"\n=== {service_name.upper()} ===")
                        # Lấy 15 dòng cuối
                        lines = f.readlines()
                        filtered_lines = []
                        for line in lines[-100:]:
                            # Lọc thông tin hữu ích
                            if "ERROR" in line or "CẢNH BÁO" in line or "Phát hiện cơ hội" in line or "Đã phân tích" in line:
                                filtered_lines.append(line.strip())
                        # Hiển thị các dòng lọc được, tối đa 15 dòng
                        for line in filtered_lines[-15:]:
                            logs.append(line.strip())
            
            # Hiển thị log với định dạng dễ đọc hơn
            formatted_logs = []
            for line in logs:
                if line.startswith("\n==="):
                    # Định dạng tiêu đề phần
                    formatted_logs.append(f"\n{line.strip('=').strip()}")
                else:
                    # Định dạng thông thường
                    formatted_logs.append(line)
            
            self.system_logs.setText("\n".join(formatted_logs))
            
            # Cuộn xuống cuối
            scrollbar = self.system_logs.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật nhật ký hệ thống: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi cập nhật nhật ký hệ thống: {str(e)}")
    
    def clear_system_logs(self):
        """Xóa nhật ký hệ thống"""
        self.system_logs.clear()
    
    def add_to_system_log(self, message):
        """
        Thêm thông báo vào nhật ký hệ thống
        
        :param message: Thông báo cần thêm
        """
        current_time = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{current_time}] {message}"
        
        # Thêm vào QTextEdit
        current_text = self.system_logs.toPlainText()
        if current_text:
            new_text = current_text + "\n" + log_message
        else:
            new_text = log_message
        
        self.system_logs.setText(new_text)
        
        # Cuộn xuống cuối
        scrollbar = self.system_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def refresh_data(self):
        """Cập nhật dữ liệu"""
        try:
            # Lấy dữ liệu thị trường
            market_data = {}
            if self.market_analyzer:
                market_overview = self.market_analyzer.get_market_overview()
                if market_overview.get("status") == "success":
                    market_data["market_overview"] = market_overview.get("data", [])
            
            # Lấy danh sách vị thế
            positions = []
            if self.position_manager:
                positions = self.position_manager.get_all_positions()
            market_data["positions"] = positions
            
            # Lấy số dư tài khoản
            account_balance = {}
            if self.position_manager:
                account_info = self.position_manager.get_account_balance()
                if account_info.get("status") == "success":
                    account_balance = account_info.get("balance", {})
            market_data["account_balance"] = account_balance
            
            # Cập nhật dữ liệu
            self.update_data(market_data)
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi cập nhật dữ liệu", str(e))
    
    def show_account_info(self):
        """Hiển thị thông tin tài khoản"""
        try:
            if not self.position_manager:
                self.show_error("Không thể hiển thị thông tin tài khoản", "Chưa khởi tạo PositionManager")
                return
            
            # Lấy thông tin tài khoản
            account_info = self.position_manager.get_account_balance()
            
            if account_info.get("status") == "success":
                balance = account_info.get("balance", {})
                
                # Tạo thông tin tài khoản
                info = f"<h3>Thông tin tài khoản</h3>"
                info += f"<p><b>Tổng số dư:</b> {balance.get('total_balance', 0):.2f} USDT</p>"
                info += f"<p><b>Số dư khả dụng:</b> {balance.get('available_balance', 0):.2f} USDT</p>"
                info += f"<p><b>Lợi nhuận chưa thực hiện:</b> {balance.get('unrealized_pnl', 0):.2f} USDT</p>"
                info += f"<p><b>Margin ban đầu của vị thế:</b> {balance.get('position_initial_margin', 0):.2f} USDT</p>"
                info += f"<p><b>Margin ban đầu của lệnh mở:</b> {balance.get('open_order_initial_margin', 0):.2f} USDT</p>"
                info += f"<p><b>Số tiền rút tối đa:</b> {balance.get('max_withdraw_amount', 0):.2f} USDT</p>"
                
                # Hiển thị thông tin
                QMessageBox.information(self, "Thông tin tài khoản", info)
            else:
                self.show_error("Lỗi khi lấy thông tin tài khoản", account_info.get("message", "Lỗi không xác định"))
        
        except Exception as e:
            logger.error(f"Lỗi khi hiển thị thông tin tài khoản: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi hiển thị thông tin tài khoản", str(e))
    
    def show_help(self):
        """Hiển thị trợ giúp"""
        help_text = """<h3>Trợ giúp</h3>
<p><b>1. Tổng quan:</b> Hiển thị số dư tài khoản, vị thế đang mở và thông tin thị trường.</p>
<p><b>2. Giao dịch:</b> Mở vị thế mới và phân tích thị trường.</p>
<p><b>3. Quản lý vị thế:</b> Quản lý các vị thế đang mở và xem lịch sử giao dịch.</p>
<p><b>4. Phân tích thị trường:</b> Phân tích kỹ thuật chi tiết.</p>
<p><b>5. Cài đặt:</b> Cấu hình API, rủi ro và giao diện.</p>

<h4>Hướng dẫn giao dịch</h4>
<p>1. Chọn cặp giao dịch và hướng giao dịch (LONG/SHORT)</p>
<p>2. Nhập kích thước vị thế hoặc nhấn "Tính toán vị thế" để tính toán tự động</p>
<p>3. Thiết lập đòn bẩy, Stop Loss và Take Profit</p>
<p>4. Nhấn "Mở Long" hoặc "Mở Short" để đặt lệnh</p>

<h4>Phân tích thị trường</h4>
<p>1. Chọn cặp giao dịch và khung thời gian</p>
<p>2. Nhấn "Phân tích" để xem phân tích kỹ thuật</p>
<p>3. Xem các chỉ báo kỹ thuật, tín hiệu và gợi ý giao dịch</p>

<h4>Quản lý vị thế</h4>
<p>1. Chọn vị thế cần quản lý</p>
<p>2. Cập nhật Stop Loss và Take Profit</p>
<p>3. Đóng vị thế khi cần thiết</p>
<p>4. Xem lịch sử giao dịch để theo dõi hiệu suất</p>

<h4>Gợi ý</h4>
<p>- Sử dụng chế độ tối để giảm mỏi mắt khi giao dịch vào ban đêm</p>
<p>- Kiểm tra trang thái kết nối ở thanh trạng thái</p>
<p>- Cập nhật dữ liệu thường xuyên để có thông tin mới nhất</p>
"""
        
        QMessageBox.information(self, "Trợ giúp", help_text)
    
    def show_missing_api_keys_error(self):
        """Hiển thị lỗi thiếu API key"""
        error_text = """<h3>Lỗi: Thiếu API Keys</h3>
<p>Ứng dụng cần API keys từ Binance Testnet để hoạt động. Vui lòng làm theo các bước sau:</p>
<ol>
<li>Truy cập trang web Binance Testnet: <a href="https://testnet.binance.vision/">https://testnet.binance.vision/</a></li>
<li>Đăng nhập và tạo API keys mới</li>
<li>Nhập API Key và API Secret vào tab Cài đặt của ứng dụng</li>
<li>Đảm bảo đã chọn "Sử dụng testnet"</li>
<li>Nhấn "Lưu cài đặt API" để áp dụng cài đặt</li>
</ol>
<p>Nếu bạn chưa có tài khoản Binance Testnet, hãy đăng ký tài khoản mới trên trang web Binance Testnet.</p>
"""
        
        QMessageBox.warning(self, "Thiếu API Keys", error_text)
    
    def show_error(self, title: str, message: str):
        """
        Hiển thị thông báo lỗi
        
        :param title: Tiêu đề
        :param message: Nội dung
        """
        QMessageBox.critical(self, title, message)
    
    def show_info(self, title: str, message: str):
        """
        Hiển thị thông báo thông tin
        
        :param title: Tiêu đề
        :param message: Nội dung
        """
        QMessageBox.information(self, title, message)
    
    def test_api_connection(self):
        """Kiểm tra kết nối API Binance"""
        try:
            from api_data_validator import validate_binance_credentials
            
            api_key = os.environ.get("BINANCE_TESTNET_API_KEY")
            api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET")
            
            result = validate_binance_credentials(api_key, api_secret, testnet=True)
            
            if result["is_valid"]:
                QMessageBox.information(self, "Kết nối thành công", 
                    "Kết nối API Binance Testnet thành công!")
            else:
                QMessageBox.warning(self, "Lỗi kết nối", 
                    f"Không thể kết nối: {result['message']}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi kiểm tra kết nối: {str(e)}")
    
    def closeEvent(self, event):
        """
        Sự kiện đóng cửa sổ
        
        :param event: Sự kiện
        """
        # Dừng thread cập nhật
        if hasattr(self, "refresh_thread") and self.refresh_thread:
            self.refresh_thread.stop()
        
        # Chấp nhận sự kiện đóng cửa sổ
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EnhancedTradingGUI()
    window.show()
    sys.exit(app.exec_())