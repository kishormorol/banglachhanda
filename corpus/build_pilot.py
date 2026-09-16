"""Build the annotation pilot from the fetched corpus.

Sampling is **poem-sampled and stratified by closed-syllable density**.

Whole poems, because the metric paper needs to score a poem's consistency across
its lines, and lines pulled out of context cannot support that. Stratified,
because the closed-syllable rule is the only thing separating the three meters:
a line of entirely open syllables reads the same under all of them, so a random
sample would fill the pilot with lines that carry no signal about meter.

The output is one pre-filled annotation record per line, in the guideline's
schema, with the scanner's proposal and `meter.confirmed` left null. Annotators
correct a draft; every correction is a datapoint about where the rules fail.

  python corpus/build_pilot.py --target 300
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

# Running a script inside corpus/ puts that directory on sys.path, not the repo
# root, so the package next door is invisible without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chhanda.scan import scan, to_annotation  # noqa: E402


def closed_density(lines: list[str]) -> float:
    """Share of syllables in the poem that are closed."""
    closed = total = 0
    for line in lines:
        syllables = scan(line).syllables
        total += len(syllables)
        closed += sum(1 for s in syllables if s.closed)
    return closed / total if total else 0.0


MAX_POEM_LINES = 40     # a single long narrative would swamp the sample
MIN_POEM_LINES = 2


def stratify(poems: list[dict], target: int, seed: int = 0) -> list[dict]:
    """Take whole poems across three density bands until the target is reached.

    Round-robin across bands rather than taking the densest first: a pilot made
    only of closed-syllable-heavy verse would measure the rules on their hardest
    cases and tell us nothing about the easy majority.

    Long poems are held back. Taking the longest first reaches 300 lines in two
    poems, which is technically 300 lines of verse and useless as a sample —
    no spread across poets' forms, and both bands unrepresented. Selection
    within a band is a seeded shuffle so the pilot is reproducible.

    Bands are split by author as well as density. With one poet that changed
    nothing; with two it stops a pilot coming out as 90% Tagore, which would tell
    us how the rules do on payar and nothing about looser modern verse.
    """
    scored = [
        {**poem, "closed_density": closed_density(poem["lines"])}
        for poem in poems
        if MIN_POEM_LINES <= len(poem["lines"]) <= MAX_POEM_LINES
    ]
    scored.sort(key=lambda p: -p["closed_density"])

    third = max(1, len(scored) // 3)
    bands = [scored[:third], scored[third: 2 * third], scored[2 * third:]]

    # One queue per (density band, author), so the round-robin spreads over both.
    authors = sorted({p.get("author", "unknown") for p in scored})
    rng = random.Random(seed)
    queues: list[list[dict]] = []
    for band in bands:
        for author in authors:
            queue = [p for p in band if p.get("author", "unknown") == author]
            rng.shuffle(queue)
            queues.append(queue)

    chosen: list[dict] = []
    count = 0
    i = 0
    ceiling = int(target * 1.1)
    while count < target and any(queues):
        queue = queues[i % len(queues)]
        i += 1
        if not queue:
            continue
        poem = queue.pop(0)
        if count + len(poem["lines"]) > ceiling:
            continue            # would overshoot; try the next queue instead
        chosen.append(poem)
        count += len(poem["lines"])
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--poems", default="corpus/poems.jsonl")
    ap.add_argument("--out", default="corpus/pilot.jsonl")
    ap.add_argument("--target", type=int, default=300, help="lines wanted")
    args = ap.parse_args()

    poems = [json.loads(ln) for ln in Path(args.poems).read_text(encoding="utf-8").splitlines() if ln.strip()]
    print(f"corpus: {len(poems)} poems, {sum(len(p['lines']) for p in poems)} lines")

    chosen = stratify(poems, args.target)
    records: list[dict] = []
    for poem in chosen:
        for i, line in enumerate(poem["lines"], start=1):
            record = to_annotation(line, poem_id=poem["poem_id"], line_no=i, register="unknown")
            record["provenance"] = {
                "title": poem["title"],
                "author": poem.get("author", "unknown"),
                "collection": poem["collection"],
                "source_url": poem["source_url"],
                "revision": poem["revision"],
                "retrieved": poem["retrieved"],
                "rights": poem["rights"],
            }
            records.append(record)

    Path(args.out).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8"
    )

    # --- report ---------------------------------------------------------
    flags = Counter(f for r in records for s in r["syllables"] for f in s["flags"])
    proposed = Counter(r["meter"]["proposed"] or "no fit" for r in records)
    review = sum(1 for r in records if r["needs_review"])
    densities = [p["closed_density"] for p in chosen]

    by_author = Counter()
    for r in records:
        by_author[r["provenance"]["author"]] += 1
    collections = Counter(p["collection"].split(" (")[0] for p in chosen)
    print(f"\npilot: {len(records)} lines from {len(chosen)} poems -> {args.out}")
    print("  poets:       " + ", ".join(f"{a} ({n} lines)" for a, n in by_author.most_common()))
    print("  collections: " + ", ".join(f"{c} ({n})" for c, n in collections.most_common()))
    print(f"  closed-syllable density: min {min(densities):.2f}  "
          f"median {statistics.median(densities):.2f}  max {max(densities):.2f}")
    print(f"  needs_review: {review} lines ({review / len(records):.0%})")
    print("\n  scanner's proposed meter (to be confirmed or overridden):")
    for meter, n in proposed.most_common():
        print(f"    {n:4}  {meter}")
    print("\n  flags raised:")
    for flag, n in flags.most_common():
        print(f"    {n:4}  {flag}")
    print("\nEvery proposal above is the rule engine's guess, not ground truth.")


if __name__ == "__main__":
    main()
