#!/usr/bin/env python3
"""
API Routes for Bot Management

Module này cung cấp các endpoint API để quản lý và điều khiển các bot giao dịch
"""

import os
import json
import logging
import time
from datetime import datetime
from flask import Blueprint, request, jsonify

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot_api")

# Tạo Blueprint
bot_api = Blueprint('bot_api', __name__)

# File chứa dữ liệu cấu hình
ACCOUNT_CONFIG_FILE = 'account_config.json'
BOT_CONFIG_FILE = 'bots_config.json'

# Cấu hình mặc định
DEFAULT_ACCOUNT_CONFIG = {
    "api_mode": "testnet",  # 'demo', 'testnet', 'live'
    "account_type": "futures",  # 'spot', 'futures'
}

# Danh sách các bot mẫu
SAMPLE_BOTS = [
    {
        "id": "bot-001",
        "name": "BTC Trend Follower",
        "strategy": "trend_following",
        "strategy_params": {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "ma_short": 20,
            "ma_long": 50
        },
        "pairs": ["BTCUSDT"],
        "timeframe": "1h",
        "status": "running",
        "created_at": "2025-02-28T12:00:00Z",
        "last_updated": "2025-03-02T08:15:30Z",
        "risk_level": "low",
        "leverage": 2,
        "position_size_pct": 1.0,
        "stats": {
            "profit_pct": 2.8,
            "positions_count": 1,
            "win_count": 8,
            "loss_count": 5,
            "last_trade_time": "18:30:25"
        }
    },
    {
        "id": "bot-002",
        "name": "ETH Oscillator",
        "strategy": "mean_reversion",
        "strategy_params": {
            "bb_period": 20,
            "bb_std": 2.0,
            "rsi_period": 14
        },
        "pairs": ["ETHUSDT"],
        "timeframe": "4h",
        "status": "running",
        "created_at": "2025-03-01T09:20:00Z",
        "last_updated": "2025-03-02T08:15:30Z",
        "risk_level": "medium",
        "leverage": 3,
        "position_size_pct": 1.5,
        "stats": {
            "profit_pct": 4.1,
            "positions_count": 2,
            "win_count": 6,
            "loss_count": 2,
            "last_trade_time": "14:15:40"
        }
    },
    {
        "id": "bot-003",
        "name": "BNB Multi-Strategy",
        "strategy": "composite",
        "strategy_params": {
            "strategies": ["trend_following", "mean_reversion"],
            "weights": [0.6, 0.4]
        },
        "pairs": ["BNBUSDT"],
        "timeframe": "1d",
        "status": "stopped",
        "created_at": "2025-02-25T14:10:00Z",
        "last_updated": "2025-03-02T06:30:10Z",
        "risk_level": "high",
        "leverage": 5,
        "position_size_pct": 2.0,
        "stats": {
            "profit_pct": -0.8,
            "positions_count": 0,
            "win_count": 3,
            "loss_count": 4,
            "last_trade_time": "09:45:12"
        }
    }
]

