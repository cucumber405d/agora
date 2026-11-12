# 2026-11-12 — Release pipeline

## RU
- **Что изменилось:** workflow `.github/workflows/release.yml` запускается по тегу `v*` на `windows-latest`: проверяет, что тег совпадает с `__version__`, гоняет ruff, mypy и pytest, собирает exe, выполняет smoke-проверку, собирает установщик Inno Setup и portable-zip и публикует GitHub Release. Текст релиза — `CHANGELOG.md`, который `scripts/changelog.py` собирает из EN-разделов импактов с даты предыдущего тега.
- **Зачем:** релиз одной командой `git tag v0.2.0 && git push origin v0.2.0`, без ручной сборки.
- **Влияние:** импакты теперь ещё и источник release notes — EN-раздел должен быть понятен пользователю.

## EN
- **What changed:** the `.github/workflows/release.yml` workflow runs on a `v*` tag on `windows-latest`: it checks that the tag matches `__version__`, runs ruff, mypy and pytest, builds the exe, smoke-tests it, builds the Inno Setup installer and a portable zip, and publishes a GitHub Release. The release text is `CHANGELOG.md`, built by `scripts/changelog.py` from the EN sections of the impacts since the previous tag's date.
- **Why:** a release is one `git tag v0.2.0 && git push origin v0.2.0`, without building by hand.
- **Impact:** impacts are now also the source of the release notes, so their EN section must make sense to users.
