from flask import Flask, request, render_template_string, redirect, session
import subprocess
import threading
import time
import secrets
import os


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


USERS = {"trinity": "123456"}


def start_main_app():
    subprocess.Popen(["python", "main.py"])


main_process = None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == 'trinity' and request.form.get('password') == '123456':
            session['logged_in'] = True
            
            global main_process
            if main_process is None:
                main_process = threading.Thread(target=start_main_app, daemon=True)
                main_process.start()
                time.sleep(2)
            
            # Force a clean 302 redirect to FastAPI front end
            return redirect('http://192.168.1.134:8000/')

    return """
<!DOCTYPE html>
<html>
<head>
    <title>LAWN OPS v2.6.1 - SECURE ACCESS</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        *{margin:0;padding:0;box-sizing:border-box;}
        body{
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            font-family: 'Inter', sans-serif;
            height: 100vh;
            overflow: hidden;
            position: relative;
        }
        .container{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10;
            background: rgba(255, 255, 255, 0.95);
            padding: 3rem 2.5rem;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            width: 90%;
            max-width: 420px;
            text-align: center;
            backdrop-filter: blur(20px);
        }
        .title{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1.5rem;
            letter-spacing: -0.025em;
        }
        .status-bar{
            background: rgba(37, 99, 235, 0.1);
            border: 1px solid #2563eb;
            padding: 1rem;
            margin-bottom: 2rem;
            border-radius: 12px;
            font-size: 0.9rem;
            color: #1e40af;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }
        .input-group{
            margin-bottom: 1.5rem;
            position: relative;
        }
        input{
            width: 100%;
            padding: 1rem 1rem 1rem 2.5rem;
            background: rgba(248, 250, 252, 0.8);
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            color: #1e293b;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        input:focus{
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
            background: rgba(255, 255, 255, 0.95);
        }
        input::placeholder{color:#94a3b8;}
        .input-icon{
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
            font-size: 1.1rem;
        }
        .login-btn{
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border: none;
            border-radius: 12px;
            color: white;
            font-family: 'Inter', sans-serif;
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .login-btn:hover{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .login-btn:active{
            transform: translateY(0);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .corner-logo{
            position: fixed;
            top: 20px;
            right: 20px;
            color: #2563eb;
            font-size: 0.8rem;
            font-family: 'Inter', sans-serif;
            z-index: 20;
            font-weight: 600;
        }
        .credentials{
            margin-top:2rem;
            font-size:0.85rem;
            color:#64748b;
        }
        .credentials div{
            margin-bottom: 0.5rem;
        }
        .credentials .small{
            font-size:0.75rem;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="corner-logo">LAWN OPS v2.6.1</div>
    <div class="container">
        <div class="title">LAWN OPS</div>
        <div class="status-bar">
            AUTHENTICATION TERMINAL ACTIVE | SECURE ROUTE SYSTEM
        </div>
        <form method="POST">
            <div class="input-group">
                <i class="input-icon">👤</i>
                <input name="username" placeholder="OPERATOR ID" required>
            </div>
            <div class="input-group">
                <i class="input-icon">🔑</i>
                <input name="password" type="password" placeholder="ACCESS CODE" required>
            </div>
            <button type="submit" class="login-btn">
                EXECUTE ACCESS PROTOCOL
            </button>
        </form>
        <div class="credentials">
            <div>TRINITY / 123456</div>
            <div class="small">FIELD OPS CLEARANCE LEVEL 1</div>
        </div>
    </div>
</body>
</html>
"""


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/', methods=['GET', 'POST'])
def root():
    return login()


if __name__ == '__main__':
    print("=" * 60)
    print("🔥 HACKER LOGIN TERMINAL - LAWN OPS v2.6.1")
    print("=" * 60)
    print("👤 OPERATOR: trinity")
    print("🔑 CODE:     123456")
    print("🌐 TERMINAL: http://localhost:5000")
    print("🎯 TARGET:   localhost:8000 (auto-launched)")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)

main.py

import os
import sqlite3
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import requests  # Use plain requests instead of library



# Your Geocodio API key
GEOCODIO_API_KEY = "04f1debf16fbfbffbe9fa41ba4ef969fae61ddb"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")



# ========== Geocodio Helper ==========
def geocode_geocodio(address):
    base_url = "https://api.geocod.io/v1.6/geocode"
    params = {
        "q": address,
        "api_key": GEOCODIO_API_KEY,
        "country": "US"
    }
    try:
        res = requests.get(base_url, params=params, timeout=10)
        data = res.json()
        if data.get("results"):
            loc = data["results"][0]["location"]
            return loc["lat"], loc["lng"]
        else:
            print("No results from Geocodio for:", address)
    except Exception as e:
        print("Geocodio error:", e)
    return None, None



# Database setup - SAFE notes column addition
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()



# Create table (existing customers keep old structure)
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    sqft INTEGER NOT NULL,
    monthly_min REAL NOT NULL,
    monthly_max REAL NOT NULL,
    notes TEXT DEFAULT ''
)
""")



# ADD notes column if missing (won't break existing data)
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN notes TEXT DEFAULT ''")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass



# ADD last_service_date column if missing
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN last_service_date TEXT")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass



# ADD latitude column if missing
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN lat REAL")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass



# ADD longitude column if missing
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN lng REAL")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass



# █████ ROUTE‑RELATED TABLE (new, recreation‑safe)
cursor.execute("""
CREATE TABLE IF NOT EXISTS route_selection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_rowid INTEGER NOT NULL,
    route_id INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    priority INTEGER DEFAULT 0
)
""")
conn.commit()



app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/Route_Printing.html", response_class=FileResponse)
async def read_route_printing():
    return FileResponse(os.path.join(STATIC_DIR, "Route_Printing.html"))


   
@app.get("/", response_class=FileResponse)
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))



@app.get("/routing.html", response_class=FileResponse)
async def read_routing():
    return FileResponse(os.path.join(STATIC_DIR, "routing.html"))



@app.get("/customers")
def get_customers():
    cursor.execute("""
        SELECT
            COALESCE(name, ''),
            COALESCE(address, ''),
            COALESCE(phone, ''),
            COALESCE(sqft, 0),
            COALESCE(monthly_min, 0),
            COALESCE(monthly_max, 0),
            COALESCE(notes, ''),
            last_service_date,
            rowid,
            lat,
            lng
        FROM customers ORDER BY last_service_date ASC NULLS LAST
    """)
    rows = cursor.fetchall()


    now = datetime.now().date()
    customers_with_status = []
    for row in rows:
        (
            name,
            address,
            phone,
            sqft,
            monthly_min,
            monthly_max,
            notes,
            last_service_date,
            rowid,
            lat,
            lng
        ) = row


        if last_service_date:
            last_date = datetime.fromisoformat(last_service_date).date()
            days_since = (now - last_date).days
        else:
            days_since = 9999  # never serviced


        # ===== NEW LOGIC: NEW SALES ARE IMMEDIATELY DUE =====
        # - If customer has a last_service_date and it's ≤ 45 days → due
        # - If customer has NO last_service_date (new sale) → also due
        is_due = (last_service_date is None) or (days_since >= 45)
        status = "due" if is_due else "not_due"


        customers_with_status.append(
            (
                name,
                address,
                phone,
                sqft,
                monthly_min,
                monthly_max,
                notes,
                days_since if last_service_date else None,
                status,     # c[8]
                rowid,      # c[9]
                lat,        # c[10]
                lng         # c[11]
            )
        )


    return {"customers": customers_with_status}



@app.post("/add_customer")
def add_customer(
    name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
    sqft: int = Form(...),
    monthly_min: float = Form(...),
    monthly_max: float = Form(...),
    notes: str = Form("")
):
    lat = None
    lng = None


    # Use full address, Geocodio will handle it
    full_address = f"{address}, Texas, United States"


    lat, lng = geocode_geocodio(full_address)


    # Insert customer with last_service_date = NULL → new sale → immediately due in get_customers
    cursor.execute("""
        INSERT INTO customers
            (name, address, phone, sqft, monthly_min, monthly_max, notes, last_service_date, lat, lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, address, phone, sqft, monthly_min, monthly_max, notes, None, lat, lng))
    conn.commit()
    return {"status": "success", "name": name}



