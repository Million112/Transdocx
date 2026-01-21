"""
GUI Application for Translator
Run with: python gui_app.py
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import yaml
import logging

# Add current directory to path to import transdocx modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from transdocx import DocxTranslator
from transdocx.utils.spinner import Spinner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Translator app")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        # Set icon if available
        try:
            self.root.iconbitmap("icon.ico")  # Optional: add an icon file
        except:
            pass
        
        # Variables
        self.input_file = tk.StringVar()
        self.config = self.load_config()
        self.translation_thread = None
        self.is_translating = False
        
        # Setup UI
        self.setup_ui()
        
        # Center window on screen
        self.center_window()
    
    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_config(self):
        """Load configuration from config.yaml - FIXED for PyInstaller"""
        import sys
        import os
        
        # Debug: In ra các thông tin
        print(f"Current directory: {os.getcwd()}")
        print(f"Executable path: {sys.executable}")
        print(f"MEIPASS: {getattr(sys, '_MEIPASS', 'Not in PyInstaller')}")
        
        # Các vị trí có thể tìm thấy config.yaml
        possible_locations = []
        
        # 1. Thư mục chứa file exe (quan trọng nhất)
        if getattr(sys, 'frozen', False):
            # Đang chạy từ PyInstaller
            exe_dir = os.path.dirname(sys.executable)
            possible_locations.append(os.path.join(exe_dir, "config.yaml"))
            possible_locations.append(os.path.join(exe_dir, "..", "config.yaml"))
        else:
            # Đang chạy từ Python script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            possible_locations.append(os.path.join(script_dir, "config.yaml"))
        
        # 2. Thư mục hiện tại
        possible_locations.append("config.yaml")
        possible_locations.append("./config.yaml")
        
        # 3. Thư mục làm việc hiện tại
        possible_locations.append(os.path.join(os.getcwd(), "config.yaml"))
        
        # 4. Trong MEIPASS (PyInstaller temp folder)
        if getattr(sys, '_MEIPASS', None):
            possible_locations.append(os.path.join(sys._MEIPASS, "config.yaml"))
        
        print(f"Looking for config in: {possible_locations}")
        
        for config_path in possible_locations:
            try:
                if os.path.exists(config_path):
                    print(f"Found config at: {config_path}")
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    logger.info(f"✓ Loaded config from {config_path}")
                    
                    # Check for API key
                    if not config.get("openai_api_key"):
                        print("Warning: API key missing in config")
                    return config
            except Exception as e:
                print(f"Error reading {config_path}: {e}")
                continue
        
        # Nếu không tìm thấy file nào
        error_msg = "✗ Config file not found in any location. Tried:\n" + "\n".join(possible_locations)
        logger.error(error_msg)
        
        # Tạo config mẫu nếu không tìm thấy
        sample_config = """openai_api_key: ""  # Thêm API key của bạn
    model: "gpt-4o-mini"
    source_lang: "English"
    target_lang: "Vietnamese"
    max_concurrent: 100
    max_chunk_size: 5000
    """
        
        # Tạo file config mẫu
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write(sample_config)
        print("Created sample config.yaml file")
        
        messagebox.showerror(
            "Config Error", 
            "config.yaml not found!\n\n"
            "I've created a sample config.yaml file for you.\n"
            "Please:\n"
            "1. Open config.yaml\n"
            "2. Add your OpenAI API key\n"
            "3. Restart the application\n\n"
            "The config.yaml should be in the same folder as translator.exe"
        )
        return {}
    
    def setup_ui(self):
        """Setup the user interface"""
        # Title
        title_label = ttk.Label(
            self.root, 
            text="📄 Document Translator", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)
        
        # File selection frame
        file_frame = ttk.Frame(self.root)
        file_frame.pack(pady=10, padx=20, fill="x")
        
        ttk.Label(file_frame, text="Select DOCX File:", font=("Arial", 10)).pack(anchor="w")
        
        # File path display and browse button
        path_frame = ttk.Frame(file_frame)
        path_frame.pack(fill="x", pady=5)
        
        self.file_entry = ttk.Entry(path_frame, textvariable=self.input_file, state="readonly")
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(
            path_frame, 
            text="📁 Browse", 
            command=self.browse_file,
            width=10
        )
        browse_btn.pack(side="right")
        
        # Info label for selected file
        self.file_info = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.file_info.pack(anchor="w", pady=(0, 10))
        
        # Config info
        config_frame = ttk.Frame(self.root)
        config_frame.pack(pady=10, padx=20, fill="x")
        
        source_lang = self.config.get("source_lang", "English")
        target_lang = self.config.get("target_lang", "Vietnamese")
        model = self.config.get("model", "gpt-4o-mini")
        
        config_text = f"📝 Config: {source_lang} → {target_lang} | Model: {model}"
        ttk.Label(config_frame, text=config_text, font=("Arial", 9)).pack(anchor="w")
        
        # Translate button
        self.translate_btn = ttk.Button(
            self.root,
            text="🚀 Translate Document",
            command=self.start_translation,
            state="disabled",
            width=20
        )
        self.translate_btn.pack(pady=20)
        
        # Progress/Status label
        self.status_label = ttk.Label(
            self.root, 
            text="Ready", 
            font=("Arial", 10),
            foreground="green"
        )
        self.status_label.pack(pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.root, 
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=5)
        
        # Output directory info
        output_info = ttk.Label(
            self.root,
            text="📁 Output folder: ./output/",
            font=("Arial", 9),
            foreground="blue"
        )
        output_info.pack(pady=10)
    
    def browse_file(self):
        """Open file dialog to select DOCX file"""
        file_path = filedialog.askopenfilename(
            title="Select DOCX File",
            filetypes=[("Word Documents", "*.docx"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.input_file.set(file_path)
            
            # Update file info
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / 1024  # KB
            
            if file_path.lower().endswith('.docx'):
                self.file_info.config(
                    text=f"✅ Selected: {file_name} ({file_size:.1f} KB)",
                    foreground="green"
                )
                self.translate_btn.config(state="normal")
            else:
                self.file_info.config(
                    text=f"⚠️ Selected file is not .docx: {file_name}",
                    foreground="orange"
                )
                self.translate_btn.config(state="disabled")
    
    def start_translation(self):
        """Start the translation process in a separate thread"""
        if not self.input_file.get():
            messagebox.showwarning("No File", "Please select a DOCX file first.")
            return
        
        # Check API key
        if not self.config.get("openai_api_key"):
            messagebox.showerror(
                "API Key Required",
                "OpenAI API key is missing in config.yaml.\n"
                "Please add your API key to config.yaml and restart the application."
            )
            return
        
        # Disable UI during translation
        self.translate_btn.config(state="disabled", text="⏳ Translating...")
        self.status_label.config(text="Processing...", foreground="orange")
        self.progress.start(10)
        self.is_translating = True
        
        # Start translation in separate thread
        self.translation_thread = threading.Thread(target=self.run_translation, daemon=True)
        self.translation_thread.start()
        
        # Check translation status periodically
        self.root.after(100, self.check_translation_status)
    
    def run_translation(self):
        """Run the actual translation (in background thread)"""
        try:
            # Get configuration
            input_file = self.input_file.get()
            output_dir = "output"
            
            # Initialize and run translator
            docx_translator = DocxTranslator(
                input_file=input_file,
                output_dir=output_dir,
                openai_api_key=self.config.get("openai_api_key"),
                model=self.config.get("model", "gpt-4o-mini"),
                source_lang=self.config.get("source_lang", "English"),
                target_lang=self.config.get("target_lang", "Vietnamese"),
                max_chunk_size=self.config.get("max_chunk_size", 5000),
                max_concurrent=self.config.get("max_concurrent", 100)
            )
            
            docx_translator.translate()
            self.translation_success = True
            self.output_path = docx_translator.get_output_path()
            
        except Exception as e:
            self.translation_success = False
            self.error_message = str(e)
            logger.error(f"Translation error: {e}")
    
    def check_translation_status(self):
        """Check if translation thread is done"""
        if self.translation_thread.is_alive():
            # Still running, check again after 100ms
            self.root.after(100, self.check_translation_status)
        else:
            # Translation finished
            self.progress.stop()
            self.is_translating = False
            
            if hasattr(self, 'translation_success') and self.translation_success:
                # Success
                self.translate_btn.config(state="normal", text="🚀 Translate Document")
                self.status_label.config(text="✅ Translation Completed!", foreground="green")
                
                # Show success message with output path
                output_file = os.path.basename(self.output_path)
                messagebox.showinfo(
                    "Translation Complete",
                    f"✅ Translation completed successfully!\n\n"
                    f"File saved to:\n{self.output_path}\n\n"
                    f"Please check the 'output' folder for the translated document."
                )
                
            else:
                # Error
                self.translate_btn.config(state="normal", text="🚀 Translate Document")
                self.status_label.config(text="❌ Translation Failed", foreground="red")
                
                error_msg = getattr(self, 'error_message', 'Unknown error')
                messagebox.showerror(
                    "Translation Failed",
                    f"❌ Translation failed:\n{error_msg}"
                )
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_translating:
            if messagebox.askyesno("Confirm", "Translation is in progress. Are you sure you want to quit?"):
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """Main entry point for GUI application"""
    root = tk.Tk()
    app = TranslatorApp(root)
    
    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    main()