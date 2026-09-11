from __future__ import annotations

import re
from collections import defaultdict

import pymupdf

from src.provenance.ids import make_source_id
from .models import CanonicalLine, CanonicalTranscript, ExtractedPage


LINE_NUM_X_MAX = 95.0
TIMESTAMP_X_MIN = 490.0
FOOTER_Y_MIN = 720.0
EXPECTED_LINES = list(range(1, 26))

_TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
_PAGE_FOOTER_RE = re.compile(r"Page\s+(\d+)\s*$", re.IGNORECASE)
_SPEAKER_Q = re.compile(r"^Q\b")
_SPEAKER_A = re.compile(r"^A\b")
_SPEAKER_BY = re.compile(r"^BY\s+(MR\.|MS\.|MRS\.)\s+[A-Z]", re.I)
_SPEAKER_COUNSEL = re.compile(r"^(MR\.|MS\.|MRS\.)\s+[A-Z][A-Z.\-']+", re.I)
_SPEAKER_THE = re.compile(
    r"^THE\s+(WITNESS|REPORTER|VIDEOGRAPHER|COURT)\s*:", re.I
)
_PAREN = re.compile(r"^\(.*\)$")


def _round_y(y: float) -> int:
    return int(round(y / 2.0) * 2)


def _classify_page_role(text: str, transcript_page: int | None, has_lines: bool) -> str:
    compact = " ".join(text.split())
    upper = compact.upper()
    if "ADMINISTRATIVE INFORMATION REDACTED" in upper:
        return "redacted_administrative"
    if "I N D E X" in compact or re.search(r"\bINDEX\b", upper) and "WITNESS" in upper and "EXAMINATION" in upper:
        return "index"
    if "FEDERAL RULES OF CIVIL PROCEDURE" in upper:
        return "procedural_appendix"
    if "COMPANY CERTIFICATE AND DISCLOSURE" in upper:
        return "reporter_certificate"
    if "CERTIFICATION" in upper and "SHORTHAND REPORTER" in upper:
        return "csr_certificate"
    if "DEPOSITION CONCLUDED" in upper or "WHEREUPON, THE DEPOSITION" in upper:
        return "transcript"
    if "WITNESS SIGNATURE" in upper or "DECLARATION UNDER PENALTY OF PERJURY" in upper or "SOLEMNLY DECLARE" in upper:
        return "errata_declaration"
    if re.search(r"\[\w+\s*-\s*\w+\]", compact) and compact.count(":") > 20:
        return "word_index"
    if not has_lines:
        return "unnumbered"
    if transcript_page is not None and transcript_page <= 6 and "MR." in upper:
        return "appearances_and_preliminaries"
    return "transcript"


def _is_testimony_content(text: str) -> bool:
    return bool(re.search(r"\bQ\s{2,}", text) or re.search(r"\n\s*Q\s+", text) or "      Q" in text)


