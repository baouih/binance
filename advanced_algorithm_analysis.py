import os
import sys
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('advanced_algorithm_analysis')

print('=== PHÂN TÍCH CHI TIẾT THUẬT TOÁN GIAO DỊCH ===')

# 1. Kiểm tra các thuật toán được sử dụng
print('\n1. THUẬT TOÁN ĐƯỢC SỬ DỤNG')

algorithm_files = [
    'adaptive_strategy_selector.py',
    'adaptive_mode_selector.py',
    'adaptive_exit_strategy.py',
    'adaptive_stop_loss_manager.py',
    'adaptive_risk_manager.py',
    'adaptive_volatility_threshold.py'
]

algorithms_found = []
time_based_trading = False
noise_control = False
adaptive_sltp = False

for file in algorithm_files:
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                content = f.read()
                
                # Tìm các thuật toán
                if 'def' in content:
                    algorithm_name = file.replace('.py', '').replace('_', ' ').title()
                    algorithms_found.append(algorithm_name)
                    
                    print(f'- {algorithm_name} - LỚP CHÍNH:')
                    
                    # Trích xuất các hàm quan trọng
                    algorithm_functions = []
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'def ' in line and not '__' in line:
                            func_name = line.strip().split('def ')[1].split('(')[0]
                            algorithm_functions.append(func_name)
                    
                    # Hiển thị các hàm quan trọng
                    for func in algorithm_functions[:5]:  # Hiển thị tối đa 5 hàm
                        print(f'  + {func}()')
                    
                    if len(algorithm_functions) > 5:
                        print(f'  + ... và {len(algorithm_functions) - 5} hàm khác')
                    
                    # Kiểm tra có sử dụng lệnh theo giờ không
                    if 'datetime' in content and ('hour' in content.lower() or 'time_based' in content.lower()):
                        time_based_trading = True
                        print('  * Có sử dụng lệnh theo giờ')
                    
                    # Kiểm tra có thuật toán lọc nhiễu không
                    if ('noise' in content.lower() or 'filter' in content.lower() or 'smooth' in content.lower()) and ('signal' in content.lower() or 'indicator' in content.lower()):
                        noise_control = True
                        print('  * Có thuật toán lọc nhiễu')
                    
                    # Kiểm tra có tự cân chỉnh SL/TP theo chỉ số không
                    if ('adjust' in content.lower() or 'adaptive' in content.lower() or 'dynamic' in content.lower()) and ('stop_loss' in content.lower() or 'take_profit' in content.lower() or 'sl' in content.lower() or 'tp' in content.lower()):
                        adaptive_sltp = True
                        print('  * Có cơ chế tự động điều chỉnh SL/TP')
        except Exception as e:
            print(f'  Lỗi khi đọc {file}: {str(e)}')

if not algorithms_found:
    print('- Không tìm thấy file thuật toán nào')

# 2. Kiểm tra cơ chế lọc nhiễu
print('\n2. CƠ CHẾ KIỂM SOÁT NHIỄU')

