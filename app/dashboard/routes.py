import os
import uuid
from datetime import datetime, date as date_cls, timedelta

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Service, Client, Appointment, Salon, Professional, Review
from app.config import Config

dashboard_bp = Blueprint("dashboard", __name__)


def salon():
    """Salão (tenant) do usuário logado."""
    return Salon.query.get(current_user.salon_id)


def plan_limits():
    s = salon()
    return Config.PLANS.get(s.plan, Config.PLANS["basic"])


@dashboard_bp.context_processor
def inject_trial_status():
    """Disponibiliza informações do plano e do período de teste."""
    if not current_user.is_authenticated:
        return {}

    s = salon()
    limits = plan_limits()
    used = s.appointments_this_month()
    limit = limits.get("max_appointments_month")
    percent = round(min(100, (used / limit) * 100)) if limit else 0

    # Teste grátis de 7 dias
    trial_days = 7
    dias_desde_criacao = (datetime.utcnow() - s.created_at).days
    trial_ativo = dias_desde_criacao < trial_days
    dias_restantes = max(0, trial_days - dias_desde_criacao)

    return {
        "trial_salon": s,
        "trial_ativo": trial_ativo,
        "dias_restantes_trial": dias_restantes,
        "sidebar_plan": {
            "label": limits["label"],
            "used": used,
            "limit": limit,
            "percent": percent,
            "financial": limits.get("financial", False),
            "reviews": limits.get("reviews", False),
            "client_area": limits.get("client_area", False),
        },
    }


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

