# ============================================================================
# AUTH ROUTES
# ----------------------------------------------------------------------------
# Login, signup, logout, staff management, and password change all live
# here. Signup is the app's default landing page (set in app/__init__.py's
# login_manager.login_view) — every fresh visit shows "Create Account"
# first. Someone who already has an account clicks "Already have an
# account? Log in" from there (that link only appears once an owner
# actually exists — see signup.html) to reach the real login form.
# The one function almost everything else depends on is owner_exists()
# (defined in models.py) — it decides whether a new signup becomes an
# "owner" or "staff" account.
# ============================================================================

from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from .. import db
from ..models import User, owner_exists, set_setting, get_profit_loss

auth_bp = Blueprint("auth", __name__)


def find_user_by_username(username):
    """
    Look a user up ignoring upper/lower case, so "Payal", "payal" and "PAYAL"
    all reach the same account. Phone keyboards love to capitalise the first
    letter, and nobody should be locked out by that. An exact match is tried
    first, so older databases that somehow hold two names differing only by
    case still behave.
    """
    exact = User.query.filter_by(username=username).first()
    if exact:
        return exact
    return User.query.filter(func.lower(User.username) == username.lower()).first()


def is_safe_next_url(target):
    """Only allow redirecting to a page inside this app (e.g. /billing/), never to another website."""
    return bool(target) and target.startswith("/") and not target.startswith("//") and "\\" not in target


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # Open signup: anyone can create their own account. The FIRST account
    # ever created becomes the "owner" (full control). Every account after
    # that is automatically "staff" (can bill and manage inventory, but
    # can't manage other accounts) — so there's always exactly one owner,
    # even though signup itself stays open to everyone.
    is_first_account = not owner_exists()

    if request.method == "POST":
        shop_name = request.form.get("shop_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
        elif len(password) < 4:
            flash("Password must be at least 4 characters.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif password != password.strip():
            flash("Password cannot start or end with a space. Please retype it.", "danger")
        elif find_user_by_username(username):
            flash("That username is already taken.", "danger")
        else:
            role = "owner" if is_first_account else "staff"
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            if is_first_account and shop_name:
                set_setting("shop_name", shop_name)
            flash("Account created! You can now log in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("signup.html", is_first_account=is_first_account)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    # No owner account yet -> send straight to first-time setup.
    if not owner_exists():
        return redirect(url_for("auth.signup"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = find_user_by_username(username)

        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            return redirect(next_page if is_safe_next_url(next_page) else url_for("dashboard.home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """
    Instead of logging out instantly, show today's closing summary first —
    sales, expenses, net profit — so whoever's closing up sees the day's
    numbers before leaving. Actual logout happens on confirmation.
    """
    today = date.today()
    month_start = today.replace(day=1)
    today_pl = get_profit_loss(today)
    month_pl = get_profit_loss(month_start)
    return render_template("logout_summary.html", today_pl=today_pl, month_pl=month_pl)


@auth_bp.route("/logout/confirm", methods=["POST"])
@login_required
def logout_confirm():
    logout_user()
    flash("You have been logged out.", "info")
    # Back to the same default landing page (signup) as every fresh visit —
    # keeps this consistent for a demo where one person logs out and the
    # next person should immediately see "Create Account" (with a Log in
    # link available), not assume they want to log back in as whoever
    # just left.
    return redirect(url_for("auth.signup"))


@auth_bp.route("/staff", methods=["GET", "POST"])
@login_required
def manage_staff():
    if current_user.role != "owner":
        flash("Only the shop owner can manage staff accounts.", "danger")
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
        elif find_user_by_username(username):
            flash("That username is already taken.", "danger")
        else:
            new_staff = User(username=username, role="staff")
            new_staff.set_password(password)
            db.session.add(new_staff)
            db.session.commit()
            flash(f"Staff account '{username}' created.", "success")
        return redirect(url_for("auth.manage_staff"))

    staff_accounts = User.query.filter_by(role="staff").all()
    return render_template("staff.html", staff_accounts=staff_accounts)


@auth_bp.route("/staff/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_staff(user_id):
    if current_user.role != "owner":
        flash("Only the shop owner can manage staff accounts.", "danger")
        return redirect(url_for("dashboard.home"))

    staff = User.query.get_or_404(user_id)
    if staff.role == "owner":
        flash("Cannot delete the owner account.", "danger")
    else:
        db.session.delete(staff)
        db.session.commit()
        flash("Staff account removed.", "info")
    return redirect(url_for("auth.manage_staff"))


@auth_bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "danger")
        elif len(new_pw) < 4:
            flash("New password must be at least 4 characters.", "danger")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash("Password updated successfully.", "success")
            return redirect(url_for("dashboard.home"))

    return render_template("change_password.html")
