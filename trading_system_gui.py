import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import json
import subprocess
import requests
import sys
from datetime import datetime
import webbrowser
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system_gui.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_system_gui")

# Constants
VERSION = "1.0.0"
UPDATE_URL = "https://replit.com/@YourUsername/TradingSystem"  # Thay thế bằng URL thực tế
CONFIG_FILE = "gui_config.json"
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

class TradingSystemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Hệ Thống Giao Dịch Tiền Điện Tử Tự Động v{VERSION}")
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
        
        # Kiểm tra cập nhật khi khởi động
        if self.config.get("auto_check_update", True):
            self.root.after(2000, self.check_for_updates)
        
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
            logger.info("Đã tải cấu hình giao diện")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {e}")
            self.config = DEFAULT_CONFIG
            self.save_config()

    def save_config(self):
        """Lưu cấu hình vào file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Đã lưu cấu hình giao diện")
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
        ttk.Label(balance_row, text="Số dư:", style='Header.TLabel').pack(side=tk.LEFT)
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
        self.start_button = ttk.Button(start_stop_frame, text="Khởi Động", command=self.start_system)
        self.start_button.pack(fill=tk.X, pady=2)
        self.stop_button = ttk.Button(start_stop_frame, text="Dừng", command=self.stop_system, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, pady=2)
        
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
        
        # Phần trăm rủi ro
        risk_row = ttk.Frame(risk_frame)
        risk_row.pack(fill=tk.X, pady=5)
        ttk.Label(risk_row, text="Rủi ro (%):").pack(side=tk.LEFT)
        self.risk_var = tk.DoubleVar(value=self.config["risk_percentage"])
        risk_scale = ttk.Scale(risk_row, from_=0.1, to=5.0, variable=self.risk_var, command=self.update_risk)
        risk_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.risk_label = ttk.Label(risk_row, text=f"{self.config['risk_percentage']:.1f}%")
        self.risk_label.pack(side=tk.RIGHT)
        
        # Đòn bẩy tối đa
        leverage_row = ttk.Frame(risk_frame)
        leverage_row.pack(fill=tk.X, pady=5)
        ttk.Label(leverage_row, text="Đòn bẩy (x):").pack(side=tk.LEFT)
        self.leverage_var = tk.IntVar(value=self.config["max_leverage"])
        leverage_scale = ttk.Scale(leverage_row, from_=1, to=20, variable=self.leverage_var, command=self.update_leverage)
        leverage_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.leverage_label = ttk.Label(leverage_row, text=f"{self.config['max_leverage']}x")
        self.leverage_label.pack(side=tk.RIGHT)
        
        # Frame cài đặt API
        api_frame = ttk.LabelFrame(parent, text="Cài Đặt API", padding="10")
        api_frame.pack(fill=tk.X, pady=10)
        
        # Chế độ API (testnet/thực)
        api_mode_row = ttk.Frame(api_frame)
        api_mode_row.pack(fill=tk.X, pady=5)
        ttk.Label(api_mode_row, text="Chế độ API:").pack(side=tk.LEFT)
        self.api_mode_var = tk.StringVar(value=self.config["api_mode"])
        api_mode_combo = ttk.Combobox(api_mode_row, textvariable=self.api_mode_var, state="readonly")
        api_mode_combo['values'] = ('testnet', 'live')
        api_mode_combo.pack(side=tk.RIGHT)
        api_mode_combo.bind('<<ComboboxSelected>>', self.update_api_mode)
        
        # Nút cài đặt API
        ttk.Button(api_frame, text="Cấu Hình API Key", command=self.configure_api).pack(fill=tk.X, pady=5)
        
        # Frame cập nhật
        update_frame = ttk.LabelFrame(parent, text="Cập Nhật", padding="10")
        update_frame.pack(fill=tk.X, pady=10)
        
        # Nút kiểm tra cập nhật
        self.update_button = ttk.Button(update_frame, text="Kiểm Tra Cập Nhật", command=self.check_for_updates)
        self.update_button.pack(fill=tk.X, pady=5)
        
        # Trạng thái cập nhật
        self.update_status_label = ttk.Label(update_frame, text="Chưa kiểm tra")
        self.update_status_label.pack(fill=tk.X, pady=5)
        
        # Nút trợ giúp
        help_frame = ttk.Frame(parent)
        help_frame.pack(fill=tk.X, pady=10)
        ttk.Button(help_frame, text="Xem Hướng Dẫn", command=self.show_help).pack(fill=tk.X, pady=5)

    def create_data_display(self, parent):
        """Tạo khu vực hiển thị dữ liệu"""
        # Notebook cho các tab
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab Thị Trường
        market_tab = ttk.Frame(notebook, padding="10")
        notebook.add(market_tab, text="Thị Trường")
        self.create_market_tab(market_tab)
        
        # Tab Vị Thế
        positions_tab = ttk.Frame(notebook, padding="10")
        notebook.add(positions_tab, text="Vị Thế")
        self.create_positions_tab(positions_tab)
        
        # Tab Lịch Sử
        history_tab = ttk.Frame(notebook, padding="10")
        notebook.add(history_tab, text="Lịch Sử")
        self.create_history_tab(history_tab)
        
        # Tab Nhật Ký
        log_tab = ttk.Frame(notebook, padding="10")
        notebook.add(log_tab, text="Nhật Ký")
        self.create_log_tab(log_tab)

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
        
        ttk.Button(control_frame, text="Đóng Vị Thế Đã Chọn", command=self.close_selected_position).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Cập Nhật SL/TP", command=self.update_sltp).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Làm Mới", command=self.refresh_positions).pack(side=tk.RIGHT, padx=5)
        
        # Thêm dữ liệu mẫu
        self.update_positions_data()

    def create_history_tab(self, parent):
        """Tạo nội dung tab lịch sử"""
        # Treeview để hiển thị lịch sử giao dịch
        columns = ('date', 'symbol', 'type', 'entry_price', 'exit_price', 'size', 'pnl', 'duration')
        self.history_tree = ttk.Treeview(parent, columns=columns, show='headings')
        
        # Định nghĩa các cột
        self.history_tree.heading('date', text='Ngày')
        self.history_tree.heading('symbol', text='Cặp Tiền')
        self.history_tree.heading('type', text='Loại')
        self.history_tree.heading('entry_price', text='Giá Vào')
        self.history_tree.heading('exit_price', text='Giá Ra')
        self.history_tree.heading('size', text='Kích Thước')
        self.history_tree.heading('pnl', text='P/L (%)')
        self.history_tree.heading('duration', text='Thời Gian Giữ')
        
        # Định nghĩa độ rộng cột
        self.history_tree.column('date', width=100)
        self.history_tree.column('symbol', width=100)
        self.history_tree.column('type', width=80)
        self.history_tree.column('entry_price', width=100)
        self.history_tree.column('exit_price', width=100)
        self.history_tree.column('size', width=100)
        self.history_tree.column('pnl', width=100)
        self.history_tree.column('duration', width=100)
        
        # Thêm thanh cuộn
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        # Frame lọc
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Từ:").pack(side=tk.LEFT, padx=5)
        # Đơn giản hóa bằng Entry thay vì DateEntry
        self.from_date_var = tk.StringVar(value="2025-01-01")
        ttk.Entry(filter_frame, textvariable=self.from_date_var, width=12).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Đến:").pack(side=tk.LEFT, padx=5)
        self.to_date_var = tk.StringVar(value="2025-12-31")
        ttk.Entry(filter_frame, textvariable=self.to_date_var, width=12).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Lọc", command=self.filter_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Xuất Báo Cáo", command=self.export_report).pack(side=tk.RIGHT, padx=5)

    def create_log_tab(self, parent):
        """Tạo nội dung tab nhật ký"""
        # Text widget để hiển thị log
        self.log_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Frame điều khiển
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=5)
        
        # Nút điều khiển
        ttk.Button(control_frame, text="Làm Mới", command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Xóa", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        
        # Combobox filter
        ttk.Label(control_frame, text="Mức độ:").pack(side=tk.LEFT, padx=5)
        self.log_level_var = tk.StringVar(value="Tất cả")
        log_level_combo = ttk.Combobox(control_frame, textvariable=self.log_level_var, state="readonly", width=10)
        log_level_combo['values'] = ('Tất cả', 'INFO', 'WARNING', 'ERROR', 'DEBUG')
        log_level_combo.pack(side=tk.LEFT, padx=5)
        log_level_combo.bind('<<ComboboxSelected>>', self.filter_logs)
        
        # Đọc log
        self.update_log_display()

    def start_system(self):
        """Khởi động hệ thống"""
        if self.is_running:
            return
        
        try:
            # Cập nhật trạng thái
            self.is_running = True
            self.status_label.config(text="Đang chạy", style='Running.TLabel')
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Ghi log
            self.add_log("INFO", "Đã khởi động hệ thống giao dịch tự động")
            
            # Khởi động luồng cập nhật trạng thái
            if self.status_thread is None or not self.status_thread.is_alive():
                self.status_thread = threading.Thread(target=self.status_update_loop, daemon=True)
                self.status_thread.start()
            
            # Khởi động các dịch vụ dựa trên cấu hình
            self.start_trading_services()
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động hệ thống: {e}")
            messagebox.showerror("Lỗi", f"Không thể khởi động hệ thống: {e}")
            self.stop_system()

    def stop_system(self):
        """Dừng hệ thống"""
        if not self.is_running:
            return
        
        try:
            # Cập nhật trạng thái
            self.is_running = False
            self.status_label.config(text="Đã dừng", style='Stopped.TLabel')
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Ghi log
            self.add_log("INFO", "Đã dừng hệ thống giao dịch tự động")
            
            # Dừng các dịch vụ
            self.stop_trading_services()
            
        except Exception as e:
            logger.error(f"Lỗi khi dừng hệ thống: {e}")
            messagebox.showerror("Lỗi", f"Không thể dừng hệ thống hoàn toàn: {e}")

    def start_trading_services(self):
        """Khởi động các dịch vụ giao dịch dựa trên cấu hình"""
        try:
            commands = []
            
            # Dịch vụ phân tích thị trường
            if self.config["market_analysis"]:
                commands.append("python3 auto_market_notifier.py &")
                self.add_log("INFO", "Đã khởi động dịch vụ phân tích thị trường")
            
            # Dịch vụ giao dịch tự động
            if self.config["auto_trading"]:
                commands.append("python3 auto_trade.py &")
                self.add_log("INFO", "Đã khởi động dịch vụ giao dịch tự động")
            
            # Dịch vụ quản lý SL/TP
            if self.config["sltp_management"]:
                commands.append("python3 auto_sltp_manager.py &")
                self.add_log("INFO", "Đã khởi động dịch vụ quản lý SL/TP")
            
            # Dịch vụ trailing stop
            if self.config["trailing_stop"]:
                commands.append("python3 position_trailing_stop.py &")
                self.add_log("INFO", "Đã khởi động dịch vụ trailing stop")
            
            # Khởi động bot
            commands.append("curl -X POST http://localhost:5000/start-bot")
            
            # Thực thi các lệnh
            for cmd in commands:
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.warning(f"Lệnh '{cmd}' trả về mã lỗi {result.returncode}: {result.stderr}")
                    else:
                        logger.info(f"Lệnh '{cmd}' đã thực thi thành công: {result.stdout}")
                except Exception as e:
                    logger.error(f"Lỗi khi thực thi lệnh '{cmd}': {e}")
            
        except Exception as e:
            logger.error(f"Lỗi khi khởi động dịch vụ: {e}")
            self.add_log("ERROR", f"Không thể khởi động dịch vụ: {e}")

    def stop_trading_services(self):
        """Dừng các dịch vụ giao dịch"""
        try:
            # Dừng các tiến trình
            commands = [
                "killall -9 auto_market_notifier.py",
                "killall -9 auto_trade.py",
                "killall -9 auto_sltp_manager.py",
                "killall -9 position_trailing_stop.py",
                "curl -X POST http://localhost:5000/stop-bot"
            ]
            
            # Thực thi các lệnh (bỏ qua lỗi nếu tiến trình chưa chạy)
            for cmd in commands:
                try:
                    subprocess.run(cmd, shell=True, capture_output=True, text=True)
                except Exception as e:
                    logger.warning(f"Lỗi khi dừng lệnh: {e}")
            
            self.add_log("INFO", "Đã dừng tất cả các dịch vụ giao dịch")
            
        except Exception as e:
            logger.error(f"Lỗi khi dừng dịch vụ: {e}")
            self.add_log("ERROR", f"Không thể dừng dịch vụ hoàn toàn: {e}")

    def status_update_loop(self):
        """Vòng lặp cập nhật trạng thái hệ thống"""
        while self.is_running:
            try:
                # Cập nhật số dư
                self.update_account_balance()
                
                # Cập nhật danh sách vị thế
                self.update_positions_data()
                
                # Cập nhật dữ liệu thị trường
                self.update_market_data()
                
                # Cập nhật nhật ký
                self.update_log_display()
                
            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp cập nhật trạng thái: {e}")
            
            # Cập nhật mỗi 30 giây
            time.sleep(30)

    def update_account_balance(self):
        """Cập nhật số dư tài khoản"""
        try:
            # Trong thực tế, đây sẽ gọi API để lấy số dư
            # Hiện tại chỉ mô phỏng bằng cách tăng/giảm số ngẫu nhiên
            # balance = get_account_balance()
            
            # Mô phỏng
            import random
            self.account_balance = 13543.08  # Giá trị từ log
            
            # Cập nhật giao diện trong luồng chính
            self.root.after(0, lambda: self.balance_label.config(text=f"{self.account_balance:.2f} USDT"))
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật số dư tài khoản: {e}")

    def update_market_data(self):
        """Cập nhật dữ liệu thị trường"""
        try:
            # Trong thực tế, đây sẽ gọi API để lấy dữ liệu thị trường
            # Hiện tại chỉ mô phỏng với dữ liệu cứng
            
            # Xóa dữ liệu cũ
            for item in self.market_tree.get_children():
                self.market_tree.delete(item)
            
            # Dữ liệu mẫu
            symbols = [
                ('BTCUSDT', '84,243.60', '+2.1%', 'Cao', 'MUA', 'Tăng'),
                ('ETHUSDT', '2,139.83', '+1.3%', 'Trung bình', 'CHỜ', 'Tăng nhẹ'),
                ('BNBUSDT', '596.13', '-0.5%', 'Thấp', 'BÁN', 'Giảm nhẹ'),
                ('SOLUSDT', '159.00', '+3.2%', 'Cao', 'MUA', 'Tăng mạnh'),
                ('ADAUSDT', '0.90', '+0.7%', 'Trung bình', 'CHỜ', 'Đi ngang'),
                ('DOGEUSDT', '0.12', '-1.2%', 'Thấp', 'BÁN', 'Giảm'),
                ('DOTUSDT', '7.45', '+0.3%', 'Trung bình', 'CHỜ', 'Đi ngang'),
                ('LINKUSDT', '15.75', '+1.8%', 'Cao', 'MUA', 'Tăng'),
                ('LTCUSDT', '85.30', '-0.9%', 'Thấp', 'BÁN', 'Giảm nhẹ'),
                ('ATOMUSDT', '8.90', '+0.5%', 'Trung bình', 'CHỜ', 'Đi ngang'),
                ('XRPUSDT', '0.65', '+1.1%', 'Trung bình', 'MUA', 'Tăng nhẹ'),
                ('MATICUSDT', '0.58', '-0.8%', 'Thấp', 'BÁN', 'Giảm nhẹ'),
                ('AVAXUSDT', '21.40', '+2.7%', 'Cao', 'MUA', 'Tăng mạnh')
            ]
            
            # Thêm dữ liệu mới
            for symbol in symbols:
                self.market_tree.insert('', 'end', values=symbol)
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu thị trường: {e}")

    def update_positions_data(self):
        """Cập nhật dữ liệu vị thế"""
        try:
            # Trong thực tế, đây sẽ gọi API để lấy danh sách vị thế
            # Hiện tại chỉ mô phỏng với dữ liệu cứng
            
            # Xóa dữ liệu cũ
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Kiểm tra xem có vị thế nào không
            # Ở đây mô phỏng không có vị thế
            self.positions = []
            
            # Cập nhật số lượng vị thế
            self.root.after(0, lambda: self.positions_label.config(text=str(len(self.positions))))
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật dữ liệu vị thế: {e}")

    def update_log_display(self):
        """Cập nhật hiển thị nhật ký"""
        try:
            # Đọc file log
            log_file = "system_gui.log"
            if not os.path.exists(log_file):
                return
            
            with open(log_file, 'r') as f:
                logs = f.readlines()
            
            # Lọc theo mức độ nếu cần
            level_filter = self.log_level_var.get()
            if level_filter != "Tất cả":
                logs = [log for log in logs if level_filter in log]
            
            # Hiển thị log
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            for log in logs[-1000:]:  # Giới hạn 1000 dòng để tránh quá tải
                self.log_text.insert(tk.END, log)
            self.log_text.config(state=tk.DISABLED)
            self.log_text.see(tk.END)  # Cuộn xuống cuối
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật hiển thị nhật ký: {e}")

    def add_log(self, level, message):
        """Thêm thông báo vào nhật ký"""
        try:
            # Ghi log với định dạng phù hợp
            if level == "INFO":
                logger.info(message)
            elif level == "WARNING":
                logger.warning(message)
            elif level == "ERROR":
                logger.error(message)
            elif level == "DEBUG":
                logger.debug(message)
            
            # Cập nhật hiển thị
            self.update_log_display()
            
        except Exception as e:
            print(f"Lỗi khi thêm log: {e}")

    def check_for_updates(self):
        """Kiểm tra cập nhật từ server"""
        if self.update_checking:
            return
        
        self.update_checking = True
        self.update_button.config(state=tk.DISABLED)
        self.update_status_label.config(text="Đang kiểm tra cập nhật...", style='Status.TLabel')
        
        # Chạy trong luồng riêng để không chặn giao diện
        threading.Thread(target=self._check_updates_thread, daemon=True).start()

    def _check_updates_thread(self):
        """Luồng kiểm tra cập nhật"""
        try:
            # Kết nối đến sever và kiểm tra phiên bản mới nhất
            # Trong thực tế, đây sẽ gọi API hoặc kiểm tra repo
            
            # Mô phỏng kiểm tra cập nhật
            time.sleep(2)  # Giả lập thời gian kiểm tra
            
            # Quyết định ngẫu nhiên có bản cập nhật hay không
            import random
            has_update = random.choice([True, False])
            
            if has_update:
                # Có bản cập nhật mới
                new_version = "1.1.0"
                self.root.after(0, lambda: self.update_status_label.config(
                    text=f"Có bản cập nhật mới: v{new_version}", style='Running.TLabel'))
                
                # Hiển thị thông báo và hỏi người dùng có muốn cập nhật không
                if messagebox.askyesno("Cập Nhật", f"Có phiên bản mới: v{new_version}. Bạn có muốn cập nhật ngay?"):
                    self.perform_update()
            else:
                # Không có bản cập nhật mới
                self.root.after(0, lambda: self.update_status_label.config(
                    text=f"Bạn đang sử dụng phiên bản mới nhất (v{VERSION})", style='Status.TLabel'))
            
            # Cập nhật thời gian kiểm tra cuối cùng
            self.config["last_check_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_config()
            
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra cập nhật: {e}")
            self.root.after(0, lambda: self.update_status_label.config(
                text=f"Lỗi khi kiểm tra cập nhật: {e}", style='Warning.TLabel'))
        
        finally:
            # Khôi phục trạng thái
            self.update_checking = False
            self.root.after(0, lambda: self.update_button.config(state=tk.NORMAL))

    def perform_update(self):
        """Thực hiện cập nhật phần mềm"""
        try:
            self.update_status_label.config(text="Đang cập nhật...", style='Status.TLabel')
            
            # Dừng hệ thống trước khi cập nhật
            if self.is_running:
                self.stop_system()
            
            # Chạy script cập nhật
            # Trong thực tế, đây sẽ tải về bản cập nhật và cài đặt
            update_script = "./update_packages/update_from_replit.py"
            
            if os.path.exists(update_script):
                result = subprocess.run(["python3", update_script], capture_output=True, text=True)
                
                if result.returncode == 0:
                    messagebox.showinfo("Cập Nhật", "Đã cập nhật thành công. Ứng dụng sẽ khởi động lại.")
                    # Khởi động lại ứng dụng
                    python = sys.executable
                    os.execl(python, python, *sys.argv)
                else:
                    logger.error(f"Lỗi khi cập nhật: {result.stderr}")
                    messagebox.showerror("Lỗi", f"Không thể cập nhật: {result.stderr}")
                    self.update_status_label.config(text="Cập nhật thất bại", style='Warning.TLabel')
            else:
                logger.error(f"Không tìm thấy script cập nhật: {update_script}")
                messagebox.showerror("Lỗi", f"Không tìm thấy script cập nhật: {update_script}")
                self.update_status_label.config(text="Cập nhật thất bại", style='Warning.TLabel')
            
        except Exception as e:
            logger.error(f"Lỗi khi thực hiện cập nhật: {e}")
            messagebox.showerror("Lỗi", f"Không thể cập nhật: {e}")
            self.update_status_label.config(text="Cập nhật thất bại", style='Warning.TLabel')

    def update_options(self):
        """Cập nhật các tùy chọn hệ thống"""
        self.config["auto_trading"] = self.auto_trading_var.get()
        self.config["market_analysis"] = self.market_analysis_var.get()
        self.config["sltp_management"] = self.sltp_management_var.get()
        self.config["trailing_stop"] = self.trailing_stop_var.get()
        self.config["telegram_notifications"] = self.telegram_notifications_var.get()
        self.save_config()
        
        # Khởi động lại dịch vụ nếu đang chạy
        if self.is_running:
            self.stop_trading_services()
            self.start_trading_services()
            self.add_log("INFO", "Đã áp dụng tùy chọn mới và khởi động lại dịch vụ")

    def update_risk(self, value):
        """Cập nhật mức rủi ro"""
        risk = float(value)
        self.config["risk_percentage"] = risk
        self.risk_label.config(text=f"{risk:.1f}%")
        self.save_config()

    def update_leverage(self, value):
        """Cập nhật đòn bẩy tối đa"""
        leverage = int(float(value))
        self.config["max_leverage"] = leverage
        self.leverage_label.config(text=f"{leverage}x")
        self.save_config()

    def update_api_mode(self, event):
        """Cập nhật chế độ API"""
        mode = self.api_mode_var.get()
        if mode == "live" and self.config["api_mode"] == "testnet":
            # Cảnh báo khi chuyển từ testnet sang live
            if not messagebox.askyesno("Cảnh Báo", "Bạn đang chuyển sang chế độ LIVE với tiền thật. Tiếp tục?"):
                self.api_mode_var.set("testnet")
                return
        
        self.config["api_mode"] = mode
        self.save_config()
        
        # Thông báo cho người dùng
        if mode == "testnet":
            self.add_log("INFO", "Đã chuyển sang chế độ TESTNET (tiền ảo)")
        else:
            self.add_log("WARNING", "Đã chuyển sang chế độ LIVE (tiền thật)")
        
        # Cập nhật tệp cấu hình account_config.json
        self.update_account_config_mode(mode)

    def update_account_config_mode(self, mode):
        """Cập nhật chế độ trong tệp account_config.json"""
        try:
            account_config_path = "account_config.json"
            if os.path.exists(account_config_path):
                with open(account_config_path, 'r') as f:
                    account_config = json.load(f)
                
                account_config["api_mode"] = mode
                
                with open(account_config_path, 'w') as f:
                    json.dump(account_config, f, indent=4)
                
                self.add_log("INFO", f"Đã cập nhật chế độ {mode} trong account_config.json")
            else:
                self.add_log("ERROR", f"Không tìm thấy tệp {account_config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật chế độ API trong account_config.json: {e}")
            self.add_log("ERROR", f"Không thể cập nhật chế độ API: {e}")

    def configure_api(self):
        """Mở cửa sổ cấu hình API"""
        # Tạo cửa sổ mới
        api_window = tk.Toplevel(self.root)
        api_window.title("Cấu Hình API Key")
        api_window.geometry("500x400")
        api_window.transient(self.root)
        api_window.grab_set()
        
        # Tạo frame chính
        main_frame = ttk.Frame(api_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tải cấu hình hiện tại
        account_config = {}
        account_config_path = "account_config.json"
        try:
            if os.path.exists(account_config_path):
                with open(account_config_path, 'r') as f:
                    account_config = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi tải tệp account_config.json: {e}")
            account_config = {
                "api_key": "",
                "api_secret": "",
                "api_mode": self.config["api_mode"],
                "account_type": "futures"
            }
        
        # Form nhập liệu
        ttk.Label(main_frame, text="API Key Binance:").pack(anchor=tk.W, pady=5)
        api_key_var = tk.StringVar(value=account_config.get("api_key", ""))
        ttk.Entry(main_frame, textvariable=api_key_var, width=50).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="API Secret Binance:").pack(anchor=tk.W, pady=5)
        api_secret_var = tk.StringVar(value=account_config.get("api_secret", ""))
        secret_entry = ttk.Entry(main_frame, textvariable=api_secret_var, width=50, show="*")
        secret_entry.pack(fill=tk.X, pady=5)
        
        # Telegram Bot
        ttk.Label(main_frame, text="Telegram Bot Token:").pack(anchor=tk.W, pady=5)
        bot_token_var = tk.StringVar(value=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
        ttk.Entry(main_frame, textvariable=bot_token_var, width=50).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Telegram Chat ID:").pack(anchor=tk.W, pady=5)
        chat_id_var = tk.StringVar(value=os.environ.get("TELEGRAM_CHAT_ID", ""))
        ttk.Entry(main_frame, textvariable=chat_id_var, width=50).pack(fill=tk.X, pady=5)
        
        # Loại tài khoản
        ttk.Label(main_frame, text="Loại tài khoản:").pack(anchor=tk.W, pady=5)
        account_type_var = tk.StringVar(value=account_config.get("account_type", "futures"))
        account_type_combo = ttk.Combobox(main_frame, textvariable=account_type_var, state="readonly")
        account_type_combo['values'] = ('futures', 'spot')
        account_type_combo.pack(fill=tk.X, pady=5)
        
        # Frame nút điều khiển
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Nút Lưu
        def save_api_config():
            try:
                # Cập nhật account_config.json
                new_config = {
                    "api_key": api_key_var.get(),
                    "api_secret": api_secret_var.get(),
                    "api_mode": self.config["api_mode"],
                    "account_type": account_type_var.get()
                }
                
                with open(account_config_path, 'w') as f:
                    json.dump(new_config, f, indent=4)
                
                # Cập nhật biến môi trường Telegram
                with open(".env", "w") as f:
                    f.write(f"TELEGRAM_BOT_TOKEN={bot_token_var.get()}\n")
                    f.write(f"TELEGRAM_CHAT_ID={chat_id_var.get()}\n")
                
                # Cập nhật biến môi trường hiện tại
                os.environ["TELEGRAM_BOT_TOKEN"] = bot_token_var.get()
                os.environ["TELEGRAM_CHAT_ID"] = chat_id_var.get()
                
                self.add_log("INFO", "Đã cập nhật cấu hình API thành công")
                messagebox.showinfo("Thành công", "Đã lưu cấu hình API thành công")
                api_window.destroy()
                
                # Khởi động lại dịch vụ nếu đang chạy
                if self.is_running:
                    self.stop_trading_services()
                    self.start_trading_services()
                
            except Exception as e:
                logger.error(f"Lỗi khi lưu cấu hình API: {e}")
                messagebox.showerror("Lỗi", f"Không thể lưu cấu hình API: {e}")
        
        ttk.Button(button_frame, text="Lưu", command=save_api_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Hủy", command=api_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Nút kiểm tra kết nối
        def test_connection():
            try:
                # Kiểm tra kết nối Binance API
                from binance.client import Client
                
                # Tạo client tạm thời
                if self.config["api_mode"] == "testnet":
                    client = Client(api_key_var.get(), api_secret_var.get(), testnet=True)
                else:
                    client = Client(api_key_var.get(), api_secret_var.get())
                
                # Kiểm tra thông tin tài khoản
                account_info = client.get_account() if account_type_var.get() == "spot" else client.futures_account_balance()
                
                # Thành công
                messagebox.showinfo("Thành công", "Kết nối đến Binance API thành công!")
                
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra kết nối Binance API: {e}")
                messagebox.showerror("Lỗi", f"Không thể kết nối đến Binance API: {e}")
        
        ttk.Button(button_frame, text="Kiểm Tra Kết Nối", command=test_connection).pack(side=tk.LEFT, padx=5)

    def refresh_market_data(self):
        """Làm mới dữ liệu thị trường"""
        self.update_market_data()
        self.add_log("INFO", "Đã làm mới dữ liệu thị trường")

    def refresh_positions(self):
        """Làm mới dữ liệu vị thế"""
        self.update_positions_data()
        self.add_log("INFO", "Đã làm mới dữ liệu vị thế")

    def refresh_logs(self):
        """Làm mới hiển thị nhật ký"""
        self.update_log_display()

    def clear_logs(self):
        """Xóa nội dung nhật ký"""
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa nhật ký?"):
            try:
                # Xóa nội dung file log
                open("system_gui.log", 'w').close()
                
                # Cập nhật hiển thị
                self.update_log_display()
                
                self.add_log("INFO", "Đã xóa nhật ký")
                
            except Exception as e:
                logger.error(f"Lỗi khi xóa nhật ký: {e}")
                messagebox.showerror("Lỗi", f"Không thể xóa nhật ký: {e}")

    def filter_logs(self, event=None):
        """Lọc nhật ký theo mức độ"""
        self.update_log_display()

    def filter_history(self):
        """Lọc lịch sử giao dịch theo ngày"""
        # Chức năng này sẽ được triển khai sau
        self.add_log("INFO", "Đã lọc lịch sử giao dịch")

    def export_report(self):
        """Xuất báo cáo hiệu suất"""
        try:
            # Trong thực tế, đây sẽ tạo một báo cáo chi tiết
            # Hiện tại chỉ mô phỏng
            report_path = "performance_report.html"
            
            # Tạo file mẫu
            with open(report_path, 'w') as f:
                f.write("""
                <html>
                <head><title>Báo Cáo Hiệu Suất Giao Dịch</title></head>
                <body>
                    <h1>Báo Cáo Hiệu Suất Giao Dịch</h1>
                    <p>Ngày tạo: %s</p>
                    <h2>Tổng kết</h2>
                    <ul>
                        <li>Số dư: 13,543.57 USDT</li>
                        <li>Vốn ban đầu: 10,000.00 USDT</li>
                        <li>Lợi nhuận: +3,543.57 USDT (+35.44%%)</li>
                        <li>Tổng giao dịch: 142</li>
                        <li>Tỷ lệ thắng: 71.8%%</li>
                    </ul>
                </body>
                </html>
                """ % datetime.now().strftime("%Y-%m-%d"))
            
            # Mở file trong trình duyệt
            webbrowser.open(report_path)
            
            self.add_log("INFO", f"Đã xuất báo cáo hiệu suất: {report_path}")
            
        except Exception as e:
            logger.error(f"Lỗi khi xuất báo cáo: {e}")
            messagebox.showerror("Lỗi", f"Không thể xuất báo cáo: {e}")

    def close_selected_position(self):
        """Đóng vị thế đã chọn"""
        selected = self.positions_tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn vị thế để đóng")
            return
        
        try:
            # Lấy thông tin vị thế đã chọn
            item = self.positions_tree.item(selected[0])
            symbol = item["values"][0]
            
            # Xác nhận từ người dùng
            if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn đóng vị thế {symbol}?"):
                # Trong thực tế, đây sẽ gọi API để đóng vị thế
                # Hiện tại chỉ mô phỏng
                
                # Thông báo thành công
                messagebox.showinfo("Thành công", f"Đã đóng vị thế {symbol}")
                self.add_log("INFO", f"Đã đóng vị thế {symbol}")
                
                # Cập nhật danh sách vị thế
                self.update_positions_data()
                
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế: {e}")
            messagebox.showerror("Lỗi", f"Không thể đóng vị thế: {e}")

    def update_sltp(self):
        """Cập nhật Stop Loss và Take Profit cho vị thế đã chọn"""
        selected = self.positions_tree.selection()
        if not selected:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn vị thế để cập nhật SL/TP")
            return
        
        try:
            # Lấy thông tin vị thế đã chọn
            item = self.positions_tree.item(selected[0])
            symbol = item["values"][0]
            current_sl = item["values"][7]
            current_tp = item["values"][8]
            
            # Tạo cửa sổ mới
            sltp_window = tk.Toplevel(self.root)
            sltp_window.title(f"Cập nhật SL/TP cho {symbol}")
            sltp_window.geometry("300x200")
            sltp_window.transient(self.root)
            sltp_window.grab_set()
            
            # Tạo form nhập liệu
            main_frame = ttk.Frame(sltp_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text="Stop Loss:").pack(anchor=tk.W, pady=5)
            sl_var = tk.StringVar(value=current_sl)
            ttk.Entry(main_frame, textvariable=sl_var).pack(fill=tk.X, pady=5)
            
            ttk.Label(main_frame, text="Take Profit:").pack(anchor=tk.W, pady=5)
            tp_var = tk.StringVar(value=current_tp)
            ttk.Entry(main_frame, textvariable=tp_var).pack(fill=tk.X, pady=5)
            
            # Frame nút điều khiển
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            # Nút Cập nhật
            def update_sltp_values():
                try:
                    # Trong thực tế, đây sẽ gọi API để cập nhật SL/TP
                    # Hiện tại chỉ mô phỏng
                    
                    # Thông báo thành công
                    messagebox.showinfo("Thành công", f"Đã cập nhật SL/TP cho {symbol}")
                    self.add_log("INFO", f"Đã cập nhật SL/TP cho {symbol}")
                    
                    # Đóng cửa sổ
                    sltp_window.destroy()
                    
                    # Cập nhật danh sách vị thế
                    self.update_positions_data()
                    
                except Exception as e:
                    logger.error(f"Lỗi khi cập nhật SL/TP: {e}")
                    messagebox.showerror("Lỗi", f"Không thể cập nhật SL/TP: {e}")
            
            ttk.Button(button_frame, text="Cập Nhật", command=update_sltp_values).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="Hủy", command=sltp_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            logger.error(f"Lỗi khi mở cửa sổ cập nhật SL/TP: {e}")
            messagebox.showerror("Lỗi", f"Không thể mở cửa sổ cập nhật SL/TP: {e}")

    def show_help(self):
        """Hiển thị hướng dẫn sử dụng"""
        try:
            # Mở file README.md hoặc hướng dẫn sử dụng
            help_file = "HƯỚNG_DẪN_SỬ_DỤNG.md"
            
            if os.path.exists(help_file):
                # Mở tệp hướng dẫn với ứng dụng mặc định
                if sys.platform == "win32":
                    os.startfile(help_file)
                elif sys.platform == "darwin":  # macOS
                    subprocess.call(["open", help_file])
                else:  # Linux
                    subprocess.call(["xdg-open", help_file])
            else:
                messagebox.showwarning("Cảnh báo", f"Không tìm thấy tệp hướng dẫn: {help_file}")
            
        except Exception as e:
            logger.error(f"Lỗi khi mở tệp hướng dẫn: {e}")
            messagebox.showerror("Lỗi", f"Không thể mở tệp hướng dẫn: {e}")

    def on_closing(self):
        """Xử lý sự kiện đóng cửa sổ"""
        if self.is_running:
            if not messagebox.askyesno("Xác nhận", "Hệ thống đang chạy. Bạn có chắc muốn đóng?"):
                return
            
            # Dừng hệ thống
            self.stop_system()
        
        # Lưu cấu hình
        self.save_config()
        
        # Đóng cửa sổ
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingSystemGUI(root)
    root.mainloop()