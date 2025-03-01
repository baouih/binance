# Hướng dẫn sử dụng CLI cho Binance Trading Bot

## Giới thiệu

Giao diện dòng lệnh (CLI) của Binance Trading Bot cung cấp một cách hiệu quả và ổn định để kiểm soát và giám sát bot giao dịch mà không cần giao diện web. Điều này đặc biệt hữu ích trong môi trường có kết nối mạng không ổn định hoặc khi cần tiết kiệm tài nguyên.

## Cách khởi động CLI

Có hai cách để khởi động giao diện CLI:

1. Sử dụng script chạy trực tiếp:
   ```
   ./run_cli.sh
   ```

2. Sử dụng Python trực tiếp:
   ```
   python new_main.py
   ```

## Các tính năng chính

Giao diện CLI cung cấp các chức năng sau:

### Menu chính

Menu chính cung cấp các tùy chọn:

- **Xem vị thế hiện tại**: Hiển thị các vị thế đang mở
- **Xem giao dịch gần đây**: Hiển thị lịch sử giao dịch gần đây
- **Xem chỉ số hiệu suất**: Hiển thị các chỉ số hiệu suất của bot
- **Xem logs**: Hiển thị logs gần đây
- **Màn hình giám sát thời gian thực**: Giám sát bot theo thời gian thực

- **Khởi động bot**: Bắt đầu chạy bot giao dịch
- **Khởi động lại bot**: Khởi động lại bot

- **Chạy backtest**: Thực hiện backtest với dữ liệu lịch sử
- **Cấu hình bot**: Thiết lập cấu hình cho bot

### Các tham số dòng lệnh

Ngoài menu tương tác, bạn có thể sử dụng các tham số dòng lệnh:

```
python new_main.py --status  # Hiển thị trạng thái bot
python new_main.py --positions  # Hiển thị vị thế hiện tại
python new_main.py --trades  # Hiển thị giao dịch gần đây
python new_main.py --logs 50  # Hiển thị 50 dòng log gần đây
python new_main.py --start  # Khởi động bot
python new_main.py --stop  # Dừng bot
python new_main.py --restart  # Khởi động lại bot
python new_main.py --monitor 10  # Giám sát bot, cập nhật mỗi 10 giây
```

## Các chế độ thị trường và chiến lược

Bot hỗ trợ phát hiện và thích ứng với các chế độ thị trường:

- **Trending**: Chiến lược EMA Cross (0.5), MACD (0.3), ADX (0.2)
- **Ranging**: Chiến lược RSI (0.4), BBands (0.4), Stochastic (0.2)
- **Volatile**: Chiến lược BBands (0.3), ATR (0.4), ADX (0.3)
- **Quiet**: Chiến lược BBands (0.5), RSI (0.3), Stochastic (0.2)
- **Unknown**: Chiến lược RSI (0.33), MACD (0.33), BBands (0.34)

## Quản lý rủi ro

Bot sử dụng các thông số quản lý rủi ro đã được kiểm chứng:
- Tham số BBands: Chu kỳ 30, độ lệch chuẩn 0.8
- Rủi ro: 0.5%, TP/SL: 1.0/0.5

## Xử lý lỗi

Nếu gặp lỗi khi sử dụng CLI, kiểm tra:

1. **Logs**: Xem logs trong `trading_bot.log` và `cli_controller.log`
2. **Kết nối API**: Đảm bảo API key và secret hợp lệ
3. **Tập tin cấu hình**: Kiểm tra tập tin `multi_coin_config.json`
4. **Quá trình xử lý**: Kiểm tra xem bot có đang chạy không với lệnh `ps aux | grep multi_coin_bot.py`
