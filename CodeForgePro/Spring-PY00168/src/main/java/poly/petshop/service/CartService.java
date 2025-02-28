package poly.petshop.service;

import java.util.Optional;

import org.springframework.stereotype.Service;

import poly.petshop.domain.Cart;
import poly.petshop.domain.Product;
import poly.petshop.domain.User;
import poly.petshop.repository.CartRepository;

@Service
public class CartService {
    private final CartRepository cartRepository;

    public CartService(CartRepository cartRepository) {
        this.cartRepository = cartRepository;
    }

    public Optional<Cart> findCartByUserAndProduct(User user, Product product) {
        return this.cartRepository.findCartByUserAndProduct(user, product);
    }
}
