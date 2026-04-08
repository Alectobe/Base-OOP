from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any

from src.models import (
    AccountStatus,
    BankAccount,
    InvalidOperationError,
    Owner,
)


class ClientStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


@dataclass
class Client:
    full_name: str
    client_id: str
    age: int
    contacts: dict[str, str]
    security_code: str
    status: ClientStatus = ClientStatus.ACTIVE
    account_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.full_name, str) or not self.full_name.strip():
            raise ValueError("ФИО клиента должно быть непустой строкой.")
        if not isinstance(self.client_id, str) or not self.client_id.strip():
            raise ValueError("ID клиента должен быть непустой строкой.")
        if not isinstance(self.age, int) or self.age < 18:
            raise ValueError("Клиент должен быть не моложе 18 лет.")
        if not isinstance(self.contacts, dict) or not self.contacts:
            raise ValueError("contacts должен быть непустым словарём.")
        if not isinstance(self.security_code, str) or not self.security_code.strip():
            raise ValueError("security_code должен быть непустой строкой.")
        if not isinstance(self.status, ClientStatus):
            raise TypeError("status должен быть экземпляром ClientStatus.")

    def add_account(self, account_id: str) -> None:
        if account_id not in self.account_ids:
            self.account_ids.append(account_id)

    def remove_account(self, account_id: str) -> None:
        if account_id in self.account_ids:
            self.account_ids.remove(account_id)

    def to_owner(self) -> Owner:
        return Owner(full_name=self.full_name, client_id=self.client_id)


