document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo Socket.IO
    let socket;
    try {
        socket = io();
        console.log('Socket.IO đang kết nối...');
        
        socket.on('connect', function() {
            console.log('Socket.IO đã kết nối!');
            updateConnectionStatus(true);
            
            // Yêu cầu dữ liệu ban đầu
            socket.emit('request_bot_status');
            socket.emit('request_market_data');
            socket.emit('request_bot_logs');
        });
        
        socket.on('disconnect', function() {
            console.log('Socket.IO đã ngắt kết nối!');
            updateConnectionStatus(false);
        });
        
        socket.on('connect_error', function(err) {
            console.error('Lỗi kết nối Socket.IO:', err);
            updateConnectionStatus(false);
        });
        
        // Lắng nghe sự kiện cập nhật trạng thái bot
        socket.on('bot_status_update', function(data) {
            updateBotStatus(data);
        });
        
        // Lắng nghe sự kiện cập nhật dữ liệu thị trường
        socket.on('market_update', function(data) {
            updateMarketData(data);
        });
        
        // Lắng nghe sự kiện log hoạt động mới
        socket.on('bot_log', function(logData) {
            addLogEntry(logData);
        });
        
        // Lắng nghe sự kiện quyết định giao dịch mới
        socket.on('trading_decision', function(decision) {
            addTradingDecision(decision);
        });
        
        // Lắng nghe sự kiện cập nhật vị thế
        socket.on('positions_update', function(positions) {
            updatePositions(positions);
        });
        
    } catch (error) {
        console.error('Lỗi khi khởi tạo Socket.IO:', error);
        updateConnectionStatus(false);
    }
    
    // Xử lý làm mới thủ công
    document.getElementById('refresh-monitor').addEventListener('click', function() {
        // Gửi yêu cầu làm mới dữ liệu
        if (socket && socket.connected) {
            socket.emit('request_bot_status');
            socket.emit('request_market_data');
            socket.emit('request_bot_logs');
            
            showToast('success', 'Đã làm mới dữ liệu.');
        } else {
            showToast('error', 'Không thể làm mới: Socket.IO đang ngắt kết nối.');
            
            // Nếu Socket.IO không kết nối, thì sử dụng API REST để lấy dữ liệu
            fetchBotStatus();
            fetchMarketData();
            fetchBotLogs();
        }
    });
    
    // Xử lý tải xuống logs
    document.getElementById('download-log').addEventListener('click', function() {
        downloadLogs();
    });
    
    // Xử lý lọc logs
    document.querySelectorAll('.log-filter').forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            filterLogs(filter);
            
            // Cập nhật trạng thái active
            document.querySelectorAll('.log-filter').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
    
    // Xử lý lựa chọn bot
    document.getElementById('bot-selector').addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('dropdown-item')) {
            e.preventDefault();
            const botId = e.target.getAttribute('data-bot-id');
            const botName = e.target.textContent;
            
            // Cập nhật trạng thái active
            document.querySelectorAll('#bot-selector .dropdown-item').forEach(item => {
                item.classList.remove('active');
            });
            e.target.classList.add('active');
            
            // Cập nhật bot được chọn
            document.getElementById('selected-bot-name').textContent = botName;
            
            // Gửi yêu cầu dữ liệu cụ thể cho bot
            if (socket && socket.connected) {
                socket.emit('request_bot_status', { botId: botId });
                socket.emit('request_bot_logs', { botId: botId });
            } else {
                fetchBotStatus(botId);
                fetchBotLogs(botId);
            }
        }
    });
    
    // Xử lý các nút điều khiển bot
    document.getElementById('start-bot-btn').addEventListener('click', function() {
        controlBot('start');
    });
    
    document.getElementById('stop-bot-btn').addEventListener('click', function() {
        controlBot('stop');
    });
    
    document.getElementById('restart-bot-btn').addEventListener('click', function() {
        controlBot('restart');
    });
    
    // Làm mới dữ liệu thị trường
    document.getElementById('refresh-market').addEventListener('click', function() {
        if (socket && socket.connected) {
            socket.emit('request_market_data');
            showToast('success', 'Đang làm mới dữ liệu thị trường...');
        } else {
            fetchMarketData();
        }
    });
    
    // Khởi tạo dữ liệu ban đầu (trong trường hợp Socket.IO không hoạt động)
    fetchBotStatus();
    fetchMarketData();
    fetchBotLogs();
    fetchBots();
});

