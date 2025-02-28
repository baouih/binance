package poly.petshop.service;

import java.util.Date;
import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Service;

import jakarta.servlet.http.HttpSession;
import poly.petshop.domain.Cart;
import poly.petshop.domain.Product;
import poly.petshop.domain.User;
import poly.petshop.repository.CartRepository;
import poly.petshop.repository.ProductRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

@Service
public class ProductService {
    private final ProductRepository productRepository;
    private final CartRepository cartRepository;
    private final UserService userService;

    public ProductService(ProductRepository productRepository,
            CartRepository cartRepository,
            UserService userService) {
        this.productRepository = productRepository;
        this.cartRepository = cartRepository;
        this.userService = userService;
    }

    public List<Product> getAllProducts() {
        List<Product> products = this.productRepository.findAll();
        return products != null ? products : List.of(); // Trả về danh sách rỗng nếu `null`
    }

    public Page<Product> getAllProducts(Pageable pageable) {
        return productRepository.findAll(pageable);
    }

    public Page<Product> searchProductsByName(String keyword, Pageable pageable) {
        return productRepository.findByTenSPContainingIgnoreCase(keyword, pageable);
    }

    // public List<Category> getAllUsersByEmail(String email) {
    // return this.userRepository.findByEmail(email);
    // }
    public boolean skuExists(String sku) {
        return productRepository.existsBysku(sku);
    }

    public Optional<Product> getProductById(int productId) {
        return productRepository.findById(productId);
    }

    public Product handleSaveProduct(Product product) {
        Product pro = this.productRepository.save(product);
        System.out.println(pro);
        return pro;
    }

    public void deletetProductById(int productId) {
        this.productRepository.deleteById(productId);
    }

    public void handleCheckAndAddProductInCart(String email, int productId, int soLuongTrongGio) {
        User user = this.userService.getUserByEmail(email);
        Optional<Product> productOpt = this.productRepository.findById(productId);

        // Kiểm tra user có tồn tại không
        if (user == null) {
            throw new RuntimeException("Không tìm thấy user với email: " + email);
        }

        // Kiểm tra sản phẩm có tồn tại không
        if (productOpt.isEmpty()) {
            throw new RuntimeException("Không tìm thấy sản phẩm với ID: " + productId);
        }

        // Tạo product thật
        Product product = productOpt.get();

        // Kiểm tra sản phẩm đã có trong giỏ hàng chưa
        Optional<Cart> existingCartOpt = this.cartRepository.findCartByUserAndProduct(user, product);

        if (existingCartOpt.isPresent()) {
            // Get Cart thiệt
            // Nếu sản phẩm đã có trong giỏ hàng, cập nhật số lượng
            Cart existingCart = existingCartOpt.get();

            // Tăng lên 1 để k phải hiện 2 dòng row
            existingCart.setSoLuongTrongGio(existingCart.getSoLuongTrongGio() + soLuongTrongGio);

            // Tiến hành lưu giỏ
            this.cartRepository.save(existingCart);

            System.out.println("Đã cập nhật số lượng sản phẩm trong giỏ hàng.");
        } else {
            // Nếu chưa có trong giỏ hàng, tạo mới
            Cart newCart = new Cart();
            newCart.setUser(user);
            newCart.setProduct(product);
            newCart.setSoLuongTrongGio(soLuongTrongGio);
            newCart.setNgayThemGio(new Date());
            this.cartRepository.save(newCart);
            System.out.println("Đã thêm sản phẩm mới vào giỏ hàng.");
            user.setTotalQuantityInCart(user.getTotalQuantityInCart() + 1);
        }

    }

    public void removeProductFromCart(String email, int productId, HttpSession session) {
        User user = this.userService.getUserByEmail(email);
        Optional<Product> productOpt = this.productRepository.findById(productId);

        if (user == null) {
            throw new RuntimeException("Không tìm thấy user với email: " + email);
        }

        if (productOpt.isEmpty()) {
            throw new RuntimeException("Không tìm thấy sản phẩm với ID: " + productId);
        }

        Product product = productOpt.get();
        Optional<Cart> cartItem = cartRepository.findCartByUserAndProduct(user, product);
        if (cartItem.isPresent()) {
            // Xóa sản phẩm khỏi giỏ hàng
            cartRepository.deleteCartByUserAndProduct(user, product);

            // Kiểm tra số lượng sản phẩm trong giỏ hàng
            int newTotalQuantity;
            if (user.getTotalQuantityInCart() > 1) {
                newTotalQuantity = user.getTotalQuantityInCart() - 1;
            } else {
                newTotalQuantity = 0;
            }

            // Cập nhật totalQuantityInCart của user
            user.setTotalQuantityInCart(newTotalQuantity);
            userService.handleSaveUser(user); // Lưu lại vào database

            // Cập nhật session
            session.setAttribute("totalQuantityInCart", newTotalQuantity);
        }
    }

    // Sản phẩm bán chạy (giả sử slTonKho thấp = bán chạy)
    public List<Product> getBestSellingProducts(int limit) {
        return productRepository.findTopByOrderBySlTonKhoAsc(PageRequest.of(0, limit));
    }

    // Sản phẩm giảm giá
    public List<Product> getDiscountedProducts(int limit) {
        return productRepository.findByGiaGiamGreaterThan(0, PageRequest.of(0, limit));
    }

    // Sản phẩm mới
    public List<Product> getNewProducts(int limit) {
        return productRepository.findTopByOrderByNgayTaoDesc(PageRequest.of(0, limit));
    }

    // Tìm kiếm theo giá
    public Page<Product> searchByPriceRange(double minPrice, double maxPrice, Pageable pageable) {
        return productRepository.findByGiaBetween(minPrice, maxPrice, pageable);
    }
}
