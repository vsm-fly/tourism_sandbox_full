# app/models/__init__.py

# Пользователи
from .user import User  # если у тебя другой модуль с User — оставь как есть

# Справочники
from .ref_codes import RefCode, CodeType

# Финансы (банк)
from .finance import BankAccount, BankOperation

# Партнёры (клиенты и поставщики)
from .party import Client, Supplier

# Туризм (внутренние туры)
from .tourism import InternalTour

__all__ = [
    "User",
    "RefCode",
    "CodeType",
    "BankAccount",
    "BankOperation",
    "Client",
    "Supplier",
    "InternalTour",
]
