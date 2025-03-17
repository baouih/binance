# Hướng Dẫn Quản Lý Rủi Ro Tự Động (ATR-Based)

## Giới thiệu
Hệ thống quản lý rủi ro là một trong những thành phần quan trọng nhất của bot giao dịch. Nó giúp bảo vệ vốn của bạn và tối ưu hóa lợi nhuận dựa trên mức độ chấp nhận rủi ro của bạn. Hệ thống hiện tại sử dụng mô hình quản lý rủi ro động dựa trên ATR, tự động điều chỉnh theo điều kiện thị trường thực tế.

## Các Mức Độ Rủi Ro

Hệ thống hỗ trợ 5 mức độ rủi ro chính:

### 1. Rất Thấp (9%)
- **Mô tả**: Chiến lược rủi ro thấp nhất, ưu tiên tuyệt đối cho việc bảo toàn vốn
- **Đặc điểm**:
  - Rủi ro tổng: 9% vốn
  - Vị thế tối đa: 3
  - Kích thước vị thế cơ sở: 3% vốn/vị thế
  - Stop Loss: Dựa trên 1.5 x ATR (tối thiểu 1.0%, tối đa 3.0%)
  - Take Profit: Dựa trên 4.5 x ATR
  - Tỷ lệ R:R: 3.0
  - Leverage tối đa: 2x
  - Drawdown tối đa: 4.5%
- **Phù hợp với**: Người mới bắt đầu, nhà đầu tư cực kỳ thận trọng

### 2. Thấp (15%)
- **Mô tả**: Chiến lược rủi ro thấp, ưu tiên bảo toàn vốn nhưng có cơ hội tăng trưởng
- **Đặc điểm**:
  - Rủi ro tổng: 15% vốn
  - Vị thế tối đa: 5
  - Kích thước vị thế cơ sở: 3% vốn/vị thế
  - Stop Loss: Dựa trên 1.7 x ATR (tối thiểu 1.5%, tối đa 4.0%)
  - Take Profit: Dựa trên 5.0 x ATR
  - Tỷ lệ R:R: 3.0
  - Leverage tối đa: 3x
  - Drawdown tối đa: 7.5%
- **Phù hợp với**: Nhà đầu tư thận trọng, trader mới với kinh nghiệm cơ bản

### 3. Trung Bình (20%)
- **Mô tả**: Chiến lược cân bằng giữa rủi ro và lợi nhuận
- **Đặc điểm**:
  - Rủi ro tổng: 20% vốn
  - Vị thế tối đa: 6
  - Kích thước vị thế cơ sở: 3.33% vốn/vị thế
  - Stop Loss: Dựa trên 2.0 x ATR (tối thiểu 2.0%, tối đa 5.0%)
  - Take Profit: Dựa trên 6.0 x ATR
  - Tỷ lệ R:R: 3.0
  - Leverage tối đa: 3x
  - Drawdown tối đa: 10%
- **Phù hợp với**: Trader có kinh nghiệm

### 4. Cao (25%)
- **Mô tả**: Chiến lược ưu tiên tăng trưởng với mức rủi ro cao
- **Đặc điểm**:
  - Rủi ro tổng: 25% vốn
  - Vị thế tối đa: 7
  - Kích thước vị thế cơ sở: 3.57% vốn/vị thế
  - Stop Loss: Dựa trên 2.2 x ATR (tối thiểu 2.5%, tối đa 6.0%)
  - Take Profit: Dựa trên 6.5 x ATR
  - Tỷ lệ R:R: 3.0
  - Leverage tối đa: 4x
  - Drawdown tối đa: 12.5%
- **Phù hợp với**: Trader có kinh nghiệm nhiều năm

### 5. Rất Cao (30%)
- **Mô tả**: Chiến lược rủi ro cao nhất, ưu tiên tuyệt đối cho tăng trưởng nhanh
- **Đặc điểm**:
  - Rủi ro tổng: 30% vốn
  - Vị thế tối đa: 8
  - Kích thước vị thế cơ sở: 3.75% vốn/vị thế
  - Stop Loss: Dựa trên 2.5 x ATR (tối thiểu 3.0%, tối đa 7.0%)
  - Take Profit: Dựa trên 7.5 x ATR
  - Tỷ lệ R:R: 3.0
  - Leverage tối đa: 5x
  - Drawdown tối đa: 15%
- **Phù hợp với**: Trader chuyên nghiệp

## Quản Lý Rủi Ro Động Dựa Trên ATR

Thay vì sử dụng mức SL và TP cố định, hệ thống hiện tại sử dụng ATR (Average True Range) để xác định mức dừng lỗ và chốt lời phù hợp với biến động thực tế của thị trường:

### Ưu Điểm của SL/TP Dựa Trên ATR:
1. **Thích ứng với biến động thị trường**: ATR là chỉ báo đo lường biến động thực tế, giúp tránh SL quá gần (bị cắn) hoặc quá xa (thua lỗ nhiều)
2. **Tự động điều chỉnh theo từng coin**: Mỗi coin có biến động khác nhau, ATR giúp tự động thích ứng
3. **Thích ứng với thay đổi thị trường**: Khi thị trường thay đổi từ biến động cao sang thấp (hoặc ngược lại), ATR tự động điều chỉnh

### Cách Hoạt Động:
- **Stop Loss**: $\text{SL} = \text{Entry Price} \pm (\text{ATR} \times \text{ATR Multiplier})$
- **Take Profit**: $\text{TP} = \text{Entry Price} \pm (\text{ATR} \times \text{TP ATR Multiplier})$
- **Kích thước vị thế tự thích ứng**: Giảm khi biến động cao, tăng khi biến động thấp

## Điều Chỉnh Theo Biến Động Thị Trường

