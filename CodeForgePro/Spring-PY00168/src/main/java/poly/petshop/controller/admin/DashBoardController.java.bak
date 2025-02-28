package poly.petshop.controller.admin;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import poly.petshop.service.OrderService;
import poly.petshop.service.ProductService;
import poly.petshop.service.UserService;

@Controller
public class DashBoardController {

    private final ProductService productService;
    private final OrderService orderService;
    private final UserService userService;

    public DashBoardController(ProductService productService, OrderService orderService, UserService userService) {
        this.productService = productService;
        this.orderService = orderService;
        this.userService = userService;
    }

    @GetMapping("/admin")
    public String getAdminPage(Model model) {
        // Thống kê cơ bản
        long totalProducts = productService.getAllProducts().size();
        long totalOrders = orderService.findAll().size();
        double totalRevenue = orderService.calculateTotalRevenue();
        long totalUsers = userService.getAllUsers().size();

        model.addAttribute("totalProducts", totalProducts);
        model.addAttribute("totalOrders", totalOrders);
        model.addAttribute("totalRevenue", totalRevenue);
        model.addAttribute("totalUsers", totalUsers);

        // Danh sách đơn hàng gần đây
        model.addAttribute("recentOrders", orderService.getRecentOrders(5));

        // Dữ liệu biểu đồ
        model.addAttribute("monthlyRevenueLabels",
                new String[] { "Th1", "Th2", "Th3", "Th4", "Th5", "Th6", "Th7", "Th8", "Th9", "Th10", "Th11", "Th12" });
        model.addAttribute("monthlyRevenueData", orderService.getMonthlyRevenue());
        model.addAttribute("monthlyOrderData", orderService.getMonthlyOrderCount());

        // Thống kê doanh thu theo loại hàng
        model.addAttribute("categoryStats", orderService.getRevenueByCategory());

        // Thống kê 10 khách hàng VIP
        model.addAttribute("vipCustomers", orderService.getTopVipCustomers());
        return "admin/dashboard/show";
    }
}