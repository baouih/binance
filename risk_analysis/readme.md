# Phân tích rủi ro - Tài liệu hướng dẫn

## Giới thiệu

Thư mục này chứa các công cụ và báo cáo phân tích rủi ro cho hệ thống giao dịch. Mục đích chính là xác định mức rủi ro tối ưu cho từng cặp giao dịch tiền điện tử trong các điều kiện thị trường khác nhau.

## Các công cụ phân tích

Hệ thống cung cấp nhiều công cụ để phân tích hiệu suất với các mức rủi ro khác nhau:

1. **Kiểm thử nhanh (`run_quick_test.py`)**: Phân tích nhanh với dữ liệu 14 ngày gần nhất. Hữu ích cho việc kiểm tra hiệu suất trong điều kiện thị trường hiện tại.

2. **Kiểm thử đơn lẻ (`test_single_coin.sh`)**: Phân tích đầy đủ cho một cặp giao dịch cụ thể.

3. **Kiểm thử tuần tự (`run_risk_tests_sequentially.sh`)**: Phân tích cho nhiều cặp giao dịch, chạy tuần tự và tạo báo cáo tổng hợp.

4. **Phân tích đầy đủ (`run_single_coin_risk_test.py`)**: Phân tích chi tiết với nhiều mức rủi ro khác nhau.

## Các mức rủi ro được kiểm thử

Hệ thống hiện tại kiểm thử 5 mức rủi ro khác nhau:

- 0.5% 
- 1.0%
- 1.5%
- 2.0%
- 3.0%

## Các báo cáo kết quả

Các báo cáo được tạo ra bao gồm:

1. **Báo cáo cho từng cặp giao dịch**: 
   - `[SYMBOL]_[INTERVAL]_risk_summary.md` - Báo cáo đầy đủ
   - `[SYMBOL]_[INTERVAL]_quick_risk_summary.md` - Báo cáo kiểm thử nhanh

2. **Báo cáo tổng hợp**:
   - `multi_coin_risk_summary.md` - Báo cáo tổng hợp cho nhiều cặp giao dịch

3. **Biểu đồ phân tích**:
   - `[SYMBOL]_[INTERVAL]_risk_comparison.png` - Biểu đồ so sánh hiệu suất các mức rủi ro

## Cách sử dụng

### Chạy kiểm thử nhanh

```bash
python run_quick_test.py --symbol BTCUSDT
```

### Chạy kiểm thử đơn lẻ

```bash
./test_single_coin.sh BTCUSDT 1h
```

### Chạy kiểm thử tuần tự cho nhiều cặp giao dịch

```bash
./run_risk_tests_sequentially.sh
```

## Phân tích kết quả 

Dựa trên kết quả kiểm thử, bạn nên xem xét các yếu tố sau để chọn mức rủi ro tối ưu:

1. **Tỷ lệ lợi nhuận/drawdown**: Mức rủi ro có tỷ lệ này cao nhất thường là lựa chọn tốt.

2. **Sharpe Ratio**: Đo lường hiệu suất điều chỉnh theo rủi ro.

3. **Profit Factor**: Tỷ lệ giữa tổng lợi nhuận và tổng thua lỗ.

4. **Điểm tổng hợp**: Kết hợp các chỉ số trên để đưa ra đánh giá toàn diện.

## Lưu ý

Hiệu suất trong quá khứ không đảm bảo cho kết quả trong tương lai. Các mức rủi ro tối ưu có thể thay đổi theo thời gian tùy thuộc vào điều kiện thị trường. Nên thực hiện kiểm thử lại định kỳ để đảm bảo các cài đặt vẫn phù hợp.