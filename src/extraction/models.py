from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SpeakerKind = Literal[
    "Q",
    "A",
    "ATTORNEY",
    "WITNESS",
    "REPORTER",
    "VIDEOGRAPHER",
    "BY",
    "PROCEEDING",
    "UNKNOWN",
]


class CanonicalLine(BaseModel):
    source_id: str
    page: int
    line: int
    speaker: str
    speaker_kind: SpeakerKind
    text: str
    timestamp: str | None = None
    pdf_page_index: int
    page_role: str
    is_testimony: bool = False
    speaker_cue: str | None = None


class ExtractedPage(BaseModel):
    pdf_page_index: int
    transcript_page: int | None
    page_role: str
    line_numbers: list[int]
    missing_lines: list[int]
    duplicate_lines: list[int]
    warnings: list[str] = Field(default_factory=list)
    raw_text: str = ""


class CanonicalTranscript(BaseModel):
    source_pdf: str
    total_pdf_pages: int
    pages: list[ExtractedPage]
    lines: list[CanonicalLine]
    testimony_page_start: int | None = None
    testimony_page_end: int | None = None
    extraction_warnings: list[str] = Field(default_factory=list)

    def line_index(self) -> dict[str, CanonicalLine]:
        return {line.source_id: line for line in self.lines}

    def by_page_line(self) -> dict[tuple[int, int], CanonicalLine]:
        return {(line.page, line.line): line for line in self.lines}


class TopicRecord(BaseModel):
    topic_id: str
    topic: str
    start_page: int
    start_line: int
    end_page: int
    end_line: int
    supporting_source_reference: str
    supporting_evidence: str
    source_ids: list[str]
    related_topic_ids: list[str] = Field(default_factory=list)
    recurrence_of: str | None = None
    is_procedural: bool = False
    transition_type: str = "new_topic"
    confidence: float = 0.0
    chunk_ids: list[str] = Field(default_factory=list)
    provenance_ok: bool = True
    provenance_notes: list[str] = Field(default_factory=list)

    def to_index_entry(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "start_page": self.start_page,
            "start_line": self.start_line,
            "end_page": self.end_page,
            "end_line": self.end_line,
            "supporting_source_reference": self.supporting_source_reference,
            "supporting_evidence": self.supporting_evidence,
            "source_ids": self.source_ids,
            "topic_id": self.topic_id,
            "related_topic_ids": self.related_topic_ids,
            "recurrence_of": self.recurrence_of,
            "is_procedural": self.is_procedural,
            "transition_type": self.transition_type,
            "confidence": self.confidence,
        }
