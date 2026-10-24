# ============================================================================
# DATABASE MODELS
# ----------------------------------------------------------------------------
# Every class below that inherits from db.Model becomes a real table in the
# SQLite database. Each db.Column(...) line becomes one column in that
# table. Flask-SQLAlchemy (the "db" object) handles turning these Python
# classes into actual SQL CREATE TABLE statements for us — we never write
# raw SQL, we just describe the shape of our data in Python.
# ============================================================================

from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db


class User(db.Model, UserMixin):
    """
    A login account — either the shop owner or a staff member.
    UserMixin (from Flask-Login) adds the methods Flask-Login needs to
    manage sessions (is_authenticated, get_id, etc.) so we don't have to
    write that boilerplate ourselves.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)               # auto-incrementing unique ID
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)   # NEVER store the real password — only the hash
    role = db.Column(db.String(20), nullable=False, default="owner")  # "owner" or "staff"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        # generate_password_hash scrambles the password one-way (like a
        # blender you can't run backwards). Even if the database file is
        # stolen, nobody can read the actual passwords out of it.
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        # Re-scrambles whatever was just typed at login and compares the
        # scrambled versions — the real password is never decrypted or
        # compared directly, because it can't be (hashing is one-way).
        return check_password_hash(self.password_hash, raw_password)


class Product(db.Model):
    """
    The SHARED identity of a product — just its name, category and unit.
    Does NOT hold price or stock directly, because the same product can be
    sold in multiple sizes at different prices (see ProductVariant below).
    """
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General")
    unit = db.Column(db.String(20), nullable=False, default="pcs")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # This line creates the "one Product has many ProductVariants" link.
    # SQLAlchemy uses it to let us write product.variants and get a list of
    # every size that product comes in. cascade="all, delete-orphan" means:
    # if a Product is deleted, all its variants are automatically deleted
    # too — we never end up with orphaned variant rows pointing to nothing.
    variants = db.relationship(
        "ProductVariant", backref="product", cascade="all, delete-orphan", order_by="ProductVariant.price"
    )


class ProductVariant(db.Model):
    """
    One sellable size/pack of a product — e.g. a "Shampoo" product might have
    three variants: '5ml Sachet' at ₹5, '10ml Sachet' at ₹10, '200ml Bottle'
    at ₹150. Each variant has its OWN price and its OWN stock count, since a
    shop sells and restocks sachets very differently from bottles.

    This is the ONLY table where price and stock actually live — billing,
    search, and stock deduction all work off ProductVariant, not Product.
    """
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)

    # This is the "foreign key" — it stores the id of the Product this
    # variant belongs to. It's what actually creates the link between the
    # two tables at the database level (the .variants relationship above
    # is just a Python-side convenience built on top of this column).
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    label = db.Column(db.String(60), nullable=False, default="Standard")  # e.g. "5ml Sachet", "1L Bottle"
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    low_stock_threshold = db.Column(db.Integer, nullable=False, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_low_stock(self):
        # @property lets us call this as "variant.is_low_stock" (like a
        # normal variable) instead of "variant.is_low_stock()" (like a
        # method call) — even though it's actually running a small
        # calculation every time it's accessed.
        return self.stock_qty <= self.low_stock_threshold

    @property
    def display_name(self):
        """Product name plus size, e.g. 'Shampoo (200ml Bottle)'. Plain name if there's only one size."""
        if self.label and self.label != "Standard":
            return f"{self.product.name} ({self.label})"
        return self.product.name

    def to_dict(self):
        # Converts this database row into a plain Python dictionary, which
        # Flask's jsonify() can turn into JSON. This is what the billing
        # page's live search API sends back to the browser.
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name,
            "label": self.label,
            "display_name": self.display_name,
            "category": self.product.category,
            "price": self.price,
            "stock_qty": self.stock_qty,
            "unit": self.product.unit,
        }


