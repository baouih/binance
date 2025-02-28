package poly.petshop.controller.admin;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import org.springframework.data.domain.PageRequest;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import jakarta.validation.Valid;
import poly.petshop.domain.User;
import poly.petshop.service.UploadService;
import poly.petshop.service.UserService;

@Controller
public class UserController {

    // @Autowired
    // private HttpServletRequest request;

    private final UploadService uploadService; // Inject UploadService
    private final UserService userService;
    private final PasswordEncoder passwordEncoder;

    // Tiem DI viet dai
    public UserController(
            UserService userService,
            UploadService uploadService,
            PasswordEncoder passwordEncoder) {
        this.userService = userService;
        this.uploadService = uploadService;
        this.passwordEncoder = passwordEncoder;
    }

    @GetMapping("/admin/user")
    public String UserPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "5") int size,
            @RequestParam(defaultValue = "userId") String sortBy,
            @RequestParam(defaultValue = "asc") String direction,
            @RequestParam(defaultValue = "") String keyword,
            Model model) {
        Sort sort = Sort.by(direction.equals("asc") ? Sort.Direction.ASC : Sort.Direction.DESC, sortBy);
        Pageable pageable = PageRequest.of(page, size, sort);

        Page<User> userPage;
        if (keyword.isEmpty()) {
            userPage = userService.getAllUsers(pageable);
        } else {
            userPage = userService.searchUsersByKeyword(keyword, pageable);
        }

        model.addAttribute("users", userPage.getContent());
        model.addAttribute("currentPage", userPage.getNumber());
        model.addAttribute("totalPages", userPage.getTotalPages());
        model.addAttribute("totalElements", userPage.getTotalElements());
        model.addAttribute("sortBy", sortBy);
        model.addAttribute("direction", direction);
        model.addAttribute("keyword", keyword);

        return "admin/user/show";
    }

    @GetMapping("/admin/user/{userId}")
    public String GetUserDetailPage(@PathVariable("userId") int userId, Model model) {
        User user = userService.getUserById(userId);
        model.addAttribute("user", user);
        model.addAttribute("userId", userId);
        System.out.println("Avatar path: " + user.getAvatar());
        return "admin/user/detail";
    }

    // Trang tạo mới user
    @GetMapping("/admin/user/create")
    public String UserPageCreate(@ModelAttribute("user") User user, Model model) {
        model.addAttribute("userRoles", List.of("Admin", "User"));
        List<String> options = new ArrayList<>();
        options.add("Nam");
        options.add("Nữ");
        model.addAttribute("options", options);
        // model.addAttribute("gioiTinhs", List.of("Nam", "Nữ"));
        return "admin/user/create";
    }

    // Table user đã tạo
    @PostMapping("/admin/user/create")
    public String PageAlreadyCreateUser(
            @ModelAttribute("user") @Valid User user,
            BindingResult newUserBindingResult,
            Model model,
            @RequestParam("image") MultipartFile file) throws IOException {

        if (newUserBindingResult.hasErrors()) {
            // validate
            List<FieldError> errors = newUserBindingResult.getFieldErrors();
            for (FieldError error : errors) {
                System.out.println(error.getField() + " - " + error.getDefaultMessage());
            }
            model.addAttribute("userRoles", List.of("Admin", "User"));
            List<String> options = new ArrayList<>();
            options.add("Nam");
            options.add("Nữ");
            model.addAttribute("options", options);

            return "admin/user/create";
        }
        if (userService.emailExists(user.getEmail())) {
            model.addAttribute("userRoles", List.of("Admin", "User"));
            List<String> options = new ArrayList<>();
            options.add("Nam");
            options.add("Nữ");
            model.addAttribute("options", options);
            model.addAttribute("error", "Email đã tồn tại! Vui lòng chọn email khác.");
            return "admin/user/create";
        }
        // Kiểm tra số điện thoại đã tồn tại
        if (user.getSoDienThoai() != null && !user.getSoDienThoai().isEmpty()
                && userService.phoneExists(user.getSoDienThoai())) {
            model.addAttribute("userRoles", List.of("Admin", "User"));
            List<String> options = new ArrayList<>();
            options.add("Nam");
            options.add("Nữ");
            model.addAttribute("options", options);
            model.addAttribute("errorSDT", "Số điện thoại đã được sử dụng! Vui lòng nhập số khác.");
            return "admin/user/create";
        }
        //
        System.out.println("User Created: " + user.toString());

        // Thư mục lưu avatar
        String avatarDirectory = System.getProperty("user.dir") + "/src/main/resources/static/images/avatar";
        // Sau khi tiêm xong thì lấy ra xài
        String fileName = uploadService.handleSaveFile(file, avatarDirectory);
        String hashPass = this.passwordEncoder.encode(user.getMatKhau());
        user.setAvatar(fileName.toString());
        user.setMatKhau(hashPass);
        this.userService.handleSaveUser(user);

        // thông báo
        model.addAttribute("msg", "Người dùng đã được tạo thành công với avatar: " + fileName);

        return "redirect:/admin/user"; // Điều hướng về trang user
    }

    // Trang update user
    @GetMapping("/admin/user/update/{userId}")
    public String GetUserUpdatePage(@PathVariable("userId") int userId, Model model) {
        User currentUser = userService.getUserById(userId);

        model.addAttribute("user", currentUser);
        model.addAttribute("userId", userId);
        model.addAttribute("userRoles", List.of("Admin", "User"));
        List<String> options = new ArrayList<>();
        options.add("Nam");
        options.add("Nữ");
        model.addAttribute("options", options);
        // model.addAttribute("gioiTinhs", List.of("Nam", "Nữ"));
        return "admin/user/update";
    }

    @PostMapping("/admin/user/update")
    public String PostUserUpdatePage(@ModelAttribute("user") @Valid User thisUser, BindingResult bindingResult,
            Model model,
            @RequestParam("image") MultipartFile file) throws IOException {

        List<FieldError> errors = new ArrayList<>(bindingResult.getFieldErrors());
        errors.removeIf(error -> error.getField().equals("matKhau")); // Không kiểm tra mật khẩu khi update

        if (!errors.isEmpty()) {
            for (FieldError error : errors) {
                System.out.println(error.getField() + " - " + error.getDefaultMessage());
            }
            model.addAttribute("userRoles", List.of("Admin", "User"));
            model.addAttribute("options", List.of("Nam", "Nữ"));
            return "admin/user/update";
        }

        User currentUser = userService.getUserById(thisUser.getUserId());
        if (currentUser != null) {
            if (file != null && !file.isEmpty()) {
                // Thư mục lưu avatar
                String avatarDirectory = System.getProperty("user.dir") + "/src/main/resources/static/images/avatar";
                // Sau khi tiêm xong thì lấy ra xài
                String fileName = uploadService.handleSaveFile(file, avatarDirectory);
                currentUser.setAvatar(fileName != null && !fileName.isEmpty() ? fileName : currentUser.getAvatar());
            } else {
                // Giữ nguyên giá trị avatar hiện tại nếu không chọn file mới
                currentUser.setAvatar(currentUser.getAvatar() != null ? currentUser.getAvatar() : "");
            }

            // Kiểm tra email đã tồn tại nhưng bỏ qua chính user hiện tại
            if (userService.emailExists(thisUser.getEmail(), thisUser.getUserId())) {
                model.addAttribute("userRoles", List.of("Admin", "User"));
                model.addAttribute("options", List.of("Nam", "Nữ"));
                model.addAttribute("error", "Email đã được sử dụng! Vui lòng chọn email khác.");
                return "admin/user/update";
            }

            // Kiểm tra số điện thoại đã tồn tại nhưng bỏ qua chính user hiện tại
            if (thisUser.getSoDienThoai() != null && !thisUser.getSoDienThoai().isEmpty() &&
                    userService.phoneExists(thisUser.getSoDienThoai(), thisUser.getUserId())) {
                model.addAttribute("userRoles", List.of("Admin", "User"));
                model.addAttribute("options", List.of("Nam", "Nữ"));
                model.addAttribute("errorSDT", "Số điện thoại đã được sử dụng! Vui lòng nhập số khác.");
                return "admin/user/update";
            }
            currentUser.setDiaChi(thisUser.getDiaChi());
            currentUser.setHoVaTen(thisUser.getHoVaTen());
            currentUser.setSoDienThoai(thisUser.getSoDienThoai());
            currentUser.setUserRole(thisUser.getUserRole());
            currentUser.setGioiTinh(thisUser.getGioiTinh());
            currentUser.setNgaySinh(thisUser.getNgaySinh());
            this.userService.handleSaveUser(currentUser);

        }
        return "redirect:/admin/user";
    }

    // Trang delete user
    @GetMapping("/admin/user/delete/{userId}")
    public String GetUserDeletePage(@PathVariable("userId") int userId, Model model) {
        User user = userService.getUserById(userId);
        model.addAttribute("user", user);
        model.addAttribute("userId", userId);
        return "admin/user/delete";
    }

    @PostMapping("/admin/user/delete")
    public String PostUserDeletePage(@ModelAttribute("user") User thisUser, Model model) {
        this.userService.deletetUserById(thisUser.getUserId());
        return "redirect:/admin/user";
    }

}

// @RestController
// public class UserController {

// // DI: dependence injection
// private UserService userService;

// public UserController(UserService userService) {
// this.userService = userService;
// }

// @GetMapping("")
// public String getHomePage() {
// return this.userService.handleHello();
// }
// }