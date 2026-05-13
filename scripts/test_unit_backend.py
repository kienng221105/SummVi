import os
import sys
import io
import asyncio
from fastapi import UploadFile

# Cấu hình đường dẫn để có thể import trực tiếp từ thư mục backend
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'api-service'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.document_service import extract_text_from_file

def print_result(name, success, details=""):
    if success:
        print(f"✅ PASS: {name} " + (f"({details})" if details else ""))
    else:
        print(f"❌ FAIL: {name} - {details}")

# ==========================================
# MOCK (GIẢ LẬP) CÁC ĐỐI TƯỢNG FASTAPI
# ==========================================
class MockUploadFile(UploadFile):
    """Giả lập một file được tải lên từ trình duyệt"""
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = io.BytesIO(content)

# ==========================================
# BẮT ĐẦU UNIT TESTS 
# ==========================================

def test_extract_txt_file():
    """Kiểm tra hàm trích xuất file TXT có lấy ra đúng nội dung không"""
    content = "Hello, đây là một đoạn văn bản tiếng Việt để test."
    mock_file = MockUploadFile(filename="test.txt", content=content.encode("utf-8"))
    
    # Gọi trực tiếp hàm trong code của bạn, KHÔNG CẦN CHẠY SERVER
    result = extract_text_from_file(mock_file)
    
    if result == content:
        print_result("Unit Test - Extract TXT", True, "Nội dung khớp hoàn toàn")
    else:
        print_result("Unit Test - Extract TXT", False, f"Nội dung bị sai lệch: '{result}'")

def test_extract_word_limit():
    """Kiểm tra xem hệ thống có cắt bớt nếu văn bản dài hơn giới hạn 5000 từ không"""
    # Tạo một văn bản có 10 từ
    content = "word " * 10
    mock_file = MockUploadFile(filename="limit.txt", content=content.encode("utf-8"))
    
    # Ép giới hạn là 5 từ thay vì 5000
    result = extract_text_from_file(mock_file, word_limit=5)
    
    # Kết quả trả về phải đúng 5 từ
    words_returned = result.split()
    if len(words_returned) == 5:
        print_result("Unit Test - Word Limit Enforcer", True, "Đã giới hạn đúng số từ quy định")
    else:
        print_result("Unit Test - Word Limit Enforcer", False, f"Mong đợi 5 từ nhưng trả về {len(words_returned)}")

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("==================================================")
    print("🧪 BẮT ĐẦU CHẠY UNIT TESTS (Không cần Server)")
    print("==================================================")
    
    test_extract_txt_file()
    test_extract_word_limit()
    
    print("==================================================")
