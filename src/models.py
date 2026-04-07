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


class AssetType(str, Enum):
    STOCKS = "stocks"
    BONDS = "bonds"
    ETF = "etf"


@dataclass(frozen=True)
class Owner:
    full_name: str
    client_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.full_name, str) or not self.full_name.strip():
            raise ValueError("Имя владельца должно быть непустой строкой.")
        if not isinstance(self.client_id, str) or not self.client_id.strip():
            raise ValueError("client_id владельца должен быть непустой строкой.")


class AbstractAccount(ABC):
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
        return uuid4().hex[:8].upper()

    @staticmethod
    def _validate_initial_balance(balance: float) -> float:
        if not isinstance(balance, (int, float)):
            raise TypeError("Баланс должен быть числом.")
        if balance < 0:
            raise ValueError("Начальный баланс не может быть отрицательным.")
        return float(balance)

    @staticmethod
    def _validate_amount(amount: float) -> float:
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом.")
        amount = float(amount)
        if amount <= 0:
            raise InvalidOperationError("Сумма должна быть больше нуля.")
        return amount

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

    @abstractmethod
    def deposit(self, amount: float) -> None:
        pass

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        pass

    @abstractmethod
    def get_account_info(self) -> dict:
        pass


class BankAccount(AbstractAccount):
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


class SavingsAccount(BankAccount):
    def __init__(
        self,
        owner: Owner,
        balance: float = 0.0,
        account_id: str | None = None,
        status: AccountStatus = AccountStatus.ACTIVE,
        currency: Currency = Currency.RUB,
        min_balance: float = 0.0,
        monthly_interest_rate: float = 0.01,
    ) -> None:
        super().__init__(
            owner=owner,
            balance=balance,
            account_id=account_id,
            status=status,
            currency=currency,
        )
        if not isinstance(min_balance, (int, float)) or min_balance < 0:
            raise ValueError("min_balance должен быть неотрицательным числом.")
        if not isinstance(monthly_interest_rate, (int, float)) or monthly_interest_rate < 0:
            raise ValueError("monthly_interest_rate должен быть неотрицательным числом.")

        self._min_balance = float(min_balance)
        self._monthly_interest_rate = float(monthly_interest_rate)

        if self.balance < self._min_balance:
            raise ValueError("Начальный баланс не может быть меньше min_balance.")

    @property
    def min_balance(self) -> float:
        return self._min_balance

    @property
    def monthly_interest_rate(self) -> float:
        return self._monthly_interest_rate

    def withdraw(self, amount: float) -> None:
        self._ensure_account_is_operable()
        valid_amount = self._validate_amount(amount)
        projected_balance = self._balance - valid_amount

        if projected_balance < self._min_balance:
            raise InvalidOperationError(
                f"Нельзя опустить баланс ниже минимального остатка {self._min_balance:.2f}."
            )

        self._balance = projected_balance

    def apply_monthly_interest(self) -> float:
        self._ensure_account_is_operable()
        interest = self._balance * self._monthly_interest_rate
        self._balance += interest
        return round(interest, 2)

    def get_account_info(self) -> dict:
        info = super().get_account_info()
        info.update(
            {
                "min_balance": round(self.min_balance, 2),
                "monthly_interest_rate": self.monthly_interest_rate,
            }
        )
        return info

    def __str__(self) -> str:
        last_4 = self.account_id[-4:]
        return (
            f"SavingsAccount(client='{self.owner.full_name}', "
            f"account='****{last_4}', "
            f"status='{self.status.value}', "
            f"balance={self.balance:.2f} {self.currency.value}, "
            f"min_balance={self.min_balance:.2f}, "
            f"monthly_rate={self.monthly_interest_rate:.2%})"
        )


