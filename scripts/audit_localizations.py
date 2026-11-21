#!/usr/bin/env python3
"""Audit English and Russian Minecraft mod locale keys in downloaded client JARs.

No game launch, network access or changes to third-party JARs are required.
Read-only audit; the result is not proof that resource-pack ordering works.
"""
import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

LOCALE = re.compile(r"^assets/([a-z0-9_.-]+)/lang/(en_us|ru_ru)\.json$")
MAX_LANG_BYTES = 8 * 1024 * 1024


def audit(mods_dir):
    files = sorted(Path(mods_dir).glob("*.jar"))
    if not files:
        raise ValueError(f"No JARs in {mods_dir}")
    english = defaultdict(dict)
    russian = defaultdict(dict)
    origins = defaultdict(set)
    warnings = []
    for jar_path in files:
        try:
            with zipfile.ZipFile(jar_path) as archive:
                for info in archive.infolist():
                    matched = LOCALE.fullmatch(info.filename)
                    if matched is None:
                        continue
                    namespace, locale = matched.groups()
                    if info.file_size > MAX_LANG_BYTES:
                        raise ValueError(f"Oversized language file in {jar_path.name}: {info.filename}")
                    try:
                        text = archive.read(info).decode("utf-8-sig")
                        data = json.loads(text)
                    except (UnicodeError, ValueError) as error:
                        warnings.append(f"{jar_path.name}: {info.filename}: {error}")
                        continue
                    if not isinstance(data, dict) or any(
                            not isinstance(k, str) or not isinstance(v, str)
                            for k, v in data.items()):
                        warnings.append(f"{jar_path.name}: invalid key/value pairs in {info.filename}")
                        continue
                    # Build tools may add metadata such as _comment; this is not player text.
                    data = {key: value for key, value in data.items()
                            if not key.startswith("_")}
                    target = english if locale == "en_us" else russian
                    target[namespace].update(data)
                    origins[namespace].add(jar_path.name)
        except (OSError, zipfile.BadZipFile) as error:
            warnings.append(f"{jar_path.name}: cannot read archive: {error}")
    results = {}
    for namespace in sorted(set(english) | set(russian)):
        en = english[namespace]
        ru = russian[namespace]
        missing = sorted(set(en) - set(ru))
        unchanged = sorted(k for k in set(en) & set(ru) if en[k] == ru[k])
        # Minecraft's String.format-based strings can crash or display broken
        # messages if a translation drops a printf placeholder. Keep this
        # diagnostic separate from missing coverage: a key can exist but still
        # require correction. Only supported format specifiers are counted.
        def placeholders(value):
            return sorted(re.findall(
                r"%(?:[1-9]\\d*\\$)?[-#+ 0,(]*\\d*(?:\\.\\d+)?[a-zA-Z]",
                value.replace("%%", ""),
            ))
        mismatches = {
            key: {"english": placeholders(en[key]), "russian": placeholders(ru[key])}
            for key in sorted(set(en) & set(ru))
            if placeholders(en[key]) != placeholders(ru[key])
        }
        results[namespace] = {
            "english_keys": len(en),
            "russian_keys": len(ru),
            "missing_count": len(missing),
            "missing_keys": missing,
            "missing_english": {key: en[key] for key in missing},
            "unchanged_count": len(unchanged),
            "unchanged_keys": unchanged,
            "placeholder_mismatch_count": len(mismatches),
            "placeholder_mismatches": mismatches,
            "source_jars": sorted(origins[namespace]),
        }
    return {
        "schema_version": 1,
        "jar_count": len(files),
        "namespace_count": len(results),
        "total_english_keys": sum(x["english_keys"] for x in results.values()),
        "total_missing_keys": sum(x["missing_count"] for x in results.values()),
        "total_placeholder_mismatches": sum(x["placeholder_mismatch_count"] for x in results.values()),
        "warning_count": len(warnings),
        "warnings": warnings,
        "namespaces": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mods", type=Path, default=Path("output/client/mods"))
    parser.add_argument("--output", type=Path, default=Path("output/localization-coverage.json"))
    parser.add_argument("--strict", action="store_true",
                        help="fail if any English keys lack a matching Russian key")
    args = parser.parse_args()
    result = audit(args.mods)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Audited {result['jar_count']} JARs / {result['namespace_count']} namespaces; "
          f"{result['total_missing_keys']} Russian keys missing, "
          f"{result['total_placeholder_mismatches']} placeholder mismatches, "
          f"{result['warning_count']} warnings.")
    print(f"Report: {args.output}")
    if args.strict and (result["total_missing_keys"] or result["warning_count"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
