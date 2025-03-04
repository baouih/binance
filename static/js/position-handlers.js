/**
 * Position Handlers - Xử lý các tương tác trên trang Quản lý vị thế
 * ----------------------------------------------------------------
 * Tập hợp các handler xử lý tương tác UI trên trang Quản lý vị thế
 * Tích hợp với các UI helper để đảm bảo giao diện nhất quán
 */

import { showAlert, showToast, showLoading, hideLoading, fetchAPI, formatCurrency, debounce, highlightChange } from './ui-helpers.js';

// Định nghĩa các API endpoint
const API_ENDPOINTS = {
    POSITIONS: '/api/positions',
    POSITION_DETAIL: '/api/position/{id}',
    CLOSE_POSITION: '/api/close-position/{id}',
    UPDATE_POSITION: '/api/position/{id}/update',
    ANALYZE_POSITION: '/api/position/{id}/analyze',
    OPEN_POSITION: '/api/open-position',
    ACCOUNT_SUMMARY: '/api/balance'
};

// Các tham số và biến toàn cục
let positionChart = null;
let tokenDistributionChart = null;
let accountSummary = {};

/**
 * Khởi tạo trang Quản lý vị thế
 */
export function initPositionPage() {
    // Tải dữ liệu ban đầu
    loadAccountSummary();
    loadPositions();
    
    // Khởi tạo các biểu đồ
    initializeCharts();
    
    // Đăng ký các sự kiện
    setupRefreshButton();
    setupPositionButtons();
    setupOpenPositionModal();
    setupEditPositionModal();
    
    // Cập nhật dữ liệu tự động mỗi 30 giây
    setInterval(loadAccountSummary, 30000);
    setInterval(loadPositions, 30000);
}

/**
 * Tải thông tin tài khoản
 */
function loadAccountSummary() {
    fetchAPI(API_ENDPOINTS.ACCOUNT_SUMMARY, {}, false, 
        // Success callback
        (data) => {
            // Lưu dữ liệu cho tham chiếu sau này
            accountSummary = data;
            
            // Cập nhật UI
            const balanceElement = document.getElementById('accountBalance');
            if (balanceElement) {
                const oldBalance = parseFloat(balanceElement.textContent.replace('$', '').replace(',', ''));
                const newBalance = data.balance;
                
                // Highlight nếu có thay đổi
                if (oldBalance !== newBalance) {
                    balanceElement.textContent = '$' + newBalance.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                    
                    highlightChange(
                        balanceElement, 
                        newBalance > oldBalance ? 'increase' : 'decrease'
                    );
                }
            }
            
            // Cập nhật các chỉ số khác
            updateRiskMetrics(data);
        },
        // Error callback
        (error) => {
            console.error('Error loading account summary:', error);
        }
    );
}

/**
 * Tải danh sách vị thế
 */
