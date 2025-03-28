/**
 * status-updater.js
 * 
 * Mô-đun này quản lý việc cập nhật trạng thái của hệ thống giao dịch trên giao diện người dùng
 * với các biện pháp xử lý lỗi nâng cao để tránh các thông báo lỗi không cần thiết trên console.
 */

(function() {
    // Cấu hình
    const config = {
        updateInterval: 5000, // khoảng thời gian cập nhật (ms)
        maxRetries: 3,        // số lần thử lại tối đa khi gặp lỗi
        retryDelay: 2000      // thời gian chờ giữa các lần thử lại (ms)
    };

    // Biến trạng thái
    let retryCount = 0;
    let lastSuccessfulUpdate = Date.now();
    let isOffline = false;

    /**
     * Cập nhật trạng thái hệ thống trên giao diện
     */
    function updateSystemStatus() {
        $.ajax({
            url: '/api/status',
            type: 'GET',
            timeout: 5000,
            success: handleStatusSuccess,
            error: handleStatusError
        });
    }

    /**
     * Xử lý phản hồi thành công từ API
     */
    function handleStatusSuccess(response) {
        try {
            // Đặt lại bộ đếm thử lại
            retryCount = 0;
            lastSuccessfulUpdate = Date.now();
            
            if (isOffline) {
                console.log('Kết nối đã được khôi phục');
                isOffline = false;
            }

            // Cập nhật trạng thái bot
            updateBotStatus(response.running);
            
            // Cập nhật thông tin tài khoản
            if (response.account_balance !== undefined) {
                updateBalanceDisplay(response.account_balance);
            }
            
            // Cập nhật thông tin vị thế
            if (response.positions_count !== undefined || response.positions !== undefined) {
                const posCount = response.positions_count !== undefined ? 
                    response.positions_count : 
                    (response.positions ? response.positions.length : 0);
                updatePositionsDisplay(posCount);
            }
            
            // Cập nhật log mới nhất
            updateLatestLogDisplay(response.latest_log);
            
        } catch (e) {
            console.log('Lỗi khi xử lý dữ liệu trạng thái:', e.message);
        }
    }

    /**
     * Xử lý lỗi từ API
     */
    function handleStatusError(xhr, status, error) {
        // Tránh hiển thị lỗi "Không thể cập nhật trạng thái" trên console
        if (retryCount < config.maxRetries) {
            retryCount++;
            setTimeout(updateSystemStatus, config.retryDelay);
        } else if (!isOffline) {
            console.log('Không thể kết nối với máy chủ sau nhiều lần thử');
            isOffline = true;
        }
    }

    /**
     * Cập nhật hiển thị trạng thái bot
     */
    function updateBotStatus(isRunning) {
        const statusElement = document.querySelector('.bot-status');
        if (!statusElement) return;
        
        if (isRunning) {
            statusElement.className = 'bot-status running';
            statusElement.innerHTML = '<i class="fas fa-circle-play"></i><span>Đang Chạy</span>';
        } else {
            statusElement.className = 'bot-status stopped';
            statusElement.innerHTML = '<i class="fas fa-circle-stop"></i><span>Đã Dừng</span>';
        }
    }

    /**
     * Cập nhật hiển thị số dư tài khoản
     */
    function updateBalanceDisplay(balance) {
        const balanceElement = document.querySelector('.bot-balance');
        if (!balanceElement) return;
        
        balanceElement.innerHTML = `<strong>Số Dư:</strong> ${balance.toFixed(2)} USDT`;
    }

    /**
     * Cập nhật hiển thị số lượng vị thế
     */
    function updatePositionsDisplay(count) {
        const positionsElement = document.querySelector('.bot-positions');
        if (!positionsElement) return;
        
        positionsElement.innerHTML = `<strong>Vị Thế Mở:</strong> ${count}`;
    }

    /**
     * Cập nhật hiển thị log mới nhất
     */
    function updateLatestLogDisplay(latestLog) {
        const logElement = document.querySelector('.bot-latest-log');
        if (!logElement) return;
        
        if (latestLog && latestLog.message) {
            logElement.innerHTML = `<strong>Log Mới Nhất:</strong> ${latestLog.message}`;
        } else {
            logElement.innerHTML = `<strong>Log Mới Nhất:</strong> Không có log`;
        }
    }

    /**
     * Kiểm tra xem người dùng có online không
     */
    function checkOnlineStatus() {
        if (navigator.onLine) {
            // Nếu trình duyệt báo online nhưng chúng ta đã mất kết nối với máy chủ quá lâu
            const offlineThreshold = 30000; // 30 giây
            if (Date.now() - lastSuccessfulUpdate > offlineThreshold) {
                if (!isOffline) {
                    console.log('Kết nối với máy chủ bị mất');
                    isOffline = true;
                }
            }
        } else {
            if (!isOffline) {
                console.log('Trình duyệt đang offline');
                isOffline = true;
            }
        }
    }

    // Lắng nghe sự kiện online/offline
    window.addEventListener('online', function() {
        console.log('Trình duyệt đã online trở lại');
        isOffline = false;
        updateSystemStatus(); // Cập nhật ngay lập tức khi có kết nối trở lại
    });

    window.addEventListener('offline', function() {
        console.log('Trình duyệt đã offline');
        isOffline = true;
    });

    // Khởi tạo khi document đã sẵn sàng
    $(document).ready(function() {
        // Cập nhật trạng thái ngay lập tức
        updateSystemStatus();
        
        // Thiết lập cập nhật định kỳ
        setInterval(updateSystemStatus, config.updateInterval);
        
        // Kiểm tra trạng thái online định kỳ
        setInterval(checkOnlineStatus, 10000);
    });

    // Đăng ký hàm cập nhật toàn cục để các module khác có thể gọi khi cần
    window.updateSystemStatus = updateSystemStatus;
})();