/**
 * BinanceTrader Bot Dashboard JavaScript
 * 
 * This file contains all the client-side logic for the trading bot dashboard
 * including real-time updates, chart rendering, and interactive UI elements.
 */

// Global variables
const socket = io();
let equityCurveChart, performanceRadarChart;
const refreshInterval = 10000; // 10 seconds refresh interval

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    
    // Initialize socket connection
    initializeSocket();
    
    // Initialize charts
    initializeCharts();
    
    // Initialize event listeners
    initializeEventListeners();
    
    // Initial data fetch
    fetchDashboardData();
});

/**
 * Initialize Socket.io connection and event handlers
 */
function initializeSocket() {
    socket.on('connect', function() {
        console.log('Connected to server');
        showToast('Connected to server', 'success');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        showToast('Connection lost. Reconnecting...', 'warning');
    });
    
    socket.on('price_update', function(data) {
        console.log('Price update:', data);
        updatePrices(data);
    });
    
    socket.on('position_update', function(data) {
        console.log('Position update:', data);
        updatePositions(data);
    });
    
    socket.on('trade_update', function(data) {
        console.log('Trade update:', data);
        updateTrades(data);
        showToast(`Trade ${data.action}: ${data.symbol} ${data.type}`, 'info');
    });
    
    socket.on('account_update', function(data) {
        console.log('Account update:', data);
        updateAccount(data);
    });
    
    socket.on('signal_update', function(data) {
        console.log('Signal update:', data);
        updateSignals(data);
    });
    
    socket.on('bot_status', function(data) {
        console.log('Bot status update:', data);
        updateBotStatus(data);
    });
    
    socket.on('backtest_results', function(data) {
        console.log('Backtest results:', data);
        displayBacktestResults(data);
    });
    
    socket.on('api_test_result', function(data) {
        console.log('API test result:', data);
        showToast(data.message, data.success ? 'success' : 'danger');
    });
    
    socket.on('telegram_test_result', function(data) {
        console.log('Telegram test result:', data);
        showToast(data.message, data.success ? 'success' : 'danger');
    });
    
    socket.on('email_test_result', function(data) {
        console.log('Email test result:', data);
        showToast(data.message, data.success ? 'success' : 'danger');
    });
}

/**
 * Initialize charts used in dashboard
 */
function initializeCharts() {
    // Equity Curve Chart
    const equityCtx = document.getElementById('equityCurveChart');
    if (equityCtx) {
        equityCurveChart = new Chart(equityCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Equity',
                        data: [],
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Drawdown',
                        data: [],
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Balance ($)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Drawdown (%)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }
    
    // Performance Radar Chart
    const performanceCtx = document.getElementById('performanceRadarChart');
    if (performanceCtx) {
        performanceRadarChart = new Chart(performanceCtx, {
            type: 'radar',
            data: {
                labels: ['Win Rate', 'Profit Factor', 'Risk/Reward', 'Sharpe Ratio', 'Recovery Factor'],
                datasets: [{
                    label: 'Performance',
                    data: [0, 0, 0, 0, 0],
                    fill: true,
                    backgroundColor: 'rgba(13, 110, 253, 0.2)',
                    borderColor: '#0d6efd',
                    pointBackgroundColor: '#0d6efd',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#0d6efd'
                }]
            },
            options: {
                elements: {
                    line: {
                        borderWidth: 3
                    }
                },
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 0,
                        suggestedMax: 1
                    }
                }
            }
        });
    }
}

/**
 * Initialize event listeners for UI elements
 */
