# Hệ Thống Xác Thực Giá và Bảo Vệ Giao Dịch

Tài liệu này mô tả hệ thống xác thực giá và bảo vệ giao dịch trong trường hợp có vấn đề với API hoặc dữ liệu giá không đáng tin cậy.

## Vấn Đề

Khi giao dịch với Binance API (đặc biệt là trên Testnet), chúng ta thường gặp các vấn đề sau:

1. API không trả về giá cho một số cặp tiền
2. Giá trả về không chính xác hoặc quá cũ
3. Dịch vụ API có thể tạm thời không khả dụng

Những vấn đề này có thể dẫn đến:

- Không thể tạo lệnh (không tính được số lượng)
- Tạo lệnh với giá sai lệch (gây tổn thất)
- Đặt TP/SL không hợp lý

## Giải Pháp

Chúng tôi đã triển khai hệ thống xác thực giá đa nguồn và bảo vệ giao dịch:

### 1. Module `prices_cache.py`

- Lưu trữ và quản lý cache giá cho các cặp tiền
- Cung cấp giá dự phòng khi API không hoạt động
- Cập nhật cache tự động
- Hỗ trợ đánh dấu thời gian để xác định giá cũ

### 2. Module `price_validator.py`

- Kiểm tra tính đáng tin cậy của giá từ nhiều nguồn (Futures API, Spot API, Exchange khác)
- Cung cấp giá đã được xác thực từ nguồn đáng tin cậy nhất
- Đảm bảo giá trị an toàn cho các lệnh giao dịch

### 3. Module `price_monitor.py`

- Giám sát liên tục giá của các cặp tiền
- Phát hiện biến động giá bất thường
- Tự động tạm dừng giao dịch khi phát hiện quá nhiều cặp tiền có vấn đề
- Gửi thông báo về các vấn đề về giá

## Cách Sử Dụng

### 1. Lấy Giá An Toàn

```python
from price_validator import get_verified_price

# Lấy giá đã được xác thực
price, is_reliable = get_verified_price("BTCUSDT", api)

if is_reliable:
    print(f"Giá đáng tin cậy: {price}")
else:
    print(f"Giá có thể không chính xác: {price}")
```

### 2. Tạo Lệnh An Toàn

```python
from price_validator import safe_create_order

# Tạo lệnh thị trường với bảo vệ giá
result = safe_create_order(
    api=api,
    symbol="BTCUSDT",
    side="BUY",
    order_type="MARKET",
    usd_value=100,
    position_side="LONG"
)

if "error" in result:
    print(f"Lỗi: {result['error']}")
else:
    print(f"Đã tạo lệnh thành công: {result}")
```

### 3. Theo Dõi Trạng Thái Giao Dịch

```python
from price_validator import is_trading_enabled

# Kiểm tra xem giao dịch có được phép không
if is_trading_enabled():
    print("Giao dịch được phép")
else:
    print("Giao dịch đã bị tạm dừng do vấn đề với giá")
```

### 4. Khởi Động Giám Sát Giá

```python
from price_monitor import start_price_monitor

# Khởi động monitor giám sát giá
monitor = start_price_monitor(api)

# Dừng giám sát khi cần
monitor.stop()
```

## Quy Trình Xác Thực Giá

1. Lấy giá từ Binance Futures API (nguồn chính)
2. Nếu không có hoặc không đáng tin cậy, lấy từ Binance Spot API
3. Nếu vẫn không có, kiểm tra với nguồn thứ ba (CoinGecko, v.v)
4. Nếu không có nguồn nào đáng tin cậy, sử dụng giá từ cache nhưng đánh dấu là không đáng tin cậy
5. Nếu phát hiện quá nhiều cặp không đáng tin cậy, tạm dừng giao dịch tự động

## Tiêu Chí Xác Định Giá Đáng Tin Cậy

1. Giá phải dương và hợp lý (không quá 0 hoặc quá lớn)
2. Giá không được chênh lệch quá 5% so với các nguồn khác
3. Giá không được quá cũ (mặc định là 60 giây)
4. Ít nhất phải có một nguồn khác xác nhận giá

## Xử Lý Lệnh Khi Không Có Giá Đáng Tin Cậy

1. **Lệnh Market**: Vẫn có thể tạo vì Binance sẽ dùng giá thị trường thực tế
2. **Lệnh Limit/Stop**: Điều chỉnh giá dựa trên giá thị trường hiện tại để đảm bảo lệnh hợp lý
3. **Lệnh TP/SL**: Điều chỉnh giá kích hoạt để đảm bảo kích hoạt đúng

## Giám Sát và Cảnh Báo

- Ghi log chi tiết về tất cả các vấn đề về giá
- Tạo file `price_alerts.log` với các cảnh báo quan trọng
- Lưu trạng thái hiện tại vào `price_monitor_status.json`
- Phát hiện và thông báo về biến động giá bất thường

## Biện Pháp An Toàn

1. **Ngừng giao dịch tự động**: Khi phát hiện quá nhiều (≥3) cặp tiền có vấn đề về giá
2. **Điều chỉnh giá lệnh**: Đảm bảo lệnh stop/limit được đặt ở mức hợp lý với thị trường
3. **Kiểm tra đa nguồn**: Xác minh giá với nhiều nguồn khác nhau
4. **Ghi log và cảnh báo**: Ghi nhận tất cả các vấn đề để phân tích sau

## Lưu Ý Quan Trọng

- Hệ thống này vẫn cho phép giao dịch ngay cả khi không có giá từ Binance API, nhưng sẽ thận trọng hơn
- Đối với các lệnh market, vẫn an toàn vì Binance sử dụng giá thị trường thực tế
- Tuy nhiên, nên hạn chế giao dịch khi không có đủ dữ liệu giá đáng tin cậy
- Giám sát thường xuyên file log để phát hiện vấn đề

## Tùy Chỉnh Tham Số

Các tham số có thể điều chỉnh trong `price_validator.py`:

- `max_price_age_seconds`: Thời gian tối đa (giây) giá được coi là mới (mặc định: 60)
- `max_deviation_percent`: Độ chênh lệch tối đa (%) giữa các nguồn (mặc định: 5%)
- `max_unreliable_symbols`: Số lượng tối đa symbols không đáng tin cậy trước khi tạm dừng giao dịch (mặc định: 3)