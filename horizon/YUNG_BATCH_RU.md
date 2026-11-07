# Массовый пробный перенос четырёх модов YUNG's в Horizon

Цель: проверить, что официальный `horizon-port-pack` способен извлечь и адаптировать **данные структур и таблицы лута** из всех четырёх модов YUNG's, используемых TechQuest 0.3.3:

- YUNG's Better Dungeons — внутренний ID `betterdungeons`.
- YUNG's Better Strongholds — внутренний ID `betterstrongholds`.
- YUNG's Better Mineshafts — внутренний ID `bettermineshafts`.
- YUNG's Better Nether Fortresses — внутренний ID `betterfortresses`.

Исходный выпуск: модпак TechQuest 0.3.3, Minecraft 1.21.1 / NeoForge 21.1.264 из [успешного Build #42372848633](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42372848633).

Пайплайн [horizon-yung-batch.yml](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/horizon-yung-batch.yml): `import`, `inventory`, `fetch` четырёх оригинальных JAR с SHA-проверкой, **повторный inventory** для обнаружения внутренних ID, `carry`, `report`. Для каждого мода обязательно должна возникнуть директория `carry` с содержимым; если нет — GitHub Actions считается ошибочным.

Все исходные JAR, модели, текстуры, структура и конвертированные данные находятся только во временном runner. В GitHub Actions публикуется **только отчёт** (metadata JSON/Markdown), никаких сторонних файлов не прикрепляется. Авторство и LGPL-3.0 всех четырёх источников должны быть сохранены и проверены отдельно перед возможным распространением производных модов.

Базовый одиночный перенос Better Dungeons уже прошёл [CI #42382057398](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42382057398): сконвертировано **314 исходных файлов, 282 файла генерации мира, 8 таблиц лута**, созданы **315 файлов** локального пакета. Официальный статус пока **partial**, потому что игровая генерация не проверена.

Этот групповой тест не утверждает, что YUNG Java-логика или генерация с новыми процессорами уже работают в Horizon 26.3. Для подтверждения нужны официальный SDK `check`, сравнение оригинального и перенесённого мира, тест новых чанков, лута, сервера и Tailscale. Нельзя устанавливать результат поверх действующего мира TechQuest 1.21.1.


## Результат первого группового переноса данных — 7 ноября 2026

GitHub Actions [#42382390837](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42382390837) **завершился успешно**. Официальный `horizon-port-pack` скачал оригинальные JAR из источников Modrinth (с проверкой хешей), обработал 4 мода YUNG's и создал отдельные локальные каталоги данных Horizon:

| Мод | Файлов в промежуточном пакете | Worldgen-файлов | Статус |
| --- | ---: | ---: | --- |
| Better Dungeons | 313 | 282 | **partial** |
| Better Strongholds | 137 | 120 | **partial** |
| Better Mineshafts | 33 | 14 | **partial** |
| Better Nether Fortresses | 203 | 187 | **partial** |
| **Итого** | **686** | **603** | 4 частичных переноса |

Обновлённое покрытие: **4 partial / 45 not yet / 37 not needed / 0 ported** из 86 компонентов. Дополнительно обработано 27 таблиц лута. Перенесённые данные и чужие JAR **не опубликованы**, в артефакте доступен лишь отчёт [Coverage-ONLY](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42382390837/artifacts/13578440342).

Это **не подтверждённый игровой порт**: не проверялись загрузка в реальном Horizon 26.3, генерация/совместимость структур, YUNG API, поведение процессоров, сервер и Tailscale. Для перехода от `partial` к `ported` нужны отдельные тесты, подтверждение прав на распространение и игровые сравнения.
