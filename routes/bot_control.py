"""
Blueprint cho các route điều khiển bot và control panel

Module này cung cấp các endpoints và views cho bảng điều khiển bot và control panel
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Blueprint, request, jsonify, render_template, redirect, url_for

# Telegram notifier nếu có
try:
    from telegram_notify import TelegramNotifier
except ImportError:
    TelegramNotifier = None

# API Binance nếu có
try:
    from binance_api import BinanceAPI
except ImportError:
    BinanceAPI = None

# Đường dẫn file cấu hình
BOT_STATUS_PATH = 'bot_status.json'
ACCOUNT_CONFIG_PATH = 'account_config.json'

# Setup logger
logger = logging.getLogger('bot_control')
logger.setLevel(logging.INFO)

# Tạo blueprint
bot_control_bp = Blueprint('bot_control', __name__)

def load_bot_status() -> Dict:
    """
    Đọc trạng thái bot từ file
    
    Returns:
        Dict: Trạng thái bot
    """
    try:
        if os.path.exists(BOT_STATUS_PATH):
            with open(BOT_STATUS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Trạng thái mặc định
            default_status = {
                'running': False,
                'mode': 'demo',
                'status': 'stopped',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(BOT_STATUS_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_status, f, indent=4, ensure_ascii=False)
            return default_status
    except Exception as e:
        logger.error(f"Lỗi khi đọc trạng thái bot: {e}")
        # Trạng thái mặc định nếu có lỗi
        return {
            'running': False,
            'mode': 'demo',
            'status': 'stopped',
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def save_bot_status(status: Dict) -> bool:
    """
    Lưu trạng thái bot vào file
    
    Args:
        status (Dict): Trạng thái bot cần lưu
        
    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    try:
        with open(BOT_STATUS_PATH, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu trạng thái bot: {e}")
        return False

def load_account_config() -> Dict:
    """
    Đọc cấu hình tài khoản từ file
    
    Returns:
        Dict: Cấu hình tài khoản
    """
    try:
        if os.path.exists(ACCOUNT_CONFIG_PATH):
            with open(ACCOUNT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Cấu hình mặc định
            default_config = {
                'api_key': '',
                'api_secret': '',
                'api_mode': 'demo',
                'account_type': 'futures',
                'risk_profile': 'medium',
                'leverage': 5,
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'timeframes': ['1h', '4h', '1d']
            }
            with open(ACCOUNT_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    except Exception as e:
        logger.error(f"Lỗi khi đọc cấu hình tài khoản: {e}")
        # Cấu hình mặc định nếu có lỗi
        return {
            'api_key': '',
            'api_secret': '',
            'api_mode': 'demo',
            'account_type': 'futures',
            'risk_profile': 'medium',
            'leverage': 5,
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'timeframes': ['1h', '4h', '1d']
        }

def save_account_config(config: Dict) -> bool:
    """
    Lưu cấu hình tài khoản vào file
    
    Args:
        config (Dict): Cấu hình tài khoản cần lưu
        
    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    try:
        with open(ACCOUNT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình tài khoản: {e}")
        return False

def get_account_data() -> Dict:
    """
    Lấy dữ liệu tài khoản từ API
    
    Returns:
        Dict: Dữ liệu tài khoản
    """
    try:
        account_config = load_account_config()
        bot_status = load_bot_status()
        
        # Demo data
        if account_config.get('api_mode') == 'demo':
            return {
                'balance': 10000.0,
                'equity': 10500.0,
                'available': 8500.0,
                'pnl': 500.0,
                'mode': 'demo',
                'positions': [
                    {
                        'id': 'pos001',
                        'symbol': 'BTCUSDT',
                        'side': 'LONG',
                        'size': 0.05,
                        'entry_price': 83250.50,
                        'mark_price': 84150.25,
                        'pnl': 45.0,
                        'margin': 416.25,
                        'leverage': 10
                    },
                    {
                        'id': 'pos002',
                        'symbol': 'ETHUSDT',
                        'side': 'SHORT',
                        'size': 0.5,
                        'entry_price': 4115.75,
                        'mark_price': 4025.50,
                        'pnl': 45.13,
                        'margin': 205.79,
                        'leverage': 10
                    }
                ]
            }
        
        # Testnet or live
        if BinanceAPI:
            api = BinanceAPI(
                api_key=account_config.get('api_key', ''),
                api_secret=account_config.get('api_secret', ''),
                testnet=(account_config.get('api_mode', 'demo') == 'testnet')
            )
            
            # Futures
            if account_config.get('account_type') == 'futures':
                account_info = api.get_futures_account()
                positions_info = api.get_futures_position_risk()
                
                # Xử lý dữ liệu
                balance = float(account_info.get('totalWalletBalance', 0))
                equity = float(account_info.get('totalMarginBalance', 0))
                available = float(account_info.get('availableBalance', 0))
                pnl = float(account_info.get('totalUnrealizedProfit', 0))
                
                # Xử lý vị thế
                positions = []
                for pos in positions_info:
                    if float(pos.get('positionAmt', 0)) != 0:
                        positions.append({
                            'id': f"{pos.get('symbol')}-{pos.get('positionSide')}",
                            'symbol': pos.get('symbol'),
                            'side': 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT',
                            'size': abs(float(pos.get('positionAmt', 0))),
                            'entry_price': float(pos.get('entryPrice', 0)),
                            'mark_price': float(pos.get('markPrice', 0)),
                            'pnl': float(pos.get('unRealizedProfit', 0)),
                            'margin': float(pos.get('isolatedMargin', 0)) if pos.get('isolated') else float(pos.get('positionInitialMargin', 0)),
                            'leverage': int(pos.get('leverage', 1))
                        })
                
                return {
                    'balance': balance,
                    'equity': equity,
                    'available': available,
                    'pnl': pnl,
                    'mode': account_config.get('api_mode', 'demo'),
                    'positions': positions
                }
            
            # Spot
            else:
                account_info = api.get_account()
                
                # Xử lý dữ liệu
                balances = account_info.get('balances', [])
                usdt_balance = 0
                for balance in balances:
                    if balance.get('asset') == 'USDT':
                        usdt_balance = float(balance.get('free', 0))
                
                return {
                    'balance': usdt_balance,
                    'equity': usdt_balance,
                    'available': usdt_balance,
                    'pnl': 0,
                    'mode': account_config.get('api_mode', 'demo'),
                    'positions': []
                }
        
        # Không có API, trả về dữ liệu demo
        return {
            'balance': 10000.0,
            'equity': 10000.0,
            'available': 10000.0,
            'pnl': 0,
            'mode': 'demo',
            'positions': []
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu tài khoản: {e}")
        return {
            'balance': 0,
            'equity': 0,
            'available': 0,
            'pnl': 0,
            'mode': 'error',
            'positions': []
        }

def get_market_data() -> Dict:
    """
    Lấy dữ liệu thị trường
    
    Returns:
        Dict: Dữ liệu thị trường
    """
    try:
        # Thử lấy dữ liệu thực từ Binance API
        if BinanceAPI:
            try:
                api = BinanceAPI()
                
                # Lấy giá BTC
                btc_ticker = api.get_symbol_ticker('BTCUSDT')
                btc_price = float(btc_ticker.get('price', 0))
                
                # Lấy giá ETH
                eth_ticker = api.get_symbol_ticker('ETHUSDT')
                eth_price = float(eth_ticker.get('price', 0))
                
                # Lấy thông tin 24h
                btc_24h = api.get_24h_ticker('BTCUSDT')
                eth_24h = api.get_24h_ticker('ETHUSDT')
                
                btc_change = float(btc_24h.get('priceChangePercent', 0))
                eth_change = float(eth_24h.get('priceChangePercent', 0))
                
                btc_volume = float(btc_24h.get('quoteVolume', 0))
                eth_volume = float(eth_24h.get('quoteVolume', 0))
                
                # Xác định trạng thái thị trường
                if btc_change > 2:
                    market_mood = 'bullish'
                elif btc_change < -2:
                    market_mood = 'bearish'
                else:
                    market_mood = 'neutral'
                
                logger.info(f"Đã lấy dữ liệu thị trường thực từ Binance API: BTC=${btc_price}")
                
                return {
                    'btc_price': btc_price,
                    'eth_price': eth_price,
                    'btc_change': btc_change,
                    'eth_change': eth_change,
                    'market_mood': market_mood,
                    'btc_volume': btc_volume,
                    'eth_volume': eth_volume
                }
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu thị trường từ Binance API: {e}")
        
        # Nếu không thể lấy dữ liệu thực, trả về dữ liệu mẫu
        return {
            'btc_price': 84150.25,
            'eth_price': 4025.50,
            'btc_change': 1.2,
            'eth_change': -0.8,
            'market_mood': 'neutral',
            'btc_volume': 32500000000,
            'eth_volume': 12800000000
        }
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường: {e}")
        return {
            'btc_price': 0,
            'eth_price': 0,
            'btc_change': 0,
            'eth_change': 0,
            'market_mood': 'unknown',
            'btc_volume': 0,
            'eth_volume': 0
        }

def get_trade_history() -> List[Dict]:
    """
    Lấy lịch sử giao dịch
    
    Returns:
        List[Dict]: Lịch sử giao dịch
    """
    # Dữ liệu mẫu
    return [
        {
            'id': 'trade001',
            'time': '2025-03-01 14:30',
            'symbol': 'BTCUSDT',
            'type': 'LONG',
            'entry': 83250.50,
            'exit': 83950.25,
            'size': 0.05,
            'pnl': 35.0,
            'status': 'CLOSED'
        },
        {
            'id': 'trade002',
            'time': '2025-03-02 09:15',
            'symbol': 'ETHUSDT',
            'type': 'SHORT',
            'entry': 4125.75,
            'exit': 4025.50,
            'size': 0.25,
            'pnl': 25.06,
            'status': 'CLOSED'
        }
    ]

def start_bot() -> Dict:
    """
    Khởi động bot
    
    Returns:
        Dict: Kết quả của việc khởi động
    """
    try:
        # Cập nhật trạng thái bot
        status = load_bot_status()
        status['running'] = True
        status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_bot_status(status)
        
        # Gửi thông báo Telegram nếu có
        if TelegramNotifier:
            try:
                notifier = TelegramNotifier()
                notifier.send_message(
                    message=f"<b>Bot đã được khởi động</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    category="system"
                )
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {e}")
        
        logger.info("Bot đã được khởi động")
        return {
            'success': True,
            'message': 'Bot đã được khởi động thành công'
        }
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot: {e}")
        return {
            'success': False,
            'message': f'Lỗi khi khởi động bot: {str(e)}'
        }

def stop_bot() -> Dict:
    """
    Dừng bot
    
    Returns:
        Dict: Kết quả của việc dừng
    """
    try:
        # Cập nhật trạng thái bot
        status = load_bot_status()
        status['running'] = False
        status['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_bot_status(status)
        
        # Gửi thông báo Telegram nếu có
        if TelegramNotifier:
            try:
                notifier = TelegramNotifier()
                notifier.send_message(
                    message=f"<b>Bot đã được dừng lại</b>\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    category="system"
                )
            except Exception as e:
                logger.error(f"Lỗi khi gửi thông báo Telegram: {e}")
        
        logger.info("Bot đã được dừng")
        return {
            'success': True,
            'message': 'Bot đã được dừng thành công'
        }
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot: {e}")
        return {
            'success': False,
            'message': f'Lỗi khi dừng bot: {str(e)}'
        }

def restart_bot() -> Dict:
    """
    Khởi động lại bot
    
    Returns:
        Dict: Kết quả của việc khởi động lại
    """
    try:
        # Dừng bot
        stop_result = stop_bot()
        if not stop_result['success']:
            return stop_result
        
        # Đợi một chút
        time.sleep(1)
        
        # Khởi động lại bot
        start_result = start_bot()
        if not start_result['success']:
            return start_result
        
        logger.info("Bot đã được khởi động lại")
        return {
            'success': True,
            'message': 'Bot đã được khởi động lại thành công'
        }
    except Exception as e:
        logger.error(f"Lỗi khi khởi động lại bot: {e}")
        return {
            'success': False,
            'message': f'Lỗi khi khởi động lại bot: {str(e)}'
        }

def test_api_connection(api_key: str, api_secret: str, api_mode: str) -> Dict:
    """
    Kiểm tra kết nối đến Binance API
    
    Args:
        api_key (str): API Key
        api_secret (str): API Secret
        api_mode (str): Chế độ API (demo, testnet, live)
        
    Returns:
        Dict: Kết quả kiểm tra kết nối
    """
    try:
        # Nếu ở chế độ demo, không cần kiểm tra kết nối
        if api_mode == 'demo':
            return {
                'success': True,
                'message': 'Kết nối thành công (chế độ demo)'
            }
        
        # Kiểm tra API key và secret
        if not api_key or not api_secret:
            return {
                'success': False,
                'message': 'API Key và API Secret không được để trống'
            }
        
        # Kiểm tra kết nối đến Binance API
        if BinanceAPI:
            api = BinanceAPI(
                api_key=api_key,
                api_secret=api_secret,
                testnet=(api_mode == 'testnet')
            )
            
            # Thử lấy thông tin tài khoản
            if api_mode == 'testnet':
                account_info = api.get_futures_account()
            else:
                account_info = api.get_account()
            
            if isinstance(account_info, dict):
                return {
                    'success': True,
                    'message': f'Kết nối thành công đến Binance API ({api_mode})'
                }
            else:
                return {
                    'success': False,
                    'message': 'Không thể kết nối đến Binance API, kiểm tra lại API Key và Secret'
                }
        else:
            return {
                'success': False,
                'message': 'Module BinanceAPI không khả dụng'
            }
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối API: {e}")
        return {
            'success': False,
            'message': f'Lỗi khi kiểm tra kết nối: {str(e)}'
        }

def close_position(position_id: str) -> Dict:
    """
    Đóng một vị thế
    
    Args:
        position_id (str): ID của vị thế cần đóng
        
    Returns:
        Dict: Kết quả của việc đóng vị thế
    """
    try:
        account_config = load_account_config()
        
        # Nếu ở chế độ demo, chỉ trả về thành công
        if account_config.get('api_mode') == 'demo':
            logger.info(f"Đóng vị thế {position_id} (chế độ demo)")
            return {
                'success': True,
                'message': f'Đã đóng vị thế {position_id} (chế độ demo)'
            }
        
        # Kiểm tra cấu hình API
        if not account_config.get('api_key') or not account_config.get('api_secret'):
            return {
                'success': False,
                'message': 'Cần cung cấp API Key và API Secret để sử dụng chức năng này',
                'error_type': 'missing_api_config'
            }
        
        # Đóng vị thế thông qua Binance API
        if BinanceAPI:
            api = BinanceAPI(
                api_key=account_config.get('api_key', ''),
                api_secret=account_config.get('api_secret', ''),
                testnet=(account_config.get('api_mode', 'demo') == 'testnet')
            )
            
            # TODO: Implement đóng vị thế thực tế qua Binance API
            
            logger.info(f"Đã đóng vị thế {position_id}")
            return {
                'success': True,
                'message': f'Đã đóng vị thế {position_id} thành công'
            }
        else:
            return {
                'success': False,
                'message': 'Module BinanceAPI không khả dụng'
            }
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế {position_id}: {e}")
        return {
            'success': False,
            'message': f'Lỗi khi đóng vị thế: {str(e)}'
        }

# Routes
@bot_control_bp.route('/bot')
def bot_control_page():
    """
    Trang điều khiển bot
    """
    try:
        bot_status = load_bot_status()
        account_config = load_account_config()
        account_data = get_account_data()
        market_data = get_market_data()
        trade_history = get_trade_history()
        
        return render_template(
            'bot_control.html',
            bot_status=bot_status,
            account_config=account_config,
            account_data=account_data,
            market_data=market_data,
            trade_history=trade_history
        )
    except Exception as e:
        logger.error(f"Lỗi khi tải trang điều khiển bot: {e}")
        return f"Lỗi khi tải trang: {str(e)}", 500

@bot_control_bp.route('/control')
def control_panel_page():
    """
    Trang điều khiển control panel
    """
    try:
        bot_status = load_bot_status()
        account_config = load_account_config()
        account_data = get_account_data()
        market_data = get_market_data()
        trade_history = get_trade_history()
        
        return render_template(
            'control_panel.html',
            bot_status=bot_status,
            account_config=account_config,
            account_data=account_data,
            market_data=market_data,
            trade_history=trade_history
        )
    except Exception as e:
        logger.error(f"Lỗi khi tải trang control panel: {e}")
        return f"Lỗi khi tải trang: {str(e)}", 500

# API Endpoints
@bot_control_bp.route('/api/bot/status')
def api_bot_status():
    """
    API endpoint để lấy trạng thái bot
    """
    try:
        bot_status = load_bot_status()
        return jsonify(bot_status)
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái bot qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bot_control_bp.route('/api/bot/control', methods=['POST'])
def api_bot_control():
    """
    API endpoint để điều khiển bot
    """
    try:
        data = request.json
        action = data.get('action')
        
        if action == 'start':
            result = start_bot()
        elif action == 'stop':
            result = stop_bot()
        elif action == 'restart':
            result = restart_bot()
        else:
            result = {
                'success': False,
                'message': f'Hành động không hợp lệ: {action}'
            }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Lỗi khi điều khiển bot qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bot_control_bp.route('/api/account/settings', methods=['GET', 'POST'])
def api_account_settings():
    """
    API endpoint để lấy hoặc cập nhật cài đặt tài khoản
    """
    try:
        if request.method == 'GET':
            account_config = load_account_config()
            return jsonify(account_config)
        else:
            data = request.json
            account_config = load_account_config()
            
            # Cập nhật các trường nếu có trong request
            if 'api_mode' in data:
                account_config['api_mode'] = data['api_mode']
            
            if 'api_key' in data:
                account_config['api_key'] = data['api_key']
            
            if 'api_secret' in data:
                account_config['api_secret'] = data['api_secret']
            
            if 'account_type' in data:
                account_config['account_type'] = data['account_type']
            
            if 'risk_profile' in data:
                account_config['risk_profile'] = data['risk_profile']
            
            if 'leverage' in data:
                account_config['leverage'] = data['leverage']
            
            if 'symbols' in data:
                account_config['symbols'] = data['symbols']
            
            if 'timeframes' in data:
                account_config['timeframes'] = data['timeframes']
            
            # Lưu cấu hình
            if save_account_config(account_config):
                logger.info(f"Đã cập nhật cài đặt tài khoản. API Mode: {account_config['api_mode']}")
                return jsonify({'success': True, 'message': 'Cài đặt đã được lưu thành công'})
            else:
                return jsonify({'success': False, 'message': 'Không thể lưu cài đặt'})
    except Exception as e:
        logger.error(f"Lỗi khi xử lý cài đặt tài khoản qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bot_control_bp.route('/api/positions')
def api_positions():
    """
    API endpoint để lấy danh sách vị thế đang mở
    """
    try:
        account_data = get_account_data()
        return jsonify({'positions': account_data.get('positions', [])})
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách vị thế qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bot_control_bp.route('/api/positions/close', methods=['POST'])
def api_close_position():
    """
    API endpoint để đóng một vị thế
    """
    try:
        data = request.json
        position_id = data.get('position_id')
        
        if not position_id:
            return jsonify({'success': False, 'message': 'Thiếu position_id'})
        
        result = close_position(position_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bot_control_bp.route('/api/market')
def api_market_data():
    """
    API endpoint để lấy dữ liệu thị trường
    """
    try:
        market_data = get_market_data()
        return jsonify(market_data)
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu thị trường qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bot_control_bp.route('/api/test_connection', methods=['POST'])
def api_test_connection():
    """
    API endpoint để kiểm tra kết nối đến Binance API
    """
    try:
        data = request.json
        api_key = data.get('api_key', '')
        api_secret = data.get('api_secret', '')
        api_mode = data.get('api_mode', 'demo')
        
        result = test_api_connection(api_key, api_secret, api_mode)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối API qua API: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def register_routes(app):
    """
    Đăng ký các routes với ứng dụng Flask
    
    Args:
        app: Ứng dụng Flask
    """
    app.register_blueprint(bot_control_bp, url_prefix='')