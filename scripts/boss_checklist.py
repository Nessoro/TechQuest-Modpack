#!/usr/bin/env python3
"""TechQuest co-op boss tracker and in-game hunt guide for Minecraft 1.21.1.

Upgrades the previously shipped Legendary Monsters checklist in place: same
advancement IDs, scoreboard objective and saved world keys. No separate JAR.
A normal written book (given on first join, craftable later) has locator guides.
"""
import io
import json
import zipfile

NAMESPACE = "techquest_bosses"
OBJECTIVE = "tqb_kills"

# Original Legendary Monsters IDs are immutable to preserve existing LAN progress.
# IDs checked against Miauczel/Legendary-Monsters-1.21.1-NeoForge ModEntities.java.
BOSSES = (
    ("ancient_guardian", "Древний страж", "overworld", "minecraft:dripstone_block", "boss"),
    ("overgrown_colossus", "Заросший колосс", "overworld", "minecraft:moss_block", "boss"),
    ("cloud_golem", "Облачный голем", "overworld", "minecraft:feather", "boss"),
    ("dune_sentinel", "Страж дюн", "overworld", "minecraft:sandstone", "boss"),
    ("frostbitten_golem", "Ледяной голем", "overworld", "minecraft:blue_ice", "boss"),
    ("posessed_paladin", "Одержимый паладин", "overworld", "minecraft:iron_sword", "boss"),
    ("skeletosaurus", "Скелетозавр", "nether", "minecraft:bone_block", "boss"),
    ("lava_eater", "Пожиратель лавы", "nether", "minecraft:magma_block", "boss"),
    ("warped_fungussus", "Искажённый грибной монстр", "nether", "minecraft:warped_fungus", "boss"),
    ("withered_abomination", "Иссушенное чудовище", "nether", "minecraft:soul_sand", "boss"),
    ("endersent", "Хорус-энт", "end", "minecraft:chorus_flower", "boss"),
    ("shulker_mimic", "Шалкеровый мимик", "end", "minecraft:shulker_shell", "miniboss"),
    ("annihilation_pursuer", "Преследователь аннигиляции", "end", "minecraft:ender_eye", "miniboss"),
    ("the_obliterator", "Уничтожитель", "end", "minecraft:nether_star", "boss"),
)

# Relative in-game exploration tips, with no invented coordinates or guarantees
# about worldgen altered by Terralith/YUNG's and other structure mods.
LEGENDARY_GUIDES = {
    "ancient_guardian": "Тёмный лес или тайга. Найди Ancient Stronghold по Eye Of Many Ribs (Око многих рёбер). Внутри есть охрана из древних существ.",
    "overgrown_colossus": "Джунгли: Mossy Temple. Используй Eye Of Moss (Око мха). Ищи большой каменный храм, покрытый растениями.",
    "cloud_golem": "Горные пики, склоны и луга: Cloudy Temple. Используй Eye Of Air (Око воздуха), затем осматривай высоту.",
    "dune_sentinel": "Пустыня: Ruined Pyramid. Eye Of Sandstorm укажет направление к разрушенной пирамиде.",
    "frostbitten_golem": "Снежные биомы: Frostbitten Temple. Eye Of Frost ведёт к ледяному храму. Проверь рецепт в JEI.",
    "posessed_paladin": "Обычный мир: Abandoned Crypt / Collapsed Kingdom. Используй Eye Of Ghost, затем спустись в подземные залы.",
    "skeletosaurus": "Незер, долина песка душ: Skeletosaurus Nest. Око Eye Of Bones указывает на гнездо с костяными блоками.",
    "lava_eater": "Незер, пустоши: Lava Eater's Nest. Используй Eye Of Magma, осторожно ищи логово возле лавы.",
    "warped_fungussus": "Незер, искажённый лес: Warped Mushroom Nest. Осматривай грибные наросты; отдельного Ока для этого босса нет.",
    "withered_abomination": "Незер: Soul Fortress Remains. Ищи развалины крепости с помощью Eye Of Soul.",
    "endersent": "Внешние острова Энда: Ancient Tower Remains. Используй Eye Of Chorus, ищи развалины башни.",
    "shulker_mimic": "Энд: Shulker Tower. Eye Of Shulker найдёт башню; мини-босс наверху.",
    "annihilation_pursuer": "Энд: Space Station. Eye Of Annihilation ведёт к станции. Преследователи находятся в её крыльях и башне; из них выпадает Eye Crystal.",
    "the_obliterator": "Энд: Space Station. Найди Teleport Machine, добывай Eye Crystal из Annihilation Pursuer и активируй машину.",
}

