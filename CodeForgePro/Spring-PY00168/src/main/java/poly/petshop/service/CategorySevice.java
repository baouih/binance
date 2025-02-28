package poly.petshop.service;

import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import poly.petshop.domain.Category;
import poly.petshop.repository.CategoryRepository;

@Service
public class CategorySevice {

    private final CategoryRepository categoryRepository;

    public CategorySevice(CategoryRepository categoryRepository) {
        this.categoryRepository = categoryRepository;
    }

    public List<Category> getAllCategories() {
        List<Category> categories = this.categoryRepository.findAll();
        return categories != null ? categories : List.of(); // Trả về danh sách rỗng nếu `null`
    }

    public Page<Category> getCategoryPage(int page, int size, String sortField, String sortDirection) {
        Sort sort = sortDirection.equalsIgnoreCase("asc") ? Sort.by(sortField).ascending()
                : Sort.by(sortField).descending();

        Pageable pageable = PageRequest.of(page, size, sort);
        return categoryRepository.findAll(pageable);
    }

    public List<Category> getsort(Sort sort) {
        List<Category> categories = this.categoryRepository.findAll(sort);
        return categories != null ? categories : List.of();
    }

    public Page<Category> ShowByPage(Pageable page) {
        return this.categoryRepository.findAll(page);
    }

    // public List<Category> getAllUsersByEmail(String email) {
    // return this.userRepository.findByEmail(email);
    // }

    public Category getCategoryById(int categoryId) {
        return this.categoryRepository.findById(categoryId);
    }

    public Category handleSaveCategory(Category category) {
        Category cate = this.categoryRepository.save(category);
        System.out.println(cate);
        return cate;
    }

    public void deletetCategoryById(int categoryId) {
        this.categoryRepository.deleteById(categoryId);
    }
}
