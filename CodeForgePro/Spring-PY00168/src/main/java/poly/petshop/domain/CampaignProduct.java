package poly.petshop.domain;

import java.io.Serializable;
import java.sql.Date;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "campaignproducts")
public class CampaignProduct implements Serializable {
    private static final long serialVersionUID = 1L;
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private int campaignProductId;

    private float discountPercentage;
    private Date effectiveDate;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "campaignId", nullable = false)
    private Campaign campaign;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "productId", nullable = false)
    private Product product;

    public CampaignProduct() {
    }

    public CampaignProduct(int campaignProductId, float discountPercentage, Date effectiveDate, Campaign campaign,
            Product product) {
        this.campaignProductId = campaignProductId;
        this.discountPercentage = discountPercentage;
        this.effectiveDate = effectiveDate;
        this.campaign = campaign;
        this.product = product;
    }

    @Override
    public String toString() {
        return "CampaignProduct [campaignProductId=" + campaignProductId + ", discountPercentage=" + discountPercentage
                + ", effectiveDate=" + effectiveDate + "]";
    }

    public int getCampaignProductId() {
        return campaignProductId;
    }

    public void setCampaignProductId(int campaignProductId) {
        this.campaignProductId = campaignProductId;
    }

    public float getDiscountPercentage() {
        return discountPercentage;
    }

    public void setDiscountPercentage(float discountPercentage) {
        this.discountPercentage = discountPercentage;
    }

    public Date getEffectiveDate() {
        return effectiveDate;
    }

    public void setEffectiveDate(Date effectiveDate) {
        this.effectiveDate = effectiveDate;
    }

    public Campaign getCampaign() {
        return campaign;
    }

    public void setCampaign(Campaign campaign) {
        this.campaign = campaign;
    }

    public Product getProduct() {
        return product;
    }

    public void setProduct(Product product) {
        this.product = product;
    }

}
