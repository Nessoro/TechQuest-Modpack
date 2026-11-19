# TechQuest 0.3.3 — исправление повторной выдачи руководства MI после смерти

Modern Industrialization v2.5.12 (NeoForge 1.21.1) по умолчанию выдаёт книгу дважды: при первом входе и снова при каждом возрождении. В TechQuest отключена только повторная выдача.

## Точные параметры

```toml
spawnWithGuideBook = true
respawnWithGuideBook = false
```

- `spawnWithGuideBook = true` — первоначальное знакомство с модом остаётся.
- `respawnWithGuideBook = false` — после смерти новая копия руководства больше не выдаётся.
- Саму книгу можно открыть штатным способом, рецепты/машины MI и внутриигровой путеводитель TechQuest не меняются.

## Автоматическая установка

- Для новых миров пресет помещается в `defaultconfigs/modern_industrialization-server.toml` и включён в `.mrpack` и клиентский/серверный набор.
- При обновлении существующего профиля GUI-установщик, а также Python-инсталляторы клиента и сервера, меняют только одну строку `respawnWithGuideBook` в уже существующем конфиге MI. Остальные параметры и данные мира сохраняются.
- Исходный TOML-файл при первом изменении копируется в `modern_industrialization-server.toml.techquest-original.bak`; повторное обновление не перезаписывает резервную копию.
- В однопользовательском Minecraft проверяется `saves/<имя_мира>/serverconfig/modern_industrialization-server.toml` и прежний путь `config/modern_industrialization-server.toml`. На выделенном сервере — `<level-name>/serverconfig/modern_industrialization-server.toml` (по `server.properties`) и `config/`.
- Закрой Minecraft перед обновлением. Создай резервную копию мира.

## Ручное исправление без переустановки

1. Закрой Minecraft или останови сервер.
2. Открой существующий файл MI server config для соответствующего мира (указан выше).
3. Найди `respawnWithGuideBook = true` и поменяй на `respawnWithGuideBook = false`. Параметр `spawnWithGuideBook` не меняй.
4. Сохрани файл и перезапусти мир/сервер. Если настройка не найдена, добавь `respawnWithGuideBook = false` до первого TOML-раздела `[... ]`.

## Проверки

Статические тесты подтверждают: первое получение книги сохраняется, повторная выдача отключена, изменения существующих конфигов минимальны и имеют одноразовый backup, другие миры, `level.dat`, настройки рецептов и EULA не изменяются. Windows EXE проверяется командой `--self-test` в CI. Реальный тест смерти/возрождения всё ещё требуется сделать внутри тестового мира.

Изменение в draft PR #50 поверх ветки с DimStorage (#49), без слияния в `main`.
