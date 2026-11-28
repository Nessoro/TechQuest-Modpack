// Oritech SimpleFluidStorage/SimpleInOutFluidStorage: Rearth, CC0-1.0.
// NativeFluidStack integration: Horizon MIT; retained license files.
use crate::mod_api::NativeFluidStack;

pub(super) const CAPACITY: i32 = 256_000;

pub(super) fn valid(stack: &NativeFluidStack) -> bool {
    stack.amount > 0 && stack.fluid != "minecraft:empty"
}

pub(super) fn insert(
    stored: &mut Option<NativeFluidStack>,
    incoming: &NativeFluidStack,
    capacity: i32,
    simulate: bool,
) -> i32 {
    if !valid(incoming) {
        return 0;
    }
    if let Some(current) = stored.as_ref().filter(|s| valid(s)) {
        if current.fluid != incoming.fluid || current.components != incoming.components {
            return 0;
        }
        let moved = incoming.amount.min((capacity - current.amount).max(0));
        if moved > 0 && !simulate {
            stored.as_mut().unwrap().amount += moved;
        }
        moved
    } else {
        let moved = incoming.amount.min(capacity.max(0));
        if moved > 0 && !simulate {
            let mut next = incoming.clone();
            next.amount = moved;
            *stored = Some(next);
        }
        moved
    }
}

pub(super) fn extract(
    stored: &mut Option<NativeFluidStack>,
    requested: &NativeFluidStack,
    simulate: bool,
) -> i32 {
    let Some(current) = stored.as_ref().filter(|s| valid(s)) else {
        return 0;
    };
    if !valid(requested)
        || current.fluid != requested.fluid
        || current.components != requested.components
    {
        return 0;
    }
    let moved = requested.amount.min(current.amount);
    if moved > 0 && !simulate {
        let amount = current.amount - moved;
        if amount == 0 {
            *stored = None;
        } else {
            stored.as_mut().unwrap().amount = amount;
        }
    }
    moved
}
