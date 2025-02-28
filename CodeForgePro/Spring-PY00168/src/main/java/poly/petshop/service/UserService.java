package poly.petshop.service;

import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;

import poly.petshop.domain.User;
import poly.petshop.repository.UserRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.crypto.password.PasswordEncoder;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository,
            PasswordEncoder passwordEncode) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncode;
    }

    public List<User> getAllUsers() {
        List<User> users = this.userRepository.findAll();
        return users != null ? users : List.of(); // Trả về danh sách rỗng nếu `null`
    }

    public Page<User> getAllUsers(Pageable pageable) {
        return userRepository.findAll(pageable);
    }

    public Page<User> searchUsersByKeyword(String keyword, Pageable pageable) {
        return userRepository.findByEmailOrHoVaTenContainingIgnoreCase(keyword, pageable);
    }

    public boolean phoneExists(String phone) {
        return userRepository.existsBySoDienThoai(phone);
    }

    public boolean emailExists(String email) {
        return userRepository.existsByEmail(email);
    }

    public boolean emailExists(String email, int userId) {
        return userRepository.existsByEmailAndUserIdNot(email, userId);
    }

    public boolean phoneExists(String phone, int userId) {
        return userRepository.existsBySoDienThoaiAndUserIdNot(phone, userId);
    }

    public List<User> getAllUsersByEmail(String email) {
        return this.userRepository.findByEmail(email);
    }

    public User getUserByEmail(String email) {
        return this.userRepository.findUserByEmail(email);
    }

    public User getUserById(int userId) {
        return this.userRepository.findById(userId);
    }

    public User handleSaveUser(User user) {
        User eric = this.userRepository.save(user);
        System.out.println(eric);
        return eric;
    }

    public void deletetUserById(int userId) {
        this.userRepository.deleteById(userId);
    }

    public String generateActivationCode() {
        return UUID.randomUUID().toString().substring(0, 8);
    }

    public User activateUser(String activationCode) {
        User user = userRepository.findByActivationCode(activationCode);
        if (user != null && !user.isActivated()) {
            user.setActivated(true);
            user.setActivationCode(null);
            return userRepository.save(user);
        }
        return null;
    }

    public User resetPassword(String resetCode, String newPassword) {
        System.out.println("Reset code received: " + resetCode);
        User user = userRepository.findByActivationCode(resetCode);
        if (user != null) {
            System.out.println("User found: " + user.getEmail());
            user.setMatKhau(passwordEncoder.encode(newPassword));
            user.setActivationCode(null);
            return userRepository.save(user);
        } else {
            System.out.println("No user found with reset code: " + resetCode);
        }
        return null;
    }
}
