#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
from tabulate import tabulate
from binance_api import BinanceAPI

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("small_account_test")

class SmallAccountTester:
    def __init__(self):
        self.api = BinanceAPI(testnet=True)
        self.account_config = self.load_config('account_config.json')
        self.small_account_configs = self.account_config.get('small_account_configs', {})
        
    def load_config(self, filename):
        """Tải cấu hình từ file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Không thể tải cấu hình từ {filename}: {str(e)}")
            return {}
            
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
                
                for filter_item in symbol_info.get('filters', []):
                    if filter_item.get('filterType') == 'LOT_SIZE':
                        min_qty = float(filter_item.get('minQty', 0))
                    elif filter_item.get('filterType') == 'MIN_NOTIONAL':
                        min_notional = float(filter_item.get('notional', 0))
                
                result[symbol] = {
                    'min_qty': min_qty,
                    'min_notional': min_notional
                }
                
            return result
        except Exception as e:
            logger.error(f"Lỗi khi lấy thông tin kích thước lệnh tối thiểu: {str(e)}")
            return {}
    
    def calculate_min_dollar_values(self, symbols=None):
        """Tính giá trị USD tối thiểu cho mỗi cặp tiền"""
        prices = self.get_current_prices(symbols)
        min_sizes = self.get_minimum_order_sizes(symbols)
        
        result = {}
        for symbol, price in prices.items():
            if symbol in min_sizes:
                min_qty = min_sizes[symbol].get('min_qty', 0)
                min_notional = min_sizes[symbol].get('min_notional', 0)
                
                min_dollar_value = min_qty * price if min_qty else 0
                result[symbol] = {
                    'current_price': price,
                    'min_qty': min_qty,
                    'min_notional': min_notional,
                    'min_dollar_value': min_dollar_value
                }
                
        return result
    
    def test_account_sizes(self, account_sizes=None):
        """Kiểm tra các kích thước tài khoản"""
        if not account_sizes:
            account_sizes = [100, 200, 300, 500, 1000]
            
        # Lấy thông tin tất cả các cặp trong cấu hình
        all_symbols = set(self.account_config.get('symbols', []))
        for config in self.small_account_configs.values():
            all_symbols.update(config.get('suitable_pairs', []))
            
        # Tính giá trị USD tối thiểu cho mỗi cặp
        min_values = self.calculate_min_dollar_values(all_symbols)
        
        results = {}
        for account_size in account_sizes:
            account_str = str(account_size)
            if account_str not in self.small_account_configs:
                logger.warning(f"Không có cấu hình cho tài khoản ${account_size}")
                continue
                
            config = self.small_account_configs[account_str]
            leverage = config.get('leverage', 1)
            risk_percentage = config.get('risk_percentage', 1)
            max_positions = config.get('max_positions', 1)
            suitable_pairs = config.get('suitable_pairs', [])
            
            # Tính giá trị giao dịch tối đa
            max_trade_value = (account_size * risk_percentage / 100) * leverage
            
            # Tìm các cặp phù hợp
            valid_pairs = []
            for symbol in all_symbols:
                if symbol in min_values:
                    min_dollar = min_values[symbol].get('min_dollar_value', 0)
                    min_notional = min_values[symbol].get('min_notional', 0)
                    
                    is_valid = (min_dollar <= max_trade_value and 
                               (min_notional <= max_trade_value or min_notional <= 0))
                    
                    if is_valid:
                        positions = int(max_trade_value / min_dollar) if min_dollar > 0 else 0
                        valid_pairs.append({
                            'symbol': symbol,
                            'min_dollar': min_dollar,
                            'price': min_values[symbol].get('current_price', 0),
                            'positions': positions,
                            'in_config': symbol in suitable_pairs
                        })
            
            # Sắp xếp các cặp theo giá trị tối thiểu
            valid_pairs.sort(key=lambda x: x['min_dollar'])
            
            results[account_size] = {
                'leverage': leverage,
                'risk_percentage': risk_percentage,
                'max_positions': max_positions,
                'max_trade_value': max_trade_value,
                'valid_pairs': valid_pairs,
                'suitable_pairs': suitable_pairs,
                'total_valid_pairs': len(valid_pairs),
                'config_valid_pairs': len([p for p in valid_pairs if p['in_config']])
            }
            
        return results
        
    def run_test(self):
        """Chạy kiểm tra và hiển thị kết quả"""
        logger.info("Bắt đầu kiểm tra cấu hình giao dịch cho tài khoản nhỏ...")
        
        # Lấy số dư tài khoản
        try:
            account_balance = self.api.futures_account_balance()
            available_balance = 0
            
            for balance in account_balance:
                if balance.get('asset') == 'USDT':
                    available_balance = float(balance.get('availableBalance', 0))
                    break
                    
            logger.info(f"Số dư khả dụng: {available_balance} USDT")
        except Exception as e:
            logger.error(f"Không thể lấy số dư tài khoản: {str(e)}")
        
        # Kiểm tra các kích thước tài khoản
        results = self.test_account_sizes()
        
        # Hiển thị kết quả tổng quan
        logger.info("\n" + "="*80)
        logger.info("KẾT QUẢ KIỂM TRA CẤU HÌNH GIAO DỊCH CHO TÀI KHOẢN NHỎ")
        logger.info("="*80)
        
        overview = []
        for account_size, result in results.items():
            overview.append({
                'Account Size': f"${account_size}",
                'Leverage': f"{result['leverage']}x",
                'Risk %': f"{result['risk_percentage']}%",
                'Max Trade Value': f"${result['max_trade_value']:.2f}",
                'Max Positions': result['max_positions'],
                'Valid Pairs': result['total_valid_pairs'],
                'Config Pairs': result['config_valid_pairs']
            })
            
        logger.info("\n" + tabulate(overview, headers='keys', tablefmt='grid'))
        
        # Hiển thị chi tiết cho từng kích thước tài khoản
        for account_size, result in results.items():
            logger.info("\n" + "="*80)
            logger.info(f"CHI TIẾT TÀI KHOẢN ${account_size}")
            logger.info("="*80)
            
            logger.info(f"Đòn bẩy: {result['leverage']}x")
            logger.info(f"Rủi ro: {result['risk_percentage']}%")
            logger.info(f"Giá trị giao dịch tối đa: ${result['max_trade_value']:.2f}")
            logger.info(f"Số vị thế tối đa: {result['max_positions']}")
            
            # Hiển thị các cặp trong cấu hình
            if result['suitable_pairs']:
                logger.info("\nCác cặp được cấu hình:")
                config_pairs = []
                
                for symbol in result['suitable_pairs']:
                    pair_data = next((p for p in result['valid_pairs'] if p['symbol'] == symbol), None)
                    if pair_data:
                        config_pairs.append({
                            'Symbol': symbol,
                            'Price': f"${pair_data['price']:.6f}",
                            'Min Value': f"${pair_data['min_dollar']:.6f}",
                            'Max Positions': pair_data['positions']
                        })
                    else:
                        config_pairs.append({
                            'Symbol': symbol,
                            'Price': "N/A",
                            'Min Value': "N/A",
                            'Max Positions': 0
                        })
                        
                logger.info("\n" + tabulate(config_pairs, headers='keys', tablefmt='grid'))
            
            # Hiển thị top 10 cặp có giá trị tối thiểu thấp nhất
            if result['valid_pairs']:
                logger.info("\nTop 10 cặp có giá trị tối thiểu thấp nhất:")
                top_pairs = []
                
                for pair in result['valid_pairs'][:10]:
                    top_pairs.append({
                        'Symbol': pair['symbol'],
                        'Price': f"${pair['price']:.6f}",
                        'Min Value': f"${pair['min_dollar']:.6f}",
                        'Max Positions': pair['positions'],
                        'In Config': "✓" if pair['in_config'] else "✗"
                    })
                    
                logger.info("\n" + tabulate(top_pairs, headers='keys', tablefmt='grid'))
                
        logger.info("\n" + "="*80)
        logger.info("HOÀN THÀNH KIỂM TRA")
        logger.info("="*80)
        
        return results
        
if __name__ == "__main__":
    tester = SmallAccountTester()
    tester.run_test()