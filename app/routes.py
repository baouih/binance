from flask import render_template

def register_routes(app):
    """
    Đăng ký các tuyến đường bổ sung cho ứng dụng.
    """
    # Trang dashboard mới
    @app.route('/dashboard')
    def dashboard():
        """Trang dashboard chính với biểu đồ thời gian thực."""
        return render_template('dashboard.html')
    
    # Trang đơn giản
    @app.route('/basic')
    def basic_page():
        """Trang cơ bản không có Socket.IO."""
        return render_template('basic.html')
    
    # Trang chính đơn giản (giữ lại cho tương thích)
    @app.route('/index_basic')
    def index_basic():
        """Trang chính đơn giản."""
        return render_template('index_basic.html')
    
    @app.route('/test')
    def test_page():
        """Trang kiểm tra đầy đủ."""
        return render_template('test.html')
    
    @app.route('/minimal')
    def minimal_test():
        """Trang kiểm tra tối giản."""
        return render_template('minimal_test.html')
    
    @app.route('/status')
    def status_page():
        """Trang trạng thái hệ thống."""
        return render_template('status.html')
    
    @app.route('/simple')
    def simple_page():
        """Trang siêu đơn giản."""
        return render_template('simple.html')
        
    # API trả về giá Bitcoin hiện tại (thay vì Socket.IO)
    @app.route('/api/price', methods=['GET'])
    def get_price():
        """API lấy giá Bitcoin hiện tại."""
        from flask import jsonify
        import requests
        
        try:
            # Gọi API Binance
            response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
            if response.status_code == 200:
                data = response.json()
                price = float(data['price'])
                return jsonify({
                    'status': 'success',
                    'symbol': 'BTCUSDT',
                    'price': price,
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Binance API error: {response.status_code}'
                }), 500
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }), 500
            
    # API đơn giản cho kiểm tra
    @app.route('/api/test', methods=['GET'])
    def api_test():
        """API kiểm tra."""
        from flask import jsonify
        from datetime import datetime
        return jsonify({
            'status': 'success',
            'message': 'API hoạt động bình thường',
            'time': str(datetime.now())
        })