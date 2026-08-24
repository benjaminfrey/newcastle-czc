"""Tests llm/redact.py — known-token PII substitution, the mandatory front
door for any application content this app sends to a third-party model
(BUILD-STATE "W5", DECISIONS-NEEDED D-0025).

Offline, no network, no LLM, no PII — llm/redact.py is a pure function over
strings the test itself supplies; nothing here touches the DB or a real
case.

Tested BOTH directions per the task brief: real PII is replaced (§A), AND
substantive numbers/dimensions/dates/districts are left untouched (§B) —
plus the two named adversarial cases (§C) and the honest image limitation
(§D).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm.redact import (  # noqa: E402
    ImagePagesNotRedactable,
    KnownTokens,
    RedactionReport,
    redact_text,
    require_operator_ticked_for_image,
    restore_text,
)


# --------------------------------------------------------------------------- #
# §A — real PII IS replaced, one test per class
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "field_name,cls,value,tag",
    [
        ("names", "name", "Robert Shattuck", "NAME"),
        ("addresses", "address", "142 Main Street, Newcastle, ME 04553", "ADDRESS"),
        ("phones", "phone", "(207) 563-1234", "PHONE"),
        ("emails", "email", "rshattuck@example.com", "EMAIL"),
        ("deed_refs", "deed_ref", "Lincoln County Registry of Deeds Book 1234, Page 56", "DEEDREF"),
    ],
)
def test_each_pii_class_is_redacted(field_name, cls, value, tag):
    known = KnownTokens(**{field_name: (value,)})
    text = f"See {value} in the file."
    result = redact_text(text, known)

    assert value not in result.text
    assert f"[REDACTED_{tag}_1]" in result.text
    assert result.report.to_dict()[cls] == {"occurrences": 1, "distinct_tokens": 1}


def test_repeated_occurrence_maps_to_same_placeholder():
    known = KnownTokens(names=("Robert Shattuck",))
    text = "Robert Shattuck is the applicant. Robert Shattuck also owns the lot."
    result = redact_text(text, known)

    assert result.text.count("[REDACTED_NAME_1]") == 2
    assert "Robert Shattuck" not in result.text
    assert result.report.to_dict()["name"] == {"occurrences": 2, "distinct_tokens": 1}


def test_case_insensitive_and_whitespace_tolerant_matching():
    known = KnownTokens(names=("John Smith",))
    text = "Applicant:  JOHN   SMITH\n(signature on file)"
    result = redact_text(text, known)

    assert "JOHN" not in result.text and "SMITH" not in result.text
    assert "[REDACTED_NAME_1]" in result.text


def test_distinct_values_get_distinct_placeholders():
    known = KnownTokens(names=("Robert Shattuck", "Jane Doe"))
    text = "Robert Shattuck (applicant) and Jane Doe (owner)."
    result = redact_text(text, known)

    assert "[REDACTED_NAME_1]" in result.text
    assert "[REDACTED_NAME_2]" in result.text
    assert result.report.to_dict()["name"] == {"occurrences": 2, "distinct_tokens": 2}


# --------------------------------------------------------------------------- #
# §B — numbers, dimensions, dates, districts survive INTACT
# --------------------------------------------------------------------------- #


def test_setback_lot_size_frontage_and_hearing_date_survive_intact():
    known = KnownTokens(
        names=("Robert Shattuck",),
        addresses=("142 Main Street, Newcastle, ME 04553",),
    )
    text = (
        "Applicant Robert Shattuck, residing at "
        "142 Main Street, Newcastle, ME 04553, proposes a rear setback of "
        "25 ft on a lot of 1.2 acres with 150.00 ft of frontage in District "
        "D1. The hearing is scheduled for March 3, 2026."
    )
    result = redact_text(text, known)

    for substantive in ("25 ft", "1.2 acres", "150.00 ft", "District D1", "March 3, 2026"):
        assert substantive in result.text, f"{substantive!r} did not survive redaction"

    assert "Robert Shattuck" not in result.text
    assert "142 Main Street" not in result.text


def test_districts_and_bare_numbers_are_never_a_token_class():
    # There is structurally no way to construct a KnownTokens that redacts
    # a number/date/district — assert the dataclass simply has no such
    # field, so this isn't just an untested convention.
    fields = KnownTokens.__dataclass_fields__
    assert set(fields) == {"names", "addresses", "phones", "emails", "deed_refs"}


def test_unrelated_case_has_nothing_to_redact():
    text = "Setback 25 ft, District SD-Marine, hearing April 14, 2026."
    result = redact_text(text, KnownTokens())
    assert result.text == text
    assert result.report.to_dict() == {}


# --------------------------------------------------------------------------- #
# §C — the two named adversarial cases
# --------------------------------------------------------------------------- #


def test_adversarial_name_and_number_adjacent():
    """A name sits directly next to a substantive number with no
    separating context — the redaction of the name must not bleed into,
    truncate, or otherwise disturb the adjacent number."""
    known = KnownTokens(names=("Jane Q. Public",))
    text = "Applicant Jane Q. Public requests a 25 ft rear setback variance."
    result = redact_text(text, known)

    assert result.text == "Applicant [REDACTED_NAME_1] requests a 25 ft rear setback variance."


def test_adversarial_unknown_street_address_survives_while_known_name_is_redacted():
    """The street address is NOT supplied as a known token — only the name
    is. Per the module's central design principle (known-token
    substitution, not generic NER), the address — including the house
    number embedded in it — must survive completely untouched; only the
    exact known name is replaced."""
    known = KnownTokens(names=("Robert Shattuck",))
    text = "The site at 142 Main Street is owned by Robert Shattuck."
    result = redact_text(text, known)

    assert "142 Main Street" in result.text
    assert "142" in result.text
    assert "Robert Shattuck" not in result.text
    assert result.text == "The site at 142 Main Street is owned by [REDACTED_NAME_1]."


def test_known_address_is_redacted_whole_including_its_house_number():
    """Companion to the adversarial case above: when the SAME address IS
    supplied as a known token (the applicant's own address on file), it is
    redacted as one whole unit — house number included — not left behind
    piecemeal."""
    known = KnownTokens(
        names=("Robert Shattuck",),
        addresses=("142 Main Street, Newcastle, ME 04553",),
    )
    text = (
        "Owned by Robert Shattuck, mailing address "
        "142 Main Street, Newcastle, ME 04553."
    )
    result = redact_text(text, known)

    assert "142" not in result.text
    assert "Main Street" not in result.text
    assert result.text.count("[REDACTED_ADDRESS_1]") == 1
    assert result.text.count("[REDACTED_NAME_1]") == 1


# --------------------------------------------------------------------------- #
# Overlap ordering — a known token embedded inside another known token
# --------------------------------------------------------------------------- #


def test_overlap_longest_match_first():
    known = KnownTokens(names=("Cole",), addresses=("15 Cole Farm Road",))
    text = "Mailing address: 15 Cole Farm Road. Contact: Cole."
    result = redact_text(text, known)

    # the address is replaced whole -- no stray leftover name placeholder
    # embedded inside where the address used to be
    assert "[REDACTED_ADDRESS_1] [REDACTED_NAME_1]" not in result.text
    assert "15 Cole Farm Road" not in result.text
    assert result.text == "Mailing address: [REDACTED_ADDRESS_1]. Contact: [REDACTED_NAME_1]."


def test_month_name_guard():
    """A degenerate 'name' value that is nothing but a calendar month is
    skipped, protecting any real date in the same document from being torn
    in half by a same-word match."""
    known = KnownTokens(names=("May",))
    text = "The hearing is scheduled for May 3, 2026."
    result = redact_text(text, known)

    assert result.text == text
    assert result.report.to_dict() == {}


# --------------------------------------------------------------------------- #
# Report shape — counts only, never values
# --------------------------------------------------------------------------- #


def test_report_never_contains_raw_values():
    known = KnownTokens(
        names=("Robert Shattuck",),
        addresses=("142 Main Street, Newcastle, ME 04553",),
        phones=("(207) 563-1234",),
        emails=("rshattuck@example.com",),
        deed_refs=("Book 1234, Page 56",),
    )
    text = (
        "Robert Shattuck, 142 Main Street, Newcastle, ME 04553, "
        "(207) 563-1234, rshattuck@example.com, Book 1234, Page 56."
    )
    result = redact_text(text, known)

    serialized = json.dumps(result.report.to_dict())
    for secret in (
        "Robert Shattuck", "142 Main Street", "563-1234",
        "rshattuck@example.com", "Book 1234",
    ):
        assert secret not in serialized

    assert result.report.to_dict() == {
        "address": {"occurrences": 1, "distinct_tokens": 1},
        "deed_ref": {"occurrences": 1, "distinct_tokens": 1},
        "email": {"occurrences": 1, "distinct_tokens": 1},
        "name": {"occurrences": 1, "distinct_tokens": 1},
        "phone": {"occurrences": 1, "distinct_tokens": 1},
    }
    assert result.report.total_occurrences == 5


def test_report_is_a_dataclass_of_int_counts_only():
    report = RedactionReport(occurrences={"name": 2}, distinct_tokens={"name": 1})
    for cls_counts in report.to_dict().values():
        for v in cls_counts.values():
            assert isinstance(v, int)


# --------------------------------------------------------------------------- #
# Round trip — a model's answer gets de-redacted before it becomes a candidate
# --------------------------------------------------------------------------- #


def test_round_trip_restore_via_result():
    known = KnownTokens(names=("Robert Shattuck",))
    result = redact_text("Applicant: Robert Shattuck.", known)

    model_answer = f"The applicant of record is {list(result.token_map)[0]}."
    restored = result.restore(model_answer)

    assert restored == "The applicant of record is Robert Shattuck."


def test_round_trip_restore_text_standalone():
    token_map = {"[REDACTED_NAME_1]": "Robert Shattuck", "[REDACTED_ADDRESS_1]": "142 Main Street"}
    answer = "[REDACTED_NAME_1] resides at [REDACTED_ADDRESS_1]."
    assert restore_text(answer, token_map) == "Robert Shattuck resides at 142 Main Street."


def test_restore_leaves_unrecognized_placeholder_untouched():
    # CONTRACT.md §1 S7 -- no silent guessing. A placeholder the model
    # mangled is left alone, not fuzzily matched.
    token_map = {"[REDACTED_NAME_1]": "Robert Shattuck"}
    answer = "The applicant is [redacted_name_1] (lowercased by the model)."
    restored = restore_text(answer, token_map)
    assert restored == answer  # unchanged -- not silently "fixed"


def test_restore_empty_inputs():
    assert restore_text("", {"[REDACTED_NAME_1]": "x"}) == ""
    assert restore_text("hello", {}) == "hello"


# --------------------------------------------------------------------------- #
# KnownTokens.from_field_labels — classification by label, not by value
# --------------------------------------------------------------------------- #


def test_from_field_labels_classifies_by_the_real_worklist_labels():
    pairs = {
        "Applicant": "Robert Shattuck",
        "Applicant Address": "142 Main Street, Newcastle, ME 04553",
        "Applicant Phone": "(207) 563-1234",
        "Applicant Email": "rshattuck@example.com",
        "Property Owner": "Robert Shattuck",
        "Owner Address": "142 Main Street, Newcastle, ME 04553",
        "Owner Deed Reference": "Book 1234, Page 56",
        "Applicant's Agent": "Jane Doe, Esq.",
        # deliberately NOT PII -- must be classified into nothing:
        "Tax Lot": "M003, L059",
        "Acreage": "1.2 acres",
        "Application Date": "2025-10-02",
        "Core Zoning District": "D1",
    }
    known = KnownTokens.from_field_labels(pairs)

    assert "Robert Shattuck" in known.names
    assert "Jane Doe, Esq." in known.names
    assert "142 Main Street, Newcastle, ME 04553" in known.addresses
    assert "(207) 563-1234" in known.phones
    assert "rshattuck@example.com" in known.emails
    assert "Book 1234, Page 56" in known.deed_refs

    all_values = set(known.names) | set(known.addresses) | set(known.phones) | set(known.emails) | set(known.deed_refs)
    for non_pii in ("M003, L059", "1.2 acres", "2025-10-02", "D1"):
        assert non_pii not in all_values


def test_from_field_labels_skips_blank_values():
    known = KnownTokens.from_field_labels({"Applicant": "  ", "Applicant Email": ""})
    assert known.names == ()
    assert known.emails == ()


# --------------------------------------------------------------------------- #
# §D — the honest page-image limitation
# --------------------------------------------------------------------------- #


def test_image_redaction_requires_explicit_operator_tick():
    with pytest.raises(ImagePagesNotRedactable):
        require_operator_ticked_for_image("doc-123", operator_ticked=False)


def test_image_redaction_proceeds_when_operator_ticked():
    # must not raise
    require_operator_ticked_for_image("doc-123", operator_ticked=True)


# --------------------------------------------------------------------------- #
# Empty / degenerate inputs
# --------------------------------------------------------------------------- #


def test_empty_text():
    result = redact_text("", KnownTokens(names=("Robert Shattuck",)))
    assert result.text == ""
    assert result.report.to_dict() == {}
    assert result.token_map == {}


def test_blank_and_duplicate_known_values_are_tolerated():
    known = KnownTokens(names=("Robert Shattuck", "  ", "Robert Shattuck", ""))
    result = redact_text("Robert Shattuck is the applicant.", known)
    assert result.text == "[REDACTED_NAME_1] is the applicant."
    assert result.report.to_dict()["name"] == {"occurrences": 1, "distinct_tokens": 1}
