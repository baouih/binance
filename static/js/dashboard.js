// Dashboard.js - JavaScript for CryptoBot Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Initialize
    initDashboard();
    
    // Setup theme switcher
    setupThemeSwitcher();
    
    // Setup charts
    setupCharts();
    
    // Add event listeners
    addEventListeners();
});

// Initialize dashboard components
function initDashboard() {
    // Replace Feather icons
    feather.replace();
    
    // Set current date/time
    updateDateTime();
    setInterval(updateDateTime, 60000);
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Update date and time display
function updateDateTime() {
    const now = new Date();
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const timeOptions = { hour: '2-digit', minute: '2-digit' };
    
    const dateElement = document.getElementById('currentDate');
    const timeElement = document.getElementById('currentTime');
    
    if (dateElement) {
        dateElement.textContent = now.toLocaleDateString('vi-VN', dateOptions);
    }
    
    if (timeElement) {
        timeElement.textContent = now.toLocaleTimeString('vi-VN', timeOptions);
    }
}

// Setup theme switcher
function setupThemeSwitcher() {
    const themeSwitch = document.getElementById('themeSwitch');
    
    if (themeSwitch) {
        // Check for saved theme
        const savedTheme = localStorage.getItem('theme') || 'dark';
        
        // Apply saved theme
        if (savedTheme === 'light') {
            document.documentElement.setAttribute('data-bs-theme', 'light');
            themeSwitch.checked = true;
        } else {
            document.documentElement.setAttribute('data-bs-theme', 'dark');
            themeSwitch.checked = false;
        }
        
        // Theme switch handler
        themeSwitch.addEventListener('change', function() {
            if (this.checked) {
                document.documentElement.setAttribute('data-bs-theme', 'light');
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            }
            // Redraw charts to match theme
            setupCharts();
        });
    }
}

// Setup charts
function setupCharts() {
    setupPriceChart();
    setupPerformanceChart();
    setupSentimentChart();
    setupMarketRegimeGauge();
}

// Setup price chart
function setupPriceChart() {
    const ctx = document.getElementById('priceChart');
    
    if (!ctx) return;
    
    // Sample data - in production this would come from your API
    const dates = [];
    const prices = [];
    const buyPoints = [];
    const sellPoints = [];
    
    // Generate sample data
    const now = new Date();
    const basePrice = 83500;
    
    for (let i = 30; i >= 0; i--) {
        const date = new Date();
        date.setHours(now.getHours() - i);
        dates.push(date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }));
        
        // Simulate price movement
        const noise = Math.sin(i * 0.4) * 500 + Math.random() * 200 - 100;
        const price = basePrice + noise;
        prices.push(price);
        
        // Add some sample trade points
        if (i === 25) {
            buyPoints.push(price - 50);
        } else {
            buyPoints.push(null);
        }
        
        if (i === 10) {
            sellPoints.push(price + 50);
        } else {
            sellPoints.push(null);
        }
    }
    
    // Get theme colors
    const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDarkTheme ? '#f8f9fa' : '#212529';
    const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Create the chart
    if (window.priceChart) {
        window.priceChart.destroy();
    }
    
    window.priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'BTC/USDT',
                    data: prices,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Buy',
                    data: buyPoints,
                    borderColor: 'rgba(0, 0, 0, 0)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    pointBackgroundColor: '#27ae60',
                    pointBorderColor: '#fff',
                    pointRadius: 6,
                    pointHoverRadius: 8
                },
                {
                    label: 'Sell',
                    data: sellPoints,
                    borderColor: 'rgba(0, 0, 0, 0)',
                    backgroundColor: 'rgba(0, 0, 0, 0)',
                    pointBackgroundColor: '#e74c3c',
                    pointBorderColor: '#fff',
                    pointRadius: 6,
                    pointHoverRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        color: textColor
                    }
                },
                y: {
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        color: textColor,
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            if (context.dataset.label === 'BTC/USDT') {
                                return 'Price: $' + context.raw.toLocaleString();
                            } else if (context.dataset.label === 'Buy' && context.raw !== null) {
                                return 'Buy: $' + context.raw.toLocaleString();
                            } else if (context.dataset.label === 'Sell' && context.raw !== null) {
                                return 'Sell: $' + context.raw.toLocaleString();
                            }
                            return '';
                        }
                    }
                }
            }
        }
    });
}

// Setup performance chart
function setupPerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    
    if (!ctx) return;
    
    // Sample data
    const dates = [];
    const balances = [];
    const marketReturns = [];
    
    // Generate sample data
    const now = new Date();
    const baseBalance = 10000;
    const baseMarket = 10000;
    
    let currentBalance = baseBalance;
    let currentMarket = baseMarket;
    
    for (let i = 30; i >= 0; i--) {
        const date = new Date();
        date.setDate(now.getDate() - i);
        dates.push(date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }));
        
        // Simulate balance growth with volatility
        currentBalance = currentBalance * (1 + (Math.random() * 0.02 - 0.005));
        balances.push(currentBalance);
        
        // Simulate market returns (slightly worse)
        currentMarket = currentMarket * (1 + (Math.random() * 0.015 - 0.005));
        marketReturns.push(currentMarket);
    }
    
    // Get theme colors
    const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDarkTheme ? '#f8f9fa' : '#212529';
    const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Create the chart
    if (window.performanceChart) {
        window.performanceChart.destroy();
    }
    
    window.performanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Bot Performance',
                    data: balances,
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1
                },
                {
                    label: 'Market',
                    data: marketReturns,
                    borderColor: '#95a5a6',
                    backgroundColor: 'rgba(149, 165, 166, 0.1)',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor,
                        display: false
                    },
                    ticks: {
                        color: textColor,
                        maxTicksLimit: 6
                    }
                },
                y: {
                    grid: {
                        color: gridColor
                    },
                    ticks: {
                        color: textColor,
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: textColor
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += '$' + context.raw.toLocaleString();
                            return label;
                        }
                    }
                }
            }
        }
    });
}

