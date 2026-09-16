---
license: cc-by-sa-4.0
language:
- bn
pretty_name: BanglaChhanda Pilot
size_categories:
- n<1K
tags:
- bangla
- bengali
- poetry
- prosody
- scansion
- meter
- literature
task_categories:
- token-classification
---

# BanglaChhanda — pilot corpus

Bangla verse prepared for **chhanda** (ছন্দ) annotation: syllable structure, foot
boundaries, and meter under `অক্ষরবৃত্ত`, `মাত্রাবৃত্ত` and `স্বরবৃত্ত`.

> [!IMPORTANT]
> **This is not gold data.** Every label in `pilot.jsonl` was produced by a
> rule-based scanner and has **not been checked by a human**. The scanner itself
> flags **73% of these lines** as needing review, and the annotation guideline it
> implements has not yet been reviewed by a prosody specialist. Treat this as a
> pre-annotation draft for annotators to correct — not as ground truth, and not as
> a benchmark.

## What is here

| File | Contents |
| --- | --- |
| `data/poems.jsonl` | 81 poems, 3,891 lines, as fetched, with per-poem provenance |
| `data/pilot.jsonl` | 303 lines from 26 poems, one pre-filled annotation record per line |
| `docs/annotation-guide-v0.1.html` | the annotation guideline these records follow |

## Sampling

Poem-sampled, stratified by closed-syllable density into three bands and taken
round-robin, with a seeded shuffle so the selection reproduces.

Whole poems, because scoring a poem's metrical consistency needs its lines
together. Stratified, because the closed-syllable rule is the only thing that
separates the three meters — a closed syllable is worth 2 matra in matrabritta, 1
in svarabritta, and 1 or 2 in akkharbritta depending on whether it ends a word. A
line of entirely open syllables reads identically under all three, so a random
sample would fill up with lines that carry no signal about meter.

Selected lines span closed-syllable density 0.07 to 0.42, across four collections:
কণিকা (12 poems), কড়ি ও কোমল (9), আকাশ-প্রদীপ (3), পলাতকা (2). আকাশ-প্রদীপ is
included deliberately — late Tagore, much of it free verse, so the sample contains
lines that should not scan at all.

## Record schema

```json
{
  "poem_id": "কণিকা-অধিকার",
  "line_no": 1,
  "text": "অধিকার বেশি কার বনের উপর",
  "register": "unknown",
  "syllables": [
    {"i": 0, "span": [0, 1], "type": "open", "word_final": false,
     "conjunct": false, "flags": []}
  ],
  "feet": [[0, 4], [4, 7]],
  "meter": {"proposed": "akkharbritta", "pattern": "payar",
            "confirmed": null, "override_reason": null},
  "needs_review": true,
  "provenance": {"source_url": "...", "revision": 1941668, "retrieved": "2026-09-16"}
}
```

**There is no matra field, on purpose.** Matra is derived from syllable structure
plus the meter's rules. Storing it would bake the textbook rules into the data and
make it impossible to test whether those rules predict what annotators actually
hear. Structure is annotated; matra is computed.

`meter.confirmed` is null throughout — the machine proposes, a human disposes.

## Flags

The scanner marks what it is unsure about instead of guessing. Counts across the
303 pilot lines:

| Flag | Lines | Meaning |
| --- | --- | --- |
| `conjunct_split` | 175 | a written cluster divided across a syllable boundary |
| `schwa_medial_uncertain` | 127 | inherent vowel before another inherent vowel — variable, partly dialectal |
| `final_schwa_kept_after_conjunct` | 83 | `শব্দ` stays shob-do rather than becoming shobd |
| `phala_kept_in_onset` | 76 | r-phala held in the onset: `আক্রমণ` is a-kro-mon |
| `y_phala_gemination_check` | 24 | y-phala may geminate; a human decides |

## Known limitations

- **Final-schwa exceptions are not modelled.** The rule deletes a word-final
  inherent vowel unless it follows a conjunct. That is wrong for a class of common
  words — `ছোট` is said cho-to, and the scanner gives one closed syllable. How
  often the rule misfires is a number the annotation should report, not something
  to patch by intuition.
- **The foot patterns are a starting set**, not a full inventory of Bangla line
  forms. Tripadi and the longer forms are absent.
- **No prosodic authority is pinned yet.** The matra rules follow the common
  textbook description; authorities differ on exactly the edge cases that decide
  inter-annotator agreement.
- **One poet, four collections.** Nothing here establishes how the rules behave on
  Nazrul, Jibanananda, or modern free verse.

## Citing this work

This dataset and code are released under **CC BY-SA 4.0**, which *requires
attribution*. If you use the scanner, the guideline or any part of the corpus in
research or in a derived resource, cite it:

```bibtex
@misc{morol2026banglachhanda,
  author    = {Morol, Md Kishor},
  orcid     = {0000-0002-4468-8260},
  title     = {{BanglaChhanda}: a rule-based scanner and pilot corpus for
               {Bangla} verse},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22798431},
  url       = {https://doi.org/10.5281/zenodo.22798431}
}
```

That is the **concept DOI**: it always resolves to the newest version, which is
what you want when citing the work in general. To pin the exact release you used,
cite the version DOI instead — v0.1.0 is [`10.5281/zenodo.22798432`](https://doi.org/10.5281/zenodo.22798432).

Author ORCID: [0000-0002-4468-8260](https://orcid.org/0000-0002-4468-8260).

Please also credit **Bengali Wikisource** for the transcriptions, as the CC BY-SA
terms of the source text require. The poems themselves are public domain.

If you correct or extend the annotations, CC BY-SA also requires you to release
the result under the same licence.

## Source, rights and attribution

Poems are by **Rabindranath Tagore** (died 1941), in the public domain in
Bangladesh and India (life + 60) and in the United States.

Transcriptions come from **[Bengali Wikisource](https://bn.wikisource.org)**, and
each poem record keeps its page URL, **revision id** and retrieval date, so any
line traces back to the exact revision it came from. The dataset is released under
CC BY-SA 4.0 in keeping with Wikisource's terms; the underlying poems are public
domain.

**Attribution is a licence condition, not a courtesy.** Using this dataset without
crediting the author and Bengali Wikisource does not comply with CC BY-SA 4.0. See
the citation block above.

## Code

The scanner, the fetcher and the pilot builder are at
**https://github.com/kishormorol/banglachhanda**.
