# Transdocx
Phần này chỉ bao gồm ứng dugnj dịch bằng API OpenAI chứ chưa tích hợp thêm phần API tự phát triển

## Bước 1: Clone thư mục về máy tính

## Bước 2: Mở cmd và di chuyển tới thư mục transdocx

## Bước 3: Nhập lệnh phía dưới vào để máy tự chạy tải các thiết bị cần thiết

`pip install -r requirements_gui.txt`

## Bước 4: Tạo một file config.yaml trong thư mục transdocx với nội dung như sau:

```openai_api_key: "" # Your OpenAI API key here
model: "gpt-4o-mini" # Default model is gpt-4o-mini. But you can change it to other models like gpt-5, gpt-5-mini, gpt-5-nano, etc.

# Translation Settings
source_lang: "English"
target_lang: "Vietnamese"

# Performance Settings
max_concurrent: 100
max_chunk_size: 5000
```

## Bước 5: Tự tạo API key openAI của bạn và điền vào phần openai_api_key: nằm trong 2 thư mục config.yaml và gui_app.py

## Bước 6: Tạo 1 folder trống tên output trong thư mục transdocx

## Bước 7: Chạy thử chương trình
Ở đây tôi sẽ thử với file sample3.docx đã có sẵn trong thư mục transdocx
### 7.1 Chạy thử tính năng dịch: 
Vào cmd ban nãy và nhập lệnh phía dưới để dịch file sample3.docx:
`python main.py sample3.docx`
Bản dịch sẽ được gửi vào trong folder output
### 7.2 Chạy thử GUI dịch file
Vào cmd ban nãy và nhập lệnh phía dưới để mở GUI dịch file sample3.docx:
`python gui_app.py`
### 7.3 Build app .exe để có thể mở ở bất kì đâu trên máy tính
Nhập lệnh phía dưới vào cmd:
`pyinstaller translator.spec`
Chương trình sẽ mất khoảng 5-15p để build app dịch. Sau khi hoàn tất, bạn sẽ thấy cmd hiển thị build thành công và trong thư mục transdocx có 1 thư mục con tên là dist. Ứng dụng mới được tạo nằm trong đó. Bây giờ hãy copy file config.yaml và dán bản sao nó vào trong thư mục dist. Giờ đây bạn có thể mở app dịch và dùng tự do.

