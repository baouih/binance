# Hướng dẫn sử dụng Trailing Stop Nâng cao

Tài liệu này hướng dẫn sử dụng các tính năng Trailing Stop nâng cao mới được thêm vào hệ thống. Các cải tiến giúp bảo vệ lợi nhuận tốt hơn và tự động điều chỉnh theo điều kiện thị trường.

## 1. Các chiến lược Trailing Stop

### 1.1. Percentage Trailing Stop (Mặc định)

Chiến lược này sử dụng phần trăm từ giá cao nhất/thấp nhất để đặt mức trailing stop. Khi lợi nhuận vượt ngưỡng kích hoạt, trailing stop sẽ được đặt và di chuyển theo giá.

**Tham số:**
- `activation_percent`: Phần trăm lợi nhuận để kích hoạt trailing stop (mặc định: 1.0%)
- `callback_percent`: Phần trăm callback từ mức cao/thấp nhất (mặc định: 0.5%)

### 1.2. Absolute Trailing Stop

Chiến lược này sử dụng giá trị tuyệt đối (USD) thay vì phần trăm. Hữu ích cho các tài khoản lớn có ngưỡng lợi nhuận cố định.

**Tham số:**
- `activation_amount`: Giá trị lợi nhuận (USD) để kích hoạt trailing stop (mặc định: 100.0 USD)
- `callback_amount`: Giá trị callback (USD) từ mức cao/thấp nhất (mặc định: 50.0 USD)

### 1.3. ATR Trailing Stop

Chiến lược này sử dụng chỉ báo ATR (Average True Range) để điều chỉnh trailing stop theo biến động thị trường. Khoảng cách trailing stop sẽ rộng hơn khi thị trường biến động mạnh.

**Tham số:**
- `atr_multiplier`: Hệ số nhân ATR (mặc định: 3.0)
- `atr_period`: Số chu kỳ để tính ATR (mặc định: 14)

### 1.4. Parabolic SAR Trailing Stop

Chiến lược này sử dụng chỉ báo Parabolic SAR để xác định điểm đảo chiều. Khi giá chạm SAR, vị thế sẽ được đóng.

**Tham số:**
- `acceleration_factor`: Hệ số tăng tốc ban đầu (mặc định: 0.02)
- `acceleration_max`: Hệ số tăng tốc tối đa (mặc định: 0.2)

### 1.5. Step Trailing Stop

Chiến lược bậc thang với nhiều mức stop khác nhau dựa trên lợi nhuận đạt được. Khi lợi nhuận tăng, mức bảo vệ cũng tăng theo.

**Tham số:**
- `profit_steps`: Danh sách các mức lợi nhuận (%) (mặc định: [1.0, 2.0, 3.0, 5.0, 8.0])
- `callback_steps`: Danh sách các mức callback (%) (mặc định: [0.5, 0.8, 1.0, 1.5, 2.0])

## 2. Cấu hình Trailing Stop

Bạn có thể cấu hình trailing stop trong file `risk_config.json`:

```json
{
  "trailing_stop": {
    "type": "percentage",
    "config": {
      "activation_percent": 1.0,
      "callback_percent": 0.5
    }
  }
}
```

**Loại chiến lược (`type`)**:
- `percentage`: Trailing stop theo phần trăm (mặc định)
- `absolute`: Trailing stop theo giá trị tuyệt đối
- `atr`: Trailing stop dựa trên ATR
- `psar`: Trailing stop dựa trên Parabolic SAR
- `step`: Trailing stop bậc thang

## 3. Cách sử dụng trong code

```python
from advanced_trailing_stop import AdvancedTrailingStop
from data_cache import DataCache

# Tạo cache dữ liệu
data_cache = DataCache()

# Tạo AdvancedTrailingStop với loại chiến lược
ts = AdvancedTrailingStop(
    strategy_type="percentage",  # loại chiến lược
    data_cache=data_cache,
    config={
        "activation_percent": 1.0,
        "callback_percent": 0.5
    }
)

# Khởi tạo vị thế với trailing stop
position = {
    'symbol': 'BTCUSDT',
    'side': 'LONG',
    'entry_price': 60000,
    'quantity': 0.1,
    'leverage': 10
}
position = ts.initialize_position(position)

# Cập nhật trailing stop với giá hiện tại
current_price = 61000
position = ts.update_trailing_stop(position, current_price)

# Kiểm tra xem có nên đóng vị thế không
should_close, reason = ts.check_stop_condition(position, current_price)
if should_close:
    print(f"Nên đóng vị thế: {reason}")
else:
    print("Chưa nên đóng vị thế")

# Thay đổi chiến lược trailing stop
ts.change_strategy("atr", {
    "atr_multiplier": 2.0,
    "atr_period": 14
})
```

## 4. Sử dụng trong giao dịch tự động

