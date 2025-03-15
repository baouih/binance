# HƯỚNG DẪN TÍCH HỢP HỆ THỐNG QUẢN LÝ RỦI RO TỐI ƯU

## I. TỔNG QUAN

Hệ thống quản lý rủi ro tối ưu được thiết kế để điều chỉnh tự động mức rủi ro dựa trên điều kiện thị trường hiện tại. Sau khi phân tích đầy đủ, hệ thống chỉ sử dụng 4 mức rủi ro phù hợp nhất:

| Mức rủi ro | % Rủi ro | Phù hợp cho thị trường | Tỷ lệ TP:SL |
|------------|----------|-------------------------|-------------|
| High Moderate | 10% | Thị trường giảm | 1.5:1 |
| High Risk | 15% | Thị trường đi ngang/biến động | 2:1 |
| Extreme Risk | 20% | Thị trường tăng bình thường | 2.5:1 |
| Ultra High Risk | 25% | Thị trường tăng mạnh | 3:1 |

Hệ thống mặc định sử dụng mức 20-25%, và tự động điều chỉnh dựa trên điều kiện thị trường.

## II. CÀI ĐẶT VÀ THIẾT LẬP

### 1. Sao chép file module

Đảm bảo file `optimized_risk_manager.py` đã được tải về và đặt trong thư mục gốc của dự án.

### 2. Import module

```python
from optimized_risk_manager import OptimizedRiskManager
```

### 3. Khởi tạo trình quản lý rủi ro

```python
# Khởi tạo với account size và mức rủi ro mặc định
risk_manager = OptimizedRiskManager(
    account_size=10000,        # Kích thước tài khoản
    default_risk_level='extreme_risk'  # Mặc định sử dụng 20%
)

# Khởi động trình quản lý
risk_manager.start()
```

## III. SỬ DỤNG TRONG HỆ THỐNG GIAO DỊCH

### 1. Cập nhật trạng thái thị trường

Mỗi khi phân tích thị trường hoàn tất, cập nhật trạng thái để điều chỉnh mức rủi ro:

```python
# Ví dụ: Thị trường đang tăng mạnh
risk_manager.update_market_state(
    regime='BULL',           # BULL, BEAR, SIDEWAYS, VOLATILE
    volatility='LOW',        # LOW, NORMAL, HIGH
    trend_strength='STRONG'  # STRONG, NEUTRAL, WEAK
)
```

### 2. Tính toán kích thước vị thế khi mở lệnh

```python
# Khi chuẩn bị mở lệnh
symbol = 'BTCUSDT'
entry_price = 50000
stop_loss = 49000  # Có thể bỏ qua nếu muốn sử dụng SL tự động

# Lấy position size và thông tin rủi ro
position_size, risk_level, risk_percentage = risk_manager.get_position_size(
    symbol=symbol,
    entry_price=entry_price,
    stop_loss_price=stop_loss
)

print(f"Mở lệnh với size: {position_size} BTC")
print(f"Mức rủi ro: {risk_level} ({risk_percentage*100}%)")
```

### 3. Tính toán các mức TP/SL tự động

```python
# Tính toán các mức TP/SL dựa trên mức rủi ro hiện tại
tp_sl_levels = risk_manager.get_tp_sl_levels(
    entry_price=50000,
    position_type='LONG',    # 'LONG' hoặc 'SHORT'
    custom_tp_ratio=None     # Có thể tùy chỉnh tỷ lệ TP:SL
)

# Sử dụng các mức
sl_price = tp_sl_levels['sl_price']
tp1 = tp_sl_levels['tp1']
tp2 = tp_sl_levels['tp2']
tp3 = tp_sl_levels['tp3']
tp4 = tp_sl_levels['tp4']  # Mục tiêu phụ cho trailing stop

print(f"SL: {sl_price}")
print(f"TP1: {tp1} (40% của mục tiêu)")
print(f"TP2: {tp2} (70% của mục tiêu)")
print(f"TP3: {tp3} (100% của mục tiêu)")
print(f"Trailing Stop Trigger: {tp4} (150% của mục tiêu)")
```

### 4. Cập nhật hiệu suất sau khi đóng lệnh

```python
# Sau khi lệnh đóng (hoặc một phần lệnh)
risk_manager.update_performance(
    risk_level='extreme_risk',  # Mức rủi ro khi mở lệnh
    profit_change=100,          # Lợi nhuận (số dương) hoặc lỗ (số âm)
    drawdown=2.5                # Drawdown của lệnh (%) 
)
```

### 5. Lưu và tải trạng thái

