package poly.petshop.domain;

import java.io.Serializable;
import java.util.Date;
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

@Entity
@Table(name = "campaigns")
public class Campaign implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int campaignId;

    @Column(nullable = false, columnDefinition = "NVARCHAR(255)")
    private String tenCam;
    @Column(nullable = false)
    private Date tuNgay;
    @Column(nullable = false)
    private Date denNgay;
    @Column(nullable = false)
    private float discount;
    @Column(nullable = false)
    private boolean phanTram;
    @Column(nullable = false)
    private Float chietKhau;

    @OneToMany(mappedBy = "campaign", cascade = CascadeType.REMOVE, fetch = FetchType.LAZY)
    private List<CampaignProduct> campaignProducts;

    public Campaign() {
    }

    public Campaign(int campaignId, String tenCam, Date tuNgay, Date denNgay, float discount, boolean phanTram,
            Float chietKhau, List<CampaignProduct> campaignProducts) {
        this.campaignId = campaignId;
        this.tenCam = tenCam;
        this.tuNgay = tuNgay;
        this.denNgay = denNgay;
        this.discount = discount;
        this.phanTram = phanTram;
        this.chietKhau = chietKhau;
        this.campaignProducts = campaignProducts;
    }

    @Override
    public String toString() {
        return "Campaign [campaignId=" + campaignId + ", tenCam=" + tenCam + ", tuNgay=" + tuNgay + ", denNgay="
                + denNgay + ", discount=" + discount + ", phanTram=" + phanTram + "]";
    }

    public int getCampaignId() {
        return campaignId;
    }

    public void setCampaignId(int campaignId) {
        this.campaignId = campaignId;
    }

    public String getTenCam() {
        return tenCam;
    }

    public void setTenCam(String tenCam) {
        this.tenCam = tenCam;
    }

    public Date getTuNgay() {
        return tuNgay;
    }

    public void setTuNgay(Date tuNgay) {
        this.tuNgay = tuNgay;
    }

    public Date getDenNgay() {
        return denNgay;
    }

    public void setDenNgay(Date denNgay) {
        this.denNgay = denNgay;
    }

    public float getDiscount() {
        return discount;
    }

    public void setDiscount(float discount) {
        this.discount = discount;
    }

    public boolean isPhanTram() {
        return phanTram;
    }

    public void setPhanTram(boolean phanTram) {
        this.phanTram = phanTram;
    }

    public Float getChietKhau() {
        return chietKhau;
    }

    public void setChietKhau(Float chietKhau) {
        this.chietKhau = chietKhau;
    }

    public List<CampaignProduct> getCampaignProducts() {
        return campaignProducts;
    }

    public void setCampaignProducts(List<CampaignProduct> campaignProducts) {
        this.campaignProducts = campaignProducts;
    }

}
