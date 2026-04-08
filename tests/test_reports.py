import unittest
from pathlib import Path

from src.main import create_demo_data
from src.reports import ReportBuilder


class TestReportBuilder(unittest.TestCase):
    def setUp(self) -> None:
        self.output_dir = Path("tests/tmp_reports")
        if self.output_dir.exists():
            for path in sorted(self.output_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

        bank, clients, accounts, transactions, audit_log, exchange_rates = create_demo_data()
        self.bank = bank
        self.clients = clients
        self.accounts = accounts
        self.transactions = transactions
        self.audit_log = audit_log
        self.exchange_rates = exchange_rates
        self.builder = ReportBuilder(
            bank=self.bank,
            transactions=self.transactions,
            audit_log=self.audit_log,
            base_output_dir=str(self.output_dir),
        )

    def tearDown(self) -> None:
        if self.output_dir.exists():
            for path in sorted(self.output_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()

    def test_build_client_report(self) -> None:
        report = self.builder.build_client_report("C001")
        self.assertEqual(report["report_type"], "client")
        self.assertEqual(report["client"]["client_id"], "C001")
        self.assertGreaterEqual(report["client"]["accounts_count"], 1)

    def test_build_bank_report(self) -> None:
        report = self.builder.build_bank_report(
            base_currency="RUB",
            exchange_rates=self.exchange_rates,
        )
        self.assertEqual(report["report_type"], "bank")
        self.assertEqual(report["bank_name"], "Base OOP Bank")
        self.assertGreaterEqual(report["clients_count"], 1)
        self.assertEqual(report["base_currency"], "RUB")
        self.assertIn("total_balance_converted", report)

    def test_build_risk_report(self) -> None:
        report = self.builder.build_risk_report()
        self.assertEqual(report["report_type"], "risk")
        self.assertIn("suspicious_operations_count", report)

    def test_build_text_report(self) -> None:
        report = self.builder.build_bank_report(
            base_currency="RUB",
            exchange_rates=self.exchange_rates,
        )
        text = self.builder.build_text_report(report)
        self.assertIn("REPORT TYPE: BANK", text)

    def test_export_to_json(self) -> None:
        report = self.builder.build_bank_report(
            base_currency="RUB",
            exchange_rates=self.exchange_rates,
        )
        file_path = self.builder.export_to_json(report, "bank_report_test.json")
        self.assertTrue(file_path.exists())
        self.assertTrue(file_path.read_text(encoding="utf-8").strip().startswith("{"))

    def test_export_to_csv(self) -> None:
        report = self.builder.build_client_report("C001")
        file_path = self.builder.export_to_csv(report["transactions"], "client_transactions_test.csv")
        self.assertTrue(file_path.exists())
        content = file_path.read_text(encoding="utf-8")
        self.assertIn("transaction_id", content)

    def test_save_text_report(self) -> None:
        report = self.builder.build_risk_report()
        text = self.builder.build_text_report(report)
        file_path = self.builder.save_text_report(text, "risk_report_test.txt")
        self.assertTrue(file_path.exists())
        self.assertIn("REPORT TYPE: RISK", file_path.read_text(encoding="utf-8"))

    def test_save_charts(self) -> None:
        chart_paths = self.builder.save_charts(prefix="test")
        self.assertGreaterEqual(len(chart_paths), 3)
        for path in chart_paths:
            self.assertTrue(path.exists())

    def test_total_commissions_use_only_completed_transactions(self) -> None:
        report = self.builder.build_bank_report(
            base_currency="RUB",
            exchange_rates=self.exchange_rates,
        )
        expected = round(
            sum(tx.commission for tx in self.transactions if tx.status.value == "completed"),
            2,
        )
        self.assertEqual(report["transactions_statistics"]["total_commissions"], expected)


if __name__ == "__main__":
    unittest.main()