// Cập nhật trạng thái kết nối
function updateConnectionStatus(connected) {
    const statusAlert = document.getElementById('bot-status-alert');
    const statusHeading = document.getElementById('bot-status-heading');
    const statusText = document.getElementById('bot-status-text');
    const statusIcon = document.getElementById('bot-status-icon');
    const connectionDot = document.getElementById('connection-status-dot');

    if (connected) {
        statusAlert.className = 'alert alert-success d-flex align-items-center';
        statusIcon.innerHTML = '<i class="fas fa-circle-notch fa-spin fa-2x me-2"></i>';
        statusHeading.textContent = 'Đã kết nối với bot';
        statusText.textContent = 'Bot đang theo dõi thị trường và cập nhật dữ liệu trong thời gian thực.';
        if (connectionDot) {
            connectionDot.className = 'status-dot status-dot-connected';
            connectionDot.title = 'Đã kết nối';
        }
    } else {
        statusAlert.className = 'alert alert-warning d-flex align-items-center';
        statusIcon.innerHTML = '<i class="fas fa-exclamation-triangle fa-2x me-2"></i>';
        statusHeading.textContent = 'Mất kết nối với bot';
        statusText.textContent = 'Đang cố gắng kết nối lại. Một số dữ liệu có thể không được cập nhật.';
        if (connectionDot) {
            connectionDot.className = 'status-dot status-dot-disconnected';
            connectionDot.title = 'Mất kết nối';
        }
    }
}

// Cập nhật trạng thái bot
function updateBotStatus(data) {
    const statusAlert = document.getElementById('bot-status-alert');
    const statusHeading = document.getElementById('bot-status-heading');
    const statusText = document.getElementById('bot-status-text');
    const statusIcon = document.getElementById('bot-status-icon');
    const riskLevel = document.getElementById('risk-level');
    const riskDescription = document.getElementById('risk-description');

    // Update risk level display if available
    if (data.risk_profile) {
        const riskProfiles = {
            'very_low': { color: 'success', text: 'Rất thấp (5-10%)', description: 'Chiến lược giao dịch cực kỳ thận trọng' },
            'low': { color: 'info', text: 'Thấp (10-15%)', description: 'Chiến lược giao dịch thận trọng' },
            'medium': { color: 'warning', text: 'Vừa phải (20-30%)', description: 'Chiến lược giao dịch cân bằng' },
            'high': { color: 'orange', text: 'Cao (30-50%)', description: 'Chiến lược giao dịch mạo hiểm' },
            'very_high': { color: 'danger', text: 'Rất cao (50-70%)', description: 'Chiến lược giao dịch cực kỳ mạo hiểm' }
        };

        const profile = riskProfiles[data.risk_profile] || riskProfiles.medium;
        if (riskLevel) {
            riskLevel.className = `badge bg-${profile.color}`;
            riskLevel.textContent = profile.text;
        }
        if (riskDescription) {
            riskDescription.textContent = profile.description;
        }
    }

    // Add mini charts if available
    if (data.price_data) {
        updateMiniCharts(data.price_data);
    }

    if (data.status === 'running') {
        statusAlert.className = 'alert alert-success d-flex align-items-center';
        statusIcon.innerHTML = '<i class="fas fa-circle-notch fa-spin fa-2x me-2"></i>';
        statusHeading.textContent = 'Bot đang hoạt động';
        statusText.innerHTML = `
            Bot đang tích cực theo dõi thị trường<br>
            <small class="text-muted">
                Cập nhật lần cuối: ${new Date().toLocaleTimeString()}
            </small>
        `;

        document.getElementById('start-bot-btn').classList.add('d-none');
        document.getElementById('stop-bot-btn').classList.remove('d-none');
    } else if (data.status === 'stopped') {
        statusAlert.className = 'alert alert-secondary d-flex align-items-center';
        statusIcon.innerHTML = '<i class="fas fa-stop-circle fa-2x me-2"></i>';
        statusHeading.textContent = 'Bot đã dừng';
        statusText.innerHTML = `
            Bot hiện đang không hoạt động<br>
            <small class="text-muted">
                Nhấn "Khởi động bot" để bắt đầu giao dịch
            </small>
        `;

        document.getElementById('start-bot-btn').classList.remove('d-none');
        document.getElementById('stop-bot-btn').classList.add('d-none');
    } else if (data.status === 'error') {
        statusAlert.className = 'alert alert-danger d-flex align-items-center';
        statusIcon.innerHTML = '<i class="fas fa-exclamation-circle fa-2x me-2"></i>';
        statusHeading.textContent = 'Bot gặp lỗi';
        statusText.innerHTML = `
            ${data.message || 'Bot gặp lỗi khi hoạt động'}<br>
            <small class="text-muted">
                Vui lòng kiểm tra nhật ký để biết thêm chi tiết
            </small>
        `;

        document.getElementById('start-bot-btn').classList.add('d-none');
        document.getElementById('stop-bot-btn').classList.add('d-none');
        document.getElementById('restart-bot-btn').classList.remove('d-none');
    }

    // Update statistics with animations
    if (data.stats) {
        animateValue('bot-uptime', data.stats.uptime || '--');
        animateValue('analysis-count', data.stats.analyses || '--');
        animateValue('decision-count', data.stats.decisions || '--');
        animateValue('order-count', data.stats.orders || '--');

        // Update performance metrics if available
        if (data.stats.performance) {
            updatePerformanceMetrics(data.stats.performance);
        }
    }
}

