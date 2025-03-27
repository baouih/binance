# Tổng quan về hệ thống quản lý rủi ro

## Giới thiệu
Hệ thống quản lý rủi ro là một trong những thành phần quan trọng nhất của nền tảng giao dịch. Hệ thống này cho phép điều chỉnh mức độ rủi ro dựa trên kích thước tài khoản và đặc tính của từng loại tiền điện tử, đồng thời cung cấp các cơ chế bảo vệ và tối ưu hóa hiệu suất.

## Cấu trúc hệ thống quản lý rủi ro

### 1. Các mức rủi ro cơ bản
Hệ thống cung cấp 5 mức rủi ro cơ bản:

| Mức rủi ro | Tên | Rủi ro mỗi giao dịch | Đòn bẩy | SL (ATR) | TP (ATR) |
|------------|-----|----------------------|---------|----------|----------|
| extremely_low | Cực kỳ thấp | 0.5-1.0% | 1-2x | 2.0 | 6.0 |
| low | Thấp | 1.5-3.0% | 2-5x | 1.5 | 4.0 |
| medium | Trung bình | 3.0-7.0% | 3-10x | 1.2 | 3.0 |
| high | Cao | 7.0-15.0% | 5-20x | 1.0 | 2.0 |
| extremely_high | Cực kỳ cao | 15.0-50.0% | 10-50x | 0.7 | 1.5 |

### 2. Điều chỉnh theo kích thước tài khoản
Hệ thống tự động điều chỉnh mức rủi ro dựa trên kích thước tài khoản:

| Kích thước tài khoản | Mức rủi ro đề xuất | Rủi ro mỗi giao dịch | Đòn bẩy | Tối đa vị thế |
|----------------------|--------------------|----------------------|---------|---------------|
| $100 | extremely_high | 30.0% | 30x | 2 |
| $200 | extremely_high | 25.0% | 26x | 2 |
| $300 | high | 20.0% | 12x | 2 |
| $500 | high | 15.0% | 11x | 3 |
| $1,000 | medium | 8.0% | 5x | 5 |
| $3,000 | medium | 5.0% | 5x | 5 |
| $5,000 | low | 3.0% | 3x | 8 |
| $10,000 | low | 1.5% | 2x | 10 |
| $50,000 | extremely_low | 0.5% | 1x | 15 |

### 3. Điều chỉnh theo đặc tính coin
Mỗi loại tiền điện tử có đặc tính riêng, ảnh hưởng đến cách thiết lập rủi ro:

#### Bitcoin (BTC)
- Hiệu suất tốt với rủi ro cao
- Mức rủi ro extremely_high: 25% / giao dịch, đòn bẩy 20x
- Tỷ lệ lợi nhuận/drawdown tốt (BTC extremely_high: 24.22% lợi nhuận / 19.48% drawdown)

#### Ethereum (ETH)
- Hiệu suất kém với rủi ro cao
- Giới hạn rủi ro ở "extremely_high": 5% / giao dịch, đòn bẩy 5x
- Hiệu suất kém (ETH extremely_high: -8.42% lợi nhuận / 31.65% drawdown)

### 4. Cơ chế bảo vệ
- Trailing stop loss
- Chốt lời từng phần
- Giới hạn tổng rủi ro mở
- Cảnh báo mức rủi ro cao
- Điều chỉnh tự động theo điều kiện thị trường

## Thư mục cấu hình
Tất cả cấu hình rủi ro được lưu trong thư mục `risk_configs/`:

1. **current_risk_config.json** - Cấu hình rủi ro hiện tại đang được sử dụng
2. **extremely_low_risk_config.json** - Cấu hình cho mức rủi ro cực kỳ thấp
3. **low_risk_config.json** - Cấu hình cho mức rủi ro thấp
4. **medium_risk_config.json** - Cấu hình cho mức rủi ro trung bình
5. **extremely_high_risk_config.json** - Cấu hình cho mức rủi ro cực kỳ cao
6. **BTC_risk_config.json** - Cấu hình rủi ro tối ưu cho Bitcoin
7. **ETH_risk_config.json** - Cấu hình rủi ro tối ưu cho Ethereum
8. **account_XXX_risk_config.json** - Cấu hình cho tài khoản với kích thước XXX

## Kết luận
Hệ thống quản lý rủi ro cung cấp cơ chế toàn diện để tối ưu hóa hiệu suất giao dịch, tự động điều chỉnh theo kích thước tài khoản và đặc tính của từng loại tiền điện tử. Với 5 mức rủi ro cơ bản, người dùng có thể dễ dàng lựa chọn mức rủi ro phù hợp với khẩu vị rủi ro của mình.