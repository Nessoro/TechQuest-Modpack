// Selected Oritech basic cable semantics: Rearth, CC0-1.0; LICENSE-ORITECH.
// Horizon native helpers: MIT, LICENSE-HORIZON. Loaded networks only.
use super::{Game, GameLevel, techquest_oritech as machines};
use horizon_client_lib::containers::{BlockEntity, ModBlockEntity};
use horizon_core::{
    geometry::Direction,
    random::{LegacyRandom, RandomSource},
};
use horizon_world::{nbt::Tag, registry::BlockStateId};
use std::{
    cell::RefCell,
    collections::{BTreeMap, BTreeSet},
    time::{SystemTime, UNIX_EPOCH},
};

pub(super) const WIRE: &str = "oritech:energy_pipe";
pub(super) const ENDPOINT: &str = "oritech:energy_pipe_connection";
const NAMES: [&str; 6] = ["down", "up", "north", "south", "west", "east"];
// 0: retain disabled sides; 1: freshly placed wire; 2: new energy provider.
thread_local! {
    static DIRTY: RefCell<BTreeMap<(String, [i32; 3]), u8>> = RefCell::new(BTreeMap::new());
    // Collections.shuffle uses a separate, unseeded java.util.Random, not
    // Level.random. Keep this stream separate from every world RNG as well.
    static RANDOM: RefCell<LegacyRandom> = RefCell::new(LegacyRandom::new(
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_nanos() as i64
        ^ i64::from(std::process::id())));
}
pub(super) fn cable(id: &str) -> bool {
    matches!(id, WIRE | ENDPOINT)
}
fn neighbor(pos: [i32; 3], face: Direction) -> [i32; 3] {
    let d = face.normal();
    std::array::from_fn(|i| pos[i].saturating_add(d[i]))
}
pub(super) fn mark(dimension: &str, pos: [i32; 3], mode: u8) {
    DIRTY.with(|queue| {
        queue
            .borrow_mut()
            .entry((dimension.into(), pos))
            .and_modify(|old| *old = (*old).max(mode))
            .or_insert(mode);
    });
}
pub(super) fn changed(level: &GameLevel<'_>, pos: [i32; 3], old: BlockStateId, new: BlockStateId) {
    let before = &level.facts.get(old).name;
    let after = &level.facts.get(new).name;
    // Properties already encode manually disconnected sides. Do not undo
    // them when a state is restored from a command or an internal refresh.
    if before == after {
        return;
    }
    let relevant = |id: &str| cable(id) || machines::machine(id) || id == machines::CORE;
    if !relevant(before)
        && !relevant(after)
        && level.world.block_entities.mod_energy(old.0).is_none()
        && level.world.block_entities.mod_energy(new.0).is_none()
    {
        return;
    }
    let mode = if cable(after) && !cable(before) {
        1
        } else if !cable(after) && after.as_ref() != "minecraft:air" {
        2
    } else {
        0
    };
    mark(level.dimension.key().id(), pos, mode);
}
fn provider(game: &Game<'_>, pos: [i32; 3], face: Direction) -> bool {
    let id = game.native_block(pos);
    if cable(&id) {
        return false;
    }
    if id == machines::CORE {
        return machines::controller(game, pos).is_some();
    }
    machines::machine(&id) || game.native_energy(game.dim.id(), pos, face).is_some()
}
fn connected(game: &Game<'_>, pos: [i32; 3], face: Direction) -> bool {
    game.native_block_property(pos, NAMES[face as usize])
        .as_deref()
        == Some("1")
}
fn refresh(game: &mut Game<'_>, pos: [i32; 3], create: u8) {
    let id = game.native_block(pos);
    if !cable(&id) {
        return;
    }
    // An absent neighboring chunk is not a machine removal. Do not discard
    // an endpoint's saved energy while startup is still loading its machine.
    if Direction::ALL.into_iter().any(|d| {
        let p = neighbor(pos, d);
        !game.world.chunks.contains_key(&(p[0] >> 4, p[2] >> 4))
    }) {
        return;
    }
    let mut arms = [false; 6];
    let mut has_machine = false;
    for face in Direction::ALL {
        let p = neighbor(pos, face);
        let other = game.native_block(p);
        let force = create & (1 << face as usize) != 0;
        let machine = provider(game, p, face.opposite());
        arms[face as usize] = if cable(&other) {
            force || (connected(game, pos, face) && connected(game, p, face.opposite()))
        } else {
            machine && (force || connected(game, pos, face))
        };
        has_machine |= machine && arms[face as usize];
    }
    let wanted = if has_machine { ENDPOINT } else { WIRE };
    let Some(default) = game.native_default_state(wanted) else {
        return;
    };
    let registry = game.pack.assets.registry;
    let Some(mut descriptor) = registry.state(default).cloned() else {
        return;
    };
    for (face, value) in NAMES.into_iter().zip(arms) {
        descriptor
            .properties
            .insert(face.into(), if value { "1" } else { "0" }.into());
    }
    let straight = arms.iter().filter(|v| **v).count() == 2
        && ((arms[0] && arms[1]) || (arms[2] && arms[3]) || (arms[4] && arms[5]));
    descriptor
        .properties
        .insert("straight".into(), straight.to_string());
    // Preserve stored waterlogged state; bucket/fluid interaction is deferred.
    if let Some(value) = game.native_block_property(pos, "waterlogged") {
        descriptor.properties.insert("waterlogged".into(), value);
    }
    if let Ok(state) = registry.resolve(&descriptor) {
        let dimension = game.dim.id().to_string();
        if state != game.world.block(pos[0], pos[1], pos[2]) {
            game.native_set_block(&dimension, pos, state, 3);
        }
    }
}
pub(super) fn flush(game: &mut Game<'_>) {
    if game.serving.is_none() && game.options.dedicated.is_none() {
        return;
    }
    let dimension = game.dim.id().to_string();
    loop {
        let events = DIRTY.with(|queue| {
            let mut queue = queue.borrow_mut();
            let keys: Vec<_> = queue
                .keys()
                .filter(|(dim, _)| dim == &dimension)
                .cloned()
                .collect();
            keys.into_iter()
                .map(|key| {
                    let mode = queue.remove(&key).unwrap();
                    (key.1, mode)
                })
                .collect::<Vec<_>>()
        });
        if events.is_empty() {
            break;
        }
        for (pos, mode) in events {
            refresh(game, pos, if mode == 1 { 63 } else { 0 });
            for face in Direction::ALL {
                let p = neighbor(pos, face);
                refresh(
                    game,
                    p,
                    if mode > 0 {
                        1 << face.opposite() as usize
                    } else {
                        0
                    },
                );
            }
        }
    }
}
pub(super) fn loaded(game: &Game<'_>, dimension: &str, chunk: [i32; 2]) {
    if (game.serving.is_none() && game.options.dedicated.is_none()) || dimension != game.dim.id() {
        return;
    }
    // Existing disabled edges stay disabled on load. A live graph is rebuilt
    // from block states, so no opaque cached network needs deserialization.
    for (key, entity) in game.world.block_entities.iter() {
        if (key.0 >> 4, key.2 >> 4) != (chunk[0], chunk[1]) {
            continue;
        }
        if let BlockEntity::Mod(entity) = entity {
            if cable(&entity.id) || machines::machine(&entity.id) || entity.id == machines::CORE {
                mark(dimension, [key.0, key.1, key.2], 0);
            }
        }
    }
}
pub(super) fn assembled(game: &mut Game<'_>, controller: [i32; 3]) {
    let positions = if game.native_block(controller) == machines::FURNACE {
        vec![[controller[0], controller[1] + 1, controller[2]]]
    } else {
        machines::multiblock_cores(game, controller).to_vec()
    };
    for pos in positions {
        mark(game.dim.id(), pos, 2);
    }
    flush(game);
}
pub(super) fn tick(game: &mut Game<'_>, pos: [i32; 3], entity: &mut ModBlockEntity) {
    let mut energy = match entity.nbt.get(&"energy".into()) {
        Some(Tag::Int(v)) => (*v).max(0),
        _ => 0,
    };
    if energy == 0 {
        return;
    }
    let mut visited = BTreeSet::new();
    let mut frontier = BTreeSet::from([pos]);
    let mut targets = BTreeSet::new();
    while !frontier.is_empty() {
        let generation = std::mem::take(&mut frontier);
        for node in generation {
            if !cable(&game.native_block(node)) || !visited.insert(node) {
                continue;
            }
            for face in Direction::ALL {
                if !connected(game, node, face) {
                    continue;
                }
                let p = neighbor(node, face);
                if cable(&game.native_block(p)) {
                    if !visited.contains(&p) {
                        frontier.insert(p);
                    }
                } else if provider(game, p, face.opposite()) {
                    targets.insert((p, face.opposite() as usize));
                }
            }
        }
        // Original checks after the complete BFS generation, not after each
        // node. This loaded-only graph intentionally has no stale nodes.
        if visited.len() >= 2048 {
            break;
        }
    }
    let mut targets: Vec<_> = targets.into_iter().collect();
    RANDOM.with(|random| {
        let mut random = random.borrow_mut();
        for n in (2..=targets.len()).rev() {
            let other = random
                .next_int_bound(n as i32)
                .expect("positive shuffle bound") as usize;
            targets.swap(n - 1, other);
        }
    });
    for (target, face) in targets {
        if energy == 0 {
            break;
        }
        let controller = machines::controller(game, target).unwrap_or(target);
        energy -=
            game.native_energy_insert(controller, Direction::ALL[face], energy.min(10000), false);
    }
    entity.nbt.insert("energy".into(), Tag::Int(energy));
}
