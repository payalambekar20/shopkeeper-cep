"""
Optional: populate the database with sample kirana-store products so you
have something to demo immediately. Run with: python seed_demo_data.py
Safe to run multiple times - skips products that already exist by name.
"""
from app import create_app, db
from app.models import Product

SAMPLE_PRODUCTS = [
    ("Tata Salt 1kg", "Grocery", 28.0, 40, "pcs"),
    ("Aashirvaad Atta 5kg", "Grocery", 260.0, 15, "pcs"),
    ("Amul Toned Milk 500ml", "Dairy", 27.0, 30, "pcs"),
    ("Parle-G Biscuit", "Snacks", 10.0, 100, "pcs"),
    ("Maggi Noodles", "Snacks", 14.0, 60, "pcs"),
    ("Colgate Toothpaste 100g", "Personal Care", 55.0, 25, "pcs"),
    ("Surf Excel 1kg", "Household", 130.0, 3, "pcs"),
    ("Basmati Rice 5kg", "Grocery", 450.0, 4, "pcs"),
    ("Fortune Sunflower Oil 1L", "Grocery", 145.0, 20, "pcs"),
    ("Dettol Soap", "Personal Care", 40.0, 2, "pcs"),
]

app = create_app()

with app.app_context():
    created = 0
    for name, category, price, stock, unit in SAMPLE_PRODUCTS:
        if not Product.query.filter_by(name=name).first():
            db.session.add(
                Product(
                    name=name,
                    category=category,
                    price=price,
                    stock_qty=stock,
                    low_stock_threshold=5,
                    unit=unit,
                )
            )
            created += 1
    db.session.commit()
    print(f"Seeded {created} new product(s). Total products in DB: {Product.query.count()}")
