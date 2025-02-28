$(document).ready(function () {
    // Lấy dữ liệu từ localStorage hoặc khởi tạo object rỗng
    let quantities = JSON.parse(localStorage.getItem('productQuantities')) || {};

    // Khôi phục số lượng khi tải trang
    let productId = $('.quantity').data('product-id');
    if (quantities[productId]) {
        $('.quantity-input').val(quantities[productId]);
    } else {
        $('.quantity-input').val(1);
    }

    // Xử lý nút cộng/trừ
    $('.quantity button').on('click', function () {
        let $button = $(this);
        let $quantityContainer = $button.closest('.quantity');
        let $quantityInput = $quantityContainer.find('.quantity-input');
        let productId = $quantityContainer.data('product-id');
        let quantity = parseInt($quantityInput.val()) || 1;

        if ($button.hasClass('btn-plus')) {
            quantity++;
        } else if ($button.hasClass('btn-minus') && quantity > 1) {
            quantity--;
        }

        $quantityInput.val(quantity);
        quantities[productId] = quantity;
        localStorage.setItem('productQuantities', JSON.stringify(quantities));
    });

    // Đảm bảo ô input được cập nhật đúng trước khi submit form
    $('form').on('submit', function (event) {
        let $form = $(this);
        let productId = $form.find('.quantity').data('product-id');
        let $quantityInput = $form.find('.quantity-input');
        let currentQuantity = parseInt($quantityInput.val()) || 1;

        // Reset ô input về 1 sau khi submit
        $quantityInput.val(1);
        quantities[productId] = 1;
        localStorage.setItem('productQuantities', JSON.stringify(quantities));

        // Log để debug
        console.log("Form submit - ProductId: " + productId + ", Quantity: " + currentQuantity);
    });
});