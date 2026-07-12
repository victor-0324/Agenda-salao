import re
import unicodedata

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import Salon, User
from app.config import Config

auth_bp = Blueprint("auth", __name__)


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s-]+", "-", text)
    return text or "salao"


def unique_slug(base):
    slug = base
    i = 1
    while Salon.query.filter_by(slug=slug).first() is not None:
        i += 1
        slug = f"{base}-{i}"
    return slug


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    selected_plan = request.args.get("plano", "pro")
    if selected_plan not in Config.PLANS:
        selected_plan = "pro"

    if request.method == "POST":
        salon_name = request.form.get("salon_name", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        plan = request.form.get("plan", "pro")
        if plan not in Config.PLANS:
            plan = "pro"

        errors = []
        if not salon_name:
            errors.append("Informe o nome do salão.")
        if not owner_name:
            errors.append("Informe seu nome.")
        if not email or "@" not in email:
            errors.append("Informe um e-mail válido.")
        if len(password) < 6:
            errors.append("A senha precisa ter pelo menos 6 caracteres.")
        if password != password2:
            errors.append("As senhas não conferem.")
        if User.query.filter_by(email=email).first():
            errors.append("Já existe uma conta com esse e-mail.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", selected_plan=plan, form=request.form)

        salon = Salon(
            name=salon_name,
            slug=unique_slug(slugify(salon_name)),
            email=email,
            phone=phone,
            plan=plan,
        )
        salon.working_hours = Config.DEFAULT_WORKING_HOURS
        db.session.add(salon)
        db.session.flush()

        user = User(salon_id=salon.id, name=owner_name, email=email, role="owner")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Conta criada! Seu link de agendamento é /agendar/{salon.slug}", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html", selected_plan=selected_plan, form={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard.index"))

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("main.landing"))
