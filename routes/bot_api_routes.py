#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Routes cho quản lý bot
---------------------------
Module này cung cấp các API cho việc quản lý bot giao dịch
"""

import os
import json
import time
import datetime
import logging
import threading
from typing import Dict, Any, List, Optional, Union
from flask import Blueprint, jsonify, request, current_app

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bot_api_routes")

# Khởi tạo Blueprint
bot_api_blueprint = Blueprint('bot_api', __name__, url_prefix='/api/bot')

# Đường dẫn đến các file cấu hình
BOT_CONFIG_PATH = os.environ.get("BOT_CONFIG_PATH", "bot_config.json")
ACCOUNT_CONFIG_PATH = os.environ.get("ACCOUNT_CONFIG_PATH", "account_config.json")

# Trạng thái bot
bots_status = {}
active_bots = []

def load_bots_config() -> List[Dict[str, Any]]:
    """
    Tải cấu hình các bot từ file
    
    :return: List chứa cấu hình các bot
    """
    try:
        if os.path.exists(BOT_CONFIG_PATH):
            with open(BOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                # Kiểm tra định dạng
                if isinstance(config, dict) and 'bots' in config:
                    return config['bots']
                elif isinstance(config, list):
                    return config
                else:
                    logger.warning(f"Định dạng cấu hình bot không đúng: {BOT_CONFIG_PATH}")
                    return []
        else:
            logger.warning(f"Không tìm thấy file cấu hình bot: {BOT_CONFIG_PATH}")
            return []
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình bot từ {BOT_CONFIG_PATH}: {str(e)}")
        return []

def save_bots_config(bots_config: List[Dict[str, Any]]) -> bool:
    """
    Lưu cấu hình các bot vào file
    
    :param bots_config: Danh sách cấu hình các bot
    :return: True nếu lưu thành công, False nếu không
    """
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(BOT_CONFIG_PATH), exist_ok=True)
        
        # Chuẩn bị dữ liệu
        config_data = {
            'bots': bots_config,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lưu cấu hình
        with open(BOT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Đã lưu cấu hình bot vào {BOT_CONFIG_PATH}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình bot vào {BOT_CONFIG_PATH}: {str(e)}")
        return False

def get_bot_status(bot_id: str) -> Dict[str, Any]:
    """
    Lấy trạng thái của bot
    
    :param bot_id: ID của bot
    :return: Trạng thái của bot
    """
    global bots_status
    
    if bot_id in bots_status:
        return bots_status[bot_id]
    else:
        return {
            'status': 'stopped',
            'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def update_bot_status(bot_id: str, status: str) -> None:
    """
    Cập nhật trạng thái của bot
    
    :param bot_id: ID của bot
    :param status: Trạng thái mới
    """
    global bots_status
    
    bots_status[bot_id] = {
        'status': status,
        'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def start_bot(bot_config: Dict[str, Any]) -> bool:
    """
    Khởi động bot
    
    :param bot_config: Cấu hình bot
    :return: True nếu khởi động thành công, False nếu không
    """
    global active_bots
    
    bot_id = bot_config.get('id', str(int(time.time())))
    
    try:
        # Kiểm tra xem bot đã được khởi động chưa
        if bot_id in [b.get('id') for b in active_bots]:
            logger.warning(f"Bot {bot_id} đã được khởi động")
            return False
        
        # Thêm bot vào danh sách active
        active_bots.append(bot_config)
        
        # Cập nhật trạng thái
        update_bot_status(bot_id, 'running')
        
        # Tạo thread mới để chạy bot
        bot_thread = threading.Thread(target=run_bot, args=(bot_config,))
        bot_thread.daemon = True
        bot_thread.start()
        
        logger.info(f"Đã khởi động bot {bot_id}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot {bot_id}: {str(e)}")
        return False

def stop_bot(bot_id: str) -> bool:
    """
    Dừng bot
    
    :param bot_id: ID của bot
    :return: True nếu dừng thành công, False nếu không
    """
    global active_bots
    
    try:
        # Tìm bot trong danh sách active
        for i, bot in enumerate(active_bots):
            if bot.get('id') == bot_id:
                # Xóa bot khỏi danh sách active
                active_bots.pop(i)
                
                # Cập nhật trạng thái
                update_bot_status(bot_id, 'stopped')
                
                logger.info(f"Đã dừng bot {bot_id}")
                return True
        
        logger.warning(f"Không tìm thấy bot {bot_id} trong danh sách active")
        return False
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot {bot_id}: {str(e)}")
        return False

def run_bot(bot_config: Dict[str, Any]) -> None:
    """
    Chạy bot
    
    :param bot_config: Cấu hình bot
    """
    bot_id = bot_config.get('id', str(int(time.time())))
    
    try:
        # Import các module cần thiết
        from binance_api import BinanceAPI
        
        # Lấy thông tin API
        api_key = os.environ.get("BINANCE_API_KEY", "")
        api_secret = os.environ.get("BINANCE_API_SECRET", "")
        
        # Lấy chế độ API từ cấu hình
        account_config = {}
        try:
            with open(ACCOUNT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                account_config = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi tải cấu hình tài khoản: {str(e)}")
        
        api_mode = account_config.get('api_mode', 'testnet')
        use_testnet = api_mode != 'live'
        
        # Khởi tạo Binance API client
        binance_client = BinanceAPI(api_key=api_key, api_secret=api_secret, testnet=use_testnet)
        
        # Lấy cấu hình bot
        bot_type = bot_config.get('type', 'auto_trader')
        bot_name = bot_config.get('name', f'Bot {bot_id}')
        bot_symbols = bot_config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
        bot_timeframe = bot_config.get('timeframe', '1h')
        bot_strategy = bot_config.get('strategy', 'ma_crossover')
        
        logger.info(f"Đang chạy bot {bot_name} (ID: {bot_id}) với chiến lược {bot_strategy}")
        
        # Vòng lặp chính của bot
        while bot_id in [b.get('id') for b in active_bots]:
            try:
                # Kiểm tra thị trường và tìm cơ hội giao dịch
                for symbol in bot_symbols:
                    # Tìm cơ hội giao dịch
                    trade_opportunity = check_trade_opportunity(binance_client, symbol, bot_timeframe, bot_strategy)
                    
                    if trade_opportunity:
                        # Thực hiện giao dịch
                        execute_trade(binance_client, trade_opportunity, bot_config)
                        
                        # Ghi log
                        logger.info(f"Bot {bot_name} đã thực hiện giao dịch: {trade_opportunity}")
                
                # Cập nhật trạng thái
                update_bot_status(bot_id, 'running')
                
            except Exception as e:
                logger.error(f"Lỗi khi chạy bot {bot_name}: {str(e)}")
                update_bot_status(bot_id, 'error')
            
            # Pause để tránh sử dụng quá nhiều CPU
            time.sleep(60)  # Đợi 1 phút trước khi kiểm tra lại
        
        logger.info(f"Bot {bot_name} đã dừng")
        
    except Exception as e:
        logger.error(f"Lỗi nghiêm trọng khi chạy bot {bot_id}: {str(e)}")
        update_bot_status(bot_id, 'error')

def check_trade_opportunity(binance_client, symbol: str, timeframe: str, strategy: str) -> Optional[Dict[str, Any]]:
    """
    Kiểm tra cơ hội giao dịch
    
    :param binance_client: Binance API client
    :param symbol: Cặp giao dịch
    :param timeframe: Khung thời gian
    :param strategy: Chiến lược
    :return: Cơ hội giao dịch nếu có, None nếu không
    """
    try:
        # Lấy dữ liệu lịch sử
        klines = binance_client.get_futures_klines(symbol=symbol, interval=timeframe, limit=100)
        
        # Chuyển đổi dữ liệu
        import pandas as pd
        import numpy as np
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Chuyển đổi kiểu dữ liệu
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Thực hiện phân tích dựa trên chiến lược
        if strategy == 'ma_crossover':
            # Tính MA
            df['ma_fast'] = df['close'].rolling(window=20).mean()
            df['ma_slow'] = df['close'].rolling(window=50).mean()
            
            # Kiểm tra tín hiệu
            buy_signal = df['ma_fast'].iloc[-2] <= df['ma_slow'].iloc[-2] and df['ma_fast'].iloc[-1] > df['ma_slow'].iloc[-1]
            sell_signal = df['ma_fast'].iloc[-2] >= df['ma_slow'].iloc[-2] and df['ma_fast'].iloc[-1] < df['ma_slow'].iloc[-1]
            
            if buy_signal:
                return {
                    'symbol': symbol,
                    'type': 'buy',
                    'price': df['close'].iloc[-1],
                    'strategy': strategy,
                    'timeframe': timeframe,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            elif sell_signal:
                return {
                    'symbol': symbol,
                    'type': 'sell',
                    'price': df['close'].iloc[-1],
                    'strategy': strategy,
                    'timeframe': timeframe,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        
        elif strategy == 'rsi':
            # Tính RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Kiểm tra tín hiệu
            buy_signal = df['rsi'].iloc[-1] < 30
            sell_signal = df['rsi'].iloc[-1] > 70
            
            if buy_signal:
                return {
                    'symbol': symbol,
                    'type': 'buy',
                    'price': df['close'].iloc[-1],
                    'strategy': strategy,
                    'timeframe': timeframe,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            elif sell_signal:
                return {
                    'symbol': symbol,
                    'type': 'sell',
                    'price': df['close'].iloc[-1],
                    'strategy': strategy,
                    'timeframe': timeframe,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
        
        # Thêm các chiến lược khác ở đây
        
        return None
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra cơ hội giao dịch cho {symbol}: {str(e)}")
        return None

def execute_trade(binance_client, trade_opportunity: Dict[str, Any], bot_config: Dict[str, Any]) -> bool:
    """
    Thực hiện giao dịch
    
    :param binance_client: Binance API client
    :param trade_opportunity: Cơ hội giao dịch
    :param bot_config: Cấu hình bot
    :return: True nếu thành công, False nếu không
    """
    try:
        bot_id = bot_config.get('id', '')
        symbol = trade_opportunity.get('symbol', '')
        trade_type = trade_opportunity.get('type', '')
        price = trade_opportunity.get('price', 0)
        
        # Chỉ mô phỏng giao dịch, không thực sự đặt lệnh
        logger.info(f"Bot {bot_id} đã mô phỏng giao dịch: {trade_type.upper()} {symbol} tại giá {price}")
        
        # Ghi log giao dịch
        log_trade(bot_id, trade_opportunity)
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi thực hiện giao dịch: {str(e)}")
        return False

def log_trade(bot_id: str, trade_data: Dict[str, Any]) -> None:
    """
    Ghi log giao dịch
    
    :param bot_id: ID của bot
    :param trade_data: Dữ liệu giao dịch
    """
    try:
        # Tạo thư mục logs nếu chưa tồn tại
        os.makedirs('logs', exist_ok=True)
        
        # Đường dẫn file log
        log_file = os.path.join('logs', f'bot_{bot_id}_trades.json')
        
        # Tạo dữ liệu giao dịch
        trade_log = {
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'bot_id': bot_id,
            'trade_data': trade_data
        }
        
        # Đọc log hiện tại
        trades = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    trades = json.load(f)
            except:
                trades = []
        
        # Thêm giao dịch mới
        trades.append(trade_log)
        
        # Lưu log
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(trades, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Lỗi khi ghi log giao dịch: {str(e)}")

@bot_api_blueprint.route('/all', methods=['GET'])
def get_all_bots():
    """Lấy danh sách tất cả các bot"""
    try:
        bots = load_bots_config()
        
        # Cập nhật trạng thái bot
        for bot in bots:
            bot_id = bot.get('id', '')
            if bot_id:
                bot['status'] = get_bot_status(bot_id)
        
        return jsonify({
            'success': True,
            'bots': bots
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>', methods=['GET'])
def get_bot(bot_id):
    """Lấy thông tin một bot cụ thể"""
    try:
        bots = load_bots_config()
        
        # Tìm bot
        bot = None
        for b in bots:
            if b.get('id') == bot_id:
                bot = b
                break
        
        if not bot:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Cập nhật trạng thái bot
        bot['status'] = get_bot_status(bot_id)
        
        return jsonify({
            'success': True,
            'bot': bot
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/', methods=['POST'])
def create_bot():
    """Tạo bot mới"""
    try:
        # Lấy dữ liệu từ request
        bot_data = request.json
        
        # Kiểm tra dữ liệu
        required_fields = ['name', 'type', 'strategy']
        for field in required_fields:
            if field not in bot_data:
                return jsonify({
                    'success': False,
                    'error': f'Thiếu trường {field}'
                }), 400
        
        # Tạo ID cho bot
        bot_id = str(int(time.time()))
        
        # Tạo bot mới
        new_bot = {
            'id': bot_id,
            'name': bot_data.get('name'),
            'type': bot_data.get('type'),
            'strategy': bot_data.get('strategy'),
            'symbols': bot_data.get('symbols', ['BTCUSDT', 'ETHUSDT']),
            'timeframe': bot_data.get('timeframe', '1h'),
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Thêm bot mới
        bots.append(new_bot)
        
        # Lưu cấu hình
        if save_bots_config(bots):
            return jsonify({
                'success': True,
                'message': f'Đã tạo bot {new_bot["name"]}',
                'bot': new_bot
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình bot'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi tạo bot mới: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>', methods=['PUT'])
def update_bot(bot_id):
    """Cập nhật thông tin bot"""
    try:
        # Lấy dữ liệu từ request
        bot_data = request.json
        
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Tìm bot
        bot_index = -1
        for i, bot in enumerate(bots):
            if bot.get('id') == bot_id:
                bot_index = i
                break
        
        if bot_index == -1:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Cập nhật thông tin bot
        for key, value in bot_data.items():
            if key not in ['id', 'created_at']:
                bots[bot_index][key] = value
        
        # Cập nhật thời gian cập nhật
        bots[bot_index]['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Lưu cấu hình
        if save_bots_config(bots):
            return jsonify({
                'success': True,
                'message': f'Đã cập nhật bot {bots[bot_index]["name"]}',
                'bot': bots[bot_index]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình bot'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>', methods=['DELETE'])
def delete_bot(bot_id):
    """Xóa bot"""
    try:
        # Kiểm tra xem bot có đang chạy không
        for bot in active_bots:
            if bot.get('id') == bot_id:
                # Dừng bot nếu đang chạy
                stop_bot(bot_id)
                break
        
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Tìm bot
        bot_index = -1
        for i, bot in enumerate(bots):
            if bot.get('id') == bot_id:
                bot_index = i
                break
        
        if bot_index == -1:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Lấy tên bot
        bot_name = bots[bot_index].get('name', f'Bot {bot_id}')
        
        # Xóa bot
        bots.pop(bot_index)
        
        # Lưu cấu hình
        if save_bots_config(bots):
            return jsonify({
                'success': True,
                'message': f'Đã xóa bot {bot_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình bot'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi xóa bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>/start', methods=['POST'])
def start_bot_api(bot_id):
    """Khởi động bot"""
    try:
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Tìm bot
        bot = None
        for b in bots:
            if b.get('id') == bot_id:
                bot = b
                break
        
        if not bot:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Kiểm tra xem bot đã đang chạy chưa
        status = get_bot_status(bot_id)
        if status.get('status') == 'running':
            return jsonify({
                'success': False,
                'error': f'Bot {bot["name"]} đang chạy'
            }), 400
        
        # Khởi động bot
        if start_bot(bot):
            return jsonify({
                'success': True,
                'message': f'Đã khởi động bot {bot["name"]}',
                'status': get_bot_status(bot_id)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Không thể khởi động bot {bot["name"]}'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi khởi động bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>/stop', methods=['POST'])
def stop_bot_api(bot_id):
    """Dừng bot"""
    try:
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Tìm bot
        bot = None
        for b in bots:
            if b.get('id') == bot_id:
                bot = b
                break
        
        if not bot:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Kiểm tra xem bot có đang chạy không
        status = get_bot_status(bot_id)
        if status.get('status') != 'running':
            return jsonify({
                'success': False,
                'error': f'Bot {bot["name"]} không đang chạy'
            }), 400
        
        # Dừng bot
        if stop_bot(bot_id):
            return jsonify({
                'success': True,
                'message': f'Đã dừng bot {bot["name"]}',
                'status': get_bot_status(bot_id)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Không thể dừng bot {bot["name"]}'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi dừng bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>/status', methods=['GET'])
def get_bot_status_api(bot_id):
    """Lấy trạng thái bot"""
    try:
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Tìm bot
        bot = None
        for b in bots:
            if b.get('id') == bot_id:
                bot = b
                break
        
        if not bot:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Lấy trạng thái bot
        status = get_bot_status(bot_id)
        
        return jsonify({
            'success': True,
            'bot_name': bot.get('name', f'Bot {bot_id}'),
            'status': status
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy trạng thái bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/<bot_id>/trades', methods=['GET'])
def get_bot_trades(bot_id):
    """Lấy lịch sử giao dịch của bot"""
    try:
        # Lấy danh sách bot hiện tại
        bots = load_bots_config()
        
        # Tìm bot
        bot = None
        for b in bots:
            if b.get('id') == bot_id:
                bot = b
                break
        
        if not bot:
            return jsonify({
                'success': False,
                'error': f'Không tìm thấy bot với ID {bot_id}'
            }), 404
        
        # Đường dẫn file log
        log_file = os.path.join('logs', f'bot_{bot_id}_trades.json')
        
        # Đọc log
        trades = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    trades = json.load(f)
            except:
                trades = []
        
        return jsonify({
            'success': True,
            'bot_name': bot.get('name', f'Bot {bot_id}'),
            'trades': trades
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy lịch sử giao dịch của bot {bot_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bot_api_blueprint.route('/strategies', methods=['GET'])
def get_strategies():
    """Lấy danh sách chiến lược giao dịch"""
    try:
        # Danh sách chiến lược giao dịch có sẵn
        strategies = [
            {
                'id': 'ma_crossover',
                'name': 'MA Crossover',
                'description': 'Chiến lược giao dịch dựa trên giao cắt của đường trung bình động',
                'params': [
                    {
                        'name': 'fast_period',
                        'type': 'int',
                        'default': 20,
                        'description': 'Chu kỳ của đường MA nhanh'
                    },
                    {
                        'name': 'slow_period',
                        'type': 'int',
                        'default': 50,
                        'description': 'Chu kỳ của đường MA chậm'
                    }
                ]
            },
            {
                'id': 'rsi',
                'name': 'RSI',
                'description': 'Chiến lược giao dịch dựa trên chỉ báo RSI',
                'params': [
                    {
                        'name': 'period',
                        'type': 'int',
                        'default': 14,
                        'description': 'Chu kỳ của RSI'
                    },
                    {
                        'name': 'overbought',
                        'type': 'float',
                        'default': 70,
                        'description': 'Ngưỡng quá mua'
                    },
                    {
                        'name': 'oversold',
                        'type': 'float',
                        'default': 30,
                        'description': 'Ngưỡng quá bán'
                    }
                ]
            },
            {
                'id': 'bb',
                'name': 'Bollinger Bands',
                'description': 'Chiến lược giao dịch dựa trên dải Bollinger',
                'params': [
                    {
                        'name': 'period',
                        'type': 'int',
                        'default': 20,
                        'description': 'Chu kỳ của dải Bollinger'
                    },
                    {
                        'name': 'std',
                        'type': 'float',
                        'default': 2,
                        'description': 'Số lần độ lệch chuẩn'
                    }
                ]
            }
        ]
        
        return jsonify({
            'success': True,
            'strategies': strategies
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách chiến lược giao dịch: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500