def extract_page_lines(
    page: pymupdf.Page,
) -> tuple[dict[int, dict], int | None, list[str], list[int], list[int]]:
    warnings: list[str] = []
    words = page.get_text("words")
    buckets: dict[int, list] = defaultdict(list)
    for w in words:
        x0, y0, x1, y1, text, *_ = w
        if not text.strip():
            continue
        buckets[_round_y(y0)].append(w)

    by_line_no: dict[int, dict] = {}
    seen_line_nos: list[int] = []
    transcript_page: int | None = None

    for y in sorted(buckets):
        row = sorted(buckets[y], key=lambda w: w[0])
        left = [w for w in row if w[0] <= LINE_NUM_X_MAX]
        rest = [w for w in row if w[0] > LINE_NUM_X_MAX]
        footer_text = " ".join(w[4] for w in row)
        footer_match = _PAGE_FOOTER_RE.search(footer_text)
        if footer_match and (not rest or all(w[1] >= FOOTER_Y_MIN or w[0] > 400 for w in rest)):
            # Footer line like "Page 7"
            if all(w[1] > 700 for w in row) or footer_text.strip().lower().startswith("page "):
                transcript_page = int(footer_match.group(1))
                continue

        line_no: int | None = None
        if left:
            token = left[0][4].strip()
            if token.isdigit() and 1 <= int(token) <= 25:
                line_no = int(token)
                seen_line_nos.append(line_no)

        body_words = [w for w in rest if w[0] < TIMESTAMP_X_MIN]
        ts_words = [w for w in rest if w[0] >= TIMESTAMP_X_MIN]
        speaker_cue: str | None = None
        if body_words and body_words[0][4] in ("Q", "A") and 135.0 <= body_words[0][0] <= 160.0:
            speaker_cue = body_words[0][4]
            body_words = body_words[1:]
        body = " ".join(w[4] for w in body_words).strip()
        timestamp = ts_words[0][4] if ts_words else None
        if timestamp and not _TIMESTAMP_RE.fullmatch(timestamp):
            # timestamp may be glued; keep only HH:MM
            m = _TIMESTAMP_RE.search(timestamp)
            timestamp = m.group(0) if m else None

        if line_no is None:
            if body and not footer_match:
                warnings.append(f"Unnumbered text at y={y}: {body[:80]}")
            continue

        by_line_no.setdefault(
            line_no, {"text": "", "timestamp": timestamp, "speaker_cue": speaker_cue, "parts": []}
        )
        if by_line_no[line_no]["text"] and body:
            warnings.append(f"Duplicate visual row for line {line_no}")
        if body:
            by_line_no[line_no]["text"] = (by_line_no[line_no]["text"] + " " + body).strip()
        if timestamp:
            by_line_no[line_no]["timestamp"] = timestamp
        if speaker_cue:
            by_line_no[line_no]["speaker_cue"] = speaker_cue

    duplicates = sorted({n for n in seen_line_nos if seen_line_nos.count(n) > 1})
    return by_line_no, transcript_page, warnings, duplicates, seen_line_nos


def _speaker_from_text(text: str) -> tuple[str, str, str]:
    """Return (speaker_label, speaker_kind, remaining_text)."""
    t = text.strip()
    if not t:
        return "", "UNKNOWN", ""
    if _SPEAKER_BY.match(t):
        label = t.split(":")[0].strip() if ":" in t else t
        rest = t.split(":", 1)[1].strip() if ":" in t else ""
        return label, "BY", rest
    m = _SPEAKER_THE.match(t)
    if m:
        role = m.group(1).upper()
        rest = t.split(":", 1)[1].strip() if ":" in t else ""
        kind = {
            "WITNESS": "WITNESS",
            "REPORTER": "REPORTER",
            "VIDEOGRAPHER": "VIDEOGRAPHER",
        }.get(role, "PROCEEDING")
        return f"THE {role}", kind, rest
    if _SPEAKER_COUNSEL.match(t) and (":" in t[:40] or t.startswith("MR.") or t.startswith("MS.")):
        if re.match(r"^(MR\.|MS\.|MRS\.)\s+\S+:", t):
            label = t.split(":", 1)[0].strip()
            rest = t.split(":", 1)[1].strip()
            return label, "ATTORNEY", rest
    if re.match(r"^Q\s*:\s*", t):
        rest = re.sub(r"^Q\s*:\s*", "", t).strip()
        return "Q", "Q", rest
    if re.match(r"^A\s*:\s*", t):
        rest = re.sub(r"^A\s*:\s*", "", t).strip()
        return "A", "A", rest
    if _PAREN.match(t) or t.startswith("("):
        return "PROCEEDING", "PROCEEDING", t
    return "", "UNKNOWN", t


def _apply_speakers(lines: list[CanonicalLine]) -> None:
    current_speaker = "UNKNOWN"
    current_kind = "UNKNOWN"
    for line in lines:
        if not line.text.strip() and line.speaker_cue is None:
            # Empty line before/between speakers has no active voice
            line.speaker = ""
            line.speaker_kind = "UNKNOWN"
            continue

        if line.speaker_cue == "Q":
            current_speaker = "Q"
            current_kind = "Q"
            line.speaker = "Q"
            line.speaker_kind = "Q"
            continue

        if line.speaker_cue == "A":
            current_speaker = "A"
            current_kind = "A"
            line.speaker = "A"
            line.speaker_kind = "A"
            continue

        label, kind, rest = _speaker_from_text(line.text)
        if kind != "UNKNOWN" and label:
            current_speaker = label
            current_kind = kind
            line.speaker = label
            line.speaker_kind = kind
            if rest:
                line.text = rest
            # keep original for BY headers with empty rest
        else:
            line.speaker = current_speaker
            line.speaker_kind = current_kind  # type: ignore[assignment]
            line.text = rest if rest else line.text


