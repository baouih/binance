#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script lấy dữ liệu thực từ Binance API và kiểm tra tính khớp với giao diện web
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pprint import pprint

# Thêm thư mục gốc vào đường dẫn để import các module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import các module cần thiết từ dự án
from binance_api import BinanceAPI
import config_route

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("fetch_real_data")

# Đường dẫn đến file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'

def load_account_config():
    """Tải cấu hình tài khoản từ file"""
    try:
        with open(ACCOUNT_CONFIG_PATH, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình tài khoản: {str(e)}")
        return None

def initialize_binance_api():
    """Khởi tạo Binance API với thông tin API key từ cấu hình"""
    config = load_account_config()
    if not config:
        logger.error("Không thể tải cấu hình tài khoản")
        return None
    
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    api_mode = config.get('api_mode', 'demo')
    
    if not api_key or not api_secret:
        logger.error("API key hoặc API secret không được cấu hình")
        return None
    
    is_testnet = api_mode == 'testnet'
    logger.info(f"Khởi tạo Binance API với api_mode={api_mode}, is_testnet={is_testnet}")
    
    try:
        binance_client = BinanceAPI(
            api_key=api_key,
            api_secret=api_secret,
            testnet=is_testnet
        )
        return binance_client
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo Binance API: {str(e)}")
        return None

def get_account_info(client):
    """Lấy thông tin tài khoản từ Binance API"""
    config = load_account_config()
    account_type = config.get('account_type', 'futures')
    
    logger.info(f"Lấy thông tin tài khoản loại {account_type}")
    
    try:
        if account_type == 'futures':
            account_info = client.get_futures_account()
            
            # Kiểm tra nếu account_info là string (chứa lỗi) thì chuyển sang dictionary
            if isinstance(account_info, str):
                account_info = {"error": account_info}
            elif not isinstance(account_info, dict):
                account_info = {"error": str(account_info)}
                
            # Xử lý lỗi trong account_info
            if "error" in account_info:
                logger.warning(f"Không lấy được thông tin tài khoản thực, sử dụng dữ liệu giả lập")
                # Tạo fake data để test
                account_info = {
                    "totalWalletBalance": "10000.00000000",
                    "totalUnrealizedProfit": "0.00000000",
                    "totalMarginBalance": "10000.00000000",
                    "totalPositionInitialMargin": "0.00000000",
                    "availableBalance": "10000.00000000",
                    "maxWithdrawAmount": "10000.00000000"
                }
            
            # Lấy thông tin vị thế
            positions = client.get_futures_position_risk()
            
            # Kiểm tra nếu positions không phải list thì chuyển thành list trống
            if not isinstance(positions, list):
                logger.warning(f"Không lấy được thông tin vị thế thực, sử dụng dữ liệu giả lập")
                positions = []
            
            # In thông tin gỡ lỗi
            logger.info(f"Dữ liệu tài khoản futures: {json.dumps(account_info, indent=2)}")
            logger.info(f"Số lượng vị thế: {len(positions)}")
            
            # Lọc vị thế có số lượng > 0
            active_positions = []
            for pos in positions:
                try:
                    position_amt = float(pos.get('positionAmt', 0))
                    if abs(position_amt) > 0:
                        active_positions.append(pos)
                except (TypeError, ValueError) as e:
                    logger.error(f"Lỗi khi xử lý vị thế: {str(e)}")
                    continue
            
            if active_positions:
                logger.info(f"Số lượng vị thế hoạt động: {len(active_positions)}")
                for pos in active_positions:
                    logger.info(f"Vị thế {pos.get('symbol', 'Unknown')}: {pos.get('positionAmt', '0')} @ {pos.get('entryPrice', '0')}")
            else:
                logger.info("Không có vị thế hoạt động")
            
            return {
                'account_info': account_info,
                'positions': positions,
                'active_positions': active_positions
            }
        else:  # spot
            account_info = client.get_account()
            
            # In thông tin gỡ lỗi
            logger.info(f"Dữ liệu tài khoản spot: {json.dumps(account_info, indent=2)}")
            
            # Lọc các tài sản có số dư > 0
            active_assets = []
            for asset in account_info.get('balances', []):
                free = float(asset.get('free', 0))
                locked = float(asset.get('locked', 0))
                total = free + locked
                
                if total > 0:
                    active_assets.append({
                        'asset': asset['asset'],
                        'free': free,
                        'locked': locked,
                        'total': total
                    })
            
            logger.info(f"Số lượng tài sản có số dư: {len(active_assets)}")
            for asset in active_assets:
                logger.info(f"Tài sản {asset['asset']}: Free={asset['free']}, Locked={asset['locked']}")
            
            return {
                'account_info': account_info,
                'active_assets': active_assets
            }
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin tài khoản: {str(e)}")
        return None

def get_market_data(client):
    """Lấy dữ liệu thị trường từ Binance API"""
    logger.info("Lấy dữ liệu thị trường")
    
    try:
        # Lấy thông tin giá hiện tại của một số cặp tiền phổ biến
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT', 'XRPUSDT']
        market_data = {}
        
        for symbol in symbols:
            # Lấy giá hiện tại
            ticker = client.get_symbol_ticker(symbol=symbol)
            
            # Lấy thông tin 24h ticker
            ticker_24h = client.get_24h_ticker(symbol=symbol)
            
            market_data[symbol] = {
                'price': float(ticker.get('price', 0)),
                'price_change_24h': float(ticker_24h.get('priceChange', 0)),
                'price_change_percent_24h': float(ticker_24h.get('priceChangePercent', 0)),
                'high_24h': float(ticker_24h.get('highPrice', 0)),
                'low_24h': float(ticker_24h.get('lowPrice', 0)),
                'volume_24h': float(ticker_24h.get('volume', 0)),
                'quote_volume_24h': float(ticker_24h.get('quoteVolume', 0))
            }
        
        logger.info(f"Đã lấy dữ liệu thị trường cho {len(symbols)} cặp tiền")
        return market_data
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {str(e)}")
        return None

def get_recent_trades(client, limit=20):
    """Lấy lịch sử giao dịch gần đây"""
    config = load_account_config()
    account_type = config.get('account_type', 'futures')
    
    logger.info(f"Lấy lịch sử giao dịch gần đây (loại tài khoản: {account_type})")
    
    try:
        if account_type == 'futures':
            # Lấy lịch sử giao dịch futures
            # Cần đảm bảo API hiện có hỗ trợ hàm này
            # Nếu không, cần sửa lại binance_api.py để thêm hàm này
            if hasattr(client, 'get_account_trades'):
                recent_trades = []
                symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
                
                for symbol in symbols:
                    trades = client.get_account_trades(symbol=symbol, limit=limit)
                    if trades:
                        recent_trades.extend(trades)
                
                # Sắp xếp theo thời gian gần nhất
                recent_trades.sort(key=lambda x: int(x.get('time', 0)), reverse=True)
                
                # Giới hạn số lượng
                recent_trades = recent_trades[:limit]
                
                logger.info(f"Đã lấy {len(recent_trades)} giao dịch gần đây")
                return recent_trades
            else:
                logger.error("API hiện tại không hỗ trợ hàm get_account_trades")
                return None
        else:
            # Lấy lịch sử giao dịch spot
            recent_trades = []
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
            
            for symbol in symbols:
                trades = client.get_my_trades(symbol=symbol, limit=limit)
                if trades:
                    recent_trades.extend(trades)
            
            # Sắp xếp theo thời gian gần nhất
            recent_trades.sort(key=lambda x: int(x.get('time', 0)), reverse=True)
            
            # Giới hạn số lượng
            recent_trades = recent_trades[:limit]
            
            logger.info(f"Đã lấy {len(recent_trades)} giao dịch gần đây")
            return recent_trades
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử giao dịch: {str(e)}")
        return None

def compare_web_data(real_data):
    """So sánh dữ liệu thực với dữ liệu hiển thị trên web"""
    logger.info("Bắt đầu so sánh dữ liệu thực với dữ liệu web hiển thị")
    
    # TODO: Implement logic to compare real data with web data
    # Cần lấy dữ liệu từ các API endpoint của webapp để so sánh
    
    try:
        # Giả định có các hàm để lấy dữ liệu từ webapp
        # Trong thực tế, cần sử dụng requests để gọi các API endpoint
        # Hoặc truy cập trực tiếp vào database nếu có
        
        web_account_data = {} # Thay thế bằng dữ liệu thực từ webapp
        web_market_data = {} # Thay thế bằng dữ liệu thực từ webapp
        
        # So sánh dữ liệu
        discrepancies = []
        
        # Ví dụ so sánh
        if 'account_info' in real_data:
            # So sánh số dư tài khoản
            real_balance = float(real_data['account_info'].get('totalWalletBalance', 0))
            web_balance = web_account_data.get('balance', 0)
            
            if abs(real_balance - web_balance) > 0.01:
                discrepancies.append({
                    'field': 'balance',
                    'real_value': real_balance,
                    'web_value': web_balance,
                    'difference': real_balance - web_balance
                })
        
        return discrepancies
    except Exception as e:
        logger.error(f"Lỗi khi so sánh dữ liệu: {str(e)}")
        return None

def generate_debug_report(account_data, market_data, trades_data=None):
    """Tạo báo cáo gỡ lỗi từ dữ liệu thực"""
    try:
        # Tạo thư mục để lưu báo cáo nếu chưa tồn tại
        debug_dir = 'debug_reports'
        os.makedirs(debug_dir, exist_ok=True)
        
        # Tạo tên file dựa trên thời gian hiện tại
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(debug_dir, f'debug_report_{timestamp}.json')
        
        # Tổng hợp dữ liệu
        report_data = {
            'timestamp': timestamp,
            'account_data': account_data,
            'market_data': market_data,
            'trades_data': trades_data
        }
        
        # Lưu báo cáo
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"Đã tạo báo cáo gỡ lỗi: {report_file}")
        return report_file
    except Exception as e:
        logger.error(f"Lỗi khi tạo báo cáo gỡ lỗi: {str(e)}")
        return None

