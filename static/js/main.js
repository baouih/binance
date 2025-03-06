// Main JavaScript file for Binance Futures Trading Bot

// Global settings
const REFRESH_INTERVAL = 15000; // Refresh interval in milliseconds (15 seconds)
const DEFAULT_SYMBOL = 'BTCUSDT';
const DEFAULT_TIMEFRAME = '1h';

// DOM elements cached for performance
const elements = {
    // Balance elements
    balanceValue: document.getElementById('balance-value'),
    
    // Market data elements
    btcPrice: document.getElementById('btc-price'),
    btcChange: document.getElementById('btc-change'),
    btcHigh: document.getElementById('btc-high'),
    btcLow: document.getElementById('btc-low'),
    btcVolume: document.getElementById('btc-volume'),
    
    // Indicator elements
    rsiValue: document.getElementById('rsi-value'),
    rsiStatus: document.getElementById('rsi-status'),
    macdValue: document.getElementById('macd-value'),
    macdStatus: document.getElementById('macd-status'),
    bbValue: document.getElementById('bb-value'),
    bbStatus: document.getElementById('bb-status'),
    atrValue: document.getElementById('atr-value'),
    
    // Position elements
    activePositions: document.getElementById('active-positions'),
    positionHistory: document.getElementById('position-history'),
    
    // Action buttons
    refreshPositions: document.getElementById('refresh-positions'),
    autoTradeSwitch: document.getElementById('autoTradeSwitch')
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Initialize data
    initializeData();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up automatic refresh
    setupAutoRefresh();
});

// Initialize all data on page load
function initializeData() {
    fetchAccountBalance();
    fetchMarketData(DEFAULT_SYMBOL);
    fetchIndicators(DEFAULT_SYMBOL, DEFAULT_TIMEFRAME);
    fetchActivePositions();
    fetchPositionHistory();
}

// Setup event listeners
function setupEventListeners() {
    // Refresh positions button
    if (elements.refreshPositions) {
        elements.refreshPositions.addEventListener('click', () => {
            fetchActivePositions();
        });
    }
    
    // Auto trade switch
    if (elements.autoTradeSwitch) {
        elements.autoTradeSwitch.addEventListener('change', (e) => {
            const isEnabled = e.target.checked;
            toggleAutoTrading(isEnabled);
        });
    }
    
    // Trade pair selection change
    const tradePairSelect = document.getElementById('tradePair');
    if (tradePairSelect) {
        tradePairSelect.addEventListener('change', (e) => {
            const symbol = e.target.value;
            fetchIndicators(symbol, DEFAULT_TIMEFRAME);
        });
    }
    
    // Setup close position buttons (will be added dynamically)
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-close-position')) {
            const positionId = e.target.getAttribute('data-position-id');
            closePosition(positionId);
        }
    });
}

// Set up automatic data refresh
function setupAutoRefresh() {
    setInterval(() => {
        fetchAccountBalance();
        fetchMarketData(DEFAULT_SYMBOL);
        fetchIndicators(DEFAULT_SYMBOL, DEFAULT_TIMEFRAME);
        fetchActivePositions();
    }, REFRESH_INTERVAL);
}

// Fetch account balance from API
function fetchAccountBalance() {
    fetch('/api/account/balance')
        .then(response => response.json())
        .then(data => {
            if (elements.balanceValue) {
                elements.balanceValue.textContent = formatNumber(data.balance);
            }
        })
        .catch(error => {
            console.error('Error fetching account balance:', error);
        });
}

// Fetch market data from API
function fetchMarketData(symbol) {
    fetch(`/api/market_data/${symbol}`)
        .then(response => response.json())
        .then(data => {
            updateMarketData(data);
        })
        .catch(error => {
            console.error(`Error fetching market data for ${symbol}:`, error);
        });
}

// Update market data in UI
function updateMarketData(data) {
    if (elements.btcPrice) {
        elements.btcPrice.textContent = `$${formatNumber(data.price)}`;
        
        // Update price change with color
        const changeValue = elements.btcChange.querySelector('.change-value');
        const changePercent = elements.btcChange.querySelector('.change-percent');
        
        if (changeValue && changePercent) {
            changeValue.textContent = `$${formatNumber(data.price_change)}`;
            changePercent.textContent = formatNumber(data.price_change_percent);
            
            if (data.price_change >= 0) {
                elements.btcChange.className = 'mb-3 price-up';
                changeValue.textContent = `+$${formatNumber(data.price_change)}`;
                changePercent.textContent = `+${formatNumber(data.price_change_percent)}`;
            } else {
                elements.btcChange.className = 'mb-3 price-down';
            }
        }
        
        // Update high, low and volume
        if (elements.btcHigh) elements.btcHigh.textContent = `$${formatNumber(data.high_24h)}`;
        if (elements.btcLow) elements.btcLow.textContent = `$${formatNumber(data.low_24h)}`;
        if (elements.btcVolume) elements.btcVolume.textContent = formatNumber(data.volume_24h);
    }
}

