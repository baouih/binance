package poly.petshop.repository;

import org.springframework.stereotype.Repository;

import poly.petshop.domain.Category;
import poly.petshop.domain.Supplier;

import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

@Repository
public interface SupplierRepository extends JpaRepository<Supplier, Integer> {
    Supplier save(Supplier supplier);

    void deleteById(int supplierId);

    List<Supplier> findAll();

    Supplier findById(int supplierId);

}
