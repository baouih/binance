# Hệ Thống Trailing Stop Tự Động

Hệ thống Trailing Stop tự động bảo vệ vị thế đang mở và đảm bảo tối đa hóa lợi nhuận khi thị trường biến động có lợi cho vị thế. Tất cả các tính năng được tự động khởi động khi bot chạy.

## Tính Năng Chính

1. **Tự Động Kích Hoạt Khi Bot Khởi Động**
   - Không cần chạy lệnh thủ công
   - Tích hợp ngay vào quy trình khởi động bot

2. **Parallel Trailing Stop Thông Minh**
   - Kích hoạt khi vị thế đạt +2% lợi nhuận
   - Callback chỉ 1% từ mức cao nhất/thấp nhất 
   - Tự động điều chỉnh theo biến động của thị trường

3. **Kết Hợp Take Profit Nhiều Cấp Độ**
   - Take Profit ngắn hạn 3% để nắm bắt lợi nhuận nhanh
   - Take Profit dài hạn 7.5% để tối đa hóa lợi nhuận khi xu hướng mạnh

4. **Cơ Chế Tự Phát Hiện và Giải Quyết Xung Đột**
   - Ngăn chặn các tiến trình chồng chéo tự động
   - Hệ thống giám sát tình trạng hoạt động 24/7

5. **Tự Động Khôi Phục Sau Sự Cố**
   - Phát hiện và khởi động lại các dịch vụ bị dừng
   - Ghi log chi tiết để dễ dàng khắc phục sự cố

## Kiến Trúc Hệ Thống

Hệ thống sử dụng kiến trúc điều phối trung tâm để đảm bảo không có thành phần nào chạy chồng chéo:

```
main.py (Bot chính)
  ↓
auto_start_integrated_system.sh (Khởi động tự động)
  ↓
trailing_stop_scheduler.py (Điều phối trung tâm)
  ↓
  ├── position_trailing_stop.py (Dịch vụ trailing stop)
  └── add_trailing_stop_to_positions.py (Thêm trailing stop)
```

## Cấu Hình 

Thông số cấu hình được lưu trong `trailing_stop_config.json`:

- **Activation Percent**: 2.0% (Kích hoạt trailing stop khi đạt lợi nhuận 2%)
- **Callback Percent**: 1.0% (Rút lui 1% từ điểm cao nhất/thấp nhất)
- **Default TP Levels**: [3.0%, 7.5%] (Take profit ngắn hạn và dài hạn)
- **Default SL Percent**: 5.0% (Stop loss mặc định)
- **Hedging Mode**: `true` (Hỗ trợ chế độ hedge)

## Cơ Chế Ngăn Chồng Chéo

Hệ thống sử dụng các biện pháp sau để đảm bảo không xảy ra chồng chép:

1. **Kiểm tra trạng thái tiến trình**
   ```python
   if is_process_running(TRAILING_STOP_PID_FILE):
       stop_trailing_service()  # Dừng dịch vụ cũ nếu đang chạy
   ```

2. **Ghi và quản lý PID**
   ```python
   save_pid(TRAILING_STOP_PID_FILE, process.pid)  # Lưu PID để theo dõi
   ```

3. **Giám sát và tự khôi phục**
   ```bash
   # Kiểm tra và khởi động lại nếu dịch vụ không hoạt động
   if ! check_trailing_stop; then
       python trailing_stop_scheduler.py start --interval 60
   fi
   ```

## Cách Hệ Thống Hoạt Động

1. Khi bot khởi động, thread trailing stop tự động chạy
2. Thread này khởi động các dịch vụ trailing stop qua script tích hợp
3. Script này đảm bảo tất cả các thành phần được khởi động đúng thứ tự
4. Hệ thống điều phối trung tâm theo dõi và quản lý tất cả các tiến trình
5. Thông qua kiểm tra PID, hệ thống đảm bảo không có dịch vụ chồng chéo

## Kết Luận

Hệ thống Trailing Stop tự động đã được tích hợp hoàn toàn vào quy trình khởi động bot. Bạn không cần thực hiện thêm bất kỳ thao tác nào - tất cả các cơ chế bảo vệ vị thế sẽ được kích hoạt ngay khi bot chạy.

Hệ thống này giúp bảo vệ lợi nhuận của bạn và tối ưu hóa chiến lược giao dịch, đặc biệt hữu ích cho tài khoản nhỏ và trung bình với quy mô $100-$1000.