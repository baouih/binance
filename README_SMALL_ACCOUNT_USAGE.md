# Hướng dẫn sử dụng hệ thống giao dịch cho tài khoản nhỏ

## Tổng quan
Hệ thống này được tối ưu hóa đặc biệt cho các tài khoản giao dịch có kích thước từ $100-$1000, với các chiến lược và quản lý rủi ro được điều chỉnh dựa trên kích thước tài khoản.

## Đặc điểm chính
- **Quản lý rủi ro thích ứng**: Tự động điều chỉnh đòn bẩy và % rủi ro dựa trên kích thước tài khoản
- **Chọn cặp tiền tối ưu**: Ưu tiên altcoin cho tài khoản dưới $700 và ưu tiên BTC cho tài khoản trên $700
- **Chiến lược thị trường đi ngang**: Tập trung vào các chiến lược đặc biệt cho thị trường sideway
- **Lựa chọn khung thời gian thông minh**: Điều chỉnh thời gian giao dịch dựa trên phân tích dữ liệu lịch sử

## Cài đặt cho các kích thước tài khoản
- **$100-$200**: Đòn bẩy 15-20x, Rủi ro 15-20%, Tối đa 2 vị thế, Không giao dịch BTC
- **$300-$500**: Đòn bẩy 7-10x, Rủi ro 7-10%, Tối đa 3-5 vị thế, Không giao dịch BTC
- **$500-$700**: Đòn bẩy 5-7x, Rủi ro 5-7%, Tối đa 5-6 vị thế, Không giao dịch BTC
- **$700+**: Đòn bẩy 5x, Rủi ro 5%, Tối đa 8 vị thế, Ưu tiên giao dịch BTC

## Chiến lược tối ưu cho thị trường đi ngang
1. **Bollinger Bounce**: Giao dịch khi giá chạm band dưới (mua) hoặc band trên (bán) kết hợp với chỉ báo RSI
2. **RSI Reversal**: Giao dịch dựa trên tín hiệu đảo chiều của chỉ báo RSI khi quá mua/quá bán

## Cách sử dụng
Chạy hệ thống với kích thước tài khoản cụ thể:
```
python account_size_based_strategy.py --balance 200
```

Chạy hệ thống và thực hiện giao dịch thật:
```
python account_size_based_strategy.py --balance 200 --execute
```

Chỉ định giờ và ngày giao dịch tối ưu:
```
python account_size_based_strategy.py --balance 200 --hours 0 8 16 --days 1 2 3
```

## Theo dõi hiệu suất
Sử dụng lệnh sau để xem hiệu suất của tài khoản:
```
python generate_performance_report.py --account-size 200
```

## Hướng dẫn tinh chỉnh
1. Chỉnh sửa tệp `configs/strategy_market_config.json` để điều chỉnh tham số chiến lược
2. Chạy các bài kiểm tra để tìm các tham số tối ưu cho điều kiện thị trường hiện tại:
   ```
   python optimize_small_account_trading.py --account-size 200 --market-type ranging
   ```

## Lưu ý quan trọng
- Luôn sử dụng stop loss để hạn chế rủi ro
- Đối với tài khoản dưới $700, tập trung vào các altcoin có thanh khoản cao
- Đối với tài khoản trên $700, ưu tiên giao dịch BTC cho sự ổn định
- Hạn chế giao dịch trong thị trường biến động cao, trừ khi chiến lược được tối ưu hóa đặc biệt
- Chiến lược bollinger_bounce được tối ưu hóa cho thị trường đi ngang
- Đòn bẩy cao cho tài khoản nhỏ sẽ giúp tăng lợi nhuận tiềm năng, nhưng cũng tăng rủi ro
- Dành thời gian cân nhắc kỹ lưỡng trước khi giao dịch thực tế với vốn thật

## Ưu tiên BTC cho tài khoản trên $700
- Tài khoản trên $700 sẽ tự động ưu tiên BTC trước, sau đó mới đến altcoin
- BTC thường ổn định hơn và phù hợp với chiến lược dài hạn hơn
- Đòn bẩy thấp hơn (5x) giúp giảm thiểu rủi ro khi giao dịch BTC
- Chiến lược trend_following có hiệu quả tốt với BTC trong thị trường xu hướng