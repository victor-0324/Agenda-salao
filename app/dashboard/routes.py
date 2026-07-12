import os
import uuid
from datetime import datetime, date as date_cls, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Service, Client, Appointment, Salon
from app.config import Config

dashboard_bp = Blueprint("dashboard", __name__)


def salon():
    """Salão (tenant) do usuário logado."""
    return Salon.query.get(current_user.salon_id)


def plan_limits():
    s = salon()
    return Config.PLANS.get(s.plan, Config.PLANS["starter"])


def save_profile_photo(s, file_storage):
    """Salva a foto de perfil no UPLOAD_FOLDER e atualiza salon.profile_photo. Retorna
    uma mensagem de erro (string) se algo der errado, ou None se deu certo."""
    filename = file_storage.filename
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return "Formato de imagem não suportado. Use PNG, JPG ou WEBP."

    remove_profile_photo(s)  # apaga a foto antiga, se existir

    safe_name = secure_filename(f"salon-{s.id}-{uuid.uuid4().hex[:8]}.{ext}")
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)
    file_storage.save(dest)
    s.profile_photo = safe_name
    return None


def remove_profile_photo(s):
    if not s.profile_photo:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], s.profile_photo)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    s.profile_photo = None


@dashboard_bp.route("/")
@login_required
def index():
    s = salon()
    today = date_cls.today()
    today_appts = (
        Appointment.query.filter_by(salon_id=s.id, date=today)
        .filter(Appointment.status != "cancelado")
        .order_by(Appointment.start_time)
        .all()
    )
    week_end = today + timedelta(days=7)
    upcoming_count = Appointment.query.filter(
        Appointment.salon_id == s.id,
        Appointment.date >= today,
        Appointment.date <= week_end,
        Appointment.status != "cancelado",
    ).count()
    total_clients = Client.query.filter_by(salon_id=s.id).count()
    used_this_month = s.appointments_this_month()
    limits = plan_limits()

    return render_template(
        "dashboard/index.html",
        salon=s,
        today_appts=today_appts,
        upcoming_count=upcoming_count,
        total_clients=total_clients,
        used_this_month=used_this_month,
        limits=limits,
    )


# ---------- Serviços ----------

@dashboard_bp.route("/servicos")
@login_required
def services():
    s = salon()
    items = Service.query.filter_by(salon_id=s.id).order_by(Service.name).all()
    return render_template("dashboard/services.html", services=items, salon=s, limits=plan_limits())


