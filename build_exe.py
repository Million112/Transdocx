"""
Build script to create translator.exe using PyInstaller
Run: python build_exe.py
"""

# import sys
# import io
# import os

# # Ép hệ thống sử dụng UTF-8 để tránh lỗi 'charmap' trên Windows .exe
# os.environ["PYTHONIOENCODING"] = "utf-8"
# if sys.stdout is not None and sys.stdout.encoding != 'utf-8':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# if sys.stderr is not None and sys.stderr.encoding != 'utf-8':
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import PyInstaller.__main__
import os
import shutil
import sys

def build_exe():
    print("🔨 Building translator.exe...")
    
    # Clean up previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    
    # PyInstaller arguments
    args = [
        'gui_app.py',  # Main GUI file
        '--name=translator',
        '--onedir',  # Single executable
        #'--windowed',  # No console window,
        
        # Thêm Data
        '--add-data=config.yaml;.',
        '--add-data=transdocx;transdocx',
        '--add-data=my_custom_marianMT;my_custom_marianMT',
        
        # Các Hidden Imports cũ của bạn
        '--hidden-import=sentencepiece',
        '--hidden-import=sacremoses',
        '--hidden-import=transformers.models.marian.tokenization_marian',
        
        # --- THÊM MỚI: Bắt buộc để HuggingFace không bị crash ---
        '--collect-all=transformers',
        '--collect-all=tokenizers',
        '--copy-metadata=tqdm',
        '--copy-metadata=regex',
        '--copy-metadata=sacremoses',
        '--copy-metadata=sentencepiece',
        '--copy-metadata=requests',
        '--copy-metadata=packaging',
        '--copy-metadata=filelock',
        '--copy-metadata=numpy',

        # # --- THÊM 2 DÒNG NÀY ĐỂ FIX LỖI PROTOBUF ---
        # '--hidden-import=google.protobuf',
        # '--collect-submodules=google.protobuf',

        # # --------------------------------------------------------
        
        '--clean',
        '--noconfirm',
    ]
    
    try:
        PyInstaller.__main__.run(args)
        print("✅ Build completed successfully!")
        print(f"📁 Executable location: {os.path.abspath('dist/translator.exe')}")
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        build_exe()
    except ImportError:
        print("❌ PyInstaller not installed. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        build_exe()