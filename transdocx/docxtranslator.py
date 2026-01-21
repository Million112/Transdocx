import os
import sys  # THÊM IMPORT NÀY
from transdocx.worker.extractor import Extractor
from transdocx.worker.injector import Injector
from transdocx.worker.translator import Translator


class DocxTranslator:
    def __init__(self, input_file: str, output_dir: str = "output", openai_api_key: str = "", model: str = "gpt-4o-mini", source_lang: str = "English", target_lang: str = "Vietnamese", max_chunk_size: int = 5000, max_concurrent: int = 100):
        self.input_file = input_file
        self.output_dir = output_dir
        self.openai_api_key = openai_api_key
        self.model = model
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.max_chunk_size = max_chunk_size
        self.max_concurrent = max_concurrent
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Please provide a valid OpenAI API key.")

        # QUAN TRỌNG: Xử lý đường dẫn trong môi trường exe
        self._setup_paths()

        # Initialize pipeline components
        self.extractor = Extractor(self.input_file, self.checkpoint_file)
        self.translator = Translator(self.checkpoint_file, self.openai_api_key, self.model, self.source_lang, self.target_lang, self.max_chunk_size, self.max_concurrent)
        self.injector = Injector(self.input_file, self.checkpoint_file, self.output_file)

    def _setup_paths(self):
        """Xử lý đường dẫn file để hoạt động trong cả môi trường exe và Python thông thường"""
        
        # In ra thông tin debug
        print(f"[DEBUG] Current directory: {os.getcwd()}")
        print(f"[DEBUG] Input file: {self.input_file}")
        
        # Xử lý đường dẫn output directory
        if not os.path.isabs(self.output_dir):
            # Nếu là đường dẫn tương đối, tạo đường dẫn tuyệt đối
            if getattr(sys, 'frozen', False):
                # Đang chạy từ exe
                base_dir = os.path.dirname(sys.executable)
            else:
                # Đang chạy từ Python script
                base_dir = os.getcwd()
            
            self.output_dir = os.path.join(base_dir, self.output_dir)
        
        print(f"[DEBUG] Output directory: {self.output_dir}")
        
        # Đảm bảo thư mục output tồn tại
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[DEBUG] Created/verified output directory: {self.output_dir}")
        
        # Derive filenames
        file_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.checkpoint_file = os.path.join(self.output_dir, f"{file_name}_checkpoint.json")
        self.output_file = os.path.join(self.output_dir, f"{file_name}_translated.docx")
        
        print(f"[DEBUG] Checkpoint file: {self.checkpoint_file}")
        print(f"[DEBUG] Output file: {self.output_file}")

    def translate(self):
        """Run the entire translation pipeline"""
        print("[INFO] Starting translation pipeline...")
        self.extract()
        self.translator.translate()
        self.inject()
        print("[INFO] Translation pipeline completed.")
    
    async def atranslate(self):
        """Run the entire translation pipeline asynchronously"""
        print("[INFO] Starting async translation pipeline...")
        self.extract()
        await self.translator._translate_all()
        self.inject()
        print("[INFO] Async translation pipeline completed.")

    def extract(self):
        """Extract segments and save checkpoint"""
        print("[INFO] Extracting content from document...")
        self.extractor.extract()
        print("[INFO] Extraction completed.")

    def inject(self):
        """Inject translated segments into a new DOCX file"""
        print("[INFO] Injecting translated content into document...")
        self.injector.inject()
        print("[INFO] Injection completed.")

    def get_output_path(self) -> str:
        """Return the absolute path of the translated file"""
        return os.path.abspath(self.output_file)