from __future__ import annotations

from src.extraction.models import CanonicalTranscript, TopicRecord
from src.provenance.ids import make_source_id


class ProvenanceError(ValueError):
    pass


class ProvenanceValidator:
    def __init__(self, transcript: CanonicalTranscript):
        self.transcript = transcript
        self.by_id = transcript.line_index()
        self.by_loc = transcript.by_page_line()

    def loc_exists(self, page: int, line: int) -> bool:
        return (page, line) in self.by_loc

    def validate_topic(self, topic: TopicRecord) -> tuple[bool, list[str]]:
        notes: list[str] = []
        if not self.loc_exists(topic.start_page, topic.start_line):
            notes.append(f"start does not exist: {make_source_id(topic.start_page, topic.start_line)}")
        if not self.loc_exists(topic.end_page, topic.end_line):
            notes.append(f"end does not exist: {make_source_id(topic.end_page, topic.end_line)}")
        start = (topic.start_page, topic.start_line)
        end = (topic.end_page, topic.end_line)
        if start > end:
            notes.append("start is after end")
        for sid in topic.source_ids:
            if sid not in self.by_id:
                notes.append(f"unknown source_id {sid}")
                break
        if topic.supporting_evidence:
            # Evidence must be drawn from source text in the span
            span_text = " ".join(
                ln.text for ln in self.transcript.lines if start <= (ln.page, ln.line) <= end
            ).lower()
            tokens = [t for t in topic.supporting_evidence.lower().split() if len(t) > 4][:12]
            hits = sum(1 for t in tokens if t.strip(".,;:…") in span_text)
            if tokens and hits < max(1, len(tokens) // 4):
                notes.append("supporting_evidence does not match source span text")
        return (len(notes) == 0), notes

    def clamp_boundary(self, page: int, line: int) -> tuple[int, int] | None:
        if self.loc_exists(page, line):
            return page, line
        # nearest existing line on same page
        same = [ln for ln in self.transcript.lines if ln.page == page]
        if not same:
            pages = sorted({ln.page for ln in self.transcript.lines})
            if not pages:
                return None
            page = min(pages, key=lambda p: abs(p - page))
            same = [ln for ln in self.transcript.lines if ln.page == page]
        nearest = min(same, key=lambda ln: abs(ln.line - line))
        return nearest.page, nearest.line


def validate_topics(transcript: CanonicalTranscript, topics: list[TopicRecord]) -> list[TopicRecord]:
    v = ProvenanceValidator(transcript)
    kept: list[TopicRecord] = []
    for topic in topics:
        ok, notes = v.validate_topic(topic)
        topic.provenance_ok = ok
        topic.provenance_notes = notes
        if not ok:
            start = v.clamp_boundary(topic.start_page, topic.start_line)
            end = v.clamp_boundary(topic.end_page, topic.end_line)
            if start and end and start <= end:
                topic.start_page, topic.start_line = start
                topic.end_page, topic.end_line = end
                ok2, notes2 = v.validate_topic(topic)
                topic.provenance_ok = ok2
                topic.provenance_notes = notes2
                if ok2:
                    kept.append(topic)
            continue
        kept.append(topic)
    return kept
