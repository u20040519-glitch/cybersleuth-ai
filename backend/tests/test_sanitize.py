"""Regression tests for the characters PostgreSQL cannot store.

An Android package routinely carries strings with a NUL byte in its string
table (`http://ns.adobe.com/xap/1.0/\u0000` for instance). The analysis
itself succeeds, but writing the result into `analysis_results.result_data`
(a JSONB column) fails with

    unsupported Unicode escape sequence
    DETAIL:  \\u0000 cannot be converted to text

which the API reported as "Analysis failed" although the module had done its
work. The tests below pin the behaviour of the sanitiser that prevents it.
"""

import json

from app.services.sanitize import clean_text, sanitize_json_value


def test_clean_text_removes_the_nul_byte():
    assert "\x00" not in clean_text("http://ns.adobe.com/xap/1.0/\x00")
    assert clean_text("http://ns.adobe.com/xap/1.0/\x00") == "http://ns.adobe.com/xap/1.0/"


def test_clean_text_keeps_the_rest_of_the_string():
    text = "Stalkerware \u2014 detected on \u00e4 device"
    assert clean_text(text) == text


def test_clean_text_removes_the_other_control_characters():
    assert clean_text("a\x01b\x1fc") == "abc"
    assert clean_text("keeps\ttabs\nand\nnewlines") == "keeps\ttabs\nand\nnewlines"


def test_sanitize_json_value_walks_the_whole_structure():
    result = {
        "findings": [{"value": {"urls": ["http://example.com/\x00"]}}],
        "metadata": {"nested": {"list": ["a\x00b", {"deep": "c\x00d"}]}},
        "count": 3,
        "score": 1.5,
        "flag": True,
        "nothing": None,
    }

    cleaned = sanitize_json_value(result)

    payload = json.dumps(cleaned)  # must not raise
    assert "\x00" not in payload
    assert cleaned["findings"][0]["value"]["urls"] == ["http://example.com/"]
    assert cleaned["metadata"]["nested"]["list"][1]["deep"] == "cd"
    assert cleaned["count"] == 3
    assert cleaned["score"] == 1.5
    assert cleaned["flag"] is True
    assert cleaned["nothing"] is None


def test_sanitize_json_value_does_not_change_the_original():
    original = {"urls": ["http://example.com/\x00"]}
    sanitize_json_value(original)
    assert "\x00" in original["urls"][0]


def test_sanitize_json_value_handles_bytes_and_unknown_types():
    cleaned = sanitize_json_value({"blob": b"a\x00b", "obj": object()})
    assert cleaned["blob"] == "ab"
    assert isinstance(cleaned["obj"], str)
