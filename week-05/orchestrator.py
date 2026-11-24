"""Let Claude decide which specialists to use for one supplier email.

An agent (specialists.MODEL) gets the system prompt in prompts/orchestrator.txt and four tools:

  run_supply_analyst       runs the analyst on the email
  draft_supplier_reply     drafts, reviews and saves a reply to the supplier (needs the analyst's brief)
  draft_customer_notice    drafts, reviews and saves a notice for ONE order at risk (by order id)
  finish                   ends the job with a summary for a person and whether a person must decide

It stops after 10 tool calls. Every choice it makes is printed, then the same summary as pipeline.py.

Run (from the repository root, with the repository's .venv):
    .venv\\Scripts\\python.exe week-05\\orchestrator.py --email <email> [--org copperline-coffee] [--save run.txt]
"""

from __future__ import annotations

import json
from pathlib import Path

import specialists as sp
from pipeline import parse_args, print_summary, run_and_save

MAX_TOOL_CALLS = 10

TOOLS = [
    {"name": "run_supply_analyst",
     "description": ("Work out how the supplier email affects the company's customer orders. Returns the analyst's "
                     "brief (orders at risk, options, decisions for a person, supplier questions). Use it whenever "
                     "the email might change how much arrives or when."),
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "draft_supplier_reply",
     "description": ("Draft a reply to the supplier, have it reviewed, and save it for a person. Needs the analyst's "
                     "brief, so run_supply_analyst must have been called first. Returns where it was saved and "
                     "whether a person must check it."),
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "draft_customer_notice",
     "description": ("Draft a notice to the customer of ONE order at risk, have it reviewed, and save it for a "
                     "person. Needs the analyst's brief. Call it once per order."),
     "input_schema": {"type": "object",
                      "properties": {"order_id": {"type": "string", "description": "An order id such as O-1043"}},
                      "required": ["order_id"]}},
    {"name": "finish",
     "description": "End the job. Give a short summary for the company's purchasing manager.",
     "input_schema": {"type": "object",
                      "properties": {"summary": {"type": "string"},
                                     "person_must_decide": {"type": "boolean",
                                                            "description": "True if a person must make a decision"}},
                      "required": ["summary", "person_must_decide"]}},
]


class Job:
    """What the specialists have produced so far for the one email being handled."""

    def __init__(self, email: str):
        self.email = email
        self.brief: dict | None = None
        self.results: list[dict] = []
        self.drafted_orders: set[str] = set()
        self.supplier_drafted = False
        self.finish: dict | None = None

    def call(self, name: str, args: dict) -> str:
        """Run one tool. Returns the text the orchestrator sees; raises ValueError for a bad request."""
        if name == "run_supply_analyst":
            self.brief = sp.run_analyst(self.email)
            return json.dumps(self.brief)
        if name == "finish":
            self.finish = {"summary": str(args.get("summary", "")),
                           "person_must_decide": bool(args.get("person_must_decide"))}
            return "Done."
        if self.brief is None:
            raise ValueError("Run run_supply_analyst first; the drafts are written from its brief.")
        if name == "draft_supplier_reply":
            if self.supplier_drafted:
                raise ValueError("The supplier reply was already drafted.")
            result = sp.supplier_reply_with_review(self.email, self.brief)
            self.supplier_drafted = True
        elif name == "draft_customer_notice":
            order_id = str(args.get("order_id", "")).strip()
            orders = {o.get("order_id"): o for o in self.brief.get("orders_at_risk") or []}
            if order_id not in orders:
                raise ValueError(f"{order_id!r} is not an order at risk. Orders at risk: {', '.join(orders) or 'none'}.")
            if order_id in self.drafted_orders:
                raise ValueError(f"The notice for {order_id} was already drafted.")
            result = sp.customer_notice_with_review(orders[order_id])
            self.drafted_orders.add(order_id)
        else:
            raise ValueError(f"Unknown tool {name!r}.")
        self.results.append(result)
        return json.dumps({"saved_to": result.get("file"), "reviewer": result.get("review", {}).get("verdict"),
                           "needs_a_person": result["needs_a_person"], "reasons": result["reasons"],
                           **({"note": result["draft"].strip()} if not result.get("file") else {})})


def run(email_path: Path) -> None:
    email = email_path.read_text(encoding="utf-8")
    sp.reset_usage()
    sp.print_company()
    job = Job(email)
    messages: list[dict] = [{"role": "user", "content": f"Supplier email to handle:\n\n{email}"}]
    calls = 0
    sp.handoff("coordinator", "orchestrator", "supplier email", email)

    while job.finish is None:
        response = sp.client().messages.create(
            model=sp.MODEL, max_tokens=sp.MAX_TOKENS, system=sp.read_prompt("orchestrator"),
            tools=TOOLS, messages=messages)
        sp.record_usage("orchestrator", response)
        sp._check_complete("orchestrator", response)
        messages.append({"role": "assistant", "content": response.content})
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\n[orchestrator says] {block.text.strip()}", flush=True)
        uses = [b for b in response.content if b.type == "tool_use"]
        if not uses:
            print("\n[orchestrator] stopped without calling finish.", flush=True)
            break
        results = []
        for use in uses:
            if calls >= MAX_TOOL_CALLS:
                results.append({"type": "tool_result", "tool_use_id": use.id, "is_error": True,
                                "content": "Tool-call limit reached."})
                continue
            calls += 1
            print(f"\n##### CHOICE {calls}/{MAX_TOOL_CALLS}: {use.name}({json.dumps(use.input)}) #####", flush=True)
            try:
                text, is_error = job.call(use.name, use.input), False
            except ValueError as e:                  # a bad request: tell the orchestrator and let it correct itself
                text, is_error = str(e), True
                print(f"[rejected] {text}", flush=True)
            except Exception as e:                   # a specialist failed: report it, let the orchestrator carry on
                text, is_error = f"{use.name} failed: {e.__class__.__name__}: {e}", True
                print(f"[failed] {text}", flush=True)
            results.append({"type": "tool_result", "tool_use_id": use.id, "content": text, "is_error": is_error})
        messages.append({"role": "user", "content": results})
        if job.finish is not None:
            break
        if calls >= MAX_TOOL_CALLS:
            print(f"\n[orchestrator] stopped at the {MAX_TOOL_CALLS}-tool-call limit without calling finish.", flush=True)
            break

    if job.finish:
        intro = [f"Orchestrator's summary: {job.finish['summary']}",
                 f"A person must make a decision: {'YES' if job.finish['person_must_decide'] else 'no'}"]
    else:
        intro = ["The orchestrator did not call finish, so a person should check this job."]
    print_summary(job.results, (job.brief or {}).get("decisions_for_a_person") or [], intro)


def main() -> None:
    args = parse_args("Let Claude choose which of a company's specialists to use for one email.")
    run_and_save(lambda: run(args.email), args.save)


if __name__ == "__main__":
    main()
