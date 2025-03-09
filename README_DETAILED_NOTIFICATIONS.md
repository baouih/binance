# Thông Báo Chi Tiết Cho Hệ Thống Giao Dịch

Module thông báo chi tiết cung cấp các thông tin đầy đủ về hoạt động của bot giao dịch qua Telegram, giúp người dùng nắm bắt được tình hình giao dịch một cách chính xác và kịp thời.

## Các tính năng chính

1. **Thông báo vào lệnh chi tiết**
   - Symbol, Side (LONG/SHORT), Giá vào, Số lượng
   - Đòn bẩy, Take Profit, Stop Loss
   - Lý do vào lệnh với các chỉ báo kỹ thuật
   - Tỷ lệ Risk/Reward

2. **Thông báo ra lệnh chi tiết**
   - Giá vào, Giá ra, Số lượng
   - Lợi nhuận/Lỗ (số tiền và phần trăm)
   - Thời gian giữ lệnh
   - Lý do đóng lệnh

3. **Thống kê giao dịch**
   - Tổng số giao dịch trong ngày
   - Số lệnh thắng/thua
   - Tỷ lệ thắng, Lợi nhuận ròng
   - Các giao dịch gần đây nhất

4. **Tóm tắt tài khoản**
   - Tổng số dư, Số dư khả dụng
   - Lợi nhuận đã/chưa thực hiện
   - Các vị thế đang mở

## Cách sử dụng

Để khởi động hệ thống thông báo chi tiết, chạy lệnh sau:

```bash
python start_detailed_notifications.py
```

### Các tham số tùy chọn

- `--config`: Đường dẫn tới file cấu hình (mặc định: account_config.json)
- `--notify-interval`: Khoảng thời gian gửi thông báo định kỳ (phút, mặc định: 15)
- `--daemonize`: Chạy như daemon trong nền

Ví dụ:

```bash
# Gửi thông báo mỗi 5 phút
python start_detailed_notifications.py --notify-interval 5

# Chạy như daemon trong nền
python start_detailed_notifications.py --daemonize
```

## Cấu trúc thông báo

### Thông báo vào lệnh

```
🟢 VÀO LỆNH - LONG BTCUSDT 🟢

💵 Giá vào: 85000
🔢 Số lượng: 0.01
⚡ Đòn bẩy: 5x
💰 Margin: 170.00 USDT

🎯 Take Profit: 87000 (2.35%)
🛑 Stop Loss: 84000 (1.18%)
⚖️ Tỷ lệ Risk/Reward: 1:2.00

🔍 LÝ DO VÀO LỆNH:
RSI vượt ngưỡng 30 từ dưới lên, MACD cho tín hiệu cắt lên, đường giá vượt MA20

📊 CHỈ BÁO:
  • RSI: 32.50
  • MACD: Tín hiệu dương
  • MA20: 84500

Thời gian: 10:15:30 09/03/2025
```

### Thông báo ra lệnh

```
✅ ĐÓNG LỆNH - LONG BTCUSDT ✅

💵 Giá vào: 85000
💵 Giá ra: 86500
🔢 Số lượng: 0.01
⚡ Đòn bẩy: 5x

📈 Lợi nhuận: 150.00 USDT (1.76%)
⏱️ Thời gian giữ: 2 giờ 30 phút

🔍 LÝ DO ĐÓNG LỆNH:
Đạt mục tiêu lợi nhuận 80%, RSI vượt ngưỡng 70, thị trường có dấu hiệu đảo chiều

📅 TỔNG KẾT:
  • Thời gian vào: 10:15:30 09/03/2025
  • Thời gian ra: 12:45:30 09/03/2025
  • Kết quả: Lãi 150.00 USDT

Thời gian: 12:45:30 09/03/2025
```

### Thống kê giao dịch

```
📊 THỐNG KÊ GIAO DỊCH NGÀY 09/03/2025 📊

🔢 Tổng số giao dịch: 5
✅ Số lệnh thắng: 3
❌ Số lệnh thua: 2
📈 Tỷ lệ thắng: 60.00%

💰 Tổng lợi nhuận: 450.00 USDT
💸 Tổng lỗ: 200.00 USDT
📈 Lợi nhuận ròng: 250.00 USDT

🕒 CÁC GIAO DỊCH GẦN ĐÂY:
  • ✅ LONG BTCUSDT: 150.00 USDT (1.76%)
  • ❌ SHORT ETHUSDT: -80.00 USDT (-0.75%)
  • ✅ LONG SOLUSDT: 120.00 USDT (2.15%)
  • ✅ LONG BNBUSDT: 180.00 USDT (1.52%)
  • ❌ SHORT XRPUSDT: -120.00 USDT (-1.10%)

Cập nhật: 20:00:00 09/03/2025
```

### Tóm tắt tài khoản

```
💼 TÓM TẮT TÀI KHOẢN 💼

💵 Tổng số dư: 13500.00 USDT
💰 Số dư khả dụng: 13000.00 USDT
💹 Số dư margin: 13500.00 USDT

📈 Lợi nhuận chưa thực hiện: 250.00 USDT
📈 Lợi nhuận đã thực hiện: 500.00 USDT

📊 VỊ THẾ ĐANG MỞ (1):
  • 🟢 LONG ETHUSDT: 1.40%

Cập nhật: 15:30:00 09/03/2025
```

## Tích hợp với hệ thống hiện tại

Hệ thống thông báo chi tiết được tích hợp với hệ thống giao dịch hiện tại thông qua các module:

1. `detailed_trade_notifications.py`: Module chính xử lý thông báo chi tiết
2. `integrate_detailed_notifications.py`: Tích hợp với API Binance để theo dõi vị thế
3. `start_detailed_notifications.py`: Script khởi động hệ thống

## Lưu ý

1. Đảm bảo `TELEGRAM_TOKEN` và `TELEGRAM_CHAT_ID` đã được cấu hình trong file `.env` hoặc `telegram_config.json`.
2. Hệ thống thông báo chi tiết có thể chạy song song với hệ thống giao dịch chính.
3. Các file lịch sử giao dịch được lưu trong `trade_history.json` để thống kê.