// Main menu controls for the implemented extractor's sample filter.
// Filter/direction semantics: Ellpeck, MIT; see LICENSE-PRETTY-PIPES.
use super::Game;
use horizon_client_lib::{
    containers::ModBlockEntity,
    hud::HudBatch,
    items::{ItemStack, Items},
    lang,
};
use horizon_client_lib::{
    techquest_pretty_pipes_filter as filter, techquest_pretty_pipes_modules as modules,
};
use horizon_core::geometry::Direction;

pub const DATA: usize = 21;

pub fn update(items: &Items, entity: &mut ModBlockEntity) {
    let mut data = vec![0; DATA];
    if let Some(settings) = entity
        .items
        .iter()
        .take(3)
        .flatten()
        .find_map(filter::Settings::load)
    {
        data[0] = settings.samples.len() as i32;
        data[1] = i32::from(settings.whitelist);
        data[2] = settings.direction.unwrap_or(6) as i32;
        for (i, sample) in settings.samples.iter().enumerate() {
            let id = sample
                .as_ref()
                .and_then(|s| items.registry_order.iter().position(|id| *id == s.item))
                .map_or(0, |id| id as u32 + 1);
            data[3 + 2 * i] = (id & 0xffff) as i32;
            data[4 + 2 * i] = (id >> 16) as i32;
        }
    }
    entity.data = data;
}

fn count(data: &[i32]) -> usize {
    match data.first() {
        Some(3) => 3,
        Some(6) => 6,
        Some(9) => 9,
        _ => 0,
    }
}
fn item<'a>(game: &'a Game<'_>, data: &[i32], slot: usize) -> Option<&'a str> {
    let low = *data.get(3 + 2 * slot)? as u16 as u32;
    let high = *data.get(4 + 2 * slot)? as u16 as u32;
    let id = (low | (high << 16)).checked_sub(1)? as usize;
    game.res.items().registry_order.get(id).map(|s| &**s)
}
fn white_key(data: &[i32]) -> &'static str {
    if data.get(1) == Some(&1) {
        "info.prettypipes.whitelist"
    } else {
        "info.prettypipes.blacklist"
    }
}
fn inside(at: [f32; 2], r: [f32; 4]) -> bool {
    at[0] >= r[0] && at[0] < r[0] + r[2] && at[1] >= r[1] && at[1] < r[1] + r[3]
}
fn sample_x(n: usize, i: usize) -> f32 {
    (176.0 - n as f32 * 18.0) / 2.0 + 1.0 + i as f32 * 18.0
}

pub fn draw(game: &Game<'_>, block: &str, data: &[i32], batch: &mut HudBatch, origin: [f32; 2]) {
    if block != "prettypipes:pipe" {
        return;
    }
    let n = count(data);
    if n == 0 {
        return;
    }
    let [x, y] = origin;
    for i in 0..n {
        let sx = sample_x(n, i);
        game.native_fill(batch, [x + sx - 1.0, y + 77.0, 18.0, 18.0], 0xff373737);
        game.native_fill(batch, [x + sx, y + 78.0, 16.0, 16.0], 0xff8b8b8b);
        if let Some(id) = item(game, data, i) {
            game.native_item(batch, id, [x + sx, y + 78.0], 16.0);
        }
    }
    for (rect, label) in [
        (
            [8.0, 99.0, 110.0, 11.0],
            lang::get(&format!(
                "dir.prettypipes.{}",
                filter::DIRECTIONS
                    .get(data.get(2).copied().unwrap_or(6) as usize)
                    .copied()
                    .unwrap_or("all")
            )),
        ),
        ([143.0, 99.0, 24.0, 11.0], lang::get(white_key(data))),
    ] {
        game.native_fill(
            batch,
            [x + rect[0], y + rect[1], rect[2], rect[3]],
            0xff707070,
        );
        game.native_text(
            batch,
            &label,
            [x + rect[0] + 3.0, y + rect[1] + 1.0],
            0xffffff,
            false,
        );
    }
}

pub fn click(block: &str, data: &[i32], at: [f32; 2], button: &mut Option<i32>) {
    if block != "prettypipes:pipe" || button.is_some() {
        return;
    }
    let n = count(data);
    if n == 0 {
        return;
    }
    for i in 0..n {
        if inside(at, [sample_x(n, i) - 1.0, 77.0, 18.0, 18.0]) {
            *button = Some(32 + i as i32);
            return;
        }
    }
    if inside(at, [143.0, 99.0, 24.0, 11.0]) {
        *button = Some(48);
    }
    if inside(at, [8.0, 99.0, 110.0, 11.0]) {
        *button = Some(49);
    }
}

pub fn tooltip(game: &Game<'_>, block: &str, data: &[i32], at: [f32; 2], lines: &mut Vec<String>) {
    let mut button = None;
    click(block, data, at, &mut button);
    if let Some(id @ 32..=40) = button {
        if let Some(id) = item(game, data, (id - 32) as usize) {
            let stem = id.replace(':', ".");
            let key = format!("item.{stem}");
            lines.push(lang::get_or(&key, &lang::get(&format!("block.{stem}"))));
        }
    } else if button == Some(48) {
        lines.push(lang::get(&format!("{}.description", white_key(data))));
    }
}

pub fn button(
    game: &mut Game<'_>,
    pos: [i32; 3],
    entity: &mut ModBlockEntity,
    id: i32,
    carried: &mut Option<ItemStack>,
) {
    if entity.id != "prettypipes:pipe" || !matches!(id, 32..=40 | 48 | 49) {
        return;
    }
    let fields = &mut **entity;
    if modules::synchronize(&mut fields.nbt, &mut fields.items).is_none() {
        return;
    }
    let Some(stack) = entity
        .items
        .iter_mut()
        .take(3)
        .flatten()
        .find(|s| filter::slots(&s.item).is_some())
    else {
        return;
    };
    let Some(mut settings) = filter::Settings::load(stack) else {
        return;
    };
    match id {
        32..=40 => {
            if !settings.ghost_click((id - 32) as usize, carried.as_ref()) {
                return;
            }
            settings.save_filter(stack);
        }
        48 => {
            settings.whitelist = !settings.whitelist;
            settings.save_filter(stack);
        }
        49 => {
            let dimension = game.native_dimension();
            settings.cycle_direction(Direction::ALL.map(|d| {
                let delta = d.normal();
                let at = std::array::from_fn(|i| pos[i].saturating_add(delta[i]));
                game.native_container_slots(dimension, at, d.opposite())
                    .is_some_and(|s| !s.is_empty())
            }));
            settings.save_direction(stack);
        }
        _ => return,
    }
    let fields = &mut **entity;
    modules::synchronize(&mut fields.nbt, &mut fields.items);
    update(game.res.items(), entity);
}
