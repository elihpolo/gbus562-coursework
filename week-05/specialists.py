"""Four specialists that a company's coordinators share.

  run_analyst(email)                       agent over the supply MCP server tools; max 10 tool calls; returns a brief (dict)
  write_supplier_reply(email, brief)       one model call; customer names are removed from its inputs first
  write_customer_notice(order)             one model call; sees only that one order's facts
  review(draft, facts, recipient)          one model call; returns {"verdict": "APPROVE"|"REVISE", "reasons": ...}

  supplier_reply_with_review(email, brief)  writer -> reviewer, at most 2 revisions, code checks, draft saved
  customer_notice_with_review(order)        same, for one customer order

Every system prompt is re-read from the company folder's prompts/ on every call. Every handoff and every
model call's token use is printed; print_usage() prints the per-specialist totals.

The API key is read from API-Key.txt in the folder above the repository. It is held in memory only: it is
never printed, logged, or written to a file.

Company: everything company-specific (CSV data, system prompts, supplier emails) comes from a company folder,
week-05/brookfield-bikes by default. Call use_org("copperline-coffee") (a folder name under week-05, or a path) to
switch. Drafts are saved under week-05/drafts/<company folder name>. Column names in the CSV files are worked
out from their header rows (company.py), not assumed.

Run the whole flow on one supplier email (from the repository root, with the repository's .venv):
    .venv\\Scripts\\python.exe week-05\\specialists.py [--org copperline-coffee] [path-to-email.eml]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import anthropic
import company
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "claude-sonnet-5"
MAX_TOOL_CALLS = 10
MAX_REVISIONS = 2
MAX_TOKENS = 8000          # per model call; the model's thinking counts toward this

WEEK_DIR = Path(__file__).resolve().parent
DATA_DIR = company.DEFAULT_ORG                     # the company folder (see use_org)
PROMPTS_DIR = DATA_DIR / "prompts"
DRAFTS_DIR = WEEK_DIR / "drafts" / DATA_DIR.name
SERVER_PATH = WEEK_DIR / "supply_mcp_server.py"
KEY_PATH = WEEK_DIR.parent.parent / "API-Key.txt"      # the folder above the repository

NO_REPLY = "NO REPLY NEEDED"


# ---------------------------------------------------------------------------
# Printing: handoffs and tokens
# ---------------------------------------------------------------------------

USAGE: dict[str, dict[str, int]] = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0})


def handoff(source: str, target: str, what: str, payload: Any) -> None:
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2, ensure_ascii=False)
    print(f"\n=== HANDOFF  {source} -> {target}  |  {what} ===\n{body}", flush=True)


def record_usage(specialist: str, response: Any) -> None:
    u = USAGE[specialist]
    u["calls"] += 1
    u["input_tokens"] += response.usage.input_tokens
    u["output_tokens"] += response.usage.output_tokens
    print(f"[tokens] {specialist}: in={response.usage.input_tokens} out={response.usage.output_tokens}", flush=True)


def print_usage() -> None:
    print("\n=== TOKENS BY SPECIALIST ===")
    print(f"{'specialist':<18}{'calls':>6}{'input':>10}{'output':>10}{'total':>10}")
    totals = [0, 0, 0]
    for name, u in USAGE.items():
        print(f"{name:<18}{u['calls']:>6}{u['input_tokens']:>10}{u['output_tokens']:>10}"
              f"{u['input_tokens'] + u['output_tokens']:>10}")
        totals = [totals[0] + u["calls"], totals[1] + u["input_tokens"], totals[2] + u["output_tokens"]]
    print(f"{'all':<18}{totals[0]:>6}{totals[1]:>10}{totals[2]:>10}{totals[1] + totals[2]:>10}", flush=True)


def reset_usage() -> None:
    USAGE.clear()


# ---------------------------------------------------------------------------
# Inputs: API key, prompts, reference data
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None
_async_client: anthropic.AsyncAnthropic | None = None


def _api_key() -> str:
    try:
        text = KEY_PATH.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"Could not read the API key file at {KEY_PATH} ({e.__class__.__name__}).") from None
    # The file may hold a bare key or a curl example; look for the key itself, then for the header value.
    for pattern in (r"sk-ant-[A-Za-z0-9_\-]+", r"x-api-key:\s*([^\s\"'\\]+)"):
        m = re.search(pattern, text)
        if m:
            return m.group(1) if m.groups() else m.group(0)
    if len(text.split()) == 1:
        return text.strip()
    raise RuntimeError(f"No API key found in {KEY_PATH}.")


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=_api_key())
    return _client


def async_client() -> anthropic.AsyncAnthropic:
    global _async_client
    if _async_client is None:
        _async_client = anthropic.AsyncAnthropic(api_key=_api_key())
    return _async_client


def use_org(value: str | Path | None) -> Path:
    """Point every specialist at a company folder (a path, or a folder name under week-05; None = Brookfield).
    Raises ValueError if the folder isn't laid out like brookfield-bikes."""
    global DATA_DIR, PROMPTS_DIR, DRAFTS_DIR
    DATA_DIR = company.resolve_org(value)
    PROMPTS_DIR = DATA_DIR / "prompts"
    DRAFTS_DIR = WEEK_DIR / "drafts" / DATA_DIR.name
    return DATA_DIR


