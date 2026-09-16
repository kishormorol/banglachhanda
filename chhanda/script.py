"""Bengali script handling: text -> orthographic units (aksharas).

An *orthographic unit* is what the script writes as one cluster: an optional
onset (one consonant, or several joined by virama), a nucleus vowel (written,
inherent, or absent when the cluster ends in a visible hasant), and any
nasal/visarga marks that follow.

This layer is deliberately mechanical. It records what is written, and makes no
claim about how the word is pronounced — that is syllable.py's job, and it is
where the uncertainty lives.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Unicode Bengali block ------------------------------------------------
INDEPENDENT_VOWELS = set("অআইঈউঊঋঌএঐওঔ")
CONSONANTS = set("কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহ") | set("ড়ঢ়য়")
KHANDA_TA = "ৎ"          # U+09CE — a bare /t/ coda, never carries a vowel
VOWEL_SIGNS = set("ািীুূৃৄেৈোৌ")
VIRAMA = "্"              # U+09CD
CHANDRABINDU = "ঁ"        # U+0981 — nasalises the vowel, adds no weight
ANUSVARA = "ং"            # U+0982 — a nasal coda, closes the syllable
VISARGA = "ঃ"            # U+0983 — contested; see guideline hard case 5
NUKTA = "়"               # U+09BC
MARKS = {CHANDRABINDU, ANUSVARA, VISARGA}

INHERENT = "অ"            # the unwritten vowel every bare consonant carries

# Vowel signs that spell a diphthong. Treated as one nucleus by default —
# guideline hard case 6 flags this as a decision the collaborator must confirm.
DIPHTHONG_SIGNS = {"ৈ", "ৌ"}
DIPHTHONG_VOWELS = {"ঐ", "ঔ"}

WORD_SEPARATORS = set(" \t\n ")
# Bengali danda and the punctuation that shows up in printed verse.
PUNCTUATION = set("।॥,;:!?'\"()[]{}—–-…*")


def is_consonant(ch: str) -> bool:
    return ch in CONSONANTS or ch == KHANDA_TA


@dataclass
class Unit:
    """One orthographic cluster, with the source offsets it came from."""

    onset: list[str] = field(default_factory=list)
    nucleus: str | None = None      # a vowel character, INHERENT, or None
    inherent: bool = False          # nucleus is the unwritten vowel
    marks: list[str] = field(default_factory=list)
    conjunct: bool = False          # onset was written as a conjunct
    start: int = 0
    end: int = 0

    @property
    def text(self) -> str:
        return "".join(self.onset) + (self.nucleus or "") + "".join(self.marks)

    @property
    def has_coda_mark(self) -> bool:
        """Anusvara and khanda-ta close a syllable; chandrabindu does not."""
        return ANUSVARA in self.marks or (
            len(self.onset) == 1 and self.onset[0] == KHANDA_TA and self.nucleus is None
        )


@dataclass
class Word:
    units: list[Unit]
    text: str
    start: int
    end: int


def split_words(text: str) -> list[tuple[str, int]]:
    """Split a line into (word, offset) pairs, dropping punctuation."""
    words: list[tuple[str, int]] = []
    current: list[str] = []
    start = 0
    for i, ch in enumerate(text):
        if ch in WORD_SEPARATORS or ch in PUNCTUATION:
            if current:
                words.append(("".join(current), start))
                current = []
        else:
            if not current:
                start = i
            current.append(ch)
    if current:
        words.append(("".join(current), start))
    return words


def parse_units(word: str, offset: int = 0) -> list[Unit]:
    """Parse one word into orthographic units.

    The awkward case is the conjunct: `ব` + virama + `দ` is written as one
    cluster, so it parses as a single unit with a two-consonant onset. Whether
    that cluster stays together or splits across a syllable boundary is decided
    later, in syllable.py.
    """
    units: list[Unit] = []
    i = 0
    n = len(word)
    while i < n:
        ch = word[i]

        if ch in INDEPENDENT_VOWELS:
            unit = Unit(nucleus=ch, start=offset + i, end=offset + i + 1)
            i += 1
            i = _consume_marks(word, i, unit, offset)
            units.append(unit)
            continue

        if is_consonant(ch):
            unit = Unit(start=offset + i)
            unit.onset.append(ch)
            i += 1
            if i < n and word[i] == NUKTA:
                unit.onset[-1] += NUKTA
                i += 1

            # Consonants chained by virama belong to the same written cluster.
            while i < n and word[i] == VIRAMA:
                if i + 1 < n and is_consonant(word[i + 1]):
                    unit.onset.append(word[i + 1])
                    unit.conjunct = True
                    i += 2
                    if i < n and word[i] == NUKTA:
                        unit.onset[-1] += NUKTA
                        i += 1
                else:
                    # A visible hasant: the cluster carries no vowel at all.
                    i += 1
                    unit.nucleus = None
                    unit.end = offset + i
                    i = _consume_marks(word, i, unit, offset)
                    units.append(unit)
                    break
            else:
                if i < n and word[i] in VOWEL_SIGNS:
                    unit.nucleus = word[i]
                    i += 1
                elif unit.onset and unit.onset[-1].startswith(KHANDA_TA):
                    unit.nucleus = None
                else:
                    unit.nucleus = INHERENT
                    unit.inherent = True
                unit.end = offset + i
                i = _consume_marks(word, i, unit, offset)
                units.append(unit)
            continue

        # Anything else (stray marks, digits, Latin) is passed over; the caller
        # has already stripped punctuation.
        i += 1

    return units


def _consume_marks(word: str, i: int, unit: Unit, offset: int) -> int:
    while i < len(word) and word[i] in MARKS:
        unit.marks.append(word[i])
        i += 1
    unit.end = offset + i
    return i


def parse_line(text: str) -> list[Word]:
    return [
        Word(units=parse_units(w, off), text=w, start=off, end=off + len(w))
        for w, off in split_words(text)
    ]
