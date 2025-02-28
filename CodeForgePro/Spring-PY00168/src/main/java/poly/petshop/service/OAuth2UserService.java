package poly.petshop.service;

import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;

import poly.petshop.domain.User;
import poly.petshop.repository.UserRepository;

import java.util.List;

@Service
public class OAuth2UserService extends DefaultOAuth2UserService {

    private final UserRepository userRepository;

    public OAuth2UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    public OAuth2User loadUser(OAuth2UserRequest userRequest) throws OAuth2AuthenticationException {
        OAuth2User oauth2User = super.loadUser(userRequest);

        // Extract user details
        String googleId = oauth2User.getAttribute("sub");
        String email = oauth2User.getAttribute("email");
        String name = oauth2User.getAttribute("name");

        // Check for existing user
        List<User> users = userRepository.findByEmail(email);
        User user;

        if (!users.isEmpty()) {
            user = users.get(0);
            // Update Google ID if not set
            if (user.getGoogleId() == null) {
                user.setGoogleId(googleId);
                userRepository.save(user);
            }
        } else {
            // Create new user
            user = new User();
            user.setGoogleId(googleId);
            user.setEmail(email);
            user.setHoVaTen(name);
            user.setUserRole("User");
            userRepository.save(user);
        }

        return oauth2User;
    }
}