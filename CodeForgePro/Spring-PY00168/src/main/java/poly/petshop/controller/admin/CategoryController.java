package poly.petshop.controller.admin;

import org.springframework.data.domain.Page;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

import poly.petshop.domain.Category;
import poly.petshop.service.CategorySevice;

@Controller
public class CategoryController {

    private final CategorySevice categorySevice;

    public CategoryController(
            CategorySevice categorySevice) {
        this.categorySevice = categorySevice;
    }

    // @GetMapping("/admin/category")
    // public String CategoryPage(Model model) {
    // model.addAttribute("categories", categorySevice.getAllCategories());
    // return "admin/category/show";
    // }

    // @GetMapping("/admin/category")
    // public String CategoryPage(Model model, @RequestParam("field")
    // Optional<String> field) {
    // Sort sort = Sort.by(Direction.DESC, field.orElse("categoryId"));
    // model.addAttribute("categories", categorySevice.getsort(sort));
    // return "admin/category/show";
    // }

    // @GetMapping("/admin/category")
    // public String CategoryPage(Model model, @RequestParam("p") Optional<Integer>
    // p) {
    // PageRequest phanTrang = PageRequest.of(p.orElse(0), 3);
    // Page<Category> page = categorySevice.ShowByPage(phanTrang);
    // model.addAttribute("trang", page);
    // // model.addAttribute("categories", categorySevice.getAllCategories());
    // return "admin/category/show";
    // }

    @GetMapping("/admin/category")
    public String CategoryPage(Model model,
            @RequestParam(defaultValue = "5") int size,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "categoryId") String sortField,
            @RequestParam(defaultValue = "asc") String sortDirection) {

        Page<Category> categories = categorySevice.getCategoryPage(page, size, sortField, sortDirection);
        model.addAttribute("categories", categories.getContent());
        model.addAttribute("currentPage", page);
        model.addAttribute("totalPages", categories.getTotalPages());
        model.addAttribute("sortField", sortField);
        model.addAttribute("sortDirection", sortDirection.equals("asc") ? "desc" : "asc");
        return "admin/category/show";
    }

    @GetMapping("/admin/category/{categoryID}")
    public String GetCategoryDetailPage(@PathVariable("categoryID") int categoryID, Model model) {
        Category category = categorySevice.getCategoryById(categoryID);
        model.addAttribute("category", category);

        model.addAttribute("categoryID", categoryID);
        return "admin/category/detail";
    }

    // Trang tạo mới category
    @GetMapping("/admin/category/create")
    public String CategoryPageCreate(@ModelAttribute("category") Category category, Model model) {
        return "admin/category/create";
    }

    // Table category đã tạo
    @PostMapping("/admin/category/create")
    public String PageAlreadyCreateCategory(@ModelAttribute("category") Category category, Model model) {
        System.out.println("Category Created: " + category.toString());
        this.categorySevice.handleSaveCategory(category);
        return "redirect:/admin/category";
    }

    // Trang update user
    @GetMapping("/admin/category/update/{categoryId}")
    public String GetCategoryUpdatePage(@PathVariable("categoryId") int categoryId, Model model) {
        Category currentCategory = categorySevice.getCategoryById(categoryId);
        model.addAttribute("category", currentCategory);
        model.addAttribute("categoryId", categoryId);
        return "admin/category/update";
    }

    @PostMapping("/admin/category/update")
    public String PostCategoryUpdatePage(@ModelAttribute("category") Category thisCategory, Model model) {
        Category currentCategory = categorySevice.getCategoryById(thisCategory.getCategoryId());
        if (currentCategory != null) {
            currentCategory.setCategoryName(thisCategory.getCategoryName());
            this.categorySevice.handleSaveCategory(currentCategory);

        }
        return "redirect:/admin/category";
    }

    // Trang delete category
    @GetMapping("/admin/category/delete/{categoryId}")
    public String GetCategoryDeletePage(@PathVariable("categoryId") int categoryId, Model model) {
        Category category = categorySevice.getCategoryById(categoryId);
        model.addAttribute("category", category);
        model.addAttribute("categoryId", categoryId);
        return "admin/category/delete";
    }

    @PostMapping("/admin/category/delete")
    public String PostCategoryDeletePage(@ModelAttribute("category") Category thisCategory, Model model) {
        this.categorySevice.deletetCategoryById(thisCategory.getCategoryId());
        return "redirect:/admin/category";
    }
}
