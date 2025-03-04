/**
 * UI Helpers - Tập hợp các hàm trợ giúp xử lý UI và UX
 * -----------------------------------------------------
 * Cung cấp các hàm dùng chung cho toàn bộ ứng dụng:
 * - Hiển thị thông báo
 * - Xử lý hiệu ứng loading
 * - Kiểm tra form
 * - XHR/fetch request helpers
 */

/**
 * Hiển thị thông báo
 * @param {string} type - Loại thông báo (success, danger, warning, info)
 * @param {string} message - Nội dung thông báo
 * @param {number} timeout - Thời gian hiển thị (ms), mặc định 5000ms
 * @param {string} targetSelector - Selector của phần tử để chèn thông báo, mặc định là .alert-container nếu tồn tại, không thì body
 */
function showAlert(type, message, timeout = 5000, targetSelector = null) {
    // Kiểm tra type hợp lệ
    if (!['success', 'danger', 'warning', 'info'].includes(type)) {
        console.error('Invalid alert type:', type);
        type = 'info';
    }
    
    // Tạo element alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    
    // Thêm biểu tượng phù hợp
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'danger') icon = 'exclamation-triangle';
    if (type === 'warning') icon = 'exclamation-circle';
    
    // Thêm nội dung
    alertDiv.innerHTML = `
        <i class="bi bi-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Tìm container để chèn alert
    let container;
    if (targetSelector) {
        container = document.querySelector(targetSelector);
    } else {
        container = document.querySelector('.alert-container');
        if (!container) {
            // Nếu không có container, tạo một cái và thêm vào đầu body
            container = document.createElement('div');
            container.className = 'alert-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.left = '50%';
            container.style.transform = 'translateX(-50%)';
            container.style.zIndex = '1050';
            container.style.width = '80%';
            container.style.maxWidth = '500px';
            document.body.insertBefore(container, document.body.firstChild);
        }
    }
    
    // Thêm alert vào container
    container.appendChild(alertDiv);
    
    // Auto-dismiss sau timeout ms
    if (timeout > 0) {
        setTimeout(() => {
            if (alertDiv) {
                // Nếu đã tạo Bootstrap alert, dùng dismiss của nó
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }
        }, timeout);
    }
    
    // Xóa alert sau khi nó đã ẩn đi
    alertDiv.addEventListener('closed.bs.alert', () => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    });
    
    return alertDiv;
}

/**
 * Hiển thị Toast notification
 * @param {string} title - Tiêu đề của toast
 * @param {string} message - Nội dung thông báo
 * @param {string} type - Loại thông báo (success, danger, warning, info)
 * @param {number} autohide - Tự động ẩn sau bao nhiêu ms, mặc định 5000ms, 0 để không tự ẩn
 */
function showToast(title, message, type = 'info', autohide = 5000) {
    // Kiểm tra type hợp lệ
    if (!['success', 'danger', 'warning', 'info'].includes(type)) {
        console.error('Invalid toast type:', type);
        type = 'info';
    }
    
    // Tạo toast container nếu chưa có
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1060';
        document.body.appendChild(toastContainer);
    }
    
    // Tạo toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = 'toast';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    if (autohide > 0) {
        toast.setAttribute('data-bs-delay', autohide.toString());
        toast.setAttribute('data-bs-autohide', 'true');
    } else {
        toast.setAttribute('data-bs-autohide', 'false');
    }
    
    // Thiết lập kiểu và biểu tượng dựa trên type
    let icon = 'info-circle';
    let bgClass = 'bg-info';
    
    if (type === 'success') {
        icon = 'check-circle-fill';
        bgClass = 'bg-success';
    } else if (type === 'danger') {
        icon = 'exclamation-triangle-fill';
        bgClass = 'bg-danger';
    } else if (type === 'warning') {
        icon = 'exclamation-triangle-fill';
        bgClass = 'bg-warning';
    }
    
    // Tạo nội dung toast
    toast.innerHTML = `
        <div class="toast-header ${bgClass} text-white">
            <i class="bi bi-${icon} me-2"></i>
            <strong class="me-auto">${title}</strong>
            <small>Vừa xong</small>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Thêm toast vào container
    toastContainer.appendChild(toast);
    
    // Khởi tạo và hiển thị toast
    const toastInstance = new bootstrap.Toast(toast);
    toastInstance.show();
    
    // Xóa toast sau khi ẩn
    toast.addEventListener('hidden.bs.toast', function () {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    });
    
    return toastInstance;
}

