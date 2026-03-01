import torch
from transformers import MarianMTModel, MarianTokenizer
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

class MarianClient:
    def __init__(self, model_path="Helsinki-NLP/opus-mt-en-vi", device="cpu"):
        self.device = "cuda" if torch.cuda.is_available() and device == "cuda" else "cpu"
        logger.info(f"Khởi tạo MarianMT model: {model_path} trên {self.device}")
        
        try:
            self.tokenizer = MarianTokenizer.from_pretrained(model_path)
            self.model = MarianMTModel.from_pretrained(model_path).to(self.device)
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình MarianMT: {e}")
            raise e

    async def translate_text(self, text: str) -> str:
        """
        Hàm dịch một đoạn text đã được tinh chỉnh chống spam và tăng tốc.
        """
        # 1. Lọc các khoảng trắng
        if not text.strip():
            return text
            
        # 2. BỘ LỌC QUAN TRỌNG: Bỏ qua việc dịch nếu text chỉ chứa số, dấu câu hoặc quá ngắn
        # (File docx thường bị xé vụn thành các đoạn chỉ có dấu phẩy hoặc space)
        if len(text.strip()) < 2 or re.match(r'^[\W\d_]+$', text.strip()):
            return text

        def _translate():
            # Chuyển text thành tensor, giới hạn input đầu vào để tránh tràn RAM
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512).to(self.device)
            
            # Tính toán độ dài tối đa cho phép của câu dịch (Dài gấp đôi câu gốc + 10 token dự phòng)
            # Đây là "khóa an toàn" chống việc mô hình spam ra 72 trang
            input_length = inputs['input_ids'].shape[1]
            max_out_len = min(512, int(input_length * 2) + 10)

            with torch.no_grad():
                translated = self.model.generate(
                    **inputs,
                    max_new_tokens=max_out_len,      # Giới hạn độ dài tuyệt đối
                    repetition_penalty=1.2,          # Phạt nặng các từ lặp lại liên tục (ngăn chặn spam)
                    no_repeat_ngram_size=3,          # Không cho phép lặp lại bất kỳ cụm 3 từ nào
                    num_beams=2,                     # Dùng beam search nhẹ để dịch sát nghĩa hơn
                    early_stopping=True              # Yêu cầu mô hình dừng ngay khi đã ra một câu hoàn chỉnh
                )
                
            return self.tokenizer.decode(translated[0], skip_special_tokens=True)
            
        return await asyncio.to_thread(_translate)