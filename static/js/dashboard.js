// Dashboard.js - JavaScript for the Crypto Trading Bot Dashboard

// Global variables
let socket;
let priceChart;
let sentimentGauge;
let priceHistory = [];
let botRunning = true;

// Initialize dashboard when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard components
    initDashboard();
    
    // Setup socket connection
    setupSocketConnection();
    
    // Add event listeners
    addEventListeners();
});

// Initialize dashboard components
function initDashboard() {
    // Update date and time
    updateDateTime();
    setInterval(updateDateTime, 1000);
    
    // Setup charts
    setupCharts();
    
    // Load initial data for tables
    loadPositionsTable();
    loadSignalsTable();
}

// Update date and time display
function updateDateTime() {
    const now = new Date();
    const dateTimeStr = now.toLocaleString();
    // If we add a date/time element to the page, update it here
}

// Setup socket connection
function setupSocketConnection() {
    // Connect to Socket.IO server
    socket = io();
    
    // Handle connection
    socket.on('connect', function() {
        console.log('Connected to server');
    });
    
    // Handle price updates
    socket.on('price_update', function(data) {
        updatePriceDisplay(data);
        console.log('Prices updated successfully');
    });
    
    // Handle sentiment updates
    socket.on('sentiment_update', function(data) {
        updateSentimentDisplay(data);
    });
    
    // Handle account updates
    socket.on('account_update', function(data) {
        updateAccountDisplay(data);
    });
    
    // Handle bot status updates
    socket.on('bot_status', function(data) {
        updateBotStatusDisplay(data);
    });
    
    // Handle disconnection
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
    });
}

// Setup charts
function setupCharts() {
    setupPriceChart();
    setupSentimentGauge();
}

// Setup price chart
function setupPriceChart() {
    const ctx = document.getElementById('price-chart').getContext('2d');
    
    // Initialize with empty data
    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'BTC/USDT',
                data: [],
                borderColor: '#11cdef',
                backgroundColor: 'rgba(17, 205, 239, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            animation: {
                duration: 500
            }
        }
    });
}

// Setup sentiment gauge
function setupSentimentGauge() {
    const ctx = document.getElementById('sentiment-gauge').getContext('2d');
    
    sentimentGauge = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'],
            datasets: [{
                data: [1, 1, 1, 1, 1], // Even distribution initially
                backgroundColor: [
                    '#dc3545', // Extreme Fear - Red
                    '#fd7e14', // Fear - Orange
                    '#6c757d', // Neutral - Gray
                    '#20c997', // Greed - Teal
                    '#198754'  // Extreme Greed - Green
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            circumference: 180,
            rotation: 270,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            },
            cutout: '75%'
        }
    });
    
    // Add needle indicator to sentiment gauge
    updateSentimentNeedle(16); // Initial value
}

// Add event listeners
function addEventListeners() {
    // Toggle bot on/off
    document.getElementById('toggle-bot').addEventListener('click', function() {
        const action = botRunning ? 'stop' : 'start';
        
        // Send API request to control bot
        fetch('/api/bot/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: action })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                botRunning = !botRunning;
                updateBotControlButton();
            }
        })
        .catch(error => console.error('Error:', error));
    });
    
    // Restart bot
    document.getElementById('restart-bot').addEventListener('click', function() {
        // Send API request to restart bot
        fetch('/api/bot/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'restart' })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                botRunning = true;
                updateBotControlButton();
            }
        })
        .catch(error => console.error('Error:', error));
    });
    
    // Close position buttons (will be added dynamically)
    document.getElementById('positions-table').addEventListener('click', function(e) {
        if (e.target.classList.contains('close-position-btn')) {
            const positionId = e.target.getAttribute('data-position-id');
            closePosition(positionId);
        }
    });
}

// Update price display
function updatePriceDisplay(data) {
    // Update price text
    document.getElementById('btc-price').textContent = parseFloat(data.price).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    
    // Add to price history
    const time = new Date(data.time);
    const timeLabel = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    priceHistory.push({
        time: timeLabel,
        price: data.price
    });
    
    // Keep only the last 20 data points
    if (priceHistory.length > 20) {
        priceHistory.shift();
    }
    
    // Update price chart
    updatePriceChart();
}

// Update price chart
function updatePriceChart() {
    // Extract labels and data from price history
    const labels = priceHistory.map(item => item.time);
    const prices = priceHistory.map(item => item.price);
    
    // Update chart data
    priceChart.data.labels = labels;
    priceChart.data.datasets[0].data = prices;
    
    // Update chart
    priceChart.update();
}

// Update sentiment display
function updateSentimentDisplay(data) {
    // Update sentiment label
    const sentimentLabel = document.getElementById('sentiment-label');
    sentimentLabel.textContent = data.description;
    
    // Update sentiment label class
    sentimentLabel.className = 'mt-2'; // Reset classes
    sentimentLabel.classList.add(data.state.replace('_', '-')); // Add state-specific class
    
    // Update sentiment gauge needle
    updateSentimentNeedle(data.value);
}

