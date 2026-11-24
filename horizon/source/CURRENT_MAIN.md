# Current Horizon migration input

Pinned NeoForge main commit: `02d4dc3bc0864ba7dc231cf0e703cf196220e55c` (TechQuest 0.3.3.1).

`current-main.json` is the exact Git blob of that commit's modlist.json. It contains 88 configured entries (82 Modrinth entries, 2 manual, 3 external, 1 optional local). The official imported component count may differ. This is a planning snapshot only, not a measured Horizon coverage report. The historical `techquest-0.3.3-candidate.json` and its SDK reports remain tied to 918b4bf.

Run `python horizon/tools/port_inventory.py --source horizon/source/current-main.json --out horizon/out/current-main`. Obtain a successful Build TechQuest alpha artifact for the pinned source before SDK carry; do not reuse historical coverage or claim runtime success.
