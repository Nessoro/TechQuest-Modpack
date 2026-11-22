#!/usr/bin/env python3
"""Install/check/start the local six-module Horizon server prototype.

Uses already prepared, locally owned inputs. No downloads, publication, account
login or existing-world conversion. The test EULA consent must be explicit at
installation; subsequent starts reuse that installation's consent.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import tomllib
import zipfile

from server_preflight import BINARIES, MODULES, UPSTREAM, digest, inspect
from stage_terralith_content import canonicalize_block_tag
from prepare_terralith_worldgen import RECIPE_ADVANCEMENTS, normalize_recipe_unlocks

LOCK = "techquest-local-install.json"
WORLD = "techquest-horizon-test"
PACK = f"{WORLD}/datapacks/techquest_terralith"
ORITECH_NATIVE = {"0.1.0": "0.1.0", "0.2.0": "0.1.0", "0.3.0": "0.2.0"}
CORE_PATCH = Path(__file__).resolve().parents[1] / "first_party/biome_modifiers/horizon-core-patch.json"
WORLD_CORE_PATCH = Path(__file__).resolve().parents[1] / "first_party/biome_world_packs/horizon-core-patch.json"


def checked_path(path: Path) -> Path:
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("symlink in installation input/output")
    return path.resolve()


def tree_files(root: Path) -> dict[str, Path]:
    checked_path(root)
    result = {}
    for path in sorted(root.rglob("*")):
        checked_path(path)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path
        elif not path.is_dir():
            raise ValueError("unsupported filesystem entry")
    return result


def fresh_environment(root: Path) -> dict[str, str]:
    # init also reads HORIZON_PLAYERS/OP/ONLINE from the environment. Never
    # import settings or account/home paths from an existing launcher session.
    env = {k: v for k, v in os.environ.items() if not k.startswith("HORIZON_")}
    for key in ("HORIZON_HOME", "HORIZON_LAUNCHER_HOME", "XDG_DATA_HOME",
                "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        folder = root / key
        folder.mkdir(parents=True)
        env[key] = str(folder)
    env.update(HORIZON_NO_AUDIO="1", HORIZON_LAUNCHER_NO_SELF_UPDATE="1")
    return env


def run(args, *, cwd: Path, env=None, timeout=180) -> str:
    result = subprocess.run([str(x) for x in args], cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Do not include generated server settings, API endpoints or raw logs.
        action = args[args.index("--dir") + 2:] if "--dir" in args else args[1:2]
        label = " ".join(str(x).split("=", 1)[0] for x in action[:3] if not str(x).startswith("/"))
        raise ValueError(f"{Path(args[0]).name} {label} failed (exit {result.returncode})")
    return result.stdout


def check_modules(modules: Path, terralith: Path, datapack: Path, sdk: Path, work: Path,
                  pretty_pipes: Path | None = None, oritech: Path | None = None) -> dict:
    files = {mod: checked_path(terralith if mod == "terralith" else modules / f"{mod}.hmod")
             for mod in MODULES}
    if pretty_pipes is not None:
        files["prettypipes"] = checked_path(pretty_pipes)
    if oritech is not None:
        files["oritech"] = checked_path(oritech)
    owners, result = {}, {}
    for mod, path in files.items():
        check = json.loads(run([sdk, "check", path, "--json"], cwd=path.parent))
        facts = check.get("report", {})
        checksum = digest(path)
        if (check.get("ok") is not True or facts.get("id") != mod
                or facts.get("api") != "0.2" or facts.get("side") != "both"
                or facts.get("sha256") != checksum):
            raise ValueError("SDK rejected module identity/API/checksum: " + mod)
        if mod == "prettypipes" and facts.get("version") not in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0"):
            raise ValueError("expected the reviewed Pretty Pipes content prototype")
        if mod == "oritech" and facts.get("version") not in ORITECH_NATIVE:
            raise ValueError("expected the reviewed Oritech energy prototype")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("duplicate archive entries: " + mod)
            for name in names:
                rel = PurePosixPath(name)
                if rel.is_absolute() or ".." in rel.parts or "\\" in name:
                    raise ValueError("unsafe archive path: " + mod)
            meta = tomllib.loads(archive.read("horizon-mod.toml").decode())
            if "registries" not in meta.get("capabilities", []):
                raise ValueError("module needs registries: " + mod)
            if mod == "prettypipes" and facts.get("version") in ("0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0"):
                menu = "data/prettypipes/horizon/menu/pipe.json"
                if (menu not in names or json.loads(archive.read(menu)) !=
                        {"slots": 67, "data_slots": 21}):
                    raise ValueError("Pretty Pipes 0.4+ menu needs 67 slots and 21 data slots")
            if mod == "oritech":
                machines = [("basic_generator_block", 1), ("powered_furnace_block", 2)]
                if facts.get("version") == "0.3.0":
                    machines.append(("pulverizer_block", 3))
                for block, slots in machines:
                    menu = f"data/oritech/horizon/menu/{block}.json"
                    expected_menu = {"slots": slots, "data_slots": 5}
                    if slots > 1:
                        expected_menu["results"] = list(range(1, slots))
                    if menu not in names or json.loads(archive.read(menu)) != expected_menu:
                        raise ValueError("Oritech energy menu has incorrect slots/data slots")
            for namespace in meta.get("namespaces", [mod]):
                if namespace in owners and owners[namespace] != mod:
                    raise ValueError("namespace has multiple owners: " + namespace)
                owners[namespace] = mod
            if mod == "terralith":
                expected = tree_files(datapack / "data/terralith")
                if not expected:
                    raise ValueError("empty Terralith datapack overlay")
                for name, source in expected.items():
                    member = "data/terralith/" + name
                    if member not in names or archive.read(member) != source.read_bytes():
                        raise ValueError("Terralith hmod/datapack differ: " + member)
                for name in names:
                    if any(name.startswith(f"data/terralith/worldgen/{kind}/")
                           for kind in ("configured_feature", "configured_carver")):
                        raise ValueError("Terralith hmod still contains obsolete worldgen paths")
                for name, source in tree_files(work / "mods/terralith/carry").items():
                    parts = Path(name).parts
                    if (len(parts) >= 5 and parts[0] == "data" and parts[2:4] == ("tags", "block")
                            and name.endswith(".json")):
                        expected_tag, _ = canonicalize_block_tag(json.loads(source.read_bytes()))
                        if name not in names or json.loads(archive.read(name)) != expected_tag:
                            raise ValueError("Terralith hmod block tags differ from canonical source: " + name)
        result[mod] = {"path": path, "sha256": checksum, "version": facts["version"]}
    return result


def check_native_pairs(mods: dict, native: list[dict], core: list[dict] | None = None,
                       *, new_installation: bool = False):
    if mods.get("oritech", {}).get("version") in ("0.2.0", "0.3.0"):
        expected_patch = json.loads(CORE_PATCH.read_text())
        runtime_patch = json.loads(WORLD_CORE_PATCH.read_text())
        if core not in ([expected_patch], [expected_patch, runtime_patch]):
            raise ValueError("Oritech progression needs the reviewed merged-biome core correction")
        # Historical 02a locks stay verifiable. New installs must also correct
        # the feature lists replaced by an enabled world datapack.
        if (new_installation or mods["oritech"]["version"] == "0.3.0") and core != [expected_patch, runtime_patch]:
            raise ValueError("Oritech progression installations need the world-pack feature correction")
    if "oritech" in mods:
        matching = [m for m in native if m.get("id") == "techquest_oritech"]
        expected = ORITECH_NATIVE.get(mods["oritech"].get("version"))
        if (len(matching) != 1 or expected is None
                or matching[0].get("version") != expected):
            raise ValueError("Oritech content/native version mismatch or missing extension")
    if "prettypipes" not in mods:
        return
    matching = [m for m in native if m.get("id") == "techquest_pretty_pipes"]
    if len(matching) != 1:
        raise ValueError("Pretty Pipes installation has no native extension declaration")
    version = mods["prettypipes"].get("version")
    if version not in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0") or matching[0].get("version") != version:
        raise ValueError("Pretty Pipes content/native version mismatch")


def validate_trial(datapack: Path, work: Path) -> dict[str, Path]:
    files = tree_files(datapack)
    if any(name not in ("pack.mcmeta", "techquest-worldgen-trial.json") and
           not (name.startswith("data/") and Path(name).suffix in (".json", ".nbt"))
           for name in files):
        raise ValueError("unexpected files in adapted datapack")
    trial = json.loads(files["techquest-worldgen-trial.json"].read_text())
    if ((trial.get("schema"), trial.get("minecraft"), trial.get("terralith")) != (1, "26.3", "2.6.2")
            or trial.get("inlined_legacy_feature_references") != 5
            or trial.get("normalized_recipe_unlock_criteria") != 5
            or set(trial.get("selected_recipe_advancements", [])) != RECIPE_ADVANCEMENTS
            or trial.get("deferred_patch_files") != []):
        raise ValueError("expected complete reviewed adaptation, including legacy references and recipe unlocks")
    sources = trial.get("sources", [])
    if not sources or len(sources) != trial.get("input_files"):
        raise ValueError("missing source provenance")
    for source in sources:
        name = PurePosixPath(source["path"])
        if (name.is_absolute() or ".." in name.parts or "\\" in source["path"]
                or source["section"] not in ("carry", "outside")):
            raise ValueError("invalid source provenance path")
        path = checked_path(work / "mods/terralith" / source["section"] / name)
        if digest(path) != source["sha256"]:
            raise ValueError("Terralith source changed since adaptation: " + name.as_posix())
    for name in RECIPE_ADVANCEMENTS:
        origins = [source for source in sources if source["path"] == name]
        if len(origins) != 1 or name not in files:
            raise ValueError("missing restored recipe advancement: " + name)
        source = work / "mods/terralith" / origins[0]["section"] / name
        expected, count = normalize_recipe_unlocks(json.loads(source.read_bytes()))
        if count != 1 or json.loads(files[name].read_bytes()) != expected:
            raise ValueError("restored advancement differs from reviewed source: " + name)
    return files


def check_native_modules(tools: Path, sdk: Path) -> list[dict]:
    """Check declared source bundles; this alone does not prove their compilation."""
    build = json.loads((tools / "build-result.json").read_text())
    specs = build.get("native_mods", [])
    if not isinstance(specs, list):
        raise ValueError("native_mods must be a list")
    result = []
    for spec in specs:
        if not isinstance(spec, dict):
            raise ValueError("native source bundle declaration must be an object")
        mod = spec.get("id", "")
        revision = spec.get("mixins_commit", "")
        if (not isinstance(mod, str) or not isinstance(revision, str)
                or not re.fullmatch(r"[a-z0-9_]{1,64}", mod)
                or not re.fullmatch(r"[0-9a-f]{40}", revision)
                or any(entry["id"] == mod for entry in result)):
            raise ValueError("invalid/duplicate declared native source bundle")
        path = checked_path(tools / "native-mods" / f"{mod}.hnmod")
        checksum = digest(path)
        if checksum != spec.get("sha256"):
            raise ValueError("native source bundle checksum differs: " + mod)
        verdict = json.loads(run([sdk, "check", path, "--json"], cwd=path.parent))
        facts = verdict.get("report", {})
        api = f"native-1/{UPSTREAM}/{revision}"
        if (verdict.get("ok") is not True or facts.get("kind") != "native-mod"
                or facts.get("id") != mod or facts.get("version") != spec.get("version")
                or facts.get("game") != "26.3" or facts.get("api") != api
                or facts.get("sha256") != checksum):
            raise ValueError("SDK rejected native source bundle identity/pins: " + mod)
        result.append({"id": mod, "version": spec["version"], "sha256": checksum, "api": api})
    return result


def check_core_patches(tools: Path) -> list[dict]:
    patches = json.loads((tools / "build-result.json").read_text()).get("core_patches", [])
    if patches == []:
        return []
    expected = json.loads(CORE_PATCH.read_text())
    runtime = json.loads(WORLD_CORE_PATCH.read_text())
    if patches not in ([expected], [expected, runtime]):
        raise ValueError("unreviewed native core correction")
    for spec in patches:
        root = tools / "core-patches" / spec["id"]
        manifest = checked_path(root / "horizon-core-patch.json")
        source = checked_path(root / spec.get("patch_file", "merged-biomes.patch"))
        if json.loads(manifest.read_text()) != spec or digest(source) != spec["patch_sha256"]:
            raise ValueError("native core correction files differ")
        if "module_file" in spec:
            module = checked_path(root / spec["module_file"])
            if digest(module) != spec["module_sha256"]:
                raise ValueError("native core correction module differs")
    return patches


def install(*, resources: Path, tools: Path, work: Path, modules: Path,
            terralith: Path, datapack: Path, sdk: Path, upstream: Path,
            output: Path, port: int, accept_eula: bool,
            pretty_pipes: Path | None = None, oritech: Path | None = None) -> dict:
    output = checked_path(output)
    if output.exists():
        raise ValueError("installation directory must be new")
    if not 1024 <= port <= 65535:
        raise ValueError("test port must be between 1024 and 65535")
    inputs = [resources, tools, work, modules, terralith, datapack, sdk, upstream]
    resources, tools, work, modules, terralith, datapack, sdk, upstream = map(checked_path, inputs)
    if pretty_pipes is not None:
        pretty_pipes = checked_path(pretty_pipes)
        inputs.append(pretty_pipes)
    if oritech is not None:
        oritech = checked_path(oritech)
        inputs.append(oritech)
    for origin in inputs:
        origin = checked_path(origin)
        if output == origin or origin in output.parents or output in origin.parents:
            raise ValueError("installation must be separate from every input")
    for parent in output.parents:
        if (parent / "level.dat").exists() or (parent / "horizon-resources.json").exists():
            raise ValueError("installation must be outside worlds and prepared resources")
    preflight = inspect(resources, tools, work, output, accept_eula)
    if not preflight["preflight_passed"]:
        raise ValueError("preflight: " + "; ".join(preflight["problems"]))
    if run(["git", "rev-parse", "HEAD"], cwd=upstream).strip() != UPSTREAM:
        raise ValueError("upstream checkout differs from the pinned commit")
    run([tools / "horizon-prepare", "--check", "--root", upstream, "--output", resources], cwd=upstream)
    payloads = validate_trial(datapack, work)
    mods = check_modules(modules, terralith, datapack, sdk, work, pretty_pipes, oritech)
    native = check_native_modules(tools, sdk)
    core = check_core_patches(tools)
    check_native_pairs(mods, native, core, new_installation=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".techquest-install-", dir=output.parent) as temporary:
        temporary = Path(temporary)
        stage = temporary / "server"
        stage.mkdir()
        env = fresh_environment(temporary / "homes")
        server = [tools / "horizon-server", "--dir", stage]
        run([*server, "init", "--eula", "--world", WORLD, "--seed", "263", "--port", str(port),
             "--whitelist", "--yes"], cwd=stage, env=env)
        settings = {
            "server.bind": "127.0.0.1", "server.online_mode": "true", "server.whitelist": "true",
            "server.view_distance": "4", "server.simulation_distance": "4",
            "engine.path": str((tools / "horizon-engine").resolve()),
            "engine.resources": str(resources.resolve()), "engine.restart_on_crash": "false",
            "panel.bind": "", "api.bind": "", "properties.pause-when-empty-seconds": "0",
        }
        for key, value in settings.items():
            run([*server, "config", "set", f"{key}={value}"], cwd=stage, env=env)
        for name in ("ops.json", "whitelist.json"):
            if not (stage / name).exists():
                (stage / name).write_text("[]\n")
        mod_dir = stage / "horizon-mods"
        mod_dir.mkdir(exist_ok=True)
        for mod, spec in mods.items():
            shutil.copyfile(spec["path"], mod_dir / f"{mod}.hmod")
        (stage / "horizon-mods.txt").write_text("".join(f"mod.{mod}:true\n" for mod in mods))
        for name, path in payloads.items():
            target = stage / PACK / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        relative = ["server.toml", "eula.txt", "horizon-mods.txt"]
        relative += [f"horizon-mods/{mod}.hmod" for mod in mods]
        relative += [f"{PACK}/{name}" for name in payloads]
        external = {str((tools / name).resolve()): digest(tools / name) for name in BINARIES}
        external[str((tools / "build-result.json").resolve())] = digest(tools / "build-result.json")
        for spec in native:
            external[str((tools / "native-mods" / f'{spec["id"]}.hnmod').resolve())] = spec["sha256"]
        for spec in core:
            names = ["horizon-core-patch.json", spec.get("patch_file", "merged-biomes.patch")]
            if "module_file" in spec:
                names.append(spec["module_file"])
            for name in names:
                path = tools / "core-patches" / spec["id"] / name
                external[str(path.resolve())] = digest(path)
        for name in ("horizon-resources.json", "horizon-prepare.json", "facts.json", "block-tags.json"):
            external[str((resources / name).resolve())] = digest(resources / name)
        report = {
            "schema": 1, "minecraft": "26.3", "upstream_commit": UPSTREAM,
            "world": WORLD, "port": port, "bind": "127.0.0.1", "online_mode": True,
            "whitelist": True, "eula_consent_provided": True,
            "modules": {mod: {k: v for k, v in spec.items() if k != "path"} for mod, spec in mods.items()},
            "files": {name: digest(stage / name) for name in sorted(relative)}, "external_files": external,
            "server_binary": str((tools / "horizon-server").resolve()),
            "native_modules": native,
            "core_patches": core,
            "sdk_validated_modules": len(mods), "resources_check_passed": True,
            "source_hashes_rechecked": len(json.loads(payloads["techquest-worldgen-trial.json"].read_text())["sources"]),
            "hmod_datapack_synchronized": True, "server_boot_tested": False,
            "client_tested": False, "multiplayer_tested": False, "full_modpack_ported": False,
            "published": False,
        }
        (stage / LOCK).write_text(json.dumps(report, indent=2) + "\n")
        verify(stage)
        stage.rename(output)
    return report


def verify(server_dir: Path) -> dict:
    server_dir = checked_path(server_dir)
    report = json.loads((server_dir / LOCK).read_text())
    if (report.get("schema") != 1 or report.get("upstream_commit") != UPSTREAM
            or report.get("minecraft") != "26.3" or report.get("world") != WORLD
            or not set(MODULES) <= set(report.get("modules", {})) <= set(MODULES) | {"prettypipes", "oritech"}):
        raise ValueError("unrecognized local installation lock")
    check_native_pairs(report["modules"], report.get("native_modules", []), report.get("core_patches", []))
    hashes = report["files"]
    expected_mods = {f"{mod}.hmod" for mod in report["modules"]}
    if set(tree_files(server_dir / "horizon-mods")) != expected_mods:
        raise ValueError("installed module set changed")
    expected_pack = {name[len(PACK) + 1:] for name in hashes if name.startswith(PACK + "/")}
    if set(tree_files(server_dir / PACK)) != expected_pack:
        raise ValueError("installed datapack file set changed")
    # Do not let an added pack silently change world generation at next start.
    if {p.name for p in (server_dir / WORLD / "datapacks").iterdir()} != {"techquest_terralith"}:
        raise ValueError("unexpected world datapack")
    for name, checksum in hashes.items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or ".." in rel.parts or "\\" in name:
            raise ValueError("invalid installation lock path")
        if digest(checked_path(server_dir / rel)) != checksum:
            raise ValueError("installed file changed: " + name)
    for name, checksum in report["external_files"].items():
        if digest(checked_path(Path(name))) != checksum:
            raise ValueError("external tool/resources changed: " + Path(name).name)
    if report["server_binary"] not in report["external_files"]:
        raise ValueError("server binary is not locked")
    cfg = tomllib.loads((server_dir / "server.toml").read_text())
    if (cfg["server"]["bind"] != "127.0.0.1" or cfg["server"]["online_mode"] is not True
            or cfg["server"]["whitelist"] is not True or cfg["panel"]["bind"] != ""
            or cfg["engine"]["restart_on_crash"] is not False or cfg["world"]["name"] != WORLD):
        raise ValueError("isolated test configuration changed")
    if any(json.loads((server_dir / name).read_text()) for name in ("ops.json", "whitelist.json")):
        raise ValueError("this unattended test must not contain player accounts")
    return report


def start(server_dir: Path) -> None:
    report = verify(server_dir)
    server_dir = server_dir.resolve()
    # Each actual start gets new launcher/data/config homes, including reopen.
    runs = server_dir / ".runs"
    checked_path(runs)
    runs.mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="start-", dir=runs))
    env = fresh_environment(root)
    print(run([report["server_binary"], "--dir", server_dir, "start"],
              cwd=server_dir, env=env, timeout=330).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("install")
    for name in ("resources", "tools", "work", "modules", "terralith", "datapack", "sdk", "upstream", "output"):
        add.add_argument("--" + name, type=Path, required=True)
    add.add_argument("--port", type=int, default=25600)
    add.add_argument("--accept-eula", action="store_true")
    add.add_argument("--pretty-pipes", type=Path,
                     help="Optional SDK-checked transport content prototype; needs its native extension")
    add.add_argument("--oritech", type=Path,
                     help="Optional SDK-checked energy content prototype; needs its native extension")
    for name in ("verify", "start"):
        sub = commands.add_parser(name)
        sub.add_argument("--server-dir", type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    try:
        if command == "start":
            start(**args)
        elif command == "verify":
            report = verify(**args)
            print(json.dumps({"verified": True, "modules": len(report["modules"]),
                              "locked_payload_files": len(report["files"])}))
        else:
            report = install(**args)
            print(json.dumps({k: v for k, v in report.items() if k not in ("files", "external_files")}, indent=2))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        parser.exit(2, f"local installation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
