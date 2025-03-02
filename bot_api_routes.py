"""
Blueprint cho các route quản lý API bot
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
                        'message': f'Không tìm thấy API key/secret cho chế độ {api_mode}. Vui lòng cấu hình API trước.'
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

def register_blueprint(app):
    """Đăng ký blueprint với ứng dụng Flask"""
    app.register_blueprint(bot_api_bp)
    logger.info("Đã đăng ký blueprint cho API Bot")