# Tài liệu hướng dẫn sử dụng các Module mới

## Giới thiệu

Tài liệu này hướng dẫn sử dụng các module mới được thêm vào hệ thống giao dịch:

1. **Order Flow Indicators**: Phân tích dòng tiền và chiều sâu thị trường
2. **Volume Profile Analyzer**: Phân tích cấu trúc khối lượng theo vùng giá
3. **Adaptive Exit Strategy**: Chiến lược thoát lệnh thích ứng theo chế độ thị trường
4. **Partial Take Profit Manager**: Quản lý chốt lời từng phần

Ngoài ra, tài liệu cũng hướng dẫn sử dụng các công cụ kiểm tra:

1. **Validate All Symbols**: Công cụ kiểm tra tất cả các module với nhiều cặp tiền
2. **Auto Test All Coins**: Công cụ tự động chạy backtest với các tham số khác nhau

## 1. Order Flow Indicators

### Mô tả
Module này cung cấp các công cụ phân tích dòng tiền và chiều sâu thị trường, giúp phát hiện các mô hình mua/bán và áp lực của thị trường.

### Các tính năng chính
- **Phân tích Order Book**: Tính toán áp lực mua/bán từ chiều sâu thị trường
- **Cumulative Delta**: Tính toán sự tích lũy/phân phối theo thời gian
- **Order Imbalance**: Phát hiện mất cân bằng trong sổ lệnh
- **Liquidity Barriers**: Xác định các vùng hỗ trợ/kháng cự dựa trên thanh khoản
- **Volume Force**: Tính toán lực của khối lượng

### Cách sử dụng

```python
from order_flow_indicators import OrderFlowIndicators

# Khởi tạo Order Flow Indicators
order_flow = OrderFlowIndicators()

# Tính toán các chỉ báo từ dữ liệu OHLCV
enhanced_df = order_flow.calculate_order_flow_indicators(market_data)

# Lấy tín hiệu giao dịch
signals = order_flow.get_order_flow_signals(enhanced_df)

# Tạo biểu đồ Order Flow
chart_path = order_flow.visualize_order_flow(enhanced_df, n_periods=50)

# Xử lý dữ liệu sổ lệnh và giao dịch thời gian thực
order_book_metrics = order_flow.process_order_book(order_book_data)
trade_metrics = order_flow.process_trades(trades_data)
```

## 2. Volume Profile Analyzer

### Mô tả
Module này cung cấp công cụ phân tích Volume Profile để xác định các vùng giá quan trọng dựa trên phân phối khối lượng giao dịch.

### Các tính năng chính
- **Volume Profile**: Tính toán phân phối khối lượng theo vùng giá
- **Point of Control (POC)**: Xác định mức giá có khối lượng giao dịch cao nhất
- **Value Area**: Xác định vùng giá tập trung khối lượng lớn
- **Support/Resistance Zones**: Phát hiện vùng hỗ trợ/kháng cự dựa trên Volume Profile
- **VWAP và các vùng giá**: Tính VWAP (Volume Weighted Average Price) và các vùng giá liên quan

### Cách sử dụng

```python
from volume_profile_analyzer import VolumeProfileAnalyzer

# Khởi tạo Volume Profile Analyzer
vp_analyzer = VolumeProfileAnalyzer()

# Tính Volume Profile
profile = vp_analyzer.calculate_volume_profile(market_data, lookback_periods=50)

# Tìm vùng hỗ trợ/kháng cự
sr_zones = vp_analyzer.find_support_resistance_zones(market_data)

# Phân tích mẫu hình Volume
patterns = vp_analyzer.analyze_volume_patterns(market_data)

# Tính VWAP và các vùng giá
vwap_zones = vp_analyzer.identify_vwap_zones(market_data, period='day')

# Tạo biểu đồ Volume Profile
chart_path = vp_analyzer.visualize_volume_profile(market_data, lookback_periods=50)

# Tạo biểu đồ VWAP
vwap_chart = vp_analyzer.visualize_vwap_zones(market_data)
```

## 3. Adaptive Exit Strategy

### Mô tả
Module này cung cấp các chiến lược thoát lệnh khác nhau tối ưu cho từng chế độ thị trường, giúp tối đa hóa lợi nhuận và giảm thiểu rủi ro.

### Các tính năng chính
- **Chiến lược thoát theo chế độ thị trường**: Chọn chiến lược phù hợp cho từng chế độ
- **Trailing Stop thích ứng**: Điều chỉnh khoảng cách trailing stop theo biến động
- **Thoát dựa trên chỉ báo**: Thoát lệnh dựa trên các chỉ báo kỹ thuật
- **Thoát dựa trên thời gian**: Thoát lệnh sau một khoảng thời gian xác định
- **Thoát dựa trên Volume Profile**: Thoát lệnh dựa trên phân tích Volume Profile
- **Thoát dựa trên Order Flow**: Thoát lệnh dựa trên phân tích Order Flow
- **Tối đa hóa lợi nhuận**: Kết hợp nhiều chiến lược để tối đa hóa lợi nhuận