class PremiumAccount(BankAccount):
    def __init__(
        self,
        owner: Owner,
        balance: float = 0.0,
        account_id: str | None = None,
        status: AccountStatus = AccountStatus.ACTIVE,
        currency: Currency = Currency.RUB,
        overdraft_limit: float = 10000.0,
        withdrawal_fee: float = 50.0,
        daily_withdrawal_limit: float = 500000.0,
    ) -> None:
        super().__init__(
            owner=owner,
            balance=balance,
            account_id=account_id,
            status=status,
            currency=currency,
        )

        if not isinstance(overdraft_limit, (int, float)) or overdraft_limit < 0:
            raise ValueError("overdraft_limit должен быть неотрицательным числом.")
        if not isinstance(withdrawal_fee, (int, float)) or withdrawal_fee < 0:
            raise ValueError("withdrawal_fee должен быть неотрицательным числом.")
        if not isinstance(daily_withdrawal_limit, (int, float)) or daily_withdrawal_limit <= 0:
            raise ValueError("daily_withdrawal_limit должен быть положительным числом.")

        self._overdraft_limit = float(overdraft_limit)
        self._withdrawal_fee = float(withdrawal_fee)
        self._daily_withdrawal_limit = float(daily_withdrawal_limit)

    @property
    def overdraft_limit(self) -> float:
        return self._overdraft_limit

    @property
    def withdrawal_fee(self) -> float:
        return self._withdrawal_fee

    @property
    def daily_withdrawal_limit(self) -> float:
        return self._daily_withdrawal_limit

    def withdraw(self, amount: float) -> None:
        self._ensure_account_is_operable()
        valid_amount = self._validate_amount(amount)

        if valid_amount > self._daily_withdrawal_limit:
            raise InvalidOperationError(
                f"Превышен лимит снятия для PremiumAccount: {self._daily_withdrawal_limit:.2f}."
            )

        total_debit = valid_amount + self._withdrawal_fee
        available_amount = self._balance + self._overdraft_limit

        if total_debit > available_amount:
            raise InsufficientFundsError(
                f"Недостаточно средств с учётом овердрафта: требуется {total_debit:.2f}, "
                f"доступно {available_amount:.2f}."
            )

        self._balance -= total_debit

    def get_account_info(self) -> dict:
        info = super().get_account_info()
        info.update(
            {
                "overdraft_limit": round(self.overdraft_limit, 2),
                "withdrawal_fee": round(self.withdrawal_fee, 2),
                "daily_withdrawal_limit": round(self.daily_withdrawal_limit, 2),
            }
        )
        return info

    def __str__(self) -> str:
        last_4 = self.account_id[-4:]
        return (
            f"PremiumAccount(client='{self.owner.full_name}', "
            f"account='****{last_4}', "
            f"status='{self.status.value}', "
            f"balance={self.balance:.2f} {self.currency.value}, "
            f"overdraft={self.overdraft_limit:.2f}, "
            f"fee={self.withdrawal_fee:.2f})"
        )


class InvestmentAccount(BankAccount):
    def __init__(
        self,
        owner: Owner,
        balance: float = 0.0,
        account_id: str | None = None,
        status: AccountStatus = AccountStatus.ACTIVE,
        currency: Currency = Currency.USD,
        portfolio: dict[str, float] | None = None,
    ) -> None:
        super().__init__(
            owner=owner,
            balance=balance,
            account_id=account_id,
            status=status,
            currency=currency,
        )

        self._portfolio: dict[str, float] = {
            AssetType.STOCKS.value: 0.0,
            AssetType.BONDS.value: 0.0,
            AssetType.ETF.value: 0.0,
        }

        if portfolio is not None:
            self._set_initial_portfolio(portfolio)

    @property
    def portfolio(self) -> dict[str, float]:
        return self._portfolio.copy()

    def _set_initial_portfolio(self, portfolio: dict[str, float]) -> None:
        if not isinstance(portfolio, dict):
            raise TypeError("portfolio должен быть словарём.")

        allowed_keys = {asset.value for asset in AssetType}
        for asset_name, amount in portfolio.items():
            if asset_name not in allowed_keys:
                raise InvalidOperationError(f"Недопустимый тип актива: {asset_name}.")
            if not isinstance(amount, (int, float)) or amount < 0:
                raise ValueError(f"Сумма актива {asset_name} должна быть неотрицательным числом.")
            self._portfolio[asset_name] = float(amount)

    def add_asset(self, asset_type: str, amount: float) -> None:
        self._ensure_account_is_operable()

        if asset_type not in self._portfolio:
            raise InvalidOperationError(f"Недопустимый тип актива: {asset_type}.")
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise InvalidOperationError("Сумма актива должна быть больше нуля.")

        self._portfolio[asset_type] += float(amount)

    def withdraw(self, amount: float) -> None:
        self._ensure_account_is_operable()
        valid_amount = self._validate_amount(amount)

        if valid_amount > self._balance:
            raise InsufficientFundsError(
                f"Недостаточно свободных денежных средств: запрошено {valid_amount:.2f}, "
                f"доступно {self._balance:.2f}."
            )

        self._balance -= valid_amount

    def get_total_portfolio_value(self) -> float:
        return round(sum(self._portfolio.values()), 2)

    def project_yearly_growth(self, growth_rates: dict[str, float] | None = None) -> dict[str, float]:
        default_growth_rates = {
            AssetType.STOCKS.value: 0.12,
            AssetType.BONDS.value: 0.05,
            AssetType.ETF.value: 0.08,
        }

        if growth_rates is None:
            growth_rates = default_growth_rates

        projected_portfolio: dict[str, float] = {}
        for asset_name, current_value in self._portfolio.items():
            rate = growth_rates.get(asset_name, 0.0)
            if not isinstance(rate, (int, float)):
                raise TypeError("Коэффициенты роста должны быть числами.")
            projected_portfolio[asset_name] = round(current_value * (1 + float(rate)), 2)

        projected_portfolio["total_projected_value"] = round(sum(projected_portfolio.values()), 2)
        return projected_portfolio

    def get_account_info(self) -> dict:
        info = super().get_account_info()
        info.update(
            {
                "portfolio": self.portfolio,
                "portfolio_total": self.get_total_portfolio_value(),
            }
        )
        return info

    def __str__(self) -> str:
        last_4 = self.account_id[-4:]
        return (
            f"InvestmentAccount(client='{self.owner.full_name}', "
            f"account='****{last_4}', "
            f"status='{self.status.value}', "
            f"cash_balance={self.balance:.2f} {self.currency.value}, "
            f"portfolio_total={self.get_total_portfolio_value():.2f})"
        )