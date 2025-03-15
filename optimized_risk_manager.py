import os
import sys
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimized_risk_manager.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('optimized_risk_manager')

class OptimizedRiskManager:
    """
    Quản lý rủi ro tối ưu hóa với chỉ 4 mức rủi ro phù hợp: 10%, 15%, 20%, 25%
    Mặc định là mức 20-25% dựa trên điều kiện thị trường
    """
    
    def __init__(self, account_size=10000, default_risk_level='extreme_risk'):
        self.account_size = account_size
        
        # Chỉ giữ lại 4 mức rủi ro theo yêu cầu
        self.risk_levels = {
            'high_moderate': 0.10,   # 10%
            'high_risk': 0.15,       # 15%
            'extreme_risk': 0.20,    # 20%
            'ultra_high_risk': 0.25  # 25%
        }
        
        # Thiết lập mức rủi ro mặc định là extreme_risk (20%) hoặc ultra_high_risk (25%)
        if default_risk_level not in self.risk_levels:
            default_risk_level = 'extreme_risk'  # Mặc định 20% nếu không hợp lệ
            
        self.current_risk_level = default_risk_level
        self.current_risk_percentage = self.risk_levels[self.current_risk_level]
        
        # Thông tin hiệu suất
        self.performance = {level: {'profit': 0, 'drawdown': 0, 'trades': 0, 'win_rate': 0} 
                           for level in self.risk_levels}
        
        # Trạng thái thị trường
        self.market_state = {
            'regime': 'NEUTRAL',  # BULL, BEAR, SIDEWAYS, VOLATILE
            'volatility': 'NORMAL',  # LOW, NORMAL, HIGH
            'trend_strength': 'NEUTRAL',  # STRONG, NEUTRAL, WEAK
        }
        
        # Lịch sử chuyển đổi
        self.transition_history = []
        
        # Trạng thái hoạt động
        self.is_running = False
        self.lock = threading.RLock()
        
        logger.info(f"Khởi tạo OptimizedRiskManager với account_size={account_size}")
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
                # Điều chỉnh mức rủi ro dựa trên trạng thái thị trường mới
                self._adapt_risk_level()
    
    def _adapt_risk_level(self):
        """Tự động điều chỉnh mức rủi ro dựa trên trạng thái thị trường"""
        with self.lock:
            old_risk_level = self.current_risk_level
            market_regime = self.market_state['regime']
            volatility = self.market_state['volatility']
            trend_strength = self.market_state['trend_strength']
            
            # Chiến lược đơn giản hóa:
            # - Thị trường tăng mạnh: Sử dụng mức rủi ro cao nhất (25%)
            # - Thị trường tăng bình thường: Sử dụng mức rủi ro cao (20%)
            # - Thị trường đi ngang/biến động: Sử dụng mức trung bình (15%)
            # - Thị trường giảm: Sử dụng mức thấp nhất (10%)
            
            if market_regime == 'BULL' and trend_strength == 'STRONG' and volatility != 'HIGH':
                # Thị trường tăng mạnh, ít biến động -> rủi ro cao nhất
                suggested_level = 'ultra_high_risk'  # 25%
            
            elif market_regime == 'BULL' and (trend_strength == 'NEUTRAL' or volatility == 'HIGH'):
                # Thị trường tăng nhưng không quá mạnh -> rủi ro cao
                suggested_level = 'extreme_risk'  # 20%
            
            elif market_regime == 'SIDEWAYS' or volatility == 'HIGH':
                # Thị trường đi ngang hoặc biến động cao -> rủi ro trung bình
                suggested_level = 'high_risk'  # 15%
            
            elif market_regime == 'BEAR':
                # Thị trường giảm -> rủi ro thấp
                suggested_level = 'high_moderate'  # 10%
            
            else:
                # Thị trường không xác định rõ -> rủi ro mặc định
                suggested_level = 'extreme_risk'  # 20%
            
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
                
                logger.info(f"Điều chỉnh mức rủi ro: {old_risk_level} ({self.risk_levels[old_risk_level]*100:.0f}%) -> "
                           f"{self.current_risk_level} ({self.current_risk_percentage*100:.0f}%) "
                           f"dựa trên trạng thái thị trường")
    
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
    
    def get_risk_level(self, account_type=None):
        """Lấy mức rủi ro hiện tại và phần trăm rủi ro"""
        with self.lock:
            # Không cần điều chỉnh theo loại tài khoản vì tất cả các mức rủi ro đều đã được tối ưu
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
                # Không có stop loss cụ thể, sử dụng mức % mặc định tùy theo mức rủi ro
                if risk_percentage <= 0.10:  # 10%
                    default_sl_pct = 0.01  # 1% SL
                elif risk_percentage <= 0.15:  # 15%
                    default_sl_pct = 0.015  # 1.5% SL
                elif risk_percentage <= 0.20:  # 20%
                    default_sl_pct = 0.02  # 2% SL
                else:  # 25%
                    default_sl_pct = 0.025  # 2.5% SL
                
                position_size = risk_amount / (entry_price * default_sl_pct)
            
            logger.info(f"Tính position size cho {symbol} tại mức rủi ro {risk_level} ({risk_percentage*100:.0f}%): "
                       f"size={position_size:.6f}, entry={entry_price:.2f}, risk_amount=${risk_amount:.2f}")
            
            return position_size, risk_level, risk_percentage
    
    def get_performance_stats(self):
        """Trả về thống kê hiệu suất của các mức rủi ro"""
        with self.lock:
            return self.performance
    
    def save_state(self, file_path='optimized_risk_state.json'):
        """Lưu trạng thái hiện tại ra file"""
        with self.lock:
            state = {
                'account_size': self.account_size,
                'current_risk_level': self.current_risk_level,
                'current_risk_percentage': self.current_risk_percentage,
                'risk_levels': self.risk_levels,
                'performance': self.performance,
                'market_state': self.market_state,
                'transition_history': self.transition_history,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=4)
            
            logger.info(f"Đã lưu trạng thái vào {file_path}")
    
    def load_state(self, file_path='optimized_risk_state.json'):
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
                # Không cập nhật risk_levels để đảm bảo luôn chỉ có 4 mức cố định
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
        """Bắt đầu quản lý rủi ro tối ưu"""
        with self.lock:
            if self.is_running:
                logger.warning("OptimizedRiskManager đã đang chạy")
                return
            
            self.is_running = True
            logger.info("Đã bắt đầu OptimizedRiskManager")
    
    def stop(self):
        """Dừng quản lý rủi ro tối ưu"""
        with self.lock:
            if not self.is_running:
                logger.warning("OptimizedRiskManager đã dừng")
                return
            
            self.is_running = False
            logger.info("Đã dừng OptimizedRiskManager")
    
    def get_tp_sl_levels(self, entry_price, position_type, custom_tp_ratio=None):
        """
        Tính toán các mức TP và SL dựa trên mức rủi ro hiện tại
        
        Parameters:
        - entry_price: Giá vào lệnh
        - position_type: 'LONG' hoặc 'SHORT'
        - custom_tp_ratio: Tỷ lệ TP:SL tùy chỉnh, mặc định là None (sử dụng tỷ lệ theo mức rủi ro)
        
        Returns:
        - Dictionary chứa các mức SL, TP1, TP2, TP3
        """
        with self.lock:
            # Xác định tỷ lệ SL theo mức rủi ro
            if self.current_risk_percentage <= 0.10:  # 10%
                sl_pct = 0.01  # 1%
            elif self.current_risk_percentage <= 0.15:  # 15%
                sl_pct = 0.015  # 1.5%
            elif self.current_risk_percentage <= 0.20:  # 20%
                sl_pct = 0.02  # 2%
            else:  # 25%
                sl_pct = 0.025  # 2.5%
            
            # Xác định tỷ lệ TP:SL
            if custom_tp_ratio:
                tp_ratio = custom_tp_ratio
            else:
                # Tỷ lệ mặc định theo mức rủi ro
                if self.current_risk_percentage <= 0.10:  # 10%
                    tp_ratio = 1.5  # TP:SL = 1.5:1
                elif self.current_risk_percentage <= 0.15:  # 15%
                    tp_ratio = 2.0  # TP:SL = 2:1
                elif self.current_risk_percentage <= 0.20:  # 20%
                    tp_ratio = 2.5  # TP:SL = 2.5:1
                else:  # 25%
                    tp_ratio = 3.0  # TP:SL = 3:1
            
            tp_pct = sl_pct * tp_ratio
            
            # Tính các mức TP và SL
            if position_type == 'LONG':
                sl_price = entry_price * (1 - sl_pct)
                tp1 = entry_price * (1 + tp_pct * 0.4)  # 40% của mục tiêu
                tp2 = entry_price * (1 + tp_pct * 0.7)  # 70% của mục tiêu
                tp3 = entry_price * (1 + tp_pct)        # 100% của mục tiêu
                tp4 = entry_price * (1 + tp_pct * 1.5)  # 150% của mục tiêu (trailing stop)
            else:  # SHORT
                sl_price = entry_price * (1 + sl_pct)
                tp1 = entry_price * (1 - tp_pct * 0.4)  # 40% của mục tiêu
                tp2 = entry_price * (1 - tp_pct * 0.7)  # 70% của mục tiêu
                tp3 = entry_price * (1 - tp_pct)        # 100% của mục tiêu
                tp4 = entry_price * (1 - tp_pct * 1.5)  # 150% của mục tiêu (trailing stop)
            
            return {
                'sl_price': sl_price,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'tp4': tp4,
                'sl_pct': sl_pct,
                'tp_pct': tp_pct,
                'tp_ratio': tp_ratio
            }

