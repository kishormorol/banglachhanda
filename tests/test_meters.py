"""Matra rules and foot fitting."""
import pytest

from chhanda.meters import (
    AKKHARBRITTA,
    MATRABRITTA,
    SVARABRITTA,
    WEAK_ALIGNMENT,
    candidate_fits,
    fit_pattern,
    matra,
    total_matra,
)
from chhanda.scan import scan, to_annotation
from chhanda.syllable import Syllable, syllabify


def syl(closed=False, word_final=False):
    s = Syllable(nucleus="অ", word_final=word_final)
    if closed:
        s.coda.append("ক")
    return s


def test_open_syllable_is_one_matra_everywhere():
    s = syl()
    assert {matra(s, m) for m in (AKKHARBRITTA, MATRABRITTA, SVARABRITTA)} == {1}


def test_closed_syllable_diverges_by_meter():
    """The one rule that distinguishes the three meters."""
    medial = syl(closed=True, word_final=False)
    final = syl(closed=True, word_final=True)
    assert matra(medial, SVARABRITTA) == 1
    assert matra(final, SVARABRITTA) == 1
    assert matra(medial, MATRABRITTA) == 2
    assert matra(final, MATRABRITTA) == 2
    assert matra(medial, AKKHARBRITTA) == 1      # heavy only at a word end
    assert matra(final, AKKHARBRITTA) == 2


def test_shobdo_matches_the_guideline_worked_example():
    """শব্দ: 2 matra in akkharbritta, 3 in matrabritta, 2 in svarabritta."""
    syls = syllabify("শব্দ")
    assert total_matra(syls, AKKHARBRITTA) == 2
    assert total_matra(syls, MATRABRITTA) == 3
    assert total_matra(syls, SVARABRITTA) == 2


def test_all_open_line_is_identical_under_every_meter():
    """Such lines carry no signal about meter — §4 of the guideline."""
    syls = syllabify("চলে বাঁকে বাঁকে")
    totals = {total_matra(syls, m) for m in (AKKHARBRITTA, MATRABRITTA, SVARABRITTA)}
    assert totals == {6}


def test_fit_pattern_exact():
    syls = [syl() for _ in range(8)]
    fit = fit_pattern(syls, SVARABRITTA, (4, 4))
    assert fit is not None and fit.exact
    assert fit.feet == [(0, 4), (4, 8)]


def test_fit_pattern_rejects_a_split_syllable():
    """A foot boundary may fall mid-word but never inside a syllable."""
    heavy = [syl(closed=True, word_final=True) for _ in range(3)]  # 2+2+2 matra
    assert fit_pattern(heavy, MATRABRITTA, (3, 3), allow_short_final=False) is None


def test_short_final_foot_is_reported_not_hidden():
    syls = [syl() for _ in range(6)]
    fit = fit_pattern(syls, SVARABRITTA, (4, 4))
    assert fit is not None
    assert not fit.exact and fit.short_final == 2


def test_candidate_fits_ranks_exact_first():
    syls = [syl() for _ in range(16)]
    fits = candidate_fits(syls)
    assert fits and fits[0].exact


def test_ambiguity_is_reported_as_multiple_candidates():
    """A line that scans several ways should say so rather than pick one."""
    syls = [syl() for _ in range(16)]
    assert len({f.meter for f in candidate_fits(syls)}) > 1


def test_unknown_meter_raises():
    with pytest.raises(ValueError):
        matra(syl(), "payar")


def test_scan_reports_flags_and_review_state():
    result = scan("কমল")
    assert result.needs_review
    assert "schwa_medial_uncertain" in result.flags


def test_annotation_record_omits_matra():
    """Matra is derived, never stored — §1 and §8 of the guideline."""
    record = to_annotation("শব্দ", poem_id="x", line_no=1)
    assert "matra" not in record
    assert all("matra" not in s for s in record["syllables"])
    assert record["meter"]["confirmed"] is None
    assert record["meter"]["proposed"] is not None or record["feet"] == []
    assert record["syllables"][0]["type"] == "closed"


def test_annotation_spans_point_into_the_original_text():
    text = "শব্দ"
    record = to_annotation(text)
    start, end = record["syllables"][0]["span"]
    assert 0 <= start < end <= len(text)


def word(closed=False, final=False):
    s = syl(closed=closed, word_final=final)
    return s


def test_alignment_is_one_when_there_are_no_internal_boundaries():
    fit = fit_pattern([syl() for _ in range(4)], SVARABRITTA, (4,))
    assert fit is not None and fit.alignment == 1.0


def test_word_aligned_feet_outrank_feet_that_slice_words():
    """Bangla feet break where words break; arithmetic alone is not metre."""
    # Eight syllables, word boundary exactly at the foot break.
    aligned = [word(final=(i == 3)) for i in range(8)]
    # Same length, but every word runs across the break.
    sliced = [word(final=(i == 5)) for i in range(8)]
    a = fit_pattern(aligned, SVARABRITTA, (4, 4))
    b = fit_pattern(sliced, SVARABRITTA, (4, 4))
    assert a is not None and b is not None
    assert a.alignment == 1.0
    assert b.alignment == 0.0
    assert a.score > b.score


def test_mid_word_boundaries_are_allowed_just_penalised():
    """Guideline hard case 9 permits them, so they must still fit."""
    sliced = [word(final=(i == 5)) for i in range(8)]
    fit = fit_pattern(sliced, SVARABRITTA, (4, 4))
    assert fit is not None and fit.exact
    assert fit.alignment < WEAK_ALIGNMENT


def test_annotation_exposes_alignment_and_weakness():
    record = to_annotation("আমাদের ছোট নদী চলে বাঁকে বাঁকে")
    assert record["meter"]["alignment"] is not None
    assert record["meter"]["weak"] in (True, False)
