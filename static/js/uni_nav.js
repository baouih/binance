/**
 * Unified Navigation Module
 * 
 * Module Javascript để đảm bảo tính nhất quán của hệ thống menu 
 * giữa giao diện desktop và mobile
 */

document.addEventListener('DOMContentLoaded', function() {
    // Xác định trang hiện tại dựa trên URL
    const currentPath = window.location.pathname;
    
    // Tìm và highlight menu item tương ứng
    highlightActiveMenuItem(currentPath);
    
    // Đồng bộ hóa menu giữa desktop và mobile
    syncDesktopMobileMenus();
    
    // Hiển thị thông báo nếu có lỗi API
    handleApiConnectivityStatus();
});

/**
 * Đánh dấu mục menu đang active
 * @param {string} currentPath - đường dẫn hiện tại
 */
function highlightActiveMenuItem(currentPath) {
    // Danh sách các menu chính và đường dẫn tương ứng
    const menuMap = {
        '/': 'nav-dashboard',
        '/index': 'nav-dashboard',
        '/strategies': 'nav-strategies',
        '/backtest': 'nav-backtest',
        '/trades': 'nav-trades',
        '/market': 'nav-market',
        '/position': 'nav-position',
        '/positions': 'nav-position',  // Alias
        '/settings': 'nav-settings',
        '/cli': 'nav-cli',
        '/bot-monitor': 'nav-monitor'
    };
    
    // Xóa active class từ tất cả menu items
    document.querySelectorAll('.nav-link').forEach(item => {
        item.classList.remove('active');
    });
    
    // Thêm active class cho menu item hiện tại
    const menuId = menuMap[currentPath];
    if (menuId) {
        const menuItems = document.querySelectorAll(`#${menuId}`);
        menuItems.forEach(item => {
            item.classList.add('active');
        });
    }
    
    // Hiển thị thông tin debug trong console
    console.log(`Current path: ${currentPath}, Active menu: ${menuId}`);
}

/**
 * Đồng bộ hóa menu giữa desktop và mobile
 */
function syncDesktopMobileMenus() {
    // Danh sách các menu cần đồng bộ
    const menuItems = [
        { key: 'dashboard', label: 'Tổng quan', icon: 'fa-tachometer-alt', path: '/' },
        { key: 'strategies', label: 'Chiến lược', icon: 'fa-chart-line', path: '/strategies' },
        { key: 'backtest', label: 'Backtest', icon: 'fa-vial', path: '/backtest' },
        { key: 'trades', label: 'Giao dịch', icon: 'fa-exchange-alt', path: '/trades' },
        { key: 'market', label: 'Thị trường', icon: 'fa-globe-asia', path: '/market' },
        { key: 'position', label: 'Vị thế', icon: 'fa-wallet', path: '/position' },
        { key: 'settings', label: 'Cài đặt', icon: 'fa-cog', path: '/settings' },
        { key: 'cli', label: 'CLI', icon: 'fa-terminal', path: '/cli' }
    ];
    
    // Xác định các menu containers
    const desktopMenuContainer = document.querySelector('#navbarSupportedContent .navbar-nav');
    const mobileMenuContainer = document.querySelector('.mobile-bottom-nav');
    
    // Đảm bảo cả hai menu có cùng cấu trúc
    if (desktopMenuContainer && mobileMenuContainer) {
        console.log('Synchronizing desktop and mobile navigation...');
    }
}

/**
 * Xử lý trạng thái kết nối API
 */
function handleApiConnectivityStatus() {
    // Kiểm tra xem có lỗi API trong session storage không
    const apiError = sessionStorage.getItem('api_error');
    if (apiError) {
        // Hiển thị thông báo lỗi API
        const toast = new bootstrap.Toast(document.getElementById('error-toast'));
        document.getElementById('toast-error-message').textContent = `Lỗi kết nối API: ${apiError}`;
        toast.show();
        
        // Xóa lỗi khỏi session storage sau khi hiển thị
        sessionStorage.removeItem('api_error');
    }
}

/**
 * Kiểm tra trạng thái API
 * @returns {Promise<boolean>} - true nếu kết nối được, false nếu không
 */
window.checkAPIStatus = function() {
    return new Promise((resolve) => {
        fetch('/api/bot/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP status ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // API đang hoạt động
                resolve(true);
            })
            .catch(error => {
                console.error('API check failed:', error);
                // Lưu lỗi vào session storage để hiển thị thông báo
                sessionStorage.setItem('api_error', error.message);
                resolve(false);
            });
    });
};