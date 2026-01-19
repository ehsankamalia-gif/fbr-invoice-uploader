# FBR Invoice Uploader - Integration Documentation

## Overview
This document details the FBR Invoice Uploader system, specifically focusing on the 2025 Refactoring for Dynamic Settings, Transactional Integrity, and Robust Error Handling.

## Key Features

### 1. Dynamic FBR Settings (Database-Driven)
- **Single Source of Truth**: Settings are no longer hard-coded in `.env` files. They are stored in the `fbr_configurations` database table.
- **Runtime Fetching**: All services (`InvoiceService`, `FBRClient`, `MainWindow`) fetch the *active* configuration from the database at the moment of execution.
- **Immediate Effect**: Changes made via the "FBR Settings" UI take effect immediately without restarting the application.
- **Environment Support**: Supports multiple environments (e.g., `SANDBOX`, `PRODUCTION`) with easy switching.

### 2. Transactional Integrity & Data Safety
- **Commit-on-Success**: Invoices are saved to the local database *only* if the FBR API returns a successful response (`Response: Success`, `Code: 100`).
- **Rollback-on-Failure**: If FBR returns an error, times out, or returns an empty response, the database transaction is rolled back. No "ghost" invoices are created.
- **Echo Detection**: The system validates that FBR did not just echo back the request without a valid FBR Invoice Number.

### 3. Architecture
- **Service-Based**: Logic is encapsulated in `InvoiceService`, `SettingsService`, and `FBRClient`.
- **Dependency Injection**: Database sessions are passed explicitly to services.
- **Lazy Loading**: Database connections are established only when needed to prevent connection leaks.

## Configuration

### Database Schema (`fbr_configurations`)
| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary Key |
| `env` | String | Environment Name (e.g., "SANDBOX") |
| `api_base_url` | String | FBR API Endpoint URL |
| `pos_id` | String | Point of Sale ID |
| `usin` | String | Unique Sales Invoice Number Prefix |
| `auth_token` | String | Bearer Token for Authentication |
| `tax_rate` | Float | Sales Tax Rate (e.g., 18.0) |
| `is_active` | Boolean | Only one config can be active at a time |

### Managing Settings
1. Open the Application.
2. Go to **Settings > FBR Configuration**.
3. Modify parameters (POS ID, Token, Tax Rate).
4. Click **Save**.
5. The new settings are immediately active.

## Error Handling

### Invoice Creation Flow
1. **Validation**: Input data (Buyer, Items) is validated.
2. **Settings Fetch**: Active settings are retrieved from DB.
3. **Payload Transformation**: Data is converted to FBR-compliant JSON (PascalCase).
4. **API Transmission**:
   - Retries: Up to 3 times with exponential backoff for network glitches.
   - Timeout: 10 seconds.
5. **Response Verification**:
   - Check HTTP Status (200 OK).
   - Check JSON Body (`Response` == "Success").
   - Check `InvoiceNumber` (Must be valid and not echoed).
6. **Persistence**:
   - **Success**: Commit to DB.
   - **Failure**: Rollback transaction, Log error, Show alert to user.

## Troubleshooting

### Common Errors
- **"FBR Error: 401 - Unauthorized"**: The Auth Token in settings is invalid or expired. Update it in FBR Settings.
- **"FBR returned echoed Invoice Number"**: The FBR API is in a glitch state where it returns the request ID instead of a new Invoice ID. The system prevented saving this invalid invoice.
- **"Received empty response from FBR"**: The API is down or blocking requests.

### Logs
- Application logs are stored in `app.log` (if configured) or printed to console.
- Look for `AUDIT` logs to track invoice submission attempts.

## Developer Notes
- **Testing**: Run `pytest tests/test_fbr_db_integration.py` to verify transactional safety.
- **Extending**: Add new fields to `FBRConfiguration` model and `SettingsService` if FBR requirements change.
