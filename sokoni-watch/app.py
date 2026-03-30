from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import json, os, random, uuid
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "sokoni-watch-nairobi-2024-secret-xk9"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 7  # 7 days
DATA_FILE = "data/stock_data.json"

# ─── Kenyan Data ──────────────────────────────────────────────────────────
CATEGORIES = {
    "Mboga": ["Sukuma Wiki", "Managu", "Kunde", "Spinach", "Cabbage", "Tomatoes", "Pilipili Hoho", "Karoti", "Beetroot", "Mchicha"],
    "Matunda": ["Embe", "Papai", "Ndizi", "Machungwa", "Pineapple", "Watermelon", "Avocado", "Passion Fruit", "Guava", "Strawberry"],
    "Nafaka": ["Mahindi", "Unga wa Ngano", "Unga wa Mahindi", "Mchele", "Maharage", "Dengu", "Njahi", "Viazi Vitamu", "Viazi Kawaida", "Mtama"],
    "Vinywaji": ["Maji ya Embe", "Uji", "Togwa", "Maziwa", "Maji ya Machungwa", "Tangawizi Juice", "Tamarind", "Passion Juice"],
    "Samaki": ["Tilapia", "Dagaa", "Sangara", "Perch", "Omena", "Catfish", "Ngege", "Kambale"],
    "Nyama": ["Nyama ya Ng'ombe", "Kuku", "Nguruwe", "Offals", "Sausages", "Mbuzi"],
    "Viungo": ["Chumvi", "Sukari", "Pilipili", "Tangawizi", "Bizari", "Curry Powder", "Turmeric", "Coriander"],
}

MARKET_LOCATIONS = [
    "Gikomba Market", "Toi Market", "Wakulima Market", "City Market",
    "Eastleigh Market", "Kangemi Market", "Kawangware Market", "Ongata Rongai",
    "Githurai 44", "Ngara Market", "Korogocho Market", "Kariobangi Market"
]

# ─── Auth helpers ─────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session or session["user"]["role"] != "admin":
            return jsonify({"error": "admin only"}), 403
        return f(*args, **kwargs)
    return decorated

# ─── Data helpers ─────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return initialize_data()

def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def generate_history():
    return [{"date": (datetime.now()-timedelta(days=6-i)).strftime("%Y-%m-%d"),
             "stock": random.randint(10,180), "sales": random.randint(5,50)} for i in range(7)]

def generate_alerts(hawkers, admin_stock):
    alerts = []
    for hawker in hawkers:
        for product in hawker["products"]:
            # Check if admin has stock for this product
            admin_qty = admin_stock.get(product["name"], 0)
            if product["current_stock"] <= product["min_threshold"]:
                level = "critical" if product["current_stock"] <= product["min_threshold"]*0.5 else "warning"
                alerts.append({
                    "id": str(uuid.uuid4())[:8],
                    "hawker_id": hawker["id"],
                    "hawker_name": hawker["name"],
                    "product": product["name"],
                    "current_stock": product["current_stock"],
                    "min_threshold": product["min_threshold"],
                    "level": level,
                    "location": hawker["location"],
                    "admin_has_stock": admin_qty > 0,
                    "admin_qty": admin_qty,
                    "timestamp": datetime.now().isoformat(),
                    "read": False
                })
    return alerts

