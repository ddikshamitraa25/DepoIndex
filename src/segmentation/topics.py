from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.extraction.models import CanonicalTranscript, TopicRecord
from src.provenance.ids import make_source_id, source_ids_for_span, supporting_reference
from src.provenance.validator import ProvenanceValidator
from .chunking import Chunk, QAUnit, build_chunks
from .llm import complete_json, llm_available


DEPOSITION_NAME = "Persis Yu Deposition"

STOPISH = {
    "correct", "yes", "no", "okay", "thank", "thanks", "know", "think", "would",
    "could", "going", "want", "that", "this", "what", "when", "have", "been",
}

CONTINUE_SIM = 0.18
RELATED_SIM = 0.32
MAX_PAGES_CONTINUE = 8
RECURRENCE_GAP_PAGES = 4
MIN_TOPIC_CHARS = 350
MAX_TOPIC_PAGES = 10


COURTESY_PREFIX = re.compile(
    r"^(thank you[.,!]?|terrific[.,!]?|okay[.,!]?|sure thing[.,!]?|sure[.,!]?|correct[.,!]?|right[.,!]?|all right[.,!]?|alright[.,!]?)\s*",
    re.I,
)


def _normalize_label(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(okay|all right|alright|so|and|now|uh|um)[,.]?\s+", "", text, flags=re.I)
    text = text.lstrip("-:;,. ").strip()
    if len(text) > 115:
        cut = text[:115]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        text = cut + "..."
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:]
    return text or "Untitled testimony segment"


def _first_question(units: list[QAUnit]) -> str:
    for u in units:
        if u.is_procedural:
            continue
        for t in u.turns:
            if t.speaker_kind == "Q" and t.text.strip():
                clean = t.text.strip()
                for _ in range(3):
                    clean = COURTESY_PREFIX.sub("", clean).strip()
                if clean.startswith("--") or len(clean.split()) < 3:
                    continue
                return clean
        for t in u.turns:
            if t.speaker_kind in ("WITNESS", "A") and t.text.strip():
                clean = t.text.strip()
                if not clean.startswith("--") and len(clean.split()) >= 4:
                    return clean
        if u.text.strip():
            clean = u.text.strip()
            if not clean.startswith("--") and len(clean.split()) >= 3:
                return clean
    return units[0].text if units else ""


def _keyphrases(texts: list[str], n: int = 6) -> list[str]:
    docs = [t for t in texts if t.strip()]
    if not docs:
        return []
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=4000, stop_words="english")
    try:
        x = vec.fit_transform(docs)
    except ValueError:
        return []
    scores = np.asarray(x.sum(axis=0)).ravel()
    names = np.array(vec.get_feature_names_out())
    order = scores.argsort()[::-1]
    out = []
    for i in order:
        term = names[i]
        if term in STOPISH or len(term) < 4:
            continue
        out.append(term)
        if len(out) >= n:
            break
    return out


def _label_for(units: list[QAUnit], phrases: list[str]) -> str:
    q = _first_question(units)
    q = _normalize_label(q)
    topical = "; ".join(phrases[:3]) if phrases else ""
    if not q or q.lower().startswith("untitled"):
        return _normalize_label(topical[0].upper() + topical[1:] if topical else "Testimony segment")
    if topical and topical.lower() not in q.lower() and len(q) <= 75:
        return _normalize_label(f"{q} ({topical})")
    return q


def _evidence(lines, start_page, start_line, end_page, end_line, limit=420) -> str:
    selected = []
    for ln in lines:
        loc = (ln.page, ln.line)
        if (start_page, start_line) <= loc <= (end_page, end_line):
            if ln.text.strip() and ln.speaker_kind in ("Q", "A", "WITNESS", "ATTORNEY"):
                selected.append(f"{ln.speaker}: {ln.text.strip()}")
            if sum(len(s) for s in selected) > limit:
                break
    if not selected:
        for ln in lines:
            loc = (ln.page, ln.line)
            if (start_page, start_line) <= loc <= (end_page, end_line) and ln.text.strip():
                selected.append(ln.text.strip())
                if sum(len(s) for s in selected) > limit:
                    break
    text = " ".join(selected)
    return text[:limit].rsplit(" ", 1)[0] + ("…" if len(text) > limit else "")


