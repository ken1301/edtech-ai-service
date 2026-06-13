You are a senior software engineer working on an educational chatbot system.

## Pre-coding Steps (MANDATORY)
Before writing any code, read and internalize the following files to understand the existing architecture and your task:
- `domain/model/`
- `application/use_cases/chatbot_usecase.py`
- `application/stateless_services/lesson2_service/`
- `vibecode/docs/overall.md`

---

## Your Tasks

### 1. Complete Layer I/O + Core Session Logic
- Define the complete **input and output contracts** for every layer in the pipeline.
- For each input field, write the **construction logic** — i.e., how that value is derived from:
  - `history_msg`, `history_compression`, `session_metadata`
  - outputs from previously-called layers in the same turn
- Implement `compress_history` and `summarize_session`.

---

### 2. Write All Prompts (as `.txt` files, XML-tagged)
Each prompt file must use `<tag>` XML-style tags where each tag name matches the corresponding layer's input field schema.

Write prompts for:

- **Pipeline layers:** `classify`, `ground`, `evaluate`
- **Response layer:** one prompt per phase — `P`, `D`, `E`, `O`
- **Non-learning response prompt** (must include safety handling)
- **Wrap-up response prompt** — triggered after all 4 problems are completed; congratulates the student and gives a brief summary of the 4 problems. Note: this is NOT `summarize_session` — do not include deep pedagogical analysis
- **`compress_history` prompt**
- **`summarize_session` prompt**

---

### 3. Complete Response Directive & Tone Arbiter Logic
- Implement the selection logic for `response_directive`
- Implement the decision logic for `tone_arbiter`

---

### 4. Complete `state_writer_layer` Logic
All layer I/O should treat `session_metadata` as the source of truth. Design data flow accordingly. Example pattern:
> The `evaluate` layer compresses `student_reasoning` across message turns → writes it into the metadata for that approach → `ground_layer` reads `student_reasoning` from metadata as its input.

Apply this pattern consistently across all layers.

---

### 5. Implement Progress Calculation on Submission
Write the logic to calculate how much **progress** is added (or subtracted) when a student makes a submission.