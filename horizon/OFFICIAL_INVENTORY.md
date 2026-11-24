# Фактический импорт TechQuest в Horizon (метаданные .mrpack)

Этот этап использует **официальный horizon-port-pack** из исходного репозитория Horizon, а не нашу предварительную классификацию по названиям. Сам инструмент и версия фиксируются на коммите `c78187dffffb60f31517eadcb87413386e8ce729`.

GitHub Actions [Horizon real modpack inventory](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/horizon-real-inventory.yml) скачивает **уже проверенный** GitHub Actions артефакт `TechQuest-1.21.1-alpha-build` из запуска [#42372848633](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42372848633) и ищет `.mrpack`.

Затем выполняются:

```bash
horizon-port-pack import source.mrpack /tmp/techquest-horizon
horizon-port-pack inventory /tmp/techquest-horizon
horizon-port-pack report /tmp/techquest-horizon
```

Результат: `coverage.md`, `coverage.json`, `inventory.json`, `inventory.csv`. В архив GitHub загружаются **только метаданные и отчёты**, не моды/JAR и не чужие текстуры, модели или исходники.

Это ещё **не перенос** механик NeoForge. Мы намеренно не запускаем `fetch`, `carry` и `port` в публичном CI, поскольку они работают с файлами и ресурсами третьих лиц. Результаты этого этапа позволят обоснованно выбрать первый кандидат для переносимых данных (например, мировых структур), отдельно проверить лицензию и уже затем внедрять настоящие `.hmod`.

### Ограничения

- Артефакт `.mrpack` из GitHub Actions хранится ограниченное время. Для будущих запусков нужно заменить `run-id` на новую успешную сборку TechQuest.
- Импорт созданного под NeoForge 1.21.1 пакета — анализ совместимости, а не гарантия игры на Horizon 26.3.
- Статус `ported` означает больше, чем запись в метаданных: нужна проверка данных и функциональности в Horizon. Результаты реального импорта не следует путать с offline-планом `horizon/tools/port_inventory.py`.
