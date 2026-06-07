import os
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from datetime import datetime, date

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'staff',
            full_name VARCHAR(200),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            session_date DATE NOT NULL UNIQUE,
            opened_by INTEGER REFERENCES users(id),
            closed_by INTEGER REFERENCES users(id),
            status VARCHAR(20) DEFAULT 'open',
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            closed_at TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS goods (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(100),
            unit VARCHAR(50),
            unit_price NUMERIC(12,4) DEFAULT 0,
            quantity NUMERIC(12,3) DEFAULT 0,
            reorder_point NUMERIC(12,3) DEFAULT 0,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(100),
            quantity INTEGER DEFAULT 1,
            unit_price NUMERIC(10,2) DEFAULT 0,
            condition VARCHAR(50) DEFAULT 'Good',
            purchase_date DATE,
            notes TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            category VARCHAR(100),
            selling_price NUMERIC(10,2) DEFAULT 0,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id SERIAL PRIMARY KEY,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            good_id INTEGER REFERENCES goods(id) ON DELETE CASCADE,
            quantity_used NUMERIC(12,3) NOT NULL,
            unit VARCHAR(50)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            session_date DATE NOT NULL DEFAULT CURRENT_DATE,
            recipe_id INTEGER REFERENCES recipes(id),
            recipe_name VARCHAR(200),
            quantity INTEGER DEFAULT 1,
            unit_price NUMERIC(10,2) DEFAULT 0,
            discount NUMERIC(10,2) DEFAULT 0,
            total_price NUMERIC(10,2) DEFAULT 0,
            comment TEXT,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS waste_log (
            id SERIAL PRIMARY KEY,
            session_date DATE NOT NULL DEFAULT CURRENT_DATE,
            item_type VARCHAR(20) DEFAULT 'good',
            good_id INTEGER REFERENCES goods(id),
            recipe_id INTEGER REFERENCES recipes(id),
            item_name VARCHAR(200),
            quantity NUMERIC(12,3),
            unit VARCHAR(50),
            reason VARCHAR(200),
            comment TEXT,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            session_date DATE NOT NULL DEFAULT CURRENT_DATE,
            description VARCHAR(300) NOT NULL,
            category VARCHAR(100),
            amount NUMERIC(10,2) NOT NULL,
            payment_method VARCHAR(50) DEFAULT 'Cash',
            comment TEXT,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS stock_adjustments (
            id SERIAL PRIMARY KEY,
            session_date DATE NOT NULL DEFAULT CURRENT_DATE,
            good_id INTEGER REFERENCES goods(id),
            adjustment_type VARCHAR(50),
            quantity NUMERIC(12,3),
            previous_qty NUMERIC(12,3),
            new_qty NUMERIC(12,3),
            reason TEXT,
            user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── Schema migrations for existing installs ──────────────────────────────
    # Upgrade unit_price to higher precision if still NUMERIC(10,2)
    cur.execute("""
        SELECT data_type, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_name='goods' AND column_name='unit_price'
    """)
    col_info = cur.fetchone()
    if col_info and col_info["numeric_scale"] is not None and int(col_info["numeric_scale"]) < 4:
        cur.execute("ALTER TABLE goods ALTER COLUMN unit_price TYPE NUMERIC(12,4)")

    # Add discount column to sales if missing
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='sales' AND column_name='discount'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE sales ADD COLUMN discount NUMERIC(10,2) DEFAULT 0")

    # Seed admin user if not exists
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        pw = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s,%s,%s,%s)",
            ("admin", pw, "admin", "Admin User")
        )
        pw2 = bcrypt.hashpw("staff123".encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s,%s,%s,%s)",
            ("staff", pw2, "staff", "Staff User")
        )

    conn.commit()
    cur.close()
    conn.close()
    _seed_data()


