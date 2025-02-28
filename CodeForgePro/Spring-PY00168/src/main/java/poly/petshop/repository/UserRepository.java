package poly.petshop.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import poly.petshop.domain.User;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

@Repository
public interface UserRepository extends JpaRepository<User, Integer> {

    User save(User eric);

    void deleteById(int userId);

    List<User> findAll();

    User findById(int userId);

    List<User> findByEmail(String email);

    boolean existsByEmail(String email);

    boolean existsBySoDienThoai(String phone);

    boolean existsByEmailAndUserIdNot(String email, int userId);

    boolean existsBySoDienThoaiAndUserIdNot(String soDienThoai, int userId);

    User findUserByEmail(String email);

    Optional<User> findByGoogleId(String googleId);

    // Phân trang tất cả người dùng
    Page<User> findAll(Pageable pageable);

    // Tìm kiếm người dùng theo email hoặc họ và tên (không phân biệt hoa thường)
    @Query("SELECT u FROM User u WHERE LOWER(u.email) LIKE LOWER(CONCAT('%', :keyword, '%')) " +
            "OR LOWER(u.hoVaTen) LIKE LOWER(CONCAT('%', :keyword, '%'))")
    Page<User> findByEmailOrHoVaTenContainingIgnoreCase(String keyword, Pageable pageable);

    User findByActivationCode(String activationCode);
}
