from models import (
    AccountFrozenError,
    AccountStatus,
    BankAccount,
    Currency,
    InsufficientFundsError,
    Owner,
)


def print_separator(title: str) -> None:
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)


def main() -> None:
    owner_active = Owner(full_name="Иван Петров", client_id="C001")
    owner_frozen = Owner(full_name="Анна Смирнова", client_id="C002")

    active_account = BankAccount(
        owner=owner_active,
        balance=1000.0,
        currency=Currency.RUB,
        status=AccountStatus.ACTIVE,
    )

    frozen_account = BankAccount(
        owner=owner_frozen,
        balance=500.0,
        currency=Currency.USD,
        status=AccountStatus.FROZEN,
    )

    print_separator("СОЗДАНИЕ СЧЕТОВ")
    print(active_account)
    print(frozen_account)

    print_separator("ВАЛИДНОЕ ПОПОЛНЕНИЕ")
    active_account.deposit(250.0)
    print(active_account)
    print(active_account.get_account_info())

    print_separator("ВАЛИДНОЕ СНЯТИЕ")
    active_account.withdraw(300.0)
    print(active_account)
    print(active_account.get_account_info())

    print_separator("ПОПЫТКА ОПЕРАЦИИ НАД ЗАМОРОЖЕННЫМ СЧЁТОМ")
    try:
        frozen_account.deposit(100.0)
    except AccountFrozenError as error:
        print(f"Ошибка пополнения: {error}")

    try:
        frozen_account.withdraw(50.0)
    except AccountFrozenError as error:
        print(f"Ошибка снятия: {error}")

    print_separator("ПОПЫТКА СНЯТЬ БОЛЬШЕ, ЧЕМ ЕСТЬ")
    try:
        active_account.withdraw(5000.0)
    except InsufficientFundsError as error:
        print(f"Ошибка снятия: {error}")


if __name__ == "__main__":
    main()