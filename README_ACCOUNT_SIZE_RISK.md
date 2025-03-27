# Hướng dẫn quản lý rủi ro dựa trên kích thước tài khoản

## Khái quát

Hệ thống giao dịch của chúng tôi được thiết kế để tự động điều chỉnh tham số rủi ro dựa trên kích thước tài khoản. Các tài khoản nhỏ (dưới $500) sẽ áp dụng mức rủi ro cao hơn để tối đa hóa khả năng tăng trưởng, trong khi các tài khoản lớn sẽ sử dụng mức rủi ro thấp hơn để bảo toàn vốn.

## Mức rủi ro dựa trên kích thước tài khoản

| Kích thước tài khoản | Mức rủi ro    | Rủi ro/Giao dịch | Đòn bẩy | Số vị thế tối đa | Coin đề xuất     |
|--------------------|--------------|-----------------|---------|-----------------|-----------------|
| $100               | Cực kỳ cao    | 30%             | 30x     | 2               | BTC, ETH        |
| $200               | Cực kỳ cao    | 25%             | 26x     | 2               | BTC, ETH        |
| $300               | Cao           | 20%             | 12x     | 2               | BTC, ETH        |
| $500               | Cao           | 15%             | 11x     | 3               | BTC, ETH, BNB, SOL |
| $1,000             | Trung bình     | 8%              | 5x      | 5               | BTC, ETH, BNB, SOL, DOGE, XRP, ADA |
| $3,000             | Trung bình     | 5%              | 5x      | 5               | BTC, ETH, BNB, SOL, DOGE, XRP, ADA |
| $5,000             | Thấp          | 3%              | 2x      | 8               | BTC, ETH, BNB, SOL, DOGE, XRP, ADA, DOT, AVAX, LINK |
| $10,000            | Thấp          | 1.5%            | 2x      | 8               | BTC, ETH, BNB, SOL, DOGE, XRP, ADA, DOT, AVAX, LINK |
| $50,000            | Cực kỳ thấp    | 0.5%            | 1x      | 8               | BTC, ETH, BNB, SOL, DOGE, XRP, ADA, DOT, AVAX, LINK |

## Đặc điểm và khuyến nghị

### Tài khoản siêu nhỏ ($100 - $300)
- **Mức rủi ro:** Cực kỳ cao (20-30% mỗi giao dịch)
- **Đặc điểm:** 
  - Sử dụng đòn bẩy cao (12-30x)
  - Chỉ giao dịch BTC và ETH để tập trung vốn
  - Tối đa 2 vị thế đồng thời
  - Mục tiêu lợi nhuận cao (1.5x so với tài khoản thông thường)
- **Khuyến nghị:**
  - Chuẩn bị tinh thần cho biến động lớn về vốn
  - Giao dịch chỉ BTC và ETH để giảm thiểu rủi ro altcoin
  - Nên sử dụng trailing stop để tối ưu lợi nhuận
  - Chốt lời từng phần khi có lãi

### Tài khoản nhỏ ($300 - $1,000)
- **Mức rủi ro:** Cao (8-15% mỗi giao dịch)
- **Đặc điểm:**
  - Đòn bẩy trung bình đến cao (5-11x)
  - Có thể giao dịch 3-5 coin chính
  - Tối đa 3-5 vị thế đồng thời
- **Khuyến nghị:**
  - Đa dạng hóa coin giao dịch nhưng vẫn ưu tiên các coin lớn
  - Áp dụng chiến lược quản lý vốn tốt
  - Đặt Stop Loss chặt chẽ

### Tài khoản trung bình ($1,000 - $5,000)
- **Mức rủi ro:** Trung bình (3-8% mỗi giao dịch)
- **Đặc điểm:**
  - Đòn bẩy trung bình (2-5x)
  - Có thể giao dịch nhiều loại coin
  - Áp dụng nhiều chiến lược khác nhau
- **Khuyến nghị:**
  - Kết hợp nhiều chiến lược thị trường khác nhau
  - Đa dạng hóa danh mục giao dịch
  - Cân bằng giữa lợi nhuận và bảo toàn vốn

### Tài khoản lớn ($5,000 trở lên)
- **Mức rủi ro:** Thấp đến cực kỳ thấp (0.5-3% mỗi giao dịch)
- **Đặc điểm:**
  - Đòn bẩy thấp (1-2x)
  - Giao dịch đa dạng coin
  - Tập trung vào bảo toàn vốn
- **Khuyến nghị:**
  - Ưu tiên chiến lược bảo toàn vốn
  - Phân bổ vốn đều cho nhiều coin và chiến lược
  - Duy trì tỷ lệ thắng cao hơn là lợi nhuận lớn

## Cách sử dụng

Hệ thống sẽ tự động nhận diện kích thước tài khoản của bạn và áp dụng mức rủi ro phù hợp. Tuy nhiên, bạn có thể điều chỉnh mức rủi ro thông qua tab "Quản lý rủi ro" trong giao diện desktop.

1. Mở ứng dụng desktop
2. Chuyển đến tab "Quản lý rủi ro"
3. Chọn mức rủi ro phù hợp hoặc để hệ thống tự động điều chỉnh
4. Nhấn "Áp dụng cài đặt rủi ro"

## Cảnh báo

Việc sử dụng mức rủi ro cao có thể dẫn đến mất vốn nhanh chóng. Đặc biệt với tài khoản nhỏ ($100-$300), mức rủi ro cực cao (20-30%) có thể dẫn đến mất đến 60-90% tài khoản nếu gặp phải một chuỗi thua lỗ.

**Chỉ sử dụng mức rủi ro cao nếu bạn chấp nhận rủi ro và có khả năng chịu đựng biến động lớn về vốn.**

## Kết luận

Hệ thống quản lý rủi ro tự động dựa trên kích thước tài khoản giúp tối ưu hóa chiến lược giao dịch cho từng loại tài khoản. Tài khoản nhỏ được thiết kế để tăng trưởng nhanh với rủi ro cao hơn, trong khi tài khoản lớn được bảo vệ với mức rủi ro thấp hơn.

Để có hiệu suất tốt nhất, hãy tuân thủ các khuyến nghị về coin giao dịch và số lượng vị thế tương ứng với kích thước tài khoản của bạn.