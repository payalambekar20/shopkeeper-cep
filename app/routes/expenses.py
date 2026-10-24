from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required
from .. import db
from ..models import Expense

expenses_bp = Blueprint("expenses", __name__, url_prefix="/expenses")


@expenses_bp.route("/")
@login_required
def list_expenses():
    days = request.args.get("days", "30")
    query = Expense.query
    if days != "all":
        try:
            cutoff = date.today() - timedelta(days=int(days))
            query = query.filter(Expense.expense_date >= cutoff)
        except ValueError:
            pass
    expenses = query.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template(
        "expenses.html",
        expenses=expenses,
        total=total,
        days=days,
        categories=Expense.EXPENSE_CATEGORIES,
        today_str=date.today().isoformat(),
    )


@expenses_bp.route("/add", methods=["POST"])
@login_required
def add_expense():
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "General").strip() or "General"
    expense_date_str = request.form.get("expense_date", "").strip()

    try:
        amount = float(request.form.get("amount", 0))
    except ValueError:
        flash("Amount must be a valid number.", "danger")
        return redirect(url_for("expenses.list_expenses"))

    if not description:
        flash("Description is required.", "danger")
        return redirect(url_for("expenses.list_expenses"))
    if amount <= 0:
        flash("Amount must be greater than zero.", "danger")
        return redirect(url_for("expenses.list_expenses"))

    try:
        expense_date = datetime.strptime(expense_date_str, "%Y-%m-%d").date() if expense_date_str else date.today()
    except ValueError:
        expense_date = date.today()

    expense = Expense(
        description=description,
        category=category,
        amount=amount,
        expense_date=expense_date,
    )
    db.session.add(expense)
    db.session.commit()
    flash(f"Expense '{description}' logged.", "success")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense removed.", "info")
    return redirect(url_for("expenses.list_expenses"))
