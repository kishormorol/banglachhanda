"""Matra values and foot patterns for the three meters.

The whole point of keeping this separate from syllable.py: syllable structure is
meter-independent, but its matra value is not. One closed syllable is worth 2
matra in matrabritta, 1 in svarabritta, and either in akkharbritta depending on
where it sits. Structure is annotated; matra is computed here.

PROVISIONAL. These rules are from general knowledge of Bangla prosody, not from
a pinned authority — §5 of the annotation guideline lists what must be checked
before anyone trusts the numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

from .syllable import Syllable

AKKHARBRITTA = "akkharbritta"
MATRABRITTA = "matrabritta"
SVARABRITTA = "svarabritta"
METERS = (AKKHARBRITTA, MATRABRITTA, SVARABRITTA)

BENGALI_NAMES = {
    AKKHARBRITTA: "অক্ষরবৃত্ত",
    MATRABRITTA: "মাত্রাবৃত্ত",
    SVARABRITTA: "স্বরবৃত্ত",
}


def matra(syllable: Syllable, meter: str) -> int:
    """Matra value of one syllable under one meter."""
    if meter not in METERS:
        # Checked before anything else: an open syllable is 1 matra under every
        # meter, so a late check would wave a misspelled meter name through.
        raise ValueError(f"unknown meter: {meter!r} (expected one of {', '.join(METERS)})")
    if meter == SVARABRITTA or not syllable.closed:
        return 1
    if meter == MATRABRITTA:
        return 2
    # Akkharbritta: a closed syllable is heavy only at the end of a word.
    return 2 if syllable.word_final else 1


def matra_sequence(syllables: list[Syllable], meter: str) -> list[int]:
    return [matra(s, meter) for s in syllables]


def total_matra(syllables: list[Syllable], meter: str) -> int:
    return sum(matra_sequence(syllables, meter))


@dataclass
class FootFit:
    meter: str
    pattern: tuple[int, ...]
    pattern_name: str
    feet: list[tuple[int, int]]      # half-open syllable index ranges
    exact: bool
    short_final: int = 0             # matra left over in a short final foot

    @property
    def score(self) -> float:
        """Exact fits rank first; a short final foot is a mild penalty."""
        return (1.0 if self.exact else 0.0) - 0.05 * (1 if self.short_final else 0)


# Named line patterns. Only the ones this project is confident enough to test
# against; more can be added once the authority in guideline §2 is pinned.
PATTERNS: dict[str, list[tuple[str, tuple[int, ...]]]] = {
    AKKHARBRITTA: [("payar", (8, 6))],
    MATRABRITTA: [
        ("matrabritta-4", (4, 4, 4, 4)),
        ("matrabritta-5", (5, 5, 5, 5)),
        ("matrabritta-6", (6, 6, 6, 6)),
        ("matrabritta-7", (7, 7, 7, 7)),
    ],
    SVARABRITTA: [("svarabritta-4", (4, 4, 4, 4))],
}


def fit_pattern(
    syllables: list[Syllable], meter: str, pattern: tuple[int, ...], allow_short_final: bool = True
) -> FootFit | None:
    """Try to divide a line into feet of the given matra counts.

    A foot boundary can fall mid-word (guideline hard case 9) but never inside a
    syllable, so a pattern that would need to split one does not fit.
    """
    values = matra_sequence(syllables, meter)
    feet: list[tuple[int, int]] = []
    i = 0
    for target in pattern:
        if i >= len(values):
            break
        run = 0
        start = i
        while i < len(values) and run < target:
            run += values[i]
            i += 1
        if run != target:
            if i >= len(values) and run < target and allow_short_final and feet:
                feet.append((start, i))
                return FootFit(meter, pattern, "", feet, exact=False, short_final=run)
            return None
        feet.append((start, i))

    if i < len(values):
        leftover = sum(values[i:])
        if allow_short_final:
            feet.append((i, len(values)))
            return FootFit(meter, pattern, "", feet, exact=False, short_final=leftover)
        return None
    return FootFit(meter, pattern, "", feet, exact=True)


def candidate_fits(syllables: list[Syllable], allow_short_final: bool = True) -> list[FootFit]:
    """Every (meter, pattern) that can account for the line, best first.

    Returning several is deliberate. Many lines genuinely scan under more than
    one meter, and a scanner that reports a single confident answer hides the
    ambiguity an annotator is there to resolve.
    """
    fits: list[FootFit] = []
    for meter, patterns in PATTERNS.items():
        for name, pattern in patterns:
            fit = fit_pattern(syllables, meter, pattern, allow_short_final)
            if fit is not None:
                fit.pattern_name = name
                fits.append(fit)
    fits.sort(key=lambda f: (-f.score, len(f.feet)))
    return fits
