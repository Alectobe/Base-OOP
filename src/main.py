from datetime import time

from src.bank import Bank, Client
from src.models import Currency, PremiumAccount, SavingsAccount


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

    bank.add_client(client1)
    bank.add_client(client2)

    print_separator("АУТЕНТИФИКАЦИЯ")
    print("Успешный вход C001:", bank.authenticate_client("C001", "1111"))
    print("Ошибка входа C002:", bank.authenticate_client("C002", "9999"))
    print("Ошибка входа C002:", bank.authenticate_client("C002", "9999"))
    print("Ошибка входа C002:", bank.authenticate_client("C002", "9999"))
    print("Повторный вход C002 после блокировки:", bank.authenticate_client("C002", "2222"))

    print_separator("ОТКРЫТИЕ СЧЕТОВ")
    savings = bank.open_account(
        client_id="C001",
        account_cls=SavingsAccount,
        balance=15000.0,
        currency=Currency.RUB,
        min_balance=3000.0,
        monthly_interest_rate=0.02,
        current_time=time(10, 30),
    )
    print(savings)

    try:
        premium = bank.open_account(
            client_id="C002",
            account_cls=PremiumAccount,
            balance=7000.0,
            currency=Currency.USD,
            overdraft_limit=5000.0,
            withdrawal_fee=20.0,
            daily_withdrawal_limit=30000.0,
            current_time=time(11, 0),
        )
        print(premium)
    except Exception as error:
        print("Не удалось открыть счёт C002:", error)

    print_separator("ОПЕРАЦИИ ПО СЧЁТУ")
    bank.deposit_to_account(savings.account_id, 2000.0, current_time=time(12, 0))
    print("После пополнения:", savings)

    bank.withdraw_from_account(savings.account_id, 4000.0, current_time=time(13, 0))
    print("После снятия:", savings)

    print_separator("ЗАМОРОЗКА")
    bank.freeze_account(savings.account_id, reason="Подозрительная активность", current_time=time(14, 0))
    print(bank.get_account(savings.account_id))

    bank.unfreeze_account(savings.account_id, current_time=time(15, 0))
    print("После разморозки:", bank.get_account(savings.account_id))

    print_separator("НОЧНОЙ ЗАПРЕТ")
    try:
        bank.deposit_to_account(savings.account_id, 500.0, current_time=time(1, 30))
    except Exception as error:
        print("Ночная операция запрещена:", error)

    print_separator("ПОИСК СЧЕТОВ")
    found_accounts = bank.search_accounts(client_id="C001")
    for account in found_accounts:
        print(account)

    print_separator("ОБЩИЙ БАЛАНС")
    print(bank.get_total_balance())

    print_separator("РЕЙТИНГ КЛИЕНТОВ")
    for item in bank.get_clients_ranking():
        print(item)

    print_separator("ПОДОЗРИТЕЛЬНЫЕ ДЕЙСТВИЯ")
    for action in bank.suspicious_actions:
        print(action)


if __name__ == "__main__":
    main()