class Bank:
    def __init__(self, name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название банка должно быть непустой строкой.")
        self._name = name
        self._clients: dict[str, Client] = {}
        self._accounts: dict[str, BankAccount] = {}
        self._failed_login_attempts: dict[str, int] = {}
        self._suspicious_actions: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def suspicious_actions(self) -> list[dict[str, Any]]:
        return self._suspicious_actions.copy()

    def add_client(self, client: Client) -> None:
        if not isinstance(client, Client):
            raise TypeError("client должен быть экземпляром Client.")
        if client.client_id in self._clients:
            raise InvalidOperationError(f"Клиент с ID {client.client_id} уже существует.")
        self._clients[client.client_id] = client
        self._failed_login_attempts[client.client_id] = 0

    def get_client(self, client_id: str) -> Client:
        client = self._clients.get(client_id)
        if client is None:
            raise InvalidOperationError(f"Клиент с ID {client_id} не найден.")
        return client

    def get_account(self, account_id: str) -> BankAccount:
        account = self._accounts.get(account_id)
        if account is None:
            raise InvalidOperationError(f"Счёт {account_id} не найден.")
        return account

    def _is_night_time(self, current_time: time | None = None) -> bool:
        now = current_time if current_time is not None else datetime.now().time()
        return time(0, 0) <= now < time(5, 0)

    def _check_operation_allowed(self, current_time: time | None = None) -> None:
        if self._is_night_time(current_time):
            raise InvalidOperationError("Операции запрещены в период с 00:00 до 05:00.")

    def _mark_suspicious_action(self, action_type: str, client_id: str, details: str) -> None:
        self._suspicious_actions.append(
            {
                "action_type": action_type,
                "client_id": client_id,
                "details": details,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def _convert_balance(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        exchange_rates: dict[tuple[str, str], float],
    ) -> float:
        if from_currency == to_currency:
            return round(amount, 2)

        rate = exchange_rates.get((from_currency, to_currency))
        if rate is None:
            raise InvalidOperationError(
                f"Нет курса конвертации {from_currency} -> {to_currency}."
            )
        return round(amount * rate, 2)

    def open_account(
        self,
        client_id: str,
        account_cls: type[BankAccount],
        current_time: time | None = None,
        **account_kwargs: Any,
    ) -> BankAccount:
        self._check_operation_allowed(current_time)

        client = self.get_client(client_id)
        if client.status == ClientStatus.BLOCKED:
            raise InvalidOperationError("Клиент заблокирован. Открытие счёта невозможно.")
        if not issubclass(account_cls, BankAccount):
            raise TypeError("account_cls должен быть классом, унаследованным от BankAccount.")

        account = account_cls(owner=client.to_owner(), **account_kwargs)
        self._accounts[account.account_id] = account
        client.add_account(account.account_id)
        return account

    def close_account(self, account_id: str, current_time: time | None = None) -> None:
        self._check_operation_allowed(current_time)

        account = self.get_account(account_id)
        account.close()

        client = self.get_client(account.owner.client_id)
        client.remove_account(account_id)

    def freeze_account(self, account_id: str, reason: str = "", current_time: time | None = None) -> None:
        self._check_operation_allowed(current_time)

        account = self.get_account(account_id)
        account.freeze()

        if reason:
            self._mark_suspicious_action(
                action_type="freeze_account",
                client_id=account.owner.client_id,
                details=f"Счёт {account_id} заморожен. Причина: {reason}",
            )

    def unfreeze_account(self, account_id: str, current_time: time | None = None) -> None:
        self._check_operation_allowed(current_time)

        account = self.get_account(account_id)
        account.activate()

    def authenticate_client(self, client_id: str, security_code: str) -> bool:
        client = self.get_client(client_id)

        if client.status == ClientStatus.BLOCKED:
            self._mark_suspicious_action(
                action_type="blocked_login_attempt",
                client_id=client_id,
                details="Попытка входа заблокированного клиента.",
            )
            return False

        if client.security_code == security_code:
            self._failed_login_attempts[client_id] = 0
            return True

        self._failed_login_attempts[client_id] += 1
        attempts = self._failed_login_attempts[client_id]

        self._mark_suspicious_action(
            action_type="failed_login",
            client_id=client_id,
            details=f"Неверный код доступа. Попытка #{attempts}.",
        )

        if attempts >= 3:
            client.status = ClientStatus.BLOCKED
            self._mark_suspicious_action(
                action_type="client_blocked",
                client_id=client_id,
                details="Клиент заблокирован после 3 неудачных попыток входа.",
            )

        return False

    def deposit_to_account(
        self,
        account_id: str,
        amount: float,
        current_time: time | None = None,
    ) -> None:
        self._check_operation_allowed(current_time)
        account = self.get_account(account_id)
        account.deposit(amount)

    def withdraw_from_account(
        self,
        account_id: str,
        amount: float,
        current_time: time | None = None,
    ) -> None:
        self._check_operation_allowed(current_time)
        account = self.get_account(account_id)
        account.withdraw(amount)

    def search_accounts(
        self,
        client_id: str | None = None,
        status: AccountStatus | None = None,
        currency: str | None = None,
        account_type: str | None = None,
    ) -> list[BankAccount]:
        result = list(self._accounts.values())

        if client_id is not None:
            result = [account for account in result if account.owner.client_id == client_id]

        if status is not None:
            result = [account for account in result if account.status == status]

        if currency is not None:
            result = [account for account in result if account.currency.value == currency]

        if account_type is not None:
            result = [account for account in result if account.__class__.__name__ == account_type]

        return result

    def get_total_balance(self) -> float:
        total = 0.0
        for account in self._accounts.values():
            if account.status != AccountStatus.CLOSED:
                total += account.balance
        return round(total, 2)

    def get_total_balance_converted(
        self,
        base_currency: str,
        exchange_rates: dict[tuple[str, str], float],
    ) -> float:
        total = 0.0

        for account in self._accounts.values():
            if account.status != AccountStatus.CLOSED:
                total += self._convert_balance(
                    amount=account.balance,
                    from_currency=account.currency.value,
                    to_currency=base_currency,
                    exchange_rates=exchange_rates,
                )

        return round(total, 2)

    def get_clients_ranking(self) -> list[dict[str, Any]]:
        ranking: list[dict[str, Any]] = []

        for client in self._clients.values():
            client_total = 0.0
            for account_id in client.account_ids:
                account = self._accounts.get(account_id)
                if account is not None and account.status != AccountStatus.CLOSED:
                    client_total += account.balance

            ranking.append(
                {
                    "client_id": client.client_id,
                    "full_name": client.full_name,
                    "status": client.status.value,
                    "total_balance": round(client_total, 2),
                    "accounts_count": len(client.account_ids),
                }
            )

        ranking.sort(key=lambda item: item["total_balance"], reverse=True)
        return ranking

    def get_clients_ranking_converted(
        self,
        base_currency: str,
        exchange_rates: dict[tuple[str, str], float],
    ) -> list[dict[str, Any]]:
        ranking: list[dict[str, Any]] = []

        for client in self._clients.values():
            client_total = 0.0

            for account_id in client.account_ids:
                account = self._accounts.get(account_id)
                if account is not None and account.status != AccountStatus.CLOSED:
                    client_total += self._convert_balance(
                        amount=account.balance,
                        from_currency=account.currency.value,
                        to_currency=base_currency,
                        exchange_rates=exchange_rates,
                    )

            ranking.append(
                {
                    "client_id": client.client_id,
                    "full_name": client.full_name,
                    "status": client.status.value,
                    "total_balance": round(client_total, 2),
                    "accounts_count": len(client.account_ids),
                    "base_currency": base_currency,
                }
            )

        ranking.sort(key=lambda item: item["total_balance"], reverse=True)
        return ranking