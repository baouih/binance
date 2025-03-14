# HỆ THỐNG QUẢN LÝ THREAD VÀ DỊCH VỤ

Tài liệu này mô tả cách thức hoạt động của hệ thống quản lý thread và dịch vụ mới được triển khai trong phiên bản gần đây của phần mềm.

## Kiến trúc hệ thống quản lý 3 lớp

Hệ thống được thiết kế với 3 lớp quản lý và giám sát để đảm bảo tính liên tục và tự động phục hồi:

1. **Lớp tự phục hồi cơ bản**: Mỗi dịch vụ có cơ chế phát hiện và khôi phục lỗi nội bộ
2. **Service Manager**: Giám sát và quản lý tất cả các dịch vụ từ bên ngoài
3. **Watchdog**: Giám sát toàn bộ hệ thống kể cả Service Manager, đảm bảo hệ thống luôn hoạt động

### Các dịch vụ chính

1. **Market Notifier (`auto_market_notifier.py`)**: 
   - Phân tích thị trường và gửi thông báo
   - Theo dõi cơ hội giao dịch
   - Cập nhật phân tích theo chu kỳ

2. **Unified Trading Service (`unified_trading_service.py`)**: 
   - Xử lý giao dịch tự động
   - Quản lý đặt lệnh và vị thế
   - Tự động thực hiện SL/TP theo cấu hình

3. **Service Manager (`enhanced_service_manager.py`)**: 
   - Giám sát tình trạng hoạt động của tất cả dịch vụ
   - Khôi phục dịch vụ bị lỗi
   - Ghi nhật ký hoạt động

4. **Watchdog (`service_watchdog.py`)**: 
   - Giám sát Service Manager
   - Phát hiện lỗi toàn hệ thống
   - Khởi động lại toàn bộ dịch vụ nếu cần

5. **Telegram Notifier (`advanced_telegram_notifier.py`)**: 
   - Gửi thông báo qua Telegram
   - Thông báo sự cố và trạng thái

## Cơ chế Heartbeat

Hệ thống sử dụng cơ chế heartbeat để theo dõi tình trạng hoạt động:

1. Mỗi dịch vụ ghi timestamp định kỳ vào file heartbeat
2. Service Manager đọc các file heartbeat để đánh giá tình trạng
3. Watchdog giám sát heartbeat của Service Manager

## Cơ chế phục hồi tự động

Hệ thống phục hồi theo thứ bậc:

1. **Cấp dịch vụ**: Thread bị lỗi được khởi động lại
2. **Cấp Service Manager**: Dịch vụ bị lỗi được khởi động lại
3. **Cấp Watchdog**: Toàn bộ hệ thống bao gồm Service Manager được khởi động lại

## Giao diện quản lý

Giao diện desktop (`enhanced_trading_gui.py`) cung cấp khả năng:

1. Theo dõi tình trạng dịch vụ theo thời gian thực
2. Khởi động/dừng dịch vụ thủ công
3. Xem nhật ký hoạt động
4. Kiểm tra sự cố

## Cài đặt và khởi động

### Khởi động tự động toàn bộ hệ thống:

```bash
python start_all_services.py
```

### Khởi động riêng từng dịch vụ:

```bash
python service_watchdog.py         # Khởi động Watchdog
python enhanced_service_manager.py  # Khởi động Service Manager
python unified_trading_service.py   # Khởi động Trading Service
python auto_market_notifier.py      # Khởi động Market Notifier
```

### Kiểm tra tình trạng:

```bash
python check_service_status.py      # Kiểm tra trạng thái các dịch vụ
```

## Giải quyết sự cố

1. Kiểm tra nhật ký trong các file `.log`
2. Sử dụng tab "Quản lý hệ thống" trong giao diện desktop
3. Khởi động lại dịch vụ cụ thể hoặc toàn bộ hệ thống

## Lưu ý quan trọng

- **Không tắt Watchdog trừ khi bạn muốn dừng toàn bộ hệ thống**
- Đảm bảo cài đặt đúng các biến môi trường (API keys, cấu hình)
- Kiểm tra thường xuyên các file nhật ký để phát hiện sự cố