def print_company() -> None:
    """Print which company folder is in use and which CSV column holds which field (worked out from the headers)."""
    columns = company.describe_columns(DATA_DIR)
    handoff("coordinator", "all specialists", "company folder and CSV columns found from the header rows",
            {"company_folder": str(DATA_DIR), "drafts_folder": str(DRAFTS_DIR), "columns": columns})


def read_prompt(name: str) -> str:
    """Read the system prompt fresh from disk, so edits apply on the next run."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def read_table(table: str) -> list[dict[str, str]]:
    """One of the company's CSV files, keyed by canonical field names (see company.py)."""
    return company.read_table(DATA_DIR, table)


def customer_names() -> list[str]:
    return sorted({r["customer"] for r in read_table("orders") if r["customer"]})


def supplier_names() -> list[str]:
    """Each supplier's company name, its distinctive first word (e.g. "Northgate"), and its contact's name."""
    names: set[str] = set()
    for r in read_table("suppliers"):
        names.update([r["supplier"], r["supplier"].split()[0] if r["supplier"] else "", r["contact_name"]])
    return sorted(n for n in names if n)


def _norm(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + " "


def find_names(text: str, names: list[str]) -> list[str]:
    """Names that appear in the text, ignoring case and punctuation, whole words only."""
    haystack = _norm(text)
    return [n for n in names if _norm(n) in haystack]


def scrub_customers(obj: Any) -> Any:
    """Copy of obj with every customer name replaced by "a customer" and every "customer" field dropped."""
    names = sorted(customer_names(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(n) for n in names), re.IGNORECASE) if names else None

    def walk(o: Any) -> Any:
        if isinstance(o, str):
            return pattern.sub("a customer", o) if pattern else o
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items() if k != "customer"}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return o

    return walk(obj)


# ---------------------------------------------------------------------------
# One model call (used by the writers and the reviewer)
# ---------------------------------------------------------------------------

def _check_complete(specialist: str, response: Any) -> None:
    """A cut-off answer is an error, never a result (thinking tokens count toward max_tokens)."""
    if response.stop_reason == "max_tokens":
        raise RuntimeError(f"{specialist}'s answer was cut off at max_tokens={MAX_TOKENS}. Raise MAX_TOKENS.")


def _one_call(specialist: str, prompt_name: str, user: str) -> str:
    response = client().messages.create(
        model=MODEL, max_tokens=MAX_TOKENS, system=read_prompt(prompt_name),
        messages=[{"role": "user", "content": user}],
    )
    record_usage(specialist, response)
    _check_complete(specialist, response)
    return "".join(b.text for b in response.content if b.type == "text").strip()


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"The analyst's answer has no JSON object: {text[:300]!r}")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------------------
# Specialist 1: analyst (agent over the supply MCP server)
# ---------------------------------------------------------------------------

BRIEF_FIELDS = ("part_id", "what_changed", "orders_at_risk", "options", "decisions_for_a_person", "supplier_questions")


def _short(text: str, limit: int = 600) -> str:
    return text if len(text) <= limit else text[:limit] + f"... [{len(text) - limit} more characters]"


