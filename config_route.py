#!/usr/bin/env python3
"""
Xử lý cấu hình thông báo và báo cáo cho Bot Trading

Module này cung cấp các route và hàm xử lý để quản lý cấu hình thông báo
và lập lịch báo cáo qua Telegram và Email
"""

import os
import json
import logging
from flask import render_template, request, jsonify, Blueprint
from dotenv import load_dotenv, set_key

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("config_route")

# Tạo Blueprint
config_bp = Blueprint('config', __name__)

# Đường dẫn đến file cấu hình
report_config_file = "report_config.json"

# Cấu hình mặc định
default_config = {
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "email_user": "",
        "recipients": [],
        "schedules": {
            "daily_report": "18:00",
            "signal_report": "08:00,16:00",
            "market_report": "09:00",
            "training_report": "after_training"
        }
    },
    "telegram": {
        "enabled": False,
        "schedules": {
            "daily_report": "18:00",
            "signal_report": "08:00,12:00,16:00,20:00",
            "market_report": "09:00,21:00",
            "training_report": "after_training"
        }
    },
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "AVAXUSDT", "DOGEUSDT", "ADAUSDT", "DOTUSDT"]
}

def load_config():
    """
    Tải cấu hình từ file
    
    Returns:
        dict: Cấu hình báo cáo
    """
    if not os.path.exists(report_config_file):
        return default_config
    
    try:
        with open(report_config_file, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình: {e}")
        return default_config

def save_config(config):
    """
    Lưu cấu hình vào file
    
    Args:
        config (dict): Cấu hình báo cáo
        
    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    try:
        with open(report_config_file, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình: {e}")
        return False

def update_env_variables(env_vars):
    """
    Cập nhật biến môi trường từ cấu hình
    
    Args:
        env_vars (dict): Các biến môi trường cần cập nhật
    """
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Cập nhật file .env nếu tồn tại
    env_file = ".env"
    if os.path.exists(env_file):
        for key, value in env_vars.items():
            set_key(env_file, key, value)

@config_bp.route('/config')
def config_page():
    """Trang cấu hình thông báo và báo cáo"""
    return render_template('config.html')

@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """API lấy cấu hình hiện tại"""
    config = load_config()
    
    # Bỏ qua thông tin nhạy cảm
    if "email" in config and "email_password" in config["email"]:
        config["email"]["email_password"] = "********"
    
    return jsonify(config)

@config_bp.route('/api/config/telegram', methods=['POST'])
def save_telegram_config():
    """API lưu cấu hình Telegram"""
    data = request.json
    config = load_config()
    
    # Cập nhật cấu hình Telegram
    config["telegram"]["enabled"] = True
    
    # Cập nhật biến môi trường
    env_vars = {}
    
    if "botToken" in data and data["botToken"]:
        env_vars["TELEGRAM_BOT_TOKEN"] = data["botToken"]
    
    if "chatId" in data and data["chatId"]:
        env_vars["TELEGRAM_CHAT_ID"] = data["chatId"]
    
    if "notifications" in data:
        config["telegram"]["notifications"] = data["notifications"]
    
    # Lưu cấu hình
    success = save_config(config)
    
    # Cập nhật biến môi trường
    if success and env_vars:
        update_env_variables(env_vars)
    
    return jsonify({"success": success})

@config_bp.route('/api/config/email', methods=['POST'])
def save_email_config():
    """API lưu cấu hình Email"""
    data = request.json
    config = load_config()
    
    # Cập nhật cấu hình Email
    config["email"]["enabled"] = True
    
    if "smtpServer" in data and data["smtpServer"]:
        config["email"]["smtp_server"] = data["smtpServer"]
        env_vars["EMAIL_SMTP_SERVER"] = data["smtpServer"]
    
    if "smtpPort" in data and data["smtpPort"]:
        config["email"]["smtp_port"] = int(data["smtpPort"])
        env_vars["EMAIL_SMTP_PORT"] = str(data["smtpPort"])
    
    if "emailUser" in data and data["emailUser"]:
        config["email"]["email_user"] = data["emailUser"]
        env_vars["EMAIL_USER"] = data["emailUser"]
    
    if "emailPassword" in data and data["emailPassword"]:
        # Lưu vào biến môi trường, không lưu vào file cấu hình
        env_vars["EMAIL_PASSWORD"] = data["emailPassword"]
    
    if "recipients" in data and data["recipients"]:
        config["email"]["recipients"] = data["recipients"]
        if data["recipients"]:
            env_vars["REPORT_EMAIL"] = data["recipients"][0]
    
    if "reports" in data:
        config["email"]["reports"] = data["reports"]
    
    # Lưu cấu hình
    success = save_config(config)
    
    # Cập nhật biến môi trường
    if success and env_vars:
        update_env_variables(env_vars)
    
    return jsonify({"success": success})

@config_bp.route('/api/config/schedule', methods=['POST'])
def save_schedule_config():
    """API lưu cấu hình lịch trình báo cáo"""
    data = request.json
    config = load_config()
    
    # Cập nhật lịch trình Telegram
    if "telegram" in data:
        for report_type, time in data["telegram"].items():
            config["telegram"]["schedules"][report_type] = time
    
    # Cập nhật lịch trình Email
    if "email" in data:
        for report_type, time in data["email"].items():
            config["email"]["schedules"][report_type] = time
    
    # Lưu cấu hình
    success = save_config(config)
    
    return jsonify({"success": success})

@config_bp.route('/api/test/telegram', methods=['POST'])
def test_telegram():
    """API kiểm tra kết nối Telegram"""
    data = request.json
    bot_token = data.get("botToken")
    chat_id = data.get("chatId")
    
    if not bot_token or not chat_id:
        return jsonify({"success": False, "message": "Thiếu Bot Token hoặc Chat ID"})
    
    try:
        # Import telegram_notifier
        from telegram_notify import TelegramNotifier
        
        # Tạo notifier tạm thời cho test
        test_notifier = TelegramNotifier(token=bot_token, chat_id=chat_id)
        
        # Gửi tin nhắn test
        success = test_notifier.send_message("<b>🧪 TIN NHẮN KIỂM TRA</b>\n\nKết nối Telegram thành công!\nBot Trading đã kết nối thành công với Telegram.")
        
        if success:
            # Cập nhật biến môi trường
            env_vars = {
                "TELEGRAM_BOT_TOKEN": bot_token,
                "TELEGRAM_CHAT_ID": chat_id
            }
            update_env_variables(env_vars)
            
            return jsonify({"success": True, "message": "Kết nối Telegram thành công!"})
        else:
            return jsonify({"success": False, "message": "Không thể gửi tin nhắn đến Telegram. Kiểm tra lại Bot Token và Chat ID."})
    
    except ImportError:
        return jsonify({"success": False, "message": "Không thể import module TelegramNotifier"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi khi kiểm tra kết nối Telegram: {str(e)}"})

@config_bp.route('/api/test/email', methods=['POST'])
def test_email():
    """API kiểm tra kết nối Email"""
    data = request.json
    smtp_server = data.get("smtpServer")
    smtp_port = data.get("smtpPort")
    email_user = data.get("emailUser")
    email_password = data.get("emailPassword")
    recipients = data.get("recipients", [])
    
    if not smtp_server or not smtp_port or not email_user or not email_password or not recipients:
        return jsonify({"success": False, "message": "Thiếu thông tin kết nối email"})
    
    try:
        # Import email_report
        from email_report import EmailReporter
        
        # Tạo reporter tạm thời cho test
        test_reporter = EmailReporter(
            smtp_server=smtp_server,
            smtp_port=int(smtp_port),
            email_user=email_user,
            email_password=email_password
        )
        
        # Gửi email test
        recipient = recipients[0] if isinstance(recipients, list) else recipients.split(',')[0].strip()
        success = test_reporter.send_email(
            subject="Kiểm tra kết nối Email - Crypto Trading Bot",
            to_email=recipient,
            text_content="Đây là email kiểm tra từ Crypto Trading Bot. Kết nối email thành công!",
            html_content="<h1>Kết nối Email thành công!</h1><p>Đây là email kiểm tra từ Crypto Trading Bot.</p>"
        )
        
        if success:
            # Cập nhật biến môi trường
            env_vars = {
                "EMAIL_SMTP_SERVER": smtp_server,
                "EMAIL_SMTP_PORT": str(smtp_port),
                "EMAIL_USER": email_user,
                "EMAIL_PASSWORD": email_password,
                "REPORT_EMAIL": recipient
            }
            update_env_variables(env_vars)
            
            return jsonify({"success": True, "message": f"Kết nối email thành công! Đã gửi email kiểm tra đến {recipient}"})
        else:
            return jsonify({"success": False, "message": "Không thể gửi email kiểm tra. Kiểm tra lại thông tin kết nối."})
    
    except ImportError:
        return jsonify({"success": False, "message": "Không thể import module EmailReporter"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi khi kiểm tra kết nối email: {str(e)}"})

@config_bp.route('/api/send-report', methods=['POST'])
def send_report_now():
    """API gửi báo cáo ngay lập tức"""
    data = request.json
    report_type = data.get("reportType")
    send_to_telegram = data.get("sendToTelegram", False)
    send_to_email = data.get("sendToEmail", False)
    
    if not report_type or (not send_to_telegram and not send_to_email):
        return jsonify({"success": False, "message": "Thiếu thông tin gửi báo cáo"})
    
    try:
        # Import run_reports
        import importlib.util
        spec = importlib.util.spec_from_file_location("run_reports", "run_reports.py")
        run_reports = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_reports)
        
        # Tạo danh sách các loại báo cáo
        report_types = [report_type]
        
        # Chạy chức năng tạo báo cáo tương ứng
        if report_type == "daily":
            success = run_reports.run_daily_report()
        elif report_type == "signal":
            success = run_reports.run_signal_report()
        elif report_type == "market":
            symbols = ["BTCUSDT", "ETHUSDT"]
            success = run_reports.run_market_report(symbols)
        elif report_type == "training":
            success = run_reports.run_training_report()
        else:
            return jsonify({"success": False, "message": f"Loại báo cáo không hợp lệ: {report_type}"})
        
        if not success:
            return jsonify({"success": False, "message": f"Lỗi khi tạo báo cáo {report_type}"})
        
        # Gửi báo cáo qua Telegram
        if send_to_telegram:
            telegram_success = run_reports.send_telegram_reports(report_types)
            if not telegram_success:
                return jsonify({"success": False, "message": f"Lỗi khi gửi báo cáo {report_type} qua Telegram"})
        
        # Gửi báo cáo qua Email
        if send_to_email:
            # Lấy email người nhận từ cấu hình
            config = load_config()
            recipients = config.get("email", {}).get("recipients", [])
            
            if not recipients:
                return jsonify({"success": False, "message": "Không có địa chỉ email người nhận"})
            
            for recipient in recipients:
                email_success = run_reports.send_email_reports(recipient, report_types)
                if not email_success:
                    return jsonify({"success": False, "message": f"Lỗi khi gửi báo cáo {report_type} qua Email"})
        
        return jsonify({"success": True, "message": f"Báo cáo {report_type} đã được gửi thành công"})
    
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi khi gửi báo cáo: {str(e)}"})