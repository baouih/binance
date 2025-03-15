"""
Adaptive Exit Strategy - Chiến lược thoát lệnh thích ứng theo chế độ thị trường

Module này cung cấp các chiến lược thoát lệnh khác nhau tối ưu cho từng chế độ thị trường,
giúp tối đa hóa lợi nhuận và giảm thiểu rủi ro.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Tuple, Optional, Union, Any
import matplotlib.pyplot as plt
from collections import defaultdict

# Thêm các module tự tạo
from enhanced_market_regime_detector import EnhancedMarketRegimeDetector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('adaptive_exit_strategy')

class AdaptiveExitStrategy:
    """
    Cung cấp chiến lược thoát lệnh thích ứng dựa trên chế độ thị trường và các yếu tố khác.
    """
    
    # Các chiến lược thoát lệnh được hỗ trợ
    EXIT_STRATEGIES = [
        'trailing_stop',              # Trailing stop thông thường
        'enhanced_trailing_stop',     # Trailing stop nâng cao với tham số thích ứng
        'partial_take_profit',        # Chốt lời từng phần
        'time_based_exit',            # Thoát lệnh dựa trên thời gian
        'indicator_based_exit',       # Thoát lệnh dựa trên chỉ báo
        'multi_time_frame_exit',      # Thoát lệnh dựa trên nhiều khung thời gian
        'volume_profile_exit',        # Thoát lệnh dựa trên Volume Profile
        'order_flow_exit',            # Thoát lệnh dựa trên Order Flow
        'profit_maximizer',           # Tối đa hóa lợi nhuận (kết hợp nhiều chiến lược)
        'volatility_based_exit'       # Thoát lệnh dựa trên biến động
    ]
    
    # Mapping chiến lược thoát lệnh phù hợp cho từng chế độ thị trường
    REGIME_EXIT_STRATEGY_MAPPING = {
        'trending_bullish': ['enhanced_trailing_stop', 'partial_take_profit'],
        'trending_bearish': ['enhanced_trailing_stop', 'partial_take_profit'],
        'ranging_narrow': ['indicator_based_exit', 'volume_profile_exit'],
        'ranging_wide': ['partial_take_profit', 'volume_profile_exit'],
        'volatile_breakout': ['enhanced_trailing_stop', 'volatility_based_exit'],
        'quiet_accumulation': ['time_based_exit', 'indicator_based_exit'],
        'neutral': ['trailing_stop', 'indicator_based_exit']
    }
    
    # Trọng số mặc định cho từng chiến lược thoát lệnh theo chế độ
    STRATEGY_WEIGHTS = {
        'trending_bullish': {
            'enhanced_trailing_stop': 0.7,
            'partial_take_profit': 0.3
        },
        'trending_bearish': {
            'enhanced_trailing_stop': 0.7,
            'partial_take_profit': 0.3
        },
        'ranging_narrow': {
            'indicator_based_exit': 0.6,
            'volume_profile_exit': 0.4
        },
        'ranging_wide': {
            'partial_take_profit': 0.5,
            'volume_profile_exit': 0.5
        },
        'volatile_breakout': {
            'enhanced_trailing_stop': 0.6,
            'volatility_based_exit': 0.4
        },
        'quiet_accumulation': {
            'time_based_exit': 0.4,
            'indicator_based_exit': 0.6
        },
        'neutral': {
            'trailing_stop': 0.5,
            'indicator_based_exit': 0.5
        }
    }
    
    # Cấu hình mặc định cho từng chiến lược
    DEFAULT_STRATEGY_CONFIGS = {
        'trailing_stop': {
            'stop_percent': 1.0,         # % khoảng cách từ giá
            'activation_percent': 0.5,   # % lợi nhuận để kích hoạt
            'step_percent': 0.25,        # % dịch chuyển
            'tightening_factor': 1.0     # Hệ số thu hẹp khoảng cách khi lợi nhuận tăng
        },
        'enhanced_trailing_stop': {
            'initial_stop_percent': 1.5,        # % khoảng cách ban đầu
            'min_stop_percent': 0.5,            # % khoảng cách tối thiểu
            'profit_factor': 0.4,               # Hệ số lợi nhuận (0.4 = 40% lợi nhuận đạt được)
            'atr_factor': 2.0,                  # Hệ số ATR
            'volatility_adjustment': True,      # Điều chỉnh theo biến động
            'trend_following': True,            # Theo dõi xu hướng
            'acceleration_factor': 0.02,        # Hệ số tăng tốc (Parabolic SAR)
            'max_acceleration': 0.2             # Hệ số tăng tốc tối đa
        },
        'partial_take_profit': {
            'levels': [                          # Các mức chốt lời từng phần
                {'percent': 1.0, 'quantity': 0.25},   # Chốt 25% khi lời 1.0%
                {'percent': 2.0, 'quantity': 0.25},   # Chốt thêm 25% khi lời 2.0%
                {'percent': 3.0, 'quantity': 0.25},   # Chốt thêm 25% khi lời 3.0%
                {'percent': 5.0, 'quantity': 0.25}    # Chốt 25% còn lại khi lời 5.0%
            ],
            'stop_adjustment': True,           # Điều chỉnh stop loss sau mỗi lần chốt một phần
            'breakeven_after_first': True      # Đưa stop loss về hòa vốn sau lần chốt lời đầu
        },
        'time_based_exit': {
            'max_holding_time': 24,              # Thời gian tối đa giữ lệnh (giờ)
            'time_decay_start': 12,              # Bắt đầu giảm mục tiêu sau bao nhiêu giờ
            'decay_factor': 0.1,                 # Hệ số giảm mỗi giờ sau khi bắt đầu
            'off_hours_exit': True,              # Thoát lệnh trong giờ thị trường ít hoạt động
            'exit_on_weekend': True              # Thoát lệnh vào cuối tuần
        },
        'indicator_based_exit': {
            'indicators': [                    # Các chỉ báo dùng để thoát lệnh
                {
                    'name': 'rsi',
                    'exit_long_above': 75,     # Thoát lệnh Long khi RSI > 75
                    'exit_short_below': 25,    # Thoát lệnh Short khi RSI < 25
                    'weight': 0.3              # Trọng số cho chỉ báo này
                },
                {
                    'name': 'macd',
                    'exit_on_signal_cross': True,  # Thoát khi MACD cắt Signal
                    'weight': 0.3
                },
                {
                    'name': 'bbands',
                    'exit_long_upper': True,      # Thoát Long khi chạm BB trên
                    'exit_short_lower': True,     # Thoát Short khi chạm BB dưới
                    'weight': 0.4
                }
            ],
            'use_confirmation': True,           # Yêu cầu xác nhận từ nhiều chỉ báo
            'confirmation_threshold': 0.6       # Ngưỡng xác nhận (trọng số tổng cộng)
        },
        'multi_time_frame_exit': {
            'timeframes': ['1m', '5m', '15m', '1h'],  # Các khung thời gian cần kiểm tra
            'exit_on_higher_tf': True,          # Thoát nếu có tín hiệu ở khung thời gian cao hơn
            'tf_weights': [0.1, 0.2, 0.3, 0.4], # Trọng số cho mỗi khung thời gian
            'confirmation_threshold': 0.5       # Ngưỡng xác nhận
        },
        'volume_profile_exit': {
            'use_poc_as_target': True,        # Sử dụng POC làm mục tiêu
            'use_va_boundaries': True,        # Sử dụng biên Value Area làm mức thoát
            'va_high_exit_for_long': True,    # Thoát Long ở VA High
            'va_low_exit_for_short': True,    # Thoát Short ở VA Low
            'volume_climax_exit': True,       # Thoát khi có Volume Climax (tăng đột biến)
            'respect_vwap': True,             # Sử dụng VWAP làm mốc tham chiếu
            'lookback_periods': 50            # Số chu kỳ nhìn lại để tính Volume Profile
        },
        'order_flow_exit': {
            'use_delta_reversal': True,      # Thoát khi Delta đảo chiều
            'delta_threshold': 0.7,          # Ngưỡng Delta
            'use_imbalance': True,           # Sử dụng chỉ số mất cân bằng
            'imbalance_threshold': 0.8,      # Ngưỡng mất cân bằng
            'respect_liquidity': True,       # Tôn trọng rào cản thanh khoản
            'confirm_with_price': True       # Xác nhận với biến động giá
        },
        'profit_maximizer': {
            'enable_trailing': True,            # Sử dụng trailing
            'enable_partial_tp': True,          # Sử dụng chốt lời từng phần
            'use_indicators': True,             # Sử dụng chỉ báo
            'aggressive_scale_out': False,      # Chốt lời mạnh tay
            'safety_first': True,               # Ưu tiên bảo toàn lợi nhuận
            'dynamic_adjustment': True,         # Điều chỉnh động theo thị trường
            'risk_reward_target': 3.0           # Mục tiêu tỷ lệ lợi nhuận/rủi ro
        },
        'volatility_based_exit': {
            'atr_factor': 2.5,               # Hệ số ATR cho stop loss
            'use_bbands': True,              # Sử dụng Bollinger Bands
            'bbands_period': 20,             # Chu kỳ BB
            'bbands_dev': 2.0,               # Số độ lệch chuẩn BB
            'exit_on_volatility_spike': True, # Thoát khi biến động tăng đột biến
            'volatility_spike_factor': 2.0,  # Hệ số tăng biến động
            'adjust_to_market_state': True   # Điều chỉnh theo trạng thái thị trường
        }
    }
    
    def __init__(self, data_storage_path: str = 'data/exit_strategies'):
        """
        Khởi tạo Adaptive Exit Strategy.
        
        Args:
            data_storage_path (str): Đường dẫn lưu trữ dữ liệu và cấu hình
        """
        self.data_storage_path = data_storage_path
        
        # Tạo thư mục lưu trữ nếu chưa tồn tại
        os.makedirs(data_storage_path, exist_ok=True)
        
        # Khởi tạo detector chế độ thị trường
        self.regime_detector = EnhancedMarketRegimeDetector()
        
        # Cấu hình cho từng chiến lược thoát lệnh
        self.strategy_configs = self.DEFAULT_STRATEGY_CONFIGS.copy()
        
        # Cấu hình active
        self.active_config = {}
        
        # Trạng thái
        self.current_regime = "neutral"
        self.active_strategies = []
        self.positions = {}
        self.exit_signals = []
        
        # Lịch sử thoát lệnh
        self.exit_history = []
        
        # Tải cấu hình nếu có
        self._load_config()
    
    def determine_exit_strategy(self, market_data: pd.DataFrame, position_data: Dict, 
                              override_regime: str = None) -> Dict:
        """
        Xác định chiến lược thoát lệnh tối ưu cho vị thế hiện tại.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            override_regime (str, optional): Ghi đè chế độ thị trường
            
        Returns:
            Dict: Chiến lược thoát lệnh được đề xuất
        """
        try:
            # Xác định chế độ thị trường
            if override_regime:
                self.current_regime = override_regime
            else:
                # Phát hiện chế độ thị trường từ dữ liệu
                regime_result = self.regime_detector.detect_regime(market_data)
                self.current_regime = regime_result['regime']
            
            # Lấy các chiến lược phù hợp cho chế độ thị trường hiện tại
            suitable_strategies = self.REGIME_EXIT_STRATEGY_MAPPING.get(
                self.current_regime, ['trailing_stop', 'indicator_based_exit']
            )
            
            # Lưu trữ các chiến lược active
            self.active_strategies = suitable_strategies
            
            # Tính điểm cho từng chiến lược
            strategy_scores = {}
            
            for strategy in suitable_strategies:
                # Lấy trọng số mặc định
                default_weight = self.STRATEGY_WEIGHTS.get(self.current_regime, {}).get(strategy, 0.5)
                
                # Tính điểm dựa trên trọng số và độ phù hợp với thị trường hiện tại
                score = default_weight
                
                # Thêm điều chỉnh dựa trên trạng thái vị thế
                if position_data:
                    # Điều chỉnh dựa trên thời gian giữ lệnh
                    if 'holding_time' in position_data:
                        holding_time = position_data['holding_time']
                        
                        # Ưu tiên time_based_exit cho lệnh giữ lâu
                        if holding_time > 12 and strategy == 'time_based_exit':
                            score += 0.2
                        
                        # Ưu tiên trailing_stop cho lệnh mới
                        if holding_time < 1 and strategy == 'trailing_stop':
                            score += 0.1
                    
                    # Điều chỉnh dựa trên lợi nhuận
                    if 'unrealized_pnl_pct' in position_data:
                        pnl_pct = position_data['unrealized_pnl_pct']
                        
                        # Ưu tiên partial_take_profit khi có lợi nhuận tốt
                        if pnl_pct > 2.0 and strategy == 'partial_take_profit':
                            score += 0.2
                        
                        # Ưu tiên trailing_stop khi lợi nhuận đang tăng
                        if pnl_pct > 1.0 and 'prev_pnl_pct' in position_data:
                            prev_pnl = position_data['prev_pnl_pct']
                            if pnl_pct > prev_pnl and strategy in ['trailing_stop', 'enhanced_trailing_stop']:
                                score += 0.15
                
                # Thêm điều chỉnh dựa trên biến động thị trường
                if 'Price_Volatility' in market_data.columns:
                    volatility = market_data['Price_Volatility'].iloc[-1]
                    avg_volatility = market_data['Price_Volatility'].mean()
                    
                    # Ưu tiên volatility_based_exit khi biến động cao
                    if volatility > avg_volatility * 1.5 and strategy == 'volatility_based_exit':
                        score += 0.2
                        
                    # Ưu tiên các chiến lược ổn định khi biến động thấp
                    if volatility < avg_volatility * 0.7 and strategy in ['indicator_based_exit', 'time_based_exit']:
                        score += 0.1
                
                # Thêm điều chỉnh dựa trên data Order Flow và Volume Profile nếu có
                if 'Order_Flow_Signal' in market_data.columns and strategy == 'order_flow_exit':
                    score += 0.1
                
                if 'BB_Width' in market_data.columns and strategy == 'indicator_based_exit':
                    # Ưu tiên indicator_based_exit khi BB đang co hẹp (thị trường tích lũy)
                    bb_width = market_data['BB_Width'].iloc[-1]
                    avg_bb_width = market_data['BB_Width'].mean()
                    
                    if bb_width < avg_bb_width * 0.8:
                        score += 0.1
                
                # Lưu điểm
                strategy_scores[strategy] = score
            
            # Chuẩn hóa điểm
            total_score = sum(strategy_scores.values())
            if total_score > 0:
                for strategy in strategy_scores:
                    strategy_scores[strategy] /= total_score
            
            # Tạo cấu hình dựa trên các chiến lược đã chọn
            exit_config = self._create_exit_config(suitable_strategies, strategy_scores)
            
            # Lưu cấu hình active
            self.active_config = exit_config
            
            # Tạo kết quả
            result = {
                'regime': self.current_regime,
                'active_strategies': suitable_strategies,
                'strategy_scores': strategy_scores,
                'exit_config': exit_config,
                'position_type': position_data.get('position_type', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Lưu lại
            self._add_to_history(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi xác định chiến lược thoát lệnh: {str(e)}")
            # Trả về chiến lược mặc định nếu có lỗi
            return {
                'regime': 'unknown',
                'active_strategies': ['trailing_stop'],
                'strategy_scores': {'trailing_stop': 1.0},
                'exit_config': self.DEFAULT_STRATEGY_CONFIGS['trailing_stop'],
                'position_type': position_data.get('position_type', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def calculate_exit_points(self, market_data: pd.DataFrame, position_data: Dict, 
                            exit_strategy: Dict = None) -> Dict:
        """
        Tính toán các điểm thoát lệnh dựa trên chiến lược đã chọn.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            exit_strategy (Dict, optional): Thông tin chiến lược thoát, nếu None sẽ sử dụng active_config
            
        Returns:
            Dict: Các điểm thoát lệnh
        """
        try:
            # Sử dụng active_config nếu không có exit_strategy
            strategy_config = exit_strategy['exit_config'] if exit_strategy else self.active_config
            
            # Lấy thông tin vị thế
            position_type = position_data.get('position_type', 'long')  # Mặc định là long
            entry_price = position_data.get('entry_price', 0)
            current_price = position_data.get('current_price', market_data['close'].iloc[-1])
            unrealized_pnl_pct = position_data.get('unrealized_pnl_pct', 0)
            
            # Tính toán các điểm thoát dựa trên các chiến lược active
            exit_points = {
                'stop_loss': None,
                'take_profit': None,
                'trailing_stop': None,
                'partial_take_profits': [],
                'indicator_exits': [],
                'time_based_exit': None,
                'final_exit_price': None,
                'exit_reason': '',
                'confidence': 0.0
            }
            
            # Tính các điểm exit theo từng chiến lược
            if 'trailing_stop' in self.active_strategies or 'enhanced_trailing_stop' in self.active_strategies:
                trailing_stop = self._calculate_trailing_stop(market_data, position_data, strategy_config)
                exit_points['trailing_stop'] = trailing_stop
            
            if 'partial_take_profit' in self.active_strategies:
                partial_tps = self._calculate_partial_take_profits(market_data, position_data, strategy_config)
                exit_points['partial_take_profits'] = partial_tps
            
            if 'indicator_based_exit' in self.active_strategies:
                indicator_exits = self._calculate_indicator_exits(market_data, position_data, strategy_config)
                exit_points['indicator_exits'] = indicator_exits
            
            if 'time_based_exit' in self.active_strategies:
                time_exit = self._calculate_time_based_exit(market_data, position_data, strategy_config)
                exit_points['time_based_exit'] = time_exit
            
            if 'volume_profile_exit' in self.active_strategies:
                volume_exits = self._calculate_volume_profile_exits(market_data, position_data, strategy_config)
                if 'volume_exits' not in exit_points:
                    exit_points['volume_exits'] = []
                exit_points['volume_exits'].extend(volume_exits)
            
            if 'order_flow_exit' in self.active_strategies:
                order_flow_exits = self._calculate_order_flow_exits(market_data, position_data, strategy_config)
                if 'order_flow_exits' not in exit_points:
                    exit_points['order_flow_exits'] = []
                exit_points['order_flow_exits'].extend(order_flow_exits)
            
            if 'volatility_based_exit' in self.active_strategies:
                volatility_exits = self._calculate_volatility_exits(market_data, position_data, strategy_config)
                if 'volatility_exits' not in exit_points:
                    exit_points['volatility_exits'] = []
                exit_points['volatility_exits'].extend(volatility_exits)
            
            # Đặc biệt, xử lý profit_maximizer nếu có
            if 'profit_maximizer' in self.active_strategies:
                maximizer_exits = self._calculate_profit_maximizer_exits(market_data, position_data, strategy_config, exit_points)
                exit_points.update(maximizer_exits)
            
            # Xác định stop loss chính
            stop_candidates = []
            if exit_points['trailing_stop']:
                stop_candidates.append((exit_points['trailing_stop']['price'], 'trailing_stop', exit_points['trailing_stop']['confidence']))
            
            for exit_point in exit_points.get('indicator_exits', []):
                if exit_point['type'] == 'stop_loss':
                    stop_candidates.append((exit_point['price'], 'indicator', exit_point['confidence']))
            
            for exit_point in exit_points.get('volatility_exits', []):
                if exit_point['type'] == 'stop_loss':
                    stop_candidates.append((exit_point['price'], 'volatility', exit_point['confidence']))
            
            # Lọc và chọn stop loss phù hợp
            valid_stop_candidates = []
            if position_type == 'long':
                # Stop loss cho long position phải nhỏ hơn giá hiện tại
                valid_stop_candidates = [(price, source, conf) for price, source, conf in stop_candidates if price < current_price]
            else:
                # Stop loss cho short position phải lớn hơn giá hiện tại
                valid_stop_candidates = [(price, source, conf) for price, source, conf in stop_candidates if price > current_price]
            
            if valid_stop_candidates:
                # Chọn stop loss dựa trên sự kết hợp giữa confidence và khoảng cách
                chosen_stop = None
                best_score = -float('inf')
                
                for price, source, conf in valid_stop_candidates:
                    # Tính điểm dựa trên khoảng cách và confidence
                    distance_pct = abs(price - current_price) / current_price
                    
                    # Khoảng cách quá gần không tốt, khoảng cách quá xa cũng không tốt
                    distance_score = 0
                    if distance_pct < 0.005:  # Dưới 0.5%
                        distance_score = distance_pct / 0.005  # 0 - 1.0
                    elif distance_pct < 0.02:  # 0.5% - 2%
                        distance_score = 1.0
                    else:  # Trên 2%
                        distance_score = 1.0 - min(1.0, (distance_pct - 0.02) / 0.03)  # 1.0 - 0
                    
                    score = conf * 0.7 + distance_score * 0.3
                    
                    if score > best_score:
                        best_score = score
                        chosen_stop = (price, source, conf)
                
                if chosen_stop:
                    exit_points['stop_loss'] = {
                        'price': chosen_stop[0],
                        'source': chosen_stop[1],
                        'confidence': chosen_stop[2]
                    }
            
            # Xác định take profit chính
            take_profit_candidates = []
            for tp in exit_points.get('partial_take_profits', []):
                take_profit_candidates.append((tp['price'], 'partial_tp', tp['confidence']))
            
            for exit_point in exit_points.get('indicator_exits', []):
                if exit_point['type'] == 'take_profit':
                    take_profit_candidates.append((exit_point['price'], 'indicator', exit_point['confidence']))
            
            for exit_point in exit_points.get('volume_exits', []):
                if exit_point['type'] == 'take_profit':
                    take_profit_candidates.append((exit_point['price'], 'volume_profile', exit_point['confidence']))
            
            # Lọc và chọn take profit phù hợp
            valid_tp_candidates = []
            if position_type == 'long':
                # Take profit cho long position phải lớn hơn giá hiện tại
                valid_tp_candidates = [(price, source, conf) for price, source, conf in take_profit_candidates if price > current_price]
            else:
                # Take profit cho short position phải nhỏ hơn giá hiện tại
                valid_tp_candidates = [(price, source, conf) for price, source, conf in take_profit_candidates if price < current_price]
            
            if valid_tp_candidates:
                # Chọn take profit đầu tiên (gần nhất)
                if position_type == 'long':
                    nearest_tp = min(valid_tp_candidates, key=lambda x: x[0])
                else:
                    nearest_tp = max(valid_tp_candidates, key=lambda x: x[0])
                
                exit_points['take_profit'] = {
                    'price': nearest_tp[0],
                    'source': nearest_tp[1],
                    'confidence': nearest_tp[2]
                }
            
            # Xác định điểm exit cuối cùng dựa trên giá hiện tại
            if current_price and position_type:
                if position_type == 'long':
                    # Long position: stop loss dưới giá hiện tại
                    if exit_points['stop_loss'] and current_price <= exit_points['stop_loss']['price']:
                        exit_points['final_exit_price'] = exit_points['stop_loss']['price']
                        exit_points['exit_reason'] = f"Stop loss ({exit_points['stop_loss']['source']})"
                        exit_points['confidence'] = exit_points['stop_loss']['confidence']
                        
                    # Long position: take profit trên giá hiện tại
                    elif exit_points['take_profit'] and current_price >= exit_points['take_profit']['price']:
                        exit_points['final_exit_price'] = exit_points['take_profit']['price']
                        exit_points['exit_reason'] = f"Take profit ({exit_points['take_profit']['source']})"
                        exit_points['confidence'] = exit_points['take_profit']['confidence']
                
                else:  # Short position
                    # Short position: stop loss trên giá hiện tại
                    if exit_points['stop_loss'] and current_price >= exit_points['stop_loss']['price']:
                        exit_points['final_exit_price'] = exit_points['stop_loss']['price']
                        exit_points['exit_reason'] = f"Stop loss ({exit_points['stop_loss']['source']})"
                        exit_points['confidence'] = exit_points['stop_loss']['confidence']
                        
                    # Short position: take profit dưới giá hiện tại
                    elif exit_points['take_profit'] and current_price <= exit_points['take_profit']['price']:
                        exit_points['final_exit_price'] = exit_points['take_profit']['price']
                        exit_points['exit_reason'] = f"Take profit ({exit_points['take_profit']['source']})"
                        exit_points['confidence'] = exit_points['take_profit']['confidence']
            
            # Thêm thông tin tính toán
            exit_points['position_type'] = position_type
            exit_points['entry_price'] = entry_price
            exit_points['current_price'] = current_price
            exit_points['regime'] = self.current_regime
            exit_points['timestamp'] = datetime.now().isoformat()
            
            # Tính risk-reward ratio
            if exit_points['stop_loss'] and exit_points['take_profit']:
                if position_type == 'long':
                    risk = entry_price - exit_points['stop_loss']['price']
                    reward = exit_points['take_profit']['price'] - entry_price
                else:
                    risk = exit_points['stop_loss']['price'] - entry_price
                    reward = entry_price - exit_points['take_profit']['price']
                
                if risk > 0:
                    exit_points['risk_reward_ratio'] = reward / risk
                else:
                    exit_points['risk_reward_ratio'] = float('inf')
            
            return exit_points
            
        except Exception as e:
            logger.error(f"Lỗi khi tính toán điểm thoát lệnh: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Trả về điểm thoát đơn giản nếu có lỗi
            return {
                'stop_loss': None,
                'take_profit': None,
                'trailing_stop': None,
                'final_exit_price': None,
                'exit_reason': 'Error calculating exit points',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_exit_signal(self, market_data: pd.DataFrame, position_data: Dict) -> Dict:
        """
        Lấy tín hiệu thoát lệnh dựa trên điều kiện thị trường và vị thế.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            
        Returns:
            Dict: Tín hiệu thoát lệnh
        """
        try:
            # Xác định chiến lược thoát lệnh
            strategy = self.determine_exit_strategy(market_data, position_data)
            
            # Tính toán các điểm thoát
            exit_points = self.calculate_exit_points(market_data, position_data, strategy)
            
            # Xác định tín hiệu thoát lệnh
            position_type = position_data.get('position_type', 'long')
            current_price = position_data.get('current_price', market_data['close'].iloc[-1])
            
            # Tham chiếu cho các mức giá
            if position_type == 'long':
                # Kiểm tra stop loss (long)
                if exit_points['stop_loss'] and current_price <= exit_points['stop_loss']['price']:
                    signal = {
                        'exit_signal': True,
                        'exit_type': 'stop_loss',
                        'exit_price': exit_points['stop_loss']['price'],
                        'exit_reason': f"Stop loss ({exit_points['stop_loss']['source']})",
                        'confidence': exit_points['stop_loss']['confidence']
                    }
                # Kiểm tra take profit (long)
                elif exit_points['take_profit'] and current_price >= exit_points['take_profit']['price']:
                    signal = {
                        'exit_signal': True,
                        'exit_type': 'take_profit',
                        'exit_price': exit_points['take_profit']['price'],
                        'exit_reason': f"Take profit ({exit_points['take_profit']['source']})",
                        'confidence': exit_points['take_profit']['confidence']
                    }
                # Kiểm tra các partial take profit
                elif exit_points.get('partial_take_profits'):
                    for tp in exit_points['partial_take_profits']:
                        if current_price >= tp['price'] and not tp.get('executed', False):
                            signal = {
                                'exit_signal': True,
                                'exit_type': 'partial_take_profit',
                                'exit_price': tp['price'],
                                'exit_percentage': tp['quantity'],
                                'exit_reason': f"Partial take profit at {tp['percent']}%",
                                'confidence': tp['confidence']
                            }
                            break
                    else:
                        signal = {
                            'exit_signal': False,
                            'exit_type': None,
                            'exit_price': None,
                            'exit_reason': "No exit signal",
                            'confidence': 0.0
                        }
                else:
                    signal = {
                        'exit_signal': False,
                        'exit_type': None,
                        'exit_price': None,
                        'exit_reason': "No exit signal",
                        'confidence': 0.0
                    }
            else:  # short position
                # Kiểm tra stop loss (short)
                if exit_points['stop_loss'] and current_price >= exit_points['stop_loss']['price']:
                    signal = {
                        'exit_signal': True,
                        'exit_type': 'stop_loss',
                        'exit_price': exit_points['stop_loss']['price'],
                        'exit_reason': f"Stop loss ({exit_points['stop_loss']['source']})",
                        'confidence': exit_points['stop_loss']['confidence']
                    }
                # Kiểm tra take profit (short)
                elif exit_points['take_profit'] and current_price <= exit_points['take_profit']['price']:
                    signal = {
                        'exit_signal': True,
                        'exit_type': 'take_profit',
                        'exit_price': exit_points['take_profit']['price'],
                        'exit_reason': f"Take profit ({exit_points['take_profit']['source']})",
                        'confidence': exit_points['take_profit']['confidence']
                    }
                # Kiểm tra các partial take profit
                elif exit_points.get('partial_take_profits'):
                    for tp in exit_points['partial_take_profits']:
                        if current_price <= tp['price'] and not tp.get('executed', False):
                            signal = {
                                'exit_signal': True,
                                'exit_type': 'partial_take_profit',
                                'exit_price': tp['price'],
                                'exit_percentage': tp['quantity'],
                                'exit_reason': f"Partial take profit at {tp['percent']}%",
                                'confidence': tp['confidence']
                            }
                            break
                    else:
                        signal = {
                            'exit_signal': False,
                            'exit_type': None,
                            'exit_price': None,
                            'exit_reason': "No exit signal",
                            'confidence': 0.0
                        }
                else:
                    signal = {
                        'exit_signal': False,
                        'exit_type': None,
                        'exit_price': None,
                        'exit_reason': "No exit signal",
                        'confidence': 0.0
                    }
            
            # Thêm thông tin
            signal['position_type'] = position_type
            signal['current_price'] = current_price
            signal['regime'] = self.current_regime
            signal['timestamp'] = datetime.now().isoformat()
            signal['strategy'] = strategy['active_strategies']
            
            # Lưu vào lịch sử
            self.exit_signals.append(signal)
            
            # Giới hạn kích thước
            if len(self.exit_signals) > 1000:
                self.exit_signals = self.exit_signals[-1000:]
            
            return signal
            
        except Exception as e:
            logger.error(f"Lỗi khi lấy tín hiệu thoát lệnh: {str(e)}")
            # Trả về tín hiệu mặc định nếu có lỗi
            return {
                'exit_signal': False,
                'exit_type': None,
                'exit_price': None,
                'exit_reason': f"Error: {str(e)}",
                'position_type': position_data.get('position_type', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'confidence': 0.0,
                'error': str(e)
            }
    
    def visualize_exit_points(self, market_data: pd.DataFrame, position_data: Dict, 
                           exit_points: Dict, output_path: Optional[str] = None) -> str:
        """
        Tạo biểu đồ các điểm thoát lệnh.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            exit_points (Dict): Thông tin về các điểm thoát lệnh
            output_path (str, optional): Đường dẫn lưu biểu đồ
            
        Returns:
            str: Đường dẫn đến biểu đồ
        """
        try:
            # Lấy dữ liệu gần đây
            recent_data = market_data.iloc[-50:].copy() if len(market_data) > 50 else market_data.copy()
            
            # Tạo biểu đồ
            plt.figure(figsize=(12, 8))
            
            # Vẽ biểu đồ giá
            plt.subplot(2, 1, 1)
            plt.plot(recent_data.index, recent_data['close'], color='black', linewidth=1.5)
            plt.title('Price Chart with Exit Points')
            plt.ylabel('Price')
            plt.grid(True, alpha=0.3)
            
            # Thêm entry price
            entry_price = position_data.get('entry_price')
            if entry_price:
                plt.axhline(y=entry_price, color='blue', linestyle='--', linewidth=1.5, label=f'Entry: {entry_price:.2f}')
            
            # Thêm stop loss
            stop_loss = exit_points.get('stop_loss')
            if stop_loss:
                plt.axhline(y=stop_loss['price'], color='red', linestyle='--', linewidth=1.5, 
                          label=f"Stop Loss: {stop_loss['price']:.2f} ({stop_loss['source']})")
            
            # Thêm take profit
            take_profit = exit_points.get('take_profit')
            if take_profit:
                plt.axhline(y=take_profit['price'], color='green', linestyle='--', linewidth=1.5, 
                          label=f"Take Profit: {take_profit['price']:.2f} ({take_profit['source']})")
            
            # Thêm trailing stop
            trailing_stop = exit_points.get('trailing_stop')
            if trailing_stop:
                plt.axhline(y=trailing_stop['price'], color='orange', linestyle='--', linewidth=1.5, 
                          label=f"Trailing Stop: {trailing_stop['price']:.2f}")
            
            # Thêm partial take profits
            partial_tps = exit_points.get('partial_take_profits', [])
            for i, tp in enumerate(partial_tps):
                plt.axhline(y=tp['price'], color='lightgreen', linestyle='-.', linewidth=1, 
                          label=f"Partial TP {i+1}: {tp['price']:.2f} ({tp['quantity']*100:.0f}%)")
            
            # Thêm legend
            plt.legend()
            
            # Vẽ biểu đồ tín hiệu thoát
            plt.subplot(2, 1, 2)
            
            # Vẽ các tín hiệu thoát từ indicator
            indicator_exits = exit_points.get('indicator_exits', [])
            exit_signals = []
            exit_confidences = []
            
            for i, exit_point in enumerate(indicator_exits):
                exit_signals.append(i)
                exit_confidences.append(exit_point['confidence'])
            
            if exit_signals:
                plt.bar(exit_signals, exit_confidences, color='purple', alpha=0.7)
                plt.xticks(exit_signals, [f"{exit_point['type']} ({exit_point['source']})" for exit_point in indicator_exits], rotation=45)
            
            plt.title('Exit Signal Confidence')
            plt.ylabel('Confidence')
            plt.ylim(0, 1.1)
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            if output_path is None:
                output_path = os.path.join(self.data_storage_path, 'exit_points_chart.png')
            
            plt.savefig(output_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ các điểm thoát lệnh tại: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ các điểm thoát lệnh: {str(e)}")
            return "Error creating chart"
    
    def update_strategy_config(self, strategy_name: str, config_updates: Dict) -> None:
        """
        Cập nhật cấu hình cho một chiến lược thoát lệnh cụ thể.
        
        Args:
            strategy_name (str): Tên chiến lược
            config_updates (Dict): Các cập nhật cấu hình
        """
        if strategy_name in self.strategy_configs:
            # Cập nhật các tham số
            self.strategy_configs[strategy_name].update(config_updates)
            logger.info(f"Đã cập nhật cấu hình cho chiến lược {strategy_name}")
            
            # Lưu cấu hình
            self._save_config()
        else:
            logger.warning(f"Chiến lược {strategy_name} không tồn tại")
    
    def update_regime_strategy_mapping(self, regime: str, strategies: List[str]) -> None:
        """
        Cập nhật mapping chiến lược thoát lệnh cho một chế độ thị trường.
        
        Args:
            regime (str): Tên chế độ thị trường
            strategies (List[str]): Danh sách chiến lược thoát lệnh
        """
        # Kiểm tra các chiến lược có hợp lệ không
        invalid_strategies = [s for s in strategies if s not in self.EXIT_STRATEGIES]
        if invalid_strategies:
            logger.warning(f"Các chiến lược không hợp lệ: {invalid_strategies}")
            return
        
        # Cập nhật mapping
        self.REGIME_EXIT_STRATEGY_MAPPING[regime] = strategies
        logger.info(f"Đã cập nhật mapping chiến lược cho chế độ {regime}: {strategies}")
        
        # Lưu cấu hình
        self._save_config()
    
    def update_strategy_weights(self, regime: str, strategy_weights: Dict[str, float]) -> None:
        """
        Cập nhật trọng số chiến lược thoát lệnh cho một chế độ thị trường.
        
        Args:
            regime (str): Tên chế độ thị trường
            strategy_weights (Dict[str, float]): Trọng số cho từng chiến lược
        """
        # Kiểm tra các chiến lược có hợp lệ không
        invalid_strategies = [s for s in strategy_weights.keys() if s not in self.EXIT_STRATEGIES]
        if invalid_strategies:
            logger.warning(f"Các chiến lược không hợp lệ: {invalid_strategies}")
            return
        
        # Cập nhật trọng số
        if regime not in self.STRATEGY_WEIGHTS:
            self.STRATEGY_WEIGHTS[regime] = {}
        
        self.STRATEGY_WEIGHTS[regime].update(strategy_weights)
        logger.info(f"Đã cập nhật trọng số chiến lược cho chế độ {regime}")
        
        # Lưu cấu hình
        self._save_config()
    
    def _calculate_trailing_stop(self, market_data: pd.DataFrame, position_data: Dict, 
                                strategy_config: Dict) -> Dict:
        """
        Tính toán trailing stop.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            Dict: Thông tin về trailing stop
        """
        position_type = position_data.get('position_type', 'long')
        entry_price = position_data.get('entry_price', 0)
        current_price = position_data.get('current_price', market_data['close'].iloc[-1])
        unrealized_pnl_pct = position_data.get('unrealized_pnl_pct', 0)
        
        # Lấy cấu hình
        if 'enhanced_trailing_stop' in strategy_config:
            config = strategy_config['enhanced_trailing_stop']
            enhanced = True
        elif 'trailing_stop' in strategy_config:
            config = strategy_config['trailing_stop']
            enhanced = False
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['trailing_stop']
            enhanced = False
        
        # Tính trailing stop
        if enhanced:
            # Enhanced Trailing Stop
            initial_stop_percent = config.get('initial_stop_percent', 1.5)
            min_stop_percent = config.get('min_stop_percent', 0.5)
            profit_factor = config.get('profit_factor', 0.4)
            atr_factor = config.get('atr_factor', 2.0)
            
            # Sử dụng ATR nếu có
            if 'ATR' in market_data.columns:
                atr = market_data['ATR'].iloc[-1]
            else:
                atr = (market_data['high'] - market_data['low']).mean() * 0.5
            
            # Tính stop ban đầu
            if position_type == 'long':
                initial_stop = entry_price * (1 - initial_stop_percent / 100)
                
                # Tính trailing stop dựa trên profit
                if unrealized_pnl_pct > 0:
                    # Trail theo % lợi nhuận đạt được
                    trailing_amount = unrealized_pnl_pct * profit_factor
                    trailing_amount = max(min_stop_percent, trailing_amount)
                    
                    # Stop dựa trên trailing
                    trailing_stop = current_price * (1 - trailing_amount / 100)
                    
                    # Stop dựa trên ATR
                    atr_stop = current_price - atr * atr_factor
                    
                    # Chọn stop cao nhất
                    stop_price = max(initial_stop, trailing_stop, atr_stop)
                else:
                    # Chưa có lợi nhuận, sử dụng stop ban đầu
                    stop_price = initial_stop
            else:
                initial_stop = entry_price * (1 + initial_stop_percent / 100)
                
                # Tính trailing stop dựa trên profit
                if unrealized_pnl_pct > 0:
                    # Trail theo % lợi nhuận đạt được
                    trailing_amount = unrealized_pnl_pct * profit_factor
                    trailing_amount = max(min_stop_percent, trailing_amount)
                    
                    # Stop dựa trên trailing
                    trailing_stop = current_price * (1 + trailing_amount / 100)
                    
                    # Stop dựa trên ATR
                    atr_stop = current_price + atr * atr_factor
                    
                    # Chọn stop thấp nhất
                    stop_price = min(initial_stop, trailing_stop, atr_stop)
                else:
                    # Chưa có lợi nhuận, sử dụng stop ban đầu
                    stop_price = initial_stop
        else:
            # Simple Trailing Stop
            stop_percent = config.get('stop_percent', 1.0)
            activation_percent = config.get('activation_percent', 0.5)
            step_percent = config.get('step_percent', 0.25)
            tightening_factor = config.get('tightening_factor', 1.0)
            
            if position_type == 'long':
                # Stop ban đầu
                initial_stop = entry_price * (1 - stop_percent / 100)
                
                # Chỉ trail nếu đạt mức kích hoạt
                if unrealized_pnl_pct >= activation_percent:
                    # Tính số bước trail
                    steps = int((unrealized_pnl_pct - activation_percent) / step_percent)
                    
                    # Tính stop mới
                    if steps > 0:
                        # Khoảng cách trailing giảm dần theo tightening_factor
                        trailing_distance = stop_percent * tightening_factor / (1 + 0.1 * steps)
                        
                        # Stop mới
                        new_stop = current_price * (1 - trailing_distance / 100)
                        
                        # Chọn stop cao nhất
                        stop_price = max(initial_stop, new_stop)
                    else:
                        stop_price = initial_stop
                else:
                    stop_price = initial_stop
            else:
                # Stop ban đầu
                initial_stop = entry_price * (1 + stop_percent / 100)
                
                # Chỉ trail nếu đạt mức kích hoạt
                if unrealized_pnl_pct >= activation_percent:
                    # Tính số bước trail
                    steps = int((unrealized_pnl_pct - activation_percent) / step_percent)
                    
                    # Tính stop mới
                    if steps > 0:
                        # Khoảng cách trailing giảm dần theo tightening_factor
                        trailing_distance = stop_percent * tightening_factor / (1 + 0.1 * steps)
                        
                        # Stop mới
                        new_stop = current_price * (1 + trailing_distance / 100)
                        
                        # Chọn stop thấp nhất
                        stop_price = min(initial_stop, new_stop)
                    else:
                        stop_price = initial_stop
                else:
                    stop_price = initial_stop
        
        # Tính độ tin cậy của stop
        if unrealized_pnl_pct > 0:
            # Độ tin cậy tăng dần theo lợi nhuận
            confidence = min(0.9, 0.5 + unrealized_pnl_pct / 10)
        else:
            # Độ tin cậy cơ bản cho stop ban đầu
            confidence = 0.5
        
        return {
            'price': stop_price,
            'type': 'trailing_stop',
            'initial_stop': initial_stop if enhanced else stop_price,
            'confidence': confidence,
            'enhanced': enhanced
        }
    
    def _calculate_partial_take_profits(self, market_data: pd.DataFrame, position_data: Dict, 
                                      strategy_config: Dict) -> List[Dict]:
        """
        Tính toán các điểm chốt lời từng phần dựa trên cấu hình từ risk_manager.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            List[Dict]: Danh sách các điểm chốt lời từng phần
        """
        position_type = position_data.get('position_type', 'long').upper()
        entry_price = position_data.get('entry_price', 0)
        
        # Lấy cấu hình
        tp_config = None
        
        # Ưu tiên cấu hình từ risk_manager nếu có
        if hasattr(self, 'risk_manager') and self.risk_manager:
            risk_config = self.risk_manager.get_risk_config()
            if risk_config and 'partial_take_profit' in risk_config:
                ptp_config = risk_config['partial_take_profit']
                if ptp_config.get('enabled', False):
                    tp_config = ptp_config
                    logger.info("Sử dụng cấu hình partial take profit từ risk_manager")
        
        # Nếu không có cấu hình từ risk_manager, sử dụng từ strategy_config
        if not tp_config and 'partial_take_profit' in strategy_config:
            tp_config = strategy_config['partial_take_profit']
            logger.info("Sử dụng cấu hình partial take profit từ strategy_config")
        
        # Nếu không có cả 2, sử dụng mặc định
        if not tp_config:
            tp_config = self.DEFAULT_STRATEGY_CONFIGS['partial_take_profit']
            logger.info("Sử dụng cấu hình partial take profit mặc định")
        
        # Xem cấu trúc của tp_config để có xử lý phù hợp
        levels = []
        if 'levels' in tp_config:
            levels = tp_config['levels']
        
        if not levels:
            logger.warning("Không tìm thấy cấu hình levels cho partial take profit")
            return []
        
        logger.info(f"Đã tìm thấy {len(levels)} mức chốt lời từng phần")
        
        # Tính các mức chốt lời
        partial_tps = []
        total_position = 1.0  # 100% vị thế
        remaining_position = total_position
        
        for level in levels:
            # Xử lý các cấu trúc khác nhau
            percent = level.get('percent', level.get('profit_percentage', 0))
            quantity_percent = level.get('quantity', level.get('percentage', 0)) / 100
            
            # Đảm bảo số lượng hợp lệ
            quantity = min(quantity_percent * total_position, remaining_position)
            remaining_position -= quantity
            
            # Tính giá chốt lời
            if position_type == 'LONG':
                # Long position: chốt lời ở giá cao hơn
                tp_price = entry_price * (1 + percent / 100)
            else:
                # Short position: chốt lời ở giá thấp hơn
                tp_price = entry_price * (1 - percent / 100)
            
            # Độ tin cậy tăng dần theo % chốt lời
            confidence = min(0.9, 0.5 + percent / 20)
            
            # Thêm vào danh sách nếu tỷ lệ hợp lệ
            if quantity > 0:
                partial_tps.append({
                    'price': tp_price,
                    'percent': percent,
                    'quantity': quantity,
                    'quantity_percentage': quantity * 100,
                    'confidence': confidence,
                    'type': 'partial_take_profit'
                })
                
                logger.info(f"Thêm mức partial TP: {percent}% lợi nhuận, đóng {quantity*100:.1f}% vị thế")
        
        return partial_tps
    
    def _calculate_indicator_exits(self, market_data: pd.DataFrame, position_data: Dict, 
                                 strategy_config: Dict) -> List[Dict]:
        """
        Tính toán các điểm thoát lệnh dựa trên chỉ báo.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            List[Dict]: Danh sách các điểm thoát lệnh dựa trên chỉ báo
        """
        position_type = position_data.get('position_type', 'long')
        entry_price = position_data.get('entry_price', 0)
        current_price = position_data.get('current_price', market_data['close'].iloc[-1])
        
        # Lấy cấu hình
        if 'indicator_based_exit' in strategy_config:
            config = strategy_config['indicator_based_exit']
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['indicator_based_exit']
        
        # Lấy danh sách chỉ báo
        indicators = config.get('indicators', [])
        
        # Tính các điểm thoát
        exit_points = []
        
        for indicator_config in indicators:
            indicator_name = indicator_config.get('name')
            weight = indicator_config.get('weight', 0.5)
            
            if indicator_name == 'rsi':
                # Thoát lệnh dựa trên RSI
                if 'RSI' in market_data.columns:
                    rsi = market_data['RSI'].iloc[-1]
                    
                    if position_type == 'long' and rsi >= indicator_config.get('exit_long_above', 75):
                        exit_points.append({
                            'price': current_price,
                            'type': 'take_profit',
                            'source': 'RSI',
                            'value': rsi,
                            'confidence': weight * 0.8,
                            'reason': f"RSI overbought: {rsi:.1f}"
                        })
                    elif position_type == 'short' and rsi <= indicator_config.get('exit_short_below', 25):
                        exit_points.append({
                            'price': current_price,
                            'type': 'take_profit',
                            'source': 'RSI',
                            'value': rsi,
                            'confidence': weight * 0.8,
                            'reason': f"RSI oversold: {rsi:.1f}"
                        })
            
            elif indicator_name == 'macd':
                # Thoát lệnh dựa trên MACD
                if all(col in market_data.columns for col in ['MACD', 'MACD_Signal']):
                    macd = market_data['MACD'].iloc[-1]
                    signal = market_data['MACD_Signal'].iloc[-1]
                    prev_macd = market_data['MACD'].iloc[-2] if len(market_data) > 2 else macd
                    prev_signal = market_data['MACD_Signal'].iloc[-2] if len(market_data) > 2 else signal
                    
                    # Kiểm tra tín hiệu cắt
                    signal_cross = (prev_macd > prev_signal and macd < signal) or (prev_macd < prev_signal and macd > signal)
                    
                    if signal_cross and indicator_config.get('exit_on_signal_cross', True):
                        exit_points.append({
                            'price': current_price,
                            'type': 'take_profit' if (position_type == 'long' and macd < signal) or (position_type == 'short' and macd > signal) else 'stop_loss',
                            'source': 'MACD',
                            'value': macd,
                            'confidence': weight * 0.7,
                            'reason': f"MACD signal cross: {macd:.4f} vs {signal:.4f}"
                        })
            
            elif indicator_name == 'bbands':
                # Thoát lệnh dựa trên Bollinger Bands
                if all(col in market_data.columns for col in ['BB_Upper', 'BB_Lower']):
                    upper = market_data['BB_Upper'].iloc[-1]
                    lower = market_data['BB_Lower'].iloc[-1]
                    
                    if position_type == 'long' and current_price >= upper and indicator_config.get('exit_long_upper', True):
                        exit_points.append({
                            'price': upper,
                            'type': 'take_profit',
                            'source': 'Bollinger',
                            'value': upper,
                            'confidence': weight * 0.9,
                            'reason': f"Price at upper band: {upper:.2f}"
                        })
                    elif position_type == 'short' and current_price <= lower and indicator_config.get('exit_short_lower', True):
                        exit_points.append({
                            'price': lower,
                            'type': 'take_profit',
                            'source': 'Bollinger',
                            'value': lower,
                            'confidence': weight * 0.9,
                            'reason': f"Price at lower band: {lower:.2f}"
                        })
        
        return exit_points
    
    def _calculate_time_based_exit(self, market_data: pd.DataFrame, position_data: Dict, 
                                 strategy_config: Dict) -> Dict:
        """
        Tính toán điểm thoát lệnh dựa trên thời gian.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            Dict: Thông tin về điểm thoát lệnh dựa trên thời gian
        """
        entry_time = position_data.get('entry_time')
        if not entry_time:
            return None
            
        # Chuyển đổi entry_time thành datetime nếu là string
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        
        # Lấy cấu hình
        if 'time_based_exit' in strategy_config:
            config = strategy_config['time_based_exit']
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['time_based_exit']
        
        # Lấy thông số
        max_holding_time = config.get('max_holding_time', 24)  # giờ
        time_decay_start = config.get('time_decay_start', 12)  # giờ
        decay_factor = config.get('decay_factor', 0.1)  # mỗi giờ
        
        # Tính thời gian đã giữ lệnh
        current_time = datetime.now()
        holding_time = (current_time - entry_time).total_seconds() / 3600  # giờ
        
        # Kiểm tra các điều kiện thoát
        exit_now = False
        reason = ""
        confidence = 0.0
        
        # Kiểm tra thời gian giữ lệnh tối đa
        if holding_time >= max_holding_time:
            exit_now = True
            reason = f"Đã đạt thời gian giữ lệnh tối đa ({max_holding_time} giờ)"
            confidence = 0.9
        
        # Kiểm tra thời gian cuối tuần nếu cần
        if config.get('exit_on_weekend', True):
            # Nếu là thứ 6 và sau 18h, hoặc là thứ 7
            if (current_time.weekday() == 4 and current_time.hour >= 18) or current_time.weekday() == 5:
                exit_now = True
                reason = "Thoát lệnh cuối tuần"
                confidence = 0.95
        
        # Kiểm tra giờ thị trường ít hoạt động
        if config.get('off_hours_exit', True):
            # Thời gian ít hoạt động: 22-2h UTC
            if current_time.hour >= 22 or current_time.hour < 2:
                exit_now = True
                reason = "Thoát lệnh trong giờ thị trường ít hoạt động"
                confidence = 0.7
        
        # Tính hệ số suy giảm theo thời gian
        decay = 0.0
        if holding_time > time_decay_start:
            # Mỗi giờ sau time_decay_start, giảm mục tiêu đi decay_factor
            decay = (holding_time - time_decay_start) * decay_factor
            decay = min(decay, 0.5)  # Giới hạn tối đa
        
        return {
            'exit_now': exit_now,
            'holding_time': holding_time,
            'max_holding_time': max_holding_time,
            'decay': decay,
            'reason': reason,
            'confidence': confidence,
            'type': 'time_based_exit'
        }
    
    def _calculate_volume_profile_exits(self, market_data: pd.DataFrame, position_data: Dict, 
                                      strategy_config: Dict) -> List[Dict]:
        """
        Tính toán các điểm thoát lệnh dựa trên Volume Profile.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            List[Dict]: Danh sách các điểm thoát lệnh dựa trên Volume Profile
        """
        position_type = position_data.get('position_type', 'long')
        entry_price = position_data.get('entry_price', 0)
        current_price = position_data.get('current_price', market_data['close'].iloc[-1])
        
        # Lấy cấu hình
        if 'volume_profile_exit' in strategy_config:
            config = strategy_config['volume_profile_exit']
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['volume_profile_exit']
        
        # Cần tính Volume Profile từ dữ liệu thị trường
        # Trong ví dụ này, giả sử đã có sẵn Volume Profile
        # Trong thực tế, cần import module Volume Profile và tính toán
        
        # Giả lập điểm POC và Value Area
        vp_exits = []
        
        # POC (Point of Control)
        if config.get('use_poc_as_target', True):
            # Giả lập POC ở giá cao hơn cho long position và thấp hơn cho short position
            if position_type == 'long':
                poc_price = entry_price * 1.02  # POC cao hơn 2%
                
                # Chỉ sử dụng POC nếu nó cao hơn giá hiện tại
                if poc_price > current_price:
                    vp_exits.append({
                        'price': poc_price,
                        'type': 'take_profit',
                        'source': 'POC',
                        'confidence': 0.7,
                        'reason': "Price reaching Point of Control"
                    })
            else:
                poc_price = entry_price * 0.98  # POC thấp hơn 2%
                
                # Chỉ sử dụng POC nếu nó thấp hơn giá hiện tại
                if poc_price < current_price:
                    vp_exits.append({
                        'price': poc_price,
                        'type': 'take_profit',
                        'source': 'POC',
                        'confidence': 0.7,
                        'reason': "Price reaching Point of Control"
                    })
        
        # Value Area
        if config.get('use_va_boundaries', True):
            if position_type == 'long' and config.get('va_high_exit_for_long', True):
                # Giả lập VA High cao hơn POC
                va_high = poc_price * 1.01 if 'poc_price' in locals() else entry_price * 1.03
                
                # Chỉ sử dụng VA High nếu nó cao hơn giá hiện tại
                if va_high > current_price:
                    vp_exits.append({
                        'price': va_high,
                        'type': 'take_profit',
                        'source': 'VA High',
                        'confidence': 0.8,
                        'reason': "Price reaching Value Area High"
                    })
            
            if position_type == 'short' and config.get('va_low_exit_for_short', True):
                # Giả lập VA Low thấp hơn POC
                va_low = poc_price * 0.99 if 'poc_price' in locals() else entry_price * 0.97
                
                # Chỉ sử dụng VA Low nếu nó thấp hơn giá hiện tại
                if va_low < current_price:
                    vp_exits.append({
                        'price': va_low,
                        'type': 'take_profit',
                        'source': 'VA Low',
                        'confidence': 0.8,
                        'reason': "Price reaching Value Area Low"
                    })
        
        return vp_exits
    
    def _calculate_order_flow_exits(self, market_data: pd.DataFrame, position_data: Dict, 
                                  strategy_config: Dict) -> List[Dict]:
        """
        Tính toán các điểm thoát lệnh dựa trên Order Flow.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            List[Dict]: Danh sách các điểm thoát lệnh dựa trên Order Flow
        """
        position_type = position_data.get('position_type', 'long')
        entry_price = position_data.get('entry_price', 0)
        current_price = position_data.get('current_price', market_data['close'].iloc[-1])
        
        # Lấy cấu hình
        if 'order_flow_exit' in strategy_config:
            config = strategy_config['order_flow_exit']
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['order_flow_exit']
        
        # Cần tính Order Flow từ dữ liệu thị trường
        # Trong ví dụ này, giả sử đã có sẵn Order Flow metrics
        # Trong thực tế, cần import module Order Flow và tính toán
        
        # Giả lập các tín hiệu Order Flow
        of_exits = []
        
        # Nếu có Delta trong dữ liệu
        if 'Cumulative_Delta_Volume' in market_data.columns and config.get('use_delta_reversal', True):
            # Lấy delta hiện tại và trước đó
            current_delta = market_data['Cumulative_Delta_Volume'].iloc[-1]
            
            # Tính delta trung bình
            avg_delta = market_data['Cumulative_Delta_Volume'].mean()
            delta_ratio = current_delta / avg_delta if avg_delta != 0 else 0
            
            # Kiểm tra điều kiện đảo chiều
            delta_threshold = config.get('delta_threshold', 0.7)
            
            if position_type == 'long' and delta_ratio < -delta_threshold:
                # Đảo chiều delta cho long position
                of_exits.append({
                    'price': current_price,
                    'type': 'stop_loss',
                    'source': 'Delta Reversal',
                    'confidence': 0.6,
                    'reason': f"Delta reversal: {delta_ratio:.2f}"
                })
            elif position_type == 'short' and delta_ratio > delta_threshold:
                # Đảo chiều delta cho short position
                of_exits.append({
                    'price': current_price,
                    'type': 'stop_loss',
                    'source': 'Delta Reversal',
                    'confidence': 0.6,
                    'reason': f"Delta reversal: {delta_ratio:.2f}"
                })
        
        # Nếu có Order Imbalance
        if 'Order_Imbalance' in market_data.columns and config.get('use_imbalance', True):
            imbalance = market_data['Order_Imbalance'].iloc[-1]
            imbalance_threshold = config.get('imbalance_threshold', 0.8)
            
            if position_type == 'long' and imbalance < -imbalance_threshold:
                # Mất cân bằng về phía bán cho long position
                of_exits.append({
                    'price': current_price,
                    'type': 'stop_loss',
                    'source': 'Order Imbalance',
                    'confidence': 0.7,
                    'reason': f"Sell imbalance: {imbalance:.2f}"
                })
            elif position_type == 'short' and imbalance > imbalance_threshold:
                # Mất cân bằng về phía mua cho short position
                of_exits.append({
                    'price': current_price,
                    'type': 'stop_loss',
                    'source': 'Order Imbalance',
                    'confidence': 0.7,
                    'reason': f"Buy imbalance: {imbalance:.2f}"
                })
        
        return of_exits
    
    def _calculate_volatility_exits(self, market_data: pd.DataFrame, position_data: Dict, 
                                  strategy_config: Dict) -> List[Dict]:
        """
        Tính toán các điểm thoát lệnh dựa trên biến động.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            
        Returns:
            List[Dict]: Danh sách các điểm thoát lệnh dựa trên biến động
        """
        position_type = position_data.get('position_type', 'long')
        entry_price = position_data.get('entry_price', 0)
        current_price = position_data.get('current_price', market_data['close'].iloc[-1])
        
        # Lấy cấu hình
        if 'volatility_based_exit' in strategy_config:
            config = strategy_config['volatility_based_exit']
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['volatility_based_exit']
        
        # Các điểm thoát lệnh dựa trên biến động
        vol_exits = []
        
        # ATR-based stop loss
        if 'ATR' in market_data.columns:
            atr = market_data['ATR'].iloc[-1]
            atr_factor = config.get('atr_factor', 2.5)
            
            if position_type == 'long':
                # Stop loss dựa trên ATR cho long position
                atr_stop = current_price - atr * atr_factor
                
                vol_exits.append({
                    'price': atr_stop,
                    'type': 'stop_loss',
                    'source': 'ATR',
                    'confidence': 0.75,
                    'reason': f"ATR-based stop: {atr_stop:.2f} (ATR: {atr:.2f})"
                })
            else:
                # Stop loss dựa trên ATR cho short position
                atr_stop = current_price + atr * atr_factor
                
                vol_exits.append({
                    'price': atr_stop,
                    'type': 'stop_loss',
                    'source': 'ATR',
                    'confidence': 0.75,
                    'reason': f"ATR-based stop: {atr_stop:.2f} (ATR: {atr:.2f})"
                })
        
        # Bollinger Bands exits
        if all(col in market_data.columns for col in ['BB_Upper', 'BB_Lower']) and config.get('use_bbands', True):
            upper = market_data['BB_Upper'].iloc[-1]
            lower = market_data['BB_Lower'].iloc[-1]
            bbands_dev = config.get('bbands_dev', 2.0)
            
            if position_type == 'long':
                # Take profit dựa trên BB Upper cho long position
                vol_exits.append({
                    'price': upper,
                    'type': 'take_profit',
                    'source': 'Bollinger',
                    'confidence': 0.65,
                    'reason': f"Upper Bollinger Band: {upper:.2f} ({bbands_dev} stdev)"
                })
            else:
                # Take profit dựa trên BB Lower cho short position
                vol_exits.append({
                    'price': lower,
                    'type': 'take_profit',
                    'source': 'Bollinger',
                    'confidence': 0.65,
                    'reason': f"Lower Bollinger Band: {lower:.2f} ({bbands_dev} stdev)"
                })
        
        # Kiểm tra tăng đột biến biến động
        if 'Price_Volatility' in market_data.columns and config.get('exit_on_volatility_spike', True):
            vol = market_data['Price_Volatility'].iloc[-1]
            avg_vol = market_data['Price_Volatility'].mean()
            spike_factor = config.get('volatility_spike_factor', 2.0)
            
            if vol > avg_vol * spike_factor:
                vol_exits.append({
                    'price': current_price,
                    'type': 'stop_loss',
                    'source': 'Volatility Spike',
                    'confidence': 0.6,
                    'reason': f"Volatility spike: {vol:.4f} vs avg {avg_vol:.4f}"
                })
        
        return vol_exits
    
    def _calculate_profit_maximizer_exits(self, market_data: pd.DataFrame, position_data: Dict, 
                                        strategy_config: Dict, existing_exits: Dict) -> Dict:
        """
        Tính toán các điểm thoát lệnh tối đa hóa lợi nhuận.
        
        Args:
            market_data (pd.DataFrame): DataFrame chứa dữ liệu thị trường
            position_data (Dict): Thông tin về vị thế hiện tại
            strategy_config (Dict): Cấu hình chiến lược
            existing_exits (Dict): Các điểm thoát đã tính toán từ các chiến lược khác
            
        Returns:
            Dict: Thông tin về các điểm thoát lệnh tối đa hóa lợi nhuận
        """
        position_type = position_data.get('position_type', 'long')
        entry_price = position_data.get('entry_price', 0)
        current_price = position_data.get('current_price', market_data['close'].iloc[-1])
        unrealized_pnl_pct = position_data.get('unrealized_pnl_pct', 0)
        
        # Lấy cấu hình
        if 'profit_maximizer' in strategy_config:
            config = strategy_config['profit_maximizer']
        else:
            config = self.DEFAULT_STRATEGY_CONFIGS['profit_maximizer']
        
        # Chỉ tiến hành tối đa hóa nếu đã có lợi nhuận
        if unrealized_pnl_pct <= 0:
            return existing_exits
        
        # Sao chép các điểm exit hiện tại
        exit_points = existing_exits.copy()
        
        # Risk-reward target
        rr_target = config.get('risk_reward_target', 3.0)
        
        # Tính risk
        risk = 0
        if exit_points.get('stop_loss'):
            if position_type == 'long':
                risk = entry_price - exit_points['stop_loss']['price']
            else:
                risk = exit_points['stop_loss']['price'] - entry_price
        else:
            # Nếu không có stop, giả định risk là 2% giá vào lệnh
            risk = entry_price * 0.02
        
        # Tính target based on risk-reward
        if risk > 0:
            if position_type == 'long':
                target_price = entry_price + (risk * rr_target)
            else:
                target_price = entry_price - (risk * rr_target)
            
            # Thêm take profit nếu chưa có hoặc nếu target mới tốt hơn
            if not exit_points.get('take_profit') or (position_type == 'long' and target_price < exit_points['take_profit']['price']) or (position_type == 'short' and target_price > exit_points['take_profit']['price']):
                exit_points['take_profit'] = {
                    'price': target_price,
                    'source': 'Risk-Reward',
                    'confidence': 0.8,
                    'reason': f"Risk-reward target: {rr_target:.1f}x"
                }
        
        # Tối ưu hóa trailing stop
        if config.get('enable_trailing', True) and unrealized_pnl_pct > 0:
            # Điều chỉnh trailing stop dựa trên lợi nhuận
            if position_type == 'long':
                breakeven_price = entry_price
                
                # At 25% of target profit, move stop to breakeven
                if unrealized_pnl_pct >= 0.25 * rr_target:
                    new_stop = max(breakeven_price, exit_points.get('trailing_stop', {}).get('price', breakeven_price))
                    
                    # Nếu đạt 50% target, lock in 25% of profit
                    if unrealized_pnl_pct >= 0.5 * rr_target:
                        profit_lock = (current_price - entry_price) * 0.25
                        new_stop = max(new_stop, entry_price + profit_lock)
                    
                    # Nếu đạt 75% target, lock in 50% of profit
                    if unrealized_pnl_pct >= 0.75 * rr_target:
                        profit_lock = (current_price - entry_price) * 0.5
                        new_stop = max(new_stop, entry_price + profit_lock)
                    
                    # Nếu đạt hoặc vượt target, lock in 75% of profit
                    if unrealized_pnl_pct >= rr_target:
                        profit_lock = (current_price - entry_price) * 0.75
                        new_stop = max(new_stop, entry_price + profit_lock)
                    
                    # Update trailing stop
                    if 'trailing_stop' not in exit_points or new_stop > exit_points['trailing_stop']['price']:
                        exit_points['trailing_stop'] = {
                            'price': new_stop,
                            'type': 'trailing_stop',
                            'source': 'Profit Maximizer',
                            'confidence': 0.85,
                            'enhanced': True
                        }
            else:  # short position
                breakeven_price = entry_price
                
                # At 25% of target profit, move stop to breakeven
                if unrealized_pnl_pct >= 0.25 * rr_target:
                    new_stop = min(breakeven_price, exit_points.get('trailing_stop', {}).get('price', breakeven_price))
                    
                    # Nếu đạt 50% target, lock in 25% of profit
                    if unrealized_pnl_pct >= 0.5 * rr_target:
                        profit_lock = (entry_price - current_price) * 0.25
                        new_stop = min(new_stop, entry_price - profit_lock)
                    
                    # Nếu đạt 75% target, lock in 50% of profit
                    if unrealized_pnl_pct >= 0.75 * rr_target:
                        profit_lock = (entry_price - current_price) * 0.5
                        new_stop = min(new_stop, entry_price - profit_lock)
                    
                    # Nếu đạt hoặc vượt target, lock in 75% of profit
                    if unrealized_pnl_pct >= rr_target:
                        profit_lock = (entry_price - current_price) * 0.75
                        new_stop = min(new_stop, entry_price - profit_lock)
                    
                    # Update trailing stop
                    if 'trailing_stop' not in exit_points or new_stop < exit_points['trailing_stop']['price']:
                        exit_points['trailing_stop'] = {
                            'price': new_stop,
                            'type': 'trailing_stop',
                            'source': 'Profit Maximizer',
                            'confidence': 0.85,
                            'enhanced': True
                        }
        
        # Tối ưu hóa partial take profits nếu chưa có
        if config.get('enable_partial_tp', True) and not exit_points.get('partial_take_profits'):
            partial_tps = []
            
            # Tính các mức take profit
            if position_type == 'long':
                # 4 mức take profit: 25%, 50%, 75%, 100% của target
                for i, pct in enumerate([0.25, 0.5, 0.75, 1.0]):
                    tp_price = entry_price + (risk * rr_target * pct)
                    partial_tps.append({
                        'price': tp_price,
                        'percent': pct * 100,
                        'quantity': 0.25,  # 25% mỗi lần
                        'confidence': 0.7 + (pct * 0.1),
                        'type': 'partial_take_profit'
                    })
            else:
                # 4 mức take profit: 25%, 50%, 75%, 100% của target
                for i, pct in enumerate([0.25, 0.5, 0.75, 1.0]):
                    tp_price = entry_price - (risk * rr_target * pct)
                    partial_tps.append({
                        'price': tp_price,
                        'percent': pct * 100,
                        'quantity': 0.25,  # 25% mỗi lần
                        'confidence': 0.7 + (pct * 0.1),
                        'type': 'partial_take_profit'
                    })
            
            exit_points['partial_take_profits'] = partial_tps
        
        return exit_points
    
    def _create_exit_config(self, strategies: List[str], strategy_scores: Dict[str, float]) -> Dict:
        """
        Tạo cấu hình thoát lệnh dựa trên các chiến lược đã chọn.
        
        Args:
            strategies (List[str]): Danh sách các chiến lược
            strategy_scores (Dict[str, float]): Điểm của từng chiến lược
            
        Returns:
            Dict: Cấu hình thoát lệnh
        """
        # Tạo cấu hình thoát lệnh mới
        exit_config = {}
        
        # Thêm cấu hình của từng chiến lược
        for strategy in strategies:
            # Lấy cấu hình mặc định
            strategy_config = self.strategy_configs.get(strategy, self.DEFAULT_STRATEGY_CONFIGS.get(strategy, {}))
            
            # Thêm vào cấu hình chung
            exit_config[strategy] = strategy_config
        
        # Thêm thông tin khác
        exit_config['strategy_scores'] = strategy_scores
        exit_config['timestamp'] = datetime.now().isoformat()
        
        return exit_config
    
    def _add_to_history(self, exit_strategy: Dict) -> None:
        """
        Thêm chiến lược thoát lệnh vào lịch sử.
        
        Args:
            exit_strategy (Dict): Thông tin về chiến lược thoát lệnh
        """
        # Tạo bản ghi lịch sử
        history_record = {
            'timestamp': datetime.now().isoformat(),
            'regime': exit_strategy['regime'],
            'active_strategies': exit_strategy['active_strategies'],
            'strategy_scores': exit_strategy['strategy_scores'],
            'position_type': exit_strategy['position_type']
        }
        
        # Thêm vào lịch sử
        self.exit_history.append(history_record)
        
        # Giới hạn kích thước lịch sử
        if len(self.exit_history) > 1000:
            self.exit_history = self.exit_history[-1000:]
    
    def _save_config(self) -> None:
        """Lưu cấu hình vào file."""
        try:
            config = {
                'strategy_configs': self.strategy_configs,
                'regime_strategy_mapping': self.REGIME_EXIT_STRATEGY_MAPPING,
                'strategy_weights': self.STRATEGY_WEIGHTS,
                'updated_at': datetime.now().isoformat()
            }
            
            # Lưu vào file
            with open(os.path.join(self.data_storage_path, 'exit_strategy_config.json'), 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"Đã lưu cấu hình thoát lệnh tại: {self.data_storage_path}/exit_strategy_config.json")
                
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình thoát lệnh: {str(e)}")
    
    def _load_config(self) -> None:
        """Tải cấu hình từ file."""
        try:
            config_file = os.path.join(self.data_storage_path, 'exit_strategy_config.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                # Cập nhật cấu hình
                if 'strategy_configs' in config:
                    self.strategy_configs.update(config['strategy_configs'])
                    
                if 'regime_strategy_mapping' in config:
                    self.REGIME_EXIT_STRATEGY_MAPPING.update(config['regime_strategy_mapping'])
                    
                if 'strategy_weights' in config:
                    self.STRATEGY_WEIGHTS.update(config['strategy_weights'])
                    
                logger.info(f"Đã tải cấu hình thoát lệnh từ: {config_file}")
                
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình thoát lệnh: {str(e)}")


if __name__ == "__main__":
    # Ví dụ sử dụng
    exit_strategy = AdaptiveExitStrategy()
    
    # Tạo dữ liệu mẫu
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Dữ liệu mẫu
    dates = [datetime.now() - timedelta(hours=i) for i in range(100, 0, -1)]
    close_prices = [100 + i * 0.5 + (i % 10) * 0.1 for i in range(100)]
    
    # Tạo DataFrame
    market_data = pd.DataFrame({
        'open': [p - 0.5 for p in close_prices],
        'high': [p + 0.5 for p in close_prices],
        'low': [p - 1.0 for p in close_prices],
        'close': close_prices,
        'volume': [1000 * (1 + 0.1 * (i % 5)) for i in range(100)]
    }, index=dates)
    
    # Thêm các chỉ báo
    market_data['RSI'] = 50 + np.sin(np.linspace(0, 4*np.pi, 100)) * 20  # RSI 30-70
    market_data['MACD'] = np.sin(np.linspace(0, 2*np.pi, 100)) * 2  # MACD -2 to 2
    market_data['MACD_Signal'] = np.sin(np.linspace(0.5, 2.5*np.pi, 100)) * 1.5  # Signal -1.5 to 1.5
    market_data['BB_Upper'] = market_data['close'] + 2
    market_data['BB_Lower'] = market_data['close'] - 2
    market_data['ATR'] = 1.5
    market_data['ADX'] = 25
    market_data['Price_Volatility'] = 0.02
    market_data['BB_Width'] = 0.02
    
    # Tạo dữ liệu vị thế
    position_data = {
        'position_type': 'long',
        'entry_price': 125,
        'current_price': 140,
        'unrealized_pnl_pct': 12.0,
        'entry_time': (datetime.now() - timedelta(hours=24)).isoformat(),
        'holding_time': 24,
        'prev_pnl_pct': 10.0
    }
    
    # Xác định chiến lược thoát lệnh
    strategy = exit_strategy.determine_exit_strategy(market_data, position_data, 'trending_bullish')
    
    print("Chiến lược thoát lệnh:")
    print(f"Chế độ thị trường: {strategy['regime']}")
    print(f"Chiến lược active: {strategy['active_strategies']}")
    print("Điểm chiến lược:")
    for s, score in strategy['strategy_scores'].items():
        print(f"  {s}: {score:.2f}")
    
    # Tính toán các điểm thoát
    exit_points = exit_strategy.calculate_exit_points(market_data, position_data, strategy)
    
    print("\nĐiểm thoát lệnh:")
    if exit_points.get('stop_loss'):
        print(f"Stop Loss: {exit_points['stop_loss']['price']:.2f} ({exit_points['stop_loss']['source']})")
    
    if exit_points.get('take_profit'):
        print(f"Take Profit: {exit_points['take_profit']['price']:.2f} ({exit_points['take_profit']['source']})")
    
    if exit_points.get('trailing_stop'):
        print(f"Trailing Stop: {exit_points['trailing_stop']['price']:.2f}")
    
    for i, tp in enumerate(exit_points.get('partial_take_profits', [])):
        print(f"Partial TP {i+1}: {tp['price']:.2f} ({tp['quantity']*100:.0f}%)")
    
    # Lấy tín hiệu thoát lệnh
    signal = exit_strategy.get_exit_signal(market_data, position_data)
    
    print("\nTín hiệu thoát lệnh:")
    print(f"Exit signal: {signal['exit_signal']}")
    if signal['exit_signal']:
        print(f"Exit type: {signal['exit_type']}")
        print(f"Exit price: {signal['exit_price']:.2f}")
        print(f"Exit reason: {signal['exit_reason']}")
    
    # Tạo biểu đồ
    chart_path = exit_strategy.visualize_exit_points(market_data, position_data, exit_points)
    print(f"\nBiểu đồ: {chart_path}")