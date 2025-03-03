/**
 * Bot Control Module
 * Module Javascript để điều khiển bot giao dịch thông qua REST API
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Bot Control Module initialized');
    
    // Tìm tất cả các nút khởi động bot
    const startBotButtons = document.querySelectorAll('.start-bot-btn');
    // Tìm tất cả các nút dừng bot
    const stopBotButtons = document.querySelectorAll('.stop-bot-btn');
    // Tìm nút khởi động lại bot
    const restartBotButtons = document.querySelectorAll('#restartBotBtn');
    
    // Thêm sự kiện cho các nút khởi động bot
    startBotButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const botId = this.getAttribute('data-bot-id') || 'default';
            controlBot('start', botId);
        });
    });
    
    // Thêm sự kiện cho các nút dừng bot
    stopBotButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const botId = this.getAttribute('data-bot-id') || 'default';
            controlBot('stop', botId);
        });
    });
    
    // Thêm sự kiện cho các nút khởi động lại bot
    restartBotButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const botId = this.getAttribute('data-bot-id') || 'default';
            controlBot('restart', botId);
        });
    });
    
    // Thêm sự kiện cho nút trên mobile
    const mobileBotToggle = document.getElementById('mobileBotToggle');
    if (mobileBotToggle) {
        mobileBotToggle.addEventListener('click', function(e) {
            e.preventDefault();
            // Kiểm tra nút đang là start hay stop dựa vào lớp CSS
            const action = this.classList.contains('btn-success') ? 'start' : 'stop';
            const botId = this.getAttribute('data-bot-id') || 'default';
            controlBot(action, botId);
        });
    }
});

/**
 * Điều khiển bot thông qua API
 * @param {string} action - Hành động: 'start', 'stop', 'restart'
 * @param {string} botId - ID của bot cần điều khiển
 */
function controlBot(action, botId = 'default') {
    console.log(`Đang thực hiện: ${action} cho bot ${botId}`);
    
    // Hiển thị loading indicator
    document.getElementById('loading-overlay').classList.remove('d-none');
    
    // Gửi request tới API
    fetch('/api/bot/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: action,
            bot_id: botId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Ẩn loading indicator
        document.getElementById('loading-overlay').classList.add('d-none');
        
        if (data.success) {
            console.log('Success:', data);
            showToast('success', data.message || `Bot ${botId} đã ${action === 'start' ? 'khởi động' : action === 'stop' ? 'dừng' : 'khởi động lại'} thành công`);
            
            // Tải lại trang sau 1 giây để cập nhật trạng thái
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            console.error('Error:', data);
            
            // Xử lý các lỗi khác nhau
            if (data.error_type === 'missing_api_config') {
                // Đối với lỗi thiếu cấu hình API
                handleMissingApiConfig();
            } else {
                // Hiển thị lỗi thông thường
                showToast('error', data.message || 'Không thể điều khiển bot');
            }
        }
    })
    .catch(error => {
        // Ẩn loading indicator
        document.getElementById('loading-overlay').classList.add('d-none');
        console.error('Error:', error);
        showToast('error', `Lỗi kết nối: ${error.message}`);
    });
}

/**
 * Hiển thị thông báo toast
 * @param {string} type - Loại thông báo: 'success', 'error'
 * @param {string} message - Nội dung thông báo
 */
function showToast(type, message) {
    // Xác định toast element
    const toastId = type === 'success' ? 'success-toast' : 'error-toast';
    const toastElement = document.getElementById(toastId);
    
    if (!toastElement) {
        console.error(`Toast element with id ${toastId} not found`);
        return;
    }
    
    // Cập nhật nội dung
    const messageElement = toastElement.querySelector('.toast-body');
    if (messageElement) {
        messageElement.textContent = message;
    }
    
    // Hiển thị toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

/**
 * Xử lý trường hợp thiếu cấu hình API
 */
function handleMissingApiConfig() {
    // Kiểm tra xem người dùng đang ở thiết bị di động không
    const isMobileDevice = window.innerWidth < 768;
    
    if (isMobileDevice) {
        // Trên mobile, chuyển hướng trực tiếp đến trang settings
        window.location.href = '/settings';
        return;
    }
    
    // Trên desktop, hiển thị modal thông báo
    const modalId = 'apiConfigMissingModal';
    
    // Kiểm tra và xóa modal cũ nếu tồn tại
    let oldModal = document.getElementById(modalId);
    if (oldModal) {
        oldModal.remove();
    }
    
    // Tạo modal mới
    const modalHTML = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content bg-dark">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title"><i class="bi bi-exclamation-triangle me-2"></i>Cần cấu hình API</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p>Bạn cần cấu hình API Key Binance trước khi có thể chạy bot trong chế độ này.</p>
                        <ol class="mt-3">
                            <li>Truy cập trang cài đặt API</li>
                            <li>Nhập API Key và API Secret</li> 
                            <li>Lưu cài đặt và thử lại</li>
                        </ol>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>
                        <a href="/settings" class="btn btn-primary">Đi đến cài đặt API</a>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Thêm modal vào body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Hiển thị modal
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}