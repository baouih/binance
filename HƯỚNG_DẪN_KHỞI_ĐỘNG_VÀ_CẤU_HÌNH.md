# HƯỚNG DẪN KHỞI ĐỘNG VÀ CẤU HÌNH HỆ THỐNG GIAO DỊCH

## 1. TỔNG QUAN HỆ THỐNG

Hệ thống giao dịch crypto cung cấp các chức năng:
- Phân tích thị trường tự động
- Giao dịch tự động theo chiến lược
- Quản lý rủi ro thích ứng
- Thông báo Telegram thời gian thực
- Giao diện đồ họa (desktop) và web

## 2. KHỞI ĐỘNG HỆ THỐNG

### 2.1. Khởi động tất cả dịch vụ

Cách đơn giản nhất để khởi động toàn bộ hệ thống:

```bash
python start_all_services.py
```

Script này sẽ khởi động:
- Market Notifier (auto_market_notifier.py)
- Unified Trading Service (unified_trading_service.py)

### 2.2. Khởi động riêng từng dịch vụ

Nếu bạn muốn khởi động từng dịch vụ riêng lẻ:

#### 2.2.1. Market Analyzer

```bash
python activate_market_analyzer.py
```

#### 2.2.2. Trading Bot

```bash
python run_bot.py
```

#### 2.2.3. Risk Manager

```bash
python risk_manager.py
```

### 2.3. Khởi động giao diện đồ họa

```bash
python run_desktop_app.py
```

## 3. CẤU HÌNH HỆ THỐNG

### 3.1. Cấu hình Binance API (Testnet)

Đảm bảo file `account_config.json` đã được cấu hình đúng:

```json
{
  "api_key": "YOUR_BINANCE_TESTNET_API_KEY",
  "api_secret": "YOUR_BINANCE_TESTNET_API_SECRET",
  "testnet": true,
  "exchange": "binance",
  "base_currency": "USDT"
}
```

Hoặc thiết lập biến môi trường:
```
BINANCE_TESTNET_API_KEY=your_key_here
BINANCE_TESTNET_API_SECRET=your_secret_here
```

### 3.2. Cấu hình thông báo Telegram

Để nhận thông báo qua Telegram, cấu hình:

```json
{
  "enable_notifications": true,
  "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "telegram_chat_id": "YOUR_TELEGRAM_CHAT_ID"
}
```

Hoặc thiết lập biến môi trường:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3.3. Cấu hình mức độ rủi ro

Thiết lập mức độ rủi ro trong file `risk_configs/risk_level_XX.json`:

```json
{
  "risk_level": 10,
  "max_open_positions": 3,
  "position_size_percent": 0.1,
  "max_risk_per_trade": 0.1,
  "stop_loss_percent": 2.0,
  "take_profit_percent": 4.0,
  "default_leverage": 3
}
```

## 4. KHẮC PHỤC SỰ CỐ REPLIT

Do Replit không hỗ trợ chạy dịch vụ 24/7, một số giải pháp:

### 4.1. Sử dụng auto_restart.py

```bash
python auto_restart.py
```

Script này sẽ:
- Kiểm tra dịch vụ đang chạy định kỳ
- Khởi động lại dịch vụ khi bị dừng
- Duy trì Replit hoạt động bằng cách tự ping

### 4.2. Tạo file exe chạy trên máy tính

Tham khảo hướng dẫn chi tiết trong `HƯỚNG_DẪN_XUẤT_EXE_CHI_TIẾT.md`

### 4.3. Sử dụng cron job trên máy chủ Linux

Trên máy chủ Linux, có thể dùng cron job để đảm bảo hoạt động 24/7:

```bash
# Mở cron editor
crontab -e

# Thêm dòng này để khởi động lại mỗi giờ
0 * * * * cd /path/to/project && python start_all_services.py >> cron.log 2>&1
```

## 5. KIỂM TRA HỆ THỐNG

### 5.1. Kiểm tra trạng thái dịch vụ

```bash
python check_services.py
```

### 5.2. Kiểm tra API Binance

```bash
python check_binance_api.py
```

### 5.3. Kiểm tra Market Notifier

```bash
python check_market_notifier.py
```

## 6. TẮTHỆ THỐNG AN TOÀN

```bash
python stop_all_services.py
```

## 7. CÁC TÍNH NĂNG NÂNG CAO

### 7.1. Auto Stop Loss & Take Profit

Bật tự động quản lý Stop Loss và Take Profit:

```bash
python auto_sltp_manager.py
```

### 7.2. Trailing Stop

Bật Trailing Stop cho các vị thế:

```bash
python add_trailing_stop_to_positions.py
```

### 7.3. Phân tích thị trường nâng cao

```bash
python run_market_analyzer.py --all-timeframes
```

## 8. CHẾ ĐỘ TESTNET

Hệ thống mặc định hoạt động trên Binance Testnet. Để chuyển sang môi trường thực (mainnet), thay đổi:

```json
{
  "testnet": false
}
```

⚠️ **CẢNH BÁO**: Chỉ chuyển sang mainnet sau khi đã thử nghiệm kỹ lưỡng trên testnet!