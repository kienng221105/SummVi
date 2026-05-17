import docx
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

def insert_paragraph_after(paragraph, text, style='Normal'):
    """Inserts a new paragraph after the given paragraph in python-docx."""
    new_p_element = OxmlElement('w:p')
    paragraph._element.addnext(new_p_element)
    new_para = Paragraph(new_p_element, paragraph._parent)
    new_para.text = text
    new_para.style = style
    return new_para

def update_docx():
    src_path = r"d:\Workplace\SummVi\docs\Báo cáo (1).docx"
    dest_path = r"d:\Workplace\SummVi\docs\Báo cáo.docx"
    
    print(f"Loading {src_path}...")
    doc = docx.Document(src_path)
    
    p_conclusion = None
    p_future = None
    
    for para in doc.paragraphs:
        t = para.text.strip()
        if t == "3. Kết luận tổng hợp":
            p_conclusion = para
        elif t == "4. Hướng phát triển trong tương lai":
            p_future = para
            
    if not p_conclusion:
        print("Error: Could not find paragraph '3. Kết luận tổng hợp'")
        return
    if not p_future:
        print("Error: Could not find paragraph '4. Hướng phát triển trong tương lai'")
        return
        
    print("Found headings. Inserting text...")
    
    # 3. Conclusion paragraphs
    conclusion_text = [
        "Hệ thống SummVi (Vietnamese Text Summarizer) đã được thiết kế, xây dựng và thực nghiệm thành công, hoàn thành trọn vẹn các mục tiêu nghiên cứu và yêu cầu thực tiễn đặt ra đối với một hệ thống tóm tắt tin tức tự động chuyên sâu cho tiếng Việt. Nhìn lại toàn bộ quá trình thực hiện đề tài, nhóm rút ra các kết luận tổng hợp quan trọng sau:",
        "1. Giải pháp công nghệ đột phá và tối ưu ngữ nghĩa: Điểm sáng lớn nhất của SummVi là việc tích hợp thành công kiến trúc Graph RAG tiên tiến, kết hợp hài hòa giữa cơ chế truy xuất ngữ nghĩa dựa trên không gian vector (Vector RAG sử dụng PhoBERT-base và cơ sở dữ liệu vector ChromaDB) và mô hình Đồ thị tri thức (Knowledge Graph sử dụng NetworkX và thuật toán phân cụm Louvain). Sự kết hợp này đã khắc phục triệt để các hạn chế của RAG truyền thống đối với tài liệu dài hoặc chuỗi bài viết liên quan, đảm bảo tính liên tục của ngữ cảnh, giữ vững mạch logic sự kiện và hạn chế tối đa hiện tượng \"ảo giác\" (hallucination) trong văn bản tóm tắt.",
        "2. Mô hình AI chuyên biệt chất lượng cao: Thông qua phương pháp chưng cất tri thức (Knowledge Distillation) từ mô hình lớn thế hệ mới DeepSeek, mô hình cốt lõi ViT5-base đã được tinh chỉnh chuyên sâu trên tập dữ liệu 12.000 bản ghi tin tức tiếng Việt chất lượng cao được thu thập từ các trang báo điện tử uy tín (Dân Trí, Thanh Niên) và tập dữ liệu chuẩn WikiLingua. Kết quả thực nghiệm trên tập validation vô cùng khả quan với chỉ số ROUGE-1 đạt 55.55%, ROUGE-2 đạt 33.98% và ROUGE-L đạt 38.72%, chứng minh khả năng tóm tắt trừu tượng (abstractive summarization) vượt trội, tạo ra các câu văn mới mạch lạc, tự nhiên và chuẩn ngữ pháp thay vì chỉ cắt ghép các câu thô từ văn bản gốc.",
        "3. Hệ sinh thái phần mềm SaaS hoàn chỉnh và bảo mật: Hệ thống không chỉ dừng lại ở mức mô hình AI thử nghiệm mà đã được phát triển thành một nền tảng Web SaaS hoàn chỉnh. Với FastAPI (backend) hiệu năng cao, Next.js (frontend) tối ưu trải nghiệm và PostgreSQL (database Neon serverless) bền vững, hệ thống cung cấp đầy đủ các nghiệp vụ quản lý người dùng, phân quyền vai trò (RBAC), quản lý lịch sử hội thoại, và vòng lặp phản hồi (feedback loop) chất lượng từ người dùng. Hệ thống bảo mật đa lớp được thiết lập chặt chẽ thông qua xác thực JWT, mã hóa Bcrypt, bảo vệ chống SQL Injection và cổng Reverse Proxy Nginx kiên cố.",
        "4. Hạ tầng Microservices sẵn sàng vận hành: Việc đóng gói toàn bộ hệ thống bằng Docker và quản lý bằng Docker Compose giúp quy trình triển khai cục bộ (local) lẫn đám mây (cloud) diễn ra nhanh chóng, đồng bộ. Với việc phân tách tính toán nặng sang GPU chuyên dụng trên Hugging Face Spaces và logic nghiệp vụ trên Render, hệ thống đạt hiệu năng suy luận ấn tượng (Inference Latency) dưới 5 giây và tỷ lệ nén thông tin đạt mức tối ưu ~91%, hoàn toàn đáp ứng tốt nhu cầu sử dụng thực tế của người dùng trong môi trường sản xuất.",
        "5. Độ tin cậy thông qua kiểm thử toàn diện: Tất cả các kịch bản kiểm thử tích hợp tự động cho toàn bộ các module (Xác thực, AI, Lịch sử, Đánh giá phản hồi, Quản trị viên, Thống kê phân tích và Legacy APIs) đều đạt tỷ lệ PASS 100%. Đây là minh chứng rõ ràng nhất cho thấy tính ổn định, độ tin cậy và khả năng vận hành trơn tru của hệ thống trong thực tế."
    ]
    
    # Insert in reverse order to keep paragraph ordering, or normal order using a cursor
    curr_para = p_conclusion
    for text in conclusion_text:
        curr_para = insert_paragraph_after(curr_para, text)
        
    # 4. Future development paragraphs
    future_text = [
        "Mặc dù hệ thống SummVi đã đạt được những kết quả rất ấn tượng và khẳng định tính ứng dụng thực tiễn cao, nhóm vẫn định hướng một lộ trình phát triển và cải tiến toàn diện trong tương lai nhằm nâng cao chất lượng dịch vụ, tối ưu hiệu năng và mở rộng tính năng của hệ thống:",
        "1. Nâng cấp năng lực mô hình ngôn ngữ lõi (Core LLMs):",
        "- Nghiên cứu tích hợp hoặc tinh chỉnh các mô hình ngôn ngữ lớn (LLM) mã nguồn mở thế hệ mới có kích thước tham số lớn hơn và được tối ưu hóa riêng cho tiếng Việt (như Vistral-7B, PhoGPT, hoặc các phiên bản Llama 3 fine-tuned tiếng Việt) để nâng cao khả năng đọc hiểu ngữ nghĩa sâu và sinh văn bản tự nhiên, giàu sắc thái biểu cảm hơn.",
        "- Áp dụng các kỹ thuật tinh chỉnh tham số hiệu quả (PEFT) như LoRA, QLoRA trên các phần cứng GPU mạnh mẽ hơn nhằm tiếp tục cải thiện độ hội tụ của mô hình và nâng cao các chỉ số ROUGE-L cũng như độ chính xác thông tin.",
        "2. Tối ưu hóa và nâng cấp kiến trúc Graph RAG:",
        "- Cải tiến bộ trích xuất thực thể (NER Extractor) và xác định mối quan hệ (Relation Extraction) bằng các kiến trúc học sâu chuyên sâu để tự động xây dựng đồ thị tri thức có độ chính xác cao hơn, giảm thiểu sự can thiệp thủ công hoặc các quy tắc heuristics tĩnh.",
        "- Di chuyển kho lưu trữ đồ thị từ cấu trúc NetworkX bộ nhớ trong sang các hệ quản trị cơ sở dữ liệu đồ thị chuyên dụng như Neo4j để nâng cao hiệu năng truy vấn, khả năng phân tích cụm cộng đồng và mở rộng quy mô đồ thị lên đến hàng triệu nút thực thể mà không gặp giới hạn tài nguyên.",
        "3. Hoàn thiện khung đánh giá chất lượng tự động và thủ công:",
        "- Tích hợp khung đánh giá RAG chuyên sâu (như RAGAS hoặc TruLens) để tự động hóa việc đo lường chất lượng hệ thống dựa trên ba khía cạnh cốt lõi: Tính trung thực của câu trả lời so với ngữ cảnh (Faithfulness), Độ liên quan của bản tóm tắt đối với câu hỏi (Answer Relevance), và Khả năng trích xuất chính xác ngữ cảnh (Context Recall).",
        "- Bổ sung chỉ số BERTScore để đánh giá chất lượng tóm tắt dựa trên độ tương đồng ngữ nghĩa mức nhúng vector (Semantic Similarity) thay vì chỉ đo độ trùng khớp từ vựng của ROUGE truyền thống.",
        "- Tổ chức các chiến dịch đánh giá thủ công (Human Evaluation) với sự tham gia của các chuyên gia ngôn ngữ để thiết lập tập dữ liệu thử nghiệm chuẩn hóa (Golden Dataset), giúp hiệu chuẩn và đánh giá khách quan nhất khả năng hành văn của hệ thống.",
        "4. Tối ưu hóa hiệu năng suy luận và kiến trúc hệ thống:",
        "- Áp dụng các phương pháp lượng tử hóa mô hình (Model Quantization như INT8/INT4) để nén dung lượng mô hình, giúp chạy mượt mà trên các hạ tầng phần cứng có cấu hình thấp hơn và giảm thiểu chi phí vận hành.",
        "- Tích hợp các framework tăng tốc suy luận hàng đầu hiện nay như vLLM, TensorRT-LLM hoặc TGI (Text Generation Inference) để giảm độ trễ phản hồi (Inference Latency) xuống dưới 2 giây và tối ưu hóa khả năng xử lý đồng thời (concurrency) của Model Service.",
        "- Xây dựng cơ chế tự động co giãn hạ tầng (Auto-scaling) trên đám mây để hệ thống tự động tăng/giảm số lượng containers xử lý tùy thuộc vào lưu lượng truy cập thực tế của người dùng.",
        "5. Mở rộng tính năng và đa dạng hóa nền tảng:",
        "- Tích hợp toàn diện tính năng tóm tắt đa văn bản (Multi-document Summarization): Mặc dù mô hình ngôn ngữ lõi của SummVi đã được tối ưu hóa và có khả năng xử lý tóm tắt nhiều tài liệu đồng thời ở tầng model-service, hệ thống định hướng sẽ được tích hợp đồng bộ ở tầng ứng dụng (API-service và giao diện người dùng frontend Next.js) để cung cấp cho người dùng khả năng tải lên và so sánh, tổng hợp thông tin từ nhiều nguồn báo chí khác nhau một cách mượt mà và trực quan.",
        "- Phát triển tính năng tóm tắt đa ngôn ngữ (Multilingual Summarization) cho phép người dùng dịch và tóm tắt trực tiếp các tài liệu tiếng Anh, tiếng Trung, tiếng Pháp... thành bản tóm tắt tiếng Việt chất lượng cao.",
        "- Mở rộng các định dạng đầu vào phong phú hơn như tích hợp mô hình chuyển đổi giọng nói thành văn bản (Speech-to-Text như Whisper) để hỗ trợ tóm tắt từ các file âm thanh (Audio/Podcast) hoặc video tin tức trực tuyến.",
        "- Phát triển các ứng dụng di động (Mobile App) và tiện ích mở rộng trên các trình duyệt phổ biến (Chrome/Edge Extension) để người dùng có thể tóm tắt nhanh nội dung các trang báo mạng chỉ với một cú nhấp chuột, mang lại sự tiện lợi và tối ưu hóa tối đa trải nghiệm người dùng."
    ]
    
    curr_para = p_future
    for text in future_text:
        curr_para = insert_paragraph_after(curr_para, text)
        
    doc.save(dest_path)
    print(f"Successfully saved updated document to {dest_path}!")

if __name__ == "__main__":
    update_docx()
