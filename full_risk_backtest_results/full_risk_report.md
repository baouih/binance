# BÁO CÁO BACKTEST ĐẦY ĐỦ 5 MỨC RỦI RO

Ngày thực hiện: 2025-03-27 15:07:53

Timeframe: 1h
Giai đoạn test: 90 ngày

## BẢNG SO SÁNH TỔNG THỂ

| Symbol | Mức rủi ro | Số giao dịch | Win rate | Lợi nhuận | Drawdown | Profit Factor |
|--------|-----------|-------------|----------|-----------|----------|---------------|
| BTC-USD | extremely_low | 125 | 34.40% | 0.11% | 0.24% | 0.98 |
| BTC-USD | low | 125 | 31.20% | 0.99% | 1.11% | 1.08 |
| BTC-USD | medium | 125 | 27.20% | 1.81% | 3.83% | 1.03 |
| BTC-USD | high | 125 | 26.40% | 10.80% | 6.31% | 1.21 |
| BTC-USD | extremely_high | 125 | 20.00% | 24.22% | 19.48% | 1.19 |
| ETH-USD | extremely_low | 137 | 33.58% | -0.36% | 0.72% | 0.72 |
| ETH-USD | low | 137 | 30.66% | -1.39% | 2.43% | 0.74 |
| ETH-USD | medium | 137 | 30.66% | 0.93% | 3.78% | 0.92 |
| ETH-USD | high | 137 | 27.01% | -1.44% | 12.83% | 0.86 |
| ETH-USD | extremely_high | 137 | 21.17% | -8.42% | 35.40% | 0.82 |

## PHÂN TÍCH HIỆU SUẤT THEO MỨC RỦI RO

| Mức rủi ro | Tổng giao dịch | Win rate | Tổng lợi nhuận | Lợi nhuận/Giao dịch | Drawdown TB |
|------------|----------------|----------|----------------|---------------------|------------|
| extremely_low | 262 | 33.97% | $-62.60 | $-0.24 | 0.48% |
| low | 262 | 30.92% | $-186.68 | $-0.71 | 1.77% |
| medium | 262 | 29.01% | $-112.63 | $-0.43 | 3.80% |
| high | 262 | 26.72% | $-61.29 | $-0.23 | 9.57% |
| extremely_high | 262 | 20.61% | $-819.99 | $-3.13 | 27.44% |

## TỶ LỆ LỢI NHUẬN / RỦI RO

| Symbol | extremely_low | low | medium | high | extremely_high |
|--------|--------------|-----|--------|------|---------------|
| BTC-USD | 0.46 | 0.89 | 0.47 | 1.71 | 1.24 |
| ETH-USD | -0.50 | -0.57 | 0.25 | -0.11 | -0.24 |

## KẾT LUẬN VÀ KHUYẾN NGHỊ

1. **Mức rủi ro có lợi nhuận cao nhất**: high
2. **Mức rủi ro có tỷ lệ thắng cao nhất**: extremely_low
3. **Mức rủi ro có tỷ lệ lợi nhuận/rủi ro tốt nhất**: high

### Đề xuất cấu hình tối ưu

Dựa trên phân tích, chúng tôi đề xuất sử dụng mức rủi ro **high** với các thông số sau:

- Rủi ro mỗi giao dịch: 7.0%
- Đòn bẩy tối đa: 10x
- Hệ số ATR cho Stop Loss: 1.0
- Hệ số ATR cho Take Profit: 2.0
- Kích hoạt Trailing Stop: 0.5%
- Callback Trailing Stop: 0.3%

### Đề xuất cải thiện

1. **Cải thiện bộ lọc tín hiệu** để tăng tỷ lệ thắng
2. **Tích hợp phân tích đa khung thời gian** để xác nhận tín hiệu
3. **Tối ưu hóa partial take profit** dựa trên biến động thị trường
4. **Điều chỉnh động các thông số rủi ro** dựa trên hiệu suất gần đây
5. **Thêm bộ lọc khối lượng giao dịch** để xác nhận các tín hiệu breakout
