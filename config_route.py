"""
Blueprint cho các route quản lý cấu hình hệ thống
"""
import os
import json
import logging
from flask import Blueprint, request, jsonify, session

# Thiết lập logging
logger = logging.getLogger('config_routes')

# Khởi tạo blueprint
config_bp = Blueprint('config', __name__)

# Đường dẫn đến file cấu hình
ACCOUNT_CONFIG_PATH = 'account_config.json'

@config_bp.route('/api/account/settings', methods=['GET'])
def get_account_settings():
    """API endpoint để lấy cài đặt tài khoản"""
    try:
        # Đọc cấu hình hiện tại
        if os.path.exists(ACCOUNT_CONFIG_PATH):
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        else:
            # Cấu hình mặc định nếu file không tồn tại
            config = {
                'api_mode': 'demo',
                'api_key': '',
                'api_secret': '',
                'telegram_enabled': False,
                'telegram_bot_token': '',
                'telegram_chat_id': '',
                'notify_new_trades': True,
                'notify_closed_trades': True,
                'notify_error_status': True,
                'notify_daily_summary': False,
                'enable_stop_loss': True,
                'enable_take_profit': True,
                'enable_trailing_stop': False,
                'max_open_positions': 5,
                'max_daily_trades': 20,
                'max_drawdown': 10,
                'auto_restart_enabled': True,
                'log_ip_activity': True
            }
            
            # Lưu cấu hình mặc định
            with open(ACCOUNT_CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=4)
        
        # Lưu chế độ API vào session để các phần khác có thể truy cập
        session['api_mode'] = config.get('api_mode', 'demo')
                
        return jsonify(config)
    except Exception as e:
        logger.error(f"Lỗi khi lấy cài đặt tài khoản: {str(e)}")
        return jsonify({'error': f"Lỗi: {str(e)}"}), 500

