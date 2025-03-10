# Ứng dụng Giao dịch Crypto - Phiên Bản Desktop

Ứng dụng giao dịch Crypto phiên bản desktop cung cấp giao diện người dùng đồ họa cho hệ thống giao dịch, cho phép bạn dễ dàng quản lý và theo dõi các giao dịch tiền điện tử.

## Tính năng

- **Giao diện người dùng đồ họa PyQt5**: Giao diện người dùng đẹp mắt và dễ sử dụng
- **Quản lý vị thế**: Mở, đóng và quản lý các vị thế giao dịch
- **Phân tích thị trường**: Phân tích kỹ thuật với nhiều chỉ báo (RSI, MACD, Bollinger Bands,...)
- **Quản lý rủi ro**: Thiết lập Stop Loss, Take Profit, Trailing Stop và các thông số quản lý rủi ro khác
- **Cập nhật tự động**: Tự động kiểm tra và cài đặt các phiên bản mới

## Yêu cầu hệ thống

- Python 3.8 trở lên
- Các thư viện Python cần thiết (sẽ được cài đặt tự động)
- Tài khoản Binance Testnet (cho mục đích thử nghiệm)

## Cài đặt

1. Tải file từ Replit:
   - Nhấn vào nút "Download as ZIP" trên Replit để tải toàn bộ project 
   - Hoặc sử dụng công cụ "package_desktop_app.py" để tạo file thực thi

2. Giải nén file (nếu tải dưới dạng ZIP):
   ```
   unzip trading-bot.zip
   cd trading-bot
   ```

3. Cài đặt các thư viện cần thiết (nếu chạy từ source code):
   ```
   pip install -r system_requirements.txt
   ```

4. Cấu hình tài khoản API:
   - Tạo file `.env` từ file `.env.example`
   - Nhập API Key và Secret của Binance Testnet vào file `.env`
   - Nhập Telegram Bot Token và Chat ID (nếu muốn nhận thông báo)

## Sử dụng

### Chạy ứng dụng desktop:

```
python run_desktop_app.py
```

Ứng dụng sẽ khởi động với giao diện đồ họa, cho phép bạn:
- Xem tổng quan thị trường
- Mở và quản lý các vị thế giao dịch
- Phân tích kỹ thuật
- Theo dõi lịch sử giao dịch
- Cấu hình hệ thống

### Đóng gói thành file .exe (Windows):

```
python package_desktop_app.py
```

File thực thi sẽ được tạo trong thư mục `dist`.

## Hướng dẫn

### Giao diện chính

Giao diện chính bao gồm 5 tab:

1. **Tổng quan**: Hiển thị thông tin số dư, danh sách vị thế đang mở và thông tin thị trường.
2. **Giao dịch**: Cho phép mở vị thế mới và xem phân tích.
3. **Quản lý vị thế**: Quản lý các vị thế đang mở và xem lịch sử giao dịch.
4. **Phân tích thị trường**: Phân tích kỹ thuật chi tiết với nhiều chỉ báo.
5. **Cài đặt**: Cấu hình API, rủi ro và giao diện.

### Mở vị thế mới

1. Chọn tab "Giao dịch"
2. Chọn cặp giao dịch (ví dụ: BTCUSDT)
3. Chọn hướng giao dịch (LONG/SHORT)
4. Nhập kích thước vị thế hoặc nhấn "Tính toán vị thế" để tính toán tự động
5. Thiết lập đòn bẩy, Stop Loss và Take Profit
6. Nhấn "Mở Long" hoặc "Mở Short" để đặt lệnh

### Quản lý vị thế

1. Chọn tab "Quản lý vị thế"
2. Chọn vị thế cần quản lý từ danh sách
3. Cập nhật Stop Loss và Take Profit nếu cần
4. Nhấn "Cập nhật SL/TP" để áp dụng thay đổi hoặc "Đóng vị thế" để đóng vị thế

### Phân tích thị trường

1. Chọn tab "Phân tích thị trường"
2. Chọn cặp giao dịch và khung thời gian
3. Nhấn "Phân tích" để xem kết quả phân tích chi tiết
4. Xem các chỉ báo kỹ thuật, mức hỗ trợ/kháng cự và xu hướng

## Cấu hình rủi ro

Bạn có thể cấu hình các thông số quản lý rủi ro trong tab "Cài đặt" > "Cài đặt rủi ro":

- **Phần trăm rủi ro**: % tổng số dư tài khoản tối đa có thể rủi ro trên mỗi giao dịch
- **Số lượng vị thế tối đa**: Số lượng vị thế có thể mở cùng lúc
- **Đòn bẩy mặc định**: Đòn bẩy mặc định được sử dụng
- **Phần trăm SL/TP**: % dưới/trên giá vào lệnh để đặt SL/TP
- **Trailing Stop**: Bật/tắt và cấu hình trailing stop
- **Giới hạn giờ giao dịch**: Giới hạn giao dịch trong các khung giờ nhất định

## Cập nhật tự động

Ứng dụng sẽ tự động kiểm tra cập nhật khi khởi động. Nếu có phiên bản mới, nó sẽ thông báo và hỏi bạn có muốn cài đặt hay không.

Bạn cũng có thể kiểm tra cập nhật thủ công bằng cách chạy:
```
python auto_update_client.py
```

## Xử lý sự cố

- **Không kết nối được với Binance API**: Kiểm tra API Key và Secret, đảm bảo bạn đang sử dụng API Testnet.
- **Lỗi khi mở vị thế**: Kiểm tra số dư và cấu hình rủi ro.
- **Lỗi khi đóng gói thành file .exe**: Đảm bảo bạn đã cài đặt PyInstaller và các thư viện cần thiết.

## Đóng góp

Chúng tôi rất hoan nghênh đóng góp từ cộng đồng. Nếu bạn muốn đóng góp, vui lòng:

1. Fork dự án
2. Tạo branch cho tính năng mới (`git checkout -b feature/amazing-feature`)
3. Commit thay đổi của bạn (`git commit -m 'Add amazing feature'`)
4. Push branch lên GitHub (`git push origin feature/amazing-feature`)
5. Mở Pull Request

## Giấy phép

Dự án này được cấp phép theo [MIT License](LICENSE).