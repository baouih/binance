import os
import logging
import json
import datetime
import re
import threading
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import binance_api
from account_type_selector import AccountTypeSelector

# Jinja2 custom filter
from datetime import datetime as dt

# Đường dẫn file cấu hình tài khoản
ACCOUNT_CONFIG_PATH = 'account_config.json'

# Cấu hình logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Khởi tạo Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_secret_key")

# Jinja2 custom filter cho datetime
@app.template_filter('datetime')
def format_datetime(value):
    """Jinja2 filter để định dạng timestamp thành datetime"""
    if isinstance(value, (int, float)):
        return dt.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    return value

# Jinja2 custom filter để tăng phiên bản
@app.template_filter('increment_version')
def increment_version(version):
    """Jinja2 filter để tự động tăng phiên bản"""
    if not version:
        return "1.0.1"
    version_parts = version.split(".")
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    return ".".join(version_parts)

# Hàm để lấy trạng thái bot từ cấu hình tài khoản
def get_bot_status_from_config():
    """Đọc trạng thái bot từ cấu hình tài khoản"""
    # Đọc trạng thái bot từ file hoặc process
    bot_running = False
    try:
        # Kiểm tra xem bot có đang chạy không (kiểm tra PID hoặc trạng thái khác)
        # File này được cập nhật bởi bot khi khởi động/dừng
        if os.path.exists('bot_status.json'):
            with open('bot_status.json', 'r') as f:
                saved_status = json.load(f)
                bot_running = saved_status.get('running', False)
                logger.debug(f"Đọc trạng thái bot từ file: running={bot_running}")
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {str(e)}")
    
    # Trả về full status
    status = {
        'running': bot_running,
        'mode': 'testnet',  # Mặc định
        'version': '1.0.0'  # Mặc định
    }
    
    # Lấy phiên bản từ update_config.json
    if os.path.exists('update_config.json'):
        try:
            with open('update_config.json', 'r') as f:
                update_config = json.load(f)
                status['version'] = update_config.get('version', '1.0.0')
                logger.debug(f"Đọc phiên bản từ update_config.json: {status['version']}")
        except Exception as e:
            logger.error(f"Lỗi khi đọc update_config.json: {str(e)}")
    
    # Nếu có file status, lấy thêm thông tin
    if os.path.exists('bot_status.json'):
        try:
            with open('bot_status.json', 'r') as f:
                saved_status = json.load(f)
                status.update(saved_status)
        except Exception as e:
            logger.error(f"Lỗi khi đọc bot_status.json: {str(e)}")
            
    # Tính uptime nếu bot đang chạy
    uptime = '0d 0h 0m'
    if bot_running and os.path.exists('bot_start_time.txt'):
        try:
            with open('bot_start_time.txt', 'r') as f:
                start_time_str = f.read().strip()
                start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                now = datetime.datetime.now()
                delta = now - start_time
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                uptime = f"{days}d {hours}h {minutes}m"
        except Exception as e:
            logger.error(f"Lỗi khi tính uptime: {str(e)}")
    
    # Thêm thông tin uptime và chi tiết bổ sung
    status.update({
        'uptime': uptime,
        'last_update': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': status.get('version', '1.0.0'),
        'last_action': 'Bot đang chạy' if bot_running else 'Bot đang dừng'
    })
    
    # Kiểm tra xem đã có thông tin cấu hình tài khoản từ file chưa
    try:
        if os.path.exists('account_config.json'):
            with open('account_config.json', 'r') as f:
                config = json.load(f)
                
                # Cập nhật mode từ cấu hình
                if 'api_mode' in config:
                    status['mode'] = config['api_mode']
    except Exception as e:
        logger.error(f"Lỗi khi đọc cấu hình bot: {str(e)}")
    
    logger.debug(f"Trạng thái bot đầy đủ: {status}")
    return status

# Khởi tạo trạng thái bot
BOT_STATUS = get_bot_status_from_config()

# Giả lập dữ liệu tài khoản (sau này lấy từ API Binance)
ACCOUNT_DATA = {
    'balance': 1000.00,
    'equity': 1000.00,
    'margin_used': 0.0,
    'margin_available': 1000.00,
    'free_balance': 1000.00,
    'positions': [],
    'leverage': 5
}

# Giả lập dữ liệu thị trường (sau này lấy từ API Binance thực)
MARKET_DATA = {
    'btc_price': 85000.00,   # Giá BTC hiện tại sẽ được cập nhật từ API Binance
    'eth_price': 2200.00,    # Giá ETH hiện tại sẽ được cập nhật từ API Binance
    'bnb_price': 410.00,     # Giá BNB hiện tại sẽ được cập nhật từ API Binance
    'sol_price': 137.50,     # Giá SOL hiện tại sẽ được cập nhật từ API Binance
    'btc_change_24h': 2.35,
    'eth_change_24h': 3.1,
    'bnb_change_24h': -1.5,
    'sol_change_24h': 5.2,
    'sentiment': {
        'value': 65,
        'state': 'warning',
        'description': 'Tham lam nhẹ'
    },
    'market_regime': {
        'BTCUSDT': 'Trending',
        'ETHUSDT': 'Ranging',
        'BNBUSDT': 'Volatile',
        'SOLUSDT': 'Trending'
    }
}

# Khởi tạo account selector
account_selector = AccountTypeSelector()


