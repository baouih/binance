# HƯỚNG DẪN SỬ DỤNG DỊCH VỤ HỢP NHẤT

## Giới thiệu

Dịch vụ hợp nhất là một thành phần mới của BinanceTrader Bot, được thiết kế để quản lý và giám sát nhiều dịch vụ tự động trong một quy trình thống nhất. Thiết kế này giúp tối ưu hóa tài nguyên hệ thống và đơn giản hóa việc quản lý.

Các dịch vụ được tích hợp bao gồm:

1. **Auto SLTP**: Tự động đặt Stop Loss và Take Profit cho các vị thế
2. **Trailing Stop**: Tự động điều chỉnh Stop Loss theo giá thị trường
3. **Market Monitor**: Giám sát biến động thị trường và gửi thông báo khi phát hiện biến động lớn

## Cài đặt và Khởi động

### Các file chính:

- `unified_trading_service.py`: Dịch vụ hợp nhất chính
- `start_unified_service.sh`: Script khởi động dịch vụ
- `service_guardian.py`: Giám sát và tự động khởi động lại dịch vụ
- `templates/services.html`: Giao diện web quản lý dịch vụ

### Cách khởi động:

1. Đảm bảo đã cấp quyền thực thi cho script khởi động:
   ```
   chmod +x start_unified_service.sh
   chmod +x service_guardian.py
   ```

2. Khởi động dịch vụ:
   ```
   ./start_unified_service.sh
   ```

3. (Tùy chọn) Khởi động guardian để tự động giám sát:
   ```
   python service_guardian.py
   ```

## Quản lý dịch vụ qua giao diện web

Dịch vụ hợp nhất có thể được quản lý qua giao diện web:

1. Truy cập vào trang web: http://[địa_chỉ_máy_chủ]:5000/services
2. Từ đây, bạn có thể:
   - Khởi động/dừng/khởi động lại từng dịch vụ
   - Cấu hình thông số cho từng dịch vụ
   - Xem log hoạt động
   - Giám sát tài nguyên hệ thống (CPU, bộ nhớ, đĩa cứng)

## Cấu hình chi tiết

### Auto SLTP (Tự động Stop Loss và Take Profit)

Auto SLTP tự động đặt Stop Loss và Take Profit cho các vị thế đang mở, giúp bảo vệ lợi nhuận và hạn chế tổn thất.

Thông số cấu hình:

- **Tỉ lệ Risk/Reward**: Tỉ lệ giữa Take Profit và Stop Loss (mặc định: 2.0)
- **Phần trăm Stop Loss**: Khoảng cách từ giá vào đến Stop Loss tính theo phần trăm (mặc định: 2.0%)
- **Chu kỳ kiểm tra**: Thời gian giữa các lần kiểm tra và cập nhật SLTP (mặc định: 30 giây)

Cách hoạt động:
1. Dịch vụ kiểm tra tất cả vị thế đang mở
2. Với mỗi vị thế, tính toán giá Stop Loss và Take Profit dựa trên giá vào và cấu hình
3. Đặt lệnh Stop Loss và Take Profit tự động

### Trailing Stop (Stop Loss Theo Giá)

Trailing Stop tự động điều chỉnh Stop Loss khi giá di chuyển có lợi cho vị thế, giúp bảo vệ lợi nhuận đồng thời cho phép lợi nhuận tiếp tục tăng.

Thông số cấu hình:

- **Phần trăm kích hoạt**: Lợi nhuận tối thiểu (%) để kích hoạt trailing stop (mặc định: 1.0%)
- **Phần trăm theo sau**: Khoảng cách từ giá hiện tại đến Stop Loss (mặc định: 0.5%)
- **Chu kỳ kiểm tra**: Thời gian giữa các lần kiểm tra và cập nhật trailing stop (mặc định: 15 giây)

Cách hoạt động:
1. Dịch vụ kiểm tra tất cả vị thế đang mở
2. Với mỗi vị thế đang có lợi nhuận vượt ngưỡng kích hoạt
3. Tính toán Stop Loss mới dựa trên giá hiện tại và phần trăm theo sau
4. Nếu Stop Loss mới tốt hơn Stop Loss hiện tại, cập nhật Stop Loss

### Market Monitor (Giám sát Thị trường)

Market Monitor theo dõi biến động thị trường và gửi thông báo khi phát hiện biến động bất thường, giúp bạn nắm bắt cơ hội giao dịch hoặc quản lý rủi ro.

Thông số cấu hình:

