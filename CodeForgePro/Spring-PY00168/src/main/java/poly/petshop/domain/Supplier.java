package poly.petshop.domain;

import java.io.Serializable;
import java.util.List;

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
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

@Entity
@Table(name = "suppliers")
public class Supplier implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int supplierId;

    @NotBlank(message = "Tên nhà cung cấp không được để trống")
    @Size(max = 100, message = "Tên không được vượt quá 100 ký tự")
    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    private String tenSup;

    @NotBlank(message = "Địa chỉ không được để trống")
    @Size(max = 255, message = "Địa chỉ không được vượt quá 255 ký tự")
    @Column(nullable = true, columnDefinition = "NVARCHAR(255)")
    private String diaChiSup;

    @NotBlank(message = "Email không được để trống")
    @Email(message = "Email không đúng định dạng")
    @Column(nullable = true, unique = true, columnDefinition = "NVARCHAR(255)")
    private String emailSup;

    @NotBlank(message = "Mã số thuế không được để trống")
    @Size(min = 10, max = 13, message = "Mã số thuế phải từ 10-13 ký tự")
    @Column(nullable = true, unique = true, columnDefinition = "NVARCHAR(255)")
    private String taxCode;

    // One supplier --> to many --> products
    @OneToMany(mappedBy = "supplier", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<Product> products;

    public Supplier() {
    }

    @Override
    public String toString() {
        return "Supplier [supplierId=" + supplierId + ", tenSup=" + tenSup + ", diaChiSup=" + diaChiSup + ", emailSup="
                + emailSup + ", taxCode=" + taxCode + "]";
    }

    public Supplier(int supplierId, String tenSup, String diaChiSup, String emailSup, String taxCode,
            List<Product> products) {
        this.supplierId = supplierId;
        this.tenSup = tenSup;
        this.diaChiSup = diaChiSup;
        this.emailSup = emailSup;
        this.taxCode = taxCode;
        this.products = products;
    }

    public int getSupplierId() {
        return supplierId;
    }

    public void setSupplierId(int supplierId) {
        this.supplierId = supplierId;
    }

    public String getTenSup() {
        return tenSup;
    }

    public void setTenSup(String tenSup) {
        this.tenSup = tenSup;
    }

    public String getDiaChiSup() {
        return diaChiSup;
    }

    public void setDiaChiSup(String diaChiSup) {
        this.diaChiSup = diaChiSup;
    }

    public String getEmailSup() {
        return emailSup;
    }

    public void setEmailSup(String emailSup) {
        this.emailSup = emailSup;
    }

    public String getTaxCode() {
        return taxCode;
    }

    public void setTaxCode(String taxCode) {
        this.taxCode = taxCode;
    }

    public List<Product> getProducts() {
        return products;
    }

    public void setProducts(List<Product> products) {
        this.products = products;
    }

}
