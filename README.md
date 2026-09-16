# banglachhanda

A rule-based scanner for Bangla verse. It takes a line, works out its syllables and
their structure, and derives matra counts and foot divisions under each of the three
meters — `অক্ষরবৃত্ত`, `মাত্রাবৃত্ত`, `স্বরবৃত্ত`.

This is the **baseline** for the BanglaChhanda project, not the product. Its job is to
be the honest floor that a learned scansion model has to beat, and to pre-fill
annotation records so annotators correct a draft instead of starting from nothing.

```python
>>> from chhanda import scan
>>> print(scan("শব্দ").summary())
শব্দ
  শব্[C] দ[O]
  অক্ষরবৃত্ত=2  মাত্রাবৃত্ত=3  স্বরবৃত্ত=2
  best: no pattern fits
  flags: final_schwa_kept_after_conjunct, conjunct_split
```

One written word, one structural analysis, three different matra readings — all
produced by rule. That is the whole design in one example.

## The design rule

**Structure is annotated; matra is computed.** A closed syllable is worth 2 matra in
matrabritta, 1 in svarabritta, and 1 or 2 in akkharbritta depending on whether it ends
a word. If annotators wrote matra counts by hand, the corpus would encode the textbook
rules and could never be used to test them. So the annotation records syllabification,
open/closed and foot boundaries; this library derives the rest.

That is why `to_annotation()` emits no matra field. It is not an omission.

## Uncertainty is flagged, never resolved quietly

Schwa deletion and conjunct splitting are not fully regular. Where a rule could
plausibly go either way, the scanner sets a flag and carries on rather than guessing:

| Flag | Meaning |
| --- | --- |
| `schwa_medial_uncertain` | inherent vowel before another inherent vowel — variable, partly dialectal |
| `final_schwa_kept_after_conjunct` | `শব্দ` stays shob-do rather than becoming shobd |
| `final_schwa_kept_monosyllable` | nothing precedes it to attach a stranded consonant to |
| `conjunct_split` | a written cluster divided across a syllable boundary |
| `phala_kept_in_onset` | r-phala held in the onset: `আক্রমণ` is a-kro-mon |
| `y_phala_gemination_check` | y-phala may geminate; guideline hard case 3 says a human decides |
| `stranded_onset` | consonants with no syllable to attach to — usually malformed input |

`scan(line).needs_review` is true when anything is flagged or no foot pattern fits.
Route those lines to a human first; they are where the rules are earning or failing.

## Known limitations

These are real and should be measured by the pilot rather than patched by guesswork.

- **Final-schwa exceptions are not modelled.** The rule deletes a word-final inherent
  vowel unless it follows a conjunct. That is right most of the time and wrong for a
  class of common words — `ছোট` is said cho-to, but the scanner gives one closed
  syllable. Fixing this properly needs an exception lexicon, and that lexicon should
  come out of annotation, not out of intuition. **How often this rule is wrong is a
  headline number for the resource paper.**
- **The foot patterns are a starting set**, not a complete inventory of Bangla line
  forms. `PATTERNS` in `meters.py` holds payar, four matrabritta feet and one
  svarabritta foot. Tripadi and the longer forms are absent.
- **No authority is pinned yet.** The matra table follows the common textbook
  description; §2 and §5 of the annotation guideline list what a prosody specialist
  must confirm before the numbers are trusted.
- **Orthography only.** No pronunciation lexicon, no dialect handling, no performance
  timing.

A note on that first limitation, since it will come up: when the scanner disagrees
with a reader about a well-known line, the scanner is the more likely one to be wrong.
It fits `আমাদের ছোট নদী চলে বাঁকে বাঁকে` as payar, exactly; whether that is the
accepted scansion of the line is precisely the sort of question the specialist review
exists to settle.

## Layout

```
chhanda/script.py     text -> orthographic units (aksharas); mechanical, no judgement
chhanda/syllable.py   units -> spoken syllables; schwa deletion and conjunct splitting
chhanda/meters.py     matra values and foot fitting per meter
chhanda/scan.py       scan() and to_annotation()
tests/                28 tests, all rule-application cases
```

No test asserts the "correct" meter of a canonical poem. Until the guideline is signed
off, doing so would be inventing ground truth.

## Running it

```
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest -q
```

Requires Python 3.10+ (uses `X | None` annotations). No runtime dependencies.

## Corpus

`corpus/fetch_wikisource.py` pulls public-domain Tagore from Bengali Wikisource with
per-poem provenance (page URL, revision id, retrieval date). `corpus/build_pilot.py`
samples it poem-wise, stratified by closed-syllable density, and writes one
pre-filled annotation record per line.

```
.venv/bin/python corpus/fetch_wikisource.py --collection "কণিকা (রবীন্দ্রনাথ ঠাকুর)" --limit 40
.venv/bin/python corpus/build_pilot.py --target 300
```

The current pilot is 303 lines from 26 poems across four collections, and the
scanner flags 73% of them for review — the honest state of the rules.

## Citing this work

This dataset and code are released under **CC BY-SA 4.0**, which *requires
attribution*. If you use the scanner, the guideline or any part of the corpus in
research or in a derived resource, cite it:

```bibtex
@misc{morol2026banglachhanda,
  author       = {Morol, Md Kishor},
  orcid        = {0000-0002-4468-8260},
  title        = {{BanglaChhanda}: a rule-based scanner and pilot corpus for
                  {Bangla} verse},
  year         = {2026},
  version      = {0.1.0},
  howpublished = {\url{https://huggingface.co/datasets/kishormorol/banglachhanda}},
  note         = {Code: \url{https://github.com/kishormorol/banglachhanda}}
}
```

Author ORCID: [0000-0002-4468-8260](https://orcid.org/0000-0002-4468-8260).

Please also credit **Bengali Wikisource** for the transcriptions, as the CC BY-SA
terms of the source text require. The poems themselves are public domain.

If you correct or extend the annotations, CC BY-SA also requires you to release
the result under the same licence.

## Related

The annotation guideline this implements is in `docs/`; the flag names above
correspond to its numbered hard cases.

The corpus and pilot are published as a dataset:
**[huggingface.co/datasets/kishormorol/banglachhanda](https://huggingface.co/datasets/kishormorol/banglachhanda)**.
The dataset card leads with the warning that none of its labels are human-checked.
