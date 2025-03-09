"""
Quản lý các module bổ sung trong hệ thống
Module này cung cấp các API để bật/tắt và quản lý các module bổ sung
"""

import logging
import json
import os
import time
import threading
from datetime import datetime
from flask import Blueprint, jsonify, request

# Import các module tích hợp
from integrate_modules import (
    integrate_modules, 
    stop_modules, 
    test_telegram_connection,
    start_detailed_notifications,
    start_position_monitor,
    start_enhanced_market_updater
)

# Thiết lập logging
logger = logging.getLogger('modules_manager')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Đảm bảo thư mục logs tồn tại
os.makedirs('logs', exist_ok=True)

# File handler
file_handler = logging.FileHandler('logs/modules_manager.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Biến lưu trữ trạng thái các module
module_status = {
    'detailed_notifications': False,
    'position_monitor': False,
    'market_updater': False,
    'integrated': False,
    'modules': None
}

# Blueprint cho API
modules_bp = Blueprint('modules', __name__)

@modules_bp.route('/modules/status', methods=['GET'])
def get_modules_status():
    """
    Lấy trạng thái các module
    """
    return jsonify(module_status)

@modules_bp.route('/modules/start', methods=['POST'])
def start_modules():
    """
    Khởi động các module
    """
    try:
        data = request.json or {}
        
        # Lấy các đối tượng từ request (nếu có)
        api_connector = data.get('api_connector', None)
        data_processor = data.get('data_processor', None)
        strategy_engine = data.get('strategy_engine', None)
        
        # Nếu không có các đối tượng này, báo lỗi
        if not all([api_connector, data_processor, strategy_engine]):
            # Import các module cần thiết
            from binance_api import BinanceAPI
            from data_processor import DataProcessor
            from composite_trading_strategy import CompositeTradingStrategy
            
            # Khởi tạo các đối tượng
            api_connector = BinanceAPI()
            data_processor = DataProcessor()
            strategy_engine = CompositeTradingStrategy()
        
        # Tích hợp các module
        modules = integrate_modules(api_connector, data_processor, strategy_engine)
        
        # Cập nhật trạng thái
        module_status['detailed_notifications'] = modules['detailed_notifier'] is not None
        module_status['position_monitor'] = modules['position_monitor'] is not None
        module_status['market_updater'] = modules['market_updater'] is not None
        module_status['integrated'] = True
        module_status['modules'] = modules
        
        logger.info("Đã khởi động tất cả các module thành công")
        
        return jsonify({
            'success': True,
            'message': 'Đã khởi động tất cả các module thành công',
            'status': {
                'detailed_notifications': module_status['detailed_notifications'],
                'position_monitor': module_status['position_monitor'],
                'market_updater': module_status['market_updater'],
                'integrated': module_status['integrated']
            }
        })
    except Exception as e:
        logger.error(f"Lỗi khi khởi động các module: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi khởi động các module: {str(e)}",
            'status': module_status
        }), 500

@modules_bp.route('/modules/stop', methods=['POST'])
def stop_all_modules():
    """
    Dừng tất cả các module
    """
    try:
        if module_status['integrated'] and module_status['modules']:
            # Dừng các module
            success = stop_modules(module_status['modules'])
            
            if success:
                # Cập nhật trạng thái
                module_status['detailed_notifications'] = False
                module_status['position_monitor'] = False
                module_status['market_updater'] = False
                module_status['integrated'] = False
                
                logger.info("Đã dừng tất cả các module thành công")
                
                return jsonify({
                    'success': True,
                    'message': 'Đã dừng tất cả các module thành công',
                    'status': module_status
                })
            else:
                logger.error("Lỗi khi dừng các module")
                return jsonify({
                    'success': False,
                    'message': 'Lỗi khi dừng các module',
                    'status': module_status
                }), 500
        else:
            logger.warning("Không có module nào đang chạy")
            return jsonify({
                'success': False,
                'message': 'Không có module nào đang chạy',
                'status': module_status
            }), 400
    except Exception as e:
        logger.error(f"Lỗi khi dừng các module: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi dừng các module: {str(e)}",
            'status': module_status
        }), 500

@modules_bp.route('/modules/test-telegram', methods=['GET'])
def test_telegram():
    """
    Kiểm tra kết nối Telegram
    """
    try:
        success = test_telegram_connection()
        
        if success:
            logger.info("Kết nối Telegram thành công")
            return jsonify({
                'success': True,
                'message': 'Kết nối Telegram thành công'
            })
        else:
            logger.warning("Kết nối Telegram thất bại")
            return jsonify({
                'success': False,
                'message': 'Kết nối Telegram thất bại'
            }), 400
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}"
        }), 500

