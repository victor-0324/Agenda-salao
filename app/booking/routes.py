from datetime import datetime, date as date_cls, timedelta, time as time_cls

from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
    send_from_directory, current_app,
)

from app.extensions import db
from app.models import Salon, Service, Client, Appointment
from app.config import Config

booking_bp = Blueprint("booking", __name__)

WEEKDAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def get_salon_or_404(slug):
    salon = Salon.query.filter_by(slug=slug).first()
    if not salon:
        abort(404)
    return salon


@booking_bp.route("/midia/<path:filename>")
def media(filename):
    """Serve fotos de perfil enviadas pelos salões (funciona com qualquer UPLOAD_FOLDER)."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


def time_to_minutes(t):
    return t.hour * 60 + t.minute


def minutes_to_time(m):
    return time_cls(hour=(m // 60) % 24, minute=m % 60)


def available_slots(salon, service, target_date):
    day_code = WEEKDAY_CODES[target_date.weekday()]
    hours = salon.working_hours.get(day_code)
    if not hours or hours.get("closed"):
        return []

    try:
        open_h, open_m = map(int, hours["open"].split(":"))
        close_h, close_m = map(int, hours["close"].split(":"))
    except (KeyError, ValueError):
        return []

    open_min = open_h * 60 + open_m
    close_min = close_h * 60 + close_m
    duration = service.duration_min

    existing = Appointment.query.filter_by(salon_id=salon.id, date=target_date).filter(
        Appointment.status != "cancelado"
    ).all()
    busy_ranges = [(time_to_minutes(a.start_time), time_to_minutes(a.end_time)) for a in existing]

    now = datetime.now()
    is_today = target_date == date_cls.today()

    slots = []
    step = 15  # granularidade dos horários exibidos
    cursor = open_min
    while cursor + duration <= close_min:
        slot_start, slot_end = cursor, cursor + duration
        overlaps = any(slot_start < b_end and slot_end > b_start for b_start, b_end in busy_ranges)
        in_the_past = is_today and (target_date == date_cls.today()) and (
            cursor <= now.hour * 60 + now.minute
        )
        if not overlaps and not in_the_past:
            slots.append(minutes_to_time(slot_start))
        cursor += step
    return slots


@booking_bp.route("/<slug>")
def salon_page(slug):
    salon = get_salon_or_404(slug)
    services = Service.query.filter_by(salon_id=salon.id, active=True).order_by(Service.name).all()
    return render_template("booking/salon.html", salon=salon, services=services)


@booking_bp.route("/<slug>/servico/<int:service_id>", methods=["GET", "POST"])
def schedule(slug, service_id):
    salon = get_salon_or_404(slug)
    service = Service.query.filter_by(id=service_id, salon_id=salon.id, active=True).first_or_404()

    date_str = request.args.get("date")
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date_cls.today()
    except ValueError:
        selected_date = date_cls.today()

    min_date = date_cls.today()
    max_date = min_date + timedelta(days=30)
    if selected_date < min_date:
        selected_date = min_date
    if selected_date > max_date:
        selected_date = max_date

    next_days = [min_date + timedelta(days=i) for i in range(14)]
    slots = available_slots(salon, service, selected_date)

    if request.method == "POST":
        limits = Config.PLANS.get(salon.plan, Config.PLANS["starter"])
        if salon.appointments_this_month() >= limits["max_appointments_month"]:
            flash("Este salão atingiu o limite de agendamentos do período. Tente falar diretamente com o salão.", "danger")
            return redirect(url_for("booking.schedule", slug=slug, service_id=service_id, date=selected_date.isoformat()))

        start_str = request.form.get("start_time")
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        if not name or not phone or not start_str:
            flash("Preencha nome, telefone e escolha um horário.", "danger")
            return redirect(url_for("booking.schedule", slug=slug, service_id=service_id, date=selected_date.isoformat()))

        try:
            h, m = map(int, start_str.split(":"))
        except ValueError:
            flash("Horário inválido.", "danger")
            return redirect(url_for("booking.schedule", slug=slug, service_id=service_id, date=selected_date.isoformat()))

        start_time = time_cls(hour=h, minute=m)
        # revalida disponibilidade (evita corrida entre dois clientes agendando ao mesmo tempo)
        still_free = any(s.hour == h and s.minute == m for s in available_slots(salon, service, selected_date))
        if not still_free:
            flash("Esse horário acabou de ser reservado por outra pessoa. Escolha outro.", "warning")
            return redirect(url_for("booking.schedule", slug=slug, service_id=service_id, date=selected_date.isoformat()))

        end_minutes = start_time.hour * 60 + start_time.minute + service.duration_min
        end_time = minutes_to_time(end_minutes)

        client = Client.query.filter_by(salon_id=salon.id, phone=phone).first()
        if not client:
            client = Client(salon_id=salon.id, name=name, phone=phone, email=email)
            db.session.add(client)
            db.session.flush()
        else:
            client.name = name
            if email:
                client.email = email

        appt = Appointment(
            salon_id=salon.id,
            service_id=service.id,
            client_id=client.id,
            date=selected_date,
            start_time=start_time,
            end_time=end_time,
            status="confirmado",
        )
        db.session.add(appt)
        db.session.commit()

        return redirect(
            url_for(
                "booking.confirmed",
                slug=slug,
                appt_id=appt.id,
            )
        )

    return render_template(
        "booking/schedule.html",
        salon=salon,
        service=service,
        selected_date=selected_date,
        next_days=next_days,
        slots=slots,
    )


@booking_bp.route("/<slug>/confirmado/<int:appt_id>")
def confirmed(slug, appt_id):
    salon = get_salon_or_404(slug)
    appt = Appointment.query.filter_by(id=appt_id, salon_id=salon.id).first_or_404()
    return render_template("booking/confirm.html", salon=salon, appt=appt)
