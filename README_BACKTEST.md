# Hướng dẫn thực hiện backtest cho tài khoản nhỏ

Tài liệu này hướng dẫn cách thực hiện backtest và phân tích hiệu suất giao dịch cho tài khoản nhỏ ($100-$300) trên thị trường crypto.

## Mục lục

1. [Tổng quan](#tổng-quan)
2. [Cài đặt và thiết lập](#cài-đặt-và-thiết-lập)
3. [Chạy backtest cơ bản](#chạy-backtest-cơ-bản)
4. [Phân tích nhiều cấu hình](#phân-tích-nhiều-cấu-hình)
5. [Tạo báo cáo và biểu đồ](#tạo-báo-cáo-và-biểu-đồ)
6. [Đọc và phân tích kết quả](#đọc-và-phân-tích-kết-quả)
7. [Tối ưu hóa chiến lược](#tối-ưu-hóa-chiến-lược)

## Tổng quan

Hệ thống backtest cho tài khoản nhỏ cho phép bạn:

- Phân tích hiệu suất giao dịch với các kích thước tài khoản khác nhau ($100, $200, $300)
- Kiểm thử nhiều cấu hình đòn bẩy và mức rủi ro
- Xác định các cặp tiền có hiệu suất tốt nhất cho từng kích thước tài khoản
- Tối ưu hóa cơ cấu danh mục đầu tư và chiến lược giao dịch
- Tạo báo cáo chi tiết với biểu đồ và bảng thống kê

## Cài đặt và thiết lập

### Yêu cầu

- Python 3.8+
- Binance API key (Testnet hoặc thật)
- Các thư viện Python trong `requirements.txt`

### Thiết lập môi trường

1. Đảm bảo rằng tất cả các thư viện cần thiết đã được cài đặt:
   ```bash
   pip install -r requirements.txt
   ```

2. Cấu hình API keys trong file `.env` (hoặc sửa trong `account_config.json`):
   ```
   BINANCE_TESTNET_API_KEY=your_testnet_api_key
   BINANCE_TESTNET_API_SECRET=your_testnet_api_secret
   ```

3. Kiểm tra tệp cấu hình `account_config.json` để đảm bảo thiết lập đúng cho tài khoản nhỏ:
   - Đòn bẩy đúng cho từng kích thước tài khoản
   - Danh sách cặp tiền phù hợp
   - Thiết lập Stop Loss và Take Profit

## Chạy backtest cơ bản

### Backtest cho một cấu hình

Để chạy backtest cho một kích thước tài khoản và khung thời gian cụ thể:

```bash
python backtest_small_account_strategy.py --account-size 100 --timeframe 1h --start-date 2024-12-01 --end-date 2025-03-01
```

Tham số:
- `--account-size`: Kích thước tài khoản ($100, $200, $300...)
- `--timeframe`: Khung thời gian (1m, 5m, 15m, 1h, 4h, 1d)
- `--start-date`: Ngày bắt đầu (YYYY-MM-DD)
- `--end-date`: Ngày kết thúc (YYYY-MM-DD)

### Xem kết quả backtest

Kết quả backtest sẽ được lưu trong thư mục `backtest_results` và biểu đồ trong `backtest_charts`. Bạn có thể mở các file JSON để xem thông tin chi tiết hoặc xem biểu đồ để trực quan hóa kết quả.

## Phân tích nhiều cấu hình

### Chạy backtest cho nhiều cấu hình

Để phân tích nhiều kích thước tài khoản và khung thời gian cùng lúc:

```bash
python run_multi_account_backtest.py --account-sizes 100 200 300 --timeframes 1h 4h --start-date 2024-12-01 --end-date 2025-03-01
```

Tham số:
- `--account-sizes`: Danh sách kích thước tài khoản
- `--timeframes`: Danh sách khung thời gian
- `--start-date`: Ngày bắt đầu (YYYY-MM-DD)
- `--end-date`: Ngày kết thúc (YYYY-MM-DD)

### Chạy tất cả các bài kiểm thử

Để chạy tất cả các bài kiểm thử và tạo báo cáo tổng hợp:

```bash
./run_all_tests.sh
```

Script này sẽ tự động:
1. Chạy backtest cho các kích thước tài khoản $100, $200, $300
2. Phân tích các khung thời gian 1h và 4h
3. Tạo báo cáo tổng hợp và biểu đồ so sánh
4. Lưu tất cả kết quả vào các thư mục tương ứng

## Tạo báo cáo và biểu đồ

### Tạo báo cáo HTML

Để tạo báo cáo tổng hợp dạng HTML:

```bash
python generate_trading_report.py
```

Báo cáo này sẽ bao gồm:
- Bảng so sánh hiệu suất theo kích thước tài khoản
- Top 20 cặp tiền có hiệu suất tốt nhất
- So sánh các cấu hình khác nhau
- Biểu đồ heatmap phân tích lợi nhuận, tỷ lệ thắng và profit factor

### Tùy chỉnh báo cáo

Bạn có thể tùy chỉnh báo cáo bằng cách:

```bash
python generate_trading_report.py --results-dir custom_results --summary-dir custom_summary
```

Báo cáo sẽ được lưu trong thư mục `reports`.

## Đọc và phân tích kết quả

Khi đọc kết quả, hãy chú ý đến các chỉ số quan trọng:

1. **Lợi nhuận ròng (Net Profit)**: Tổng lợi nhuận sau tất cả các giao dịch
2. **Tỷ lệ thắng (Win Rate)**: Tỷ lệ giao dịch có lãi trên tổng số giao dịch
3. **Profit Factor**: Tỷ lệ giữa tổng lợi nhuận và tổng lỗ
4. **Drawdown tối đa**: Mức sụt giảm lớn nhất từ đỉnh cũ
5. **Sharpe Ratio**: Chỉ số đánh giá lợi nhuận so với rủi ro

Bạn nên so sánh các chỉ số này giữa các cấu hình khác nhau để tìm ra cấu hình tối ưu cho tài khoản của mình.

## Tối ưu hóa chiến lược

Dựa trên kết quả backtest, bạn có thể tối ưu hóa chiến lược bằng cách:

1. Điều chỉnh đòn bẩy và mức rủi ro cho phù hợp với kích thước tài khoản
2. Tập trung vào các cặp tiền có hiệu suất tốt nhất
3. Tùy chỉnh tham số Stop Loss và Take Profit
4. Điều chỉnh số lượng vị thế tối đa cho từng kích thước tài khoản
5. Thử nghiệm các khung thời gian và chiến lược khác nhau

Sau khi tối ưu hóa, bạn nên chạy lại backtest để xác nhận cải thiện trong hiệu suất.