import unittest

from src.models import (
    AccountFrozenError,
    AccountStatus,
    BankAccount,
    Currency,
    InsufficientFundsError,
    InvalidOperationError,
    Owner,
)


class TestBankAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.owner = Owner(full_name="Тестовый Клиент", client_id="TEST001")
        self.account = BankAccount(
            owner=self.owner,
            balance=1000.0,
            currency=Currency.EUR,
            status=AccountStatus.ACTIVE,
        )

    def test_deposit_success(self) -> None:
        self.account.deposit(500.0)
        self.assertEqual(self.account.balance, 1500.0)

    def test_withdraw_success(self) -> None:
        self.account.withdraw(300.0)
        self.assertEqual(self.account.balance, 700.0)

    def test_withdraw_insufficient_funds(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.account.withdraw(5000.0)

    def test_frozen_account_rejects_operations(self) -> None:
        frozen_account = BankAccount(
            owner=self.owner,
            balance=100.0,
            currency=Currency.USD,
            status=AccountStatus.FROZEN,
        )
        with self.assertRaises(AccountFrozenError):
            frozen_account.deposit(10.0)
        with self.assertRaises(AccountFrozenError):
            frozen_account.withdraw(10.0)

    def test_invalid_amount(self) -> None:
        with self.assertRaises(InvalidOperationError):
            self.account.deposit(0)

        with self.assertRaises(InvalidOperationError):
            self.account.withdraw(-10)

    def test_auto_generated_account_id(self) -> None:
        self.assertEqual(len(self.account.account_id), 8)
        self.assertIsInstance(self.account.account_id, str)

    def test_account_info(self) -> None:
        info = self.account.get_account_info()
        self.assertEqual(info["account_type"], "BankAccount")
        self.assertEqual(info["owner_name"], "Тестовый Клиент")
        self.assertEqual(info["currency"], "EUR")


if __name__ == "__main__":
    unittest.main()