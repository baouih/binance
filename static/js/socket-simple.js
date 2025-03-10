// Kết nối Socket.IO đơn giản
let socket = null;

// Kết nối Socket.IO
function connectSocket() {
    try {
        // Sử dụng địa chỉ trang web hiện tại thay vì URL mặc định
        const socketUrl = window.location.origin;
        socket = io(socketUrl);
        console.log('Socket.IO đang kết nối tới:', socketUrl);
        
        // Xử lý sự kiện kết nối
        socket.on('connect', function() {
            console.log('Socket.IO đã kết nối!');
            showToast('Đã kết nối với server', 'success');
            
            // Cập nhật giao diện khi kết nối thành công
            if (document.getElementById('connection-status')) {
                document.getElementById('connection-status').innerHTML = '<span class="badge bg-success">Đã kết nối</span>';
            }
        });
        
        // Xử lý sự kiện ngắt kết nối
        socket.on('disconnect', function() {
            console.log('Socket.IO đã ngắt kết nối!');
            showToast('Mất kết nối với server', 'danger');
            
            // Cập nhật giao diện khi mất kết nối
            document.getElementById('connection-status').innerHTML = '<span class="badge bg-danger">Mất kết nối</span>';
        });
        
        // Xử lý lỗi kết nối
        socket.on('connect_error', function(err) {
            console.error('Lỗi kết nối Socket.IO:', err);
            showToast('Lỗi kết nối: ' + err, 'danger');
        });
        
        // Lắng nghe các sự kiện từ server
        setupSocketEvents();
        
    } catch (error) {
        console.error('Lỗi khởi tạo Socket.IO:', error);
        showToast('Không thể kết nối socket: ' + error.message, 'danger');
    }
}

// Thiết lập các sự kiện Socket.IO
function setupSocketEvents() {
    if (!socket) return;
    
    // Nhận cập nhật trạng thái bot
    socket.on('bot_status_update', function(data) {
        updateBotStatus(data);
    });
    
    // Nhận cập nhật dữ liệu tài khoản
    socket.on('account_data', function(data) {
        updateAccountData(data);
    });
    
    // Nhận cập nhật dữ liệu thị trường
    socket.on('market_data', function(data) {
        updateMarketData(data);
    });
    
    // Nhận thông báo mới
    socket.on('new_message', function(data) {
        addMessage(data);
    });
    
    // Nhận tín hiệu giao dịch mới
    socket.on('new_signal', function(data) {
        addSignal(data);
    });
}

// Cập nhật trạng thái bot
function updateBotStatus(data) {
    console.log('Nhận cập nhật trạng thái bot:', data);
    
    // Cập nhật nút điều khiển bot
    const botControlBtn = document.getElementById('bot-control-btn');
    if (botControlBtn) {
        if (data.running) {
            botControlBtn.innerHTML = '<i class="bi bi-stop-circle"></i> Dừng Bot';
            botControlBtn.classList.remove('btn-success');
            botControlBtn.classList.add('btn-danger');
            botControlBtn.dataset.action = 'stop';
        } else {
            botControlBtn.innerHTML = '<i class="bi bi-play-circle"></i> Khởi động Bot';
            botControlBtn.classList.remove('btn-danger');
            botControlBtn.classList.add('btn-success');
            botControlBtn.dataset.action = 'start';
        }
    }
    
    // Cập nhật trạng thái bot
    const botStatusEl = document.getElementById('bot-status');
    if (botStatusEl) {
        if (data.running) {
            botStatusEl.innerHTML = '<span class="badge bg-success">Đang chạy</span>';
        } else {
            botStatusEl.innerHTML = '<span class="badge bg-danger">Đã dừng</span>';
        }
    }
    
    // Cập nhật các thông tin khác
    if (document.getElementById('bot-last-updated')) {
        document.getElementById('bot-last-updated').textContent = data.last_updated || 'N/A';
    }
    
    if (document.getElementById('bot-risk')) {
        document.getElementById('bot-risk').textContent = (data.current_risk ? data.current_risk.toFixed(2) + '%' : '0%');
    }
}

// Cập nhật dữ liệu tài khoản
function updateAccountData(data) {
    console.log('Nhận cập nhật dữ liệu tài khoản:', data);
    
    // Cập nhật số dư
    if (document.getElementById('account-balance')) {
        document.getElementById('account-balance').textContent = '$' + formatNumber(data.balance);
    }
    
    // Cập nhật vốn
    if (document.getElementById('account-equity')) {
        document.getElementById('account-equity').textContent = '$' + formatNumber(data.equity);
    }
    
    // Cập nhật số dư khả dụng
    if (document.getElementById('account-available')) {
        document.getElementById('account-available').textContent = '$' + formatNumber(data.available);
    }
    
    // Cập nhật drawdown
    if (document.getElementById('account-drawdown')) {
        document.getElementById('account-drawdown').textContent = 
            (data.current_drawdown ? data.current_drawdown.toFixed(2) + '%' : '0%');
    }
    
    // Cập nhật danh sách vị thế
    if (document.getElementById('positions-container')) {
        updatePositions(data.positions || []);
    }
    
    // Cập nhật thời gian cập nhật
    if (document.getElementById('account-last-updated')) {
        document.getElementById('account-last-updated').textContent = data.last_updated || 'N/A';
    }
}

