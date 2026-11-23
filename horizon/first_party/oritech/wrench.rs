// Selected original Wrench semantics: Rearth, CC0-1.0; LICENSE-ORITECH.
// Horizon Game/use/cooldown integration: MIT, LICENSE-HORIZON.
use super::{
    Game, Hit, techquest_oritech_cable_hit as selection, techquest_oritech_cables as cables,
};
use horizon_client_lib::items::ItemStack;
use horizon_core::geometry::{Direction, Vec3};
use std::{cell::RefCell, ops::ControlFlow};

const WRENCH: &str = "oritech:wrench";
thread_local! {
    // Outer None: not a wrench turn. Some(None): the vanilla block phase
    // has not reached item use. Some(Some(result)): one item attempt ran.
    static TURN: RefCell<Option<Option<bool>>> = const { RefCell::new(None) };
}
struct Turn;
impl Drop for Turn {
    fn drop(&mut self) {
        TURN.with(|v| *v.borrow_mut() = None);
    }
}

/// Let the original Game block/permission/cooldown phases run once, then
/// translate the one captured custom item result into SUCCESS or FAIL. A
/// recursion guard enters the original body, rather than duplicating it.
pub(super) fn interact(
    game: &mut Game<'_>,
    hit: Option<&Hit>,
) -> ControlFlow<horizon_client_lib::Result<bool>> {
    if (game.serving.is_none() && game.options.dedicated.is_none())
        || game.held().is_none_or(|stack| &*stack.item != WRENCH)
        || TURN.with(|v| v.borrow().is_some())
    {
        return ControlFlow::Continue(());
    }
    TURN.with(|v| *v.borrow_mut() = Some(None));
    let scope = Turn;
    let base = game.use_hand(hit);
    let attempted = TURN.with(|v| v.borrow().flatten());
    drop(scope);
    ControlFlow::Break(base.map(|base| match attempted {
        Some(success) => {
            if success {
                game.swing_arm();
            } else {
                game.use_failed = true;
            }
            true
        }
        None => base,
    }))
}

pub(super) fn item_use(game: &mut Game<'_>, stack: &ItemStack, claimed: &mut bool) {
    if *claimed || &*stack.item != WRENCH || !TURN.with(|v| matches!(*v.borrow(), Some(None))) {
        return;
    }
    // Mark before side effects, so even a nested native event cannot run a
    // second attempt. useOn + use, or a following network packet, must not
    // toggle back; the original shared cooldown also blocks that packet.
    TURN.with(|v| *v.borrow_mut() = Some(Some(false)));
    let result = attempt(game);
    TURN.with(|v| *v.borrow_mut() = Some(Some(result)));
    // Leave claimed false: the guard restores the exact custom result and
    // performs a success-only swing after the harmless stick-template tail.
}

fn attempt(game: &mut Game<'_>) -> bool {
    if game.cooldowns.is_on_cooldown(WRENCH) {
        return false;
    }
    game.add_cooldown(WRENCH.into(), 8);
    let Some(eye) = game.eye_position() else {
        return false;
    };
    let view = super::view_vector(game.yaw, game.pitch);
    let Some(hit) = game.clip_ray(eye, view, f64::from(game.block_reach)) else {
        return false;
    };
    if cables::cable(&game.native_block(hit.pos)) {
        if game.keys.held(super::Mapping::Sneak) {
            // Level.destroyBlock(true), not creative player mining: the
            // original Shift wrench also drops one normal cable in creative.
            let removed = game
                .native_machine_destroy_block(hit.pos, None, false)
                .is_some();
            cables::flush(game);
            return removed;
        }
        let mask = selection::MASK_SIDES
            .iter()
            .enumerate()
            .fold(0u8, |mask, (bit, side)| {
                let key = ["down", "up", "north", "south", "west", "east"][*side as usize];
                if game.native_block_property(hit.pos, key).as_deref() == Some("1") {
                    mask | (1 << bit)
                } else {
                    mask
                }
            });
        let local = Vec3::new(
            eye[0] - f64::from(hit.pos[0]),
            eye[1] - f64::from(hit.pos[1]),
            eye[2] - f64::from(hit.pos[2]),
        );
        let end = local.add_vector(Vec3::new(view[0] * 5.0, view[1] * 5.0, view[2] * 5.0));
        selection::select_side(mask, local, end)
            .is_some_and(|side| cables::toggle_side(game, hit.pos, side))
    } else {
        // The five ported machines are not Wrenchable in the original.
        // Once their block phase passes (e.g. secondary use), a ray hitting
        // their face may address the adjacent cable, even while sneaking.
        let Some(face) = Direction::ALL
            .into_iter()
            .find(|side| side.normal() == hit.face)
        else {
            return false;
        };
        let d = face.normal();
        let neighbor = std::array::from_fn(|i| hit.pos[i].saturating_add(d[i]));
        cables::cable(&game.native_block(neighbor))
            && cables::toggle_side(game, neighbor, face.opposite())
    }
}
