from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
TRANSCRIPT = OUTPUTS / "canonical_transcript.json"


@pytest.fixture
def client():
    return TestClient(main.app)


def test_root_and_committed_topic_list(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "DepoIndex" in res.text

    res = client.get("/api/topics")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 29
    assert len(data["topics"]) == 29
    assert "transcript_available" in data

    res = client.get("/api/search?q=PEAKS")
    assert res.status_code == 200
    assert len(res.json()["results"]) > 0

    res = client.get("/api/completeness")
    assert res.status_code == 200
    assert res.json()["extracted_testimony_lines"] == 2042

    res = client.get("/api/validation")
    assert res.status_code == 200
    assert res.json()["available"] is True
    assert res.json()["entries_reviewed"] == 25


def test_topic_detail_without_transcript(monkeypatch, tmp_path):
    dest = tmp_path / "outputs"
    dest.mkdir()
    for name in ("topic_index.json", "completeness_report.json"):
        (dest / name).write_text((OUTPUTS / name).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(main, "OUTPUTS", dest)
    client = TestClient(main.app)

    res = client.get("/api/topics/T001")
    assert res.status_code == 200
    data = res.json()
    assert data["topic"]["topic_id"] == "T001"
    assert data["transcript_available"] is False
    assert data["source_lines"] == []
    assert "intentionally excluded" in data["transcript_unavailable_reason"]
    assert data["topic"]["start_page"] == 7
    assert data["topic"]["source_ids"]
    assert data["topic"]["supporting_evidence"]

    res = client.get("/api/topics/T029")
    assert res.status_code == 200
    data = res.json()
    assert data["topic"]["topic_id"] == "T029"
    assert data["transcript_available"] is False
    assert data["source_lines"] == []

    res = client.get("/api/provenance/check?topic_id=T001")
    assert res.status_code == 200
    prov = res.json()
    assert prov["verification_status"] == "unavailable"
    assert prov["verification_available"] is False
    assert prov["transcript_available"] is False
    assert prov["ok"] is False
    assert "intentionally excluded" in prov["reason"]
    assert "source_lines" not in prov or not prov.get("source_lines")


def test_topic_detail_with_synthetic_transcript(monkeypatch, tmp_path):
    dest = tmp_path / "outputs"
    dest.mkdir()
    topic = {
        "topic_id": "T001",
        "topic": "Synthetic API fixture topic",
        "start_page": 7,
        "start_line": 1,
        "end_page": 7,
        "end_line": 2,
        "supporting_source_reference": "Synthetic fixture P7:L1 - P7:L2",
        "supporting_evidence": "Synthetic evidence only for API path coverage.",
        "source_ids": ["P7:L1", "P7:L2"],
        "related_topic_ids": [],
        "recurrence_of": None,
        "is_procedural": False,
        "confidence": 0.55,
    }
    transcript = {
        "lines": [
            {
                "page": 7,
                "line": 1,
                "source_id": "P7:L1",
                "speaker": "Q",
                "text": "SYNTHETIC_FIXTURE_LINE_ONE",
            },
            {
                "page": 7,
                "line": 2,
                "source_id": "P7:L2",
                "speaker": "A",
                "text": "SYNTHETIC_FIXTURE_LINE_TWO",
            },
        ]
    }
    (dest / "topic_index.json").write_text(json.dumps([topic]), encoding="utf-8")
    (dest / "canonical_transcript.json").write_text(json.dumps(transcript), encoding="utf-8")
    monkeypatch.setattr(main, "OUTPUTS", dest)
    client = TestClient(main.app)

    res = client.get("/api/topics/T001")
    assert res.status_code == 200
    data = res.json()
    assert data["transcript_available"] is True
    assert [ln["text"] for ln in data["source_lines"]] == [
        "SYNTHETIC_FIXTURE_LINE_ONE",
        "SYNTHETIC_FIXTURE_LINE_TWO",
    ]

    res = client.get("/api/provenance/check?topic_id=T001")
    assert res.status_code == 200
    prov = res.json()
    assert prov["transcript_available"] is True
    assert prov["verification_available"] is True
    assert prov["verification_status"] == "verified"
    assert prov["ok"] is True
    assert prov["line_count"] == 2
    assert prov["start_exists"] is True
    assert prov["end_exists"] is True


@pytest.mark.requires_transcript
def test_real_transcript_source_viewer_if_present(client):
    if not TRANSCRIPT.exists():
        pytest.skip(
            "outputs/canonical_transcript.json is absent (reproducible artifact, gitignored)"
        )
    res = client.get("/api/topics/T001")
    assert res.status_code == 200
    data = res.json()
    assert data["transcript_available"] is True
    assert len(data["source_lines"]) > 0
    assert all(ln.get("source_id") for ln in data["source_lines"])

    res = client.get("/api/provenance/check?topic_id=T001")
    assert res.status_code == 200
    prov = res.json()
    assert prov["verification_status"] == "verified"
    assert prov["ok"] is True
