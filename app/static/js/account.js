/**
 * Account Controller
 * Handles account data and balance display
 */

class AccountController {
  constructor() {
    this.balance = 0;
    this.availableBalance = 0;
    this.marginBalance = 0;
    this.unrealizedPnl = 0;
    this.equity = 0;
    this.positions = [];
    this.trades = [];
  }

  init() {
    this.loadAccountInfo();
    this.initRealtimeUpdates();
  }

  async loadAccountInfo() {
    try {
      // Get account info from market data endpoint
      const response = await fetch('/api/market_data');
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.account) {
        this.updateAccountInfo(data.account);
      }
    } catch (error) {
      console.error('Error loading account info:', error);
    }
  }

  updateAccountInfo(accountData) {
    this.balance = accountData.total_balance || 0;
    this.availableBalance = accountData.available_balance || 0;
    this.marginBalance = accountData.margin_balance || 0;
    this.unrealizedPnl = accountData.unrealized_pnl || 0;
    this.equity = accountData.equity || 0;
    
    // Update UI
    this.updateAccountDisplay();
  }

  updateAccountDisplay() {
    // Update balance displays
    const totalBalanceElement = document.getElementById('total-balance');
    if (totalBalanceElement) {
      totalBalanceElement.textContent = this.formatCurrency(this.balance);
    }
    
    const availableBalanceElement = document.getElementById('available-balance');
    if (availableBalanceElement) {
      availableBalanceElement.textContent = this.formatCurrency(this.availableBalance);
    }
    
    const unrealizedPnlElement = document.getElementById('unrealized-pnl');
    if (unrealizedPnlElement) {
      unrealizedPnlElement.textContent = this.formatCurrency(this.unrealizedPnl);
      unrealizedPnlElement.classList.remove('text-success', 'text-danger');
      unrealizedPnlElement.classList.add(this.unrealizedPnl >= 0 ? 'text-success' : 'text-danger');
    }
    
    const equityElement = document.getElementById('equity');
    if (equityElement) {
      equityElement.textContent = this.formatCurrency(this.equity);
    }
  }

  initRealtimeUpdates() {
    // Listen for account updates if using socket
    if (window.socketClient) {
      window.socketClient.subscribe('account_update', (data) => {
        this.updateAccountInfo(data);
      });
    }
  }
  
  async loadPositions() {
    try {
      // Simulate some positions in development mode
      this.positions = [
        {
          id: 1,
          symbol: 'BTCUSDT',
          side: 'LONG',
          entry_price: 81500.0,
          quantity: 0.05,
          liquidation_price: 75000.0,
          margin: 2000,
          pnl: 130.5,
          pnl_percent: 6.5,
          status: 'OPEN'
        },
        {
          id: 2,
          symbol: 'ETHUSDT',
          side: 'SHORT',
          entry_price: 3500.0,
          quantity: 0.8,
          liquidation_price: 4200.0,
          margin: 1500,
          pnl: -80.0,
          pnl_percent: -5.3,
          status: 'OPEN'
        }
      ];
      
      this.updatePositionsDisplay();
    } catch (error) {
      console.error('Error loading positions:', error);
    }
  }
  
  updatePositionsDisplay() {
    const positionsContainer = document.getElementById('positions-container');
    if (!positionsContainer) return;
    
    if (this.positions.length === 0) {
      positionsContainer.innerHTML = `
        <div class="alert alert-info">
          <p class="mb-0">No open positions</p>
        </div>
      `;
      return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-dark table-sm">';
    html += '<thead><tr><th>Symbol</th><th>Side</th><th>Size</th><th>Entry</th><th>PnL</th><th></th></tr></thead><tbody>';
    
    this.positions.forEach(position => {
      const pnlClass = position.pnl >= 0 ? 'text-success' : 'text-danger';
      html += `
        <tr>
          <td>${position.symbol}</td>
          <td class="${position.side === 'LONG' ? 'text-success' : 'text-danger'}">${position.side}</td>
          <td>${position.quantity}</td>
          <td>${position.entry_price.toFixed(2)}</td>
          <td class="${pnlClass}">${position.pnl.toFixed(2)} (${position.pnl_percent.toFixed(2)}%)</td>
          <td><button class="btn btn-sm btn-danger close-position-btn" data-position-id="${position.id}">Close</button></td>
        </tr>
      `;
    });
    
    html += '</tbody></table></div>';
    positionsContainer.innerHTML = html;
    
    // Add event listeners for close buttons
    const closeButtons = positionsContainer.querySelectorAll('.close-position-btn');
    closeButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        const positionId = e.target.getAttribute('data-position-id');
        this.closePosition(positionId);
      });
    });
  }
  
  async closePosition(positionId) {
    try {
      // In simulation mode, just remove the position
      this.positions = this.positions.filter(p => p.id.toString() !== positionId.toString());
      this.updatePositionsDisplay();
      
      // Show success message
      this.showSuccess('Position closed successfully');
    } catch (error) {
      console.error('Error closing position:', error);
      this.showError('Failed to close position');
    }
  }
  
  async loadTradeHistory() {
    try {
      // Simulate some trade history in development mode
      const currentTime = new Date();
      
      this.trades = [
        {
          id: 101,
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
          quantity: 0.05,
          price: 81500.0,
          time: new Date(currentTime.getTime() - 3600000).toISOString(), // 1 hour ago
          value: 4075.0,
          fee: 4.075,
          status: 'FILLED'
        },
        {
          id: 100,
          symbol: 'ETHUSDT',
          side: 'SELL',
          type: 'LIMIT',
          quantity: 0.8,
          price: 3500.0,
          time: new Date(currentTime.getTime() - 7200000).toISOString(), // 2 hours ago
          value: 2800.0,
          fee: 2.8,
          status: 'FILLED'
        },
        {
          id: 99,
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
          quantity: 0.03,
          price: 82000.0,
          time: new Date(currentTime.getTime() - 86400000).toISOString(), // 1 day ago
          value: 2460.0,
          fee: 2.46,
          status: 'FILLED'
        }
      ];
      
      this.updateTradeHistoryDisplay();
    } catch (error) {
      console.error('Error loading trade history:', error);
    }
  }
  
  updateTradeHistoryDisplay() {
    const tradeHistoryContainer = document.getElementById('trade-history-container');
    if (!tradeHistoryContainer) return;
    
    if (this.trades.length === 0) {
      tradeHistoryContainer.innerHTML = `
        <div class="alert alert-info">
          <p class="mb-0">No trading history available.</p>
        </div>
      `;
      return;
    }
    
    let html = '<div class="table-responsive" style="max-height: 200px; overflow-y: auto;"><table class="table table-dark table-sm">';
    html += '<thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Price</th><th>Quantity</th><th>Value</th></tr></thead><tbody>';
    
    this.trades.forEach(trade => {
      const tradeTime = new Date(trade.time);
      html += `
        <tr>
          <td>${tradeTime.toLocaleTimeString()}</td>
          <td>${trade.symbol}</td>
          <td class="${trade.side === 'BUY' ? 'text-success' : 'text-danger'}">${trade.side}</td>
          <td>${trade.price.toFixed(2)}</td>
          <td>${trade.quantity}</td>
          <td>${trade.value.toFixed(2)}</td>
        </tr>
      `;
    });
    
    html += '</tbody></table></div>';
    tradeHistoryContainer.innerHTML = html;
  }

  showSuccess(message) {
    // Show toast notification
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer) {
      const toast = document.createElement('div');
      toast.className = 'toast show';
      toast.setAttribute('role', 'alert');
      toast.setAttribute('aria-live', 'assertive');
      toast.setAttribute('aria-atomic', 'true');
      toast.innerHTML = `
        <div class="toast-header bg-success text-white">
          <strong class="me-auto">Success</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          ${message}
        </div>
      `;
      toastContainer.appendChild(toast);
      
      // Auto-dismiss after 3 seconds
      setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
          toastContainer.removeChild(toast);
        }, 500);
      }, 3000);
    }
  }

  showError(message) {
    // Show toast notification
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer) {
      const toast = document.createElement('div');
      toast.className = 'toast show';
      toast.setAttribute('role', 'alert');
      toast.setAttribute('aria-live', 'assertive');
      toast.setAttribute('aria-atomic', 'true');
      toast.innerHTML = `
        <div class="toast-header bg-danger text-white">
          <strong class="me-auto">Error</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          ${message}
        </div>
      `;
      toastContainer.appendChild(toast);
      
      // Auto-dismiss after 3 seconds
      setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
          toastContainer.removeChild(toast);
        }, 500);
      }, 3000);
    }
  }

  formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
  window.accountController = new AccountController();
});