"""Orthographic units -> spoken syllables.

Bangla orthography over-counts syllables: `কমল` writes three aksharas and is
said with two. Meter follows the spoken line, so scansion has to undo that. Two
processes do most of the work:

  * **schwa deletion** — the inherent vowel drops in some positions,
  * **conjunct splitting** — a written cluster divides across a boundary, so
    `শব্দ` is said `শব্ + দ` and the first syllable ends in a consonant.

Neither is fully regular, and the irregular residue is exactly what the
annotation guideline asks a human to rule on. So every rule below that could
plausibly go the other way sets a flag rather than deciding quietly. A syllable
carrying flags is a syllable to put in front of an annotator.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .script import (
    INHERENT,
    Unit,
    Word,
    parse_line,
)

# A cluster is split before its final consonant, so that consonant starts the
# next syllable and the rest close the previous one. R-phala is the exception:
# `আক্রমণ` is said a-kro-mon, not ak-ro-mon, so the র stays in the onset.
NO_SPLIT_BEFORE = {"র"}


@dataclass
class Syllable:
    onset: list[str] = field(default_factory=list)
    nucleus: str | None = None
    coda: list[str] = field(default_factory=list)
    word_index: int = 0
    word_final: bool = False
    conjunct: bool = False
    flags: list[str] = field(default_factory=list)
    start: int = 0
    end: int = 0

    @property
    def closed(self) -> bool:
        """`বদ্ধাক্ষর` — ends in a consonant."""
        return bool(self.coda)

    @property
    def type(self) -> str:
        return "closed" if self.closed else "open"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{''.join(self.onset)}{self.nucleus or ''}{''.join(self.coda)} {self.type}>"


def _delete_final_schwa(units: list[Unit]) -> tuple[bool, list[str]]:
    """Does this word's final inherent vowel drop?

    It usually does — `মানুষ` is ma-nush, not ma-nu-sho. It is kept after a
    conjunct, because dropping it would leave a cluster the language will not
    end a word on: `শব্দ` stays shob-do.
    """
    last = units[-1]
    if not last.inherent:
        return False, []
    if len(units) == 1:
        # A one-unit word has nothing to attach a stranded consonant to.
        return False, ["final_schwa_kept_monosyllable"]
    if last.conjunct:
        return False, ["final_schwa_kept_after_conjunct"]
    return True, []


def _delete_medial_schwa(units: list[Unit], idx: int) -> tuple[bool, list[str]]:
    """Does a word-medial inherent vowel drop?

    Deletes when the following unit carries a written vowel — `কলকাতা` is
    kol-ka-ta. Never deletes in the first unit, which would leave the word
    starting on a bare consonant (`করেছি` is ko-re-chi, not kre-chi).

    When the next unit also carries an inherent vowel the outcome is genuinely
    variable and partly dialectal, so this returns "no" and flags it.
    """
    if idx == 0:
        return False, []
    unit = units[idx]
    if not unit.inherent:
        return False, []
    nxt = units[idx + 1]
    if nxt.inherent:
        return False, ["schwa_medial_uncertain"]
    return True, []


def syllabify_word(units: list[Unit], word_index: int = 0) -> list[Syllable]:
    if not units:
        return []

    # 1. Decide which inherent vowels survive.
    keep: list[bool] = []
    flags_per_unit: list[list[str]] = []
    for i, unit in enumerate(units):
        flags: list[str] = []
        if unit.nucleus is None:
            keep.append(False)          # a visible hasant: no vowel to start with
        elif i == len(units) - 1:
            drop, flags = _delete_final_schwa(units)
            keep.append(not drop)
        else:
            drop, flags = _delete_medial_schwa(units, i)
            keep.append(not drop)
        flags_per_unit.append(flags)

    # 2. Build syllables. A unit with a surviving vowel opens a new syllable;
    #    one without attaches its consonants to the syllable before it.
    syllables: list[Syllable] = []
    for i, unit in enumerate(units):
        onset = list(unit.onset)
        flags = list(flags_per_unit[i])

        if keep[i]:
            start = unit.start
            # A medial conjunct splits: all but the last consonant close the
            # previous syllable.
            if unit.conjunct and len(onset) > 1 and syllables and onset[-1] not in NO_SPLIT_BEFORE:
                moved, onset = onset[:-1], [onset[-1]]
                syllables[-1].coda.extend(moved)
                # Each moved consonant occupies two characters in the source:
                # the consonant itself and the virama that joins it on. The
                # boundary is where the previous syllable ends and this one starts.
                start = unit.start + 2 * len(moved)
                syllables[-1].end = start
                flags.append("conjunct_split")
                if "য" in moved or onset[0] == "য":
                    flags.append("y_phala_gemination_check")
            elif unit.conjunct and len(onset) > 1 and onset[-1] in NO_SPLIT_BEFORE:
                flags.append("phala_kept_in_onset")

            syllable = Syllable(
                onset=onset,
                nucleus=unit.nucleus,
                word_index=word_index,
                conjunct=unit.conjunct,
                flags=flags,
                start=start,
                end=unit.end,
            )
            if unit.has_coda_mark:
                syllable.coda.append("ং")
            syllables.append(syllable)
        else:
            if not syllables:
                # Nothing precedes it: keep it as a syllable of its own rather
                # than dropping characters on the floor.
                syllables.append(
                    Syllable(
                        onset=onset,
                        nucleus=unit.nucleus or INHERENT,
                        word_index=word_index,
                        flags=flags + ["stranded_onset"],
                        start=unit.start,
                        end=unit.end,
                    )
                )
            else:
                syllables[-1].coda.extend(onset)
                syllables[-1].end = unit.end
                syllables[-1].flags.extend(flags)
                if unit.has_coda_mark:
                    syllables[-1].coda.append("ং")

    if syllables:
        syllables[-1].word_final = True
    return syllables


def syllabify(text: str) -> list[Syllable]:
    """Syllabify a whole line of verse."""
    out: list[Syllable] = []
    words: list[Word] = parse_line(text)
    for w_i, word in enumerate(words):
        out.extend(syllabify_word(word.units, word_index=w_i))
    return out