def initialize_data():
    # Admin credentials
    users = {
        "admin": {
            "id": "admin-001",
            "username": "admin",
            "password": "sokoni2024",
            "role": "admin",
            "name": "Bwana Sokoni",
            "phone": "+254712345678"
        }
    }

    # Admin's master stock warehouse
    admin_warehouse = {}
    for cat, products in CATEGORIES.items():
        for product in products:
            admin_warehouse[product] = {
                "name": product,
                "category": cat,
                "quantity": random.randint(100, 1000),
                "unit": random.choice(["kg", "bunch", "piece", "litre", "packet"]),
                "price_ksh": round(random.uniform(20, 500), 2),
                "reorder_level": 100
            }

    # Hawkers
    hawker_names = [
        ("Mama Njeri", "mama_njeri", "njeri2024"),
        ("Baba Kamau", "baba_kamau", "kamau2024"),
        ("Auntie Wanjiku", "auntie_wanjiku", "wanjiku2024"),
        ("Uncle Otieno", "uncle_otieno", "otieno2024"),
        ("Mama Amina", "mama_amina", "amina2024"),
        ("Sister Chebet", "sister_chebet", "chebet2024"),
        ("Baba Hassan", "baba_hassan", "hassan2024"),
        ("Mama Zawadi", "mama_zawadi", "zawadi2024"),
    ]

    hawkers = []
    for i, (name, username, password) in enumerate(hawker_names):
        cat = list(CATEGORIES.keys())[i % len(CATEGORIES)]
        products_list = CATEGORIES[cat][:5]
        hawker_id = str(uuid.uuid4())[:8]

        # Register hawker as user
        users[username] = {
            "id": hawker_id,
            "username": username,
            "password": password,
            "role": "hawker",
            "name": name,
            "phone": f"+2547{random.randint(10000000,99999999)}"
        }

        products = []
        for product in products_list:
            max_stock = random.randint(50, 200)
            current = random.randint(5, max_stock)
            products.append({
                "id": str(uuid.uuid4())[:6],
                "name": product,
                "category": cat,
                "current_stock": current,
                "max_stock": max_stock,
                "min_threshold": int(max_stock * 0.2),
                "unit": admin_warehouse[product]["unit"],
                "price_ksh": admin_warehouse[product]["price_ksh"],
                "last_restocked": (datetime.now()-timedelta(days=random.randint(0,5))).isoformat(),
                "sales_today": random.randint(0, 30),
                "history": generate_history()
            })

        hawkers.append({
            "id": hawker_id,
            "name": name,
            "username": username,
            "location": MARKET_LOCATIONS[i % len(MARKET_LOCATIONS)],
            "category": cat,
            "phone": users[username]["phone"],
            "products": products,
            "joined": (datetime.now()-timedelta(days=random.randint(30,365))).isoformat(),
            "mpesa_till": str(random.randint(100000, 999999)),
            "active": True
        })

    # Build admin stock dict for alert generation
    admin_stock_qty = {k: v["quantity"] for k, v in admin_warehouse.items()}
    alerts = generate_alerts(hawkers, admin_stock_qty)

    data = {
        "users": users,
        "hawkers": hawkers,
        "admin_warehouse": admin_warehouse,
        "alerts": alerts,
        "last_updated": datetime.now().isoformat()
    }
    save_data(data)
    return data

# ─── Page Routes ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login")
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/logout-api", methods=["POST"])
def logout_api():
    """Clear session via POST - used by login page before re-login"""
    session.clear()
    return jsonify({"success": True})

# ─── Auth API ─────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.json
    data = load_data()
    username = body.get("username","").strip().lower()
    password = body.get("password","").strip()
    user = data["users"].get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Jina au neno siri si sahihi — Wrong username or password"}), 401
    session.clear()
    session.permanent = True
    session["user"] = {"id": user["id"], "username": username, "role": user["role"], "name": user["name"]}
    return jsonify({"success": True, "role": user["role"], "name": user["name"]})

@app.route("/api/me")
@login_required
def api_me():
    return jsonify(session["user"])

