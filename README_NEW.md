# Advanced Cryptocurrency Trading Bot

Hệ thống bot giao dịch tiền điện tử tự động với khả năng học máy và phân tích thị trường thời gian thực. Hỗ trợ giao dịch đa đồng tiền, thích ứng với điều kiện thị trường, và cung cấp thông báo qua Telegram.

## 🚀 Tính năng chính

- **Phân tích đa khung thời gian**: Kết hợp tín hiệu từ nhiều khung thời gian (15m, 1h, 4h, 1d) để tìm điểm vào lệnh tối ưu
- **Học máy thích ứng**: Tự động huấn luyện và cập nhật mô hình ML theo chế độ thị trường
- **Chỉ báo tổng hợp**: Kết hợp 9 chỉ báo kỹ thuật (RSI, MACD, Bollinger Bands...) với trọng số động
- **Phân tích thanh khoản**: Phát hiện các vùng tập trung lệnh chờ và cơ hội giao dịch
- **Quản lý rủi ro thông minh**: Tự động điều chỉnh kích thước vị thế theo biến động thị trường
- **Thông báo Telegram**: Gửi tín hiệu giao dịch, báo cáo hiệu suất và cảnh báo tới Telegram
- **Backtest tích hợp**: Kiểm tra hiệu suất chiến lược với dữ liệu lịch sử
- **Hỗ trợ đa đồng tiền**: Giao dịch đồng thời nhiều cặp tiền (BTC, ETH, BNB, SOL...)

## 📊 Các chế độ thị trường

Bot tự động phát hiện và thích ứng với 6 chế độ thị trường:
- **Trending Up**: Xu hướng tăng rõ ràng, tăng tỉ lệ risk/reward
- **Trending Down**: Xu hướng giảm rõ ràng, thích hợp cho vị thế Short
- **Ranging**: Thị trường đi ngang, thích hợp cho chiến lược biên độ
- **Volatile**: Biến động cao, giảm kích thước vị thế và tăng khoảng cách stop loss
- **Breakout**: Phá vỡ kháng cự/hỗ trợ, tìm cơ hội theo xu hướng mới
- **Neutral**: Không có xu hướng rõ ràng, thận trọng với các giao dịch

## 🔧 Cài đặt

### Yêu cầu
- Python 3.8+
- Tài khoản Binance Futures (hoặc testnet)
- Khóa API Binance với quyền giao dịch

### Thiết lập
1. Clone repository
```
git clone <repository_url>
cd crypto-trading-bot
```

2. Cài đặt thư viện
```
pip install -r requirements.txt
```

3. Thiết lập biến môi trường
```
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"
```

4. Cấu hình Telegram (tùy chọn)
```
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_telegram_chat_id"
```

## 🚀 Sử dụng

### Chạy bot đa đồng tiền
```
./start_multi_coin_bot.sh
```

### Chạy bot trong chế độ thực tế
```
./start_multi_coin_bot.sh --live
```

### Thay đổi thời gian giữa các lần kiểm tra
```
./start_multi_coin_bot.sh --interval 180  # 3 phút
```

### Cấu hình
Chỉnh sửa `multi_coin_config.json` để thay đổi:
- Cặp giao dịch và tham số
- Cài đặt quản lý rủi ro
- Tần suất thông báo
- Thông số học máy và chiến lược

## 📦 Cấu trúc dự án

```
├── multi_coin_trading.py      # Bot giao dịch đa đồng tiền 
├── start_multi_coin_bot.sh    # Script khởi động bot
├── multi_coin_config.json     # Cấu hình bot và chiến lược
├── run_live_trading.py        # Bot giao dịch đơn đồng tiền
├── telegram_notify.py         # Hệ thống thông báo Telegram
├── app/
│   ├── binance_api.py         # Tích hợp Binance API
│   ├── data_processor.py      # Xử lý dữ liệu và tính toán chỉ báo
│   ├── advanced_ml_optimizer.py  # ML model optimization
│   ├── market_regime_detector.py # Phát hiện chế độ thị trường
│   └── composite_indicator.py # Chỉ báo tổng hợp
├── models/                    # Thư mục lưu mô hình ML
└── backtest_charts/           # Biểu đồ và kết quả backtest
```

## 🖥️ Web Dashboard

Bot được cung cấp kèm theo giao diện web để theo dõi:
- Tín hiệu giao dịch thời gian thực
- Vị thế đang mở và lịch sử giao dịch
- Hiệu suất theo thời gian
- Thông số thị trường và phân tích kỹ thuật

Để khởi động dashboard:
```
python main.py
```

Truy cập: http://localhost:5000

## ⚠️ Cảnh báo rủi ro

Giao dịch tiền điện tử luôn tiềm ẩn rủi ro mất vốn. Bot này được cung cấp cho mục đích giáo dục và thử nghiệm, không phải lời khuyên tài chính. Luôn bắt đầu với số tiền nhỏ và thử nghiệm kỹ lưỡng trước khi sử dụng số tiền lớn.

## 📃 Giấy phép

MIT