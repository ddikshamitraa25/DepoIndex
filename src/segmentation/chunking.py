from __future__ import annotations

import os
from dataclasses import dataclass

from src.extraction.models import CanonicalLine, CanonicalTranscript
from src.provenance.ids import make_range_id


@dataclass
class Turn:
    speaker: str
    speaker_kind: str
    lines: list[CanonicalLine]

    @property
    def text(self) -> str:
        return " ".join(ln.text.strip() for ln in self.lines if ln.text.strip())

    @property
    def start(self) -> CanonicalLine:
        return self.lines[0]

    @property
    def end(self) -> CanonicalLine:
        return self.lines[-1]


@dataclass
class QAUnit:
    unit_id: str
    turns: list[Turn]
    is_procedural: bool
    procedural_reason: str | None = None

    @property
    def lines(self) -> list[CanonicalLine]:
        return [ln for t in self.turns for ln in t.lines]

    @property
    def text(self) -> str:
        return " ".join(t.text for t in self.turns if t.text)

    @property
    def start(self) -> CanonicalLine:
        return self.lines[0]

    @property
    def end(self) -> CanonicalLine:
        return self.lines[-1]


@dataclass
class Chunk:
    chunk_id: str
    source_range: str
    qa_units: list[QAUnit]
    source_ids: list[str]

    @property
    def text(self) -> str:
        return "\n".join(
            f"[{u.start.source_id}-{u.end.source_id}] {u.text}" for u in self.qa_units
        )

    @property
    def lines(self) -> list[CanonicalLine]:
        return [ln for u in self.qa_units for ln in u.lines]


PROCEDURAL_PHRASES = (
    "objection",
    "same objection",
    "form of the question",
    "go off the record",
    "off the record",
    "on the record",
    "back on the record",
    "this concludes today",
    "deposition concluded",
    "take a break",
    "going off the record",
    "the videographer",
    "the reporter",
    "could you sit up",
    "read that back",
    "let's go off",
)


def is_procedural_text(text: str, speaker_kind: str) -> str | None:
    low = text.lower()
    if speaker_kind in ("REPORTER", "VIDEOGRAPHER"):
        return speaker_kind.lower()
    if speaker_kind == "PROCEEDING":
        return "parenthetical"
    if speaker_kind == "ATTORNEY" and any(
        p in low for p in ("objection", "same objection", "form")
    ):
        return "objection"
    if any(p in low for p in PROCEDURAL_PHRASES):
        if speaker_kind in ("ATTORNEY", "REPORTER", "VIDEOGRAPHER", "PROCEEDING", "BY"):
            return "colloquy_or_procedure"
        if "objection" in low:
            return "objection"
    return None


def group_turns(lines: list[CanonicalLine]) -> list[Turn]:
    turns: list[Turn] = []
    current: list[CanonicalLine] = []
    speaker = None
    kind = None
    for ln in lines:
        key = (ln.speaker, ln.speaker_kind)
        if current and key != (speaker, kind):
            turns.append(Turn(speaker=speaker or "UNKNOWN", speaker_kind=kind or "UNKNOWN", lines=current))
            current = []
        speaker, kind = ln.speaker, ln.speaker_kind
        current.append(ln)
    if current:
        turns.append(Turn(speaker=speaker or "UNKNOWN", speaker_kind=kind or "UNKNOWN", lines=current))
    return turns


def group_qa_units(turns: list[Turn]) -> list[QAUnit]:
    units: list[QAUnit] = []
    bucket: list[Turn] = []
    n = 0

    def flush() -> None:
        nonlocal n, bucket
        if not bucket:
            return
        n += 1
        texts = " ".join(t.text for t in bucket)
        kinds = {t.speaker_kind for t in bucket}
        reason = None
        for t in bucket:
            reason = is_procedural_text(t.text, t.speaker_kind)
            if reason:
                break
        # Pure objection / reporter / videographer units
        procedural = False
        if kinds <= {"ATTORNEY", "REPORTER", "VIDEOGRAPHER", "PROCEEDING", "BY"} and reason:
            procedural = True
        if reason in ("objection", "reporter", "videographer", "parenthetical") and not any(
            t.speaker_kind in ("Q", "A", "WITNESS") for t in bucket
        ):
            procedural = True
        units.append(
            QAUnit(
                unit_id=f"QA{n:04d}",
                turns=bucket,
                is_procedural=procedural,
                procedural_reason=reason,
            )
        )
        bucket = []

    for turn in turns:
        if turn.speaker_kind == "Q" and bucket:
            has_qa = any(t.speaker_kind in ("Q", "A", "WITNESS") for t in bucket)
            is_proc = all(bool(is_procedural_text(t.text, t.speaker_kind)) for t in bucket if t.text.strip())
            if has_qa or is_proc:
                flush()
        bucket.append(turn)
    flush()
    return units


def build_chunks(
    transcript: CanonicalTranscript,
    target_chars: int | None = None,
    max_units: int | None = None,
) -> list[Chunk]:
    target_chars = target_chars or int(os.getenv("DEPOINDEX_CHUNK_CHARS", "1800"))
    max_units = max_units or int(os.getenv("DEPOINDEX_CHUNK_MAX_UNITS", "6"))
    testimony = [ln for ln in transcript.lines if ln.is_testimony]
    turns = group_turns(testimony)
    units = group_qa_units(turns)
    chunks: list[Chunk] = []
    i = 0
    cid = 0
    while i < len(units):
        cid += 1
        group: list[QAUnit] = []
        chars = 0
        while i < len(units):
            unit = units[i]
            if group and (chars >= target_chars or len(group) >= max_units):
                break
            # Keep a short procedural interruption attached to the current chunk
            group.append(unit)
            chars += len(unit.text)
            i += 1
            if unit.is_procedural and len(group) == 1 and i < len(units):
                continue
        source_ids = [ln.source_id for u in group for ln in u.lines]
        start, end = group[0].start, group[-1].end
        chunks.append(
            Chunk(
                chunk_id=f"C{cid:03d}",
                source_range=make_range_id(start.page, start.line, end.page, end.line),
                qa_units=group,
                source_ids=source_ids,
            )
        )
    return chunks
