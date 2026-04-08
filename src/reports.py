from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from src.audit import AuditLog, RiskLevel
from src.bank import Bank
from src.transactions import Transaction, TransactionStatus, TransactionType


class ReportBuilder:
    def __init__(
        self,
        bank: Bank,
        transactions: list[Transaction],
        audit_log: AuditLog,
        base_output_dir: str = "reports",
    ) -> None:
        self._bank = bank
        self._transactions = transactions
        self._audit_log = audit_log
        self._base_output_dir = Path(base_output_dir)
        self._base_output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def output_dir(self) -> Path:
        return self._base_output_dir

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat(timespec="seconds")
        if hasattr(value, "value"):
            return value.value
        if is_dataclass(value):
            return asdict(value)
        return value

    def _serialize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return {key: self._serialize_value(value) for key, value in data.items()}

    def build_client_report(self, client_id: str) -> dict[str, Any]:
        client = self._bank.get_client(client_id)
        accounts = self._bank.search_accounts(client_id=client_id)
        account_ids = {account.account_id for account in accounts}

        client_transactions = [
            tx for tx in self._transactions
            if tx.sender_account_id in account_ids or tx.receiver_account_id in account_ids
        ]
        client_transactions.sort(key=lambda tx: tx.created_at)

        suspicious_entries = [
            entry.to_dict()
            for entry in self._audit_log.entries
            if entry.client_id == client_id and entry.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}
        ]

        report = {
            "report_type": "client",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "client": {
                "client_id": client.client_id,
                "full_name": client.full_name,
                "status": client.status.value,
                "contacts": client.contacts,
                "accounts_count": len(accounts),
            },
            "accounts": [account.get_account_info() for account in accounts],
            "transactions_summary": {
                "total_transactions": len(client_transactions),
                "completed": sum(1 for tx in client_transactions if tx.status == TransactionStatus.COMPLETED),
                "failed": sum(1 for tx in client_transactions if tx.status == TransactionStatus.FAILED),
                "blocked": sum(1 for tx in client_transactions if tx.status == TransactionStatus.BLOCKED),
                "cancelled": sum(1 for tx in client_transactions if tx.status == TransactionStatus.CANCELLED),
            },
            "transactions": [
                {
                    "transaction_id": tx.transaction_id,
                    "type": tx.transaction_type.value,
                    "amount": tx.amount,
                    "currency": tx.currency.value,
                    "sender_account_id": tx.sender_account_id,
                    "receiver_account_id": tx.receiver_account_id,
                    "status": tx.status.value,
                    "commission": tx.commission,
                    "failure_reason": tx.failure_reason,
                    "created_at": tx.created_at.isoformat(timespec="seconds"),
                }
                for tx in client_transactions
            ],
            "risk_profile": self._audit_log.get_client_risk_profile(client_id),
            "suspicious_operations": suspicious_entries,
        }
        return report

    def build_bank_report(
        self,
        base_currency: str = "RUB",
        exchange_rates: dict[tuple[str, str], float] | None = None,
    ) -> dict[str, Any]:
        if exchange_rates is None:
            raise ValueError("Для банкового отчёта нужен exchange_rates для мультивалютной агрегации.")

        ranking = self._bank.get_clients_ranking_converted(base_currency, exchange_rates)
        status_counter = Counter(tx.status.value for tx in self._transactions)
        type_counter = Counter(tx.transaction_type.value for tx in self._transactions)

        accounts = self._bank.search_accounts()
        currencies_counter = Counter(account.currency.value for account in accounts)
        account_types_counter = Counter(account.__class__.__name__ for account in accounts)

        report = {
            "report_type": "bank",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "bank_name": self._bank.name,
            "base_currency": base_currency,
            "total_balance_raw": self._bank.get_total_balance(),
            "total_balance_converted": self._bank.get_total_balance_converted(base_currency, exchange_rates),
            "clients_count": len(ranking),
            "accounts_count": len(accounts),
            "top_clients": ranking[:3],
            "transactions_statistics": {
                "total_transactions": len(self._transactions),
                "by_status": dict(status_counter),
                "by_type": dict(type_counter),
                "total_commissions": round(
                    sum(
                        tx.commission
                        for tx in self._transactions
                        if tx.status == TransactionStatus.COMPLETED
                    ),
                    2,
                ),
                "successful_external_commissions": round(
                    sum(
                        tx.commission
                        for tx in self._transactions
                        if tx.status == TransactionStatus.COMPLETED
                        and tx.transaction_type == TransactionType.TRANSFER_EXTERNAL
                    ),
                    2,
                ),
            },
            "accounts_statistics": {
                "by_currency": dict(currencies_counter),
                "by_type": dict(account_types_counter),
            },
            "audit_statistics": self._audit_log.get_error_statistics(),
        }
        return report

    def build_risk_report(self) -> dict[str, Any]:
        suspicious_entries = self._audit_log.get_suspicious_operations_report()

        risk_counter = Counter()
        for entry in self._audit_log.entries:
            if entry.risk_level is not None:
                risk_counter[entry.risk_level.value] += 1

        blocked_transactions = [
            {
                "transaction_id": tx.transaction_id,
                "type": tx.transaction_type.value,
                "amount": tx.amount,
                "currency": tx.currency.value,
                "status": tx.status.value,
                "failure_reason": tx.failure_reason,
            }
            for tx in self._transactions
            if tx.status == TransactionStatus.BLOCKED
        ]

        report = {
            "report_type": "risk",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "risk_statistics": dict(risk_counter),
            "suspicious_operations_count": len(suspicious_entries),
            "blocked_transactions_count": len(blocked_transactions),
            "blocked_transactions": blocked_transactions,
            "suspicious_operations": suspicious_entries,
        }
        return report

    def build_text_report(self, report_data: dict[str, Any]) -> str:
        report_type = report_data.get("report_type", "unknown")
        lines: list[str] = []
        lines.append(f"REPORT TYPE: {report_type.upper()}")
        lines.append(f"GENERATED AT: {report_data.get('generated_at', '-')}")
        lines.append("=" * 70)

        if report_type == "client":
            client = report_data["client"]
            lines.append(f"CLIENT: {client['full_name']} ({client['client_id']})")
            lines.append(f"STATUS: {client['status']}")
            lines.append(f"CONTACTS: {client['contacts']}")
            lines.append(f"ACCOUNTS COUNT: {client['accounts_count']}")
            lines.append("")

            lines.append("ACCOUNTS:")
            for account in report_data["accounts"]:
                lines.append(
                    f"  - {account['account_type']} | "
                    f"{account['account_id']} | "
                    f"{account['balance']} {account['currency']} | "
                    f"status={account['status']}"
                )

            lines.append("")
            lines.append("TRANSACTIONS SUMMARY:")
            for key, value in report_data["transactions_summary"].items():
                lines.append(f"  {key}: {value}")

            lines.append("")
            lines.append("RISK PROFILE:")
            for key, value in report_data["risk_profile"].items():
                lines.append(f"  {key}: {value}")

        elif report_type == "bank":
            lines.append(f"BANK NAME: {report_data['bank_name']}")
            lines.append(f"BASE CURRENCY: {report_data['base_currency']}")
            lines.append(f"TOTAL BALANCE RAW: {report_data['total_balance_raw']}")
            lines.append(f"TOTAL BALANCE CONVERTED: {report_data['total_balance_converted']}")
            lines.append(f"CLIENTS COUNT: {report_data['clients_count']}")
            lines.append(f"ACCOUNTS COUNT: {report_data['accounts_count']}")
            lines.append("")

            lines.append("TOP CLIENTS:")
            for item in report_data["top_clients"]:
                lines.append(
                    f"  - {item['full_name']} ({item['client_id']}) | "
                    f"balance={item['total_balance']} {item['base_currency']} | accounts={item['accounts_count']}"
                )

            lines.append("")
            lines.append("TRANSACTIONS STATISTICS:")
            for key, value in report_data["transactions_statistics"].items():
                lines.append(f"  {key}: {value}")

            lines.append("")
            lines.append("ACCOUNTS STATISTICS:")
            for key, value in report_data["accounts_statistics"].items():
                lines.append(f"  {key}: {value}")

            lines.append("")
            lines.append("AUDIT STATISTICS:")
            for key, value in report_data["audit_statistics"].items():
                lines.append(f"  {key}: {value}")

        elif report_type == "risk":
            lines.append("RISK STATISTICS:")
            for key, value in report_data["risk_statistics"].items():
                lines.append(f"  {key}: {value}")

            lines.append(f"SUSPICIOUS OPERATIONS COUNT: {report_data['suspicious_operations_count']}")
            lines.append(f"BLOCKED TRANSACTIONS COUNT: {report_data['blocked_transactions_count']}")

            lines.append("")
            lines.append("BLOCKED TRANSACTIONS:")
            for item in report_data["blocked_transactions"]:
                lines.append(
                    f"  - {item['transaction_id']} | {item['type']} | "
                    f"{item['amount']} {item['currency']} | {item['failure_reason']}"
                )

        else:
            for key, value in report_data.items():
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

    def export_to_json(self, report_data: dict[str, Any], filename: str) -> Path:
        file_path = self._base_output_dir / filename
        serializable = self._serialize_dict(report_data)

        with file_path.open("w", encoding="utf-8") as file:
            json.dump(serializable, file, ensure_ascii=False, indent=4)

        return file_path

    def export_to_csv(self, rows: list[dict[str, Any]], filename: str) -> Path:
        file_path = self._base_output_dir / filename

        if not rows:
            with file_path.open("w", encoding="utf-8", newline="") as file:
                file.write("")
            return file_path

        fieldnames = list(rows[0].keys())

        with file_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(self._serialize_dict(row))

        return file_path

    def save_text_report(self, text: str, filename: str) -> Path:
        file_path = self._base_output_dir / filename
        file_path.write_text(text, encoding="utf-8")
        return file_path

    def save_charts(self, prefix: str = "report") -> list[Path]:
        chart_dir = self._base_output_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)

        saved_files: list[Path] = []

        status_counter = Counter(tx.status.value for tx in self._transactions)
        if status_counter:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.pie(status_counter.values(), labels=status_counter.keys(), autopct="%1.1f%%")
            ax.set_title("Распределение транзакций по статусам")
            file_path = chart_dir / f"{prefix}_pie_status.png"
            fig.savefig(file_path, bbox_inches="tight")
            plt.close(fig)
            saved_files.append(file_path)

        type_counter = Counter(tx.transaction_type.value for tx in self._transactions)
        if type_counter:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(list(type_counter.keys()), list(type_counter.values()))
            ax.set_title("Количество транзакций по типам")
            ax.set_xlabel("Тип транзакции")
            ax.set_ylabel("Количество")
            file_path = chart_dir / f"{prefix}_bar_types.png"
            fig.savefig(file_path, bbox_inches="tight")
            plt.close(fig)
            saved_files.append(file_path)

        completed_transactions = sorted(
            [tx for tx in self._transactions if tx.status == TransactionStatus.COMPLETED],
            key=lambda tx: tx.created_at,
        )

        if completed_transactions:
            running_total = 0.0
            x_values: list[str] = []
            y_values: list[float] = []

            for tx in completed_transactions:
                delta = 0.0

                if tx.transaction_type == TransactionType.DEPOSIT:
                    delta = tx.amount
                elif tx.transaction_type == TransactionType.WITHDRAW:
                    delta = -tx.amount
                elif tx.transaction_type == TransactionType.TRANSFER_EXTERNAL:
                    delta = -(tx.amount + tx.commission)
                elif tx.transaction_type == TransactionType.TRANSFER_INTERNAL:
                    delta = 0.0

                running_total += delta
                x_values.append(tx.created_at.strftime("%H:%M"))
                y_values.append(round(running_total, 2))

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(x_values, y_values, marker="o")
            ax.set_title("График движения условного баланса")
            ax.set_xlabel("Время")
            ax.set_ylabel("Баланс")
            plt.xticks(rotation=45)
            file_path = chart_dir / f"{prefix}_line_balance.png"
            fig.savefig(file_path, bbox_inches="tight")
            plt.close(fig)
            saved_files.append(file_path)

        return saved_files