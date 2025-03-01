# Hướng Dẫn Triển Khai Bot Trading

Tài liệu này cung cấp hướng dẫn chi tiết về cách triển khai và cấu hình bot trong môi trường test và sản xuất.

## Cấu Hình Môi Trường

Hệ thống sử dụng biến môi trường để điều khiển hoạt động của bot. Các biến môi trường được đặt trong file `.env`. Bạn có thể tạo file này bằng cách sao chép từ `.env.example`:

```bash
cp .env.example .env
```

### Các Biến Môi Trường Chính

| Biến | Mô tả | Giá trị mặc định |
|------|-------|-----------------|
| BINANCE_API_KEY | API Key của Binance | - |
| BINANCE_API_SECRET | API Secret của Binance | - |
| TELEGRAM_BOT_TOKEN | Token của Telegram Bot | - |
| TELEGRAM_CHAT_ID | Chat ID nhận thông báo | - |
| AUTO_START_BOT | Tự động khởi động bot khi khởi động server | false |
| AUTO_RESTART_BOT | Tự động khởi động lại bot khi bị crash | false |

## Các Chế Độ Hoạt Động

### Chế Độ Test

Trong chế độ test, bạn nên tắt các tính năng tự động để kiểm soát hoạt động của bot thủ công:

```
AUTO_START_BOT=false
AUTO_RESTART_BOT=false
```

Điều này cho phép:
- Kiểm soát khi nào bot khởi động/dừng lại thông qua giao diện web
- Ngăn bot tự khởi động lại khi có lỗi (để bạn có thể xem xét lỗi)
- Giảm tải cho máy chủ trong quá trình phát triển

### Chế Độ Sản Xuất (Production)

Khi triển khai cho môi trường sản xuất, bạn nên bật các tính năng tự động:

```
AUTO_START_BOT=true
AUTO_RESTART_BOT=true
```

Điều này đảm bảo:
- Bot tự động khởi động khi server khởi động
- Bot tự động khởi động lại nếu bị crash
- Hệ thống chạy 24/7 không cần can thiệp thủ công

## Khởi Động Bot Thủ Công

Trong trường hợp bạn muốn khởi động bot thủ công:

1. Truy cập vào giao diện web
2. Nhấn vào nút "Start Bot" trong giao diện 
3. Theo dõi trạng thái bot trong tab Dashboard

## Cấu Hình Thông Báo

### Telegram

Để nhận thông báo qua Telegram:

1. Tạo bot Telegram qua BotFather
2. Lấy token của bot và đặt vào biến `TELEGRAM_BOT_TOKEN`
3. Lấy chat ID (có thể sử dụng @myidbot) và đặt vào biến `TELEGRAM_CHAT_ID`
4. Truy cập tab "Configuration" trong giao diện web để kiểm tra và cấu hình thêm
5. Kiểm tra kết nối Telegram bằng nút "Test Connection"

### Email

Để nhận báo cáo qua email:

1. Đặt thông tin email trong các biến môi trường:
   - EMAIL_USERNAME
   - EMAIL_PASSWORD
   - EMAIL_SMTP_SERVER
   - EMAIL_SMTP_PORT
   - EMAIL_RECIPIENT
2. Truy cập tab "Configuration" trong giao diện web để cấu hình lịch trình gửi email
3. Kiểm tra kết nối email bằng nút "Test Email"

## Xử Lý Sự Cố

### Lỗi Socket/Connection

Nếu gặp lỗi "Bad file descriptor" hoặc các vấn đề về kết nối:

1. Khởi động lại server
2. Kiểm tra lại cấu hình EventLet và SocketIO trong file main.py
3. Giảm tải bằng cách tăng các giá trị `time.sleep()` trong các hàm cập nhật

### Lỗi Bot

Nếu bot gặp lỗi:

1. Kiểm tra logs trong file `trading_bot.log`
2. Truy cập tab "Logs" trong giao diện web để xem logs chi tiết
3. Sửa lỗi và khởi động lại bot thủ công

## Ghi Chú Quan Trọng

- **Testnet vs Mainnet**: Đảm bảo bạn đang sử dụng API testnet trong môi trường test, và API mainnet trong môi trường sản xuất
- **Quản lý rủi ro**: Luôn kiểm tra cấu hình quản lý rủi ro trước khi chạy bot trong môi trường sản xuất
- **Giám sát**: Thường xuyên kiểm tra hiệu suất của bot thông qua giao diện web và báo cáo tự động
- **Backup**: Sao lưu dữ liệu cấu hình và trạng thái giao dịch định kỳ