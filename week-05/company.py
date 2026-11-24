"""Company folders for the supplier-response team, and reading their CSV files without assuming column names.

A company folder (for example week-05/brookfield-bikes or week-05/copperline-coffee) holds
  orders.csv  bill-of-materials.csv  parts.csv  inbound.csv  suppliers.csv
  prompts/    analyst.txt  customer-writer.txt  orchestrator.txt  reviewer.txt  supplier-writer.txt
  supplier-emails/

Each company names its columns differently (Brookfield: model, qty, ship_in_days, qty_per_bike; Copperline:
product, units, ship_by_day, per_unit). read_table works out from each file's header row which column holds
which field, by scoring the words in each header against the words that field is usually called, and by checking
that numeric fields really hold whole numbers. It returns rows keyed by the same canonical field names for every
company. If a required field can't be found, or two columns tie for it, it raises ColumnError and names the headers.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

WEEK_DIR = Path(__file__).resolve().parent
DEFAULT_ORG = WEEK_DIR / "brookfield-bikes"

TABLES = ("orders", "bill-of-materials", "parts", "inbound", "suppliers")
PROMPTS = ("analyst", "customer-writer", "orchestrator", "reviewer", "supplier-writer")


class ColumnError(ValueError):
    """A CSV file's header row can't be matched to the fields we need."""


def _field(words: str, numeric: bool = False, required: bool = True) -> dict:
    """words: 'word:weight word:weight ...' (singular words; plurals are matched too)."""
    return {"words": {w: int(n) for w, n in (p.split(":") for p in words.split())},
            "numeric": numeric, "required": required}


SPECS: dict[str, dict[str, dict]] = {
    "orders": {
        "order_id": _field("order:2 id:3 number:2 num:2 no:2 ref:2 reference:2"),
        "customer": _field("customer:5 client:5 buyer:5 purchaser:5 account:3 company:3 name:1"),
        "contact_email": _field("email:5 mail:4 contact:2", required=False),
        "product": _field("product:5 model:5 item:4 sku:3 machine:4 bike:3 type:2 goods:3"),
        "quantity": _field("qty:5 quantity:5 unit:4 count:3 piece:3 pcs:3 ordered:2 bike:2", numeric=True),
        "ship_day": _field("ship:4 shipping:4 due:4 deliver:4 delivery:4 promise:3 need:3 by:1 day:3", numeric=True),
        "late_penalty": _field("penalty:5 late:4 fine:3", required=False),
    },
    "bill-of-materials": {
        "product": _field("product:5 model:5 item:4 machine:4 bike:3 type:2"),
        "part_id": _field("part:3 id:3 component:4 sku:2 number:1"),
        "per_unit": _field("per:3 unit:3 qty:3 quantity:3 each:2 usage:2 required:2 count:2", numeric=True),
    },
    "parts": {
        "part_id": _field("part:3 id:3 sku:2 number:1"),
        "description": _field("description:5 desc:5 name:3 title:3"),
        "on_hand": _field("on:1 hand:4 stock:4 inventory:4 available:3 qty:2 quantity:2 count:2", numeric=True),
        "supplier": _field("supplier:5 vendor:5 source:3 manufacturer:2"),
    },
    "inbound": {
        "po_number": _field("po:4 purchase:3 order:3 number:3 num:2 ref:2 id:1"),
        "part_id": _field("part:3 id:3 sku:2"),
        "supplier": _field("supplier:5 vendor:5 source:3 manufacturer:2"),
        "quantity": _field("qty:5 quantity:5 unit:4 count:3", numeric=True),
        "arrives_in_days": _field("arrive:4 eta:4 due:3 delivery:3 deliver:3 day:3", numeric=True),
    },
    "suppliers": {
        "supplier": _field("supplier:5 vendor:5 company:3 name:1"),
        "contact_name": _field("contact:3 name:3 rep:2 person:3 manager:2", required=False),
        "contact_email": _field("email:5 mail:4 contact:2", required=False),
        "part_id": _field("part:3 id:3 sku:2", required=False),
    },
}


# ---------------------------------------------------------------------------
# Company folders
# ---------------------------------------------------------------------------

def resolve_org(value: str | Path | None) -> Path:
    """The company folder named by --org: a path, or a folder name under week-05. None means Brookfield."""
    if value is None:
        path = DEFAULT_ORG
    else:
        path = Path(value)
        if not path.is_dir() and (WEEK_DIR / path).is_dir():
            path = WEEK_DIR / path
    path = path.resolve()
    if not path.is_dir():
        raise ValueError(f"company folder not found: {value}")
    missing = ([f"{t}.csv" for t in TABLES if not (path / f"{t}.csv").is_file()]
               + [f"prompts/{p}.txt" for p in PROMPTS if not (path / "prompts" / f"{p}.txt").is_file()])
    if missing:
        raise ValueError(f"{path} is missing: {', '.join(missing)}")
    return path


# ---------------------------------------------------------------------------
# Column inference
# ---------------------------------------------------------------------------

def _stem(token: str) -> str:
    return token[:-1] if token.endswith("s") and not token.endswith("ss") and len(token) > 2 else token


def _tokens(header: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", header)          # camelCase -> camel Case
    return [_stem(t) for t in re.split(r"[^a-z0-9]+", spaced.lower()) if t]


def _is_whole_numbers(values: list[str]) -> bool:
    filled = [v for v in values if v]
    return bool(filled) and all(re.fullmatch(r"-?\d+(\.0+)?", v) for v in filled)


def resolve_columns(table: str, headers: list[str], rows: list[dict[str, str]]) -> dict[str, str]:
    """Map each canonical field of the table to the header that holds it."""
    spec = SPECS[table]
    numeric_ok = {h: _is_whole_numbers([r.get(h, "") for r in rows]) for h in headers}
    candidates: list[tuple[int, str, str]] = []
    for field, s in spec.items():
        for header in headers:
            if s["numeric"] and not numeric_ok[header]:
                continue
            score = sum(s["words"].get(t, 0) for t in _tokens(header))
            if re.sub(r"[^a-z0-9]+", "_", header.lower()).strip("_") == field:
                score += 10
            if score > 0:
                candidates.append((score, field, header))
    candidates.sort(key=lambda c: (-c[0], c[1], c[2]))

    mapping: dict[str, str] = {}
    used: set[str] = set()
    for score, field, header in candidates:
        if field in mapping or header in used:
            continue
        rivals = [h for sc, f, h in candidates if f == field and sc == score and h != header and h not in used]
        if rivals:
            raise ColumnError(f"{table}.csv: can't tell which column holds {field}: "
                              f"{header!r} and {rivals[0]!r} fit equally well. Headers: {headers}")
        mapping[field] = header
        used.add(header)
    missing = [f for f, s in spec.items() if s["required"] and f not in mapping]
    if missing:
        raise ColumnError(f"{table}.csv: can't tell which column holds {', '.join(missing)}. Headers: {headers}")
    return mapping


def _read_raw(org_dir: Path, table: str) -> tuple[list[str], list[dict[str, str]]]:
    with (org_dir / f"{table}.csv").open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = [(h or "").strip() for h in (reader.fieldnames or [])]
        rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]
    return headers, rows


def read_table(org_dir: Path, table: str) -> list[dict[str, str]]:
    """Rows of one of the company's CSV files, keyed by canonical field names (values are stripped strings).
    Optional fields the file doesn't have come back as ''. Raises OSError or ColumnError."""
    headers, rows = _read_raw(org_dir, table)
    mapping = resolve_columns(table, headers, rows)
    return [{field: row.get(mapping.get(field, ""), "") for field in SPECS[table]} for row in rows]


def describe_columns(org_dir: Path) -> dict[str, dict[str, str]]:
    """For each CSV file, which header was chosen for each field (for printing)."""
    out: dict[str, dict[str, str]] = {}
    for table in TABLES:
        headers, rows = _read_raw(org_dir, table)
        out[f"{table}.csv"] = resolve_columns(table, headers, rows)
    return out
