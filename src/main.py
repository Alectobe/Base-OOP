from __future__ import annotations

from datetime import datetime, time

from src.audit import AuditLog, RiskAnalyzer, RiskLevel
from src.bank import Bank, Client
from src.models import Currency, InvestmentAccount, PremiumAccount, SavingsAccount
from src.reports import ReportBuilder
from src.transactions import (
    Transaction,
    TransactionProcessor,
    TransactionQueue,
    TransactionStatus,
    TransactionType,
)


def print_separator(title: str) -> None:
    print("\n" + "=" * 25 + f" {title} " + "=" * 25)


def create_demo_data() -> tuple[Bank, list[Client], dict[str, object], list[Transaction], AuditLog]:
    bank = Bank("Base OOP Bank")
    audit_log = AuditLog(file_path="reports/day7_audit.log")
    risk_analyzer = RiskAnalyzer(
        large_amount_threshold=40000.0,
        frequent_operations_count=3,
        frequent_operations_window_minutes=10,
    )

    processor = TransactionProcessor(
        bank=bank,
        audit_log=audit_log,
        risk_analyzer=risk_analyzer,
        exchange_rates={
            ("RUB", "USD"): 0.011,
            ("USD", "RUB"): 90.0,
            ("EUR", "USD"): 1.08,
            ("USD", "EUR"): 0.93,
            ("RUB", "EUR"): 0.010,
            ("EUR", "RUB"): 98.0,
            ("KZT", "RUB"): 0.19,
            ("RUB", "KZT"): 5.20,
            ("CNY", "RUB"): 12.50,
            ("RUB", "CNY"): 0.08,
            ("KZT", "USD"): 0.0021,
            ("USD", "KZT"): 470.0,
            ("USD", "CNY"): 7.20,
            ("CNY", "USD"): 0.139,
            ("EUR", "KZT"): 510.0,
            ("KZT", "EUR"): 0.00196,
        },
        external_transfer_fee_rate=0.015,
        fixed_external_fee=10.0,
    )

    clients = [
        Client("Иван Петров", "C001", 31, {"phone": "+79990000001", "email": "ivan@example.com"}, "1111"),
        Client("Анна Смирнова", "C002", 28, {"phone": "+79990000002", "email": "anna@example.com"}, "2222"),
        Client("Олег Сидоров", "C003", 35, {"phone": "+79990000003", "email": "oleg@example.com"}, "3333"),
        Client("Мария Кузнецова", "C004", 26, {"phone": "+79990000004", "email": "maria@example.com"}, "4444"),
        Client("Дмитрий Волков", "C005", 40, {"phone": "+79990000005", "email": "dmitry@example.com"}, "5555"),
        Client("Елена Орлова", "C006", 33, {"phone": "+79990000006", "email": "elena@example.com"}, "6666"),
    ]
    for client in clients:
        bank.add_client(client)

    accounts: dict[str, object] = {}
    accounts["ivan_savings"] = bank.open_account("C001", SavingsAccount, balance=120000.0, currency=Currency.RUB, min_balance=5000.0, monthly_interest_rate=0.012, current_time=time(10, 0))
    accounts["ivan_premium"] = bank.open_account("C001", PremiumAccount, balance=4000.0, currency=Currency.USD, overdraft_limit=7000.0, withdrawal_fee=15.0, daily_withdrawal_limit=40000.0, current_time=time(10, 1))
    accounts["anna_savings"] = bank.open_account("C002", SavingsAccount, balance=15000.0, currency=Currency.EUR, min_balance=1000.0, monthly_interest_rate=0.01, current_time=time(10, 2))
    accounts["anna_invest"] = bank.open_account("C002", InvestmentAccount, balance=12000.0, currency=Currency.USD, portfolio={"stocks": 7000.0, "bonds": 2500.0, "etf": 3000.0}, current_time=time(10, 3))
    accounts["oleg_premium"] = bank.open_account("C003", PremiumAccount, balance=30000.0, currency=Currency.RUB, overdraft_limit=10000.0, withdrawal_fee=25.0, daily_withdrawal_limit=100000.0, current_time=time(10, 4))
    accounts["oleg_savings"] = bank.open_account("C003", SavingsAccount, balance=900000.0, currency=Currency.KZT, min_balance=100000.0, monthly_interest_rate=0.008, current_time=time(10, 5))
    accounts["maria_invest"] = bank.open_account("C004", InvestmentAccount, balance=8000.0, currency=Currency.EUR, portfolio={"stocks": 2500.0, "bonds": 1500.0, "etf": 1800.0}, current_time=time(10, 6))
    accounts["maria_premium"] = bank.open_account("C004", PremiumAccount, balance=6000.0, currency=Currency.USD, overdraft_limit=5000.0, withdrawal_fee=10.0, daily_withdrawal_limit=35000.0, current_time=time(10, 7))
    accounts["dmitry_savings"] = bank.open_account("C005", SavingsAccount, balance=20000.0, currency=Currency.CNY, min_balance=3000.0, monthly_interest_rate=0.009, current_time=time(10, 8))
    accounts["dmitry_premium"] = bank.open_account("C005", PremiumAccount, balance=25000.0, currency=Currency.RUB, overdraft_limit=8000.0, withdrawal_fee=20.0, daily_withdrawal_limit=80000.0, current_time=time(10, 9))
    accounts["elena_invest"] = bank.open_account("C006", InvestmentAccount, balance=18000.0, currency=Currency.USD, portfolio={"stocks": 9000.0, "bonds": 4000.0, "etf": 3500.0}, current_time=time(10, 10))
    accounts["elena_savings"] = bank.open_account("C006", SavingsAccount, balance=9000.0, currency=Currency.RUB, min_balance=1500.0, monthly_interest_rate=0.011, current_time=time(10, 11))

    bank.freeze_account(accounts["dmitry_savings"].account_id, reason="Ручная проверка", current_time=time(14, 0))

    base_day = datetime(2026, 4, 7)
    transactions = [
        Transaction(TransactionType.DEPOSIT, 5000.0, Currency.RUB, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=0)),
        Transaction(TransactionType.WITHDRAW, 2000.0, Currency.RUB, sender_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=2)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 150.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=3)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 120.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, created_at=base_day.replace(hour=2, minute=15)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 5000.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, receiver_account_id=accounts["dmitry_premium"].account_id, created_at=base_day.replace(hour=11, minute=5)),
        Transaction(TransactionType.WITHDRAW, 250.0, Currency.USD, sender_account_id=accounts["maria_premium"].account_id, created_at=base_day.replace(hour=11, minute=6)),
        Transaction(TransactionType.DEPOSIT, 800.0, Currency.USD, receiver_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=7)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 3000.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=8)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 100.0, Currency.EUR, sender_account_id=accounts["anna_savings"].account_id, receiver_account_id=accounts["maria_invest"].account_id, created_at=base_day.replace(hour=11, minute=9)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 700.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=11, minute=10)),
        Transaction(TransactionType.DEPOSIT, 1000.0, Currency.CNY, receiver_account_id=accounts["dmitry_savings"].account_id, created_at=base_day.replace(hour=11, minute=11)),
        Transaction(TransactionType.WITHDRAW, 50000.0, Currency.KZT, sender_account_id=accounts["oleg_savings"].account_id, created_at=base_day.replace(hour=11, minute=12)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 200.0, Currency.USD, sender_account_id=accounts["elena_invest"].account_id, receiver_account_id=accounts["maria_premium"].account_id, created_at=base_day.replace(hour=11, minute=13)),
        Transaction(TransactionType.DEPOSIT, 600.0, Currency.RUB, receiver_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=14)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 180.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=15)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 190.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=17)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 210.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, receiver_account_id=accounts["dmitry_premium"].account_id, created_at=base_day.replace(hour=11, minute=18)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 70000.0, Currency.RUB, sender_account_id=accounts["ivan_savings"].account_id, receiver_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=1, minute=10)),
        Transaction(TransactionType.WITHDRAW, 50000.0, Currency.RUB, sender_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=20), max_retries=0),
        Transaction(TransactionType.DEPOSIT, 300.0, Currency.CNY, receiver_account_id=accounts["dmitry_savings"].account_id, created_at=base_day.replace(hour=11, minute=21), max_retries=0),
        Transaction(TransactionType.TRANSFER_INTERNAL, 50000.0, Currency.EUR, sender_account_id=accounts["anna_savings"].account_id, receiver_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=22), max_retries=0),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 50.0, Currency.USD, sender_account_id=accounts["maria_premium"].account_id, created_at=base_day.replace(hour=11, minute=23)),
        Transaction(TransactionType.DEPOSIT, 20000.0, Currency.KZT, receiver_account_id=accounts["oleg_savings"].account_id, created_at=base_day.replace(hour=11, minute=24)),
        Transaction(TransactionType.WITHDRAW, 1000.0, Currency.USD, sender_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=25)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 800.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=26)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 900.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=27)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 1000.0, Currency.RUB, sender_account_id=accounts["dmitry_premium"].account_id, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=28)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 2000.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=2, minute=0)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 65000.0, Currency.RUB, sender_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=2, minute=30)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 300.0, Currency.USD, sender_account_id=accounts["elena_invest"].account_id, receiver_account_id=accounts["anna_invest"].account_id, created_at=base_day.replace(hour=11, minute=29)),
        Transaction(TransactionType.DEPOSIT, 400.0, Currency.EUR, receiver_account_id=accounts["maria_invest"].account_id, created_at=base_day.replace(hour=11, minute=30)),
        Transaction(TransactionType.WITHDRAW, 50.0, Currency.EUR, sender_account_id=accounts["anna_savings"].account_id, created_at=base_day.replace(hour=11, minute=31)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 100000.0, Currency.KZT, sender_account_id=accounts["oleg_savings"].account_id, receiver_account_id=accounts["oleg_premium"].account_id, created_at=base_day.replace(hour=11, minute=32)),
        Transaction(TransactionType.TRANSFER_EXTERNAL, 20000.0, Currency.USD, sender_account_id=accounts["ivan_premium"].account_id, created_at=base_day.replace(hour=11, minute=33), max_retries=0),
        Transaction(TransactionType.DEPOSIT, 750.0, Currency.RUB, receiver_account_id=accounts["ivan_savings"].account_id, created_at=base_day.replace(hour=11, minute=34)),
        Transaction(TransactionType.TRANSFER_INTERNAL, 500.0, Currency.RUB, sender_account_id=accounts["ivan_savings"].account_id, receiver_account_id=accounts["elena_savings"].account_id, created_at=base_day.replace(hour=11, minute=35)),
    ]

    queue = TransactionQueue()
    for index, tx in enumerate(transactions, start=1):
        queue.add_transaction(tx, priority=(index % 7) + 1)

    queue.cancel_transaction(transactions[30].transaction_id)
    processor.process_queue(queue, now=datetime(2026, 4, 7, 16, 0, 0))

    return bank, clients, accounts, transactions, audit_log


