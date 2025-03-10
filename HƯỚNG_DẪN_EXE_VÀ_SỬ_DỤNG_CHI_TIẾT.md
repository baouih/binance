# HƯỚNG DẪN ĐÓNG GÓI VÀ SỬ DỤNG HỆ THỐNG TRADING BOT

## PHẦN 1: ĐÓNG GÓI ỨNG DỤNG THÀNH FILE EXE

### 1.1. Chuẩn bị môi trường

Trước khi đóng gói ứng dụng, cần chuẩn bị môi trường và các công cụ cần thiết:

1. **Cài đặt Python**: Đảm bảo đã cài đặt Python phiên bản 3.7 trở lên
2. **Cài đặt các thư viện**: Chạy lệnh sau để cài đặt các thư viện cần thiết:
   ```
   pip install -r system_requirements.txt
   ```
3. **Cài đặt PyInstaller**: Nếu chưa có, hãy cài đặt PyInstaller:
   ```
   pip install pyinstaller
   ```

### 1.2. Cấu hình trước khi đóng gói

Trước khi đóng gói, cần cấu hình một số thông tin:

1. **Kiểm tra auto_update_client.py**: Trong file này, đảm bảo đã cấu hình đúng URL của server cập nhật.
2. **Kiểm tra file .env**: Tạo file `.env` từ `.env.example` và điền các thông tin API key.
3. **Cập nhật version.txt**: Đảm bảo file `version.txt` đã có phiên bản mới nhất.

### 1.3. Tiến hành đóng gói

Có 2 cách để đóng gói ứng dụng:

#### Cách 1: Sử dụng file package_desktop_app.py

Đây là cách được khuyến nghị, vì file `package_desktop_app.py` đã được tối ưu hóa để đóng gói đúng cách:

```
python package_desktop_app.py
```

File này sẽ tự động:
- Tạo thư mục `dist` chứa ứng dụng
- Bao gồm tất cả các tài nguyên cần thiết
- Tạo file cài đặt Setup.exe (nếu cấu hình)

#### Cách 2: Sử dụng PyInstaller trực tiếp

Nếu muốn tùy chỉnh quá trình đóng gói, có thể sử dụng PyInstaller trực tiếp:

```
pyinstaller --name="Trading Bot" --icon=static/icons/app_icon.ico --windowed --onefile run_desktop_app.py
```

Tùy chọn:
- `--onefile`: Tạo một file exe duy nhất
- `--windowed`: Không hiển thị cửa sổ console
- `--icon`: Đường dẫn đến file icon

### 1.4. Các tệp đã đóng gói

Sau khi đóng gói thành công, bạn sẽ thấy:

1. **Thư mục dist**: Chứa file exe chính và các tài nguyên
2. **Thư mục build**: Chứa các tệp tạm thời trong quá trình đóng gói
3. **File `Trading Bot.spec`**: File cấu hình PyInstaller

### 1.5. Xử lý sự cố khi đóng gói

Nếu gặp lỗi trong quá trình đóng gói:

1. **Thư viện thiếu**: Đảm bảo đã cài đặt đầy đủ các thư viện trong `system_requirements.txt`
2. **Lỗi đường dẫn**: Kiểm tra tất cả đường dẫn tương đối trong code
3. **Tài nguyên thiếu**: Đảm bảo tất cả các tệp tài nguyên (icon, âm thanh, v.v.) đều có trong thư mục được chỉ định

## PHẦN 2: CÀI ĐẶT VÀ SỬ DỤNG ỨNG DỤNG

### 2.1. Cài đặt ứng dụng

1. **Sao chép thư mục dist**: Sao chép toàn bộ thư mục `dist` đến máy tính mục tiêu
2. **Tạo file .env**: Tạo hoặc sao chép file `.env` vào thư mục ứng dụng
3. **Thiết lập cấu hình**: Chạy ứng dụng và thiết lập cấu hình ban đầu

