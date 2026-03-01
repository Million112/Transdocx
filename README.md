# Transdocx
Ứng dụng đã được tích hợp đầy đủ 2 tính năng dịch bằng API OpenAI và model dịch tự train MarianMT

## Cài đặt sơ bộ

### Bước 1: Clone thư mục về máy tính

### Bước 2: Mở cmd và di chuyển tới thư mục transdocx

### Bước 3: Nhập lệnh phía dưới vào để máy tự chạy tải các thiết bị cần thiết

`pip install -r requirements_gui.txt`

### Bước 4: Tạo 1 folder trống tên output trong thư mục transdocx

## Cài đặt dịch bằng API OpenAI 

Nếu bạn chỉ muốn sử dụng dịch bằng MarianMT thì có thể bỏ qua phần này

### Bước 1: Tạo một file config.yaml trong thư mục transdocx với nội dung như sau:

```openai_api_key: "" # Your OpenAI API key here
# --- Cấu hình chung ---
source_lang: "English"
target_lang: "Vietnamese"
default_engine: "openai"  # Lựa chọn mặc định khi mở app: "openai" hoặc "marian"

# --- Cấu hình OpenAI (Cloud API) ---
openai_api_key: ""  # Giữ nguyên key cũ của bạn
model: "gpt-4o-mini"
max_concurrent: 100
max_chunk_size: 5000

# --- Cấu hình MarianMT (Local Model) ---
marian_model_path: "./my_custom_marianMT"
marian_device: "cuda"  # Đổi thành "cuda" nếu máy bạn có card rời NVIDIA và đã cài CUDA
```

### Bước 2: Tự tạo API key openAI của bạn và điền vào phần 'openai_api_key:' nằm trong 2 thư mục config.yaml và gui_app.py

## Cài đặt dịch bằng mô hình học máy MarianMT

Nếu bạn chỉ muốn sử dụng dịch bằng API phía trên thì có thể bỏ qua phần này

### Bước 1: Cài đặt chạy bằng GPU

Nếu bạn không có GPU như NVDIA thì có thể bỏ qua bước này, ở đây tôi sử dụng NVIDIA gtx1650

Nếu bạn chỉ cài pip install torch bình thường, có thể nó sẽ chỉ cài bản CPU. Để tận dụng sức mạnh của card đồ họa, người dùng nên cài bản hỗ trợ CUDA.

Sửa lại file cofig.yaml từ `cuda` thành `cpu`

Lệnh cài cho máy có GPU NVIDIA: `pip install torch --index-url https://download.pytorch.org/whl/cu121`

### Bước 2: Chạy thực thi chương trình train model

Hiện tại tôi đã có dữ liệu sẵn là 10000 câu anh-việt trong file train_data.csv. Nếu bạn muốn thay đổi có thể sửa đổi code trong file extract_data.py

Nhập lệnh sau để train model: `python train_model.py`

Model sẽ train 10000 câu này 4 lần, với gtx1650 của tôi mất tầm gần 3 tiếng, nó sẽ lâu hoặc nhanh hơn tùy thuộc vào máy của bạn. Sau khi train xong, máy sẽ xuất hiện một thư mục tên là `my_custom_marianMT`.

## Chạy thử chương trình
Ở đây tôi sẽ thử với file sample3.docx đã có sẵn trong thư mục transdocx
### Cách 1: Chạy thử GUI dịch file
Vào cmd ban nãy và nhập lệnh phía dưới để mở GUI dịch file sample3.docx:
`python gui_app.py`

Nó sẽ hiển thị ra một GUI dịch cho bạn sử dụng

### Cách 2: Build app .exe để có thể mở ở bất kì đâu trên máy tính
Nhập lệnh phía dưới vào cmd:
`python build_exe.py`
Chương trình sẽ mất khoảng 5-15p để build app dịch. Sau khi hoàn tất, bạn sẽ thấy cmd hiển thị build thành công và trong thư mục transdocx có 1 thư mục con tên là dist, file .exe nằm trong dist/translator/. Giờ đây bạn có thể mở app dịch và dùng tự do.

