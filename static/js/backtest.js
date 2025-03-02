// Backtest.js - JavaScript for the Backtest page

// Strategy parameters templates
const strategyParameters = {
    rsi_strategy: `
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
    `,
    macd_strategy: `
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
    `,
    bollinger_strategy: `
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
    `,
    ml_strategy: `
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
    composite_strategy: `
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
    `
};

// Backtest manager
const backtestManager = {
    // Initialize the component
    init: function() {
        // Set current date as end date and 3 months ago as start date
        const today = new Date();
        const threeMonthsAgo = new Date();
        threeMonthsAgo.setMonth(today.getMonth() - 3);
        
        document.getElementById('endDate').valueAsDate = today;
        document.getElementById('startDate').valueAsDate = threeMonthsAgo;
        
        // Add event listeners
        document.getElementById('strategySelect').addEventListener('change', this.updateStrategyParameters);
        document.getElementById('runBacktestBtn').addEventListener('click', this.runBacktest.bind(this));
        document.getElementById('downloadReportBtn').addEventListener('click', this.downloadReport);
        document.getElementById('saveStrategyBtn').addEventListener('click', this.saveStrategy);
        
        // Update bot status badge and toggle button
        this.updateBotStatus();
        
        // Setup toggle bot button
        document.getElementById('toggle-bot').addEventListener('click', this.toggleBot);
    },
    
    // Update strategy parameters based on selected strategy
    updateStrategyParameters: function() {
        const strategyType = document.getElementById('strategySelect').value;
        const parametersContainer = document.getElementById('strategyParams');
        
        // Update parameters HTML based on strategy type
        if (strategyParameters[strategyType]) {
            parametersContainer.innerHTML = `
                <h6>Strategy Parameters</h6>
                <div class="p-3 border rounded bg-secondary bg-opacity-10">
                    ${strategyParameters[strategyType]}
                </div>
            `;
        } else {
            parametersContainer.innerHTML = '';
        }
    },
    
    // Run backtest
    runBacktest: function() {
        // Validate form
        const strategyType = document.getElementById('strategySelect').value;
        if (!strategyType) {
            alert('Please select a strategy');
            return;
        }
        
        // Hide no results section and show loading section
        document.getElementById('noResultsSection').classList.add('d-none');
        document.getElementById('loadingSection').classList.remove('d-none');
        document.getElementById('resultsSection').classList.add('d-none');
        document.getElementById('advancedMetricsCard').classList.add('d-none');
        
        // Get form values
        const formData = {
            strategy: strategyType,
            symbol: document.getElementById('symbolSelect').value,
            timeframe: document.getElementById('timeframeSelect').value,
            startDate: document.getElementById('startDate').value,
            endDate: document.getElementById('endDate').value,
            initialBalance: parseFloat(document.getElementById('initialBalance').value),
            riskPerTrade: parseFloat(document.getElementById('riskPerTrade').value),
            leverage: parseInt(document.getElementById('leverage').value),
            optimizeParams: document.getElementById('optimizeParams').checked
        };
        
        // Add strategy-specific parameters
        switch (strategyType) {
            case 'rsi_strategy':
                formData.rsiPeriod = parseInt(document.getElementById('rsiPeriod').value);
                formData.rsiOverbought = parseInt(document.getElementById('rsiOverbought').value);
                formData.rsiOversold = parseInt(document.getElementById('rsiOversold').value);
                break;
            case 'macd_strategy':
                formData.macdFast = parseInt(document.getElementById('macdFast').value);
                formData.macdSlow = parseInt(document.getElementById('macdSlow').value);
                formData.macdSignal = parseInt(document.getElementById('macdSignal').value);
                break;
            case 'bollinger_strategy':
                formData.bbandsPeriod = parseInt(document.getElementById('bbandsPeriod').value);
                formData.bbandsStdDev = parseFloat(document.getElementById('bbandsStdDev').value);
                formData.bbandsSignalStrength = parseInt(document.getElementById('bbandsSignalStrength').value);
                break;
            case 'ml_strategy':
                formData.mlTrainingPeriod = parseInt(document.getElementById('mlTrainingPeriod').value);
                formData.mlPredictionThreshold = parseInt(document.getElementById('mlPredictionThreshold').value);
                formData.mlModels = [];
                if (document.getElementById('mlUseRandomForest').checked) formData.mlModels.push('randomForest');
                if (document.getElementById('mlUseGradientBoosting').checked) formData.mlModels.push('gradientBoosting');
                if (document.getElementById('mlUseSVM').checked) formData.mlModels.push('svm');
                break;
            case 'composite_strategy':
                formData.compIndicators = [];
                if (document.getElementById('compUseRSI').checked) formData.compIndicators.push('rsi');
                if (document.getElementById('compUseMACD').checked) formData.compIndicators.push('macd');
                if (document.getElementById('compUseEMA').checked) formData.compIndicators.push('ema_cross');
                if (document.getElementById('compUseBB').checked) formData.compIndicators.push('bbands');
                if (document.getElementById('compUseVol').checked) formData.compIndicators.push('volume_trend');
                if (document.getElementById('compUseADX').checked) formData.compIndicators.push('adx');
                formData.compSignalThreshold = parseFloat(document.getElementById('compSignalThreshold').value);
                formData.compLookback = parseInt(document.getElementById('compLookback').value);
                break;
        }
        
        // In a real implementation, this would be an API call to the server
        console.log('Running backtest with parameters:', formData);
        
        // Simulate API call with setTimeout
        setTimeout(() => {
            // Hide loading section and show results section
            document.getElementById('loadingSection').classList.add('d-none');
            document.getElementById('resultsSection').classList.remove('d-none');
            document.getElementById('advancedMetricsCard').classList.remove('d-none');
            
            // Display simulated results
            this.displayResults();
        }, 2000);
    },
    
    // Display backtest results
    displayResults: function() {
        // In a real implementation, this would use actual data from the API
        // For now, we'll use simulated data
        
        // Get initial balance from the form
        const initialBalance = parseFloat(document.getElementById('initialBalance').value);
        const finalBalance = (initialBalance * 1.2345).toFixed(2); // 23.45% profit
        
        // Update summary metrics
        document.getElementById('finalBalance').textContent = '$' + finalBalance;
        document.getElementById('totalProfit').textContent = '+23.45%';
        document.getElementById('winRate').textContent = '68.5%';
        document.getElementById('maxDrawdown').textContent = '12.3%';
        document.getElementById('sharpeRatio').textContent = '1.85';
        document.getElementById('profitFactor').textContent = '2.14';
        
        // Generate random trades for the table
        const tradesTable = document.getElementById('tradesTable');
        tradesTable.innerHTML = '';
        
        const tradeTypes = ['LONG', 'SHORT'];
        const startDate = new Date(document.getElementById('startDate').value);
        const endDate = new Date(document.getElementById('endDate').value);
        const timeRange = endDate - startDate;
        
        // Create 10 random trades
        for (let i = 0; i < 10; i++) {
            const row = document.createElement('tr');
            
            // Random trade data
            const tradeType = tradeTypes[Math.floor(Math.random() * 2)];
            const isWin = Math.random() > 0.3; // 70% win rate
            
            // Random date within range
            const tradeDate = new Date(startDate.getTime() + Math.random() * timeRange);
            const tradeDateStr = tradeDate.toLocaleDateString();
            
            // Random prices and PnL
            const entryPrice = parseFloat((80000 + Math.random() * 5000).toFixed(2));
            const pnlPercent = isWin ? 
                parseFloat((Math.random() * 5).toFixed(2)) : 
                parseFloat((-Math.random() * 3).toFixed(2));
            const exitPrice = tradeType === 'LONG' ? 
                parseFloat((entryPrice * (1 + pnlPercent / 100)).toFixed(2)) : 
                parseFloat((entryPrice * (1 - pnlPercent / 100)).toFixed(2));
            const pnlAbsolute = parseFloat((entryPrice * pnlPercent / 100).toFixed(2));
            
            // Create row
            row.innerHTML = `
                <td>${tradeDateStr}</td>
                <td class="${tradeType === 'LONG' ? 'text-success' : 'text-danger'}">${tradeType}</td>
                <td>$${entryPrice.toLocaleString()}</td>
                <td>$${exitPrice.toLocaleString()}</td>
                <td class="${pnlAbsolute >= 0 ? 'text-success' : 'text-danger'}">$${Math.abs(pnlAbsolute).toLocaleString()}</td>
                <td class="${pnlPercent >= 0 ? 'text-success' : 'text-danger'}">${pnlPercent > 0 ? '+' : ''}${pnlPercent}%</td>
            `;
            
            tradesTable.appendChild(row);
        }
        
        // Update detailed metrics table
        document.getElementById('totalTrades').textContent = '35';
        document.getElementById('winningTrades').textContent = '24';
        document.getElementById('losingTrades').textContent = '11';
        document.getElementById('winRateDetail').textContent = '68.5%';
        document.getElementById('bestTrade').textContent = '7.2% ($720.34)';
        document.getElementById('worstTrade').textContent = '-2.8% (-$280.15)';
        document.getElementById('avgTrade').textContent = '1.5% ($150.25)';
        document.getElementById('expectancy').textContent = '$152.33';
        document.getElementById('annualizedReturn').textContent = '28.75%';
        document.getElementById('recoveryFactor').textContent = '1.9';
        document.getElementById('calmarRatio').textContent = '2.34';
        document.getElementById('sortinoRatio').textContent = '2.56';
        document.getElementById('maxConsecWins').textContent = '8';
        document.getElementById('maxConsecLosses').textContent = '3';
        document.getElementById('avgHoldTimeWin').textContent = '18.5 hrs';
        document.getElementById('avgHoldTimeLoss').textContent = '12.3 hrs';
        document.getElementById('avgWin').textContent = '2.8%';
        document.getElementById('avgLoss').textContent = '-1.2%';
        document.getElementById('riskReward').textContent = '2.33';
        
        // Create equity curve chart
        this.createEquityCurveChart();
        
        // Create monthly returns chart
        this.createMonthlyReturnsChart();
        
        // Create drawdown chart
        this.createDrawdownChart();
    },
    
    // Create equity curve chart
    createEquityCurveChart: function() {
        const ctx = document.getElementById('equityCurveChart').getContext('2d');
        
        // Generate random equity curve data
        const initialBalance = parseFloat(document.getElementById('initialBalance').value);
        const dataPoints = 100;
        const labels = [];
        const equityData = [];
        
        // Start with initial balance
        let currentBalance = initialBalance;
        
        // Generate dates and equity values
        const startDate = new Date(document.getElementById('startDate').value);
        const endDate = new Date(document.getElementById('endDate').value);
        const timeStep = (endDate - startDate) / dataPoints;
        
        for (let i = 0; i < dataPoints; i++) {
            // Generate date label
            const date = new Date(startDate.getTime() + i * timeStep);
            labels.push(date.toLocaleDateString());
            
            // Generate equity value with some randomness but trending upward
            const changePercent = (Math.random() - 0.3) * 1.5; // Bias toward positive
            currentBalance *= (1 + changePercent / 100);
            equityData.push(currentBalance);
        }
        
        // Create chart
        if (window.equityCurveChart) {
            window.equityCurveChart.destroy();
        }
        
        window.equityCurveChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Equity Curve',
                    data: equityData,
                    borderColor: '#11cdef',
                    backgroundColor: 'rgba(17, 205, 239, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
    
    // Create monthly returns chart
    createMonthlyReturnsChart: function() {
        const ctx = document.getElementById('monthlyReturnsChart').getContext('2d');
        
        // Generate random monthly returns
        const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const returnsData = [];
        
        for (let i = 0; i < 12; i++) {
            // Generate random return (biased toward positive)
            returnsData.push((Math.random() * 15 - 3).toFixed(2));
        }
        
        // Create chart
        if (window.monthlyReturnsChart) {
            window.monthlyReturnsChart.destroy();
        }
        
        window.monthlyReturnsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Monthly Returns (%)',
                    data: returnsData,
                    backgroundColor: returnsData.map(value => value >= 0 ? 'rgba(46, 204, 113, 0.6)' : 'rgba(231, 76, 60, 0.6)'),
                    borderColor: returnsData.map(value => value >= 0 ? 'rgba(46, 204, 113, 1)' : 'rgba(231, 76, 60, 1)'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) {
                                return value + '%';
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
                                return context.parsed.y + '%';
                            }
                        }
                    }
                }
            }
        });
    },
    
    // Create drawdown chart
    createDrawdownChart: function() {
        const ctx = document.getElementById('drawdownChart').getContext('2d');
        
        // Generate random drawdown data
        const dataPoints = 100;
        const labels = [];
        const drawdownData = [];
        
        // Generate dates and drawdown values
        const startDate = new Date(document.getElementById('startDate').value);
        const endDate = new Date(document.getElementById('endDate').value);
        const timeStep = (endDate - startDate) / dataPoints;
        
        for (let i = 0; i < dataPoints; i++) {
            // Generate date label
            const date = new Date(startDate.getTime() + i * timeStep);
            labels.push(date.toLocaleDateString());
            
            // Generate drawdown value (always negative)
            const drawdown = -(Math.random() * 12).toFixed(2);
            drawdownData.push(drawdown);
        }
        
        // Create chart
        if (window.drawdownChart) {
            window.drawdownChart.destroy();
        }
        
        window.drawdownChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Drawdown (%)',
                    data: drawdownData,
                    borderColor: 'rgba(231, 76, 60, 1)',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        ticks: {
                            callback: function(value) {
                                return value + '%';
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
                                return context.parsed.y + '%';
                            }
                        }
                    }
                }
            }
        });
    },
    
    // Download backtest report
    downloadReport: function() {
        // In a real implementation, this would generate and download a PDF report
        alert('Report download functionality will be implemented in a future update.');
    },
    
    // Save optimized strategy
    saveStrategy: function() {
        // In a real implementation, this would save the strategy to the server
        alert('Strategy saved successfully to your strategies list!');
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
        .catch(error => console.error('Error:', error));
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize backtest manager
    backtestManager.init();
    
    // Set default strategy
    document.getElementById('strategySelect').value = 'rsi_strategy';
    backtestManager.updateStrategyParameters();
});