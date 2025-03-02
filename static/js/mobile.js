// JavaScript for mobile enhancements

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
            
            // Change icon
            const icon = mobileMenuBtn.querySelector('i');
            if (icon) {
                if (sidebar.classList.contains('show')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-times');
                } else {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });
        
        // Close sidebar when clicking on a link (on mobile)
        const sidebarLinks = sidebar.querySelectorAll('a.nav-link');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth < 768) {
                    sidebar.classList.remove('show');
                    
                    // Reset icon
                    const icon = mobileMenuBtn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('fa-times');
                        icon.classList.add('fa-bars');
                    }
                }
            });
        });
        
        // Close sidebar when clicking outside
        document.addEventListener('click', function(event) {
            if (window.innerWidth < 768 && 
                !sidebar.contains(event.target) && 
                !mobileMenuBtn.contains(event.target) && 
                sidebar.classList.contains('show')) {
                
                sidebar.classList.remove('show');
                
                // Reset icon
                const icon = mobileMenuBtn.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            }
        });
    }
    
    // Automatically adjust tables for mobile view
    const tables = document.querySelectorAll('table');
    if (tables.length > 0) {
        tables.forEach(table => {
            if (!table.parentElement.classList.contains('table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.classList.add('table-responsive');
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
    }
    
    // Enhance form elements for mobile
    const formSelects = document.querySelectorAll('select');
    formSelects.forEach(select => {
        select.classList.add('form-select');
    });
    
    // Add extra spacing to form elements on mobile
    if (window.innerWidth <= 576) {
        const formGroups = document.querySelectorAll('.form-group, .mb-3');
        formGroups.forEach(group => {
            group.style.marginBottom = '1.5rem';
        });
    }
});

// Fix for iOS devices to handle position:fixed correctly with virtual keyboard
function fixIOSVirtualKeyboard() {
    if (/iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream) {
        document.addEventListener('focus', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                document.body.classList.add('ios-keyboard-open');
            }
        }, true);
        
        document.addEventListener('blur', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                document.body.classList.remove('ios-keyboard-open');
            }
        }, true);
    }
}

fixIOSVirtualKeyboard();