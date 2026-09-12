# DepoIndex - AI-Powered Deposition Topic Index with Deterministic Provenance

**Author:** Diksha Mitra  
**VIT Bhopal University | B.Tech CSE (Core) | 2024-2028**  
[GitHub](https://github.com/ddikshamitraa25) · [LinkedIn](https://www.linkedin.com/in/diksha-mitra-491929365/)

**Problem #3 submission - AI/LLM Engineer Internship Problem-Solving Round**

DepoIndex turns a deposition transcript PDF into a chronological, page/line-cited topic index. Every entry in the output can be traced back to an exact `P<page>:L<line>` location in the original transcript, so an attorney (or a reviewer) can check any claim against the source in seconds instead of re-reading the whole deposition.

This build was run end-to-end against the **Persis Yu deposition** (*Heather Turrey v. Vervent, Inc.*), a 122-page PDF with 82 pages of substantive testimony. All numbers in this README come from the committed files in `outputs/` and `validation/`, not from a re-run performed while writing this document.

---

## 1. Project Overview

Given a deposition PDF, DepoIndex:

1. Extracts the transcript **coordinate-by-coordinate** from the PDF (not just raw text dump), so line numbers, speaker labels, and timestamps are read from their actual on-page position rather than guessed from formatting.
2. Builds a **canonical transcript** where every line has an immutable ID (`P7:L12`, etc.) that never changes across runs.
3. Groups lines into speaker turns, then question/answer units, then bounded chunks.
4. Segments those chunks into **chronological topics** using TF-IDF + cosine similarity over the substantive (non-procedural) testimony text, with page-distance thresholds instead of pure semantic clustering.
5. Validates every generated topic's page/line boundaries and evidence text against the canonical transcript before it is allowed into the final index - an unverifiable topic is either boundary-clamped to the nearest real line or dropped.
6. Serves the result through a small FastAPI application an attorney can browse, filter, and search.

The system defaults to a **fully deterministic mode with no external LLM/API key required**. An optional LLM assist path exists in the code (`DEPOINDEX_LLM_PROVIDER=openai|ollama`) for topic-boundary decisions, but even in that mode the LLM is never allowed to touch page or line numbers - it only sees immutable chunk IDs and hands boundary decisions back to the deterministic provenance layer.

## 2. Problem Statement

Long depositions (in this case 122 pages / 2,042 lines of testimony) are hard for attorneys to navigate quickly. A plain-text summary or an LLM-generated bullet list is not usable in litigation because it can't be checked - if an AI says "the witness discussed the CFPB settlement," there's no way to confirm that without re-reading the whole transcript, and there's no guarantee the AI didn't paraphrase or hallucinate.

What's actually needed is an index where **every topic entry carries an exact, checkable citation** into the source transcript, in the same page/line format a court reporter and attorneys already use.

## 3. Key Requirements / What the System Solves

- Convert an unstructured deposition PDF into a structured, line-addressable transcript.
- Produce a chronological topic index (not a topic-frequency cloud or non-chronological cluster list) - attorneys read depositions in order, and cross-examination often returns to the same subject later, so ordering matters.
- Guarantee that every citation in the output resolves to a real line that actually exists, with real text.
- Distinguish substantive testimony from procedural content (objections, breaks, exhibit marking, reporter/videographer remarks) without either discarding it silently or letting it pollute topic titles.
- Make the output **reproducible**: the same PDF run twice should produce the same topics, boundaries, and citations.
- Do all of the above **without requiring an LLM/API key** by default, while leaving room for an optional LLM assist.

## 4. Architecture / End-to-End Pipeline

```text
┌──────────────────────────────────────────────────────────────┐
│                   Persis_Yu_Deposition.pdf                   │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 Coordinate-Aware PDF Extraction              │
│                    PyMuPDF Word Bounding Boxes               │
│                                                              │
│  • Per-line text        • Line number                        │
│  • Speaker cue          • Timestamp                          │
│  • Page role                                                 │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Canonical Transcript                      │
│              src/extraction/pdf_extract.py                   │
│                                                              │
│    CanonicalLine records + testimony-page range detection    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Immutable Source IDs                     │
│                        P<page>:L<line>                       │
│                     src/provenance/ids.py                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                   Turn → QA Unit → Chunking                  │
│                   src/segmentation/chunking.py               │
│                                                              │
│                   Turn • QAUnit • Chunk                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Topic Segmentation                       │
│                 TF-IDF + Cosine Similarity                   │
│                 src/segmentation/topics.py                   │
│                                                              │
│         Optional LLM Boundary Assist (off by default)        │
│                 src/segmentation/llm.py                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Provenance Validation                     │
│                 src/provenance/validator.py                  │
│                                                              │
│  • Boundary existence     • Ordering                         │
│  • Evidence cross-check   • Clamp-or-drop                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Completeness Audit                      │
│               src/validation/completeness.py                 │
│                                                              │
│        Page coverage • Line coverage • Gaps • Duplicates     │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                           Outputs                            │
│                                                              │
│  topic_index.json           topic_index.md                   │
│  completeness_report.json   run_summary.json                 │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Attorney-Facing Application             │
│                       app/main.py                            │
│                                                              │
│             Browse • Filter • Search • Verify                │
└──────────────────────────────────────────────────────────────┘
```

Each stage only passes forward data it can prove came from the source transcript - the topic segmenter never invents a page or line number; it only groups pre-existing `CanonicalLine` objects.

## 5. Extraction and Canonical Transcript

Extraction happens in `src/extraction/pdf_extract.py` using PyMuPDF's `page.get_text("words")`, which returns each word with its `(x0, y0, x1, y1, text)` bounding box.

- Words are bucketed into visual rows by rounded `y0`.
- Within a row, words left of `x0 = 95.0` are treated as the printed line-number column; words right of that are the line body.
- A `Page N` footer (`y >= 720`) is used to recover the transcript's own page number, independent of the PDF's physical page index — this matters because the PDF's word-index appendix at the end restarts its own "Page 1" footer, which would otherwise collide with the real testimony page 1.
- Timestamps (`HH:MM`) are read from a fixed right-hand column (`x0 >= 490.0`).
- Page **role** is classified (`transcript`, `index`, `word_index`, `procedural_appendix`, `reporter_certificate`, `errata_declaration`, `csr_certificate`, `redacted_administrative`, `appearances_and_preliminaries`, `unnumbered`) so that non-testimony pages (exhibit index, word index, certificate pages, redacted front matter) are excluded from the testimony line count instead of being silently merged into it.
- The testimony range itself (`testimony_page_start`, `testimony_page_end`) is detected from the first `Q` turn and the "this concludes today" / "deposition concluded" markers, rather than being hardcoded.

Every extracted line becomes a `CanonicalLine` with a `source_id` of the form `P<page>:L<line>`, generated in `src/provenance/ids.py::make_source_id`. These IDs are assigned once at extraction time and never regenerated or renumbered downstream — the topic segmenter, the chunker, and the FastAPI app all consume the same immutable IDs.

## 6. Provenance-First Design

The core citation format is:

```
P7:L12
```

and for a span:

```
P7:L1 - P9:L18
```

or, when a span crosses pages, the cross-page form used internally:

```
P7:L1-P9:L18
```

This matters because it's the same coordinate system a court reporter's own transcript uses — an attorney can open the deposition PDF, go to page 7, count to line 12, and see exactly the sentence DepoIndex is citing. There is no translation layer between "what the AI says" and "what's actually on the page."

Provenance is enforced, not just asserted, by `src/provenance/validator.py::ProvenanceValidator`:

- `loc_exists(page, line)` checks the boundary against the real canonical line index.
- `validate_topic()` rejects a topic if its start doesn't exist, its end doesn't exist, start is after end, any `source_id` in the topic is unknown, or the topic's `supporting_evidence` text doesn't actually overlap with the words found in that page/line span (a lightweight token-overlap check, not just "the text was copied").
- If a topic fails validation, `clamp_boundary()` snaps it to the nearest real line on the same page (or the nearest page if the page itself doesn't exist) and re-validates. If it still fails, the topic is **dropped**, not silently kept with a bad citation.

In the current committed run, 29/29 generated topics pass validation with no boundary clamping needed (confirmed by `tests/test_committed_outputs.py::test_committed_topics_have_valid_source_ids_and_evidence`).

## 7. Topic Segmentation Method

Segmentation happens in `src/segmentation/topics.py` and is deliberately not "ask an LLM to summarize the transcript into topics." It works over the QA-unit/chunk structure built in `src/segmentation/chunking.py`:

1. Testimony lines are grouped into **Turns** (consecutive lines by the same speaker/speaker-kind).
2. Turns are grouped into **QAUnits** — a unit starts when a new `Q` turn begins after the current bucket already contains Q/A/witness content, so a unit roughly corresponds to one question-and-answer exchange (plus any attached objections/colloquy).
3. QAUnits are grouped into **Chunks** up to `DEPOINDEX_CHUNK_CHARS` (default 1800 characters) or `DEPOINDEX_CHUNK_MAX_UNITS` (default 6 units), whichever comes first.
4. A `TfidfVectorizer` (`ngram_range=(1,2)`, English stop words, up to 8,000 features) is fit over the substantive (non-procedural) text of each chunk.
5. Chunks are walked in order. Each chunk is compared by cosine similarity to the running centroid of the current topic group:
   - `CONTINUE_SIM = 0.18` — similarity at or above this, and the topic hasn't already spanned more than `MAX_PAGES_CONTINUE = 8` pages, means "same topic, keep going."
   - Purely procedural chunks are attached to whichever topic is currently open rather than breaking it.
   - Below the continue threshold, the current topic is flushed and a new one starts. Before flushing, the chunk is also compared against the centroids of *all prior topics* — if the best match is at or above `RELATED_SIM = 0.32` and the intervening gap is at least `RECURRENCE_GAP_PAGES = 4` pages, the new topic is tagged as `related_distinct` and links back to the earlier one (see §8).
6. Small trailing groups (under `MIN_TOPIC_CHARS = 350` characters) are merged into the preceding topic rather than left as noise-sized topics.
7. Any topic that still spans more than `MAX_TOPIC_PAGES = 10` pages is split again at the internal chunk-pair with the lowest cosine similarity.
8. Topic labels come from `_first_question()` — the first substantive `Q` turn in the group, with courtesy filler (`"Okay,"`, `"Thank you,"`, `"Correct,"`, etc.) and interrupted `--` fragments stripped — combined with up to three TF-IDF keyphrases in parentheses when the question text is short or generic.
9. Each resulting topic gets a `supporting_evidence` snippet (up to ~420 characters of the actual Q/A/witness text in its span) and a `confidence` score computed as `min(0.95, 0.55 + 0.05 * log(1 + unit_count))` — a simple monotonic function of how many QA units back the topic, not a model-calibrated probability.

If `DEPOINDEX_LLM_PROVIDER` is set to `openai` or `ollama` (it is `none` by default and requires no key to run), the same chunks are additionally sent to an LLM that returns `continue` / `new_topic` / `brief_digression` / `related_distinct` decisions per chunk, at `temperature=0`. The LLM only ever labels a pre-existing chunk; it cannot generate or move a page/line number. If the LLM call fails, times out, returns malformed JSON, or fewer than half the chunks get a decision, the deterministic TF-IDF path above is used instead. **The committed run in this repository was produced with `DEPOINDEX_LLM_PROVIDER=none`** (confirmed in `outputs/run_summary.json`), i.e. purely by the deterministic segmenter.

## 8. Topic Recurrence / Re-entry Handling

The schema supports marking a topic as a re-entry into an earlier subject:

- `TopicRecord.recurrence_of: str | None`
- `TopicRecord.related_topic_ids: list[str]`

The recurrence logic is implemented in `src/segmentation/topics.py`. Each generated topic receives a keyphrase fingerprint, and a later topic can be linked to an earlier topic when the fingerprint matches and the intervening page gap satisfies `RECURRENCE_GAP_PAGES = 4`. This allows the system to distinguish a genuinely reappearing subject from a continuous topic that should remain within the same segment.

**On this deposition, the recurrence path was not triggered.** In the committed `outputs/topic_index.json`, all 29 topics have `recurrence_of: null` and `related_topic_ids: []`. This result is directly verified by `tests/test_committed_outputs.py::test_no_recurrence_links_in_submitted_index`.

The system still correctly handles the important boundary problem: a subject that reappears much later should not cause unrelated intervening testimony to be merged into one large topic. For example, the CFPB settlement / PEAKS-loan-unenforceability subject appears in multiple later portions of the deposition (T021, T028, and T029). The `MAX_PAGES_CONTINUE = 8` constraint prevents these separated passages from being merged into one continuous topic, so they remain distinct chronological entries.

The takeaway is that recurrence detection is an implemented and testable feature, but it did not produce a recurrence link for this particular deposition. The committed output reports the actual behavior rather than claiming a recurrence link that was not generated.

## 9. Verified Results / Project Metrics

All figures below are read directly from `outputs/completeness_report.json`, `outputs/run_summary.json`, and `outputs/topic_index.json`.

| Metric | Value |
|---|---|
| Total PDF pages | 122 |
| Testimony page range | P7 - P88 |
| Testimony pages | 82 |
| Canonical transcript lines (all pages) | 2,233 |
| Testimony lines | 2,042 |
| Chunks | 43 |
| Topics generated | 29 |
| Topics with recurrence link populated | 0 |
| Gaps detected (missing testimony pages/lines) | 0 |
| Duplicate line assignments across topics | 0 |
| Dropped / skipped testimony lines | 0 |
| Invalid provenance references | 0 |
| Missing source IDs | 0 |
| Evidence-text mismatches | 0 |
| Chronological order violations | 0 |
| Manual validation sample | 25 topic entries |
| Location accuracy (computed) | 100% |
| Automated tests (with source PDF present) | 26 passed, 2 warnings |
| Deterministic 3-run comparison | Identical topics, boundaries, source IDs, SHA-256 hashes |

## 10. Completeness Validation

`src/validation/completeness.py::build_completeness_report` performs a deterministic audit, not a spot-check:

- **Page coverage**: every transcript page in the detected testimony range (`testimony_page_start` → `testimony_page_end`, here P7–P88) is checked for presence.
- **Line coverage / gaps**: for each testimony page, if the page-level extractor recorded `missing_lines` (a line number that should exist given the max line seen on that page but wasn't captured), it's reported as a gap.
- **Duplicate detection**: pages where the same printed line number appeared twice in the visual row scan are reported separately from gaps.
- **Silent-skip check**: independently of the page-level extractor's own bookkeeping, the completeness report re-derives, per testimony page, the set of line numbers actually present in the canonical transcript and compares it against the full expected range `1..max(line)`. Any hole here would show up as `gaps_detected`, distinct from the page extractor's own warnings.

Committed result: `gaps_detected: []`, `duplicate_lines: []` - zero testimony-page gaps and zero duplicate line assignments across all 2,042 testimony lines.

`extraction_warnings` (160 entries, `outputs/completeness_report.json`) are a **separate, non-testimony bucket** — they are informational notices from front-matter pages (title page, redacted-administrative notice, exhibit index) and the end-of-document word index, where unnumbered text (headers, index terms, cross-reference numbers) was seen outside the numbered-line columns. These are expected on non-transcript page roles and do not represent lost testimony content; none of them fall on a page inside the P7–P88 testimony range's numbered-line extraction.

## 11. Automated Testing

Test suite: `tests/test_pipeline.py`, `tests/test_api.py`, `tests/test_committed_outputs.py` (26 tests total, run via `pytest`, configured in `pytest.ini`).

- **`tests/test_pipeline.py`** exercises the extraction/segmentation/provenance pipeline directly. All but one of its tests are marked `requires_pdf` and are **skipped automatically** if `data/Persis_Yu_Deposition.pdf` is not present - because the source PDF is intentionally excluded from the repository (`.gitignore`: `data/*.pdf`).
- **`tests/test_committed_outputs.py`** validates the *committed* JSON/Markdown artifacts in `outputs/` and `validation/` directly (topic count, chronological ordering, valid source-ID format, no duplicate line assignment across topics, completeness numbers, manual-validation sample size and location-accuracy value, and the no-recurrence-link assertion described in §8). These tests do **not** require the source PDF.
- **`tests/test_api.py`** exercises the FastAPI endpoints, including the "transcript unavailable" fallback path (see §15) using synthetic fixtures, so it also does not require the source PDF.

Two ways this suite runs in practice:

- **With `data/Persis_Yu_Deposition.pdf` present** (i.e. in the original development environment): `pytest -v` collects and runs all 26 tests - **26 passed, 2 warnings** (the warnings are `StarletteDeprecationWarning`/`DeprecationWarning` noise from the FastAPI/Starlette test client, unrelated to DepoIndex logic).
- **Without the PDF** (e.g. a fresh clone of this public repository, which does not include the source file): the 12 `requires_pdf`-marked tests in `tests/test_pipeline.py` plus one `requires_transcript`-marked test in `tests/test_api.py` are skipped, and the remaining 13 tests — covering committed-output integrity, provenance schema logic, and the API — still run and pass.

## 12. Manual Validation

25 of the 29 generated topics were manually reviewed against the source text (`validation/manual_validation_report.json`, mirrored as `validation/manual_validation_report.md`).

**Location accuracy is the only figure computed as a hard percentage.** Per the JSON report's own `methodology` field: *"Location accuracy is the only percentage computed from citation existence checks. Topic relevance, boundary quality, coverage, and redundancy were assigned as qualitative labels in the review script and are not independent automated measurements."*

- **Location accuracy: 100%** - all 25 sampled topics' start/end citations correspond to real, existing transcript lines in valid chronological order (start ≤ end). This is a genuine computed check, not a reviewer opinion.
- **Topic relevance** - qualitative reviewer judgment. All 25 sampled entries were judged `High` (the topic label accurately reflects the substantive subject of the span).
- **Boundary quality** - qualitative reviewer judgment. Sampled boundaries were judged `Good`; one entry (T012, at P36:L7) is flagged with a reviewer note on a complex simultaneous-speaker boundary, discussed further in §13.
- **Coverage** - qualitative for the sampled spans; separately, the deterministic completeness audit (§10) confirms 0 gaps and 0 duplicates across all 2,042 testimony lines, which is a computed fact rather than a review judgment.
- **Redundancy** - recorded per-entry as `None` in the qualitative review; not a computed metric.

Note: the Markdown mirror of this report (`validation/manual_validation_report.md`) presents "Topic Relevance: 100.0%" and "Boundary Quality: 95.5%" as headline numbers. Per the JSON's own methodology note, these are qualitative labels rendered as summary percentages for readability, not independently computed metrics the way location accuracy is — this README reports them as reviewer judgments accordingly, and no additional percentage is fabricated for redundancy (which the report does not summarize numerically at all).

## 13. Failure Analysis / Difficult Cases

Full detail in `validation/failure_analysis.md`. Four real difficult cases were identified during development:

**Case 1 - Indefinite article "A" misread as a witness-answer marker.** A naive regex `^A\b` on raw extracted text matched the start of ordinary sentences like *"A couple other questions now."* (P9:L20) or *"A small handful of times..."* (P25:L24), wrongly flipping the active speaker to the witness and stripping the leading "A" from the sentence. Root cause: raw text extraction loses the column position that distinguishes a genuine `Q`/`A` speaker label from body text starting with the letter A. Fix: use PyMuPDF word bounding boxes and only treat a leading `Q`/`A` token as a speaker cue if its `x0` falls in the `135.0–160.0` column band; text at a wider `x0` is left as ordinary body text. Verified against `P9:L20` and `P25:L24` directly in `tests/test_pipeline.py::test_geometric_speaker_parsing`.

**Case 2 - Interrupted fragments producing useless topic titles.** At P36:L5–L7, a court-reporter parenthetical (`(Simultaneous speakers.)`) interrupts overlapping speech, and the greedy "first Q turn" label picker originally produced the topic title `"-- talking about?"`. Fix: `_first_question()` now rejects turns starting with `--` or under 3 substantive words, strips courtesy filler, and falls back to the first substantive witness answer or a keyphrase-based label when no usable question exists.

**Case 3 - Non-contiguous topic recurrence vs. monolithic merging.** The CFPB settlement / PEAKS-loan-unenforceability subject is examined three times, separated by ~19 pages of unrelated testimony about government loan programs and investigations (P61–62, then P82–86, then P86–88 → T021, T028, T029). Naive TF-IDF/embedding clustering without a locality constraint would merge all of this into one 26-page topic on shared vocabulary (`cfpb`, `settlement`, `unenforceable`, `peaks`). Mitigation: `MAX_PAGES_CONTINUE = 8` caps continuous-topic growth regardless of similarity, so the three passages are correctly split into three chronologically distinct topics. As noted in §8, the recurrence-link fields that would connect T021↔T028↔T029 are *not* populated in the committed output — the boundary-splitting safeguard worked, but the cross-linking safeguard did not fire for this fingerprint overlap. Possible future improvement: loosen the keyphrase-fingerprint match or add an embedding-similarity fallback specifically for the cross-link step (independent of the page-continuation threshold).

**Case 4 - Off-the-record recesses and procedural colloquy.** Two brief recesses (P37, P76) involve multiple speaker changes (attorneys, the witness, the videographer, a reporter parenthetical) in quick succession. Splitting on every speaker change would create meaningless micro-topics; ignoring the shift entirely risks misclassifying procedural speech as substantive testimony. Fix: `is_procedural_text()` in `src/segmentation/chunking.py` flags recess/objection/off-the-record language, and short procedural units are attached to the enclosing substantive chunk rather than becoming their own topic; a QA unit made up entirely of such content is flagged `is_procedural: true` on the resulting topic (surfaced in the FastAPI app as a filterable flag, §15).

## 14. Three-Run Stability / Reproducibility

`outputs/stability_report.md`, generated by `scripts/compare_runs.py` against three full pipeline executions (`runs/run1`, `runs/run2`, `runs/run3`) with `DEPOINDEX_LLM_PROVIDER=none`:

- **Topic count**: 29 / 29 / 29 - identical.
- **Topic labels**: identical across all three runs.
- **Start and end boundaries** (page:line) for all 29 topics: identical across all three runs.
- **Supporting references** (`"Persis Yu Deposition P<start> - P<end>"`): identical.
- **Source IDs mapped** (2,042 testimony lines): identical.
- **Extracted pages/lines** (122 pages / 2,233 lines): identical.
- **SHA-256 checksums** of `canonical_transcript.json`, `chunks.json`, `completeness_report.json`, `topic_index.json`, and `topic_index.md` matched bit-for-bit across all three runs.

This is possible because every stage in the pipeline is deterministic in this configuration: coordinate-based PyMuPDF extraction, fixed-vocabulary scikit-learn TF-IDF/cosine similarity, and threshold comparisons with no random seeds or sampling anywhere in the deterministic code path.

**Scope of this claim**: this demonstrates reproducibility for *this specific PDF*, run on the *same machine/runtime configuration*, in the deterministic (`DEPOINDEX_LLM_PROVIDER=none`) mode that was actually exercised. It is not a claim that DepoIndex produces bit-identical output for any PDF on any machine, and it explicitly does not cover the optional LLM-assisted mode, which the code deliberately clamps to `temperature=0` and falls back from on error but which still depends on an external, non-deterministic API by nature.

## 15. FastAPI Web Application

`app/main.py`, served with a small static front end in `app/static/` (vanilla HTML/JS/CSS — filterable topic list, a detail pane, and a client-side "semantic search" box).

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the static single-page UI (`app/static/index.html`). |
| `/api/topics` | GET | Returns all topics from `outputs/topic_index.json`. Supports `q` (substring filter over topic text, evidence, and source IDs) and `procedural` (`true`/`false`) query params. Includes `transcript_available` so the UI knows whether full source-line viewing is possible. |
| `/api/topics/{topic_id}` | GET | Returns one topic, its `related` topics (by `related_topic_ids`), and — if the canonical transcript is present — the exact source lines for its span. |
| `/api/search` | GET | TF-IDF + cosine-similarity search over topic titles and evidence text (`q`, `k` params) — a lightweight "find related testimony" tool, separate from the deterministic segmentation itself. |
| `/api/completeness` | GET | Returns `outputs/completeness_report.json` as-is. |
| `/api/validation` | GET | Returns `validation/manual_validation_report.json` as-is (or `{"available": false}` if absent). |
| `/api/provenance/check?topic_id=...` | GET | Re-runs the existence/ordering/source-ID checks for one topic against the live canonical transcript, returning `verification_status: verified/failed/unavailable`. |

**When the canonical transcript isn't available**: `outputs/canonical_transcript.json` is intentionally excluded from the repository because it is a large generated output derived from the source deposition PDF, which is not committed to this repository (listed in `.gitignore`). If it's missing, `/api/topics/{id}` and `/api/provenance/check` still return the topic metadata and citations from the committed `topic_index.json`, but with `transcript_available: false`, `source_lines: []`, and an explicit `transcript_unavailable_reason` string explaining that full line-level verification requires the original transcript/PDF, which is intentionally excluded from this repository. This behavior is covered by `tests/test_api.py::test_topic_detail_without_transcript`.

## 16. Installation

PowerShell, Windows (matches the local project path used during development, `C:\DepoIndex`):

```powershell
git clone https://github.com/ddikshamitraa25/DepoIndex.git
cd DepoIndex

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

copy .env.example .env
```

## 17. Configuration

All configuration is read from environment variables (optionally via `.env`, loaded with `python-dotenv`). See `.env.example`:

```
DEPOINDEX_LLM_PROVIDER=none                         # openai | ollama | none — deterministic segmenter is used by default
OPENAI_API_KEY=                                     # only needed if DEPOINDEX_LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1
DEPOINDEX_PDF_PATH=data/Persis_Yu_Deposition.pdf
DEPOINDEX_TEMPERATURE=0
```

`DEPOINDEX_CHUNK_CHARS` (default `1800`) and `DEPOINDEX_CHUNK_MAX_UNITS` (default `6`) can also be set to tune chunk size, read directly in `src/segmentation/chunking.py::build_chunks`.

**No API key is required to run the pipeline, the tests, or the web app in the default configuration.**

## 18. Running the Pipeline

The source deposition PDF (`Persis_Yu_Deposition.pdf`) is **not committed** to this repository (`.gitignore`: `data/*.pdf`). To reproduce the pipeline end-to-end, place the PDF at `data\Persis_Yu_Deposition.pdf` (or point `DEPOINDEX_PDF_PATH` at it), then:

```powershell
python run_pipeline.py
```

This writes/overwrites `outputs/canonical_transcript.json`, `outputs/chunks.json`, `outputs/topic_index.json`, `outputs/topic_index.md`, `outputs/completeness_report.json`, and `outputs/run_summary.json`.

To reproduce the three-run stability comparison:

```powershell
python run_pipeline.py --run-name run1
python run_pipeline.py --run-name run2
python run_pipeline.py --run-name run3
python scripts/compare_runs.py
```

## 19. Running the Web Application

```powershell
uvicorn app.main:app --reload
```

Then open:

```
http://127.0.0.1:8000
```

The committed `outputs/topic_index.json` and `outputs/completeness_report.json` are enough to browse the topic index and read every citation and evidence snippet; full source-line drill-down additionally requires `outputs/canonical_transcript.json`, produced by running the pipeline against the source PDF (§18).

## 20. Verification Commands

```powershell
python scripts/verify_outputs.py
python scripts/verify_provenance.py
python scripts/verify_completeness.py
pytest -v
python scripts/compare_runs.py
```

`verify_outputs.py` checks that all expected output files exist and prints basic shape info (topic count, first/last topic, line/chunk counts). `verify_provenance.py` re-validates every committed topic's boundaries, source IDs, and evidence text against the canonical transcript and prints a pass/fail summary. `verify_completeness.py` asserts there are no missing testimony pages or dropped lines in the committed completeness report. `compare_runs.py` regenerates `outputs/stability_report.md` from `runs/run1-3` (requires those directories to exist — see §18).

## 21. Project Structure

```
DepoIndex/
├── .env.example
├── .gitignore
├── README.md
├── pytest.ini
├── requirements.txt
├── run_pipeline.py
├── app/
│   ├── __init__.py
│   ├── main.py                         # FastAPI application
│   └── static/
│       ├── app.js
│       ├── index.html
│       └── style.css
├── data/                               # gitignored: place Persis_Yu_Deposition.pdf here to run the pipeline
├── outputs/
│   ├── completeness_report.json
│   ├── run_summary.json
│   ├── stability_report.md
│   ├── topic_index.json
│   └── topic_index.md
│                                       # canonical_transcript.json / chunks.json are also produced here but gitignored (regenerable, large)
├── runs/                               # gitignored: run1/run2/run3 stability-comparison snapshots
├── scripts/
│   ├── compare_runs.py
│   ├── create_presentation.py
│   ├── generate_manual_validation.py
│   ├── test_live_server.py
│   ├── verify_completeness.py
│   ├── verify_outputs.py
│   └── verify_provenance.py
├── slides/
│   ├── DepoIndex_Presentation.pptx
│   └── presentation_transcript.md
├── src/
│   ├── __init__.py
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── models.py                   # CanonicalLine, ExtractedPage, CanonicalTranscript, TopicRecord
│   │   └── pdf_extract.py              # coordinate-aware extraction
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── reports.py                  # topic_index.json / .md writers
│   │   └── run.py                      # run_pipeline() / CLI entrypoint
│   ├── provenance/
│   │   ├── __init__.py
│   │   ├── ids.py                      # source-ID formatting/parsing
│   │   └── validator.py                # ProvenanceValidator, clamp/drop logic
│   ├── segmentation/
│   │   ├── __init__.py
│   │   ├── chunking.py                 # Turn / QAUnit / Chunk, procedural detection
│   │   ├── llm.py                      # optional OpenAI/Ollama boundary assist
│   │   └── topics.py                   # TF-IDF segmentation, labeling, recurrence logic
│   └── validation/
│       ├── __init__.py
│       └── completeness.py             # page/line coverage, gap and duplicate detection
├── tests/
│   ├── test_api.py
│   ├── test_committed_outputs.py
│   └── test_pipeline.py
└── validation/
    ├── failure_analysis.md
    ├── manual_validation_report.json
    └── manual_validation_report.md
```

## 22. Presentation / Demo Deliverables

- `slides/DepoIndex_Presentation.pptx` - a 5-slide, 16:9 presentation deck generated by `scripts/create_presentation.py`.
- `slides/presentation_transcript.md` - a written speaker transcript for the deck.

These are narrative/presentation materials intended to walk a reviewer through the project. This README and the committed JSON/test outputs are the authoritative source for verified project results.

## 23. Known Limitations

- **Requires the source PDF for full reproduction and for most of `tests/test_pipeline.py`.** The source deposition PDF is intentionally excluded from the repository, so a fresh clone can inspect and verify the *committed* outputs and run the API/output-integrity tests, but cannot re-run extraction/segmentation from scratch without supplying the PDF separately.
- **Recurrence linking did not fire on this deposition.** The schema and code path exist (§8), but `related_topic_ids`/`recurrence_of` are empty in the current committed output; three genuinely recurring subjects (§13, Case 3) are correctly split chronologically but not cross-linked.
- **Topic granularity is tuned around this transcript's Q&A cadence.** The chunk-size and similarity thresholds (`CONTINUE_SIM`, `MAX_PAGES_CONTINUE`, `MIN_TOPIC_CHARS`, etc.) were arrived at empirically against this deposition's structure; a transcript with long uninterrupted witness monologues (rather than tight Q&A exchanges) would likely need different tuning or additional sub-sentence boundary detection.
- **Single-witness, single-document design.** The pipeline processes one deposition PDF into one canonical transcript and one topic index; there's no cross-deposition index, multi-witness handling, or exhibit-linking beyond what's mentioned in testimony text.
- **The optional LLM-assist path is not exercised in the committed run.** It exists in `src/segmentation/llm.py` and is covered by the deterministic-fallback logic, but the results in this repository were produced entirely by the TF-IDF/cosine deterministic segmenter (`DEPOINDEX_LLM_PROVIDER=none`).
- **Manual validation covered 25 of 29 topics**, not all of them, and (per §12) only location accuracy is a computed percentage — relevance, boundary quality, and coverage are qualitative reviewer judgments, and the Markdown validation report's headline percentages for those fields should be read with that caveat.
- **No public-facing hosted demo.** The FastAPI app is designed to run locally (`http://127.0.0.1:8000`); this repository does not include or claim a public demo URL.

## 24. Engineering Design Decisions / Trade-offs

**How is a topic defined?** A contiguous, chronologically-ordered run of QA units whose substantive (non-procedural) text stays above a TF-IDF cosine-similarity threshold with the topic's running centroid, up to a page-span cap. It's a segmentation boundary decision, not a fixed taxonomy - there's no predefined list of "topic categories" the system is matching against.

**Why this granularity?** Chunk size (~1800 characters / up to 6 QA units) and the `MIN_TOPIC_CHARS = 350` merge floor were chosen so a topic corresponds to roughly one attorney line of questioning (a handful of related Q&A exchanges) rather than either a single question or an entire multi-page examination — the former is too granular to be useful as an index, the latter defeats the purpose of an index.

**How are topic boundaries chosen?** By cosine-similarity drop below `CONTINUE_SIM` between consecutive chunk vectors and the running topic centroid, subject to the `MAX_PAGES_CONTINUE = 8` hard cap regardless of similarity (so a single subject can't silently swallow the whole deposition, see §13 Case 3), and an internal re-split on oversized groups (`MAX_TOPIC_PAGES = 10`) at their weakest internal similarity point.

**How are continuation vs. re-entry handled?** Continuation = similarity stays high and the topic hasn't hit its page cap. Re-entry = a *new* topic whose keyphrase fingerprint matches a topic that already ended, after a gap of at least `RECURRENCE_GAP_PAGES = 4` pages - implemented, but did not trigger on this deposition's fingerprints (§8).

**How is provenance preserved?** Every object downstream of extraction (chunk, QA unit, topic) carries only references (`source_id`, `source_range`) back to `CanonicalLine` records that were created once, at extraction time, from PDF word coordinates. Nothing downstream is allowed to fabricate or renumber a citation; `ProvenanceValidator` is the single gate that decides whether a generated topic's citations are real before they reach `outputs/topic_index.json`.

**What happens to skipped/procedural content?** It isn't skipped — it's tagged. `is_procedural_text()` flags objections, off-the-record language, and reporter/videographer speech; short procedural stretches are folded into the surrounding substantive topic (so the examination thread isn't fragmented), and a QA unit that's *entirely* procedural produces a topic explicitly labeled `is_procedural: true`, which the FastAPI UI can filter out.

**How is reproducibility ensured?** By avoiding randomness anywhere in the default path: coordinate-based (not OCR-based) PDF extraction, fixed-vocabulary scikit-learn TF-IDF, pure threshold comparisons with no sampling, and an LLM path that's off by default and, when enabled, is clamped to `temperature=0` with an automatic fallback to the deterministic path on any failure.

**How can an attorney verify an entry?** Take the `supporting_source_reference` (e.g. `Persis Yu Deposition P82:L18 - P86:L9`) or any `source_id` in the topic, open the original PDF to that page, and count to that line — or, with the transcript loaded, hit `/api/provenance/check?topic_id=...` and get a machine-checked `verified`/`failed` status against the same canonical data the index was built from.

**What would change at larger scale (multiple depositions, longer transcripts)?** The per-deposition pipeline itself is O(pages), so a much longer single transcript would mostly need larger chunk/topic-count tuning. Multiple depositions would need: a shared source-ID namespace that includes a deposition identifier (not just `P<page>:L<line>`), a cross-deposition topic index rather than one JSON file per matter, and probably an embedding-based similarity step in addition to TF-IDF for cross-document topic matching, since vocabulary won't overlap as tightly across different witnesses' testimony.

## 25. Final Results / Conclusion

Running the deterministic pipeline once against the Persis Yu deposition produced 29 chronologically-ordered, fully-cited topics from 2,042 testimony lines across 82 pages, with zero completeness gaps, zero duplicate line assignments, and zero provenance failures in the committed output. A 25-topic manual sample confirmed 100% location accuracy (the only hard-computed validation metric) with high qualitative marks on relevance and boundary quality. Three independent pipeline runs produced bit-identical artifacts (SHA-256-verified), confirming the deterministic segmenter behaves as designed for this input. Cross-topic recurrence linking is implemented but was not triggered on this deposition; this is documented as a known limitation of the current run rather than claimed as a detected result. The result is a small, auditable system where every claim the index makes about the deposition can be checked against the original transcript in seconds.
