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
  }
  
  // Handle disconnection
  onDisconnect() {
    console.log('Socket disconnected');
    this.connected = false;
    
    // Update visual indicator
    this.updateConnectionStatus(false);
    
    // Attempt to reconnect
    this.attemptReconnect();
  }
  
  // Handle connection error
  onConnectError(error) {
    console.error('Socket connection error:', error);
    this.connected = false;
    
    // Update visual indicator
    this.updateConnectionStatus(false);
    
    // Attempt to reconnect
    this.attemptReconnect();
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
