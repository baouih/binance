# Hướng Dẫn Vận Hành Bot 24/7

Tài liệu này hướng dẫn cách thiết lập và vận hành bot giao dịch liên tục 24/7 mà không cần giám sát thường xuyên. Hệ thống có khả năng tự phục hồi khi xảy ra lỗi và tự động khởi động lại khi hệ thống khởi động lại.

## Mục Lục

1. [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
2. [Cách Vận Hành Bot 24/7](#cách-vận-hành-bot-247)
3. [Chức Năng Tự Phục Hồi](#chức-năng-tự-phục-hồi)
4. [Chạy Bot Như Dịch Vụ Hệ Thống](#chạy-bot-như-dịch-vụ-hệ-thống)
5. [Theo Dõi và Giám Sát](#theo-dõi-và-giám-sát)
6. [Xử Lý Sự Cố](#xử-lý-sự-cố)
7. [Kết Nối Thông Báo Telegram](#kết-nối-thông-báo-telegram)

## Yêu Cầu Hệ Thống

- **Phần Cứng Tối Thiểu**:
  - CPU: 2 nhân, 2.0 GHz
  - RAM: 4GB
  - Ổ cứng: 20GB trống
  - Kết nối internet ổn định

- **Hệ Điều Hành**:
  - Windows 10/11
  - Linux (Ubuntu 20.04+, CentOS 8+)
  - macOS 10.15+

- **Phần Mềm Yêu Cầu**:
  - Python 3.9+
  - Tất cả các thư viện đã được cài đặt (xem `requirements.txt`)
  - Quyền admin để cài đặt dịch vụ hệ thống (tùy chọn)

## Cách Vận Hành Bot 24/7

Có ba cách chính để vận hành bot 24/7:

### 1. Sử dụng Auto Restart Guardian

`auto_restart_guardian.py` là thành phần giám sát bot, tự động phát hiện và khởi động lại bot khi gặp lỗi.

```bash
# Khởi động với cấu hình mặc định
python auto_restart_guardian.py

# Khởi động với mức rủi ro cụ thể
python auto_restart_guardian.py --risk-level 20

# Khởi động với các tùy chọn bổ sung
python auto_restart_guardian.py --max-restarts 10 --check-interval 30
```

Các tham số:
- `--risk-level`: Mức rủi ro (10, 15, 20, 30)
- `--max-restarts`: Số lần khởi động lại tối đa trong 1 giờ (mặc định: 5)
- `--check-interval`: Thời gian kiểm tra trạng thái (giây, mặc định: 60)

### 2. Sử dụng Giao Diện Desktop

1. Khởi động giao diện desktop:
   ```bash
   python bot_gui.py
   ```

2. Trong giao diện, chọn tab "Cấu Hình"
3. Chọn mức rủi ro phù hợp
4. Nhấn "Khởi Động" để bắt đầu bot
5. Bật tùy chọn "Tự động khởi động lại khi gặp lỗi" để bot luôn hoạt động

### 3. Chạy File Thực Thi (EXE)

Nếu bạn đã biên dịch file thực thi:

1. Chạy file `TradingBot.exe`
2. Làm theo các bước tương tự như khi sử dụng giao diện desktop

## Chức Năng Tự Phục Hồi

Bot được trang bị các cơ chế tự phục hồi:

1. **Phát Hiện Lỗi**: Giám sát liên tục các lỗi và sự cố
2. **Khôi Phục Vị Thế**: Khi khởi động lại, bot sẽ tự động phục hồi thông tin về các vị thế đang mở
3. **Giới Hạn Khởi Động Lại**: Tối đa 5 lần/giờ để tránh vòng lặp lỗi
4. **Log Chi Tiết**: Ghi lại mọi lỗi và hành động khôi phục để phân tích sau

## Chạy Bot Như Dịch Vụ Hệ Thống

Để chạy bot như một dịch vụ hệ thống, chạy script cài đặt:

```bash
# Trên Windows, chạy với quyền Administrator
python setup_24_7_service.py

# Trên Linux/macOS, chạy với quyền root
sudo python setup_24_7_service.py

# Tùy chỉnh tên dịch vụ và mức rủi ro
python setup_24_7_service.py --name my_trading_bot --risk-level 15
```

Các tham số:
- `--name`: Tên dịch vụ (mặc định: trading_bot)
- `--description`: Mô tả dịch vụ
- `--no-auto-start`: Không tự động khởi động khi hệ thống khởi động
- `--risk-level`: Mức rủi ro (10, 15, 20, 30)

### Quản Lý Dịch Vụ

**Windows**:
```bash
# Xem trạng thái
sc query trading_bot

# Dừng dịch vụ
net stop trading_bot

# Khởi động dịch vụ
net start trading_bot
```

**Linux**:
```bash
# Xem trạng thái
systemctl status trading_bot

# Dừng dịch vụ
sudo systemctl stop trading_bot

# Khởi động dịch vụ
sudo systemctl start trading_bot
```

**macOS**:
```bash
# Xem trạng thái
launchctl list | grep trading_bot

# Dừng dịch vụ
sudo launchctl unload /Library/LaunchDaemons/com.trading_bot.plist

# Khởi động dịch vụ
sudo launchctl load -w /Library/LaunchDaemons/com.trading_bot.plist
```

## Theo Dõi và Giám Sát

### Kiểm Tra Trạng Thái

Bot tạo các file trạng thái có thể kiểm tra:

1. **Trạng thái Guardian**: File `guardian_status.json` chứa thông tin về uptime, số lần khởi động lại, và trạng thái hiện tại của bot
2. **Logs**: Thư mục `logs` chứa nhật ký hoạt động chi tiết

### Theo Dõi Từ Xa

Để theo dõi từ xa, bot hỗ trợ:

1. **Thông báo Telegram**: Gửi cập nhật trạng thái và cảnh báo
2. **API Web**: Truy vấn trạng thái qua HTTP (nếu kích hoạt)

## Xử Lý Sự Cố

### Vấn Đề Phổ Biến

1. **Bot liên tục khởi động lại**:
   - Kiểm tra logs để xác định nguyên nhân
   - Tắt cấu hình rủi ro cao nếu thị trường biến động mạnh
   - Kiểm tra kết nối API

2. **Vấn đề kết nối API**:
   - Kiểm tra thông tin API key/secret
   - Xác minh mạng internet hoạt động bình thường
   - Kiểm tra trạng thái sàn giao dịch

3. **Sử dụng CPU/RAM cao**:
   - Giảm số lượng cặp tiền theo dõi
   - Tăng khoảng thời gian kiểm tra
   - Xóa bớt log cũ

### Khởi Động Lại Thủ Công

Nếu cần khởi động lại bot thủ công:

```bash
# Dừng bot hiện tại
python stop_bot.py

# Khởi động lại với Guardian
python auto_restart_guardian.py
```

## Kết Nối Thông Báo Telegram

Để nhận thông báo qua Telegram:

1. Cài đặt biến môi trường hoặc thêm vào file `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

2. Kích hoạt thông báo trong cấu hình:
   ```bash
   python bot_startup.py --enable-telegram
   ```

3. Kiểm tra kết nối:
   ```bash
   python test_telegram_notification.py
   ```

## Kiểm Tra Hệ Thống

Trước khi chạy bot 24/7, nên chạy kiểm tra:

```bash
# Kiểm tra nhanh (60 giây)
python run_bot_test.py --duration 60

# Kiểm tra kỹ (1 giờ)
python run_bot_test.py --duration 3600 --risk-level 30
```

Kết quả kiểm tra sẽ cho biết liệu bot có hoạt động ổn định không và ghi lại mọi vấn đề để tham khảo.

---

## Ghi Chú Quan Trọng

- **Backup Dữ Liệu**: Lưu trữ cấu hình và thông tin quan trọng
- **Theo Dõi Sự Biến Động**: Thị trường tiền điện tử biến động mạnh, giám sát thường xuyên
- **Luôn Cập Nhật**: Cập nhật bot khi có phiên bản mới để có tính năng và bảo mật tốt nhất

---

*Nếu bạn có bất kỳ câu hỏi hoặc vấn đề nào, vui lòng tham khảo tài liệu đầy đủ hoặc liên hệ với đội hỗ trợ.*