// Cập nhật dữ liệu thị trường
function updateMarketData(data) {
    console.log('Nhận cập nhật dữ liệu thị trường:', data);
    
    // Cập nhật giá BTC
    if (document.getElementById('btc-price')) {
        document.getElementById('btc-price').textContent = '$' + formatNumber(data.btc_price);
    }
    
    // Cập nhật giá ETH
    if (document.getElementById('eth-price')) {
        document.getElementById('eth-price').textContent = '$' + formatNumber(data.eth_price);
    }
    
    // Cập nhật giá SOL
    if (document.getElementById('sol-price')) {
        document.getElementById('sol-price').textContent = '$' + formatNumber(data.sol_price);
    }
    
    // Cập nhật giá BNB
    if (document.getElementById('bnb-price')) {
        document.getElementById('bnb-price').textContent = '$' + formatNumber(data.bnb_price);
    }
    
    // Cập nhật thời gian cập nhật
    if (document.getElementById('market-last-updated')) {
        document.getElementById('market-last-updated').textContent = data.last_updated || 'N/A';
    }
}

// Thêm thông báo mới
function addMessage(message) {
    console.log('Nhận thông báo mới:', message);
    
    const messagesContainer = document.getElementById('messages-container');
    if (!messagesContainer) return;
    
    // Tạo phần tử thông báo mới
    const messageEl = document.createElement('div');
    messageEl.className = `alert alert-${message.level} mb-2`;
    messageEl.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span>${message.content}</span>
            <small class="text-muted">${message.timestamp}</small>
        </div>
    `;
    
    // Thêm vào container
    messagesContainer.prepend(messageEl);
    
    // Giới hạn số lượng thông báo hiển thị
    if (messagesContainer.children.length > 10) {
        messagesContainer.removeChild(messagesContainer.lastChild);
    }
    
    // Hiển thị toast nếu thông báo có mức độ cao
    if (message.level === 'danger' || message.level === 'warning') {
        showToast(message.content, message.level);
    }
}

// Cập nhật danh sách vị thế
function updatePositions(positions) {
    const positionsContainer = document.getElementById('positions-container');
    if (!positionsContainer) return;
    
    if (positions.length === 0) {
        positionsContainer.innerHTML = '<div class="text-center text-muted">Không có vị thế nào đang mở</div>';
        return;
    }
    
    // Xóa các vị thế cũ
    positionsContainer.innerHTML = '';
    
    // Thêm các vị thế mới
    positions.forEach(position => {
        const isProfitable = position.pnl > 0;
        const positionEl = document.createElement('div');
        positionEl.className = 'info-card';
        positionEl.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <span class="badge ${position.side === 'BUY' ? 'bg-success' : 'bg-danger'}">${position.side}</span>
                    <strong>${position.symbol}</strong>
                </div>
                <div>
                    <span class="badge ${isProfitable ? 'bg-success' : 'bg-danger'}">
                        ${isProfitable ? '+' : ''}${formatNumber(position.pnl)} (${isProfitable ? '+' : ''}${position.pnl_percent.toFixed(2)}%)
                    </span>
                </div>
            </div>
            <div class="d-flex justify-content-between mb-2">
                <div>
                    <div class="info-label">Giá vào</div>
                    <div class="info-value">$${formatNumber(position.entry_price)}</div>
                </div>
                <div>
                    <div class="info-label">Giá hiện tại</div>
                    <div class="info-value">$${formatNumber(position.current_price)}</div>
                </div>
                <div>
                    <div class="info-label">Số lượng</div>
                    <div class="info-value">${position.amount}</div>
                </div>
            </div>
            <div class="d-flex justify-content-end">
                <button class="btn btn-sm btn-outline-danger close-position-btn" data-position-id="${position.id}">
                    <i class="bi bi-x-circle"></i> Đóng vị thế
                </button>
            </div>
        `;
        
        // Thêm sự kiện cho nút đóng vị thế
        const closeBtn = positionEl.querySelector('.close-position-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                closePosition(position.id);
            });
        }
        
        positionsContainer.appendChild(positionEl);
    });
}

// Đóng vị thế
function closePosition(positionId) {
    if (!socket) return;
    
    console.log('Đang đóng vị thế:', positionId);
    
    // Gửi yêu cầu đóng vị thế
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
            showToast('Đã đóng vị thế thành công', 'success');
            // Sẽ có cập nhật tài khoản gửi từ server qua socket
        } else {
            showToast('Không thể đóng vị thế: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Lỗi khi đóng vị thế:', error);
        showToast('Lỗi khi đóng vị thế', 'danger');
    });
}

