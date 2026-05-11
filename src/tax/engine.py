from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from models import EvidenceRecord, IncomeRecord, TaxResult
from tax.rules import TaxRules


TWOPLACES = Decimal("0.01")


def calculate_tax_results(
    records: list[IncomeRecord],
    evidence: dict[str, EvidenceRecord],
    rules: TaxRules,
) -> list[TaxResult]:
    results: list[TaxResult] = []
    for record in records:
        ev = evidence.get(record.record_id)
        flags = list(record.review_flags)
        gross_amount = record.gross_amount or record.net_amount
        foreign_tax = record.withholding_tax or Decimal("0")

        if record.income_type == "dividend":
            if ev and ev.withholding_rate is not None and foreign_tax == 0:
                flags.append("withholding_rate_found_but_not_applied_without_share_reconciliation")
            if foreign_tax == 0:
                flags.append("no_confirmed_foreign_tax_credit")

        fx_rate = rules.fx_rates.get(record.currency, Decimal("1"))
        if record.currency not in rules.fx_rates:
            flags.append("fx_rate_missing_or_placeholder")

        taxable_rmb = money(gross_amount * fx_rate)
        mainland_tax = money(taxable_rmb * rules.mainland_rate)
        foreign_tax_rmb = money(foreign_tax * fx_rate)
        credit_limit = mainland_tax
        allowable_credit = min(foreign_tax_rmb, credit_limit)
        tax_due = money(mainland_tax - allowable_credit)
        results.append(
            TaxResult(
                record_id=record.record_id,
                taxable_amount_original=money(gross_amount),
                fx_rate=fx_rate,
                taxable_amount_rmb=taxable_rmb,
                mainland_tax_rmb=mainland_tax,
                candidate_foreign_tax_original=money(foreign_tax),
                candidate_foreign_tax_rmb=foreign_tax_rmb,
                credit_limit_rmb=credit_limit,
                allowable_credit_rmb=allowable_credit,
                estimated_tax_due_rmb=tax_due,
                review_flags=tuple(dict.fromkeys(flags)),
            )
        )
    return results


def money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