@app.route('/')
def index():
    """Trang chủ Dashboard"""
    try:
        # Thêm timestamp vào dữ liệu để tránh cache
        now = datetime.datetime.now()
        version = f"v{now.hour}{now.minute}{now.second}"
        
        # Log chi tiết để debug
        logger.info(f"====== START INDEX RENDERING at {now} =======")
        
        # Cập nhật BOT_STATUS từ cấu hình tài khoản mới nhất
        BOT_STATUS.update(get_bot_status_from_config())
        logger.info(f"Trang chủ - Chế độ API hiện tại: {BOT_STATUS.get('mode', 'testnet')}")
        
        # Đảm bảo thông tin trạng thái bot có đầy đủ thông tin chế độ
        current_bot_status = BOT_STATUS.copy()
        if 'mode' not in current_bot_status:
            current_bot_status['mode'] = 'testnet'  # 'demo', 'testnet', 'live'
        if 'account_type' not in current_bot_status:
            current_bot_status['account_type'] = 'futures'  # 'spot', 'futures'
        if 'strategy_mode' not in current_bot_status:
            current_bot_status['strategy_mode'] = 'auto'  # 'auto', 'manual'
        
        # Đảm bảo dữ liệu tài khoản có đầy đủ thông tin vị thế
        current_account_data = ACCOUNT_DATA.copy()
        
        # Đọc dữ liệu vị thế từ active_positions.json
        active_positions = {}
        try:
            with open('active_positions.json', 'r', encoding='utf-8') as f:
                active_positions = json.load(f)
            logger.info(f"Đã đọc active_positions.json, có {len(active_positions)} vị thế")
        except Exception as e:
            logger.error(f"Không thể đọc active_positions.json: {e}")
            
        # Chuyển đổi dữ liệu từ active_positions.json sang định dạng positions
        positions_list = []
        for symbol, position in active_positions.items():
            # Debug thông tin vị thế
            logger.info(f"Đang xử lý vị thế {symbol}: {position}")
            
            # Tính P/L
            entry_price = float(position.get('entry_price', 0))
            current_price = float(position.get('current_price', 0))
            side = position.get('side', 'LONG')
            leverage = int(position.get('leverage', 1))
            quantity = float(position.get('quantity', 0))
            
            # Tính P/L và P/L %
            if side == 'LONG':
                pnl = (current_price - entry_price) * quantity
                pnl_percent = (current_price - entry_price) / entry_price * 100 * leverage
            else:  # SHORT
                pnl = (entry_price - current_price) * quantity
                pnl_percent = (entry_price - current_price) / entry_price * 100 * leverage
            
            # Log kết quả tính toán
            logger.info(f"Vị thế {symbol} {side}: Entry {entry_price}, Current {current_price}, P/L {pnl:.2f} ({pnl_percent:.2f}%)")
                
            positions_list.append({
                'id': f"pos_{symbol}",
                'symbol': symbol,
                'type': side,  # Lưu ý: template sử dụng 'type' nhưng dữ liệu gốc là 'side'
                'entry_price': entry_price,
                'current_price': current_price,
                'quantity': quantity,
                'leverage': leverage,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'entry_time': position.get('entry_time', ''),
                'stop_loss': position.get('stop_loss', 0),
                'take_profit': position.get('take_profit', 0)
            })
            
        if not positions_list:
            # Thêm dữ liệu vị thế giả lập nếu không có
            positions_list = [
                {
                    'id': 'pos1',
                    'symbol': 'BTCUSDT',
                    'type': 'LONG',
                    'entry_price': 72000,
                    'current_price': 75000,
                    'quantity': 0.1,
                    'leverage': 1,
                    'pnl': 300,
                    'pnl_percent': 4.17,
                    'entry_time': '2025-02-28 18:30:00',
                    'stop_loss': 68000,
                    'take_profit': 80000
                }
            ]
            
        current_account_data['positions'] = positions_list
        
        # Debug: In ra danh sách vị thế
        logger.info(f"Số lượng vị thế: {len(positions_list)}")
        for pos in positions_list:
            logger.info(f"Debug Vị thế: {pos['symbol']} {pos['type']} at {pos['entry_price']}")
            
        # Tạo danh sách hoạt động gần đây từ vị thế hiện tại
        recent_activities = []
        for position in positions_list:
            activity_type = "Mở vị thế mới"
            icon_class = "text-success" if position['type'] == 'LONG' else "text-danger"
            icon = "bi-arrow-up-circle-fill" if position['type'] == 'LONG' else "bi-arrow-down-circle-fill"
            description = f"Mở vị thế {position['type']} {position['symbol']} tại ${position['entry_price']:.2f}"
            
            # Lấy thời gian từ entry_time hoặc mặc định là hiện tại
            time_str = position.get('entry_time', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            try:
                if isinstance(time_str, str):
                    time_obj = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    time_display = time_obj.strftime('%H:%M')
                else:
                    time_display = "12:00"
            except Exception as e:
                logger.error(f"Lỗi xử lý thời gian: {str(e)}")
                time_display = "12:00"
                
            recent_activities.append({
                'type': activity_type,
                'class': icon_class,
                'icon': icon,
                'description': description,
                'time': time_display,
                'position_id': position.get('id')
            })
            
            # Log thông tin hoạt động
            logger.info(f"Đã thêm hoạt động: {description} lúc {time_display}")
        
        # Thêm hoạt động bot khởi động nếu không có vị thế
        if not positions_list:
            recent_activities.append({
                'type': 'Bot startup',
                'class': 'text-info',
                'icon': 'bi-play-circle',
                'description': 'Bot đã bắt đầu hoạt động',
                'time': datetime.datetime.now().strftime('%H:%M'),
                'position_id': None
            })
        
        # Đảm bảo activities được sắp xếp theo thời gian mới nhất (giả sử entry_time mới nhất ở đầu)
        current_account_data['activities'] = recent_activities
        
        # Debug activities
        logger.info(f"Danh sách activities: {len(current_account_data['activities'])}")
        for act in current_account_data['activities']:
            logger.info(f"Activity: {act['description']} at {act['time']}")
        
        return render_template('index.html', 
                            bot_status=current_bot_status,
                            account_data=current_account_data,
                            market_data=MARKET_DATA,
                            version=version)
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang chủ: {str(e)}")
        return render_template('error.html', 
                            error_message="Không thể tải trang chủ. Vui lòng thử lại sau.")


@app.route('/strategies')
def strategies():
    """Trang quản lý chiến lược"""
    return render_template('strategies.html', 
                          bot_status=BOT_STATUS)


@app.route('/backtest')
def backtest():
    """Trang backtest"""
    return render_template('backtest.html', 
                          bot_status=BOT_STATUS)


@app.route('/trades')
def trades():
    """Trang lịch sử giao dịch"""
    return render_template('trades.html', 
                          bot_status=BOT_STATUS)


@app.route('/market')
def market():
    """Trang phân tích thị trường"""
    try:
        # Tạo dữ liệu giả lập cập nhật
        current_market_data = MARKET_DATA.copy()
        
        # Cập nhật giá hiện tại cho phiên làm việc hiện tại
        current_market_data['btc_price'] = 71250.45
        current_market_data['btc_change_24h'] = 3.15
        
        # Thêm dữ liệu chi tiết cho biểu đồ
        current_market_data['chart_data'] = {
            'labels': ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'],
            'prices': [69842, 70123, 71505, 71250, 70980, 71100, 71250],
            'volumes': [125.5, 142.3, 189.7, 165.2, 138.6, 142.1, 159.8]
        }
        
        # Thêm dữ liệu top gainers và losers
        current_market_data['top_gainers'] = [
            {'symbol': 'SOL', 'name': 'Solana', 'price': 137.50, 'change': 5.2, 'volume': 280},
            {'symbol': 'AVAX', 'name': 'Avalanche', 'price': 35.20, 'change': 4.8, 'volume': 120},
            {'symbol': 'DOT', 'name': 'Polkadot', 'price': 7.85, 'change': 4.2, 'volume': 95},
            {'symbol': 'LINK', 'name': 'Chainlink', 'price': 18.45, 'change': 3.9, 'volume': 78},
            {'symbol': 'ETH', 'name': 'Ethereum', 'price': 3150.00, 'change': 3.1, 'volume': 450}
        ]
        
        current_market_data['top_losers'] = [
            {'symbol': 'DOGE', 'name': 'Dogecoin', 'price': 0.12, 'change': -2.8, 'volume': 110},
            {'symbol': 'BNB', 'name': 'Binance Coin', 'price': 410.00, 'change': -1.5, 'volume': 150},
            {'symbol': 'XRP', 'name': 'Ripple', 'price': 0.48, 'change': -1.2, 'volume': 95},
            {'symbol': 'ADA', 'name': 'Cardano', 'price': 0.42, 'change': -0.9, 'volume': 85},
            {'symbol': 'MATIC', 'name': 'Polygon', 'price': 0.68, 'change': -0.7, 'volume': 65}
        ]
        
        # Thêm dữ liệu phân tích chuyên sâu
        current_market_data['market_analysis'] = {
            'btc_volatility': 2.3,  # Biến động (%)
            'market_sentiment': 65,  # Thang điểm 0-100
            'liquidity_index': 78,   # Thang điểm 0-100
            'market_cycle': 'Uptrend', # Chu kỳ thị trường hiện tại
            'fear_greed_index': 65, # Chỉ số sợ hãi/tham lam
            'major_supports': [68500, 67000, 65200], # Các vùng hỗ trợ chính
            'major_resistances': [72500, 74000, 76000], # Các vùng kháng cự chính
            'analysis_summary': 'Thị trường đang trong xu hướng tăng với khối lượng ổn định. Các chỉ báo kỹ thuật cho thấy khả năng tiếp tục đà tăng nhưng có thể có điều chỉnh ngắn hạn tại các vùng kháng cự.'
        }
        
        # Thêm dữ liệu tin tức thị trường
        current_market_data['market_news'] = [
            {
                'title': 'Bitcoin vượt ngưỡng 70.000 USD lần đầu tiên kể từ tháng 3',
                'source': 'CoinDesk',
                'time': '2h trước',
                'impact': 'positive',
                'url': '#'
            },
            {
                'title': 'Ethereum chuẩn bị cập nhật mạng lưới mới vào tháng 4',
                'source': 'CryptoNews',
                'time': '5h trước',
                'impact': 'positive',
                'url': '#'
            },
            {
                'title': 'Binance giới thiệu các công cụ giao dịch mới dành cho nhà đầu tư',
                'source': 'Binance Blog',
                'time': '1 ngày trước',
                'impact': 'neutral',
                'url': '#'
            }
        ]
        
        # Thêm dữ liệu chỉ báo kỹ thuật
        current_market_data['technical_indicators'] = {
            'ma_signals': {
                'ma_20': 'bullish',
                'ma_50': 'bullish',
                'ma_100': 'bullish',
                'ma_200': 'bullish'
            },
            'oscillators': {
                'rsi': {
                    'value': 62,
                    'signal': 'neutral'
                },
                'macd': {
                    'value': 125,
                    'signal': 'bullish'
                },
                'stoch': {
                    'value': 75,
                    'signal': 'neutral'
                }
            },
            'overall_signal': 'bullish'
        }
        
        # Tạo template nếu chưa tồn tại
        import os
        template_path = 'templates/market.html'
        if not os.path.exists(template_path):
            with open(template_path, 'w') as f:
                f.write("""<!DOCTYPE html>
<html lang="vi" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phân tích thị trường - Bot Giao Dịch Crypto</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <link rel="icon" href="/static/img/favicon.ico" type="image/x-icon">
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        .market-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin-bottom: 16px;
        }
        .status-badge {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .status-running {
            background-color: #3fb950;
        }
        .status-stopped {
            background-color: #f85149;
        }
        .mode-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 0.8rem;
            margin-right: 10px;
            color: white;
        }
        .mode-demo {
            background-color: #6c757d;
        }
        .mode-testnet {
            background-color: #fd7e14;
        }
        .mode-live {
            background-color: #dc3545;
        }
        .market-table th, .market-table td {
            padding: 0.5rem;
        }
        .positive-change {
            color: #3fb950;
        }
        .negative-change {
            color: #f85149;
        }
        .news-item {
            border-left: 3px solid;
            padding-left: 15px;
            margin-bottom: 15px;
        }
        .news-positive {
            border-color: #3fb950;
        }
        .news-negative {
            border-color: #f85149;
        }
        .news-neutral {
            border-color: #58a6ff;
        }
        .indicator-bullish {
            color: #3fb950;
        }
        .indicator-bearish {
            color: #f85149;
        }
        .indicator-neutral {
            color: #8b949e;
        }
    </style>
</head>
<body>
    <div class="container py-4">
        <header class="d-flex flex-wrap justify-content-between py-3 mb-4 border-bottom">
            <div class="d-flex align-items-center mb-3 mb-md-0 me-md-auto">
                <a href="/" class="d-flex align-items-center text-decoration-none">
                    <i class="bi bi-currency-bitcoin fs-3 me-2"></i>
                    <span class="fs-4">Bot Giao Dịch Crypto</span>
                </a>
                <div class="ms-3">
                    <span class="mode-badge mode-demo">Chế độ Demo</span>
                </div>
            </div>
            
            <div class="d-flex align-items-center">
                <!-- Language selector -->
                <div class="dropdown me-3">
                    <button class="btn btn-sm btn-outline-primary dropdown-toggle" type="button" id="languageDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-translate"></i> Ngôn ngữ
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="languageDropdown">
                        <li><a class="dropdown-item" href="#" data-language="vi"><span class="me-2">🇻🇳</span>Tiếng Việt</a></li>
                        <li><a class="dropdown-item" href="#" data-language="en"><span class="me-2">🇺🇸</span>English</a></li>
                    </ul>
                </div>
                
                <!-- Bot status -->
                <div class="me-3">
                    <span class="status-badge {{ 'status-running' if bot_status.running else 'status-stopped' }}"></span>
                    <span>{{ 'Đang chạy' if bot_status.running else 'Đang dừng' }}</span>
                </div>
                
                <!-- Bot controls -->
                <div class="btn-group">
                    <a href="/" class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-house"></i> Trang chủ
                    </a>
                </div>
            </div>
        </header>

        <div class="row mb-4">
            <div class="col">
                <h2><i class="bi bi-bar-chart-line"></i> Phân tích thị trường</h2>
                <p class="text-muted">Dữ liệu thị trường thời gian thực và phân tích chuyên sâu</p>
            </div>
        </div>

        <div class="row mb-4">
            <!-- BTC Price Card -->
            <div class="col-md-4">
                <div class="market-card p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5>BTC/USDT</h5>
                        <span class="badge bg-info">Trending</span>
                    </div>
                    <h2>${{ '{:,.2f}'.format(market_data.btc_price) }}</h2>
                    <p class="{{ 'positive-change' if market_data.btc_change_24h > 0 else 'negative-change' }}">
                        <i class="bi {{ 'bi-arrow-up-right' if market_data.btc_change_24h > 0 else 'bi-arrow-down-right' }}"></i>
                        {{ '{:.2f}'.format(market_data.btc_change_24h) }}% (24h)
                    </p>
                </div>
            </div>
            <!-- Fear & Greed Index -->
            <div class="col-md-4">
                <div class="market-card p-3">
                    <h5>Chỉ số Sợ hãi & Tham lam</h5>
                    <div class="d-flex justify-content-center align-items-center my-2">
                        <div class="position-relative" style="width: 100px; height: 100px;">
                            <div class="position-absolute top-50 start-50 translate-middle text-center">
                                <h3>{{ market_data.market_analysis.fear_greed_index }}</h3>
                                <small>{{ 'Tham lam' if market_data.market_analysis.fear_greed_index > 50 else 'Sợ hãi' }}</small>
                            </div>
                            <!-- Circular progress gauge would go here -->
                            <svg viewBox="0 0 36 36" class="position-absolute top-0 start-0" style="width: 100%; height: 100%;">
                                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#30363d" stroke-width="2" />
                                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="{{ '#3fb950' if market_data.market_analysis.fear_greed_index > 50 else '#f85149' }}" stroke-width="2" stroke-dasharray="{{ market_data.market_analysis.fear_greed_index }}, 100" />
                            </svg>
                        </div>
                    </div>
                    <p class="text-center text-muted mt-2">Cập nhật: Hôm nay</p>
                </div>
            </div>
            <!-- Market Analysis Summary -->
            <div class="col-md-4">
                <div class="market-card p-3">
                    <h5>Tóm tắt thị trường</h5>
                    <ul class="list-unstyled">
                        <li class="mb-2">
                            <span class="fw-bold">Chu kỳ:</span> 
                            <span class="badge bg-success">{{ market_data.market_analysis.market_cycle }}</span>
                        </li>
                        <li class="mb-2">
                            <span class="fw-bold">Biến động:</span> 
                            <span>{{ market_data.market_analysis.btc_volatility }}%</span>
                        </li>
                        <li class="mb-2">
                            <span class="fw-bold">Thanh khoản:</span>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar bg-info" style="width: {{ market_data.market_analysis.liquidity_index }}%"></div>
                            </div>
                        </li>
                        <li>
                            <span class="fw-bold">Tín hiệu:</span> 
                            <span class="indicator-{{ market_data.technical_indicators.overall_signal }}">
                                {{ 'Tăng giá' if market_data.technical_indicators.overall_signal == 'bullish' else 'Giảm giá' if market_data.technical_indicators.overall_signal == 'bearish' else 'Trung lập' }}
                            </span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <!-- Price Chart -->
            <div class="col-md-8">
                <div class="market-card p-3">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5>Biểu đồ giá BTC/USDT</h5>
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-outline-secondary active">1H</button>
                            <button class="btn btn-outline-secondary">4H</button>
                            <button class="btn btn-outline-secondary">1D</button>
                            <button class="btn btn-outline-secondary">1W</button>
                        </div>
                    </div>
                    <div style="height: 300px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px;">
                        <!-- Chart would go here - using a placeholder -->
                        <div class="d-flex justify-content-center align-items-center h-100">
                            <div class="text-center">
                                <div class="spinner-border text-secondary mb-2" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mb-0">Đang tải biểu đồ...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Technical Indicators -->
            <div class="col-md-4">
                <div class="market-card p-3">
                    <h5>Chỉ báo kỹ thuật</h5>
                    <div class="mb-3">
                        <h6>Đường trung bình động</h6>
                        <div class="d-flex justify-content-between mb-1">
                            <span>MA20</span>
                            <span class="indicator-{{ market_data.technical_indicators.ma_signals.ma_20 }}">
                                <i class="bi {{ 'bi-arrow-up' if market_data.technical_indicators.ma_signals.ma_20 == 'bullish' else 'bi-arrow-down' }}"></i>
                                {{ 'Tăng' if market_data.technical_indicators.ma_signals.ma_20 == 'bullish' else 'Giảm' }}
                            </span>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span>MA50</span>
                            <span class="indicator-{{ market_data.technical_indicators.ma_signals.ma_50 }}">
                                <i class="bi {{ 'bi-arrow-up' if market_data.technical_indicators.ma_signals.ma_50 == 'bullish' else 'bi-arrow-down' }}"></i>
                                {{ 'Tăng' if market_data.technical_indicators.ma_signals.ma_50 == 'bullish' else 'Giảm' }}
                            </span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>MA200</span>
                            <span class="indicator-{{ market_data.technical_indicators.ma_signals.ma_200 }}">
                                <i class="bi {{ 'bi-arrow-up' if market_data.technical_indicators.ma_signals.ma_200 == 'bullish' else 'bi-arrow-down' }}"></i>
                                {{ 'Tăng' if market_data.technical_indicators.ma_signals.ma_200 == 'bullish' else 'Giảm' }}
                            </span>
                        </div>
                    </div>
                    <div>
                        <h6>Bộ dao động</h6>
                        <div class="d-flex justify-content-between mb-1">
                            <span>RSI (14)</span>
                            <span class="indicator-{{ market_data.technical_indicators.oscillators.rsi.signal }}">
                                {{ market_data.technical_indicators.oscillators.rsi.value }}
                            </span>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span>MACD</span>
                            <span class="indicator-{{ market_data.technical_indicators.oscillators.macd.signal }}">
                                {{ 'Tăng' if market_data.technical_indicators.oscillators.macd.signal == 'bullish' else 'Giảm' }}
                            </span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Stochastic</span>
                            <span class="indicator-{{ market_data.technical_indicators.oscillators.stoch.signal }}">
                                {{ market_data.technical_indicators.oscillators.stoch.value }}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mb-4">
            <!-- Top Gainers & Losers -->
            <div class="col-md-6">
                <div class="market-card p-3">
                    <ul class="nav nav-tabs mb-3">
                        <li class="nav-item">
                            <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#gainers">Top Tăng giá</button>
                        </li>
                        <li class="nav-item">
                            <button class="nav-link" data-bs-toggle="tab" data-bs-target="#losers">Top Giảm giá</button>
                        </li>
                    </ul>
                    <div class="tab-content">
                        <div class="tab-pane fade show active" id="gainers">
                            <div class="table-responsive">
                                <table class="table table-sm market-table mb-0">
                                    <thead>
                                        <tr>
                                            <th>Token</th>
                                            <th>Giá</th>
                                            <th>Thay đổi 24h</th>
                                            <th>Khối lượng (M)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for coin in market_data.top_gainers %}
                                        <tr>
                                            <td>
                                                <strong>{{ coin.symbol }}</strong><br>
                                                <small class="text-muted">{{ coin.name }}</small>
                                            </td>
                                            <td>${{ '{:,.2f}'.format(coin.price) }}</td>
                                            <td class="positive-change">+{{ coin.change }}%</td>
                                            <td>{{ coin.volume }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="tab-pane fade" id="losers">
                            <div class="table-responsive">
                                <table class="table table-sm market-table mb-0">
                                    <thead>
                                        <tr>
                                            <th>Token</th>
                                            <th>Giá</th>
                                            <th>Thay đổi 24h</th>
                                            <th>Khối lượng (M)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for coin in market_data.top_losers %}
                                        <tr>
                                            <td>
                                                <strong>{{ coin.symbol }}</strong><br>
                                                <small class="text-muted">{{ coin.name }}</small>
                                            </td>
                                            <td>${{ '{:,.2f}'.format(coin.price) }}</td>
                                            <td class="negative-change">{{ coin.change }}%</td>
                                            <td>{{ coin.volume }}</td>
                                        </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Market News -->
            <div class="col-md-6">
                <div class="market-card p-3">
                    <h5>Tin tức thị trường mới nhất</h5>
                    <div>
                        {% for news in market_data.market_news %}
                        <div class="news-item news-{{ news.impact }}">
                            <h6>{{ news.title }}</h6>
                            <div class="d-flex justify-content-between">
                                <small class="text-muted">{{ news.source }}</small>
                                <small class="text-muted">{{ news.time }}</small>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    <div class="text-center mt-3">
                        <a href="#" class="btn btn-sm btn-outline-secondary">Xem thêm tin tức</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Market Analysis -->
            <div class="col-12">
                <div class="market-card p-3">
                    <h5>Phân tích thị trường chi tiết</h5>
                    <p>{{ market_data.market_analysis.analysis_summary }}</p>
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Vùng hỗ trợ chính</h6>
                            <ul>
                                {% for level in market_data.market_analysis.major_supports %}
                                <li>${{ '{:,.0f}'.format(level) }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6>Vùng kháng cự chính</h6>
                            <ul>
                                {% for level in market_data.market_analysis.major_resistances %}
                                <li>${{ '{:,.0f}'.format(level) }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                    <div class="alert alert-info mt-3">
                        <i class="bi bi-info-circle"></i> <strong>Lưu ý:</strong> Phân tích thị trường này chỉ mang tính chất tham khảo và không phải là lời khuyên đầu tư.
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Language switcher
            document.querySelectorAll('[data-language]').forEach(item => {
                item.addEventListener('click', event => {
                    const language = event.currentTarget.dataset.language;
                    fetch('/api/language', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ language: language }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // Refresh the page to apply the new language
                            location.reload();
                        }
                    });
                });
            });
        });
    </script>
</body>
</html>""")
        
        return render_template('market.html', 
                             bot_status=BOT_STATUS,
                             market_data=current_market_data)
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang thị trường: {str(e)}")
        return render_template('error.html', 
                             error_message="Không thể tải dữ liệu thị trường. Vui lòng thử lại sau.")


@app.route('/position')
def position():
    """Trang quản lý vị thế"""
    try:
        # Khởi tạo dữ liệu hiệu suất cho template
        performance_data = {
            'total_profit': 312.5,
            'win_rate': 68.5,
            'average_profit': 125.8,
            'largest_win': 450.0,
            'largest_loss': -200.0,
            'profit_factor': 2.34
        }
        
        # Cập nhật dữ liệu vị thế từ dữ liệu mẫu hoặc API thực
        current_positions = [
            {
                'id': 'pos1',
                'symbol': 'BTCUSDT',
                'type': 'LONG',
                'entry_price': 72000,
                'current_price': 75000,
                'quantity': 0.1,
                'leverage': 5,
                'pnl': 300,
                'pnl_percent': 4.17,
                'entry_time': '2025-02-28 18:30:00',
                'duration': '1d 12h 26m',
                'stop_loss': 68000,
                'take_profit': 80000,
                'status': 'active',
                'risk_reward': 2.5,
                'strategy': 'RSI + BB',
                'tags': ['trend-following', 'medium-term']
            },
            {
                'id': 'pos2',
                'symbol': 'SOLUSDT',
                'type': 'LONG',
                'entry_price': 125,
                'current_price': 137.5,
                'quantity': 1,
                'leverage': 3,
                'pnl': 12.5,
                'pnl_percent': 10,
                'entry_time': '2025-02-28 20:10:00',
                'duration': '1d 10h 46m',
                'stop_loss': 115,
                'take_profit': 150,
                'status': 'active',
                'risk_reward': 2.5,
                'strategy': 'Support Level',
                'tags': ['support-bounce', 'short-term']
            },
            {
                'id': 'pos3',
                'symbol': 'BNBUSDT',
                'type': 'SHORT',
                'entry_price': 410,
                'current_price': 420,
                'quantity': 0.2,
                'leverage': 2,
                'pnl': -2,
                'pnl_percent': -2.44,
                'entry_time': '2025-02-28 22:05:00',
                'duration': '1d 8h 51m',
                'stop_loss': 430,
                'take_profit': 380,
                'status': 'active',
                'risk_reward': 1.5,
                'strategy': 'Resistance Level',
                'tags': ['resistance-rejection', 'medium-term']
            }
        ]
        
        # Dữ liệu lịch sử vị thế đã đóng
        closed_positions = [
            {
                'id': 'pos_hist_1',
                'symbol': 'ETHUSDT',
                'type': 'LONG',
                'entry_price': 3000,
                'exit_price': 3150,
                'quantity': 0.5,
                'leverage': 2,
                'pnl': 75,
                'pnl_percent': 5.0,
                'entry_time': '2025-02-25 14:30:00',
                'exit_time': '2025-02-27 09:15:00',
                'duration': '1d 18h 45m',
                'exit_reason': 'take_profit',
                'strategy': 'MACD Cross',
                'successful': True
            },
            {
                'id': 'pos_hist_2',
                'symbol': 'DOGEUSDT',
                'type': 'LONG',
                'entry_price': 0.12,
                'exit_price': 0.115,
                'quantity': 1000,
                'leverage': 1,
                'pnl': -5,
                'pnl_percent': -4.17,
                'entry_time': '2025-02-26 10:20:00',
                'exit_time': '2025-02-27 16:45:00',
                'duration': '1d 6h 25m',
                'exit_reason': 'stop_loss',
                'strategy': 'Breakout',
                'successful': False
            },
            {
                'id': 'pos_hist_3',
                'symbol': 'ADAUSDT',
                'type': 'SHORT',
                'entry_price': 0.45,
                'exit_price': 0.42,
                'quantity': 500,
                'leverage': 2,
                'pnl': 3,
                'pnl_percent': 6.67,
                'entry_time': '2025-02-24 18:30:00',
                'exit_time': '2025-02-26 21:10:00',
                'duration': '2d 2h 40m',
                'exit_reason': 'manual',
                'strategy': 'Fibonacci Retracement',
                'successful': True
            }
        ]
        
        # Dữ liệu hiệu suất tổng thể
        performance_data = {
            'total_trades': 25,
            'winning_trades': 17,
            'losing_trades': 8,
            'win_rate': 68.0,
            'average_win': 12.5,
            'average_loss': -7.8,
            'profit_factor': 2.72,
            'expectancy': 5.87,
            'max_drawdown': 15.3,
            'avg_holding_time': '1d 14h',
            'best_trade': 45.2,
            'worst_trade': -18.6,
            'total_profit': 580.5,
            'total_profit_percent': 5.8
        }
        
        # Thông tin thị trường cho các cặp có vị thế
        market_data = {
            'BTCUSDT': {
                'price': 75000,
                'change_24h': 2.5,
                'volume': 1500000000,
                'market_regime': 'Trending',
                'volatility': 'Medium'
            },
            'SOLUSDT': {
                'price': 137.5,
                'change_24h': 5.2,
                'volume': 280000000,
                'market_regime': 'Trending',
                'volatility': 'High'
            },
            'BNBUSDT': {
                'price': 420,
                'change_24h': -1.5,
                'volume': 150000000,
                'market_regime': 'Ranging',
                'volatility': 'Low'
            }
        }
        
        # Cập nhật dữ liệu tài khoản với các vị thế hiện tại
        account_data = {
            'balance': 10400,
            'equity': 10710.5,
            'free_balance': 10400,
            'margin': 0,
            'positions': current_positions
        }
        
        # Tạo template nếu chưa tồn tại
        import os
        template_path = 'templates/position.html'
        if not os.path.exists(template_path):
            with open(template_path, 'w') as f:
                f.write("""<!DOCTYPE html>
<html lang="vi" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quản lý vị thế - Bot Giao Dịch Crypto</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <link rel="icon" href="/static/img/favicon.ico" type="image/x-icon">
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
        }
        .position-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin-bottom: 16px;
        }
        .status-badge {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .status-running {
            background-color: #3fb950;
        }
        .status-stopped {
            background-color: #f85149;
        }
        .mode-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 0.8rem;
            margin-right: 10px;
            color: white;
        }
        .mode-demo {
            background-color: #6c757d;
        }
        .mode-testnet {
            background-color: #fd7e14;
        }
        .mode-live {
            background-color: #dc3545;
        }
        .position-table th, .position-table td {
            padding: 0.5rem;
        }
        .positive-pnl {
            color: #3fb950;
        }
        .negative-pnl {
            color: #f85149;
        }
        .exit-reason-take_profit {
            color: #3fb950;
        }
        .exit-reason-stop_loss {
            color: #f85149;
        }
        .exit-reason-manual {
            color: #58a6ff;
        }
    </style>
</head>
<body>
    <div class="container py-4">
        <header class="d-flex flex-wrap justify-content-between py-3 mb-4 border-bottom">
            <div class="d-flex align-items-center mb-3 mb-md-0 me-md-auto">
                <a href="/" class="d-flex align-items-center text-decoration-none">
                    <i class="bi bi-currency-bitcoin fs-3 me-2"></i>
                    <span class="fs-4">Bot Giao Dịch Crypto</span>
                </a>
                <div class="ms-3">
                    <span class="mode-badge mode-demo">Chế độ Demo</span>
                </div>
            </div>
            
            <div class="d-flex align-items-center">
                <!-- Language selector -->
                <div class="dropdown me-3">
                    <button class="btn btn-sm btn-outline-primary dropdown-toggle" type="button" id="languageDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-translate"></i> Ngôn ngữ
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="languageDropdown">
                        <li><a class="dropdown-item" href="#" data-language="vi"><span class="me-2">🇻🇳</span>Tiếng Việt</a></li>
                        <li><a class="dropdown-item" href="#" data-language="en"><span class="me-2">🇺🇸</span>English</a></li>
                    </ul>
                </div>
                
                <!-- Bot status -->
                <div class="me-3">
                    <span class="status-badge {{ 'status-running' if bot_status.running else 'status-stopped' }}"></span>
                    <span>{{ 'Đang chạy' if bot_status.running else 'Đang dừng' }}</span>
                </div>
                
                <!-- Bot controls -->
                <div class="btn-group">
                    <a href="/" class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-house"></i> Trang chủ
                    </a>
                </div>
            </div>
        </header>

        <div class="row mb-4">
            <div class="col">
                <h2><i class="bi bi-graph-up"></i> Quản lý vị thế</h2>
                <p class="text-muted">Quản lý và theo dõi các vị thế giao dịch đang mở và lịch sử</p>
            </div>
        </div>

        <div class="row mb-4">
            <!-- Account Overview -->
            <div class="col-md-4">
                <div class="position-card p-3">
                    <h5>Tổng quan tài khoản</h5>
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-2">
                            <span>Số dư:</span>
                            <span class="fw-bold">${{ '{:,.2f}'.format(account_data.balance) }}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Equity:</span>
                            <span class="fw-bold">${{ '{:,.2f}'.format(account_data.equity) }}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Margin:</span>
                            <span>{{ '{:,.2f}'.format(account_data.margin) }}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Số dư khả dụng:</span>
                            <span>${{ '{:,.2f}'.format(account_data.free_balance) }}</span>
                        </div>
                    </div>
                    <div class="d-grid gap-2">
                        <button class="btn btn-outline-info" type="button" data-bs-toggle="modal" data-bs-target="#newPositionModal">
                            <i class="bi bi-plus-circle"></i> Mở vị thế mới
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Position Summary -->
            <div class="col-md-4">
                <div class="position-card p-3">
                    <h5>Tóm tắt vị thế</h5>
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-2">
                            <span>Tổng vị thế mở:</span>
                            <span class="fw-bold">{{ account_data.positions|length }}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>PnL tổng:</span>
                            {% set total_pnl = 0 %}
                            {% for position in account_data.positions %}
                                {% set total_pnl = total_pnl + position.pnl %}
                            {% endfor %}
                            <span class="fw-bold {{ 'positive-pnl' if total_pnl >= 0 else 'negative-pnl' }}">
                                ${{ '{:,.2f}'.format(total_pnl) }}
                            </span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Vị thế LONG:</span>
                            <span>{{ account_data.positions|selectattr('type', 'equalto', 'LONG')|list|length }}</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Vị thế SHORT:</span>
                            <span>{{ account_data.positions|selectattr('type', 'equalto', 'SHORT')|list|length }}</span>
                        </div>
                    </div>
                    <div class="d-grid gap-2">
                        <button class="btn btn-outline-danger" type="button" id="closeAllPositionsBtn">
                            <i class="bi bi-x-circle"></i> Đóng tất cả vị thế
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Risk Management -->
            <div class="col-md-4">
                <div class="position-card p-3">
                    <h5>Quản lý rủi ro</h5>
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-2">
                            <span>Rủi ro mỗi giao dịch:</span>
                            <span>1.0%</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Đòn bẩy mặc định:</span>
                            <span>3x</span>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Stop-loss mặc định:</span>
                            <span>-3.0%</span>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Take-profit mặc định:</span>
                            <span>+6.0%</span>
                        </div>
                    </div>
                    <div class="d-grid gap-2">
                        <button class="btn btn-outline-secondary" type="button" data-bs-toggle="modal" data-bs-target="#riskSettingsModal">
                            <i class="bi bi-gear"></i> Cài đặt rủi ro
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Open Positions -->
        <div class="position-card p-3 mb-4">
            <h5>Vị thế đang mở</h5>
            <div class="table-responsive">
                <table class="table table-sm position-table mb-0">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Loại</th>
                            <th>Giá vào</th>
                            <th>Giá hiện tại</th>
                            <th>SL/TP</th>
                            <th>Số lượng</th>
                            <th>Đòn bẩy</th>
                            <th>PnL</th>
                            <th>Thời gian vào</th>
                            <th>Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for position in account_data.positions %}
                        <tr>
                            <td><strong>{{ position.symbol }}</strong></td>
                            <td>
                                <span class="{{ 'text-success' if position.type == 'LONG' else 'text-danger' }}">
                                    {{ position.type }}
                                </span>
                            </td>
                            <td>{{ '{:,.2f}'.format(position.entry_price) }}</td>
                            <td>{{ '{:,.2f}'.format(position.current_price) }}</td>
                            <td>
                                <small>SL: {{ '{:,.2f}'.format(position.stop_loss) }}</small><br>
                                <small>TP: {{ '{:,.2f}'.format(position.take_profit) }}</small>
                            </td>
                            <td>{{ position.quantity }}</td>
                            <td>{{ position.leverage }}x</td>
                            <td class="{{ 'positive-pnl' if position.pnl > 0 else 'negative-pnl' }}">
                                ${{ '{:,.2f}'.format(position.pnl) }}<br>
                                <small>{{ '{:,.2f}%'.format(position.pnl_percent) }}</small>
                            </td>
                            <td>{{ position.entry_time }}</td>
                            <td>
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-danger close-position-btn" data-position-id="{{ position.id }}">
                                        <i class="bi bi-x-circle"></i> Đóng
                                    </button>
                                    <button class="btn btn-outline-secondary edit-position-btn" data-position-id="{{ position.id }}">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="10" class="text-center">Không có vị thế đang mở</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Position History -->
        <div class="position-card p-3">
            <h5>Lịch sử vị thế</h5>
            <div class="table-responsive">
                <table class="table table-sm position-table mb-0">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Loại</th>
                            <th>Giá vào/ra</th>
                            <th>SL/TP</th>
                            <th>Số lượng</th>
                            <th>Đòn bẩy</th>
                            <th>PnL</th>
                            <th>Thời gian vào/ra</th>
                            <th>Lý do đóng</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for position in position_history %}
                        <tr>
                            <td><strong>{{ position.symbol }}</strong></td>
                            <td>
                                <span class="{{ 'text-success' if position.type == 'LONG' else 'text-danger' }}">
                                    {{ position.type }}
                                </span>
                            </td>
                            <td>
                                <small>Vào: {{ '{:,.2f}'.format(position.entry_price) }}</small><br>
                                <small>Ra: {{ '{:,.2f}'.format(position.exit_price) }}</small>
                            </td>
                            <td>
                                <small>SL: {{ '{:,.2f}'.format(position.stop_loss) }}</small><br>
                                <small>TP: {{ '{:,.2f}'.format(position.take_profit) }}</small>
                            </td>
                            <td>{{ position.quantity }}</td>
                            <td>{{ position.leverage }}x</td>
                            <td class="{{ 'positive-pnl' if position.pnl > 0 else 'negative-pnl' }}">
                                ${{ '{:,.2f}'.format(position.pnl) }}<br>
                                <small>{{ '{:,.2f}%'.format(position.pnl_percent) }}</small>
                            </td>
                            <td>
                                <small>Vào: {{ position.entry_time }}</small><br>
                                <small>Ra: {{ position.exit_time }}</small>
                            </td>
                            <td>
                                <span class="exit-reason-{{ position.exit_reason }}">
                                    {% if position.exit_reason == 'take_profit' %}
                                        Take Profit
                                    {% elif position.exit_reason == 'stop_loss' %}
                                        Stop Loss
                                    {% elif position.exit_reason == 'manual' %}
                                        Đóng thủ công
                                    {% else %}
                                        {{ position.exit_reason }}
                                    {% endif %}
                                </span>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="9" class="text-center">Không có dữ liệu lịch sử</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modal mở vị thế mới -->
    <div class="modal fade" id="newPositionModal" tabindex="-1" aria-labelledby="newPositionModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content bg-dark">
                <div class="modal-header">
                    <h5 class="modal-title" id="newPositionModalLabel">Mở vị thế mới</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="newPositionForm">
                        <div class="mb-3">
                            <label for="symbol" class="form-label">Symbol</label>
                            <select class="form-select" id="symbol" required>
                                <option value="BTCUSDT">BTCUSDT</option>
                                <option value="ETHUSDT">ETHUSDT</option>
                                <option value="BNBUSDT">BNBUSDT</option>
                                <option value="SOLUSDT">SOLUSDT</option>
                                <option value="ADAUSDT">ADAUSDT</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Loại vị thế</label>
                            <div class="d-flex">
                                <div class="form-check me-4">
                                    <input class="form-check-input" type="radio" name="positionType" id="typeLong" value="LONG" checked>
                                    <label class="form-check-label text-success" for="typeLong">
                                        LONG
                                    </label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="positionType" id="typeShort" value="SHORT">
                                    <label class="form-check-label text-danger" for="typeShort">
                                        SHORT
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label for="quantity" class="form-label">Số lượng</label>
                            <input type="number" class="form-control" id="quantity" step="0.001" min="0.001" required>
                        </div>
                        <div class="mb-3">
                            <label for="leverage" class="form-label">Đòn bẩy (1-100x)</label>
                            <input type="number" class="form-control" id="leverage" min="1" max="100" value="3" required>
                        </div>
                        <div class="mb-3">
                            <label for="stopLossPercent" class="form-label">Stop-Loss (%)</label>
                            <input type="number" class="form-control" id="stopLossPercent" step="0.1" value="3" required>
                        </div>
                        <div class="mb-3">
                            <label for="takeProfitPercent" class="form-label">Take-Profit (%)</label>
                            <input type="number" class="form-control" id="takeProfitPercent" step="0.1" value="6" required>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Hủy</button>
                    <button type="button" class="btn btn-primary" id="submitNewPosition">Mở vị thế</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal cài đặt rủi ro -->
    <div class="modal fade" id="riskSettingsModal" tabindex="-1" aria-labelledby="riskSettingsModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content bg-dark">
                <div class="modal-header">
                    <h5 class="modal-title" id="riskSettingsModalLabel">Cài đặt quản lý rủi ro</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="riskSettingsForm">
                        <div class="mb-3">
                            <label for="riskPerTrade" class="form-label">Rủi ro mỗi giao dịch (%)</label>
                            <input type="number" class="form-control" id="riskPerTrade" step="0.1" min="0.1" max="5" value="1" required>
                            <div class="form-text">% tài khoản tối đa có thể mất trong một giao dịch</div>
                        </div>
                        <div class="mb-3">
                            <label for="defaultLeverage" class="form-label">Đòn bẩy mặc định</label>
                            <input type="number" class="form-control" id="defaultLeverage" min="1" max="100" value="3" required>
                        </div>
                        <div class="mb-3">
                            <label for="defaultSL" class="form-label">Stop-Loss mặc định (%)</label>
                            <input type="number" class="form-control" id="defaultSL" step="0.1" min="0.5" value="3" required>
                        </div>
                        <div class="mb-3">
                            <label for="defaultTP" class="form-label">Take-Profit mặc định (%)</label>
                            <input type="number" class="form-control" id="defaultTP" step="0.1" min="0.5" value="6" required>
                        </div>
                        <div class="mb-3">
                            <label for="maxPositions" class="form-label">Số vị thế mở tối đa</label>
                            <input type="number" class="form-control" id="maxPositions" min="1" max="20" value="5" required>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="useTrailingStop" checked>
                            <label class="form-check-label" for="useTrailingStop">Sử dụng Trailing Stop</label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Hủy</button>
                    <button type="button" class="btn btn-primary" id="saveRiskSettings">Lưu cài đặt</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Xử lý đóng vị thế
            document.querySelectorAll('.close-position-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const positionId = this.dataset.positionId;
                    if (confirm('Bạn có chắc muốn đóng vị thế này?')) {
                        closePosition(positionId);
                    }
                });
            });
            
            // Xử lý đóng tất cả vị thế
            document.getElementById('closeAllPositionsBtn').addEventListener('click', function() {
                if (confirm('Bạn có chắc muốn đóng TẤT CẢ vị thế đang mở?')) {
                    document.querySelectorAll('.close-position-btn').forEach(button => {
                        closePosition(button.dataset.positionId);
                    });
                }
            });
            
            // Hàm đóng vị thế
            function closePosition(positionId) {
                fetch('/api/positions/close', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ position_id: positionId }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('Đã đóng vị thế thành công!');
                        location.reload();
                    } else {
                        alert('Lỗi khi đóng vị thế: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Đã xảy ra lỗi khi kết nối đến máy chủ');
                });
            }
            
            // Xử lý mở vị thế mới
            document.getElementById('submitNewPosition').addEventListener('click', function() {
                // TODO: Thêm logic gửi dữ liệu lên server để mở vị thế mới
                alert('Chức năng mở vị thế mới đang được phát triển. Vui lòng thử lại sau.');
            });
            
            // Xử lý lưu cài đặt rủi ro
            document.getElementById('saveRiskSettings').addEventListener('click', function() {
                // TODO: Thêm logic gửi dữ liệu lên server để lưu cài đặt rủi ro
                alert('Đã lưu cài đặt rủi ro!');
                document.getElementById('riskSettingsModal').querySelector('.btn-close').click();
            });
            
            // Language switcher
            document.querySelectorAll('[data-language]').forEach(item => {
                item.addEventListener('click', event => {
                    const language = event.currentTarget.dataset.language;
                    fetch('/api/language', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ language: language }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // Refresh the page to apply the new language
                            location.reload();
                        }
                    });
                });
            });
        });
    </script>
</body>
</html>""")
        
        # Lịch sử giao dịch
        position_history = [
            {
                'id': 'hist1',
                'symbol': 'ETHUSDT',
                'type': 'LONG',
                'entry_price': 2200,
                'exit_price': 2350,
                'quantity': 0.5,
                'leverage': 1,
                'pnl': 75,
                'pnl_percent': 6.82,
                'stop_loss': 2150,
                'take_profit': 2400,
                'entry_time': '2025-02-25 14:30:00',
                'exit_time': '2025-02-27 09:45:00',
                'exit_reason': 'take_profit'
            },
            {
                'id': 'hist2',
                'symbol': 'BTCUSDT',
                'type': 'SHORT',
                'entry_price': 72500,
                'exit_price': 71200,
                'quantity': 0.05,
                'leverage': 1,
                'pnl': 65,
                'pnl_percent': 1.79,
                'stop_loss': 73000,
                'take_profit': 71000,
                'entry_time': '2025-02-26 10:15:00',
                'exit_time': '2025-02-27 18:20:00',
                'exit_reason': 'take_profit'
            },
            {
                'id': 'hist3',
                'symbol': 'DOGEUSDT',
                'type': 'LONG',
                'entry_price': 0.11,
                'exit_price': 0.105,
                'quantity': 1000,
                'leverage': 1,
                'pnl': -5,
                'pnl_percent': -4.55,
                'stop_loss': 0.105,
                'take_profit': 0.12,
                'entry_time': '2025-02-27 11:30:00',
                'exit_time': '2025-02-28 03:10:00',
                'exit_reason': 'stop_loss'
            }
        ]
        
        return render_template('position.html', 
                             bot_status=BOT_STATUS,
                             account_data=account_data,
                             position_history=position_history)
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang vị thế: {str(e)}")
        return render_template('error.html', 
                             error_message="Không thể tải dữ liệu vị thế. Vui lòng thử lại sau.")


@app.route('/settings')
def settings():
    """Trang cài đặt bot"""
    try:
        # Tạo dữ liệu cài đặt hiện tại
        current_settings = {
            'api_key': '••••••••••••••••',
            'api_secret': '••••••••••••••••••••••••••••••••',
            'api_mode': BOT_STATUS['mode'],  # 'demo', 'testnet', 'live'
            'account_type': BOT_STATUS['account_type'],  # 'spot', 'futures'
            'risk_profile': 'medium',  # 'very_low', 'low', 'medium', 'high', 'very_high'
            'risk_per_trade': 1.0,  # Phần trăm rủi ro trên mỗi giao dịch
            'max_positions': 5,  # Số lượng vị thế tối đa
            'leverage': 5,  # Đòn bẩy mặc định (1-100)
            'enable_auto_bot': True,  # Tự động điều chỉnh chiến lược
            'telegram_enabled': False,  # Kích hoạt thông báo Telegram
            'telegram_token': '',
            'telegram_chat_id': '',
            'strategy_mode': BOT_STATUS['strategy_mode'],  # 'auto', 'manual'
            'active_symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'],
            'timeframes': ['15m', '1h', '4h', '1d'],
            'auto_restart': True,  # Tự động khởi động lại khi bot bị crash
            'language': 'vi'  # 'vi', 'en'
        }
        
        # Tạo dữ liệu chiến lược hiện tại
        current_strategies = [
            {
                'id': 'rsi_strategy',
                'name': 'RSI Strategy',
                'enabled': True,
                'timeframes': ['1h', '4h'],
                'default_for': ['trending', 'volatile'],
                'params': {
                    'rsi_period': 14,
                    'rsi_overbought': 70,
                    'rsi_oversold': 30,
                    'use_ma_filter': True,
                    'ma_period': 200
                }
            },
            {
                'id': 'macd_strategy',
                'name': 'MACD Strategy',
                'enabled': True,
                'timeframes': ['1h', '4h', '1d'],
                'default_for': ['trending'],
                'params': {
                    'fast_period': 12,
                    'slow_period': 26,
                    'signal_period': 9,
                    'use_histogram': True
                }
            },
            {
                'id': 'bb_strategy',
                'name': 'Bollinger Bands',
                'enabled': True,
                'timeframes': ['15m', '1h', '4h'],
                'default_for': ['ranging'],
                'params': {
                    'bb_period': 20,
                    'bb_std': 2.0,
                    'use_confirmation': True
                }
            },
            {
                'id': 'sr_strategy',
                'name': 'Support/Resistance',
                'enabled': True,
                'timeframes': ['1h', '4h', '1d'],
                'default_for': ['ranging', 'volatile'],
                'params': {
                    'num_levels': 5,
                    'lookback_period': 30,
                    'zone_width_percent': 1.0
                }
            },
            {
                'id': 'auto_strategy',
                'name': 'Auto Strategy (AI)',
                'enabled': True,
                'timeframes': ['15m', '1h', '4h', '1d'],
                'default_for': ['all'],
                'params': {
                    'market_regime_detection': True,
                    'adaptive_parameters': True,
                    'use_ml_prediction': True,
                    'optimization_frequency': 'daily'
                }
            }
        ]
        
        # Tạo dữ liệu cài đặt rủi ro
        risk_settings = {
            'risk_profiles': {
                'very_low': {
                    'risk_percent': 0.5,
                    'max_positions': 3,
                    'max_leverage': 2
                },
                'low': {
                    'risk_percent': 1.0,
                    'max_positions': 5,
                    'max_leverage': 5
                },
                'medium': {
                    'risk_percent': 2.0,
                    'max_positions': 7,
                    'max_leverage': 10
                },
                'high': {
                    'risk_percent': 3.0,
                    'max_positions': 10,
                    'max_leverage': 20
                },
                'very_high': {
                    'risk_percent': 5.0,
                    'max_positions': 15,
                    'max_leverage': 50
                }
            }
        }
        
        return render_template('settings.html', 
                            bot_status=BOT_STATUS,
                            settings=current_settings,
                            strategies=current_strategies,
                            risk_settings=risk_settings)
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị trang cài đặt: {str(e)}")
        return render_template('error.html', 
                            error_message="Không thể tải trang cài đặt. Vui lòng thử lại sau.")


