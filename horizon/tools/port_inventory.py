#!/usr/bin/env python3
"""Offline TechQuest-to-Horizon migration inventory.

NO Java JAR is downloaded or run. These are planning decisions, not measured
Horizon launcher verdicts. Real coverage comes only from Horizon modpack import.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "techquest-0.3.3-candidate.json"
OUTPUT = ROOT / "out"

# Only possible data carry-over candidates; Java structure generators may still block porting.
DATA_CANDIDATES = {
    "terralith", "yungs-better-dungeons", "yungs-better-mineshafts",
    "yungs-better-strongholds", "yungs-better-nether-fortresses",
    "when-dungeons-arise",
}
REPLACE_OR_SKIP = {"Оптимизация", "Библиотеки", "Сервер"}
CLIENT = {"Интерфейс", "Карта и интерфейс", "Руководства"}
GAMEPLAY = {
    "Технологии", "Хранение", "RPG", "Мобы", "Боссы", "Мир",
    "Приключения", "Исследование", "Комфорт", "Передвижение",
    "Военная техника", "Разрушения",
}


def inventory(pack: dict) -> list[dict]:
    results = []
    seen = set()

    def add(mod: dict, origin: str, key: str, fallback_group: str) -> None:
        ident = mod.get(key)
        if not isinstance(ident, str) or not ident:
            raise ValueError("Invalid ID for " + origin)
        unique = (origin, ident.casefold())
        if unique in seen:
            raise ValueError("Duplicate source entry: " + ident)
        seen.add(unique)
        group = mod.get("group") or fallback_group
        if origin != "modrinth":
            choice = "manual_source_review"
            reason = "Check source rights/version; Java logic still needs native implementation."
            source = mod.get("source", "")
        elif group in REPLACE_OR_SKIP:
            choice = "replace_or_skip"
            reason = "Java optimisation/library/server utility cannot run as JAR; Horizon may replace it."
            source = "https://modrinth.com/mod/" + ident
        elif mod.get("client_only") or group in CLIENT:
            choice = "client_native_rewrite"
            reason = "Client UI and mixins require independent Horizon native features."
            source = "https://modrinth.com/mod/" + ident
        elif ident in DATA_CANDIDATES:
            choice = "inspect_data_assets"
            reason = "Check data, structure pools and code-driven worldgen before any conversion."
            source = "https://modrinth.com/mod/" + ident
        elif group in GAMEPLAY:
            choice = "native_logic_rewrite"
            reason = "Machines, AI, magic, entities, dimensions and networking depend on Java code."
            source = "https://modrinth.com/mod/" + ident
        else:
            choice = "manual_investigation"
            reason = "Unknown component; needs Horizon launcher coverage."
            source = "https://modrinth.com/mod/" + ident
        results.append({
            "id": ident, "group": group, "origin": origin,
            "required_in_neoforge": bool(mod.get("required", True)),
            "client_only": bool(mod.get("client_only", False)),
            "source": source, "decision": choice,
            "reason": reason, "horizon_status": "unverified",
        })

    for mod in pack.get("mods", []):
        add(mod, "modrinth", "project", "Прочее")
    for mod in pack.get("manual_mods", []):
        add(mod, "manual", "name", "Технологии")
    for mod in pack.get("external_mods", []):
        add(mod, "external", "name", "Военная техника")
    for mod in pack.get("optional_local_mods", []):
        add(mod, "optional_local", "name", "Военная техника")
    return results


def build_report(path: Path) -> dict:
    raw = path.read_bytes()
    pack = json.loads(raw)
    if pack.get("minecraft") != "1.21.1" or pack.get("loader") != "neoforge":
        raise ValueError("Expected a NeoForge 1.21.1 source manifest")
    mods = inventory(pack)
    return {
        "schema": 1, "source_file": path.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_minecraft": "1.21.1", "target_horizon": "26.3",
        "horizon_coverage_measured": False, "ported_third_party_mods": 0,
        "summary": {"source_entries": len(mods),
                    "planning_categories": dict(sorted(Counter(x["decision"] for x in mods).items()))},
        "entries": mods,
    }


def markdown_report(report: dict) -> str:
    rows = [
        "# TechQuest / Horizon: предварительная матрица",
        "", "**НЕ является результатом импорта в Horizon.**",
        "Все Horizon-статусы пока unverified; сторонних Java-модов перенесено: 0.",
        "NeoForge 1.21.1 и Horizon 26.3 несовместимы по Java API.",
        "", "## Предварительные решения",
        "",
    ]
    for category, n in report["summary"]["planning_categories"].items():
        rows.append(f"- {category}: {n}")
    rows += ["", "## По модам", "", "| Мод | Группа | План | Реальный статус |", "|---|---|---|---|"]
    for mod in report["entries"]:
        ident = mod["id"].replace("|", "/")
        rows.append(f'| {ident} | {mod["group"]} | {mod["decision"]} | unverified |')
    rows += [
        "", "## Как замерить реальное покрытие",
        "", "1. Скачать исходный .mrpack TechQuest из успешного Build TechQuest alpha.",
        "2. Horizon Launcher -> Modpacks -> Import a pack file и выбрать .mrpack.",
        "3. Посмотреть статусы Ported / Partial / Not yet / Not needed для каждого мода.",
        "4. CLI: `horizon-launcher modpack import <pack.mrpack>`, затем `horizon-launcher modpack list`.",
        "5. CLI: `horizon-launcher modpack port <pack> [--from <folder>]` выполняет поддерживаемый импорт локально.",
        "6. Перенесённые данные НЕ означают работоспособность Java-механик.",
        "", "Лицензии и права на исходные ресурсы модов проверять перед распространением.",
        "",
    ]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Horizon planning inventory (no JAR downloads)")
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    report = build_report(args.source)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "port-inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "port-inventory.md").write_text(markdown_report(report), encoding="utf-8")
    print(f'Inventory: {report["summary"]["source_entries"]}; actual Horizon coverage NOT MEASURED.')
    print("Reports:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