// Add new function for performance metrics
function updatePerformanceMetrics(performance) {
    const metrics = {
        'total-pnl': performance.total_pnl || 0,
        'win-rate': performance.win_rate || 0,
        'avg-profit': performance.avg_profit || 0,
        'max-drawdown': performance.max_drawdown || 0
    };

    Object.entries(metrics).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            const isPositive = value > 0;
            const formattedValue = typeof value === 'number' ? 
                (id === 'win-rate' ? `${value.toFixed(1)}%` : `$${Math.abs(value).toFixed(2)}`) :
                value.toString();

            element.innerHTML = `
                <span class="text-${isPositive ? 'success' : 'danger'}">
                    ${isPositive ? '+' : '-'}${formattedValue}
                </span>
            `;
        }
    });
}

// Add new function for mini charts
function updateMiniCharts(priceData) {
    Object.entries(priceData).forEach(([symbol, data]) => {
        const chartId = `${symbol.toLowerCase()}-mini-chart`;
        const canvas = document.getElementById(chartId);

        if (canvas) {
            const ctx = canvas.getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.timestamps,
                    datasets: [{
                        data: data.prices,
                        borderColor: data.trend === 'up' ? '#28a745' : '#dc3545',
                        borderWidth: 1,
                        fill: false,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { display: false }
                    }
                }
            });
        }
    });
}

// Add new function for value animation
function animateValue(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) return;

    if (typeof value === 'number') {
        const start = parseInt(element.textContent) || 0;
        const duration = 1000;
        const step = (timestamp) => {
            if (!start) start = timestamp;
            const progress = Math.min((timestamp - start) / duration, 1);
            element.textContent = Math.floor(progress * (value - start) + start);
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    } else {
        element.textContent = value;
    }
}

// Cập nhật dữ liệu thị trường
function updateMarketData(data) {
    // Cập nhật chỉ số thị trường
    updateCoinTrend('btc', data.market_regime?.BTC, data.btc_price, data.btc_change_24h);
    updateCoinTrend('eth', data.market_regime?.ETH, data.eth_price, data.eth_change_24h);
    updateCoinTrend('sol', data.market_regime?.SOL, data.sol_price, data.sol_change_24h);
    updateCoinTrend('bnb', data.market_regime?.BNB, null, null);
    
    // Cập nhật giá coin và các chỉ báo kỹ thuật
    if (data.indicators) {
        updateCoinIndicators('btc', data.indicators.BTC);
        updateCoinIndicators('eth', data.indicators.ETH);
        updateCoinIndicators('sol', data.indicators.SOL);
        updateCoinIndicators('bnb', data.indicators.BNB);
    }
    
    // Cập nhật tâm lý thị trường
    if (data.sentiment) {
        const sentimentValue = document.getElementById('sentiment-value');
        const sentimentBar = document.getElementById('sentiment-bar');
        const sentimentDesc = document.getElementById('sentiment-description');
        
        sentimentValue.textContent = data.sentiment.value;
        sentimentBar.style.width = `${data.sentiment.value}%`;
        sentimentDesc.textContent = data.sentiment.text;
        
        // Cập nhật màu sắc dựa trên trạng thái
        if (data.sentiment.state === 'danger') {
            sentimentBar.className = 'progress-bar bg-danger';
        } else if (data.sentiment.state === 'warning') {
            sentimentBar.className = 'progress-bar bg-warning';
        } else if (data.sentiment.state === 'success') {
            sentimentBar.className = 'progress-bar bg-success';
        }
    }
    
    // Cập nhật tín hiệu giao dịch
    if (data.signals) {
        updateSignal('btc', data.signals.BTC);
        updateSignal('eth', data.signals.ETH);
        updateSignal('sol', data.signals.SOL);
        updateSignal('bnb', data.signals.BNB);
    }
}

