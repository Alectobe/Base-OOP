from __future__ import annotations

from collections import Counter
from datetime import datetime, time
from typing import Iterable

from src.audit import AuditLog, RiskAnalyzer, RiskLevel
from src.bank import Bank, Client
from src.models import Currency, InvestmentAccount, PremiumAccount, SavingsAccount
from src.transactions import (
    Transaction,
    TransactionProcessor,
    TransactionQueue,
    TransactionStatus,
    TransactionType,
)


def print_separator(title: str) -> None:
    print("\n" + "=" * 25 + f" {title} " + "=" * 25)


def short_account(account_id: str) -> str:
    return f"****{account_id[-4:]}"


def create_clients(bank: Bank) -> list[Client]:
    clients = [
        Client(
            full_name="Иван Петров",
            client_id="C001",
            age=31,
            contacts={"phone": "+79990000001", "email": "ivan@example.com"},
            security_code="1111",
        ),
        Client(
            full_name="Анна Смирнова",
            client_id="C002",
            age=28,
            contacts={"phone": "+79990000002", "email": "anna@example.com"},
            security_code="2222",
        ),
        Client(
            full_name="Олег Сидоров",
            client_id="C003",
            age=35,
            contacts={"phone": "+79990000003", "email": "oleg@example.com"},
            security_code="3333",
        ),
        Client(
            full_name="Мария Кузнецова",
            client_id="C004",
            age=26,
            contacts={"phone": "+79990000004", "email": "maria@example.com"},
            security_code="4444",
        ),
        Client(
            full_name="Дмитрий Волков",
            client_id="C005",
            age=40,
            contacts={"phone": "+79990000005", "email": "dmitry@example.com"},
            security_code="5555",
        ),
        Client(
            full_name="Елена Орлова",
            client_id="C006",
            age=33,
            contacts={"phone": "+79990000006", "email": "elena@example.com"},
            security_code="6666",
        ),
    ]

    for client in clients:
        bank.add_client(client)

    return clients


def create_accounts(bank: Bank) -> dict[str, object]:
    accounts: dict[str, object] = {}

    accounts["ivan_savings"] = bank.open_account(
        client_id="C001",
        account_cls=SavingsAccount,
        balance=120000.0,
        currency=Currency.RUB,
        min_balance=5000.0,
        monthly_interest_rate=0.012,
        current_time=time(10, 0),
    )
    accounts["ivan_premium"] = bank.open_account(
        client_id="C001",
        account_cls=PremiumAccount,
        balance=4000.0,
        currency=Currency.USD,
        overdraft_limit=7000.0,
        withdrawal_fee=15.0,
        daily_withdrawal_limit=40000.0,
        current_time=time(10, 1),
    )

    accounts["anna_savings"] = bank.open_account(
        client_id="C002",
        account_cls=SavingsAccount,
        balance=15000.0,
        currency=Currency.EUR,
        min_balance=1000.0,
        monthly_interest_rate=0.01,
        current_time=time(10, 2),
    )
    accounts["anna_invest"] = bank.open_account(
        client_id="C002",
        account_cls=InvestmentAccount,
        balance=12000.0,
        currency=Currency.USD,
        portfolio={"stocks": 7000.0, "bonds": 2500.0, "etf": 3000.0},
        current_time=time(10, 3),
    )

    accounts["oleg_premium"] = bank.open_account(
        client_id="C003",
        account_cls=PremiumAccount,
        balance=30000.0,
        currency=Currency.RUB,
        overdraft_limit=10000.0,
        withdrawal_fee=25.0,
        daily_withdrawal_limit=100000.0,
        current_time=time(10, 4),
    )
    accounts["oleg_savings"] = bank.open_account(
        client_id="C003",
        account_cls=SavingsAccount,
        balance=900000.0,
        currency=Currency.KZT,
        min_balance=100000.0,
        monthly_interest_rate=0.008,
        current_time=time(10, 5),
    )

    accounts["maria_invest"] = bank.open_account(
        client_id="C004",
        account_cls=InvestmentAccount,
        balance=8000.0,
        currency=Currency.EUR,
        portfolio={"stocks": 2500.0, "bonds": 1500.0, "etf": 1800.0},
        current_time=time(10, 6),
    )
    accounts["maria_premium"] = bank.open_account(
        client_id="C004",
        account_cls=PremiumAccount,
        balance=6000.0,
        currency=Currency.USD,
        overdraft_limit=5000.0,
        withdrawal_fee=10.0,
        daily_withdrawal_limit=35000.0,
        current_time=time(10, 7),
    )

    accounts["dmitry_savings"] = bank.open_account(
        client_id="C005",
        account_cls=SavingsAccount,
        balance=20000.0,
        currency=Currency.CNY,
        min_balance=3000.0,
        monthly_interest_rate=0.009,
        current_time=time(10, 8),
    )
    accounts["dmitry_premium"] = bank.open_account(
        client_id="C005",
        account_cls=PremiumAccount,
        balance=25000.0,
        currency=Currency.RUB,
        overdraft_limit=8000.0,
        withdrawal_fee=20.0,
        daily_withdrawal_limit=80000.0,
        current_time=time(10, 9),
    )

    accounts["elena_invest"] = bank.open_account(
        client_id="C006",
        account_cls=InvestmentAccount,
        balance=18000.0,
        currency=Currency.USD,
        portfolio={"stocks": 9000.0, "bonds": 4000.0, "etf": 3500.0},
        current_time=time(10, 10),
    )
    accounts["elena_savings"] = bank.open_account(
        client_id="C006",
        account_cls=SavingsAccount,
        balance=9000.0,
        currency=Currency.RUB,
        min_balance=1500.0,
        monthly_interest_rate=0.011,
        current_time=time(10, 11),
    )

    return accounts


