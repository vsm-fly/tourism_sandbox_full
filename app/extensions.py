# app/extensions.py
from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData

# ---------- SQLAlchemy naming convention ----------
# Это устраняет ошибки Alembic наподобие "Constraint must have a name"
# и делает имена констрейнтов стабильными между СУБД (особенно важно для SQLite).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)

# ---------- Flask extensions ----------
# expire_on_commit=False — удобнее в веб-приложении (объекты не «протухают» после commit)
db = SQLAlchemy(metadata=metadata, session_options={"expire_on_commit": False})
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Роут логина и категория флеш-сообщения — можно переопределить в create_app при желании
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

def init_extensions(app) -> None:
    """
    Необязательный хелпер: если хочешь, можешь вызывать это в create_app вместо ручной инициализации.
    """
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

def register_user_loader() -> None:
    """
    Зарегистрировать user_loader отдельно, после того как импортированы модели.
    В create_app это удобно вызывать ПОСЛЕ `from app import models`.
    Это избегает циклического импорта (models -> extensions -> models).
    """
    from app.models import User  # локальный импорт, чтобы не ловить цикл

    @login_manager.user_loader
    def load_user(user_id: str):
        # SQLAlchemy 2.x: Query.get() помечен как legacy, но для простоты здесь он ок.
        # Если хочешь строго по новой API — используй db.session.get(User, int(user_id)).
        try:
            return db.session.get(User, int(user_id))
        except Exception:
            return None
