import unittest
from datetime import datetime, timedelta, time

from src.bank import Bank, Client
from src.models import AccountStatus, Currency, PremiumAccount, SavingsAccount
from src.transactions import (
    Transaction,
    TransactionProcessor,
    TransactionQueue,
    TransactionStatus,
    TransactionType,
)


class TestTransactionQueue(unittest.TestCase):
    def test_add_pop_and_cancel(self) -> None:
        queue = TransactionQueue()
        tx1 = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=100.0,
            currency=Currency.RUB,
            receiver_account_id="A1",
        )
        tx2 = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=200.0,
            currency=Currency.RUB,
            receiver_account_id="A2",
        )

        queue.add_transaction(tx1, priority=20)
        queue.add_transaction(tx2, priority=10)

        first = queue.pop_ready_transaction()
        self.assertEqual(first.transaction_id, tx2.transaction_id)

        queue.add_transaction(tx1, priority=5)
        queue.cancel_transaction(tx1.transaction_id)
        cancelled = queue.pop_ready_transaction()
        self.assertIsNone(cancelled)


class TestTransactionProcessor(unittest.TestCase):
    def setUp(self) -> None:
        self.bank = Bank("Test Bank")

        self.client1 = Client(
            full_name="Иван Петров",
            client_id="C001",
            age=30,
            contacts={"phone": "+79990000001"},
            security_code="1111",
        )
        self.client2 = Client(
            full_name="Анна Смирнова",
            client_id="C002",
            age=29,
            contacts={"phone": "+79990000002"},
            security_code="2222",
        )

        self.bank.add_client(self.client1)
        self.bank.add_client(self.client2)

        self.acc1 = self.bank.open_account(
            client_id="C001",
            account_cls=SavingsAccount,
            balance=10000.0,
            currency=Currency.RUB,
            min_balance=1000.0,
            monthly_interest_rate=0.01,
            current_time=time(10, 0),
        )
        self.acc2 = self.bank.open_account(
            client_id="C002",
            account_cls=PremiumAccount,
            balance=1000.0,
            currency=Currency.USD,
            overdraft_limit=3000.0,
            withdrawal_fee=10.0,
            daily_withdrawal_limit=20000.0,
            current_time=time(10, 5),
        )

        self.processor = TransactionProcessor(
            self.bank,
            exchange_rates={
                ("RUB", "USD"): 0.01,
                ("USD", "RUB"): 100.0,
            },
            external_transfer_fee_rate=0.01,
            fixed_external_fee=5.0,
        )

    def test_deposit(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=500.0,
            currency=Currency.RUB,
            receiver_account_id=self.acc1.account_id,
        )
        result = self.processor.process_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)
        self.assertEqual(self.acc1.balance, 10500.0)

    def test_withdraw(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.WITHDRAW,
            amount=1000.0,
            currency=Currency.RUB,
            sender_account_id=self.acc1.account_id,
        )
        result = self.processor.process_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(self.acc1.balance, 9000.0)

    def test_internal_transfer(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=100.0,
            currency=Currency.USD,
            sender_account_id=self.acc2.account_id,
            receiver_account_id=self.acc1.account_id,
        )
        result = self.processor.process_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)
        self.assertEqual(self.acc2.balance, 890.0)
        self.assertEqual(self.acc1.balance, 20000.0)

    def test_external_transfer_with_commission(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=100.0,
            currency=Currency.USD,
            sender_account_id=self.acc2.account_id,
        )
        result = self.processor.process_transaction(tx)
        self.assertTrue(result)
        self.assertEqual(tx.commission, 6.0)
        self.assertEqual(self.acc2.balance, 884.0)

    def test_frozen_account_transfer_forbidden(self) -> None:
        self.acc1.freeze()
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=300.0,
            currency=Currency.RUB,
            receiver_account_id=self.acc1.account_id,
            max_retries=0,
        )
        result = self.processor.process_transaction(tx)
        self.assertFalse(result)
        self.assertEqual(tx.status, TransactionStatus.FAILED)

    def test_minus_forbidden_except_premium(self) -> None:
        normal_tx = Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=20000.0,
            currency=Currency.RUB,
            sender_account_id=self.acc1.account_id,
            receiver_account_id=self.acc2.account_id,
            max_retries=0,
        )
        result = self.processor.process_transaction(normal_tx)
        self.assertFalse(result)
        self.assertEqual(normal_tx.status, TransactionStatus.FAILED)

    def test_queue_with_delayed_transaction(self) -> None:
        queue = TransactionQueue()
        future_tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=200.0,
            currency=Currency.RUB,
            receiver_account_id=self.acc1.account_id,
            scheduled_at=datetime.now() + timedelta(minutes=10),
        )
        queue.add_transaction(future_tx, priority=1)

        processed_now = self.processor.process_queue(queue, now=datetime.now())
        self.assertEqual(len(processed_now), 0)

        processed_later = self.processor.process_queue(
            queue,
            now=datetime.now() + timedelta(minutes=11),
        )
        self.assertEqual(len(processed_later), 1)
        self.assertEqual(future_tx.status, TransactionStatus.COMPLETED)

    def test_retry_then_fail(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=100.0,
            currency=Currency.EUR,
            receiver_account_id=self.acc1.account_id,
            max_retries=1,
        )

        first_result = self.processor.process_transaction(tx)
        self.assertFalse(first_result)
        self.assertEqual(tx.status, TransactionStatus.DELAYED)

        second_result = self.processor.process_transaction(tx)
        self.assertFalse(second_result)
        self.assertEqual(tx.status, TransactionStatus.FAILED)

    def test_cancelled_transaction_not_processed(self) -> None:
        queue = TransactionQueue()
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=500.0,
            currency=Currency.RUB,
            receiver_account_id=self.acc1.account_id,
        )
        queue.add_transaction(tx, priority=1)
        queue.cancel_transaction(tx.transaction_id)

        processed = self.processor.process_queue(queue)
        self.assertEqual(len(processed), 0)
        self.assertEqual(tx.status, TransactionStatus.CANCELLED)

    def test_completed_transactions_collected(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=100.0,
            currency=Currency.RUB,
            receiver_account_id=self.acc1.account_id,
        )
        self.processor.process_transaction(tx)
        self.assertEqual(len(self.processor.processed_transactions), 1)

    def test_error_log_filled(self) -> None:
        self.acc2._status = AccountStatus.FROZEN
        tx = Transaction(
            transaction_type=TransactionType.WITHDRAW,
            amount=50.0,
            currency=Currency.USD,
            sender_account_id=self.acc2.account_id,
            max_retries=0,
        )
        self.processor.process_transaction(tx)
        self.assertGreaterEqual(len(self.processor.error_log), 1)


if __name__ == "__main__":
    unittest.main()