from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from heapq import heappop, heappush
from itertools import count
from typing import Any
from uuid import uuid4

from src.audit import AuditLevel, AuditLog, RiskAnalyzer, RiskLevel
from src.bank import Bank
from src.models import (
    AccountStatus,
    BankAccount,
    Currency,
    InvalidOperationError,
    PremiumAccount,
)


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    TRANSFER_INTERNAL = "transfer_internal"
    TRANSFER_EXTERNAL = "transfer_external"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DELAYED = "delayed"
    BLOCKED = "blocked"


@dataclass
class Transaction:
    transaction_type: TransactionType
    amount: float
    currency: Currency
    sender_account_id: str | None = None
    receiver_account_id: str | None = None
    commission: float = 0.0
    status: TransactionStatus = TransactionStatus.PENDING
    failure_reason: str = ""
    scheduled_at: datetime | None = None
    max_retries: int = 2
    retry_delay_seconds: int = 60
    transaction_id: str = field(default_factory=lambda: uuid4().hex[:10].upper())
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime | None = None
    retries_used: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.transaction_type, TransactionType):
            raise TypeError("transaction_type должен быть экземпляром TransactionType.")
        if not isinstance(self.currency, Currency):
            raise TypeError("currency должен быть экземпляром Currency.")
        if not isinstance(self.amount, (int, float)) or float(self.amount) <= 0:
            raise ValueError("amount должен быть положительным числом.")
        if not isinstance(self.commission, (int, float)) or float(self.commission) < 0:
            raise ValueError("commission должен быть неотрицательным числом.")
        if not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValueError("max_retries должен быть целым числом >= 0.")
        if not isinstance(self.retry_delay_seconds, int) or self.retry_delay_seconds <= 0:
            raise ValueError("retry_delay_seconds должен быть целым числом > 0.")

        self.amount = float(self.amount)
        self.commission = float(self.commission)

    def can_run_now(self, now: datetime | None = None) -> bool:
        current = now or datetime.now()
        return self.scheduled_at is None or self.scheduled_at <= current

    def mark_processing(self) -> None:
        self.status = TransactionStatus.PROCESSING
        self.updated_at = datetime.now()

    def mark_completed(self) -> None:
        self.status = TransactionStatus.COMPLETED
        self.failure_reason = ""
        self.updated_at = datetime.now()
        self.processed_at = self.updated_at

    def mark_failed(self, reason: str) -> None:
        self.status = TransactionStatus.FAILED
        self.failure_reason = reason
        self.updated_at = datetime.now()

    def mark_cancelled(self, reason: str = "Отменено пользователем.") -> None:
        self.status = TransactionStatus.CANCELLED
        self.failure_reason = reason
        self.updated_at = datetime.now()

    def mark_delayed(self, reason: str, base_time: datetime | None = None) -> None:
        reference_time = base_time or datetime.now()
        delay_seconds = self.retry_delay_seconds * self.retries_used
        self.status = TransactionStatus.DELAYED
        self.failure_reason = reason
        self.scheduled_at = reference_time + timedelta(seconds=delay_seconds)
        self.updated_at = datetime.now()

    def mark_blocked(self, reason: str) -> None:
        self.status = TransactionStatus.BLOCKED
        self.failure_reason = reason
        self.updated_at = datetime.now()


class TransactionQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[int, datetime, int, Transaction]] = []
        self._sequence = count()
        self._cancelled_ids: set[str] = set()

    def add_transaction(self, transaction: Transaction, priority: int = 100) -> None:
        if not isinstance(transaction, Transaction):
            raise TypeError("transaction должен быть экземпляром Transaction.")
        if not isinstance(priority, int):
            raise TypeError("priority должен быть целым числом.")

        scheduled_at = transaction.scheduled_at or transaction.created_at
        heappush(self._heap, (priority, scheduled_at, next(self._sequence), transaction))

    def cancel_transaction(self, transaction_id: str) -> bool:
        self._cancelled_ids.add(transaction_id)
        return True

    def pop_ready_transaction(self, now: datetime | None = None) -> Transaction | None:
        current = now or datetime.now()
        skipped: list[tuple[int, datetime, int, Transaction]] = []

        while self._heap:
            item = heappop(self._heap)
            _, _, _, transaction = item

            if transaction.transaction_id in self._cancelled_ids:
                transaction.mark_cancelled()
                continue

            if transaction.can_run_now(current):
                for skipped_item in skipped:
                    heappush(self._heap, skipped_item)
                return transaction

            skipped.append(item)

        for skipped_item in skipped:
            heappush(self._heap, skipped_item)

        return None

    def has_pending(self) -> bool:
        return len(self._heap) > 0

    def size(self) -> int:
        return len(self._heap)


