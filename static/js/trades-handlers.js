/**
 * Trades Handlers - Xử lý các tương tác người dùng trên trang Lịch sử giao dịch
 * Tích hợp với UI Helper cho trải nghiệm thống nhất
 */
import { showToast, showAlert, showLoading, hideLoading, confirmAction } from './ui-helpers.js';

document.addEventListener('DOMContentLoaded', () => {
    initPerformanceChart();
    initTradeFilters();
    initTradeInteractions();
    initDatePickers();
    initExportFunctions();
});

/**
 * Khởi tạo biểu đồ hiệu suất
 */
function initPerformanceChart() {
    const performanceCtx = document.getElementById('performanceChart')?.getContext('2d');
    if (!performanceCtx) return;

    const performanceChart = new Chart(performanceCtx, {
        type: 'line',
        data: {
            labels: Array.from(document.querySelectorAll('[data-trade-date]')).map(el => el.dataset.tradeDate).reverse(),
            datasets: [{
                label: 'P/L Tích lũy',
                data: (function() {
                    let cumulative = 0;
                    return Array.from(document.querySelectorAll('[data-trade-pnl]')).map(el => {
                        cumulative += parseFloat(el.dataset.tradePnl);
                        return cumulative;
                    }).reverse();
                })(),
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y;
                            return `P/L Tích lũy: ${value >= 0 ? '+' : ''}$${value.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return `$${value}`;
                        }
                    }
                }
            }
        }
    });

    // Win Rate Chart
    const winRateCtx = document.getElementById('winRateChart')?.getContext('2d');
    if (!winRateCtx) return;

    // Get win/loss data from the page
    const totalTrades = parseInt(document.getElementById('totalTradesCount')?.textContent || '0');
    const winTrades = parseInt(document.getElementById('winTradesCount')?.textContent || '0');
    const lossTrades = totalTrades - winTrades;
    
    const winRateChart = new Chart(winRateCtx, {
        type: 'doughnut',
        data: {
            labels: ['Thắng', 'Thua'],
            datasets: [{
                data: [winTrades, lossTrades],
                backgroundColor: [
                    'rgba(75, 192, 92, 0.7)',
                    'rgba(255, 99, 132, 0.7)'
                ],
                borderColor: [
                    'rgba(75, 192, 92, 1)',
                    'rgba(255, 99, 132, 1)'
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
                            return `${context.label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

/**
 * Khởi tạo bộ lọc giao dịch
 */
function initTradeFilters() {
    const filterForm = document.getElementById('filterForm');
    const filterBtn = document.getElementById('applyFiltersBtn');
    const resetBtn = document.getElementById('resetFiltersBtn');

    if (!filterForm || !filterBtn || !resetBtn) return;

    filterBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        showLoading();
        
        // Simulate filtering (in real app, this would submit the form)
        setTimeout(() => {
            hideLoading();
            showToast('Thông báo', 'Đã áp dụng bộ lọc', 'info');
            
            // In real app, the page would refresh with filtered data
            // For now, just show a message
            showAlert('info', 'Bộ lọc đã được áp dụng. Trong ứng dụng thực tế, dữ liệu sẽ được cập nhật.');
        }, 1000);
    });

    resetBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        // Reset all filters
        const inputs = filterForm.querySelectorAll('input, select');
        inputs.forEach(input => {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = '';
            }
        });
        
        showToast('Thông báo', 'Đã đặt lại bộ lọc', 'info');
    });

    // Implement quick filter buttons
    const quickFilterBtns = document.querySelectorAll('.quick-filter-btn');
    quickFilterBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const filterType = this.dataset.filter;
            
            // Set filters based on button type
            switch(filterType) {
                case 'today':
                    const today = new Date().toISOString().split('T')[0];
                    document.getElementById('startDate').value = today;
                    document.getElementById('endDate').value = today;
                    break;
                case 'yesterday':
                    const yesterday = new Date();
                    yesterday.setDate(yesterday.getDate() - 1);
                    document.getElementById('startDate').value = yesterday.toISOString().split('T')[0];
                    document.getElementById('endDate').value = yesterday.toISOString().split('T')[0];
                    break;
                case 'week':
                    const weekStart = new Date();
                    weekStart.setDate(weekStart.getDate() - 7);
                    document.getElementById('startDate').value = weekStart.toISOString().split('T')[0];
                    document.getElementById('endDate').value = new Date().toISOString().split('T')[0];
                    break;
                case 'month':
                    const monthStart = new Date();
                    monthStart.setDate(monthStart.getDate() - 30);
                    document.getElementById('startDate').value = monthStart.toISOString().split('T')[0];
                    document.getElementById('endDate').value = new Date().toISOString().split('T')[0];
                    break;
                case 'profitable':
                    document.getElementById('resultFilter').value = 'profit';
                    break;
                case 'losing':
                    document.getElementById('resultFilter').value = 'loss';
                    break;
            }
            
            // Auto-apply the filter
            filterBtn.click();
        });
    });
}

/**
 * Khởi tạo các tương tác trên bảng giao dịch
 */
