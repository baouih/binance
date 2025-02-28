package poly.petshop.controller.client;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

import poly.petshop.domain.Product;
import poly.petshop.service.ProductService;

@Controller
public class HomeProductController {
    private final ProductService productService;

    public HomeProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping("/product/{productId}")
    public String getHomeProduct(Model model, @PathVariable("productId") int productId) {
        Optional<Product> optionalProduct = productService.getProductById(productId);
        if (optionalProduct.isPresent()) {
            model.addAttribute("product", optionalProduct.get());
        } else {
            model.addAttribute("error", "Sản phẩm không tồn tại!");
        }
        model.addAttribute("productId", productId);
        List<Product> products = this.productService.getAllProducts();
        model.addAttribute("products", products);
        return "client/product/detail";
    }
}
