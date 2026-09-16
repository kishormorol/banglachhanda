"""Top-level API: scan a line, and emit a pre-filled annotation record.

`scan()` is the rule-based baseline the modelling paper compares against.
`to_annotation()` is the same result shaped as the guideline's JSON schema, so
annotators correct a draft instead of starting from an empty line — cheaper, and
every correction is a datapoint about where the rules fail.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .meters import (
    BENGALI_NAMES,
    FootFit,
    METERS,
    WEAK_ALIGNMENT,
    candidate_fits,
    matra_sequence,
    total_matra,
)
from .syllable import Syllable, syllabify


@dataclass
class Scansion:
    text: str
    syllables: list[Syllable]
    fits: list[FootFit] = field(default_factory=list)

    @property
    def flags(self) -> list[str]:
        """Every uncertainty flag raised anywhere in the line."""
        seen: list[str] = []
        for s in self.syllables:
            for f in s.flags:
                if f not in seen:
                    seen.append(f)
        return seen

    @property
    def needs_review(self) -> bool:
        weak = bool(self.fits) and self.fits[0].alignment < WEAK_ALIGNMENT
        return bool(self.flags) or not self.fits or not self.fits[0].exact or weak

    @property
    def best(self) -> FootFit | None:
        return self.fits[0] if self.fits else None

    def matra(self, meter: str) -> list[int]:
        return matra_sequence(self.syllables, meter)

    def summary(self) -> str:
        # Slice the original text rather than reassembling from parts: the
        # inherent vowel is unwritten and chandrabindu lives on the vowel, so a
        # reassembled string misrepresents what the reader sees.
        parts = [
            f"{self.text[s.start:s.end] or ''.join(s.onset)}"
            f"[{'C' if s.closed else 'O'}]"
            for s in self.syllables
        ]
        head = f"{self.text}\n  " + " ".join(parts)
        counts = "\n  " + "  ".join(
            f"{BENGALI_NAMES[m]}={total_matra(self.syllables, m)}" for m in METERS
        )
        if self.best:
            fit = self.best
            head += counts + (
                f"\n  best: {fit.pattern_name} "
                f"({'exact' if fit.exact else f'short final {fit.short_final}'}"
                f", word-alignment {fit.alignment:.0%})"
            )
        else:
            head += counts + "\n  best: no pattern fits"
        if self.flags:
            head += "\n  flags: " + ", ".join(self.flags)
        return head


def scan(text: str) -> Scansion:
    syllables = syllabify(text)
    return Scansion(text=text, syllables=syllables, fits=candidate_fits(syllables))


def to_annotation(
    text: str, poem_id: str = "", line_no: int = 0, register: str = "unknown"
) -> dict:
    """A pre-filled record in the guideline's schema.

    `meter.confirmed` is left null on purpose: the machine proposes, the human
    disposes. Matra is absent by design — it is derived, never stored.
    """
    result = scan(text)
    best = result.best
    return {
        "poem_id": poem_id,
        "line_no": line_no,
        "text": text,
        "register": register,
        "syllables": [
            {
                "i": i,
                "span": [s.start, s.end],
                "type": s.type,
                "word_final": s.word_final,
                "conjunct": s.conjunct,
                "flags": s.flags,
            }
            for i, s in enumerate(result.syllables)
        ],
        "feet": [list(f) for f in best.feet] if best else [],
        "short_final_foot": bool(best and best.short_final),
        "meter": {
            "proposed": best.meter if best else None,
            "pattern": best.pattern_name if best else None,
            # How much of the proposal is metre rather than arithmetic: the share
            # of foot boundaries landing at word boundaries. A low value means the
            # numbers add up and nothing else does.
            "alignment": round(best.alignment, 2) if best else None,
            "weak": bool(best and best.alignment < WEAK_ALIGNMENT),
            "confirmed": None,
            "override_reason": None,
        },
        "licence": False,
        "annotator": None,
        "needs_review": result.needs_review,
        "notes": "",
    }
