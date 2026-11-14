#!/usr/bin/env python3
"""Prepare a local Terralith worldgen trial; never installs into an existing world.

Expands legacy weird_scaled_sampler before the official 26.3 upgrader runs.
Third-party data stay local. Sources and all unselected outside files are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib

RARITIES = {
    "type_1": ((-0.5, 0.0, 0.5), (0.75, 1.0, 1.5, 2.0)),
    "type_2": ((-0.75, -0.5, 0.5, 0.75), (0.5, 0.75, 1.0, 2.0, 3.0)),
}
KINDS = {"worldgen", "dimension", "dimension_type", "structure"}
DOCUMENTATION_BIOME = "terralith:comment_dont_generate_strips_here"
PUMPKIN = "minecraft:patch_pumpkin"
CANE = "minecraft:patch_sugar_cane"
# Vanilla 1.21.1 TrunkPlacer.isDirt after binding its original dirt tag.
# The 26.3 dirt tag has different members, so using that tag changes behavior.
LEGACY_TREE_SOILS = ("minecraft:dirt", "minecraft:coarse_dirt", "minecraft:podzol",
                     "minecraft:muddy_mangrove_roots", "minecraft:moss_block",
                     "minecraft:rooted_dirt", "minecraft:mud")


def expand(value):
    """Return (legacy-compatible expression, number of samplers expanded).

    r * abs(noise(x/r, y/r, z/r)), selected by the input's rarity interval.
    Unrelated expressions are unchanged; unknown mapper shapes fail closed.
    The official upgrader translates the resulting arithmetic/cache children.
    """
    if isinstance(value, list):
        pairs = [expand(child) for child in value]
        return [v for v, _ in pairs], sum(n for _, n in pairs)
    if not isinstance(value, dict):
        return value, 0
    pairs = {key: expand(child) for key, child in value.items()}
    result = {key: pair[0] for key, pair in pairs.items()}
    count = sum(pair[1] for pair in pairs.values())
    if value.get("type") not in ("weird_scaled_sampler", "minecraft:weird_scaled_sampler"):
        return result, count
    if set(value) != {"type", "input", "noise", "rarity_value_mapper"}:
        raise ValueError("unreviewed weird_scaled_sampler fields")
    mapper = value["rarity_value_mapper"]
    if not isinstance(mapper, str) or mapper not in RARITIES:
        raise ValueError("unreviewed rarity mapper")
    noise = value["noise"]
    if not isinstance(noise, str):
        raise ValueError("expected a named legacy noise holder")
    thresholds, scales = RARITIES[mapper]
    branches = [{"type": "minecraft:mul", "argument1": scale,
                 "argument2": {"type": "minecraft:abs", "argument": {
                     "type": "minecraft:noise", "noise": noise,
                     "xz_scale": 1.0 / scale, "y_scale": 1.0 / scale}}}
                for scale in scales]
    return {"type": "minecraft:interval_select", "input": result["input"],
            "thresholds": list(thresholds), "functions": branches}, count + 1


def selected(relative: Path) -> bool:
    parts = relative.parts
    kind = len(parts) >= 4 and (parts[2] in KINDS
                               or parts[2:4] == ("tags", "worldgen"))
    return (kind and parts[0] == "data"
            and relative.suffix in (".json", ".nbt"))


def normalize_carvers(biome: dict) -> tuple[dict, int]:
    """1.21.1's AIR list becomes 26.3's ordered carver holder set.

    A nonempty LIQUID step cannot be collapsed without a separate review.
    """
    if not isinstance(biome, dict):
        raise ValueError("expected a biome JSON object")
    carvers = biome.get("carvers")
    if not isinstance(carvers, dict):
        return biome, 0
    if set(carvers) - {"air", "liquid"} or carvers.get("liquid", []) != []:
        raise ValueError("unreviewed legacy carving steps")
    air = carvers.get("air", [])
    if not isinstance(air, list) or not all(isinstance(v, str) for v in air):
        raise ValueError("expected an ordered list of named AIR carvers")
    return {**biome, "carvers": list(air)}, 1


def normalize_feature_order(biome: dict) -> tuple[dict, int]:
    """Migrate the adjacent cane/pumpkin pair to vanilla 26.3 order.

    Preserve every feature and every other order relation. Interleaved or
    duplicate pairs need review rather than an arbitrary global reordering.
    """
    features = biome.get("features", [])
    if not isinstance(features, list) or any(not isinstance(step, list) for step in features):
        raise ValueError("expected biome feature lists")
    if len(features) <= 9 or CANE not in features[9] or PUMPKIN not in features[9]:
        return biome, 0
    step = list(features[9])
    if step.count(CANE) != 1 or step.count(PUMPKIN) != 1:
        raise ValueError("duplicate feature-order pair needs review")
    cane, pumpkin = step.index(CANE), step.index(PUMPKIN)
    if pumpkin < cane:
        return biome, 0
    if pumpkin != cane + 1:
        raise ValueError("interleaved feature-order pair needs review")
    step[cane], step[pumpkin] = step[pumpkin], step[cane]
    return {**biome, "features": features[:9] + [step] + features[10:]}, 1


def normalize_marker(value):
    """Remove only Terralith 2.6.2's explicit non-biome comment in an OR list."""
    if isinstance(value, list):
        pairs = [normalize_marker(v) for v in value]
        return [v for v, _ in pairs], sum(n for _, n in pairs)
    if not isinstance(value, dict):
        return value, 0
    pairs = {k: normalize_marker(v) for k, v in value.items()}
    result = {k: v for k, (v, _) in pairs.items()}
    count = sum(n for _, n in pairs.values())
    names = value.get("biome_is")
    if (value.get("type") in ("minecraft:biome", "biome") and isinstance(names, list)
            and DOCUMENTATION_BIOME in names):
        result["biome_is"] = [v for v in names if v != DOCUMENTATION_BIOME]
        count += names.count(DOCUMENTATION_BIOME)
    return result, count