### 2.2. Cấu hình lần đầu sử dụng

Khi chạy ứng dụng lần đầu, hãy thực hiện các bước sau:

1. **Cấu hình API**: Nhập API Key và Secret của Binance Testnet
2. **Cấu hình Telegram**: Nhập Bot Token và Chat ID
3. **Cấu hình rủi ro**: Thiết lập các thông số quản lý rủi ro phù hợp
4. **Kiểm tra kết nối**: Nhấn nút "Kiểm tra kết nối" để xác nhận API hoạt động

### 2.3. Giao diện chính và các chức năng

Giao diện chính bao gồm 5 tab với các chức năng sau:

#### 2.3.1. Tab Tổng quan (Overview)

- **Bảng điều khiển**: Hiển thị tổng quan số dư và hiệu suất
- **Danh sách vị thế**: Danh sách các vị thế đang mở
- **Cập nhật thị trường**: Bảng thông tin thị trường thời gian thực
- **Biểu đồ hiệu suất**: Biểu đồ hiển thị hiệu suất theo thời gian

**Chi tiết các nút chức năng**:
- **Cập nhật dữ liệu**: Làm mới tất cả dữ liệu thị trường
- **Xuất báo cáo**: Xuất báo cáo hiệu suất dưới dạng PDF
- **Lọc vị thế**: Lọc vị thế theo trạng thái và thời gian

#### 2.3.2. Tab Giao dịch (Trading)

- **Bộ lọc cặp giao dịch**: Tìm kiếm và lọc các cặp tiền
- **Biểu đồ kỹ thuật**: Biểu đồ giá với các chỉ báo kỹ thuật
- **Form đặt lệnh**: Mở vị thế mới

**Chi tiết các nút chức năng**:
- **Tính toán vị thế**: Tự động tính toán kích thước vị thế tối ưu
- **Mở Long/Short**: Đặt lệnh mở vị thế mới
- **Áp dụng chiến lược**: Áp dụng chiến lược giao dịch tự động
- **Quét cơ hội**: Quét thị trường tìm cơ hội giao dịch

#### 2.3.3. Tab Quản lý vị thế (Position Management)

- **Danh sách vị thế**: Bảng hiển thị chi tiết các vị thế đang mở
- **Chi tiết vị thế**: Thông tin chi tiết về vị thế được chọn
- **Quản lý SL/TP**: Cập nhật Stop Loss và Take Profit

**Chi tiết các nút chức năng**:
- **Đóng vị thế**: Đóng vị thế đã chọn
- **Cập nhật SL/TP**: Cập nhật mức Stop Loss và Take Profit
- **Thêm Trailing Stop**: Bật/tắt Trailing Stop
- **Lịch sử giao dịch**: Xem lịch sử các giao dịch đã đóng

#### 2.3.4. Tab Phân tích thị trường (Market Analysis)

- **Phân tích kỹ thuật**: Phân tích chi tiết các chỉ báo kỹ thuật
- **Quét thị trường**: Quét tự động tìm cơ hội giao dịch
- **Phân tích xu hướng**: Xác định xu hướng ngắn, trung và dài hạn

**Chi tiết các nút chức năng**:
- **Phân tích**: Chạy phân tích kỹ thuật cho cặp tiền được chọn
- **Tìm cơ hội**: Tìm kiếm các cơ hội giao dịch tiềm năng
- **Xuất phân tích**: Lưu kết quả phân tích dưới dạng PDF

#### 2.3.5. Tab Cài đặt (Settings)

- **Cài đặt API**: Quản lý API Key và Secret
- **Cài đặt Telegram**: Cấu hình thông báo Telegram
- **Cài đặt rủi ro**: Quản lý rủi ro và giới hạn giao dịch
- **Cài đặt giao diện**: Tùy chỉnh giao diện người dùng
- **Cài đặt thông báo**: Cấu hình thông báo và cảnh báo