function initializeEventListeners() {
    // Bot control buttons
    const startBot = document.getElementById('start-bot');
    if (startBot) {
        startBot.addEventListener('click', function() {
            socket.emit('bot_control', { action: 'start' });
        });
    }
    
    const stopBot = document.getElementById('stop-bot');
    if (stopBot) {
        stopBot.addEventListener('click', function() {
            socket.emit('bot_control', { action: 'stop' });
        });
    }
    
    const restartBot = document.getElementById('restart-bot');
    if (restartBot) {
        restartBot.addEventListener('click', function() {
            socket.emit('bot_control', { action: 'restart' });
        });
    }
    
    // Close position buttons
    document.querySelectorAll('.close-position-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const positionId = this.getAttribute('data-position-id');
            socket.emit('close_position', { position_id: positionId });
        });
    });
    
    // View all buttons
    const viewAllPositions = document.getElementById('view-all-positions');
    if (viewAllPositions) {
        viewAllPositions.addEventListener('click', function() {
            document.getElementById('positions-tab').click();
        });
    }
    
    const viewAllTrades = document.getElementById('view-all-trades');
    if (viewAllTrades) {
        viewAllTrades.addEventListener('click', function() {
            document.getElementById('trades-tab').click();
        });
    }
    
    // Save settings button
    const saveSettings = document.getElementById('save-settings');
    if (saveSettings) {
        saveSettings.addEventListener('click', function() {
            saveAllSettings();
        });
    }
    
    // Test connection buttons
    const testApiBtn = document.getElementById('test-api-btn');
    if (testApiBtn) {
        testApiBtn.addEventListener('click', function() {
            socket.emit('test_api');
        });
    }
    
    const testTelegramBtn = document.getElementById('test-telegram-btn');
    if (testTelegramBtn) {
        testTelegramBtn.addEventListener('click', function() {
            socket.emit('test_telegram');
        });
    }
    
    const testEmailBtn = document.getElementById('test-email-btn');
    if (testEmailBtn) {
        testEmailBtn.addEventListener('click', function() {
            socket.emit('test_email');
        });
    }
    
    // Backtest form submission
    const backtestForm = document.getElementById('backtest-form');
    if (backtestForm) {
        backtestForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const form = this;
            const formData = new FormData(form);
            const params = {};
            
            for (let [key, value] of formData.entries()) {
                params[key] = value;
            }
            
            socket.emit('run_backtest', params);
            
            // Show loading state
            const backtestResults = document.getElementById('backtest-results');
            if (backtestResults) {
                backtestResults.innerHTML = `
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p>Running backtest... This may take a minute.</p>
                    </div>
                `;
            }
        });
    }
    
    // Toggle leverage options
    const useLeverage = document.getElementById('use_leverage');
    if (useLeverage) {
        useLeverage.addEventListener('change', function() {
            const leverageOptions = document.querySelector('.leverage-options');
            if (leverageOptions) {
                if (this.checked) {
                    leverageOptions.classList.remove('d-none');
                } else {
                    leverageOptions.classList.add('d-none');
                }
            }
        });
    }
    
    // Generate report buttons
    document.querySelectorAll('.report-card button').forEach(btn => {
        btn.addEventListener('click', function() {
            const reportType = this.closest('.report-card').querySelector('h5').textContent;
            socket.emit('generate_report', { type: reportType });
            showToast(`Generating ${reportType}...`, 'info');
        });
    });
}

/**
 * Fetch initial dashboard data
 */
function fetchDashboardData() {
    socket.emit('get_dashboard_data');
}

/**
 * Update prices displayed in the UI
 */
function updatePrices(data) {
    // Update current prices in open positions
    document.querySelectorAll('[data-price-symbol]').forEach(elem => {
        const symbol = elem.getAttribute('data-price-symbol');
        if (data[symbol]) {
            elem.textContent = formatPrice(data[symbol]);
        }
    });
}

/**
 * Update positions displayed in the UI
 */
function updatePositions(data) {
    // Handle position updates - could be a full refresh or incremental updates
    if (data.type === 'full_refresh') {
        // TODO: Implement full refresh of positions
    } else if (data.type === 'update') {
        // TODO: Implement update of specific position
    } else if (data.type === 'close') {
        // TODO: Implement removal of closed position
    }
}

/**
 * Update trades displayed in the UI
 */