class TransactionProcessor:
    def __init__(
        self,
        bank: Bank,
        exchange_rates: dict[tuple[str, str], float] | None = None,
        external_transfer_fee_rate: float = 0.02,
        fixed_external_fee: float = 30.0,
        audit_log: AuditLog | None = None,
        risk_analyzer: RiskAnalyzer | None = None,
    ) -> None:
        self._bank = bank
        self._exchange_rates = exchange_rates or {
            ("RUB", "USD"): 0.011,
            ("USD", "RUB"): 90.0,
            ("EUR", "USD"): 1.08,
            ("USD", "EUR"): 0.93,
            ("RUB", "EUR"): 0.010,
            ("EUR", "RUB"): 98.0,
            ("KZT", "RUB"): 0.19,
            ("RUB", "KZT"): 5.2,
            ("CNY", "RUB"): 12.5,
            ("RUB", "CNY"): 0.08,
        }
        self._external_transfer_fee_rate = float(external_transfer_fee_rate)
        self._fixed_external_fee = float(fixed_external_fee)
        self._error_log: list[dict[str, str]] = []
        self._processed_transactions: list[Transaction] = []
        self._audit_log = audit_log
        self._risk_analyzer = risk_analyzer

    @property
    def error_log(self) -> list[dict[str, str]]:
        return self._error_log.copy()

    @property
    def processed_transactions(self) -> list[Transaction]:
        return self._processed_transactions.copy()

    @property
    def exchange_rates(self) -> dict[tuple[str, str], float]:
        return self._exchange_rates.copy()

    def _log_audit(
        self,
        level: AuditLevel,
        event_type: str,
        message: str,
        transaction: Transaction,
        risk_level: RiskLevel | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._audit_log is None:
            return

        client_id = None
        account_id = transaction.sender_account_id or transaction.receiver_account_id

        if transaction.sender_account_id:
            try:
                sender = self._bank.get_account(transaction.sender_account_id)
                client_id = sender.owner.client_id
            except Exception:
                client_id = None
        elif transaction.receiver_account_id:
            try:
                receiver = self._bank.get_account(transaction.receiver_account_id)
                client_id = receiver.owner.client_id
            except Exception:
                client_id = None

        self._audit_log.log(
            level=level,
            event_type=event_type,
            message=message,
            client_id=client_id,
            account_id=account_id,
            transaction_id=transaction.transaction_id,
            risk_level=risk_level,
            metadata=extra_metadata or {},
        )

    def _log_error(self, transaction: Transaction, message: str) -> None:
        self._error_log.append(
            {
                "transaction_id": transaction.transaction_id,
                "message": message,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def _convert_amount(self, amount: float, from_currency: Currency, to_currency: Currency) -> float:
        if from_currency == to_currency:
            return round(amount, 2)

        rate = self._exchange_rates.get((from_currency.value, to_currency.value))
        if rate is None:
            raise InvalidOperationError(
                f"Нет курса конвертации {from_currency.value} -> {to_currency.value}."
            )
        return round(amount * rate, 2)

    def _check_account_operable(self, account: BankAccount) -> None:
        if account.status == AccountStatus.FROZEN:
            raise InvalidOperationError(f"Счёт {account.account_id} заморожен.")
        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError(f"Счёт {account.account_id} закрыт.")

    def _ensure_transfer_allowed(self, sender: BankAccount, amount: float) -> None:
        if isinstance(sender, PremiumAccount):
            return
        if sender.balance - amount < 0:
            raise InvalidOperationError(
                "Перевод запрещён: недостаточно средств, минус разрешён только для PremiumAccount."
            )

    def _calculate_external_commission(self, amount: float) -> float:
        return round(amount * self._external_transfer_fee_rate + self._fixed_external_fee, 2)

    def _analyze_risk(self, transaction: Transaction) -> dict[str, Any] | None:
        if self._risk_analyzer is None:
            return None
        return self._risk_analyzer.analyze_transaction(transaction, operation_time=transaction.created_at)

    def process_transaction(self, transaction: Transaction) -> bool:
        risk_result = self._analyze_risk(transaction)

        if risk_result is not None:
            risk_level = risk_result["risk_level"]
            triggers = risk_result["triggers"]

            if risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}:
                self._log_audit(
                    level=AuditLevel.WARNING if risk_level == RiskLevel.MEDIUM else AuditLevel.CRITICAL,
                    event_type="risk_detected",
                    message=f"Обнаружен риск {risk_level.value}: {', '.join(triggers) if triggers else 'no_triggers'}",
                    transaction=transaction,
                    risk_level=risk_level,
                    extra_metadata={"triggers": triggers},
                )

            if risk_result["should_block"]:
                transaction.mark_blocked("Операция заблокирована системой риск-анализа.")
                self._log_error(transaction, transaction.failure_reason)
                self._log_audit(
                    level=AuditLevel.CRITICAL,
                    event_type="transaction_blocked",
                    message="Операция заблокирована как опасная.",
                    transaction=transaction,
                    risk_level=risk_level,
                    extra_metadata={"triggers": triggers},
                )
                return False

        transaction.mark_processing()

        try:
            if transaction.transaction_type == TransactionType.DEPOSIT:
                self._process_deposit(transaction)
            elif transaction.transaction_type == TransactionType.WITHDRAW:
                self._process_withdraw(transaction)
            elif transaction.transaction_type == TransactionType.TRANSFER_INTERNAL:
                self._process_internal_transfer(transaction)
            elif transaction.transaction_type == TransactionType.TRANSFER_EXTERNAL:
                self._process_external_transfer(transaction)
            else:
                raise InvalidOperationError("Неизвестный тип транзакции.")

            transaction.mark_completed()
            self._processed_transactions.append(transaction)

            self._log_audit(
                level=AuditLevel.INFO,
                event_type="transaction_completed",
                message="Транзакция успешно выполнена.",
                transaction=transaction,
            )
            return True

        except Exception as error:
            transaction.retries_used += 1
            self._log_error(transaction, str(error))

            if transaction.retries_used <= transaction.max_retries:
                transaction.mark_delayed(str(error))
            else:
                transaction.mark_failed(str(error))

            self._log_audit(
                level=AuditLevel.ERROR,
                event_type="transaction_failed",
                message=str(error),
                transaction=transaction,
            )
            return False

    def _process_deposit(self, transaction: Transaction) -> None:
        if not transaction.receiver_account_id:
            raise InvalidOperationError("Для deposit требуется receiver_account_id.")

        receiver = self._bank.get_account(transaction.receiver_account_id)
        self._check_account_operable(receiver)

        amount_in_receiver_currency = self._convert_amount(
            transaction.amount,
            transaction.currency,
            receiver.currency,
        )
        receiver.deposit(amount_in_receiver_currency)

    def _process_withdraw(self, transaction: Transaction) -> None:
        if not transaction.sender_account_id:
            raise InvalidOperationError("Для withdraw требуется sender_account_id.")

        sender = self._bank.get_account(transaction.sender_account_id)
        self._check_account_operable(sender)

        amount_in_sender_currency = self._convert_amount(
            transaction.amount,
            transaction.currency,
            sender.currency,
        )
        sender.withdraw(amount_in_sender_currency)

    def _process_internal_transfer(self, transaction: Transaction) -> None:
        if not transaction.sender_account_id or not transaction.receiver_account_id:
            raise InvalidOperationError("Для внутреннего перевода нужны sender_account_id и receiver_account_id.")

        sender = self._bank.get_account(transaction.sender_account_id)
        receiver = self._bank.get_account(transaction.receiver_account_id)

        self._check_account_operable(sender)
        self._check_account_operable(receiver)

        amount_in_sender_currency = self._convert_amount(
            transaction.amount,
            transaction.currency,
            sender.currency,
        )

        self._ensure_transfer_allowed(sender, amount_in_sender_currency)
        sender.withdraw(amount_in_sender_currency)

        amount_in_receiver_currency = self._convert_amount(
            transaction.amount,
            transaction.currency,
            receiver.currency,
        )
        receiver.deposit(amount_in_receiver_currency)

    def _process_external_transfer(self, transaction: Transaction) -> None:
        if not transaction.sender_account_id:
            raise InvalidOperationError("Для внешнего перевода требуется sender_account_id.")

        sender = self._bank.get_account(transaction.sender_account_id)
        self._check_account_operable(sender)

        amount_in_sender_currency = self._convert_amount(
            transaction.amount,
            transaction.currency,
            sender.currency,
        )
        commission = self._calculate_external_commission(amount_in_sender_currency)

        if not isinstance(sender, PremiumAccount) and sender.balance - (amount_in_sender_currency + commission) < 0:
            raise InvalidOperationError(
                "Внешний перевод запрещён: недостаточно средств с учётом комиссии."
            )

        sender.withdraw(amount_in_sender_currency + commission)
        transaction.commission = commission

    def process_queue(self, queue: TransactionQueue, now: datetime | None = None) -> list[Transaction]:
        processed: list[Transaction] = []
        current_now = now or datetime.now()

        while queue.has_pending():
            transaction = queue.pop_ready_transaction(now=current_now)
            if transaction is None:
                break

            success = self.process_transaction(transaction)

            if transaction.status != TransactionStatus.CANCELLED:
                processed.append(transaction)

            if not success and transaction.status == TransactionStatus.DELAYED:
                queue.add_transaction(transaction, priority=50)

        return processed