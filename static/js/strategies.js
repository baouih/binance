// Strategies.js - JavaScript for the Strategies page

// Strategy parameter templates
const strategyParameters = {
    technical: `
        <h6>Technical Parameters</h6>
        <div class="p-3 border rounded bg-secondary bg-opacity-10 mb-3">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="indicator-type" class="form-label">Primary Indicator</label>
                    <select class="form-select" id="indicator-type" required>
                        <option value="rsi">RSI</option>
                        <option value="macd">MACD</option>
                        <option value="bollinger">Bollinger Bands</option>
                        <option value="ema">EMA Crossover</option>
                        <option value="ichimoku">Ichimoku Cloud</option>
                    </select>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="confirmation-indicator" class="form-label">Confirmation Indicator</label>
                    <select class="form-select" id="confirmation-indicator">
                        <option value="">None</option>
                        <option value="volume">Volume</option>
                        <option value="adx">ADX</option>
                        <option value="stochastic">Stochastic</option>
                    </select>
                </div>
            </div>
            
            <div id="indicator-params" class="mb-3">
                <!-- RSI Parameters (default) -->
                <div class="row" id="rsi-params">
                    <div class="col-md-4 mb-3">
                        <label for="rsi-period" class="form-label">RSI Period</label>
                        <input type="number" class="form-control" id="rsi-period" value="14" min="2" max="50">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="rsi-overbought" class="form-label">Overbought Level</label>
                        <input type="number" class="form-control" id="rsi-overbought" value="70" min="50" max="90">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="rsi-oversold" class="form-label">Oversold Level</label>
                        <input type="number" class="form-control" id="rsi-oversold" value="30" min="10" max="50">
                    </div>
                </div>
            </div>
        </div>
    `,
    ml: `
        <h6>Machine Learning Parameters</h6>
        <div class="p-3 border rounded bg-secondary bg-opacity-10 mb-3">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="ml-type" class="form-label">ML Model Type</label>
                    <select class="form-select" id="ml-type" required>
                        <option value="random_forest">Random Forest</option>
                        <option value="gradient_boosting">Gradient Boosting</option>
                        <option value="neural_network">Neural Network</option>
                        <option value="ensemble">Ensemble (All Models)</option>
                    </select>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="feature-selection" class="form-label">Feature Selection</label>
                    <select class="form-select" id="feature-selection">
                        <option value="auto">Automatic</option>
                        <option value="manual">Manual</option>
                    </select>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="prediction-threshold" class="form-label">Prediction Threshold (%)</label>
                    <input type="number" class="form-control" id="prediction-threshold" value="65" min="50" max="95" step="1">
                </div>
                <div class="col-md-6 mb-3">
                    <label for="training-frequency" class="form-label">Training Frequency</label>
                    <select class="form-select" id="training-frequency">
                        <option value="daily">Daily</option>
                        <option value="weekly" selected>Weekly</option>
                        <option value="monthly">Monthly</option>
                        <option value="regime_change">On Market Regime Change</option>
                    </select>
                </div>
            </div>
            
            <div class="mb-3">
                <label class="form-label">Features to Include</label>
                <div class="row">
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="include-price" checked>
                            <label class="form-check-label" for="include-price">Price Action</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="include-volume" checked>
                            <label class="form-check-label" for="include-volume">Volume Metrics</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="include-indicators" checked>
                            <label class="form-check-label" for="include-indicators">Technical Indicators</label>
                        </div>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="include-sentiment">
                            <label class="form-check-label" for="include-sentiment">Sentiment Data</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="include-onchain">
                            <label class="form-check-label" for="include-onchain">On-chain Metrics</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="include-market-regime" checked>
                            <label class="form-check-label" for="include-market-regime">Market Regime</label>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `,
    sentiment: `
        <h6>Sentiment Analysis Parameters</h6>
        <div class="p-3 border rounded bg-secondary bg-opacity-10 mb-3">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="sentiment-source" class="form-label">Sentiment Sources</label>
                    <select class="form-select" id="sentiment-source" multiple>
                        <option value="fear_greed_index" selected>Fear & Greed Index</option>
                        <option value="social_media">Social Media</option>
                        <option value="news_analysis">News Analysis</option>
                        <option value="order_book">Order Book Imbalance</option>
                        <option value="funding_rate">Funding Rate</option>
                    </select>
                    <div class="form-text">Hold Ctrl or Cmd to select multiple sources</div>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="sentiment-signal-threshold" class="form-label">Signal Threshold</label>
                    <input type="number" class="form-control" id="sentiment-signal-threshold" value="70" min="50" max="95" step="1">
                    <div class="form-text">Minimum confidence level to generate a signal</div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="contrarian-mode" class="form-label">Strategy Mode</label>
                    <select class="form-select" id="contrarian-mode">
                        <option value="contrarian" selected>Contrarian</option>
                        <option value="follow">Follow Trend</option>
                        <option value="adaptive">Adaptive (Regime-based)</option>
                    </select>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="sentiment-lookback" class="form-label">Lookback Period</label>
                    <input type="number" class="form-control" id="sentiment-lookback" value="7" min="1" max="30">
                    <div class="form-text">Days to analyze for sentiment trends</div>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="require-confirmation" checked>
                    <label class="form-check-label" for="require-confirmation">
                        Require technical confirmation
                    </label>
                    <div class="form-text">Only generate signals when confirmed by technical indicators</div>
                </div>
            </div>
        </div>
    `,
    composite: `
        <h6>Composite Strategy Parameters</h6>
        <div class="p-3 border rounded bg-secondary bg-opacity-10 mb-3">
            <div class="mb-3">
                <label class="form-label">Component Strategies</label>
                <div class="row">
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="use-technical" checked>
                            <label class="form-check-label" for="use-technical">Technical Analysis</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="use-ml" checked>
                            <label class="form-check-label" for="use-ml">Machine Learning</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="use-sentiment" checked>
                            <label class="form-check-label" for="use-sentiment">Sentiment Analysis</label>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="composite-signal-threshold" class="form-label">Signal Threshold</label>
                    <input type="number" class="form-control" id="composite-signal-threshold" value="0.6" min="0.1" max="1.0" step="0.1">
                    <div class="form-text">Minimum combined score (-1 to 1) to generate a signal</div>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="weightings-method" class="form-label">Strategy Weightings</label>
                    <select class="form-select" id="weightings-method">
                        <option value="equal">Equal Weights</option>
                        <option value="dynamic" selected>Dynamic (Performance-based)</option>
                        <option value="regime">Regime-dependent</option>
                        <option value="custom">Custom</option>
                    </select>
                </div>
            </div>
            
            <div id="custom-weights" style="display: none;">
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label for="technical-weight" class="form-label">Technical Weight</label>
                        <input type="number" class="form-control" id="technical-weight" value="0.3" min="0" max="1" step="0.1">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="ml-weight" class="form-label">ML Weight</label>
                        <input type="number" class="form-control" id="ml-weight" value="0.4" min="0" max="1" step="0.1">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="sentiment-weight" class="form-label">Sentiment Weight</label>
                        <input type="number" class="form-control" id="sentiment-weight" value="0.3" min="0" max="1" step="0.1">
                    </div>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="use-market-regime-filter" checked>
                    <label class="form-check-label" for="use-market-regime-filter">
                        Use market regime filter
                    </label>
                    <div class="form-text">Adjust strategy parameters based on current market regime</div>
                </div>
            </div>
        </div>
    `,
    orderflow: `
        <h6>Order Flow Analysis Parameters</h6>
        <div class="p-3 border rounded bg-secondary bg-opacity-10 mb-3">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="liquidity-source" class="form-label">Liquidity Data Source</label>
                    <select class="form-select" id="liquidity-source" required>
                        <option value="order_book" selected>Order Book</option>
                        <option value="vwap">VWAP</option>
                        <option value="cumulative_delta">Cumulative Delta</option>
                        <option value="composite">Composite (All Sources)</option>
                    </select>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="order-book-depth" class="form-label">Order Book Depth</label>
                    <input type="number" class="form-control" id="order-book-depth" value="20" min="5" max="50">
                    <div class="form-text">Number of price levels to analyze</div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6 mb-3">
                    <label for="liquidity-threshold" class="form-label">Liquidity Threshold</label>
                    <input type="number" class="form-control" id="liquidity-threshold" value="2.0" min="0.5" max="10" step="0.1">
                    <div class="form-text">Minimum liquidity ratio to identify a significant zone</div>
                </div>
                <div class="col-md-6 mb-3">
                    <label for="update-frequency" class="form-label">Update Frequency (sec)</label>
                    <input type="number" class="form-control" id="update-frequency" value="30" min="5" max="300" step="5">
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="detect-liquidity-sweeps" checked>
                    <label class="form-check-label" for="detect-liquidity-sweeps">
                        Detect liquidity sweeps
                    </label>
                    <div class="form-text">Generate signals on liquidity sweeps and order book imbalances</div>
                </div>
            </div>
            
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="require-technical-confirmation">
                    <label class="form-check-label" for="require-technical-confirmation">
                        Require technical confirmation
                    </label>
                    <div class="form-text">Only generate signals when confirmed by technical indicators</div>
                </div>
            </div>
        </div>
    `
};

