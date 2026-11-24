//! Pure scheduling and topology for the first-party vertical transfer node.
//! No game globals; the authoritative Horizon host owns the actual inventory move.

pub const PERIOD: i32 = 8;
pub const MAX_ITEMS: u32 = 1;

/// Returns the next saved cooldown and whether this tick may attempt a move.
/// A powered node tries once per eight ticks. Unpowered ticks never move items.
pub fn pulse(saved: i32, powered: bool) -> (i32, bool) {
    let saved = saved.clamp(0, PERIOD - 1);
    if !powered {
        return (saved, false);
    }
    if saved == 0 {
        (PERIOD - 1, true)
    } else {
        (saved - 1, false)
    }
}

/// Source above, destination below. No arithmetic wrap at invalid coordinates.
pub fn endpoints([x, y, z]: [i32; 3]) -> Option<([i32; 3], [i32; 3])> {
    Some(([x, y.checked_add(1)?, z], [x, y.checked_sub(1)?, z]))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn powered_rate_is_one_attempt_per_period() {
        let mut saved = 0;
        let mut attempts = Vec::new();
        for tick in 0..32 {
            let (next, attempt) = pulse(saved, true);
            saved = next;
            if attempt {
                attempts.push(tick);
            }
        }
        assert_eq!(attempts, [0, 8, 16, 24]);
        assert_eq!(MAX_ITEMS, 1);
    }

    #[test]
    fn unpowered_does_not_move_or_advance() {
        assert_eq!(pulse(4, false), (4, false));
        assert_eq!(pulse(0, false), (0, false));
    }

    #[test]
    fn saved_cooldown_resumes_without_extra_move() {
        assert_eq!(pulse(3, true), (2, false));
        assert_eq!(pulse(1, true), (0, false));
        assert_eq!(pulse(0, true), (7, true));
    }

    #[test]
    fn corrupted_cooldown_is_bounded() {
        assert_eq!(pulse(i32::MAX, true), (6, false));
        assert_eq!(pulse(i32::MIN, false), (0, false));
    }

    #[test]
    fn vertical_endpoints_keep_x_and_z() {
        assert_eq!(endpoints([5, 64, -2]), Some(([5, 65, -2], [5, 63, -2])));
    }

    #[test]
    fn coordinate_overflow_refused() {
        assert_eq!(endpoints([0, i32::MAX, 0]), None);
        assert_eq!(endpoints([0, i32::MIN, 0]), None);
    }
}
