"""Catalogue invariants: ids unique, prerequisites exist and are not harder,
exif keys match ExifRule, and every technique is reachable by climbing."""

import pytest

from app.domain import taxonomy
from app.domain.entities import ExifRule
from app.domain.taxonomy import EXIF_RULE_KEYS, TECHNIQUES, Family, TaxonomyError


def test_catalogue_is_valid():
    taxonomy.validate()


def test_exif_rule_keys_mirror_entity():
    assert frozenset(ExifRule.model_fields) == EXIF_RULE_KEYS


def test_every_exif_rule_builds_an_exif_rule():
    for t in TECHNIQUES:
        ExifRule(**t.exif)


def test_level_one_has_no_prerequisites():
    for t in TECHNIQUES:
        if t.level == 1:
            assert t.requires == (), t.id


def test_every_family_has_a_level_one_entry_point():
    for family in Family:
        assert any(t.level == 1 for t in taxonomy.by_family(family)), family


def test_unlocked_from_nothing_is_exactly_the_root_set():
    roots = {t.id for t in taxonomy.unlocked(set())}
    assert roots == {t.id for t in TECHNIQUES if not t.requires}


def test_unlocked_excludes_already_attempted():
    attempted = {"backlight", "golden_hour"}
    ids = {t.id for t in taxonomy.unlocked(attempted)}
    assert "backlight" not in ids
    assert "rim_light" in ids  # requires backlight only
    assert "chiaroscuro" not in ids  # requires low_key and rembrandt


def test_get_unknown_raises():
    with pytest.raises(TaxonomyError):
        taxonomy.get("nope")


def test_size_is_in_the_useful_range():
    # Small enough to be a legible graph, large enough that experiments do not repeat in a month.
    assert 55 <= len(TECHNIQUES) <= 90
