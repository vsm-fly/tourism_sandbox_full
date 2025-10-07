# app/forms/bank_account.py
from __future__ import annotations
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

BANKS = ["Алиф", "Васл", "Ориёнбанк", "Халык", "IBT", "Хумо", "Спитамен", "Эсхата", "Мегафон лайф", "DC"]
CURRENCIES = ["TJS", "USD", "RUB", "EUR", "UZS"]


def _num_filter(x):
    """Нормализует значение для DecimalField: допускает None | str | int | float | Decimal."""
    if x is None:
        return None
    if isinstance(x, (int, float, Decimal)):
        return x
    if isinstance(x, str):
        return x.replace(",", ".").replace(" ", "").strip()
    return x


def _strip(s):
    return s.strip() if isinstance(s, str) else s


class BankAccountForm(FlaskForm):
    bank_name = SelectField(
        "Банк",
        choices=[(b, b) for b in BANKS],
        validators=[DataRequired(), Length(max=50)],
    )

    number = StringField(
        "Номер счёта",
        validators=[DataRequired(), Length(max=20)],
        filters=[_strip],
        render_kw={"maxlength": 20},
    )

    currency = SelectField(
        "Валюта",
        choices=[(c, c) for c in CURRENCIES],
        validators=[DataRequired(), Length(min=3, max=3)],
    )

    # В БД поля может не быть — сохраняем только если модель его поддерживает (см. роут с hasattr)
    opening_balance = DecimalField(
        "Начальный баланс",
        validators=[Optional()],
        default=None,                # раньше было 0 (int) → падал _num_filter
        filters=[_num_filter],
        places=2,
        render_kw={"step": "0.01"},
    )

    submit = SubmitField("Сохранить")
