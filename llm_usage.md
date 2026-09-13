# AI / LLM Usage

AI-assisted development tools were used during the development of DepoIndex as development and debugging assistants.

## How AI Was Used

AI assistance was used for the following development tasks:

- Drafting and refining parts of the PyMuPDF-based PDF extraction and page/line provenance logic.
- Assisting with debugging transcript extraction and speaker-attribution issues.
- Reviewing and improving the topic segmentation implementation and handling of continuation, digression, and recurrence cases.
- Assisting with API and frontend implementation details for the verification and topic-index interface.
- Assisting with test-case ideas, debugging, and documentation.
- Reviewing the validation and stability methodology and suggesting edge cases to check.

AI was used as an engineering aid rather than as the source of truth for the generated Topic Index.

## AI Output That Was Rejected or Modified

AI-generated suggestions were not accepted without verification.

One important design decision was to reject approaches that would generate or reconstruct page/line references independently from the source transcript. Approximate or regenerated references would not satisfy the provenance requirement of the assignment.

The final implementation instead anchors every Topic Index entry to the canonical transcript and source IDs created during PDF extraction. Page and line references are preserved through the extraction and segmentation pipeline and are verified against the canonical transcript.

AI-generated code and suggestions were also modified where necessary to fit the deterministic pipeline, existing project structure, validation requirements, and actual deposition data.

## How AI-Assisted Code Was Validated

AI-assisted code was validated through multiple checks:

- The complete automated test suite was executed successfully.
- The complete deposition was processed through the pipeline.
- The generated canonical transcript was checked for page and line addressability.
- Topic source IDs were checked against the canonical transcript.
- Provenance validation was performed to verify that generated references resolve to actual source lines.
- 25 Topic Index entries were manually reviewed against the deposition.
- Location accuracy was calculated from the manually reviewed entries.
- Completeness checks were performed to detect missing or duplicated testimony lines.
- The complete pipeline was executed three times on the same deposition and the resulting topic counts, labels, boundaries, source references, and output hashes were compared.
- The deployed application was tested to verify topic drill-down and source provenance verification.

## Role of AI in the Final System

The final committed Topic Index was generated using the deterministic TF-IDF-based segmentation pipeline. The optional LLM-assisted segmentation path was implemented as an alternative approach but was not used for the committed default run.

The final output was therefore evaluated using deterministic processing, automated validation, source-level provenance checks, manual review, and repeated-run stability testing rather than relying solely on AI-generated output.

## Principle

AI assistance was used to accelerate development, debugging, and review, while implementation decisions and final results were verified against the source deposition and through automated and manual validation.
