# =============================================================================
# CYBERSLEUTH AI - Text sanitising for the database
# =============================================================================
# PostgreSQL text values cannot contain a NUL byte, and JSONB goes through the
# same rule: a JSON string that contains U+0000 is rejected with
#
#   unsupported Unicode escape sequence
#   DETAIL:  \u0000 cannot be converted to text
#
# That is not a theoretical problem. An Android package routinely carries
# strings such as `http://ns.adobe.com/xap/1.0/\u0000` in its DEX string
# table, and the forensic modules copy such strings into their findings. The
# analysis itself then succeeds, but writing the result into
# `analysis_results.result_data` (a JSONB column) fails - the whole run is
# reported as "Analysis failed" although the module found plenty.
#
# The functions below walk a result structure and remove the characters that
# PostgreSQL cannot store, so a finding is reported as it is instead of
# breaking the write.
# =============================================================================

from __future__ import annotations

from typing import Any, Dict, List

# Characters that cannot be stored in a PostgreSQL text value.
# NUL is the one that occurs in practice; the other C0 controls and the
# surrogate range are removed as well, because they break the JSON parser or
# make the findings unreadable.
_FORBIDDEN = {chr(0), chr(1), chr(2), chr(3), chr(4), chr(5), chr(6), chr(7),
              chr(8), chr(11), chr(12), chr(14), chr(15), chr(16), chr(17),
              chr(18), chr(19), chr(20), chr(21), chr(22), chr(23), chr(24),
              chr(25), chr(26), chr(27), chr(28), chr(29), chr(30), chr(31)}

# str.translate() looks the keys up by Unicode ordinal, so the mapping is
# built from ord() and not from the characters themselves.
_TRANSLATION = {ord(code): None for code in _FORBIDDEN}


def clean_text(value: str) -> str:
    """Remove the characters PostgreSQL cannot store from a string."""
    if not value:
        return value

    cleaned = value.translate(_TRANSLATION)

    # Lone surrogates break the JSON encoder as well.
    if any(0xD800 <= ord(char) <= 0xDFFF for char in cleaned):
        cleaned = "".join(
            char for char in cleaned if not (0xD800 <= ord(char) <= 0xDFFF)
        )

    return cleaned


def sanitize_json_value(value: Any) -> Any:
    """Recursively clean every string inside a JSON-compatible structure.

    Dictionaries and lists are rebuilt, so the original structure is not
    modified in place.
    """
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, dict):
        return {clean_text(str(key)): sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, bytes):
        return clean_text(value.decode("utf-8", errors="replace"))
    return clean_text(str(value))