/**
 * Hiển thị overlay loading
 * @param {string} message - Thông điệp hiển thị khi loading (tùy chọn)
 * @returns {HTMLElement} Phần tử loading overlay đã tạo
 */
function showLoading(message = 'Đang xử lý...') {
    // Kiểm tra xem đã có loading overlay chưa
    let loadingOverlay = document.getElementById('loadingOverlay');
    
    if (!loadingOverlay) {
        loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'loadingOverlay';
        loadingOverlay.className = 'loading-overlay';
        
        // Tạo nội dung loading
        const loadingContent = document.createElement('div');
        loadingContent.className = 'd-flex flex-column align-items-center';
        
        // Spinner
        loadingContent.innerHTML = `
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Đang tải...</span>
            </div>
            <div class="text-white">${message}</div>
        `;
        
        loadingOverlay.appendChild(loadingContent);
        document.body.appendChild(loadingOverlay);
        
        // Ngăn scroll
        document.body.style.overflow = 'hidden';
    }
    
    return loadingOverlay;
}

/**
 * Ẩn overlay loading
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        // Thêm class để tạo hiệu ứng fade out
        loadingOverlay.style.animation = 'fadeOut 0.2s ease-in-out';
        
        // Xóa sau khi hiệu ứng hoàn tất
        setTimeout(() => {
            if (loadingOverlay.parentNode) {
                loadingOverlay.parentNode.removeChild(loadingOverlay);
                // Cho phép scroll lại
                document.body.style.overflow = '';
            }
        }, 200);
    }
}

/**
 * Kiểm tra tính hợp lệ của form
 * @param {HTMLFormElement} form - Form cần kiểm tra
 * @param {Object} customValidators - Các validator tùy chỉnh (key: name của input, value: hàm validator)
 * @returns {boolean} Form có hợp lệ hay không
 */
function validateForm(form, customValidators = {}) {
    if (!form) return false;
    
    let isValid = true;
    const inputs = form.querySelectorAll('input, textarea, select');
    
    // Reset previous errors
    const errorMessages = form.querySelectorAll('.error-message');
    errorMessages.forEach(el => el.parentNode.removeChild(el));
    
    // Check each input
    inputs.forEach(input => {
        input.classList.remove('is-invalid');
        
        // Skip disabled inputs
        if (input.disabled) return;
        
        // Required fields
        if (input.required && !input.value.trim()) {
            markInvalid(input, 'Trường này là bắt buộc');
            isValid = false;
            return;
        }
        
        // Email validation
        if (input.type === 'email' && input.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value.trim())) {
                markInvalid(input, 'Email không hợp lệ');
                isValid = false;
                return;
            }
        }
        
        // Number validation
        if (input.type === 'number' && input.value.trim()) {
            const value = parseFloat(input.value);
            if (isNaN(value)) {
                markInvalid(input, 'Vui lòng nhập một số hợp lệ');
                isValid = false;
                return;
            }
            
            if (input.min && value < parseFloat(input.min)) {
                markInvalid(input, `Giá trị tối thiểu là ${input.min}`);
                isValid = false;
                return;
            }
            
            if (input.max && value > parseFloat(input.max)) {
                markInvalid(input, `Giá trị tối đa là ${input.max}`);
                isValid = false;
                return;
            }
        }
        
        // Custom validator
        if (input.name && customValidators[input.name]) {
            const validatorResult = customValidators[input.name](input.value, input);
            if (validatorResult !== true) {
                markInvalid(input, validatorResult || 'Giá trị không hợp lệ');
                isValid = false;
                return;
            }
        }
    });
    
    return isValid;
    
    // Helper để đánh dấu input không hợp lệ
    function markInvalid(input, message) {
        input.classList.add('is-invalid');
        
        // Thêm thông báo lỗi
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback error-message';
        errorDiv.textContent = message;
        
        // Thêm sau input hoặc sau parent của input (với một số trường hợp như checkbox)
        if (input.type === 'checkbox' || input.type === 'radio') {
            const parent = input.closest('.form-check') || input.parentNode;
            parent.appendChild(errorDiv);
        } else {
            input.parentNode.appendChild(errorDiv);
        }
    }
}

/**
 * Kiểm tra trạng thái kết nối mạng
 * @returns {boolean} Trạng thái kết nối
 */
function isOnline() {
    return navigator.onLine;
}

