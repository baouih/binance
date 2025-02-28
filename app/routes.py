from flask import render_template

def register_routes(app):
    """
    Đăng ký các tuyến đường bổ sung cho ứng dụng.
    """
    # Ghi đè route chính để sử dụng trang đơn giản
    @app.route('/')
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
    
    @app.route('/basic')
    def basic_page():
        """Trang cơ bản không có Socket.IO."""
        return render_template('basic.html')
        
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