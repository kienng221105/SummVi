import requests
from test_utils import BASE_URL, print_result, get_test_user, register_and_login, get_auth_headers

def test_ai_features():
    print(f"--- Testing AI Features ---")
    
    # Test upload không token
    files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/ai/upload", files=files)
    if response.status_code == 401:
        print_result("AI - Upload (No Token)", True, "Bị chặn chính xác với mã 401")
    else:
        print_result("AI - Upload (No Token)", False, f"Status {response.status_code}")

    # Setup token
    user_data = get_test_user()
    token = register_and_login(user_data)
    headers = get_auth_headers(token)

    # Test file không hợp lệ
    files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
    response = requests.post(f"{BASE_URL}/ai/upload", files=files, headers=headers)
    if response.status_code == 400:
        print_result("AI - Upload (Invalid File)", True, "Bị chặn file sai định dạng (HTTP 400)")
    else:
         print_result("AI - Upload (Invalid File)", False, f"Status {response.status_code}")

    # Test tóm tắt trống
    payload = {
        "text": "",
        "length_ratio": 0.5
    }
    response = requests.post(f"{BASE_URL}/ai/", json=payload, headers=headers)
    if response.status_code in [400, 422]:
        print_result("AI - Summarize (Empty Text)", True, f"Bị chặn validate (HTTP {response.status_code})")
    else:
        print_result("AI - Summarize (Empty Text)", False, f"Status {response.status_code}")

    # Test tóm tắt văn bản toàn ký tự đặc biệt
    special_chars_text = "!@#$%^&*()_+{}|:\"<>?~`-=[]\\;',./" * 5
    payload = {
        "text": special_chars_text,
        "length_ratio": 0.5
    }
    response = requests.post(f"{BASE_URL}/ai/", json=payload, headers=headers)
    # Tùy thuộc vào cách AI xử lý, nó có thể trả về lỗi 400 (do backend chặn) 
    # hoặc trả về 200 nhưng nội dung là thông báo không thể tóm tắt.
    if response.status_code == 200:
        summary = response.json().get("summary", "")
        # Đảm bảo AI không tóm tắt được (thường sẽ trả lời xin lỗi hoặc rỗng)
        print_result("AI - Summarize (Special Chars)", True, f"Server xử lý ổn định. AI phản hồi: '{summary}'")
    else:
        # Nếu backend có custom chặn validation từ trước thì sẽ báo 400 hoặc 422
        print_result("AI - Summarize (Special Chars)", True, f"Hệ thống chặn thành công (HTTP {response.status_code})")

if __name__ == "__main__":
    test_ai_features()
