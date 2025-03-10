#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot GUI - Giao diện đồ họa cho hệ thống giao dịch 24/7

Phiên bản này được tối ưu hóa để chạy liên tục 24/7 với việc giám sát và quản lý rủi ro tự động.
Ứng dụng có thể biên dịch thành file exe để chạy trên hệ điều hành Windows.
"""

import os
import sys
import json
import time
import logging
import threading
import subprocess
import datetime
import webbrowser
from pathlib import Path
import urllib.request
from functools import partial

# Đảm bảo thư mục logs tồn tại
os.makedirs("logs", exist_ok=True)

# Định cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot_gui.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot_gui')

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QPushButton, QLabel, QComboBox, QTabWidget, QGridLayout, 
        QGroupBox, QCheckBox, QLineEdit, QTextEdit, QScrollArea, 
        QSplitter, QFrame, QProgressBar, QMessageBox, QFileDialog,
        QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
        QSpacerItem, QSlider, QDoubleSpinBox, QSpinBox, QRadioButton
    )
    from PyQt5.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QUrl, QSize, QRect, 
        QDateTime, QSortFilterProxyModel, QDir
    )
    from PyQt5.QtGui import (
        QIcon, QPixmap, QFont, QPalette, QColor, QTextCursor,
        QStandardItemModel, QStandardItem, QBrush
    )
    
    # PyQtGraph cho biểu đồ
    try:
        import pyqtgraph as pg
    except ImportError:
        logger.warning("PyQtGraph không được cài đặt. Chức năng biểu đồ sẽ bị hạn chế.")
        pg = None
    
    # Thử nhập các module phụ thuộc khác
    try:
        import numpy as np
    except ImportError:
        logger.warning("NumPy không được cài đặt. Một số chức năng sẽ bị hạn chế.")
        np = None
    
    try:
        import pandas as pd
    except ImportError:
        logger.warning("Pandas không được cài đặt. Một số chức năng sẽ bị hạn chế.")
        pd = None
        
    # Matplotlib cho biểu đồ nếu không có PyQtGraph
    if pg is None:
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
        except ImportError:
            logger.warning("Matplotlib không được cài đặt. Chức năng biểu đồ sẽ bị hạn chế.")
            plt = None
except ImportError as e:
    logger.error(f"Lỗi khi nhập các module PyQt5: {str(e)}")
    print(f"Lỗi: {str(e)}")
    print("Vui lòng cài đặt PyQt5 để chạy giao diện đồ họa.")
    print("Cài đặt: pip install PyQt5")
    sys.exit(1)


class BotThread(QThread):
    """Thread để chạy bot trong nền"""
    # Tín hiệu để cập nhật trạng thái và log
    update_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, parent=None, account_config=None, risk_level=None):
        super(BotThread, self).__init__(parent)
        self.is_running = False
        self.account_config = account_config
        self.risk_level = risk_level
        self.process = None
    
    def run(self):
        """Chạy bot trong thread riêng biệt"""
        self.is_running = True
        self.update_signal.emit("Khởi động bot giao dịch...")
        
        try:
            # Khởi tạo các thư mục cần thiết nếu chưa tồn tại
            os.makedirs("logs", exist_ok=True)
            
            # Mở subprocess để chạy bot
            cmd = [sys.executable, "bot_startup.py"]
            if self.risk_level:
                cmd.extend(["--risk-level", self.risk_level])
            
            # Mở subprocess với pipe để đọc output
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Đọc output từ bot
            while self.is_running and self.process.poll() is None:
                output = self.process.stdout.readline()
                if output:
                    try:
                        self.update_signal.emit(output.strip().decode('utf-8'))
                    except UnicodeDecodeError:
                        self.update_signal.emit(output.strip().decode('latin-1'))
            
            # Đọc lỗi nếu có
            for error in self.process.stderr.readlines():
                if error:
                    try:
                        self.error_signal.emit(error.strip().decode('utf-8'))
                    except UnicodeDecodeError:
                        self.error_signal.emit(error.strip().decode('latin-1'))
            
            # Kiểm tra trạng thái kết thúc
            if self.process.poll() is not None and self.process.returncode != 0:
                self.error_signal.emit(f"Bot kết thúc với mã lỗi: {self.process.returncode}")
            else:
                self.update_signal.emit("Bot đã dừng thành công.")
        
        except Exception as e:
            self.error_signal.emit(f"Lỗi khi chạy bot: {str(e)}")
            logger.error(f"Lỗi trong BotThread: {str(e)}")
        
        finally:
            self.is_running = False
    
    def stop(self):
        """Dừng bot và thread"""
        self.is_running = False
        if self.process and self.process.poll() is None:
            # Gửi SIGTERM để kết thúc tiến trình gracefully
            self.process.terminate()
            # Đợi tối đa 5 giây
            for _ in range(5):
                if self.process.poll() is not None:
                    break
                time.sleep(1)
            # Nếu vẫn chưa kết thúc, buộc kết thúc
            if self.process.poll() is None:
                self.process.kill()
            
        self.update_signal.emit("Đã gửi tín hiệu dừng cho bot.")
        self.wait(3000)  # Đợi tối đa 3 giây


class UpdateThread(QThread):
    """Thread để kiểm tra và cập nhật phiên bản mới"""
    update_progress = pyqtSignal(int, str)
    update_completed = pyqtSignal(bool, str)
    
    def __init__(self, parent=None):
        super(UpdateThread, self).__init__(parent)
        self.update_url = "https://api.example.com/trading-bot/updates"  # Thay bằng URL thực tế
    
    def run(self):
        """Kiểm tra và tải cập nhật mới"""
        try:
            self.update_progress.emit(10, "Đang kiểm tra bản cập nhật...")
            
            # Thêm xử lý cập nhật thực tế ở đây
            from update_packages.update_bot import BotUpdater
            updater = BotUpdater()
            
            self.update_progress.emit(30, "Đang kiểm tra phiên bản hiện tại...")
            current_version = updater.get_current_version()
            
            self.update_progress.emit(50, "Đang kiểm tra phiên bản mới nhất...")
            latest_version = updater.get_latest_version()
            
            self.update_progress.emit(70, "Đang so sánh phiên bản...")
            
            if updater.needs_update():
                self.update_progress.emit(80, "Đang tải bản cập nhật mới...")
                success = updater.update()
                
                if success:
                    self.update_progress.emit(100, "Cập nhật thành công!")
                    self.update_completed.emit(True, f"Đã cập nhật lên phiên bản {latest_version}")
                else:
                    self.update_completed.emit(False, "Cập nhật thất bại. Vui lòng thử lại sau.")
            else:
                self.update_progress.emit(100, "Đã là phiên bản mới nhất!")
                self.update_completed.emit(True, f"Bạn đang sử dụng phiên bản mới nhất: {current_version}")
                
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật: {str(e)}")
            self.update_completed.emit(False, f"Lỗi: {str(e)}")


class LogMonitorThread(QThread):
    """Thread để theo dõi và cập nhật log"""
    new_log = pyqtSignal(str)
    
    def __init__(self, parent=None, log_file=None):
        super(LogMonitorThread, self).__init__(parent)
        self.log_file = log_file or "logs/trading_bot.log"
        self.is_running = False
    
    def run(self):
        """Theo dõi file log và phát tín hiệu khi có bản ghi mới"""
        self.is_running = True
        
        # Tạo file log nếu chưa tồn tại
        if not os.path.exists(self.log_file):
            try:
                os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
                with open(self.log_file, 'w', encoding="utf-8") as f:
                    f.write(f"# Log file created at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            except Exception as e:
                logger.error(f"Không thể tạo file log: {str(e)}")
                self.new_log.emit(f"Lỗi: Không thể tạo file log ({str(e)})")
                return
        
        # Theo dõi file log
        try:
            with open(self.log_file, 'r', encoding="utf-8") as f:
                # Di chuyển đến cuối file
                f.seek(0, 2)
                
                while self.is_running:
                    line = f.readline()
                    if line:
                        self.new_log.emit(line.strip())
                    else:
                        # Không có dữ liệu mới, đợi một chút
                        time.sleep(0.1)
                        
        except Exception as e:
            logger.error(f"Lỗi khi đọc file log: {str(e)}")
            self.new_log.emit(f"Lỗi: Không thể đọc file log ({str(e)})")
    
    def stop(self):
        """Dừng theo dõi log"""
        self.is_running = False
        self.wait(1000)  # Đợi tối đa 1 giây


class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng"""
    
    def __init__(self):
        super(MainWindow, self).__init__()
        
        self.init_ui()
        self.load_config()
        self.init_risk_levels()
        
        # Khởi tạo các thread
        self.bot_thread = None
        self.update_thread = None
        self.log_monitor = LogMonitorThread(self)
        self.log_monitor.new_log.connect(self.append_log)
        self.log_monitor.start()
        
        # Thiết lập timer để cập nhật giao diện
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)  # Cập nhật mỗi giây
        
        logger.info("Giao diện bot đã khởi động")
    
    def init_ui(self):
        """Khởi tạo giao diện người dùng"""
        self.setWindowTitle("Trading Bot Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Widget chính và layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tạo widget tab
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab Tổng quan
        self.create_dashboard_tab()
        
        # Tab Cài đặt
        self.create_settings_tab()
        
        # Tab Quản lý rủi ro
        self.create_risk_management_tab()
        
        # Tab Chiến lược
        self.create_strategy_tab()
        
        # Tab Log
        self.create_log_tab()
        
        # Tab Tài liệu
        self.create_help_tab()
        
        # Thanh trạng thái
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Sẵn sàng")
        
        # Các biến trạng thái
        self.bot_running = False
        self.current_risk_level = "20"  # Mặc định là 20%
    
    def create_dashboard_tab(self):
        """Tạo tab tổng quan"""
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)
        
        # Tiêu đề
        title_label = QLabel("Bảng Điều Khiển Bot Giao Dịch")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Tạo layout grid cho các thông số
        grid_layout = QGridLayout()
        
        # Thêm các widget vào grid
        # Dòng 1
        self.status_group = QGroupBox("Trạng Thái")
        status_layout = QVBoxLayout(self.status_group)
        self.status_label = QLabel("Đã dừng")
        status_layout.addWidget(self.status_label)
        grid_layout.addWidget(self.status_group, 0, 0)
        
        self.version_group = QGroupBox("Phiên Bản")
        version_layout = QVBoxLayout(self.version_group)
        self.version_label = QLabel("1.0.0")
        version_layout.addWidget(self.version_label)
        grid_layout.addWidget(self.version_group, 0, 1)
        
        self.risk_group = QGroupBox("Mức Rủi Ro")
        risk_layout = QVBoxLayout(self.risk_group)
        self.risk_label = QLabel("20%")
        risk_layout.addWidget(self.risk_label)
        grid_layout.addWidget(self.risk_group, 0, 2)
        
        # Dòng 2
        self.balance_group = QGroupBox("Số Dư")
        balance_layout = QVBoxLayout(self.balance_group)
        self.balance_label = QLabel("$0.00")
        self.balance_label.setAlignment(Qt.AlignCenter)
        balance_font = QFont("Arial", 12, QFont.Bold)
        self.balance_label.setFont(balance_font)
        balance_layout.addWidget(self.balance_label)
        grid_layout.addWidget(self.balance_group, 1, 0)
        
        self.pnl_group = QGroupBox("P/L Hôm Nay")
        pnl_layout = QVBoxLayout(self.pnl_group)
        self.pnl_label = QLabel("+$0.00 (0.0%)")
        self.pnl_label.setAlignment(Qt.AlignCenter)
        pnl_font = QFont("Arial", 12, QFont.Bold)
        self.pnl_label.setFont(pnl_font)
        pnl_layout.addWidget(self.pnl_label)
        grid_layout.addWidget(self.pnl_group, 1, 1)
        
        self.positions_group = QGroupBox("Vị Thế Hiện Tại")
        positions_layout = QVBoxLayout(self.positions_group)
        self.positions_label = QLabel("0/5")
        self.positions_label.setAlignment(Qt.AlignCenter)
        positions_font = QFont("Arial", 12, QFont.Bold)
        self.positions_label.setFont(positions_font)
        positions_layout.addWidget(self.positions_label)
        grid_layout.addWidget(self.positions_group, 1, 2)
        
        # Thêm grid vào layout chính
        layout.addLayout(grid_layout)
        
        # Bảng vị thế giao dịch
        positions_table_group = QGroupBox("Vị Thế Giao Dịch")
        positions_table_layout = QVBoxLayout(positions_table_group)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(6)
        self.positions_table.setHorizontalHeaderLabels(["Symbol", "Loại", "Giá Vào", "Giá Hiện Tại", "Số Lượng", "P/L"])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        positions_table_layout.addWidget(self.positions_table)
        
        layout.addWidget(positions_table_group)
        
        # Biểu đồ tổng quan
        chart_group = QGroupBox("Biểu Đồ")
        chart_layout = QVBoxLayout(chart_group)
        
        if pg is not None:
            # Sử dụng PyQtGraph
            self.chart_widget = pg.PlotWidget()
            self.chart_widget.setBackground('w')
            self.chart_widget.setTitle("Hiệu Suất Giao Dịch")
            self.chart_widget.setLabel('left', 'Lợi Nhuận (%)')
            self.chart_widget.setLabel('bottom', 'Thời Gian')
            self.chart_widget.showGrid(x=True, y=True)
            
            # Dữ liệu mẫu
            x = list(range(100))
            y = [0 for _ in range(100)]  # Dữ liệu trống
            self.performance_curve = self.chart_widget.plot(x, y, pen=pg.mkPen(color='b', width=2))
            
            chart_layout.addWidget(self.chart_widget)
        else:
            # Sử dụng Matplotlib nếu không có PyQtGraph
            if plt is not None:
                self.figure = Figure(figsize=(5, 4), dpi=100)
                self.canvas = FigureCanvas(self.figure)
                self.axes = self.figure.add_subplot(111)
                self.axes.set_title("Hiệu Suất Giao Dịch")
                self.axes.set_xlabel("Thời Gian")
                self.axes.set_ylabel("Lợi Nhuận (%)")
                self.axes.grid(True)
                
                # Dữ liệu mẫu
                x = list(range(100))
                y = [0 for _ in range(100)]  # Dữ liệu trống
                self.performance_line, = self.axes.plot(x, y, 'b-')
                
                chart_layout.addWidget(self.canvas)
            else:
                chart_label = QLabel("Biểu đồ không khả dụng. Vui lòng cài đặt PyQtGraph hoặc Matplotlib.")
                chart_layout.addWidget(chart_label)
        
        layout.addWidget(chart_group)
        
        # Khu vực nút điều khiển
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Bắt Đầu Bot")
        self.start_button.clicked.connect(self.start_bot)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Dừng Bot")
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        self.update_button = QPushButton("Kiểm Tra Cập Nhật")
        self.update_button.clicked.connect(self.check_update)
        control_layout.addWidget(self.update_button)
        
        self.settings_button = QPushButton("Cài Đặt")
        self.settings_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        control_layout.addWidget(self.settings_button)
        
        layout.addLayout(control_layout)
        
        # Thêm tab vào tabs
        self.tabs.addTab(dashboard_tab, "Tổng Quan")
    
    def create_settings_tab(self):
        """Tạo tab cài đặt"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # Tiêu đề
        title_label = QLabel("Cài Đặt Hệ Thống")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Form cài đặt
        form_group = QGroupBox("Cài Đặt API")
        form_layout = QGridLayout(form_group)
        
        # API Key
        form_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.api_key_input, 0, 1)
        
        # API Secret
        form_layout.addWidget(QLabel("API Secret:"), 1, 0)
        self.api_secret_input = QLineEdit()
        self.api_secret_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.api_secret_input, 1, 1)
        
        # API Mode (Testnet/Live)
        form_layout.addWidget(QLabel("API Mode:"), 2, 0)
        self.api_mode_combo = QComboBox()
        self.api_mode_combo.addItems(["Testnet", "Live"])
        form_layout.addWidget(self.api_mode_combo, 2, 1)
        
        # Khớp lệnh tự động
        form_layout.addWidget(QLabel("Khớp lệnh tự động:"), 3, 0)
        self.auto_trading_checkbox = QCheckBox("Bật")
        form_layout.addWidget(self.auto_trading_checkbox, 3, 1)
        
        # Telegram Notifications
        form_layout.addWidget(QLabel("Thông báo Telegram:"), 4, 0)
        self.telegram_checkbox = QCheckBox("Bật")
        form_layout.addWidget(self.telegram_checkbox, 4, 1)
        
        # Telegram Bot Token
        form_layout.addWidget(QLabel("Telegram Bot Token:"), 5, 0)
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.telegram_token_input, 5, 1)
        
        # Telegram Chat ID
        form_layout.addWidget(QLabel("Telegram Chat ID:"), 6, 0)
        self.telegram_chat_id_input = QLineEdit()
        form_layout.addWidget(self.telegram_chat_id_input, 6, 1)
        
        layout.addWidget(form_group)
        
        # Cài đặt hệ thống
        system_group = QGroupBox("Cài Đặt Hệ Thống")
        system_layout = QGridLayout(system_group)
        
        # Tần suất cập nhật dữ liệu
        system_layout.addWidget(QLabel("Tần suất cập nhật dữ liệu (giây):"), 0, 0)
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(5, 60)
        self.update_interval_spin.setValue(10)
        system_layout.addWidget(self.update_interval_spin, 0, 1)
        
        # Ghi log chi tiết
        system_layout.addWidget(QLabel("Ghi log chi tiết:"), 1, 0)
        self.detailed_log_checkbox = QCheckBox("Bật")
        system_layout.addWidget(self.detailed_log_checkbox, 1, 1)
        
        # Tự động khởi động lại khi lỗi
        system_layout.addWidget(QLabel("Tự động khởi động lại khi lỗi:"), 2, 0)
        self.auto_restart_checkbox = QCheckBox("Bật")
        system_layout.addWidget(self.auto_restart_checkbox, 2, 1)
        
        # Lưu trữ dữ liệu
        system_layout.addWidget(QLabel("Thư mục dữ liệu:"), 3, 0)
        data_dir_layout = QHBoxLayout()
        self.data_dir_input = QLineEdit("./data")
        data_dir_layout.addWidget(self.data_dir_input)
        
        self.browse_button = QPushButton("...")
        self.browse_button.clicked.connect(self.browse_data_dir)
        data_dir_layout.addWidget(self.browse_button)
        
        system_layout.addLayout(data_dir_layout, 3, 1)
        
        layout.addWidget(system_group)
        
        # Nút lưu cài đặt
        button_layout = QHBoxLayout()
        self.save_settings_button = QPushButton("Lưu Cài Đặt")
        self.save_settings_button.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_settings_button)
        
        self.reset_settings_button = QPushButton("Khôi Phục Mặc Định")
        self.reset_settings_button.clicked.connect(self.reset_config)
        button_layout.addWidget(self.reset_settings_button)
        
        layout.addLayout(button_layout)
        
        # Thêm khoảng trống co giãn
        layout.addStretch()
        
        # Thêm tab vào tabs
        self.tabs.addTab(settings_tab, "Cài Đặt")
    
    def create_risk_management_tab(self):
        """Tạo tab quản lý rủi ro"""
        risk_tab = QWidget()
        layout = QVBoxLayout(risk_tab)
        
        # Tiêu đề
        title_label = QLabel("Quản Lý Rủi Ro")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Nhóm mức rủi ro
        risk_level_group = QGroupBox("Mức Rủi Ro")
        risk_level_layout = QVBoxLayout(risk_level_group)
        
        # ComboBox mức rủi ro
        self.risk_level_combo = QComboBox()
        self.risk_level_combo.addItems(["10% - Rủi ro thấp", "15% - Rủi ro vừa phải", 
                                       "20% - Rủi ro trung bình cao", "30% - Rủi ro cao"])
        self.risk_level_combo.setCurrentIndex(2)  # Mặc định là 20%
        self.risk_level_combo.currentIndexChanged.connect(self.risk_level_changed)
        risk_level_layout.addWidget(self.risk_level_combo)
        
        # Mô tả mức rủi ro
        self.risk_description_label = QLabel("Rủi ro trung bình cao - Phù hợp cho trader có kinh nghiệm")
        risk_level_layout.addWidget(self.risk_description_label)
        
        layout.addWidget(risk_level_group)
        
        # Tham số rủi ro
        risk_params_group = QGroupBox("Tham Số Rủi Ro")
        risk_params_layout = QGridLayout(risk_params_group)
        
        # Kích thước vị thế tối đa
        risk_params_layout.addWidget(QLabel("Kích thước vị thế tối đa (%):"), 0, 0)
        self.max_position_size_spin = QDoubleSpinBox()
        self.max_position_size_spin.setRange(0.1, 10.0)
        self.max_position_size_spin.setSingleStep(0.1)
        self.max_position_size_spin.setValue(2.0)
        risk_params_layout.addWidget(self.max_position_size_spin, 0, 1)
        
        # Số vị thế tối đa
        risk_params_layout.addWidget(QLabel("Số vị thế tối đa:"), 1, 0)
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 20)
        self.max_positions_spin.setValue(5)
        risk_params_layout.addWidget(self.max_positions_spin, 1, 1)
        
        # Stop Loss
        risk_params_layout.addWidget(QLabel("Stop Loss (%):"), 2, 0)
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(0.1, 10.0)
        self.stop_loss_spin.setSingleStep(0.1)
        self.stop_loss_spin.setValue(1.0)
        risk_params_layout.addWidget(self.stop_loss_spin, 2, 1)
        
        # Take Profit
        risk_params_layout.addWidget(QLabel("Take Profit (%):"), 3, 0)
        self.take_profit_spin = QDoubleSpinBox()
        self.take_profit_spin.setRange(0.1, 20.0)
        self.take_profit_spin.setSingleStep(0.1)
        self.take_profit_spin.setValue(3.0)
        risk_params_layout.addWidget(self.take_profit_spin, 3, 1)
        
        # Đòn bẩy
        risk_params_layout.addWidget(QLabel("Đòn bẩy:"), 4, 0)
        self.leverage_combo = QComboBox()
        self.leverage_combo.addItems(["1x", "3x", "5x", "7x", "10x", "20x"])
        self.leverage_combo.setCurrentIndex(2)  # Mặc định là 5x
        risk_params_layout.addWidget(self.leverage_combo, 4, 1)
        
        # Thua lỗ tối đa mỗi ngày
        risk_params_layout.addWidget(QLabel("Thua lỗ tối đa mỗi ngày (%):"), 5, 0)
        self.max_daily_loss_spin = QDoubleSpinBox()
        self.max_daily_loss_spin.setRange(1.0, 20.0)
        self.max_daily_loss_spin.setSingleStep(0.5)
        self.max_daily_loss_spin.setValue(5.0)
        risk_params_layout.addWidget(self.max_daily_loss_spin, 5, 1)
        
        layout.addWidget(risk_params_group)
        
        # Cài đặt bảo vệ
        protection_group = QGroupBox("Cài Đặt Bảo Vệ")
        protection_layout = QVBoxLayout(protection_group)
        
        # Trailing Stop
        trailing_stop_layout = QHBoxLayout()
        self.trailing_stop_checkbox = QCheckBox("Sử dụng Trailing Stop")
        trailing_stop_layout.addWidget(self.trailing_stop_checkbox)
        
        trailing_stop_layout.addWidget(QLabel("Callback (%):"))
        self.trailing_stop_callback_spin = QDoubleSpinBox()
        self.trailing_stop_callback_spin.setRange(0.1, 5.0)
        self.trailing_stop_callback_spin.setSingleStep(0.05)
        self.trailing_stop_callback_spin.setValue(0.2)
        trailing_stop_layout.addWidget(self.trailing_stop_callback_spin)
        
        protection_layout.addLayout(trailing_stop_layout)
        
        # Lọc thông minh
        self.smart_entry_checkbox = QCheckBox("Sử dụng chức năng nhập lệnh thông minh")
        protection_layout.addWidget(self.smart_entry_checkbox)
        
        # Lọc chế độ thị trường
        self.market_regime_filter_checkbox = QCheckBox("Sử dụng lọc theo chế độ thị trường")
        protection_layout.addWidget(self.market_regime_filter_checkbox)
        
        # Lọc biến động
        self.volatility_filter_checkbox = QCheckBox("Sử dụng lọc theo biến động")
        protection_layout.addWidget(self.volatility_filter_checkbox)
        
        layout.addWidget(protection_group)
        
        # Nút điều khiển
        button_layout = QHBoxLayout()
        
        self.apply_risk_button = QPushButton("Áp Dụng Cấu Hình")
        self.apply_risk_button.clicked.connect(self.apply_risk_config)
        button_layout.addWidget(self.apply_risk_button)
        
        self.save_risk_button = QPushButton("Lưu Cấu Hình")
        self.save_risk_button.clicked.connect(self.save_risk_config)
        button_layout.addWidget(self.save_risk_button)
        
        layout.addLayout(button_layout)
        
        # Thêm tab vào tabs
        self.tabs.addTab(risk_tab, "Quản Lý Rủi Ro")
    
    def create_strategy_tab(self):
        """Tạo tab chiến lược"""
        strategy_tab = QWidget()
        layout = QVBoxLayout(strategy_tab)
        
        # Tiêu đề
        title_label = QLabel("Chiến Lược Giao Dịch")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Chọn chiến lược
        strategy_group = QGroupBox("Chiến Lược")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Adaptive Strategy", "ML Integrated Strategy", 
                                    "Trend Following", "Ranging Market", "Fibonacci Retracement"])
        self.strategy_combo.setCurrentIndex(0)  # Mặc định là Adaptive Strategy
        strategy_layout.addWidget(self.strategy_combo)
        
        # Mô tả chiến lược
        self.strategy_description = QTextEdit()
        self.strategy_description.setReadOnly(True)
        self.strategy_description.setFixedHeight(100)
        self.strategy_description.setPlainText(
            "Adaptive Strategy: Chiến lược tự điều chỉnh dựa trên chế độ thị trường hiện tại. "
            "Kết hợp nhiều chỉ báo và tính năng máy học để tối ưu hóa điểm vào và ra lệnh."
        )
        strategy_layout.addWidget(self.strategy_description)
        
        # Nút kích hoạt chiến lược
        self.activate_strategy_button = QPushButton("Kích Hoạt Chiến Lược")
        self.activate_strategy_button.clicked.connect(self.activate_strategy)
        strategy_layout.addWidget(self.activate_strategy_button)
        
        layout.addWidget(strategy_group)
        
        # Tham số chiến lược
        params_group = QGroupBox("Tham Số Chiến Lược")
        params_layout = QGridLayout(params_group)
        
        # Activation Threshold
        params_layout.addWidget(QLabel("Activation Threshold:"), 0, 0)
        self.activation_threshold_spin = QSpinBox()
        self.activation_threshold_spin.setRange(50, 100)
        self.activation_threshold_spin.setValue(80)
        params_layout.addWidget(self.activation_threshold_spin, 0, 1)
        
        # Callback Rate
        params_layout.addWidget(QLabel("Callback Rate:"), 1, 0)
        self.callback_rate_spin = QSpinBox()
        self.callback_rate_spin.setRange(5, 50)
        self.callback_rate_spin.setValue(20)
        params_layout.addWidget(self.callback_rate_spin, 1, 1)
        
        # Trend Confirmation Periods
        params_layout.addWidget(QLabel("Trend Confirmation Periods:"), 2, 0)
        self.trend_confirmation_spin = QSpinBox()
        self.trend_confirmation_spin.setRange(1, 10)
        self.trend_confirmation_spin.setValue(3)
        params_layout.addWidget(self.trend_confirmation_spin, 2, 1)
        
        # Timeframes
        params_layout.addWidget(QLabel("Timeframes:"), 3, 0)
        self.timeframes_combo = QComboBox()
        self.timeframes_combo.addItems(["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
        self.timeframes_combo.setCurrentIndex(3)  # Mặc định là 30m
        params_layout.addWidget(self.timeframes_combo, 3, 1)
        
        # Nút lưu tham số
        self.save_params_button = QPushButton("Lưu Tham Số")
        self.save_params_button.clicked.connect(self.save_strategy_params)
        params_layout.addWidget(self.save_params_button, 4, 0, 1, 2)
        
        layout.addWidget(params_group)
        
        # Bảng hiệu suất chiến lược
        performance_group = QGroupBox("Hiệu Suất Chiến Lược")
        performance_layout = QVBoxLayout(performance_group)
        
        self.strategy_performance_table = QTableWidget()
        self.strategy_performance_table.setColumnCount(6)
        self.strategy_performance_table.setHorizontalHeaderLabels(["Chiến Lược", "Win Rate", "Profit Factor", "Số Lệnh", "Lợi Nhuận", "Drawdown"])
        self.strategy_performance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Thêm dữ liệu mẫu
        self.strategy_performance_table.setRowCount(1)
        self.strategy_performance_table.setItem(0, 0, QTableWidgetItem("Adaptive Strategy"))
        self.strategy_performance_table.setItem(0, 1, QTableWidgetItem("65.2%"))
        self.strategy_performance_table.setItem(0, 2, QTableWidgetItem("1.78"))
        self.strategy_performance_table.setItem(0, 3, QTableWidgetItem("142"))
        self.strategy_performance_table.setItem(0, 4, QTableWidgetItem("+21.4%"))
        self.strategy_performance_table.setItem(0, 5, QTableWidgetItem("12.8%"))
        
        performance_layout.addWidget(self.strategy_performance_table)
        
        layout.addWidget(performance_group)
        
        # Thêm khoảng trống co giãn
        layout.addStretch()
        
        # Thêm tab vào tabs
        self.tabs.addTab(strategy_tab, "Chiến Lược")
    
    def create_log_tab(self):
        """Tạo tab log"""
        log_tab = QWidget()
        layout = QVBoxLayout(log_tab)
        
        # Tiêu đề
        title_label = QLabel("Logs")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Bộ lọc log
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Lọc:"))
        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItems(["Tất cả", "Giao dịch", "Lỗi", "Hệ thống", "Thông báo"])
        filter_layout.addWidget(self.log_filter_combo)
        
        filter_layout.addWidget(QLabel("Cấp độ:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentIndex(1)  # Mặc định là INFO
        filter_layout.addWidget(self.log_level_combo)
        
        self.refresh_log_button = QPushButton("Làm Mới")
        self.refresh_log_button.clicked.connect(self.refresh_logs)
        filter_layout.addWidget(self.refresh_log_button)
        
        self.clear_log_button = QPushButton("Xóa")
        self.clear_log_button.clicked.connect(self.clear_logs)
        filter_layout.addWidget(self.clear_log_button)
        
        layout.addLayout(filter_layout)
        
        # Khu vực hiển thị log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setStyleSheet("font-family: Courier; font-size: 10pt;")
        layout.addWidget(self.log_text)
        
        # Thêm tab vào tabs
        self.tabs.addTab(log_tab, "Logs")
    
    def create_help_tab(self):
        """Tạo tab trợ giúp"""
        help_tab = QWidget()
        layout = QVBoxLayout(help_tab)
        
        # Tiêu đề
        title_label = QLabel("Tài Liệu Hướng Dẫn")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Khu vực tabs cho các loại hướng dẫn
        help_tabs = QTabWidget()
        
        # Tab Hướng dẫn sử dụng
        usage_tab = QWidget()
        usage_layout = QVBoxLayout(usage_tab)
        
        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_text.setHtml("""
        <h2>Hướng Dẫn Sử Dụng</h2>
        <p>Chào mừng đến với hệ thống bot giao dịch tiền điện tử tự động! Dưới đây là hướng dẫn cơ bản để bắt đầu:</p>
        
        <h3>1. Cài Đặt API</h3>
        <p>Trước tiên, bạn cần thiết lập kết nối API Binance:</p>
        <ul>
            <li>Truy cập tab <b>Cài Đặt</b></li>
            <li>Nhập <b>API Key</b> và <b>API Secret</b> từ tài khoản Binance của bạn</li>
            <li>Chọn môi trường <b>Testnet</b> để thử nghiệm hoặc <b>Live</b> để giao dịch thực</li>
            <li>Nhấn <b>Lưu Cài Đặt</b> để áp dụng</li>
        </ul>
        
        <h3>2. Quản Lý Rủi Ro</h3>
        <p>Thiết lập mức độ rủi ro phù hợp với chiến lược của bạn:</p>
        <ul>
            <li>Truy cập tab <b>Quản Lý Rủi Ro</b></li>
            <li>Chọn mức rủi ro từ 10% (thấp) đến 30% (cao)</li>
            <li>Điều chỉnh các tham số như kích thước vị thế, stop loss, và take profit</li>
            <li>Nhấn <b>Áp Dụng Cấu Hình</b> để cập nhật</li>
        </ul>
        
        <h3>3. Chọn Chiến Lược</h3>
        <p>Cấu hình chiến lược giao dịch:</p>
        <ul>
            <li>Truy cập tab <b>Chiến Lược</b></li>
            <li>Chọn loại chiến lược từ danh sách</li>
            <li>Điều chỉnh các tham số chiến lược</li>
            <li>Nhấn <b>Kích Hoạt Chiến Lược</b> để áp dụng</li>
        </ul>
        
        <h3>4. Bắt Đầu Giao Dịch</h3>
        <p>Khởi động bot và theo dõi hoạt động:</p>
        <ul>
            <li>Truy cập tab <b>Tổng Quan</b></li>
            <li>Nhấn <b>Bắt Đầu Bot</b> để khởi động hệ thống</li>
            <li>Theo dõi vị thế và hiệu suất trên bảng điều khiển</li>
            <li>Kiểm tra logs để xem chi tiết hoạt động</li>
        </ul>
        
        <h3>5. Duy Trì Hệ Thống</h3>
        <p>Đảm bảo hệ thống luôn được cập nhật:</p>
        <ul>
            <li>Nhấn <b>Kiểm Tra Cập Nhật</b> định kỳ</li>
            <li>Sao lưu cấu hình qua chức năng <b>Lưu Cấu Hình</b></li>
            <li>Theo dõi logs để phát hiện vấn đề</li>
        </ul>
        """)
        usage_layout.addWidget(usage_text)
        help_tabs.addTab(usage_tab, "Hướng Dẫn Sử Dụng")
        
        # Tab Cấu hình rủi ro
        risk_help_tab = QWidget()
        risk_help_layout = QVBoxLayout(risk_help_tab)
        
        risk_help_text = QTextEdit()
        risk_help_text.setReadOnly(True)
        risk_help_text.setHtml("""
        <h2>Hướng Dẫn Cấu Hình Rủi Ro</h2>
        <p>Hiểu và thiết lập đúng mức độ rủi ro là yếu tố quyết định thành công khi giao dịch:</p>
        
        <h3>Các mức rủi ro</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th>Mức rủi ro</th>
                <th>Mô tả</th>
                <th>Phù hợp cho</th>
            </tr>
            <tr>
                <td><b>10%</b></td>
                <td>Rủi ro thấp, an toàn nhất</td>
                <td>Người mới bắt đầu, người ưa an toàn</td>
            </tr>
            <tr>
                <td><b>15%</b></td>
                <td>Rủi ro vừa phải, cân bằng</td>
                <td>Người có kinh nghiệm cơ bản</td>
            </tr>
            <tr>
                <td><b>20%</b></td>
                <td>Rủi ro trung bình cao</td>
                <td>Trader có kinh nghiệm</td>
            </tr>
            <tr>
                <td><b>30%</b></td>
                <td>Rủi ro cao, tiềm năng lợi nhuận lớn</td>
                <td>Trader chuyên nghiệp</td>
            </tr>
        </table>
        
        <h3>Các tham số rủi ro quan trọng</h3>
        <ul>
            <li><b>Kích thước vị thế tối đa</b>: % vốn cho mỗi giao dịch</li>
            <li><b>Stop Loss</b>: % thua lỗ trước khi đóng lệnh</li>
            <li><b>Take Profit</b>: % lợi nhuận mục tiêu</li>
            <li><b>Đòn bẩy</b>: Mức nhân vốn (leverage)</li>
            <li><b>Thua lỗ tối đa mỗi ngày</b>: Giới hạn % thua lỗ mỗi ngày</li>
        </ul>
        
        <h3>Tính năng bảo vệ</h3>
        <ul>
            <li><b>Trailing Stop</b>: Tự động điều chỉnh stop loss theo giá di chuyển</li>
            <li><b>Nhập lệnh thông minh</b>: Tối ưu hóa điểm vào lệnh</li>
            <li><b>Lọc chế độ thị trường</b>: Chỉ giao dịch trong các điều kiện thị trường phù hợp</li>
            <li><b>Lọc biến động</b>: Tránh giao dịch khi biến động quá cao hoặc quá thấp</li>
        </ul>
        
        <h3>Lời khuyên</h3>
        <p>Luôn bắt đầu với mức rủi ro thấp và dần dần tăng lên khi bạn có nhiều kinh nghiệm. Không bao giờ giao dịch với số tiền bạn không thể chấp nhận mất.</p>
        """)
        risk_help_layout.addWidget(risk_help_text)
        help_tabs.addTab(risk_help_tab, "Cấu Hình Rủi Ro")
        
        # Tab Chiến lược
        strategy_help_tab = QWidget()
        strategy_help_layout = QVBoxLayout(strategy_help_tab)
        
        strategy_help_text = QTextEdit()
        strategy_help_text.setReadOnly(True)
        strategy_help_text.setHtml("""
        <h2>Hướng Dẫn Chiến Lược Giao Dịch</h2>
        <p>Hệ thống hỗ trợ nhiều chiến lược giao dịch khác nhau, mỗi chiến lược phù hợp với các điều kiện thị trường cụ thể:</p>
        
        <h3>Các chiến lược có sẵn</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th>Chiến lược</th>
                <th>Mô tả</th>
                <th>Điều kiện thị trường lý tưởng</th>
            </tr>
            <tr>
                <td><b>Adaptive Strategy</b></td>
                <td>Tự động điều chỉnh theo chế độ thị trường hiện tại</td>
                <td>Mọi điều kiện thị trường</td>
            </tr>
            <tr>
                <td><b>ML Integrated Strategy</b></td>
                <td>Sử dụng học máy để dự đoán xu hướng giá</td>
                <td>Thị trường có xu hướng rõ ràng</td>
            </tr>
            <tr>
                <td><b>Trend Following</b></td>
                <td>Theo xu hướng thị trường</td>
                <td>Thị trường tăng hoặc giảm mạnh</td>
            </tr>
            <tr>
                <td><b>Ranging Market</b></td>
                <td>Giao dịch trong kênh giá sideway</td>
                <td>Thị trường đi ngang</td>
            </tr>
            <tr>
                <td><b>Fibonacci Retracement</b></td>
                <td>Sử dụng các mức Fibonacci để xác định điểm vào/ra</td>
                <td>Thị trường điều chỉnh trong xu hướng</td>
            </tr>
        </table>
        
        <h3>Các tham số chiến lược</h3>
        <ul>
            <li><b>Activation Threshold</b>: Ngưỡng độ tin cậy để kích hoạt tín hiệu</li>
            <li><b>Callback Rate</b>: Tốc độ phản ứng với biến động giá</li>
            <li><b>Trend Confirmation Periods</b>: Số nến để xác nhận xu hướng</li>
            <li><b>Timeframes</b>: Khung thời gian phân tích</li>
        </ul>
        
        <h3>Tối ưu hóa chiến lược</h3>
        <p>Để tối ưu hóa chiến lược của bạn:</p>
        <ul>
            <li>Chạy backtest trên dữ liệu lịch sử trước khi áp dụng</li>
            <li>Bắt đầu với các tham số mặc định và điều chỉnh dần dần</li>
            <li>Theo dõi hiệu suất và điều chỉnh nếu cần</li>
            <li>Kết hợp với cấu hình rủi ro phù hợp</li>
        </ul>
        """)
        strategy_help_layout.addWidget(strategy_help_text)
        help_tabs.addTab(strategy_help_tab, "Chiến Lược")
        
        # Tab FAQ
        faq_tab = QWidget()
        faq_layout = QVBoxLayout(faq_tab)
        
        faq_text = QTextEdit()
        faq_text.setReadOnly(True)
        faq_text.setHtml("""
        <h2>Câu Hỏi Thường Gặp (FAQ)</h2>
        
        <h3>Q: Bot có hoạt động khi tôi tắt máy tính không?</h3>
        <p>A: Không, bot cần máy tính của bạn hoạt động để chạy. Nếu bạn muốn bot hoạt động 24/7, hãy xem xét chạy trên một máy chủ đám mây hoặc VPS.</p>
        
        <h3>Q: Tôi có thể sử dụng bot với sàn giao dịch nào?</h3>
        <p>A: Hiện tại, bot hỗ trợ Binance Futures là chính. Các sàn khác sẽ được hỗ trợ trong các phiên bản tương lai.</p>
        
        <h3>Q: Tôi nên bắt đầu với số vốn bao nhiêu?</h3>
        <p>A: Chúng tôi khuyên bạn nên bắt đầu với số vốn nhỏ (100-500 USDT) trong môi trường testnet trước, sau đó chuyển sang tài khoản thực với số vốn bạn có thể chấp nhận mất.</p>
        
        <h3>Q: Bot có tự động nạp hoặc rút tiền không?</h3>
        <p>A: Không, bot chỉ thực hiện giao dịch. Việc nạp và rút tiền phải được thực hiện thủ công trên sàn giao dịch.</p>
        
        <h3>Q: Làm thế nào để tôi biết bot đang hoạt động đúng?</h3>
        <p>A: Bạn có thể theo dõi hoạt động của bot thông qua tab Logs và Tổng Quan. Bot cũng gửi thông báo đến Telegram nếu bạn đã cấu hình.</p>
        
        <h3>Q: Tôi có thể sử dụng bot trên nhiều tài khoản cùng lúc không?</h3>
        <p>A: Mỗi phiên bản bot chỉ có thể kết nối với một tài khoản tại một thời điểm. Để sử dụng nhiều tài khoản, bạn cần chạy nhiều phiên bản bot.</p>
        
        <h3>Q: Làm thế nào để cập nhật bot?</h3>
        <p>A: Nhấn nút "Kiểm Tra Cập Nhật" trên tab Tổng Quan. Bot sẽ tự động kiểm tra và tải các bản cập nhật mới.</p>
        
        <h3>Q: Tôi nên chọn chiến lược nào?</h3>
        <p>A: Nếu bạn mới bắt đầu, hãy sử dụng "Adaptive Strategy" vì nó tự động điều chỉnh theo điều kiện thị trường. Khi bạn có nhiều kinh nghiệm hơn, bạn có thể thử các chiến lược khác.</p>
        
        <h3>Q: Làm thế nào để sao lưu cấu hình của tôi?</h3>
        <p>A: Trên tab Cài Đặt, nhấn nút "Lưu Cấu Hình". Cấu hình sẽ được lưu vào thư mục bạn chọn.</p>
        
        <h3>Q: Tôi gặp lỗi khi kết nối API, phải làm sao?</h3>
        <p>A: Hãy kiểm tra lại API Key và Secret của bạn. Đảm bảo rằng chúng có quyền giao dịch future và đã được kích hoạt trên Binance.</p>
        """)
        faq_layout.addWidget(faq_text)
        help_tabs.addTab(faq_tab, "FAQ")
        
        # Thêm help_tabs vào layout
        layout.addWidget(help_tabs)
        
        # Liên kết và hỗ trợ
        support_layout = QHBoxLayout()
        
        docs_button = QPushButton("Tài Liệu Chi Tiết")
        docs_button.clicked.connect(lambda: webbrowser.open("https://github.com/username/trading-bot/wiki"))
        support_layout.addWidget(docs_button)
        
        contact_button = QPushButton("Liên Hệ Hỗ Trợ")
        contact_button.clicked.connect(lambda: webbrowser.open("mailto:support@example.com"))
        support_layout.addWidget(contact_button)
        
        layout.addLayout(support_layout)
        
        # Thêm tab vào tabs
        self.tabs.addTab(help_tab, "Tài Liệu")
    
    def load_config(self):
        """Tải cấu hình từ file"""
        config_file = "account_config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Tải các thông số API
                if "api_key" in config:
                    self.api_key_input.setText(config["api_key"])
                
                if "api_secret" in config:
                    self.api_secret_input.setText(config["api_secret"])
                
                if "testnet" in config:
                    self.api_mode_combo.setCurrentIndex(0 if config["testnet"] else 1)
                
                # Tải thông số Telegram
                if "telegram_token" in config:
                    self.telegram_token_input.setText(config["telegram_token"])
                
                if "telegram_chat_id" in config:
                    self.telegram_chat_id_input.setText(config["telegram_chat_id"])
                
                if "telegram_enabled" in config:
                    self.telegram_checkbox.setChecked(config["telegram_enabled"])
                
                # Tải các thông số khác
                if "auto_trading" in config:
                    self.auto_trading_checkbox.setChecked(config["auto_trading"])
                
                if "detailed_logging" in config:
                    self.detailed_log_checkbox.setChecked(config["detailed_logging"])
                
                if "auto_restart" in config:
                    self.auto_restart_checkbox.setChecked(config["auto_restart"])
                
                if "data_dir" in config:
                    self.data_dir_input.setText(config["data_dir"])
                
                if "update_interval" in config:
                    self.update_interval_spin.setValue(config["update_interval"])
                
                # Tải thông số rủi ro
                if "risk_level" in config:
                    self.current_risk_level = config["risk_level"]
                    self.set_risk_level_ui(self.current_risk_level)
                
                logger.info("Đã tải cấu hình từ file account_config.json")
            except Exception as e:
                logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
                QMessageBox.warning(self, "Lỗi Cấu Hình", f"Không thể tải cấu hình: {str(e)}")
    
    def save_config(self):
        """Lưu cấu hình vào file"""
        config_file = "account_config.json"
        
        try:
            # Kiểm tra xem file đã tồn tại chưa
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Cập nhật các thông số API
            config["api_key"] = self.api_key_input.text()
            config["api_secret"] = self.api_secret_input.text()
            config["testnet"] = (self.api_mode_combo.currentIndex() == 0)
            
            # Cập nhật thông số Telegram
            config["telegram_token"] = self.telegram_token_input.text()
            config["telegram_chat_id"] = self.telegram_chat_id_input.text()
            config["telegram_enabled"] = self.telegram_checkbox.isChecked()
            
            # Lưu lại cấu hình vào file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
            # Hiển thị thông báo
            QMessageBox.information(self, "Thành công", "Đã lưu cài đặt API thành công!")
            logger.info("Đã lưu cấu hình API thành công")
            
            # Cập nhật các thông số khác
            config["auto_trading"] = self.auto_trading_checkbox.isChecked()
            config["detailed_logging"] = self.detailed_log_checkbox.isChecked()
            config["auto_restart"] = self.auto_restart_checkbox.isChecked()
            config["data_dir"] = self.data_dir_input.text()
            config["update_interval"] = self.update_interval_spin.value()
            
            # Lưu file
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            logger.info("Đã lưu cấu hình vào file account_config.json")
            QMessageBox.information(self, "Lưu Cấu Hình", "Cấu hình đã được lưu thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")
            QMessageBox.warning(self, "Lỗi Cấu Hình", f"Không thể lưu cấu hình: {str(e)}")
    
    def reset_config(self):
        """Khôi phục cấu hình mặc định"""
        if QMessageBox.question(self, "Khôi Phục Mặc Định", 
                               "Bạn có chắc muốn khôi phục về cấu hình mặc định?",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            # Khôi phục các thông số về mặc định
            self.api_key_input.clear()
            self.api_secret_input.clear()
            self.api_mode_combo.setCurrentIndex(0)  # Testnet
            
            self.telegram_token_input.clear()
            self.telegram_chat_id_input.clear()
            self.telegram_checkbox.setChecked(False)
            
            self.auto_trading_checkbox.setChecked(True)
            self.detailed_log_checkbox.setChecked(True)
            self.auto_restart_checkbox.setChecked(True)
            self.data_dir_input.setText("./data")
            self.update_interval_spin.setValue(10)
            
            # Khôi phục mức rủi ro về mặc định
            self.current_risk_level = "20"
            self.set_risk_level_ui(self.current_risk_level)
            
            logger.info("Đã khôi phục cấu hình về mặc định")
            QMessageBox.information(self, "Khôi Phục Mặc Định", "Cấu hình đã được khôi phục về mặc định!")
    
    def browse_data_dir(self):
        """Chọn thư mục dữ liệu"""
        dir_path = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Dữ Liệu", 
                                                  self.data_dir_input.text())
        if dir_path:
            self.data_dir_input.setText(dir_path)
    
    def init_risk_levels(self):
        """Khởi tạo thông tin mức rủi ro"""
        risk_descriptions = {
            "10": "Rủi ro thấp - Phù hợp cho người mới bắt đầu hoặc người có tâm lý thận trọng",
            "15": "Rủi ro vừa phải - Cân bằng giữa an toàn và cơ hội sinh lời",
            "20": "Rủi ro trung bình cao - Phù hợp cho trader có kinh nghiệm",
            "30": "Rủi ro cao - Chỉ dành cho trader chuyên nghiệp với khả năng chịu đựng rủi ro cao"
        }
        
        self.risk_descriptions = risk_descriptions
        self.set_risk_level_ui(self.current_risk_level)
    
    def set_risk_level_ui(self, risk_level):
        """Thiết lập UI theo mức rủi ro"""
        if risk_level not in ["10", "15", "20", "30"]:
            risk_level = "20"  # Mặc định
        
        self.current_risk_level = risk_level
        
        # Cập nhật combo box
        index_map = {"10": 0, "15": 1, "20": 2, "30": 3}
        self.risk_level_combo.setCurrentIndex(index_map.get(risk_level, 2))
        
        # Cập nhật mô tả
        self.risk_description_label.setText(self.risk_descriptions.get(risk_level, ""))
        
        # Cập nhật nhãn trên tab tổng quan
        self.risk_label.setText(f"{risk_level}%")
        
        # Tải cấu hình rủi ro từ file
        try:
            config_path = f"risk_configs/risk_level_{risk_level}.json"
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    risk_config = json.load(f)
                
                # Cập nhật UI với các tham số rủi ro
                self.max_position_size_spin.setValue(risk_config.get("max_position_size_percent", 2.0))
                self.max_positions_spin.setValue(risk_config.get("max_open_positions", 5))
                self.stop_loss_spin.setValue(risk_config.get("stop_loss_percent", 1.0))
                self.take_profit_spin.setValue(risk_config.get("take_profit_percent", 3.0))
                
                # Đòn bẩy
                leverage = risk_config.get("leverage", 5)
                leverage_index_map = {1: 0, 3: 1, 5: 2, 7: 3, 10: 4, 20: 5}
                self.leverage_combo.setCurrentIndex(leverage_index_map.get(leverage, 2))
                
                # Thua lỗ tối đa
                self.max_daily_loss_spin.setValue(risk_config.get("max_daily_loss_percent", 5.0))
                
                # Các tùy chọn bảo vệ
                self.trailing_stop_checkbox.setChecked(risk_config.get("enable_trailing_stop", False))
                self.trailing_stop_callback_spin.setValue(risk_config.get("trailing_stop_callback", 0.2))
                self.smart_entry_checkbox.setChecked(risk_config.get("use_smart_entry", True))
                self.market_regime_filter_checkbox.setChecked(risk_config.get("use_market_regime_filter", True))
                self.volatility_filter_checkbox.setChecked(risk_config.get("use_volatility_filter", True))
                
                logger.info(f"Đã tải cấu hình rủi ro {risk_level}%")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình rủi ro {risk_level}%: {str(e)}")
    
    def risk_level_changed(self, index):
        """Xử lý khi thay đổi mức rủi ro"""
        risk_levels = ["10", "15", "20", "30"]
        if 0 <= index < len(risk_levels):
            self.set_risk_level_ui(risk_levels[index])
    
    def apply_risk_config(self):
        """Áp dụng cấu hình rủi ro hiện tại"""
        try:
            from risk_level_manager import RiskLevelManager
            risk_manager = RiskLevelManager()
            success = risk_manager.apply_risk_config(self.current_risk_level)
            
            if success:
                logger.info(f"Đã áp dụng cấu hình rủi ro {self.current_risk_level}%")
                QMessageBox.information(self, "Áp Dụng Cấu Hình Rủi Ro", 
                                       f"Đã áp dụng cấu hình rủi ro {self.current_risk_level}% thành công!")
            else:
                logger.error(f"Không thể áp dụng cấu hình rủi ro {self.current_risk_level}%")
                QMessageBox.warning(self, "Lỗi Cấu Hình Rủi Ro", 
                                    f"Không thể áp dụng cấu hình rủi ro {self.current_risk_level}%")
        except Exception as e:
            logger.error(f"Lỗi khi áp dụng cấu hình rủi ro: {str(e)}")
            QMessageBox.warning(self, "Lỗi Cấu Hình Rủi Ro", 
                              f"Lỗi: {str(e)}")
    
    def save_risk_config(self):
        """Lưu cấu hình rủi ro hiện tại"""
        try:
            # Tạo thư mục risk_configs nếu chưa tồn tại
            os.makedirs("risk_configs", exist_ok=True)
            
            # Thu thập thông số từ UI
            risk_config = {
                "max_position_size_percent": self.max_position_size_spin.value(),
                "max_open_positions": self.max_positions_spin.value(),
                "stop_loss_percent": self.stop_loss_spin.value(),
                "take_profit_percent": self.take_profit_spin.value(),
                "leverage": int(self.leverage_combo.currentText().replace("x", "")),
                "max_daily_loss_percent": self.max_daily_loss_spin.value(),
                "enable_trailing_stop": self.trailing_stop_checkbox.isChecked(),
                "trailing_stop_callback": self.trailing_stop_callback_spin.value(),
                "use_smart_entry": self.smart_entry_checkbox.isChecked(),
                "use_market_regime_filter": self.market_regime_filter_checkbox.isChecked(),
                "use_volatility_filter": self.volatility_filter_checkbox.isChecked(),
                "session_start_hour": 0,
                "session_end_hour": 24,
                "auto_compounding": True,
            }
            
            # Lưu vào file
            config_path = f"risk_configs/risk_level_{self.current_risk_level}.json"
            with open(config_path, 'w', encoding="utf-8") as f:
                json.dump(risk_config, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình rủi ro {self.current_risk_level}%")
            QMessageBox.information(self, "Lưu Cấu Hình Rủi Ro", 
                                   f"Đã lưu cấu hình rủi ro {self.current_risk_level}% thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình rủi ro: {str(e)}")
            QMessageBox.warning(self, "Lỗi Cấu Hình Rủi Ro", 
                              f"Lỗi: {str(e)}")
    
    def activate_strategy(self):
        """Kích hoạt chiến lược đã chọn"""
        strategy = self.strategy_combo.currentText()
        
        # Tạo các thông số chiến lược
        strategy_params = {
            "activation_threshold": self.activation_threshold_spin.value(),
            "callback_rate": self.callback_rate_spin.value(),
            "trend_confirmation_periods": self.trend_confirmation_spin.value(),
            "timeframe": self.timeframes_combo.currentText()
        }
        
        # Lưu cấu hình chiến lược
        try:
            os.makedirs("strategies", exist_ok=True)
            
            # Tạo tên file dựa trên chiến lược
            strategy_file = strategy.lower().replace(" ", "_") + ".json"
            strategy_path = os.path.join("strategies", strategy_file)
            
            with open(strategy_path, 'w', encoding="utf-8") as f:
                json.dump(strategy_params, f, indent=4)
            
            logger.info(f"Đã lưu cấu hình chiến lược {strategy}")
            
            # Cập nhật cấu hình tài khoản với chiến lược hiện tại
            config_file = "account_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding="utf-8") as f:
                    config = json.load(f)
                
                config["active_strategy"] = strategy
                config["strategy_file"] = strategy_file
                
                with open(config_file, 'w', encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
            
            QMessageBox.information(self, "Kích Hoạt Chiến Lược", 
                                   f"Đã kích hoạt chiến lược {strategy} thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi khi kích hoạt chiến lược: {str(e)}")
            QMessageBox.warning(self, "Lỗi Chiến Lược", 
                              f"Lỗi: {str(e)}")
    
    def save_strategy_params(self):
        """Lưu tham số chiến lược"""
        strategy = self.strategy_combo.currentText()
        
        # Tạo các thông số chiến lược
        strategy_params = {
            "activation_threshold": self.activation_threshold_spin.value(),
            "callback_rate": self.callback_rate_spin.value(),
            "trend_confirmation_periods": self.trend_confirmation_spin.value(),
            "timeframe": self.timeframes_combo.currentText()
        }
        
        # Lưu cấu hình chiến lược
        try:
            os.makedirs("strategies", exist_ok=True)
            
            # Tạo tên file dựa trên chiến lược
            strategy_file = strategy.lower().replace(" ", "_") + ".json"
            strategy_path = os.path.join("strategies", strategy_file)
            
            with open(strategy_path, 'w', encoding="utf-8") as f:
                json.dump(strategy_params, f, indent=4)
            
            logger.info(f"Đã lưu tham số chiến lược {strategy}")
            QMessageBox.information(self, "Lưu Tham Số Chiến Lược", 
                                   f"Đã lưu tham số chiến lược {strategy} thành công!")
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu tham số chiến lược: {str(e)}")
            QMessageBox.warning(self, "Lỗi Chiến Lược", 
                              f"Lỗi: {str(e)}")
    
    def start_bot(self):
        """Bắt đầu bot giao dịch"""
        # Kiểm tra xem bot đã đang chạy chưa
        if self.bot_running:
            QMessageBox.information(self, "Bot Đang Chạy", 
                                   "Bot đã đang chạy. Vui lòng dừng bot trước khi bắt đầu lại.")
            return
        
        # Kiểm tra cấu hình API
        if not self.api_key_input.text() or not self.api_secret_input.text():
            QMessageBox.warning(self, "Thiếu Cấu Hình API", 
                              "Vui lòng cấu hình API Key và Secret trong tab Cài Đặt.")
            return
        
        try:
            # Lưu cấu hình
            self.save_config()
            
            # Khởi tạo thread bot
            self.bot_thread = BotThread(self, risk_level=self.current_risk_level)
            self.bot_thread.update_signal.connect(self.append_log)
            self.bot_thread.error_signal.connect(self.handle_bot_error)
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo bot: {str(e)}")
            QMessageBox.critical(self, "Lỗi Khởi Động", f"Không thể khởi động bot: {str(e)}")
            return
        
        # Bắt đầu bot
        self.bot_thread.start()
        
        # Cập nhật trạng thái
        self.bot_running = True
        self.status_label.setText("Đang chạy")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        logger.info("Bot đã bắt đầu")
    
    def stop_bot(self):
        """Dừng bot giao dịch"""
        if not self.bot_running or self.bot_thread is None:
            return
        
        # Hiển thị hộp thoại xác nhận
        if QMessageBox.question(self, "Dừng Bot", 
                               "Bạn có chắc muốn dừng bot?",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            # Gửi tín hiệu dừng đến thread
            self.bot_thread.stop()
            
            # Cập nhật trạng thái
            self.bot_running = False
            self.status_label.setText("Đã dừng")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            logger.info("Bot đã dừng")
    
    def handle_bot_error(self, error_message):
        """Xử lý lỗi từ bot thread"""
        logger.error(f"Lỗi bot: {error_message}")
        self.append_log(f"LỖI: {error_message}")
        
        # Nếu bot bị lỗi, dừng lại
        self.bot_running = False
        self.status_label.setText("Lỗi")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def check_update(self):
        """Kiểm tra cập nhật mới"""
        # Tạo dialog hiển thị tiến trình
        self.update_dialog = QDialog(self)
        self.update_dialog.setWindowTitle("Kiểm Tra Cập Nhật")
        self.update_dialog.setFixedSize(400, 150)
        
        dialog_layout = QVBoxLayout(self.update_dialog)
        
        # Thêm progress bar
        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        dialog_layout.addWidget(self.update_progress_bar)
        
        # Thêm nhãn trạng thái
        self.update_status_label = QLabel("Đang kiểm tra cập nhật...")
        dialog_layout.addWidget(self.update_status_label)
        
        # Nút hủy
        cancel_button = QPushButton("Hủy")
        cancel_button.clicked.connect(self.update_dialog.reject)
        dialog_layout.addWidget(cancel_button)
        
        # Khởi tạo thread cập nhật
        self.update_thread = UpdateThread(self)
        self.update_thread.update_progress.connect(self.update_progress)
        self.update_thread.update_completed.connect(self.update_completed)
        
        # Bắt đầu thread cập nhật
        self.update_thread.start()
        
        # Hiển thị dialog
        self.update_dialog.exec_()
    
    def update_progress(self, progress, message):
        """Cập nhật tiến trình cập nhật"""
        self.update_progress_bar.setValue(progress)
        self.update_status_label.setText(message)
    
    def update_completed(self, success, message):
        """Xử lý khi cập nhật hoàn tất"""
        self.update_dialog.accept()
        
        if success:
            QMessageBox.information(self, "Cập Nhật", message)
        else:
            QMessageBox.warning(self, "Lỗi Cập Nhật", message)
    
    def append_log(self, message):
        """Thêm thông báo log vào text edit"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        self.log_text.append(log_message)
        # Cuộn xuống cuối
        self.log_text.moveCursor(QTextCursor.End)
    
    def refresh_logs(self):
        """Làm mới logs"""
        # Lọc log theo loại
        log_filter = self.log_filter_combo.currentText()
        log_level = self.log_level_combo.currentText()
        
        try:
            # Đọc file log
            log_file = "logs/trading_bot.log"
            if not os.path.exists(log_file):
                return
            
            # Xóa log hiện tại
            self.log_text.clear()
            
            # Đọc và lọc log
            with open(log_file, 'r', encoding="utf-8") as f:
                for line in f:
                    # Lọc theo cấp độ log
                    if log_level != "DEBUG" and log_level not in line:
                        continue
                    
                    # Lọc theo loại log
                    if log_filter == "Giao dịch" and "TRADE" not in line:
                        continue
                    elif log_filter == "Lỗi" and "ERROR" not in line:
                        continue
                    elif log_filter == "Hệ thống" and "SYSTEM" not in line:
                        continue
                    elif log_filter == "Thông báo" and "NOTIFY" not in line:
                        continue
                    
                    self.log_text.append(line.strip())
            
            # Cuộn xuống cuối
            self.log_text.moveCursor(QTextCursor.End)
            
        except Exception as e:
            logger.error(f"Lỗi khi làm mới logs: {str(e)}")
    
    def clear_logs(self):
        """Xóa logs"""
        if QMessageBox.question(self, "Xóa Logs", 
                               "Bạn có chắc muốn xóa nội dung logs hiện tại?",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.log_text.clear()
    
    def update_ui(self):
        """Cập nhật giao diện người dùng định kỳ"""
        # Cập nhật thông tin tài khoản
        if self.bot_running:
            # TODO: Cập nhật thông tin từ bot trong thời gian thực
            # Hiện tại chỉ là dữ liệu mẫu
            pass
        
        # Cập nhật thời gian
        self.status_bar.showMessage(f"Thời gian hiện tại: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        if self.bot_running:
            reply = QMessageBox.question(self, "Xác nhận thoát", 
                                       "Bot đang chạy. Bạn có chắc muốn thoát?",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Dừng bot
                if self.bot_thread:
                    self.bot_thread.stop()
                
                # Dừng thread theo dõi log
                if self.log_monitor:
                    self.log_monitor.stop()
                
                # Lưu cấu hình
                self.save_config()
                
                event.accept()
            else:
                event.ignore()
        else:
            # Lưu cấu hình
            self.save_config()
            
            # Dừng thread theo dõi log
            if self.log_monitor:
                self.log_monitor.stop()
            
            event.accept()


def main():
    """Hàm main"""
    # Đảm bảo thư mục logs tồn tại
    os.makedirs("logs", exist_ok=True)
    
    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Sử dụng style Fusion cho giao diện đồng nhất
    
    # Thiết lập stylesheet
    stylesheet = """
    QMainWindow {
        background-color: #f0f0f0;
    }
    
    QTabWidget::pane {
        border: 1px solid #d7d7d7;
        background-color: #ffffff;
    }
    
    QTabBar::tab {
        background-color: #e0e0e0;
        padding: 8px 12px;
        border: 1px solid #d7d7d7;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    
    QTabBar::tab:selected {
        background-color: #ffffff;
        border-bottom: 1px solid #ffffff;
    }
    
    QGroupBox {
        border: 1px solid #d7d7d7;
        border-radius: 5px;
        margin-top: 10px;
        background-color: #ffffff;
        padding-top: 10px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        background-color: #e7e7e7;
        padding: 5px 10px;
        border-radius: 3px;
    }
    
    QPushButton {
        background-color: #2979ff;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
    }
    
    QPushButton:hover {
        background-color: #1565c0;
    }
    
    QPushButton:disabled {
        background-color: #cccccc;
    }
    
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        border: 1px solid #d7d7d7;
        border-radius: 4px;
        padding: 5px;
        background-color: #f9f9f9;
    }
    
    QTableWidget {
        border: 1px solid #d7d7d7;
        gridline-color: #e0e0e0;
        selection-background-color: #2979ff;
        selection-color: white;
    }
    
    QTableWidget QHeaderView::section {
        background-color: #e7e7e7;
        padding: 5px;
        border: 1px solid #d7d7d7;
        font-weight: bold;
    }
    
    QScrollBar:vertical {
        border: none;
        background: #f0f0f0;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    
    QScrollBar::handle:vertical {
        background: #c0c0c0;
        min-height: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    
    QProgressBar {
        border: 1px solid #d7d7d7;
        border-radius: 4px;
        text-align: center;
        background-color: #f9f9f9;
    }
    
    QProgressBar::chunk {
        background-color: #2979ff;
        border-radius: 3px;
    }
    """
    app.setStyleSheet(stylesheet)
    
    # Khởi tạo cửa sổ chính
    window = MainWindow()
    window.show()
    
    # Chạy ứng dụng
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()