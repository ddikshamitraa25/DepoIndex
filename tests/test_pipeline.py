from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.extraction.pdf_extract import extract_deposition
from src.provenance.ids import make_range_id, make_source_id, parse_source_id
from src.provenance.validator import ProvenanceValidator
from src.extraction.models import TopicRecord
from src.segmentation.chunking import build_chunks, group_turns
from src.segmentation.topics import segment_topics


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "Persis_Yu_Deposition.pdf"


@pytest.fixture(scope="session")
def transcript():
    if not PDF.exists():
        pytest.skip("Deposition PDF is not present")
    return extract_deposition(str(PDF))


def test_source_id_generation_and_parse():
    assert make_source_id(12, 4) == "P12:L4"
    assert make_range_id(12, 4, 12, 12) == "P12:L4-L12"
    assert make_range_id(24, 1, 25, 25) == "P24:L1-P25:L25"
    assert parse_source_id("P12:L4") == (12, 4, 12, 4)
    assert parse_source_id("P12:L4-L12") == (12, 4, 12, 12)
    assert parse_source_id("P24:L1-P25:L25") == (24, 1, 25, 25)
    with pytest.raises(ValueError):
        parse_source_id("page-12-line-4")


def test_pdf_extraction_page_and_line_numbers(transcript):
    assert transcript.total_pdf_pages == 122
    assert transcript.testimony_page_start is not None
    assert transcript.testimony_page_end is not None
    assert transcript.testimony_page_start <= 12
    assert transcript.testimony_page_end >= 80
    testimony = [ln for ln in transcript.lines if ln.is_testimony]
    assert len(testimony) > 1000
    # Canonical IDs must match extracted page/line, never invented
    for ln in testimony[:50]:
        assert ln.source_id == f"P{ln.page}:L{ln.line}"
        assert 1 <= ln.line <= 25
    # Known line from inspection of the PDF
    loc = transcript.by_page_line()
    assert (7, 12) in loc
    assert "Good afternoon" in loc[(7, 12)].text
    assert loc[(7, 12)].speaker == "Q"


def test_missing_and_duplicate_line_detection(transcript):
    testimony_pages = [
        p
        for p in transcript.pages
        if p.transcript_page
        and transcript.testimony_page_start <= p.transcript_page <= transcript.testimony_page_end
        and p.page_role == "transcript"
    ]
    assert testimony_pages
    for p in testimony_pages:
        if p.duplicate_lines:
            assert isinstance(p.duplicate_lines, list)
        assert isinstance(p.missing_lines, list)


def test_provenance_rejects_invalid_boundaries(transcript):
    v = ProvenanceValidator(transcript)
    bad = TopicRecord(
        topic_id="Tbad",
        topic="invented",
        start_page=999,
        start_line=1,
        end_page=999,
        end_line=2,
        supporting_source_reference="x",
        supporting_evidence="nope",
        source_ids=["P999:L1"],
    )
    ok, notes = v.validate_topic(bad)
    assert ok is False
    assert notes


def test_provenance_accepts_real_span(transcript):
    ln = next(x for x in transcript.lines if x.is_testimony and x.text.strip())
    v = ProvenanceValidator(transcript)
    rec = TopicRecord(
        topic_id="Tok",
        topic="sample",
        start_page=ln.page,
        start_line=ln.line,
        end_page=ln.page,
        end_line=ln.line,
        supporting_source_reference="Persis Yu Deposition " + ln.source_id,
        supporting_evidence=ln.text[:80],
        source_ids=[ln.source_id],
    )
    ok, notes = v.validate_topic(rec)
    assert ok, notes


def test_chronological_topic_order(transcript):
    chunks = build_chunks(transcript)
    topics = segment_topics(transcript, chunks)
    assert topics
    pairs = [(t.start_page, t.start_line) for t in topics]
    assert pairs == sorted(pairs)