function initTradeInteractions() {
    // Trade details accordion
    const tradeRows = document.querySelectorAll('.trade-row');
    
    tradeRows.forEach(row => {
        row.addEventListener('click', function() {
            const tradeId = this.dataset.tradeId;
            const detailRow = document.getElementById(`trade-detail-${tradeId}`);
            
            if (detailRow) {
                // Toggle details visibility
                const wasHidden = detailRow.classList.contains('d-none');
                
                // Hide all other details first
                document.querySelectorAll('.trade-detail-row').forEach(r => {
                    r.classList.add('d-none');
                });
                
                // Toggle current detail row
                if (wasHidden) {
                    detailRow.classList.remove('d-none');
                    
                    // Highlight selected row
                    document.querySelectorAll('.trade-row').forEach(r => {
                        r.classList.remove('selected-row');
                    });
                    
                    this.classList.add('selected-row');
                } else {
                    this.classList.remove('selected-row');
                }
            }
        });
    });

    // Delete trade button
    const deleteButtons = document.querySelectorAll('.delete-trade-btn');
    
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent row click
            
            const tradeId = this.dataset.tradeId;
            
            confirmAction(
                'Xác nhận xóa',
                'Bạn có chắc chắn muốn xóa giao dịch này không? Hành động này không thể hoàn tác.',
                () => {
                    showLoading();
                    
                    // In a real app, make API call to delete trade
                    setTimeout(() => {
                        hideLoading();
                        
                        // Remove the row with animation
                        const row = document.querySelector(`.trade-row[data-trade-id="${tradeId}"]`);
                        const detailRow = document.getElementById(`trade-detail-${tradeId}`);
                        
                        if (row) {
                            row.style.height = row.offsetHeight + 'px';
                            row.style.overflow = 'hidden';
                            row.style.transition = 'all 0.5s ease';
                            
                            setTimeout(() => {
                                row.style.height = '0';
                                row.style.padding = '0';
                                row.style.margin = '0';
                                
                                if (detailRow) {
                                    detailRow.style.height = '0';
                                    detailRow.style.padding = '0';
                                    detailRow.style.margin = '0';
                                }
                                
                                setTimeout(() => {
                                    row.remove();
                                    if (detailRow) detailRow.remove();
                                    
                                    showToast('Thành công', 'Đã xóa giao dịch', 'success');
                                    
                                    // Update counters and charts (in a real app)
                                    updateTradeCounters();
                                }, 500);
                            }, 10);
                        }
                    }, 1000);
                }
            );
        });
    });

    // Review trade button
    const reviewButtons = document.querySelectorAll('.review-trade-btn');
    
    reviewButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Prevent row click
            
            const tradeId = this.dataset.tradeId;
            
            showLoading();
            
            // In a real app, make API call to get trade details
            setTimeout(() => {
                hideLoading();
                
                // Show review modal or alert (for demo)
                showAlert('info', `
                    <h5>Đánh giá giao dịch #${tradeId}</h5>
                    <p>Trong ứng dụng thực, tại đây sẽ hiển thị đánh giá chi tiết về giao dịch này, bao gồm:</p>
                    <ul>
                        <li>Phân tích thời điểm vào lệnh/ra lệnh</li>
                        <li>So sánh với các chỉ báo kỹ thuật</li>
                        <li>Đánh giá tuân thủ chiến lược</li>
                        <li>Các phát hiện và đề xuất cải thiện</li>
                    </ul>
                `);
            }, 1000);
        });
    });
}

/**
 * Khởi tạo date pickers
 */
function initDatePickers() {
    // If using a date picker library, initialize it here
    // For now, using native date inputs
    const datePickers = document.querySelectorAll('input[type="date"]');
    
    // Set default date range (last 30 days)
    if (datePickers.length >= 2) {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);
        
        const startInput = document.getElementById('startDate');
        const endInput = document.getElementById('endDate');
        
        if (startInput && !startInput.value) {
            startInput.value = startDate.toISOString().split('T')[0];
        }
        
        if (endInput && !endInput.value) {
            endInput.value = endDate.toISOString().split('T')[0];
        }
    }
}

/**
 * Khởi tạo các chức năng xuất dữ liệu
 */
function initExportFunctions() {
    const exportCSVBtn = document.getElementById('exportCSVBtn');
    const exportPDFBtn = document.getElementById('exportPDFBtn');
    
    if (exportCSVBtn) {
        exportCSVBtn.addEventListener('click', function() {
            showLoading();
            
            // In a real app, make API call to export data
            setTimeout(() => {
                hideLoading();
                showToast('Thành công', 'Đã xuất dữ liệu sang CSV', 'success');
            }, 1500);
        });
    }
    
    if (exportPDFBtn) {
        exportPDFBtn.addEventListener('click', function() {
            showLoading();
            
            // In a real app, make API call to export data
            setTimeout(() => {
                hideLoading();
                showToast('Thành công', 'Đã xuất dữ liệu sang PDF', 'success');
            }, 1500);
        });
    }
}

/**
 * Cập nhật bộ đếm giao dịch
 */
function updateTradeCounters() {
    // Count remaining trades
    const remainingTrades = document.querySelectorAll('.trade-row').length;
    
    // Count winning trades
    const winningTrades = document.querySelectorAll('.trade-row[data-trade-result="win"]').length;
    
    // Update counters in UI
    const totalTradesEl = document.getElementById('totalTradesCount');
    const winTradesEl = document.getElementById('winTradesCount');
    const winRateEl = document.getElementById('winRateValue');
    
    if (totalTradesEl) totalTradesEl.textContent = remainingTrades;
    if (winTradesEl) winTradesEl.textContent = winningTrades;
    if (winRateEl && remainingTrades > 0) {
        const winRate = (winningTrades / remainingTrades * 100).toFixed(2);
        winRateEl.textContent = `${winRate}%`;
    }
}