from datetime import datetime, date as date_cls, timedelta, time as time_cls

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, abort

from app.extensions import db
from app.models import Salon, Client, Appointment, Professional, Service, Review
from app.config import Config
from app.booking.routes import available_slots, minutes_to_time

client_bp = Blueprint("client", __name__, url_prefix="/cliente")


def _salon(slug):
    salon = Salon.query.filter_by(slug=slug).first_or_404()
    if not Config.PLANS.get(salon.plan, {}).get("client_area"):
        abort(404)
    return salon


def _client(salon):
    client_id = session.get("client_portal_id")
    salon_id = session.get("client_portal_salon_id")
    if not client_id or salon_id != salon.id:
        return None
    return Client.query.filter_by(id=client_id, salon_id=salon.id, portal_active=True).first()


def _require_client(salon):
    client = _client(salon)
    if not client:
        flash("Entre na área do cliente para continuar.", "warning")
        return None
    return client


@client_bp.route("/<slug>/entrar", methods=["GET", "POST"])
def login(slug):
    salon = _salon(slug)
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        client = Client.query.filter_by(salon_id=salon.id, phone=phone).first()
        if client and client.portal_active and client.check_password(password):
            session["client_portal_id"] = client.id
            session["client_portal_salon_id"] = salon.id
            return redirect(url_for("client.home", slug=slug))
        flash("Telefone ou senha inválidos.", "danger")
    return render_template("client/login.html", salon=salon)


@client_bp.route("/<slug>/ativar", methods=["GET", "POST"])
def activate(slug):
    salon = _salon(slug)
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        client = Client.query.filter_by(salon_id=salon.id, phone=phone).first()
        if not client:
            flash("Não encontramos agendamentos com esse telefone.", "danger")
        elif len(password) < 6:
            flash("A senha precisa ter pelo menos 6 caracteres.", "danger")
        elif password != password2:
            flash("As senhas não conferem.", "danger")
        else:
            client.set_password(password)
            db.session.commit()
            session["client_portal_id"] = client.id
            session["client_portal_salon_id"] = salon.id
            flash("Área do cliente ativada.", "success")
            return redirect(url_for("client.home", slug=slug))
    return render_template("client/activate.html", salon=salon)


@client_bp.route("/<slug>/sair")
def logout(slug):
    session.pop("client_portal_id", None)
    session.pop("client_portal_salon_id", None)
    flash("Você saiu da área do cliente.", "info")
    return redirect(url_for("client.login", slug=slug))


@client_bp.route("/<slug>")
def home(slug):
    salon = _salon(slug)
    client = _require_client(salon)
    if not client:
        return redirect(url_for("client.login", slug=slug))
    appointments = (
        Appointment.query.filter_by(salon_id=salon.id, client_id=client.id)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )
    return render_template("client/home.html", salon=salon, client=client, appointments=appointments, today=date_cls.today())


@client_bp.route("/<slug>/agendamento/<int:appt_id>/cancelar", methods=["POST"])
def cancel(slug, appt_id):
    salon = _salon(slug)
    client = _require_client(salon)
    if not client:
        return redirect(url_for("client.login", slug=slug))
    appt = Appointment.query.filter_by(id=appt_id, salon_id=salon.id, client_id=client.id).first_or_404()
    if appt.status == "concluido" or appt.date < date_cls.today():
        flash("Esse atendimento não pode mais ser cancelado pela área do cliente.", "warning")
    else:
        appt.status = "cancelado"
        db.session.commit()
        flash("Agendamento cancelado.", "success")
    return redirect(url_for("client.home", slug=slug))


@client_bp.route("/<slug>/agendamento/<int:appt_id>/remarcar", methods=["GET", "POST"])
def reschedule(slug, appt_id):
    salon = _salon(slug)
    client = _require_client(salon)
    if not client:
        return redirect(url_for("client.login", slug=slug))
    appt = Appointment.query.filter_by(id=appt_id, salon_id=salon.id, client_id=client.id).first_or_404()
    if appt.status in ("concluido", "cancelado") or appt.date < date_cls.today():
        flash("Esse atendimento não pode ser remarcado.", "warning")
        return redirect(url_for("client.home", slug=slug))

    professional = appt.professional_ref
    selected_date_str = request.values.get("date")
    try:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date() if selected_date_str else appt.date
    except ValueError:
        selected_date = appt.date
    min_date = date_cls.today()
    max_date = min_date + timedelta(days=30)
    selected_date = max(min_date, min(selected_date, max_date))
    slots = available_slots(salon, appt.service, selected_date, professional, exclude_appointment_id=appt.id)

    if request.method == "POST":
        start_str = request.form.get("start_time", "")
        try:
            h, m = map(int, start_str.split(":"))
        except ValueError:
            flash("Escolha um horário válido.", "danger")
            return redirect(url_for("client.reschedule", slug=slug, appt_id=appt.id, date=selected_date.isoformat()))
        if not any(slot.hour == h and slot.minute == m for slot in slots):
            flash("Esse horário não está mais disponível.", "warning")
            return redirect(url_for("client.reschedule", slug=slug, appt_id=appt.id, date=selected_date.isoformat()))
        appt.date = selected_date
        appt.start_time = time_cls(h, m)
        appt.end_time = minutes_to_time(h * 60 + m + appt.service.duration_min)
        appt.status = "confirmado"
        db.session.commit()
        flash("Agendamento remarcado com sucesso.", "success")
        return redirect(url_for("client.home", slug=slug))

    dates = [min_date + timedelta(days=i) for i in range(14)]
    return render_template("client/reschedule.html", salon=salon, client=client, appt=appt, selected_date=selected_date, dates=dates, slots=slots)


@client_bp.route("/<slug>/agendamento/<int:appt_id>/avaliar", methods=["GET", "POST"])
def review(slug, appt_id):
    salon = _salon(slug)
    if not Config.PLANS.get(salon.plan, {}).get("reviews"):
        abort(404)
    client = _require_client(salon)
    if not client:
        return redirect(url_for("client.login", slug=slug))
    appt = Appointment.query.filter_by(id=appt_id, salon_id=salon.id, client_id=client.id).first_or_404()
    if appt.status != "concluido":
        flash("A avaliação é liberada depois que o serviço for concluído.", "warning")
        return redirect(url_for("client.home", slug=slug))
    if appt.review:
        flash("Esse atendimento já foi avaliado.", "info")
        return redirect(url_for("client.home", slug=slug))
    if request.method == "POST":
        rating = request.form.get("rating", type=int)
        comment = request.form.get("comment", "").strip()
        if rating not in range(1, 6):
            flash("Escolha uma nota de 1 a 5.", "danger")
        else:
            item = Review(
                salon_id=salon.id,
                appointment_id=appt.id,
                client_id=client.id,
                professional_id=appt.professional_id,
                rating=rating,
                comment=comment,
            )
            db.session.add(item)
            db.session.commit()
            flash("Obrigado pela avaliação!", "success")
            return redirect(url_for("client.home", slug=slug))
    return render_template("client/review.html", salon=salon, client=client, appt=appt)
