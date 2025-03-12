/**
 * status-updater.js - Cập nhật trạng thái các dịch vụ
 */

// Cấu hình
const API_URL = '/api/services/market-notifier/status';
const UPDATE_INTERVAL = 15000; // 15 giây
let updateTimer = null;

// Khởi tạo khi tài liệu đã tải xong
document.addEventListener('DOMContentLoaded', function() {
    console.log('Status updater initialized v1.0.1');
    console.log('DOM loaded, checking for status panel...');
    
    // Debug DOM elements
    const statusPanel = document.querySelector('.status-panel');
    console.log('Status panel found:', statusPanel ? 'Yes' : 'No');
    
    const statusItems = document.querySelectorAll('.status-item');
    console.log('Status items found:', statusItems.length);
    
    statusItems.forEach((item, i) => {
        console.log(`Item ${i}:`, item.getAttribute('data-service'));
    });
    
    // Cập nhật lần đầu
    console.log('Calling initial status update...');
    updateStatus();
    
    // Thiết lập cập nhật định kỳ
    console.log(`Setting interval for ${UPDATE_INTERVAL/1000} seconds`);
    updateTimer = setInterval(updateStatus, UPDATE_INTERVAL);
    
    // Thiết lập sự kiện cho nút làm mới
    const refreshButton = document.getElementById('refresh-status');
    console.log('Refresh button found:', refreshButton ? 'Yes' : 'No');
    if (refreshButton) {
        refreshButton.addEventListener('click', updateStatus);
    }
});

// Hàm cập nhật trạng thái
function updateStatus() {
    console.log('Updating status...');
    
    // Dữ liệu fallback khi có lỗi
    const fallbackData = {
        status: 'unknown',
        running: false,
        pid: null,
        last_check: formatDateTime(new Date()),
        status_detail: 'Không thể kết nối tới máy chủ'
    };
    
    // Gọi API
    console.log(`Fetching data from ${API_URL}...`);
    
    fetch(API_URL)
        .then(response => {
            console.log('Response received:', response.status, response.statusText);
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);
            renderStatus(data);
        })
        .catch(error => {
            console.error('Error fetching status:', error);
            renderStatus(fallbackData);
        });
}

// Hiển thị trạng thái lên UI
function renderStatus(data) {
    // Tìm phần tử hiển thị trạng thái
    const statusItem = document.querySelector('.status-item[data-service="market_notifier"]');
    if (!statusItem) {
        console.error('Status item not found');
        return;
    }
    
    // Cập nhật indicator
    const indicator = statusItem.querySelector('.status-indicator');
    if (indicator) {
        indicator.className = 'status-indicator';
        indicator.classList.add(data.status || 'unknown');
        indicator.setAttribute('data-status', data.status || 'unknown');
    }
    
    // Cập nhật text
    const statusText = statusItem.querySelector('.status-text');
    if (statusText) {
        let text = 'Không xác định';
        if (data.status === 'running') text = 'Đang chạy';
        else if (data.status === 'stopped') text = 'Đã dừng';
        else if (data.status === 'error') text = 'Lỗi';
        
        statusText.textContent = text;
    }
    
    // Cập nhật thời gian
    const statusTime = statusItem.querySelector('.status-time');
    if (statusTime) {
        statusTime.textContent = data.last_check || formatTime(new Date());
    }
    
    // Cập nhật chi tiết
    const detailsElement = statusItem.querySelector('.service-details');
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
    
    // Cập nhật thời gian cập nhật cuối cùng
    const lastUpdate = document.getElementById('last-status-update');
    if (lastUpdate) {
        lastUpdate.textContent = formatTime(new Date());
    }
}

// Thêm một mục chi tiết vào phần tử cha
function addDetailItem(parent, key, value) {
    const item = document.createElement('div');
    item.className = 'detail-item';
    
    const keySpan = document.createElement('span');
    keySpan.className = 'detail-key';
    keySpan.textContent = formatKey(key) + ':';
    
    const valueSpan = document.createElement('span');
    valueSpan.className = 'detail-value';
    valueSpan.textContent = value;
    
    item.appendChild(keySpan);
    item.appendChild(valueSpan);
    parent.appendChild(item);
}

// Định dạng khóa
function formatKey(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}

// Định dạng thời gian
function formatTime(date) {
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds}`;
}

// Định dạng ngày giờ đầy đủ
function formatDateTime(date) {
    return date.toISOString().replace('T', ' ').substring(0, 19);
}