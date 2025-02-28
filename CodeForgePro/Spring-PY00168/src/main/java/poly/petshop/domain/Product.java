package poly.petshop.domain;

import java.io.Serializable;
import java.util.Date;
import java.util.List;

import org.hibernate.validator.constraints.Length;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

@Entity
@Table(name = "products")
public class Product implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int productId;

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    @NotEmpty(message = "Tên sản phẩm không được để trống")
    @Size(min = 3, message = "Tên sản phẩm phải có ít nhất 3 ký tự")
    private String tenSP;

    @Column(nullable = false, columnDefinition = "NVARCHAR(1000)")
    @NotEmpty(message = "Mô tả sản phẩm không được để trống")
    @Size(max = 1000, message = "Mô tả sản phẩm không quá 1000 ký tự")
    private String moTaSP;

    @Column(nullable = false, columnDefinition = "NVARCHAR(1000)")
    @Size(max = 1000, message = "Mô tả ngắn không quá 1000 ký tự")
    @NotEmpty(message = "Mô tả ngắn sản phẩm không được để trống")
    private String moTaNganSP;

    @Column(nullable = true)
    private Double giaGiam;

    @Column(nullable = true, columnDefinition = "NVARCHAR(255)")
    private String imageURL;

    @Column(nullable = false, unique = true)
    @NotEmpty(message = "SKU không được để trống")
    private String sku;

    @Column(nullable = false)
    @Min(value = 0, message = "Số lượng tồn kho không thể nhỏ hơn 0")
    private int slTonKho;

    @Column(nullable = true)
    @DecimalMin(value = "0.0", message = "Thuế không thể nhỏ hơn 0")
    private float thue;

    @Column(name = "ngay_tao")
    private Date ngayTao;

    @Column(nullable = false)
    @DecimalMin(value = "0.01", message = "Giá sản phẩm phải lớn hơn 0")
    private float gia;

    // many product to one category
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "categoryId")
    private Category category;

    // many products to one supplier
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "supplierId")
    private Supplier supplier;

    // one product to many orderdetails
    @OneToMany(mappedBy = "product", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<OrderDetail> orderDetails;

    // one product to many reviews
    @OneToMany(mappedBy = "product", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Review> reviews;

    @OneToMany(mappedBy = "product", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<CampaignProduct> campaignProducts;

    @OneToMany(mappedBy = "product", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Cart> carts;

    public Product(int productId, String tenSP, @Length(min = 3, max = 1000) String moTaSP,
            @Length(min = 3, max = 1000) String moTaNganSP, String imageURL, String sku, int slTonKho, float thue,
            float gia, Category category, Supplier supplier, List<OrderDetail> orderDetails, List<Review> reviews,
            List<CampaignProduct> campaignProducts, List<Cart> carts) {
        this.productId = productId;
        this.tenSP = tenSP;
        this.moTaSP = moTaSP;
        this.moTaNganSP = moTaNganSP;
        this.imageURL = imageURL;
        this.sku = sku;
        this.slTonKho = slTonKho;
        this.thue = thue;
        this.gia = gia;
        this.category = category;
        this.supplier = supplier;
        this.orderDetails = orderDetails;
        this.reviews = reviews;
        this.campaignProducts = campaignProducts;
        this.carts = carts;
    }

    @Override
    public String toString() {
        return "Product [productId=" + productId + ", tenSP=" + tenSP + ", moTaSP=" + moTaSP + ", moTaNganSP="
                + moTaNganSP + ", imageURL=" + imageURL + ", sku=" + sku + ", slTonKho=" + slTonKho + ", thue=" + thue
                + ", gia=" + gia + "]";
    }

    public Product() {
    }

    public Date getNgayTao() {
        return ngayTao;
    }

    public void setNgayTao(Date ngayTao) {
        this.ngayTao = ngayTao;
    }

    public double getGiaGiam() {
        return giaGiam;
    }

    public void setGiaGiam(double giaGiam) {
        this.giaGiam = giaGiam;
    }

    public int getProductId() {
        return productId;
    }

    public void setProductId(int productId) {
        this.productId = productId;
    }

    public String getTenSP() {
        return tenSP;
    }

    public void setTenSP(String tenSP) {
        this.tenSP = tenSP;
    }

    public String getMoTaSP() {
        return moTaSP;
    }

    public void setMoTaSP(String moTaSP) {
        this.moTaSP = moTaSP;
    }

    public String getImageURL() {
        return imageURL;
    }

    public void setImageURL(String imageURL) {
        this.imageURL = imageURL;
    }

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public int getSlTonKho() {
        return slTonKho;
    }

    public void setSlTonKho(int slTonKho) {
        this.slTonKho = slTonKho;
    }

    public float getThue() {
        return thue;
    }

    public void setThue(float thue) {
        this.thue = thue;
    }

    public Category getCategory() {
        return category;
    }

    public void setCategory(Category category) {
        this.category = category;
    }

    public Supplier getSupplier() {
        return supplier;
    }

    public void setSupplier(Supplier supplier) {
        this.supplier = supplier;
    }

    public List<OrderDetail> getOrderDetails() {
        return orderDetails;
    }

    public void setOrderDetails(List<OrderDetail> orderDetails) {
        this.orderDetails = orderDetails;
    }

    public List<Review> getReviews() {
        return reviews;
    }

    public void setReviews(List<Review> reviews) {
        this.reviews = reviews;
    }

    public List<CampaignProduct> getCampaignProducts() {
        return campaignProducts;
    }

    public void setCampaignProducts(List<CampaignProduct> campaignProducts) {
        this.campaignProducts = campaignProducts;
    }

    public float getGia() {
        return gia;
    }

    public void setGia(float gia) {
        this.gia = gia;
    }

    public String getMoTaNganSP() {
        return moTaNganSP;
    }

    public void setMoTaNganSP(String moTaNganSP) {
        this.moTaNganSP = moTaNganSP;
    }

    public List<Cart> getCarts() {
        return carts;
    }

    public void setCarts(List<Cart> carts) {
        this.carts = carts;
    }

}
