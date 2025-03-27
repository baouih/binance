# Hướng Dẫn Phân Bổ Rủi Ro Thích Ứng Theo Kích Thước Tài Khoản

## Tổng Quan

Tài liệu này mô tả cách hệ thống tự động điều chỉnh mức độ rủi ro và phân bổ vốn dựa trên kích thước tài khoản, từ tài khoản siêu nhỏ ($100) đến tài khoản lớn ($10,000+).

## Nguyên Lý Phân Bổ Rủi Ro

Hệ thống áp dụng nguyên lý "Rủi ro cao hơn cho tài khoản nhỏ hơn" vì:

1. Tài khoản nhỏ cần tỷ lệ tăng trưởng nhanh hơn để đạt đến quy mô hiệu quả
2. Giới hạn kích thước lệnh tối thiểu của sàn giao dịch yêu cầu tỷ lệ đòn bẩy cao hơn
3. Tài khoản nhỏ thường có ít vị thế mở cùng lúc, giảm tính đa dạng hóa

## Cấu Hình Rủi Ro Theo Kích Thước

### Tài Khoản $100
- **Đòn bẩy**: 20x
- **Rủi ro mỗi giao dịch**: 20-30% 
- **Vị thế tối đa**: 1
- **Cặp tiền phù hợp**: Altcoin có biến động cao (SOLUSDT, AVAXUSDT, DOGEUSDT)
- **Ưu tiên**: Thị trường đi ngang, bollinger_bounce, rsi_reversal
- **Chiến lược**: Siêu tích cực với đòn bẩy cao và nhạy với biến động

### Tài Khoản $200-$300
- **Đòn bẩy**: 15x → 10x
- **Rủi ro mỗi giao dịch**: 15% → 10%
- **Vị thế tối đa**: 2 → 3
- **Cặp tiền phù hợp**: Loại trừ BTC, ưu tiên altcoin
- **Ưu tiên**: Cân bằng giữa chiến lược ngắn hạn và trung hạn
- **Chiến lược**: Tập trung thị trường đi ngang và momentum

### Tài Khoản $300-$500
- **Đòn bẩy**: 10x
- **Rủi ro mỗi giao dịch**: 10%
- **Vị thế tối đa**: 3
- **Cặp tiền phù hợp**: Vẫn loại trừ BTC
- **Chiến lược**: Sử dụng cài đặt mặc định, ưu tiên các cặp biến động vừa phải

### Tài Khoản $500-$700
- **Đòn bẩy**: 7x
- **Rủi ro mỗi giao dịch**: 7% 
- **Vị thế tối đa**: 4
- **Cặp tiền phù hợp**: Thêm ETH, BNB vào danh sách phù hợp
- **Chiến lược**: Ưu tiên trend_following, ít rủi ro hơn

### Tài Khoản $700-$1000
- **Đòn bẩy**: 5x
- **Rủi ro mỗi giao dịch**: 5%
- **Vị thế tối đa**: 5
- **Cặp tiền phù hợp**: Ưu tiên BTC, ETH, và các coin lớn
- **Chiến lược**: An toàn hơn, ưu tiên xu hướng dài hạn

### Tài Khoản $1000-$3000
- **Đòn bẩy**: 5x → 3x
- **Rủi ro mỗi giao dịch**: 5% → 3%
- **Vị thế tối đa**: 5 → 8
- **Cặp tiền phù hợp**: Đầy đủ các cặp, ưu tiên cặp thanh khoản cao
- **Chiến lược**: Đa dạng hóa, kết hợp nhiều chiến lược khác nhau

### Tài Khoản $3000-$5000
- **Đòn bẩy**: 3x
- **Rủi ro mỗi giao dịch**: 3% → 2%
- **Vị thế tối đa**: 8 → 10
- **Cặp tiền phù hợp**: Tất cả các cặp
- **Chiến lược**: Phân bổ động theo hiệu suất gần đây

### Tài Khoản $5000-$10000
- **Đòn bẩy**: 2x
- **Rủi ro mỗi giao dịch**: 2% → 1%
- **Vị thế tối đa**: 10 → 15
- **Chiến lược**: Tối ưu hóa Sharpe ratio, ít rủi ro

### Tài Khoản $10000+
- **Đòn bẩy**: 2x → 1x
- **Rủi ro mỗi giao dịch**: 1% → 0.5%
- **Vị thế tối đa**: 15+
- **Chiến lược**: Tối đa hóa sự ổn định, phòng thủ rủi ro

## Điều Chỉnh Thông Số Tự Động

