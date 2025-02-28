package poly.petshop.interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import poly.petshop.domain.User;

@Component
public class AuthInterceptor implements HandlerInterceptor {
    @Autowired
    HttpSession session;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        User user = (User) session.getAttribute("user"); // Lấy từ session sau khi đăng nhập
        String uri = request.getRequestURI();

        // Chia sẻ dữ liệu cho mọi request
        if (user != null) {
            request.setAttribute("userEmail", user.getEmail());
            request.setAttribute("userFullName", user.getHoVaTen());
        }

        // Bảo vệ các URI cần đăng nhập
        if (uri.startsWith("/myaccount") || uri.startsWith("/cart") || uri.startsWith("/thanhtoan")) {
            if (user == null) {
                session.setAttribute("securityUri", uri);
                response.sendRedirect("/login");
                return false;
            }
        }

        // Bảo vệ URI admin
        if (uri.startsWith("/admin") && (user == null || !user.getUserRole().equals("Admin"))) {
            session.setAttribute("securityUri", uri);
            response.sendRedirect("/login");
            return false;
        }

        return true;
    }
}