function updateTrades(data) {
    // Handle trade updates - could be a full refresh or incremental updates
    if (data.type === 'full_refresh') {
        // TODO: Implement full refresh of trades
    } else if (data.type === 'new') {
        // TODO: Implement adding new trade
    }
}

/**
 * Update account information
 */
function updateAccount(data) {
    // Update balance and other account info
    if (data.balance) {
        document.querySelectorAll('[data-account="balance"]').forEach(elem => {
            elem.textContent = `$${data.balance.toFixed(2)}`;
        });
    }
    
    // Update equity curve if available
    if (data.equity_data && equityCurveChart) {
        equityCurveChart.data.labels = data.equity_data.labels;
        equityCurveChart.data.datasets[0].data = data.equity_data.equity;
        equityCurveChart.data.datasets[1].data = data.equity_data.drawdown;
        equityCurveChart.update();
    }
    
    // Update performance metrics if available
    if (data.performance && performanceRadarChart) {
        const metrics = data.performance;
        const chartData = [
            metrics.win_rate ? metrics.win_rate / 100 : 0,
            metrics.profit_factor ? Math.min(metrics.profit_factor / 5, 1) : 0,
            metrics.risk_reward ? Math.min(metrics.risk_reward / 5, 1) : 0,
            metrics.sharpe_ratio ? Math.min(metrics.sharpe_ratio / 3, 1) : 0,
            metrics.recovery_factor ? Math.min(metrics.recovery_factor / 3, 1) : 0
        ];
        
        performanceRadarChart.data.datasets[0].data = chartData;
        performanceRadarChart.update();
    }
}

/**
 * Update trading signals
 */
function updateSignals(data) {
    // Update composite score and signal indicators
    if (data.composite_score !== undefined) {
        const signalStrength = document.querySelector('.signal-strength');
        if (signalStrength) {
            let signalText, signalClass;
            
            if (data.composite_score > 0.5) {
                signalText = 'Strong Buy';
                signalClass = 'bg-success';
            } else if (data.composite_score > 0) {
                signalText = 'Buy';
                signalClass = 'bg-success';
            } else if (data.composite_score > -0.5) {
                signalText = 'Sell';
                signalClass = 'bg-danger';
            } else {
                signalText = 'Strong Sell';
                signalClass = 'bg-danger';
            }
            
            signalStrength.innerHTML = `
                <span class="badge ${signalClass}">${signalText}</span>
            `;
        }
        
        // Update progress bar for composite score
        const progressBar = document.querySelector('.indicators-breakdown .progress-bar');
        if (progressBar) {
            progressBar.style.width = `${(data.composite_score + 1) * 50}%`;
            progressBar.className = `progress-bar ${data.composite_score >= 0 ? 'bg-success' : 'bg-danger'}`;
        }
    }
    
    // Update individual indicators
    if (data.indicators) {
        const signalList = document.querySelector('.signal-list');
        if (signalList) {
            signalList.innerHTML = '';
            
            for (const [indicator, signal] of Object.entries(data.indicators)) {
                let badgeClass = 'bg-secondary';
                let signalText = 'Neutral';
                
                if (signal > 0.5) {
                    badgeClass = 'bg-success';
                    signalText = 'Buy';
                } else if (signal > 0) {
                    badgeClass = 'bg-success';
                    signalText = 'Weak Buy';
                } else if (signal > -0.5) {
                    badgeClass = 'bg-danger';
                    signalText = 'Weak Sell';
                } else if (signal <= -0.5) {
                    badgeClass = 'bg-danger';
                    signalText = 'Sell';
                }
                
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
                listItem.innerHTML = `
                    ${indicator}
                    <span class="badge ${badgeClass}">${signalText}</span>
                `;
                
                signalList.appendChild(listItem);
            }
        }
    }
}

/**
 * Update bot status display
 */
function updateBotStatus(data) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    const startBtn = document.getElementById('start-bot');
    const stopBtn = document.getElementById('stop-bot');
    
    if (statusDot && statusText && startBtn && stopBtn) {
        if (data.running) {
            statusDot.classList.add('active');
            statusText.textContent = 'Running';
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            statusDot.classList.remove('active');
            statusText.textContent = 'Stopped';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }
}

