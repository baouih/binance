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
@Table(name = "payments")
public class Payment implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int paymentId;

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    private String pThucTT;

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    private String statusTT;

    @Column(nullable = false)
    private Date ngayTT;

    @Column(nullable = false)
    private float tongTienTT;

    // many payments to one order
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "orderId", nullable = false)
    private Order order;
    // many payments to one user
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "userId", nullable = false)
    private User user;

    public Payment() {
    }

    @Override
    public String toString() {
        return "Payment [paymentId=" + paymentId + ", pThucTT=" + pThucTT + ", statusTT=" + statusTT + ", ngayTT="
                + ngayTT + ", tongTienTT=" + tongTienTT + "]";
    }

    public Payment(int paymentId, String pThucTT, String statusTT, Date ngayTT, float tongTienTT, Order order,
            User user) {
        this.paymentId = paymentId;
        this.pThucTT = pThucTT;
        this.statusTT = statusTT;
        this.ngayTT = ngayTT;
        this.tongTienTT = tongTienTT;
        this.order = order;
        this.user = user;
    }

    public int getPaymentId() {
        return paymentId;
    }

    public void setPaymentId(int paymentId) {
        this.paymentId = paymentId;
    }

    public String getpThucTT() {
        return pThucTT;
    }

    public void setpThucTT(String pThucTT) {
        this.pThucTT = pThucTT;
    }

    public String getStatusTT() {
        return statusTT;
    }

    public void setStatusTT(String statusTT) {
        this.statusTT = statusTT;
    }

    public Date getNgayTT() {
        return ngayTT;
    }

    public void setNgayTT(Date ngayTT) {
        this.ngayTT = ngayTT;
    }

    public float getTongTienTT() {
        return tongTienTT;
    }

    public void setTongTienTT(float tongTienTT) {
        this.tongTienTT = tongTienTT;
    }

    public Order getOrder() {
        return order;
    }

    public void setOrder(Order order) {
        this.order = order;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

}
