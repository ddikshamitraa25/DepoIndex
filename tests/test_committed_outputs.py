from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
SOURCE_ID_RE = re.compile(r"^P\d+:L\d+$")


def _topics():
    path = OUTPUTS / "topic_index.json"
    assert path.exists(), "outputs/topic_index.json must be committed"
    return json.loads(path.read_text(encoding="utf-8"))


def _completeness():
    path = OUTPUTS / "completeness_report.json"
    assert path.exists(), "outputs/completeness_report.json must be committed"
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_topic_index_count_and_ids():
    topics = _topics()
    assert len(topics) == 29
    ids = [t["topic_id"] for t in topics]
    assert ids == [f"T{i:03d}" for i in range(1, 30)]
    assert len(set(ids)) == 29


def test_committed_topics_are_chronological():
    topics = _topics()
    pairs = [(t["start_page"], t["start_line"], t["end_page"], t["end_line"]) for t in topics]
    assert pairs == sorted(pairs)
    for t in topics:
        assert (t["start_page"], t["start_line"]) <= (t["end_page"], t["end_line"])


def test_committed_topics_have_valid_source_ids_and_evidence():
    required = {
        "topic",
        "start_page",
        "start_line",
        "end_page",
        "end_line",
        "supporting_source_reference",
        "supporting_evidence",
        "source_ids",
        "topic_id",
    }
    topics = _topics()
    for t in topics:
        assert required <= set(t)
        assert t["source_ids"]
        assert t["supporting_evidence"].strip()
        assert t["supporting_source_reference"].strip()
        for sid in t["source_ids"]:
            assert SOURCE_ID_RE.match(sid), sid
        start_id = f"P{t['start_page']}:L{t['start_line']}"
        end_id = f"P{t['end_page']}:L{t['end_line']}"
        assert t["source_ids"][0] == start_id
        assert t["source_ids"][-1] == end_id


def test_committed_topics_have_no_duplicate_line_assignments():
    seen = {}
    for t in _topics():
        for sid in t["source_ids"]:
            assert sid not in seen, f"{sid} assigned to both {seen[sid]} and {t['topic_id']}"
            seen[sid] = t["topic_id"]


def test_committed_completeness_matches_known_run():
    report = _completeness()
    assert report["total_pdf_pages"] == 122
    assert report["testimony_page_start"] == 7
    assert report["testimony_page_end"] == 88
    assert len(report["testimony_pages"]) == 82
    assert report["extracted_lines"] == 2233
    assert report["extracted_testimony_lines"] == 2042
    assert report["chunks_created"] == 43
    assert report["gaps_detected"] == []
    assert report["duplicate_lines"] == []


def test_run_summary_matches_committed_index():
    summary = json.loads((OUTPUTS / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["topic_count"] == 29
    assert summary["extracted_lines"] == 2233
    assert summary["testimony_lines"] == 2042
    assert summary["chunks"] == 43
    assert summary["llm_provider"] == "none"
    assert summary["testimony_page_start"] == 7
    assert summary["testimony_page_end"] == 88


def test_json_markdown_topic_count_consistency():
    topics = _topics()
    md = (OUTPUTS / "topic_index.md").read_text(encoding="utf-8")
    for t in topics:
        start = f"P{t['start_page']}:L{t['start_line']}"
        end = f"P{t['end_page']}:L{t['end_line']}"
        assert start in md
        assert end in md


def test_no_recurrence_links_in_submitted_index():
    topics = _topics()
    assert all(t.get("recurrence_of") in (None, "") for t in topics)
    assert all(t.get("related_topic_ids") in ([], None) for t in topics)


def test_manual_validation_sample_size():
    path = ROOT / "validation" / "manual_validation_report.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["entries_reviewed"] == 25
    assert len(data["evaluations"]) == 25
    assert data["metrics"]["location_accuracy_pct"] == 100.0
    assert "95.5" not in json.dumps(data)
