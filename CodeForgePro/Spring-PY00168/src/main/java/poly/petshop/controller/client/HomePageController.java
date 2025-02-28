package poly.petshop.controller.client;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import poly.petshop.domain.Product;
import poly.petshop.service.ProductService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

@Controller
public class HomePageController {

    private final ProductService productService;

    public HomePageController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping("/")
    public String getHomePage(Model model,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "8") int size) {

        // Phân trang
        Pageable pageable = PageRequest.of(page, size, Sort.by("productId").ascending());

        // Tất cả sản phẩm
        Page<Product> allProducts = productService.getAllProducts(pageable);

        // Truyền dữ liệu vào model
        model.addAttribute("allProducts", allProducts.getContent());
        model.addAttribute("currentPage", allProducts.getNumber());
        model.addAttribute("totalPages", allProducts.getTotalPages());

        return "client/homepage/index";
    }

    @GetMapping("/shop")
    public String getShoppingPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "9") int size,
            @RequestParam(defaultValue = "productId") String sortBy,
            @RequestParam(defaultValue = "asc") String direction,
            @RequestParam(defaultValue = "") String keyword,
            Model model) {

        Sort sort = Sort.by(direction.equals("asc") ? Sort.Direction.ASC : Sort.Direction.DESC, sortBy);
        Pageable pageable = PageRequest.of(page, size, sort);

        Page<Product> productPage;
        if (keyword.isEmpty()) {
            productPage = productService.getAllProducts(pageable);
        } else {
            productPage = productService.searchProductsByName(keyword, pageable);
        }

        model.addAttribute("products", productPage.getContent());
        model.addAttribute("currentPage", productPage.getNumber());
        model.addAttribute("totalPages", productPage.getTotalPages());
        model.addAttribute("totalElements", productPage.getTotalElements());
        model.addAttribute("sortBy", sortBy);
        model.addAttribute("direction", direction);
        model.addAttribute("keyword", keyword);

        return "client/pagechualamcontroller/shop";
    }

    @GetMapping("/404")
    public String getMy404Page() {
        return "client/pagechualamcontroller/404";
    }

    @GetMapping("/contact")
    public String getMycontactPage() {
        return "client/contact/contact";
    }
}