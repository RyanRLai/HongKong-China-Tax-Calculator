from __future__ import annotations

from .standard_chartered_hk import StandardCharteredHKParser


def get_parser(bank_code: str):
    parsers = {
        StandardCharteredHKParser.bank_code: StandardCharteredHKParser,
    }
    try:
        return parsers[bank_code]()
    except KeyError as exc:
        supported = ", ".join(sorted(parsers))
        raise ValueError(f"Unsupported bank '{bank_code}'. Supported banks: {supported}") from exc
