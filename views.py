from flask import render_template, request, redirect, url_for, flash, jsonify
from database.models import User, TradingPosition, TradingStrategy, TradingHistory

def register_routes(app):
    """Register all routes to the Flask app"""
    
    @app.route('/')
    def index():
        """Home page"""
        bot_status = {
            'running': True,
            'mode': 'testnet',
            'api_connected': True,
            'last_update': '2025-03-10 03:55:00',
            'active_strategy': 'RSI Strategy',
            'strategy_mode': 'auto',
            'balance': 10000.00
        }
        
        account_data = {
            'balance': 10000.00,
            'change_24h': 2.5,
            'change_7d': 5.8,
            'total_profit': 580.25,
            'total_profit_percent': 5.8,
            'positions': [],
            'unrealized_pnl': 120.50
        }
        
        market_data = {
            'btc_price': 65000.00,
            'btc_change_24h': 1.2,
            'eth_price': 3500.00,
            'eth_change_24h': -0.8,
            'market_mode': 'Uptrend',
            'market_strength': 72,
            'volatility_level': 'Medium',
            'volatility_value': 45
        }
        
        strategy_stats = {
            'win_rate': 62.5
        }
        
        # Dữ liệu giá mẫu để sử dụng trong template
        fake_prices = {
            'BTCUSDT': 65000.00,
            'ETHUSDT': 3500.00,
            'SOLUSDT': 145.25,
            'AVAXUSDT': 42.50,
            'DOGEUSDT': 0.12
        }
        
        signals = [
            {'symbol': 'BTCUSDT', 'signal': 'buy', 'time': '14:25'},
            {'symbol': 'ETHUSDT', 'signal': 'sell', 'time': '14:15'},
            {'symbol': 'SOLUSDT', 'signal': 'neutral', 'time': '14:10'}
        ]
        
        # Dữ liệu hiệu suất tổng thể để hiển thị trong báo cáo
        performance_stats = {
            'total_trades': 24,
            'win_trades': 16,
            'loss_trades': 8,
            'win_rate': 66.7,
            'average_profit': 3.2,
            'average_loss': 1.8,
            'profit_factor': 2.84,
            'total_pnl': 982.50,
            'best_trade': 250.75,
            'worst_trade': -125.30,
            'max_drawdown': 8.5,
            'max_drawdown_value': 850.00,
            'recovery_factor': 2.1,
            'sharpe_ratio': 1.85,
            'sortino_ratio': 2.34,
            'average_trade_duration': '4h 35m'
        }
        
        # Danh sách theo dõi các cặp tiền tệ
        watchlist = {
            'BTCUSDT': {
                'price': 65000.00,
                'change_24h': 1.2,
                'volume': '2.3B',
                'trend': 'up',
                'signal': 'buy',
                'strength': 85
            },
            'ETHUSDT': {
                'price': 3500.00,
                'change_24h': -0.8,
                'volume': '1.5B',
                'trend': 'down',
                'signal': 'sell',
                'strength': 65
            },
            'SOLUSDT': {
                'price': 145.25,
                'change_24h': 3.5,
                'volume': '850M',
                'trend': 'up',
                'signal': 'buy',
                'strength': 78
            },
            'AVAXUSDT': {
                'price': 42.50,
                'change_24h': 0.3,
                'volume': '320M',
                'trend': 'neutral',
                'signal': 'neutral',
                'strength': 52
            },
            'DOGEUSDT': {
                'price': 0.12,
                'change_24h': 5.8,
                'volume': '950M',
                'trend': 'up',
                'signal': 'buy',
                'strength': 88
            }
        }
        
        # Thống kê giao dịch chi tiết
        trade_stats = {
            'avg_trade_time': '5h 23m',
            'time_in_market': '68%',
            'longest_trade': '3d 4h',
            'shortest_trade': '35m',
            'most_traded_pair': 'BTCUSDT',
            'best_performing_pair': 'SOLUSDT',
            'worst_performing_pair': 'ETHUSDT',
            'largest_win': '$325.75',
            'largest_loss': '$178.24',
            'avg_win_size': '$120.35',
            'avg_loss_size': '$65.48',
            'win_loss_ratio': '1.84',
            'trade_frequency': '4.2/day'
        }

        return render_template('index.html', 
                             title="Hệ Thống Bot Giao Dịch",
                             bot_status=bot_status,
                             account_data=account_data,
                             market_data=market_data,
                             strategy_stats=strategy_stats,
                             fake_prices=fake_prices,
                             signals=signals,
                             performance_stats=performance_stats,
                             watchlist=watchlist,
                             trade_stats=trade_stats)

    @app.route('/dashboard')
    def dashboard():
        """Dashboard page"""
        return render_template('dashboard.html', title="Dashboard")

    @app.route('/api/status')
    def status():
        """API endpoint for system status"""
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
        """API endpoint for risk levels"""
        risk_levels = [
            {"name": "10%", "description": "Rủi ro thấp, an toàn cho người mới bắt đầu"},
            {"name": "15%", "description": "Rủi ro vừa phải, cân bằng giữa rủi ro và lợi nhuận"},
            {"name": "20%", "description": "Rủi ro trung bình cao, cho trader có kinh nghiệm"},
            {"name": "30%", "description": "Rủi ro cao, chỉ dành cho trader chuyên nghiệp"}
        ]
        return jsonify(risk_levels)

    @app.route('/api/change-risk', methods=['POST'])
    def change_risk():
        """API endpoint to change risk level"""
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
        """API endpoint to update bot"""
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