# Broken Arrow × TechQuest — техническая реализуемость (13.11.2026)

## Исследованные факты

1. В `main` TechQuest закреплены `0.3.3-alpha`, Minecraft `1.21.1`, NeoForge `21.1.264`, Java 21. `modlist.json` содержит официальный `incoming-3.10.4.jar` как обязательный для клиента и сервера; обновлять его ради моста без проверки нельзя.
2. Incoming 3.10.4 поддерживает операционные команды в т.ч. `/incoming bunker at x y z`, `/incoming missile at x y z` и `/incoming salvo missile 1 0 at x y z`. Операторы и консоль могут выдавать команды без расходования боеприпасов. Существуют внутренние `StrikeService.launch(...)` и `Result(ok, eta)`, но это НЕ обещание публичной стабильной Java API.
3. Официальное руководство Broken Arrow подтверждает редактор сценариев, вызываемый из игры, и внутреигровую кнопку Help.
4. Официальный changelog Broken Arrow 16.12.2025 подтверждает LuaNode и GameAPI; 2026 патчи добавляют методы LuaUnit для fire mission и precision strike. Они работают **внутри Broken Arrow**, что не равно внешней интеграции.
5. В доступных опубликованных материалах НЕ удалось подтвердить документированную возможность редактора выполнять исходящие HTTP-запросы, создавать TCP/UDP-сокеты, читать/писать произвольные файлы или принимать входящие события от внешней программы.

## Итог по уровням возможностей

| Возможность | Статус | Комментарий |
|---|---|---|
| Авиудар в TechQuest через Incoming | **Подтверждён интерфейс команды** | Требует испытаний в отдельном мире |
| Запрос и результат через собственный Bridge Server | **Реализуемо средствами Java/HTTP** | Собственная система, не возможность BA |
| Внутренняя сценарная логика BA через LuaNode | **Подтверждено** | Внешний I/O не подтверждён |
| Автоматически нажать «удар» в BA и доставить команду в MC | **Не подтверждено** | Без официальной интеграционной поверхности недоступно |
| Возврат результата непосредственно в HUD BA | **Не подтверждено** | Резерв: companion UI |

## Пороговое исследование редактора (перед любой реализацией BA Adapter)

На **установленной пользователем** лицензированной версии открыть Broken Arrow → Scenarios → Create Scenario → Edit Scenario → Help. Сверить LuaNode и API/GameAPI, список доступных библиотек и версию игры. Не полагаться на старые видеоролики или неофициальные предположения о полном Lua.

Проверить в официальных материалах/спросить разработчика:
- Существует ли разрешённый API для HTTP/WebSocket/локального IPC в runtime сценария? Влияет ли EAC, single-player, private Scenario lobby?
- Разрешены ли `io`/`os` и доступ к пользовательским файлам в LuaNode? **Не пытаться вскрывать песочницу**, если функции отсутствуют.
- Какие события сценария соответствуют нажатию кнопки поддержки, отдаче приказа и получению идентификатора цели?
- Может ли сценарий получить обратно внешний статус и изменить UI через документированные узлы?
- Каковы ограничения multiplayer/Workshop и гарантия совместимости при обновлениях игры?

**Решение:** только при прямом подтверждении штатного разрешённого внешнего канала строить BA-native Adapter (A). Иначе использовать companion Adapter (B): отдельно от исполняемого процесса BA, без памяти, DLL и перехвата ввода.

## Источники

- TechQuest `main`: https://github.com/Nessoro/TechQuest-Modpack/blob/main/modlist.json
- Incoming 3.10.4 (команды): https://github.com/zentixua/incoming/blob/v3.10.4/docs/guide/ru/commands.md
- Incoming 3.10.4 (командный код): https://github.com/zentixua/incoming/blob/v3.10.4/mod/src/main/java/ua/zentix/incoming/command/IncomingCommand.java
- Incoming 3.10.4 (реализация): https://github.com/zentixua/incoming/blob/v3.10.4/mod/src/main/java/ua/zentix/incoming/strike/StrikeService.java
- Руководство Broken Arrow (раздел Scenario Editor): https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/1604270/manuals/7e54aa513d64fc8d3a68831a1fc960efda9d23dc/BrokenArrowManualEBOOK.pdf
- Официальное обновление BA 16.12.2025: https://www6.slitherine.com/news/broken-arrow-allied-command-update-out-now
- Изменения редактора/Луа в BA (разработчик): https://steamcommunity.com/app/1604270/allnews/
- Документация NeoForge команд: https://docs.neoforged.net/docs/misc/commands/

Ни сборка NeoForge bridge JAR, ни реальный тест Broken Arrow в этой исследовательской версии пока не выполнялись.
