// Developer helper calling Horizon's pinned MIT content/port APIs.
// Copyright (c) 2026 Ludovic Marie and Horizon contributors; LICENSE-HORIZON.
use horizon_client_lib::mod_content::{self, ContentMod};
use serde_json::{Value, json};
use std::{
    env, fs,
    io::{self, Read},
    path::Path,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("upgrade") => {
            let mut input = String::new();
            io::stdin().read_to_string(&mut input)?;
            let mut values: Value = serde_json::from_str(&input)?;
            for (_, recipe) in values["recipes"].as_object_mut().unwrap() {
                assert!(
                    horizon_port_pack::carry::upgrade_recipe(recipe),
                    "unsupported recipe"
                );
            }
            for (_, loot) in values["loot"].as_object_mut().unwrap() {
                horizon_port_pack::carry::upgrade_loot(loot);
            }
            println!("{}", serde_json::to_string(&values)?);
        }
        Some("build") => {
            assert!(args.len() >= 4, "build BASE NEW_OUT MOD...");
            let mut mods = Vec::new();
            for name in &args[4..] {
                let path = Path::new(name);
                let package = horizon_mods::Package::read(path)?;
                mods.push(ContentMod {
                    id: package.manifest.id.clone(),
                    content: horizon_mods::Content::read(path, &package.manifest)?,
                });
            }
            mods.sort_by(|a, b| a.id.cmp(&b.id));
            assert!(!Path::new(&args[3]).exists(), "new content root required");
            let warnings = mod_content::build(Path::new(&args[2]), &mods, Path::new(&args[3]))?;
            fs::write(
                Path::new(&args[3]).join("techquest-content-build.json"),
                serde_json::to_vec_pretty(
                    &json!({"warnings":warnings,"modules":mods.iter().map(|m| &m.id).collect::<Vec<_>>()}),
                )?,
            )?;
            println!("{}", json!({"built":true,"warnings":warnings}));
        }
        _ => panic!("upgrade (JSON stdin) | build BASE NEW_OUT MOD..."),
    }
    Ok(())
}
