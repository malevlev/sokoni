from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import json, os, random, uuid, psycopg2, psycopg2.extras
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "sokoni-watch-nairobi-2024-secret-xk9"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 86400 * 7

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_conn():
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

def db_query(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_one(sql, params=()):
    rows = db_query(sql, params)
    return rows[0] if rows else None

def db_exec(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()

CATEGORIES = {
    "Mboga": ["Sukuma Wiki","Managu","Kunde","Spinach","Cabbage","Tomatoes","Pilipili Hoho","Karoti","Beetroot","Mchicha"],
    "Matunda": ["Embe","Papai","Ndizi","Machungwa","Pineapple","Watermelon","Avocado","Passion Fruit","Guava","Strawberry"],
    "Nafaka": ["Mahindi","Unga wa Ngano","Unga wa Mahindi","Mchele","Maharage","Dengu","Njahi","Viazi Vitamu","Viazi Kawaida","Mtama"],
    "Vinywaji": ["Maji ya Embe","Uji","Togwa","Maziwa","Maji ya Machungwa","Tangawizi Juice","Tamarind","Passion Juice"],
    "Samaki": ["Tilapia","Dagaa","Sangara","Perch","Omena","Catfish","Ngege","Kambale"],
    "Nyama": ["Nyama ya Ng'ombe","Kuku","Nguruwe","Offals","Sausages","Mbuzi"],
    "Viungo": ["Chumvi","Sukari","Pilipili","Tangawizi","Bizari","Curry Powder","Turmeric","Coriander"],
}

MARKET_LOCATIONS = [
    "Gikomba Market","Toi Market","Wakulima Market","City Market",
    "Eastleigh Market","Kangemi Market","Kawangware Market","Ongata Rongai",
    "Githurai 44","Ngara Market","Korogocho Market","Kariobangi Market"
]

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT,
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS hawkers (
            id TEXT PRIMARY KEY,
            name TEXT,
            username TEXT,
            location TEXT,
            category TEXT,
            phone TEXT,
            joined TEXT,
            mpesa_till TEXT,
            active BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            hawker_id TEXT REFERENCES hawkers(id) ON DELETE CASCADE,
            name TEXT,
            category TEXT,
            current_stock INTEGER DEFAULT 0,
            max_stock INTEGER DEFAULT 100,
            min_threshold INTEGER DEFAULT 20,
            unit TEXT DEFAULT 'kg',
            price_ksh REAL DEFAULT 50,
            last_restocked TEXT,
            sales_today INTEGER DEFAULT 0,
            history JSONB DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS warehouse (
            name TEXT PRIMARY KEY,
            category TEXT,
            quantity INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'kg',
            price_ksh REAL DEFAULT 50,
            reorder_level INTEGER DEFAULT 100
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            hawker_id TEXT,
            hawker_name TEXT,
            product TEXT,
            current_stock INTEGER,
            min_threshold INTEGER,
            level TEXT,
            location TEXT,
            admin_has_stock BOOLEAN,
            admin_qty INTEGER,
            timestamp TEXT,
            read BOOLEAN DEFAULT FALSE
        );
    """)
    conn.commit()
    conn.close()

def _refresh_alerts():
    db_exec("DELETE FROM alerts")
    hawkers = db_query("SELECT * FROM hawkers")
    for h in hawkers:
        products = db_query("SELECT * FROM products WHERE hawker_id=%s", (h["id"],))
        for p in products:
            if p["current_stock"] <= p["min_threshold"]:
                level = "critical" if p["current_stock"] <= p["min_threshold"]*0.5 else "warning"
                wh = db_one("SELECT quantity FROM warehouse WHERE name=%s", (p["name"],))
                admin_qty = wh["quantity"] if wh else 0
                db_exec("""INSERT INTO alerts (id,hawker_id,hawker_name,product,current_stock,
                           min_threshold,level,location,admin_has_stock,admin_qty,timestamp,read)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (str(uuid.uuid4())[:8], h["id"], h["name"], p["name"],
                         p["current_stock"], p["min_threshold"], level, h["location"],
                         admin_qty>0, admin_qty, datetime.now().isoformat(), False))

def seed_db():
    if db_one("SELECT id FROM users WHERE username='admin'"):
        return
    db_exec("INSERT INTO users (id,username,password,role,name,phone) VALUES (%s,%s,%s,%s,%s,%s)",
            ("admin-001","admin","sokoni2024","admin","Bwana Sokoni","+254712345678"))
    for cat, prods in CATEGORIES.items():
        for product in prods:
            db_exec("""INSERT INTO warehouse (name,category,quantity,unit,price_ksh,reorder_level)
                       VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (name) DO NOTHING""",
                    (product, cat, random.randint(100,1000),
                     random.choice(["kg","bunch","piece","litre","packet"]),
                     round(random.uniform(20,500),2), 100))
    hawker_names = [
        ("Mama Njeri","mama_njeri","njeri2024"),("Baba Kamau","baba_kamau","kamau2024"),
        ("Auntie Wanjiku","auntie_wanjiku","wanjiku2024"),("Uncle Otieno","uncle_otieno","otieno2024"),
        ("Mama Amina","mama_amina","amina2024"),("Sister Chebet","sister_chebet","chebet2024"),
        ("Baba Hassan","baba_hassan","hassan2024"),("Mama Zawadi","mama_zawadi","zawadi2024"),
    ]
    for i,(name,username,password) in enumerate(hawker_names):
        cat = list(CATEGORIES.keys())[i % len(CATEGORIES)]
        hid = str(uuid.uuid4())[:8]
        phone = f"+2547{random.randint(10000000,99999999)}"
        db_exec("INSERT INTO users (id,username,password,role,name,phone) VALUES (%s,%s,%s,%s,%s,%s)",
                (hid,username,password,"hawker",name,phone))
        db_exec("INSERT INTO hawkers (id,name,username,location,category,phone,joined,mpesa_till,active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (hid,name,username,MARKET_LOCATIONS[i%len(MARKET_LOCATIONS)],cat,phone,
                 (datetime.now()-timedelta(days=random.randint(30,365))).isoformat(),
                 str(random.randint(100000,999999)),True))
        for product in CATEGORIES[cat][:5]:
            wh = db_one("SELECT * FROM warehouse WHERE name=%s",(product,))
            if not wh: continue
            max_s = random.randint(50,200)
            curr = random.randint(5,max_s)
            hist = json.dumps([{"date":(datetime.now()-timedelta(days=6-j)).strftime("%Y-%m-%d"),
                                 "stock":random.randint(10,180),"sales":random.randint(5,50)} for j in range(7)])
            db_exec("""INSERT INTO products (id,hawker_id,name,category,current_stock,max_stock,
                       min_threshold,unit,price_ksh,last_restocked,sales_today,history)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (str(uuid.uuid4())[:6],hid,product,cat,curr,max_s,int(max_s*0.2),
                     wh["unit"],wh["price_ksh"],(datetime.now()-timedelta(days=random.randint(0,5))).isoformat(),
                     random.randint(0,30),hist))
    _refresh_alerts()

def login_required(f):
    @wraps(f)
    def d(*a,**kw):
        if "user" not in session: return jsonify({"error":"unauthorized"}),401
        return f(*a,**kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a,**kw):
        if "user" not in session or session["user"]["role"]!="admin": return jsonify({"error":"admin only"}),403
        return f(*a,**kw)
    return d

@app.route("/")
def index():
    if "user" not in session: return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login")
def login():
    if "user" in session: return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

@app.route("/logout-api", methods=["POST"])
def logout_api():
    session.clear(); return jsonify({"success":True})

@app.route("/api/login", methods=["POST"])
def api_login():
    body = request.json
    username = body.get("username","").strip().lower()
    password = body.get("password","").strip()
    user = db_one("SELECT * FROM users WHERE username=%s AND password=%s",(username,password))
    if not user: return jsonify({"error":"Jina au neno siri si sahihi — Wrong username or password"}),401
    session.clear(); session.permanent=True
    session["user"]={"id":user["id"],"username":username,"role":user["role"],"name":user["name"]}
    return jsonify({"success":True,"role":user["role"],"name":user["name"]})

@app.route("/api/me")
@login_required
def api_me(): return jsonify(session["user"])

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    role = session["user"]["role"]
    if role=="admin":
        hawkers = db_query("SELECT id FROM hawkers")
        wh = db_query("SELECT quantity,price_ksh FROM warehouse")
        return jsonify({
            "total_hawkers": len(hawkers),
            "total_products": db_one("SELECT COUNT(*) as c FROM products")["c"],
            "low_stock_count": db_one("SELECT COUNT(*) as c FROM products WHERE current_stock<=min_threshold")["c"],
            "critical_count": db_one("SELECT COUNT(*) as c FROM products WHERE current_stock<=min_threshold*0.5")["c"],
            "total_sales_today": db_one("SELECT COALESCE(SUM(sales_today),0) as s FROM products")["s"],
            "active_alerts": db_one("SELECT COUNT(*) as c FROM alerts WHERE read=FALSE")["c"],
            "warehouse_items": len(wh),
            "warehouse_value": round(sum(w["quantity"]*w["price_ksh"] for w in wh),2),
            "last_updated": datetime.now().isoformat()
        })
    else:
        hawker = db_one("SELECT * FROM hawkers WHERE id=%s",(session["user"]["id"],))
        if not hawker: return jsonify({"error":"Hawker not found"}),404
        products = db_query("SELECT * FROM products WHERE hawker_id=%s",(hawker["id"],))
        hot = [(r["name"],r["total"]) for r in db_query("SELECT name,SUM(sales_today) as total FROM products GROUP BY name ORDER BY total DESC LIMIT 5")]
        hawker["products"]=products
        return jsonify({
            "hawker":hawker,
            "low_stock":sum(1 for p in products if p["current_stock"]<=p["min_threshold"]),
            "total_sales":sum(p["sales_today"] for p in products),
            "product_count":len(products),
            "hot_products":hot,
            "active_alerts":db_one("SELECT COUNT(*) as c FROM alerts WHERE hawker_id=%s AND read=FALSE",(hawker["id"],))["c"]
        })

@app.route("/api/hawkers")
@login_required
def get_hawkers():
    hawkers = db_query("SELECT * FROM hawkers")
    for h in hawkers: h["products"]=db_query("SELECT * FROM products WHERE hawker_id=%s",(h["id"],))
    return jsonify(hawkers)

@app.route("/api/hawkers", methods=["POST"])
@admin_required
def add_hawker():
    body=request.json; username=body["username"].strip().lower()
    if db_one("SELECT id FROM users WHERE username=%s",(username,)): return jsonify({"error":"Username already exists"}),400
    hid=str(uuid.uuid4())[:8]; phone=body.get("phone",""); cat=body.get("category","Mboga")
    db_exec("INSERT INTO users (id,username,password,role,name,phone) VALUES (%s,%s,%s,%s,%s,%s)",(hid,username,body["password"],"hawker",body["name"],phone))
    db_exec("INSERT INTO hawkers (id,name,username,location,category,phone,joined,mpesa_till,active) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(hid,body["name"],username,body.get("location","Nairobi"),cat,phone,datetime.now().isoformat(),body.get("mpesa_till",""),True))
    return jsonify({"success":True,"hawker":db_one("SELECT * FROM hawkers WHERE id=%s",(hid,))})

@app.route("/api/hawkers/<hawker_id>", methods=["DELETE"])
@admin_required
def delete_hawker(hawker_id):
    if not db_one("SELECT id FROM hawkers WHERE id=%s",(hawker_id,)): return jsonify({"error":"Not found"}),404
    db_exec("DELETE FROM products WHERE hawker_id=%s",(hawker_id,))
    db_exec("DELETE FROM alerts WHERE hawker_id=%s",(hawker_id,))
    db_exec("DELETE FROM hawkers WHERE id=%s",(hawker_id,))
    db_exec("DELETE FROM users WHERE id=%s",(hawker_id,))
    return jsonify({"success":True})

@app.route("/api/hawkers/<hawker_id>")
@login_required
def get_hawker(hawker_id):
    h=db_one("SELECT * FROM hawkers WHERE id=%s",(hawker_id,))
    if not h: return jsonify({"error":"Not found"}),404
    h["products"]=db_query("SELECT * FROM products WHERE hawker_id=%s",(hawker_id,))
    return jsonify(h)

@app.route("/api/distribute", methods=["POST"])
@admin_required
def distribute_stock():
    body=request.json
    h=db_one("SELECT * FROM hawkers WHERE id=%s",(body["hawker_id"],))
    if not h: return jsonify({"error":"Hawker not found"}),404
    pname=body["product_name"]; qty=int(body["quantity"])
    wh=db_one("SELECT * FROM warehouse WHERE name=%s",(pname,))
    if not wh: return jsonify({"error":"Product not in warehouse"}),404
    if wh["quantity"]<qty: return jsonify({"error":f"Not enough stock. Available: {wh['quantity']}"}),400
    db_exec("UPDATE warehouse SET quantity=quantity-%s WHERE name=%s",(qty,pname))
    existing=db_one("SELECT * FROM products WHERE hawker_id=%s AND name=%s",(body["hawker_id"],pname))
    if existing:
        db_exec("UPDATE products SET current_stock=%s,last_restocked=%s WHERE id=%s",(min(existing["current_stock"]+qty,existing["max_stock"]),datetime.now().isoformat(),existing["id"]))
    else:
        max_s=qty*2; hist=json.dumps([{"date":(datetime.now()-timedelta(days=6-i)).strftime("%Y-%m-%d"),"stock":random.randint(10,180),"sales":random.randint(5,50)} for i in range(7)])
        db_exec("INSERT INTO products (id,hawker_id,name,category,current_stock,max_stock,min_threshold,unit,price_ksh,last_restocked,sales_today,history) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid.uuid4())[:6],body["hawker_id"],pname,wh["category"],qty,max_s,int(max_s*0.2),wh["unit"],wh["price_ksh"],datetime.now().isoformat(),0,hist))
    _refresh_alerts()
    return jsonify({"success":True,"warehouse_remaining":db_one("SELECT quantity FROM warehouse WHERE name=%s",(pname,))["quantity"]})

@app.route("/api/warehouse")
@admin_required
def get_warehouse(): return jsonify(db_query("SELECT * FROM warehouse ORDER BY category,name"))

@app.route("/api/warehouse", methods=["POST"])
@admin_required
def add_warehouse_stock():
    body=request.json; name=body["name"].strip()
    if db_one("SELECT name FROM warehouse WHERE name=%s",(name,)):
        db_exec("UPDATE warehouse SET quantity=quantity+%s WHERE name=%s",(int(body["quantity"]),name))
    else:
        db_exec("INSERT INTO warehouse (name,category,quantity,unit,price_ksh,reorder_level) VALUES (%s,%s,%s,%s,%s,%s)",(name,body.get("category","Mboga"),int(body["quantity"]),body.get("unit","kg"),float(body.get("price_ksh",50)),int(body.get("reorder_level",100))))
    return jsonify({"success":True})

@app.route("/api/warehouse/<product_name>", methods=["DELETE"])
@admin_required
def delete_warehouse_item(product_name):
    decoded=product_name.replace("_"," ")
    if db_one("SELECT name FROM warehouse WHERE name=%s",(decoded,)):
        db_exec("DELETE FROM warehouse WHERE name=%s",(decoded,)); return jsonify({"success":True})
    return jsonify({"error":"Not found"}),404

@app.route("/api/hawker/update_stock", methods=["POST"])
@login_required
def hawker_update_stock():
    if session["user"]["role"]!="hawker": return jsonify({"error":"Hawkers only"}),403
    body=request.json
    if not db_one("SELECT id FROM hawkers WHERE id=%s",(session["user"]["id"],)): return jsonify({"error":"Not found"}),404
    p=db_one("SELECT * FROM products WHERE id=%s AND hawker_id=%s",(body["product_id"],session["user"]["id"]))
    if not p: return jsonify({"error":"Product not found"}),404
    if body.get("action")=="sold":
        sold=min(int(body["quantity"]),p["current_stock"])
        db_exec("UPDATE products SET current_stock=current_stock-%s,sales_today=sales_today+%s WHERE id=%s",(sold,sold,p["id"]))
    else:
        db_exec("UPDATE products SET current_stock=%s WHERE id=%s",(int(body["quantity"]),p["id"]))
    _refresh_alerts()
    return jsonify({"success":True,"product":db_one("SELECT * FROM products WHERE id=%s",(p["id"],))})

@app.route("/api/market_pulse")
@login_required
def market_pulse():
    pulse={}
    for h in db_query("SELECT id,category FROM hawkers"):
        cat=h["category"]
        if cat not in pulse: pulse[cat]={"total_products":0,"low_stock":0,"hawkers":0,"total_sales":0}
        pulse[cat]["hawkers"]+=1
        for p in db_query("SELECT * FROM products WHERE hawker_id=%s",(h["id"],)):
            pulse[cat]["total_products"]+=1; pulse[cat]["total_sales"]+=p["sales_today"]
            if p["current_stock"]<=p["min_threshold"]: pulse[cat]["low_stock"]+=1
    hot=[(r["name"],r["total"]) for r in db_query("SELECT name,SUM(sales_today) as total FROM products GROUP BY name ORDER BY total DESC LIMIT 10")]
    return jsonify({"categories":pulse,"hot_products":hot})

@app.route("/api/alerts")
@login_required
def get_alerts():
    if session["user"]["role"]=="admin": return jsonify(db_query("SELECT * FROM alerts ORDER BY timestamp DESC"))
    return jsonify(db_query("SELECT * FROM alerts WHERE hawker_id=%s ORDER BY timestamp DESC",(session["user"]["id"],)))

@app.route("/api/alerts/read/<alert_id>", methods=["POST"])
@login_required
def mark_read(alert_id):
    db_exec("UPDATE alerts SET read=TRUE WHERE id=%s",(alert_id,)); return jsonify({"success":True})

@app.route("/api/categories")
@login_required
def get_categories(): return jsonify(CATEGORIES)

@app.route("/api/simulate_sales", methods=["POST"])
@admin_required
def simulate_sales():
    for p in db_query("SELECT * FROM products"):
        sold=random.randint(0,min(10,p["current_stock"]))
        db_exec("UPDATE products SET current_stock=current_stock-%s,sales_today=sales_today+%s WHERE id=%s",(sold,sold,p["id"]))
    _refresh_alerts(); return jsonify({"success":True})

with app.app_context():
    if DATABASE_URL:
        init_db()
        seed_db()

if __name__=="__main__":
    app.run(debug=True,port=5000)
