from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from decimal import Decimal, InvalidOperation
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
    if "user" in session:
        return redirect(url_for("index"))

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
    conn    = get_db()

    if search:
        products = conn.execute(
            "SELECT * FROM products WHERE user_id = ? AND name LIKE ?",
            (user_id, f"%{search}%")
        ).fetchall()
    else:
        products = conn.execute(
            "SELECT * FROM products WHERE user_id = ?",
            (user_id,)
        ).fetchall()

    conn.close()
    return render_template("view_products.html", products=products, search=search)

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
