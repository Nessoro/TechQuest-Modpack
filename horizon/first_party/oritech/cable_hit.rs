// Oritech GenericPipeBlock side selection: Rearth, CC0-1.0; LICENSE-ORITECH.
// Uses pinned MIT Horizon geometry (LICENSE-HORIZON), not dependency Java code.
use horizon_core::{
    geometry::{Aabb, Direction, Vec3, VoxelShape},
    position::BlockPos,
};
use std::sync::OnceLock;

pub(super) const MASK_SIDES: [Direction; 6] = [
    Direction::North,
    Direction::East,
    Direction::South,
    Direction::West,
    Direction::Up,
    Direction::Down,
];

fn parts(wide: bool) -> &'static [VoxelShape; 7] {
    static THIN: OnceLock<[VoxelShape; 7]> = OnceLock::new();
    static WIDE: OnceLock<[VoxelShape; 7]> = OnceLock::new();
    let cache = if wide { &WIDE } else { &THIN };
    cache.get_or_init(|| {
        let (lo, hi) = if wide { (5.0, 11.0) } else { (6.0, 10.0) };
        [
            [lo, lo, 0.0, hi, hi, lo],
            [hi, lo, lo, 16.0, hi, hi],
            [lo, lo, hi, hi, hi, 16.0],
            [0.0, lo, lo, lo, hi, hi],
            [lo, hi, lo, hi, 16.0, hi],
            [lo, 0.0, lo, hi, lo, hi],
            [lo, lo, lo, hi, hi, hi],
        ]
        .map(|v| {
            VoxelShape::from_box(Aabb::new(
                Vec3::new(v[0] / 16.0, v[1] / 16.0, v[2] / 16.0),
                Vec3::new(v[3] / 16.0, v[4] / 16.0, v[5] / 16.0),
            ))
            .expect("fixed cable box")
        })
    })
}

pub(super) fn selection_hit(mask: u8, start: Vec3, end: Vec3) -> bool {
    parts(false).iter().enumerate().any(|(i, shape)| {
        (i == 6 || mask & (1 << i) != 0) && shape.clip(start, end, BlockPos::new(0, 0, 0)).is_some()
    })
}

/// Local coordinates and original N/E/S/W/U/D mask bits. The actual energy
/// cable is thin, but its wrench side selector tests thicker outer pieces.
pub(super) fn select_side(mask: u8, start: Vec3, end: Vec3) -> Option<Direction> {
    if !selection_hit(mask, start, end) {
        return None;
    }
    let mut nearest = f64::MAX;
    let mut selected = (0..6).find(|i| mask & (1 << i) != 0).unwrap_or(6);
    let mut point = Vec3::ZERO;
    for (i, shape) in parts(true).iter().enumerate() {
        if i != 6 && mask & (1 << i) == 0 {
            continue;
        }
        // Original skips the center after an outer hit, even if that center
        // would be closer. Choosing the closest face alone changes behavior.
        if i == 6 && nearest < f64::MAX {
            continue;
        }
        let Some(hit) = shape.clip(start, end, BlockPos::new(0, 0, 0)) else {
            continue;
        };
        let distance = hit.location.distance(start);
        if distance < nearest {
            nearest = distance;
            selected = i;
            point = hit.location;
        }
    }
    let difference = if selected == 6 {
        point.subtract(Vec3::new(0.5, 0.5, 0.5))
    } else {
        let d = MASK_SIDES[selected].normal();
        Vec3::new(f64::from(d[0]), f64::from(d[1]), f64::from(d[2]))
    };
    Some(Direction::approximate_nearest(difference))
}
