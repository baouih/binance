/**
 * Tab Manager - Quản lý trạng thái tab trên trang web
 * File này xử lý việc lưu trữ và khôi phục tab hiện tại khi người dùng làm mới trang
 */

document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo TabManager cho từng trang
    initTabManager();
});

/**
 * Khởi tạo tab manager trên trang hiện tại
 */
function initTabManager() {
    // Kiểm tra xem trang có tabs không
    const tabLists = document.querySelectorAll('[role="tablist"]');
    if (!tabLists || tabLists.length === 0) return;
    
    // Xử lý từng tablist trên trang
    tabLists.forEach(tabList => {
        const tabListId = tabList.id;
        if (!tabListId) return; // Bỏ qua nếu không có ID
        
        // Khôi phục tab đang active từ localStorage
        const activeTabId = localStorage.getItem(`active_tab_${tabListId}`);
        if (activeTabId) {
            // Tìm tab theo ID và kích hoạt
            const tabElement = document.getElementById(activeTabId);
            if (tabElement) {
                // Sử dụng Bootstrap API để kích hoạt tab
                const tabInstance = new bootstrap.Tab(tabElement);
                tabInstance.show();
                
                // Thêm class active cho tab
                const tabContentId = tabElement.getAttribute('aria-controls') || 
                                    tabElement.getAttribute('href')?.replace('#', '');
                if (tabContentId) {
                    // Đảm bảo nội dung tab hiển thị
                    const tabContent = document.getElementById(tabContentId);
                    if (tabContent) {
                        // Xóa active khỏi tất cả tab content
                        document.querySelectorAll('.tab-pane').forEach(el => {
                            el.classList.remove('active', 'show');
                        });
                        
                        // Thêm active vào tab content hiện tại
                        tabContent.classList.add('active', 'show');
                    }
                }
            }
        }
        
        // Lưu tab hiện tại khi người dùng chuyển tab
        const tabs = tabList.querySelectorAll('[role="tab"]');
        tabs.forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(event) {
                // Lưu ID của tab vào localStorage
                localStorage.setItem(`active_tab_${tabListId}`, event.target.id);
            });
        });
    });
}