def normalize_trees(value):
    """Preserve legacy soil replacement using the optional below-trunk provider.

    A non-forced tree samples dirt_provider only when the existing block is
    not one of the original seven soils. No fallback means no write/sample.
    """
    if isinstance(value, list):
        pairs = [normalize_trees(v) for v in value]
        return [v for v, _ in pairs], sum(n for _, n in pairs)
    if not isinstance(value, dict):
        return value, 0
    pairs = {k: normalize_trees(v) for k, v in value.items()}
    result = {k: v for k, (v, _) in pairs.items()}
    count = sum(n for _, n in pairs.values())
    if value.get("type") not in ("tree", "minecraft:tree"):
        return result, count
    config = result.get("config", result)
    if not isinstance(config, dict):
        raise ValueError("expected a tree configuration object")
    if "dirt_provider" not in config:
        return result, count
    if "below_trunk_provider" in config:
        raise ValueError("tree has both legacy and current soil providers")
    provider = config["dirt_provider"]
    if (not isinstance(provider, dict) or set(provider) != {"type", "state"}
            or provider["type"] not in ("simple_state_provider", "minecraft:simple_state_provider")):
        raise ValueError("review a non-simple legacy tree dirt provider")
    force = config.get("force_dirt", False)
    if not isinstance(force, bool):
        raise ValueError("expected boolean force_dirt")
    below = provider if force else {
        "type": "minecraft:rule_based", "rules": [{
            "if_true": {"type": "minecraft:not", "predicate": {
                "type": "minecraft:matching_blocks", "blocks": list(LEGACY_TREE_SOILS)}},
            "then": provider}]}
    config = {k: v for k, v in config.items() if k not in ("dirt_provider", "force_dirt")}
    config["below_trunk_provider"] = below
    return ({**result, "config": config} if "config" in result else config), count + 1


