# Third-party localization notice — BuildCraft Community Edition

Original Russian language strings and handbook translations were derived from
[BCCE-team/Localizations](https://github.com/BCCE-team/Localizations)
at commit `eff3c6005331b5ef00f461f6a7a39bb0a458eb68`.

Source files:
- `buildcraft/lang/ru_ru.json`
- `buildcraft/guide/text/ru_ru.json`

Original contributors: BCCE-team/Localizations contributors.

License of these source files: **Mozilla Public License 2.0 (MPL-2.0)**.
The license text is included as
`THIRD_PARTY_LICENSES/BCCE_LOCALIZATIONS_MPL-2.0.txt` in the
TechQuest compatibility mod and the corresponding repository source.

Changes made for TechQuest:
- Russian language strings were merged with existing pack-specific translations;
- missing English BuildCraft 8.0.23 entries were translated;
- technical abbreviations and mod/brand names were preserved;
- original language keys and formatting placeholders were retained.

The resulting files remain available in source form in this repository.
No authorship of the original BCCE translations is claimed by TechQuest.

## Just Enough Items (JEI)

The file `assets/jei/lang/ru_ru.json` in TechQuest Compatibility is based on
[`mezz/JustEnoughItems` / Minecraft 1.21.1 Russian translation](https://github.com/mezz/JustEnoughItems/blob/1.21.1/Common/src/main/resources/assets/jei/lang/ru_ru.json).
The original translations, their authors and the JEI project retain attribution.
License: **MIT**, reproduced in `THIRD_PARTY_LICENSES/JEI_MIT.txt`.
TechQuest added translations for the eight new bookmark-preview settings that were
absent from the upstream Russian file examined on 2026-11-20.
This language resource is an overlay: the original version-pinned JEI binary is
not modified, and no JEI source or binary code is redistributed as part of this change.

## Mekanism and Mekanism: Generators

The Russian JSON files at `assets/mekanism/lang/ru_ru.json` and
`assets/mekanismgenerators/lang/ru_ru.json` are drawn from the official
[`mekanism/Mekanism`](https://github.com/mekanism/Mekanism) repository's
`1.21.x` source branch, accessed on 2026-11-20.

The original translators and Mekanism project retain attribution.
License: **MIT**, included as `THIRD_PARTY_LICENSES/MEKANISM_MIT.txt`.
These text resources are bundled as locale overlays in TechQuest Compatibility;
neither Mekanism's original binaries nor gameplay logic are modified.
The source branch may include more recent texts than pinned Mekanism 10.7.19.85;
the exact keys and placeholders must be checked by the pack CI auditor.

## Mowzie's Mobs Russian language strings

`assets/mowziesmobs/lang/ru_ru.json` is the Russian language resource from
[`BobMowzie/MowziesMobs-Public`](https://github.com/BobMowzie/MowziesMobs-Public/blob/main/src/main/resources/assets/mowziesmobs/lang/ru_ru.json).
Copyright remains with **Bob Mowzie, pau101 and the credited localization authors**;
the original mod is [Mowzie's Mobs](https://www.curseforge.com/minecraft/mc-mods/mowzies-mobs).
This is an **unofficial, fan-made TechQuest localization overlay** and not an
official Mowzie's Mobs distribution or endorsement.
The upstream custom license has been included verbatim at
`THIRD_PARTY_LICENSES/MOWZIES_MOBS_LICENSE.txt`.
TechQuest does not change or repackage the original mod JAR. The replacement
locale is intended to work around invalid JSON in the pinned JAR's Russian
language entry; actual NeoForge behavior has **not** yet been tested in game.

## Xaero's World Map Russian language strings

`assets/xaeroworldmap/lang/ru_ru.json` is copied from the community
[`mpustovoi/Translations-For-Mods` translation](https://github.com/mpustovoi/Translations-For-Mods/blob/main/assets/xaeroworldmap/lang/ru_ru.json),
by its contributors. It remains subject to **Creative Commons
Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**.
The upstream license text is copied at
`THIRD_PARTY_LICENSES/XAERO_RU_CC-BY-SA-4.0.txt`.
This attribution and license apply to the translated text file, not the
rest of the TechQuest repository or any original Minecraft mod JAR.

## Open Parties and Claims Russian language strings

`assets/openpartiesandclaims/lang/ru_ru.json` is a **modified selection**
of the Russian language resources maintained by
[`MinWixMods/langs`](https://github.com/MinWixMods/langs/blob/main/openpartiesandclaims/ru_ru.json).
Only translation keys actually present in the pinned English 1.21 language file
were retained; formatting placeholders were audited, 21 outdated messages
were retranslated by TechQuest, and exact duplicate messages were filled.
The source translation is **MIT licensed**; the original license is included as
`THIRD_PARTY_LICENSES/MINWIX_MIT.txt`. The file is not an endorsement of
TechQuest by Xaero or MinWixMods.
