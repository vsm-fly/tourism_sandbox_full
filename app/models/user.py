from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .base import PKMixin, TimestampMixin
from app.extensions import db


class Role(db.Model, PKMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    users = relationship("User", back_populates="role", lazy="selectin")


class User(UserMixin, db.Model, PKMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_id: Mapped[int | None] = mapped_column(Integer, db.ForeignKey("roles.id"))
    role = relationship("Role", back_populates="users", lazy="joined")

    # ---- Пароли ----
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # (UserMixin уже даёт get_id(), is_authenticated и т.п.)
    def __repr__(self) -> str:  # удобно для логов
        return f"<User id={self.id} username={self.username!r}>"
