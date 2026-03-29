import os
import sqlite3
from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timedelta
import requests
import json
import math
from typing import List, Dict, Tuple, Optional

# Your Geocodio API key
GEOCODIO_API_KEY = "04f1debf16fbfbffbe9fa41ba4ef969fae61ddb"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")


# ========== Geocodio Helper ==========
def geocode_geocodio(address):
    base_url = "https://api.geocod.io/v1.6/geocode"
    
    # Improve address formatting for better accuracy
    formatted_address = address.strip()
    
    # Add "United States" if not already present and address looks incomplete
    if not any(state in formatted_address.upper() for state in ['TX', 'GA', 'NC', 'SC', 'TN', 'TEXAS', 'GEORGIA', 'NORTH CAROLINA', 'SOUTH CAROLINA', 'TENNESSEE']):
        # If no state is mentioned, try to be more specific
        if 'united states' not in formatted_address.lower():
            formatted_address += ", United States"
    
    params = {
        "q": formatted_address,
        "api_key": GEOCODIO_API_KEY,
        "country": "US"
    }
    try:
        res = requests.get(base_url, params=params, timeout=10)
        data = res.json()
        if data.get("results"):
            loc = data["results"][0]["location"]
            print(f"Geocoded '{formatted_address}' to ({loc['lat']}, {loc['lng']})")
            return loc["lat"], loc["lng"]
        else:
            print("No results from Geocodio for:", formatted_address)
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

# ADD actual_price column if missing
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN actual_price REAL")
    conn.commit()
except sqlite3.OperationalError:
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

# 🧠 TECHNICIAN MANAGEMENT TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS technicians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    color_hex TEXT DEFAULT '#3b82f6',  -- Color for their territory on map
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
)
""")

# Technician territories (geographic zones)
cursor.execute("""
CREATE TABLE IF NOT EXISTS technician_territories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technician_id INTEGER NOT NULL,
    territory_name TEXT NOT NULL,
    center_lat REAL NOT NULL,
    center_lng REAL NOT NULL,
    radius_miles REAL DEFAULT 10.0,  -- Service radius
    polygon_coords TEXT,  -- JSON string of polygon coordinates for complex shapes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (technician_id) REFERENCES technicians (id) ON DELETE CASCADE
)
""")

# 🧠 SAAS ROUTE OPTIMIZATION TABLES
# Service schedule table for predictive scheduling
cursor.execute("""
CREATE TABLE IF NOT EXISTS service_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_rowid INTEGER NOT NULL,
    scheduled_date DATE NOT NULL,
    priority_score REAL DEFAULT 1.0,
    cluster_id INTEGER,
    route_optimized BOOLEAN DEFAULT FALSE,
    service_day TEXT, -- 'Monday', 'Tuesday', etc.
    estimated_duration INTEGER DEFAULT 30, -- minutes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_rowid) REFERENCES customers (rowid),
    FOREIGN KEY (cluster_id) REFERENCES route_clusters (id)
)
""")

# Route clusters for geographic grouping
cursor.execute("""
CREATE TABLE IF NOT EXISTS route_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name TEXT NOT NULL,
    center_lat REAL NOT NULL,
    center_lng REAL NOT NULL,
    service_day TEXT, -- Preferred service day for this cluster
    average_service_time INTEGER DEFAULT 120, -- Total minutes for cluster
    customer_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Route optimization history for analytics
cursor.execute("""
CREATE TABLE IF NOT EXISTS route_optimization_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    optimization_date DATE NOT NULL,
    total_customers INTEGER DEFAULT 0,
    total_distance REAL DEFAULT 0.0, -- miles
    total_time INTEGER DEFAULT 0, -- minutes
    fuel_cost_estimate REAL DEFAULT 0.0,
    algorithm_used TEXT DEFAULT 'greedy',
    efficiency_score REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Add new columns to customers table for enhanced routing
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN service_frequency INTEGER DEFAULT 45")  # Days between services
    cursor.execute("ALTER TABLE customers ADD COLUMN priority_score REAL DEFAULT 1.0")  # Priority multiplier
    cursor.execute("ALTER TABLE customers ADD COLUMN cluster_id INTEGER")  # Link to route cluster
    cursor.execute("ALTER TABLE customers ADD COLUMN preferred_service_day TEXT")  # Customer preference
    cursor.execute("ALTER TABLE customers ADD COLUMN service_duration INTEGER DEFAULT 30")  # Minutes per service
    cursor.execute("ALTER TABLE customers ADD COLUMN last_optimized_date DATE")  # When customer was last included in optimization
    conn.commit()
except sqlite3.OperationalError:
    # Columns already exist, safe to ignore
    pass

conn.commit()

# 🧠 SAAS ROUTE OPTIMIZATION ENGINE
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in miles using Haversine formula"""
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return float('inf')
    
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def create_geographic_clusters(customers: List[Dict], eps_miles: float = 1.0) -> Dict[int, List[Dict]]:
    """Simple geographic clustering using distance-based approach"""
    clusters = {}
    cluster_id = 0
    
    unassigned = customers.copy()
    
    while unassigned:
        # Start a new cluster with the first unassigned customer
        center_customer = unassigned[0]
        current_cluster = [center_customer]
        unassigned.remove(center_customer)
        
        # Find all customers within eps_miles of any customer in current cluster
        changed = True
        while changed and unassigned:
            changed = False
            for customer in unassigned[:]:  # Copy to avoid modification during iteration
                for cluster_customer in current_cluster:
                    distance = calculate_distance(
                        customer['lat'], customer['lng'],
                        cluster_customer['lat'], cluster_customer['lng']
                    )
                    if distance <= eps_miles:
                        current_cluster.append(customer)
                        unassigned.remove(customer)
                        changed = True
                        break
        
        clusters[cluster_id] = current_cluster
        cluster_id += 1
    
    return clusters

def optimize_route_greedy(customers: List[Dict]) -> List[Dict]:
    """Greedy algorithm for route optimization - always go to nearest unvisited customer"""
    if not customers:
        return []
    
    if len(customers) == 1:
        return customers
    
    optimized = []
    remaining = customers.copy()
    
    # Start with the customer furthest from center (to avoid backtracking)
    center_lat = sum(c['lat'] for c in customers) / len(customers)
    center_lng = sum(c['lng'] for c in customers) / len(customers)
    
    # Find furthest customer from center
    furthest_customer = max(remaining, key=lambda c: calculate_distance(
        c['lat'], c['lng'], center_lat, center_lng
    ))
    optimized.append(furthest_customer)
    remaining.remove(furthest_customer)
    
    # Greedy nearest neighbor
    current = optimized[0]
    while remaining:
        nearest_customer = min(remaining, key=lambda c: calculate_distance(
            current['lat'], current['lng'], c['lat'], c['lng']
        ))
        optimized.append(nearest_customer)
        remaining.remove(nearest_customer)
        current = nearest_customer
    
    return optimized

def predict_service_schedule(days_ahead: int = 30) -> Dict:
    """Predict optimal service schedule for next N days"""
    try:
        today = datetime.now().date()
        
        # Get all customers with coordinates
        cursor.execute("""
            SELECT rowid, name, address, lat, lng, last_service_date, 
                   service_frequency, priority_score, preferred_service_day, service_duration
            FROM customers 
            WHERE lat IS NOT NULL AND lng IS NOT NULL
        """)
        customers_data = cursor.fetchall()
        
        customers = []
        for row in customers_data:
            (rowid, name, address, lat, lng, last_service_date, 
             service_frequency, priority_score, preferred_service_day, service_duration) = row
            
            # Calculate next due date
            if last_service_date:
                last_date = datetime.fromisoformat(last_service_date).date()
                next_due = last_date + timedelta(days=service_frequency)
            else:
                next_due = today  # New customers are due immediately
            
            customers.append({
                'rowid': rowid,
                'name': name,
                'address': address,
                'lat': lat,
                'lng': lng,
                'next_due': next_due,
                'priority_score': priority_score or 1.0,
                'preferred_service_day': preferred_service_day,
                'service_duration': service_duration or 30
            })
        
        # Filter customers due in the next days_ahead period
        cutoff_date = today + timedelta(days=days_ahead)
        due_customers = [c for c in customers if c['next_due'] <= cutoff_date]
        
        if not due_customers:
            return {"schedule": {}, "clusters": {}, "metrics": {"total_customers": 0}}
        
        # Create geographic clusters
        clusters = create_geographic_clusters(due_customers, eps_miles=2.0)
        
        # Generate day-by-day schedule
        schedule = {}
        service_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day_offset in range(days_ahead):
            current_date = today + timedelta(days=day_offset)
            day_name = current_date.strftime('%A')
            
            # Find customers due on or before this date who aren't already scheduled
            available_customers = []
            already_scheduled = set()
            for day_clusters in schedule.values():
                for cluster_customers in day_clusters:
                    for customer in cluster_customers:
                        already_scheduled.add(customer['rowid'])
            
            for customer in due_customers:
                if (customer['next_due'] <= current_date and 
                    customer['rowid'] not in already_scheduled):
                    available_customers.append(customer)
            
            if available_customers:
                # Cluster available customers
                daily_clusters = create_geographic_clusters(available_customers, eps_miles=1.5)
                
                # Optimize routes within each cluster
                optimized_clusters = []
                for cluster_id, cluster_customers in daily_clusters.items():
                    optimized_route = optimize_route_greedy(cluster_customers)
                    optimized_clusters.append(optimized_route)
                
                schedule[current_date.isoformat()] = optimized_clusters
        
        # Calculate metrics
        total_customers = sum(len(day_customers) for day_clusters in schedule.values() for day_customers in day_clusters)
        total_distance = 0
        total_time = 0
        
        for day_clusters in schedule.values():
            for route in day_clusters:
                if len(route) > 1:
                    # Calculate route distance
                    for i in range(len(route) - 1):
                        total_distance += calculate_distance(
                            route[i]['lat'], route[i]['lng'],
                            route[i+1]['lat'], route[i+1]['lng']
                        )
                total_time += sum(c['service_duration'] for c in route)
        
        metrics = {
            "total_customers": total_customers,
            "total_distance": round(total_distance, 2),
            "total_time": total_time,
            "fuel_cost_estimate": round(total_distance * 0.50, 2),  # $0.50 per mile estimate
            "efficiency_score": round(total_customers / max(total_distance, 1), 2)
        }
        
        return {
            "schedule": schedule,
            "clusters": {k: [{"name": c["name"], "address": c["address"]} for c in v] for k, v in clusters.items()},
            "metrics": metrics
        }
    except Exception as e:
        print(f"Error in predict_service_schedule: {e}")
        import traceback
        traceback.print_exc()
        return {"schedule": {}, "clusters": {}, "metrics": {"total_customers": 0}}

def save_optimized_schedule(schedule_data: Dict) -> bool:
    """Save optimized schedule to database"""
    try:
        # Clear existing schedule
        cursor.execute("DELETE FROM service_schedule")
        conn.commit()
        
        # Save new schedule
        for date_str, day_clusters in schedule_data["schedule"].items():
            for cluster_customers in day_clusters:
                for customer in cluster_customers:
                    cursor.execute("""
                        INSERT INTO service_schedule 
                        (customer_rowid, scheduled_date, priority_score, route_optimized, service_day, estimated_duration)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        customer['rowid'],
                        date_str,
                        customer['priority_score'],
                        True,
                        datetime.fromisoformat(date_str).strftime('%A'),
                        customer['service_duration']
                    ))
        
        # Save optimization history
        metrics = schedule_data["metrics"]
        cursor.execute("""
            INSERT INTO route_optimization_history
            (optimization_date, total_customers, total_distance, total_time, 
             fuel_cost_estimate, algorithm_used, efficiency_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().date(),
            metrics["total_customers"],
            metrics["total_distance"],
            metrics["total_time"],
            metrics["fuel_cost_estimate"],
            "greedy_clustering",
            metrics["efficiency_score"]
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving schedule: {e}")
        return False

# █████ TREATMENT PLANS TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS treatment_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grass_type_name TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL,
    treatment_number INTEGER NOT NULL,
    chemicals TEXT DEFAULT '[]',
    notes TEXT DEFAULT '[]',
    FOREIGN KEY (plan_id) REFERENCES treatment_plans(id) ON DELETE CASCADE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS condition_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_name TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chemical_autos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chemical_name TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT DEFAULT '',
    service_area_zips TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS service_visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    service_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    treatment_id INTEGER,
    condition_before TEXT DEFAULT 'Fair',
    condition_after TEXT DEFAULT 'Fair',
    chemicals_used TEXT DEFAULT '[]',
    notes TEXT DEFAULT '',
    duration_minutes INTEGER DEFAULT 0,
    labor_hours REAL DEFAULT 0,
    material_cost REAL DEFAULT 0,
    gps_lat REAL,
    gps_lng REAL,
    technician_name TEXT DEFAULT 'Unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (treatment_id) REFERENCES treatments(id)
)
""")

# 🏢 OFFICE WORKERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS office_workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location_id INTEGER NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
)
""")

conn.commit()

# Add order column to treatments if missing
try:
    cursor.execute("ALTER TABLE treatments ADD COLUMN treatment_order INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass

# Add location_id to customers if missing
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN location_id INTEGER DEFAULT 1")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass

# ADD measurement_data column for storing property measurements
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN measurement_data TEXT")
    conn.commit()
except sqlite3.OperationalError:
    # Already exists, safe to ignore
    pass

# ADD lat/lng columns to locations table for route optimization
try:
    cursor.execute("ALTER TABLE locations ADD COLUMN lat REAL")
    conn.commit()
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE locations ADD COLUMN lng REAL")
    conn.commit()
except sqlite3.OperationalError:
    pass

# ADD location_id column to customers table for multi-location support
try:
    cursor.execute("ALTER TABLE customers ADD COLUMN location_id INTEGER DEFAULT NULL")
    conn.commit()
except sqlite3.OperationalError:
    pass

# ADD location_id column to technicians table for multi-location support
try:
    cursor.execute("ALTER TABLE technicians ADD COLUMN location_id INTEGER DEFAULT NULL")
    conn.commit()
except sqlite3.OperationalError:
    pass

app = FastAPI()

# Session middleware for login (browser session only - closes when tab closes)
app.add_middleware(SessionMiddleware, secret_key='lawncare-super-secret-2026-trinity', max_age=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple hardcoded credentials - change these!
USERNAME = "123456"
PASSWORD = "123456"

def require_auth(request: Request):
    """Dependency to check if user is logged in"""
    if not request.session.get('logged_in'):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.session

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """Show login page if not authenticated"""
    if request.session.get('logged_in'):
        return RedirectResponse(url="/")
    
    error_msg = f'<div class="error-message"><i class="fas fa-radiation"></i> {error}</div>' if error else ''
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LawnOps | Chemical Warfare Division</title>
        <link href="https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Oswald:wght@400;600;700&family=Roboto+Condensed:wght@400;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Roboto Condensed', sans-serif;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #1a2f1a 0%, #2d3a2d 50%, #1a2f1a 100%);
                position: relative;
                overflow: hidden;
            }}
            
            /* Tactical grid overlay */
            body::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-image:
                    linear-gradient(rgba(0,255,0,0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0,255,0,0.03) 1px, transparent 1px);
                background-size: 50px 50px;
                pointer-events: none;
            }}
            
            /* Crosshair in center */
            body::after {{
                content: '+';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 400px;
                color: rgba(0,255,0,0.02);
                pointer-events: none;
                font-weight: 100;
            }}
            
            .login-container {{
                position: relative;
                z-index: 10;
                width: 100%;
                max-width: 480px;
                padding: 20px;
            }}
            
            .login-box {{
                background: linear-gradient(145deg, #2d3a2d 0%, #1e2b1e 100%);
                border: 3px solid #4a5d4a;
                border-radius: 0;
                padding: 50px 40px;
                position: relative;
                box-shadow: 
                    0 20px 60px rgba(0,0,0,0.8),
                    inset 0 1px 0 rgba(0,255,0,0.1);
            }}
            
            /* Corner targeting brackets */
            .login-box::before,
            .login-box::after {{
                content: '';
                position: absolute;
                width: 40px;
                height: 40px;
                border: 4px solid #7a8d3a;
            }}
            
            .login-box::before {{
                top: -4px;
                left: -4px;
                border-right: none;
                border-bottom: none;
            }}
            
            .login-box::after {{
                bottom: -4px;
                right: -4px;
                border-left: none;
                border-top: none;
            }}
            
            /* Bottom left corner */
            .corner-bl {{
                position: absolute;
                bottom: -4px;
                left: -4px;
                width: 40px;
                height: 40px;
                border: 4px solid #7a8d3a;
                border-right: none;
                border-top: none;
            }}
            
            /* Top right corner */
            .corner-tr {{
                position: absolute;
                top: -4px;
                right: -4px;
                width: 40px;
                height: 40px;
                border: 4px solid #7a8d3a;
                border-left: none;
                border-bottom: none;
            }}
            
            .logo-section {{
                text-align: center;
                margin-bottom: 40px;
                position: relative;
            }}
            
            /* Backpack sprayer operator icon */
            .logo-icon {{
                width: 100px;
                height: 100px;
                background: linear-gradient(145deg, #4a5d3a 0%, #3a4d2a 100%);
                border: 3px solid #7a8d3a;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                position: relative;
            }}
            
            .logo-icon::before {{
                content: '';
                position: absolute;
                top: -10px;
                left: -10px;
                right: -10px;
                bottom: -10px;
                border: 2px dashed #7a8d3a;
                opacity: 0.5;
            }}
            
            .logo-icon i {{
                font-size: 50px;
                color: #c8d46a;
            }}
            
            /* Chemical hazard stamp */
            .hazard-stamp {{
                position: absolute;
                top: -25px;
                right: -15px;
                font-family: 'Black Ops One', cursive;
                font-size: 11px;
                color: #ffd700;
                border: 2px solid #ffd700;
                padding: 4px 8px;
                transform: rotate(15deg);
                text-transform: uppercase;
                letter-spacing: 1px;
                opacity: 0.9;
                background: rgba(0,0,0,0.5);
            }}
            
            .logo-text {{
                font-family: 'Black Ops One', cursive;
                font-size: 44px;
                letter-spacing: 3px;
                text-transform: uppercase;
                background: linear-gradient(180deg, #c8d46a 0%, #7a8d3a 50%, #4a5d3a 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                text-shadow: 0 2px 4px rgba(0,0,0,0.5);
                position: relative;
                display: inline-block;
            }}
            
            /* Night vision green glow */
            .logo-text::after {{
                content: 'LAWNOPS';
                position: absolute;
                top: 0;
                left: 0;
                background: linear-gradient(180deg, #00ff00 0%, #00aa00 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                z-index: -1;
                opacity: 0.3;
                filter: blur(8px);
            }}
            
            .subtitle {{
                font-family: 'Oswald', sans-serif;
                font-size: 13px;
                color: #7a8d3a;
                text-transform: uppercase;
                letter-spacing: 5px;
                margin-top: 10px;
            }}
            
            .divider {{
                width: 80px;
                height: 3px;
                background: linear-gradient(90deg, transparent, #7a8d3a, transparent);
                margin: 20px auto;
            }}
            
            .input-group {{
                margin-bottom: 25px;
                position: relative;
            }}
            
            .input-group label {{
                display: block;
                margin-bottom: 8px;
                color: #7a8d3a;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            
            .input-wrapper {{
                position: relative;
                border: 2px solid #4a5d4a;
                background: #1a2f1a;
            }}
            
            .input-wrapper::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
                height: 100%;
                background: #7a8d3a;
            }}
            
            .input-wrapper i {{
                position: absolute;
                left: 15px;
                top: 50%;
                transform: translateY(-50%);
                color: #5a6d4a;
                font-size: 14px;
            }}
            
            input {{
                width: 100%;
                padding: 14px 16px 14px 45px;
                border: none;
                background: transparent;
                color: #c8d46a;
                font-size: 14px;
                font-family: 'Roboto Condensed', sans-serif;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            input::placeholder {{
                color: #4a5d4a;
                text-transform: uppercase;
            }}
            
            input:focus {{
                outline: none;
                box-shadow: inset 0 0 10px rgba(0,255,0,0.2);
            }}
            
            input:focus + i {{
                color: #c8d46a;
            }}
            
            .login-btn {{
                width: 100%;
                padding: 16px;
                background: linear-gradient(145deg, #4a5d3a 0%, #3a4d2a 100%);
                color: #c8d46a;
                border: 2px solid #7a8d3a;
                border-radius: 0;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Oswald', sans-serif;
                text-transform: uppercase;
                letter-spacing: 3px;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            
            .login-btn::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(200,212,106,0.2), transparent);
                transition: left 0.5s;
            }}
            
            .login-btn:hover {{
                background: #5a6d4a;
                border-color: #c8d46a;
                letter-spacing: 5px;
                box-shadow: 0 0 20px rgba(122,141,58,0.4);
            }}
            
            .login-btn:hover::before {{
                left: 100%;
            }}
            
            .login-btn i {{
                margin-left: 10px;
            }}
            
            .error-message {{
                background: #3a2f1a;
                border: 1px solid #8b6914;
                border-left: 4px solid #ffd700;
                color: #d4a76a;
                padding: 12px 16px;
                margin-bottom: 25px;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #5a6d4a;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 2px;
            }}
            
            /* Scan line effect - night vision style */
            .scan-line {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: rgba(0,255,0,0.3);
                animation: scan 6s linear infinite;
                pointer-events: none;
                z-index: 100;
                box-shadow: 0 0 10px #00ff00;
            }}
            
            @keyframes scan {{
                0% {{ transform: translateY(-100vh); }}
                100% {{ transform: translateY(100vh); }}
            }}
            
            /* Munitions status indicator */
            .status-bar {{
                position: absolute;
                top: -30px;
                left: 0;
                right: 0;
                display: flex;
                justify-content: space-between;
                font-size: 10px;
                color: #7a8d3a;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            
            .status-indicator {{
                display: flex;
                align-items: center;
                gap: 5px;
            }}
            
            .status-dot {{
                width: 8px;
                height: 8px;
                background: #00ff00;
                border-radius: 50%;
                animation: pulse 2s infinite;
                box-shadow: 0 0 5px #00ff00;
            }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            
            @media (max-width: 480px) {{
                .login-box {{
                    padding: 40px 25px;
                }}
                .logo-text {{
                    font-size: 36px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="scan-line"></div>
        <div class="login-container">
            <div class="login-box">
                <div class="corner-bl"></div>
                <div class="corner-tr"></div>
                
                <div class="status-bar">
                    <div class="status-indicator">
                        <div class="status-dot"></div>
                        <span>SYSTEM ONLINE</span>
                    </div>
                    <span>CWD // SECURE</span>
                </div>
                
                <div class="logo-section">
                    <div class="hazard-stamp">CHEMICAL</div>
                    <div class="logo-icon">
                        <i class="fas fa-spray-can"></i>
                    </div>
                    <h1 class="logo-text">LawnOps</h1>
                    <div class="divider"></div>
                    <p class="subtitle">Chemical Warfare Division</p>
                </div>
                
                {error_msg}
                
                <form method="POST" action="/login">
                    <div class="input-group">
                        <label for="username">Operative ID</label>
                        <div class="input-wrapper">
                            <input type="text" id="username" name="username" placeholder="ENTER OPERATIVE ID" required autofocus autocomplete="username">
                            <i class="fas fa-fingerprint"></i>
                        </div>
                    </div>
                    
                    <div class="input-group">
                        <label for="password">Clearance Code</label>
                        <div class="input-wrapper">
                            <input type="password" id="password" name="password" placeholder="ENTER CLEARANCE CODE" required autocomplete="current-password">
                            <i class="fas fa-lock"></i>
                        </div>
                    </div>
                    
                    <button type="submit" class="login-btn">
                        Initialize Access <i class="fas fa-chevron-right"></i>
                    </button>
                </form>
                
                <div class="footer">
                    <p>Authorized Chemical Personnel Only // CWD-Alpha</p>
                    <p>Munitions Status: Locked & Loaded</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/login")
async def do_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form - check hardcoded admin OR office_workers DB"""
    import hashlib
    
    # Check hardcoded admin credentials first
    if username == USERNAME and password == PASSWORD:
        request.session['logged_in'] = True
        request.session['username'] = username
        request.session['user_type'] = 'admin'
        return RedirectResponse(url="/", status_code=302)
    
    # Check office_workers database
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute(
        "SELECT id, name, location_id, is_active FROM office_workers WHERE username = ? AND password_hash = ? AND is_active = 1",
        (username, password_hash)
    )
    row = cursor.fetchone()
    
    if row:
        request.session['logged_in'] = True
        request.session['username'] = username
        request.session['user_type'] = 'office_worker'
        request.session['worker_id'] = row[0]
        request.session['worker_name'] = row[1]
        request.session['location_id'] = row[2]
        return RedirectResponse(url="/", status_code=302)
    
    return RedirectResponse(url="/login?error=Invalid+credentials", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    """Logout and clear session"""
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/check_auth")
async def check_auth(request: Request):
    """API endpoint to check if user is logged in"""
    return {"authenticated": request.session.get('logged_in', False)}

@app.get("/me")
async def get_current_user(request: Request):
    """Get current logged-in user info with location details"""
    if not request.session.get('logged_in'):
        return {"authenticated": False}
    
    user_type = request.session.get('user_type', 'unknown')
    username = request.session.get('username', '')
    
    response = {
        "authenticated": True,
        "user_type": user_type,
        "username": username
    }
    
    if user_type == 'office_worker':
        response['worker_name'] = request.session.get('worker_name', '')
        location_id = request.session.get('location_id')
        response['location_id'] = location_id
        
        # Get location details for map centering
        if location_id:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, address, lat, lng FROM locations WHERE id = ?",
                (location_id,)
            )
            loc = cursor.fetchone()
            conn.close()
            if loc:
                response['location'] = {
                    'name': loc[0],
                    'address': loc[1],
                    'lat': loc[2],
                    'lng': loc[3]
                }
    
    return response

# Protected routes - all redirect to /login if not authenticated

@app.get("/Route_Printing.html", response_class=FileResponse)
async def read_route_printing(request: Request):
    require_auth(request)
    return FileResponse(os.path.join(STATIC_DIR, "Route_Printing.html"))
    
@app.get("/", response_class=FileResponse)
async def read_index(request: Request):
    if not request.session.get('logged_in'):
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/routing.html", response_class=FileResponse)
async def read_routing(request: Request):
    if not request.session.get('logged_in'):
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "routing.html"))

@app.get("/owner", response_class=FileResponse)
async def read_owner(request: Request):
    if not request.session.get('logged_in'):
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "owner.html"))

@app.get("/analytics", response_class=FileResponse)
async def read_analytics(request: Request):
    if not request.session.get('logged_in'):
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "analytics.html"))

@app.get("/customers")
def get_customers(request: Request):
    if not request.session.get('logged_in'):
        return RedirectResponse(url="/login")
    
    # Get user's location_id (for office workers)
    location_id = request.session.get('location_id')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        # If office worker with location, filter by location
        if location_id:
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
                    lng,
                    actual_price,
                    measurement_data,
                    location_id
                FROM customers 
                WHERE location_id = ? OR location_id IS NULL
                ORDER BY CASE WHEN last_service_date IS NULL THEN 0 ELSE 1 END, last_service_date ASC
            """, (location_id,))
        else:
            # Admin sees all customers
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
                    lng,
                    actual_price,
                    measurement_data,
                    location_id
                FROM customers 
                ORDER BY CASE WHEN last_service_date IS NULL THEN 0 ELSE 1 END, last_service_date ASC
            """)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Database error in get_customers: {e}")
        conn.close()
        return {"customers": [], "error": str(e)}

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
            lng,
            actual_price,
            measurement_data,
            location_id
        ) = row

        if last_service_date:
            last_date = datetime.fromisoformat(last_service_date).date()
            days_since = (now - last_date).days
        else:
            days_since = 9999  # never serviced

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
                last_service_date,
                status,
                rowid,
                lat,
                lng,
                actual_price,
                measurement_data,
                location_id
            )
        )

    conn.close()
    return {"customers": customers_with_status}


@app.post("/add_customer")
def add_customer(
    request: Request,
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
    lat, lng = geocode_geocodio(address)
    
    # Get the office worker's location_id
    location_id = request.session.get('location_id')

    # Insert customer with location_id
    cursor.execute("""
        INSERT INTO customers
            (name, address, phone, sqft, monthly_min, monthly_max, notes, last_service_date, lat, lng, location_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, address, phone, sqft, monthly_min, monthly_max, notes, None, lat, lng, location_id))
    conn.commit()
    new_rowid = cursor.lastrowid
    return {"status": "success", "name": name, "rowid": new_rowid}


@app.post("/update_notes")
def update_notes(rowid: int = Form(...), notes: str = Form(...)):
    cursor.execute("UPDATE customers SET notes = ? WHERE rowid = ?", (notes, rowid))
    conn.commit()
    return {"status": "success"}

@app.post("/update_actual_price")
def update_actual_price(rowid: int = Form(...), actual_price: float = Form(...)):
    cursor.execute("UPDATE customers SET actual_price = ? WHERE rowid = ?", (actual_price, rowid))
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


@app.post("/save_measurement")
def save_measurement(rowid: int = Form(...), measurement_data: str = Form(...), sqft: int = Form(None), monthly_min: float = Form(None), monthly_max: float = Form(None)):
    """Save property measurement polygon for a customer and update sqft/price if no actual price set"""
    try:
        cursor.execute("UPDATE customers SET measurement_data = ? WHERE rowid = ?", (measurement_data, rowid))
        
        # Also update sqft if measurement provides it
        if sqft is not None and sqft > 0:
            cursor.execute("UPDATE customers SET sqft = ? WHERE rowid = ?", (sqft, rowid))
        
        # Only update price range if no actual_price is set
        cursor.execute("SELECT actual_price FROM customers WHERE rowid = ?", (rowid,))
        row = cursor.fetchone()
        actual_price = row[0] if row else None
        
        if actual_price is None or actual_price == 0:
            if monthly_min is not None and monthly_min > 0:
                cursor.execute("UPDATE customers SET monthly_min = ? WHERE rowid = ?", (monthly_min, rowid))
            if monthly_max is not None and monthly_max > 0:
                cursor.execute("UPDATE customers SET monthly_max = ? WHERE rowid = ?", (monthly_max, rowid))
        
        conn.commit()
        return {"status": "success", "message": "Measurement saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def geocode_missing():
    cursor.execute("SELECT rowid, address FROM customers WHERE lat IS NULL OR lng IS NULL")
    rows = cursor.fetchall()
    count = 0
    for rowid, address in rows:
        # Use full address
        lat, lng = geocode_geocodio(address)
        if lat is not None and lng is not None:
            cursor.execute(
                "UPDATE customers SET lat = ?, lng = ? WHERE rowid = ?",
                (lat, lng, rowid)
            )
            conn.commit()
            print(f"Updated {full} -> {lat}, {lng}")
            count += 1
    return {"status": "geocoded", "updated": count}


# =============== TREATMENT PLANS ENDPOINTS ===============

@app.get("/treatment-plans")
def get_treatment_plans():
    """Fetch all treatment plans with their treatments, chemicals, and notes - ordered by treatment_order"""
    cursor.execute("SELECT id, grass_type_name FROM treatment_plans ORDER BY grass_type_name")
    plans = cursor.fetchall()
    
    result = []
    for plan_id, grass_type_name in plans:
        cursor.execute("""
            SELECT id, treatment_order, chemicals, notes 
            FROM treatments 
            WHERE plan_id = ? 
            ORDER BY treatment_order ASC
        """, (plan_id,))
        treatments = cursor.fetchall()
        
        treatment_list = []
        display_number = 1
        for t_id, t_order, chems_json, notes_json in treatments:
            import json
            chems = json.loads(chems_json) if chems_json else []
            notes = json.loads(notes_json) if notes_json else []
            treatment_list.append({
                "id": t_id,
                "order": t_order,
                "number": display_number,  # Display number 1, 2, 3...
                "chems": chems,
                "notes": notes
            })
            display_number += 1
        
        result.append({
            "id": plan_id,
            "name": grass_type_name,
            "treatments": treatment_list
        })
    
    return {"grassTypes": result}


@app.get("/global-data")
def get_global_data():
    """Fetch condition codes and chemical autos with their IDs"""
    cursor.execute("SELECT id, code_name FROM condition_codes ORDER BY code_name")
    codes = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    cursor.execute("SELECT id, chemical_name FROM chemical_autos ORDER BY chemical_name")
    chems = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    
    return {
        "conditionCodes": codes,
        "chemicalAutos": chems
    }


@app.post("/treatment-plans")
def create_treatment_plan(grass_type_name: str = Form(...)):
    """Create a new treatment plan (grass type)"""
    try:
        cursor.execute(
            "INSERT INTO treatment_plans (grass_type_name) VALUES (?)",
            (grass_type_name,)
        )
        conn.commit()
        plan_id = cursor.lastrowid
        return {"status": "success", "id": plan_id, "name": grass_type_name}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Grass type already exists"}


@app.delete("/treatment-plans/{plan_id}")
def delete_treatment_plan(plan_id: int):
    """Delete a treatment plan (cascades to treatments)"""
    cursor.execute("DELETE FROM treatment_plans WHERE id = ?", (plan_id,))
    conn.commit()
    if cursor.rowcount > 0:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Plan not found"}


@app.post("/treatments")
def create_treatment(plan_id: int = Form(...)):
    """Create a new treatment within a plan"""
    try:
        # Get max order and add 1 for new treatment
        cursor.execute(
            "SELECT MAX(COALESCE(treatment_order, -1)) FROM treatments WHERE plan_id = ?",
            (plan_id,)
        )
        result = cursor.fetchone()
        max_order = result[0] if (result and result[0] is not None) else -1
        new_order = max_order + 1
        
        cursor.execute(
            "INSERT INTO treatments (plan_id, treatment_number, treatment_order, chemicals, notes) VALUES (?, ?, ?, '[]', '[]')",
            (plan_id, new_order, new_order)
        )
        conn.commit()
        t_id = cursor.lastrowid
        return {"status": "success", "id": t_id}
    except Exception as e:
        import traceback
        print(f"Treatment creation error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.delete("/treatments/{treatment_id}")
def delete_treatment(treatment_id: int):
    """Delete a specific treatment"""
    cursor.execute("DELETE FROM treatments WHERE id = ?", (treatment_id,))
    conn.commit()
    if cursor.rowcount > 0:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Treatment not found"}


@app.post("/treatments/{treatment_id}/reorder")
def reorder_treatment(treatment_id: int, new_order: int = Form(...)):
    """Change the order of a treatment"""
    cursor.execute("UPDATE treatments SET treatment_order = ? WHERE id = ?", (new_order, treatment_id))
    conn.commit()
    if cursor.rowcount > 0:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Treatment not found"}


@app.post("/treatments/{treatment_id}/chems")
def add_chemical_to_treatment(treatment_id: int, chemical: str = Form(...)):
    """Add a chemical to a treatment"""
    import json
    cursor.execute("SELECT chemicals FROM treatments WHERE id = ?", (treatment_id,))
    row = cursor.fetchone()
    if not row:
        return {"status": "error", "message": "Treatment not found"}
    
    chems = json.loads(row[0]) if row[0] else []
    chems.append(chemical)
    
    cursor.execute("UPDATE treatments SET chemicals = ? WHERE id = ?", (json.dumps(chems), treatment_id))
    conn.commit()
    return {"status": "success"}


@app.delete("/treatments/{treatment_id}/chems/{index}")
def delete_chemical_from_treatment(treatment_id: int, index: int):
    """Delete a chemical from a treatment"""
    import json
    cursor.execute("SELECT chemicals FROM treatments WHERE id = ?", (treatment_id,))
    row = cursor.fetchone()
    if not row:
        return {"status": "error", "message": "Treatment not found"}
    
    chems = json.loads(row[0]) if row[0] else []
    if 0 <= index < len(chems):
        chems.pop(index)
        cursor.execute("UPDATE treatments SET chemicals = ? WHERE id = ?", (json.dumps(chems), treatment_id))
        conn.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Index out of range"}


@app.post("/treatments/{treatment_id}/notes")
def add_note_to_treatment(treatment_id: int, note: str = Form(...)):
    """Add a note to a treatment"""
    import json
    cursor.execute("SELECT notes FROM treatments WHERE id = ?", (treatment_id,))
    row = cursor.fetchone()
    if not row:
        return {"status": "error", "message": "Treatment not found"}
    
    notes = json.loads(row[0]) if row[0] else []
    notes.append(note)
    
    cursor.execute("UPDATE treatments SET notes = ? WHERE id = ?", (json.dumps(notes), treatment_id))
    conn.commit()
    return {"status": "success"}


@app.delete("/treatments/{treatment_id}/notes/{index}")
def delete_note_from_treatment(treatment_id: int, index: int):
    """Delete a note from a treatment"""
    import json
    cursor.execute("SELECT notes FROM treatments WHERE id = ?", (treatment_id,))
    row = cursor.fetchone()
    if not row:
        return {"status": "error", "message": "Treatment not found"}
    
    notes = json.loads(row[0]) if row[0] else []
    if 0 <= index < len(notes):
        notes.pop(index)
        cursor.execute("UPDATE treatments SET notes = ? WHERE id = ?", (json.dumps(notes), treatment_id))
        conn.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Index out of range"}


@app.post("/condition-codes")
def add_condition_code(code_name: str = Form(...)):
    """Add a condition code"""
    try:
        cursor.execute(
            "INSERT INTO condition_codes (code_name) VALUES (?)",
            (code_name,)
        )
        conn.commit()
        return {"status": "success", "code": code_name}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Condition code already exists"}


@app.delete("/condition-codes/{code_id}")
def delete_condition_code(code_id: int):
    """Delete a condition code"""
    cursor.execute("DELETE FROM condition_codes WHERE id = ?", (code_id,))
    conn.commit()
    if cursor.rowcount > 0:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Code not found"}


@app.post("/chemical-autos")
def add_chemical_auto(chemical_name: str = Form(...)):
    """Add a chemical to auto-population list"""
    try:
        cursor.execute(
            "INSERT INTO chemical_autos (chemical_name) VALUES (?)",
            (chemical_name,)
        )
        conn.commit()
        return {"status": "success", "chemical": chemical_name}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Chemical already exists"}


@app.delete("/chemical-autos/{chem_id}")
def delete_chemical_auto(chem_id: int):
    """Delete a chemical from auto-population list"""
    cursor.execute("DELETE FROM chemical_autos WHERE id = ?", (chem_id,))
    conn.commit()
    if cursor.rowcount > 0:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Chemical not found"}


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


# ====== 🔧 TECHNICIAN MANAGEMENT ENDPOINTS ======

@app.get("/technicians")
def get_technicians():
    """Get all technicians with their locations"""
    try:
        cursor.execute("""
            SELECT t.id, t.name, t.location_id, t.color_hex, t.is_active, 
                   l.name as location_name, l.address as location_address
            FROM technicians t
            JOIN locations l ON t.location_id = l.id
            ORDER BY t.is_active DESC, t.name
        """)
        technicians = cursor.fetchall()
        
        result = []
        for tech in technicians:
            result.append({
                "id": tech[0],
                "name": tech[1],
                "location_id": tech[2],
                "color_hex": tech[3],
                "is_active": tech[4],
                "location_name": tech[5],
                "location_address": tech[6]
            })
        
        return {"status": "success", "technicians": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get technicians: {str(e)}"}

@app.post("/technicians")
def add_technician(name: str = Form(...), location_id: int = Form(...), color_hex: str = Form("#3b82f6")):
    """Add a new technician"""
    try:
        cursor.execute("""
            INSERT INTO technicians (name, location_id, color_hex)
            VALUES (?, ?, ?)
        """, (name, location_id, color_hex))
        conn.commit()
        
        return {"status": "success", "message": f"Technician '{name}' added successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to add technician: {str(e)}"}

@app.put("/technicians/{technician_id}")
def update_technician(technician_id: int, name: str = Form(None), location_id: int = Form(None), 
                      color_hex: str = Form(None), is_active: bool = Form(None)):
    """Update technician details"""
    try:
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if location_id is not None:
            updates.append("location_id = ?")
            params.append(location_id)
        if color_hex is not None:
            updates.append("color_hex = ?")
            params.append(color_hex)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        
        if not updates:
            return {"status": "error", "message": "No updates provided"}
        
        params.append(technician_id)
        cursor.execute(f"UPDATE technicians SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        
        return {"status": "success", "message": "Technician updated successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to update technician: {str(e)}"}

@app.delete("/technicians/{technician_id}")
def delete_technician(technician_id: int):
    """Delete a technician"""
    try:
        cursor.execute("DELETE FROM technicians WHERE id = ?", (technician_id,))
        conn.commit()
        
        return {"status": "success", "message": "Technician deleted successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete technician: {str(e)}"}

@app.get("/technician_territories")
def get_technician_territories(request: Request):
    """Get all technician territories for map visualization - filtered by user's location"""
    try:
        # Get user's location_id (for office workers)
        location_id = request.session.get('location_id')
        
        # Use the correct database file
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        if location_id:
            # Office workers only see territories for their location
            cursor.execute("""
                SELECT tt.id, tt.technician_id, tt.territory_name, tt.center_lat, tt.center_lng,
                       tt.radius_miles, tt.polygon_coords, t.name as technician_name, t.color_hex
                FROM technician_territories tt
                JOIN technicians t ON tt.technician_id = t.id
                WHERE t.is_active = 1 AND t.location_id = ?
            """, (location_id,))
        else:
            # Admin sees all territories
            cursor.execute("""
                SELECT tt.id, tt.technician_id, tt.territory_name, tt.center_lat, tt.center_lng,
                       tt.radius_miles, tt.polygon_coords, t.name as technician_name, t.color_hex
                FROM technician_territories tt
                JOIN technicians t ON tt.technician_id = t.id
                WHERE t.is_active = 1
            """)
        territories = cursor.fetchall()
        conn.close()
        
        result = []
        for territory in territories:
            result.append({
                "id": territory[0],
                "technician_id": territory[1],
                "territory_name": territory[2],
                "center_lat": territory[3],
                "center_lng": territory[4],
                "radius_miles": territory[5],
                "polygon_coords": territory[6],
                "technician_name": territory[7],
                "color_hex": territory[8]
            })
        
        return {"status": "success", "territories": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get territories: {str(e)}"}

@app.post("/technician_territories/auto_assign")
def auto_assign_territories(location_id: int = Form(...), radius: int = Form(...)):
    """Automatically create pie-slice territories for all technicians at a location"""
    try:
        local_cursor = conn.cursor()
        
        # Get location details
        local_cursor.execute("SELECT name, address FROM locations WHERE id = ?", (location_id,))
        location = local_cursor.fetchone()
        if not location:
            return {"status": "error", "message": "Location not found"}
        
        # Get active technicians for this location
        local_cursor.execute("SELECT id, name, color_hex FROM technicians WHERE location_id = ? AND is_active = 1", (location_id,))
        technicians = local_cursor.fetchall()
        
        if not technicians:
            return {"status": "error", "message": "No active technicians found for this location"}
        
        # Get location coordinates (geocode the address)
        location_coords = geocode_address(location[1])
        if not location_coords:
            return {"status": "error", "message": "Could not geocode location address"}
        
        # Clear existing territories for this location
        local_cursor.execute("""
            DELETE FROM technician_territories 
            WHERE technician_id IN (SELECT id FROM technicians WHERE location_id = ?)
        """, (location_id,))
        
        # Create pie-slice territories
        import math
        num_technicians = len(technicians)
        service_radius = 50  # 50-mile service zone
        angle_step = 360 / num_technicians
        
        for i, tech in enumerate(technicians):
            # Calculate start and end angles for this slice
            start_angle = math.radians(i * angle_step)
            end_angle = math.radians((i + 1) * angle_step)
            
            # Generate polygon points for the pie slice
            # Start from center, arc around the outer edge, back to center
            polygon_points = []
            
            # Add center point (office location)
            polygon_points.append([location_coords[0], location_coords[1]])
            
            # Add points along the outer curved arc
            # Use more points for a smoother curve
            num_arc_points = max(8, int(angle_step / 5))  # At least 8 points, or one every 5 degrees
            for j in range(num_arc_points + 1):
                angle = start_angle + (end_angle - start_angle) * j / num_arc_points
                # Calculate point on the outer circle
                arc_lat = location_coords[0] + (service_radius * math.cos(angle)) / 69
                arc_lng = location_coords[1] + (service_radius * math.sin(angle)) / (69 * math.cos(math.radians(location_coords[0])))
                polygon_points.append([arc_lat, arc_lng])
            
            # Back to center to close the polygon
            polygon_points.append([location_coords[0], location_coords[1]])
            
            # Store the polygon coordinates
            polygon_json = json.dumps(polygon_points)
            
            # Calculate center point of this territory (for reference)
            mid_angle = (start_angle + end_angle) / 2
            territory_lat = location_coords[0] + (service_radius * 0.5 * math.cos(mid_angle)) / 69
            territory_lng = location_coords[1] + (service_radius * 0.5 * math.sin(mid_angle)) / (69 * math.cos(math.radians(location_coords[0])))
            
            local_cursor.execute("""
                INSERT INTO technician_territories 
                (technician_id, territory_name, center_lat, center_lng, radius_miles, polygon_coords)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tech[0], f"{tech[1]} Territory", territory_lat, territory_lng, service_radius, polygon_json))
        
        conn.commit()
        
        return {
            "status": "success", 
            "message": f"Created {num_technicians} pie-slice territories for {location[0]}",
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to auto-assign territories: {str(e)}"}

def geocode_address(address: str):
    """Geocoding using Geocodio API"""
    return geocode_geocodio(address)

@app.post("/technician_territories/custom")
def create_custom_territory(
    technician_id: int = Form(...),
    territory_name: str = Form(...),
    center_lat: float = Form(...),
    center_lng: float = Form(...),
    radius_miles: float = Form(...),
    polygon_coords: str = Form(...)
):
    """Create a custom territory with polygon coordinates"""
    try:
        # Verify technician exists and is active
        cursor.execute("SELECT id, name FROM technicians WHERE id = ? AND is_active = 1", (technician_id,))
        technician = cursor.fetchone()
        if not technician:
            return {"status": "error", "message": "Technician not found or inactive"}
        
        # Clear existing territory for this technician
        cursor.execute("DELETE FROM technician_territories WHERE technician_id = ?", (technician_id,))
        
        # Insert new custom territory
        cursor.execute("""
            INSERT INTO technician_territories 
            (technician_id, territory_name, center_lat, center_lng, radius_miles, polygon_coords)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (technician_id, territory_name, center_lat, center_lng, radius_miles, polygon_coords))
        
        conn.commit()
        
        return {
            "status": "success", 
            "message": f"Custom territory created for {technician[1]}",
            "territory_id": cursor.lastrowid
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to create custom territory: {str(e)}"}

@app.delete("/technician_territories/{technician_id}")
def delete_technician_territory(technician_id: int):
    """Delete a technician's territory (unassign)"""
    try:
        local_cursor = conn.cursor()
        local_cursor.execute("DELETE FROM technician_territories WHERE technician_id = ?", (technician_id,))
        conn.commit()
        deleted_count = local_cursor.rowcount
        
        if deleted_count > 0:
            return {"status": "success", "message": "Territory deleted"}
        else:
            return {"status": "success", "message": "No territory found to delete"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete territory: {str(e)}"}

# ====== 🧠 SAAS ROUTE OPTIMIZATION ENDPOINTS ======

@app.post("/optimize_routes")
def optimize_routes(days_ahead: int = 30):
    """Generate optimized service schedule for next N days"""
    try:
        schedule_data = predict_service_schedule(days_ahead)
        
        # Save to database
        success = save_optimized_schedule(schedule_data)
        
        if success:
            return {
                "status": "success", 
                "message": f"Routes optimized for {days_ahead} days ahead",
                "data": schedule_data
            }
        else:
            return {
                "status": "error", 
                "message": "Failed to save optimized schedule"
            }
    except Exception as e:
        return {"status": "error", "message": f"Optimization failed: {str(e)}"}

@app.get("/predicted_schedule")
def get_predicted_schedule(days_ahead: int = 30):
    """Get predicted service schedule without saving"""
    try:
        schedule_data = predict_service_schedule(days_ahead)
        return {
            "status": "success",
            "data": schedule_data
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate schedule: {str(e)}"}

@app.get("/route_clusters")
def get_route_clusters():
    """Get current geographic clusters"""
    try:
        # Get all customers with coordinates
        cursor.execute("""
            SELECT rowid, name, address, lat, lng, priority_score
            FROM customers 
            WHERE lat IS NOT NULL AND lng IS NOT NULL
        """)
        customers_data = cursor.fetchall()
        
        customers = []
        for row in customers_data:
            rowid, name, address, lat, lng, priority_score = row
            customers.append({
                'rowid': rowid,
                'name': name,
                'address': address,
                'lat': lat,
                'lng': lng,
                'priority_score': priority_score or 1.0
            })
        
        # Create clusters
        clusters = create_geographic_clusters(customers, eps_miles=2.0)
        
        # Format for frontend
        cluster_data = {}
        for cluster_id, cluster_customers in clusters.items():
            # Calculate cluster center
            center_lat = sum(c['lat'] for c in cluster_customers) / len(cluster_customers)
            center_lng = sum(c['lng'] for c in cluster_customers) / len(cluster_customers)
            
            cluster_data[f"cluster_{cluster_id}"] = {
                "center": {"lat": center_lat, "lng": center_lng},
                "customers": [
                    {
                        "rowid": c['rowid'],
                        "name": c['name'],
                        "address": c['address'],
                        "lat": c['lat'],
                        "lng": c['lng'],
                        "priority_score": c['priority_score']
                    }
                    for c in cluster_customers
                ],
                "customer_count": len(cluster_customers)
            }
        
        return {
            "status": "success",
            "clusters": cluster_data,
            "total_clusters": len(clusters),
            "total_customers": len(customers)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get clusters: {str(e)}"}

@app.get("/route_efficiency_metrics")
def get_efficiency_metrics():
    """Get route optimization analytics and metrics"""
    try:
        # Get recent optimization history
        cursor.execute("""
            SELECT optimization_date, total_customers, total_distance, total_time,
                   fuel_cost_estimate, algorithm_used, efficiency_score
            FROM route_optimization_history 
            ORDER BY optimization_date DESC 
            LIMIT 30
        """)
        history_data = cursor.fetchall()
        
        history = []
        for row in history_data:
            (opt_date, total_customers, total_distance, total_time, 
             fuel_cost, algorithm, efficiency_score) = row
            history.append({
                "date": opt_date,
                "total_customers": total_customers,
                "total_distance": total_distance,
                "total_time": total_time,
                "fuel_cost_estimate": fuel_cost,
                "algorithm_used": algorithm,
                "efficiency_score": efficiency_score
            })
        
        # Get current schedule summary
        cursor.execute("""
            SELECT COUNT(*) as total_scheduled,
                   COUNT(DISTINCT scheduled_date) as days_covered,
                   SUM(estimated_duration) as total_service_time
            FROM service_schedule 
            WHERE scheduled_date >= date('now')
        """)
        current_summary = cursor.fetchone()
        
        # Calculate averages
        if history:
            avg_customers_per_day = sum(h["total_customers"] for h in history) / len(history)
            avg_distance_per_customer = sum(h["total_distance"] for h in history) / max(sum(h["total_customers"] for h in history), 1)
            avg_efficiency = sum(h["efficiency_score"] for h in history) / len(history)
        else:
            avg_customers_per_day = 0
            avg_distance_per_customer = 0
            avg_efficiency = 0
        
        return {
            "status": "success",
            "current_schedule": {
                "total_scheduled": current_summary[0] or 0,
                "days_covered": current_summary[1] or 0,
                "total_service_time": current_summary[2] or 0
            },
            "averages": {
                "customers_per_day": round(avg_customers_per_day, 1),
                "distance_per_customer": round(avg_distance_per_customer, 2),
                "efficiency_score": round(avg_efficiency, 2)
            },
            "recent_history": history,
            "total_optimizations": len(history)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get metrics: {str(e)}"}

@app.post("/manual_schedule_adjustment")
def manual_schedule_adjustment(
    customer_rowid: int = Form(...),
    new_date: str = Form(...),
    reason: str = Form("Manual adjustment")
):
    """Manually adjust a customer's scheduled service date"""
    try:
        # Update the schedule
        cursor.execute("""
            UPDATE service_schedule 
            SET scheduled_date = ?, service_day = ?
            WHERE customer_rowid = ?
        """, (
            new_date,
            datetime.fromisoformat(new_date).strftime('%A'),
            customer_rowid
        ))
        
        # Log the adjustment
        cursor.execute("""
            INSERT INTO route_optimization_history
            (optimization_date, total_customers, algorithm_used, efficiency_score)
            VALUES (?, 0, 'manual_adjustment', 0.0)
        """, (datetime.now().date(),))
        
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Customer {customer_rowid} rescheduled to {new_date}",
            "new_date": new_date,
            "reason": reason
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to adjust schedule: {str(e)}"}

@app.get("/daily_route/{date}")
def get_daily_route(date: str):
    """Get optimized route for a specific date"""
    try:
        cursor.execute("""
            SELECT c.rowid, c.name, c.address, c.lat, c.lng, c.service_duration,
                   s.priority_score, s.estimated_duration
            FROM customers c
            JOIN service_schedule s ON c.rowid = s.customer_rowid
            WHERE s.scheduled_date = ?
            ORDER BY s.priority_score DESC
        """, (date,))
        
        route_data = cursor.fetchall()
        
        if not route_data:
            return {"status": "success", "route": [], "metrics": {"total_customers": 0, "total_time": 0}}
        
        customers = []
        for row in route_data:
            (rowid, name, address, lat, lng, service_duration, 
             priority_score, estimated_duration) = row
            customers.append({
                'rowid': rowid,
                'name': name,
                'address': address,
                'lat': lat,
                'lng': lng,
                'service_duration': service_duration or 30,
                'priority_score': priority_score or 1.0,
                'estimated_duration': estimated_duration or 30
            })
        
        # Optimize the route
        optimized_route = optimize_route_greedy(customers)
        
        # Calculate metrics
        total_time = sum(c['service_duration'] for c in optimized_route)
        total_distance = 0
        if len(optimized_route) > 1:
            for i in range(len(optimized_route) - 1):
                total_distance += calculate_distance(
                    optimized_route[i]['lat'], optimized_route[i]['lng'],
                    optimized_route[i+1]['lat'], optimized_route[i+1]['lng']
                )
        
        return {
            "status": "success",
            "date": date,
            "route": optimized_route,
            "metrics": {
                "total_customers": len(optimized_route),
                "total_time": total_time,
                "total_distance": round(total_distance, 2),
                "fuel_cost_estimate": round(total_distance * 0.50, 2)
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get daily route: {str(e)}"}

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


# ========== LOCATIONS ENDPOINTS ==========

@app.get("/locations")
def get_locations():
    """Get all locations"""
    local_cursor = conn.cursor()
    local_cursor.execute("SELECT id, name, address, service_area_zips, phone FROM locations ORDER BY name ASC")
    rows = local_cursor.fetchall()
    locations = []
    for loc_id, name, address, service_area_zips, phone in rows:
        locations.append({
            "id": loc_id,
            "name": name,
            "address": address,
            "service_area_zips": service_area_zips,
            "phone": phone
        })
    return {"locations": locations}


@app.post("/locations")
def create_location(name: str = Form(...), address: str = Form(default=""), service_area_zips: str = Form(default=""), phone: str = Form(default="")):
    """Create a new location with automatic geocoding"""
    try:
        # Geocode the address to get lat/lng
        lat = None
        lng = None
        if address:
            try:
                lat, lng = geocode_geocodio(address)
            except Exception as e:
                print(f"Geocoding failed for address '{address}': {e}")
        
        cursor.execute(
            "INSERT INTO locations (name, address, service_area_zips, phone, lat, lng) VALUES (?, ?, ?, ?, ?, ?)",
            (name, address, service_area_zips, phone, lat, lng)
        )
        conn.commit()
        loc_id = cursor.lastrowid
        return {"status": "success", "id": loc_id, "message": f"Location '{name}' created"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Location name already exists"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/locations/{location_id}")
def update_location(location_id: int, name: str = Form(...), address: str = Form(default=""), service_area_zips: str = Form(default=""), phone: str = Form(default="")):
    """Update a location with automatic geocoding if address changes"""
    try:
        # Check if address is being updated
        cursor.execute("SELECT address FROM locations WHERE id = ?", (location_id,))
        current_address = cursor.fetchone()
        
        # Geocode the new address to get lat/lng if address changed
        lat = None
        lng = None
        if address and (not current_address or current_address[0] != address):
            try:
                lat, lng = geocode_geocodio(address)
                print(f"Geocoded updated address '{address}' to {lat}, {lng}")
            except Exception as e:
                print(f"Geocoding failed for address '{address}': {e}")
        
        cursor.execute(
            "UPDATE locations SET name = ?, address = ?, service_area_zips = ?, phone = ?, lat = ?, lng = ? WHERE id = ?",
            (name, address, service_area_zips, phone, lat, lng, location_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            return {"status": "success", "message": f"Location updated"}
        else:
            return {"status": "error", "message": "Location not found"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Location name already exists"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/locations/{location_id}")
def delete_location(location_id: int):
    """Delete a location"""
    try:
        # Check if location has customers
        cursor.execute("SELECT COUNT(*) FROM customers WHERE location_id = ?", (location_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            return {"status": "error", "message": f"Cannot delete location with {count} customer(s). Reassign customers first."}
        
        cursor.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return {"status": "success", "message": "Location deleted"}
        else:
            return {"status": "error", "message": "Location not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ========== OFFICE WORKERS ENDPOINTS ==========

@app.get("/office-workers")
def get_office_workers():
    """Get all office workers with their location info"""
    try:
        cursor.execute("""
            SELECT ow.id, ow.name, ow.location_id, ow.username, ow.is_active, ow.created_at,
                   l.name as location_name
            FROM office_workers ow
            JOIN locations l ON ow.location_id = l.id
            ORDER BY ow.name ASC
        """)
        rows = cursor.fetchall()
        workers = []
        for row in rows:
            workers.append({
                "id": row[0],
                "name": row[1],
                "location_id": row[2],
                "username": row[3],
                "is_active": bool(row[4]),
                "created_at": row[5],
                "location_name": row[6]
            })
        return {"office_workers": workers}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/office-workers")
def create_office_worker(
    name: str = Form(...),
    location_id: int = Form(...),
    username: str = Form(...),
    password: str = Form(...)
):
    """Create a new office worker"""
    try:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("""
            INSERT INTO office_workers (name, location_id, username, password_hash, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (name, location_id, username, password_hash, True))
        conn.commit()
        worker_id = cursor.lastrowid
        return {"status": "success", "id": worker_id, "message": f"Office worker '{name}' created"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/office-workers/{worker_id}")
def update_office_worker(
    worker_id: int,
    name: str = Form(None),
    location_id: int = Form(None),
    username: str = Form(None),
    password: str = Form(None),
    is_active: bool = Form(None)
):
    """Update an office worker"""
    try:
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if location_id is not None:
            updates.append("location_id = ?")
            params.append(location_id)
        if username is not None:
            updates.append("username = ?")
            params.append(username)
        if password is not None:
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            updates.append("password_hash = ?")
            params.append(password_hash)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        
        if not updates:
            return {"status": "error", "message": "No updates provided"}
        
        params.append(worker_id)
        cursor.execute(f"UPDATE office_workers SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        
        if cursor.rowcount > 0:
            return {"status": "success", "message": "Office worker updated"}
        else:
            return {"status": "error", "message": "Office worker not found"}
    except sqlite3.IntegrityError:
        return {"status": "error", "message": "Username already exists"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.delete("/office-workers/{worker_id}")
def delete_office_worker(worker_id: int):
    """Delete an office worker"""
    try:
        cursor.execute("DELETE FROM office_workers WHERE id = ?", (worker_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return {"status": "success", "message": "Office worker deleted"}
        else:
            return {"status": "error", "message": "Office worker not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ========== SERVICE VISITS ENDPOINTS ==========

@app.get("/service-visits")
def get_service_visits(location_id: int = None, days: int = 30):
    """Get service visits, optionally filtered by location and date range"""
    if location_id:
        cursor.execute("""
            SELECT sv.id, sv.location_id, sv.customer_id, sv.service_date, sv.treatment_id,
                   sv.condition_before, sv.condition_after, sv.chemicals_used, sv.notes,
                   sv.duration_minutes, sv.labor_hours, sv.material_cost, sv.technician_name,
                   c.name as customer_name, l.name as location_name
            FROM service_visits sv
            JOIN customers c ON sv.customer_id = c.id
            JOIN locations l ON sv.location_id = l.id
            WHERE sv.location_id = ? AND sv.service_date >= datetime('now', '-' || ? || ' days')
            ORDER BY sv.service_date DESC
        """, (location_id, days))
    else:
        cursor.execute("""
            SELECT sv.id, sv.location_id, sv.customer_id, sv.service_date, sv.treatment_id,
                   sv.condition_before, sv.condition_after, sv.chemicals_used, sv.notes,
                   sv.duration_minutes, sv.labor_hours, sv.material_cost, sv.technician_name,
                   c.name as customer_name, l.name as location_name
            FROM service_visits sv
            JOIN customers c ON sv.customer_id = c.id
            JOIN locations l ON sv.location_id = l.id
            WHERE sv.service_date >= datetime('now', '-' || ? || ' days')
            ORDER BY sv.service_date DESC
        """, (days,))
    
    rows = cursor.fetchall()
    visits = []
    for row in rows:
        visits.append({
            "id": row[0],
            "location_id": row[1],
            "customer_id": row[2],
            "service_date": row[3],
            "treatment_id": row[4],
            "condition_before": row[5],
            "condition_after": row[6],
            "chemicals_used": row[7],
            "notes": row[8],
            "duration_minutes": row[9],
            "labor_hours": row[10],
            "material_cost": row[11],
            "technician_name": row[12],
            "customer_name": row[13],
            "location_name": row[14]
        })
    return {"service_visits": visits}


@app.post("/service-visits")
def create_service_visit(
    location_id: int = Form(...),
    customer_id: int = Form(...),
    condition_before: str = Form(default="Fair"),
    condition_after: str = Form(default="Fair"),
    chemicals_used: str = Form(default="[]"),
    notes: str = Form(default=""),
    duration_minutes: int = Form(default=0),
    labor_hours: float = Form(default=0),
    material_cost: float = Form(default=0),
    technician_name: str = Form(default="Unknown"),
    treatment_id: int = Form(default=None)
):
    """Create a new service visit record"""
    try:
        cursor.execute("""
            INSERT INTO service_visits 
            (location_id, customer_id, condition_before, condition_after, chemicals_used, notes, 
             duration_minutes, labor_hours, material_cost, technician_name, treatment_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (location_id, customer_id, condition_before, condition_after, chemicals_used, notes,
              duration_minutes, labor_hours, material_cost, technician_name, treatment_id))
        conn.commit()
        visit_id = cursor.lastrowid
        
        # Also update customer's last_service_date
        cursor.execute("UPDATE customers SET last_service_date = datetime('now') WHERE id = ?", (customer_id,))
        conn.commit()
        
        return {"status": "success", "id": visit_id, "message": "Service visit recorded"}
    except Exception as e:
        import traceback
        print(f"Service visit creation error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/analytics/overview")
def get_analytics_overview(location_id: int = None, days: int = 30):
    """Get high-level analytics: total visits, total revenue, avg condition improvement"""
    if location_id:
        filter_clause = "WHERE sv.location_id = ?"
        params = (location_id, days)
    else:
        filter_clause = ""
        params = (days,)
    
    query = f"""
        SELECT 
            COUNT(sv.id) as total_visits,
            SUM(sv.labor_hours) as total_labor_hours,
            SUM(sv.material_cost) as total_material_cost,
            AVG(CAST(sv.condition_after AS INTEGER)) as avg_condition_after
        FROM service_visits sv
        {filter_clause}
        AND sv.service_date >= datetime('now', '-' || ? || ' days')
    """
    
    cursor.execute(query, params if location_id else params)
    row = cursor.fetchone()
    
    if not row:
        return {
            "total_visits": 0,
            "total_labor_hours": 0,
            "total_material_cost": 0,
            "avg_condition_after": 0,
            "estimated_revenue": 0
        }
    
    total_visits, total_labor_hours, total_material_cost, avg_condition = row
    estimated_revenue = (total_labor_hours or 0) * 50 + (total_material_cost or 0)  # rough estimate
    
    return {
        "total_visits": total_visits or 0,
        "total_labor_hours": total_labor_hours or 0,
        "total_material_cost": total_material_cost or 0,
        "avg_condition_after": round(avg_condition or 0, 1),
        "estimated_revenue": round(estimated_revenue, 2)
    }


@app.get("/analytics/by-location")
def get_analytics_by_location(days: int = 30):
    """Get analytics broken down by location"""
    cursor.execute("""
        SELECT 
            l.id,
            l.name,
            COUNT(sv.id) as visit_count,
            SUM(sv.labor_hours) as total_labor_hours,
            SUM(sv.material_cost) as total_material_cost,
            COUNT(DISTINCT sv.customer_id) as unique_customers
        FROM locations l
        LEFT JOIN service_visits sv ON l.id = sv.location_id 
            AND sv.service_date >= datetime('now', '-' || ? || ' days')
        GROUP BY l.id, l.name
        ORDER BY visit_count DESC
    """, (days,))
    
    rows = cursor.fetchall()
    locations_analytics = []
    for row in rows:
        locations_analytics.append({
            "location_id": row[0],
            "location_name": row[1],
            "visit_count": row[2] or 0,
            "total_labor_hours": row[3] or 0,
            "total_material_cost": row[4] or 0,
            "unique_customers": row[5] or 0,
            "estimated_revenue": round((row[3] or 0) * 50 + (row[4] or 0), 2)
        })
    return {"locations": locations_analytics}


@app.get("/analytics/worker-performance")
def get_worker_performance(days: int = 30):
    """Get technician/worker performance analytics"""
    cursor.execute("""
        SELECT 
            sv.technician_name,
            COUNT(sv.id) as services_completed,
            SUM(sv.labor_hours) as total_hours,
            SUM(sv.material_cost) as total_material_cost,
            AVG(CAST(sv.condition_after AS INTEGER)) as avg_condition_improvement
        FROM service_visits sv
        WHERE sv.service_date >= datetime('now', '-' || ? || ' days')
        GROUP BY sv.technician_name
        ORDER BY services_completed DESC
    """, (days,))
    
    rows = cursor.fetchall()
    workers = []
    for row in rows:
        workers.append({
            "technician_name": row[0],
            "services_completed": row[1] or 0,
            "total_hours": row[2] or 0,
            "total_material_cost": row[3] or 0,
            "avg_condition_improvement": round(row[4] or 0, 1),
            "estimated_revenue": round((row[2] or 0) * 50 + (row[3] or 0), 2)
        })
    return {"workers": workers}


@app.get("/analytics/condition-trends")
def get_condition_trends(location_id: int = None):
    """Get lawn condition improvement trends"""
    if location_id:
        query = """
            SELECT 
                sv.condition_before,
                sv.condition_after,
                COUNT(*) as count
            FROM service_visits sv
            WHERE sv.location_id = ?
            GROUP BY sv.condition_before, sv.condition_after
        """
        cursor.execute(query, (location_id,))
    else:
        query = """
            SELECT 
                sv.condition_before,
                sv.condition_after,
                COUNT(*) as count
            FROM service_visits sv
            GROUP BY sv.condition_before, sv.condition_after
        """
        cursor.execute(query)
    
    rows = cursor.fetchall()
    trends = []
    for row in rows:
        trends.append({
            "condition_before": row[0],
            "condition_after": row[1],
            "count": row[2]
        })
    return {"trends": trends}


@app.get("/analytics/office-dashboard")
def get_office_dashboard(request: Request, days: int = 30):
    """Get office worker dashboard metrics for their assigned location"""
    if not request.session.get('logged_in'):
        return {"error": "Not authenticated"}
    
    user_type = request.session.get('user_type')
    location_id = request.session.get('location_id')
    
    # Admin can optionally filter by location, office worker sees their location only
    if user_type == 'office_worker' and not location_id:
        return {"error": "No location assigned"}
    
    target_location = location_id if user_type == 'office_worker' else request.query_params.get('location_id')
    
    if not target_location:
        return {"error": "Location required"}
    
    try:
        # Get service stats for the location
        cursor.execute("""
            SELECT 
                COUNT(*) as total_scheduled,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'rescheduled' THEN 1 ELSE 0 END) as rescheduled
            FROM service_schedule
            WHERE location_id = ? AND scheduled_date >= date('now', '-{} days')
        """.format(days), (target_location,))
        row = cursor.fetchone()
        total_scheduled = row[0] or 0
        completed = row[1] or 0
        rescheduled = row[2] or 0
        
        completed_pct = (completed / total_scheduled * 100) if total_scheduled > 0 else 0
        reschedule_pct = (rescheduled / total_scheduled * 100) if total_scheduled > 0 else 0
        
        # Get revenue stats
        cursor.execute("""
            SELECT 
                SUM(actual_price) as actual_revenue,
                SUM(monthly_min) as estimated_min,
                SUM(monthly_max) as estimated_max
            FROM customers
            WHERE location_id = ?
        """, (target_location,))
        row = cursor.fetchone()
        actual_revenue = row[0] or 0
        estimated_min = row[1] or 0
        estimated_max = row[2] or 0
        
        # Get today's sales (new customers added today)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM customers 
            WHERE location_id = ? AND date(created_at) = date('now')
        """, (target_location,))
        sales_today = cursor.fetchone()[0] or 0
        
        return {
            "location_id": target_location,
            "completed_pct": round(completed_pct, 1),
            "reschedule_pct": round(reschedule_pct, 1),
            "actual_revenue": round(actual_revenue, 2),
            "estimated_revenue": round((estimated_min + estimated_max) / 2, 2),
            "sales_today": sales_today,
            "total_scheduled": total_scheduled,
            "completed": completed,
            "rescheduled": rescheduled
        }
        
    except Exception as e:
        return {"error": str(e)}


# ====== OFFICE WORKER DAILY ROUTE OPTIMIZATION ======

import math

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate straight-line distance between two points in miles"""
    R = 3959  # Earth's radius in miles
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def point_in_polygon(lat: float, lng: float, polygon_coords: list) -> bool:
    """Check if a point is inside a polygon using ray casting algorithm
    Note: polygon_coords is stored as [lat, lng] pairs, but algorithm needs [x, y] = [lng, lat]
    """
    n = len(polygon_coords)
    inside = False
    
    j = n - 1
    for i in range(n):
        # Swap: stored as [lat, lng], but algorithm needs [x, y] = [lng, lat]
        yi, xi = polygon_coords[i]  # lat, lng
        yj, xj = polygon_coords[j]  # lat, lng
        
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside

@app.get("/routing/daily-routes")
def get_daily_routes(request: Request, location_id: int = None, date: str = None):
    """
    Generate optimized daily routes for all technicians at a location.
    Office workers see their assigned location only, admins can specify location.
    """
    if not request.session.get('logged_in'):
        return {"status": "error", "message": "Not authenticated"}
    
    user_type = request.session.get('user_type')
    user_location_id = request.session.get('location_id')
    
    if user_type == 'office_worker':
        target_location = user_location_id
    else:
        target_location = location_id
    
    if not target_location:
        return {"status": "error", "message": "Location required"}
    
    try:
        # Get office location coordinates
        cursor.execute("SELECT lat, lng, address FROM locations WHERE id = ?", (target_location,))
        loc_data = cursor.fetchone()
        
        if not loc_data:
            return {"status": "error", "message": "Office location not found"}
        
        office_lat, office_lng, office_address = loc_data
        
        if not office_lat or not office_lng:
            # Fallback: geocode the address
            office_lat, office_lng = geocode_address(office_address or "Keller, TX")
        
        # Get all active technicians at this location with their territories
        cursor.execute("""
            SELECT t.id, t.name, t.color_hex, tt.polygon_coords
            FROM technicians t
            LEFT JOIN technician_territories tt ON t.id = tt.technician_id
            WHERE t.location_id = ? AND t.is_active = 1
        """, (target_location,))
        
        technicians = cursor.fetchall()
        
        if not technicians:
            return {"status": "error", "message": "No active technicians at this location"}
        
        # Generate routes for each technician
        daily_routes = []
        
        for tech in technicians:
            tech_id, tech_name, tech_color, polygon_coords = tech
            
            if not polygon_coords:
                daily_routes.append({
                    "technician_id": tech_id,
                    "technician_name": tech_name,
                    "technician_color": tech_color,
                    "customers": [],
                    "message": "No territory assigned"
                })
                continue
            
            try:
                coords = json.loads(polygon_coords)
            except:
                daily_routes.append({
                    "technician_id": tech_id,
                    "technician_name": tech_name,
                    "technician_color": tech_color,
                    "customers": [],
                    "message": "Invalid territory data"
                })
                continue
            
            # Get due customers in this technician's territory (45+ days like the rest of the app)
            cursor.execute("""
                SELECT 
                    c.id, c.name, c.address, c.sqft, c.actual_price, 
                    c.lat, c.lng, c.last_service_date,
                    julianday('now') - julianday(c.last_service_date) as days_since_service
                FROM customers c
                WHERE c.location_id = ? AND c.lat IS NOT NULL AND c.lng IS NOT NULL
                    AND (c.last_service_date IS NULL OR julianday('now') - julianday(c.last_service_date) > 45)
            """, (target_location,))
            
            all_due_customers = cursor.fetchall()
            print(f"Tech {tech_name}: Found {len(all_due_customers)} total due customers at location {target_location}")
            print(f"Tech {tech_name}: Territory coords: {coords[:3] if coords else 'none'}...")
            
            customers = []
            for row in all_due_customers:
                lat, lng = row[5], row[6]
                print(f"  Checking {row[1]} at ({lat}, {lng}) in polygon...")
                in_poly = point_in_polygon(lat, lng, coords)
                print(f"    -> point_in_polygon result: {in_poly}")
                if in_poly:
                    customers.append({
                        "id": row[0],
                        "name": row[1],
                        "address": row[2],
                        "sqft": row[3] or 0,
                        "actual_price": row[4] or 0,
                        "lat": row[5],
                        "lng": row[6],
                        "days_since_service": row[8] or 999
                    })
            
            print(f"Tech {tech_name}: {len(customers)} customers in territory")
            
            # Sort by days since service (most overdue first)
            customers.sort(key=lambda x: x["days_since_service"], reverse=True)
            
            # Optimize route with capacity constraints (200k sqft or $1500)
            MAX_SQFT = 200000
            MAX_REVENUE = 1500.0
            
            route = []
            total_sqft = 0
            total_revenue = 0
            current_lat = office_lat
            current_lng = office_lng
            
            remaining = customers.copy()
            
            while remaining:
                # Find nearest customer
                nearest_idx = None
                nearest_dist = float('inf')
                
                for i, customer in enumerate(remaining):
                    dist = haversine_distance(current_lat, current_lng, customer["lat"], customer["lng"])
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_idx = i
                
                if nearest_idx is None:
                    break
                
                customer = remaining[nearest_idx]
                
                # Check capacity constraints
                new_sqft = total_sqft + customer["sqft"]
                new_revenue = total_revenue + customer["actual_price"]
                
                if new_sqft > MAX_SQFT or new_revenue > MAX_REVENUE:
                    break
                
                # Add to route with metrics
                customer["drive_miles"] = round(nearest_dist, 2)
                customer["drive_minutes"] = round((nearest_dist / 30) * 60, 1)
                customer["service_minutes"] = round(customer["sqft"] / 1000, 1)
                
                route.append(customer)
                total_sqft = new_sqft
                total_revenue = new_revenue
                
                current_lat = customer["lat"]
                current_lng = customer["lng"]
                remaining.pop(nearest_idx)
            
            # Calculate totals including return to office
            total_drive_miles = sum(c["drive_miles"] for c in route)
            total_service_minutes = sum(c["service_minutes"] for c in route)
            total_drive_minutes = sum(c["drive_minutes"] for c in route)
            
            if route:
                return_dist = haversine_distance(current_lat, current_lng, office_lat, office_lng)
                total_drive_miles += round(return_dist, 2)
                total_drive_minutes += round((return_dist / 30) * 60, 1)
            
            daily_routes.append({
                "technician_id": tech_id,
                "technician_name": tech_name,
                "technician_color": tech_color,
                "customers": route,
                "total_sqft": total_sqft,
                "total_revenue": round(total_revenue, 2),
                "total_drive_miles": round(total_drive_miles, 2),
                "total_service_minutes": round(total_service_minutes, 1),
                "total_drive_minutes": round(total_drive_minutes, 1),
                "total_time_minutes": round(total_service_minutes + total_drive_minutes, 1),
                "customer_count": len(route),
                "remaining_due": len(remaining)
            })
        
        # Calculate summary
        all_customers = sum(r["customer_count"] for r in daily_routes)
        total_sqft = sum(r["total_sqft"] for r in daily_routes)
        total_revenue = sum(r["total_revenue"] for r in daily_routes)
        
        return {
            "status": "success",
            "location_id": target_location,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "office_location": {"lat": office_lat, "lng": office_lng},
            "technician_routes": daily_routes,
            "summary": {
                "total_technicians": len(daily_routes),
                "total_customers_assigned": all_customers,
                "total_sqft": total_sqft,
                "total_revenue": round(total_revenue, 2)
            }
        }
        
    except Exception as e:
        import traceback
        print(f"Daily routes error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}