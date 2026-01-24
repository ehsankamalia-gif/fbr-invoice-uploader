import sqlite3

def inspect():
    conn = sqlite3.connect('fbr_invoices.db')
    cursor = conn.cursor()
    
    print("--- Motorcycles Table Info ---")
    try:
        cursor.execute("PRAGMA table_info(motorcycles)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(e)
        
    print("\n--- Product Models Table Info ---")
    try:
        cursor.execute("PRAGMA table_info(product_models)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(e)

    conn.close()

if __name__ == "__main__":
    inspect()
