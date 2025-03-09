# HƯỚNG DẪN QUẢN LÝ HỆ THỐNG GIAO DỊCH

## Tổng quan hệ thống
Hệ thống giao dịch tiền điện tử bao gồm 3 dịch vụ chính:
1. **Dịch vụ giao dịch chính** (main.py) - Phân tích thị trường và thực hiện giao dịch
2. **Auto SLTP Manager** (auto_sltp_manager.py) - Quản lý Stop Loss và Take Profit tự động
3. **Trailing Stop Service** (position_trailing_stop.py) - Quản lý Trailing Stop để bảo vệ lợi nhuận

## Khởi động hệ thống
Để khởi động toàn bộ hệ thống:
```
./auto_startup_services.sh
```

Script này sẽ kiểm tra và khởi động 3 dịch vụ chính nếu chúng chưa chạy.

## Khởi động các dịch vụ riêng lẻ

### Khởi động dịch vụ giao dịch chính
```
python main.py
```

### Khởi động Auto SLTP Manager
```
./auto_start_sltp_manager.sh
```
hoặc sử dụng phiên bản không tương tác:
```
./headless_start_sltp_manager.sh
```

### Khởi động Trailing Stop Service
```
./start_trailing_stop.sh
```
hoặc sử dụng phiên bản không tương tác:
```
./headless_trailing_stop.sh
```

### Khởi động lại dịch vụ Trailing Stop (nếu gặp lỗi)
```
./fix_trailing_stop.sh
```

## Giám sát hệ thống

### Xem log dịch vụ giao dịch chính
```
tail -f trading_service.log
```

### Xem log Auto SLTP Manager
```
tail -f auto_sltp_manager.log
```

### Xem log Trailing Stop Service
```
tail -f trailing_stop_service.log
```

### Kiểm tra trạng thái tất cả dịch vụ
```
ps aux | grep -E "python (position_trailing_stop.py|auto_sltp_manager.py|main.py)" | grep -v grep
```

## Tự động khởi động lại

### Cài đặt tác vụ tự động khởi động qua cron
```
./crontab_setup.sh
```

Script này sẽ cài đặt các tác vụ cron để tự động khởi động lại dịch vụ nếu chúng bị dừng:
- Kiểm tra và khởi động lại tất cả dịch vụ 5 phút một lần
- Kiểm tra riêng Trailing Stop Service mỗi giờ
- Kiểm tra riêng Auto SLTP Manager mỗi giờ

## Dừng dịch vụ

### Dừng một dịch vụ cụ thể
```
pkill -f "python position_trailing_stop.py"  # Dừng Trailing Stop
pkill -f "python auto_sltp_manager.py"       # Dừng Auto SLTP Manager
pkill -f "python main.py"                    # Dừng dịch vụ giao dịch chính
```

### Dừng tất cả dịch vụ
```
./stop_all_services.sh
```

## Xử lý sự cố

### Vấn đề với Trailing Stop
Nếu dịch vụ Trailing Stop không khởi động hoặc không hoạt động đúng:
```
./fix_trailing_stop.sh
```

### Vấn đề với Auto SLTP Manager
Nếu dịch vụ Auto SLTP Manager không khởi động hoặc không hoạt động đúng:
```
./headless_start_sltp_manager.sh
```

### Kiểm tra vị thế hiện tại
```
python -c "
import json
try:
    with open('active_positions.json', 'r') as f:
        positions = json.load(f)
    if positions:
        for symbol, pos in positions.items():
            print(f\"  {symbol}: {pos.get('side')} @ {pos.get('entry_price', 0):.2f}\")
            print(f\"     SL: {pos.get('stop_loss', 'N/A'):.2f}, TP: {pos.get('take_profit', 'N/A'):.2f}\")
            trailing_status = 'Đã kích hoạt' if pos.get('trailing_activated', False) else 'Chưa kích hoạt'
            print(f\"     Trailing Stop: {trailing_status}\")
    else:
        print('  Không có vị thế nào đang mở')
except Exception as e:
    print(f'  Lỗi khi đọc vị thế: {e}')
"
```

## Hệ thống headless
Tất cả các script khởi động đã hỗ trợ chạy ở chế độ headless, phù hợp cho việc triển khai lên server và không cần tương tác người dùng. Các script headless bao gồm:

- **headless_start_sltp_manager.sh** - Khởi động Auto SLTP Manager
- **headless_trailing_stop.sh** - Khởi động Trailing Stop Service
- **auto_startup_services.sh** - Khởi động tất cả dịch vụ