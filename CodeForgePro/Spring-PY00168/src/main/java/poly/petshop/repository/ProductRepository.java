package poly.petshop.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import poly.petshop.domain.Product;

@Repository
public interface ProductRepository extends JpaRepository<Product, Integer> {
    Product save(Product product);

    void deleteById(int productId);

    boolean existsBysku(String sku);

    List<Product> findAll();

    Optional<Product> findById(int productId);

    // Phân trang tất cả sản phẩm
    Page<Product> findAll(Pageable pageable);

    // Tìm kiếm sản phẩm theo tên (không phân biệt hoa thường)
    @Query("SELECT p FROM Product p WHERE LOWER(p.tenSP) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    Page<Product> findByTenSPContainingIgnoreCase(String keyword, Pageable pageable);

    List<Product> findTopByOrderBySlTonKhoAsc(Pageable pageable); // Bán chạy

    List<Product> findByGiaGiamGreaterThan(double giaGiam, Pageable pageable); // Giảm giá

    List<Product> findTopByOrderByNgayTaoDesc(Pageable pageable); // Hàng mới

    Page<Product> findByGiaBetween(double minPrice, double maxPrice, Pageable pageable); // Tìm theo giá

}
