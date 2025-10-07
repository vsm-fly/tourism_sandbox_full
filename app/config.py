import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_bool(name: str, default: bool) -> bool:
    """Удобный парсер булевых переменных окружения."""
    v = os.getenv(name)
    if v is None or v == "":
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    # --- Секрет и БД ---
    SECRET_KEY = os.getenv("SECRET_KEY") or None

    SQLALCHEMY_DATABASE_URI = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or f"sqlite:///{os.path.join(os.path.dirname(BASE_DIR), 'instance', 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- CSRF ---
    WTF_CSRF_TIME_LIMIT = os.getenv("WTF_CSRF_TIME_LIMIT")
    WTF_CSRF_TIME_LIMIT = (
        int(WTF_CSRF_TIME_LIMIT) if WTF_CSRF_TIME_LIMIT not in (None, "") else None
    )

    # --- Имена кук ---
    SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tourismops_session")
    REMEMBER_COOKIE_NAME = os.getenv("REMEMBER_COOKIE_NAME", "tourismops_remember")

    # --- Настройки кук (дефолт безопасные) ---
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Strict")
    REMEMBER_COOKIE_SAMESITE = os.getenv("REMEMBER_COOKIE_SAMESITE", "Strict")

    # Эти флаги в наследниках можно переопределить,
    # но по умолчанию прослушиваем COOKIE_SECURE (вкл по умолчанию)
    SESSION_COOKIE_SECURE = _env_bool("COOKIE_SECURE", True)
    REMEMBER_COOKIE_SECURE = _env_bool("COOKIE_SECURE", True)

    # --- Сессия ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    SESSION_REFRESH_EACH_REQUEST = False

    # --- Прочее ---
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    JSON_AS_ASCII = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # Если нужно тестировать по HTTP, можно временно отключить:
    # SESSION_COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)
    # REMEMBER_COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)
    # Рекомендуем работать по HTTPS и оставлять включённым.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
    # Когда включены secure-куки, удобнее подсказать схему:
    if BaseConfig.SESSION_COOKIE_SECURE:
        PREFERRED_URL_SCHEME = "https"


class ProductionConfig(BaseConfig):
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI must be set in production")

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY or SECRET_KEY == "dev-insecure-change-me":
        raise RuntimeError("SECRET_KEY must be set to a strong random value in production")

    # В проде secure-куки обязаны быть включены.
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    # SameSite можно переопределять из окружения при нужде интеграций/SSO
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Strict")
    REMEMBER_COOKIE_SAMESITE = os.getenv("REMEMBER_COOKIE_SAMESITE", "Strict")

    PREFERRED_URL_SCHEME = "https"

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
    }


class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # В тестах secure-куки можно выключить для простоты
    SESSION_COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)
    REMEMBER_COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestConfig,
}
