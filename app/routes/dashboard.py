from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from .. import db
from ..models import Product, ProductVariant, Bill, BillItem, get_profit_loss

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def home():
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    month_start = today.replace(day=1)
    month_start_dt = datetime.combine(month_start, datetime.min.time())

    today_sales = db.session.query(func.coalesce(func.sum(Bill.total), 0.0)).filter(
        Bill.created_at >= today_start
    ).scalar()
    today_bill_count = Bill.query.filter(Bill.created_at >= today_start).count()

    month_sales = db.session.query(func.coalesce(func.sum(Bill.total), 0.0)).filter(
        Bill.created_at >= month_start_dt
    ).scalar()
    month_bill_count = Bill.query.filter(Bill.created_at >= month_start_dt).count()

    today_pl = get_profit_loss(today)
    month_pl = get_profit_loss(month_start)

    all_variants = ProductVariant.query.all()
    low_stock_products = [v for v in all_variants if v.is_low_stock]

    top_products = (
        db.session.query(
            BillItem.product_name,
            func.sum(BillItem.quantity).label("total_qty"),
        )
        .join(Bill, Bill.id == BillItem.bill_id)
        .filter(Bill.created_at >= month_start_dt)
        .group_by(BillItem.product_name)
        .order_by(func.sum(BillItem.quantity).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        today_bill_count=today_bill_count,
        month_sales=month_sales,
        month_bill_count=month_bill_count,
        today_pl=today_pl,
        month_pl=month_pl,
        total_products=len(all_variants),
        low_stock_products=low_stock_products,
        top_products=top_products,
    )


@dashboard_bp.route("/api/sales-chart")
@login_required
def sales_chart_data():
    """Last 14 days of sales totals, for Chart.js."""
    days = 14
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time())

    rows = (
        db.session.query(
            func.date(Bill.created_at).label("day"),
            func.sum(Bill.total).label("total"),
        )
        .filter(Bill.created_at >= start_dt)
        .group_by(func.date(Bill.created_at))
        .all()
    )
    totals_by_day = {str(row.day): float(row.total) for row in rows}

    labels = []
    data = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime("%d %b"))
        data.append(round(totals_by_day.get(d.isoformat(), 0.0), 2))

    return jsonify({"labels": labels, "data": data})
