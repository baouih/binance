# Hướng dẫn tinh chỉnh chiến lược cho thị trường đi ngang

## Giới thiệu
Tài liệu này cung cấp hướng dẫn chi tiết về cách điều chỉnh các chiến lược giao dịch được tối ưu hóa cho thị trường đi ngang, đặc biệt là cho tài khoản nhỏ từ $100-$300.

## Chiến lược chính cho thị trường đi ngang

### 1. Bollinger Bounce
Chiến lược này giao dịch khi giá chạm band dưới (mua) hoặc band trên (bán) của Bollinger Bands, kết hợp với tín hiệu quá mua/quá bán từ RSI.

**Các tham số quan trọng:**
- `bb_period`: Số nến cho Bollinger Bands (15-20)
- `bb_std_dev`: Độ lệch chuẩn (2.0 là tiêu chuẩn)
- `rsi_period`: Số nến cho RSI (10-14)
- `rsi_oversold`: Ngưỡng quá bán (30)
- `rsi_overbought`: Ngưỡng quá mua (70)
- `stop_loss_percent`: % stop loss (1.2-1.5%)
- `take_profit_percent`: % take profit (2.4-3.0%)

**Tối ưu cho tài khoản nhỏ:**
- Giảm `bb_period` xuống 15 nến để nhạy hơn
- Giảm `rsi_period` xuống 10 nến
- Tăng `take_profit_percent` lên 3.0% để tối đa hóa lợi nhuận
- Giữ `stop_loss_percent` ở mức 1.5% để tránh bị dừng lỗ quá sớm

### 2. RSI Reversal
Chiến lược này giao dịch khi RSI cho tín hiệu đảo chiều trong vùng quá mua/quá bán, kết hợp với giá và đường trung bình động.

**Các tham số quan trọng:**
- `rsi_period`: Số nến cho RSI (10-14)
- `rsi_oversold`: Ngưỡng quá bán (30)
- `rsi_overbought`: Ngưỡng quá mua (70)
- `ma_period`: Số nến cho MA (30-50)
- `stop_loss_percent`: % stop loss (1.2-1.5%)
- `take_profit_percent`: % take profit (2.5-3.0%)

**Tối ưu cho tài khoản nhỏ:**
- Giảm `rsi_period` xuống 10 nến để nhạy hơn
- Giảm `ma_period` xuống 30 nến
- Tăng `take_profit_percent` lên 3.0%
- Giữ `stop_loss_percent` ở mức 1.5%

## Cặp tiền được đề xuất cho tài khoản nhỏ
1. **LTCUSDT**: Litecoin có thanh khoản cao, biến động vừa phải, phù hợp cho bollinger_bounce
2. **ATOMUSDT**: Cosmos có biến động tốt trong thị trường đi ngang
3. **LINKUSDT**: Chainlink thường có xu hướng đi ngang với mức giá ổn định
4. **DOGEUSDT**: Dogecoin có biến động cao, phù hợp cho tài khoản nhỏ
5. **XRPUSDT**: Ripple có thanh khoản cao, biến động vừa phải

## Tinh chỉnh tham số
Để tinh chỉnh tham số cho các điều kiện thị trường cụ thể:

1. Chỉnh sửa tệp `configs/strategy_market_config.json`
2. Thực hiện backtest với tham số mới:
   ```
   python backtest_small_account_strategy.py --account-size 200 --strategy bollinger_bounce --timeframe 1h
   ```
3. Phân tích kết quả backtest và điều chỉnh:
   ```
   python analyze_backtest_results.py --strategy bollinger_bounce --account-size 200
   ```

## Quản lý rủi ro cho tài khoản nhỏ
- **Đòn bẩy tối đa**: 15x cho tài khoản $100-$200
- **Số vị thế đồng thời**: Tối đa 2 vị thế cho tài khoản $100-$200
- **Phân bổ vốn**: Không quá 75% tổng tài khoản được sử dụng cùng lúc
- **Điều chỉnh stop loss**: Stop loss rộng hơn 1.5% để tránh bị stopped out quá sớm
- **Điều chỉnh take profit**: Take profit cao hơn 3.0% để tối đa hóa lợi nhuận

## Tạo cấu hình tùy chỉnh
Bạn có thể tạo cấu hình tùy chỉnh cho các kích thước tài khoản cụ thể trong `account_size_adjustments` của tệp cấu hình: