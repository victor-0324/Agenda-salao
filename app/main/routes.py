from flask import Blueprint, render_template
from flask_login import current_user

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    if current_user.is_authenticated:
        from flask import redirect, url_for
        return redirect(url_for("dashboard.index"))
    return render_template("main/landing.html")


@main_bp.route("/precos")
def pricing():
    return render_template("main/pricing.html")
