/**
 * Trading Controller
 * Handles trading operations and strategy management
 */

class TradingController {
  constructor() {
    this.symbol = 'BTCUSDT';
    this.strategy = 'rsi';
    this.strategyParams = {
      rsi: {
        overbought: 70,
        oversold: 30
      },
      macd: {},
      ema_cross: {
        short_period: 9,
        long_period: 21
      },
      bbands: {
        deviation_multiplier: 2.0
      },
      ml: {
        probability_threshold: 0.65
      }
    };
    this.account = {
      balance: 0,
      positions: [],
      history: []
    };
    this.lastSignal = 0; // -1: sell, 0: neutral, 1: buy
  }

  // Initialize trading controller
  init(symbol) {
    this.symbol = symbol;
    this.loadAccountInfo();
    console.log(`Trading controller initialized for ${this.symbol}`);
  }
  
  // Set trading symbol
  setSymbol(symbol) {
    this.symbol = symbol;
    console.log(`Trading symbol set to ${this.symbol}`);
  }
  
  // Set trading strategy
  setStrategy(strategy) {
    this.strategy = strategy;
    console.log(`Trading strategy set to ${this.strategy}`);
  }
  
  // Update strategy parameters
  updateStrategyParams(params) {
    if (!params) return;
    
    if (this.strategy === 'rsi') {
      this.strategyParams.rsi = {
        ...this.strategyParams.rsi,
        ...params
      };
    } else if (this.strategy === 'macd') {
      this.strategyParams.macd = {
        ...this.strategyParams.macd,
        ...params
      };
    } else if (this.strategy === 'ema_cross') {
      this.strategyParams.ema_cross = {
        ...this.strategyParams.ema_cross,
        ...params
      };
    } else if (this.strategy === 'bbands') {
      this.strategyParams.bbands = {
        ...this.strategyParams.bbands,
        ...params
      };
    } else if (this.strategy === 'ml') {
      this.strategyParams.ml = {
        ...this.strategyParams.ml,
        ...params
      };
    }
    
    console.log(`Strategy parameters updated for ${this.strategy}:`, this.strategyParams[this.strategy]);
  }
  
  // Load account information
  async loadAccountInfo() {
    try {
      const response = await fetch('/api/account');
      const accountData = await response.json();
      
      this.account = accountData;
      this.updateAccountDisplay();
      
      return accountData;
    } catch (error) {
      console.error('Error loading account info:', error);
      return null;
    }
  }
  
  // Update account information display
  updateAccountDisplay() {
    // Update balance
    const balanceElement = document.getElementById('account-balance');
    if (balanceElement) {
      balanceElement.textContent = this.formatCurrency(this.account.balance);
    }
    
    // Update positions
    this.updatePositionsTable();
    
    // Update trade history
    this.updateTradeHistoryTable();
    
    // Update performance metrics
    this.updatePerformanceMetrics();
  }
  
  // Update positions table
  updatePositionsTable() {
    const containerElement = document.getElementById('positions-container');
    if (!containerElement) return;
    
    if (!this.account.positions || this.account.positions.length === 0) {
      containerElement.innerHTML = '<div class="alert alert-info">No open positions</div>';
      return;
    }
    
    // Create table
    const table = document.createElement('table');
    table.className = 'table table-sm';
    
    // Table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
      <tr>
        <th>Symbol</th>
        <th>Side</th>
        <th>Size</th>
        <th>Entry Price</th>
        <th>Current Price</th>
        <th>PnL</th>
        <th>Actions</th>
      </tr>
    `;
    table.appendChild(thead);
    
    // Table body
    const tbody = document.createElement('tbody');
    
    this.account.positions.forEach(position => {
      const tr = document.createElement('tr');
      
      const pnlPercent = position.pnl_percent;
      const pnlClass = pnlPercent > 0 ? 'text-success' : pnlPercent < 0 ? 'text-danger' : '';
      
      tr.innerHTML = `
        <td>${position.symbol}</td>
        <td>${position.side}</td>
        <td>${position.quantity.toFixed(5)}</td>
        <td>${position.entry_price.toFixed(2)}</td>
        <td>${position.current_price.toFixed(2)}</td>
        <td class="${pnlClass}">${pnlPercent.toFixed(2)}%</td>
        <td>
          <button class="btn btn-danger btn-sm close-position-btn" data-position-id="${position.id}">
            Close
          </button>
        </td>
      `;
      
      tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    containerElement.innerHTML = '';
    containerElement.appendChild(table);
    
    // Add event listeners for close buttons
    document.querySelectorAll('.close-position-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const positionId = e.target.dataset.positionId;
        this.closePosition(positionId);
      });
    });
  }
  
  // Update trade history table
  updateTradeHistoryTable() {
    const containerElement = document.getElementById('trade-history-container');
    if (!containerElement) return;
    
    if (!this.account.trade_history || this.account.trade_history.length === 0) {
      containerElement.innerHTML = '<div class="alert alert-info">No trade history</div>';
      return;
    }
    
    // Create table
    const table = document.createElement('table');
    table.className = 'table table-sm';
    
    // Table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
      <tr>
        <th>Symbol</th>
        <th>Side</th>
        <th>Quantity</th>
        <th>Entry Price</th>
        <th>Exit Price</th>
        <th>PnL</th>
        <th>Time</th>
      </tr>
    `;
    table.appendChild(thead);
    
    // Table body
    const tbody = document.createElement('tbody');
    
    // Sort by timestamp descending (newest first)
    const sortedHistory = [...this.account.trade_history].sort((a, b) => {
      return new Date(b.timestamp) - new Date(a.timestamp);
    });
    
    // Take only the last 10 trades
    const recentTrades = sortedHistory.slice(0, 10);
    
    recentTrades.forEach(trade => {
      const tr = document.createElement('tr');
      
      const pnlPercent = trade.pnl_percent;
      const pnlClass = pnlPercent > 0 ? 'text-success' : pnlPercent < 0 ? 'text-danger' : '';
      
      tr.innerHTML = `
        <td>${trade.symbol}</td>
        <td>${trade.side}</td>
        <td>${trade.quantity.toFixed(5)}</td>
        <td>${trade.entry_price.toFixed(2)}</td>
        <td>${trade.exit_price.toFixed(2)}</td>
        <td class="${pnlClass}">${pnlPercent.toFixed(2)}%</td>
        <td>${this.formatDate(trade.timestamp)}</td>
      `;
      
      tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    containerElement.innerHTML = '';
    containerElement.appendChild(table);
  }
  
  // Update performance metrics
  updatePerformanceMetrics() {
    const metrics = this.account.performance_metrics;
    if (!metrics) return;
    
    // Update each metric element
    this.updateMetricElement('win-rate', metrics.win_rate ? (metrics.win_rate * 100).toFixed(2) + '%' : 'N/A');
    this.updateMetricElement('profit-factor', metrics.profit_factor ? metrics.profit_factor.toFixed(2) : 'N/A');
    this.updateMetricElement('total-trades', metrics.total_trades || 0);
    this.updateMetricElement('total-profit', metrics.total_profit ? (metrics.total_profit * 100).toFixed(2) + '%' : '0.00%');
    this.updateMetricElement('max-drawdown', metrics.max_drawdown ? (metrics.max_drawdown * 100).toFixed(2) + '%' : 'N/A');
  }
  
  // Update a single metric element
  updateMetricElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value;
      
      // Add color classes for profit/loss metrics
      if (id === 'total-profit') {
        const numValue = parseFloat(value);
        if (!isNaN(numValue)) {
          element.className = numValue > 0 ? 'metric-positive' : numValue < 0 ? 'metric-negative' : '';
        }
      }
    }
  }
  