def _seed_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM goods")
    row = cur.fetchone()
    if row["cnt"] > 0:
        cur.close()
        conn.close()
        return

    goods_data = [
        # Coffee Ingredients
        ("Light Roast Beans", "Coffee", "g", 0.08, 5780, 1000),
        ("Dark Roast Beans", "Coffee", "g", 0.07, 10740, 1000),
        ("Espresso Beans (Medium)", "Coffee", "g", 0.09, 9000, 1000),
        ("Decaf Beans", "Coffee", "g", 0.10, 2000, 500),
        # Milk & Dairy
        ("Fresh Milk", "Dairy", "ml", 0.003, 10000, 2000),
        ("Oat Milk", "Dairy", "ml", 0.006, 5000, 1000),
        ("Almond Milk", "Dairy", "ml", 0.007, 3000, 500),
        ("Soy Milk", "Dairy", "ml", 0.005, 3000, 500),
        ("Heavy Cream", "Dairy", "ml", 0.008, 2000, 500),
        ("Whipped Cream (can)", "Dairy", "ml", 0.015, 1500, 300),
        # Syrups & Flavorings
        ("Vanilla Syrup", "Syrup", "ml", 0.02, 2000, 500),
        ("Caramel Syrup", "Syrup", "ml", 0.02, 2000, 500),
        ("Hazelnut Syrup", "Syrup", "ml", 0.02, 1500, 500),
        ("Chocolate Sauce", "Syrup", "ml", 0.025, 1500, 300),
        ("Brown Sugar Syrup", "Syrup", "ml", 0.018, 2000, 500),
        ("Matcha Powder", "Powder", "g", 0.15, 1000, 200),
        ("Cocoa Powder", "Powder", "g", 0.05, 1000, 200),
        ("Cinnamon Powder", "Powder", "g", 0.03, 500, 100),
        ("Vanilla Powder", "Powder", "g", 0.12, 500, 100),
        # Sugar
        ("White Sugar", "Sweetener", "g", 0.002, 5000, 1000),
        ("Brown Sugar", "Sweetener", "g", 0.003, 3000, 500),
        ("Honey", "Sweetener", "ml", 0.025, 1000, 200),
        ("Stevia", "Sweetener", "g", 0.10, 500, 100),
        # Tea
        ("Black Tea Bags", "Tea", "pcs", 0.15, 200, 50),
        ("Green Tea Bags", "Tea", "pcs", 0.18, 100, 30),
        ("Chamomile Tea Bags", "Tea", "pcs", 0.20, 100, 30),
        ("Earl Grey Tea Bags", "Tea", "pcs", 0.18, 100, 30),
        # Food items
        ("Croissant", "Bakery", "pcs", 1.50, 50, 10),
        ("Muffin", "Bakery", "pcs", 1.20, 50, 10),
        ("Sandwich Bread", "Bakery", "pcs", 0.30, 100, 20),
        ("Cheese Slices", "Food", "pcs", 0.50, 100, 20),
        ("Butter", "Food", "g", 0.01, 1000, 200),
        ("Eggs", "Food", "pcs", 0.25, 100, 20),
        # Ice & Water
        ("Ice Cubes", "Beverage", "g", 0.001, 10000, 2000),
        ("Still Water (bottle)", "Beverage", "pcs", 0.50, 100, 24),
        ("Sparkling Water (bottle)", "Beverage", "pcs", 0.75, 50, 12),
        # Cups & Packaging
        ("Paper Cups 8oz", "Packaging", "pcs", 0.10, 500, 100),
        ("Paper Cups 12oz", "Packaging", "pcs", 0.12, 500, 100),
        ("Paper Cups 16oz", "Packaging", "pcs", 0.15, 300, 100),
        ("Cup Lids", "Packaging", "pcs", 0.05, 1000, 200),
        ("Paper Bags", "Packaging", "pcs", 0.08, 300, 50),
        ("Napkins", "Packaging", "pcs", 0.01, 1000, 200),
        ("Straws (paper)", "Packaging", "pcs", 0.03, 500, 100),
        ("Coffee Sleeves", "Packaging", "pcs", 0.05, 500, 100),
        # Cleaning
        ("Dish Soap", "Cleaning", "ml", 0.005, 2000, 500),
        ("Sanitizer", "Cleaning", "ml", 0.008, 1000, 200),
        ("Paper Towels", "Cleaning", "rolls", 1.50, 20, 5),
        ("Trash Bags", "Cleaning", "pcs", 0.20, 50, 10),
    ]

    for name, cat, unit, price, qty, reorder in goods_data:
        cur.execute(
            "INSERT INTO goods (name, category, unit, unit_price, quantity, reorder_point) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, cat, unit, price, qty, reorder)
        )

    equipment_data = [
        ("Espresso Machine", "Coffee Equipment", 1, 2500.00, "Good"),
        ("Coffee Grinder (Commercial)", "Coffee Equipment", 2, 800.00, "Good"),
        ("Milk Frother/Steam Wand", "Coffee Equipment", 1, 150.00, "Good"),
        ("Pour Over Stand", "Coffee Equipment", 2, 45.00, "Good"),
        ("French Press", "Coffee Equipment", 3, 35.00, "Good"),
        ("Cold Brew Tower", "Coffee Equipment", 1, 350.00, "Good"),
        ("Blender (Commercial)", "Coffee Equipment", 1, 400.00, "Good"),
        ("Coffee Scale (0.1g)", "Coffee Equipment", 2, 60.00, "Good"),
        ("Kettle (Gooseneck)", "Coffee Equipment", 2, 85.00, "Good"),
        ("Refrigerator", "Kitchen", 2, 1200.00, "Good"),
        ("Display Case", "Kitchen", 1, 600.00, "Good"),
        ("Microwave", "Kitchen", 1, 200.00, "Good"),
        ("Ice Maker", "Kitchen", 1, 500.00, "Good"),
        ("POS System", "Technology", 1, 800.00, "Good"),
        ("Cash Register/Drawer", "Technology", 1, 250.00, "Good"),
        ("Receipt Printer", "Technology", 1, 180.00, "Good"),
        ("WiFi Router", "Technology", 1, 120.00, "Good"),
        ("Security Camera", "Technology", 4, 150.00, "Good"),
        ("Air Conditioner", "Furniture", 2, 1500.00, "Good"),
        ("Tables", "Furniture", 8, 120.00, "Good"),
        ("Chairs", "Furniture", 32, 45.00, "Good"),
        ("Bar Stools", "Furniture", 6, 60.00, "Good"),
        ("Counter Display", "Furniture", 1, 300.00, "Good"),
        ("Menu Board (Digital)", "Furniture", 2, 400.00, "Good"),
        ("Cappuccino Cups (Set 12)", "Utensils", 12, 25.00, "Good"),
        ("Glass Mugs (Set)", "Utensils", 12, 30.00, "Good"),
        ("Tomcollin Glass 280ML", "Utensils", 24, 8.00, "Good"),
        ("SS Pitcher 650ML", "Utensils", 2, 15.00, "Good"),
        ("Tamper", "Coffee Equipment", 2, 30.00, "Good"),
        ("Portafilter", "Coffee Equipment", 2, 80.00, "Good"),
        ("Fire Extinguisher", "Safety", 2, 80.00, "Good"),
        ("First Aid Kit", "Safety", 1, 40.00, "Good"),
    ]

    for name, cat, qty, price, cond in equipment_data:
        cur.execute(
            "INSERT INTO equipment (name, category, quantity, unit_price, condition) VALUES (%s,%s,%s,%s,%s)",
            (name, cat, qty, price, cond)
        )

    conn.commit()
    cur.close()
    conn.close()
    _seed_recipes()


