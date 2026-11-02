"""Organisation Portal pure units: the topic categoriser, activation codes and temporary passwords."""

import re

import pytest

from backend.app.services.org_categoriser import CATEGORIES, CATEGORY_KEYS, categorise, category_label
from backend.app.services.org_credentials import (
    CODE_ALPHABET,
    activation_code_hint,
    generate_activation_code,
    generate_temporary_password,
    hash_activation_code,
    normalise_activation_code,
    slugify,
)

CODE_FORMAT = re.compile(r"^CLY-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$")


def test_categories_match_the_contract():
    assert CATEGORY_KEYS == ("cc", "ci", "som", "fica", "integration", "troubleshooting", "architecture", "general")
    assert dict(CATEGORIES)["fica"] == "FI-CA"
    assert category_label("unknown") == "General SAP"


@pytest.mark.parametrize("question, answer, expected", [
    ("Billing documents are not generated after the billing run", "", "troubleshooting"),
    ("Why does the CC rating fail with error 42?", "", "troubleshooting"),
    ("How do I reprocess stuck consumption items?", "", "troubleshooting"),
    ("Billing completed but no invoicing document was created in Convergent Invoicing. What should I check?",
     "", "troubleshooting"),
    ("Why wasn't the invoice posted to FI-CA?", "", "troubleshooting"),
    ("The billing run didn't generate billable items for one contract", "", "troubleshooting"),
    ("Billable items are missing after the rating run", "", "troubleshooting"),
    ("How do I fix a blocked contract account in FI-CA?", "", "troubleshooting"),
    ("When are billable items created in Convergent Invoicing?", "", "ci"),
    # Integration needs two *named* components; "invoicing documents" is a CI term, not a name.
    ("How are invoicing documents posted to FI-CA contract accounts?", "", "fica"),
    ("How does CC hand charged items to CI?", "", "integration"),
    ("Explain the end-to-end flow from SOM to FI-CA", "", "integration"),
    ("Which IDoc carries the provider contract?", "", "integration"),
    ("How are charge plans and price plans used?", "", "cc"),
    ("What is a billable item class in Convergent Invoicing?", "", "ci"),
    ("How do subscription orders change a solution quote?", "", "som"),
    ("How does dunning work for contract accounts?", "", "fica"),
    ("How do I configure number ranges in SPRO?", "", "architecture"),
    ("What is the recommended system architecture?", "", "architecture"),
    ("What is SAP?", "SAP is an enterprise software company.", "general"),
])
def test_categorise_follows_the_documented_order(question, answer, expected):
    assert categorise(question, answer) == expected


def test_answer_text_adds_component_weight_but_does_not_make_a_question_troubleshooting():
    assert categorise("Explain the master data", "Contract accounts and dunning in FI-CA ...") == "fica"
    assert categorise("Explain the master data", "An error can occur if ... the issue is ...") == "general"


def test_generated_codes_have_the_documented_format_and_are_unique():
    codes = {generate_activation_code() for _ in range(200)}
    assert len(codes) == 200
    for code in codes:
        assert CODE_FORMAT.match(code)
        assert not set(code[4:].replace("-", "")) & set("01OI")
    assert len(CODE_ALPHABET) == 32 and len(set(CODE_ALPHABET)) == 32  # 16 symbols * 5 bits = 80 bits


def test_normalisation_accepts_spacing_case_and_missing_prefix():
    code = generate_activation_code()
    body = code[4:].replace("-", "")
    variants = [code, code.lower(), f"  {code}  ", body, body.lower(), " ".join(body), f"cly {body[:8]} {body[8:]}",
                code.replace("-", "‐")]
    assert {normalise_activation_code(variant) for variant in variants} == {code}


@pytest.mark.parametrize("raw", ["", None, "CLY-AAAA-AAAA-AAAA", "CLY-AAAA-AAAA-AAAA-AAA0", "CLY-OOOO-1111-IIII-AAAA",
                                 "XYZ-AAAA-AAAA-AAAA-AAAA", "A" * 101, "CLY-AAAA-AAAA-AAAA-AAAA-AAAA"])
def test_normalisation_rejects_impossible_codes(raw):
    assert normalise_activation_code(raw) is None


def test_hash_and_hint_never_contain_the_full_code():
    code = generate_activation_code()
    digest = hash_activation_code(code)
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert digest == hash_activation_code(normalise_activation_code(code.lower()))
    assert activation_code_hint(code) == code[-4:]


def test_temporary_passwords_meet_the_password_rules():
    passwords = {generate_temporary_password() for _ in range(100)}
    assert len(passwords) == 100
    for password in passwords:
        assert 12 <= len(password.encode("utf-8")) <= 72


def test_slugify():
    assert slugify("  Acme & Sons, GmbH ") == "acme-sons-gmbh"
    assert slugify("!!!") == "organisation"
