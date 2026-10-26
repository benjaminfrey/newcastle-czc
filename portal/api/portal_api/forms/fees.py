"""The Town's Planning Fee Schedule (definitions/fees.yaml; projects brief §7)."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from portal_api.forms.definitions import DefinitionError

FILE = Path(__file__).parent / "definitions" / "fees.yaml"


@dataclass(frozen=True)
class FeeLine:
    key: str
    name: str
    fee: object  # dollars, "varies", or {"per_sf": dollars}


@dataclass(frozen=True)
class Permit:
    key: str
    schedule_name: str
    name: str
    application_fee: object  # dollars, "varies", or None (no application fee)
    reviews: tuple


@dataclass(frozen=True)
class Fees:
    permits: tuple
    review_map: dict
    source: dict
    status: str
    approved_by: str | None
    approved_on: str | None

    def line(self, review_key: str) -> tuple[Permit, FeeLine]:
        """The permit and fee line a review falls under."""
        permit_key, line_key = self.review_map[review_key]
        permit = next(p for p in self.permits if p.key == permit_key)
        return permit, next(r for r in permit.reviews if r.key == line_key)


def _fee(where: str, v):
    if v == "varies" or (isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0):
        return v
    if isinstance(v, dict) and set(v) == {"per_sf"}:
        return {"per_sf": float(v["per_sf"])}
    raise DefinitionError(f"fees.yaml: {where}: a fee is dollars, varies, or per_sf")


@cache
def load_fees(path: Path = FILE) -> Fees:
    doc = yaml.safe_load(path.read_text())
    permits = []
    for p in doc["permits"]:
        app_fee = None if p["application_fee"] is None else _fee(p["key"], p["application_fee"])
        permits.append(Permit(p["key"], p["schedule_name"], p["name"], app_fee,
                              tuple(FeeLine(r["key"], r["name"], _fee(f"{p['key']}.{r['key']}", r["fee"]))
                                    for r in p["reviews"])))
    fees = Fees(tuple(permits), dict(doc["review_map"]), dict(doc["source"]), doc["status"],
                doc.get("approved_by"), doc.get("approved_on"))
    for key in fees.review_map:
        try:
            fees.line(key)
        except StopIteration:
            raise DefinitionError(f"fees.yaml: review_map {key!r} names no fee line") from None
    return fees
