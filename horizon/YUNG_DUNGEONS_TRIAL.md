# Первый пробный перенос стороннего мода: YUNG's Better Dungeons

**Статус:** отдельный автоматизированный тест переноса данных, не готовый игровой мод.

Почему именно он:
- Официальный `horizon-port-pack` уже классифицировал его как **data-tier**, один из шести возможных кандидатов.
- На Modrinth автор указал LGPL-3.0; перед возможной публикацией переведённого `.hmod` потребуются корректные уведомления об авторстве, лицензии и проверка всей цепочки зависимостей.
- В отличие от Wyrmroost, Create и Mekanism основная часть структур может переноситься на уровне данных, хотя специфичная генерация и Java-логика по-прежнему не гарантированы.

Pipeline в workflow `.github/workflows/horizon-yung-dungeons.yml`:

```bash
horizon-port-pack import <TechQuest.mrpack> <work>
horizon-port-pack inventory <work>
horizon-port-pack fetch <work> yungs-better-dungeons
horizon-port-pack carry <work> yungs-better-dungeons
horizon-port-pack report <work>
```

Запуск скачивает оригинальный JAR по проверяемой ссылке только **в эфемерном GitHub runner**, использует официальный конвертер Horizon и НЕ публикует JAR, перенесённые структуры или ассеты. Загружаются исключительно `coverage.json`, `coverage.md` и `fetch.json`.

Проверки после успешного конвертера: прочитать отчёт, убедиться, что структуры и лут не потеряны, подтвердить зависимость от YUNG's API, найти совместимый Horizon формат 26.3, проверить генерацию в новом игровом мире. До этих проверок нельзя выдавать результат за игровой порт.

См. [фактический отчёт покрытия всей сборки](OFFICIAL_INVENTORY.md), [GitHub Actions workflow](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/horizon-yung-dungeons.yml).

Никакие изменения не вносятся в основной TechQuest NeoForge или в экспериментальную 0.3.3.
