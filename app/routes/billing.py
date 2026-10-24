# ============================================================================
# BILLING ROUTES
# ----------------------------------------------------------------------------
# This file turns a shopping cart into a real, saved Bill. The single most
# important idea in this whole file: NEVER TRUST THE BROWSER. Everything
# the cart sends (prices, stock availability) gets re-checked against the
# database here, because a browser's dev tools could be used to fake almost
# anything on the client side.
# ============================================================================

import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from .. import db
from ..models import Product, ProductVariant, Bill, BillItem, next_bill_number

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.route("/", methods=["GET"])
@login_required
def new_bill():
    # Just shows the empty billing page — the cart itself lives entirely
    # in the browser's memory (JavaScript) until "Generate Bill" is clicked.
    return render_template("billing.html")


@billing_bp.route("/create", methods=["POST"])
@login_required
def create_bill():
    """
    Expects a JSON-encoded cart in the 'cart_data' form field:
    [{"product_id": 1, "quantity": 2}, ...]
    Note: "product_id" here actually refers to a ProductVariant's id (the
    specific size/pack being sold), since price and stock are tracked per
    variant, not per product. Recalculates prices server-side from the DB —
    never trusts client-sent totals.
    """
    # STEP 1: Read the basic form fields the cashier filled in.
    customer_name = request.form.get("customer_name", "").strip()
    customer_phone = request.form.get("customer_phone", "").strip()

    # Phone number is optional, but if one was entered it must be exactly
    # 10 digits — this re-checks on the server even though the billing
    # page's input field already restricts typing, since a browser field
    # restriction can always be bypassed (e.g. submitting the form
    # directly), and the server should never trust the client alone.
    if customer_phone and (not customer_phone.isdigit() or len(customer_phone) != 10):
        flash("Customer phone number must be exactly 10 digits.", "danger")
        return redirect(url_for("billing.new_bill"))

    # STEP 2: Parse the numbers and the cart JSON, bailing out safely if
    # anything is malformed (e.g. someone submitted garbage manually).
    try:
        discount_percent = float(request.form.get("discount_percent", 0) or 0)
        tax_percent = float(request.form.get("tax_percent", 0) or 0)
        cart = json.loads(request.form.get("cart_data", "[]"))
    except (ValueError, json.JSONDecodeError):
        flash("Something went wrong reading the cart. Please try again.", "danger")
        return redirect(url_for("billing.new_bill"))

    if not cart:
        flash("Cart is empty. Add at least one item before billing.", "danger")
        return redirect(url_for("billing.new_bill"))

    if discount_percent < 0 or discount_percent > 100 or tax_percent < 0 or tax_percent > 100:
        flash("Discount and tax must be between 0 and 100 percent.", "danger")
        return redirect(url_for("billing.new_bill"))

    # STEP 3: Walk through every cart entry and VALIDATE + RECALCULATE from
    # the database. This is the core security step — the browser might have
    # displayed a different price, but we only trust variant.price here,
    # which comes straight from the database, not from the submitted form.
    bill_items = []
    subtotal = 0.0

    for entry in cart:
        variant = ProductVariant.query.get(entry.get("product_id"))
        try:
            qty = int(entry.get("quantity", 0))
        except (TypeError, ValueError):
            qty = 0

        if not variant or qty <= 0:
            continue  # silently skip anything invalid rather than crashing

        # Stock check — this is what makes overselling impossible, even if
        # someone tampered with the browser to show a bigger "available"
        # number than what's actually in the database.
        if qty > variant.stock_qty:
            flash(
                f"Not enough stock for '{variant.display_name}'. Available: {variant.stock_qty}, requested: {qty}.",
                "danger",
            )
            return redirect(url_for("billing.new_bill"))

        line_total = round(variant.price * qty, 2)
        subtotal += line_total
        bill_items.append(
            {
                "variant": variant,
                "unit_price": variant.price,
                "quantity": qty,
                "line_total": line_total,
            }
        )

    if not bill_items:
        flash("No valid items in cart.", "danger")
        return redirect(url_for("billing.new_bill"))

    # STEP 4: Apply discount, then tax on top of the discounted amount
    # (this order matters — tax is calculated AFTER discount is subtracted,
    # which is standard billing practice).
    discount_amount = round(subtotal * (discount_percent / 100), 2)
    taxable_amount = subtotal - discount_amount
    tax_amount = round(taxable_amount * (tax_percent / 100), 2)
    total = round(taxable_amount + tax_amount, 2)

    # STEP 5: Create the Bill row first...
    bill = Bill(
        bill_number=next_bill_number(),
        customer_name=customer_name or None,
        customer_phone=customer_phone or None,
        subtotal=round(subtotal, 2),
        discount_percent=discount_percent,
        tax_percent=tax_percent,
        total=total,
    )
    db.session.add(bill)
    # db.session.flush() sends this INSERT to the database immediately
    # (without fully committing the transaction yet) so that bill.id gets
    # assigned by the database's auto-increment RIGHT NOW. We need that id
    # below to link each BillItem back to this bill.
    db.session.flush()

    # STEP 6: ...then create one BillItem per cart line, AND deduct stock
    # from the actual ProductVariant at the same time. Both happen in the
    # same database transaction, so either both succeed or (if something
    # crashes) neither does — the stock count and the bill record can
    # never get out of sync with each other.
    for item in bill_items:
        variant = item["variant"]
        variant.stock_qty -= item["quantity"]
        db.session.add(
            BillItem(
                bill_id=bill.id,
                variant_id=variant.id,
                product_name=variant.display_name,   # snapshot — see models.py comment on BillItem
                unit_price=item["unit_price"],         # snapshot
                quantity=item["quantity"],
                line_total=item["line_total"],
            )
        )

    db.session.commit()  # makes everything above permanent
    flash(f"Bill {bill.bill_number} generated successfully.", "success")
    return redirect(url_for("billing.view_receipt", bill_id=bill.id))


@billing_bp.route("/receipt/<int:bill_id>")
@login_required
def view_receipt(bill_id):
    # get_or_404: fetch the bill, or automatically show a 404 error page
    # if that id doesn't exist — saves writing a manual "if not found" check.
    bill = Bill.query.get_or_404(bill_id)
    return render_template("receipt.html", bill=bill)


@billing_bp.route("/history")
@login_required
def history():
    # Supports ?days=7, ?days=30, or ?days=all in the URL, defaulting to 30.
    days = request.args.get("days", "30")
    query = Bill.query
    if days != "all":
        try:
            cutoff = datetime.utcnow() - timedelta(days=int(days))
            query = query.filter(Bill.created_at >= cutoff)
        except ValueError:
            pass  # if someone puts a weird value in the URL, just show everything
    bills = query.order_by(Bill.created_at.desc()).all()  # newest first
    return render_template("bill_history.html", bills=bills, days=days)
