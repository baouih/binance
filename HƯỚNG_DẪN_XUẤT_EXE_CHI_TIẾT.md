# HƯỚNG DẪN CHI TIẾT XUẤT FILE EXE

## 1. TỔNG QUAN

Tài liệu này cung cấp hướng dẫn chi tiết để xuất hệ thống giao dịch crypto thành file thực thi (`.exe`) để chạy trên máy tính cá nhân. Điều này giúp tránh các hạn chế của Replit như không thể chạy 24/7.

## 2. CÁC BƯỚC CHUẨN BỊ

### 2.1. Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10/11 (khuyên dùng), hoặc Linux/macOS
- **Python**: Phiên bản 3.8 trở lên (khuyên dùng Python 3.9)
- **RAM**: Tối thiểu 8GB, khuyên dùng 16GB
- **Dung lượng ổ cứng**: Ít nhất 5GB trống

### 2.2. Tải mã nguồn

- Tải toàn bộ dự án từ Replit:
  - Click nút "Download as ZIP" ở góc trên bên phải
  - Hoặc sử dụng git clone nếu bạn có quyền truy cập

### 2.3. Cài đặt môi trường

1. **Cài đặt Python**:
   - Tải và cài đặt Python từ [python.org](https://www.python.org/downloads/)
   - Đảm bảo đánh dấu "Add Python to PATH" trong quá trình cài đặt

2. **Tạo và kích hoạt môi trường ảo** (tùy chọn nhưng khuyên dùng):
   ```bash
   # Tạo môi trường ảo
   python -m venv venv

   # Kích hoạt môi trường ảo (Windows)
   venv\Scripts\activate

   # Kích hoạt môi trường ảo (Linux/Mac)
   source venv/bin/activate
   ```

3. **Cài đặt các thư viện phụ thuộc**:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

## 3. XUẤT FILE EXE

Có hai phương pháp xuất file exe:

### 3.1. Phương pháp 1: Sử dụng script tự động

Đây là phương pháp đơn giản nhất và được khuyên dùng:

1. **Mở Command Prompt** (Windows) hoặc Terminal (Linux/Mac)

2. **Điều hướng đến thư mục dự án**:
   ```bash
   cd đường_dẫn_đến_thư_mục_dự_án
   ```

3. **Chạy script build_executable.py**:
   ```bash
   python build_executable.py
   ```

4. **Tùy chọn bổ sung** (không bắt buộc):
   ```bash
   # Tạo file exe đơn lẻ
   python build_executable.py --onefile

   # Tùy chỉnh tên file exe
   python build_executable.py --name "TradingBot_Custom"
   
   # Tùy chỉnh thư mục đầu ra
   python build_executable.py --output "dist/my_custom_folder"
   ```

5. **Kiểm tra kết quả**:
   - File exe sẽ được tạo trong thư mục `dist/TradingBot` (hoặc thư mục bạn đã chỉ định)

### 3.2. Phương pháp 2: Sử dụng package_desktop_app.py

Phương pháp này tạo ra phiên bản desktop nhẹ hơn với giao diện đồ họa:

1. **Chạy script package_desktop_app.py**:
   ```bash
   python package_desktop_app.py
   ```

2. **Kiểm tra kết quả**:
   - File exe sẽ được tạo trong thư mục `dist` với tên dạng `TradingBot_v*.*.*.exe`
   - Ví dụ: `TradingBot_v1.0.5.exe`

## 4. CẤU HÌNH VÀ SỬ DỤNG

### 4.1. Thiết lập API Keys

Để sử dụng file exe với Binance Testnet, bạn cần cấu hình API keys:

1. **Tạo file .env**:
   - Tạo file `.env` trong cùng thư mục với file exe
   - Thêm các thông tin sau:
     ```
     BINANCE_TESTNET_API_KEY=your_api_key_here
     BINANCE_TESTNET_API_SECRET=your_api_secret_here
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token (nếu muốn nhận thông báo)
     TELEGRAM_CHAT_ID=your_telegram_chat_id (nếu muốn nhận thông báo)
     ```

2. **Hoặc nhập trực tiếp trong ứng dụng**:
   - Mở file exe đã tạo
   - Vào tab "Cài đặt" > "Cài đặt API"
   - Nhập API Key và Secret từ Binance Testnet
   - Lưu cài đặt

### 4.2. Chạy ứng dụng

1. **Mở file exe** bằng cách nhấp đúp vào nó hoặc chạy từ dòng lệnh:
   ```bash
   dist\TradingBot\TradingBot.exe    # Phương pháp 1
   # hoặc
   dist\TradingBot_v1.0.0.exe         # Phương pháp 2
   ```

2. **Kiểm tra kết nối API**:
   - Sau khi ứng dụng khởi động, nó sẽ tự động kiểm tra kết nối API
   - Nếu kết nối thành công, bạn sẽ thấy số dư tài khoản và thông tin thị trường

3. **Cấu hình thông số giao dịch**:
   - Vào tab "Cài đặt" > "Cài đặt rủi ro"
   - Thiết lập % rủi ro, đòn bẩy và các thông số khác

## 5. XỬ LÝ SỰ CỐ

### 5.1. File exe không hoạt động

- **Lỗi "Missing DLL"**:
  - Cài đặt Microsoft Visual C++ Redistributable
  - Link tải: https://aka.ms/vs/17/release/vc_redist.x64.exe

- **Lỗi "Blocked by antivirus"**:
  - Thêm ngoại lệ trong phần mềm antivirus hoặc Windows Defender
  - Chuyển sang sử dụng phương pháp xuất dạng thư mục thay vì file đơn lẻ

- **Lỗi "Python not found"**:
  - Đảm bảo sử dụng PyInstaller với cùng phiên bản Python đã cài đặt các gói phụ thuộc

### 5.2. Lỗi kết nối API

- **Kiểm tra API keys**:
  - Đảm bảo sử dụng API keys của Binance Testnet (không phải tài khoản thực)
  - Kiểm tra keys có quyền Futures Trading

- **Kiểm tra kết nối internet**:
  - Đảm bảo máy tính có kết nối internet ổn định
  - Một số tường lửa có thể chặn kết nối WebSocket

### 5.3. Lỗi không hiển thị giao diện

- **Lỗi PyQt5**:
  - Đảm bảo đã cài đặt PyQt5 trước khi build exe
  - Thử cài đặt lại: `pip install PyQt5==5.15.6`

- **Màn hình trắng hoặc đen**:
  - Kiểm tra card đồ họa có hỗ trợ OpenGL
  - Thử chạy với tham số GPU offload: `TradingBot.exe --disable-gpu`

## 6. KHUYẾN NGHỊ

### 6.1. Cấu hình được khuyên dùng

- **Mức độ rủi ro**: 1-2% trên mỗi giao dịch
- **Đòn bẩy tối đa**: 5x-10x (phụ thuộc vào mức độ biến động của thị trường)
- **Số lượng vị thế đồng thời**: Tối đa 3-5 vị thế

### 6.2. Bảo trì hệ thống

- **Kiểm tra cập nhật**:
  - Ứng dụng sẽ tự động kiểm tra cập nhật khi khởi động
  - Bạn cũng có thể kiểm tra thủ công trong tab "Cài đặt" > "Kiểm tra cập nhật"

- **Sao lưu dữ liệu**:
  - Sao lưu file cấu hình `account_config.json` định kỳ
  - Sao lưu thư mục `risk_configs` chứa các cấu hình rủi ro

## 7. CÁC TÀI LIỆU LIÊN QUAN

Để biết thêm thông tin chi tiết, vui lòng tham khảo các tài liệu sau:

- README_DESKTOP_APP.md: Hướng dẫn sử dụng ứng dụng desktop
- README_EXECUTABLE.md: Thông tin thêm về quá trình tạo exe
- README_TESTNET_USAGE.md: Hướng dẫn sử dụng Binance Testnet 
- README_RISK_MANAGEMENT.md: Chiến lược quản lý rủi ro