**Chi tiết các nút chức năng**:
- **Lưu cài đặt**: Lưu các thay đổi cấu hình
- **Kiểm tra kết nối**: Kiểm tra kết nối API và Telegram
- **Khôi phục mặc định**: Đặt lại tất cả cài đặt về mặc định
- **Kiểm tra cập nhật**: Kiểm tra và cài đặt bản cập nhật mới

### 2.4. Các chức năng nâng cao

#### 2.4.1. Bot giao dịch tự động

Hệ thống hỗ trợ chế độ bot giao dịch tự động với các tính năng:

1. **Cấu hình Bot**: Trong tab Cài đặt > Bot giao dịch
   - **Thời gian hoạt động**: Cấu hình khung giờ hoạt động
   - **Chiến lược giao dịch**: Chọn chiến lược mặc định
   - **Tần suất quét**: Thiết lập tần suất quét thị trường
   - **Các cặp giao dịch**: Chọn danh sách cặp giao dịch theo dõi

2. **Bật/tắt Bot**: Sử dụng nút "Bật Bot" trong tab Tổng quan
   - Bot sẽ tự động quét thị trường theo tần suất đã cấu hình
   - Thực hiện giao dịch dựa trên chiến lược được chọn
   - Gửi thông báo qua Telegram khi mở/đóng vị thế

3. **Theo dõi hoạt động Bot**: Trong tab Tổng quan > Log hoạt động
   - Xem lịch sử các hoạt động của bot
   - Kiểm tra các quyết định giao dịch và lý do

#### 2.4.2. Thông báo Telegram chi tiết

Hệ thống gửi các thông báo chi tiết qua Telegram, bao gồm:

1. **Thông báo vị thế**:
   - Khi mở vị thế mới: Symbol, giá vào, SL/TP, kích thước
   - Khi đóng vị thế: Symbol, giá ra, lợi nhuận/lỗ, thời gian nắm giữ
   - Khi kích hoạt SL/TP: Loại kích hoạt, giá thực thi, P/L

2. **Thông báo cơ hội**:
   - Phát hiện cơ hội giao dịch: Symbol, loại tín hiệu, lý do, mức giá
   - Phát hiện xu hướng mới: Symbol, khung thời gian, loại xu hướng

3. **Thông báo hệ thống**:
   - Khởi động/dừng bot
   - Lỗi kết nối API
   - Cập nhật phiên bản mới
   - Cảnh báo rủi ro (vượt giới hạn, v.v.)

#### 2.4.3. Sao lưu và khôi phục cấu hình

Hệ thống cho phép sao lưu và khôi phục cấu hình:

1. **Sao lưu cấu hình**: Trong tab Cài đặt > Sao lưu
   - Lưu tất cả cài đặt hiện tại vào file JSON
   - Bao gồm cấu hình API, rủi ro, giao diện, v.v.

2. **Khôi phục cấu hình**: Trong tab Cài đặt > Khôi phục
   - Nhập file sao lưu đã lưu trước đó
   - Áp dụng lại tất cả cài đặt từ file sao lưu

#### 2.4.4. Xuất dữ liệu và báo cáo

Hệ thống cho phép xuất nhiều loại báo cáo:

1. **Báo cáo hiệu suất**: Trong tab Tổng quan > Xuất báo cáo
   - Báo cáo tổng quan: Tỷ lệ thắng/thua, P/L, ROI
   - Biểu đồ hiệu suất theo thời gian

2. **Báo cáo phân tích**: Trong tab Phân tích > Xuất phân tích
   - Kết quả phân tích kỹ thuật chi tiết
   - Đề xuất giao dịch và lý do

3. **Lịch sử giao dịch**: Trong tab Quản lý vị thế > Xuất lịch sử
   - Danh sách tất cả giao dịch đã hoàn thành
   - Thống kê theo cặp tiền, chiến lược, thời gian

