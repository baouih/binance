// Main JavaScript file for the BinanceTrader Bot

// Biến toàn cục để theo dõi trạng thái kết nối API
window.apiConnectionStatus = {
    isConnected: false,
    lastConnected: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 3
};

// Chức năng tải ban đầu của API
window.initializeAPIConnection = function() {
    if (window.apiConnectionStatus.isConnected) {
        console.log('API connection already established, skipping initialization');
        return Promise.resolve(true);
    }
    
    console.log('Initializing API connection...');
    
    return fetch('/api/bot/status')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('API connection established:', data);
            window.apiConnectionStatus.isConnected = true;
            window.apiConnectionStatus.lastConnected = new Date();
            window.apiConnectionStatus.reconnectAttempts = 0;
            return true;
        })
        .catch(error => {
            console.error('API connection error:', error);
            window.apiConnectionStatus.isConnected = false;
            return false;
        });
};

// Kiểm tra định kỳ trạng thái API
window.checkAPIStatus = function() {
    // Nếu đã kết nối trong 30 giây qua, hãy bỏ qua kiểm tra
    if (window.apiConnectionStatus.isConnected && 
        window.apiConnectionStatus.lastConnected && 
        (new Date() - window.apiConnectionStatus.lastConnected) < 30000) {
        return Promise.resolve(true);
    }
    
    console.log('Checking API status...');
    
    return fetch('/api/bot/status')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('API status check successful:', data);
            window.apiConnectionStatus.isConnected = true;
            window.apiConnectionStatus.lastConnected = new Date();
            window.apiConnectionStatus.reconnectAttempts = 0;
            return true;
        })
        .catch(error => {
            console.error('API status check failed:', error);
            window.apiConnectionStatus.isConnected = false;
            
            // Thử kết nối lại nếu chưa đạt số lần thử tối đa
            if (window.apiConnectionStatus.reconnectAttempts < window.apiConnectionStatus.maxReconnectAttempts) {
                window.apiConnectionStatus.reconnectAttempts++;
                console.log(`Attempting to reconnect (${window.apiConnectionStatus.reconnectAttempts}/${window.apiConnectionStatus.maxReconnectAttempts})...`);
                return window.initializeAPIConnection();
            }
            
            return false;
        });
};

// Khởi tạo kết nối khi trang được tải
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo kết nối API
    window.initializeAPIConnection();
    
    // Thiết lập kiểm tra định kỳ
    setInterval(window.checkAPIStatus, 60000); // Kiểm tra mỗi 60 giây
    // Helper function to show toast messages
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
    
    // Theme toggle functionality
    const toggleThemeBtn = document.getElementById('toggleTheme');
    const themeText = document.getElementById('themeText');
    const htmlElement = document.documentElement;
    
    if (toggleThemeBtn) {
        toggleThemeBtn.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            htmlElement.setAttribute('data-bs-theme', newTheme);
            
            if (themeText) {
                themeText.textContent = newTheme === 'dark' ? 'Chế độ sáng' : 'Chế độ tối';
            }
            
            // Store theme preference in localStorage
            localStorage.setItem('theme', newTheme);
        });
    }
    
    // Apply saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.setAttribute('data-bs-theme', savedTheme);
        if (themeText) {
            themeText.textContent = savedTheme === 'dark' ? 'Chế độ sáng' : 'Chế độ tối';
        }
    }
    
    // Show/hide loading overlay
    window.showLoading = function() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.remove('d-none');
        }
    };
    
    window.hideLoading = function() {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('d-none');
        }
    };
    
    // Format numbers with commas
    window.formatNumber = function(num, decimals = 2) {
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    };
    
    // Format currency amounts
    window.formatCurrency = function(amount, currency = 'USD', decimals = 2) {
        return amount.toLocaleString('en-US', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    };
    
    // Format percentage values
    window.formatPercentage = function(value, decimals = 2) {
        return value.toLocaleString('en-US', {
            style: 'percent',
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    };
    
    // Helper function to create a color based on value
    window.getColorForValue = function(value, thresholds = {
        positive: 0,
        warning_positive: 5,
        warning_negative: -5,
        negative: -10
    }) {
        if (value >= thresholds.warning_positive) {
            return 'success';
        } else if (value > thresholds.positive) {
            return 'info';
        } else if (value >= thresholds.warning_negative) {
            return 'warning';
        } else {
            return 'danger';
        }
    };
    
    // Helper function to create trend arrow
    window.getTrendArrow = function(value) {
        if (value > 0) {
            return '<i class="fas fa-arrow-up text-success"></i>';
        } else if (value < 0) {
            return '<i class="fas fa-arrow-down text-danger"></i>';
        } else {
            return '<i class="fas fa-minus text-secondary"></i>';
        }
    };
    
    // Format time ago
    window.timeAgo = function(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        let interval = Math.floor(seconds / 31536000);
        if (interval >= 1) {
            return interval + ' năm trước';
        }
        
        interval = Math.floor(seconds / 2592000);
        if (interval >= 1) {
            return interval + ' tháng trước';
        }
        
        interval = Math.floor(seconds / 86400);
        if (interval >= 1) {
            return interval + ' ngày trước';
        }
        
        interval = Math.floor(seconds / 3600);
        if (interval >= 1) {
            return interval + ' giờ trước';
        }
        
        interval = Math.floor(seconds / 60);
        if (interval >= 1) {
            return interval + ' phút trước';
        }
        
        return Math.floor(seconds) + ' giây trước';
    };
    
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Set up global error handling for fetch requests
window.fetchWithErrorHandling = async function(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        
        // Show error toast
        const errorToast = document.getElementById('error-toast');
        const errorMessage = document.getElementById('toast-error-message');
        
        if (errorToast && errorMessage) {
            errorMessage.textContent = 'Lỗi kết nối: ' + error.message;
            const toast = new bootstrap.Toast(errorToast);
            toast.show();
        }
        
        return { error: error.message };
    }
};