// Update sentiment gauge needle
function updateSentimentNeedle(value) {
    // Calculate angle based on sentiment value (0-100)
    const angle = value * 1.8 - 90; // Map 0-100 to -90 to 90 degrees
    
    // Remove existing needle
    const container = document.querySelector('.sentiment-gauge-container');
    const oldNeedle = container.querySelector('.gauge-needle');
    if (oldNeedle) {
        oldNeedle.remove();
    }
    
    // Create needle element
    const needle = document.createElement('div');
    needle.className = 'gauge-needle';
    needle.style.position = 'absolute';
    needle.style.width = '2px';
    needle.style.height = '50px';
    needle.style.backgroundColor = '#fff';
    needle.style.top = '50%';
    needle.style.left = '50%';
    needle.style.transformOrigin = 'bottom center';
    needle.style.transform = `translateX(-50%) rotate(${angle}deg)`;
    needle.style.zIndex = '10';
    needle.style.transition = 'transform 0.5s ease';
    
    // Add dot at needle base
    const dot = document.createElement('div');
    dot.style.position = 'absolute';
    dot.style.width = '10px';
    dot.style.height = '10px';
    dot.style.backgroundColor = '#fff';
    dot.style.borderRadius = '50%';
    dot.style.bottom = '0';
    dot.style.left = '50%';
    dot.style.transform = 'translateX(-50%)';
    
    // Append elements
    needle.appendChild(dot);
    container.appendChild(needle);
}

// Update account display
function updateAccountDisplay(data) {
    // Update balance
    document.getElementById('account-balance').textContent = data.balance.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    
    // Update positions table
    updatePositionsTable(data.positions);
}

// Update positions table
function updatePositionsTable(positions) {
    const tableBody = document.getElementById('positions-table');
    
    // Clear table
    tableBody.innerHTML = '';
    
    // Add rows for each position
    positions.forEach(position => {
        const row = document.createElement('tr');
        
        // Add class based on position type
        row.classList.add(position.type.toLowerCase() === 'long' ? 'position-long' : 'position-short');
        
        // Create row content
        row.innerHTML = `
            <td>${position.symbol}</td>
            <td>${position.type}</td>
            <td>$${position.entry_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>$${position.current_price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="${position.pnl >= 0 ? 'text-success' : 'text-danger'}">
                $${Math.abs(position.pnl).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                (${position.pnl_percent.toFixed(2)}%)
            </td>
            <td>
                <button class="btn btn-sm btn-outline-danger close-position-btn" data-position-id="${position.id}">
                    Close
                </button>
            </td>
        `;
        
        // Add to table
        tableBody.appendChild(row);
    });
    
    // If no positions, show message
    if (positions.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="6" class="text-center">No active positions</td>';
        tableBody.appendChild(row);
    }
}

// Load positions table initially
function loadPositionsTable() {
    fetch('/api/account')
        .then(response => response.json())
        .then(data => {
            updatePositionsTable(data.positions);
        })
        .catch(error => console.error('Error:', error));
}

// Load signals table initially
function loadSignalsTable() {
    fetch('/api/signals')
        .then(response => response.json())
        .then(signals => {
            const tableBody = document.getElementById('signals-table');
            
            // Clear table
            tableBody.innerHTML = '';
            
            // Add rows for each signal
            signals.forEach(signal => {
                const row = document.createElement('tr');
                
                // Create row content
                row.innerHTML = `
                    <td>${signal.time}</td>
                    <td>${signal.symbol}</td>
                    <td class="${signal.signal === 'BUY' ? 'signal-buy' : 'signal-sell'}">${signal.signal}</td>
                    <td>$${signal.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td>
                        <div class="progress" style="height: 5px;">
                            <div class="progress-bar bg-info" style="width: ${signal.confidence}%"></div>
                        </div>
                        <small>${signal.confidence}%</small>
                    </td>
                    <td><span class="badge bg-secondary">${signal.market_regime}</span></td>
                `;
                
                // Add to table
                tableBody.appendChild(row);
            });
            
            // If no signals, show message
            if (signals.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="6" class="text-center">No recent signals</td>';
                tableBody.appendChild(row);
            }
        })
        .catch(error => console.error('Error:', error));
}

// Update bot status display
function updateBotStatusDisplay(data) {
    // Update status value
    document.getElementById('status-value').textContent = data.running ? 'Running' : 'Stopped';
    
    // Update uptime
    document.getElementById('uptime-value').textContent = data.uptime;
    
    // Update version
    document.getElementById('version-value').textContent = data.version;
    
    // Update strategies
    document.getElementById('strategies-value').textContent = data.active_strategies.join(', ');
    
    // Update bot running state
    botRunning = data.running;
    
    // Update bot control button
    updateBotControlButton();
    
    // Update status badge
    const statusBadge = document.getElementById('bot-status-badge');
    statusBadge.textContent = data.running ? 'Running' : 'Stopped';
    statusBadge.className = data.running ? 'badge bg-success me-2' : 'badge bg-danger me-2';
}

// Update bot control button
function updateBotControlButton() {
    const button = document.getElementById('toggle-bot');
    
    if (botRunning) {
        button.textContent = 'Stop Bot';
        button.className = 'btn btn-sm btn-outline-danger';
    } else {
        button.textContent = 'Start Bot';
        button.className = 'btn btn-sm btn-outline-success';
    }
}

// Close position
function closePosition(positionId) {
    // Send API request to close position
    fetch('/api/positions/close', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ position_id: positionId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Refresh positions table
            loadPositionsTable();
        }
    })
    .catch(error => console.error('Error:', error));
}