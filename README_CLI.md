# BinanceTrader CLI Tool

Công cụ dòng lệnh (CLI) cho hệ thống giao dịch tiền điện tử BinanceTrader.

## Tổng quan

BinanceTrader CLI Tool là một giao diện dòng lệnh giúp quản lý và giám sát bot giao dịch tiền điện tử BinanceTrader. Công cụ này cung cấp khả năng:

- Giám sát trạng thái bot
- Xem thông tin vị thế mở và giao dịch gần đây
- Khởi động/dừng/khởi động lại bot
- Cấu hình các thông số bot
- Xem logs và chỉ số hiệu suất
- Chạy backtest
- Giám sát theo thời gian thực

## Bắt đầu

### Cách khởi động nhanh

Cách đơn giản nhất để bắt đầu sử dụng công cụ là chạy script:

```bash
./run_tool.sh
```

Hoặc trực tiếp:

```bash
python cli_controller.py
```

### Sử dụng tham số dòng lệnh

Bạn cũng có thể sử dụng các tham số dòng lệnh để thực hiện các tác vụ cụ thể:

```bash
# Hiển thị trạng thái bot
python cli_controller.py --status

# Hiển thị vị thế hiện tại
python cli_controller.py --positions

# Hiển thị giao dịch gần đây
python cli_controller.py --trades

# Hiển thị 30 dòng log gần nhất
python cli_controller.py --logs 30

# Khởi động bot
python cli_controller.py --start

# Dừng bot
python cli_controller.py --stop

# Khởi động lại bot
python cli_controller.py --restart

# Giám sát theo thời gian thực với chu kỳ làm mới 10 giây
python cli_controller.py --monitor 10

# Chạy backtest
python cli_controller.py --backtest
```

## Menu tương tác

Khi chạy công cụ mà không có tham số, bạn sẽ được đưa vào menu tương tác với các tùy chọn sau:

### Menu chính

1. **Xem vị thế hiện tại**
2. **Xem giao dịch gần đây**
3. **Xem chỉ số hiệu suất**
4. **Xem logs**
5. **Màn hình giám sát thời gian thực**
- **s**. Khởi động/Dừng bot
- **r**. Khởi động lại bot
- **b**. Chạy backtest
- **c**. Cấu hình bot
- **q**. Thoát

### Menu cấu hình

1. **Bật/Tắt tự động khởi động**
2. **Bật/Tắt tự động khởi động lại**
3. **Cấu hình API key**
4. **Cấu hình thông báo Telegram**
- **b**. Quay lại

## Chế độ giám sát theo thời gian thực

Chế độ giám sát theo thời gian thực cung cấp khả năng theo dõi liên tục trạng thái bot và các vị thế mở. Thông tin sẽ tự động làm mới sau một khoảng thời gian do người dùng thiết lập.

## Biến môi trường

Công cụ sử dụng các biến môi trường từ file `.env` để cấu hình bot. Các biến quan trọng:

- `AUTO_START_BOT`: Tự động khởi động bot khi khởi động server
- `AUTO_RESTART_BOT`: Tự động khởi động lại bot khi bị crash
- `BINANCE_API_KEY`: API key Binance
- `BINANCE_API_SECRET`: API secret Binance
- `TELEGRAM_BOT_TOKEN`: Token Telegram bot
- `TELEGRAM_CHAT_ID`: ID chat Telegram

## Yêu cầu

- Python 3.8+
- pandas
- tabulate

## Xử lý sự cố

Nếu gặp lỗi khi khởi động công cụ:

1. Kiểm tra xem file `trading_state.json` có tồn tại không
2. Đảm bảo quyền thực thi cho file `cli_controller.py` và `run_tool.sh`
3. Kiểm tra logs trong file `cli_controller.log`