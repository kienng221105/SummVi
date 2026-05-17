## 🌳 1. Sơ đồ cây thư mục tổng quan (Directory Tree)

```text
SummVi/ (Thư mục gốc dự án)
├── 📁 apps/                          # Các ứng dụng Client
│   └── 📁 frontend/                  # Mã nguồn giao diện Web (Next.js)
│       ├── 📁 public/                # Tài nguyên hình ảnh, biểu tượng tĩnh
│       └── 📁 src/
│           └── 📁 app/               # Next.js App Router
│               ├── 📁 admin/         # Trang quản trị dành cho Admin
│               ├── 📁 api/           # Các API Routes nội bộ Client
│               ├── 📁 components/    # Các UI Components tái sử dụng (Workspace, Sidebar,...)
│               ├── 📁 lib/           # Thư viện gọi API kết nối Backend (api.js)
│               ├── 📁 login/         # Giao diện Đăng nhập người dùng
│               ├── 📁 register/      # Giao diện Đăng ký tài khoản mới
│               ├── 📁 settings/      # Trang thiết lập tài khoản cá nhân
│               ├── 📄 globals.css    # Cấu hình phong cách CSS toàn cục (Tailwind UI)
│               ├── 📄 layout.js      # Giao diện khung (Root Layout) của Web
│               └── 📄 page.js        # Điểm vào chính (Landing Page / Workspace)
│
├── 📁 backend/                       # Hệ thống Backend Microservices
│   ├── 📁 api-service/               # Core API Gateway & Business Service (FastAPI)
│   │   ├── 📁 app/
│   │   │   ├── 📁 api/               # Router điều phối API Endpoint
│   │   │   │   ├── 📁 dependencies/  # Các dependency injection (Xác thực JWT, DB Session)
│   │   │   │   └── 📁 routes/        # Router Endpoint phân hệ (auth, ai, rating, admin,...)
│   │   │   ├── 📁 core/              # Cấu hình bảo mật JWT, thiết lập Database connection
│   │   │   ├── 📁 models/            # SQLAlchemy Models ánh xạ Cơ sở dữ liệu (User, Conversation,...)
│   │   │   ├── 📁 schemas/           # Pydantic Schemas validate dữ liệu đầu vào/ra
│   │   │   ├── 📁 services/          # Tầng xử lý Logic Nghiệp vụ (Business logic)
│   │   │   └── 📄 main.py            # Điểm khởi chạy API Service (Cổng 8000)
│   │   └── 📄 requirements.txt       # Danh sách thư viện Python của API Service
│   │
│   └── 📁 model-service/             # AI Inference Microservice (FastAPI)
│       ├── 📁 app/
│       │   ├── 📁 api/               # Router API tiếp nhận yêu cầu tóm tắt AI
│       │   ├── 📁 core/              # Cấu hình Model config, log, path
│       │   ├── 📁 schemas/           # Validate dữ liệu đầu vào/ra của Model
│       │   ├── 📁 services/          # Tầng Wrapper AI (Graph RAG, Louvain community, ViT5 inference)
│       │   └── 📄 main.py            # Điểm khởi chạy Model Service (Cổng 8001)
│       └── 📄 requirements.txt       # Danh sách thư viện Python của Model Service (PyTorch, HuggingFace,...)
│
├── 📁 configs/                       # Cấu hình hệ thống (Nginx, Docker setup,...)
├── 📁 data/                          # Dữ liệu nội bộ (Model Cache, Database SQLite)
├── 📁 docs/                          # Tài liệu kỹ thuật dự án
│   └── 📄 Ket_qua_kiem_thu.md        # Báo cáo 27 kịch bản kiểm thử tự động hệ thống
│
├── 📁 ml/                            # Tài nguyên Học máy (Machine Learning)
│   ├── 📁 fine_tuning/               # Kịch bản fine-tune ViT5 & Knowledge Distillation
│   └── 📁 data_pipeline/             # Tiền xử lý dữ liệu tin tức, rút trích đồ thị tri thức
│
├── 📁 scripts/                       # Bộ công cụ vận hành & Kiểm thử tự động (Pytest)
│   ├── 📄 conftest.py                # Cấu hình Pytest, Mocking DB, HTTP Client
│   ├── 📄 run_and_report_tests.py    # Script chạy 27 kịch bản kiểm thử và tự động tạo báo cáo
│   ├── 📄 test_admin.py              # Testcase phân hệ Quản trị Admin
│   ├── 📄 test_ai_api.py             # Testcase phân hệ Tóm tắt AI & Sức khỏe mô hình
│   ├── 📄 test_analytics.py          # Testcase phân hệ phân tích biểu đồ BI
│   ├── 📄 test_auth_api.py           # Testcase phân hệ Đăng ký, Đăng nhập bảo mật
│   ├── 📄 test_history_api.py        # Testcase phân hệ Quản lý Lịch sử trò chuyện
│   ├── 📄 test_rating.py             # Testcase phân hệ Vòng phản hồi người dùng (Rating/Feedback)
│   └── 📄 test_summarize.py          # Testcase phân hệ Tóm tắt Legacy không xác thực
│
├── 📄 .env.example                   # Tệp khai báo biến môi trường mẫu
├── 📄 docker-compose.yml             # Cấu hình Docker tự động build & liên kết Microservices
├── 📄 nginx.conf                     # Cấu hình Nginx Reverse Proxy điều phối lưu lượng
└── 📄 run_all.ps1                    # PowerShell Script khởi động dự án chỉ bằng 1 câu lệnh
```

