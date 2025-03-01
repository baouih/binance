# Binance Futures Trading Bot - CLI Mode

Phiên bản CLI của Binance Futures Trading Bot được tối ưu hóa để giảm tài nguyên sử dụng và tăng độ ổn định. Phiên bản này loại bỏ hoàn toàn giao diện web và sử dụng giao diện dòng lệnh (CLI) cho tất cả các tương tác.

## Đặc điểm chính

- Giao diện dòng lệnh đầy đủ chức năng
- Hỗ trợ song ngữ Việt-Anh
- Giảm đáng kể tài nguyên sử dụng và bộ nhớ
- Tăng độ ổn định của hệ thống giao dịch
- Hỗ trợ đầy đủ các chức năng quản lý và giám sát bot

## Cách sử dụng

### Khởi động bot CLI

```bash
python new_main.py
```

### Tham số dòng lệnh

Bạn có thể sử dụng các tham số dòng lệnh để truy cập nhanh các chức năng:

- `--status` hoặc `-s`: Hiển thị trạng thái bot
- `--positions` hoặc `-p`: Hiển thị các vị thế đang mở
- `--trades` hoặc `-t`: Hiển thị giao dịch gần đây
- `--logs [N]` hoặc `-l [N]`: Hiển thị N dòng log gần đây
- `--start`: Khởi động bot
- `--stop`: Dừng bot
- `--restart`: Khởi động lại bot
- `--monitor [INTERVAL]` hoặc `-m [INTERVAL]`: Giám sát thời gian thực

Ví dụ:
```bash
python new_main.py --status
python new_main.py --logs 50
python new_main.py --monitor 10
```

### Menu tương tác

Khi chạy không có tham số, bot sẽ hiển thị menu tương tác cho phép bạn:

1. Xem vị thế hiện tại
2. Xem giao dịch gần đây
3. Xem chỉ số hiệu suất
4. Xem logs
5. Giám sát thời gian thực
6. Khởi động/dừng/khởi động lại bot
7. Chạy backtest
8. Cấu hình bot

## Script hỗ trợ

Sử dụng script `run_cli.sh` để chạy phiên bản CLI và tự động tắt phiên bản web:

```bash
./run_cli.sh
```

## Cấu hình

Cấu hình của bot được lưu trong file `multi_coin_config.json`. Bạn có thể chỉnh sửa file này trực tiếp hoặc sử dụng tùy chọn "Cấu hình bot" trong menu tương tác.

## Yêu cầu API keys

Bot yêu cầu API keys từ Binance để hoạt động. Đảm bảo bạn đã thiết lập các biến môi trường:

- `BINANCE_API_KEY`: API key Binance
- `BINANCE_API_SECRET`: API secret Binance

Các API keys này có thể được thiết lập trong file `.env`.

## Bảo trì và logs

Các file logs được lưu tại:
- `trading_bot.log`: Log chính của bot
- `trading_summary.log`: Tóm tắt giao dịch
- `backtest_logs_1h.log`: Log kết quả backtest

---

## English Version

# Binance Futures Trading Bot - CLI Mode

The CLI version of the Binance Futures Trading Bot is optimized to reduce resource usage and increase stability. This version completely removes the web interface and uses a command-line interface (CLI) for all interactions.

## Key Features

- Full-featured command line interface
- Bilingual support (Vietnamese-English)
- Significantly reduced resource and memory usage
- Increased stability of the trading system
- Full support for bot management and monitoring functions

## Usage

### Start the CLI bot

```bash
python new_main.py
```

### Command Line Parameters

You can use command line parameters to quickly access functions:

- `--status` or `-s`: Display bot status
- `--positions` or `-p`: Display open positions
- `--trades` or `-t`: Display recent trades
- `--logs [N]` or `-l [N]`: Display N recent log lines
- `--start`: Start the bot
- `--stop`: Stop the bot
- `--restart`: Restart the bot
- `--monitor [INTERVAL]` or `-m [INTERVAL]`: Real-time monitoring

Examples:
```bash
python new_main.py --status
python new_main.py --logs 50
python new_main.py --monitor 10
```

### Interactive Menu

When run without parameters, the bot will display an interactive menu allowing you to:

1. View current positions
2. View recent trades
3. View performance metrics
4. View logs
5. Real-time monitoring
6. Start/stop/restart the bot
7. Run backtest
8. Configure the bot

## Support Script

Use the `run_cli.sh` script to run the CLI version and automatically shut down the web version:

```bash
./run_cli.sh
```

## Configuration

The bot's configuration is stored in the `multi_coin_config.json` file. You can edit this file directly or use the "Configure bot" option in the interactive menu.

## API Key Requirements

The bot requires API keys from Binance to operate. Make sure you have set up the environment variables:

- `BINANCE_API_KEY`: Binance API key
- `BINANCE_API_SECRET`: Binance API secret

These API keys can be set in the `.env` file.

## Maintenance and Logs

Log files are stored at:
- `trading_bot.log`: Main bot log
- `trading_summary.log`: Trading summary
- `backtest_logs_1h.log`: Backtest results log