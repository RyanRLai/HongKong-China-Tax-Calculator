from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class TaxRules:
    year: int
    mainland_rate: Decimal
    fx_rates: dict[str, Decimal]
    notes: tuple[str, ...]


def load_tax_rules(year: int, rules_dir: Path) -> TaxRules:
    path = rules_dir / f"{year}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Tax rules file not found: {path}")
    data = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    rate = Decimal(str(data.get("mainland_individual_income_tax_rate", "0.20")))
    fx_rates = {
        key.removeprefix("fx_rate_").upper(): Decimal(str(value))
        for key, value in data.items()
        if key.startswith("fx_rate_")
    }
    notes = tuple(value for key, value in sorted(data.items()) if key.startswith("note_"))
    return TaxRules(year=year, mainland_rate=rate, fx_rates=fx_rates, notes=notes)


def _parse_simple_yaml(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip("'\"")
        result[key.strip()] = value
    return result
