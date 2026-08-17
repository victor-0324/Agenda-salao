import json
import secrets
import string
from datetime import datetime, date as date_cls, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def gen_slug_suffix(n=4):
    return "".join(secrets.choice(string.digits) for _ in range(n))


def parse_datetime(value):
    """
    Converte datas recebidas pela Kiwify/n8n para datetime.

    Exemplos aceitos:
    - 2026-08-17 11:15
    - 19/08/2026 11:14
    - 2026-08-17 11:15:00
    - 19/08/2026 11:14:00
    """
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    formatos = (
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    )

    for formato in formatos:
        try:
            return datetime.strptime(value, formato)
        except (ValueError, TypeError):
            continue

    return None


class Salon(db.Model):
    __tablename__ = "salons"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(120),
        nullable=False
    )

    slug = db.Column(
        db.String(140),
        unique=True,
        nullable=False,
        index=True
    )

    email = db.Column(
        db.String(120),
        nullable=False
    )

    phone = db.Column(
        db.String(30)
    )

    plan = db.Column(
        db.String(20),
        default="premium",
        nullable=False
    )

    working_hours_json = db.Column(
        db.Text,
        default="{}"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # =========================================================
    # VISUAL
    # =========================================================

    theme = db.Column(
        db.String(20),
        default="feminino",
        nullable=False
    )

    # =========================================================
    # TESTE GRÁTIS
    # =========================================================

    trial_ends_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # =========================================================
    # ASSINATURA
    # =========================================================

    subscription_status = db.Column(
        db.String(30),
        default="trial",
        nullable=False,
        index=True
    )

    subscription_ends_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # =========================================================
    # PERFIL PÚBLICO
    # =========================================================

    address = db.Column(
        db.String(255)
    )

    instagram = db.Column(
        db.String(255)
    )

    whatsapp = db.Column(
        db.String(30)
    )

    profile_photo = db.Column(
        db.String(255)
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================

    users = db.relationship(
        "User",
        backref="salon",
        lazy=True,
        cascade="all, delete-orphan"
    )

    services = db.relationship(
        "Service",
        backref="salon",
        lazy=True,
        cascade="all, delete-orphan"
    )

    clients = db.relationship(
        "Client",
        backref="salon",
        lazy=True,
        cascade="all, delete-orphan"
    )

    appointments = db.relationship(
        "Appointment",
        backref="salon",
        lazy=True,
        cascade="all, delete-orphan"
    )

    pagamentos = db.relationship(
        "Assinaturas",
        back_populates="salon",
        lazy=True,
        cascade="all, delete-orphan"
    )

    # =========================================================
    # HORÁRIOS
    # =========================================================

    @property
    def working_hours(self):
        try:
            return (
                json.loads(self.working_hours_json)
                if self.working_hours_json
                else {}
            )
        except (ValueError, TypeError):
            return {}

    @working_hours.setter
    def working_hours(self, value):
        self.working_hours_json = json.dumps(value)

    # =========================================================
    # INSTAGRAM
    # =========================================================

    @property
    def instagram_url(self):
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

    # =========================================================
    # WHATSAPP
    # =========================================================

    @property
    def whatsapp_url(self):
        raw = (
            self.whatsapp
            or self.phone
            or ""
        ).strip()

        digits = "".join(
            ch for ch in raw
            if ch.isdigit()
        )

        if not digits:
            return None

        if len(digits) <= 11:
            digits = "55" + digits

        message = (
            f"Olá! Vi a página do {self.name} "
            f"e quero saber mais."
        )

        from urllib.parse import quote

        return (
            f"https://wa.me/{digits}"
            f"?text={quote(message)}"
        )

    # =========================================================
    # AGENDAMENTOS
    # =========================================================

    def appointments_this_month(self):
        today = date_cls.today()
        start = today.replace(day=1)

        return Appointment.query.filter(
            Appointment.salon_id == self.id,
            Appointment.date >= start,
            Appointment.status != "cancelado",
        ).count()

    def plan_limits(self, plans_config):
        return plans_config.get(
            self.plan,
            plans_config["premium"]
        )

    # =========================================================
    # TESTE GRÁTIS
    # =========================================================

    @property
    def trial_days_left(self):
        if not self.trial_ends_at:
            return 0

        delta = (
            self.trial_ends_at
            - datetime.utcnow()
        )

        return max(
            0,
            delta.days + (
                1 if delta.seconds > 0 else 0
            )
        )

    @property
    def trial_total_days(self):
        if not self.trial_ends_at:
            return 0

        return max(
            1,
            (
                self.trial_ends_at
                - self.created_at
            ).days
        )

    @property
    def trial_percent_left(self):
        total = self.trial_total_days

        if not total:
            return 0

        return round(
            min(
                100,
                max(
                    0,
                    (
                        self.trial_days_left
                        / total
                    ) * 100
                )
            )
        )

    @property
    def is_trial_expired(self):
        if not self.trial_ends_at:
            return False

        return (
            datetime.utcnow()
            > self.trial_ends_at
        )

    # =========================================================
    # ASSINATURA ATIVA
    # =========================================================

    @property
    def is_subscription_active(self):
        """
        Retorna True somente se existir uma assinatura
        ativa e dentro da validade.
        """
        if self.subscription_status != "active":
            return False

        if not self.subscription_ends_at:
            return False

        return (
            self.subscription_ends_at
            > datetime.utcnow()
        )

    # =========================================================
    # ACESSO AO SISTEMA / AGENDAMENTO
    # =========================================================

    @property
    def is_booking_active(self):
        """
        O salão pode receber agendamentos quando:

        1. ainda está no período de teste; OU
        2. possui assinatura ativa e válida.
        """

        # Assinatura paga válida
        if self.is_subscription_active:
            return True

        # Teste grátis válido
        if (
            self.trial_ends_at
            and self.trial_ends_at
            > datetime.utcnow()
        ):
            return True

        return False


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="owner"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Service(db.Model):
    __tablename__ = "services"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    duration_min = db.Column(
        db.Integer,
        nullable=False,
        default=30
    )

    price = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    appointments = db.relationship(
        "Appointment",
        backref="service",
        lazy=True
    )


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    phone = db.Column(
        db.String(30),
        nullable=False
    )

    email = db.Column(
        db.String(120)
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    appointments = db.relationship(
        "Appointment",
        backref="client",
        lazy=True
    )


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False
    )

    service_id = db.Column(
        db.Integer,
        db.ForeignKey("services.id"),
        nullable=False
    )

    client_id = db.Column(
        db.Integer,
        db.ForeignKey("clients.id"),
        nullable=False
    )

    professional = db.Column(
        db.String(120)
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default="confirmado"
    )

    notes = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class Assinaturas(db.Model):
    __tablename__ = "pagamentos"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =========================================================
    # SALÃO
    # =========================================================

    salon_id = db.Column(
        db.Integer,
        db.ForeignKey("salons.id"),
        nullable=False,
        index=True
    )

    salon = db.relationship(
        "Salon",
        back_populates="pagamentos"
    )

    # =========================================================
    # KIWIIFY
    # =========================================================

    order_id = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True
    )

    order_ref = db.Column(
        db.String(100),
        nullable=True,
        index=True
    )

    # =========================================================
    # PRODUTO / PLANO
    # =========================================================

    product_id = db.Column(
        db.String(100),
        nullable=True
    )

    product_name = db.Column(
        db.String(255),
        nullable=True
    )

    plan = db.Column(
        db.String(50),
        nullable=True
    )

    # =========================================================
    # STATUS
    # =========================================================

    status = db.Column(
        db.String(50),
        nullable=False,
        default="waiting_payment",
        index=True
    )

    webhook_event = db.Column(
        db.String(100),
        nullable=True
    )

    # =========================================================
    # PAGAMENTO
    # =========================================================

    payment_method = db.Column(
        db.String(50),
        nullable=True
    )

    # Valores em centavos
    amount = db.Column(
        db.Integer,
        nullable=True
    )

    kiwify_fee = db.Column(
        db.Integer,
        nullable=True
    )

    net_amount = db.Column(
        db.Integer,
        nullable=True
    )

    # =========================================================
    # CLIENTE DA COMPRA
    # =========================================================

    customer_name = db.Column(
        db.String(150),
        nullable=True
    )

    customer_email = db.Column(
        db.String(150),
        nullable=True,
        index=True
    )

    customer_phone = db.Column(
        db.String(50),
        nullable=True
    )

    # =========================================================
    # PIX
    # =========================================================

    pix_code = db.Column(
        db.Text,
        nullable=True
    )

    pix_expiration = db.Column(
        db.DateTime,
        nullable=True
    )

    # =========================================================
    # DATAS
    # =========================================================

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    approved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    refunded_at = db.Column(
        db.DateTime,
        nullable=True
    )
