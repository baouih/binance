(function ($) {
    "use strict";

    // Spinner
    var spinner = function () {
        setTimeout(function () {
            if ($('#spinner').length > 0) {
                $('#spinner').removeClass('show');
            }
        }, 1);
    };
    spinner(0);


    // Fixed Navbar
    $(window).scroll(function () {
        if ($(window).width() < 992) {
            if ($(this).scrollTop() > 55) {
                $('.fixed-top').addClass('shadow');
            } else {
                $('.fixed-top').removeClass('shadow');
            }
        } else {
            if ($(this).scrollTop() > 55) {
                $('.fixed-top').addClass('shadow').css('top', 0);
            } else {
                $('.fixed-top').removeClass('shadow').css('top', 0);
            }
        } 
    });
    
    
   // Back to top button
   $(window).scroll(function () {
    if ($(this).scrollTop() > 300) {
        $('.back-to-top').fadeIn('slow');
    } else {
        $('.back-to-top').fadeOut('slow');
    }
    });
    $('.back-to-top').click(function () {
        $('html, body').animate({scrollTop: 0}, 1500, 'easeInOutExpo');
        return false;
    });


    // Testimonial carousel
    $(".testimonial-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 2000,
        center: false,
        dots: true,
        loop: true,
        margin: 25,
        nav : true,
        navText : [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ],
        responsiveClass: true,
        responsive: {
            0:{
                items:1
            },
            576:{
                items:1
            },
            768:{
                items:1
            },
            992:{
                items:2
            },
            1200:{
                items:2
            }
        }
    });


    // vegetable carousel
    $(".vegetable-carousel").owlCarousel({
        autoplay: true,
        smartSpeed: 1500,
        center: false,
        dots: true,
        loop: true,
        margin: 25,
        nav : true,
        navText : [
            '<i class="bi bi-arrow-left"></i>',
            '<i class="bi bi-arrow-right"></i>'
        ],
        responsiveClass: true,
        responsive: {
            0:{
                items:1
            },
            576:{
                items:1
            },
            768:{
                items:2
            },
            992:{
                items:3
            },
            1200:{
                items:4
            }
        }
    });


    // Modal Video
    $(document).ready(function () {
        var $videoSrc;
        $('.btn-play').click(function () {
            $videoSrc = $(this).data("src");
        });
        console.log($videoSrc);

        $('#videoModal').on('shown.bs.modal', function (e) {
            $("#video").attr('src', $videoSrc + "?autoplay=1&amp;modestbranding=1&amp;showinfo=0");
        })

        $('#videoModal').on('hide.bs.modal', function (e) {
            $("#video").attr('src', $videoSrc);
        })
    });



    // Product Quantity
    // $('.quantity button').on('click', function () {
    //     var button = $(this);
    //     var oldValue = button.parent().parent().find('input').val();
    //     if (button.hasClass('btn-plus')) {
    //         var newVal = parseFloat(oldValue) + 1;
    //     } else {
    //         if (oldValue > 0) {
    //             var newVal = parseFloat(oldValue) - 1;
    //         } else {
    //             newVal = 0;
    //         }
    //     }
    //     button.parent().parent().find('input').val(newVal);
    // });

    $(document).ready(function () {
        function updateTotalPrice() {
            let totalCartPrice = 0;
            let shippingFee = 30000; // Giả định phí vận chuyển là 30,000 Đ
    
            $(".quantity").each(function () {
                let $row = $(this).closest("tr");
                let price = parseFloat($row.data("price")); // Giá sản phẩm
                let quantity = parseInt($row.find(".quantity-input").val()); // Số lượng
                let total = price * quantity; // Tổng tiền từng sản phẩm
                $row.find(".total-price").text(total.toLocaleString() + " Đ"); // Cập nhật tổng tiền từng sản phẩm
    
                totalCartPrice += total; // Cộng dồn tổng tiền giỏ hàng
            });
    
            // Cập nhật tổng tiền tạm tính
            $(".subtotal-price").text(totalCartPrice.toLocaleString() + " Đ");
    
            // Cập nhật tổng tiền cuối cùng (cộng thêm phí ship)
            let finalTotal = totalCartPrice + shippingFee;
            $(".cart-total-price").text(finalTotal.toLocaleString() + " Đ");
        }
    
        // Xử lý khi nhấn nút tăng/giảm số lượng
        $('.quantity button').on('click', function () {
            let $button = $(this);
            let $row = $button.closest("tr");
            let $quantityInput = $row.find(".quantity-input");
            let quantity = parseInt($quantityInput.val());
    
            if ($button.hasClass('btn-plus')) {
                quantity++;
            } else {
                if (quantity > 1) { // Không cho giảm dưới 1
                    quantity--;
                }
            }
    
            $quantityInput.val(quantity); // Cập nhật số lượng
            updateTotalPrice(); // Cập nhật tổng tiền
        });
    
        // Cập nhật tổng tiền khi trang load
        updateTotalPrice();
    });
    $(document).ready(function () {
    $(".btn-remove").click(function () {
        let productId = $(this).data("id"); // Lấy ID sản phẩm cần xóa
        let $row = $(this).closest("tr"); // Lấy hàng chứa sản phẩm để xóa

        $.ajax({
            url: "/cart/remove/" + productId,
            type: "POST",
            success: function (response) {
                $row.remove(); // Xóa sản phẩm khỏi giao diện
                updateTotalPrice(); // Cập nhật lại tổng tiền
            },
            error: function (xhr) {
                alert("Lỗi khi xóa sản phẩm: " + xhr.responseText);
            }
        });
    });

    function updateTotalPrice() {
        let totalCartPrice = 0;
        $(".quantity").each(function () {
            let price = parseFloat($(this).closest("tr").data("price"));
            let quantity = parseInt($(this).find(".quantity-input").val());
            totalCartPrice += price * quantity;
        });

        $(".subtotal-price").text(totalCartPrice.toLocaleString() + " Đ");
        $(".cart-total-price").text((totalCartPrice + 30000).toLocaleString() + " Đ");

        // Ẩn toàn bộ phần tổng tiền nếu không còn sản phẩm nào
        if ($(".quantity").length === 0) {
            $("div:has(.cart-total-price)").hide();
        }
    }
});
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".delete-cart-item").forEach(button => {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            let productId = this.getAttribute("data-id");

            fetch(`/delete-cart-product/${productId}`, {
                method: "POST"
            }).then(response => {
                if (response.ok) {
                    window.location.reload(); // Reload trang sau khi xóa
                }
            }).catch(error => console.error("Lỗi khi xóa sản phẩm:", error));
        });
    });
});
    
})(jQuery);

