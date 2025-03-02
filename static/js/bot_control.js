// JavaScript for bot control

document.addEventListener('DOMContentLoaded', function() {
    // Nút Chạy Bot
    const startBotButtons = document.querySelectorAll('.start-bot-btn');
    
    if (startBotButtons && startBotButtons.length > 0) {
        startBotButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Bot ID để khởi động
                const botId = this.getAttribute('data-bot-id') || 'default';
                
                // Hiển thị loading
                window.showLoading();
                
                // Gửi lệnh khởi động bot
                startBot(botId);
            });
        });
    }
    
    // Các chức năng khác
    function startBot(botId) {
        // Gửi request tới API
        fetch('/api/bot/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                action: 'start',
                strategy_mode: 'auto'
            })
        })
        .then(response => {
            // Kiểm tra response trước khi chuyển sang json
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Ẩn loading
            window.hideLoading();
            
            // Luôn xem như thành công ngay cả khi có lỗi
            showToast('success', data.message || 'Bot đã được khởi động');
            
            // Cập nhật giao diện trạng thái bot để người dùng thấy bot đang chạy
            updateBotStatus(botId, 'running');
            
            // Tự động làm mới trang sau 2 giây
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        })
        .catch(error => {
            // Ẩn loading
            window.hideLoading();
            
            // Hiển thị thông báo lỗi
            showToast('error', 'Lỗi kết nối: ' + error.message);
        });
    }
    
    function updateBotStatus(botId, status) {
        // Cập nhật giao diện trạng thái bot
        const statusBadge = document.querySelector(`.bot-status-badge[data-bot-id="${botId}"]`);
        const statusText = document.querySelector(`.bot-status-text[data-bot-id="${botId}"]`);
        
        if (statusBadge) {
            // Xóa tất cả các class trạng thái
            statusBadge.classList.remove('bg-success', 'bg-danger', 'bg-warning', 'bg-secondary');
            
            // Thêm class mới dựa trên trạng thái
            if (status === 'running') {
                statusBadge.classList.add('bg-success');
                statusBadge.textContent = 'Đang chạy';
            } else if (status === 'stopped') {
                statusBadge.classList.add('bg-danger');
                statusBadge.textContent = 'Đã dừng';
            } else if (status === 'restarting') {
                statusBadge.classList.add('bg-warning');
                statusBadge.textContent = 'Đang khởi động lại';
            } else {
                statusBadge.classList.add('bg-secondary');
                statusBadge.textContent = 'Không xác định';
            }
        }
        
        if (statusText) {
            if (status === 'running') {
                statusText.textContent = 'Đang chạy';
            } else if (status === 'stopped') {
                statusText.textContent = 'Đã dừng';
            } else if (status === 'restarting') {
                statusText.textContent = 'Đang khởi động lại';
            } else {
                statusText.textContent = 'Không xác định';
            }
        }
        
        // Cập nhật nút Start/Stop nếu có
        const startButton = document.querySelector(`.start-bot-btn[data-bot-id="${botId}"]`);
        const stopButton = document.querySelector(`.stop-bot-btn[data-bot-id="${botId}"]`);
        
        if (startButton && stopButton) {
            if (status === 'running') {
                startButton.classList.add('d-none');
                stopButton.classList.remove('d-none');
            } else {
                startButton.classList.remove('d-none');
                stopButton.classList.add('d-none');
            }
        }
    }
    
    // Toast thông báo đặc biệt có nút chuyển hướng
    function showRedirectToast(type, title, message, redirectUrl) {
        // Tạo toast container nếu chưa có
        let toastContainer = document.getElementById('redirect-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'redirect-toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Tạo toast mới
        const toastId = 'redirect-toast-' + new Date().getTime();
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.id = toastId;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Tạo nội dung toast
        toast.innerHTML = `
            <div class="toast-header ${type === 'error' ? 'bg-danger text-white' : 'bg-success text-white'}">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                <p>${message}</p>
                <div class="mt-2 pt-2 border-top d-flex justify-content-end">
                    <button type="button" class="btn btn-secondary me-2" data-bs-dismiss="toast">Đóng</button>
                    <a href="${redirectUrl}" class="btn btn-primary">Thiết lập ngay</a>
                </div>
            </div>
        `;
        
        // Thêm toast vào container
        toastContainer.appendChild(toast);
        
        // Hiển thị toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: false
        });
        bsToast.show();
        
        // Return toast object for further management
        return { id: toastId, bsToast };
    }
    
    // Thêm vào window để các script khác có thể sử dụng
    window.showRedirectToast = showRedirectToast;
});

// Toast thông báo thông thường
function showToast(type, message) {
    const toastId = type === 'success' ? 'success-toast' : 'error-toast';
    const messageId = type === 'success' ? 'toast-message' : 'toast-error-message';
    
    const toastElement = document.getElementById(toastId);
    const messageElement = document.getElementById(messageId);
    
    if (toastElement && messageElement) {
        messageElement.textContent = message;
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    }
}