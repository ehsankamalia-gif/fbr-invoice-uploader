import PyInstaller.__main__
import os
import shutil
import customtkinter
import certifi

def build():
    # Define assets to include
    # Format: "source;dest" for Windows
    assets = [
        ("assets", "assets"),
        ("capture_config.json", "."),
        ("invoice_print_layout.json", ".")
    ]
    
    # Construct --add-data arguments
    add_data_args = []
    
    # Add CustomTkinter assets (theme files, etc.)
    ctk_path = os.path.dirname(customtkinter.__file__)
    add_data_args.append(f"--add-data={ctk_path};customtkinter/")

    # Add certifi cacert.pem
    certifi_path = os.path.join(os.path.dirname(certifi.__file__), 'cacert.pem')
    if os.path.exists(certifi_path):
        add_data_args.append(f"--add-data={certifi_path};certifi/")
    else:
        print("Warning: certifi cacert.pem not found")
    
    for src, dst in assets:
        if os.path.exists(src):
            add_data_args.append(f"--add-data={src};{dst}")
        else:
            print(f"Warning: Asset {src} not found, skipping.")

    # Hidden imports for libraries that PyInstaller might miss
    hidden_imports = [
        "--hidden-import=babel.numbers",
        "--hidden-import=pymysql",
        "--hidden-import=PIL",
        "--hidden-import=customtkinter",
        "--hidden-import=requests",
        "--hidden-import=tenacity",
        "--hidden-import=playwright",
        "--hidden-import=app.services.form_capture_service", # Dynamic import sometimes
    ]

    # Main PyInstaller arguments
    args = [
        "fbr_invoice_uploader/app/main.py",  # Entry point
        "--paths=fbr_invoice_uploader",      # Add inner repo to path
        "--name=Honda_FBR_Uploader",         # EXE name
        "--onefile",                       # Single EXE file
        "--windowed",                      # No console window
        "--clean",                         # Clean cache
        "--noconfirm",                     # Overwrite output
        # "--icon=assets/icon.ico",       # Icon (if available)
    ] + add_data_args + hidden_imports

    print("Starting build process...")
    print(f"Command args: {args}")
    
    PyInstaller.__main__.run(args)
    
    print("\nBuild complete. Check 'dist' folder for the executable.")

if __name__ == "__main__":
    build()
