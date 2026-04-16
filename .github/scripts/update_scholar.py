"""Fetch Google Scholar stats for the configured author and write _data/scholar.yml.

Runs in CI. Failures leave the existing data file untouched so the site keeps
showing the last known values instead of blanking out.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from scholarly import scholarly

SCHOLAR_ID = os.environ.get("SCHOLAR_ID")
OUTPUT = Path("_data/scholar.yml")


def main() -> int:
    if not SCHOLAR_ID:
        print("SCHOLAR_ID env var is required", file=sys.stderr)
        return 1

    try:
        author = scholarly.search_author_id(SCHOLAR_ID)
        author = scholarly.fill(author, sections=["indices", "counts"])
    except Exception as exc:
        print(f"Failed to fetch Scholar data: {exc}", file=sys.stderr)
        return 1

    data = {
        "citations": int(author.get("citedby", 0)) or None,
        "citations_5y": int(author.get("citedby5y", 0)) or None,
        "h_index": int(author.get("hindex", 0)) or None,
        "h_index_5y": int(author.get("hindex5y", 0)) or None,
        "i10_index": int(author.get("i10index", 0)) or None,
        "i10_index_5y": int(author.get("i10index5y", 0)) or None,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    if not data["citations"] and not data["h_index"]:
        print("Fetched empty stats; refusing to overwrite.", file=sys.stderr)
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    print(f"Wrote {OUTPUT}: {data}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
