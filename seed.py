"""Cria um salão de demonstração para testar o sistema rapidamente.

Uso: python seed.py
Login de teste: demo@salao.com / 123456
Link público: /agendar/studio-bella-hair
"""
from app import create_app
from app.extensions import db
from app.models import Salon, User, Service
from app.config import Config

app = create_app()

with app.app_context():
    if Salon.query.filter_by(slug="studio-bella-hair").first():
        print("Salão demo já existe.")
    else:
        salon = Salon(
            name="Studio Bella Hair",
            slug="studio-bella-hair",
            email="demo@salao.com",
            phone="(11) 98888-7777",
            plan="pro",
            address="Rua das Flores, 123 — Jardim Paulista, São Paulo",
            instagram="@studiobellahair",
            whatsapp="(11) 98888-7777",
        )
        salon.working_hours = Config.DEFAULT_WORKING_HOURS
        db.session.add(salon)
        db.session.flush()

        user = User(salon_id=salon.id, name="Ana Paula", email="demo@salao.com", role="owner")
        user.set_password("123456")
        db.session.add(user)

        services = [
            Service(salon_id=salon.id, name="Corte feminino", duration_min=45, price=80.0),
            Service(salon_id=salon.id, name="Corte masculino", duration_min=30, price=50.0),
            Service(salon_id=salon.id, name="Escova", duration_min=40, price=60.0),
            Service(salon_id=salon.id, name="Coloração", duration_min=90, price=180.0),
            Service(salon_id=salon.id, name="Manicure", duration_min=40, price=45.0),
        ]
        db.session.add_all(services)
        db.session.commit()
        print("Salão demo criado!")
        print("Login: demo@salao.com / senha: 123456")
        print("Link público: /agendar/studio-bella-hair")
