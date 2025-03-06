# Hướng Dẫn Chạy Thử Nghiệm Đa Mức Rủi Ro

Tài liệu này hướng dẫn cách chạy thử nghiệm 3 tháng với 5 mức rủi ro khác nhau cho tất cả các cặp tiền đã cấu hình.

## 1. Giới thiệu

Hệ thống này cho phép bạn chạy backtest với 5 mức rủi ro khác nhau (0.5%, 1.0%, 1.5%, 2.0%, và 3.0%) trên tất cả các cặp tiền trong tài khoản của bạn. Việc này giúp xác định mức rủi ro tối ưu cho mỗi cặp tiền, đồng thời hiểu rõ hơn về mối quan hệ giữa rủi ro và lợi nhuận trong các điều kiện thị trường khác nhau.

## 2. Các script chính

Hệ thống này gồm 3 script chính:

1. **run_multi_risk_test.py**: Chạy backtest cho một vài cặp tiền cụ thể với tất cả các mức rủi ro
2. **run_3month_multi_risk_test.py**: Chạy backtest toàn diện cho tất cả cặp tiền và tất cả mức rủi ro
3. **risk_analysis_report.py**: Tạo báo cáo phân tích rủi ro với biểu đồ và khuyến nghị

## 3. Cách sử dụng

### 3.1. Chạy backtest cho một vài cặp tiền

```bash
python run_multi_risk_test.py --symbols BTCUSDT ETHUSDT --interval 1h
```

Tham số:
- `--symbols`: Danh sách các cặp tiền cần test (mặc định: tất cả các cặp trong account_config.json)
- `--interval`: Khung thời gian (mặc định: 1h)
- `--no-adaptive`: Không sử dụng chế độ rủi ro thích ứng (mặc định: sử dụng rủi ro thích ứng)

### 3.2. Chạy backtest toàn diện cho tất cả cặp tiền

```bash
python run_3month_multi_risk_test.py --start_date 2023-12-01 --end_date 2024-03-01
```

Tham số:
- `--symbols`: Danh sách các cặp tiền cần test (mặc định: tất cả các cặp trong account_config.json)
- `--timeframes`: Danh sách khung thời gian (mặc định: 1h, 4h)
- `--start_date`: Ngày bắt đầu (mặc định: 2023-12-01)
- `--end_date`: Ngày kết thúc (mặc định: 2024-03-01)
- `--max_workers`: Số lượng process chạy song song (mặc định: 2)

### 3.3. Tạo báo cáo phân tích rủi ro

```bash
python risk_analysis_report.py
```

Tham số:
- `--input`: File dữ liệu đầu vào (mặc định: backtest_summary/multi_risk_summary.json)
- `--output`: File báo cáo đầu ra (mặc định: risk_analysis/risk_analysis_report.html)

## 4. Kết quả và báo cáo

Sau khi chạy các script, kết quả sẽ được lưu trong các thư mục sau:

- `backtest_results/`: Chứa kết quả chi tiết của từng backtest
- `backtest_summary/`: Chứa báo cáo tổng hợp
- `risk_analysis/`: Chứa phân tích rủi ro và các biểu đồ trực quan
- `risk_analysis/charts/`: Chứa các biểu đồ so sánh
- `risk_analysis/risk_analysis_report.html`: Báo cáo chi tiết dạng HTML

## 5. Giải thích phân tích rủi ro

Phân tích rủi ro giúp bạn hiểu:

1. **Mức rủi ro tối ưu cho mỗi cặp tiền**: Mức rủi ro nào mang lại lợi nhuận cao nhất
2. **Tương quan giữa rủi ro và lợi nhuận**: Liệu việc tăng rủi ro có dẫn đến tăng lợi nhuận không
3. **Phân phối mức rủi ro tối ưu**: Các mức rủi ro nào phổ biến nhất trong danh mục
4. **Top cặp tiền hiệu quả nhất**: Những cặp tiền nào mang lại hiệu suất tốt nhất
5. **Khuyến nghị rủi ro tổng thể**: Mức rủi ro nên áp dụng cho toàn bộ hệ thống

## 6. Khắc phục sự cố

Nếu gặp vấn đề khi chạy các script, hãy kiểm tra các file log sau:

- `multi_risk_test.log`: Log của script run_multi_risk_test.py
- `multi_risk_3month_test.log`: Log của script run_3month_multi_risk_test.py
- `risk_analysis_report.log`: Log của script risk_analysis_report.py

## 7. Ví dụ lệnh chạy

### Chạy test nhanh trên BTC và ETH:

```bash
python run_multi_risk_test.py --symbols BTCUSDT ETHUSDT
```

### Chạy test toàn bộ trong 1 tháng:

```bash
python run_3month_multi_risk_test.py --start_date 2024-02-01 --end_date 2024-03-01
```

### Chạy test tất cả cặp tiền với 3 tháng dữ liệu đầy đủ:

```bash
python run_3month_multi_risk_test.py
```