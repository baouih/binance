package poly.petshop.repository;

import java.util.List;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import poly.petshop.domain.Category;

@Repository
public interface CategoryRepository extends JpaRepository<Category, Integer> {
    Category save(Category category);

    void deleteById(int categoryId);

    List<Category> findAll();

    Page<Category> findAll(Pageable pageable);

    Category findById(int categoryId);

}
