"""Migra uma instalação existente do SalonPro sem apagar dados.

Inclui:
- perfil público/tema/trial do salão;
- profissionais e vínculo profissional x serviço;
- professional_id nos agendamentos;
- profissional padrão para salões antigos, preservando o fluxo atual.

Uso: python migrate.py
"""
from datetime import datetime, timedelta

from sqlalchemy import inspect, text

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import Salon, Service, Professional, Appointment

app = create_app()

SALON_COLUMNS = {
    "address": "VARCHAR(255)",
    "instagram": "VARCHAR(255)",
    "whatsapp": "VARCHAR(30)",
    "profile_photo": "VARCHAR(255)",
    "theme": "VARCHAR(20) DEFAULT 'feminino'",
    "trial_ends_at": "DATETIME",
    "subscription_status": "VARCHAR(30) DEFAULT 'trial'",
    "subscription_ends_at": "DATETIME",
}

CLIENT_COLUMNS = {
    "password_hash": "VARCHAR(255)",
    "portal_active": "BOOLEAN DEFAULT 0 NOT NULL",
}

APPOINTMENT_COLUMNS = {
    "professional_id": "INTEGER NULL",
    "payment_status": "VARCHAR(20) DEFAULT 'pendente' NOT NULL",
    "payment_method": "VARCHAR(30)",
    "paid_amount": "FLOAT",
    "paid_at": "DATETIME",
}

with app.app_context():
    inspector = inspect(db.engine)
    preexisting_tables = set(inspector.get_table_names())
    preexisting_appointment_columns = ({col["name"] for col in inspector.get_columns("appointments")} if "appointments" in preexisting_tables else set())
    is_plan_v3_upgrade = "payment_status" not in preexisting_appointment_columns

    # create_all já cria as tabelas novas (professionals e professional_services)
    # sem apagar ou alterar as tabelas existentes.
    db.create_all()
    inspector = inspect(db.engine)

    salon_columns = {col["name"] for col in inspector.get_columns("salons")}
    client_columns = {col["name"] for col in inspector.get_columns("clients")}
    appointment_columns = {col["name"] for col in inspector.get_columns("appointments")}

    added = []
    with db.engine.begin() as conn:
        for column, col_type in SALON_COLUMNS.items():
            if column not in salon_columns:
                conn.execute(text(f"ALTER TABLE salons ADD COLUMN {column} {col_type}"))
                added.append(f"salons.{column}")
        for column, col_type in CLIENT_COLUMNS.items():
            if column not in client_columns:
                conn.execute(text(f"ALTER TABLE clients ADD COLUMN {column} {col_type}"))
                added.append(f"clients.{column}")
        for column, col_type in APPOINTMENT_COLUMNS.items():
            if column not in appointment_columns:
                conn.execute(text(f"ALTER TABLE appointments ADD COLUMN {column} {col_type}"))
                added.append(f"appointments.{column}")

    if added:
        print("Colunas adicionadas:", ", ".join(added))
    else:
        print("Estrutura de colunas já estava atualizada.")

    # Converte os nomes da versão anterior apenas na primeira migração para esta estrutura.
    # v2: essencial=29,90 / pro=59,90 / premium=119,90
    # v3: basic=29,90 / premium=59,90 / pro=99,90
    if is_plan_v3_upgrade:
        legacy_map = {"essencial": "basic", "pro": "premium", "premium": "pro"}
        for salon in Salon.query.all():
            if salon.plan in legacy_map:
                salon.plan = legacy_map[salon.plan]

    # Preenche trial em salões antigos.
    salons_without_trial = Salon.query.filter(Salon.trial_ends_at.is_(None)).all()
    for salon in salons_without_trial:
        salon.trial_ends_at = datetime.utcnow() + timedelta(days=Config.TRIAL_DAYS)

    # Garante pelo menos um profissional para cada salão antigo e associa
    # todos os serviços existentes a ele, para não quebrar links já publicados.
    created_professionals = 0
    linked_services = 0
    for salon in Salon.query.all():
        professional = Professional.query.filter_by(salon_id=salon.id).order_by(Professional.id).first()
        if not professional:
            owner = next((u for u in salon.users if u.role == "owner"), salon.users[0] if salon.users else None)
            professional = Professional(
                salon_id=salon.id,
                name=owner.name if owner else "Equipe do salão",
                email=owner.email if owner else salon.email,
                phone=salon.phone,
                specialty="Atendimento",
                active=True,
            )
            professional.working_hours = salon.working_hours or Config.DEFAULT_WORKING_HOURS
            db.session.add(professional)
            db.session.flush()
            created_professionals += 1

        for service in Service.query.filter_by(salon_id=salon.id).all():
            if not service.professionals:
                service.professionals.append(professional)
                linked_services += 1

        # Agendamentos antigos não tinham professional_id. Tenta respeitar o nome
        # legado e, se não houver correspondência, usa o profissional padrão.
        salon_professionals = Professional.query.filter_by(salon_id=salon.id).all()
        by_name = {p.name.strip().lower(): p for p in salon_professionals if p.name}
        for appointment in Appointment.query.filter_by(salon_id=salon.id, professional_id=None).all():
            legacy_name = (appointment.professional or "").strip().lower()
            target = by_name.get(legacy_name) if legacy_name else None
            appointment.professional_id = (target or professional).id

    migrated_appointments = Appointment.query.filter(Appointment.professional_id.isnot(None)).count()
    db.session.commit()
    print(f"Profissionais padrão criados: {created_professionals}")
    print(f"Serviços vinculados automaticamente: {linked_services}")
    print(f"Agendamentos com profissional associado: {migrated_appointments}")
    print("Migração concluída com sucesso.")
