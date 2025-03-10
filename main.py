import os

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Routes
@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html', title="Hệ Thống Bot Giao Dịch")

@app.route('/dashboard')
def dashboard():
    """Trang dashboard"""
    return render_template('dashboard.html', title="Dashboard")

@app.route('/api/status')
def status():
    """API endpoint cho trạng thái hệ thống"""
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "uptime": "12h 30m",
        "system_info": {
            "python_version": "3.11.2",
            "platform": "Linux"
        }
    })

@app.route('/api/risk-levels')
def risk_levels():
    """API endpoint cho các mức rủi ro"""
    risk_levels = [
        {"name": "10%", "description": "Rủi ro thấp, an toàn cho người mới bắt đầu"},
        {"name": "15%", "description": "Rủi ro vừa phải, cân bằng giữa rủi ro và lợi nhuận"},
        {"name": "20%", "description": "Rủi ro trung bình cao, cho trader có kinh nghiệm"},
        {"name": "30%", "description": "Rủi ro cao, chỉ dành cho trader chuyên nghiệp"}
    ]
    return jsonify(risk_levels)

@app.route('/api/change-risk', methods=['POST'])
def change_risk():
    """API endpoint để thay đổi mức rủi ro"""
    risk_level = request.json.get('risk_level')
    if risk_level in ['10', '15', '20', '30']:
        try:
            from risk_level_manager import RiskLevelManager
            risk_manager = RiskLevelManager()
            success = risk_manager.apply_risk_config(risk_level)
            
            if success:
                return jsonify({"success": True, "message": f"Đã thay đổi mức rủi ro sang {risk_level}%"})
            else:
                return jsonify({"success": False, "message": "Lỗi khi thay đổi mức rủi ro"}), 500
                
        except Exception as e:
            return jsonify({"success": False, "message": f"Lỗi: {str(e)}"}), 500
    else:
        return jsonify({"success": False, "message": "Mức rủi ro không hợp lệ"}), 400

@app.route('/api/update-bot', methods=['POST'])
def update_bot():
    """API endpoint để cập nhật bot"""
    try:
        from update_packages.update_bot import BotUpdater
        updater = BotUpdater()
        success = updater.update()
        
        if success:
            return jsonify({"success": True, "message": "Bot đã được cập nhật thành công"})
        else:
            return jsonify({"success": False, "message": "Không có cập nhật mới hoặc cập nhật thất bại"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi khi cập nhật bot: {str(e)}"}), 500

# Khởi tạo cơ sở dữ liệu
with app.app_context():
    # Make sure to import the models here or their tables won't be created
    from models import User  # Import the models
    
    # Tạo bảng nếu chưa tồn tại
    db.create_all()
    
    # Khởi tạo thư mục templates nếu chưa tồn tại
    os.makedirs('templates', exist_ok=True)
    
    # Tạo template index.html mặc định nếu chưa tồn tại
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #f0f2f5;
            color: #333;
        }
        .container {
            max-width: 800px;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        h1 {
            color: #1877f2;
        }
        .btn {
            display: inline-block;
            background-color: #1877f2;
            color: white;
            padding: 10px 20px;
            margin: 10px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
        }
        .info {
            margin: 20px 0;
            padding: 15px;
            background-color: #e7f3ff;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hệ Thống Bot Giao Dịch</h1>
        <div class="info">
            <p>Chào mừng đến với hệ thống bot giao dịch tiền điện tử!</p>
            <p>Sử dụng ứng dụng desktop để quản lý bot của bạn.</p>
        </div>
        <a href="/dashboard" class="btn">Dashboard</a>
        <a href="#" class="btn" onclick="checkStatus()">Kiểm Tra Trạng Thái</a>
        
        <div id="status-output" style="margin-top: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; display: none;"></div>
    </div>
    
    <script>
        function checkStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const statusOutput = document.getElementById('status-output');
                    statusOutput.innerHTML = `
                        <h3>Trạng Thái Hệ Thống</h3>
                        <p><strong>Trạng thái:</strong> ${data.status}</p>
                        <p><strong>Phiên bản:</strong> ${data.version}</p>
                        <p><strong>Thời gian hoạt động:</strong> ${data.uptime}</p>
                    `;
                    statusOutput.style.display = 'block';
                })
                .catch(error => {
                    console.error('Lỗi:', error);
                    alert('Không thể kết nối đến server!');
                });
        }
    </script>
