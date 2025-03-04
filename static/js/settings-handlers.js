/**
 * Settings Page Handlers
 * -------------------------
 * Xử lý tất cả các sự kiện và tương tác trên trang cài đặt
 * Sử dụng các helper functions từ ui-helpers.js
 */

import { showAlert, showLoading, hideLoading, validateForm, fetchAPI } from './ui-helpers.js';

// Các API endpoint
const API_ENDPOINTS = {
    GENERAL_SETTINGS: '/api/v1/settings/general',
    API_SETTINGS: '/api/v1/settings/api',
    TEST_API_CONNECTION: '/api/v1/test-connection',
    TRADING_COINS: '/api/v1/trading/coins',
    RISK_SETTINGS: '/api/v1/settings/risk',
    TELEGRAM_SETTINGS: '/api/v1/settings/telegram',
    TEST_TELEGRAM: '/api/v1/test-telegram',
    NOTIFICATION_SETTINGS: '/api/v1/settings/notifications',
    ADVANCED_SETTINGS: '/api/v1/settings/advanced',
    LOG_ENTRIES: '/api/v1/logs'
};

/**
 * Khởi tạo trang cài đặt
 */
function initSettingsPage() {
    // Đăng ký tất cả các sự kiện
    setupTradingCoinsHandlers();
    setupGeneralSettingsHandlers();
    setupApiSettingsHandlers();
    setupRiskSettingsHandlers();
    setupTelegramSettingsHandlers();
    setupNotificationSettingsHandlers();
    setupAdvancedSettingsHandlers();
    setupLogsHandlers();
    
    // Thiết lập các phụ thuộc UI
    setupUIDependencies();
    
    // Thiết lập các hiệu ứng toggle
    setupToggles();
}

/**
 * Thiết lập các handler cho phần Đồng coin giao dịch
 */
