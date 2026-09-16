"""Fetch public-domain Bangla poems from Bengali Wikisource.

Provenance is recorded per poem, not per poet — guideline §10 item 5. Each record
keeps the page title, revision id and retrieval date, so any line in the pilot can
be traced back to the exact revision it came from.

Copyright: Rabindranath Tagore died in 1941, so the works are in the public domain
in Bangladesh and India (life + 60) and in the US. The transcription is Wikisource's.
Nothing here is redistributed; it is fetched into a local corpus for annotation.

  python corpus/fetch_wikisource.py --collection "কণিকা (রবীন্দ্রনাথ ঠাকুর)" --limit 60
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://bn.wikisource.org/w/api.php"
UA = "banglachhanda-research/0.1 (Bangla prosody corpus; contact via repo)"
PAUSE = 1.5          # be polite; this is someone else's server
MAX_RETRIES = 4

# Navigation furniture the parser renders around the poem body.
CHROME = re.compile(r"[◄►]|^​+$|^\d+$|^\(পৃ|^$")


def api(params: dict) -> dict:
    """One API call, backing off when the server asks us to slow down."""
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < MAX_RETRIES - 1:
                wait = PAUSE * (3 ** (attempt + 1))
                print(f"  .. {exc.code}, waiting {wait:.0f}s")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def poem_id(title: str) -> str:
    """A stable, readable id: collection leaf + poem title, spaces hyphenated."""
    book, _, leaf = title.partition("/")
    book = book.split(" (")[0].strip()
    slug = f"{book}-{leaf}".strip("-")
    return re.sub(r"[\s/]+", "-", slug)


def list_subpages(collection: str, limit: int) -> list[str]:
    out: list[str] = []
    cont: dict = {}
    while len(out) < limit:
        data = api({
            "action": "query",
            "generator": "allpages",
            "gapprefix": collection + "/",
            "gaplimit": min(50, limit - len(out)),
            **cont,
        })
        pages = data.get("query", {}).get("pages", {})
        out.extend(p["title"] for p in pages.values())
        if "continue" not in data:
            break
        cont = data["continue"]
        time.sleep(PAUSE)
    return sorted(out)[:limit]


def poem_lines(title: str, collection: str = "") -> tuple[list[str], int | None]:
    """Return the poem's lines plus the revision id they came from."""
    data = api({"action": "parse", "page": title, "prop": "text|revid"})
    parse = data.get("parse", {})
    raw = parse.get("text", {}).get("*", "")
    if not raw:
        return [], None

    text = re.sub(r"<style.*?</style>|<script.*?</script>|<sup.*?</sup>", "", raw, flags=re.S)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</(p|div|dd|dl|li|h\d)>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = text.replace(" ", " ")

    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and not CHROME.search(ln)]

    # The rendered page repeats the poem's own title before the body. Only look
    # for it in the opening lines: a poem may legitimately contain a line equal
    # to its own title, and cutting at that would silently drop the opening.
    leaf = title.split("/")[-1]
    positions = [i for i, ln in enumerate(lines[:10]) if ln == leaf]
    if positions:
        lines = lines[positions[-1] + 1:]

    # Drop the run-together header Wikisource emits (collection+author+title+page).
    # Matching on the title alone would delete real lines: the opening line of
    # কণিকা/অধিকার is "অধিকার বেশি কার বনের উপর", which contains its own title.
    # The header is identified by carrying the collection name as well.
    book = collection.split(" (")[0].strip()
    if book:
        lines = [
            ln for i, ln in enumerate(lines)
            if not (i < 10 and leaf in ln and book in ln)
        ]
    return lines, parse.get("revid")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection", required=True, action="append")
    ap.add_argument("--limit", type=int, default=40, help="poems per collection")
    ap.add_argument("--out", default="corpus/poems.jsonl")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    written = 0

    with out_path.open("w", encoding="utf-8") as fh:
        for collection in args.collection:
            titles = list_subpages(collection, args.limit)
            print(f"{collection}: {len(titles)} subpages")
            for title in titles:
                try:
                    lines, revid = poem_lines(title, collection)
                except Exception as exc:                    # noqa: BLE001
                    print(f"  !! {title}: {exc}")
                    continue
                time.sleep(PAUSE)
                if not lines:
                    print(f"  -- empty: {title}")
                    continue
                record = {
                    # Keep the Bengali: an ASCII slug regex deletes the whole
                    # title and leaves every poem with a meaningless counter id.
                    "poem_id": poem_id(title),
                    "title": title.split("/")[-1],
                    "collection": collection,
                    "source": "bn.wikisource.org",
                    "source_url": "https://bn.wikisource.org/wiki/"
                    + urllib.parse.quote(title.replace(" ", "_")),
                    "revision": revid,
                    "retrieved": today,
                    "rights": "Author died 1941; public domain. Transcription: Bengali Wikisource.",
                    "lines": lines,
                }
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
                print(f"  ok {title.split('/')[-1]} ({len(lines)} lines)")

    print(f"\nwrote {written} poems -> {out_path}")


if __name__ == "__main__":
    main()
