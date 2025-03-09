# Hệ thống Auto SL/TP Manager

Hệ thống Auto SL/TP Manager là một công cụ mạnh mẽ giúp tự động quản lý các lệnh Stop Loss (SL) và Take Profit (TP) cho các vị thế giao dịch của bạn trên Binance Futures. Hệ thống này đặc biệt hữu ích cho các tài khoản Hedge Mode, giúp bảo vệ lợi nhuận và hạn chế rủi ro cho các vị thế đang mở.

## Tính năng chính

1. **Tự động thiết lập SL/TP:** Tự động đặt lệnh Stop Loss và Take Profit cho tất cả các vị thế đang mở
2. **Trailing Stop Loss:** Theo dõi và điều chỉnh Stop Loss khi giá di chuyển theo hướng có lợi, giúp bảo vệ lợi nhuận
3. **Hỗ trợ Hedge Mode:** Tương thích hoàn toàn với tài khoản Hedge Mode của Binance Futures
4. **Tùy chỉnh linh hoạt:** Dễ dàng điều chỉnh các tham số như phần trăm SL/TP, khoảng cách trailing stop, v.v.
5. **Chạy liên tục:** Hoạt động liên tục trong nền, đảm bảo luôn luôn bảo vệ các vị thế của bạn

## Cài đặt và Cấu hình

### Cấu hình cơ bản

Tham số cấu hình được lưu trong file `configs/sltp_config.json`:

```json
{
    "default_sl_percent": 2.0,       // % Stop Loss mặc định từ giá entry
    "default_tp_percent": 3.0,       // % Take Profit mặc định từ giá entry
    "min_profit_percent": 1.0,       // % lợi nhuận tối thiểu để trailing stop
    "trailing_percent": 1.0,         // % khoảng cách trailing stop
    "activation_percent": 2.0,       // % lợi nhuận để kích hoạt trailing stop
    "interval_seconds": 60,          // Thời gian giữa các lần kiểm tra (giây)
    "symbols": [                     // Danh sách các cặp tiền được hỗ trợ
        "BTCUSDT",
        "ETHUSDT", 
        "BNBUSDT",
        "SOLUSDT",
        ...
    ]
}
```

### Cấu hình nâng cao

```json
"advanced_settings": {
    "use_atr_for_sl": false,         // Sử dụng ATR để tính Stop Loss
    "atr_multiplier": 1.5,           // Hệ số nhân ATR
    "dynamic_tp_multiplier": 1.5,    // Hệ số nhân động cho Take Profit
    "partial_tp_enabled": false,     // Bật/tắt TP một phần
    "partial_tp_levels": [           // Các mức TP một phần
        {
            "percent": 1.5,          // TP khi đạt 1.5% lợi nhuận
            "close_percent": 30      // Đóng 30% vị thế
        },
        // Các mức khác
    ]
}
```

## Cách sử dụng

### Khởi động tự động

```bash
./auto_start_sltp_manager.sh
```

Script này sẽ khởi động Auto SL/TP Manager trong nền và lưu các log vào file `auto_sltp_manager.log`.

### Khởi động thủ công

```bash
# Sử dụng cho tài khoản testnet
python auto_sltp_manager.py --testnet --interval 60

# Sử dụng cho tài khoản thực
python auto_sltp_manager.py --interval 60
```

### Kiểm tra trạng thái

```bash
# Xem log
tail -f auto_sltp_manager.log

# Kiểm tra tiến trình
cat auto_sltp_manager.pid
ps -p $(cat auto_sltp_manager.pid)
```

### Dừng hệ thống

```bash
kill $(cat auto_sltp_manager.pid)
```

## Cách hoạt động

1. **Khởi tạo:** Hệ thống khởi động và kết nối đến API Binance
2. **Quét vị thế:** Định kỳ quét tất cả các vị thế đang mở
3. **Thiết lập SL/TP:** Nếu vị thế chưa có SL/TP, hệ thống sẽ tự động thiết lập
4. **Monitoring:** Theo dõi giá và vị thế để cập nhật SL/TP khi cần thiết
5. **Trailing Stop:** Khi lợi nhuận đạt mức kích hoạt, hệ thống sẽ bắt đầu trailing stop
6. **Bảo vệ lợi nhuận:** Tự động nâng Stop Loss theo giá thị trường

## Ưu điểm của Auto SL/TP Manager

- **Bảo vệ vốn:** Luôn đảm bảo có Stop Loss cho mọi vị thế
- **Bảo toàn lợi nhuận:** Trailing stop giúp khóa lợi nhuận khi thị trường đảo chiều
- **Tự động hóa:** Không cần theo dõi và điều chỉnh SL/TP thủ công
- **Tương thích Hedge Mode:** Hoạt động hoàn hảo với tài khoản Hedge Mode của Binance
- **Linh hoạt:** Dễ dàng tùy chỉnh theo chiến lược giao dịch cá nhân

## Lưu ý quan trọng

- Luôn kiểm tra kỹ các tham số cấu hình trước khi sử dụng
- Thường xuyên kiểm tra log để đảm bảo hệ thống hoạt động bình thường
- Kiểm tra số dư và trạng thái tài khoản trước khi giao dịch
- Để `interval_seconds` ở mức hợp lý (30-60 giây) để không gây tải lên API Binance