```python
# Lưu trạng thái khi kết thúc phiên
risk_manager.save_state('risk_manager_state.json')

# Tải lại trạng thái khi khởi động
risk_manager.load_state('risk_manager_state.json')
```

## IV. TÍCH HỢP VỚI POSITION MANAGER

### 1. Sửa đổi position_manager.py

Thêm OptimizedRiskManager vào position_manager:

```python
from optimized_risk_manager import OptimizedRiskManager

class PositionManager:
    def __init__(self):
        # Các khởi tạo hiện tại
        
        # Thêm risk manager
        self.risk_manager = OptimizedRiskManager(
            account_size=self.account_size,
            default_risk_level='extreme_risk'
        )
        self.risk_manager.start()
        
    def open_position(self, symbol, position_type, entry_price, leverage=None, size=None, sl_price=None, tp_price=None):
        # Nếu không chỉ định size, tính toán dựa trên risk manager
        if size is None:
            # Tính position size theo risk manager
            position_size, risk_level, risk_pct = self.risk_manager.get_position_size(
                symbol=symbol, 
                entry_price=entry_price,
                stop_loss_price=sl_price
            )
            size = position_size
            
        # Nếu không chỉ định sl_price hoặc tp_price, tính toán dựa trên risk manager
        if sl_price is None or tp_price is None:
            tp_sl_levels = self.risk_manager.get_tp_sl_levels(
                entry_price=entry_price,
                position_type=position_type
            )
            
            # Sử dụng các giá trị được tính toán
            if sl_price is None:
                sl_price = tp_sl_levels['sl_price']
            if tp_price is None:
                tp_price = tp_sl_levels['tp3']  # Sử dụng TP3 (100% mục tiêu)
                
            # Lưu lại các mức TP để sử dụng cho partial TP
            tp1 = tp_sl_levels['tp1']
            tp2 = tp_sl_levels['tp2']
            tp3 = tp_sl_levels['tp3']
            tp4 = tp_sl_levels['tp4']
            
        # Tiếp tục mở lệnh như bình thường...
        
    def close_position(self, symbol, amount=None, price=None, reason=None):
        # Các xử lý đóng lệnh hiện tại
        
        # Sau khi đóng lệnh thành công, cập nhật hiệu suất
        if position.status == 'CLOSED':
            # Cập nhật hiệu suất cho risk manager
            self.risk_manager.update_performance(
                risk_level=position.risk_level,  # Cần thêm risk_level vào thông tin position
                profit_change=position.pnl,
                drawdown=position.max_drawdown
            )
```

### 2. Cập nhật thông tin thị trường 

Trong module phân tích thị trường:

```python
def analyze_market():
    # Phân tích thị trường
    if bull_trend and strong_signals:
        regime = 'BULL'
        trend_strength = 'STRONG'
    elif bear_trend:
        regime = 'BEAR'
        trend_strength = 'STRONG'
    else:
        regime = 'SIDEWAYS'
        trend_strength = 'NEUTRAL'
    
    # Tính volatility
    if volatility_indicator > high_threshold:
        volatility = 'HIGH'
    elif volatility_indicator < low_threshold:
        volatility = 'LOW'
    else:
        volatility = 'NORMAL'
    
    # Cập nhật risk manager
    position_manager.risk_manager.update_market_state(
        regime=regime,
        volatility=volatility,
        trend_strength=trend_strength
    )
```

## V. LƯU Ý QUAN TRỌNG

1. **Tự động điều chỉnh theo thị trường**: Hệ thống sẽ tự động chuyển đổi giữa các mức rủi ro dựa trên phân tích thị trường.

2. **TP/SL động**: Tỷ lệ TP:SL được điều chỉnh theo mức rủi ro, với tỷ lệ cao hơn khi rủi ro cao hơn.

3. **Theo dõi hiệu suất**: Hệ thống lưu lại hiệu suất của mỗi mức rủi ro để phân tích sau này.

4. **Lưu trạng thái**: Nhớ lưu trạng thái định kỳ để không mất dữ liệu theo dõi hiệu suất.

5. **Phù hợp với backtest**: Các mức rủi ro đã được tối ưu hóa dựa trên kết quả backtest, đặc biệt là mức 20% và 25% mang lại hiệu quả cao nhất.

## VI. KẾT LUẬN

Hệ thống quản lý rủi ro tối ưu giúp tự động điều chỉnh mức rủi ro dựa trên điều kiện thị trường, tối đa hóa lợi nhuận trong thị trường tăng và giảm thiểu rủi ro trong thị trường giảm. Việc tập trung vào 4 mức rủi ro tối ưu (10%, 15%, 20%, 25%) giúp đơn giản hóa quá trình quyết định mà vẫn đảm bảo hiệu quả giao dịch.