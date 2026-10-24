# ============================================================================
# INVENTORY ROUTES
# ----------------------------------------------------------------------------
# Handles everything about products: viewing the list, adding/editing/
# deleting a size ("variant"), and the two small JSON APIs the billing page
# calls (search-as-you-type, and quick-add-mid-sale).
# ============================================================================

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required
from sqlalchemy import or_
from .. import db
from ..models import Product, ProductVariant

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/")
@login_required
def list_products():
    # Everything shown here is really a list of VARIANTS (one row per
    # size/pack), not products — that's why every query below starts from
    # ProductVariant and .join(Product) to also pull in the shared name/
    # category/unit fields.
    query = request.args.get("q", "").strip()
    filter_low = request.args.get("low") == "1"

    variants_query = ProductVariant.query.join(Product)
    if query:
        like_term = f"%{query}%"
        # ilike = case-insensitive LIKE, and % is a wildcard — this matches
        # the search text ANYWHERE in the name/category/label, not just the start.
        variants_query = variants_query.filter(
            or_(Product.name.ilike(like_term), Product.category.ilike(like_term), ProductVariant.label.ilike(like_term))
        )
    variants = variants_query.order_by(Product.name.asc(), ProductVariant.price.asc()).all()

    if filter_low:
        # Done in Python (not SQL) because is_low_stock is a calculated
        # @property, not a real database column — can't filter a query by it.
        variants = [v for v in variants if v.is_low_stock]

    return render_template("inventory.html", variants=variants, query=query, filter_low=filter_low)


@inventory_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        unit = request.form.get("unit", "pcs").strip() or "pcs"
        label = request.form.get("label", "").strip() or "Standard"

        try:
            price = float(request.form.get("price", 0))
            stock_qty = int(request.form.get("stock_qty", 0))
            threshold = int(request.form.get("low_stock_threshold", 5))
        except ValueError:
            flash("Price and quantity must be valid numbers.", "danger")
            return render_template("product_form.html", variant=None, form_data=request.form)

        if not name:
            flash("Product name is required.", "danger")
            return render_template("product_form.html", variant=None, form_data=request.form)
        if price < 0 or stock_qty < 0:
            flash("Price and stock cannot be negative.", "danger")
            return render_template("product_form.html", variant=None, form_data=request.form)

        # If a product with this name already exists, add this as a new
        # size/variant under it instead of creating a duplicate product.
        # .ilike() = case-insensitive match, so "shampoo" and "Shampoo"
        # are treated as the same product, not two different ones.
        product = Product.query.filter(Product.name.ilike(name)).first()
        if not product:
            product = Product(name=name, category=category, unit=unit)
            db.session.add(product)
            # flush() sends the INSERT now so product.id exists immediately
            # (needed below to link the new variant to it), without fully
            # committing the transaction yet.
            db.session.flush()
        else:
            existing_variant = ProductVariant.query.filter(
                ProductVariant.product_id == product.id, ProductVariant.label.ilike(label)
            ).first()
            if existing_variant:
                flash(
                    f"'{product.name}' already has a size/variant called '{label}'. Edit it instead of adding a duplicate.",
                    "danger",
                )
                return render_template("product_form.html", variant=None, form_data=request.form)

        variant = ProductVariant(
            product_id=product.id,
            label=label,
            price=price,
            stock_qty=stock_qty,
            low_stock_threshold=threshold,
        )
        db.session.add(variant)
        db.session.commit()
        flash(f"'{variant.display_name}' added.", "success")
        return redirect(url_for("inventory.list_products"))

    return render_template("product_form.html", variant=None, form_data=None)


