"""
Build script to create translator.exe using PyInstaller
Run: python build_exe.py
"""
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
        '--onefile',  # Single executable
        '--windowed',  # No console window
        # '--icon=icon.ico',  # Optional: add if you have an icon
        '--add-data=config.yaml;.',  # Include config file
        '--add-data=transdocx;transdocx',  # Include package
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