# Hàm test
def test_optimized_risk_manager():
    """Kiểm tra chức năng của OptimizedRiskManager"""
    # Khởi tạo với mức rủi ro mặc định là extreme_risk (20%)
    risk_manager = OptimizedRiskManager(account_size=10000)
    
    print("\n=== TEST OPTIMIZED RISK MANAGER ===")
    print(f"Mức rủi ro ban đầu: {risk_manager.current_risk_level} ({risk_manager.current_risk_percentage*100:.0f}%)")
    
    # Kiểm tra phản ứng với các trạng thái thị trường khác nhau
    test_cases = [
        # Thị trường tăng mạnh, ít biến động -> 25%
        {'regime': 'BULL', 'volatility': 'LOW', 'trend_strength': 'STRONG'},
        
        # Thị trường tăng, biến động cao -> 20%
        {'regime': 'BULL', 'volatility': 'HIGH', 'trend_strength': 'STRONG'},
        
        # Thị trường đi ngang -> 15%
        {'regime': 'SIDEWAYS', 'volatility': 'NORMAL', 'trend_strength': 'NEUTRAL'},
        
        # Thị trường giảm -> 10%
        {'regime': 'BEAR', 'volatility': 'NORMAL', 'trend_strength': 'STRONG'},
        
        # Trở lại thị trường tăng -> 25%
        {'regime': 'BULL', 'volatility': 'LOW', 'trend_strength': 'STRONG'},
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\nTest case {i+1}: {case}")
        risk_manager.update_market_state(**case)
        level, percentage = risk_manager.get_risk_level()
        print(f"Mức rủi ro sau khi cập nhật: {level} ({percentage*100:.0f}%)")
        
        # Mô phỏng tính position size
        symbol = 'BTCUSDT'
        entry_price = 50000
        
        # Tính SL/TP
        tp_sl = risk_manager.get_tp_sl_levels(entry_price, 'LONG')
        
        size, r_level, r_percentage = risk_manager.get_position_size(symbol, entry_price, tp_sl['sl_price'])
        risk_amount = risk_manager.account_size * r_percentage
        
        print(f"Position size: {size:.6f} BTC")
        print(f"Rủi ro: ${risk_amount:.2f} ({r_percentage*100:.0f}% của ${risk_manager.account_size:.0f})")
        print(f"SL: ${tp_sl['sl_price']:.2f} ({tp_sl['sl_pct']*100:.2f}% từ entry)")
        print(f"TP1: ${tp_sl['tp1']:.2f}, TP2: ${tp_sl['tp2']:.2f}, TP3: ${tp_sl['tp3']:.2f}")
        print(f"TP:SL Ratio = {tp_sl['tp_ratio']:.1f}:1")
    
    # Lưu trạng thái
    risk_manager.save_state('test_optimized_risk_state.json')
    
    # Mô phỏng cập nhật hiệu suất
    print("\nCập nhật hiệu suất:")
    
    # Thêm một vài giao dịch cho mỗi mức rủi ro
    for level in risk_manager.risk_levels:
        # Thêm một lệnh thắng
        risk_manager.update_performance(level, 100, 2.0)
        # Thêm một lệnh thua
        risk_manager.update_performance(level, -50, 5.0)
    
    # Kiểm tra hiệu suất
    performance = risk_manager.get_performance_stats()
    print("\nHiệu suất sau khi cập nhật:")
    for level, stats in performance.items():
        print(f"  - {level}: profit=${stats['profit']:.2f}, drawdown={stats['drawdown']:.2f}%, "
              f"trades={stats['trades']}, win_rate={stats.get('win_rate', 0):.2f}%")
    
    print("\n=== HOÀN THÀNH KIỂM TRA ===")

if __name__ == "__main__":
    test_optimized_risk_manager()