### Cách sử dụng

```python
from adaptive_exit_strategy import AdaptiveExitStrategy

# Khởi tạo Adaptive Exit Strategy
exit_strategy = AdaptiveExitStrategy()

# Thông tin vị thế
position_data = {
    'position_type': 'long',
    'entry_price': 50000,
    'current_price': 51000,
    'unrealized_pnl_pct': 2.0,
    'entry_time': '2023-01-01T10:00:00'
}

# Xác định chiến lược thoát lệnh
strategy = exit_strategy.determine_exit_strategy(market_data, position_data)

# Tính toán các điểm thoát
exit_points = exit_strategy.calculate_exit_points(market_data, position_data, strategy)

# Lấy tín hiệu thoát lệnh
signal = exit_strategy.get_exit_signal(market_data, position_data)

# Tạo biểu đồ các điểm thoát lệnh
chart_path = exit_strategy.visualize_exit_points(market_data, position_data, exit_points)

# Cập nhật cấu hình cho từng chiến lược
exit_strategy.update_strategy_config('trailing_stop', {'stop_percent': 1.5})

# Cập nhật mapping chiến lược cho từng chế độ
exit_strategy.update_regime_strategy_mapping('trending_bullish', 
                                           ['enhanced_trailing_stop', 'partial_take_profit'])
```

## 4. Partial Take Profit Manager

### Mô tả
Module này cung cấp các công cụ để quản lý và thực hiện chốt lời từng phần theo các mức cấu hình khác nhau dựa trên lợi nhuận, thời gian và chế độ thị trường.

### Các tính năng chính
- **Chốt lời từng phần**: Thiết lập các mức chốt lời theo % lợi nhuận
- **Điều chỉnh stop loss**: Tự động điều chỉnh stop loss sau mỗi lần chốt lời
- **Chốt lời theo chế độ thị trường**: Điều chỉnh mức chốt lời theo chế độ thị trường
- **Cấu hình tùy chỉnh**: Cho phép tùy chỉnh từng vị thế

### Cách sử dụng

```python
from partial_take_profit_manager import PartialTakeProfitManager

# Khởi tạo Partial Take Profit Manager
tp_manager = PartialTakeProfitManager()

# Thông tin vị thế
position_data = {
    'symbol': 'BTCUSDT',
    'position_id': 'test_pos_1',
    'position_type': 'long',
    'entry_price': 50000,
    'current_price': 51000,
    'position_size': 0.1
}

# Thiết lập các mức chốt lời
tp_result = tp_manager.set_tp_levels(market_data, position_data)

# Kiểm tra tín hiệu chốt lời
current_price = 51500  # Giả định giá tăng
tp_signal = tp_manager.check_tp_signals(position_data['symbol'], 
                                       position_data['position_id'], 
                                       current_price)

# Thực hiện chốt lời
if tp_signal['tp_signal']:
    execution_data = {
        'level': tp_signal['level'],
        'price': tp_signal['price'],
        'quantity': tp_signal['quantity']
    }
    
    execute_result = tp_manager.execute_partial_tp(position_data['symbol'], 
                                                 position_data['position_id'], 
                                                 execution_data)

# Tạo biểu đồ các mức chốt lời
chart_path = tp_manager.visualize_tp_levels(position_data['symbol'], 
                                          position_data['position_id'], 
                                          market_data)

# Lấy trạng thái chốt lời
status = tp_manager.get_position_tp_status(position_data['symbol'], 
                                         position_data['position_id'])

# Cấu hình tùy chỉnh
custom_levels = [
    {'percent': 1.0, 'quantity': 0.2, 'adjust_stop': True},
    {'percent': 2.0, 'quantity': 0.3, 'adjust_stop': True},
    {'percent': 3.0, 'quantity': 0.5, 'adjust_stop': True}
]

custom_result = tp_manager.custom_tp_levels_for_position(
    'ETHUSDT', 'custom_pos', position_data, custom_levels
)
```

## 5. Validate All Symbols

### Mô tả
Công cụ này tự động kiểm tra tất cả các module mới với nhiều cặp tiền, xác minh tính toàn vẹn của dữ liệu và khả năng hoạt động của các module.

### Các tính năng
- **Kiểm tra dữ liệu**: Xác minh tính toàn vẹn và chất lượng dữ liệu
- **Kiểm tra module**: Kiểm tra tất cả các module mới
- **Báo cáo chi tiết**: Tạo báo cáo và biểu đồ thống kê kết quả kiểm tra

### Cách sử dụng

