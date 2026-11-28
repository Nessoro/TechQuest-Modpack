// World-pack feature modifier replay using Horizon's pinned MIT biome APIs.
// Copyright (c) 2026 Ludovic Marie and Horizon contributors. LICENSE-HORIZON.
use super::{
    BIOME_TAGS, BIOMES, FEATURE_TAGS, J, PLACED_FEATURES, Result, biomes, merge_tag, read_json,
};
use horizon_world::worldgen::overrides::WorldgenOverrides;
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::{Path, PathBuf},
};

fn json_files(dir: &Path, files: &mut Vec<PathBuf>) -> Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        if entry.file_type()?.is_dir() {
            json_files(&entry.path(), files)?;
        } else if entry.path().extension().is_some_and(|s| s == "json") {
            files.push(entry.path());
        }
    }
    Ok(())
}

/// Apply add/remove_features after the world's selected packs have replaced
/// biome definitions. Spawn modifiers are deliberately not replayed here.
pub fn reapply_worldpack_features(
    root: &Path,
    overrides: &mut WorldgenOverrides,
) -> Result<Vec<String>> {
    let mut files = Vec::new();
    let data = root.join("data");
    if !data.is_dir() {
        return Ok(Vec::new());
    }
    for namespace in fs::read_dir(&data)? {
        let namespace = namespace?;
        for loader in ["forge", "neoforge"] {
            let dir = namespace.path().join(loader).join("biome_modifier");
            if dir.is_dir() {
                json_files(&dir, &mut files)?;
            }
        }
    }
    files.sort();
    let mut warnings = Vec::new();
    let mut modifiers = Vec::new();
    for file in files {
        let text = fs::read_to_string(&file)?;
        let value: serde_json::Value = serde_json::from_str(&text)?;
        if !matches!(
            value["type"].as_str(),
            Some(
                "forge:add_features"
                    | "neoforge:add_features"
                    | "forge:remove_features"
                    | "neoforge:remove_features"
            )
        ) {
            continue;
        }
        let relative = file
            .strip_prefix(root)?
            .to_str()
            .ok_or("non-UTF8 modifier path")?;
        let namespace = relative
            .split('/')
            .nth(1)
            .ok_or("modifier has no namespace")?;
        modifiers.extend(biomes::Modifier::read(
            namespace,
            relative,
            &text,
            &mut warnings,
        )?);
    }
    if modifiers.is_empty() {
        return Ok(warnings);
    }
    let root_biomes = read_json(&root.join(BIOMES))?;
    let mut doc = root_biomes.clone();
    // Root modifiers ran before world packs existed. Restore only the original
    // feature lists, preserving already-applied non-feature root attributes.
    // This also lets a world's replace:true biome tag change the target set.
    let original = read_json(&root.join("worldgen/biomes_before_modifiers.json"))?;
    if let J::Obj(entries) = original {
        for (id, original_text) in entries {
            let (Some(J::Str(current)), J::Str(original)) = (doc.get(&id), original_text) else {
                continue;
            };
            let mut value: J = serde_json::from_str(current)?;
            let before: J = serde_json::from_str(&original)?;
            let features = before
                .get("features")
                .cloned()
                .unwrap_or_else(|| J::Arr(Vec::new()));
            if value.get("features") != Some(&features) {
                value.set("features", features);
                doc.set(&id, J::Str(serde_json::to_string(&value)?));
            }
        }
    }
    let overridden: BTreeSet<String> = overrides
        .entries("biomes")
        .map(|(id, _)| id.to_owned())
        .collect();
    for (id, text) in overrides.entries("biomes") {
        doc.set(id, J::Str(text.to_owned()));
    }
    let ids: BTreeSet<String> = match &doc {
        J::Obj(entries) => entries.iter().map(|(id, _)| id.clone()).collect(),
        _ => return Err("biome bundle is not an object".into()),
    };
    let bundle = |name: &str| -> Result<BTreeMap<String, String>> {
        if !root.join(name).exists() {
            return Ok(BTreeMap::new());
        }
        Ok(match read_json(&root.join(name))? {
            J::Obj(entries) => entries
                .into_iter()
                .filter_map(|(id, value)| match value {
                    J::Str(text) => Some((id, text)),
                    _ => None,
                })
                .collect(),
            _ => return Err(format!("{name} is not an object").into()),
        })
    };
    let mut tags = bundle(BIOME_TAGS)?;
    for (id, _, text) in overrides.tags("biome_tags") {
        let value: J = serde_json::from_str(text)?;
        let Some(J::Arr(values)) = value.get("values") else {
            return Err(format!("{id}: no biome tag values").into());
        };
        let previous = if value.get("replace") == Some(&J::Bool(true)) {
            None
        } else {
            tags.get(id).map(String::as_str)
        };
        let merged = merge_tag(previous, values, id)?;
        tags.insert(id.to_owned(), merged);
    }
    let mut placed: BTreeSet<String> = bundle(PLACED_FEATURES)?.into_keys().collect();
    placed.extend(
        overrides
            .entries("placed_features")
            .map(|(id, _)| id.to_owned()),
    );
    let feature_tags = bundle(FEATURE_TAGS)?;
    let empty_ids = BTreeSet::new();
    let empty_tags = BTreeMap::new();
    biomes::apply(
        &mut doc,
        &modifiers,
        &biomes::Registry {
            what: "biome",
            ids: &ids,
            tags: &tags,
        },
        &biomes::Registry {
            what: "placed feature",
            ids: &placed,
            tags: &feature_tags,
        },
        &biomes::Registry {
            what: "entity type",
            ids: &empty_ids,
            tags: &empty_tags,
        },
        &BTreeMap::new(),
        &mut warnings,
    )?;
    if let J::Obj(entries) = doc {
        for (id, value) in entries {
            if let J::Str(text) = value {
                if overridden.contains(&id)
                    || root_biomes.get(&id).and_then(J::as_str) != Some(text.as_str())
                {
                    overrides.set("biomes", &id, text);
                }
            }
        }
    }
    Ok(warnings)
}
