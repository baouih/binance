import os
import sys
import logging
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('adaptive_multi_risk.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('adaptive_multi_risk')

class AdaptiveMultiRiskManager:
    """
    Quản lý nhiều chiến lược với các mức rủi ro khác nhau
    Tự động chuyển đổi giữa các mức rủi ro dựa trên điều kiện thị trường và hiệu suất
    """
    
    def __init__(self, account_size=10000, risk_levels=None):
        self.account_size = account_size
        # Thiết lập mặc định các mức rủi ro từ phân tích backtest
        self.risk_levels = risk_levels or {
            'ultra_conservative': 0.03,  # 3% - Mức an toàn nhất, lợi nhuận thấp, drawdown thấp
            'conservative': 0.05,        # 5% - Mức an toàn, lợi nhuận ổn định
            'moderate': 0.07,            # 7% - Mức cân bằng
            'aggressive': 0.09,          # 9% - Lợi nhuận khá, rủi ro vừa phải, RR tốt nhất
            'high_risk': 0.15,           # 15% - Lợi nhuận cao, rủi ro cao
            'extreme_risk': 0.20,        # 20% - Lợi nhuận rất cao, rủi ro vẫn chấp nhận được
            'ultra_high_risk': 0.25,     # 25% - Lợi nhuận cao nhất với RR tốt
            'super_high_risk': 0.30,     # 30% - Lợi nhuận rất cao, nhưng rủi ro cao
            'max_risk': 0.40             # 40% - Lợi nhuận cực cao, rủi ro rất cao
        }
        
        # Khởi tạo chiến lược mặc định
        self.current_risk_level = 'moderate'  # Mặc định bắt đầu với mức cân bằng
        self.current_risk_percentage = self.risk_levels[self.current_risk_level]
        
        # Thiết lập phân bổ vốn giữa các mức rủi ro
        self.allocation = {
            'ultra_conservative': 0.20,  # 20% vốn cho mức an toàn nhất
            'conservative': 0.20,        # 20% vốn cho mức an toàn
            'moderate': 0.20,            # 20% vốn cho mức cân bằng
            'aggressive': 0.20,          # 20% vốn cho mức tấn công
            'high_risk': 0.10,           # 10% vốn cho mức rủi ro cao
            'extreme_risk': 0.05,        # 5% vốn cho mức rủi ro cực cao
            'ultra_high_risk': 0.03,     # 3% vốn cho mức rủi ro rất cao
            'super_high_risk': 0.02,     # 2% vốn cho mức rủi ro siêu cao
            'max_risk': 0.00             # 0% vốn cho mức rủi ro tối đa (mặc định không sử dụng)
        }
        
        # Hiệu suất của từng mức rủi ro
        self.performance = {level: {'profit': 0, 'drawdown': 0, 'trades': 0, 'win_rate': 0} 
                           for level in self.risk_levels}
        
        # Trạng thái thị trường hiện tại
        self.market_state = {
            'regime': 'NEUTRAL',  # BULL, BEAR, SIDEWAYS, VOLATILE
            'volatility': 'NORMAL',  # LOW, NORMAL, HIGH
            'trend_strength': 'NEUTRAL',  # STRONG, NEUTRAL, WEAK
        }
        
        # Lưu lịch sử chuyển đổi
        self.transition_history = []
        
        # Trạng thái hoạt động
        self.is_running = False
        self.lock = threading.RLock()
        
        logger.info(f"Khởi tạo AdaptiveMultiRiskManager với account_size={account_size}")
        logger.info(f"Mức rủi ro mặc định: {self.current_risk_level} ({self.current_risk_percentage*100:.0f}%)")
    
    def update_market_state(self, regime, volatility, trend_strength):
        """Cập nhật trạng thái thị trường hiện tại"""
        with self.lock:
            old_state = self.market_state.copy()
            self.market_state = {
                'regime': regime,
                'volatility': volatility,
                'trend_strength': trend_strength
            }
            
            if old_state != self.market_state:
                logger.info(f"Cập nhật trạng thái thị trường: {old_state} -> {self.market_state}")
                # Kiểm tra xem có cần điều chỉnh mức rủi ro không
                self._adapt_risk_level()
    
    def update_performance(self, risk_level, profit_change, drawdown=None):
        """Cập nhật hiệu suất cho một mức rủi ro cụ thể"""
        with self.lock:
            if risk_level not in self.performance:
                logger.warning(f"Mức rủi ro không tồn tại: {risk_level}")
                return
            
            self.performance[risk_level]['profit'] += profit_change
            
            if drawdown is not None:
                # Chỉ cập nhật drawdown nếu giá trị mới lớn hơn
                self.performance[risk_level]['drawdown'] = max(
                    self.performance[risk_level]['drawdown'], 
                    drawdown
                )
            
            # Tăng số lệnh
            self.performance[risk_level]['trades'] += 1
            
            # Cập nhật win_rate nếu là lệnh thắng
            if profit_change > 0:
                wins = self.performance[risk_level].get('wins', 0) + 1
                self.performance[risk_level]['wins'] = wins
                self.performance[risk_level]['win_rate'] = wins / self.performance[risk_level]['trades'] * 100
            
            logger.info(f"Cập nhật hiệu suất {risk_level}: profit={self.performance[risk_level]['profit']:.2f}, "
                        f"drawdown={self.performance[risk_level]['drawdown']:.2f}, "
                        f"win_rate={self.performance[risk_level]['win_rate']:.2f}%")
            
            # Kiểm tra xem có cần điều chỉnh mức rủi ro không
            self._adapt_risk_level()
    
    def _adapt_risk_level(self):
        """Tự động điều chỉnh mức rủi ro dựa trên trạng thái thị trường và hiệu suất"""
        with self.lock:
            old_risk_level = self.current_risk_level
            market_regime = self.market_state['regime']
            volatility = self.market_state['volatility']
            trend_strength = self.market_state['trend_strength']
            
            # Điều chỉnh dựa trên trạng thái thị trường
            if market_regime == 'BULL' and trend_strength == 'STRONG':
                if volatility == 'LOW':
                    # Thị trường tăng mạnh, ít biến động -> tăng rủi ro
                    suggested_level = 'high_risk'
                elif volatility == 'NORMAL':
                    # Thị trường tăng mạnh, biến động vừa phải -> tăng rủi ro vừa phải
                    suggested_level = 'aggressive'
                else:  # HIGH volatility
                    # Thị trường tăng mạnh nhưng biến động cao -> thận trọng
                    suggested_level = 'moderate'
            
            elif market_regime == 'BEAR' and trend_strength == 'STRONG':
                if volatility == 'LOW':
                    # Thị trường giảm mạnh, ít biến động -> giảm rủi ro
                    suggested_level = 'conservative'
                elif volatility == 'NORMAL':
                    # Thị trường giảm mạnh, biến động vừa phải -> thận trọng cao
                    suggested_level = 'ultra_conservative'
                else:  # HIGH volatility
                    # Thị trường giảm mạnh và biến động cao -> rủi ro tối thiểu
                    suggested_level = 'ultra_conservative'
            
            elif market_regime == 'SIDEWAYS':
                if volatility == 'LOW':
                    # Thị trường đi ngang, ít biến động -> rủi ro vừa phải
                    suggested_level = 'moderate'
                elif volatility == 'NORMAL':
                    # Thị trường đi ngang, biến động vừa phải -> thận trọng
                    suggested_level = 'conservative'
                else:  # HIGH volatility
                    # Thị trường đi ngang nhưng biến động cao -> thận trọng cao
                    suggested_level = 'ultra_conservative'
            
            elif market_regime == 'VOLATILE':
                # Thị trường biến động mạnh -> giảm rủi ro
                suggested_level = 'ultra_conservative'
            
            else:  # NEUTRAL và các trường hợp khác
                # Mặc định sử dụng mức cân bằng
                suggested_level = 'moderate'
            
            # Chỉ thay đổi nếu mức đề xuất khác với mức hiện tại
            if suggested_level != self.current_risk_level:
                # Lưu lại lịch sử chuyển đổi
                transition = {
                    'timestamp': datetime.now().isoformat(),
                    'from_level': self.current_risk_level,
                    'to_level': suggested_level,
                    'market_state': self.market_state.copy(),
                    'reason': f"Tự động điều chỉnh dựa trên trạng thái thị trường: {self.market_state}"
                }
                self.transition_history.append(transition)
                
                # Cập nhật mức rủi ro mới
                self.current_risk_level = suggested_level
                self.current_risk_percentage = self.risk_levels[self.current_risk_level]
                
                logger.info(f"Điều chỉnh mức rủi ro: {old_risk_level} -> {self.current_risk_level} "
                           f"({self.current_risk_percentage*100:.0f}%) dựa trên trạng thái thị trường")
    
    def get_risk_level(self, account_type=None):
        """Lấy mức rủi ro hiện tại và phần trăm rủi ro"""
        with self.lock:
            # Nếu có chỉ định loại tài khoản, có thể điều chỉnh mức rủi ro phù hợp
            if account_type == 'small':
                # Tài khoản nhỏ thường không nên sử dụng mức rủi ro quá cao
                if self.current_risk_level in ['extreme_risk', 'ultra_high_risk', 'super_high_risk', 'max_risk']:
                    adjusted_level = 'high_risk'
                    logger.info(f"Điều chỉnh mức rủi ro cho tài khoản nhỏ: {self.current_risk_level} -> {adjusted_level}")
                    return adjusted_level, self.risk_levels[adjusted_level]
            
            # Trả về mức mặc định
            return self.current_risk_level, self.current_risk_percentage
    
    def get_position_size(self, symbol, entry_price, stop_loss_price=None, account_type=None):
        """Tính toán kích thước vị thế dựa trên mức rủi ro hiện tại"""
        with self.lock:
            risk_level, risk_percentage = self.get_risk_level(account_type)
            
            # Tính risk amount (số tiền chấp nhận rủi ro)
            risk_amount = self.account_size * risk_percentage
            
            # Nếu có stop loss, tính position size dựa trên khoảng cách stop loss
            if stop_loss_price is not None and stop_loss_price > 0:
                if entry_price > stop_loss_price:  # LONG position
                    sl_distance_pct = (entry_price - stop_loss_price) / entry_price
                else:  # SHORT position
                    sl_distance_pct = (stop_loss_price - entry_price) / entry_price
                
                # Đảm bảo sl_distance_pct không quá nhỏ dẫn đến position size quá lớn
                sl_distance_pct = max(sl_distance_pct, 0.005)  # Tối thiểu 0.5%
                
                # Tính position size
                position_size = risk_amount / (entry_price * sl_distance_pct)
            else:
                # Không có stop loss cụ thể, sử dụng mức % mặc định
                default_sl_pct = 0.02  # 2% mặc định
                position_size = risk_amount / (entry_price * default_sl_pct)
            
            logger.info(f"Tính position size cho {symbol} tại mức rủi ro {risk_level} ({risk_percentage*100:.0f}%): "
                       f"size={position_size:.6f}, entry={entry_price:.2f}, risk_amount=${risk_amount:.2f}")
            
            return position_size, risk_level, risk_percentage
    
    def allocate_capital(self):
        """Phân bổ vốn giữa các mức rủi ro khác nhau"""
        with self.lock:
            allocation_result = {}
            for level, percentage in self.allocation.items():
                if percentage > 0:
                    allocation_result[level] = {
                        'risk_percentage': self.risk_levels[level],
                        'capital_allocation': percentage,
                        'allocated_amount': self.account_size * percentage
                    }
            
            logger.info(f"Phân bổ vốn: {json.dumps(allocation_result, indent=2)}")
            return allocation_result
    
    def get_performance_stats(self):
        """Trả về thống kê hiệu suất của các mức rủi ro"""
        with self.lock:
            return self.performance
    
    def save_state(self, file_path='multi_risk_state.json'):
        """Lưu trạng thái hiện tại ra file"""
        with self.lock:
            state = {
                'account_size': self.account_size,
                'current_risk_level': self.current_risk_level,
                'current_risk_percentage': self.current_risk_percentage,
                'risk_levels': self.risk_levels,
                'allocation': self.allocation,
                'performance': self.performance,
                'market_state': self.market_state,
                'transition_history': self.transition_history,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=4)
            
            logger.info(f"Đã lưu trạng thái vào {file_path}")
    
    def load_state(self, file_path='multi_risk_state.json'):
        """Tải trạng thái từ file"""
        if not os.path.exists(file_path):
            logger.warning(f"Không tìm thấy file {file_path}")
            return False
        
        with self.lock:
            try:
                with open(file_path, 'r') as f:
                    state = json.load(f)
                
                self.account_size = state.get('account_size', self.account_size)
                self.current_risk_level = state.get('current_risk_level', self.current_risk_level)
                self.current_risk_percentage = state.get('current_risk_percentage', self.current_risk_percentage)
                self.risk_levels = state.get('risk_levels', self.risk_levels)
                self.allocation = state.get('allocation', self.allocation)
                self.performance = state.get('performance', self.performance)
                self.market_state = state.get('market_state', self.market_state)
                self.transition_history = state.get('transition_history', self.transition_history)
                
                logger.info(f"Đã tải trạng thái từ {file_path}")
                logger.info(f"Mức rủi ro hiện tại: {self.current_risk_level} ({self.current_risk_percentage*100:.0f}%)")
                return True
            
            except Exception as e:
                logger.error(f"Lỗi khi tải trạng thái: {str(e)}")
                return False
    
    def start(self):
        """Bắt đầu quản lý rủi ro thích ứng"""
        with self.lock:
            if self.is_running:
                logger.warning("AdaptiveMultiRiskManager đã đang chạy")
                return
            
            self.is_running = True
            logger.info("Đã bắt đầu AdaptiveMultiRiskManager")
    
    def stop(self):
        """Dừng quản lý rủi ro thích ứng"""
        with self.lock:
            if not self.is_running:
                logger.warning("AdaptiveMultiRiskManager đã dừng")
                return
            
            self.is_running = False
            logger.info("Đã dừng AdaptiveMultiRiskManager")

# Hàm test
def test_adaptive_multi_risk():
    """Kiểm tra chức năng của AdaptiveMultiRiskManager"""
    risk_manager = AdaptiveMultiRiskManager(account_size=10000)
    
    print("\n=== TEST ADAPTIVE MULTI-RISK MANAGER ===")
    print(f"Mức rủi ro ban đầu: {risk_manager.current_risk_level} ({risk_manager.current_risk_percentage*100:.0f}%)")
    
    # Kiểm tra phản ứng với các trạng thái thị trường khác nhau
    test_cases = [
        # Thị trường tăng mạnh, ít biến động
        {'regime': 'BULL', 'volatility': 'LOW', 'trend_strength': 'STRONG'},
        
        # Thị trường tăng mạnh, biến động cao
        {'regime': 'BULL', 'volatility': 'HIGH', 'trend_strength': 'STRONG'},
        
        # Thị trường giảm mạnh, biến động cao
        {'regime': 'BEAR', 'volatility': 'HIGH', 'trend_strength': 'STRONG'},
        
        # Thị trường đi ngang, ít biến động
        {'regime': 'SIDEWAYS', 'volatility': 'LOW', 'trend_strength': 'NEUTRAL'},
        
        # Thị trường biến động mạnh
        {'regime': 'VOLATILE', 'volatility': 'HIGH', 'trend_strength': 'WEAK'},
        
        # Về trạng thái trung lập
        {'regime': 'NEUTRAL', 'volatility': 'NORMAL', 'trend_strength': 'NEUTRAL'},
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\nTest case {i+1}: {case}")
        risk_manager.update_market_state(**case)
        level, percentage = risk_manager.get_risk_level()
        print(f"Mức rủi ro sau khi cập nhật: {level} ({percentage*100:.0f}%)")
        
        # Mô phỏng tính position size
        symbol = 'BTCUSDT'
        entry_price = 50000
        stop_loss = entry_price * 0.98  # 2% stop loss
        size, r_level, r_percentage = risk_manager.get_position_size(symbol, entry_price, stop_loss)
        print(f"Position size: {size:.6f} BTC, Rủi ro: ${r_percentage*100:.0f}% của ${risk_manager.account_size:.0f} = ${risk_manager.account_size*r_percentage:.2f}")
    
    # Kiểm tra phân bổ vốn
    print("\nPhân bổ vốn giữa các mức rủi ro:")
    allocation = risk_manager.allocate_capital()
    for level, data in allocation.items():
        print(f"  - {level}: {data['capital_allocation']*100:.0f}% (${data['allocated_amount']:.0f}) với mức rủi ro {data['risk_percentage']*100:.0f}%")
    
    # Lưu và tải trạng thái
    risk_manager.save_state('test_multi_risk_state.json')
    
    # Mô phỏng cập nhật hiệu suất
    print("\nCập nhật hiệu suất:")
    # Thắng ở mức rủi ro thấp
    risk_manager.update_performance('conservative', 100, 1.2)
    # Thua ở mức rủi ro cao
    risk_manager.update_performance('high_risk', -200, 5.3)
    
    # Kiểm tra lại hiệu suất
    performance = risk_manager.get_performance_stats()
    print("Hiệu suất sau khi cập nhật:")
    for level, stats in performance.items():
        if stats['trades'] > 0:
            print(f"  - {level}: profit=${stats['profit']:.2f}, drawdown={stats['drawdown']:.2f}%, trades={stats['trades']}, win_rate={stats['win_rate']:.2f}%")
    
    print("\n=== HOÀN THÀNH KIỂM TRA ===")

if __name__ == "__main__":
    test_adaptive_multi_risk()