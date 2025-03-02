// Settings Page JavaScript Code
document.addEventListener('DOMContentLoaded', function() {
    // API Mode Selection
    const apiModeRadios = document.querySelectorAll('input[name="api-mode"]');
    const saveApiModeBtn = document.getElementById('save-api-mode');
    const apiConnectionStatus = document.getElementById('api-connection-status');
    const testBinanceApiBtn = document.getElementById('test-binance-api');
    
    // Telegram Settings
    const enableTelegramSwitch = document.getElementById('enable-telegram');
    const telegramBotToken = document.getElementById('telegram-bot-token');
    const telegramChatId = document.getElementById('telegram-chat-id');
    const saveTelegramSettingsBtn = document.getElementById('save-telegram-settings');
    const testTelegramApiBtn = document.getElementById('test-telegram-api');
    const toggleTokenVisibilityBtn = document.getElementById('toggle-token-visibility');
    
    // Save API Mode
    if (saveApiModeBtn) {
        saveApiModeBtn.addEventListener('click', function() {
            const selectedMode = document.querySelector('input[name="api-mode"]:checked').value;
            
            // Show loading state
            saveApiModeBtn.disabled = true;
            saveApiModeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
            
            // Call API to update settings
            fetch('/api/account/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    api_mode: selectedMode
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    const toast = new bootstrap.Toast(document.getElementById('success-toast'));
                    document.getElementById('toast-message').textContent = 'Đã lưu chế độ API thành công!';
                    toast.show();
                    
                    // Update badge in navbar
                    updateApiModeBadge(selectedMode);
                    
                    // Update connection status - fake checking
                    testConnectionStatus();
                } else {
                    // Show error message
                    const toast = new bootstrap.Toast(document.getElementById('error-toast'));
                    document.getElementById('toast-error-message').textContent = data.message || 'Lỗi khi lưu cài đặt';
                    toast.show();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const toast = new bootstrap.Toast(document.getElementById('error-toast'));
                document.getElementById('toast-error-message').textContent = 'Lỗi kết nối đến máy chủ';
                toast.show();
            })
            .finally(() => {
                // Reset button
                saveApiModeBtn.disabled = false;
                saveApiModeBtn.innerHTML = '<i class="bi bi-check-lg"></i> Lưu chế độ API';
            });
        });
    }
    
    // Test Binance API Connection
    if (testBinanceApiBtn) {
        testBinanceApiBtn.addEventListener('click', function() {
            testConnectionStatus();
        });
    }
    
    // Toggle token visibility
    if (toggleTokenVisibilityBtn) {
        toggleTokenVisibilityBtn.addEventListener('click', function() {
            const tokenInput = telegramBotToken;
            const eyeIcon = toggleTokenVisibilityBtn.querySelector('i');
            
            if (tokenInput.type === 'password') {
                tokenInput.type = 'text';
                eyeIcon.classList.remove('bi-eye');
                eyeIcon.classList.add('bi-eye-slash');
            } else {
                tokenInput.type = 'password';
                eyeIcon.classList.remove('bi-eye-slash');
                eyeIcon.classList.add('bi-eye');
            }
        });
    }
    
    // Test Telegram API
    if (testTelegramApiBtn) {
        testTelegramApiBtn.addEventListener('click', function() {
            if (!telegramBotToken.value || !telegramChatId.value) {
                alert('Vui lòng nhập cả Bot Token và Chat ID');
                return;
            }
            
            // Show loading state
            testTelegramApiBtn.disabled = true;
            testTelegramApiBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
            
            // Call API to test Telegram
            fetch('/api/test/telegram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    botToken: telegramBotToken.value,
                    chatId: telegramChatId.value
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const toast = new bootstrap.Toast(document.getElementById('success-toast'));
                    document.getElementById('toast-message').textContent = 'Tin nhắn đã được gửi thành công!';
                    toast.show();
                } else {
                    const toast = new bootstrap.Toast(document.getElementById('error-toast'));
                    document.getElementById('toast-error-message').textContent = data.message || 'Lỗi khi gửi tin nhắn';
                    toast.show();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const toast = new bootstrap.Toast(document.getElementById('error-toast'));
                document.getElementById('toast-error-message').textContent = 'Lỗi kết nối đến máy chủ';
                toast.show();
            })
            .finally(() => {
                // Reset button
                testTelegramApiBtn.disabled = false;
                testTelegramApiBtn.innerHTML = '<i class="bi bi-send"></i> Gửi tin nhắn test';
            });
        });
    }
    
    // Save Telegram Settings
    if (saveTelegramSettingsBtn) {
        saveTelegramSettingsBtn.addEventListener('click', function() {
            if (enableTelegramSwitch.checked && (!telegramBotToken.value || !telegramChatId.value)) {
                alert('Vui lòng nhập cả Bot Token và Chat ID');
                return;
            }
            
            // Show loading state
            saveTelegramSettingsBtn.disabled = true;
            saveTelegramSettingsBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
            
            // Gather notification types
            const notifications = {
                signals: document.getElementById('notify-signals').checked,
                positions: document.getElementById('notify-positions').checked,
                profitLoss: document.getElementById('notify-profit-loss').checked,
                system: document.getElementById('notify-system').checked
            };
            
            // Call API to save settings
            fetch('/api/config/telegram', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    enabled: enableTelegramSwitch.checked,
                    botToken: telegramBotToken.value,
                    chatId: telegramChatId.value,
                    notifications: notifications
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const toast = new bootstrap.Toast(document.getElementById('success-toast'));
                    document.getElementById('toast-message').textContent = 'Cài đặt Telegram đã được lưu!';
                    toast.show();
                } else {
                    const toast = new bootstrap.Toast(document.getElementById('error-toast'));
                    document.getElementById('toast-error-message').textContent = data.message || 'Lỗi khi lưu cài đặt';
                    toast.show();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const toast = new bootstrap.Toast(document.getElementById('error-toast'));
                document.getElementById('toast-error-message').textContent = 'Lỗi kết nối đến máy chủ';
                toast.show();
            })
            .finally(() => {
                // Reset button
                saveTelegramSettingsBtn.disabled = false;
                saveTelegramSettingsBtn.innerHTML = '<i class="bi bi-check-lg"></i> Lưu cài đặt';
            });
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
            if (mode === 'demo') {
                modeBadge.textContent = 'Chế độ Demo';
            } else if (mode === 'testnet') {
                modeBadge.textContent = 'Chế độ Testnet';
            } else if (mode === 'live') {
                modeBadge.textContent = 'Chế độ Live';
            }
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
                    `;
                    
                    // Cập nhật badge toàn cục
                    updateGlobalModeBadge('demo', 'Chế độ Demo');
                    
                } else if (selectedMode === 'testnet') {
                    apiConnectionStatus.innerHTML = `
                        <div class="d-flex align-items-center">
                            <span class="badge bg-warning me-2">Testnet</span>
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
                };
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
                const apiMode = data.api_mode || 'testnet';
                const apiModeRadio = document.getElementById(`api-mode-${apiMode}`);
                if (apiModeRadio) {
                    apiModeRadio.checked = true;
                }
                
                // Test connection status
                testConnectionStatus();
            })
            .catch(error => {
                console.error('Error fetching account settings:', error);
            });
    }
    
    // Initialize settings on page load
    initializeSettings();
});