def _centroid(mat, idxs):
    return np.asarray(mat[idxs].mean(axis=0)).ravel()


def _llm_decisions(chunks: list[Chunk]) -> dict[str, dict] | None:
    if not llm_available():
        return None
    payload_chunks = []
    for ch in chunks:
        payload_chunks.append(
            {
                "CHUNK_ID": ch.chunk_id,
                "SOURCE_RANGE": ch.source_range,
                "text": ch.text[:4000],
            }
        )
    # Batches keep prompts bounded
    decisions: dict[str, dict] = {}
    batch_size = 8
    for i in range(0, len(payload_chunks), batch_size):
        batch = payload_chunks[i : i + batch_size]
        user = (
            "Assign topic actions to these chunks. JSON only.\n"
            + json_dumps(batch)
        )
        out = complete_json(user)
        if not out or "decisions" not in out:
            return None
        for d in out["decisions"]:
            cid = d.get("chunk_id")
            if cid:
                decisions[cid] = d
    if len(decisions) < max(1, len(chunks) // 2):
        return None
    return decisions


def json_dumps(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def _merge_chunk_groups(groups: list[list[Chunk]]) -> list[list[Chunk]]:
    merged: list[list[Chunk]] = []
    for g in groups:
        if not merged:
            merged.append(g)
            continue
        prev = merged[-1]
        prev_text_len = sum(len(c.text) for c in prev)
        g_text_len = sum(len(c.text) for c in g)
        if g_text_len < MIN_TOPIC_CHARS and prev_text_len < 6000:
            prev.extend(g)
        else:
            merged.append(g)
    return merged


def segment_topics(transcript: CanonicalTranscript, chunks: list[Chunk] | None = None) -> list[TopicRecord]:
    chunks = chunks or build_chunks(transcript)
    if not chunks:
        return []

    unit_texts = []
    for ch in chunks:
        substantive = " ".join(u.text for u in ch.qa_units if not u.is_procedural) or ch.text
        unit_texts.append(substantive if substantive.strip() else ch.text or "empty")

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=8000,
        stop_words="english",
    )
    matrix = vectorizer.fit_transform(unit_texts)

    llm_map = _llm_decisions(chunks)

    groups: list[list[Chunk]] = []
    actions: list[str] = []
    current: list[int] = []
    topic_centroids: list[tuple[list[int], np.ndarray, str]] = []

    def flush_current(action: str) -> None:
        nonlocal current
        if not current:
            return
        groups.append([chunks[i] for i in current])
        actions.append(action)
        vec = _centroid(matrix, current)
        phrases = _keyphrases([unit_texts[i] for i in current], 4)
        label_key = " ".join(phrases) or f"topic-{len(groups)}"
        topic_centroids.append((list(current), vec, label_key))
        current = []

    for i, ch in enumerate(chunks):
        only_proc = all(u.is_procedural for u in ch.qa_units) and bool(ch.qa_units)
        llm = llm_map.get(ch.chunk_id) if llm_map else None
        if current:
            sim = float(cosine_similarity(_centroid(matrix, current).reshape(1, -1), matrix[i]).item())
            start_page = chunks[current[0]].qa_units[0].start.page
            this_page = ch.qa_units[0].start.page
            span_pages = this_page - start_page
        else:
            sim = 0.0
            span_pages = 0

        action = "new_topic"
        if llm:
            action = llm.get("action") or "new_topic"
            if action == "continue" and current:
                current.append(i)
                continue
            if action in ("brief_digression",) and current:
                current.append(i)
                continue
            if current:
                flush_current("new_topic")
            current = [i]
            continue

        if only_proc and current:
            current.append(i)
            continue
        if not current:
            current = [i]
            continue
        if sim >= CONTINUE_SIM and span_pages <= MAX_PAGES_CONTINUE:
            current.append(i)
            continue
        # recurrence vs new
        best_j = -1
        best_sim = 0.0
        for j, (_idxs, vec, _lab) in enumerate(topic_centroids):
            s = float(cosine_similarity(vec.reshape(1, -1), matrix[i]).item())
            if s > best_sim:
                best_sim = s
                best_j = j
        flush_current("new_topic")
        current = [i]
        if best_j >= 0 and best_sim >= RELATED_SIM:
            pass  # previous already flushed; mark later during topic build

    flush_current("new_topic")
    groups = _merge_chunk_groups(groups)

    # Split oversized groups on internal similarity drop
    refined: list[list[Chunk]] = []
    chunk_index = {c.chunk_id: idx for idx, c in enumerate(chunks)}
    for g in groups:
        if not g:
            continue
        start_p = g[0].qa_units[0].start.page
        end_p = g[-1].qa_units[-1].end.page
        if end_p - start_p <= MAX_TOPIC_PAGES or len(g) <= 2:
            refined.append(g)
            continue
        split_at = []
        for k in range(1, len(g)):
            a = chunk_index[g[k - 1].chunk_id]
            b = chunk_index[g[k].chunk_id]
            s = float(cosine_similarity(matrix[a], matrix[b]).item())
            if s < CONTINUE_SIM:
                split_at.append(k)
        if not split_at:
            refined.append(g)
        else:
            prev = 0
            for k in split_at:
                if k - prev >= 1:
                    refined.append(g[prev:k])
                    prev = k
            refined.append(g[prev:])

    records: list[TopicRecord] = []
    fingerprint_to_id: dict[str, str] = {}
    validator = ProvenanceValidator(transcript)

    for n, g in enumerate(refined, start=1):
        units = [u for ch in g for u in ch.qa_units]
        lines = [ln for u in units for ln in u.lines]
        start, end = lines[0], lines[-1]
        phrases = _keyphrases([" ".join(u.text for u in units)], 6)
        llm_labels = []
        if llm_map:
            for ch in g:
                lab = (llm_map.get(ch.chunk_id) or {}).get("topic_label")
                if lab:
                    llm_labels.append(lab)
        topic_label = _normalize_label(llm_labels[0]) if llm_labels else _label_for(units, phrases)
        procedural = all(u.is_procedural for u in units)
        if procedural:
            reason = next((u.procedural_reason for u in units if u.procedural_reason), "procedure")
            topic_label = f"Procedural interruption ({reason})"

        fp = hashlib.sha1(" ".join(phrases[:4]).encode("utf-8")).hexdigest()[:10]
        topic_id = f"T{n:03d}"
        recurrence_of = None
        related = []
        transition = "new_topic"
        if fp in fingerprint_to_id:
            prev_id = fingerprint_to_id[fp]
            gap = start.page - next(t.end_page for t in records if t.topic_id == prev_id)
            if gap >= RECURRENCE_GAP_PAGES:
                recurrence_of = prev_id
                related = [prev_id]
                transition = "related_distinct"
                topic_label = f"{topic_label} (later span)"
            else:
                transition = "related_distinct"
                related = [prev_id]
        else:
            fingerprint_to_id[fp] = topic_id

        source_ids = source_ids_for_span(
            transcript.lines, start.page, start.line, end.page, end.line
        )
        # Restrict to lines actually in this topic when possible
        topic_source = [ln.source_id for ln in lines]
        if topic_source:
            source_ids = topic_source

        rec = TopicRecord(
            topic_id=topic_id,
            topic=topic_label,
            start_page=start.page,
            start_line=start.line,
            end_page=end.page,
            end_line=end.line,
            supporting_source_reference=supporting_reference(
                DEPOSITION_NAME, start.page, start.line, end.page, end.line
            ),
            supporting_evidence=_evidence(
                transcript.lines, start.page, start.line, end.page, end.line
            ),
            source_ids=source_ids,
            related_topic_ids=related,
            recurrence_of=recurrence_of,
            is_procedural=procedural,
            transition_type=transition,
            confidence=round(min(0.95, 0.55 + 0.05 * math.log(1 + len(units))), 3),
            chunk_ids=[ch.chunk_id for ch in g],
        )
        ok, notes = validator.validate_topic(rec)
        rec.provenance_ok = ok
        rec.provenance_notes = notes
        if ok:
            records.append(rec)

    records.sort(key=lambda t: (t.start_page, t.start_line, t.end_page, t.end_line))
    return records
