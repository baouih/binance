/**
 * status-updater.js - Cập nhật trạng thái các dịch vụ
 * 
 * Script này xử lý việc cập nhật trạng thái trên giao diện người dùng
 * từ dữ liệu API theo định kỳ.
 */

// Định nghĩa URL API
const SERVICE_API_URL = '/api/services/market-notifier/status'; // API endpoint chính cho market notifier

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
    // Hardcoded fallback data to ensure UI displays correctly even if API fails
    const fallbackData = {
        status: 'unknown',
        pid: null,
        running: false,
        last_check: new Date().toISOString().replace('T', ' ').substring(0, 19),
        status_detail: 'Chưa kết nối được với máy chủ'
    };
    
    try {
        // Gọi API lấy trạng thái
        console.log('Đang gọi API endpoint:', SERVICE_API_URL);
        
        // Thử dùng fetch với URL
        fetch(SERVICE_API_URL)
            .then(response => {
                console.log('Nhận được phản hồi từ API:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`Không thể kết nối tới API: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Dữ liệu nhận được:', data);
                updateUI(data); // Cập nhật UI với dữ liệu thật
            })
            .catch(error => {
                console.error('Lỗi khi gọi API:', error);
                // Cập nhật UI với dữ liệu fallback khi có lỗi
                updateUI(fallbackData); 
            });
    } catch (error) {
        console.error('Lỗi ngoại lệ:', error);
        updateUI(fallbackData);
    }
    
    // Function nội bộ để cập nhật UI
    function updateUI(data) {
        const statusPanel = document.querySelector('.status-panel');
        if (!statusPanel) return;
        
        // Tìm phần tử hiển thị trạng thái
        const notifierItem = document.querySelector('.status-item[data-service="market_notifier"]');
        if (!notifierItem) return;
        
        // Cập nhật indicator
        const indicator = notifierItem.querySelector('.status-indicator');
        if (indicator) {
            indicator.className = 'status-indicator';
            indicator.classList.add(data.status || 'unknown');
            indicator.setAttribute('data-status', data.status || 'unknown');
        }
        
        // Cập nhật text
        const statusText = notifierItem.querySelector('.status-text');
        if (statusText) {
            let text = 'Không xác định';
            if (data.status === 'running') text = 'Đang chạy';
            else if (data.status === 'stopped') text = 'Đã dừng';
            else if (data.status === 'error') text = 'Lỗi';
            
            statusText.textContent = text;
        }
        
        // Cập nhật thời gian
        const timeElement = notifierItem.querySelector('.status-time');
        if (timeElement && data.last_check) {
            timeElement.textContent = data.last_check;
        }
        
        // Cập nhật chi tiết
        const detailsElement = notifierItem.querySelector('.service-details');
        if (detailsElement) {
            // Xóa nội dung cũ
            detailsElement.innerHTML = '';
            
            // Thêm chi tiết mới
            if (data.pid) {
                addDetailItem(detailsElement, 'PID', data.pid);
            }
            
            if (data.status_detail) {
                addDetailItem(detailsElement, 'Chi tiết', data.status_detail);
            }
        }
        
        // Cập nhật thời gian cập nhật cuối
        const lastUpdate = document.getElementById('last-status-update');
        if (lastUpdate) {
            const now = new Date();
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            const seconds = now.getSeconds().toString().padStart(2, '0');
            lastUpdate.textContent = `${hours}:${minutes}:${seconds}`;
        }
    }
}
}

/**
 * Cập nhật UI với dữ liệu trạng thái
 * @param {Object} statusData - Dữ liệu trạng thái từ API
 */
function updateStatusUI(statusData) {
    // Debug - ghi ra console để xem dữ liệu
    console.log('Dữ liệu trạng thái nhận được:', statusData);
    
    // Kiểm tra xem dữ liệu có hợp lệ không
    if (!statusData || typeof statusData !== 'object') {
        console.error('Dữ liệu trạng thái không hợp lệ:', statusData);
        return;
    }
    
    // Cập nhật trạng thái dịch vụ thông báo thị trường
    const marketNotifierElement = document.querySelector('.status-item[data-service="market_notifier"]');
    if (marketNotifierElement) {
        const statusIndicator = marketNotifierElement.querySelector('.status-indicator');
        const statusText = marketNotifierElement.querySelector('.status-text');
        const statusTime = marketNotifierElement.querySelector('.status-time');
        
        if (statusIndicator) {
            // Xóa tất cả các lớp trạng thái
            statusIndicator.className = 'status-indicator';
            
            // Thêm lớp dựa trên trạng thái
            let statusClass = 'unknown';
            if (statusData.status === 'running') statusClass = 'running';
            else if (statusData.status === 'stopped') statusClass = 'stopped';
            else if (statusData.status === 'error') statusClass = 'error';
            
            statusIndicator.classList.add(statusClass);
            statusIndicator.setAttribute('data-status', statusData.status || 'unknown');
        }
        
        if (statusText) {
            let statusMessage = 'Không xác định';
            if (statusData.status === 'running') statusMessage = 'Đang chạy';
            else if (statusData.status === 'stopped') statusMessage = 'Đã dừng';
            else if (statusData.status === 'error') statusMessage = 'Lỗi';
            
            statusText.textContent = statusMessage;
        }
        
        if (statusTime && statusData.last_check) {
            try {
                // Định dạng thời gian
                const updateTime = new Date(statusData.last_check);
                statusTime.textContent = formatTime(updateTime);
            } catch (e) {
                console.error('Lỗi khi định dạng thời gian:', e);
                statusTime.textContent = statusData.last_check || '--:--:--';
            }
        }
        
        // Cập nhật thông tin bổ sung
        const detailsElement = marketNotifierElement.querySelector('.service-details');
        if (detailsElement) {
            detailsElement.innerHTML = ''; // Xóa nội dung cũ
            
            // Thêm các chi tiết mới
            if (statusData.pid) {
                addDetailItem(detailsElement, 'PID', statusData.pid);
            }
            
            if (statusData.started_at) {
                addDetailItem(detailsElement, 'Thời gian khởi động', statusData.started_at);
            }
            
            if (statusData.monitored_coins && Array.isArray(statusData.monitored_coins) && statusData.monitored_coins.length > 0) {
                addDetailItem(detailsElement, 'Coin theo dõi', statusData.monitored_coins.join(', '));
            }
        }
    }

    // Cập nhật thời gian cập nhật cuối cùng
    const lastUpdateElement = document.getElementById('last-status-update');
    if (lastUpdateElement) {
        const now = new Date();
        lastUpdateElement.textContent = formatTime(now);
    }
}

/**
 * Thêm một mục chi tiết vào phần tử cha
 */
function addDetailItem(parentElement, key, value) {
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
    parentElement.appendChild(detailItem);
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

// Gắn các hàm vào đối tượng window để có thể sử dụng ở nơi khác
window.statusUpdater = {
    updateServiceStatus,
    startPeriodicUpdates,
    stopPeriodicUpdates
};