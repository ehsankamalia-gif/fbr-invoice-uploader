import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
