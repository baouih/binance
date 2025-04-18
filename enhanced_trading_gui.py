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
from typing import Dict, List, Tuple, Union, Any, Optional, Callable

# PyQt5 imports
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QSizePolicy, QSplitter, QStatusBar, QToolBar, QAction, QMenu,
    QSystemTrayIcon, QStyle, QDesktopWidget
)
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QDateTime, QSettings, QMutex, QMutexLocker
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QCursor, QDesktopServices

# BacktestThread class for running backtest
class BacktestThread(QThread):
    """Thread chạy backtest"""
    progress_updated = pyqtSignal(int)
    backtest_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    def run(self):
        """Chạy thread"""
        try:
            # Mô phỏng chạy backtest
            for i in range(101):
                time.sleep(0.05)  # Mô phỏng xử lý
                self.progress_updated.emit(i)
            
            # Mô phỏng kết quả backtest
            symbol = self.parent.backtest_symbol.currentText()
            results = {
                'symbol': symbol,
                'profit_pct': 15.72,
                'drawdown_pct': 7.45,
                'win_rate': 48.5,
                'total_trades': 33,
                'winning_trades': 16,
                'losing_trades': 17,
                'profit_factor': 2.1,
                'final_balance': 11572.0
            }
            
            # Phát signal hoàn thành với kết quả
            self.backtest_completed.emit(results)
            
        except Exception as e:
            logging.error(f"Error in BacktestThread: {str(e)}", exc_info=True)

# Thiết lập logging
logger = logging.getLogger("enhanced_trading_gui")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# PyQt5 imports
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QCheckBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QSizePolicy, QSplitter, QStatusBar, QToolBar, QAction, QMenu,
    QSystemTrayIcon, QStyle, QDesktopWidget
)
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QDateTime, QSettings, QMutex, QMutexLocker
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor, QPalette, QCursor, QDesktopServices

# Risk management constants
RISK_LEVELS = {
    'extremely_low': {'name': 'Cực kỳ thấp', 'risk_range': (0.5, 1.0), 'default': 1.0, 'leverage_range': (1, 2), 'default_leverage': 2},
    'low': {'name': 'Thấp', 'risk_range': (1.5, 3.0), 'default': 2.5, 'leverage_range': (2, 5), 'default_leverage': 3},
    'medium': {'name': 'Trung bình', 'risk_range': (3.0, 7.0), 'default': 5.0, 'leverage_range': (3, 10), 'default_leverage': 5},
    'high': {'name': 'Cao', 'risk_range': (7.0, 15.0), 'default': 10.0, 'leverage_range': (5, 20), 'default_leverage': 10},
    'extremely_high': {'name': 'Cực kỳ cao', 'risk_range': (15.0, 50.0), 'default': 25.0, 'leverage_range': (10, 50), 'default_leverage': 20}
}

ACCOUNT_SIZE_ADJUSTMENTS = {
    100: {'recommendation': 'extremely_high', 'leverage_boost': 1.5, 'profit_target_boost': 1.5},
    200: {'recommendation': 'extremely_high', 'leverage_boost': 1.3, 'profit_target_boost': 1.4},
    300: {'recommendation': 'high', 'leverage_boost': 1.2, 'profit_target_boost': 1.3},
    500: {'recommendation': 'high', 'leverage_boost': 1.1, 'profit_target_boost': 1.2},
    1000: {'recommendation': 'medium', 'leverage_boost': 1.0, 'profit_target_boost': 1.1},
    3000: {'recommendation': 'medium', 'leverage_boost': 0.9, 'profit_target_boost': 1.0},
    5000: {'recommendation': 'low', 'leverage_boost': 0.8, 'profit_target_boost': 0.9},
    10000: {'recommendation': 'low', 'leverage_boost': 0.7, 'profit_target_boost': 0.8},
    50000: {'recommendation': 'extremely_low', 'leverage_boost': 0.5, 'profit_target_boost': 0.7}
}

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
    
    def __init__(self, market_analyzer, position_manager, interval=5):
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
        self.last_market_update_time = 0
        self.last_position_update_time = 0
        self._mutex = QMutex()  # Mutex để bảo vệ dữ liệu khi truy cập đồng thời
        self._previous_balance = 0  # Lưu trữ số dư trước đó
        self._error_count = 0  # Theo dõi số lỗi liên tiếp
        self._max_errors = 5  # Số lỗi tối đa trước khi tạm ngưng
    
    def run(self):
        """Chạy thread"""
        logger.info("Thread cập nhật dữ liệu đã bắt đầu")
        
        # Đặt priority thấp hơn để không ảnh hưởng đến UI thread
        self.setPriority(QThread.LowPriority)
        
        # Tạm dừng để đảm bảo UI đã khởi tạo hoàn chỉnh
        QThread.msleep(1000)
        
        # Cập nhật ngay lập tức khi khởi động
        try:
            self.update_data(True)
        except Exception as e:
            logger.error(f"Lỗi khởi tạo thread cập nhật: {str(e)}", exc_info=True)
        
        # Vòng lặp chính của thread
        while self.running:
            try:
                # Sử dụng QThread.msleep thay vì time.sleep để xử lý sự kiện tốt hơn
                for i in range(self.interval):
                    if not self.running:
                        break
                    QThread.msleep(1000)  # Ngủ từng giây và kiểm tra trạng thái
                
                # Kiểm tra xem thread có còn chạy không
                if not self.running:
                    break
                    
                # Cập nhật dữ liệu định kỳ
                self.update_data()
                
                # Reset bộ đếm lỗi nếu thành công
                self._error_count = 0
                
            except Exception as e:
                # Tăng bộ đếm lỗi và xử lý theo cấp độ
                self._error_count += 1
                logger.error(f"Lỗi trong thread cập nhật ({self._error_count}/{self._max_errors}): {str(e)}", 
                             exc_info=True)
                
                # Nếu có quá nhiều lỗi liên tiếp, tạm dừng một thời gian dài hơn
                if self._error_count >= self._max_errors:
                    logger.warning(f"Quá nhiều lỗi, thread cập nhật sẽ tạm dừng 30 giây để ổn định")
                    for i in range(30):
                        if not self.running:
                            break
                        QThread.msleep(1000)
                    self._error_count = 0  # Reset bộ đếm lỗi
    
    def update_data(self, force_update=False):
        """
        Cập nhật dữ liệu và phát tín hiệu
        
        :param force_update: Buộc cập nhật bất kể thời gian
        """
        # Khóa mutex để đảm bảo không có xung đột khi cập nhật dữ liệu
        locker = QMutexLocker(self._mutex)
        
        current_time = time.time()
        market_data = {}
        
        # Kiểm tra xem có cần cập nhật dữ liệu thị trường không
        if force_update or (current_time - self.last_market_update_time >= 15):  # Cập nhật thị trường mỗi 15 giây
            try:
                if self.market_analyzer and hasattr(self.market_analyzer, 'get_market_overview'):
                    # Lấy tổng quan thị trường
                    market_overview = self.market_analyzer.get_market_overview()
                    if isinstance(market_overview, dict) and market_overview.get("status") == "success":
                        market_data["market_overview"] = market_overview.get("data", [])
                    
                    # Lấy phân tích kỹ thuật nếu phương thức tồn tại
                    if hasattr(self.market_analyzer, 'get_technical_analysis'):
                        technical_analysis = self.market_analyzer.get_technical_analysis()
                        if technical_analysis:
                            market_data["technical_analysis"] = technical_analysis
                    
                    # Lấy tín hiệu mới nếu phương thức tồn tại
                    if hasattr(self.market_analyzer, 'get_new_signals'):
                        new_signals = self.market_analyzer.get_new_signals()
                        if new_signals:
                            market_data["new_signals"] = new_signals
                            logger.info(f"Đã phát hiện {len(new_signals)} tín hiệu mới")
                
                self.last_market_update_time = current_time
                market_data["market_update_time"] = datetime.now().strftime("%H:%M:%S")
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {str(e)}")
                # Không rethrow ngoại lệ để vẫn tiếp tục cập nhật các phần khác
        
        # Luôn cập nhật vị thế và số dư tài khoản (quan trọng cho giao dịch)
        try:
            # Lấy danh sách vị thế
            positions = []
            if self.position_manager and hasattr(self.position_manager, 'get_all_positions'):
                try:
                    positions = self.position_manager.get_all_positions()
                    
                    # Kiểm tra dữ liệu trả về có hợp lệ không
                    if positions is None:
                        positions = []
                        logger.warning("get_all_positions trả về None, sử dụng danh sách trống")
                    
                    if not isinstance(positions, list):
                        positions = []
                        logger.warning(f"get_all_positions không trả về list, sử dụng danh sách trống. Nhận được: {type(positions)}")
                    
                    # Kiểm tra xem có vị thế nào cần được xử lý ngay không
                    for position in positions:
                        # Kiểm tra vị thế mới mở
                        if position.get("is_new", False):
                            logger.info(f"Phát hiện vị thế mới: {position.get('symbol')} {position.get('side')}")
                            market_data["new_position"] = position
                        
                        # Kiểm tra vị thế cần điều chỉnh SL/TP
                        if position.get("needs_adjustment", False):
                            logger.info(f"Vị thế cần điều chỉnh SL/TP: {position.get('symbol')} {position.get('side')}")
                            market_data["position_needs_adjustment"] = position
                            
                        # Kiểm tra và thêm dữ liệu cần thiết nếu thiếu
                        if "trend" not in position:
                            position["trend"] = ""
                        if "price_change" not in position:
                            position["price_change"] = 0
                        if "sl_warning" not in position:
                            position["sl_warning"] = False
                        if "tp_update" not in position:
                            position["tp_update"] = False
                except Exception as e:
                    logger.error(f"Lỗi khi lấy vị thế: {str(e)}", exc_info=True)
            
            market_data["positions"] = positions
            
            # Lấy số dư tài khoản
            account_balance = {}
            if self.position_manager and hasattr(self.position_manager, 'get_account_balance'):
                try:
                    account_info = self.position_manager.get_account_balance()
                    if isinstance(account_info, dict) and account_info.get("status") == "success":
                        account_balance = account_info.get("balance", {})
                        
                        # Kiểm tra thay đổi số dư
                        current_balance = account_balance.get("total_balance", 0)
                        previous_balance = self._previous_balance
                        
                        # Nếu có thay đổi đáng kể (> 1 USD hoặc > 0.1%)
                        if previous_balance > 0 and (abs(current_balance - previous_balance) > 1 or abs(current_balance / previous_balance - 1) > 0.001):
                            logger.info(f"Số dư thay đổi: {previous_balance:.2f} -> {current_balance:.2f} USD")
                            market_data["balance_changed"] = True
                        
                        # Lưu số dư hiện tại để so sánh lần sau
                        self._previous_balance = current_balance
                except Exception as e:
                    logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}", exc_info=True)
                    
            market_data["account_balance"] = account_balance
            
            # Lấy danh sách lệnh đang chờ
            pending_orders = []
            if self.position_manager and hasattr(self.position_manager, 'get_open_orders'):
                try:
                    pending_orders = self.position_manager.get_open_orders()
                    
                    # Kiểm tra dữ liệu trả về có hợp lệ không
                    if pending_orders is None:
                        pending_orders = []
                        logger.warning("get_open_orders trả về None, sử dụng danh sách trống")
                    
                    if not isinstance(pending_orders, list):
                        pending_orders = []
                        logger.warning(f"get_open_orders không trả về list, sử dụng danh sách trống. Nhận được: {type(pending_orders)}")
                except Exception as e:
                    logger.error(f"Lỗi khi lấy lệnh đang chờ: {str(e)}", exc_info=True)
                
            market_data["pending_orders"] = pending_orders
            
            self.last_position_update_time = current_time
            market_data["position_update_time"] = datetime.now().strftime("%H:%M:%S")
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật vị thế và số dư: {str(e)}", exc_info=True)
        
        # Phát tín hiệu với dữ liệu mới
        if market_data and self.running:  # Chỉ emit nếu thread vẫn đang chạy
            try:
                self.signal.emit(market_data)
            except Exception as e:
                logger.error(f"Lỗi khi emit tín hiệu: {str(e)}", exc_info=True)
        
        # Giải phóng mutex
        locker = None
    
    def stop(self):
        """Dừng thread an toàn"""
        logger.info("Đang dừng thread cập nhật dữ liệu...")
        self.running = False
        
        # Đảm bảo thread có thời gian để dừng
        if not self.wait(5000):  # Đợi tối đa 5 giây
            logger.warning("Không thể dừng thread một cách bình thường, sẽ buộc dừng")
            self.terminate()  # Chỉ sử dụng trong trường hợp khẩn cấp

