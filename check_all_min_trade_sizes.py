#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import pandas as pd
from binance_api import BinanceAPI
from tabulate import tabulate

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("min_trade_checker")

def get_common_trading_pairs():
    """Danh sách các cặp giao dịch phổ biến trên Binance Futures"""
    return [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", 
        "XRPUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT",
        "LINKUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "NEARUSDT"
    ]

def get_all_usdt_pairs(exchange_info):
    """Lấy tất cả các cặp giao dịch kết thúc bằng USDT"""
    usdt_pairs = []
    for symbol in exchange_info.get('symbols', []):
        if symbol.get('symbol', '').endswith('USDT') and symbol.get('status') == 'TRADING':
            usdt_pairs.append(symbol.get('symbol'))
    return usdt_pairs

def check_all_min_trade_sizes():
    """Kiểm tra kích thước giao dịch tối thiểu cho tất cả các cặp tiền phổ biến"""
    try:
        # Khởi tạo API
        api = BinanceAPI(testnet=True)
        
        logger.info("Đang lấy thông tin chi tiết từ Binance Futures...")
        
        # Lấy thông tin trao đổi
        exchange_info = api.futures_exchange_info()
        if not exchange_info or 'symbols' not in exchange_info:
            logger.error("Không thể lấy thông tin exchange từ Binance API")
            return False
            
        logger.info(f"Đã lấy thông tin từ {len(exchange_info.get('symbols', []))} cặp giao dịch")
        
        # Lấy tất cả các cặp kết thúc bằng USDT
        all_pairs = get_all_usdt_pairs(exchange_info)
        logger.info(f"Tìm thấy {len(all_pairs)} cặp giao dịch USDT")
        
        # Nếu không có cặp nào, sử dụng danh sách các cặp phổ biến
        if not all_pairs:
            all_pairs = get_common_trading_pairs()
            logger.info(f"Sử dụng danh sách {len(all_pairs)} cặp phổ biến")
        
        # Chuẩn bị danh sách để lưu kết quả
        results = []
        
        # Lấy giá hiện tại của tất cả các cặp
        logger.info("Đang lấy thông tin giá hiện tại...")
        tickers = api.futures_ticker_price()
        
        if not tickers:
            logger.error("Không thể lấy thông tin giá từ Binance API")
            return False
            
        price_dict = {ticker['symbol']: float(ticker['price']) for ticker in tickers if 'symbol' in ticker and 'price' in ticker}
        logger.info(f"Đã lấy giá của {len(price_dict)} cặp giao dịch")
        
        # Lấy thông tin chi tiết về các yêu cầu tối thiểu cho mỗi cặp
        symbols_info = {}
        for symbol in exchange_info.get('symbols', []):
            symbols_info[symbol['symbol']] = symbol
        
        # Phân tích và lưu thông tin cho mỗi cặp giao dịch
        logger.info("Đang phân tích kích thước giao dịch tối thiểu...")
        
        for pair in all_pairs:
            if pair in symbols_info and pair in price_dict:
                symbol_info = symbols_info[pair]
                current_price = price_dict[pair]
                
                # Lấy thông tin về kích thước lô tối thiểu và bước giá
                min_qty = None
                min_notional = None
                price_precision = symbol_info.get('pricePrecision', 2)
                qty_precision = symbol_info.get('quantityPrecision', 2)
                
                # Lấy thông tin từ bộ lọc
                for filter_item in symbol_info.get('filters', []):
                    if filter_item.get('filterType') == 'LOT_SIZE':
                        min_qty = float(filter_item.get('minQty', 0))
                    elif filter_item.get('filterType') == 'MIN_NOTIONAL':
                        min_notional = float(filter_item.get('notional', 0))
                
                # Tính giá trị $ tối thiểu
                min_dollar_value = min_qty * current_price if min_qty else 0
                
                # Thêm vào kết quả
                results.append({
                    'Pair': pair,
                    'Current Price': current_price,
                    'Min Quantity': min_qty,
                    'Min Notional': min_notional,
                    'Min $ Value': min_dollar_value,
                    'Price Precision': price_precision,
                    'Qty Precision': qty_precision
                })
        
        if not results:
            logger.error("Không tìm thấy kết quả phân tích nào.")
            return False
        
        # Sắp xếp kết quả theo giá trị $ tối thiểu
        results = sorted(results, key=lambda x: x['Min $ Value'])
        logger.info(f"Đã phân tích xong {len(results)} cặp giao dịch")
        
        # Hiển thị kết quả dưới dạng bảng
        df = pd.DataFrame(results)
        logger.info("\n" + "="*100)
        logger.info("KÍCH THƯỚC GIAO DỊCH TỐI THIỂU CHO CÁC CẶP TIỀN")
        logger.info("="*100)
        
        # Hiển thị top 20 cặp có giá trị tối thiểu thấp nhất
        top_low_value = df.head(20)
        table_low = tabulate(top_low_value, headers='keys', tablefmt='psql', floatfmt='.8f', numalign='right', showindex=False)
        logger.info(f"\nTop 20 cặp có giá trị tối thiểu thấp nhất:")
        logger.info("\n" + table_low)
        
        # Hiển thị các cặp phổ biến
        popular_pairs = get_common_trading_pairs()
        df_popular = df[df['Pair'].isin(popular_pairs)]
        table_popular = tabulate(df_popular, headers='keys', tablefmt='psql', floatfmt='.8f', numalign='right', showindex=False)
        logger.info(f"\nCác cặp phổ biến:")
        logger.info("\n" + table_popular)
        
        # Phân tích và hiển thị các cặp tiền phù hợp cho từng kích thước tài khoản
        account_sizes = [100, 200, 300, 500, 1000]
        risk_levels = [5, 10, 15, 20, 25, 30]
        leverage_levels = [5, 10, 15, 20]
        
        logger.info("\n" + "="*100)
        logger.info("CÁC CẶP TIỀN PHÙ HỢP CHO TỪNG KÍCH THƯỚC TÀI KHOẢN")
        logger.info("="*100)
        
        suitable_configs = []
        
        for account_size in account_sizes:
            logger.info(f"\nTài khoản {account_size} USD:")
            logger.info("-"*80)
            
            account_suitable_configs = []
            
            for risk in risk_levels:
                for leverage in leverage_levels:
                    max_dollar_value = (account_size * risk / 100) * leverage
                    
                    # Lọc các cặp tiền phù hợp
                    suitable_pairs = []
                    for result in results:
                        if result['Min $ Value'] <= max_dollar_value and (result['Min Notional'] <= max_dollar_value or result['Min Notional'] is None):
                            suitable_pairs.append({
                                'Pair': result['Pair'],
                                'Min $ Value': result['Min $ Value'],
                                'Current Price': result['Current Price'],
                                'Account Size': account_size,
                                'Risk %': risk,
                                'Leverage': leverage,
                                'Max Trade Value': max_dollar_value,
                                'Possible Positions': int(max_dollar_value / result['Min $ Value']) if result['Min $ Value'] > 0 else 0
                            })
                    
                    if suitable_pairs:
                        # Chỉ hiển thị các cấu hình có ít nhất 3 cặp tiền phổ biến
                        popular_in_suitable = [p for p in suitable_pairs if p['Pair'] in popular_pairs]
                        
                        if len(popular_in_suitable) >= 3:
                            logger.info(f"Risk: {risk}%, Leverage: {leverage}x, Max Trade Value: ${max_dollar_value:.2f}")
                            logger.info(f"  Số cặp tiền phù hợp: {len(suitable_pairs)}, Số cặp phổ biến: {len(popular_in_suitable)}")
                            
                            # Hiển thị top 5 cặp phổ biến
                            for pair in popular_in_suitable[:5]:
                                logger.info(f"  - {pair['Pair']}: Min ${pair['Min $ Value']:.2f}, Có thể mở tối đa {pair['Possible Positions']} vị thế")
                            
                            config = {
                                'Account Size': account_size,
                                'Risk %': risk,
                                'Leverage': leverage,
                                'Max Trade Value': max_dollar_value,
                                'Suitable Pairs Count': len(suitable_pairs),
                                'Popular Pairs Count': len(popular_in_suitable),
                                'Suitable Pairs': [p['Pair'] for p in suitable_pairs],
                                'Popular Suitable Pairs': [p['Pair'] for p in popular_in_suitable],
                                'Possible Positions': {p['Pair']: p['Possible Positions'] for p in suitable_pairs}
                            }
                            
                            account_suitable_configs.append(config)
                            suitable_configs.append(config)
            
            # Hiển thị số lượng cấu hình phù hợp
            if account_suitable_configs:
                logger.info(f"Tìm thấy {len(account_suitable_configs)} cấu hình phù hợp cho tài khoản ${account_size}")
            else:
                logger.info(f"Không tìm thấy cấu hình phù hợp cho tài khoản ${account_size}")
        
        # Lưu kết quả phân tích vào file JSON
        with open('min_trade_analysis.json', 'w') as f:
            json.dump({
                'min_trade_info': results,
                'suitable_configs': suitable_configs
            }, f, indent=2)
        
        logger.info("\n" + "="*100)
        logger.info("Đã lưu kết quả phân tích vào file min_trade_analysis.json")
        logger.info("="*100)
        
        # Tạo cấu hình cho tài khoản nhỏ cho tất cả các cặp tiền
        create_small_account_configs(results, suitable_configs)
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kích thước giao dịch tối thiểu: {str(e)}")
        return False

