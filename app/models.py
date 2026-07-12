import json
import secrets
import string
from datetime import datetime, date as date_cls

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def gen_slug_suffix(n=4):
    return "".join(secrets.choice(string.digits) for _ in range(n))


class Salon(db.Model):
    __tablename__ = "salons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    plan = db.Column(db.String(20), default="starter", nullable=False)
    working_hours_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Perfil público exibido na página de agendamento
    address = db.Column(db.String(255))
    instagram = db.Column(db.String(255))
    whatsapp = db.Column(db.String(30))
    profile_photo = db.Column(db.String(255))  # nome do arquivo salvo em uploads

    users = db.relationship("User", backref="salon", lazy=True, cascade="all, delete-orphan")
    services = db.relationship("Service", backref="salon", lazy=True, cascade="all, delete-orphan")
    clients = db.relationship("Client", backref="salon", lazy=True, cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", backref="salon", lazy=True, cascade="all, delete-orphan")

    @property
    def working_hours(self):
        try:
            return json.loads(self.working_hours_json) if self.working_hours_json else {}
        except (ValueError, TypeError):
            return {}

    @working_hours.setter
    def working_hours(self, value):
        self.working_hours_json = json.dumps(value)

    @property
    def instagram_url(self):
        """Aceita @usuario, usuario ou link completo e sempre devolve uma URL válida."""
        value = (self.instagram or "").strip()
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return value
        handle = value.lstrip("@")
        return f"https://instagram.com/{handle}"

    @property
    def instagram_handle(self):
        value = (self.instagram or "").strip()
        if not value:
            return None
        if "instagram.com" in value:
            handle = value.rstrip("/").split("/")[-1]
        else:
            handle = value.lstrip("@")
        return f"@{handle}" if handle else None

    @property
    def whatsapp_url(self):
        """Monta o link wa.me a partir do whatsapp (ou telefone, como reserva)."""
        raw = (self.whatsapp or self.phone or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            return None
        if len(digits) <= 11:  # número sem DDI -> assume Brasil
            digits = "55" + digits
        message = f"Olá! Vi a página do {self.name} e quero saber mais."
        from urllib.parse import quote
        return f"https://wa.me/{digits}?text={quote(message)}"

    def appointments_this_month(self):
        today = date_cls.today()
        start = today.replace(day=1)
        return Appointment.query.filter(
            Appointment.salon_id == self.id,
            Appointment.date >= start,
            Appointment.status != "cancelado",
        ).count()

    def plan_limits(self, plans_config):
        return plans_config.get(self.plan, plans_config["starter"])


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey("salons.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="owner")  # owner | staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey("salons.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    duration_min = db.Column(db.Integer, nullable=False, default=30)
    price = db.Column(db.Float, nullable=False, default=0.0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="service", lazy=True)


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey("salons.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship("Appointment", backref="client", lazy=True)


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    salon_id = db.Column(db.Integer, db.ForeignKey("salons.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    professional = db.Column(db.String(120))  # nome do profissional (simplificado)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default="confirmado")  # confirmado | concluido | cancelado
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
