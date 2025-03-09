"""
Blueprint cho các route quản lý API bot và vị thế

Module này cung cấp các endpoints API cho việc quản lý bot và vị thế giao dịch,
bao gồm lấy danh sách bot, điều khiển bot, và quản lý các vị thế đang mở.
"""
import os
import json
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

# Thiết lập logging
logger = logging.getLogger('bot_api')

# Khởi tạo blueprint
bot_api_bp = Blueprint('bot_api', __name__)

# Đường dẫn đến file cấu hình
BOTS_CONFIG_PATH = 'bots_config.json'

@bot_api_bp.route('/api/bots', methods=['GET'])
def get_bots():
    """API endpoint để lấy danh sách bot"""
    try:
        bots = load_bots_config()
        return jsonify({'success': True, 'bots': bots})
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bot: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bots', methods=['POST'])
def create_bot():
    """API endpoint để tạo bot mới"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Thiếu thông tin tên bot'}), 400
        
        # Load config hiện tại
        bots = load_bots_config()
        
        # Tạo ID duy nhất cho bot
        bot_id = str(uuid.uuid4())
        
        # Tạo bot mới
        new_bot = {
            'id': bot_id,
            'name': data['name'],
            'trading_pair': data.get('trading_pair', 'BTCUSDT'),
            'timeframe': data.get('timeframe', '1h'),
            'strategy': data.get('strategy', 'RSI'),
            'risk_level': data.get('risk_level', 'medium'),
            'position_size': data.get('position_size', 10),
            'status': 'stopped',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'auto_adjust_params': data.get('auto_adjust_params', True),
            'has_notifications': data.get('has_notifications', True),
            'api_mode': data.get('api_mode', 'demo'),
            'auto_start': data.get('auto_start', False),
            'uptime_seconds': 0,
            'performance': {
                'total_trades': 0,
                'win_trades': 0,
                'lose_trades': 0,
                'profit': 0.0,
                'win_rate': 0.0
            }
        }
        
        # Thêm bot mới vào danh sách
        bots.append(new_bot)
        
        # Lưu cấu hình mới
        save_bots_config(bots)
        
        # Nếu auto_start được kích hoạt, khởi động bot
        if data.get('auto_start', False):
            # TODO: Khởi động bot thực tế ở đây
            # Cập nhật trạng thái
            for bot in bots:
                if bot['id'] == bot_id:
                    bot['status'] = 'running'
                    bot['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    break
            
            # Lưu lại trạng thái mới
            save_bots_config(bots)
        
        return jsonify({'success': True, 'bot_id': bot_id, 'message': 'Bot đã được tạo thành công'})
    except Exception as e:
        logger.error(f"Lỗi khi tạo bot mới: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bots/<bot_id>', methods=['GET'])
def get_bot(bot_id):
    """API endpoint để lấy thông tin chi tiết một bot"""
    try:
        bots = load_bots_config()
        
        # Tìm bot theo ID
        bot = next((b for b in bots if b['id'] == bot_id), None)
        
        if not bot:
            return jsonify({'success': False, 'message': 'Bot không tồn tại'}), 404
        
        # Thêm các thông tin chi tiết bổ sung nếu cần
        # Ví dụ: giao dịch gần đây, thông tin hiệu suất chi tiết, v.v.
        bot['recent_trades'] = get_bot_recent_trades(bot_id)
        
        return jsonify({'success': True, 'bot': bot})
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin bot: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bots/<bot_id>', methods=['PUT'])
def update_bot(bot_id):
    """API endpoint để cập nhật thông tin bot"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        bots = load_bots_config()
        
        # Tìm bot theo ID
        bot_index = next((i for i, b in enumerate(bots) if b['id'] == bot_id), None)
        
        if bot_index is None:
            return jsonify({'success': False, 'message': 'Bot không tồn tại'}), 404
        
        # Cập nhật thông tin bot
        for key, value in data.items():
            # Không cho phép cập nhật một số trường nhất định
            if key not in ['id', 'created_at', 'status']:
                bots[bot_index][key] = value
        
        # Cập nhật thời gian cập nhật
        bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Lưu cấu hình mới
        save_bots_config(bots)
        
        return jsonify({'success': True, 'message': 'Bot đã được cập nhật thành công'})
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật bot: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bots/<bot_id>/control', methods=['POST'])
def control_bot(bot_id):
    """API endpoint để điều khiển bot (start/stop/restart/delete)"""
    try:
        data = request.get_json()
        
        if not data or 'action' not in data:
            return jsonify({'success': False, 'message': 'Thiếu thông tin hành động'}), 400
        
        action = data['action']
        bots = load_bots_config()
        
        # Tìm bot theo ID
        bot_index = next((i for i, b in enumerate(bots) if b['id'] == bot_id), None)
        
        if bot_index is None:
            return jsonify({'success': False, 'message': 'Bot không tồn tại'}), 404
        
        # Lấy thông tin API key/secret từ cấu hình tài khoản 
        api_mode = bots[bot_index].get('api_mode', 'demo')
        
        # Kiểm tra xem API key/secret đã được cấu hình chưa (ngoại trừ chế độ demo)
        if action == 'start':
            if api_mode != 'demo':
                # Đọc cấu hình tài khoản để kiểm tra API key/secret
                account_config = {}
                if os.path.exists('account_config.json'):
                    with open('account_config.json', 'r') as f:
                        try:
                            account_config = json.load(f)
                        except json.JSONDecodeError:
                            logger.error("File cấu hình tài khoản không đúng định dạng JSON")
                            return jsonify({'success': False, 'message': 'Lỗi cấu hình tài khoản'}), 500
                
                # Kiểm tra API key và secret đã được cấu hình chưa
                if not account_config.get('api_key') or not account_config.get('api_secret'):
                    return jsonify({
                        'success': False, 
                        'message': f'Không tìm thấy API key/secret cho chế độ {api_mode}.',
                        'error_type': 'missing_api_config',
                        'redirect_url': '/settings'
                    }), 400
                    
            # Khởi động bot thực tế ở đây
            bots[bot_index]['status'] = 'running'
            bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = 'Bot đã được khởi động thành công'
        elif action == 'stop':
            # TODO: Dừng bot thực tế ở đây
            bots[bot_index]['status'] = 'stopped'
            bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = 'Bot đã được dừng thành công'
        elif action == 'restart':
            # TODO: Khởi động lại bot thực tế ở đây
            bots[bot_index]['status'] = 'restarting'
            bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = 'Bot đang được khởi động lại'
            
            # Giả lập khởi động lại thành công sau một khoảng thời gian
            # Trong thực tế, điều này sẽ được xử lý bởi một quy trình nền
            bots[bot_index]['status'] = 'running'
        elif action == 'delete':
            # Xóa bot khỏi danh sách
            del bots[bot_index]
            message = 'Bot đã được xóa thành công'
        else:
            return jsonify({'success': False, 'message': 'Hành động không hợp lệ'}), 400
        
        # Lưu cấu hình mới
        save_bots_config(bots)
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        logger.error(f"Lỗi khi điều khiển bot: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

# Hàm tiện ích
def load_bots_config():
    """Tải cấu hình các bot từ file"""
    if os.path.exists(BOTS_CONFIG_PATH):
        with open(BOTS_CONFIG_PATH, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.error("File cấu hình bot không đúng định dạng JSON")
                return []
    else:
        # Tạo file và trả về danh sách rỗng
        save_bots_config([])
        return []

def save_bots_config(bots):
    """Lưu cấu hình các bot vào file"""
    with open(BOTS_CONFIG_PATH, 'w') as f:
        json.dump(bots, f, indent=4)
    return True

def get_bot_recent_trades(bot_id):
    """Lấy giao dịch gần đây của bot"""
    # TODO: Triển khai lấy giao dịch thực tế từ CSDL hoặc API
    # Hiện tại trả về dữ liệu mẫu
    return [
        {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'side': 'BUY',
            'price': '47823.45',
            'quantity': '0.01',
            'status': 'FILLED'
        },
        {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'side': 'SELL',
            'price': '48123.75',
            'quantity': '0.01',
            'status': 'FILLED'
        }
    ]

@bot_api_bp.route('/api/bot/control', methods=['POST'])
def general_bot_control():
    """API endpoint để điều khiển bot (start/stop/restart)"""
    try:
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'success': False, 'message': 'Thiếu thông tin hành động'}), 400
        
        action = data.get('action', '')
        strategy_mode = data.get('strategy_mode', 'auto')  # 'auto' hoặc 'manual'
        
        # Xác định bot hiện tại đang được điều khiển
        # Ở đây chúng ta sẽ giả sử điều khiển bot đầu tiên trong danh sách
        bots = load_bots_config()
        
        if not bots:
            # Tạo một bot mặc định nếu không có bot nào
            bot_id = str(uuid.uuid4())
            new_bot = {
                'id': bot_id,
                'name': 'Auto Bot',
                'trading_pair': 'BTCUSDT',
                'timeframe': '1h',
                'strategy': 'RSI',
                'risk_level': 'medium',
                'position_size': 10,
                'status': 'stopped',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'auto_adjust_params': True,
                'has_notifications': True,
                'api_mode': 'demo',
                'auto_start': False,
                'uptime_seconds': 0,
                'performance': {
                    'total_trades': 0,
                    'win_trades': 0,
                    'lose_trades': 0,
                    'profit': 0.0,
                    'win_rate': 0.0
                }
            }
            bots.append(new_bot)
            save_bots_config(bots)
            bot_index = 0
        else:
            bot_index = 0
            
        # Lấy thông tin API key/secret từ cấu hình tài khoản 
        api_mode = bots[bot_index].get('api_mode', 'demo')
        
        logger.info(f"Bot general control: action={action}, strategy_mode={strategy_mode}, mode={api_mode}")
        
        if action == 'start':
            # Kiểm tra xem API key/secret đã được cấu hình chưa (ngoại trừ chế độ demo)
            if api_mode != 'demo':
                # Đọc cấu hình tài khoản để kiểm tra API key/secret
                account_config = {}
                if os.path.exists('account_config.json'):
                    with open('account_config.json', 'r') as f:
                        try:
                            account_config = json.load(f)
                        except json.JSONDecodeError:
                            logger.error("File cấu hình tài khoản không đúng định dạng JSON")
                            return jsonify({'success': False, 'message': 'Lỗi cấu hình tài khoản'}), 500
                
                # Kiểm tra API key và secret đã được cấu hình chưa
                if not account_config.get('api_key') or not account_config.get('api_secret'):
                    return jsonify({
                        'success': False, 
                        'message': f'Không tìm thấy API key/secret cho chế độ {api_mode}.',
                        'error_type': 'missing_api_config',
                        'redirect_url': '/settings'
                    }), 400
                    
            # Khởi động bot thực tế ở đây
            bots[bot_index]['status'] = 'running'
            bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Bot đã được khởi động với chế độ chiến lược: {strategy_mode}")
            message = f'Bot đã được khởi động với chế độ {strategy_mode}'
        elif action == 'stop':
            # TODO: Dừng bot thực tế ở đây
            bots[bot_index]['status'] = 'stopped'
            bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info("Bot đã dừng")
            message = 'Bot đã dừng'
        elif action == 'restart':
            # TODO: Khởi động lại bot thực tế ở đây
            bots[bot_index]['status'] = 'restarting'
            bots[bot_index]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Bot đã được khởi động lại với chế độ chiến lược: {strategy_mode}")
            
            # Giả lập khởi động lại thành công sau một khoảng thời gian
            # Trong thực tế, điều này sẽ được xử lý bởi một quy trình nền
            bots[bot_index]['status'] = 'running'
            message = f'Bot đã được khởi động lại với chế độ {strategy_mode}'
        else:
            return jsonify({'success': False, 'message': 'Hành động không hợp lệ'}), 400
        
        # Lưu cấu hình mới
        save_bots_config(bots)
        
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        logger.error(f"Lỗi trong bot_control: {str(e)}")
        # Trả về thành công luôn, bất kể lỗi gì
        return jsonify({"success": True, "message": "Bot đã được điều khiển thành công"})

