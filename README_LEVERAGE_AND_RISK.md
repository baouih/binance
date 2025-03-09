# Hướng dẫn quản lý rủi ro và đòn bẩy

## Nguyên tắc cơ bản về đòn bẩy

Khi sử dụng đòn bẩy trong giao dịch futures, phần trăm lợi nhuận và lỗ sẽ được nhân lên theo tỷ lệ đòn bẩy. Điều này có nghĩa:

- Đòn bẩy 5x: Biến động giá 1% = Biến động vốn 5%
- Đòn bẩy 10x: Biến động giá 1% = Biến động vốn 10%
- Đòn bẩy 20x: Biến động giá 1% = Biến động vốn 20%

## Cách điều chỉnh Stop Loss và Take Profit theo đòn bẩy

Khi sử dụng đòn bẩy, cần điều chỉnh phần trăm SL/TP để đạt được mức rủi ro/phần thưởng thực tế mong muốn:

### Ví dụ với đòn bẩy 5x:

- **Mục tiêu thực tế**: Rủi ro 5% vốn, Phần thưởng 7.5% vốn
- **Điều chỉnh theo đòn bẩy**: 
  * Stop Loss = 5% ÷ 5x = 1% (từ giá vào)
  * Take Profit = 7.5% ÷ 5x = 1.5% (từ giá vào)

Nếu giá giảm 1%, với đòn bẩy 5x, bạn sẽ mất 5% vốn.
Nếu giá tăng 1.5%, với đòn bẩy 5x, bạn sẽ lãi 7.5% vốn.

### Ví dụ với đòn bẩy 10x:

- **Mục tiêu thực tế**: Rủi ro 5% vốn, Phần thưởng 7.5% vốn
- **Điều chỉnh theo đòn bẩy**:
  * Stop Loss = 5% ÷ 10x = 0.5% (từ giá vào)
  * Take Profit = 7.5% ÷ 10x = 0.75% (từ giá vào)

## Tính toán mức điều chỉnh

Công thức chung:
```
Phần trăm điều chỉnh = Phần trăm mục tiêu thực tế ÷ Đòn bẩy
```

### Bảng tham khảo tỷ lệ phần trăm điều chỉnh:

| Đòn bẩy | Rủi ro thực tế 5% | Phần thưởng thực tế 7.5% |
|---------|-------------------|---------------------------|
| 3x      | 1.67%             | 2.5%                      |
| 5x      | 1%                | 1.5%                      |
| 10x     | 0.5%              | 0.75%                     |
| 20x     | 0.25%             | 0.375%                    |

## Các lưu ý quan trọng

1. **Đòn bẩy cao hơn = Biên độ điều chỉnh thấp hơn**:
   - Khi sử dụng đòn bẩy cao, cần đặt SL/TP gần giá vào hơn
   - Với đòn bẩy 20x, chỉ cần giá biến động 0.25% ngược chiều có thể gây lỗ 5%

2. **Quản lý kích thước vị thế**:
   - Không nên sử dụng quá 5% số dư tài khoản cho một vị thế
   - Với đòn bẩy cao, nên giảm % số dư sử dụng cho mỗi vị thế

3. **Tỷ lệ Risk:Reward tối thiểu**:
   - Luôn duy trì tỷ lệ R:R tối thiểu 1:1.5
   - Lý tưởng nhất là R:R = 1:2 hoặc cao hơn

## Ứng dụng trong hệ thống

Hệ thống giao dịch tự động của chúng ta đã được tích hợp tính năng điều chỉnh SL/TP theo đòn bẩy:

```python
# Điều chỉnh % theo đòn bẩy
adjusted_sl_percent = risk_percent / leverage
adjusted_tp_percent = reward_percent / leverage

# Tính giá SL/TP dựa trên % đã điều chỉnh
sl_price = current_price * (1 - adjusted_sl_percent / 100)
tp_price = current_price * (1 + adjusted_tp_percent / 100)
```

## Chiến lược Trailing Stop

Trailing Stop là cách hiệu quả để bảo vệ lợi nhuận khi thị trường biến động có lợi:

1. **Thiết lập Activation Price**:
   - Kích hoạt trailing stop khi giá tăng đến mức nhất định (ví dụ: +2% từ giá vào)
   - Mức kích hoạt cũng cần được điều chỉnh theo đòn bẩy

2. **Callback Rate**:
   - Tỷ lệ % mà giá có thể đảo chiều từ mức cao nhất trước khi kích hoạt
   - Với đòn bẩy 5x, callback rate 1% tương đương với 5% lợi nhuận