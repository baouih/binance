# Import Spring Project vào Visual Studio Code

## Yêu cầu hệ thống
1. Java Development Kit (JDK) 17
   - Tải và cài đặt JDK 17 từ [Oracle](https://www.oracle.com/java/technologies/downloads/#java17) hoặc [OpenJDK](https://openjdk.java.net/)
   - Thiết lập biến môi trường JAVA_HOME và thêm vào PATH

2. Visual Studio Code
   - Tải và cài đặt [Visual Studio Code](https://code.visualstudio.com/)
   - Cài đặt các extension sau:
     - Extension Pack for Java
     - Spring Boot Extension Pack
     - Maven for Java

3. Maven (không bắt buộc vì project đã có Maven wrapper)
   - Maven được tích hợp sẵn trong VS Code qua extension
   - Nếu muốn cài đặt riêng: [Tải Maven](https://maven.apache.org/download.cgi)

## Các bước thiết lập project

1. Clone repository:
   ```bash
   git clone https://github.com/RubeeFunix/Spring-PY00168.git
   ```

2. Mở project trong VS Code:
   - Chọn File > Open Folder
   - Chọn thư mục Spring-PY00168
   - Đợi VS Code index project và tải extensions

3. Cấu hình Java:
   - Mở Command Palette (Ctrl+Shift+P)
   - Gõ "Java: Configure Java Runtime"
   - Chọn JDK 17 đã cài đặt

4. Build project:
   ```bash
   # Sử dụng Maven wrapper để build
   ./mvnw clean install

   # Hoặc sử dụng Maven Explorer trong VS Code:
   # 1. Mở Maven Explorer (View > Maven)
   # 2. Click vào icons clean và install
   ```

5. Chạy ứng dụng:
   - Mở file `src/main/java/poly/petshop/AsignmentPy00168Application.java`
   - Click vào nút Run trên thanh Debug
   - Hoặc chạy bằng lệnh:
     ```bash
     ./mvnw spring-boot:run -Dserver.port=5000
     ```
   - Truy cập http://localhost:5000 để kiểm tra

## Tính năng Debug trong VS Code

1. Debug Mode:
   - Đặt breakpoint bằng cách click vào lề trái của editor
   - Chọn Run > Start Debugging (F5)
   - Sử dụng các nút Step Over, Step Into, Continue trong thanh Debug

2. Hot Reload với Spring Boot DevTools:
   - Đã được cấu hình sẵn trong pom.xml
   - Khi thay đổi code, ứng dụng sẽ tự động reload

3. Spring Boot Dashboard:
   - Mở Spring Boot Dashboard từ thanh Activity Bar
   - Quản lý và restart các Spring Boot applications

4. Database Explorer:
   - Cài thêm extension Database Client
   - Kết nối và quản lý database từ VS Code

## Cấu hình Database
**(Phần này cần được bổ sung chi tiết hơn dựa trên database được sử dụng trong project)**

1. **Thêm driver database:** Thêm dependency của driver database vào file `pom.xml`. Ví dụ:  Nếu sử dụng MySQL, thêm dependency MySQL Connector/J.
2. **Cấu hình thông tin kết nối:** Cấu hình thông tin kết nối database trong file `application.properties` hoặc `application.yml`.  Bao gồm URL, username, và password.
3. **Kiểm tra kết nối:** Sử dụng tool của VS Code để test kết nối với database.


## Xử lý lỗi thường gặp

1. Lỗi không tìm thấy JDK:
   - Kiểm tra JAVA_HOME trong terminal:
     ```bash
     echo %JAVA_HOME%  # Windows
     echo $JAVA_HOME   # Linux/Mac
     ```
   - Cấu hình lại Java Runtime trong VS Code

2. Lỗi Maven build:
   ```bash
   # Xóa thư mục target
   rm -rf target/

   # Xóa cache Maven
   rm -rf ~/.m2/repository/poly/petshop

   # Build lại với -X để xem log chi tiết
   ./mvnw clean install -X
   ```

3. Lỗi Spring Boot không start:
   - Kiểm tra port 5000 có đang được sử dụng không:
     ```bash
     netstat -ano | findstr :5000  # Windows
     lsof -i :5000                 # Linux/Mac
     ```
   - Kiểm tra application.properties có cấu hình đúng không
   - Xem log trong Debug Console của VS Code

4. Lỗi không tải được dependencies:
   - Kiểm tra kết nối internet
   - Xóa thư mục .m2/repository và để Maven tải lại
   - Kiểm tra settings.xml trong .m2 có cấu hình proxy không
   - Thử thay đổi Maven mirror trong settings.xml

## Liên hệ hỗ trợ

Nếu cần hỗ trợ thêm:
1. Tạo issue trên GitHub repository
2. Kiểm tra phần Discussions trên GitHub
3. Tham khảo [Spring Boot Documentation](https://docs.spring.io/spring-boot/docs/current/reference/html/)