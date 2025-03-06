# Thống Kê Hiệu Suất Theo Mức Rủi Ro

Dưới đây là bảng thống kê hiệu suất backtest của chiến lược combined trên BTCUSDT với các mức rủi ro khác nhau:

| Mức rủi ro | Đòn bẩy | Số giao dịch | Tỷ lệ thắng | Lợi nhuận | Drawdown tối đa | Thua lỗ trung bình |
|:----------:|:-------:|:------------:|:------------:|:----------:|:---------------:|:------------------:|
| 0.2%       | 3x      | 2            | 0.00%        | -$28.58    | 0.29%           | $14.29            |
| 0.5%       | 3x      | 2            | 0.00%        | -$71.45    | 0.71%           | $35.73            |
| 1.0%       | 3x      | 2            | 0.00%        | -$142.90   | 1.43%           | $71.45            |
| 2.0%       | 3x      | 2            | 0.00%        | -$285.81   | 2.86%           | $142.90           |
| 5.0%       | 3x      | 2            | 0.00%        | -$714.52   | 7.15%           | $357.26           |

## Phân Tích Kết Quả

1. **Tương quan trực tiếp**: Có mối tương quan trực tiếp giữa % rủi ro và mức lỗ. Khi rủi ro tăng lên, mức lỗ tăng theo hệ số tương tự.

2. **Hiệu quả quản lý rủi ro**: Với mức rủi ro thấp (0.2%), dù không có giao dịch thắng, tổng lỗ vẫn được giữ ở mức tối thiểu (-0.29%).

3. **Tác động đòn bẩy**: Đòn bẩy 3x đang được sử dụng cho tất cả backtest, nhưng có thể điều chỉnh để giảm rủi ro hơn nữa.

4. **Tỷ lệ thắng thấp**: Tỷ lệ thắng 0% cho thấy chiến lược cần được cải thiện về độ chính xác tín hiệu trước khi tăng mức rủi ro.

## Khuyến Nghị Rủi Ro Tối Ưu

Dựa trên kết quả backtest, mức rủi ro tối ưu cho chiến lược hiện tại là 0.2% đến 0.5% cho mỗi giao dịch. Điều này sẽ giúp bảo toàn vốn tốt hơn trong khi chúng ta tiếp tục cải thiện hiệu suất chiến lược.

Cần lưu ý rằng kết quả này là cho BTCUSDT, và các cặp tiền khác có thể có các mức rủi ro tối ưu khác nhau dựa trên biến động riêng của chúng.

## Hướng Cải Thiện

1. **Tối ưu hóa tham số chiến lược** để tăng tỷ lệ thắng, đây là ưu tiên hàng đầu
2. **Điều chỉnh bộ lọc tín hiệu** để giảm số lượng tín hiệu giả
3. **Xem xét kết hợp thêm chiến lược** phù hợp với chế độ thị trường hiện tại
4. **Thêm trailing stop** để bảo vệ lợi nhuận khi có giao dịch thắng
5. **Tự động điều chỉnh rủi ro** theo biến động thị trường