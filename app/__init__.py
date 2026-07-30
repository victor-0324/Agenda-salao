import os
from flask import Flask
from app.config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.booking.routes import booking_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/conta")
    app.register_blueprint(dashboard_bp, url_prefix="/painel")
    app.register_blueprint(booking_bp, url_prefix="/agendar")

    register_template_helpers(app)

    with app.app_context():
        db.create_all()

    return app


def register_template_helpers(app):
    WEEKDAYS_PT = {
        "mon": "Segunda",
        "tue": "Terça",
        "wed": "Quarta",
        "thu": "Quinta",
        "fri": "Sexta",
        "sat": "Sábado",
        "sun": "Domingo",
    }

    @app.template_filter("brl")
    def brl(value):
        try:
            return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return value

    @app.template_filter("weekday_pt")
    def weekday_pt(code):
        return WEEKDAYS_PT.get(code, code)

    @app.context_processor
    def inject_globals():
        from app.config import Config as C
        return {"PLANS": C.PLANS, "weekday_order": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}
