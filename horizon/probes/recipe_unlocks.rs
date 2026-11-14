// First-party native component probe for pinned Horizon c78187d.
// Args: EFFECTIVE_CONTENT_ROOT INSTALLED_WORLD ORIGINAL_TERRALITH_OUTSIDE.
// Reads the actual DataStore, Tree, InventoryIndex, item matcher, Progress and
// ServerRecipeBook components. The event driver is a harness, not Game's private
// event handler, a real player login or a graphical client test.
use horizon_client::{
    advancements::{self as adv, InventoryIndex, ItemView, Progress, Tree, World},
    datapack::{self, DataStore},
    blocks::BlockFacts,
    crafting::Recipes,
    items::{ItemStack, Items},
    recipe_book::{RecipeIndex, Settings},
};
use horizon_world::loot::PackOverlay;
use serde_json::{json, Value};
use std::{collections::{BTreeMap, HashMap, HashSet}, env, path::Path};

const NAMES: [&str; 5] = ["dispenser", "dropper", "lever", "observer", "piston"];

struct ItemWorld(HashMap<String, HashSet<String>>);
impl World for ItemWorld {
    fn in_tag(&self, registry: &str, tag: &str, id: &str) -> bool {
        assert_eq!(registry, "item");
        self.0.get(tag).is_some_and(|values| values.contains(id))
    }
    fn dimension(&self) -> &str { panic!("unexpected world query") }
    fn weather(&self) -> (bool, bool) { panic!("unexpected world query") }
    fn biome(&self, _: [i32; 3]) -> String { panic!("unexpected world query") }
    fn structures(&self, _: [i32; 3]) -> Vec<String> { panic!("unexpected world query") }
    fn block(&self, _: [i32; 3]) -> (String, BTreeMap<String, String>) { panic!("unexpected world query") }
    fn fluid(&self, _: [i32; 3]) -> Option<String> { panic!("unexpected world query") }
    fn can_see_sky(&self, _: [i32; 3]) -> bool { panic!("unexpected world query") }
    fn light(&self, _: [i32; 3]) -> i32 { panic!("unexpected world query") }
    fn smokey(&self, _: [i32; 3]) -> bool { panic!("unexpected world query") }
}

