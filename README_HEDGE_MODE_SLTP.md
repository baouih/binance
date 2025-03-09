# Hướng dẫn quản lý SL/TP trong chế độ Hedge Mode

## Tổng quan

Tài liệu này hướng dẫn cách sử dụng hệ thống Stop Loss/Take Profit (SL/TP) với tài khoản Binance Futures ở cả hai chế độ:
- **Hedge Mode** (chế độ phòng hộ): Cho phép mở đồng thời vị thế LONG và SHORT trên cùng một cặp tiền
- **One-way Mode** (chế độ một chiều): Chỉ cho phép một vị thế (LONG hoặc SHORT) trên một cặp tiền tại một thời điểm

## Các tham số quan trọng

### Hedge Mode

Khi tài khoản ở chế độ hedge mode, cần chú ý:

1. **Tham số `positionSide`**: PHẢI được sử dụng cho mọi lệnh
   - `LONG`: Cho vị thế mua
   - `SHORT`: Cho vị thế bán
   - KHÔNG sử dụng `BOTH` trong hedge mode

2. **Các điểm chú ý**:
   - KHÔNG kết hợp `positionSide` với `reduceOnly=true`
   - KHÔNG kết hợp `positionSide` với `closePosition=true`
   - LUÔN chỉ định chính xác số lượng giao dịch
   - Lệnh SELL đóng vị thế LONG; lệnh BUY đóng vị thế SHORT

### One-way Mode

Khi tài khoản ở chế độ one-way mode, cần chú ý:

1. **Tham số `reduceOnly`**:
   - Sử dụng `reduceOnly=true` cho lệnh SL/TP
   - KHÔNG sử dụng `positionSide` trong one-way mode

2. **Các điểm chú ý**:
   - Có thể sử dụng `closePosition=true` thay cho số lượng cụ thể
   - Side của lệnh SL/TP phải ngược với vị thế (BUY→SELL, SELL→BUY)

## Cách sử dụng Auto SL/TP Manager

Các module đã được cập nhật để tự động phát hiện chế độ tài khoản và sử dụng tham số phù hợp:

```python
# Khởi tạo API với các bản vá lỗi
from binance_api import BinanceAPI
from binance_api_fixes import apply_fixes_to_api

api = BinanceAPI()
api = apply_fixes_to_api(api)

# Đặt SL/TP cho vị thế LONG trong hedge mode
result = api.set_stop_loss_take_profit(
    symbol="BTCUSDT",
    position_side="LONG",  # Quan trọng trong hedge mode
    stop_loss_price=85000,
    take_profit_price=90000
)

# Đặt SL/TP cho vị thế trong one-way mode 
# (không cần chỉ định position_side)
result = api.set_stop_loss_take_profit(
    symbol="BTCUSDT",
    stop_loss_price=85000,
    take_profit_price=90000
)
```

## Xác minh lệnh SL/TP

Bạn có thể kiểm tra lệnh SL/TP đã được đặt chính xác bằng công cụ `verify_sltp_orders.py`:

```bash
python verify_sltp_orders.py
```

Kết quả sẽ hiển thị các lệnh SL/TP hiện có cho từng vị thế, xác nhận các tham số đã được áp dụng đúng.

## Quy trình khắc phục lỗi

Nếu gặp lỗi khi đặt lệnh SL/TP, hãy kiểm tra:

1. **Chế độ tài khoản**: Xác định tài khoản đang ở chế độ hedge mode hay one-way mode
   ```python
   api.hedge_mode  # True nếu là hedge mode
   ```

2. **Thông tin vị thế**: Xác nhận vị thế tồn tại và số lượng
   ```python
   positions = api.get_futures_position_risk()
   # Kiểm tra positionAmt và positionSide
   ```

3. **Lỗi API thường gặp**:
   - `-4061`: Lỗi position side không khớp
   - `-4013`: Lỗi kết hợp reduceOnly với positionSide
   - `-2022`: Lỗi không tìm thấy positionSide cho tài khoản one-way

## Cấu hình SL/TP tự động

Trong file `sltp_config.json`, bạn có thể cấu hình SL/TP mặc định:

```json
{
  "default_sl_percentage": 2.0,
  "default_tp_percentage": 3.0,
  "update_interval_seconds": 60,
  "enable_auto_sltp": true
}
```

Hệ thống sẽ tự động áp dụng SL/TP dựa trên các tỷ lệ phần trăm được cấu hình, và sẽ xử lý đúng tham số dựa vào chế độ tài khoản.

## Lưu ý bổ sung

- Khi thay đổi giữa các chế độ tài khoản, TP/SL tự động sẽ được điều chỉnh phù hợp
- Với tài khoản hedge mode, bảo đảm luôn chỉ định positionSide chính xác
- Không cần thay đổi code khi chuyển đổi giữa các chế độ - hệ thống sẽ tự động phát hiện