## PHẦN 3: KIỂM TRA VÀ XỬ LÝ SỰ CỐ

### 3.1. Kiểm tra hệ thống

Để đảm bảo hệ thống hoạt động tốt, thực hiện kiểm tra định kỳ:

1. **Kiểm tra kết nối API**:
   - Trong tab Cài đặt > Kiểm tra kết nối
   - Xác minh kết nối tới Binance Testnet API

2. **Kiểm tra thông báo Telegram**:
   - Trong tab Cài đặt > Kiểm tra Telegram
   - Gửi tin nhắn test để xác minh kết nối

3. **Kiểm tra chức năng bot**:
   - Chạy bot trong thời gian ngắn
   - Xác minh log hoạt động và quyết định

4. **Kiểm tra toàn diện**:
   - Chạy script kiểm tra: `python desktop_app_validation.py`
   - Kiểm tra tất cả các chức năng chính của hệ thống

### 3.2. Xử lý các sự cố thường gặp

Dưới đây là cách xử lý một số sự cố thường gặp:

#### 3.2.1. Lỗi kết nối API

**Dấu hiệu**:
- Thông báo "Lỗi kết nối API"
- Không thể lấy dữ liệu thị trường
- Không thể mở/đóng vị thế

**Giải pháp**:
1. Kiểm tra API Key và Secret trong tab Cài đặt
2. Xác minh API có quyền giao dịch Futures
3. Đảm bảo kết nối internet ổn định
4. Kiểm tra tài khoản Binance (có đủ tiền, không bị khóa)

#### 3.2.2. Lỗi kết nối Telegram

**Dấu hiệu**:
- Không nhận được thông báo Telegram
- Thông báo lỗi khi kiểm tra kết nối

**Giải pháp**:
1. Kiểm tra Bot Token và Chat ID
2. Xác minh đã chat với bot trên Telegram
3. Đảm bảo bot có quyền gửi tin nhắn trong nhóm

#### 3.2.3. Lỗi mở vị thế

**Dấu hiệu**:
- Thông báo lỗi khi cố gắng mở vị thế
- Lệnh không được thực thi

**Giải pháp**:
1. Kiểm tra số dư tài khoản
2. Đảm bảo đòn bẩy được thiết lập đúng
3. Xác minh kích thước vị thế hợp lệ (đủ lớn)
4. Kiểm tra giới hạn rủi ro (số lượng vị thế tối đa)

#### 3.2.4. Lỗi đóng gói exe

**Dấu hiệu**:
- Lỗi khi chạy `package_desktop_app.py`
- File exe không được tạo hoặc không chạy được

**Giải pháp**:
1. Kiểm tra đã cài đặt đầy đủ các thư viện
2. Đảm bảo đường dẫn tương đối chính xác
3. Thử sử dụng cấu hình đơn giản hơn (`--onefile`)

#### 3.2.5. Lỗi bot không giao dịch

**Dấu hiệu**:
- Bot đang chạy nhưng không mở vị thế
- Không có log hoạt động

**Giải pháp**:
1. Kiểm tra cấu hình bot (cặp giao dịch, chiến lược)
2. Xác minh giới hạn rủi ro không quá nghiêm ngặt
3. Kiểm tra điều kiện thị trường có phù hợp với chiến lược

### 3.3. Cập nhật và nâng cấp

Để cập nhật ứng dụng lên phiên bản mới nhất:

1. **Cập nhật tự động**:
   - Khi khởi động, ứng dụng sẽ tự động kiểm tra cập nhật
   - Nhấp "Có" khi được hỏi cài đặt bản cập nhật mới

2. **Cập nhật thủ công**:
   - Trong tab Cài đặt > Kiểm tra cập nhật
   - Hoặc chạy `python auto_update_client.py`

3. **Cài đặt lại từ đầu**:
   - Tải phiên bản mới nhất từ nguồn chính thức
   - Sao lưu cấu hình trước khi cài đặt
   - Khôi phục cấu hình sau khi cài đặt mới

