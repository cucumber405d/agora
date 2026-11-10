# 2026-11-10 — Critic feedback text, full critique in the feed

## RU
- **Что изменилось:** у вердикта критика появилось обязательное поле `feedback` — общий отзыв в 1–3 предложения, даже при одобрении. Лента показывает критику полностью: оценку, отзыв, `Issues` и `Suggestions` (раньше предложения не отображались). Когда приходит итог, черновики итераций сворачиваются, а критика под ними остаётся видна, так что полный текст ответа на экране один раз. Инструкция критика стала строже: утверждения, не подтверждённые контекстом, считаются замечаниями, 9–10 баллов только без замечаний. Отзыв попадает генератору при доработке и в экспорт `F6`.
- **Зачем:** при одобрении на первой итерации критика состояла только из числа, а ответ на экране дублировался.
- **Влияние:** своя инструкция критика (`reflection.prompts.critic`) должна просить и поле `feedback`; без него ответ считается невалидным.

## EN
- **What changed:** the critic's verdict has a required `feedback` field — an overall assessment in 1–3 sentences, also when approved. The feed shows the full critique: score, feedback, `Issues` and `Suggestions` (suggestions were not shown before). When the final answer arrives, iteration drafts collapse while the critiques below them stay visible, so the full answer text appears once. The critic instruction is stricter: claims not supported by the context count as issues, 9–10 points only without issues. The feedback is passed to the generator on revision and included in the `F6` export.
- **Why:** when approved on the first iteration the critique was just a number, and the answer appeared twice on screen.
- **Impact:** a custom critic instruction (`reflection.prompts.critic`) must also ask for `feedback`; without it the verdict is invalid.
