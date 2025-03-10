import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import db

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "trading_bot_secret_key")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///trading_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import views after app is created to avoid circular imports
from views import register_routes
register_routes(app)

# Initialize app context and database
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    from database.models import User, TradingPosition, TradingStrategy, TradingHistory
    
    # Create tables if they don't exist
    db.create_all()
    
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create default templates if they don't exist
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
    
    # Create dashboard.html if it doesn't exist
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
                            <input type="number" id="take-profit" value="3.0" min="0.5" max="20" step="0.5" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                    </div>
                    
                    <div style="flex: 1; min-width: 300px;">
                        <h3>Chiến Lược Nâng Cao</h3>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Trailing Stop (%):</label>
                            <input type="number" id="trailing-stop" value="0.5" min="0.1" max="5" step="0.1" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Số Vị Thế Tối Đa:</label>
                            <input type="number" id="max-positions" value="3" min="1" max="10" step="1" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        </div>
                        
                        <div style="margin-bottom: 15px;">
                            <label style="display: block; margin-bottom: 5px;">Dừng Lỗ Thích Nghi:</label>
                            <input type="checkbox" id="adaptive-stop-loss" checked>
                            <span>Tự động điều chỉnh stop loss dựa trên biến động thị trường</span>
                        </div>
                    </div>
                </div>
                
                <button type="button" class="btn" onclick="saveRiskSettings()">Lưu Cài Đặt Rủi Ro</button>
            </div>
            
            <div id="strategies" class="tab-content">
                <h2>Chiến Lược Giao Dịch</h2>
                <p>Danh sách các chiến lược giao dịch có sẵn.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <thead>
                        <tr style="background-color: #f0f2f5;">
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Tên</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Mô Tả</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Trạng Thái</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 1px solid #ddd;">Hành Động</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Đảo Chiều RSI</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Giao dịch khi RSI đảo chiều từ vùng quá mua/quá bán</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd; color: green;">Hoạt Động</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                                <button class="btn" style="padding: 5px 10px; font-size: 12px;">Cấu Hình</button>
                                <button class="btn" style="padding: 5px 10px; font-size: 12px; background-color: #dc3545;">Dừng</button>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Đột Phá Bollinger</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Giao dịch khi giá đột phá dải Bollinger</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd; color: gray;">Không Hoạt Động</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                                <button class="btn" style="padding: 5px 10px; font-size: 12px;">Cấu Hình</button>
                                <button class="btn" style="padding: 5px 10px; font-size: 12px; background-color: #28a745;">Kích Hoạt</button>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">MA Cross</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">Giao dịch khi MA ngắn cắt MA dài</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd; color: gray;">Không Hoạt Động</td>
                            <td style="padding: 10px; border-bottom: 1px solid #ddd;">
                                <button class="btn" style="padding: 5px 10px; font-size: 12px;">Cấu Hình</button>
                                <button class="btn" style="padding: 5px 10px; font-size: 12px; background-color: #28a745;">Kích Hoạt</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
                
                <button class="btn">Thêm Chiến Lược Mới</button>
            </div>
            
            <div id="logs" class="tab-content">
                <h2>Nhật Ký Hệ Thống</h2>
                <div style="height: 400px; overflow-y: auto; background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; padding: 10px; font-family: monospace; font-size: 14px;">
                    <div>[2025-03-10 08:15:23] INFO: Hệ thống khởi động</div>
                    <div>[2025-03-10 08:15:24] INFO: Kết nối thành công đến API Binance</div>
                    <div>[2025-03-10 08:15:25] INFO: Tải thành công cấu hình rủi ro: 10%</div>
                    <div>[2025-03-10 08:30:15] INFO: Phát hiện tín hiệu mua BTC/USDT</div>
                    <div>[2025-03-10 08:30:16] INFO: Mở vị thế LONG BTC/USDT tại $60,000</div>
                    <div>[2025-03-10 08:45:30] INFO: Phát hiện tín hiệu bán ETH/USDT</div>
                    <div>[2025-03-10 08:45:31] INFO: Mở vị thế SHORT ETH/USDT tại $2,200</div>
                    <div>[2025-03-10 09:15:45] INFO: Cập nhật stop loss cho BTC/USDT: $59,400</div>
                    <div>[2025-03-10 09:30:22] INFO: Cập nhật take profit cho ETH/USDT: $2,134</div>
                    <div>[2025-03-10 10:00:00] INFO: Phân tích dữ liệu thị trường hoàn tất</div>
                </div>
                
                <div style="margin-top: 20px;">
                    <label style="display: block; margin-bottom: 5px;">Mức Độ Log:</label>
                    <select id="log-level" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                        <option value="info">INFO</option>
                        <option value="debug">DEBUG</option>
                        <option value="warning">WARNING</option>
                        <option value="error">ERROR</option>
                    </select>
                </div>
                
                <button type="button" class="btn" style="margin-top: 10px;" onclick="clearLogs()">Xóa Logs</button>
                <button type="button" class="btn" style="margin-top: 10px;" onclick="downloadLogs()">Tải Logs</button>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabId) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all menu items
            document.querySelectorAll('.menu-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to selected menu item
            document.querySelector(`.menu-item[onclick="showTab('${tabId}')"]`).classList.add('active');
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
                    document.getElementById('current-risk-level').textContent = riskLevel + '%';
                } else {
                    riskStatus.textContent = 'Lỗi: ' + data.message;
                }
            })
            .catch(error => {
                console.error('Lỗi:', error);
                riskStatus.textContent = 'Lỗi kết nối đến server';
            });
        }
        
        function updateBot() {
            if (confirm('Bạn có chắc chắn muốn cập nhật bot không?')) {
                fetch('/api/update-bot', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
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
                    alert('Lỗi kết nối đến server');
                });
            }
        }
        
        function saveSettings() {
            alert('Đã lưu cài đặt!');
        }
        
        function saveRiskSettings() {
            alert('Đã lưu cài đặt rủi ro!');
        }
        
        function clearLogs() {
            if (confirm('Bạn có chắc chắn muốn xóa tất cả logs không?')) {
                alert('Đã xóa logs!');
            }
        }
        
        function downloadLogs() {
            alert('Đang tải logs...');
        }
    </script>
</body>
</html>
            """)