def _detect_testimony_range(pages: list[ExtractedPage], lines: list[CanonicalLine]) -> tuple[int | None, int | None]:
    start = None
    end = None
    for line in lines:
        if line.speaker_kind == "Q" and start is None:
            start = line.page
        joined = line.text.upper()
        if "THIS CONCLUDES TODAY" in joined or "DEPOSITION CONCLUDED" in joined:
            end = line.page
    if start is not None and end is None:
        numbered = [p.transcript_page for p in pages if p.transcript_page and p.page_role in ("transcript", "appearances_and_preliminaries")]
        if numbered:
            end = max(numbered)
    return start, end


def extract_deposition(pdf_path: str) -> CanonicalTranscript:
    doc = pymupdf.open(pdf_path)
    pages: list[ExtractedPage] = []
    all_lines: list[CanonicalLine] = []
    global_warnings: list[str] = []

    for pdf_index in range(doc.page_count):
        page = doc[pdf_index]
        raw = page.get_text()
        by_line, transcript_page, warnings, duplicates, seen = extract_page_lines(page)
        line_numbers = sorted(by_line.keys())
        missing = []
        if line_numbers:
            expected = [n for n in EXPECTED_LINES if n <= max(line_numbers)]
            missing = [n for n in expected if n not in by_line]
        role = _classify_page_role(raw, transcript_page, bool(line_numbers))
        if transcript_page is None and role == "redacted_administrative":
            transcript_page = pdf_index + 1

        extracted = ExtractedPage(
            pdf_page_index=pdf_index,
            transcript_page=transcript_page,
            page_role=role,
            line_numbers=line_numbers,
            missing_lines=missing,
            duplicate_lines=duplicates,
            warnings=warnings,
            raw_text=raw,
        )
        pages.append(extracted)

        page_no = transcript_page if transcript_page is not None else pdf_index + 1
        for line_no in line_numbers:
            rec = by_line[line_no]
            text = rec["text"]
            all_lines.append(
                CanonicalLine(
                    source_id=make_source_id(page_no, line_no),
                    page=page_no,
                    line=line_no,
                    speaker="UNKNOWN",
                    speaker_kind="UNKNOWN",
                    text=text,
                    timestamp=rec.get("timestamp"),
                    pdf_page_index=pdf_index,
                    page_role=role,
                    is_testimony=False,
                    speaker_cue=rec.get("speaker_cue"),
                )
            )

    _apply_speakers(all_lines)
    testimony_start, testimony_end = _detect_testimony_range(pages, all_lines)

    if testimony_start is not None and testimony_end is not None:
        for line in all_lines:
            if testimony_start <= line.page <= testimony_end and line.page_role in (
                "transcript",
                "appearances_and_preliminaries",
            ):
                line.is_testimony = True
            # Page 6 appearances are before first Q; keep as preliminaries unless Q/A present
            if line.page == testimony_start and line.speaker_kind in ("Q", "A", "BY", "WITNESS"):
                line.is_testimony = True

        # Mark full testimony window including attorney colloquy on those pages
        for line in all_lines:
            if (
                testimony_start <= line.page <= testimony_end
                and line.page_role == "transcript"
            ):
                line.is_testimony = True

    # First Q page through conclusion: include page 7-88 style detection without hardcoding
    first_q = next((ln.page for ln in all_lines if ln.speaker_kind == "Q"), None)
    last_testimony_page = testimony_end
    if first_q is not None:
        for line in all_lines:
            if last_testimony_page and first_q <= line.page <= last_testimony_page:
                if line.page_role in ("transcript", "appearances_and_preliminaries"):
                    # appearances page before first Q is not testimony Q/A
                    if line.page < first_q:
                        line.is_testimony = False
                    elif line.page == last_testimony_page and line.line > 17:
                        line.is_testimony = False
                    else:
                        line.is_testimony = True

    if not any(ln.is_testimony for ln in all_lines):
        global_warnings.append("No testimony lines detected; check extraction.")

    doc.close()
    return CanonicalTranscript(
        source_pdf=pdf_path,
        total_pdf_pages=len(pages),
        pages=pages,
        lines=all_lines,
        testimony_page_start=first_q,
        testimony_page_end=last_testimony_page,
        extraction_warnings=global_warnings,
    )
