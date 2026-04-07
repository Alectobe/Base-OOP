import unittest

from src.models import (
    Currency,
    InsufficientFundsError,
    InvalidOperationError,
    InvestmentAccount,
    Owner,
    PremiumAccount,
    SavingsAccount,
)


class TestSavingsAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = Owner(full_name="Тест Savings", client_id="S001")
        self.account = SavingsAccount(
            owner=self.owner,
            balance=10000.0,
            currency=Currency.RUB,
            min_balance=2000.0,
            monthly_interest_rate=0.01,
        )

    def test_apply_monthly_interest(self) -> None:
        interest = self.account.apply_monthly_interest()
        self.assertEqual(interest, 100.0)
        self.assertEqual(self.account.balance, 10100.0)

    def test_withdraw_respects_min_balance(self) -> None:
        with self.assertRaises(InvalidOperationError):
            self.account.withdraw(9000.0)

    def test_withdraw_success(self) -> None:
        self.account.withdraw(3000.0)
        self.assertEqual(self.account.balance, 7000.0)


class TestPremiumAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = Owner(full_name="Тест Premium", client_id="P001")
        self.account = PremiumAccount(
            owner=self.owner,
            balance=5000.0,
            currency=Currency.USD,
            overdraft_limit=2000.0,
            withdrawal_fee=50.0,
            daily_withdrawal_limit=10000.0,
        )

    def test_withdraw_with_overdraft(self) -> None:
        self.account.withdraw(6000.0)
        self.assertEqual(self.account.balance, -1050.0)

    def test_withdraw_exceeds_available_funds(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.account.withdraw(7000.0)

    def test_withdraw_exceeds_limit(self) -> None:
        with self.assertRaises(InvalidOperationError):
            self.account.withdraw(15000.0)


class TestInvestmentAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = Owner(full_name="Тест Investment", client_id="I001")
        self.account = InvestmentAccount(
            owner=self.owner,
            balance=10000.0,
            currency=Currency.USD,
            portfolio={
                "stocks": 5000.0,
                "bonds": 3000.0,
                "etf": 2000.0,
            },
        )

    def test_add_asset(self) -> None:
        self.account.add_asset("stocks", 1000.0)
        self.assertEqual(self.account.portfolio["stocks"], 6000.0)

    def test_get_total_portfolio_value(self) -> None:
        self.assertEqual(self.account.get_total_portfolio_value(), 10000.0)

    def test_project_yearly_growth(self) -> None:
        projection = self.account.project_yearly_growth()
        self.assertEqual(projection["stocks"], 5600.0)
        self.assertEqual(projection["bonds"], 3150.0)
        self.assertEqual(projection["etf"], 2160.0)
        self.assertEqual(projection["total_projected_value"], 10910.0)

    def test_withdraw_cash_balance_only(self) -> None:
        self.account.withdraw(1500.0)
        self.assertEqual(self.account.balance, 8500.0)

    def test_withdraw_insufficient_cash(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.account.withdraw(20000.0)


if __name__ == "__main__":
    unittest.main()