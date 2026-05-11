from __future__ import annotations

from models import IncomeRecord, TaxResult
from tax.rules import TaxRules


def build_calculation_process_text(record: IncomeRecord, result: TaxResult, rules: TaxRules) -> str:
    steps = [
        f"1. 原币应税金额 = {result.taxable_amount_original} {record.currency}",
        (
            "2. 应税收入人民币 = 原币应税金额 × 汇率 = "
            f"{result.taxable_amount_original} × {result.fx_rate} = {result.taxable_amount_rmb} RMB"
        ),
        (
            "3. 中国内地税额 = 应税收入人民币 × 税率 = "
            f"{result.taxable_amount_rmb} × {rules.mainland_rate} = {result.mainland_tax_rmb} RMB"
        ),
        (
            "4. 候选境外税人民币 = 候选境外税 × 汇率 = "
            f"{result.candidate_foreign_tax_original} × {result.fx_rate} = {result.candidate_foreign_tax_rmb} RMB"
        ),
        (
            "5. 可抵扣境外税额 = min(候选境外税人民币, 中国内地税额) = "
            f"{result.allowable_credit_rmb} RMB"
        ),
        (
            "6. 估算应缴税 = 中国内地税额 - 可抵扣境外税额 = "
            f"{result.mainland_tax_rmb} - {result.allowable_credit_rmb} = {result.estimated_tax_due_rmb} RMB"
        ),
    ]
    return "\n".join(steps)
