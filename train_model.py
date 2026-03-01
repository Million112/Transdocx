import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
# Dòng quan trọng nhất để bỏ qua lỗi check version torch:
import transformers
transformers.utils.import_utils.is_torch_greater_or_equal_than_2_6 = lambda: True

import pandas as pd
import torch
from datasets import Dataset
from transformers import (
    MarianMTModel, 
    MarianTokenizer, 
    Seq2SeqTrainingArguments, 
    Seq2SeqTrainer, 
    DataCollatorForSeq2Seq
)


def main():
    # 1. Cấu hình thiết bị (ÉP XUNG GPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_checkpoint = "Helsinki-NLP/opus-mt-en-vi"
    output_dir = "./my_custom_marianMT"
    data_path = "train_data.csv"

    print(f"🚀 Thiết bị đang sử dụng: {device.upper()}")
    if device == "cuda":
        print(f"💎 Tên GPU: {torch.cuda.get_device_name(0)}")

    # 2. Tải Tokenizer và Model
    tokenizer = MarianTokenizer.from_pretrained(model_checkpoint)
    # Ép model lên GPU ngay khi load
    model = MarianMTModel.from_pretrained(model_checkpoint).to(device) 

    # 3. Chuẩn bị dữ liệu (Giữ nguyên vì bạn làm đã chuẩn)
    df = pd.read_csv(data_path).dropna()
    dataset = Dataset.from_pandas(df)

    def preprocess_function(examples):
        inputs = [str(ex) for ex in examples["en"]]
        targets = [str(ex) for ex in examples["vi"]]
        model_inputs = tokenizer(inputs, max_length=128, truncation=True, padding="max_length")
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(targets, max_length=128, truncation=True, padding="max_length")
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized_datasets = dataset.map(preprocess_function, batched=True)
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    # 4. Cấu hình tham số (Đã sửa lỗi và tối ưu)
    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        eval_strategy="no",
        learning_rate=3e-5,
        per_device_train_batch_size=2, 
        weight_decay=0.01,
        save_total_limit=2,
        num_train_epochs=4,
        predict_with_generate=True,
        fp16=(device == "cuda"), # Chỉ bật FP16 nếu là GPU
        logging_steps=50,
        save_steps=500,
        warmup_steps=100,
        dataloader_num_workers=0 # Để 0 để tránh lỗi đa luồng trên Windows
    )

    # 5. Khởi tạo Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    # 6. Huấn luyện
    print(f"🔥 Bắt đầu huấn luyện {len(df)} câu trong 4 Epoch...")
    trainer.train()

    # 7. Lưu kết quả
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"✅ Hoàn tất! Model mới đã nằm tại: {output_dir}")

if __name__ == "__main__":
    main()