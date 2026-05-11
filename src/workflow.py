from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evidence import HKEXEvidenceProvider
from parsers import get_parser
from reporting import write_excel_report
from tax import calculate_tax_results, load_tax_rules


@dataclass(frozen=True)
class TaxCalculationSummary:
    parsed_pdfs: int
    income_records: int
    rows_needing_review: int
    output_path: Path


def run_tax_calculation(
    year: int,
    bank: str,
    input_dir: Path,
    output_path: Path,
    rules_dir: Path,
    hkex_enabled: bool,
) -> TaxCalculationSummary:
    parser = get_parser(bank)
    rules = load_tax_rules(year, rules_dir)
    parse_result = parser.parse_directory(input_dir, year)
    evidence_provider = HKEXEvidenceProvider(enabled=hkex_enabled)
    evidence = evidence_provider.lookup_many(parse_result.records)
    tax_results = calculate_tax_results(parse_result.records, evidence, rules)
    write_excel_report(output_path, parse_result.records, tax_results, parse_result.logs, evidence, rules)

    flagged = sum(1 for result in tax_results if result.review_flags)
    return TaxCalculationSummary(
        parsed_pdfs=len(parse_result.logs),
        income_records=len(parse_result.records),
        rows_needing_review=flagged,
        output_path=output_path,
    )
