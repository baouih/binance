/**
 * Simple Dashboard Script
 * Phiên bản đơn giản của bảng điều khiển giao dịch không phụ thuộc vào Socket.IO
 */

document.addEventListener("DOMContentLoaded", function() {
  // Hiển thị trạng thái mô phỏng
  const statusElement = document.getElementById('connection-status-container');
  if (statusElement) {
    statusElement.innerHTML = '<span class="badge bg-warning">Chế Độ Mô Phỏng Đơn Giản</span>';
  }
  
  // Tạo giá Bitcoin mô phỏng và cập nhật định kỳ
  simulatePriceUpdates();
  
  // Xử lý các sự kiện điều hướng
  setupNavigationEvents();
  
  // Hiển thị thông báo chào mừng
  showMessage("Chào mừng đến với phiên bản đơn giản của Trading Bot!");
});

// Tạo và cập nhật giá mô phỏng
function simulatePriceUpdates() {
  function updatePrice() {
    const basePrice = 79500;
    const variance = 500;
    const price = basePrice + Math.random() * variance;
    
    const priceElement = document.getElementById('current-price');
    if (priceElement) {
      priceElement.textContent = price.toFixed(2);
    }
  }
  
  // Cập nhật ngay lập tức và sau đó mỗi 3 giây
  updatePrice();
  setInterval(updatePrice, 3000);
}

// Thiết lập xử lý sự kiện điều hướng
function setupNavigationEvents() {
  const navLinks = document.querySelectorAll('.navbar-nav a.nav-link');
  navLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href) {
        window.location.href = href;
      }
    });
  });
  
  // Xử lý các nút đặc biệt
  const actionButtons = document.querySelectorAll('[data-action]');
  actionButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      const action = this.getAttribute('data-action');
      
      switch(action) {
        case 'buy':
          showMessage("Đã đặt lệnh MUA mô phỏng thành công!");
          break;
        case 'sell':
          showMessage("Đã đặt lệnh BÁN mô phỏng thành công!");
          break;
        case 'start-bot':
          showMessage("Bot đã bắt đầu hoạt động ở chế độ mô phỏng!");
          break;
        case 'stop-bot':
          showMessage("Bot đã dừng hoạt động!");
          break;
        default:
          console.log("Hành động không được hỗ trợ:", action);
      }
    });
  });
}

// Hiển thị thông báo
function showMessage(message, type = 'success') {
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer) return;
  
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type} border-0`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  toastContainer.appendChild(toast);
  
  const bsToast = new bootstrap.Toast(toast, {
    autohide: true,
    delay: 3000
  });
  
  bsToast.show();
  
  // Auto remove after hiding
  toast.addEventListener('hidden.bs.toast', function () {
    toast.remove();
  });
}