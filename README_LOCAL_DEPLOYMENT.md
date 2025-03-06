# Hướng Dẫn Triển Khai Bot Trading Trên Máy Local

## 1. Giới Thiệu

Tài liệu này hướng dẫn chi tiết cách triển khai Adaptive Crypto Trading Bot trên máy tính cá nhân của bạn sau khi đã phát triển và kiểm thử thành công trên Replit.

## 2. Yêu Cầu Hệ Thống

- Python 3.8+
- Git
- Kết nối internet ổn định
- Tài khoản Binance (Testnet hoặc Mainnet)
- Tài khoản Telegram (nếu sử dụng thông báo)

## 3. Các Bước Triển Khai

### 3.1 Clone Dự Án

```bash
git clone <url_repo_của_bạn>
cd <thư_mục_dự_án>
```

### 3.2 Cài Đặt Môi Trường

Tạo môi trường ảo và cài đặt các thư viện cần thiết:

```bash
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 Cấu Hình Môi Trường

1. Tạo file `.env` từ file mẫu:

```bash
cp .env.example .env
```

2. Cập nhật các thông tin cấu hình trong file `.env`:

```
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
AUTO_START_BOT=false
AUTO_RESTART_BOT=false
```

### 3.4 Kiểm Tra Cấu Hình Tài Khoản

Kiểm tra file `account_config.json` và cập nhật các thông số cho phù hợp với nhu cầu giao dịch của bạn:

```json
{
    "account_type": "futures",
    "api_mode": "testnet",  // Đổi thành "live" khi sẵn sàng giao dịch thật
    "symbols": ["BTCUSDT", "ETHUSDT", ...],
    "timeframes": ["1m", "5m", "15m", "1h", "4h", "1d"],
    "leverage": 5,
    "risk_per_trade": 1.0
}
```

### 3.5 Kiểm Tra Cấu Hình Bot

Kiểm tra file `bot_config.json` để đảm bảo các chiến lược và cài đặt quản lý rủi ro phù hợp:

```json
{
    "strategies": {
        "trend_following": {
            "enabled": true,
            "weight": 1.0
        },
        "mean_reversion": {
            "enabled": true,
            "weight": 0.7
        },
        "breakout": {
            "enabled": true,
            "weight": 0.8
        }
    },
    "risk_management": {
        "max_position_size_pct": 10,
        "max_daily_drawdown_pct": 5,
        "default_stop_loss_pct": 2.5,
        "default_take_profit_pct": 5.0
    }
}
```

## 4. Khởi Động Bot

### 4.1 Khởi Động Thủ Công Qua CLI

```bash
python cli_controller.py --start
```

Hoặc khởi động với chế độ monitor:

```bash
python cli_controller.py --monitor 5
```

### 4.2 Kiểm Tra Trạng Thái Bot

Kiểm tra xem bot đã khởi động thành công chưa:

```bash
python check_strategy_status.py
```

Kiểm tra các vị thế hiện tại:

```bash
python check_positions.py
```

## 5. Các Lệnh Quản Lý Bot

### 5.1 Xem Thông Tin Thị Trường

```bash
python check_market.py
```

### 5.2 Xem Chiến Lược Đang Áp Dụng

```bash
python check_strategies.py
```

### 5.3 Xem Vị Thế Đang Mở

```bash
python check_positions.py
```

### 5.4 Xem Lịch Sử Giao Dịch

```bash
python check_trades.py
```

### 5.5 Dừng Bot

```bash
python cli_controller.py --stop
```

## 6. Cấu Hình Chạy Liên Tục

### 6.1 Sử Dụng Screen (Linux/Mac)

```bash
screen -S trading_bot
python cli_controller.py --start
# Nhấn Ctrl+A, sau đó nhấn D để thoát khỏi screen
# Để quay lại screen: screen -r trading_bot
```

### 6.2 Sử Dụng Systemd (Linux)

Tạo file service:

```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Nội dung file:

```
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/your/project/venv/bin/python cli_controller.py --start
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Kích hoạt service:

```bash
sudo systemctl enable trading-bot.service
sudo systemctl start trading-bot.service
sudo systemctl status trading-bot.service
```

## 7. Theo Dõi Và Bảo Trì

### 7.1 Kiểm Tra Logs

```bash
tail -f trading_bot.log
```

### 7.2 Cập Nhật Bot

```bash
git pull origin main
pip install -r requirements.txt
```

### 7.3 Backup Dữ Liệu

Thường xuyên sao lưu các file cấu hình và dữ liệu giao dịch:

```bash
# Tạo thư mục backup
mkdir -p backups/$(date +%Y%m%d)
# Sao lưu các file quan trọng
cp *.json .env backups/$(date +%Y%m%d)/
cp -r data backups/$(date +%Y%m%d)/
```

## 8. Xử Lý Sự Cố

### 8.1 Bot Không Khởi Động

- Kiểm tra logs: `cat trading_bot.log`
- Kiểm tra API keys trong `.env`
- Đảm bảo kết nối internet ổn định

### 8.2 Lỗi Kết Nối Binance

- Kiểm tra API keys trong `.env`
- Kiểm tra timezone máy tính
- Đảm bảo IP của bạn không bị chặn bởi Binance

### 8.3 Bot Khởi Động Nhưng Không Giao Dịch

- Kiểm tra cấu hình `bot_config.json`
- Kiểm tra chế độ thị trường hiện tại
- Kiểm tra tín hiệu giao dịch hiện tại

## 9. Chuyển Từ Testnet Sang Mainnet

Khi bạn đã kiểm tra kỹ và sẵn sàng giao dịch thật:

1. Cập nhật file `account_config.json`, thay đổi `api_mode` từ `testnet` thành `live`
2. Cập nhật API keys trong `.env` thành keys của tài khoản thật
3. Xem lại cấu hình quản lý rủi ro trong `bot_config.json`
4. Bắt đầu với số tiền nhỏ và tăng dần khi bot chứng minh được hiệu quả

## 10. Khuyến Nghị Bổ Sung

1. **Theo dõi hiệu suất**: Thường xuyên kiểm tra hiệu suất bot và điều chỉnh nếu cần.
2. **Đặt cảnh báo**: Cấu hình thông báo Telegram để nhận cảnh báo khi có sự cố.
3. **Khởi động từ từ**: Bắt đầu với ít cặp tiền và tăng dần khi bot hoạt động ổn định.
4. **Kiểm tra thường xuyên**: Theo dõi hàng ngày, đặc biệt trong thời gian đầu triển khai.

## 11. Tài Liệu Liên Quan

- [README_CLI.md](README_CLI.md): Hướng dẫn sử dụng CLI
- [README_DEPLOYMENT.md](README_DEPLOYMENT.md): Hướng dẫn triển khai tổng quát
- [README_MARKET_ANALYSIS.md](README_MARKET_ANALYSIS.md): Hướng dẫn phân tích thị trường
- [README_TRAILING_STOP.md](README_TRAILING_STOP.md): Hướng dẫn về trailing stop