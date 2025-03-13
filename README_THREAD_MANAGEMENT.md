# Hướng Dẫn Quản Lý Thread & Dịch Vụ Hệ Thống

## Tổng Quan

Hệ thống trading của chúng ta hoạt động với nhiều dịch vụ chạy đồng thời. Việc quản lý thread và đảm bảo các dịch vụ hoạt động liên tục là rất quan trọng. Tài liệu này cung cấp hướng dẫn chi tiết về cách quản lý thread và dịch vụ trong hệ thống.

## Kiến Trúc Hệ Thống

Hệ thống gồm các thành phần chính:

1. **Market Notifier**: Phân tích thị trường và gửi thông báo
2. **Unified Trading Service**: Hợp nhất nhiều dịch vụ nhỏ (Auto SLTP, Trailing Stop)
3. **Service Manager**: Giám sát và khởi động lại dịch vụ khi cần thiết 
4. **Watchdog**: Theo dõi tất cả các dịch vụ, bao gồm cả Service Manager

## Cơ Chế Tự Phục Hồi

Hệ thống sử dụng cấu trúc giám sát đa tầng:

1. **Dịch vụ tự phục hồi**: Mỗi dịch vụ có thể tự khởi động lại khi phát hiện lỗi
2. **Service Manager**: Giám sát trạng thái các dịch vụ và khởi động lại khi cần
3. **Watchdog**: Đảm bảo tất cả các dịch vụ (kể cả Service Manager) luôn hoạt động

## Tín Hiệu Heartbeat

Để phát hiện khi một dịch vụ bị treo:

1. Mỗi dịch vụ định kỳ ghi log "Heartbeat" vào file log
2. Service Manager kiểm tra log để xác định xem dịch vụ có còn hoạt động không
3. Nếu không tìm thấy heartbeat trong khoảng thời gian nhất định, dịch vụ sẽ được khởi động lại

## Khởi Động Dịch Vụ

### Khởi động thủ công

Để khởi động tất cả dịch vụ thủ công:

```bash
python start_all_services.py
```

### Khởi động Watchdog

Để khởi động Watchdog (đảm bảo tất cả dịch vụ luôn chạy):

```bash
python service_watchdog.py
```

### Sử dụng giao diện desktop

1. Mở ứng dụng desktop: `python run_desktop_app.py`
2. Chuyển đến tab "Quản lý hệ thống"
3. Sử dụng các nút để khởi động/dừng các dịch vụ

## Giám Sát Dịch Vụ

### Kiểm tra trạng thái

```bash
python check_service_status.py
```

### Xem log của dịch vụ

```bash
# Market Notifier
tail -f market_notifier.log

# Unified Trading Service
tail -f unified_trading_service.log

# Service Manager
tail -f service_manager.log

# Watchdog
tail -f watchdog.log
```

## Xử Lý Sự Cố Thread

### Thread bị treo

Các thread có thể bị treo vì nhiều lý do:

1. **Deadlock**: Các thread chờ đợi tài nguyên của nhau
2. **Timeout API**: Thread bị treo khi gọi API bên ngoài không phản hồi
3. **Lỗi không xử lý**: Exception không được bắt đúng cách

### Giải pháp

Hệ thống sử dụng nhiều giải pháp:

1. **Timeout cho API calls**: Tất cả API calls đều có timeout
2. **Cơ chế retry**: Tự động thử lại khi gặp lỗi tạm thời
3. **Exception handling**: Xử lý toàn diện tất cả ngoại lệ
4. **Heartbeat**: Phát hiện thread bị treo và khởi động lại
5. **Phân cấp giám sát**: Nhiều lớp giám sát để đảm bảo phục hồi

## Hiệu Suất Và Tài Nguyên

### Giám sát tài nguyên

Service Manager giám sát mức sử dụng tài nguyên:

1. **Bộ nhớ**: Giới hạn bộ nhớ cho mỗi dịch vụ
2. **CPU**: Giới hạn % sử dụng CPU

### Tối ưu hóa

1. **Hợp nhất dịch vụ**: Unified Trading Service nhóm nhiều dịch vụ nhỏ
2. **Làm việc theo lịch**: Các tác vụ được lên lịch với khoảng thời gian hợp lý
3. **Sử dụng các biện pháp nhẹ**: Tránh polling liên tục

## Lời Khuyên

1. **Luôn kiểm tra log**: Khi gặp vấn đề, đọc file log là bước đầu tiên
2. **Không khởi động lại thủ công quá nhiều**: Để hệ thống tự phục hồi
3. **Cập nhật cấu hình**: Điều chỉnh các thông số trong file cấu hình khi cần thiết
4. **Theo dõi tài nguyên hệ thống**: Sử dụng `htop` hoặc công cụ tương tự để theo dõi

## Tài Nguyên Bổ Sung

- **auto_restart.py**: Script tự động khởi động lại dịch vụ nếu hệ thống gặp lỗi nghiêm trọng
- **enhanced_service_manager.py**: Service Manager với khả năng giám sát tài nguyên
- **service_watchdog.py**: Ứng dụng theo dõi toàn bộ hệ thống và đảm bảo hoạt động liên tục