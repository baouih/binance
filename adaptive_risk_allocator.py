"""
Adaptive Risk Allocator - Bộ điều chỉnh rủi ro thích ứng

Module này cung cấp công cụ điều chỉnh mức rủi ro thích ứng dựa trên
chế độ thị trường, hiệu suất tài khoản và các yếu tố khác.

Mục tiêu chính là đảm bảo mức rủi ro phù hợp với điều kiện thị trường hiện tại
và tối ưu hóa tỷ lệ thắng/thua của hệ thống.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Tuple, Optional, Union, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_risk_allocator')

# Import EnhancedMarketRegimeDetector nếu có
try:
    from enhanced_market_regime_detector import EnhancedMarketRegimeDetector
    USE_ENHANCED_DETECTOR = True
    logger.info("Sử dụng Enhanced Market Regime Detector")
except ImportError:
    USE_ENHANCED_DETECTOR = False
    logger.warning("Enhanced Market Regime Detector không có sẵn, sử dụng phương pháp đơn giản")

class AdaptiveRiskAllocator:
    """
    Điều chỉnh mức rủi ro dựa trên chế độ thị trường, hiệu suất tài khoản
    và các yếu tố khác. Hỗ trợ điều chỉnh tự động và đề xuất mức rủi ro
    phù hợp với điều kiện thị trường.
    """
    
    def __init__(self, base_risk: float = 2.0, max_risk: float = 5.0, min_risk: float = 0.5, 
               account_factor_weight: float = 0.3, market_factor_weight: float = 0.7):
        """
        Khởi tạo Adaptive Risk Allocator.
        
        Args:
            base_risk (float): Mức rủi ro cơ sở (%) - mặc định là 2.0%
            max_risk (float): Mức rủi ro tối đa (%) - mặc định là 5.0%
            min_risk (float): Mức rủi ro tối thiểu (%) - mặc định là 0.5%
            account_factor_weight (float): Trọng số cho hiệu suất tài khoản (0-1)
            market_factor_weight (float): Trọng số cho điều kiện thị trường (0-1)
        """
        # Mức rủi ro cơ sở và giới hạn
        self.base_risk = base_risk
        self.max_risk = max_risk
        self.min_risk = min_risk
        
        # Trọng số cho các yếu tố điều chỉnh
        self.account_factor_weight = account_factor_weight
        self.market_factor_weight = market_factor_weight
        
        # Sử dụng EnhancedMarketRegimeDetector nếu có
        if USE_ENHANCED_DETECTOR:
            self.regime_detector = EnhancedMarketRegimeDetector()
        else:
            self.regime_detector = None
            
        # Mức rủi ro cơ sở theo chế độ thị trường
        self.regime_base_risk = {
            'trending_bullish': base_risk * 1.25,    # 2.5% cho xu hướng tăng
            'trending_bearish': base_risk * 1.0,     # 2.0% cho xu hướng giảm
            'ranging_narrow': base_risk * 0.9,       # 1.8% cho dao động hẹp
            'ranging_wide': base_risk * 1.1,         # 2.2% cho dao động rộng
            'volatile_breakout': base_risk * 0.75,   # 1.5% cho bứt phá mạnh
            'quiet_accumulation': base_risk * 1.15,  # 2.3% cho tích lũy yên lặng
            'neutral': base_risk                     # 2.0% cho trung tính
        }
        
        # Các cài đặt rủi ro theo profile
        self.risk_profile_settings = {
            'conservative': {
                'base_multiplier': 0.75,  # 75% của mức cơ sở
                'max_risk': max_risk * 0.6,
                'min_risk': min_risk,
                'win_streak_bonus': 0.05,  # +0.05% cho mỗi lệnh thắng liên tiếp
                'lose_streak_penalty': 0.1,  # -0.1% cho mỗi lệnh thua liên tiếp
                'drawdown_sensitivity': 0.05  # -0.05% cho mỗi 1% drawdown
            },
            'balanced': {
                'base_multiplier': 1.0,  # 100% của mức cơ sở
                'max_risk': max_risk * 0.8,
                'min_risk': min_risk,
                'win_streak_bonus': 0.1,
                'lose_streak_penalty': 0.15,
                'drawdown_sensitivity': 0.04
            },
            'aggressive': {
                'base_multiplier': 1.2,  # 120% của mức cơ sở
                'max_risk': max_risk,
                'min_risk': min_risk,
                'win_streak_bonus': 0.15,
                'lose_streak_penalty': 0.2,
                'drawdown_sensitivity': 0.03
            }
        }
        
        # Lưu trữ lịch sử điều chỉnh
        self.adjustment_history = []
        self.last_adjustment_time = None
        
        # Trạng thái thị trường hiện tại
        self.current_market_state = {
            'regime': 'neutral',
            'volatility': 'normal',
            'trend_strength': 'neutral',
            'last_update': datetime.now()
        }
        
        # Tạo thư mục lưu trữ
        os.makedirs('data/risk_adjustments', exist_ok=True)
    
    def calculate_adaptive_risk(self, market_data: pd.DataFrame, account_stats: Dict = None, 
                              symbol: str = None, profile: str = 'balanced') -> Dict:
        """
        Tính toán mức rủi ro thích ứng dựa trên dữ liệu thị trường và hiệu suất tài khoản.
        
        Args:
            market_data (pd.DataFrame): Dữ liệu thị trường OHLCV
            account_stats (Dict, optional): Thống kê tài khoản (win_streak, lose_streak, current_drawdown, ...)
            symbol (str, optional): Cặp tiền tệ
            profile (str, optional): Profile rủi ro ('conservative', 'balanced', 'aggressive')
            
        Returns:
            Dict: Kết quả phân tích rủi ro thích ứng
        """
        try:
            # Xác định chế độ thị trường
            regime = self._detect_market_regime(market_data, symbol)
            
            # Xác định mức rủi ro cơ sở theo chế độ thị trường
            base_regime_risk = self.regime_base_risk.get(regime, self.base_risk)
            
            # Điều chỉnh theo profile
            profile_settings = self.risk_profile_settings.get(profile, self.risk_profile_settings['balanced'])
            adjusted_base_risk = base_regime_risk * profile_settings['base_multiplier']
            
            # Nếu có thông tin tài khoản, áp dụng điều chỉnh dựa trên hiệu suất
            account_adjustment = 0
            if account_stats:
                # Điều chỉnh theo chuỗi thắng/thua
                win_streak = account_stats.get('win_streak', 0)
                lose_streak = account_stats.get('lose_streak', 0)
                
                win_bonus = min(win_streak * profile_settings['win_streak_bonus'], 0.5)  # Tối đa +0.5%
                lose_penalty = min(lose_streak * profile_settings['lose_streak_penalty'], 1.0)  # Tối đa -1.0%
                
                # Điều chỉnh theo drawdown
                current_drawdown = account_stats.get('current_drawdown', 0)  # % drawdown
                drawdown_penalty = min(current_drawdown * profile_settings['drawdown_sensitivity'], 1.0)  # Tối đa -1.0%
                
                # Tổng điều chỉnh
                account_adjustment = win_bonus - lose_penalty - drawdown_penalty
            
            # Tính mức rủi ro thích ứng cuối cùng
            adaptive_risk = adjusted_base_risk + account_adjustment * self.account_factor_weight
            
            # Giới hạn trong khoảng min-max
            adaptive_risk = min(max(adaptive_risk, profile_settings['min_risk']), profile_settings['max_risk'])
            
            # Tạo kết quả
            result = {
                'regime': regime,
                'base_risk': self.base_risk,
                'base_regime_risk': base_regime_risk,
                'adaptive_risk': adaptive_risk,
                'account_adjustment': account_adjustment,
                'profile': profile,
                'timestamp': datetime.now().isoformat(),
                'analysis_factors': {
                    'win_streak': account_stats.get('win_streak', 0) if account_stats else 0,
                    'lose_streak': account_stats.get('lose_streak', 0) if account_stats else 0,
                    'current_drawdown': account_stats.get('current_drawdown', 0) if account_stats else 0
                }
            }
            
            # Lưu lịch sử điều chỉnh
            self._save_adjustment_history(result, symbol)
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tính mức rủi ro thích ứng: {str(e)}")
            return {
                'regime': 'neutral',
                'base_risk': self.base_risk,
                'base_regime_risk': self.base_risk,
                'adaptive_risk': self.base_risk,
                'account_adjustment': 0,
                'profile': profile,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def calculate_position_size(self, account_balance: float, entry_price: float, 
                              stop_loss_price: float, risk_percentage: float = None,
                              symbol: str = None, market_data: pd.DataFrame = None) -> Dict:
        """
        Tính toán kích thước vị thế dựa trên mức rủi ro.
        
        Args:
            account_balance (float): Số dư tài khoản
            entry_price (float): Giá vào lệnh
            stop_loss_price (float): Giá dừng lỗ
            risk_percentage (float, optional): Mức rủi ro (%). Nếu None, sẽ sử dụng mức thích ứng.
            symbol (str, optional): Cặp tiền tệ
            market_data (pd.DataFrame, optional): Dữ liệu thị trường OHLCV
            
        Returns:
            Dict: Thông tin kích thước vị thế
        """
        try:
            # Nếu không cung cấp mức rủi ro, tính toán mức thích ứng
            if risk_percentage is None:
                if market_data is not None and symbol is not None:
                    # Tính mức rủi ro thích ứng
                    adaptive_result = self.calculate_adaptive_risk(market_data, symbol=symbol)
                    risk_percentage = adaptive_result['adaptive_risk']
                else:
                    # Sử dụng mức rủi ro cơ sở
                    risk_percentage = self.base_risk
            
            # Tính số tiền rủi ro
            risk_amount = account_balance * (risk_percentage / 100)
            
            # Tính khoảng cách dừng lỗ (%)
            if entry_price > stop_loss_price:  # Long position
                stop_loss_distance_percent = (entry_price - stop_loss_price) / entry_price * 100
                position_type = 'long'
            else:  # Short position
                stop_loss_distance_percent = (stop_loss_price - entry_price) / entry_price * 100
                position_type = 'short'
            
            # Tính kích thước vị thế (số coin)
            position_size_in_coins = risk_amount / (entry_price * stop_loss_distance_percent / 100)
            
            # Tính kích thước vị thế (USD)
            position_size_in_usd = position_size_in_coins * entry_price
            
            # Tính leverage cần thiết nếu sử dụng margin/futures
            leverage_needed = position_size_in_usd / account_balance
            suggested_leverage = min(20, max(1, round(leverage_needed * 1.2)))  # Thêm 20% margin
            
            # Tạo kết quả
            result = {
                'risk_percentage': risk_percentage,
                'risk_amount': risk_amount,
                'entry_price': entry_price,
                'stop_loss_price': stop_loss_price,
                'stop_loss_distance_percent': stop_loss_distance_percent,
                'position_size_in_coins': position_size_in_coins,
                'position_size_in_usd': position_size_in_usd,
                'leverage_needed': leverage_needed,
                'suggested_leverage': suggested_leverage,
                'position_type': position_type,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi tính kích thước vị thế: {str(e)}")
            return {
                'error': str(e),
                'risk_percentage': risk_percentage if risk_percentage is not None else self.base_risk,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_risk_suggestion(self, symbol: str, risk_profile: str = 'balanced') -> Dict:
        """
        Đưa ra đề xuất mức rủi ro dựa trên chế độ thị trường hiện tại.
        
        Args:
            symbol (str): Cặp tiền tệ
            risk_profile (str): Profile rủi ro ('conservative', 'balanced', 'aggressive')
            
        Returns:
            Dict: Đề xuất mức rủi ro
        """
        # Lấy chế độ thị trường hiện tại (hoặc trung tính nếu không có)
        current_regime = self.current_market_state.get('regime', 'neutral')
        
        # Mức rủi ro cơ sở theo chế độ
        base_regime_risk = self.regime_base_risk.get(current_regime, self.base_risk)
        
        # Điều chỉnh theo profile
        profile_settings = self.risk_profile_settings.get(risk_profile, self.risk_profile_settings['balanced'])
        suggested_risk = base_regime_risk * profile_settings['base_multiplier']
        
        # Giới hạn trong khoảng min-max
        suggested_risk = min(max(suggested_risk, profile_settings['min_risk']), profile_settings['max_risk'])
        
        # Xác định lý do đề xuất
        reasons = {
            'trending_bullish': "Xu hướng tăng mạnh, có thể tăng rủi ro để tối đa hóa lợi nhuận.",
            'trending_bearish': "Xu hướng giảm, duy trì mức rủi ro cơ sở để đảm bảo an toàn.",
            'ranging_narrow': "Thị trường dao động hẹp, giảm nhẹ rủi ro và tập trung vào các giao dịch phạm vi.",
            'ranging_wide': "Thị trường dao động rộng, tăng nhẹ rủi ro để tận dụng biến động lớn.",
            'volatile_breakout': "Thị trường bứt phá mạnh, giảm rủi ro để đối phó với biến động cao.",
            'quiet_accumulation': "Thị trường đang tích lũy yên lặng, có thể tăng nhẹ rủi ro cho các cơ hội bứt phá.",
            'neutral': "Thị trường không có xu hướng rõ ràng, duy trì mức rủi ro cơ sở."
        }
        
        suggestion_reason = reasons.get(current_regime, reasons['neutral'])
        
        # Thêm thông tin chi tiết dựa trên profile
        profile_descriptions = {
            'conservative': "Profile bảo thủ: ưu tiên bảo toàn vốn, giảm thiểu rủi ro.",
            'balanced': "Profile cân bằng: cân bằng giữa rủi ro và lợi nhuận.",
            'aggressive': "Profile tích cực: chấp nhận rủi ro cao hơn để tối đa hóa lợi nhuận."
        }
        
        profile_description = profile_descriptions.get(risk_profile, profile_descriptions['balanced'])
        
        # Tạo đề xuất
        result = {
            'symbol': symbol,
            'current_regime': current_regime,
            'risk_profile': risk_profile,
            'profile_description': profile_description,
            'suggested_risk_percentage': suggested_risk,
            'base_regime_risk': base_regime_risk,
            'suggestion_reason': suggestion_reason,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    def get_adjustment_history(self, symbol: str = None, days: int = 30) -> List[Dict]:
        """
        Lấy lịch sử điều chỉnh rủi ro.
        
        Args:
            symbol (str, optional): Cặp tiền tệ
            days (int, optional): Số ngày lịch sử
            
        Returns:
            List[Dict]: Lịch sử điều chỉnh rủi ro
        """
        try:
            # Nếu có symbol, tải từ file
            if symbol:
                file_path = f'data/risk_adjustments/{symbol}_risk_history.json'
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        all_history = json.load(f)
                    
                    # Lọc theo số ngày
                    if days:
                        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                        filtered_history = [h for h in all_history if h['timestamp'] >= cutoff_date]
                        return filtered_history
                    
                    return all_history
            
            # Nếu không có symbol hoặc file không tồn tại, trả về lịch sử trong bộ nhớ
            return self.adjustment_history
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy lịch sử điều chỉnh: {str(e)}")
            return []
    
    def _detect_market_regime(self, market_data: pd.DataFrame, symbol: str = None) -> str:
        """
        Phát hiện chế độ thị trường hiện tại.
        
        Args:
            market_data (pd.DataFrame): Dữ liệu thị trường OHLCV
            symbol (str, optional): Cặp tiền tệ
            
        Returns:
            str: Chế độ thị trường
        """
        # Sử dụng EnhancedMarketRegimeDetector nếu có
        if USE_ENHANCED_DETECTOR and self.regime_detector:
            result = self.regime_detector.detect_regime(market_data, symbol)
            regime = result.get('regime', 'neutral')
            
            # Cập nhật trạng thái thị trường hiện tại
            self.current_market_state['regime'] = regime
            self.current_market_state['last_update'] = datetime.now()
            
            return regime
        
        # Phương pháp đơn giản nếu không có EnhancedMarketRegimeDetector
        try:
            # Kiểm tra xu hướng
            if 'close' in market_data.columns and len(market_data) >= 20:
                ma20 = market_data['close'].rolling(window=20).mean()
                ma50 = market_data['close'].rolling(window=50).mean() if len(market_data) >= 50 else None
                
                latest_close = market_data['close'].iloc[-1]
                latest_ma20 = ma20.iloc[-1]
                
                # Tính biến động
                volatility = market_data['close'].pct_change().std() * 100  # % biến động
                
                if ma50 is not None:
                    latest_ma50 = ma50.iloc[-1]
                    
                    # Xu hướng tăng
                    if latest_close > latest_ma20 > latest_ma50 and latest_close / latest_ma50 > 1.03:
                        regime = 'trending_bullish'
                    # Xu hướng giảm
                    elif latest_close < latest_ma20 < latest_ma50 and latest_close / latest_ma50 < 0.97:
                        regime = 'trending_bearish'
                    # Dao động hẹp
                    elif 0.98 < latest_close / latest_ma50 < 1.02 and volatility < 1.5:
                        regime = 'ranging_narrow'
                    # Dao động rộng
                    elif 0.95 < latest_close / latest_ma50 < 1.05 and volatility >= 1.5:
                        regime = 'ranging_wide'
                    # Bứt phá mạnh
                    elif (latest_close / latest_ma20 > 1.05 or latest_close / latest_ma20 < 0.95) and volatility > 3:
                        regime = 'volatile_breakout'
                    # Tích lũy yên lặng
                    elif 0.99 < latest_close / latest_ma20 < 1.01 and volatility < 1:
                        regime = 'quiet_accumulation'
                    else:
                        regime = 'neutral'
                else:
                    # Đơn giản hơn nếu không đủ dữ liệu
                    if latest_close > latest_ma20 * 1.03:
                        regime = 'trending_bullish'
                    elif latest_close < latest_ma20 * 0.97:
                        regime = 'trending_bearish'
                    else:
                        regime = 'neutral'
                
                # Cập nhật trạng thái thị trường hiện tại
                self.current_market_state['regime'] = regime
                self.current_market_state['volatility'] = 'high' if volatility > 2 else ('low' if volatility < 1 else 'normal')
                self.current_market_state['last_update'] = datetime.now()
                
                return regime
            
            return 'neutral'  # Mặc định nếu không đủ dữ liệu
            
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện chế độ thị trường: {str(e)}")
            return 'neutral'
    
    def _save_adjustment_history(self, adjustment_result: Dict, symbol: str = None) -> None:
        """
        Lưu lịch sử điều chỉnh rủi ro.
        
        Args:
            adjustment_result (Dict): Kết quả điều chỉnh rủi ro
            symbol (str, optional): Cặp tiền tệ
        """
        try:
            # Thêm vào lịch sử trong bộ nhớ
            self.adjustment_history.append(adjustment_result)
            self.last_adjustment_time = datetime.now()
            
            # Giới hạn kích thước
            if len(self.adjustment_history) > 1000:
                self.adjustment_history = self.adjustment_history[-1000:]
            
            # Nếu có symbol, lưu vào file
            if symbol:
                file_path = f'data/risk_adjustments/{symbol}_risk_history.json'
                
                # Tải lịch sử cũ nếu có
                existing_history = []
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            existing_history = json.load(f)
                    except:
                        pass
                
                # Thêm điều chỉnh mới
                existing_history.append(adjustment_result)
                
                # Giới hạn kích thước
                if len(existing_history) > 1000:
                    existing_history = existing_history[-1000:]
                
                # Lưu vào file
                with open(file_path, 'w') as f:
                    json.dump(existing_history, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Lỗi khi lưu lịch sử điều chỉnh: {str(e)}")


if __name__ == "__main__":
    # Ví dụ sử dụng
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Tạo dữ liệu mẫu
    days = 100
    now = datetime.now()
    dates = [now - timedelta(days=i) for i in range(days, 0, -1)]
    
    # Tạo giá theo mô hình đơn giản
    prices = []
    
    for i in range(days):
        # Chia thành các đoạn khác nhau để mô phỏng các chế độ thị trường
        if i < days * 0.3:  # 30% đầu: trending bullish
            trend = 10 * (i / (days * 0.3))
            noise = np.random.normal(0, 1)
            price = 100 + trend + noise
        elif i < days * 0.6:  # 30% tiếp: ranging
            mid_price = 110
            swing = 5 * np.sin(i * 0.2)
            noise = np.random.normal(0, 1)
            price = mid_price + swing + noise
        else:  # 40% cuối: trending bearish
            start_price = 110
            drop = 15 * ((i - days * 0.6) / (days * 0.4))
            noise = np.random.normal(0, 1)
            price = start_price - drop + noise
        
        prices.append(price)
    
    # Tạo DataFrame
    df = pd.DataFrame({
        'open': [prices[i-1] if i > 0 else prices[i] * 0.99 for i in range(days)],
        'high': [p * (1 + 0.01 * np.random.random()) for p in prices],
        'low': [p * (1 - 0.01 * np.random.random()) for p in prices],
        'close': prices,
        'volume': [1000 * (1 + 0.5 * np.random.random()) for _ in range(days)]
    }, index=dates)
    
    # Tạo allocator
    risk_allocator = AdaptiveRiskAllocator(base_risk=2.5)
    
    # Mô phỏng thống kê tài khoản
    account_stats = {
        'win_streak': 3,
        'lose_streak': 0,
        'current_drawdown': 5.0  # 5% drawdown
    }
    
    # Tính toán mức rủi ro thích ứng
    result = risk_allocator.calculate_adaptive_risk(df, account_stats, symbol='EXAMPLE')
    
    print(f"Chế độ thị trường: {result['regime']}")
    print(f"Mức rủi ro cơ sở: {result['base_risk']:.2f}%")
    print(f"Mức rủi ro cơ sở theo chế độ: {result['base_regime_risk']:.2f}%")
    print(f"Điều chỉnh theo tài khoản: {result['account_adjustment']:.2f}%")
    print(f"Mức rủi ro thích ứng cuối cùng: {result['adaptive_risk']:.2f}%")
    
    # Tính kích thước vị thế
    position_result = risk_allocator.calculate_position_size(
        account_balance=10000,
        entry_price=100,
        stop_loss_price=95,
        risk_percentage=result['adaptive_risk']
    )
    
    print("\nKích thước vị thế:")
    print(f"Số tiền rủi ro: ${position_result['risk_amount']:.2f}")
    print(f"Khoảng cách dừng lỗ: {position_result['stop_loss_distance_percent']:.2f}%")
    print(f"Kích thước vị thế (coins): {position_result['position_size_in_coins']:.6f}")
    print(f"Kích thước vị thế (USD): ${position_result['position_size_in_usd']:.2f}")
    print(f"Leverage cần thiết: {position_result['leverage_needed']:.2f}x")
    print(f"Leverage đề xuất: {position_result['suggested_leverage']}x")
    
    # Lấy đề xuất cho các mức rủi ro khác nhau
    for level in ['conservative', 'balanced', 'aggressive']:
        suggestion = risk_allocator.get_risk_suggestion('EXAMPLE', level)
        print(f"\nĐề xuất cho mức {level}:")
        print(f"Mức rủi ro đề xuất: {suggestion['suggested_risk_percentage']:.2f}%")
        print(f"Lý do: {suggestion['suggestion_reason']}")