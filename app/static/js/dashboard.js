/**
 * Dashboard Controller
 * Manages the trading dashboard UI and interactions
 * 
 * Bộ điều khiển Dashboard
 * Quản lý giao diện người dùng và tương tác của bảng điều khiển giao dịch
 */

class DashboardController {
  constructor() {
    this.charts = new TradingCharts();
    // Use the global socketClient instance that's initialized in the HTML
    this.socket = window.socketClient || new SocketClient();
    this.trader = new TradingController();
    this.symbol = 'BTCUSDT';
    this.timeframe = '1h';
    this.activeBots = [];
    this.backtestResults = [];
    this.marketData = {};
    this.updateInterval = null;
  }

  // Initialize the dashboard
  async init() {
    // Setup event listeners
    this.setupEventListeners();
    
    // Make sure socket is initialized
    if (!this.socket.isConnected() && typeof this.socket.init === 'function') {
      this.socket.init();
    }
    
    // Get symbols and intervals
    await this.loadSymbols();
    await this.loadIntervals();
    
    // Get strategies
    await this.loadStrategies();
    
    // Initialize trader
    this.trader.init(this.symbol);
    
    // Load initial data
    await this.loadHistoricalData();
    
    // Setup periodic updates
    this.startPeriodicUpdates();
    
    // Initialize charts
    this.initializeCharts();
    
    // Load initial bot status
    await this.loadBotStatus();
    
    // Connect socket for real-time updates
    this.connectRealtimeUpdates();
    
    console.log('Dashboard initialized');
  }
  
  // Setup event listeners for UI interactions
  setupEventListeners() {
    // Symbol selector
    const symbolSelector = document.getElementById('symbol-selector');
    if (symbolSelector) {
      symbolSelector.addEventListener('change', (e) => {
        this.symbol = e.target.value;
        this.loadHistoricalData();
        this.trader.setSymbol(this.symbol);
      });
    }
    
    // Timeframe selector
    const intervalSelector = document.getElementById('interval-selector');
    if (intervalSelector) {
      intervalSelector.addEventListener('change', (e) => {
        this.timeframe = e.target.value;
        this.loadHistoricalData();
      });
    }
    
    // Strategy selector
    const strategySelector = document.getElementById('strategy-selector');
    if (strategySelector) {
      strategySelector.addEventListener('change', (e) => {
        const strategy = e.target.value;
        this.trader.setStrategy(strategy);
        
        // Show/hide strategy parameters based on selection
        document.querySelectorAll('.strategy-params').forEach(el => {
          el.style.display = 'none';
        });
        
        const paramsDiv = document.getElementById(`${strategy}-params`);
        if (paramsDiv) {
          paramsDiv.style.display = 'block';
        }
      });
    }
    
    // Create bot button
    const createBotBtn = document.getElementById('create-bot-btn');
    if (createBotBtn) {
      createBotBtn.addEventListener('click', () => this.createTradeBot());
    }
    
    // Buy button
    const buyBtn = document.getElementById('buy-btn');
    if (buyBtn) {
      buyBtn.addEventListener('click', () => this.executeOrder('buy'));
    }
    
    // Sell button
    const sellBtn = document.getElementById('sell-btn');
    if (sellBtn) {
      sellBtn.addEventListener('click', () => this.executeOrder('sell'));
    }
    
    // Run backtest button
    const backtestBtn = document.getElementById('run-backtest-btn');
    if (backtestBtn) {
      backtestBtn.addEventListener('click', () => this.runBacktest());
    }
  }
  
  // Load available trading symbols
  async loadSymbols() {
    try {
      const response = await fetch('/api/symbols');
      const symbols = await response.json();
      
      // Populate symbol selector
      const symbolSelector = document.getElementById('symbol-selector');
      if (symbolSelector) {
        symbolSelector.innerHTML = '';
        symbols.forEach(symbol => {
          const option = document.createElement('option');
          option.value = symbol;
          option.textContent = symbol;
          symbolSelector.appendChild(option);
        });
        
        // Set default
        symbolSelector.value = this.symbol;
      }
    } catch (error) {
      console.error('Error loading symbols:', error);
      this.showError('Failed to load trading symbols');
    }
  }
  
