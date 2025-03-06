# Hệ thống Quản lý Chốt lời (Profit Manager)

Hệ thống này được thiết kế để tự động quản lý việc chốt lời cho các vị thế giao dịch cryptocurrency, kết hợp với hệ thống Trailing Stop sẵn có. Module này giải quyết vấn đề để vị thế mở quá lâu, gây tốn phí giữ vị thế qua đêm (funding fee) và giảm thiểu rủi ro khi thị trường đảo chiều.

## Các Chiến lược Chốt lời

Hệ thống Profit Manager hỗ trợ 5 chiến lược chốt lời khác nhau:

### 1. Chốt lời theo Thời gian (Time-based)
- Đóng vị thế sau một khoảng thời gian nhất định (ví dụ: 24h, 48h)
- Giúp hạn chế việc trả phí funding fee qua đêm
- Phù hợp cho chiến lược scalping hoặc swing trading ngắn hạn

### 2. Chốt lời theo Mục tiêu (Target Profit)
- Đóng vị thế khi đạt mức lợi nhuận mục tiêu (ví dụ: 2%, 5%)
- Cố định mục tiêu lợi nhuận
- Đảm bảo chốt lời khi thị trường có biến động thuận lợi

### 3. Chốt lời theo Chỉ báo Kỹ thuật (Indicator-based)
- Đóng vị thế dựa trên tín hiệu từ các chỉ báo kỹ thuật (RSI, MACD, etc.)
- Ví dụ: Đóng vị thế LONG khi RSI vượt 70 (quá mua)
- Kết hợp được các tín hiệu kỹ thuật vào quyết định chốt lời

### 4. Chốt lời theo Đảo chiều Giá (Price Reversal)
- Đóng vị thế khi phát hiện dấu hiệu đảo chiều của thị trường
- Ví dụ: Đóng vị thế LONG khi có 3 nến đỏ liên tiếp
- Giúp thoát trước khi thị trường đảo chiều mạnh

### 5. Chốt lời Động theo Biến động (Dynamic Volatility)
- Điều chỉnh mục tiêu chốt lời dựa trên mức biến động của thị trường
- Biến động thấp: mục tiêu lợi nhuận thấp (ví dụ: 1.5%)
- Biến động cao: mục tiêu lợi nhuận cao (ví dụ: 5%)
- Thích ứng với điều kiện thị trường hiện tại

## Tích hợp với Trailing Stop

Hệ thống PositionManager kết hợp cả Profit Manager và Trailing Stop:

1. **Trailing Stop**: Bảo vệ lợi nhuận theo xu hướng, dịch chuyển mức stop loss khi giá di chuyển có lợi
2. **Profit Manager**: Chủ động chốt lời khi đáp ứng một trong các điều kiện

Khi cả hai đều được kích hoạt, vị thế sẽ được đóng bởi cơ chế nào kích hoạt trước.

## Tùy chỉnh Cấu hình

Cấu hình mẫu cho Profit Manager có tại `configs/profit_manager_config.json`:

```json
{
    "time_based": {
        "enabled": true,
        "max_hold_time": 48
    },
    "target_profit": {
        "enabled": true,
        "profit_target": 5.0
    },
    "indicator_based": {
        "enabled": true,
        "rsi_overbought": 70.0,
        "rsi_oversold": 30.0
    },
    "price_reversal": {
        "enabled": true,
        "candle_count": 3
    },
    "dynamic_volatility": {
        "enabled": true,
        "low_vol_target": 1.5,
        "medium_vol_target": 3.0,
        "high_vol_target": 5.0
    }
}
```

Mỗi chiến lược có thể được bật/tắt độc lập và các tham số có thể được tùy chỉnh.

## Cách Sử dụng

### Sử dụng PositionManager

```python
from position_manager import PositionManager
from data_cache import DataCache

# Tạo cache dữ liệu
data_cache = DataCache()

# Tạo cấu hình
trailing_config = {
    'strategy_type': 'percentage',
    'config': {
        'activation_percent': 1.0,
        'callback_percent': 0.5
    }
}

profit_config = {
    'time_based': {
        'enabled': True,
        'max_hold_time': 48
    },
    'target_profit': {
        'enabled': True,
        'profit_target': 5.0
    }
}

# Tạo position manager
position_manager = PositionManager(trailing_config, profit_config, data_cache)

# Tạo vị thế
position = {
    'id': 'test_position',
    'symbol': 'BTCUSDT',
    'side': 'LONG',
    'entry_price': 50000,
    'quantity': 0.1,
    'entry_time': datetime.now()
}

# Khởi tạo vị thế
position = position_manager.initialize_position(position)

# Cập nhật vị thế với giá hiện tại
current_price = 51000
position = position_manager.update_position(position, current_price)

# Kiểm tra điều kiện đóng
should_close, reason = position_manager.check_exit_conditions(position, current_price)

if should_close:
    print(f"Đóng vị thế: {reason}")
    # Thực hiện đóng vị thế
```

## Kiểm thử

Chạy bộ kiểm thử đầy đủ để xác nhận chức năng hoạt động:

```
python test_position_manager.py
```

Kết quả kiểm thử sẽ được lưu trong `test_results/position_manager_test_results.json`.

## Lợi ích chính

1. **Bảo vệ Lợi nhuận:** Chốt lời kịp thời, không để mất lợi nhuận khi thị trường đảo chiều
2. **Giảm Chi phí:** Hạn chế thời gian giữ vị thế, tiết kiệm phí funding
3. **Tự động hóa:** Không cần theo dõi thủ công, hệ thống tự động xử lý
4. **Linh hoạt:** Nhiều chiến lược đa dạng có thể kết hợp tùy theo nhu cầu
5. **Dễ mở rộng:** Dễ dàng thêm các chiến lược chốt lời mới