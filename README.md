# Inventory Control System 📦🛒

A modern, multi-user **Inventory Control System** built with **Flask** and **SQLite**. Manage your products, monitor stock levels in real time, and let the system automatically schedule restocking shipments — all through a clean, responsive UI with dark mode support.

---

## 🏪 Introduction to Smart Inventory Management

In traditional inventory workflows, stock tracking is manual, error-prone, and reactive — you discover you've run out of a product only *after* a customer asks for it.

**Enter StockPilot.**

Instead of spreadsheets and guesswork, StockPilot gives you a **real-time command center** for your inventory:

- **📊 Live Dashboard:** Instantly see total products, total units, and items running low — all in one glance.
- **⚠️ Low Stock Detection:** The system automatically flags any product with ≤ 15 units remaining.
- **🚚 Auto-Restocking:** When stock dips below the threshold, StockPilot schedules shipments automatically — critical items (≤ 5 units) get **1-day delivery**, others get **2-day delivery**.
- **🔐 Multi-User Isolation:** Every user sees only their own products and shipments, secured behind bcrypt-hashed authentication.

> If your stock is running low, StockPilot catches it before your customers do!

---

## ✨ Key Features

| | Feature | Description |
|---|---------|-------------|
| 🔐 | **Secure Authentication** | User registration & login with [bcrypt](https://pypi.org/project/bcrypt/) password hashing, session-based access control, and password strength validation. |
| 📊 | **Real-Time Dashboard** | Live stats grid showing total products, total units, and low-stock count with recent additions and quick action shortcuts. |
| 📋 | **Full CRUD Operations** | Add, view, edit, and delete products with inline form validation and confirmation prompts. |
| 🔍 | **Search & Filters** | Text search by product name, low-stock filter, price sorting (high/low), and quantity sorting — all via a sleek filter modal. |
| 🚚 | **Auto Shipment Scheduling** | Automatically detects low-stock items and schedules restocking shipments with ETA tracking and auto-completion on arrival. |
| 💰 | **Indian Rupee (₹) Formatting** | Custom Jinja2 filter formats prices in the Indian numbering system (e.g., `₹12,34,567.89`). |
| 🌙 | **Dark Mode** | One-click toggle between light and dark themes, persisted in `localStorage` and respecting system `prefers-color-scheme`. |
| 📱 | **Fully Responsive** | Clean, mobile-friendly layout that works on desktop, tablet, and phone screens. |

---

## 🛠️ Tech Stack

| Category | Technology |
|----------|-----------|
| Framework | [Flask](https://flask.palletsprojects.com/) (Python) |
| Database | [SQLite](https://www.sqlite.org/) |
| Templating | [Jinja2](https://jinja.palletsprojects.com/) |
| Password Security | [bcrypt](https://pypi.org/project/bcrypt/) |
| Styling | Custom CSS3 (no frameworks) |
| Fonts | [Inter](https://fonts.google.com/specimen/Inter) & [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans) |
| Production Server | [Gunicorn](https://gunicorn.org/) |

---

## 🚀 Getting Started

Follow these steps to set up and run StockPilot on your local machine.

### Prerequisites

Ensure you have [Python](https://www.python.org/) (v3.8 or higher) and pip installed.

```bash
python --version
pip --version
```

### Installation Steps

**1. Clone the Repository**

```bash
git clone https://github.com/Joshi4git-hub/Inventory_Control_System_SQLite.git
cd Inventory_Control_System_SQLite
```

**2. Create a Virtual Environment** (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install Dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the Development Server**

```bash
python app.py
```

**5. Open in Browser**

Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser to access the application.

> The SQLite database (`inventory.db`) is created automatically on first run. No manual database setup is required.

---

## 📁 Project Structure

```
Inventory_Control_System_SQLite/
├── app.py                   # Main Flask app — routes, models, and business logic
├── inventory.db             # SQLite database (auto-created on first run)
├── inventory.sqbpro         # DB Browser for SQLite project file
├── requirements.txt         # Python dependencies (Flask, bcrypt, gunicorn)
├── static/
│   └── style.css            # Complete stylesheet (light + dark themes, responsive)
└── templates/
    ├── base.html            # Base layout — navbar, flash messages, dark mode toggle
    ├── index.html           # Dashboard — stats grid, recent items, low stock alerts
    ├── login.html           # Login page with auth card
    ├── register.html        # Registration page with validation
    ├── add_product.html     # Add new product form
    ├── edit_product.html    # Edit existing product form
    ├── view_products.html   # Product listing with search, filter & sort modal
    └── shipment.html        # Shipment schedule with ETA tracking
```

---

## 🗄️ Database Schema

The application uses three interconnected SQLite tables:

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│    users     │       │     products     │       │      shipments       │
├──────────────┤       ├──────────────────┤       ├──────────────────────┤
│ id       PK  │──┐    │ id          PK   │──┐    │ id              PK   │
│ username  UK │  │    │ name             │  │    │ product_id      FK ──│──> products.id
│ email     UK │  └──> │ user_id     FK   │  └──> │ user_id         FK ──│──> users.id
│ password     │       │ quantity         │       │ order_qty            │
└──────────────┘       │ price            │       │ order_date           │
                       │ supplier         │       │ arrival_date         │
                       └──────────────────┘       │ status (pending/     │
                                                  │         completed)   │
                                                  └──────────────────────┘
```

- **users** — Stores registered accounts with bcrypt-hashed passwords.
- **products** — Each product belongs to a user (multi-tenant isolation).
- **shipments** — Auto-generated restocking orders linked to both a product and a user.

---

## 🔑 How the Auto-Shipment System Works

StockPilot's shipment engine runs automatically every time the **Shipments** page is visited:

```
[ Low Stock Detected ]  ──>  [ Shipment Scheduled ]  ──>  [ Auto-Completed on Arrival ]
    (≤ 15 units)                (50 units ordered)           (stock quantity updated)
```

### Step-by-Step Flow

1. **Detection:** The system scans all products for the logged-in user and identifies items with quantity ≤ 15.

2. **Scheduling:** For each low-stock item *without* an existing pending shipment:
   - **Critical stock (≤ 5 units)** → Shipment arrives in **1 day**
   - **Low stock (6–15 units)** → Shipment arrives in **2 days**
   - Default restock quantity: **50 units**

3. **Auto-Completion:** On each visit, any pending shipment whose arrival date has passed is automatically marked as `completed`, and the ordered quantity is added back to the product's stock.

4. **Duplicate Prevention:** The system never creates a second pending shipment for a product that already has one in the pipeline.

---

## ⚙️ Configuration Reference

| Setting | Location | Default Value |
|---------|----------|---------------|
| Secret Key | `app.py` line 10 | `"inventory_secret_key_2024"` |
| Database Path | `app.py` line 13 | `./inventory.db` |
| Low Stock Threshold | `app.py` lines 204, 280, 331 | `15 units` |
| Restock Quantity | `app.py` line 345 | `50 units` |
| Debug Mode | `app.py` line 450 | `True` |

> ⚠️ **Production Warning:** Before deploying, change `app.secret_key` to a strong random value and set `debug=False`.

---

## 🖥️ Production Deployment

**Linux / macOS** — Use Gunicorn (included in `requirements.txt`):

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**Windows** — Use [Waitress](https://docs.pylonsproject.org/projects/waitress/) instead:

```bash
pip install waitress
waitress-serve --port=8000 app:app
```

---

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -m "Add your feature"`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open** a Pull Request

---

## 🧑‍💻 Author & Maintainer

- **GitHub Profile:** [@Joshi4git-hub](https://github.com/Joshi4git-hub)
- **Repository:** [Joshi4git-hub/Inventory_Control_System_SQLite](https://github.com/Joshi4git-hub/Inventory_Control_System_SQLite)

---

## 📜 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.
