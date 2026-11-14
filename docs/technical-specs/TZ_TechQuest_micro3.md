# Техническое задание №1 — TechQuest 0.3.3-micro3

## Удаление RPG Core с сохранением TechQuest Compatibility

**Редакция:** 14.11.2026  
**Репозиторий:** https://github.com/Nessoro/TechQuest-Modpack  
**PR:** https://github.com/Nessoro/TechQuest-Modpack/pull/30 (draft)  
**Ветка реализации:** fix/micro3-remove-first-party-mods-033  
**База:** feat/micro2-rpg-core-033  
**Платформа:** Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21.

### Цель
Полностью исключить собственный TechQuest RPG Core 0.1.0 из будущих клиентских, серверных, Modrinth и Windows-пакетов, не потеряв исправления TechQuest Compatibility 1.0.0. PMMO также не должен возвращаться.

### Обязательные требования
1. Убрать techquest-rpg-core-0.1.0.jar из **генерации**, output/client/mods, output/server/mods, .mrpack, серверного bootstrap и графического Windows EXE.
2. Сохранить techquest-compat-1.0.0.jar на всех соответствующих сторонах и два назначения: рецепты **Create ↔ Industrial Craft 2: Nostalgia** и клиентский Mixin исправления ранней загрузки **Better Zoom**.
3. Исключить повторное появление PMMO JAR и RPG Core при обновлении существующего профиля.
4. Не менять состав и настройки остальных модов, в том числе BuildCraft, Create, IC2, Mekanism, AE2, FTB Ultimine, Physics Mod, Incoming, Patchouli.
5. Оставить один оптимизированный профиль для Minecraft Launcher. Игроку не нужны Python, консоль или Prism Launcher.
6. Не удалять saves, config, options.txt, карты, сведения Launcher. При обновлении mods обеспечить предсказуемый резервный каталог и откат; не создавать множество лишних копий.
7. Не модифицировать публичный micro2, не объединять PR и не публиковать релиз без отдельного решения владельца.

### Что проверить по компонентам
| Компонент | Требование |
|---|---|
| build_pack.py | RPG Core не генерируется, Compatibility JAR генерируется и попадает во все нужные пакеты |
| scripts/install_client.py | Разрешено извлечение Compatibility, запрещена штатная поставка RPG Core |
| scripts/install_server.py | Compatibility поставляется, RPG Core не поставляется; патч Superb Warfare не повреждён |
| windows-installer/Program.cs | GUI ставит актуальный Compatibility, не возвращает RPG Core и безопасно обновляет mods |
| .github/workflows/build-alpha.yml | Проверка отсутствия RPG Core/PMMO и наличия Compatibility на клиенте, сервере и в .mrpack |
| tests/ | Позитивные и негативные регрессионные тесты, повторная установка, откат |
| README.md, docs/MICROPATCH_MICRO3_RU.md | Актуальные инструкции и риски |

### План тестирования
- Unit tests: python -m unittest discover -s tests -v.
- Полная сборка: python build_pack.py; проверка хешей и непротиворечивости modrinth.index.json.
- GUI: собрать TechQuestInstaller.exe, выполнить self-test, новую установку и обновление тестового профиля с историческим RPG Core. Проверить, что предыдущий mods сохранён в единой резервной директории, а сбой вызывает откат.
- Игра: настоящий клиент до главного меню, новый тестовый мир, рецепт Create ↔ IC2, функция Better Zoom; dedicated server до Done и вход игрока — только при отдельном явном принятии Minecraft EULA.
- Отдельно проверить известный дефект добычи блоков вверх: тест одного блока без активного Ultimine, затем тест колонны блоков и Physics Mod. **Удаление RPG Core само по себе не считается исправлением дефекта.**

### Критерии приёмки
- [ ] Ни один будущий пакет не содержит RPG Core или PMMO.
- [ ] Compatibility есть в клиенте и сервере, в .mrpack и Windows EXE; оба его назначения подтверждены в настоящей игре.
- [ ] Клиент, сервер, GUI и повторная установка работают.
- [ ] Миры и пользовательские настройки сохранены, откат проверен.
- [ ] Unit tests, полная сборка, self-test и аудит на одном commit SHA зелёные; к PR приложен отчёт игрового испытания.

### Не входит
Переработка FTB Ultimine/Physics Mod, замена IC2, новые промышленные моды, публичный релиз. Отдельный дефект добычи вверх при необходимости оформляется отдельно.

### Конечный результат
Коммиты в существующей ветке, обновлённый PR #30, перечень изменённых файлов, матрица состава на всех сторонах и проверяемые логи. Не объявлять стабильным без реальных испытаний.
