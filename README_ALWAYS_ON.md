# Hướng Dẫn Thiết Lập Always On Cho Bot

Hướng dẫn này giúp bạn thiết lập chức năng Always On cho bot Binance Trader, giúp bot chạy liên tục 24/7 ngay cả khi bạn đóng tab hoặc out khỏi ứng dụng.

## Phương Pháp 1: Sử Dụng Keep-Alive và UptimeRobot

### Bước 1: Khởi Động Dịch Vụ Keep-Alive
```bash
python setup_always_on.py
```

### Bước 2: Thiết Lập UptimeRobot
1. Truy cập website: https://uptimerobot.com/
2. Đăng ký tài khoản miễn phí
3. Sau khi đăng nhập, chọn 'Add New Monitor'
4. Chọn 'HTTP(s)' làm Monitor Type
5. Đặt tên cho monitor, ví dụ: 'Binance Trader Bot'
6. Nhập URL của Replit của bạn: https://YourReplitURL.replit.app
7. Để mọi cài đặt khác ở mặc định và lưu
8. UptimeRobot sẽ tự động ping ứng dụng của bạn mỗi 5 phút

### Cách Thức Hoạt Động
- Dịch vụ keep-alive tạo một HTTP server đơn giản trên cổng 8080
- UptimeRobot sẽ ping URL của bạn đều đặn mỗi 5 phút
- Điều này giữ cho Replit luôn chạy, ngăn nó đi vào chế độ "sleep"

## Phương Pháp 2: Nâng Cấp Lên Replit Pro

Nếu bạn muốn giải pháp chính thức và đáng tin cậy hơn:

1. Nâng cấp lên Replit Pro
2. Bật tính năng "Always On" trong mục "Hosting"
3. Bot sẽ chạy 24/7 mà không cần thêm bất kỳ cấu hình nào

## Kiểm Tra Trạng Thái

Để kiểm tra xem dịch vụ keep-alive có đang chạy không:

```bash
curl http://localhost:8080/status
```

Kết quả trả về sẽ là: `{"status":"running","uptime":"active","version":"1.0.0"}`

---

Lưu ý: Khi sử dụng phương pháp keep-alive, nếu bot bị crash hoặc Replit tự khởi động lại, dịch vụ keep-alive và bot sẽ tự động khởi động lại nhờ vào tích hợp trong file main.py.
