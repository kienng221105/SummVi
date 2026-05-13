import requests
import sys
from test_utils import BASE_URL, print_result

def test_health_check():
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200 and response.json().get("status") == "ok":
            print_result("Health Check", True)
        else:
            print_result("Health Check", False, f"Status Code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print_result("System", False, "Không thể kết nối server FastAPI. Dừng các bài test tiếp theo.")
        sys.exit(1)

def test_read_root():
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
         print_result("Root Endpoint (/)", True)
    else:
         print_result("Root Endpoint (/)", False, f"Status Code: {response.status_code}")

if __name__ == "__main__":
    print(f"--- Testing Connection ---")
    test_health_check()
    test_read_root()
