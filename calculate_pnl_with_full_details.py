#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tính toán lợi nhuận chính xác với đầy đủ chi tiết (Calculate PnL with Full Details)

Module này cung cấp các công cụ để tính toán chính xác lợi nhuận/lỗ của giao dịch,
bao gồm phí giao dịch, phí funding, và xử lý các trường hợp đặc biệt như đóng vị thế từng phần.
"""

import os
import sys
import json
import time
import logging
import datetime
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pnl_calculator.log')
    ]
)
logger = logging.getLogger('pnl_calculator')

# Thêm thư mục gốc vào sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import các module cần thiết
try:
    from binance_api import BinanceAPI
except ImportError:
    logger.error("Không thể import module binance_api. Hãy đảm bảo bạn đang chạy từ thư mục gốc.")
    binance_api_available = False
else:
    binance_api_available = True

class PnLCalculator:
    """Lớp tính toán lợi nhuận/lỗ chính xác với đầy đủ chi tiết"""
    
    def __init__(self, binance_api: Optional[Any] = None, cache_funding_rates: bool = True,
                funding_cache_file: str = 'funding_rates_cache.json'):
        """
        Khởi tạo PnL Calculator
        
        Args:
            binance_api: Đối tượng BinanceAPI đã được khởi tạo
            cache_funding_rates: Có lưu cache funding rates hay không
            funding_cache_file: Đường dẫn file cache funding rates
        """
        self.binance_api = binance_api
        self.cache_funding_rates = cache_funding_rates
        self.funding_cache_file = funding_cache_file
        self.funding_rates_cache = {}
        
        if self.cache_funding_rates:
            self._load_funding_rates_cache()
    
    def _load_funding_rates_cache(self) -> None:
        """Tải cache funding rates từ file"""
        try:
            if os.path.exists(self.funding_cache_file):
                with open(self.funding_cache_file, 'r') as f:
                    self.funding_rates_cache = json.load(f)
                logger.info(f"Đã tải funding rates cache từ {self.funding_cache_file}")
        except Exception as e:
            logger.error(f"Lỗi khi tải funding rates cache: {str(e)}")
            self.funding_rates_cache = {}
    
    def _save_funding_rates_cache(self) -> None:
        """Lưu cache funding rates vào file"""
        try:
            with open(self.funding_cache_file, 'w') as f:
                json.dump(self.funding_rates_cache, f, indent=4)
            logger.info(f"Đã lưu funding rates cache vào {self.funding_cache_file}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu funding rates cache: {str(e)}")

    def get_funding_rates(self, symbol: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Lấy funding rates trong khoảng thời gian cho một cặp giao dịch
        
        Args:
            symbol: Cặp giao dịch
            start_time: Thời gian bắt đầu (unix timestamp ms)
            end_time: Thời gian kết thúc (unix timestamp ms)
            
        Returns:
            List[Dict]: Danh sách funding rates
        """
        if not self.binance_api:
            logger.warning("BinanceAPI không được cung cấp, không thể lấy funding rates từ API")
            return []
        
        # Kiểm tra cache
        cache_key = f"{symbol}_{start_time}_{end_time}"
        if self.cache_funding_rates and cache_key in self.funding_rates_cache:
            logger.info(f"Đã lấy funding rates từ cache cho {symbol}")
            return self.funding_rates_cache[cache_key]
        
        # Lấy từ API
        try:
            # Chuyển đổi timestamp sang ms nếu cần
            if start_time < 10**12:  # Nếu không phải timestamp ms
                start_time *= 1000
            if end_time < 10**12:
                end_time *= 1000
                
            funding_rates = self.binance_api.get_funding_rate_history(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                limit=1000  # Maximum allowed by Binance
            )
            
            # Lưu vào cache
            if self.cache_funding_rates:
                self.funding_rates_cache[cache_key] = funding_rates
                self._save_funding_rates_cache()
                
            return funding_rates
        except Exception as e:
            logger.error(f"Lỗi khi lấy funding rates cho {symbol}: {str(e)}")
            return []

    def calculate_funding_payment(self, symbol: str, position_value: float, 
                               entry_time: int, exit_time: int, position_side: str) -> float:
        """
        Tính toán tổng funding payment cho một vị thế
        
        Args:
            symbol: Cặp giao dịch
            position_value: Giá trị vị thế (giá * số lượng * đòn bẩy)
            entry_time: Thời gian vào lệnh (unix timestamp ms)
            exit_time: Thời gian thoát lệnh (unix timestamp ms)
            position_side: Hướng vị thế ('LONG' hoặc 'SHORT')
            
        Returns:
            float: Tổng funding payment (dương: trả, âm: nhận)
        """
        funding_rates = self.get_funding_rates(symbol, entry_time, exit_time)
        total_payment = 0.0
        
        for rate_info in funding_rates:
            rate = float(rate_info['fundingRate'])
            
            # Đối với vị thế LONG, rate > 0 nghĩa là trả, rate < 0 nghĩa là nhận
            # Đối với vị thế SHORT, ngược lại
            if position_side == 'LONG':
                payment = position_value * rate
            else:  # SHORT
                payment = position_value * (-rate)
                
            total_payment += payment
            
        logger.info(f"Tổng funding payment cho {symbol} ({position_side}): {total_payment:.6f} USDT")
        return total_payment

    def calculate_pnl_with_full_details(
        self, entry_price: float, exit_price: float, position_size: float, 
        leverage: int = 1, position_side: str = 'LONG',
        open_fee_rate: float = 0.0004, close_fee_rate: float = 0.0004,
        entry_time: int = None, exit_time: int = None, symbol: str = None,
        partial_exits: List[Tuple[float, float]] = None
    ) -> Dict:
        """
        Tính toán PnL đầy đủ chi tiết cho một giao dịch
        
        Args:
            entry_price: Giá vào lệnh
            exit_price: Giá thoát lệnh cuối cùng (nếu partial_exits=None)
            position_size: Số lượng
            leverage: Đòn bẩy
            position_side: Hướng vị thế ('LONG' hoặc 'SHORT')
            open_fee_rate: Phí mở vị thế
            close_fee_rate: Phí đóng vị thế
            entry_time: Thời gian vào lệnh (unix timestamp ms)
            exit_time: Thời gian thoát lệnh (unix timestamp ms)
            symbol: Cặp giao dịch (cần cho funding rate)
            partial_exits: Danh sách các lần đóng một phần [(giá, số lượng),...]
            
        Returns:
            Dict: Chi tiết PnL và các thành phần
        """
        # Kiểm tra dữ liệu đầu vào
        if entry_price <= 0 or (exit_price <= 0 and not partial_exits):
            logger.error("Giá vào/ra không hợp lệ")
            return {"error": "Giá vào/ra không hợp lệ"}
            
        if position_size <= 0:
            logger.error("Số lượng không hợp lệ")
            return {"error": "Số lượng không hợp lệ"}
            
        if leverage < 1:
            logger.error("Đòn bẩy không hợp lệ")
            return {"error": "Đòn bẩy không hợp lệ"}
            
        if position_side not in ['LONG', 'SHORT']:
            logger.error("Hướng vị thế không hợp lệ")
            return {"error": "Hướng vị thế không hợp lệ"}
        
        # Tính toán giá trị vị thế và margin
        position_value = entry_price * position_size  # Notional value
        margin = position_value / leverage  # Số tiền thực tế sử dụng
        
        # Tính phí mở vị thế
        open_fee = position_value * open_fee_rate
        
        # Tính PnL từ giá
        if partial_exits:
            # Xử lý đóng từng phần
            remaining_size = position_size
            close_fee = 0.0
            realized_pnl = 0.0
            
            for exit_px, exit_size in partial_exits:
                if exit_size > remaining_size:
                    exit_size = remaining_size  # Đảm bảo không đóng nhiều hơn số lượng còn lại
                
                part_value = exit_px * exit_size
                
                # Tính PnL cho phần này
                if position_side == 'LONG':
                    part_pnl = exit_size * (exit_px - entry_price) * leverage
                else:  # SHORT
                    part_pnl = exit_size * (entry_price - exit_px) * leverage
                
                realized_pnl += part_pnl
                close_fee += part_value * close_fee_rate
                remaining_size -= exit_size
                
                if remaining_size <= 0:
                    break
            
            # Phần còn lại (nếu có) sử dụng exit_price
            if remaining_size > 0 and exit_price > 0:
                final_part_value = exit_price * remaining_size
                
                if position_side == 'LONG':
                    final_part_pnl = remaining_size * (exit_price - entry_price) * leverage
                else:  # SHORT
                    final_part_pnl = remaining_size * (entry_price - exit_price) * leverage
                
                realized_pnl += final_part_pnl
                close_fee += final_part_value * close_fee_rate
        else:
            # Đóng toàn bộ một lần
            if position_side == 'LONG':
                realized_pnl = position_size * (exit_price - entry_price) * leverage
            else:  # SHORT
                realized_pnl = position_size * (entry_price - exit_price) * leverage
            
            close_fee = exit_price * position_size * close_fee_rate
        
        # Tính funding payment nếu có đủ thông tin
        funding_payment = 0.0
        if all([entry_time, exit_time, symbol]) and self.binance_api:
            funding_payment = self.calculate_funding_payment(
                symbol=symbol,
                position_value=position_value,
                entry_time=entry_time,
                exit_time=exit_time,
                position_side=position_side
            )
        
        # Tổng PnL và ROI
        total_fees = open_fee + close_fee
        net_pnl = realized_pnl - total_fees - funding_payment
        roi_percent = (net_pnl / margin) * 100 if margin > 0 else 0
        
        result = {
            'entry_price': entry_price,
            'exit_price': exit_price if not partial_exits else None,
            'position_size': position_size,
            'leverage': leverage,
            'position_side': position_side,
            'position_value': position_value,
            'margin': margin,
            'realized_pnl': realized_pnl,
            'open_fee': open_fee,
            'close_fee': close_fee,
            'total_fees': total_fees,
            'funding_payment': funding_payment,
            'net_pnl': net_pnl,
            'roi_percent': roi_percent,
            'partial_exits': partial_exits,
            'remaining_size': remaining_size if partial_exits else 0,
            'pnl_components': {
                'price_pnl': realized_pnl,
                'fees': -total_fees,
                'funding': -funding_payment
            },
            'pnl_components_percentage': {
                'price_pnl': (realized_pnl / margin) * 100 if margin > 0 else 0,
                'fees': (-total_fees / margin) * 100 if margin > 0 else 0,
                'funding': (-funding_payment / margin) * 100 if margin > 0 else 0
            }
        }
        
        logger.info(f"PnL chi tiết cho {symbol}: {json.dumps(result, indent=2)}")
        return result

    def calculate_pnl_for_trade_history(self, trade_history: List[Dict]) -> Dict:
        """
        Tính PnL cho lịch sử giao dịch
        
        Args:
            trade_history: Danh sách các giao dịch
            
        Returns:
            Dict: Tổng hợp PnL và chi tiết
        """
        total_pnl = 0.0
        total_margin = 0.0
        trade_details = []
        
        for trade in trade_history:
            # Kiểm tra và lấy các thông tin cần thiết
            if not all(k in trade for k in ['symbol', 'entry_price', 'exit_price', 'position_size', 'leverage']):
                logger.warning(f"Bỏ qua giao dịch thiếu thông tin: {trade}")
                continue
                
            # Xác định các tham số bổ sung
            partial_exits = trade.get('partial_exits', None)
            entry_time = trade.get('entry_time', None)
            exit_time = trade.get('exit_time', None)
            position_side = trade.get('position_side', 'LONG')
            
            # Tính PnL
            pnl_result = self.calculate_pnl_with_full_details(
                entry_price=trade['entry_price'],
                exit_price=trade['exit_price'],
                position_size=trade['position_size'],
                leverage=trade['leverage'],
                position_side=position_side,
                entry_time=entry_time,
                exit_time=exit_time,
                symbol=trade['symbol'],
                partial_exits=partial_exits
            )
            
            if 'error' in pnl_result:
                logger.warning(f"Lỗi khi tính PnL cho giao dịch: {pnl_result['error']}")
                continue
                
            total_pnl += pnl_result['net_pnl']
            total_margin += pnl_result['margin']
            
            trade_details.append({
                'trade_id': trade.get('trade_id', f"trade_{len(trade_details)}"),
                'symbol': trade['symbol'],
                'position_side': position_side,
                'entry_time': datetime.datetime.fromtimestamp(entry_time/1000).strftime('%Y-%m-%d %H:%M:%S') if entry_time else None,
                'exit_time': datetime.datetime.fromtimestamp(exit_time/1000).strftime('%Y-%m-%d %H:%M:%S') if exit_time else None,
                'duration_hours': (exit_time - entry_time) / (1000 * 3600) if entry_time and exit_time else None,
                'pnl': pnl_result
            })
        
        overall_roi = (total_pnl / total_margin) * 100 if total_margin > 0 else 0
        
        return {
            'total_pnl': total_pnl,
            'total_margin': total_margin,
            'overall_roi_percent': overall_roi,
            'trade_count': len(trade_details),
            'average_pnl_per_trade': total_pnl / len(trade_details) if trade_details else 0,
            'trade_details': trade_details
        }

    def analyze_position_exit_scenarios(
        self, current_price: float, entry_price: float, position_size: float,
        leverage: int, position_side: str, entry_time: int, symbol: str,
        target_prices: List[float] = None, time_horizons: List[int] = None
    ) -> Dict:
        """
        Phân tích các kịch bản thoát vị thế ở các mức giá khác nhau
        
        Args:
            current_price: Giá hiện tại
            entry_price: Giá vào lệnh
            position_size: Số lượng
            leverage: Đòn bẩy
            position_side: Hướng vị thế ('LONG' hoặc 'SHORT')
            entry_time: Thời gian vào lệnh (unix timestamp ms)
            symbol: Cặp giao dịch
            target_prices: Danh sách các mức giá thoát cần phân tích
            time_horizons: Danh sách các mốc thời gian cần phân tích (giờ)
            
        Returns:
            Dict: Phân tích các kịch bản thoát vị thế
        """
        if not target_prices:
            # Tạo các mức giá mặc định dựa trên giá hiện tại
            price_changes = [-0.1, -0.05, -0.02, -0.01, 0.01, 0.02, 0.05, 0.1]
            target_prices = [current_price * (1 + change) for change in price_changes]
            
        if not time_horizons:
            # Mặc định: 1 giờ, 8 giờ, 24 giờ, 3 ngày, 7 ngày
            time_horizons = [1, 8, 24, 72, 168]
            
        now = int(time.time() * 1000)
        
        scenarios = []
        for target_price in target_prices:
            # Tính % thay đổi từ giá hiện tại
            price_change_pct = (target_price - current_price) / current_price * 100
            
            for horizon in time_horizons:
                # Tính thời gian thoát
                exit_time = now + horizon * 3600 * 1000  # chuyển giờ thành ms
                
                # Tính PnL cho kịch bản này
                pnl_result = self.calculate_pnl_with_full_details(
                    entry_price=entry_price,
                    exit_price=target_price,
                    position_size=position_size,
                    leverage=leverage,
                    position_side=position_side,
                    entry_time=entry_time,
                    exit_time=exit_time,
                    symbol=symbol
                )
                
                if 'error' in pnl_result:
                    continue
                    
                scenarios.append({
                    'target_price': target_price,
                    'price_change_pct': price_change_pct,
                    'time_horizon_hours': horizon,
                    'exit_time': datetime.datetime.fromtimestamp(exit_time/1000).strftime('%Y-%m-%d %H:%M:%S'),
                    'net_pnl': pnl_result['net_pnl'],
                    'roi_percent': pnl_result['roi_percent'],
                    'details': pnl_result
                })
                
        return {
            'current_price': current_price,
            'entry_price': entry_price,
            'current_unrealized_pnl': self.calculate_pnl_with_full_details(
                entry_price=entry_price,
                exit_price=current_price,
                position_size=position_size,
                leverage=leverage,
                position_side=position_side,
                entry_time=entry_time,
                exit_time=now,
                symbol=symbol
            )['net_pnl'],
            'scenarios': sorted(scenarios, key=lambda x: x['roi_percent'], reverse=True)
        }


