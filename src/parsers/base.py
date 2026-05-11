from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from models import IncomeRecord, ParsedDocumentLog


@dataclass(frozen=True)
class ParseResult:
    records: list[IncomeRecord]
    logs: list[ParsedDocumentLog]


class BaseStatementParser(Protocol):
    bank_code: str

    def parse_directory(self, input_dir: Path, tax_year: int) -> ParseResult:
        ...
