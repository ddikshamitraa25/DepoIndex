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
    return {"count": len(items), "topics": items}


@app.get("/api/topics/{topic_id}")
def topic_detail(topic_id: str):
    items = _load_json("topic_index.json")
    topic = next((t for t in items if t.get("topic_id") == topic_id), None)
    if topic is None:
        # allow index number
        try:
            topic = items[int(topic_id)]
        except (ValueError, IndexError):
            raise HTTPException(status_code=404, detail="Unknown topic")
    transcript = _load_json("canonical_transcript.json")
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
    related = [t for t in items if t.get("topic_id") in (topic.get("related_topic_ids") or [])]
    return {"topic": topic, "source_lines": lines, "related": related}


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
    detail = topic_detail(topic_id)
    topic = detail["topic"]
    lines = detail["source_lines"]
    ids = {ln["source_id"] for ln in lines}
    missing = [sid for sid in topic.get("source_ids", []) if sid not in ids]
    return {
        "topic_id": topic.get("topic_id"),
        "start_exists": any(
            ln["page"] == topic["start_page"] and ln["line"] == topic["start_line"] for ln in lines
        ),
        "end_exists": any(
            ln["page"] == topic["end_page"] and ln["line"] == topic["end_line"] for ln in lines
        ),
        "source_ids_resolved": len(topic.get("source_ids", [])) - len(missing),
        "missing_source_ids": missing[:20],
        "line_count": len(lines),
        "ok": not missing and bool(lines),
    }
