import pymysql

conn = pymysql.connect(host='127.0.0.1', user='root', password='', db='honda_fbr')
cursor = conn.cursor()

print("--- ALL TABLES ---")
cursor.execute("SHOW TABLES")
all_tables = [row[0] for row in cursor.fetchall()]
print(all_tables)

tables = ['fbr_configurations', 'purchase_order_items', 'purchase_orders', 'suppliers', 'users']
for t in tables:
    if t not in all_tables:
        print(f"\nSkipping {t} (Not Found)")
        continue
    print(f"\n--- {t} ---")
    cursor.execute(f"DESCRIBE {t}")
    for row in cursor.fetchall():
        print(row)

conn.close()
