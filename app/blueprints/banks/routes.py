from __future__ import annotations

from datetime import date as date_cls, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import StringIO, BytesIO
import csv

from flask import (
    render_template, request, redirect, url_for,
    flash, abort, jsonify, Response, send_file
)
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_

from app.extensions import db
from app.models.finance import BankOperation, BankAccount
from app.models.ref_codes import RefCode
from . import bp

# WTForms для счетов
from app.forms.bank_account import BankAccountForm

# XLSX (необязательно)
try:
    from openpyxl import Workbook
except Exception:
    Workbook = None


# ===== Справочники для форм (пока константы) =====
BANKS = ["Алиф", "Васл", "Ориёнбанк", "Халык", "IBT", "Хумо", "Спитамен", "Эсхата", "Мегафон лайф", "DC"]
CURRENCIES = ["TJS", "USD", "RUB", "EUR", "UZS"]


# ===== Утилиты =====

def _to_decimal(value: str | None, default: str = "0") -> Decimal:
    """Безопасное приведение строки к Decimal."""
    s = (value or default).replace(" ", "").strip().replace(",", ".")
    return Decimal(s)

def _require_admin():
    if not getattr(current_user, "is_admin", False):
        r = getattr(current_user, "role", None)
        role_val = ((getattr(r, "name", None) or getattr(r, "code", None) or "") if r else "").strip().lower()
        if role_val != "admin":
            abort(403)

def _filter_accounts_query(q: str, currency: str):
    query = BankAccount.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(BankAccount.number.ilike(like), BankAccount.bank_name.ilike(like)))
    if currency:
        query = query.filter(BankAccount.currency == currency)
    return query

def _parse_date(s: str | None) -> date_cls | None:
    if not s:
        return None
    try:
        return date_cls.fromisoformat(s.strip())
    except ValueError:
        return None

def _filter_ops_query(args):
    """Фильтры для списка операций."""
    bank = (args.get("bank") or "").strip()
    currency = (args.get("currency") or "").strip().upper()
    section = (args.get("section") or "").strip()
    account = (args.get("account_number") or "").strip()
    code = (args.get("client_code") or "").strip()
    q = (args.get("q") or "").strip()
    date_from = _parse_date(args.get("date_from"))
    date_to = _parse_date(args.get("date_to"))

    query = BankOperation.query

    if bank:
        query = query.filter(BankOperation.bank_name == bank)
    if currency:
        query = query.filter(BankOperation.currency == currency)
    if section:
        query = query.filter(BankOperation.section == section)
    if account:
        query = query.filter(BankOperation.account_number == account)
    if code:
        query = query.filter(BankOperation.client_code == code)
    if date_from and date_to:
        query = query.filter(and_(BankOperation.date_op >= date_from, BankOperation.date_op <= date_to))
    elif date_from:
        query = query.filter(BankOperation.date_op >= date_from)
    elif date_to:
        query = query.filter(BankOperation.date_op <= date_to)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(BankOperation.basis.ilike(like), BankOperation.client_name.ilike(like)))

    return query


# ===== AJAX: автоподстановка наименования по коду =====

@bp.get("/api/ref-code/<string:code>", endpoint="ajax_ref_code")
@login_required
def ajax_ref_code(code: str):
    rc = RefCode.query.filter_by(code=code.strip()).first()
    return jsonify({"ok": bool(rc), "name": (rc.name if rc else "")})


# ===== Операции банка =====

@bp.get("/")
@login_required
def list_ops():
    """
    Список операций.
    Если фильтры не заданы — показываем последние 200 без пагинации.
    Если фильтры заданы — включаем пагинацию.
    """
    args = request.args
    page = args.get("page", 1, type=int)
    per_page = 50

    base_q = _filter_ops_query(args).order_by(BankOperation.date_op.desc(), BankOperation.id.desc())

    if not args:  # пустой query string
        base_q = base_q.limit(200)
        ops = base_q.all()
        pagination = None
    else:
        pagination = db.paginate(base_q, page=page, per_page=per_page, error_out=False)
        ops = pagination.items

    banks = BANKS
    currencies = CURRENCIES
    sections = ["Приход", "Расход"]
    accounts = BankAccount.query.order_by(BankAccount.bank_name.asc(), BankAccount.number.asc()).all()

    return render_template(
        "banks/list.html",
        ops=ops,
        pagination=pagination,
        banks=banks,
        currencies=currencies,
        sections=sections,
        accounts=accounts,
        bank=(args.get("bank") or ""),
        currency=(args.get("currency") or ""),
        section=(args.get("section") or ""),
        account_number=(args.get("account_number") or ""),
        client_code=(args.get("client_code") or ""),
        q=(args.get("q") or ""),
        date_from=(args.get("date_from") or ""),
        date_to=(args.get("date_to") or ""),
    )


