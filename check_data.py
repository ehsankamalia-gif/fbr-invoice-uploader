import pymysql

conn = pymysql.connect(host='127.0.0.1', user='root', password='', db='honda_fbr')
cursor = conn.cursor()

print("Checking invoice_items...")
cursor.execute("SELECT COUNT(*) FROM invoice_items WHERE motorcycle_id IS NULL AND (chassis_number IS NOT NULL OR engine_number IS NOT NULL)")
count = cursor.fetchone()[0]
print(f"Items with missing motorcycle_id but present chassis/engine: {count}")

print("Checking invoices buyer info...")
cursor.execute("SELECT COUNT(DISTINCT buyer_cnic) FROM invoices WHERE buyer_cnic IS NOT NULL")
count = cursor.fetchone()[0]
print(f"Unique buyers in invoices: {count}")

conn.close()
