/**
 * Mobile touch and viewport-specific enhancements
 * 
 * This script handles mobile-specific touchscreen and viewport enhancements
 * for better mobile experience in portrait mode
 */

document.addEventListener('DOMContentLoaded', function() {
    // Only apply these enhancements on mobile devices
    if (window.innerWidth <= 576) {
        enhanceMobileTables();
        enhanceMobileForms();
        adjustMobileLayout();
        setupMobileSwipeActions();
    }
    
    // Handle orientation changes
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 576) {
            adjustMobileLayout();
        }
    });
});

/**
 * Enhances tables for mobile view
 */
function enhanceMobileTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        // Add responsive class if not already present
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.classList.add('table-responsive');
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
        
        // Reduce font size for mobile tables
        table.classList.add('table-sm');
        
        // Add zebra striping for better readability
        table.classList.add('table-striped');
    });
}

/**
 * Enhances form elements for mobile
 */
function enhanceMobileForms() {
    // Increase height of input fields for better touchability
    const inputs = document.querySelectorAll('input[type="text"], input[type="number"], input[type="password"], input[type="email"]');
    inputs.forEach(input => {
        input.style.height = '44px';
        input.style.fontSize = '16px'; // Prevents iOS zoom on focus
    });
    
    // Add touch-friendly styling to form controls
    const formSelects = document.querySelectorAll('select');
    formSelects.forEach(select => {
        select.style.height = '44px';
        select.style.fontSize = '16px';
    });
    
    // Increase spacing between form elements
    const formGroups = document.querySelectorAll('.form-group, .mb-3');
    formGroups.forEach(group => {
        group.style.marginBottom = '20px';
    });
    
    // Make checkboxes and radio buttons larger
    const checkboxes = document.querySelectorAll('.form-check-input');
    checkboxes.forEach(checkbox => {
        checkbox.style.width = '20px';
        checkbox.style.height = '20px';
    });
}

/**
 * Adjusts layout for mobile portrait mode
 */
function adjustMobileLayout() {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.style.paddingLeft = '10px';
        mainContent.style.paddingRight = '10px';
    }
    
    // Adjust cards to use full width
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.style.width = '100%';
    });
    
    // Make buttons more touch-friendly
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        if (!button.classList.contains('btn-sm')) {
            button.style.padding = '10px 15px';
        }
    });
    
    // Adjust tabs and pills for better touch targets
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.style.padding = '12px 15px';
    });
}

/**
 * Sets up mobile swipe actions for common UI interactions
 */
function setupMobileSwipeActions() {
    let startX, startY, endX, endY;
    const minSwipeDistance = 50; // Minimum distance for a swipe to be registered
    
    document.addEventListener('touchstart', function(event) {
        startX = event.touches[0].clientX;
        startY = event.touches[0].clientY;
    }, false);
    
    document.addEventListener('touchend', function(event) {
        endX = event.changedTouches[0].clientX;
        endY = event.changedTouches[0].clientY;
        
        handleSwipe();
    }, false);
    
    function handleSwipe() {
        // Calculate horizontal and vertical distances
        const diffX = endX - startX;
        const diffY = endY - startY;
        
        // Check if the swipe was horizontal (more horizontal than vertical)
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > minSwipeDistance) {
            // Right swipe
            if (diffX > 0) {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && !sidebar.classList.contains('show')) {
                    sidebar.classList.add('show');
                    const icon = document.querySelector('#mobile-menu-btn i');
                    if (icon) {
                        icon.classList.remove('fa-bars');
                        icon.classList.add('fa-times');
                    }
                }
            } 
            // Left swipe
            else {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && sidebar.classList.contains('show')) {
                    sidebar.classList.remove('show');
                    const icon = document.querySelector('#mobile-menu-btn i');
                    if (icon) {
                        icon.classList.remove('fa-times');
                        icon.classList.add('fa-bars');
                    }
                }
            }
        }
    }
}