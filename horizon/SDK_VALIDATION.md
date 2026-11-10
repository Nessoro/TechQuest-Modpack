# Официальная проверка Horizon SDK

Этот workflow проверяет первый собственный блок TechQuest с помощью настоящего [cargo-horizon-mod](https://github.com/horizon-rust/horizon), а не только ZIP-упаковки на Python.

Используем закреплённую ревизию Horizon: HORIZON_REV = c78187dffffb60f31517eadcb87413386e8ce729.

1. GitHub Actions компилирует официальный Rust SDK из проверяемого исходного коммита.
2. В каталоге first_party/expedition_marker выполняется официальный build.
3. Выполняется официальный check --json и публикуется артефакт с результатом.
4. При ошибке workflow не объявляет мод проверенным; нужно исправить код под реальный API.

Workflow: https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/horizon-sdk-check.yml

Это подтверждает только совместимость структуры контент-мода с SDK и проверками реестра. Это не тест реальной игры Horizon 26.3, не запуск многопользовательского сервера и не доказательство переноса сторонних Java-механик. Для этого нужны отдельные runtime-проверки и лицензии на сторонние ресурсы.