---

## 🔍 2. Giải thích chi tiết các phân hệ cốt lõi

### 💻 2.1. Phân hệ Frontend (`apps/frontend`)
Được phát triển trên nền tảng **Next.js 14+** (sử dụng App Router) kết hợp cùng TailwindCSS tạo nên giao diện SaaS sang trọng, mượt mà:
*   `src/app/page.js`: Đóng vai trò là trang Workspace chính của người dùng sau khi đăng nhập. Cho phép tùy chỉnh độ dài tóm tắt, tải tệp tài liệu, hiển thị tiến trình rút gọn, phân tích chỉ số nén và kích hoạt vòng phản hồi đánh giá (Rating Loop).
*   `src/app/lib/api.js`: Module giao tiếp HTTP Client tập trung, định nghĩa các hàm gọi API đến API Gateway của backend kèm theo token Bearer JWT để xác thực.
*   `src/app/components/`:
    *   `workspace-page.js`: Trái tim giao diện tương tác, tích hợp chức năng kéo thả file và hiển thị kết quả tóm tắt.
    *   `sidebar.js`: Hiển thị danh sách cuộc hội thoại cũ đã lưu, cho phép khôi phục hoặc xóa hội thoại cũ trực tiếp từ database.

### 🛡️ 2.2. Phân hệ Core API Service (`backend/api-service`)
Là cổng đón nhận (Gateway) toàn bộ luồng nghiệp vụ của hệ thống, tương tác với Database chính (PostgreSQL / SQLite):
*   `app/api/routes/auth.py`: Quản lý quy trình đăng ký, đăng nhập tài khoản bằng mật khẩu mã hóa bcrypt hoặc đăng nhập SSO bằng tài khoản Google (OAuth2).
*   `app/api/routes/ai.py`: Nhận yêu cầu tóm tắt từ client, xác thực quyền truy cập của người dùng và chuyển tiếp yêu cầu tóm tắt an toàn sang phân hệ `model-service`.
*   `app/services/analytics_service.py`: Tổng hợp các số liệu thống kê BI (độ dài trung bình, từ khóa xuất hiện nhiều nhất, tỷ lệ nén thông tin) để phục vụ cho các biểu đồ phân tích trên dashboard admin.

### 🧠 2.3. Phân hệ AI Inference Service (`backend/model-service`)
Chịu trách nhiệm trực tiếp chạy các giải thuật học sâu và xử lý tri thức chuyên sâu:
*   `app/services/inference_service.py`: Tải các mô hình học máy vào bộ nhớ cache, triển khai quy trình **Graph RAG**:
    1. Chia nhỏ văn bản đầu vào thành các chunk thông tin.
    2. Rút trích thực thể và quan hệ thông qua mô hình Embedding.
    3. Xây dựng đồ thị tri thức bằng NetworkX và phân cụm thông tin bằng thuật toán Louvain.
    4. Tổng hợp thông tin từ các cụm đồ thị và tóm tắt cuối cùng thông qua mô hình ngôn ngữ tiếng Việt chuyên biệt **ViT5**.

### 🧪 2.4. Phân hệ Kiểm thử & Bảo trì (`scripts`)
Toàn bộ kịch bản kiểm thử tích hợp (integration tests) hệ thống được cô lập hoàn toàn tại đây, đảm bảo tính nguyên bản tối đa của mã nguồn gốc:
*   `conftest.py`: Thiết lập môi trường SQLite in-memory độc lập cho mỗi phiên chạy thử nghiệm, tự động chèn dữ liệu giả lập (mock data) và ghi đè dependency xác thực để kiểm tra mọi ngóc ngách của API một cách an toàn.
*   `run_and_report_tests.py`: Điều phối việc chạy đồng thời 27 kịch bản kiểm thử bằng Pytest, thu thập kết quả log thực tế và sinh ra báo cáo đánh giá cực kỳ chi tiết tại tệp `docs/Ket_qua_kiem_thu.md`.

---

## 🔄 3. Luồng đi của dữ liệu trong hệ thống (Data Flow)

Để hiểu cách các thư mục trên tương tác với nhau, luồng dữ liệu khi người dùng bấm nút "Tạo tóm tắt" diễn ra như sau:

```text
[1] Next.js Client (page.js) gửi request -> http://localhost:8000/ai/summarize
      │
[2] FastAPI API Service tiếp nhận (ai.py) -> Xác thực JWT Token (dependencies) -> Truy vấn DB lưu lịch sử (history_service.py)
      │
[3] API Service gọi RPC nội bộ -> http://localhost:8001/model/summarize (model_client.py)
      │
[4] Model Service tiếp nhận (inference_service.py) -> Xử lý Graph RAG -> Fine-tuned ViT5 Inference
      │
[5] Trả kết quả tóm tắt ngược lại cho API Service -> Lưu thông tin vào DB -> Trả về Client hiển thị lên màn hình.
```

---
