from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from src.extraction.pdf_extract import extract_deposition
from src.pipeline.reports import dump_json, write_topic_index_json, write_topic_index_md
from src.segmentation.chunking import build_chunks
from src.segmentation.topics import segment_topics
from src.validation.completeness import build_completeness_report


ROOT = Path(__file__).resolve().parents[2]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_pipeline(
    pdf_path: str | None = None,
    output_dir: str | Path | None = None,
    run_name: str | None = None,
) -> dict:
    load_dotenv(ROOT / ".env")
    pdf = Path(pdf_path or os.getenv("DEPOINDEX_PDF_PATH", ROOT / "data" / "Persis_Yu_Deposition.pdf"))
    if not pdf.is_absolute():
        pdf = ROOT / pdf
    if not pdf.exists():
        raise FileNotFoundError(
            f"Deposition PDF not found at {pdf}. Place Persis_Yu_Deposition.pdf in data\\ "
            "or set DEPOINDEX_PDF_PATH."
        )
    out = Path(output_dir) if output_dir else ROOT / "outputs"
    out.mkdir(parents=True, exist_ok=True)

    transcript = extract_deposition(str(pdf))
    chunks = build_chunks(transcript)
    topics = segment_topics(transcript, chunks)
    completeness = build_completeness_report(transcript, chunks)

    canonical = transcript.model_dump()
    dump_json(out / "canonical_transcript.json", canonical)
    dump_json(
        out / "chunks.json",
        [
            {
                "chunk_id": c.chunk_id,
                "source_range": c.source_range,
                "source_ids": c.source_ids,
                "text": c.text,
            }
            for c in chunks
        ],
    )
    write_topic_index_json(out / "topic_index.json", topics)
    write_topic_index_md(out / "topic_index.md", topics)
    dump_json(out / "completeness_report.json", completeness)

    summary = {
        "ran_at": _now(),
        "pdf": str(pdf),
        "llm_provider": os.getenv("DEPOINDEX_LLM_PROVIDER", "none"),
        "topic_count": len(topics),
        "extracted_lines": len(transcript.lines),
        "testimony_lines": sum(1 for ln in transcript.lines if ln.is_testimony),
        "chunks": len(chunks),
        "testimony_page_start": transcript.testimony_page_start,
        "testimony_page_end": transcript.testimony_page_end,
        "total_pdf_pages": transcript.total_pdf_pages,
        "topics": [t.to_index_entry() for t in topics],
    }
    dump_json(out / "run_summary.json", summary)

    if run_name:
        run_dir = ROOT / "runs" / run_name
        if run_dir.exists():
            shutil.rmtree(run_dir)
        shutil.copytree(out, run_dir)
        # keep a compact copy of the index
        dump_json(run_dir / "run_summary.json", summary)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DepoIndex pipeline")
    parser.add_argument("--pdf", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()
    summary = run_pipeline(args.pdf, args.output_dir, args.run_name)
    print(json.dumps({k: v for k, v in summary.items() if k != "topics"}, indent=2))


if __name__ == "__main__":
    main()
