# Hong Kong Overseas Income Tax Calculator

Local-first tool for organizing Hong Kong bank statement income, estimating mainland China individual income tax, and preparing a reviewable Excel workbook.

## Run

Use Python 3 with `pypdf` and `openpyxl` installed. If the packages are missing, install them first:

```bash
python3 -m pip install -r requirements.txt
```

### Desktop App

Open the local upload window:

```bash
python3 src/gui.py
```

In the window you can choose one or more PDF bank statements, choose the Excel output path, and click `Generate Report`.
By default, HKEX online lookup is disabled so the tool can run more reliably without internet access.

### Command Line

You can still run the original command line flow:

```bash
python3 src/main.py --year 2025 --bank standard_chartered_hk --input inputs --output outputs/tax_report_2025.xlsx --no-hkex
```

Remove `--no-hkex` to allow live HKEX lookup attempts. Any unmatched dividend remains in `Review_Flags`.

## Reading The Excel Output

The workbook keeps the original review sheets and adds beginner-friendly Chinese explanation sheets:

- `Chinese_Summary`: Chinese summary of parsed records, taxable income, tax before credit, credit, estimated tax due, and review count.
- `Calculation_Process`: one row per income record with the calculation process, such as taxable amount multiplied by FX rate, tax rate calculation, foreign tax credit limit, and final estimated tax due.

The key formula is:

```text
estimated tax due = mainland tax before credit - allowable foreign tax credit
```

## Extending To Another Bank

Add a parser implementing `parse_directory()` and returning the common `IncomeRecord` fields, then register it in `src/parsers/registry.py`. The tax engine and Excel report do not need bank-specific changes.

## Important Limitations

The generated workbook is for organization and estimation. Before filing, manually confirm tax residency, dividend withholding evidence, official FX rates, and any foreign tax credit claim with a professional adviser or the tax authority.
