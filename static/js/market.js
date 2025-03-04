/**
 * Market.js - Script for market data and chart functionality
 * 
 * This script handles fetching real-time market data from Binance API 
 * and rendering charts and updates for the market page.
 * Uses UI helpers from ui-helpers.js for consistent user experience.
 */

// Import UI helpers
import { showAlert, showToast, showLoading, hideLoading, fetchAPI } from './ui-helpers.js';

document.addEventListener('DOMContentLoaded', function() {
    console.log('Market.js loaded');

    // Market chart element
    const marketChartElement = document.getElementById('marketChart');
    
    // Chart type buttons
    const chartTypeButtons = document.querySelectorAll('.chart-type');
    
    // Refresh market data button
    const refreshMarketButton = document.getElementById('refresh-market');
    
    // Auto refresh toggle
    const autoRefreshToggle = document.getElementById('auto-refresh');
    
    // Current chart configuration
    let chartConfig = {
        timeframe: '24h', // Default timeframe 
        symbol: 'BTCUSDT', // Default symbol
        type: 'line',      // Default chart type
    };
    
    // Chart instance
    let marketChart = null;
    
    // Auto refresh interval
    let autoRefreshInterval = null;
    
    // Timeframe options
    const timeframeOptions = document.querySelectorAll('.timeframe-option');
    timeframeOptions.forEach(option => {
        option.addEventListener('click', function() {
            const value = this.getAttribute('data-value');
            document.getElementById('timeframe-text').textContent = this.textContent;
            chartConfig.timeframe = value;
            
            // Set all options as inactive
            timeframeOptions.forEach(opt => {
                opt.classList.remove('active');
            });
            
            // Set current option as active
            this.classList.add('active');
            
            // Show loading toast
            showToast('Đang cập nhật', `Đang tải dữ liệu khung thời gian ${this.textContent}`, 'info');
            
            loadMarketData();
        });
    });
    
    // Initialize chart
    if (marketChartElement) {
        initializeChart();
    }
    
    // Add event listeners to chart type buttons
    chartTypeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const chartType = this.getAttribute('data-type');
            
            // Remove active class from all buttons
            chartTypeButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Update chart type
            chartConfig.type = chartType;
            
            // Show toast notification
            showToast('Đang cập nhật', `Đang chuyển sang biểu đồ dạng ${this.textContent}`, 'info');
            
            // Reinitialize chart
            if (marketChart) {
                marketChart.destroy();
            }
            initializeChart();
        });
    });
    
    // Add event listener to refresh button
    if (refreshMarketButton) {
        refreshMarketButton.addEventListener('click', function() {
            // Update button state to show loading
            const originalText = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang tải...';
            this.disabled = true;
            
            // Show toast notification
            showToast('Đang cập nhật', 'Đang làm mới dữ liệu thị trường', 'info');
            
            // Load market data
            loadMarketData()
                .finally(() => {
                    // Restore button state
                    this.innerHTML = originalText;
                    this.disabled = false;
                });
        });
    }
    
    // Handle auto refresh toggle
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', function() {
            if (this.checked) {
                enableAutoRefresh();
                showToast('Thông báo', 'Đã bật tự động làm mới dữ liệu (30 giây/lần)', 'success');
            } else {
                disableAutoRefresh();
                showToast('Thông báo', 'Đã tắt tự động làm mới dữ liệu', 'info');
            }
        });
        
        // Initialize auto refresh based on initial state
        if (autoRefreshToggle.checked) {
            enableAutoRefresh();
        }
    }
    
    /**
     * Initialize market chart
     */
    function initializeChart() {
        if (!marketChartElement) return;
        
        const ctx = marketChartElement.getContext('2d');
        
        // Default data while real data loads
        const defaultData = {
            labels: Array(24).fill(0).map((_, i) => i),
            datasets: [{
                label: `${chartConfig.symbol} Price`,
                data: Array(24).fill(null),
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                fill: false,
                tension: 0.4
            }]
        };
        
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += '$' + context.parsed.y.toLocaleString();
                            }
                            return label;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        };
        
        marketChart = new Chart(ctx, {
            type: chartConfig.type === 'candle' ? 'bar' : 'line',
            data: defaultData,
            options: options
        });
        
        // Load real data
        loadChartData();
    }
    
    /**
     * Load market overview data
     * @returns {Promise} Promise that resolves when data is loaded
     */
    function loadMarketData() {
        // Sử dụng hàm fetchAPI từ ui-helpers.js
        return fetchAPI(`/api/market/data?timeframe=${chartConfig.timeframe}`, {}, true, 
            // Success callback
            (data) => {
                // Update BTC price and change
                const btcPrice = document.getElementById('btc-price');
                if (btcPrice && data.btc_price) {
                    btcPrice.textContent = `$${data.btc_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                }
                
                // Update ETH price and change
                const ethPrice = document.getElementById('eth-price');
                if (ethPrice && data.eth_price) {
                    ethPrice.textContent = `$${data.eth_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                }
                
                // Update SOL price and change
                const solPrice = document.getElementById('sol-price');
                if (solPrice && data.sol_price) {
                    solPrice.textContent = `$${data.sol_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                }
                
                // Update BNB price and change
                const bnbPrice = document.getElementById('bnb-price');
                if (bnbPrice && data.bnb_price) {
                    bnbPrice.textContent = `$${data.bnb_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                }
                
                // Update price changes and colors
                document.querySelectorAll('.price-change').forEach(el => {
                    const change = parseFloat(el.textContent);
                    el.classList.remove('positive', 'negative');
                    if (change > 0) {
                        el.classList.add('positive');
                    } else if (change < 0) {
                        el.classList.add('negative');
                    }
                });
                
                // Show success notification
                showToast('Thông báo', 'Dữ liệu thị trường đã được cập nhật', 'success');
                
                // Also update chart data
                loadChartData();
            },
            // Error callback
            (error) => {
                showAlert('danger', `Lỗi khi tải dữ liệu thị trường: ${error.message}`);
            }
        );
    }
    
    /**
     * Load chart data from API
     * @returns {Promise} Promise that resolves when chart data is loaded
     */
    function loadChartData() {
        if (!marketChart) return Promise.resolve();
        
        // Hiển thị trạng thái loading cho biểu đồ
        const chartContainer = marketChartElement.closest('.info-card');
        if (chartContainer) {
            chartContainer.classList.add('loading');
            
            // Thêm overlay loading nếu chưa có
            if (!chartContainer.querySelector('.chart-loading')) {
                const loadingOverlay = document.createElement('div');
                loadingOverlay.className = 'chart-loading d-flex align-items-center justify-content-center';
                loadingOverlay.innerHTML = `
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Đang tải...</span>
                    </div>
                `;
                chartContainer.querySelector('#priceChartContainer').appendChild(loadingOverlay);
            }
        }
        
        // Sử dụng fetchAPI nhưng không hiển thị loading toàn màn hình
        return fetchAPI(`/api/market/chart?symbol=${chartConfig.symbol}&timeframe=${chartConfig.timeframe}`, {}, false, 
            // Success callback
            (data) => {
                if (data.labels && data.prices) {
                    updateChart(data.labels, data.prices);
                } else {
                    console.error('Invalid chart data format:', data);
                    showAlert('warning', 'Định dạng dữ liệu biểu đồ không hợp lệ');
                }
                
                // Xóa trạng thái loading
                if (chartContainer) {
                    chartContainer.classList.remove('loading');
                    const loadingOverlay = chartContainer.querySelector('.chart-loading');
                    if (loadingOverlay) {
                        loadingOverlay.remove();
                    }
                }
            },
            // Error callback
            (error) => {
                console.error('Error fetching chart data:', error);
                showAlert('danger', `Lỗi khi tải dữ liệu biểu đồ: ${error.message}`);
                
                // Xóa trạng thái loading
                if (chartContainer) {
                    chartContainer.classList.remove('loading');
                    const loadingOverlay = chartContainer.querySelector('.chart-loading');
                    if (loadingOverlay) {
                        loadingOverlay.remove();
                    }
                }
            }
        );
    }
    
    /**
     * Update chart with new data
     * @param {Array} labels - Array of time labels
     * @param {Array} prices - Array of price values
     */
    function updateChart(labels, prices) {
        if (!marketChart) return;
        
        const chartData = {
            labels: labels,
            datasets: [{
                label: `${chartConfig.symbol} Price`,
                data: prices,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderWidth: 2,
                fill: chartConfig.type === 'line',
                tension: 0.4
            }]
        };
        
        marketChart.data = chartData;
        marketChart.update();
    }
    
    /**
     * Enable auto refresh of market data
     */
    function enableAutoRefresh() {
        // Clear existing interval if any
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
        
        // Set new interval (refresh every 30 seconds)
        autoRefreshInterval = setInterval(loadMarketData, 30000);
    }
    
    /**
     * Disable auto refresh of market data
     */
    function disableAutoRefresh() {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
    }
    
    /**
     * Show toast message
     * @param {string} type - 'success' or 'error'
     * @param {string} message - Message to display
     */
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
    
    // Initial load of market data
    loadMarketData();
});