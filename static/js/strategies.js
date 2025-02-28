// Strategies.js - JavaScript for the Trading Strategies page

// Strategy parameters templates
const strategyParameters = {
    rsi: `
        <div class="row">
            <div class="col-md-4 mb-3">
                <label for="rsiPeriod" class="form-label">RSI Period</label>
                <input type="number" class="form-control" id="rsiPeriod" value="14" min="2" max="50" required>
            </div>
            <div class="col-md-4 mb-3">
                <label for="rsiOverbought" class="form-label">Overbought Level</label>
                <input type="number" class="form-control" id="rsiOverbought" value="70" min="50" max="90" required>
            </div>
            <div class="col-md-4 mb-3">
                <label for="rsiOversold" class="form-label">Oversold Level</label>
                <input type="number" class="form-control" id="rsiOversold" value="30" min="10" max="50" required>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="rsiTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="rsiTakeProfit" value="2.5" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="rsiStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="rsiStopLoss" value="1.5" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="rsiUseVolume" checked>
            <label class="form-check-label" for="rsiUseVolume">Use volume confirmation</label>
        </div>
    `,
    macd: `
        <div class="row">
            <div class="col-md-4 mb-3">
                <label for="macdFast" class="form-label">Fast Period</label>
                <input type="number" class="form-control" id="macdFast" value="12" min="2" max="50" required>
            </div>
            <div class="col-md-4 mb-3">
                <label for="macdSlow" class="form-label">Slow Period</label>
                <input type="number" class="form-control" id="macdSlow" value="26" min="5" max="100" required>
            </div>
            <div class="col-md-4 mb-3">
                <label for="macdSignal" class="form-label">Signal Period</label>
                <input type="number" class="form-control" id="macdSignal" value="9" min="2" max="50" required>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="macdTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="macdTakeProfit" value="3.0" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="macdStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="macdStopLoss" value="1.8" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="macdUseHistogram" checked>
            <label class="form-check-label" for="macdUseHistogram">Use histogram for confirmation</label>
        </div>
    `,
    bbands: `
        <div class="row">
            <div class="col-md-4 mb-3">
                <label for="bbandsPeriod" class="form-label">Period</label>
                <input type="number" class="form-control" id="bbandsPeriod" value="20" min="5" max="100" required>
            </div>
            <div class="col-md-4 mb-3">
                <label for="bbandsStdDev" class="form-label">Standard Deviations</label>
                <input type="number" class="form-control" id="bbandsStdDev" value="2" min="1" max="4" step="0.1" required>
            </div>
            <div class="col-md-4 mb-3">
                <label for="bbandsSignalStrength" class="form-label">Signal Strength (%)</label>
                <input type="number" class="form-control" id="bbandsSignalStrength" value="90" min="50" max="100" required>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="bbandsTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="bbandsTakeProfit" value="2.0" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="bbandsStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="bbandsStopLoss" value="1.5" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="bbandsUseMidExit" checked>
            <label class="form-check-label" for="bbandsUseMidExit">Use middle band for exit signal</label>
        </div>
    `,
    ema_cross: `
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="emaFast" class="form-label">Fast EMA Period</label>
                <input type="number" class="form-control" id="emaFast" value="9" min="3" max="50" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="emaSlow" class="form-label">Slow EMA Period</label>
                <input type="number" class="form-control" id="emaSlow" value="21" min="5" max="200" required>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="emaTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="emaTakeProfit" value="3.5" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="emaStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="emaStopLoss" value="2.0" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="emaUseVolume" checked>
            <label class="form-check-label" for="emaUseVolume">Use volume confirmation</label>
        </div>
    `,
    ml: `
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="mlTrainingPeriod" class="form-label">Training Period (days)</label>
                <input type="number" class="form-control" id="mlTrainingPeriod" value="60" min="15" max="365" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="mlPredictionThreshold" class="form-label">Prediction Threshold (%)</label>
                <input type="number" class="form-control" id="mlPredictionThreshold" value="65" min="50" max="95" required>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="mlTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="mlTakeProfit" value="4.0" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="mlStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="mlStopLoss" value="2.5" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="mlUseEnsemble" checked>
            <label class="form-check-label" for="mlUseEnsemble">Use ensemble of models</label>
        </div>
        <div class="mb-3">
            <label class="form-label">Models to Use</label>
            <div class="row">
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mlUseRandomForest" checked>
                        <label class="form-check-label" for="mlUseRandomForest">Random Forest</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mlUseGradientBoosting" checked>
                        <label class="form-check-label" for="mlUseGradientBoosting">Gradient Boosting</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mlUseSVM" checked>
                        <label class="form-check-label" for="mlUseSVM">SVM</label>
                    </div>
                </div>
            </div>
        </div>
    `,
    composite: `
        <div class="mb-3">
            <label class="form-label">Indicators to Include</label>
            <div class="row">
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="compUseRSI" checked>
                        <label class="form-check-label" for="compUseRSI">RSI</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="compUseMACD" checked>
                        <label class="form-check-label" for="compUseMACD">MACD</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="compUseEMA" checked>
                        <label class="form-check-label" for="compUseEMA">EMA Cross</label>
                    </div>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="compUseBB" checked>
                        <label class="form-check-label" for="compUseBB">Bollinger Bands</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="compUseVol" checked>
                        <label class="form-check-label" for="compUseVol">Volume Analysis</label>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="compUseADX">
                        <label class="form-check-label" for="compUseADX">ADX</label>
                    </div>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="compSignalThreshold" class="form-label">Signal Threshold</label>
                <input type="number" class="form-control" id="compSignalThreshold" value="0.6" min="0.1" max="1.0" step="0.1" required>
                <div class="form-text">Minimum score (-1 to 1) to generate a signal</div>
            </div>
            <div class="col-md-6 mb-3">
                <label for="compLookback" class="form-label">Lookback Period</label>
                <input type="number" class="form-control" id="compLookback" value="5" min="1" max="20" required>
                <div class="form-text">Periods to analyze for trend</div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="compTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="compTakeProfit" value="3.5" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="compStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="compStopLoss" value="2.0" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="compDynamicWeights" checked>
            <label class="form-check-label" for="compDynamicWeights">Use dynamic weights based on performance</label>
        </div>
    `,
    mtf: `
        <div class="mb-3">
            <label class="form-label">Timeframes to Include</label>
            <div class="row">
                <div class="col-md-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mtfUse15m">
                        <label class="form-check-label" for="mtfUse15m">15m</label>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mtfUse1h" checked>
                        <label class="form-check-label" for="mtfUse1h">1h</label>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mtfUse4h" checked>
                        <label class="form-check-label" for="mtfUse4h">4h</label>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="mtfUse1d" checked>
                        <label class="form-check-label" for="mtfUse1d">1d</label>
                    </div>
                </div>
            </div>
        </div>
        <div class="mb-3">
            <label for="mtfPrimaryIndicator" class="form-label">Primary Indicator</label>
            <select class="form-select" id="mtfPrimaryIndicator" required>
                <option value="rsi" selected>RSI</option>
                <option value="macd">MACD</option>
                <option value="bbands">Bollinger Bands</option>
                <option value="ema_cross">EMA Crossover</option>
            </select>
        </div>
        <div class="mb-3">
            <label for="mtfConfirmationTF" class="form-label">Confirmation Timeframe</label>
            <select class="form-select" id="mtfConfirmationTF" required>
                <option value="15m">15 minutes</option>
                <option value="1h">1 hour</option>
                <option value="4h" selected>4 hours</option>
                <option value="1d">1 day</option>
            </select>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="mtfTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="mtfTakeProfit" value="3.2" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="mtfStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="mtfStopLoss" value="1.8" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="form-check mb-3">
            <input class="form-check-input" type="checkbox" id="mtfDynamicWeights" checked>
            <label class="form-check-label" for="mtfDynamicWeights">Use dynamic timeframe weights</label>
        </div>
    `,
    liquidity: `
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="liqOrderbookDepth" class="form-label">Orderbook Depth</label>
                <input type="number" class="form-control" id="liqOrderbookDepth" value="500" min="100" max="2000" step="100" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="liqRefreshRate" class="form-label">Refresh Rate (sec)</label>
                <input type="number" class="form-control" id="liqRefreshRate" value="30" min="5" max="60" required>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="liqMinimumStrength" class="form-label">Minimum Zone Strength</label>
                <input type="number" class="form-control" id="liqMinimumStrength" value="70" min="50" max="95" required>
                <div class="form-text">Minimum strength (0-100) for liquidity zones</div>
            </div>
            <div class="col-md-6 mb-3">
                <label for="liqPriceRange" class="form-label">Price Range (%)</label>
                <input type="number" class="form-control" id="liqPriceRange" value="2.0" min="0.5" max="10" step="0.1" required>
                <div class="form-text">Price range around current price to analyze</div>
            </div>
        </div>
        <div class="row">
            <div class="col-md-6 mb-3">
                <label for="liqTakeProfit" class="form-label">Take Profit (%)</label>
                <input type="number" class="form-control" id="liqTakeProfit" value="2.8" min="0.5" max="20" step="0.1" required>
            </div>
            <div class="col-md-6 mb-3">
                <label for="liqStopLoss" class="form-label">Stop Loss (%)</label>
                <input type="number" class="form-control" id="liqStopLoss" value="1.5" min="0.5" max="10" step="0.1" required>
            </div>
        </div>
        <div class="mb-3">
            <label for="liqTradeType" class="form-label">Trade Type</label>
            <select class="form-select" id="liqTradeType" required>
                <option value="both" selected>Both Long and Short</option>
                <option value="long">Long Only</option>
                <option value="short">Short Only</option>
            </select>
        </div>
    `
};