def main() -> None:
    bank, clients, accounts, transactions, audit_log = create_demo_data()
    report_builder = ReportBuilder(bank, transactions, audit_log, base_output_dir="reports")

    client_report = report_builder.build_client_report("C001")
    bank_report = report_builder.build_bank_report()
    risk_report = report_builder.build_risk_report()

    client_text = report_builder.build_text_report(client_report)
    bank_text = report_builder.build_text_report(bank_report)
    risk_text = report_builder.build_text_report(risk_report)

    client_json_path = report_builder.export_to_json(client_report, "client_C001_report.json")
    bank_json_path = report_builder.export_to_json(bank_report, "bank_report.json")
    risk_json_path = report_builder.export_to_json(risk_report, "risk_report.json")

    client_csv_path = report_builder.export_to_csv(client_report["transactions"], "client_C001_transactions.csv")
    suspicious_csv_path = report_builder.export_to_csv(risk_report["suspicious_operations"], "risk_operations.csv")

    client_txt_path = report_builder.save_text_report(client_text, "client_C001_report.txt")
    bank_txt_path = report_builder.save_text_report(bank_text, "bank_report.txt")
    risk_txt_path = report_builder.save_text_report(risk_text, "risk_report.txt")

    chart_paths = report_builder.save_charts(prefix="day7")

    print_separator("СОЗДАННЫЕ ОТЧЁТЫ")
    print(client_json_path)
    print(bank_json_path)
    print(risk_json_path)
    print(client_csv_path)
    print(suspicious_csv_path)
    print(client_txt_path)
    print(bank_txt_path)
    print(risk_txt_path)

    print_separator("СОЗДАННЫЕ ГРАФИКИ")
    for path in chart_paths:
        print(path)

    print_separator("ПРИМЕР ТЕКСТОВОГО ОТЧЁТА ПО КЛИЕНТУ")
    print(client_text)

    print_separator("КРАТКАЯ СВОДКА")
    print(f"Клиентов: {len(clients)}")
    print(f"Счетов: {len(accounts)}")
    print(f"Транзакций: {len(transactions)}")
    print(f"Audit events: {len(audit_log.entries)}")
    print(f"Общий баланс банка: {bank.get_total_balance()}")


if __name__ == "__main__":
    main()