def show_all_clients(clients: Iterable[Client]) -> None:
    print_separator("КЛИЕНТЫ БАНКА")
    for client in clients:
        print(
            f"{client.client_id} | {client.full_name} | "
            f"status={client.status.value} | contacts={client.contacts}"
        )


def show_all_accounts(accounts: dict[str, object]) -> None:
    print_separator("СОЗДАННЫЕ СЧЕТА")
    for alias, account in accounts.items():
        print(f"{alias:16} -> {account}")


def build_transactions(accounts: dict[str, object]) -> list[Transaction]:
    base_day = datetime(2026, 4, 7)

    txs = [
        Transaction(TransactionType.DEPOSIT, 5000.0, Currency.RUB, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=0)),
        Transaction(TransactionType.WITHDRAW, 2000.0, Currency.RUB, sender_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=2)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 150.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=3)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 120.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, created_at=base_day.replace(hour=2, minute=15)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 5000.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, receiver_account_id=accounts["dmitry_premium"].account_id, created_at=base_day.replace(hour=11, minute=5)),
        Transaction(TransactionType.WITHDRAW, 250.0, Currency.USD, sender_account_id=accounts["maria_premium"].account_id, created_at=base_day.replace(hour=11, minute=6)),
        Transaction(TransactionType.DEPOSIT, 800.0, Currency.USD, receiver_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=7)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 3000.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=8)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 100.0, Currency.EUR, sender_account_id=accounts["anna_savings"].account_id, receiver_account_id=accounts["maria_invest"].account_id, created_at=base_day.replace(hour=11, minute=9)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 700.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=11, minute=10)),
        Transaction(TransactionType.DEPOSIT, 1000.0, Currency.CNY, receiver_account_id=accounts["dmitry_savings"].account_id, created_at=base_day.replace(hour=11, minute=11)),
        Transaction(TransactionType.WITHDRAW, 50000.0, Currency.KZT, sender_account_id=accounts["oleg_savings"].account_id, created_at=base_day.replace(hour=11, minute=12)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 200.0, Currency.USD, sender_account_id=accounts["elena_invest"].account_id, receiver_account_id=accounts["maria_premium"].account_id, created_at=base_day.replace(hour=11, minute=13)),
        Transaction(TransactionType.DEPOSIT, 600.0, Currency.RUB, receiver_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=14)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 180.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=15)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 190.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=17)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 210.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["dmitry_premium"].account_id, created_at=base_day.replace(hour=11, minute=18)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 70000.0, Currency.RUB, sender_account_id=accounts["ivan_savings"].account_id, receiver_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=1, minute=10)),
        Transaction(TransactionType.WITHDRAW, 50000.0, Currency.RUB, sender_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=20), max_retries=0),
        Transaction(TransactionType.DEPOSIT, 300.0, Currency.CNY, receiver_account_id=accounts["dmitry_savings"].account_id, created_at=base_day.replace(hour=11, minute=21), max_retries=0),
        Transaction(TransactionType.TRANSFER_INTERNAL, 50000.0, Currency.EUR, sender_account_id=accounts["anna_savings"].account_id, receiver_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=22), max_retries=0),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 50.0, Currency.USD, sender_account_id=accounts["maria_premium"].account_id, created_at=base_day.replace(hour=11, minute=23)),
        Transaction(TransactionType.DEPOSIT, 20000.0, Currency.KZT, receiver_account_id=accounts["oleg_savings"].account_id, created_at=base_day.replace(hour=11, minute=24)),
        Transaction(TransactionType.WITHDRAW, 1000.0, Currency.USD, sender_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=25)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 800.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=26)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 900.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=27)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 1000.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=28)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 2000.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=2, minute=0)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 65000.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=2, minute=30)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 300.0, Currency.USD, sender_account_id=accounts["elena_invest"].account_id, receiver_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=29)),
        Transaction(TransactionType.DEPOSIT, 400.0, Currency.EUR, receiver_account_id=accounts["maria_invest"].account_id, created_at=base_day.replace(hour=11, minute=30)),
        Transaction(TransactionType.WITHDRAW, 50.0, Currency.EUR, sender_account_id=accounts["anna_savings"].account_id, created_at=base_day.replace(hour=11, minute=31)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 100000.0, Currency.KZT, sender_account_id=accounts["oleg_savings"].account_id, receiver_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=11, minute=32)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 20000.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, created_at=base_day.replace(hour=11, minute=33), max_retries=0),
        Transaction(TransactionType.DEPOSIT, 750.0, Currency.RUB, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=34)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 500.0, Currency.RUB, sender_account_id=accounts["ivan_savings"].account_id, receiver_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=35)),
    ]

    return txs


