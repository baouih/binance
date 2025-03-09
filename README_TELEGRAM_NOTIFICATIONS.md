# Hệ thống Thông báo Telegram

Hệ thống Thông báo Telegram cung cấp các cập nhật thời gian thực về hoạt động giao dịch, biến động thị trường, và trạng thái vị thế thông qua Telegram. Tính năng này giúp bạn luôn cập nhật thông tin về hệ thống giao dịch của mình kể cả khi không ở trước máy tính.

## Tính năng chính

1. **Thông báo tín hiệu giao dịch:** Nhận thông báo khi có tín hiệu giao dịch mới hoặc khi SL/TP được thiết lập
2. **Cảnh báo biến động giá:** Thông báo khi giá có biến động mạnh hoặc đột phá khỏi ngưỡng quan trọng
3. **Cập nhật vị thế:** Báo cáo định kỳ về vị thế hiện tại và lợi nhuận
4. **Thông báo SL/TP:** Cập nhật khi Stop Loss hoặc Take Profit được thay đổi
5. **Thông báo hệ thống:** Thông báo về trạng thái hệ thống, thời gian hoạt động, và số dư tài khoản

## Cài đặt Bot Telegram

### Bước 1: Tạo Bot Telegram
1. Mở Telegram và tìm kiếm "@BotFather"
2. Gửi tin nhắn `/newbot` để tạo bot mới
3. Đặt tên cho bot (ví dụ: "Trading Assistant")
4. Chọn username cho bot (phải kết thúc bằng "bot", ví dụ: "my_trading_assistant_bot")
5. BotFather sẽ cung cấp một **token API**. Lưu token này lại, bạn sẽ cần nó cho cấu hình.

### Bước 2: Lấy Chat ID
1. Tìm kiếm bot của bạn trong Telegram (theo username đã đặt)
2. Nhấn "Start" để bắt đầu cuộc trò chuyện
3. Gửi tin nhắn bất kỳ cho bot
4. Mở URL sau trên trình duyệt (thay `YOUR_BOT_TOKEN` bằng token của bạn):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
5. Tìm giá trị `"chat":{"id":XXXXXXXXX}` trong kết quả JSON
6. `XXXXXXXXX` chính là **Chat ID** của bạn

### Bước 3: Cấu hình hệ thống thông báo
1. Mở file `configs/telegram_config.json`
2. Cập nhật các giá trị sau:
   ```json
   {
       "bot_token": "YOUR_BOT_TOKEN",
       "chat_id": "YOUR_CHAT_ID",
       ...
   }
   ```
3. Lưu file

## Sử dụng

### Khởi động tích hợp Auto SL/TP với Telegram

```bash
chmod +x auto_start_sltp_telegram.sh
./auto_start_sltp_telegram.sh
```

Script này sẽ:
- Khởi động hệ thống Auto SL/TP Manager tích hợp với Telegram
- Gửi thông báo khởi động tới Telegram
- Tự động quản lý và cập nhật SL/TP với thông báo qua Telegram

### Kiểm tra trạng thái

```bash
# Xem log
tail -f sltp_telegram_integration.log

# Kiểm tra tiến trình
ps -p $(cat sltp_telegram_integration.pid)
```

### Dừng hệ thống

```bash
kill $(cat sltp_telegram_integration.pid)
```

## Tùy chỉnh thông báo

Bạn có thể tùy chỉnh loại thông báo và tần suất trong file `configs/telegram_config.json`:

```json
"notification_settings": {
    "enable_trade_signals": true,       // Thông báo tín hiệu giao dịch
    "enable_price_alerts": true,        // Cảnh báo biến động giá
    "enable_position_updates": true,    // Cập nhật vị thế
    "enable_sltp_alerts": true,         // Thông báo SL/TP
    "min_price_change_percent": 3.0,    // % thay đổi giá tối thiểu để cảnh báo
    "price_alert_cooldown": 3600,       // Thời gian giữa các cảnh báo giá (giây)
    "position_update_interval": 3600,   // Thời gian giữa các cập nhật vị thế (giây)
    "max_notifications_per_hour": 20,   // Số lượng thông báo tối đa mỗi giờ
    "quiet_hours_start": 0,             // Giờ bắt đầu thời gian im lặng (0-23)
    "quiet_hours_end": 0                // Giờ kết thúc thời gian im lặng (0-23)
}
```

## Loại thông báo

### 1. Thông báo tín hiệu giao dịch
```
🚨 TÍN HIỆU GIAO DỊCH MỚI 🚨

Cặp: BTCUSDT
Hướng: 🟢 LONG
Giá vào lệnh: 85000.00
Stop Loss: 83000.00
Take Profit: 89000.00
Risk/Reward: 1:2.00
Khung thời gian: 1h
Chiến lược: Composite Strategy
Độ tin cậy: ⭐⭐⭐⭐ (75.0%)

💡 Đặt SL/TP theo mức được gợi ý để đảm bảo quản lý vốn!
```

### 2. Cảnh báo biến động giá
```
📈 CẢNH BÁO GIÁ BTCUSDT 📈

Giá hiện tại: 86000
Thay đổi: +5.20%
Khung thời gian: 15m
Lý do: Breakout detected

Cảnh báo này dựa trên các thay đổi đáng kể về giá.
```

### 3. Cập nhật vị thế
```
📊 CẬP NHẬT VỊ THẾ

Vị thế đang mở: 3

🟢 BTCUSDT 📈 LONG
   Size: 0.0250 (2125.00 USDT)
   Entry: 85000.00 | Mark: 86000.00
   P/L: +25.00 USDT (+1.18%)
🔴 ETHUSDT 📉 SHORT
   Size: 1.5000 (3150.00 USDT)
   Entry: 2200.00 | Mark: 2210.00
   P/L: -15.00 USDT (-0.45%)

Số dư tài khoản: 13500.00 USDT
Tổng vị thế: 5275.00 USDT
Tỷ lệ margin: 39.07%
Unrealized P/L: +10.00 USDT
P/L ngày: +120.50 USDT (+0.89%)
```

### 4. Thông báo SL/TP
```
🔄 CẬP NHẬT SL/TP 🔄

Cặp: BTCUSDT
Hướng: 📈 LONG
Stop Loss: 83000.00 ➡️ 83500.00
Lý do: Trailing Stop

Hệ thống đã tự động điều chỉnh mức SL/TP.
```

## Lưu ý quan trọng

- Đảm bảo rằng bot của bạn đã được bật và mã token là chính xác
- Kiểm tra thường xuyên để đảm bảo hệ thống thông báo hoạt động
- Thiết lập "quiet hours" nếu bạn không muốn nhận thông báo vào những khung giờ nhất định
- Sử dụng `max_notifications_per_hour` để tránh spam thông báo khi thị trường biến động mạnh
- Cân nhắc thiết lập `min_price_change_percent` cao hơn trong thị trường biến động để giảm số lượng thông báo