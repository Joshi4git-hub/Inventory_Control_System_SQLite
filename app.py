from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
import sqlite3
import bcrypt
import os

app = Flask(__name__)
app.secret_key = "inventory_secret_key_2024"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "inventory.db")

# ── Database Connection ──
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ── Create Tables ──
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL UNIQUE,
            email    TEXT    NOT NULL UNIQUE,
            password BLOB    NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            quantity INTEGER NOT NULL,
            price    REAL    NOT NULL,
            supplier TEXT    NOT NULL,
            user_id  INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL,
            user_id      INTEGER NOT NULL,
            order_qty    INTEGER NOT NULL,
            order_date   TEXT    NOT NULL,
            arrival_date TEXT    NOT NULL,
            status       TEXT    NOT NULL CHECK(status IN ('pending', 'completed')),
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()

# ── Currency Formatting ──
def format_inr(value):
    if value is None:
        return ""
    try:
        value = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        try:
            value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return value

    sign = "-" if value < 0 else ""
    value = abs(value)
    value = value.quantize(Decimal("0.01"))
    integer_part, _, fraction = f"{value:.2f}".partition(".")

    if len(integer_part) <= 3:
        grouped = integer_part
    else:
        grouped = integer_part[-3:]
        prefix = integer_part[:-3]
        while len(prefix) > 2:
            grouped = prefix[-2:] + "," + grouped
            prefix = prefix[:-2]
        if prefix:
            grouped = prefix + "," + grouped

    return f"{sign}{grouped}.{fraction}"

app.jinja_env.filters["inr"] = format_inr