@dashboard_bp.route("/servicos/novo", methods=["GET", "POST"])
@login_required
def service_new():
    s = salon()
    limits = plan_limits()
    current_count = Service.query.filter_by(salon_id=s.id).count()

    if current_count >= limits["max_services"]:
        flash(
            f"Seu plano {limits['label']} permite até {limits['max_services']} serviços. "
            "Faça upgrade para cadastrar mais.",
            "warning",
        )
        return redirect(url_for("dashboard.services"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duration = request.form.get("duration_min", "30")
        price = request.form.get("price", "0")
        errors = []
        if not name:
            errors.append("Informe o nome do serviço.")
        try:
            duration = int(duration)
            if duration <= 0:
                raise ValueError
        except ValueError:
            errors.append("Duração inválida.")
            duration = 30
        try:
            price = float(price.replace(",", "."))
        except ValueError:
            errors.append("Preço inválido.")
            price = 0

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("dashboard/service_form.html", service=None, form=request.form)

        item = Service(salon_id=s.id, name=name, duration_min=duration, price=price, active=True)
        db.session.add(item)
        db.session.commit()
        flash("Serviço cadastrado.", "success")
        return redirect(url_for("dashboard.services"))

    return render_template("dashboard/service_form.html", service=None, form={})


@dashboard_bp.route("/servicos/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def service_edit(service_id):
    s = salon()
    item = Service.query.filter_by(id=service_id, salon_id=s.id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        duration = request.form.get("duration_min", "30")
        price = request.form.get("price", "0")
        active = request.form.get("active") == "on"
        errors = []
        if not name:
            errors.append("Informe o nome do serviço.")
        try:
            duration = int(duration)
        except ValueError:
            errors.append("Duração inválida.")
            duration = item.duration_min
        try:
            price = float(str(price).replace(",", "."))
        except ValueError:
            errors.append("Preço inválido.")
            price = item.price

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("dashboard/service_form.html", service=item, form=request.form)

        item.name, item.duration_min, item.price, item.active = name, duration, price, active
        db.session.commit()
        flash("Serviço atualizado.", "success")
        return redirect(url_for("dashboard.services"))

    return render_template("dashboard/service_form.html", service=item, form={})


@dashboard_bp.route("/servicos/<int:service_id>/excluir", methods=["POST"])
@login_required
def service_delete(service_id):
    s = salon()
    item = Service.query.filter_by(id=service_id, salon_id=s.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Serviço removido.", "info")
    return redirect(url_for("dashboard.services"))


# ---------- Clientes ----------

@dashboard_bp.route("/clientes")
@login_required
def clients():
    s = salon()
    q = request.args.get("q", "").strip()
    query = Client.query.filter_by(salon_id=s.id)
    if q:
        query = query.filter(Client.name.ilike(f"%{q}%"))
    items = query.order_by(Client.name).all()
    return render_template("dashboard/clients.html", clients=items, q=q)


@dashboard_bp.route("/clientes/novo", methods=["GET", "POST"])
@login_required
def client_new():
    s = salon()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        notes = request.form.get("notes", "").strip()

        if not name or not phone:
            flash("Nome e telefone são obrigatórios.", "danger")
            return render_template("dashboard/client_form.html", client=None, form=request.form)

        item = Client(salon_id=s.id, name=name, phone=phone, email=email, notes=notes)
        db.session.add(item)
        db.session.commit()
        flash("Cliente cadastrado.", "success")
        return redirect(url_for("dashboard.clients"))

    return render_template("dashboard/client_form.html", client=None, form={})


@dashboard_bp.route("/clientes/<int:client_id>/editar", methods=["GET", "POST"])
@login_required
def client_edit(client_id):
    s = salon()
    item = Client.query.filter_by(id=client_id, salon_id=s.id).first_or_404()

    if request.method == "POST":
        item.name = request.form.get("name", "").strip()
        item.phone = request.form.get("phone", "").strip()
        item.email = request.form.get("email", "").strip()
        item.notes = request.form.get("notes", "").strip()
        db.session.commit()
        flash("Cliente atualizado.", "success")
        return redirect(url_for("dashboard.clients"))

    return render_template("dashboard/client_form.html", client=item, form={})


# ---------- Agendamentos ----------

@dashboard_bp.route("/agendamentos")
@login_required
def appointments():
    s = salon()
    date_str = request.args.get("date")
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date_cls.today()
    except ValueError:
        selected_date = date_cls.today()

    items = (
        Appointment.query.filter_by(salon_id=s.id, date=selected_date)
        .order_by(Appointment.start_time)
        .all()
    )
    return render_template(
        "dashboard/appointments.html",
        appointments=items,
        selected_date=selected_date,
        prev_date=selected_date - timedelta(days=1),
        next_date=selected_date + timedelta(days=1),
    )


@dashboard_bp.route("/agendamentos/<int:appt_id>/status", methods=["POST"])
@login_required
def appointment_status(appt_id):
    s = salon()
    item = Appointment.query.filter_by(id=appt_id, salon_id=s.id).first_or_404()
    new_status = request.form.get("status")
    if new_status in ("confirmado", "concluido", "cancelado"):
        item.status = new_status
        db.session.commit()
        flash("Status atualizado.", "success")
    return redirect(url_for("dashboard.appointments", date=item.date.isoformat()))


# ---------- Configurações ----------

@dashboard_bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
def settings():
    s = salon()

    if request.method == "POST":
        hours = {}
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            hours[day] = {
                "open": request.form.get(f"{day}_open", "09:00"),
                "close": request.form.get(f"{day}_close", "18:00"),
                "closed": request.form.get(f"{day}_closed") == "on",
            }
        s.working_hours = hours
        s.name = request.form.get("name", s.name).strip() or s.name
        s.phone = request.form.get("phone", s.phone)
        s.address = request.form.get("address", "").strip()
        s.instagram = request.form.get("instagram", "").strip()
        s.whatsapp = request.form.get("whatsapp", "").strip()

        photo = request.files.get("profile_photo")
        if photo and photo.filename:
            error = save_profile_photo(s, photo)
            if error:
                flash(error, "danger")
                return redirect(url_for("dashboard.settings"))

        if request.form.get("remove_photo") == "on":
            remove_profile_photo(s)

        db.session.commit()
        flash("Configurações salvas.", "success")
        return redirect(url_for("dashboard.settings"))

    return render_template("dashboard/settings.html", salon=s)
