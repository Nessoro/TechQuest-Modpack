# Expedition Marker — первый контент-мод TechQuest под Horizon

Первый **собственный демонстрационный блок** для Horizon 26.3: `techquest_expedition_marker:expedition_marker`, создаётся из ванильных аметиста и светопыли, имеет модель, освещение, рецептуру и добычу. Использует текстуру по ссылке `minecraft:block/amethyst_block`, не включает сторонние ресурсы и не запускает Java-код.

Это **не порт механик Create, IC2, Wyrmroost и других**. Текущий контент-мод показывает корректное направление разработки для Horizon API 0.2 и подлежит проверке в настоящем движке.

```bash
cargo install --git https://github.com/horizon-rust/horizon cargo-horizon-mod
cd horizon/first_party/expedition_marker
cargo horizon-mod build
cargo horizon-mod check target/horizon-mod/techquest_expedition_marker.hmod
```

Команда из корня репозитория `python horizon/tools/build_demo_hmod.py` дополнительно упаковывает проект в ZIP-контейнер `.hmod` для структурного теста, **не заменяя официальный cargo check**. Для настоящего запуска нужен установленный Horizon и лицензия Minecraft Java Edition.