def enqueue_transactions(queue: TransactionQueue, transactions: list[Transaction]) -> None:
    print_separator("ПОПАДАНИЕ ТРАНЗАКЦИЙ В ОЧЕРЕДЬ")
    for index, tx in enumerate(transactions, start=1):
        priority = (index % 7) + 1
        queue.add_transaction(tx, priority=priority)
        print(
            f"QUEUE | tx={tx.transaction_id} | type={tx.transaction_type.value} | "
            f"priority={priority} | amount={tx.amount:.2f} {tx.currency.value}"
        )


def process_transactions(processor: TransactionProcessor, queue: TransactionQueue) -> list[Transaction]:
    print_separator("ИСПОЛНЕНИЕ ОЧЕРЕДИ")
    processed = processor.process_queue(queue, now=datetime(2026, 4, 7, 16, 0, 0))

    for tx in processed:
        print(
            f"EXEC  | tx={tx.transaction_id} | type={tx.transaction_type.value} | "
            f"status={tx.status.value} | reason={tx.failure_reason or '-'} | "
            f"fee={tx.commission:.2f}"
        )

    return processed


def show_client_accounts(bank: Bank, client_id: str) -> None:
    client = bank.get_client(client_id)

    print_separator(f"СЧЕТА КЛИЕНТА {client.full_name}")
    accounts = bank.search_accounts(client_id=client_id)

    for account in accounts:
        print(account)

    if not accounts:
        print("Счета не найдены.")


def show_client_history(bank: Bank, client_id: str, transactions: list[Transaction]) -> None:
    client = bank.get_client(client_id)
    account_ids = set(client.account_ids)

    history = [
        tx for tx in transactions
        if tx.sender_account_id in account_ids or tx.receiver_account_id in account_ids
    ]
    history.sort(key=lambda item: item.created_at)

    print_separator(f"ИСТОРИЯ КЛИЕНТА {client.full_name}")
    if not history:
        print("История пуста.")
        return

    for tx in history:
        sender = short_account(tx.sender_account_id) if tx.sender_account_id else "BANK"
        receiver = short_account(tx.receiver_account_id) if tx.receiver_account_id else "EXTERNAL"
        print(
            f"{tx.created_at.strftime('%Y-%m-%d %H:%M')} | "
            f"{tx.transaction_id} | {tx.transaction_type.value:18} | "
            f"{sender:8} -> {receiver:8} | "
            f"{tx.amount:10.2f} {tx.currency.value} | "
            f"{tx.status.value:10} | {tx.failure_reason or '-'}"
        )


def show_client_suspicious_operations(audit_log: AuditLog, client_id: str) -> None:
    print_separator(f"ПОДОЗРИТЕЛЬНЫЕ ОПЕРАЦИИ КЛИЕНТА {client_id}")
    entries = [
        entry for entry in audit_log.entries
        if entry.client_id == client_id and entry.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}
    ]

    if not entries:
        print("Подозрительные операции не найдены.")
        return

    for entry in entries:
        print(
            f"{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{entry.level.value:8} | {entry.event_type:20} | "
            f"risk={entry.risk_level.value if entry.risk_level else '-'} | "
            f"{entry.message}"
        )


def show_top_clients(bank: Bank) -> None:
    print_separator("ТОП-3 КЛИЕНТОВ")
    ranking = bank.get_clients_ranking()[:3]

    for index, item in enumerate(ranking, start=1):
        print(
            f"{index}. {item['full_name']} ({item['client_id']}) | "
            f"accounts={item['accounts_count']} | "
            f"total_balance={item['total_balance']:.2f}"
        )