@config_bp.route('/api/account/settings', methods=['POST'])
def update_account_settings():
    """API endpoint để cập nhật cài đặt tài khoản"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        # Đọc cấu hình hiện tại
        if os.path.exists(ACCOUNT_CONFIG_PATH):
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Cập nhật cấu hình với dữ liệu mới
        for key, value in data.items():
            # Nếu api_key hoặc api_secret là None, có nghĩa là giữ nguyên giá trị cũ
            if (key == 'api_key' or key == 'api_secret') and value is None:
                continue  # Bỏ qua, giữ nguyên giá trị cũ
            else:
                config[key] = value
        
        # Lưu cấu hình mới
        with open(ACCOUNT_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
            
        # Lưu chế độ API vào session để các phần khác có thể truy cập
        if 'api_mode' in data:
            session['api_mode'] = data['api_mode']
            
        logger.info(f"Đã cập nhật cài đặt tài khoản. API Mode: {data.get('api_mode', 'không rõ')}")
        
        return jsonify({'success': True, 'message': 'Đã cập nhật cài đặt tài khoản thành công'})
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cài đặt tài khoản: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@config_bp.route('/api/notification/settings', methods=['POST'])
def update_notification_settings():
    """API endpoint để cập nhật cài đặt thông báo"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        # Đọc cấu hình hiện tại
        if os.path.exists(ACCOUNT_CONFIG_PATH):
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Cập nhật cấu hình thông báo
        notification_fields = [
            'telegram_enabled', 'telegram_bot_token', 'telegram_chat_id',
            'notify_new_trades', 'notify_closed_trades', 'notify_error_status',
            'notify_daily_summary'
        ]
        
        for field in notification_fields:
            if field in data:
                config[field] = data[field]
        
        # Lưu cấu hình mới
        with open(ACCOUNT_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Đã cập nhật cài đặt thông báo thành công'})
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cài đặt thông báo: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@config_bp.route('/api/security/settings', methods=['POST'])
def update_security_settings():
    """API endpoint để cập nhật cài đặt bảo mật"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        # Đọc cấu hình hiện tại
        if os.path.exists(ACCOUNT_CONFIG_PATH):
            with open(ACCOUNT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Cập nhật cấu hình bảo mật
        security_fields = [
            'enable_stop_loss', 'enable_take_profit', 'enable_trailing_stop',
            'max_open_positions', 'max_daily_trades', 'max_drawdown',
            'auto_restart_enabled', 'log_ip_activity'
        ]
        
        for field in security_fields:
            if field in data:
                config[field] = data[field]
        
        # Lưu cấu hình mới
        with open(ACCOUNT_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Đã cập nhật cài đặt bảo mật thành công'})
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật cài đặt bảo mật: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

@config_bp.route('/api/telegram/test', methods=['POST'])
def test_telegram():
    """API endpoint để kiểm tra kết nối Telegram"""
    try:
        data = request.get_json()
        
        if not data or 'bot_token' not in data or 'chat_id' not in data:
            return jsonify({'success': False, 'message': 'Thiếu thông tin bot token hoặc chat ID'}), 400
        
        bot_token = data['bot_token']
        chat_id = data['chat_id']
        message = data.get('message')  # Lấy tin nhắn tùy chỉnh nếu có
        
        # Sử dụng module telegram_notify để gửi tin nhắn test
        try:
            from telegram_notify import TelegramNotifier
            
            # Khởi tạo notifier tạm thời với token và chat_id được cung cấp
            temp_notifier = TelegramNotifier(token=bot_token, chat_id=chat_id)
            
            # Gửi tin nhắn test
            if message:
                # Nếu có tin nhắn tùy chỉnh, sử dụng tin nhắn đó
                success = temp_notifier.send_message(message, parse_mode="HTML")
            else:
                # Sử dụng hàm gửi tin nhắn kiểm tra có sẵn với định dạng đẹp
                success = temp_notifier.send_test_message()
            
            if success:
                logger.info(f"Đã gửi tin nhắn test đến Telegram chat ID: {chat_id}")
                
                # Lưu token và chat_id tạm thời để sử dụng khi lưu cài đặt
                return jsonify({
                    'success': True, 
                    'message': 'Đã gửi tin nhắn test thành công. Vui lòng kiểm tra Telegram của bạn.'
                })
            else:
                logger.error(f"Không thể gửi tin nhắn Telegram")
                return jsonify({
                    'success': False, 
                    'message': 'Không thể gửi tin nhắn test. Vui lòng kiểm tra token và chat ID.'
                }), 400
        
        except Exception as telegram_error:
            logger.error(f"Lỗi khi sử dụng telegram_notify: {str(telegram_error)}")
            
            # Fallback: Sử dụng cách gửi tin nhắn qua requests trực tiếp nếu module có vấn đề
            try:
                import requests
                telegram_api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                default_message = """🧪 <b>KIỂM TRA KẾT NỐI TELEGRAM</b>

✅ Bot giao dịch đã kết nối thành công với Telegram!

<b>Bạn sẽ nhận được các thông báo sau:</b>
• 💰 Thông tin số dư tài khoản
• 📊 Vị thế đang mở/đóng
• 🤖 Trạng thái bot (chạy/dừng)
• 📈 Phân tích thị trường
• ⚙️ Thay đổi cấu hình
• 📑 Báo cáo lãi/lỗ định kỳ

⏰ """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                payload = {
                    'chat_id': chat_id,
                    'text': message or default_message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(telegram_api_url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"[Fallback] Đã gửi tin nhắn test đến Telegram chat ID: {chat_id}")
                    return jsonify({'success': True, 'message': 'Đã gửi tin nhắn test thành công'})
                else:
                    logger.error(f"Lỗi gửi tin nhắn Telegram: {response.text}")
                    return jsonify({
                        'success': False, 
                        'message': f'Lỗi Telegram API: {response.status_code} - {response.text}'
                    }), 400
            except Exception as req_error:
                logger.error(f"Lỗi kết nối Telegram (fallback): {str(req_error)}")
                return jsonify({
                    'success': False, 
                    'message': f'Lỗi kết nối Telegram: {str(req_error)}'
                }), 500
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra Telegram: {str(e)}")
        return jsonify({'success': False, 'message': f"Lỗi: {str(e)}"}), 500

def register_blueprint(app):
    """Đăng ký blueprint với ứng dụng Flask"""
    app.register_blueprint(config_bp)
    logger.info("Đã đăng ký blueprint cho cấu hình")