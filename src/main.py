from datetime import datetime, time

from src.audit import AuditLog, RiskAnalyzer
from src.bank import Bank, Client
from src.models import Currency, PremiumAccount, SavingsAccount
from src.transactions import Transaction, TransactionProcessor, TransactionQueue, TransactionType


def print_separator(title: str) -> None:
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)


def main() -> None:
    bank = Bank("Base OOP Bank")

    client1 = Client(
        full_name="Иван Петров",
        client_id="C001",
        age=30,
        contacts={"phone": "+79990000001", "email": "ivan@example.com"},
        security_code="1111",
    )
    client2 = Client(
        full_name="Анна Смирнова",
        client_id="C002",
        age=29,
        contacts={"phone": "+79990000002", "email": "anna@example.com"},
        security_code="2222",
    )

    bank.add_client(client1)
    bank.add_client(client2)

    acc1 = bank.open_account(
        client_id="C001",
        account_cls=SavingsAccount,
        balance=120000.0,
        currency=Currency.RUB,
        min_balance=5000.0,
        monthly_interest_rate=0.01,
        current_time=time(10, 0),
    )
    acc2 = bank.open_account(
        client_id="C002",
        account_cls=PremiumAccount,
        balance=3000.0,
        currency=Currency.USD,
        overdraft_limit=5000.0,
        withdrawal_fee=15.0,
        daily_withdrawal_limit=30000.0,
        current_time=time(10, 10),
    )

    audit_log = AuditLog(file_path="logs/audit.log")
    risk_analyzer = RiskAnalyzer(
        large_amount_threshold=50000.0,
        frequent_operations_count=3,
        frequent_operations_window_minutes=10,
    )
    processor = TransactionProcessor(
        bank=bank,
        audit_log=audit_log,
        risk_analyzer=risk_analyzer,
    )
    queue = TransactionQueue()

    transactions = [
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=1000.0,
            currency=Currency.RUB,
            receiver_account_id=acc1.account_id,
            created_at=datetime(2026, 4, 7, 11, 0, 0),
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=200.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
            receiver_account_id=acc1.account_id,
            created_at=datetime(2026, 4, 7, 11, 1, 0),
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=250.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
            receiver_account_id=acc1.account_id,
            created_at=datetime(2026, 4, 7, 11, 2, 0),
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=260.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
            receiver_account_id=acc1.account_id,
            created_at=datetime(2026, 4, 7, 11, 3, 0),
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=70000.0,
            currency=Currency.RUB,
            sender_account_id=acc1.account_id,
            receiver_account_id=acc2.account_id,
            created_at=datetime(2026, 4, 7, 11, 5, 0),
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=150.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
            created_at=datetime(2026, 4, 7, 1, 30, 0),
        ),
    ]

    print_separator("ДОБАВЛЕНИЕ ТРАНЗАКЦИЙ В ОЧЕРЕДЬ")
    for index, tx in enumerate(transactions, start=1):
        queue.add_transaction(tx, priority=index)
        print(tx.transaction_id, tx.transaction_type.value, tx.amount, tx.currency.value)

    print_separator("ОБРАБОТКА")
    processed = processor.process_queue(queue)
    for tx in processed:
        print(tx.transaction_id, tx.status.value, tx.failure_reason)

    print_separator("ПОДОЗРИТЕЛЬНЫЕ ОПЕРАЦИИ")
    for item in audit_log.get_suspicious_operations_report():
        print(item)

    print_separator("РИСК-ПРОФИЛЬ КЛИЕНТА C002")
    print(audit_log.get_client_risk_profile("C002"))

    print_separator("СТАТИСТИКА ОШИБОК")
    print(audit_log.get_error_statistics())

    print_separator("ВСЕ AUDIT EVENTS")
    for entry in audit_log.entries:
        print(entry.to_dict())


if __name__ == "__main__":
    main()