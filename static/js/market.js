/**
 * Market.js - Script for market data and chart functionality
 * 
 * This script handles fetching real-time market data from Binance API 
 * and rendering charts and updates for the market page.
 */

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
            loadMarketData();
        });
    }
    
    // Handle auto refresh toggle
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', function() {
            if (this.checked) {
                enableAutoRefresh();
            } else {
                disableAutoRefresh();
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
     */
    function loadMarketData() {
        // Show loading indicator
        document.body.classList.add('loading');
        
        // Fetch real-time data from API
        fetch(`/api/market/data?timeframe=${chartConfig.timeframe}`)
            .then(response => response.json())
            .then(data => {
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
                
                // Hide loading indicator
                document.body.classList.remove('loading');
                
                // Also update chart data
                loadChartData();
            })
            .catch(error => {
                console.error('Error fetching market data:', error);
                document.body.classList.remove('loading');
                
                // Show error toast
                showToast('error', 'Lỗi khi tải dữ liệu thị trường');
            });
    }
    
    /**
     * Load chart data from API
     */
    function loadChartData() {
        if (!marketChart) return;
        
        // Fetch chart data from API
        fetch(`/api/market/chart?symbol=${chartConfig.symbol}&timeframe=${chartConfig.timeframe}`)
            .then(response => response.json())
            .then(data => {
                if (data.labels && data.prices) {
                    updateChart(data.labels, data.prices);
                } else {
                    console.error('Invalid chart data format:', data);
                }
            })
            .catch(error => {
                console.error('Error fetching chart data:', error);
            });
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