// First-party decoder audit for pinned Horizon c78187d. No Minecraft files included.
// Build as an example of horizon-world; arguments: effective content root, trial datapack.
use horizon_world::{
    registry::BlockRegistry,
    worldgen::{
        generator::{GeneratorData, OverworldGenerator},
        overrides::WorldgenOverrides,
    },
};
use std::{fs, io, path::Path};

fn files(root: &Path, directory: &Path, overrides: &mut WorldgenOverrides) -> io::Result<()> {
    for entry in fs::read_dir(directory)? {
        let entry = entry?;
        let path = entry.path();
        if entry.file_type()?.is_symlink() {
            return Err(io::Error::other("symlink in audit input"));
        }
        if path.is_dir() {
            files(root, &path, overrides)?;
        } else if path.extension().is_some_and(|ext| ext == "json") {
            let relative = path.strip_prefix(root).map_err(io::Error::other)?;
            overrides.add_file("trial", &relative.to_string_lossy(), || {
                fs::read_to_string(&path).ok()
            });
        }
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 {
        return Err("expected EFFECTIVE_CONTENT_ROOT TRIAL_DATAPACK".into());
    }
    let root = Path::new(&args[1]);
    let pack = Path::new(&args[2]);
    let mut overrides = WorldgenOverrides::default();
    files(pack, &pack.join("data"), &mut overrides)?;
    let registry = Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(
        root.join("facts.json"),
    )?)?));
    let data = GeneratorData::load_with(&root.join("worldgen"), registry, &overrides)?;
    let generator = OverworldGenerator::new(data, 263)?;
    let unsupported = generator.unsupported_features();
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "schema": 1,
            "minecraft": "26.3",
            "seed": 263,
            "generator_pipeline_accepted": true,
            "unsupported_count": unsupported.len(),
            "unsupported_features": unsupported,
            "scope": "JSON registries and feature decoding; not structure placement or gameplay",
            "server_boot_tested": false,
            "gameplay_ported": false
        }))?
    );
    Ok(())
}
