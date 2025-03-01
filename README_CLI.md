# Binance Trading Bot - CLI Interface

## Tổng quan

Giao diện dòng lệnh (CLI) cho Binance Trading Bot cung cấp cách đơn giản và hiệu quả để kiểm soát, giám sát và tương tác với bot giao dịch mà không cần sử dụng giao diện web. Điều này đặc biệt hữu ích khi:

- Kết nối web không ổn định (các vấn đề về WebSocket)
- Cần kiểm soát bot từ xa qua SSH
- Chạy bot trên môi trường máy chủ không có giao diện đồ họa
- Tạo báo cáo tự động và lên lịch các tác vụ

## Cài đặt

Bot CLI sử dụng các thư viện Python tiêu chuẩn và một số thư viện bổ sung để tạo biểu đồ và báo cáo:

```bash
# Cài đặt các thư viện cần thiết
pip install matplotlib numpy pandas tabulate

# Đảm bảo các script có quyền thực thi
chmod +x run_tool.sh
chmod +x reports/create_reports.sh
chmod +x enhanced_cli_visualizer.py
```

## Cách sử dụng cơ bản

Để tương tác với bot, sử dụng script `run_tool.sh`:

```bash
./run_tool.sh <lệnh> [tham_số]
```

### Các lệnh có sẵn:

| Lệnh | Mô tả | Ví dụ |
|------|-------|-------|
| `status` | Xem trạng thái hiện tại của bot | `./run_tool.sh status` |
| `start` | Khởi động bot | `./run_tool.sh start` |
| `stop` | Dừng bot | `./run_tool.sh stop` |
| `restart` | Khởi động lại bot | `./run_tool.sh restart` |
| `trades [n]` | Hiển thị n giao dịch gần đây | `./run_tool.sh trades 20` |
| `positions` | Xem danh sách vị thế đang mở | `./run_tool.sh positions` |
| `logs [n]` | Xem n dòng log gần đây nhất | `./run_tool.sh logs 50` |
| `monitor` | Mở màn hình giám sát thời gian thực | `./run_tool.sh monitor` |
| `backtest` | Chạy backtest nhanh | `./run_tool.sh backtest` |
| `report` | Tạo báo cáo đầy đủ (HTML và biểu đồ) | `./run_tool.sh report` |
| `equity` | Tạo biểu đồ đường cong vốn | `./run_tool.sh equity` |
| `performance` | Tạo biểu đồ hiệu suất | `./run_tool.sh performance` |

## Báo cáo và Trực quan hóa

Bot CLI bao gồm công cụ trực quan hóa nâng cao để tạo biểu đồ và báo cáo chi tiết về hiệu suất giao dịch:

### Tạo báo cáo đầy đủ

```bash
./run_tool.sh report
```

Lệnh này sẽ tạo báo cáo HTML đầy đủ trong thư mục `reports/` kèm theo các biểu đồ:
- Đường cong vốn và drawdown
- Biểu đồ chỉ số hiệu suất dạng radar chart
- Biểu đồ phân tích theo symbol

### Tạo biểu đồ riêng lẻ

```bash
# Tạo biểu đồ đường cong vốn
./run_tool.sh equity

# Tạo biểu đồ hiệu suất
./run_tool.sh performance
```

## Tính năng giám sát thời gian thực

Sử dụng chế độ `monitor` để giám sát bot theo thời gian thực:

```bash
./run_tool.sh monitor
```

Chế độ này hiển thị một màn hình tương tác với thông tin cập nhật liên tục về:
- Trạng thái bot
- Vị thế hiện tại
- Giao dịch gần đây
- Tài khoản và số dư
- Tín hiệu thị trường gần đây

Nhấn `Ctrl+C` để thoát chế độ giám sát.

## Cấu hình Tự động khởi động và khởi động lại

Bạn có thể cài đặt bot để tự động khởi động và khởi động lại khi gặp sự cố:

```bash
# Cập nhật file .env để bật tự động khởi động
AUTO_START=true
AUTO_RESTART=true
```

Cài đặt này có thể được điều chỉnh riêng cho môi trường thử nghiệm và sản xuất:

```bash
# Cho môi trường thử nghiệm (TEST_MODE=true)
TEST_AUTO_START=false    # Không tự động khởi động trong môi trường test
TEST_AUTO_RESTART=true   # Tự động khởi động lại trong môi trường test

# Cho môi trường sản xuất (TEST_MODE=false)
PROD_AUTO_START=true     # Tự động khởi động trong môi trường sản xuất
PROD_AUTO_RESTART=true   # Tự động khởi động lại trong môi trường sản xuất
```

## Sử dụng nâng cao

### Các tùy chọn trực quan hóa nâng cao

Bạn có thể sử dụng trực tiếp công cụ trực quan hóa nâng cao với nhiều tùy chọn chi tiết hơn:

```bash
# Xem tất cả các tùy chọn có sẵn
python enhanced_cli_visualizer.py --help

# Ví dụ: Tạo tất cả các biểu đồ và lưu vào thư mục tùy chỉnh
python enhanced_cli_visualizer.py --dashboard -o custom_reports/
```

### Lên lịch báo cáo tự động

Bạn có thể sử dụng cron để lên lịch tạo báo cáo tự động:

```bash
# Mở crontab
crontab -e

# Thêm dòng này để tạo báo cáo hàng ngày lúc 00:01
1 0 * * * cd /đường/dẫn/tới/bot && ./reports/create_reports.sh
```

## Xử lý sự cố

Nếu bạn gặp vấn đề với công cụ CLI:

1. Kiểm tra log:
```bash
./run_tool.sh logs 50
```

2. Đảm bảo tất cả các script có quyền thực thi:
```bash
chmod +x *.sh
chmod +x reports/*.sh
chmod +x *.py
```

3. Kiểm tra trạng thái bot:
```bash
./run_tool.sh status
```

4. Nếu bot bị treo, thử khởi động lại:
```bash
./run_tool.sh restart
```

## Kết luận

Giao diện CLI cung cấp cách mạnh mẽ và đáng tin cậy để tương tác với bot giao dịch, tạo báo cáo và giám sát hiệu suất. Đặc biệt hữu ích trong môi trường không ổn định hoặc khi cần quản lý từ xa.