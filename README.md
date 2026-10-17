# TechQuest: Industrial Frontier

> **Minecraft Java 1.21.1 • NeoForge 21.1.x • Java 21 • сервер с друзьями**

TechQuest — большая комплексная сборка вокруг **BuildCraft Community Edition** и **Industrial Craft 2: Nostalgia**. Дополнительно в план включены Create, Mekanism, Modern Industrialization, AE2, магия, развитие, новые мобы и миры.

**Статус: `0.1.0-alpha` / исходники и сайт опубликованы в GitHub. Готовая игровая сборка НЕ проверена запуском клиента/сервера.** Не переносите старый мир без резервной копии. Перечисленные моды — кандидаты, а не подтверждённый полностью совместимый набор.

## Навигация

| Раздел | Для чего |
| --- | --- |
| [`modlist.json`](modlist.json) | Список кандидатов, основных и необязательных модов |
| [`build_pack.py`](build_pack.py) | Резолвер Modrinth-зависимостей и сборщик клиентских/серверных файлов |
| [`MODPACK_README_RU.md`](MODPACK_README_RU.md) | Пошаговая установка на ПК и сервере |
| [`ПУБЛИКАЦИЯ_И_САЙТ.md`](ПУБЛИКАЦИЯ_И_САЙТ.md) | Публикация репозитория и сайта, в том числе с телефона |
| [`docs/`](docs/) | Сайт сообщества для GitHub Pages |
| [Баг-репорты](https://github.com/Nessoro/TechQuest-Modpack/issues/new?template=bug_report.yml) | Форма ошибки с полями окружения и воспроизведения |
| [Предложения модов](https://github.com/Nessoro/TechQuest-Modpack/issues/new?template=mod_request.yml) | Форма нового мода и его совместимости |

## Запуск сайта на GitHub Pages

1. Репозиторий уже создан: `Nessoro/TechQuest-Modpack`.
2. В GitHub откройте **Settings → Pages → Build and deployment → Deploy from a branch**.
3. Выберите ветку `main`, папку `/docs`, нажмите **Save**.
4. Сайт опубликован по адресу `https://nessoro.github.io/TechQuest-Modpack/` (GitHub Pages build завершился успешно 17.10.2026).
5. Убедитесь, что вкладка **Issues** включена в Settings → General → Features.

Сайт не хранит сообщения у себя: кнопка «Создать отчёт / Отправить предложение» открывает **заполненный черновик GitHub Issue**, затем пользователь входит в GitHub и подтверждает публикацию. На сайте также автоматически отображаются недавние открытые Issues.

**Если владелец или имя репозитория будут другими:** измените `REPO` в `docs/index.html` и URL в `.github/ISSUE_TEMPLATE/config.yml`.

## Проверка доступности модов

[Автоматическая проверка Modrinth](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/audit-mods.yml) запускается при изменении списка модов, вручную и по понедельникам.

Она создаёт отчёты `compatibility.md` и `compatibility.json` в артефакте `techquest-compatibility-report`: для каждого кандидата показывает наличие подходящей версии под Minecraft 1.21.1 / NeoForge. Это **не** игровой тест. Моды из CurseForge, включая IC2: Nostalgia, проверяются отдельно.

Для локального отчёта: `python scripts/audit_modlist.py`.

## Скачать сборку (экспериментальная альфа)

В разделе [Build TechQuest alpha](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/build-alpha.yml) откройте самый новый **успешный** запуск. Внизу страницы в **Artifacts** скачайте `TechQuest-1.21.1-alpha-build`.

Архив содержит:
- `TechQuest_1.21.1_0.1.0.mrpack` — импортируйте в поддерживающий Modrinth-модпаки лаунчер.
- `versions-lock.json` — зафиксированные версии и обязательные зависимости.
- `BUILD_STATUS.json` — результат проверки загрузки и контрольных сумм.
- `TechQuest_Server_Bootstrap.zip` — установщик выделенного сервера с загрузкой модов от правообладателей.

Для отдельного сервера распакуйте `TechQuest_Server_Bootstrap.zip`, установите **Java 21 и Python 3.9+**, затем запустите команду из каталога распаковки:

```sh
python scripts/install_server.py --pack TechQuest.mrpack --target server
```

Программа скачает серверные версии модов с проверкой хешей и установит NeoForge. **IC2: Nostalgia не включён в автоматический публичный артефакт, потому что сборщик использует Modrinth API, а этот порт находится на CurseForge.** Его страница указывает лицензию GPLv3; совместимость и соблюдение условий распространения надо проверять отдельно. Установите оригинальный JAR вручную либо используйте локальный сборщик ниже. Установщик не принимает EULA автоматически: ознакомьтесь с ней и подтвердите согласие в `server/eula.txt` самостоятельно. Для запуска Linux используйте `server/run.sh nogui`, Windows — `server/run.bat nogui`. Сохранённая конфигурация сервера намеренно ограничивает доступ белым списком.

**Внимание:** успешное создание пакета и загрузка файлов с проверкой хешей не доказывают совместимость модов или отсутствие крашей при старте. Не используйте для постоянного мира до тестового запуска клиента и сервера.

## IndustrialCraft — обязательный компонент (установка)

**BuildCraft и IndustrialCraft — два главных мода TechQuest.** Отсутствие IC2 в публичном `.mrpack` — ограничение сборочного конвейера, а не решение исключить IC2 из проекта.

Скачайте файл [Industrial Craft 2: Nostalgia для Minecraft 1.21.1 / NeoForge](https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia/files/9217244) непосредственно с CurseForge:
`industrial-craft-2-nostalgia-21.1.0-local.26.jar`.

**Обычная установка:** после импорта `.mrpack` откройте каталог игры в лаунчере, положите этот JAR в `mods/`; на выделенном сервере положите **тот же самый JAR** в `server/mods/`.

**Создать локальный полный клиентский `.mrpack`:** скопируйте исходный `.mrpack` и IC2 JAR в папку проекта, затем запустите:

```sh
python scripts/include_industrialcraft.py --pack TechQuest_1.21.1_0.1.0.mrpack --jar industrial-craft-2-nostalgia-21.1.0-local.26.jar --output TechQuest_WITH_IC2_LOCAL.mrpack
```

Можно также добавить `--server-mods server/mods`, чтобы локальный скрипт положил тот же JAR в папку сервера (если его там ещё нет). Итоговый `TechQuest_WITH_IC2_LOCAL.mrpack` содержит оригинальный IC2 JAR в `overrides/mods` и предназначен для личного использования. **Не коммитьте этот файл или сторонние бинарные JAR в публичный репозиторий.** При дальнейшей раздаче файлов соблюдайте условия оригинального проекта и авторов всех компонентов.

**Текущий статус:** клиент+сервер с IC2 ещё **не проходили тест запуска**. До проверки не переносите постоянный игровой мир.

## Серверный smoke-test (по желанию администратора)

Для проверки фактического запуска NeoForge предусмотрен [ручной workflow Smoke-test NeoForge server](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/smoke-server.yml).
Он требует **явного согласия с Minecraft EULA** через переключатель `accept_minecraft_eula`. Workflow скачает моды, установит временный NeoForge 1.21.1, запустит сервер и приложит логи к результату.
**Ограничение:** сторонний порт IC2: Nostalgia не включается в автоматический тест (нельзя перепубликовывать без проверки лицензии). Даже успешный smoke-test не заменяет испытание полного набора модов с IC2 и игру нескольких участников.

## Собрать файлы модпака

```sh
python build_pack.py --resolve-only   # Получить версии и выявить несовместимые/недоступные моды
python build_pack.py                  # Создать output/client, output/server и .mrpack
python scripts/sync_site_mods.py       # Обновить каталог сайта после правки modlist.json
python -m unittest discover -s tests -v
```

Нужны интернет, Python 3.9+ и отдельно установленная Java 21 для Minecraft. IndustrialCraft 2: Nostalgia скачивается пользователем с [CurseForge](https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia/files/9217244) в `manual-mods/`, из-за ограничения на перераспространение модов. **Не загружайте чужие JAR, файлы сервера или миры в git:** в `.gitignore` есть соответствующие исключения.

### Важные ссылки

- [BuildCraft Community Edition](https://modrinth.com/mod/buildcraft-community-edition) — официальный релиз `8.0.23+1.21.1+neoforge`.
- [IC2: Nostalgia](https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia) — неофициальный порт, релиз 16.10.2026, требует дополнительных проверок.
- [GitHub Pages: publication source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

Этот проект не связан с Mojang/Microsoft. Все моды принадлежат их авторам; лицензии каждого проекта соблюдаются отдельно. Код сайта и собственные скрипты можно использовать по условиям `LICENSE`.