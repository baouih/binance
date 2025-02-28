# Binance Futures Trading Bot

## Giới thiệu

Hệ thống giao dịch tự động cao cấp cho Binance Futures với khả năng phân tích thị trường thời gian thực, phát hiện chế độ thị trường và chiến lược học máy nâng cao.

Mã nguồn này bao gồm:
- Giao diện Web dựa trên Flask
- Tích hợp trực tiếp với Binance Futures API
- Theo dõi giá thời gian thực qua WebSocket
- Nhiều chiến lược giao dịch khác nhau
- Hỗ trợ học máy nâng cao với nhiều mô hình
- Phân tích và phát hiện chế độ thị trường
- Tối ưu hóa chiến lược dựa trên điều kiện thị trường

## Thiết lập

### Yêu cầu

- Python 3.8 trở lên
- Binance API key và API secret (cho môi trường thực tế)

### Cài đặt

1. Clone repository
2. Cài đặt các dependencies: `pip install -r requirements.txt`
3. Cấu hình API keys trong file `.env` (tham khảo `.env.example`)
4. Chạy web server: `python main.py`

## Các tính năng

### 1. Chiến lược giao dịch

Bot hỗ trợ nhiều loại chiến lược giao dịch:

- **RSI Strategy**: Giao dịch dựa trên chỉ báo RSI
- **MACD Strategy**: Giao dịch dựa trên tín hiệu MACD
- **EMA Crossover**: Giao dịch dựa trên giao cắt đường trung bình động EMA
- **Bollinger Bands**: Giao dịch dựa trên dải Bollinger
- **ML Strategy**: Giao dịch dựa trên dự đoán học máy
- **Advanced ML Strategy**: Giao dịch dựa trên mô hình học máy nâng cao
- **Combined Strategy**: Kết hợp nhiều chiến lược khác nhau
- **Auto Strategy**: Tự động chọn chiến lược tốt nhất dựa trên chế độ thị trường

### 2. Phát hiện chế độ thị trường

Hệ thống tự động phát hiện các chế độ thị trường khác nhau:

- Trending Up (Xu hướng tăng)
- Trending Down (Xu hướng giảm)
- Ranging (Đi ngang)
- Volatile (Biến động mạnh)
- Breakout (Bứt phá)
- Neutral (Trung tính)

### 3. Học máy nâng cao

Các mô hình học máy được hỗ trợ:

- Random Forest
- Gradient Boosting
- SVM
- Neural Networks
- Ensemble Models

## Sử dụng

### Chạy ở chế độ mô phỏng

```bash
python trading_bot_run.py --symbol BTCUSDT --interval 1h --strategy auto
```

### Chạy với chiến lược học máy nâng cao

```bash
python trading_bot_run.py --symbol BTCUSDT --interval 1h --strategy advanced_ml
```

### Chạy ở chế độ thực

```bash
python trading_bot_run.py --symbol BTCUSDT --interval 1h --strategy auto --live
```

### Sử dụng cấu hình tối ưu

```bash
python trading_bot_run.py --symbol BTCUSDT --interval 1h --config advanced_ml_config.json
```

### Huấn luyện mô hình học máy

```bash
python train_ml_models.py --symbol BTCUSDT --interval 1h --days 90 --lookahead 6
```

## Tham số

### Tham số chung

- `--symbol`: Cặp giao dịch (mặc định: BTCUSDT)
- `--interval`: Khung thời gian (mặc định: 1h)
- `--live`: Chạy trong môi trường thực tế (không sử dụng = chế độ mô phỏng)
- `--leverage`: Đòn bẩy (1-50, mặc định: 1)
- `--risk`: Phần trăm rủi ro (0.1-10.0, mặc định: 1.0)
- `--check-interval`: Khoảng thời gian kiểm tra (giây, mặc định: 60)
- `--strategy`: Loại chiến lược (auto, ml, advanced_ml, regime_ml, combined, rsi, macd, ema, bbands)
- `--config`: File cấu hình tối ưu
- `--no-ml`: Không sử dụng học máy trong dự đoán

## Giao diện Web

Mở trình duyệt và truy cập: `http://localhost:5000`

Giao diện web bao gồm:
- Dashboard thời gian thực
- Biểu đồ giá và chỉ báo
- Bảng vị thế đang mở
- Lịch sử giao dịch
- Phân tích thị trường
- Cài đặt và cấu hình

## API Documentation

Xem `API_DOCS.md` để biết thêm chi tiết về các API endpoints.

## Cảnh báo

Bot giao dịch này được cung cấp cho mục đích học tập và nghiên cứu. Giao dịch tiền điện tử có rủi ro cao. Sử dụng với sự cẩn trọng và chỉ giao dịch với số tiền bạn có thể chấp nhận mất.

## License

MIT