// Cập nhật xu hướng coin
function updateCoinTrend(coin, trend, price, change) {
    const trendIndicator = document.getElementById(`${coin}-trend-indicator`);
    const trendText = document.getElementById(`${coin}-trend-text`);
    
    if (trend) {
        trendText.textContent = getTrendText(trend);
        
        if (trend === 'trending' || trend === 'bullish') {
            trendIndicator.className = 'market-indicator trend-up';
        } else if (trend === 'bearish' || trend === 'downtrend') {
            trendIndicator.className = 'market-indicator trend-down';
        } else if (trend === 'ranging' || trend === 'sideways') {
            trendIndicator.className = 'market-indicator trend-sideways';
        } else if (trend === 'volatile') {
            trendIndicator.className = 'market-indicator trend-sideways';
        }
    }
    
    // Cập nhật giá nếu có
    if (price) {
        const priceElement = document.getElementById(`${coin}-price`);
        if (priceElement) {
            priceElement.textContent = formatPrice(price);
            
            // Thêm chỉ báo thay đổi nếu có
            if (change) {
                const changeClass = change >= 0 ? 'text-success' : 'text-danger';
                const changePrefix = change >= 0 ? '+' : '';
                priceElement.innerHTML = `${formatPrice(price)} <small class="${changeClass}">${changePrefix}${change.toFixed(2)}%</small>`;
            }
        }
    }
}

// Cập nhật các chỉ báo kỹ thuật cho coin
function updateCoinIndicators(coin, indicators) {
    if (!indicators) return;
    
    const rsiElement = document.getElementById(`${coin}-rsi`);
    const macdElement = document.getElementById(`${coin}-macd`);
    const trendElement = document.getElementById(`${coin}-trend`);
    
    if (rsiElement && indicators.rsi) {
        const rsiValue = indicators.rsi.toFixed(2);
        let rsiClass = 'text-muted';
        
        if (rsiValue < 30) rsiClass = 'text-success';
        else if (rsiValue > 70) rsiClass = 'text-danger';
        
        rsiElement.textContent = rsiValue;
        rsiElement.className = rsiClass;
    }
    
    if (macdElement && indicators.macd) {
        const macdValue = indicators.macd.toFixed(4);
        const macdClass = macdValue > 0 ? 'text-success' : 'text-danger';
        
        macdElement.textContent = macdValue;
        macdElement.className = macdClass;
    }
    
    if (trendElement && indicators.trend) {
        trendElement.textContent = getTrendText(indicators.trend);
    }
}

// Cập nhật tín hiệu giao dịch
function updateSignal(coin, signal) {
    if (!signal) return;
    
    const signalElement = document.getElementById(`${coin}-signal`);
    if (!signalElement) return;
    
    if (signal.type === 'BUY' || signal.type === 'buy') {
        signalElement.className = 'badge rounded-pill bg-success';
        signalElement.textContent = `MUA ${signal.strength || ''}`.trim();
    } else if (signal.type === 'SELL' || signal.type === 'sell') {
        signalElement.className = 'badge rounded-pill bg-danger';
        signalElement.textContent = `BÁN ${signal.strength || ''}`.trim();
    } else if (signal.type === 'HOLD' || signal.type === 'hold' || signal.type === 'neutral') {
        signalElement.className = 'badge rounded-pill bg-warning';
        signalElement.textContent = 'GIỮ';
    } else {
        signalElement.className = 'badge rounded-pill bg-secondary';
        signalElement.textContent = signal.type || 'N/A';
    }
}

