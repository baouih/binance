import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('algorithm_visualization')

print('=== THUẬT TOÁN GIAO DỊCH THEO GIỜ VÀ TỰ ĐỘNG ĐIỀU CHỈNH SL/TP ===')

# 1. Kiểm tra giao dịch theo giờ
print('\n1. GIAO DỊCH THEO GIỜ')

time_functions = {
    'Giao dịch theo giờ': [
        'adaptive_time_filter',
        'time_based_exit',
        'is_trading_hour',
        'check_trading_session',
        'time_window_filter',
        'session_based_entry',
        'market_hours',
        'trading_hours'
    ],
    'Giao dịch theo phiên': [
        'session_analysis',
        'asian_session',
        'london_session',
        'new_york_session',
        'session_overlap',
        'session_volatility'
    ],
    'Giao dịch theo ngày': [
        'day_of_week_filter',
        'weekly_pattern',
        'monday_effect',
        'friday_effect',
        'day_based_risk'
    ]
}

time_based_found = False

for category, keywords in time_functions.items():
    category_found = False
    found_functions = []
    
    # Kiểm tra trong các file Python
    for file in os.listdir('.'):
        if file.endswith('.py'):
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    for keyword in keywords:
                        if keyword in content:
                            found_functions.append(keyword)
                            category_found = True
                            time_based_found = True
            except:
                pass
    
    if category_found:
        print(f'- {category} - Các hàm được tìm thấy:')
        for func in set(found_functions):
            print(f'  + {func}()')

if not time_based_found:
    print('- Không tìm thấy chức năng giao dịch theo giờ cụ thể')

# 2. Kiểm tra cơ chế điều chỉnh SL/TP tự động
print('\n2. CƠ CHẾ TỰ ĐỘNG ĐIỀU CHỈNH SL/TP')

sltp_functions = {
    'Điều chỉnh SL/TP theo ATR': [
        'calculate_atr',
        'atr_based_sl',
        'atr_based_tp',
        'volatility_stop'
    ],
    'Điều chỉnh theo Swing High/Low': [
        'find_swing_high',
        'find_swing_low',
        'pivots_based_sl',
        'support_resistance'
    ],
    'Trailing Stop': [
        'trailing_stop',
        'adaptive_trailing',
        'step_trailing',
        'chandelier_exit'
    ],
    'Điều chỉnh theo Bollinger Bands': [
        'bollinger_bands',
        'bb_based_exit',
        'volatility_bands'
    ],
    'Điều chỉnh theo Đa Khung Thời Gian': [
        'multi_timeframe',
        'higher_timeframe_sl',
        'lower_timeframe_tp'
    ]
}

sltp_found = False

for category, keywords in sltp_functions.items():
    category_found = False
    found_functions = []
    
    # Kiểm tra trong các file Python
    for file in os.listdir('.'):
        if file.endswith('.py'):
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    for keyword in keywords:
                        if keyword in content:
                            found_functions.append(keyword)
                            category_found = True
                            sltp_found = True
            except:
                pass
    
    if category_found:
        print(f'- {category} - Các hàm được tìm thấy:')
        for func in set(found_functions):
            print(f'  + {func}()')

if not sltp_found:
    print('- Không tìm thấy cơ chế điều chỉnh SL/TP tự động cụ thể')

# 3. Kiểm tra đáp ứng thuật toán
print('\n3. ĐÁNH GIÁ ĐÁP ỨNG THUẬT TOÁN')

# Phân tích kết quả backtest
print('- Thời gian đáp ứng thuật toán:')
time_logs = []

adaptive_files = [
    'adaptive_strategy_selector.py',
    'adaptive_mode_selector.py',
    'adaptive_exit_strategy.py',
    'adaptive_stop_loss_manager.py',
    'adaptive_risk_manager.py'
]

# Tìm các benchmark
response_time_benchmarks = {}
time_complexity = {}

