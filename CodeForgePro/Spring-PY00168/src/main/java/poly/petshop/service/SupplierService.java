package poly.petshop.service;

import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import poly.petshop.domain.Supplier;
import poly.petshop.repository.SupplierRepository;

@Service
public class SupplierService {
    private final SupplierRepository supplierRepository;

    public SupplierService(SupplierRepository supplierRepository) {
        this.supplierRepository = supplierRepository;
    }

    public List<Supplier> getAllSuppliers() {
        List<Supplier> suppliers = this.supplierRepository.findAll();
        return suppliers != null ? suppliers : List.of(); // Trả về danh sách rỗng nếu `null`
    }

    // public List<Supplier> getAllUsersByEmail(String email) {
    // return this.userRepository.findByEmail(email);
    // }

    public Supplier getSupplierById(int supplierId) {
        return this.supplierRepository.findById(supplierId);
    }

    public Supplier handleSaveSupplier(Supplier category) {
        Supplier sup = this.supplierRepository.save(category);
        System.out.println(sup);
        return sup;
    }

    public void deletetSupplierById(int supplierId) {
        this.supplierRepository.deleteById(supplierId);
    }

    public Page<Supplier> getAllSuppliers(Pageable pageable) {
        return this.supplierRepository.findAll(pageable); // Sửa thành findAll với pageable
    }

}
