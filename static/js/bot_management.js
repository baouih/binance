// Bot Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const botsTableBody = document.getElementById('bots-table-body');
    const lastUpdateTime = document.getElementById('last-update-time');
    const totalBotsCount = document.getElementById('total-bots-count');
    const runningBotsCount = document.getElementById('running-bots-count');
    const stoppedBotsCount = document.getElementById('stopped-bots-count');
    const errorBotsCount = document.getElementById('error-bots-count');
    const createBotBtn = document.getElementById('create-bot-btn');
    const searchBotInput = document.getElementById('search-bot');
    
    // Create Bot Modal elements
    const botNameInput = document.getElementById('bot-name');
    const tradingPairSelect = document.getElementById('trading-pair');
    const timeframeSelect = document.getElementById('timeframe');
    const strategySelect = document.getElementById('strategy');
    const riskLevelSelect = document.getElementById('risk-level');
    const positionSizeInput = document.getElementById('position-size');
    const autoStartCheckbox = document.getElementById('auto-start');
    const autoAdjustParamsCheckbox = document.getElementById('auto-adjust-params');
    const enableNotificationsCheckbox = document.getElementById('enable-notifications');
    
    // Bot Details Modal elements
    const botDetailsModal = new bootstrap.Modal(document.getElementById('botDetailsModal'));
    const botDetailsContent = document.getElementById('bot-details-content');
    const editBotBtn = document.getElementById('edit-bot-btn');
    
    // Add event listeners
    if (createBotBtn) {
        createBotBtn.addEventListener('click', createBot);
    }
    
    if (searchBotInput) {
        searchBotInput.addEventListener('input', filterBots);
    }
    
    // Initialize - load bots list
    loadBots();
    
    // Refresh bots data every 30 seconds
    setInterval(loadBots, 30000);
    
    // Functions
    function loadBots() {
        if (!botsTableBody) return;
        
        // Show loading
        botsTableBody.innerHTML = `
            <tr class="text-center">
                <td colspan="6" class="py-3">
                    <div class="spinner-border spinner-border-sm text-primary me-2" role="status">
                        <span class="visually-hidden">Đang tải...</span>
                    </div>
                    <span>Đang tải danh sách bot...</span>
                </td>
            </tr>
        `;
        
        // Fetch bots data
        fetch('/api/bots')
            .then(response => response.json())
            .then(data => {
                if (data.bots && Array.isArray(data.bots)) {
                    updateBotsTable(data.bots);
                    updateBotsCounters(data.bots);
                    
                    // Update last updated time
                    if (lastUpdateTime) {
                        const now = new Date();
                        lastUpdateTime.textContent = now.toLocaleTimeString();
                    }
                } else {
                    showError('Định dạng dữ liệu không hợp lệ');
                }
            })
            .catch(error => {
                console.error('Error loading bots:', error);
                showError('Lỗi kết nối: ' + error.message);
            });
    }
    
    function updateBotsTable(bots) {
        if (!botsTableBody) return;
        
        if (bots.length === 0) {
            botsTableBody.innerHTML = `
                <tr class="text-center">
                    <td colspan="6" class="py-3">
                        <div class="text-muted">
                            <i class="fas fa-robot fa-2x mb-2"></i>
                            <p>Chưa có bot nào được tạo</p>
                            <button type="button" class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#createBotModal">
                                <i class="fas fa-plus me-1"></i> Tạo Bot mới
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        botsTableBody.innerHTML = '';
        
        bots.forEach(bot => {
            const row = document.createElement('tr');
            
            // Status badge
            let statusBadge = '';
            if (bot.status === 'running') {
                statusBadge = '<span class="badge bg-success">Đang chạy</span>';
            } else if (bot.status === 'stopped') {
                statusBadge = '<span class="badge bg-secondary">Đã dừng</span>';
            } else if (bot.status === 'error') {
                statusBadge = '<span class="badge bg-danger">Lỗi</span>';
            } else if (bot.status === 'restarting') {
                statusBadge = '<span class="badge bg-warning text-dark">Đang khởi động lại</span>';
            }
            
            // Control buttons
            let controlButtons = '';
            
            if (bot.status === 'running') {
                controlButtons = `
                    <button type="button" class="btn btn-sm btn-outline-danger bot-control-button me-1" data-action="stop" data-bot-id="${bot.id}">
                        <i class="fas fa-stop"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-warning bot-control-button me-1" data-action="restart" data-bot-id="${bot.id}">
                        <i class="fas fa-sync"></i>
                    </button>
                `;
            } else if (bot.status === 'stopped' || bot.status === 'error') {
                controlButtons = `
                    <button type="button" class="btn btn-sm btn-outline-success bot-control-button me-1" data-action="start" data-bot-id="${bot.id}">
                        <i class="fas fa-play"></i>
                    </button>
                `;
            } else if (bot.status === 'restarting') {
                controlButtons = `
                    <button type="button" class="btn btn-sm btn-outline-secondary bot-control-button me-1" disabled>
                        <i class="fas fa-spinner fa-spin"></i>
                    </button>
                `;
            }
            
            // View and delete buttons
            controlButtons += `
                <button type="button" class="btn btn-sm btn-outline-info bot-control-button me-1" data-action="view" data-bot-id="${bot.id}">
                    <i class="fas fa-eye"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-danger bot-control-button" data-action="delete" data-bot-id="${bot.id}">
                    <i class="fas fa-trash"></i>
                </button>
            `;
            
            // Format uptime
            let uptimeText = '-';
            if (bot.uptime_seconds) {
                const hours = Math.floor(bot.uptime_seconds / 3600);
                const minutes = Math.floor((bot.uptime_seconds % 3600) / 60);
                
                if (hours > 0) {
                    uptimeText = `${hours}h ${minutes}m`;
                } else {
                    uptimeText = `${minutes}m`;
                }
            }
            
            row.innerHTML = `
                <td>
                    <div class="d-flex align-items-center">
                        <span class="me-2">${bot.name}</span>
                        ${bot.has_notifications ? '<i class="fas fa-bell text-warning small" title="Thông báo đang bật"></i>' : ''}
                    </div>
                </td>
                <td>${bot.trading_pair}</td>
                <td>${bot.strategy}</td>
                <td>${statusBadge}</td>
                <td>${uptimeText}</td>
                <td>
                    <div class="btn-group" role="group">
                        ${controlButtons}
                    </div>
                </td>
            `;
            
            botsTableBody.appendChild(row);
        });
        
        // Add event listeners to control buttons
        document.querySelectorAll('.bot-control-button').forEach(button => {
            button.addEventListener('click', handleBotControl);
        });
    }
    
    function updateBotsCounters(bots) {
        if (totalBotsCount) {
            totalBotsCount.textContent = bots.length;
        }
        
        if (runningBotsCount) {
            const running = bots.filter(bot => bot.status === 'running').length;
            runningBotsCount.textContent = running;
        }
        
        if (stoppedBotsCount) {
            const stopped = bots.filter(bot => bot.status === 'stopped').length;
            stoppedBotsCount.textContent = stopped;
        }
        
        if (errorBotsCount) {
            const errors = bots.filter(bot => bot.status === 'error').length;
            errorBotsCount.textContent = errors;
        }
    }
    
    function handleBotControl(event) {
        const button = event.currentTarget;
        const action = button.getAttribute('data-action');
        const botId = button.getAttribute('data-bot-id');
        
        if (!action || !botId) return;
        
        if (action === 'view') {
            showBotDetails(botId);
            return;
        }
        
        if (action === 'delete') {
            // Confirm delete
            if (!confirm('Bạn có chắc muốn xóa bot này không?')) {
                return;
            }
        }
        
        // Show loading on button
        const originalHtml = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;
        
        // Send control request
        fetch(`/api/bots/${botId}/control`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: action })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('success', data.message || 'Thành công!');
                
                // Reload bots
                loadBots();
            } else {
                showToast('error', data.message || 'Đã xảy ra lỗi');
                
                // Restore button
                button.innerHTML = originalHtml;
                button.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error controlling bot:', error);
            showToast('error', 'Lỗi kết nối: ' + error.message);
            
            // Restore button
            button.innerHTML = originalHtml;
            button.disabled = false;
        });
    }
    
    function showBotDetails(botId) {
        if (!botDetailsContent) return;
        
        // Show loading
        botDetailsContent.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Đang tải...</span>
                </div>
                <p class="mt-2">Đang tải thông tin chi tiết...</p>
            </div>
        `;
        
        // Show modal
        botDetailsModal.show();
        
        // Fetch bot details
        fetch(`/api/bots/${botId}`)
            .then(response => response.json())
            .then(data => {
                if (data.bot) {
                    updateBotDetailsContent(data.bot);
                } else {
                    botDetailsContent.innerHTML = `
                        <div class="alert alert-danger">
                            Bot không tồn tại hoặc đã bị xóa.
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error loading bot details:', error);
                botDetailsContent.innerHTML = `
                    <div class="alert alert-danger">
                        Lỗi kết nối: ${error.message}
                    </div>
                `;
            });
    }
    
    function updateBotDetailsContent(bot) {
        if (!botDetailsContent) return;
        
        // Status badge
        let statusBadge = '';
        if (bot.status === 'running') {
            statusBadge = '<span class="badge bg-success">Đang chạy</span>';
        } else if (bot.status === 'stopped') {
            statusBadge = '<span class="badge bg-secondary">Đã dừng</span>';
        } else if (bot.status === 'error') {
            statusBadge = '<span class="badge bg-danger">Lỗi</span>';
        } else if (bot.status === 'restarting') {
            statusBadge = '<span class="badge bg-warning text-dark">Đang khởi động lại</span>';
        }
        
        // Format uptime
        let uptimeText = '-';
        if (bot.uptime_seconds) {
            const hours = Math.floor(bot.uptime_seconds / 3600);
            const minutes = Math.floor((bot.uptime_seconds % 3600) / 60);
            
            if (hours > 0) {
                uptimeText = `${hours} giờ ${minutes} phút`;
            } else {
                uptimeText = `${minutes} phút`;
            }
        }
        
        // Format performance
        let performanceText = '';
        if (bot.performance) {
            const profit = bot.performance.profit || 0;
            const profitClass = profit >= 0 ? 'text-success' : 'text-danger';
            const profitSign = profit >= 0 ? '+' : '';
            
            performanceText = `
                <div class="mt-4">
                    <h6>Hiệu suất</h6>
                    <div class="row">
                        <div class="col-md-3 mb-2">
                            <small class="text-muted d-block">Lợi nhuận</small>
                            <span class="${profitClass}">${profitSign}${profit.toFixed(2)}%</span>
                        </div>
                        <div class="col-md-3 mb-2">
                            <small class="text-muted d-block">Tổng giao dịch</small>
                            <span>${bot.performance.total_trades || 0}</span>
                        </div>
                        <div class="col-md-3 mb-2">
                            <small class="text-muted d-block">Thắng/Thua</small>
                            <span>${bot.performance.win_trades || 0}/${bot.performance.lose_trades || 0}</span>
                        </div>
                        <div class="col-md-3 mb-2">
                            <small class="text-muted d-block">Tỷ lệ thắng</small>
                            <span>${bot.performance.win_rate ? bot.performance.win_rate.toFixed(2) + '%' : '-'}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Render bot details
        botDetailsContent.innerHTML = `
            <div class="mb-4">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h4>${bot.name}</h4>
                        <div class="d-flex align-items-center">
                            ${statusBadge}
                            <span class="ms-2">${bot.trading_pair} (${bot.timeframe})</span>
                        </div>
                    </div>
                    <div class="text-end">
                        <small class="text-muted d-block">ID: ${bot.id}</small>
                        <small class="text-muted d-block">Tạo: ${new Date(bot.created_at).toLocaleString()}</small>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <h6>Cấu hình Bot</h6>
                    <table class="table table-sm table-dark">
                        <tbody>
                            <tr>
                                <td width="40%">Chiến lược</td>
                                <td>${bot.strategy}</td>
                            </tr>
                            <tr>
                                <td>Mức độ rủi ro</td>
                                <td>${bot.risk_level}</td>
                            </tr>
                            <tr>
                                <td>Kích thước vị thế</td>
                                <td>${bot.position_size}%</td>
                            </tr>
                            <tr>
                                <td>Thời gian hoạt động</td>
                                <td>${uptimeText}</td>
                            </tr>
                            <tr>
                                <td>Tự động điều chỉnh</td>
                                <td>${bot.auto_adjust_params ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-danger"></i>'}</td>
                            </tr>
                            <tr>
                                <td>Thông báo</td>
                                <td>${bot.has_notifications ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-danger"></i>'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="col-md-6">
                    <h6>Trạng thái hiện tại</h6>
                    <table class="table table-sm table-dark">
                        <tbody>
                            <tr>
                                <td width="40%">Trạng thái</td>
                                <td>${statusBadge}</td>
                            </tr>
                            <tr>
                                <td>Vị thế mở</td>
                                <td>${bot.open_positions || 0}</td>
                            </tr>
                            <tr>
                                <td>Lần cập nhật cuối</td>
                                <td>${bot.last_update ? new Date(bot.last_update).toLocaleString() : '-'}</td>
                            </tr>
                            <tr>
                                <td>Tín hiệu gần nhất</td>
                                <td>${bot.last_signal || '-'}</td>
                            </tr>
                            <tr>
                                <td>CPU/Memory</td>
                                <td>${bot.cpu_usage || '-'}% / ${bot.memory_usage || '-'} MB</td>
                            </tr>
                            <tr>
                                <td>API Mode</td>
                                <td>${bot.api_mode || 'demo'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            ${performanceText}
            
            ${bot.status === 'error' ? `
                <div class="alert alert-danger mt-4">
                    <h6><i class="fas fa-exclamation-triangle me-2"></i>Thông tin lỗi</h6>
                    <p class="mb-0">${bot.error_message || 'Không có chi tiết lỗi'}</p>
                </div>
            ` : ''}
            
            <div class="mt-4">
                <h6>Giao dịch gần đây</h6>
                ${bot.recent_trades && bot.recent_trades.length > 0 ? `
                    <div class="table-responsive">
                        <table class="table table-sm table-dark">
                            <thead>
                                <tr>
                                    <th>Thời gian</th>
                                    <th>Loại</th>
                                    <th>Giá</th>
                                    <th>Số lượng</th>
                                    <th>Trạng thái</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${bot.recent_trades.map(trade => `
                                    <tr>
                                        <td>${new Date(trade.time).toLocaleString()}</td>
                                        <td>${trade.side === 'BUY' ? '<span class="text-success">Mua</span>' : '<span class="text-danger">Bán</span>'}</td>
                                        <td>${trade.price}</td>
                                        <td>${trade.quantity}</td>
                                        <td>${trade.status}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                ` : '<p class="text-muted">Chưa có giao dịch nào</p>'}
            </div>
        `;
    }
    
    function createBot() {
        // Validate form
        if (!validateCreateBotForm()) {
            return;
        }
        
        // Get form values
        const botData = {
            name: botNameInput.value.trim(),
            trading_pair: tradingPairSelect.value,
            timeframe: timeframeSelect.value,
            strategy: strategySelect.value,
            risk_level: riskLevelSelect.value,
            position_size: parseFloat(positionSizeInput.value),
            auto_start: autoStartCheckbox.checked,
            auto_adjust_params: autoAdjustParamsCheckbox.checked,
            has_notifications: enableNotificationsCheckbox.checked
        };
        
        // Show loading
        createBotBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Đang tạo...';
        createBotBtn.disabled = true;
        
        // Send create request
        fetch('/api/bots', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(botData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('success', 'Đã tạo bot thành công!');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('createBotModal'));
                modal.hide();
                
                // Reset form
                resetCreateBotForm();
                
                // Reload bots
                loadBots();
            } else {
                showToast('error', data.message || 'Đã xảy ra lỗi khi tạo bot');
            }
            
            // Reset button
            createBotBtn.innerHTML = 'Tạo Bot';
            createBotBtn.disabled = false;
        })
        .catch(error => {
            console.error('Error creating bot:', error);
            showToast('error', 'Lỗi kết nối: ' + error.message);
            
            // Reset button
            createBotBtn.innerHTML = 'Tạo Bot';
            createBotBtn.disabled = false;
        });
    }
    
    function validateCreateBotForm() {
        let isValid = true;
        let errorMessage = '';
        
        // Validate required fields
        if (!botNameInput.value.trim()) {
            errorMessage = 'Vui lòng nhập tên bot';
            isValid = false;
        } else if (!tradingPairSelect.value) {
            errorMessage = 'Vui lòng chọn cặp giao dịch';
            isValid = false;
        } else if (!timeframeSelect.value) {
            errorMessage = 'Vui lòng chọn khung thời gian';
            isValid = false;
        } else if (!strategySelect.value) {
            errorMessage = 'Vui lòng chọn chiến lược giao dịch';
            isValid = false;
        } else if (!riskLevelSelect.value) {
            errorMessage = 'Vui lòng chọn mức độ rủi ro';
            isValid = false;
        }
        
        // Validate position size
        const positionSize = parseFloat(positionSizeInput.value);
        if (isNaN(positionSize) || positionSize < 1 || positionSize > 100) {
            errorMessage = 'Kích thước vị thế phải từ 1% đến 100%';
            isValid = false;
        }
        
        if (!isValid) {
            showToast('error', errorMessage);
        }
        
        return isValid;
    }
    
    function resetCreateBotForm() {
        if (botNameInput) botNameInput.value = '';
        if (tradingPairSelect) tradingPairSelect.value = '';
        if (timeframeSelect) timeframeSelect.value = '';
        if (strategySelect) strategySelect.value = '';
        if (riskLevelSelect) riskLevelSelect.value = '';
        if (positionSizeInput) positionSizeInput.value = '10';
        if (autoStartCheckbox) autoStartCheckbox.checked = true;
        if (autoAdjustParamsCheckbox) autoAdjustParamsCheckbox.checked = true;
        if (enableNotificationsCheckbox) enableNotificationsCheckbox.checked = true;
    }
    
    function filterBots() {
        if (!searchBotInput || !botsTableBody) return;
        
        const searchText = searchBotInput.value.toLowerCase();
        const rows = botsTableBody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const botName = row.querySelector('td:first-child')?.textContent.toLowerCase() || '';
            const tradingPair = row.querySelector('td:nth-child(2)')?.textContent.toLowerCase() || '';
            const strategy = row.querySelector('td:nth-child(3)')?.textContent.toLowerCase() || '';
            
            if (botName.includes(searchText) || tradingPair.includes(searchText) || strategy.includes(searchText)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    function showError(message) {
        if (!botsTableBody) return;
        
        botsTableBody.innerHTML = `
            <tr class="text-center">
                <td colspan="6" class="py-3">
                    <div class="alert alert-danger mb-0">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <span>${message}</span>
                    </div>
                </td>
            </tr>
        `;
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
});