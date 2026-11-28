// Execute the exact native cable-side module against original binary output.
#[path = "../first_party/oritech/cable_hit.rs"]
mod cable_hit;
use horizon_core::{geometry::{Aabb, Direction, Vec3, VoxelShape, ShapeOp}, position::BlockPos};
use serde_json::{Value, json};
use std::{env, fs};

fn vec(value: &Value) -> Vec3 {
    let v = value.as_array().unwrap();
    Vec3::new(
        v[0].as_f64().unwrap(),
        v[1].as_f64().unwrap(),
        v[2].as_f64().unwrap(),
    )
}
fn name(side: Direction) -> &'static str {
    ["down", "up", "north", "south", "west", "east"][side as usize]
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 3, "original-result.json staged-content-directory");
    let original: Value = serde_json::from_slice(&fs::read(&args[1])?)?;
    assert_eq!(
        original["fake_player_head_body_and_previous_rotation_synchronized"],
        true
    );
    let rows = original["geometry"].as_array().unwrap();
    let mut payload_shapes = Vec::new();
    for block in ["energy_pipe", "energy_pipe_connection"] {
        let path = std::path::Path::new(&args[2]).join(format!("data/oritech/horizon/block/{block}.json"));
        let payload: Value = serde_json::from_slice(&fs::read(path)?)?;
        assert_eq!(payload["shapes"], payload["collision_shapes"]);
        let props = payload["shapes"]["properties"].as_array().unwrap();
        let mut resolved = Vec::new();
        for mask in 0..64u8 {
            let key = props.iter().map(|prop| {
                let bit = cable_hit::MASK_SIDES.iter().position(|&side| name(side) == prop.as_str().unwrap()).unwrap();
                if mask & (1 << bit) == 0 { "0" } else { "1" }
            }).collect::<Vec<_>>().join(",");
            let mut shape = VoxelShape::empty();
            for bounds in payload["shapes"]["values"][&key].as_array().unwrap() {
                let b: Vec<f64> = bounds.as_array().unwrap().iter().map(|v| v.as_f64().unwrap()).collect();
                assert!(b.iter().all(|v| (0.0..=1.0).contains(v)), "BlockShapes uses block units");
                let part = VoxelShape::from_box(Aabb::new(Vec3::new(b[0],b[1],b[2]),Vec3::new(b[3],b[4],b[5])))?;
                shape = shape.join_unoptimized(&part, ShapeOp::OR)?;
            }
            resolved.push(shape);
        }
        payload_shapes.push(resolved);
    }
    let mut hits = 0;
    let mut mismatches = Vec::new();
    for (i, row) in rows.iter().enumerate() {
        let mask = row["mask"].as_u64().unwrap() as u8;
        let actual = cable_hit::select_side(mask, vec(&row["eye"]), vec(&row["end"]));
        let expected = row.get("selected_side").and_then(Value::as_str);
        for shapes in &payload_shapes {
            let hit = shapes[mask as usize].clip(vec(&row["eye"]), vec(&row["end"]), BlockPos::new(0,0,0)).is_some();
            assert_eq!(hit, expected.is_some(), "installed cable outline differs at ray {i}");
        }
        if actual.is_some() {
            hits += 1;
        }
        if actual.map(name) != expected {
            mismatches.push(json!({"index":i,"row":row,"actual":actual.map(name)}));
        }
    }
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"schema":1,"rays":rows.len(),"hits":hits,"mismatches":mismatches,"same_module_as_native":true,
                "content_shape_rays":rows.len()*payload_shapes.len(),"resolved_shapes":128,"content_units_checked":true})
        )?
    );
    assert!(
        mismatches.is_empty(),
        "wrench geometry differs from original"
    );
    Ok(())
}