Hệ thống giao dịch tự động sẽ tự động sử dụng `AdvancedTrailingStop` thông qua `EnhancedIntegratedSystem`:

```python
from enhanced_integrated_system import EnhancedIntegratedSystem

# Khởi tạo hệ thống tích hợp nâng cao
system = EnhancedIntegratedSystem()

# Kiểm tra vị thế
system.check_positions()

# Chạy dịch vụ giám sát với chu kỳ 30 giây
system.run_monitoring_service(interval=30)
```

## 5. Thông báo Trailing Stop

Hệ thống sẽ tự động gửi thông báo khi:
- Trailing stop được kích hoạt
- Trailing stop được cập nhật theo giá mới
- Vị thế được đóng do chạm trailing stop

## 6. Lợi ích chính

1. **Bảo vệ lợi nhuận tốt hơn**: Theo dõi và khóa lợi nhuận một cách tự động.
2. **Đa dạng chiến lược**: 5 chiến lược khác nhau phù hợp với nhiều điều kiện thị trường.
3. **Thích nghi với biến động thị trường**: Các chiến lược như ATR tự động điều chỉnh theo biến động.
4. **Chống mất lợi nhuận**: Khi thị trường đảo chiều, trailing stop giúp bảo vệ lợi nhuận đã đạt được.
5. **Tích hợp với hệ thống thông báo**: Nhận thông báo theo thời gian thực về trailing stop và vị thế.

## 7. Các trường dữ liệu mới trong vị thế

Khi sử dụng `AdvancedTrailingStop`, vị thế sẽ có thêm các trường dữ liệu:

- `trailing_type`: Loại chiến lược trailing stop đang sử dụng
- `trailing_activated`: True nếu trailing stop đã được kích hoạt
- `trailing_stop`: Giá trailing stop hiện tại
- `highest_price`: Giá cao nhất đã đạt được (cho LONG)
- `lowest_price`: Giá thấp nhất đã đạt được (cho SHORT)

Tùy theo chiến lược, còn có thêm các trường khác như:
- `trailing_activation_percent`, `trailing_callback_percent` (Percentage)
- `trailing_activation_amount`, `trailing_callback_amount` (Absolute)
- `trailing_atr_multiplier`, `trailing_atr_period`, `atr_value` (ATR)
- `trailing_af`, `trailing_af_max`, `psar_value` (Parabolic SAR)
- `trailing_profit_steps`, `trailing_callback_steps`, `trailing_current_step` (Step)

## 8. Lưu ý quan trọng

1. **Luôn khởi tạo vị thế trước**: Hãy gọi `initialize_position()` trước khi sử dụng các chức năng khác.
2. **Đồng bộ với Binance**: Nếu bạn thay đổi giá trailing stop theo cách thủ công, hãy đảm bảo đồng bộ với Binance.
3. **Giá trị ATR**: Nếu bạn sử dụng chiến lược ATR, hãy đảm bảo dữ liệu ATR đã được tính và lưu trong cache.
4. **Hiệu suất**: Việc cập nhật trailing stop cho nhiều vị thế có thể tốn tài nguyên - cân nhắc tần suất cập nhật.
5. **Tích hợp với hệ thống khác**: Khi tích hợp, hãy kiểm tra kỹ tính tương thích với các module khác.

## 9. Ví dụ thực tế

**Ví dụ 1: Vị thế LONG với Trailing Stop theo phần trăm**

Giả sử bạn mở vị thế LONG BTCUSDT ở giá $60,000 với đòn bẩy 10x:
- Khi giá tăng lên $60,600 (lợi nhuận 1%), trailing stop được kích hoạt ở $60,300 (0.5% dưới mức cao nhất)
- Khi giá tiếp tục tăng lên $61,000, trailing stop cũng được nâng lên $60,695
- Nếu giá giảm xuống $60,695, vị thế sẽ được đóng với lợi nhuận 1.16%

**Ví dụ 2: Vị thế SHORT với Trailing Stop dựa trên ATR**

Giả sử bạn mở vị thế SHORT ETHUSDT ở giá $3,000 với đòn bẩy 5x và ATR hiện tại là $150:
- Khi giá giảm xuống $2,850 (lợi nhuận 5%), trailing stop được kích hoạt ở $3,150 (ATR * 2 trên mức thấp nhất)
- Khi giá tiếp tục giảm xuống $2,800, trailing stop cũng được hạ xuống $3,100
- Nếu giá tăng lên $3,100, vị thế sẽ được đóng với lợi nhuận 3.33%

## 10. Liên hệ hỗ trợ

Nếu bạn có câu hỏi hoặc gặp vấn đề khi sử dụng Trailing Stop nâng cao, vui lòng liên hệ qua:
- Email: support@example.com
- Telegram: @your_support_bot