# New registry IDs checked against:
# - lender544/new1.20.1 ModEntities.java (Cataclysm entity registry)
# - CERBON-MODS/Bosses-of-Mass-Destruction-FORGE / published boss roster
# - The-Aether-Team/The-Aether AetherEntityTypes.java (1.21.1-develop)
# Tuple: stable key, entity type, title, section, vanilla icon, kind, hint.
EXTRA_BOSSES = (
    ("cataclysm_ender_guardian", "cataclysm:ender_guardian", "Страж Энда", "cataclysm", "minecraft:end_stone_bricks", "boss", "Разыщи Ruined Citadel на внешних островах Энда. Eye of Void помогает найти цитадель."),
    ("cataclysm_netherite_monstrosity", "cataclysm:netherite_monstrosity", "Незеритовый монстр", "cataclysm", "minecraft:netherite_scrap", "boss", "Незер: Soul Black Smith (кузница душ). Ищи с помощью Eye of Monstrous."),
    ("cataclysm_ignis", "cataclysm:ignis", "Игнис", "cataclysm", "minecraft:blaze_powder", "boss", "Незер: Burning Arena, наводчик Eye of Flame. Добудь Burning Ashes из Ignited Revenant и активируй Altar of Fire."),
    ("cataclysm_harbinger", "cataclysm:the_harbinger", "Предвестник", "cataclysm", "minecraft:nether_star", "boss", "Под землёй обычного мира: Ancient Factory. Eye of Mech ведёт к фабрике; найди спящего босса."),
    ("cataclysm_leviathan", "cataclysm:the_leviathan", "Левиафан", "cataclysm", "minecraft:heart_of_the_sea", "boss", "Глубокий океан: Sunken City, наводчик Eye of Abyss. Активируй Altar of Abyss предметом Abyssal Sacrifice."),
    ("cataclysm_ancient_remnant", "cataclysm:ancient_remnant", "Древний останец", "cataclysm", "minecraft:chiseled_sandstone", "boss", "Пустыня: Cursed Pyramid. Eye of Desert ведёт к пирамиде. Ищи Necklace of the Desert в подозрительном песке."),
    ("cataclysm_maledictus", "cataclysm:maledictus", "Маледиктус", "cataclysm", "minecraft:blue_ice", "boss", "Снежные равнины: Frosted Prison (Eye of Curse). Найди Strange Key у Aptrgangr, открой Door of Seal, разбуди босса."),
    ("cataclysm_scylla", "cataclysm:scylla", "Сцилла", "cataclysm", "minecraft:prismarine", "boss", "Тёплый океан: парящий Acropolis (около Y=200). Используй Eye of Storm и осматривай небо."),
    ("cataclysm_ender_golem", "cataclysm:ender_golem", "Голем Энда", "cataclysm", "minecraft:purpur_block", "miniboss", "Энд: Ruined Citadel. Исследуй коридоры перед битвой со Стражем Энда."),
    ("cataclysm_ignited_revenant", "cataclysm:ignited_revenant", "Пылающий ревенант", "cataclysm", "minecraft:blaze_rod", "miniboss", "Незер: под верхним уровнем Burning Arena. Ревенанты охраняют алтарь и дают Burning Ashes."),
    ("cataclysm_aptrgangr", "cataclysm:aptrgangr", "Аптергангр", "cataclysm", "minecraft:iron_axe", "miniboss", "Снежные равнины: Frosted Prison и Abandoned Ruins. Из него выпадает Strange Key."),
    ("bomd_lich", "bosses_of_mass_destruction:lich", "Ночной лич", "bomd", "minecraft:soul_lantern", "boss", "Холодные биомы обычного мира: Lich Tower. Soul Star ведёт к башне; нужны четыре звезды для алтаря."),
    ("bomd_void_blossom", "bosses_of_mass_destruction:void_blossom", "Цветок Пустоты", "bomd", "minecraft:spore_blossom", "boss", "Глубоко под обычным миром, близ пышных пещер. Следуй за Void Lily к логову."),
    ("bomd_gauntlet", "bosses_of_mass_destruction:gauntlet", "Незерская перчатка", "bomd", "minecraft:blackstone", "boss", "Незер: редкая Gauntlet Arena в нижних слоях. Осматривай большие постройки из чёрного камня."),
    ("bomd_obsidilith", "bosses_of_mass_destruction:obsidilith", "Обсидиолит", "bomd", "minecraft:obsidian", "boss", "Внешние острова Энда: редкая Obsidilith Arena, ищи обсидиановый алтарь."),
    ("aether_slider", "aether:slider", "Слайдер", "aether", "minecraft:stone_bricks", "boss", "Измерение Aether: Bronze Dungeon, каменное подземелье в островах. Открой зал босса."),
    ("aether_valkyrie_queen", "aether:valkyrie_queen", "Королева валькирий", "aether", "minecraft:golden_sword", "boss", "Aether: Silver Dungeon, парящий замок. Победи стражей и поговори с королевой."),
    ("aether_sun_spirit", "aether:sun_spirit", "Дух Солнца", "aether", "minecraft:blaze_rod", "boss", "Aether: Gold Dungeon (золотое подземелье). Найди трон Духа Солнца."),
    ("vanilla_wither", "minecraft:wither", "Визер", "vanilla", "minecraft:wither_skeleton_skull", "boss", "Построй букву Т из 4 блоков песка душ/почвы душ и поставь 3 черепа визер-скелета наверху."),
    ("vanilla_dragon", "minecraft:ender_dragon", "Дракон Энда", "vanilla", "minecraft:dragon_head", "boss", "Центральный остров Энда. Для повторного призыва установи 4 кристалла Энда у выходного портала."),
)

