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
    KIWIFY_WEBHOOK_TOKEN = os.getenv("KIWIFY_WEBHOOK_TOKEN")
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

    # Planos comerciais e permissões por recurso.
    # max_professionals inclui o profissional proprietário criado no cadastro.
    PLANS = {
        "basic": {
            "label": "Basic",
            "price": 29.90,
            "max_establishments": 1,
            "max_services": 10,
            "services_label": "Até 10 serviços",
            "max_professionals": 1,
            "can_add_professionals": False,
            "max_appointments_month": None,
            "financial": False,
            "client_area": False,
            "reviews": False,
            "tagline": "Agenda essencial para quem atende sozinho",
            "features": [
                "1 estabelecimento",
                "Até 10 serviços",
                "Agenda online e página de agendamento",
                "Profissional proprietário incluído",
                "Não permite adicionar profissionais",
            ],
        },
        "premium": {
            "label": "Premium",
            "price": 59.90,
            "max_establishments": 1,
            "max_services": None,
            "services_label": "Serviços ilimitados",
            "max_professionals": 5,
            "can_add_professionals": True,
            "max_appointments_month": None,
            "financial": True,
            "client_area": False,
            "reviews": False,
            "tagline": "Para salões com equipe e controle financeiro",
            "features": [
                "1 estabelecimento",
                "Serviços ilimitados",
                "Até 5 profissionais",
                "Agenda individual por profissional",
                "Área financeira e relatórios",
            ],
        },
        "pro": {
            "label": "Pro",
            "price": 99.90,
            "max_establishments": 1,
            "max_services": None,
            "services_label": "Serviços ilimitados",
            "max_professionals": 999,
            "professionals_label": "Mais de 5 profissionais",
            "can_add_professionals": True,
            "max_appointments_month": None,
            "financial": True,
            "client_area": True,
            "reviews": True,
            "tagline": "Gestão completa, experiência do cliente e reputação",
            "features": [
                "1 estabelecimento",
                "Serviços ilimitados",
                "Mais de 5 profissionais",
                "Área do cliente para visualizar, remarcar e cancelar",
                "Avaliações dos atendimentos e profissionais",
                "Área financeira e relatórios",
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
