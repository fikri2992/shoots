"""Catalogue integrity: ids, Evidence rules, and legacy metadata are valid."""

import pytest

from app.domain import taxonomy
from app.domain.entities import ExifRule
from app.domain.taxonomy import EXIF_RULE_KEYS, TECHNIQUES, TaxonomyError


def test_catalogue_is_valid():
    taxonomy.validate()


def test_exif_rule_keys_mirror_entity():
    assert frozenset(ExifRule.model_fields) == EXIF_RULE_KEYS


def test_every_exif_rule_builds_an_exif_rule():
    for t in TECHNIQUES:
        ExifRule(**t.exif)


def test_get_unknown_raises():
    with pytest.raises(TaxonomyError):
        taxonomy.get("nope")


def test_size_is_in_the_useful_range():
    # Finite enough that every model output can be validated against it.
    assert 55 <= len(TECHNIQUES) <= 90