def test_json_structure_of_topics(transcript):
    topics = segment_topics(transcript, build_chunks(transcript))
    required = {
        "topic",
        "start_page",
        "start_line",
        "end_page",
        "end_line",
        "supporting_source_reference",
        "supporting_evidence",
        "source_ids",
    }
    for t in topics:
        entry = t.to_index_entry()
        assert required <= set(entry)
        assert isinstance(entry["source_ids"], list)
        assert entry["source_ids"]
        json.dumps(entry)


def test_turns_have_speakers(transcript):
    testimony = [ln for ln in transcript.lines if ln.is_testimony]
    turns = group_turns(testimony)
    assert turns
    speakers = {t.speaker_kind for t in turns}
    assert "Q" in speakers
    assert "A" in speakers or "WITNESS" in speakers


def test_geometric_speaker_parsing(transcript):
    loc = transcript.by_page_line()
    # P9:L20 is counsel continuation starting with 'A couple other questions now.'
    assert (9, 20) in loc
    assert loc[(9, 20)].speaker == "Q"
    assert loc[(9, 20)].text.startswith("A couple other questions now.")
    # P25:L24 is witness answer starting with 'A small handful of times.'
    assert (25, 24) in loc
    assert loc[(25, 24)].speaker == "A"
    assert loc[(25, 24)].text.startswith("A small handful of times.")


def test_completeness_report_coverage(transcript):
    chunks = build_chunks(transcript)
    from src.validation.completeness import build_completeness_report
    report = build_completeness_report(transcript, chunks)
    assert report["total_pdf_pages"] == 122
    assert report["testimony_page_start"] == 7
    assert report["testimony_page_end"] == 88
    assert len(report["testimony_pages"]) == 82
    assert report["extracted_testimony_lines"] == 2042
    assert len(report["gaps_detected"]) == 0
    assert len(report["duplicate_lines"]) == 0


def test_all_generated_topics_pass_provenance(transcript):
    v = ProvenanceValidator(transcript)
    topics_file = ROOT / "outputs" / "topic_index.json"
    if not topics_file.exists():
        pytest.skip("outputs/topic_index.json not yet generated")
    topics_raw = json.loads(topics_file.read_text(encoding="utf-8"))
    for tr in topics_raw:
        rec = TopicRecord(**tr)
        ok, notes = v.validate_topic(rec)
        assert ok, f"Topic {rec.topic_id} failed provenance: {notes}"


def test_gap_detection_logic(transcript):
    # Simulate a copy of transcript with a dropped line
    from src.validation.completeness import build_completeness_report
    copy_lines = [ln for ln in transcript.lines if ln.source_id != "P15:L10"]
    transcript_copy = transcript.model_copy(update={"lines": copy_lines})
    chunks = build_chunks(transcript)
    report = build_completeness_report(transcript_copy, chunks)
    missing_pages = [g["page"] for g in report["gaps_detected"]]
    assert 15 in missing_pages


def test_fastapi_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    res = client.get("/")
    assert res.status_code == 200
    assert "DepoIndex" in res.text
    
    res = client.get("/api/topics")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 29
    assert len(data["topics"]) == 29
    
    res = client.get("/api/topics/T001")
    assert res.status_code == 200
    detail = res.json()
    assert detail["topic"]["topic_id"] == "T001"
    assert len(detail["source_lines"]) > 0
    
    res = client.get("/api/search?q=PEAKS")
    assert res.status_code == 200
    search_res = res.json()
    assert len(search_res["results"]) > 0
    
    res = client.get("/api/completeness")
    assert res.status_code == 200
    assert res.json()["extracted_testimony_lines"] == 2042
    
    res = client.get("/api/validation")
    assert res.status_code == 200
    assert res.json()["available"] is True
    assert res.json()["entries_reviewed"] >= 20
    
    res = client.get("/api/provenance/check?topic_id=T001")
    assert res.status_code == 200
    assert res.json()["ok"] is True
