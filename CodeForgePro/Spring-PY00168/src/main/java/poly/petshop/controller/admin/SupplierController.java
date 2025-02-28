package poly.petshop.controller.admin;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import jakarta.validation.Valid;
import poly.petshop.domain.Supplier;
import poly.petshop.service.SupplierService;

@Controller
public class SupplierController {
    private final SupplierService supplierService;

    public SupplierController(SupplierService supplierService) {
        this.supplierService = supplierService;
    }

    @GetMapping("/admin/supplier")
    public String SupplierPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "5") int size,
            @RequestParam(defaultValue = "supplierId") String sortBy,
            @RequestParam(defaultValue = "asc") String direction,
            Model model) {
        Sort sort = Sort.by(direction.equals("asc") ? Sort.Direction.ASC : Sort.Direction.DESC, sortBy);
        Pageable pageable = PageRequest.of(page, size, sort);
        Page<Supplier> supplierPage = supplierService.getAllSuppliers(pageable);

        model.addAttribute("suppliers", supplierPage.getContent());
        model.addAttribute("currentPage", supplierPage.getNumber());
        model.addAttribute("totalPages", supplierPage.getTotalPages());
        model.addAttribute("totalElements", supplierPage.getTotalElements());
        model.addAttribute("sortBy", sortBy);
        model.addAttribute("direction", direction);

        return "admin/supplier/show";
    }

    @GetMapping("/admin/supplier/{supplierId}")
    public String GetSupplierDetailPage(@PathVariable("supplierId") int supplierId, Model model) {
        Supplier supplier = supplierService.getSupplierById(supplierId);
        model.addAttribute("supplier", supplier);
        model.addAttribute("supplierId", supplierId);
        return "admin/supplier/detail";
    }

    @GetMapping("/admin/supplier/create")
    public String SupplierPageCreate(@ModelAttribute("supplier") Supplier supplier, Model model) {
        return "admin/supplier/create";
    }

    @PostMapping("/admin/supplier/create")
    public String PageAlreadyCreateSupplier(
            @Valid @ModelAttribute("supplier") Supplier supplier,
            BindingResult bindingResult,
            Model model) {
        if (bindingResult.hasErrors()) {
            return "admin/supplier/create";
        }
        this.supplierService.handleSaveSupplier(supplier);
        return "redirect:/admin/supplier";
    }

    @GetMapping("/admin/supplier/update/{supplierId}")
    public String GetSupplierUpdatePage(@PathVariable("supplierId") int supplierId, Model model) {
        Supplier currentSupplier = supplierService.getSupplierById(supplierId);
        model.addAttribute("supplier", currentSupplier);
        model.addAttribute("supplierId", supplierId);
        return "admin/supplier/update";
    }

    @GetMapping("/admin/supplier/delete/{supplierId}")
    public String GetSupplierDeletePage(@PathVariable("supplierId") int supplierId, Model model) {
        Supplier supplier = supplierService.getSupplierById(supplierId);
        model.addAttribute("supplier", supplier);
        model.addAttribute("supplierId", supplierId);
        return "admin/supplier/delete";
    }

    @PostMapping("/admin/supplier/delete")
    public String PostSupplierDeletePage(@ModelAttribute("supplier") Supplier thisSupplier, Model model) {
        this.supplierService.deletetSupplierById(thisSupplier.getSupplierId());
        return "redirect:/admin/supplier";
    }
}