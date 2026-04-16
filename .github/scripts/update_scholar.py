"""Fetch Google Scholar stats for the configured author and write _data/scholar.yml.

Does a direct HTTP GET against the public profile page and parses the stats
table. No third-party scraping library, no proxies — runs in a few seconds.
Failures leave the existing data file untouched so the site keeps showing the
last known values.
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error
import yaml

SCHOLAR_ID = os.environ.get("SCHOLAR_ID")
OUTPUT = Path("_data/scholar.yml")
URL = "https://scholar.google.com/citations?user={id}&hl=en"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def fetch_html(scholar_id: str) -> str:
    req = urllib.request.Request(
        URL.format(id=scholar_id),
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_stats(html: str) -> dict:
    # The stats table has rows with <td class="gsc_rsb_std">N</td><td class="gsc_rsb_std">M</td>
    # in order: Citations (all, 5y), h-index (all, 5y), i10-index (all, 5y).
    values = [int(v) for v in re.findall(r'class="gsc_rsb_std">(\d+)</td>', html)]
    if len(values) < 6:
        raise ValueError(f"Unexpected Scholar page layout (got {len(values)} stats)")
    return {
        "citations": values[0],
        "citations_5y": values[1],
        "h_index": values[2],
        "h_index_5y": values[3],
        "i10_index": values[4],
        "i10_index_5y": values[5],
    }


def main() -> int:
    if not SCHOLAR_ID:
        print("SCHOLAR_ID env var is required", file=sys.stderr)
        return 1

    try:
        html = fetch_html(SCHOLAR_ID)
    except urllib.error.URLError as exc:
        print(f"Failed to fetch Scholar page: {exc}", file=sys.stderr)
        return 1

    if "CAPTCHA" in html or "unusual traffic" in html.lower():
        print("Scholar returned a CAPTCHA page; skipping.", file=sys.stderr)
        return 1

    try:
        stats = parse_stats(html)
    except ValueError as exc:
        print(f"Failed to parse Scholar page: {exc}", file=sys.stderr)
        return 1

    data = {
        **stats,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    print(f"Wrote {OUTPUT}: {data}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