// Socket.IO instance
let socket;

// Strategy Manager
const strategyManager = {
    activeStrategies: [],
    savedStrategies: [],
    
    // Initialize the component
    init: function() {
        // Load strategies from API
        this.loadStrategies();
        
        // Add event listeners
        document.getElementById('strategyType').addEventListener('change', this.updateStrategyParameters);
        document.getElementById('saveStrategy').addEventListener('click', this.saveStrategy.bind(this));
        
        // Template buttons
        document.querySelectorAll('[data-template]').forEach(button => {
            button.addEventListener('click', (e) => {
                const templateName = e.target.getAttribute('data-template');
                this.loadTemplate(templateName);
            });
        });
    },
    
    // Load strategies from API
    loadStrategies: function() {
        // Simulate loading active strategies
        // In a real implementation, this would fetch from the server
        this.activeStrategies = [
            {
                id: 'strategy-1',
                name: 'Composite ML Strategy',
                symbol: 'BTCUSDT',
                timeframe: '1h',
                type: 'ml',
                active: true,
                parameters: {
                    risk: 2.0,
                    leverage: 3,
                    takeProfit: 3.5,
                    stopLoss: 1.8,
                    // ML specific parameters
                    trainingPeriod: 60,
                    predictionThreshold: 65,
                    useEnsemble: true,
                    models: ['randomForest', 'gradientBoosting', 'svm']
                }
            },
            {
                id: 'strategy-2',
                name: 'Multi-Timeframe RSI',
                symbol: 'ETHUSDT',
                timeframe: '4h',
                type: 'mtf',
                active: true,
                parameters: {
                    risk: 1.5,
                    leverage: 2,
                    takeProfit: 3.2,
                    stopLoss: 1.8,
                    // MTF specific parameters
                    timeframes: ['1h', '4h', '1d'],
                    primaryIndicator: 'rsi',
                    confirmationTimeframe: '4h',
                    rsiPeriod: 14,
                    rsiOverbought: 70,
                    rsiOversold: 30
                }
            }
        ];
        
        // Simulate loading saved strategies
        this.savedStrategies = [];
        
        // Render strategies
        this.renderStrategies();
    },
    
    // Render strategies to DOM
    renderStrategies: function() {
        // Render active strategies
        const activeContainer = document.getElementById('active-strategies-container');
        // Clear active strategies container (except template cards)
        activeContainer.innerHTML = '';
        
        // Add active strategies
        this.activeStrategies.forEach(strategy => {
            const card = this.createStrategyCard(strategy);
            activeContainer.appendChild(card);
        });
        
        // If no active strategies, show message
        if (this.activeStrategies.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'col-12';
            emptyMessage.innerHTML = `
                <div class="alert alert-info">
                    No active strategies yet. Create a new strategy or activate a saved one.
                </div>
            `;
            activeContainer.appendChild(emptyMessage);
        }
        
        // Render saved strategies
        const savedContainer = document.getElementById('saved-strategies-container');
        // Clear saved strategies container
        savedContainer.innerHTML = '';
        
        // Add saved strategies
        this.savedStrategies.forEach(strategy => {
            const card = this.createStrategyCard(strategy);
            savedContainer.appendChild(card);
        });
        
        // If no saved strategies, show message
        if (this.savedStrategies.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.className = 'col-12';
            emptyMessage.innerHTML = `
                <div class="alert alert-info">
                    No saved strategies yet. Create new strategies to save them here.
                </div>
            `;
            savedContainer.appendChild(emptyMessage);
        }
    },
    
    // Create a strategy card
    createStrategyCard: function(strategy) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-4';
        
        // Create parameter list
        let parametersList = '';
        if (strategy.parameters) {
            parametersList += `<li>Risk per trade: ${strategy.parameters.risk}%</li>`;
            parametersList += `<li>Leverage: ${strategy.parameters.leverage}x</li>`;
            
            if (strategy.parameters.takeProfit) {
                parametersList += `<li>Take profit: ${strategy.parameters.takeProfit}%</li>`;
            }
            
            if (strategy.parameters.stopLoss) {
                parametersList += `<li>Stop loss: ${strategy.parameters.stopLoss}%</li>`;
            }
            
            // Type-specific parameters
            switch (strategy.type) {
                case 'rsi':
                    if (strategy.parameters.rsiPeriod) {
                        parametersList += `<li>RSI period: ${strategy.parameters.rsiPeriod}</li>`;
                    }
                    if (strategy.parameters.rsiOverbought && strategy.parameters.rsiOversold) {
                        parametersList += `<li>Levels: ${strategy.parameters.rsiOversold}/${strategy.parameters.rsiOverbought}</li>`;
                    }
                    break;
                    
                case 'ml':
                    if (strategy.parameters.trainingPeriod) {
                        parametersList += `<li>Training period: ${strategy.parameters.trainingPeriod} days</li>`;
                    }
                    if (strategy.parameters.predictionThreshold) {
                        parametersList += `<li>Prediction threshold: ${strategy.parameters.predictionThreshold}%</li>`;
                    }
                    break;
                    
                case 'mtf':
                    if (strategy.parameters.timeframes) {
                        parametersList += `<li>Timeframes: ${strategy.parameters.timeframes.join(', ')}</li>`;
                    }
                    if (strategy.parameters.primaryIndicator) {
                        parametersList += `<li>Primary indicator: ${strategy.parameters.primaryIndicator}</li>`;
                    }
                    break;
            }
        }
        
        // Get strategy description
        let strategyDescription = this.getStrategyDescription(strategy.type);
        
        // Create card HTML
        col.innerHTML = `
            <div class="card h-100" data-strategy-id="${strategy.id}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">${strategy.name}</h5>
                    <span class="badge ${strategy.active ? 'bg-success' : 'bg-secondary'}">${strategy.active ? 'Active' : 'Inactive'}</span>
                </div>
                <div class="card-body">
                    <p class="mb-2"><strong>Symbol:</strong> ${strategy.symbol}</p>
                    <p class="mb-2"><strong>Timeframe:</strong> ${strategy.timeframe}</p>
                    <p class="mb-2"><strong>Type:</strong> ${this.formatStrategyType(strategy.type)}</p>
                    <p class="mb-2"><strong>Parameters:</strong></p>
                    <ul class="small">
                        ${parametersList}
                    </ul>
                    <p class="small text-muted">${strategyDescription}</p>
                </div>
                <div class="card-footer d-flex justify-content-between">
                    ${strategy.active ? 
                      '<button class="btn btn-sm btn-outline-danger btn-deactivate">Deactivate</button>' : 
                      '<button class="btn btn-sm btn-outline-success btn-activate">Activate</button>'}
                    <button class="btn btn-sm btn-outline-secondary btn-edit">Edit</button>
                </div>
            </div>
        `;
        
        // Add event listeners
        const card = col.querySelector('.card');
        
        // Activate/Deactivate button
        if (strategy.active) {
            card.querySelector('.btn-deactivate').addEventListener('click', () => {
                this.deactivateStrategy(strategy.id);
            });
        } else {
            card.querySelector('.btn-activate').addEventListener('click', () => {
                this.activateStrategy(strategy.id);
            });
        }
        
        // Edit button
        card.querySelector('.btn-edit').addEventListener('click', () => {
            this.editStrategy(strategy.id);
        });
        
        return col;
    },
    
    // Format strategy type for display
    formatStrategyType: function(type) {
        const typeMap = {
            'rsi': 'RSI',
            'macd': 'MACD',
            'bbands': 'Bollinger Bands',
            'ema_cross': 'EMA Crossover',
            'ml': 'Machine Learning',
            'composite': 'Composite Indicator',
            'mtf': 'Multi-Timeframe',
            'liquidity': 'Liquidity Analysis'
        };
        
        return typeMap[type] || type;
    },
    
    // Get description for a strategy type
    getStrategyDescription: function(type) {
        const descriptions = {
            'rsi': 'Strategy uses Relative Strength Index to identify overbought and oversold conditions.',
            'macd': 'Strategy uses MACD crossover signals for trend detection and entry/exit points.',
            'bbands': 'Strategy uses Bollinger Bands to identify price extremes and mean reversion opportunities.',
            'ema_cross': 'Strategy uses EMA crossovers to identify trend changes and entry signals.',
            'ml': 'Strategy uses machine learning models with dynamic adjustments for market regimes.',
            'composite': 'Strategy combines multiple technical indicators for improved signal accuracy.',
            'mtf': 'Strategy analyzes multiple timeframes for confirmed signals and trend alignment.',
            'liquidity': 'Strategy identifies liquidity zones from order book data for precise entries and exits.'
        };
        
        return descriptions[type] || 'Custom trading strategy';
    },
    
    // Update strategy parameters based on selected type
    updateStrategyParameters: function() {
        const strategyType = document.getElementById('strategyType').value;
        const parametersContainer = document.getElementById('strategyParameters');
        
        // Update parameters HTML based on strategy type
        if (strategyParameters[strategyType]) {
            parametersContainer.innerHTML = `
                <h6>Strategy Parameters</h6>
                <div class="p-3 border rounded bg-secondary bg-opacity-10">
                    ${strategyParameters[strategyType]}
                </div>
            `;
        } else {
            parametersContainer.innerHTML = `
                <h6>Strategy Parameters</h6>
                <div class="p-3 border rounded bg-secondary bg-opacity-10">
                    <p class="text-muted small mb-0">
                        No specific parameters for this strategy type.
                    </p>
                </div>
            `;
        }
    },
    
    // Save strategy
    saveStrategy: function() {
        // Get form values
        const strategyName = document.getElementById('strategyName').value;
        const strategySymbol = document.getElementById('strategySymbol').value;
        const strategyTimeframe = document.getElementById('strategyTimeframe').value;
        const strategyType = document.getElementById('strategyType').value;
        const strategyRisk = parseFloat(document.getElementById('strategyRisk').value);
        const strategyLeverage = parseInt(document.getElementById('strategyLeverage').value);
        const activateStrategy = document.getElementById('activateStrategy').checked;
        
        // Validate inputs
        if (!strategyName || !strategySymbol || !strategyTimeframe || !strategyType) {
            alert('Please fill in all required fields');
            return;
        }
        
        // Get strategy-specific parameters
        const parameters = {
            risk: strategyRisk,
            leverage: strategyLeverage
        };
        
        // Add type-specific parameters
        switch (strategyType) {
            case 'rsi':
                parameters.rsiPeriod = parseInt(document.getElementById('rsiPeriod').value);
                parameters.rsiOverbought = parseInt(document.getElementById('rsiOverbought').value);
                parameters.rsiOversold = parseInt(document.getElementById('rsiOversold').value);
                parameters.takeProfit = parseFloat(document.getElementById('rsiTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('rsiStopLoss').value);
                parameters.useVolume = document.getElementById('rsiUseVolume').checked;
                break;
                
            case 'macd':
                parameters.macdFast = parseInt(document.getElementById('macdFast').value);
                parameters.macdSlow = parseInt(document.getElementById('macdSlow').value);
                parameters.macdSignal = parseInt(document.getElementById('macdSignal').value);
                parameters.takeProfit = parseFloat(document.getElementById('macdTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('macdStopLoss').value);
                parameters.useHistogram = document.getElementById('macdUseHistogram').checked;
                break;
                
            case 'bbands':
                parameters.bbandsPeriod = parseInt(document.getElementById('bbandsPeriod').value);
                parameters.bbandsStdDev = parseFloat(document.getElementById('bbandsStdDev').value);
                parameters.bbandsSignalStrength = parseInt(document.getElementById('bbandsSignalStrength').value);
                parameters.takeProfit = parseFloat(document.getElementById('bbandsTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('bbandsStopLoss').value);
                parameters.useMidExit = document.getElementById('bbandsUseMidExit').checked;
                break;
                
            case 'ema_cross':
                parameters.emaFast = parseInt(document.getElementById('emaFast').value);
                parameters.emaSlow = parseInt(document.getElementById('emaSlow').value);
                parameters.takeProfit = parseFloat(document.getElementById('emaTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('emaStopLoss').value);
                parameters.useVolume = document.getElementById('emaUseVolume').checked;
                break;
                
            case 'ml':
                parameters.trainingPeriod = parseInt(document.getElementById('mlTrainingPeriod').value);
                parameters.predictionThreshold = parseInt(document.getElementById('mlPredictionThreshold').value);
                parameters.takeProfit = parseFloat(document.getElementById('mlTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('mlStopLoss').value);
                parameters.useEnsemble = document.getElementById('mlUseEnsemble').checked;
                parameters.models = [];
                if (document.getElementById('mlUseRandomForest').checked) parameters.models.push('randomForest');
                if (document.getElementById('mlUseGradientBoosting').checked) parameters.models.push('gradientBoosting');
                if (document.getElementById('mlUseSVM').checked) parameters.models.push('svm');
                break;
                
            case 'composite':
                parameters.indicators = [];
                if (document.getElementById('compUseRSI').checked) parameters.indicators.push('rsi');
                if (document.getElementById('compUseMACD').checked) parameters.indicators.push('macd');
                if (document.getElementById('compUseEMA').checked) parameters.indicators.push('ema_cross');
                if (document.getElementById('compUseBB').checked) parameters.indicators.push('bbands');
                if (document.getElementById('compUseVol').checked) parameters.indicators.push('volume_trend');
                if (document.getElementById('compUseADX').checked) parameters.indicators.push('adx');
                parameters.signalThreshold = parseFloat(document.getElementById('compSignalThreshold').value);
                parameters.lookback = parseInt(document.getElementById('compLookback').value);
                parameters.takeProfit = parseFloat(document.getElementById('compTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('compStopLoss').value);
                parameters.dynamicWeights = document.getElementById('compDynamicWeights').checked;
                break;
                
            case 'mtf':
                parameters.timeframes = [];
                if (document.getElementById('mtfUse15m').checked) parameters.timeframes.push('15m');
                if (document.getElementById('mtfUse1h').checked) parameters.timeframes.push('1h');
                if (document.getElementById('mtfUse4h').checked) parameters.timeframes.push('4h');
                if (document.getElementById('mtfUse1d').checked) parameters.timeframes.push('1d');
                parameters.primaryIndicator = document.getElementById('mtfPrimaryIndicator').value;
                parameters.confirmationTimeframe = document.getElementById('mtfConfirmationTF').value;
                parameters.takeProfit = parseFloat(document.getElementById('mtfTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('mtfStopLoss').value);
                parameters.dynamicWeights = document.getElementById('mtfDynamicWeights').checked;
                break;
                
            case 'liquidity':
                parameters.orderbookDepth = parseInt(document.getElementById('liqOrderbookDepth').value);
                parameters.refreshRate = parseInt(document.getElementById('liqRefreshRate').value);
                parameters.minimumStrength = parseInt(document.getElementById('liqMinimumStrength').value);
                parameters.priceRange = parseFloat(document.getElementById('liqPriceRange').value);
                parameters.takeProfit = parseFloat(document.getElementById('liqTakeProfit').value);
                parameters.stopLoss = parseFloat(document.getElementById('liqStopLoss').value);
                parameters.tradeType = document.getElementById('liqTradeType').value;
                break;
        }
        
        // Create strategy object
        const strategy = {
            id: 'strategy-' + Date.now(), // Generate a unique ID
            name: strategyName,
            symbol: strategySymbol,
            timeframe: strategyTimeframe,
            type: strategyType,
            active: activateStrategy,
            parameters: parameters
        };
        
        // In a real implementation, this would send data to the server
        console.log('Saving strategy:', strategy);
        
        // Add to appropriate list
        if (activateStrategy) {
            this.activeStrategies.push(strategy);
        } else {
            this.savedStrategies.push(strategy);
        }
        
        // Render strategies
        this.renderStrategies();
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addStrategyModal'));
        modal.hide();
        
        // Reset form
        document.getElementById('newStrategyForm').reset();
        
        // Show success message
        alert('Strategy saved successfully!');
    },
    
    // Activate a strategy
    activateStrategy: function(strategyId) {
        // Find the strategy
        const strategyIndex = this.savedStrategies.findIndex(s => s.id === strategyId);
        if (strategyIndex === -1) return;
        
        // Get the strategy
        const strategy = this.savedStrategies[strategyIndex];
        
        // Update strategy status
        strategy.active = true;
        
        // Move to active strategies
        this.activeStrategies.push(strategy);
        this.savedStrategies.splice(strategyIndex, 1);
        
        // Render strategies
        this.renderStrategies();
        
        // In a real implementation, this would update the server
        console.log('Activated strategy:', strategy);
    },
    
    // Deactivate a strategy
    deactivateStrategy: function(strategyId) {
        // Find the strategy
        const strategyIndex = this.activeStrategies.findIndex(s => s.id === strategyId);
        if (strategyIndex === -1) return;
        
        // Get the strategy
        const strategy = this.activeStrategies[strategyIndex];
        
        // Update strategy status
        strategy.active = false;
        
        // Move to saved strategies
        this.savedStrategies.push(strategy);
        this.activeStrategies.splice(strategyIndex, 1);
        
        // Render strategies
        this.renderStrategies();
        
        // In a real implementation, this would update the server
        console.log('Deactivated strategy:', strategy);
    },
    
    // Edit a strategy
    editStrategy: function(strategyId) {
        // Find the strategy in active strategies
        let strategy = this.activeStrategies.find(s => s.id === strategyId);
        let isActive = true;
        
        // If not found in active strategies, check saved strategies
        if (!strategy) {
            strategy = this.savedStrategies.find(s => s.id === strategyId);
            isActive = false;
        }
        
        if (!strategy) return;
        
        // TODO: Implement strategy editing functionality
        alert('Strategy editing will be implemented in a future update.');
    },
    
    // Load a strategy template
    loadTemplate: function(templateName) {
        // Set strategy type in form
        document.getElementById('strategyType').value = templateName;
        
        // Update parameters form
        this.updateStrategyParameters();
        
        // Set default strategy name based on template
        const nameMap = {
            'rsi': 'RSI Strategy',
            'macd': 'MACD Strategy',
            'bbands': 'Bollinger Bands Strategy',
            'ema_cross': 'EMA Crossover Strategy',
            'ml': 'ML Strategy',
            'composite': 'Composite Indicator Strategy',
            'mtf': 'Multi-Timeframe Strategy',
            'liquidity': 'Liquidity Analysis Strategy'
        };
        
        document.getElementById('strategyName').value = nameMap[templateName] || 'New Strategy';
        
        // Open add strategy modal
        const modal = new bootstrap.Modal(document.getElementById('addStrategyModal'));
        modal.show();
    }
};

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize strategies
    strategyManager.init();
    
    // Setup Socket.IO for bot status updates
    socket = io();
    
    // Update bot status badge
    socket.on('bot_status', function(data) {
        const statusBadge = document.getElementById('bot-status-badge');
        statusBadge.textContent = data.running ? 'Running' : 'Stopped';
        statusBadge.className = data.running ? 'badge bg-success me-2' : 'badge bg-danger me-2';
        
        // Update button
        const button = document.getElementById('toggle-bot');
        if (data.running) {
            button.textContent = 'Stop Bot';
            button.className = 'btn btn-sm btn-outline-danger';
        } else {
            button.textContent = 'Start Bot';
            button.className = 'btn btn-sm btn-outline-success';
        }
    });
    
    // Toggle bot on/off
    document.getElementById('toggle-bot').addEventListener('click', function() {
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
        .catch(error => console.error('Error:', error));
    });
});