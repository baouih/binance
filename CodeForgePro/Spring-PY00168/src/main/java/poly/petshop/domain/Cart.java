package poly.petshop.domain;

import java.io.Serializable;
import java.util.Date;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.validation.constraints.Min;

@Entity
@Table(name = "carts")
public class Cart implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int cartId;

    @Column(nullable = false)
    @Min(value = 0)
    private int soLuongTrongGio;

    @Column(nullable = false)
    private Date ngayThemGio;

    // many carts to one user
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "userId", nullable = false)
    private User user;

    // many carts to one product
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "productId", nullable = false)
    private Product product;

    public Cart() {
    }

    public Cart(int cartId, int soLuongTrongGio, Date ngayThemGio, User user, Product product) {
        this.cartId = cartId;
        this.soLuongTrongGio = soLuongTrongGio;
        this.ngayThemGio = ngayThemGio;
        this.user = user;
        this.product = product;
    }

    @Override
    public String toString() {
        return "Cart [cartId=" + cartId + ", soLuongTrongGio=" + soLuongTrongGio + ", ngayThemGio=" + ngayThemGio + "]";
    }

    public int getCartId() {
        return cartId;
    }

    public void setCartId(int cartId) {
        this.cartId = cartId;
    }

    public int getSoLuongTrongGio() {
        return soLuongTrongGio;
    }

    public void setSoLuongTrongGio(int soLuongTrongGio) {
        this.soLuongTrongGio = soLuongTrongGio;
    }

    public Date getNgayThemGio() {
        return ngayThemGio;
    }

    public void setNgayThemGio(Date ngayThemGio) {
        this.ngayThemGio = ngayThemGio;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public Product getProduct() {
        return product;
    }

    public void setProduct(Product product) {
        this.product = product;
    }

}
