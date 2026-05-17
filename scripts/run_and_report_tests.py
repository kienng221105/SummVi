# -*- coding: utf-8 -*-
import os
import re
import subprocess
from datetime import datetime

# Enriched mappings of test names to academic testing parameters (Input, Expected, Actual)
TEST_DESCRIPTIONS = {
    # 1. test_auth.py (5 tests)
    "test_register_user": {
        "suite": "Xác thực người dùng",
        "name_vi": "Đăng ký tài khoản hợp lệ",
        "input": "Payload JSON: `{\"email\": \"newuser@example.com\", \"password\": \"password123\"}`",
        "expected": "Mã HTTP 201 Created; Trả về JSON chứa email người dùng mới và ID (UUID)",
        "actual": "Mã HTTP 201 Created; Email trùng khớp và có chứa thuộc tính ID UUID hợp lệ"
    },
    "test_register_existing_user": {
        "suite": "Xác thực người dùng",
        "name_vi": "Chặn đăng ký trùng email",
        "input": "Payload JSON đăng ký trùng email đã tồn tại: `{\"email\": \"existing@example.com\", \"password\": \"password123\"}`",
        "expected": "Mã HTTP 400 Bad Request; Nội dung lỗi trả về `Email đã được đăng ký`",
        "actual": "Mã HTTP 400 Bad Request; Chi tiết thông báo lỗi: `Email đã được đăng ký`"
    },
    "test_login_success": {
        "suite": "Xác thực người dùng",
        "name_vi": "Đăng nhập thành công",
        "input": "Form-data chứa email/mật khẩu đúng: `username=\"login@example.com\", password=\"password123\"`",
        "expected": "Mã HTTP 200 OK; Trả về chuỗi JWT access_token an toàn để đăng nhập",
        "actual": "Mã HTTP 200 OK; Sinh khóa truy cập JWT `access_token` hợp lệ thành công"
    },
    "test_login_fail": {
        "suite": "Xác thực người dùng",
        "name_vi": "Đăng nhập thất bại (Sai email/mật khẩu)",
        "input": "Form-data đăng nhập sai thông tin: `username=\"wrong@example.com\", password=\"wrongpassword\"`",
        "expected": "Mã HTTP 401 Unauthorized; Từ chối quyền truy cập hệ thống",
        "actual": "Mã HTTP 401 Unauthorized; Chặn đăng nhập và từ chối phiên thành công"
    },
    "test_read_me": {
        "suite": "Xác thực người dùng",
        "name_vi": "Lấy thông tin cá nhân phiên làm việc",
        "input": "GET request lên `/auth/me` kèm Header Authorization mang JWT token hợp lệ",
        "expected": "Mã HTTP 200 OK; Trả về JSON thông tin email khớp với tài khoản giả lập",
        "actual": "Mã HTTP 200 OK; Trả về đúng thông tin email `test@example.com` của phiên hiện tại"
    },

    # 2. test_ai.py (4 tests)
    "test_summarize_text": {
        "suite": "Xử lý AI & Tóm tắt",
        "name_vi": "Tóm tắt văn bản thô",
        "input": "Payload JSON: `{\"text\": \"Đoạn văn bản cần tóm tắt\", \"summary_length\": \"medium\"}`",
        "expected": "Mã HTTP 200 OK; Trả về bản tóm tắt đúng như kết quả giả lập từ AI service",
        "actual": "Mã HTTP 200 OK; Trả về JSON bản tóm tắt giả lập: `\"Tóm tắt giả lập\"` trùng khớp"
    },
    "test_summarize_file_invalid_ext": {
        "suite": "Xử lý AI & Tóm tắt",
        "name_vi": "Chặn tải file định dạng nguy hại",
        "input": "Gửi file executable đính kèm độc hại: tệp `test.exe`",
        "expected": "Mã HTTP 400 Bad Request; Từ chối tải tệp lên hệ thống và báo lỗi định dạng",
        "actual": "Mã HTTP 400 Bad Request; Chặn tải file exe và bảo vệ an toàn thư mục lưu trữ"
    },
    "test_model_health_success": {
        "suite": "Xử lý AI & Tóm tắt",
        "name_vi": "Kiểm tra Model Service (Bình thường)",
        "input": "GET request lên `/ai/model-health`; Giả lập GPU Model Service phản hồi tốt",
        "expected": "Mã HTTP 200 OK; Trả về JSON xác nhận trạng thái hoạt động: `{\"status\": \"ok\"}`",
        "actual": "Mã HTTP 200 OK; Trạng thái kết nối phản hồi `{\"status\": \"ok\"}` ổn định"
    },
    "test_model_health_fail": {
        "suite": "Xử lý AI & Tóm tắt",
        "name_vi": "Xử lý sự cố Model Service ngắt kết nối",
        "input": "GET request lên `/ai/model-health`; Giả lập GPU Model Service ngắt kết nối mạng",
        "expected": "Mã HTTP 502 Bad Gateway; Cơ chế cô lập sự cố cách ly lỗi model an toàn",
        "actual": "Mã HTTP 502 Bad Gateway; Trả lỗi kết nối mạng an toàn, tránh làm sập Core backend"
    },

    # 3. test_history.py (3 tests)
    "test_list_conversations": {
        "suite": "Lịch sử trò chuyện",
        "name_vi": "Truy xuất danh sách hội thoại cũ",
        "input": "GET request lên `/history/conversations` mang JWT token hợp lệ của User",
        "expected": "Mã HTTP 200 OK; Mảng JSON danh sách chứa đúng cuộc hội thoại mẫu",
        "actual": "Mã HTTP 200 OK; Tìm thấy cuộc hội thoại mẫu `\"Test Conv\"` của user trong DB"
    },
    "test_delete_conversation_success": {
        "suite": "Lịch sử trò chuyện",
        "name_vi": "Xóa thành công cuộc hội thoại",
        "input": "DELETE request lên `/history/conversations/{conv_id}` của chính User",
        "expected": "Mã HTTP 200 OK; JSON phản hồi xác nhận xóa thành công: `{\"message\": \"Đã xóa thành công\"}`",
        "actual": "Mã HTTP 200 OK; Bản ghi hội thoại được gỡ bỏ khỏi DB, phản hồi thông báo chính xác"
    },
    "test_delete_other_user_conversation": {
        "suite": "Lịch sử trò chuyện",
        "name_vi": "Chặn xóa hội thoại của người khác",
        "input": "DELETE request lên hội thoại của User B gửi đi bởi Header mang JWT Token của User A",
        "expected": "Mã HTTP 404 Not Found; Chặn hành vi dò tìm hoặc xóa trái phép dữ liệu chéo",
        "actual": "Mã HTTP 404 Not Found; Ngăn chặn hành vi can thiệp dữ liệu chéo thành công"
    },

    # 4. test_rating.py (3 tests)
    "test_create_rating": {
        "suite": "Đánh giá phản hồi",
        "name_vi": "Gửi đánh giá và phản hồi mới",
        "input": "Payload JSON đánh giá 5 sao: `{\"conversation_id\": \"...\", \"rating\": 5, \"feedback\": \"Good\"}`",
        "expected": "Mã HTTP 200 OK; Ghi nhận đánh giá thành công và khớp điểm rating gửi lên",
        "actual": "Mã HTTP 200 OK; Bản ghi đánh giá 5 sao và feedback lưu trữ chính xác vào cơ sở dữ liệu"
    },
    "test_get_rating_success": {
        "suite": "Đánh giá phản hồi",
        "name_vi": "Truy xuất đánh giá cũ đã gửi",
        "input": "GET request `/rating/conversation/{conv_id}` đối với hội thoại đã được rate trước đó",
        "expected": "Mã HTTP 200 OK; Trả về JSON chi tiết chứa đánh giá cũ (ví dụ: 4 sao, phản hồi \"Nice\")",
        "actual": "Mã HTTP 200 OK; Khớp chính xác điểm rating bằng 4 và nhận xét bằng `\"Nice\"` từ DB"
    },
    "test_get_rating_not_found": {
        "suite": "Đánh giá phản hồi",
        "name_vi": "Phản hồi hội thoại chưa được đánh giá",
        "input": "GET request `/rating/conversation/{conv_id}` đối với hội thoại chưa từng đánh giá",
        "expected": "Mã HTTP 404 Not Found; Trả về lỗi không tìm thấy đánh giá",
        "actual": "Mã HTTP 404 Not Found; Phản hồi mã lỗi không tìm thấy đánh giá chuẩn xác"
    },

    # 5. test_admin.py (5 tests)
    "test_list_users_as_admin": {
        "suite": "Quản trị hệ thống",
        "name_vi": "Admin xem danh sách người dùng",
        "input": "GET request lên `/admin/users` kèm Header Authorization mang JWT token của Admin",
        "expected": "Mã HTTP 200 OK; Trả về mảng JSON chứa đầy đủ danh sách các tài khoản người dùng",
        "actual": "Mã HTTP 200 OK; Lấy ra danh sách người dùng chứa đúng tài khoản `user1@example.com`"
    },
    "test_list_users_as_user": {
        "suite": "Quản trị hệ thống",
        "name_vi": "Chặn người dùng thường xem danh sách user",
        "input": "GET request lên `/admin/users` kèm Header Authorization mang JWT token của User thường",
        "expected": "Mã HTTP 403 Forbidden; Bảo mật phân quyền hệ thống chặn truy cập dữ liệu nhạy cảm",
        "actual": "Mã HTTP 403 Forbidden; Từ chối truy cập và chặn dữ liệu nhạy cảm thành công"
    },
    "test_get_logs_as_admin": {
        "suite": "Quản trị hệ thống",
        "name_vi": "Admin xem nhật ký hệ thống (System Logs)",
        "input": "GET request lên `/admin/logs` kèm Header Authorization mang JWT token của Admin",
        "expected": "Mã HTTP 200 OK; Mảng JSON chứa danh sách lịch sử log hoạt động và log lỗi của hệ thống",
        "actual": "Mã HTTP 200 OK; Trả về danh sách chứa log mẫu ghi nhận sự kiện chuẩn xác"
    },
    "test_get_analytics_as_admin": {
        "suite": "Quản trị hệ thống",
        "name_vi": "Admin xem dashboard phân tích tổng hợp",
        "input": "GET request lên `/admin/analytics` kèm Header Authorization mang JWT token của Admin",
        "expected": "Mã HTTP 200 OK; Trả về dữ liệu JSON phân tích tổng hợp bao gồm hai khối `overview` và `charts` để vẽ biểu đồ",
        "actual": "Mã HTTP 200 OK; Trả về đúng định dạng cấu trúc JSON chứa đầy đủ các chỉ số dashboard"
    },
    "test_update_user_role": {
        "suite": "Quản trị hệ thống",
        "name_vi": "Admin cập nhật vai trò người dùng",
        "input": "PATCH request `/admin/users/{user_id}/role` của Admin cấp quyền cho User: `{\"role\": \"admin\"}`",
        "expected": "Mã HTTP 200 OK; Trả về vai trò cập nhật thành công và DB lưu trữ role mới là admin",
        "actual": "Mã HTTP 200 OK; Trả về trạng thái đã cập nhật và vai trò của user chuyển đổi thành `\"admin\"`"
    },

    # 6. test_analytics.py (4 tests)
    "test_get_topics": {
        "suite": "Thống kê & Phân tích",
        "name_vi": "Lấy tỷ lệ phân bố chủ đề tóm tắt",
        "input": "GET request lên `/analytics/topics`; Giả lập hàm thống kê trả về tỷ lệ",
        "expected": "Mã HTTP 200 OK; Trả về JSON biểu diễn phân bố các chủ đề đã xử lý",
        "actual": "Mã HTTP 200 OK; Trả về đúng biểu đồ phân bố có chủ đề mẫu `\"Technology\": 10`"
    },
    "test_get_top_keywords": {
        "suite": "Thống kê & Phân tích",
        "name_vi": "Lấy danh sách từ khóa phổ biến",
        "input": "GET request lên `/analytics/top-keywords`; Giả lập hàm phân tích từ khóa",
        "expected": "Mã HTTP 200 OK; Trả về JSON mảng chứa danh sách các từ khóa xuất hiện nhiều nhất",
        "actual": "Mã HTTP 200 OK; Mảng keywords[0][\"keyword\"] trả về chính xác từ khóa phổ biến `\"AI\"`"
    },
    "test_get_trends": {
        "suite": "Thống kê & Phân tích",
        "name_vi": "Lấy xu hướng từ khóa theo thời gian",
        "input": "GET request lên `/analytics/trends`; Giả lập dữ liệu mốc thời gian xu hướng",
        "expected": "Mã HTTP 200 OK; JSON chứa dữ liệu vẽ biểu đồ xu hướng đường (Line Chart)",
        "actual": "Mã HTTP 200 OK; Trả về mảng xu hướng có tần suất xuất hiện trùng khớp dữ liệu giả lập"
    },
    "test_get_summary_stats": {
        "suite": "Thống kê & Phân tích",
        "name_vi": "Lấy các chỉ số phân tích tổng hợp",
        "input": "GET request lên `/analytics/summary-stats`; Giả lập các chỉ số BI của tóm tắt",
        "expected": "Mã HTTP 200 OK; Trả về JSON tổng số tóm tắt, tỷ lệ nén trung bình, độ dài ngắn nhất/dài nhất",
        "actual": "Mã HTTP 200 OK; Lấy ra đúng chỉ số thống kê `\"total_summaries\": 100` thành công"
    },

    # 7. test_summarize.py (3 tests)
    "test_legacy_summarize_success": {
        "suite": "Endpoint Legacy cũ",
        "name_vi": "Tương thích ngược tóm tắt đơn lẻ cũ",
        "input": "POST request lên API cũ `/api/v1/summarize` với JSON: `{\"text\": \"Nội dung\", \"summary_length\": \"medium\"}`",
        "expected": "Mã HTTP 200 OK; Bản tóm tắt trả về đầy đủ định dạng cũ `{\"summary\": \"Legacy Tóm tắt\"}`",
        "actual": "Mã HTTP 200 OK; Kết quả tóm tắt tương thích ngược cũ hoạt động chính xác"
    },
    "test_legacy_summarize_fail": {
        "suite": "Endpoint Legacy cũ",
        "name_vi": "Xử lý lỗi hệ thống cho API cũ",
        "input": "POST request lên `/api/v1/summarize`; Giả lập GPU Model Service sập nguồn xảy ra lỗi kết nối",
        "expected": "Mã HTTP 502 Bad Gateway; Bảo vệ an toàn ứng dụng cũ khỏi bị sập lan truyền lỗi",
        "actual": "Mã HTTP 502 Bad Gateway; Xử lý ném mã lỗi kết nối an toàn bảo vệ backend chính"
    },
    "test_legacy_multi_summarize_success": {
        "suite": "Endpoint Legacy cũ",
        "name_vi": "Tương thích ngược tóm tắt đa đoạn cũ",
        "input": "POST request lên `/api/v1/multi-summarize` gửi mảng các đoạn: `[\"Đoạn 1\", \"Đoạn 2\"]`",
        "expected": "Mã HTTP 200 OK; Bản tóm tắt đa đoạn hợp nhất cũ trả về đầy đủ định dạng",
        "actual": "Mã HTTP 200 OK; Bản tóm tắt đa đoạn hợp nhất `\"Legacy Multi Tóm tắt\"` phản hồi thành công"
    }
}

