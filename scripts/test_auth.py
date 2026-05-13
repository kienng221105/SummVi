import requests
from test_utils import BASE_URL, print_result, get_test_user

def test_auth_flow():
    print(f"--- Testing Authentication ---")
    user_data = get_test_user()
    
    # 1. Register
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code == 201:
        print_result("Auth - Register", True, f"Tạo thành công: {user_data['email']}")
    else:
        print_result("Auth - Register", False, f"Status {response.status_code} - {response.text}")

    # 2. Login
    payload = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = requests.post(f"{BASE_URL}/auth/login", data=payload)
    if response.status_code == 200:
        token = response.json().get("access_token")
        print_result("Auth - Login", True, "Lấy Token thành công")
    else:
        print_result("Auth - Login", False, f"Status {response.status_code}")
        return

    # 3. Get Me
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if response.status_code == 200:
        user_data_resp = response.json()
        print_result("Auth - Get Me", True, f"User ID: {user_data_resp.get('id')}")
    else:
        print_result("Auth - Get Me", False, f"Status {response.status_code}")

if __name__ == "__main__":
    test_auth_flow()