def normalize_disk_providers(value):
    """Give the legacy disk RuleBasedStateProvider its current discriminator.

    The old record's fallback and ordered rules are preserved; the official
    upgrader handles their nested providers and block states afterwards.
    """
    if isinstance(value, list):
        pairs = [normalize_disk_providers(v) for v in value]
        return [v for v, _ in pairs], sum(n for _, n in pairs)
    if not isinstance(value, dict):
        return value, 0
    pairs = {k: normalize_disk_providers(v) for k, v in value.items()}
    result = {k: v for k, (v, _) in pairs.items()}
    count = sum(n for _, n in pairs.values())
    if value.get("type") not in ("disk", "minecraft:disk"):
        return result, count
    config = result.get("config", result)
    if not isinstance(config, dict):
        raise ValueError("expected a disk configuration object")
    provider = config.get("state_provider")
    if not isinstance(provider, dict) or "type" in provider:
        return result, count
    if not ({"fallback", "rules"} & set(provider)):
        return result, count
    if set(provider) != {"fallback", "rules"} or not isinstance(provider["rules"], list):
        raise ValueError("unreviewed legacy disk provider shape")
    if any(not isinstance(rule, dict) or set(rule) != {"if_true", "then"}
           for rule in provider["rules"]):
        raise ValueError("unreviewed legacy disk rule shape")
    config = {**config, "state_provider": {"type": "minecraft:rule_based", **provider}}
    return ({**result, "config": config} if "config" in result else config), count + 1


def noise_parameter_key(value: dict) -> str:
    if (set(value) != {"firstOctave", "amplitudes"}
            or type(value["firstOctave"]) is not int
            or not isinstance(value["amplitudes"], list)
            or len(value["amplitudes"]) > 32
            or any(type(v) not in (int, float) or v < 0 for v in value["amplitudes"])):
        raise ValueError("unreviewed legacy noise parameters")
    return json.dumps({"firstOctave": value["firstOctave"],
                       "amplitudes": [float(v) for v in value["amplitudes"]]},
                      sort_keys=True, separators=(",", ":"), allow_nan=False)


def noise_provider(value) -> bool:
    return (isinstance(value, dict) and isinstance(value.get("type"), str)
            and "seed" in value and "scale" in value
            and value["type"].removeprefix("minecraft:") in (
                "noise_provider", "dual_noise_provider", "noise_threshold_provider",
                "noise", "dual_noise", "noise_threshold"))


def collect_noise_parameters(value, records: dict) -> int:
    count = 0
    if isinstance(value, list):
        return sum(collect_noise_parameters(v, records) for v in value)
    if not isinstance(value, dict):
        return 0
    if noise_provider(value):
        for field in ("noise", "slow_noise"):
            spec = value.get(field)
            if isinstance(spec, dict) and "firstOctave" in spec:
                records[noise_parameter_key(spec)] = spec
                count += 1
    return count + sum(collect_noise_parameters(v, records) for v in value.values())


def inline_noise_parameters(value, converted: dict):
    if isinstance(value, list):
        pairs = [inline_noise_parameters(v, converted) for v in value]
        return [v for v, _ in pairs], sum(n for _, n in pairs)
    if not isinstance(value, dict):
        return value, 0
    pairs = {k: inline_noise_parameters(v, converted) for k, v in value.items()}
    result = {k: v for k, (v, _) in pairs.items()}
    count = sum(n for _, n in pairs.values())
    if noise_provider(value):
        for field in ("noise", "slow_noise"):
            spec = value.get(field)
            if isinstance(spec, dict) and "firstOctave" in spec:
                result[field] = converted[noise_parameter_key(spec)]
                count += 1
    return result, count


