# 2026-11-09 — Reflection graph

## RU
- **Что изменилось:** reflection-цикл реализован как граф LangGraph `generate → critique → (generate | finalize)` с событиями прогона (`IterationStarted`, `DraftChunk`, `DraftDone`, `CritiqueDone`).
- **Зачем:** цикл останавливается, когда критик одобрил черновик или score ≥ `approve_threshold`; иначе — по `max_iterations`.
- **Влияние:** если лимит итераций исчерпан, итогом становится черновик с наибольшим score (при равенстве — более поздний), а не просто последний.

## EN
- **What changed:** the reflection loop is a LangGraph graph `generate → critique → (generate | finalize)` that emits run events (`IterationStarted`, `DraftChunk`, `DraftDone`, `CritiqueDone`).
- **Why:** the loop stops when the critic approves or score ≥ `approve_threshold`; otherwise at `max_iterations`.
- **Impact:** when the iteration limit is hit, the result is the highest-scored draft (later wins ties), not simply the last one.
