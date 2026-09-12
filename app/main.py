from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
STATIC = Path(__file__).resolve().parent / "static"

TRANSCRIPT_UNAVAILABLE_REASON = (
    "Full source verification requires the original deposition PDF/canonical "
    "transcript, which is intentionally excluded from this repository."
)

app = FastAPI(title="DepoIndex", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _load_json(name: str):
    path = OUTPUTS / name
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{name} is missing. Run python run_pipeline.py first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _transcript_path() -> Path:
    return OUTPUTS / "canonical_transcript.json"


def _load_transcript_or_none():
    path = _transcript_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _find_topic(topic_id: str, items: list[dict]) -> dict:
    topic = next((t for t in items if t.get("topic_id") == topic_id), None)
    if topic is None:
        try:
            topic = items[int(topic_id)]
        except (ValueError, IndexError):
            raise HTTPException(status_code=404, detail="Unknown topic")
    return topic


def _source_lines_for_topic(topic: dict, transcript: dict) -> list[dict]:
    lines = [
        ln
        for ln in transcript["lines"]
        if (topic["start_page"], topic["start_line"])
        <= (ln["page"], ln["line"])
        <= (topic["end_page"], topic["end_line"])
        and ln["source_id"] in set(topic.get("source_ids") or [])
    ]
    if not lines:
        lines = [
            ln
            for ln in transcript["lines"]
            if (topic["start_page"], topic["start_line"])
            <= (ln["page"], ln["line"])
            <= (topic["end_page"], topic["end_line"])
        ]
    return lines


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/topics")
def topics(q: str | None = None, procedural: bool | None = None):
    items = _load_json("topic_index.json")
    if procedural is False:
        items = [t for t in items if not t.get("is_procedural")]
    if procedural is True:
        items = [t for t in items if t.get("is_procedural")]
    if q:
        ql = q.lower()
        items = [
            t
            for t in items
            if ql in t.get("topic", "").lower()
            or ql in t.get("supporting_evidence", "").lower()
            or ql in " ".join(t.get("source_ids", [])).lower()
        ]
    return {
        "count": len(items),
        "topics": items,
        "transcript_available": _transcript_path().exists(),
    }


@app.get("/api/topics/{topic_id}")
def topic_detail(topic_id: str):
    items = _load_json("topic_index.json")
    topic = _find_topic(topic_id, items)
    related = [t for t in items if t.get("topic_id") in (topic.get("related_topic_ids") or [])]
    transcript = _load_transcript_or_none()
    if transcript is None:
        return {
            "topic": topic,
            "source_lines": [],
            "related": related,
            "transcript_available": False,
            "transcript_unavailable_reason": TRANSCRIPT_UNAVAILABLE_REASON,
        }
    lines = _source_lines_for_topic(topic, transcript)
    return {
        "topic": topic,
        "source_lines": lines,
        "related": related,
        "transcript_available": True,
    }


@app.get("/api/search")
def semantic_search(q: str = Query(..., min_length=2), k: int = 8):
    items = _load_json("topic_index.json")
    corpus = [f"{t.get('topic','')} {t.get('supporting_evidence','')}" for t in items]
    if not corpus:
        return {"query": q, "results": []}
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform(corpus + [q])
    sims = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    order = np.argsort(sims)[::-1][:k]
    results = []
    for i in order:
        if sims[i] <= 0:
            continue
        t = dict(items[int(i)])
        t["similarity"] = round(float(sims[i]), 4)
        results.append(t)
    return {"query": q, "results": results}


@app.get("/api/completeness")
def completeness():
    return _load_json("completeness_report.json")


@app.get("/api/validation")
def validation():
    path = ROOT / "validation" / "manual_validation_report.json"
    if not path.exists():
        return {"available": False}
    return {"available": True, **json.loads(path.read_text(encoding="utf-8"))}


@app.get("/api/provenance/check")
def provenance_check(topic_id: str):
    items = _load_json("topic_index.json")
    topic = _find_topic(topic_id, items)
    transcript = _load_transcript_or_none()
    if transcript is None:
        return {
            "topic_id": topic.get("topic_id"),
            "transcript_available": False,
            "verification_available": False,
            "verification_status": "unavailable",
            "ok": False,
            "reason": TRANSCRIPT_UNAVAILABLE_REASON,
            "start_exists": None,
            "end_exists": None,
            "source_ids_resolved": 0,
            "missing_source_ids": [],
            "line_count": 0,
        }

    lines = _source_lines_for_topic(topic, transcript)
    ids = {ln["source_id"] for ln in lines}
    missing = [sid for sid in topic.get("source_ids", []) if sid not in ids]
    start_exists = any(
        ln["page"] == topic["start_page"] and ln["line"] == topic["start_line"] for ln in lines
    )
    end_exists = any(
        ln["page"] == topic["end_page"] and ln["line"] == topic["end_line"] for ln in lines
    )
    ok = not missing and bool(lines) and start_exists and end_exists
    return {
        "topic_id": topic.get("topic_id"),
        "transcript_available": True,
        "verification_available": True,
        "verification_status": "verified" if ok else "failed",
        "ok": ok,
        "start_exists": start_exists,
        "end_exists": end_exists,
        "source_ids_resolved": len(topic.get("source_ids", [])) - len(missing),
        "missing_source_ids": missing[:20],
        "line_count": len(lines),
    }
