# Binance Trading Bot

Bot giao dịch Bitcoin tự động với chiến lược thích ứng đa chế độ thị trường và tối ưu hóa ML.

## Chuyển đổi sang CLI Mode

Hệ thống đã được chuyển đổi từ giao diện web sang giao diện dòng lệnh (CLI) để cải thiện hiệu suất và độ ổn định. Việc này giúp giảm thiểu tài nguyên sử dụng và cải thiện độ tin cậy của bot, đặc biệt là khi chạy trong thời gian dài.

## Hướng dẫn sử dụng

Có 3 cách để khởi động bot:

### 1. Sử dụng script khởi động nhanh

```bash
./cli_startup.sh
```

Script này sẽ kiểm tra môi trường, dừng các dịch vụ web đang chạy và khởi động CLI.

### 2. Khởi động CLI trực tiếp

```bash
python new_main.py
```

### 3. Sử dụng tham số dòng lệnh

Bạn có thể sử dụng các tham số dòng lệnh để thực hiện các hành động cụ thể:

```bash
python new_main.py --status     # Hiển thị trạng thái bot
python new_main.py --positions  # Hiển thị vị thế hiện tại
python new_main.py --trades     # Hiển thị giao dịch gần đây
python new_main.py --logs 50    # Hiển thị 50 dòng log gần đây
python new_main.py --start      # Khởi động bot
python new_main.py --stop       # Dừng bot
python new_main.py --restart    # Khởi động lại bot
python new_main.py --monitor 10 # Giám sát bot, cập nhật mỗi 10 giây
```

## Chiến lược Thích ứng

Bot sử dụng cơ chế phát hiện chế độ thị trường để tự động chọn chiến lược tối ưu:

- **Trending**: Sử dụng EMA Cross (0.5), MACD (0.3), ADX (0.2)
- **Ranging**: Sử dụng RSI (0.4), BBands (0.4), Stochastic (0.2)
- **Volatile**: Sử dụng BBands (0.3), ATR (0.4), ADX (0.3)
- **Quiet**: Sử dụng BBands (0.5), RSI (0.3), Stochastic (0.2)
- **Unknown**: Sử dụng RSI (0.33), MACD (0.33), BBands (0.34)

## Cấu hình

Bạn cần thiết lập API keys Binance trong file `.env`:

```
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

Cấu hình chi tiết hơn có thể được điều chỉnh trong file `multi_coin_config.json`.

## Tính năng chính

- Phát hiện chế độ thị trường tự động
- Tự động chuyển đổi chiến lược phù hợp
- Quản lý rủi ro động theo biến động thị trường
- Báo cáo hiệu suất chi tiết
- Giao diện dòng lệnh trực quan với menu tương tác
- Giảm thiểu sử dụng tài nguyên hệ thống

## Tài liệu bổ sung

Để biết thêm chi tiết, vui lòng tham khảo các tài liệu sau:

- [Hướng dẫn CLI](README_CLI.md): Hướng dẫn chi tiết về giao diện dòng lệnh
- [API Docs](API_DOCS.md): Tài liệu API cho phát triển nâng cao
- [Hướng dẫn triển khai](README_DEPLOYMENT.md): Hướng dẫn triển khai bot trên các nền tảng khác nhau