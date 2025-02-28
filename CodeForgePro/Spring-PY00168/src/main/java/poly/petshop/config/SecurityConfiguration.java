package poly.petshop.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

import poly.petshop.service.OAuth2UserService;

@Configuration
@EnableWebSecurity
public class SecurityConfiguration {

    private final OAuth2UserService oAuth2UserService;

    public SecurityConfiguration(OAuth2UserService oAuth2UserService) {
        this.oAuth2UserService = oAuth2UserService;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                // Allow all static resources and public endpoints
                .requestMatchers("/health", "/", "/css/**", "/js/**", "/images/**", "/content/**", "/lib/**").permitAll()
                // Configure OAuth2 secured endpoints here if needed
                // .requestMatchers("/admin/**").authenticated()
                // Temporarily allow all requests during development 
                .anyRequest().permitAll()
            )
            .oauth2Login(oauth2 -> oauth2
                .userInfoEndpoint(userInfo -> userInfo
                    .userService(oAuth2UserService)
                )
            );

        return http.build();
    }
}