function loadPositions() {
    // Hiển thị loading spinner nhỏ cho phần vị thế
    const positionsContainer = document.getElementById('openPositions');
    if (positionsContainer) {
        // Thêm class loading và hiển thị spinner nhỏ
        positionsContainer.classList.add('loading');
        
        if (!positionsContainer.querySelector('.positions-loading')) {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'positions-loading text-center py-3';
            loadingDiv.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Đang tải...</span>
                </div>
                <p class="mt-2 text-muted">Đang tải danh sách vị thế...</p>
            `;
            positionsContainer.appendChild(loadingDiv);
        }
    }
    
    fetchAPI(API_ENDPOINTS.POSITIONS, {}, false,
        // Success callback
        (data) => {
            // Xóa loading spinner
            if (positionsContainer) {
                positionsContainer.classList.remove('loading');
                const loadingDiv = positionsContainer.querySelector('.positions-loading');
                if (loadingDiv) {
                    loadingDiv.remove();
                }
            }
            
            // Cập nhật danh sách vị thế
            updatePositionsList(data.positions || []);
            
            // Cập nhật biểu đồ phân bố token
            updateTokenDistributionChart(data.positions || []);
            
            // Hiện toast thông báo nếu có vị thế mới
            const previousCount = positionsContainer?.querySelectorAll('.position-card').length || 0;
            if (data.positions && data.positions.length > previousCount) {
                showToast('Thông báo', 'Đã thêm vị thế mới', 'success');
            }
        },
        // Error callback
        (error) => {
            console.error('Error loading positions:', error);
            
            // Xóa loading spinner
            if (positionsContainer) {
                positionsContainer.classList.remove('loading');
                const loadingDiv = positionsContainer.querySelector('.positions-loading');
                if (loadingDiv) {
                    loadingDiv.remove();
                }
            }
            
            // Hiển thị trạng thái không có vị thế
            if (positionsContainer) {
                positionsContainer.innerHTML = `
                    <div class="text-center py-5">
                        <i class="bi bi-wallet2 fs-1 text-muted"></i>
                        <p class="mt-3 text-muted">Không có vị thế nào đang mở</p>
                        <p class="text-muted">Bạn có thể mở vị thế mới bằng cách nhấn nút "Mở vị thế mới" ở trên</p>
                    </div>
                `;
            }
        }
    );
}

/**
 * Cập nhật danh sách vị thế trong UI
 * @param {Array} positions - Danh sách vị thế
 */
function updatePositionsList(positions) {
    const positionsContainer = document.getElementById('openPositions');
    if (!positionsContainer) return;
    
    // Nếu không có vị thế, hiển thị trạng thái trống
    if (!positions || positions.length === 0) {
        positionsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-wallet2 fs-1 text-muted"></i>
                <p class="mt-3 text-muted">Không có vị thế nào đang mở</p>
                <p class="text-muted">Bạn có thể mở vị thế mới bằng cách nhấn nút "Mở vị thế mới" ở trên</p>
            </div>
        `;
        return;
    }
    
    // Tạo HTML cho các vị thế
    let positionsHTML = '';
    positions.forEach(position => {
        positionsHTML += createPositionCardHTML(position);
    });
    
    // Cập nhật UI
    positionsContainer.innerHTML = positionsHTML;
    
    // Đăng ký lại các sự kiện cho các nút
    setupPositionButtons();
}

/**
 * Tạo HTML cho thẻ vị thế
 * @param {Object} position - Thông tin vị thế
 * @returns {string} HTML của thẻ vị thế
 */
function createPositionCardHTML(position) {
    // Tính toán các giá trị
    const isProfitable = position.pnl > 0;
    const risk = position.type === 'LONG' 
        ? position.entry_price - position.stop_loss 
        : position.stop_loss - position.entry_price;
    const reward = position.type === 'LONG'
        ? position.take_profit - position.entry_price
        : position.entry_price - position.take_profit;
    const riskRewardRatio = risk > 0 ? (reward / risk).toFixed(2) : '0';
    
    return `
        <div class="position-card mb-3 ${isProfitable ? 'profit' : position.pnl < 0 ? 'loss' : ''}" 
            data-position-id="${position.id}"
            data-toggle="position-details">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div>
                    <h5 class="mb-0">${position.symbol}</h5>
                    <span class="badge bg-${position.type === 'LONG' ? 'success' : 'danger'}">
                        ${position.type}
                    </span>
                    <span class="badge bg-secondary ms-1">
                        x${position.leverage || 1}
                    </span>
                </div>
                <div class="text-end">
                    <div class="info-value">
                        $${position.current_price ? position.current_price.toFixed(2) : '0.00'}
                    </div>
                    <div class="price-change ${position.pnl_percent > 0 ? 'positive' : position.pnl_percent < 0 ? 'negative' : ''}">
                        ${position.pnl_percent ? position.pnl_percent.toFixed(2) : '0.00'}%
                    </div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-3 col-6">
                    <div class="info-label">Giá vào</div>
                    <div>$${position.entry_price ? position.entry_price.toFixed(2) : '0.00'}</div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="info-label">Khối lượng</div>
                    <div>${position.quantity || '0.00'}</div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="info-label">Stop Loss</div>
                    <div>$${position.stop_loss ? position.stop_loss.toFixed(2) : '0.00'}</div>
                </div>
                <div class="col-md-3 col-6">
                    <div class="info-label">Take Profit</div>
                    <div>$${position.take_profit ? position.take_profit.toFixed(2) : '0.00'}</div>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="info-label">P/L</div>
                <div class="d-flex justify-content-between align-items-center">
                    <div class="info-value ${isProfitable ? 'text-success' : position.pnl < 0 ? 'text-danger' : ''}">
                        ${position.pnl ? position.pnl.toFixed(2) : '0.00'} USD (${position.pnl_percent ? position.pnl_percent.toFixed(2) : '0.00'}%)
                    </div>
                    <div>
                        <span class="badge ${isProfitable ? 'bg-success' : position.pnl < 0 ? 'bg-danger' : 'bg-secondary'}">
                            ${isProfitable ? 'Lợi nhuận' : position.pnl < 0 ? 'Lỗ' : 'Hòa vốn'}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="info-label">Risk/Reward</div>
                    <div>${riskRewardRatio}:1</div>
                </div>
                <div class="col-md-6 text-md-end">
                    <div class="info-label">Thời gian giữ</div>
                    <div>${position.entry_time || '2025-02-28 18:30:00'}</div>
                </div>
            </div>
            
            <div class="d-flex gap-2 mt-3">
                <button class="btn btn-sm btn-outline-danger close-position-btn" data-position-id="${position.id}">
                    <i class="bi bi-x-circle me-1"></i>
                    Đóng vị thế
                </button>
                <button class="btn btn-sm btn-outline-secondary edit-position-btn" data-position-id="${position.id}" data-bs-toggle="modal" data-bs-target="#editPositionModal">
                    <i class="bi bi-pencil me-1"></i>
                    Chỉnh sửa SL/TP
                </button>
                <button class="btn btn-sm btn-outline-primary analyze-position-btn" data-position-id="${position.id}">
                    <i class="bi bi-graph-up me-1"></i>
                    Phân tích
                </button>
            </div>
        </div>
    `;
}

/**
 * Cập nhật biểu đồ phân bố token
 * @param {Array} positions - Danh sách vị thế
 */
function updateTokenDistributionChart(positions) {
    if (!tokenDistributionChart) return;
    
    // Tính toán phân bố token
    const tokenMap = {};
    let totalValue = 0;
    
    positions.forEach(position => {
        const value = position.entry_price * position.quantity;
        totalValue += value;
        
        // Lấy symbol gốc (ví dụ: BTC từ BTCUSDT)
        const baseSymbol = position.symbol.replace(/USDT$|BUSD$/, '');
        tokenMap[baseSymbol] = (tokenMap[baseSymbol] || 0) + value;
    });
    
    // Tạo mảng dữ liệu cho biểu đồ
    const labels = Object.keys(tokenMap);
    const data = Object.values(tokenMap);
    
    // Cập nhật biểu đồ
    tokenDistributionChart.data.labels = labels;
    tokenDistributionChart.data.datasets[0].data = data;
    tokenDistributionChart.update();
}

/**
 * Cập nhật các chỉ số quản lý rủi ro
 * @param {Object} data - Dữ liệu tài khoản
 */
function updateRiskMetrics(data) {
    // Cập nhật số vị thế
    const positionCountElement = document.getElementById('positionCount');
    if (positionCountElement && data.position_count !== undefined) {
        positionCountElement.textContent = data.position_count;
    }
    
    // Cập nhật Unrealized P/L
    const unrealizedPnlElement = document.getElementById('unrealizedPnl');
    if (unrealizedPnlElement && data.unrealized_pnl !== undefined) {
        const oldPnl = parseFloat(unrealizedPnlElement.textContent.replace('$', '').replace(',', ''));
        const newPnl = data.unrealized_pnl;
        
        unrealizedPnlElement.textContent = '$' + newPnl.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        
        // Set class dựa vào giá trị
        unrealizedPnlElement.className = 'info-value';
        if (newPnl > 0) {
            unrealizedPnlElement.classList.add('text-success');
        } else if (newPnl < 0) {
            unrealizedPnlElement.classList.add('text-danger');
        }
        
        // Highlight nếu có thay đổi
        if (oldPnl !== newPnl) {
            highlightChange(
                unrealizedPnlElement, 
                newPnl > oldPnl ? 'increase' : 'decrease'
            );
        }
    }
    
    // Cập nhật Margin sử dụng
    const usedMarginElement = document.getElementById('usedMargin');
    if (usedMarginElement && data.used_margin !== undefined) {
        const marginPercent = data.balance > 0 ? (data.used_margin / data.balance * 100) : 0;
        usedMarginElement.textContent = `$${data.used_margin.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })} (${marginPercent.toFixed(2)}%)`;
    }
    
    // Cập nhật rủi ro danh mục
    const portfolioRiskElement = document.getElementById('portfolioRisk');
    const portfolioRiskProgressBar = document.getElementById('portfolioRiskBar');
    
    if (portfolioRiskElement && portfolioRiskProgressBar && data.portfolio_risk !== undefined) {
        portfolioRiskElement.textContent = data.portfolio_risk.toFixed(2) + '%';
        
        portfolioRiskProgressBar.style.width = `${data.portfolio_risk}%`;
        portfolioRiskProgressBar.setAttribute('aria-valuenow', data.portfolio_risk);
        
        // Thay đổi màu dựa vào mức rủi ro
        portfolioRiskProgressBar.className = 'progress-bar';
        if (data.portfolio_risk <= 10) {
            portfolioRiskProgressBar.classList.add('bg-success');
        } else if (data.portfolio_risk <= 20) {
            portfolioRiskProgressBar.classList.add('bg-warning');
        } else {
            portfolioRiskProgressBar.classList.add('bg-danger');
        }
    }
}

/**
 * Thiết lập sự kiện cho nút làm mới
 */
function setupRefreshButton() {
    const refreshBtn = document.getElementById('refreshPositionsBtn');
    if (!refreshBtn) return;
    
    refreshBtn.addEventListener('click', function() {
        // Hiển thị trạng thái loading trên nút
        const originalHTML = this.innerHTML;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang tải...';
        this.disabled = true;
        
        // Tải lại dữ liệu
        Promise.all([loadPositions(), loadAccountSummary()])
            .then(() => {
                // Hiển thị thông báo
                showToast('Thông báo', 'Dữ liệu đã được cập nhật', 'success');
            })
            .catch(error => {
                console.error('Error refreshing data:', error);
                showAlert('danger', 'Không thể cập nhật dữ liệu. Vui lòng thử lại sau.');
            })
            .finally(() => {
                // Khôi phục trạng thái nút
                this.innerHTML = originalHTML;
                this.disabled = false;
            });
    });
}

/**
 * Thiết lập sự kiện cho các nút trên thẻ vị thế
 */
function setupPositionButtons() {
    // Nút đóng vị thế
    document.querySelectorAll('.close-position-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const positionId = this.dataset.positionId;
            confirmClosePosition(positionId);
        });
    });
    
    // Nút chỉnh sửa vị thế (xử lý trong setupEditPositionModal)
    
    // Nút phân tích vị thế
    document.querySelectorAll('.analyze-position-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const positionId = this.dataset.positionId;
            analyzePosition(positionId);
        });
    });
}

