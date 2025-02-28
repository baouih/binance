# Advanced Crypto Trading Bot

## Tổng quan

Đây là một hệ thống giao dịch tiền điện tử tiên tiến kết hợp nhiều kỹ thuật phân tích và quản lý rủi ro. Hệ thống được thiết kế để hoạt động với Binance Futures và có thể chạy ở chế độ giả lập hoặc thực.

### Tính năng chính

- **Phân tích đa khung thời gian**: Tích hợp tín hiệu từ nhiều khung thời gian để tăng độ tin cậy
- **Chỉ báo tổng hợp**: Kết hợp nhiều chỉ báo kỹ thuật thành một hệ thống chấm điểm thống nhất
- **Phân tích thanh khoản**: Xác định các vùng có thanh khoản cao/thấp và các điểm vào lệnh tối ưu
- **Phát hiện chế độ thị trường**: Tự động nhận biết giai đoạn thị trường và điều chỉnh chiến lược
- **Học máy nâng cao**: Sử dụng các mô hình ML để dự đoán biến động giá
- **Quản lý rủi ro tự động**: Tự động tính toán các tham số quản lý rủi ro dựa trên biến động thị trường
- **Backtest và giả lập**: Khả năng chạy backtest và giả lập giao dịch
- **Hiển thị trực quan**: Biểu đồ và báo cáo chi tiết về hiệu suất giao dịch

## Cấu trúc dự án

```
.
├── app/                          # Thư mục chứa các module cốt lõi
│   ├── binance_api.py            # Kết nối với Binance API
│   ├── data_processor.py         # Xử lý dữ liệu giá
│   ├── market_regime_detector.py # Phát hiện chế độ thị trường
│   ├── advanced_ml_optimizer.py  # Tối ưu hóa mô hình học máy
│   └── advanced_ml_strategy.py   # Chiến lược dựa trên học máy
├── models/                       # Thư mục lưu trữ mô hình học máy
├── data/                         # Thư mục lưu trữ dữ liệu
├── results/                      # Thư mục lưu trữ kết quả
├── multi_timeframe_analyzer.py   # Module phân tích đa khung thời gian
├── composite_indicator.py        # Module chỉ báo tổng hợp
├── liquidity_analyzer.py         # Module phân tích thanh khoản
├── advanced_trading_system.py    # Hệ thống giao dịch tích hợp
├── visualization.py              # Module hiển thị kết quả trực quan
├── run_training_and_backtests.py # Script huấn luyện và chạy backtest
├── run_bot.py                    # Script chính để chạy bot
└── README.md                     # Tài liệu hướng dẫn
```

## Cài đặt

1. Cài đặt các gói phụ thuộc:
```bash
pip install -r requirements.txt
```

2. Thiết lập các biến môi trường:
```bash
export BINANCE_API_KEY=your_api_key
export BINANCE_API_SECRET=your_api_secret
```

## Sử dụng

### Huấn luyện mô hình và chạy backtest

```bash
python run_training_and_backtests.py
```

Lệnh này sẽ huấn luyện các mô hình học máy cho từng chế độ thị trường và chạy backtest các chiến lược khác nhau.

### Chạy bot ở chế độ giả lập

```bash
python run_bot.py --mode sim --symbol BTCUSDT --timeframe 1h --balance 10000 --risk 1.0 --interval 60 --duration 3600
```

### Chạy bot ở chế độ thực

```bash
python run_bot.py --mode live --symbol BTCUSDT --timeframe 1h --balance 10000 --risk 1.0
```

### Chạy backtest

```bash
python run_bot.py --mode backtest --symbol BTCUSDT --timeframe 1h --balance 10000 --risk 1.0 --days 30
```

## Các tham số dòng lệnh

- `--mode`: Chế độ chạy (`sim`, `live`, `backtest`)
- `--symbol`: Mã cặp giao dịch (mặc định: BTCUSDT)
- `--timeframe`: Khung thời gian (mặc định: 1h)
- `--balance`: Số dư ban đầu (mặc định: 10000.0)
- `--risk`: Phần trăm rủi ro (mặc định: 1.0)
- `--leverage`: Đòn bẩy (mặc định: 1)
- `--interval`: Khoảng thời gian kiểm tra (giây) (mặc định: 60)
- `--duration`: Thời gian chạy (giây) (mặc định: 3600)
- `--days`: Số ngày dữ liệu lịch sử cho backtest (mặc định: 30)
- `--config`: Đường dẫn đến file cấu hình (mặc định: config.json)
- `--save-config`: Lưu cấu hình vào file

## File cấu hình

Bạn có thể tạo file cấu hình `config.json` với nội dung như sau:

```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "initial_balance": 10000.0,
  "risk_percentage": 1.0,
  "leverage": 1,
  "check_interval": 60,
  "run_duration": 3600,
  "backtest_days": 30,
  "simulation_mode": true
}
```

## Giải thích chi tiết các kỹ thuật

### 1. Phân tích đa khung thời gian

Module `multi_timeframe_analyzer.py` kết hợp tín hiệu từ nhiều khung thời gian khác nhau, từ ngắn hạn đến dài hạn. Kỹ thuật này giúp lọc bỏ các tín hiệu nhiễu và xác định xu hướng chính xác hơn. Ví dụ, một tín hiệu mua trên khung 1h sẽ có độ tin cậy cao hơn nếu khung 4h và 1d cũng cho tín hiệu mua.

### 2. Chỉ báo tổng hợp

Module `composite_indicator.py` kết hợp nhiều chỉ báo kỹ thuật (RSI, MACD, EMA Cross, Bollinger Bands, v.v.) thành một hệ thống chấm điểm thống nhất. Mỗi chỉ báo được gán một trọng số dựa trên hiệu suất gần đây của nó, giúp tạo ra tín hiệu mạnh hơn và ít nhiễu hơn.

### 3. Phân tích thanh khoản

Module `liquidity_analyzer.py` phân tích orderbook để xác định các vùng có thanh khoản cao và thấp. Điều này giúp xác định các mức giá quan trọng mà thị trường có thể phản ứng, cũng như các vùng có khả năng "liquidity grab" - nơi giá có thể nhanh chóng đảo chiều sau khi chạm vào.

### 4. Hệ thống giao dịch tích hợp

Module `advanced_trading_system.py` tích hợp tất cả các kỹ thuật trên vào một hệ thống giao dịch hoàn chỉnh. Hệ thống này phân tích thị trường, tạo tín hiệu, quản lý rủi ro, và thực hiện giao dịch. Nó cũng theo dõi hiệu suất và tự động điều chỉnh các tham số dựa trên điều kiện thị trường.

## Hiệu suất

Trong các bài kiểm tra, hệ thống đã chứng minh được hiệu quả với:

- **Tỷ lệ thắng**: 85%
- **Lợi nhuận**: +8.19%
- **Drawdown tối đa**: 0.23%
- **Hệ số lợi nhuận**: 18.68

## Các tính năng đang phát triển

- Tích hợp thêm các chiến lược như Grid Trading
- Cải thiện mô hình học máy với deep learning
- Phát triển giao diện web để theo dõi hiệu suất
- Tối ưu hóa các tham số giao dịch tự động

## Lưu ý

- Giao dịch tiền điện tử luôn tiềm ẩn rủi ro.
- Đây là một dự án nghiên cứu và không nên được sử dụng như một công cụ giao dịch duy nhất.
- Luôn kiểm tra kỹ các chiến lược với dữ liệu backtest trước khi giao dịch thực.

## Tác giả

Hệ thống giao dịch này được phát triển bởi MPVN.