def main():
    """Hàm chính để test PnLCalculator"""
    from binance_api import BinanceAPI
    
    # Khởi tạo BinanceAPI
    binance_api = BinanceAPI()
    
    # Khởi tạo PnLCalculator
    calculator = PnLCalculator(binance_api=binance_api)
    
    # Ví dụ tính PnL đơn giản
    result = calculator.calculate_pnl_with_full_details(
        entry_price=84089.33,
        exit_price=89776.9,
        position_size=0.09,
        leverage=5,
        position_side='LONG',
        symbol='BTCUSDT',
        entry_time=int(time.time() * 1000) - 3600000,  # 1 giờ trước
        exit_time=int(time.time() * 1000)
    )
    
    print("\n=== Ví dụ tính PnL chi tiết ===")
    print(json.dumps(result, indent=2))
    
    # Ví dụ tính PnL với đóng vị thế từng phần
    result_partial = calculator.calculate_pnl_with_full_details(
        entry_price=84089.33,
        exit_price=89776.9,
        position_size=0.09,
        leverage=5,
        position_side='LONG',
        symbol='BTCUSDT',
        entry_time=int(time.time() * 1000) - 3600000,
        exit_time=int(time.time() * 1000),
        partial_exits=[
            (86000, 0.03),  # Đóng 1/3 vị thế ở giá 86000
            (87500, 0.03)   # Đóng 1/3 vị thế ở giá 87500
        ]
    )
    
    print("\n=== Ví dụ tính PnL với đóng vị thế từng phần ===")
    print(json.dumps(result_partial, indent=2))
    
    # Ví dụ phân tích các kịch bản thoát vị thế
    scenarios = calculator.analyze_position_exit_scenarios(
        current_price=84500,
        entry_price=84089.33,
        position_size=0.09,
        leverage=5,
        position_side='LONG',
        entry_time=int(time.time() * 1000) - 3600000,
        symbol='BTCUSDT'
    )
    
    print("\n=== Ví dụ phân tích các kịch bản thoát vị thế ===")
    print(json.dumps(scenarios, indent=2))
    

if __name__ == "__main__":
    main()