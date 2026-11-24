"""Supply MCP server: a company's parts, orders, and shipment coverage.

Tools (all read-only; they read the CSV files in the company folder, week-05/brookfield-bikes by default)
  get_part(part_id)                  stock on hand, scheduled shipments, and the products that use the part
  get_orders_for_part(part_id)       open orders that need the part, with units needed, ship day, late penalty
  check_coverage(part_id, arrivals)  which orders the part covers if it arrives on the given schedule

Days are counted from today: day 0 is today, and a shipment that arrives on day N can be
used by an order that ships on day N.

Run (from the repository root, with the repository's .venv):
    .venv\\Scripts\\python.exe week-05\\supply_mcp_server.py [--org copperline-coffee]

--org names a company folder (a path, or a folder name under week-05) laid out like brookfield-bikes. The CSV
column names are not assumed: company.py works out from each header row which column holds the product, the
quantity, the parts per unit, the ship day, and so on.

No API key is needed: the server returns data, and the client (an agent) does the writing.
The CSV files are re-read on every call, so edits show up without restarting the server.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TypedDict

import company
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

DATA_DIR = company.DEFAULT_ORG

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


def log(message: str) -> None:
    print(f"[supply_mcp_server] {message}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def read_table(table: str) -> list[dict[str, str]]:
    """Rows of one CSV file, keyed by canonical field names (see company.py)."""
    try:
        return company.read_table(DATA_DIR, table)
    except company.ColumnError as e:
        raise ToolError(str(e)) from None
    except OSError as e:
        raise ToolError(f"{table}.csv could not be read ({e.__class__.__name__}).") from None


def to_int(value: str, what: str, source: str) -> int:
    try:
        return int(float(value)) if value.replace(".", "", 1).lstrip("-").isdigit() else int(value)
    except ValueError:
        raise ToolError(f"{source}: {what} {value!r} is not a whole number.") from None


class ScheduledShipment(TypedDict):
    po_number: str
    supplier: str
    qty: int
    arrives_in_days: int


class ProductUse(TypedDict):
    product: str
    parts_per_unit: int


class PartInfo(TypedDict):
    part_id: str
    description: str
    supplier: str
    on_hand: int
    scheduled_shipments: list[ScheduledShipment]
    products_using_part: list[ProductUse]


class OrderNeed(TypedDict):
    order_id: str
    customer: str
    product: str
    units_ordered: int
    parts_per_unit: int
    units_needed: int
    ship_in_days: int
    late_penalty: str


class OrdersForPart(TypedDict):
    part_id: str
    orders: list[OrderNeed]            # in ship-day order
    total_units_needed: int


class Arrival(TypedDict):
    qty: int
    day: int


class OrderCoverage(TypedDict):
    order_id: str
    customer: str
    units_needed: int
    ship_in_days: int
    late_penalty: str
    covered: bool
    units_short: int                   # units not available by the ship day (0 if covered)
    first_ship_day: int | None         # first day the order can ship complete; None if the arrivals never cover it
    days_late: int | None              # first_ship_day - ship_in_days (0 if covered); None if never covered
    units_never_covered: int           # units still missing after every listed arrival (0 if it is ever covered)


class CoverageResult(TypedDict):
    part_id: str
    on_hand: int
    arrivals_used: list[Arrival]
    total_supply: int
    total_units_needed: int
    orders: list[OrderCoverage]
    orders_at_risk: list[str]


def find_part(part_id: str) -> dict[str, str]:
    wanted = (part_id or "").strip().upper()
    if not wanted:
        raise ToolError("No part_id was given. Use a part id such as MC-500.")
    parts = read_table("parts")
    for row in parts:
        if row["part_id"].upper() == wanted:
            return row
    known = ", ".join(r["part_id"] for r in parts)
    raise ToolError(f"No part {part_id.strip()!r} was found. Known parts: {known}.")


def products_for_part(part_id: str) -> list[ProductUse]:
    bom = read_table("bill-of-materials")
    return [ProductUse(product=r["product"], parts_per_unit=to_int(r["per_unit"], "parts per unit", "bill-of-materials.csv"))
            for r in bom if r["part_id"].upper() == part_id.upper()]


def orders_needing(part_id: str) -> list[OrderNeed]:
    per_unit = {m["product"]: m["parts_per_unit"] for m in products_for_part(part_id)}
    orders = read_table("orders")
    needs: list[OrderNeed] = []
    for r in orders:
        if r["product"] not in per_unit:
            continue
        units = to_int(r["quantity"], "quantity", "orders.csv")
        needs.append(OrderNeed(
            order_id=r["order_id"], customer=r["customer"], product=r["product"],
            units_ordered=units, parts_per_unit=per_unit[r["product"]], units_needed=units * per_unit[r["product"]],
            ship_in_days=to_int(r["ship_day"], "ship day", "orders.csv"),
            late_penalty=r["late_penalty"] or "unknown",
        ))
    needs.sort(key=lambda n: (n["ship_in_days"], n["order_id"]))
    return needs


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

def validate_arrivals(arrivals: list[Arrival]) -> list[Arrival]:
    cleaned = []
    for i, a in enumerate(arrivals or [], 1):
        qty, day = a.get("qty"), a.get("day")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ToolError(f"Arrival {i}: qty must be a whole number above 0 (got {qty!r}).")
        if not isinstance(day, int) or isinstance(day, bool) or day < 0:
            raise ToolError(f"Arrival {i}: day must be a whole number of days from today, 0 or more (got {day!r}).")
        cleaned.append(Arrival(qty=qty, day=day))
    return sorted(cleaned, key=lambda a: a["day"])


def compute_coverage(on_hand: int, needs: list[OrderNeed], arrivals: list[Arrival]) -> list[OrderCoverage]:
    """Fill orders complete, in ship-day order. Each order's units come after the units of every
    earlier order, so a short order holds up the ones after it."""
    def supply_by(day: int) -> int:
        return on_hand + sum(a["qty"] for a in arrivals if a["day"] <= day)

    total_supply = supply_by(max([0] + [a["day"] for a in arrivals]))
    results: list[OrderCoverage] = []
    cumulative = 0                      # units needed by this order and every order before it
    for n in needs:
        cumulative += n["units_needed"]
        short_at_ship = max(0, cumulative - supply_by(n["ship_in_days"]))
        units_short = min(n["units_needed"], short_at_ship)
        if cumulative <= supply_by(n["ship_in_days"]):
            first_day, late = n["ship_in_days"], 0
        elif cumulative <= total_supply:
            first_day = next(d for d in sorted({a["day"] for a in arrivals}) if supply_by(d) >= cumulative)
            late = first_day - n["ship_in_days"]
        else:
            first_day, late = None, None
        results.append(OrderCoverage(
            order_id=n["order_id"], customer=n["customer"], units_needed=n["units_needed"],
            ship_in_days=n["ship_in_days"], late_penalty=n["late_penalty"],
            covered=units_short == 0, units_short=units_short,
            first_ship_day=first_day, days_late=late,
            units_never_covered=min(n["units_needed"], max(0, cumulative - total_supply)),
        ))
    return results


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

def create_server() -> MCPServer:
    mcp = MCPServer(
        "supply",
        instructions=("Supply data for one company's parts and customer orders. Days are counted from today (day 0). "
                      "Use get_part and get_orders_for_part for facts, and check_coverage to find which "
                      "orders a part's arrivals cover. Do not work out coverage yourself."),
        log_level="WARNING",
    )

    @mcp.tool(annotations=READ_ONLY, description=(
        "Return a part's description, supplier, units on hand, scheduled shipments (PO number, "
        "quantity, and arrival in days from today), and the products that use it, with parts "
        "per unit. part_id looks like MC-500."))
    def get_part(part_id: str) -> PartInfo:
        row = find_part(part_id)
        pid = row["part_id"]
        inbound = read_table("inbound")
        return PartInfo(
            part_id=pid, description=row["description"], supplier=row["supplier"],
            on_hand=to_int(row["on_hand"], "on_hand", "parts.csv"),
            scheduled_shipments=[
                ScheduledShipment(po_number=r["po_number"], supplier=r["supplier"],
                                  qty=to_int(r["quantity"], "quantity", "inbound.csv"),
                                  arrives_in_days=to_int(r["arrives_in_days"], "arrives_in_days", "inbound.csv"))
                for r in inbound if r["part_id"].upper() == pid.upper()],
            products_using_part=products_for_part(pid),
        )

    @mcp.tool(annotations=READ_ONLY, description=(
        "Return the open customer orders that need a part, in ship-day order. For each: order id, "
        "customer, product, units ordered, units of the part needed (units ordered times parts per unit), "
        "ship day (days from today), and whether a late penalty applies."))
    def get_orders_for_part(part_id: str) -> OrdersForPart:
        pid = find_part(part_id)["part_id"]
        needs = orders_needing(pid)
        return OrdersForPart(part_id=pid, orders=needs, total_units_needed=sum(n["units_needed"] for n in needs))

    @mcp.tool(annotations=READ_ONLY, description=(
        "Check which open orders a part covers if it arrives on a NEW schedule. `arrivals` is a "
        "list of {qty, day} (day = days from today) and REPLACES the part's scheduled shipments; "
        "pass an empty list if nothing more will arrive. Units on hand are included. Orders are "
        "filled complete in ship-day order, so a short order holds up the orders after it. For each "
        "order it returns covered, or units short at the ship day and the first day it can ship "
        "complete (null if the arrivals never cover it). To compare options, call it once per option."))
    def check_coverage(part_id: str, arrivals: list[Arrival]) -> CoverageResult:
        row = find_part(part_id)
        pid = row["part_id"]
        on_hand = to_int(row["on_hand"], "on_hand", "parts.csv")
        schedule = validate_arrivals(arrivals)
        needs = orders_needing(pid)
        orders = compute_coverage(on_hand, needs, schedule)
        return CoverageResult(
            part_id=pid, on_hand=on_hand, arrivals_used=schedule,
            total_supply=on_hand + sum(a["qty"] for a in schedule),
            total_units_needed=sum(n["units_needed"] for n in needs),
            orders=orders, orders_at_risk=[o["order_id"] for o in orders if not o["covered"]],
        )

    return mcp


def main() -> None:
    global DATA_DIR
    parser = argparse.ArgumentParser(description="Supply MCP server (stdio).")
    parser.add_argument("--org", metavar="FOLDER", default=None,
                        help="company folder: a path, or a folder name under week-05 (default: brookfield-bikes)")
    args = parser.parse_args()
    try:
        DATA_DIR = company.resolve_org(args.org)
    except ValueError as e:
        parser.error(str(e))
    log(f"Data folder: {DATA_DIR}")
    create_server().run("stdio")


if __name__ == "__main__":
    main()
