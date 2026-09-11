from __future__ import annotations

import json
from pathlib import Path

from src.extraction.models import TopicRecord


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def write_topic_index_json(path: Path, topics: list[TopicRecord]) -> None:
    dump_json(path, [t.to_index_entry() for t in topics])


def write_topic_index_md(path: Path, topics: list[TopicRecord]) -> None:
    lines = [
        "# Persis Yu Deposition — Topic Index",
        "",
        "Chronological index generated from the canonical transcript. "
        "Page/line citations are copied from extracted source IDs; they are not model-invented.",
        "",
        "| Topic | Start | End | Supporting Evidence |",
        "|---|---|---|---|",
    ]
    for t in topics:
        topic = t.topic.replace("|", "/")
        ev = t.supporting_evidence.replace("|", "/").replace("\n", " ")
        if len(ev) > 220:
            ev = ev[:217] + "..."
        start = f"P{t.start_page}:L{t.start_line}"
        end = f"P{t.end_page}:L{t.end_line}"
        lines.append(f"| {topic} | {start} | {end} | {ev} |")
    lines.extend(
        [
            "",
            "## Recurrence policy",
            "",
            "If the same subject appears several pages later, DepoIndex keeps a **separate chronological span** "
            "and records `recurrence_of` / `related_topic_ids` instead of merging distant testimony.",
            "",
            "## Digression policy",
            "",
            "Objections, reporter/videographer remarks, and off-the-record/break colloquy are attached to the "
            "surrounding substantive topic when brief. Purely procedural stretches are labeled as procedural "
            "interruptions and are not treated as expert-opinion topics.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