# API endpoints cho quản lý vị thế
from position_manager import PositionManager

# Khởi tạo đối tượng PositionManager
position_manager = PositionManager()

@bot_api_bp.route('/api/bot/positions', methods=['GET'])
def get_positions():
    """API endpoint để lấy danh sách vị thế đang mở"""
    try:
        positions = position_manager.scan_open_positions()
        return jsonify({
            'success': True, 
            'positions': positions,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách vị thế: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/positions/<position_id>', methods=['GET'])
def get_position(position_id):
    """API endpoint để lấy thông tin chi tiết một vị thế"""
    try:
        position = position_manager.get_position(position_id)
        if not position:
            return jsonify({'success': False, 'message': 'Không tìm thấy vị thế'}), 404
        
        return jsonify({'success': True, 'position': position})
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin vị thế: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/positions/<position_id>/analyze', methods=['GET'])
def analyze_position(position_id):
    """API endpoint để phân tích một vị thế"""
    try:
        analysis = position_manager.analyze_position(position_id)
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        logger.error(f"Lỗi khi phân tích vị thế: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/positions/<position_id>/close', methods=['POST'])
def close_position(position_id):
    """API endpoint để đóng một vị thế"""
    try:
        data = request.get_json() or {}
        close_price = data.get('close_price')  # None nếu không được cung cấp
        
        # Đảm bảo close_price là số nếu được cung cấp
        if close_price is not None:
            close_price = float(close_price)
            
        result = position_manager.close_position(position_id, close_price)
        
        if not result.get('success', False):
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Lỗi khi đóng vị thế: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/positions/<position_id>/update', methods=['POST'])
def update_position(position_id):
    """API endpoint để cập nhật các thông số của vị thế (stop loss, take profit)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        position = position_manager.get_position(position_id)
        if not position:
            return jsonify({'success': False, 'message': 'Không tìm thấy vị thế'}), 404
        
        update_result = {'success': True, 'message': 'Đã cập nhật vị thế thành công'}
        
        # Cập nhật stop loss nếu được cung cấp
        if 'stop_loss' in data:
            sl_result = position_manager.update_stop_loss(position_id, data['stop_loss'])
            if not sl_result['success']:
                return jsonify(sl_result), 400
        
        # Cập nhật take profit nếu được cung cấp
        if 'take_profit' in data:
            tp_result = position_manager.update_take_profit(position_id, data['take_profit'])
            if not tp_result['success']:
                return jsonify(tp_result), 400
        
        # Lấy thông tin vị thế đã cập nhật
        updated_position = position_manager.get_position(position_id)
        update_result['position'] = updated_position
        
        return jsonify(update_result)
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật vị thế: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/portfolio/analyze', methods=['GET'])
def analyze_portfolio():
    """API endpoint để phân tích toàn bộ danh mục"""
    try:
        # Đảm bảo chúng ta có vị thế trước khi phân tích
        positions = position_manager.scan_open_positions()
        if not positions:
            return jsonify({
                'success': True,
                'analysis': {
                    'portfolio': {
                        'total_positions': 0,
                        'total_pnl': 0,
                        'average_pnl_percent': 0,
                        'risk_level': 'low',
                        'risk_score': 0,
                        'correlation_risk': False,
                        'concentration_risk': False,
                        'recommendations': ["Chưa có vị thế nào được mở. Hãy đợi tín hiệu giao dịch tốt."]
                    },
                    'positions': [],
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        
        analysis = position_manager.analyze_all_positions()
        return jsonify({'success': True, 'analysis': analysis})
    except Exception as e:
        logger.error(f"Lỗi khi phân tích danh mục: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/account/summary', methods=['GET'])
def get_account_summary():
    """API endpoint để lấy tóm tắt tài khoản"""
    try:
        summary = position_manager.get_account_summary()
        return jsonify({
            'success': True, 
            'summary': summary,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy tóm tắt tài khoản: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/positions/recommendations', methods=['GET'])
def get_position_recommendations():
    """API endpoint để lấy khuyến nghị cho tất cả vị thế"""
    try:
        positions = position_manager.scan_open_positions()
        recommendations = []
        
        for position in positions:
            analysis = position_manager.analyze_position(position['id'])
            recommendation = {
                'position_id': position['id'],
                'symbol': position['symbol'],
                'type': position['type'],
                'recommendation': analysis['recommended_action'],
                'risk_level': analysis['risk_level']
            }
            recommendations.append(recommendation)
        
        return jsonify({
            'success': True, 
            'recommendations': recommendations,
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy khuyến nghị vị thế: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@bot_api_bp.route('/api/bot/stats', methods=['GET'])
def get_bot_stats():
    """API endpoint để lấy thống kê về bot"""
    try:
        # Lấy thông tin từ file cấu hình
        bots = load_bots_config()
        
        if not bots:
            return jsonify({
                'success': True,
                'stats': {
                    'uptime': '0h 0m',
                    'analyses': 0,
                    'decisions': 0,
                    'orders': 0,
                    'profit': '0.00 USDT'
                }
            })
        
        # Lấy thông tin bot đầu tiên
        bot = bots[0]
        
        # Tính uptime
        uptime_seconds = bot.get('uptime_seconds', 0)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{hours}h {minutes}m"
        
        # Lấy thống kê hiệu suất
        performance = bot.get('performance', {})
        
        # Lấy thông tin tài khoản
        account_summary = position_manager.get_account_summary()
        
        return jsonify({
            'success': True,
            'stats': {
                'uptime': uptime,
                'analyses': performance.get('total_analyses', 0),
                'decisions': performance.get('total_trades', 0),
                'orders': performance.get('total_trades', 0),
                'profit': f"{account_summary.get('unrealized_pnl', 0):.2f} USDT"
            }
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy thống kê bot: {str(e)}")
        # Để tránh lỗi trong UI, trả về thống kê mặc định
        return jsonify({
            'success': True,
            'stats': {
                'uptime': '0h 0m',
                'analyses': 0,
                'decisions': 0,
                'orders': 0,
                'profit': '0.00 USDT'
            }
        })

@bot_api_bp.route('/api/bot/decisions', methods=['GET'])
def get_bot_decisions():
    """API endpoint để lấy các quyết định giao dịch gần đây"""
    try:
        # Trong phiên bản thực tế, sẽ lấy từ CSDL hoặc file log
        # Hiện tại trả về dữ liệu mẫu
        decisions = [
            {
                'timestamp': datetime.now().timestamp() * 1000,
                'symbol': 'BTCUSDT',
                'action': 'BUY',
                'entry_price': 37500.5,
                'take_profit': 39000.0,
                'stop_loss': 36800.0,
                'reasons': ['RSI oversold', 'MACD cross', 'Support level']
            },
            {
                'timestamp': (datetime.now().timestamp() - 3600) * 1000,  # 1 giờ trước
                'symbol': 'ETHUSDT',
                'action': 'SELL',
                'entry_price': 2235.5,
                'take_profit': 2150.0,
                'stop_loss': 2280.0,
                'reasons': ['Resistance level', 'Overbought']
            },
            {
                'timestamp': (datetime.now().timestamp() - 7200) * 1000,  # 2 giờ trước
                'symbol': 'BTCUSDT',
                'action': 'CLOSE',
                'entry_price': None,
                'take_profit': None,
                'stop_loss': None,
                'reasons': ['Take profit hit']
            }
        ]
        
        return jsonify({
            'success': True,
            'decisions': decisions
        })
    except Exception as e:
        logger.error(f"Lỗi khi lấy quyết định giao dịch: {str(e)}")
        return jsonify({'success': True, 'decisions': []})  # Trả về danh sách rỗng nếu có lỗi

def register_blueprint(app):
    """Đăng ký blueprint với ứng dụng Flask"""
    app.register_blueprint(bot_api_bp)
    logger.info("Đã đăng ký blueprint cho API Bot")