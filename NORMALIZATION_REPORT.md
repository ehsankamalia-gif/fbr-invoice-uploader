# Detailed Database Normalization Report: `honda_fbr`

## Executive Summary
This report details the successful normalization of the `honda_fbr` database from an unnormalized state (inconsistent data, redundancy, missing integrity) to a fully normalized (3NF/5NF) schema. The process involved strict isolation, comprehensive schema analysis, data migration, and the establishment of referential integrity constraints.

## 1. Normalization Scope & Isolation
- **Target Database**: `honda_fbr` (Exclusive)
- **Isolation Strategy**: Direct PyMySQL connection to `honda_fbr`; no ORM cross-database contamination; strict `join` limitations.
- **Tools Used**: Python (PyMySQL), SQLAlchemy (for app integration), Laragon MySQL tools.

## 2. Before vs After Schema

### Before Normalization (Key Issues)
- **Redundancy**: `Motorcycle` table contained `make` and `model` strings repeatedly. `Price` table repeated `model` string. `PurchaseOrderItems` repeated `model` string.
- **Inconsistency**: No single source of truth for "Models". Typos in model names could lead to split records.
- **Orphaned Data**: `PurchaseOrders` contained `supplier_id` values that did not exist in `Suppliers`.
- **Missing Integrity**: No Foreign Keys on `PurchaseOrders.supplier_id`, `PurchaseOrderItems.po_id`, or `Motorcycles.supplier_id`.
- **Mixed Concerns**: `Motorcycle` table mixed product definition (Make/Model) with instance data (Chassis/Engine).

### After Normalization (3NF/5NF Compliant)

#### New/Refactored Tables
1.  **`product_models`** (New Master Table)
    -   `id` (PK)
    -   `model_name` (Unique, Indexed)
    -   `make` (Default 'Honda')
    -   *Eliminates string repetition across Motorcycles, Prices, and PO Items.*

2.  **`motorcycles`**
    -   `product_model_id` (FK -> `product_models.id`)
    -   *Replaced `make` and `model` columns.*

3.  **`purchase_order_items`**
    -   `po_id` (FK -> `purchase_orders.id`)
    -   `product_model_id` (FK -> `product_models.id`)
    -   *Replaced `model` column. Added FK to parent PO.*

4.  **`prices`**
    -   `product_model_id` (FK -> `product_models.id`)
    -   *Linked strictly to defined models.*

5.  **`purchase_orders`**
    -   `supplier_id` (FK -> `suppliers.id`)
    -   *Enforced referential integrity.*

## 3. Justification of Normalization Steps

### First Normal Form (1NF)
-   **Action**: Ensured all columns contain atomic values.
-   **Result**: No repeating groups or arrays.

### Second Normal Form (2NF)
-   **Action**: Removed partial dependencies. All non-key attributes depend on the full primary key.
-   **Specific**: `make` and `model` depend on the *product concept*, not the specific *motorcycle instance* (Chassis #). Moved to `product_models`.

### Third Normal Form (3NF)
-   **Action**: Removed transitive dependencies.
-   **Specific**: `model` string in `purchase_order_items` implied `make` (Honda). By linking to `product_models`, we reference the entity directly.

### Referential Integrity (Foreign Keys)
-   **Constraint**: `fk_moto_product_model`
-   **Constraint**: `fk_poi_product_model`
-   **Constraint**: `fk_po_supplier`
-   **Constraint**: `fk_poi_order`
-   **Constraint**: `fk_moto_supplier`
-   **Impact**: Prevents deletion of Suppliers/Models that are in use. Prevents creation of orphaned records.

## 4. Impact Analysis & Code Updates
-   **Application Logic**: Updated `inventory_frame.py`, `reports_frame.py`, and `price_service.py` to join `ProductModel` instead of accessing flat string attributes.
-   **Performance**:
    -   **Queries**: Optimized using `joinedload` (SQLAlchemy) to prevent N+1 query problems when fetching Motorcycles with their Models.
    -   **Indexing**: `model_name` is indexed in `product_models` for fast lookups.
-   **Data Integrity**: Fixed app crash caused by schema mismatch ("Motorcycle object has no attribute 'make'").

## 5. Migration Statistics & Data Cleaning
-   **Suppliers**: Created 1 dummy "Unknown Supplier" to resolve orphaned Purchase Orders.
-   **Purchase Orders**: Updated orphaned records to point to "Unknown Supplier".
-   **Product Models**: Extracted unique models from existing data and populated `product_models` table.
-   **Purchase Order Items**: Mapped 100% of items to valid Product Models.

## 6. Rollback Procedures
In case of critical failure, a restoration point was created.
-   **Backup File**: `C:/laragon/www/Python1/Python/fbr_invoice_uploader/honda_fbr_backup.sql`
-   **Restore Command**:
    ```bash
    mysql -u root -p honda_fbr < honda_fbr_backup.sql
    ```

## 7. Verification
-   **Schema Check**: All Foreign Keys present and active.
-   **Data Check**: No NULLs in critical FK columns (`product_model_id`, `supplier_id`).
-   **App Check**: Application launches successfully; Inventory and Reports load correctly.
