//! Execute the production storage code against original runtime observations.
//! The shim only supplies the owned resource type; no storage logic is copied.
use serde_json::{Value, json};
mod mod_api {
    #[derive(Clone, Debug, PartialEq)]
    pub struct NativeFluidStack {
        pub fluid: String,
        pub amount: i32,
        pub components: String,
    }
}
#[path = "../first_party/oritech/fluid_storage.rs"]
mod storage;
fn read(v: &Value) -> mod_api::NativeFluidStack {
    mod_api::NativeFluidStack {
        fluid: v["fluid"].as_str().unwrap().into(),
        amount: v["amount"].as_i64().unwrap() as i32,
        components: v["components"].as_str().unwrap().into(),
    }
}
fn main() {
    let path = std::env::args().nth(1).expect("original JSON");
    let original: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let capacity = original["capacity"].as_i64().unwrap() as i32;
    assert_eq!(capacity, storage::CAPACITY);
    let rows = original["storage"].as_array().unwrap();
    for (i, row) in rows.iter().enumerate() {
        let initial = read(&row["initial"]);
        let mut held = storage::valid(&initial).then_some(initial);
        let request = read(&row["request"]);
        let simulate = row["simulate"].as_bool().unwrap();
        let moved = if row["insert"].as_bool().unwrap() {
            storage::insert(&mut held, &request, capacity, simulate)
        } else {
            storage::extract(&mut held, &request, simulate)
        };
        let after = match held {
            Some(s) => {
                json!({"fluid":s.fluid,"amount":s.amount,"components":s.components,"empty":false})
            }
            None => json!({"fluid":"minecraft:empty","amount":0,"components":"{}","empty":true}),
        };
        assert_eq!(json!(moved), row["moved"], "moved case {i}");
        assert_eq!(after, row["after"], "state case {i}");
    }
    println!(
        "{}",
        json!({"schema":1,"capacity":capacity,"comparisons":rows.len(),
        "candidate_storage_code_executed":true,"component_equality_checked":true,
        "type_shim_uses_original_component_patch_debug_strings":true,"mismatches":[]})
    );
}