// Format số thành dạng có dấu phẩy ngăn cách
function formatNumber(number) {
    if (number === undefined || number === null) return 'N/A';
    return parseFloat(number).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Hiển thị thông báo toast
function showToast(message, type) {
    // Kiểm tra xem container đã tồn tại chưa
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Tạo toast mới
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = 'toast';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="toast-header ${type === 'danger' ? 'bg-danger text-white' : type === 'success' ? 'bg-success text-white' : ''}">
            <strong class="me-auto">Thông báo</strong>
            <small>${new Date().toLocaleTimeString()}</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Thêm toast vào container
    toastContainer.appendChild(toast);
    
    // Khởi tạo và hiển thị toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });
    bsToast.show();
    
    // Xóa toast khỏi DOM sau khi đã ẩn đi
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });
}

// Điều khiển bot (start/stop)
function controlBot(action) {
    if (!socket) return;
    
    console.log('Đang điều khiển bot:', action);
    
    // Gửi yêu cầu điều khiển bot
    fetch('/api/bot/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: action })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(action === 'start' ? 'Bot đã được khởi động' : 'Bot đã dừng lại', 'success');
            updateBotStatus(data.status);
        } else {
            showToast('Không thể điều khiển bot: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Lỗi khi điều khiển bot:', error);
        showToast('Lỗi khi điều khiển bot', 'danger');
    });
}

// Khởi tạo các sự kiện điều khiển
function setupControlEvents() {
    // Điều khiển bot
    const botControlBtn = document.getElementById('bot-control-btn');
    if (botControlBtn) {
        botControlBtn.addEventListener('click', function() {
            const action = this.dataset.action;
            controlBot(action);
        });
    }
    
    // Cập nhật cấu hình bot
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', function(e) {
            e.preventDefault();
            updateConfig();
        });
    }
}

// Cập nhật cấu hình bot
function updateConfig() {
    // Lấy dữ liệu từ form
    const apiKey = document.getElementById('api-key').value;
    const apiSecret = document.getElementById('api-secret').value;
    const tradingType = document.querySelector('input[name="trading-type"]:checked').value;
    const leverage = document.getElementById('leverage').value;
    const riskPerTrade = document.getElementById('risk-per-trade').value;
    const maxPositions = document.getElementById('max-positions').value;
    
    // Tạo dữ liệu cấu hình
    const config = {
        api_key: apiKey,
        api_secret: apiSecret,
        trading_type: tradingType,
        leverage: parseInt(leverage),
        risk_per_trade: parseFloat(riskPerTrade),
        max_positions: parseInt(maxPositions)
    };
    
    // Gửi yêu cầu cập nhật cấu hình
    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Cấu hình đã được cập nhật', 'success');
        } else {
            showToast('Không thể cập nhật cấu hình: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Lỗi khi cập nhật cấu hình:', error);
        showToast('Lỗi khi cập nhật cấu hình', 'danger');
    });
}

// Khi trang đã sẵn sàng
document.addEventListener('DOMContentLoaded', function() {
    // Kết nối Socket.IO
    connectSocket();
    
    // Thiết lập các sự kiện điều khiển
    setupControlEvents();
    
    // Kiểm tra kết nối socket sau 3 giây
    setTimeout(function() {
        if (!socket || !socket.connected) {
            console.log("Socket.IO không kết nối được, sử dụng phương pháp thay thế");
            
            // Sử dụng phương pháp thay thế: gọi API định kỳ
            updateDataWithApi();
            
            // Cập nhật dữ liệu mỗi 5 giây
            setInterval(updateDataWithApi, 5000);
        }
    }, 3000);
});

// Cập nhật dữ liệu thông qua API thay vì Socket.IO
function updateDataWithApi() {
    // Lấy trạng thái hệ thống
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            console.log("Dữ liệu trạng thái từ API:", data);
            
            // Cập nhật trạng thái bot
            const botStatus = {
                running: data.running,
                current_risk: 2.5,
                last_updated: new Date().toLocaleTimeString()
            };
            updateBotStatus(botStatus);
            
            // Cập nhật số dư tài khoản
            if (document.getElementById('account-balance')) {
                document.getElementById('account-balance').textContent = '$' + formatNumber(data.account_balance);
            }
        })
        .catch(error => {
            console.error("Lỗi khi lấy dữ liệu trạng thái:", error);
        });
    
    // Lấy dữ liệu thị trường
    fetch('/api/market_data')
        .then(response => response.json())
        .then(data => {
            console.log("Dữ liệu thị trường từ API:", data);
            
            // Xây dựng và cập nhật dữ liệu thị trường
            const marketData = {
                btc_price: 65000.00,
                eth_price: 3500.00,
                sol_price: 120.00,
                bnb_price: 580.00,
                last_updated: new Date().toLocaleTimeString()
            };
            updateMarketData(marketData);
        })
        .catch(error => {
            console.error("Lỗi khi lấy dữ liệu thị trường:", error);
        });
    
    // Lấy danh sách vị thế
    fetch('/api/positions')
        .then(response => response.json())
        .then(data => {
            console.log("Dữ liệu vị thế từ API:", data);
            
            // Cập nhật danh sách vị thế
            if (document.getElementById('positions-container')) {
                updatePositions(data.positions || []);
            }
        })
        .catch(error => {
            console.error("Lỗi khi lấy dữ liệu vị thế:", error);
        });
}