def _seed_recipes():
    conn = get_conn()
    cur = conn.cursor()

    def get_good_id(name):
        cur.execute("SELECT id FROM goods WHERE name = %s", (name,))
        r = cur.fetchone()
        return r["id"] if r else None

    recipes_data = [
        ("Espresso", "Coffee", 3.50, [("Espresso Beans (Medium)", 18, "g")]),
        ("Double Espresso", "Coffee", 5.00, [("Espresso Beans (Medium)", 36, "g")]),
        ("Americano", "Coffee", 4.00, [("Espresso Beans (Medium)", 18, "g")]),
        ("Cappuccino", "Coffee", 5.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 120, "ml"),
        ]),
        ("Latte", "Coffee", 5.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 200, "ml"),
        ]),
        ("Flat White", "Coffee", 5.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 120, "ml"),
        ]),
        ("Macchiato", "Coffee", 5.00, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 30, "ml"),
        ]),
        ("Mocha", "Coffee", 6.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 150, "ml"),
            ("Chocolate Sauce", 20, "ml"),
            ("Whipped Cream (can)", 30, "ml"),
        ]),
        ("Caramel Latte", "Coffee", 6.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 200, "ml"),
            ("Caramel Syrup", 20, "ml"),
        ]),
        ("Vanilla Latte", "Coffee", 6.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 200, "ml"),
            ("Vanilla Syrup", 20, "ml"),
        ]),
        ("Hazelnut Latte", "Coffee", 6.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 200, "ml"),
            ("Hazelnut Syrup", 20, "ml"),
        ]),
        ("Iced Latte", "Cold Coffee", 6.00, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 200, "ml"),
            ("Ice Cubes", 100, "g"),
        ]),
        ("Iced Americano", "Cold Coffee", 4.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Ice Cubes", 150, "g"),
        ]),
        ("Iced Mocha", "Cold Coffee", 7.00, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Fresh Milk", 150, "ml"),
            ("Chocolate Sauce", 20, "ml"),
            ("Ice Cubes", 100, "g"),
            ("Whipped Cream (can)", 30, "ml"),
        ]),
        ("Cold Brew", "Cold Coffee", 6.00, [
            ("Dark Roast Beans", 30, "g"),
            ("Ice Cubes", 100, "g"),
        ]),
        ("Matcha Latte", "Specialty", 6.50, [
            ("Matcha Powder", 5, "g"),
            ("Fresh Milk", 200, "ml"),
            ("Honey", 10, "ml"),
        ]),
        ("Hot Chocolate", "Specialty", 6.00, [
            ("Chocolate Sauce", 30, "ml"),
            ("Fresh Milk", 200, "ml"),
            ("Whipped Cream (can)", 30, "ml"),
        ]),
        ("Chai Latte", "Tea", 5.50, [
            ("Black Tea Bags", 2, "pcs"),
            ("Fresh Milk", 150, "ml"),
            ("Brown Sugar", 10, "g"),
            ("Cinnamon Powder", 2, "g"),
        ]),
        ("Green Tea Latte", "Tea", 5.50, [
            ("Matcha Powder", 4, "g"),
            ("Fresh Milk", 180, "ml"),
            ("Honey", 10, "ml"),
        ]),
        ("English Breakfast Tea", "Tea", 3.50, [("Black Tea Bags", 1, "pcs")]),
        ("Oat Milk Latte", "Specialty", 6.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Oat Milk", 200, "ml"),
        ]),
        ("Almond Milk Latte", "Specialty", 6.50, [
            ("Espresso Beans (Medium)", 18, "g"),
            ("Almond Milk", 200, "ml"),
        ]),
        ("Brown Sugar Shaken Espresso", "Cold Coffee", 7.00, [
            ("Espresso Beans (Medium)", 36, "g"),
            ("Brown Sugar Syrup", 30, "ml"),
            ("Ice Cubes", 150, "g"),
            ("Fresh Milk", 100, "ml"),
        ]),
        ("Croissant", "Food", 3.50, [("Croissant", 1, "pcs")]),
        ("Muffin", "Food", 3.00, [("Muffin", 1, "pcs")]),
        ("Bottled Water", "Beverage", 1.50, [("Still Water (bottle)", 1, "pcs")]),
        ("Sparkling Water", "Beverage", 2.00, [("Sparkling Water (bottle)", 1, "pcs")]),
    ]

    for recipe_name, cat, price, ingredients in recipes_data:
        cur.execute(
            "INSERT INTO recipes (name, category, selling_price) VALUES (%s,%s,%s) RETURNING id",
            (recipe_name, cat, price)
        )
        recipe_id = cur.fetchone()["id"]
        for ing_name, qty, unit in ingredients:
            good_id = get_good_id(ing_name)
            if good_id:
                cur.execute(
                    "INSERT INTO recipe_ingredients (recipe_id, good_id, quantity_used, unit) VALUES (%s,%s,%s,%s)",
                    (recipe_id, good_id, qty, unit)
                )

    conn.commit()
    cur.close()
    conn.close()


