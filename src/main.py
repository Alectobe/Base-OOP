from datetime import datetime, timedelta, time

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
        age=28,
        contacts={"phone": "+79990000002", "email": "anna@example.com"},
        security_code="2222",
    )
    client3 = Client(
        full_name="Олег Сидоров",
        client_id="C003",
        age=35,
        contacts={"phone": "+79990000003", "email": "oleg@example.com"},
        security_code="3333",
    )

    bank.add_client(client1)
    bank.add_client(client2)
    bank.add_client(client3)

    acc1 = bank.open_account(
        client_id="C001",
        account_cls=SavingsAccount,
        balance=15000.0,
        currency=Currency.RUB,
        min_balance=3000.0,
        monthly_interest_rate=0.01,
        current_time=time(10, 0),
    )
    acc2 = bank.open_account(
        client_id="C002",
        account_cls=PremiumAccount,
        balance=5000.0,
        currency=Currency.USD,
        overdraft_limit=4000.0,
        withdrawal_fee=20.0,
        daily_withdrawal_limit=30000.0,
        current_time=time(10, 5),
    )
    acc3 = bank.open_account(
        client_id="C003",
        account_cls=InvestmentAccount,
        balance=12000.0,
        currency=Currency.EUR,
        portfolio={"stocks": 4000.0, "bonds": 2000.0, "etf": 3000.0},
        current_time=time(10, 10),
    )

    queue = TransactionQueue()
    processor = TransactionProcessor(bank)

    now = datetime.now()

    transactions = [
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=1000.0,
            currency=Currency.RUB,
            receiver_account_id=acc1.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.WITHDRAW,
            amount=500.0,
            currency=Currency.RUB,
            sender_account_id=acc1.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=100.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
            receiver_account_id=acc3.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=200.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=3000.0,
            currency=Currency.RUB,
            sender_account_id=acc1.account_id,
            receiver_account_id=acc2.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=700.0,
            currency=Currency.EUR,
            receiver_account_id=acc3.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.WITHDRAW,
            amount=250.0,
            currency=Currency.EUR,
            sender_account_id=acc3.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=100000.0,
            currency=Currency.RUB,
            sender_account_id=acc1.account_id,
            receiver_account_id=acc3.account_id,
        ),
        Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=1500.0,
            currency=Currency.USD,
            sender_account_id=acc2.account_id,
            scheduled_at=now + timedelta(seconds=1),
        ),
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=800.0,
            currency=Currency.USD,
            receiver_account_id=acc2.account_id,
        ),
    ]

    priorities = [20, 30, 10, 15, 40, 25, 35, 5, 50, 12]

    print_separator("ДОБАВЛЕНИЕ 10 ТРАНЗАКЦИЙ В ОЧЕРЕДЬ")
    for transaction, priority in zip(transactions, priorities):
        queue.add_transaction(transaction, priority=priority)
        print(
            f"Добавлена транзакция {transaction.transaction_id}: "
            f"{transaction.transaction_type.value}, priority={priority}"
        )

    print_separator("ОТМЕНА ОДНОЙ ТРАНЗАКЦИИ")
    queue.cancel_transaction(transactions[6].transaction_id)
    print(f"Отменена транзакция {transactions[6].transaction_id}")

    print_separator("ПЕРВАЯ ОБРАБОТКА ОЧЕРЕДИ")
    processed_first = processor.process_queue(queue, now=now)
    for transaction in processed_first:
        print(
            f"{transaction.transaction_id}: "
            f"status={transaction.status.value}, "
            f"reason='{transaction.failure_reason}', "
            f"commission={transaction.commission:.2f}"
        )

    print_separator("ВТОРАЯ ОБРАБОТКА ОЧЕРЕДИ ОТЛОЖЕННЫХ")
    processed_second = processor.process_queue(queue, now=now + timedelta(minutes=1))
    for transaction in processed_second:
        print(
            f"{transaction.transaction_id}: "
            f"status={transaction.status.value}, "
            f"reason='{transaction.failure_reason}', "
            f"commission={transaction.commission:.2f}"
        )

    print_separator("ИТОГОВЫЕ СЧЕТА")
    print(acc1)
    print(acc2)
    print(acc3)

    print_separator("ОШИБКИ ПРОЦЕССОРА")
    for item in processor.error_log:
        print(item)

    print_separator("ВСЕ ТРАНЗАКЦИИ")
    for transaction in transactions:
        print(
            transaction.transaction_id,
            transaction.transaction_type.value,
            transaction.status.value,
            transaction.failure_reason,
        )

    print_separator("ОБЩИЙ БАЛАНС БАНКА")
    print(bank.get_total_balance())


if __name__ == "__main__":
    main()