package poly.petshop;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;
import org.springframework.context.annotation.Bean;
import org.springframework.boot.CommandLineRunner;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@SpringBootApplication
public class AsignmentPy00168Application extends SpringBootServletInitializer {

    private static final Logger logger = LoggerFactory.getLogger(AsignmentPy00168Application.class);

    public static void main(String[] args) {
        try {
            logger.info("Starting Spring Boot application...");
            SpringApplication.run(AsignmentPy00168Application.class, args);
            logger.info("Spring Boot application started successfully");
        } catch (Exception e) {
            logger.error("Failed to start Spring Boot application", e);
            throw e;
        }
    }

    @Bean
    public CommandLineRunner startupCheck() {
        return args -> {
            logger.info("Application startup check...");
            logger.info("Application is running and ready to serve requests");
        };
    }
}