enum Event<'a> { Recipe(&'a str), Inventory(&'a str, u32) }

fn apply(tree: &Tree, index: &InventoryIndex, recipes: &RecipeIndex, world: &ItemWorld,
         target: usize, event: &Event, progress: &mut Progress, book: &mut Settings) -> Vec<String> {
    let candidates = match event {
        Event::Recipe(id) => tree.recipe_criteria(id),
        Event::Inventory(id, _) => index.candidates([*id]),
    };
    let a = &tree.list[target];
    let mut added = Vec::new();
    for (ai, ci) in candidates {
        if ai != target || progress.done(a) || progress.has(&a.id, &a.criteria[ci].name) { continue; }
        let conditions = a.criteria[ci].conditions.read();
        let matched = match event {
            // The private Game handler's recipe predicate, after native indexing.
            Event::Recipe(id) => conditions["recipes"].as_str().is_some_and(|r| adv::full(r) == *id),
            Event::Inventory(id, count) => {
                // These five source inventory criteria have no slots/player or
                // other restrictions. Fail rather than approximate a new shape.
                assert_eq!(conditions.as_object().unwrap().len(), 1);
                let stack = ItemView { id: id.to_string(), count: *count, ..Default::default() };
                conditions["items"].as_array().unwrap().iter().all(|p| adv::item(p, &stack, world))
            },
        };
        if !matched { continue; }
        let before = progress.done(a);
        assert!(progress.grant(&a.id, &a.criteria[ci].name, "2026-11-14 00:00:00 +0000"));
        if !before && progress.done(a) {
            let rewards: Vec<_> = a.rewards.recipes.iter().filter(|id| recipes.contains(id)).cloned().collect();
            added.extend(book.add_recipes(recipes, &rewards).1);
        }
    }
    added
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 4 { return Err("expected EFFECTIVE_CONTENT_ROOT INSTALLED_WORLD ORIGINAL_OUTSIDE".into()); }
    let root = Path::new(&args[1]);
    let packs = datapack::discover(Path::new(&args[2]));
    assert_eq!(packs.len(), 1, "expected the installed isolated world datapack");
    let store = DataStore::load(&packs.iter().collect::<Vec<_>>());
    assert!(store.errors.is_empty());
    let files: Vec<_> = store.files.into_iter().collect();
    let overlay = PackOverlay { files: &files };
    let tree = Tree::load_with(&root.join("data"), &overlay);
    let baseline = Tree::load(&root.join("data"));
    let original = Tree::load(&Path::new(&args[3]).join("data"));
    let recipes = RecipeIndex::load(root, &overlay);
    let registry = horizon_world::registry::BlockRegistry::from_facts_json(std::fs::File::open(root.join("facts.json"))?)?;
    let block_facts = BlockFacts::load(root, &registry)?;
    let items = Items::load(root, &registry, &block_facts, &overlay)?;
    let crafts = Recipes::load(root, &items, &overlay)?;
    let world = ItemWorld(horizon_client::items::load_tags(root, "item", &overlay)?);
    let index = InventoryIndex::build(&tree, |tag| world.0.get(tag).map_or(Vec::new(), |s| s.iter().map(String::as_str).collect()));
    let legacy_index = InventoryIndex::build(&original, |tag| world.0.get(tag).map_or(Vec::new(), |s| s.iter().map(String::as_str).collect()));
    let mut cases = Vec::<Value>::new();
    let mut legacy_recipe_events_rejected = 0;
    let mut crafting_cases = Vec::new();
    for name in NAMES {
        let id = format!("minecraft:recipes/redstone/{name}");
        let target = tree.find_id(&id).ok_or("missing restored advancement")?;
        let a = &tree.list[target];
        let vanilla = format!("minecraft:{name}");
        let alternate = format!("terralith:{name}_alt");
        let rewards = vec![vanilla.clone(), alternate.clone()];
        assert_eq!(a.rewards.recipes, rewards);
        assert_eq!(baseline.get(&id).unwrap().rewards.recipes, [vanilla.clone()]);
        assert!(recipes.contains(&vanilla) && recipes.contains(&alternate));
        let legacy_target = original.find_id(&id).ok_or("missing legacy advancement")?;
        let mut old_progress = Progress::default();
        let mut old_book = Settings::default();
        old_book.add_recipes(&recipes, std::slice::from_ref(&vanilla));
        assert!(apply(&original, &legacy_index, &recipes, &world, legacy_target,
                      &Event::Recipe(&vanilla), &mut old_progress, &mut old_book).is_empty());
        assert!(!old_progress.done(&original.list[legacy_target]));
        legacy_recipe_events_rejected += 1;
        let pattern: &[&str] = match name {
            "dispenser" => &["###", "#X#", "#R#"],
            "dropper" => &["###", "# #", "#R#"],
            "lever" => &["X", "#"],
            "observer" => &["###", "RRQ", "###"],
            "piston" => &["TTT", "#X#", "#R#"],
            _ => unreachable!(),
        };
        assert!(!world.0["minecraft:stone_crafting_materials"].contains("minecraft:dirt"));
        let mut stones: Vec<_> = world.0["minecraft:stone_crafting_materials"].iter().collect();
        stones.sort();
        for stone in stones {
            for size in [2, 3] {
                if pattern.len() > size || pattern[0].len() > size { continue; }
                for top in 0..=size-pattern.len() { for left in 0..=size-pattern[0].len() { for mirror in [false, true] {
                    let mut grid = vec![None; size*size];
                    let mut stone_slot = None;
                    for (y, row) in pattern.iter().enumerate() {
                        for (x, symbol) in row.bytes().enumerate() {
                            let item = match symbol {
                                b'#' => stone.as_str(), b'T' => "minecraft:oak_planks", b'Q' => "minecraft:quartz",
                                b'R' => "minecraft:redstone", b'X' => match name {
                                    "dispenser" => "minecraft:bow", "lever" => "minecraft:stick", "piston" => "minecraft:iron_ingot",
                                    _ => unreachable!(),
                                }, b' ' => continue, _ => unreachable!(),
                            };
                            let x = if mirror { row.len()-1-x } else { x };
                            let slot = (top+y)*size+left+x;
                            grid[slot] = Some(ItemStack::new(item, 1));
                            if symbol == b'#' { stone_slot = Some(slot); }
                        }
                    }
                    assert!(crafts.recipe_matches(&alternate, &grid, size));
                    let (matched, output) = crafts.find(&grid, size).ok_or("alternate recipe did not craft")?;
                    assert_eq!(&*output.item, vanilla);
                    assert_eq!(output.count, 1);
                    if stone != "minecraft:cobblestone" { assert_eq!(matched, alternate); }
                    assert!(crafts.remainders(matched, &grid, size).iter().all(Option::is_none));
                    let mut wrong_stone = grid.clone();
                    wrong_stone[stone_slot.unwrap()] = Some(ItemStack::new("minecraft:dirt", 1));
                    assert!(!crafts.recipe_matches(&alternate, &wrong_stone, size));
                    let mut missing = grid.clone();
                    let slot = missing.iter().position(Option::is_some).unwrap();
                    missing[slot] = None;
                    assert!(!crafts.recipe_matches(&alternate, &missing, size));
                    crafting_cases.push(json!({"recipe": alternate, "stone": stone, "size":size,
                        "offset":[left,top],"mirrored":mirror,"matched":matched,"result":vanilla,
                        "count":1,"remainders_empty":true,"dirt_rejected":true,"missing_ingredient_rejected":true}));
                } } }
            }
        }
        let mut inputs: Vec<_> = NAMES.iter().flat_map(|n| [format!("minecraft:{n}"), format!("terralith:{n}_alt")])
            .map(|r| ("recipe", r, 1)).collect();
        inputs.push(("recipe", "minecraft:stick".into(), 1));
        let mut held: Vec<String> = ["minecraft:bow", "minecraft:redstone", "minecraft:quartz", "minecraft:coal"]
            .into_iter().map(str::to_owned).collect();
        held.extend(world.0.get("minecraft:stone_crafting_materials").ok_or("missing stone tag")?.iter().cloned());
        held.sort(); held.dedup();
        for item in held { for count in [1, 64] { inputs.push(("inventory", item.clone(), count)); } }
        for (mode, input, count) in inputs {
            let event = if mode == "recipe" { Event::Recipe(&input) } else { Event::Inventory(&input, count) };
            let expected = if mode == "recipe" { input == vanilla } else { match name {
                "dispenser" => input == "minecraft:bow",
                "dropper" | "piston" => input == "minecraft:redstone",
                "observer" => input == "minecraft:quartz",
                "lever" => world.0["minecraft:stone_crafting_materials"].contains(&input),
                _ => unreachable!(),
            }};
            let mut progress = Progress::default();
            let mut book = Settings::default();
            // Game emits recipe_unlocked AFTER the recipe entered the book.
            // Inventory events, by contrast, start with no learned recipes.
            if mode == "recipe" {
                assert!(recipes.contains(&input));
                book.add_recipes(&recipes, std::slice::from_ref(&input));
            }
            let before_recipes: Vec<_> = book.recipes.iter().cloned().collect();
            let already_knew_alternate = book.knows(&alternate);
            let added = apply(&tree, &index, &recipes, &world, target, &event, &mut progress, &mut book);
            assert_eq!(progress.done(a), expected, "{id} {mode} {input}");
            assert_eq!(added, if expected {
                if mode == "recipe" { vec![alternate.clone()] } else { rewards.clone() }
            } else { Vec::new() });
            assert_eq!(book.knows(&alternate), expected || already_knew_alternate);
            // Repeating the same event must not grant rewards twice.
            assert!(apply(&tree, &index, &recipes, &world, target, &event, &mut progress, &mut book).is_empty());
            let saved_progress = progress.to_json(&tree, horizon_world::DATA_VERSION);
            let mut restored_progress = Progress::from_json(&saved_progress);
            let mut restored_book = Settings::read_valid(Some(&book.write()), &|id| recipes.contains(id));
            assert_eq!(restored_progress.done(a), expected);
            assert_eq!(restored_book.knows(&alternate), expected || already_knew_alternate);
            assert!(apply(&tree, &index, &recipes, &world, target, &event, &mut restored_progress, &mut restored_book).is_empty());
            cases.push(json!({"advancement": id, "event": mode, "input": input, "count": count,
                              "recipes_before_event":before_recipes,"unlocked": added,
                              "progress_and_book_roundtrip": true, "replay_awards_nothing": true}));
        }
    }
    println!("{}", serde_json::to_string_pretty(&json!({"schema":1,"minecraft":"26.3",
        "restored_advancements":5,"legacy_recipe_events_rejected":legacy_recipe_events_rejected,
        "cases":cases,"crafting_cases":crafting_cases,"native_components_tested":true,"event_driver_is_harness":true,
        "actual_player_login_tested":false,"full_game_event_dispatch_tested":false}))?);
    Ok(())
}
