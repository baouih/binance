# Hướng Dẫn Kiểm Thử Khắc Nghiệt (Stress Testing)

## Giới Thiệu

Tài liệu này hướng dẫn cách thực hiện kiểm thử khắc nghiệt (stress testing) đối với hệ thống giao dịch để đảm bảo tính ổn định và độ tin cậy trong các điều kiện thị trường cực đoan và các tình huống lỗi.

## Tại Sao Cần Kiểm Thử Khắc Nghiệt

Kiểm thử thông thường thường chỉ đánh giá hệ thống trong điều kiện thị trường bình thường. Tuy nhiên, các sự cố nghiêm trọng thường xảy ra trong các điều kiện đặc biệt như:

1. **Flash crash** - Sụp đổ thị trường đột ngột (BTC -20% trong vài phút)
2. **Biến động cực cao** - Thị trường di chuyển mạnh liên tục giữa các vùng giá
3. **Độ trễ API cao** - Khi sàn giao dịch quá tải và phản hồi chậm
4. **Lỗi API ngẫu nhiên** - Khi kết nối bị gián đoạn hoặc có lỗi từ phía sàn
5. **Rò rỉ bộ nhớ** - Khi hệ thống chạy liên tục trong thời gian dài

## Các Bài Kiểm Tra Được Triển Khai

Module `stress_test_system.py` triển khai các bài kiểm tra sau:

### 1. Kiểm Tra Phát Hiện Thị Trường Sideway

Kiểm tra khả năng phát hiện chính xác các loại thị trường khác nhau:
- Thị trường thông thường
- Flash crash (sụp đổ nhanh)
- Price spike (tăng giá đột ngột)
- Sideways squeeze (thị trường sideway cực đoan)
- High volatility (biến động cao)
- Low liquidity (thanh khoản thấp)

### 2. Kiểm Tra Trailing Stop Trong Điều Kiện Cực Đoan

Đánh giá khả năng bảo vệ lợi nhuận của trailing stop trong các điều kiện thị trường khắc nghiệt:
- Flash crash - Thị trường sụp đổ nhanh chóng
- Price spike - Thị trường tăng mạnh đột ngột
- High volatility - Thị trường biến động dữ dội

### 3. Kiểm Tra Xử Lý Lỗi API

Đánh giá khả năng chịu lỗi của hệ thống khi API gặp sự cố:
- API thất bại với tỷ lệ cao (80%)
- API phản hồi chậm (độ trễ cao)
- API không khả dụng khi cần hủy lệnh

### 4. Kiểm Tra Sử Dụng Bộ Nhớ

Phát hiện các vấn đề tiềm ẩn về quản lý bộ nhớ:
- Rò rỉ bộ nhớ khi tạo nhiều vị thế
- Tăng bộ nhớ bất thường khi cập nhật giá liên tục
- Không giải phóng bộ nhớ khi đóng vị thế

### 5. Kiểm Tra An Toàn Đa Luồng

Đánh giá tính ổn định khi nhiều luồng cùng truy cập và cập nhật:
- Nhiều luồng cùng cập nhật giá
- Kiểm tra tính nhất quán của dữ liệu
- Phát hiện race condition

## Cách Chạy Kiểm Thử

### Chạy Tất Cả Các Bài Kiểm Tra

```bash
python stress_test_system.py
```

### Chạy Từng Bài Kiểm Tra Riêng

```python
from stress_test_system import StressTestRunner

# Tạo đối tượng kiểm thử
tester = StressTestRunner()

# Chạy kiểm tra phát hiện thị trường sideway
results = tester.test_sideways_detection()
print(results['status'])  # 'passed', 'warning', 'failed', hoặc 'error'

# Chạy kiểm tra trailing stop
results = tester.test_trailing_stop_extreme()

# Chạy kiểm tra xử lý lỗi API
results = tester.test_api_failure_handling()

# Chạy kiểm tra sử dụng bộ nhớ
results = tester.test_memory_usage()

# Chạy kiểm tra an toàn đa luồng
results = tester.test_multithreading_safety()
```

## Phân Tích Kết Quả Kiểm Thử

Sau khi chạy, các kết quả được lưu trong thư mục `stress_test_results`, bao gồm:

1. **File JSON kết quả chi tiết** - Chứa tất cả thông tin từ các bài kiểm tra
2. **Biểu đồ phân tích thị trường** - Tạo bởi bài kiểm tra phát hiện thị trường sideway

Mỗi bài kiểm tra có thể có một trong các trạng thái sau:
- **PASSED** - Hệ thống hoạt động như mong đợi
- **WARNING** - Phát hiện vấn đề tiềm ẩn có thể gây sự cố trong tương lai
- **FAILED** - Phát hiện lỗi nghiêm trọng cần được sửa ngay
- **ERROR** - Không thể hoàn thành bài kiểm tra do lỗi không mong đợi

## Cải Thiện Sau Khi Phát Hiện Vấn Đề

Dựa trên kết quả kiểm thử, các cải thiện phổ biến bao gồm:

1. **Cải thiện xử lý ngoại lệ** - Thêm các khối try-except để xử lý các lỗi API
2. **Tối ưu bộ nhớ** - Sửa các vấn đề rò rỉ bộ nhớ, theo dõi và giới hạn dữ liệu lịch sử
3. **Tăng đồng bộ hóa** - Cải thiện các cơ chế lock để tránh xung đột đa luồng
4. **Thêm cơ chế fallback** - Triển khai các chiến lược dự phòng khi API không khả dụng
5. **Cải thiện giới hạn và bảo vệ** - Thêm các giới hạn an toàn và tính năng tự động ngắt

## Thực Hành Tốt Nhất Cho Stress Testing

1. **Chạy thường xuyên** - Tự động hóa kiểm thử và chạy sau mỗi thay đổi lớn
2. **Thêm kịch bản mới** - Liên tục cập nhật kịch bản kiểm thử dựa trên các sự cố thực tế
3. **Theo dõi hiệu suất** - Đo thời gian xử lý và tài nguyên sử dụng trong quá trình kiểm thử
4. **Kiểm thử nhiều cài đặt** - Kiểm thử với các tham số và cấu hình khác nhau
5. **Mô phỏng sự cố thực tế** - Tạo kịch bản dựa trên các sự cố thị trường đã xảy ra

## Tùy Chỉnh Các Bài Kiểm Tra

Bạn có thể tùy chỉnh các bài kiểm tra bằng cách sửa đổi các tham số trong module `stress_test_system.py`:

- Thay đổi `position_count` và `update_count` để kiểm tra với khối lượng khác nhau
- Điều chỉnh `failure_rate` để mô phỏng các mức độ lỗi API khác nhau
- Thêm các kịch bản thị trường mới vào phương thức `generate_extreme_market_data`