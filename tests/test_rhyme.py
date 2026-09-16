"""Rhyme detection.

The rhyming pairs here are real couplet endings from কণিকা, which is written in
rhymed couplets throughout — so a pair that fails to rhyme is a bug in the
folding rules, not a disagreement about taste.
"""
from chhanda.rhyme import rhyme_key, rhyme_scheme, rhymes


def test_rhymes_across_different_onsets():
    """করে / পড়ে — the onsets differ, the rhyme is on -e."""
    assert rhymes("করে", "পড়ে")


def test_real_couplet_endings_rhyme():
    assert rhymes("বুকে", "মুখে")
    assert rhymes("বিজুলি", "ভুলি")


def test_unrelated_endings_do_not_rhyme():
    assert not rhymes("বুকে", "ভুলি")
    assert not rhymes("নদী", "বাঁকে")


def test_sibilants_fold_together():
    """শ, ষ and স are one sound, so spelling must not split the rhyme."""
    assert rhyme_key("আশ") == rhyme_key("আষ") == rhyme_key("আস")


def test_nasals_fold_together():
    assert rhyme_key("বান") == rhyme_key("বাণ")


def test_vowel_length_is_not_contrastive():
    """ই/ঈ and উ/ঊ fold: modern Bangla does not contrast length."""
    assert rhyme_key("নদি") == rhyme_key("নদী")


def test_depth_two_is_stricter_than_depth_one():
    """A shared final vowel is not yet a rich rhyme."""
    assert rhymes("করে", "পড়ে", depth=1)
    assert not rhymes("করে", "চলে", depth=2)


def test_empty_input_has_no_key_and_never_rhymes():
    assert rhyme_key("") == ""
    assert not rhymes("", "")


def test_scheme_labels_a_rhymed_couplet():
    scheme = rhyme_scheme(["ধ্বনিটিরে প্রতিধ্বনি সদা ব্যঙ্গ করে", "ধ্বনি-কাছে ঋণী সে যে পাছে ধরা পড়ে"])
    assert scheme.pattern == "aa"
    assert scheme.rhymed_share == 1.0


def test_unrhymed_lines_are_not_given_their_own_letter():
    """Free verse must not come out looking like an elaborate scheme."""
    scheme = rhyme_scheme(["আকাশ নীল", "গাছের পাতা", "নদীর জল"])
    assert scheme.pattern == "---"
    assert scheme.rhymed_share == 0.0


def test_alternating_scheme():
    scheme = rhyme_scheme(["বুকে", "ভুলি", "মুখে", "তুলি"])
    assert scheme.pattern == "abab"
