from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


Money = Decimal


@dataclass(frozen=True)
class IncomeRecord:
    record_id: str
    tax_year: int
    bank: str
    account_last4: str
    transaction_date: date
    income_type: str
    currency: str
    net_amount: Money
    source_file: str
    source_page: int
    source_line: str
    confidence: float
    stock_code: str = ""
    company_name: str = ""
    gross_amount: Optional[Money] = None
    withholding_tax: Optional[Money] = None
    description: str = ""
    review_flags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ParsedDocumentLog:
    source_file: str
    bank: str
    status: str
    pages: int
    text_chars: int
    records_found: int
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvidenceRecord:
    record_id: str
    source: str
    status: str
    url: str = ""
    announcement_title: str = ""
    announcement_date: str = ""
    matched_text: str = ""
    withholding_rate: Optional[Decimal] = None
    dividend_per_share: Optional[Decimal] = None
    currency: str = ""
    review_flags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TaxResult:
    record_id: str
    taxable_amount_original: Money
    fx_rate: Decimal
    taxable_amount_rmb: Money
    mainland_tax_rmb: Money
    candidate_foreign_tax_original: Money
    candidate_foreign_tax_rmb: Money
    credit_limit_rmb: Money
    allowable_credit_rmb: Money
    estimated_tax_due_rmb: Money
    review_flags: tuple[str, ...] = field(default_factory=tuple)