```bash
# Kiểm tra tất cả các cặp tiền có dữ liệu 3 tháng
python validate_all_symbols.py

# Kiểm tra các cặp tiền cụ thể
python validate_all_symbols.py --symbols BTCUSDT ETHUSDT BNBUSDT

# Lưu kết quả vào thư mục tùy chỉnh
python validate_all_symbols.py --output_dir my_validation_results
```

Từ code Python:
```python
from validate_all_symbols import SymbolValidator

# Khởi tạo validator
validator = SymbolValidator(
    data_dir='data',
    output_dir='validation_results',
    min_data_months=3
)

# Chạy kiểm tra với 4 threads
results = validator.validate_all_symbols(max_workers=4)
```

## 6. Auto Test All Coins

### Mô tả
Công cụ này tự động chạy backtest với nhiều cặp tiền và các tham số khác nhau, giúp tìm ra các tham số tối ưu.

### Các tính năng
- **Tự động kiểm tra module**: Kiểm tra các module trước khi chạy backtest
- **Chạy backtest với nhiều tham số**: Thử nghiệm với các khung thời gian và hệ số rủi ro khác nhau
- **Báo cáo tổng hợp**: Tạo báo cáo tổng hợp và phân tích kết quả

### Cách sử dụng

```bash
# Chạy backtest cho tất cả các cặp tiền có dữ liệu 3 tháng
python auto_test_all_coins.py

# Chạy với các tham số tùy chỉnh
python auto_test_all_coins.py --timeframes 1h 4h --risk_levels 2.0 3.0 4.0

# Chạy cho các cặp tiền cụ thể
python auto_test_all_coins.py --symbols BTCUSDT ETHUSDT
```

Từ code Python:
```python
from auto_test_all_coins import AutoTestAllCoins

# Khởi tạo auto tester
auto_tester = AutoTestAllCoins(
    data_dir='data',
    output_dir='test_results',
    validate_first=True,
    risk_levels=[2.0, 2.5, 3.0, 4.0, 5.0],
    timeframes=['1h', '4h', '1d'],
    min_data_months=3,
    max_parallel=4
)

# Chạy kiểm tra
auto_tester.run(symbols_filter=['BTCUSDT', 'ETHUSDT'])
```

## Tích hợp Các Module Mới

### Trong Bot Giao dịch

```python
from order_flow_indicators import OrderFlowIndicators
from volume_profile_analyzer import VolumeProfileAnalyzer
from adaptive_exit_strategy import AdaptiveExitStrategy
from partial_take_profit_manager import PartialTakeProfitManager

# Khởi tạo các module
order_flow = OrderFlowIndicators()
volume_profile = VolumeProfileAnalyzer()
exit_strategy = AdaptiveExitStrategy()
tp_manager = PartialTakeProfitManager()

# Trong hàm xử lý tín hiệu vào lệnh
def process_entry_signal(market_data, signal):
    # Thêm chỉ báo Order Flow
    enhanced_data = order_flow.calculate_order_flow_indicators(market_data)
    of_signals = order_flow.get_order_flow_signals(enhanced_data)
    
    # Thêm phân tích Volume Profile
    vp = volume_profile.calculate_volume_profile(market_data)
    sr_zones = volume_profile.find_support_resistance_zones(market_data)
    
    # Kết hợp các tín hiệu
    if signal['type'] == 'buy' and of_signals['overall_bias'] == 'buy':
        # Tạo vị thế
        position = enter_position(signal)
        
        # Thiết lập các mức chốt lời
        tp_manager.set_tp_levels(market_data, position)

# Trong hàm xử lý thoát lệnh
def process_exit_check(market_data, position):
    # Xác định chiến lược thoát lệnh
    strategy = exit_strategy.determine_exit_strategy(market_data, position)
    
    # Lấy tín hiệu thoát lệnh
    exit_signal = exit_strategy.get_exit_signal(market_data, position)
    
    # Kiểm tra tín hiệu chốt lời từng phần
    tp_signal = tp_manager.check_tp_signals(position['symbol'], 
                                          position['position_id'], 
                                          position['current_price'])
    
    # Xử lý tín hiệu
    if exit_signal['exit_signal']:
        # Thoát toàn bộ vị thế
        exit_position(position, exit_signal['exit_reason'])
    elif tp_signal['tp_signal']:
        # Thực hiện chốt lời từng phần
        execution_data = {
            'level': tp_signal['level'],
            'price': tp_signal['price'],
            'quantity': tp_signal['quantity']
        }
        
        tp_manager.execute_partial_tp(position['symbol'], 
                                    position['position_id'], 
                                    execution_data)
```

### Trong Backtest

