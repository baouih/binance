/**
 * status-updater.js - Cập nhật trạng thái các dịch vụ
 * 
 * Script này xử lý việc cập nhật trạng thái trên giao diện người dùng
 * từ dữ liệu API theo định kỳ.
 */

// Định nghĩa URL API
const STATUS_API_URL = '/api/status';
const SERVICE_API_URL = '/api/services/status';

// Biến lưu trạng thái update timer
let statusUpdateTimer = null;
const UPDATE_INTERVAL = 15000; // 15 giây

/**
 * Khởi tạo các listener cập nhật trạng thái
 */
function initStatusUpdater() {
    console.log('Initializing status updater...');
    
    // Bắt đầu cập nhật theo định kỳ
    startPeriodicUpdates();
    
    // Đăng ký sự kiện cho nút làm mới
    const refreshButton = document.getElementById('refresh-status');
    if (refreshButton) {
        refreshButton.addEventListener('click', () => {
            updateServiceStatus(true);
        });
    }
    
    // Cập nhật lần đầu
    updateServiceStatus();
}

/**
 * Bắt đầu cập nhật định kỳ
 */
function startPeriodicUpdates() {
    // Hủy timer cũ nếu có
    if (statusUpdateTimer) {
        clearInterval(statusUpdateTimer);
    }
    
    // Thiết lập timer mới
    statusUpdateTimer = setInterval(() => {
        updateServiceStatus();
    }, UPDATE_INTERVAL);
    
    console.log(`Đã thiết lập cập nhật trạng thái mỗi ${UPDATE_INTERVAL/1000} giây`);
}

/**
 * Ngừng cập nhật định kỳ
 */
function stopPeriodicUpdates() {
    if (statusUpdateTimer) {
        clearInterval(statusUpdateTimer);
        statusUpdateTimer = null;
        console.log('Đã ngừng cập nhật trạng thái định kỳ');
    }
}

/**
 * Cập nhật trạng thái các dịch vụ
 * @param {boolean} showLoading - Hiển thị biểu tượng loading
 */
function updateServiceStatus(showLoading = false) {
    // Kiểm tra xem có cần hiển thị UI của status không
    const statusPanel = document.querySelector('.status-panel');
    if (!statusPanel) {
        return;
    }
    
    // Hiển thị trạng thái đang tải nếu yêu cầu
    if (showLoading) {
        const statusItems = document.querySelectorAll('.status-item');
        statusItems.forEach(item => {
            const statusIndicator = item.querySelector('.status-indicator');
            if (statusIndicator) {
                statusIndicator.className = 'status-indicator loading';
                statusIndicator.setAttribute('data-status', 'loading');
            }
        });
    }
    
    // Gọi API lấy trạng thái
    fetch(SERVICE_API_URL)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Không thể kết nối tới API: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            updateStatusUI(data);
        })
        .catch(error => {
            console.error('Lỗi khi cập nhật trạng thái:', error);
            // Hiển thị lỗi trong UI
            const statusItems = document.querySelectorAll('.status-item');
            statusItems.forEach(item => {
                const statusIndicator = item.querySelector('.status-indicator');
                if (statusIndicator) {
                    statusIndicator.className = 'status-indicator error';
                    statusIndicator.setAttribute('data-status', 'error');
                }
            });
        });
}

/**
 * Cập nhật UI với dữ liệu trạng thái
 * @param {Object} statusData - Dữ liệu trạng thái từ API
 */
function updateStatusUI(statusData) {
    // Cập nhật từng dịch vụ
    Object.keys(statusData).forEach(service => {
        const serviceData = statusData[service];
        const serviceElement = document.querySelector(`.status-item[data-service="${service}"]`);
        
        if (serviceElement) {
            const statusIndicator = serviceElement.querySelector('.status-indicator');
            const statusText = serviceElement.querySelector('.status-text');
            const statusTime = serviceElement.querySelector('.status-time');
            
            if (statusIndicator) {
                // Xóa tất cả các lớp trạng thái
                statusIndicator.className = 'status-indicator';
                
                // Thêm lớp dựa trên trạng thái
                let statusClass = 'unknown';
                if (serviceData.status === 'running') statusClass = 'running';
                else if (serviceData.status === 'stopped') statusClass = 'stopped';
                else if (serviceData.status === 'error') statusClass = 'error';
                
                statusIndicator.classList.add(statusClass);
                statusIndicator.setAttribute('data-status', serviceData.status);
            }
            
            if (statusText) {
                let statusMessage = 'Không xác định';
                if (serviceData.status === 'running') statusMessage = 'Đang chạy';
                else if (serviceData.status === 'stopped') statusMessage = 'Đã dừng';
                else if (serviceData.status === 'error') statusMessage = 'Lỗi';
                
                statusText.textContent = statusMessage;
            }
            
            if (statusTime && serviceData.last_update) {
                // Định dạng thời gian
                const updateTime = new Date(serviceData.last_update);
                statusTime.textContent = formatTime(updateTime);
            }
            
            // Cập nhật thông tin bổ sung
            const detailsElement = serviceElement.querySelector('.service-details');
            if (detailsElement && serviceData.details) {
                detailsElement.innerHTML = ''; // Xóa nội dung cũ
                
                // Thêm các chi tiết mới
                for (const [key, value] of Object.entries(serviceData.details)) {
                    const detailItem = document.createElement('div');
                    detailItem.className = 'detail-item';
                    
                    const keyElement = document.createElement('span');
                    keyElement.className = 'detail-key';
                    keyElement.textContent = formatDetailKey(key) + ':';
                    
                    const valueElement = document.createElement('span');
                    valueElement.className = 'detail-value';
                    valueElement.textContent = value;
                    
                    detailItem.appendChild(keyElement);
                    detailItem.appendChild(valueElement);
                    detailsElement.appendChild(detailItem);
                }
            }
        }
    });
    
    // Cập nhật thời gian cập nhật cuối cùng
    const lastUpdateElement = document.getElementById('last-status-update');
    if (lastUpdateElement) {
        const now = new Date();
        lastUpdateElement.textContent = formatTime(now);
    }
}

/**
 * Định dạng khóa chi tiết để hiển thị
 * @param {string} key - Khóa cần định dạng
 * @returns {string} Chuỗi đã định dạng
 */
function formatDetailKey(key) {
    // Chuyển snake_case hoặc camelCase thành Title Case với khoảng trắng
    return key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

/**
 * Định dạng thời gian
 * @param {Date} date - Đối tượng Date cần định dạng
 * @returns {string} Chuỗi thời gian đã định dạng
 */
function formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds}`;
}

// Khởi tạo khi trang đã tải xong
document.addEventListener('DOMContentLoaded', initStatusUpdater);

// Export các hàm để có thể sử dụng ở nơi khác
export { 
    updateServiceStatus, 
    startPeriodicUpdates, 
    stopPeriodicUpdates 
};