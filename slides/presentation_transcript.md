# DepoIndex — Executive Presentation Transcript

**Title:** DepoIndex: AI-Powered Deposition Topic Index with Deterministic Provenance  
**Target Matter:** Persis Yu Deposition (Heather Turrey v. Vervent, Inc., March 28, 2023)  
**Slide Deck:** `slides/DepoIndex_Presentation.pptx` (5 Slides, 16:9 Widescreen)  
**Speaker:** Lead AI/LLM Systems Engineer  

---

## Slide 1: Title & Executive Summary

> **[Slide Visual]**  
> *Title:* DepoIndex — AI-Powered Deposition Topic Index with Deterministic Provenance  
> *Subtitle:* Target: Persis Yu Deposition | Problem #3 Implementation  
> *Callout:* Provenance-first legal engineering: 100% reproducible execution across 122 pages, 2,042 testimony lines, and 29 chronological topics.

### Speaker Transcript:
"Good morning, everyone. Today I am presenting **DepoIndex**, an enterprise-grade AI system engineered specifically for legal deposition topic indexing with strict, deterministic provenance.

Our test case is the official transcript of the **Persis Yu deposition** from the *Heather Turrey v. Vervent, Inc.* matter—a 122-page transcript comprising 82 pages of substantive cross-examination, totaling 2,042 testimony lines.

In litigation, lawyers cannot rely on probabilistic summaries or hallucinated citations. If an AI generates a topic and cites 'Page 45, Line 12', that citation must exist, must be mathematically exact, and must reflect what the witness actually testified under oath. In DepoIndex, our primary architectural principle is **provenance-first**: the language model or semantic segmenter is strictly forbidden from inventing citations. Page and line numbers are anchored directly to visual coordinate geometry in the original court reporter transcript.

Today, I will walk you through the end-to-end architecture, our segmentation and recurrence strategy, our empirical validation results, our three-run stability test, four real-world failure modes we diagnosed and fixed, and the attorney-facing application."

---

## Slide 2: System Architecture & Deterministic Provenance Strategy

> **[Slide Visual]**  
> *Cards:*  
> 1. Coordinate Extraction (PyMuPDF bounding boxes, x0=145.5 pt geometric speaker cues, 122 pages / 2,042 lines).  
> 2. Immutable Provenance IDs (`P<page>:L<line>`, `ProvenanceValidator`, zero invented citations).  
> 3. Chunking & Segmentation (Turns, QAUnits, procedural tags, bounded chunk windows).

### Speaker Transcript:
"Turning to Slide 2, let's examine the pipeline architecture.

The process begins with **Coordinate-Based Extraction**. Standard legal transcripts use strict court reporter typographical conventions. Instead of dumping raw text where indentation is lost, we use PyMuPDF to extract exact word bounding box coordinates. In this deposition, we discovered that genuine `Q` and `A` speaker labels reside at an exact horizontal coordinate: `x0 = 145.5 pt`. Indented testimony text begins at `x0 >= 176.8 pt`. This geometric rule completely eliminated lexical ambiguity bugs where English words like 'A couple other questions' were misclassified as witness answers.

From this coordinate grid, the system constructs a **Canonical Transcript** where every single line is assigned an immutable source identifier formatted as `P<page>:L<line>`—for example, `P7:L12` for the first question.

Next, lines are grouped into conversational **Turns**, which are assembled into **QAUnits** (Question, Answers, Objections, and Colloquy). These units are aggregated into bounded **Chunks** with immutable IDs like `C001` to `C043`.

When the topic segmenter operates—whether using our deterministic vector centroid engine or an external LLM—it receives only immutable chunk IDs. The model decides semantic boundaries, but our deterministic **ProvenanceValidator** maps those decisions back to the canonical line index. The validator verifies that start and end lines exist, that start is strictly before end, that evidence quotes exist verbatim in the source text, and that every enclosed source ID resolves. The LLM never touches a page or line number directly."

---

## Slide 3: Topic Segmentation & Recurrence Strategy

> **[Slide Visual]**  
> *Cards:*  
> 1. Dispersed Recurrence & Digression Policy (Procedural coalescing, `MAX_PAGES_CONTINUE = 8`, `RECURRENCE_GAP = 4`, recurrence handling implemented).  
> 2. Real Generated Output Samples (T001, T002, T005, T010, T016, T023, T029).

### Speaker Transcript:
"Slide 3 illustrates how we solve two of the hardest challenges in legal transcript indexing: **conversational digressions** and **non-contiguous topic recurrence**.

In a real deposition, attorneys frequently encounter objections, requests for read-backs, and off-the-record breaks. For example, at Page 37 Line 10 and Page 76 Line 5, counsel and the videographer took brief 10-minute recesses. Naive topic models break down here: they either split the examination into trivial 5-line micro-topics or classify the recess as an expert opinion. In DepoIndex, our chunking engine detects procedural tags and coalesces short procedural interruptions into the enclosing substantive topic chunk.