# ── Login Required ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            flash("Please login to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ── REGISTER ──
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("register"))

        conn = get_db()
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing:
            flash("Username or email already registered.", "error")
            conn.close()
            return redirect(url_for("register"))

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed)
        )
        conn.commit()
        conn.close()

        flash("Account created! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# ── LOGIN ──
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            session["user"]    = user["username"]
            session["user_id"] = user["id"]
            flash(f'Welcome back, {user["username"]}!', "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

# ── LOGOUT ──
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

# ── HOME ──
@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    conn    = get_db()

    total_products = conn.execute(
        "SELECT COUNT(*) FROM products WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    total_quantity = conn.execute(
        "SELECT SUM(quantity) FROM products WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0] or 0

    low_stock = conn.execute(
        "SELECT * FROM products WHERE user_id = ? AND quantity <= 15 LIMIT 5",
        (user_id,)
    ).fetchall()

    recent = conn.execute(
        "SELECT * FROM products WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_products=total_products,
        total_quantity=total_quantity,
        low_stock=low_stock,
        recent=recent,
    )

# ── ADD PRODUCT ──
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        quantity = request.form.get("quantity", "0").strip()
        price    = request.form.get("price", "0").strip()
        supplier = request.form.get("supplier", "").strip()

        if not name or not supplier:
            flash("Product name and supplier are required.", "error")
            return redirect(url_for("add_product"))

        price = price.replace(",", "").replace("₹", "").strip()
        try:
            quantity = int(quantity)
            price    = float(price)
        except ValueError:
            flash("Quantity must be an integer and Price must be a number.", "error")
            return redirect(url_for("add_product"))

        conn = get_db()
        conn.execute(
            "INSERT INTO products (name, quantity, price, supplier, user_id) VALUES (?, ?, ?, ?, ?)",
            (name, quantity, price, supplier, session["user_id"])
        )
        conn.commit()
        conn.close()

        flash(f'"{name}" added successfully!', "success")
        return redirect(url_for("view_products"))

    return render_template("add_product.html")

# ── VIEW PRODUCTS ──
@app.route("/view")
@login_required
def view_products():
    user_id = session["user_id"]
    search  = request.args.get("q", "").strip()
    low_stock = request.args.get("low_stock", "").strip().lower() == "on"
    price_sort = request.args.get("price_sort", "").strip()
    qty_sort = request.args.get("qty_sort", "").strip()
    
    conn = get_db()

    # Build query
    query = "SELECT * FROM products WHERE user_id = ?"
    params = [user_id]

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if low_stock:
        query += " AND quantity <= 15"

    # Add sorting
    order_by = "name ASC"
    if price_sort == "high_to_low":
        order_by = "price DESC"
    elif price_sort == "low_to_high":
        order_by = "price ASC"
    elif qty_sort == "high_to_low":
        order_by = "quantity DESC"
    elif qty_sort == "low_to_high":
        order_by = "quantity ASC"

    query += f" ORDER BY {order_by}"
    products = conn.execute(query, params).fetchall()

    conn.close()
    return render_template(
        "view_products.html",
        products=products,
        search=search,
        low_stock=low_stock,
        price_sort=price_sort,
        qty_sort=qty_sort
    )

# ── SHIPMENTS ──
@app.route("/shipments")
@login_required
def shipments():
    user_id = session["user_id"]
    conn = get_db()

    today = date.today()

    # Complete shipments that have arrived today or earlier
    due_shipments = conn.execute(
        "SELECT * FROM shipments WHERE user_id = ? AND status = 'pending' AND arrival_date <= ?",
        (user_id, today.isoformat())
    ).fetchall()
    for shipment in due_shipments:
        conn.execute(
            "UPDATE products SET quantity = quantity + ? WHERE id = ? AND user_id = ?",
            (shipment["order_qty"], shipment["product_id"], user_id)
        )
        conn.execute(
            "UPDATE shipments SET status = 'completed' WHERE id = ?",
            (shipment["id"],)
        )

    # Schedule shipments for any low-stock product that does not already have a pending shipment
    low_stock = conn.execute(
        "SELECT * FROM products WHERE user_id = ? AND quantity <= 15 ORDER BY quantity ASC",
        (user_id,)
    ).fetchall()

    for product in low_stock:
        pending = conn.execute(
            "SELECT 1 FROM shipments WHERE product_id = ? AND user_id = ? AND status = 'pending'",
            (product["id"], user_id)
        ).fetchone()
        if pending:
            continue

        eta_days = 1 if product["quantity"] <= 5 else 2
        order_qty = 50
        arrival_date = today + timedelta(days=eta_days)

        conn.execute(
            "INSERT INTO shipments (product_id, user_id, order_qty, order_date, arrival_date, status) VALUES (?, ?, ?, ?, ?, 'pending')",
            (product["id"], user_id, order_qty, today.isoformat(), arrival_date.isoformat())
        )

    conn.commit()

    shipments = conn.execute(
        "SELECT s.*, p.name, p.supplier, p.quantity FROM shipments s JOIN products p ON p.id = s.product_id WHERE s.user_id = ? AND s.status = 'pending' ORDER BY s.arrival_date ASC",
        (user_id,)
    ).fetchall()
    conn.close()

    shipment_list = []
    for shipment in shipments:
        arrival_date_raw = shipment["arrival_date"]
        try:
            arrival_date = date.fromisoformat(arrival_date_raw)
        except (TypeError, ValueError):
            continue

        eta_days = (arrival_date - today).days
        if eta_days > 0:
            eta_text = f"Arrives in {eta_days} day{'' if eta_days == 1 else 's'}"
        elif eta_days == 0:
            eta_text = "Arrives today"
        else:
            eta_text = f"Arrived {-eta_days} day{'' if eta_days == -1 else 's'} ago"

        shipment_list.append({
            "id": shipment["product_id"],
            "name": shipment["name"],
            "quantity": shipment["quantity"],
            "supplier": shipment["supplier"],
            "eta_days": eta_days,
            "arrival_date": arrival_date.strftime("%b %d, %Y"),
            "eta_text": eta_text
        })

    return render_template("shipment.html", shipments=shipment_list)

# ── DELETE PRODUCT ──
@app.route("/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    conn = get_db()
    conn.execute(
        "DELETE FROM products WHERE id = ? AND user_id = ?",
        (product_id, session["user_id"])
    )
    conn.commit()
    conn.close()
    flash("Product deleted.", "success")
    return redirect(url_for("view_products"))

# ── EDIT PRODUCT ──
@app.route("/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    conn    = get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ? AND user_id = ?",
        (product_id, session["user_id"])
    ).fetchone()

    if not product:
        flash("Product not found.", "error")
        conn.close()
        return redirect(url_for("view_products"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        quantity = request.form.get("quantity", "0").strip()
        price    = request.form.get("price", "0").strip()
        supplier = request.form.get("supplier", "").strip()

        price = price.replace(",", "").replace("₹", "").strip()
        try:
            quantity = int(quantity)
            price    = float(price)
        except ValueError:
            flash("Invalid quantity or price.", "error")
            conn.close()
            return redirect(url_for("edit_product", product_id=product_id))

        conn.execute(
            """UPDATE products
               SET name = ?, quantity = ?, price = ?, supplier = ?
               WHERE id = ? AND user_id = ?""",
            (name, quantity, price, supplier, product_id, session["user_id"])
        )
        conn.commit()
        conn.close()

        flash(f'"{name}" updated successfully!', "success")
        return redirect(url_for("view_products"))

    conn.close()
    return render_template("edit_product.html", product=product)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