## PHẦN 4: BACKTEST VÀ KIỂM TRA THUẬT TOÁN

### 4.1. Chạy backtest từ giao diện

Ứng dụng cho phép chạy backtest để kiểm tra chiến lược giao dịch:

1. **Cấu hình backtest**:
   - Trong tab Phân tích > Backtest
   - Chọn cặp tiền, khung thời gian, khoảng thời gian
   - Chọn chiến lược và tham số

2. **Chạy backtest**:
   - Nhấn nút "Chạy Backtest"
   - Chờ quá trình hoàn tất (có thể mất vài phút)

3. **Phân tích kết quả**:
   - Xem tổng quan hiệu suất: P/L, ROI, tỷ lệ thắng/thua
   - Xem biểu đồ hiệu suất theo thời gian
   - Xem danh sách giao dịch chi tiết

4. **Tối ưu hóa tham số**:
   - Sử dụng công cụ tối ưu hóa tham số
   - Chạy nhiều backtest với các tham số khác nhau
   - Tìm bộ tham số tối ưu

### 4.2. Chạy backtest từ command line

Để chạy backtest với nhiều tùy chọn hơn, sử dụng command line:

```
python run_backtest.py --symbol BTCUSDT --timeframe 1h --start 2023-01-01 --end 2023-12-31 --strategy MACD_RSI --risk 1
```

Các tham số:
- `--symbol`: Cặp tiền (VD: BTCUSDT)
- `--timeframe`: Khung thời gian (VD: 15m, 1h, 4h, 1d)
- `--start`: Ngày bắt đầu (YYYY-MM-DD)
- `--end`: Ngày kết thúc (YYYY-MM-DD)
- `--strategy`: Chiến lược (VD: MACD_RSI, MACD_EMA, RSI_BB)
- `--risk`: Tỷ lệ rủi ro (% số dư)
- `--output`: Thư mục lưu kết quả

### 4.3. Tối ưu hóa chiến lược

Để tìm bộ tham số tối ưu cho chiến lược:

1. **Sử dụng công cụ tối ưu hóa**:
   ```
   python optimize_strategy.py --symbol BTCUSDT --timeframe 1h --strategy MACD_RSI
   ```

2. **Phân tích kết quả tối ưu hóa**:
   - Xem file `optimization_results/BTCUSDT_MACD_RSI_optimization.json`
   - Áp dụng bộ tham số tối ưu vào chiến lược

### 4.4. Kiểm tra độ ổn định

Để kiểm tra độ ổn định của chiến lược:

1. **Chạy nhiều backtest trên các khoảng thời gian khác nhau**:
   - Sử dụng script `stability_test.py`
   - Phân tích độ ổn định của hiệu suất

2. **Kiểm tra trên nhiều cặp tiền khác nhau**:
   - Sử dụng script `multi_symbol_test.py`
   - So sánh hiệu suất trên các cặp tiền khác nhau

## PHẦN 5: TÙY CHỈNH VÀ MỞ RỘNG

### 5.1. Tùy chỉnh giao diện

Ứng dụng cho phép tùy chỉnh giao diện:

1. **Thay đổi giao diện**: Trong tab Cài đặt > Giao diện
   - Chọn chủ đề (sáng/tối)
   - Tùy chỉnh màu sắc chính
   - Tùy chỉnh kích thước font

2. **Cấu hình bảng**: Trong mỗi bảng dữ liệu
   - Nhấp chuột phải > Cấu hình bảng
   - Chọn các cột hiển thị
   - Sắp xếp thứ tự cột

### 5.2. Thêm chiến lược mới

Để thêm chiến lược giao dịch mới:

1. **Tạo file chiến lược**:
   - Tạo file mới trong thư mục `strategies/`
   - Triển khai các phương thức cần thiết

