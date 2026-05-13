import sys
from test_utils import BASE_URL, print_result, get_test_user, register_and_login, get_auth_headers
import requests

def evaluate_summary_quality():
    """Test đánh giá chất lượng AI bằng cách so khớp từ vựng đơn giản (Mô phỏng ROUGE score)"""
    # 1. Đoạn văn gốc
    source_text = (
        "Trí tuệ nhân tạo (AI) đang phát triển rất nhanh chóng. "
        "Nó ứng dụng trong y tế, giáo dục và giao thông. "
        "Tuy nhiên, AI cũng đặt ra những thách thức về bảo mật và việc làm."
    )
    
    # 2. Tóm tắt mẫu do con người viết (Ground Truth)
    human_summary = "AI phát triển nhanh mang lại ứng dụng đa ngành nhưng có rủi ro về việc làm và bảo mật."
    
    # Setup token
    user_data = get_test_user()
    token = register_and_login(user_data)
    if not token:
        print_result("AI Eval", False, "Không thể login để gọi API")
        return
        
    # 3. Gọi AI tóm tắt
    payload = {
        "text": source_text,
        "length_ratio": 0.5
    }
    
    response = requests.post(f"{BASE_URL}/ai/", json=payload, headers=get_auth_headers(token))
    if response.status_code != 200:
        print_result("AI Eval", False, f"API lỗi {response.status_code}")
        return
        
    ai_summary = response.json().get("summary", "")
    
    # 4. Đánh giá đơn giản (Word Overlap / ROUGE-1 mộc)
    human_words = set(human_summary.lower().split())
    ai_words = set(ai_summary.lower().split())
    
    # Đếm số từ trùng lặp
    overlap = len(human_words.intersection(ai_words))
    precision = overlap / len(ai_words) if ai_words else 0
    recall = overlap / len(human_words) if human_words else 0
    
    if precision + recall == 0:
        f1_score = 0
    else:
        f1_score = 2 * (precision * recall) / (precision + recall)
        
    # Chấm điểm: Cần độ giống nhau tối thiểu 20%
    if f1_score > 0.2:
        print_result("AI Quality Evaluation", True, f"F1-Score: {f1_score:.2f} (Đạt yêu cầu) - AI trả về: '{ai_summary}'")
    else:
        print_result("AI Quality Evaluation", False, f"F1-Score: {f1_score:.2f} (Kém) - AI trả về: '{ai_summary}'")

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("==================================================")
    print("🤖 BẮT ĐẦU CHẠY AI EVALUATION TESTS")
    print("==================================================")
    evaluate_summary_quality()
    print("==================================================")
