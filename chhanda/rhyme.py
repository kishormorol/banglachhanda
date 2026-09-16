"""Rhyme (অন্ত্যমিল) over the syllable layer.

Bangla rhyme is a fact about sound, not spelling. `শ`, `ষ` and `স` are one
sibilant; `ণ` and `ন` are one nasal; `জ` and `য` fall together. Orthography keeps
distinctions the ear does not, so matching written characters both misses real
rhymes and invents false ones.

What counts as the rhyming part: the last syllable's nucleus and coda, ignoring
its onset — `করে` and `পড়ে` rhyme on -e although the onsets differ. `depth`
extends the comparison back through earlier syllables, which is what separates a
rich rhyme from two words that merely end in the same vowel.

Limits worth stating plainly: this reads orthography, with no pronunciation
lexicon behind it. The inherent vowel is mapped to one phoneme though its
realisation varies, and vowel-height alternations are not modelled. It finds
rhyme as the script suggests it, not as a reciter would land it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .syllable import Syllable, syllabify

# Letters that sound alike collapse to one symbol. Folding the distinctions the
# ear ignores is the whole job; keeping them would break real rhymes.
CONSONANT_CLASS = {
    "শ": "ʃ", "ষ": "ʃ", "স": "ʃ",
    "ণ": "n", "ন": "n",
    "জ": "dʒ", "য": "dʒ",
    "ড়": "ɽ", "ঢ়": "ɽ",
    "ৎ": "t", "ত": "t", "ট": "t",
    "দ": "d", "ড": "d",
    "ক": "k", "খ": "kʰ",
    "গ": "g", "ঘ": "gʰ",
    "প": "p", "ফ": "pʰ",
    "ব": "b", "ভ": "bʰ",
    "ম": "m", "ং": "ŋ", "ঙ": "ŋ", "ঞ": "n",
    "র": "r", "ল": "l", "হ": "h",
    "চ": "tʃ", "ছ": "tʃʰ",
    "থ": "tʰ", "ঠ": "tʰ",
    "ধ": "dʰ", "ঢ": "dʰ",
    "য়": "j",
}

# Written vowel -> one symbol. Length is not contrastive in modern Bangla, so
# ই/ঈ and উ/ঊ fold together; keeping them apart would split rhyming pairs.
VOWEL_CLASS = {
    "া": "a", "আ": "a",
    "ি": "i", "ী": "i", "ই": "i", "ঈ": "i",
    "ু": "u", "ূ": "u", "উ": "u", "ঊ": "u",
    "ে": "e", "এ": "e",
    "ৈ": "oi", "ঐ": "oi",
    "ো": "o", "ও": "o",
    "ৌ": "ou", "ঔ": "ou",
    "ৃ": "ri", "ঋ": "ri",
    "অ": "ɔ",          # the inherent vowel; realisation varies, see module docstring
}


def _fold_consonant(ch: str) -> str:
    return CONSONANT_CLASS.get(ch.replace("়", ""), ch)


def _fold_vowel(ch: str | None) -> str:
    if ch is None:
        return ""
    return VOWEL_CLASS.get(ch, ch)


def syllable_rhyme(syllable: Syllable) -> str:
    """The rhyming part of one syllable: nucleus + coda, onset dropped."""
    nucleus = _fold_vowel(syllable.nucleus)
    coda = "".join(_fold_consonant(c) for c in syllable.coda)
    return nucleus + coda


def rhyme_key(text: str, depth: int = 1) -> str:
    """Key for the end of a line. Equal keys rhyme.

    `depth` counts syllables back from the end. depth=1 is the loose rhyme Bangla
    verse usually marks; depth=2 requires the preceding syllable to match too,
    which is what tells a real rhyme from a shared final vowel.
    """
    syllables = syllabify(text)
    if not syllables:
        return ""
    tail = syllables[-depth:] if depth > 0 else syllables
    parts = [syllable_rhyme(tail[-1])]
    # Earlier syllables contribute their onset as well: at this depth the
    # consonant is part of what makes the rhyme rich.
    for syllable in reversed(tail[:-1]):
        onset = "".join(_fold_consonant(c) for c in syllable.onset)
        parts.insert(0, onset + syllable_rhyme(syllable))
    return "·".join(parts)


def rhymes(a: str, b: str, depth: int = 1) -> bool:
    key_a, key_b = rhyme_key(a, depth), rhyme_key(b, depth)
    return bool(key_a) and key_a == key_b


@dataclass
class RhymeScheme:
    labels: list[str]          # "a", "b", … per line; "-" for an unrhymed line
    keys: list[str]
    pattern: str               # the labels joined, e.g. "aabb"

    @property
    def rhymed_share(self) -> float:
        """Share of lines that rhyme with at least one other."""
        if not self.labels:
            return 0.0
        return sum(1 for label in self.labels if label != "-") / len(self.labels)


def rhyme_scheme(lines: list[str], depth: int = 1) -> RhymeScheme:
    """Label a stanza's rhyme scheme — aabb, abab, and so on.

    A line whose key matches nothing else is "-" rather than a fresh letter: an
    unrhymed line is not a rhyme class of one, and calling it one would make free
    verse look like an elaborate scheme.
    """
    keys = [rhyme_key(line, depth) for line in lines]
    counts: dict[str, int] = {}
    for key in keys:
        if key:
            counts[key] = counts.get(key, 0) + 1

    labels: list[str] = []
    assigned: dict[str, str] = {}
    next_label = ord("a")
    for key in keys:
        if not key or counts.get(key, 0) < 2:
            labels.append("-")
            continue
        if key not in assigned:
            assigned[key] = chr(next_label)
            next_label += 1
        labels.append(assigned[key])
    return RhymeScheme(labels=labels, keys=keys, pattern="".join(labels))
