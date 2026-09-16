"""Attribution rules for the corpus fetcher.

These encode a decision, not just behaviour: the corpus takes a poet only when
the copyright term has actually expired, because the dataset is redistributed
under CC BY-SA. Anyone loosening that should have to delete a test that says so.
"""
import datetime as dt

import pytest

from corpus import fetch_wikisource as fw


def test_tagore_resolves_with_a_sourced_rights_line():
    author, rights = fw.attribution("কণিকা (রবীন্দ্রনাথ ঠাকুর)")
    assert author == "Rabindranath Tagore"
    assert "1941" in rights and "public domain" in rights
    assert "Wikisource" in rights


def test_jibanananda_resolves():
    author, rights = fw.attribution("জীবনানন্দ দাশের শ্রেষ্ঠ কবিতা")
    assert author == "Jibanananda Das"
    assert "1954" in rights
    assert "2015" in rights          # life + 60, so free from 2015


def test_unlisted_poet_is_refused_rather_than_guessed():
    with pytest.raises(ValueError, match="no poet matches"):
        fw.attribution("Some Collection Nobody Registered")


def test_poet_still_in_copyright_is_refused(monkeypatch):
    """Nazrul (d. 1976) is out until 2037 — the reason he is not in the corpus."""
    monkeypatch.setattr(fw, "POETS", [("কাজী নজরুল ইসলাম", "Kazi Nazrul Islam", 1976)])
    with pytest.raises(ValueError, match="in copyright until 2037"):
        fw.attribution("অগ্নি-বীণা (কাজী নজরুল ইসলাম)", today=dt.date(2026, 9, 16))


def test_term_expiry_is_computed_not_hardcoded():
    """The same poet becomes fetchable once the term runs out."""
    monkeypatch_poets = [("কাজী নজরুল ইসলাম", "Kazi Nazrul Islam", 1976)]
    original = fw.POETS
    fw.POETS = monkeypatch_poets
    try:
        with pytest.raises(ValueError):
            fw.attribution("অগ্নি-বীণা (কাজী নজরুল ইসলাম)", today=dt.date(2036, 12, 31))
        author, rights = fw.attribution(
            "অগ্নি-বীণা (কাজী নজরুল ইসলাম)", today=dt.date(2037, 1, 1)
        )
        assert author == "Kazi Nazrul Islam"
        assert "2037" in rights
    finally:
        fw.POETS = original


def test_poem_id_keeps_the_bengali():
    assert fw.poem_id("কণিকা (রবীন্দ্রনাথ ঠাকুর)/অধিকার") == "কণিকা-অধিকার"