GROUPS = (
    ("overworld", "Legendary: Верхний мир", "minecraft:grass_block"),
    ("nether", "Legendary: Незер", "minecraft:netherrack"),
    ("end", "Legendary: Энд", "minecraft:end_stone"),
    ("cataclysm", "Cataclysm", "minecraft:netherite_sword"),
    ("bomd", "Mass Destruction", "minecraft:crying_obsidian"),
    ("aether", "The Aether", "minecraft:glowstone"),
    ("vanilla", "Обычные боссы", "minecraft:dragon_egg"),
)


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _display(title, description, icon, *, frame="task", toast=False, background=None):
    output = {
        "icon": {"id": icon}, "title": title, "description": description,
        "frame": frame, "show_toast": toast,
        "announce_to_chat": False, "hidden": False,
    }
    if background:
        output["background"] = background
    return output


def _records():
    for entity_id, title, group, icon, kind in BOSSES:
        yield (entity_id, "legendary_monsters:" + entity_id, title, group,
               icon, kind, LEGENDARY_GUIDES[entity_id], "Legendary Monsters")
    for key, entity_type, title, group, icon, kind, hint in EXTRA_BOSSES:
        mod_name = {
            "cataclysm": "L_Ender's Cataclysm",
            "bomd": "Bosses of Mass Destruction",
            "aether": "The Aether",
            "vanilla": "Minecraft",
        }[group]
        yield key, entity_type, title, group, icon, kind, hint, mod_name


def guide_book_components():
    """Vanilla written-book data components for 1.21.1 (filterable raw pages)."""
    pages = [
        "TechQuest\nОХОТА НА БОССОВ\n\nВсе победы общие в одном мире/LAN.\nОткрывай Достижения (L).\n\nЗдесь: где искать, что использовать и как вызвать босса.",
        "КАК ПОЛЬЗОВАТЬСЯ\n\nПроверяй рецепты через JEI. В Legendary Monsters глаза-наводчики Eye ведут к строениям. В Cataclysm также есть специальные Eyes.\n\nБольшие данжи ищи в новых чанках.",
        "ПРОГРЕСС\n\nСчитается убийство, зачисленное игроку. Победа любого друга откроет достижение всем.\n\nСмерти от механизмов без зачёта игроку не учитываются.\n\nСтарые победы Legendary сохраняются.",
    ]
    for _key, _type, title, _group, _icon, _kind, hint, mod in _records():
        pages.append(title + "\n" + mod + "\n\n" + hint)
    pages.append("ПОИСК\n\nЕсли глаз не показывает цель, переходи в подходящее измерение/биом и пробуй снова.\n\nСтавь метки в Xaero. Миры с модами генерации могут отличаться от карт по сиду.")
    # In 1.21.1 every filterable page's "raw" value is a serialized text component.
    return {
        "minecraft:written_book_content": {
            "title": {"raw": "Охота на боссов"},
            "author": "TechQuest",
            "generation": 0,
            "resolved": True,
            "pages": [{"raw": json.dumps({"text": page}, ensure_ascii=False)} for page in pages],
        }
    }


