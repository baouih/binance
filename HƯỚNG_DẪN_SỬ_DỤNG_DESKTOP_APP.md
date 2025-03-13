# HƯỚNG DẪN SỬ DỤNG GIAO DIỆN DESKTOP CRYPTO TRADING BOT

## GIỚI THIỆU

Giao diện desktop của Crypto Trading Bot là một phiên bản hoàn chỉnh với đầy đủ tính năng của hệ thống giao dịch, giúp bạn dễ dàng thực hiện và quản lý các giao dịch crypto trên Binance Testnet một cách trực quan và hiệu quả.

Phiên bản desktop cung cấp các tính năng:
- Giao diện đồ họa trực quan với dark theme
- Quản lý tất cả dịch vụ từ một nơi
- Phân tích kỹ thuật và thị trường theo thời gian thực
- Quản lý vị thế và rủi ro
- Thông báo tức thì qua Telegram

## CÀI ĐẶT VÀ KHỞI ĐỘNG

### Phương pháp 1: Chạy từ mã nguồn

1. **Cài đặt các thư viện cần thiết**:
   ```bash
   pip install PyQt5 pandas numpy requests python-binance python-dotenv matplotlib
   ```

2. **Cấu hình API key**:
   - Tạo file `.env` trong thư mục gốc
   - Thêm các biến môi trường:
     ```
     BINANCE_TESTNET_API_KEY=your_api_key
     BINANCE_TESTNET_API_SECRET=your_api_secret
     TELEGRAM_BOT_TOKEN=your_telegram_token
     TELEGRAM_CHAT_ID=your_telegram_chat_id
     ```

3. **Chạy ứng dụng**:
   ```bash
   python run_desktop_app.py
   ```

### Phương pháp 2: Sử dụng file thực thi (EXE)

1. **Tạo file EXE**:
   ```bash
   python package_desktop_app.py
   ```

2. **Chạy file EXE**:
   - File được tạo ra sẽ nằm trong thư mục `dist` với tên `TradingBot_vX.Y.Z.exe`
   - Chạy file này để khởi động ứng dụng

## HƯỚNG DẪN SỬ DỤNG

### Cấu hình ban đầu

1. Sau khi khởi động ứng dụng, chuyển đến tab **Cài đặt**
2. Nhập **API Key** và **API Secret** từ Binance Testnet
3. Nhập thông tin **Telegram Bot** (Token và Chat ID) nếu muốn nhận thông báo
4. Nhấn **Lưu cài đặt API** và **Lưu cài đặt Telegram**

### Quản lý dịch vụ hệ thống

1. Chuyển đến tab **Quản lý hệ thống**
2. Để bắt đầu tất cả dịch vụ, nhấn nút **Khởi động tất cả dịch vụ**
3. Để dừng tất cả dịch vụ, nhấn nút **Dừng tất cả dịch vụ**
4. Bạn cũng có thể khởi động/dừng từng dịch vụ riêng biệt:
   - **Market Analyzer**: Phân tích thị trường theo thời gian thực
   - **Trading System**: Hệ thống giao dịch tự động
   - **Auto SLTP**: Quản lý Stop Loss và Take Profit tự động
   - **Telegram Notifier**: Gửi thông báo qua Telegram

### Giao dịch thủ công

1. Chuyển đến tab **Giao dịch**
2. Chọn cặp giao dịch (ví dụ: BTCUSDT)
3. Chọn hướng giao dịch (LONG/SHORT)
4. Nhập kích thước vị thế và đòn bẩy
5. Thiết lập Stop Loss và Take Profit (hoặc chọn tự động)
6. Nhấn nút **Mở Long** hoặc **Mở Short** để bắt đầu giao dịch

### Quản lý vị thế

1. Chuyển đến tab **Quản lý vị thế**
2. Bảng vị thế hiển thị tất cả các vị thế đang mở
3. Chọn một vị thế và nhập giá trị Stop Loss/Take Profit mới
4. Nhấn nút **Cập nhật SL/TP** để cập nhật
5. Nhấn nút **Đóng vị thế** để đóng vị thế đã chọn

### Phân tích thị trường

1. Chuyển đến tab **Phân tích thị trường**
2. Chọn cặp giao dịch và khung thời gian
3. Nhấn nút **Phân tích** để xem phân tích kỹ thuật
4. Kết quả phân tích sẽ hiển thị các chỉ báo, xu hướng và tín hiệu giao dịch

### Theo dõi nhật ký hệ thống

1. Trong tab **Quản lý hệ thống**, phần dưới hiển thị nhật ký hệ thống
2. Nhấn nút **Cập nhật nhật ký** để xem nhật ký mới nhất
3. Nhấn nút **Xóa nhật ký** để xóa nhật ký hiện tại

