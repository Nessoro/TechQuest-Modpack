// CountCap must see the entire template before the chunk's write clipping.
// Otherwise the guaranteed minimum is repeated in every intersected chunk.
// Capped and every other processor keep the pinned engine's original decision.
fn count_scope(
    processor: &crate::worldgen::structure::processor::Processor,
) -> std::ops::ControlFlow<bool> {
    if matches!(
        processor,
        crate::worldgen::structure::processor::Processor::CountCap(_)
    ) {
        std::ops::ControlFlow::Break(true)
    } else {
        std::ops::ControlFlow::Continue(())
    }
}
