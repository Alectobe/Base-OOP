import unittest
from datetime import datetime, time
from pathlib import Path

from src.audit import AuditLevel, AuditLog, RiskAnalyzer, RiskLevel
from src.bank import Bank, Client
from src.models import Currency, PremiumAccount, SavingsAccount
from src.transactions import Transaction, TransactionProcessor, TransactionStatus, TransactionType


class TestAuditLog(unittest.TestCase):
    def setUp(self) -> None:
        self.log_file = Path("tests/tmp_audit.log")
        if self.log_file.exists():
            self.log_file.unlink()

        self.audit_log = AuditLog(file_path=str(self.log_file))

    def tearDown(self) -> None:
        if self.log_file.exists():
            self.log_file.unlink()

    def test_log_to_memory_and_file(self) -> None:
        self.audit_log.log(
            level=AuditLevel.INFO,
            event_type="test_event",
            message="Тестовая запись",
            client_id="C001",
        )
        self.assertEqual(len(self.audit_log.entries), 1)
        self.assertTrue(self.log_file.exists())
        self.assertIn("Тестовая запись", self.log_file.read_text(encoding="utf-8"))

    def test_filter_entries(self) -> None:
        self.audit_log.log(AuditLevel.INFO, "event1", "message1", client_id="C001")
        self.audit_log.log(AuditLevel.ERROR, "event2", "message2", client_id="C002")

        filtered = self.audit_log.filter_entries(level=AuditLevel.ERROR)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].client_id, "C002")


class TestRiskAnalyzer(unittest.TestCase):
    def setUp(self) -> None:
        self.analyzer = RiskAnalyzer(
            large_amount_threshold=10000.0,
            frequent_operations_count=3,
            frequent_operations_window_minutes=10,
        )

    def test_large_amount_high_with_night(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=15000.0,
            currency=Currency.RUB,
            sender_account_id="A1",
            created_at=datetime(2026, 4, 7, 1, 0, 0),
        )
        result = self.analyzer.analyze_transaction(tx)
        self.assertEqual(result["risk_level"], RiskLevel.HIGH)
        self.assertTrue(result["should_block"])

    def test_new_receiver_medium(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=100.0,
            currency=Currency.RUB,
            sender_account_id="A1",
            receiver_account_id="A2",
            created_at=datetime(2026, 4, 7, 12, 0, 0),
        )
        result = self.analyzer.analyze_transaction(tx)
        self.assertEqual(result["risk_level"], RiskLevel.MEDIUM)

    def test_frequent_operations_high(self) -> None:
        base_time = datetime(2026, 4, 7, 12, 0, 0)

        tx1 = Transaction(TransactionType.TRANSFER_EXTERNAL, 100.0, Currency.RUB, sender_account_id="A1", created_at=base_time)
        tx2 = Transaction(TransactionType.TRANSFER_EXTERNAL, 120.0, Currency.RUB, sender_account_id="A1", created_at=base_time.replace(minute=2))
        tx3 = Transaction(TransactionType.TRANSFER_EXTERNAL, 130.0, Currency.RUB, sender_account_id="A1", created_at=base_time.replace(minute=4))

        self.analyzer.analyze_transaction(tx1)
        self.analyzer.analyze_transaction(tx2)
        result = self.analyzer.analyze_transaction(tx3)

        self.assertEqual(result["risk_level"], RiskLevel.MEDIUM)


class TestTransactionProcessorWithAudit(unittest.TestCase):
    def setUp(self) -> None:
        self.bank = Bank("Audit Bank")

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
            age=28,
            contacts={"phone": "+79990000002"},
            security_code="2222",
        )

        self.bank.add_client(self.client1)
        self.bank.add_client(self.client2)

        self.acc1 = self.bank.open_account(
            client_id="C001",
            account_cls=SavingsAccount,
            balance=100000.0,
            currency=Currency.RUB,
            min_balance=1000.0,
            monthly_interest_rate=0.01,
            current_time=time(10, 0),
        )
        self.acc2 = self.bank.open_account(
            client_id="C002",
            account_cls=PremiumAccount,
            balance=2000.0,
            currency=Currency.USD,
            overdraft_limit=5000.0,
            withdrawal_fee=10.0,
            daily_withdrawal_limit=50000.0,
            current_time=time(10, 10),
        )

        self.audit_log = AuditLog()
        self.risk_analyzer = RiskAnalyzer(
            large_amount_threshold=50000.0,
            frequent_operations_count=3,
            frequent_operations_window_minutes=10,
        )
        self.processor = TransactionProcessor(
            bank=self.bank,
            audit_log=self.audit_log,
            risk_analyzer=self.risk_analyzer,
            exchange_rates={
                ("RUB", "USD"): 0.01,
                ("USD", "RUB"): 100.0,
            },
            external_transfer_fee_rate=0.01,
            fixed_external_fee=5.0,
        )

    def test_normal_transaction_logged(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=1000.0,
            currency=Currency.RUB,
            receiver_account_id=self.acc1.account_id,
            created_at=datetime(2026, 4, 7, 11, 0, 0),
        )
        result = self.processor.process_transaction(tx)

        self.assertTrue(result)
        self.assertEqual(tx.status, TransactionStatus.COMPLETED)
        self.assertGreaterEqual(len(self.audit_log.entries), 1)

    def test_high_risk_transaction_blocked(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=70000.0,
            currency=Currency.RUB,
            sender_account_id=self.acc1.account_id,
            receiver_account_id=self.acc2.account_id,
            created_at=datetime(2026, 4, 7, 1, 10, 0),
        )
        result = self.processor.process_transaction(tx)

        self.assertFalse(result)
        self.assertEqual(tx.status, TransactionStatus.BLOCKED)

    def test_suspicious_operations_report(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=100.0,
            currency=Currency.USD,
            sender_account_id=self.acc2.account_id,
            created_at=datetime(2026, 4, 7, 2, 15, 0),
        )
        self.processor.process_transaction(tx)

        report = self.audit_log.get_suspicious_operations_report()
        self.assertGreaterEqual(len(report), 1)

    def test_client_risk_profile(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_EXTERNAL,
            amount=100.0,
            currency=Currency.USD,
            sender_account_id=self.acc2.account_id,
            created_at=datetime(2026, 4, 7, 2, 15, 0),
        )
        self.processor.process_transaction(tx)

        profile = self.audit_log.get_client_risk_profile("C002")
        self.assertEqual(profile["client_id"], "C002")
        self.assertGreaterEqual(profile["suspicious_events"], 1)

    def test_error_statistics(self) -> None:
        tx = Transaction(
            transaction_type=TransactionType.TRANSFER_INTERNAL,
            amount=70000.0,
            currency=Currency.RUB,
            sender_account_id=self.acc1.account_id,
            receiver_account_id=self.acc2.account_id,
            created_at=datetime(2026, 4, 7, 1, 10, 0),
        )
        self.processor.process_transaction(tx)

        stats = self.audit_log.get_error_statistics()
        self.assertGreaterEqual(stats["total_errors"], 1)


if __name__ == "__main__":
    unittest.main()