def obter_saudacao():
    hora = datetime.now().hour

    if 5 <= hora < 12:
        return "☀️ Bom dia"
    elif 12 <= hora < 18:
        return "🌤️ Boa tarde"
    else:
        return "🌙 Boa noite"

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
    total_professionals = Professional.query.filter_by(salon_id=s.id, active=True).count()
    used_this_month = s.appointments_this_month()
    limits = plan_limits()

    upcoming_appts = (
        Appointment.query.filter(
            Appointment.salon_id == s.id,
            Appointment.date >= today,
            Appointment.status != "cancelado",
        )
        .order_by(Appointment.date, Appointment.start_time)
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        salon=s,
        today_appts=today_appts,
        upcoming_count=upcoming_count,
        upcoming_appts=upcoming_appts,
        total_clients=total_clients,
        total_professionals=total_professionals,
        used_this_month=used_this_month,
        limits=limits,
        saudacao=obter_saudacao(),
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
    professionals = Professional.query.filter_by(salon_id=s.id, active=True).order_by(Professional.name).all()

    max_services = limits.get("max_services")
    if max_services is not None and current_count >= max_services:
        flash(
            f"Seu plano {limits['label']} permite até {max_services} serviços. "
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
            return render_template("dashboard/service_form.html", service=None, form=request.form, professionals=professionals, salon=current_user.salon,
    trial_salon=current_user.salon)

        item = Service(salon_id=s.id, name=name, duration_min=duration, price=price, active=True)
        selected_ids = {int(v) for v in request.form.getlist("professional_ids") if str(v).isdigit()}
        if not limits.get("can_add_professionals") and professionals:
            item.professionals = [professionals[0]]
        else:
            item.professionals = [p for p in professionals if p.id in selected_ids]
        db.session.add(item)
        db.session.commit()
        flash("Serviço cadastrado.", "success")
        return redirect(url_for("dashboard.services"))

    return render_template("dashboard/service_form.html",salon=current_user.salon,
    trial_salon=current_user.salon, service=None, form={}, professionals=professionals)


@dashboard_bp.route("/servicos/<int:service_id>/editar", methods=["GET", "POST"])
@login_required
def service_edit(service_id):
    s = salon()
    limits = plan_limits()
    item = Service.query.filter_by(id=service_id, salon_id=s.id).first_or_404()
    professionals = Professional.query.filter_by(salon_id=s.id, active=True).order_by(Professional.name).all()

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
            return render_template("dashboard/service_form.html", service=item, form=request.form, professionals=professionals, salon=current_user.salon,
    trial_salon=current_user.salon)

        item.name, item.duration_min, item.price, item.active = name, duration, price, active
        selected_ids = {int(v) for v in request.form.getlist("professional_ids") if str(v).isdigit()}
        if not limits.get("can_add_professionals") and professionals:
            item.professionals = [professionals[0]]
        else:
            item.professionals = [p for p in professionals if p.id in selected_ids]
        db.session.commit()
        flash("Serviço atualizado.", "success")
        return redirect(url_for("dashboard.services"))

    return render_template("dashboard/service_form.html", service=item, form={}, professionals=professionals, salon=current_user.salon,
    trial_salon=current_user.salon)


@dashboard_bp.route("/servicos/<int:service_id>/excluir", methods=["POST"])
@login_required
def service_delete(service_id):
    s = salon()
    item = Service.query.filter_by(id=service_id, salon_id=s.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Serviço removido.", "info")
    return redirect(url_for("dashboard.services"))


# ---------- Profissionais ----------

@dashboard_bp.route("/profissionais")
@login_required
def professionals():
    s = salon()
    items = Professional.query.filter_by(salon_id=s.id).order_by(Professional.name).all()
    return render_template(
        "dashboard/professionals.html",
        professionals=items,
        salon=s,
        limits=plan_limits(),
        trial_salon=s,
    )


def _professional_hours_from_form(s):
    hours = {}
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        hours[day] = {
            "open": request.form.get(f"{day}_open", "09:00"),
            "close": request.form.get(f"{day}_close", "18:00"),
            "closed": request.form.get(f"{day}_closed") == "on",
        }
    return hours


@dashboard_bp.route("/profissionais/novo", methods=["GET", "POST"])
@login_required
def professional_new():
    s = salon()
    limits = plan_limits()
    current_count = Professional.query.filter_by(salon_id=s.id, active=True).count()
    if not limits.get("can_add_professionals", False):
        flash(f"O plano {limits['label']} não permite adicionar profissionais. Faça upgrade para Premium ou Pro.", "warning")
        return redirect(url_for("dashboard.professionals"))
    if current_count >= limits["max_professionals"]:
        flash(
            f"Seu plano {limits['label']} permite até {limits['max_professionals']} profissional(is). Faça upgrade para ampliar a equipe.",
            "warning",
        )
        return redirect(url_for("dashboard.professionals"))

    services = Service.query.filter_by(salon_id=s.id, active=True).order_by(Service.name).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Informe o nome do profissional.", "danger")
            return render_template("dashboard/professional_form.html", professional=None, services=services, salon=s, trial_salon=s)

        item = Professional(
            salon_id=s.id,
            name=name,
            phone=request.form.get("phone", "").strip(),
            email=request.form.get("email", "").strip(),
            specialty=request.form.get("specialty", "").strip(),
            active=True,
        )
        item.working_hours = _professional_hours_from_form(s)
        selected_ids = {int(v) for v in request.form.getlist("service_ids") if str(v).isdigit()}
        item.services = [service for service in services if service.id in selected_ids]
        db.session.add(item)
        db.session.commit()
        flash("Profissional cadastrado com agenda própria.", "success")
        return redirect(url_for("dashboard.professionals"))

    return render_template("dashboard/professional_form.html", professional=None, services=services, salon=s, trial_salon=s)


@dashboard_bp.route("/profissionais/<int:professional_id>/editar", methods=["GET", "POST"])
@login_required
def professional_edit(professional_id):
    s = salon()
    item = Professional.query.filter_by(id=professional_id, salon_id=s.id).first_or_404()
    services = Service.query.filter_by(salon_id=s.id, active=True).order_by(Service.name).all()

    if request.method == "POST":
        item.name = request.form.get("name", "").strip() or item.name
        item.phone = request.form.get("phone", "").strip()
        item.email = request.form.get("email", "").strip()
        item.specialty = request.form.get("specialty", "").strip()
        item.active = request.form.get("active") == "on"
        item.working_hours = _professional_hours_from_form(s)
        selected_ids = {int(v) for v in request.form.getlist("service_ids") if str(v).isdigit()}
        item.services = [service for service in services if service.id in selected_ids]
        db.session.commit()
        flash("Profissional atualizado.", "success")
        return redirect(url_for("dashboard.professionals"))

    return render_template("dashboard/professional_form.html", professional=item, services=services, salon=s, trial_salon=s)


@dashboard_bp.route("/profissionais/<int:professional_id>/excluir", methods=["POST"])
@login_required
def professional_delete(professional_id):
    s = salon()
    limits = plan_limits()
    item = Professional.query.filter_by(id=professional_id, salon_id=s.id).first_or_404()
    if not limits.get("can_add_professionals"):
        flash("O profissional principal do plano Basic não pode ser removido. Você pode editar nome, serviços e horários.", "warning")
        return redirect(url_for("dashboard.professionals"))
    appointment_count = Appointment.query.filter(
        Appointment.professional_id == item.id
    ).count()
    if appointment_count:
        item.active = False
        db.session.commit()
        flash("Profissional inativado para preservar o histórico de agendamentos.", "warning")
    else:
        db.session.delete(item)
        db.session.commit()
        flash("Profissional removido.", "info")
    return redirect(url_for("dashboard.professionals"))


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
    return render_template("dashboard/clients.html", clients=items, q=q, salon=current_user.salon,
    trial_salon=current_user.salon)


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

    return render_template("dashboard/client_form.html", client=None, form={}, salon=current_user.salon,
    trial_salon=current_user.salon)


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

    return render_template("dashboard/client_form.html", client=item, form={}, salon=current_user.salon,
    trial_salon=current_user.salon)


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

    professional_id = request.args.get("professional_id", type=int)
    query = Appointment.query.filter_by(salon_id=s.id, date=selected_date)
    if professional_id:
        query = query.filter(Appointment.professional_id == professional_id)
    items = query.order_by(Appointment.start_time).all()
    professionals = Professional.query.filter_by(salon_id=s.id, active=True).order_by(Professional.name).all()
    return render_template(
        "dashboard/appointments.html",
        appointments=items,
        selected_date=selected_date,
        prev_date=selected_date - timedelta(days=1),
        next_date=selected_date + timedelta(days=1),
        professionals=professionals,
        selected_professional_id=professional_id,
        salon=current_user.salon,
        trial_salon=current_user.salon
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


# ---------- Financeiro (Premium e Pro) ----------

def _feature_enabled(feature):
    return bool(plan_limits().get(feature))


def _feature_block(feature, label):
    if _feature_enabled(feature):
        return None
    flash(f"{label} não está disponível no seu plano atual. Faça upgrade para acessar.", "warning")
    return redirect(url_for("main.pricing"))


@dashboard_bp.route("/financeiro")
@login_required
def financial():
    blocked = _feature_block("financial", "A área financeira")
    if blocked:
        return blocked
    s = salon()
    month = request.args.get("month")
    try:
        selected = datetime.strptime(month, "%Y-%m").date() if month else date_cls.today().replace(day=1)
    except ValueError:
        selected = date_cls.today().replace(day=1)
    next_month = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)

    items = Appointment.query.filter(
        Appointment.salon_id == s.id,
        Appointment.date >= selected,
        Appointment.date < next_month,
        Appointment.status != "cancelado",
    ).order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()

    received = sum((a.paid_amount if a.paid_amount is not None else a.service.price) for a in items if a.payment_status == "pago")
    pending = sum(a.service.price for a in items if a.payment_status != "pago")
    paid_count = sum(1 for a in items if a.payment_status == "pago")
    by_method = {}
    for a in items:
        if a.payment_status == "pago":
            method = a.payment_method or "Não informado"
            by_method[method] = by_method.get(method, 0) + (a.paid_amount if a.paid_amount is not None else a.service.price)

    return render_template(
        "dashboard/financial.html", salon=s, trial_salon=s, items=items,
        selected_month=selected, received=received, pending=pending,
        paid_count=paid_count, by_method=by_method,
    )


@dashboard_bp.route("/financeiro/agendamento/<int:appt_id>/pagamento", methods=["POST"])
@login_required
def appointment_payment(appt_id):
    blocked = _feature_block("financial", "A área financeira")
    if blocked:
        return blocked
    s = salon()
    item = Appointment.query.filter_by(id=appt_id, salon_id=s.id).first_or_404()
    status = request.form.get("payment_status", "pendente")
    if status not in ("pendente", "pago"):
        status = "pendente"
    item.payment_status = status
    if status == "pago":
        raw_amount = request.form.get("paid_amount", "").strip().replace(",", ".")
        try:
            item.paid_amount = float(raw_amount) if raw_amount else item.service.price
        except ValueError:
            item.paid_amount = item.service.price
        item.payment_method = request.form.get("payment_method", "").strip() or None
        item.paid_at = datetime.utcnow()
    else:
        item.paid_amount = None
        item.payment_method = None
        item.paid_at = None
    db.session.commit()
    flash("Pagamento atualizado.", "success")
    return redirect(request.referrer or url_for("dashboard.financial"))


@dashboard_bp.route("/financeiro/relatorio.csv")
@login_required
def financial_report():
    blocked = _feature_block("financial", "Os relatórios financeiros")
    if blocked:
        return blocked
    s = salon()
    month = request.args.get("month")
    try:
        selected = datetime.strptime(month, "%Y-%m").date() if month else date_cls.today().replace(day=1)
    except ValueError:
        selected = date_cls.today().replace(day=1)
    next_month = (selected.replace(day=28) + timedelta(days=4)).replace(day=1)
    items = Appointment.query.filter(
        Appointment.salon_id == s.id,
        Appointment.date >= selected,
        Appointment.date < next_month,
        Appointment.status != "cancelado",
    ).order_by(Appointment.date, Appointment.start_time).all()
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Data", "Cliente", "Serviço", "Profissional", "Status serviço", "Status pagamento", "Forma", "Valor"])
    for a in items:
        value = a.paid_amount if a.payment_status == "pago" and a.paid_amount is not None else a.service.price
        writer.writerow([
            a.date.strftime("%d/%m/%Y"), a.client.name, a.service.name, a.professional_name,
            a.status, a.payment_status, a.payment_method or "", f"{value:.2f}".replace(".", ",")
        ])
    content = "\ufeff" + output.getvalue()
    filename = f"financeiro-{s.slug}-{selected.strftime('%Y-%m')}.csv"
    return Response(content, mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename={filename}"})


# ---------- Avaliações (Pro) ----------

@dashboard_bp.route("/avaliacoes")
@login_required
def reviews():
    blocked = _feature_block("reviews", "A área de avaliações")
    if blocked:
        return blocked
    s = salon()
    items = Review.query.filter_by(salon_id=s.id).order_by(Review.created_at.desc()).all()
    average = (sum(r.rating for r in items) / len(items)) if items else 0
    professionals = Professional.query.filter_by(salon_id=s.id).all()
    professional_stats = []
    for p in professionals:
        reviews = [r for r in items if r.professional_id == p.id]
        if reviews:
            professional_stats.append({"professional": p, "count": len(reviews), "average": sum(r.rating for r in reviews) / len(reviews)})
    return render_template("dashboard/reviews.html", salon=s, trial_salon=s, reviews=items, average=average, professional_stats=professional_stats)


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

        theme = request.form.get("theme", s.theme)
        if theme in Config.THEMES:
            s.theme = theme

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