async def _run_analyst(email: str) -> dict:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH), "--org", str(DATA_DIR)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
                     for t in (await session.list_tools()).tools]
            messages: list[dict] = [{"role": "user", "content":
                                     f"Supplier email:\n\n{email}\n\nReply with the brief as JSON only."}]
            calls = 0
            while True:
                out_of_calls = calls >= MAX_TOOL_CALLS
                extra = {"tool_choice": {"type": "none"}} if out_of_calls else {}
                response = await async_client().messages.create(
                    model=MODEL, max_tokens=MAX_TOKENS, system=read_prompt("analyst"),
                    tools=tools, messages=messages, **extra)
                record_usage("analyst", response)
                _check_complete("analyst", response)
                messages.append({"role": "assistant", "content": response.content})
                uses = [b for b in response.content if b.type == "tool_use"]
                if not uses or out_of_calls:
                    break
                results = []
                for use in uses:
                    if calls >= MAX_TOOL_CALLS:        # the budget ran out in the middle of a batch
                        results.append({"type": "tool_result", "tool_use_id": use.id, "is_error": True,
                                        "content": "Tool-call limit reached. Give your brief now."})
                        continue
                    calls += 1
                    handoff("analyst", "supply tool", f"call {calls}/{MAX_TOOL_CALLS}: {use.name}", use.input)
                    result = await session.call_tool(use.name, use.input)
                    text = "\n".join(c.text for c in result.content if getattr(c, "type", "") == "text")
                    handoff("supply tool", "analyst", f"result of call {calls}" + (" (error)" if result.is_error else ""),
                            _short(text))
                    results.append({"type": "tool_result", "tool_use_id": use.id, "content": text,
                                    "is_error": bool(result.is_error)})
                messages.append({"role": "user", "content": results})
            if calls >= MAX_TOOL_CALLS:
                print(f"[analyst] stopped at the {MAX_TOOL_CALLS}-tool-call limit", flush=True)
            text = "".join(b.text for b in response.content if b.type == "text")
    return _extract_json(text)


def run_analyst(email: str) -> dict:
    """Work out how a supplier email affects customer orders. Returns the brief as a dict.
    Uses asyncio.run, so call it from ordinary (non-async) code."""
    handoff("coordinator", "analyst", "supplier email", email)
    brief = asyncio.run(_run_analyst(email))
    missing = [f for f in BRIEF_FIELDS if f not in brief]
    if missing:
        raise ValueError(f"The analyst's brief is missing: {', '.join(missing)}. Brief: {brief}")
    handoff("analyst", "coordinator", "brief (full)", brief)
    return brief


# ---------------------------------------------------------------------------
# Specialists 2-4: supplier writer, customer writer, reviewer
# ---------------------------------------------------------------------------

def _revision_note(previous_draft: str | None, reviewer_notes: str | None) -> str:
    if not previous_draft:
        return ""
    return (f"\n\nYour previous draft:\n{previous_draft}\n\nThe reviewer asked for changes:\n{reviewer_notes}\n\n"
            "Write the complete corrected draft.")


def write_supplier_reply(email: str, brief: dict, previous_draft: str | None = None,
                         reviewer_notes: str | None = None) -> str:
    """One model call. Customer names are removed from the email and the brief before the model sees them."""
    safe_email, safe_brief = scrub_customers(email), scrub_customers(brief)
    user = (f"Supplier's email:\n\n{safe_email}\n\nAnalyst's brief (JSON):\n{json.dumps(safe_brief, indent=2)}"
            + _revision_note(previous_draft, reviewer_notes))
    handoff("coordinator", "supplier_writer", "inputs with customer names removed", user)
    draft = _one_call("supplier_writer", "supplier-writer", user)
    handoff("supplier_writer", "coordinator", "draft", draft)
    return draft


