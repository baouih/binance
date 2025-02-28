/**
 * Socket Client
 * Handles WebSocket communication for real-time updates
 */

class SocketClient {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.callbacks = {}; 
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 15; // Tăng số lần thử kết nối lại (15 lần)
    this.reconnectDelay = 5000; // Tăng thời gian chờ giữa các lần thử kết nối (5 giây)
    
    // Dữ liệu giả lập để hiển thị khi mất kết nối
    this.simulationData = {
      prices: {
        'BTCUSDT': 84000 + Math.random() * 2000,
        'ETHUSDT': 3500 + Math.random() * 200,
        'BNBUSDT': 580 + Math.random() * 30,
        'ADAUSDT': 0.50 + Math.random() * 0.05,
        'SOLUSDT': 140 + Math.random() * 15,
      },
      lastUpdate: Date.now(),
      simulationInterval: null
    };
  }

  // Initialize the socket connection
  init() {
    try {
      // Check if Socket.IO is available
      if (typeof io === 'undefined') {
        console.error('Socket.IO not found. Real-time updates will not be available.');
        return false;
      }
      
      // Tạo kết nối socket với các tùy chọn nâng cao
      this.socket = io({
        transports: ['websocket', 'polling'], // Sử dụng cả WebSocket và polling
        reconnectionAttempts: this.maxReconnectAttempts, // Sử dụng giá trị từ constructor
        reconnectionDelay: this.reconnectDelay, // Sử dụng giá trị từ constructor
        timeout: 30000, // Tăng timeout lên 30 giây
        forceNew: true, // Tạo kết nối mới thay vì tái sử dụng
        autoConnect: true // Tự động kết nối khi khởi tạo
      });
      
      // Setup event handlers
      this.socket.on('connect', () => this.onConnect());
      this.socket.on('disconnect', () => this.onDisconnect());
      this.socket.on('connect_error', (error) => this.onConnectError(error));
      
      return true;
    } catch (error) {
      console.error('Error initializing socket:', error);
      return false;
    }
  }
  
  // Subscribe to a specific event
  subscribe(event, callback) {
    if (!this.socket) {
      console.error('Socket not initialized. Cannot subscribe to events.');
      return false;
    }
    
    // Store callback
    if (!this.callbacks[event]) {
      this.callbacks[event] = [];
    }
    
    this.callbacks[event].push(callback);
    
    // Set up listener if not already
    if (this.callbacks[event].length === 1) {
      this.socket.on(event, (data) => {
        this.callbacks[event].forEach(cb => cb(data));
      });
    }
    
    return true;
  }
  
  // Unsubscribe from a specific event
  unsubscribe(event, callback) {
    if (!this.callbacks[event]) return;
    
    // Find and remove the callback
    const index = this.callbacks[event].indexOf(callback);
    if (index !== -1) {
      this.callbacks[event].splice(index, 1);
    }
    
    // If no more callbacks, remove the listener
    if (this.callbacks[event].length === 0) {
      this.socket.off(event);
      delete this.callbacks[event];
    }
  }
  
  // Send data to the server
  emit(event, data) {
    if (!this.socket || !this.connected) {
      console.error('Socket not connected. Cannot emit events.');
      return false;
    }
    
    this.socket.emit(event, data);
    return true;
  }
  
  // Handle connection established
  onConnect() {
    console.log('Socket connected');
    this.connected = true;
    this.reconnectAttempts = 0;
    
    // Add visual indicator to the UI
    this.updateConnectionStatus(true);
    
    // Dừng chế độ mô phỏng khi kết nối lại thành công
    this._stopSimulation();
  }
  
  // Handle disconnection
  onDisconnect() {
    console.log('Socket disconnected');
    this.connected = false;
    
    // Update visual indicator
    this.updateConnectionStatus(false);
    
    // Attempt to reconnect
    this.attemptReconnect();
    
    // Start simulation mode for continuous UI updates
    this._startSimulation();
  }
  
  // Bắt đầu chế độ mô phỏng khi mất kết nối
  _startSimulation() {
    if (this.simulationData.simulationInterval) return;
    
    this.simulationData.simulationInterval = setInterval(() => {
      // Cập nhật giá mô phỏng và tạo biến động giá tự nhiên
      Object.keys(this.simulationData.prices).forEach(symbol => {
        const currentPrice = this.simulationData.prices[symbol];
        // Tạo biến động giá ngẫu nhiên từ -0.5% đến +0.6%
        const changePercent = (Math.random() - 0.45) * 0.01;
        const newPrice = currentPrice * (1 + changePercent);
        this.simulationData.prices[symbol] = newPrice;
        
        // Gửi cập nhật giá mô phỏng tới các callback price_update
        if (this.callbacks['price_update']) {
          const priceData = {
            symbol: symbol,
            price: newPrice.toFixed(2),
            time: Date.now(),
            simulated: true
          };
          
          this.callbacks['price_update'].forEach(cb => cb(priceData));
        }
      });
      
      // Thỉnh thoảng tạo cập nhật tâm lý thị trường mô phỏng
      if (Math.random() > 0.8 && this.callbacks['sentiment_update']) {
        const sentimentData = {
          score: 40 + Math.random() * 30,
          category: 'neutral',
          details: {
            technical: 45 + Math.random() * 15,
            social: 40 + Math.random() * 20,
            fear_greed: 48 + Math.random() * 10
          },
          simulated: true
        };
        
        this.callbacks['sentiment_update'].forEach(cb => cb(sentimentData));
      }
    }, 3000);
  }
  
  // Dừng chế độ mô phỏng khi kết nối lại thành công
  _stopSimulation() {
    if (this.simulationData.simulationInterval) {
      clearInterval(this.simulationData.simulationInterval);
      this.simulationData.simulationInterval = null;
    }
  }
  
  // Handle connection error
  onConnectError(error) {
    console.error('Socket connection error:', error);
    this.connected = false;
    
    // Update visual indicator
    this.updateConnectionStatus(false);
    
    // Attempt to reconnect
    this.attemptReconnect();
    
    // Start simulation mode when connection error occurs
    this._startSimulation();
  }
  
  // Attempt to reconnect after disconnection
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Maximum reconnection attempts reached. Giving up.');
      return;
    }
    
    this.reconnectAttempts++;
    
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    setTimeout(() => {
      if (!this.connected) {
        this.socket.connect();
      }
    }, this.reconnectDelay);
  }
  
  // Update connection status indicator in the UI
  updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connection-status');
    if (!statusElement) return;
    
    if (connected) {
      statusElement.className = 'badge bg-success';
      statusElement.textContent = 'Đã Kết Nối'; // Connected
      statusElement.title = 'Kết nối thành công đến máy chủ dữ liệu thời gian thực';
    } else {
      statusElement.className = 'badge bg-danger';
      statusElement.textContent = 'Mất Kết Nối'; // Disconnected
      statusElement.title = 'Không thể kết nối đến máy chủ dữ liệu thời gian thực';
    }
    
    // Hiển thị thông báo về trạng thái kết nối
    if (!connected && this.reconnectAttempts > 3) {
      const toastContainer = document.getElementById('toast-container');
      if (toastContainer) {
        const toast = document.createElement('div');
        toast.className = 'toast show';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
          <div class="toast-header bg-warning text-dark">
            <strong class="me-auto">Thông Báo Kết Nối</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
          <div class="toast-body">
            Đang thử kết nối lại với máy chủ dữ liệu thời gian thực lần thứ ${this.reconnectAttempts}...
            <small class="text-secondary d-block mt-1">Các cập nhật số dư và tín hiệu giao dịch có thể bị chậm trễ.</small>
          </div>
        `;
        toastContainer.appendChild(toast);
        
        // Tự động ẩn thông báo sau 3 giây
        setTimeout(() => {
          toast.classList.remove('show');
          setTimeout(() => {
            toastContainer.removeChild(toast);
          }, 300);
        }, 3000);
      }
    }
  }
  
  // Manually disconnect
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
  
  // Manually connect
  connect() {
    if (this.socket && !this.connected) {
      this.socket.connect();
    }
  }
  
  // Check if connected
  isConnected() {
    return this.connected;
  }
}
