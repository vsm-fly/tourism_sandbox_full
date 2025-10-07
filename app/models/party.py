# app/models/party.py
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from .base import PKMixin, TimestampMixin


class Client(db.Model, PKMixin, TimestampMixin):
    __tablename__ = "clients"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Связи с внутренними турами: обе ветки указывают на таблицу internal_tours
    internal_tours_as_client = relationship(
        "InternalTour",
        foreign_keys="InternalTour.client_id",
        back_populates="client",
        lazy="selectin",
    )
    internal_tours_as_supplier = relationship(
        "InternalTour",
        foreign_keys="InternalTour.supplier_id",
        back_populates="supplier",
        lazy="selectin",
    )

    # Связь с внешними турами (ExternalTour.client_id -> clients.id)
    external_tours = relationship(
        "ExternalTour",
        back_populates="client",
        lazy="selectin",
    )


class Supplier(db.Model, PKMixin, TimestampMixin):
    __tablename__ = "suppliers"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Связь с внешними турами (ExternalTour.supplier_id -> suppliers.id)
    external_tours = relationship(
        "ExternalTour",
        back_populates="supplier",
        lazy="selectin",
    )
