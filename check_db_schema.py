#!/usr/bin/env python3
"""
Database Schema Checker for Honda FBR Invoice Uploader
"""

import sqlite3
import os

def check_database_schema():
    """Check and display the current database schema"""
    db_path = 'fbr_invoices.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file '{db_path}' not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"📊 Database Schema for: {db_path}")
        print(f"📋 Total Tables: {len(tables)}")
        print("=" * 50)
        
        for table in tables:
            table_name = table[0]
            print(f"\n🗃️  Table: {table_name}")
            print("-" * 30)
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print(f"{'Column Name':<20} {'Type':<15} {'Nullable':<10} {'Default':<15}")
            print("-" * 60)
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                col_notnull = "NOT NULL" if col[3] else "NULL"
                col_default = str(col[4]) if col[4] is not None else "None"
                print(f"{col_name:<20} {col_type:<15} {col_notnull:<10} {col_default:<15}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            print(f"📈 Row Count: {row_count}")
            
            # Get indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            if indexes:
                print(f"🔑 Indexes:")
                for idx in indexes:
                    print(f"  - {idx[1]} ({'UNIQUE' if idx[2] else 'NON-UNIQUE'})")
        
        # Check for any database constraints or foreign keys
        print("\n" + "=" * 50)
        print("🔍 Additional Database Information:")
        
        # Get foreign keys
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                print(f"\n🔗 Foreign Keys in {table_name}:")
                for fk in foreign_keys:
                    print(f"  - {fk[3]} -> {fk[2]}.{fk[4]}")
        
        conn.close()
        
        print(f"\n✅ Database schema check completed successfully!")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    check_database_schema()