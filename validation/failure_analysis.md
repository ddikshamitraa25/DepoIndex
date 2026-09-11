# DepoIndex — Failure Analysis & Edge-Case Engineering Report

## Executive Summary

During the development, audit, and validation of DepoIndex against the 122-page **Persis Yu Deposition** (`Persis_Yu_Deposition.pdf`), several critical failure modes and edge cases were identified. This document analyzes four real difficult cases encountered in the transcript, explaining:
1. What the system produced (or would have produced under baseline approaches)
2. What should have been produced
3. Why the failure occurred (root-cause analysis)
4. The deterministic engineering improvement implemented to resolve it

---

## Case 1: Indefinite Article "A" False Speaker Misclassification at Page Transitions

- **Location:** Page 9, Line 19–21 (`P9:L19 - P9:L21`) and Page 25, Line 23–25 (`P25:L23 - P25:L25`)
- **Category:** Speaker Classification / Page Transitions / Lexical Ambiguity

### 1. What System Originally Produced
The initial text-based regular expression in `pdf_extract.py`:
```python
_SPEAKER_A = re.compile(r"^A\b")
```
matched any text line whose trimmed content began with the letter `A` followed by a word boundary. 

On Page 9, Line 20:
- Line 19: `Q    So thank you.`
- Line 20: `     A couple other questions now.`
- Line 21: `A    Sure.`

The baseline extractor matched `^A\b` on Line 20 (`"A couple other questions now."`), stripped the leading `"A "`, classified Line 20 as speaker `A` (witness), and left the text as `"couple other questions now."`! It then treated Line 21 (`"A Sure."`) as a second consecutive answer.

Similarly on Page 25, Line 24:
- Line 23: `Q    And how many times have you done that?`
- Line 24: `A    A small handful of times.  Less than half a --`
- Line 25: `     less than half a dozen.`

The regex stripped the witness's opening word `"A "` from her answer `"A small handful of times."`

### 2. What Should Have Been Produced
- **Page 9, Line 20:** Counsel Mr. Purcell is continuing his question: `"So thank you. A couple other questions now."` The speaker must remain `Q`, and the word `"A"` must not be stripped. Witness Ms. Yu responds on Line 21: `"Sure."` (Speaker `A`).
- **Page 25, Line 24:** Witness Ms. Yu begins her answer with the speaker marker `A`, and the substantive text begins with the word `"A small handful of times..."`

### 3. Why It Failed
Deposition transcript text formats do not use JSON or XML tags; they rely on typographical indentation and court reporter spacing conventions. In raw string extraction without coordinates, the string `"A couple other questions now."` is lexically indistinguishable from `"A  Couple other questions now."`

### 4. Improvement Implemented
PyMuPDF word bounding boxes expose coordinate geometries `(x0, y0, x1, y1, text)`. Analysis of all 122 pages in `Persis_Yu_Deposition.pdf` proved:
- Every genuine `Q` speaker label occurs at `x0 == 145.5` (218 occurrences).
- Every genuine `A` speaker label occurs at `x0 == 145.5` (176 occurrences).
- Indented body text begins at `x0 >= 176.8`.

We implemented geometric cue extraction in `extract_page_lines`:
```python
speaker_cue: str | None = None
if body_words and body_words[0][4] in ("Q", "A") and 135.0 <= body_words[0][0] <= 160.0:
    speaker_cue = body_words[0][4]
    body_words = body_words[1:]
```
If a line starts with the word `"A"` at `x0 > 160.0`, `speaker_cue` is `None`. The word `"A"` is preserved as part of the substantive text, and the active speaker does not change.

---

## Case 2: Simultaneous Speakers and Interrupted Verbal Fragments at Topic Boundary

- **Location:** Page 36, Lines 5–15 (`P36:L5 - P36:L15`)
- **Category:** Ambiguous Boundaries / Colloquy & Interruptions

### 1. What System Produced
At `P36:L5 - P36:L7`, examining counsel and the witness spoke simultaneously:
- `P36:L5 A: Their --`
- `P36:L6 PROCEEDING: (Simultaneous speakers.)`
- `P36:L7 Q: -- talking about?`
- `P36:L8 A: So the representations, certainly there's -- there are numerous sources that cite to misrepresentations with regard specifically to the financing of the education...`

The initial question extractor greedily selected the first `Q` line in the chunk (`P36:L7`), producing an uninformative topic title:
`"-- talking about? (degree; talking; somebody)"`

### 2. What Should Have Been Produced
An attorney reviewing the index needs to know that this section contains Ms. Yu's detailed testimony on **misrepresentations regarding ITT education financing cited in Senate HELP Committee and CFPB investigation reports**.

### 3. Why It Failed
The original `_first_question()` function selected the earliest turn with `speaker_kind == "Q"`, failing to inspect whether the turn was a truncated conversational fragment caused by mid-sentence interruption or court reporter parentheticals (`Simultaneous speakers`).

### 4. Improvement Implemented
1. Updated `_first_question()` to reject turns that start with leading dashes (`--`) or contain fewer than 3 substantive words.
2. Filtered conversational filler / courtesy preambles (`"Thank you"`, `"Okay"`, `"Sure"`).
3. If counsel's question was an interrupted fragment, the system falls back to the substantive witness turn or keyphrase summary, generating:
   `"The representations, certainly there's -- there are numerous sources that cite to misrepresentations with regard..."`

---

## Case 3: Dispersed Topic Recurrence vs. Monolithic Spanning: CFPB Settlement & Loan Unenforceability