def order_facts(order: dict) -> dict:
    """The facts the customer writer may see about ONE order. No penalty flag, no contact details, no other order."""
    row = next((r for r in read_table("orders") if r["order_id"] == order.get("order_id")), {})
    ship, ready = order.get("ship_day"), order.get("ready_day")
    facts = {
        "order_id": order.get("order_id"),
        "customer": order.get("customer") or row.get("customer"),
        "product": order.get("product") or order.get("model") or row.get("product"),
        "units_ordered": order.get("units_ordered") or order.get("bikes") or order.get("qty") or row.get("quantity"),
        "days_later_than_planned": (ready - ship) if isinstance(ship, int) and isinstance(ready, int) else None,
    }
    if facts["days_later_than_planned"] is None:
        facts["note"] = "No new ship date is known yet."
    return facts


def write_customer_notice(order: dict, previous_draft: str | None = None,
                          reviewer_notes: str | None = None) -> str:
    """One model call, given only that one order's facts."""
    user = f"Order facts:\n{json.dumps(order_facts(order), indent=2)}" + _revision_note(previous_draft, reviewer_notes)
    handoff("coordinator", "customer_writer", f"facts for order {order.get('order_id')}", user)
    draft = _one_call("customer_writer", "customer-writer", user)
    handoff("customer_writer", "coordinator", "draft", draft)
    return draft


def review(draft: str, facts: Any, recipient: str) -> dict:
    """One model call. recipient is "supplier" or "customer". Returns {"verdict": "APPROVE"|"REVISE", "reasons": str}."""
    if recipient not in ("supplier", "customer"):
        raise ValueError("recipient must be 'supplier' or 'customer'")
    facts_text = facts if isinstance(facts, str) else json.dumps(facts, indent=2, ensure_ascii=False)
    user = f"This draft goes to a {recipient}.\n\nFacts the draft was written from:\n{facts_text}\n\nDraft:\n{draft}"
    handoff("coordinator", "reviewer", f"draft to a {recipient}", user)
    text = _one_call("reviewer", "reviewer", user)
    lines = text.splitlines()
    first = lines[0].strip().upper().strip("*# ") if lines else ""
    raw = text
    if first.startswith("APPROVE") and "REVISE" not in text.upper():
        verdict = "APPROVE"
    elif first.startswith("REVISE"):
        verdict = "REVISE"
    else:                                   # an unclear or contradictory answer is never treated as approval
        verdict, text = "REVISE", f"(The reviewer's answer was unclear; treated as REVISE.)\n{text}"
    reasons = "\n".join(text.splitlines()[1:]).strip()
    result = {"verdict": verdict, "reasons": reasons}
    handoff("reviewer", "coordinator", f"verdict (raw answer: {raw[:2000]!r})" if verdict != "APPROVE" or reasons
            else "verdict", result)
    return result


# ---------------------------------------------------------------------------
# Review step: writer -> reviewer (max 2 revisions) -> code checks -> save
# ---------------------------------------------------------------------------

def _review_loop(write: Callable[[str | None, str | None], str], facts: Any, recipient: str) -> tuple[str, dict, int]:
    draft = write(None, None)
    if draft.strip().upper().startswith(NO_REPLY):
        return draft, {"verdict": "APPROVE", "reasons": "No reply needed."}, 0
    revisions = 0
    while True:
        verdict = review(draft, facts, recipient)
        if verdict["verdict"] == "APPROVE" or revisions >= MAX_REVISIONS:
            return draft, verdict, revisions
        revisions += 1
        print(f"[review] REVISE -> revision {revisions} of {MAX_REVISIONS}", flush=True)
        draft = write(draft, verdict["reasons"])


def _save(filename: str, recipient: str, draft: str, verdict: dict, revisions: int, reasons: list[str]) -> Path:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    path = DRAFTS_DIR / filename
    status = "NEEDS A PERSON: " + "; ".join(reasons) if reasons else "No flags. A person still checks it before it is sent."
    header = (f"To: {recipient}\nSaved: {datetime.now():%Y-%m-%d %H:%M}\nStatus: {status}\n"
              f"Reviewer: {verdict['verdict']} after {revisions} revision(s)\n" + "-" * 60 + "\n")
    path.write_text(header + draft + "\n", encoding="utf-8")
    return path


def print_final_draft(recipient: str, order_id: str | None, draft: str, marked: bool) -> None:
    """The final draft, printed once after its review step."""
    title = "FINAL DRAFT TO SUPPLIER" if recipient == "supplier" else f"FINAL DRAFT TO CUSTOMER {order_id}"
    print(f"\n{title}\n{draft.strip()}\nMarked for a person: {'yes' if marked else 'no'}", flush=True)