// Thêm mục nhật ký mới
function addLogEntry(logData) {
    const logContainer = document.getElementById('activity-log');
    
    // Tạo phần tử cho mục log mới
    const logItem = document.createElement('div');
    logItem.className = `log-item ${getLogClass(logData.category)}`;
    logItem.setAttribute('data-category', logData.category);
    
    // Format thời gian
    const timestamp = new Date(logData.timestamp);
    const timeStr = timestamp.toLocaleTimeString();
    
    // Tạo nội dung cho mục log
    logItem.innerHTML = `
        <span class="log-timestamp">${timeStr}</span>
        <span class="log-category log-${logData.category}">${getCategoryName(logData.category)}</span>
        <span class="log-message">${logData.message}</span>
    `;
    
    // Thêm mục log vào đầu danh sách
    logContainer.insertBefore(logItem, logContainer.firstChild);
    
    // Giới hạn số lượng mục log (giữ 100 mục gần nhất)
    const maxLogs = 100;
    const logs = logContainer.querySelectorAll('.log-item');
    if (logs.length > maxLogs) {
        for (let i = maxLogs; i < logs.length; i++) {
            logs[i].remove();
        }
    }
}

// Thêm quyết định giao dịch mới
function addTradingDecision(decision) {
    const decisionsContainer = document.getElementById('recent-decisions');
    
    // Xác định class dựa trên loại quyết định
    let decisionClass = 'trade-decision-hold';
    let badgeClass = 'bg-warning';
    let badgeText = 'GIỮ';
    
    if (decision.action === 'BUY' || decision.action === 'buy') {
        decisionClass = 'trade-decision-buy';
        badgeClass = 'bg-success';
        badgeText = 'MUA';
    } else if (decision.action === 'SELL' || decision.action === 'sell') {
        decisionClass = 'trade-decision-sell';
        badgeClass = 'bg-danger';
        badgeText = 'BÁN';
    }
    
    // Tạo phần tử cho quyết định mới
    const decisionItem = document.createElement('div');
    decisionItem.className = `trade-decision-card ${decisionClass} p-3 border-bottom`;
    
    // Tạo HTML cho phần đầu quyết định
    let decisionHtml = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="mb-0">${decision.symbol}</h6>
            <div>
                <span class="badge ${badgeClass} me-1">${badgeText}</span>
                <small class="text-muted">${formatTime(decision.timestamp)}</small>
            </div>
        </div>
    `;
    
    // Thêm thông tin về giá nếu có
    if (decision.entry_price) {
        decisionHtml += `<p class="mb-2">Điểm vào lệnh: ${formatPrice(decision.entry_price)}</p>`;
    }
    
    if (decision.take_profit) {
        const tpPercent = ((decision.take_profit / decision.entry_price - 1) * 100).toFixed(2);
        const plusSign = decision.action === 'BUY' ? '+' : '-';
        decisionHtml += `<p class="mb-2">Take profit: ${formatPrice(decision.take_profit)} (${plusSign}${tpPercent}%)</p>`;
    }
    
    if (decision.stop_loss) {
        const slPercent = Math.abs((decision.stop_loss / decision.entry_price - 1) * 100).toFixed(2);
        const minusSign = decision.action === 'BUY' ? '-' : '+';
        decisionHtml += `<p class="mb-2">Stop loss: ${formatPrice(decision.stop_loss)} (${minusSign}${slPercent}%)</p>`;
    }
    
    // Thêm lý do
    if (decision.reasons && decision.reasons.length > 0) {
        decisionHtml += `<p class="mb-0"><strong>Lý do:</strong></p>`;
        decision.reasons.forEach(reason => {
            decisionHtml += `<div class="reason-item">${reason}</div>`;
        });
    }
    
    decisionItem.innerHTML = decisionHtml;
    
    // Thêm quyết định vào đầu danh sách
    decisionsContainer.insertBefore(decisionItem, decisionsContainer.firstChild);
    
    // Giới hạn số lượng quyết định hiển thị (giữ 5 quyết định gần nhất)
    const decisions = decisionsContainer.querySelectorAll('.trade-decision-card');
    if (decisions.length > 5) {
        for (let i = 5; i < decisions.length; i++) {
            decisions[i].remove();
        }
    }
}

// Cập nhật danh sách vị thế
function updatePositions(positions) {
    const positionsTable = document.getElementById('monitor-positions-table');
    const noPositionsRow = document.getElementById('no-monitor-positions-row');
    
    // Xóa các hàng cũ (trừ hàng thông báo không có vị thế)
    const oldRows = positionsTable.querySelectorAll('tr:not(#no-monitor-positions-row)');
    oldRows.forEach(row => row.remove());
    
    // Hiển thị hoặc ẩn thông báo không có vị thế
    if (!positions || positions.length === 0) {
        noPositionsRow.classList.remove('d-none');
        return;
    } else {
        noPositionsRow.classList.add('d-none');
    }
    
    // Thêm các vị thế mới
    positions.forEach(position => {
        const row = document.createElement('tr');
        
        // Xác định class cho hàng dựa trên P&L
        if (position.pnl > 0) {
            row.className = 'table-success';
        } else if (position.pnl < 0) {
            row.className = 'table-danger';
        }
        
        // Xác định loại vị thế (LONG/SHORT)
        const posType = position.type || (position.side === 'BUY' ? 'LONG' : 'SHORT');
        const typeClass = posType === 'LONG' || posType === 'BUY' ? 'bg-success' : 'bg-danger';
        
        // Tính P&L phần trăm
        const pnlPercent = position.pnl_percent || 
            (position.pnl && position.entry_price ? 
             (position.pnl / (position.entry_price * position.size) * 100).toFixed(2) : 
             '--');
        
        // Format P&L
        const pnlStr = position.pnl > 0 ? 
            `<span class="text-success">+${position.pnl.toFixed(2)} (${pnlPercent}%)</span>` : 
            `<span class="text-danger">${position.pnl.toFixed(2)} (${pnlPercent}%)</span>`;
        
        row.innerHTML = `
            <td>${position.symbol}</td>
            <td><span class="badge ${typeClass}">${posType}</span></td>
            <td>${formatPrice(position.entry_price)}</td>
            <td>${formatPrice(position.current_price || position.mark_price)}</td>
            <td>${pnlStr}</td>
            <td>${formatPrice(position.take_profit || '--')}</td>
            <td>${formatPrice(position.stop_loss || '--')}</td>
        `;
        
        positionsTable.appendChild(row);
    });
}

// Điều khiển bot (start/stop/restart)
function controlBot(action) {
    // Lấy bot ID được chọn
    const activeBotItem = document.querySelector('#bot-selector .dropdown-item.active');
    const botId = activeBotItem ? activeBotItem.getAttribute('data-bot-id') : 'all';
    
    // Hiển thị loading
    document.getElementById('loading-overlay').classList.remove('d-none');
    
    // Gửi yêu cầu điều khiển bot
    fetch('/api/bot/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: action,
            bot_id: botId === 'all' ? null : botId,
            strategy_mode: 'auto' // Mặc định sử dụng chế độ tự động
        })
    })
    .then(response => response.json())
    .then(data => {
        // Ẩn loading
        document.getElementById('loading-overlay').classList.add('d-none');
        
        if (data.success) {
            showToast('success', data.message || `Bot đã được ${getActionText(action)} thành công.`);
            
            // Cập nhật giao diện
            fetchBotStatus();
        } else {
            showToast('error', data.message || `Không thể ${getActionText(action)} bot.`);
        }
    })
    .catch(error => {
        // Ẩn loading
        document.getElementById('loading-overlay').classList.add('d-none');
        
        console.error('Lỗi khi điều khiển bot:', error);
        showToast('error', `Lỗi khi ${getActionText(action)} bot: ${error.message}`);
    });
}

// Lấy danh sách bot
function fetchBots() {
    fetch('/api/bots')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.bots) {
                updateBotsList(data.bots);
            }
        })
        .catch(error => {
            console.error('Lỗi khi lấy danh sách bot:', error);
        });
}

// Cập nhật danh sách bot trên giao diện
function updateBotsList(bots) {
    const botSelector = document.getElementById('bot-selector');
    
    // Lưu lại các mục cố định
    const staticItems = botSelector.innerHTML;
    
    // Xóa các mục cũ (trừ các mục cố định)
    botSelector.innerHTML = staticItems;
    
    // Thêm các bot mới
    bots.forEach(bot => {
        const item = document.createElement('li');
        item.innerHTML = `<a class="dropdown-item" href="#" data-bot-id="${bot.id}">${bot.name}</a>`;
        botSelector.appendChild(item);
    });
}

// Lấy trạng thái bot thông qua API REST
function fetchBotStatus(botId = null) {
    const url = botId ? `/api/bots/${botId}` : '/api/bot/status';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (botId) {
                // Trường hợp lấy thông tin chi tiết bot
                if (data.success && data.bot) {
                    updateBotStatus({
                        status: data.bot.status,
                        stats: {
                            uptime: formatDuration(data.bot.uptime_seconds || 0),
                            analyses: data.bot.stats?.analyses || 0,
                            decisions: data.bot.stats?.decisions || 0,
                            orders: data.bot.stats?.orders || 0
                        }
                    });
                }
            } else {
                // Trường hợp lấy trạng thái tổng hợp
                updateBotStatus(data);
            }
        })
        .catch(error => {
            console.error('Lỗi khi lấy trạng thái bot:', error);
        });
}

// Lấy dữ liệu thị trường thông qua API REST
function fetchMarketData() {
    fetch('/api/market')
        .then(response => response.json())
        .then(data => {
            updateMarketData(data);
        })
        .catch(error => {
            console.error('Lỗi khi lấy dữ liệu thị trường:', error);
        });
}

// Lấy logs của bot thông qua API REST
function fetchBotLogs(botId = null) {
    const url = botId ? `/api/bot/logs/${botId}` : '/api/bot/logs';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.logs) {
                // Xóa logs cũ
                document.getElementById('activity-log').innerHTML = '';
                
                // Thêm logs mới (theo thứ tự thời gian mới nhất đến cũ nhất)
                data.logs.reverse().forEach(log => {
                    addLogEntry(log);
                });
            }
        })
        .catch(error => {
            console.error('Lỗi khi lấy logs của bot:', error);
        });
}

// Tải xuống logs
function downloadLogs() {
    // Lấy toàn bộ nội dung logs
    const logs = Array.from(document.querySelectorAll('.log-item')).map(item => {
        const timestamp = item.querySelector('.log-timestamp').textContent;
        const category = item.querySelector('.log-category').textContent;
        const message = item.querySelector('.log-message').textContent;
        
        return `[${timestamp}] [${category}] ${message}`;
    }).join('\n');
    
    // Tạo file download
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    // Tạo link download và kích hoạt
    const a = document.createElement('a');
    a.href = url;
    a.download = `bot_logs_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    
    // Dọn dẹp
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 0);
    
    showToast('success', 'Logs đã được tải xuống.');
}