  // Execute a trade
  async executeTrade(side, quantity) {
    if (!this.symbol || !side || !quantity) {
      console.error('Invalid trade parameters');
      return null;
    }
    
    try {
      const order = {
        symbol: this.symbol,
        side: side.toLowerCase(),
        type: 'market',
        quantity: parseFloat(quantity)
      };
      
      const response = await fetch('/api/place_order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(order)
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        console.log(`Order executed: ${side} ${quantity} ${this.symbol}`);
        
        // Refresh account info
        await this.loadAccountInfo();
        
        return result;
      } else {
        console.error('Order execution failed:', result.message);
        return null;
      }
    } catch (error) {
      console.error('Error executing trade:', error);
      return null;
    }
  }
  
  // Close a position
  async closePosition(positionId) {
    try {
      const response = await fetch('/api/close_position', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ position_id: positionId })
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        console.log(`Position ${positionId} closed successfully`);
        
        // Refresh account info
        await this.loadAccountInfo();
        
        return true;
      } else {
        console.error('Failed to close position:', result.message);
        return false;
      }
    } catch (error) {
      console.error('Error closing position:', error);
      return false;
    }
  }
  
  // Start automated trading
  async startTrading() {
    try {
      const response = await fetch('/api/start_trading', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          symbol: this.symbol,
          strategy: this.strategy,
          params: this.strategyParams[this.strategy]
        })
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        console.log('Automated trading started');
        return true;
      } else {
        console.error('Failed to start trading:', result.message);
        return false;
      }
    } catch (error) {
      console.error('Error starting trading:', error);
      return false;
    }
  }
  
  // Stop automated trading
  async stopTrading() {
    try {
      const response = await fetch('/api/stop_trading', {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        console.log('Automated trading stopped');
        return true;
      } else {
        console.error('Failed to stop trading:', result.message);
        return false;
      }
    } catch (error) {
      console.error('Error stopping trading:', error);
      return false;
    }
  }
  
  // Get current trading signal
  async getSignal() {
    try {
      const response = await fetch(`/api/get_signal?symbol=${this.symbol}&strategy=${this.strategy}`);
      const result = await response.json();
      
      if (result.signal !== undefined) {
        this.lastSignal = result.signal;
        
        // Update signal indicator
        this.updateSignalIndicator(result.signal, result.probability);
        
        return result.signal;
      } else {
        console.error('Failed to get trading signal:', result.message);
        return 0;
      }
    } catch (error) {
      console.error('Error getting trading signal:', error);
      return 0;
    }
  }
  
  // Update signal indicator in UI
  updateSignalIndicator(signal, probability) {
    const signalElement = document.getElementById('current-signal');
    const probabilityElement = document.getElementById('signal-probability');
    
    if (!signalElement) return;
    
    let signalText = 'NEUTRAL';
    let signalClass = 'signal-neutral';
    
    if (signal === 1) {
      signalText = 'BUY';
      signalClass = 'signal-buy';
    } else if (signal === -1) {
      signalText = 'SELL';
      signalClass = 'signal-sell';
    }
    
    signalElement.textContent = signalText;
    signalElement.className = signalClass;
    
    if (probabilityElement && probability !== undefined) {
      probabilityElement.textContent = (probability * 100).toFixed(1) + '%';
    }
  }
  
  // Format currency value
  formatCurrency(value) {
    return parseFloat(value).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }
  
  // Format date
  formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
