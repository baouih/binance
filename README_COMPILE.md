# Hướng dẫn biên dịch thành file thực thi (EXE)

## Chuẩn bị

### 1. Cài đặt các gói cần thiết
Trước khi biên dịch, hãy đảm bảo bạn đã cài đặt tất cả các gói thư viện cần thiết:

```bash
pip install -r package_requirements.txt
```

### 2. Cấu trúc thư mục
Đảm bảo bạn có cấu trúc thư mục sau:

```
├── trading_system_gui.py      # File giao diện chính
├── run_gui.py                 # File khởi động
├── exe_build.py               # Script biên dịch
├── HƯỚNG_DẪN_SỬ_DỤNG.md      # Hướng dẫn sử dụng
├── version.json               # Thông tin phiên bản
├── account_config.json        # Cấu hình tài khoản
├── telegram_config.json       # Cấu hình telegram
├── configs/                   # Thư mục cấu hình
├── data/                      # Thư mục dữ liệu
└── update_packages/           # Thư mục cập nhật
    └── update_from_replit.py  # Script cập nhật
```

## Biên dịch

### Phương pháp 1: Sử dụng script tự động

1. Chạy file `exe_build.py`:
```bash
python exe_build.py
```

2. Quá trình biên dịch sẽ bắt đầu và tạo ra file thực thi trong thư mục `dist/`.

### Phương pháp 2: Biên dịch thủ công

1. Sử dụng PyInstaller trực tiếp:
```bash
pyinstaller --name=TradingSystem --onefile --windowed --icon=static/favicon.ico run_gui.py --add-data "HƯỚNG_DẪN_SỬ_DỤNG.md:." --add-data "account_config.json:." --add-data "telegram_config.json:." --add-data "configs:configs" --add-data "data:data" --add-data "update_packages:update_packages" --hidden-import pandas --hidden-import numpy --hidden-import binance --hidden-import ccxt --hidden-import matplotlib
```

## Sử dụng

1. Sau khi biên dịch, bạn sẽ tìm thấy file `TradingSystem.exe` trong thư mục `dist/`.
2. Sao chép file này vào một thư mục mới và chạy.
3. Khi khởi động lần đầu, hệ thống sẽ tạo các file cấu hình cần thiết.
4. Thiết lập API Key và các cài đặt cần thiết trong ứng dụng.

## Ghi chú

- Đảm bảo các file `.env` và `account_config.json` đã được thiết lập đúng trước khi biên dịch.
- Nếu bạn thay đổi mã nguồn, bạn cần biên dịch lại để áp dụng thay đổi.
- Đối với các cập nhật tương lai, bạn có thể sử dụng tính năng cập nhật tự động trong ứng dụng.

## Xử lý sự cố

### Lỗi thư viện thiếu
Nếu gặp lỗi về thư viện thiếu khi chạy file exe:

1. Đảm bảo đã cài đặt tất cả thư viện cần thiết:
```bash
pip install -r package_requirements.txt
```

2. Thêm các thư viện bị thiếu vào tham số `--hidden-import` khi biên dịch.

### Lỗi không tìm thấy file dữ liệu
Đảm bảo bạn đã thêm tất cả các thư mục và file cần thiết vào tham số `--add-data`.

### Lỗi khi chạy trên máy khác
Đảm bảo máy đích có phiên bản Windows tương thích (Windows 10/11).