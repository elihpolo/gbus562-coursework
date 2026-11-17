"""Organizations the HR MCP server and agent can work for.

--org accepts any organization folder that directly contains:
    hr-docs/            policy documents (HTML, PDF, Markdown, or text)
    employees.csv       one row per employee; the email and leave-balance columns
                        are found from the headers (see hr_mcp_server.py)
    system_prompt.txt   the agent's system prompt
(sample-emails/ is optional.)

The value can be:
    - a short name from SHORT_NAMES below, e.g. "hartwell" (the default) or "ridgeline"
    - the name of a folder in week-04, e.g. "ridgeline-hotels" or "acme-hr"
    - a path to a folder anywhere, e.g. "C:\\data\\acme-hr" or "week-04\\acme-hr"

Each organization gets its own Chroma database in week-04/chroma_db/<key>/ (git-ignored),
where <key> is the short name or, for other folders, the folder name.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

WEEK_DIR = Path(__file__).resolve().parent

# Short names for the organizations that come with the assignment:
# short name -> (folder in week-04, display name)
SHORT_NAMES: dict[str, tuple[str, str]] = {
    "hartwell": ("hartwell-hr", "Hartwell Foods"),
    "ridgeline": ("ridgeline-hotels", "Ridgeline Hotels"),
}
DEFAULT_ORG = "hartwell"
REQUIRED = ("hr-docs", "employees.csv", "system_prompt.txt")

ORG_HELP = (f"organization: a short name ({', '.join(SHORT_NAMES)}), the name of a folder in week-04, "
            f"or a path to a folder that contains {', '.join(REQUIRED)} (default: {DEFAULT_ORG})")


@dataclass(frozen=True)
class Org:
    key: str      # names this organization's Chroma database folder
    name: str     # display name, e.g. "Ridgeline Hotels"
    folder: Path

    @property
    def docs_dir(self) -> Path:
        return self.folder / "hr-docs"

    @property
    def employees_csv(self) -> Path:
        return self.folder / "employees.csv"

    @property
    def sample_emails_dir(self) -> Path:
        return self.folder / "sample-emails"

    @property
    def system_prompt_file(self) -> Path:
        return self.folder / "system_prompt.txt"

    @property
    def arg(self) -> str:
        """A value that --org resolves back to this organization (short name or full path)."""
        return self.key if self.key in SHORT_NAMES else str(self.folder)

    @property
    def db_root(self) -> Path:
        """Each organization gets its own Chroma database (git-ignored)."""
        return WEEK_DIR / "chroma_db" / self.key


def _display_name(folder: Path) -> str:
    """"acme-hr" -> "Acme HR", "blue_river_clinic" -> "Blue River Clinic"."""
    words = re.split(r"[-_\s]+", folder.name.strip())
    return " ".join(w.upper() if w.lower() == "hr" else w.capitalize() for w in words if w) or folder.name


def _key_for(folder: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", folder.name.lower()).strip("-") or "org"


def get_org(value: str) -> Org:
    """Resolve --org to an organization folder and check it has the files the tools need."""
    value = (value or "").strip()
    if not value:
        sys.exit("ERROR: --org needs a value")

    if value.lower() in SHORT_NAMES:
        folder = WEEK_DIR / SHORT_NAMES[value.lower()][0]
    else:
        candidate = Path(value).expanduser()
        if candidate.is_dir():                               # a path (absolute or from the current folder)
            folder = candidate
        elif (WEEK_DIR / value).is_dir():                    # a folder name in week-04
            folder = WEEK_DIR / value
        else:
            sys.exit(f"ERROR: organization {value!r} not found. Use a short name "
                     f"({', '.join(SHORT_NAMES)}), a folder in {WEEK_DIR}, or a path to a folder.")
    folder = folder.resolve()

    # A built-in organization keeps its short name (and database) however it was named.
    for key, (folder_name, name) in SHORT_NAMES.items():
        if folder == (WEEK_DIR / folder_name).resolve():
            org = Org(key=key, name=name, folder=folder)
            break
    else:
        org = Org(key=_key_for(folder), name=_display_name(folder), folder=folder)

    missing = [n for n in REQUIRED if not (folder / n).exists()]
    if missing:
        sys.exit(f"ERROR: {folder} is not an organization folder; it is missing: {', '.join(missing)}")
    if not org.docs_dir.is_dir():
        sys.exit(f"ERROR: {org.docs_dir} must be a folder of policy documents")
    return org