/**
 * Xác nhận đóng vị thế
 * @param {string} positionId - ID của vị thế cần đóng
 */
function confirmClosePosition(positionId) {
    if (confirm('Bạn có chắc chắn muốn đóng vị thế này không?')) {
        closePosition(positionId);
    }
}

/**
 * Đóng vị thế
 * @param {string} positionId - ID của vị thế cần đóng
 */
function closePosition(positionId) {
    // URL với ID vị thế
    const url = API_ENDPOINTS.CLOSE_POSITION.replace('{id}', positionId);
    
    // Hiển thị loading
    showLoading('Đang đóng vị thế...');
    
    fetchAPI(url, { method: 'POST' }, false, 
        // Success callback
        (data) => {
            hideLoading();
            
            showToast('Thành công', 'Vị thế đã được đóng thành công', 'success');
            
            // Hiển thị kết quả
            if (data.profit_loss) {
                const isProfitable = data.profit_loss > 0;
                showAlert(
                    isProfitable ? 'success' : 'danger',
                    `Vị thế đã đóng với ${isProfitable ? 'lợi nhuận' : 'lỗ'}: $${Math.abs(data.profit_loss).toFixed(2)}`
                );
            }
            
            // Cập nhật danh sách vị thế và thông tin tài khoản
            setTimeout(() => {
                loadPositions();
                loadAccountSummary();
            }, 1000);
        },
        // Error callback
        (error) => {
            hideLoading();
            showAlert('danger', `Lỗi khi đóng vị thế: ${error.message}`);
        }
    );
}

