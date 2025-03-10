# Hướng Dẫn Khởi Động Nhanh

Tài liệu này hướng dẫn cách cài đặt và chạy bot giao dịch một cách nhanh chóng.

## Nội Dung

1. [Cài Đặt Nhanh](#cài-đặt-nhanh)
2. [Chạy Bot](#chạy-bot)
3. [Chạy Chế Độ 24/7](#chạy-chế-độ-247)
4. [Quản Lý Mức Rủi Ro](#quản-lý-mức-rủi-ro)
5. [Xử Lý Sự Cố](#xử-lý-sự-cố)

## Cài Đặt Nhanh

### Windows

1. Cài đặt Python 3.9+ từ [python.org](https://www.python.org/downloads/)
   - **Quan trọng**: Tick chọn "Add Python to PATH" khi cài đặt

2. Click chuột phải vào file `install_and_run.bat` và chọn "Run as administrator"

3. Đợi quá trình cài đặt hoàn tất

### Linux/Mac

1. Cài đặt Python 3.9+ (nếu chưa có):
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv

   # macOS
   brew install python3
   ```

2. Mở Terminal và chạy:
   ```bash
   chmod +x install_and_run.sh
   ./install_and_run.sh
   ```

## Chạy Bot

### Sử Dụng Giao Diện Đồ Họa

- **Windows**: Click đúp vào file `install_and_run.bat`
- **Linux/Mac**: Mở Terminal và chạy `./install_and_run.sh`

Hoặc chạy trực tiếp từ dòng lệnh:
```bash
python bot_gui.py  # Windows
python3 bot_gui.py  # Linux/Mac
```

### Chạy Bot Bằng Dòng Lệnh

```bash
# Windows
python bot_startup.py --risk-level 20

# Linux/Mac
python3 bot_startup.py --risk-level 20
```

## Chạy Chế Độ 24/7

### Sử Dụng Script Tự Động

- **Windows**: Click đúp vào file `run_24_7_mode.bat`
- **Linux/Mac**: Mở Terminal và chạy:
  ```bash
  chmod +x run_24_7_mode.sh
  ./run_24_7_mode.sh
  ```

### Chạy Bằng Dòng Lệnh

```bash
# Windows
python auto_restart_guardian.py --risk-level 20

# Linux/Mac
python3 auto_restart_guardian.py --risk-level 20
```

## Quản Lý Mức Rủi Ro

Bot hỗ trợ 4 mức rủi ro: 10%, 15%, 20%, 30%

### Xem Cấu Hình Rủi Ro

```bash
# Windows
python risk_level_manager.py --show

# Linux/Mac
python3 risk_level_manager.py --show
```

### Thiết Lập Mức Rủi Ro

```bash
# Windows
python risk_level_manager.py --set-active 20

# Linux/Mac
python3 risk_level_manager.py --set-active 20
```

## Xử Lý Sự Cố

### Lỗi "No module named..."

Chạy script cài đặt thư viện:
```bash
# Windows
python setup_dependencies.py

# Linux/Mac
python3 setup_dependencies.py
```

### Bot Khởi Động Liên Tục

Kiểm tra file log trong thư mục `logs` để xác định nguyên nhân.

### Bot Không Kết Nối Được API

Kiểm tra file cấu hình `account_config.json` và cập nhật API key/secret.

---

Để biết thêm thông tin chi tiết, vui lòng xem:
- `README_24_7_MODE.md` - Hướng dẫn chi tiết về vận hành 24/7
- `README_EXECUTABLE.md` - Hướng dẫn tạo file thực thi
- `README_RISK_MANAGEMENT.md` - Thông tin về quản lý rủi ro