/**
 * Gửi request API với xử lý loading và thông báo
 * @param {string} url - URL endpoint
 * @param {Object} options - Tùy chọn fetch API
 * @param {boolean} showLoadingIndicator - Có hiển thị loading indicator không
 * @param {function} successCallback - Callback khi thành công
 * @param {function} errorCallback - Callback khi lỗi
 * @returns {Promise} Promise của fetch
 */
function fetchAPI(url, options = {}, showLoadingIndicator = true, successCallback = null, errorCallback = null) {
    // Kiểm tra kết nối mạng
    if (!isOnline()) {
        showAlert('danger', 'Không có kết nối mạng. Vui lòng kiểm tra lại kết nối internet của bạn.');
        if (errorCallback) errorCallback({ message: 'Không có kết nối mạng' });
        return Promise.reject(new Error('No internet connection'));
    }
    
    // Thiết lập headers mặc định
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    const fetchOptions = { ...defaultOptions, ...options };
    
    // Hiển thị loading nếu cần
    if (showLoadingIndicator) {
        showLoading();
    }
    
    // Gửi request
    return fetch(url, fetchOptions)
        .then(response => {
            // Ẩn loading
            if (showLoadingIndicator) {
                hideLoading();
            }
            
            // Kiểm tra response có OK không
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            // Trả về JSON nếu có
            return response.json().catch(() => {
                // Nếu không phải JSON, trả về response text
                return response.text();
            });
        })
        .then(data => {
            // Gọi success callback nếu có
            if (successCallback) {
                successCallback(data);
            }
            return data;
        })
        .catch(error => {
            // Ẩn loading nếu có lỗi
            if (showLoadingIndicator) {
                hideLoading();
            }
            
            // Hiển thị thông báo lỗi
            console.error('API Error:', error);
            
            // Xử lý các mã lỗi HTTP cụ thể
            let errorMessage = 'Đã xảy ra lỗi khi kết nối đến máy chủ';
            let errorType = 'danger';
            
            if (error.message) {
                if (error.message.includes('HTTP error! Status: 404')) {
                    errorMessage = 'API không tồn tại hoặc đường dẫn không chính xác (404)';
                } else if (error.message.includes('HTTP error! Status: 401')) {
                    errorMessage = 'Lỗi xác thực, vui lòng đăng nhập lại (401)';
                    // Có thể chuyển hướng đến trang đăng nhập ở đây
                } else if (error.message.includes('HTTP error! Status: 403')) {
                    errorMessage = 'Bạn không có quyền truy cập API này (403)';
                } else if (error.message.includes('HTTP error! Status: 500')) {
                    errorMessage = 'Lỗi máy chủ, vui lòng thử lại sau hoặc liên hệ hỗ trợ (500)';
                } else if (error.message.includes('HTTP error! Status: 502') || 
                         error.message.includes('HTTP error! Status: 503') || 
                         error.message.includes('HTTP error! Status: 504')) {
                    errorMessage = 'Máy chủ tạm thời không khả dụng, vui lòng thử lại sau';
                    errorType = 'warning';
                } else {
                    errorMessage = `Lỗi: ${error.message}`;
                }
            }
            
            showAlert(errorType, errorMessage);
            
            // Gọi error callback nếu có
            if (errorCallback) {
                errorCallback(error, errorMessage);
            }
            
            throw error;
        });
}

/**
 * Format số thành chuỗi tiền tệ
 * @param {number} amount - Số tiền cần format
 * @param {string} currency - Mã tiền tệ (USD, VND, BTC, ETH, ...)
 * @param {string} locale - Locale để format (vi-VN, en-US, ...)
 * @returns {string} Chuỗi đã format
 */
function formatCurrency(amount, currency = 'USD', locale = 'vi-VN') {
    // Định dạng số thập phân phù hợp với loại tiền tệ
    let decimals = 2;
    if (['BTC', 'ETH', 'BNB'].includes(currency)) {
        decimals = 8;
    } else if (['USDT', 'BUSD'].includes(currency)) {
        decimals = 2;
    }
    
    try {
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(amount);
    } catch (error) {
        // Fallback nếu không hỗ trợ locale hoặc currency
        console.warn('Currency formatting error:', error);
        return `${amount.toFixed(decimals)} ${currency}`;
    }
}

/**
 * Format ngày giờ
 * @param {Date|string} date - Đối tượng Date hoặc chuỗi ngày
 * @param {string} format - Định dạng (short, long, datetime, time)
 * @param {string} locale - Locale để format
 * @returns {string} Chuỗi ngày đã format
 */
