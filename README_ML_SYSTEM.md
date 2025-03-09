# Hệ thống ML cho Giao dịch Tiền điện tử

Hệ thống học máy tích hợp cho giao dịch tiền điện tử với chiến lược rủi ro cao.

## Tổng quan

Hệ thống ML được thiết kế để nâng cao hiệu suất của chiến lược giao dịch rủi ro cao bằng cách:

1. **Dự đoán xu hướng giá** sử dụng các thuật toán học máy
2. **Kết hợp với phân tích kỹ thuật** để tạo ra tín hiệu mạnh mẽ hơn
3. **Áp dụng quản lý rủi ro thông minh** dựa trên các mô hình ML
4. **Tối ưu hóa chiến lược** cho từng loại tiền và khung thời gian

## Cấu trúc hệ thống

```
├── ml_models/                  # Thư mục chứa các mô hình ML đã huấn luyện
├── ml_charts/                  # Biểu đồ hiệu suất mô hình ML
├── ml_results/                 # Kết quả đánh giá mô hình ML
├── ml_test_charts/             # Biểu đồ backtest chiến lược ML
├── ml_test_results/            # Kết quả backtest chiến lược ML
├── ml_signals/                 # Tín hiệu ML được tạo ra
├── ml_pipeline_results/        # Kết quả chạy pipeline ML
├── enhanced_ml_trainer.py      # Công cụ huấn luyện mô hình ML
├── ml_strategy_tester.py       # Công cụ kiểm thử chiến lược ML
├── run_ml_pipeline.py          # Công cụ chạy pipeline ML
├── ml_integration_manager.py   # Quản lý tích hợp ML vào hệ thống giao dịch
├── run_complete_ml_pipeline.py # Công cụ chạy toàn bộ quy trình ML
├── start_ml_integration.py     # Khởi động dịch vụ tích hợp ML
└── deploy_ml_to_production.py  # Công cụ triển khai ML vào sản phẩm
```

## Quy trình sử dụng

### 1. Huấn luyện Mô hình ML

```bash
# Huấn luyện cho tất cả các coin thanh khoản cao
python run_complete_ml_pipeline.py

# Huấn luyện cho một số coin cụ thể
python run_complete_ml_pipeline.py --coins BTCUSDT ETHUSDT

# Huấn luyện với tối ưu hóa siêu tham số (mất nhiều thời gian hơn)
python run_complete_ml_pipeline.py --optimize
```

### 2. Xem kết quả huấn luyện

Sau khi huấn luyện, bạn có thể kiểm tra kết quả trong các thư mục:
- `ml_results/` - Chứa các file JSON với các chỉ số hiệu suất
- `ml_charts/` - Chứa các biểu đồ trực quan hóa hiệu suất
- `ml_test_results/` - Chứa các kết quả backtest
- `ml_pipeline_results/` - Chứa cấu hình triển khai

### 3. Tích hợp vào hệ thống giao dịch

```bash
# Khởi động dịch vụ tích hợp ML (chạy nền)
python start_ml_integration.py

# Khởi động với khoảng thời gian cập nhật tùy chỉnh
python start_ml_integration.py --interval 30  # cập nhật mỗi 30 phút

# Chạy một lần không chạy nền
python start_ml_integration.py --run-once

# Dừng dịch vụ
python start_ml_integration.py --stop

# Cài đặt vào cron để chạy tự động
python start_ml_integration.py --install
```

### 4. Triển khai vào môi trường sản xuất

```bash
# Triển khai toàn bộ hệ thống ML
python deploy_ml_to_production.py

# Triển khai không khởi động dịch vụ
python deploy_ml_to_production.py --no-service

# Khôi phục triển khai trước đó
python deploy_ml_to_production.py --rollback
```

## Coin hỗ trợ

Mặc định, hệ thống hỗ trợ các coin thanh khoản cao sau:
- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- ADAUSDT
- XRPUSDT
- DOGEUSDT
- DOTUSDT
- AVAXUSDT
- MATICUSDT

## Khung thời gian hỗ trợ

Mặc định, hệ thống hỗ trợ các khung thời gian sau:
- 1h
- 4h

## Các thuật toán ML sử dụng

Hệ thống sử dụng kết hợp các thuật toán ML sau:
- Random Forest
- Gradient Boosting
- SVM (Support Vector Machine)

## Tích hợp với chiến lược Rủi ro cao

Hệ thống ML được thiết kế để kết hợp với chiến lược Rủi ro cao hiện có:

1. **Chế độ Xác nhận kép**: Tín hiệu giao dịch chỉ được tạo ra khi cả ML và chiến lược Rủi ro cao đều đồng ý.
2. **Tối ưu hóa tham số rủi ro**: Rủi ro và đòn bẩy được tối ưu hóa dựa trên dự đoán ML.
3. **Phân tích chế độ thị trường**: ML giúp xác định chế độ thị trường hiện tại để điều chỉnh chiến lược.

## Lưu ý

- Đảm bảo API key Binance có quyền truy cập dữ liệu lịch sử đủ dài.
- Huấn luyện mô hình có thể mất nhiều thời gian tùy thuộc vào số lượng coin và khung thời gian.
- Đề xuất thử nghiệm trên testnet trước khi sử dụng trong môi trường thực tế.
- Backup các mô hình ML trước khi triển khai phiên bản mới.

## Quy trình bảo trì

1. **Huấn luyện lại định kỳ**: Nên huấn luyện lại mô hình mỗi 1-3 tháng.
2. **Kiểm thử không ngừng**: Chạy backtest thường xuyên với dữ liệu mới.
3. **Giám sát hiệu suất**: Theo dõi hiệu suất dự đoán của mô hình.
4. **Nâng cấp dần dần**: Nâng cấp từng phần của hệ thống thay vì toàn bộ.