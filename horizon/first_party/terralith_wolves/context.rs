// One-shot bridge from Game's cached world tags to the reusable selector.
// No cross-thread state, I/O or random draws. A mismatched read discards it.
use std::cell::RefCell;
thread_local! {
    static PENDING: RefCell<Option<(String,u8)>> = const { RefCell::new(None) };
}
pub fn clear() { PENDING.with(|slot| *slot.borrow_mut() = None); }
pub fn stage(biome: &str, variant: u8) {
    PENDING.with(|slot| *slot.borrow_mut() = Some((biome.to_owned(),variant)));
}
pub fn take(biome: &str) -> Option<u8> {
    PENDING.with(|slot| slot.borrow_mut().take()).and_then(|(name,variant)| (name==biome).then_some(variant))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn context_is_consumed_once() {
        stage("terralith:wintry_forest",4);
        assert_eq!(take("terralith:wintry_forest"),Some(4));
        assert_eq!(take("terralith:wintry_forest"),None);
    }
    #[test]
    fn stale_context_does_not_reach_another_biome_or_world() {
        stage("terralith:wintry_forest",4);
        assert_eq!(take("minecraft:plains"),None);
        assert_eq!(take("terralith:wintry_forest"),None);
        stage("terralith:wintry_forest",4);clear();
        assert_eq!(take("terralith:wintry_forest"),None);
    }
    #[test]
    fn concurrent_game_threads_keep_separate_contexts() {
        stage("terralith:alpine_highlands",3);
        let child=std::thread::spawn(|| {
            assert_eq!(take("terralith:alpine_highlands"),None);
            stage("terralith:wintry_forest",4);
            take("terralith:wintry_forest")
        });
        assert_eq!(child.join().unwrap(),Some(4));
        assert_eq!(take("terralith:alpine_highlands"),Some(3));
    }
}
