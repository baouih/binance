package poly.petshop.config;

import java.io.IOException;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.web.DefaultRedirectStrategy;
import org.springframework.security.web.RedirectStrategy;
import org.springframework.security.web.WebAttributes;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.security.web.savedrequest.HttpSessionRequestCache;
import org.springframework.security.web.savedrequest.SavedRequest;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import poly.petshop.domain.User;
import poly.petshop.service.UserService;

public class CustomSuccessHandler implements AuthenticationSuccessHandler {

    @Autowired
    private UserService userService;

    protected String determineTargetUrl(final Authentication authentication) {

        Map<String, String> roleTargetUrlMap = new HashMap<>();
        roleTargetUrlMap.put("ROLE_User", "/");
        roleTargetUrlMap.put("ROLE_Admin", "/admin");

        final Collection<? extends GrantedAuthority> authorities = authentication.getAuthorities();
        for (final GrantedAuthority grantedAuthority : authorities) {
            String authorityName = grantedAuthority.getAuthority();
            if (roleTargetUrlMap.containsKey(authorityName)) {
                return roleTargetUrlMap.get(authorityName);
            }
        }

        throw new IllegalStateException();
    }

    protected void clearAuthenticationAttributes(HttpServletRequest request, Authentication authentication) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return;
        }
        session.removeAttribute(WebAttributes.AUTHENTICATION_EXCEPTION);
        String email = authentication.getName();
        User user = this.userService.getUserByEmail(email);
        if (user != null) {
            session.setAttribute("user", user);
            session.setAttribute("avatar", user.getAvatar());
            session.setAttribute("id", user.getUserId());
            session.setAttribute("email", user.getEmail());
            session.setAttribute("hoVaTen", user.getHoVaTen());
            session.setAttribute("totalQuantityInCart", user.getTotalQuantityInCart());
        }

    }

    private RedirectStrategy redirectStrategy = new DefaultRedirectStrategy();

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
            Authentication authentication) throws IOException, ServletException {
        // url de redirect sau login
        SavedRequest savedRequest = new HttpSessionRequestCache().getRequest(request, response);
        String targetUrl;

        // Chỉ dùng SavedRequest nếu nó hợp lệ, nếu không thì dùng determineTargetUrl
        if (savedRequest != null && !savedRequest.getRedirectUrl().contains("/error")) {
            targetUrl = savedRequest.getRedirectUrl();
            System.out.println("Using saved request URL: " + targetUrl);
        } else {
            targetUrl = determineTargetUrl(authentication);
            System.out.println("Determined target URL: " + targetUrl);
        }

        if (response.isCommitted()) {
            System.out.println("Response already committed");
            return;
        }

        try {
            redirectStrategy.sendRedirect(request, response, targetUrl);
            System.out.println("Redirect successful to: " + targetUrl);
        } catch (Exception e) {
            System.err.println("Redirect failed: " + e.getMessage());
            e.printStackTrace();
        }
        // don dep session
        clearAuthenticationAttributes(request, authentication);
    }

}
