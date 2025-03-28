# Báo Cáo Kiểm Thử Nhiều Mức Rủi Ro

## Thông Tin Kiểm Thử

- **Symbol:** BTCUSDT
- **Interval:** 1h
- **Thời gian:** 2025-03-28 08:22:28

## Kết Quả Tổng Hợp

### So sánh lợi nhuận (%)

| Strategy | Risk 10% | Risk 15% | Risk 20% | Risk 25% |
|----------|------------------------------------------------------------|
| multi_risk | 0.03% | 0.07% | 0.09% | 0.07% |
| sideways | 0.10% | 0.18% | 0.25% | 0.42% |
| combined | 0.07% | 0.14% | 0.20% | 0.28% |

### So sánh tỷ lệ thắng (%)

| Strategy | Risk 10% | Risk 15% | Risk 20% | Risk 25% |
|----------|------------------------------------------------------------|
| multi_risk | 94.96% | 91.45% | 74.73% | 63.64% |
| sideways | 100.00% | 100.00% | 100.00% | 100.00% |
| combined | 96.25% | 93.55% | 84.83% | 81.90% |

### So sánh drawdown tối đa (%)

| Strategy | Risk 10% | Risk 15% | Risk 20% | Risk 25% |
|----------|------------------------------------------------------------|
| multi_risk | 0.00% | 0.00% | 0.00% | 0.01% |
| sideways | 0.00% | 0.00% | 0.00% | 0.00% |
| combined | 0.00% | 0.00% | 0.00% | 0.00% |

## Hiệu Suất Theo Điều Kiện Thị Trường


### Chiến lược: multi_risk


#### Risk 10%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 5 | 100.00% | $0.03 |
| SIDEWAYS | 62 | 91.94% | $0.02 |
| BULL | 47 | 100.00% | $0.04 |
| VOLATILE | 5 | 80.00% | $0.02 |

#### Risk 15%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 5 | 100.00% | $0.06 |
| SIDEWAYS | 64 | 87.50% | $0.05 |
| BULL | 43 | 97.67% | $0.08 |
| VOLATILE | 5 | 80.00% | $0.03 |

#### Risk 20%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 4 | 75.00% | $0.08 |
| SIDEWAYS | 49 | 65.31% | $0.07 |
| BULL | 33 | 87.88% | $0.15 |
| VOLATILE | 5 | 80.00% | $0.08 |

#### Risk 25%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 2 | 50.00% | $0.08 |
| SIDEWAYS | 29 | 51.72% | $0.07 |
| BULL | 21 | 76.19% | $0.21 |
| VOLATILE | 3 | 100.00% | $0.16 |

### Chiến lược: sideways


#### Risk 10%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| SIDEWAYS | 177 | 100.00% | $0.06 |

#### Risk 15%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| SIDEWAYS | 163 | 100.00% | $0.11 |

#### Risk 20%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| SIDEWAYS | 142 | 100.00% | $0.18 |

#### Risk 25%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| SIDEWAYS | 127 | 100.00% | $0.33 |

### Chiến lược: combined


#### Risk 10%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 5 | 100.00% | $0.03 |
| SIDEWAYS | 128 | 96.09% | $0.05 |
| BULL | 23 | 100.00% | $0.03 |
| VOLATILE | 4 | 75.00% | $0.02 |

#### Risk 15%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 5 | 100.00% | $0.06 |
| SIDEWAYS | 124 | 93.55% | $0.10 |
| BULL | 22 | 95.45% | $0.07 |
| VOLATILE | 4 | 75.00% | $0.03 |

#### Risk 20%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 4 | 75.00% | $0.08 |
| SIDEWAYS | 116 | 86.21% | $0.15 |
| BULL | 21 | 80.95% | $0.13 |
| VOLATILE | 4 | 75.00% | $0.08 |

#### Risk 25%

| Market Condition | Trades | Win Rate | Avg Profit |
|-----------------|--------|----------|------------|
| NEUTRAL | 2 | 50.00% | $0.08 |
| SIDEWAYS | 97 | 84.54% | $0.26 |
| BULL | 14 | 64.29% | $0.16 |
| VOLATILE | 3 | 100.00% | $0.19 |

## Nhận Xét và Kết Luận

### Những phát hiện chính

- **Lợi nhuận cao nhất:** 0.42% đạt được với chiến lược *sideways* ở mức rủi ro *25%*
- **Tỷ lệ thắng cao nhất:** 100.00% đạt được với chiến lược *sideways* ở mức rủi ro *10%*
- **Tỷ số lợi nhuận/rủi ro tốt nhất:** 212.17 đạt được với chiến lược *combined* ở mức rủi ro *15%*

### Đề xuất chiến lược

- **Chiến lược sideways** với mức rủi ro **25%** cho hiệu suất lợi nhuận tốt nhất.
- **Chiến lược combined** với mức rủi ro **15%** cho tỷ lệ lợi nhuận/rủi ro tốt nhất, phù hợp với nhà đầu tư cẩn trọng.

### Nhận xét về mức rủi ro

- Các mức rủi ro cao (20-25%) cho lợi nhuận trung bình (0.22%) tốt hơn so với các mức rủi ro thấp (10-15%, 0.10%).
- Tuy nhiên, các mức rủi ro cao cũng đi kèm với drawdown lớn hơn, phù hợp với nhà đầu tư chấp nhận biến động lớn.

### Hiệu suất chiến lược thị trường đi ngang

- Chiến lược thị trường đi ngang đạt hiệu suất tốt nhất với mức rủi ro **10%**, cho tỷ lệ thắng **100.00%**.
- Điều này cho thấy chiến lược đã được tối ưu hóa tốt cho thị trường đi ngang.

### Kết luận

- Các chiến lược khác nhau cho hiệu suất tốt trên các phương diện khác nhau:
  * **Lợi nhuận cao nhất:** sideways (25%)
  * **Tỷ lệ thắng cao nhất:** sideways (10%)
  * **Tỷ lệ lợi nhuận/rủi ro tốt nhất:** combined (15%)

### Đề xuất cuối cùng

- **Ưu tiên sử dụng chiến lược combined với mức rủi ro 15%** để cân bằng tốt giữa lợi nhuận và rủi ro.
