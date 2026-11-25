# TechQuest 0.3.3.3 — проверки совместимости военного оружия с боссами

**Статус:** draft-кандидат. Ни работа игрового мира, ни нанесение урона ещё не подтверждены для 0.3.3.3. Он наследует настройки `range_cap = 256.0` и клиент 16 / сервер 14 чанков из тестовой 0.3.3.2.

## Что установлено тестами 0.3.3.2

- На расстоянии около 20 блоков вертолётное орудие Superb Warfare визуально попадало по Голему Энда, но HP оставалось 150/150.
- Отдельные бомбы Incoming разрушали поверхность, но HP Голема Энда не менялось. В другой серии атак голем погиб; определить тип смертельного снаряда достоверно нельзя.
- Ракета Iskander убивала Голема Энда, но не убила Уничтожителя из Legendary Monsters. Уничтожитель имеет собственные игровые ограничения; не обходить их автоматически.
- Голем исчезал из отображения при отлёте. Исходник Cataclysm содержит `removeWhenFarAway=false`, так что это не доказывает деспавн.

## Реальное изменение в 0.3.3.3

В собственный `techquest-compat-1.0.0.jar` включён аддитивный `cataclysm:bypasses_hurt_time`. Он добавляет отсутствовавшие в Superb Warfare `superbwarfare:gunfire`, `superbwarfare:gunfire_headshot` и проверенные по исходникам Incoming 3.10.4 типы `incoming:strike`, `incoming:shockwave`, `incoming:kinetic`, `incoming:debris`, `incoming:fragment`, `incoming:nuclear_blast`, `incoming:player_nuclear_blast`. Остальной список тегов сохраняется благодаря `replace:false`.

Это только обход **внутреннего накопителя damageBucket Cataclysm**. Он **не** меняет боссов Aether / Legendary Monsters / Mowzie, фазовый иммунитет, требуемые инструменты, предельную дистанцию из 0.3.3.2, `damage_cap`, ванильные i-frames или отсутствие серверного события попадания. Для перечисленных типов изменится ограничение суммарного DPS Cataclysm — оценить баланс в игре. Исправление не гарантировано.

Оригинальные проверенные источники: [SBW 0.8.9.2 ModDamageTypeTagProvider](https://github.com/Mercurows/SuperbWarfare/blob/0.8.9.2-1.21/src/main/kotlin/com/atsuishio/superbwarfare/datagen/ModDamageTypeTagProvider.kt), [Incoming v3.10.4 ModDamageTypes](https://github.com/zentixua/incoming/blob/v3.10.4/mod/src/main/java/ua/zentix/incoming/registry/ModDamageTypes.java), [Cataclysm LLibrary_Boss_Monster](https://github.com/lender544/new1.20.1/blob/1.21/src/main/java/com/github/L_Ender/cataclysm/entity/AnimationMonster/BossMonsters/LLibrary_Boss_Monster.java).

## Короткий план игрового теста

1. Установить именно 0.3.3.3 **в новую папку**, открыть одиночный плоский мир на сложности Normal с командами. Проверить в `config/cataclysm-common.toml` значение `[mobs.ender_golem.cap_config] range_cap = 256.0`.
2. Призвать Голема Энда: `/summon cataclysm:ender_golem ~ ~1 ~5`. Для стабильной проверки остановить AI и пробудить его: `/data merge entity @e[type=cataclysm:ender_golem,limit=1,sort=nearest] {NoAI:1b,is_Awaken:1b}`.
3. Измерить HP командой `/data get entity @e[type=cataclysm:ender_golem,limit=1,sort=nearest] Health`. Сразу после одного выстрела снова измерить HP, не ориентироваться только на внешний индикатор.
4. Отдельно испытать одиночный выстрел стрелкового оружия SBW, вертолётное орудие SBW, одно попадание Incoming Grad / Lancet и одну авиабомбу Incoming на 20 блоках; затем повторить на 100 блоках. Для каждого опыта создать нового Голема Энда, не смешивать с другим оружием.
5. Для каждой бомбы сравнить зомби и голема в одном радиусе: если зомби не получил урон, возможно, причина в геометрии взрыва или настройках Incoming.
6. Iskander оставить контролем, проверить игровые фазы Уничтожителя, кирку для Slider из Aether. Не добавлять `minecraft:bypasses_invulnerability`. На выделенном сервере повторить с синхронными версиями модов и сохранёнными логами.

**Положительный результат** — непосредственно зафиксированное уменьшение HP после разрешённого удара, при неизменных игровых фазах. CI и старт меню не являются доказательством.