- **Location:** Page 61 (`T021`), Page 82 (`T028`), and Page 86 (`T029`)
- **Category:** Topic Recurrence vs. Monolithic Merging / Non-Contiguous Testimony

### 1. What System Produced / Potential Risk
In the deposition, counsel questions Ms. Yu regarding the **CFPB Settlement Agreement** and whether PEAKS loans were **legally unenforceable** across multiple non-contiguous chapters:
1. `P61:L24 - P62:L24`: Counsel asks if Ms. Yu personally read the CFPB settlement agreement (`T021`).
2. `P63:L1 - P82:L17`: Intervening 19 pages exploring government loan programs, state AG investigations, Department of Education findings, and loan servicing functions.
3. `P82:L18 - P86:L9`: Counsel returns to the CFPB settlement, asking whether the settlement occurred in Fall 2020 and whether loans were unenforceable (`T028`).
4. `P86:L10 - P88:L17`: Counsel drills down on Ms. Yu's ultimate opinion that PEAKS loans were unenforceable at inception (`T029`).

Under standard semantic clustering (e.g. naive TF-IDF or embedding clustering without chronological locality constraints), the high cosine similarity between the passages (shared terms: `cfpb`, `settlement`, `unenforceable`, `peaks`, `loans`) would merge all 26 pages into a single giant topic.

### 2. What Should Have Been Produced
Three distinct chronological topics:
- `T021`: `P61:L24 - P62:L24` — Review of CFPB settlement document.
- `T028`: `P82:L18 - P86:L9` — Timing of Fall 2020 settlement and unenforceability findings.
- `T029`: `P86:L10 - P88:L17` — Witness opinion on unenforceability at inception.

Each topic must retain exact page/line boundaries and cross-reference the earlier related topics via `recurrence_of` or `related_topic_ids`.

### 3. Why It Failed in Baseline Systems
Embeddings and TF-IDF vectors measure topic semantics but are blind to chronological structure and legal examination dynamics. Merging distant passages violates the attorney requirement to inspect chronological testimony flow.

### 4. Improvement Implemented
Implemented strict boundary constraints in `src/segmentation/topics.py`:
- `MAX_PAGES_CONTINUE = 8`: Even if semantic similarity remains high, no topic may extend continuously beyond 8 pages without a transition check.
- `RECURRENCE_GAP_PAGES = 4`: If a similar topic fingerprint recurs after >= 4 pages of intervening testimony, it is instantiated as a **new distinct topic record** with `transition_type = "related_distinct"` and `related_topic_ids` linking the prior span.

---

## Case 4: Handling Off-the-Record Recesses & Procedural Colloquy

- **Location:** Page 37, Lines 5–15 (`P37:L5 - P37:L15`) and Page 76, Lines 5–12 (`P76:L5 - P76:L12`)
- **Category:** Objections & Digressions / Procedural Interruptions

### 1. What System Produced
On Page 37:
- `P37:L5 MR. PURCELL: break now.`
- `P37:L6 THE WITNESS: Okay.`
- `P37:L7 MR. BLOOD: Ten minutes?`
- `P37:L8 MR. PURCELL: Sure.`
- `P37:L9 MR. BLOOD: Okay.`
- `P37:L10 THE VIDEOGRAPHER: We are going off the record at 2:00 P.M.`
- `P37:L12 PROCEEDING: (A brief recess was taken.)`
- `P37:L13 THE VIDEOGRAPHER: We are going back on the record at 2:12 P.M.`
- `P37:L15 BY MR. PURCELL:`
- `P37:L16 Q: Ms. Yu, you understand that you're still under penalty of perjury; correct?`

If treated as an independent topic, this creates a useless 10-line topic ("Ten minutes? / We are going off the record"). If ignored, the sudden shift in speakers and text causes segmentation breaks.

### 2. What Should Have Been Produced
The procedural recess should be coalesced into the ongoing substantive topic chunk (`T012`: ITT Misrepresentations & Valuation) without creating fragmented micro-topics, while still tagging the parenthetical and videographer speech as procedural colloquy.

### 3. Why It Failed in Baseline Systems
Naive chunkers either treat every speaker change as a boundary (splitting on `THE VIDEOGRAPHER`) or fail to identify that the recess is procedural, misattributing it as an opinion segment.

### 4. Improvement Implemented
In `src/segmentation/chunking.py`:
1. `is_procedural_text()` checks for keywords (`off the record`, `on the record`, `recess`, `penalty of perjury`, `objection`).
2. `build_chunks()` attaches short procedural units (< 6 turns) to the enclosing substantive chunk so that the attorney's examination thread is preserved unbroken.
3. Pure procedural topics are flagged with `is_procedural: true` and can be toggled on/off in the attorney UI.

---

## Summary of Architectural Safeguards

| Failure Risk | Root Cause | Implemented Safeguard | Verification |
|---|---|---|---|
| Misidentifying word "A" as speaker | Lexical ambiguity | Strict X-coordinate column boundary (`135 <= x0 <= 160`) | 100% of 2233 lines verified |
| Uninformative topic title from interrupted fragment | Greedy turn selection | Filter leading `--`, courtesy filler, require >= 3 words | 29 topics verified |
| Monolithic topic merging across 25 pages | Semantic embedding drift | `MAX_PAGES_CONTINUE = 8`, `RECURRENCE_GAP = 4` | Distinct chronological spans with `related_topic_ids` |
| Micro-topic fragmentation on breaks/objections | Semantic shift on procedure | Procedural coalescing within chunking algorithm | Breaks at P37 and P76 absorbed cleanly |