### Điều Chỉnh Stop Loss / Take Profit
- **Tài khoản nhỏ ($100-$300)**:
  - SL chặt hơn: 1.2-1.5% 
  - TP cao hơn: 3.5-6%
  - Tỷ lệ R:R: 2.5-3.0

- **Tài khoản trung bình ($300-$3000)**:
  - SL trung bình: 1.5-2%
  - TP trung bình: 3-4%
  - Tỷ lệ R:R: 2.0

- **Tài khoản lớn ($3000+)**:
  - SL rộng hơn: 2-3%
  - TP thận trọng: 2.5-3%
  - Tỷ lệ R:R: 1.5

### Điều Chỉnh Chiến Lược Theo Kích Thước Tài Khoản
- **Tài khoản siêu nhỏ ($100)**: Bollinger bounce (50%), Range trading (30%), RSI reversal (20%)
- **Tài khoản nhỏ ($300)**: Momentum (30%), Breakout (30%), Bollinger bounce (40%)
- **Tài khoản trung bình ($1000)**: Trend following (50%), Momentum (30%), Mean reversion (20%)
- **Tài khoản lớn ($5000+)**: Trend following (60%), Breakout (20%), Mean reversion (20%)

## Cách Hệ Thống Xác Định Kích Thước Tài Khoản

```python
def select_account_config(balance=None):
    """
    Chọn cấu hình phù hợp dựa trên số dư
    
    Args:
        balance (float): Số dư tài khoản, nếu None sẽ tự động lấy từ API
        
    Returns:
        tuple: (Cấu hình, Kích thước tài khoản được chọn)
    """
    if balance is None:
        balance = self.get_account_balance()
        
    # Ngưỡng kích thước tài khoản
    account_sizes = sorted([int(size) for size in self.configs.keys()])
    
    # Tìm kích thước phù hợp nhất
    selected_size = None
    for size in account_sizes:
        if balance <= size:
            selected_size = size
            break
    
    # Nếu lớn hơn mọi kích thước, chọn kích thước lớn nhất
    if selected_size is None:
        selected_size = account_sizes[-1]
        
    return self.configs[str(selected_size)], selected_size
```

## Phân Bổ Vốn Thích Ứng

Hệ thống phân bổ vốn theo công thức thích ứng dựa trên số dư tài khoản:

### Công Thức Phân Bổ Vốn
```python
def calculate_position_size(self, symbol, side='BUY'):
    """
    Tính toán kích thước vị thế dựa trên quản lý rủi ro
    
    Args:
        symbol (str): Mã cặp tiền
        side (str): Phía giao dịch (BUY hoặc SELL)
        
    Returns:
        Tuple[float, float]: (Số lượng, Giá trị USD)
    """
    # Lấy thông tin thị trường hiện tại
    ticker_info = self.api.get_ticker(symbol)
    current_price = float(ticker_info['lastPrice'])
    
    # Lấy thông tin symbol
    symbol_info = self.api.get_symbol_info(symbol)
    step_size = float([f for f in symbol_info['filters'] 
                      if f['filterType'] == 'LOT_SIZE'][0]['stepSize'])
    
    # Số tiền rủi ro cho giao dịch này (dựa trên % rủi ro)
    risk_amount = self.account_size * (self.risk_percentage / 100)
    
    # Tính toán kích thước vị thế
    quantity = risk_amount / current_price
    
    # Điều chỉnh đòn bẩy
    quantity = quantity * self.leverage
    
    # Làm tròn theo step size
    quantity = self._round_step_size(quantity, step_size)
    
    # Tính giá trị USD
    usd_value = quantity * current_price
    
    return quantity, usd_value
```

## Ưu Điểm của Hệ Thống

1. **Thích ứng tự động**: Không cần điều chỉnh thủ công khi tài khoản tăng/giảm
2. **Tối ưu hóa tăng trưởng**: Tài khoản nhỏ có cơ hội tăng trưởng nhanh hơn
3. **Bảo vệ vốn**: Tài khoản lớn được bảo vệ tốt hơn với mức rủi ro thấp
4. **Quản lý đa cặp tiền**: Phân bổ danh mục đầu tư theo kích thước tài khoản
5. **Điều chỉnh chiến lược**: Lựa chọn chiến lược phù hợp với quy mô vốn

## Kết Luận

Hệ thống phân bổ rủi ro thích ứng tự động điều chỉnh cài đặt giao dịch theo kích thước tài khoản, giúp tối ưu hóa tăng trưởng cho tài khoản nhỏ trong khi bảo vệ vốn tốt hơn cho tài khoản lớn. Điều này đảm bảo hệ thống hoạt động hiệu quả ở mọi quy mô, từ $100 đến $10,000+.