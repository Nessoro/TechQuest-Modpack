//! Native, server-authoritative industrial item transfer. Original TechQuest code.
use horizon_client::mod_api::{
    BlockEntityEvent, BlockEntityTickEvent, BlockEntityTicksEvent, Compound, Direction, Hooks,
    Host, Tag,
};

mod logic;

const BLOCK: &str = "techquest_industrial_content:transfer_node";
const ENTITY: &str = "techquest_industrial_transfer:transfer_node";
const COOLDOWN: &str = "techquest_cooldown";

pub fn hooks() -> Box<dyn Hooks> {
    Box::new(TransferMod)
}

struct TransferMod;

impl Hooks for TransferMod {
    fn block_entity(
        &self,
        _host: &mut dyn Host,
        event: &mut BlockEntityEvent<'_>,
    ) -> Option<(String, Compound)> {
        (event.block == BLOCK).then(|| (ENTITY.to_owned(), Compound::default()))
    }

    fn block_entity_ticks(&self, _host: &dyn Host, event: &mut BlockEntityTicksEvent<'_>) {
        if event.block == BLOCK {
            event.ticks = true;
        }
    }

    fn block_entity_tick(&self, host: &mut dyn Host, event: &mut BlockEntityTickEvent<'_>) {
        if event.entity.id != ENTITY {
            return;
        }
        let Some((source, target)) = logic::endpoints(event.pos) else {
            return;
        };
        let dimension = host.dimension();
        let powered = host.neighbor_signal(dimension, event.pos) > 0;
        let cooldown = match event.entity.nbt.get(&COOLDOWN.into()) {
            Some(Tag::Int(value)) => *value,
            _ => 0,
        };
        let (next, attempt) = logic::pulse(cooldown, powered);
        if next != cooldown {
            event.entity.nbt.insert(COOLDOWN.into(), Tag::Int(next));
        }
        if attempt {
            // Use Horizon's checked move, never extract and then manually insert.
            // Refused items stay at their source; unloaded targets and same-container
            // moves are rejected by the engine. No global scans or forced chunks.
            host.move_items(
                dimension,
                source,
                Direction::Down,
                target,
                Direction::Up,
                None,
                logic::MAX_ITEMS,
            );
        }
    }
}
