// Trades.js - JavaScript for the Trade History page

// Trade history manager
const tradeHistoryManager = {
    // Initialize the component
    init: function() {
        // Add event listeners
        document.getElementById('apply-filters').addEventListener('click', this.applyFilters.bind(this));
        document.getElementById('reset-filters').addEventListener('click', this.resetFilters.bind(this));
        document.getElementById('export-trades').addEventListener('click', this.exportTrades);
        
        // Add event listeners to trade view buttons
        const viewButtons = document.querySelectorAll('.view-trade');
        viewButtons.forEach(button => {
            button.addEventListener('click', this.showTradeDetails.bind(this));
        });
        
        // Setup toggle bot button
        document.getElementById('toggle-bot').addEventListener('click', this.toggleBot);
        
        // Update bot status badge and toggle button
        this.updateBotStatus();
        
        // Create charts
        this.createEquityChart();
        this.createSymbolsChart();
        this.createStrategiesChart();
    },
    
    // Apply filters to trade table
    applyFilters: function() {
        // In a real implementation, this would fetch filtered data from the server
        console.log('Filters applied:');
        console.log('Date range:', document.getElementById('date-range').value);
        console.log('Symbol:', document.getElementById('symbol-filter').value);
        console.log('Strategy:', document.getElementById('strategy-filter').value);
        console.log('Result:', document.getElementById('result-filter').value);
        
        // Show a temporary message about filtering
        alert('Filtering applied. In a real implementation, this would update the trade table.');
    },
    
    // Reset filters to default values
    resetFilters: function() {
        document.getElementById('date-range').value = '30d';
        document.getElementById('symbol-filter').value = 'all';
        document.getElementById('strategy-filter').value = 'all';
        document.getElementById('result-filter').value = 'all';
        
        // Apply the reset filters
        this.applyFilters();
    },
    
    // Export trades to CSV
    exportTrades: function() {
        // In a real implementation, this would generate and download a CSV file
        alert('Trade data export functionality will be implemented in a future update.');
    },
    
    // Show trade details modal
    showTradeDetails: function(event) {
        const tradeId = event.target.getAttribute('data-trade-id');
        
        // In a real implementation, this would fetch trade details from the server
        console.log('Showing details for trade ID:', tradeId);
        
        // For demo purposes, we'll show the modal with sample data
        const tradeModal = new bootstrap.Modal(document.getElementById('tradeDetailsModal'));
        
        // Set the modal title
        document.getElementById('tradeDetailsModalLabel').textContent = `Trade #${tradeId} Details`;
        
        // Show the modal
        tradeModal.show();
        
        // Create the trade chart
        this.createTradeChart();
    },
    
    // Create equity curve chart
    createEquityChart: function() {
        const ctx = document.getElementById('equity-chart').getContext('2d');
        
        // Generate sample equity curve data
        const labels = [];
        const equityData = [];
        const initialBalance = 10000;
        
        // Generate dates and equity values for the last 30 days
        const today = new Date();
        let currentBalance = initialBalance;
        
        for (let i = 30; i >= 0; i--) {
            const date = new Date();
            date.setDate(today.getDate() - i);
            labels.push(date.toLocaleDateString());
            
            // Generate equity value with some randomness but trending upward
            const changePercent = (Math.random() - 0.3) * 1.5; // Bias toward positive
            currentBalance *= (1 + changePercent / 100);
            equityData.push(currentBalance);
        }
        
        // Create chart
        if (window.equityChart) {
            window.equityChart.destroy();
        }
        
        window.equityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Account Balance',
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
    
    // Create symbols distribution chart
    createSymbolsChart: function() {
        const ctx = document.getElementById('symbols-chart').getContext('2d');
        
        // Sample data
        const data = {
            labels: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT'],
            datasets: [{
                label: 'Number of Trades',
                data: [25, 18, 12, 8, 5],
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }]
        };
        
        // Create chart
        if (window.symbolsChart) {
            window.symbolsChart.destroy();
        }
        
        window.symbolsChart = new Chart(ctx, {
            type: 'pie',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    },
    
    // Create strategies win/loss chart
    createStrategiesChart: function() {
        const ctx = document.getElementById('strategies-chart').getContext('2d');
        
        // Sample data
        const data = {
            labels: ['RSI', 'MACD', 'ML', 'Composite'],
            datasets: [
                {
                    label: 'Winning Trades',
                    data: [10, 8, 12, 4],
                    backgroundColor: 'rgba(46, 204, 113, 0.7)',
                    borderColor: 'rgba(46, 204, 113, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Losing Trades',
                    data: [4, 3, 6, 1],
                    backgroundColor: 'rgba(231, 76, 60, 0.7)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 1
                }
            ]
        };
        
        // Create chart
        if (window.strategiesChart) {
            window.strategiesChart.destroy();
        }
        
        window.strategiesChart = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: false
                    },
                    y: {
                        stacked: false,
                        beginAtZero: true
                    }
                }
            }
        });
    },
    
    // Create trade detail chart
    createTradeChart: function() {
        const ctx = document.getElementById('trade-chart').getContext('2d');
        
        // Generate sample price data
        const labels = [];
        const priceData = [];
        
        // Generate 24 hours of hourly data for the trade
        const entryDate = new Date('2025-02-26T14:32:15');
        const exitDate = new Date('2025-02-26T18:55:42');
        
        // Start 12 hours before entry
        const startDate = new Date(entryDate);
        startDate.setHours(startDate.getHours() - 12);
        
        // End 12 hours after exit
        const endDate = new Date(exitDate);
        endDate.setHours(endDate.getHours() + 12);
        
        // Generate data points
        let currentPrice = 82000; // Starting price
        const hourStep = 3600000; // 1 hour in milliseconds
        
        for (let time = startDate.getTime(); time <= endDate.getTime(); time += hourStep) {
            const date = new Date(time);
            labels.push(date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            
            // Add some randomness to price
            const changePercent = (Math.random() - 0.4) * 0.5; // Slight upward bias
            currentPrice *= (1 + changePercent / 100);
            
            // Ensure we hit entry and exit prices at the right times
            if (Math.abs(time - entryDate.getTime()) < hourStep / 2) {
                currentPrice = 82456.12; // Entry price
            } else if (Math.abs(time - exitDate.getTime()) < hourStep / 2) {
                currentPrice = 84210.35; // Exit price
            }
            
            priceData.push(currentPrice);
        }
        
        // Create chart
        if (window.tradeChart) {
            window.tradeChart.destroy();
        }
        
        window.tradeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'BTC/USDT Price',
                    data: priceData,
                    borderColor: '#11cdef',
                    backgroundColor: 'rgba(17, 205, 239, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    annotation: {
                        annotations: {
                            entryLine: {
                                type: 'line',
                                xMin: labels[12], // Entry point
                                xMax: labels[12],
                                borderColor: 'green',
                                borderWidth: 2,
                                label: {
                                    content: 'Entry',
                                    enabled: true,
                                    position: 'top'
                                }
                            },
                            exitLine: {
                                type: 'line',
                                xMin: labels[16], // Exit point
                                xMax: labels[16],
                                borderColor: 'red',
                                borderWidth: 2,
                                label: {
                                    content: 'Exit',
                                    enabled: true,
                                    position: 'top'
                                }
                            }
                        }
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
            tradeHistoryManager.updateBotStatus();
        })
        .catch(error => console.error('Error:', error));
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize trade history manager
    tradeHistoryManager.init();
});