# Hướng Dẫn Triển Khai Bot Trading Trên Máy Local

## Báo Cáo Kiểm Tra Cuối Cùng

Đã hoàn thành kiểm tra toàn diện hệ thống giao dịch adaptive crypto trading bot và xác nhận tất cả các hệ thống đang hoạt động bình thường. Dưới đây là thông tin tổng quan:

### Tài Khoản
- **Số dư tài khoản testnet**: 13,571.16 USDT
- **Loại tài khoản**: Futures
- **Chế độ API**: Testnet
- **Đòn bẩy**: 5x
- **Rủi ro mỗi giao dịch**: 1.0%

### Cặp Tiền Đang Theo Dõi
Bot đang theo dõi 14 cặp tiền:
- BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, SOLUSDT
- DOGEUSDT, XRPUSDT, LINKUSDT, AVAXUSDT, DOTUSDT
- MATICUSDT, LTCUSDT, ATOMUSDT, UNIUSDT

### Chiến Lược Giao Dịch
- **Chiến lược đang hoạt động**: trend_following, mean_reversion, breakout, momentum
- **Chế độ thị trường hiện tại**: ranging
- **Tham số chiến lược**: Đã được tối ưu hóa cho từng chế độ thị trường

### Kiểm Tra Hệ Thống
- **Kết nối API**: OK
- **Dữ liệu thị trường**: Đang cập nhật đúng
- **Phát hiện chế độ thị trường**: Hoạt động chính xác
- **Hệ thống quản lý rủi ro**: Đã cấu hình đúng

## Các Bước Triển Khai Local

### 1. Sao Chép Dự Án Về Máy Local

```bash
# Clone repository về máy
git clone <URL_REPOSITORY>

# Di chuyển vào thư mục dự án
cd adaptive-crypto-trading-bot
```

### 2. Cài Đặt Môi Trường

```bash
# Tạo môi trường ảo Python
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows:
venv\Scripts\activate
# Trên MacOS/Linux:
source venv/bin/activate

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 3. Cấu Hình Biến Môi Trường

Tạo file `.env` từ mẫu:

```bash
cp .env.example .env
```

Cập nhật các thông tin trong file `.env`:
```
BINANCE_API_KEY=API_KEY_CỦA_BẠN
BINANCE_API_SECRET=API_SECRET_CỦA_BẠN

# Telegram notifications (tùy chọn)
TELEGRAM_BOT_TOKEN=TOKEN_BOT_TELEGRAM
TELEGRAM_CHAT_ID=CHAT_ID_TELEGRAM

# Bot control settings
AUTO_START_BOT=false
AUTO_RESTART_BOT=false
```

### 4. Kiểm Tra Trước Khi Khởi Động

```bash
# Kiểm tra kết nối API
python check_positions_simple.py

# Kiểm tra dữ liệu thị trường
python check_market.py
```

### 5. Khởi Động Bot

```bash
# Sử dụng CLI Controller
python cli_controller.py --start
```

Hoặc sử dụng chế độ monitor để theo dõi liên tục:
```bash
python cli_controller.py --monitor 5  # Cập nhật mỗi 5 giây
```

### 6. Chạy Bot Liên Tục

#### Sử dụng Screen (Linux/MacOS)
```bash
screen -S trading_bot
python cli_controller.py --start
# Nhấn Ctrl+A, sau đó nhấn D để thoát khỏi screen
```

#### Sử dụng Nohup (Linux/MacOS)
```bash
nohup python cli_controller.py --start > trading_bot_output.log 2>&1 &
```

#### Windows Task Scheduler
Tạo task chạy file batch (.bat) với nội dung:
```
@echo off
cd /d "đường_dẫn_đến_thư_mục_dự_án"
call venv\Scripts\activate
python cli_controller.py --start
```

## Các Lệnh Hữu Ích

```bash
# Kiểm tra trạng thái bot
python check_strategy_status.py

# Xem vị thế hiện tại
python check_positions.py

# Xem thông tin thị trường
python check_market.py

# Kiểm tra chiến lược
python check_strategies.py

# Dừng bot
python cli_controller.py --stop
```

## Lưu Ý Quan Trọng

1. **Chế độ testnet vs mainnet**: Mặc định, bot đang chạy ở chế độ testnet. Để chuyển sang giao dịch thật, cần thay đổi `api_mode` trong file `account_config.json` từ "testnet" thành "live" và cập nhật API keys thật trong file `.env`.

2. **Quản lý rủi ro**: Nên bắt đầu với số tiền nhỏ khi chuyển sang giao dịch thật và theo dõi kỹ hiệu suất trong thời gian đầu.

3. **Backup dữ liệu**: Thường xuyên sao lưu các file cấu hình (`account_config.json`, `bot_config.json`) và dữ liệu giao dịch trong thư mục `data/`.

4. **Kiểm tra logs**: Kiểm tra file logs `trading_bot.log` và `cli_controller.log` nếu gặp vấn đề.

## Tài Liệu Tham Khảo

- [README_CLI.md](README_CLI.md) - Hướng dẫn sử dụng CLI đầy đủ
- [README_DEPLOYMENT.md](README_DEPLOYMENT.md) - Hướng dẫn triển khai chi tiết
- [README_LOCAL_DEPLOYMENT.md](README_LOCAL_DEPLOYMENT.md) - Hướng dẫn triển khai local đầy đủ

Chi tiết hơn về các chức năng và cách sử dụng bot, vui lòng tham khảo tài liệu README đi kèm.