#!/usr/bin/env python3
"""Fix the payment_processors table column name without losing data"""
import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    # Check current columns
    cursor.execute("PRAGMA table_info(payment_processors)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'secret_key_hash' in columns and 'secret_key_encrypted' not in columns:
        print("Renaming column: secret_key_hash -> secret_key_encrypted")
        cursor.execute("ALTER TABLE payment_processors RENAME COLUMN secret_key_hash TO secret_key_encrypted")
        conn.commit()
        print("Success! Column renamed. Your payment processor config is preserved.")
    elif 'secret_key_encrypted' in columns:
        print("Column already correct (secret_key_encrypted). No changes needed.")
    else:
        print("Neither column found. Table may be new/uninitialized.")
        
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
