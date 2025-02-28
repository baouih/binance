package poly.petshop;

import java.time.Duration;
import java.util.Locale;

import org.springframework.context.MessageSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.support.ReloadableResourceBundleMessageSource;
import org.springframework.web.servlet.LocaleResolver;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.i18n.CookieLocaleResolver;
import org.springframework.web.servlet.i18n.LocaleChangeInterceptor;

@Configuration
public class MessageConfig implements WebMvcConfigurer {

    @Bean("messageSource")
    public MessageSource getMessageSource() {
        ReloadableResourceBundleMessageSource ms = new ReloadableResourceBundleMessageSource();
        ms.setBasenames("classpath:i18n/layout"); // Đường dẫn tới các file properties
        ms.setDefaultEncoding("UTF-8"); // Đảm bảo hỗ trợ UTF-8
        return ms;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        LocaleChangeInterceptor interceptor = new LocaleChangeInterceptor();
        interceptor.setParamName("lang"); // Tham số trên URL để thay đổi ngôn ngữ (vd: ?lang=en)
        registry.addInterceptor(interceptor);
    }

    @Bean
    public LocaleResolver localeResolver() {
        // Sử dụng CookieLocaleResolver để lưu ngôn ngữ trong cookie
        CookieLocaleResolver cookieLocaleResolver = new CookieLocaleResolver();
        cookieLocaleResolver.setCookieName("lang"); // Tên cookie lưu trữ ngôn ngữ
        cookieLocaleResolver.setCookiePath("/"); // Áp dụng cho toàn ứng dụng
        cookieLocaleResolver.setCookieMaxAge((int) Duration.ofDays(30).getSeconds()); // Thời gian sống của cookie
        cookieLocaleResolver.setDefaultLocale(new Locale("vi")); // Ngôn ngữ mặc định
        return cookieLocaleResolver;
    }
}