@bp.get("/export.xlsx", endpoint="ops_export_xlsx")
@login_required
def ops_export_xlsx():
    """Экспорт операций в XLSX (учитывает фильтры)."""
    if Workbook is None:
        flash("Экспорт в XLSX недоступен: пакет openpyxl не установлен.", "warning")
        return redirect(url_for("banks.list_ops"))

    query = _filter_ops_query(request.args).order_by(BankOperation.date_op.desc())
    if not request.args:
        query = query.limit(200)
    rows = query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Операции"
    ws.append([
        "Дата", "Банк", "Счёт", "Секция",
        "Код", "Контрагент", "Основание",
        "Валюта", "Курс", "Номинал", "Эквивалент",
        "Примечание",
    ])

    def _num(v): return float(v) if isinstance(v, Decimal) else v

    for r in rows:
        ws.append([
            r.date_op, r.bank_name, r.account_number, r.section,
            r.client_code, r.client_name, r.basis, r.currency,
            _num(r.rate), _num(r.nominal), _num(r.equivalent), r.note,
        ])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = f"bank_operations_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return send_file(
        bio,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.get("/export.csv", endpoint="ops_export_csv")
@login_required
def ops_export_csv():
    """Экспорт операций в CSV (учитывает фильтры)."""
    query = _filter_ops_query(request.args).order_by(BankOperation.date_op.desc())
    if not request.args:
        query = query.limit(200)
    rows = query.all()

    si = StringIO()
    w = csv.writer(si)
    w.writerow(["Дата","Банк","Счёт","Секция","Код","Контрагент","Основание","Валюта","Курс","Номинал","Эквивалент","Примечание"])

    def _num(v): return float(v) if isinstance(v, Decimal) else v

    for r in rows:
        w.writerow([
            r.date_op, r.bank_name, r.account_number, r.section,
            r.client_code, r.client_name, r.basis, r.currency,
            _num(r.rate), _num(r.nominal), _num(r.equivalent), r.note
        ])

    filename = f"bank_operations_{datetime.now():%Y%m%d_%H%M}.csv"
    return Response(
        si.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_op():
    """Создание операции (банк и валюта берутся из выбранного счёта на сервере)."""
    if request.method == "POST":
        f = request.form

        # --- серверная проверка обязательных полей ---
        required = {
            "account_number": "№ счёта",
            "section": "Секция",
            "client_code": "Код контрагента",
            "rate": "Курс",
            "nominal": "Номинал",
        }
        missing = [v for k, v in required.items() if not (f.get(k) or "").strip()]
        if missing:
            flash("Заполните обязательные поля: " + ", ".join(missing), "danger")
            return redirect(url_for("banks.new_op"))

        # дата операции (по умолчанию — сегодня)
        raw_date = (f.get("date_op") or "").strip()
        try:
            date_op = date_cls.fromisoformat(raw_date) if raw_date else date_cls.today()
        except ValueError:
            date_op = date_cls.today()
            flash("Дата операции распознана некорректно, подставлена текущая дата.", "warning")

        # числа в Decimal
        try:
            rate = _to_decimal(f.get("rate"), default="1")
            nominal = _to_decimal(f.get("nominal"), default="0")
        except InvalidOperation:
            flash("Курс/Номинал заданы неверно.", "danger")
            return redirect(url_for("banks.new_op"))

        if rate < 0 or nominal < 0:
            flash("Курс и Номинал не могут быть отрицательными.", "danger")
            return redirect(url_for("banks.new_op"))

        eqv = (rate * nominal).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # секция
        section = (f.get("section") or "").strip()
        if section not in ("Приход", "Расход"):
            flash("Секция должна быть «Приход» или «Расход».", "danger")
            return redirect(url_for("banks.new_op"))

        client_code = (f.get("client_code") or "").strip()
        client_name = (f.get("client_name") or "").strip()

        # автоподстановка имени, если пусто
        if client_code and not client_name:
            rc = RefCode.query.filter(RefCode.code == client_code).first()
            if rc:
                client_name = rc.name

        # сверяем счёт и подставляем банк/валюту из БД
        acc_num = (f.get("account_number") or "").strip()
        acc_obj = BankAccount.query.filter_by(number=acc_num).first()
        if not acc_obj:
            flash("Счёт не найден в справочнике счетов.", "danger")
            return redirect(url_for("banks.new_op"))

        bank_name = acc_obj.bank_name
        currency = acc_obj.currency

        op = BankOperation(
            date_op=date_op,
            bank_name=bank_name,
            account_number=acc_num,
            section=section,
            client_code=client_code,
            client_name=client_name,
            basis=(f.get("basis") or "").strip(),
            currency=currency,
            rate=rate,
            nominal=nominal,
            equivalent=eqv,
            note=(f.get("note") or "").strip(),
        )

        # FK на счёт, если поле присутствует в модели
        if hasattr(BankOperation, "bank_account_id"):
            op.bank_account_id = acc_obj.id

        db.session.add(op)
        try:
            db.session.commit()
            flash("Операция сохранена", "success")
            return redirect(url_for("banks.list_ops"))
        except IntegrityError:
            db.session.rollback()
            flash("Ошибка сохранения операции (возможен конфликт БД).", "danger")

    accounts = BankAccount.query.order_by(BankAccount.bank_name.asc(), BankAccount.number.asc()).all()
    codes = RefCode.query.order_by(RefCode.code.asc()).all()
    return render_template(
        "banks/form.html",
        banks=BANKS,
        accounts=accounts,
        codes=codes,
        currencies=CURRENCIES,
    )


# ===== Редактирование/удаление операции =====

@bp.route("/<int:op_id>/edit", methods=["GET", "POST"], endpoint="ops_edit")
@login_required
def ops_edit(op_id: int):
    """Редактирование операции."""
    op = BankOperation.query.get_or_404(op_id)

    if request.method == "POST":
        f = request.form

        # дата
        raw_date = (f.get("date_op") or "").strip()
        try:
            op.date_op = date_cls.fromisoformat(raw_date) if raw_date else date_cls.today()
        except ValueError:
            op.date_op = date_cls.today()
            flash("Дата операции распознана некорректно, подставлена текущая дата.", "warning")

        # числа
        try:
            rate = _to_decimal(f.get("rate"), default="1")
            nominal = _to_decimal(f.get("nominal"), default="0")
        except InvalidOperation:
            flash("Курс/Номинал заданы неверно.", "danger")
            return redirect(url_for("banks.ops_edit", op_id=op.id))

        if rate < 0 or nominal < 0:
            flash("Курс и Номинал не могут быть отрицательными.", "danger")
            return redirect(url_for("banks.ops_edit", op_id=op.id))

        eqv = (rate * nominal).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # код/имя
        client_code = (f.get("client_code") or "").strip()
        client_name = (f.get("client_name") or "").strip()
        if client_code and not client_name:
            rc = RefCode.query.filter(RefCode.code == client_code).first()
            if rc:
                client_name = rc.name or client_name

        # выбранный счёт => банк/валюта/связь
        acc_num = (f.get("account_number") or "").strip()
        acc_obj = BankAccount.query.filter_by(number=acc_num).first()
        if not acc_obj:
            flash("Счёт не найден в справочнике счетов.", "danger")
            return redirect(url_for("banks.ops_edit", op_id=op.id))

        op.bank_name = acc_obj.bank_name
        op.account_number = acc_num
        op.section = (f.get("section") or "").strip()
        op.client_code = client_code
        op.client_name = client_name
        op.basis = (f.get("basis") or "").strip()
        op.currency = acc_obj.currency
        op.rate = rate
        op.nominal = nominal
        op.equivalent = eqv
        op.note = (f.get("note") or "").strip()

        if hasattr(BankOperation, "bank_account_id"):
            op.bank_account_id = acc_obj.id

        try:
            db.session.commit()
            flash("Операция обновлена", "success")
            return redirect(url_for("banks.list_ops"))
        except IntegrityError:
            db.session.rollback()
            flash("Не удалось сохранить изменения (ошибка БД).", "danger")

    # GET
    accounts = BankAccount.query.order_by(BankAccount.bank_name.asc(), BankAccount.number.asc()).all()
    codes = RefCode.query.order_by(RefCode.code.asc()).all()
    return render_template(
        "banks/form.html",
        banks=BANKS,
        accounts=accounts,
        codes=codes,
        currencies=CURRENCIES,
        op=op,
        is_edit=True,
    )


@bp.post("/<int:op_id>/delete", endpoint="ops_delete")
@login_required
def ops_delete(op_id: int):
    """Удаление операции (только админ)."""
    _require_admin()

    op = BankOperation.query.get(op_id)
    if not op:
        flash("Операция не найдена.", "warning")
        return redirect(url_for("banks.list_ops"))

    try:
        db.session.delete(op)
        db.session.commit()
        flash("Операция удалена", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Не удалось удалить операцию (ошибка БД).", "danger")

    return redirect(url_for("banks.list_ops"))


# ===== Счета банка =====

@bp.get("/bank/accounts", endpoint="accounts_list")
@login_required
def accounts_list():
    """Список счетов: поиск, фильтр по валюте, пагинация."""
    q = (request.args.get("q") or "").strip()
    currency = (request.args.get("currency") or "").strip().upper()
    page = request.args.get("page", 1, type=int)
    per_page = 20

    base_q = _filter_accounts_query(q, currency).order_by(BankAccount.id.desc())
    pagination = db.paginate(base_q, page=page, per_page=per_page, error_out=False)

    currencies = ["", "TJS", "USD", "RUB", "EUR", "UZS"]
    return render_template(
        "banks/accounts_list.html",
        accounts=pagination.items,
        q=q, currency=currency, currencies=currencies,
        pagination=pagination,
    )


@bp.get("/bank/accounts/export.csv", endpoint="accounts_export_csv")
@login_required
def accounts_export_csv():
    """Экспорт счетов в CSV (учитывает фильтры q, currency)."""
    q = (request.args.get("q") or "").strip()
    currency = (request.args.get("currency") or "").strip().upper()
    rows = _filter_accounts_query(q, currency).order_by(BankAccount.id.desc()).all()

    si = StringIO()
    w = csv.writer(si)
    w.writerow(["ID", "Банк", "Счёт", "Валюта", "Создан", "Обновлён"])
    for r in rows:
        w.writerow([r.id, r.bank_name, r.number, r.currency, getattr(r, "created_at", ""), getattr(r, "updated_at", "")])

    filename = f"bank_accounts_{datetime.now():%Y%m%d_%H%M}.csv"
    return Response(
        si.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@bp.get("/bank/accounts/export.xlsx", endpoint="accounts_export_xlsx")
@login_required
def accounts_export_xlsx():
    """Экспорт счетов в XLSX (учитывает фильтры q, currency)."""
    if Workbook is None:
        flash("Экспорт в XLSX недоступен: пакет openpyxl не установлен.", "warning")
        return redirect(url_for("banks.accounts_list", **request.args))

    q = (request.args.get("q") or "").strip()
    currency = (request.args.get("currency") or "").strip().upper()
    rows = _filter_accounts_query(q, currency).order_by(BankAccount.id.desc()).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Счета"
    ws.append(["ID", "Банк", "Счёт", "Валюта", "Создан", "Обновлён"])
    for r in rows:
        ws.append([r.id, r.bank_name, r.number, r.currency, getattr(r, "created_at", None), getattr(r, "updated_at", None)])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = f"bank_accounts_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return send_file(
        bio,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.route("/bank/accounts/new", methods=["GET", "POST"], endpoint="accounts_new")
@login_required
def accounts_new():
    """Создание счёта (WTForms)."""
    form = BankAccountForm()
    if form.validate_on_submit():
        exists = BankAccount.query.filter(BankAccount.number == form.number.data.strip()).first()
        if exists:
            flash("Счёт с таким номером уже существует.", "warning")
            return render_template("banks/accounts_new.html", form=form)

        acc = BankAccount(
            bank_name=form.bank_name.data,
            number=form.number.data.strip(),
            currency=form.currency.data,
        )
        if hasattr(BankAccount, "balance") and form.opening_balance.data is not None:
            acc.balance = form.opening_balance.data

        db.session.add(acc)
        try:
            db.session.commit()
            flash("Счёт успешно добавлен", "success")
            return redirect(url_for("banks.accounts_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Не удалось сохранить счёт (возможен дубликат номера).", "danger")

    return render_template("banks/accounts_new.html", form=form)


@bp.route("/bank/accounts/<int:acc_id>/edit", methods=["GET", "POST"], endpoint="accounts_edit")
@login_required
def accounts_edit(acc_id: int):
    """Редактирование счёта."""
    acc = BankAccount.query.get_or_404(acc_id)
    form = BankAccountForm(obj=acc)

    if form.validate_on_submit():
        exists = (
            BankAccount.query
            .filter(BankAccount.number == form.number.data.strip(), BankAccount.id != acc.id)
            .first()
        )
        if exists:
            flash("Счёт с таким номером уже существует.", "warning")
            return render_template("banks/accounts_edit.html", form=form, acc=acc)

        acc.bank_name = form.bank_name.data
        acc.number = form.number.data.strip()
        acc.currency = form.currency.data

        try:
            db.session.commit()
            flash("Счёт обновлён", "success")
            return redirect(url_for("banks.accounts_list"))
        except IntegrityError:
            db.session.rollback()
            flash("Не удалось сохранить изменения (возможен конфликт уникальности).", "danger")

    return render_template("banks/accounts_edit.html", form=form, acc=acc)


@bp.post("/bank/accounts/<int:acc_id>/delete")
@login_required
def accounts_delete(acc_id: int):
    """Удаление счёта (только админ)."""
    _require_admin()

    acc = BankAccount.query.get(acc_id)
    if not acc:
        flash("Счёт не найден.", "warning")
        return redirect(url_for("banks.accounts_list"))

    try:
        db.session.delete(acc)
        db.session.commit()
        flash("Счёт удалён", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Нельзя удалить счёт: на него ссылаются операции или возникла ошибка БД.", "danger")

    return redirect(url_for("banks.accounts_list"))