/**
 * Phân tích vị thế
 * @param {string} positionId - ID của vị thế cần phân tích
 */
function analyzePosition(positionId) {
    // URL với ID vị thế
    const url = API_ENDPOINTS.ANALYZE_POSITION.replace('{id}', positionId);
    
    // Hiển thị loading
    showLoading('Đang phân tích vị thế...');
    
    fetchAPI(url, {}, false, 
        // Success callback
        (data) => {
            hideLoading();
            
            // TODO: Hiển thị modal phân tích chi tiết hoặc trang phân tích riêng
            showToast('Thành công', 'Đã phân tích vị thế', 'success');
            
            // Tạm thời hiển thị kết quả dưới dạng alert
            let analysisHTML = `
                <div class="mb-3">
                    <h5>Phân tích vị thế ${data.symbol || 'Không xác định'}</h5>
                    <p>Loại: ${data.type || 'N/A'} - Giá vào: $${data.entry_price ? data.entry_price.toFixed(2) : '0.00'}</p>
                    <p>P/L hiện tại: ${data.pnl ? data.pnl.toFixed(2) : '0.00'} USD (${data.pnl_percent ? data.pnl_percent.toFixed(2) : '0.00'}%)</p>
                </div>
                <div class="mb-3">
                    <h6>Đề xuất</h6>
                    <p>${data.recommendation || 'Không có đề xuất'}</p>
                </div>
            `;
            
            showAlert('info', analysisHTML);
        },
        // Error callback
        (error) => {
            hideLoading();
            showAlert('danger', `Lỗi khi phân tích vị thế: ${error.message}`);
        }
    );
}