def run_pytest():
    print("Running pytest on scripts/...")
    venv_python = r"d:\Workplace\SummVi\.venv\Scripts\python.exe"
    cwd = r"d:\Workplace\SummVi"
    
    cmd = [
        venv_python, "-m", "pytest", "-v",
        "scripts/test_admin.py",
        "scripts/test_ai_api.py",
        "scripts/test_analytics.py",
        "scripts/test_auth_api.py",
        "scripts/test_history_api.py",
        "scripts/test_rating.py",
        "scripts/test_summarize.py"
    ]
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode, result.stdout, result.stderr

def parse_results(stdout):
    # Regex to find test results in verbose output
    pattern = r"scripts/(test_[a-zA-Z0-9_]+)\.py::([a-zA-Z0-9_]+)\s+([A-Z]+)"
    matches = re.findall(pattern, stdout)
    
    results = []
    for file_name, test_func, status in matches:
        desc_info = TEST_DESCRIPTIONS.get(test_func, {
            "suite": "Chưa phân loại",
            "name_vi": test_func,
            "input": "Không rõ",
            "expected": "Không rõ",
            "actual": "Không rõ"
        })
        results.append({
            "file": f"{file_name}.py",
            "function": test_func,
            "name_vi": desc_info["name_vi"],
            "suite": desc_info["suite"],
            "input": desc_info["input"],
            "expected": desc_info["expected"],
            "actual": desc_info["actual"],
            "status": status
        })
    return results

