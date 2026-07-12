"""Adiciona as colunas novas (perfil público do salão) num banco já existente,
sem apagar nenhum dado. Seguro rodar mais de uma vez.

Uso: python migrate.py
"""
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db

app = create_app()

NEW_COLUMNS = {
    "address": "VARCHAR(255)",
    "instagram": "VARCHAR(255)",
    "whatsapp": "VARCHAR(30)",
    "profile_photo": "VARCHAR(255)",
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