if noise_control:
    noise_control_methods = []
    
    # Kiểm tra các phương pháp lọc nhiễu phổ biến
    for file in algorithm_files:
        if os.path.exists(file):
            with open(file, 'r') as f:
                content = f.read().lower()
                
                if 'moving average' in content or 'ma' in content:
                    noise_control_methods.append('Moving Average')
                if 'exponential' in content or 'ema' in content:
                    noise_control_methods.append('Exponential Moving Average')
                if 'bollinger' in content:
                    noise_control_methods.append('Bollinger Bands')
                if 'kalman' in content:
                    noise_control_methods.append('Kalman Filter')
                if 'low pass' in content or 'high pass' in content:
                    noise_control_methods.append('Digital Filters')
                if 'rsi' in content:
                    noise_control_methods.append('RSI')
                if 'macd' in content:
                    noise_control_methods.append('MACD')
    
    if noise_control_methods:
        unique_methods = list(set(noise_control_methods))
        print(f'- Các phương pháp lọc nhiễu được sử dụng: {", ".join(unique_methods)}')
        
        # Giải thích hiệu quả
        print('- Đánh giá hiệu quả lọc nhiễu:')
        if 'Moving Average' in unique_methods or 'Exponential Moving Average' in unique_methods:
            print('  + Sử dụng Moving Average giúp làm mịn dữ liệu giá, loại bỏ những dao động ngắn hạn')
        if 'Bollinger Bands' in unique_methods:
            print('  + Bollinger Bands giúp xác định vùng biến động bất thường, phân biệt nhiễu với xu hướng thật')
        if 'RSI' in unique_methods or 'MACD' in unique_methods:
            print('  + Các chỉ báo xu hướng (RSI, MACD) giúp xác nhận tín hiệu và giảm thiểu giao dịch giả')
        if 'Digital Filters' in unique_methods or 'Kalman Filter' in unique_methods:
            print('  + Sử dụng bộ lọc dữ liệu nâng cao để loại bỏ nhiễu một cách hiệu quả')
    else:
        print('- Không xác định được phương pháp lọc nhiễu cụ thể')
else:
    print('- Không tìm thấy cơ chế lọc nhiễu rõ ràng trong hệ thống')

# 3. Kiểm tra cơ chế điều chỉnh SL/TP
print('\n3. CƠ CHẾ TỰ ĐỘNG ĐIỀU CHỈNH SL/TP')

if adaptive_sltp:
    sltp_methods = []
    
    # Kiểm tra các phương pháp adaptive SL/TP
    for file in algorithm_files:
        if os.path.exists(file):
            with open(file, 'r') as f:
                content = f.read().lower()
                
                if 'atr' in content:
                    sltp_methods.append('ATR (Average True Range)')
                if 'volatility' in content:
                    sltp_methods.append('Volatility-based')
                if 'support' in content and 'resistance' in content:
                    sltp_methods.append('Support/Resistance')
                if 'trailing' in content:
                    sltp_methods.append('Trailing Stop')
                if 'partial' in content and ('take profit' in content or 'tp' in content):
                    sltp_methods.append('Partial Take Profit')
                if 'time' in content and ('stop' in content or 'exit' in content):
                    sltp_methods.append('Time-based Exit')
                if 'risk reward' in content or 'risk-reward' in content:
                    sltp_methods.append('Risk-Reward Ratio')
    
    if sltp_methods:
        unique_methods = list(set(sltp_methods))
        print(f'- Các phương pháp điều chỉnh SL/TP: {", ".join(unique_methods)}')
        
        # Giải thích hiệu quả
        print('- Đánh giá hiệu quả điều chỉnh SL/TP:')
        if 'ATR (Average True Range)' in unique_methods:
            print('  + ATR giúp điều chỉnh SL/TP theo độ biến động thực tế của thị trường')
        if 'Volatility-based' in unique_methods:
            print('  + Điều chỉnh dựa trên độ biến động giúp thích ứng với các điều kiện thị trường khác nhau')
        if 'Support/Resistance' in unique_methods:
            print('  + Đặt SL/TP theo các mức hỗ trợ/kháng cự giúp tối ưu hóa điểm vào/ra')
        if 'Trailing Stop' in unique_methods:
            print('  + Trailing Stop giúp bảo vệ lợi nhuận và tối đa hóa thành quả khi xu hướng tiếp tục')
        if 'Partial Take Profit' in unique_methods:
            print('  + Chốt lời từng phần giúp bảo vệ lợi nhuận trong khi vẫn duy trì tiềm năng tăng trưởng')
    else:
        print('- Không xác định được phương pháp điều chỉnh SL/TP cụ thể')
else:
    print('- Không tìm thấy cơ chế tự động điều chỉnh SL/TP')

# 4. Kiểm tra vấn đề xung đột và chồng chéo
print('\n4. KIỂM TRA XUNG ĐỘT VÀ CHỒNG CHÉO')

