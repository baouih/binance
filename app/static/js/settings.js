/**
 * Settings Controller
 * Handles settings management for the trading bot
 */

class SettingsController {
  constructor() {
    this.settingsForm = document.getElementById('settings-form');
    this.testnetSwitch = document.getElementById('testnet-switch');
    this.simulationSwitch = document.getElementById('simulation-switch');
    this.networkStatusText = document.getElementById('network-status');
    this.simulationStatusText = document.getElementById('simulation-status');
    this.testnetDetails = document.getElementById('testnet-details');
    this.mainnetDetails = document.getElementById('mainnet-details');
    this.modeIndicator = document.getElementById('mode-indicator');
    
    this.setupEventListeners();
    this.fetchSettingsStatus();
  }
  
  setupEventListeners() {
    // Network switch
    this.testnetSwitch.addEventListener('change', () => {
      this.updateNetworkSettings(this.testnetSwitch.checked);
    });
    
    // Simulation switch
    this.simulationSwitch.addEventListener('change', () => {
      this.updateSimulationSettings(this.simulationSwitch.checked);
    });
    
    // API form submit
    document.getElementById('api-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveApiKeys();
    });
  }
  
  fetchSettingsStatus() {
    fetch('/api/settings/status_config')
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          // Update switches based on current settings
          this.testnetSwitch.checked = data.network === 'testnet';
          this.simulationSwitch.checked = data.simulation_mode;
          
          // Update display
          this.updateNetworkDisplay(data.network === 'testnet');
          this.updateSimulationDisplay(data.simulation_mode);
          
          // Update global mode indicator
          this.updateGlobalModeIndicator(data.simulation_mode);
        } else {
          this.showToast(`Không thể tải thông tin cài đặt: ${data.message}`, 'warning');
        }
      })
      .catch(error => {
        console.error('Error fetching settings status:', error);
        this.showToast('Lỗi kết nối đến máy chủ', 'danger');
      });
  }
  
  updateNetworkSettings(useTestnet) {
    fetch('/api/settings/network', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        testnet: useTestnet
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        this.updateNetworkDisplay(useTestnet);
        this.showToast(`Đã chuyển sang chế độ ${useTestnet ? 'TESTNET' : 'MAINNET'}`, 'success');
        
        // Force reload page to update all components
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        this.showToast(`Lỗi: ${data.message}`, 'danger');
        // Revert switch if there was an error
        this.testnetSwitch.checked = !useTestnet;
      }
    })
    .catch(error => {
      console.error('Error updating network settings:', error);
      this.showToast('Lỗi kết nối đến máy chủ', 'danger');
      this.testnetSwitch.checked = !useTestnet;
    });
  }
  
  updateSimulationSettings(useSimulation) {
    fetch('/api/settings/simulation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        simulation: useSimulation
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        this.updateSimulationDisplay(useSimulation);
        this.updateGlobalModeIndicator(useSimulation);
        this.showToast(`Đã ${useSimulation ? 'BẬT' : 'TẮT'} chế độ mô phỏng`, 'success');
        
        // Force reload page to update all components
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        this.showToast(`Lỗi: ${data.message}`, 'danger');
        this.simulationSwitch.checked = !useSimulation;
      }
    })
    .catch(error => {
      console.error('Error updating simulation settings:', error);
      this.showToast('Lỗi kết nối đến máy chủ', 'danger');
      this.simulationSwitch.checked = !useSimulation;
    });
  }
  
  saveApiKeys() {
    const apiKey = document.getElementById('api-key').value.trim();
    const apiSecret = document.getElementById('api-secret').value.trim();
    
    // Validate form
    if (!apiKey || !apiSecret) {
      this.showToast('Vui lòng nhập cả API key và API secret', 'danger');
      return;
    }
    
    // Send API keys to server
    fetch('/api/settings/api_keys', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        api_key: apiKey,
        api_secret: apiSecret
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        this.showToast('Đã lưu API keys thành công', 'success');
        
        // Force reload page to update account info
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        this.showToast(`Lỗi: ${data.message}`, 'danger');
      }
    })
    .catch(error => {
      console.error('Error saving API keys:', error);
      this.showToast('Lỗi kết nối đến máy chủ', 'danger');
    });
  }
  
  updateNetworkDisplay(isTestnet) {
    this.networkStatusText.textContent = isTestnet ? 'Testnet' : 'Mainnet';
    this.networkStatusText.className = isTestnet ? 'badge bg-info' : 'badge bg-danger';
    
    // Toggle details visibility
    if (this.testnetDetails) {
      this.testnetDetails.style.display = isTestnet ? 'block' : 'none';
    }
    if (this.mainnetDetails) {
      this.mainnetDetails.style.display = isTestnet ? 'none' : 'block';
    }
  }
  
  updateSimulationDisplay(isSimulation) {
    this.simulationStatusText.textContent = isSimulation ? 'Enabled' : 'Disabled';
    this.simulationStatusText.className = isSimulation ? 'badge bg-secondary' : 'badge bg-success';
  }
  
  updateGlobalModeIndicator(isSimulation) {
    // Update the global indicator in the navbar
    if (this.modeIndicator) {
      if (isSimulation) {
        this.modeIndicator.textContent = 'Simulation Mode';
        this.modeIndicator.className = 'badge bg-warning';
      } else {
        this.modeIndicator.textContent = 'Live Trading';
        this.modeIndicator.className = 'badge bg-success';
      }
    }
  }
  
  showToast(message, type = 'primary') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
      toast.remove();
    });
  }
}

// Initialize settings controller when page loads
document.addEventListener('DOMContentLoaded', function() {
  if (document.getElementById('settings-container')) {
    window.settingsController = new SettingsController();
  }
});