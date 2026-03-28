import os
import sqlite3

# FIXED: Points to ROOT database.db
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    sqft INTEGER NOT NULL,
    monthly_min REAL NOT NULL,
    monthly_max REAL NOT NULL
)
""")
conn.commit()

def parse_sq_ft(s):
    s = s.strip().lower()
    if s.endswith("k"):
        value = float(s[:-1]) * 1000
    else:
        value = float(s)
    if value <= 0:
        raise ValueError("Sqft must be positive")
    return int(value)

def calculate_treatment_price(sqft):
    base_small = 3000
    base_large = 10000
    price_small = 50
    price_large = 100

    if sqft <= base_small:
        price = price_small
    elif sqft >= base_large:
        price = price_large * (sqft / base_large)
    else:
        ratio = (sqft - base_small) / (base_large - base_small)
        price = price_small + ratio * (price_large - price_small)
    return price  # Price per treatment (not monthly)

def get_phone():
    while True:
        phone = input("Phone number? ")
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return digits
        print("Enter a valid 10-digit phone number.")

def main():
    print("=== Lawn Quote Tool ===\n")
    name = input("Name? ")
    address = input("Address? ")
    phone = get_phone()
    sqft_input = input("Sq ft? (e.g. 2500 or 2.5k) ")

    try:
        sqft = parse_sq_ft(sqft_input)
    except ValueError as e:
        print(e)
        return

    treatment_price = calculate_treatment_price(sqft)
    treatment_min = treatment_price * 0.9
    treatment_max = treatment_price * 1.1

    print("\n--- Quote ---")
    print(f"{name} | {address}")
    print(f"Sqft: {sqft} | Phone: {phone}")
    print(f"Per Treatment: ${treatment_min:.0f} - ${treatment_max:.0f}")

    cursor.execute("""
        INSERT INTO customers (name, address, phone, sqft, monthly_min, monthly_max)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, address, phone, sqft, treatment_min, treatment_max))
    conn.commit()
    print("\nSaved to database.db AND web app can see it!")

if __name__ == "__main__":
    try:
        main()
    finally:
        conn.close()