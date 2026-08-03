import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
    # SQLALCHEMY_DATABASE_URI = os.environ.get(
    #     "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'agendasalao.db')}"
    # )
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    # PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    # WTF_CSRF_TIME_LIMIT = None

    # class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_CONNECTION")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_TIME_LIMIT = None

    API_LOCATION_KEY = os.getenv("API_LOCATION_KEY")
    # Se UPLOAD_FOLDER não vier definido no .env (ou vier vazio), usa uma pasta
    # dentro de static/ mesmo, assim as fotos ficam sempre acessíveis publicamente.
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER") or os.path.join(basedir, "static", "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB por arquivo enviado

    # Janela de horário padrão para novos salões (usada até configurarem os próprios horários)
    DEFAULT_WORKING_HOURS = {
        "mon": {"open": "09:00", "close": "19:00", "closed": False},
        "tue": {"open": "09:00", "close": "19:00", "closed": False},
        "wed": {"open": "09:00", "close": "19:00", "closed": False},
        "thu": {"open": "09:00", "close": "19:00", "closed": False},
        "fri": {"open": "09:00", "close": "19:00", "closed": False},
        "sat": {"open": "09:00", "close": "17:00", "closed": False},
        "sun": {"open": "09:00", "close": "13:00", "closed": True},
    }

    # Planos comerciais: isso é o que torna o produto "vendável" - limites reais por plano,
    # usados tanto na página de preços quanto no bloqueio de funcionalidades no painel.
    PLANS = {
        "premium": {
            "label": "Premium",
            "price": 14.99,
            "max_services": 999,
            "max_professionals": 999,
            "max_appointments_month": 999999,
            "tagline": "Para redes e salões de alto volume",
            "features": [
                "Tudo do Pro",
                "Profissionais e serviços ilimitados",
                "Agendamentos ilimitados",
                "Suporte prioritário via WhatsApp",
                "Múltiplas unidades (em breve)",
            ],
        },
    }

    TRIAL_DAYS = 7

    # Versões visuais disponíveis para o painel e para a página pública de agendamento
    THEMES = {
        "feminino": {
            "label": "Feminino",
            "description": "Paleta rosa e roxo, visual neon — inspirado em salões de beleza.",
        },
        "masculino": {
            "label": "Masculino",
            "description": "Paleta azul e grafite, visual mais sóbrio — inspirado em barbearias.",
        },
    }