@app.route('/account')
def account():
    """Trang cài đặt tài khoản và API"""
    return render_template('account.html', 
                          bot_status=BOT_STATUS)


@app.route('/updates')
def updates():
    """Trang quản lý cập nhật"""
    try:
        from update_manager import UpdateManager
        update_manager = UpdateManager()
        return render_template('updates.html', 
                            bot_status=BOT_STATUS,
                            current_version=update_manager.get_current_version(),
                            available_updates=update_manager.get_available_updates(),
                            update_history=update_manager.get_update_history(),
                            backups=update_manager.get_available_backups())
    except Exception as e:
        logger.error(f"Lỗi khi tải trang updates: {e}")
        return render_template('error.html', 
                            error_message=f"Không thể tải trang cập nhật: {str(e)}",
                            bot_status=BOT_STATUS)


@app.route('/trading_report')
def trading_report():
    """Trang báo cáo giao dịch"""
    return render_template('trading_report.html',
                          bot_status=BOT_STATUS)


@app.route('/cli')
def cli():
    """Trang giao diện dòng lệnh"""
    return render_template('cli.html',
                          bot_status=BOT_STATUS)


# API Endpoints
@app.route('/api/language', methods=['POST'])
def change_language():
    """Thay đổi ngôn ngữ"""
    data = request.json
    language = data.get('language', 'en')
    
    # Lưu cài đặt ngôn ngữ vào session
    session['language'] = language
    logger.info(f"Đã thay đổi ngôn ngữ thành: {language}")
    
    return jsonify({'status': 'success', 'message': 'Ngôn ngữ đã được thay đổi'})