## CÁCH TẠO VÀ SỬ DỤNG FILE EXE

### Tạo file EXE

1. **Chuẩn bị môi trường**:
   - Đảm bảo đã cài đặt `pyinstaller`:
     ```bash
     pip install pyinstaller
     ```

2. **Chạy script đóng gói**:
   ```bash
   python package_desktop_app.py
   ```

3. **Kiểm tra kết quả**:
   - Sau khi quá trình đóng gói hoàn tất, file EXE sẽ được tạo trong thư mục `dist`
   - Tên file có dạng `TradingBot_vX.Y.Z.exe` (với X.Y.Z là phiên bản)

### Cấu hình và sử dụng file EXE

1. **Chạy file EXE**:
   - Double-click vào file để khởi động ứng dụng

2. **Cấu hình lần đầu tiên**:
   - Khi chạy lần đầu, ứng dụng sẽ yêu cầu thông tin API key
   - Nhập thông tin API Binance Testnet và Telegram
   - Thông tin sẽ được lưu cho các lần sử dụng tiếp theo

3. **Lưu ý khi sử dụng file EXE**:
   - File EXE chứa tất cả các module cần thiết cho ứng dụng
   - Không cần cài đặt Python hoặc các thư viện khác
   - Không cần thay đổi các biến môi trường trong hệ thống

## CÁC TÍNH NĂNG NÂNG CAO

### Auto SLTP (Stop Loss/Take Profit tự động)

1. Trong tab **Cài đặt**, phần **Cài đặt rủi ro**
2. Nhập phần trăm Stop Loss và Take Profit
3. Bật/tắt tùy chọn **Trailing Stop**
4. Nhấn nút **Lưu cài đặt rủi ro**
5. Đảm bảo dịch vụ **Auto SLTP** đã được khởi động trong tab **Quản lý hệ thống**

### Trailing Stop

1. Trong tab **Cài đặt**, phần **Cài đặt rủi ro**
2. Đánh dấu vào ô **Sử dụng Trailing Stop**
3. Nhấn nút **Lưu cài đặt rủi ro**
4. Khi vị thế đạt đến mức lợi nhuận nhất định, Trailing Stop sẽ tự động điều chỉnh để bảo vệ lợi nhuận

### Thông báo Telegram

1. Trong tab **Cài đặt**, phần **Cài đặt Telegram**
2. Nhập Bot Token và Chat ID
3. Chọn các loại thông báo muốn nhận
4. Nhấn nút **Lưu cài đặt Telegram**
5. Thử kết nối bằng cách nhấn nút **Kiểm tra kết nối**

## GIẢI QUYẾT SỰ CỐ

### Không thể kết nối với Binance API

1. Kiểm tra API Key và API Secret đã nhập đúng chưa
2. Đảm bảo đã chọn đúng môi trường (Testnet)
3. Kiểm tra kết nối internet
4. Thử tạo API Key mới từ trang Binance Testnet

### Dịch vụ không khởi động

1. Kiểm tra log trong tab **Quản lý hệ thống**
2. Đảm bảo các file script tương ứng tồn tại
3. Kiểm tra quyền thực thi file
4. Khởi động lại ứng dụng và thử lại

### Lỗi khi tạo file EXE

1. Đảm bảo đã cài đặt PyInstaller
2. Kiểm tra log trong file `packaging.log`
3. Đảm bảo tất cả các thư viện phụ thuộc đã được cài đặt
4. Thử cập nhật PyInstaller lên phiên bản mới nhất

### Ứng dụng bị treo hoặc không phản hồi

1. Đóng và khởi động lại ứng dụng
2. Kiểm tra tài nguyên hệ thống (CPU, RAM)
3. Kiểm tra log để xác định nguyên nhân
4. Thử dừng các dịch vụ không cần thiết để giảm tải

## LƯU Ý QUAN TRỌNG

1. **Sử dụng môi trường Testnet**: Ứng dụng này được thiết kế để chạy trên Binance Testnet. Không sử dụng API Key thật cho ứng dụng này.

2. **Quản lý rủi ro**: Luôn cấu hình các tham số quản lý rủi ro phù hợp với chiến lược giao dịch của bạn.

3. **Sao lưu dữ liệu**: Nên sao lưu các file cấu hình thường xuyên để tránh mất dữ liệu.

4. **Cập nhật ứng dụng**: Kiểm tra và cập nhật ứng dụng lên phiên bản mới nhất để có được các tính năng và sửa lỗi mới nhất.

---

© 2025 Crypto Trading Bot Team - Phiên bản 1.0.0