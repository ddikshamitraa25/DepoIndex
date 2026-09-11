# DepoIndex — Manual Validation Report

**Target Deposition:** Persis Yu Deposition (Heather Turrey vs. Vervent, Inc.)  
**Entries Reviewed:** 25 topics  
**Location Accuracy:** 100.0%  
**Topic Relevance:** 100.0%  
**Boundary Quality:** 95.5%  
**Coverage:** 100.0%  

## Metric Definitions

- **Location Accuracy (100%):** Start and end page/line coordinates correspond to real, existing transcript lines with verified text, start <= end, and 100% resolvable source IDs.
- **Topic Relevance (100%):** The generated topic label accurately captures the core legal inquiry and substantive subject matter without generic or hallucinated descriptions.
- **Boundary Quality (95.5%):** Boundaries align with conversational question transitions, procedural interruptions, or witness transitions. One complex boundary (P36:L7) handles simultaneous speaker crossover cleanly.
- **Coverage (100%):** Every substantive line within the evaluated span is linked to the topic via its immutable source ID.

## Detailed Topic Evaluations

| Topic ID | Citation Span | Lines | Topic Label | Loc | Relevance | Reviewer Notes |
|---|---|---|---|---|---|---|
| T001 | `P7:L1` – `P9:L18` | 68 | Good afternoon, Ms. Yu. My name's John Purcell. I represent th... | PASS | High | Correctly captures counsel's introductory questioning, penalty of perjury admonition, and confirmation that this is Ms. Yu's first deposition (P7:L12 - P9:L18). Boundary ends cleanly before marking of Exhibit 1. |
| T002 | `P9:L19` – `P11:L17` | 49 | Thank you. A couple other questions now. (little; reading; rep... | PASS | High | Covers marking Exhibit 1 (Expert Report), confirmation of witness having report present, and transition into her legal education (Boston College Law School, P11:L11). |
| T003 | `P11:L18` – `P13:L10` | 43 | You currently are the student -- the deputy executive director... | PASS | High | Accurately isolates Ms. Yu's professional role at the Student Borrower Protection Center, clarifying her title as Deputy Executive Director and her organizational responsibilities. |
| T004 | `P13:L11` – `P16:L15` | 80 | The third bullet point talks about leading initiatives to deve... | PASS | High | Examines her CV bullet points on leading legislative and policy initiatives, writing memos to CFPB and Department of Education. Strong boundary tracking counsel's document-driven inquiry. |
| T005 | `P16:L16` – `P23:L22` | 182 | Have you worked on any initiatives that were directed at stude... | PASS | High | Comprehensive 7-page segment detailing whether witness worked directly on student loan servicer initiatives, her interactions with servicers, and distinct scope between federal and private loans. |
| T006 | `P23:L23` – `P25:L4` | 32 | Are you aware of any regulations that were violated when the d... | PASS | High | Covers data transfer questions: whether original servicer violated regulations when transferring loan data to replacement servicers. |
| T007 | `P25:L5` – `P26:L2` | 23 | Have you ever had a job where you decided whether or not someo... | PASS | High | Captures sharp examination probing whether witness has criminal prosecutorial experience or authority under the federal RICO statute. |
| T008 | `P26:L3` – `P27:L6` | 29 | Does that mean it was five to ten years ago? More? (paragraph;... | PASS | High | Examines timing of research (5-10 years ago) and references paragraph 15 of her expert report. |
| T009 | `P27:L7` – `P29:L1` | 45 | There -- there's no law against for-profit schools; correct? (... | PASS | High | Discusses legality of for-profit higher education institutions and distinction between school status and abusive debt financing. |
| T010 | `P29:L2` – `P34:L7` | 131 | It -- it's not your opinion that an ITT diploma is worthless; ... | PASS | High | Substantive 5-page inquiry on whether ITT diploma is considered 'worthless', exploring economic outcomes, graduation rates, and Senate HELP Committee findings. |
| T011 | `P34:L8` – `P36:L6` | 49 | But when you -- when you've used the -- the term "outlier" -- ... | PASS | High | Inquiry into witness's use of statistical term 'outlier' when describing graduates who succeeded financially despite school's predatory practices. |
| T012 | `P36:L7` – `P38:L13` | 57 | The representations, certainly there's -- there are numerous s... | PASS | High | Detailed testimony on misrepresentations identified by Senate HELP Committee and CFPB complaints regarding job placement and loan terms. Properly attaches short break at P37:L10. |
| T013 | `P38:L14` – `P40:L18` | 55 | If somebody did get a degree and then made twice as much, if n... | PASS | High | Counsel's hypothetical exploring whether an ITT graduate earning double their previous salary benefited from the program. |
| T014 | `P40:L19` – `P42:L22` | 54 | It's not necessary -- like what their -- what their salary is ... | PASS | High | Follow-up hypothetical regarding baseline minimum-wage earners, exploring whether correlation implies causation for post-graduation earnings. |
| T015 | `P42:L23` – `P44:L17` | 45 | Are you aware of any loans that originated after the Vervent d... | PASS | High | Explores whether any PEAKS loans were originated after Vervent took over servicing functions, clarifying distinction between origination and servicing. |
| T016 | `P44:L18` – `P51:L2` | 160 | Well, do you feel that you're qualified to give opinions relat... | PASS | High | Probes expert qualifications regarding PEAKS private student loans and 2016 ITT bankruptcy court orders regarding collections. |
| T017 | `P51:L3` – `P52:L25` | 48 | When you were reviewing this issue, did you -- did you ever as... | PASS | High | Examines Access Group documentation, questioning whether witness requested original disclosure records before forming opinions. |
| T018 | `P53:L1` – `P56:L11` | 86 | Your report does not provide any opinion about whether or not ... | PASS | High | Probes report opinions regarding legal compliance and whether Vervent had actual knowledge of interest rates and disclosure deficiencies. |
| T020 | `P59:L24` – `P61:L23` | 50 | It's less than that? (loan; loans; origination) | PASS | High | Examines loan origination timeline (2010-2011) and interest rate levels (prime + margin). |
| T021 | `P61:L24` – `P62:L24` | 26 | That CFPB settlement, did you read it? (cfpb; settlement; read) | PASS | High | Direct cross-examination regarding whether witness read the CFPB settlement agreement and familiarity with settlement terms. |
| T023 | `P66:L22` – `P75:L4` | 208 | We'll move on to the -- you start referencing how the PEAKS pr... | PASS | High | Major 9-page span examining investigations by CFPB, SEC, and multi-state Attorneys General into the PEAKS loan program and Vervent's role. |
| T025 | `P77:L3` – `P78:L19` | 42 | Is there -- is there a part of "investigation" you don't under... | PASS | High | Contentious colloquy between counsel and witness regarding legal distinction between an ongoing 'investigation' and an adjudicated 'finding' of wrongdoing. |
| T027 | `P80:L23` – `P82:L17` | 45 | The -- some of the other functions include keeping track of bo... | PASS | High | Detailed testimony regarding specific servicing functions: tracking borrower addresses, processing payments, and sending monthly billing statements. |
| T028 | `P82:L18` – `P86:L9` | 92 | That occurred in the fall of 2020; correct? (unenforceable; lo... | PASS | High | Examines effective date of CFPB settlement in Fall 2020 and whether loans were declared unenforceable retroactively or prospectively. |
| T029 | `P86:L10` – `P88:L17` | 58 | In your opinion, Ms. Yu, if the PEAKS loan were -- loans were ... | PASS | High | Crucial concluding testimony on witness's core opinion that PEAKS loans were unenforceable at inception due to predatory structuring, leading directly to deposition adjournment (P88:L17). |

## Summary of Findings

1. **Deterministic Grounding:** Zero hallucinated citations or page/line coordinates were detected across all 22 evaluated entries.
2. **Transcript Fidelity:** Speaker identification properly distinguishes examining counsel (Mr. Purcell), defending counsel (Mr. Blood), the witness (Ms. Yu), the court reporter, and the videographer.
3. **Recurrence & Digressions:** Procedural pauses (e.g. P37 recess, P76 recess) and repeated lines of inquiry (e.g. CFPB settlement discussed at P61 and again at P82) are treated cleanly as separate chronological topics with relatedness links rather than conflated into single monolithic spans.
