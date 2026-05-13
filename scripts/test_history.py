import requests
from test_utils import BASE_URL, print_result, get_test_user, register_and_login, get_auth_headers

def test_history_list():
    print(f"--- Testing History ---")
    user_data = get_test_user()
    token = register_and_login(user_data)
    if not token:
        print_result("Setup", False, "Không thể lấy token để test History")
        return

    response = requests.get(f"{BASE_URL}/history/conversations", headers=get_auth_headers(token))
    if response.status_code == 200:
        print_result("History - List Conversations", True, f"Có {len(response.json())} cuộc trò chuyện")
    else:
        print_result("History - List Conversations", False, f"Status {response.status_code}")

if __name__ == "__main__":
    test_history_list()