def normalize_patches(value):
    """Compose legacy attempts without changing random draws or short circuiting.

    A one-child overlay supplies the configured-feature boundary; the inner
    overlay retains an inline or named placed feature and its modifiers.
    Symmetric trapezoids draw nextInt(spread+1) twice, including spread=0.
    The pinned engine only accepts offsets in [-16,16]; wider patches remain
    explicitly unsupported instead of being clipped or redistributed.
    """
    if isinstance(value, list):
        pairs = [normalize_patches(v) for v in value]
        return [v for v, _ in pairs], sum(n for _, n in pairs)
    if not isinstance(value, dict):
        return value, 0
    pairs = {k: normalize_patches(v) for k, v in value.items()}
    result = {k: v for k, (v, _) in pairs.items()}
    count = sum(n for _, n in pairs.values())
    if value.get("type") not in ("random_patch", "minecraft:random_patch",
                                 "flower", "minecraft:flower"):
        return result, count
    if set(value) != {"type", "tries", "xz_spread", "y_spread", "feature"}:
        raise ValueError("unreviewed legacy patch fields")
    if any(type(value[k]) is not int or value[k] < 0
           for k in ("tries", "xz_spread", "y_spread")):
        raise ValueError("expected nonnegative patch integers")
    if not isinstance(value["feature"], (str, dict)):
        raise ValueError("expected a named or inline patch placed feature")
    if value["tries"] > 4096 or max(value["xz_spread"], value["y_spread"]) > 16:
        return result, count
    def spread(size):
        return {"type": "minecraft:trapezoid", "min": -size, "max": size, "plateau": 0}
    attempt = {"feature": {"type": "minecraft:overlay", "features": [result["feature"]]},
               "placement": [{"type": "minecraft:count", "count": value["tries"]},
                             {"type": "minecraft:offset", "x": spread(value["xz_spread"]),
                              "y": spread(value["y_spread"]), "z": spread(value["xz_spread"])}]}
    return {"type": "minecraft:overlay", "features": [attempt]}, count + 1


def has_legacy_patch(value):
    if isinstance(value, list):
        return any(has_legacy_patch(v) for v in value)
    if not isinstance(value, dict):
        return False
    return (value.get("type") in ("random_patch", "minecraft:random_patch",
                                  "flower", "minecraft:flower")
            or any(has_legacy_patch(v) for v in value.values()))