- **Cặp tiền theo dõi**: Danh sách cặp tiền cần theo dõi, phân cách bằng dấu phẩy (mặc định: BTCUSDT,ETHUSDT,SOLUSDT)
- **Ngưỡng biến động**: Mức biến động giá (%) đủ để kích hoạt cảnh báo (mặc định: 3.0%)
- **Chu kỳ kiểm tra**: Thời gian giữa các lần kiểm tra thị trường (mặc định: 60 giây)

Cách hoạt động:
1. Dịch vụ kiểm tra biến động giá của các cặp tiền được cấu hình
2. Nếu biến động vượt quá ngưỡng cấu hình, gửi thông báo qua Telegram (nếu đã cấu hình)

## Quản lý dịch vụ qua API

Ngoài giao diện web, bạn cũng có thể quản lý dịch vụ qua API:

- `GET /api/services/status`: Lấy trạng thái của tất cả dịch vụ
- `GET /api/services/system`: Lấy thông tin hệ thống (CPU, bộ nhớ, đĩa cứng)
- `GET /api/services/logs`: Lấy log hoạt động
- `POST /api/services/logs/clear`: Xóa log
- `POST /api/services/control`: Điều khiển một dịch vụ (start/stop/restart)
- `POST /api/services/control/all`: Điều khiển tất cả dịch vụ
- `GET /api/services/config/all`: Lấy cấu hình của tất cả dịch vụ
- `POST /api/services/config`: Cập nhật cấu hình cho một dịch vụ

## Tự động hóa và Giám sát

Service Guardian là một thành phần giám sát tự động, đảm bảo dịch vụ hợp nhất luôn hoạt động. Nếu dịch vụ bị lỗi hoặc dừng đột ngột, Guardian sẽ tự động khởi động lại.

Tính năng của Guardian:

- Kiểm tra định kỳ trạng thái dịch vụ hợp nhất
- Tự động phát hiện và khởi động lại dịch vụ khi cần thiết
- Giới hạn số lần khởi động lại trong một khoảng thời gian để tránh lặp lại lỗi
- Ghi log chi tiết để hỗ trợ xử lý sự cố

## Xử lý sự cố

Nếu gặp vấn đề với dịch vụ hợp nhất, hãy kiểm tra các file log sau:

- `unified_service.log`: Log của dịch vụ hợp nhất
- `service_guardian.log`: Log của guardian

Các vấn đề thường gặp:

1. **Dịch vụ không chạy**:
   - Kiểm tra file log để xem lỗi chi tiết
   - Đảm bảo các thông tin kết nối Binance API đã được cấu hình đúng
   - Kiểm tra quyền thực thi của script khởi động

2. **Lỗi kết nối API**:
   - Kiểm tra cấu hình API key và secret
   - Đảm bảo mạng internet hoạt động bình thường
   - Xác minh rằng API Binance không có sự cố

3. **Dịch vụ tự động dừng**:
   - Đảm bảo hệ thống có đủ tài nguyên (CPU, bộ nhớ)
   - Kiểm tra log để tìm lỗi gây ra vấn đề
   - Khởi động guardian để tự động phục hồi

## Ví dụ Cấu hình

### Cấu hình cho tài khoản nhỏ (< 1000 USDT)

**Auto SLTP**:
- Risk/Reward: 2.0
- Stop Loss: 3.0%
- Chu kỳ kiểm tra: 60 giây

**Trailing Stop**:
- Kích hoạt: 1.5%
- Theo sau: 0.8%
- Chu kỳ kiểm tra: 30 giây

**Market Monitor**:
- Cặp tiền: BTCUSDT,ETHUSDT
- Ngưỡng biến động: 2.5%
- Chu kỳ kiểm tra: 120 giây

### Cấu hình cho tài khoản lớn (> 10000 USDT)

**Auto SLTP**:
- Risk/Reward: 2.5
- Stop Loss: 1.5%
- Chu kỳ kiểm tra: 30 giây

**Trailing Stop**:
- Kích hoạt: 0.8%
- Theo sau: 0.4%
- Chu kỳ kiểm tra: 15 giây

**Market Monitor**:
- Cặp tiền: BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT
- Ngưỡng biến động: 1.5%
- Chu kỳ kiểm tra: 60 giây

## Kết luận

Dịch vụ hợp nhất cung cấp một giải pháp toàn diện để tự động hóa các khía cạnh quan trọng của giao dịch cryptocurrency, từ quản lý rủi ro đến theo dõi thị trường. Với giao diện quản lý trực quan và khả năng tự phục hồi, hệ thống đảm bảo hoạt động liên tục và hiệu quả ngay cả trong môi trường biến động.

---

© 2025 BinanceTrader Bot | Phiên bản: 1.0.0