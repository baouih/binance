# Hướng dẫn sử dụng ứng dụng desktop với kết quả backtest

## Giới thiệu

Ứng dụng desktop Trading System đã được cập nhật với kết quả backtest mới nhất, giúp bạn có thể tham khảo và đánh giá hiệu suất của các chiến lược trước khi giao dịch. Ứng dụng được thiết kế để chạy trên Windows và có thể được cài đặt dễ dàng.

## Cập nhật kết quả backtest

Các kết quả backtest đã được cập nhật vào ứng dụng desktop, bao gồm:

1. **Báo cáo tổng quan**:
   - Tỷ lệ thắng của các chiến lược
   - Đánh giá hiệu suất theo mức độ rủi ro
   - So sánh với chiến lược HODL

2. **Kết quả chi tiết**:
   - Chiến lược Sideways: Tỷ lệ thắng 85-100%
   - Chiến lược Multi-Risk: Tỷ lệ thắng 60-95%
   - Chiến lược Adaptive: Tỷ lệ thắng 65-85%

3. **Biểu đồ phân tích**:
   - Biểu đồ hiệu suất theo thời gian
   - Biểu đồ so sánh các mức độ rủi ro
   - Phân tích drawdown

## Đóng gói và sử dụng trên PC

### Cách đóng gói ứng dụng

1. Đảm bảo đã cài đặt PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Chạy script đóng gói:
   ```
   python package_desktop_app_with_backtest.py
   ```

3. Sau khi hoàn thành, file EXE sẽ được tạo trong thư mục `dist/TradingSystem/`.

4. File ZIP chứa toàn bộ ứng dụng sẽ được tạo trong thư mục `dist_packages/`.

### Cài đặt và chạy

1. Sao chép thư mục `dist/TradingSystem/` hoặc giải nén file ZIP vào máy tính Windows.

2. Chạy file `TradingSystem.exe` để khởi động ứng dụng.

3. Không cần cài đặt thêm, ứng dụng đã bao gồm tất cả thư viện cần thiết.

## Sử dụng tab Backtest

Ứng dụng desktop đã bổ sung tab Backtest với các tính năng sau:

1. **Tóm tắt hiệu suất**:
   - Bảng hiển thị tỷ lệ thắng của các chiến lược
   - Đề xuất chiến lược theo kích thước tài khoản

2. **Báo cáo chi tiết**:
   - Phân tích chi tiết về hiệu suất backtest
   - Đánh giá rủi ro và lợi nhuận
   - Kiểm định hệ thống giao dịch

3. **Biểu đồ kết quả**:
   - Các biểu đồ phân tích backtest
   - So sánh trực quan giữa các chiến lược và mức độ rủi ro

## Đề xuất cấu hình theo kích thước tài khoản

### Tài khoản nhỏ ($100-500)
- **Mức độ rủi ro**: 20-30%
- **Đòn bẩy**: 15-20x
- **Chiến lược phù hợp**: Sideways + Adaptive
- **Lợi nhuận kỳ vọng**: 30-100% mỗi tháng
- **Tỷ lệ thắng mục tiêu**: 50-75%

### Tài khoản trung bình ($500-$5,000)
- **Mức độ rủi ro**: 10-15%
- **Đòn bẩy**: 5-10x
- **Chiến lược phù hợp**: Multi-Risk + Adaptive
- **Lợi nhuận kỳ vọng**: 5-30% mỗi tháng
- **Tỷ lệ thắng mục tiêu**: 70-90%

### Tài khoản lớn (>$5,000)
- **Mức độ rủi ro**: 2-3%
- **Đòn bẩy**: 3-5x
- **Chiến lược phù hợp**: Sideways + Multi-Risk
- **Lợi nhuận kỳ vọng**: 0.5-5% mỗi tháng
- **Tỷ lệ thắng mục tiêu**: 90-100%

## Khắc phục sự cố

1. **Lỗi không hiển thị biểu đồ**:
   - Đảm bảo thư mục `assets` được sao chép đầy đủ
   - Khởi động lại ứng dụng

2. **Lỗi không hiển thị báo cáo**:
   - Kiểm tra thư mục `reports` có đầy đủ các file markdown
   - Đảm bảo file cấu hình `gui_config.json` tồn tại

3. **Ứng dụng không khởi động**:
   - Cài đặt Microsoft Visual C++ Redistributable
   - Kiểm tra các thư viện trong thư mục `TradingSystem`

## Liên hệ hỗ trợ

Nếu bạn gặp bất kỳ vấn đề nào khi sử dụng ứng dụng desktop với kết quả backtest, vui lòng liên hệ để được hỗ trợ kỹ thuật.

---

*Lưu ý: Kết quả backtest không đảm bảo hiệu suất trong tương lai. Vui lòng cân nhắc rủi ro trước khi giao dịch.*