def boss_checklist_datapack():
    """Return the reproducible Open Loader ZIP installed into the world."""
    pack = {
        "pack.mcmeta": _json({"pack": {
            "pack_format": 48,
            "description": "TechQuest boss checklist & hunt guide (Minecraft 1.21.1)",
        }}),
        "data/minecraft/tags/function/load.json": _json({
            "values": [NAMESPACE + ":load"]}),
        "data/minecraft/tags/function/tick.json": _json({
            "values": [NAMESPACE + ":tick"]}),
        "data/" + NAMESPACE + "/advancement/root.json": _json({
            "display": _display("TechQuest: охота на боссов",
                                "Общий прогресс LAN. Найди в инвентаре книгу «Охота на боссов»!",
                                "minecraft:nether_star",
                                background="minecraft:textures/block/deepslate_tiles.png"),
            "criteria": {"login": {"trigger": "minecraft:tick"}},
        }),
        "data/" + NAMESPACE + "/advancement/receive_guide.json": _json({
            "parent": NAMESPACE + ":root",
            "criteria": {"login": {"trigger": "minecraft:tick"}},
            "rewards": {"loot": [NAMESPACE + ":hunt_guide"]},
        }),
        "data/" + NAMESPACE + "/function/load.mcfunction": (
            "scoreboard objectives add " + OBJECTIVE + " dummy\n"
            "execute unless score #clock " + OBJECTIVE + " matches 0.. "
            "run scoreboard players set #clock " + OBJECTIVE + " 0\n").encode("utf-8"),
        "data/" + NAMESPACE + "/function/tick.mcfunction": (
            "scoreboard players add #clock " + OBJECTIVE + " 1\n"
            "execute if score #clock " + OBJECTIVE + " matches 20.. "
            "run function " + NAMESPACE + ":sync\n").encode("utf-8"),
    }
    book = guide_book_components()
    pack["data/" + NAMESPACE + "/loot_table/hunt_guide.json"] = _json({
        "type": "minecraft:advancement_reward",
        "pools": [{"rolls": 1, "entries": [{
            "type": "minecraft:item", "name": "minecraft:written_book",
            "functions": [{"function": "minecraft:set_components", "components": book}],
        }]}],
    })
    # A replacement copy is available in survival without commands.
    # Distinct recipe from the TechQuest Patchouli guide (book + compass).
    pack["data/" + NAMESPACE + "/recipe/hunt_guide.json"] = _json({
        "type": "minecraft:crafting_shapeless",
        "category": "misc",
        "ingredients": [{"item": "minecraft:book"}, {"item": "minecraft:ender_eye"}],
        "result": {"id": "minecraft:written_book", "count": 1, "components": book},
    })

    for group, title, icon in GROUPS:
        pack["data/" + NAMESPACE + "/advancement/" + group + ".json"] = _json({
            "parent": NAMESPACE + ":root",
            "display": _display(title, "Найди боссов: " + title, icon),
            "criteria": {"login": {"trigger": "minecraft:tick"}},
        })

    sync = ["scoreboard players set #clock " + OBJECTIVE + " 0"]
    for key, entity_type, title, group, icon, kind, hint, mod in _records():
        pack["data/" + NAMESPACE + "/advancement/" + key + ".json"] = _json({
            "parent": NAMESPACE + ":" + group,
            "display": _display(
                title,
                ("Мини-босс" if kind == "miniboss" else "Босс") + " · "
                + mod + ". " + hint,
                icon, frame="goal" if kind == "miniboss" else "challenge",
                toast=True,
            ),
            "criteria": {"kill": {
                "trigger": "minecraft:player_killed_entity",
                "conditions": {"entity": {"type": entity_type}},
            }},
            "rewards": {"function": NAMESPACE + ":kill/" + key},
        })
        pack["data/" + NAMESPACE + "/function/kill/" + key + ".mcfunction"] = (
            "scoreboard players set #" + key + " " + OBJECTIVE + " 1\n"
        ).encode("utf-8")
        sync.append("execute if score #" + key + " " + OBJECTIVE
                    + " matches 1.. run advancement grant @a only "
                    + NAMESPACE + ":" + key)

    pack["data/" + NAMESPACE + "/function/sync.mcfunction"] = (
        "\n".join(sync) + "\n").encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(pack):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, pack[name])
    return output.getvalue()
