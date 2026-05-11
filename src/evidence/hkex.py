from __future__ import annotations

import re
import urllib.parse
import urllib.request
from decimal import Decimal

from models import EvidenceRecord, IncomeRecord


class HKEXEvidenceProvider:
    """Small, replaceable HKEX evidence layer.

    HKEX pages change over time, so this provider records the official lookup
    URL and only applies tax data when it can find explicit withholding wording.
    """

    hkex_home = "https://www.hkexnews.hk/index.htm"
    entitlements_url = "https://www3.hkexnews.hk/reports/doe/eent.htm"

    def __init__(self, enabled: bool = True, timeout: int = 10):
        self.enabled = enabled
        self.timeout = timeout

    def lookup_many(self, records: list[IncomeRecord]) -> dict[str, EvidenceRecord]:
        evidence: dict[str, EvidenceRecord] = {}
        for record in records:
            if record.income_type != "dividend":
                continue
            evidence[record.record_id] = self.lookup_dividend(record)
        return evidence

    def lookup_dividend(self, record: IncomeRecord) -> EvidenceRecord:
        if not record.stock_code:
            return EvidenceRecord(
                record_id=record.record_id,
                source="HKEXnews",
                status="not_searched",
                url=self.hkex_home,
                review_flags=("stock_code_missing",),
            )

        query = urllib.parse.urlencode({"q": f"{record.stock_code} dividend withholding tax"})
        search_url = f"{self.hkex_home}?{query}"
        if not self.enabled:
            return EvidenceRecord(
                record_id=record.record_id,
                source="HKEXnews",
                status="manual_review_required",
                url=search_url,
                review_flags=("hkex_network_lookup_disabled", "manual_hkex_announcement_match_required"),
            )

        try:
            request = urllib.request.Request(
                self.entitlements_url,
                headers={"User-Agent": "tax-calculation-local-tool/1.0"},
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            return EvidenceRecord(
                record_id=record.record_id,
                source="HKEXnews",
                status="lookup_failed",
                url=search_url,
                review_flags=(f"hkex_lookup_failed:{type(exc).__name__}", "manual_hkex_announcement_match_required"),
            )

        normalized_code = record.stock_code.lstrip("0") or record.stock_code
        if normalized_code not in html and record.stock_code not in html:
            return EvidenceRecord(
                record_id=record.record_id,
                source="HKEXnews",
                status="not_found_in_current_entitlements",
                url=search_url,
                review_flags=("manual_hkex_announcement_match_required",),
            )

        snippet = self._snippet_around_code(html, normalized_code)
        withholding_rate = self._extract_withholding_rate(snippet)
        flags = []
        status = "matched_current_entitlements"
        if withholding_rate is None:
            flags.append("withholding_rate_not_found_in_snippet")
        return EvidenceRecord(
            record_id=record.record_id,
            source="HKEXnews",
            status=status,
            url=self.entitlements_url,
            matched_text=self._clean_html(snippet)[:500],
            withholding_rate=withholding_rate,
            review_flags=tuple(flags),
        )

    def _snippet_around_code(self, html: str, code: str) -> str:
        index = html.find(code)
        if index < 0:
            return ""
        start = max(index - 800, 0)
        end = min(index + 1200, len(html))
        return html[start:end]

    def _extract_withholding_rate(self, text: str) -> Decimal | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:withholding|tax)", text, flags=re.I)
        if not match:
            match = re.search(r"(?:withholding|tax).*?(\d+(?:\.\d+)?)\s*%", text, flags=re.I)
        if not match:
            return None
        return Decimal(match.group(1)) / Decimal("100")

    def _clean_html(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(text.split())