@app.post("/update_notes")
def update_notes(rowid: int = Form(...), notes: str = Form(...)):
    cursor.execute("UPDATE customers SET notes = ? WHERE rowid = ?", (notes, rowid))
    conn.commit()
    return {"status": "success"}



@app.post("/delete_customer")
def delete_customer(rowid: int = Form(...)):
    cursor.execute("DELETE FROM customers WHERE rowid = ?", (rowid,))
    conn.commit()
    if cursor.rowcount > 0:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Customer not found"}



@app.post("/mark_service")
def mark_service(rowid: int = Form(...)):
    # When you actually go to the property, record the service date
    # Then the 45‑day timer starts from THAT date
    cursor.execute("UPDATE customers SET last_service_date = date('now') WHERE rowid = ?", (rowid,))
    conn.commit()
    return {"status": "success"}



@app.get("/geocode_missing")
def geocode_missing():
    cursor.execute("SELECT rowid, address FROM customers WHERE lat IS NULL OR lng IS NULL")
    rows = cursor.fetchall()
    count = 0
    for rowid, address in rows:
        # Use full address
        full = f"{address}, Texas, United States"
        lat, lng = geocode_geocodio(full)
        if lat is not None and lng is not None:
            cursor.execute(
                "UPDATE customers SET lat = ?, lng = ?, address = ? WHERE rowid = ?",
                (lat, lng, full, rowid)
            )
            conn.commit()
            print(f"Updated {full} -> {lat}, {lng}")
            count += 1
    return {"status": "geocoded", "updated": count}



# =============== FORCE SOME CUSTOMERS TO BE "due" ===============
# Mark customer 1 as serviced 2 days ago → due
cursor.execute("""
    UPDATE customers
    SET last_service_date = date('now', '-2 days')
    WHERE rowid = 1
""")
conn.commit()


# Mark customer 2 as serviced 50 days ago → not due
cursor.execute("""
    UPDATE customers
    SET last_service_date = date('now', '-50 days')
    WHERE rowid = 2
""")
conn.commit()



# ====== Route / Print Order endpoints ======


# Store a route (expects: JSON { "route": [{"rowid": <int>, "sqft": <float>}, ...] })
@app.post("/build_route")
def build_route(route_data: dict):
    selected = route_data.get("route", [])
    if not selected:
        return {"status": "error", "message": "Empty route"}


    # For now, use a dummy route_id = 1 (you can later use a real ID or date)
    route_id = 1


    # Clear any old route selections for this route_id
    cursor.execute("DELETE FROM route_selection WHERE route_id = ?", (route_id,))
    conn.commit()


    # Insert new route selections with priority = index order
    for priority, customer in enumerate(selected):
        rowid = customer["rowid"]
        cursor.execute(
            "INSERT INTO route_selection (customer_rowid, route_id, priority) VALUES (?, ?, ?)",
            (rowid, route_id, priority)
        )
    conn.commit()
    return {"status": "success", "route_id": route_id, "selected_count": len(selected)}



# Fetch current route (for printing) - returns customers in priority order
@app.get("/current_route")
def get_current_route():
    route_id = 1  # match what build_route uses


    cursor.execute("""
        SELECT
            c.name, c.address, c.phone, c.sqft, c.rowid, c.lat, c.lng
        FROM customers c
        JOIN route_selection r ON c.rowid = r.customer_rowid
        WHERE r.route_id = ?
        ORDER BY r.priority ASC
    """, (route_id,))
    rows = cursor.fetchall()


    customers = []
    for name, address, phone, sqft, rowid, lat, lng in rows:
        customers.append({
            "name": name,
            "address": address,
            "phone": phone,
            "sqft": sqft,
            "rowid": rowid,
            "lat": lat,
            "lng": lng
        })
    return {"route": customers}