# Hướng dẫn sử dụng hệ thống tài khoản nhỏ

## Giới thiệu

Hệ thống giao dịch này được tối ưu hóa đặc biệt cho các tài khoản nhỏ (dưới 200 USDT), giúp đáp ứng các giới hạn về giá trị giao dịch tối thiểu của Binance Futures, đồng thời tối đa hóa hiệu suất giao dịch.

## Tính năng chính

1. **Tự động điều chỉnh đòn bẩy** theo loại tài sản:
   - BTC: 20x
   - ETH: 15x
   - Altcoin: 10x

2. **Mục tiêu lợi nhuận tối ưu** cho tài khoản nhỏ:
   - BTC: 1.5%
   - ETH: 2.0%
   - Altcoin: 3.0%

3. **Ưu tiên giao dịch** các cặp tiền có giá trị giao dịch tối thiểu thấp:
   - Ưu tiên cao: ADAUSDT, DOGEUSDT, MATICUSDT, XRPUSDT (5 USDT min)
   - Ưu tiên trung bình: ETHUSDT, DOTUSDT (20 USDT min)
   - Ưu tiên thấp: BTCUSDT, BNBUSDT (100 USDT min)

4. **Tự động thiết lập Stop Loss/Take Profit** cho mọi vị thế.

5. **Giám sát tài khoản liên tục** và điều chỉnh các tham số theo thời gian thực.

## Cách sử dụng

### Khởi động hệ thống

Để khởi động toàn bộ hệ thống tài khoản nhỏ, chạy lệnh:

```bash
chmod +x start_small_account.sh
./start_small_account.sh
```

Quá trình khởi động sẽ:
1. Kiểm tra và điều chỉnh cài đặt đòn bẩy
2. Thiết lập SL/TP cho các vị thế đang mở
3. Khởi động giám sát tài khoản nhỏ
4. Khởi động trailing stop tự động

### Chỉ chạy giám sát

Để chỉ chạy giám sát tài khoản nhỏ:

```bash
python3 small_account_monitor.py --interval 300 --testnet
```

Tham số:
- `--interval`: Khoảng thời gian giữa các lần kiểm tra (giây)
- `--max-runtime`: Thời gian chạy tối đa (không bắt buộc)
- `--testnet`: Sử dụng testnet thay vì mainnet

### Thiết lập SL/TP

Để thiết lập Stop Loss và Take Profit cho các vị thế đang mở:

```bash
python3 auto_setup_sltp.py --testnet
```

## Quy trình giao dịch

1. **Đánh giá vốn**: Hệ thống kiểm tra xem tài khoản có phải là tài khoản nhỏ không (dưới 200 USDT).

2. **Điều chỉnh đòn bẩy**: Tự động đặt đòn bẩy phù hợp cho từng loại tài sản.

3. **Tính toán kích thước vị thế**:
   - Điều chỉnh tỷ lệ rủi ro xuống 0.7 lần tỷ lệ mặc định
   - Đảm bảo đáp ứng giá trị giao dịch tối thiểu của Binance
   - Kiểm soát tối đa 50% tài khoản cho một vị thế

4. **Thiết lập Stop Loss/Take Profit**:
   - SL: Dựa trên ATR hoặc phần trăm cố định
   - TP: Áp dụng mục tiêu theo từng loại tài sản, điều chỉnh theo đòn bẩy

5. **Giám sát liên tục**:
   - Theo dõi hiệu suất từng vị thế
   - Đưa ra khuyến nghị chốt lời khi đạt mục tiêu

## Cấu hình

Hệ thống sử dụng các file cấu hình sau:

1. **configs/risk_config.json**: Cấu hình quản lý rủi ro và tài khoản nhỏ
2. **configs/profit_manager_config.json**: Cấu hình mục tiêu lợi nhuận
3. **account_config.json**: Cấu hình tài khoản và API

### Điều chỉnh cấu hình tài khoản nhỏ

Các tham số tài khoản nhỏ có thể tùy chỉnh trong `configs/risk_config.json`:

```json
"small_account_settings": {
    "enabled": true,
    "account_size_threshold": 200.0,
    "btc_leverage_adjustment": 20,
    "eth_leverage_adjustment": 15,
    "altcoin_leverage_adjustment": 10,
    "risk_per_trade_adjustment": 0.7,
    "min_position_value": 5.0,
    "max_account_percent": 50.0,
    "preferred_symbols": ["ADAUSDT", "DOGEUSDT", "MATICUSDT", "XRPUSDT", "ETHUSDT"]
}
```

## Lưu ý quan trọng

1. **Đòn bẩy cao hơn đồng nghĩa với rủi ro cao hơn**. Hệ thống sử dụng đòn bẩy cao để đáp ứng các giới hạn giao dịch tối thiểu, nhưng đã điều chỉnh giảm các tham số rủi ro khác để bù đắp.

2. **Mục tiêu lợi nhuận đã được điều chỉnh** theo đòn bẩy và loại tài sản để đảm bảo tỷ lệ thắng cao hơn.

3. **Đối với tài khoản dưới 100 USDT**, nên tập trung vào các cặp tiền có giá trị giao dịch tối thiểu 5 USDT như ADA, DOGE, MATIC, XRP.

4. **Kiểm tra logs thường xuyên** để theo dõi hiệu suất hệ thống:
   ```
   tail -f logs/small_account_monitor_*.log
   ```

## Xử lý sự cố

### Nếu hệ thống không khởi động được
Kiểm tra các quyền thực thi của các script:
```bash
chmod +x start_small_account.sh
chmod +x auto_setup_sltp.py
chmod +x auto_start_trailing_stop.sh
```

### Nếu gặp lỗi về API
Kiểm tra kết nối internet và cấu hình API key trong file `.env`

### Nếu vị thế không được đặt SL/TP tự động
Chạy thủ công lệnh:
```bash
python3 auto_setup_sltp.py --testnet
```