// Strategies manager
const strategiesManager = {
    // Initialize the component
    init: function() {
        // Add event listeners
        document.getElementById('create-strategy-btn').addEventListener('click', this.showCreateStrategyModal);
        document.getElementById('save-strategy-btn').addEventListener('click', this.saveStrategy);
        document.getElementById('activate-all-btn').addEventListener('click', this.activateAll);
        document.getElementById('deactivate-all-btn').addEventListener('click', this.deactivateAll);
        
        // Strategy type change event
        document.getElementById('strategy-type-select').addEventListener('change', this.updateStrategyParameters);
        
        // Add event listeners for view, edit, activate, and deactivate buttons
        document.querySelectorAll('.view-strategy').forEach(button => {
            button.addEventListener('click', this.viewStrategy.bind(this));
        });
        
        document.querySelectorAll('.edit-strategy').forEach(button => {
            button.addEventListener('click', this.editStrategy.bind(this));
        });
        
        document.querySelectorAll('.activate-strategy').forEach(button => {
            button.addEventListener('click', this.activateStrategy.bind(this));
        });
        
        document.querySelectorAll('.deactivate-strategy').forEach(button => {
            button.addEventListener('click', this.deactivateStrategy.bind(this));
        });
        
        // Add event listener for indicator type change
        const indicatorTypeSelect = document.getElementById('indicator-type');
        if (indicatorTypeSelect) {
            indicatorTypeSelect.addEventListener('change', this.updateIndicatorParameters);
        }
        
        // Setup toggle bot button
        document.getElementById('toggle-bot').addEventListener('click', this.toggleBot);
        
        // Update bot status badge and toggle button
        this.updateBotStatus();
        
        // Create charts
        this.createPerformanceChart();
        this.createMarketRegimeChart();
        
        // Initialize custom weights toggle
        const weightingsMethod = document.getElementById('weightings-method');
        if (weightingsMethod) {
            weightingsMethod.addEventListener('change', function() {
                const customWeights = document.getElementById('custom-weights');
                if (this.value === 'custom') {
                    customWeights.style.display = 'block';
                } else {
                    customWeights.style.display = 'none';
                }
            });
        }
    },
    
    // Show create strategy modal
    showCreateStrategyModal: function() {
        // Reset form
        document.getElementById('strategy-form').reset();
        
        // Set modal title
        document.getElementById('editStrategyModalLabel').textContent = 'Create New Strategy';
        
        // Clear strategy-specific parameters
        document.getElementById('strategy-specific-params').innerHTML = '';
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editStrategyModal'));
        modal.show();
    },
    
    // Save strategy
    saveStrategy: function() {
        // Get form values
        const strategyName = document.getElementById('strategy-name-input').value;
        const strategyType = document.getElementById('strategy-type-select').value;
        
        if (!strategyName || !strategyType) {
            alert('Please enter a strategy name and select a strategy type.');
            return;
        }
        
        // In a real implementation, this would send the data to the server
        console.log('Saving strategy:', strategyName, strategyType);
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editStrategyModal'));
        modal.hide();
        
        // Show success message
        alert('Strategy saved successfully!');
    },
    
    // Update strategy parameters based on selected strategy type
    updateStrategyParameters: function() {
        const strategyType = document.getElementById('strategy-type-select').value;
        const parametersContainer = document.getElementById('strategy-specific-params');
        
        // Update parameters HTML based on strategy type
        if (strategyParameters[strategyType]) {
            parametersContainer.innerHTML = strategyParameters[strategyType];
            
            // Initialize any sub-components
            if (strategyType === 'technical') {
                // Add event listener for indicator type change
                const indicatorTypeSelect = document.getElementById('indicator-type');
                if (indicatorTypeSelect) {
                    indicatorTypeSelect.addEventListener('change', strategiesManager.updateIndicatorParameters);
                }
            } else if (strategyType === 'composite') {
                // Initialize custom weights toggle
                const weightingsMethod = document.getElementById('weightings-method');
                if (weightingsMethod) {
                    weightingsMethod.addEventListener('change', function() {
                        const customWeights = document.getElementById('custom-weights');
                        if (this.value === 'custom') {
                            customWeights.style.display = 'block';
                        } else {
                            customWeights.style.display = 'none';
                        }
                    });
                }
            }
        } else {
            parametersContainer.innerHTML = '';
        }
    },
    
    // Update indicator parameters based on selected indicator type
    updateIndicatorParameters: function() {
        const indicatorType = document.getElementById('indicator-type').value;
        const indicatorParamsContainer = document.getElementById('indicator-params');
        
        // Define parameter templates for each indicator type
        const indicatorParams = {
            rsi: `
                <div class="row" id="rsi-params">
                    <div class="col-md-4 mb-3">
                        <label for="rsi-period" class="form-label">RSI Period</label>
                        <input type="number" class="form-control" id="rsi-period" value="14" min="2" max="50">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="rsi-overbought" class="form-label">Overbought Level</label>
                        <input type="number" class="form-control" id="rsi-overbought" value="70" min="50" max="90">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="rsi-oversold" class="form-label">Oversold Level</label>
                        <input type="number" class="form-control" id="rsi-oversold" value="30" min="10" max="50">
                    </div>
                </div>
            `,
            macd: `
                <div class="row" id="macd-params">
                    <div class="col-md-4 mb-3">
                        <label for="macd-fast" class="form-label">Fast Period</label>
                        <input type="number" class="form-control" id="macd-fast" value="12" min="5" max="30">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="macd-slow" class="form-label">Slow Period</label>
                        <input type="number" class="form-control" id="macd-slow" value="26" min="10" max="50">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="macd-signal" class="form-label">Signal Period</label>
                        <input type="number" class="form-control" id="macd-signal" value="9" min="5" max="20">
                    </div>
                </div>
            `,
            bollinger: `
                <div class="row" id="bollinger-params">
                    <div class="col-md-4 mb-3">
                        <label for="bb-period" class="form-label">BB Period</label>
                        <input type="number" class="form-control" id="bb-period" value="20" min="10" max="50">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="bb-std-dev" class="form-label">Standard Deviations</label>
                        <input type="number" class="form-control" id="bb-std-dev" value="2" min="1" max="4" step="0.1">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="bb-signal-pct" class="form-label">Signal Strength (%)</label>
                        <input type="number" class="form-control" id="bb-signal-pct" value="90" min="50" max="100">
                    </div>
                </div>
            `,
            ema: `
                <div class="row" id="ema-params">
                    <div class="col-md-4 mb-3">
                        <label for="ema-short" class="form-label">Short EMA Period</label>
                        <input type="number" class="form-control" id="ema-short" value="9" min="5" max="50">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="ema-long" class="form-label">Long EMA Period</label>
                        <input type="number" class="form-control" id="ema-long" value="21" min="10" max="100">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="ema-signal-length" class="form-label">Signal Length</label>
                        <input type="number" class="form-control" id="ema-signal-length" value="3" min="1" max="10">
                    </div>
                </div>
            `,
            ichimoku: `
                <div class="row" id="ichimoku-params">
                    <div class="col-md-3 mb-3">
                        <label for="tenkan-period" class="form-label">Tenkan Period</label>
                        <input type="number" class="form-control" id="tenkan-period" value="9" min="5" max="30">
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="kijun-period" class="form-label">Kijun Period</label>
                        <input type="number" class="form-control" id="kijun-period" value="26" min="10" max="60">
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="senkou-b-period" class="form-label">Senkou B Period</label>
                        <input type="number" class="form-control" id="senkou-b-period" value="52" min="30" max="120">
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="displacement" class="form-label">Displacement</label>
                        <input type="number" class="form-control" id="displacement" value="26" min="10" max="60">
                    </div>
                </div>
            `
        };
        
        // Update parameters HTML based on indicator type
        if (indicatorParams[indicatorType]) {
            indicatorParamsContainer.innerHTML = indicatorParams[indicatorType];
        } else {
            indicatorParamsContainer.innerHTML = '';
        }
    },
    
    // View strategy details
    viewStrategy: function(event) {
        const strategyId = event.target.getAttribute('data-strategy-id');
        
        // In a real implementation, this would fetch strategy details from the server
        console.log('Viewing strategy ID:', strategyId);
        
        // For demonstration purposes, we'll show the modal with sample data
        const strategyModal = new bootstrap.Modal(document.getElementById('strategyDetailsModal'));
        
        // Change modal title based on strategy ID
        document.getElementById('strategyDetailsModalLabel').textContent = 'Strategy Details';
        
        // Sample data for different strategies
        const strategyData = {
            '1': {
                name: 'Composite ML Strategy',
                type: 'Machine Learning',
                created: '2025-02-15',
                status: 'Active',
                winRate: '72%',
                avgReturn: '+2.8%',
                profitFactor: '2.4',
                totalTrades: '62',
                description: 'Composite ML Strategy combines multiple machine learning models trained on different market regimes to predict price movements. The strategy uses random forest, gradient boosting, and neural networks with dynamic feature selection based on current market conditions. It adapts to changing market regimes and adjusts its position sizing accordingly.',
                symbols: 'BTC/USDT, ETH/USDT',
                timeframes: '1h, 4h, 1d',
                risk: '1.5%',
                maxPositions: '2',
                threshold: '65%',
                models: 'Random Forest, GBM, Neural Net',
                featureSelection: 'Dynamic',
                trainingFreq: 'Weekly'
            },
            '2': {
                name: 'Multi-timeframe Analyzer',
                type: 'Technical',
                created: '2025-01-28',
                status: 'Active',
                winRate: '68%',
                avgReturn: '+2.1%',
                profitFactor: '1.9',
                totalTrades: '45',
                description: 'Multi-timeframe Analyzer combines signals from multiple timeframes to identify high-probability trading opportunities. It uses a time-weighted approach that prioritizes longer timeframe signals while using shorter timeframes for entry/exit timing. The strategy incorporates strong trend filters and volume confirmation.',
                symbols: 'BTC/USDT, ETH/USDT, SOL/USDT',
                timeframes: '15m, 1h, 4h, 1d',
                risk: '1.0%',
                maxPositions: '3',
                threshold: '70%',
                models: 'N/A',
                featureSelection: 'N/A',
                trainingFreq: 'N/A'
            },
            '3': {
                name: 'Sentiment-based Counter',
                type: 'Sentiment',
                created: '2025-02-20',
                status: 'Active',
                winRate: '64%',
                avgReturn: '+3.5%',
                profitFactor: '2.7',
                totalTrades: '12',
                description: 'Sentiment-based Counter is a contrarian strategy that looks for extreme market sentiment conditions to identify potential reversals. The strategy uses the Fear & Greed Index along with social media sentiment analysis to determine market psychology. It enters positions when sentiment reaches extreme levels and confirms with technical analysis.',
                symbols: 'BTC/USDT',
                timeframes: '4h, 1d',
                risk: '2.0%',
                maxPositions: '1',
                threshold: '85%',
                models: 'N/A',
                featureSelection: 'N/A',
                trainingFreq: 'N/A'
            },
            '4': {
                name: 'RSI Strategy',
                type: 'Technical',
                created: '2025-01-10',
                status: 'Inactive',
                winRate: '61%',
                avgReturn: '+1.8%',
                profitFactor: '1.6',
                totalTrades: '92',
                description: 'RSI Strategy is a mean-reversion strategy that identifies overbought and oversold conditions using the Relative Strength Index (RSI). The strategy enters long positions when RSI drops below the oversold threshold and enters short positions when RSI rises above the overbought threshold. It includes confirmation filters for trend and volume.',
                symbols: 'BTC/USDT, ETH/USDT, BNB/USDT',
                timeframes: '1h, 4h',
                risk: '1.0%',
                maxPositions: '3',
                threshold: 'N/A',
                models: 'N/A',
                featureSelection: 'N/A',
                trainingFreq: 'N/A'
            },
            '5': {
                name: 'MACD Strategy',
                type: 'Technical',
                created: '2025-01-15',
                status: 'Inactive',
                winRate: '58%',
                avgReturn: '+1.5%',
                profitFactor: '1.4',
                totalTrades: '76',
                description: 'MACD Strategy identifies trend direction and momentum using the Moving Average Convergence Divergence (MACD) indicator. The strategy enters long positions when the MACD line crosses above the signal line and enters short positions when the MACD line crosses below the signal line. It uses custom fast and slow period settings optimized for cryptocurrency markets.',
                symbols: 'BTC/USDT, ETH/USDT',
                timeframes: '1h, 4h',
                risk: '1.2%',
                maxPositions: '2',
                threshold: 'N/A',
                models: 'N/A',
                featureSelection: 'N/A',
                trainingFreq: 'N/A'
            },
            '6': {
                name: 'Liquidity Analysis',
                type: 'Order Flow',
                created: '2025-02-05',
                status: 'Inactive',
                winRate: '75%',
                avgReturn: '+2.9%',
                profitFactor: '3.1',
                totalTrades: '8',
                description: 'Liquidity Analysis strategy identifies and exploits areas of liquidity concentration in the order book. It targets liquidity sweeps and stop hunts by identifying price levels with high order density and anticipating price movements toward and away from these levels. The strategy is particularly effective in volatile market conditions.',
                symbols: 'BTC/USDT',
                timeframes: '5m, 15m, 1h',
                risk: '1.5%',
                maxPositions: '1',
                threshold: 'N/A',
                models: 'N/A',
                featureSelection: 'N/A',
                trainingFreq: 'N/A'
            }
        };
        
        // Set data in modal if we have it for this strategy
        if (strategyData[strategyId]) {
            const data = strategyData[strategyId];
            
            // Set basic information
            document.getElementById('strategy-name').textContent = data.name;
            document.getElementById('strategy-type').textContent = data.type;
            document.getElementById('strategy-created').textContent = data.created;
            document.getElementById('strategy-status').innerHTML = data.status === 'Active' ? 
                '<span class="badge bg-success">Active</span>' : 
                '<span class="badge bg-secondary">Inactive</span>';
            
            // Set performance metrics
            document.getElementById('strategy-win-rate').textContent = data.winRate;
            document.getElementById('strategy-avg-return').textContent = data.avgReturn;
            document.getElementById('strategy-profit-factor').textContent = data.profitFactor;
            document.getElementById('strategy-total-trades').textContent = data.totalTrades;
            
            // Set description
            document.getElementById('strategy-description').textContent = data.description;
            
            // Set configuration
            document.getElementById('strategy-symbols').textContent = data.symbols;
            document.getElementById('strategy-timeframes').textContent = data.timeframes;
            document.getElementById('strategy-risk').textContent = data.risk;
            document.getElementById('strategy-max-positions').textContent = data.maxPositions;
            
            // Set strategy-specific parameters
            document.getElementById('strategy-threshold').textContent = data.threshold;
            document.getElementById('strategy-models').textContent = data.models;
            document.getElementById('strategy-feature-selection').textContent = data.featureSelection;
            document.getElementById('strategy-training-freq').textContent = data.trainingFreq;
        }
        
        // Show the modal
        strategyModal.show();
        
        // Create strategy detail chart
        this.createStrategyDetailChart();
    },
    
    // Edit strategy
    editStrategy: function(event) {
        const strategyId = event.target.getAttribute('data-strategy-id');
        
        // In a real implementation, this would fetch strategy details from the server
        console.log('Editing strategy ID:', strategyId);
        
        // For demonstration purposes, we'll show the edit modal with sample data
        document.getElementById('editStrategyModalLabel').textContent = 'Edit Strategy';
        
        // Set sample form values (would come from the server in a real implementation)
        document.getElementById('strategy-name-input').value = 'Composite ML Strategy';
        document.getElementById('strategy-type-select').value = 'ml';
        this.updateStrategyParameters();
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editStrategyModal'));
        modal.show();
    },
    
    // Activate strategy
    activateStrategy: function(event) {
        const strategyId = event.target.getAttribute('data-strategy-id');
        
        // In a real implementation, this would send an activation request to the server
        console.log('Activating strategy ID:', strategyId);
        
        // Show a temporary message
        alert('Strategy activated successfully!');
    },
    
    // Deactivate strategy
    deactivateStrategy: function(event) {
        const strategyId = event.target.getAttribute('data-strategy-id');
        
        // In a real implementation, this would send a deactivation request to the server
        console.log('Deactivating strategy ID:', strategyId);
        
        // Show a temporary message
        alert('Strategy deactivated successfully!');
    },
    
    // Activate all strategies
    activateAll: function() {
        // In a real implementation, this would send an activation request for all strategies
        console.log('Activating all strategies');
        
        // Show a temporary message
        alert('All strategies activated successfully!');
    },
    
    // Deactivate all strategies
    deactivateAll: function() {
        // In a real implementation, this would send a deactivation request for all strategies
        console.log('Deactivating all strategies');
        
        // Show a temporary message
        alert('All strategies deactivated successfully!');
    },
    
    // Create strategy performance comparison chart
    createPerformanceChart: function() {
        const ctx = document.getElementById('strategy-performance-chart').getContext('2d');
        
        // Sample data for strategy performance
        const data = {
            labels: ['Composite ML', 'Multi-timeframe', 'Sentiment-based', 'RSI', 'MACD', 'Liquidity Analysis'],
            datasets: [
                {
                    label: 'Win Rate (%)',
                    data: [72, 68, 64, 61, 58, 75],
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Avg. Return (%)',
                    data: [2.8, 2.1, 3.5, 1.8, 1.5, 2.9],
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Profit Factor',
                    data: [2.4, 1.9, 2.7, 1.6, 1.4, 3.1],
                    backgroundColor: 'rgba(255, 206, 86, 0.5)',
                    borderColor: 'rgba(255, 206, 86, 1)',
                    borderWidth: 1
                }
            ]
        };
        
        // Create chart
        if (window.performanceChart) {
            window.performanceChart.destroy();
        }
        
        window.performanceChart = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    },
    
    // Create market regime performance chart
    createMarketRegimeChart: function() {
        const ctx = document.getElementById('market-regime-chart').getContext('2d');
        
        // Sample data for market regime performance
        const data = {
            labels: ['Trending Up', 'Trending Down', 'Ranging', 'Volatile', 'Breakout'],
            datasets: [
                {
                    label: 'Composite ML',
                    data: [2.1, 1.8, 0.9, 2.5, 3.2],
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Multi-timeframe',
                    data: [2.4, 1.5, 0.7, 1.9, 2.8],
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Sentiment-based',
                    data: [1.2, 2.7, 1.1, 3.8, 1.4],
                    backgroundColor: 'rgba(255, 206, 86, 0.5)',
                    borderColor: 'rgba(255, 206, 86, 1)',
                    borderWidth: 1
                }
            ]
        };
        
        // Create chart
        if (window.regimeChart) {
            window.regimeChart.destroy();
        }
        
        window.regimeChart = new Chart(ctx, {
            type: 'radar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        min: 0,
                        max: 4,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    },
    
    // Create strategy detail chart
    createStrategyDetailChart: function() {
        const ctx = document.getElementById('strategy-detail-chart').getContext('2d');
        
        // Generate sample data for past 30 days
        const labels = [];
        const equityData = [];
        
        // Generate dates for the last 30 days
        const today = new Date();
        for (let i = 29; i >= 0; i--) {
            const date = new Date();
            date.setDate(today.getDate() - i);
            labels.push(date.toLocaleDateString());
        }
        
        // Generate random equity curve with an upward trend
        let equity = 10000;
        for (let i = 0; i < 30; i++) {
            const dailyReturn = (Math.random() - 0.3) * 2; // Bias toward positive returns
            equity *= (1 + dailyReturn / 100);
            equityData.push(equity);
        }
        
        // Create chart
        if (window.strategyDetailChart) {
            window.strategyDetailChart.destroy();
        }
        
        window.strategyDetailChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Strategy Equity Curve',
                    data: equityData,
                    borderColor: '#11cdef',
                    backgroundColor: 'rgba(17, 205, 239, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
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
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return '$' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    },
    
    // Update bot status
    updateBotStatus: function() {
        // In a real implementation, this would fetch the bot status from the server
        const botStatusBadge = document.getElementById('bot-status-badge');
        const toggleBotButton = document.getElementById('toggle-bot');
        
        // Fetch bot status
        fetch('/api/bot/status')
            .then(response => response.json())
            .then(data => {
                // Update badge
                botStatusBadge.textContent = data.running ? 'Running' : 'Stopped';
                botStatusBadge.className = data.running ? 'badge bg-success me-2' : 'badge bg-danger me-2';
                
                // Update button
                toggleBotButton.textContent = data.running ? 'Stop Bot' : 'Start Bot';
                toggleBotButton.className = data.running ? 'btn btn-sm btn-outline-danger' : 'btn btn-sm btn-outline-success';
            })
            .catch(error => console.error('Error fetching bot status:', error));
    },
    
    // Toggle bot
    toggleBot: function() {
        const action = this.textContent === 'Stop Bot' ? 'stop' : 'start';
        
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
            // Update status after toggling
            strategiesManager.updateBotStatus();
        })
        .catch(error => console.error('Error:', error));
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize strategies manager
    strategiesManager.init();
});