def show_transaction_statistics(transactions: list[Transaction], audit_log: AuditLog) -> None:
    print_separator("СТАТИСТИКА ТРАНЗАКЦИЙ")

    status_counter = Counter(tx.status.value for tx in transactions)
    type_counter = Counter(tx.transaction_type.value for tx in transactions)
    total_fees = sum(tx.commission for tx in transactions)
    suspicious_count = len(audit_log.get_suspicious_operations_report())
    error_stats = audit_log.get_error_statistics()

    print("По статусам:")
    for status, count in sorted(status_counter.items()):
        print(f"  {status:10} -> {count}")

    print("По типам:")
    for tx_type, count in sorted(type_counter.items()):
        print(f"  {tx_type:18} -> {count}")

    print(f"Всего комиссий: {total_fees:.2f}")
    print(f"Подозрительных audit events: {suspicious_count}")
    print(f"Ошибок по audit log: {error_stats['total_errors']}")
    print(f"Критических событий: {error_stats['critical_errors']}")


def show_total_balance(bank: Bank) -> None:
    print_separator("ОБЩИЙ БАЛАНС БАНКА")
    print(
        "Итоговый баланс по текущей модели Bank.get_total_balance() "
        f"(без нормализации валют): {bank.get_total_balance():.2f}"
    )


def main() -> None:
    bank = Bank("Base OOP Bank")
    audit_log = AuditLog(file_path="logs/day6_audit.log")
    risk_analyzer = RiskAnalyzer(
        large_amount_threshold=40000.0,
        frequent_operations_count=3,
        frequent_operations_window_minutes=10,
    )

    processor = TransactionProcessor(
        bank=bank,
        audit_log=audit_log,
        risk_analyzer=risk_analyzer,
        exchange_rates={
            ("RUB", "USD"): 0.011,
            ("USD", "RUB"): 90.0,
            ("EUR", "USD"): 1.08,
            ("USD", "EUR"): 0.93,
            ("RUB", "EUR"): 0.010,
            ("EUR", "RUB"): 98.0,
            ("KZT", "RUB"): 0.19,
            ("RUB", "KZT"): 5.20,
            ("CNY", "RUB"): 12.50,
            ("RUB", "CNY"): 0.08,
            ("KZT", "USD"): 0.0021,
            ("USD", "KZT"): 470.0,
            ("EUR", "RUB"): 98.0,
            ("RUB", "CNY"): 0.08,
            ("USD", "CNY"): 7.20,
            ("CNY", "USD"): 0.139,
            ("EUR", "KZT"): 510.0,
            ("KZT", "EUR"): 0.00196,
        },
        external_transfer_fee_rate=0.015,
        fixed_external_fee=10.0,
    )

    clients = create_clients(bank)
    accounts = create_accounts(bank)

    show_all_clients(clients)
    show_all_accounts(accounts)

    bank.freeze_account(accounts["dmitry_savings"].account_id, reason="Ручная проверка", current_time=time(14, 0))

    transactions = build_transactions(accounts)

    queue = TransactionQueue()
    enqueue_transactions(queue, transactions)

    queue.cancel_transaction(transactions[30].transaction_id)
    print_separator("ОТМЕНА ТРАНЗАКЦИИ")
    print(
        f"CANCEL | tx={transactions[30].transaction_id} | "
        f"type={transactions[30].transaction_type.value} | status=cancel_requested"
    )

    process_transactions(processor, queue)

    print_separator("ОТКЛОНЁННЫЕ / ЗАБЛОКИРОВАННЫЕ ТРАНЗАКЦИИ")
    rejected = [
        tx for tx in transactions
        if tx.status in {TransactionStatus.FAILED, TransactionStatus.BLOCKED, TransactionStatus.CANCELLED}
    ]
    for tx in rejected:
        print(
            f"REJECT | tx={tx.transaction_id} | status={tx.status.value} | "
            f"type={tx.transaction_type.value} | reason={tx.failure_reason or '-'}"
        )

    show_client_accounts(bank, "C001")
    show_client_history(bank, "C001", transactions)
    show_client_suspicious_operations(audit_log, "C001")

    show_client_accounts(bank, "C005")
    show_client_history(bank, "C005", transactions)
    show_client_suspicious_operations(audit_log, "C005")

    show_top_clients(bank)
    show_transaction_statistics(transactions, audit_log)
    show_total_balance(bank)

    print_separator("ИТОГ")
    print(f"Клиентов создано: {len(clients)}")
    print(f"Счетов создано: {len(accounts)}")
    print(f"Транзакций смоделировано: {len(transactions)}")
    print(f"Audit events: {len(audit_log.entries)}")
    print(f"Error log records: {len(processor.error_log)}")


if __name__ == "__main__":
    main()