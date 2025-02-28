package poly.petshop.controller.admin;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import org.springframework.stereotype.Controller;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

import jakarta.servlet.http.HttpServletRequest;
import poly.petshop.domain.Order;
import poly.petshop.domain.OrderDetail;
import poly.petshop.domain.Product;
import poly.petshop.domain.User;
import poly.petshop.repository.OrderDetailRepository;
import poly.petshop.service.OrderService;
import poly.petshop.service.ProductService;
import poly.petshop.service.UserService;

@Controller
public class OrderController {

    private final OrderService orderService;
    private final UserService userService;
    private final ProductService productService;
    private final OrderDetailRepository orderDetailRepository;

    public OrderController(OrderService orderService, UserService userService, ProductService productService,
            OrderDetailRepository orderDetailRepository) {
        this.orderService = orderService;
        this.userService = userService;
        this.productService = productService;
        this.orderDetailRepository = orderDetailRepository;
    }

    @GetMapping("/admin/order")
    public String getOrderPage(Model model) {
        model.addAttribute("orders", orderService.findAll());
        return "admin/order/show";
    }

    @GetMapping("/admin/order/{orderId}")
    public String getOneOrderPage(Model model, @PathVariable("orderId") int orderId) {
        Order order = orderService.findbyOrders(orderId);

        model.addAttribute("order", order);
        model.addAttribute("orderDetails", order.getOrderDetails());
        model.addAttribute("orderId", orderId);
        return "admin/order/detail";
    }

    @GetMapping("/admin/order/create")
    public String OrderPageCreate(@ModelAttribute("order") Order order, Model model) {
        model.addAttribute("users", userService.getAllUsers());
        model.addAttribute("products", productService.getAllProducts());
        return "admin/order/create";
    }

    @PostMapping("/admin/order/create")
    public String PageAlreadyCreateOrder(@ModelAttribute("order") Order order, Model model,
            HttpServletRequest request) {
        // kiem tra chon user
        User orderUser = null;
        if (order.getUser() != null) {
            orderUser = this.userService.getUserById(order.getUser().getUserId());
        }

        order.setUser(orderUser);
        order.setNgayOrder(new Date());
        order.setTrangThai("PROCESSING");

        // Tạo đơn hàng trước khi thêm sản phẩm vào
        Order newOrder = this.orderService.handleSaveOrder(order);
        // Xử lý thêm sản phẩm vào đơn hàng
        List<OrderDetail> orderDetails = new ArrayList<>();
        List<Integer> selectedProductIds = order.getSelectedProductIds();
        float[] totalPrice = { 0 };
        if (selectedProductIds == null) {
            selectedProductIds = new ArrayList<>();
        }

        for (Integer productId : selectedProductIds) {
            productService.getProductById(productId).ifPresent(product -> {
                OrderDetail orderDetail = new OrderDetail();
                orderDetail.setOrder(newOrder);
                orderDetail.setProduct(product);
                orderDetail.setSoLuong(1); // Admin có thể chỉnh sửa số lượng sau
                orderDetail.setDonGia(product.getGia());
                orderDetail.setTongGia(product.getGia() * orderDetail.getSoLuong());
                // Cộng dồn tổng giá trị
                totalPrice[0] += orderDetail.getTongGia();
                orderDetails.add(orderDetail);
            });
        }

        orderDetailRepository.saveAll(orderDetails);
        newOrder.setTongGiaTri(totalPrice[0]); // Lấy giá trị từ mảng float[]
        orderService.handleSaveOrder(newOrder);

        return "redirect:/admin/order";
    }

    @GetMapping("/admin/order/update/{orderId}")
    public String getOrderUpdatePage(@PathVariable("orderId") int orderId, Model model) {
        Order order = orderService.findbyOrders(orderId);
        if (order == null) {
            return "redirect:/admin/order";
        }

        model.addAttribute("order", order);
        model.addAttribute("users", userService.getAllUsers());
        model.addAttribute("products", productService.getAllProducts());
        return "admin/order/update";
    }

    @PostMapping("/admin/order/update")
    @Transactional
    public String updateOrder(@ModelAttribute("order") Order updatedOrder, @RequestParam("orderId") int orderId) {
        Order existingOrder = orderService.findbyOrders(orderId);

        if (existingOrder == null) {
            return "redirect:/admin/order";
        }

        // Chỉ cập nhật trạng thái đơn hàng
        existingOrder.setTrangThai(updatedOrder.getTrangThai());

        // Xóa các OrderDetail cũ (nếu cần cập nhật lại danh sách sản phẩm)
        existingOrder.getOrderDetails().clear();
        orderService.handleSaveOrder(existingOrder);

        float totalPrice = 0;
        for (OrderDetail detail : updatedOrder.getOrderDetails()) {
            Product product = productService.getProductById(detail.getProduct().getProductId()).orElse(null);
            if (product != null) {
                detail.setOrder(existingOrder);
                detail.setProduct(product);
                detail.setDonGia(product.getGia());
                detail.setTongGia(detail.getSoLuong() * product.getGia());
                totalPrice += detail.getTongGia();
                existingOrder.getOrderDetails().add(detail);
            }
        }

        existingOrder.setTongGiaTri(totalPrice);
        orderService.handleSaveOrder(existingOrder);

        return "redirect:/admin/order";
    }

    // Trang delete order
    @GetMapping("/admin/order/delete/{orderId}")
    public String GetOrderDeletePage(@PathVariable("orderId") int orderId, Model model) {
        Order order = orderService.findbyOrders(orderId);
        model.addAttribute("order", order);
        model.addAttribute("orderId", orderId);
        return "admin/order/delete";
    }

    @PostMapping("/admin/order/delete")
    public String PostOrderDeletePage(@RequestParam("orderId") int orderId) {
        orderService.deleteOrder(orderId);
        return "redirect:/admin/order";
    }

}
