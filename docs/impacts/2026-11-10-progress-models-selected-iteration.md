# 2026-11-10 — Models in Progress, selected iteration in the result

## RU
- **Что изменилось:** в начале панели Progress показаны модели генератора и критика (`Gen …`, `Crit …`). Итог называет выбранную итерацию и её оценку: в Progress — `Final It2 7/10 max_iterations`, в ленте — `Final (max_iterations, Iter 2, score 7)`, в экспорте `F6` — «iteration 2, score 7»; при `critic_failed` вместо оценки — `not graded`. В результат прогона (`RunResult`) добавлены поля `selected_iteration` и `selected_score`.
- **Зачем:** при исчерпании итераций итогом становится лучший, а не последний черновик, и раньше было не видно, какой именно.
- **Влияние:** `best_score` сохранён для совместимости; `selected_score` — оценка именно выбранного черновика.

## EN
- **What changed:** the Progress panel starts with the generator and critic models (`Gen …`, `Crit …`). The result names the selected iteration and its score: Progress shows `Final It2 7/10 max_iterations`, the feed `Final (max_iterations, Iter 2, score 7)`, the `F6` export "iteration 2, score 7"; with `critic_failed` the score reads `not graded`. `RunResult` gained `selected_iteration` and `selected_score`.
- **Why:** when the iterations run out the result is the best, not the last, draft, and it was not visible which one was chosen.
- **Impact:** `best_score` is kept for compatibility; `selected_score` is the score of the selected draft itself.
