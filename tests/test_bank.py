import unittest
from datetime import time

from src.bank import Bank, Client, ClientStatus
from src.models import (
    AccountStatus,
    Currency,
    InvalidOperationError,
    PremiumAccount,
    SavingsAccount,
)


class TestClient(unittest.TestCase):
    def test_client_age_validation(self) -> None:
        with self.assertRaises(ValueError):
            Client(
                full_name="Несовершеннолетний Клиент",
                client_id="U001",
                age=17,
                contacts={"phone": "+79990000000"},
                security_code="1234",
            )


class TestBank(unittest.TestCase):
    def setUp(self) -> None:
        self.bank = Bank("Test Bank")

        self.client1 = Client(
            full_name="Иван Петров",
            client_id="C001",
            age=30,
            contacts={"phone": "+79990000001", "email": "ivan@example.com"},
            security_code="1111",
        )

        self.client2 = Client(
            full_name="Анна Смирнова",
            client_id="C002",
            age=25,
            contacts={"phone": "+79990000002", "email": "anna@example.com"},
            security_code="2222",
        )

        self.bank.add_client(self.client1)
        self.bank.add_client(self.client2)

    def test_add_client_duplicate(self) -> None:
        with self.assertRaises(InvalidOperationError):
            self.bank.add_client(self.client1)

    def test_authenticate_success(self) -> None:
        self.assertTrue(self.bank.authenticate_client("C001", "1111"))

    def test_authenticate_block_after_three_attempts(self) -> None:
        self.assertFalse(self.bank.authenticate_client("C001", "0000"))
        self.assertFalse(self.bank.authenticate_client("C001", "0000"))
        self.assertFalse(self.bank.authenticate_client("C001", "0000"))
        self.assertEqual(self.bank.get_client("C001").status, ClientStatus.BLOCKED)

    def test_open_account(self) -> None:
        account = self.bank.open_account(
            client_id="C001",
            account_cls=SavingsAccount,
            balance=10000.0,
            currency=Currency.RUB,
            min_balance=1000.0,
            monthly_interest_rate=0.01,
            current_time=time(10, 0),
        )
        self.assertEqual(account.owner.client_id, "C001")
        self.assertIn(account.account_id, self.bank.get_client("C001").account_ids)

    def test_open_account_at_night_is_forbidden(self) -> None:
        with self.assertRaises(InvalidOperationError):
            self.bank.open_account(
                client_id="C001",
                account_cls=SavingsAccount,
                balance=10000.0,
                currency=Currency.RUB,
                min_balance=1000.0,
                monthly_interest_rate=0.01,
                current_time=time(1, 0),
            )

    def test_freeze_and_unfreeze_account(self) -> None:
        account = self.bank.open_account(
            client_id="C001",
            account_cls=PremiumAccount,
            balance=5000.0,
            currency=Currency.USD,
            overdraft_limit=2000.0,
            withdrawal_fee=20.0,
            daily_withdrawal_limit=10000.0,
            current_time=time(11, 0),
        )

        self.bank.freeze_account(account.account_id, reason="manual check", current_time=time(12, 0))
        self.assertEqual(account.status, AccountStatus.FROZEN)

        self.bank.unfreeze_account(account.account_id, current_time=time(13, 0))
        self.assertEqual(account.status, AccountStatus.ACTIVE)

    def test_search_accounts(self) -> None:
        account1 = self.bank.open_account(
            client_id="C001",
            account_cls=SavingsAccount,
            balance=12000.0,
            currency=Currency.RUB,
            min_balance=1000.0,
            monthly_interest_rate=0.01,
            current_time=time(10, 0),
        )
        account2 = self.bank.open_account(
            client_id="C002",
            account_cls=PremiumAccount,
            balance=8000.0,
            currency=Currency.USD,
            overdraft_limit=2000.0,
            withdrawal_fee=25.0,
            daily_withdrawal_limit=15000.0,
            current_time=time(10, 30),
        )

        result = self.bank.search_accounts(client_id="C001")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].account_id, account1.account_id)
        self.assertNotEqual(result[0].account_id, account2.account_id)

    def test_total_balance(self) -> None:
        self.bank.open_account(
            client_id="C001",
            account_cls=SavingsAccount,
            balance=10000.0,
            currency=Currency.RUB,
            min_balance=1000.0,
            monthly_interest_rate=0.01,
            current_time=time(10, 0),
        )
        self.bank.open_account(
            client_id="C002",
            account_cls=PremiumAccount,
            balance=7000.0,
            currency=Currency.USD,
            overdraft_limit=3000.0,
            withdrawal_fee=10.0,
            daily_withdrawal_limit=10000.0,
            current_time=time(10, 10),
        )

        self.assertEqual(self.bank.get_total_balance(), 17000.0)

    def test_clients_ranking(self) -> None:
        self.bank.open_account(
            client_id="C001",
            account_cls=SavingsAccount,
            balance=15000.0,
            currency=Currency.RUB,
            min_balance=2000.0,
            monthly_interest_rate=0.02,
            current_time=time(9, 0),
        )
        self.bank.open_account(
            client_id="C002",
            account_cls=PremiumAccount,
            balance=5000.0,
            currency=Currency.USD,
            overdraft_limit=2000.0,
            withdrawal_fee=15.0,
            daily_withdrawal_limit=12000.0,
            current_time=time(9, 30),
        )

        ranking = self.bank.get_clients_ranking()
        self.assertEqual(ranking[0]["client_id"], "C001")
        self.assertEqual(ranking[1]["client_id"], "C002")

    def test_suspicious_actions_logged(self) -> None:
        self.bank.authenticate_client("C001", "0000")
        self.assertGreaterEqual(len(self.bank.suspicious_actions), 1)


if __name__ == "__main__":
    unittest.main()