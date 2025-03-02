// Bot Management JavaScript Code
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const botStatusCards = document.querySelectorAll('.bot-status-card');
    const botControlButtons = document.querySelectorAll('.bot-control-button');
    const createBotForm = document.getElementById('create-bot-form');
    
    // Initialize bot statuses with interval updates
    initializeBotStatuses();
    
    // Bot control buttons event listeners
    if (botControlButtons) {
        botControlButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const botId = this.dataset.botId;
                const action = this.dataset.action;
                
                // Show confirmation for critical actions
                if (action === 'stop' || action === 'delete') {
                    if (!confirm(`Bạn có chắc chắn muốn ${action === 'stop' ? 'dừng' : 'xóa'} bot này không?`)) {
                        return;
                    }
                }
                
                // Show loading state
                this.disabled = true;
                const originalText = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
                
                // Send control command to server
                controlBot(botId, action)
                    .then(response => {
                        if (response.success) {
                            // Update UI based on action
                            if (action === 'start') {
                                updateBotStatus(botId, 'running');
                            } else if (action === 'stop') {
                                updateBotStatus(botId, 'stopped');
                            } else if (action === 'restart') {
                                updateBotStatus(botId, 'restarting');
                                setTimeout(() => updateBotStatus(botId, 'running'), 3000);
                            } else if (action === 'delete') {
                                removeBotFromUI(botId);
                            }
                            
                            showToast('success', response.message || 'Thao tác thành công!');
                        } else {
                            showToast('error', response.message || 'Thao tác thất bại!');
                        }
                    })
                    .catch(error => {
                        console.error('Error controlling bot:', error);
                        showToast('error', 'Đã xảy ra lỗi khi gửi lệnh');
                    })
                    .finally(() => {
                        // Reset button state
                        this.disabled = false;
                        this.innerHTML = originalText;
                    });
            });
        });
    }
    
    // Create new bot form submission
    if (createBotForm) {
        createBotForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(this);
            const botData = {
                name: formData.get('bot-name'),
                strategy: formData.get('bot-strategy'),
                pairs: Array.from(document.getElementById('bot-pairs').selectedOptions).map(opt => opt.value),
                timeframe: formData.get('bot-timeframe'),
                risk_level: formData.get('bot-risk-level')
            };
            
            // Validate form data
            if (!botData.name || !botData.strategy || botData.pairs.length === 0) {
                showToast('error', 'Vui lòng điền đầy đủ thông tin bắt buộc');
                return;
            }
            
            // Show loading state
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang tạo...';
            
            // Send request to create bot
            createBot(botData)
                .then(response => {
                    if (response.success) {
                        // Close modal and refresh page
                        const modal = bootstrap.Modal.getInstance(document.getElementById('createBotModal'));
                        modal.hide();
                        
                        // Show success message and reload page after delay
                        showToast('success', 'Đã tạo bot mới thành công!');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        showToast('error', response.message || 'Không thể tạo bot mới');
                    }
                })
                .catch(error => {
                    console.error('Error creating bot:', error);
                    showToast('error', 'Đã xảy ra lỗi khi tạo bot mới');
                })
                .finally(() => {
                    // Reset button state
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Tạo Bot';
                });
        });
    }
    
    // API functions
    function controlBot(botId, action) {
        return fetch(`/api/bot/${botId}/control`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action })
        })
        .then(response => response.json());
    }
    
    function createBot(botData) {
        return fetch('/api/bot/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(botData)
        })
        .then(response => response.json());
    }
    
    function getBotStatus(botId) {
        return fetch(`/api/bot/${botId}/status`)
            .then(response => response.json());
    }
    
    // UI update functions
    function updateBotStatus(botId, status) {
        const statusCard = document.querySelector(`.bot-status-card[data-bot-id="${botId}"]`);
        if (!statusCard) return;
        
        // Remove all status classes
        statusCard.classList.remove('status-running', 'status-stopped', 'status-error', 'status-restarting');
        
        // Add appropriate status class
        statusCard.classList.add(`status-${status}`);
        
        // Update status text and icon
        const statusBadge = statusCard.querySelector('.status-badge');
        const statusIcon = statusCard.querySelector('.status-icon');
        
        if (status === 'running') {
            statusBadge.className = 'badge bg-success status-badge';
            statusBadge.textContent = 'Đang chạy';
            statusIcon.className = 'fas fa-circle-notch fa-spin text-success status-icon';
        } else if (status === 'stopped') {
            statusBadge.className = 'badge bg-secondary status-badge';
            statusBadge.textContent = 'Đã dừng';
            statusIcon.className = 'fas fa-stop-circle text-secondary status-icon';
        } else if (status === 'error') {
            statusBadge.className = 'badge bg-danger status-badge';
            statusBadge.textContent = 'Lỗi';
            statusIcon.className = 'fas fa-exclamation-circle text-danger status-icon';
        } else if (status === 'restarting') {
            statusBadge.className = 'badge bg-warning status-badge';
            statusBadge.textContent = 'Đang khởi động lại';
            statusIcon.className = 'fas fa-sync fa-spin text-warning status-icon';
        }
    }
    
    function removeBotFromUI(botId) {
        const botRow = document.querySelector(`tr[data-bot-id="${botId}"]`);
        if (botRow) {
            botRow.classList.add('fade-out');
            setTimeout(() => {
                botRow.remove();
                updateBotCounter();
            }, 500);
        }
    }
    
    function updateBotCounter() {
        const totalBots = document.querySelectorAll('tr[data-bot-id]').length;
        const counterElement = document.getElementById('total-bots-counter');
        if (counterElement) {
            counterElement.textContent = totalBots;
        }
    }
    
    function showToast(type, message) {
        if (type === 'success') {
            const toast = new bootstrap.Toast(document.getElementById('success-toast'));
            document.getElementById('toast-message').textContent = message;
            toast.show();
        } else {
            const toast = new bootstrap.Toast(document.getElementById('error-toast'));
            document.getElementById('toast-error-message').textContent = message;
            toast.show();
        }
    }
    
    function initializeBotStatuses() {
        // Initial status update
        botStatusCards.forEach(card => {
            const botId = card.dataset.botId;
            updateBotStatusFromServer(botId);
        });
        
        // Set interval for status updates
        setInterval(() => {
            botStatusCards.forEach(card => {
                const botId = card.dataset.botId;
                updateBotStatusFromServer(botId);
            });
        }, 30000); // Update every 30 seconds
    }
    
    function updateBotStatusFromServer(botId) {
        getBotStatus(botId)
            .then(data => {
                if (data.success) {
                    updateBotStatus(botId, data.status);
                    
                    // Update additional info
                    const infoElement = document.querySelector(`.bot-info[data-bot-id="${botId}"]`);
                    if (infoElement && data.info) {
                        // Update positions info
                        const positionsCount = data.info.positions_count || 0;
                        const positionsElement = infoElement.querySelector('.positions-count');
                        if (positionsElement) {
                            positionsElement.textContent = positionsCount;
                        }
                        
                        // Update profit info
                        const profit = data.info.profit || 0;
                        const profitElement = infoElement.querySelector('.bot-profit');
                        if (profitElement) {
                            profitElement.textContent = profit > 0 ? `+${profit.toFixed(2)}%` : `${profit.toFixed(2)}%`;
                            profitElement.className = 'bot-profit ' + (profit >= 0 ? 'text-success' : 'text-danger');
                        }
                        
                        // Update last trade time
                        const lastTradeTime = data.info.last_trade_time || 'N/A';
                        const lastTradeElement = infoElement.querySelector('.last-trade-time');
                        if (lastTradeElement) {
                            lastTradeElement.textContent = lastTradeTime;
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error updating bot status:', error);
            });
    }
});