2. **Đăng ký chiến lược**:
   - Thêm chiến lược vào `strategy_registry.py`
   - Chiến lược mới sẽ xuất hiện trong giao diện

### 5.3. Mở rộng chức năng

Các hướng mở rộng chức năng:

1. **Thêm chỉ báo kỹ thuật mới**:
   - Triển khai trong `technical_indicators.py`
   - Thêm vào phân tích kỹ thuật

2. **Tích hợp sàn giao dịch khác**:
   - Tạo adapter cho sàn mới
   - Triển khai các phương thức tương tự Binance

3. **Thêm phương pháp thông báo**:
   - Bổ sung email, SMS, Discord, v.v.
   - Tích hợp vào hệ thống thông báo

4. **Cải tiến phân tích thị trường**:
   - Thêm phân tích on-chain
   - Tích hợp dữ liệu sentiment
   - Bổ sung học máy và AI

## PHẦN 6: BẢO MẬT VÀ AN TOÀN

### 6.1. Bảo mật API Key

Để bảo vệ API Key:

1. **Lưu trữ an toàn**:
   - API Key được mã hóa trong file .env
   - Không chia sẻ hoặc đưa vào mã nguồn

2. **Giới hạn quyền**:
   - Chỉ cấp quyền cần thiết cho API Key
   - Giới hạn địa chỉ IP nếu có thể

### 6.2. Sao lưu dữ liệu

Thực hiện sao lưu dữ liệu định kỳ:

1. **Sao lưu cấu hình**:
   - Sử dụng chức năng sao lưu trong tab Cài đặt
   - Lưu trữ file sao lưu ở nơi an toàn

2. **Sao lưu lịch sử giao dịch**:
   - Xuất lịch sử giao dịch định kỳ
   - Lưu trữ báo cáo hiệu suất

### 6.3. Cập nhật an ninh

Để đảm bảo an ninh:

1. **Cập nhật thường xuyên**:
   - Luôn sử dụng phiên bản mới nhất
   - Cài đặt các bản cập nhật bảo mật

2. **Kiểm tra định kỳ**:
   - Theo dõi hoạt động giao dịch bất thường
   - Kiểm tra kết nối API thường xuyên

## PHẦN 7: GIAO DỊCH THỰC TẾ

### 7.1. Chuyển từ Testnet sang môi trường thực

Khi đã sẵn sàng giao dịch thực:

1. **Chuẩn bị API Key thực**:
   - Tạo API Key từ tài khoản Binance chính
   - Cấu hình quyền và giới hạn phù hợp

2. **Cập nhật cấu hình**:
   - Trong tab Cài đặt > API
   - Chuyển chế độ từ Testnet sang Thực
   - Nhập API Key và Secret mới

3. **Kiểm tra cẩn thận**:
   - Chạy kiểm tra kết nối
   - Xác minh số dư và thông tin tài khoản
   - Đảm bảo cài đặt rủi ro phù hợp

### 7.2. Theo dõi và quản lý

Khi giao dịch thực, theo dõi chặt chẽ:

1. **Theo dõi vị thế**:
   - Kiểm tra định kỳ các vị thế đang mở
   - Theo dõi thông báo từ Telegram

2. **Phân tích hiệu suất**:
   - Đánh giá hiệu suất giao dịch thường xuyên
   - Điều chỉnh chiến lược nếu cần

3. **Quản lý rủi ro**:
   - Giám sát phần trăm rủi ro tổng thể
   - Điều chỉnh kích thước vị thế theo biến động thị trường

## PHẦN 8: TÀI LIỆU THAM KHẢO

### 8.1. Tài liệu API

- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Python Binance Library](https://python-binance.readthedocs.io/)

### 8.2. Tài liệu PyQt5

- [PyQt5 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt5/)
- [PyQt5 Tutorial](https://www.tutorialspoint.com/pyqt5/)

### 8.3. Tài liệu khác

- [Technical Analysis Library](https://technical-analysis-library-in-python.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)