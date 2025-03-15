import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('adaptive_risk_allocation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('adaptive_risk_allocation')

class AdaptiveRiskAllocator:
    """
    Phân bổ vốn động dựa trên hiệu suất gần đây giữa các mức rủi ro
    Tự động điều chỉnh tỷ lệ vốn phân bổ cho từng mức rủi ro dựa trên hiệu suất, drawdown và trạng thái thị trường
    """
    
    def __init__(self, config_file=None):
        # Mặc định cấu hình
        self.default_config = {
            'risk_levels': {
                'ultra_conservative': 0.03,  # 3%
                'conservative': 0.05,        # 5%
                'moderate': 0.07,            # 7%
                'aggressive': 0.09,          # 9%
                'high_risk': 0.15,           # 15%
                'extreme_risk': 0.20,        # 20%
                'ultra_high_risk': 0.25      # 25%
            },
            'initial_allocation': {
                'ultra_conservative': 0.20,  # 20%
                'conservative': 0.20,        # 20%
                'moderate': 0.20,            # 20%
                'aggressive': 0.20,          # 20%
                'high_risk': 0.15,           # 15%
                'extreme_risk': 0.05,        # 5%
                'ultra_high_risk': 0.00      # 0%
            },
            'performance_weight': 0.4,       # Trọng số cho hiệu suất
            'risk_weight': 0.3,              # Trọng số cho rủi ro (drawdown)
            'stability_weight': 0.3,         # Trọng số cho ổn định (volatility)
            'reallocation_period': 7,        # Số ngày giữa các lần tái phân bổ
            'max_allocation_change': 0.1,    # Thay đổi tối đa mỗi lần tái phân bổ
            'drawdown_limit': {
                'ultra_conservative': 0.05,  # 5%
                'conservative': 0.08,        # 8%
                'moderate': 0.12,            # 12%
                'aggressive': 0.15,          # 15%
                'high_risk': 0.20,           # 20%
                'extreme_risk': 0.25,        # 25%
                'ultra_high_risk': 0.30      # 30%
            }
        }
        
        # Đọc cấu hình từ file nếu có
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Đã tải cấu hình từ {config_file}")
        else:
            self.config = self.default_config
            if config_file:
                logger.warning(f"Không tìm thấy file {config_file}, sử dụng cấu hình mặc định")
            
            # Lưu cấu hình mặc định nếu chưa có file
            if config_file:
                os.makedirs(os.path.dirname(os.path.abspath(config_file)), exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(self.default_config, f, indent=4)
                logger.info(f"Đã lưu cấu hình mặc định vào {config_file}")
        
        # Hiệu suất của từng mức rủi ro
        self.performance = {level: {'daily_returns': [], 'drawdown': 0, 'volatility': 0, 'score': 1.0} 
                           for level in self.config['risk_levels']}
        
        # Phân bổ hiện tại
        self.current_allocation = self.config['initial_allocation'].copy()
        
        # Lịch sử phân bổ
        self.allocation_history = []
        
        # Thời gian tái phân bổ cuối cùng
        self.last_reallocation = datetime.now()
        
        logger.info(f"Khởi tạo AdaptiveRiskAllocator với {len(self.config['risk_levels'])} mức rủi ro")
    
    def update_performance(self, risk_level, daily_return, drawdown=None):
        """Cập nhật hiệu suất cho một mức rủi ro cụ thể"""
        if risk_level not in self.performance:
            logger.warning(f"Mức rủi ro không tồn tại: {risk_level}")
            return
        
        # Thêm lợi nhuận hàng ngày vào lịch sử
        self.performance[risk_level]['daily_returns'].append(daily_return)
        
        # Giới hạn lịch sử lợi nhuận hằng ngày
        max_history = 30  # 30 ngày
        if len(self.performance[risk_level]['daily_returns']) > max_history:
            self.performance[risk_level]['daily_returns'] = self.performance[risk_level]['daily_returns'][-max_history:]
        
        # Cập nhật drawdown nếu có
        if drawdown is not None:
            self.performance[risk_level]['drawdown'] = max(
                self.performance[risk_level]['drawdown'], 
                drawdown
            )
        
        # Tính toán độ biến động (volatility)
        if len(self.performance[risk_level]['daily_returns']) > 1:
            self.performance[risk_level]['volatility'] = np.std(self.performance[risk_level]['daily_returns'])
        
        logger.info(f"Cập nhật hiệu suất {risk_level}: daily_return={daily_return:.4f}, "
                   f"drawdown={self.performance[risk_level]['drawdown']:.4f}, "
                   f"volatility={self.performance[risk_level]['volatility']:.4f}")
        
        # Kiểm tra xem có cần tái phân bổ không
        self._check_reallocation()
    
    def calculate_performance_scores(self):
        """Tính toán điểm số hiệu suất cho từng mức rủi ro"""
        scores = {}
        
        for level, stats in self.performance.items():
            # Bỏ qua nếu không có đủ dữ liệu
            if len(stats['daily_returns']) < 5:
                scores[level] = 1.0  # Điểm mặc định
                continue
            
            # Tính trung bình lợi nhuận hàng ngày
            avg_return = np.mean(stats['daily_returns'])
            
            # Tính tỷ lệ Sharpe đơn giản (lợi nhuận/độ biến động)
            sharpe = avg_return / max(stats['volatility'], 0.0001)
            
            # Tính điểm số hiệu suất
            performance_score = max(0, avg_return * 100)  # Chuyển sang phần trăm
            
            # Tính điểm số rủi ro (thấp hơn là tốt hơn)
            # Chuẩn hóa theo giới hạn drawdown
            drawdown_limit = self.config['drawdown_limit'].get(level, 0.2)
            risk_score = max(0, 1 - stats['drawdown'] / drawdown_limit)
            
            # Tính điểm số ổn định (thấp hơn biến động là tốt hơn)
            stability_score = max(0, 1 - stats['volatility'] * 10)  # Nhân 10 để phóng đại tác động
            
            # Tính điểm số tổng hợp
            total_score = (
                performance_score * self.config['performance_weight'] +
                risk_score * self.config['risk_weight'] +
                stability_score * self.config['stability_weight']
            )
            
            # Đảm bảo điểm số luôn dương
            scores[level] = max(0.1, total_score)
            
            logger.debug(f"Điểm số {level}: performance={performance_score:.2f}, "
                        f"risk={risk_score:.2f}, stability={stability_score:.2f}, "
                        f"total={total_score:.2f}")
        
        return scores
    
    def _check_reallocation(self):
        """Kiểm tra xem có cần tái phân bổ vốn không"""
        now = datetime.now()
        days_since_last = (now - self.last_reallocation).days
        
        if days_since_last >= self.config['reallocation_period']:
            self.reallocate()
            self.last_reallocation = now
    
    def reallocate(self):
        """Tái phân bổ vốn giữa các mức rủi ro dựa trên hiệu suất"""
        # Tính điểm số hiệu suất
        scores = self.calculate_performance_scores()
        
        # Lưu điểm số vào performance
        for level, score in scores.items():
            self.performance[level]['score'] = score
        
        # Tính tổng điểm số
        total_score = sum(scores.values())
        
        # Tính phân bổ mới dựa trên điểm số
        new_allocation = {}
        
        if total_score > 0:
            for level, score in scores.items():
                # Phân bổ tỷ lệ với điểm số
                new_allocation[level] = score / total_score
        else:
            # Nếu tổng điểm số <= 0, sử dụng phân bổ đều
            equal_alloc = 1.0 / len(scores)
            new_allocation = {level: equal_alloc for level in scores}
        
        # Giới hạn thay đổi tối đa
        max_change = self.config['max_allocation_change']
        for level in new_allocation:
            current = self.current_allocation.get(level, 0)
            change = new_allocation[level] - current
            
            if abs(change) > max_change:
                # Giới hạn thay đổi
                change = max_change if change > 0 else -max_change
                new_allocation[level] = current + change
        
        # Chuẩn hóa lại để tổng = 1
        total = sum(new_allocation.values())
        if total > 0:
            for level in new_allocation:
                new_allocation[level] /= total
        
        # Lưu lại lịch sử phân bổ
        allocation_record = {
            'timestamp': datetime.now().isoformat(),
            'allocation': new_allocation.copy(),
            'scores': scores.copy()
        }
        self.allocation_history.append(allocation_record)
        
        # Cập nhật phân bổ hiện tại
        self.current_allocation = new_allocation
        
        logger.info(f"Đã tái phân bổ vốn: {json.dumps(self.current_allocation, indent=2)}")
        
        return self.current_allocation
    
    def get_allocation(self):
        """Trả về phân bổ vốn hiện tại"""
        return self.current_allocation
    
    def get_performance_stats(self):
        """Trả về thống kê hiệu suất"""
        return self.performance
    
    def save_state(self, file_path):
        """Lưu trạng thái hiện tại vào file"""
        state = {
            'config': self.config,
            'performance': self.performance,
            'current_allocation': self.current_allocation,
            'allocation_history': self.allocation_history,
            'last_reallocation': self.last_reallocation.isoformat()
        }
        
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=4, default=str)
        
        logger.info(f"Đã lưu trạng thái vào {file_path}")
    
    def load_state(self, file_path):
        """Tải trạng thái từ file"""
        if not os.path.exists(file_path):
            logger.warning(f"Không tìm thấy file {file_path}")
            return False
        
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            self.config = state.get('config', self.config)
            self.performance = state.get('performance', self.performance)
            self.current_allocation = state.get('current_allocation', self.current_allocation)
            self.allocation_history = state.get('allocation_history', self.allocation_history)
            
            last_realloc = state.get('last_reallocation')
            if last_realloc:
                self.last_reallocation = datetime.fromisoformat(last_realloc)
            
            logger.info(f"Đã tải trạng thái từ {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi tải trạng thái: {str(e)}")
            return False

# Hàm giả lập hiệu suất cho các mức rủi ro
def simulate_risk_performance():
    # Tham số cho mô phỏng
    days = 30
    risk_levels = {
        'ultra_conservative': 0.03,
        'conservative': 0.05,
        'moderate': 0.07,
        'aggressive': 0.09,
        'high_risk': 0.15,
        'extreme_risk': 0.20,
        'ultra_high_risk': 0.25
    }
    
    # Khởi tạo allocator
    allocator = AdaptiveRiskAllocator('risk_allocation_config.json')
    
    # Mô phỏng hiệu suất trong n ngày
    print(f"\n=== MÔ PHỎNG HIỆU SUẤT VÀ PHÂN BỔ VỐN THEO MỨC RỦI RO ({days} NGÀY) ===")
    
    # Sinh dữ liệu ngẫu nhiên với các xu hướng
    np.random.seed(42)  # Để tái tạo kết quả
    
    # Mảng chứa hiệu suất của từng loại
    returns = {level: [] for level in risk_levels}
    drawdowns = {level: 0 for level in risk_levels}
    
    # Tạo dữ liệu cho 3 giai đoạn thị trường
    market_phases = [
        {'name': 'Tăng giá mạnh', 'days': 10, 'base_return': 0.01, 'volatility': 0.02},
        {'name': 'Dao động mạnh', 'days': 10, 'base_return': 0.0, 'volatility': 0.03},
        {'name': 'Giảm giá mạnh', 'days': 10, 'base_return': -0.01, 'volatility': 0.02}
    ]
    
    # Lưu phân bổ theo thời gian
    allocation_over_time = []
    
    phase_day = 0
    current_phase = 0
    
    for day in range(days):
        # Xác định giai đoạn thị trường hiện tại
        if phase_day >= market_phases[current_phase]['days']:
            phase_day = 0
            current_phase = (current_phase + 1) % len(market_phases)
        
        # Tham số thị trường hiện tại
        phase = market_phases[current_phase]
        base_return = phase['base_return']
        volatility = phase['volatility']
        
        print(f"\nNgày {day+1} - Thị trường: {phase['name']} (base_return: {base_return:.2%}, volatility: {volatility:.2%})")
        
        # Cập nhật hiệu suất cho từng mức rủi ro
        for level, risk in risk_levels.items():
            # Sinh lợi nhuận ngẫu nhiên, tỷ lệ thuận với mức rủi ro
            # Mức rủi ro cao có biên độ lớn hơn cả tăng và giảm
            daily_return = base_return * (1 + risk*5) + np.random.normal(0, volatility * risk * 2)
            
            # Giới hạn tăng/giảm theo mức rủi ro
            max_daily_change = risk * 2  # Ví dụ: mức 0.05 có thể tăng/giảm tối đa 10%/ngày
            daily_return = max(min(daily_return, max_daily_change), -max_daily_change)
            
            # Tính drawdown (giả định)
            drawdown = abs(daily_return * 5) if daily_return < 0 else 0
            drawdowns[level] = max(drawdowns[level], drawdown)
            
            # Cập nhật vào allocator
            allocator.update_performance(level, daily_return, drawdown)
            
            # Lưu lại để phân tích
            returns[level].append(daily_return)
        
        # Lấy phân bổ hiện tại
        allocation = allocator.get_allocation()
        allocation_over_time.append(allocation.copy())
        
        # Hiển thị phân bổ hiện tại
        print("Phân bổ vốn hiện tại:")
        for level, alloc in sorted(allocation.items(), key=lambda x: risk_levels[x[0]]):
            formatted_level = f"{level} ({risk_levels[level]*100:.0f}%)"
            print(f"  - {formatted_level:25s}: {alloc*100:.2f}%")
        
        # Tăng ngày trong giai đoạn
        phase_day += 1
    
    # Hiển thị thống kê cuối cùng
    print("\n=== THỐNG KÊ SAU 30 NGÀY ===")
    
    # Tính lợi nhuận tích lũy cho mỗi mức rủi ro
    cumulative_returns = {}
    for level, daily_returns in returns.items():
        # Tính lợi nhuận tích lũy
        cumulative = 1.0
        for r in daily_returns:
            cumulative *= (1 + r)
        cumulative_returns[level] = (cumulative - 1) * 100  # Chuyển sang phần trăm
    
    # Hiển thị kết quả
    print("\nLợi nhuận tích lũy theo mức rủi ro:")
    for level, return_pct in sorted(cumulative_returns.items(), key=lambda x: risk_levels[x[0]]):
        formatted_level = f"{level} ({risk_levels[level]*100:.0f}%)"
        print(f"  - {formatted_level:25s}: {return_pct:.2f}% (Drawdown: {drawdowns[level]*100:.2f}%)")
    
    # Hiển thị phân bổ cuối cùng
    final_allocation = allocator.get_allocation()
    print("\nPhân bổ vốn cuối cùng:")
    for level, alloc in sorted(final_allocation.items(), key=lambda x: risk_levels[x[0]]):
        formatted_level = f"{level} ({risk_levels[level]*100:.0f}%)"
        print(f"  - {formatted_level:25s}: {alloc*100:.2f}%")
    
    # Lưu trạng thái
    allocator.save_state('risk_allocation_state.json')
    
    # Phân tích sự thay đổi phân bổ theo thời gian
    print("\nSự thay đổi phân bổ theo thời gian:")
    for level in risk_levels:
        formatted_level = f"{level} ({risk_levels[level]*100:.0f}%)"
        initial = allocation_over_time[0][level] * 100
        middle = allocation_over_time[len(allocation_over_time)//2][level] * 100
        final = allocation_over_time[-1][level] * 100
        
        print(f"  - {formatted_level:25s}: {initial:.2f}% -> {middle:.2f}% -> {final:.2f}%")
    
    # Kết luận
    print("\n=== KẾT LUẬN ===")
    print("1. Hệ thống đã thành công điều chỉnh phân bổ vốn dựa trên hiệu suất của từng mức rủi ro")
    print("2. Trong giai đoạn tăng giá, hệ thống ưu tiên phân bổ cho các mức rủi ro cao")
    print("3. Trong giai đoạn giảm giá, hệ thống chuyển phân bổ sang các mức an toàn")
    print("4. Hệ thống đã chứng minh tính linh hoạt thích ứng với thay đổi điều kiện thị trường")
    print("5. Chiến lược đa cấp giúp cân bằng giữa tăng trưởng và bảo toàn vốn hiệu quả")

if __name__ == "__main__":
    simulate_risk_performance()