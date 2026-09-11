from __future__ import annotations

from collections import Counter

from src.extraction.models import CanonicalTranscript
from src.segmentation.chunking import Chunk


def build_completeness_report(
    transcript: CanonicalTranscript,
    chunks: list[Chunk],
) -> dict:
    testimony_pages = sorted(
        {p.transcript_page for p in transcript.pages if p.transcript_page and p.page_role in ("transcript",)}
    )
    if transcript.testimony_page_start and transcript.testimony_page_end:
        testimony_pages = [
            p
            for p in range(transcript.testimony_page_start, transcript.testimony_page_end + 1)
            if any(pg.transcript_page == p for pg in transcript.pages)
        ]
    extracted_pages = sorted({ln.page for ln in transcript.lines})
    extracted_testimony_pages = sorted({ln.page for ln in transcript.lines if ln.is_testimony})
    gaps = []
    for page in extracted_testimony_pages:
        rec = next((p for p in transcript.pages if p.transcript_page == page), None)
        if rec and rec.missing_lines:
            gaps.append({"page": page, "missing_lines": rec.missing_lines})
    duplicates = []
    for page in transcript.pages:
        if page.duplicate_lines:
            duplicates.append({"page": page.transcript_page, "lines": page.duplicate_lines})

    # Silent skip check: consecutive testimony source IDs should cover 1-25 per page
    skipped = []
    by_page: dict[int, list[int]] = {}
    for ln in transcript.lines:
        if ln.is_testimony:
            by_page.setdefault(ln.page, []).append(ln.line)
    for page, lines in sorted(by_page.items()):
        expected = set(range(1, max(lines) + 1))
        missing = sorted(expected - set(lines))
        if missing:
            skipped.append({"page": page, "missing_in_canonical": missing})

    page_roles = Counter(p.page_role for p in transcript.pages)
    warnings = list(transcript.extraction_warnings)
    for p in transcript.pages:
        warnings.extend([f"p{p.transcript_page}: {w}" for w in p.warnings[:5]])

    return {
        "total_pdf_pages": transcript.total_pdf_pages,
        "testimony_pages": testimony_pages,
        "testimony_page_start": transcript.testimony_page_start,
        "testimony_page_end": transcript.testimony_page_end,
        "extracted_pages": extracted_pages,
        "extracted_testimony_pages": extracted_testimony_pages,
        "extracted_lines": len(transcript.lines),
        "extracted_testimony_lines": sum(1 for ln in transcript.lines if ln.is_testimony),
        "chunks_created": len(chunks),
        "gaps_detected": gaps + skipped,
        "duplicate_lines": duplicates,
        "extraction_warnings": warnings[:200],
        "page_roles": dict(page_roles),
        "non_testimony_roles": sorted(
            {p.page_role for p in transcript.pages if p.page_role not in ("transcript",)}
        ),
    }
