import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def assign_chemical_to_all_without_services():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Get all chemical services (should have service_type='chemical')
    cursor.execute("""
        SELECT id, name, location_id FROM services WHERE service_type = 'chemical' LIMIT 1
    """)
    chemical_service = cursor.fetchone()
    
    if not chemical_service:
        print("No chemical service found in database!")
        conn.close()
        return
    
    chemical_service_id = chemical_service[0]
    chemical_service_name = chemical_service[1]
    print(f"Found chemical service: ID={chemical_service_id}, Name={chemical_service_name}")
    
    # Find all customers who have NO services assigned
    cursor.execute("""
        SELECT c.id, c.name, c.location_id
        FROM customers c
        WHERE c.id NOT IN (
            SELECT DISTINCT customer_id FROM customer_services
        )
    """)
    
    customers_without_services = cursor.fetchall()
    print(f"\nFound {len(customers_without_services)} customers without any services:")
    
    assigned_count = 0
    for customer in customers_without_services:
        customer_id = customer[0]
        customer_name = customer[1]
        customer_location = customer[2]
        
        # Assign chemical service to this customer
        try:
            cursor.execute("""
                INSERT INTO customer_services (customer_id, service_id, price, is_active)
                VALUES (?, ?, 0, 1)
            """, (customer_id, chemical_service_id))
            assigned_count += 1
            print(f"  [OK] Assigned chemical service to {customer_name} (ID: {customer_id})")
        except sqlite3.IntegrityError:
            print(f"  [SKIP] Service already exists for {customer_name}")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"SUMMARY: Assigned chemical service to {assigned_count} customers")
    print(f"{'='*50}")

if __name__ == "__main__":
    assign_chemical_to_all_without_services()
