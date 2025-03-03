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
    
    // Kiểm tra trạng thái bot khi trang tải
    updateBotStatus();
    
    // Cập nhật trạng thái mỗi 15 giây
    setInterval(updateBotStatus, 15000);
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
    
    // Đảm bảo kết nối API trước khi gửi request
    window.checkAPIStatus().then(isConnected => {
        if (!isConnected) {
            document.getElementById('loading-overlay').classList.add('d-none');
            showToast('error', 'Không thể kết nối với API. Vui lòng làm mới trang.');
            return;
        }
        
        // Gửi request tới API
        fetch(`/api/bot/control/${botId}`, {
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
            
            // Cập nhật trạng thái trên giao diện thay vì tải lại trang
            setTimeout(() => {
                updateBotStatusUI(action);
            }, 500);
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
/**
 * Cập nhật trạng thái bot từ server API
 */
function updateBotStatus() {
    // Cập nhật trạng thái bot từ API
    fetch('/api/bot/status')
        .then(response => response.json())
        .then(data => {
            console.log('Bot status checked:', data);
            updateBotStatusUI(null, data);
        })
        .catch(error => {
            console.error('Error checking bot status:', error);
        });
}

/**
 * Cập nhật UI khi trạng thái bot thay đổi
 * @param {string} action - Hành động vừa thực hiện: 'start', 'stop', 'restart'
 * @param {Object} data - Dữ liệu trạng thái từ API (nếu đã có)
 */
function updateBotStatusUI(action, statusData = null) {
    // Nếu không có dữ liệu, lấy từ API
    if (!statusData) {
        fetch('/api/bot/status')
            .then(response => response.json())
            .then(data => {
                console.log('Bot status updated:', data);
                updateBotUIElements(data);
            })
            .catch(error => {
                console.error('Error updating UI:', error);
            });
    } else {
        // Nếu đã có dữ liệu, sử dụng trực tiếp
        updateBotUIElements(statusData);
    }
}

/**
 * Cập nhật các phần tử UI với dữ liệu trạng thái
 * @param {Object} data - Dữ liệu trạng thái từ API
 */
function updateBotUIElements(data) {
    // Cập nhật trạng thái hiển thị
    const statusIndicator = document.querySelector('.bot-status-indicator');
    if (statusIndicator) {
        // Xóa nội dung cũ
        statusIndicator.innerHTML = '';
        
        // Tạo badge mới dựa trên trạng thái
        let badge;
        if (data.status === 'running') {
            badge = `<span class="badge rounded-pill text-bg-success">
                <i class="fas fa-circle-notch fa-spin me-1"></i> Đang chạy
            </span>`;
        } else if (data.status === 'restarting') {
            badge = `<span class="badge rounded-pill text-bg-warning">
                <i class="fas fa-sync fa-spin me-1"></i> Đang khởi động lại
            </span>`;
        } else {
            badge = `<span class="badge rounded-pill text-bg-secondary">
                <i class="fas fa-stop-circle me-1"></i> Đã dừng
            </span>`;
        }
        
        // Thêm badge mới
        statusIndicator.innerHTML = badge;
    }
    
    // Cập nhật menu dropdown
    const dropdownMenu = document.querySelector('#botActions + .dropdown-menu');
    if (dropdownMenu) {
        const startBtn = dropdownMenu.querySelector('.start-bot-btn');
        const stopBtn = dropdownMenu.querySelector('.stop-bot-btn');
        
        if (data.status === 'running') {
            // Ẩn start, hiện stop
            if (startBtn) startBtn.parentElement.style.display = 'none';
            if (stopBtn) stopBtn.parentElement.style.display = 'block';
        } else {
            // Hiện start, ẩn stop
            if (startBtn) startBtn.parentElement.style.display = 'block';
            if (stopBtn) stopBtn.parentElement.style.display = 'none';
        }
    }
    
    // Cập nhật các phần tử khác nếu cần
    const statusModeElements = document.querySelectorAll('[id="status-mode"]');
    statusModeElements.forEach(element => {
        element.textContent = data.mode ? data.mode.toUpperCase() : 'DEMO';
    });
    
    const statusDotElements = document.querySelectorAll('[id="status-dot"]');
    statusDotElements.forEach(element => {
        if (data.status === 'running') {
            element.style.backgroundColor = 'var(--bs-success)';
        } else if (data.status === 'restarting') {
            element.style.backgroundColor = 'var(--bs-warning)';
        } else {
            element.style.backgroundColor = 'var(--bs-danger)';
        }
    });
    
    const statusTextElements = document.querySelectorAll('[id="status-text"]');
    statusTextElements.forEach(element => {
        if (data.status === 'running') {
            element.textContent = 'Đang chạy';
        } else if (data.status === 'restarting') {
            element.textContent = 'Đang khởi động lại';
        } else {
            element.textContent = 'Đã dừng';
        }
    });
    
    // Cập nhật nút mobile nếu có
    const mobileBotToggle = document.getElementById('mobileBotToggle');
    if (mobileBotToggle) {
        if (data.status === 'running') {
            mobileBotToggle.classList.remove('btn-success');
            mobileBotToggle.classList.add('btn-danger');
            mobileBotToggle.innerHTML = '<i class="fas fa-stop-circle"></i> Dừng Bot';
        } else {
            mobileBotToggle.classList.remove('btn-danger');
            mobileBotToggle.classList.add('btn-success');
            mobileBotToggle.innerHTML = '<i class="fas fa-play-circle"></i> Chạy Bot';
        }
    }
}

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