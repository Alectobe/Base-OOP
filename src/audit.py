from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class AuditLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class AuditEntry:
    timestamp: datetime
    level: AuditLevel
    event_type: str
    message: str
    client_id: str | None = None
    account_id: str | None = None
    transaction_id: str | None = None
    risk_level: RiskLevel | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
            "level": self.level.value,
            "event_type": self.event_type,
            "message": self.message,
            "client_id": self.client_id,
            "account_id": self.account_id,
            "transaction_id": self.transaction_id,
            "risk_level": self.risk_level.value if self.risk_level else None,
            "metadata": self.metadata,
        }

    def to_line(self) -> str:
        return str(self.to_dict())


class AuditLog:
    def __init__(self, file_path: str | None = None) -> None:
        self._entries: list[AuditEntry] = []
        self._file_path = Path(file_path) if file_path else None

        if self._file_path is not None:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._file_path.exists():
                self._file_path.touch()

    @property
    def entries(self) -> list[AuditEntry]:
        return self._entries.copy()

    def log(
        self,
        level: AuditLevel,
        event_type: str,
        message: str,
        client_id: str | None = None,
        account_id: str | None = None,
        transaction_id: str | None = None,
        risk_level: RiskLevel | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(),
            level=level,
            event_type=event_type,
            message=message,
            client_id=client_id,
            account_id=account_id,
            transaction_id=transaction_id,
            risk_level=risk_level,
            metadata=metadata or {},
        )
        self._entries.append(entry)

        if self._file_path is not None:
            with self._file_path.open("a", encoding="utf-8") as file:
                file.write(entry.to_line() + "\n")

        return entry

    def filter_entries(
        self,
        level: AuditLevel | None = None,
        client_id: str | None = None,
        transaction_id: str | None = None,
        risk_level: RiskLevel | None = None,
        event_type: str | None = None,
    ) -> list[AuditEntry]:
        result = self._entries

        if level is not None:
            result = [entry for entry in result if entry.level == level]
        if client_id is not None:
            result = [entry for entry in result if entry.client_id == client_id]
        if transaction_id is not None:
            result = [entry for entry in result if entry.transaction_id == transaction_id]
        if risk_level is not None:
            result = [entry for entry in result if entry.risk_level == risk_level]
        if event_type is not None:
            result = [entry for entry in result if entry.event_type == event_type]

        return result

    def get_suspicious_operations_report(self) -> list[dict[str, Any]]:
        suspicious = [
            entry.to_dict()
            for entry in self._entries
            if entry.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}
        ]
        return suspicious

    def get_client_risk_profile(self, client_id: str) -> dict[str, Any]:
        client_entries = [entry for entry in self._entries if entry.client_id == client_id]
        risk_entries = [
            entry for entry in client_entries
            if entry.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}
        ]

        highest_risk = RiskLevel.LOW
        if any(entry.risk_level == RiskLevel.HIGH for entry in risk_entries):
            highest_risk = RiskLevel.HIGH
        elif any(entry.risk_level == RiskLevel.MEDIUM for entry in risk_entries):
            highest_risk = RiskLevel.MEDIUM

        return {
            "client_id": client_id,
            "total_events": len(client_entries),
            "suspicious_events": len(risk_entries),
            "high_risk_events": sum(1 for entry in risk_entries if entry.risk_level == RiskLevel.HIGH),
            "medium_risk_events": sum(1 for entry in risk_entries if entry.risk_level == RiskLevel.MEDIUM),
            "highest_risk": highest_risk.value,
        }

    def get_error_statistics(self) -> dict[str, Any]:
        error_entries = [
            entry for entry in self._entries
            if entry.level in {AuditLevel.ERROR, AuditLevel.CRITICAL}
        ]

        by_event_type: dict[str, int] = {}
        for entry in error_entries:
            by_event_type[entry.event_type] = by_event_type.get(entry.event_type, 0) + 1

        return {
            "total_errors": len(error_entries),
            "critical_errors": sum(1 for entry in error_entries if entry.level == AuditLevel.CRITICAL),
            "by_event_type": by_event_type,
        }


class RiskAnalyzer:
    def __init__(
        self,
        large_amount_threshold: float = 50000.0,
        frequent_operations_count: int = 3,
        frequent_operations_window_minutes: int = 10,
    ) -> None:
        self._large_amount_threshold = float(large_amount_threshold)
        self._frequent_operations_count = int(frequent_operations_count)
        self._frequent_operations_window = timedelta(minutes=frequent_operations_window_minutes)

        self._history_by_sender: dict[str, list[datetime]] = {}
        self._known_receivers_by_sender: dict[str, set[str]] = {}

    @staticmethod
    def _is_night_operation(operation_time: datetime) -> bool:
        return 0 <= operation_time.hour < 5

    def _is_large_amount(self, amount: float) -> bool:
        return amount >= self._large_amount_threshold

    def _is_frequent_operation(self, sender_account_id: str | None, operation_time: datetime) -> bool:
        if not sender_account_id:
            return False

        history = self._history_by_sender.setdefault(sender_account_id, [])
        lower_bound = operation_time - self._frequent_operations_window

        recent_operations = [item for item in history if item >= lower_bound]
        recent_operations.append(operation_time)

        history.clear()
        history.extend(recent_operations)

        return len(recent_operations) >= self._frequent_operations_count

    def _is_new_receiver(self, sender_account_id: str | None, receiver_account_id: str | None) -> bool:
        if not sender_account_id or not receiver_account_id:
            return False

        receivers = self._known_receivers_by_sender.setdefault(sender_account_id, set())
        if receiver_account_id in receivers:
            return False

        receivers.add(receiver_account_id)
        return True

    def analyze_transaction(self, transaction: Any, operation_time: datetime | None = None) -> dict[str, Any]:
        timestamp = operation_time or getattr(transaction, "created_at", datetime.now())

        triggers: list[str] = []

        if self._is_large_amount(float(transaction.amount)):
            triggers.append("large_amount")

        if self._is_frequent_operation(getattr(transaction, "sender_account_id", None), timestamp):
            triggers.append("frequent_operations")

        tx_type = getattr(transaction, "transaction_type", None)
        if tx_type is not None and getattr(tx_type, "value", "") in {"transfer_internal", "transfer_external"}:
            if self._is_new_receiver(
                getattr(transaction, "sender_account_id", None),
                getattr(transaction, "receiver_account_id", None),
            ):
                triggers.append("new_receiver")

        if self._is_night_operation(timestamp):
            triggers.append("night_operation")

        if "large_amount" in triggers and "night_operation" in triggers:
            risk_level = RiskLevel.HIGH
        elif len(triggers) >= 2:
            risk_level = RiskLevel.HIGH
        elif len(triggers) == 1:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return {
            "risk_level": risk_level,
            "triggers": triggers,
            "should_block": risk_level == RiskLevel.HIGH,
        }