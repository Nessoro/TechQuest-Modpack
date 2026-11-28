"""Cross-check checked-in recipe definitions against fresh, read-only JAR evidence.

This cannot establish runtime obtainability. The release gate deliberately rejects
unreviewed targets and unknown runtime coverage.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = "dragonrise_reforge:"
BASE = ROOT / "compat/techquest-compat/data/techquest/recipe/dragonrise"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def registrations(disassembly):
    names = {}
    last = None
    registering = False
    for line in disassembly.split("static {};")[-1].splitlines():
        match = re.search(r"// String ([a-z0-9_]+)$", line)
        if match:
            last = match[1]
        if "DeferredRegister.register:" in line or "// Method register:" in line:
            registering = True
        field = re.search(r"putstatic\s+.*// Field ([A-Za-z0-9_]+):", line)
        if field and registering:
            if last is None or field[1] in names:
                raise ValueError("Unexpected registration bytecode")
            names[field[1]] = NS + last
            registering = False
    return names


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def verify(evidence):
    inv = read(ROOT / "compat/dragonrise_inventory.json")
    detail = read(evidence / "dragonrise-detail-evidence.json")
    prog = read(evidence / "dragonrise-progression-evidence.json")
    summary = read(evidence / "dragonrise-evidence.json")
    dr = detail["dragonrise"]
    classes = dr["registration_or_codec_disassembly"]
    def klass(suffix):
        return next(v for k,v in classes.items() if k.endswith("." + suffix))
    items = registrations(klass("ModItems"))
    entities = registrations(klass("ModEntities"))
    aux = registrations(klass("DragonVehicleDeployer"))
    tabs = klass("ModTabs")
    visible_items = {items[f] for f in re.findall(r"ModItems\.([A-Za-z0-9_]+):",tabs)
                     if "ICON" not in f.upper()}
    visible_entities = {entities[f] for f in re.findall(r"ModEntities\.([A-Za-z0-9_]+):",tabs)}
    real_items = set(items.values()) | {aux["VEHICLE_DEPLOYER_BLOCK_ITEM"]}
    real_entities = set(entities.values())
    real_blocks = {aux["VEHICLE_DEPLOYER_BLOCK"]}
    rows = inv["entries"]
    targets = [e for e in rows if e.get("recipe_id")]
    bykind = lambda kinds: {e["registry_id"] for e in rows if e["kind"] in kinds}
    errors = []
    def check(condition,message):
        if not condition:
            errors.append(message)
    for kind,actual,recorded in (
        ("items",real_items,bykind({"item"})),
        ("entities",real_entities,bykind({"vehicle","entity"})),
        ("blocks",real_blocks,bykind({"block"})),
    ):
        check(actual==recorded, f"{kind}: missing {sorted(actual-recorded)}, extra {sorted(recorded-actual)}")
    check(summary["dragonrise"]["sha256"] == inv["source"]["dragonrise_sha256"], "DragonRise source fingerprint changed")
    check(summary["superb_warfare"]["sha256"] == inv["source"]["superb_warfare_sha256"], "SBW source fingerprint changed")
    target_items = {e["registry_id"] for e in targets if e["kind"]=="item"}
    target_entities = {e["registry_id"] for e in targets if e["kind"]=="vehicle"}
    check(visible_items <= target_items, "Creative-tab items missing: "+str(sorted(visible_items-target_items)))
    check(visible_entities <= target_entities, "Creative-tab deployment targets missing: "+str(sorted(visible_entities-target_entities)))
    originals = {NS+p.rsplit("/",1)[-1][:-5] for p in dr["recipe_payloads"]}
    for e in rows:
        check(set(e.get("original_recipe_ids",[])) <= originals,"Invalid legacy recipe reference: "+e["registry_id"])
    # A hidden registration is not automatically a player-facing deployment target.
    # Re-evaluate these explicit decisions if the pinned source evidence changes.
    def legacy_entity_result(obj):
        result = obj.get("result")
        return result.get("entity") if isinstance(result, dict) else None
    legacy_entities = {legacy_entity_result(obj) for obj in dr["recipe_payloads"].values()}
    for e in rows:
        if e.get("review_evidence") != "hidden_no_player_path":
            continue
        ident = e["registry_id"]
        check(ident not in visible_entities and ident not in legacy_entities and ident not in real_items
              and ident + "_deployer" not in real_items,
              "Hidden entity now has a player-facing path: " + ident)
        definition = "data/dragonrise_reforge/sbw/vehicles/" + ident.split(":",1)[1] + ".json"
        check((definition in dr["vehicle_definitions"]) == e["server_definition_present"],
              "Hidden entity server definition changed: " + ident)
    generator = klass("GeneratorEntity")
    deployer = klass("GeneratorDeployer")
    check(all(token in generator for token in ("getBurnTime", "ItemStack.shrink", "extractEnergy", "fuelTick")),
          "Generator fuel/energy evidence changed")
    check(all(token in deployer for token in ("GeneratorEntity", "Abilities.instabuild", "ItemStack.shrink")),
          "Generator deployment evidence changed")
    results = {}
    for mod,p in prog.items():
        results[mod] = {s for r in p["recipe_results"] for s in strings([r["result"],r["output"]])}
    known = set().union(*results.values())
    # Create's sequenced assembly uses a results array; the evidence collector
    # records its recipe path and registry bytecode rather than a result field.
    if (any(r["path"]=="data/create/recipe/sequenced_assembly/precision_mechanism.json"
            for r in prog["Create"]["recipe_results"])
        and any("// String precision_mechanism" in v for v in prog["Create"]["class_disassembly"].values())):
        known.add("create:precision_mechanism")
    vanilla = {"minecraft:leather","minecraft:string","minecraft:iron_ingot","minecraft:paper",
               "minecraft:red_dye","minecraft:glowstone_dust","minecraft:glass_pane","minecraft:copper_ingot"}
    known |= vanilla | real_items
    for e in targets:
        rid=e["recipe_id"].split("dragonrise/",1)[1]
        path=BASE/(rid+".json")
        if not path.is_file():
            errors.append("Missing recipe "+e["recipe_id"])
            continue
        r=read(path)
        if "inputs" in r:
            ingredients=[re.sub(r"^\d+ ","",v) for v in r["inputs"]]
        elif "key" in r:
            ingredients=[v["item"] for v in r["key"].values()]
        else:
            ingredients=[v["item"] for v in r["ingredients"]]
        for i in ingredients:
            check(i in known,"Unverified ingredient "+i+" in "+e["recipe_id"])
    for ammo in inv["external_ammunition"]:
        check(ammo["registry_id"] in results["SBW"],"Missing SBW ammo recipe "+ammo["registry_id"])
    unresolved=[e["registry_id"] for e in rows if e["implementation_status"]=="review_required"]
    report={"registry_counts":{"items":len(real_items),"entities":len(real_entities),"blocks":len(real_blocks)},
            "creative_targets":{"items":len(visible_items),"vehicles":len(visible_entities)},
            "recipe_targets":len(targets),"unresolved":unresolved,"errors":errors,
            "runtime_verified":False,"obtainable_coverage_percent":None}
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("evidence",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--require-complete",action="store_true")
    args=parser.parse_args()
    report=verify(args.evidence)
    serialized=json.dumps(report,indent=2)
    print(serialized)
    if args.output:
        args.output.write_text(serialized+"\n",encoding="utf-8")
    if report["errors"]:
        raise SystemExit("Static inventory / ingredient verification failed")
    if args.require_complete and (report["unresolved"] or not report["runtime_verified"]):
        raise SystemExit("Release blocked: unresolved targets or missing runtime obtainability evidence")


if __name__=="__main__":
    main()
