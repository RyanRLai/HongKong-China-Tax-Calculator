from __future__ import annotations

import hashlib
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from models import IncomeRecord, ParsedDocumentLog
from parsers.base import ParseResult


class StandardCharteredHKParser:
    bank_code = "standard_chartered_hk"
    bank_name = "Standard Chartered Hong Kong"

    _currency_re = re.compile(r"^(HKD|USD|CNY|CNH|AUD|CAD|CHF|EUR|GBP|JPY|NZD|SGD)\b")
    _account_re = re.compile(r"(\d{3,}-\d{2,}-\d{3,}-\d{3,})(?:-\w+)?")
    _money_re = re.compile(r"(?<![\w])[-(]?\d[\d,]*\.\d{2}\)?")
    _stock_re = re.compile(r"\((\d{1,6})\)")
    _month_names = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def parse_directory(self, input_dir: Path, tax_year: int) -> ParseResult:
        records: list[IncomeRecord] = []
        logs: list[ParsedDocumentLog] = []
        for pdf_path in sorted(input_dir.glob("*.pdf")):
            file_records, doc_log = self._parse_pdf(pdf_path, tax_year)
            records.extend(file_records)
            logs.append(doc_log)
        return ParseResult(records=records, logs=logs)

    def _parse_pdf(self, pdf_path: Path, tax_year: int) -> tuple[list[IncomeRecord], ParsedDocumentLog]:
        warnings: list[str] = []
        records: list[IncomeRecord] = []
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            page_texts = [page.extract_text() or "" for page in reader.pages]
        except ImportError as exc:
            raise RuntimeError("Missing dependency: install pypdf with `python3 -m pip install -r requirements.txt`.") from exc
        except Exception as exc:  # pragma: no cover - defensive for malformed PDFs
            return [], ParsedDocumentLog(
                source_file=pdf_path.name,
                bank=self.bank_code,
                status="error",
                pages=0,
                text_chars=0,
                records_found=0,
                warnings=(f"pdf_read_error: {type(exc).__name__}",),
            )

        full_text = "\n".join(page_texts)
        statement_date = self._extract_statement_date(full_text)
        if statement_date is None:
            warnings.append("statement_date_not_found")

        current_currency = ""
        current_account_last4 = ""
        for page_no, text in enumerate(page_texts, start=1):
            for raw_line in text.splitlines():
                line = " ".join(raw_line.replace("\xa0", " ").split())
                if not line:
                    continue
                currency_match = self._currency_re.match(line)
                if currency_match:
                    current_currency = currency_match.group(1)
                account_match = self._account_re.search(line)
                if account_match:
                    current_account_last4 = account_match.group(1)[-4:]

                lower_line = line.lower()
                if "cash dividend" in lower_line:
                    record = self._parse_dividend_line(
                        line, pdf_path.name, page_no, tax_year, statement_date, current_currency, current_account_last4
                    )
                    if record:
                        records.append(record)
                elif "credit interest" in lower_line:
                    record = self._parse_interest_line(
                        line, pdf_path.name, page_no, tax_year, statement_date, current_currency, current_account_last4
                    )
                    if record:
                        records.append(record)

        all_record_count = len(records)
        records = [record for record in records if record.transaction_date.year == tax_year]
        excluded_count = all_record_count - len(records)
        if excluded_count:
            warnings.append(f"excluded_non_tax_year_records:{excluded_count}")

        status = "ok" if records else "no_records_found"
        if not full_text.strip():
            status = "no_text_found"
            warnings.append("pdf_may_be_scanned")
        return records, ParsedDocumentLog(
            source_file=pdf_path.name,
            bank=self.bank_code,
            status=status,
            pages=len(page_texts),
            text_chars=len(full_text),
            records_found=len(records),
            warnings=tuple(warnings),
        )

    def _parse_dividend_line(
        self,
        line: str,
        source_file: str,
        page_no: int,
        tax_year: int,
        statement_date: date | None,
        current_currency: str,
        account_last4: str,
    ) -> IncomeRecord | None:
        tx_date = self._extract_transaction_date(line, statement_date, tax_year)
        amount = self._extract_transaction_amount(line)
        if tx_date is None or amount is None:
            return None
        stock_code_match = self._stock_re.search(line)
        stock_code = stock_code_match.group(1).zfill(5) if stock_code_match else ""
        company_name = self._extract_company_name(line)
        flags = []
        confidence = 0.86
        if not stock_code:
            flags.append("stock_code_not_found")
            confidence -= 0.15
        if not current_currency:
            flags.append("currency_not_found")
            confidence -= 0.2
        flags.append("withholding_not_confirmed")
        return IncomeRecord(
            record_id=self._record_id(source_file, page_no, line),
            tax_year=tax_year,
            bank=self.bank_code,
            account_last4=account_last4,
            transaction_date=tx_date,
            income_type="dividend",
            currency=current_currency or "UNKNOWN",
            net_amount=amount,
            source_file=source_file,
            source_page=page_no,
            source_line=line,
            confidence=max(confidence, 0.1),
            stock_code=stock_code,
            company_name=company_name,
            description="Cash Dividend",
            review_flags=tuple(flags),
        )

    def _parse_interest_line(
        self,
        line: str,
        source_file: str,
        page_no: int,
        tax_year: int,
        statement_date: date | None,
        current_currency: str,
        account_last4: str,
    ) -> IncomeRecord | None:
        tx_date = self._extract_transaction_date(line, statement_date, tax_year)
        amount = self._extract_transaction_amount(line)
        if tx_date is None or amount is None:
            return None
        flags = []
        confidence = 0.9
        if not current_currency:
            flags.append("currency_not_found")
            confidence -= 0.2
        return IncomeRecord(
            record_id=self._record_id(source_file, page_no, line),
            tax_year=tax_year,
            bank=self.bank_code,
            account_last4=account_last4,
            transaction_date=tx_date,
            income_type="interest",
            currency=current_currency or "UNKNOWN",
            net_amount=amount,
            source_file=source_file,
            source_page=page_no,
            source_line=line,
            confidence=max(confidence, 0.1),
            description="Credit Interest",
            review_flags=tuple(flags),
        )

    def _extract_statement_date(self, text: str) -> date | None:
        patterns = [
            re.compile(r"Statement Date.*?(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日"),
            re.compile(r"Statement Date.*?(\d{4})\s+(\d{1,2})\s+(\d{1,2})年"),
            re.compile(r"Statement Date.*?(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})"),
        ]
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            try:
                if match.group(2).isalpha():
                    day = int(match.group(1))
                    month = self._month_names[match.group(2).lower()]
                    year = int(match.group(3))
                else:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                return date(year, month, day)
            except (ValueError, KeyError):
                continue
        return None

    def _extract_transaction_date(self, line: str, statement_date: date | None, tax_year: int) -> date | None:
        candidates: list[tuple[int, int]] = []
        match = re.search(r"(\d{1,2})月\s*(\d{1,2})日", line)
        if match:
            candidates.append((int(match.group(1)), int(match.group(2))))
        match = re.search(r"^(\d{1,2})\s+(\d{1,2})月\s*日", line)
        if match:
            candidates.append((int(match.group(1)), int(match.group(2))))
        match = re.search(r"^(\d{1,2})\s+([A-Za-z]{3})\b", line)
        if match:
            month = self._month_names.get(match.group(2).lower())
            if month:
                candidates.append((month, int(match.group(1))))
        if not candidates:
            return None

        month, day = candidates[0]
        year = tax_year
        if statement_date:
            year = statement_date.year
            # January statements commonly contain December transactions from the prior tax year.
            if month > statement_date.month:
                year -= 1
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _extract_transaction_amount(self, line: str) -> Decimal | None:
        amounts = [self._to_decimal(token) for token in self._money_re.findall(line)]
        amounts = [amount for amount in amounts if amount is not None]
        if not amounts:
            return None
        return amounts[0]

    def _extract_company_name(self, line: str) -> str:
        after_stock = self._stock_re.split(line, maxsplit=1)
        if len(after_stock) >= 3:
            candidate = after_stock[2]
        else:
            candidate = line.split("Cash Dividend", 1)[-1]
        candidate = re.split(r"\b存賬\b|\bDeposit\b|\d[\d,]*\.\d{2}", candidate, maxsplit=1)[0]
        return " ".join(candidate.replace(")", " ").split())

    def _to_decimal(self, token: str) -> Decimal | None:
        cleaned = token.replace(",", "")
        negative = cleaned.startswith("(") and cleaned.endswith(")")
        cleaned = cleaned.strip("()")
        try:
            amount = Decimal(cleaned)
            return -amount if negative else amount
        except InvalidOperation:
            return None

    def _record_id(self, source_file: str, page_no: int, line: str) -> str:
        digest = hashlib.sha1(f"{source_file}|{page_no}|{line}".encode("utf-8")).hexdigest()
        return digest[:12]
