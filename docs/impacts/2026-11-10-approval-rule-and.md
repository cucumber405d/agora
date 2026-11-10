# 2026-11-10 — Approval requires critic approval AND the score threshold

## RU
- **Что изменилось:** черновик принимается, только если критик одобрил его **и** `score >= approve_threshold`. Раньше достаточно было одного из условий.
- **Зачем:** `approve_threshold: 10` не останавливал цикл: критик ставил `approved: true` со score 9, и прогон заканчивался после первой итерации. Порог должен быть жёсткой планкой.
- **Влияние:** прогоны в среднем длиннее; при пороге 9–10 и маленькой модели почти всегда идут до `max_iterations`, итог — черновик с лучшим score. Высокий score без `approved` теперь тоже даёт новую итерацию.

## EN
- **What changed:** a draft is accepted only if the critic approves it **and** `score >= approve_threshold`. Previously either condition was enough.
- **Why:** `approve_threshold: 10` did not stop the loop: the critic returned `approved: true` with score 9 and the run ended after one iteration. The threshold must be a hard floor.
- **Impact:** runs are longer on average; with a threshold of 9–10 and a small model they usually go to `max_iterations`, and the result is the best-scored draft. A high score without `approved` now also triggers another iteration.
