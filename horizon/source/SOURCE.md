# Источники TechQuest для Horizon

Текущий снимок планирования — [techquest-post-pr48-candidate.json](techquest-post-pr48-candidate.json),
точные байты `modlist.json` из merge-коммита PR #48
`f5d779750c56762dcfa6ea0c4c76e088a8782759` в `Nessoro/TechQuest-Modpack`.
PR слит в `feat/micro5-refined-storage-jei-033`, а не в main. Версия источника:
TechQuest 0.3.3-alpha, Minecraft 1.21.1 / NeoForge 21.1.264.
SHA-256 снимка: `3fed6bbcc4662631619035ba6378cc0c345441cbdb341779965246aa23e39005`.

В нём 77 объявленных прямых Modrinth-модов, из которых 76 имеют разрешённый
пин; необязательный `iron-chests` не закреплён и не имеет подходящей версии
для целевого loader/game. Вместе с зависимостями сохранён **101 точный пин**
проект/версия/файл/SHA-512. Все 54 обязательные связи проверены по свежим
публичным metadata Modrinth. Скрипт `tools/validate_source_lock.py` не выбирает
latest, не скачивает и не запускает JAR. Это проверка metadata, а не полного
профиля или игрового переноса. [Результат](POST_PR48_VALIDATION.json).

Текущие API-метки стороны у семи проектов отличаются от сохранённых в сборке;
исходная environment policy сохранена, расхождения перечислены в отчёте.
Они не подменяют проверку запуска клиента/сервера. Два manual, три external
и один optional-local источник требуют отдельной проверки; они не входят
в утверждение о 101 проверенном Modrinth-пине.

По сравнению с прежним lock добавлены 13 проектов и удалён Project MMO;
88 общих пинов совпадают полностью. MCHeli, TaCZ и ParCool не возвращены;
validator отклоняет их также при обращении через canonical project ID.
Новый состав включает Oritech, Fluidic Tanks, Refined Storage, Pretty Pipes,
Sophisticated Storage и другие компоненты. Нативная работа этих новых
механик пока не подтверждена.

## Источник уже выполненных worldgen-тестов

[techquest-0.3.3-candidate.json](techquest-0.3.3-candidate.json) сохранён без
изменения: main `918b4bf9ecd133a18eb8a7f57ad2d5da47b2fcb2`, 89 Modrinth-пинов.
Успешный исходный mrpack — Build TechQuest alpha **42597702544**, артефакт
`TechQuest-1.21.1-alpha-build`. Исторические combined/SDK workflows продолжают
воспроизводить этот вход; они не объявляются тестами полного состава #48.

Все пять Terralith/YUNG исходных пинов сохранились; существующие локальные JAR
повторно сверены SHA-512 с новым снимком. Ранее проверенные native worldgen,
спавнеры и chest limits не переносились повторно и не потеряли своё происхождение.
Более ранние отчёты о 86 компонентах относятся к ещё более старому источнику.

Основной NeoForge main не меняется. Сторонние JAR/ресурсы, миры и полные API-кеши
остаются вне репозитория. Новый source inventory не выдаётся за покрытие Horizon.
