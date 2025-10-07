# app/models/internal_tour.py
from __future__ import annotations

from datetime import datetime, date

from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship

from app.extensions import db
from .base import PKMixin, TimestampMixin


class InternalTour(db.Model):
    __tablename__ = "internal_tours"

    id = db.Column(Integer, primary_key=True)

    # Основные поля
    order_date = db.Column(Date, nullable=False, default=date.today)
    kind       = db.Column(String(50),  nullable=False)
    fio        = db.Column(String(160), nullable=False)
    start_date = db.Column(Date,        nullable=False)
    end_date   = db.Column(Date,        nullable=False)
    direction  = db.Column(String(160), nullable=False)

    # FK ОБЕ на clients.id  ← ВАЖНО
    supplier_id = db.Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    client_id   = db.Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    # Деньги / вычисляемые поля
    cost   = db.Column(Numeric(10, 2), nullable=False, default=0)
    price  = db.Column(Numeric(10, 2), nullable=False, default=0)
    net    = db.Column(Numeric(10, 2), nullable=False, default=0)
    margin = db.Column(Numeric(5, 1),  nullable=False, default=0)

    note = db.Column(Text)

    # --- Legacy-совместимость с существующей БД ---
    order_type         = db.Column(String(50), nullable=False, default="internal")
    sale_price_legacy  = db.Column("sale_price", Numeric(10, 2), nullable=False, default=0)
    net_profit_legacy  = db.Column("net_profit", Numeric(10, 2), nullable=False, default=0)
    notes_legacy       = db.Column("notes", Text, default="")

    created_at = db.Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи — обе к Client; back_populates должны совпадать с определениями в модели Client
    supplier = relationship(
        "Client",
        foreign_keys=[supplier_id],
        back_populates="internal_tours_as_supplier",
        lazy="selectin",
    )
    client = relationship(
        "Client",
        foreign_keys=[client_id],
        back_populates="internal_tours_as_client",
        lazy="selectin",
    )

    def recompute(self) -> None:
        """Пересчёт net и margin из cost/price."""
        c = float(self.cost or 0)
        p = float(self.price or 0)
        net = round(p - c, 2)
        self.net = net
        self.margin = round((net / p) * 100, 1) if p else 0

    def __repr__(self) -> str:
        return f"<InternalTour id={self.id} kind={self.kind!r} fio={self.fio!r} order_date={self.order_date}>"


class ExternalTour(db.Model, PKMixin, TimestampMixin):
    __tablename__ = "external_tours"

    order_type = db.Column(String(50), nullable=False)
    fio        = db.Column(String(255), nullable=False)
    start_date = db.Column(DateTime)
    end_date   = db.Column(DateTime)
    direction  = db.Column(String(255))

    cost       = db.Column(Numeric(18, 2), nullable=False, default=0)
    sale_price = db.Column(Numeric(18, 2), nullable=False, default=0)
    net_profit = db.Column(Numeric(18, 2), nullable=False, default=0)
    margin     = db.Column(Numeric(9, 4),  nullable=False, default=0)

    notes      = db.Column(String(1000))

    supplier_id = db.Column(Integer, ForeignKey("suppliers.id"))
    client_id   = db.Column(Integer, ForeignKey("clients.id"))

    supplier = relationship("Supplier", back_populates="external_tours", lazy="joined")
    client   = relationship("Client",   back_populates="external_tours", lazy="joined")


# --- Back-compat виртуальные поля для шаблонов ---
try:
    if not hasattr(InternalTour, "supplier_code"):
        InternalTour.supplier_code = property(
            lambda self: self.supplier.code if getattr(self, "supplier", None) else None
        )
    if not hasattr(InternalTour, "client_code"):
        InternalTour.client_code = property(
            lambda self: self.client.code if getattr(self, "client", None) else None
        )
except Exception:
    pass
