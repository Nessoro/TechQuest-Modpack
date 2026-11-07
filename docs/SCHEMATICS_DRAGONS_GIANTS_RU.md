# TechQuest 0.3.3 — схемы, драконы и большие монстры

**Статус: тестовая интеграция в PR #5.** Minecraft 1.21.1 / NeoForge 21.1.264 / Java 21. Для нового релиза используйте отдельную папку и резервную копию мира.

## Схемы — аналог Litematica
- [Forgematica 0.4.3](https://modrinth.com/mod/forgematica) и [MaFgLib 0.4.3](https://modrinth.com/mod/mafglib) — только **клиентские**. Они позволяют использовать голограммы, схемы `.litematic`, проверять блоки и список материалов.
- Нельзя устанавливать эти два JAR на выделенный NeoForge-сервер; они должны присутствовать только в клиенте.
- Сравните результаты с Create Schematicannon; тестируйте сочетание с Sodium, Xaero и ParCool. При просадках FPS отключайте голограммы.

## Новые драконы и массивные существа
- [Wyrmroost 1.4.1](https://modrinth.com/mod/wyrmroost/version/1.4.1) — разнообразные драконы, приручение, полёт и исследования. Клиент и сервер. **IceAndFire CE удалён**, это альтернатива.
- [Legendary Monsters 2.2.3](https://modrinth.com/mod/legendary-monsters/version/Dfoikvr0) — большие боссы, включая Skeletosaurus, Lava Eater, Cloud Golem и других.
- [Twisted Mobs](https://modrinth.com/mod/twisted-mobs) — гигантские/титанические зомби и Goliath.
- [Ben's Titans](https://modrinth.com/mod/bens-titans-unoffical-neoforge-port-) **не включён**: неофициальный молодой порт 1.21.1, оригинальный мод зависит от Alex's Caves для Forge 1.20.1. Нужны отдельные проверки API, лицензий, производительности и фактической совместимости.

## Тесты перед слиянием
- [ ] CI Validate, Audit mod availability, Build TechQuest alpha (EXE и ClamAV).
- [ ] Подтвердить клиентский манифест Forgematica + MaFgLib и их отсутствие в серверном.
- [ ] Клиент и сервер запускаются с Wyrmroost, Legendary Monsters и Twisted Mobs.
- [ ] В новом обычном мире проверить полёт, приручение, спавн Giant/Titan и боссов.
- [ ] Проверить `.litematic` и FPS при крупных голограммах на слабом ПК.
- [ ] Замерить TPS через Spark с 1, 3, 5 большими мобами, не рядом с основной базой.
- [ ] Проверить Tailscale 2+ игрока и сохранение мира при перезаходе.
- [ ] Перед обновлением сохранённого мира сделать бэкап; не устанавливать новые моды поверх 0.3.2.

Успешный CI не заменяет игровую проверку. Wyrmroost и Twisted Mobs распространяются с сохранением прав авторов, чужие JAR не коммитятся в GitHub.