// Setup sentiment chart
function setupSentimentChart() {
    const ctx = document.getElementById('sentimentChart');
    
    if (!ctx) return;
    
    // Sample data
    const dates = [];
    const btcSentiment = [];
    const ethSentiment = [];
    
    // Generate sample data
    const now = new Date();
    
    for (let i = 10; i >= 0; i--) {
        const date = new Date();
        date.setHours(now.getHours() - i*6);
        dates.push(date.toLocaleDateString('vi-VN', { day: '2-digit', hour: '2-digit' }));
        
        // Simulate sentiment values (0-100)
        btcSentiment.push(35 + Math.sin(i*0.8) * 20 + Math.random() * 5);
        ethSentiment.push(45 + Math.cos(i*0.8) * 15 + Math.random() * 5);
    }
    
    // Get theme colors
    const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDarkTheme ? '#f8f9fa' : '#212529';
    const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    
    // Create the chart
    if (window.sentimentChart) {
        window.sentimentChart.destroy();
    }
    
    window.sentimentChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'BTC Sentiment',
                    data: btcSentiment,
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'ETH Sentiment',
                    data: ethSentiment,
                    borderColor: '#9b59b6',
                    backgroundColor: 'rgba(155, 89, 182, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            scales: {
                x: {
                    grid: {
                        color: gridColor,
                        display: false
                    },
                    ticks: {
                        color: textColor,
                        maxTicksLimit: 4
                    }
                },
                y: {
                    grid: {
                        color: gridColor
                    },
                    min: 0,
                    max: 100,
                    ticks: {
                        color: textColor,
                        stepSize: 25
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: textColor
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            
                            const value = context.raw;
                            let sentiment = '';
                            
                            if (value < 25) {
                                sentiment = 'Extreme Fear';
                            } else if (value < 40) {
                                sentiment = 'Fear';
                            } else if (value < 60) {
                                sentiment = 'Neutral';
                            } else if (value < 75) {
                                sentiment = 'Greed';
                            } else {
                                sentiment = 'Extreme Greed';
                            }
                            
                            return label + value.toFixed(1) + ' (' + sentiment + ')';
                        }
                    }
                }
            }
        }
    });
}

// Setup market regime gauge chart
function setupMarketRegimeGauge() {
    const ctx = document.getElementById('marketRegimeGauge');
    
    if (!ctx) return;
    
    // Get theme colors
    const isDarkTheme = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDarkTheme ? '#f8f9fa' : '#212529';
    
    // Sample data - in a real app this would come from your API
    const regimes = ['Trending Up', 'Trending Down', 'Ranging', 'Volatile', 'Breakout'];
    const data = [15, 5, 45, 30, 5]; // Percentages
    
    // Colors for each regime
    const colors = [
        '#27ae60', // Trending Up - Green
        '#e74c3c', // Trending Down - Red
        '#3498db', // Ranging - Blue
        '#f39c12', // Volatile - Orange
        '#9b59b6'  // Breakout - Purple
    ];
    
    if (window.regimeChart) {
        window.regimeChart.destroy();
    }
    
    window.regimeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: regimes,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: isDarkTheme ? 'rgba(45, 55, 72, 0.9)' : '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: textColor,
                        padding: 10,
                        boxWidth: 15
                    }
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.raw + '%';
                        }
                    }
                }
            }
        }
    });
}

// Add event listeners
function addEventListeners() {
    // Timeframe buttons for price chart
    const timeframeButtons = document.querySelectorAll('[data-timeframe]');
    timeframeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            timeframeButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            
            // In a real app, you would fetch new data for selected timeframe and update chart
            console.log('Selected timeframe:', this.getAttribute('data-timeframe'));
            
            // For demo, we'll just regenerate the price chart with new random data
            setupPriceChart();
        });
    });
    
    // Refresh positions button
    const refreshPositionsBtn = document.getElementById('refreshPositions');
    if (refreshPositionsBtn) {
        refreshPositionsBtn.addEventListener('click', function() {
            // In a real app, you would fetch the latest positions
            console.log('Refreshing positions...');
            
            // Show loading animation
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            
            // Simulate delay
            setTimeout(() => {
                // Reset button
                this.innerHTML = '<i data-feather="refresh-cw" class="icon-sm"></i>';
                feather.replace();
                
                // Show success message
                const toast = new bootstrap.Toast(document.getElementById('refreshSuccessToast'));
                toast.show();
            }, 1000);
        });
    }
    
    // Strategy toggle switches
    const strategyToggles = document.querySelectorAll('.form-check-input[id^="strategy"]');
    strategyToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            console.log('Strategy', this.id, 'is now', this.checked ? 'active' : 'inactive');
            
            // In a real app, you would update the strategy status via API
        });
    });
}