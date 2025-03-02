/**
 * Mobile interface enhancements and optimizations
 * 
 * This script provides core mobile functionality for improved user experience
 * including menu toggle, portrait/landscape adaptations, and responsive UI adjustments
 */

document.addEventListener('DOMContentLoaded', function() {
    setupMobileMenu();
    checkMobileLayout();
    
    // Handle orientation changes
    window.addEventListener('resize', checkMobileLayout);
});

/**
 * Set up the mobile menu toggle button and functionality
 */
function setupMobileMenu() {
    // Check if we're on a mobile device (< 768px)
    if (window.innerWidth < 768) {
        // Create mobile menu button if it doesn't exist
        if (!document.getElementById('mobile-menu-btn')) {
            const menuBtn = document.createElement('button');
            menuBtn.id = 'mobile-menu-btn';
            menuBtn.className = 'btn mobile-menu-toggle';
            menuBtn.innerHTML = '<i class="bi bi-list"></i>';
            menuBtn.setAttribute('aria-label', 'Toggle Menu');
            document.body.appendChild(menuBtn);
            
            // Add event listener to toggle menu
            menuBtn.addEventListener('click', toggleMobileMenu);
        }
        
        // Ensure all navbar elements are properly prepared for mobile
        const navbarItems = document.querySelectorAll('.navbar-nav .nav-item');
        navbarItems.forEach(item => {
            item.style.width = '100%';
        });
        
        // Fix navbar positioning
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            navbar.style.position = 'fixed';
            navbar.style.top = '0';
            navbar.style.width = '100%';
            navbar.style.zIndex = '1000';
            
            // Add padding to body to prevent content from being hidden under navbar
            document.body.style.paddingTop = (navbar.offsetHeight + 10) + 'px';
        }
    }
}

/**
 * Toggle mobile menu visibility
 */
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    const menuBtn = document.getElementById('mobile-menu-btn');
    
    if (sidebar) {
        sidebar.classList.toggle('show');
        
        // Update menu button icon
        if (menuBtn) {
            const icon = menuBtn.querySelector('i');
            if (sidebar.classList.contains('show')) {
                icon.className = 'bi bi-x';
            } else {
                icon.className = 'bi bi-list';
            }
        }
    }
}

/**
 * Check and adjust layout based on device orientation and screen size
 */
function checkMobileLayout() {
    // Vấn đề là Safari iOS không hiển thị đúng userAgent, check bổ sung
    const isMobile = window.innerWidth < 768 || 
                    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
                    (navigator.userAgent.includes("Safari") && !navigator.userAgent.includes("Chrome") && window.innerWidth < 1000);
    const isPortrait = window.innerHeight > window.innerWidth;
    
    // Theo dõi tỷ lệ màn hình để phát hiện thiết bị di động
    const aspectRatio = window.innerWidth / window.innerHeight;
    const isProbablyMobile = aspectRatio < 1.3 && window.innerWidth < 1000;
    
    // Lưu thông tin phát hiện thiết bị
    if (isProbablyMobile || isMobile) {
        localStorage.setItem('isMobileDevice', 'true');
    }
    
    console.log("Device detection:", { 
        isMobile: isMobile, 
        innerWidth: window.innerWidth,
        aspectRatio: aspectRatio,
        isProbablyMobile: isProbablyMobile,
        userAgent: navigator.userAgent,
        isPortrait: isPortrait 
    });
    
    if (isMobile) {
        // Apply mobile-specific adjustments
        document.body.classList.add('mobile-view');
        console.log("Mobile view applied");
        
        // Ensure mobile navigation is properly set up
        setupMobileNavigation();
        
        // Add specific class for portrait orientation
        if (isPortrait) {
            document.body.classList.add('portrait-view');
            document.body.classList.remove('landscape-view');
            applyPortraitOptimizations();
        } else {
            document.body.classList.add('landscape-view');
            document.body.classList.remove('portrait-view');
            applyLandscapeOptimizations();
        }
        
        // Ensure mobile menu button is visible and positioned correctly
        const menuBtn = document.getElementById('mobile-menu-btn');
        if (menuBtn) {
            menuBtn.style.display = 'block';
            menuBtn.style.left = '10px';
            menuBtn.style.top = '10px';
        }
        
        // Save mobile detection state to localStorage
        localStorage.setItem('isMobileDevice', 'true');
    } else {
        // Reset to desktop view
        document.body.classList.remove('mobile-view', 'portrait-view', 'landscape-view');
        
        // Hide mobile menu button on desktop
        const menuBtn = document.getElementById('mobile-menu-btn');
        if (menuBtn) {
            menuBtn.style.display = 'none';
        }
        
        // Update localStorage
        localStorage.setItem('isMobileDevice', 'false');
    }
}