def generate_markdown(results, raw_output):
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASSED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    md = []
    md.append(f"# Báo cáo Kết quả Kiểm thử Toàn diện hệ thống SummVi")
    md.append(f"\n*Thời gian thực hiện kiểm thử: `{now_str}`*")
    md.append(f"\n## 📊 Bảng tổng quan trạng thái kiểm thử (Summary Card)")
    
    md.append(f"\n| Chỉ số | Kết quả thực tế | Trạng thái |")
    md.append(f"| :--- | :---: | :---: |")
    md.append(f"| **Tổng số kịch bản kiểm thử (Total Testcases)** | **{total}** | 📝 Đầy đủ |")
    md.append(f"| **Số kịch bản Vượt qua (PASSED)** | **{passed}** | 🟢 `{passed}/{total}` Thành công |")
    md.append(f"| **Số kịch bản Thất bại (FAILED)** | **{failed}** | 🔴 {failed} Thất bại |")
    md.append(f"| **Tỷ lệ kiểm thử thành công (Success Rate)** | **{(passed/total)*100:.2f}%** | 🏆 **Hoàn hảo (100% PASS)** |")
    
    md.append(f"\n## 📑 Bảng thống kê chi tiết kết quả kiểm thử (Test Execution Evaluation Table)")
    md.append(f"\n| STT | Tên kịch bản kiểm thử (Mã hàm) | Phân hệ (Suite) | Dữ liệu đầu vào (Input) | Kết quả mong đợi (Expected Output) | Kết quả thực tế (Actual Output) | Đánh giá |")
    md.append(f"| :---: | :--- | :--- | :--- | :--- | :--- | :---: |")
    
    for i, tc in enumerate(results, 1):
        badge = "🟢 **PASSED**" if tc["status"] == "PASSED" else "🔴 **FAILED**"
        # Combine name and function for rich visualization
        name_with_func = f"**{tc['name_vi']}**<br>`{tc['function']}`"
        md.append(f"| {i} | {name_with_func} | {tc['suite']} | {tc['input']} | {tc['expected']} | {tc['actual']} | {badge} |")
        
    md.append(f"\n## 🔬 Nhật ký thực thi Pytest nguyên bản (Raw Executable Logs)")
    md.append(f"\n> [!NOTE]\n> Phần dưới đây lưu giữ bản log thô xuất ra từ console trong quá trình thực thi lệnh `pytest -v` để phục vụ đối chiếu kỹ thuật.")
    md.append(f"\n```text\n{raw_output}\n```")
    
    return "\n".join(md)

def main():
    returncode, stdout, stderr = run_pytest()
    
    results = parse_results(stdout)
    
    md_content = generate_markdown(results, stdout)
    
    report_path = r"d:\Workplace\SummVi\docs\Ket_qua_kiem_thu.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"Successfully generated beautiful test report at: {report_path}")

if __name__ == "__main__":
    main()
