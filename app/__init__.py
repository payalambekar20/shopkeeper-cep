import os
import sys
import secrets
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
# Signup is the default landing page every time the app is opened —
# whoever's demoing/using it sees "Create Account" first. Someone who
# already has an account clicks "Already have an account? Log in" from
# there to reach the actual login form, rather than the app guessing or
# remembering who used it last.
login_manager.login_view = "auth.signup"
login_manager.login_message = "Please sign in or create an account to continue."
login_manager.login_message_category = "warning"


def _get_instance_path():
    """
    Where the database file should live.

    Normally Flask's own default (a folder next to the app's code) is fine.
    But when this app is bundled into a standalone .exe (via PyInstaller),
    the code actually runs from a TEMPORARY folder that gets wiped and
    re-extracted fresh every time the program starts — so a database saved
    there would lose all its data the moment the shop owner closed and
    reopened the program. getattr(sys, "frozen", False) is how you detect
    "am I running as a bundled .exe right now?" — PyInstaller sets this
    flag automatically. If so, we point the instance folder at a stable
    location next to the actual .exe file instead.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        return os.path.join(base_dir, "instance")
    return None  # let Flask use its normal default


def create_app():
    app = Flask(__name__, instance_relative_config=True, instance_path=_get_instance_path())

    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "shop.db"),
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        LOW_STOCK_DEFAULT_THRESHOLD=5,
        SHOP_NAME=os.environ.get("SHOP_NAME", "My Shop"),
    )

    db.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    from .routes.auth import auth_bp
    from .routes.inventory import inventory_bp
    from .routes.billing import billing_bp
    from .routes.dashboard import dashboard_bp
    from .routes.expenses import expenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)

    with app.app_context():
        db.create_all()

        # SECRET_KEY: an env var (set this for the Render/cloud deploy)
        # always wins. Otherwise, generate a random key ONCE and store it
        # IN the database itself — so it lives and dies with that specific
        # shop's data. This matters a lot for reset_for_new_shop.py: when
        # that script archives the old database and a fresh one is
        # created, this key is regenerated too, which automatically
        # invalidates every old browser session cookie. Without this, a
        # leftover cookie from before a reset could silently log someone
        # into a brand new shop's owner account without ever seeing the
        # login or signup page — which is exactly the bug this fixes.
        secret = os.environ.get("SECRET_KEY")
        if not secret:
            secret = models.get_setting("app_secret_key", "")
            if not secret:
                secret = secrets.token_hex(32)
                models.set_setting("app_secret_key", secret)
        app.config["SECRET_KEY"] = secret

    @app.template_filter("inr")
    def inr_format(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return f"₹{value:,.2f}"

    @app.context_processor
    def inject_shop_name():
        from .models import get_setting
        return {"shop_name": get_setting("shop_name", app.config["SHOP_NAME"])}

    return app
