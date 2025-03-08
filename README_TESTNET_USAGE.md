# Hướng dẫn sử dụng Binance Futures Testnet

## Tổng quan
Đây là hệ thống giao dịch tự động cho tài khoản nhỏ ($100-$1000), được tối ưu hóa cho Binance Futures với quản lý rủi ro thích ứng và chiến lược dựa trên kích thước tài khoản.

## Các file chính trong hệ thống

- **create_test_order_v3.py**: File chính để đặt lệnh giao dịch trên Testnet
- **check_active_positions_v2.py**: Kiểm tra vị thế và lệnh đang mở
- **check_position_mode.py**: Kiểm tra và thay đổi chế độ vị thế (Hedge Mode/One-way)
- **binance_api.py**: Thư viện API kết nối đến Binance

## Cách sử dụng hệ thống

### 1. Cấu hình API key

Hệ thống sử dụng biến môi trường để lưu trữ API key:
- BINANCE_TESTNET_API_KEY
- BINANCE_TESTNET_API_SECRET

### 2. Kiểm tra chế độ vị thế

Chạy lệnh sau để kiểm tra chế độ vị thế hiện tại:
```
python check_position_mode.py
```

Nếu muốn thay đổi chế độ vị thế, sửa file trên và uncomment dòng cuối:
```python
# Đặt 'False' cho One-way Mode (chỉ Long hoặc Short)
# Đặt 'True' cho Hedge Mode (đồng thời Long và Short)
change_position_mode(False)  # hoặc True
```

### 3. Đặt lệnh giao dịch

File `create_test_order_v3.py` cho phép đặt lệnh test với các tham số đã được cấu hình:

```
python create_test_order_v3.py
```

Các tham số giao dịch có thể tùy chỉnh trong file:
- Symbol (BTCUSDT, ETHUSDT, v.v.)
- Đòn bẩy (mặc định: 5x)
- Phần trăm rủi ro (mặc định: 2.0% số dư)
- Stop loss (mặc định: 5.0%)
- Take profit (mặc định: 7.5%)

### 4. Kiểm tra vị thế đang hoạt động

Để xem vị thế hiện tại và lệnh đang mở:
```
python check_active_positions_v2.py
```

Thông tin hiển thị bao gồm:
- Số dư tài khoản
- Danh sách vị thế đang hoạt động 
- Thông tin chi tiết: giá vào, giá hiện tại, PnL, leverage, v.v.
- Danh sách lệnh đang mở (stop loss, take profit)

## Quản lý rủi ro

Hệ thống được thiết kế với các nguyên tắc quản lý rủi ro:
1. Chỉ giao dịch một phần nhỏ số dư (1-2%)
2. Luôn đặt stop loss để bảo vệ tài khoản
3. Tỷ lệ risk/reward tối thiểu 1:1.5 (mặc định 5% SL / 7.5% TP)
4. Đòn bẩy vừa phải (mặc định 5x)

## Lưu ý
- Tất cả giao dịch diễn ra trên Testnet, không ảnh hưởng đến tiền thật
- Hệ thống đang ở giai đoạn kiểm thử, chưa nên sử dụng cho giao dịch thực tế
- Cần đặc biệt chú ý đến chế độ vị thế trước khi giao dịch (Hedge Mode/One-way)