def update_telegram_config(bot_token, chat_id):
    """
    Cập nhật cấu hình Telegram
    
    Args:
        bot_token (str): Token bot Telegram
        chat_id (str): ID chat
        
    Returns:
        bool: True nếu cập nhật thành công
    """
    try:
        # Đường dẫn file cấu hình
        config_paths = [
            'telegram_config.json',
            'configs/telegram_notification_config.json'
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                # Đọc cấu hình hiện tại
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Cập nhật cấu hình
                config['bot_token'] = bot_token
                config['chat_id'] = chat_id
                config['enabled'] = True
                
                # Lưu cấu hình mới
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                logger.info(f"Đã cập nhật cấu hình Telegram trong {config_path}")
        
        return True
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình Telegram: {str(e)}")
        return False

@modules_bp.route('/modules/update-telegram-config', methods=['POST'])
def update_telegram_config_route():
    """
    Cập nhật cấu hình Telegram qua API
    """
    try:
        data = request.json
        
        if not data or 'bot_token' not in data or 'chat_id' not in data:
            return jsonify({
                'success': False,
                'message': 'Thiếu thông tin bot_token hoặc chat_id'
            }), 400
        
        bot_token = data['bot_token']
        chat_id = data['chat_id']
        
        # Cập nhật cấu hình
        success = update_telegram_config(bot_token, chat_id)
        
        if success:
            # Kiểm tra kết nối với cấu hình mới
            connection_success = test_telegram_connection()
            
            if connection_success:
                return jsonify({
                    'success': True,
                    'message': 'Đã cập nhật cấu hình Telegram và kết nối thành công'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Đã cập nhật cấu hình nhưng kết nối thất bại, vui lòng kiểm tra lại thông tin'
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': 'Lỗi khi cập nhật cấu hình Telegram'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cấu hình Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi cập nhật cấu hình Telegram: {str(e)}"
        }), 500

@modules_bp.route('/position-monitor/report', methods=['GET'])
def get_position_report():
    """
    Lấy báo cáo về các vị thế hiện tại
    """
    try:
        if not module_status['position_monitor'] or not module_status['modules']:
            return jsonify({
                'success': False,
                'message': 'Module giám sát vị thế chưa được khởi động'
            }), 400
        
        # Lấy monitor từ modules
        monitor = module_status['modules'].get('position_monitor')
        
        if not monitor:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy module giám sát vị thế'
            }), 400
        
        # Phân tích vị thế
        analysis = monitor.analyze_positions()
        
        # Tạo báo cáo văn bản
        report = monitor.generate_positions_report()
        
        return jsonify({
            'success': True,
            'message': 'Đã lấy báo cáo vị thế thành công',
            'data': {
                'analysis': analysis,
                'report': report
            }
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy báo cáo vị thế: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi lấy báo cáo vị thế: {str(e)}"
        }), 500

@modules_bp.route('/position-monitor/send-report', methods=['POST'])
def send_position_report():
    """
    Gửi báo cáo vị thế qua Telegram
    """
    try:
        if not module_status['position_monitor'] or not module_status['modules']:
            return jsonify({
                'success': False,
                'message': 'Module giám sát vị thế chưa được khởi động'
            }), 400
        
        # Lấy monitor từ modules
        monitor = module_status['modules'].get('position_monitor')
        
        if not monitor:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy module giám sát vị thế'
            }), 400
        
        # Gửi báo cáo
        success = monitor.send_positions_report()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Đã gửi báo cáo vị thế thành công'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Lỗi khi gửi báo cáo vị thế qua Telegram'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi gửi báo cáo vị thế: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi gửi báo cáo vị thế: {str(e)}"
        }), 500

@modules_bp.route('/market-updater/update', methods=['POST'])
def trigger_market_update():
    """
    Kích hoạt cập nhật thị trường thủ công
    """
    try:
        if not module_status['market_updater'] or not module_status['modules']:
            return jsonify({
                'success': False,
                'message': 'Module cập nhật thị trường chưa được khởi động'
            }), 400
        
        # Lấy updater từ modules
        updater = module_status['modules'].get('market_updater')
        
        if not updater:
            return jsonify({
                'success': False,
                'message': 'Không tìm thấy module cập nhật thị trường'
            }), 400
        
        # Cập nhật thị trường
        result = updater.update_market()
        
        if result.get('success', False):
            return jsonify({
                'success': True,
                'message': 'Đã cập nhật thị trường thành công',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Lỗi khi cập nhật thị trường: {result.get('error', 'Unknown error')}",
                'data': result
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật thị trường: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Lỗi khi cập nhật thị trường: {str(e)}"
        }), 500

def register_module_routes(app):
    """
    Đăng ký các route cho quản lý module
    
    Args:
        app: Flask app
    """
    app.register_blueprint(modules_bp, url_prefix='/api')
    logger.info("Đã đăng ký các route quản lý module")

# Hàm khởi động module manager
def start_module_manager(api_connector=None, data_processor=None, strategy_engine=None, auto_start=False):
    """
    Khởi động module manager
    
    Args:
        api_connector: API connector (optional)
        data_processor: Bộ xử lý dữ liệu (optional)
        strategy_engine: Engine chiến lược giao dịch (optional)
        auto_start (bool): Tự động khởi động các module
        
    Returns:
        bool: True nếu khởi động thành công
    """
    try:
        logger.info("Khởi động Module Manager...")
        
        if auto_start and api_connector and data_processor and strategy_engine:
            # Tích hợp các module
            modules = integrate_modules(api_connector, data_processor, strategy_engine)
            
            # Cập nhật trạng thái
            module_status['detailed_notifications'] = modules['detailed_notifier'] is not None
            module_status['position_monitor'] = modules['position_monitor'] is not None
            module_status['market_updater'] = modules['market_updater'] is not None
            module_status['integrated'] = True
            module_status['modules'] = modules
            
            logger.info("Đã tự động khởi động tất cả các module")
        
        logger.info("Đã khởi động Module Manager thành công")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi khởi động Module Manager: {str(e)}")
        return False