class Bill(db.Model):
    """One completed sale/receipt."""
    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "20260920-0001"
    customer_name = db.Column(db.String(120), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    tax_percent = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One Bill has many BillItems (one row per product sold in that bill).
    items = db.relationship("BillItem", backref="bill", cascade="all, delete-orphan")


class BillItem(db.Model):
    """
    One line item within a bill (e.g. "2x Rice 5kg @ ₹400").

    IMPORTANT DESIGN DECISION: product_name and unit_price are SNAPSHOTS —
    copies of what the product was called and cost AT THE MOMENT OF SALE.
    We do NOT just look up the live product name/price every time, because
    if the shop changes a price next month, old receipts must still show
    what was actually charged back then. This is standard practice in real
    invoicing/e-commerce systems — your Amazon order history doesn't change
    just because a product's price changed after you bought it.
    """
    __tablename__ = "bill_items"

    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)  # snapshot, e.g. "Shampoo (200ml Bottle)"
    unit_price = db.Column(db.Float, nullable=False)          # snapshot of price at time of sale
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(db.Float, nullable=False)


class Expense(db.Model):
    """One shop expense — rent, electricity, wages, restocking cost, etc."""
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60), nullable=False, default="General")
    amount = db.Column(db.Float, nullable=False, default=0.0)
    expense_date = db.Column(db.Date, nullable=False, default=date.today)  # the day the expense happened
    created_at = db.Column(db.DateTime, default=datetime.utcnow)            # the day it was typed into the app

    EXPENSE_CATEGORIES = [
        "Rent",
        "Electricity",
        "Staff Wages",
        "Restocking / Purchases",
        "Transport",
        "Maintenance",
        "General",
    ]


class Setting(db.Model):
    """
    A simple key-value store for small bits of app-wide config — right now
    just the shop's name. Instead of adding a "shop_name" column somewhere
    awkward, this lets us store any future setting the same simple way
    without changing the database structure again.
    """
    __tablename__ = "settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(255), nullable=False)


def owner_exists():
    """
    True if a shop owner account has already been created on this install.
    This one function quietly powers a lot of behavior: it decides whether
    /login redirects to /signup, whether a new signup becomes owner or
    staff, and (after reset_for_new_shop.py moves the database away) lets
    the app correctly detect "this is a fresh install" again.
    """
    return User.query.filter_by(role="owner").first() is not None


def get_setting(key, default=""):
    row = Setting.query.get(key)
    return row.value if row else default


def set_setting(key, value):
    row = Setting.query.get(key)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))
    db.session.commit()


def next_bill_number():
    # Format: YYYYMMDD-0001, YYYYMMDD-0002, ... resetting each day.
    # We count how many bills already exist today and add 1.
    today_str = date.today().strftime("%Y%m%d")
    count_today = Bill.query.filter(Bill.bill_number.like(f"{today_str}-%")).count()
    return f"{today_str}-{count_today + 1:04d}"  # :04d pads with zeros, e.g. 0007


def get_profit_loss(start_date, end_date=None):
    """
    Sales minus expenses for a date range (inclusive).

    Deliberately pulled out into ONE shared function instead of writing
    this calculation separately in the dashboard and the logout summary —
    that way both places are GUARANTEED to always show identical numbers,
    since they're both calling the exact same code.
    """
    from sqlalchemy import func

    start_dt = datetime.combine(start_date, datetime.min.time())  # start of that day, 00:00:00
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())  # end of that day, 23:59:59
    else:
        end_dt = datetime.combine(date.today(), datetime.max.time())
        end_date = date.today()

    # func.sum() is SQL's SUM(). func.coalesce(..., 0.0) means "if there
    # are zero rows to sum, give back 0 instead of nothing" — without this,
    # a brand-new shop with no sales yet would crash this calculation.
    sales = db.session.query(func.coalesce(func.sum(Bill.total), 0.0)).filter(
        Bill.created_at >= start_dt, Bill.created_at <= end_dt
    ).scalar()
    bill_count = Bill.query.filter(Bill.created_at >= start_dt, Bill.created_at <= end_dt).count()
    expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0.0)).filter(
        Expense.expense_date >= start_date, Expense.expense_date <= end_date
    ).scalar()

    sales = round(sales, 2)
    expenses = round(expenses, 2)
    return {
        "sales": sales,
        "expenses": expenses,
        "profit": round(sales - expenses, 2),
        "bill_count": bill_count,
    }