function setupTradingCoinsHandlers() {
    // Select all
    const selectAllCoinsBtn = document.getElementById('selectAllCoins');
    if (selectAllCoinsBtn) {
        selectAllCoinsBtn.addEventListener('click', function () {
            document.querySelectorAll('.trading-coin-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
        });
    }
    
    // Deselect all
    const deselectAllCoinsBtn = document.getElementById('deselectAllCoins');
    if (deselectAllCoinsBtn) {
        deselectAllCoinsBtn.addEventListener('click', function () {
            document.querySelectorAll('.trading-coin-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
        });
    }
    
    // Reset to default
    const resetDefaultCoinBtn = document.getElementById('resetDefaultCoin');
    if (resetDefaultCoinBtn) {
        resetDefaultCoinBtn.addEventListener('click', function () {
            document.querySelectorAll('.trading-coin-checkbox').forEach(checkbox => {
                checkbox.checked = checkbox.value === 'BTCUSDT';
            });
        });
    }
    
    // Save trading coins settings
    const saveTradingCoinsBtn = document.getElementById('saveTradingCoinsSettings');
    if (saveTradingCoinsBtn) {
        saveTradingCoinsBtn.addEventListener('click', function () {
            // Hiển thị loading
            showLoading('Đang lưu danh sách đồng coin...');
            
            // Thu thập danh sách coin đã chọn
            const selectedCoins = [];
            document.querySelectorAll('.trading-coin-checkbox').forEach(checkbox => {
                if (checkbox.checked) {
                    selectedCoins.push(checkbox.value);
                }
            });
            
            // Kiểm tra nếu không chọn coin nào
            if (selectedCoins.length === 0) {
                hideLoading();
                showAlert('warning', 'Vui lòng chọn ít nhất một đồng coin để giao dịch.');
                return;
            }
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.TRADING_COINS, {
                method: 'POST',
                body: JSON.stringify({ coins: selectedCoins })
            }, false) // loading đã được hiển thị ở trên
                .then(data => {
                    hideLoading();
                    if (data.success) {
                        showAlert('success', 'Danh sách đồng coin giao dịch đã được cập nhật thành công!');
                        
                        // Cập nhật UI nếu cần
                        if (data.selected_coins && data.selected_coins.length > 0) {
                            document.querySelectorAll('.trading-coin-checkbox').forEach(checkbox => {
                                checkbox.checked = data.selected_coins.includes(checkbox.value);
                            });
                        }
                    } else {
                        showAlert('danger', data.message || 'Có lỗi xảy ra khi cập nhật danh sách đồng coin giao dịch.');
                    }
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Cài đặt chung
 */
function setupGeneralSettingsHandlers() {
    const saveGeneralSettingsBtn = document.getElementById('saveGeneralSettings');
    if (saveGeneralSettingsBtn) {
        saveGeneralSettingsBtn.addEventListener('click', function () {
            // Validate form if needed
            
            // Lấy các giá trị
            const botMode = document.getElementById('botMode')?.value;
            const accountType = document.getElementById('accountType')?.value;
            const strategyMode = document.getElementById('strategyMode')?.value;
            const language = document.getElementById('language')?.value;
            const timezone = document.getElementById('timezoneSelect')?.value;
            const autoStart = document.getElementById('autoStartSwitch')?.checked;
            
            // Hiển thị loading
            showLoading('Đang lưu cài đặt chung...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.GENERAL_SETTINGS, {
                method: 'POST',
                body: JSON.stringify({
                    bot_mode: botMode,
                    account_type: accountType,
                    strategy_mode: strategyMode,
                    language: language,
                    timezone: timezone,
                    auto_start: autoStart
                })
            }, false)
                .then(data => {
                    hideLoading();
                    showAlert('success', 'Cài đặt chung đã được lưu thành công!');
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Kết nối API
 */
function setupApiSettingsHandlers() {
    // Toggle secret key visibility
    const toggleSecretKeyBtn = document.getElementById('toggleSecretKey');
    if (toggleSecretKeyBtn) {
        toggleSecretKeyBtn.addEventListener('click', function () {
            const secretKeyInput = document.getElementById('secretKey');
            const eyeIcon = this.querySelector('i');
            
            if (secretKeyInput) {
                if (secretKeyInput.type === 'password') {
                    secretKeyInput.type = 'text';
                    eyeIcon.classList.remove('bi-eye');
                    eyeIcon.classList.add('bi-eye-slash');
                } else {
                    secretKeyInput.type = 'password';
                    eyeIcon.classList.remove('bi-eye-slash');
                    eyeIcon.classList.add('bi-eye');
                }
            }
        });
    }
    
    // Save API settings
    const saveApiSettingsBtn = document.getElementById('saveApiSettings');
    if (saveApiSettingsBtn) {
        saveApiSettingsBtn.addEventListener('click', function () {
            // Lấy các giá trị
            const apiKey = document.getElementById('apiKey')?.value;
            const secretKey = document.getElementById('secretKey')?.value;
            
            // Validate
            if (!apiKey || !secretKey) {
                showAlert('danger', 'Vui lòng nhập API Key và Secret Key');
                return;
            }
            
            // Hiển thị loading
            showLoading('Đang lưu cài đặt API...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.API_SETTINGS, {
                method: 'POST',
                body: JSON.stringify({
                    api_key: apiKey,
                    secret_key: secretKey
                })
            }, false)
                .then(data => {
                    hideLoading();
                    showAlert('success', 'Cài đặt API đã được lưu thành công!');
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
    
    // Test API connection
    const testApiConnectionBtn = document.getElementById('testApiConnection');
    if (testApiConnectionBtn) {
        testApiConnectionBtn.addEventListener('click', function () {
            // Lấy các giá trị
            const apiKey = document.getElementById('apiKey')?.value;
            const secretKey = document.getElementById('secretKey')?.value;
            
            // Validate
            if (!apiKey || !secretKey) {
                showAlert('danger', 'Vui lòng nhập API Key và Secret Key');
                return;
            }
            
            // Hiển thị loading
            showLoading('Đang kiểm tra kết nối API...');
            
            // Cập nhật trạng thái nút
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Đang kiểm tra...';
            this.disabled = true;
            
            // Hiển thị trạng thái API
            const apiStatusElem = document.getElementById('apiConnectionStatus');
            if (apiStatusElem) {
                apiStatusElem.innerHTML = '<span class="badge bg-warning">Đang kiểm tra...</span>';
            }
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.TEST_API_CONNECTION, {
                method: 'POST',
                body: JSON.stringify({
                    api_key: apiKey,
                    secret_key: secretKey
                })
            }, false)
                .then(data => {
                    hideLoading();
                    
                    // Khôi phục nút
                    this.innerHTML = originalText;
                    this.disabled = false;
                    
                    // Hiển thị thông báo thành công
                    showAlert('success', 'Kết nối API thành công!');
                    
                    // Cập nhật trạng thái API
                    if (apiStatusElem) {
                        apiStatusElem.innerHTML = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Kết nối thành công</span>';
                    }
                    
                    // Cập nhật trạng thái kết nối API trên toàn bộ giao diện
                    const apiStatusBadges = document.querySelectorAll('.status-badge');
                    apiStatusBadges.forEach(badge => {
                        if (badge.classList.contains('connected') || badge.classList.contains('disconnected')) {
                            badge.classList.remove('disconnected');
                            badge.classList.add('connected');
                            
                            // Cập nhật nội dung
                            const badgeIcon = badge.querySelector('i');
                            if (badgeIcon) {
                                badgeIcon.classList.remove('bi-plug');
                                badgeIcon.classList.add('bi-plug-fill');
                            }
                            
                            // Cập nhật text
                            badge.innerHTML = badge.innerHTML.replace('Chưa kết nối', 'Đã kết nối');
                        }
                    });
                    
                    // Thay đổi nút từ "Lưu cấu hình API" thành "Đã kết nối"
                    const saveApiBtn = document.getElementById('saveApiSettings');
                    if (saveApiBtn) {
                        saveApiBtn.innerHTML = '<i class="bi bi-check-circle me-2"></i>Đã kết nối';
                        saveApiBtn.classList.remove('btn-primary');
                        saveApiBtn.classList.add('btn-success');
                    }
                })
                .catch((error, errorMessage) => {
                    hideLoading();
                    
                    // Khôi phục nút
                    this.innerHTML = originalText;
                    this.disabled = false;
                    
                    // Cập nhật trạng thái API
                    if (apiStatusElem) {
                        apiStatusElem.innerHTML = `<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Kết nối thất bại</span>`;
                    }
                    
                    // Hiển thị thông báo lỗi chi tiết
                    if (error.message) {
                        if (error.message.includes('HTTP error! Status: 404')) {
                            // Hiển thị thông báo lỗi về API không tồn tại
                            showAlert('danger', 'API endpoint kiểm tra kết nối không tồn tại. Vui lòng liên hệ quản trị viên.', 10000);
                            console.error('API endpoint not found:', API_ENDPOINTS.TEST_API_CONNECTION);
                            
                            // Hiển thị gợi ý trên giao diện
                            apiStatusElem.innerHTML = `
                                <div class="api-status api-status-error p-3 mb-2">
                                    <h6 class="error-text mb-2"><i class="bi bi-exclamation-triangle-fill me-2"></i>Lỗi API 404</h6>
                                    <p class="mb-2">API endpoint kiểm tra kết nối không tồn tại. Endpoint: <code>${API_ENDPOINTS.TEST_API_CONNECTION}</code></p>
                                    <div class="alert alert-info small mb-0">
                                        <i class="bi bi-info-circle me-1"></i> Gợi ý: Kiểm tra phiên bản API (v1/v2) hoặc cài đặt server API.
                                    </div>
                                </div>
                                <div style="height:80px"></div><!-- Tạo khoảng trống cố định không gây lấn xuống -->`;
                        } else {
                            // Hiển thị các lỗi khác
                            apiStatusElem.innerHTML = `
                                <div class="api-status api-status-error p-3 mb-2">
                                    <h6 class="error-text mb-2"><i class="bi bi-exclamation-triangle-fill me-2"></i>Lỗi kết nối API</h6>
                                    <p class="mb-0">${error.message}</p>
                                </div>
                                <div style="height:80px"></div><!-- Tạo khoảng trống cố định không gây lấn xuống -->`;
                        }
                    }
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Quản lý rủi ro
 */
function setupRiskSettingsHandlers() {
    // Risk per trade slider
    const riskPerTradeSlider = document.getElementById('riskPerTrade');
    const riskPerTradeValue = document.getElementById('riskPerTradeValue');
    
    if (riskPerTradeSlider && riskPerTradeValue) {
        riskPerTradeSlider.addEventListener('input', function () {
            riskPerTradeValue.textContent = this.value + '%';
        });
    }
    
    // Max positions slider
    const maxPositionsSlider = document.getElementById('maxPositions');
    const maxPositionsValue = document.getElementById('maxPositionsValue');
    
    if (maxPositionsSlider && maxPositionsValue) {
        maxPositionsSlider.addEventListener('input', function () {
            maxPositionsValue.textContent = this.value;
        });
    }
    
    // Max risk total slider
    const maxRiskTotalSlider = document.getElementById('maxRiskTotal');
    const maxRiskTotalValue = document.getElementById('maxRiskTotalValue');
    
    if (maxRiskTotalSlider && maxRiskTotalValue) {
        maxRiskTotalSlider.addEventListener('input', function () {
            maxRiskTotalValue.textContent = this.value + '%';
        });
    }
    
    // Save risk settings
    const saveRiskSettingsBtn = document.getElementById('saveRiskSettings');
    if (saveRiskSettingsBtn) {
        saveRiskSettingsBtn.addEventListener('click', function () {
            // Lấy các giá trị
            const riskPerTrade = riskPerTradeSlider?.value;
            const maxPositions = maxPositionsSlider?.value;
            const maxRiskTotal = maxRiskTotalSlider?.value;
            
            // Hiển thị loading
            showLoading('Đang lưu cài đặt quản lý rủi ro...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.RISK_SETTINGS, {
                method: 'POST',
                body: JSON.stringify({
                    risk_per_trade: riskPerTrade,
                    max_positions: maxPositions,
                    max_risk_total: maxRiskTotal
                })
            }, false)
                .then(data => {
                    hideLoading();
                    showAlert('success', 'Cài đặt quản lý rủi ro đã được lưu thành công!');
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Telegram
 */
function setupTelegramSettingsHandlers() {
    // Toggle Telegram settings visibility
    const telegramEnabledSwitch = document.getElementById('telegramEnabledSwitch');
    const telegramSettings = document.getElementById('telegramSettings');
    
    if (telegramEnabledSwitch && telegramSettings) {
        telegramEnabledSwitch.addEventListener('change', function () {
            telegramSettings.style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Save Telegram settings
    const saveTelegramSettingsBtn = document.getElementById('saveTelegramSettings');
    if (saveTelegramSettingsBtn) {
        saveTelegramSettingsBtn.addEventListener('click', function () {
            // Check if Telegram is enabled
            if (!telegramEnabledSwitch?.checked) {
                showAlert('success', 'Cài đặt Telegram đã được lưu. Thông báo Telegram đã tắt.');
                return;
            }
            
            // Lấy các giá trị
            const botToken = document.getElementById('telegramBotToken')?.value;
            const chatId = document.getElementById('telegramChatId')?.value;
            
            // Validate
            if (!botToken || !chatId) {
                showAlert('danger', 'Vui lòng nhập Bot Token và Chat ID');
                return;
            }
            
            // Hiển thị loading
            showLoading('Đang lưu cài đặt Telegram...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.TELEGRAM_SETTINGS, {
                method: 'POST',
                body: JSON.stringify({
                    enabled: true,
                    bot_token: botToken,
                    chat_id: chatId
                })
            }, false)
                .then(data => {
                    hideLoading();
                    showAlert('success', 'Cài đặt Telegram đã được lưu thành công!');
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
    
    // Test Telegram
    const testTelegramBtn = document.getElementById('testTelegramBtn');
    if (testTelegramBtn) {
        testTelegramBtn.addEventListener('click', function () {
            // Lấy các giá trị
            const botToken = document.getElementById('telegramBotToken')?.value;
            const chatId = document.getElementById('telegramChatId')?.value;
            
            // Validate
            if (!botToken || !chatId) {
                showAlert('danger', 'Vui lòng nhập Bot Token và Chat ID');
                return;
            }
            
            // Hiển thị loading
            showLoading('Đang gửi tin nhắn test...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.TEST_TELEGRAM, {
                method: 'POST',
                body: JSON.stringify({
                    bot_token: botToken,
                    chat_id: chatId
                })
            }, false)
                .then(data => {
                    hideLoading();
                    if (data.success) {
                        showAlert('success', 'Tin nhắn test đã được gửi. Vui lòng kiểm tra Telegram của bạn.');
                    } else {
                        showAlert('danger', data.message || 'Không thể gửi tin nhắn test');
                    }
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Thông báo
 */
function setupNotificationSettingsHandlers() {
    // Save notification settings
    const saveNotificationSettingsBtn = document.getElementById('saveNotificationSettings');
    if (saveNotificationSettingsBtn) {
        saveNotificationSettingsBtn.addEventListener('click', function () {
            // Lấy các giá trị
            const notifyOnTrade = document.getElementById('notifyOnTrade')?.checked;
            const notifyOnStopLoss = document.getElementById('notifyOnStopLoss')?.checked;
            const notifyOnTakeProfit = document.getElementById('notifyOnTakeProfit')?.checked;
            const notifyOnSignal = document.getElementById('notifyOnSignal')?.checked;
            
            // Hiển thị loading
            showLoading('Đang lưu cài đặt thông báo...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.NOTIFICATION_SETTINGS, {
                method: 'POST',
                body: JSON.stringify({
                    notify_on_trade: notifyOnTrade,
                    notify_on_stop_loss: notifyOnStopLoss,
                    notify_on_take_profit: notifyOnTakeProfit,
                    notify_on_signal: notifyOnSignal
                })
            }, false)
                .then(data => {
                    hideLoading();
                    showAlert('success', 'Cài đặt thông báo đã được lưu thành công!');
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Tùy chọn nâng cao
 */
function setupAdvancedSettingsHandlers() {
    // Toggle trading time constraints
    const enableTradingTimeConstraint = document.getElementById('enableTradingTimeConstraint');
    const tradingTimeConstraints = document.getElementById('tradingTimeConstraints');
    
    if (enableTradingTimeConstraint && tradingTimeConstraints) {
        enableTradingTimeConstraint.addEventListener('change', function () {
            tradingTimeConstraints.style.display = this.checked ? 'flex' : 'none';
        });
    }
    
    // Save advanced settings
    const saveAdvancedSettingsBtn = document.getElementById('saveAdvancedSettings');
    if (saveAdvancedSettingsBtn) {
        saveAdvancedSettingsBtn.addEventListener('click', function () {
            // Lấy các giá trị
            const enableTradingTimeConstraint = document.getElementById('enableTradingTimeConstraint')?.checked;
            const tradingStartTime = document.getElementById('tradingStartTime')?.value;
            const tradingEndTime = document.getElementById('tradingEndTime')?.value;
            
            // Validate time constraints if enabled
            if (enableTradingTimeConstraint && (!tradingStartTime || !tradingEndTime)) {
                showAlert('danger', 'Vui lòng nhập thời gian bắt đầu và kết thúc giao dịch');
                return;
            }
            
            // Hiển thị loading
            showLoading('Đang lưu cài đặt nâng cao...');
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.ADVANCED_SETTINGS, {
                method: 'POST',
                body: JSON.stringify({
                    enable_trading_time_constraint: enableTradingTimeConstraint,
                    trading_start_time: tradingStartTime,
                    trading_end_time: tradingEndTime
                })
            }, false)
                .then(data => {
                    hideLoading();
                    showAlert('success', 'Cài đặt nâng cao đã được lưu thành công!');
                })
                .catch(() => {
                    hideLoading();
                    // Message already shown by fetchAPI
                });
        });
    }
}

/**
 * Thiết lập các handler cho phần Nhật ký hệ thống
 */
function setupLogsHandlers() {
    // Refresh logs
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', function () {
            const logContent = document.getElementById('logContent');
            if (!logContent) return;
            
            // Hiển thị loading trong container log
            logContent.innerHTML = '<div class="text-center my-3"><div class="spinner-border spinner-border-sm text-primary" role="status"></div><span class="ms-2">Đang tải...</span></div>';
            
            // Gửi API request
            fetchAPI(API_ENDPOINTS.LOG_ENTRIES, {
                method: 'GET'
            }, false)
                .then(data => {
                    if (data && data.logs) {
                        // Format log entries
                        const logEntries = data.logs.map(log => {
                            let levelClass = 'text-primary';
                            if (log.level === 'WARNING') levelClass = 'text-warning';
                            if (log.level === 'ERROR') levelClass = 'text-danger';
                            if (log.level === 'TRADE') levelClass = 'text-info';
                            
                            return `<div class="log-entry">
                                <span class="text-secondary">[${log.timestamp}]</span>
                                <span class="${levelClass}">[${log.level}]</span>
                                ${log.message}
                            </div>`;
                        }).join('\n');
                        
                        logContent.innerHTML = logEntries || '<div class="text-center">Không có dữ liệu nhật ký.</div>';
                        showAlert('success', 'Nhật ký đã được làm mới thành công!');
                    } else {
                        logContent.innerHTML = '<div class="text-center">Không có dữ liệu nhật ký.</div>';
                        showAlert('info', 'Không có nhật ký mới.');
                    }
                })
                .catch(error => {
                    logContent.innerHTML = '<div class="alert alert-danger">Có lỗi xảy ra khi tải nhật ký. Vui lòng thử lại sau.</div>';
                });
        });
    }
    
    // Download logs
    const downloadLogsBtn = document.getElementById('downloadLogsBtn');
    if (downloadLogsBtn) {
        downloadLogsBtn.addEventListener('click', function () {
            // Lấy nội dung log hoặc gửi request lấy toàn bộ log
            const logContent = document.getElementById('logContent')?.innerText || '';
            
            // Tạo blob và download
            const blob = new Blob([logContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = 'bot_logs_' + new Date().toISOString().split('T')[0] + '.txt';
            a.click();
            
            URL.revokeObjectURL(url);
            showAlert('success', 'Nhật ký đã được tải xuống thành công!');
        });
    }
    
    // Auto-refresh logs
    const autoRefreshLogs = document.getElementById('autoRefreshLogs');
    let logRefreshInterval;
    
    if (autoRefreshLogs) {
        autoRefreshLogs.addEventListener('change', function () {
            if (this.checked) {
                logRefreshInterval = setInterval(() => {
                    document.getElementById('refreshLogsBtn')?.click();
                }, 30000); // Refresh every 30 seconds
            } else {
                clearInterval(logRefreshInterval);
            }
        });
    }
}

/**
 * Thiết lập các phụ thuộc UI
 */
function setupUIDependencies() {
    // Thiết lập các phụ thuộc ban đầu
    const telegramEnabledSwitch = document.getElementById('telegramEnabledSwitch');
    const telegramSettings = document.getElementById('telegramSettings');
    
    if (telegramEnabledSwitch && telegramSettings) {
        telegramSettings.style.display = telegramEnabledSwitch.checked ? 'block' : 'none';
    }
    
    const enableTradingTimeConstraint = document.getElementById('enableTradingTimeConstraint');
    const tradingTimeConstraints = document.getElementById('tradingTimeConstraints');
    
    if (enableTradingTimeConstraint && tradingTimeConstraints) {
        tradingTimeConstraints.style.display = enableTradingTimeConstraint.checked ? 'flex' : 'none';
    }
}

/**
 * Thiết lập các nút toggle trên trang
 */
function setupToggles() {
    // Tìm tất cả các nút toggle và gắn sự kiện
    document.querySelectorAll('.form-check-input[type="checkbox"]').forEach(toggle => {
        if (toggle.id && toggle.id.includes('Switch') && !toggle.dataset.hasEventListener) {
            toggle.dataset.hasEventListener = true;
            
            // Thêm hiệu ứng khi toggle thay đổi
            toggle.addEventListener('change', function() {
                const toggleLabel = this.nextElementSibling;
                if (toggleLabel) {
                    toggleLabel.classList.add('opacity-75');
                    setTimeout(() => {
                        toggleLabel.classList.remove('opacity-75');
                    }, 300);
                }
                
                // Hiển thị thông báo thay đổi trạng thái
                const featureName = toggleLabel?.textContent?.trim() || 'Tính năng';
                if (this.checked) {
                    showAlert('success', `${featureName} đã được bật.`);
                } else {
                    showAlert('info', `${featureName} đã được tắt.`);
                }
            });
        }
    });
}

// Khởi tạo trang khi DOM đã load
document.addEventListener('DOMContentLoaded', initSettingsPage);

// Export các hàm để sử dụng từ module khác (nếu cần)
export {
    initSettingsPage,
    setupTradingCoinsHandlers,
    setupGeneralSettingsHandlers,
    setupApiSettingsHandlers,
    setupRiskSettingsHandlers,
    setupTelegramSettingsHandlers,
    setupNotificationSettingsHandlers,
    setupAdvancedSettingsHandlers,
    setupLogsHandlers
};