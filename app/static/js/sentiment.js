/**
 * Market Sentiment Module
 * Handles the display and updates of market sentiment data
 */

class SentimentDisplay {
  constructor() {
    this.currentSentiment = null;
    this.sentimentHistory = [];
    this.socket = null;
    this.sentimentChart = null;
  }
  
  init(socket) {
    this.socket = socket;
    this.setupEventListeners();
    this.loadCurrentSentiment();
    this.loadSentimentHistory();
    this.initSentimentChart();
  }
  
  setupEventListeners() {
    // Listen for real-time sentiment updates
    if (this.socket) {
      this.socket.subscribe('sentiment_update', (data) => {
        this.handleSentimentUpdate(data);
      });
    }
  }
  
  async loadCurrentSentiment() {
    try {
      const response = await fetch('/api/sentiment');
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      const data = await response.json();
      this.currentSentiment = data;
      this.updateSentimentDisplay(data);
    } catch (error) {
      console.error('Error loading sentiment data:', error);
    }
  }
  
  async loadSentimentHistory(hours = 24) {
    try {
      const response = await fetch(`/api/sentiment/history?hours=${hours}`);
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      const data = await response.json();
      this.sentimentHistory = data;
      this.updateSentimentChart();
    } catch (error) {
      console.error('Error loading sentiment history:', error);
    }
  }
  
  handleSentimentUpdate(data) {
    this.currentSentiment = data;
    this.updateSentimentDisplay(data);
    
    // Add to history and update chart
    this.sentimentHistory.push(data);
    if (this.sentimentHistory.length > 100) {
      this.sentimentHistory.shift(); // Remove oldest item
    }
    this.updateSentimentChart();
  }
  
  updateSentimentDisplay(data) {
    // Update the sentiment score display
    const sentimentElement = document.getElementById('sentiment-value');
    const sentimentLabelElement = document.getElementById('sentiment-label');
    const sentimentContainerElement = document.getElementById('sentiment-container');
    
    if (sentimentElement) {
      sentimentElement.textContent = data.sentiment_score.toFixed(1);
    }
    
    if (sentimentLabelElement) {
      sentimentLabelElement.textContent = data.label;
      sentimentLabelElement.style.color = data.color;
    }
    
    if (sentimentContainerElement) {
      // Set the background color with transparency
      const color = data.color;
      // Extract hex and convert to RGB for transparency
      const r = parseInt(color.substring(1, 3), 16);
      const g = parseInt(color.substring(3, 5), 16);
      const b = parseInt(color.substring(5, 7), 16);
      sentimentContainerElement.style.backgroundColor = `rgba(${r}, ${g}, ${b}, 0.1)`;
      sentimentContainerElement.style.borderColor = color;
    }
    
    // Update sentiment indicators
    this.updateSentimentIndicators(data);
  }
  
  updateSentimentIndicators(data) {
    // Update the technical, social, and fear/greed indicators
    const technicalElement = document.getElementById('technical-sentiment');
    const socialElement = document.getElementById('social-sentiment');
    const fearGreedElement = document.getElementById('fear-greed-index');
    
    if (technicalElement) {
      technicalElement.textContent = data.technical.toFixed(1);
      technicalElement.style.color = this.getColorForValue(data.technical);
    }
    
    if (socialElement) {
      socialElement.textContent = data.social.toFixed(1);
      socialElement.style.color = this.getColorForValue(data.social);
    }
    
    if (fearGreedElement) {
      fearGreedElement.textContent = data.fear_greed.toFixed(1);
      fearGreedElement.style.color = this.getColorForValue(data.fear_greed);
    }
  }
  
  getColorForValue(value) {
    // Return a color based on the value (0-100)
    if (value < 20) return '#d32f2f'; // Extremely bearish
    if (value < 40) return '#f44336'; // Bearish
    if (value < 60) return '#9e9e9e'; // Neutral
    if (value < 80) return '#4caf50'; // Bullish
    return '#2e7d32'; // Extremely bullish
  }
  
  initSentimentChart() {
    const chartElement = document.getElementById('sentiment-chart');
    if (!chartElement) {
      return;
    }
    
    // Create the chart
    const ctx = chartElement.getContext('2d');
    this.sentimentChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Market Sentiment',
            data: [],
            borderColor: '#4CAF50',
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: true
          },
          {
            label: 'Technical',
            data: [],
            borderColor: '#2196F3',
            borderWidth: 1,
            tension: 0.4,
            fill: false
          },
          {
            label: 'Social',
            data: [],
            borderColor: '#9C27B0',
            borderWidth: 1,
            tension: 0.4,
            fill: false
          },
          {
            label: 'Fear & Greed',
            data: [],
            borderColor: '#FF9800',
            borderWidth: 1,
            tension: 0.4,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Time'
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: 'Sentiment Score'
            },
            min: 0,
            max: 100,
            ticks: {
              stepSize: 20
            }
          }
        }
      }
    });
  }
  
  updateSentimentChart() {
    if (!this.sentimentChart || !this.sentimentHistory || this.sentimentHistory.length === 0) {
      return;
    }
    
    // Format the timestamps for display
    const labels = this.sentimentHistory.map(item => {
      const date = new Date(item.timestamp);
      return date.toLocaleTimeString();
    });
    
    // Get the sentiment data
    const sentimentData = this.sentimentHistory.map(item => item.sentiment_score);
    const technicalData = this.sentimentHistory.map(item => item.technical);
    const socialData = this.sentimentHistory.map(item => item.social);
    const fearGreedData = this.sentimentHistory.map(item => item.fear_greed);
    
    // Update the chart data
    this.sentimentChart.data.labels = labels;
    this.sentimentChart.data.datasets[0].data = sentimentData;
    this.sentimentChart.data.datasets[1].data = technicalData;
    this.sentimentChart.data.datasets[2].data = socialData;
    this.sentimentChart.data.datasets[3].data = fearGreedData;
    
    // Update chart colors based on the current sentiment
    if (this.currentSentiment) {
      this.sentimentChart.data.datasets[0].borderColor = this.currentSentiment.color;
      this.sentimentChart.data.datasets[0].backgroundColor = `${this.currentSentiment.color}20`; // Add 20 for 12% opacity in hex
    }
    
    // Update the chart
    this.sentimentChart.update();
  }
}

// Initialize when the page loads
document.addEventListener('DOMContentLoaded', () => {
  window.sentimentDisplay = new SentimentDisplay();
});