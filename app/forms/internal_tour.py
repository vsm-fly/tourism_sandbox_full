# app/forms/internal_tour.py
from __future__ import annotations

from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField,
    DateField, DecimalField, SubmitField
)
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError

import sqlalchemy as sa
from app.extensions import db
# Адресные импорты, чтобы избежать круговых зависимостей
from app.models.ref_codes import RefCode
from app.models.party import Supplier, Client


KINDS = [
    "Тур", "Трансфер", "Гостиница", "Питание", "Виза",
    "Входные билеты", "Гид переводчик", "Мастер классы",
    "Аренда зала/инвентарь", "Доп услуги",
]


def _num_filter(x):
    # Поддержка форматов "1 234,56" -> "1234.56"
    return x.replace(" ", "").replace(",", ".").strip() if isinstance(x, str) else x


def _strip(x):
    return x.strip() if isinstance(x, str) else x


# ---- ленивый кэш для id типа «Поставщик» ----
# False = ещё не вычисляли; None = таблицы/строки нет; int = найденный id
_SUPPLIER_TYPE_ID_CACHE: int | None | bool = False


def _get_supplier_type_id() -> int | None:
    """
    Возвращает id типа «Поставщик» из таблицы code_types или None,
    если таблицы/строки нет. Кэшируется на время жизни процесса.
    ВАЖНО: вызывать только при наличии app context (внутри запроса).
    """
    global _SUPPLIER_TYPE_ID_CACHE
    if _SUPPLIER_TYPE_ID_CACHE is not False:
        return _SUPPLIER_TYPE_ID_CACHE if _SUPPLIER_TYPE_ID_CACHE is not None else None

    try:
        # В SA 2.0 можно использовать scalar_one_or_none() для явности.
        val = db.session.execute(
            sa.text("SELECT id FROM code_types WHERE name = :n"),
            {"n": "Поставщик"},
        ).scalar()
        _SUPPLIER_TYPE_ID_CACHE = int(val) if val is not None else None
    except Exception:
        _SUPPLIER_TYPE_ID_CACHE = None

    return _SUPPLIER_TYPE_ID_CACHE


class InternalTourForm(FlaskForm):
    order_date  = DateField("Дата заказа", default=date.today, validators=[DataRequired()])
    kind        = SelectField("Вид", choices=[(k, k) for k in KINDS], validators=[DataRequired()])
    fio         = StringField("ФИО", validators=[DataRequired(), Length(max=160)], filters=[_strip])
    start_date  = DateField("Дата начала", validators=[DataRequired()])
    end_date    = DateField("Дата окончания", validators=[DataRequired()])
    direction   = StringField("Направление", validators=[DataRequired(), Length(max=160)], filters=[_strip])

    supplier_code = StringField("Поставщик (код)", validators=[DataRequired(), Length(max=32)], filters=[_strip])
    client_code   = StringField("Клиент (код)",     validators=[DataRequired(), Length(max=32)], filters=[_strip])

    cost  = DecimalField(
        "Себестоимость", places=2,
        validators=[DataRequired(), NumberRange(min=0)],
        filters=[_num_filter],
    )
    price = DecimalField(
        "Цена продажи", places=2,
        validators=[DataRequired(), NumberRange(min=0)],
        filters=[_num_filter],
    )

    net    = DecimalField("Нетто заработок", places=2, render_kw={"readonly": True, "disabled": True})
    margin = DecimalField("Маржа, %", places=1, render_kw={"readonly": True, "disabled": True})

    note   = TextAreaField("Примечание")
    submit = SubmitField("Сохранить")

    # Эти поля использует роут при сохранении
    _supplier_obj: Supplier | None = None
    _client_obj: Client | None = None

    @staticmethod
    def _ensure_party(model, code: str, name: str):
        """
        Найти (или создать) запись в таблице model (Supplier/Client) по коду.
        ВНИМАНИЕ: это сайд-эффект валидации (создание записи). Если нужно более «чисто»,
        перенеси создание в роут после validate_on_submit().
        """
        obj = model.query.filter_by(code=code).first()
        if obj:
            return obj
        obj = model(code=code, name=name)
        db.session.add(obj)
        db.session.flush()  # получить id без полного коммита
        return obj

    # --------- валидаторы полей ---------

    def validate_supplier_code(self, field):
        code = (field.data or "").strip()
        rc = RefCode.query.filter_by(code=code).first()
        if not rc:
            raise ValidationError("Код поставщика не найден в справочнике.")

        supplier_type_id = _get_supplier_type_id()
        # Если тип «Поставщик» существует — требуем точного совпадения
        if supplier_type_id is not None and rc.type_id != supplier_type_id:
            raise ValidationError("В поле «Поставщик (код)» допустимы только коды типа «Поставщик».")

        self._supplier_obj = self._ensure_party(Supplier, code=rc.code, name=(rc.name or rc.code))

    def validate_client_code(self, field):
        code = (field.data or "").strip()
        rc = RefCode.query.filter_by(code=code).first()
        if not rc:
            raise ValidationError("Код клиента не найден в справочнике.")

        supplier_type_id = _get_supplier_type_id()
        # Клиент может быть любым типом, КРОМЕ «Поставщик» (если такой тип есть)
        if supplier_type_id is not None and rc.type_id == supplier_type_id:
            raise ValidationError("В поле «Клиент (код)» запрещены коды типа «Поставщик».")

        self._client_obj = self._ensure_party(Client, code=rc.code, name=(rc.name or rc.code))

    # --------- общая валидация ---------

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if not ok:
            return False

        # Запрет совпадения сторон
        if self._supplier_obj and self._client_obj and self._supplier_obj.id == self._client_obj.id:
            self.client_code.errors.append("Поставщик и Клиент не должны совпадать.")
            return False

        # Контроль дат
        if self.start_date.data and self.end_date.data and self.start_date.data > self.end_date.data:
            self.end_date.errors.append("Дата окончания должна быть не раньше даты начала.")
            return False

        return True
