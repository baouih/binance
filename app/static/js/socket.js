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
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
  }

  // Initialize the socket connection
  init() {
    try {
      // Check if Socket.IO is available
      if (typeof io === 'undefined') {
        console.error('Socket.IO not found. Real-time updates will not be available.');
        return false;
      }
      
      // Create socket connection
      this.socket = io();
      
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
      statusElement.textContent = 'Connected';
    } else {
      statusElement.className = 'badge bg-danger';
      statusElement.textContent = 'Disconnected';
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
