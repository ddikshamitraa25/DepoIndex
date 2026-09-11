from __future__ import annotations

import re

from src.extraction.models import CanonicalLine


_RANGE_RE = re.compile(r"^P(?P<page>\d+):L(?P<start>\d+)(?:-L(?P<end>\d+))?$")
_CROSS_RE = re.compile(
    r"^P(?P<sp>\d+):L(?P<sl>\d+)-P(?P<ep>\d+):L(?P<el>\d+)$"
)


def make_source_id(page: int, line: int) -> str:
    return f"P{page}:L{line}"


def make_range_id(start_page: int, start_line: int, end_page: int, end_line: int) -> str:
    if start_page == end_page:
        if start_line == end_line:
            return make_source_id(start_page, start_line)
        return f"P{start_page}:L{start_line}-L{end_line}"
    return f"P{start_page}:L{start_line}-P{end_page}:L{end_line}"


def parse_source_id(source_id: str) -> tuple[int, int, int, int]:
    cross = _CROSS_RE.match(source_id)
    if cross:
        return (
            int(cross.group("sp")),
            int(cross.group("sl")),
            int(cross.group("ep")),
            int(cross.group("el")),
        )
    m = _RANGE_RE.match(source_id)
    if not m:
        raise ValueError(f"Invalid source_id: {source_id}")
    page = int(m.group("page"))
    start = int(m.group("start"))
    end = int(m.group("end") or start)
    return page, start, page, end


def source_ids_for_span(
    lines: list[CanonicalLine],
    start_page: int,
    start_line: int,
    end_page: int,
    end_line: int,
) -> list[str]:
    ids: list[str] = []
    for line in lines:
        loc = (line.page, line.line)
        if (start_page, start_line) <= loc <= (end_page, end_line):
            ids.append(line.source_id)
    return ids


def supporting_reference(
    deposition_name: str,
    start_page: int,
    start_line: int,
    end_page: int,
    end_line: int,
) -> str:
    return (
        f"{deposition_name} "
        f"{make_source_id(start_page, start_line)} - "
        f"{make_source_id(end_page, end_line)}"
    )
