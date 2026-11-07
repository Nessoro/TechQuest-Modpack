#!/usr/bin/env python3
"""Check Minecraft/NeoForge version availability on Modrinth; do not download mod JARs."""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://api.modrinth.com/v2"
UA = "TechQuest-Modpack/0.1 (github.com/Nessoro/TechQuest-Modpack)"

def fetch_versions(slug, mc, loader):
    query = urllib.parse.urlencode({
        "loaders": json.dumps([loader]), "game_versions": json.dumps([mc])})
    url = BASE + "/project/" + urllib.parse.quote(slug, safe="") + "/version?" + query
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                try:
                    seconds = min(float(exc.headers.get("Retry-After", "2")), 20)
                except (ValueError, TypeError):
                    seconds = 2
                time.sleep(max(seconds, attempt + 1))
                continue
            raise

def choose_version(versions, prefix="", version_id=""):
    filtered = [v for v in versions
                if (not prefix or v.get("version_number", "").startswith(prefix))
                and (not version_id or v.get("id") == version_id)]
    if not filtered:
        return None
    stable = [v for v in filtered if v.get("version_type") == "release"]
    return max(stable or filtered, key=lambda v: v.get("date_published", ""))

def audit(cfg, fetch=fetch_versions):
    results = []
    for item in cfg["mods"]:
        slug = item["project"]
        row = {"mod": slug, "group": item.get("group", ""),
               "required": bool(item.get("required", False)),
               "status": "unknown", "version": None, "reason": None}
        try:
            versions = fetch(slug, cfg["minecraft"], cfg["loader"])
            version = choose_version(versions, item.get("version_prefix", ""), item.get("version_id", ""))
            if version is None:
                row["status"] = "missing"
                row["reason"] = "No matching loader/Minecraft version, pinned prefix or version ID"
            else:
                row["status"] = "available"
                row["version"] = version.get("version_number", "(unknown)")
                row["published"] = version.get("date_published")
        except (ValueError, urllib.error.URLError, OSError, TypeError) as exc:
            row["status"] = "error"
            row["reason"] = str(exc)[:220]
        results.append(row)
        print(f"{row['status']:>9}  {'[CORE]' if row['required'] else '[OPTION]'} {slug}  {row['version'] or row['reason'] or ''}", flush=True)
        time.sleep(.17)
    return results

def render_markdown(cfg, rows):
    available = sum(row["status"] == "available" for row in rows)
    problematic = sum(row["required"] and row["status"] != "available" for row in rows)
    lines = [
        "# TechQuest — отчёт по доступности версий", "",
        "Дата: " + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        f"Цель: **Minecraft {cfg['minecraft']} / {cfg['loader']} {cfg['loader_version']}**", "",
        f"**Доступны:** {available}/{len(rows)}. **Проблемных обязательных:** {problematic}.", "",
        "> Наличие версии на Modrinth не подтверждает совместимость модов между собой.",
        "> Запуск клиента и сервера необходимо проверять отдельно.", "",
        "| Результат | Мод | Обязательный | Версия / причина |",
        "|:--|:--|:--:|:--|"
    ]
    for row in rows:
        status = {"available": "✅", "missing": "❌", "error": "⚠️"}[row["status"]]
        detail = (row["version"] or row["reason"] or "—").replace("|", "/")
        lines.append(f"| {status} | `{row['mod']}` | {'да' if row['required'] else 'нет'} | {detail} |")
    lines.extend(["", "## Моды, добавляемые вручную", ""])
    for item in cfg.get("manual_mods", []):
        lines.append(f"- **{item['name']}** — {item['source']}")
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser(description="TechQuest Modrinth availability audit")
    parser.add_argument("--manifest", type=Path, default=ROOT / "modlist.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "audit")
    opts = parser.parse_args()
    cfg = json.loads(opts.manifest.read_text(encoding="utf-8"))
    opts.output_dir.mkdir(parents=True, exist_ok=True)
    rows = audit(cfg)
    report = render_markdown(cfg, rows)
    (opts.output_dir / "compatibility.md").write_text(report, encoding="utf-8")
    (opts.output_dir / "compatibility.json").write_text(json.dumps(
        {"minecraft": cfg["minecraft"], "loader": cfg["loader"],
         "results": rows, "manual_mods": cfg.get("manual_mods", [])},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
            output.write(report)
    print(f"Report saved to {opts.output_dir}")
    return 2 if any(row["required"] and row["status"] != "available" for row in rows) else 0

if __name__ == "__main__":
    sys.exit(main())
