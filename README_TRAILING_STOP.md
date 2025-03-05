# Hướng dẫn sử dụng Trailing Stop tự động

Tài liệu này mô tả cách sử dụng và cấu hình hệ thống Trailing Stop tự động trên bot giao dịch Binance Futures.

## Giới thiệu

**Trailing Stop** là một công cụ quản lý rủi ro nâng cao, tự động điều chỉnh mức stop loss theo biến động giá của thị trường, giúp bảo vệ lợi nhuận và tối ưu hóa điểm thoát lệnh.

Ví dụ: 
- Đối với vị thế **LONG**, khi giá tăng, Trailing Stop cũng sẽ tự động được nâng lên theo.
- Đối với vị thế **SHORT**, khi giá giảm, Trailing Stop cũng sẽ tự động được hạ xuống theo.

## Cách thức hoạt động

1. **Kích hoạt**: Trailing Stop sẽ được kích hoạt khi lợi nhuận của vị thế đạt đến ngưỡng xác định (mặc định là 2%)
2. **Cập nhật tự động**: Khi đã kích hoạt, Trailing Stop sẽ tự động di chuyển theo hướng có lợi của thị trường
3. **Bảo vệ lợi nhuận**: Nếu thị trường đảo chiều và chạm vào mức Trailing Stop, vị thế sẽ được đóng để bảo vệ lợi nhuận

## Cấu hình

Các tham số Trailing Stop có thể điều chỉnh trong file `risk_config.json`:

```json
"stop_loss": {
    "default_percent": 5.0, 
    "trailing": {
        "enabled": true,
        "activation_percent": 2.0,  // Kích hoạt trailing khi lời 2%
        "callback_percent": 1.0,    // Callback 1% từ đỉnh
        "step_percent": 0.5         // Di chuyển mỗi bước 0.5%
    }
}
```

- **activation_percent**: Mức lợi nhuận để kích hoạt Trailing Stop (mặc định: 2%)
- **callback_percent**: Khoảng cách giữa Trailing Stop và mức cao/thấp nhất (mặc định: 1%)
- **step_percent**: Kích thước bước di chuyển tối thiểu (mặc định: 0.5%)

## Sử dụng

### Kiểm tra trạng thái Trailing Stop

```bash
python position_trailing_stop.py --mode check
```

### Khởi động dịch vụ Trailing Stop

```bash
./start_bot_services.sh
```

Dịch vụ sẽ tự động:
1. Phát hiện các vị thế đang mở
2. Thiết lập và theo dõi Trailing Stop
3. Gửi thông báo qua Telegram khi Trailing Stop được kích hoạt hoặc vị thế đóng

### Tắt dịch vụ Trailing Stop

```bash
./stop_bot_services.sh
```

## Lợi ích của Trailing Stop

- **Tối ưu hóa lợi nhuận**: Cho phép chạy lãi xa hơn trong xu hướng mạnh
- **Bảo vệ tự động**: Tự động đóng vị thế khi thị trường đảo chiều, bảo vệ lợi nhuận đã đạt được
- **Loại bỏ yếu tố cảm xúc**: Vận hành theo quy tắc, không bị ảnh hưởng bởi cảm xúc của nhà giao dịch
- **Vận hành 24/7**: Dịch vụ chạy liên tục, không cần can thiệp thủ công

## Thiết lập Telegram cho Trailing Stop

Để nhận thông báo khi Trailing Stop được kích hoạt hoặc vị thế được đóng:

```bash
python telegram_setup.py
```

Làm theo hướng dẫn trên màn hình để thiết lập thông báo Telegram.