def load_account_config():
    """
    Tải cấu hình tài khoản từ file

    Returns:
        dict: Cấu hình tài khoản
    """
    try:
        if os.path.exists(ACCOUNT_CONFIG_FILE):
            with open(ACCOUNT_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_ACCOUNT_CONFIG
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình tài khoản: {e}")
        return DEFAULT_ACCOUNT_CONFIG

def save_account_config(config):
    """
    Lưu cấu hình tài khoản vào file

    Args:
        config (dict): Cấu hình tài khoản

    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    try:
        with open(ACCOUNT_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình tài khoản: {e}")
        return False

def load_bots_config():
    """
    Tải cấu hình các bot từ file

    Returns:
        list: Danh sách các bot
    """
    try:
        if os.path.exists(BOT_CONFIG_FILE):
            with open(BOT_CONFIG_FILE, 'r') as f:
                return json.load(f)
        return SAMPLE_BOTS
    except Exception as e:
        logger.error(f"Lỗi khi tải cấu hình bot: {e}")
        return SAMPLE_BOTS

def save_bots_config(bots):
    """
    Lưu cấu hình các bot vào file

    Args:
        bots (list): Danh sách các bot

    Returns:
        bool: True nếu lưu thành công, False nếu không
    """
    try:
        with open(BOT_CONFIG_FILE, 'w') as f:
            json.dump(bots, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Lỗi khi lưu cấu hình bot: {e}")
        return False

def find_bot_by_id(bot_id):
    """
    Tìm bot theo ID

    Args:
        bot_id (str): ID của bot

    Returns:
        tuple: (bot_obj, index) nếu tìm thấy, (None, -1) nếu không
    """
    bots = load_bots_config()
    for i, bot in enumerate(bots):
        if bot["id"] == bot_id:
            return bot, i
    return None, -1

def generate_bot_id():
    """
    Tạo ID mới cho bot

    Returns:
        str: ID mới
    """
    bots = load_bots_config()
    max_id = 0
    for bot in bots:
        if bot["id"].startswith("bot-"):
            try:
                id_num = int(bot["id"].split("-")[1])
                max_id = max(max_id, id_num)
            except:
                pass
    return f"bot-{max_id + 1:03d}"

@bot_api.route('/api/bot/<bot_id>/status', methods=['GET'])
def get_bot_status(bot_id):
    """API endpoint để lấy trạng thái của bot"""
    bot, _ = find_bot_by_id(bot_id)
    
    if not bot:
        return jsonify({"success": False, "message": "Bot không tồn tại"})
    
    return jsonify({
        "success": True,
        "status": bot["status"],
        "info": {
            "positions_count": bot["stats"].get("positions_count", 0),
            "profit": bot["stats"].get("profit_pct", 0),
            "last_trade_time": bot["stats"].get("last_trade_time", "N/A")
        }
    })

@bot_api.route('/api/bot/<bot_id>/control', methods=['POST'])
def control_bot(bot_id):
    """API endpoint để điều khiển bot (start/stop/restart/delete)"""
    data = request.json
    action = data.get("action")
    
    if not action:
        return jsonify({"success": False, "message": "Thiếu thông tin action"})
    
    bot, index = find_bot_by_id(bot_id)
    
    if not bot:
        return jsonify({"success": False, "message": "Bot không tồn tại"})
    
    bots = load_bots_config()
    
    if action == "start":
        bot["status"] = "running"
        bot["last_updated"] = datetime.now().isoformat()
        bots[index] = bot
        success = save_bots_config(bots)
        return jsonify({"success": success, "message": "Bot đã được khởi động"})
    
    elif action == "stop":
        bot["status"] = "stopped"
        bot["last_updated"] = datetime.now().isoformat()
        bots[index] = bot
        success = save_bots_config(bots)
        return jsonify({"success": success, "message": "Bot đã được dừng"})
    
    elif action == "restart":
        # Mô phỏng việc khởi động lại bot
        bot["status"] = "restarting"
        bot["last_updated"] = datetime.now().isoformat()
        bots[index] = bot
        save_bots_config(bots)
        
        # Sau 2 giây, cập nhật trạng thái thành "running"
        time.sleep(2)
        bot["status"] = "running"
        bot["last_updated"] = datetime.now().isoformat()
        bots[index] = bot
        success = save_bots_config(bots)
        
        return jsonify({"success": success, "message": "Bot đã được khởi động lại"})
    
    elif action == "delete":
        bots.pop(index)
        success = save_bots_config(bots)
        return jsonify({"success": success, "message": "Bot đã được xóa"})
    
    elif action == "edit" or action == "view":
        # Chỉ trả về dữ liệu bot, không thay đổi trạng thái
        return jsonify({"success": True, "bot": bot})
    
    else:
        return jsonify({"success": False, "message": f"Action không hợp lệ: {action}"})

@bot_api.route('/api/bot/create', methods=['POST'])
def create_bot():
    """API endpoint để tạo bot mới"""
    data = request.json
    
    # Kiểm tra dữ liệu
    required_fields = ["name", "strategy", "pairs", "timeframe", "risk_level"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"Thiếu thông tin: {field}"})
    
    # Tạo bot mới
    new_bot = {
        "id": generate_bot_id(),
        "name": data["name"],
        "strategy": data["strategy"],
        "pairs": data["pairs"],
        "timeframe": data["timeframe"],
        "status": "stopped",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "risk_level": data["risk_level"],
        "strategy_params": get_default_strategy_params(data["strategy"]),
        "leverage": get_default_leverage(data["risk_level"]),
        "position_size_pct": get_default_position_size(data["risk_level"]),
        "stats": {
            "profit_pct": 0,
            "positions_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "last_trade_time": "N/A"
        }
    }
    
    # Lưu bot mới
    bots = load_bots_config()
    bots.append(new_bot)
    success = save_bots_config(bots)
    
    if success:
        return jsonify({"success": True, "message": "Bot đã được tạo thành công", "bot": new_bot})
    else:
        return jsonify({"success": False, "message": "Lỗi khi tạo bot mới"})

@bot_api.route('/api/bots', methods=['GET'])
def get_all_bots():
    """API endpoint để lấy danh sách tất cả các bot"""
    bots = load_bots_config()
    return jsonify({"success": True, "bots": bots})

@bot_api.route('/api/bot/<bot_id>/update', methods=['POST'])
def update_bot(bot_id):
    """API endpoint để cập nhật thông tin bot"""
    data = request.json
    bot, index = find_bot_by_id(bot_id)
    
    if not bot:
        return jsonify({"success": False, "message": "Bot không tồn tại"})
    
    # Cập nhật thông tin bot
    fields_to_update = [
        "name", "strategy", "pairs", "timeframe", "status", 
        "risk_level", "leverage", "position_size_pct", "strategy_params"
    ]
    
    for field in fields_to_update:
        if field in data:
            bot[field] = data[field]
    
    bot["last_updated"] = datetime.now().isoformat()
    
    # Lưu thay đổi
    bots = load_bots_config()
    bots[index] = bot
    success = save_bots_config(bots)
    
    if success:
        return jsonify({"success": True, "message": "Bot đã được cập nhật", "bot": bot})
    else:
        return jsonify({"success": False, "message": "Lỗi khi cập nhật bot"})

@bot_api.route('/api/account/settings', methods=['GET'])
def get_account_settings():
    """API endpoint để lấy cài đặt tài khoản"""
    config = load_account_config()
    return jsonify(config)

@bot_api.route('/api/account/settings', methods=['POST'])
def update_account_settings():
    """API endpoint để cập nhật cài đặt tài khoản"""
    data = request.json
    config = load_account_config()
    
    # Cập nhật chế độ API
    if "api_mode" in data:
        config["api_mode"] = data["api_mode"]
    
    # Cập nhật loại tài khoản
    if "account_type" in data:
        config["account_type"] = data["account_type"]
    
    # Lưu cấu hình
    success = save_account_config(config)
    
    return jsonify({"status": "success" if success else "error", "message": "Cài đặt đã được cập nhật" if success else "Lỗi khi cập nhật cài đặt"})

@bot_api.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """API endpoint để lấy thống kê cho dashboard"""
    bots = load_bots_config()
    
    total_bots = len(bots)
    running_bots = sum(1 for bot in bots if bot["status"] == "running")
    stopped_bots = total_bots - running_bots
    
    # Tính tổng lợi nhuận
    total_profit = sum(bot["stats"].get("profit_pct", 0) for bot in bots)
    
    # Số lượng vị thế hiện tại
    total_positions = sum(bot["stats"].get("positions_count", 0) for bot in bots if bot["status"] == "running")
    
    # Thống kê thắng/thua
    total_wins = sum(bot["stats"].get("win_count", 0) for bot in bots)
    total_losses = sum(bot["stats"].get("loss_count", 0) for bot in bots)
    win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
    
    return jsonify({
        "success": True,
        "stats": {
            "total_bots": total_bots,
            "running_bots": running_bots,
            "stopped_bots": stopped_bots,
            "total_profit": total_profit,
            "total_positions": total_positions,
            "win_rate": win_rate
        }
    })

def get_default_strategy_params(strategy):
    """
    Lấy tham số mặc định cho chiến lược

    Args:
        strategy (str): Tên chiến lược

    Returns:
        dict: Tham số mặc định
    """
    if strategy == "trend_following":
        return {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "ma_short": 20,
            "ma_long": 50
        }
    elif strategy == "mean_reversion":
        return {
            "bb_period": 20,
            "bb_std": 2.0,
            "rsi_period": 14
        }
    elif strategy == "breakout":
        return {
            "atr_period": 14,
            "atr_multiplier": 2.0,
            "lookback_period": 20
        }
    elif strategy == "composite":
        return {
            "strategies": ["trend_following", "mean_reversion"],
            "weights": [0.6, 0.4]
        }
    elif strategy == "ml_adaptive":
        return {
            "lookback_window": 50,
            "prediction_horizon": 5,
            "retrain_interval": 100
        }
    else:
        return {}

def get_default_leverage(risk_level):
    """
    Lấy đòn bẩy mặc định dựa trên cấp độ rủi ro

    Args:
        risk_level (str): Cấp độ rủi ro

    Returns:
        int: Đòn bẩy mặc định
    """
    if risk_level == "low":
        return 2
    elif risk_level == "medium":
        return 5
    elif risk_level == "high":
        return 10
    else:
        return 1

def get_default_position_size(risk_level):
    """
    Lấy kích thước vị thế mặc định dựa trên cấp độ rủi ro

    Args:
        risk_level (str): Cấp độ rủi ro

    Returns:
        float: Kích thước vị thế mặc định (%)
    """
    if risk_level == "low":
        return 1.0
    elif risk_level == "medium":
        return 2.0
    elif risk_level == "high":
        return 5.0
    else:
        return 0.5