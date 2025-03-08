#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import time
import math
from datetime import datetime
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("small_account_manager")

class SmallAccountManager:
    def __init__(self):
        self.api = BinanceAPI(testnet=True)
        self.account_config = self.load_config('account_config.json')
        self.small_account_configs = self.account_config.get('small_account_configs', {})
        self.current_config = None
        self.min_sizes = {}
        self.current_prices = {}
        
    def load_config(self, filename):
        """Tải cấu hình từ file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Không thể tải cấu hình từ {filename}: {str(e)}")
            return {}
    
    def get_account_balance(self):
        """Lấy số dư tài khoản"""
        try:
            account_balance = self.api.futures_account_balance()
            available_balance = 0
            
            for balance in account_balance:
                if balance.get('asset') == 'USDT':
                    available_balance = float(balance.get('availableBalance', 0))
                    break
                    
            logger.info(f"Số dư khả dụng: {available_balance} USDT")
            return available_balance
        except Exception as e:
            logger.error(f"Không thể lấy số dư tài khoản: {str(e)}")
            return 0
    
    def select_account_config(self, balance):
        """Chọn cấu hình phù hợp dựa trên số dư"""
        # Chuyển đổi các key từ string thành float để so sánh
        sizes = [float(size) for size in self.small_account_configs.keys()]
        sizes.sort()
        
        selected_size = None
        for size in sizes:
            if balance >= size:
                selected_size = size
            else:
                break
                
        if selected_size is None and sizes:
            # Nếu số dư nhỏ hơn tất cả các mức, chọn mức nhỏ nhất
            selected_size = sizes[0]
            
        if selected_size:
            config = self.small_account_configs.get(str(int(selected_size)), {})
            logger.info(f"Đã chọn cấu hình cho tài khoản ${int(selected_size)}")
            self.current_config = config
            return config
        else:
            logger.error("Không tìm thấy cấu hình phù hợp")
            return None
            
    def get_current_prices(self, symbols=None):
        """Lấy giá hiện tại của các cặp tiền"""
        try:
            tickers = self.api.futures_ticker_price()
            if not tickers:
                logger.error("Không thể lấy thông tin giá hiện tại")
                return {}
                
            price_dict = {ticker['symbol']: float(ticker['price']) 
                         for ticker in tickers 
                         if 'symbol' in ticker and 'price' in ticker}
            
            if symbols:
                return {symbol: price_dict.get(symbol, 0) for symbol in symbols}
            
            self.current_prices = price_dict
            return price_dict
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá: {str(e)}")
            return {}
            
    def get_minimum_order_sizes(self, symbols=None):
        """Lấy thông tin về kích thước lệnh tối thiểu"""
        try:
            exchange_info = self.api.futures_exchange_info()
            if not exchange_info or 'symbols' not in exchange_info:
                logger.error("Không thể lấy thông tin giao dịch")
                return {}
                
            result = {}
            for symbol_info in exchange_info.get('symbols', []):
                symbol = symbol_info.get('symbol')
                if symbols and symbol not in symbols:
                    continue
                    
                min_qty = None
                min_notional = None
                tick_size = None
                step_size = None
                price_precision = symbol_info.get('pricePrecision', 0)
                qty_precision = symbol_info.get('quantityPrecision', 0)
                
                for filter_item in symbol_info.get('filters', []):
                    if filter_item.get('filterType') == 'LOT_SIZE':
                        min_qty = float(filter_item.get('minQty', 0))
                        step_size = float(filter_item.get('stepSize', 0))
                    elif filter_item.get('filterType') == 'MIN_NOTIONAL':
                        min_notional = float(filter_item.get('notional', 0))
                    elif filter_item.get('filterType') == 'PRICE_FILTER':
                        tick_size = float(filter_item.get('tickSize', 0))
                
                result[symbol] = {
                    'min_qty': min_qty,
                    'min_notional': min_notional,
                    'tick_size': tick_size,
                    'step_size': step_size,
                    'price_precision': price_precision,
                    'qty_precision': qty_precision
                }
                
            self.min_sizes = result
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin kích thước lệnh tối thiểu: {str(e)}")
            return {}
    
    def round_step_size(self, quantity, step_size):
        """Làm tròn số lượng theo step size"""
        if step_size == 0:
            return quantity
            
        precision = int(round(-math.log10(step_size)))
        rounded = math.floor(quantity / step_size) * step_size
        return round(rounded, precision)
    
    def calculate_position_size(self, symbol, account_size, risk_percentage, leverage):
        """Tính kích thước vị thế dựa trên mức rủi ro và đòn bẩy"""
        # Lấy giá hiện tại
        if symbol not in self.current_prices:
            self.get_current_prices([symbol])
            
        current_price = self.current_prices.get(symbol, 0)
        if current_price <= 0:
            logger.error(f"Không thể lấy giá hiện tại cho {symbol}")
            return 0, 0
            
        # Lấy thông tin min/step sizes
        if symbol not in self.min_sizes:
            self.get_minimum_order_sizes([symbol])
            
        symbol_info = self.min_sizes.get(symbol, {})
        min_qty = symbol_info.get('min_qty', 0)
        step_size = symbol_info.get('step_size', 0)
        
        # Tính giá trị USD tối đa cho vị thế này
        max_position_value = (account_size * risk_percentage / 100) * leverage
        
        # Tính số lượng
        raw_quantity = max_position_value / current_price
        
        # Kiểm tra số lượng tối thiểu
        if raw_quantity < min_qty:
            logger.warning(f"Số lượng tính toán {raw_quantity} nhỏ hơn mức tối thiểu {min_qty} cho {symbol}")
            return 0, 0
            
        # Làm tròn số lượng theo step size
        quantity = self.round_step_size(raw_quantity, step_size)
        
        # Tính lại giá trị đô la
        actual_value = quantity * current_price
        
        return quantity, actual_value
    
    def set_leverage(self, symbol, leverage):
        """Thiết lập đòn bẩy cho một symbol"""
        try:
            result = self.api.futures_change_leverage(symbol=symbol, leverage=leverage)
            logger.info(f"Đã đặt đòn bẩy {leverage}x cho {symbol}: {result}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi đặt đòn bẩy cho {symbol}: {str(e)}")
            return False
    
    def create_market_order(self, symbol, side, quantity):
        """Tạo lệnh thị trường"""
        try:
            order = self.api.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            logger.info(f"Đã tạo lệnh {side} {quantity} {symbol}: {order}")
            return order
        except Exception as e:
            logger.error(f"Lỗi khi tạo lệnh {side} {quantity} {symbol}: {str(e)}")
            return None
    
    def check_active_positions(self):
        """Kiểm tra các vị thế đang mở"""
        try:
            positions = self.api.get_futures_position_risk()
            active_positions = []
            
            for pos in positions:
                amt = float(pos.get('positionAmt', 0))
                if amt != 0:
                    active_positions.append({
                        'symbol': pos.get('symbol'),
                        'amount': amt,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_profit': float(pos.get('unRealizedProfit', 0)),
                        'leverage': int(pos.get('leverage', 1))
                    })
            
            logger.info(f"Tìm thấy {len(active_positions)} vị thế đang mở")
            return active_positions
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra vị thế: {str(e)}")
            return []
    
    def run_test_order(self, symbol, account_size, risk_percentage, leverage):
        """Chạy thử nghiệm đặt lệnh cho tài khoản nhỏ"""
        try:
            # Set leverage
            self.set_leverage(symbol, leverage)
            
            # Calculate position size
            quantity, actual_value = self.calculate_position_size(
                symbol, account_size, risk_percentage, leverage
            )
            
            if quantity <= 0:
                logger.error(f"Không thể tính toán kích thước vị thế cho {symbol}")
                return False
                
            logger.info(f"Đã tính toán vị thế: {quantity} {symbol} (${actual_value:.2f})")
            
            # Hiện tại chỉ mô phỏng đặt lệnh, không thực sự đặt
            # Bỏ comment 2 dòng dưới đây để thực sự đặt lệnh
            # order = self.create_market_order(symbol, 'BUY', quantity)
            # return order is not None
            
            return True
        except Exception as e:
            logger.error(f"Lỗi khi chạy thử nghiệm lệnh: {str(e)}")
            return False
    
    def run_tests(self):
        """Chạy các thử nghiệm đặt lệnh"""
        logger.info("Bắt đầu chạy thử nghiệm cho tài khoản nhỏ...")
        
        # Lấy số dư
        balance = self.get_account_balance()
        if balance <= 0:
            logger.error("Không thể lấy số dư tài khoản")
            return False
            
        # Chọn cấu hình phù hợp
        config = self.select_account_config(balance)
        if not config:
            return False
            
        # Lấy thông tin cấu hình
        leverage = config.get('leverage', 1)
        risk_percentage = config.get('risk_percentage', 1)
        max_positions = config.get('max_positions', 1)
        suitable_pairs = config.get('suitable_pairs', [])
        
        logger.info(f"Cấu hình: Đòn bẩy {leverage}x, Rủi ro {risk_percentage}%, Vị thế tối đa {max_positions}")
        
        # Lấy giá hiện tại và thông tin kích thước tối thiểu
        self.get_current_prices(suitable_pairs)
        self.get_minimum_order_sizes(suitable_pairs)
        
        # Kiểm tra các vị thế đang mở
        active_positions = self.check_active_positions()
        active_symbols = [pos['symbol'] for pos in active_positions]
        
        # Tính toán số vị thế còn lại có thể mở
        remaining_positions = max_positions - len(active_positions)
        if remaining_positions <= 0:
            logger.warning(f"Đã đạt số lượng vị thế tối đa ({max_positions})")
            return False
            
        logger.info(f"Còn lại {remaining_positions} vị thế có thể mở")
        
        # Chạy thử nghiệm cho từng cặp tiền
        results = []
        
        for symbol in suitable_pairs:
            if symbol in active_symbols:
                logger.info(f"Bỏ qua {symbol} vì đã có vị thế đang mở")
                continue
                
            logger.info(f"Kiểm tra {symbol}...")
            
            success = self.run_test_order(
                symbol, balance, risk_percentage, leverage
            )
            
            results.append({
                'symbol': symbol,
                'success': success
            })
            
        # Hiển thị kết quả tổng quan
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        logger.info("\n" + "="*80)
        logger.info("KẾT QUẢ THỬ NGHIỆM")
        logger.info("="*80)
        logger.info(f"Tổng số cặp kiểm tra: {len(results)}")
        logger.info(f"Thành công: {len(successful)}")
        logger.info(f"Thất bại: {len(failed)}")
        
        if successful:
            logger.info("\nCác cặp thành công:")
            for result in successful:
                logger.info(f"- {result['symbol']}")
                
        if failed:
            logger.info("\nCác cặp thất bại:")
            for result in failed:
                logger.info(f"- {result['symbol']}")
                
        logger.info("\n" + "="*80)
        logger.info("HOÀN THÀNH")
        logger.info("="*80)
        
        return len(successful) > 0

if __name__ == "__main__":
    manager = SmallAccountManager()
    manager.run_tests()