# ── AUTH ─────────────────────────────────────────────────────────────────────

def verify_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return dict(user)
        return None
    finally:
        cur.close()
        conn.close()


def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, full_name, role, created_at FROM users ORDER BY id")
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def create_user(username, password, role, full_name):
    conn = get_conn()
    cur = conn.cursor()
    try:
        pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (%s,%s,%s,%s) RETURNING id",
            (username, pw, role, full_name)
        )
        uid = cur.fetchone()["id"]
        conn.commit()
        return uid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_user_password(user_id, new_password):
    conn = get_conn()
    cur = conn.cursor()
    try:
        pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (pw, user_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id=%s AND username != 'admin'", (user_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ── SESSIONS ─────────────────────────────────────────────────────────────────

def get_or_create_session(today, user_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM sessions WHERE session_date = %s", (today,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO sessions (session_date, opened_by, status) VALUES (%s,%s,'open') RETURNING *",
                (today, user_id)
            )
            row = cur.fetchone()
            conn.commit()
        return dict(row)
    finally:
        cur.close()
        conn.close()


def close_session(session_id, user_id, notes):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE sessions SET status='closed', closed_by=%s, closed_at=NOW(), notes=%s WHERE id=%s",
            (user_id, notes, session_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_sessions(limit=30):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT s.*, u1.full_name AS opened_name, u2.full_name AS closed_name
            FROM sessions s
            LEFT JOIN users u1 ON s.opened_by = u1.id
            LEFT JOIN users u2 ON s.closed_by = u2.id
            ORDER BY s.session_date DESC LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


# ── GOODS ────────────────────────────────────────────────────────────────────

def get_goods(active_only=True):
    conn = get_conn()
    cur = conn.cursor()
    try:
        q = "SELECT * FROM goods"
        if active_only:
            q += " WHERE is_active = TRUE"
        q += " ORDER BY category, name"
        cur.execute(q)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_good(good_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM goods WHERE id=%s", (good_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


def add_good(name, category, unit, unit_price, quantity, reorder_point, description=""):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO goods (name, category, unit, unit_price, quantity, reorder_point, description) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (name, category, unit, unit_price, quantity, reorder_point, description)
        )
        uid = cur.fetchone()["id"]
        conn.commit()
        return uid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_good(good_id, name, category, unit, unit_price, quantity, reorder_point, description=""):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE goods SET name=%s, category=%s, unit=%s, unit_price=%s, quantity=%s, reorder_point=%s, description=%s, updated_at=NOW() WHERE id=%s",
            (name, category, unit, unit_price, quantity, reorder_point, description, good_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def restock_good(good_id, added_qty, user_id, reason="Restock"):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT quantity FROM goods WHERE id=%s", (good_id,))
        row = cur.fetchone()
        prev_qty = float(row["quantity"])
        new_qty = prev_qty + added_qty
        cur.execute("UPDATE goods SET quantity=%s, updated_at=NOW() WHERE id=%s", (new_qty, good_id))
        cur.execute(
            "INSERT INTO stock_adjustments (good_id, adjustment_type, quantity, previous_qty, new_qty, reason, user_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (good_id, "restock", added_qty, prev_qty, new_qty, reason, user_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def deactivate_good(good_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE goods SET is_active=FALSE WHERE id=%s", (good_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_restock_alerts():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT g.id, g.name, g.category, g.quantity, g.unit, g.reorder_point,
                   ri.quantity_used,
                   r.name AS recipe_name,
                   FLOOR(g.quantity / NULLIF(ri.quantity_used, 0)) AS possible_drinks
            FROM goods g
            JOIN recipe_ingredients ri ON ri.good_id = g.id
            JOIN recipes r ON r.id = ri.recipe_id AND r.is_active = TRUE
            WHERE g.is_active = TRUE
              AND (g.quantity / NULLIF(ri.quantity_used, 0)) < 10
            ORDER BY possible_drinks ASC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_low_stock_goods():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT * FROM goods
            WHERE is_active = TRUE AND reorder_point > 0 AND quantity <= reorder_point
            ORDER BY (quantity / NULLIF(reorder_point, 1)) ASC
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_revenue_trend(days=7):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT session_date, COALESCE(SUM(total_price), 0) AS revenue
            FROM sales
            WHERE session_date >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY session_date
            ORDER BY session_date
        """ % int(days))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


# ── EQUIPMENT ────────────────────────────────────────────────────────────────

def get_equipment():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM equipment WHERE is_active=TRUE ORDER BY category, name")
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def add_equipment(name, category, quantity, unit_price, condition, purchase_date, notes):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO equipment (name, category, quantity, unit_price, condition, purchase_date, notes) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (name, category, quantity, unit_price, condition, purchase_date or None, notes)
        )
        uid = cur.fetchone()["id"]
        conn.commit()
        return uid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_equipment(eq_id, name, category, quantity, unit_price, condition, notes):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE equipment SET name=%s, category=%s, quantity=%s, unit_price=%s, condition=%s, notes=%s, updated_at=NOW() WHERE id=%s",
            (name, category, quantity, unit_price, condition, notes, eq_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def deactivate_equipment(eq_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE equipment SET is_active=FALSE WHERE id=%s", (eq_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ── RECIPES ─────────────────────────────────────────────────────────────────

def get_recipes(active_only=True):
    conn = get_conn()
    cur = conn.cursor()
    try:
        q = "SELECT * FROM recipes"
        if active_only:
            q += " WHERE is_active=TRUE"
        q += " ORDER BY category, name"
        cur.execute(q)
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_recipe(recipe_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM recipes WHERE id=%s", (recipe_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
        conn.close()


def get_recipe_ingredients(recipe_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT ri.*, g.name AS good_name, g.unit AS good_unit, g.unit_price
            FROM recipe_ingredients ri
            JOIN goods g ON g.id = ri.good_id
            WHERE ri.recipe_id = %s
        """, (recipe_id,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def add_recipe(name, category, selling_price, description, ingredients):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO recipes (name, category, selling_price, description) VALUES (%s,%s,%s,%s) RETURNING id",
            (name, category, selling_price, description)
        )
        recipe_id = cur.fetchone()["id"]
        for ing in ingredients:
            cur.execute(
                "INSERT INTO recipe_ingredients (recipe_id, good_id, quantity_used, unit) VALUES (%s,%s,%s,%s)",
                (recipe_id, ing["good_id"], ing["quantity"], ing["unit"])
            )
        conn.commit()
        return recipe_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_recipe(recipe_id, name, category, selling_price, description, ingredients):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE recipes SET name=%s, category=%s, selling_price=%s, description=%s, updated_at=NOW() WHERE id=%s",
            (name, category, selling_price, description, recipe_id)
        )
        cur.execute("DELETE FROM recipe_ingredients WHERE recipe_id=%s", (recipe_id,))
        for ing in ingredients:
            cur.execute(
                "INSERT INTO recipe_ingredients (recipe_id, good_id, quantity_used, unit) VALUES (%s,%s,%s,%s)",
                (recipe_id, ing["good_id"], ing["quantity"], ing["unit"])
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def deactivate_recipe(recipe_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE recipes SET is_active=FALSE WHERE id=%s", (recipe_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_recipe_cost(recipe_id):
    ingredients = get_recipe_ingredients(recipe_id)
    return sum(float(i["quantity_used"]) * float(i["unit_price"]) for i in ingredients)


# ── SALES ───────────────────────────────────────────────────────────────────

def add_sale(session_date, recipe_id, recipe_name, quantity, unit_price, comment, user_id, discount=0):
    conn = get_conn()
    cur = conn.cursor()
    try:
        subtotal = float(unit_price) * int(quantity)
        discount = float(discount or 0)
        total = max(0.0, subtotal - discount)
        cur.execute(
            """INSERT INTO sales (session_date, recipe_id, recipe_name, quantity, unit_price, discount, total_price, comment, user_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (session_date, recipe_id, recipe_name, quantity, unit_price, discount, total, comment, user_id)
        )
        sale_id = cur.fetchone()["id"]
        # Deduct stock for each ingredient
        ingredients = get_recipe_ingredients(recipe_id)
        for ing in ingredients:
            used = float(ing["quantity_used"]) * int(quantity)
            cur.execute(
                "UPDATE goods SET quantity = GREATEST(0, quantity - %s), updated_at=NOW() WHERE id=%s",
                (used, ing["good_id"])
            )
        conn.commit()
        return sale_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_sales(session_date=None, limit=500):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if session_date:
            cur.execute("""
                SELECT s.*, u.full_name AS staff_name
                FROM sales s LEFT JOIN users u ON u.id = s.user_id
                WHERE s.session_date = %s ORDER BY s.created_at DESC LIMIT %s
            """, (session_date, limit))
        else:
            cur.execute("""
                SELECT s.*, u.full_name AS staff_name
                FROM sales s LEFT JOIN users u ON u.id = s.user_id
                ORDER BY s.created_at DESC LIMIT %s
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def update_sale(sale_id, quantity, unit_price, comment, discount=0):
    conn = get_conn()
    cur = conn.cursor()
    try:
        subtotal = float(unit_price) * int(quantity)
        discount = float(discount or 0)
        total = max(0.0, subtotal - discount)
        cur.execute(
            "UPDATE sales SET quantity=%s, unit_price=%s, discount=%s, total_price=%s, comment=%s, updated_at=NOW() WHERE id=%s",
            (quantity, unit_price, discount, total, comment, sale_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def delete_sale(sale_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM sales WHERE id=%s", (sale_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_daily_sales_summary(session_date):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                COUNT(*) AS total_transactions,
                COALESCE(SUM(quantity), 0) AS total_items,
                COALESCE(SUM(total_price), 0) AS total_revenue
            FROM sales WHERE session_date = %s
        """, (session_date,))
        row = dict(cur.fetchone())
        cur.execute("""
            SELECT recipe_name, SUM(quantity) AS qty, SUM(total_price) AS revenue
            FROM sales WHERE session_date = %s
            GROUP BY recipe_name ORDER BY qty DESC LIMIT 5
        """, (session_date,))
        top = [dict(r) for r in cur.fetchall()]
        return row, top
    finally:
        cur.close()
        conn.close()


# ── WASTE LOG ───────────────────────────────────────────────────────────────

def add_waste(session_date, item_type, item_id, item_name, quantity, unit, reason, comment, user_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        good_id = item_id if item_type == "good" else None
        recipe_id = item_id if item_type == "recipe" else None
        cur.execute(
            """INSERT INTO waste_log (session_date, item_type, good_id, recipe_id, item_name, quantity, unit, reason, comment, user_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (session_date, item_type, good_id, recipe_id, item_name, quantity, unit, reason, comment, user_id)
        )
        wid = cur.fetchone()["id"]
        if item_type == "good" and good_id:
            cur.execute(
                "UPDATE goods SET quantity = GREATEST(0, quantity - %s), updated_at=NOW() WHERE id=%s",
                (quantity, good_id)
            )
        conn.commit()
        return wid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_waste_log(session_date=None, limit=500):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if session_date:
            cur.execute("""
                SELECT w.*, u.full_name AS staff_name
                FROM waste_log w LEFT JOIN users u ON u.id = w.user_id
                WHERE w.session_date = %s ORDER BY w.created_at DESC LIMIT %s
            """, (session_date, limit))
        else:
            cur.execute("""
                SELECT w.*, u.full_name AS staff_name
                FROM waste_log w LEFT JOIN users u ON u.id = w.user_id
                ORDER BY w.created_at DESC LIMIT %s
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def update_waste(waste_id, quantity, unit, reason, comment):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE waste_log SET quantity=%s, unit=%s, reason=%s, comment=%s, updated_at=NOW() WHERE id=%s",
            (quantity, unit, reason, comment, waste_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def delete_waste(waste_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM waste_log WHERE id=%s", (waste_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ── EXPENSES ─────────────────────────────────────────────────────────────────

def add_expense(session_date, description, category, amount, payment_method, comment, user_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO expenses (session_date, description, category, amount, payment_method, comment, user_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (session_date, description, category, amount, payment_method, comment, user_id)
        )
        eid = cur.fetchone()["id"]
        conn.commit()
        return eid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_expenses(session_date=None, limit=500):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if session_date:
            cur.execute("""
                SELECT e.*, u.full_name AS staff_name
                FROM expenses e LEFT JOIN users u ON u.id = e.user_id
                WHERE e.session_date = %s ORDER BY e.created_at DESC LIMIT %s
            """, (session_date, limit))
        else:
            cur.execute("""
                SELECT e.*, u.full_name AS staff_name
                FROM expenses e LEFT JOIN users u ON u.id = e.user_id
                ORDER BY e.created_at DESC LIMIT %s
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def update_expense(exp_id, description, category, amount, payment_method, comment):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE expenses SET description=%s, category=%s, amount=%s, payment_method=%s, comment=%s, updated_at=NOW() WHERE id=%s",
            (description, category, amount, payment_method, comment, exp_id)
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def delete_expense(exp_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM expenses WHERE id=%s", (exp_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ── SUMMARY & REPORTS ────────────────────────────────────────────────────────

def get_daily_summary(session_date):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COALESCE(SUM(total_price),0) AS revenue FROM sales WHERE session_date=%s", (session_date,))
        revenue = float(cur.fetchone()["revenue"])
        cur.execute("SELECT COALESCE(SUM(amount),0) AS expenses FROM expenses WHERE session_date=%s", (session_date,))
        expenses = float(cur.fetchone()["expenses"])
        cur.execute("SELECT COUNT(*) AS cnt FROM waste_log WHERE session_date=%s", (session_date,))
        waste_count = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM sales WHERE session_date=%s", (session_date,))
        sales_count = cur.fetchone()["cnt"]
        return {
            "revenue": revenue,
            "expenses": expenses,
            "profit": revenue - expenses,
            "waste_count": waste_count,
            "sales_count": sales_count,
        }
    finally:
        cur.close()
        conn.close()


def get_stock_adjustments(limit=100):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT sa.*, g.name AS good_name, u.full_name AS staff_name
            FROM stock_adjustments sa
            LEFT JOIN goods g ON g.id = sa.good_id
            LEFT JOIN users u ON u.id = sa.user_id
            ORDER BY sa.created_at DESC LIMIT %s
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def get_report_data(from_date, to_date):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT session_date, COALESCE(SUM(total_price),0) AS revenue
            FROM sales
            WHERE session_date BETWEEN %s AND %s
            GROUP BY session_date ORDER BY session_date
        """, (from_date, to_date))
        rev_data = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT session_date, COALESCE(SUM(amount),0) AS expenses
            FROM expenses
            WHERE session_date BETWEEN %s AND %s
            GROUP BY session_date ORDER BY session_date
        """, (from_date, to_date))
        exp_data = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT recipe_name, SUM(quantity) AS qty, SUM(total_price) AS revenue
            FROM sales WHERE session_date BETWEEN %s AND %s
            GROUP BY recipe_name ORDER BY qty DESC LIMIT 10
        """, (from_date, to_date))
        top_items = [dict(r) for r in cur.fetchall()]

        return rev_data, exp_data, top_items
    finally:
        cur.close()
        conn.close()
