from __future__ import annotations

import unittest
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models import IncomeRecord
from tax import TaxRules, calculate_tax_results


class TaxEngineTests(unittest.TestCase):
    def test_interest_without_foreign_credit(self):
        record = IncomeRecord(
            record_id="r1",
            tax_year=2025,
            bank="fake_bank",
            account_last4="1234",
            transaction_date=date(2025, 12, 31),
            income_type="interest",
            currency="HKD",
            net_amount=Decimal("100.00"),
            source_file="fake.pdf",
            source_page=1,
            source_line="CREDIT INTEREST 100.00 1000.00",
            confidence=0.9,
        )
        rules = TaxRules(year=2025, mainland_rate=Decimal("0.20"), fx_rates={"HKD": Decimal("1")}, notes=())
        [result] = calculate_tax_results([record], {}, rules)
        self.assertEqual(result.mainland_tax_rmb, Decimal("20.00"))
        self.assertEqual(result.estimated_tax_due_rmb, Decimal("20.00"))

    def test_credit_capped_by_mainland_tax(self):
        record = IncomeRecord(
            record_id="r2",
            tax_year=2025,
            bank="fake_bank",
            account_last4="1234",
            transaction_date=date(2025, 8, 1),
            income_type="dividend",
            currency="HKD",
            net_amount=Decimal("80.00"),
            gross_amount=Decimal("100.00"),
            withholding_tax=Decimal("30.00"),
            source_file="fake.pdf",
            source_page=1,
            source_line="Cash Dividend",
            confidence=0.9,
        )
        rules = TaxRules(year=2025, mainland_rate=Decimal("0.20"), fx_rates={"HKD": Decimal("1")}, notes=())
        [result] = calculate_tax_results([record], {}, rules)
        self.assertEqual(result.credit_limit_rmb, Decimal("20.00"))
        self.assertEqual(result.allowable_credit_rmb, Decimal("20.00"))
        self.assertEqual(result.estimated_tax_due_rmb, Decimal("0.00"))


if __name__ == "__main__":
    unittest.main()