// Fetch technical indicators from API
function fetchIndicators(symbol, timeframe) {
    fetch(`/api/indicators/${symbol}?timeframe=${timeframe}`)
        .then(response => response.json())
        .then(data => {
            updateIndicators(data);
        })
        .catch(error => {
            console.error(`Error fetching indicators for ${symbol}:`, error);
        });
}

// Update indicators in UI
function updateIndicators(data) {
    // Update RSI
    if (elements.rsiValue) {
        elements.rsiValue.textContent = formatNumber(data.rsi);
        
        let rsiStatusText = 'Trung lập';
        let rsiStatusClass = 'status status-neutral';
        
        if (data.rsi > 70) {
            rsiStatusText = 'Quá mua';
            rsiStatusClass = 'status status-bearish';
        } else if (data.rsi < 30) {
            rsiStatusText = 'Quá bán';
            rsiStatusClass = 'status status-bullish';
        }
        
        elements.rsiStatus.textContent = rsiStatusText;
        elements.rsiStatus.className = rsiStatusClass;
    }
    
    // Update MACD
    if (elements.macdValue) {
        elements.macdValue.textContent = formatNumber(data.macd.macd_line);
        
        let macdStatusText = 'Trung lập';
        let macdStatusClass = 'status status-neutral';
        
        if (data.macd.histogram > 0) {
            macdStatusText = 'Tăng';
            macdStatusClass = 'status status-bullish';
        } else if (data.macd.histogram < 0) {
            macdStatusText = 'Giảm';
            macdStatusClass = 'status status-bearish';
        }
        
        elements.macdStatus.textContent = macdStatusText;
        elements.macdStatus.className = macdStatusClass;
    }
    
    // Update Bollinger Bands
    if (elements.bbValue) {
        elements.bbValue.textContent = formatNumber(data.bollinger_bands.width) + '%';
        
        let bbStatusText = 'Trung lập';
        let bbStatusClass = 'status status-neutral';
        
        if (data.bollinger_bands.width > 5) {
            bbStatusText = 'Mở rộng';
            bbStatusClass = 'status status-bullish';
        } else if (data.bollinger_bands.width < 2) {
            bbStatusText = 'Thu hẹp';
            bbStatusClass = 'status status-bearish';
        }
        
        elements.bbStatus.textContent = bbStatusText;
        elements.bbStatus.className = bbStatusClass;
    }
    
    // Update ATR
    if (elements.atrValue) {
        elements.atrValue.textContent = formatNumber(data.atr);
    }
}

// Fetch active positions from API
function fetchActivePositions() {
    if (elements.activePositions) {
        elements.activePositions.innerHTML = '<tr><td colspan="11" class="text-center">Đang tải...</td></tr>';
    }
    
    fetch('/api/positions/active')
        .then(response => response.json())
        .then(data => {
            updateActivePositions(data);
        })
        .catch(error => {
            console.error('Error fetching active positions:', error);
            if (elements.activePositions) {
                elements.activePositions.innerHTML = '<tr><td colspan="11" class="text-center text-danger">Lỗi khi tải dữ liệu</td></tr>';
            }
        });
}

// Update active positions in UI
function updateActivePositions(positions) {
    if (!elements.activePositions) return;
    
    if (positions.length === 0) {
        elements.activePositions.innerHTML = '<tr><td colspan="11" class="text-center">Không có vị thế đang hoạt động</td></tr>';
        return;
    }
    
    let html = '';
    positions.forEach(position => {
        const pnlClass = position.pnl >= 0 ? 'profit' : 'loss';
        const positionClass = position.side === 'LONG' ? 'long-position' : 'short-position';
        
        html += `
            <tr class="${positionClass}">
                <td>${position.symbol}</td>
                <td>
                    <span class="badge ${position.side === 'LONG' ? 'bg-success' : 'bg-danger'}">${position.side}</span>
                </td>
                <td>${formatNumber(position.entry_price)}</td>
                <td>${formatNumber(position.current_price)}</td>
                <td>${formatNumber(position.stop_loss)}</td>
                <td>${formatNumber(position.take_profit)}</td>
                <td>${position.quantity}</td>
                <td>${position.leverage}x</td>
                <td class="${pnlClass}">
                    ${formatNumber(position.pnl)} (${formatNumber(position.pnl_percent)}%)
                </td>
                <td>${formatDate(position.entry_time)}</td>
                <td>
                    <button class="btn btn-sm btn-danger btn-close-position" data-position-id="${position.id}">
                        <i class="fas fa-times-circle"></i> Đóng
                    </button>
                </td>
            </tr>
        `;
    });
    
    elements.activePositions.innerHTML = html;
}

