from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


class AccountError(Exception):
    """Базовое исключение для ошибок банковского счёта."""


class AccountFrozenError(AccountError):
    """Операция невозможна: счёт заморожен."""


class AccountClosedError(AccountError):
    """Операция невозможна: счёт закрыт."""


class InvalidOperationError(AccountError):
    """Недопустимая операция."""


class InsufficientFundsError(AccountError):
    """Недостаточно средств для выполнения операции."""


class AccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    CNY = "CNY"


@dataclass(frozen=True)
class Owner:
    """Простая модель владельца счёта."""
    full_name: str
    client_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.full_name, str) or not self.full_name.strip():
            raise ValueError("Имя владельца должно быть непустой строкой.")
        if not isinstance(self.client_id, str) or not self.client_id.strip():
            raise ValueError("client_id владельца должен быть непустой строкой.")


class AbstractAccount(ABC):
    """Абстрактная модель банковского счёта."""

    def __init__(
        self,
        owner: Owner,
        balance: float = 0.0,
        account_id: str | None = None,
        status: AccountStatus = AccountStatus.ACTIVE,
    ) -> None:
        if not isinstance(owner, Owner):
            raise TypeError("owner должен быть экземпляром Owner.")
        if not isinstance(status, AccountStatus):
            raise TypeError("status должен быть экземпляром AccountStatus.")

        self._account_id = account_id if account_id is not None else self._generate_account_id()
        self._owner = owner
        self._balance = self._validate_initial_balance(balance)
        self._status = status

    @staticmethod
    def _generate_account_id() -> str:
        """Генерирует короткий UUID из 8 символов."""
        return uuid4().hex[:8].upper()

    @staticmethod
    def _validate_initial_balance(balance: float) -> float:
        if not isinstance(balance, (int, float)):
            raise TypeError("Баланс должен быть числом.")
        if balance < 0:
            raise ValueError("Начальный баланс не может быть отрицательным.")
        return float(balance)

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def owner(self) -> Owner:
        return self._owner

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def status(self) -> AccountStatus:
        return self._status

    def freeze(self) -> None:
        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Нельзя заморозить закрытый счёт.")
        self._status = AccountStatus.FROZEN

    def activate(self) -> None:
        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Нельзя активировать закрытый счёт.")
        self._status = AccountStatus.ACTIVE

    def close(self) -> None:
        self._status = AccountStatus.CLOSED

    def _ensure_account_is_operable(self) -> None:
        if self._status == AccountStatus.FROZEN:
            raise AccountFrozenError("Операция невозможна: счёт заморожен.")
        if self._status == AccountStatus.CLOSED:
            raise AccountClosedError("Операция невозможна: счёт закрыт.")

    @staticmethod
    def _validate_amount(amount: float) -> float:
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом.")
        amount = float(amount)
        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть больше нуля.")
        return amount

    @abstractmethod
    def deposit(self, amount: float) -> None:
        """Пополнение счёта."""

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        """Снятие со счёта."""

    @abstractmethod
    def get_account_info(self) -> dict:
        """Возвращает подробную информацию о счёте."""

class BankAccount(AbstractAccount):
    """Конкретная реализация банковского счёта."""

    def __init__(
        self,
        owner: Owner,
        balance: float = 0.0,
        account_id: str | None = None,
        status: AccountStatus = AccountStatus.ACTIVE,
        currency: Currency = Currency.RUB,
    ) -> None:
        if not isinstance(currency, Currency):
            raise TypeError("currency должен быть экземпляром Currency.")
        super().__init__(owner=owner, balance=balance, account_id=account_id, status=status)
        self._currency = currency

    @property
    def currency(self) -> Currency:
        return self._currency

    def deposit(self, amount: float) -> None:
        self._ensure_account_is_operable()
        valid_amount = self._validate_amount(amount)
        self._balance += valid_amount

    def withdraw(self, amount: float) -> None:
        self._ensure_account_is_operable()
        valid_amount = self._validate_amount(amount)
        if valid_amount > self._balance:
            raise InsufficientFundsError(
                f"Недостаточно средств: запрошено {valid_amount:.2f}, доступно {self._balance:.2f}."
            )
        self._balance -= valid_amount

    def get_account_info(self) -> dict:
        return {
            "account_type": self.__class__.__name__,
            "account_id": self.account_id,
            "owner_name": self.owner.full_name,
            "owner_client_id": self.owner.client_id,
            "status": self.status.value,
            "balance": round(self.balance, 2),
            "currency": self.currency.value,
        }

    def __str__(self) -> str:
        last_4 = self.account_id[-4:]
        return (
            f"{self.__class__.__name__}"
            f"(client='{self.owner.full_name}', "
            f"account='****{last_4}', "
            f"status='{self.status.value}', "
            f"balance={self.balance:.2f} {self.currency.value})"
        )