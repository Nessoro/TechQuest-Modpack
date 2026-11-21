#!/usr/bin/env python3
"""Server-authoritative, co-op Legendary Monsters checklist for Minecraft 1.21.1.

Vanilla advancements detect *player-credited* kills, a world scoreboard stores
the shared result, and a lightweight tick function grants completed milestones
to all online players (including players who join after the kill).
No separate client mod, commands, or permissions are required for players.
"""
import io
import json
import zipfile

NAMESPACE = "techquest_bosses"
OBJECTIVE = "tqb_kills"

# Entity IDs checked against Miauczel/Legendary-Monsters-1.21.1-NeoForge
# src/main/java/net/miauczel/legendary_monsters/entity/ModEntities.java.
# Tuple: registry path, Russian name, dimension group, vanilla icon, category.
BOSSES = (
    ("ancient_guardian", "Древний страж", "overworld", "minecraft:dripstone_block", "boss"),
    ("overgrown_colossus", "Заросший колосс", "overworld", "minecraft:moss_block", "boss"),
    ("cloud_golem", "Облачный голем", "overworld", "minecraft:feather", "boss"),
    ("dune_sentinel", "Страж дюн", "overworld", "minecraft:sandstone", "boss"),
    ("frostbitten_golem", "Ледяной голем", "overworld", "minecraft:blue_ice", "boss"),
    # The upstream registry really spells this 'posessed', not 'possessed'.
    ("posessed_paladin", "Одержимый паладин", "overworld", "minecraft:iron_sword", "boss"),
    ("skeletosaurus", "Скелетозавр", "nether", "minecraft:bone_block", "boss"),
    ("lava_eater", "Пожиратель лавы", "nether", "minecraft:magma_block", "boss"),
    ("warped_fungussus", "Искажённый грибной монстр", "nether", "minecraft:warped_fungus", "boss"),
    ("withered_abomination", "Иссушенное чудовище", "nether", "minecraft:soul_sand", "boss"),
    # Chorusent is registered upstream as 'endersent'.
    ("endersent", "Хорус-энт", "end", "minecraft:chorus_flower", "boss"),
    ("shulker_mimic", "Шалкеровый мимик", "end", "minecraft:shulker_shell", "miniboss"),
    ("annihilation_pursuer", "Преследователь аннигиляции", "end", "minecraft:ender_eye", "miniboss"),
    ("the_obliterator", "Уничтожитель", "end", "minecraft:nether_star", "boss"),
)

GROUPS = (
    ("overworld", "Верхний мир", "minecraft:grass_block"),
    ("nether", "Незер", "minecraft:netherrack"),
    ("end", "Энд", "minecraft:end_stone"),
)


def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _display(title, description, icon, *, frame="task", toast=False, background=None):
    result = {
        "icon": {"id": icon},
        "title": title,
        "description": description,
        "frame": frame,
        "show_toast": toast,
        "announce_to_chat": False,
        "hidden": False,
    }
    if background:
        result["background"] = background
    return result


def boss_checklist_datapack():
    """Return a reproducible Open Loader ZIP; no external mods/JARs bundled."""
    data = {
        "pack.mcmeta": _json({
            "pack": {
                "pack_format": 48,
                "description": "TechQuest shared Legendary Monsters boss checklist (1.21.1)",
            }
        }),
        "data/minecraft/tags/function/load.json": _json({
            "values": [NAMESPACE + ":load"]
        }),
        "data/minecraft/tags/function/tick.json": _json({
            "values": [NAMESPACE + ":tick"]
        }),
        "data/" + NAMESPACE + "/advancement/root.json": _json({
            "display": _display(
                "TechQuest: охота на боссов",
                "Победы над боссами Legendary Monsters: общий прогресс мира",
                "minecraft:nether_star",
                background="minecraft:textures/block/deepslate_tiles.png",
            ),
            "criteria": {"login": {"trigger": "minecraft:tick"}},
        }),
        "data/" + NAMESPACE + "/function/load.mcfunction": (
            "scoreboard objectives add " + OBJECTIVE + " dummy\n"
            "execute unless score #clock " + OBJECTIVE + " matches 0.. "
            "run scoreboard players set #clock " + OBJECTIVE + " 0\n"
        ).encode("utf-8"),
        "data/" + NAMESPACE + "/function/tick.mcfunction": (
            "scoreboard players add #clock " + OBJECTIVE + " 1\n"
            "execute if score #clock " + OBJECTIVE + " matches 20.. "
            "run function " + NAMESPACE + ":sync\n"
        ).encode("utf-8"),
    }

    for group, title, icon in GROUPS:
        data["data/" + NAMESPACE + "/advancement/" + group + ".json"] = _json({
            "parent": NAMESPACE + ":root",
            "display": _display(title, "Раздел охоты: " + title, icon),
            "criteria": {"login": {"trigger": "minecraft:tick"}},
        })

    sync_commands = ["scoreboard players set #clock " + OBJECTIVE + " 0"]
    for entity_id, name, group, icon, category in BOSSES:
        path = "data/" + NAMESPACE + "/advancement/" + entity_id + ".json"
        data[path] = _json({
            "parent": NAMESPACE + ":" + group,
            "display": _display(
                name,
                ("Мини-босс" if category == "miniboss" else "Босс")
                + " Legendary Monsters. Победа любого участника засчитывается всем.",
                icon,
                frame="goal" if category == "miniboss" else "challenge",
                toast=True,
            ),
            "criteria": {
                "kill": {
                    "trigger": "minecraft:player_killed_entity",
                    "conditions": {
                        "entity": {"type": "legendary_monsters:" + entity_id}
                    },
                }
            },
            "rewards": {"function": NAMESPACE + ":kill/" + entity_id},
        })
        data["data/" + NAMESPACE + "/function/kill/" + entity_id + ".mcfunction"] = (
            "scoreboard players set #" + entity_id + " " + OBJECTIVE + " 1\n"
        ).encode("utf-8")
        sync_commands.append(
            "execute if score #" + entity_id + " " + OBJECTIVE
            + " matches 1.. run advancement grant @a only "
            + NAMESPACE + ":" + entity_id
        )

    data["data/" + NAMESPACE + "/function/sync.mcfunction"] = (
        "\n".join(sync_commands) + "\n"
    ).encode("utf-8")

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(data):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data[name])
    return output.getvalue()
