from src.models import (
    AccountStatus,
    Currency,
    InsufficientFundsError,
    InvalidOperationError,
    InvestmentAccount,
    Owner,
    PremiumAccount,
    SavingsAccount,
)


def print_separator(title: str) -> None:
    print("\n" + "=" * 20 + f" {title} " + "=" * 20)


def main() -> None:
    owner1 = Owner(full_name="Иван Петров", client_id="C001")
    owner2 = Owner(full_name="Анна Смирнова", client_id="C002")
    owner3 = Owner(full_name="Олег Сидоров", client_id="C003")

    savings = SavingsAccount(
        owner=owner1,
        balance=10000.0,
        currency=Currency.RUB,
        min_balance=2000.0,
        monthly_interest_rate=0.015,
    )

    premium = PremiumAccount(
        owner=owner2,
        balance=5000.0,
        currency=Currency.USD,
        overdraft_limit=3000.0,
        withdrawal_fee=25.0,
        daily_withdrawal_limit=20000.0,
    )

    investment = InvestmentAccount(
        owner=owner3,
        balance=15000.0,
        currency=Currency.USD,
        portfolio={
            "stocks": 10000.0,
            "bonds": 5000.0,
            "etf": 7000.0,
        },
    )

    accounts = [savings, premium, investment]

    print_separator("СОЗДАННЫЕ СЧЕТА")
    for account in accounts:
        print(account)

    print_separator("SAVINGS ACCOUNT")
    print("До начисления процентов:", savings)
    interest = savings.apply_monthly_interest()
    print(f"Начисленные проценты: {interest:.2f} {savings.currency.value}")
    print("После начисления процентов:", savings)

    try:
        savings.withdraw(9500.0)
    except InvalidOperationError as error:
        print(f"Ошибка снятия с накопительного счёта: {error}")

    savings.withdraw(3000.0)
    print("После корректного снятия:", savings)
    print(savings.get_account_info())

    print_separator("PREMIUM ACCOUNT")
    print("До снятия:", premium)
    premium.withdraw(7000.0)
    print("После снятия с овердрафтом и комиссией:", premium)
    print(premium.get_account_info())

    try:
        premium.withdraw(50000.0)
    except (InvalidOperationError, InsufficientFundsError) as error:
        print(f"Ошибка premium-счёта: {error}")

    print_separator("INVESTMENT ACCOUNT")
    print("До изменений:", investment)
    investment.add_asset("stocks", 2500.0)
    investment.add_asset("etf", 1500.0)
    investment.withdraw(2000.0)
    print("После операций:", investment)
    print("Информация:", investment.get_account_info())
    print("Прогноз роста на год:", investment.project_yearly_growth())

    print_separator("ПОЛИМОРФИЗМ")
    for account in accounts:
        print(f"{account.__class__.__name__}:")
        print(account)
        print(account.get_account_info())


if __name__ == "__main__":
    main()