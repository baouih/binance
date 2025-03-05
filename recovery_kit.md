# Bộ công cụ khôi phục Crypto Trading Bot

## Tổng quan
Bộ công cụ này giúp bạn dễ dàng khắc phục sự cố và khôi phục hoạt động của Crypto Trading Bot trên máy tính cá nhân hoặc server. Tài liệu này cung cấp hướng dẫn chi tiết về cách giải quyết các vấn đề phổ biến và thực hiện các thao tác bảo trì.

## Các công cụ đã tạo
Trong bộ kit này, chúng tôi đã cung cấp ba công cụ chính:

1. **log_collector.py**: Thu thập logs và file cấu hình để phân tích lỗi
2. **remote_helper.py**: Kết nối và điều khiển bot từ xa
3. **watchdog_runner.sh**: Khởi động và giám sát hoạt động của bot

## Cách sử dụng để khôi phục trên máy cá nhân

### Bước 1: Xuất mã nguồn
Trước tiên, bạn cần xuất mã nguồn từ Replit để triển khai trên máy của mình:

```bash
python log_collector.py
```

Chọn tùy chọn 2 (Tạo gói triển khai đầy đủ) và tải gói xuống máy tính của bạn.

### Bước 2: Cài đặt trên máy cá nhân
1. Giải nén file zip đã tải xuống
2. Mở terminal hoặc command prompt trong thư mục đã giải nén
3. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

### Bước 3: Cấu hình bot
1. Sao chép file `.env.example` thành `.env`:
   ```bash
   cp .env.example .env
   ```
2. Chỉnh sửa file `.env` với API key Binance của bạn và các thông tin cấu hình khác
3. Kiểm tra file `account_config.json` để đảm bảo nó phù hợp với tài khoản của bạn

### Bước 4: Khởi động bot
1. Cấp quyền thực thi cho các script:
   ```bash
   chmod +x *.sh
   ```
2. Khởi động hệ thống:
   ```bash
   ./watchdog_runner.sh
   ```

## Xử lý sự cố phổ biến

### 1. Bot không khởi động
Nguyên nhân có thể là do thiếu quyền thực thi hoặc thiếu thư viện:

```bash
# Cấp quyền thực thi
chmod +x *.sh *.py

# Kiểm tra log khởi động
cat auto_recovery.log
cat watchdog.log

# Đảm bảo đã cài đặt tất cả thư viện
pip install -r requirements.txt
```

### 2. Lỗi kết nối API Binance
Nguyên nhân có thể là do API key không hợp lệ hoặc không có quyền truy cập:

```bash
# Kiểm tra file .env
cat .env

# Kiểm tra log API
grep "API" flask_app.log
```

### 3. Lỗi hệ thống giám sát
Để khôi phục hệ thống giám sát:

```bash
# Dừng tất cả tiến trình hiện tại
pkill -f python
pkill -f gunicorn

# Khởi động lại hệ thống
./watchdog_runner.sh
```

## Thiết lập kết nối từ xa

Bạn có thể sử dụng `remote_helper.py` để thiết lập kết nối từ xa, cho phép chuyên gia hỗ trợ bạn từ xa:

1. Chạy script thiết lập:
   ```bash
   python remote_helper.py --setup
   ```

2. Nhập các thông tin kết nối được cung cấp bởi đội hỗ trợ

3. Khởi động kết nối:
   ```bash
   python remote_helper.py
   ```

4. Cung cấp ID kết nối cho đội hỗ trợ

## Các lệnh hữu ích

### Kiểm tra trạng thái bot
```bash
cat bot_status.json
```

### Xem vị thế đang mở
```bash
cat active_positions.json
```

### Kiểm tra logs
```bash
tail -f *.log
```

### Lấy báo cáo trạng thái đầy đủ
```bash
python log_collector.py
```
Chọn tùy chọn 1 để tạo gói debug.

## Lưu ý bảo mật
- Không chia sẻ file `.env` và API key của bạn với bất kỳ ai
- Chỉ sử dụng `remote_helper.py` với những người bạn tin tưởng
- Luôn sao lưu dữ liệu trước khi thực hiện các thay đổi lớn

## Liên hệ hỗ trợ
Nếu bạn gặp vấn đề không thể tự khắc phục, vui lòng liên hệ hỗ trợ qua:
- Email: support@example.com
- Telegram: @bot_support
- Discord: discord.gg/bot_support