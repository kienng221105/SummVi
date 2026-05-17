# SummVi - Vietnamese Text Summarization Platform 


---


## 1. Giới thiệu dự án (About SummVi)


**SummVi** là nền tảng tóm tắt văn bản tiếng Việt thông minh hàng đầu hiện nay, ứng dụng các công nghệ tiên tiến nhất bao gồm **Graph RAG (Retrieval-Augmented Generation)**, **Knowledge Graph (Louvain community detection)** và mô hình ngôn ngữ **ViT5-base** tinh chỉnh (fine-tuned) bằng phương pháp chưng cất tri thức (**Knowledge Distillation**) từ DeepSeek. Hệ thống giúp giải quyết triệt để bài toán ảo giác thông tin (hallucination), hỗ trợ tóm tắt văn bản đơn lẻ, đa văn bản phức tạp, tài liệu học thuật siêu dài với tốc độ cực nhanh và giao diện SaaS tối giản, hiện đại.


---


## 2. Hướng dẫn cài đặt Docker (Docker Installation Guide)


Để khởi chạy toàn bộ hệ thống bằng Docker chỉ với một nút bấm, máy tính của bạn cần cài đặt **Docker & Docker Desktop**. Hãy chọn một trong hai cách dưới đây:


### Cách 1: Cài đặt qua trang Web chính thức (Khuyên dùng)
1. Truy cập trang chủ Docker: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
2. Chọn phiên bản tải về phù hợp với hệ điều hành của bạn (**Docker Desktop for Windows / Mac / Linux**).
3. Nhấp đúp vào file `.exe` hoặc `.dmg` vừa tải và tiến hành cài đặt (bấm *Next* theo hướng dẫn mặc định).
4. Khởi động ứng dụng **Docker Desktop** sau khi cài đặt hoàn tất.


### Cách 2: Cài đặt nhanh qua Terminal (Dành cho nhà phát triển)
*   **Trên Windows (PowerShell / Command Prompt):**
    ```powershell
    winget install Docker.DockerDesktop
    ```
*   **Trên macOS (sử dụng Homebrew):**
    ```bash
    brew install --cask docker
    ```
*   **Trên Ubuntu / Linux:**
    ```bash
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    ```


---


## 3. Hướng dẫn cài đặt Node.js (Node.js Installation Guide)


Node.js cần thiết để chạy giao diện người dùng Next.js. Hãy cài đặt phiên bản **LTS (Long Term Support)** mới nhất:


