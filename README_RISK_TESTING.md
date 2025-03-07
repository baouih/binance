# Hướng dẫn chạy kiểm thử đa mức rủi ro

Tài liệu này giải thích cách sử dụng các công cụ kiểm thử rủi ro để phân tích hiệu suất các chiến lược giao dịch với 5 mức rủi ro khác nhau (0.5%, 1.0%, 1.5%, 2.0%, 3.0%) trên dữ liệu thực tế 3 tháng gần nhất.

## Chuẩn bị

Trước khi chạy các kiểm thử, đảm bảo rằng cấu hình tài khoản đã được thiết lập chính xác trong `account_config.json` và API Binance Testnet đang hoạt động.

## Kiểm thử một đồng coin duy nhất

Để chạy kiểm thử cho một đồng coin cụ thể:

```bash
./test_single_coin.sh BTCUSDT
```

Hoặc với khung thời gian khác:

```bash
./test_single_coin.sh ETHUSDT 4h
```

Kết quả sẽ được lưu trong thư mục `risk_analysis`:
- Báo cáo: `risk_analysis/BTCUSDT_1h_risk_summary.md`
- Biểu đồ: `risk_analysis/BTCUSDT_1h_risk_comparison.png`

## Kiểm thử theo nhóm đồng coin

Để chạy kiểm thử cho một nhóm đồng coin cụ thể:

```bash
./run_risk_test_by_group.sh 1  # Chạy nhóm 1: BTC, ETH, BNB
```

Các nhóm đã được định nghĩa:
- Nhóm 1: BTCUSDT, ETHUSDT, BNBUSDT
- Nhóm 2: ADAUSDT, SOLUSDT, DOGEUSDT, XRPUSDT
- Nhóm 3: LINKUSDT, AVAXUSDT, DOTUSDT
- Nhóm 4: MATICUSDT, LTCUSDT, ATOMUSDT, UNIUSDT

Báo cáo tổng hợp cho nhóm sẽ được lưu tại:
`risk_analysis/summary/group1_coins_risk_summary.md`

## Kiểm thử tất cả các đồng coin

Để chạy kiểm thử cho tất cả 14 đồng coin theo thứ tự:

```bash
./run_risk_tests_sequentially.sh
```

Quá trình này sẽ mất nhiều thời gian, và các báo cáo sẽ được lưu trong:
`risk_analysis/summary/all_coins_risk_summary.md`

## Tùy chỉnh kiểm thử

Bạn có thể trực tiếp sử dụng script Python để có nhiều tùy chọn hơn:

```bash
python run_single_coin_risk_test.py --symbol BTCUSDT --interval 1h
```

## Cấu trúc kết quả

Sau khi chạy các kiểm thử, kết quả sẽ được tổ chức như sau:

- `backtest_results/`: Chứa các file JSON chi tiết cho từng kiểm thử
- `backtest_charts/`: Chứa các biểu đồ chi tiết từ backtest
- `risk_analysis/`: Chứa báo cáo và biểu đồ so sánh các mức rủi ro
- `risk_analysis/summary/`: Chứa báo cáo tổng hợp các nhóm đồng coin

## Phân tích kết quả

Mỗi báo cáo sẽ hiển thị:
- So sánh hiệu suất giữa các mức rủi ro
- Mức rủi ro tối ưu dựa trên lợi nhuận
- Mức rủi ro với Sharpe ratio tốt nhất
- Mức rủi ro với drawdown thấp nhất
- Khuyến nghị mức rủi ro phù hợp nhất

## Xử lý lỗi

Nếu gặp vấn đề trong quá trình chạy kiểm thử:
- Kiểm tra xem API Binance Testnet có hoạt động không
- Kiểm tra file log `single_coin_risk_test.log`
- Đảm bảo có đủ dữ liệu lịch sử cho khoảng thời gian 3 tháng