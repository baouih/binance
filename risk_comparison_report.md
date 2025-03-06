# Báo cáo Phân tích Hiệu suất Theo Mức Rủi ro

## 1. Tổng quan

Báo cáo này phân tích hiệu suất giao dịch của hệ thống với các mức rủi ro khác nhau, sử dụng cơ chế rủi ro thích ứng theo điều kiện thị trường. Hiện tại, phân tích tập trung vào hai mức rủi ro đã hoàn thành backtest: 0.5% và 1.5%.

## 2. So sánh Hiệu suất Tổng thể

| Tiêu chí | Rủi ro 0.5% | Rủi ro 1.5% |
|----------|-------------|-------------|
| **Lợi nhuận** | 0.49% | 0.51% |
| **Tổng số giao dịch** | 17 | 3 |
| **Win rate** | 82.35% | 100% |
| **Profit factor** | 2.25 | ∞ |
| **Drawdown tối đa** | 0.32% | 0% |
| **Lợi nhuận trung bình/giao dịch** | 6.25 USDT | 16.98 USDT |
| **Thua lỗ trung bình/giao dịch** | -12.95 USDT | N/A |

## 3. Phân tích Theo Chế độ Thị trường

### 3.1. Rủi ro 0.5%

| Chế độ Thị trường | Số giao dịch | Win rate | Lợi nhuận | Profit factor | Lợi nhuận TB/giao dịch |
|-------------------|--------------|----------|-----------|---------------|------------------------|
| **Ranging** | 11 | 72.73% | 0.06% | 1.16 | 5.63 USDT |
| **Trending** | 2 | 100% | 0.14% | ∞ | 7.15 USDT |
| **Quiet** | 4 | 100% | 0.28% | ∞ | 7.04 USDT |

### 3.2. Rủi ro 1.5%

| Chế độ Thị trường | Số giao dịch | Win rate | Lợi nhuận | Profit factor | Lợi nhuận TB/giao dịch |
|-------------------|--------------|----------|-----------|---------------|------------------------|
| **Ranging** | 1 | 100% | 0.14% | ∞ | 14.22 USDT |
| **Quiet** | 2 | 100% | 0.37% | ∞ | 18.37 USDT |

## 4. Đánh giá Tác động của Rủi ro Thích ứng

Hệ thống tự động điều chỉnh mức rủi ro dựa trên chế độ thị trường phát hiện được:

| Chế độ Thị trường | Điều chỉnh Rủi ro | Chiến lược Ưu tiên |
|-------------------|--------------------|-------------------|
| **Trending** | +20% | Trend Following (70%) |
| **Ranging** | -20% | Mean Reversion (60%) |
| **Volatile** | -40% | Breakout & Volatility Based (40% mỗi loại) |
| **Quiet** | 0% | Mean Reversion & Support/Resistance (40% mỗi loại) |

## 5. So sánh Lợi nhuận Theo Kích thước Vị thế

Với mức rủi ro cao hơn (1.5% so với 0.5%):
- Kích thước vị thế lớn hơn khoảng 3 lần
- Dẫn đến lợi nhuận trung bình/giao dịch cao hơn 2.7 lần (16.98 USDT so với 6.25 USDT)
- Tuy nhiên, hệ thống thực hiện ít giao dịch hơn, có thể do ngưỡng kích hoạt giữ nghiêm ngặt hơn

## 6. Nhận xét Về Hiệu suất Theo Chế độ Thị trường

| Chế độ Thị trường | Nhận xét |
|-------------------|----------|
| **Ranging** | Hiệu suất thấp nhất (win rate 72.73% với rủi ro 0.5%), nhưng vẫn có lợi nhuận. Việc giảm rủi ro xuống 80% trong chế độ này là hợp lý. |
| **Trending** | Hiệu suất rất tốt (win rate 100%), khẳng định việc tăng rủi ro lên 120% trong chế độ này là hợp lý. |
| **Quiet** | Hiệu suất tốt nhất (win rate 100%, lợi nhuận cao nhất), đặc biệt với rủi ro 1.5%. |

## 7. Tóm tắt và Đề xuất

Dựa trên hai mức rủi ro đã phân tích:

1. **Mức rủi ro 0.5%**:
   - Ưu điểm: Nhiều giao dịch hơn, drawdown thấp
   - Nhược điểm: Lợi nhuận trung bình/giao dịch thấp hơn, profit factor thấp hơn
   - Phù hợp với nhà đầu tư thận trọng, ưu tiên bảo toàn vốn

2. **Mức rủi ro 1.5%**:
   - Ưu điểm: Win rate 100%, profit factor vô hạn, lợi nhuận/giao dịch cao
   - Nhược điểm: Ít giao dịch hơn
   - Phù hợp với nhà đầu tư chấp nhận rủi ro cao hơn để có lợi nhuận lớn hơn

3. **Rủi ro thích ứng**:
   - Việc điều chỉnh rủi ro theo chế độ thị trường mang lại hiệu quả rõ rệt
   - Cơ chế tăng rủi ro trong thị trường trending và giảm trong thị trường ranging hoạt động hiệu quả

4. **Đề xuất**:
   - Tiếp tục thử nghiệm với các mức rủi ro còn lại (1.0%, 2.0%, 3.0%)
   - Xem xét tinh chỉnh thêm điều chỉnh rủi ro theo chế độ thị trường
   - Có thể tối ưu hóa thêm các tham số để tăng số lượng giao dịch ở mức rủi ro cao hơn

## 8. Phân tích Biến động Thị trường và Các Giao dịch Cụ thể

Phân tích các giao dịch cụ thể cho thấy:

- Với rủi ro 0.5%, các giao dịch thua lỗ đều xảy ra trong chế độ thị trường "ranging", phản ánh bản chất khó dự đoán của thị trường dao động
- Với rủi ro 1.5%, không có giao dịch thua lỗ, nhưng số lượng giao dịch rất ít (chỉ 3 giao dịch)
- Hệ thống hoạt động đặc biệt hiệu quả trong các thị trường "quiet" và "trending"

---
*Báo cáo được tạo vào: 06/03/2025*