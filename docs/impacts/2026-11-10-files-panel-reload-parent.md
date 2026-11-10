# 2026-11-10 — File panel: re-read folders, go to parent

## RU
- **Что изменилось:** папка в панели файлов перечитывается с диска при каждом повторном раскрытии (закрыть → открыть); `Ctrl+R` перечитывает всю панель, как в Far; `Backspace` или `Ctrl+PgUp` поднимают корень панели в родительский каталог. Полный путь текущего корня виден в заголовке панели.
- **Зачем:** новые файлы, добавленные во время работы, не появлялись; нельзя было выбрать файл выше каталога запуска.
- **Влияние:** отметки `[x]` сохраняются при перечитывании и смене каталога; отметки удалённых файлов снимаются, подсчёт контекста обновляется. Каталог для `F6` (`agora-runs/`) остаётся каталогом запуска.

## EN
- **What changed:** a folder in the file panel is re-read from disk every time it is re-opened (collapse → expand); `Ctrl+R` re-reads the whole panel, as in Far; `Backspace` or `Ctrl+PgUp` move the panel root to the parent directory. The full path of the current root is shown in the panel title.
- **Why:** files added while the app was running did not appear; files above the start directory could not be selected.
- **Impact:** `[x]` marks survive re-reads and directory changes; marks of deleted files are dropped and the context count is updated. The `F6` directory (`agora-runs/`) stays the start directory.