def create_small_account_configs(trade_info, suitable_configs):
    """Tạo cấu hình cho tài khoản nhỏ dựa trên kết quả phân tích"""
    try:
        # Nhóm cặp tiền theo giá trị tối thiểu
        low_min_pairs = []
        medium_min_pairs = []
        high_min_pairs = []
        
        for info in trade_info:
            if info['Min $ Value'] < 10:
                low_min_pairs.append(info['Pair'])
            elif info['Min $ Value'] < 50:
                medium_min_pairs.append(info['Pair'])
            else:
                high_min_pairs.append(info['Pair'])
        
        # Lấy các cặp phổ biến
        popular_pairs = get_common_trading_pairs()
        
        # Tìm các cặp phổ biến trong mỗi nhóm
        popular_low = [p for p in low_min_pairs if p in popular_pairs]
        popular_medium = [p for p in medium_min_pairs if p in popular_pairs]
        popular_high = [p for p in high_min_pairs if p in popular_pairs]
        
        logger.info(f"Phân loại cặp tiền theo giá trị tối thiểu:")
        logger.info(f"- Thấp (<$10): {len(low_min_pairs)} cặp, {len(popular_low)} cặp phổ biến")
        logger.info(f"- Trung bình ($10-$50): {len(medium_min_pairs)} cặp, {len(popular_medium)} cặp phổ biến")
        logger.info(f"- Cao (>$50): {len(high_min_pairs)} cặp, {len(popular_high)} cặp phổ biến")
        
        # Tạo cấu hình cho từng kích thước tài khoản
        small_account_configs = {
            "100": {
                "leverage": 20,
                "risk_percentage": 20,
                "max_positions": 1,
                "suitable_pairs": popular_low[:8] if popular_low else low_min_pairs[:10],
                "note": "Cấu hình cho tài khoản $100, chỉ nên giao dịch các cặp tiền có giá trị tối thiểu thấp"
            },
            "200": {
                "leverage": 15,
                "risk_percentage": 15,
                "max_positions": 2,
                "suitable_pairs": (popular_low + popular_medium[:3]) if (popular_low or popular_medium) else (low_min_pairs + medium_min_pairs[:5]),
                "note": "Cấu hình cho tài khoản $200, có thể giao dịch các cặp tiền có giá trị tối thiểu thấp đến trung bình"
            },
            "300": {
                "leverage": 10,
                "risk_percentage": 10,
                "max_positions": 3,
                "suitable_pairs": (popular_low + popular_medium + popular_high[:1]) if (popular_low or popular_medium) else (low_min_pairs + medium_min_pairs),
                "note": "Cấu hình cho tài khoản $300, có thể giao dịch hầu hết các cặp tiền trừ những cặp có giá trị tối thiểu cao"
            }
        }
        
        # Cập nhật cấu hình với thêm các thông tin về BTC
        for account_size, config in small_account_configs.items():
            # Kiểm tra xem BTC có phù hợp với cấu hình này không
            btc_min_value = next((info['Min $ Value'] for info in trade_info if info['Pair'] == 'BTCUSDT'), None)
            if btc_min_value:
                max_trade_value = int(account_size) * config['risk_percentage'] / 100 * config['leverage']
                btc_suitable = btc_min_value <= max_trade_value
                
                config['btc_min_value'] = btc_min_value
                config['max_trade_value'] = max_trade_value
                config['btc_suitable'] = btc_suitable
                
                if btc_suitable:
                    config['btc_positions'] = int(max_trade_value / btc_min_value) if btc_min_value > 0 else 0
                    if 'BTCUSDT' not in config['suitable_pairs']:
                        config['suitable_pairs'].append('BTCUSDT')
                else:
                    config['btc_positions'] = 0
        
        # Lưu cấu hình vào file
        with open('small_account_risk_configs.json', 'w') as f:
            json.dump(small_account_configs, f, indent=2)
            
        logger.info("\n" + "="*100)
        logger.info("ĐỀ XUẤT CẤU HÌNH RỦI RO CHO TÀI KHOẢN NHỎ")
        logger.info("="*100)
        
        # Hiển thị thông tin cấu hình
        for account_size, config in small_account_configs.items():
            logger.info(f"\nTài khoản ${account_size}:")
            logger.info(f"- Đòn bẩy: {config['leverage']}x")
            logger.info(f"- Rủi ro: {config['risk_percentage']}%")
            logger.info(f"- Số vị thế tối đa: {config['max_positions']}")
            logger.info(f"- Giá trị giao dịch tối đa: ${config['max_trade_value']:.2f}")
            
            btc_info = "Có thể giao dịch" if config.get('btc_suitable', False) else "Không thể giao dịch"
            logger.info(f"- BTC: {btc_info} (Min: ${config.get('btc_min_value', 0):.2f}, Vị thế tối đa: {config.get('btc_positions', 0)})")
            
            # Hiển thị các cặp phù hợp
            suitable_pairs = config['suitable_pairs']
            logger.info(f"- Số cặp phù hợp: {len(suitable_pairs)}")
            if suitable_pairs:
                for pair in suitable_pairs[:5]:  # Chỉ hiển thị 5 cặp đầu tiên
                    pair_min = next((info['Min $ Value'] for info in trade_info if info['Pair'] == pair), 0)
                    logger.info(f"  + {pair}: Min ${pair_min:.2f}")
                
                if len(suitable_pairs) > 5:
                    logger.info(f"  + ... và {len(suitable_pairs) - 5} cặp khác")
        
        logger.info("\n" + "="*100)
        logger.info("Đã tạo cấu hình cho tài khoản nhỏ và lưu vào file small_account_risk_configs.json")
        logger.info("="*100)
        
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo cấu hình cho tài khoản nhỏ: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Bắt đầu kiểm tra kích thước giao dịch tối thiểu cho tất cả các cặp tiền...")
    check_all_min_trade_sizes()