  // Load available time intervals
  async loadIntervals() {
    try {
      const response = await fetch('/api/intervals');
      const intervals = await response.json();
      
      // Populate interval selector
      const intervalSelector = document.getElementById('interval-selector');
      if (intervalSelector) {
        intervalSelector.innerHTML = '';
        intervals.forEach(interval => {
          const option = document.createElement('option');
          option.value = interval;
          option.textContent = interval;
          intervalSelector.appendChild(option);
        });
        
        // Set default
        intervalSelector.value = this.timeframe;
      }
    } catch (error) {
      console.error('Error loading intervals:', error);
      this.showError('Failed to load timeframes');
    }
  }
  
  // Load available trading strategies
  async loadStrategies() {
    try {
      const response = await fetch('/api/strategies');
      if (!response.ok) {
        throw new Error('Failed to load trading strategies');
      }
      
      const strategies = await response.json();
      
      // Populate strategy selector
      const strategySelector = document.getElementById('strategy-selector');
      const backTestStrategySelector = document.getElementById('backtest-strategy');
      
      // Update bot strategy selector
      if (strategySelector) {
        strategySelector.innerHTML = '';
        
        // Add default empty option with instructions
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Chọn Chiến Lược (Select Strategy)';
        defaultOption.selected = true;
        strategySelector.appendChild(defaultOption);
        
        // Add strategy options
        strategies.forEach(strategy => {
          const option = document.createElement('option');
          option.value = strategy.id;
          option.textContent = strategy.name;
          option.setAttribute('data-description', strategy.description);
          strategySelector.appendChild(option);
        });
        
        // Add help text element for strategy description if not exists
        if (!document.getElementById('strategy-description')) {
          const helpText = document.createElement('small');
          helpText.id = 'strategy-description';
          helpText.className = 'form-text text-muted mt-1';
          helpText.style.display = 'none';
          strategySelector.parentNode.appendChild(helpText);
        }
        
        // Add event listener to show strategy-specific parameters and description
        strategySelector.addEventListener('change', (e) => {
          const selectedStrategy = e.target.value;
          this.showStrategyParams(selectedStrategy, 'bot');
          
          // Show strategy description
          const selectedOption = strategySelector.options[strategySelector.selectedIndex];
          const description = selectedOption.getAttribute('data-description');
          const helpText = document.getElementById('strategy-description');
          
          if (helpText && description) {
            helpText.textContent = description;
            helpText.style.display = 'block';
          } else if (helpText) {
            helpText.style.display = 'none';
          }
        });
      }
      
      // Update backtest strategy selector
      if (backTestStrategySelector) {
        backTestStrategySelector.innerHTML = '';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Chọn Chiến Lược (Select Strategy)';
        defaultOption.selected = true;
        backTestStrategySelector.appendChild(defaultOption);
        
        // Add strategy options
        strategies.forEach(strategy => {
          const option = document.createElement('option');
          option.value = strategy.id;
          option.textContent = strategy.name;
          option.setAttribute('data-description', strategy.description);
          backTestStrategySelector.appendChild(option);
        });
        
        // Add help text element for strategy description if not exists
        if (!document.getElementById('backtest-strategy-description')) {
          const helpText = document.createElement('small');
          helpText.id = 'backtest-strategy-description';
          helpText.className = 'form-text text-muted mt-1';
          helpText.style.display = 'none';
          backTestStrategySelector.parentNode.appendChild(helpText);
        }
        
        // Add event listener to show strategy-specific parameters and description
        backTestStrategySelector.addEventListener('change', (e) => {
          const selectedStrategy = e.target.value;
          this.showStrategyParams(selectedStrategy, 'backtest');
          
          // Show strategy description
          const selectedOption = backTestStrategySelector.options[backTestStrategySelector.selectedIndex];
          const description = selectedOption.getAttribute('data-description');
          const helpText = document.getElementById('backtest-strategy-description');
          
          if (helpText && description) {
            helpText.textContent = description;
            helpText.style.display = 'block';
          } else if (helpText) {
            helpText.style.display = 'none';
          }
        });
      }
    } catch (error) {
      console.error('Error loading strategies:', error);
      this.showError('Không thể tải chiến lược giao dịch (Failed to load trading strategies)');
    }
  }
  
