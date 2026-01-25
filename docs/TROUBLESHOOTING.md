# Troubleshooting Guide

## Common Issues

### 1. FBR API Connection Failed
**Symptoms**: "Sync Failed" message, logs show `ConnectionError`.
**Solution**:
- Check your internet connection.
- Verify FBR API URL in `.env`.
- Ensure FBR services are up (they sometimes have downtime).

### 2. Authentication Error
**Symptoms**: HTTP 401/403 errors.
**Solution**:
- Check `FBR_AUTH_TOKEN` in `.env`.
- Ensure your POS ID and USIN are correct and registered.
- Tokens may expire; generate a new one from FBR portal.

### 3. Database Locked
**Symptoms**: Application freezes or errors about "database locked".
**Solution**:
- Restart the application.
- Ensure no other instance is running.

### 4. Fiscalization Errors
**Symptoms**: Invoice rejected by FBR.
**Solution**:
- Check log file `fbr_uploader.log` for specific error messages from FBR.
- Common causes: Duplicate Invoice Number, Invalid NTN, Invalid HS Code.
