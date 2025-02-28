package poly.petshop.controller.admin;

import java.io.IOException;
import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;

import jakarta.validation.Valid;
import poly.petshop.domain.Category;
import poly.petshop.domain.Product;
import poly.petshop.domain.Supplier;
import poly.petshop.service.CategorySevice;
import poly.petshop.service.ProductService;
import poly.petshop.service.SupplierService;
import poly.petshop.service.UploadService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;

@Controller
public class ProductController {

    private final UploadService uploadService; // Inject UploadService
    private final ProductService productService;
    private final CategorySevice categorySevice;
    private final SupplierService supplierService;

    // Tiem DI viet dai
    public ProductController(
            ProductService productService,
            UploadService uploadService,
            CategorySevice categorySevice,
            SupplierService supplierService) {
        this.productService = productService;
        this.uploadService = uploadService;
        this.categorySevice = categorySevice;
        this.supplierService = supplierService;
    }

    @GetMapping("/admin/product")
    public String ProductPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "5") int size,
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

        return "admin/product/show";
    }

    @GetMapping("/admin/product/{productId}")
    public String GetProductDetailPage(@PathVariable("productId") int productId, Model model) {
        Optional<Product> product = productService.getProductById(productId);
        if (product.isPresent()) {
            model.addAttribute("product", product.get());
        }
        model.addAttribute("productId", productId);
        return "admin/product/detail";
    }

    // Trang tạo mới user
    @GetMapping("/admin/product/create")
    public String ProductPageCreate(@ModelAttribute("product") Product product, Model model) {
        List<Category> categories = categorySevice.getAllCategories();
        List<Supplier> suppliers = supplierService.getAllSuppliers();

        // Thêm danh sách vào model để sử dụng trong view
        model.addAttribute("categories", categories);
        model.addAttribute("suppliers", suppliers);
        return "admin/product/create";
    }

    // Table user đã tạo
    @PostMapping("/admin/product/create")
    public String PageAlreadyProductUser(@ModelAttribute("product") @Valid Product product,
            BindingResult newProductBindingResult, Model model,
            @RequestParam("image") MultipartFile file) throws IOException {

        System.out.println("Product Created: " + product.toString());
        // validate
        List<FieldError> errors = newProductBindingResult.getFieldErrors();
        for (FieldError error : errors) {
            System.out.println(error.getField() + " - " + error.getDefaultMessage());
        }
        if (newProductBindingResult.hasErrors()) {
            List<Category> categories = categorySevice.getAllCategories();
            List<Supplier> suppliers = supplierService.getAllSuppliers();

            // Thêm danh sách vào model để sử dụng trong view
            model.addAttribute("categories", categories);
            model.addAttribute("suppliers", suppliers);

            return "admin/product/create";
        }
        if (productService.skuExists(product.getSku())) {
            List<Category> categories = categorySevice.getAllCategories();
            List<Supplier> suppliers = supplierService.getAllSuppliers();

            // Thêm danh sách vào model để sử dụng trong view
            model.addAttribute("categories", categories);
            model.addAttribute("suppliers", suppliers);

            model.addAttribute("error", "SKU đã tồn tại! Vui lòng nhập SKU khác.");
            return "admin/product/create";
        }
        // Lấy đối tượng đầy đủ từ ID đã được gửi từ form
        Category category = categorySevice.getCategoryById(product.getCategory().getCategoryId());
        Supplier supplier = supplierService.getSupplierById(product.getSupplier().getSupplierId());

        // Gán Category và Supplier cho Product
        product.setCategory(category);
        product.setSupplier(supplier);
        // Thư mục lưu avatar
        String avatarDirectory = System.getProperty("user.dir") + "/src/main/resources/static/images/product";
        // Sau khi tiêm xong thì lấy ra xài
        String fileName = uploadService.handleSaveFile(file, avatarDirectory);
        product.setImageURL(fileName.toString());
        this.productService.handleSaveProduct(product);

        // thông báo
        model.addAttribute("msg", "Product created successfully with avatar: " +
                fileName);

        return "redirect:/admin/product"; // Điều hướng về trang user
    }

    // Trang update product
    @GetMapping("/admin/product/update/{productId}")
    public String GetProductUpdatePage(@PathVariable("productId") int productId, Model model) {
        Optional<Product> currentProduct = productService.getProductById(productId);
        if (currentProduct.isPresent()) {
            model.addAttribute("product", currentProduct.get());
        }
        model.addAttribute("productId", productId);

        List<Category> categories = categorySevice.getAllCategories();
        List<Supplier> suppliers = supplierService.getAllSuppliers();

        // Thêm danh sách vào model để sử dụng trong view
        model.addAttribute("categories", categories);
        model.addAttribute("suppliers", suppliers);
        return "admin/product/update";
    }

    @PostMapping("/admin/product/update")
    public String PostProductUpdatePage(@ModelAttribute("product") Product thisProduct, Model model,
            @RequestParam("image") MultipartFile file) throws IOException {
        Optional<Product> currentProductOpt = productService.getProductById(thisProduct.getProductId());
        if (currentProductOpt.isPresent()) {
            Product currentProduct = currentProductOpt.get();
            if (!file.isEmpty()) {
                // Thư mục lưu avatar
                String avatarDirectory = System.getProperty("user.dir") + "/src/main/resources/static/images/product";
                // Sau khi tiêm xong thì lấy ra xài
                String fileName = uploadService.handleSaveFile(file, avatarDirectory);
                currentProduct.setImageURL(fileName);
            }
            // // Kiểm tra email đã tồn tại nhưng bỏ qua chính user hiện tại
            // if (userService.emailExists(thisUser.getEmail(), thisUser.getUserId())) {
            // model.addAttribute("userRoles", List.of("Admin", "User"));
            // model.addAttribute("options", List.of("Nam", "Nữ"));
            // model.addAttribute("error", "Email đã được sử dụng! Vui lòng chọn email
            // khác.");
            // return "admin/user/update";
            // }

            // // Kiểm tra số điện thoại đã tồn tại nhưng bỏ qua chính user hiện tại
            // if (userService.phoneExists(thisUser.getSoDienThoai(), thisUser.getUserId()))
            // {
            // model.addAttribute("userRoles", List.of("Admin", "User"));
            // model.addAttribute("options", List.of("Nam", "Nữ"));
            // model.addAttribute("errorSDT", "Số điện thoại đã được sử dụng! Vui lòng nhập
            // số khác.");
            // return "admin/user/update";
            // }
            currentProduct.setTenSP(thisProduct.getTenSP());
            currentProduct.setMoTaSP(thisProduct.getMoTaSP());
            currentProduct.setMoTaNganSP(thisProduct.getMoTaNganSP());
            currentProduct.setSku(thisProduct.getSku());
            currentProduct.setSlTonKho(thisProduct.getSlTonKho());
            currentProduct.setThue(thisProduct.getThue());
            currentProduct.setGia(thisProduct.getGia());
            // Lấy đối tượng đầy đủ từ ID đã được gửi từ form
            Category category = categorySevice.getCategoryById(thisProduct.getCategory().getCategoryId());
            Supplier supplier = supplierService.getSupplierById(thisProduct.getSupplier().getSupplierId());

            // Gán Category và Supplier cho Product
            currentProduct.setCategory(category);
            currentProduct.setSupplier(supplier);
            this.productService.handleSaveProduct(currentProduct);

        }
        return "redirect:/admin/product";
    }

    // Trang delete product
    @GetMapping("/admin/product/delete/{productId}")
    public String GetProductDeletePage(@PathVariable("productId") int productId, Model model) {
        Optional<Product> productOpt = productService.getProductById(productId);
        if (productOpt.isPresent()) {
            model.addAttribute("product", productOpt.get());
        } else {
            model.addAttribute("error", "Sản phẩm không tồn tại!");
        }

        model.addAttribute("productId", productId);
        return "admin/product/delete";
    }

    @PostMapping("/admin/product/delete")
    public String PostProductDeletePage(@ModelAttribute("product") Product thisProduct, Model model) {
        this.productService.deletetProductById(thisProduct.getProductId());
        return "redirect:/admin/product";
    }

}

// @RestController
// public class UserController {

// // DI: dependence injection
// private UserService userService;

// public UserController(UserService userService) {
// this.userService = userService;
// }

// @GetMapping("")
// public String getHomePage() {
// return this.userService.handleHello();
// }
// }