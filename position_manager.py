#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module quản lý vị thế (PositionManager)

Module này cung cấp các chức năng quản lý lệnh đang mở, phân tích và đưa ra khuyến nghị
dựa trên điều kiện thị trường, cũng như tính toán các thông số rủi ro.
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional
import pandas as pd
import numpy as np

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('position_manager')

class PositionManager:
    """Lớp quản lý vị thế và phân tích"""
    
    def __init__(self, binance_api=None, market_analyzer=None, config_path='config.json'):
        """
        Khởi tạo quản lý vị thế
        
        Args:
            binance_api: Đối tượng BinanceAPI để tương tác với sàn
            market_analyzer: Đối tượng phân tích thị trường
            config_path (str): Đường dẫn đến file cấu hình
        """
        self.binance_api = binance_api
        self.market_analyzer = market_analyzer
        self.config_path = config_path
        self.positions = []
        self.position_history = []
        self.load_config()
        
    def load_config(self):
        """Tải cấu hình từ file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info("Đã tải cấu hình từ %s", self.config_path)
            else:
                self.config = self._get_default_config()
                logger.warning("Không tìm thấy file cấu hình, sử dụng cấu hình mặc định")
        except Exception as e:
            logger.error("Lỗi khi tải cấu hình: %s", str(e))
            self.config = self._get_default_config()
    
    def _get_default_config(self):
        """Trả về cấu hình mặc định"""
        return {
            "risk_management": {
                "max_positions": 5,
                "max_position_size_percent": 20,
                "max_daily_loss_percent": 5,
                "trailing_stop_activation_percent": 1.5,
                "trailing_stop_callback_percent": 0.5
            },
            "position_analysis": {
                "take_profit_targets": [1.5, 3, 5, 10],
                "stop_loss_levels": [1, 2, 3, 5],
                "correlation_threshold": 0.7,
                "profit_take_thresholds": [5, 10, 15],
                "loss_cut_thresholds": [3, 5, 10]
            }
        }
    
    def save_config(self):
        """Lưu cấu hình vào file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info("Đã lưu cấu hình vào %s", self.config_path)
            return True
        except Exception as e:
            logger.error("Lỗi khi lưu cấu hình: %s", str(e))
            return False
    
    def scan_open_positions(self) -> List[Dict]:
        """
        Quét và cập nhật tất cả các vị thế đang mở từ Binance
        
        Returns:
            List[Dict]: Danh sách các vị thế đang mở
        """
        try:
            if self.binance_api:
                # Gọi API Binance để lấy vị thế đang mở
                positions_data = self.binance_api.get_futures_position_risk()
                positions = []
                
                for pos in positions_data:
                    # Chỉ lấy những vị thế thực sự đang mở (số lượng khác 0)
                    if float(pos.get('positionAmt', 0)) != 0:
                        position_info = self._format_position_data(pos)
                        positions.append(position_info)
                
                self.positions = positions
                logger.info(f"Đã quét được {len(positions)} vị thế đang mở")
                return positions
            else:
                # Nếu không có API, trả về dữ liệu demo
                return self._get_demo_positions()
        except Exception as e:
            logger.error(f"Lỗi khi quét vị thế đang mở: {str(e)}")
            return self._get_demo_positions()
    
    def _format_position_data(self, position_data: Dict) -> Dict:
        """
        Định dạng lại dữ liệu vị thế từ Binance API
        
        Args:
            position_data (Dict): Dữ liệu vị thế từ Binance
            
        Returns:
            Dict: Dữ liệu vị thế đã được định dạng lại
        """
        symbol = position_data.get('symbol', '')
        position_amt = float(position_data.get('positionAmt', 0))
        entry_price = float(position_data.get('entryPrice', 0))
        mark_price = float(position_data.get('markPrice', 0))
        leverage = int(position_data.get('leverage', 1))
        unrealized_profit = float(position_data.get('unRealizedProfit', 0))
        
        position_type = 'LONG' if position_amt > 0 else 'SHORT'
        position_size_usd = abs(position_amt * mark_price)
        
        # Tính toán PnL theo phần trăm
        pnl_percent = 0
        if entry_price > 0:
            if position_type == 'LONG':
                pnl_percent = ((mark_price - entry_price) / entry_price) * 100 * leverage
            else:
                pnl_percent = ((entry_price - mark_price) / entry_price) * 100 * leverage
        
        # Tạo ID duy nhất cho vị thế
        position_id = f"{symbol}_{position_type}_{int(time.time())}"
        
        return {
            'id': position_id,
            'symbol': symbol,
            'type': position_type,
            'amount': abs(position_amt),
            'entry_price': entry_price,
            'current_price': mark_price,
            'leverage': leverage,
            'pnl': unrealized_profit,
            'pnl_percent': pnl_percent,
            'position_size_usd': position_size_usd,
            'stop_loss': None,  # Cần API khác để lấy thông tin này
            'take_profit': None,  # Cần API khác để lấy thông tin này
            'entry_time': None,  # Cần API khác để lấy thông tin này
            'duration': None,    # Sẽ tính khi có entry_time
            'tags': [],
            'notes': '',
            'last_analyzed': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _get_demo_positions(self) -> List[Dict]:
        """
        Tạo dữ liệu vị thế giả lập cho môi trường demo
        
        Returns:
            List[Dict]: Danh sách các vị thế giả lập
        """
        logger.info("Sử dụng dữ liệu vị thế giả lập")
        
        demo_positions = [
            {
                'id': 'BTCUSDT_LONG_1',
                'symbol': 'BTCUSDT',
                'type': 'LONG',
                'amount': 0.01,
                'entry_price': 36500.0,
                'current_price': 38200.0,
                'leverage': 10,
                'pnl': 17.0,
                'pnl_percent': 4.66,
                'position_size_usd': 382.0,
                'stop_loss': 35000.0,
                'take_profit': 40000.0,
                'entry_time': (datetime.now().timestamp() - 86400),  # 1 ngày trước
                'duration': '1d',
                'tags': ['trend_following', 'medium_risk'],
                'notes': 'Vị thế mở theo tín hiệu RSI oversold + MACD cross',
                'last_analyzed': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'id': 'ETHUSDT_SHORT_1',
                'symbol': 'ETHUSDT',
                'type': 'SHORT',
                'amount': 0.1,
                'entry_price': 2200.0,
                'current_price': 2330.0,
                'leverage': 5,
                'pnl': -13.0,
                'pnl_percent': -2.95,
                'position_size_usd': 233.0,
                'stop_loss': 2400.0,
                'take_profit': 1900.0,
                'entry_time': (datetime.now().timestamp() - 43200),  # 12 giờ trước
                'duration': '12h',
                'tags': ['counter_trend', 'high_risk'],
                'notes': 'Vị thế mở theo tín hiệu Overbought + Resistance',
                'last_analyzed': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # Cập nhật danh sách vị thế hiện tại
        self.positions = demo_positions
        return demo_positions
    
    def analyze_position(self, position_id: str) -> Dict:
        """
        Phân tích một vị thế cụ thể
        
        Args:
            position_id (str): ID của vị thế cần phân tích
            
        Returns:
            Dict: Kết quả phân tích
        """
        position = self.get_position(position_id)
        if not position:
            logger.error(f"Không tìm thấy vị thế với ID: {position_id}")
            return {'success': False, 'message': 'Không tìm thấy vị thế'}
        
        # Lấy dữ liệu thị trường để phân tích
        market_data = self._get_market_data(position['symbol'])
        
        # Tính toán các thông số phân tích
        analysis_result = {
            'position_id': position_id,
            'symbol': position['symbol'],
            'type': position['type'],
            'entry_price': position['entry_price'],
            'current_price': position['current_price'],
            'pnl': position['pnl'],
            'pnl_percent': position['pnl_percent'],
            'market_condition': self._analyze_market_condition(market_data),
            'risk_level': self._calculate_risk_level(position, market_data),
            'recommended_action': self._generate_recommendation(position, market_data),
            'stop_loss_recommendations': self._calculate_stop_loss_levels(position, market_data),
            'take_profit_recommendations': self._calculate_take_profit_levels(position, market_data),
            'estimated_target_time': self._estimate_target_time(position, market_data),
            'probability_analysis': self._analyze_probability(position, market_data),
            'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Cập nhật thời gian phân tích cuối cùng
        position['last_analyzed'] = analysis_result['analysis_timestamp']
        
        return analysis_result
    
    def get_position(self, position_id: str) -> Optional[Dict]:
        """
        Lấy thông tin một vị thế theo ID
        
        Args:
            position_id (str): ID của vị thế
            
        Returns:
            Optional[Dict]: Thông tin vị thế hoặc None nếu không tìm thấy
        """
        for position in self.positions:
            if position['id'] == position_id:
                return position
        return None
    
    def close_position(self, position_id: str, close_price: float = None) -> Dict:
        """
        Đóng một vị thế theo ID
        
        Args:
            position_id (str): ID của vị thế
            close_price (float, optional): Giá đóng vị thế
            
        Returns:
            Dict: Kết quả thực hiện lệnh đóng
        """
        position = self.get_position(position_id)
        if not position:
            logger.error(f"Không thể đóng vị thế không tồn tại: {position_id}")
            return {'success': False, 'message': 'Không tìm thấy vị thế'}
        
        try:
            # Gọi Binance API để đóng vị thế thực tế
            if self.binance_api:
                # Triển khai sau khi có API đầy đủ
                pass
            
            # Nếu không có API hoặc đang ở chế độ demo
            if not close_price:
                close_price = position['current_price']
            
            # Tính toán kết quả vị thế
            pnl = position['pnl']
            pnl_percent = position['pnl_percent']
            
            # Lưu vị thế vào lịch sử
            closed_position = position.copy()
            closed_position['close_price'] = close_price
            closed_position['close_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            closed_position['final_pnl'] = pnl
            closed_position['final_pnl_percent'] = pnl_percent
            
            self.position_history.append(closed_position)
            
            # Xóa vị thế khỏi danh sách đang mở
            self.positions = [p for p in self.positions if p['id'] != position_id]
            
            logger.info(f"Đã đóng vị thế {position_id} với P&L: {pnl} ({pnl_percent:.2f}%)")
            
            return {
                'success': True,
                'message': f'Đã đóng vị thế {position["symbol"]} {position["type"]} với P&L: {pnl:.2f} USDT ({pnl_percent:.2f}%)',
                'position': closed_position
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi đóng vị thế {position_id}: {str(e)}")
            return {'success': False, 'message': f'Lỗi: {str(e)}'}
    
    def update_stop_loss(self, position_id: str, stop_loss: float) -> Dict:
        """
        Cập nhật stop loss cho một vị thế
        
        Args:
            position_id (str): ID của vị thế
            stop_loss (float): Giá stop loss mới
            
        Returns:
            Dict: Kết quả cập nhật
        """
        position = self.get_position(position_id)
        if not position:
            return {'success': False, 'message': 'Không tìm thấy vị thế'}
        
        try:
            # Kiểm tra tính hợp lệ của stop loss
            if position['type'] == 'LONG' and stop_loss >= position['current_price']:
                return {'success': False, 'message': 'Stop loss cho lệnh LONG phải thấp hơn giá hiện tại'}
            if position['type'] == 'SHORT' and stop_loss <= position['current_price']:
                return {'success': False, 'message': 'Stop loss cho lệnh SHORT phải cao hơn giá hiện tại'}
            
            # Gọi Binance API để cập nhật stop loss
            if self.binance_api:
                # Triển khai sau khi có API đầy đủ
                pass
            
            # Cập nhật thông tin vị thế
            position['stop_loss'] = stop_loss
            
            logger.info(f"Đã cập nhật stop loss cho vị thế {position_id}: {stop_loss}")
            
            return {
                'success': True,
                'message': f'Đã cập nhật stop loss cho vị thế {position["symbol"]} {position["type"]}: {stop_loss}',
                'position': position
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật stop loss cho vị thế {position_id}: {str(e)}")
            return {'success': False, 'message': f'Lỗi: {str(e)}'}
    
    def update_take_profit(self, position_id: str, take_profit: float) -> Dict:
        """
        Cập nhật take profit cho một vị thế
        
        Args:
            position_id (str): ID của vị thế
            take_profit (float): Giá take profit mới
            
        Returns:
            Dict: Kết quả cập nhật
        """
        position = self.get_position(position_id)
        if not position:
            return {'success': False, 'message': 'Không tìm thấy vị thế'}
        
        try:
            # Kiểm tra tính hợp lệ của take profit
            if position['type'] == 'LONG' and take_profit <= position['current_price']:
                return {'success': False, 'message': 'Take profit cho lệnh LONG phải cao hơn giá hiện tại'}
            if position['type'] == 'SHORT' and take_profit >= position['current_price']:
                return {'success': False, 'message': 'Take profit cho lệnh SHORT phải thấp hơn giá hiện tại'}
            
            # Gọi Binance API để cập nhật take profit
            if self.binance_api:
                # Triển khai sau khi có API đầy đủ
                pass
            
            # Cập nhật thông tin vị thế
            position['take_profit'] = take_profit
            
            logger.info(f"Đã cập nhật take profit cho vị thế {position_id}: {take_profit}")
            
            return {
                'success': True,
                'message': f'Đã cập nhật take profit cho vị thế {position["symbol"]} {position["type"]}: {take_profit}',
                'position': position
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi cập nhật take profit cho vị thế {position_id}: {str(e)}")
            return {'success': False, 'message': f'Lỗi: {str(e)}'}
    
    def analyze_all_positions(self) -> Dict:
        """
        Phân tích tất cả các vị thế đang mở
        
        Returns:
            Dict: Kết quả phân tích tất cả vị thế
        """
        # Cập nhật danh sách vị thế đang mở
        self.scan_open_positions()
        
        analysis_results = []
        for position in self.positions:
            analysis = self.analyze_position(position['id'])
            analysis_results.append(analysis)
        
        # Phân tích danh mục tổng thể
        portfolio_analysis = self._analyze_portfolio()
        
        return {
            'positions': analysis_results,
            'portfolio': portfolio_analysis,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _analyze_portfolio(self) -> Dict:
        """
        Phân tích danh mục tổng thể
        
        Returns:
            Dict: Kết quả phân tích danh mục
        """
        if not self.positions:
            return {
                'total_positions': 0,
                'total_pnl': 0,
                'total_pnl_percent': 0,
                'risk_level': 'low',
                'recommendation': 'Không có vị thế đang mở'
            }
        
        total_pnl = sum(p['pnl'] for p in self.positions)
        average_pnl_percent = sum(p['pnl_percent'] for p in self.positions) / len(self.positions)
        
        # Phân tích tương quan giữa các vị thế
        correlation_matrix = self._calculate_position_correlation()
        
        # Tổng hợp tổng rủi ro
        total_risk = self._calculate_total_portfolio_risk()
        
        # Đưa ra khuyến nghị chung cho danh mục
        portfolio_recommendation = self._generate_portfolio_recommendation()
        
        return {
            'total_positions': len(self.positions),
            'total_pnl': total_pnl,
            'average_pnl_percent': average_pnl_percent,
            'risk_level': total_risk['risk_level'],
            'risk_score': total_risk['risk_score'],
            'correlation_risk': bool(correlation_matrix['high_correlation']),
            'concentration_risk': self._has_concentration_risk(),
            'recommendations': portfolio_recommendation
        }
    
    def _calculate_position_correlation(self) -> Dict:
        """
        Tính toán ma trận tương quan giữa các vị thế
        
        Returns:
            Dict: Thông tin về tương quan vị thế
        """
        if len(self.positions) < 2:
            return {'high_correlation': False, 'correlated_pairs': []}
        
        # Trong môi trường thực tế, cần lấy dữ liệu giá theo thời gian để tính tương quan
        # Đây là mô phỏng đơn giản
        correlated_pairs = []
        high_correlation = False
        
        return {
            'high_correlation': high_correlation,
            'correlated_pairs': correlated_pairs
        }
    
    def _has_concentration_risk(self) -> bool:
        """
        Kiểm tra xem danh mục có rủi ro tập trung không
        
        Returns:
            bool: True nếu có rủi ro tập trung
        """
        if not self.positions:
            return False
        
        # Kiểm tra vị thế lớn nhất chiếm bao nhiêu phần trăm danh mục
        total_size = sum(p['position_size_usd'] for p in self.positions)
        if total_size == 0:
            return False
            
        max_position_size = max(p['position_size_usd'] for p in self.positions)
        max_position_percent = (max_position_size / total_size) * 100
        
        # Nếu một vị thế chiếm trên 40% tổng danh mục, xem là có rủi ro tập trung
        return max_position_percent > 40
    
    def _calculate_total_portfolio_risk(self) -> Dict:
        """
        Tính toán tổng rủi ro của danh mục
        
        Returns:
            Dict: Thông tin rủi ro danh mục
        """
        if not self.positions:
            return {'risk_level': 'low', 'risk_score': 0}
        
        # Tính điểm rủi ro dựa trên nhiều yếu tố
        risk_score = 0
        
        # 1. Số lượng vị thế (nhiều vị thế = rủi ro cao hơn)
        position_count = len(self.positions)
        if position_count > 5:
            risk_score += 3
        elif position_count > 3:
            risk_score += 2
        else:
            risk_score += 1
        
        # 2. Tỷ lệ vị thế đang lỗ
        losing_positions = [p for p in self.positions if p['pnl'] < 0]
        losing_ratio = len(losing_positions) / position_count if position_count > 0 else 0
        
        if losing_ratio > 0.7:
            risk_score += 3
        elif losing_ratio > 0.5:
            risk_score += 2
        elif losing_ratio > 0.3:
            risk_score += 1
        
        # 3. Mức độ lỗ trung bình của các vị thế đang lỗ
        if losing_positions:
            avg_loss_percent = sum(p['pnl_percent'] for p in losing_positions) / len(losing_positions)
            if avg_loss_percent < -10:
                risk_score += 3
            elif avg_loss_percent < -5:
                risk_score += 2
            elif avg_loss_percent < -2:
                risk_score += 1
        
        # Đánh giá mức độ rủi ro
        risk_level = 'low'
        if risk_score >= 7:
            risk_level = 'very_high'
        elif risk_score >= 5:
            risk_level = 'high'
        elif risk_score >= 3:
            risk_level = 'medium'
        
        return {'risk_level': risk_level, 'risk_score': risk_score}
    
    def _generate_portfolio_recommendation(self) -> List[str]:
        """
        Đưa ra khuyến nghị chung cho danh mục
        
        Returns:
            List[str]: Danh sách các khuyến nghị
        """
        if not self.positions:
            return ["Chưa có vị thế nào được mở. Hãy đợi tín hiệu giao dịch tốt."]
        
        recommendations = []
        
        # Tính toán các số liệu hỗ trợ khuyến nghị
        losing_positions = [p for p in self.positions if p['pnl'] < 0]
        profitable_positions = [p for p in self.positions if p['pnl'] > 0]
        losing_ratio = len(losing_positions) / len(self.positions) if self.positions else 0
        
        # Phân tích danh mục
        portfolio_risk = self._calculate_total_portfolio_risk()
        
        # Đưa ra các khuyến nghị dựa trên phân tích
        if portfolio_risk['risk_level'] == 'very_high':
            recommendations.append("⚠️ Cảnh báo: Danh mục đang có rủi ro rất cao. Nên cắt giảm vị thế ngay lập tức.")
        elif portfolio_risk['risk_level'] == 'high':
            recommendations.append("⚠️ Danh mục đang có rủi ro cao. Cân nhắc đóng bớt các vị thế lỗ nặng.")
        
        if losing_ratio > 0.7:
            recommendations.append("❗ Hơn 70% vị thế đang lỗ. Nên tạm dừng mở thêm vị thế mới.")
        elif losing_ratio > 0.5:
            recommendations.append("⚠️ Hơn 50% vị thế đang lỗ. Thận trọng với việc mở thêm vị thế mới.")
        
        if self._has_concentration_risk():
            recommendations.append("⚠️ Rủi ro tập trung: Có vị thế chiếm tỷ trọng quá lớn trong danh mục.")
        
        if profitable_positions and losing_positions:
            recommendations.append("💡 Có thể chốt lời các vị thế đang lãi để bù đắp các vị thế đang lỗ.")
        
        if len(self.positions) > self.config['risk_management']['max_positions']:
            recommendations.append(f"⚠️ Số lượng vị thế vượt quá giới hạn đã đặt ({self.config['risk_management']['max_positions']}).")
        
        if not recommendations:
            recommendations.append("✅ Danh mục hiện tại đang có rủi ro thấp, có thể tiếp tục giao dịch bình thường.")
            
        return recommendations
    
    def _get_market_data(self, symbol: str) -> Dict:
        """
        Lấy dữ liệu thị trường cho một symbol
        
        Args:
            symbol (str): Mã cặp giao dịch
            
        Returns:
            Dict: Dữ liệu thị trường
        """
        # Trong triển khai thực tế, nên gọi đến market_analyzer để lấy dữ liệu
        if self.market_analyzer:
            # return self.market_analyzer.get_market_data(symbol)
            pass
        
        # Dữ liệu mẫu cho môi trường demo
        return {
            'symbol': symbol,
            'current_price': 38000 if symbol == 'BTCUSDT' else 2300,
            'daily_change_percent': 2.5 if symbol == 'BTCUSDT' else -1.2,
            'volume': 10000000,
            'atr': 1200 if symbol == 'BTCUSDT' else 80,
            'rsi': 65 if symbol == 'BTCUSDT' else 45,
            'trend': 'uptrend' if symbol == 'BTCUSDT' else 'downtrend',
            'support_levels': [37000, 36000, 35000] if symbol == 'BTCUSDT' else [2200, 2100, 2000],
            'resistance_levels': [39000, 40000, 41000] if symbol == 'BTCUSDT' else [2400, 2500, 2600],
            'volatility': 'medium' if symbol == 'BTCUSDT' else 'high'
        }
    
    def _analyze_market_condition(self, market_data: Dict) -> Dict:
        """
        Phân tích điều kiện thị trường
        
        Args:
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict: Kết quả phân tích điều kiện thị trường
        """
        return {
            'trend': market_data.get('trend', 'neutral'),
            'strength': 'medium',
            'volatility': market_data.get('volatility', 'medium'),
            'momentum': 'positive' if market_data.get('rsi', 50) > 50 else 'negative',
            'support': market_data.get('support_levels', [])[0] if market_data.get('support_levels') else None,
            'resistance': market_data.get('resistance_levels', [])[0] if market_data.get('resistance_levels') else None
        }
    
    def _calculate_risk_level(self, position: Dict, market_data: Dict) -> str:
        """
        Tính toán mức độ rủi ro của vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            str: Mức độ rủi ro ('low', 'medium', 'high', 'very_high')
        """
        risk_score = 0
        
        # 1. Mức độ lỗ
        if position['pnl_percent'] < -10:
            risk_score += 3
        elif position['pnl_percent'] < -5:
            risk_score += 2
        elif position['pnl_percent'] < 0:
            risk_score += 1
        
        # 2. Đòn bẩy cao
        if position['leverage'] > 10:
            risk_score += 3
        elif position['leverage'] > 5:
            risk_score += 2
        elif position['leverage'] > 2:
            risk_score += 1
        
        # 3. Vị thế đi ngược xu hướng
        if ((position['type'] == 'LONG' and market_data.get('trend') == 'downtrend') or
            (position['type'] == 'SHORT' and market_data.get('trend') == 'uptrend')):
            risk_score += 2
        
        # 4. Biến động thị trường cao
        if market_data.get('volatility') == 'high':
            risk_score += 2
        elif market_data.get('volatility') == 'very_high':
            risk_score += 3
        
        # Đánh giá mức độ rủi ro
        if risk_score >= 8:
            return 'very_high'
        elif risk_score >= 5:
            return 'high'
        elif risk_score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendation(self, position: Dict, market_data: Dict) -> Dict:
        """
        Đưa ra khuyến nghị cho vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict: Khuyến nghị cho vị thế
        """
        risk_level = self._calculate_risk_level(position, market_data)
        action = ''
        reason = ''
        
        # Dựa vào lợi nhuận
        if position['pnl_percent'] > 15:
            action = 'CLOSE'
            reason = 'Vị thế đã đạt lợi nhuận trên 15%, nên chốt lời'
        elif position['pnl_percent'] > 10:
            action = 'PARTIAL_CLOSE'
            reason = 'Vị thế đã đạt lợi nhuận trên 10%, nên chốt một phần'
        elif position['pnl_percent'] > 5:
            action = 'MOVE_SL'
            reason = 'Vị thế đã có lời, nên điều chỉnh stop loss để bảo vệ lợi nhuận'
        elif position['pnl_percent'] < -10:
            action = 'CLOSE'
            reason = 'Vị thế đang lỗ trên 10%, nên cắt lỗ để hạn chế thiệt hại'
        elif position['pnl_percent'] < -7 and risk_level == 'high':
            action = 'CLOSE'
            reason = 'Vị thế đang lỗ và có rủi ro cao, nên cắt lỗ'
        elif position['pnl_percent'] < -5:
            action = 'WATCH'
            reason = 'Vị thế đang lỗ, cần theo dõi chặt chẽ'
        else:
            action = 'HOLD'
            reason = 'Vị thế đang trong khoảng an toàn, giữ nguyên'
        
        # Xét thêm điều kiện thị trường
        market_condition = self._analyze_market_condition(market_data)
        
        # Nếu vị thế đi ngược xu hướng mạnh
        if ((position['type'] == 'LONG' and market_condition['trend'] == 'downtrend' and market_condition['strength'] == 'strong') or
            (position['type'] == 'SHORT' and market_condition['trend'] == 'uptrend' and market_condition['strength'] == 'strong')):
            if action != 'CLOSE':
                action = 'WATCH' if position['pnl_percent'] > 0 else 'CONSIDER_CLOSE'
                reason += '. Vị thế đang đi ngược xu hướng thị trường mạnh'
        
        return {
            'action': action,
            'reason': reason,
            'risk_level': risk_level
        }
    
    def _calculate_stop_loss_levels(self, position: Dict, market_data: Dict) -> List[Dict]:
        """
        Tính toán các mức stop loss được đề xuất
        
        Args:
            position (Dict): Thông tin vị thế
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            List[Dict]: Danh sách các mức stop loss được đề xuất
        """
        stop_loss_levels = []
        current_price = position['current_price']
        entry_price = position['entry_price']
        atr = market_data.get('atr', current_price * 0.02)  # Mặc định 2% nếu không có ATR
        
        # Mức stop loss dựa trên ATR
        atr_multipliers = [1, 1.5, 2, 3]
        
        for multiplier in atr_multipliers:
            sl_price = 0
            risk_percent = 0
            
            if position['type'] == 'LONG':
                sl_price = current_price - (atr * multiplier)
                if sl_price <= 0:
                    continue
                risk_percent = ((current_price - sl_price) / current_price) * 100 * position['leverage']
            else:  # SHORT
                sl_price = current_price + (atr * multiplier)
                risk_percent = ((sl_price - current_price) / current_price) * 100 * position['leverage']
            
            stop_loss_levels.append({
                'price': sl_price,
                'risk_percent': risk_percent,
                'type': f'ATR x{multiplier}',
                'description': f'Dựa trên {multiplier}x ATR (${atr:.2f})'
            })
        
        # Mức stop loss dựa trên điểm hỗ trợ/kháng cự
        if position['type'] == 'LONG' and market_data.get('support_levels'):
            for i, support in enumerate(market_data['support_levels']):
                if support < current_price:
                    risk_percent = ((current_price - support) / current_price) * 100 * position['leverage']
                    stop_loss_levels.append({
                        'price': support,
                        'risk_percent': risk_percent,
                        'type': f'Support {i+1}',
                        'description': f'Dựa trên mức hỗ trợ ${support:.2f}'
                    })
        
        if position['type'] == 'SHORT' and market_data.get('resistance_levels'):
            for i, resistance in enumerate(market_data['resistance_levels']):
                if resistance > current_price:
                    risk_percent = ((resistance - current_price) / current_price) * 100 * position['leverage']
                    stop_loss_levels.append({
                        'price': resistance,
                        'risk_percent': risk_percent,
                        'type': f'Resistance {i+1}',
                        'description': f'Dựa trên mức kháng cự ${resistance:.2f}'
                    })
        
        # Sắp xếp theo mức rủi ro tăng dần
        stop_loss_levels.sort(key=lambda x: x['risk_percent'])
        
        return stop_loss_levels
    
    def _calculate_take_profit_levels(self, position: Dict, market_data: Dict) -> List[Dict]:
        """
        Tính toán các mức take profit được đề xuất
        
        Args:
            position (Dict): Thông tin vị thế
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            List[Dict]: Danh sách các mức take profit được đề xuất
        """
        take_profit_levels = []
        current_price = position['current_price']
        entry_price = position['entry_price']
        atr = market_data.get('atr', current_price * 0.02)  # Mặc định 2% nếu không có ATR
        
        # Mức take profit dựa trên R:R (risk-reward ratio)
        risk_reward_ratios = [1, 1.5, 2, 3, 5]
        
        # Nếu có stop loss, sử dụng làm cơ sở cho R:R
        if position['stop_loss']:
            risk = abs(entry_price - position['stop_loss'])
            
            for rr in risk_reward_ratios:
                tp_price = 0
                profit_percent = 0
                
                if position['type'] == 'LONG':
                    tp_price = entry_price + (risk * rr)
                    profit_percent = ((tp_price - current_price) / current_price) * 100 * position['leverage']
                else:  # SHORT
                    tp_price = entry_price - (risk * rr)
                    if tp_price <= 0:
                        continue
                    profit_percent = ((current_price - tp_price) / current_price) * 100 * position['leverage']
                
                take_profit_levels.append({
                    'price': tp_price,
                    'profit_percent': profit_percent,
                    'type': f'R:R {rr}',
                    'description': f'Dựa trên tỷ lệ risk-reward {rr}:1'
                })
        
        # Mức take profit dựa trên ATR
        atr_multipliers = [2, 3, 5, 8]
        
        for multiplier in atr_multipliers:
            tp_price = 0
            profit_percent = 0
            
            if position['type'] == 'LONG':
                tp_price = current_price + (atr * multiplier)
                profit_percent = ((tp_price - current_price) / current_price) * 100 * position['leverage']
            else:  # SHORT
                tp_price = current_price - (atr * multiplier)
                if tp_price <= 0:
                    continue
                profit_percent = ((current_price - tp_price) / current_price) * 100 * position['leverage']
            
            take_profit_levels.append({
                'price': tp_price,
                'profit_percent': profit_percent,
                'type': f'ATR x{multiplier}',
                'description': f'Dựa trên {multiplier}x ATR (${atr:.2f})'
            })
        
        # Mức take profit dựa trên điểm kháng cự/hỗ trợ
        if position['type'] == 'LONG' and market_data.get('resistance_levels'):
            for i, resistance in enumerate(market_data['resistance_levels']):
                if resistance > current_price:
                    profit_percent = ((resistance - current_price) / current_price) * 100 * position['leverage']
                    take_profit_levels.append({
                        'price': resistance,
                        'profit_percent': profit_percent,
                        'type': f'Resistance {i+1}',
                        'description': f'Dựa trên mức kháng cự ${resistance:.2f}'
                    })
        
        if position['type'] == 'SHORT' and market_data.get('support_levels'):
            for i, support in enumerate(market_data['support_levels']):
                if support < current_price:
                    profit_percent = ((current_price - support) / current_price) * 100 * position['leverage']
                    take_profit_levels.append({
                        'price': support,
                        'profit_percent': profit_percent,
                        'type': f'Support {i+1}',
                        'description': f'Dựa trên mức hỗ trợ ${support:.2f}'
                    })
        
        # Sắp xếp theo mức lợi nhuận tăng dần
        take_profit_levels.sort(key=lambda x: x['profit_percent'])
        
        return take_profit_levels
    
    def _estimate_target_time(self, position: Dict, market_data: Dict) -> Dict:
        """
        Ước tính thời gian để đạt mục tiêu
        
        Args:
            position (Dict): Thông tin vị thế
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict: Thời gian ước tính
        """
        # Mô phỏng đơn giản, trong thực tế cần thuật toán phức tạp hơn
        if not position.get('take_profit'):
            return {
                'estimate': 'unknown',
                'message': 'Không thể ước tính do chưa đặt take profit'
            }
        
        price_diff = abs(position['take_profit'] - position['current_price'])
        current_price = position['current_price']
        
        # Giả định biến động giá trung bình mỗi ngày là 2%
        avg_daily_change = current_price * 0.02
        
        # Ước tính số ngày cần thiết
        days_needed = price_diff / avg_daily_change
        
        # Chia thành các khoảng thời gian
        if days_needed < 1:
            hours_needed = days_needed * 24
            if hours_needed < 1:
                return {
                    'estimate': 'very_short',
                    'message': 'Có thể đạt trong vài phút tới 1 giờ'
                }
            else:
                return {
                    'estimate': 'short',
                    'message': f'Khoảng {int(hours_needed)} giờ'
                }
        elif days_needed < 3:
            return {
                'estimate': 'medium',
                'message': f'Khoảng {int(days_needed)} ngày'
            }
        elif days_needed < 7:
            return {
                'estimate': 'long',
                'message': 'Khoảng 3-7 ngày'
            }
        else:
            return {
                'estimate': 'very_long',
                'message': 'Trên 1 tuần'
            }
    
    def _analyze_probability(self, position: Dict, market_data: Dict) -> Dict:
        """
        Phân tích xác suất thành công của vị thế
        
        Args:
            position (Dict): Thông tin vị thế
            market_data (Dict): Dữ liệu thị trường
            
        Returns:
            Dict: Phân tích xác suất
        """
        success_probability = 0.5  # Mặc định 50%
        
        # Điều chỉnh dựa trên xu hướng
        if ((position['type'] == 'LONG' and market_data.get('trend') == 'uptrend') or
            (position['type'] == 'SHORT' and market_data.get('trend') == 'downtrend')):
            success_probability += 0.1
        elif ((position['type'] == 'LONG' and market_data.get('trend') == 'downtrend') or
              (position['type'] == 'SHORT' and market_data.get('trend') == 'uptrend')):
            success_probability -= 0.1
        
        # Điều chỉnh dựa trên RSI
        rsi = market_data.get('rsi', 50)
        if position['type'] == 'LONG':
            if rsi < 30:  # Quá bán
                success_probability += 0.1
            elif rsi > 70:  # Quá mua
                success_probability -= 0.1
        else:  # SHORT
            if rsi > 70:  # Quá mua
                success_probability += 0.1
            elif rsi < 30:  # Quá bán
                success_probability -= 0.1
        
        # Điều chỉnh dựa trên P&L hiện tại
        if position['pnl_percent'] > 5:
            success_probability += 0.05
        elif position['pnl_percent'] < -5:
            success_probability -= 0.05
        
        # Giới hạn xác suất trong khoảng 0.1-0.9
        success_probability = max(0.1, min(0.9, success_probability))
        
        # Định nghĩa các khoảng xác suất
        probability_level = 'medium'
        if success_probability >= 0.7:
            probability_level = 'high'
        elif success_probability <= 0.3:
            probability_level = 'low'
        
        return {
            'success_probability': success_probability,
            'level': probability_level,
            'message': f'Xác suất thành công: {int(success_probability * 100)}%'
        }
    
    def get_account_summary(self) -> Dict:
        """
        Lấy tóm tắt về tài khoản
        
        Returns:
            Dict: Tóm tắt tài khoản
        """
        try:
            if self.binance_api:
                # Gọi API Binance để lấy thông tin tài khoản futures
                account_info = self.binance_api.get_futures_account()
                
                # Tính toán các thông số
                total_balance = float(account_info.get('totalWalletBalance', 0))
                available_balance = float(account_info.get('availableBalance', 0))
                total_margin = float(account_info.get('totalMarginBalance', 0))
                
                # Tổng lợi nhuận chưa thực hiện
                unrealized_pnl = sum(float(p.get('unRealizedProfit', 0)) for p in account_info.get('positions', [])
                                   if float(p.get('positionAmt', 0)) != 0)
                
                # Tính margin đang sử dụng và tỷ lệ margin
                used_margin = total_margin - available_balance
                margin_ratio = (used_margin / total_margin) * 100 if total_margin > 0 else 0
                
                return {
                    'total_balance': total_balance,
                    'available_balance': available_balance,
                    'used_margin': used_margin,
                    'margin_ratio': margin_ratio,
                    'unrealized_pnl': unrealized_pnl,
                    'position_count': len([p for p in account_info.get('positions', []) 
                                         if float(p.get('positionAmt', 0)) != 0])
                }
            else:
                # Trả về dữ liệu giả lập
                return self._get_demo_account_summary()
        except Exception as e:
            logger.error(f"Lỗi khi lấy tóm tắt tài khoản: {str(e)}")
            return self._get_demo_account_summary()
    
    def _get_demo_account_summary(self) -> Dict:
        """
        Trả về tóm tắt tài khoản giả lập
        
        Returns:
            Dict: Tóm tắt tài khoản giả lập
        """
        return {
            'total_balance': 1000.0,
            'available_balance': 850.0,
            'used_margin': 150.0,
            'margin_ratio': 15.0,
            'unrealized_pnl': 25.0,
            'position_count': len(self.positions)
        }
    
    def get_performance_metrics(self) -> Dict:
        """
        Lấy các chỉ số hiệu suất của việc quản lý vị thế
        
        Returns:
            Dict: Các chỉ số hiệu suất
        """
        if not self.position_history:
            return {
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'expectancy': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'avg_holding_time': '0h',
                'total_trades': 0
            }
        
        winning_trades = [p for p in self.position_history if p['final_pnl'] > 0]
        losing_trades = [p for p in self.position_history if p['final_pnl'] <= 0]
        
        total_trades = len(self.position_history)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        avg_profit = sum(p['final_pnl'] for p in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(p['final_pnl'] for p in losing_trades) / len(losing_trades) if losing_trades else 0
        
        total_profit = sum(p['final_pnl'] for p in winning_trades)
        total_loss = abs(sum(p['final_pnl'] for p in losing_trades))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        expectancy = (win_rate * avg_profit) - ((1 - win_rate) * abs(avg_loss)) if total_trades > 0 else 0
        
        best_trade = max([p['final_pnl'] for p in self.position_history]) if self.position_history else 0
        worst_trade = min([p['final_pnl'] for p in self.position_history]) if self.position_history else 0
        
        # Tính thời gian giữ vị thế trung bình
        avg_holding_time = '0h'  # Triển khai sau khi có dữ liệu thời gian đầy đủ
        
        return {
            'win_rate': win_rate * 100,  # Chuyển sang phần trăm
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_holding_time': avg_holding_time,
            'total_trades': total_trades
        }

def main():
    """Hàm chính để test PositionManager"""
    position_manager = PositionManager()
    
    # Quét vị thế đang mở
    open_positions = position_manager.scan_open_positions()
    print(f"Đã quét được {len(open_positions)} vị thế đang mở:")
    for pos in open_positions:
        print(f"  - {pos['symbol']} {pos['type']}: {pos['pnl_percent']:.2f}%")
    
    # Phân tích một vị thế
    if open_positions:
        position_id = open_positions[0]['id']
        analysis = position_manager.analyze_position(position_id)
        print(f"\nPhân tích vị thế {position_id}:")
        print(f"  - Khuyến nghị: {analysis['recommended_action']['action']} - {analysis['recommended_action']['reason']}")
        print(f"  - Mức độ rủi ro: {analysis['risk_level']}")
    
    # Phân tích danh mục
    portfolio_analysis = position_manager._analyze_portfolio()
    print("\nPhân tích danh mục:")
    print(f"  - Số lượng vị thế: {portfolio_analysis['total_positions']}")
    print(f"  - Tổng P&L: {portfolio_analysis['total_pnl']:.2f}")
    print(f"  - Mức độ rủi ro: {portfolio_analysis['risk_level']}")
    
    for rec in portfolio_analysis['recommendations']:
        print(f"  - {rec}")
    
    # Lấy tóm tắt tài khoản
    account_summary = position_manager.get_account_summary()
    print("\nTóm tắt tài khoản:")
    print(f"  - Số dư: {account_summary['total_balance']:.2f} USDT")
    print(f"  - Số dư khả dụng: {account_summary['available_balance']:.2f} USDT")
    print(f"  - Tỷ lệ margin: {account_summary['margin_ratio']:.2f}%")

if __name__ == "__main__":
    main()