</body>
</html>
            """)
    
    # Tạo template dashboard.html mặc định nếu chưa tồn tại
    if not os.path.exists('templates/dashboard.html'):
        with open('templates/dashboard.html', 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
            background-color: #f0f2f5;
            color: #333;
        }
        .header {
            background-color: #1877f2;
            color: white;
            padding: 15px;
            text-align: center;
        }
        .container {
            flex: 1;
            display: flex;
            padding: 20px;
        }
        .sidebar {
            width: 250px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 15px;
            margin-right: 20px;
        }
        .main-content {
            flex: 1;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 20px;
        }
        .menu-item {
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            cursor: pointer;
        }
        .menu-item:hover {
            background-color: #f0f2f5;
        }
        .menu-item.active {
            background-color: #e7f3ff;
            color: #1877f2;
            font-weight: bold;
        }
        .risk-selector {
            margin: 20px 0;
            padding: 15px;
            background-color: #e7f3ff;
            border-radius: 5px;
        }
        .btn {
            display: inline-block;
            background-color: #1877f2;
            color: white;
            padding: 10px 20px;
            margin: 10px 5px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #166fe5;
        }
        .footer {
            background-color: #1877f2;
            color: white;
            text-align: center;
            padding: 10px;
            margin-top: 20px;
        }
        .dashboard-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            flex: 1;
            min-width: 200px;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .stat-card h3 {
            margin-top: 0;
            color: #1877f2;
        }
        .stat-card .value {
            font-size: 24px;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Bot Giao Dịch</h1>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="menu-item active" onclick="showTab('dashboard')">Dashboard</div>
            <div class="menu-item" onclick="showTab('settings')">Cài Đặt</div>
            <div class="menu-item" onclick="showTab('risk-management')">Quản Lý Rủi Ro</div>
            <div class="menu-item" onclick="showTab('strategies')">Chiến Lược</div>
            <div class="menu-item" onclick="showTab('logs')">Logs</div>
            
            <div class="risk-selector">
                <h3>Mức Rủi Ro</h3>
                <select id="risk-level" onchange="changeRiskLevel()">
                    <option value="10">10% - Thấp</option>
                    <option value="15">15% - Vừa phải</option>
                    <option value="20">20% - Trung bình cao</option>
                    <option value="30">30% - Cao</option>
                </select>
                <div id="risk-status" style="margin-top: 10px; font-size: 14px;"></div>
            </div>
            
            <button class="btn" onclick="updateBot()">Cập Nhật Bot</button>
            <a href="/" class="btn" style="display: block; text-align: center;">Trang Chủ</a>
        </div>
        
        <div class="main-content">
            <div id="dashboard" class="tab-content active">
                <h2>Thống Kê Tổng Quan</h2>
                
                <div class="dashboard-stats">
                    <div class="stat-card">
                        <h3>Số Dư</h3>
                        <div class="value">$10,000</div>
                    </div>
                    <div class="stat-card">
                        <h3>P/L Hôm Nay</h3>
                        <div class="value" style="color: green;">+$250</div>
                    </div>
                    <div class="stat-card">
                        <h3>Vị Thế Hiện Tại</h3>
                        <div class="value">3</div>
                    </div>
                </div>
                
                <h2>Vị Thế Giao Dịch</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f0f2f5;">
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Symbol</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Side</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Entry Price</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Current Price</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">P/L</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">BTC/USDT</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">LONG</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">$60,000</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">$61,200</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd; color: green;">+2.0%</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">ETH/USDT</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">SHORT</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">$2,200</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">$2,150</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd; color: green;">+2.3%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div id="settings" class="tab-content">
                <h2>Cài Đặt</h2>
                <p>Cài đặt hệ thống sẽ được hiển thị ở đây.</p>
                
                <form id="settings-form">
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">API Key:</label>
                        <input type="password" id="api-key" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">API Secret:</label>
                        <input type="password" id="api-secret" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Chế Độ API:</label>
                        <select id="api-mode" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <option value="testnet">Testnet</option>
                            <option value="live">Live</option>
                        </select>
                    </div>
                    
                    <button type="button" class="btn" onclick="saveSettings()">Lưu Cài Đặt</button>
                </form>
            </div>
            
            <div id="risk-management" class="tab-content">
                <h2>Quản Lý Rủi Ro</h2>
                
                <div style="margin-bottom: 20px;">
                    <h3>Mức Rủi Ro Hiện Tại: <span id="current-risk-level">10%</span></h3>
                    <p>Điều chỉnh các tham số rủi ro cho chiến lược của bạn.</p>
                </div>
                
                <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 300px;">
                        <h3>Tham Số Rủi Ro</h3>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Kích Thước Vị Thế Tối Đa (%):</label>
                            <input type="number" id="max-position-size" value="2.0" min="0.1" max="10" step="0.1" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Stop Loss (%):</label>
                            <input type="number" id="stop-loss" value="1.0" min="0.1" max="10" step="0.1" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Take Profit (%):</label>
                            <input type="number" id="take-profit" value="3.0" min="0.1" max="20" step="0.1" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 300px;">
                        <h3>Đòn Bẩy & Bảo Vệ</h3>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Đòn Bẩy:</label>
                            <select id="leverage" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                                <option value="1">1x</option>
                                <option value="3">3x</option>
                                <option value="5" selected>5x</option>
                                <option value="10">10x</option>
                                <option value="20">20x</option>
                            </select>
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Thua Lỗ Tối Đa Mỗi Ngày (%):</label>
                            <input type="number" id="max-daily-loss" value="5.0" min="1" max="20" step="0.5" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label><input type="checkbox" id="use-trailing-stop"> Sử Dụng Trailing Stop</label>
                        </div>
                    </div>
                </div>
                
                <button type="button" class="btn" onclick="saveRiskSettings()">Lưu Thiết Lập Rủi Ro</button>
            </div>
            
            <div id="strategies" class="tab-content">
                <h2>Chiến Lược Giao Dịch</h2>
                
                <div style="margin-bottom: 20px;">
                    <h3>Chiến Lược Hiện Tại</h3>
                    <select id="active-strategy" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;">
                        <option value="low_risk_strategy">Low Risk Strategy</option>
                        <option value="medium_risk_strategy">Medium Risk Strategy</option>
                        <option value="high_risk_strategy">High Risk Strategy</option>
                        <option value="trending_strategy">Trending Strategy</option>
                        <option value="ranging_strategy">Ranging Strategy</option>
                        <option value="adaptive_strategy">Adaptive Strategy</option>
                        <option value="ml_integrated_strategy">ML Integrated Strategy</option>
                    </select>
                    
                    <button type="button" class="btn" onclick="activateStrategy()">Kích Hoạt Chiến Lược</button>
                </div>
                
                <div style="margin-top: 30px;">
                    <h3>Tham Số Chiến Lược</h3>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Activation Threshold:</label>
                        <input type="number" id="activation-threshold" value="80" min="0" max="100" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Callback Rate:</label>
                        <input type="number" id="callback-rate" value="20" min="0" max="100" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px;">Trend Confirmation Periods:</label>
                        <input type="number" id="trend-confirmation" value="3" min="1" max="10" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    </div>
                    
                    <button type="button" class="btn" onclick="saveStrategySettings()">Lưu Tham Số</button>
                </div>
            </div>
            
            <div id="logs" class="tab-content">
                <h2>Logs</h2>
                
                <div style="margin-bottom: 15px;">
                    <select id="log-filter" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-right: 10px;">
                        <option value="all">Tất Cả Logs</option>
                        <option value="trades">Logs Giao Dịch</option>
                        <option value="errors">Logs Lỗi</option>
                        <option value="system">Logs Hệ Thống</option>
                    </select>
                    
                    <button type="button" class="btn" onclick="refreshLogs()">Làm Mới</button>
                </div>
                
                <div id="log-container" style="background-color: #f0f2f5; border-radius: 5px; padding: 15px; height: 400px; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">
                    [2025-03-10 02:14:44] INFO: Khởi động hệ thống bot giao dịch
                    [2025-03-10 02:14:47] INFO: Đã tải cấu hình tài khoản từ account_config.json
                    [2025-03-10 02:14:47] INFO: Kết nối đến môi trường TESTNET Binance
                    [2025-03-10 02:14:48] INFO: Đã lấy thông tin vị thế từ account API
                    [2025-03-10 02:14:48] INFO: Đã lấy dữ liệu thị trường từ API: BTCUSDT=81627.10, ETHUSDT=2046.49...
                </div>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>Trading Bot System &copy; 2025</p>
    </div>
    
    <script>
        function showTab(tabId) {
            // Ẩn tất cả tab
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Hiển thị tab được chọn
            document.getElementById(tabId).classList.add('active');
            
            // Cập nhật menu
            document.querySelectorAll('.menu-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Highlight menu item
            event.target.classList.add('active');
        }
        
        function changeRiskLevel() {
            const riskLevel = document.getElementById('risk-level').value;
            const riskStatus = document.getElementById('risk-status');
            
            riskStatus.textContent = 'Đang cập nhật...';
            
            fetch('/api/change-risk', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ risk_level: riskLevel }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    riskStatus.textContent = data.message;
                    riskStatus.style.color = 'green';
                    
                    // Cập nhật hiển thị mức rủi ro hiện tại
                    document.getElementById('current-risk-level').textContent = riskLevel + '%';
                } else {
                    riskStatus.textContent = data.message;
                    riskStatus.style.color = 'red';
                }
            })
            .catch(error => {
                console.error('Lỗi:', error);
                riskStatus.textContent = 'Lỗi khi thay đổi mức rủi ro!';
                riskStatus.style.color = 'red';
            });
        }
        
        function updateBot() {
            if (confirm('Bạn có chắc muốn cập nhật bot?')) {
                fetch('/api/update-bot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                    } else {
                        alert('Lỗi: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Lỗi:', error);
                    alert('Lỗi khi cập nhật bot!');
                });
            }
        }
        
        function saveSettings() {
            alert('Đã lưu cài đặt!');
        }
        
        function saveRiskSettings() {
            alert('Đã lưu thiết lập rủi ro!');
        }
        
        function activateStrategy() {
            const strategy = document.getElementById('active-strategy').value;
            alert('Đã kích hoạt chiến lược: ' + strategy);
        }
        
        function saveStrategySettings() {
            alert('Đã lưu tham số chiến lược!');
        }
        
        function refreshLogs() {
            const filter = document.getElementById('log-filter').value;
            console.log('Đang lọc logs với filter:', filter);
            // Tại đây sẽ gọi API để lấy logs theo filter
        }
    </script>
</body>
</html>
            """)

if __name__ == "__main__":
    # Để chạy ứng dụng trong development
    app.run(host="0.0.0.0", port=5000, debug=True)