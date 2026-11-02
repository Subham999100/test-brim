"""Activation codes and temporary passwords for the Organisation Portal (docs/ORGANISATION_PORTAL.md).

Codes look like CLY-XXXX-XXXX-XXXX-XXXX: 16 characters from a 32-symbol alphabet without the look-alikes
0/O/1/I, i.e. 80 bits from `secrets`. Only the SHA-256 of the normalised code is stored. Neither codes nor
temporary passwords are ever logged or written to the audit log.
"""

import hashlib
import re
import secrets
from typing import Optional

CODE_PREFIX = "CLY"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 32 symbols: 5 bits each
CODE_GROUPS = 4
CODE_GROUP_SIZE = 4
CODE_BODY_LENGTH = CODE_GROUPS * CODE_GROUP_SIZE  # 16 symbols = 80 bits
_SEPARATORS = re.compile(r"[\s\-‐-―−]+")

# Temporary passwords: no look-alike characters, 16 symbols (~94 bits); within the 12-72 byte password rule.
TEMP_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
TEMP_PASSWORD_LENGTH = 16


def _format(body: str) -> str:
    groups = [body[i:i + CODE_GROUP_SIZE] for i in range(0, CODE_BODY_LENGTH, CODE_GROUP_SIZE)]
    return "-".join([CODE_PREFIX, *groups])


def generate_activation_code() -> str:
    return _format("".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_BODY_LENGTH)))


def normalise_activation_code(raw: Optional[str]) -> Optional[str]:
    """Canonical CLY-XXXX-XXXX-XXXX-XXXX form, or None when the input cannot be a code.

    Upper-cases, removes spaces and hyphens and re-inserts the prefix, so "cly abcd-efgh..." and
    "ABCDEFGH..." (without the prefix) both match."""
    if not raw or len(raw) > 100:
        return None
    compact = _SEPARATORS.sub("", raw).upper()
    if len(compact) == len(CODE_PREFIX) + CODE_BODY_LENGTH and compact.startswith(CODE_PREFIX):
        compact = compact[len(CODE_PREFIX):]
    if len(compact) != CODE_BODY_LENGTH or any(ch not in CODE_ALPHABET for ch in compact):
        return None
    return _format(compact)


def hash_activation_code(normalised_code: str) -> str:
    return hashlib.sha256(normalised_code.encode("ascii")).hexdigest()


def activation_code_hint(normalised_code: str) -> str:
    return normalised_code[-4:]


def generate_temporary_password() -> str:
    return "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(TEMP_PASSWORD_LENGTH))


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug[:120] or "organisation"