/**
 * Khởi tạo các biểu đồ
 */
function initializeCharts() {
    // Biểu đồ phân bố token
    const tokenChartCanvas = document.getElementById('tokenDistributionChart');
    if (tokenChartCanvas && typeof Chart !== 'undefined') {
        tokenDistributionChart = new Chart(tokenChartCanvas, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(255, 159, 64, 0.7)',
                        'rgba(199, 199, 199, 0.7)'
                    ],
                    borderColor: [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)',
                        'rgba(199, 199, 199, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 15,
                            padding: 10
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = (value / total * 100).toFixed(2);
                                return `${context.label}: $${value.toFixed(2)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Thiết lập modal mở vị thế mới
 */
function setupOpenPositionModal() {
    // Lấy các phần tử
    const modal = document.getElementById('openPositionModal');
    if (!modal) return;
    
    // Modal bootstrap
    const openPositionModal = new bootstrap.Modal(modal);
    
    // Các phần tử form
    const symbolSelect = document.getElementById('symbolSelect');
    const sideSelect = document.getElementById('sideSelect');
    const entryPriceInput = document.getElementById('entryPrice');
    const stopLossInput = document.getElementById('stopLoss');
    const takeProfitInput = document.getElementById('takeProfit');
    const riskPercentInput = document.getElementById('riskPercent');
    const leverageInput = document.getElementById('leverageInput');
    const leverageValue = document.getElementById('leverageValue');
    const useTrailingStop = document.getElementById('useTrailingStop');
    
    // Các phần tử hiển thị tính toán
    const calculatedQuantity = document.getElementById('calculatedQuantity');
    const calculatedRisk = document.getElementById('calculatedRisk');
    const calculatedRR = document.getElementById('calculatedRR');
    const calculatedMargin = document.getElementById('calculatedMargin');
    
    // Nút mở vị thế
    const submitBtn = document.getElementById('submitOpenPosition');
    
    // Cập nhật giá trị đòn bẩy khi thay đổi slider
    if (leverageInput && leverageValue) {
        leverageInput.addEventListener('input', function() {
            leverageValue.textContent = this.value + 'x';
            updatePositionCalculations();
        });
    }
    
    // Cập nhật tính toán khi thay đổi các trường input
    const updateCalculations = debounce(updatePositionCalculations, 300);
    
    // Đăng ký sự kiện
    if (symbolSelect) symbolSelect.addEventListener('change', updateCalculations);
    if (sideSelect) sideSelect.addEventListener('change', updateCalculations);
    if (entryPriceInput) entryPriceInput.addEventListener('input', updateCalculations);
    if (stopLossInput) stopLossInput.addEventListener('input', updateCalculations);
    if (takeProfitInput) takeProfitInput.addEventListener('input', updateCalculations);
    if (riskPercentInput) riskPercentInput.addEventListener('input', updateCalculations);
    
    // Nút mở vị thế
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            // Validate form
            if (!validateOpenPositionForm()) {
                return;
            }
            
            // Tạo dữ liệu để gửi đi
            const formData = {
                symbol: symbolSelect.value,
                side: sideSelect.value,
                entry_price: parseFloat(entryPriceInput.value),
                stop_loss: parseFloat(stopLossInput.value),
                take_profit: parseFloat(takeProfitInput.value),
                risk_percent: parseFloat(riskPercentInput.value),
                leverage: parseInt(leverageInput.value),
                use_trailing_stop: useTrailingStop.checked
            };
            
            // Gọi API mở vị thế
            openPosition(formData, openPositionModal);
        });
    }
    
    // Hàm cập nhật tính toán
    function updatePositionCalculations() {
        if (!symbolSelect || !sideSelect || !entryPriceInput || !stopLossInput || 
            !takeProfitInput || !riskPercentInput || !leverageInput || 
            !calculatedQuantity || !calculatedRisk || !calculatedRR || !calculatedMargin) {
            return;
        }
        
        // Lấy các giá trị input
        const entryPrice = parseFloat(entryPriceInput.value) || 0;
        const stopLoss = parseFloat(stopLossInput.value) || 0;
        const takeProfit = parseFloat(takeProfitInput.value) || 0;
        const riskPercent = parseFloat(riskPercentInput.value) || 0;
        const leverage = parseInt(leverageInput.value) || 1;
        const side = sideSelect.value;
        
        // Xác định giá vào - giá SL
        let priceDiff = 0;
        if (side === 'BUY') { // LONG
            priceDiff = entryPrice - stopLoss;
        } else { // SHORT
            priceDiff = stopLoss - entryPrice;
        }
        
        // Tính toán khối lượng dựa trên % rủi ro
        let quantity = 0;
        let riskAmount = 0;
        
        if (priceDiff > 0 && entryPrice > 0) {
            // Số tiền rủi ro (% của balance)
            riskAmount = (accountSummary.balance || 10000) * (riskPercent / 100);
            
            // Số lượng đồng coin
            quantity = (riskAmount / priceDiff) * leverage;
        }
        
        // Tính R:R ratio
        let rrRatio = 0;
        if (side === 'BUY') { // LONG
            const riskPerUnit = entryPrice - stopLoss;
            const rewardPerUnit = takeProfit - entryPrice;
            rrRatio = riskPerUnit > 0 ? rewardPerUnit / riskPerUnit : 0;
        } else { // SHORT
            const riskPerUnit = stopLoss - entryPrice;
            const rewardPerUnit = entryPrice - takeProfit;
            rrRatio = riskPerUnit > 0 ? rewardPerUnit / riskPerUnit : 0;
        }
        
        // Tính margin cần thiết
        const margin = (entryPrice * quantity) / leverage;
        
        // Cập nhật UI
        calculatedQuantity.textContent = quantity.toFixed(5);
        calculatedRisk.textContent = `$${riskAmount.toFixed(2)} (${riskPercent}%)`;
        calculatedRR.textContent = `${rrRatio.toFixed(2)}:1`;
        calculatedMargin.textContent = `$${margin.toFixed(2)}`;
        
        // Highlight các phần tử đã thay đổi
        highlightChange(calculatedQuantity, 'update');
        highlightChange(calculatedRisk, 'update');
        highlightChange(calculatedRR, 'update');
        highlightChange(calculatedMargin, 'update');
    }
    
    // Validate form
    function validateOpenPositionForm() {
        // Reset validation state
        let isValid = true;
        const invalidFields = [];
        
        // Kiểm tra symbol
        if (!symbolSelect.value) {
            invalidFields.push('Symbol');
            isValid = false;
        }
        
        // Kiểm tra entry price
        if (!entryPriceInput.value || parseFloat(entryPriceInput.value) <= 0) {
            entryPriceInput.classList.add('is-invalid');
            invalidFields.push('Giá vào');
            isValid = false;
        } else {
            entryPriceInput.classList.remove('is-invalid');
        }
        
        // Kiểm tra stop loss
        if (!stopLossInput.value || parseFloat(stopLossInput.value) <= 0) {
            stopLossInput.classList.add('is-invalid');
            invalidFields.push('Stop Loss');
            isValid = false;
        } else {
            stopLossInput.classList.remove('is-invalid');
        }
        
        // Kiểm tra take profit
        if (!takeProfitInput.value || parseFloat(takeProfitInput.value) <= 0) {
            takeProfitInput.classList.add('is-invalid');
            invalidFields.push('Take Profit');
            isValid = false;
        } else {
            takeProfitInput.classList.remove('is-invalid');
        }
        
        // Kiểm tra logic của stop loss và take profit
        const entryPrice = parseFloat(entryPriceInput.value) || 0;
        const stopLoss = parseFloat(stopLossInput.value) || 0;
        const takeProfit = parseFloat(takeProfitInput.value) || 0;
        const side = sideSelect.value;
        
        if (side === 'BUY') { // LONG
            if (stopLoss >= entryPrice) {
                stopLossInput.classList.add('is-invalid');
                invalidFields.push('Stop Loss phải nhỏ hơn Giá vào trong vị thế LONG');
                isValid = false;
            }
            
            if (takeProfit <= entryPrice) {
                takeProfitInput.classList.add('is-invalid');
                invalidFields.push('Take Profit phải lớn hơn Giá vào trong vị thế LONG');
                isValid = false;
            }
        } else { // SHORT
            if (stopLoss <= entryPrice) {
                stopLossInput.classList.add('is-invalid');
                invalidFields.push('Stop Loss phải lớn hơn Giá vào trong vị thế SHORT');
                isValid = false;
            }
            
            if (takeProfit >= entryPrice) {
                takeProfitInput.classList.add('is-invalid');
                invalidFields.push('Take Profit phải nhỏ hơn Giá vào trong vị thế SHORT');
                isValid = false;
            }
        }
        
        // Hiển thị thông báo lỗi nếu có
        if (!isValid) {
            showAlert('danger', `Vui lòng kiểm tra lại các trường: ${invalidFields.join(', ')}`);
        }
        
        return isValid;
    }
}

/**
 * Mở vị thế mới
 * @param {Object} formData - Dữ liệu vị thế
 * @param {bootstrap.Modal} modal - Modal để đóng sau khi thành công
 */
function openPosition(formData, modal) {
    // Hiển thị loading
    showLoading('Đang mở vị thế...');
    
    fetchAPI(API_ENDPOINTS.OPEN_POSITION, {
        method: 'POST',
        body: JSON.stringify(formData)
    }, false, 
        // Success callback
        (data) => {
            hideLoading();
            
            // Đóng modal
            if (modal) {
                modal.hide();
            }
            
            // Hiển thị thông báo thành công
            showAlert('success', 'Đã mở vị thế thành công');
            
            // Cập nhật danh sách vị thế và thông tin tài khoản
            setTimeout(() => {
                loadPositions();
                loadAccountSummary();
            }, 1000);
        },
        // Error callback
        (error) => {
            hideLoading();
            showAlert('danger', `Lỗi khi mở vị thế: ${error.message}`);
        }
    );
}

/**
 * Thiết lập modal chỉnh sửa vị thế
 */
function setupEditPositionModal() {
    // Lấy các phần tử
    const modal = document.getElementById('editPositionModal');
    if (!modal) return;
    
    // Modal bootstrap
    const editPositionModal = new bootstrap.Modal(modal);
    
    // Các phần tử form
    const positionIdInput = document.getElementById('editPositionId');
    const symbolElement = document.getElementById('editPositionSymbol');
    const typeElement = document.getElementById('editPositionType');
    const priceElement = document.getElementById('editPositionPrice');
    const entryPriceInput = document.getElementById('editEntryPrice');
    const quantityInput = document.getElementById('editQuantity');
    const stopLossInput = document.getElementById('editStopLoss');
    const takeProfitInput = document.getElementById('editTakeProfit');
    const useTrailingStop = document.getElementById('editUseTrailingStop');
    
    // Nút cập nhật
    const updateBtn = document.getElementById('updatePositionBtn');
    
    // Xử lý sự kiện khi mở modal
    modal.addEventListener('show.bs.modal', function (event) {
        const button = event.relatedTarget;
        if (!button) return;
        
        const positionId = button.dataset.positionId;
        if (!positionId) return;
        
        // Tải thông tin vị thế
        fetchPositionDetail(positionId);
    });
    
    // Nút cập nhật vị thế
    if (updateBtn) {
        updateBtn.addEventListener('click', function() {
            // Validate form
            if (!validateEditPositionForm()) {
                return;
            }
            
            // Lấy dữ liệu
            const formData = {
                stop_loss: parseFloat(stopLossInput.value),
                take_profit: parseFloat(takeProfitInput.value),
                use_trailing_stop: useTrailingStop.checked
            };
            
            // Cập nhật vị thế
            updatePosition(positionIdInput.value, formData, editPositionModal);
        });
    }
    
    // Hàm tải thông tin chi tiết vị thế
    function fetchPositionDetail(positionId) {
        if (!positionIdInput || !symbolElement || !typeElement || 
            !priceElement || !entryPriceInput || !quantityInput || 
            !stopLossInput || !takeProfitInput || !useTrailingStop) {
            return;
        }
        
        // Hiển thị loading trong modal
        const modalBody = modal.querySelector('.modal-body');
        if (modalBody) {
            modalBody.style.opacity = '0.5';
            const loadingSpinner = document.createElement('div');
            loadingSpinner.className = 'position-absolute w-100 h-100 d-flex align-items-center justify-content-center';
            loadingSpinner.style.top = '0';
            loadingSpinner.style.left = '0';
            loadingSpinner.style.zIndex = '1000';
            loadingSpinner.innerHTML = `
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            `;
            modalBody.appendChild(loadingSpinner);
        }
        
        // URL với ID vị thế
        const url = API_ENDPOINTS.POSITION_DETAIL.replace('{id}', positionId);
        
        fetchAPI(url, {}, false, 
            // Success callback
            (data) => {
                // Xóa loading spinner
                if (modalBody) {
                    modalBody.style.opacity = '1';
                    const loadingSpinner = modalBody.querySelector('.position-absolute');
                    if (loadingSpinner) {
                        loadingSpinner.remove();
                    }
                }
                
                // Cập nhật thông tin trong form
                positionIdInput.value = positionId;
                symbolElement.textContent = data.symbol;
                typeElement.textContent = data.type;
                typeElement.className = `badge ${data.type === 'LONG' ? 'bg-success' : 'bg-danger'}`;
                
                priceElement.textContent = `$${data.current_price.toFixed(2)}`;
                entryPriceInput.value = data.entry_price.toFixed(2);
                quantityInput.value = data.quantity;
                stopLossInput.value = data.stop_loss.toFixed(2);
                takeProfitInput.value = data.take_profit.toFixed(2);
                useTrailingStop.checked = data.use_trailing_stop || false;
            },
            // Error callback
            (error) => {
                // Xóa loading spinner
                if (modalBody) {
                    modalBody.style.opacity = '1';
                    const loadingSpinner = modalBody.querySelector('.position-absolute');
                    if (loadingSpinner) {
                        loadingSpinner.remove();
                    }
                }
                
                showAlert('danger', `Lỗi khi tải thông tin vị thế: ${error.message}`);
                
                // Đóng modal
                editPositionModal.hide();
            }
        );
    }
    
    // Validate form chỉnh sửa
    function validateEditPositionForm() {
        // Reset validation state
        let isValid = true;
        const invalidFields = [];
        
        // Kiểm tra stop loss
        if (!stopLossInput.value || parseFloat(stopLossInput.value) <= 0) {
            stopLossInput.classList.add('is-invalid');
            invalidFields.push('Stop Loss');
            isValid = false;
        } else {
            stopLossInput.classList.remove('is-invalid');
        }
        
        // Kiểm tra take profit
        if (!takeProfitInput.value || parseFloat(takeProfitInput.value) <= 0) {
            takeProfitInput.classList.add('is-invalid');
            invalidFields.push('Take Profit');
            isValid = false;
        } else {
            takeProfitInput.classList.remove('is-invalid');
        }
        
        // Hiển thị thông báo lỗi nếu có
        if (!isValid) {
            showAlert('danger', `Vui lòng kiểm tra lại các trường: ${invalidFields.join(', ')}`);
        }
        
        return isValid;
    }
}

/**
 * Cập nhật vị thế
 * @param {string} positionId - ID của vị thế
 * @param {Object} formData - Dữ liệu cập nhật
 * @param {bootstrap.Modal} modal - Modal để đóng sau khi thành công
 */
function updatePosition(positionId, formData, modal) {
    // URL với ID vị thế
    const url = API_ENDPOINTS.UPDATE_POSITION.replace('{id}', positionId);
    
    // Hiển thị loading
    showLoading('Đang cập nhật vị thế...');
    
    fetchAPI(url, {
        method: 'POST',
        body: JSON.stringify(formData)
    }, false, 
        // Success callback
        (data) => {
            hideLoading();
            
            // Đóng modal
            if (modal) {
                modal.hide();
            }
            
            // Hiển thị thông báo thành công
            showAlert('success', 'Đã cập nhật vị thế thành công');
            
            // Cập nhật danh sách vị thế
            setTimeout(() => {
                loadPositions();
            }, 1000);
        },
        // Error callback
        (error) => {
            hideLoading();
            showAlert('danger', `Lỗi khi cập nhật vị thế: ${error.message}`);
        }
    );
}

// Khởi tạo khi DOM đã tải xong
document.addEventListener('DOMContentLoaded', initPositionPage);