// Fetch position history from API
function fetchPositionHistory() {
    if (elements.positionHistory) {
        elements.positionHistory.innerHTML = '<tr><td colspan="9" class="text-center">Đang tải...</td></tr>';
    }
    
    fetch('/api/positions/history')
        .then(response => response.json())
        .then(data => {
            updatePositionHistory(data);
        })
        .catch(error => {
            console.error('Error fetching position history:', error);
            if (elements.positionHistory) {
                elements.positionHistory.innerHTML = '<tr><td colspan="9" class="text-center text-danger">Lỗi khi tải dữ liệu</td></tr>';
            }
        });
}

// Update position history in UI
function updatePositionHistory(positions) {
    if (!elements.positionHistory) return;
    
    if (positions.length === 0) {
        elements.positionHistory.innerHTML = '<tr><td colspan="9" class="text-center">Không có lịch sử giao dịch</td></tr>';
        return;
    }
    
    let html = '';
    positions.forEach(position => {
        const pnlClass = position.pnl >= 0 ? 'profit' : 'loss';
        const positionClass = position.side === 'LONG' ? 'long-position' : 'short-position';
        
        html += `
            <tr class="${positionClass}">
                <td>${position.symbol}</td>
                <td>
                    <span class="badge ${position.side === 'LONG' ? 'bg-success' : 'bg-danger'}">${position.side}</span>
                </td>
                <td>${formatNumber(position.entry_price)}</td>
                <td>${formatNumber(position.exit_price)}</td>
                <td>${position.quantity}</td>
                <td>${position.leverage}x</td>
                <td class="${pnlClass}">
                    ${formatNumber(position.pnl)} (${formatNumber(position.pnl_percent)}%)
                </td>
                <td>
                    <span class="badge ${getExitReasonClass(position.exit_reason)}">${position.exit_reason}</span>
                </td>
                <td>${formatDate(position.entry_time)} → ${formatDate(position.exit_time)}</td>
            </tr>
        `;
    });
    
    elements.positionHistory.innerHTML = html;
}

// Close a position
function closePosition(positionId) {
    if (!confirm('Bạn có chắc chắn muốn đóng vị thế này?')) {
        return;
    }
    
    // Mock implementation for now
    // In a real implementation, this would make an API call to close the position
    console.log(`Closing position ${positionId}...`);
    
    // Refresh active positions to show the change
    setTimeout(fetchActivePositions, 1000);
}

// Toggle auto trading feature
function toggleAutoTrading(enabled) {
    console.log(`Auto trading ${enabled ? 'enabled' : 'disabled'}`);
    // In a real implementation, this would make an API call to enable/disable auto trading
}

// Helper function: Format number with comma separator and limited decimal places
function formatNumber(num, decimals = 2) {
    if (num === undefined || num === null) return '-';
    
    // For larger numbers, limit the decimal places more aggressively
    if (Math.abs(num) >= 1000) {
        decimals = 1;
    }
    if (Math.abs(num) >= 10000) {
        decimals = 0;
    }
    
    return new Intl.NumberFormat('vi-VN', { 
        minimumFractionDigits: 0,
        maximumFractionDigits: decimals 
    }).format(num);
}

// Helper function: Format date as a readable string
function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString('vi-VN', { 
            month: 'numeric', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit'
        });
    } catch (e) {
        console.error('Error formatting date', e);
        return dateString;
    }
}

// Helper function: Get the appropriate class for exit reason badge
function getExitReasonClass(reason) {
    switch (reason) {
        case 'TAKE_PROFIT':
            return 'bg-success';
        case 'STOP_LOSS':
            return 'bg-danger';
        case 'TRAILING_STOP':
            return 'bg-warning';
        case 'MANUAL':
            return 'bg-info';
        default:
            return 'bg-secondary';
    }
}