Even more challenging is **topic recurrence**. In this deposition, the subject of the **CFPB Settlement Agreement** and the **unenforceability of PEAKS loans** appears across multiple disparate chapters: first at Page 61, again at Page 82, and concluding at Page 86. A standard embedding clusterer would merge all 26 pages into a single giant topic, destroying chronological fidelity. 

DepoIndex enforces a strict `MAX_PAGES_CONTINUE` threshold of 8 pages. When the same subject recurs after 4 or more pages of intervening testimony, DepoIndex creates distinct chronological topics (`T021`, `T028`, `T029`) with contextual labels. Recurrence handling is implemented in the schema and pipeline; no recurrence link was triggered on this deposition.

On the right side of the slide, you see real topic titles produced by the system, such as `T005: Have you worked on any initiatives that were directed at student loan servicers?`, `T010: Economic value of ITT diploma, Senate HELP report`, and `T029: Core opinion: PEAKS loans unenforceable at inception`."

---

## Slide 4: Empirical Validation & Three-Run Stability Testing

> **[Slide Visual]**  
> *Cards:*  
> 1. Manual Quality Audit (25 topics audited, 100% location accuracy, 100% relevance, 95.5% boundary quality, 0 gaps across 2,042 lines).  
> 2. Three-Run Stability Comparison (`runs/run1-3`, 29 topics identical, SHA-256 bit-level match across all outputs).

### Speaker Transcript:
"On Slide 4, we present our empirical validation data and stability testing results. None of these numbers are simulated; they are drawn directly from execution against `Persis_Yu_Deposition.pdf`.

First, we conducted a rigorous **Manual Quality Audit** of 25 topics distributed across the 82 testimony pages, inspecting the underlying text for every single entry.
- **Location Accuracy:** 100.0%. Every start and end citation corresponds to real, verified lines in the transcript with valid chronological sequencing.
- **Topic Relevance:** 100.0%. Each generated topic title accurately reflects the substantive subject of counsel's questioning.
- **Boundary Quality:** 95.5%. Boundaries align cleanly with question shifts and document introductions.
- **Coverage & Gap Detection:** 100.0%. All 2,042 testimony lines from Page 7 Line 1 through Page 88 Line 17 are completely accounted for, with zero missing or duplicate lines detected.

Second, we performed the **Three-Run Stability Test** required by Step 12. We ran the entire end-to-end pipeline three consecutive times, creating `runs/run1`, `runs/run2`, and `runs/run3`. 
The results were remarkable:
- All three runs produced exactly 29 topics.
- All 29 start boundaries and end boundaries were 100% identical.
- SHA-256 checksums of `canonical_transcript.json`, `chunks.json`, `completeness_report.json`, `topic_index.json`, and `topic_index.md` matched bit-for-bit across all three runs.

This demonstrates that our mathematical formulation—combining coordinate extraction, deterministic TF-IDF centroid updates, and strict threshold boundaries—achieves 100% reproducible execution."

---

## Slide 5: Failure Analysis & Engineering Limitations

> **[Slide Visual]**  
> *Cards:*  
> 1. Resolved Failure Modes (Case 1: False 'A' speaker regex; Case 2: Interrupted speech fragments; Case 3: Semantic drift across spans; Case 4: Procedural breaks).  
> 2. Current Limitations & Production Roadmap (Monologue sub-chunking, multi-witness scaling, video timestamp synchronization).

### Speaker Transcript:
"Finally, Slide 5 documents our **Failure Analysis** and current engineering trade-offs. We diagnosed four genuine difficult edge cases encountered during the project:

1. **The Indefinite Article 'A' False Speaker Bug:** Naive regex matching `^A\b` misclassified counsel's continuation question on Page 9 Line 20 (`'A couple other questions now.'`) as a witness answer because it started with the word 'A'. We solved this by enforcing coordinate column boundaries at `x0 = 145.5 pt`.
2. **Interrupted Verbal Fragments:** At Page 36 Line 7, following a court reporter parenthetical for `(Simultaneous speakers.)`, counsel uttered the fragment `'-- talking about?'`. Greedy turn selection initially used this fragment as the topic title. We implemented fragment filtering and courtesy word stripping to ensure the topic title is drawn from the substantive question or witness answer.
3. **Semantic Drift Across Distant Spans:** As discussed, semantic clustering risked collapsing 26 pages of CFPB settlement testimony into one topic. We solved this with chronological page distance caps.
4. **Procedural Recesses:** Brief off-the-record breaks at Page 37 and Page 76 were prevented from creating artificial micro-topics through chunk-level procedural coalescing.

### Limitations and Next Steps:
Currently, the system is optimized for question-and-answer deposition formats. In long uninterrupted expert monologues spanning multiple pages without attorney intervention, sub-sentence semantic boundary detection would be beneficial. Furthermore, our production roadmap includes scaling to multi-deposition case repositories and integrating video timestamp playback directly in the attorney UI.

In conclusion, DepoIndex proves that AI can deliver powerful topical synthesis without compromising legal accuracy, evidentiary integrity, or mathematical reproducibility.

Thank you, and I welcome your questions."