/**
 * Display backtest results
 */
function displayBacktestResults(data) {
    const backtestResults = document.getElementById('backtest-results');
    const performanceMetrics = document.getElementById('performance-metrics');
    const backtestTrades = document.getElementById('backtest-trades');
    
    if (!backtestResults || !performanceMetrics || !backtestTrades) return;
    
    if (data.error) {
        backtestResults.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle me-2"></i>
                ${data.error}
            </div>
        `;
        return;
    }
    
    // Display equity curve chart
    backtestResults.innerHTML = `
        <canvas id="backtestEquityCurve" height="300"></canvas>
    `;
    
    const ctx = document.getElementById('backtestEquityCurve').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.dates,
            datasets: [
                {
                    label: 'Equity Curve',
                    data: data.equity_curve,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    fill: true
                },
                {
                    label: 'Drawdown',
                    data: data.drawdown,
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    fill: true,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Balance ($)'
                    }
                },
                y1: {
                    position: 'right',
                    title: {
                        display: true,
                        text: 'Drawdown (%)'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                }
            }
        }
    });
    
    // Display performance metrics
    const metrics = data.performance_metrics;
    performanceMetrics.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <table class="table table-bordered">
                    <tr>
                        <td>Initial Balance</td>
                        <td class="fw-bold">$${metrics.initial_balance.toFixed(2)}</td>
                    </tr>
                    <tr>
                        <td>Final Balance</td>
                        <td class="fw-bold">$${metrics.final_balance.toFixed(2)}</td>
                    </tr>
                    <tr>
                        <td>Total Return</td>
                        <td class="fw-bold ${metrics.total_return >= 0 ? 'text-success' : 'text-danger'}">
                            ${metrics.total_return >= 0 ? '+' : ''}${metrics.total_return.toFixed(2)}%
                        </td>
                    </tr>
                    <tr>
                        <td>Win Rate</td>
                        <td class="fw-bold">${metrics.win_rate.toFixed(2)}%</td>
                    </tr>
                    <tr>
                        <td>Profit Factor</td>
                        <td class="fw-bold">${metrics.profit_factor.toFixed(2)}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <table class="table table-bordered">
                    <tr>
                        <td>Max Drawdown</td>
                        <td class="fw-bold text-danger">${metrics.max_drawdown.toFixed(2)}%</td>
                    </tr>
                    <tr>
                        <td>Sharpe Ratio</td>
                        <td class="fw-bold">${metrics.sharpe_ratio.toFixed(2)}</td>
                    </tr>
                    <tr>
                        <td>Total Trades</td>
                        <td class="fw-bold">${metrics.total_trades}</td>
                    </tr>
                    <tr>
                        <td>Avg Profit/Trade</td>
                        <td class="fw-bold ${metrics.avg_profit >= 0 ? 'text-success' : 'text-danger'}">
                            $${metrics.avg_profit.toFixed(2)}
                        </td>
                    </tr>
                    <tr>
                        <td>Risk Reward Ratio</td>
                        <td class="fw-bold">${metrics.risk_reward_ratio.toFixed(2)}</td>
                    </tr>
                </table>
            </div>
        </div>
    `;
    
    // Display trade list
    let tradesHTML = `
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Type</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>PnL ($)</th>
                        <th>PnL (%)</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.trades.forEach((trade, index) => {
        tradesHTML += `
            <tr class="${trade.pnl >= 0 ? 'table-success' : 'table-danger'}">
                <td>${index + 1}</td>
                <td>${trade.type}</td>
                <td>$${trade.entry_price.toFixed(2)}</td>
                <td>$${trade.exit_price.toFixed(2)}</td>
                <td class="${trade.pnl >= 0 ? 'text-success' : 'text-danger'}">
                    ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
                </td>
                <td class="${trade.pnl >= 0 ? 'text-success' : 'text-danger'}">
                    ${trade.pnl >= 0 ? '+' : ''}${trade.pnl_percent.toFixed(2)}%
                </td>
            </tr>
        `;
    });
    
    tradesHTML += `
                </tbody>
            </table>
        </div>
    `;
    
    backtestTrades.innerHTML = tradesHTML;
}

/**
 * Save all settings from settings tabs
 */
function saveAllSettings() {
    // General settings
    const generalSettings = {
        bot_name: document.getElementById('bot_name')?.value,
        default_symbol: document.getElementById('default_symbol')?.value,
        default_timeframe: document.getElementById('default_timeframe')?.value,
        auto_start: document.getElementById('auto_start')?.checked,
        auto_restart: document.getElementById('auto_restart')?.checked,
        test_mode: document.getElementById('test_mode')?.checked
    };
    
    // Strategy settings - this would get more complex based on active strategy
    const strategySettings = {
        active_strategy: document.getElementById('active_strategy')?.value,
        // Additional strategy-specific settings would be collected here
        rsi: {
            period: document.getElementById('rsi_period')?.value,
            overbought: document.getElementById('rsi_overbought')?.value,
            oversold: document.getElementById('rsi_oversold')?.value
        },
        macd: {
            fast: document.getElementById('macd_fast')?.value,
            slow: document.getElementById('macd_slow')?.value,
            signal: document.getElementById('macd_signal')?.value
        }
        // More strategy settings...
    };
    
    // API settings
    const apiSettings = {
        api_key: document.getElementById('binance_api_key')?.value,
        api_secret: document.getElementById('binance_api_secret')?.value,
        use_testnet: document.getElementById('use_testnet')?.checked
    };
    
    // Notification settings
    const notificationSettings = {
        enable_notifications: document.getElementById('enable_notifications')?.checked,
        telegram: {
            enabled: document.getElementById('enable_telegram')?.checked,
            bot_token: document.getElementById('telegram_bot_token')?.value,
            chat_id: document.getElementById('telegram_chat_id')?.value
        },
        email: {
            enabled: document.getElementById('enable_email')?.checked,
            address: document.getElementById('email_address')?.value,
            smtp_server: document.getElementById('smtp_server')?.value,
            smtp_port: document.getElementById('smtp_port')?.value,
            smtp_username: document.getElementById('smtp_username')?.value,
            smtp_password: document.getElementById('smtp_password')?.value
        },
        events: {
            trade_open: document.getElementById('notify_trade_open')?.checked,
            trade_close: document.getElementById('notify_trade_close')?.checked,
            error: document.getElementById('notify_error')?.checked,
            daily_report: document.getElementById('notify_daily_report')?.checked,
            signal: document.getElementById('notify_signal')?.checked
        }
    };
    
    // Risk management settings
    const riskSettings = {
        max_risk_per_trade: document.getElementById('max_risk_per_trade')?.value,
        position_sizing_method: document.getElementById('position_sizing_method')?.value,
        max_open_positions: document.getElementById('max_open_positions')?.value,
        max_drawdown: document.getElementById('max_drawdown')?.value,
        use_trailing_stop: document.getElementById('use_trailing_stop')?.checked,
        trailing_stop_activation: document.getElementById('trailing_stop_activation')?.value,
        trailing_stop_callback: document.getElementById('trailing_stop_callback')?.value
    };
    
    // Combine all settings
    const allSettings = {
        general: generalSettings,
        strategy: strategySettings,
        api: apiSettings,
        notifications: notificationSettings,
        risk: riskSettings
    };
    
    // Send to server
    socket.emit('save_settings', allSettings);
    
    showToast('Settings saved successfully!', 'success');
}

/**
 * Display a toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * Format price with appropriate decimal places
 */
function formatPrice(price) {
    if (price < 0.1) {
        return price.toFixed(6);
    } else if (price < 1) {
        return price.toFixed(4);
    } else if (price < 1000) {
        return price.toFixed(2);
    } else {
        return price.toFixed(2);
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

/**
 * Format percentage value
 */
function formatPercentage(value) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}