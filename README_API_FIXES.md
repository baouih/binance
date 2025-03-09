# Tài liệu về các sửa đổi và hướng dẫn tích hợp Binance API

## Giới thiệu
Tài liệu này ghi nhận các vấn đề đã gặp khi tích hợp với Binance API và cách khắc phục. Mục đích là để tránh lặp lại các lỗi trong quá trình phát triển.

## Vấn đề với Binance API

### 1. Xử lý position side trong chế độ hedge mode

**Vấn đề:**
- Lỗi position side mismatch (-4061) khi tạo lệnh trong chế độ hedge mode
- Hệ thống gặp lỗi khi không chỉ định position_side phù hợp

**Giải pháp:**
- Kiểm tra chế độ tài khoản trước khi tạo lệnh (hedge mode hay one-way mode)
- Trong hedge mode, luôn chỉ định position_side là 'LONG' hoặc 'SHORT'
- Không sử dụng reduce_only cùng với position_side
- Ví dụ:
```python
if hedge_mode:
    params['positionSide'] = position_side  # 'LONG' hoặc 'SHORT'
else:
    if reduce_only:
        params['reduceOnly'] = 'true'
```

### 2. Xử lý giá trị lệnh tối thiểu (minimum notional value)

**Vấn đề:**
- Binance yêu cầu giá trị lệnh tối thiểu (100 USDT cho Testnet)
- Lỗi xảy ra khi tạo lệnh với giá trị quá nhỏ

**Giải pháp:**
- Tính toán số lượng dựa vào giá trị USD mong muốn và giá hiện tại
- Làm tròn theo precision của mỗi symbol
- Ví dụ:
```python
quantity = usd_value / current_price
quantity = round(quantity, precision)
```

### 3. Lấy giá hiện tại của các cặp tiền

**Vấn đề:**
- Không lấy được giá của một số cặp tiền trên Testnet
- Dữ liệu không đồng nhất giữa các API endpoints

**Giải pháp:**
- Sử dụng futures_ticker_price với cú pháp đúng
- Xử lý các cặp không có trên Testnet
- Thêm xử lý lỗi và fallback:
```python
try:
    ticker_data = api.futures_ticker_price(symbol)
    if isinstance(ticker_data, dict) and 'price' in ticker_data:
        price = float(ticker_data['price'])
    else:
        # Fallback hoặc thông báo lỗi
        logger.error(f"Không lấy được giá của {symbol}")
except Exception as e:
    logger.error(f"Lỗi khi lấy giá {symbol}: {str(e)}")
```

### 4. Giám sát thread để đảm bảo ổn định hệ thống

**Vấn đề:**
- Các threads có thể dừng đột ngột hoặc treo
- Khó theo dõi trạng thái của nhiều threads cùng lúc

**Giải pháp:**
- Sử dụng hệ thống giám sát thread
- Xử lý lỗi và tự động khởi động lại threads khi cần
- Ghi log đầy đủ để dễ dàng debug

## Các hướng dẫn về tích hợp

### 1. Kiểm tra tài khoản Binance trước khi bắt đầu
```python
# Kiểm tra kết nối
account = api.get_futures_account()
if account and 'totalWalletBalance' in account:
    balance = float(account['totalWalletBalance'])
    logger.info(f"Kết nối thành công, số dư ví: {balance} USDT")
```

### 2. Xác minh chế độ hedge mode
```python
# Kiểm tra và đặt hedge mode
hedge_mode = api.check_hedge_mode()
if hedge_mode:
    logger.info("Tài khoản ở chế độ hedge mode")
else:
    logger.info("Tài khoản ở chế độ one-way mode")
```

### 3. Tạo lệnh thị trường với xử lý lỗi
```python
try:
    order = api.create_order_with_position_side(
        symbol="BTCUSDT",
        side="BUY",
        order_type="MARKET",
        usd_value=100,
        position_side="LONG"
    )
    
    if order.get('error'):
        logger.error(f"Lỗi tạo lệnh: {order.get('error')}")
    else:
        logger.info(f"Lệnh thành công: {json.dumps(order, indent=2)}")
except Exception as e:
    logger.error(f"Lỗi không mong đợi: {str(e)}")
```

### 4. Đặt Take Profit và Stop Loss
```python
try:
    tp_sl = api.set_stop_loss_take_profit(
        symbol="BTCUSDT",
        position_side="LONG",
        entry_price=50000,  # Giá hiện tại
        stop_loss_price=48500,  # -3%
        take_profit_price=52500,  # +5%
        usd_value=50  # 50% vị thế
    )
except Exception as e:
    logger.error(f"Lỗi khi đặt TP/SL: {str(e)}")
```

## Lưu ý quan trọng

1. **Testnet vs Mainnet:**
   - Một số cặp tiền có thể không có trên Testnet
   - Dữ liệu trên Testnet có thể không đồng bộ với Mainnet
   - Luôn kiểm tra kỹ trước khi triển khai trên Mainnet

2. **Xử lý lỗi và logging:**
   - Luôn bọc các gọi API trong khối try-except
   - Ghi log đầy đủ để dễ dàng debug
   - Thêm cơ chế thử lại và fallback

3. **Bảo mật:**
   - Không lưu API key và secret trực tiếp trong code
   - Sử dụng biến môi trường hoặc file .env