// Lọc logs theo loại
function filterLogs(filter) {
    const logs = document.querySelectorAll('.log-item');
    
    logs.forEach(log => {
        if (filter === 'all' || log.getAttribute('data-category') === filter) {
            log.classList.remove('d-none');
        } else {
            log.classList.add('d-none');
        }
    });
}

// Hiển thị thông báo toast
function showToast(type, message) {
    const toastId = type === 'success' ? 'success-toast' : 'error-toast';
    const messageId = type === 'success' ? 'toast-message' : 'toast-error-message';
    
    const toast = document.getElementById(toastId);
    const messageElement = document.getElementById(messageId);
    
    messageElement.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

// Các hàm trợ giúp

// Lấy class cho log
function getLogClass(category) {
    return `log-${category}`;
}

// Lấy tên hiển thị cho các loại log
function getCategoryName(category) {
    const categories = {
        'analysis': 'PHÂN TÍCH',
        'decision': 'QUYẾT ĐỊNH',
        'action': 'HÀNH ĐỘNG',
        'error': 'LỖI',
        'market': 'THỊ TRƯỜNG',
        'system': 'HỆ THỐNG'
    };
    
    return categories[category] || category.toUpperCase();
}

// Lấy tên cho trend
function getTrendText(trend) {
    const trends = {
        'trending': 'Xu hướng tăng',
        'bullish': 'Xu hướng tăng mạnh',
        'bearish': 'Xu hướng giảm mạnh',
        'downtrend': 'Xu hướng giảm',
        'ranging': 'Đi ngang',
        'sideways': 'Đi ngang',
        'volatile': 'Biến động mạnh'
    };
    
    return trends[trend] || trend;
}

// Format thời gian từ timestamp
function formatTime(timestamp) {
    if (!timestamp) return '--';
    
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// Format giá
function formatPrice(price) {
    if (!price || price === '--') return '--';
    
    // Định dạng số với phân cách hàng nghìn và tối đa 2 số thập phân
    return parseFloat(price).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Format khoảng thời gian
function formatDuration(seconds) {
    if (!seconds) return '--';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

// Lấy tên hành động
function getActionText(action) {
    const actions = {
        'start': 'khởi động',
        'stop': 'dừng',
        'restart': 'khởi động lại'
    };
    
    return actions[action] || action;
}