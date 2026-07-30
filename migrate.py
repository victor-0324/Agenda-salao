"""Adiciona as colunas novas (perfil público do salão, tema visual e teste grátis)
num banco já existente, sem apagar nenhum dado. Seguro rodar mais de uma vez.

Uso: python migrate.py
"""
from datetime import datetime, timedelta

from sqlalchemy import inspect, text

from app import create_app
from app.config import Config
from app.extensions import db

app = create_app()

NEW_COLUMNS = {
    "address": "VARCHAR(255)",
    "instagram": "VARCHAR(255)",
    "whatsapp": "VARCHAR(30)",
    "profile_photo": "VARCHAR(255)",
    "theme": "VARCHAR(20) DEFAULT 'feminino'",
    "trial_ends_at": "DATETIME",
}

with app.app_context():
    inspector = inspect(db.engine)
    existing_columns = {col["name"] for col in inspector.get_columns("salons")}

    added = []
    with db.engine.begin() as conn:
        for column, col_type in NEW_COLUMNS.items():
            if column in existing_columns:
                continue
            conn.execute(text(f"ALTER TABLE salons ADD COLUMN {column} {col_type}"))
            added.append(column)

    if added:
        print(f"Colunas adicionadas em 'salons': {', '.join(added)}")
    else:
        print("Nada para migrar — todas as colunas já existem.")

    # Salões antigos, criados antes do controle de teste grátis existir, não tinham
    # trial_ends_at preenchido. Aqui damos a eles o benefício do teste completo a partir
    # de hoje, em vez de deixar trial_ends_at nulo (o que os deixaria com trial vitalício).
    with db.engine.begin() as conn:
        result = conn.execute(
            text("SELECT id, created_at FROM salons WHERE trial_ends_at IS NULL")
        ).fetchall()
        for row in result:
            trial_end = datetime.utcnow() + timedelta(days=Config.TRIAL_DAYS)
            conn.execute(
                text("UPDATE salons SET trial_ends_at = :trial_end WHERE id = :id"),
                {"trial_end": trial_end, "id": row[0]},
            )
        if result:
            print(f"trial_ends_at preenchido para {len(result)} salão(ões) existente(s).")
