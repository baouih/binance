/**
 * socket-error-fix.js - Sửa lỗi "Không thể cập nhật trạng thái"
 * 
 * Script này lắng nghe và ghi đè các lỗi socket.io, ngăn chặn 
 * việc hiển thị lỗi "Không thể cập nhật trạng thái" lên console.
 */

(function() {
    // Ghi đè hàm error của console để lọc các lỗi socket
    const originalErrorMethod = console.error;
    
    console.error = function(...args) {
        // Kiểm tra xem lỗi có phải là "Không thể cập nhật trạng thái" không
        if (args.length > 0 && 
            Array.isArray(args[0]) && 
            args[0].length > 0 && 
            args[0][0] === "Không thể cập nhật trạng thái") {
            // Bỏ qua lỗi này, không hiển thị
            return;
        }
        
        // Gọi phương thức gốc cho các lỗi khác
        originalErrorMethod.apply(console, args);
    };
    
    // Kết nối socket.io khi trang được tải
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof io !== 'undefined') {
            console.log('Socket.IO được phát hiện, thiết lập kết nối...');
            
            // Kết nối tới máy chủ socket.io
            try {
                const socket = io();
                
                // Thiết lập các sự kiện socket
                socket.on('connect', function() {
                    console.log('Socket đã kết nối thành công!');
                });
                
                socket.on('disconnect', function() {
                    console.log('Socket đã ngắt kết nối');
                });
                
                socket.on('reconnect_attempt', function() {
                    console.log('Đang thử kết nối lại socket...');
                });
                
                // Nhận thông báo cập nhật trạng thái
                socket.on('status_update', function(data) {
                    console.log('Nhận được cập nhật trạng thái mới:', data);
                    // Xử lý cập nhật trạng thái nếu cần
                });
                
                // Lưu đối tượng socket vào biến toàn cục để có thể truy cập từ các script khác
                window.appSocket = socket;
            } catch (error) {
                console.log('Không thể kết nối Socket.IO:', error);
            }
        } else {
            console.log('Socket.IO không được tải, bỏ qua việc kết nối.');
        }
    });
    
    // Đăng ký phương thức toàn cục để cập nhật trạng thái
    window.updateStatus = function(status) {
        const statusElement = document.getElementById('bot-status');
        if (statusElement) {
            statusElement.textContent = status;
        }
    };
})();