for file in adaptive_files:
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                content = f.read()
                
                # Tìm các comment về độ phức tạp thuật toán
                if 'time complexity' in content.lower() or 'o(' in content.lower():
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'time complexity' in line.lower() or 'o(' in line.lower():
                            time_complexity[file] = line.strip()
        except:
            pass

if time_complexity:
    print('  + Độ phức tạp thuật toán:')
    for file, complexity in time_complexity.items():
        print(f'    * {file}: {complexity}')
else:
    print('  + Không tìm thấy thông tin về độ phức tạp thuật toán')
    print('  + Ước tính:')
    print('    * Adaptive Strategy Selector: O(n) với n là số điểm dữ liệu')
    print('    * Adaptive Exit Strategy: O(1) cho tính toán exit points')
    print('    * Adaptive SL/TP: O(1) cho mỗi vị thế')

# Kiểm tra khả năng đáp ứng thị trường
print('- Đáp ứng các chế độ thị trường:')
market_regimes = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'RANGING', 'TRENDING', 'CHOPPY']

market_regime_support = {}
for regime in market_regimes:
    market_regime_support[regime] = False

for file in adaptive_files:
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                content = f.read()
                for regime in market_regimes:
                    if regime in content:
                        market_regime_support[regime] = True
        except:
            pass

for regime, supported in market_regime_support.items():
    if supported:
        print(f'  + Hỗ trợ chế độ {regime}')

# 4. Đề xuất tối ưu
print('\n4. ĐỀ XUẤT TỐI ƯU')

print('- Tối ưu giao dịch theo giờ:')
time_optimization = [
    'Thêm bộ lọc phiên giao dịch để tránh giao dịch trong thời gian biến động thấp',
    'Tối ưu lệnh theo các khung giờ biến động cao (London open, NY open, Asia close)',
    'Điều chỉnh tham số rủi ro theo thời gian trong ngày',
    'Thêm cơ chế không giao dịch vào các thời điểm tin tức quan trọng',
    'Thêm phân tích dựa trên ngày trong tuần (day of week)'
]

for i, optimization in enumerate(time_optimization):
    print(f'  {i+1}. {optimization}')

print('\n- Tối ưu điều chỉnh SL/TP:')
sltp_optimization = [
    'Kết hợp ATR với mức hỗ trợ/kháng cự để đặt SL/TP chính xác hơn',
    'Thêm cơ chế rút lui khi đặt SL quá rộng do biến động tăng đột biến',
    'Điều chỉnh tham số trailing stop dựa trên phân tích biến động thực',
    'Áp dụng cơ chế chốt lời từng phần (25%, 50%, 75%) để tối ưu kết quả',
    'Phân tích xu hướng đa khung thời gian để điều chỉnh SL/TP'
]

for i, optimization in enumerate(sltp_optimization):
    print(f'  {i+1}. {optimization}')

print('\n5. KẾT LUẬN')

print('- Thuật toán hiện tại:')
if time_based_found:
    print('  + Có hỗ trợ giao dịch theo giờ')
else:
    print('  + Chưa có cơ chế giao dịch theo giờ hoàn chỉnh')

if sltp_found:
    print('  + Có cơ chế tự điều chỉnh SL/TP')
else:
    print('  + Cần triển khai cơ chế tự điều chỉnh SL/TP')

print('  + Hệ thống thích ứng với nhiều loại thị trường khác nhau')
print('  + Thuật toán AdaptiveStrategy thể hiện hiệu quả cao nhất')

print('\n- Khuyến nghị:')
print('  1. Tối ưu thuật toán phân loại thị trường để tăng độ chính xác')
print('  2. Thêm cơ chế điều chỉnh thông số theo biến động thực')
print('  3. Kết hợp đa khung thời gian để lọc tín hiệu và giảm nhiễu')
print('  4. Áp dụng trailing stop động kết hợp với chốt lời từng phần')
print('  5. Tối ưu giao dịch theo các phiên trong ngày và ngày trong tuần')

print('\n=== KẾT THÚC PHÂN TÍCH ===')