@app.route('/api/telegram/test', methods=['POST'])
def test_telegram():
    """Kiểm tra kết nối Telegram"""
    data = request.json
    token = data.get('token', '')
    chat_id = data.get('chat_id', '')
    
    if not token or not chat_id:
        return jsonify({'status': 'error', 'message': 'Thiếu token hoặc chat ID'})
    
    # Mô phỏng gửi tin nhắn thử nghiệm
    try:
        # Lưu ý: Trong ứng dụng thực tế, chúng ta sẽ thực sự gửi một tin nhắn qua API Telegram
        logger.info(f"Gửi tin nhắn thử nghiệm với token={token[:5]}... và chat_id={chat_id}")
        
        # Mô phỏng thành công
        return jsonify({
            'status': 'success', 
            'message': 'Thông báo kiểm tra được gửi thành công! Vui lòng kiểm tra điện thoại của bạn.'
        })
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo Telegram: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Không thể gửi thông báo: {str(e)}'
        })


# Route /api/bot/control đã được chuyển sang blueprint bot_api_routes.py
    elif action == 'switch_mode':
        BOT_STATUS['strategy_mode'] = strategy_mode
        logger.info(f"Đã chuyển chế độ chiến lược sang: {strategy_mode}")
        return jsonify({
            'success': True, 
            'message': f'Đã chuyển chế độ chiến lược sang {strategy_mode}'
        })
    
    else:
        return jsonify({'success': False, 'message': 'Hành động không hợp lệ'})


