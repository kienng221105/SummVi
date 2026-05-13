import requests
from test_utils import BASE_URL, print_result, get_test_user, register_and_login, get_auth_headers

def test_security():
    print(f"--- Testing Security / RBAC ---")
    user_data = get_test_user()
    token = register_and_login(user_data)
    headers = get_auth_headers(token)

    response = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    if response.status_code == 403:
        print_result("Security - Admin API", True, "Bảo vệ thành công, trả về 403 cho User thường")
    else:
        print_result("Security - Admin API", False, f"Status {response.status_code}")

if __name__ == "__main__":
    test_security()
