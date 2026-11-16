"""Forensic module endpoints and correlation engine logic."""

import io
import json

from app.correlation import engine as correlation_engine

from .conftest import sample_jpeg_bytes, sample_wav_bytes


async def test_deeptrace_analyzes_jpeg(client, investigator, uploaded_jpeg):
    response = await client.post(
        "/api/deeptrace/analyze",
        json={"evidence_id": uploaded_jpeg["id"], "options": {}},
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    result = body["result_data"]
    assert result["module"] == "deeptrace"
    assert result["sha256"] == uploaded_jpeg["sha256_hash"]
    assert isinstance(result["findings"], list) and result["findings"]


async def test_cybersleuth_analyzes_chat_json(client, investigator, case):
    chat = [
        {"timestamp": "2026-11-08T20:14:02Z", "from": "Meena", "message": "ping me at meena@example.com about https://evil.example.com/payload"},
        {"timestamp": "2026-11-08T20:15:37Z", "from": "R", "message": "got it, sha256 59c65a93d5ac09256e7cbfbe268676367ad7c5d65acc9255ac1c53f7bdb0ce2d"},
    ]
    upload = await client.post(
        "/api/evidence/upload",
        files={"file": ("chat.json", json.dumps(chat).encode(), "application/json")},
        data={"investigation_id": case["id"]},
        headers=investigator["headers"],
    )
    assert upload.status_code == 201
    evidence_id = upload.json()["id"]

    response = await client.post(
        "/api/cybersleuth/analyze",
        json={"evidence_id": evidence_id, "options": {}},
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    result = response.json()["result_data"]
    assert result["status"] == "completed"
    assert result["metadata"]["records"]["structure"] == "json-chat"
    assert result["metadata"]["regex_counts"]["emails"] >= 1
    assert result["metadata"]["records"]["timeline_events"] == 2


async def test_analyze_requires_accessible_evidence(client, investigator):
    response = await client.post(
        "/api/deeptrace/analyze",
        json={"evidence_id": "00000000-0000-0000-0000-000000000000", "options": {}},
        headers=investigator["headers"],
    )
    assert response.status_code == 404


async def test_analysis_result_with_a_nul_byte_is_stored(
    client, investigator, uploaded_jpeg, monkeypatch
):
    """A NUL byte in a finding must not break the write of the result.

    PostgreSQL cannot hold a NUL byte inside a text value, and `result_data`
    is a JSONB column. Packages carry such strings in their string tables
    (`http://ns.adobe.com/xap/1.0/\\u0000`), and the analysis used to fail
    with "unsupported Unicode escape sequence" while the module had already
    done its work.
    """
    from app.api import analysis as analysis_api

    def analyzer_with_nul(file_path, options):
        return {
            "module": "deeptrace",
            "status": "completed",
            "summary": "embedded endpoint http://ns.adobe.com/xap/1.0/\x00",
            "confidence_score": 0.5,
            "filename": "sample.jpg",
            "sha256": "0" * 64,
            "mime": "image/jpeg",
            "dimensions": None,
            "findings": [
                {
                    "label": "Embedded network endpoints",
                    "detail": "http://ns.adobe.com/xap/1.0/\x00",
                    "method": "measured",
                    "severity": "high",
                    "value": {"urls": ["http://ns.adobe.com/xap/1.0/\x00"]},
                }
            ],
            "timeline": [],
            "metadata": {"network_strings": {"urls": ["http://ns.adobe.com/xap/1.0/\x00"]}},
            "derived_files": [],
        }

    monkeypatch.setattr(
        analysis_api, "_load_analyzer", lambda module: (analyzer_with_nul, True)
    )

    response = await client.post(
        "/api/deeptrace/analyze",
        json={"evidence_id": uploaded_jpeg["id"], "options": {}},
        headers=investigator["headers"],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"

    urls = body["result_data"]["findings"][0]["value"]["urls"]
    assert urls == ["http://ns.adobe.com/xap/1.0/"]
    assert "\x00" not in json.dumps(body)

    # The row is really in the database and can be read back.
    listed = await client.get(
        "/api/analysis/results",
        params={"evidence_id": uploaded_jpeg["id"]},
        headers=investigator["headers"],
    )
    assert listed.status_code == 200
    assert any(row["id"] == body["id"] for row in listed.json())


async def test_correlation_runs_over_investigation(client, investigator, case, uploaded_jpeg):
    analyze = await client.post(
        "/api/deeptrace/analyze",
        json={"evidence_id": uploaded_jpeg["id"], "options": {}},
        headers=investigator["headers"],
    )
    assert analyze.status_code == 200

    response = await client.post(
        f"/api/correlation/{case['id']}",
        headers=investigator["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["investigation_id"] == case["id"]
    assert isinstance(body["timeline"], list)
    assert isinstance(body["graph"]["nodes"], list)


def test_collect_events_adds_file_hash_entity():
    analyses = [
        {
            "module": "deeptrace",
            "evidence_id": "ev-1",
            "result_data": {
                "sha256": "A" * 64,
                "findings": [
                    {
                        "label": "EXIF present",
                        "detail": "camera metadata exists",
                        "method": "measured",
                        "severity": "info",
                        "value": None,
                    }
                ],
                "timeline": [],
            },
        }
    ]
    events = correlation_engine.collect_events(analyses)
    assert events
    assert any(f"sha256:{'a' * 64}" in event.entities for event in events)


def test_shared_entity_connection_detected():
    analyses = [
        {
            "module": "spytrace",
            "evidence_id": "ev-apk",
            "result_data": {
                "sha256": "b" * 64,
                "timeline": [],
                "findings": [
                    {
                        "label": "Embedded network endpoints",
                        "detail": "Embedded: https://shared.example.com/repo",
                        "method": "measured",
                        "severity": "high",
                        "value": None,
                    }
                ],
            },
        },
        {
            "module": "cybersleuth",
            "evidence_id": "ev-chat",
            "result_data": {
                "sha256": "c" * 64,
                "timeline": [
                    {
                        "timestamp": "2026-11-08T20:14:02+00:00",
                        "label": "Message from R",
                        "source": "chat.json",
                        "details": "R: install it from https://shared.example.com/repo please",
                    }
                ],
                "findings": [],
            },
        },
    ]
    events = correlation_engine.collect_events(analyses)
    connections = correlation_engine.detect_connections(events)
    shared = [c for c in connections if c.connection_type == "shared_entity"]
    assert any("shared.example.com" in c.description for c in shared)


def test_undated_events_do_not_appear_in_timeline():
    analyses = [
        {
            "module": "deeptrace",
            "evidence_id": "ev-1",
            "result_data": {
                "sha256": "d" * 64,
                "findings": [
                    {
                        "label": "Noise profile",
                        "detail": "uniform noise",
                        "method": "measured",
                        "severity": "info",
                        "value": None,
                    }
                ],
                "timeline": [
                    {
                        "timestamp": "2026-11-09T21:14:22+00:00",
                        "label": "EXIF capture",
                        "source": "sample.jpg",
                        "details": "captured",
                    }
                ],
            },
        }
    ]
    events = correlation_engine.collect_events(analyses)
    timeline = correlation_engine.build_timeline(events)
    placed = [row for row in timeline if row["timestamp"]]
    assert len(placed) == 1
    assert placed[0]["label"] == "EXIF capture"


def test_identical_timestamps_produce_timestamp_match():
    analyses = [
        {
            "module": "cybersleuth",
            "evidence_id": "ev-notes",
            "result_data": {
                "sha256": "e" * 64,
                "timeline": [
                    {
                        "timestamp": "2026-11-09T21:14:22+00:00",
                        "label": "note line",
                        "source": "notes.txt",
                        "details": "capture taken",
                    }
                ],
                "findings": [],
            },
        },
        {
            "module": "deeptrace",
            "evidence_id": "ev-chat",
            "result_data": {
                "sha256": "f" * 64,
                "timeline": [
                    {
                        "timestamp": "2026-11-09T21:14:22+00:00",
                        "label": "Message from R",
                        "source": "chat.json",
                        "details": "screenshot taken",
                    }
                ],
                "findings": [],
            },
        },
    ]
    events = correlation_engine.collect_events(analyses)
    connections = correlation_engine.detect_connections(events)
    assert any(c.connection_type == "timestamp_match" for c in connections)