def _finish(filename: str, recipient: str, draft: str, verdict: dict, revisions: int,
            leaked: list[str], extra_reasons: list[str], order_id: str | None = None) -> dict:
    reasons = list(extra_reasons)
    if leaked:
        reasons.insert(0, ("customer" if recipient == "supplier" else "supplier")
                       + f" name in the draft: {', '.join(leaked)}")
    if verdict["verdict"] != "APPROVE":
        reasons.append(f"the reviewer still said REVISE after {revisions} revision(s)")
    path = _save(filename, recipient, draft, verdict, revisions, reasons)
    print_final_draft(recipient, order_id, draft, bool(reasons))
    result = {"file": str(path), "recipient": recipient, "draft": draft, "review": verdict,
              "revisions": revisions, "name_check_hits": leaked, "needs_a_person": bool(reasons), "reasons": reasons}
    handoff("coordinator", "person", f"saved {path.name}", {k: v for k, v in result.items() if k != "draft"})
    return result


def supplier_reply_with_review(email: str, brief: dict) -> dict:
    """Write, review (at most 2 revisions), check no customer name is in the draft, save to week-05/drafts."""
    facts = {"supplier_email": scrub_customers(email), "analyst_brief": scrub_customers(brief)}
    draft, verdict, revisions = _review_loop(
        lambda prev, notes: write_supplier_reply(email, brief, prev, notes), facts, "supplier")
    if draft.strip().upper().startswith(NO_REPLY):
        print_final_draft("supplier", None, draft, False)
        result = {"file": None, "recipient": "supplier", "draft": draft, "needs_a_person": False, "reasons": []}
        handoff("coordinator", "person", "no reply needed; nothing saved", result)
        return result
    leaked = find_names(draft, customer_names())
    return _finish(f"supplier-reply-{brief.get('part_id', 'unknown')}.txt", "supplier", draft, verdict, revisions,
                   leaked, [])


def customer_notice_with_review(order: dict) -> dict:
    """Write, review (at most 2 revisions), check no supplier name is in the draft, save to week-05/drafts.
    A late penalty on the order marks the draft for a person."""
    facts = order_facts(order)
    draft, verdict, revisions = _review_loop(
        lambda prev, notes: write_customer_notice(order, prev, notes), facts, "customer")
    leaked = find_names(draft, supplier_names())
    penalty = order.get("late_penalty")
    if penalty is None:
        penalty = next((r["late_penalty"] for r in read_table("orders") if r["order_id"] == order.get("order_id")), "")
    extra = [] if str(penalty).strip().lower() == "no" else ["the order has a late penalty" if str(penalty).strip().lower()
                                                                == "yes" else "the order's late-penalty status is unknown"]
    return _finish(f"customer-notice-{order.get('order_id', 'unknown')}.txt", "customer", draft, verdict, revisions,
                   leaked, extra, order.get("order_id"))


# ---------------------------------------------------------------------------
# Demo: one supplier email through every specialist
# ---------------------------------------------------------------------------

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run one supplier email through every specialist.")
    parser.add_argument("email", nargs="?", type=Path, help="supplier email (default: the company's first sample email)")
    parser.add_argument("--org", metavar="FOLDER", help="company folder: a path, or a folder name under week-05")
    args = parser.parse_args()
    try:
        use_org(args.org)
    except ValueError as e:
        parser.error(str(e))
    email_path = args.email or sorted((DATA_DIR / "supplier-emails").glob("*.eml"))[0]
    email = email_path.read_text(encoding="utf-8")
    print_company()
    brief = run_analyst(email)
    outcomes = [supplier_reply_with_review(email, brief)]
    outcomes += [customer_notice_with_review(o) for o in brief["orders_at_risk"]]
    print_usage()
    print("\n=== DRAFTS ===")
    for o in outcomes:
        print(f"{o['file']}: " + ("NEEDS A PERSON (" + "; ".join(o["reasons"]) + ")" if o["needs_a_person"] else "no flags"))


if __name__ == "__main__":
    main()
