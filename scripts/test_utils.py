import os
import sys
import uuid
import requests

# Fix windows encoding error
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = os.environ.get("API_URL", "http://localhost:8000")

def print_result(name, success, details=""):
    if success:
        print(f"✅ PASS: {name} " + (f"({details})" if details else ""))
    else:
        print(f"❌ FAIL: {name} - {details}")

def get_test_user():
    return {
        "email": f"testuser_{uuid.uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!"
    }

def register_and_login(user_data):
    """Đăng ký và đăng nhập, trả về access_token"""
    requests.post(f"{BASE_URL}/auth/register", json=user_data)
    
    payload = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    response = requests.post(f"{BASE_URL}/auth/login", data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def get_auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