@inventory_bp.route("/<int:variant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(variant_id):
    variant = ProductVariant.query.get_or_404(variant_id)
    product = variant.product

    if request.method == "POST":
        try:
            price = float(request.form.get("price", 0))
            stock_qty = int(request.form.get("stock_qty", 0))
            threshold = int(request.form.get("low_stock_threshold", 5))
        except ValueError:
            flash("Price and quantity must be valid numbers.", "danger")
            return render_template("product_form.html", variant=variant, form_data=request.form)

        name = request.form.get("name", "").strip()
        label = request.form.get("label", "").strip() or "Standard"
        if not name:
            flash("Product name is required.", "danger")
            return render_template("product_form.html", variant=variant, form_data=request.form)
        if price < 0 or stock_qty < 0:
            flash("Price and stock cannot be negative.", "danger")
            return render_template("product_form.html", variant=variant, form_data=request.form)

        product.name = name
        product.category = request.form.get("category", "General").strip() or "General"
        product.unit = request.form.get("unit", "pcs").strip() or "pcs"
        variant.label = label
        variant.price = price
        variant.stock_qty = stock_qty
        variant.low_stock_threshold = threshold
        db.session.commit()
        flash(f"'{variant.display_name}' updated.", "success")
        return redirect(url_for("inventory.list_products"))

    return render_template("product_form.html", variant=variant, form_data=None)


@inventory_bp.route("/<int:variant_id>/delete", methods=["POST"])
@login_required
def delete_product(variant_id):
    variant = ProductVariant.query.get_or_404(variant_id)
    product = variant.product
    name = variant.display_name
    db.session.delete(variant)
    db.session.flush()

    # If that was the last size/variant for this product, remove the
    # now-empty product too so it doesn't linger in searches.
    if ProductVariant.query.filter_by(product_id=product.id).count() == 0:
        db.session.delete(product)

    db.session.commit()
    flash(f"'{name}' deleted.", "info")
    return redirect(url_for("inventory.list_products"))


@inventory_bp.route("/api/quick-add", methods=["POST"])
@login_required
def api_quick_add():
    """
    Lets the cashier add a brand-new product (or a new size of an existing
    one) directly from the billing screen mid-sale, instead of stopping to
    use the Inventory page. Saves it permanently, so it's searchable for
    every future sale too.
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    label = (data.get("label") or "").strip() or "Standard"
    category = (data.get("category") or "General").strip() or "General"
    unit = (data.get("unit") or "pcs").strip() or "pcs"

    try:
        price = float(data.get("price", 0))
        stock_qty = int(data.get("stock_qty", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Price and stock must be valid numbers."}), 400

    if not name:
        return jsonify({"error": "Product name is required."}), 400
    if price < 0 or stock_qty < 0:
        return jsonify({"error": "Price and stock cannot be negative."}), 400

    product = Product.query.filter(Product.name.ilike(name)).first()
    if product:
        existing_variant = ProductVariant.query.filter(
            ProductVariant.product_id == product.id, ProductVariant.label.ilike(label)
        ).first()
        if existing_variant:
            # Don't create a duplicate — hand back the existing variant so
            # the cashier can just sell from it.
            return jsonify({"error": "duplicate", "product": existing_variant.to_dict()}), 409
    else:
        product = Product(name=name, category=category, unit=unit)
        db.session.add(product)
        db.session.flush()

    variant = ProductVariant(
        product_id=product.id,
        label=label,
        price=price,
        stock_qty=stock_qty,
        low_stock_threshold=5,
    )
    db.session.add(variant)
    db.session.commit()
    return jsonify(variant.to_dict()), 201


@inventory_bp.route("/api/search")
@login_required
def api_search():
    """Used by the billing page to look up products live as the cashier types."""
    query = request.args.get("q", "").strip()
    variants_query = ProductVariant.query.join(Product).filter(ProductVariant.stock_qty > 0)
    if query:
        like_term = f"%{query}%"
        variants_query = variants_query.filter(
            or_(Product.name.ilike(like_term), ProductVariant.label.ilike(like_term))
        )
    variants = variants_query.order_by(Product.name.asc(), ProductVariant.price.asc()).limit(15).all()
    return jsonify([v.to_dict() for v in variants])
