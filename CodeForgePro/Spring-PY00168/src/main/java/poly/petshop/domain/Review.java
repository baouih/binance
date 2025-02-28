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

@Entity
@Table(name = "reviews")
public class Review implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int reviewId;

    @Column(nullable = false)
    private int xepHangDG;

    @Column(nullable = true, columnDefinition = "NVARCHAR(1000)")
    private String nDungDanhGia;

    @Column(nullable = false)
    private Date ngayDanhGia;

    // many reviews to one user
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "userId", nullable = false)
    private User user;

    // many reviews to one product
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "productId", nullable = false)
    private Product product;

    public Review(int reviewId, int xepHangDG, String nDungDanhGia, Date ngayDanhGia, User user, Product product) {
        this.reviewId = reviewId;
        this.xepHangDG = xepHangDG;
        this.nDungDanhGia = nDungDanhGia;
        this.ngayDanhGia = ngayDanhGia;
        this.user = user;
        this.product = product;
    }

    public Review() {
    }

    public int getReviewId() {
        return reviewId;
    }

    public void setReviewId(int reviewId) {
        this.reviewId = reviewId;
    }

    public int getXepHangDG() {
        return xepHangDG;
    }

    public void setXepHangDG(int xepHangDG) {
        this.xepHangDG = xepHangDG;
    }

    public String getnDungDanhGia() {
        return nDungDanhGia;
    }

    public void setnDungDanhGia(String nDungDanhGia) {
        this.nDungDanhGia = nDungDanhGia;
    }

    public Date getNgayDanhGia() {
        return ngayDanhGia;
    }

    public void setNgayDanhGia(Date ngayDanhGia) {
        this.ngayDanhGia = ngayDanhGia;
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
