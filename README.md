# URL Shortener & Analytics System

Hệ thống rút gọn liên kết hiệu năng cao với khả năng phân tích dữ liệu thời gian thực.

## 🚀 Giới thiệu

Project này là một dịch vụ URL Shortener đầy đủ tính năng, được xây dựng với mục tiêu tối ưu hiệu năng và khả năng mở rộng. Hệ thống không chỉ rút gọn link mà còn cung cấp các công cụ phân tích chi tiết về lượt click, người dùng, và vị trí địa lý.

## ✨ Tính năng chính

- **Rút gọn link**: Tạo short link ngẫu nhiên hoặc tùy chỉnh.
- **Phân tích Real-time**: Theo dõi lượt click, referer, device, location ngay lập tức.
- **Hiệu năng cao**: Sử dụng Redis để caching và MongoDB để lưu trữ logs.
- **RESTful API**: API đầy đủ cho việc tích hợp với bên thứ 3.
- **Admin Dashboard**: Quản lý người dùng và hệ thống.

## 🛠 Tech Stack

- **Backend**: Django REST Framework (Python)
- **Database**: 
  - PostgreSQL: Dữ liệu người dùng, links.
  - MongoDB: Click logs, analytics data.
- **Caching & Queue**: Redis
- **Containerization**: Docker, Docker Compose

## 📖 Luồng hoạt động (Workflow)

### 1. Rút gọn Link
1. Người dùng gửi yêu cầu tạo link (kèm URL gốc).
2. Hệ thống kiểm tra Rate Limit (giới hạn lượt tạo).
3. Hệ thống tạo mã `short_code` (7 ký tự) duy nhất.
4. Lưu vào PostgreSQL.

### 2. Xử lý Click (Redirect)
1. Người dùng truy cập `domain.com/r/<short_code>`.
2. Hệ thống tìm link trong Database (hoặc Cache).
3. Kiểm tra tính hợp lệ:
   - Link có Active không?
   - Link có hết hạn chưa?
4. **Ghi log (Async)**: Ghi thông tin người dùng (IP, User Agent) vào MongoDB.
5. Redirect người dùng về URL gốc (HTTP 302).

### 3. Phân tích dữ liệu (Analytics)
- Dữ liệu click từ MongoDB được tổng hợp (Aggregate) để tạo ra các báo cáo:
  - Tổng số click theo ngày/giờ.
  - Top nguồn truy cập (Referer).
  - Vị trí địa lý người dùng.
- API `stats` sử dụng Database Aggregation để trả về kết quả cực nhanh.

## 📦 Cài đặt & Chạy thử

### Yêu cầu
- Docker & Docker Compose

### Các bước thực hiện

1. **Clone project:**
   ```bash
   git clone https://github.com/nguyenphutrieu22521534/URL-Shortener-Click-Analytics-Realtime.git
   cd shorter
   ```

2. **Khởi chạy services (Database, Redis):**
   ```bash
   # Chạy MySQL/Postgres, Mongo, Redis
   docker-compose -f docker/docker-compose-mysql.yaml up -d
   ```

3. **Cài đặt dependencies (Dev mode):**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r req.txt
   ```

4. **Migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Chạy server:**
   ```bash
   python manage.py runserver
   ```

## 🔌 API Documentation

| Method | Endpoint | Mô tả |
| :--- | :--- | :--- |
| **AUTH** | | |
| `POST` | `/api/auth/register/` | Đăng ký tài khoản |
| `POST` | `/api/auth/login/` | Đăng nhập (Lấy Token) |
| **LINKS** | | |
| `GET` | `/api/links/` | Lấy danh sách links |
| `POST` | `/api/links/` | Tạo link mới |
| `GET` | `/api/links/<id>/` | Xem chi tiết link |
| `GET` | `/api/links/stats/` | Xem thống kê tổng quan |

## 📝 Pending Features (Roadmap)
- [ ] Giao diện người dùng (UI) đẹp mắt (Glassmorphism).
- [ ] Tích hợp thanh toán (Subscription).
- [ ] Export báo cáo ra CSV/PDF.

---
**Author**: Nguyen Phu Trieu
