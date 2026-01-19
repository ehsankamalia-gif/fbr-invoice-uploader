from app.services.settings_service import settings_service
import json

def check_settings():
    settings = settings_service.get_active_settings()
    print("Active Settings:")
    print(json.dumps(settings, indent=4, default=str))

if __name__ == "__main__":
    check_settings()