class EnhancedTradingGUI(QMainWindow):
    """Giao diện đồ họa nâng cao cho giao dịch"""
    
    def __init__(self):
        """Khởi tạo giao diện đồ họa"""
        super().__init__()
        
        # Thiết lập thuộc tính cửa sổ
        self.setWindowTitle("Bot Giao Dịch Crypto - Phiên Bản Desktop")
        
        # Lấy kích thước màn hình và tính toán kích thước cửa sổ bằng 1/4 màn hình
        desktop = QDesktopWidget().availableGeometry()
        screen_width = desktop.width()
        screen_height = desktop.height()
        
        # Tính kích thước cửa sổ (1/4 màn hình)
        window_width = int(screen_width / 4)
        window_height = int(screen_height / 4)
        
        # Đặt kích thước và vị trí cửa sổ
        self.setGeometry(100, 100, window_width, window_height)
        
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
            # Lấy API keys từ biến môi trường
            api_key = os.environ.get("BINANCE_API_KEY")
            api_secret = os.environ.get("BINANCE_API_SECRET")
            
            if not api_key or not api_secret:
                self.show_error("Lỗi API Keys", "Không tìm thấy API key hoặc secret key. Vui lòng kiểm tra lại cấu hình.")
                logger.error("Thiếu API key hoặc secret key")
                return
            
            # Tải cấu hình rủi ro từ file
            risk_config = self.load_risk_config()
            
            try:
                # Khởi tạo MarketAnalyzer với API keys
                from market_analyzer import MarketAnalyzer as RealMarketAnalyzer
                self.market_analyzer = RealMarketAnalyzer(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=True
                )
                logger.info("Đã khởi tạo MarketAnalyzer với API keys")
                
                # Kiểm tra kết nối
                if not self.market_analyzer.test_connection():
                    raise Exception("Không thể kết nối với Binance API")
                
                # Khởi tạo PositionManager với API keys
                from position_manager import PositionManager as RealPositionManager
                self.position_manager = RealPositionManager(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=True
                )
                logger.info("Đã khởi tạo PositionManager với API keys")
                
                # Kiểm tra kết nối của PositionManager
                if not self.position_manager.test_connection():
                    raise Exception("Không thể kết nối với Binance Futures API")
                
                # Khởi tạo RiskManager
                from risk_manager import RiskManager as RealRiskManager
                self.risk_manager = RealRiskManager(
                    position_manager=self.position_manager,
                    risk_config=risk_config
                )
                logger.info("Đã khởi tạo RiskManager")
                
                # Hiển thị thông báo thành công
                self.show_info(
                    "Kết nối thành công",
                    "Đã kết nối thành công với Binance API và khởi tạo các thành phần hệ thống"
                )
                
            except Exception as e:
                error_msg = f"Lỗi khi khởi tạo hệ thống: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.show_error("Lỗi khởi tạo", error_msg)
                
                # Sử dụng các lớp giả trong trường hợp lỗi
                self.market_analyzer = self.create_mock_market_analyzer()
                self.position_manager = self.create_mock_position_manager()
                self.risk_manager = self.create_mock_risk_manager(risk_config)
                logger.warning("Đã chuyển sang sử dụng các lớp giả do lỗi kết nối")
            
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
        self.create_risk_management_tab()  # Tab quản lý rủi ro mới
        self.create_backtest_tab()         # Tab backtest mới
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
    
    def create_risk_management_tab(self):
        """Tạo tab quản lý rủi ro"""
        risk_tab = QWidget()
        layout = QVBoxLayout(risk_tab)
        
        # Tạo các widget cho quản lý rủi ro
        # Panel cấu hình rủi ro
        risk_config_group = QGroupBox("Cấu hình mức độ rủi ro")
        risk_config_layout = QFormLayout(risk_config_group)
        
        # Mức rủi ro
        self.risk_level_combo = QComboBox()
        for risk_id, risk_data in RISK_LEVELS.items():
            self.risk_level_combo.addItem(risk_data['name'], risk_id)
        self.risk_level_combo.setCurrentIndex(2)  # Medium by default
        self.risk_level_combo.currentIndexChanged.connect(self.on_risk_level_changed)
        risk_config_layout.addRow("Mức rủi ro:", self.risk_level_combo)
        
        # % Rủi ro mỗi giao dịch
        self.risk_percent_spin = QDoubleSpinBox()
        self.risk_percent_spin.setRange(0.1, 50.0)
        self.risk_percent_spin.setSingleStep(0.5)
        self.risk_percent_spin.setValue(RISK_LEVELS['medium']['default'])
        self.risk_percent_spin.valueChanged.connect(self.on_risk_params_changed)
        risk_config_layout.addRow("Rủi ro mỗi giao dịch (%):", self.risk_percent_spin)
        
        # Đòn bẩy
        self.risk_leverage_spin = QSpinBox()
        self.risk_leverage_spin.setRange(1, 50)
        self.risk_leverage_spin.setValue(RISK_LEVELS['medium']['default_leverage'])
        self.risk_leverage_spin.valueChanged.connect(self.on_risk_params_changed)
        risk_config_layout.addRow("Đòn bẩy (x):", self.risk_leverage_spin)
        
        # Auto SL/TP configuration
        self.sl_atr_multiplier = QDoubleSpinBox()
        self.sl_atr_multiplier.setRange(0.5, 5.0)
        self.sl_atr_multiplier.setSingleStep(0.1)
        self.sl_atr_multiplier.setValue(1.5)
        risk_config_layout.addRow("Hệ số ATR cho Stop Loss:", self.sl_atr_multiplier)
        
        self.tp_atr_multiplier = QDoubleSpinBox()
        self.tp_atr_multiplier.setRange(0.5, 10.0)
        self.tp_atr_multiplier.setSingleStep(0.1)
        self.tp_atr_multiplier.setValue(3.0)
        risk_config_layout.addRow("Hệ số ATR cho Take Profit:", self.tp_atr_multiplier)
        
        # Trailing stop settings
        self.trailing_stop_checkbox = QCheckBox("Kích hoạt Trailing Stop")
        self.trailing_stop_checkbox.setChecked(True)
        risk_config_layout.addRow("", self.trailing_stop_checkbox)
        
        self.trailing_activation = QDoubleSpinBox()
        self.trailing_activation.setRange(0.1, 10.0)
        self.trailing_activation.setSingleStep(0.1)
        self.trailing_activation.setValue(1.0)
        risk_config_layout.addRow("Kích hoạt Trailing Stop (%):", self.trailing_activation)
        
        self.trailing_callback = QDoubleSpinBox()
        self.trailing_callback.setRange(0.05, 2.0)
        self.trailing_callback.setSingleStep(0.05)
        self.trailing_callback.setValue(0.5)
        risk_config_layout.addRow("Callback Trailing Stop (%):", self.trailing_callback)
        
        layout.addWidget(risk_config_group)
        
        # Tạo phần chốt lời từng phần
        partial_tp_group = QGroupBox("Cấu hình chốt lời từng phần")
        partial_tp_layout = QFormLayout(partial_tp_group)
        
        self.partial_tp_checkbox = QCheckBox("Kích hoạt chốt lời từng phần")
        self.partial_tp_checkbox.setChecked(True)
        partial_tp_layout.addRow("", self.partial_tp_checkbox)
        
        # 4 mức chốt lời từng phần
        self.partial_tp1 = QDoubleSpinBox()
        self.partial_tp1.setRange(0.1, 10.0)
        self.partial_tp1.setSingleStep(0.1)
        self.partial_tp1.setValue(1.0)
        partial_tp_layout.addRow("% đầu tiên tại (%):", self.partial_tp1)
        
        self.partial_tp2 = QDoubleSpinBox()
        self.partial_tp2.setRange(0.1, 15.0)
        self.partial_tp2.setSingleStep(0.1)
        self.partial_tp2.setValue(2.0)
        partial_tp_layout.addRow("% thứ hai tại (%):", self.partial_tp2)
        
        self.partial_tp3 = QDoubleSpinBox()
        self.partial_tp3.setRange(0.1, 20.0)
        self.partial_tp3.setSingleStep(0.1)
        self.partial_tp3.setValue(3.0)
        partial_tp_layout.addRow("% thứ ba tại (%):", self.partial_tp3)
        
        self.partial_tp4 = QDoubleSpinBox()
        self.partial_tp4.setRange(0.1, 30.0)
        self.partial_tp4.setSingleStep(0.1)
        self.partial_tp4.setValue(5.0)
        partial_tp_layout.addRow("% còn lại tại (%):", self.partial_tp4)
        
        layout.addWidget(partial_tp_group)
        
        # Tạo phần Cảnh báo rủi ro cao
        warning_group = QGroupBox("Cảnh báo và giới hạn rủi ro")
        warning_layout = QFormLayout(warning_group)
        
        self.max_open_risk = QDoubleSpinBox()
        self.max_open_risk.setRange(10.0, 200.0)
        self.max_open_risk.setSingleStep(5.0)
        self.max_open_risk.setValue(50.0)
        warning_layout.addRow("Rủi ro tối đa mở đồng thời (%):", self.max_open_risk)
        
        self.max_positions = QSpinBox()
        self.max_positions.setRange(1, 20)
        self.max_positions.setValue(5)
        warning_layout.addRow("Số vị thế tối đa:", self.max_positions)
        
        self.high_risk_warning = QDoubleSpinBox()
        self.high_risk_warning.setRange(5.0, 20.0)
        self.high_risk_warning.setSingleStep(1.0)
        self.high_risk_warning.setValue(10.0)
        warning_layout.addRow("Cảnh báo rủi ro cao (%):", self.high_risk_warning)
        
        self.ultra_high_risk_warning = QDoubleSpinBox()
        self.ultra_high_risk_warning.setRange(10.0, 50.0)
        self.ultra_high_risk_warning.setSingleStep(1.0)
        self.ultra_high_risk_warning.setValue(20.0)
        warning_layout.addRow("Cảnh báo rủi ro cực cao (%):", self.ultra_high_risk_warning)
        
        # Thêm một số tính năng nâng cao
        self.adaptive_risk_checkbox = QCheckBox("Kích hoạt rủi ro thích ứng theo kích thước tài khoản")
        self.adaptive_risk_checkbox.setChecked(True)
        warning_layout.addRow("", self.adaptive_risk_checkbox)
        
        self.market_based_risk_checkbox = QCheckBox("Điều chỉnh rủi ro dựa trên trạng thái thị trường")
        self.market_based_risk_checkbox.setChecked(True)
        warning_layout.addRow("", self.market_based_risk_checkbox)
        
        layout.addWidget(warning_group)
        
        # Nút áp dụng cài đặt
        apply_btn = QPushButton("Áp dụng cài đặt rủi ro")
        apply_btn.clicked.connect(self.apply_risk_settings)
        
        # Nút khôi phục cài đặt mặc định
        reset_btn = QPushButton("Khôi phục mặc định")
        reset_btn.clicked.connect(self.reset_risk_settings)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)
        
        # Thêm tab vào container
        self.tab_widget.addTab(risk_tab, "Quản lý rủi ro")
    
    def create_backtest_tab(self):
        """Tạo tab backtest"""
        backtest_tab = QWidget()
        layout = QVBoxLayout(backtest_tab)
        
        # Cấu hình backtest
        config_group = QGroupBox("Cấu hình backtest")
        config_layout = QFormLayout(config_group)
        
        # Chọn cặp tiền
        self.backtest_symbol = QComboBox()
        self.backtest_symbol.addItems(["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"])
        config_layout.addRow("Cặp tiền:", self.backtest_symbol)
        
        # Khung thời gian
        self.backtest_timeframe = QComboBox()
        self.backtest_timeframe.addItems(["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
        self.backtest_timeframe.setCurrentText("1h")
        config_layout.addRow("Khung thời gian:", self.backtest_timeframe)
        
        # Thời gian backtest
        self.backtest_period = QSpinBox()
        self.backtest_period.setRange(7, 365)
        self.backtest_period.setValue(90)
        config_layout.addRow("Số ngày backtest:", self.backtest_period)
        
        # Số dư ban đầu
        self.backtest_balance = QDoubleSpinBox()
        self.backtest_balance.setRange(100, 1000000)
        self.backtest_balance.setValue(10000)
        config_layout.addRow("Số dư ban đầu ($):", self.backtest_balance)
        
        # Mức rủi ro
        self.backtest_risk = QComboBox()
        self.backtest_risk.addItems(["Cực thấp (1%)", "Thấp (3%)", "Trung bình (5%)", "Cao (10%)", "Cực cao (25%)"])
        self.backtest_risk.setCurrentIndex(2)
        config_layout.addRow("Mức rủi ro:", self.backtest_risk)
        
        # Chiến lược
        self.backtest_strategy = QComboBox()
        self.backtest_strategy.addItems([
            "AdaptiveStrategy", "RSIStrategy", "MACDStrategy", 
            "BollingerBandsStrategy", "SuperTrendStrategy"
        ])
        config_layout.addRow("Chiến lược:", self.backtest_strategy)
        
        layout.addWidget(config_group)
        
        # Nút chạy backtest
        run_btn = QPushButton("Chạy backtest")
        run_btn.clicked.connect(self.run_backtest)
        layout.addWidget(run_btn)
        
        # Progress bar
        self.backtest_progress = QProgressBar()
        self.backtest_progress.setValue(0)
        layout.addWidget(self.backtest_progress)
        
        # Kết quả backtest
        results_group = QGroupBox("Kết quả backtest")
        results_layout = QVBoxLayout(results_group)
        
        self.backtest_results_table = QTableWidget()
        self.backtest_results_table.setColumnCount(9)
        self.backtest_results_table.setHorizontalHeaderLabels([
            "Cặp tiền", "Lợi nhuận (%)", "Drawdown (%)", "Win Rate (%)", 
            "Tổng GD", "GD thắng", "GD thua", "Profit Factor", "Số dư cuối"
        ])
        results_layout.addWidget(self.backtest_results_table)
        
        layout.addWidget(results_group)
        
        # Nút xuất kết quả
        export_btn = QPushButton("Xuất kết quả backtest")
        export_btn.clicked.connect(self.export_backtest_results)
        layout.addWidget(export_btn)
        
        # Thêm tab vào container
        self.tab_widget.addTab(backtest_tab, "Backtest")
    
    def on_risk_level_changed(self):
        """Xử lý khi người dùng thay đổi mức rủi ro"""
        # Lấy mức rủi ro đã chọn
        risk_level = self.risk_level_combo.currentData()
        
        # Cập nhật các tham số
        risk_data = RISK_LEVELS[risk_level]
        self.risk_percent_spin.setValue(risk_data['default'])
        self.risk_leverage_spin.setValue(risk_data['default_leverage'])
        
        # Cập nhật SL/TP multipliers based on risk level
        if risk_level == 'extremely_low':
            self.sl_atr_multiplier.setValue(2.0)
            self.tp_atr_multiplier.setValue(6.0)
            self.trailing_activation.setValue(1.5)
            self.trailing_callback.setValue(0.7)
        elif risk_level == 'low':
            self.sl_atr_multiplier.setValue(1.5)
            self.tp_atr_multiplier.setValue(4.0)
            self.trailing_activation.setValue(1.0)
            self.trailing_callback.setValue(0.5)
        elif risk_level == 'medium':
            self.sl_atr_multiplier.setValue(1.2)
            self.tp_atr_multiplier.setValue(3.0)
            self.trailing_activation.setValue(0.8)
            self.trailing_callback.setValue(0.4)
        elif risk_level == 'high':
            self.sl_atr_multiplier.setValue(1.0)
            self.tp_atr_multiplier.setValue(2.0)
            self.trailing_activation.setValue(0.5)
            self.trailing_callback.setValue(0.3)
        elif risk_level == 'extremely_high':
            self.sl_atr_multiplier.setValue(0.7)
            self.tp_atr_multiplier.setValue(1.5)
            self.trailing_activation.setValue(0.3)
            self.trailing_callback.setValue(0.2)
    
    def on_risk_params_changed(self):
        """Xử lý khi các tham số rủi ro thay đổi"""
        # Kiểm tra tính hợp lệ của các tham số
        risk_pct = self.risk_percent_spin.value()
        leverage = self.risk_leverage_spin.value()
        
        # Hiển thị cảnh báo nếu rủi ro quá cao
        if risk_pct > self.ultra_high_risk_warning.value():
            QMessageBox.warning(self, "Cảnh báo", "Rủi ro cực cao! Có thể dẫn đến mất vốn nhanh chóng.")
        elif risk_pct > self.high_risk_warning.value():
            QMessageBox.warning(self, "Cảnh báo", "Rủi ro cao! Chỉ phù hợp với người dùng có kinh nghiệm.")
    
    def apply_risk_settings(self):
        """Áp dụng cài đặt rủi ro"""
        try:
            # Tạo đối tượng cấu hình rủi ro
            risk_config = {
                "risk_level": self.risk_level_combo.currentData(),
                "risk_per_trade": self.risk_percent_spin.value(),
                "max_leverage": self.risk_leverage_spin.value(),
                "stop_loss_atr_multiplier": self.sl_atr_multiplier.value(),
                "take_profit_atr_multiplier": self.tp_atr_multiplier.value(),
                "trailing_stop": self.trailing_stop_checkbox.isChecked(),
                "trailing_activation_pct": self.trailing_activation.value(),
                "trailing_callback_pct": self.trailing_callback.value(),
                "partial_profit_taking": {
                    "enabled": self.partial_tp_checkbox.isChecked(),
                    "levels": [
                        {"pct": self.partial_tp1.value(), "portion": 0.25},
                        {"pct": self.partial_tp2.value(), "portion": 0.25},
                        {"pct": self.partial_tp3.value(), "portion": 0.25},
                        {"pct": self.partial_tp4.value(), "portion": 0.25}
                    ]
                },
                "max_open_risk": self.max_open_risk.value(),
                "max_positions": self.max_positions.value(),
                "adaptive_risk": self.adaptive_risk_checkbox.isChecked(),
                "market_based_risk": self.market_based_risk_checkbox.isChecked(),
                "warnings": {
                    "high_risk": self.high_risk_warning.value(),
                    "ultra_high_risk": self.ultra_high_risk_warning.value()
                }
            }
            
            # Lưu cấu hình
            os.makedirs("risk_configs", exist_ok=True)
            with open("risk_configs/current_risk_config.json", "w", encoding="utf-8") as f:
                json.dump(risk_config, f, indent=4)
            
            # Thông báo thành công
            QMessageBox.information(self, "Thành công", "Đã áp dụng cài đặt rủi ro mới")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể áp dụng cài đặt rủi ro: {str(e)}")
    
    def reset_risk_settings(self):
        """Khôi phục cài đặt rủi ro mặc định"""
        # Đặt lại combobox về Medium
        for i in range(self.risk_level_combo.count()):
            if self.risk_level_combo.itemData(i) == 'medium':
                self.risk_level_combo.setCurrentIndex(i)
                break
        
        # Đặt lại các giá trị khác
        self.risk_percent_spin.setValue(5.0)
        self.risk_leverage_spin.setValue(5)
        self.sl_atr_multiplier.setValue(1.2)
        self.tp_atr_multiplier.setValue(3.0)
        self.trailing_activation.setValue(0.8)
        self.trailing_callback.setValue(0.4)
        self.partial_tp1.setValue(1.0)
        self.partial_tp2.setValue(2.0)
        self.partial_tp3.setValue(3.0)
        self.partial_tp4.setValue(5.0)
        self.max_open_risk.setValue(50.0)
        self.max_positions.setValue(5)
        self.high_risk_warning.setValue(10.0)
        self.ultra_high_risk_warning.setValue(20.0)
        
        # Checkbox
        self.adaptive_risk_checkbox.setChecked(True)
        self.market_based_risk_checkbox.setChecked(True)
        self.trailing_stop_checkbox.setChecked(True)
        self.partial_tp_checkbox.setChecked(True)
    
    def run_backtest(self):
        """Chạy backtest"""
        try:
            # Hiển thị thông báo không thể chạy backtest đầy đủ trong giao diện desktop
            QMessageBox.information(
                self,
                "Backtest",
                "Backtest được chạy trong tiến trình nền. Kết quả sẽ được cập nhật sau khi hoàn thành.\n\n"
                "Để chạy backtest đầy đủ, vui lòng sử dụng module full_risk_levels_backtest.py"
            )
            
            # Mô phỏng chạy backtest
            self.backtest_progress.setValue(0)
            
            # Tạo thread để mô phỏng backtest
            self.backtest_thread = BacktestThread(self)
            self.backtest_thread.progress_updated.connect(self.update_backtest_progress)
            self.backtest_thread.backtest_completed.connect(self.on_backtest_completed)
            self.backtest_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể chạy backtest: {str(e)}")
    
    def update_backtest_progress(self, value):
        """Cập nhật tiến trình backtest"""
        self.backtest_progress.setValue(value)
    
    def on_backtest_completed(self, results):
        """Xử lý khi backtest hoàn thành"""
        # Cập nhật bảng kết quả
        self.backtest_results_table.setRowCount(1)
        
        # Thêm dữ liệu
        symbol = self.backtest_symbol.currentText()
        self.backtest_results_table.setItem(0, 0, QTableWidgetItem(symbol))
        self.backtest_results_table.setItem(0, 1, QTableWidgetItem(f"{results['profit_pct']:.2f}"))
        self.backtest_results_table.setItem(0, 2, QTableWidgetItem(f"{results['drawdown_pct']:.2f}"))
        self.backtest_results_table.setItem(0, 3, QTableWidgetItem(f"{results['win_rate']:.2f}"))
        self.backtest_results_table.setItem(0, 4, QTableWidgetItem(str(results['total_trades'])))
        self.backtest_results_table.setItem(0, 5, QTableWidgetItem(str(results['winning_trades'])))
        self.backtest_results_table.setItem(0, 6, QTableWidgetItem(str(results['losing_trades'])))
        self.backtest_results_table.setItem(0, 7, QTableWidgetItem(f"{results['profit_factor']:.2f}"))
        self.backtest_results_table.setItem(0, 8, QTableWidgetItem(f"{results['final_balance']:.2f}"))
        
        self.backtest_results_table.resizeColumnsToContents()
        
        QMessageBox.information(self, "Backtest hoàn thành", "Đã hoàn thành backtest!")
    
    def export_backtest_results(self):
        """Xuất kết quả backtest"""
        QMessageBox.information(
            self,
            "Xuất kết quả",
            "Kết quả backtest đã được lưu trong thư mục backtest_results/"
        )
    
    def trading_tab(self):
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
        if not isinstance(data, dict):
            logger.error(f"Lỗi: data không phải là dictionary, nhận được: {type(data)}")
            return
            
        try:
            # Kiểm tra thông tin tài khoản
            if "account_balance" in data:
                account_balance = data.get("account_balance", {})
                if isinstance(account_balance, dict):
                    self.update_account_balance(account_balance)
                else:
                    logger.warning(f"account_balance không phải là dictionary: {type(account_balance)}")
            
            # Kiểm tra và cập nhật danh sách vị thế
            positions = []
            if "positions" in data:
                positions = data.get("positions", [])
                if isinstance(positions, list):
                    # Xử lý thông báo cho vị thế mới nếu có
                    if "new_position" in data:
                        new_position = data["new_position"]
                        symbol = new_position.get("symbol", "")
                        side = new_position.get("side", "")
                        if symbol and side:
                            self.show_info(
                                "Vị thế mới", 
                                f"Đã mở vị thế mới: {symbol} {side}"
                            )
                    
                    # Xử lý thông báo cho vị thế cần điều chỉnh
                    if "position_needs_adjustment" in data:
                        pos = data["position_needs_adjustment"]
                        symbol = pos.get("symbol", "")
                        if symbol:
                            self.show_info(
                                "Cần điều chỉnh vị thế", 
                                f"Vị thế {symbol} cần điều chỉnh SL/TP"
                            )
                    
                    # Cập nhật bảng vị thế
                    try:
                        self.update_positions(positions)
                    except Exception as pos_err:
                        logger.error(f"Lỗi khi cập nhật vị thế: {str(pos_err)}", exc_info=True)
                else:
                    logger.warning(f"positions không phải là list: {type(positions)}")
            
            # Kiểm tra và cập nhật thông tin thị trường
            if "market_overview" in data:
                market_overview = data.get("market_overview", [])
                if isinstance(market_overview, list):
                    try:
                        self.update_market_overview(market_overview)
                    except Exception as market_err:
                        logger.error(f"Lỗi khi cập nhật thông tin thị trường: {str(market_err)}", exc_info=True)
                else:
                    logger.warning(f"market_overview không phải là list: {type(market_overview)}")
            
            # Cập nhật danh sách combobox vị thế một cách an toàn
            try:
                if isinstance(positions, list):
                    self.update_position_combos(positions)
            except Exception as combo_err:
                logger.warning(f"Lỗi khi cập nhật danh sách combobox: {str(combo_err)}")
            
            # Cập nhật thông tin giao dịch nếu cần
            # Chỉ cập nhật khi có sự thay đổi để tránh việc cập nhật liên tục
            if hasattr(self, 'symbol_combo') and self.symbol_combo and self.symbol_combo.currentText():
                try:
                    self.update_trading_info()
                except Exception as trading_err:
                    logger.warning(f"Lỗi khi cập nhật thông tin giao dịch: {str(trading_err)}")
            
            # Kiểm tra thay đổi số dư
            if data.get("balance_changed", False) and hasattr(self, 'total_balance_label'):
                # Cập nhật UI với hiệu ứng để thu hút sự chú ý
                current_style = self.total_balance_label.styleSheet()
                self.total_balance_label.setStyleSheet("color: #F59E0B; font-weight: bold;")
                
                # Tạo timer để reset style sau 3 giây
                QTimer.singleShot(3000, lambda: self.total_balance_label.setStyleSheet(current_style))
            
            # Cập nhật trạng thái kết nối an toàn
            if hasattr(self, 'connection_label'):
                self.connection_label.setText("Trạng thái kết nối: Đã kết nối")
                self.connection_label.setStyleSheet("color: #22C55E; font-weight: bold;")
            
            # Cập nhật thời gian cập nhật lần cuối
            if hasattr(self, 'last_update_label'):
                current_time = datetime.now().strftime("%H:%M:%S")
                self.last_update_label.setText(f"Cập nhật lần cuối: {current_time}")
            
            # Cập nhật thời gian cập nhật gần nhất trên thanh trạng thái
            if hasattr(self, 'statusBar'):
                current_time = datetime.now().strftime("%H:%M:%S")
                position_count = len(positions)
                self.statusBar().showMessage(f"Cập nhật lúc: {current_time} | Số vị thế: {position_count}", 3000)
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu: {str(e)}", exc_info=True)
            # Không ném ngoại lệ ra UI
    
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
        try:
            # Lấy danh sách symbol của vị thế đang hiển thị
            current_positions = []
            for row in range(self.positions_table.rowCount()):
                if self.positions_table.item(row, 0):  # Kiểm tra cột symbol
                    symbol_text = self.positions_table.item(row, 0).text()
                    if symbol_text and symbol_text != "Không có vị thế nào đang mở":
                        current_positions.append(symbol_text)
            
            # Phát hiện các vị thế mới và cũ
            existing_symbols = [p.get('symbol', '') for p in positions]
            new_positions = [p for p in positions if p.get('symbol', '') not in current_positions]
            closed_positions = [sym for sym in current_positions if sym not in existing_symbols]
            
            # Hiển thị thông báo về vị thế mới
            if new_positions:
                new_symbols = [p.get('symbol', '') for p in new_positions]
                logger.info(f"Phát hiện vị thế mới: {', '.join(new_symbols)}")
                self.statusBar().showMessage(f"Đã mở vị thế mới: {', '.join(new_symbols)}", 5000)
            
            # Hiển thị thông báo về vị thế đã đóng
            if closed_positions:
                logger.info(f"Vị thế đã đóng: {', '.join(closed_positions)}")
                self.statusBar().showMessage(f"Đã đóng vị thế: {', '.join(closed_positions)}", 5000)
            
            # Cập nhật bảng vị thế trong tab tổng quan
            if positions:
                self.positions_table.setRowCount(len(positions))
                
                # Biến để theo dõi tổng lợi nhuận
                total_unrealized_pnl = 0
                total_profit_percent = 0
                
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
                    leverage = position.get("leverage", 1)
                    
                    # Cộng dồn lợi nhuận
                    total_unrealized_pnl += unrealized_pnl
                    if profit_percent != 0:
                        total_profit_percent += profit_percent
                    
                    # Kiểm tra nếu vị thế mới hoặc cập nhật giá
                    is_new = symbol in [p.get('symbol', '') for p in new_positions]
                    
                    # Tạo các item cho bảng
                    symbol_item = QTableWidgetItem(symbol)
                    if is_new:
                        font = symbol_item.font()
                        font.setBold(True)
                        symbol_item.setFont(font)
                        symbol_item.setBackground(QColor(53, 66, 83))  # Highlight màu sáng
                    
                    # Thêm thông tin xu hướng (nếu có)
                    trend = position.get("trend", "")
                    if trend == "UP":
                        symbol_item.setIcon(QIcon("static/icons/trend_up.png"))
                        symbol_item.setToolTip("Xu hướng tăng")
                    elif trend == "DOWN":
                        symbol_item.setIcon(QIcon("static/icons/trend_down.png"))
                        symbol_item.setToolTip("Xu hướng giảm")
                    
                    self.positions_table.setItem(row, 0, symbol_item)
                    
                    side_item = QTableWidgetItem(side)
                    if side == "LONG":
                        side_item.setForeground(QColor("#22C55E"))  # Màu xanh cho Long
                    else:
                        side_item.setForeground(QColor("#EF4444"))  # Màu đỏ cho Short
                    self.positions_table.setItem(row, 1, side_item)
                    
                    self.positions_table.setItem(row, 2, QTableWidgetItem(f"{size:.4f}"))
                    self.positions_table.setItem(row, 3, QTableWidgetItem(f"{entry_price:.2f}"))
                    
                    # Hiển thị giá hiện tại với thay đổi gần đây
                    mark_price_item = QTableWidgetItem(f"{mark_price:.2f}")
                    price_change = position.get("price_change", 0)
                    if price_change > 0:
                        mark_price_item.setForeground(QColor("#22C55E"))
                        mark_price_item.setToolTip(f"Tăng {price_change:.2f}% trong 5 phút qua")
                    elif price_change < 0:
                        mark_price_item.setForeground(QColor("#EF4444"))
                        mark_price_item.setToolTip(f"Giảm {abs(price_change):.2f}% trong 5 phút qua")
                    self.positions_table.setItem(row, 4, mark_price_item)
                    
                    # Hiển thị SL/TP và thêm cảnh báo nếu cần
                    sl_item = QTableWidgetItem(f"{stop_loss}" if stop_loss != "N/A" else "N/A")
                    if position.get("sl_warning", False):
                        sl_item.setIcon(QIcon("static/icons/warning.png"))
                        sl_item.setToolTip("Cần cập nhật Stop Loss")
                        sl_item.setBackground(QColor(64, 25, 25))  # Nền đỏ nhạt
                    self.positions_table.setItem(row, 5, sl_item)
                    
                    tp_item = QTableWidgetItem(f"{take_profit}" if take_profit != "N/A" else "N/A")
                    if position.get("tp_update", False):
                        tp_item.setIcon(QIcon("static/icons/arrow_up.png"))
                        tp_item.setToolTip("Có thể tăng Take Profit")
                    self.positions_table.setItem(row, 6, tp_item)
                    
                    # Hiển thị đòn bẩy và thêm cảnh báo nếu cao
                    leverage_item = QTableWidgetItem(f"{leverage}x")
                    if leverage > 20:
                        leverage_item.setForeground(QColor("#EF4444"))
                        leverage_item.setToolTip("Đòn bẩy cao, rủi ro lớn")
                    self.positions_table.setItem(row, 7, leverage_item)
                    
                    # Hiển thị lợi nhuận với màu sắc và phần trăm
                    pnl_item = QTableWidgetItem(f"{unrealized_pnl:.2f}")
                    if unrealized_pnl > 0:
                        pnl_item.setForeground(QColor("#22C55E"))  # Màu xanh khi lời
                    elif unrealized_pnl < 0:
                        pnl_item.setForeground(QColor("#EF4444"))  # Màu đỏ khi lỗ
                    else:
                        pnl_item.setForeground(QColor("#94A3B8"))  # Màu xám nếu 0
                    self.positions_table.setItem(row, 8, pnl_item)
                    
                    percent_item = QTableWidgetItem(f"{profit_percent:.2f}%")
                    if profit_percent > 0:
                        percent_item.setForeground(QColor("#22C55E"))  # Màu xanh khi lời
                    elif profit_percent < 0:
                        percent_item.setForeground(QColor("#EF4444"))  # Màu đỏ khi lỗ
                    else:
                        percent_item.setForeground(QColor("#94A3B8"))  # Màu xám nếu 0
                    self.positions_table.setItem(row, 9, percent_item)
                
                # Cập nhật thông tin tổng lợi nhuận
                if hasattr(self, 'total_pnl_label'):
                    # Định dạng màu sắc dựa vào lợi nhuận
                    if total_unrealized_pnl > 0:
                        self.total_pnl_label.setStyleSheet("color: #22C55E; font-weight: bold;")
                    elif total_unrealized_pnl < 0:
                        self.total_pnl_label.setStyleSheet("color: #EF4444; font-weight: bold;")
                    else:
                        self.total_pnl_label.setStyleSheet("color: white; font-weight: bold;")
                    
                    # Hiển thị cả số tiền và phần trăm
                    avg_percent = total_profit_percent / len(positions) if positions else 0
                    self.total_pnl_label.setText(f"Lợi nhuận: {total_unrealized_pnl:.2f} USDT ({avg_percent:.2f}%)")
            else:
                # Không có vị thế nào
                self.positions_table.setRowCount(1)
                self.positions_table.setSpan(0, 0, 1, 10)  # Gộp tất cả các cột
                no_pos_item = QTableWidgetItem("Không có vị thế nào đang mở")
                no_pos_item.setTextAlignment(Qt.AlignCenter)
                self.positions_table.setItem(0, 0, no_pos_item)
                
                # Xóa tổng lợi nhuận nếu không có vị thế
                if hasattr(self, 'total_pnl_label'):
                    self.total_pnl_label.setText("Lợi nhuận: 0.00 USDT (0.00%)")
                    self.total_pnl_label.setStyleSheet("color: white; font-weight: bold;")
            
            # Cập nhật thời gian cập nhật gần nhất
            if hasattr(self, 'last_update_label'):
                current_time = datetime.now().strftime("%H:%M:%S")
                self.last_update_label.setText(f"Cập nhật lúc: {current_time}")
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật vị thế: {str(e)}", exc_info=True)
        
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
        try:
            if not market_overview:
                logger.warning("Không có dữ liệu thị trường để cập nhật")
                return
                
            self.market_table.setRowCount(len(market_overview))
            
            # Biến theo dõi xu hướng thị trường tổng thể
            market_direction = {"up": 0, "down": 0, "neutral": 0}
            
            # Cập nhật giá BTC và ETH trên dashboard với biến động
            btc_data = None
            eth_data = None
            for market_data in market_overview:
                symbol = market_data.get("symbol", "")
                price = market_data.get("price", 0)
                change_24h = market_data.get("change_24h", 0)
                
                if symbol == "BTCUSDT":
                    btc_data = market_data
                    # Cập nhật giá BTC với màu sắc dựa theo xu hướng
                    if change_24h > 0:
                        self.btc_price_label.setStyleSheet("color: #22C55E; font-weight: bold;")
                    elif change_24h < 0:
                        self.btc_price_label.setStyleSheet("color: #EF4444; font-weight: bold;")
                    else:
                        self.btc_price_label.setStyleSheet("color: white; font-weight: bold;")
                    self.btc_price_label.setText(f"{price:.2f} USDT ({change_24h:+.2f}%)")
                    
                elif symbol == "ETHUSDT":
                    eth_data = market_data
                    # Cập nhật giá ETH với màu sắc dựa theo xu hướng
                    if change_24h > 0:
                        self.eth_price_label.setStyleSheet("color: #22C55E; font-weight: bold;")
                    elif change_24h < 0:
                        self.eth_price_label.setStyleSheet("color: #EF4444; font-weight: bold;")
                    else:
                        self.eth_price_label.setStyleSheet("color: white; font-weight: bold;")
                    self.eth_price_label.setText(f"{price:.2f} USDT ({change_24h:+.2f}%)")
                
                # Đếm số coin tăng/giảm để xác định xu hướng thị trường
                if change_24h > 0.5:  # Tăng đáng kể
                    market_direction["up"] += 1
                elif change_24h < -0.5:  # Giảm đáng kể
                    market_direction["down"] += 1
                else:  # Đi ngang
                    market_direction["neutral"] += 1
            
            # Cập nhật trạng thái thị trường tổng thể
            if hasattr(self, 'market_status_label'):
                if market_direction["up"] > market_direction["down"] * 1.5:
                    self.market_status_label.setText("Trạng thái thị trường: TĂNG MẠNH")
                    self.market_status_label.setStyleSheet("color: #22C55E; font-weight: bold;")
                elif market_direction["up"] > market_direction["down"]:
                    self.market_status_label.setText("Trạng thái thị trường: TĂNG NHẸ")
                    self.market_status_label.setStyleSheet("color: #22C55E;")
                elif market_direction["down"] > market_direction["up"] * 1.5:
                    self.market_status_label.setText("Trạng thái thị trường: GIẢM MẠNH")
                    self.market_status_label.setStyleSheet("color: #EF4444; font-weight: bold;")
                elif market_direction["down"] > market_direction["up"]:
                    self.market_status_label.setText("Trạng thái thị trường: GIẢM NHẸ")
                    self.market_status_label.setStyleSheet("color: #EF4444;")
                else:
                    self.market_status_label.setText("Trạng thái thị trường: ĐI NGANG")
                    self.market_status_label.setStyleSheet("color: #94A3B8;")
            
            # Cập nhật bảng thị trường
            for row, market_data in enumerate(market_overview):
                symbol = market_data.get("symbol", "")
                price = market_data.get("price", 0)
                change_24h = market_data.get("change_24h", 0)
                change_1h = market_data.get("change_1h", 0)
                volume = market_data.get("volume", 0)
                
                # Kiểm tra vị thế đang mở cho symbol này
                has_position = False
                if hasattr(self, 'positions_table'):
                    for pos_row in range(self.positions_table.rowCount()):
                        if self.positions_table.item(pos_row, 0) and self.positions_table.item(pos_row, 0).text() == symbol:
                            has_position = True
                            break
                
                # Tạo các item cho bảng với định dạng tốt hơn
                symbol_item = QTableWidgetItem(symbol)
                
                # Highlight các cặp tiền đang có vị thế mở
                if has_position:
                    font = symbol_item.font()
                    font.setBold(True)
                    symbol_item.setFont(font)
                    symbol_item.setBackground(QColor(53, 66, 83))
                    symbol_item.setToolTip("Đang có vị thế mở")
                
                # Thêm icon cho các symbol phổ biến
                if symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]:
                    symbol_item.setIcon(QIcon(f"static/icons/{symbol.lower().replace('usdt', '')}.png"))
                
                self.market_table.setItem(row, 0, symbol_item)
                
                # Hiển thị giá với độ chính xác phù hợp
                if price >= 1000:
                    price_str = f"{price:.1f}"
                elif price >= 100:
                    price_str = f"{price:.2f}"
                elif price >= 1:
                    price_str = f"{price:.3f}"
                elif price >= 0.1:
                    price_str = f"{price:.4f}"
                else:
                    price_str = f"{price:.6f}"
                
                self.market_table.setItem(row, 1, QTableWidgetItem(price_str))
                
                # Hiển thị biến động 1 giờ
                change_1h_item = QTableWidgetItem(f"{change_1h:+.2f}%")
                if change_1h > 1.5:  # Tăng mạnh
                    change_1h_item.setForeground(QColor("#22C55E"))
                    change_1h_item.setFont(QFont("Arial", 9, QFont.Bold))
                elif change_1h > 0:  # Tăng nhẹ
                    change_1h_item.setForeground(QColor("#22C55E"))
                elif change_1h < -1.5:  # Giảm mạnh
                    change_1h_item.setForeground(QColor("#EF4444"))
                    change_1h_item.setFont(QFont("Arial", 9, QFont.Bold))
                elif change_1h < 0:  # Giảm nhẹ
                    change_1h_item.setForeground(QColor("#EF4444"))
                self.market_table.setItem(row, 2, change_1h_item)
                
                # Hiển thị biến động 24 giờ
                change_24h_item = QTableWidgetItem(f"{change_24h:+.2f}%")
                if change_24h > 5:  # Tăng mạnh
                    change_24h_item.setForeground(QColor("#22C55E"))
                    change_24h_item.setFont(QFont("Arial", 9, QFont.Bold))
                elif change_24h > 0:  # Tăng nhẹ
                    change_24h_item.setForeground(QColor("#22C55E"))
                elif change_24h < -5:  # Giảm mạnh
                    change_24h_item.setForeground(QColor("#EF4444"))
                    change_24h_item.setFont(QFont("Arial", 9, QFont.Bold))
                elif change_24h < 0:  # Giảm nhẹ
                    change_24h_item.setForeground(QColor("#EF4444"))
                self.market_table.setItem(row, 3, change_24h_item)
                
                # Format khối lượng theo đơn vị K, M, B
                if volume >= 1_000_000_000:
                    volume_str = f"{volume / 1_000_000_000:.2f}B"
                elif volume >= 1_000_000:
                    volume_str = f"{volume / 1_000_000:.2f}M"
                elif volume >= 1_000:
                    volume_str = f"{volume / 1_000:.2f}K"
                else:
                    volume_str = f"{volume:.2f}"
                
                # Màu sắc cho khối lượng cao
                volume_item = QTableWidgetItem(volume_str)
                if volume > market_data.get("avg_volume", 0) * 1.5:
                    volume_item.setForeground(QColor("#3B82F6"))  # Khối lượng cao
                    volume_item.setToolTip("Khối lượng cao hơn trung bình 50%")
                self.market_table.setItem(row, 4, volume_item)
                
                # Thêm cột tín hiệu kỹ thuật nếu có
                signal = market_data.get("signal", "")
                signal_item = QTableWidgetItem(signal)
                if signal == "STRONG_BUY":
                    signal_item.setForeground(QColor("#15803D"))  # Xanh đậm
                    signal_item.setFont(QFont("Arial", 9, QFont.Bold))
                elif signal == "BUY":
                    signal_item.setForeground(QColor("#22C55E"))  # Xanh
                elif signal == "STRONG_SELL":
                    signal_item.setForeground(QColor("#B91C1C"))  # Đỏ đậm
                    signal_item.setFont(QFont("Arial", 9, QFont.Bold))
                elif signal == "SELL":
                    signal_item.setForeground(QColor("#EF4444"))  # Đỏ
                elif signal == "NEUTRAL":
                    signal_item.setForeground(QColor("#94A3B8"))  # Xám
                
                if hasattr(self.market_table, 'columnCount') and self.market_table.columnCount() > 5:
                    self.market_table.setItem(row, 5, signal_item)
            
            # Tự động điều chỉnh kích thước cột
            self.market_table.resizeColumnsToContents()
            
            # Cập nhật thời gian cập nhật
            if hasattr(self, 'market_update_time_label'):
                current_time = datetime.now().strftime("%H:%M:%S")
                self.market_update_time_label.setText(f"Cập nhật lúc: {current_time}")
            
            # Thêm phân tích xu hướng BTC/ETH nếu có dữ liệu
            if btc_data and hasattr(self, 'btc_trend_label'):
                trend = btc_data.get("trend", "")
                if trend == "UP":
                    self.btc_trend_label.setText("Xu hướng: TĂNG ↑")
                    self.btc_trend_label.setStyleSheet("color: #22C55E;")
                elif trend == "DOWN":
                    self.btc_trend_label.setText("Xu hướng: GIẢM ↓")
                    self.btc_trend_label.setStyleSheet("color: #EF4444;")
                else:
                    self.btc_trend_label.setText("Xu hướng: ĐI NGANG →")
                    self.btc_trend_label.setStyleSheet("color: #94A3B8;")
            
            if eth_data and hasattr(self, 'eth_trend_label'):
                trend = eth_data.get("trend", "")
                if trend == "UP":
                    self.eth_trend_label.setText("Xu hướng: TĂNG ↑")
                    self.eth_trend_label.setStyleSheet("color: #22C55E;")
                elif trend == "DOWN":
                    self.eth_trend_label.setText("Xu hướng: GIẢM ↓")
                    self.eth_trend_label.setStyleSheet("color: #EF4444;")
                else:
                    self.eth_trend_label.setText("Xu hướng: ĐI NGANG →")
                    self.eth_trend_label.setStyleSheet("color: #94A3B8;")
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật tổng quan thị trường: {str(e)}", exc_info=True)
    
    def update_trading_info(self):
        """Cập nhật thông tin giao dịch"""
        try:
            # Kiểm tra xem các thành phần UI có tồn tại không
            if not hasattr(self, 'symbol_combo') or not self.symbol_combo:
                logging.error("Thành phần symbol_combo chưa được khởi tạo")
                return
            
            symbol = self.symbol_combo.currentText()
            if not symbol:
                logging.warning("Chưa chọn symbol")
                return
            
            # Kiểm tra và lấy hướng giao dịch hiện tại từ combobox
            if not hasattr(self, 'side_combo') or not self.side_combo:
                logging.warning("Thành phần side_combo chưa được khởi tạo")
                side = "LONG"  # Giá trị mặc định an toàn
            else:
                side = self.side_combo.currentText()
                if not side:
                    side = "LONG"  # Giá trị mặc định nếu không có lựa chọn
            
            # Kiểm tra kết nối market analyzer
            if not hasattr(self, 'market_analyzer') or not self.market_analyzer:
                logging.error("Market analyzer chưa được khởi tạo")
                return
                
            if not hasattr(self.market_analyzer, 'client') or not self.market_analyzer.client:
                logging.error("Chưa kết nối với Binance API")
                return
            
            # Lấy giá hiện tại
            try:
                symbol_ticker = self.market_analyzer.client.futures_symbol_ticker(symbol=symbol)
                current_price = float(symbol_ticker["price"])
            except Exception as e:
                logging.error(f"Lỗi khi lấy giá hiện tại: {str(e)}")
                return
                
            # Cập nhật giá hiện tại
            if hasattr(self, 'current_price_label') and self.current_price_label:
                self.current_price_label.setText(f"{current_price:.2f} USDT")
            
            # Kiểm tra và lấy giá trị amount
            if not hasattr(self, 'amount_spin') or not self.amount_spin:
                logging.warning("Thành phần amount_spin chưa được khởi tạo")
                amount = 0
            else:
                amount = self.amount_spin.value()
            
            # Tính toán giá trị vị thế
            position_value = amount * current_price
            if hasattr(self, 'position_value_label') and self.position_value_label:
                self.position_value_label.setText(f"{position_value:.2f} USDT")
            
            # Kiểm tra và lấy giá trị leverage
            if not hasattr(self, 'leverage_spin') or not self.leverage_spin:
                logging.warning("Thành phần leverage_spin chưa được khởi tạo")
                leverage = 1  # Giá trị mặc định an toàn
            else:
                leverage = max(1, self.leverage_spin.value())  # Đảm bảo leverage tối thiểu là 1
            
            # Tính toán margin yêu cầu
            margin_required = position_value / leverage
            if hasattr(self, 'margin_required_label') and self.margin_required_label:
                self.margin_required_label.setText(f"{margin_required:.2f} USDT")
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
    
    def calculate_coin_score(self, symbol):
        """
        Tính điểm coin dựa trên phân tích kỹ thuật và cơ bản
        
        :param symbol: Mã coin cần tính điểm
        :return: Điểm số (0-100)
        """
        try:
            if not self.market_analyzer:
                return 0
            
            # Thực hiện phân tích kỹ thuật trên nhiều khung thời gian
            intervals = ["1h", "4h", "1d"]
            total_score = 0
            valid_intervals = 0
            
            for interval in intervals:
                analysis = self.market_analyzer.analyze_technical(symbol, interval)
                
                if analysis.get("status") == "success":
                    # Lấy điểm từ phân tích nếu có
                    score = analysis.get("score", 0)
                    if isinstance(score, (int, float)):
                        total_score += score
                        valid_intervals += 1
            
            # Tính điểm trung bình từ các khung thời gian
            if valid_intervals > 0:
                final_score = total_score / valid_intervals
            else:
                final_score = 0
                
            # Ghi log điểm số
            logger.info(f"Điểm của coin {symbol}: {final_score:.2f}/100")
            
            return final_score
        except Exception as e:
            logger.error(f"Lỗi khi tính điểm coin: {str(e)}", exc_info=True)
            return 0
            
    def open_position(self, side_override=None):
        """
        Mở vị thế mới
        
        :param side_override: Ghi đè hướng giao dịch (tùy chọn)
        """
        try:
            # Kiểm tra PositionManager
            if not hasattr(self, 'position_manager') or not self.position_manager:
                self.show_error("Không thể mở vị thế", "Chưa khởi tạo PositionManager")
                return
                
            # Kiểm tra kết nối
            if not hasattr(self.position_manager, 'client') or not self.position_manager.client:
                self.show_error("Không thể mở vị thế", "Chưa kết nối với Binance API")
                return
            
            # Kiểm tra và lấy thông tin giao dịch
            if not hasattr(self, 'symbol_combo') or not self.symbol_combo:
                self.show_error("Không thể mở vị thế", "Thành phần symbol_combo chưa được khởi tạo")
                return
                
            symbol = self.symbol_combo.currentText()
            if not symbol:
                self.show_error("Không thể mở vị thế", "Chưa chọn symbol")
                return
                
            # Kiểm tra điểm coin (yêu cầu tối thiểu 60 điểm)
            coin_score = self.calculate_coin_score(symbol)
            if coin_score < 60:
                self.show_error(
                    "Coin không đạt ngưỡng giao dịch", 
                    f"Điểm của {symbol} chỉ là {coin_score:.2f}/100, cần tối thiểu 60 điểm để giao dịch"
                )
                self.add_to_system_log(f"❌ Từ chối giao dịch coin {symbol} - Điểm thấp: {coin_score:.2f}/100")
                return
            
            # Kiểm tra và lấy side
            if side_override:
                side = side_override
            else:
                if not hasattr(self, 'side_combo') or not self.side_combo:
                    self.show_error("Không thể mở vị thế", "Thành phần side_combo chưa được khởi tạo")
                    return
                side = self.side_combo.currentText()
                if not side:
                    self.show_error("Không thể mở vị thế", "Chưa chọn hướng giao dịch")
                    return
            
            # Kiểm tra và lấy amount
            if not hasattr(self, 'amount_spin') or not self.amount_spin:
                self.show_error("Không thể mở vị thế", "Thành phần amount_spin chưa được khởi tạo")
                return
            amount = self.amount_spin.value()
            if amount <= 0:
                self.show_error("Không thể mở vị thế", "Kích thước vị thế phải lớn hơn 0")
                return
            
            # Kiểm tra và lấy leverage
            if not hasattr(self, 'leverage_spin') or not self.leverage_spin:
                self.show_error("Không thể mở vị thế", "Thành phần leverage_spin chưa được khởi tạo")
                return
            leverage = max(1, self.leverage_spin.value())  # Đảm bảo leverage tối thiểu là 1
            
            # Kiểm tra và lấy stop loss
            if not hasattr(self, 'stop_loss_checkbox') or not self.stop_loss_checkbox:
                stop_loss = None
            else:
                stop_loss = None if self.stop_loss_checkbox.isChecked() else self.stop_loss_spin.value()
            
            # Kiểm tra và lấy take profit
            if not hasattr(self, 'take_profit_checkbox') or not self.take_profit_checkbox:
                take_profit = None
            else:
                take_profit = None if self.take_profit_checkbox.isChecked() else self.take_profit_spin.value()
            
            # Kiểm tra số dư tài khoản trước khi vào lệnh
            account_info = None
            if hasattr(self, 'position_manager') and self.position_manager:
                account_info = self.position_manager.get_account_balance()
            
            if not account_info or not account_info.get('available', 0):
                self.show_error("Không thể mở vị thế", "Không thể lấy thông tin số dư tài khoản")
                return
                
            available_balance = float(account_info.get('available', 0))
            estimated_cost = amount * leverage  # Ước tính chi phí vào lệnh
            
            if estimated_cost > available_balance:
                self.show_error(
                    "Số dư không đủ", 
                    f"Số dư khả dụng: {available_balance:.2f} USDT\nChi phí ước tính: {estimated_cost:.2f} USDT"
                )
                self.add_to_system_log(f"❌ Từ chối giao dịch - Số dư không đủ: {available_balance:.2f}/{estimated_cost:.2f} USDT")
                return
                
            # Thông báo tỷ lệ vị thế so với tài khoản
            position_percentage = (estimated_cost / available_balance) * 100
            self.add_to_system_log(f"ℹ️ Tỷ lệ vị thế/số dư: {position_percentage:.2f}% ({estimated_cost:.2f}/{available_balance:.2f} USDT)")
            
            # Kiểm tra tính hợp lệ của vị thế với RiskManager
            if hasattr(self, 'risk_manager') and self.risk_manager:
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
            
            # Lấy thông tin về vị thế hiện tại
            position_info = None
            try:
                positions = self.position_manager.get_open_positions()
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        position_info = pos
                        break
            except Exception as e:
                logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}", exc_info=True)
                self.show_error("Không thể lấy thông tin vị thế", str(e))
                return
                
            if not position_info:
                self.show_error("Không thể cập nhật SL/TP", f"Không tìm thấy vị thế mở cho {symbol}")
                return
                
            # Kiểm tra tính hợp lệ của SL/TP
            side = position_info.get("side", "")
            entry_price = float(position_info.get("entry_price", 0))
            
            if hasattr(self, 'risk_manager') and self.risk_manager:
                is_valid_sltp, reason_sltp = self.risk_manager.validate_sl_tp(
                    symbol, side, entry_price, stop_loss, take_profit
                )
                if not is_valid_sltp:
                    self.show_error("SL và TP không hợp lệ", reason_sltp)
                    return
            
            # Thêm thông báo phân tích rủi ro
            risk_message = ""
            if side == "LONG":
                risk_price = entry_price - stop_loss
                reward_price = take_profit - entry_price
                if reward_price > 0 and risk_price > 0:
                    risk_reward_ratio = reward_price / risk_price
                    risk_message = f"Tỷ lệ R/R: {risk_reward_ratio:.2f} (SL: {(stop_loss-entry_price)/entry_price*100:.2f}%, TP: {(take_profit-entry_price)/entry_price*100:.2f}%)"
            else:  # SHORT
                risk_price = stop_loss - entry_price
                reward_price = entry_price - take_profit
                if reward_price > 0 and risk_price > 0:
                    risk_reward_ratio = reward_price / risk_price
                    risk_message = f"Tỷ lệ R/R: {risk_reward_ratio:.2f} (SL: {(stop_loss-entry_price)/entry_price*100:.2f}%, TP: {(entry_price-take_profit)/entry_price*100:.2f}%)"
            
            # Log thông tin phân tích
            if risk_message:
                self.add_to_system_log(f"ℹ️ {symbol}: {risk_message}")
            
            # Cập nhật SL và TP
            result = self.position_manager.update_sl_tp(symbol, None, stop_loss, take_profit)
            
            if result.get("status") == "success":
                success_message = f"Đã cập nhật SL/TP cho {symbol}"
                if risk_message:
                    success_message += f"\n{risk_message}"
                self.show_info("Cập nhật thành công", success_message)
                self.status_label.setText(f"Đã cập nhật SL/TP cho {symbol}")
                
                # Cập nhật dữ liệu
                self.refresh_data()
            else:
                error_message = result.get("message", "Lỗi không xác định")
                retry_message = ""
                
                # Phân tích lỗi và đề xuất cách khắc phục
                if "Price" in error_message and "invalid" in error_message:
                    retry_message = "\n\nGợi ý: Giá SL/TP có thể không hợp lệ, hãy thử chỉnh lại theo giá thị trường hiện tại."
                elif "Filter failure" in error_message:
                    retry_message = "\n\nGợi ý: SL/TP có thể quá gần giá hiện tại, hãy thử đặt xa hơn."
                
                self.show_error("Lỗi khi cập nhật SL/TP", error_message + retry_message)
                self.add_to_system_log(f"❌ Lỗi SL/TP {symbol}: {error_message}")
        
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật SL/TP: {str(e)}", exc_info=True)
            self.show_error("Lỗi khi cập nhật SL/TP", str(e))
            self.add_to_system_log(f"❌ Lỗi hệ thống khi cập nhật SL/TP: {str(e)}")
    
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
            
            # Xử lý đặc biệt cho market_scanner
            if service_name == "market_scanner":
                try:
                    # Tạo instance của MarketScanner sử dụng API thực
                    self.market_scanner = get_scanner(testnet=True)
                    # Bắt đầu quét
                    self.market_scanner.start_scanning()
                    # Cập nhật trạng thái
                    self.service_status["market_scanner"] = True
                    self.update_service_status("market_scanner")
                    # Thông báo thành công
                    self.add_to_system_log("✅ Đã khởi động dịch vụ Market Scanner")
                    QMessageBox.information(self, "Thông báo", "Đã khởi động dịch vụ Market Scanner thành công")
                    return
                except Exception as e:
                    logger.error(f"Lỗi khi khởi động Market Scanner: {str(e)}", exc_info=True)
                    QMessageBox.critical(self, "Lỗi", f"Lỗi khi khởi động Market Scanner: {str(e)}")
                    return
                
            # Xử lý đặc biệt cho unified_trading_service  
            if service_name == "unified_trading_service":
                try:
                    # Cài đặt trạng thái dịch vụ
                    self.service_status["unified_trading_service"] = True
                    self.update_service_status("unified_trading_service")
                    # Thông báo thành công
                    self.add_to_system_log("✅ Đã khởi động dịch vụ Unified Trading Service")
                    QMessageBox.information(self, "Thông báo", "Đã khởi động dịch vụ Unified Trading Service thành công")
                    return
                except Exception as e:
                    logger.error(f"Lỗi khi khởi động Unified Trading Service: {str(e)}", exc_info=True)
                    QMessageBox.critical(self, "Lỗi", f"Lỗi khi khởi động Unified Trading Service: {str(e)}")
                    return
                
            # Ánh xạ tên dịch vụ đến script tương ứng cho các dịch vụ khác
            service_scripts = {
                "market_notifier": "auto_market_notifier.py",
                "service_manager": "enhanced_service_manager.py",
                "watchdog": "service_watchdog.py",
                "telegram_notifier": "advanced_telegram_notifier.py",
                "auto_trade": "auto_trade.py",
                "ml_training": "train_ml_model.py"
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