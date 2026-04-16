"""Fetch Google Scholar stats via SerpAPI and write _data/scholar.yml.

Uses SerpAPI's google_scholar_author engine — the numbers match what visitors
see on scholar.google.com. Failures leave the existing data file untouched so
the site keeps showing the last known values.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCHOLAR_ID = os.environ.get("SCHOLAR_ID")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
OUTPUT = Path("_data/scholar.yml")
API = "https://serpapi.com/search.json"


def fetch() -> dict:
    params = urllib.parse.urlencode(
        {
            "engine": "google_scholar_author",
            "author_id": SCHOLAR_ID,
            "api_key": SERPAPI_KEY,
            "hl": "en",
        }
    )
    req = urllib.request.Request(f"{API}?{params}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract(payload: dict) -> dict:
    # cited_by.table is a list: [{citations: {all, since_YYYY}}, {h_index: ...}, {i10_index: ...}]
    table = payload.get("cited_by", {}).get("table", [])
    flat = {}
    for row in table:
        flat.update(row)

    def pick(key: str, scope: str) -> int | None:
        cell = flat.get(key, {})
        if scope == "all":
            return cell.get("all")
        # "since" key varies by year, e.g. "since_2019"
        for k, v in cell.items():
            if k.startswith("since_"):
                return v
        return None

    return {
        "citations": pick("citations", "all"),
        "citations_5y": pick("citations", "since"),
        "h_index": pick("h_index", "all"),
        "h_index_5y": pick("h_index", "since"),
        "i10_index": pick("i10_index", "all"),
        "i10_index_5y": pick("i10_index", "since"),
    }


def main() -> int:
    if not SCHOLAR_ID:
        print("SCHOLAR_ID env var is required", file=sys.stderr)
        return 1
    if not SERPAPI_KEY:
        print("SERPAPI_KEY env var is required", file=sys.stderr)
        return 1

    try:
        payload = fetch()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"SerpAPI HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"SerpAPI request failed: {exc}", file=sys.stderr)
        return 1

    if payload.get("error"):
        print(f"SerpAPI error: {payload['error']}", file=sys.stderr)
        return 1

    stats = extract(payload)
    if not stats["citations"] and not stats["h_index"]:
        print(f"No stats in response: {payload.get('cited_by')}", file=sys.stderr)
        return 1

    data = {**stats, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d")}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    print(f"Wrote {OUTPUT}: {data}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