function formatDate(date, format = 'short', locale = 'vi-VN') {
    if (!date) return '';
    
    // Chuyển về đối tượng Date nếu là string
    if (typeof date === 'string') {
        date = new Date(date);
    }
    
    // Kiểm tra date có hợp lệ không
    if (!(date instanceof Date) || isNaN(date)) {
        return 'Ngày không hợp lệ';
    }
    
    try {
        switch (format) {
            case 'short':
                return new Intl.DateTimeFormat(locale, {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit'
                }).format(date);
            
            case 'long':
                return new Intl.DateTimeFormat(locale, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                }).format(date);
            
            case 'datetime':
                return new Intl.DateTimeFormat(locale, {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                }).format(date);
            
            case 'time':
                return new Intl.DateTimeFormat(locale, {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                }).format(date);
            
            default:
                return date.toLocaleString(locale);
        }
    } catch (error) {
        console.warn('Date formatting error:', error);
        return date.toString();
    }
}

/**
 * Debounce - trì hoãn thực thi hàm cho đến khi người dùng dừng nhập
 * @param {function} func - Hàm cần thực thi
 * @param {number} wait - Thời gian chờ (ms)
 * @returns {function} Hàm đã được debounce
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Khởi tạo tooltip và popover Bootstrap
 * Gọi hàm này sau khi DOM đã load
 */
function initializeTooltips() {
    // Khởi tạo tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Khởi tạo popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Highlight phần tử khi có thay đổi giá trị
 * @param {HTMLElement} element - Phần tử cần highlight
 * @param {string} type - Loại thay đổi (increase, decrease)
 * @param {number} duration - Thời gian hiệu ứng (ms)
 */
function highlightChange(element, type, duration = 2000) {
    if (!element) return;
    
    // Thêm class highlight tương ứng
    element.classList.add(`value-${type}`);
    
    // Xóa class sau thời gian định sẵn
    setTimeout(() => {
        element.classList.remove(`value-${type}`);
    }, duration);
}

/**
 * Scroll đến phần tử
 * @param {HTMLElement|string} element - Phần tử hoặc selector để scroll đến
 * @param {number} offset - Offset từ đỉnh (px)
 * @param {string} behavior - Kiểu scroll (smooth, auto)
 */
function scrollToElement(element, offset = 0, behavior = 'smooth') {
    if (typeof element === 'string') {
        element = document.querySelector(element);
    }
    
    if (!element) return;
    
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: behavior
    });
}

/**
 * Khởi động các event listeners cần thiết khi trang đã load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo tooltips và popovers
    initializeTooltips();
    
    // Gắn sự kiện cho các nút chung
    document.querySelectorAll('.btn-refresh').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.dataset.target;
            const loadingMessage = this.dataset.loadingMessage || 'Đang tải dữ liệu...';
            
            if (targetId) {
                const target = document.getElementById(targetId);
                if (target) {
                    target.innerHTML = `
                        <div class="text-center py-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Đang tải...</span>
                            </div>
                            <div class="mt-2">${loadingMessage}</div>
                        </div>
                    `;
                    
                    // Refresh content after delay (simulated fetch)
                    setTimeout(() => {
                        target.innerHTML = '<div class="alert alert-success">Dữ liệu đã được tải lại thành công!</div>';
                    }, 1000);
                }
            }
        });
    });
    
    // Gắn sự kiện cho tất cả nút Save Settings
    document.querySelectorAll('[id$="Settings"]').forEach(button => {
        if (button.id.startsWith('save')) {
            // Check if event is already attached
            if (!button.dataset.hasEventListener) {
                button.dataset.hasEventListener = true;
                button.addEventListener('click', function() {
                    // ID prefix after 'save' indicates settings type
                    const settingsType = button.id.replace('save', '').replace('Settings', '');
                    
                    // Show loading
                    showLoading();
                    
                    // Simulate API call
                    setTimeout(() => {
                        hideLoading();
                        showAlert('success', `Cài đặt ${settingsType.toLowerCase() || 'chung'} đã được lưu thành công!`);
                    }, 1000);
                });
            }
        }
    });
});

// Export các hàm để sử dụng từ module khác
export {
    showAlert,
    showToast,
    showLoading,
    hideLoading,
    validateForm,
    isOnline,
    fetchAPI,
    formatCurrency,
    formatDate,
    debounce,
    initializeTooltips,
    highlightChange,
    scrollToElement
};