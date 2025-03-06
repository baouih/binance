#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tool giám sát và quản lý tài khoản giao dịch nhỏ (dưới 200 USDT)

Script này cung cấp các tính năng đặc biệt để giám sát và quản lý các tài khoản giao dịch nhỏ,
đảm bảo tuân thủ các giới hạn về giá trị giao dịch tối thiểu của Binance Futures.
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/small_account_monitor.log'
)
logger = logging.getLogger('small_account_monitor')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

# Thêm thư mục gốc vào sys.path để import các module
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from binance_api import BinanceAPI
from profit_manager import ProfitManager
from dynamic_risk_allocator import DynamicRiskAllocator
from data_cache import DataCache
from auto_setup_sltp import setup_sltp_for_positions

class SmallAccountMonitor:
    """Lớp giám sát và quản lý tài khoản giao dịch nhỏ"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        """
        Khởi tạo monitor
        
        Args:
            api_key (str, optional): API key Binance
            api_secret (str, optional): API secret Binance
            testnet (bool): Sử dụng testnet hay không
        """
        self.binance_api = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=testnet)
        self.data_cache = DataCache()
        
        # Tải cấu hình
        self.risk_config = self._load_config('configs/risk_config.json')
        self.profit_config = self._load_config('configs/profit_manager_config.json')
        self.account_config = self._load_config('account_config.json')
        
        # Khởi tạo các đối tượng quản lý
        self.risk_allocator = DynamicRiskAllocator(data_cache=self.data_cache)
        self.risk_allocator.config = self.risk_config  # Gán cấu hình trực tiếp
        self.profit_manager = ProfitManager(config=self.profit_config, data_cache=self.data_cache)
        
        # Lấy cài đặt tài khoản nhỏ
        self.small_account_settings = self.risk_config.get('small_account_settings', {})
        self.preferred_symbols = self.small_account_settings.get('preferred_symbols', [])
        self.account_size_threshold = self.small_account_settings.get('account_size_threshold', 200.0)
        
        logger.info(f"Đã khởi tạo SmallAccountMonitor, testnet={testnet}")
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Tải cấu hình từ file
        
        Args:
            config_path (str): Đường dẫn đến file cấu hình
            
        Returns:
            Dict: Cấu hình đã tải
        """
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Không thể tải cấu hình từ {config_path}: {str(e)}")
            return {}
    
    def is_small_account(self) -> bool:
        """
        Kiểm tra xem tài khoản hiện tại có phải là tài khoản nhỏ không
        
        Returns:
            bool: True nếu là tài khoản nhỏ, False nếu không
        """
        account_balance = self.get_account_balance()
        return account_balance < self.account_size_threshold
    
    def get_account_balance(self) -> float:
        """
        Lấy số dư tài khoản
        
        Returns:
            float: Số dư tài khoản (USDT)
        """
        try:
            account_info = self.binance_api.get_futures_account()
            
            # Tìm USDT trong account info
            if isinstance(account_info, dict) and 'assets' in account_info:
                for asset in account_info['assets']:
                    if asset.get('asset') == 'USDT':
                        return float(asset.get('walletBalance', 0))
            
            return 0
        except Exception as e:
            logger.error(f"Lỗi khi lấy số dư tài khoản: {str(e)}")
            return 0
    
    def get_preferred_trading_symbols(self) -> List[str]:
        """
        Lấy danh sách các cặp tiền ưu tiên cho tài khoản nhỏ
        
        Returns:
            List[str]: Danh sách cặp tiền
        """
        if not self.preferred_symbols:
            return ["ADAUSDT", "DOGEUSDT", "MATICUSDT", "XRPUSDT", "ETHUSDT"]
        
        return self.preferred_symbols
    
    def get_open_positions(self) -> List[Dict]:
        """
        Lấy danh sách vị thế đang mở
        
        Returns:
            List[Dict]: Danh sách vị thế
        """
        try:
            positions = self.binance_api.futures_get_position()
            
            # Lọc các vị thế có amount != 0
            active_positions = []
            for position in positions:
                position_amt = float(position.get('positionAmt', 0))
                if abs(position_amt) > 0:
                    active_positions.append(position)
            
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi lấy danh sách vị thế: {str(e)}")
            return []
    
    def check_leverage_settings(self) -> Dict[str, bool]:
        """
        Kiểm tra và điều chỉnh cài đặt đòn bẩy cho các cặp tiền ưu tiên
        
        Returns:
            Dict[str, bool]: Kết quả điều chỉnh
        """
        results = {}
        preferred_symbols = self.get_preferred_trading_symbols()
        
        for symbol in preferred_symbols:
            try:
                # Lấy vị thế hiện tại để kiểm tra đòn bẩy
                position = self.binance_api.futures_get_position(symbol)
                current_leverage = int(position[0].get('leverage', 1)) if position else 1
                target_leverage = self._get_target_leverage(symbol)
                
                if current_leverage != target_leverage:
                    logger.info(f"Điều chỉnh đòn bẩy cho {symbol}: {current_leverage}x -> {target_leverage}x")
                    result = self.binance_api.futures_change_leverage(symbol, target_leverage)
                    if 'leverage' in result:
                        results[symbol] = True
                        logger.info(f"Đã điều chỉnh đòn bẩy cho {symbol} thành {target_leverage}x")
                    else:
                        results[symbol] = False
                        logger.error(f"Không thể điều chỉnh đòn bẩy cho {symbol}: {result}")
                else:
                    results[symbol] = True
                    logger.info(f"Đòn bẩy cho {symbol} đã đúng: {current_leverage}x")
            except Exception as e:
                results[symbol] = False
                logger.error(f"Lỗi khi kiểm tra/điều chỉnh đòn bẩy cho {symbol}: {str(e)}")
        
        return results
    
    def _get_target_leverage(self, symbol: str) -> int:
        """
        Lấy đòn bẩy mục tiêu cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            int: Đòn bẩy mục tiêu
        """
        if symbol == 'BTCUSDT':
            return self.small_account_settings.get('btc_leverage_adjustment', 20)
        elif symbol == 'ETHUSDT':
            return self.small_account_settings.get('eth_leverage_adjustment', 15)
        else:
            return self.small_account_settings.get('altcoin_leverage_adjustment', 10)
    
    def check_and_setup_sltp(self) -> Dict[str, bool]:
        """
        Kiểm tra và thiết lập SL/TP cho các vị thế đang mở
        
        Returns:
            Dict[str, bool]: Kết quả thiết lập
        """
        try:
            setup_sltp_for_positions(testnet=True)
            return {'success': True}
        except Exception as e:
            logger.error(f"Lỗi khi thiết lập SL/TP: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_market_data(self, symbol: str) -> Dict:
        """
        Lấy dữ liệu thị trường cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            Dict: Dữ liệu thị trường
        """
        try:
            ticker = self.binance_api.get_symbol_ticker(symbol)
            price = float(ticker.get('price', 0))
            
            # Lấy thêm dữ liệu 24h
            ticker_24h = self.binance_api.get_24h_ticker(symbol)
            
            volume_24h = float(ticker_24h.get('volume', 0)) * price
            price_change_24h = float(ticker_24h.get('priceChangePercent', 0))
            
            return {
                'symbol': symbol,
                'price': price,
                'volume_24h': volume_24h,
                'price_change_24h': price_change_24h,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu thị trường cho {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def calculate_optimal_position_size(self, symbol: str, risk_percentage: float = None) -> Dict:
        """
        Tính toán kích thước vị thế tối ưu cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            risk_percentage (float, optional): Phần trăm rủi ro
            
        Returns:
            Dict: Thông tin vị thế tối ưu
        """
        try:
            # Lấy giá hiện tại
            current_price = float(self.binance_api.get_symbol_ticker(symbol).get('price', 0))
            
            # Tính giá trị ATR
            atr_value = self._calculate_atr(symbol)
            
            # Tính giá stop loss
            if atr_value:
                atr_multiplier = self.risk_config.get('stop_loss', {}).get('atr_multiplier', 1.5)
                stop_loss = current_price * (1 - atr_value * atr_multiplier / current_price)
            else:
                # Nếu không có ATR, sử dụng % cố định
                sl_percent = self.risk_config.get('risk_levels', {}).get('medium', {}).get('risk_per_trade', 1.0)
                stop_loss = current_price * (1 - sl_percent / 100)
            
            # Lấy số dư tài khoản
            account_balance = self.get_account_balance()
            
            # Nếu không có risk_percentage, lấy từ cấu hình
            if not risk_percentage:
                base_risk = self.risk_config.get('base_risk_percentage', 1.0)
                adjustment = self.small_account_settings.get('risk_per_trade_adjustment', 0.7)
                risk_percentage = base_risk * adjustment
            
            # Tính toán kích thước vị thế
            position_info = self.risk_allocator.calculate_position_size_for_small_account(
                symbol, current_price, stop_loss, account_balance, risk_percentage
            )
            
            return position_info
        except Exception as e:
            logger.error(f"Lỗi khi tính toán kích thước vị thế cho {symbol}: {str(e)}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _calculate_atr(self, symbol: str, timeframe: str = '1h', period: int = 14) -> Optional[float]:
        """
        Tính ATR (Average True Range)
        
        Args:
            symbol (str): Mã cặp tiền
            timeframe (str): Khung thời gian
            period (int): Số chu kỳ
            
        Returns:
            Optional[float]: Giá trị ATR hoặc None nếu không tính được
        """
        try:
            # Lấy dữ liệu k-line
            klines = self.binance_api.get_klines(symbol, timeframe, limit=period+1)
            
            if not klines or len(klines) < period:
                return None
            
            # Tính True Range
            tr_values = []
            for i in range(1, len(klines)):
                high = float(klines[i][2])
                low = float(klines[i][3])
                prev_close = float(klines[i-1][4])
                
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                
                tr = max(tr1, tr2, tr3)
                tr_values.append(tr)
            
            # Tính ATR
            atr = sum(tr_values) / len(tr_values)
            return atr
        
        except Exception as e:
            logger.error(f"Lỗi khi tính ATR cho {symbol}: {str(e)}")
            return None
    
    def monitor_positions(self) -> List[Dict]:
        """
        Giám sát các vị thế đang mở
        
        Returns:
            List[Dict]: Thông tin các vị thế
        """
        try:
            positions = self.get_open_positions()
            
            if not positions:
                logger.info("Không có vị thế nào đang mở")
                return []
            
            position_info = []
            for position in positions:
                symbol = position.get('symbol')
                position_amt = float(position.get('positionAmt', 0))
                entry_price = float(position.get('entryPrice', 0))
                leverage = int(position.get('leverage', 1))
                
                # Bỏ qua vị thế rỗng
                if abs(position_amt) <= 0:
                    continue
                
                # Lấy giá hiện tại
                current_price = float(self.binance_api.get_symbol_ticker(symbol).get('price', 0))
                
                # Tính lợi nhuận
                side = 'LONG' if position_amt > 0 else 'SHORT'
                if side == 'LONG':
                    pnl_percent = (current_price - entry_price) / entry_price * 100
                else:
                    pnl_percent = (entry_price - current_price) / entry_price * 100
                
                # Tính PnL với đòn bẩy
                pnl_with_leverage = pnl_percent * leverage
                
                # Tính giá trị vị thế USD
                position_value = abs(position_amt) * current_price
                
                # Lấy target profit
                target_profit = self._get_target_profit(symbol)
                
                # Điều chỉnh target profit theo đòn bẩy
                effective_target = target_profit / leverage if leverage > 1 else target_profit
                
                # Thêm vào kết quả
                position_info.append({
                    'symbol': symbol,
                    'side': side,
                    'position_amt': position_amt,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'leverage': leverage,
                    'pnl_percent': pnl_percent,
                    'pnl_with_leverage': pnl_with_leverage,
                    'position_value': position_value,
                    'target_profit': effective_target,
                    'close_recommendation': pnl_percent >= effective_target
                })
                
                logger.info(f"Vị thế {symbol} {side}: Giá vào={entry_price}, Giá hiện tại={current_price}, " 
                          f"PnL={pnl_percent:.2f}% ({pnl_with_leverage:.2f}% với đòn bẩy {leverage}x), "
                          f"Mục tiêu={effective_target:.2f}%")
            
            return position_info
        
        except Exception as e:
            logger.error(f"Lỗi khi giám sát vị thế: {str(e)}")
            return []
    
    def _get_target_profit(self, symbol: str) -> float:
        """
        Lấy mục tiêu lợi nhuận cho một cặp tiền
        
        Args:
            symbol (str): Mã cặp tiền
            
        Returns:
            float: Mục tiêu lợi nhuận (%)
        """
        small_account_settings = self.profit_config.get('small_account_settings', {})
        
        if symbol == 'BTCUSDT':
            return small_account_settings.get('btc_profit_target', 1.5)
        elif symbol == 'ETHUSDT':
            return small_account_settings.get('eth_profit_target', 2.0)
        else:
            return small_account_settings.get('altcoin_profit_target', 3.0)
    
    def get_trading_recommendations(self) -> List[Dict]:
        """
        Lấy khuyến nghị giao dịch cho tài khoản nhỏ
        
        Returns:
            List[Dict]: Danh sách khuyến nghị
        """
        recommendations = []
        preferred_symbols = self.get_preferred_trading_symbols()
        
        for symbol in preferred_symbols:
            try:
                # Lấy dữ liệu thị trường
                market_data = self.get_market_data(symbol)
                
                # Tính toán kích thước vị thế tối ưu
                position_info = self.calculate_optimal_position_size(symbol)
                
                # Kiểm tra nếu có lỗi
                if 'error' in position_info:
                    continue
                
                # Lấy giá trị min notional
                min_notional = position_info.get('min_notional', 5.0)
                
                # Kiểm tra nếu đủ điều kiện giao dịch
                position_size_usd = position_info.get('position_size_usd', 0)
                
                if position_size_usd >= min_notional:
                    recommendation = {
                        'symbol': symbol,
                        'price': market_data.get('price'),
                        'position_size_usd': position_size_usd,
                        'quantity': position_info.get('quantity'),
                        'leverage': position_info.get('leverage'),
                        'min_notional': min_notional,
                        'is_tradable': True,
                        'volume_24h': market_data.get('volume_24h'),
                        'price_change_24h': market_data.get('price_change_24h')
                    }
                else:
                    recommendation = {
                        'symbol': symbol,
                        'price': market_data.get('price'),
                        'position_size_usd': position_size_usd,
                        'min_notional': min_notional,
                        'is_tradable': False,
                        'reason': f"Kích thước vị thế ({position_size_usd:.2f} USDT) dưới giá trị giao dịch tối thiểu ({min_notional} USDT)"
                    }
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.error(f"Lỗi khi tạo khuyến nghị cho {symbol}: {str(e)}")
        
        return recommendations
    
    def run_monitor(self, interval: int = 60, max_runtime: int = None):
        """
        Chạy giám sát liên tục
        
        Args:
            interval (int): Khoảng thời gian giữa các lần kiểm tra (giây)
            max_runtime (int, optional): Thời gian chạy tối đa (giây)
        """
        start_time = time.time()
        logger.info("Bắt đầu giám sát tài khoản nhỏ")
        
        try:
            while True:
                # Kiểm tra thời gian chạy
                if max_runtime and time.time() - start_time > max_runtime:
                    logger.info(f"Đã đạt thời gian chạy tối đa ({max_runtime} giây)")
                    break
                
                # Kiểm tra xem có phải tài khoản nhỏ không
                is_small = self.is_small_account()
                account_balance = self.get_account_balance()
                
                if is_small:
                    logger.info(f"Đang giám sát tài khoản nhỏ: {account_balance} USDT")
                    
                    # Kiểm tra cài đặt đòn bẩy
                    self.check_leverage_settings()
                    
                    # Kiểm tra và thiết lập SL/TP
                    self.check_and_setup_sltp()
                    
                    # Giám sát vị thế
                    self.monitor_positions()
                    
                    # Lấy khuyến nghị giao dịch
                    recommendations = self.get_trading_recommendations()
                    
                    # Hiển thị khuyến nghị
                    tradable_symbols = [r['symbol'] for r in recommendations if r.get('is_tradable', False)]
                    if tradable_symbols:
                        logger.info(f"Các cặp tiền có thể giao dịch: {', '.join(tradable_symbols)}")
                    else:
                        logger.info("Không có cặp tiền nào đáp ứng điều kiện giao dịch tối thiểu")
                    
                else:
                    logger.info(f"Không phải tài khoản nhỏ: {account_balance} USDT > {self.account_size_threshold} USDT")
                
                # Chờ đến lần kiểm tra tiếp theo
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Đã dừng giám sát bởi người dùng")
        except Exception as e:
            logger.error(f"Lỗi khi chạy giám sát: {str(e)}")

def main():
    """Hàm chính"""
    parser = argparse.ArgumentParser(description='Giám sát và quản lý tài khoản giao dịch nhỏ')
    parser.add_argument('--interval', type=int, default=60, help='Khoảng thời gian giữa các lần kiểm tra (giây)')
    parser.add_argument('--max-runtime', type=int, help='Thời gian chạy tối đa (giây)')
    parser.add_argument('--testnet', action='store_true', help='Sử dụng testnet')
    args = parser.parse_args()
    
    monitor = SmallAccountMonitor(testnet=args.testnet)
    monitor.run_monitor(interval=args.interval, max_runtime=args.max_runtime)

if __name__ == "__main__":
    main()