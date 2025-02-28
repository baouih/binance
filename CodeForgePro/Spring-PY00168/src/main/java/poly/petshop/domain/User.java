package poly.petshop.domain;

import java.io.Serializable;
import java.util.Date;
import java.util.List;

import org.springframework.format.annotation.DateTimeFormat;

import com.fasterxml.jackson.annotation.JsonIgnore;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Null;
import jakarta.validation.constraints.Past;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

@Entity
@Table(name = "users")
public class User implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int userId;

    @Column(nullable = false, unique = true, columnDefinition = "NVARCHAR(255)")
    @Email(message = "Email không hợp lệ. Vui lòng nhập email đúng định dạng (ví dụ: user@example.com)", regexp = "^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\\.[a-zA-Z]{2,}$")
    @NotEmpty(message = "Email không được để trống")
    private String email;

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    @NotEmpty(message = "Mật khẩu không được để trống")
    @Size(min = 8, max = 100, message = "Mật khẩu phải từ 8 đến 100 ký tự")
    @Pattern(regexp = "^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d)(?=.*[@#$%^&+=!]).{8,}$", message = "Mật khẩu phải chứa ít nhất một chữ cái in hoa, một chữ cái thường, một số, và một ký tự đặc biệt (@, #, $, %, ^, &, +, =, !)")
    @JsonIgnore
    private String matKhau;

    @Column(nullable = true)
    @DateTimeFormat(pattern = "yyyy-MM-dd")
    @Past(message = "Ngày sinh không hợp lệ (phải nhỏ hơn ngày hiện tại)")
    private Date ngaySinh;

    @Column(nullable = true, columnDefinition = "NVARCHAR(255)")
    private String gioiTinh;
    // Thêm trường displayMatKhau để hiển thị "********"
    private String displayMatKhau;
    // @Column(nullable = false)
    @DateTimeFormat(pattern = "yyyy-MM-dd")
    private Date ngayTaoAcc = new Date();

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    @NotEmpty(message = "Vai trò người dùng không được để trống. Vui lòng chọn Admin hoặc User")
    private String userRole = "User";

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    @NotEmpty(message = "Họ và tên không được để trống")
    @Size(min = 2, max = 255, message = "Họ và tên phải từ 2 đến 255 ký tự")
    @Pattern(regexp = "^[a-zA-Z_ÀÁÂÃÈÉÊẾÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêếìíòóôõùúăđĩũơƯĂẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂưăạảấầẩẫậắằẳẵặẹẻẽềềểỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪễệỉịọỏốồổỗộớờởỡợụủứừỬỮỰỲỴÝỶỸửữựỳỵỷỹ\\ ]+$", message = "Họ và tên không hợp lệ. Chỉ được chứa chữ cái tiếng Việt, không dấu hoặc có dấu, và khoảng trắng (ví dụ: Nguyễn Văn Hùng)")
    private String hoVaTen;

    @Column(nullable = true, columnDefinition = "NVARCHAR(15)", unique = true)
    @Pattern(regexp = "^0[1-9][0-9]{8,9}$", message = "Số điện thoại không hợp lệ. Phải bắt đầu bằng 0 và có từ 10 đến 11 chữ số (ví dụ: 0987654321)")
    private String soDienThoai;

    @Column(nullable = true, columnDefinition = "NVARCHAR(255)")
    private String diaChi;
    @Column(nullable = false, columnDefinition = "BIT DEFAULT 0")
    private boolean activated = false;
    @Column(length = 100)
    private String activationCode;
    @Column
    private Integer totalQuantityInCart = 0;

    @Column(nullable = true, columnDefinition = "NVARCHAR(255)")
    private String avatar;

    // One user --> to many --> orders
    @OneToMany(mappedBy = "user", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Order> orders;

    // One user --> to many --> payments
    @OneToMany(mappedBy = "user", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Payment> payments;

    // One user --> to many --> reviews
    @OneToMany(mappedBy = "user", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Review> reviews;

    // One user --> to many --> carts
    @OneToMany(mappedBy = "user", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Cart> carts;

    public boolean isActivated() {
        return activated;
    }

    public void setActivated(boolean activated) {
        this.activated = activated;
    }

    public String getActivationCode() {
        return activationCode;
    }

    public void setActivationCode(String activationCode) {
        this.activationCode = activationCode;
    }

    public String getDisplayMatKhau() {
        return displayMatKhau;
    }

    public void setDisplayMatKhau(String displayMatKhau) {
        this.displayMatKhau = displayMatKhau;
    }

    private String googleId;

    public String getGoogleId() {
        return googleId;
    }

    public void setGoogleId(String googleId) {
        this.googleId = googleId;
    }

    public User() {
    }

    @Override
    public String toString() {
        return "User [userId=" + userId + ", email=" + email + ", matKhau=" + matKhau + ", ngaySinh=" + ngaySinh
                + ", gioiTinh=" + gioiTinh + ", ngayTaoAcc=" + ngayTaoAcc + ", userRole=" + userRole + ", hoVaTen="
                + hoVaTen + ", soDienThoai=" + soDienThoai + ", diaChi=" + diaChi + ", totalQuantityInCart="
                + totalQuantityInCart + ", avatar=" + avatar + ", googleId=" + googleId + "]";
    }

    public User(int userId,
            @Email(message = "Email không hợp lệ", regexp = "^[a-zA-Z0-9_!#$%&'*+/=?`{|}~^.-]+@[a-zA-Z0-9.-]+$") @NotEmpty(message = "Email không được để trống") String email,
            @NotEmpty(message = "Password không được để trống") @Size(min = 8, message = "Mật khẩu phải lớn hơn 8 ký tự") @Pattern(regexp = "^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d)(?=.*[@#$%^&+=!]).{8,}$", message = "Mật khẩu phải chứa ít nhất một chữ hoa, một chữ thường, một số và một ký tự đặc biệt") String matKhau,
            @Past(message = "Ngày sinh không hợp lệ (phải nhỏ hơn ngày hiện tại)") Date ngaySinh, String gioiTinh,
            Date ngayTaoAcc, @NotEmpty(message = "Hãy chọn vai trò người dùng") String userRole,
            @NotEmpty(message = "Nhập họ và tên") @Size(min = 2, message = "Họ và tên từ 2 ký tự trở lên") String hoVaTen,
            String soDienThoai, String diaChi, Integer totalQuantityInCart, String avatar, List<Order> orders,
            List<Payment> payments, List<Review> reviews, List<Cart> carts, String googleId) {
        this.userId = userId;
        this.email = email;
        this.matKhau = matKhau;
        this.ngaySinh = ngaySinh;
        this.gioiTinh = gioiTinh;
        this.ngayTaoAcc = ngayTaoAcc;
        this.userRole = userRole;
        this.hoVaTen = hoVaTen;
        this.soDienThoai = soDienThoai;
        this.diaChi = diaChi;
        this.totalQuantityInCart = totalQuantityInCart;
        this.avatar = avatar;
        this.orders = orders;
        this.payments = payments;
        this.reviews = reviews;
        this.carts = carts;
        this.googleId = googleId;
    }

    public int getUserId() {
        return userId;
    }

    public void setUserId(int userId) {
        this.userId = userId;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getMatKhau() {
        return matKhau;
    }

    public void setMatKhau(String matKhau) {
        this.matKhau = matKhau;
    }

    public Date getNgaySinh() {
        return ngaySinh;
    }

    public void setNgaySinh(Date ngaySinh) {
        this.ngaySinh = ngaySinh;
    }

    public String getGioiTinh() {
        return gioiTinh;
    }

    public void setGioiTinh(String gioiTinh) {
        this.gioiTinh = gioiTinh;
    }

    public Date getNgayTaoAcc() {
        return ngayTaoAcc;
    }

    public void setNgayTaoAcc(Date ngayTaoAcc) {
        this.ngayTaoAcc = ngayTaoAcc;
    }

    public String getUserRole() {
        return userRole;
    }

    public void setUserRole(String userRole) {
        this.userRole = userRole;
    }

    public String getHoVaTen() {
        return hoVaTen;
    }

    public void setHoVaTen(String hoVaTen) {
        this.hoVaTen = hoVaTen;
    }

    public String getSoDienThoai() {
        return soDienThoai;
    }

    public void setSoDienThoai(String soDienThoai) {
        this.soDienThoai = soDienThoai;
    }

    public String getDiaChi() {
        return diaChi;
    }

    public void setDiaChi(String diaChi) {
        this.diaChi = diaChi;
    }

    public String getAvatar() {
        return avatar;
    }

    public void setAvatar(String avatar) {
        this.avatar = avatar;
    }

    public List<Order> getOrders() {
        return orders;
    }

    public void setOrders(List<Order> orders) {
        this.orders = orders;
    }

    public List<Payment> getPayments() {
        return payments;
    }

    public void setPayments(List<Payment> payments) {
        this.payments = payments;
    }

    public List<Review> getReviews() {
        return reviews;
    }

    public void setReviews(List<Review> reviews) {
        this.reviews = reviews;
    }

    public List<Cart> getCarts() {
        return carts;
    }

    public void setCarts(List<Cart> carts) {
        this.carts = carts;
    }

    public Integer getTotalQuantityInCart() {
        return totalQuantityInCart;
    }

    public void setTotalQuantityInCart(Integer totalQuantityInCart) {
        this.totalQuantityInCart = totalQuantityInCart;
    }

}
