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
4. Сайт появится по адресу `https://nessoro.github.io/TechQuest-Modpack/` (точный адрес GitHub покажет в Settings → Pages).
5. Убедитесь, что вкладка **Issues** включена в Settings → General → Features.

Сайт не хранит сообщения у себя: кнопка «Создать отчёт / Отправить предложение» открывает **заполненный черновик GitHub Issue**, затем пользователь входит в GitHub и подтверждает публикацию. На сайте также автоматически отображаются недавние открытые Issues.

**Если владелец или имя репозитория будут другими:** измените `REPO` в `docs/assets/app.js` и URL в `.github/ISSUE_TEMPLATE/config.yml`.

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