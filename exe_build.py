import PyInstaller.__main__
import os
import shutil

# Danh sách các tệp và thư mục cần thêm vào gói
additional_files = [
    "account_config.json",
    "HƯỚNG_DẪN_SỬ_DỤNG.md",
    ".env",
    "telegram_config.json",
    "configs/",
    "data/"
]

# Danh sách module cần thiết
modules = [
    "pandas",
    "numpy",
    "requests",
    "json",
    "datetime",
    "logging",
    "threading",
    "time",
    "os",
    "sys",
    "subprocess",
    "binance",
    "ccxt",
    "matplotlib",
    "tabulate",
    "schedule",
    "pyinstaller",
    "webbrowser"
]

# Các tệp Python cần đóng gói
python_files = [
    "trading_system_gui.py",
    "auto_market_notifier.py",
    "auto_sltp_manager.py",
    "auto_trade.py",
    "position_trailing_stop.py",
    "market_analysis_system.py",
    "binance_api.py",
    "telegram_notifier.py",
    "advanced_telegram_notifier.py",
    "data_processor.py",
    "composite_indicator.py",
    "composite_trading_strategy.py",
    "market_regime_detector.py",
    "detailed_notifications.py",
    "update_packages/update_from_replit.py"
]

# Kiểm tra các tệp và thư mục tồn tại
for file in additional_files + python_files:
    if not os.path.exists(file):
        print(f"Cảnh báo: {file} không tồn tại, có thể gây lỗi khi đóng gói")

# Tạo thư mục dist nếu chưa tồn tại
if not os.path.exists("dist"):
    os.makedirs("dist")

# Tạo thư mục build nếu chưa tồn tại
if not os.path.exists("build"):
    os.makedirs("build")

# Đóng gói ứng dụng với PyInstaller
print("Bắt đầu đóng gói ứng dụng...")

PyInstaller.__main__.run([
    'trading_system_gui.py',               # tệp script chính
    '--name=TradingSystem',                # tên ứng dụng đã đóng gói
    '--onefile',                           # đóng gói thành một tệp duy nhất
    '--windowed',                          # không hiển thị console window
    '--icon=static/favicon.ico',           # biểu tượng (nếu có)
    '--add-data=HƯỚNG_DẪN_SỬ_DỤNG.md:.',  # thêm file hướng dẫn
    '--add-data=account_config.json:.',    # thêm file cấu hình tài khoản
    '--add-data=telegram_config.json:.',   # thêm file cấu hình telegram
    '--add-data=.env:.',                   # thêm file biến môi trường
    '--add-data=configs:configs',          # thêm thư mục configs
    '--add-data=data:data',                # thêm thư mục data
    '--add-data=update_packages:update_packages', # thêm thư mục cập nhật
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=binance',
    '--hidden-import=ccxt',
    '--hidden-import=matplotlib',
    '--hidden-import=tabulate',
    '--hidden-import=schedule',
])

print("Đã hoàn thành đóng gói ứng dụng!")
print("File thực thi được tạo tại: dist/TradingSystem.exe")

# Thông báo kết quả
print("\nHướng dẫn sử dụng:")
print("1. Chạy file TradingSystem.exe trong thư mục dist")
print("2. Thiết lập API Key trong phần Cài đặt API")
print("3. Nhấn nút Khởi động để bắt đầu hệ thống")

# Kiểm tra xem file đã được tạo thành công hay chưa
if os.path.exists("dist/TradingSystem.exe"):
    print("\nĐóng gói thành công!")
else:
    print("\nĐóng gói thất bại, vui lòng kiểm tra lại!")