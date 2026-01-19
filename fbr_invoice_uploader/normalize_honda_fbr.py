import pymysql
import sys

def get_db_connection():
    return pymysql.connect(host='127.0.0.1', user='root', password='', db='honda_fbr', cursorclass=pymysql.cursors.DictCursor)

def run_migration():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            print("Starting Normalization of honda_fbr...")

            # 1. Purchase Orders - Supplier FK
            print("\n[1/4] Checking Purchase Orders - Supplier FK...")
            cursor.execute("SELECT COUNT(*) as cnt FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='honda_fbr' AND TABLE_NAME='purchase_orders' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_po_supplier'")
            if cursor.fetchone()['cnt'] == 0:
                print("Adding FK to purchase_orders.supplier_id...")
                # Ensure all supplier_ids exist
                cursor.execute("SELECT DISTINCT supplier_id FROM purchase_orders WHERE supplier_id NOT IN (SELECT id FROM suppliers)")
                orphans = cursor.fetchall()
                if orphans:
                    print(f"Warning: Found {len(orphans)} purchase orders with invalid supplier_ids. Setting them to NULL or creating dummy supplier.")
                    # Simple fix: Create dummy supplier if needed, or just warn. 
                    # For now, let's assume integrity or set to NULL if allowed. 
                    # Models say nullable=False. So we must fix.
                    # Create "Unknown Supplier"
                    cursor.execute("INSERT INTO suppliers (name) VALUES ('Unknown Supplier')")
                    dummy_id = conn.insert_id()
                    cursor.execute(f"UPDATE purchase_orders SET supplier_id = {dummy_id} WHERE supplier_id NOT IN (SELECT id FROM suppliers)")
                
                cursor.execute("ALTER TABLE purchase_orders ADD CONSTRAINT fk_po_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)")
                print("FK added.")
            else:
                print("FK already exists.")

            # 1.5 Fix ProductModel column name (name -> model_name)
            print("\n[1.5/4] Checking ProductModels column name...")
            cursor.execute("SHOW COLUMNS FROM product_models LIKE 'model_name'")
            if not cursor.fetchone():
                print("Renaming 'name' to 'model_name' in product_models...")
                # Check if 'name' exists
                cursor.execute("SHOW COLUMNS FROM product_models LIKE 'name'")
                if cursor.fetchone():
                    cursor.execute("ALTER TABLE product_models CHANGE COLUMN name model_name VARCHAR(50) NOT NULL")
                    print("Renamed successfully.")
                else:
                    print("Column 'name' not found either. Something is wrong.")
            else:
                print("Column 'model_name' already exists.")

            # 1.6 Add missing columns to product_models (engine_capacity, pct_code, item_code)
            print("\n[1.6/4] Checking ProductModels missing columns...")
            columns_to_check = [
                ("engine_capacity", "VARCHAR(20) NULL"),
                ("pct_code", "VARCHAR(20) NULL"),
                ("item_code", "VARCHAR(50) NULL")
            ]
            for col_name, col_def in columns_to_check:
                cursor.execute(f"SHOW COLUMNS FROM product_models LIKE '{col_name}'")
                if not cursor.fetchone():
                    print(f"Adding column '{col_name}' to product_models...")
                    cursor.execute(f"ALTER TABLE product_models ADD COLUMN {col_name} {col_def}")
                else:
                    print(f"Column '{col_name}' already exists.")

            # 2. Purchase Order Items - Product Model Normalization
            print("\n[2/4] Normalizing Purchase Order Items...")
            cursor.execute("SHOW COLUMNS FROM purchase_order_items LIKE 'product_model_id'")
            if not cursor.fetchone():
                print("Adding product_model_id column...")
                cursor.execute("ALTER TABLE purchase_order_items ADD COLUMN product_model_id INT")
                
                print("Mapping models to product_model_id...")
                # Create missing product models first
                cursor.execute("SELECT DISTINCT model FROM purchase_order_items WHERE model NOT IN (SELECT model_name FROM product_models)")
                missing_models = cursor.fetchall()
                for m in missing_models:
                    model_name = m['model']
                    print(f"Creating missing ProductModel: {model_name}")
                    cursor.execute("INSERT INTO product_models (model_name, make) VALUES (%s, 'Honda')", (model_name,))
                
                # Update IDs
                cursor.execute("""
                    UPDATE purchase_order_items poi 
                    JOIN product_models pm ON poi.model = pm.model_name 
                    SET poi.product_model_id = pm.id
                """)
                
                # Verify no NULLs
                cursor.execute("SELECT COUNT(*) as cnt FROM purchase_order_items WHERE product_model_id IS NULL")
                nulls = cursor.fetchone()['cnt']
                if nulls > 0:
                    raise Exception(f"Failed to map {nulls} items to product models.")
                
            else:
                print("product_model_id already exists.")

            # Check if 'model' column still exists
            cursor.execute("SHOW COLUMNS FROM purchase_order_items LIKE 'model'")
            if cursor.fetchone():
                print("Dropping old 'model' column...")
                cursor.execute("ALTER TABLE purchase_order_items DROP COLUMN model")
            
            # Check FK
            cursor.execute("SELECT COUNT(*) as cnt FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='honda_fbr' AND TABLE_NAME='purchase_order_items' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_poi_product_model'")
            if cursor.fetchone()['cnt'] == 0:
                print("Adding FK fk_poi_product_model...")
                # Ensure not null
                cursor.execute("ALTER TABLE purchase_order_items MODIFY COLUMN product_model_id INT NOT NULL")
                cursor.execute("ALTER TABLE purchase_order_items ADD CONSTRAINT fk_poi_product_model FOREIGN KEY (product_model_id) REFERENCES product_models(id)")
                print("Done.")
            else:
                print("FK fk_poi_product_model already exists.")

            # 3. Purchase Order Items - PO FK
            print("\n[3/4] Checking Purchase Order Items - PO FK...")
            cursor.execute("SELECT COUNT(*) as cnt FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='honda_fbr' AND TABLE_NAME='purchase_order_items' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_poi_order'")
            if cursor.fetchone()['cnt'] == 0:
                print("Adding FK to purchase_order_items.po_id...")
                # Cleanup orphans
                cursor.execute("DELETE FROM purchase_order_items WHERE po_id NOT IN (SELECT id FROM purchase_orders)")
                cursor.execute("ALTER TABLE purchase_order_items ADD CONSTRAINT fk_poi_order FOREIGN KEY (po_id) REFERENCES purchase_orders(id) ON DELETE CASCADE")
                print("FK added.")
            else:
                print("FK already exists.")

            # 4. Motorcycles - Supplier FK
            print("\n[4/4] Checking Motorcycles - Supplier FK...")
            # Check if column exists first (Models have it, DB might not)
            cursor.execute("SHOW COLUMNS FROM motorcycles LIKE 'supplier_id'")
            if not cursor.fetchone():
                print("Adding supplier_id column to motorcycles...")
                cursor.execute("ALTER TABLE motorcycles ADD COLUMN supplier_id INT")
                cursor.execute("ALTER TABLE motorcycles ADD CONSTRAINT fk_moto_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)")
            else:
                # Check FK
                cursor.execute("SELECT COUNT(*) as cnt FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA='honda_fbr' AND TABLE_NAME='motorcycles' AND CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_NAME='fk_moto_supplier'")
                if cursor.fetchone()['cnt'] == 0:
                    print("Adding FK fk_moto_supplier...")
                    # Handle invalid supplier_ids if any data exists
                    cursor.execute("UPDATE motorcycles SET supplier_id = NULL WHERE supplier_id NOT IN (SELECT id FROM suppliers)")
                    cursor.execute("ALTER TABLE motorcycles ADD CONSTRAINT fk_moto_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)")
                    print("FK added.")
                else:
                    print("FK already exists.")

            conn.commit()
            print("\nNormalization Complete Successfully!")

    except Exception as e:
        print(f"\nError: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
