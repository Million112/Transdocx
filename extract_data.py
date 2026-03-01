from datasets import load_dataset
import pandas as pd

def extract_dataset(num_samples=10000):
    print(f"📡 Đang kết nối tới HuggingFace để tải dataset 'ncduy/mt-en-vi'...")
    
    try:
        # Tải dataset (chỉ tải phần 'train')
        # Dataset này có cấu trúc: {'en': '...', 'vi': '...'}
        dataset = load_dataset("ncduy/mt-en-vi", split="train", streaming=True)
        
        print(f"🔍 Đang trích xuất {num_samples} câu ngẫu nhiên...")
        
        en_sentences = []
        vi_sentences = []
        
        # Lấy dữ liệu từ stream để tiết kiệm RAM
        count = 0
        for item in dataset:
            en_text = item['en']
            vi_text = item['vi']
            
            # Lọc nhẹ: Chỉ lấy những câu có độ dài vừa phải (từ 5 đến 50 từ)
            # Tránh lấy những câu quá ngắn hoặc quá dài làm model bị loãng
            en_word_count = len(en_text.split())
            if 5 <= en_word_count <= 50:
                en_sentences.append(en_text)
                vi_sentences.append(vi_text)
                count += 1
            
            if count >= num_samples:
                break
        
        # Tạo DataFrame và lưu thành CSV
        df = pd.DataFrame({'en': en_sentences, 'vi': vi_sentences})
        
        # Xóa các dòng trùng lặp nếu có
        df = df.drop_duplicates()
        
        output_file = "train_data.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"✅ Thành công! Đã tạo file {output_file} với {len(df)} cặp câu.")
        print(f"📊 Ví dụ câu đầu tiên:")
        print(f"   EN: {en_sentences[0]}")
        print(f"   VI: {vi_sentences[0]}")

    except Exception as e:
        print(f"❌ Lỗi khi tải dữ liệu: {e}")

if __name__ == "__main__":
    extract_dataset(10000)