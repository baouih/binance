package poly.petshop.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import poly.petshop.domain.Order;
import poly.petshop.domain.User;

import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, Integer> {
    List<Order> findByUser(User user);

    Order findByOrderId(int orderId);

    Order save(Order order);

    void deleteById(int orderId);

    // Lấy 5 đơn hàng gần đây
    List<Order> findTop5ByOrderByNgayOrderDesc();

    // Tính doanh thu theo tháng trong năm hiện tại
    @Query("SELECT MONTH(o.ngayOrder), SUM(o.tongGiaTri) FROM Order o " +
            "WHERE YEAR(o.ngayOrder) = YEAR(CURRENT_DATE) GROUP BY MONTH(o.ngayOrder)")
    List<Object[]> findMonthlyRevenue();

    // Đếm số đơn hàng theo tháng trong năm hiện tại
    @Query("SELECT MONTH(o.ngayOrder), COUNT(o) FROM Order o " +
            "WHERE YEAR(o.ngayOrder) = YEAR(CURRENT_DATE) GROUP BY MONTH(o.ngayOrder)")
    List<Object[]> findMonthlyOrderCount();
}
