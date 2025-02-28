/**
 * Trading Bot Charts
 * Handles chart creation and updates for the trading bot application
 */

class TradingCharts {
  constructor() {
    this.priceChart = null;
    this.indicatorCharts = {};
    this.backtestChart = null;
    this.equityChart = null;
    this.chartData = {
      ohlc: [],
      volume: [],
      indicators: {
        rsi: [],
        macd: [],
        macdSignal: [],
        macdHistogram: [],
        ema9: [],
        ema21: [],
        sma20: [],
        sma50: [],
        bbUpper: [],
        bbMiddle: [],
        bbLower: []
      }
    };
    this.lastPrice = null;
    this.priceDirection = null;
  }

  // Initialize the main price chart
  initPriceChart(containerId, data = null) {
    const container = document.getElementById(containerId);
    
    if (!container) {
      console.error(`Container with ID "${containerId}" not found`);
      return;
    }
    
    // Initialize chart data if needed
    if (!this.chartData) {
      this.chartData = { 
        ohlc: [], 
        volume: [],
        timestamps: []
      };
      
      // Generate sample data if none provided
      if (!data) {
        console.log('No initial price data, generating sample data');
        data = this._generateSampleData();
      }
    }
    
    // If we have data, process it
    if (data) {
      console.log(`Processing ${data.length} data points for chart`);
      this.updateChartData(data);
    }
    
    // Create the main price chart
    this.priceChart = new Chart(container.getContext('2d'), {
      type: 'candlestick',
      data: {
        datasets: [{
          label: 'BTCUSDT',
          data: this.chartData.ohlc,
          color: {
            up: 'rgba(38, 166, 154, 1)',
            down: 'rgba(239, 83, 80, 1)',
            unchanged: 'rgba(156, 156, 156, 1)',
          }
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour',
              displayFormats: {
                hour: 'MMM d, HH:mm'
              }
            },
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            },
            ticks: {
              source: 'data',
              autoSkip: true,
              maxRotation: 0
            }
          },
          y: {
            position: 'right',
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: function(context) {
                const point = context.raw;
                return [
                  `Open: ${point.o}`,
                  `High: ${point.h}`,
                  `Low: ${point.l}`,
                  `Close: ${point.c}`
                ];
              }
            }
          },
          legend: {
            display: false
          }
        }
      }
    });
    
    return this.priceChart;
  }
  
  // Initialize RSI chart
  initRSIChart(containerId) {
    const container = document.getElementById(containerId);
    
    if (!container) {
      console.error(`Container with ID "${containerId}" not found`);
      return;
    }
    
    this.indicatorCharts.rsi = new Chart(container.getContext('2d'), {
      type: 'line',
      data: {
        datasets: [{
          label: 'RSI',
          data: this.chartData.indicators.rsi,
          borderColor: 'rgba(255, 99, 132, 1)',
          borderWidth: 1,
          pointRadius: 0,
          fill: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour'
            },
            display: false
          },
          y: {
            min: 0,
            max: 100,
            position: 'right',
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          }
        },
        plugins: {
          annotation: {
            annotations: {
              overbought: {
                type: 'line',
                yMin: 70,
                yMax: 70,
                borderColor: 'rgba(255, 0, 0, 0.5)',
                borderWidth: 1,
                borderDash: [5, 5]
              },
              oversold: {
                type: 'line',
                yMin: 30,
                yMax: 30,
                borderColor: 'rgba(0, 255, 0, 0.5)',
                borderWidth: 1,
                borderDash: [5, 5]
              }
            }
          }
        }
      }
    });
    
    return this.indicatorCharts.rsi;
  }
  
  // Initialize MACD chart
  initMACDChart(containerId) {
    const container = document.getElementById(containerId);
    
    if (!container) {
      console.error(`Container with ID "${containerId}" not found`);
      return;
    }
    
    this.indicatorCharts.macd = new Chart(container.getContext('2d'), {
      type: 'line',
      data: {
        datasets: [{
          label: 'MACD',
          data: this.chartData.indicators.macd,
          borderColor: 'rgba(33, 150, 243, 1)',
          borderWidth: 1,
          pointRadius: 0,
          fill: false
        }, {
          label: 'Signal',
          data: this.chartData.indicators.macdSignal,
          borderColor: 'rgba(255, 152, 0, 1)',
          borderWidth: 1,
          pointRadius: 0,
          fill: false
        }, {
          label: 'Histogram',
          data: this.chartData.indicators.macdHistogram,
          type: 'bar',
          backgroundColor: context => {
            const value = context.raw.y;
            return value >= 0 ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)';
          },
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'hour'
            },
            display: false
          },
          y: {
            position: 'right',
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        }
      }
    });
    
    return this.indicatorCharts.macd;
  }
  
  // Initialize Backtest chart
  initBacktestChart(containerId, backtestResults) {
    const container = document.getElementById(containerId);
    
    if (!container) {
      console.error(`Container with ID "${containerId}" not found`);
      return;
    }
    
    // Parse backtest data
    const dates = backtestResults.results.map(item => new Date(item.date));
    const prices = backtestResults.results.map(item => item.close);
    const equity = backtestResults.results.map(item => item.equity);
    const signals = backtestResults.results.map(item => item.signal);
    
    // Extract buy and sell signals
    const buySignals = [];
    const sellSignals = [];
    
    for (let i = 0; i < dates.length; i++) {
      if (signals[i] === 1) {
        buySignals.push({
          x: dates[i],
          y: prices[i]
        });
      } else if (signals[i] === -1) {
        sellSignals.push({
          x: dates[i],
          y: prices[i]
        });
      }
    }
    
    this.backtestChart = new Chart(container.getContext('2d'), {
      type: 'line',
      data: {
        datasets: [{
          label: 'Price',
          data: dates.map((date, i) => ({ x: date, y: prices[i] })),
          borderColor: 'rgba(151, 187, 205, 1)',
          backgroundColor: 'rgba(151, 187, 205, 0.1)',
          borderWidth: 1,
          pointRadius: 0,
          fill: true,
          yAxisID: 'y'
        }, {
          label: 'Equity',
          data: dates.map((date, i) => ({ x: date, y: equity[i] })),
          borderColor: 'rgba(255, 193, 7, 1)',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
          yAxisID: 'y1'
        }, {
          label: 'Buy Signals',
          data: buySignals,
          borderColor: 'rgba(38, 166, 154, 1)',
          backgroundColor: 'rgba(38, 166, 154, 1)',
          borderWidth: 0,
          pointRadius: 5,
          pointStyle: 'triangle',
          fill: false,
          yAxisID: 'y',
          showLine: false
        }, {
          label: 'Sell Signals',
          data: sellSignals,
          borderColor: 'rgba(239, 83, 80, 1)',
          backgroundColor: 'rgba(239, 83, 80, 1)',
          borderWidth: 0,
          pointRadius: 5,
          pointStyle: 'triangle',
          rotation: 180,
          fill: false,
          yAxisID: 'y',
          showLine: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day',
              displayFormats: {
                day: 'MMM d'
              }
            },
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          },
          y: {
            type: 'linear',
            position: 'left',
            title: {
              display: true,
              text: 'Price'
            },
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          },
          y1: {
            type: 'linear',
            position: 'right',
            title: {
              display: true,
              text: 'Equity'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: function(context) {
                const datasetLabel = context.dataset.label;
                const value = context.raw.y;
                return `${datasetLabel}: ${value.toFixed(2)}`;
              }
            }
          }
        }
      }
    });
    
    return this.backtestChart;
  }
  
  // Initialize Equity chart
  initEquityChart(containerId, equityData) {
    const container = document.getElementById(containerId);
    
    if (!container) {
      console.error(`Container with ID "${containerId}" not found`);
      return;
    }
    
    // Parse equity data
    const dates = equityData.map(item => new Date(item.date));
    const equity = equityData.map(item => item.equity);
    const returns = equityData.map(item => item.return);
    
    this.equityChart = new Chart(container.getContext('2d'), {
      type: 'line',
      data: {
        datasets: [{
          label: 'Equity',
          data: dates.map((date, i) => ({ x: date, y: equity[i] })),
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          borderWidth: 2,
          fill: true,
          tension: 0.1,
          yAxisID: 'y'
        }, {
          label: 'Return %',
          data: dates.map((date, i) => ({ x: date, y: returns[i] })),
          borderColor: 'rgba(255, 159, 64, 1)',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
          yAxisID: 'y1'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day'
            },
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          },
          y: {
            type: 'linear',
            position: 'left',
            title: {
              display: true,
              text: 'Equity'
            },
            grid: {
              color: 'rgba(70, 70, 70, 0.3)'
            }
          },
          y1: {
            type: 'linear',
            position: 'right',
            title: {
              display: true,
              text: 'Return %'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
    
    return this.equityChart;
  }
  
  // Update chart data with new price data
  updateChartData(data) {
    if (!data || !Array.isArray(data)) {
      console.error('Invalid data provided to updateChartData');
      return;
    }
    
    // Convert data to chart format
    this.chartData.ohlc = data.map(item => ({
      x: new Date(item.time),
      o: item.open,
      h: item.high,
      l: item.low,
      c: item.close
    }));
    
    // Convert data for indicators if available
    if (data[0] && data[0].indicators) {
      this.chartData.indicators.rsi = data.map(item => ({
        x: new Date(item.time),
        y: item.indicators.rsi
      }));
      
      this.chartData.indicators.macd = data.map(item => ({
        x: new Date(item.time),
        y: item.indicators.macd
      }));
      
      this.chartData.indicators.macdSignal = data.map(item => ({
        x: new Date(item.time),
        y: item.indicators.macd_signal
      }));
      
      this.chartData.indicators.macdHistogram = data.map(item => ({
        x: new Date(item.time),
        y: item.indicators.macd - item.indicators.macd_signal
      }));
      
      // Add other indicators as needed
    }
  }
  
  // Update price display with real-time data
  updatePriceDisplay(price, elementId = 'current-price') {
    const priceElement = document.getElementById(elementId);
    if (!priceElement) return;
    
    // Determine price direction
    if (this.lastPrice !== null) {
      this.priceDirection = price > this.lastPrice ? 'up' : price < this.lastPrice ? 'down' : this.priceDirection;
    }
    
    // Format the price
    const formattedPrice = parseFloat(price).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    
    // Update the price display
    priceElement.textContent = formattedPrice;
    priceElement.className = 'price-display';
    
    if (this.priceDirection === 'up') {
      priceElement.classList.add('price-up');
    } else if (this.priceDirection === 'down') {
      priceElement.classList.add('price-down');
    }
    
    // Save the current price
    this.lastPrice = price;
  }
  
  // Add a new price candle to the chart
  addPriceCandle(data) {
    if (!this.priceChart) return;
    
    const candle = {
      x: new Date(data.time),
      o: data.open,
      h: data.high,
      l: data.low,
      c: data.close
    };
    
    // Add the new candle to the data
    this.chartData.ohlc.push(candle);
    
    // Remove old data if there's too much
    if (this.chartData.ohlc.length > 500) {
      this.chartData.ohlc.shift();
    }
    
    // Update the chart
    this.priceChart.data.datasets[0].data = this.chartData.ohlc;
    this.priceChart.update();
  }
  
  // Update all charts with new data
  updateAllCharts() {
    if (this.priceChart) {
      this.priceChart.update();
    }
    
    Object.values(this.indicatorCharts).forEach(chart => {
      if (chart) {
        chart.update();
      }
    });
  }
  
  // Clear all chart data
  clearChartData() {
    this.chartData.ohlc = [];
    this.chartData.volume = [];
    
    Object.keys(this.chartData.indicators).forEach(key => {
      this.chartData.indicators[key] = [];
    });
    
    this.updateAllCharts();
  }
}
