import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fbr_uploader.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    # 1. Handle Splash Screen (only works in frozen mode)
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.update_text("Loading components...")
    except ImportError:
        pass

    # 2. Heavy Imports (Delayed to allow splash screen to show first)
    try:
        from app.ui.main_window import App
    except (AssertionError, ImportError) as e:
        # Catching specific SQLAlchemy/Typing error common in wrong environments
        if "SQLCoreOperations" in str(e) or "TypingOnly" in str(e):
            print("\n" + "="*60)
            print("CRITICAL ERROR: INCOMPATIBLE ENVIRONMENT DETECTED")
            print("="*60)
            print(f"Error details: {e}")
            print("-" * 60)
            print("You are likely running this application with a Python environment")
            print("that has incompatible libraries installed.")
            print("\nPLEASE FOLLOW THESE STEPS:")
            print("1. Do not run 'python -m app.main' directly.")
            print("2. Instead, double-click 'run.bat' in the project folder.")
            print("   OR run 'run.bat' from the terminal.")
            print("="*60 + "\n")
            input("Press Enter to exit...")
            sys.exit(1)
        raise

    # 3. Close Splash Screen
    try:
        import pyi_splash
        if pyi_splash.is_alive():
            pyi_splash.close()
    except ImportError:
        pass

    # 4. Run App
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
