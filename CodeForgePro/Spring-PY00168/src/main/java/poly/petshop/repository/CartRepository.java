package poly.petshop.repository;

import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import poly.petshop.domain.Cart;
import poly.petshop.domain.Product;
import poly.petshop.domain.User;

@Repository
public interface CartRepository extends JpaRepository<Cart, Integer> {
    Optional<Cart> findCartByUserAndProduct(User user, Product product);

    List<Cart> findByUser(User user);

    @Transactional
    @Modifying
    @Query("DELETE FROM Cart c WHERE c.user = :user AND c.product = :product")
    void deleteCartByUserAndProduct(@Param("user") User user, @Param("product") Product product);
}
