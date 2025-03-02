// Settings.js - JavaScript for the Settings page

// Settings manager
const settingsManager = {
    // Initialize the component
    init: function() {
        // Add event listeners for settings tabs
        document.querySelectorAll('.list-group-item[data-bs-toggle="list"]').forEach(tab => {
            tab.addEventListener('click', this.switchTab.bind(this));
        });
        
        // Add event listeners for form buttons
        document.getElementById('test-binance-api').addEventListener('click', this.testBinanceApi);
        document.getElementById('test-telegram-api').addEventListener('click', this.testTelegramApi);
        document.getElementById('save-api-settings').addEventListener('click', this.saveApiSettings);
        document.getElementById('save-trading-settings').addEventListener('click', this.saveTradingSettings);
        document.getElementById('reset-trading-settings').addEventListener('click', this.resetTradingSettings);
        document.getElementById('save-risk-settings').addEventListener('click', this.saveRiskSettings);
        document.getElementById('reset-risk-settings').addEventListener('click', this.resetRiskSettings);
        document.getElementById('save-notification-settings').addEventListener('click', this.saveNotificationSettings);
        document.getElementById('save-system-settings').addEventListener('click', this.saveSystemSettings);
        document.getElementById('clear-cache-btn').addEventListener('click', this.clearCache);
        document.getElementById('reset-system-btn').addEventListener('click', this.resetSystem);
        document.getElementById('create-backup-btn').addEventListener('click', this.createBackup);
        document.getElementById('restore-backup-btn').addEventListener('click', this.restoreBackup);
        document.getElementById('add-pair-btn').addEventListener('click', this.addCustomPair);
        
        // Add event listener for backup file selection
        const backupFileInput = document.getElementById('backup-file');
        if (backupFileInput) {
            backupFileInput.addEventListener('change', function() {
                document.getElementById('restore-backup-btn').disabled = !this.files.length;
            });
        }
        
        // Add event listener for trailing stop checkbox
        const trailingStopCheckbox = document.getElementById('use-trailing-stop');
        if (trailingStopCheckbox) {
            trailingStopCheckbox.addEventListener('change', function() {
                const trailingStopParams = document.getElementById('trailing-stop-params');
                trailingStopParams.style.display = this.checked ? 'block' : 'none';
            });
        }
        
        // Add event listener for email notifications checkbox
        const emailCheckbox = document.getElementById('enable-email');
        if (emailCheckbox) {
            emailCheckbox.addEventListener('change', function() {
                const emailInput = document.getElementById('email-address');
                const emailFrequency = document.getElementById('email-frequency');
                
                emailInput.disabled = !this.checked;
                emailFrequency.disabled = !this.checked;
            });
        }
        
        // Initialize email input state
        if (document.getElementById('enable-email') && !document.getElementById('enable-email').checked) {
            document.getElementById('email-address').disabled = true;
            document.getElementById('email-frequency').disabled = true;
        }
        
        // Setup toggle bot button
        document.getElementById('toggle-bot').addEventListener('click', this.toggleBot);
        
        // Update bot status badge and toggle button
        this.updateBotStatus();
        
        // Load settings from the server (or use defaults if no settings exist)
        this.loadSettings();
    },
    
    // Switch tabs
    switchTab: function(event) {
        // Get the target tab
        const targetTab = event.target.getAttribute('href');
        
        // Remove active class from all tabs
        document.querySelectorAll('.list-group-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to the clicked tab
        event.target.classList.add('active');
    },
    
    // Test Binance API connection
    testBinanceApi: function() {
        const apiKey = document.getElementById('binance-api-key').value;
        const apiSecret = document.getElementById('binance-api-secret').value;
        const useTestnet = document.getElementById('use-testnet').checked;
        
        if (!apiKey || !apiSecret) {
            alert('Please enter both API Key and API Secret.');
            return;
        }
        
        // In a real implementation, this would send a request to the server to test the API connection
        console.log('Testing Binance API connection...');
        console.log('API Key:', apiKey);
        console.log('Use Testnet:', useTestnet);
        
        // Simulate API test
        setTimeout(() => {
            alert('Binance API connection successful!');
        }, 1000);
    },
    
    // Test Telegram API connection
    testTelegramApi: function() {
        const botToken = document.getElementById('telegram-bot-token').value;
        const chatId = document.getElementById('telegram-chat-id').value;
        
        if (!botToken || !chatId) {
            alert('Please enter both Bot Token and Chat ID.');
            return;
        }
        
        // Hiển thị đang xử lý
        const testButton = document.getElementById('test-telegram-api');
        const originalText = testButton.innerText;
        testButton.innerText = 'Đang gửi...';
        testButton.disabled = true;
        
        // Gửi yêu cầu đến server để test Telegram API thực tế
        fetch('/api/telegram/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token: botToken,
                chat_id: chatId
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Telegram test response:', data);
            if (data.status === 'success') {
                alert(data.message);
            } else {
                alert('Lỗi: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error testing Telegram API:', error);
            alert('Lỗi kết nối đến Telegram API: ' + error);
        })
        .finally(() => {
            // Khôi phục trạng thái nút
            testButton.innerText = originalText;
            testButton.disabled = false;
        });
    },
    
    // Save API settings
    saveApiSettings: function() {
        const apiKey = document.getElementById('binance-api-key').value;
        const apiSecret = document.getElementById('binance-api-secret').value;
        const useTestnet = document.getElementById('use-testnet').checked;
        const botToken = document.getElementById('telegram-bot-token').value;
        const chatId = document.getElementById('telegram-chat-id').value;
        
        // Validate inputs
        if (!apiKey || !apiSecret) {
            alert('Please enter both Binance API Key and API Secret.');
            return;
        }
        
        // Create settings object
        const settings = {
            binance: {
                apiKey: apiKey,
                apiSecret: apiSecret,
                useTestnet: useTestnet
            },
            telegram: {
                botToken: botToken,
                chatId: chatId,
                enabled: !!(botToken && chatId)
            }
        };
        
        // In a real implementation, this would send the settings to the server
        console.log('Saving API settings:', settings);
        
        // Show success message
        alert('API settings saved successfully!');
    },
    
    // Save trading settings
    saveTradingSettings: function() {
        // Get selected trading pairs
        const tradingPairsSelect = document.getElementById('trading-pairs');
        const selectedPairs = Array.from(tradingPairsSelect.selectedOptions).map(option => option.value);
        
        // Get selected timeframes
        const timeframes = [];
        document.querySelectorAll('input[id^="timeframe-"]').forEach(checkbox => {
            if (checkbox.checked) {
                timeframes.push(checkbox.id.replace('timeframe-', ''));
            }
        });
        
        // Get other trading settings
        const primaryTimeframe = document.getElementById('primary-timeframe').value;
        const orderUpdateInterval = document.getElementById('order-update-interval').value;
        const marketScanInterval = document.getElementById('market-scan-interval').value;
        const autoRestart = document.getElementById('auto-restart').checked;
        const logDebugInfo = document.getElementById('log-debug-info').checked;
        
        // Validate inputs
        if (selectedPairs.length === 0) {
            alert('Please select at least one trading pair.');
            return;
        }
        
        if (timeframes.length === 0) {
            alert('Please select at least one timeframe.');
            return;
        }
        
        // Create settings object
        const settings = {
            tradingPairs: selectedPairs,
            timeframes: timeframes,
            primaryTimeframe: primaryTimeframe,
            orderUpdateInterval: parseInt(orderUpdateInterval),
            marketScanInterval: parseInt(marketScanInterval),
            autoRestart: autoRestart,
            logDebugInfo: logDebugInfo
        };
        
        // In a real implementation, this would send the settings to the server
        console.log('Saving trading settings:', settings);
        
        // Show success message
        alert('Trading settings saved successfully!');
    },
    
    // Reset trading settings to defaults
    resetTradingSettings: function() {
        if (confirm('Are you sure you want to reset all trading settings to default values?')) {
            // Reset trading pairs
            const tradingPairsSelect = document.getElementById('trading-pairs');
            for (let i = 0; i < tradingPairsSelect.options.length; i++) {
                tradingPairsSelect.options[i].selected = tradingPairsSelect.options[i].value === 'BTCUSDT' || tradingPairsSelect.options[i].value === 'ETHUSDT';
            }
            
            // Reset timeframes
            document.querySelectorAll('input[id^="timeframe-"]').forEach(checkbox => {
                checkbox.checked = checkbox.id === 'timeframe-15m' || checkbox.id === 'timeframe-1h' || checkbox.id === 'timeframe-4h' || checkbox.id === 'timeframe-1d';
            });
            
            // Reset other trading settings
            document.getElementById('primary-timeframe').value = '1h';
            document.getElementById('order-update-interval').value = '5';
            document.getElementById('market-scan-interval').value = '15';
            document.getElementById('auto-restart').checked = true;
            document.getElementById('log-debug-info').checked = false;
            
            alert('Trading settings have been reset to default values.');
        }
    },
    
    // Save risk settings
    saveRiskSettings: function() {
        // Get risk settings
        const riskPerTrade = document.getElementById('risk-per-trade').value;
        const maxOpenPositions = document.getElementById('max-open-positions').value;
        const leverage = document.getElementById('leverage').value;
        const marginType = document.getElementById('margin-type').value;
        const automaticPositionSizing = document.getElementById('automatic-position-sizing').checked;
        const takeProfit = document.getElementById('take-profit').value;
        const stopLoss = document.getElementById('stop-loss').value;
        const useTrailingStop = document.getElementById('use-trailing-stop').checked;
        const trailingStart = document.getElementById('trailing-start').value;
        const trailingDistance = document.getElementById('trailing-distance').value;
        const dailyLossLimit = document.getElementById('daily-loss-limit').value;
        const weeklyLossLimit = document.getElementById('weekly-loss-limit').value;
        const resetLimitsAfterProfit = document.getElementById('reset-limits-after-profit').checked;
        
        // Create settings object
        const settings = {
            riskPerTrade: parseFloat(riskPerTrade),
            maxOpenPositions: parseInt(maxOpenPositions),
            leverage: parseInt(leverage),
            marginType: marginType,
            automaticPositionSizing: automaticPositionSizing,
            takeProfit: parseFloat(takeProfit),
            stopLoss: parseFloat(stopLoss),
            trailingStop: {
                enabled: useTrailingStop,
                activationThreshold: parseFloat(trailingStart),
                distance: parseFloat(trailingDistance)
            },
            riskLimits: {
                dailyLossLimit: parseFloat(dailyLossLimit),
                weeklyLossLimit: parseFloat(weeklyLossLimit),
                resetAfterProfit: resetLimitsAfterProfit
            }
        };
        
        // In a real implementation, this would send the settings to the server
        console.log('Saving risk settings:', settings);
        
        // Show success message
        alert('Risk settings saved successfully!');
    },
    
    // Reset risk settings to defaults
    resetRiskSettings: function() {
        if (confirm('Are you sure you want to reset all risk settings to default values?')) {
            // Reset risk settings
            document.getElementById('risk-per-trade').value = '1.0';
            document.getElementById('max-open-positions').value = '3';
            document.getElementById('leverage').value = '3';
            document.getElementById('margin-type').value = 'isolated';
            document.getElementById('automatic-position-sizing').checked = true;
            document.getElementById('take-profit').value = '2.5';
            document.getElementById('stop-loss').value = '1.5';
            document.getElementById('use-trailing-stop').checked = true;
            document.getElementById('trailing-start').value = '1.0';
            document.getElementById('trailing-distance').value = '0.5';
            document.getElementById('daily-loss-limit').value = '5';
            document.getElementById('weekly-loss-limit').value = '10';
            document.getElementById('reset-limits-after-profit').checked = true;
            
            // Show trailing stop params
            document.getElementById('trailing-stop-params').style.display = 'block';
            
            alert('Risk settings have been reset to default values.');
        }
    },
    
    // Save notification settings
    saveNotificationSettings: function() {
        // Get notification settings
        const notifyTrades = document.getElementById('notify-trades').checked;
        const notifySignals = document.getElementById('notify-signals').checked;
        const notifyErrors = document.getElementById('notify-errors').checked;
        const notifyDailySummary = document.getElementById('notify-daily-summary').checked;
        const minimalNotifications = document.getElementById('minimal-notifications').checked;
        const enableEmail = document.getElementById('enable-email').checked;
        const emailAddress = document.getElementById('email-address').value;
        const emailFrequency = document.getElementById('email-frequency').value;
        
        // Validate inputs
        if (enableEmail && !emailAddress) {
            alert('Please enter an email address or disable email notifications.');
            return;
        }
        
        // Create settings object
        const settings = {
            telegram: {
                notifyTrades: notifyTrades,
                notifySignals: notifySignals,
                notifyErrors: notifyErrors,
                notifyDailySummary: notifyDailySummary,
                minimalNotifications: minimalNotifications
            },
            email: {
                enabled: enableEmail,
                address: emailAddress,
                frequency: emailFrequency
            }
        };
        
        // In a real implementation, this would send the settings to the server
        console.log('Saving notification settings:', settings);
        
        // Show success message
        alert('Notification settings saved successfully!');
    },
    
    // Save system settings
    saveSystemSettings: function() {
        // Get system settings
        const refreshInterval = document.getElementById('refresh-interval').value;
        const language = document.getElementById('language').value;
        const logLevel = document.getElementById('log-level').value;
        const logRetention = document.getElementById('log-retention').value;
        const optimizeMemory = document.getElementById('optimize-memory').checked;
        
        // Create settings object
        const settings = {
            ui: {
                refreshInterval: parseInt(refreshInterval),
                language: language
            },
            system: {
                logLevel: logLevel,
                logRetention: parseInt(logRetention),
                optimizeMemory: optimizeMemory
            }
        };
        
        // Hiển thị đang xử lý
        const saveButton = document.getElementById('save-system-settings');
        const originalText = saveButton.innerText;
        saveButton.innerText = 'Đang lưu...';
        saveButton.disabled = true;
        
        // Thay đổi ngôn ngữ
        if (language) {
            // Gửi yêu cầu thay đổi ngôn ngữ
            fetch('/api/language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    language: language
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Language change response:', data);
                if (data.status === 'success') {
                    console.log('Language changed successfully');
                    // Reload trang để áp dụng ngôn ngữ mới
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                } else {
                    alert('Lỗi: ' + data.message);
                    // Khôi phục nút
                    saveButton.innerText = originalText;
                    saveButton.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error changing language:', error);
                alert('Lỗi khi thay đổi ngôn ngữ: ' + error);
                // Khôi phục nút
                saveButton.innerText = originalText;
                saveButton.disabled = false;
            });
        } else {
            // Không thay đổi ngôn ngữ, chỉ lưu các cài đặt khác
            console.log('Saving system settings:', settings);
            alert('Cài đặt hệ thống đã được lưu!');
            // Khôi phục trạng thái nút
            saveButton.innerText = originalText;
            saveButton.disabled = false;
        }
    },
    
    // Clear cache
    clearCache: function() {
        if (confirm('Are you sure you want to clear all cached data? This will not affect your settings or trade history.')) {
            // In a real implementation, this would send a request to the server to clear the cache
            console.log('Clearing cache...');
            
            // Show success message
            setTimeout(() => {
                alert('Cache cleared successfully!');
            }, 1000);
        }
    },
    
    // Reset system
    resetSystem: function() {
        if (confirm('WARNING: Are you sure you want to reset the entire system? This will clear all settings, strategies, and cached data. Trade history will be preserved.')) {
            // In a real implementation, this would send a request to the server to reset the system
            console.log('Resetting system...');
            
            // Show success message
            setTimeout(() => {
                alert('System reset successfully! The page will now reload.');
                window.location.reload();
            }, 1500);
        }
    },
    
    // Create backup
    createBackup: function() {
        // Get backup settings
        const includeTradeHistory = document.getElementById('include-trade-history').checked;
        const includeApiKeys = document.getElementById('include-api-keys').checked;
        
        // In a real implementation, this would send a request to the server to create a backup
        console.log('Creating backup...');
        console.log('Include trade history:', includeTradeHistory);
        console.log('Include API keys:', includeApiKeys);
        
        // Simulate backup creation
        setTimeout(() => {
            // Create a download link
            const link = document.createElement('a');
            link.href = '#';
            link.download = 'crypto_bot_backup_' + new Date().toISOString().slice(0, 10) + '.json';
            
            // Add event to simulate download
            link.addEventListener('click', function(e) {
                e.preventDefault();
                alert('Backup file downloaded successfully!');
            });
            
            // Click the link to start download
            link.click();
        }, 1500);
    },
    
    // Restore backup
    restoreBackup: function() {
        const backupFile = document.getElementById('backup-file').files[0];
        const overwriteExisting = document.getElementById('overwrite-existing').checked;
        
        if (!backupFile) {
            alert('Please select a backup file to restore.');
            return;
        }
        
        // In a real implementation, this would upload the file to the server
        console.log('Restoring from backup...');
        console.log('File:', backupFile.name);
        console.log('Overwrite existing:', overwriteExisting);
        
        // Simulate backup restoration
        setTimeout(() => {
            alert('Settings restored successfully! The page will now reload.');
            window.location.reload();
        }, 2000);
    },
    
    // Add custom trading pair
    addCustomPair: function() {
        const pairName = prompt('Enter the trading pair symbol (e.g., AVAXUSDT):');
        
        if (pairName) {
            // Check if the pair already exists
            const tradingPairsSelect = document.getElementById('trading-pairs');
            const existingOption = Array.from(tradingPairsSelect.options).find(option => option.value === pairName);
            
            if (existingOption) {
                alert('This trading pair already exists in the list.');
                existingOption.selected = true;
                return;
            }
            
            // Add the new pair to the select element
            const option = document.createElement('option');
            option.value = pairName;
            option.text = pairName.replace('USDT', '/USDT');
            option.selected = true;
            tradingPairsSelect.add(option);
        }
    },
    
    // Load settings from the server
    loadSettings: function() {
        // In a real implementation, this would fetch settings from the server
        console.log('Loading settings...');
        
        // For now, we'll use default values (already set in HTML)
    },
    
    // Update bot status
    updateBotStatus: function() {
        // In a real implementation, this would fetch the bot status from the server
        const botStatusBadge = document.getElementById('bot-status-badge');
        const toggleBotButton = document.getElementById('toggle-bot');
        
        // Fetch bot status
        fetch('/api/bot/status')
            .then(response => response.json())
            .then(data => {
                // Update badge
                botStatusBadge.textContent = data.running ? 'Running' : 'Stopped';
                botStatusBadge.className = data.running ? 'badge bg-success me-2' : 'badge bg-danger me-2';
                
                // Update button
                toggleBotButton.textContent = data.running ? 'Stop Bot' : 'Start Bot';
                toggleBotButton.className = data.running ? 'btn btn-sm btn-outline-danger' : 'btn btn-sm btn-outline-success';
            })
            .catch(error => console.error('Error fetching bot status:', error));
    },
    
    // Toggle bot
    toggleBot: function() {
        const action = this.textContent === 'Stop Bot' ? 'stop' : 'start';
        
        // Send API request to control bot
        fetch('/api/bot/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: action })
        })
        .then(response => response.json())
        .then(data => {
            // Update status after toggling
            settingsManager.updateBotStatus();
        })
        .catch(error => console.error('Error:', error));
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings manager
    settingsManager.init();
});