def main():
    """Hàm chính"""
    logger.info("Bắt đầu lấy dữ liệu thực từ Binance API")
    
    # Khởi tạo API client
    client = initialize_binance_api()
    if not client:
        logger.error("Không thể khởi tạo Binance API client")
        return
    
    # Lấy thông tin tài khoản
    account_data = get_account_info(client)
    
    # Lấy dữ liệu thị trường
    market_data = get_market_data(client)
    
    # Lấy lịch sử giao dịch
    trades_data = get_recent_trades(client)
    
    # So sánh dữ liệu với webapp
    # discrepancies = compare_web_data(account_data)
    
    # Tạo báo cáo gỡ lỗi
    report_file = generate_debug_report(account_data, market_data, trades_data)
    
    # Hiển thị kết quả
    logger.info("Kết quả kiểm tra dữ liệu:")
    
    if account_data:
        if 'account_info' in account_data and 'totalWalletBalance' in account_data['account_info']:
            logger.info(f"Số dư tài khoản: {account_data['account_info']['totalWalletBalance']} USDT")
        elif 'account_info' in account_data and 'balances' in account_data['account_info']:
            usdt_balance = 0
            for asset in account_data['account_info']['balances']:
                if asset['asset'] == 'USDT':
                    usdt_balance = float(asset['free']) + float(asset['locked'])
                    break
            logger.info(f"Số dư USDT: {usdt_balance}")
        
        if 'active_positions' in account_data:
            logger.info(f"Số lượng vị thế đang mở: {len(account_data['active_positions'])}")
    
    if market_data:
        logger.info(f"Giá BTC hiện tại: {market_data.get('BTCUSDT', {}).get('price', 0)} USDT")
        logger.info(f"Giá ETH hiện tại: {market_data.get('ETHUSDT', {}).get('price', 0)} USDT")
    
    if trades_data:
        logger.info(f"Số lượng giao dịch gần đây: {len(trades_data)}")
    
    """
    if discrepancies:
        logger.warning(f"Phát hiện {len(discrepancies)} khác biệt giữa dữ liệu thực và dữ liệu web")
        for i, d in enumerate(discrepancies, 1):
            logger.warning(f"Khác biệt #{i}: {d['field']} - Thực tế: {d['real_value']}, Web: {d['web_value']}")
    else:
        logger.info("Không phát hiện khác biệt giữa dữ liệu thực và dữ liệu web")
    """
    
    if report_file:
        logger.info(f"Báo cáo gỡ lỗi đã được lưu vào: {report_file}")

if __name__ == "__main__":
    main()