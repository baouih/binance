package poly.petshop.service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class UploadService {

    public String handleSaveFile(MultipartFile file, String directionPath) throws IOException {
        if (file.isEmpty()) {
            return "";
        }
        // Xác định thư mục lưu file dựa trên customDirectory
        Path uploadPath = Paths.get(directionPath);

        // ghifile
        String fileName = file.getOriginalFilename();
        if (fileName == null || fileName.trim().isEmpty()) {
            throw new IOException("Tên file không hợp lệ");
        }

        String sanitizedFileName = fileName.replaceAll("[^a-zA-Z0-9._-]", "_");

        Path fileNameAndPath = uploadPath.resolve(sanitizedFileName);
        Files.write(fileNameAndPath, file.getBytes());

        // Kiểm tra xem file đã tồn tại sau khi lưu
        if (!Files.exists(fileNameAndPath)) {
            throw new IOException("File không được lưu thành công: " + fileNameAndPath.toString());
        }
        // Trả về tên file (chuỗi)
        return sanitizedFileName.toString();
    }
}