/**
 * Set up mobile navigation and ensure click handlers are properly attached
 */
function setupMobileNavigation() {
    // Ensure bottom navigation works correctly
    const mobileNavButtons = document.querySelectorAll('.nav-mobile-btn');
    
    mobileNavButtons.forEach(btn => {
        // Remove existing event listeners to prevent duplicates
        const clonedBtn = btn.cloneNode(true);
        if (btn.parentNode) {
            btn.parentNode.replaceChild(clonedBtn, btn);
        }
        
        // Add click event listener
        clonedBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get tab ID from data attribute or href
            let tabId = this.getAttribute('data-bs-target');
            if (tabId) {
                tabId = tabId.replace('#', '');
            } else if (this.getAttribute('href')) {
                tabId = this.getAttribute('href').replace('#', '');
            } else {
                tabId = this.id.replace('-mobile-btn', '');
            }
            
            console.log("Mobile navigation clicked:", tabId);
            
            // Handle direct link cases
            if (this.getAttribute('href') && this.getAttribute('href').startsWith('/')) {
                console.log("Direct navigation to:", this.getAttribute('href'));
                window.location.href = this.getAttribute('href');
                return;
            }
            
            // Handle special cases
            if (tabId === 'settings') {
                console.log("Settings navigation triggered");
                window.location.href = '/settings';
                return;
            }
            
            // Otherwise use the standard tab activation
            activateMobileTab(this, tabId);
        });
    });
    
    // Ensure mobile bot toggle button works
    const mobileBotToggle = document.getElementById('mobileBotToggle');
    if (mobileBotToggle) {
        // Remove existing event listeners
        const clonedToggle = mobileBotToggle.cloneNode(true);
        if (mobileBotToggle.parentNode) {
            mobileBotToggle.parentNode.replaceChild(clonedToggle, mobileBotToggle);
        }
        
        // Add new event listener
        clonedToggle.addEventListener('click', function() {
            console.log("Mobile bot toggle clicked");
            // Kiểm tra xem API đã được thiết lập chưa
            fetch('/api/account/settings')
            .then(response => response.json())
            .then(data => {
                console.log("API settings:", data);
                if (data.api_mode === 'testnet' || data.api_mode === 'live') {
                    if (!data.api_key || !data.api_secret) {
                        // Chưa có API key
                        console.log("API keys not set, redirecting to settings");
                        window.location.href = '/settings';
                        return;
                    }
                    // Gọi API khởi động bot
                    toggleBotStatus();
                } else {
                    // Đang ở chế độ demo, giả lập khởi động
                    toggleBotStatus();
                }
            })
            .catch(error => {
                console.error("Error checking API settings:", error);
                alert("Lỗi khi kiểm tra cài đặt API. Vui lòng thử lại.");
            });
        });
    } else {
        console.log("Mobile bot toggle button not found");
    }
}

/**
 * Apply optimizations for portrait orientation
 */
function applyPortraitOptimizations() {
    // Stack columns vertically in portrait mode
    const rowColumns = document.querySelectorAll('.row > [class*="col-"]');
    rowColumns.forEach(col => {
        // Remove any column size classes and set to full width
        for (let i = 1; i <= 12; i++) {
            col.classList.remove(`col-${i}`, `col-md-${i}`, `col-lg-${i}`);
        }
        col.classList.add('col-12');
    });
    
    // Make tables scrollable horizontally
    const tables = document.querySelectorAll('table:not(.table-responsive)');
    tables.forEach(table => {
        if (!table.closest('.table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
    
    // Adjust card spacing for better mobile viewing
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.style.marginBottom = '15px';
    });
}

/**
 * Apply optimizations for landscape orientation
 */
function applyLandscapeOptimizations() {
    // In landscape, we can be a bit more generous with columns
    const rowColumns = document.querySelectorAll('.row > [class*="col-"]');
    rowColumns.forEach(col => {
        // Restore any original column sizing from data attribute if saved
        const originalClass = col.getAttribute('data-original-class');
        if (originalClass) {
            col.className = originalClass;
        }
    });
    
    // Adjust navbar height in landscape
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        navbar.style.padding = '0.3rem 1rem';
    }
}