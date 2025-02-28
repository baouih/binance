package poly.petshop.domain;

import java.io.Serializable;
import java.util.Date;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Entity
@Table(name = "shop_orders") 
public class Order implements Serializable {
    private static final long serialVersionUID = 1L;
    private static final Logger logger = LoggerFactory.getLogger(Order.class);

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer orderId;

    @Column(nullable = false)
    private Date ngayOrder;

    @Column(nullable = false, length = 50)
    private String trangThai;

    @Column(nullable = false)
    private Double tongGiaTri;

    public Order() {
        logger.debug("Creating new Order instance");
    }

    public Integer getOrderId() {
        return orderId;
    }

    public void setOrderId(Integer orderId) {
        this.orderId = orderId;
    }

    public Date getNgayOrder() {
        return ngayOrder;
    }

    public void setNgayOrder(Date ngayOrder) {
        this.ngayOrder = ngayOrder;
    }

    public String getTrangThai() {
        return trangThai;
    }

    public void setTrangThai(String trangThai) {
        this.trangThai = trangThai;
    }

    public Double getTongGiaTri() {
        return tongGiaTri;
    }

    public void setTongGiaTri(Double tongGiaTri) {
        this.tongGiaTri = tongGiaTri;
    }

    @Override
    public String toString() {
        return "Order [orderId=" + orderId + ", ngayOrder=" + ngayOrder + 
               ", trangThai=" + trangThai + ", tongGiaTri=" + tongGiaTri + "]";
    }
}