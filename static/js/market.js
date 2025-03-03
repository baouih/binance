// JavaScript cho trang thị trường
document.addEventListener('DOMContentLoaded', function() {
    console.log('Market.js loaded');
    
    // Cài đặt biểu đồ thị trường
    setupMarketChart();
    
    // Cài đặt cập nhật tự động
    setupAutoRefresh();
    
    // Xử lý nút làm mới
    document.getElementById('refresh-market').addEventListener('click', function() {
        refreshMarketData();
    });
    
    // Xử lý thay đổi khung thời gian
    document.querySelectorAll('.timeframe-option').forEach(function(option) {
        option.addEventListener('click', function() {
            const timeframe = this.getAttribute('data-value');
            document.getElementById('timeframe-text').textContent = this.textContent;
            updateChartTimeframe(timeframe);
        });
    });
});

// Tạo biểu đồ thị trường
function setupMarketChart() {
    const ctx = document.getElementById('marketChart').getContext('2d');
    
    // Dữ liệu mẫu cho biểu đồ
    const labels = [];
    const prices = [];
    
    // Tạo dữ liệu mẫu cho 30 ngày
    const today = new Date();
    for (let i = 29; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        labels.push(date.toLocaleDateString('vi-VN'));
        
        // Giá mẫu với một vài biến động
        const basePrice = 80000 + Math.random() * 5000;
        prices.push(basePrice + (Math.sin(i/2) * 2000));
    }
    
    window.marketChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'BTC/USDT',
                data: prices,
                borderColor: '#1f77b4',
                backgroundColor: 'rgba(31, 119, 180, 0.1)',
                borderWidth: 2,
                tension: 0.2,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('en-US', { 
                                    style: 'currency', 
                                    currency: 'USD' 
                                }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    },
                    grid: {
                        color: 'rgba(200, 200, 200, 0.15)'
                    }
                }
            }
        }
    });
}

// Cập nhật khung thời gian biểu đồ
function updateChartTimeframe(timeframe) {
    console.log(`Updating chart timeframe to: ${timeframe}`);
    
    // Trong ứng dụng thực tế, sẽ gọi API để lấy dữ liệu cho khung thời gian mới
    // API endpoint có thể là: `/api/market/chart?symbol=BTCUSDT&timeframe=${timeframe}`
    
    // Mô phỏng cập nhật dữ liệu
    const today = new Date();
    const labels = [];
    const prices = [];
    
    let days = 30;
    switch(timeframe) {
        case '1h':
            days = 1;
            break;
        case '4h':
            days = 2;
            break;
        case '24h':
            days = 7;
            break;
        case '7d':
            days = 30;
            break;
        case '30d':
            days = 90;
            break;
    }
    
    // Tạo dữ liệu mới
    for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        
        if (timeframe === '1h' || timeframe === '4h') {
            date.setHours(today.getHours() - i);
            labels.push(date.toLocaleTimeString('vi-VN'));
        } else {
            labels.push(date.toLocaleDateString('vi-VN'));
        }
        
        // Giá mẫu với một vài biến động
        const basePrice = 80000 + Math.random() * 5000;
        prices.push(basePrice + (Math.sin(i/2) * 2000));
    }
    
    // Cập nhật dữ liệu biểu đồ
    window.marketChart.data.labels = labels;
    window.marketChart.data.datasets[0].data = prices;
    window.marketChart.update();
}

// Cài đặt cập nhật tự động
function setupAutoRefresh() {
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    let refreshInterval;
    
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', function() {
            if (this.checked) {
                refreshInterval = setInterval(refreshMarketData, 30000); // Cập nhật mỗi 30 giây
                console.log('Auto refresh enabled');
            } else {
                clearInterval(refreshInterval);
                console.log('Auto refresh disabled');
            }
        });
        
        // Khởi tạo auto refresh nếu checkbox được chọn
        if (autoRefreshCheckbox.checked) {
            refreshInterval = setInterval(refreshMarketData, 30000);
            console.log('Auto refresh initialized');
        }
    }
}

// Làm mới dữ liệu thị trường
function refreshMarketData() {
    console.log('Refreshing market data...');
    
    // Gọi API để lấy dữ liệu thị trường mới nhất
    fetch('/api/market')
        .then(response => response.json())
        .then(data => {
            console.log('Market data refreshed:', data);
            updateMarketUI(data);
        })
        .catch(error => {
            console.error('Error refreshing market data:', error);
        });
}

// Cập nhật UI thị trường với dữ liệu mới
function updateMarketUI(data) {
    // Cập nhật giá BTC
    if (data.btc_price) {
        document.getElementById('btc-price').textContent = `$${parseFloat(data.btc_price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
    
    // Cập nhật giá ETH
    if (data.eth_price) {
        document.getElementById('eth-price').textContent = `$${parseFloat(data.eth_price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
    
    // Cập nhật giá SOL
    if (data.sol_price) {
        document.getElementById('sol-price').textContent = `$${parseFloat(data.sol_price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
    
    // Cập nhật giá BNB
    if (data.bnb_price) {
        document.getElementById('bnb-price').textContent = `$${parseFloat(data.bnb_price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }
    
    // Cập nhật thông tin Market Regime (nếu có)
    if (data.market_regime) {
        const regimeElements = document.querySelectorAll('.indicator-dot');
        regimeElements.forEach(element => {
            element.classList.remove('active');
        });
        
        // Tìm và kích hoạt chế độ thị trường hiện tại
        const currentRegimeClass = data.market_regime.toLowerCase();
        const currentRegimeElement = document.querySelector(`.indicator-dot.${currentRegimeClass}`);
        if (currentRegimeElement) {
            currentRegimeElement.classList.add('active');
        }
    }
    
    // Hiển thị thông báo cập nhật
    const timestamp = new Date().toLocaleTimeString('vi-VN');
    console.log(`Market data updated at ${timestamp}`);
}