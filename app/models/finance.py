# app/models/finance.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import String, Numeric, Date, CheckConstraint, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import PKMixin, TimestampMixin
from app.extensions import db


class BankAccount(db.Model, PKMixin, TimestampMixin):
    __tablename__ = "bank_accounts"

    bank_name: Mapped[str] = mapped_column(String(50), nullable=False)
    number:    Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    currency:  Mapped[str] = mapped_column(String(3), nullable=False, default="TJS")


class BankOperation(db.Model, PKMixin, TimestampMixin):
    __tablename__ = "bank_operations"

    date_op:        Mapped[date]  = mapped_column(Date, nullable=False, default=date.today)
    bank_name:      Mapped[str]   = mapped_column(String(50), nullable=False)
    account_number: Mapped[str]   = mapped_column(String(20), nullable=False, index=True)

    # FK на счёт (после миграции обязателен)
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"),
        nullable=False,
        index=True,
    )
    account: Mapped[BankAccount] = relationship("BankAccount", lazy="joined")

    section:     Mapped[str]        = mapped_column(String(10), nullable=False)  # Приход/Расход
    client_code: Mapped[str]        = mapped_column(String(10), nullable=False, index=True)
    client_name: Mapped[str]        = mapped_column(String(128), nullable=False)

    basis:       Mapped[str | None] = mapped_column(String(255), nullable=True)

    currency:    Mapped[str]        = mapped_column(String(3), nullable=False, default="TJS")
    rate:        Mapped[Decimal]    = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("1"))
    nominal:     Mapped[Decimal]    = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    equivalent:  Mapped[Decimal]    = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    note:        Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("rate >= 0",       name="bo_rate_ge_0"),
        CheckConstraint("nominal >= 0",    name="bo_nominal_ge_0"),
        CheckConstraint("equivalent >= 0", name="bo_equivalent_ge_0"),
    )
