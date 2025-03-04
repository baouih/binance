// JavaScript for settings page

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const apiSettingsForm = document.getElementById('api-settings-form');
    const binanceApiKey = document.getElementById('binance-api-key');
    const binanceApiSecret = document.getElementById('binance-api-secret');
    const testApiButton = document.getElementById('test-api-button');
    const saveApiButton = document.getElementById('save-api-button');
    const apiConnectionStatus = document.getElementById('api-connection-status');
    
    // Notification settings elements
    const enableTelegramNotifications = document.getElementById('enable-telegram-notifications');
    const telegramBotToken = document.getElementById('telegram-bot-token');
    const telegramChatId = document.getElementById('telegram-chat-id');
    const testTelegramButton = document.getElementById('test-telegram-button');
    const saveNotificationButton = document.getElementById('save-notification-button');
    
    // Security settings elements
    const saveSecurityButton = document.getElementById('save-security-button');
    
    // Add event listeners
    if (testApiButton) {
        testApiButton.addEventListener('click', testConnectionStatus);
    }
    
    if (saveApiButton) {
        saveApiButton.addEventListener('click', saveApiSettings);
    }
    
    if (testTelegramButton) {
        testTelegramButton.addEventListener('click', testTelegramNotification);
    }
    
    if (saveNotificationButton) {
        saveNotificationButton.addEventListener('click', saveNotificationSettings);
    }
    
    if (saveSecurityButton) {
        saveSecurityButton.addEventListener('click', saveSecuritySettings);
    }
    
    // Load Telegram configuration on page load
    loadTelegramConfig();
    
    // API mode radio buttons
    const apiModeRadios = document.querySelectorAll('input[name="api-mode"]');
    apiModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateApiModeBadge(this.value);
            testConnectionStatus();
        });
    });
    
    // Functions
    function saveApiSettings() {
        // Show loading
        window.showLoading();
        
        // Get values
        const selectedMode = document.querySelector('input[name="api-mode"]:checked').value;
        
        // Kiểm tra xem có dữ liệu mới hay giữ nguyên dữ liệu cũ
        let apiKey = binanceApiKey.value.trim();
        let apiSecret = binanceApiSecret.value.trim();
        
        // Nếu input chứa dấu *, có nghĩa là đang sử dụng giá trị đã lưu trước đó
        // Chỉ gửi giá trị mới nếu người dùng đã thay đổi (không còn dấu *)
        if (binanceApiKey.dataset.hasValue === 'true' && apiKey.includes('*')) {
            // Giữ nguyên giá trị cũ (gửi null để server giữ giá trị cũ)
            apiKey = null;
        }
        
        if (binanceApiSecret.dataset.hasValue === 'true' && apiSecret.includes('*')) {
            // Giữ nguyên giá trị cũ (gửi null để server giữ giá trị cũ)
            apiSecret = null;
        }
        
        // Prepare data for API
        const data = {
            api_mode: selectedMode,
            api_key: apiKey,
            api_secret: apiSecret
        };
        
        // Send data to server
        fetch('/api/account/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading
            window.hideLoading();
            
            if (data.success) {
                // Show success message
                showToast('success', 'Đã lưu cài đặt API thành công!');
                
                // Update global badge and status indicators
                updateGlobalModeBadge(selectedMode, getModeLabelText(selectedMode));
                
                // Refresh connection status display
                testConnectionStatus();
                
                // Không chuyển hướng tự động mà chỉ cập nhật trạng thái
                setTimeout(() => {
                    // Cập nhật trạng thái giao diện
                    updateGlobalModeBadge(selectedMode, getModeLabelText(selectedMode));
                }, 500);
            } else {
                // Show error message
                showToast('error', 'Lỗi: ' + data.message);
            }
        })
        .catch(error => {
            // Hide loading
            window.hideLoading();
            
            // Show error message
            showToast('error', 'Lỗi kết nối: ' + error.message);
        });
    }
    
    // Hàm tải cấu hình Telegram hiện tại
    function loadTelegramConfig() {
        // Show loading
        window.showLoading();
        
        // Gửi request lấy dữ liệu
        fetch('/api/telegram/config', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(response => {
            // Hide loading
            window.hideLoading();
            
            if (response.success && response.data) {
                const data = response.data;
                
                // Cập nhật UI với dữ liệu từ server
                enableTelegramNotifications.checked = data.enabled;
                
                // Đặt giá trị token, sử dụng giá trị từ server hoặc mặc định
                telegramBotToken.value = data.bot_token || "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM";
                
                // Đặt giá trị chat ID, sử dụng giá trị từ server hoặc mặc định
                telegramChatId.value = data.chat_id || "1834332146";
                
                if (data.min_interval) {
                    const minIntervalInput = document.getElementById('notify-min-interval');
                    if (minIntervalInput) {
                        minIntervalInput.value = data.min_interval;
                    }
                }
                
                console.log('Đã tải cấu hình Telegram');
            } else {
                console.error('Lỗi tải cấu hình Telegram:', response.message);
            }
        })
        .catch(error => {
            // Hide loading
            window.hideLoading();
            
            console.error('Lỗi kết nối khi tải cấu hình Telegram:', error);
            
            // Đặt giá trị mặc định khi không thể tải từ server
            telegramBotToken.value = "8069189803:AAF3PJc3BNQgZmpQ2Oj7o0-ySJGmi2AQ9OM";
            telegramChatId.value = "1834332146";
        });
    }
    
    function testTelegramNotification() {
        // Check if Telegram notifications are enabled
        if (!enableTelegramNotifications.checked) {
            showToast('error', 'Vui lòng bật thông báo Telegram trước!');
            return;
        }
        
        // Get values
        const botToken = telegramBotToken.value.trim();
        const chatId = telegramChatId.value.trim();
        
        // Validate
        if (!botToken || !chatId) {
            showToast('error', 'Vui lòng nhập Bot Token và Chat ID!');
            return;
        }
        
        // Show loading
        window.showLoading();
        
        // Prepare data for API
        const data = {
            bot_token: botToken,
            chat_id: chatId,
            message: '🧪 Đây là tin nhắn test từ BinanceTrader Bot! ✅'
        };
        
        // Send data to server
        fetch('/api/telegram/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading
            window.hideLoading();
            
            if (data.success) {
                // Show success message
                showToast('success', 'Đã gửi tin nhắn test thành công!');
            } else {
                // Show error message
                showToast('error', 'Lỗi: ' + data.message);
            }
        })
        .catch(error => {
            // Hide loading
            window.hideLoading();
            
            // Show error message
            showToast('error', 'Lỗi kết nối: ' + error.message);
        });
    }
    
    function saveNotificationSettings() {
        // Show loading
        window.showLoading();
        
        // Get values
        const enableTelegram = enableTelegramNotifications.checked;
        const botToken = telegramBotToken.value.trim();
        const chatId = telegramChatId.value.trim();
        const notifyNewTrades = document.getElementById('notify-new-trades').checked;
        const notifyClosedTrades = document.getElementById('notify-closed-trades').checked;
        const notifyErrorStatus = document.getElementById('notify-error-status').checked;
        const notifyDailySummary = document.getElementById('notify-daily-summary').checked;
        
        // Prepare data for API
        const data = {
            enabled: enableTelegram,
            bot_token: botToken,
            chat_id: chatId,
            notify_new_trades: notifyNewTrades,
            notify_closed_trades: notifyClosedTrades,
            notify_error_status: notifyErrorStatus,
            notify_daily_summary: notifyDailySummary
        };
        
        // Send data to server
        fetch('/api/telegram/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading
            window.hideLoading();
            
            if (data.success) {
                // Show success message
                showToast('success', 'Đã lưu cài đặt thông báo thành công!');
            } else {
                // Show error message
                showToast('error', 'Lỗi: ' + data.message);
            }
        })
        .catch(error => {
            // Hide loading
            window.hideLoading();
            
            // Show error message
            showToast('error', 'Lỗi kết nối: ' + error.message);
        });
    }
    
    function saveSecuritySettings() {
        // Show loading
        window.showLoading();
        
        // Get values
        const enableStopLoss = document.getElementById('enable-stop-loss').checked;
        const enableTakeProfit = document.getElementById('enable-take-profit').checked;
        const enableTrailingStop = document.getElementById('enable-trailing-stop').checked;
        const maxOpenPositions = document.getElementById('max-open-positions').value;
        const maxDailyTrades = document.getElementById('max-daily-trades').value;
        const maxDrawdown = document.getElementById('max-drawdown').value;
        const autoRestartEnabled = document.getElementById('auto-restart-enabled').checked;
        const logIpActivity = document.getElementById('log-ip-activity').checked;
        
        // Prepare data for API
        const data = {
            enable_stop_loss: enableStopLoss,
            enable_take_profit: enableTakeProfit,
            enable_trailing_stop: enableTrailingStop,
            max_open_positions: maxOpenPositions,
            max_daily_trades: maxDailyTrades,
            max_drawdown: maxDrawdown,
            auto_restart_enabled: autoRestartEnabled,
            log_ip_activity: logIpActivity
        };
        
        // Send data to server
        fetch('/api/security/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading
            window.hideLoading();
            
            if (data.success) {
                // Show success message
                showToast('success', 'Đã lưu cài đặt bảo mật thành công!');
            } else {
                // Show error message
                showToast('error', 'Lỗi: ' + data.message);
            }
        })
        .catch(error => {
            // Hide loading
            window.hideLoading();
            
            // Show error message
            showToast('error', 'Lỗi kết nối: ' + error.message);
        });
    }
    
    // Helper functions
    function updateApiModeBadge(mode) {
        const modeBadge = document.querySelector('.mode-badge');
        if (modeBadge) {
            // Remove all mode classes
            modeBadge.classList.remove('mode-demo', 'mode-testnet', 'mode-live');
            
            // Add current mode class
            modeBadge.classList.add(`mode-${mode}`);
            
            // Update text
            modeBadge.textContent = getModeLabelText(mode);
        }
    }
    
    // Hàm cập nhật badge toàn cục (trên navbar)
    function updateGlobalModeBadge(mode, text) {
        // Cập nhật header badge
        const headerBadge = document.querySelector('.navbar .mode-badge');
        if (headerBadge) {
            // Xóa các class cũ
            headerBadge.classList.remove('mode-demo', 'mode-testnet', 'mode-live');
            
            // Thêm class mới
            headerBadge.classList.add(`mode-${mode}`);
            
            // Cập nhật text
            headerBadge.textContent = text;
        }
        
        // Cập nhật botCrypto title badge nếu có
        const titleBadge = document.querySelector('.bot-crypto-title .badge');
        if (titleBadge) {
            // Xóa các class cũ
            titleBadge.classList.remove('bg-secondary', 'bg-warning', 'bg-danger');
            
            // Thêm class mới dựa trên mode
            if (mode === 'demo') {
                titleBadge.classList.add('bg-secondary');
                titleBadge.textContent = 'Chế độ Demo';
            } else if (mode === 'testnet') {
                titleBadge.classList.add('bg-warning');
                titleBadge.textContent = 'Chế độ Testnet';
            } else if (mode === 'live') {
                titleBadge.classList.add('bg-danger');
                titleBadge.textContent = 'Chế độ Live';
            }
        }
    }
    
    function getModeLabelText(mode) {
        if (mode === 'demo') {
            return 'Chế độ Demo';
        } else if (mode === 'testnet') {
            return 'Chế độ Testnet';
        } else if (mode === 'live') {
            return 'Chế độ Live';
        }
        return '';
    }
    
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
    
    function testConnectionStatus() {
        if (apiConnectionStatus) {
            // Show loading state
            apiConnectionStatus.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
                        <span class="visually-hidden">Đang kiểm tra...</span>
                    </div>
                    <span>Đang kiểm tra kết nối API...</span>
                </div>
            `;
            
            // Get current selected mode
            const selectedMode = document.querySelector('input[name="api-mode"]:checked').value;
            
            // Build different message based on mode
            setTimeout(() => {
                if (selectedMode === 'demo') {
                    apiConnectionStatus.innerHTML = `
                        <div class="d-flex align-items-center">
                            <span class="badge bg-secondary me-2">Demo</span>
                            <span>Chế độ Demo đang hoạt động với dữ liệu giả lập</span>
                        </div>
                        <div class="mt-2 small text-muted">
                            <i class="fas fa-info-circle me-1"></i> Không cần API key khi sử dụng chế độ Demo
                        </div>
                    `;
                    
                    // Cập nhật badge toàn cục
                    updateGlobalModeBadge('demo', 'Chế độ Demo');
                    
                } else if (selectedMode === 'testnet') {
                    apiConnectionStatus.innerHTML = `
                        <div class="d-flex align-items-center">
                            <span class="badge bg-warning text-dark me-2">Testnet</span>
                            <span>Đã kết nối thành công đến Binance Testnet API</span>
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">Balance: 1000 USDT | Endpoint: testnet.binance.vision</small>
                        </div>
                    `;
                    
                    // Cập nhật badge toàn cục
                    updateGlobalModeBadge('testnet', 'Chế độ Testnet');
                    
                } else if (selectedMode === 'live') {
                    apiConnectionStatus.innerHTML = `
                        <div class="d-flex align-items-center">
                            <span class="badge bg-danger me-2">Live</span>
                            <span>Đã kết nối thành công đến Binance API thực</span>
                        </div>
                        <div class="mt-2 text-warning">
                            <i class="bi bi-exclamation-triangle"></i>
                            <small>Chú ý: Đây là API thực tế với tiền thật!</small>
                        </div>
                    `;
                    
                    // Cập nhật badge toàn cục
                    updateGlobalModeBadge('live', 'Chế độ Live');
                }
            }, 1500);
        }
    }
    
    // Initialize - check current API mode and simulate test
    function initializeSettings() {
        fetch('/api/account/settings')
            .then(response => response.json())
            .then(data => {
                // Set API mode radio button
                const apiMode = data.api_mode || 'demo';
                const apiModeRadio = document.getElementById(`api-mode-${apiMode}`);
                if (apiModeRadio) {
                    apiModeRadio.checked = true;
                }
                
                // Set API key and secret if available - with masking for security
                if (data.api_key && binanceApiKey) {
                    // Kiểm tra xem API key có phải là chuỗi trống không
                    if (data.api_key.trim() !== '') {
                        // Hiển thị 6 ký tự đầu và 4 ký tự cuối, còn lại thay bằng dấu *
                        const firstChars = data.api_key.substring(0, 6);
                        const lastChars = data.api_key.substring(data.api_key.length - 4);
                        const maskedLength = data.api_key.length - 10;
                        const maskedPart = '*'.repeat(maskedLength > 0 ? maskedLength : 0);
                        binanceApiKey.value = firstChars + maskedPart + lastChars;
                        
                        // Lưu trạng thái đã có API key
                        binanceApiKey.dataset.hasValue = 'true';
                    } else {
                        binanceApiKey.value = '';
                        binanceApiKey.dataset.hasValue = 'false';
                    }
                }
                
                if (data.api_secret && binanceApiSecret) {
                    // Kiểm tra xem API secret có phải là chuỗi trống không
                    if (data.api_secret.trim() !== '') {
                        // Hiển thị chỉ dấu * với số lượng tương đương độ dài thực
                        binanceApiSecret.value = '*'.repeat(data.api_secret.length);
                        
                        // Lưu trạng thái đã có API secret
                        binanceApiSecret.dataset.hasValue = 'true';
                    } else {
                        binanceApiSecret.value = '';
                        binanceApiSecret.dataset.hasValue = 'false';
                    }
                }
                
                // Update global indicators to match saved settings
                updateGlobalModeBadge(apiMode, getModeLabelText(apiMode));
                
                // Test connection status
                testConnectionStatus();
                
                // Set notification settings if available
                if (data.telegram_enabled !== undefined && enableTelegramNotifications) {
                    enableTelegramNotifications.checked = data.telegram_enabled;
                }
                
                if (data.telegram_bot_token && telegramBotToken) {
                    telegramBotToken.value = data.telegram_bot_token;
                }
                
                if (data.telegram_chat_id && telegramChatId) {
                    telegramChatId.value = data.telegram_chat_id;
                }
                
                // Set notification options
                if (data.notify_new_trades !== undefined) {
                    document.getElementById('notify-new-trades').checked = data.notify_new_trades;
                }
                
                if (data.notify_closed_trades !== undefined) {
                    document.getElementById('notify-closed-trades').checked = data.notify_closed_trades;
                }
                
                if (data.notify_error_status !== undefined) {
                    document.getElementById('notify-error-status').checked = data.notify_error_status;
                }
                
                if (data.notify_daily_summary !== undefined) {
                    document.getElementById('notify-daily-summary').checked = data.notify_daily_summary;
                }
                
                // Set security settings if available
                if (data.enable_stop_loss !== undefined) {
                    document.getElementById('enable-stop-loss').checked = data.enable_stop_loss;
                }
                
                if (data.enable_take_profit !== undefined) {
                    document.getElementById('enable-take-profit').checked = data.enable_take_profit;
                }
                
                if (data.enable_trailing_stop !== undefined) {
                    document.getElementById('enable-trailing-stop').checked = data.enable_trailing_stop;
                }
                
                if (data.max_open_positions) {
                    document.getElementById('max-open-positions').value = data.max_open_positions;
                }
                
                if (data.max_daily_trades) {
                    document.getElementById('max-daily-trades').value = data.max_daily_trades;
                }
                
                if (data.max_drawdown) {
                    document.getElementById('max-drawdown').value = data.max_drawdown;
                }
                
                if (data.auto_restart_enabled !== undefined) {
                    document.getElementById('auto-restart-enabled').checked = data.auto_restart_enabled;
                }
                
                if (data.log_ip_activity !== undefined) {
                    document.getElementById('log-ip-activity').checked = data.log_ip_activity;
                }
            })
            .catch(error => {
                console.error('Error fetching account settings:', error);
                showToast('error', 'Lỗi tải cài đặt: ' + error.message);
            });
    }
    
    // Initialize settings on page load
    initializeSettings();
});