  // Load historical price data
  async loadHistoricalData() {
    try {
      this.showLoading(true);
      
      const response = await fetch(`/api/historical_data?symbol=${this.symbol}&interval=${this.timeframe}`);
      const data = await response.json();
      
      // Update chart data
      this.charts.updateChartData(data);
      
      // Update charts
      this.charts.updateAllCharts();
      
      // Update price display
      if (data.length > 0) {
        this.charts.updatePriceDisplay(data[data.length - 1].close);
      }
      
      // Load technical indicators
      await this.loadIndicators();
      
      this.showLoading(false);
    } catch (error) {
      console.error('Error loading historical data:', error);
      this.showError('Failed to load price data');
      this.showLoading(false);
    }
  }
  
  // Load technical indicators
  async loadIndicators() {
    try {
      const response = await fetch(`/api/indicators?symbol=${this.symbol}&interval=${this.timeframe}`);
      const data = await response.json();
      
      // Update indicators display
      this.updateIndicatorsDisplay(data);
    } catch (error) {
      console.error('Error loading indicators:', error);
    }
  }
  
  // Initialize charts
  initializeCharts() {
    // Main price chart
    this.charts.initPriceChart('price-chart');
    
    // RSI chart
    this.charts.initRSIChart('rsi-chart');
    
    // MACD chart
    this.charts.initMACDChart('macd-chart');
  }
  
  // Start periodic updates
  startPeriodicUpdates() {
    // Clear existing interval if any
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
    }
    
    // Setup new interval (every 60 seconds)
    this.updateInterval = setInterval(() => {
      this.loadMarketData();
      this.loadBotStatus();
    }, 60000);
    
