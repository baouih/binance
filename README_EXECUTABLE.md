# Hướng Dẫn Tạo File Thực Thi (Executable)

Tài liệu này hướng dẫn cách tạo file thực thi (.exe trên Windows hoặc file binary trên Linux/macOS) để chạy bot giao dịch mà không cần cài đặt Python hoặc các thư viện phụ thuộc.

## Mục Lục

1. [Yêu Cầu Trước Khi Bắt Đầu](#yêu-cầu-trước-khi-bắt-đầu)
2. [Tạo File Thực Thi](#tạo-file-thực-thi)
3. [Tùy Chọn Biên Dịch](#tùy-chọn-biên-dịch)
4. [Cấu Trúc Thư Mục Sau Khi Biên Dịch](#cấu-trúc-thư-mục-sau-khi-biên-dịch)
5. [Chạy File Thực Thi](#chạy-file-thực-thi)
6. [Xử Lý Sự Cố](#xử-lý-sự-cố)
7. [Gói Phân Phối](#gói-phân-phối)

## Yêu Cầu Trước Khi Bắt Đầu

Để tạo file thực thi, bạn cần:

- Python 3.9+ đã cài đặt
- Tất cả thư viện phụ thuộc đã được cài đặt:
  ```bash
  pip install -r requirements.txt
  ```
- PyInstaller (công cụ biên dịch):
  ```bash
  pip install pyinstaller
  ```
- Hệ thống gốc tương tự với hệ thống đích (ví dụ: biên dịch trên Windows cho Windows)

## Tạo File Thực Thi

### Phương Pháp Đơn Giản (Tự Động)

Sử dụng script `build_executable.py` để tự động hóa quá trình:

```bash
# Biên dịch với cấu hình mặc định
python build_executable.py

# Biên dịch với các tùy chọn bổ sung
python build_executable.py --output dist/my_trading_bot --name "My Trading Bot" --icon path/to/icon.ico
```

Các tham số:
- `--output`: Thư mục output (mặc định: `dist`)
- `--onefile`: Tạo một file duy nhất thay vì thư mục (cờ boolean)
- `--name`: Tên file thực thi (mặc định: `TradingBot`)
- `--icon`: Đường dẫn đến file icon

### Phương Pháp Thủ Công

Nếu muốn kiểm soát chi tiết hơn:

1. Tạo file spec:
   ```bash
   pyi-makespec --windowed --icon=static/images/bot_icon.ico bot_gui.py
   ```

2. Chỉnh sửa file spec theo nhu cầu

3. Biên dịch với file spec:
   ```bash
   pyinstaller bot_gui.spec
   ```

## Tùy Chọn Biên Dịch

### One-File vs One-Directory

- **One-Directory**: (Mặc định) Tạo ra một thư mục chứa file thực thi và các thư viện phụ thuộc
  - Ưu điểm: Khởi động nhanh, dễ cập nhật
  - Nhược điểm: Nhiều file

- **One-File**: Tạo một file thực thi duy nhất
  - Ưu điểm: Dễ phân phối, gọn nhẹ
  - Nhược điểm: Khởi động chậm hơn (giải nén tạm thời khi chạy)

### Giao Diện Console

- **Console** (`--console`): Hiển thị cửa sổ console khi chạy
  - Ưu điểm: Hiển thị thông báo lỗi, output trực tiếp
  - Nhược điểm: Không chuyên nghiệp cho người dùng cuối

- **Windows/Ẩn Console** (`--windowed`): Ẩn cửa sổ console
  - Ưu điểm: Giao diện sạch sẽ, chuyên nghiệp
  - Nhược điểm: Khó debug lỗi

## Cấu Trúc Thư Mục Sau Khi Biên Dịch

### One-Directory Mode

```
dist/
└── TradingBot/
    ├── TradingBot.exe         # File thực thi chính
    ├── python3x.dll           # Thư viện Python
    ├── _internal/             # Các module Python
    ├── risk_configs/          # Cấu hình rủi ro
    ├── strategies/            # Chiến lược giao dịch
    ├── templates/             # Templates web
    ├── static/                # Tài nguyên tĩnh
    └── ... (các file và thư viện khác)
```

### One-File Mode

```
dist/
└── TradingBot.exe             # File thực thi duy nhất
```

**Lưu ý**: Trong chế độ One-File, vẫn cần sao chép các file cấu hình và thư mục dữ liệu cần thiết vào thư mục chạy.

## Chạy File Thực Thi

### Windows

Đơn giản chỉ cần nhấp đôi vào file `.exe` hoặc chạy từ dòng lệnh:

```bash
# Chế độ One-Directory
dist\TradingBot\TradingBot.exe

# Chế độ One-File
dist\TradingBot.exe
```

### Linux

```bash
# Đảm bảo có quyền thực thi
chmod +x dist/TradingBot

# Chạy
./dist/TradingBot
```

### macOS

```bash
# Chạy
./dist/TradingBot
```

### Tham Số Command Line

File thực thi hỗ trợ các tham số giống như khi chạy script gốc:

```bash
# Chạy với mức rủi ro cụ thể
TradingBot.exe --risk-level 20

# Chạy trong chế độ test
TradingBot.exe --test-mode
```

## Xử Lý Sự Cố

### Vấn Đề Phổ Biến

1. **File thực thi không chạy**:
   - Thử chạy từ dòng lệnh để xem lỗi
   - Kiểm tra đã cài đặt Visual C++ Redistributable (Windows)
   - Đảm bảo tất cả các file phụ thuộc đã được bao gồm

2. **Lỗi "Missing module"**:
   - Thêm module vào danh sách `hidden_imports` trong file spec
   - Cài đặt lại thư viện thiếu và biên dịch lại

3. **Lỗi quyền truy cập**:
   - Chạy với quyền Administrator (Windows)
   - Đảm bảo có quyền thực thi (`chmod +x`) trên Linux/macOS

4. **File quá lớn**:
   - Sử dụng `--exclude` để loại bỏ thư viện không cần thiết
   - Sử dụng `UPX` để nén file (thêm `--upx-dir=path/to/upx`)

### Debug Mode

Để debug vấn đề, biên dịch với cờ debug:

```bash
python build_executable.py --debug
```

Hoặc thủ công:

```bash
pyinstaller --debug all bot_gui.spec
```

## Gói Phân Phối

Để phân phối ứng dụng:

### 1. Chuẩn Bị Gói

```bash
# Tự động tạo gói phân phối
python create_distribution_package.py
```

Hoặc thủ công:

1. Biên dịch file thực thi
2. Sao chép các file cấu hình cần thiết
3. Tạo file README và hướng dẫn cài đặt
4. Nén tất cả vào một archive (ZIP, TAR, etc.)

### 2. Bao Gồm Các File Quan Trọng

Đảm bảo gói phân phối bao gồm:

- File thực thi
- Thư mục risk_configs/
- File cấu hình tài khoản mẫu
- Tài liệu hướng dẫn
- Thông tin giấy phép và phiên bản

### 3. Tạo Chương Trình Cài Đặt (Tùy Chọn)

Trên Windows, có thể tạo bộ cài đặt với NSIS hoặc Inno Setup:

```bash
# Tạo bộ cài đặt với NSIS
python create_installer.py --type nsis

# Tạo bộ cài đặt với Inno Setup
python create_installer.py --type inno
```

---

## Ghi Chú Quan Trọng

- **Mỗi Nền Tảng Một Bản Build**: File thực thi được tạo trên Windows chỉ chạy được trên Windows, tương tự cho Linux và macOS
- **Cập Nhật Thường Xuyên**: Các file thực thi có thể không tự động cập nhật, cần tạo và phân phối phiên bản mới
- **Kiểm Tra Trước Khi Phân Phối**: Luôn kiểm tra kỹ file thực thi trên hệ thống tương tự với môi trường người dùng cuối
- **Bảo Mật API Keys**: File thực thi không mã hóa mã nguồn, tránh nhúng API keys hoặc thông tin nhạy cảm

---

*Nếu bạn gặp vấn đề trong quá trình tạo file thực thi, vui lòng tham khảo tài liệu đầy đủ của PyInstaller tại https://pyinstaller.org/en/stable/*