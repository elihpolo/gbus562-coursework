"""Run one supplier email through the specialists, in a fixed order:

  1. the supply analyst
  2. a customer notice for each order at risk (skipped if there are none)
  3. a reply to the supplier

Every draft goes through the review step (reviewer, at most 2 revisions, name checks, saved to
week-05/drafts/<company folder name>), and the final draft is printed once after it.
At the end it prints a summary: drafts saved, drafts marked for a person, decisions for a person, total tokens.

Run (from the repository root, with the repository's .venv):
    .venv\\Scripts\\python.exe week-05\\pipeline.py --email week-05\\brookfield-bikes\\supplier-emails\\01-northgate-controller-delay.eml
    .venv\\Scripts\\python.exe week-05\\pipeline.py --email <email> --save run.txt     (also writes everything printed to run.txt, UTF-8)
    .venv\\Scripts\\python.exe week-05\\pipeline.py --org copperline-coffee --email <email>     (another company's folder)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import specialists as sp


class Tee:
    """Send everything printed to the console and to a file."""

    def __init__(self, console, file):
        self.console, self.file = console, file

    def write(self, text: str) -> int:
        self.console.write(text)
        self.file.write(text)
        return len(text)

    def flush(self) -> None:
        self.console.flush()
        self.file.flush()


def run(email_path: Path) -> None:
    email = email_path.read_text(encoding="utf-8")
    sp.reset_usage()
    sp.print_company()

    print("\n##### STEP 1: supply analyst #####")
    brief = sp.run_analyst(email)

    at_risk = brief.get("orders_at_risk") or []
    results: list[dict] = []
    print(f"\n##### STEP 2: customer notices ({len(at_risk)} order(s) at risk) #####")
    if not at_risk:
        print("No orders at risk; skipping customer notices.")
    for order in at_risk:
        results.append(sp.customer_notice_with_review(order))

    print("\n##### STEP 3: supplier reply #####")
    results.append(sp.supplier_reply_with_review(email, brief))

    print_summary(results, brief.get("decisions_for_a_person") or [])


def print_summary(results: list[dict], decisions: list[str], intro: list[str] = ()) -> None:
    """Drafts saved, drafts marked for a person, decisions for a person, and total tokens.
    intro lines (if any) are printed first, under the header."""
    saved = [r for r in results if r.get("file")]
    marked = [r for r in saved if r["needs_a_person"]]
    total_in = sum(u["input_tokens"] for u in sp.USAGE.values())
    total_out = sum(u["output_tokens"] for u in sp.USAGE.values())

    print("\n##### SUMMARY #####")
    for line in intro:
        print(line)
    print(f"Drafts saved: {len(saved)}")
    for r in saved:
        print(f"  {r['file']}")
    for r in results:
        if not r.get("file"):
            print(f"  (supplier reply not saved: {r['draft'].strip()})")
    print(f"Drafts marked for a person: {len(marked)}")
    for r in marked:
        print(f"  {Path(r['file']).name}: {'; '.join(r['reasons'])}")
    print(f"Decisions for a person: {len(decisions)}")
    for d in decisions:
        print(f"  - {d}")
    sp.print_usage()
    print(f"Total tokens: {total_in + total_out} (input {total_in}, output {total_out})")


def parse_args(description: str) -> argparse.Namespace:
    """Parse --email, --org and --save, and point the specialists at the chosen company folder."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--email", type=Path, required=True, help="path of one supplier email (.eml or text)")
    parser.add_argument("--org", metavar="FOLDER", default=None,
                        help="company folder: a path, or a folder name under week-05 (default: brookfield-bikes)")
    parser.add_argument("--save", type=Path, metavar="FILE", help="also write everything printed to FILE (UTF-8)")
    args = parser.parse_args()
    if not args.email.is_file():
        parser.error(f"email not found: {args.email}")
    try:
        sp.use_org(args.org)
    except ValueError as e:
        parser.error(str(e))
    return args


def main() -> None:
    args = parse_args("Run one supplier email through a company's specialists, in a fixed order.")
    run_and_save(lambda: run(args.email), args.save)


def run_and_save(job, save: Path | None) -> None:
    """Run job(); with save, also write everything it prints to that file (UTF-8)."""
    sys.stdout.reconfigure(encoding="utf-8")
    if not save:
        job()
        return
    save.parent.mkdir(parents=True, exist_ok=True)
    with save.open("w", encoding="utf-8", newline="") as f:
        console = sys.stdout
        sys.stdout = Tee(console, f)
        try:
            job()
        finally:
            sys.stdout = console


if __name__ == "__main__":
    main()