    // Initial update
    this.loadMarketData();
  }
  
  // Load market data
  async loadMarketData() {
    try {
      const response = await fetch(`/api/market_data?symbol=${this.symbol}`);
      this.marketData = await response.json();
      
      // Update market data display
      this.updateMarketDataDisplay();
    } catch (error) {
      console.error('Error loading market data:', error);
    }
  }
  
  // Update market data display
  updateMarketDataDisplay() {
    // Price element
    const priceElement = document.getElementById('current-price');
    if (priceElement && this.marketData.price) {
      this.charts.updatePriceDisplay(this.marketData.price);
    }
    
    // Quick price element (thay đổi)
    const quickPriceElement = document.getElementById('quick-price');
    if (quickPriceElement && this.marketData.price) {
      const formattedPrice = new Intl.NumberFormat('vi-VN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(this.marketData.price);
      quickPriceElement.innerHTML = `${formattedPrice} <span id="price-change-24h" class="badge ${this.marketData.change_24h >= 0 ? 'text-bg-success' : 'text-bg-danger'}">${this.marketData.change_24h >= 0 ? '+' : ''}${this.marketData.change_24h.toFixed(2)}%</span>`;
    }
    
    // 24h change
    const changeElement = document.getElementById('price-change-24h');
    if (changeElement && this.marketData.change_24h !== undefined) {
      const change = this.marketData.change_24h;
      changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
      changeElement.className = `badge ${change >= 0 ? 'text-bg-success' : 'text-bg-danger'}`;
    }
    
    // 24h volume
    const volumeElement = document.getElementById('volume-24h');
    if (volumeElement && this.marketData.volume_24h) {
      const volume = this.marketData.volume_24h;
      volumeElement.textContent = volume.toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      });
    }
    
    // 24h high/low
    const highElement = document.getElementById('price-high-24h');
    const lowElement = document.getElementById('price-low-24h');
    
    if (highElement && this.marketData.high_24h) {
      highElement.textContent = this.marketData.high_24h.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    }
    
    if (lowElement && this.marketData.low_24h) {
      lowElement.textContent = this.marketData.low_24h.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    }
  }
  
  // Update indicators display
  updateIndicatorsDisplay(data) {
    // RSI
    const rsiElement = document.getElementById('rsi-value');
    if (rsiElement && data.rsi) {
      rsiElement.textContent = data.rsi.toFixed(2);
      
      // Set color based on value
      if (data.rsi > 70) {
        rsiElement.className = 'text-danger';
      } else if (data.rsi < 30) {
        rsiElement.className = 'text-success';
      } else {
        rsiElement.className = 'text-light';
      }
    }
    
    // MACD
    const macdElement = document.getElementById('macd-value');
    if (macdElement && data.macd !== undefined) {
      macdElement.textContent = data.macd.toFixed(2);
      macdElement.className = data.macd >= 0 ? 'text-success' : 'text-danger';
    }
    
    // MACD Signal
    const macdSignalElement = document.getElementById('macd-signal-value');
    if (macdSignalElement && data.macd_signal !== undefined) {
      macdSignalElement.textContent = data.macd_signal.toFixed(2);
    }
    
    // EMA Cross
    const emaCrossElement = document.getElementById('ema-cross-value');
    if (emaCrossElement && data.ema9 && data.ema21) {
      const ema9 = data.ema9;
      const ema21 = data.ema21;
      const crossState = ema9 > ema21 ? 'Bullish' : 'Bearish';
      emaCrossElement.textContent = crossState;
      emaCrossElement.className = ema9 > ema21 ? 'text-success' : 'text-danger';
    }
    
    // Bollinger Bands Width
    const bbWidthElement = document.getElementById('bb-width-value');
    if (bbWidthElement && data.bb_upper && data.bb_lower && data.bb_middle) {
      const width = ((data.bb_upper - data.bb_lower) / data.bb_middle) * 100;
      bbWidthElement.textContent = width.toFixed(2) + '%';
    }
    
    // Volume Ratio
    const volumeRatioElement = document.getElementById('volume-ratio-value');
    if (volumeRatioElement && data.volume_ratio) {
      volumeRatioElement.textContent = data.volume_ratio.toFixed(2) + 'x';
      volumeRatioElement.className = data.volume_ratio > 1 ? 'text-success' : 'text-light';
    }
  }
  
  // Create a new trading bot
  async createTradeBot() {
    try {
      this.showLoading(true);
      
      // Get strategy parameters
      const strategySelector = document.getElementById('strategy-selector');
      const strategy = strategySelector ? strategySelector.value : '';
      
      if (!strategy) {
        this.showError('Vui lòng chọn chiến lược giao dịch (Please select a trading strategy)');
        this.showLoading(false);
        return;
      }
      
      // Get strategy-specific parameters
      let params = {};
      
      if (strategy === 'rsi') {
        params = {
          overbought: parseFloat(document.getElementById('rsi-overbought').value || 70),
          oversold: parseFloat(document.getElementById('rsi-oversold').value || 30)
        };
      } else if (strategy === 'ema_cross') {
        params = {
          short_period: parseInt(document.getElementById('ema-short-period').value || 9),
          long_period: parseInt(document.getElementById('ema-long-period').value || 21)
        };
      } else if (strategy === 'bbands') {
        params = {
          deviation_multiplier: parseFloat(document.getElementById('bb-multiplier').value || 2.0)
        };
      } else if (strategy === 'macd') {
        // MACD doesn't need parameters in this implementation
        params = {};
      } else if (strategy === 'ml') {
        params = {
          probability_threshold: parseFloat(document.getElementById('ml-threshold').value || 0.65)
        };
      }
      
      // Create bot request
      const botData = {
        symbol: this.symbol,
        interval: this.timeframe,
        strategy: strategy,
        params: params
      };
      
      console.log('Creating bot with data:', botData);
      
      const response = await fetch('/api/create_bot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(botData)
      });
      
      const result = await response.json();
      
      if (response.ok && result.bot_id) {
        this.showSuccess(result.message || `Bot tạo thành công với ID: ${result.bot_id}`);
        // Refresh bot status
        await this.loadBotStatus();
      } else {
        this.showError(result.error || 'Không thể tạo bot giao dịch (Failed to create bot)');
      }
      
      this.showLoading(false);
    } catch (error) {
      console.error('Error creating bot:', error);
      this.showError('Lỗi khi tạo bot: ' + (error.message || 'Không rõ lỗi'));
      this.showLoading(false);
    }
  }
  
  // Execute a manual trading order
  async executeOrder(side) {
    try {
      // Get quantity
      const quantityInput = document.getElementById('order-quantity');
      const quantity = parseFloat(quantityInput?.value || 0);
      
      if (!quantity || quantity <= 0) {
        this.showError('Please enter a valid quantity');
        return;
      }
      
      // Place order
      const orderData = {
        symbol: this.symbol,
        side: side,
        type: 'market',
        quantity: quantity
      };
      
      const response = await fetch('/api/place_order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orderData)
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        this.showSuccess(`Order executed: ${side.toUpperCase()} ${quantity} ${this.symbol}`);
        // Clear quantity input
        if (quantityInput) quantityInput.value = '';
      } else {
        this.showError(result.message || 'Failed to execute order');
      }
    } catch (error) {
      console.error('Error executing order:', error);
      this.showError('Failed to execute order');
    }
  }
  
  // Load bot status
  async loadBotStatus() {
    try {
      const response = await fetch('/api/bot_status');
      this.activeBots = await response.json();
      
      // Update bot status display
      this.updateBotStatusDisplay();
    } catch (error) {
      console.error('Error loading bot status:', error);
    }
  }
  
  // Update bot status display
  updateBotStatusDisplay() {
    const botListContainer = document.getElementById('active-bots-container');
    if (!botListContainer) return;
    
    // Clear container
    botListContainer.innerHTML = '';
    
    if (this.activeBots.length === 0) {
      botListContainer.innerHTML = '<div class="alert alert-info">Chưa có bot nào đang hoạt động. <small class="text-secondary">(No active bots)</small></div>';
      return;
    }
    
    // Create table
    const table = document.createElement('table');
    table.className = 'table table-sm table-hover';
    
    // Table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
      <tr>
        <th>Cặp Giao Dịch <small class="text-secondary">(Symbol)</small></th>
        <th>Chiến Lược <small class="text-secondary">(Strategy)</small></th>
        <th>Trạng Thái <small class="text-secondary">(Status)</small></th>
        <th>Giao Dịch <small class="text-secondary">(Trades)</small></th>
        <th>Tỉ Lệ Thắng <small class="text-secondary">(Win Rate)</small></th>
        <th>Lãi/Lỗ <small class="text-secondary">(P&L)</small></th>
        <th>Thao Tác <small class="text-secondary">(Actions)</small></th>
      </tr>
    `;
    table.appendChild(thead);
    
    // Table body
    const tbody = document.createElement('tbody');
    
    this.activeBots.forEach(bot => {
      const tr = document.createElement('tr');
      
      // Format metrics
      const trades = bot.metrics.total_trades || 0;
      const winRate = bot.metrics.win_rate ? (bot.metrics.win_rate * 100).toFixed(2) + '%' : 'N/A';
      const pnl = bot.metrics.profit_pct ? (bot.metrics.profit_pct * 100).toFixed(2) + '%' : '0.00%';
      const pnlClass = bot.metrics.profit_pct > 0 ? 'text-success' : bot.metrics.profit_pct < 0 ? 'text-danger' : '';
      
      tr.innerHTML = `
        <td>${bot.symbol}</td>
        <td>${bot.strategy}</td>
        <td><span class="badge ${bot.running ? 'bg-success' : 'bg-danger'}">${bot.running ? 'Đang Chạy' : 'Đã Dừng'}</span></td>
        <td>${trades}</td>
        <td>${winRate}</td>
        <td class="${pnlClass}">${pnl}</td>
        <td>
          <button class="btn btn-sm ${bot.running ? 'btn-warning' : 'btn-success'} me-1" 
                  data-bot-id="${bot.bot_id}" 
                  data-action="${bot.running ? 'stop' : 'start'}">
            ${bot.running ? 'Dừng' : 'Chạy'}
          </button>
          <button class="btn btn-sm btn-danger" data-bot-id="${bot.bot_id}" data-action="delete">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
              <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
              <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
            </svg>
          </button>
        </td>
      `;
      
      tbody.appendChild(tr);
    });
    
    table.appendChild(tbody);
    botListContainer.appendChild(table);
    
    // Add event listeners for bot actions
    document.querySelectorAll('[data-bot-id]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const botId = e.target.dataset.botId;
        const action = e.target.dataset.action;
        
        if (action === 'stop') {
          this.stopBot(botId);
        } else if (action === 'start') {
          this.startBot(botId);
        } else if (action === 'delete') {
          this.deleteBot(botId);
        }
      });
    });
  }
  
  // Stop a trading bot
  async stopBot(botId) {
    try {
      const response = await fetch('/api/stop_bot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bot_id: botId })
      });
      
      const result = await response.json();
      
      if (result.status === 'stopped') {
        this.showSuccess(`Bot ${botId} stopped successfully`);
        // Refresh bot status
        await this.loadBotStatus();
      } else {
        this.showError(result.error || 'Failed to stop bot');
      }
    } catch (error) {
      console.error('Error stopping bot:', error);
      this.showError('Failed to stop trading bot');
    }
  }
  
  // Start a trading bot
  async startBot(botId) {
    try {
      const response = await fetch('/api/start_bot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bot_id: botId })
      });
      
      const result = await response.json();
      
      if (result.status === 'started') {
        this.showSuccess(`Bot ${botId} started successfully`);
        // Refresh bot status
        await this.loadBotStatus();
      } else {
        this.showError(result.error || 'Failed to start bot');
      }
    } catch (error) {
      console.error('Error starting bot:', error);
      this.showError('Failed to start trading bot');
    }
  }
  
  // Delete a trading bot
  async deleteBot(botId) {
    try {
      const response = await fetch('/api/delete_bot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ bot_id: botId })
      });
      
      const result = await response.json();
      
      if (result.status === 'deleted') {
        this.showSuccess(`Bot ${botId} deleted successfully`);
        // Refresh bot status
        await this.loadBotStatus();
      } else {
        this.showError(result.error || 'Failed to delete bot');
      }
    } catch (error) {
      console.error('Error deleting bot:', error);
      this.showError('Failed to delete trading bot');
    }
  }
  
  // Run backtest
  async runBacktest() {
    try {
      this.showLoading(true);
      
      // Get backtest parameters
      const strategy = document.getElementById('backtest-strategy').value;
      const lookbackDays = parseInt(document.getElementById('backtest-lookback').value || 30);
      const initialBalance = parseFloat(document.getElementById('backtest-initial-balance').value || 10000);
      
      // Get strategy-specific parameters
      let params = {};
      
      if (strategy === 'rsi') {
        params = {
          overbought: parseFloat(document.getElementById('backtest-rsi-overbought').value || 70),
          oversold: parseFloat(document.getElementById('backtest-rsi-oversold').value || 30)
        };
      } else if (strategy === 'ema_cross') {
        params = {
          short_period: parseInt(document.getElementById('backtest-ema-short').value || 9),
          long_period: parseInt(document.getElementById('backtest-ema-long').value || 21)
        };
      }
      
      // Create backtest request
      const backtestData = {
        symbol: this.symbol,
        interval: this.timeframe,
        strategy: strategy,
        params: params,
        lookback_days: lookbackDays,
        initial_balance: initialBalance
      };
      
      const response = await fetch('/api/run_backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(backtestData)
      });
      
      const result = await response.json();
      
      if (result.backtest_id) {
        this.showSuccess('Backtest completed successfully');
        
        // Store backtest results
        this.backtestResults.push(result);
        
        // Display backtest results
        this.displayBacktestResults(result);
      } else {
        this.showError(result.error || 'Failed to run backtest');
      }
      
      this.showLoading(false);
    } catch (error) {
      console.error('Error running backtest:', error);
      this.showError('Failed to run backtest');
      this.showLoading(false);
    }
  }
  
  // Display backtest results
  displayBacktestResults(results) {
    // Get the container
    const resultsContainer = document.getElementById('backtest-results-container');
    if (!resultsContainer) return;
    
    // Create results card
    const card = document.createElement('div');
    card.className = 'card mb-4';
    
    // Format metrics
    const metrics = results.metrics;
    const totalTrades = metrics.total_trades;
    const winRate = (metrics.win_rate * 100).toFixed(2) + '%';
    const profitPercent = (metrics.profit_pct * 100).toFixed(2) + '%';
    const profitAmount = metrics.profit_amount.toFixed(2);
    const maxDrawdown = (metrics.max_drawdown * 100).toFixed(2) + '%';
    const sharpeRatio = metrics.sharpe_ratio ? metrics.sharpe_ratio.toFixed(2) : 'N/A';
    
    card.innerHTML = `
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Backtest Results: ${this.symbol} (${this.timeframe})</h5>
        <span class="badge ${metrics.profit_pct >= 0 ? 'bg-success' : 'bg-danger'}">
          ${profitPercent} P&L
        </span>
      </div>
      <div class="card-body">
        <div class="row mb-3">
          <div class="col-md-3 col-sm-6">
            <div class="card bg-secondary">
              <div class="card-body text-center p-3">
                <h6 class="card-title">Total Trades</h6>
                <p class="metric-value">${totalTrades}</p>
              </div>
            </div>
          </div>
          <div class="col-md-3 col-sm-6">
            <div class="card bg-secondary">
              <div class="card-body text-center p-3">
                <h6 class="card-title">Win Rate</h6>
                <p class="metric-value">${winRate}</p>
              </div>
            </div>
          </div>
          <div class="col-md-3 col-sm-6">
            <div class="card bg-secondary">
              <div class="card-body text-center p-3">
                <h6 class="card-title">Profit</h6>
                <p class="metric-value ${metrics.profit_pct >= 0 ? 'metric-positive' : 'metric-negative'}">
                  ${profitAmount}
                </p>
              </div>
            </div>
          </div>
          <div class="col-md-3 col-sm-6">
            <div class="card bg-secondary">
              <div class="card-body text-center p-3">
                <h6 class="card-title">Max Drawdown</h6>
                <p class="metric-value metric-negative">${maxDrawdown}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="chart-container">
          <canvas id="backtest-chart-${results.backtest_id}"></canvas>
        </div>
        
        <h6 class="mt-3 mb-2">Trade History</h6>
        <div class="table-responsive">
          <table class="table table-sm">
            <thead>
              <tr>
                <th>Side</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Amount</th>
                <th>P&L</th>
                <th>P&L %</th>
              </tr>
            </thead>
            <tbody>
              ${results.trades.slice(0, 5).map(trade => `
                <tr>
                  <td>${trade.side}</td>
                  <td>${parseFloat(trade.entry_price).toFixed(2)}</td>
                  <td>${parseFloat(trade.exit_price).toFixed(2)}</td>
                  <td>${parseFloat(trade.amount).toFixed(2)}</td>
                  <td class="${trade.pnl_amount >= 0 ? 'text-success' : 'text-danger'}">
                    ${parseFloat(trade.pnl_amount).toFixed(2)}
                  </td>
                  <td class="${trade.pnl_pct >= 0 ? 'text-success' : 'text-danger'}">
                    ${(trade.pnl_pct * 100).toFixed(2)}%
                  </td>
                </tr>
              `).join('')}
              ${results.trades.length > 5 ? `
                <tr>
                  <td colspan="6" class="text-center">
                    <em>Showing 5 of ${results.trades.length} trades</em>
                  </td>
                </tr>
              ` : ''}
            </tbody>
          </table>
        </div>
      </div>
    `;
    
    // Insert at the beginning
    if (resultsContainer.firstChild) {
      resultsContainer.insertBefore(card, resultsContainer.firstChild);
    } else {
      resultsContainer.appendChild(card);
    }
    
    // Initialize backtest chart
    setTimeout(() => {
      this.charts.initBacktestChart(`backtest-chart-${results.backtest_id}`, results);
    }, 100);
  }
  
  // Connect real-time price updates via socket
  connectRealtimeUpdates() {
    this.socket.subscribe('price_update', (data) => {
      if (data.symbol === this.symbol) {
        // Update price display
        this.charts.updatePriceDisplay(data.price);
        
        // Update price in market data
        if (this.marketData) {
          this.marketData.price = data.price;
        }
      }
    });
  }
  
  // Show loading indicator
  showLoading(show) {
    const loader = document.getElementById('page-loader');
    if (loader) {
      loader.style.display = show ? 'flex' : 'none';
    }
  }
  
  // Show success message
  showSuccess(message) {
    // Create toast
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="toast-header bg-success text-white">
        <strong class="me-auto">Thành Công <small class="text-light">(Success)</small></strong>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toastContainer.removeChild(toast);
      }, 500);
    }, 5000);
  }
  
  // Show error message
  showError(message) {
    // Create toast
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="toast-header bg-danger text-white">
        <strong class="me-auto">Lỗi <small class="text-light">(Error)</small></strong>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
      <div class="toast-body">
        ${message}
      </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        toastContainer.removeChild(toast);
      }, 500);
    }, 5000);
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  const dashboard = new DashboardController();
  dashboard.init();
  
  // Expose to global scope for debugging
  window.dashboard = dashboard;
});