def prepare(work: Path, port_tool: Path, output: Path, resources: Path | None = None) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("output must be a new directory; existing worlds are never modified")
    if any((parent / "level.dat").exists() for parent in output.resolve().parents):
        raise ValueError("stage outside an existing world, then review before installation")
    if any((parent / "horizon-resources.json").exists() for parent in output.resolve().parents):
        raise ValueError("stage outside prepared game resources")
    for origin in (work, resources):
        if origin is not None and origin.resolve() in output.resolve().parents:
            raise ValueError("output must be separate from source work and prepared resources")
    root = work.resolve() / "mods/terralith"
    manifest = tomllib.loads((root / "carry/horizon-mod.toml").read_text())
    if manifest.get("id") != "terralith" or manifest.get("version") != "2.6.2":
        raise ValueError("review a different Terralith version before adapting it")
    base_hash = None
    if resources is not None:
        prepared = json.loads((resources / "horizon-resources.json").read_text())
        if prepared.get("minecraft") != "26.3" or prepared.get("schema") != 7:
            raise ValueError("expected official Horizon 26.3 resources")
        data = (resources / "worldgen/biomes.json").read_bytes()
        base_hash = hashlib.sha256(data).hexdigest()
        pairs = []
        for text in json.loads(data).values():
            steps = json.loads(text).get("features", [])
            if len(steps) > 9 and PUMPKIN in steps[9] and CANE in steps[9]:
                pairs.append(steps[9].index(PUMPKIN) < steps[9].index(CANE))
        if not pairs or not all(pairs):
            raise ValueError("prepared vanilla feature order differs: review migration")
    sources, payloads, transformed, total, carver_lists = [], {}, [], 0, 0
    unselected_outside = []
    for section in ("carry", "outside"):
        base = root / section
        for path in sorted((base / "data").rglob("*")):
            if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
                raise ValueError("symlink in local source")
            if not path.is_file():
                continue
            relative = path.relative_to(base).as_posix()
            if not selected(path.relative_to(base)):
                if section == "outside":
                    unselected_outside.append(relative)
                continue
            data = path.read_bytes()
            previous = payloads.get(relative)
            if previous is not None and previous != data:
                raise ValueError("conflicting carry/outside source: " + relative)
            payloads[relative] = data
            sources.append({"section": section, "path": relative,
                            "sha256": hashlib.sha256(data).hexdigest()})
    if not payloads or "data/minecraft/dimension/overworld.json" not in payloads:
        raise ValueError("complete carried and outside worldgen inputs required")
    if "data/terralith/worldgen/biome/comment_dont_generate_strips_here.json" in payloads:
        raise ValueError("documentation marker is now a real biome: review required")
    # Validate and transform all inputs before creating any output.
    markers, feature_orders, trees, disk_providers = 0, 0, 0, 0
    noise_records, noise_occurrences = {}, 0
    for relative, data in list(payloads.items()):
        if relative.endswith(".json"):
            value, count = expand(json.loads(data))
            noise_occurrences += collect_noise_parameters(value, noise_records)
            value, removed = normalize_marker(value)
            value, tree_count = normalize_trees(value)
            value, disk_count = normalize_disk_providers(value)
            normalized = 0
            reordered = 0
            if "/worldgen/biome/" in relative:
                value, normalized = normalize_carvers(value)
                value, reordered = normalize_feature_order(value)
            if count or normalized or removed or reordered or tree_count or disk_count:
                payloads[relative] = (json.dumps(value, indent=2) + "\n").encode()
                transformed.append(relative)
                total += count
                carver_lists += normalized
                markers += removed
                feature_orders += reordered
                trees += tree_count
                disk_providers += disk_count
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".terralith-worldgen-", dir=output.parent) as temporary:
        stage = Path(temporary)
        raw, upgraded = stage / "input", stage / "upgraded"
        for relative, data in payloads.items():
            path = raw / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (raw / "pack.mcmeta").write_text(json.dumps({"pack": {
            "pack_format": 48, "description": "TechQuest local Terralith worldgen trial"}}))
        generated = {}
        for key, spec in noise_records.items():
            name = hashlib.sha256(key.encode()).hexdigest()
            relative = f"data/terralith/worldgen/noise/_techquest_parameters/{name}.json"
            if relative in payloads:
                raise ValueError("generated noise parameter path conflicts with a source")
            path = raw / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(spec))
            generated[key] = relative
        result = subprocess.run([str(port_tool.resolve()), "upgrade-datapack", str(raw), str(upgraded)],
                                capture_output=True, text=True, check=True, timeout=180)
        converted = {}
        for key, relative in generated.items():
            path = upgraded / relative
            spec = json.loads(path.read_text())
            if "base_octave" not in spec or "firstOctave" in spec:
                raise ValueError("official upgrader did not convert noise parameters")
            converted[key] = spec
            path.unlink()  # Only our temporary conversion record, never a source file.
        noise_converted, patches = 0, 0
        deferred_patches = []
        for path in sorted((upgraded / "data").rglob("*.json")):
            value, count = inline_noise_parameters(json.loads(path.read_bytes()), converted)
            value, patch_count = normalize_patches(value)
            if has_legacy_patch(value):
                deferred_patches.append(path.relative_to(upgraded).as_posix())
            if count or patch_count:
                path.write_text(json.dumps(value, indent=2) + "\n")
            noise_converted += count
            patches += patch_count
        if noise_converted != noise_occurrences:
            raise ValueError("noise parameter occurrence count changed during official upgrade")
        report = {"schema": 1, "minecraft": "26.3", "source_minecraft": "1.21.1",
                  "terralith": "2.6.2", "input_files": len(payloads),
                  "expanded_samplers": total, "transformed_files": transformed,
                  "normalized_carver_lists": carver_lists,
                  "removed_documentation_biome_markers": markers,
                  "reordered_adjacent_feature_pairs": feature_orders,
                  "normalized_tree_configs": trees,
                  "normalized_disk_providers": disk_providers,
                  "normalized_noise_provider_parameters": noise_converted,
                  "unique_noise_parameter_records": len(generated),
                  "temporary_noise_records_removed": True,
                  "normalized_patch_configs": patches,
                  "deferred_patch_files": deferred_patches,
                  "prepared_biomes_sha256": base_hash,
                  "sources": sources, "official_upgrade_output": result.stdout.splitlines(),
                  "unselected_outside": unselected_outside,
                  "source_files_modified": False, "server_boot_tested": False,
                  "natural_generation_verified": False, "gameplay_ported": False,
                  "bit_exact_1_21_1_parity_claimed": False}
        (upgraded / "techquest-worldgen-trial.json").write_text(
            json.dumps(report, indent=2) + "\n")
        upgraded.rename(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--port-tool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.work, args.port_tool, args.output, args.resources)
    print(json.dumps({k: v for k, v in report.items() if k != "sources"}, indent=2))


if __name__ == "__main__":
    main()