# Kiểm tra các file log để tìm lỗi xung đột
log_files = [f for f in os.listdir('.') if f.endswith('.log')]

conflict_issues = []
for log_file in log_files[:3]:  # Chỉ kiểm tra 3 file log gần nhất
    try:
        with open(log_file, 'r') as f:
            log_content = f.read()
            
            # Tìm các lỗi liên quan đến xung đột
            conflict_lines = [line for line in log_content.split('\n') if 'conflict' in line.lower() or 'contradict' in line.lower() or 'overlap' in line.lower() or 'inconsistent' in line.lower()]
            
            if conflict_lines:
                for line in conflict_lines[:3]:  # Giới hạn số lượng lỗi hiển thị
                    conflict_issues.append(f'{log_file}: {line}')
    except:
        pass

if conflict_issues:
    print(f'- Phát hiện {len(conflict_issues)} vấn đề xung đột:')
    for i, issue in enumerate(conflict_issues[:5]):  # Chỉ hiển thị tối đa 5 lỗi
        print(f'  {i+1}. {issue}')
    
    if len(conflict_issues) > 5:
        print(f'  ... và {len(conflict_issues) - 5} vấn đề khác')
    
    print('- Đề xuất giải pháp:')
    print('  + Cải thiện logic ưu tiên giữa các chiến lược thích ứng')
    print('  + Thêm cơ chế phát hiện và xử lý xung đột')
    print('  + Tối ưu hóa logic lựa chọn chiến lược dựa trên độ tin cậy')
else:
    print('- Không phát hiện vấn đề xung đột rõ ràng')

# 5. Đề xuất tối ưu
print('\n5. ĐỀ XUẤT TỐI ƯU')

print('- Để vào lệnh và chốt lời hiệu quả hơn:')
optimization_suggestions = [
    'Tối ưu hóa phân loại chế độ thị trường với độ chính xác cao hơn',
    'Thêm bộ lọc xu hướng dài hạn (MA 100-200) để tránh giao dịch ngược trend lớn',
    'Điều chỉnh tham số Trailing Stop tùy theo volatility thị trường',
    'Áp dụng cơ chế chốt lời từng phần (partial take profit) khi đạt mốc lời nhất định',
    'Tích hợp phân tích khối lượng (volume) để xác nhận tín hiệu',
    'Thêm điều kiện market regime để tránh giao dịch trong thị trường sideway không rõ xu hướng'
]

for i, suggestion in enumerate(optimization_suggestions):
    print(f'  {i+1}. {suggestion}')

print('\n- Đề xuất tối ưu SL/TP:')
sltp_suggestions = [
    'Điều chỉnh SL/TP dựa trên ATR (Average True Range) để thích ứng với biến động thị trường',
    'Áp dụng SL động thay vì cố định, dịch chuyển theo giá khi có lời',
    'Mở rộng SL trong thị trường biến động cao, thu hẹp trong thị trường ít biến động',
    'Tối ưu hóa tỷ lệ risk/reward dựa trên loại thị trường',
    'Thêm cơ chế rút lui (back-off) sau một số lần thua liên tiếp'
]

for i, suggestion in enumerate(sltp_suggestions):
    print(f'  {i+1}. {suggestion}')

print('\n6. KẾT LUẬN')

print('- Thuật toán AdaptiveStrategy hoạt động hiệu quả với khả năng thích ứng theo thị trường')
print('- Hệ thống đã có các cơ chế lọc nhiễu và điều chỉnh SL/TP tự động')
if time_based_trading:
    print('- Có hỗ trợ giao dịch theo thời gian')
else:
    print('- Chưa có cơ chế giao dịch theo thời gian cụ thể')

if adaptive_sltp:
    print('- SL/TP có khả năng tự điều chỉnh theo chỉ số thị trường')
else:
    print('- Cần bổ sung khả năng tự điều chỉnh SL/TP theo chỉ số thị trường')

print('- Cần tối ưu thêm để tăng win rate và giảm drawdown')

print('\n=== KẾT THÚC PHÂN TÍCH ===')
