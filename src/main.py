from __future__ import annotations

import argparse
from pathlib import Path

from workflow import run_tax_calculation


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hong Kong overseas income tax calculator")
    parser.add_argument("--year", type=int, required=True, help="Tax year, e.g. 2025")
    parser.add_argument("--bank", required=True, help="Bank parser code, e.g. standard_chartered_hk")
    parser.add_argument("--input", required=True, type=Path, help="Input directory containing statement PDFs")
    parser.add_argument("--output", required=True, type=Path, help="Output .xlsx path")
    parser.add_argument("--rules-dir", type=Path, default=Path("tax_rules"), help="Tax rules directory")
    parser.add_argument("--no-hkex", action="store_true", help="Disable live HKEX lookup and create manual-review evidence rows")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    summary = run_tax_calculation(
        year=args.year,
        bank=args.bank,
        input_dir=args.input,
        output_path=args.output,
        rules_dir=args.rules_dir,
        hkex_enabled=not args.no_hkex,
    )
    print(f"Parsed PDFs: {summary.parsed_pdfs}")
    print(f"Income records: {summary.income_records}")
    print(f"Rows needing review: {summary.rows_needing_review}")
    print(f"Wrote: {summary.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