Hệ thống phân loại biến động thị trường thành 5 mức và tự động điều chỉnh cấu hình giao dịch:

### 1. Biến Động Rất Thấp (< 1.5%)
- **Kích thước vị thế**: Tăng 20%
- **Stop Loss**: Thu hẹp 10%
- **Leverage**: Tăng 20%
- **Ví dụ**: Nếu cấu hình cơ sở là vị thế 3%, leverage 3x, thì trong điều kiện biến động thấp sẽ tự động điều chỉnh thành vị thế 3.6%, leverage 3.6x

### 2. Biến Động Thấp (1.5% - 3.0%)
- **Kích thước vị thế**: Tăng 10%
- **Stop Loss**: Giữ nguyên
- **Leverage**: Tăng 10%

### 3. Biến Động Trung Bình (3.0% - 5.0%)
- **Kích thước vị thế**: Giữ nguyên
- **Stop Loss**: Nới rộng 10%
- **Leverage**: Giữ nguyên

### 4. Biến Động Cao (5.0% - 7.0%)
- **Kích thước vị thế**: Giảm 30%
- **Stop Loss**: Nới rộng 30%
- **Leverage**: Giảm 30%

### 5. Biến Động Cực Cao (> 7.0%)
- **Kích thước vị thế**: Giảm 50%
- **Stop Loss**: Nới rộng 50%
- **Leverage**: Giảm 50%
- **Ví dụ**: Nếu cấu hình cơ sở là vị thế 3%, leverage 3x, thì trong điều kiện biến động cực cao sẽ tự động điều chỉnh thành vị thế 1.5%, leverage 1.5x

## Bộ Lọc Thời Gian (Time Filter)

Hệ thống tránh vào lệnh vào các thời điểm có biến động cao:

- **Tránh thời điểm biến động cao**:
  - Đầu tuần (Thứ Hai 00:00 - 03:00)
  - Cuối tuần (Thứ Sáu 20:00 - 23:59)

- **Ưu tiên thời gian giao dịch tối ưu**:
  - Phiên Á - Âu (08:00 - 17:00)

## Stop Loss Thích Ứng (Adaptive Stop Loss)

Hệ thống sử dụng chiến lược stop loss động để bảo vệ lợi nhuận và tối đa hóa kết quả:

### 1. Trailing Stop
- **Kích hoạt khi**: Lợi nhuận đạt mức 1.0 x ATR
- **Khoảng cách trailing**: Tính bằng bội số của ATR (từ 0.7 đến 1.5 tùy mức rủi ro)
- **Cách hoạt động**: Stop loss tự động di chuyển theo giá, duy trì khoảng cách ATR nhất định

### 2. Chốt Lời Từng Phần
- **Mức 1**: Đóng 30% vị thế khi lợi nhuận đạt 1.5 x ATR
- **Mức 2**: Đóng thêm 30% khi lợi nhuận đạt 2.5 x ATR
- **Mức 3**: Đóng nốt 40% còn lại khi lợi nhuận đạt 4.0 x ATR

## Tùy Chỉnh Hệ Thống

### Thông qua Giao Diện Web
1. Truy cập trang quản lý: http://localhost:5000
2. Chọn tab "Cài Đặt" → "Quản Lý Rủi Ro"
3. Chọn mức độ rủi ro và các tùy chỉnh ATR
4. Nhấn "Áp Dụng"

### Thông qua File Cấu Hình
1. Mở file cấu hình: `account_risk_config.json`
2. Thay đổi các thông số trong các mục:
   - `active_risk_level`
   - `atr_settings`
   - `volatility_adjustment`
   - `adaptive_stop_loss`
3. Lưu file và khởi động lại hệ thống

### Thông qua Dòng Lệnh
```bash
# Đặt mức rủi ro
python risk_manager.py --set-risk-level medium

# Thay đổi cài đặt ATR
python risk_manager.py --set-atr-multiplier 2.2 --set-atr-period 14

# Bật/tắt stop loss thích ứng
python risk_manager.py --toggle-adaptive-sl True
```

## Đánh Giá Hiệu Quả Hệ Thống

### So Sánh Các Mức Rủi Ro
```bash
python compare_risk_levels.py --levels very_low,low,medium,high,very_high --period 6m
```

### Đánh Giá Tác Động của ATR
```bash
python evaluate_atr_impact.py --atr-multipliers 1.5,2.0,2.5 --period 3m
```

### Phân Tích Độ Biến Động và Tác Động
```bash
python analyze_volatility_impact.py --symbol BTCUSDT --timeframe 4h --days 30
```

## Lời Khuyên Nâng Cao

1. **Thích nghi với thị trường hiện tại**:
   - Thị trường sideway: Sử dụng mức rủi ro thấp hoặc trung bình
   - Thị trường xu hướng mạnh: Có thể sử dụng mức rủi ro cao hơn

2. **Điều chỉnh theo loại coin**:
   - Coin biến động cao (altcoin): Giảm mức rủi ro, tăng hệ số ATR
   - Coin biến động thấp (Bitcoin): Có thể sử dụng mức rủi ro cao hơn

3. **Thời điểm tối ưu**:
   - Thời điểm tin tức: Tránh giao dịch hoặc giảm đáng kể kích thước vị thế
   - Thời điểm biến động thấp: Thích hợp để mở vị thế với kích thước lớn hơn

4. **Thực hành tốt nhất**:
   - Luôn kiểm tra ATR hiện tại trước khi vào lệnh
   - Không vượt quá 20% tổng vốn trong giao dịch đầu tiên
   - Đánh giá lại chiến lược rủi ro định kỳ, 2-4 tuần một lần
   - Khi thị trường thay đổi mạnh, hãy tạm dừng và đánh giá lại cấu hình ATR