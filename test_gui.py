#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Giao diện test để kiểm tra các nút và chức năng
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import json
import logging
from datetime import datetime

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_gui.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_gui")

# Constants
VERSION = "1.0.0"
CONFIG_FILE = "test_gui_config.json"
DEFAULT_CONFIG = {
    "api_mode": "testnet",
    "risk_percentage": 1.0,
    "max_leverage": 5,
    "auto_trading": False,
    "market_analysis": True,
    "sltp_management": True,
    "trailing_stop": True,
    "telegram_notifications": True,
    "update_interval": 30,
    "last_check_update": None
}

class TestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Kiểm Tra Giao Diện Hệ Thống Giao Dịch v{VERSION}")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Thiết lập biến trạng thái
        self.is_running = False
        self.update_checking = False
        self.account_balance = 0.0
        self.positions = []
        self.load_config()
        
        # Tạo style cho giao diện
        self.style = ttk.Style()
        self.style.theme_use('clam')  # Sử dụng theme clam
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('TLabel', font=('Helvetica', 10))
        self.style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        self.style.configure('Status.TLabel', font=('Helvetica', 11))
        self.style.configure('Running.TLabel', foreground='green')
        self.style.configure('Stopped.TLabel', foreground='red')
        self.style.configure('Warning.TLabel', foreground='orange')
        
        # Tạo giao diện
        self.create_gui()
        
        # Khởi tạo các luồng
        self.update_thread = None
        self.status_thread = None
        
        # Thiết lập sự kiện đóng cửa sổ
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        """Tải cấu hình từ file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                    # Đảm bảo tất cả các khóa cần thiết đều có mặt
                    for key, value in DEFAULT_CONFIG.items():
                        if key not in self.config:
                            self.config[key] = value
            else:
                self.config = DEFAULT_CONFIG
                self.save_config()
            logger.info("Đã tải cấu hình giao diện test")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            self.config = DEFAULT_CONFIG
            self.save_config()

    def save_config(self):
        """Lưu cấu hình vào file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Đã lưu cấu hình giao diện test")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}")

    def create_gui(self):
        """Tạo giao diện người dùng"""
        # Tạo frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Chia thành 2 cột: trái (điều khiển) và phải (hiển thị dữ liệu)
        control_frame = ttk.Frame(main_frame, padding="5", relief="ridge", borderwidth=1)
        control_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        data_frame = ttk.Frame(main_frame, padding="5")
        data_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame điều khiển
        self.create_control_panel(control_frame)
        
        # Frame hiển thị dữ liệu
        self.create_data_display(data_frame)

    def create_control_panel(self, parent):
        """Tạo panel điều khiển"""
        # Frame trạng thái hệ thống
        status_frame = ttk.LabelFrame(parent, text="Trạng Thái Hệ Thống", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        # Trạng thái hoạt động
        status_row = ttk.Frame(status_frame)
        status_row.pack(fill=tk.X, pady=5)
        ttk.Label(status_row, text="Trạng thái:", style='Header.TLabel').pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_row, text="Chưa chạy", style='Stopped.TLabel')
        self.status_label.pack(side=tk.RIGHT)
        
        # Số dư tài khoản
        balance_row = ttk.Frame(status_frame)
        balance_row.pack(fill=tk.X, pady=5)
        ttk.Label(balance_row, text="Số dư (test):", style='Header.TLabel').pack(side=tk.LEFT)
        self.balance_label = ttk.Label(balance_row, text="0.00 USDT")
        self.balance_label.pack(side=tk.RIGHT)
        
        # Số vị thế mở
        positions_row = ttk.Frame(status_frame)
        positions_row.pack(fill=tk.X, pady=5)
        ttk.Label(positions_row, text="Vị thế mở:", style='Header.TLabel').pack(side=tk.LEFT)
        self.positions_label = ttk.Label(positions_row, text="0")
        self.positions_label.pack(side=tk.RIGHT)
        
        # Frame điều khiển chính
        control_frame = ttk.LabelFrame(parent, text="Điều Khiển", padding="10")
        control_frame.pack(fill=tk.X, pady=10)
        
        # Nút khởi động/dừng hệ thống
        start_stop_frame = ttk.Frame(control_frame)
        start_stop_frame.pack(fill=tk.X, pady=5)
        self.start_button = ttk.Button(start_stop_frame, text="Khởi Động Test", command=self.start_system)
        self.start_button.pack(fill=tk.X, pady=2)
        self.stop_button = ttk.Button(start_stop_frame, text="Dừng Test", command=self.stop_system, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=2)
        
        # Frame Kiểm tra chức năng
        test_frame = ttk.LabelFrame(parent, text="Kiểm Tra Chức Năng", padding="10")
        test_frame.pack(fill=tk.X, pady=10)
        
        # Các nút kiểm tra
        ttk.Button(test_frame, text="Kiểm Tra Kết Nối API", command=self.test_api_connection).pack(fill=tk.X, pady=2)
        ttk.Button(test_frame, text="Kiểm Tra Lấy Dữ Liệu Thị Trường", command=self.test_market_data).pack(fill=tk.X, pady=2)
        ttk.Button(test_frame, text="Kiểm Tra Thông Báo Telegram", command=self.test_telegram).pack(fill=tk.X, pady=2)
        ttk.Button(test_frame, text="Kiểm Tra Quản Lý Vị Thế", command=self.test_position_management).pack(fill=tk.X, pady=2)
        ttk.Button(test_frame, text="Kiểm Tra Phân Tích Kỹ Thuật", command=self.test_technical_analysis).pack(fill=tk.X, pady=2)
        
        # Frame tùy chọn hệ thống
        options_frame = ttk.LabelFrame(parent, text="Tùy Chọn Hệ Thống", padding="10")
        options_frame.pack(fill=tk.X, pady=10)
        
        # Checkbox cho các tùy chọn
        self.auto_trading_var = tk.BooleanVar(value=self.config["auto_trading"])
        ttk.Checkbutton(options_frame, text="Giao dịch tự động", variable=self.auto_trading_var, 
                       command=self.update_options).pack(fill=tk.X, pady=2)
        
        self.market_analysis_var = tk.BooleanVar(value=self.config["market_analysis"])
        ttk.Checkbutton(options_frame, text="Phân tích thị trường", variable=self.market_analysis_var, 
                       command=self.update_options).pack(fill=tk.X, pady=2)
        
        self.sltp_management_var = tk.BooleanVar(value=self.config["sltp_management"])
        ttk.Checkbutton(options_frame, text="Quản lý SL/TP", variable=self.sltp_management_var, 
                       command=self.update_options).pack(fill=tk.X, pady=2)
        
        self.trailing_stop_var = tk.BooleanVar(value=self.config["trailing_stop"])
        ttk.Checkbutton(options_frame, text="Trailing Stop", variable=self.trailing_stop_var, 
                       command=self.update_options).pack(fill=tk.X, pady=2)
        
        self.telegram_notifications_var = tk.BooleanVar(value=self.config["telegram_notifications"])
        ttk.Checkbutton(options_frame, text="Thông báo Telegram", variable=self.telegram_notifications_var, 
                       command=self.update_options).pack(fill=tk.X, pady=2)
        
        # Frame cài đặt rủi ro
        risk_frame = ttk.LabelFrame(parent, text="Cài Đặt Rủi Ro", padding="10")
        risk_frame.pack(fill=tk.X, pady=10)
        
        # Mức rủi ro
        risk_level_frame = ttk.Frame(risk_frame)
        risk_level_frame.pack(fill=tk.X, pady=5)
        ttk.Label(risk_level_frame, text="Mức rủi ro:").pack(side=tk.LEFT)
        self.risk_level_var = tk.StringVar(value="10")
        risk_combo = ttk.Combobox(risk_level_frame, textvariable=self.risk_level_var, state="readonly")
        risk_combo['values'] = ('10', '15', '20', '30')
        risk_combo.pack(side=tk.RIGHT)
        risk_combo.bind('<<ComboboxSelected>>', self.update_risk_level)
        
        # Đòn bẩy tối đa
        leverage_row = ttk.Frame(risk_frame)
        leverage_row.pack(fill=tk.X, pady=5)
        ttk.Label(leverage_row, text="Đòn bẩy (x):").pack(side=tk.LEFT)
        self.leverage_var = tk.IntVar(value=self.config["max_leverage"])
        leverage_scale = ttk.Scale(leverage_row, from_=1, to=20, variable=self.leverage_var, command=self.update_leverage)
        leverage_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.leverage_label = ttk.Label(leverage_row, text=f"{self.config['max_leverage']}x")
        self.leverage_label.pack(side=tk.RIGHT)

    def create_data_display(self, parent):
        """Tạo khu vực hiển thị dữ liệu"""
        # Notebook cho các tab
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab Kiểm Tra
        test_tab = ttk.Frame(notebook, padding="10")
        notebook.add(test_tab, text="Kiểm Tra")
        self.create_test_tab(test_tab)
        
        # Tab Thị Trường
        market_tab = ttk.Frame(notebook, padding="10")
        notebook.add(market_tab, text="Thị Trường")
        self.create_market_tab(market_tab)
        
        # Tab Vị Thế
        positions_tab = ttk.Frame(notebook, padding="10")
        notebook.add(positions_tab, text="Vị Thế")
        self.create_positions_tab(positions_tab)
        
        # Tab Nhật Ký
        log_tab = ttk.Frame(notebook, padding="10")
        notebook.add(log_tab, text="Nhật Ký")
        self.create_log_tab(log_tab)

    def create_test_tab(self, parent):
        """Tạo tab kiểm tra"""
        # Khu vực nhật ký kiểm tra
        log_frame = ttk.LabelFrame(parent, text="Nhật Ký Kiểm Tra", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.test_log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.test_log.pack(fill=tk.BOTH, expand=True)
        self.test_log.config(state=tk.DISABLED)
        
        # Khu vực trạng thái kiểm tra
        status_frame = ttk.LabelFrame(parent, text="Trạng Thái Kiểm Tra", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        # Tạo grid layout cho các trạng thái kiểm tra
        self.test_statuses = {}
        tests = [
            "Kết nối API", "Dữ liệu thị trường", "Thông báo Telegram", 
            "Quản lý vị thế", "Phân tích kỹ thuật"
        ]
        
        for i, test in enumerate(tests):
            row = i // 2
            col = i % 2
            
            test_frame = ttk.Frame(status_frame)
            test_frame.grid(row=row, column=col, sticky="ew", padx=10, pady=5)
            status_frame.grid_columnconfigure(col, weight=1)
            
            ttk.Label(test_frame, text=f"{test}:").pack(side=tk.LEFT)
            status_label = ttk.Label(test_frame, text="Chưa kiểm tra")
            status_label.pack(side=tk.RIGHT)
            self.test_statuses[test] = status_label

    def create_market_tab(self, parent):
        """Tạo nội dung tab thị trường"""
        # Frame tìm kiếm và lọc
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Tìm kiếm:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(filter_frame, text="Làm Mới", command=self.refresh_market_data).pack(side=tk.RIGHT, padx=5)
        
        # Treeview để hiển thị dữ liệu thị trường
        columns = ('symbol', 'price', 'change_24h', 'volume', 'signal', 'trend')
        self.market_tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        # Định nghĩa các cột
        self.market_tree.heading('symbol', text='Cặp Tiền')
        self.market_tree.heading('price', text='Giá Hiện Tại')
        self.market_tree.heading('change_24h', text='Thay Đổi 24h')
        self.market_tree.heading('volume', text='Khối Lượng')
        self.market_tree.heading('signal', text='Tín Hiệu')
        self.market_tree.heading('trend', text='Xu Hướng')
        
        # Định nghĩa độ rộng cột
        self.market_tree.column('symbol', width=100)
        self.market_tree.column('price', width=100)
        self.market_tree.column('change_24h', width=100)
        self.market_tree.column('volume', width=100)
        self.market_tree.column('signal', width=100)
        self.market_tree.column('trend', width=100)
        
        # Thêm thanh cuộn
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.market_tree.yview)
        self.market_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.market_tree.pack(fill=tk.BOTH, expand=True)
        
        # Thêm dữ liệu mẫu
        self.update_market_data()

    def create_positions_tab(self, parent):
        """Tạo nội dung tab vị thế"""
        # Treeview để hiển thị vị thế
        columns = ('symbol', 'type', 'entry_price', 'current_price', 'size', 'pnl', 'time', 'sl', 'tp')
        self.positions_tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        # Định nghĩa các cột
        self.positions_tree.heading('symbol', text='Cặp Tiền')
        self.positions_tree.heading('type', text='Loại')
        self.positions_tree.heading('entry_price', text='Giá Vào')
        self.positions_tree.heading('current_price', text='Giá Hiện Tại')
        self.positions_tree.heading('size', text='Kích Thước')
        self.positions_tree.heading('pnl', text='P/L (%)')
        self.positions_tree.heading('time', text='Thời Gian')
        self.positions_tree.heading('sl', text='Stop Loss')
        self.positions_tree.heading('tp', text='Take Profit')
        
        # Định nghĩa độ rộng cột
        self.positions_tree.column('symbol', width=100)
        self.positions_tree.column('type', width=80)
        self.positions_tree.column('entry_price', width=100)
        self.positions_tree.column('current_price', width=100)
        self.positions_tree.column('size', width=100)
        self.positions_tree.column('pnl', width=100)
        self.positions_tree.column('time', width=150)
        self.positions_tree.column('sl', width=100)
        self.positions_tree.column('tp', width=100)
        
        # Thêm thanh cuộn
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.positions_tree.pack(fill=tk.BOTH, expand=True)
        
        # Frame các nút điều khiển
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Mở Vị Thế Test", command=self.add_test_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Đóng Vị Thế Đã Chọn", command=self.close_selected_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Làm Mới", command=self.refresh_positions).pack(side=tk.RIGHT, padx=5)
        
        # Thêm dữ liệu mẫu
        self.update_positions_data()

    def create_log_tab(self, parent):
        """Tạo tab nhật ký"""
        # Khu vực nhật ký hoạt động
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Thêm nút làm mới và xóa nhật ký
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Làm Mới Nhật Ký", command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Xóa Nhật Ký", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        
        # Thêm log mẫu
        self.add_log("Hệ thống kiểm tra đã khởi động")

    def add_log(self, message):
        """Thêm thông báo vào nhật ký"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Thêm vào log text
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Ghi log
        logger.info(message)

    def add_test_log(self, message):
        """Thêm thông báo vào nhật ký kiểm tra"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Thêm vào test log
        self.test_log.config(state=tk.NORMAL)
        self.test_log.insert(tk.END, log_message)
        self.test_log.see(tk.END)
        self.test_log.config(state=tk.DISABLED)
        
        # Thêm vào log chính
        self.add_log(f"[KIỂM TRA] {message}")

    def update_test_status(self, test_name, status, passed=None):
        """Cập nhật trạng thái kiểm tra"""
        label = self.test_statuses.get(test_name)
        if label:
            label.config(text=status)
            if passed is not None:
                if passed:
                    label.config(foreground='green')
                else:
                    label.config(foreground='red')
            else:
                label.config(foreground='black')

    def start_system(self):
        """Khởi động hệ thống"""
        if not self.is_running:
            self.is_running = True
            self.status_label.config(text="Đang chạy", style='Running.TLabel')
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Cập nhật thông tin giả lập
            self.account_balance = 10000.0
            self.balance_label.config(text=f"{self.account_balance:.2f} USDT")
            
            # Khởi động luồng cập nhật
            self.update_thread = threading.Thread(target=self.update_data, daemon=True)
            self.update_thread.start()
            
            self.add_log("Hệ thống kiểm tra đã khởi động")
            messagebox.showinfo("Thông báo", "Hệ thống kiểm tra đã được khởi động thành công!")

    def stop_system(self):
        """Dừng hệ thống"""
        if self.is_running:
            self.is_running = False
            self.status_label.config(text="Đã dừng", style='Stopped.TLabel')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            self.add_log("Hệ thống kiểm tra đã dừng")
            messagebox.showinfo("Thông báo", "Hệ thống kiểm tra đã dừng!")

    def update_data(self):
        """Cập nhật dữ liệu theo chu kỳ"""
        while self.is_running:
            # Cập nhật dữ liệu thị trường
            self.update_market_data()
            
            # Cập nhật thông tin vị thế
            self.update_positions_data()
            
            # Đợi khoảng thời gian cập nhật
            time.sleep(5)

    def update_market_data(self):
        """Cập nhật dữ liệu thị trường"""
        # Xóa dữ liệu cũ
        for item in self.market_tree.get_children():
            self.market_tree.delete(item)
        
        # Thêm dữ liệu mẫu
        test_data = [
            ('BTCUSDT', '65432.50', '+2.5%', '2.5B', 'Mua', 'Tăng'),
            ('ETHUSDT', '3542.75', '+1.8%', '1.2B', 'Chờ', 'Sideway'),
            ('BNBUSDT', '567.80', '-0.5%', '350M', 'Bán', 'Giảm'),
            ('SOLUSDT', '128.45', '+5.2%', '820M', 'Mua mạnh', 'Tăng'),
            ('ADAUSDT', '0.45', '-1.2%', '150M', 'Chờ', 'Sideway'),
            ('XRPUSDT', '0.58', '+0.8%', '180M', 'Chờ', 'Tăng nhẹ'),
            ('DOGEUSDT', '0.12', '+3.5%', '95M', 'Mua', 'Tăng'),
            ('DOTUSDT', '6.82', '-0.3%', '65M', 'Chờ', 'Sideway')
        ]
        
        for data in test_data:
            self.market_tree.insert('', tk.END, values=data)
            
        if hasattr(self, 'positions_label'):
            self.positions_label.config(text=str(len(self.positions)))

    def update_positions_data(self):
        """Cập nhật dữ liệu vị thế"""
        # Xóa dữ liệu cũ
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        # Thêm dữ liệu vị thế
        for position in self.positions:
            self.positions_tree.insert('', tk.END, values=position)

    def add_test_position(self):
        """Thêm vị thế test"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Tạo vị thế mẫu (cặp tiền, loại, giá vào, giá hiện tại, kích thước, P/L, thời gian, SL, TP)
        position_types = ['LONG', 'SHORT']
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        
        import random
        symbol = random.choice(symbols)
        pos_type = random.choice(position_types)
        
        entry_price = round(random.uniform(100, 65000), 2)
        current_price = round(entry_price * (1 + random.uniform(-0.05, 0.05)), 2)
        
        size = round(random.uniform(0.01, 0.5), 3)
        
        if pos_type == 'LONG':
            pnl = round((current_price - entry_price) / entry_price * 100, 2)
            sl = round(entry_price * 0.97, 2)
            tp = round(entry_price * 1.05, 2)
        else:
            pnl = round((entry_price - current_price) / entry_price * 100, 2)
            sl = round(entry_price * 1.03, 2)
            tp = round(entry_price * 0.95, 2)
        
        new_position = (
            symbol, pos_type, entry_price, current_price, 
            size, f"{pnl}%", current_time, sl, tp
        )
        
        self.positions.append(new_position)
        self.positions_tree.insert('', tk.END, values=new_position)
        self.positions_label.config(text=str(len(self.positions)))
        
        self.add_log(f"Đã mở vị thế test: {symbol} {pos_type} tại giá {entry_price}")

    def close_selected_position(self):
        """Đóng vị thế đã chọn"""
        selected = self.positions_tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn vị thế để đóng")
            return
        
        for item in selected:
            values = self.positions_tree.item(item, 'values')
            self.positions_tree.delete(item)
            
            # Xóa khỏi danh sách vị thế
            for i, position in enumerate(self.positions):
                if position[0] == values[0] and position[6] == values[6]:  # Kiểm tra cặp tiền và thời gian
                    self.positions.pop(i)
                    break
        
        self.positions_label.config(text=str(len(self.positions)))
        self.add_log(f"Đã đóng vị thế: {values[0]} {values[1]}")

    def refresh_positions(self):
        """Làm mới dữ liệu vị thế"""
        # Cập nhật giá mới và P/L cho các vị thế
        updated_positions = []
        
        for position in self.positions:
            symbol, pos_type, entry_price, _, size, _, time, sl, tp = position
            
            # Tạo giá mới ngẫu nhiên
            import random
            entry_price = float(entry_price)
            current_price = round(entry_price * (1 + random.uniform(-0.07, 0.07)), 2)
            
            if pos_type == 'LONG':
                pnl = round((current_price - entry_price) / entry_price * 100, 2)
            else:
                pnl = round((entry_price - current_price) / entry_price * 100, 2)
            
            updated_position = (
                symbol, pos_type, entry_price, current_price, 
                size, f"{pnl}%", time, sl, tp
            )
            updated_positions.append(updated_position)
        
        self.positions = updated_positions
        self.update_positions_data()
        self.add_log("Đã làm mới dữ liệu vị thế")

    def refresh_market_data(self):
        """Làm mới dữ liệu thị trường"""
        self.update_market_data()
        self.add_log("Đã làm mới dữ liệu thị trường")

    def refresh_logs(self):
        """Làm mới nhật ký"""
        self.add_log("Đã làm mới nhật ký")

    def clear_logs(self):
        """Xóa nhật ký"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.add_log("Đã xóa nhật ký")

    def update_options(self):
        """Cập nhật tùy chọn từ checkbox"""
        self.config["auto_trading"] = self.auto_trading_var.get()
        self.config["market_analysis"] = self.market_analysis_var.get()
        self.config["sltp_management"] = self.sltp_management_var.get()
        self.config["trailing_stop"] = self.trailing_stop_var.get()
        self.config["telegram_notifications"] = self.telegram_notifications_var.get()
        self.save_config()
        
        options = []
        if self.config["auto_trading"]:
            options.append("Giao dịch tự động")
        if self.config["market_analysis"]:
            options.append("Phân tích thị trường")
        if self.config["sltp_management"]:
            options.append("Quản lý SL/TP")
        if self.config["trailing_stop"]:
            options.append("Trailing Stop")
        if self.config["telegram_notifications"]:
            options.append("Thông báo Telegram")
        
        self.add_log(f"Đã cập nhật tùy chọn: {', '.join(options)}")

    def update_risk_level(self, event=None):
        """Cập nhật mức rủi ro"""
        risk_level = self.risk_level_var.get()
        self.add_log(f"Đã chọn mức rủi ro: {risk_level}%")
        
        # Cập nhật mức đòn bẩy tương ứng
        if risk_level == "10":
            self.leverage_var.set(1)
        elif risk_level == "15":
            self.leverage_var.set(2)
        elif risk_level == "20":
            self.leverage_var.set(5)
        elif risk_level == "30":
            self.leverage_var.set(10)
        
        self.update_leverage()

    def update_leverage(self, event=None):
        """Cập nhật giá trị đòn bẩy"""
        leverage = self.leverage_var.get()
        self.leverage_label.config(text=f"{leverage}x")
        self.config["max_leverage"] = leverage
        self.save_config()
        self.add_log(f"Đã cập nhật đòn bẩy: {leverage}x")

    def test_api_connection(self):
        """Kiểm tra kết nối API"""
        self.add_test_log("Đang kiểm tra kết nối với Binance API...")
        self.update_test_status("Kết nối API", "Đang kiểm tra")
        
        # Giả lập kiểm tra thành công
        time.sleep(1)
        self.add_test_log("✅ Kết nối API thành công!")
        self.update_test_status("Kết nối API", "Thành công", True)

    def test_market_data(self):
        """Kiểm tra lấy dữ liệu thị trường"""
        self.add_test_log("Đang kiểm tra lấy dữ liệu thị trường...")
        self.update_test_status("Dữ liệu thị trường", "Đang kiểm tra")
        
        # Giả lập kiểm tra thành công
        time.sleep(1.5)
        self.add_test_log("✅ Lấy dữ liệu thị trường thành công!")
        self.update_market_data()
        self.update_test_status("Dữ liệu thị trường", "Thành công", True)

    def test_telegram(self):
        """Kiểm tra thông báo Telegram"""
        self.add_test_log("Đang kiểm tra kết nối Telegram...")
        self.update_test_status("Thông báo Telegram", "Đang kiểm tra")
        
        # Giả lập kiểm tra thành công
        time.sleep(1.2)
        self.add_test_log("✅ Kết nối Telegram thành công!")
        self.add_test_log("📩 Đã gửi tin nhắn kiểm tra tới Telegram")
        self.update_test_status("Thông báo Telegram", "Thành công", True)

    def test_position_management(self):
        """Kiểm tra quản lý vị thế"""
        self.add_test_log("Đang kiểm tra chức năng quản lý vị thế...")
        self.update_test_status("Quản lý vị thế", "Đang kiểm tra")
        
        # Giả lập kiểm tra thành công
        time.sleep(1.8)
        self.add_test_log("✅ Kiểm tra mở vị thế thành công")
        self.add_test_log("✅ Kiểm tra cập nhật SL/TP thành công")
        self.add_test_log("✅ Kiểm tra đóng vị thế thành công")
        
        # Thêm vị thế mẫu để minh họa
        self.add_test_position()
        
        self.update_test_status("Quản lý vị thế", "Thành công", True)

    def test_technical_analysis(self):
        """Kiểm tra phân tích kỹ thuật"""
        self.add_test_log("Đang kiểm tra chức năng phân tích kỹ thuật...")
        self.update_test_status("Phân tích kỹ thuật", "Đang kiểm tra")
        
        # Giả lập kiểm tra thành công
        time.sleep(2)
        self.add_test_log("✅ Kiểm tra phân tích chỉ báo RSI thành công")
        self.add_test_log("✅ Kiểm tra phân tích chỉ báo MACD thành công")
        self.add_test_log("✅ Kiểm tra phân tích Bollinger Bands thành công")
        self.add_test_log("✅ Kiểm tra phân tích Volume Profile thành công")
        self.update_test_status("Phân tích kỹ thuật", "Thành công", True)

    def on_closing(self):
        """Xử lý sự kiện đóng cửa sổ"""
        if self.is_running:
            if messagebox.askokcancel("Xác nhận thoát", "Hệ thống đang chạy. Bạn có chắc chắn muốn thoát?"):
                self.stop_system()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    # Kiểm tra phiên bản Python
    if sys.version_info < (3, 8):
        print("ERROR: Yêu cầu Python 3.8 trở lên")
        sys.exit(1)
    
    # Khởi động giao diện
    print("Khởi động giao diện kiểm tra hệ thống giao dịch...")
    
    root = tk.Tk()
    app = TestGUI(root)
    
    # Hiển thị thông báo chào mừng
    messagebox.showinfo(
        "Chào mừng",
        "Chào mừng đến với Giao Diện Kiểm Tra!"
        "\n\nBạn có thể sử dụng giao diện này để kiểm tra các chức năng hệ thống."
    )
    
    root.mainloop()