# ─── Dashboard Stats ──────────────────────────────────────────────────────
@app.route("/api/dashboard")
@login_required
def api_dashboard():
    data = load_data()
    role = session["user"]["role"]
    if role == "admin":
        total_products = sum(len(h["products"]) for h in data["hawkers"])
        low_stock = sum(1 for h in data["hawkers"] for p in h["products"] if p["current_stock"] <= p["min_threshold"])
        critical = sum(1 for h in data["hawkers"] for p in h["products"] if p["current_stock"] <= p["min_threshold"]*0.5)
        total_sales = sum(p["sales_today"] for h in data["hawkers"] for p in h["products"])
        warehouse_items = len(data["admin_warehouse"])
        warehouse_value = sum(v["quantity"]*v["price_ksh"] for v in data["admin_warehouse"].values())
        return jsonify({
            "total_hawkers": len(data["hawkers"]),
            "total_products": total_products,
            "low_stock_count": low_stock,
            "critical_count": critical,
            "total_sales_today": total_sales,
            "active_alerts": len([a for a in data["alerts"] if not a["read"]]),
            "warehouse_items": warehouse_items,
            "warehouse_value": round(warehouse_value, 2),
            "last_updated": data["last_updated"]
        })
    else:
        # Hawker dashboard
        hawker = next((h for h in data["hawkers"] if h["id"] == session["user"]["id"]), None)
        if not hawker:
            return jsonify({"error": "Hawker not found"}), 404
        low = sum(1 for p in hawker["products"] if p["current_stock"] <= p["min_threshold"])
        total_sales = sum(p["sales_today"] for p in hawker["products"])
        # What's hot market-wide
        all_sales = {}
        for h in data["hawkers"]:
            for p in h["products"]:
                all_sales[p["name"]] = all_sales.get(p["name"], 0) + p["sales_today"]
        hot = sorted(all_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        return jsonify({
            "hawker": hawker,
            "low_stock": low,
            "total_sales": total_sales,
            "product_count": len(hawker["products"]),
            "hot_products": hot,
            "active_alerts": len([a for a in data["alerts"] if a["hawker_id"]==hawker["id"] and not a["read"]])
        })

# ─── Hawkers Management (Admin) ───────────────────────────────────────────
@app.route("/api/hawkers")
@login_required
def get_hawkers():
    data = load_data()
    return jsonify(data["hawkers"])

@app.route("/api/hawkers", methods=["POST"])
@admin_required
def add_hawker():
    body = request.json
    data = load_data()
    username = body["username"].strip().lower()
    if username in data["users"]:
        return jsonify({"error": "Username already exists"}), 400
    hawker_id = str(uuid.uuid4())[:8]
    cat = body.get("category", "Mboga")
    data["users"][username] = {
        "id": hawker_id, "username": username,
        "password": body["password"], "role": "hawker",
        "name": body["name"], "phone": body.get("phone","")
    }
    new_hawker = {
        "id": hawker_id, "name": body["name"], "username": username,
        "location": body.get("location","Nairobi"), "category": cat,
        "phone": body.get("phone",""), "products": [],
        "joined": datetime.now().isoformat(),
        "mpesa_till": body.get("mpesa_till",""), "active": True
    }
    data["hawkers"].append(new_hawker)
    save_data(data)
    return jsonify({"success": True, "hawker": new_hawker})

@app.route("/api/hawkers/<hawker_id>", methods=["DELETE"])
@admin_required
def delete_hawker(hawker_id):
    data = load_data()
    hawker = next((h for h in data["hawkers"] if h["id"] == hawker_id), None)
    if not hawker:
        return jsonify({"error": "Not found"}), 404
    # Remove user account
    data["users"] = {k:v for k,v in data["users"].items() if v.get("id") != hawker_id}
    data["hawkers"] = [h for h in data["hawkers"] if h["id"] != hawker_id]
    data["alerts"] = [a for a in data["alerts"] if a["hawker_id"] != hawker_id]
    save_data(data)
    return jsonify({"success": True})

@app.route("/api/hawkers/<hawker_id>")
@login_required
def get_hawker(hawker_id):
    data = load_data()
    hawker = next((h for h in data["hawkers"] if h["id"] == hawker_id), None)
    if not hawker:
        return jsonify({"error": "Not found"}), 404
    return jsonify(hawker)

# ─── Stock Distribution (Admin → Hawker) ─────────────────────────────────
@app.route("/api/distribute", methods=["POST"])
@admin_required
def distribute_stock():
    """Admin distributes stock from warehouse to a hawker"""
    body = request.json
    data = load_data()
    hawker = next((h for h in data["hawkers"] if h["id"] == body["hawker_id"]), None)
    if not hawker:
        return jsonify({"error": "Hawker not found"}), 404
    product_name = body["product_name"]
    qty = int(body["quantity"])
    warehouse_item = data["admin_warehouse"].get(product_name)
    if not warehouse_item:
        return jsonify({"error": "Product not in warehouse"}), 404
    if warehouse_item["quantity"] < qty:
        return jsonify({"error": f"Not enough stock. Available: {warehouse_item['quantity']}"}), 400
    # Deduct from warehouse
    warehouse_item["quantity"] -= qty
    # Add/update hawker product
    existing = next((p for p in hawker["products"] if p["name"] == product_name), None)
    if existing:
        existing["current_stock"] = min(existing["current_stock"] + qty, existing["max_stock"])
        existing["last_restocked"] = datetime.now().isoformat()
    else:
        max_stock = qty * 2
        hawker["products"].append({
            "id": str(uuid.uuid4())[:6],
            "name": product_name,
            "category": warehouse_item["category"],
            "current_stock": qty,
            "max_stock": max_stock,
            "min_threshold": int(max_stock * 0.2),
            "unit": warehouse_item["unit"],
            "price_ksh": warehouse_item["price_ksh"],
            "last_restocked": datetime.now().isoformat(),
            "sales_today": 0,
            "history": generate_history()
        })
    # Clear resolved alerts
    data["alerts"] = [a for a in data["alerts"] if not (a["hawker_id"]==body["hawker_id"] and a["product"]==product_name)]
    admin_stock_qty = {k: v["quantity"] for k, v in data["admin_warehouse"].items()}
    data["alerts"] = generate_alerts(data["hawkers"], admin_stock_qty)
    data["last_updated"] = datetime.now().isoformat()
    save_data(data)
    return jsonify({"success": True, "warehouse_remaining": warehouse_item["quantity"]})

# ─── Warehouse Management ─────────────────────────────────────────────────
@app.route("/api/warehouse")
@admin_required
def get_warehouse():
    data = load_data()
    return jsonify(list(data["admin_warehouse"].values()))

@app.route("/api/warehouse", methods=["POST"])
@admin_required
def add_warehouse_stock():
    body = request.json
    data = load_data()
    name = body["name"].strip()
    if name in data["admin_warehouse"]:
        data["admin_warehouse"][name]["quantity"] += int(body["quantity"])
    else:
        data["admin_warehouse"][name] = {
            "name": name, "category": body.get("category","Mboga"),
            "quantity": int(body["quantity"]),
            "unit": body.get("unit","kg"),
            "price_ksh": float(body.get("price_ksh",50)),
            "reorder_level": int(body.get("reorder_level",100))
        }
    save_data(data)
    return jsonify({"success": True})

@app.route("/api/warehouse/<product_name>", methods=["DELETE"])
@admin_required
def delete_warehouse_item(product_name):
    data = load_data()
    decoded = product_name.replace("_", " ")
    if decoded in data["admin_warehouse"]:
        del data["admin_warehouse"][decoded]
        save_data(data)
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

# ─── Hawker: Update Their Own Stock ──────────────────────────────────────
@app.route("/api/hawker/update_stock", methods=["POST"])
@login_required
def hawker_update_stock():
    if session["user"]["role"] != "hawker":
        return jsonify({"error": "Hawkers only"}), 403
    body = request.json
    data = load_data()
    hawker = next((h for h in data["hawkers"] if h["id"] == session["user"]["id"]), None)
    if not hawker:
        return jsonify({"error": "Not found"}), 404
    product = next((p for p in hawker["products"] if p["id"] == body["product_id"]), None)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    action = body.get("action", "set")
    if action == "sold":
        sold = min(int(body["quantity"]), product["current_stock"])
        product["current_stock"] -= sold
        product["sales_today"] += sold
    elif action == "set":
        product["current_stock"] = int(body["quantity"])
    admin_stock_qty = {k: v["quantity"] for k, v in data["admin_warehouse"].items()}
    data["alerts"] = generate_alerts(data["hawkers"], admin_stock_qty)
    data["last_updated"] = datetime.now().isoformat()
    save_data(data)
    return jsonify({"success": True, "product": product})

# ─── Market Pulse ──────────────────────────────────────────────────────────
@app.route("/api/market_pulse")
@login_required
def market_pulse():
    data = load_data()
    pulse = {}
    all_products = {}
    for hawker in data["hawkers"]:
        cat = hawker["category"]
        if cat not in pulse:
            pulse[cat] = {"total_products":0,"low_stock":0,"hawkers":0,"total_sales":0}
        pulse[cat]["hawkers"] += 1
        for p in hawker["products"]:
            pulse[cat]["total_products"] += 1
            pulse[cat]["total_sales"] += p["sales_today"]
            if p["current_stock"] <= p["min_threshold"]:
                pulse[cat]["low_stock"] += 1
            all_products[p["name"]] = all_products.get(p["name"],0) + p["sales_today"]
    hot = sorted(all_products.items(), key=lambda x:x[1], reverse=True)[:10]
    return jsonify({"categories": pulse, "hot_products": hot})

@app.route("/api/alerts")
@login_required
def get_alerts():
    data = load_data()
    if session["user"]["role"] == "admin":
        return jsonify(data["alerts"])
    hawker_id = session["user"]["id"]
    return jsonify([a for a in data["alerts"] if a["hawker_id"] == hawker_id])

@app.route("/api/alerts/read/<alert_id>", methods=["POST"])
@login_required
def mark_read(alert_id):
    data = load_data()
    for a in data["alerts"]:
        if a["id"] == alert_id:
            a["read"] = True
    save_data(data)
    return jsonify({"success": True})

@app.route("/api/categories")
@login_required
def get_categories():
    return jsonify(CATEGORIES)

@app.route("/api/simulate_sales", methods=["POST"])
@admin_required
def simulate_sales():
    data = load_data()
    for hawker in data["hawkers"]:
        for product in hawker["products"]:
            sold = random.randint(0, min(10, product["current_stock"]))
            product["current_stock"] = max(0, product["current_stock"] - sold)
            product["sales_today"] += sold
    admin_stock_qty = {k: v["quantity"] for k, v in data["admin_warehouse"].items()}
    data["alerts"] = generate_alerts(data["hawkers"], admin_stock_qty)
    data["last_updated"] = datetime.now().isoformat()
    save_data(data)
    return jsonify({"success": True})

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        initialize_data()
    app.run(debug=True, port=5000)
