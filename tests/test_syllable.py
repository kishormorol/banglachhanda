"""Syllabification tests.

Every case here is one the rules should settle on their own. Canonical poem
scansions are deliberately absent: until a prosody specialist signs off on the
guideline, asserting that a given Tagore line "is" payar would be inventing
ground truth, which is the one thing this project must not do.
"""
from chhanda.syllable import syllabify


def shapes(text):
    return [(s.type, s.word_final) for s in syllabify(text)]


def test_shobdo_splits_medial_conjunct():
    """শব্দ is said shob-do: the conjunct divides and closes the first syllable."""
    syls = syllabify("শব্দ")
    assert len(syls) == 2
    assert syls[0].closed and "ব" in syls[0].coda
    assert not syls[1].closed
    assert syls[1].word_final


def test_final_schwa_kept_after_conjunct():
    syls = syllabify("শব্দ")
    assert "final_schwa_kept_after_conjunct" in syls[0].flags + syls[1].flags


def test_final_schwa_deleted_normally():
    """মানুষ is ma-nush, not ma-nu-sho."""
    syls = syllabify("মানুষ")
    assert len(syls) == 2
    assert syls[1].closed


def test_komol_two_syllables():
    """কমল writes three aksharas and is said with two."""
    syls = syllabify("কমল")
    assert len(syls) == 2
    assert not syls[0].closed
    assert syls[1].closed


def test_medial_schwa_deletes_before_written_vowel():
    """কলকাতা is kol-ka-ta."""
    syls = syllabify("কলকাতা")
    assert len(syls) == 3
    assert syls[0].closed
    assert not syls[1].closed and not syls[2].closed


def test_first_syllable_schwa_never_deletes():
    """করেছি is ko-re-chi — a word cannot open on a bare consonant."""
    syls = syllabify("করেছি")
    assert len(syls) == 3
    assert all(not s.closed for s in syls)


def test_anusvara_closes_syllable():
    syls = syllabify("বাংলা")
    assert len(syls) == 2
    assert syls[0].closed


def test_chandrabindu_does_not_close():
    """Nasalisation sits on the vowel and adds no weight."""
    syls = syllabify("বাঁকে")
    assert len(syls) == 2
    assert all(not s.closed for s in syls)


def test_ref_closes_preceding_syllable():
    """কর্ম is kor-mo: ref closes, and the final vowel survives the conjunct."""
    syls = syllabify("কর্ম")
    assert len(syls) == 2
    assert syls[0].closed and "র" in syls[0].coda
    assert not syls[1].closed


def test_r_phala_stays_in_onset():
    """আক্রমণ is a-kro-mon, not ak-ro-mon."""
    syls = syllabify("আক্রমণ")
    assert len(syls) == 3
    assert not syls[0].closed
    assert "র" in syls[1].onset
    assert syls[2].closed


def test_uncertain_medial_schwa_is_flagged_not_guessed():
    """Inherent vowel before another inherent vowel is variable — flag it."""
    syls = syllabify("কমল")
    assert any("schwa_medial_uncertain" in s.flags for s in syls)


def test_monosyllable_keeps_its_vowel():
    syls = syllabify("ক")
    assert len(syls) == 1
    assert "final_schwa_kept_monosyllable" in syls[0].flags


def test_line_marks_word_final_per_word():
    syls = syllabify("চলে বাঁকে বাঁকে")
    assert [s.word_final for s in syls] == [False, True, False, True, False, True]
    assert all(not s.closed for s in syls)


def test_punctuation_is_ignored():
    assert len(syllabify("চলে বাঁকে বাঁকে।")) == len(syllabify("চলে বাঁকে বাঁকে"))


def test_spans_are_ordered_and_within_text():
    text = "আমাদের ছোট নদী"
    syls = syllabify(text)
    assert syls[0].start >= 0
    assert all(a.start <= b.start for a, b in zip(syls, syls[1:]))
    assert syls[-1].end <= len(text)
