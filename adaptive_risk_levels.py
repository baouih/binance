import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_risk_manager')

class AdaptiveRiskManager:
    """
    Quản lý rủi ro thích ứng với nhiều cấp độ rủi ro khác nhau
    """
    def __init__(self, config_path='risk_configs/adaptive_risk_config.json'):
        self.config_path = config_path
        self.risk_levels = {
            'ultra_conservative': 0.03,  # 3%
            'conservative': 0.05,        # 5%
            'moderate': 0.07,            # 7%
            'aggressive': 0.09,          # 9%
            'high_risk': 0.15,           # 15%
            'extreme_risk': 0.20         # 20%
        }
        self.current_risk_level = 'moderate'  # Mặc định bắt đầu với mức rủi ro trung bình
        self.win_streak = 0
        self.loss_streak = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.last_evaluation_time = datetime.now()
        self.market_regime = 'NEUTRAL'
        self.load_or_create_config()
        logger.info(f"Khởi tạo Adaptive Risk Manager với {len(self.risk_levels)} cấp độ rủi ro")

    def load_or_create_config(self):
        """Tải hoặc tạo mới cấu hình"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.risk_levels = config.get('risk_levels', self.risk_levels)
                    self.current_risk_level = config.get('current_risk_level', self.current_risk_level)
                    self.win_streak = config.get('win_streak', 0)
                    self.loss_streak = config.get('loss_streak', 0)
                    self.total_trades = config.get('total_trades', 0)
                    self.winning_trades = config.get('winning_trades', 0)
                logger.info(f"Đã tải cấu hình từ {self.config_path}")
            else:
                # Tạo thư mục nếu chưa tồn tại
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                self.save_config()
                logger.info(f"Đã tạo mới cấu hình tại {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình: {str(e)}")
            self.save_config()  # Lưu cấu hình mặc định

    def save_config(self):
        """Lưu cấu hình hiện tại"""
        try:
            config = {
                'risk_levels': self.risk_levels,
                'current_risk_level': self.current_risk_level,
                'win_streak': self.win_streak,
                'loss_streak': self.loss_streak,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'last_update': datetime.now().isoformat()
            }
            
            # Tạo thư mục nếu chưa tồn tại
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Đã lưu cấu hình vào {self.config_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {str(e)}")

    def update_trade_result(self, is_win, pnl=0, trade_info=None):
        """
        Cập nhật kết quả giao dịch và điều chỉnh mức rủi ro nếu cần
        
        Args:
            is_win (bool): True nếu lệnh thắng, False nếu lệnh thua
            pnl (float): Lợi nhuận/lỗ của lệnh
            trade_info (dict): Thông tin chi tiết về lệnh
        """
        self.total_trades += 1
        
        if is_win:
            self.winning_trades += 1
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.win_streak = 0
            self.loss_streak += 1
        
        # Tính win rate
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        # Điều chỉnh mức độ rủi ro dựa trên win streak và loss streak
        self._adjust_risk_level()
        
        # Log kết quả
        logger.info(f"Cập nhật kết quả lệnh: {'Thắng' if is_win else 'Thua'}, PnL: {pnl}, "
                    f"Win Streak: {self.win_streak}, Loss Streak: {self.loss_streak}, "
                    f"Win Rate: {win_rate:.2%}, Risk Level: {self.current_risk_level}")
        
        # Lưu cấu hình
        self.save_config()
        
        return {
            'new_risk_level': self.current_risk_level,
            'risk_percentage': self.get_current_risk_percentage(),
            'win_rate': win_rate,
            'total_trades': self.total_trades
        }

    def _adjust_risk_level(self):
        """Điều chỉnh mức độ rủi ro dựa trên kết quả gần đây"""
        old_level = self.current_risk_level
        
        # Tăng mức rủi ro khi có win streak
        if self.win_streak >= 5:
            if self.current_risk_level == 'ultra_conservative':
                self.current_risk_level = 'conservative'
            elif self.current_risk_level == 'conservative':
                self.current_risk_level = 'moderate'
            elif self.current_risk_level == 'moderate':
                self.current_risk_level = 'aggressive'
            elif self.current_risk_level == 'aggressive':
                self.current_risk_level = 'high_risk'
            elif self.current_risk_level == 'high_risk':
                self.current_risk_level = 'extreme_risk'
                
        # Giảm mức rủi ro khi có loss streak
        elif self.loss_streak >= 3:
            if self.current_risk_level == 'extreme_risk':
                self.current_risk_level = 'high_risk'
            elif self.current_risk_level == 'high_risk':
                self.current_risk_level = 'aggressive'
            elif self.current_risk_level == 'aggressive':
                self.current_risk_level = 'moderate'
            elif self.current_risk_level == 'moderate':
                self.current_risk_level = 'conservative'
            elif self.current_risk_level == 'conservative':
                self.current_risk_level = 'ultra_conservative'
        
        # Kiểm tra win rate tổng thể và điều chỉnh nếu cần
        if self.total_trades >= 20:
            win_rate = self.winning_trades / self.total_trades
            
            if win_rate < 0.4 and self.current_risk_level not in ['ultra_conservative', 'conservative']:
                # Giảm 2 cấp độ nếu win rate quá thấp
                if self.current_risk_level == 'extreme_risk':
                    self.current_risk_level = 'aggressive'
                elif self.current_risk_level == 'high_risk':
                    self.current_risk_level = 'moderate'
                elif self.current_risk_level == 'aggressive':
                    self.current_risk_level = 'conservative'
                elif self.current_risk_level == 'moderate':
                    self.current_risk_level = 'ultra_conservative'
            elif win_rate > 0.65 and self.current_risk_level not in ['high_risk', 'extreme_risk']:
                # Tăng 1 cấp độ nếu win rate rất cao
                if self.current_risk_level == 'ultra_conservative':
                    self.current_risk_level = 'conservative'
                elif self.current_risk_level == 'conservative':
                    self.current_risk_level = 'moderate'
                elif self.current_risk_level == 'moderate':
                    self.current_risk_level = 'aggressive'
                elif self.current_risk_level == 'aggressive':
                    self.current_risk_level = 'high_risk'
        
        # Điều chỉnh theo market regime
        if self.market_regime in ['BULL', 'STRONG_BULL']:
            # Trong thị trường tăng mạnh, có thể tăng rủi ro thêm 1 cấp
            if self.current_risk_level == 'ultra_conservative':
                self.current_risk_level = 'conservative'
            elif self.current_risk_level == 'conservative':
                self.current_risk_level = 'moderate'
            elif self.current_risk_level == 'moderate':
                self.current_risk_level = 'aggressive'
        elif self.market_regime in ['BEAR', 'STRONG_BEAR']:
            # Trong thị trường giảm mạnh, giảm rủi ro 1 cấp
            if self.current_risk_level == 'extreme_risk':
                self.current_risk_level = 'high_risk'
            elif self.current_risk_level == 'high_risk':
                self.current_risk_level = 'aggressive'
            elif self.current_risk_level == 'aggressive':
                self.current_risk_level = 'moderate'
            elif self.current_risk_level == 'moderate':
                self.current_risk_level = 'conservative'
            
        if old_level != self.current_risk_level:
            logger.info(f"Đã điều chỉnh mức rủi ro từ {old_level} sang {self.current_risk_level}")

    def get_current_risk_percentage(self):
        """Lấy phần trăm rủi ro hiện tại"""
        return self.risk_levels.get(self.current_risk_level, 0.07)

    def calculate_position_size(self, capital, entry_price, stop_loss_price, symbol=None, market_regime=None):
        """
        Tính toán kích thước vị thế dựa trên mức rủi ro hiện tại
        
        Args:
            capital (float): Vốn khả dụng
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá stop loss
            symbol (str, optional): Mã giao dịch
            market_regime (str, optional): Chế độ thị trường hiện tại
        
        Returns:
            float: Kích thước vị thế phù hợp
        """
        if market_regime:
            self.market_regime = market_regime
        
        # Lấy % rủi ro hiện tại
        risk_percentage = self.get_current_risk_percentage()
        
        # Số tiền rủi ro tối đa cho lệnh này
        risk_amount = capital * risk_percentage
        
        # Tính khoảng cách % từ entry đến stop loss
        if entry_price and stop_loss_price and entry_price != 0:
            risk_per_unit = abs(entry_price - stop_loss_price) / entry_price
        else:
            risk_per_unit = 0.015  # Mặc định 1.5% nếu không có SL cụ thể
        
        # Tránh chia cho 0
        if risk_per_unit == 0:
            risk_per_unit = 0.015
        
        # Tính kích thước vị thế
        position_size = risk_amount / (entry_price * risk_per_unit)
        
        # Điều chỉnh theo đặc thù của symbol nếu cần
        if symbol:
            # Đây là nơi bạn có thể thêm logic điều chỉnh theo từng loại coin
            # Ví dụ: BTC có thể có kích thước nhỏ hơn, altcoin có thể lớn hơn
            pass
        
        logger.info(f"Đã tính toán position size: {position_size:.6f} với risk level: {self.current_risk_level} "
                   f"({risk_percentage:.1%}), risk amount: ${risk_amount:.2f}")
        
        return position_size

    def calculate_adaptive_sl_tp(self, entry_price, direction, symbol=None, market_regime=None):
        """
        Tính toán mức SL/TP thích ứng dựa trên mức rủi ro hiện tại
        
        Args:
            entry_price (float): Giá vào lệnh
            direction (str): 'LONG' hoặc 'SHORT'
            symbol (str, optional): Mã giao dịch
            market_regime (str, optional): Chế độ thị trường hiện tại
        
        Returns:
            dict: Thông tin về SL/TP được điều chỉnh
        """
        if market_regime:
            self.market_regime = market_regime
        
        # Lấy % rủi ro cơ bản
        base_sl_percentage = 0.015  # 1.5%
        base_tp_percentage = 0.03   # 3.0%
        
        # Điều chỉnh dựa trên mức rủi ro hiện tại
        risk_factor = self.get_current_risk_percentage() / 0.07  # So với mức moderate (7%)
        
        # Các giá trị SL/TP mặc định
        sl_percentage = base_sl_percentage
        tp_percentage = base_tp_percentage * risk_factor  # TP tỷ lệ với mức rủi ro
        
        # Điều chỉnh theo chế độ thị trường
        if self.market_regime in ['VOLATILE_BULL', 'VOLATILE_BEAR']:
            sl_percentage *= 1.5  # Tăng SL trong thị trường biến động
            tp_percentage *= 1.3  # Tăng TP trong thị trường biến động
        elif self.market_regime in ['SIDEWAYS', 'NEUTRAL', 'CHOPPY']:
            sl_percentage *= 0.8  # Giảm SL trong thị trường đi ngang
            tp_percentage *= 0.7  # Giảm TP trong thị trường đi ngang
        
        # Tính giá trị SL/TP
        if direction == 'LONG':
            stop_loss = entry_price * (1 - sl_percentage)
            take_profit = entry_price * (1 + tp_percentage)
        else:  # SHORT
            stop_loss = entry_price * (1 + sl_percentage)
            take_profit = entry_price * (1 - tp_percentage)
        
        # Thiết lập các mức Take Profit từng phần
        if direction == 'LONG':
            tp1 = entry_price * (1 + tp_percentage * 0.4)  # 40% của mục tiêu
            tp2 = entry_price * (1 + tp_percentage * 0.8)  # 80% của mục tiêu
            tp3 = take_profit  # 100% của mục tiêu
            tp4 = entry_price * (1 + tp_percentage * 1.5)  # 150% của mục tiêu (cho trailing stop)
        else:  # SHORT
            tp1 = entry_price * (1 - tp_percentage * 0.4)
            tp2 = entry_price * (1 - tp_percentage * 0.8)
            tp3 = take_profit
            tp4 = entry_price * (1 - tp_percentage * 1.5)
        
        # Thiết lập thông số trailing stop
        trailing_activation = 0.015  # Kích hoạt ở mức 1.5% lợi nhuận
        trailing_step = 0.003  # Bước di chuyển 0.3%
        
        # Điều chỉnh trailing stop theo chế độ thị trường
        if self.market_regime in ['VOLATILE_BULL', 'VOLATILE_BEAR']:
            trailing_step = 0.005  # Tăng bước di chuyển trong thị trường biến động
        elif self.market_regime in ['STRONG_BULL', 'STRONG_BEAR']:
            trailing_activation = 0.02  # Kích hoạt muộn hơn trong thị trường xu hướng mạnh
        
        result = {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'tp4': tp4,
            'trailing_activation': trailing_activation,
            'trailing_step': trailing_step,
            'sl_percentage': sl_percentage,
            'tp_percentage': tp_percentage,
            'risk_level': self.current_risk_level,
            'risk_percentage': self.get_current_risk_percentage()
        }
        
        logger.info(f"Đã tính toán SL/TP thích ứng cho {direction} {symbol if symbol else ''}: "
                   f"SL={stop_loss:.2f}, TP={take_profit:.2f}, Risk={self.current_risk_level}")
        
        return result

    def evaluate_market_conditions(self, market_data):
        """
        Đánh giá điều kiện thị trường để cập nhật chế độ
        
        Args:
            market_data (dict): Dữ liệu thị trường
        """
        # TODO: Thêm logic phân tích thị trường
        pass

# Phần chạy thử nghiệm
def test_adaptive_risk_manager():
    """Chạy thử AdaptiveRiskManager"""
    print("=== KIỂM TRA ADAPTIVE RISK MANAGER ===")
    
    # Tạo thực thể AdaptiveRiskManager
    risk_manager = AdaptiveRiskManager(config_path='risk_configs/test_adaptive_risk.json')
    
    # Thiết lập thông số ban đầu
    capital = 10000  # $10,000
    entry_price = 50000  # $50,000 BTC
    sl_price = 49250  # $49,250 (1.5% dưới entry)
    
    # Test 1: Tính position size với mức rủi ro mặc định
    print("\n1. Tính position size với mức rủi ro mặc định (moderate - 7%):")
    size = risk_manager.calculate_position_size(capital, entry_price, sl_price, symbol='BTCUSDT')
    print(f"- Position Size: {size:.6f} BTC")
    print(f"- Mức rủi ro: {risk_manager.current_risk_level} ({risk_manager.get_current_risk_percentage():.1%})")
    
    # Test 2: Mô phỏng chuỗi giao dịch thắng
    print("\n2. Mô phỏng chuỗi giao dịch thắng:")
    for i in range(6):
        result = risk_manager.update_trade_result(is_win=True, pnl=100)
        print(f"- Lệnh thắng #{i+1}: Mức rủi ro mới = {result['new_risk_level']} ({result['risk_percentage']:.1%})")
    
    # Kiểm tra position size mới
    size = risk_manager.calculate_position_size(capital, entry_price, sl_price, symbol='BTCUSDT')
    print(f"- Position Size mới: {size:.6f} BTC")
    
    # Test 3: Mô phỏng chuỗi giao dịch thua
    print("\n3. Mô phỏng chuỗi giao dịch thua:")
    for i in range(4):
        result = risk_manager.update_trade_result(is_win=False, pnl=-100)
        print(f"- Lệnh thua #{i+1}: Mức rủi ro mới = {result['new_risk_level']} ({result['risk_percentage']:.1%})")
    
    # Kiểm tra position size sau chuỗi thua
    size = risk_manager.calculate_position_size(capital, entry_price, sl_price, symbol='BTCUSDT')
    print(f"- Position Size sau chuỗi thua: {size:.6f} BTC")
    
    # Test 4: Kiểm tra adaptive SL/TP
    print("\n4. Kiểm tra adaptive SL/TP ở các chế độ thị trường khác nhau:")
    
    market_regimes = ['NEUTRAL', 'BULL', 'BEAR', 'VOLATILE_BULL', 'VOLATILE_BEAR', 'STRONG_BULL', 'SIDEWAYS']
    
    for regime in market_regimes:
        sltp = risk_manager.calculate_adaptive_sl_tp(50000, 'LONG', symbol='BTCUSDT', market_regime=regime)
        print(f"\n- Chế độ {regime}:")
        print(f"  + SL: ${sltp['stop_loss']:.2f} ({sltp['sl_percentage']*100:.2f}%)")
        print(f"  + TP: ${sltp['take_profit']:.2f} ({sltp['tp_percentage']*100:.2f}%)")
        print(f"  + TP1: ${sltp['tp1']:.2f} (25% vị thế)")
        print(f"  + TP2: ${sltp['tp2']:.2f} (25% vị thế)")
        print(f"  + TP3: ${sltp['tp3']:.2f} (25% vị thế)")
        print(f"  + TP4: ${sltp['tp4']:.2f} (25% trailing stop)")
        print(f"  + Trailing kích hoạt tại: {sltp['trailing_activation']*100:.1f}%, bước: {sltp['trailing_step']*100:.1f}%")
    
    print("\n=== KẾT THÚC KIỂM TRA ===")

# Chạy test khi file được thực thi trực tiếp
if __name__ == "__main__":
    test_adaptive_risk_manager()