### Cách 1: Cài đặt qua trang Web chính thức
1. Truy cập trang chủ Node.js: [https://nodejs.org/](https://nodejs.org/)
2. Tải phiên bản được khuyến nghị cho đại đa số người dùng (**LTS**).
3. Chạy trình cài đặt và làm theo các bước mặc định cho đến khi hoàn tất.


### Cách 2: Cài đặt nhanh qua Terminal
*   **Trên Windows (PowerShell / Command Prompt):**
    ```powershell
    winget install OpenJS.NodeJS
    ```
*   **Trên macOS (sử dụng Homebrew):**
    ```bash
    brew install node
    ```
*   **Trên Linux (Ubuntu/Debian sử dụng NodeSource):**
    ```bash
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    ```


---


## 4. Hướng dẫn khởi chạy hệ thống bằng `run_all.ps1` (Chế độ Docker)


Dự án được tích hợp sẵn kịch bản khởi chạy tự động thông minh bằng **PowerShell Script**. Hãy thực hiện theo 3 bước hướng dẫn dưới đây để cấu hình và chạy hệ thống ở chế độ Docker một cách hoàn chỉnh:


> [!IMPORTANT]
> Hãy chắc chắn rằng ứng dụng **Docker Desktop** đã được mở và đang chạy dưới nền trước khi thực hiện các bước này!


### Bước A: Cấu hình Biến môi trường & Tạo Google Client ID (Chuẩn bị)
Trước khi khởi chạy hệ thống, bạn cần cấu hình các biến môi trường (đặc biệt là tính năng Đăng nhập nhanh bằng tài khoản Google):


1. **Chuẩn bị file cấu hình:** 
   * Hãy sao chép file `.env.example` thành file `.env` ở thư mục gốc của dự án:
     ```powershell
     cp .env.example .env
     ```


2. **Tạo mã Google Client ID riêng biệt để kiểm thử:**
   * **Bước 1 (Tạo Dự án):** Truy cập vào [Google Cloud Console](https://console.cloud.google.com/), đăng nhập bằng Gmail của bạn. Nhấp vào danh sách dự án ở thanh trên cùng > Chọn **New Project** (Dự án mới) > Đặt tên dự án (ví dụ: `SummVi Auth`) và nhấn **Create** (Tạo).
   * **Bước 2 (OAuth Consent Screen):** Tại menu bên trái, vào **APIs & Services** > **OAuth consent screen** > Chọn loại người dùng **External** và nhấn **Create** > Điền các thông tin bắt buộc (Tên ứng dụng: `SummVi`, email hỗ trợ người dùng, email liên hệ của nhà phát triển) và nhấn **Save and Continue** cho đến hết các bước.
   * **Bước 3 (Tạo Credentials):** Chọn tab **Credentials** ở menu bên trái > Click nút **+ Create Credentials** ở trên cùng > Chọn **OAuth client ID**:
     * *Application type (Loại ứng dụng):* Chọn **Web application** (Ứng dụng Web).
     * *Name (Tên):* `SummVi Client`
     * *Authorized JavaScript origins (Nguồn JavaScript được ủy quyền):* Nhấp **Add URI** và nhập chính xác: `http://localhost:3000`
     * *Authorized redirect URIs (URI chuyển hướng được ủy quyền):* Nhấp **Add URI** và nhập chính xác: `http://localhost:3000`
     * Nhấn **Create**. Sao chép mã **Your Client ID** vừa hiển thị (dạng `xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com`).
   * **Bước 4 (Cập nhật cấu hình):** Mở file `.env` mới tạo ở bước 1 (hoặc file `.env.example`), tìm đến dòng số 35 và dán mã Client ID của bạn vào:
     ```env
     GOOGLE_CLIENT_ID=xxxxxxxxxxxx-xxxxxxxxxxxxxxxx.apps.googleusercontent.com
     ```


---


### Bước B: Cho phép chạy Script trên PowerShell
Mở **PowerShell** trong thư mục dự án và chạy lệnh sau để cấp quyền thực thi tạm thời cho tập lệnh cục bộ trên hệ thống:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```


---


### Bước C: Thực thi file tập lệnh và Chọn Option Docker
1. Chạy file tập lệnh khởi động tại thư mục gốc:
   ```powershell
   .\run_all.ps1
   ```
2. Khi màn hình PowerShell hiển thị câu hỏi yêu cầu lựa chọn chế độ chạy:
   `Run SummVi? (1: Local, 2: Docker)`
   
=> Hãy nhập số **`2`** và nhấn **Enter**.
* Tập lệnh sẽ tự động kiểm tra biến môi trường, liên kết các network ảo và chạy lệnh `docker compose up --build -d` ngầm dưới nền cho bạn một cách mượt mà nhất.


---


## 5. Hướng dẫn truy cập và sử dụng dịch vụ (Usage Links)


Sau khi Docker Compose khởi chạy thành công, tất cả các phân hệ sẽ tự động liên kết với nhau. Bạn hãy mở trình duyệt web và truy cập vào các đường dẫn sau để bắt đầu sử dụng:


| Phân hệ / Dịch vụ | Đường dẫn truy cập (URL) | Công dụng |
| :--- | :--- | :--- |
| **Giao diện Người dùng (Frontend)** | [http://localhost:3000](http://localhost:3000) | Giao diện Next.js chính thức của **SummVi** để tóm tắt văn bản, đăng nhập bằng tài khoản Google vừa cấu hình, theo dõi lịch sử chat, đánh giá feedback. |
| **API Gateway & Swagger Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Tài liệu kỹ thuật API chi tiết (Swagger UI) để thử nghiệm các endpoint backend trực tiếp. |
| **Kiểm tra Sức khỏe Backend (Health)** | [http://localhost:8000/health](http://localhost:8000/health) | Trả về `{"status":"ok"}` nếu Core Backend đang hoạt động ổn định. |
| **PostgreSQL Database** | `localhost:5432` | Cổng lưu trữ dữ liệu người dùng, cấu hình DB cục bộ (nội bộ Docker). |


---


> [!TIP]
> Để dừng toàn bộ các dịch vụ Docker đang chạy ngầm, bạn chỉ cần gõ lệnh sau trong terminal:
> ```bash
> docker compose down
> ```