# Sửa lỗi xung đột với Blueprint config_route.py
# Bỏ đường dẫn này vì đã được xử lý trong config_route.py
# @app.route('/api/account/settings', methods=['GET', 'POST'])
# def account_settings():
#     """Lấy hoặc cập nhật cài đặt tài khoản"""
#     if request.method == 'GET':
#         # Lấy cài đặt hiện tại
#         settings = {
#             'api_mode': BOT_STATUS.get('mode', 'testnet'),  # 'demo', 'testnet', 'live'
#             'account_type': BOT_STATUS.get('account_type', 'futures'),  # 'spot', 'futures'
#             'risk_profile': 'medium',  # 'very_low', 'low', 'medium', 'high', 'very_high'
#             'leverage': 10,  # 1-100
#             'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
#             'timeframes': ['5m', '15m', '1h', '4h']
#         }
#         return jsonify(settings)
    
# Xóa phần POST để tránh xung đột với config_route.py
# Các phần xung đột đã được xử lý trong file config_route.py


@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Đóng một vị thế"""
    data = request.json
    position_id = data.get('position_id')
    
    # Tìm vị thế trong danh sách (giả lập)
    # Sau này gọi API thực tế để đóng vị thế
    logger.info(f"Yêu cầu đóng vị thế {position_id}")
    
    return jsonify({'status': 'success', 'message': f'Vị thế {position_id} đã được đóng'})


@app.route('/api/bot/status', methods=['GET'])
def get_bot_status():
    """Lấy trạng thái hiện tại của bot"""
    # Luôn đọc trạng thái mới nhất từ file
    updated_status = get_bot_status_from_config()
    # Cập nhật BOT_STATUS toàn cục
    BOT_STATUS.update(updated_status)
    # Thêm trường status cho frontend
    response_data = BOT_STATUS.copy()
    response_data['status'] = 'running' if BOT_STATUS.get('running', False) else 'stopped'
    logger.debug(f"Trạng thái bot hiện tại: {response_data}")
    return jsonify(response_data)
    
@app.route('/api/bot/status/check', methods=['GET'])
def check_bot_status():
    """Endpoint mới kiểm tra trạng thái của bot"""
    updated_status = get_bot_status_from_config()
    BOT_STATUS.update(updated_status)
    # Tạo response với trạng thái rõ ràng
    response_data = {
        'running': BOT_STATUS.get('running', False),
        'status': 'running' if BOT_STATUS.get('running', False) else 'stopped',
        'mode': BOT_STATUS.get('mode', 'demo'),
        'version': BOT_STATUS.get('version', '1.0.0'),
        'active_symbols': BOT_STATUS.get('active_symbols', []),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    logger.info(f"Kiểm tra trạng thái bot: {response_data}")
    return jsonify(response_data)


@app.route('/api/account', methods=['GET'])
def get_account():
    """Lấy dữ liệu tài khoản"""
    try:
        # Lấy thông tin cấu hình tài khoản mới nhất
        BOT_STATUS.update(get_bot_status_from_config())
        
        # Chế độ hoạt động từ cấu hình cập nhật
        mode = BOT_STATUS.get('mode', 'testnet')
        
        # Khởi tạo API client với thông tin API key từ biến môi trường
        api_key = os.environ.get('BINANCE_API_KEY', '')
        api_secret = os.environ.get('BINANCE_API_SECRET', '')
        
        # Dù ở chế độ nào cũng kết nối để kiểm tra dữ liệu API, nếu demo thì vẫn có API
        logger.info(f"Đang kết nối Binance API với key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
        logger.info(f"Chế độ API: {mode}, Testnet: {mode == 'testnet'}")
        
        binance_client = binance_api.BinanceAPI(
            api_key=api_key,
            api_secret=api_secret,
            testnet=(mode == 'testnet')
        )
        
        # Lấy dữ liệu tài khoản từ Binance
        account_info = {}
        positions = []
        use_real_data = True  # Cờ để xác định sử dụng dữ liệu thực hay giả lập
        
        try:
            # Lấy thông tin tài khoản
            if BOT_STATUS.get('account_type') == 'futures':
                account_info = binance_client.get_futures_account()
                
                # Kiểm tra nếu có lỗi trong dữ liệu tài khoản
                if isinstance(account_info, str) or (isinstance(account_info, dict) and account_info.get('error')):
                    logger.error(f"Lỗi API: {account_info if isinstance(account_info, str) else account_info.get('error')}")
                    if mode == 'demo':
                        use_real_data = False
                        logger.info("Chuyển sang sử dụng dữ liệu giả lập do lỗi API và đang trong chế độ demo")
                    
                # Lấy thông tin vị thế
                position_risk = binance_client.get_futures_position_risk()
                
                # Kiểm tra nếu position_risk không phải list hoặc rỗng
                if not isinstance(position_risk, list):
                    logger.error(f"Lỗi API khi lấy vị thế: {position_risk}")
                    if mode == 'demo':
                        use_real_data = False
                
                # Nếu vẫn sử dụng dữ liệu thực, xử lý dữ liệu từ API
                if use_real_data:
                    # Chuyển đổi dữ liệu vị thế
                    for pos in position_risk:
                        try:
                            # Chỉ thêm vị thế có số lượng khác 0
                            position_amt = float(pos.get('positionAmt', 0))
                            if abs(position_amt) > 0:
                                positions.append({
                                    'id': f"pos_{pos.get('symbol', 'unknown')}",
                                    'symbol': pos.get('symbol', 'UNKNOWN'),
                                    'type': 'LONG' if position_amt > 0 else 'SHORT',
                                    'entry_price': float(pos.get('entryPrice', 0)),
                                    'current_price': float(pos.get('markPrice', 0)),
                                    'quantity': abs(position_amt),
                                    'leverage': int(float(pos.get('leverage', 1))),
                                    'pnl': float(pos.get('unRealizedProfit', 0)),
                                    'pnl_percent': float(pos.get('unRealizedProfit', 0)) / (float(pos.get('isolatedWallet', 1)) or 1) * 100 if float(pos.get('isolatedWallet', 0)) > 0 else 0,
                                    'entry_time': datetime.datetime.fromtimestamp(int(pos.get('updateTime', datetime.datetime.now().timestamp() * 1000)) / 1000).strftime('%Y-%m-%d %H:%M:%S') if pos.get('updateTime') else datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'stop_loss': 0,
                                    'take_profit': 0
                                })
                        except Exception as e:
                            logger.error(f"Lỗi khi xử lý vị thế {pos.get('symbol', 'unknown')}: {str(e)}")
                else:  # spot
                    account_info = binance_client.get_account()
                    # Spot không có vị thế, chỉ có tài sản
                
                # Thiết lập dữ liệu tài khoản
                if BOT_STATUS.get('account_type') == 'futures':
                    # Lấy thông tin leverage từ tài khoản nếu có
                    avg_leverage = 5  # Mặc định
                    if positions:
                        total_leverage = sum(pos.get('leverage', 1) for pos in positions)
                        avg_leverage = total_leverage // len(positions)
                    
                    # Xử lý an toàn các giá trị tài khoản để tránh lỗi
                    balance = 0
                    try:
                        balance = float(account_info.get('totalWalletBalance', 0))
                    except (TypeError, ValueError):
                        logger.error("Lỗi khi chuyển đổi totalWalletBalance")
                    
                    equity = 0
                    try:
                        equity = float(account_info.get('totalMarginBalance', 0))
                    except (TypeError, ValueError):
                        logger.error("Lỗi khi chuyển đổi totalMarginBalance")
                        equity = balance  # Fallback to balance
                    
                    margin_used = 0
                    try:
                        margin_used = float(account_info.get('totalPositionInitialMargin', 0))
                    except (TypeError, ValueError):
                        logger.error("Lỗi khi chuyển đổi totalPositionInitialMargin")
                    
                    margin_available = 0
                    try:
                        margin_available = float(account_info.get('availableBalance', 0))
                    except (TypeError, ValueError):
                        logger.error("Lỗi khi chuyển đổi availableBalance")
                        margin_available = balance - margin_used  # Calculate if not available
                    
                    # Đóng gói dữ liệu tài khoản
                    balance_data = {
                        'balance': balance,
                        'equity': equity,
                        'margin_used': margin_used,
                        'margin_available': margin_available,
                        'free_balance': margin_available,  # Same as available margin
                        'positions': positions,
                        'leverage': avg_leverage
                    }
                else:  # spot
                    # Tính tổng giá trị tài sản USDT
                    total_usdt = 0
                    for asset in account_info.get('balances', []):
                        if asset['asset'] == 'USDT':
                            total_usdt = float(asset['free']) + float(asset['locked'])
                    
                    balance_data = {
                        'balance': total_usdt,
                        'equity': total_usdt,
                        'margin_used': 0,
                        'margin_available': total_usdt,
                        'free_balance': total_usdt,
                        'positions': [],  # Spot không có vị thế
                        'leverage': 1
                    }
                
                logger.info(f"Đã lấy dữ liệu tài khoản thành công: {len(positions)} vị thế")
                return jsonify(balance_data)
            
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu từ Binance API: {str(e)}")
                # Trả về dữ liệu giả lập nếu có lỗi
        
        # Trả về dữ liệu giả lập cho chế độ demo hoặc khi lỗi
        logger.info("Sử dụng dữ liệu tài khoản giả lập trong chế độ demo")
        return jsonify(ACCOUNT_DATA)
    
    except Exception as e:
        logger.error(f"Lỗi khi xử lý API account: {str(e)}")
        return jsonify(ACCOUNT_DATA)


@app.route('/api/signals', methods=['GET'])
def get_signals():
    """Lấy tín hiệu giao dịch gần đây"""
    # Giả lập tín hiệu giao dịch
    signals = [
        {
            'time': (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M'),
            'symbol': 'BTCUSDT',
            'signal': 'BUY',
            'confidence': 85,
            'price': 70123.45,
            'executed': True
        },
        {
            'time': (datetime.datetime.now() - datetime.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M'),
            'symbol': 'ETHUSDT',
            'signal': 'SELL',
            'confidence': 72,
            'price': 3890.12,
            'executed': True
        },
        {
            'time': (datetime.datetime.now() - datetime.timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M'),
            'symbol': 'SOLUSDT',
            'signal': 'BUY',
            'confidence': 67,
            'price': 175.35,
            'executed': False
        }
    ]
    return jsonify(signals)


@app.route('/api/market', methods=['GET'])
def get_market():
    """Lấy dữ liệu thị trường"""
    try:
        # Lấy thông tin cấu hình tài khoản mới nhất
        BOT_STATUS.update(get_bot_status_from_config())
        
        # Chế độ hoạt động từ cấu hình cập nhật
        mode = BOT_STATUS.get('mode', 'testnet')
        logger.info(f"Chế độ API hiện tại: {mode}")
        
        # Luôn thử kết nối API Binance trước, kể cả trong chế độ demo
        try:
            # Khởi tạo API client với thông tin API key từ biến môi trường
            api_key = os.environ.get('BINANCE_API_KEY', '')
            api_secret = os.environ.get('BINANCE_API_SECRET', '')
            
            binance_client = binance_api.BinanceAPI(
                api_key=api_key,
                api_secret=api_secret,
                testnet=(mode == 'testnet')
            )
            
            # Dữ liệu giá và thay đổi mặc định để tránh lỗi
            market_data_real = {
                'btc_price': 0,
                'eth_price': 0,
                'bnb_price': 0, 
                'sol_price': 0,
                'btc_change_24h': 0,
                'eth_change_24h': 0,
                'bnb_change_24h': 0,
                'sol_change_24h': 0
            }
            
            use_real_data = True
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
            tickers = {}
            tickers_24h = {}
            
            # Lấy giá hiện tại và dữ liệu 24h
            for symbol in symbols:
                try:
                    ticker = binance_client.get_symbol_ticker(symbol=symbol)
                    if not isinstance(ticker, dict) or 'price' not in ticker:
                        logger.error(f"Lỗi dữ liệu ticker không đúng định dạng cho {symbol}: {ticker}")
                        use_real_data = False if mode == 'demo' else True
                        break
                    tickers[symbol] = ticker
                    
                    ticker_24h = binance_client.get_24h_ticker(symbol=symbol)
                    if not isinstance(ticker_24h, dict) or 'priceChangePercent' not in ticker_24h:
                        logger.error(f"Lỗi dữ liệu ticker 24h không đúng định dạng cho {symbol}: {ticker_24h}")
                        use_real_data = False if mode == 'demo' else True
                        break
                    tickers_24h[symbol] = ticker_24h
                except Exception as e:
                    logger.error(f"Lỗi khi lấy dữ liệu {symbol}: {str(e)}")
                    use_real_data = False if mode == 'demo' else True
                    break
            
            # Nếu vẫn sử dụng dữ liệu thực, xử lý dữ liệu từ API
            if use_real_data and len(tickers) == len(symbols):
                try:
                    # Cập nhật dữ liệu giá
                    market_data_real['btc_price'] = float(tickers['BTCUSDT'].get('price', 0))
                    market_data_real['eth_price'] = float(tickers['ETHUSDT'].get('price', 0))
                    market_data_real['bnb_price'] = float(tickers['BNBUSDT'].get('price', 0))
                    market_data_real['sol_price'] = float(tickers['SOLUSDT'].get('price', 0))
                    
                    # Cập nhật dữ liệu thay đổi 24h
                    market_data_real['btc_change_24h'] = float(tickers_24h['BTCUSDT'].get('priceChangePercent', 0))
                    market_data_real['eth_change_24h'] = float(tickers_24h['ETHUSDT'].get('priceChangePercent', 0))
                    market_data_real['bnb_change_24h'] = float(tickers_24h['BNBUSDT'].get('priceChangePercent', 0))
                    market_data_real['sol_change_24h'] = float(tickers_24h['SOLUSDT'].get('priceChangePercent', 0))
                    
                    # Tạo dữ liệu thị trường từ API
                    market_data = {
                        'btc_price': market_data_real['btc_price'],
                        'eth_price': market_data_real['eth_price'],
                        'bnb_price': market_data_real['bnb_price'],
                        'sol_price': market_data_real['sol_price'],
                        'btc_change_24h': market_data_real['btc_change_24h'],
                        'eth_change_24h': market_data_real['eth_change_24h'],
                        'bnb_change_24h': market_data_real['bnb_change_24h'],
                        'sol_change_24h': market_data_real['sol_change_24h'],
                        'sentiment': {
                            'value': int(50 + market_data_real['btc_change_24h']),  # Giá trị tạm thời
                            'state': 'success' if market_data_real['btc_change_24h'] > 0 else 'danger',
                            'change': market_data_real['btc_change_24h'],
                            'description': 'Tham lam' if market_data_real['btc_change_24h'] > 0 else 'Sợ hãi'
                        },
                        'market_regime': {
                            'BTCUSDT': 'Trending' if abs(market_data_real['btc_change_24h']) > 2 else 'Ranging',
                            'ETHUSDT': 'Trending' if abs(market_data_real['eth_change_24h']) > 2 else 'Ranging',
                            'BNBUSDT': 'Trending' if abs(market_data_real['bnb_change_24h']) > 2 else 'Ranging',
                            'SOLUSDT': 'Trending' if abs(market_data_real['sol_change_24h']) > 2 else 'Ranging'
                        }
                    }
                    
                    logger.info(f"Đã lấy dữ liệu thị trường thành công từ Binance API")
                    return jsonify(market_data)
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý dữ liệu thị trường: {str(e)}")
                    # Sẽ tiếp tục sử dụng dữ liệu giả lập nếu có lỗi
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu thị trường từ Binance API: {str(e)}")
            # Trả về dữ liệu giả lập nếu có lỗi
        
        # Trả về dữ liệu giả lập cho chế độ demo hoặc khi lỗi
        logger.info("Sử dụng dữ liệu thị trường giả lập")
        return jsonify(MARKET_DATA)
    
    except Exception as e:
        logger.error(f"Lỗi khi xử lý API market: {str(e)}")
        return jsonify(MARKET_DATA)


@app.route('/api/cli/execute', methods=['POST'])
def execute_cli_command():
    """Thực thi lệnh từ CLI web"""
    data = request.json
    command = data.get('command', '')
    
    # Xử lý lệnh
    result = {
        'success': True,
        'output': f"Executed command: {command}",
        'error': None
    }
    
    # TODO: Implement thực tế xử lý lệnh từ CLI
    
    return jsonify(result)


# Tác vụ nền
def update_market_data():
    """Cập nhật dữ liệu thị trường theo định kỳ"""
    global BOT_STATUS
    try:
        # Cập nhật BOT_STATUS từ file
        BOT_STATUS.update(get_bot_status_from_config())
        logger.debug(f"Đã cập nhật BOT_STATUS từ file, trạng thái bot: {BOT_STATUS.get('running', False)}")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật BOT_STATUS: {str(e)}")
    
    # TODO: Cập nhật dữ liệu thị trường khác nếu cần


def update_account_data():
    """Cập nhật dữ liệu tài khoản theo định kỳ"""
    global BOT_STATUS
    try:
        # Cập nhật BOT_STATUS từ file
        BOT_STATUS.update(get_bot_status_from_config())
        logger.debug(f"Đã cập nhật BOT_STATUS từ file, số dư: {BOT_STATUS.get('balance', 0)} USDT")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật BOT_STATUS: {str(e)}")
    
    # TODO: Cập nhật dữ liệu tài khoản khác nếu cần


# Khởi động tác vụ nền và đăng ký blueprint
logger.info("Đã đăng ký blueprint cho cấu hình")

# Thiết lập tác vụ nền để cập nhật trạng thái
def background_tasks():
    """Chạy các tác vụ nền theo định kỳ"""
    logger.info("Bắt đầu các tác vụ nền để cập nhật dữ liệu")
    
    # Cập nhật dữ liệu thị trường mỗi 10 giây
    try:
        update_market_data()
        global market_task
        from threading import Timer
        market_task = Timer(10.0, background_tasks)
        market_task.daemon = True
        market_task.start()
        logger.debug("Đã lên lịch tác vụ nền tiếp theo trong 10 giây")
    except Exception as e:
        logger.error(f"Lỗi trong tác vụ nền: {str(e)}")

# Kiểm tra môi trường
if os.environ.get('TESTING') == 'true':
    logger.info("Auto-start bot is disabled in testing environment")
else:
    # Khởi động tác vụ nền
    import threading
    market_task = None
    
    try:
        background_tasks()
        logger.info("Đã khởi động tác vụ nền để cập nhật dữ liệu")
    except Exception as e:
        logger.error(f"Lỗi khi khởi động tác vụ nền: {str(e)}")

logger.info("Background tasks started")

# Trong trường hợp bot đang chạy nhưng trạng thái không đồng bộ
if BOT_STATUS['running'] == False and os.path.exists('bot_status.json'):
    try:
        with open('bot_status.json', 'r') as f:
            saved_status = json.load(f)
            if saved_status.get('running', False):
                logger.info("Phát hiện trạng thái bot không khớp. Cập nhật BOT_STATUS...")
                BOT_STATUS.update(saved_status)
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra trạng thái bot: {str(e)}")


# Đăng ký updates route blueprint
def register_update_routes():
    try:
        from routes import update_route
        update_route.register_blueprint(app)
        logger.info("Đã đăng ký blueprint update_route")
    except Exception as e:
        logger.error(f"Lỗi khi đăng ký update_route: {e}")

# Đăng ký các blueprints
register_update_routes()

# Tạo các thư mục cần thiết cho hệ thống cập nhật
os.makedirs("update_packages", exist_ok=True)
os.makedirs("backups", exist_ok=True)


if __name__ == '__main__':
    # Đảm bảo threading daemon được dừng khi nhấn Ctrl+C
    import atexit
    
    def cleanup():
        """Hàm dọn dẹp khi ứng dụng dừng"""
        global market_task
        if market_task:
            logger.info("Dừng tác vụ nền...")
            market_task.cancel()
    
    atexit.register(cleanup)
    
    # Khởi động ứng dụng Flask
    app.run(host='0.0.0.0', port=5000, debug=True)