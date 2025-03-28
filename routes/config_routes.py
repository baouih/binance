#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Routes cho cấu hình hệ thống
---------------------------
Module này cung cấp các API cho việc quản lý cấu hình hệ thống
"""

import os
import json
import logging
from typing import Dict, Any, List
from flask import Blueprint, jsonify, request, current_app

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config_routes")

# Khởi tạo Blueprint
config_blueprint = Blueprint('config', __name__, url_prefix='/api/config')

# Đường dẫn đến các file cấu hình
ACCOUNT_CONFIG_PATH = os.environ.get("ACCOUNT_CONFIG_PATH", "account_config.json")
TELEGRAM_CONFIG_PATH = os.environ.get("TELEGRAM_CONFIG_PATH", "telegram_config.json")
BOT_CONFIG_PATH = os.environ.get("BOT_CONFIG_PATH", "bot_config.json")

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Tải cấu hình từ file
    
    :param config_path: Đường dẫn đến file cấu hình
    :return: Dict chứa cấu hình
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"Không tìm thấy file cấu hình: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình từ {config_path}: {str(e)}")
        return {}

def save_config(config_path: str, config_data: Dict[str, Any]) -> bool:
    """
    Lưu cấu hình vào file
    
    :param config_path: Đường dẫn đến file cấu hình
    :param config_data: Dữ liệu cấu hình
    :return: True nếu lưu thành công, False nếu không
    """
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Lưu cấu hình
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Đã lưu cấu hình vào {config_path}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình vào {config_path}: {str(e)}")
        return False

@config_blueprint.route('/account', methods=['GET'])
def get_account_config():
    """Lấy cấu hình tài khoản"""
    try:
        config = load_config(ACCOUNT_CONFIG_PATH)
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy cấu hình tài khoản: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/account', methods=['POST'])
def update_account_config():
    """Cập nhật cấu hình tài khoản"""
    try:
        # Lấy cấu hình hiện tại
        current_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Lấy cấu hình mới từ request
        new_config = request.json
        
        # Cập nhật cấu hình
        if not isinstance(current_config, dict):
            current_config = {}
        
        current_config.update(new_config)
        
        # Lưu cấu hình
        if save_config(ACCOUNT_CONFIG_PATH, current_config):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật cấu hình tài khoản',
                'config': current_config
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình tài khoản'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình tài khoản: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/telegram', methods=['GET'])
def get_telegram_config():
    """Lấy cấu hình Telegram"""
    try:
        config = load_config(TELEGRAM_CONFIG_PATH)
        
        # Ẩn bot_token trong phản hồi
        if 'bot_token' in config:
            config['bot_token'] = '******'
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy cấu hình Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/telegram', methods=['POST'])
def update_telegram_config():
    """Cập nhật cấu hình Telegram"""
    try:
        # Lấy cấu hình hiện tại
        current_config = load_config(TELEGRAM_CONFIG_PATH)
        
        # Lấy cấu hình mới từ request
        new_config = request.json
        
        # Cập nhật cấu hình
        if not isinstance(current_config, dict):
            current_config = {}
        
        current_config.update(new_config)
        
        # Lưu cấu hình
        if save_config(TELEGRAM_CONFIG_PATH, current_config):
            # Tạo phiên bản để trả về mà không có bot_token
            response_config = current_config.copy()
            if 'bot_token' in response_config:
                response_config['bot_token'] = '******'
            
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật cấu hình Telegram',
                'config': response_config
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình Telegram'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/bot', methods=['GET'])
def get_bot_config():
    """Lấy cấu hình bot"""
    try:
        config = load_config(BOT_CONFIG_PATH)
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy cấu hình bot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/bot', methods=['POST'])
def update_bot_config():
    """Cập nhật cấu hình bot"""
    try:
        # Lấy cấu hình hiện tại
        current_config = load_config(BOT_CONFIG_PATH)
        
        # Lấy cấu hình mới từ request
        new_config = request.json
        
        # Cập nhật cấu hình
        if not isinstance(current_config, dict):
            current_config = {}
        
        current_config.update(new_config)
        
        # Lưu cấu hình
        if save_config(BOT_CONFIG_PATH, current_config):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật cấu hình bot',
                'config': current_config
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình bot'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình bot: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/symbols', methods=['GET'])
def get_symbols_config():
    """Lấy danh sách cặp tiền được cấu hình"""
    try:
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Lấy danh sách cặp tiền
        symbols = account_config.get('symbols', [])
        
        # Lấy danh sách cặp tiền được kích hoạt
        enabled_symbols = account_config.get('enabled_symbols', symbols)
        
        return jsonify({
            'success': True,
            'all_symbols': symbols,
            'enabled_symbols': enabled_symbols
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách cặp tiền: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/symbols', methods=['POST'])
def update_symbols_config():
    """Cập nhật danh sách cặp tiền được kích hoạt"""
    try:
        # Lấy danh sách cặp tiền từ request
        data = request.json
        enabled_symbols = data.get('enabled_symbols', [])
        
        # Lấy cấu hình tài khoản hiện tại
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Cập nhật danh sách cặp tiền được kích hoạt
        account_config['enabled_symbols'] = enabled_symbols
        
        # Lưu cấu hình
        if save_config(ACCOUNT_CONFIG_PATH, account_config):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật danh sách cặp tiền được kích hoạt',
                'enabled_symbols': enabled_symbols
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật danh sách cặp tiền: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/risk', methods=['GET'])
def get_risk_config():
    """Lấy cấu hình quản lý rủi ro"""
    try:
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Lấy cấu hình rủi ro
        risk_config = account_config.get('risk_management', {})
        
        return jsonify({
            'success': True,
            'risk_config': risk_config
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy cấu hình quản lý rủi ro: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/risk', methods=['POST'])
def update_risk_config():
    """Cập nhật cấu hình quản lý rủi ro"""
    try:
        # Lấy cấu hình rủi ro từ request
        data = request.json
        risk_config = data.get('risk_config', {})
        
        # Lấy cấu hình tài khoản hiện tại
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Cập nhật cấu hình rủi ro
        account_config['risk_management'] = risk_config
        
        # Lưu cấu hình
        if save_config(ACCOUNT_CONFIG_PATH, account_config):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật cấu hình quản lý rủi ro',
                'risk_config': risk_config
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình quản lý rủi ro: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/strategies', methods=['GET'])
def get_strategies_config():
    """Lấy cấu hình chiến lược giao dịch"""
    try:
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Lấy cấu hình chiến lược
        strategies_config = account_config.get('strategies', {})
        
        return jsonify({
            'success': True,
            'strategies_config': strategies_config
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy cấu hình chiến lược giao dịch: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/strategies', methods=['POST'])
def update_strategies_config():
    """Cập nhật cấu hình chiến lược giao dịch"""
    try:
        # Lấy cấu hình chiến lược từ request
        data = request.json
        strategies_config = data.get('strategies_config', {})
        
        # Lấy cấu hình tài khoản hiện tại
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Cập nhật cấu hình chiến lược
        account_config['strategies'] = strategies_config
        
        # Lưu cấu hình
        if save_config(ACCOUNT_CONFIG_PATH, account_config):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật cấu hình chiến lược giao dịch',
                'strategies_config': strategies_config
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình chiến lược giao dịch: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/timeframes', methods=['GET'])
def get_timeframes_config():
    """Lấy danh sách khung thời gian được cấu hình"""
    try:
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Lấy danh sách khung thời gian
        timeframes = account_config.get('timeframes', ["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
        
        # Lấy khung thời gian mặc định
        default_timeframe = account_config.get('default_timeframe', "1h")
        
        return jsonify({
            'success': True,
            'timeframes': timeframes,
            'default_timeframe': default_timeframe
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách khung thời gian: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/timeframes', methods=['POST'])
def update_timeframes_config():
    """Cập nhật danh sách khung thời gian"""
    try:
        # Lấy dữ liệu từ request
        data = request.json
        timeframes = data.get('timeframes', ["1m", "5m", "15m", "30m", "1h", "4h", "1d"])
        default_timeframe = data.get('default_timeframe', "1h")
        
        # Lấy cấu hình tài khoản hiện tại
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Cập nhật danh sách khung thời gian
        account_config['timeframes'] = timeframes
        account_config['default_timeframe'] = default_timeframe
        
        # Lưu cấu hình
        if save_config(ACCOUNT_CONFIG_PATH, account_config):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật danh sách khung thời gian',
                'timeframes': timeframes,
                'default_timeframe': default_timeframe
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật danh sách khung thời gian: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/api_mode', methods=['GET'])
def get_api_mode():
    """Lấy chế độ API hiện tại"""
    try:
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Lấy chế độ API
        api_mode = account_config.get('api_mode', 'testnet')
        
        return jsonify({
            'success': True,
            'api_mode': api_mode
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy chế độ API: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@config_blueprint.route('/api_mode', methods=['POST'])
def update_api_mode():
    """Cập nhật chế độ API"""
    try:
        # Lấy dữ liệu từ request
        data = request.json
        api_mode = data.get('api_mode', 'testnet')
        
        # Kiểm tra giá trị hợp lệ
        if api_mode not in ['testnet', 'live']:
            return jsonify({
                'success': False,
                'error': 'Chế độ API không hợp lệ. Chỉ chấp nhận "testnet" hoặc "live"'
            }), 400
        
        # Lấy cấu hình tài khoản hiện tại
        account_config = load_config(ACCOUNT_CONFIG_PATH)
        
        # Cập nhật chế độ API
        account_config['api_mode'] = api_mode
        
        # Lưu cấu hình
        if save_config(ACCOUNT_CONFIG_PATH, account_config):
            return jsonify({
                'success': True,
                'message': f'Đã cập nhật chế độ API thành {api_mode}',
                'api_mode': api_mode
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Không thể lưu cấu hình'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật chế độ API: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500