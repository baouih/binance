# Hướng dẫn sử dụng Hedge Mode Backtesting

## Tổng quan
Module hedge mode backtesting cho phép kiểm tra hiệu suất của chiến lược giao dịch đánh hai chiều đồng thời (hedge mode) so với phương pháp giao dịch truyền thống chỉ theo một hướng (one-way mode).

## Các tính năng chính
- **Backtesting đa cặp tiền tệ**: Kiểm tra nhiều cặp tiền cùng lúc
- **So sánh trực tiếp**: Đánh giá hiệu suất hedge mode vs single direction
- **Báo cáo chi tiết**: Phân tích thống kê đầy đủ về lợi nhuận, tỷ lệ thắng, drawdown
- **Biểu đồ equity curve**: Hiển thị biến động vốn theo thời gian
- **Tối ưu theo khung thời gian**: Xác định phiên giao dịch tốt nhất trong ngày

## Cách sử dụng

### 1. Chạy backtest cơ bản
```python
# Import module
import hedge_mode_backtest

# Backtest cho một cặp tiền
hedge_mode_backtest.run_backtest(['BTCUSDT'], risk_level='medium', days=30)

# Backtest cho nhiều cặp tiền
symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
hedge_mode_backtest.run_backtest(symbols, risk_level='high', days=15)
```

### 2. Các tham số cấu hình
- **symbols**: Danh sách các cặp tiền cần test (list)
- **risk_level**: Mức độ rủi ro (low, medium, high)
- **days**: Số ngày kiểm tra dữ liệu lịch sử
- **timeframe**: Khung thời gian (1h, 4h, 1d) - mặc định 1h
- **initial_balance**: Số dư ban đầu (USDT) - mặc định 10000 USDT
- **leverage**: Đòn bẩy - mặc định 20x

### 3. Mức độ rủi ro
- **Low**: SL 2%, TP 4%, risk 1% mỗi lệnh, tối đa 5 vị thế
- **Medium**: SL 5%, TP 10%, risk 2% mỗi lệnh, tối đa 7 vị thế
- **High**: SL 7%, TP 21%, risk 3% mỗi lệnh, tối đa 10 vị thế

## Kết quả backtest

Kết quả backtest được lưu trong thư mục `backtest_results` với các file sau:
- **JSON**: Dữ liệu backtest đầy đủ dạng JSON
- **TXT**: Báo cáo tóm tắt dạng text
- **PNG**: Biểu đồ equity curve

Ví dụ báo cáo:
```
===== BÁO CÁO BACKTEST CHẾ ĐỘ HEDGE MODE =====

Ngày thực hiện: 2025-03-14 07:10:29
Số tiền ban đầu: 10000 USDT
Số tiền cuối: 10471.41 USDT
Lợi nhuận: 471.41 USDT (4.71%)
Drawdown tối đa: 0.00%
Số lệnh: 10
Tỷ lệ thắng: 80.00%
Profit Factor: 11.96

SO SÁNH HEDGE MODE VỚI SINGLE DIRECTION:
-----------------------------------

Symbol: BTCUSDT
- Hedge Mode: 10471.41 USDT (4.71%)
- Single Direction: 10427.48 USDT (4.27%)
- Chênh lệch: 43.93 USDT (HEDGE MODE TỐT HƠN)
```

## Kết luận & Khuyến nghị

Dựa trên kết quả backtest, chúng tôi khuyến nghị:

1. **Khi nào dùng Hedge Mode**:
   - Trong thị trường sideway (đi ngang)
   - Lúc biến động mạnh không rõ xu hướng
   - Phiên London/NY Close (03:00-05:00)

2. **Khi nào dùng Single Direction**:
   - Khi thị trường có xu hướng rõ ràng
   - Ưu tiên LONG trong phiên Daily Candle Close (06:30-07:30)
   - Ưu tiên SHORT trong phiên London Open (15:00-17:00) và New York Open (20:30-22:30)

3. **Thiết lập tối ưu cho Hedge Mode**:
   - Risk mỗi lệnh: 2-3% tài khoản
   - Đòn bẩy: 10-20x
   - SL/TP tỉ lệ 1:3 (SL 7%, TP 21%)
   - Chọn thời điểm giao dịch phù hợp theo phiên