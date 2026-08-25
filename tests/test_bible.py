import pytest

from videopsalm import BibleCatalog, BibleReference, BibleTranslation, parse_reference


def test_parse_written_and_spoken_references() -> None:
    assert parse_reference("John 3:16") == BibleReference("John", 3, 16)
    assert parse_reference("Romans chapter 8 verse 1") == BibleReference("Romans", 8, 1)
    assert parse_reference("John 3 verses 16 through 18") == BibleReference("John", 3, 16, 18)


def test_parse_abbreviation_and_context_continuation() -> None:
    reference = parse_reference("Rom 8:1")
    assert reference == BibleReference("Romans", 8, 1)
    assert parse_reference("verse 2", context=reference) == BibleReference("Romans", 8, 2)


def test_catalog_requires_license_for_display() -> None:
    reference = BibleReference("John", 3, 16)
    catalog = BibleCatalog(BibleTranslation("demo", "en", "Demo", licensed=False), {reference: "text"})
    with pytest.raises(PermissionError):
        catalog.lookup(reference)

    licensed = BibleCatalog(BibleTranslation("demo", "en", "Demo", licensed=True), {reference: "text"})
    assert licensed.lookup(reference) == "text"
