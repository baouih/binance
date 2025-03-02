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
    const isMobile = window.innerWidth < 768;
    const isPortrait = window.innerHeight > window.innerWidth;
    
    if (isMobile) {
        // Apply mobile-specific adjustments
        document.body.classList.add('mobile-view');
        
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
    } else {
        // Reset to desktop view
        document.body.classList.remove('mobile-view', 'portrait-view', 'landscape-view');
        
        // Hide mobile menu button on desktop
        const menuBtn = document.getElementById('mobile-menu-btn');
        if (menuBtn) {
            menuBtn.style.display = 'none';
        }
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