```python
from order_flow_indicators import OrderFlowIndicators
from volume_profile_analyzer import VolumeProfileAnalyzer
from adaptive_exit_strategy import AdaptiveExitStrategy
from partial_take_profit_manager import PartialTakeProfitManager

# Thêm các tham số dòng lệnh
parser.add_argument('--use_order_flow', type=bool, default=False, 
                   help='Sử dụng Order Flow Indicators')
parser.add_argument('--use_volume_profile', type=bool, default=False, 
                   help='Sử dụng Volume Profile')
parser.add_argument('--use_adaptive_exit', type=bool, default=False, 
                   help='Sử dụng Adaptive Exit Strategy')
parser.add_argument('--use_partial_tp', type=bool, default=False, 
                   help='Sử dụng Partial Take Profit')

# Khởi tạo các module nếu được chọn
if args.use_order_flow:
    order_flow = OrderFlowIndicators()

if args.use_volume_profile:
    volume_profile = VolumeProfileAnalyzer()

if args.use_adaptive_exit:
    exit_strategy = AdaptiveExitStrategy()

if args.use_partial_tp:
    tp_manager = PartialTakeProfitManager()

# Trong hàm backtest
for i in range(len(data)):
    current_data = data.iloc[:i+1]
    
    # Thêm chỉ báo Order Flow nếu được chọn
    if args.use_order_flow:
        current_data = order_flow.calculate_order_flow_indicators(current_data)
    
    # Xử lý tín hiệu vào lệnh
    # ...
    
    # Xử lý thoát lệnh với chiến lược thích ứng
    if args.use_adaptive_exit and position:
        exit_signal = exit_strategy.get_exit_signal(current_data, position)
        if exit_signal['exit_signal']:
            # Xử lý thoát lệnh
            # ...
    
    # Xử lý chốt lời từng phần
    if args.use_partial_tp and position:
        # ...
```

## Lời khuyên và Thực hành tốt nhất

1. **Bắt đầu với cấu hình mặc định**: Các module mới đã được cấu hình với các tham số mặc định tốt. Hãy bắt đầu với chúng trước khi tùy chỉnh.

2. **Kết hợp nhiều chỉ báo**: Order Flow và Volume Profile hoạt động tốt nhất khi kết hợp với các chỉ báo kỹ thuật truyền thống.

3. **Kiểm tra trước khi chạy thực tế**: Luôn sử dụng `validate_all_symbols.py` để kiểm tra các module trước khi chạy toàn bộ hệ thống.

4. **Tối ưu hóa tham số**: Sử dụng `auto_test_all_coins.py` để tìm ra các tham số tối ưu cho từng cặp tiền và chiến lược.

5. **Đánh giá hiệu suất**: Theo dõi hiệu suất của các module mới so với chiến lược cũ để đảm bảo chúng mang lại giá trị thực sự.

6. **Kiểm tra sức tải**: Các module phân tích Order Flow và Volume Profile có thể tốn nhiều tài nguyên. Đảm bảo hệ thống có đủ năng lực để xử lý.

7. **Nâng cao dần dần**: Thêm từng module một và đánh giá tác động của chúng, thay vì thêm tất cả cùng một lúc.

## Câu hỏi thường gặp

**Q: Order Flow Indicators có yêu cầu dữ liệu đặc biệt nào không?**  
A: Để có hiệu quả tốt nhất, Order Flow Indicators nên được sử dụng với dữ liệu sổ lệnh và giao dịch thời gian thực, nhưng module cũng hoạt động tốt với dữ liệu OHLCV thông thường.

**Q: Volume Profile phù hợp với khung thời gian nào?**  
A: Volume Profile hoạt động tốt trên tất cả các khung thời gian, nhưng thường hiệu quả nhất với khung thời gian 1h trở lên.

**Q: Các chiến lược thoát lệnh có thay đổi theo chế độ thị trường như thế nào?**  
A: Adaptive Exit Strategy tự động chọn chiến lược thoát lệnh phù hợp cho từng chế độ thị trường. Ví dụ, trong thị trường xu hướng, nó ưu tiên trailing stop, trong khi trong thị trường sideway, nó ưu tiên chốt lời theo vùng giá.

**Q: Làm thế nào để reset cấu hình Partial Take Profit cho một vị thế?**  
A: Sử dụng phương thức `reset_position_tp(symbol, position_id)` để xóa cấu hình chốt lời cho một vị thế cụ thể.

**Q: Có thể tùy chỉnh chiến lược theo từng cặp tiền không?**  
A: Có, bạn có thể tùy chỉnh chiến lược cho từng cặp tiền bằng cách lưu và tải cấu hình riêng cho mỗi cặp.

## Cập nhật và Phát triển

Các module mới sẽ được cập nhật và cải tiến liên tục. Kiểm tra thư mục dự án thường xuyên để có phiên bản mới nhất. Nếu có lỗi hoặc đề xuất cải tiến, vui lòng báo cáo hoặc đóng góp vào dự án.